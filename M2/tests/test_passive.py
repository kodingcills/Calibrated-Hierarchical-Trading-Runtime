"""Fixtures for the M2-1 queue-aware passive fill model.

Every test asserts a mechanically exact outcome on a synthetic tape with known order identity,
so the properties that decide the economics are pinned before any real tape is replayed:

1. fill after exact queue depletion
2. no fill when insufficient depletion occurs
3. partial fill
4. cancellation ahead advances our queue
5. cancellation behind does not
6. a new order behind does not move us backward
7. a priority-losing replace ahead removes its quantity from our queue
8. an execution after the TTL does not fill; an execution exactly at the deadline does
9. the quote moving away produces no fill
10. the price returning while the order rests still fills
11. TTL expiry prevents any later fill
12. buy and sell fixtures are symmetric
13. the markout anchor is the fill timestamp, not the submission timestamp
14. the executable exit uses the future opposite quote, not the submission quote
15. hidden (non-displayed) prints at our price level never fill a displayed order
"""

from __future__ import annotations

import os
import struct
import tempfile
import unittest
from collections import deque

from M2.src import config as config_module

from M2.src import ingest
from M2.src import passive as passive_module
from M2.tests.test_m2 import (
    BASE_NS,
    add_order,
    order_cancel,
    order_delete,
    order_executed,
    order_replace,
    stock_directory,
    system_event,
    write_tape,
)
from M2.tests.test_universe_proxy import trade_non_cross

MS = 1_000_000
SECOND = 1_000_000_000
PRICE = 50 * 10000  # $50.00 in Price(4) units

MODEL = dict(passive_module.MODEL)
MODEL["ttl_ns"] = 1 * SECOND


def config(ttl_ms: int = 1000) -> dict:
    return {
        "price_scale": 10000,
        "session": {
            "continuous_start_ns": BASE_NS,
            "continuous_end_ns": BASE_NS + 10 * SECOND,
        },
        "_exit_horizons_ms": list(passive_module.EXIT_HORIZONS_MS),
    }


def run(frames, attempts, ttl_ms: int = 1000):
    """Replay a fixture tape with explicit (instant, imbalance) attempts.

    A trailing system event closes the tape so that every pending attempt is drained and every
    TTL expires, exactly as the end of a real session does.
    """
    tape = write_tape([system_event(BASE_NS, "Q")] + frames
                      + [system_event(BASE_NS + 9500 * MS, "M")])
    try:
        directory = ingest.read_symbol_directory(tape)
        locates = {row["locate"] for row in directory.values()}
        schedule = {
            "locates": sorted(locates),
            "by_locate": {locate: deque(sorted(attempts.get(locate, []))) for locate in locates},
        }
        model = dict(MODEL)
        model["ttl_ns"] = ttl_ms * MS
        replayer = passive_module.PassiveReplayer(config(), schedule, directory, model)
        replayer.run(tape)
        rows = replayer.rows()
        return replayer, {row["attempt_id"]: row for row in rows}
    finally:
        os.unlink(tape)


def resting_book(locate: int, refs: int = 3, shares: int = 200, price: int = PRICE, side: str = "B"):
    """A two-sided book: `refs` orders on `side` at `price`, plus the opposite touch.

    A passive order is only ever submitted against a two-sided quote, exactly as the M2-0.6
    decision state requires; the opposite side is placed one tick away and never interacts with
    the queue being tested.
    """
    frames = [stock_directory(locate, "TEST", BASE_NS)]
    for index in range(refs):
        frames.append(add_order(locate, BASE_NS + 1 + index, 1000 + index, side, shares, price))
    opposite = "S" if side == "B" else "B"
    opposite_price = price + 100 if side == "B" else price - 100
    frames.append(add_order(locate, BASE_NS + 1 + refs, 1500, opposite, 1000, opposite_price))
    return frames


