"""Tests for the M2-0.6 single-day liquidity proxy and the explicit-locates scope.

The properties that matter for the universe-proxy diagnostic:

* dollar volume is taken from the venue trade tape with the right price *source* per
  message type (an order execution has no price of its own - it must use the resting
  order's price, which is the error that would silently corrupt the liquidity rank);
* crosses are excluded from the continuous-session liquidity measure rather than
  counted as continuous-session volume;
* the security-type screen, the price floor and the decile ranking follow the frozen
  rule's own order of reasoning, and the scope keeps only the largest names inside
  the decile;
* the replay scope can be driven by a frozen manifest, without changing the default
  add-count ranking path that M2-0's reproducibility rests on.
"""

from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest

from M2.src import book as book_module
from M2.src import ingest
from M2.src import universe_proxy
from M2.tests.test_m2 import (
    BASE_NS,
    add_order,
    header,
    order_cancel,
    order_delete,
    order_executed,
    order_executed_with_price,
    order_replace,
    stock_directory,
    system_event,
    write_tape,
)

SECOND = 1_000_000_000
PRICE_SCALE = 10000


def trade_non_cross(
    locate: int, timestamp_ns: int, reference: int, side: str, shares: int, price_raw: int, symbol: str = "TEST"
) -> bytes:
    payload = (
        header(locate, 0, timestamp_ns)
        + struct.pack(">Q", reference)
        + side.encode("ascii")
        + struct.pack(">I", shares)
        + symbol.encode("ascii").ljust(8)
        + struct.pack(">I", price_raw)
        + struct.pack(">Q", 1)
    )
    return ingest.build_itch_frame(0x50, payload)


def cross_trade(locate: int, timestamp_ns: int, symbol: str = "TEST") -> bytes:
    """A Cross Trade frame with the documented 40-byte body.

    The body length is taken from the repository's own framing contract
    (``ingest.MSG_LENGTH[0x51]``); the payload is padded to it rather than to a layout
    this test would otherwise have to invent, because the scan only counts crosses.
    """
    body = (bytes([0x51]) + header(locate, 0, timestamp_ns)).ljust(ingest.MSG_LENGTH[0x51], b"\x00")
    return len(body).to_bytes(2, "big") + body


def proxy_config() -> dict:
    return {
        "price_scale": PRICE_SCALE,
        "price_floor_usd": 1.0,
        "universe": {"liquidity_decile_fraction": 0.10},
    }


