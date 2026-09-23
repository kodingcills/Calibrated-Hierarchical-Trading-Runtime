"""Data-integrity accounting for the M2-0 pass.

Every counter here exists because the corresponding failure mode would silently
bias the calculation if it were not measured:

* the feed carries no receive clock and no sequence number, so the absent
  contracts are recorded rather than replaced by an assumption (the tracking
  number is audited as an explicitly labelled substitute);
* timestamps are not guaranteed to be globally ordered, so reversals and
  same-timestamp runs are counted and never sorted away;
* the book can only be trusted if orphan events, negative remaining size, order
  reference collisions and crossed/locked states are counted per symbol.

Nothing in this module repairs data. It measures, and it reports.
"""

from __future__ import annotations

import csv
import os
from typing import Iterable, Sequence

# Book-state anomaly kinds counted per symbol.
ANOMALY_KINDS = (
    "orphan_execute",
    "orphan_execute_with_price",
    "orphan_cancel",
    "orphan_delete",
    "orphan_replace",
    "replace_duplicate_new_ref",
    "order_id_collision",
    "negative_remaining",
    "cancel_oversized",
    "implausible_size",
)

# Non-book administrative anomalies worth surfacing.
ADMIN_KINDS = ("trading_action_halt", "trading_action_resume", "operational_halt", "operational_resume")


class SymbolAudit:
    """Per-symbol integrity counters."""

    __slots__ = (
        "symbol",
        "locate",
        "messages",
        "book_messages",
        "reversals",
        "max_reversal_ns",
        "late_after_decision",
        "identical_ts",
        "duplicates_bucket",
        "adds",
        "adds_mpid",
        "executes",
        "executes_with_price",
        "cancels",
        "deletes",
        "replaces",
        "anomalies",
        "crossed_book_updates",
        "locked_book_updates",
        "empty_side_updates",
        "reconciliation_samples",
        "reconciliation_mismatches",
        "live_orders_end",
        "last_event_ns",
    )

    def __init__(self, locate: int, symbol: str = "") -> None:
        self.symbol = symbol
        self.locate = locate
        self.messages = 0
        self.book_messages = 0
        self.reversals = 0
        self.max_reversal_ns = 0
        self.late_after_decision = 0
        self.identical_ts = 0
        self.duplicates_bucket = 0
        self.adds = 0
        self.adds_mpid = 0
        self.executes = 0
        self.executes_with_price = 0
        self.cancels = 0
        self.deletes = 0
        self.replaces = 0
        self.anomalies = {kind: 0 for kind in ANOMALY_KINDS}
        self.crossed_book_updates = 0
        self.locked_book_updates = 0
        self.empty_side_updates = 0
        self.reconciliation_samples = 0
        self.reconciliation_mismatches = 0
        self.live_orders_end = 0
        self.last_event_ns = 0

    def as_row(self) -> dict:
        return {
            "symbol": self.symbol,
            "locate": self.locate,
            "messages": self.messages,
            "book_messages": self.book_messages,
            "timestamp_reversals": self.reversals,
            "max_reversal_ns": self.max_reversal_ns,
            "messages_late_after_decision": self.late_after_decision,
            "identical_timestamp_messages": self.identical_ts,
            "exact_duplicates_within_bucket": self.duplicates_bucket,
            "adds": self.adds,
            "adds_mpid": self.adds_mpid,
            "executes": self.executes,
            "executes_with_price": self.executes_with_price,
            "cancels": self.cancels,
            "deletes": self.deletes,
            "replaces": self.replaces,
            **{f"anomaly_{kind}": value for kind, value in self.anomalies.items()},
            "crossed_book_updates": self.crossed_book_updates,
            "locked_book_updates": self.locked_book_updates,
            "empty_side_updates": self.empty_side_updates,
            "reconciliation_samples": self.reconciliation_samples,
            "reconciliation_mismatches": self.reconciliation_mismatches,
            "live_orders_end_of_day": self.live_orders_end,
        }


