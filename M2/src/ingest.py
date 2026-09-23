"""Nasdaq TotalView-ITCH 5.0 raw feed decoding.

Primary source for every field semantic used here: "Nasdaq TotalView-ITCH 5.0",
published by Nasdaq, retrieved 2026-09-22 from
https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf
(revision log entry 2023-04-28). Field offsets below are transcribed from that
document's message-format tables; nothing here is coded from memory.

Facts the rest of the pipeline depends on, all from that document:

* All integer fields are big-endian ("Data Types").
* Prices are integers with an implied precision: ``Price(4)`` means four implied
  decimals. Raw prices are therefore kept as integers, with ``TICK_RAW = 100``
  raw units per cent.
* Timestamps are "nanoseconds since midnight" and are *not* accompanied by a
  receive clock. There is no sequence number in the payload; sequencing is a
  property of the transport wrapper (SoupBinTCP / MoldUDP64), which is not part
  of a captured file. Both absences are recorded in the schema contract rather
  than replaced by an assumption.
* Order reference numbers are day-unique; stock locate codes are assigned per day
  and "there should be no expectation that the assignment will be the same across
  multiple days".
* Undisplayed ("Trade Message") executions carry order reference number zero and
  never touch the displayed book.

Container framing (established empirically against this file, not stated in the
specification document): every message is preceded by a two-byte big-endian
length. The decoder verifies that the declared length equals the documented
length of the message type; a mismatch is a framing error and raises. This turns
the length field into a structural integrity check on the whole tape.

The decoder is deliberately a length table plus inline struct unpacking: the
sample tape holds hundreds of millions of messages and per-message object
creation dominates runtime.
"""

from __future__ import annotations

import gzip
import hashlib
import os
import struct
from typing import BinaryIO, Iterator

# 4 MiB working chunk: large enough to amortise IO, small enough to keep the
# resident set flat on a whole-tape pass.
CHUNK = 1 << 22

# Two-byte big-endian message length in front of every message in this file.
FRAME_PREFIX = 2

# Common header layout, spec section 1.1: stock locate (2, offset 1),
# tracking number (2, offset 3), timestamp (6, offset 5). The timestamp is read
# as a 4-byte high word plus a 2-byte low word so that one struct call covers the
# whole header.
HEADER = struct.Struct(">HHIH")
U64 = struct.Struct(">Q")
U32 = struct.Struct(">I")

# Message lengths, spec sections 1.1-1.8 (payload only, excluding the 2-byte
# frame length). Keyed by the message-type byte.
MSG_LENGTH = {
    0x53: 12,  # 'S' System Event
    0x52: 39,  # 'R' Stock Directory
    0x48: 25,  # 'H' Stock Trading Action
    0x59: 20,  # 'Y' Reg SHO Short Sale Price Test Restricted Indicator
    0x4C: 26,  # 'L' Market Participant Position
    0x56: 35,  # 'V' MWCB Decline Level
    0x57: 12,  # 'W' MWCB Status
    0x4B: 28,  # 'K' IPO Quoting Period Update
    0x4A: 35,  # 'J' LULD Auction Collar
    0x68: 21,  # 'h' Operational Halt
    0x41: 36,  # 'A' Add Order, no MPID attribution
    0x46: 40,  # 'F' Add Order with MPID attribution
    0x45: 31,  # 'E' Order Executed
    0x43: 36,  # 'C' Order Executed With Price
    0x58: 23,  # 'X' Order Cancel
    0x44: 19,  # 'D' Order Delete
    0x55: 35,  # 'U' Order Replace
    0x50: 44,  # 'P' Trade (non-cross)
    0x51: 40,  # 'Q' Cross Trade
    0x42: 19,  # 'B' Broken Trade
    0x49: 50,  # 'I' NOII
    0x4E: 20,  # 'N' Retail Price Improvement Indicator
    0x4F: 48,  # 'O' Direct Listing with Capital Raise price discovery
}

