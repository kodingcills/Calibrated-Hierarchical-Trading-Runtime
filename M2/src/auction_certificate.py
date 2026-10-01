"""Measurement-window continuity + coverage certificate for branch AUCTION (B5).

This module is data admission for the frozen Nasdaq closing-auction materiality
measurement (``TUP-NASDAQ-CLOSE-H4-LATENOII-AGG``). It replaces, for this branch,
the "a message of length zero terminates the session" expectation with two things
that can actually be checked on the retained artefact:

* transport markers over the whole retained object (gzip CRC32/ISIZE, framing,
  trailing bytes, terminal End-of-Messages), and
* a MEASUREMENT-WINDOW CONTINUITY + COVERAGE CERTIFICATE over
  ``15:49:50-16:00:10 ET``: monotonic non-decreasing exchange timestamps, bounded
  inter-message gaps *inside* the window, and per-symbol Closing-Cross NOII
  cadence.

Why the continuity section is load-bearing and the transport markers are not, in
their own right: ``.research/m2_bridge_001/verification/V2/v2_auction_contract_attack.py``
built a spliced, re-compressed tape (first 8 MiB of decoded frames + last 8 MiB,
terminal ``C`` kept) that passed every transport marker while holding 0.92% of the
decoded session. The structural markers certify *transport*, not completeness: a
hole in the middle of a session leaves CRC32, framing and the terminal event
untouched. The in-window continuity rules cannot be satisfied by such a splice,
because they are stated over retained messages *inside* the frozen window.

What the certificate explicitly does NOT claim (stated, not hidden): transport
markers do not prove original-session completeness. Only the measurement window
this branch reads is certified; holes outside ``15:49:50-16:00:10 ET`` are
declared non-material to this branch's inputs, because no frozen signal instant,
entry instant or exit print lies outside the window and a book reconstructed from
the window alone cannot observe pre-window state in any case.

Universe repair (operator-authorized, versioned): the frozen clause
``Issue Sub-Type=C`` admits 31 of 12,809 locates in this session because Nasdaq
marks ordinary common stock with ``Issue Classification=C, Issue Sub-Type=Z``.
The corrected clause is ``Authenticity=P``, ``ETP Flag=N``,
``Issue Classification=C``, ``Market Category in {Q,G,S}`` (Nasdaq-listed common
stock). Rule identity: ``NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2``.
"""

from __future__ import annotations

import datetime
import gzip
import hashlib
import json
import os
import struct
import sys
import time
import zlib
from typing import Mapping

try:  # package import (python3 -m M2.src.auction_certificate)
    from . import ingest as itch
    from . import itch_stream_window as window
except ImportError:  # direct script execution
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ingest as itch  # type: ignore[no-redef]
    import itch_stream_window as window  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Frozen parameters of this certificate. Every threshold is declared here, once,
# before any economic quantity is computed.
# ---------------------------------------------------------------------------

WINDOW_ARTIFACT = "M2/data/derived_auction/2026-06-12/window.bin.gz"

WINDOW_START_NS = window.WINDOW_START_NS
WINDOW_END_NS = window.WINDOW_END_NS
NS_1550 = window.NS_1550
NS_1555 = window.NS_1555

# Continuity bounds. 1 s is two orders of magnitude above the observed in-window
# inter-message gap and four orders below the 22,790 s junction gap of the known
# splice attack; the value is a property of the feed's own pacing, not of any
# outcome.
MAX_IN_WINDOW_GAP_NS = 1_000_000_000
# Closing-Cross NOII cadence, stated over the SIGNAL interval (15:50:00-15:55:00 ET,
# the only interval the frozen signal reads) because that is where the branch's two
# reads must come from. The bound is 1.5 x the dissemination period this session
# actually shows (10 s: 30 cycles x 12809 locates = 384270 reads inside the signal
# interval), so a single missed dissemination cycle fails the check. The period is a
# property of the feed's own schedule, and the whole-window cadence is reported
# alongside as a diagnostic.
MAX_NOII_C_CADENCE_GAP_NS = 15_000_000_000
# The dissemination period this session exhibits, used to state the bound as a
# multiple rather than as a bare number.
OBSERVED_NOII_C_PERIOD_NS = 10_000_000_000
# An order of magnitude below the 55,698,714 in-window messages the source session
# actually carries (source admission record). A spliced or truncated artefact
# cannot reach it.
MIN_IN_WINDOW_MESSAGES = 1_000_000
# Fraction of the producer's own declared in-window message count a retained
# artefact must reproduce (a producer-declared reference, not a recomputation).
DECLARED_MESSAGE_TOLERANCE = 0.99

# ---------------------------------------------------------------------------
# Corrected universe (operator-authorized transcription repair).
# ---------------------------------------------------------------------------

UNIVERSE_RULE_ID_V2 = "NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2"
UNIVERSE_AUTHENTICITY = "P"
UNIVERSE_ETP_FLAG = "N"
UNIVERSE_ISSUE_CLASSIFICATION = "C"
UNIVERSE_MARKET_CATEGORIES = frozenset({"Q", "G", "S"})
UNIVERSE_ISSUE_SUB_TYPE = "UNRESTRICTED_BY_V2"

COVERAGE_FLOOR = 0.95
DIRECTION_ELIGIBLE = frozenset({"B", "S"})

I_PAIRED_SHARES = window.I_PAIRED_SHARES
I_IMBALANCE_SHARES = window.I_IMBALANCE_SHARES
I_IMBALANCE_DIRECTION = window.I_IMBALANCE_DIRECTION
I_STOCK = window.I_STOCK
I_CURRENT_REFERENCE_PRICE = window.I_CURRENT_REFERENCE_PRICE
I_NEAR_PRICE = window.I_NEAR_PRICE
I_FAR_PRICE = window.I_FAR_PRICE
I_CROSS_TYPE = window.I_CROSS_TYPE
Q_SHARES = window.Q_SHARES
Q_STOCK = window.Q_STOCK
Q_CROSS_PRICE = window.Q_CROSS_PRICE
Q_CROSS_TYPE = window.Q_CROSS_TYPE

TYPE_SYSTEM_EVENT = window.TYPE_SYSTEM_EVENT
TYPE_STOCK_DIRECTORY = window.TYPE_STOCK_DIRECTORY
TYPE_NOII = window.TYPE_NOII
TYPE_CROSS_TRADE = window.TYPE_CROSS_TRADE