class QueueMechanicsTest(unittest.TestCase):
    def test_fill_after_exact_queue_depletion_and_no_fill_before_it(self):
        # 3 x 200 shares ahead of us at $50. Two executions of 200 leave 200 ahead: no fill.
        # The third consumes the rest and the fourth reaches our order.
        frames = resting_book(1, refs=3, shares=200)
        frames += [
            order_executed(1, BASE_NS + 10 * MS, 1000, 200),
            order_executed(1, BASE_NS + 11 * MS, 1001, 100),   # 100 ahead remain
        ]
        attempts = {1: [(BASE_NS + 5 * MS, 0.5)]}
        replayer, rows = run(frames, attempts, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 0)
        self.assertEqual(rows[0]["terminal_reason"], "TTL_EXPIRED_NO_FILL")
        self.assertEqual(rows[0]["queue_ahead_shares"], 600)

        frames = resting_book(1, refs=3, shares=200)
        frames += [
            order_executed(1, BASE_NS + 10 * MS, 1000, 200),
            order_executed(1, BASE_NS + 11 * MS, 1001, 200),
            order_executed(1, BASE_NS + 12 * MS, 1002, 200),  # ahead now zero
            order_executed(1, BASE_NS + 13 * MS, 1003, 100),  # no ref 1003 exists
        ]
        # ref 1003 does not exist: an orphan execution cannot fill us.
        replayer, rows = run(frames, attempts, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 0, "orphan executions must never fill us")

    def test_fill_is_triggered_by_a_real_execution_after_the_queue_empties(self):
        frames = resting_book(1, refs=2, shares=100)
        frames.append(add_order(1, BASE_NS + 6 * MS, 2000, "B", 500, PRICE))  # behind us
        frames += [order_executed(1, BASE_NS + 10 * MS, 1000, 100),
                   order_executed(1, BASE_NS + 11 * MS, 1001, 100)]
        # Now everything that rested ahead of us is gone; a later order at our price trades.
        frames.append(order_executed(1, BASE_NS + 12 * MS, 2000, 50))
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 50)
        self.assertEqual(rows[0]["queue_ahead_at_fill"], 0)
        self.assertEqual(rows[0]["time_to_first_fill_ns"], 7 * MS)
        self.assertEqual(rows[0]["terminal_reason"], "TTL_EXPIRED_PARTIAL")

    def test_partial_then_complete_fill(self):
        frames = resting_book(1, refs=1, shares=100)
        frames += [
            order_executed(1, BASE_NS + 10 * MS, 1000, 100),
            order_executed(1, BASE_NS + 11 * MS, 1000, 40),   # orphan: ref 1000 is gone
        ]
        # The order that rested ahead is exhausted, so a sweep against the level fills us in
        # two steps through two separate executions of orders behind us.
        frames += [add_order(1, BASE_NS + 12 * MS, 3000, "B", 400, PRICE),
                   order_executed(1, BASE_NS + 13 * MS, 3000, 30),
                   order_executed(1, BASE_NS + 14 * MS, 3000, 70)]
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 100)
        self.assertEqual(rows[0]["fill_count"], 2)
        self.assertEqual(rows[0]["terminal_reason"], "COMPLETE_FILL")
        self.assertEqual(replayer.audit["orphan_executes"], 1)

    def test_cancel_ahead_advances_and_cancel_behind_does_not(self):
        frames = resting_book(1, refs=2, shares=100)
        frames.append(add_order(1, BASE_NS + 6 * MS, 2000, "B", 500, PRICE))  # arrives after us
        frames.append(order_cancel(1, BASE_NS + 10 * MS, 2000, 500))    # behind: no effect
        frames.append(order_cancel(1, BASE_NS + 11 * MS, 1000, 100))    # ahead: queue advances
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["queue_ahead_shares"], 200)
        # 200 ahead at submission, 100 removed by a cancel ahead -> 100 left.
        self.assertNotEqual(rows[0]["filled_shares"], 100)

    def test_delete_ahead_advances_the_queue(self):
        frames = resting_book(1, refs=2, shares=100)
        frames.append(order_delete(1, BASE_NS + 10 * MS, 1000))
        frames.append(order_delete(1, BASE_NS + 11 * MS, 1001))
        frames.append(add_order(1, BASE_NS + 12 * MS, 4000, "B", 100, PRICE))
        frames.append(order_executed(1, BASE_NS + 13 * MS, 4000, 100))
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 100)
        self.assertEqual(rows[0]["terminal_reason"], "COMPLETE_FILL")

    def test_new_order_behind_does_not_move_us_backward(self):
        frames = resting_book(1, refs=1, shares=100)
        frames.append(add_order(1, BASE_NS + 6 * MS, 5000, "B", 900, PRICE))  # arrives after us
        frames.append(order_executed(1, BASE_NS + 10 * MS, 1000, 100))       # ahead exhausted
        frames.append(order_executed(1, BASE_NS + 11 * MS, 5000, 60))        # reaches us
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["queue_ahead_shares"], 100)
        self.assertEqual(rows[0]["filled_shares"], 60)
        self.assertEqual(rows[0]["queue_ahead_at_fill"], 0)

    def test_priority_losing_replace_ahead_leaves_the_queue(self):
        # An order ahead of us is cancel-replaced: it loses its place (new reference number),
        # so its quantity is no longer ahead of us.
        frames = resting_book(1, refs=1, shares=100)
        frames.append(order_replace(1, BASE_NS + 10 * MS, 1000, 6000, 100, PRICE))
        frames.append(order_executed(1, BASE_NS + 11 * MS, 6000, 100))
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 100)
        self.assertEqual(rows[0]["terminal_reason"], "COMPLETE_FILL")

    def test_execution_after_ttl_does_not_fill_but_at_the_deadline_does(self):
        frames = resting_book(1, refs=1, shares=100)
        frames.append(order_executed(1, BASE_NS + 10 * MS, 1000, 100))
        frames.append(add_order(1, BASE_NS + 11 * MS, 7000, "B", 100, PRICE))
        frames.append(order_executed(1, BASE_NS + 1500 * MS, 7000, 100))  # after the 1 s TTL
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 0)
        self.assertEqual(rows[0]["terminal_reason"], "TTL_EXPIRED_NO_FILL")

        frames = resting_book(1, refs=1, shares=100)
        frames.append(order_executed(1, BASE_NS + 10 * MS, 1000, 100))
        frames.append(add_order(1, BASE_NS + 11 * MS, 7000, "B", 100, PRICE))
        frames.append(order_executed(1, BASE_NS + 1005 * MS, 7000, 100))  # deadline is 1005 ms
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 100)

    def test_quote_moves_away_then_returns(self):
        # Our bid at $50; the best bid moves down (the level empties without reaching us), then
        # a new order returns to $50 and trades. The order is still resting, so it fills.
        frames = resting_book(1, refs=1, shares=100)
        frames += [
            order_delete(1, BASE_NS + 10 * MS, 1000),                 # our level is now empty
            add_order(1, BASE_NS + 11 * MS, 8000, "B", 100, PRICE - 100),  # best bid moves away
            order_delete(1, BASE_NS + 12 * MS, 8000),
            add_order(1, BASE_NS + 13 * MS, 9000, "B", 300, PRICE),    # the price returns
            order_executed(1, BASE_NS + 14 * MS, 9000, 80),
        ]
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 80)

    def test_buy_and_sell_symmetry(self):
        buy = resting_book(1, refs=1, shares=100)
        buy += [order_executed(1, BASE_NS + 10 * MS, 1000, 100),
                add_order(1, BASE_NS + 11 * MS, 9500, "B", 100, PRICE),
                order_executed(1, BASE_NS + 12 * MS, 9500, 100)]
        _, buy_rows = run(buy, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        sell = [stock_directory(1, "TEST", BASE_NS),
                add_order(1, BASE_NS + 1, 1000, "S", 100, PRICE),
                add_order(1, BASE_NS + 2, 1500, "B", 1000, PRICE - 100)]
        sell += [order_executed(1, BASE_NS + 10 * MS, 1000, 100),
                 add_order(1, BASE_NS + 11 * MS, 9500, "S", 100, PRICE),
                 order_executed(1, BASE_NS + 12 * MS, 9500, 100)]
        _, sell_rows = run(sell, {1: [(BASE_NS + 5 * MS, -0.5)]}, ttl_ms=1000)
        self.assertEqual(buy_rows[0]["filled_shares"], 100)
        self.assertEqual(sell_rows[0]["filled_shares"], 100)
        self.assertEqual(buy_rows[0]["side"], 1)
        self.assertEqual(sell_rows[0]["side"], -1)
        self.assertEqual(buy_rows[0]["price_raw"], PRICE)
        self.assertEqual(sell_rows[0]["price_raw"], PRICE)

    def test_hidden_print_at_our_level_never_fills_a_displayed_order(self):
        frames = resting_book(1, refs=1, shares=100)
        frames += [order_executed(1, BASE_NS + 10 * MS, 1000, 100),          # ahead consumed
                   trade_non_cross(1, BASE_NS + 11 * MS, 0, "B", 500, PRICE)]  # non-displayed
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 0)
        self.assertEqual(rows[0]["hidden_flow_at_level_shares"], 500)
        self.assertEqual(replayer.audit["hidden_flow_shares"], 500)

    def test_priority_anomaly_is_counted_not_absorbed(self):
        # An order behind us trades while quantity that rested ahead of us is still queued.
        frames = resting_book(1, refs=1, shares=100)
        frames += [add_order(1, BASE_NS + 6 * MS, 11000, "B", 100, PRICE),
                   order_executed(1, BASE_NS + 10 * MS, 11000, 100)]
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["filled_shares"], 0)
        self.assertEqual(rows[0]["priority_anomalies"], 1)
        self.assertEqual(replayer.audit["priority_anomalies"], 1)