class BucketDuplicateDetector:
    """Exact duplicate detection inside an aligned time bucket, O(bucket) memory.

    The tape is hundreds of millions of messages; a whole-tape seen-set is not
    affordable and a hash of every message is not needed to catch the failure
    that matters (a message emitted twice). Duplicates are therefore detected
    exactly within the configured bucket, and the bucket is part of the
    reported contract.
    """

    def __init__(self, bucket_ns: int) -> None:
        self.bucket_ns = bucket_ns
        self.bucket = None
        self.seen: set[int] = set()
        self.duplicates = 0

    def observe(self, timestamp_ns: int, key: bytes) -> bool:
        """``key`` is the raw message payload; a copy is required because a
        writable memoryview is not hashable."""
        bucket = timestamp_ns // self.bucket_ns
        if bucket != self.bucket:
            self.bucket = bucket
            self.seen.clear()
        digest = hash(key)
        if digest in self.seen:
            self.duplicates += 1
            return True
        self.seen.add(digest)
        return False


class TapeAudit:
    """Whole-tape and per-symbol integrity state for one trading day."""

    def __init__(
        self,
        session_start_ns: int,
        session_end_ns: int,
        bucket_ns: int,
        gap_threshold_ns: int,
        tracked_locates: Iterable[int] = (),
    ) -> None:
        self.session_start_ns = session_start_ns
        self.session_end_ns = session_end_ns
        self.bucket_ns = bucket_ns
        self.gap_threshold_ns = gap_threshold_ns
        self.messages = 0
        self.book_messages = 0
        self.reversals = 0
        self.max_reversal_ns = 0
        self.identical_ts = 0
        self.late_after_decision = 0
        self.duplicates_adjacent = 0
        self.tracking_regressions = 0
        self.tracking_gaps = 0
        self.tracking_max_gap = 0
        self.gaps: list[tuple[int, int]] = []
        self.gap_count = 0
        self.largest_gap_ns = 0
        self.session_events: list[tuple[int, str, str]] = []
        self.symbols: dict[int, SymbolAudit] = {
            locate: SymbolAudit(locate) for locate in tracked_locates
        }
        self.detector = BucketDuplicateDetector(bucket_ns)  # per scope symbol
        self.detector_full = BucketDuplicateDetector(bucket_ns)  # whole tape
        self.exact_adjacent_duplicates = 0
        self.exact_bucket_duplicates_full_tape = 0
        self.tuple_key_repeats_adjacent = 0

    def note_message(
        self,
        locate: int,
        timestamp_ns: int,
        previous_ts: int | None,
        tracking_number: int,
        previous_tracking: int | None,
        late_after_decision: bool,
    ) -> None:
        """Whole-tape accounting for one message."""
        self.messages += 1
        if previous_ts is not None:
            if timestamp_ns < previous_ts:
                self.reversals += 1
                delta = previous_ts - timestamp_ns
                if delta > self.max_reversal_ns:
                    self.max_reversal_ns = delta
                if self.session_start_ns <= timestamp_ns < self.session_end_ns:
                    if delta > self.gap_threshold_ns:
                        self.gap_count += 1
                        if delta > self.largest_gap_ns:
                            self.largest_gap_ns = delta
                        if len(self.gaps) < 1000:
                            self.gaps.append((previous_ts, timestamp_ns))
            elif timestamp_ns == previous_ts:
                self.identical_ts += 1
            elif previous_ts < timestamp_ns:
                gap = timestamp_ns - previous_ts
                if gap > self.gap_threshold_ns and self.session_start_ns <= previous_ts < self.session_end_ns:
                    self.gap_count += 1
                    if gap > self.largest_gap_ns:
                        self.largest_gap_ns = gap
                    if len(self.gaps) < 1000:
                        self.gaps.append((previous_ts, timestamp_ns))
        if previous_tracking is not None:
            if tracking_number < previous_tracking:
                self.tracking_regressions += 1
            elif tracking_number > previous_tracking + 1:
                self.tracking_gaps += 1
                delta = tracking_number - previous_tracking
                if delta > self.tracking_max_gap:
                    self.tracking_max_gap = delta
        if late_after_decision:
            self.late_after_decision += 1

    def note_symbol(
        self,
        locate: int,
        timestamp_ns: int,
        previous_symbol_ts: int | None,
        late_after_decision: bool,
        duplicate: bool,
        adjacent_duplicate: bool,
    ) -> None:
        state = self.symbols.get(locate)
        if state is None:
            return
        state.messages += 1
        state.last_event_ns = timestamp_ns
        if previous_symbol_ts is not None:
            if timestamp_ns < previous_symbol_ts:
                state.reversals += 1
                delta = previous_symbol_ts - timestamp_ns
                if delta > state.max_reversal_ns:
                    state.max_reversal_ns = delta
            elif timestamp_ns == previous_symbol_ts:
                state.identical_ts += 1
        if late_after_decision:
            state.late_after_decision += 1
        if duplicate:
            state.duplicates_bucket += 1
        if adjacent_duplicate:
            state.duplicates_adjacent += 1

    def note_system_event(self, timestamp_ns: int, code: str, name: str) -> None:
        self.session_events.append((timestamp_ns, code, name))

    def note_anomaly(self, locate: int, kind: str, magnitude: int = 1) -> None:
        state = self.symbols.get(locate)
        if state is None:
            return
        state.anomalies[kind] = state.anomalies.get(kind, 0) + magnitude

    def totals(self) -> dict:
        return {
            "messages": self.messages,
            "book_messages": self.book_messages,
            "timestamp_reversals": self.reversals,
            "max_reversal_ns": self.max_reversal_ns,
            "identical_timestamp_messages": self.identical_ts,
            "messages_late_after_decision": self.late_after_decision,
            "duplicates_within_bucket": self.detector.duplicates,
            "tracking_number_regressions": self.tracking_regressions,
            "tracking_number_gaps": self.tracking_gaps,
            "tracking_number_max_gap": self.tracking_max_gap,
            "intervals_gt_gap_threshold": self.gap_count,
            "largest_interval_ns": self.largest_gap_ns,
        }