MSG_NAME = {
    0x53: "system_event",
    0x52: "stock_directory",
    0x48: "stock_trading_action",
    0x59: "reg_sho",
    0x4C: "market_participant_position",
    0x56: "mwcb_decline_level",
    0x57: "mwcb_status",
    0x4B: "ipo_quoting_period",
    0x4A: "luld_auction_collar",
    0x68: "operational_halt",
    0x41: "add_order",
    0x46: "add_order_mpid",
    0x45: "order_executed",
    0x43: "order_executed_with_price",
    0x58: "order_cancel",
    0x44: "order_delete",
    0x55: "order_replace",
    0x50: "trade_non_cross",
    0x51: "cross_trade",
    0x42: "broken_trade",
    0x49: "noii",
    0x4E: "retail_price_improvement",
    0x4F: "dlcr_price_discovery",
}

# Messages that change the displayed book. 'P' Trade (non-cross) is excluded by
# the specification ("Trade Messages do not affect the book"), as are 'B' Broken
# Trade and the cross messages.
BOOK_MODIFYING = frozenset({0x41, 0x46, 0x45, 0x43, 0x58, 0x44, 0x55})
ADD_TYPES = frozenset({0x41, 0x46})

# System event codes, spec section 1.1.
SYSTEM_EVENT_NAME = {
    b"O": "start_of_messages",
    b"S": "start_of_system_hours",
    b"Q": "start_of_market_hours",
    b"M": "end_of_market_hours",
    b"E": "end_of_system_hours",
    b"C": "end_of_messages",
}

# Stock Directory field offsets, spec section 1.2.1 (payload-relative).
R_STOCK = 11
R_MARKET_CATEGORY = 19
R_FINANCIAL_STATUS = 20
R_ROUND_LOT = 21
R_ROUND_LOTS_ONLY = 25
R_ISSUE_CLASSIFICATION = 26
R_ISSUE_SUB_TYPE = 27
R_AUTHENTICITY = 29
R_SHORT_SALE_THRESHOLD = 30
R_IPO_FLAG = 31
R_LULD_TIER = 32
R_ETP_FLAG = 33
R_ETP_LEVERAGE = 34
R_INVERSE = 38

# Market categories that mean "Nasdaq is the listing venue" (spec 1.2.1).
NASDAQ_LISTED_CATEGORIES = frozenset({"Q", "G", "S"})


class FeedFormatError(RuntimeError):
    """Raised when the byte stream cannot be the documented product."""


def open_source(path: str) -> BinaryIO:
    """Open a raw feed file, transparently decompressing a gzip member."""
    if path.endswith(".gz"):
        return gzip.open(path, "rb")
    return open(path, "rb")


def sha256_file(path: str, chunk: int = CHUNK) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: str, chunk: int = CHUNK) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def size_bytes(path: str) -> int:
    return os.path.getsize(path)


def decode_alpha(raw: bytes) -> str:
    """Alpha fields are ASCII, left justified, right padded with spaces."""
    return raw.decode("ascii", errors="strict").rstrip(" ")


def _framing_error(message_type: int, declared: int, expected: int) -> FeedFormatError:
    return FeedFormatError(
        "framing mismatch: message type "
        f"0x{message_type:02x} declares length {declared}, documented length is {expected}"
    )


def check_no_trailing_bytes(buffer: bytearray) -> None:
    """Leftover bytes after the last complete frame mean a truncated tape."""
    if buffer:
        raise FeedFormatError(
            f"truncated tape: {len(buffer)} trailing bytes do not form a complete framed message"
        )