class LiquidityScanTest(unittest.TestCase):
    def test_dollar_volume_price_source_per_message_type(self):
        # One order rests at $10.00 and is executed by an E message, which carries no
        # price: the volume must be priced at the resting order's price, not at anything
        # else. A C message carries its own execution price. A P message is a trade.
        tape = write_tape(
            [
                system_event(BASE_NS, "Q"),
                stock_directory(1, "AAA", BASE_NS),
                add_order(1, BASE_NS + 1, 100, "B", 500, 10 * PRICE_SCALE),
                order_executed(1, BASE_NS + 2, 100, 200),
                order_executed_with_price(1, BASE_NS + 3, 100, 100, 11 * PRICE_SCALE),
                trade_non_cross(1, BASE_NS + 4, 0, "B", 50, 12 * PRICE_SCALE),
                cross_trade(1, BASE_NS + 5),
            ]
        )
        try:
            scan = universe_proxy.scan_liquidity(tape, {1})
        finally:
            os.unlink(tape)
        self.assertEqual(scan.messages, 7)
        expected = 200 * 10 * PRICE_SCALE + 100 * 11 * PRICE_SCALE + 50 * 12 * PRICE_SCALE
        self.assertEqual(scan.dollar_volume[1], expected)
        self.assertEqual(scan.shares[1], 350)
        self.assertEqual(scan.trades[1], 3)
        # The cross is counted, never priced into the liquidity measure: crossing
        # sessions are not continuous-session liquidity.
        self.assertEqual(scan.cross_messages[1], 1)

    def test_cancel_delete_replace_and_orphans(self):
        # The live-order map must release fully cancelled and deleted orders, and a
        # replace must move the price, otherwise a later execution is priced off a stale
        # order. Orphans are counted, never priced.
        tape = write_tape(
            [
                system_event(BASE_NS, "Q"),
                stock_directory(1, "AAA", BASE_NS),
                add_order(1, BASE_NS + 1, 100, "B", 500, 10 * PRICE_SCALE),
                add_order(1, BASE_NS + 2, 101, "S", 500, 11 * PRICE_SCALE),
                add_order(1, BASE_NS + 3, 102, "B", 500, 9 * PRICE_SCALE),
                order_cancel(1, BASE_NS + 4, 100, 500),          # fully cancelled -> released
                order_delete(1, BASE_NS + 5, 101),               # deleted -> released
                order_replace(1, BASE_NS + 6, 102, 103, 300, 95 * PRICE_SCALE // 10),
                order_executed(1, BASE_NS + 7, 103, 100),        # priced at the replaced price
                order_executed(1, BASE_NS + 8, 100, 10),         # orphan: 100 was cancelled
                order_cancel(1, BASE_NS + 9, 101, 10),           # orphan: 101 was deleted
            ]
        )
        try:
            scan = universe_proxy.scan_liquidity(tape, {1})
        finally:
            os.unlink(tape)
        self.assertEqual(scan.dollar_volume[1], 100 * 95 * PRICE_SCALE // 10)
        self.assertEqual(scan.orphan_executes, 1)
        self.assertEqual(scan.orphan_cancels, 1)
        self.assertEqual(scan.max_live_orders, 3)

    def test_partial_cancel_and_partial_execution_keep_the_order_live(self):
        tape = write_tape(
            [
                system_event(BASE_NS, "Q"),
                stock_directory(1, "AAA", BASE_NS),
                add_order(1, BASE_NS + 1, 100, "B", 500, 10 * PRICE_SCALE),
                order_cancel(1, BASE_NS + 2, 100, 200),
                order_executed(1, BASE_NS + 3, 100, 250),  # leaves 50 -> still live
                order_executed(1, BASE_NS + 4, 100, 50),
                order_executed(1, BASE_NS + 5, 100, 1),    # now an orphan
            ]
        )
        try:
            scan = universe_proxy.scan_liquidity(tape, {1})
        finally:
            os.unlink(tape)
        self.assertEqual(scan.shares[1], 300)
        self.assertEqual(scan.orphan_executes, 1)
        self.assertEqual(scan.max_live_orders, 1)

    def test_untracked_locate_is_decoded_but_not_accumulated(self):
        tape = write_tape(
            [
                system_event(BASE_NS, "Q"),
                stock_directory(2, "BBB", BASE_NS),
                add_order(2, BASE_NS + 1, 200, "B", 100, 10 * PRICE_SCALE),
                order_executed(2, BASE_NS + 2, 200, 100),
            ]
        )
        try:
            scan = universe_proxy.scan_liquidity(tape, {1})
        finally:
            os.unlink(tape)
        self.assertEqual(scan.messages, 4)
        self.assertEqual(scan.dollar_volume, {})
        self.assertEqual(scan.orphan_executes, 0)

    def test_median_trade_price_is_trade_count_weighted(self):
        tape = write_tape(
            [
                system_event(BASE_NS, "Q"),
                stock_directory(1, "AAA", BASE_NS),
                trade_non_cross(1, BASE_NS + 1, 0, "B", 10, 10 * PRICE_SCALE),
                trade_non_cross(1, BASE_NS + 2, 0, "B", 10, 20 * PRICE_SCALE),
                trade_non_cross(1, BASE_NS + 3, 0, "B", 10, 30 * PRICE_SCALE),
            ]
        )
        try:
            scan = universe_proxy.scan_liquidity(tape, {1})
        finally:
            os.unlink(tape)
        self.assertEqual(scan.median_trade_price_raw(1), float(20 * PRICE_SCALE))
        self.assertIsNone(scan.median_trade_price_raw(99))


class ProxyMembershipTest(unittest.TestCase):
    def build(self):
        frames = [system_event(BASE_NS, "Q")]
        # locate, symbol, category, classification, etp, trade price, dollar volume
        spec = [
            (1, "BIG", "Q", "C", "N", 50, 900),    # eligible, largest volume
            (2, "MID", "Q", "C", "N", 20, 500),    # eligible
            (3, "SML", "Q", "C", "N", 10, 100),    # eligible
            (4, "ETF", "Q", "C", "Y", 30, 800),    # excluded: ETP
            (5, "OTH", "N", "C", "N", 40, 700),    # excluded: not Nasdaq-listed
            (6, "PFD", "Q", "P", "N", 40, 600),    # excluded: not common stock
            (7, "PEN", "Q", "C", "N", 0.5, 400),   # excluded: below the price floor
            (8, "NOTR", "Q", "C", "N", None, 0),   # excluded: no trades
        ]
        for locate, symbol, category, classification, etp, price, volume in spec:
            frames.append(
                stock_directory(
                    locate, symbol, BASE_NS, market_category=category, issue_classification=classification,
                    etp_flag=etp,
                )
            )
            if price is not None:
                frames.append(
                    trade_non_cross(
                        locate, BASE_NS + 1, 0, "B", volume, int(round(price * PRICE_SCALE)), symbol
                    )
                )
        tape = write_tape(frames)
        try:
            directory = ingest.read_symbol_directory(tape)
            scan = universe_proxy.scan_liquidity(tape, set(directory))
        finally:
            os.unlink(tape)
        return universe_proxy.proxy_membership(proxy_config(), scan, directory)

    def test_security_type_and_price_screens_precede_the_decile(self):
        rows = {row["symbol"]: row for row in self.build()}
        self.assertEqual(set(rows), {"BIG", "MID", "SML", "PEN", "NOTR"})
        self.assertEqual(rows["PEN"]["reason_code"], universe_proxy.PROXY_REASON_PRICE)
        self.assertEqual(rows["NOTR"]["reason_code"], universe_proxy.PROXY_REASON_NO_TRADES)
        self.assertFalse(rows["PEN"]["price_ok"])
        self.assertIsNone(rows["NOTR"]["liquidity_rank"])

    def test_decile_membership_and_rank_use_the_rule_primitive(self):
        rows = {row["symbol"]: row for row in self.build()}
        # Three names pass the price screen; ceil(3 * 0.10) == 1, so the decile is the
        # single largest dollar-volume name.
        self.assertTrue(rows["BIG"]["in_liquidity_decile"])
        self.assertEqual(rows["BIG"]["reason_code"], universe_proxy.PROXY_REASON_ELIGIBLE)
        self.assertFalse(rows["MID"]["in_liquidity_decile"])
        self.assertEqual(rows["MID"]["reason_code"], universe_proxy.PROXY_REASON_NOT_DECILE)
        self.assertEqual([rows["BIG"]["liquidity_rank"], rows["MID"]["liquidity_rank"], rows["SML"]["liquidity_rank"]],
                         [0, 1, 2])
        self.assertTrue(all(row["reporting_only"] for row in rows.values()))

    def test_scope_takes_the_largest_names_inside_the_decile(self):
        rows = self.build()
        for row in rows:
            if row["price_ok"]:
                row["in_liquidity_decile"] = True
        scope = universe_proxy.scope_locates(rows, 2)
        self.assertEqual([row["symbol"] for row in scope], ["BIG", "MID"])
        self.assertEqual([row["dollar_volume_usd"] for row in scope], [45000.0, 10000.0])


class ExplicitLocatesScopeTest(unittest.TestCase):
    def test_manifest_scope_order_eligibility_and_default_path(self):
        directory = {
            1: {"symbol": "AAA", "market_category": "Q", "issue_classification": "C", "etp_flag": "N",
                "authenticity": "P"},
            2: {"symbol": "BBB", "market_category": "Q", "issue_classification": "C", "etp_flag": "N",
                "authenticity": "P"},
            3: {"symbol": "CCC", "market_category": "N", "issue_classification": "C", "etp_flag": "N",
                "authenticity": "P"},
        }
        summary = {
            "locate_add_counts": {"1": 10, "2": 90, "3": 50},
            "locate_first_add_price": {"1": 50_000, "2": 90_000, "3": 40_000},
        }
        configuration = {
            "price_scale": PRICE_SCALE,
            "price_floor_usd": 1.0,
            "dev_scope": {
                "candidate_pool_size": 1,
                "require_nasdaq_listed": True,
                "require_common_stock": True,
                "require_not_etp": True,
                "require_price_floor": True,
            },
        }
        selected, excluded = book_module.select_candidates(configuration, summary, directory)
        self.assertEqual([row["symbol"] for row in selected], ["BBB"])
        self.assertEqual([row["reason"] for row in excluded], ["NOT_NASDAQ_LISTED", "OUTSIDE_COMPUTE_SCOPE_RANK"])

        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"scope_locates": [{"locate": 2}, {"locate": 3}, {"locate": 1}]}, handle)
        handle.close()
        try:
            configuration["dev_scope"]["explicit_locates_manifest"] = handle.name
            selected, excluded = book_module.select_candidates(configuration, summary, directory)
        finally:
            os.unlink(handle.name)
        # Manifest order is preserved; locate 3 fails the Nasdaq-listing sentence and is
        # reported instead of silently dropped.
        self.assertEqual([row["symbol"] for row in selected], ["BBB", "AAA"])
        self.assertEqual([row["rank"] for row in selected], [0, 1])
        self.assertIn({"locate": 3, "symbol": "", "reason": "MANIFEST_LOCATE_FAILS_ELIGIBILITY"}, excluded)