class MarkoutAnchorTest(unittest.TestCase):
    def test_markout_is_anchored_at_the_fill_and_exit_uses_the_future_quote(self):
        frames = [stock_directory(1, "TEST", BASE_NS),
                  add_order(1, BASE_NS + 1, 1000, "B", 100, PRICE),
                  add_order(1, BASE_NS + 1, 1002, "B", 500, PRICE - 100),  # deeper bid
                  add_order(1, BASE_NS + 2, 1001, "S", 100, PRICE + 100)]
        frames += [add_order(1, BASE_NS + 8 * MS, 11500, "S", 900, PRICE + 50),  # ask improves
                   order_executed(1, BASE_NS + 10 * MS, 1000, 100),   # ahead consumed
                   add_order(1, BASE_NS + 11 * MS, 12000, "B", 100, PRICE),
                   order_executed(1, BASE_NS + 11 * MS, 12000, 100),  # our 100-share fill
                   # after the fill the bid strengthens to $50.05, then to $50.10
                   add_order(1, BASE_NS + 12 * MS, 13000, "B", 500, PRICE + 5),
                   add_order(1, BASE_NS + 20 * MS, 14000, "B", 500, PRICE + 10)]
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        row = rows[0]
        self.assertEqual(row["filled_shares"], 100)
        # The mid at the fill is measured after the execution that filled us, not at submission:
        # the ask improved to $50.50 at t+8 ms while the submission mid used $51.00. The bid that
        # filled us was consumed by the same sweep, so the best bid is now $49.90.
        self.assertEqual(row["mid2_at_fill"], (PRICE - 100) + (PRICE + 50))
        self.assertEqual(row["mid2_raw"], PRICE + (PRICE + 100))
        self.assertNotEqual(row["mid2_raw"], row["mid2_at_fill"])
        # The fill is at BASE_NS+11 ms (the execution that reaches us). The 10 ms exit therefore
        # resolves at the first message after BASE_NS+21 ms, where the best bid is $50.10.
        self.assertEqual(row["exit_bid_10ms"], PRICE + 10)
        self.assertEqual(row["exit_bid_100ms"], PRICE + 10)
        self.assertEqual(row["exit_ask_10ms"], PRICE + 50)