def read_symbol_directory(path: str) -> dict[int, dict]:
    """Collect the Stock Directory messages from the whole tape, keyed by locate."""
    directory: dict[int, dict] = {}
    with open_source(path) as handle:
        buffer = bytearray()
        position = 0
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            buffer += block
            view = memoryview(buffer)
            limit = len(view)
            while position + 1 < limit:
                declared = (view[position] << 8) | view[position + 1]
                if position + FRAME_PREFIX + declared > limit:
                    break
                base = position + FRAME_PREFIX
                message_type = view[base]
                expected = MSG_LENGTH.get(message_type)
                if expected is None:
                    raise FeedFormatError(
                        f"unknown message type byte 0x{message_type:02x} at stream offset {base}"
                    )
                if declared != expected:
                    raise _framing_error(message_type, declared, expected)
                if message_type == 0x52:  # 'R'
                    locate, _tracking, ts_hi, ts_lo = HEADER.unpack_from(buffer, base + 1)
                    record = directory.get(locate)
                    directory[locate] = {
                        "locate": locate,
                        "symbol": decode_alpha(bytes(view[base + R_STOCK : base + R_STOCK + 8])),
                        "timestamp_ns": (ts_hi << 16) | ts_lo,
                        "market_category": chr(view[base + R_MARKET_CATEGORY]),
                        "financial_status": chr(view[base + R_FINANCIAL_STATUS]),
                        "round_lot_size": U32.unpack_from(buffer, base + R_ROUND_LOT)[0],
                        "round_lots_only": chr(view[base + R_ROUND_LOTS_ONLY]),
                        "issue_classification": chr(view[base + R_ISSUE_CLASSIFICATION]),
                        "issue_sub_type": decode_alpha(
                            bytes(view[base + R_ISSUE_SUB_TYPE : base + R_ISSUE_SUB_TYPE + 2])
                        ),
                        "authenticity": chr(view[base + R_AUTHENTICITY]),
                        "short_sale_threshold": chr(view[base + R_SHORT_SALE_THRESHOLD]),
                        "ipo_flag": chr(view[base + R_IPO_FLAG]),
                        "luld_reference_price_tier": chr(view[base + R_LULD_TIER]),
                        "etp_flag": chr(view[base + R_ETP_FLAG]),
                        "etp_leverage_factor": U32.unpack_from(buffer, base + R_ETP_LEVERAGE)[0],
                        "inverse_indicator": chr(view[base + R_INVERSE]),
                        "directory_messages": (record["directory_messages"] + 1) if record else 1,
                    }
                position += FRAME_PREFIX + declared
            view.release()
            del buffer[:position]
            position = 0
    check_no_trailing_bytes(buffer)
    return directory