class LargeTickProxyTest(unittest.TestCase):
    """The large-tick screen is the frozen rule's own sentence, applied to one day."""

    def _derived(self, rows):
        import pyarrow as pa
        import pyarrow.parquet as pq

        derived = tempfile.mkdtemp(prefix="m2-proxy-derived-")
        table = pa.table(
            {
                "locate": pa.array([row[0] for row in rows], type=pa.int32()),
                "spread_raw": pa.array([row[1] for row in rows], type=pa.int32()),
                "mid2_raw": pa.array([row[2] for row in rows], type=pa.int64()),
            }
        )
        pq.write_table(table, os.path.join(derived, "decisions.parquet"))
        return derived

    def test_median_and_fraction_sentences_and_the_observation_floor(self):
        rows = []
        # locate 1: always one tick -> large tick
        rows += [(1, 100, 20_000)] * 1200
        # locate 2: always one tick but too few observations -> excluded
        rows += [(2, 100, 20_000)] * 10
        # locate 3: one tick 60% of the time, median one tick -> large tick
        rows += [(3, 100, 20_000)] * 1200 + [(3, 300, 20_000)] * 800
        # locate 4: median one tick but only 49.86% of observations at one tick, because
        # sub-penny spreads sit below it: the conjunction, not the median alone, decides.
        rows += [(4, 1, 20_000)] * 400 + [(4, 100, 20_000)] * 499 + [(4, 1000, 20_000)] * 102
        # locate 5: crossed/invalid state -> no valid observations at all
        rows += [(5, 0, 0)] * 1500
        derived = self._derived(rows)
        try:
            classification = universe_proxy.classify_large_tick_proxy(
                {"universe": {"theta_fraction_at_one_tick": 0.5}, "tick_raw": 100},
                derived,
                {1: "ONE", 2: "FEW", 3: "MOSTLY", 4: "HALF", 5: "BAD"},
            )
        finally:
            import shutil

            shutil.rmtree(derived, ignore_errors=True)
        by_symbol = {row["symbol"]: row for row in classification}
        self.assertTrue(by_symbol["ONE"]["large_tick_proxy"])
        self.assertFalse(by_symbol["FEW"]["large_tick_proxy"])
        self.assertFalse(by_symbol["FEW"]["minimum_observations_met"])
        self.assertEqual(by_symbol["FEW"]["valid_observations"], 10)
        self.assertTrue(by_symbol["MOSTLY"]["large_tick_proxy"])
        self.assertAlmostEqual(by_symbol["MOSTLY"]["fraction_at_one_tick"], 0.6, places=6)
        self.assertLess(by_symbol["HALF"]["fraction_at_one_tick"], 0.5)
        self.assertEqual(by_symbol["HALF"]["valid_observations"], 1001)
        self.assertFalse(by_symbol["HALF"]["large_tick_proxy"])
        self.assertTrue(by_symbol["HALF"]["median_spread_equals_one_tick"])
        self.assertFalse(by_symbol["HALF"]["fraction_threshold_met"])
        self.assertEqual(by_symbol["BAD"]["valid_observations"], 0)
        self.assertFalse(by_symbol["BAD"]["large_tick_proxy"])
        self.assertTrue(all(row["reporting_only"] for row in classification))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