class AuditTest(unittest.TestCase):
    def test_attempts_are_only_submitted_when_a_two_sided_quote_exists(self):
        # One-sided book on purpose: no ask, so no decision state and no attempt.
        frames = [stock_directory(1, "TEST", BASE_NS),
                  add_order(1, BASE_NS + 1, 1000, "B", 100, PRICE)]
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(replayer.audit["attempts"], 0)
        self.assertEqual(replayer.audit["attempts_skipped_no_quote"], 1)

    def test_zero_imbalance_submits_nothing(self):
        frames = resting_book(1, refs=1, shares=100)
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.0)]}, ttl_ms=1000)
        self.assertEqual(replayer.audit["attempts"], 0)
        self.assertEqual(replayer.audit["attempts_skipped_zero_imbalance"], 1)


class AnalysisArithmeticTest(unittest.TestCase):
    """The money math: markouts anchored at the fill, and EV per attempt including no-fills."""

    def _attempts(self):
        import pyarrow as pa
        import pyarrow.parquet as pq

        rows = [
            # attempt 0: buy fill at $50.00, mid 100.01 -> exits at $50.02/$50.04
            dict(attempt_id=0, ts_ns=BASE_NS, locate=1, symbol="TEST", side=1, price_raw=PRICE,
                 size=100, queue_ahead_shares=100, queue_ahead_orders=1,
                 queue_position_percentile=0.5, imbalance=0.5, spread_raw=100, mid2_raw=2 * PRICE + 100,
                 price_usd=50.005, filled_shares=100, fill_count=1,
                 first_fill_ts_ns=BASE_NS + 10 * MS, last_fill_ts_ns=BASE_NS + 10 * MS,
                 time_to_first_fill_ns=10 * MS, filled_price_raw=PRICE, terminal_reason="COMPLETE_FILL",
                 queue_ahead_at_fill=0, hidden_flow_at_level_shares=0, executed_shares_at_level=100,
                 priority_anomalies=0, mid2_at_fill=2 * PRICE + 200,
                 exit_bid_10ms=PRICE + 200, exit_ask_10ms=PRICE + 400,
                 exit_bid_1000ms=PRICE + 200, exit_ask_1000ms=PRICE + 400),
            # attempt 1: no fill at all
            dict(attempt_id=1, ts_ns=BASE_NS + 1_000_000_000, locate=2, symbol="OTHER", side=1,
                 price_raw=PRICE, size=100, queue_ahead_shares=500, queue_ahead_orders=3,
                 queue_position_percentile=0.83, imbalance=0.3, spread_raw=100,
                 mid2_raw=2 * PRICE + 100, price_usd=50.005, filled_shares=0, fill_count=0,
                 first_fill_ts_ns=0, last_fill_ts_ns=0, time_to_first_fill_ns=0,
                 filled_price_raw=0, terminal_reason="TTL_EXPIRED_NO_FILL", queue_ahead_at_fill=-1,
                 hidden_flow_at_level_shares=0, executed_shares_at_level=0, priority_anomalies=0,
                 mid2_at_fill=0, exit_bid_10ms=0, exit_ask_10ms=0, exit_bid_1000ms=0,
                 exit_ask_1000ms=0),
        ]
        columns = {}
        for name, dtype in passive_module.ATTEMPT_SCHEMA:
            if pa.types.is_integer(dtype):
                columns[name] = pa.array([int(row.get(name, 0)) for row in rows], type=dtype)
            elif pa.types.is_floating(dtype):
                columns[name] = pa.array([float(row.get(name, 0)) for row in rows], type=dtype)
            else:
                columns[name] = pa.array([row.get(name) for row in rows], type=dtype)
        handle = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        handle.close()
        pq.write_table(pa.table(columns), handle.name)
        return handle.name

    def test_markouts_and_ev_per_attempt(self):
        import pyarrow.parquet as pq

        from M2.src import costs as costs_module
        from M2.src import passive_analysis

        path = self._attempts()
        try:
            configuration = {
                "price_scale": 10000,
                "statistics": {"bootstrap": {"resamples": 32, "seed": 1}},
            }
            ledger = costs_module.load_ledger(config_module.repo_path(
                "M2/config/cost_ledger_v1.json"))
            analysis = passive_analysis.PassiveAnalysis(
                configuration, path, ledger, {"TEST": True, "OTHER": True})
            self.assertTrue(analysis.large_tick.all())
            result = analysis.run()
        finally:
            os.unlink(path)
        summary = result["fill_summary"][0]
        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["filled_attempts"], 1)
        self.assertAlmostEqual(summary["fill_rate"], 0.5)
        self.assertAlmostEqual(summary["median_time_to_first_fill_ms"], 10.0)
        horizon = [row for row in result["horizon_rows"]
                   if row["subset"] == "primary" and row["horizon_ms"] == 1000][0]
        # mid at fill = (50.00 + 50.02) / 2 = 50.01; exit mid = (50.02 + 50.04)/2 = 50.03.
        # midpoint adverse-selection markout = +0.02/50.01 = +4.0 bps for a long.
        self.assertAlmostEqual(horizon["mid_markout_bps_mean"], 1e4 * 0.02 / 50.01, places=6)
        # fill-price markout = (50.03 - 50.00)/50.00 = +6.0 bps.
        self.assertAlmostEqual(horizon["fill_price_markout_bps_mean"], 1e4 * 0.03 / 50.00, places=6)
        # executable exit sells the fill at the bid: (50.02 - 50.00)/50.00 = +4.0 bps gross.
        self.assertAlmostEqual(horizon["gross_exit_bps_mean"], 1e4 * 0.02 / 50.00, places=6)
        floor = [row for row in result["exit_rows"]
                 if row["subset"] == "primary" and row["cost_regime"] == "structural_floor"][0]
        # One fill of 100 shares out of two attempts: EV per attempt is half the fill's value,
        # expressed in dollars and in bps of one order's notional.
        self.assertAlmostEqual(floor["ev_per_attempt_usd"],
                               0.5 * floor["ev_per_filled_share_bps"] * 1e-4 * 100 * 50.00, places=6)
        self.assertAlmostEqual(floor["ev_per_attempt_bps"],
                               0.5 * floor["ev_per_filled_share_bps"], places=6)
        self.assertLess(floor["ev_per_filled_share_bps"], horizon["gross_exit_bps_mean"])




