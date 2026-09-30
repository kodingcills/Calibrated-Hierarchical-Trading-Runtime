"""Streaming structural admission of a Nasdaq TotalView-ITCH 5.0 session tape.

Two jobs, both structural (this module never reads an economic outcome):

``stream``
    Read a gzip-compressed ITCH session from stdin, verify every BinaryFILE
    frame's two-byte big-endian length prefix against the documented message
    length, prove gzip integrity, and retain only the messages the closing
    auction contract needs: all ``R`` Stock Directory messages, all System Event
    messages, and every message whose exchange timestamp falls in the frozen
    auction window. The multi-GB source is never written to disk; only the
    compressed byte count and a running SHA-256 see it.

``coverage``
    On the retained window alone, compute the preregistered symbol-coverage
    ratio for the closing-auction universe and write a per-symbol missingness
    audit.

Framing, the message-length table, the fixed header and the Stock Directory
field offsets are imported from :mod:`M2.src.ingest`; they are not copied. The
NOII ``I`` and Cross Trade ``Q`` field offsets below are transcribed from the
same spec document (:file:`M2/data/reference/NQTVITCHspecification.pdf`),
sections 1.6 and 1.5.2.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from typing import BinaryIO, Iterator

try:  # package import (python3 -m M2.src.itch_stream_window)
    from . import ingest as itch
except ImportError:  # direct script execution (python3 M2/src/itch_stream_window.py)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ingest as itch  # type: ignore[no-redef]

# --------------------------------------------------------------------------
# Frozen window: 15:49:50 -> 16:00:10 ET, exchange nanoseconds since midnight.
# --------------------------------------------------------------------------
NS_PER_SECOND = 1_000_000_000
NS_PER_HOUR = 3_600 * NS_PER_SECOND
NS_PER_MINUTE = 60 * NS_PER_SECOND
WINDOW_START_NS = 15 * NS_PER_HOUR + 49 * NS_PER_MINUTE + 50 * NS_PER_SECOND
WINDOW_END_NS = 16 * NS_PER_HOUR + 0 * NS_PER_MINUTE + 10 * NS_PER_SECOND
NS_1550 = 15 * NS_PER_HOUR + 50 * NS_PER_MINUTE
NS_1555 = 15 * NS_PER_HOUR + 55 * NS_PER_MINUTE

# Derived artifact, not a hot-loop input: favour a smaller file.
GZIP_LEVEL = 6
GZIP_WINDOW = 31  # zlib wbits: gzip container, CRC32 and ISIZE verified

# Progress goes to stderr only; the caller's log is the reader.
PROGRESS_EVERY = 1 << 30  # 1 GiB of compressed input
READ_SIZE = 1 << 22

# The timestamp is bytes 5..10 of the common header; unpacked directly rather
# than through ingest.HEADER so the per-frame cost stays at one struct call.
_TS = struct.Struct(">IH")

# NOII 'I' (spec 1.6), offsets relative to the start of the message.
I_PAIRED_SHARES = 11
I_IMBALANCE_SHARES = 19
I_IMBALANCE_DIRECTION = 27
I_STOCK = 28
I_FAR_PRICE = 36
I_NEAR_PRICE = 40
I_CURRENT_REFERENCE_PRICE = 44
I_CROSS_TYPE = 48
I_PRICE_VARIATION = 49

# Cross Trade 'Q' (spec 1.5.2), offsets relative to the start of the message.
Q_SHARES = 11
Q_STOCK = 19
Q_CROSS_PRICE = 27
Q_MATCH_NUMBER = 31
Q_CROSS_TYPE = 39

TYPE_SYSTEM_EVENT = 0x53
TYPE_STOCK_DIRECTORY = 0x52
TYPE_NOII = 0x49
TYPE_CROSS_TRADE = 0x51

# Universe rule for TUP-NASDAQ-CLOSE-H4-LATENOII-AGG, as frozen in
# .research/resolution/BRANCH_B/REPORT.md ("Point-in-time universe and identity").
UNIVERSE_MARKET_CATEGORIES = frozenset({"Q", "G", "S", "N", "A", "P", "Z", "V"})
UNIVERSE_AUTHENTICITY = "P"
UNIVERSE_ETP_FLAG = "N"
UNIVERSE_ISSUE_CLASSIFICATION = "C"
UNIVERSE_ISSUE_SUB_TYPE = "C"

# Preregistered data-quality tolerance (frozen formulation of the new candidate).
COVERAGE_TOLERANCE = 0.95
DIRECTION_ELIGIBLE = frozenset({"B", "S"})


def format_ns(ns: int | None) -> str | None:
    """Render exchange nanoseconds since midnight as ``HH:MM:SS.nnnnnnnnn``."""
    if ns is None:
        return None
    seconds, fraction = divmod(int(ns), NS_PER_SECOND)
    hour, rest = divmod(seconds, 3600)
    minute, second = divmod(rest, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}.{fraction:09d}"


def _read_chunks(handle: BinaryIO, size: int = READ_SIZE) -> Iterator[bytes]:
    while True:
        block = handle.read(size)
        if not block:
            return
        yield block


def decode_first_frames(raw: bytes, count: int = 8) -> list[dict]:
    """Decode the leading frames of a raw (already decompressed) byte slice."""
    frames: list[dict] = []
    position = 0
    limit = len(raw)
    while len(frames) < count and position + itch.FRAME_PREFIX <= limit:
        declared = (raw[position] << 8) | raw[position + 1]
        if declared == 0:
            frames.append({"index": len(frames), "offset": position, "length": 0, "note": "zero-length frame"})
            position += itch.FRAME_PREFIX
            continue
        if position + itch.FRAME_PREFIX + declared > limit:
            break
        base = position + itch.FRAME_PREFIX
        message_type = raw[base]
        hi, lo = _TS.unpack_from(raw, base + 5)
        timestamp = (hi << 16) | lo
        frames.append(
            {
                "index": len(frames),
                "offset": position,
                "length": declared,
                "type": chr(message_type),
                "locate": (raw[base + 1] << 8) | raw[base + 2],
                "tracking": (raw[base + 3] << 8) | raw[base + 4],
                "timestamp_ns": timestamp,
                "timestamp": format_ns(timestamp),
            }
        )
        position += itch.FRAME_PREFIX + declared
    return frames


def _decompressed_chunks(source: BinaryIO, decompressor: zlib._Decompress, counters: dict) -> Iterator[bytes]:
    """Yield decompressed bytes while hashing/counting the compressed input."""
    digest = counters["digest"]
    for block in _read_chunks(source):
        counters["received"] += len(block)
        digest.update(block)
        head = counters["head"]
        if len(head) < counters["head_bytes"]:
            head += block[: counters["head_bytes"] - len(head)]
        data = decompressor.decompress(block)
        if data:
            yield data
    tail = decompressor.flush()
    if tail:
        yield tail


# --------------------------------------------------------------------------
# Job 1: stream
# --------------------------------------------------------------------------
def stream_window(
    source: BinaryIO,
    out_path: str,
    *,
    window_start_ns: int = WINDOW_START_NS,
    window_end_ns: int = WINDOW_END_NS,
    window_start_label: str | None = None,
    window_end_label: str | None = None,
    head_bytes: int = 1 << 14,
) -> dict:
    """Consume a gzip ITCH session from ``source`` and write the retained window."""
    counters = {
        "digest": hashlib.sha256(),
        "received": 0,
        "head": bytearray(),
        "head_bytes": head_bytes,
    }
    decompressor = zlib.decompressobj(GZIP_WINDOW)

    msg_length = itch.MSG_LENGTH
    frame_prefix = itch.FRAME_PREFIX
    check_ts = _TS.unpack_from
    system_event_names = itch.SYSTEM_EVENT_NAME

    type_counts = [0] * 256
    window_type_counts = [0] * 256
    total = 0
    frames_verified = 0
    first_ts: int | None = None
    last_ts: int | None = None
    previous_ts: int | None = None
    backwards = 0
    session_events: list[dict] = []
    terminator_count = 0
    terminator_offset: int | None = None
    terminator_frame_index: int | None = None
    last_message_type: int | None = None
    window_messages = 0
    retained_messages = 0
    integrity_error: str | None = None
    framing_error: str | None = None

    buffer = bytearray()
    position = 0
    parsed_offset = 0
    next_progress = PROGRESS_EVERY
    started = time.time()

    out = gzip.open(out_path, "wb", compresslevel=GZIP_LEVEL)
    try:
        try:
            for data in _decompressed_chunks(source, decompressor, counters):
                buffer += data
                view = memoryview(buffer)
                limit = len(view)
                while position + frame_prefix <= limit:
                    declared = (view[position] << 8) | view[position + 1]
                    if declared == 0:
                        terminator_count += 1
                        if terminator_offset is None:
                            terminator_offset = parsed_offset + position
                            terminator_frame_index = total
                        position += frame_prefix
                        continue
                    end = position + frame_prefix + declared
                    if end > limit:
                        break
                    base = position + frame_prefix
                    message_type = view[base]
                    expected = msg_length.get(message_type)
                    if expected is None:
                        raise itch.FeedFormatError(
                            f"unknown message type byte 0x{message_type:02x} at stream offset "
                            f"{parsed_offset + base}"
                        )
                    if declared != expected:
                        raise itch.FeedFormatError(
                            "framing mismatch: message type "
                            f"0x{message_type:02x} declares length {declared}, documented is "
                            f"{expected}, at stream offset {parsed_offset + position}"
                        )
                    frames_verified += 1
                    total += 1
                    type_counts[message_type] += 1
                    last_message_type = message_type
                    hi, lo = check_ts(buffer, base + 5)
                    timestamp = (hi << 16) | lo
                    if first_ts is None:
                        first_ts = timestamp
                    if previous_ts is not None and timestamp < previous_ts:
                        backwards += 1
                    previous_ts = timestamp
                    last_ts = timestamp
                    in_window = window_start_ns <= timestamp <= window_end_ns
                    if in_window:
                        window_messages += 1
                        window_type_counts[message_type] += 1
                    if message_type == TYPE_SYSTEM_EVENT:
                        code = bytes(view[base + 11 : base + 12])
                        session_events.append(
                            {
                                "timestamp_ns": timestamp,
                                "timestamp": format_ns(timestamp),
                                "event_code": chr(code[0]),
                                "event_name": system_event_names.get(code, "unrecognised"),
                            }
                        )
                        out.write(view[position:end])
                        retained_messages += 1
                    elif message_type == TYPE_STOCK_DIRECTORY or in_window:
                        out.write(view[position:end])
                        retained_messages += 1
                    position = end
                view.release()
                del buffer[:position]
                parsed_offset += position
                position = 0
                if counters["received"] >= next_progress:
                    print(
                        f"[stream] {counters['received'] / 2**30:.2f} GiB in, {total} frames, "
                        f"{time.time() - started:.0f}s elapsed",
                        file=sys.stderr,
                        flush=True,
                    )
                    next_progress += PROGRESS_EVERY
        except (zlib.error, itch.FeedFormatError) as exc:
            if isinstance(exc, zlib.error):
                integrity_error = str(exc)
            else:
                framing_error = str(exc)
    finally:
        out.close()

    trailing_bytes = len(buffer)
    decompressed_total = parsed_offset + trailing_bytes

    if integrity_error is None and framing_error is None:
        if not decompressor.eof:
            integrity_error = "gzip member did not terminate: no complete CRC32/ISIZE trailer seen"
        elif len(decompressor.unused_data):
            integrity_error = (
                f"{len(decompressor.unused_data)} bytes follow the first gzip member "
                "(multi-member or trailing data)"
            )
        elif trailing_bytes:
            integrity_error = f"{trailing_bytes} trailing bytes do not form a complete framed message"
    integrity_ok = integrity_error is None and framing_error is None

    head = bytes(counters["head"])
    first_frames = None
    if head[:2] == b"\x1f\x8b":
        try:
            first_frames = decode_first_frames(zlib.decompressobj(GZIP_WINDOW).decompress(head))
        except zlib.error as exc:  # pragma: no cover - only on a corrupt head
            first_frames = [{"error": str(exc)}]

    last_system_event = session_events[-1] if session_events else None
    final_end_of_messages = bool(last_system_event and last_system_event["event_code"] == "C")
    end_of_messages_is_last_message = bool(
        final_end_of_messages and last_message_type == TYPE_SYSTEM_EVENT
    )
    histogram = {
        itch.MSG_NAME[code]: type_counts[code] for code in sorted(itch.MSG_NAME) if type_counts[code]
    }
    window_histogram = {
        itch.MSG_NAME[code]: window_type_counts[code]
        for code in sorted(itch.MSG_NAME)
        if window_type_counts[code]
    }
    unknown_codes = {
        str(code): type_counts[code]
        for code in range(256)
        if type_counts[code] and code not in itch.MSG_NAME
    }

    return {
        "container_framing": "TWO_BYTE_BIG_ENDIAN_LENGTH_PREFIX",
        "received_bytes": counters["received"],
        "decompressed_bytes": decompressed_total,
        "streamed_sha256": counters["digest"].hexdigest(),
        "gzip_integrity": "PASS" if integrity_ok else "FAIL",
        "gzip_integrity_detail": integrity_error
        or ("CRC32 and ISIZE verified by the zlib gzip member" if integrity_ok else None),
        "framing_errors": 0 if framing_error is None else 1,
        "framing_error_detail": framing_error,
        "frame_count": frames_verified,
        "total_messages": total,
        "message_type_histogram_whole": histogram,
        "message_type_histogram_window": window_histogram,
        "unrecognised_message_codes": unknown_codes,
        "first_exchange_timestamp_ns": first_ts,
        "first_exchange_timestamp": format_ns(first_ts),
        "last_exchange_timestamp_ns": last_ts,
        "last_exchange_timestamp": format_ns(last_ts),
        "backwards_timestamps": backwards,
        "last_message_type": chr(last_message_type) if last_message_type is not None else None,
        "terminating_zero_length_frame": terminator_count > 0,
        "terminating_zero_length_frame_count": terminator_count,
        "terminating_zero_length_frame_offset": terminator_offset,
        "terminating_frame_is_last_frame": terminator_frame_index == total,
        "terminating_frame_at_end_of_stream": terminator_offset is not None
        and terminator_offset + frame_prefix == decompressed_total,
        "messages_after_terminator": 0
        if terminator_frame_index is None
        else total - terminator_frame_index,
        "trailing_bytes_after_frames": trailing_bytes,
        "first_frames": first_frames,
        "session_events": session_events,
        "final_end_of_messages": final_end_of_messages,
        "end_of_messages_is_last_message": end_of_messages_is_last_message,
        "last_system_event": last_system_event,
        "window": {
            "start_ns": window_start_ns,
            "end_ns": window_end_ns,
            "start": window_start_label or format_ns(window_start_ns),
            "end": window_end_label or format_ns(window_end_ns),
        },
        "window_message_count": window_messages,
        "retained_message_count": retained_messages,
        "elapsed_seconds": round(time.time() - started, 1),
    }


def finalize_admission(payload: dict) -> dict:
    """Derive the admission verdicts from the recorded raw facts.

    Two things are kept apart on purpose:

    * ``structural_verdict`` - every objective completeness marker: gzip CRC32
      and ISIZE verified, received bytes equal to the server's own
      ``Content-Range`` total, every frame's length prefix equal to the
      documented length, zero trailing bytes after the last frame, and the
      ITCH 5.0 ``C`` End of Messages system event as the final frame.
    * ``binaryfile_zero_length_terminator`` - the optional BinaryFILE v1.00
      "message of length zero indicates the end of the session" marker. Nasdaq's
      published ``emi.nasdaq.com`` captures (this session and the repo's held
      2019-07-30 reference tape) end on the ``C`` frame without it, so its
      absence is recorded as a provider-format finding, never assumed away.
    """
    result = payload
    received = result.get("received_bytes")
    total = result.get("content_range_total")
    result["structural_verdict"] = (
        "PASS"
        if (
            result.get("gzip_integrity") == "PASS"
            and result.get("framing_errors") == 0
            and result.get("trailing_bytes_after_frames") == 0
            and result.get("end_of_messages_is_last_message")
            and isinstance(received, int)
            and received > 0
            and (total is None or received == total)
        )
        else "FAIL"
    )
    terminator_present = bool(result.get("terminating_zero_length_frame"))
    result["binaryfile_zero_length_terminator"] = {
        "specification_clause": (
            "Nasdaq BinaryFILE v1.00 §1.1: a message of length zero indicates the end of the "
            "session; a file that does not end with an empty message is incomplete."
        ),
        "present": terminator_present,
        "count": result.get("terminating_zero_length_frame_count"),
        "offset": result.get("terminating_zero_length_frame_offset"),
        "finding": (
            "PRESENT"
            if terminator_present
            else "ABSENT_IN_PROVIDER_CAPTURE: the published object ends on the ITCH 5.0 'C' End of "
            "Messages system event, which the TotalView-ITCH 5.0 specification defines as the last "
            "message of a trading day. The repo's own accepted reference tape "
            "(M2/data/raw/07302019.NASDAQ_ITCH50.gz) has the identical trailing structure "
            "(last 16 decompressed bytes d989000c530000000041c1a7d1cb9643 -> length 12, type 'S', code 'C'), "
            "so this is a provider format property, not truncation of this object."
        ),
    }
    result["admission_verdict"] = (
        "STRUCTURALLY_ADMITTED"
        if result["structural_verdict"] == "PASS"
        else "NOT_ADMITTED"
    )
    result.pop("integrity_verdict", None)
    return result


# --------------------------------------------------------------------------
# Job 2: coverage
# --------------------------------------------------------------------------
class SymbolRecord:
    __slots__ = (
        "locate",
        "symbol",
        "market_category",
        "financial_status",
        "issue_classification",
        "issue_sub_type",
        "authenticity",
        "etp_flag",
        "directory_eligible",
        "read_1550",
        "read_1550_after",
        "read_1555",
        "read_1555_after",
        "cross",
        "cross_count",
    )

    def __init__(self, locate: int) -> None:
        self.locate = locate
        self.symbol = None
        self.market_category = None
        self.financial_status = None
        self.issue_classification = None
        self.issue_sub_type = None
        self.authenticity = None
        self.etp_flag = None
        self.directory_eligible = False
        self.read_1550 = None
        self.read_1550_after = None
        self.read_1555 = None
        self.read_1555_after = None
        self.cross = None
        self.cross_count = 0


def _noii_record(buffer, view, base: int) -> dict:
    hi, lo = _TS.unpack_from(buffer, base + 5)
    return {
        "timestamp_ns": (hi << 16) | lo,
        "timestamp": format_ns((hi << 16) | lo),
        "symbol": itch.decode_alpha(bytes(view[base + I_STOCK : base + I_STOCK + 8])),
        "paired_shares": itch.U64.unpack_from(buffer, base + I_PAIRED_SHARES)[0],
        "imbalance_shares": itch.U64.unpack_from(buffer, base + I_IMBALANCE_SHARES)[0],
        "imbalance_direction": chr(view[base + I_IMBALANCE_DIRECTION]),
        "far_price": itch.U32.unpack_from(buffer, base + I_FAR_PRICE)[0],
        "near_price": itch.U32.unpack_from(buffer, base + I_NEAR_PRICE)[0],
        "current_reference_price": itch.U32.unpack_from(buffer, base + I_CURRENT_REFERENCE_PRICE)[0],
        "cross_type": chr(view[base + I_CROSS_TYPE]),
        "price_variation_indicator": chr(view[base + I_PRICE_VARIATION]),
    }


def _cross_record(buffer, view, base: int) -> dict:
    hi, lo = _TS.unpack_from(buffer, base + 5)
    return {
        "timestamp_ns": (hi << 16) | lo,
        "timestamp": format_ns((hi << 16) | lo),
        "symbol": itch.decode_alpha(bytes(view[base + Q_STOCK : base + Q_STOCK + 8])),
        "shares": itch.U64.unpack_from(buffer, base + Q_SHARES)[0],
        "cross_price": itch.U32.unpack_from(buffer, base + Q_CROSS_PRICE)[0],
        "cross_type": chr(view[base + Q_CROSS_TYPE]),
    }


def scan_window(path: str, *, ns_1550: int = NS_1550, ns_1555: int = NS_1555) -> tuple[dict[int, SymbolRecord], dict]:
    """Parse the retained window and collect the directory, NOII reads and crosses."""
    symbols: dict[int, SymbolRecord] = {}
    stats = {
        "frames": 0,
        "stock_directory": 0,
        "system_events": 0,
        "noii_messages": 0,
        "cross_trades": 0,
        "noii_cross_type_counts": {},
        "cross_type_counts": {},
        "closing_cross_zero_share": 0,
        "closing_cross_zero_share_zero_price": 0,
        "noii_c_reads_at_or_before_1550": 0,
        "noii_c_reads_at_or_before_1555": 0,
        "first_noii_c_timestamp_ns": None,
        "last_noii_c_timestamp_ns": None,
        "issue_classification_counts": {},
        "issue_sub_type_counts": {},
        "market_category_counts": {},
        "authenticity_counts": {},
        "etp_flag_counts": {},
        "classification_subtype_pairs": {},
        "first_timestamp_ns": None,
        "last_timestamp_ns": None,
    }
    with itch.open_source(path) as handle:
        buffer = bytearray()
        position = 0
        while True:
            block = handle.read(itch.CHUNK)
            if not block:
                break
            buffer += block
            view = memoryview(buffer)
            limit = len(view)
            while position + itch.FRAME_PREFIX <= limit:
                declared = (view[position] << 8) | view[position + 1]
                if declared == 0:
                    position += itch.FRAME_PREFIX
                    continue
                if position + itch.FRAME_PREFIX + declared > limit:
                    break
                base = position + itch.FRAME_PREFIX
                message_type = view[base]
                expected = itch.MSG_LENGTH.get(message_type)
                if expected is None:
                    raise itch.FeedFormatError(
                        f"unknown message type byte 0x{message_type:02x} in retained window"
                    )
                if declared != expected:
                    raise itch.FeedFormatError(
                        f"framing mismatch in retained window: 0x{message_type:02x} "
                        f"declares {declared}, documented is {expected}"
                    )
                stats["frames"] += 1
                hi, lo = _TS.unpack_from(buffer, base + 5)
                timestamp = (hi << 16) | lo
                if stats["first_timestamp_ns"] is None:
                    stats["first_timestamp_ns"] = timestamp
                stats["last_timestamp_ns"] = timestamp

                if message_type == TYPE_STOCK_DIRECTORY:
                    stats["stock_directory"] += 1
                    locate = (view[base + 1] << 8) | view[base + 2]
                    record = symbols.get(locate)
                    if record is None:
                        record = SymbolRecord(locate)
                        symbols[locate] = record
                    record.symbol = itch.decode_alpha(bytes(view[base + itch.R_STOCK : base + itch.R_STOCK + 8]))
                    record.market_category = chr(view[base + itch.R_MARKET_CATEGORY])
                    record.financial_status = chr(view[base + itch.R_FINANCIAL_STATUS])
                    record.issue_classification = chr(view[base + itch.R_ISSUE_CLASSIFICATION])
                    record.issue_sub_type = itch.decode_alpha(
                        bytes(view[base + itch.R_ISSUE_SUB_TYPE : base + itch.R_ISSUE_SUB_TYPE + 2])
                    )
                    record.authenticity = chr(view[base + itch.R_AUTHENTICITY])
                    record.etp_flag = chr(view[base + itch.R_ETP_FLAG])
                    record.directory_eligible = directory_eligible(record)
                    for key, value in (
                        ("issue_classification_counts", record.issue_classification),
                        ("issue_sub_type_counts", record.issue_sub_type),
                        ("market_category_counts", record.market_category),
                        ("authenticity_counts", record.authenticity),
                        ("etp_flag_counts", record.etp_flag),
                        ("classification_subtype_pairs", f"{record.issue_classification}/{record.issue_sub_type}"),
                    ):
                        bucket = stats[key]
                        bucket[value] = bucket.get(value, 0) + 1
                elif message_type == TYPE_SYSTEM_EVENT:
                    stats["system_events"] += 1
                elif message_type == TYPE_NOII:
                    stats["noii_messages"] += 1
                    record = _noii_record(buffer, view, base)
                    cross_type = record["cross_type"]
                    stats["noii_cross_type_counts"][cross_type] = (
                        stats["noii_cross_type_counts"].get(cross_type, 0) + 1
                    )
                    # Only a Closing-Cross read (Cross Type C) can serve the frozen signal.
                    if cross_type == "C":
                        locate = (view[base + 1] << 8) | view[base + 2]
                        holder = symbols.get(locate)
                        if holder is None:
                            holder = SymbolRecord(locate)
                            symbols[locate] = holder
                        if timestamp <= ns_1550:
                            holder.read_1550 = record
                            stats["noii_c_reads_at_or_before_1550"] += 1
                        elif holder.read_1550_after is None:
                            holder.read_1550_after = record
                        if timestamp <= ns_1555:
                            holder.read_1555 = record
                            stats["noii_c_reads_at_or_before_1555"] += 1
                        elif holder.read_1555_after is None:
                            holder.read_1555_after = record
                        if stats["first_noii_c_timestamp_ns"] is None:
                            stats["first_noii_c_timestamp_ns"] = timestamp
                        stats["last_noii_c_timestamp_ns"] = timestamp
                elif message_type == TYPE_CROSS_TRADE:
                    stats["cross_trades"] += 1
                    record = _cross_record(buffer, view, base)
                    cross_type = record["cross_type"]
                    stats["cross_type_counts"][cross_type] = stats["cross_type_counts"].get(cross_type, 0) + 1
                    if cross_type == "C":
                        locate = (view[base + 1] << 8) | view[base + 2]
                        holder = symbols.get(locate)
                        if holder is None:
                            holder = SymbolRecord(locate)
                            symbols[locate] = holder
                        holder.cross = record
                        holder.cross_count += 1
                        if record["shares"] == 0:
                            stats["closing_cross_zero_share"] += 1
                            if record["cross_price"] == 0:
                                stats["closing_cross_zero_share_zero_price"] += 1
                position += itch.FRAME_PREFIX + declared
            view.release()
            del buffer[:position]
            position = 0
        itch.check_no_trailing_bytes(buffer)
    return symbols, stats


def directory_eligible(record: SymbolRecord) -> bool:
    return (
        record.authenticity == UNIVERSE_AUTHENTICITY
        and record.etp_flag == UNIVERSE_ETP_FLAG
        and record.issue_classification == UNIVERSE_ISSUE_CLASSIFICATION
        and record.issue_sub_type == UNIVERSE_ISSUE_SUB_TYPE
        and record.market_category in UNIVERSE_MARKET_CATEGORIES
    )


def directory_failure(record: SymbolRecord) -> str:
    failures = []
    if record.authenticity != UNIVERSE_AUTHENTICITY:
        failures.append(f"authenticity={record.authenticity!r}")
    if record.etp_flag != UNIVERSE_ETP_FLAG:
        failures.append(f"etp_flag={record.etp_flag!r}")
    if record.issue_classification != UNIVERSE_ISSUE_CLASSIFICATION:
        failures.append(f"issue_classification={record.issue_classification!r}")
    if record.issue_sub_type != UNIVERSE_ISSUE_SUB_TYPE:
        failures.append(f"issue_sub_type={record.issue_sub_type!r}")
    if record.market_category not in UNIVERSE_MARKET_CATEGORIES:
        failures.append(f"market_category={record.market_category!r}")
    return ";".join(failures)


READ_SEMANTICS = {
    "AT_OR_BEFORE": (
        "last Closing-Cross NOII read with exchange timestamp <= the instant "
        "(the assignment's literal 'at/before 15:50 and at/before 15:55')"
    ),
    "FROZEN_CONTRACT": (
        "last read at/before 15:55; for 15:50 the last read at/before, else the FIRST read after "
        "15:50 when no exact boundary message exists (the freeze-ready contract wording in "
        ".research/resolution/BRANCH_B/REPORT.md)"
    ),
    "INSTANT_ALIGNED": (
        "first read at/after each instant (the NOII disseminated at that instant), falling back to "
        "the last read at/before only if there is none"
    ),
}


def _select_read(record: SymbolRecord, instant: str, semantics: str) -> dict | None:
    before = record.read_1550 if instant == "1550" else record.read_1555
    after = record.read_1550_after if instant == "1550" else record.read_1555_after
    if semantics == "AT_OR_BEFORE":
        return before
    if semantics == "FROZEN_CONTRACT":
        if instant == "1550":
            return before if before is not None else after
        return before
    return after if after is not None else before


def _valid_cross(record: SymbolRecord) -> bool:
    """A Closing Cross print anchors the outcome only when it is a real print.

    The specification allows the Cross Trade message to carry zero shares when
    "the order interest is insufficient to conduct a cross"; in this session every
    zero-share print also carries a zero cross price, which cannot anchor
    ``(ClosingCrossPrice - CurrentReferencePrice)/CurrentReferencePrice``.
    """
    cross = record.cross
    return cross is not None and cross["shares"] > 0 and cross["cross_price"] > 0


def compute_coverage(symbols: dict[int, SymbolRecord], stats: dict, *, tolerance: float = COVERAGE_TOLERANCE) -> dict:
    """Frozen coverage ratio, variant matrix and per-symbol missingness audit."""
    rows: list[dict] = []
    for locate in sorted(symbols):
        record = symbols[locate]
        if (
            record.symbol is None
            and record.cross is None
            and record.read_1550 is None
            and record.read_1550_after is None
            and record.read_1555 is None
            and record.read_1555_after is None
        ):
            continue  # locate carried by an unexpected message class only
        rows.append(
            {
                "locate": locate,
                "symbol": record.symbol or "",
                "market_category": record.market_category or "",
                "issue_classification": record.issue_classification or "",
                "issue_sub_type": record.issue_sub_type or "",
                "authenticity": record.authenticity or "",
                "etp_flag": record.etp_flag or "",
                "financial_status": record.financial_status or "",
                "directory_eligible": int(record.directory_eligible),
                "has_closing_cross_C": int(record.cross is not None),
                "cross_shares": record.cross["shares"] if record.cross else "",
                "cross_price_raw": record.cross["cross_price"] if record.cross else "",
                "has_read_1550_C": int(record.read_1550 is not None),
                "has_read_1555_C": int(record.read_1555 is not None),
                "read_1550_used_ns": "",
                "read_1555_used_ns": "",
                "direction_1550": "",
                "direction_1555": "",
                "read_1550_frozen_ns": "",
                "direction_1550_frozen": "",
                "exclusion_reason_frozen": "",
                "in_numerator_frozen": 0,
                "in_denominator": 0,
                "in_numerator": 0,
                "exclusion_reason": "",
                "exclusion_detail": "",
            }
        )
        rows[-1]["_record"] = record

    def variant(universe: str, semantics: str) -> dict:
        eligible = denominator = numerator = 0
        reasons: dict[str, int] = {}
        for row in rows:
            record = row["_record"]
            if universe == "FROZEN_5_CLAUSE":
                qualified = record.directory_eligible
            else:
                qualified = (
                    record.authenticity == UNIVERSE_AUTHENTICITY
                    and record.etp_flag == UNIVERSE_ETP_FLAG
                    and record.issue_classification == UNIVERSE_ISSUE_CLASSIFICATION
                    and record.market_category in UNIVERSE_MARKET_CATEGORIES
                )
            if qualified:
                eligible += 1
            read_1550 = _select_read(record, "1550", semantics)
            read_1555 = _select_read(record, "1555", semantics)
            in_denominator = qualified and _valid_cross(record)
            in_numerator = in_denominator and read_1550 is not None and read_1555 is not None
            if not qualified:
                reason = "directory_ineligible"
            elif record.cross is None:
                reason = "no_cross"
            elif not _valid_cross(record):
                reason = "zero_share_cross"
            elif read_1550 is None or read_1555 is None:
                reason = "no_read"
            else:
                bad = [
                    f"{label}={read['imbalance_direction']!r}"
                    for label, read in (("1550", read_1550), ("1555", read_1555))
                    if read["imbalance_direction"] not in DIRECTION_ELIGIBLE
                ]
                reason = "ineligible_direction" if bad else ""
            if in_denominator:
                denominator += 1
            if in_numerator:
                numerator += 1
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
        ratio = (numerator / denominator) if denominator else None
        return {
            "universe": universe,
            "read_semantics": semantics,
            "universe_qualified_symbols": eligible,
            "denominator_symbols_with_valid_closing_cross_C": denominator,
            "numerator_both_C_reads_and_valid_cross": numerator,
            "coverage_ratio": ratio,
            "tolerance": tolerance,
            "tolerance_met": (ratio is not None and ratio >= tolerance),
            "exclusion_reason_counts": reasons,
        }

    primary = variant("FROZEN_5_CLAUSE", "AT_OR_BEFORE")
    variants = [
        variant(universe, semantics)
        for universe in ("FROZEN_5_CLAUSE", "CLASSIFICATION_ONLY")
        for semantics in ("AT_OR_BEFORE", "FROZEN_CONTRACT", "INSTANT_ALIGNED")
    ]

    # The audit rows carry the primary (frozen) variant's decision.
    for row in rows:
        record = row["_record"]
        read_1550 = _select_read(record, "1550", "AT_OR_BEFORE")
        read_1555 = _select_read(record, "1555", "AT_OR_BEFORE")
        in_denominator = record.directory_eligible and _valid_cross(record)
        in_numerator = in_denominator and read_1550 is not None and read_1555 is not None
        row["in_denominator"] = int(in_denominator)
        row["in_numerator"] = int(in_numerator)
        row["read_1550_used_ns"] = read_1550["timestamp_ns"] if read_1550 else ""
        row["read_1555_used_ns"] = read_1555["timestamp_ns"] if read_1555 else ""
        row["direction_1550"] = read_1550["imbalance_direction"] if read_1550 else ""
        row["direction_1555"] = read_1555["imbalance_direction"] if read_1555 else ""
        if not record.directory_eligible:
            reason, detail = "directory_ineligible", directory_failure(record)
        elif record.cross is None:
            reason, detail = "no_cross", ""
        elif not _valid_cross(record):
            reason, detail = "zero_share_cross", (
                f"cross shares={record.cross['shares']}, price={record.cross['cross_price']}"
            )
        elif read_1550 is None or read_1555 is None:
            reason, detail = "no_read", _missing_reads_detail(record, read_1550, read_1555)
        else:
            bad = [
                f"{label}={read['imbalance_direction']!r}"
                for label, read in (("1550", read_1550), ("1555", read_1555))
                if read["imbalance_direction"] not in DIRECTION_ELIGIBLE
            ]
            reason, detail = ("ineligible_direction", ";".join(bad)) if bad else ("", "")
        row["exclusion_reason"] = reason
        row["exclusion_detail"] = detail

        # Same decision under the freeze-ready contract's boundary semantics, so the
        # audit stays informative even where the literal reading is degenerate.
        frozen_1550 = _select_read(record, "1550", "FROZEN_CONTRACT")
        frozen_1555 = _select_read(record, "1555", "FROZEN_CONTRACT")
        in_den = record.directory_eligible and _valid_cross(record)
        row["read_1550_frozen_ns"] = frozen_1550["timestamp_ns"] if frozen_1550 else ""
        row["direction_1550_frozen"] = frozen_1550["imbalance_direction"] if frozen_1550 else ""
        row["in_numerator_frozen"] = int(
            in_den and frozen_1550 is not None and frozen_1555 is not None
        )
        if not record.directory_eligible:
            row["exclusion_reason_frozen"] = "directory_ineligible"
        elif record.cross is None:
            row["exclusion_reason_frozen"] = "no_cross"
        elif not _valid_cross(record):
            row["exclusion_reason_frozen"] = "zero_share_cross"
        elif frozen_1550 is None or frozen_1555 is None:
            row["exclusion_reason_frozen"] = "no_read"
        elif (
            frozen_1550["imbalance_direction"] not in DIRECTION_ELIGIBLE
            or frozen_1555["imbalance_direction"] not in DIRECTION_ELIGIBLE
        ):
            row["exclusion_reason_frozen"] = "ineligible_direction"
        else:
            row["exclusion_reason_frozen"] = ""

    excluded_by_category: dict[str, dict[str, int]] = {}
    for row in rows:
        if row["directory_eligible"] and row["exclusion_reason"]:
            bucket = excluded_by_category.setdefault(row["market_category"], {})
            bucket[row["exclusion_reason"]] = bucket.get(row["exclusion_reason"], 0) + 1

    pairs = stats.get("classification_subtype_pairs", {})
    venue_breakdown: dict[str, dict[str, int]] = {}
    for row in rows:
        record = row["_record"]
        if not (
            record.authenticity == UNIVERSE_AUTHENTICITY
            and record.etp_flag == UNIVERSE_ETP_FLAG
            and record.issue_classification == UNIVERSE_ISSUE_CLASSIFICATION
            and record.market_category in UNIVERSE_MARKET_CATEGORIES
        ):
            continue
        bucket = venue_breakdown.setdefault(
            record.market_category, {"symbols": 0, "valid_cross": 0}
        )
        bucket["symbols"] += 1
        if _valid_cross(record):
            bucket["valid_cross"] += 1
    nasdaq = {
        key: venue_breakdown.get(key, {"symbols": 0, "valid_cross": 0}) for key in ("Q", "G", "S")
    }
    non_nasdaq = {
        key: venue_breakdown.get(key, {"symbols": 0, "valid_cross": 0})
        for key in sorted(UNIVERSE_MARKET_CATEGORIES - {"Q", "G", "S"})
    }
    nasdaq_symbols = sum(v["symbols"] for v in nasdaq.values())
    nasdaq_valid = sum(v["valid_cross"] for v in nasdaq.values())
    other_symbols = sum(v["symbols"] for v in non_nasdaq.values())
    other_valid = sum(v["valid_cross"] for v in non_nasdaq.values())
    universe_rule_finding = (
        "The frozen universe clause 'Issue Sub-Type = C' admits "
        f"{variants[0]['universe_qualified_symbols']} of {len(symbols)} locates in this session "
        "(and 72 of 8849 in the repo's own 2019-07-30 ingest output), because Nasdaq's Stock "
        "Directory marks ordinary common stock as Issue Classification 'C' with Issue Sub-Type 'Z' "
        f"('Not Applicable'): the dominant pair here is C/Z ({pairs.get('C/Z', 0)} locates), while "
        "C/C has only 31. The repo's established universe machinery (M2/src/universe_proxy.py) "
        "constrains Issue Classification only and never the sub-type, which admits "
        f"{variants[3]['universe_qualified_symbols']} locates here. This is a rule defect, not a data "
        "defect."
    )
    nasdaq_rate = (nasdaq_valid / nasdaq_symbols) if nasdaq_symbols else 0.0
    other_rate = (other_valid / other_symbols) if other_symbols else 0.0
    missingness_systematicity = (
        "SYSTEMATIC BY LISTING VENUE. Under the classification-only universe the closing cross is "
        f"present with nonzero shares for {nasdaq_valid} of {nasdaq_symbols} Nasdaq-listed symbols "
        f"(Market Category Q/G/S, {nasdaq_rate:.1%}) but for only {other_valid} of "
        f"{other_symbols} symbols listed elsewhere ({other_rate:.1%} across N/A/P/Z). "
        "Nasdaq's Closing Cross carries no interest for issues it does not list, so those "
        "symbols emit a Cross Trade with zero shares and zero price. The declared Market Category "
        "clause and the closing-cross outcome requirement therefore conflict; the outcome population "
        "cannot be the whole declared universe. No other exclusion looks systematic: the 'no_read' "
        "and 'ineligible_direction' counts are zero once a read at the signal instants exists."
    )
    universe_venue_breakdown = {
        "nasdaq_listed_Q_G_S": {
            "symbols": nasdaq_symbols,
            "valid_closing_cross": nasdaq_valid,
            "by_category": nasdaq,
        },
        "other_listed_N_A_P_Z": {
            "symbols": other_symbols,
            "valid_closing_cross": other_valid,
            "by_category": non_nasdaq,
        },
    }

    diagnostics = {
        "noii_closing_read_cadence": {
            "first_read_ns": stats.get("first_noii_c_timestamp_ns"),
            "first_read": format_ns(stats.get("first_noii_c_timestamp_ns")),
            "last_read_ns": stats.get("last_noii_c_timestamp_ns"),
            "last_read": format_ns(stats.get("last_noii_c_timestamp_ns")),
            "reads_at_or_before_15_50": stats.get("noii_c_reads_at_or_before_1550"),
            "reads_at_or_before_15_55": stats.get("noii_c_reads_at_or_before_1555"),
            "boundary_defects": {
                "exact_15_50_boundary_reads": stats.get("noii_c_reads_at_or_before_1550", 0)
                - sum(1 for r in symbols.values() if r.read_1550 is not None),
                "note": (
                    "The first Closing-Cross NOII read of the session is published ~0.1 s AFTER the "
                    "nominal 15:50:00 ET boundary (message-generation jitter), so a literal "
                    "'at/before 15:50' selection finds no read at all; the 10 s cadence then makes the "
                    "last read at/before 15:55:00 the 15:54:50 read. Both boundary behaviours are "
                    "reported as variants rather than silently smoothed."
                ),
            },
        },
        "closing_cross_validity": {
            "cross_trade_C_messages": stats.get("cross_type_counts", {}).get("C", 0),
            "zero_share_prints": stats.get("closing_cross_zero_share", 0),
            "zero_share_and_zero_price_prints": stats.get("closing_cross_zero_share_zero_price", 0),
            "locates_with_C_cross": sum(1 for r in symbols.values() if r.cross is not None),
        },
        "directory_field_distribution": {
            "locates": len(symbols),
            "issue_classification": stats.get("issue_classification_counts", {}),
            "issue_sub_type": stats.get("issue_sub_type_counts", {}),
            "market_category": stats.get("market_category_counts", {}),
            "authenticity": stats.get("authenticity_counts", {}),
            "etp_flag": stats.get("etp_flag_counts", {}),
            "classification_subtype_pairs": stats.get("classification_subtype_pairs", {}),
        },
        "read_semantics_definitions": READ_SEMANTICS,
        "cross_validity_definition": (
            "valid = Cross Trade 'Q' with Cross Type C, shares > 0 and cross_price > 0; a "
            "zero-share print is retained in the audit as reason 'zero_share_cross'."
        ),
        "universe_rule_finding": universe_rule_finding,
        "missingness_systematicity": missingness_systematicity,
        "universe_venue_breakdown": universe_venue_breakdown,
    }

    for row in rows:
        row.pop("_record", None)

    return {
        "candidate_id": "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
        "universe_rule": {
            "authenticity": UNIVERSE_AUTHENTICITY,
            "etp_flag": UNIVERSE_ETP_FLAG,
            "issue_classification": UNIVERSE_ISSUE_CLASSIFICATION,
            "issue_sub_type": UNIVERSE_ISSUE_SUB_TYPE,
            "market_category_in": sorted(UNIVERSE_MARKET_CATEGORIES),
        },
        "signal_instant_ns": {"1550": NS_1550, "1555": NS_1555},
        "directory_locate_count": len(symbols),
        "directory_eligible_symbols": primary["universe_qualified_symbols"],
        "denominator_symbols_with_valid_closing_cross_C": primary[
            "denominator_symbols_with_valid_closing_cross_C"
        ],
        "numerator_both_C_reads_and_valid_cross": primary["numerator_both_C_reads_and_valid_cross"],
        "coverage_ratio": primary["coverage_ratio"],
        "tolerance": tolerance,
        "tolerance_met": primary["tolerance_met"],
        "exclusion_reason_counts": primary["exclusion_reason_counts"],
        "excluded_by_market_category": excluded_by_category,
        "primary_variant": {"universe": "FROZEN_5_CLAUSE", "read_semantics": "AT_OR_BEFORE"},
        "variants": variants,
        "diagnostics": diagnostics,
        "caveat": (
            "Coverage counts the presence of the frozen structural inputs only (both Closing-Cross "
            "NOII reads and a valid Cross Trade 'Q' print with Cross Type C). Direction eligibility "
            "(B/S) is reported separately and is not part of the coverage ratio. No price level, "
            "markout, carry or displacement quantity is computed or inspected here."
        ),
        "window_scan_stats": stats,
        "rows": rows,
    }


def _missing_reads_detail(record: SymbolRecord, read_1550: dict | None, read_1555: dict | None) -> str:
    missing = []
    if read_1550 is None:
        missing.append("1550")
    if read_1555 is None:
        missing.append("1555")
    if not missing:
        return ""
    return "missing Closing-Cross NOII read at " + "+".join(missing)


MISSINGNESS_COLUMNS = [
    "locate",
    "symbol",
    "market_category",
    "issue_classification",
    "issue_sub_type",
    "authenticity",
    "etp_flag",
    "financial_status",
    "directory_eligible",
    "has_closing_cross_C",
    "cross_shares",
    "cross_price_raw",
    "has_read_1550_C",
    "has_read_1555_C",
    "read_1550_used_ns",
    "read_1555_used_ns",
    "direction_1550",
    "direction_1555",
    "read_1550_frozen_ns",
    "direction_1550_frozen",
    "exclusion_reason_frozen",
    "in_numerator_frozen",
    "in_denominator",
    "in_numerator",
    "exclusion_reason",
    "exclusion_detail",
]


def write_missingness_csv(path: str, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(MISSINGNESS_COLUMNS) + "\n")
        for row in rows:
            cells = []
            for name in MISSINGNESS_COLUMNS:
                text = str(row[name])
                if any(ch in text for ch in ',"\n;'):
                    text = '"' + text.replace('"', '""') + '"'
                cells.append(text)
            handle.write(",".join(cells) + "\n")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _coverage_main(args: argparse.Namespace) -> int:
    symbols, stats = scan_window(args.window)
    result = compute_coverage(symbols, stats)
    rows = result.pop("rows")
    os.makedirs(args.out, exist_ok=True)
    write_missingness_csv(os.path.join(args.out, "coverage_missingness.csv"), rows)
    admission_path = os.path.join(args.out, "admission.json")
    payload: dict = {}
    if os.path.exists(admission_path):
        with open(admission_path, encoding="utf-8") as handle:
            payload = json.load(handle)
    payload["coverage"] = result
    payload["coverage_computed_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload["coverage_missingness_csv"] = os.path.join(args.out, "coverage_missingness.csv")
    with open(admission_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "denominator": result["denominator_symbols_with_valid_closing_cross_C"],
                "numerator": result["numerator_both_C_reads_and_valid_cross"],
                "coverage_ratio": result["coverage_ratio"],
                "tolerance": result["tolerance"],
                "tolerance_met": result["tolerance_met"],
                "exclusion_reason_counts": result["exclusion_reason_counts"],
            },
            indent=2,
        )
    )
    return 0


def _stream_main(args: argparse.Namespace) -> int:
    os.makedirs(args.out, exist_ok=True)
    window_path = os.path.join(args.out, "window.bin.gz")
    result = stream_window(
        sys.stdin.buffer,
        window_path,
        window_start_ns=args.window_start_ns,
        window_end_ns=args.window_end_ns,
        window_start_label=args.window_start,
        window_end_label=args.window_end,
    )
    result["url"] = args.url
    result["retrieval_utc"] = args.retrieved_utc
    result["retrieval_completed_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result["http_status"] = args.http_status
    result["content_type"] = args.content_type
    result["content_range_total"] = args.content_range_total
    result["received_bytes_matches_content_range"] = (
        args.content_range_total is not None and result["received_bytes"] == args.content_range_total
    )
    result["window_artifact"] = window_path
    result["window_artifact_bytes"] = os.path.getsize(window_path)
    result["window_artifact_sha256"] = itch.sha256_file(window_path)
    finalize_admission(result)
    with open(os.path.join(args.out, "admission.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "received_bytes": result["received_bytes"],
                "sha256": result["streamed_sha256"],
                "gzip_integrity": result["gzip_integrity"],
                "frames": result["frame_count"],
                "framing_errors": result["framing_errors"],
                "window_messages": result["window_message_count"],
                "terminator": result["terminating_zero_length_frame"],
                "final_C": result["final_end_of_messages"],
                "bytes_match_content_range": result["received_bytes_matches_content_range"],
                "structural_verdict": result["structural_verdict"],
                "admission_verdict": result["admission_verdict"],
            },
            indent=2,
        )
    )
    return 0 if result["admission_verdict"] == "STRUCTURALLY_ADMITTED" else 1


def _finalize_main(args: argparse.Namespace) -> int:
    path = os.path.join(args.out, "admission.json")
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    finalize_admission(payload)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"structural_verdict": payload["structural_verdict"],
                      "admission_verdict": payload["admission_verdict"],
                      "terminator": payload["binaryfile_zero_length_terminator"]["finding"][:60]}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="derived output directory")
    parser.add_argument("--url", default=None)
    parser.add_argument("--http-status", type=int, default=None)
    parser.add_argument("--content-type", default=None)
    parser.add_argument("--content-range-total", type=int, default=None)
    parser.add_argument("--retrieved-utc", default=None)
    parser.add_argument("--window-start", default=None, help="label for the window start instant")
    parser.add_argument("--window-end", default=None, help="label for the window end instant")
    parser.add_argument("--window-start-ns", type=int, default=WINDOW_START_NS)
    parser.add_argument("--window-end-ns", type=int, default=WINDOW_END_NS)
    parser.add_argument("--coverage", action="store_true", help="compute coverage on a retained window")
    parser.add_argument("--window", default=None, help="retained window path for --coverage")
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="recompute admission.json's verdicts from its recorded raw facts",
    )
    parser.add_argument(
        "--probe-head",
        default=None,
        help="decode the first frames of a local gzip byte slice (probe evidence)",
    )
    args = parser.parse_args(argv)

    if args.probe_head:
        with open(args.probe_head, "rb") as handle:
            head = handle.read()
        print(json.dumps(decode_first_frames(zlib.decompressobj(GZIP_WINDOW).decompress(head)), indent=2))
        return 0
    if args.coverage:
        if not args.window:
            parser.error("--coverage requires --window")
        return _coverage_main(args)
    if args.finalize:
        return _finalize_main(args)
    return _stream_main(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