def scan_tape(path: str) -> dict:
    """Single sequential pass: framing check, type histogram, per-locate counts.

    ``tracking_number`` is not a sequence contract, so it is audited elsewhere for
    monotonicity only; this pass exists to establish the tape's shape (message
    counts, timestamps, session events) before the expensive replay.
    """
    type_counts = [0] * 256
    locate_add_counts: dict[int, int] = {}
    locate_msg_counts: dict[int, int] = {}
    locate_first_add_price: dict[int, int] = {}
    locate_first_add_ts: dict[int, int] = {}
    system_events: list[dict] = []
    total = 0
    first_ts = None
    last_ts = None
    previous_ts = None
    backwards = 0
    identical_runs = 0
    max_backwards_ns = 0
    adjacent_duplicates = 0
    frames_verified = 0

    previous_key = None
    with open_source(path) as handle:
        buffer = bytearray()
        position = 0
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            buffer += block
            view = memoryview(buffer)
            limit = len(view)
            while position + 1 < limit:
                declared = (view[position] << 8) | view[position + 1]
                if position + FRAME_PREFIX + declared > limit:
                    break
                base = position + FRAME_PREFIX
                message_type = view[base]
                expected = MSG_LENGTH.get(message_type)
                if expected is None:
                    raise FeedFormatError(
                        f"unknown message type byte 0x{message_type:02x} at stream offset {base}"
                    )
                if declared != expected:
                    raise _framing_error(message_type, declared, expected)
                frames_verified += 1
                locate, tracking, ts_hi, ts_lo = HEADER.unpack_from(buffer, base + 1)
                timestamp = (ts_hi << 16) | ts_lo
                key = (message_type, timestamp, tracking, locate)
                if key == previous_key:
                    adjacent_duplicates += 1
                previous_key = key
                type_counts[message_type] += 1
                total += 1
                if first_ts is None:
                    first_ts = timestamp
                if previous_ts is not None:
                    if timestamp < previous_ts:
                        backwards += 1
                        delta = previous_ts - timestamp
                        if delta > max_backwards_ns:
                            max_backwards_ns = delta
                    elif timestamp == previous_ts:
                        identical_runs += 1
                previous_ts = timestamp
                last_ts = timestamp
                if locate:
                    locate_msg_counts[locate] = locate_msg_counts.get(locate, 0) + 1
                    if message_type in ADD_TYPES:
                        locate_add_counts[locate] = locate_add_counts.get(locate, 0) + 1
                        if locate not in locate_first_add_price:
                            locate_first_add_price[locate] = U32.unpack_from(buffer, base + 32)[0]
                            locate_first_add_ts[locate] = timestamp
                elif message_type == 0x53:
                    code = bytes(view[base + 11 : base + 12])
                    system_events.append(
                        {
                            "timestamp_ns": timestamp,
                            "event_code": code.decode("ascii"),
                            "event_name": SYSTEM_EVENT_NAME.get(code, "unrecognised"),
                        }
                    )
                position += FRAME_PREFIX + declared
            view.release()
            del buffer[:position]
            position = 0
    check_no_trailing_bytes(buffer)

    return {
        "container_framing": "TWO_BYTE_BIG_ENDIAN_LENGTH_PREFIX",
        "frames_verified": frames_verified,
        "total_messages": total,
        "type_counts": {
            MSG_NAME[code]: type_counts[code] for code in sorted(MSG_NAME) if type_counts[code]
        },
        "type_counts_raw": {str(code): type_counts[code] for code in range(256) if type_counts[code]},
        "first_timestamp_ns": first_ts,
        "last_timestamp_ns": last_ts,
        "backwards_timestamps": backwards,
        "identical_timestamp_runs": identical_runs,
        "adjacent_duplicates": adjacent_duplicates,
        "max_backwards_ns": max_backwards_ns,
        "system_events": system_events,
        "locate_message_counts": {str(k): v for k, v in locate_msg_counts.items()},
        "locate_add_counts": {str(k): v for k, v in locate_add_counts.items()},
        "locate_first_add_price": {str(k): v for k, v in locate_first_add_price.items()},
        "locate_first_add_timestamp_ns": {str(k): v for k, v in locate_first_add_ts.items()},
    }