class FillModelBoundTest(unittest.TestCase):
    """The no-queue model is the optimistic bound: it must differ from FIFO exactly by the
    queue-position requirement, and in the direction that raises fills."""

    def _frames(self):
        frames = resting_book(1, refs=3, shares=500)          # 1500 shares resting ahead
        frames += [add_order(1, BASE_NS + 6 * MS, 3000, "B", 100, PRICE),
                   order_executed(1, BASE_NS + 10 * MS, 3000, 100)]  # trades 100, ahead untouched
        return frames

    def test_fifo_does_not_fill_but_no_queue_does(self):
        frames = self._frames()
        _, fifo_rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(fifo_rows[0]["filled_shares"], 0)
        self.assertEqual(fifo_rows[0]["queue_ahead_shares"], 1500)

        tape = write_tape([system_event(BASE_NS, "Q")] + frames
                          + [system_event(BASE_NS + 9500 * MS, "M")])
        try:
            directory = ingest.read_symbol_directory(tape)
            schedule = {"locates": [1], "by_locate": {1: deque(sorted([(BASE_NS + 5 * MS, 0.5)]))}}
            model = dict(MODEL)
            model["ttl_ns"] = 1000 * MS
            model["fill_model"] = "no_queue"
            replayer = passive_module.PassiveReplayer(config(), schedule, directory, model)
            replayer.run(tape)
            rows = {row["attempt_id"]: row for row in replayer.rows()}
        finally:
            os.unlink(tape)
        self.assertEqual(rows[0]["filled_shares"], 100)
        self.assertEqual(rows[0]["terminal_reason"], "COMPLETE_FILL")