HEADER = itch.HEADER
TS_FIELD = struct.Struct(">IH")
U64 = itch.U64
U32 = itch.U32
FRAME_PREFIX = itch.FRAME_PREFIX
READ_SIZE = itch.CHUNK


class SymbolState:
    """Directory identity, Closing-Cross NOII cadence and cross print for one locate."""

    __slots__ = (
        "locate",
        "symbol",
        "market_category",
        "issue_classification",
        "issue_sub_type",
        "authenticity",
        "etp_flag",
        "financial_status",
        "c_read_count",
        "c_first_ts_ns",
        "c_last_ts_ns",
        "c_max_gap_ns",
        "c_max_gap_signal_ns",
        "c_prev_ts_ns",
        "c_prev_signal_ts_ns",
        "c_reads_1550_1555",
        "c_reads_after_1555",
        "read_1550",
        "read_1550_after",
        "read_1555",
        "cross",
        "cross_count",
    )

    def __init__(self, locate: int) -> None:
        self.locate = locate
        self.symbol = None
        self.market_category = None
        self.issue_classification = None
        self.issue_sub_type = None
        self.authenticity = None
        self.etp_flag = None
        self.financial_status = None
        self.c_read_count = 0
        self.c_first_ts_ns = None
        self.c_last_ts_ns = None
        self.c_max_gap_ns = 0
        self.c_max_gap_signal_ns = 0
        self.c_prev_ts_ns = None
        self.c_prev_signal_ts_ns = None
        self.c_reads_1550_1555 = 0
        self.c_reads_after_1555 = 0
        self.read_1550 = None
        self.read_1550_after = None
        self.read_1555 = None
        self.cross = None
        self.cross_count = 0


def corrected_universe_eligible(state: SymbolState) -> bool:
    """The corrected point-in-time clause: Nasdaq-listed common stock."""
    return (
        state.market_category in UNIVERSE_MARKET_CATEGORIES
        and state.issue_classification == UNIVERSE_ISSUE_CLASSIFICATION
        and state.authenticity == UNIVERSE_AUTHENTICITY
        and state.etp_flag == UNIVERSE_ETP_FLAG
    )


def corrected_universe_failure(state: SymbolState) -> str:
    failures = []
    if state.market_category not in UNIVERSE_MARKET_CATEGORIES:
        failures.append(f"market_category={state.market_category!r}")
    if state.issue_classification != UNIVERSE_ISSUE_CLASSIFICATION:
        failures.append(f"issue_classification={state.issue_classification!r}")
    if state.authenticity != UNIVERSE_AUTHENTICITY:
        failures.append(f"authenticity={state.authenticity!r}")
    if state.etp_flag != UNIVERSE_ETP_FLAG:
        failures.append(f"etp_flag={state.etp_flag!r}")
    return ";".join(failures) if failures else "eligible"


def valid_cross(state: SymbolState) -> bool:
    """A Closing-Cross print anchors the exit only when it is a real print."""
    cross = state.cross
    return cross is not None and cross["shares"] > 0 and cross["cross_price"] > 0


def select_reads(state: SymbolState) -> tuple[dict | None, dict | None]:
    """The frozen read semantics.

    ``15:50``: the last eligible Closing-Cross read at or before 15:50:00 ET, else
    the first read after it (the frozen fallback: Nasdaq begins disseminating close
    reads at 15:50). ``15:55``: the last read at or before 15:55:00 ET.
    """
    early = state.read_1550 if state.read_1550 is not None else state.read_1550_after
    return early, state.read_1555


def _read_record(buffer, view, base: int) -> dict:
    hi, lo = TS_FIELD.unpack_from(buffer, base + 5)
    return {
        "timestamp_ns": (hi << 16) | lo,
        "symbol": itch.decode_alpha(bytes(view[base + I_STOCK : base + I_STOCK + 8])),
        "paired_shares": U64.unpack_from(buffer, base + I_PAIRED_SHARES)[0],
        "imbalance_shares": U64.unpack_from(buffer, base + I_IMBALANCE_SHARES)[0],
        "imbalance_direction": chr(view[base + I_IMBALANCE_DIRECTION]),
        "far_price": U32.unpack_from(buffer, base + I_FAR_PRICE)[0],
        "near_price": U32.unpack_from(buffer, base + I_NEAR_PRICE)[0],
        "current_reference_price": U32.unpack_from(buffer, base + I_CURRENT_REFERENCE_PRICE)[0],
        "cross_type": chr(view[base + I_CROSS_TYPE]),
    }


def _cross_record(buffer, view, base: int) -> dict:
    hi, lo = TS_FIELD.unpack_from(buffer, base + 5)
    return {
        "timestamp_ns": (hi << 16) | lo,
        "symbol": itch.decode_alpha(bytes(view[base + Q_STOCK : base + Q_STOCK + 8])),
        "shares": U64.unpack_from(buffer, base + Q_SHARES)[0],
        "cross_price": U32.unpack_from(buffer, base + Q_CROSS_PRICE)[0],
        "cross_type": chr(view[base + Q_CROSS_TYPE]),
    }