def _write_csv(path: str, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


TIMESTAMP_AUDIT_COLUMNS = [
    "date",
    "scope",
    "symbol",
    "locate",
    "messages",
    "duplicate_check_applied",
    "duplicates_adjacent",
    "duplicates_within_bucket",
    "timestamp_reversals",
    "max_reversal_ns",
    "identical_timestamp_messages",
    "messages_late_after_decision",
    "exact_duplicates_within_bucket_full_tape",
    "tuple_key_repeats_adjacent",
    "receive_clock_present",
    "sequence_number_present",
    "channel_field_present",
]

SEQUENCE_AUDIT_COLUMNS = [
    "date",
    "scope",
    "symbol",
    "locate",
    "sequence_numbers_present",
    "sequence_source",
    "tracking_number_regressions",
    "tracking_number_gaps",
    "tracking_number_max_gap",
    "substitute_check_verdict",
    "note",
]

ORDERING_ANOMALY_COLUMNS = [
    "date",
    "scope",
    "symbol",
    "locate",
    "timestamp_reversals",
    "identical_timestamp_messages",
    "messages_late_after_decision",
    "cross_channel_ordering_ambiguity",
    "canonical_order_source",
    "action_taken",
]

BOOK_AUDIT_COLUMNS = [
    "date",
    "scope",
    "symbol",
    "locate",
    "adds",
    "adds_mpid",
    "executes",
    "executes_with_price",
    "cancels",
    "deletes",
    "replaces",
    "orphan_execute",
    "orphan_execute_with_price",
    "orphan_cancel",
    "orphan_delete",
    "orphan_replace",
    "replace_duplicate_new_ref",
    "order_id_collision",
    "negative_remaining",
    "cancel_oversized",
    "implausible_size",
    "crossed_book_updates",
    "locked_book_updates",
    "empty_side_updates",
    "reconciliation_samples",
    "reconciliation_mismatches",
    "live_orders_end_of_day",
    "verdict",
]

BOOK_CROSSCHECK_COLUMNS = [
    "date",
    "symbol",
    "locate",
    "reference_product",
    "observations",
    "bid_match_rate",
    "ask_match_rate",
    "spread_match_rate",
    "unexplained_mismatches",
    "note",
]


def write_timestamp_audit(path: str, date: str, audit: TapeAudit) -> None:
    rows = []
    for state in audit.symbols.values():
        row = state.as_row()
        rows.append(
            {
                "date": date,
                "scope": "DEV_SCOPE",
                "symbol": row["symbol"],
                "locate": row["locate"],
                "messages": row["messages"],
                "duplicate_check_applied": "WITHIN_100MS_BUCKET_EXACT_PAYLOAD",
                "duplicates_adjacent": "NOT_PER_SYMBOL",
                "duplicates_within_bucket": row["exact_duplicates_within_bucket"],
                "timestamp_reversals": row["timestamp_reversals"],
                "max_reversal_ns": row["max_reversal_ns"],
                "identical_timestamp_messages": row["identical_timestamp_messages"],
                "messages_late_after_decision": row["messages_late_after_decision"],
                "receive_clock_present": "false",
                "sequence_number_present": "false",
                "channel_field_present": "false",
            }
        )
    totals = audit.totals()
    rows.append(
        {
            "date": date,
            "scope": "FULL_TAPE",
            "symbol": "ALL",
            "locate": "",
            "messages": totals["messages"],
            "duplicate_check_applied": "EXACT_PAYLOAD_BOTH_ADJACENT_AND_WITHIN_100MS_BUCKET",
            "duplicates_adjacent": audit.exact_adjacent_duplicates,
            "duplicates_within_bucket": audit.exact_bucket_duplicates_full_tape,
            "tuple_key_repeats_adjacent": audit.tuple_key_repeats_adjacent,
            "exact_duplicates_within_bucket_full_tape": audit.exact_bucket_duplicates_full_tape,
            "timestamp_reversals": totals["timestamp_reversals"],
            "max_reversal_ns": totals["max_reversal_ns"],
            "identical_timestamp_messages": totals["identical_timestamp_messages"],
            "messages_late_after_decision": totals["messages_late_after_decision"],
            "receive_clock_present": "false",
            "sequence_number_present": "false",
            "channel_field_present": "false",
        }
    )
    _write_csv(path, rows, TIMESTAMP_AUDIT_COLUMNS)


def write_sequence_audit(path: str, date: str, audit: TapeAudit) -> None:
    totals = audit.totals()
    note = (
        "The ITCH payload carries no sequence number; sequencing belongs to the transport "
        "wrapper (SoupBinTCP/MoldUDP64) and is absent from a captured file. The tracking number "
        "is audited as a SUBSTITUTE only: it is documented as a Nasdaq-internal tracking number, "
        "not as a sequence contract, so a gap here is reported and not repaired."
    )
    verdict = (
        "MONOTONIC_SUBSTITUTE_OK"
        if totals["tracking_number_regressions"] == 0
        else "SUBSTITUTE_REGRESSIONS_PRESENT"
    )
    rows = [
        {
            "date": date,
            "scope": "FULL_TAPE",
            "symbol": "ALL",
            "locate": "",
            "sequence_numbers_present": "false",
            "sequence_source": "ABSENT_IN_PRODUCT",
            "tracking_number_regressions": totals["tracking_number_regressions"],
            "tracking_number_gaps": totals["tracking_number_gaps"],
            "tracking_number_max_gap": totals["tracking_number_max_gap"],
            "substitute_check_verdict": verdict,
            "note": note,
        }
    ]
    for state in audit.symbols.values():
        rows.append(
            {
                "date": date,
                "scope": "DEV_SCOPE",
                "symbol": state.symbol,
                "locate": state.locate,
                "sequence_numbers_present": "false",
                "sequence_source": "ABSENT_IN_PRODUCT",
                "tracking_number_regressions": "NOT_PER_SYMBOL",
                "tracking_number_gaps": "NOT_PER_SYMBOL",
                "tracking_number_max_gap": "NOT_PER_SYMBOL",
                "substitute_check_verdict": "SEE_FULL_TAPE_ROW",
                "note": "tracking number is a feed-level counter, not a per-symbol sequence",
            }
        )
    _write_csv(path, rows, SEQUENCE_AUDIT_COLUMNS)


def write_ordering_audit(path: str, date: str, audit: TapeAudit) -> None:
    rows = []
    for state in audit.symbols.values():
        row = state.as_row()
        rows.append(
            {
                "date": date,
                "scope": "DEV_SCOPE",
                "symbol": row["symbol"],
                "locate": row["locate"],
                "timestamp_reversals": row["timestamp_reversals"],
                "identical_timestamp_messages": row["identical_timestamp_messages"],
                "messages_late_after_decision": row["messages_late_after_decision"],
                "cross_channel_ordering_ambiguity": "NOT_APPLICABLE_SINGLE_FEED",
                "canonical_order_source": "FILE_ORDER_THEN_TIMESTAMP_AS_OF",
                "action_taken": "NONE_RECORDED_NOT_REPAIRED",
            }
        )
    totals = audit.totals()
    rows.append(
        {
            "date": date,
            "scope": "FULL_TAPE",
            "symbol": "ALL",
            "locate": "",
            "timestamp_reversals": totals["timestamp_reversals"],
            "identical_timestamp_messages": totals["identical_timestamp_messages"],
            "messages_late_after_decision": totals["messages_late_after_decision"],
            "cross_channel_ordering_ambiguity": "NOT_APPLICABLE_SINGLE_FEED",
            "canonical_order_source": "FILE_ORDER_THEN_TIMESTAMP_AS_OF",
            "action_taken": "NONE_RECORDED_NOT_REPAIRED",
        }
    )
    _write_csv(path, rows, ORDERING_ANOMALY_COLUMNS)


def write_book_audit(path: str, date: str, audit: TapeAudit, verdict: str) -> None:
    rows = []
    for state in audit.symbols.values():
        row = state.as_row()
        rows.append(
            {
                "date": date,
                "scope": "DEV_SCOPE",
                "symbol": row["symbol"],
                "locate": row["locate"],
                **{
                    key: row[key]
                    for key in (
                        "adds",
                        "adds_mpid",
                        "executes",
                        "executes_with_price",
                        "cancels",
                        "deletes",
                        "replaces",
                        "crossed_book_updates",
                        "locked_book_updates",
                        "empty_side_updates",
                        "reconciliation_samples",
                        "reconciliation_mismatches",
                        "live_orders_end_of_day",
                    )
                },
                **{k[len("anomaly_"):]: v for k, v in row.items() if k.startswith("anomaly_orphan_")},
                "replace_duplicate_new_ref": row["anomaly_replace_duplicate_new_ref"],
                "order_id_collision": row["anomaly_order_id_collision"],
                "negative_remaining": row["anomaly_negative_remaining"],
                "cancel_oversized": row["anomaly_cancel_oversized"],
                "implausible_size": row["anomaly_implausible_size"],
                "verdict": verdict,
            }
        )
    _write_csv(path, rows, BOOK_AUDIT_COLUMNS)


def write_book_crosscheck(
    path: str,
    date: str,
    rows: Sequence[dict],
    reference_product: str,
    note: str,
) -> None:
    payload = [
        {
            "date": date,
            "symbol": row["symbol"],
            "locate": row["locate"],
            "reference_product": reference_product,
            "observations": row["reconciliation_samples"],
            "bid_match_rate": row["bid_match_rate"],
            "ask_match_rate": row["ask_match_rate"],
            "spread_match_rate": row["spread_match_rate"],
            "unexplained_mismatches": row["unexplained_mismatches"],
            "note": note,
        }
        for row in rows
    ]
    _write_csv(path, payload, BOOK_CROSSCHECK_COLUMNS)