class QuoteBookConsistencyTest(unittest.TestCase):
    """An execution must reduce the quote book: otherwise the touch is a phantom level.

    This is the defect that was found on the real tape (a quarter of attempts quoted a price
    level whose quantity had already been executed), so the contract is pinned here.
    """

    def test_attempt_after_a_level_is_executed_quotes_the_new_best_bid(self):
        frames = resting_book(1, refs=1, shares=100, price=PRICE)          # best bid $50.00
        frames += [add_order(1, BASE_NS + 2, 2500, "B", 400, PRICE - 100),  # deeper bid $49.90
                   order_executed(1, BASE_NS + 3, 1000, 100)]               # $50.00 is consumed
        # The attempt is taken after the execution, so it must join $49.90, not $50.00.
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(rows[0]["price_raw"], PRICE - 100)
        self.assertEqual(rows[0]["queue_ahead_shares"], 400)
        self.assertEqual(replayer.audit["level_state_mismatches"], 0)

    def test_level_accounting_never_diverges_from_the_quote_book(self):
        frames = resting_book(1, refs=3, shares=200)
        frames += [order_executed(1, BASE_NS + 10 * MS, 1000, 150),
                   order_cancel(1, BASE_NS + 11 * MS, 1001, 50),
                   order_delete(1, BASE_NS + 12 * MS, 1002),
                   order_executed(1, BASE_NS + 13 * MS, 1000, 50)]
        replayer, rows = run(frames, {1: [(BASE_NS + 5 * MS, 0.5)]}, ttl_ms=1000)
        self.assertEqual(replayer.audit["level_state_mismatches"], 0)
        self.assertEqual(replayer.audit["level_aggregate_mismatches"], 0)