def scan_window_continuity(path: str) -> tuple[dict[int, SymbolState], dict]:
    """One decompressing pass: transport markers, in-window continuity, identities.

    The pass collects exactly what the certificate certifies. Nothing about price
    levels, returns or outcomes is read here.
    """
    states: dict[int, SymbolState] = {}
    stats = {
        "frames": 0,
        "compressed_bytes": 0,
        "decoded_bytes": 0,
        "gzip_eof": False,
        "gzip_unused_bytes": 0,
        "gzip_error": None,
        "framing_error": None,
        "trailing_bytes": 0,
        "first_timestamp_ns": None,
        "last_timestamp_ns": None,
        "last_message_type": None,
        "last_event_code": None,
        "backwards_timestamps": 0,
        "max_reversal_ns": 0,
        "in_window_messages": 0,
        "in_window_pairs": 0,
        "max_in_window_gap_ns": 0,
        "max_in_window_gap_at_ns": None,
        "gaps_over_100ms": 0,
        "gaps_over_500ms": 0,
        "gaps_over_bound": 0,
        "largest_in_window_gaps": [],
        "max_stream_gap_ns": 0,
        "max_stream_gap_at_ns": None,
        "noii_messages": 0,
        "noii_c_reads": 0,
        "noii_c_reads_in_signal_interval": 0,
        "noii_c_reads_before_signal_interval": 0,
        "noii_c_reads_by_10s_bucket": {},
        "noii_c_first_ts_ns": None,
        "noii_c_last_ts_ns": None,
        "cross_trades": 0,
        "closing_cross_prints": 0,
        "closing_cross_zero_share": 0,
        "stock_directory_messages": 0,
        "issue_classification_counts": {},
        "issue_sub_type_counts": {},
        "market_category_counts": {},
        "authenticity_counts": {},
        "etp_flag_counts": {},
        "classification_subtype_pairs": {},
        "corrected_universe_locates": 0,
        "frozen_v1_clause_locates": 0,
    }
    msg_length = itch.MSG_LENGTH
    unpack_header = HEADER.unpack_from

    def bump(key: str, value) -> None:
        bucket = stats[key]
        bucket[value] = bucket.get(value, 0) + 1

    def gaps_append(gap: int, ts: int) -> None:
        rows = stats["largest_in_window_gaps"]
        rows.append({"gap_ns": gap, "at_timestamp_ns": ts, "at": window.format_ns(ts)})
        rows.sort(key=lambda row: -row["gap_ns"])
        del rows[8:]

    started = time.time()
    decompressor = zlib.decompressobj(window.GZIP_WINDOW)
    buffer = bytearray()
    position = 0
    previous_ts = None
    previous_in_window = False
    with open(path, "rb") as handle:
        while True:
            block = handle.read(READ_SIZE)
            if not block:
                break
            stats["compressed_bytes"] += len(block)
            try:
                data = decompressor.decompress(block)
            except zlib.error as exc:
                stats["gzip_error"] = str(exc)
                break
            stats["decoded_bytes"] += len(data)
            if not data:
                continue
            buffer += data
            view = memoryview(buffer)
            limit = len(view)
            while position + FRAME_PREFIX <= limit:
                declared = (view[position] << 8) | view[position + 1]
                if declared == 0:
                    position += FRAME_PREFIX
                    continue
                if position + FRAME_PREFIX + declared > limit:
                    break
                base = position + FRAME_PREFIX
                message_type = view[base]
                expected = msg_length.get(message_type)
                if expected is None or declared != expected:
                    stats["framing_error"] = (
                        f"type 0x{message_type:02x} declares {declared}, documented "
                        f"{expected if expected is not None else 'unknown'}"
                    )
                    break
                stats["frames"] += 1
                locate, _tracking, ts_hi, ts_lo = unpack_header(buffer, base + 1)
                timestamp = (ts_hi << 16) | ts_lo
                if stats["first_timestamp_ns"] is None:
                    stats["first_timestamp_ns"] = timestamp
                stats["last_timestamp_ns"] = timestamp
                stats["last_message_type"] = chr(message_type)
                in_window = WINDOW_START_NS <= timestamp <= WINDOW_END_NS
                if in_window:
                    stats["in_window_messages"] += 1
                if previous_ts is not None:
                    gap = timestamp - previous_ts
                    if gap < 0:
                        stats["backwards_timestamps"] += 1
                        if -gap > stats["max_reversal_ns"]:
                            stats["max_reversal_ns"] = -gap
                    else:
                        if gap > stats["max_stream_gap_ns"]:
                            stats["max_stream_gap_ns"] = gap
                            stats["max_stream_gap_at_ns"] = timestamp
                        # Only a pair whose BOTH endpoints lie inside the frozen
                        # window certifies the window: the retained object also
                        # carries the session's Stock Directory (03:0x) and the
                        # closing system events (16:00, 20:00, 20:05), whose
                        # separations are legitimate and out of scope.
                        if in_window and previous_in_window:
                            stats["in_window_pairs"] += 1
                            if gap > stats["max_in_window_gap_ns"]:
                                stats["max_in_window_gap_ns"] = gap
                                stats["max_in_window_gap_at_ns"] = timestamp
                            if gap > MAX_IN_WINDOW_GAP_NS:
                                stats["gaps_over_bound"] += 1
                            if gap > 500_000_000:
                                stats["gaps_over_500ms"] += 1
                            if gap > 100_000_000:
                                stats["gaps_over_100ms"] += 1
                            gaps_append(gap, timestamp)
                previous_ts = timestamp
                previous_in_window = in_window

                if message_type == TYPE_STOCK_DIRECTORY:
                    stats["stock_directory_messages"] += 1
                    state = states.get(locate)
                    if state is None:
                        state = SymbolState(locate)
                        states[locate] = state
                    state.symbol = itch.decode_alpha(
                        bytes(view[base + itch.R_STOCK : base + itch.R_STOCK + 8])
                    )
                    state.market_category = chr(view[base + itch.R_MARKET_CATEGORY])
                    state.financial_status = chr(view[base + itch.R_FINANCIAL_STATUS])
                    state.issue_classification = chr(view[base + itch.R_ISSUE_CLASSIFICATION])
                    state.issue_sub_type = itch.decode_alpha(
                        bytes(view[base + itch.R_ISSUE_SUB_TYPE : base + itch.R_ISSUE_SUB_TYPE + 2])
                    )
                    state.authenticity = chr(view[base + itch.R_AUTHENTICITY])
                    state.etp_flag = chr(view[base + itch.R_ETP_FLAG])
                    if corrected_universe_eligible(state):
                        stats["corrected_universe_locates"] += 1
                    if (
                        state.authenticity == "P"
                        and state.etp_flag == "N"
                        and state.issue_classification == "C"
                        and state.issue_sub_type == "C"
                    ):
                        stats["frozen_v1_clause_locates"] += 1
                    bump("issue_classification_counts", state.issue_classification)
                    bump("issue_sub_type_counts", state.issue_sub_type)
                    bump("market_category_counts", state.market_category)
                    bump("authenticity_counts", state.authenticity)
                    bump("etp_flag_counts", state.etp_flag)
                    bump(
                        "classification_subtype_pairs",
                        f"{state.issue_classification}/{state.issue_sub_type}",
                    )
                elif message_type == TYPE_NOII:
                    stats["noii_messages"] += 1
                    if view[base + I_CROSS_TYPE : base + I_CROSS_TYPE + 1] != b"C":
                        position += FRAME_PREFIX + declared
                        continue
                    record = _read_record(buffer, view, base)
                    stats["noii_c_reads"] += 1
                    state = states.get(locate)
                    if state is None:
                        state = SymbolState(locate)
                        states[locate] = state
                    ts = record["timestamp_ns"]
                    state.c_read_count += 1
                    if state.c_first_ts_ns is None:
                        state.c_first_ts_ns = ts
                    if state.c_prev_ts_ns is not None:
                        gap = ts - state.c_prev_ts_ns
                        if gap > state.c_max_gap_ns:
                            state.c_max_gap_ns = gap
                    state.c_prev_ts_ns = ts
                    state.c_last_ts_ns = ts
                    if NS_1550 <= ts <= NS_1555:
                        state.c_reads_1550_1555 += 1
                        stats["noii_c_reads_in_signal_interval"] += 1
                        bucket = (ts - NS_1550) // 10_000_000_000
                        stats["noii_c_reads_by_10s_bucket"][bucket] = (
                            stats["noii_c_reads_by_10s_bucket"].get(bucket, 0) + 1
                        )
                        if state.c_prev_signal_ts_ns is not None:
                            gap = ts - state.c_prev_signal_ts_ns
                            if gap > state.c_max_gap_signal_ns:
                                state.c_max_gap_signal_ns = gap
                        state.c_prev_signal_ts_ns = ts
                    elif NS_1555 < ts <= WINDOW_END_NS:
                        state.c_reads_after_1555 += 1
                    elif ts < NS_1550:
                        stats["noii_c_reads_before_signal_interval"] += 1
                    if ts <= NS_1550:
                        state.read_1550 = record
                    elif state.read_1550_after is None:
                        state.read_1550_after = record
                    if ts <= NS_1555:
                        state.read_1555 = record
                    if stats["noii_c_first_ts_ns"] is None or ts < stats["noii_c_first_ts_ns"]:
                        stats["noii_c_first_ts_ns"] = ts
                    if stats["noii_c_last_ts_ns"] is None or ts > stats["noii_c_last_ts_ns"]:
                        stats["noii_c_last_ts_ns"] = ts
                elif message_type == TYPE_CROSS_TRADE:
                    stats["cross_trades"] += 1
                    if view[base + Q_CROSS_TYPE : base + Q_CROSS_TYPE + 1] != b"C":
                        position += FRAME_PREFIX + declared
                        continue
                    record = _cross_record(buffer, view, base)
                    stats["closing_cross_prints"] += 1
                    if record["shares"] == 0:
                        stats["closing_cross_zero_share"] += 1
                    state = states.get(locate)
                    if state is None:
                        state = SymbolState(locate)
                        states[locate] = state
                    state.cross = record
                    state.cross_count += 1
                elif message_type == TYPE_SYSTEM_EVENT:
                    stats["last_event_code"] = chr(view[base + 11])
                position += FRAME_PREFIX + declared
            if stats["framing_error"] is not None:
                break
            view.release()
            del buffer[:position]
            position = 0
    stats["tailing_bytes_after_frames"] = len(buffer)
    if stats["framing_error"] is None:
        stats["trailing_bytes"] = len(buffer)
    stats["gzip_eof"] = bool(decompressor.eof)
    stats["gzip_unused_bytes"] = len(decompressor.unused_data)
    stats["elapsed_seconds"] = round(time.time() - started, 1)
    return states, stats