def iter_book_events(path: str) -> Iterator[tuple]:
    """Reference decoder used by tests: one tuple per book-modifying message.

    The production replay in ``book.py`` decodes inline for speed; this generator
    exists so tests can assert the decoding rules against small fixtures without
    duplicating the offset table.
    """
    with open_source(path) as handle:
        buffer = bytearray()
        position = 0
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            buffer += block
            view = memoryview(buffer)
            limit = len(view)
            while position + 1 < limit:
                declared = (view[position] << 8) | view[position + 1]
                if position + FRAME_PREFIX + declared > limit:
                    break
                base = position + FRAME_PREFIX
                message_type = view[base]
                expected = MSG_LENGTH.get(message_type)
                if expected is None:
                    raise FeedFormatError(f"unknown message type byte 0x{message_type:02x}")
                if declared != expected:
                    raise _framing_error(message_type, declared, expected)
                locate, _tracking, ts_hi, ts_lo = HEADER.unpack_from(buffer, base + 1)
                timestamp = (ts_hi << 16) | ts_lo
                if message_type in ADD_TYPES:
                    yield (
                        "add",
                        timestamp,
                        locate,
                        U64.unpack_from(buffer, base + 11)[0],
                        chr(view[base + 19]),
                        U32.unpack_from(buffer, base + 20)[0],
                        U32.unpack_from(buffer, base + 32)[0],
                    )
                elif message_type == 0x45:
                    yield (
                        "execute",
                        timestamp,
                        locate,
                        U64.unpack_from(buffer, base + 11)[0],
                        U32.unpack_from(buffer, base + 19)[0],
                    )
                elif message_type == 0x43:
                    yield (
                        "execute_with_price",
                        timestamp,
                        locate,
                        U64.unpack_from(buffer, base + 11)[0],
                        U32.unpack_from(buffer, base + 19)[0],
                        chr(view[base + 31]),
                        U32.unpack_from(buffer, base + 32)[0],
                    )
                elif message_type == 0x58:
                    yield (
                        "cancel",
                        timestamp,
                        locate,
                        U64.unpack_from(buffer, base + 11)[0],
                        U32.unpack_from(buffer, base + 19)[0],
                    )
                elif message_type == 0x44:
                    yield ("delete", timestamp, locate, U64.unpack_from(buffer, base + 11)[0])
                elif message_type == 0x55:
                    yield (
                        "replace",
                        timestamp,
                        locate,
                        U64.unpack_from(buffer, base + 11)[0],
                        U64.unpack_from(buffer, base + 19)[0],
                        U32.unpack_from(buffer, base + 27)[0],
                        U32.unpack_from(buffer, base + 31)[0],
                    )
                position += FRAME_PREFIX + declared
            view.release()
            del buffer[:position]
            position = 0
    check_no_trailing_bytes(buffer)


def build_itch_frame(message_type: int, payload_without_type: bytes) -> bytes:
    """Encode a message for synthetic fixtures: length prefix plus payload."""
    body = bytes([message_type]) + payload_without_type
    expected = MSG_LENGTH[message_type]
    if len(body) != expected:
        raise ValueError(f"message body is {len(body)} bytes, documented length is {expected}")
    return len(body).to_bytes(2, "big") + body


def main(argv: list[str] | None = None) -> int:
    """Stage 1: scan a raw tape and write the derived ingest summary."""
    import argparse
    import json

    from . import config as config_module

    parser = argparse.ArgumentParser(description="Scan a raw ITCH tape (stage 1).")
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_0.yaml")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    raw_path = config_module.repo_path(
        os.path.join(configuration["paths"]["raw_dir"], configuration["dataset"]["raw_files"][0])
    )
    derived = config_module.repo_path(config_module.derived_dir(configuration))
    os.makedirs(derived, exist_ok=True)

    summary = scan_tape(raw_path)
    summary["raw_path"] = os.path.relpath(raw_path, config_module.REPO_ROOT)
    summary["raw_bytes"] = size_bytes(raw_path)
    summary["sha256"] = sha256_file(raw_path)
    summary["computed_md5"] = md5_file(raw_path)
    directory = read_symbol_directory(raw_path)
    summary["symbol_directory_size"] = len(directory)

    config_module.write_json(os.path.join(derived, "ingest_summary.json"), summary)

    import pyarrow as pa
    import pyarrow.parquet as pq

    if directory:
        columns = sorted(next(iter(directory.values())).keys())
        table = pa.table({name: [row[name] for row in directory.values()] for name in columns})
        pq.write_table(table, os.path.join(derived, "symbol_directory.parquet"))

    print(
        json.dumps(
            {
                "total_messages": summary["total_messages"],
                "frames_verified": summary["frames_verified"],
                "symbols": summary["symbol_directory_size"],
                "backwards_timestamps": summary["backwards_timestamps"],
                "adjacent_duplicates": summary["adjacent_duplicates"],
                "derived_dir": os.path.relpath(derived, config_module.REPO_ROOT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