class CrossSymbolLevelTest(unittest.TestCase):
    """A price is not unique across symbols: two names can quote the same level.

    Merging them into one queue (the defect found on the real tape) inflates the quantity ahead of
    a hypothetical order, so this contract is pinned directly.
    """

    def test_same_price_on_two_symbols_keeps_separate_queues(self):
        frames = [stock_directory(1, "AAA", BASE_NS), stock_directory(2, "BBB", BASE_NS)]
        frames += [add_order(1, BASE_NS + 1, 1000, "B", 200, PRICE),
                   add_order(1, BASE_NS + 2, 1001, "S", 300, PRICE + 100),
                   add_order(2, BASE_NS + 3, 2000, "B", 900, PRICE),      # same price, other symbol
                   add_order(2, BASE_NS + 4, 2001, "S", 300, PRICE + 100)]
        tape = write_tape([system_event(BASE_NS, "Q")] + frames
                          + [system_event(BASE_NS + 9500 * MS, "M")])
        try:
            directory = ingest.read_symbol_directory(tape)
            schedule = {"locates": [1, 2], "by_locate": {1: deque([(BASE_NS + 5 * MS, 0.5)]),
                                                         2: deque([(BASE_NS + 5 * MS, 0.5)])}}
            model = dict(MODEL)
            model["ttl_ns"] = 1000 * MS
            replayer = passive_module.PassiveReplayer(config(), schedule, directory, model)
            replayer.run(tape)
            rows = {row["locate"]: row for row in replayer.rows()}
        finally:
            os.unlink(tape)
        self.assertEqual(rows[1]["queue_ahead_shares"], 200, "AAA must not inherit BBB's queue")
        self.assertEqual(rows[2]["queue_ahead_shares"], 900)
        self.assertEqual(replayer.audit["level_state_mismatches"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