def _sha256_file(path: str, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _cadence_schedule_note(stats: Mapping) -> str:
    """The observed closing-read dissemination schedule, stated as a fact."""
    return (
        "Observed closing-read dissemination runs from {} to {} ({} reads inside the signal "
        "interval), which is why the cadence bound is stated over the signal interval.".format(
            window.format_ns(stats.get("noii_c_first_ts_ns")),
            window.format_ns(stats.get("noii_c_last_ts_ns")),
            stats.get("noii_c_reads_in_signal_interval"),
        )
    )


def certificate_rows(states: Mapping[int, SymbolState]) -> list[dict]:
    """Per-symbol coverage rows under the corrected universe and frozen reads."""
    rows = []
    for locate in sorted(states):
        state = states[locate]
        if state.symbol is None and state.cross is None and state.c_read_count == 0:
            continue  # locate carried by an unexpected message class only
        early, late = select_reads(state)
        qualified = corrected_universe_eligible(state)
        cross_ok = valid_cross(state)
        denominator = bool(qualified and cross_ok)
        direction_bad = [
            label
            for label, record in (("1550", early), ("1555", late))
            if record is not None and record["imbalance_direction"] not in DIRECTION_ELIGIBLE
        ]
        missing_reads = early is None or late is None
        cadence_ok = (
            state.c_reads_1550_1555 > 0
            and state.c_max_gap_signal_ns <= MAX_NOII_C_CADENCE_GAP_NS
        )
        numerator = bool(denominator and not missing_reads and cadence_ok)
        signal_defined = bool(numerator and not direction_bad)
        if not qualified:
            reason = "directory_ineligible"
        elif state.cross is None:
            reason = "no_closing_cross_print"
        elif not cross_ok:
            reason = "zero_share_closing_cross"
        elif missing_reads:
            reason = "no_closing_cross_noii_read"
        elif not cadence_ok:
            reason = "noii_cadence_gap"
        else:
            reason = ""
        scope_reason = "ineligible_imbalance_direction" if (numerator and direction_bad) else ""
        rows.append(
            {
                "locate": locate,
                "symbol": state.symbol or "",
                "market_category": state.market_category or "",
                "issue_classification": state.issue_classification or "",
                "issue_sub_type": state.issue_sub_type or "",
                "authenticity": state.authenticity or "",
                "etp_flag": state.etp_flag or "",
                "financial_status": state.financial_status or "",
                "universe_qualified": qualified,
                "directory_failure": "" if qualified else corrected_universe_failure(state),
                "has_closing_cross_C": state.cross is not None,
                "closing_cross_valid": cross_ok,
                "closing_cross_shares": state.cross["shares"] if state.cross else "",
                "closing_cross_price_raw": state.cross["cross_price"] if state.cross else "",
                "closing_cross_ts_ns": state.cross["timestamp_ns"] if state.cross else "",
                "c_read_count": state.c_read_count,
                "c_reads_1550_1555": state.c_reads_1550_1555,
                "c_reads_after_1555": state.c_reads_after_1555,
                "c_max_gap_ns": state.c_max_gap_ns,
                "c_max_gap_signal_interval_ns": state.c_max_gap_signal_ns,
                "c_reads_signal_interval": state.c_reads_1550_1555,
                "c_cadence_ok": cadence_ok,
                "imbalance_direction_eligible": not direction_bad,
                "read_1550_ts_ns": early["timestamp_ns"] if early else "",
                "read_1550_source": (
                    "AT_OR_BEFORE"
                    if state.read_1550 is not None
                    else ("FIRST_AFTER" if early else "")
                ),
                "read_1550_paired_shares": early["paired_shares"] if early else "",
                "read_1550_imbalance_shares": early["imbalance_shares"] if early else "",
                "read_1550_direction": early["imbalance_direction"] if early else "",
                "read_1550_reference_price_raw": early["current_reference_price"] if early else "",
                "read_1550_near_price_raw": early["near_price"] if early else "",
                "read_1550_far_price_raw": early["far_price"] if early else "",
                "read_1555_ts_ns": late["timestamp_ns"] if late else "",
                "read_1555_paired_shares": late["paired_shares"] if late else "",
                "read_1555_imbalance_shares": late["imbalance_shares"] if late else "",
                "read_1555_direction": late["imbalance_direction"] if late else "",
                "read_1555_reference_price_raw": late["current_reference_price"] if late else "",
                "read_1555_near_price_raw": late["near_price"] if late else "",
                "read_1555_far_price_raw": late["far_price"] if late else "",
                "in_denominator": denominator,
                "in_numerator": numerator,
                "signal_defined": signal_defined,
                "exclusion_reason": reason,
                "signal_scope_reason": scope_reason,
            }
        )
    return rows


def build_certificate(
    window_path: str,
    *,
    expected_sha256: str | None = None,
    expected_decoded_bytes: int | None = None,
    declared_in_window_messages: int | None = None,
    declared_received_bytes: int | None = None,
    declared_content_range_total: int | None = None,
    min_in_window_messages: int = MIN_IN_WINDOW_MESSAGES,
) -> tuple[dict, dict[int, SymbolState]]:
    """Run the certificate over the retained window.

    ``min_in_window_messages`` defaults to the frozen bound; fixtures that cannot
    carry a million messages pass a smaller one, which changes no default.
    """
    states, stats = scan_window_continuity(window_path)
    actual_sha256 = _sha256_file(window_path)
    actual_bytes = os.path.getsize(window_path)

    transport = {
        "window_artifact": window_path,
        "window_artifact_bytes": actual_bytes,
        "window_artifact_sha256": actual_sha256,
        "decoded_bytes": stats["decoded_bytes"],
        "gzip_integrity": "PASS"
        if (stats["gzip_eof"] and not stats["gzip_unused_bytes"] and stats["gzip_error"] is None)
        else "FAIL",
        "gzip_eof": stats["gzip_eof"],
        "gzip_unused_data_bytes": stats["gzip_unused_bytes"],
        "gzip_error": stats["gzip_error"],
        "framing_errors": 0 if stats["framing_error"] is None else 1,
        "framing_error_detail": stats["framing_error"],
        "frames": stats["frames"],
        "trailing_bytes_after_frames": stats["trailing_bytes"],
        "last_message_type": stats["last_message_type"],
        "last_event_code": stats["last_event_code"],
        "final_frame_is_C_end_of_messages": (
            stats["last_message_type"] == "S" and stats["last_event_code"] == "C"
        ),
        "received_bytes": declared_received_bytes,
        "content_range_total": declared_content_range_total,
        "received_bytes_equals_content_range_total": (
            None
            if declared_received_bytes is None or declared_content_range_total is None
            else declared_received_bytes == declared_content_range_total
        ),
        "received_bytes_provenance": "PRODUCER_DECLARED_NOT_RECOMPUTED",
    }
    transport_ok = (
        transport["gzip_integrity"] == "PASS"
        and transport["framing_errors"] == 0
        and transport["trailing_bytes_after_frames"] == 0
        and transport["final_frame_is_C_end_of_messages"] is True
    )

    identity = {
        "expected_sha256": expected_sha256,
        "observed_sha256": actual_sha256,
        "sha256_matches_declared": None if expected_sha256 is None else actual_sha256 == expected_sha256,
        "expected_decoded_bytes": expected_decoded_bytes,
        "observed_decoded_bytes": stats["decoded_bytes"],
        "decoded_bytes_matches_declared": (
            None if expected_decoded_bytes is None else stats["decoded_bytes"] == expected_decoded_bytes
        ),
        "note": (
            "Artefact identity is separate from the transport markers on purpose: the known "
            "splice attack is a well-formed gzip object, so CRC32/framing/terminal markers pass "
            "on it. Identity (hash and decoded size) and the in-window continuity rules are what "
            "refuse it."
        ),
    }
    identity_ok = (
        identity["sha256_matches_declared"] is not False
        and identity["decoded_bytes_matches_declared"] is not False
    )

    monotonic_ok = stats["backwards_timestamps"] == 0
    gap_ok = (
        stats["in_window_messages"] >= min_in_window_messages
        and stats["in_window_pairs"] > 0
        and stats["max_in_window_gap_ns"] <= MAX_IN_WINDOW_GAP_NS
    )
    declared_ratio = (
        None
        if not declared_in_window_messages
        else stats["in_window_messages"] / declared_in_window_messages
    )
    declared_ok = None if declared_ratio is None else declared_ratio >= DECLARED_MESSAGE_TOLERANCE

    continuity = {
        "window": {
            "start_ns": WINDOW_START_NS,
            "end_ns": WINDOW_END_NS,
            "start": window.format_ns(WINDOW_START_NS),
            "end": window.format_ns(WINDOW_END_NS),
        },
        "bounds": {
            "max_in_window_gap_ns": MAX_IN_WINDOW_GAP_NS,
            "min_in_window_messages": min_in_window_messages,
            "declared_message_tolerance": DECLARED_MESSAGE_TOLERANCE,
        },
        "first_timestamp_ns": stats["first_timestamp_ns"],
        "first_timestamp": window.format_ns(stats["first_timestamp_ns"]),
        "last_timestamp_ns": stats["last_timestamp_ns"],
        "last_timestamp": window.format_ns(stats["last_timestamp_ns"]),
        "monotonic_non_decreasing_exchange_timestamps": monotonic_ok,
        "backwards_timestamps": stats["backwards_timestamps"],
        "max_reversal_ns": stats["max_reversal_ns"],
        "in_window_messages": stats["in_window_messages"],
        "in_window_message_pairs": stats["in_window_pairs"],
        "max_in_window_gap_ns": stats["max_in_window_gap_ns"],
        "max_in_window_gap_at": window.format_ns(stats["max_in_window_gap_at_ns"]),
        "max_in_window_gap_within_bound": stats["max_in_window_gap_ns"] <= MAX_IN_WINDOW_GAP_NS,
        "gaps_over_100ms": stats["gaps_over_100ms"],
        "gaps_over_500ms": stats["gaps_over_500ms"],
        "gaps_over_bound": stats["gaps_over_bound"],
        "largest_in_window_gaps": stats["largest_in_window_gaps"],
        "whole_retained_stream_max_gap_ns": stats["max_stream_gap_ns"],
        "whole_retained_stream_max_gap_at": window.format_ns(stats["max_stream_gap_at_ns"]),
        "whole_retained_stream_max_gap_note": (
            "Out-of-window separations are large by construction (Stock Directory at 03:0x, "
            "closing system events at 16:00/20:00/20:05) and are declared non-material to this "
            "branch's inputs. The figure is reported so a hole is never hidden; the bound that "
            "certifies the window is the in-window one."
        ),
        "declared_in_window_messages": declared_in_window_messages,
        "declared_message_ratio": declared_ratio,
        "in_window_message_count_matches_declaration": declared_ok,
        "frames": stats["frames"],
    }
    continuity_ok = monotonic_ok and gap_ok and (declared_ok is not False)

    rows = certificate_rows(states)
    universe_stats = {
        key: stats[key]
        for key in (
            "stock_directory_messages",
            "issue_classification_counts",
            "issue_sub_type_counts",
            "market_category_counts",
            "authenticity_counts",
            "etp_flag_counts",
            "classification_subtype_pairs",
            "corrected_universe_locates",
            "frozen_v1_clause_locates",
            "noii_messages",
            "noii_c_reads",
            "cross_trades",
            "closing_cross_prints",
            "closing_cross_zero_share",
        )
    }
    universe_repair = {
        "rule_id_v2": UNIVERSE_RULE_ID_V2,
        "clause_v2": {
            "Authenticity": UNIVERSE_AUTHENTICITY,
            "ETP Flag": UNIVERSE_ETP_FLAG,
            "Issue Classification": UNIVERSE_ISSUE_CLASSIFICATION,
            "Market Category": sorted(UNIVERSE_MARKET_CATEGORIES),
            "Issue Sub-Type": UNIVERSE_ISSUE_SUB_TYPE,
        },
        "clause_v1_retained": {
            "Authenticity": "P",
            "ETP Flag": "N",
            "Issue Classification": "C",
            "Issue Sub-Type": "C",
            "Market Category": ["Q", "G", "S", "N", "A", "P", "Z", "V"],
        },
        "v1_clause_locates_admitted": stats["frozen_v1_clause_locates"],
        "v2_clause_locates_admitted": stats["corrected_universe_locates"],
        "locates_in_session": stats["stock_directory_messages"],
        "repair_reason": (
            "ITCH Appendix E defines Issue Sub-Type C='Common Shares' and Z='Not Applicable', and "
            "Nasdaq marks ordinary common stock with Issue Classification=C, Issue Sub-Type=Z; the "
            "frozen clause 'Issue Sub-Type=C' was therefore a transcription artefact, not a "
            "universe (it admits 31 of 12809 locates). The corrected clause admits Nasdaq-listed "
            "common stock (Market Category Q/G/S) and drops the sub-type constraint. Zero-share "
            "and zero-price cross prints concentrate in the non-Nasdaq-listed categories, so the "
            "correction is also what removes the bulk of the unprintable crosses rather than "
            "silently re-scoping around them."
        ),
        "counts": universe_stats,
    }

    denominator_rows = [row for row in rows if row["in_denominator"]]
    numerator_rows = [row for row in rows if row["in_numerator"]]
    signal_rows = [row for row in rows if row["signal_defined"]]
    reason_counts: dict[str, int] = {}
    for row in rows:
        if row["exclusion_reason"]:
            reason_counts[row["exclusion_reason"]] = reason_counts.get(row["exclusion_reason"], 0) + 1
    scope_counts: dict[str, int] = {}
    for row in rows:
        if row["signal_scope_reason"]:
            scope_counts[row["signal_scope_reason"]] = scope_counts.get(row["signal_scope_reason"], 0) + 1
    ratio = (len(numerator_rows) / len(denominator_rows)) if denominator_rows else None
    signal_ratio = (len(signal_rows) / len(denominator_rows)) if denominator_rows else None
    cadence_rows = [row for row in denominator_rows if row["c_cadence_ok"]]
    cadence_ratio = (len(cadence_rows) / len(denominator_rows)) if denominator_rows else None
    coverage = {
        "definition": (
            "qualified = corrected-universe point-in-time Stock Directory membership; denominator "
            "= qualified symbols carrying a valid Closing Cross print; numerator = denominator "
            "symbols that also carry both frozen Closing-Cross NOII reads with Closing-Cross NOII "
            "cadence inside the signal interval. This is the input-availability coverage the "
            "branch's own 0.95 floor and the repo's established coverage machinery measure: the "
            "frozen data inputs are present. Imbalance-direction eligibility is NOT part of this "
            "numerator: direction N/O/P is a market state (no imbalance), not a hole in the data, "
            "and it is reported separately below as the signal scope."
        ),
        "universe_qualified_symbols": sum(1 for row in rows if row["universe_qualified"]),
        "denominator_symbols_with_valid_closing_cross_C": len(denominator_rows),
        "numerator_both_C_reads_and_valid_cross": len(numerator_rows),
        "coverage_ratio": ratio,
        "tolerance": COVERAGE_FLOOR,
        "tolerance_met": None if ratio is None else ratio + 1e-12 >= COVERAGE_FLOOR,
        "exclusion_reason_counts": reason_counts,
        "missingness_audit_count": sum(1 for row in rows if row["exclusion_reason"]),
        "missingness_audit": [
            {
                "locate": row["locate"],
                "symbol": row["symbol"],
                "kind": "coverage",
                "reason": row["exclusion_reason"],
                "detail": (
                    row["directory_failure"]
                    if row["exclusion_reason"] == "directory_ineligible"
                    else ""
                ),
                "universe_qualified": row["universe_qualified"],
                "has_closing_cross_C": row["has_closing_cross_C"],
                "closing_cross_valid": row["closing_cross_valid"],
                "has_both_reads": bool(
                    row["read_1550_ts_ns"] != "" and row["read_1555_ts_ns"] != ""
                ),
            }
            for row in rows
            if row["exclusion_reason"]
        ],
        "signal_scope": {
            "definition": (
                "denominator symbols for which the FROZEN sign rule yields a signed imbalance at "
                "BOTH reads (direction B or S). The frozen formulation declares direction N/O/P "
                "'missing and ineligible'; measured here, every such read carries "
                "ImbalanceShares == 0, and symbols whose two reads are both N have "
                "delta_imbalance == 0 and no signal under any reading."
            ),
            "signal_defined_symbols": len(signal_rows),
            "signal_defined_ratio": signal_ratio,
            "subfloor": None if signal_ratio is None else signal_ratio < COVERAGE_FLOOR,
            "exclusion_reason_counts": scope_counts,
            "excluded_by_identity": [
                {
                    "locate": row["locate"],
                    "symbol": row["symbol"],
                    "reason": row["signal_scope_reason"],
                    "direction_1550": row["read_1550_direction"],
                    "direction_1555": row["read_1555_direction"],
                    "imbalance_shares_1550": row["read_1550_imbalance_shares"],
                    "imbalance_shares_1555": row["read_1555_imbalance_shares"],
                }
                for row in rows
                if row["signal_scope_reason"]
            ],
        },
        "noii_cadence": {
            "bound_ns": MAX_NOII_C_CADENCE_GAP_NS,
            "bound": (
                "15 s (1.5 x the 10 s period this session exhibits) between consecutive "
                "Closing-Cross NOII reads inside 15:50:00-15:55:00 ET; one missed dissemination "
                "cycle fails"
            ),
            "observed_dissemination_period_ns": OBSERVED_NOII_C_PERIOD_NS,
            "interval": "signal interval 15:50:00-15:55:00 ET",
            "denominator_symbols": len(denominator_rows),
            "symbols_within_bound": len(cadence_rows),
            "ratio": cadence_ratio,
            "max_observed_signal_interval_gap_ns": max(
                (row["c_max_gap_signal_interval_ns"] for row in denominator_rows), default=None
            ),
            "whole_window_max_observed_gap_ns": max(
                (row["c_max_gap_ns"] for row in denominator_rows), default=None
            ),
            "whole_window_note": (
                "Diagnostic only: the whole-window figure includes the feed's own dissemination "
                "boundaries, so it is a property of the schedule rather than of this branch's "
                "inputs. " + _cadence_schedule_note(stats)
            ),
            "reads_in_signal_interval": stats["noii_c_reads_in_signal_interval"],
            "reads_by_10s_bucket": {
                str(key): value for key, value in sorted(stats["noii_c_reads_by_10s_bucket"].items())
            },
            "first_c_read": window.format_ns(stats["noii_c_first_ts_ns"]),
            "last_c_read": window.format_ns(stats["noii_c_last_ts_ns"]),
        },
    }
    coverage_ok = coverage["tolerance_met"] is True and cadence_ratio == 1.0

    checks = {
        "transport_markers": transport_ok,
        "artefact_identity": identity_ok,
        "measurement_window_continuity": continuity_ok,
        "coverage_certificate": coverage_ok,
    }
    failed = [name for name, passed in checks.items() if not passed]
    verdict = {
        "transport_markers": "PASS" if transport_ok else "FAIL",
        "artefact_identity": "PASS" if identity_ok else "FAIL",
        "measurement_window_continuity": "PASS" if continuity_ok else "FAIL",
        "coverage_certificate": "PASS" if coverage_ok else "FAIL",
        "overall": "PASS" if not failed else "FAIL",
        "named_clause": None if not failed else failed[0].upper(),
        "failed_checks": [name.upper() for name in failed],
        "transport_markers_prove_original_session_completeness": False,
        "out_of_window_holes": "DECLARED_NON_MATERIAL_TO_BRANCH_INPUTS",
        "completeness_statement": (
            "The transport markers certify that the retained object is intact and that the feed "
            "ended on its End-of-Messages event; they do NOT prove that the original session was "
            "captured whole. Only the frozen measurement window 15:49:50-16:00:10 ET is certified, "
            "by the in-window continuity rules and the per-symbol NOII cadence; holes outside that "
            "window are declared non-material to this branch's inputs, because no frozen signal "
            "instant, entry instant or exit print lies outside it and a book reconstructed from "
            "the window cannot observe pre-window state in any case."
        ),
    }
    certificate = {
        "certificate_id": "AUCTION-MEASUREMENT-WINDOW-CERTIFICATE-v2",
        "branch": "AUCTION",
        "candidate_id": "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
        "session_date": "2026-06-12",
        "generated_utc": None,
        "transport_markers": transport,
        "artefact_identity": identity,
        "measurement_window_continuity": continuity,
        "universe_repair": universe_repair,
        "coverage_certificate": coverage,
        "verdict": verdict,
    }
    return certificate, states


def write_extract(path: str, rows: list[dict]) -> str:
    fields = (
        "locate",
        "symbol",
        "universe_qualified",
        "directory_failure",
        "closing_cross_valid",
        "closing_cross_shares",
        "closing_cross_price_raw",
        "closing_cross_ts_ns",
        "read_1550_ts_ns",
        "read_1550_source",
        "read_1550_paired_shares",
        "read_1550_imbalance_shares",
        "read_1550_direction",
        "read_1550_reference_price_raw",
        "read_1550_near_price_raw",
        "read_1550_far_price_raw",
        "c_reads_signal_interval",
        "c_max_gap_signal_interval_ns",
        "c_cadence_ok",
        "read_1555_ts_ns",
        "read_1555_paired_shares",
        "read_1555_imbalance_shares",
        "read_1555_direction",
        "read_1555_reference_price_raw",
        "read_1555_near_price_raw",
        "read_1555_far_price_raw",
        "in_denominator",
        "in_numerator",
        "signal_defined",
        "exclusion_reason",
        "signal_scope_reason",
    )
    payload = [{field: row[field] for field in fields} for row in rows]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=0, sort_keys=True)
        handle.write("\n")
    return _sha256_file(path)


