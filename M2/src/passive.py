"""Deterministic queue-aware passive execution replay (M2-1).

Purpose
-------
Answer one question on the existing development tape: if a passive order joins the actual
historical queue at the decision instant, when and why does it fill, and what is left of the
value after the market has selected that fill?

What the model does and does not claim
--------------------------------------
* The Nasdaq TotalView-ITCH feed carries the **displayed** book with per-order identity: adds
  (A/F), executions (E/C), partial cancels (X), deletes (D) and cancel-replaces (U with a new
  reference number). Time priority among displayed orders at one price is therefore
  DETERMINISTIC_FROM_FEED: the feed order is the engine order.
* A hypothetical order joins at the **back** of its price level, so everything resting there at
  submission is ahead of it and nothing arriving later is. Queue advancement is tracked per
  reference number through a global arrival sequence, so an execution or cancellation of an
  order that arrived later can never advance our position.
* A fill requires that the displayed quantity ahead has actually been consumed or removed and
  that real executable flow reaches our position. Nothing is filled probabilistically, and a
  print at our price with quantity still ahead of us does not fill us.
* Non-displayed interest is invisible in this feed: `P` messages are matches of non-displayable
  orders and carry no book identity. Under price-display-time ranking a displayed order cannot
  be jumped by non-displayed interest at the same price, so the primary model does not fill from
  `P` flow. That makes the primary model OPTIMISTIC on fill count; hidden flow at our price
  level is counted per attempt so the size of the assumption is measurable.

This module never writes into the M2-0 or M2-0.6 artifact directories.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import json
import os
import time
from collections import deque

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from . import config as config_module
from . import ingest
from .book import SIDE_ASK, SIDE_BID, SymbolBook

NS_PER_MS = 1_000_000

TYPE_ADD = 0x41
TYPE_ADD_MPID = 0x46
TYPE_EXECUTED = 0x45
TYPE_EXECUTED_WITH_PRICE = 0x43
TYPE_CANCEL = 0x58
TYPE_DELETE = 0x44
TYPE_REPLACE = 0x55
TYPE_TRADE = 0x50
TYPE_CROSS = 0x51
TYPE_TRADING_ACTION = 0x48

R_ORDER_REF = 11
R_SIDE = 19
R_SHARES_ADD = 20
R_PRICE_ADD = 32
R_EXECUTED = 19
R_CANCEL = 19
R_NEW_REF = 19
R_SHARES_REPLACE = 27
R_PRICE_REPLACE = 31
R_SHARES_TRADE = 20
R_PRICE_TRADE = 32

KIND_EXIT = 0
KIND_TTL = 1

EXIT_HORIZONS_MS = (10, 25, 50, 100, 250, 500, 1000)

ATTEMPT_SCHEMA = [
    ("attempt_id", pa.int64()),
    ("ts_ns", pa.int64()),
    ("locate", pa.int32()),
    ("symbol", pa.string()),
    ("side", pa.int8()),
    ("price_raw", pa.int32()),
    ("size", pa.int32()),
    ("queue_ahead_shares", pa.int64()),
    ("queue_ahead_orders", pa.int32()),
    ("queue_position_percentile", pa.float32()),
    ("imbalance", pa.float32()),
    ("spread_raw", pa.int32()),
    ("mid2_raw", pa.int64()),
    ("price_usd", pa.float64()),
    ("filled_shares", pa.int32()),
    ("fill_count", pa.int32()),
    ("first_fill_ts_ns", pa.int64()),
    ("last_fill_ts_ns", pa.int64()),
    ("time_to_first_fill_ns", pa.int64()),
    ("filled_price_raw", pa.int32()),
    ("terminal_reason", pa.string()),
    ("queue_ahead_at_fill", pa.int64()),
    ("hidden_flow_at_level_shares", pa.int64()),
    ("executed_shares_at_level", pa.int64()),
    ("priority_anomalies", pa.int32()),
    ("mid2_at_fill", pa.int64()),
] + [
    (f"exit_{side}_{horizon}ms", pa.int32())
    for horizon in EXIT_HORIZONS_MS
    for side in ("bid", "ask")
]

MODEL = {
    "order_size_shares": 100,
    "order_side_rule": "sign(queue_imbalance); no order is submitted when imbalance == 0",
    "order_price_rule": "join the near touch: best bid for a buy, best ask for a sell",
    "queue_ahead_rule": "every displayed order resting at that price level at submission is "
                        "ahead of us; nothing arriving later is",
    "fill_rule": "fill only against executions (E/C) at our price level, in file order, after "
                 "the displayed quantity ahead of us has been consumed or removed and real "
                 "executable flow reaches our position; no fill from non-displayed trade "
                 "prints; no probabilistic fills",
    "partial_fill_rule": "fill quantity is bounded by the aggressor's executed shares and by "
                         "our remaining size",
    "ttl_ns": 1_000_000_000,
    "cancellation_policy": "none beyond TTL: no signal-based cancel, so no cancel-latency "
                           "assumption enters the primary result",
    "exit_rule": "aggressive exit at the prevailing executable quote at fill + horizon; sell "
                 "at the best bid after a buy fill, buy at the best ask after a sell fill",
    "exit_horizons_ms": list(EXIT_HORIZONS_MS),
    "fill_model": "fifo",
    "fill_model_note": "fifo: a fill requires the displayed quantity ahead of us to be consumed "
                       "or removed first (the conservative model). no_queue: the optimistic "
                       "upper bound, in which any execution at our price level reaches us "
                       "immediately, i.e. the queue-position penalty is set to zero. The two "
                       "bracket the truth and are never mixed in one number.",
    "scope_primary": "the 33 rule-conformant large-tick names of the M2-0.6 single-day proxy",
    "scope_secondary": "all 115 replayed names of the M2-0.6 liquidity scope",
}


class Hypothesis:
    """One hypothetical passive order and its queue position."""

    __slots__ = ("attempt_id", "locate", "symbol", "side", "price", "size", "remaining",
                 "submit_ns", "deadline_ns", "join_seq", "ahead_size", "n_ahead",
                 "filled", "fill_count", "first_fill_ns", "last_fill_ns", "fill_price_raw",
                 "terminal", "queue_ahead_at_fill", "hidden_flow", "executed_at_level",
                 "anomalies", "mid2_at_fill", "exits", "exit_scheduled", "retired")

    def __init__(self, attempt_id, locate, symbol, side, price, size, submit_ns, deadline_ns,
                 join_seq, ahead_size, n_ahead):
        self.attempt_id = attempt_id
        self.locate = locate
        self.symbol = symbol
        self.side = side
        self.price = price
        self.size = size
        self.remaining = size
        self.submit_ns = submit_ns
        self.deadline_ns = deadline_ns
        self.join_seq = join_seq
        self.ahead_size = ahead_size
        self.n_ahead = n_ahead
        self.filled = 0
        self.fill_count = 0
        self.first_fill_ns = 0
        self.last_fill_ns = 0
        self.fill_price_raw = 0
        self.terminal = ""
        self.queue_ahead_at_fill = -1
        self.hidden_flow = 0
        self.executed_at_level = 0
        self.anomalies = 0
        self.mid2_at_fill = 0
        self.exits: dict = {}
        self.exit_scheduled = False
        self.retired = False


class PassiveReplayer:
    def __init__(self, configuration: dict, schedule: dict, directory: dict, model: dict,
                 trace_anomalies: int = 0, limit_messages: int = 0) -> None:
        self.configuration = configuration
        self.model = model
        self.session_start = int(configuration["session"]["continuous_start_ns"])
        self.session_end = int(configuration["session"]["continuous_end_ns"])
        self.ttl_ns = int(model["ttl_ns"])
        self.size = int(model["order_size_shares"])
        self.exit_ns = [int(h) * NS_PER_MS for h in model["exit_horizons_ms"]]
        self.books = {locate: SymbolBook(locate, directory[locate]["symbol"]) for locate in schedule["locates"]}
        self.symbol_name = {locate: directory[locate]["symbol"] for locate in schedule["locates"]}
        self.orders: dict[int, list] = {}
        self.sequence: dict[int, int] = {}
        self.fifo: dict[tuple[int, int], deque] = {}
        self.aggregate: dict[tuple[int, int], int] = {}
        self.active: dict[int, list] = {locate: [] for locate in schedule["locates"]}
        self.heap: list = []
        self.attempts: list[dict] = []
        self.arrival_counter = 0
        self.schedule = schedule
        self.trace_anomalies = trace_anomalies
        self.trace_mismatches = False
        self.verify_levels = False
        self.level_divergences: list = []
        self.trace_lines: list = []
        self.limit_messages = limit_messages
        self.audit = {
            "messages": 0, "frames_verified": 0,
            "attempts": 0, "attempts_skipped_no_quote": 0, "attempts_skipped_zero_imbalance": 0,
            "fill_events": 0, "fill_shares": 0, "attempts_with_fill": 0,
            "attempts_partial_only": 0, "attempts_complete": 0, "attempts_no_fill": 0,
            "ttl_expired": 0, "session_end_open": 0,
            "priority_anomalies": 0, "priority_anomaly_shares": 0,
            "hidden_flow_shares": 0, "executed_shares_at_level": 0,
            "exits_resolved": 0, "exits_unavailable": 0, "fills_without_post_fill_mid": 0,
            "exit_lag_ns_sum": 0, "exit_lag_ns_max": 0, "exit_lag_count": 0,
            "orphan_executes": 0, "orphan_cancels": 0, "orphan_deletes": 0,
            "orphan_replaces": 0, "duplicate_add_refs": 0, "level_aggregate_mismatches": 0,
            "level_state_mismatches": 0,
            "halts": 0, "cross_messages": 0,
        }
        self.summary: dict = {}

    # ------------------------------------------------------------------ level bookkeeping
    def _key(self, locate: int, side: int, price: int) -> tuple[int, int, int]:
        """Level identity is (symbol, side, price).

        A price is not unique across symbols: two Nasdaq names can both quote $212.50, and a
        global (side, price) key silently merges their queues, inflating the quantity ahead of a
        hypothetical order. That defect was found on the real tape and is pinned by
        `level_state_mismatches`, which compares this accounting against each symbol's own book.
        """
        return (locate, side, price)

    def _level_add(self, locate: int, side: int, price: int, size: int) -> None:
        key = self._key(locate, side, price)
        self.aggregate[key] = self.aggregate.get(key, 0) + size

    def _level_remove(self, locate: int, side: int, price: int, size: int) -> None:
        key = self._key(locate, side, price)
        current = self.aggregate.get(key, 0)
        if size > current:
            self.audit["level_aggregate_mismatches"] += 1
        remaining = current - size
        if remaining > 0:
            self.aggregate[key] = remaining
        else:
            self.aggregate.pop(key, None)

    def _fifo_push(self, locate: int, side: int, price: int, ref: int) -> None:
        self.fifo.setdefault(self._key(locate, side, price), deque()).append(ref)

    def _fifo_drop(self, locate: int, side: int, price: int, ref: int) -> None:
        key = self._key(locate, side, price)
        fifo = self.fifo.get(key)
        if fifo is None:
            return
        try:
            fifo.remove(ref)
        except ValueError:
            pass
        if not fifo:
            self.fifo.pop(key, None)

    # ------------------------------------------------------------------ submission
    def _submit(self, locate: int, instant_ns: int, imbalance: float) -> None:
        if imbalance == 0 or not np.isfinite(imbalance):
            self.audit["attempts_skipped_zero_imbalance"] += 1
            return
        book = self.books[locate]
        side = SIDE_BID if imbalance > 0 else SIDE_ASK
        price = book.best_bid if side == SIDE_BID else book.best_ask
        other = book.best_ask if side == SIDE_BID else book.best_bid
        if price is None or other is None:
            self.audit["attempts_skipped_no_quote"] += 1
            return
        key = self._key(locate, side, price)
        ahead_size = self.aggregate.get(key, 0)
        levels = book.bids if side == SIDE_BID else book.asks
        book_level = levels.get(price, 0)
        if book_level != ahead_size:
            # The queue-accounting aggregate and the quote book must be the same number; any
            # divergence is a bookkeeping defect, reported rather than absorbed.
            self.audit["level_state_mismatches"] += 1
            if len(self.trace_lines) < self.trace_anomalies and self.trace_mismatches:
                truth = 0
                count = 0
                for other_ref, entry in self.orders.items():
                    if entry[0] == side and entry[1] == price:
                        truth += entry[2]
                        count += 1
                self.trace_lines.append({
                    "kind": "level_mismatch", "locate": locate, "symbol": self.symbol_name.get(locate, ""),
                    "side": side, "price": price, "book_level": book_level, "aggregate_level": ahead_size,
                    "order_map_truth": truth, "order_map_refs": count,
                    "best_bid": book.best_bid, "best_ask": book.best_ask,
                    "level_is_best": book.best_bid == price if side == SIDE_BID else book.best_ask == price,
                })
        fifo = self.fifo.get(key)
        n_ahead = len(fifo) if fifo else 0
        attempt_id = len(self.attempts)
        hypo = Hypothesis(
            attempt_id=attempt_id, locate=locate, symbol=self.symbol_name[locate], side=side,
            price=price, size=self.size, submit_ns=instant_ns,
            deadline_ns=instant_ns + self.ttl_ns, join_seq=self.arrival_counter,
            ahead_size=ahead_size, n_ahead=n_ahead,
        )
        self.active[locate].append(hypo)
        heapq.heappush(self.heap, (hypo.deadline_ns, KIND_TTL, attempt_id))
        self.audit["attempts"] += 1
        self.attempts.append({
            "attempt_id": attempt_id,
            "ts_ns": instant_ns,
            "locate": locate,
            "symbol": hypo.symbol,
            "side": 1 if side == SIDE_BID else -1,
            "price_raw": price,
            "size": self.size,
            "queue_ahead_shares": ahead_size,
            "queue_ahead_orders": n_ahead,
            "queue_position_percentile": (
                float(ahead_size) / float(ahead_size + self.size)
                if ahead_size + self.size > 0 else 0.0
            ),
            "imbalance": float(imbalance),
            "spread_raw": (other - price) if side == SIDE_BID else (price - other),
            "mid2_raw": price + other,
            "price_usd": (price + other) / 2.0 / float(self.configuration["price_scale"]),
            "_hypo": hypo,
        })

    # ------------------------------------------------------------------ fills
    def _on_execution(self, locate: int, ref: int, shares: int, timestamp: int) -> None:
        fill_model = self.model.get("fill_model", "fifo")
        entry = self.orders.get(ref)
        if entry is None:
            self.audit["orphan_executes"] += 1
            return
        side, price, remaining = entry
        executed = min(shares, remaining)
        self._level_remove(locate, side, price, executed)
        # The quote book must be reduced too: every other level-affecting event does this, and
        # omitting it here leaves phantom quantity at executed prices, which corrupts the touch,
        # the mid and every exit price downstream.
        self.books[locate].reduce(side, price, executed)
        seq = self.sequence.get(ref)
        if remaining - executed <= 0:
            self.orders.pop(ref, None)
            self.sequence.pop(ref, None)
            self._fifo_drop(locate, side, price, ref)
        else:
            entry[2] = remaining - executed
        if self.audit["level_aggregate_mismatches"] and False:  # pragma: no cover
            pass

        for hypo in self.active.get(locate, ()):
            if hypo.retired or hypo.price != price or hypo.side != side or hypo.remaining <= 0:
                continue
            hypo.executed_at_level += executed
            self.audit["executed_shares_at_level"] += executed
            if fill_model == "no_queue":
                # Optimistic upper bound: the queue-position penalty is set to zero, so any
                # execution at our price level reaches us immediately. This is not a claim about
                # the venue; it is the bound that keeps the identifiability gap from hiding a
                # viable strategy.
                hypo.ahead_size = 0
                self._fill(hypo, timestamp, price, executed)
                continue
            ahead_before = hypo.ahead_size
            if seq is not None and seq < hypo.join_seq:
                consumed_ahead = min(executed, ahead_before)
                hypo.ahead_size = max(0, ahead_before - consumed_ahead)
                if hypo.ahead_size == 0:
                    hypo.n_ahead = 0
                else:
                    hypo.n_ahead = max(0, hypo.n_ahead - 1)
                excess = executed - consumed_ahead
            else:
                # The execution hit a displayed order that was NOT resting ahead of us.
                if ahead_before > 0:
                    # Quantity that was resting ahead of us was still queued, yet a later
                    # order traded. That is a priority anomaly for this model: count it, do
                    # not silently absorb it.
                    hypo.anomalies += 1
                    self.audit["priority_anomalies"] += 1
                    self.audit["priority_anomaly_shares"] += executed
                    if len(self.trace_lines) < self.trace_anomalies:
                        fifo = self.fifo.get(self._key(locate, side, price))
                        self.trace_lines.append({
                            "kind": "anomaly",
                            "locate": locate,
                            "symbol": self.symbol_name.get(locate, ""),
                            "ts_ns": timestamp,
                            "side": side,
                            "price": price,
                            "executed_ref_seq": seq,
                            "hypo_join_seq": hypo.join_seq,
                            "ahead_size": ahead_before,
                            "ahead_orders": hypo.n_ahead,
                            "level_fifo_len": len(fifo) if fifo else 0,
                            "ref_in_level_fifo": bool(fifo and ref in fifo),
                            "ref_resting_ahead": bool(seq is not None and seq < hypo.join_seq),
                            "executed_shares": executed,
                            "hypo_filled": hypo.filled,
                        })
                excess = executed
            if ahead_before == 0 and excess > 0:
                self._fill(hypo, timestamp, price, excess)

    def _fill(self, hypo: Hypothesis, timestamp: int, price: int, shares: int) -> None:
        take = min(shares, hypo.remaining)
        if take <= 0:
            return
        hypo.remaining -= take
        hypo.filled += take
        hypo.fill_count += 1
        self.audit["fill_events"] += 1
        self.audit["fill_shares"] += take
        if hypo.fill_count == 1:
            hypo.first_fill_ns = timestamp
            hypo.fill_price_raw = price
            hypo.queue_ahead_at_fill = hypo.ahead_size
            mid2 = self.books[hypo.locate].mid2()
            hypo.mid2_at_fill = mid2 or 0
            if not mid2:
                # A fill that leaves its own side of the book empty has no post-fill mid: the
                # markout for that fill is reported as missing, never as a zero.
                self.audit["fills_without_post_fill_mid"] += 1
            hypo.exit_scheduled = True
            for index, horizon_ns in enumerate(self.exit_ns):
                heapq.heappush(self.heap, (timestamp + horizon_ns, KIND_EXIT,
                                           hypo.attempt_id * 100 + index))
        hypo.last_fill_ns = timestamp
        if hypo.remaining == 0:
            hypo.terminal = "COMPLETE_FILL"
            self.audit["attempts_complete"] += 1
            self._retire(hypo)

    def _retire(self, hypo: Hypothesis) -> None:
        if hypo.retired:
            return
        hypo.retired = True
        active = self.active.get(hypo.locate)
        if active and hypo in active:
            active.remove(hypo)

    def _expire(self, attempt_id: int, deadline_ns: int) -> None:
        if attempt_id >= len(self.attempts):
            return
        hypo = self.attempts[attempt_id]["_hypo"]
        if hypo.retired or hypo.remaining <= 0:
            return
        if hypo.filled == 0:
            hypo.terminal = "TTL_EXPIRED_NO_FILL"
            self.audit["ttl_expired"] += 1
            self.audit["attempts_no_fill"] += 1
        else:
            hypo.terminal = "TTL_EXPIRED_PARTIAL"
            self.audit["attempts_partial_only"] += 1
        self._retire(hypo)

    def _resolve_exit(self, payload: int, timestamp: int) -> None:
        attempt_id, index = divmod(payload, 100)
        if attempt_id >= len(self.attempts):
            return
        hypo = self.attempts[attempt_id]["_hypo"]
        book = self.books[hypo.locate]
        horizon = self.model["exit_horizons_ms"][index]
        bid, ask = book.best_bid, book.best_ask
        if bid is None or ask is None or timestamp > self.session_end:
            self.audit["exits_unavailable"] += 1
            return
        hypo.exits[horizon] = (bid, ask)
        self.audit["exits_resolved"] += 1
        if hypo.first_fill_ns:
            lag = timestamp - (hypo.first_fill_ns + self.exit_ns[index])
            if lag >= 0:
                self.audit["exit_lag_ns_sum"] += lag
                self.audit["exit_lag_ns_max"] = max(self.audit["exit_lag_ns_max"], lag)
                self.audit["exit_lag_count"] += 1

    def _verify_touched_level(self, locate: int) -> None:
        """Debug: after every event, the touched levels must agree between the two structures."""
        book = self.books[locate]
        if len(self.level_divergences) >= 8:
            return
        for side, levels in ((SIDE_BID, book.bids), (SIDE_ASK, book.asks)):
            keys = set(levels) | {price for (loc, s, price) in self.aggregate
                                  if s == side and loc == locate}
            for price in keys:
                left = levels.get(price, 0)
                right = self.aggregate.get(self._key(locate, side, price), 0)
                if left != right:
                    truth = sum(entry[2] for entry in self.orders.values()
                                if entry[0] == side and entry[1] == price)
                    self.level_divergences.append({
                        "locate": locate, "symbol": self.symbol_name.get(locate, ""), "side": side,
                        "price": price, "book": left, "aggregate": right, "order_map_truth": truth,
                    })
                    return

    # ------------------------------------------------------------------ pass
    def run(self, raw_path: str) -> None:
        orders = self.orders
        sequence = self.sequence
        aggregate = self.aggregate
        heap = self.heap
        heap_push = heapq.heappush
        heap_pop = heapq.heappop
        session_start = self.session_start
        session_end = self.session_end
        books = self.books
        active = self.active
        pending_heap: list = []
        for locate, rows in self.schedule["by_locate"].items():
            for instant, imbalance in rows:
                heapq.heappush(pending_heap, (instant, locate, imbalance))
        header = ingest.HEADER
        u64 = ingest.U64
        u32 = ingest.U32
        message_lengths = ingest.MSG_LENGTH
        started = time.time()
        with ingest.open_source(raw_path) as handle:
            buffer = bytearray()
            position = 0
            while True:
                block = handle.read(ingest.CHUNK)
                if not block:
                    break
                buffer += block
                view = memoryview(buffer)
                limit = len(view)
                while position + 1 < limit:
                    declared = (view[position] << 8) | view[position + 1]
                    if position + ingest.FRAME_PREFIX + declared > limit:
                        break
                    base = position + ingest.FRAME_PREFIX
                    message_type = view[base]
                    expected = message_lengths.get(message_type)
                    if expected is None:
                        raise ingest.FeedFormatError(
                            f"unknown message type byte 0x{message_type:02x} at offset {base}"
                        )
                    if declared != expected:
                        raise ingest.FeedFormatError(
                            f"framing mismatch: type 0x{message_type:02x} declares {declared}, "
                            f"documented {expected}"
                        )
                    locate, _tracking, ts_hi, ts_lo = header.unpack_from(buffer, base + 1)
                    timestamp = (ts_hi << 16) | ts_lo
                    self.audit["messages"] += 1
                    if self.limit_messages and self.audit["messages"] > self.limit_messages:
                        break
                    self.audit["frames_verified"] += 1

                    # Resolve everything due strictly before this message, using the same
                    # as-of rule as the M2-0 engine: a request at T observes every message
                    # that precedes it in file order with timestamp <= T.
                    while heap and heap[0][0] < timestamp:
                        due, kind, payload = heap_pop(heap)
                        if kind == KIND_TTL:
                            self._expire(payload, due)
                        else:
                            self._resolve_exit(payload, timestamp)

                    # Attempts fire on the global clock, exactly as the M2-0 decision grid did:
                    # every attempt whose instant is strictly before this message is submitted
                    # with its symbol's book as of that instant.
                    if session_start <= timestamp < session_end:
                        while pending_heap and pending_heap[0][0] < timestamp:
                            instant, pending_locate, imbalance = heapq.heappop(pending_heap)
                            self._submit(pending_locate, instant, imbalance)

                    book = books.get(locate)
                    if book is not None:
                        if self.verify_levels:
                            self._verify_touched_level(locate)
                        if message_type == TYPE_ADD or message_type == TYPE_ADD_MPID:
                            ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                            side = SIDE_BID if view[base + R_SIDE] == 0x42 else SIDE_ASK
                            shares = u32.unpack_from(buffer, base + R_SHARES_ADD)[0]
                            price = u32.unpack_from(buffer, base + R_PRICE_ADD)[0]
                            previous = orders.get(ref)
                            if previous is not None:
                                self.audit["duplicate_add_refs"] += 1
                                self._fifo_drop(locate, previous[0], previous[1], ref)
                                self._level_remove(locate, previous[0], previous[1], previous[2])
                                book.reduce(previous[0], previous[1], previous[2])
                                sequence.pop(ref, None)
                            orders[ref] = [side, price, shares]
                            sequence[ref] = self.arrival_counter
                            self.arrival_counter += 1
                            self._level_add(locate, side, price, shares)
                            self._fifo_push(locate, side, price, ref)
                            book.add(side, price, shares)
                        elif message_type == TYPE_EXECUTED or message_type == TYPE_EXECUTED_WITH_PRICE:
                            ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                            shares = u32.unpack_from(buffer, base + R_EXECUTED)[0]
                            self._on_execution(locate, ref, shares, timestamp)
                        elif message_type == TYPE_CANCEL:
                            ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                            cancelled = u32.unpack_from(buffer, base + R_CANCEL)[0]
                            entry = orders.get(ref)
                            if entry is None:
                                self.audit["orphan_cancels"] += 1
                            else:
                                side, price, remaining = entry
                                take = min(cancelled, remaining)
                                self._level_remove(locate, side, price, take)
                                book.reduce(side, price, take)
                                if remaining - take <= 0:
                                    orders.pop(ref, None)
                                    sequence.pop(ref, None)
                                    self._fifo_drop(locate, side, price, ref)
                                else:
                                    entry[2] = remaining - take
                                seq = sequence.get(ref)
                                if seq is not None:
                                    for hypo in active.get(locate, ()):
                                        if (not hypo.retired and hypo.price == price
                                                and hypo.side == side and seq < hypo.join_seq
                                                and hypo.ahead_size > 0):
                                            hypo.ahead_size = max(0, hypo.ahead_size - take)
                        elif message_type == TYPE_DELETE:
                            ref = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                            entry = orders.pop(ref, None)
                            if entry is None:
                                self.audit["orphan_deletes"] += 1
                            else:
                                side, price, remaining = entry
                                seq = sequence.pop(ref, None)
                                self._level_remove(locate, side, price, remaining)
                                book.reduce(side, price, remaining)
                                self._fifo_drop(locate, side, price, ref)
                                if seq is not None:
                                    for hypo in active.get(locate, ()):
                                        if (not hypo.retired and hypo.price == price
                                                and hypo.side == side and seq < hypo.join_seq
                                                and hypo.ahead_size > 0):
                                            hypo.ahead_size = max(0, hypo.ahead_size - remaining)
                        elif message_type == TYPE_REPLACE:
                            original = u64.unpack_from(buffer, base + R_ORDER_REF)[0]
                            replacement = u64.unpack_from(buffer, base + R_NEW_REF)[0]
                            shares = u32.unpack_from(buffer, base + R_SHARES_REPLACE)[0]
                            price = u32.unpack_from(buffer, base + R_PRICE_REPLACE)[0]
                            entry = orders.pop(original, None)
                            if entry is None:
                                self.audit["orphan_replaces"] += 1
                            else:
                                side, old_price, remaining = entry
                                seq = sequence.pop(original, None)
                                self._level_remove(locate, side, old_price, remaining)
                                book.reduce(side, old_price, remaining)
                                self._fifo_drop(locate, side, old_price, original)
                                if seq is not None:
                                    for hypo in active.get(locate, ()):
                                        if (not hypo.retired and hypo.price == old_price
                                                and hypo.side == side and seq < hypo.join_seq
                                                and hypo.ahead_size > 0):
                                            hypo.ahead_size = max(0, hypo.ahead_size - remaining)
                                orders[replacement] = [side, price, shares]
                                sequence[replacement] = self.arrival_counter
                                self.arrival_counter += 1
                                self._level_add(locate, side, price, shares)
                                self._fifo_push(locate, side, price, replacement)
                                book.add(side, price, shares)
                        elif message_type == TYPE_TRADE:
                            shares = u32.unpack_from(buffer, base + R_SHARES_TRADE)[0]
                            price = u32.unpack_from(buffer, base + R_PRICE_TRADE)[0]
                            for hypo in active.get(locate, ()):
                                if (not hypo.retired and hypo.remaining > 0
                                        and hypo.price == price):
                                    hypo.hidden_flow += shares
                                    self.audit["hidden_flow_shares"] += shares
                        elif message_type == TYPE_CROSS:
                            self.audit["cross_messages"] += 1
                        elif message_type == TYPE_TRADING_ACTION:
                            self.audit["halts"] += 1
                    position += ingest.FRAME_PREFIX + declared
                if self.limit_messages and self.audit["messages"] > self.limit_messages:
                    break
                buffer = buffer[position:]
                position = 0
            else:
                ingest.check_no_trailing_bytes(buffer)

        for locate, hypos in active.items():
            for hypo in hypos:
                if not hypo.retired:
                    hypo.terminal = "SESSION_END_OPEN"
                    self.audit["session_end_open"] += 1
                    hypo.retired = True
        self.summary = {
            "elapsed_seconds": time.time() - started,
            "attempts": len(self.attempts),
            "arrival_counter": self.arrival_counter,
        }

    # ------------------------------------------------------------------ rows
    def rows(self) -> list[dict]:
        out = []
        for record in self.attempts:
            hypo = record.pop("_hypo")
            row = dict(record)
            row["filled_shares"] = hypo.filled
            row["fill_count"] = hypo.fill_count
            row["first_fill_ts_ns"] = hypo.first_fill_ns
            row["last_fill_ts_ns"] = hypo.last_fill_ns
            row["time_to_first_fill_ns"] = (
                hypo.first_fill_ns - hypo.submit_ns if hypo.first_fill_ns else 0
            )
            row["filled_price_raw"] = hypo.fill_price_raw
            row["terminal_reason"] = hypo.terminal or "SESSION_END_OPEN"
            row["queue_ahead_at_fill"] = hypo.queue_ahead_at_fill
            row["hidden_flow_at_level_shares"] = hypo.hidden_flow
            row["executed_shares_at_level"] = hypo.executed_at_level
            row["priority_anomalies"] = hypo.anomalies
            row["mid2_at_fill"] = hypo.mid2_at_fill
            for horizon, (bid, ask) in hypo.exits.items():
                row[f"exit_bid_{horizon}ms"] = bid
                row[f"exit_ask_{horizon}ms"] = ask
            out.append(row)
        return out


def build_schedule(decisions_path: str, locates: set[int]) -> dict:
    table = pq.read_table(decisions_path, columns=["ts_ns", "locate", "imbalance"])
    ts = table["ts_ns"].to_numpy(zero_copy_only=False)
    locates_col = table["locate"].to_numpy(zero_copy_only=False)
    imbalance = table["imbalance"].to_numpy(zero_copy_only=False)
    by_locate: dict[int, list] = {locate: [] for locate in locates}
    keep = np.isin(locates_col, np.fromiter(sorted(locates), dtype=locates_col.dtype))
    for index in np.nonzero(keep)[0]:
        value = float(imbalance[index])
        if not np.isfinite(value):
            value = 0.0
        by_locate[int(locates_col[index])].append((int(ts[index]), value))
    return {
        "locates": sorted(locates),
        "by_locate": {locate: deque(sorted(rows)) for locate, rows in by_locate.items()},
    }


def write_parquet(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    columns = {}
    for name, dtype in ATTEMPT_SCHEMA:
        if pa.types.is_integer(dtype):
            columns[name] = pa.array([int(row.get(name, 0)) for row in rows], type=dtype)
        elif pa.types.is_floating(dtype):
            values = [row.get(name) for row in rows]
            columns[name] = pa.array([float("nan") if v is None else float(v) for v in values],
                                     type=dtype)
        else:
            columns[name] = pa.array([row.get(name) for row in rows], type=dtype)
    pq.write_table(pa.table(columns), path)


# ---------------------------------------------------------------------- scope stage
def write_scope_manifest(configuration: dict, config_path: str) -> dict:
    membership = list(csv.DictReader(open(config_module.repo_path(
        configuration["passive"]["large_tick_membership"]
    ), newline="")))
    symbols = {row["symbol"]: int(row["locate"]) for row in membership if row["symbol"]}
    primary = sorted(
        (row["symbol"] for row in membership if row["large_tick_proxy"] == "True"),
    )
    secondary = sorted(symbols)
    payload = {
        "scope_version": "M2-1-PASSIVE-SCOPE-v1",
        "source": {"large_tick_membership": configuration["passive"]["large_tick_membership"],
                   "source_derived_dir": configuration["passive"]["source_derived_dir"]},
        "primary": [{"symbol": symbol, "locate": symbols[symbol]} for symbol in primary],
        "secondary": [{"symbol": symbol, "locate": symbols[symbol]} for symbol in secondary],
        "config_sha256": config_module.sha256_file(config_path),
    }
    path = config_module.repo_path(configuration["passive"]["scope_manifest"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M2-1 passive queue-aware replay.")
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_1_passive.yaml")
    parser.add_argument("--stage", choices=["scope", "replay"], default="replay")
    parser.add_argument("--ttl-ms", type=int, default=0,
                        help="override the frozen TTL for a predeclared diagnostic run")
    parser.add_argument("--scope", choices=["primary", "secondary"], default="secondary",
                        help="which frozen scope to replay")
    parser.add_argument("--fill-model", choices=["fifo", "no_queue"], default="fifo")
    parser.add_argument("--trace-anomalies", type=int, default=0,
                        help="debug: collect this many priority-anomaly traces")
    parser.add_argument("--verify-levels", action="store_true",
                        help="debug: check level agreement after every event")
    parser.add_argument("--trace-mismatches", action="store_true",
                        help="debug: also collect level-accounting mismatch traces")
    parser.add_argument("--limit-messages", type=int, default=0,
                        help="debug: stop after this many messages")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    if arguments.stage == "scope":
        payload = write_scope_manifest(configuration, arguments.config)
        print(json.dumps({"primary": len(payload["primary"]),
                          "secondary": len(payload["secondary"])}, indent=1))
        return 0

    model = dict(MODEL)
    model["fill_model"] = arguments.fill_model
    if arguments.ttl_ms:
        model["ttl_ns"] = arguments.ttl_ms * NS_PER_MS
    configuration["_exit_horizons_ms"] = model["exit_horizons_ms"]

    manifest_path = config_module.repo_path(configuration["passive"]["scope_manifest"])
    manifest = json.load(open(manifest_path))
    scope_key = "primary" if arguments.scope == "primary" else "secondary"
    locates = {int(entry["locate"]) for entry in manifest[scope_key]}
    source_derived = config_module.repo_path(configuration["passive"]["source_derived_dir"])
    schedule = build_schedule(os.path.join(source_derived, "decisions.parquet"), locates)
    raw_path = config_module.repo_path(
        os.path.join(configuration["paths"]["raw_dir"], configuration["dataset"]["raw_files"][0])
    )
    directory = ingest.read_symbol_directory(raw_path)
    replayer = PassiveReplayer(configuration, schedule, directory, model,
                               trace_anomalies=arguments.trace_anomalies,
                               limit_messages=arguments.limit_messages)
    replayer.trace_mismatches = arguments.trace_mismatches
    replayer.verify_levels = arguments.verify_levels
    label = (f"{model['fill_model']}_ttl{int(model['ttl_ns'] // NS_PER_MS)}ms_"
             f"{arguments.scope}")
    print(f"passive replay: {len(locates)} symbols, TTL {model['ttl_ns'] / NS_PER_MS:.0f} ms, "
          f"label {label}", flush=True)
    replayer.run(raw_path)

    derived_out = config_module.repo_path(config_module.derived_dir(configuration))
    os.makedirs(derived_out, exist_ok=True)
    rows = replayer.rows()
    write_parquet(os.path.join(derived_out, f"passive_attempts_{label}.parquet"), rows)
    config_module.write_json(
        os.path.join(derived_out, f"passive_run_summary_{label}.json"),
        {
            "label": label,
            "scope": scope_key,
            "symbols": len(locates),
            "model": model,
            "audit": replayer.audit,
            "summary": replayer.summary,
            "attempts": len(rows),
            "config_sha256": config_module.sha256_file(arguments.config),
            "code_sha256": config_module.sha256_file("M2/src/passive.py"),
            "scope_manifest_sha256": config_module.sha256_file(
                configuration["passive"]["scope_manifest"]
            ),
            "anomaly_traces": replayer.trace_lines,
            "level_divergences": replayer.level_divergences,
        },
    )
    print(json.dumps({"label": label, "attempts": len(rows), **replayer.audit}, indent=1)[:2500])
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