# ---------------------------------------------------------------------------
# Negative control: the known splice attack
# ---------------------------------------------------------------------------


def _trim_to_frame_boundary(data: bytes) -> bytes:
    pos, n = 0, len(data)
    while pos + 2 <= n:
        declared = (data[pos] << 8) | data[pos + 1]
        if declared == 0:
            pos += 2
            continue
        end = pos + 2 + declared
        if end > n:
            break
        pos = end
    return bytes(data[:pos])


def _trim_tail_aligned(data: bytes, pad: int = 64) -> bytes | None:
    n = len(data)
    for off in range(min(pad, n)):
        pos = off
        ok = True
        while pos + 2 <= n:
            declared = (data[pos] << 8) | data[pos + 1]
            if declared == 0:
                pos += 2
                continue
            end = pos + 2 + declared
            if end > n:
                ok = False
                break
            if declared != itch.MSG_LENGTH.get(data[pos + 2], None):
                ok = False
                break
            pos = end
        if ok and pos == n and n - off >= 14 and data[n - 12] == 0x53 and data[n - 1] == ord("C"):
            return bytes(data[off:])
    return None


def splice_negative_control(window_path: str, *, keep_bytes: int = 8 << 20) -> dict:
    """Rebuild the known splice attack and certify it.

    Construction is the V2 script's: the first and last ``keep_bytes`` of DECODED
    frames, cut on frame boundaries, the terminal ``C`` kept, re-compressed as a
    fresh single-member gzip. The attack exists precisely because every transport
    marker still passes; the certificate must fail it on the window rules.
    """
    decompressor = zlib.decompressobj(window.GZIP_WINDOW)
    head = bytearray()
    tail = bytearray()
    decoded = 0
    with open(window_path, "rb") as handle:
        while True:
            block = handle.read(1 << 22)
            if not block:
                break
            data = decompressor.decompress(block)
            decoded += len(data)
            if len(head) < keep_bytes:
                head += data[: keep_bytes - len(head)]
            tail += data
            if len(tail) > keep_bytes:
                del tail[: len(tail) - keep_bytes]
    head_trimmed = _trim_to_frame_boundary(head)
    tail_trimmed = _trim_tail_aligned(bytes(tail))
    if tail_trimmed is None:  # pragma: no cover - depends on the artefact's last frame
        raise RuntimeError("could not align the decoded tail to a frame boundary")
    spliced = head_trimmed + tail_trimmed

    scratch = os.path.join(os.path.dirname(os.path.abspath(window_path)), "nc_spliced_window.bin.gz")
    with open(scratch, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6) as gz:
            gz.write(spliced)
    certificate, _states = build_certificate(
        scratch, expected_decoded_bytes=decoded, declared_in_window_messages=None
    )
    sha = _sha256_file(scratch)
    os.remove(scratch)

    transport = certificate["transport_markers"]
    continuity = certificate["measurement_window_continuity"]
    return {
        "control_id": "SPLICE_NEGATIVE_CONTROL",
        "attack_reference": ".research/m2_bridge_001/verification/V2/v2_auction_contract_attack.py",
        "pristine_decoded_bytes": decoded,
        "spliced_decoded_bytes": len(spliced),
        "spliced_percent_of_pristine": (100.0 * len(spliced) / decoded) if decoded else None,
        "spliced_sha256": sha,
        "transport_markers_verdict": certificate["verdict"]["transport_markers"],
        "transport_markers": {
            "gzip_integrity": transport["gzip_integrity"],
            "framing_errors": transport["framing_errors"],
            "trailing_bytes_after_frames": transport["trailing_bytes_after_frames"],
            "final_frame_is_C_end_of_messages": transport["final_frame_is_C_end_of_messages"],
        },
        "continuity_verdict": certificate["verdict"]["measurement_window_continuity"],
        "continuity": {
            "in_window_messages": continuity["in_window_messages"],
            "in_window_message_pairs": continuity["in_window_message_pairs"],
            "max_in_window_gap_ns": continuity["max_in_window_gap_ns"],
            "monotonic_non_decreasing_exchange_timestamps": continuity[
                "monotonic_non_decreasing_exchange_timestamps"
            ],
        },
        "coverage_verdict": certificate["verdict"]["coverage_certificate"],
        "decoded_bytes_matches_declared": certificate["artefact_identity"][
            "decoded_bytes_matches_declared"
        ],
        "failed_checks": certificate["verdict"]["failed_checks"],
        "flagged": certificate["verdict"]["overall"] == "FAIL",
        "verdict_note": (
            "The splice keeps {:.2%} of the decoded session and still passes every transport "
            "marker, which is why transport markers alone are not a completeness contract. The "
            "certificate refuses it on three independent grounds: it carries {} messages inside "
            "15:49:50-16:00:10 ET where the real session carries at least {}; its largest "
            "in-window inter-message gap is {:.3f} s against a 1 s bound; and its decoded size is "
            "not the retained artefact's.".format(
                (len(spliced) / decoded) if decoded else 0.0,
                continuity["in_window_messages"],
                MIN_IN_WINDOW_MESSAGES,
                continuity["max_in_window_gap_ns"] / 1e9,
            )
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window", default=WINDOW_ARTIFACT)
    parser.add_argument("--out", required=True, help="certificate JSON path")
    parser.add_argument("--extract", default=None, help="per-symbol extract JSON path")
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument("--expected-decoded-bytes", type=int, default=None)
    parser.add_argument("--declared-in-window-messages", type=int, default=None)
    parser.add_argument("--declared-received-bytes", type=int, default=None)
    parser.add_argument("--declared-content-range-total", type=int, default=None)
    parser.add_argument("--negative-control", action="store_true")
    arguments = parser.parse_args(argv)

    certificate, states = build_certificate(
        arguments.window,
        expected_sha256=arguments.expected_sha256,
        expected_decoded_bytes=arguments.expected_decoded_bytes,
        declared_in_window_messages=arguments.declared_in_window_messages,
        declared_received_bytes=arguments.declared_received_bytes,
        declared_content_range_total=arguments.declared_content_range_total,
    )
    if arguments.negative_control:
        certificate["splice_negative_control"] = splice_negative_control(arguments.window)
    certificate["generated_utc"] = (
        datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    )
    with open(arguments.out, "w", encoding="utf-8") as handle:
        json.dump(certificate, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(f"certificate -> {arguments.out} sha256={_sha256_file(arguments.out)}")
    print(json.dumps(certificate["verdict"], indent=1, sort_keys=True))
    if arguments.extract:
        sha = write_extract(arguments.extract, certificate_rows(states))
        print(f"extract -> {arguments.extract} sha256={sha}")
    if "splice_negative_control" in certificate:
        control = certificate["splice_negative_control"]
        print(
            "negative control: transport={} continuity={} flagged={} sha256={}".format(
                control["transport_markers_verdict"],
                control["continuity_verdict"],
                control["flagged"],
                control["spliced_sha256"],
            )
        )
    return 0 if certificate["verdict"]["overall"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
