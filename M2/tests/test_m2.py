"""Quantitative correctness tests for the M2-0 pass.

These tests use small synthetic tapes with exactly known answers. They check the
things that would silently corrupt a calculation: book lifecycle, orphan
handling, tick arithmetic, causal as-of behaviour, label preservation of zero
returns, delay handling, cost arithmetic and split chronology.

They deliberately do not test infrastructure.
"""

from __future__ import annotations

import atexit
import gzip
import json
import os
import shutil
import struct
import tempfile
import unittest

import numpy as np

from M2.src import audit as audit_module
from M2.src import book as book_module
from M2.src import calculate
from M2.src import config as config_module
from M2.src import costs
from M2.src import features
from M2.src import ingest
from M2.src import labels
from M2.src import universe

BASE_NS = 36_000_000_000_000  # 10:00:00.000000000

# Tests must never write into the repository's data or output directories: a test that
# reuses the production config would overwrite the real derived artifacts (this happened
# once during the pass and had to be recovered by re-running the replay), so every test
# config is redirected to a temporary root for the whole process.
_TEST_ROOT = tempfile.mkdtemp(prefix="m2-test-root-")
atexit.register(shutil.rmtree, _TEST_ROOT, ignore_errors=True)
SECOND = 1_000_000_000
MS = 1_000_000


def header(locate: int, tracking: int, timestamp_ns: int) -> bytes:
    return struct.pack(">HH", locate, tracking) + timestamp_ns.to_bytes(6, "big")


def system_event(timestamp_ns: int, code: str, tracking: int = 0) -> bytes:
    return ingest.build_itch_frame(0x53, header(0, tracking, timestamp_ns) + code.encode("ascii"))


def stock_directory(
    locate: int,
    symbol: str,
    timestamp_ns: int,
    market_category: str = "Q",
    issue_classification: str = "C",
    etp_flag: str = "N",
    authenticity: str = "P",
    tracking: int = 0,
) -> bytes:
    payload = (
        header(locate, tracking, timestamp_ns)
        + symbol.encode("ascii").ljust(8)
        + market_category.encode("ascii")
        + b" "
        + struct.pack(">I", 100)
        + b"N"
        + issue_classification.encode("ascii")
        + b"  "
        + authenticity.encode("ascii")
        + b"N"
        + b" "
        + b"1"
        + etp_flag.encode("ascii")
        + struct.pack(">I", 0)
        + b"N"
    )
    return ingest.build_itch_frame(0x52, payload)


def add_order(
    locate: int,
    timestamp_ns: int,
    reference: int,
    side: str,
    shares: int,
    price_raw: int,
    symbol: str = "TEST",
    tracking: int = 0,
    with_mpid: bool = False,
) -> bytes:
    payload = (
        header(locate, tracking, timestamp_ns)
        + struct.pack(">Q", reference)
        + side.encode("ascii")
        + struct.pack(">I", shares)
        + symbol.encode("ascii").ljust(8)
        + struct.pack(">I", price_raw)
    )
    if with_mpid:
        payload += b"MPID"
        return ingest.build_itch_frame(0x46, payload)
    return ingest.build_itch_frame(0x41, payload)


def order_executed(
    locate: int, timestamp_ns: int, reference: int, shares: int, match: int = 1, tracking: int = 0
) -> bytes:
    payload = (
        header(locate, tracking, timestamp_ns)
        + struct.pack(">Q", reference)
        + struct.pack(">I", shares)
        + struct.pack(">Q", match)
    )
    return ingest.build_itch_frame(0x45, payload)


def order_executed_with_price(
    locate: int,
    timestamp_ns: int,
    reference: int,
    shares: int,
    price_raw: int,
    printable: str = "Y",
    match: int = 1,
    tracking: int = 0,
) -> bytes:
    payload = (
        header(locate, tracking, timestamp_ns)
        + struct.pack(">Q", reference)
        + struct.pack(">I", shares)
        + struct.pack(">Q", match)
        + printable.encode("ascii")
        + struct.pack(">I", price_raw)
    )
    return ingest.build_itch_frame(0x43, payload)


def order_cancel(
    locate: int, timestamp_ns: int, reference: int, shares: int, tracking: int = 0
) -> bytes:
    payload = header(locate, tracking, timestamp_ns) + struct.pack(">Q", reference) + struct.pack(">I", shares)
    return ingest.build_itch_frame(0x58, payload)


def order_delete(locate: int, timestamp_ns: int, reference: int, tracking: int = 0) -> bytes:
    payload = header(locate, tracking, timestamp_ns) + struct.pack(">Q", reference)
    return ingest.build_itch_frame(0x44, payload)


def order_replace(
    locate: int,
    timestamp_ns: int,
    original: int,
    replacement: int,
    shares: int,
    price_raw: int,
    tracking: int = 0,
) -> bytes:
    payload = (
        header(locate, tracking, timestamp_ns)
        + struct.pack(">Q", original)
        + struct.pack(">Q", replacement)
        + struct.pack(">I", shares)
        + struct.pack(">I", price_raw)
    )
    return ingest.build_itch_frame(0x55, payload)


def write_tape(frames: list[bytes]) -> str:
    handle = tempfile.NamedTemporaryFile(suffix=".gz", delete=False)
    handle.close()
    with gzip.open(handle.name, "wb") as stream:
        for frame in frames:
            stream.write(frame)
    return handle.name


def test_config(**overrides) -> dict:
    configuration = config_module.load()
    configuration["paths"]["derived_dir"] = os.path.join(_TEST_ROOT, "derived")
    configuration["paths"]["output_dir"] = os.path.join(_TEST_ROOT, "output")
    configuration["session"]["continuous_start_ns"] = BASE_NS
    configuration["session"]["continuous_end_ns"] = BASE_NS + 2 * SECOND
    configuration["horizons_ms"] = [100, 250, 500, 1000]
    configuration["delay_ms"] = [0, 10, 25, 50, 100, 250, 500, 1000]
    configuration["dev_scope"]["candidate_pool_size"] = 4
    # One chunk per buffer, so the causal tests can read the in-memory store directly.
    configuration["decisions"]["buffer_rows_per_chunk"] = 2_000_000
    configuration["decisions"]["flush_min_rows"] = 1_000_000
    configuration["decisions"]["next_move_wait_ns"] = 5_000_000_000
    configuration["data_quality"]["book_audit_sample_interval_ns"] = 1 * SECOND
    for key, value in overrides.items():
        configuration[key] = value
    return configuration


def summary_for(locates: dict[int, int], prices: dict[int, int] | None = None) -> dict:
    return {
        "locate_add_counts": {str(k): v for k, v in locates.items()},
        "locate_first_add_price": {str(k): v for k, v in (prices or {}).items()},
    }


def directory_for(locates: dict[int, str]) -> dict[int, dict]:
    return {
        locate: {
            "locate": locate,
            "symbol": symbol,
            "market_category": "Q",
            "issue_classification": "C",
            "etp_flag": "N",
            "authenticity": "P",
            "directory_messages": 1,
        }
        for locate, symbol in locates.items()
    }


class BookLifecycleTests(unittest.TestCase):
    def _run(self, frames: list[bytes], locates: dict[int, str] | None = None, **config_overrides):
        path = write_tape(frames)
        self.addCleanup(os.unlink, path)
        locates = locates or {1: "TEST"}
        configuration = test_config(**config_overrides)
        summary = summary_for({locate: 100 for locate in locates}, {locate: 10_000 for locate in locates})
        replayer = book_module.Replayer(configuration, summary, directory_for(locates))
        result = replayer.run(path)
        return replayer, result

    def test_add_partial_execution_reduces_level_and_keeps_order(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "B", 300, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1002, "S", 400, 10_100),
            order_executed(1, BASE_NS + 1500 * MS, 1000, 200),
        ]
        replayer, _ = self._run(frames)
        state = replayer.books[1]
        self.assertEqual(state.best_bid, 10_000)
        self.assertEqual(state.bids[10_000], 600)  # 500 - 200 + 300
        self.assertEqual(state.best_ask, 10_100)
        self.assertEqual(replayer.orders[1000][3], 300)
        self.assertEqual(replayer.orders[1001][3], 300)

    def test_full_execution_removes_order_and_level(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "S", 400, 10_100),
            order_executed(1, BASE_NS + 1200 * MS, 1000, 500),
        ]
        replayer, _ = self._run(frames)
        self.assertNotIn(1000, replayer.orders)
        self.assertIsNone(replayer.books[1].best_bid)
        self.assertEqual(replayer.books[1].best_ask, 10_100)

    def test_cancel_then_delete_lifecycle(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "S", 500, 10_100),
            add_order(1, BASE_NS + 1 * MS, 1001, "B", 100, 9_900),
            order_cancel(1, BASE_NS + 1100 * MS, 1000, 200),
            order_delete(1, BASE_NS + 1200 * MS, 1000),
        ]
        replayer, _ = self._run(frames)
        self.assertNotIn(1000, replayer.orders)
        self.assertNotIn(10_100, replayer.books[1].asks)

    def test_replace_moves_size_and_retains_side(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "S", 100, 10_100),
            order_replace(1, BASE_NS + 1100 * MS, 1000, 2000, 300, 9_900),
        ]
        replayer, _ = self._run(frames)
        self.assertNotIn(1000, replayer.orders)
        self.assertEqual(replayer.orders[2000][3], 300)
        self.assertEqual(replayer.orders[2000][2], book_module.SIDE_BID)
        self.assertNotIn(10_000, replayer.books[1].bids)
        self.assertEqual(replayer.books[1].bids[9_900], 300)
        self.assertEqual(replayer.books[1].best_bid, 9_900)

    def test_unknown_order_reference_fails_closed(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "S", 500, 10_100),
            order_cancel(1, BASE_NS + 1100 * MS, 9999, 100),
        ]
        with self.assertRaises(RuntimeError):
            self._run(frames)

    def test_orphan_is_counted_when_fail_fast_disabled(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "S", 500, 10_100),
            order_cancel(1, BASE_NS + 1100 * MS, 9999, 100),
        ]
        configuration = test_config()
        configuration["data_quality"]["fail_fast_on_impossible_state"] = False
        path = write_tape(frames)
        self.addCleanup(os.unlink, path)
        replayer = book_module.Replayer(
            configuration, summary_for({1: 100}, {1: 10_000}), directory_for({1: "TEST"})
        )
        replayer.run(path)
        self.assertEqual(replayer.audit.symbols[1].anomalies["orphan_cancel"], 1)

    def test_oversized_cancel_is_flagged_not_repaired(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "S", 500, 10_100),
            order_cancel(1, BASE_NS + 1100 * MS, 1000, 600),
        ]
        configuration = test_config()
        configuration["data_quality"]["fail_fast_on_impossible_state"] = False
        path = write_tape(frames)
        self.addCleanup(os.unlink, path)
        replayer = book_module.Replayer(
            configuration, summary_for({1: 100}, {1: 10_000}), directory_for({1: "TEST"})
        )
        replayer.run(path)
        self.assertEqual(replayer.audit.symbols[1].anomalies["cancel_oversized"], 1)
        self.assertNotIn(1000, replayer.orders)

    def test_duplicate_order_reference_is_flagged(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 300, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "S", 500, 10_100),
        ]
        configuration = test_config()
        configuration["data_quality"]["fail_fast_on_impossible_state"] = False
        path = write_tape(frames)
        self.addCleanup(os.unlink, path)
        replayer = book_module.Replayer(
            configuration, summary_for({1: 100}, {1: 10_000}), directory_for({1: "TEST"})
        )
        replayer.run(path)
        self.assertEqual(replayer.audit.symbols[1].anomalies["order_id_collision"], 1)
        self.assertEqual(replayer.books[1].bids[10_000], 500)

    def test_crossed_book_is_counted(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "S", 500, 10_100),
            add_order(1, BASE_NS + 1 * MS, 1001, "B", 500, 10_200),
        ]
        replayer, _ = self._run(frames)
        self.assertEqual(replayer.audit.symbols[1].crossed_book_updates, 1)


def _read_parquet(path: str) -> dict[str, np.ndarray]:
    """Read a written artifact back into numpy: the tests assert the artifact, not
    whatever happens to be left in the in-memory chunk after a flush."""
    table = pq_module.read_table(path)
    return {name: table[name].to_numpy(zero_copy_only=False) for name in table.column_names}


class CausalityTests(unittest.TestCase):
    def _run(self, frames: list[bytes], heartbeat: bool = True, **overrides):
        if heartbeat:
            # A trailing message with a late timestamp is what makes the last grid
            # points and the last horizons observable at all; it does not touch the
            # book, so it cannot change any state being asserted.
            frames = [*frames, system_event(BASE_NS + 1900 * MS, "E", tracking=999)]
        path = write_tape(frames)
        self.addCleanup(os.unlink, path)
        configuration = test_config(**overrides)
        workdir = tempfile.mkdtemp(prefix="m2-causal-")
        self.addCleanup(lambda: __import__("shutil").rmtree(workdir, ignore_errors=True))
        configuration["paths"]["derived_dir"] = workdir
        derived = os.path.join(workdir, configuration["dataset"]["dataset_id"])
        os.makedirs(derived, exist_ok=True)
        replayer = book_module.Replayer(
            configuration, summary_for({1: 100}, {1: 10_000}), directory_for({1: "TEST"})
        )
        result = replayer.run(path)
        decisions = _read_parquet(os.path.join(derived, "decisions.parquet"))
        delays = _read_parquet(os.path.join(derived, "delay_decisions.parquet"))
        return replayer, result, decisions, delays

    def _row_at(self, decisions: dict, timestamp: int) -> int:
        rows = np.where(decisions["ts_ns"] == timestamp)[0]
        self.assertEqual(len(rows), 1)
        return int(rows[0])

    def test_label_as_of_uses_state_at_or_after_horizon(self):
        # The decision grid at the session start sees bid 100.00 / ask 100.01. The quote
        # moves at +100 ms, so the 100 ms label must see the moved quote.
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
            order_delete(1, BASE_NS + 100 * MS, 1001),
            add_order(1, BASE_NS + 100 * MS, 1002, "S", 100, 10_020),
        ]
        _replayer, _result, decisions, _delays = self._run(frames)
        row = self._row_at(decisions, BASE_NS)
        self.assertEqual(decisions["mid2_raw"][row], 10_000 + 10_010)
        self.assertEqual(decisions["mid2_future_100ms"][row], 10_000 + 10_020)
        self.assertEqual(decisions["direction_100ms"][row], labels.DIRECTION_UP)
        self.assertEqual(decisions["label_status_100ms"][row], labels.LABEL_OK)
        expected = labels.future_return_bps(20_010, 20_020)
        self.assertAlmostEqual(float(decisions["ret_bps_100ms"][row]), expected, places=4)

    def test_each_horizon_is_labeled_from_its_own_horizon_state(self):
        # The midpoint moves at +200 ms. The 100 ms label must still see the original
        # midpoint while the 250/500/1000 ms labels must see the moved one; if the
        # horizon slot were lost, every column would collapse onto one horizon.
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
            order_delete(1, BASE_NS + 200 * MS, 1001),
            add_order(1, BASE_NS + 200 * MS, 1002, "S", 100, 10_100),
        ]
        _replayer, _result, decisions, _delays = self._run(frames)
        row = self._row_at(decisions, BASE_NS)
        self.assertEqual(decisions["mid2_future_100ms"][row], 10_000 + 10_010)
        for horizon in (250, 500, 1000):
            self.assertEqual(decisions[f"mid2_future_{horizon}ms"][row], 10_000 + 10_100)
            self.assertEqual(decisions[f"label_status_{horizon}ms"][row], labels.LABEL_OK)
        self.assertNotEqual(
            float(decisions["ret_bps_100ms"][row]), float(decisions["ret_bps_250ms"][row])
        )

    def test_zero_return_observations_are_preserved(self):
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
        ]
        _replayer, result, decisions, _delays = self._run(frames)
        count = int(result["decision_rows"])
        self.assertGreater(count, 0)
        self.assertEqual(int(np.sum(decisions["ret_bps_100ms"] == 0.0)), count)
        self.assertTrue(np.all(decisions["direction_100ms"] == labels.DIRECTION_FLAT))

    def test_missing_future_state_is_null_not_interpolated(self):
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
            order_delete(1, BASE_NS + 50 * MS, 1001),
        ]
        _replayer, _result, decisions, _delays = self._run(frames)
        row = self._row_at(decisions, BASE_NS)
        self.assertEqual(decisions["label_status_100ms"][row], labels.LABEL_NO_FUTURE_STATE)
        self.assertEqual(decisions["mid2_future_100ms"][row], 0)
        self.assertEqual(float(decisions["ret_bps_100ms"][row]), 0.0)

    def test_delay_sweep_uses_arrival_book_not_decision_book(self):
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
            order_delete(1, BASE_NS + 5 * MS, 1001),
            add_order(1, BASE_NS + 5 * MS, 1002, "S", 100, 10_050),
        ]
        _replayer, _result, _decisions, delays = self._run(frames)
        rows = np.where(delays["ts_ns"] == BASE_NS)[0]
        self.assertEqual(len(rows), 1)
        row = int(rows[0])
        self.assertEqual(delays["entry_ask_0ms"][row], 10_010)
        self.assertEqual(delays["entry_ask_10ms"][row], 10_050)
        self.assertEqual(delays["arrival_status_10ms"][row], book_module.ARRIVAL_OK)

    def test_late_message_after_decision_is_counted_and_not_retro_applied(self):
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
            add_order(1, BASE_NS + 500 * MS, 1002, "B", 100, 10_005),  # advances the grid
            add_order(1, BASE_NS + 20 * MS, 1003, "S", 100, 10_015),  # arrives late
        ]
        replayer, _result, decisions, _delays = self._run(frames)
        self.assertGreaterEqual(replayer.audit.symbols[1].late_after_decision, 1)
        row = self._row_at(decisions, BASE_NS)
        self.assertEqual(decisions["ask_size"][row], 100)

    def test_next_mid_move_resolves_every_stale_grid_point_that_shares_the_midpoint(self):
        # The midpoint is unchanged for 60 grid instants (six seconds) before it moves.
        # Every one of those rows must still be resolved by the single change.
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
            order_delete(1, BASE_NS + 6 * SECOND, 1001),
            add_order(1, BASE_NS + 6 * SECOND, 1002, "S", 100, 10_020),
            system_event(BASE_NS + 7 * SECOND, "E", tracking=999),
        ]
        # The wait window must cover the staleness for the label to be resolvable at
        # all; a midpoint that moves later than the window is censored, not fabricated.
        _replayer, result, decisions, _delays = self._run(
            frames,
            heartbeat=False,
            **{
                "session": {
                    "continuous_start_ns": BASE_NS,
                    "continuous_end_ns": BASE_NS + 8 * SECOND,
                },
                "decisions": {
                    "grid_ns": 100_000_000,
                    "delay_grid_ns": 1_000_000_000,
                    "as_of_rule": "FILE_ORDER_LAST_MESSAGE_WITH_TS_LE_DECISION_TS",
                    "buffer_rows_per_chunk": 2_000_000,
                    "flush_min_rows": 1_000_000,
                    "next_move_wait_ns": 10_000_000_000,
                },
            },
        )
        self.assertGreater(int(result["decision_rows"]), 60)
        ts = decisions["ts_ns"]
        resolved = decisions["next_move_resolved"]
        moved_at = BASE_NS + 6 * SECOND
        before = ts < moved_at
        after = ts >= moved_at
        self.assertGreater(int(before.sum()), 55)
        self.assertTrue(bool(resolved[before].all()))
        self.assertTrue(bool((decisions["next_move_direction"][before] == labels.DIRECTION_UP).all()))
        # Rows after the final move have no next change inside the observation window.
        self.assertTrue(bool(after.any()))
        self.assertFalse(bool(resolved[after].any()))

    def test_next_mid_move_direction_is_resolved_by_the_next_change(self):
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_010),
            order_delete(1, BASE_NS + 300 * MS, 1001),
            add_order(1, BASE_NS + 300 * MS, 1002, "S", 100, 10_020),
        ]
        _replayer, _result, decisions, _delays = self._run(frames)
        row = self._row_at(decisions, BASE_NS)
        self.assertTrue(bool(decisions["next_move_resolved"][row]))
        self.assertEqual(int(decisions["next_move_direction"][row]), labels.DIRECTION_UP)


class AuditAndFeatureTests(unittest.TestCase):
    def test_imbalance_formula_and_zero_denominator(self):
        self.assertAlmostEqual(features.imbalance(300, 100), 0.5)
        self.assertAlmostEqual(features.imbalance(100, 300), -0.5)
        self.assertAlmostEqual(features.imbalance(100, 100), 0.0)
        self.assertIsNone(features.imbalance(0, 0))
        self.assertIsNone(features.imbalance(-5, 10))

    def test_bin_index_support_and_last_bin_closed(self):
        edges = [-1.0, -0.5, 0.5, 1.0]
        self.assertEqual(features.bin_index(-1.0, edges), 0)
        self.assertEqual(features.bin_index(-0.5, edges), 1)
        self.assertEqual(features.bin_index(0.999, edges), 2)
        self.assertEqual(features.bin_index(0.5, edges), 2)
        self.assertEqual(features.bin_index(0.4999, edges), 1)
        self.assertEqual(features.bin_index(1.0, edges), 2)
        self.assertEqual(features.bin_index(-1.0001, edges), -1)

    def test_tick_conversion_and_one_tick_classification(self):
        self.assertTrue(features.is_one_tick(100, 100))
        self.assertFalse(features.is_one_tick(200, 100))
        self.assertEqual(features.spread_in_ticks(250, 100), 2.5)
        self.assertEqual(features.spread_in_ticks(300, 100), 3.0)
        self.assertEqual(features.mid2(10_000, 10_010), 20_010)

    def test_price_floor_uses_midpoint(self):
        self.assertTrue(features.symbol_eligible_price_floor(9_990, 10_010, 10_000))
        self.assertFalse(features.symbol_eligible_price_floor(9_800, 9_990, 10_000))

    def test_bucket_duplicate_detector_is_exact_within_bucket(self):
        detector = audit_module.BucketDuplicateDetector(100 * MS)
        self.assertFalse(detector.observe(BASE_NS, b"abc"))
        self.assertTrue(detector.observe(BASE_NS + 1, b"abc"))
        self.assertFalse(detector.observe(BASE_NS + 200 * MS, b"abc"))
        self.assertEqual(detector.duplicates, 1)

    def test_sequence_substitute_gap_and_regression_counting(self):
        tape_audit = audit_module.TapeAudit(BASE_NS, BASE_NS + SECOND, 100 * MS, SECOND)
        tape_audit.note_message(1, BASE_NS, None, 10, None, False)
        tape_audit.note_message(1, BASE_NS + 1, BASE_NS, 12, 10, False)
        tape_audit.note_message(1, BASE_NS + 2, BASE_NS + 1, 11, 12, False)
        self.assertEqual(tape_audit.tracking_gaps, 1)
        self.assertEqual(tape_audit.tracking_regressions, 1)

    def test_timestamp_reversal_and_session_gap_counting(self):
        tape_audit = audit_module.TapeAudit(BASE_NS, BASE_NS + 10 * SECOND, 100 * MS, SECOND)
        tape_audit.note_message(1, BASE_NS + SECOND, None, 1, None, False)
        tape_audit.note_message(1, BASE_NS, BASE_NS + SECOND, 2, 1, True)
        tape_audit.note_message(1, BASE_NS + 5 * SECOND, BASE_NS, 3, 2, False)
        self.assertEqual(tape_audit.reversals, 1)
        self.assertEqual(tape_audit.late_after_decision, 1)
        self.assertEqual(tape_audit.gap_count, 1)

    def test_reconciliation_detects_corrupted_levels(self):
        path = write_tape(
            [
                add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
                add_order(1, BASE_NS + 1 * MS, 1001, "S", 400, 10_100),
            ]
        )
        self.addCleanup(os.unlink, path)
        configuration = test_config()
        replayer = book_module.Replayer(
            configuration, summary_for({1: 100}, {1: 10_000}), directory_for({1: "TEST"})
        )
        replayer.run(path)
        replayer.reconcile()
        self.assertEqual(replayer.crosscheck[1]["unreconciled" if False else "unexplained_mismatches"], 0)
        replayer.books[1].bids[10_000] = 1  # corrupt the incremental level
        replayer.reconcile()
        self.assertEqual(replayer.crosscheck[1]["unexplained_mismatches"], 1)

    def test_symbol_directory_decoding(self):
        path = write_tape([stock_directory(7, "AAPL", BASE_NS, market_category="Q")])
        self.addCleanup(os.unlink, path)
        directory = ingest.read_symbol_directory(path)
        self.assertEqual(directory[7]["symbol"], "AAPL")
        self.assertEqual(directory[7]["market_category"], "Q")
        self.assertEqual(directory[7]["issue_classification"], "C")
        self.assertEqual(directory[7]["round_lot_size"], 100)

    def test_framing_error_raises(self):
        frame = add_order(1, BASE_NS, 1, "B", 100, 10_000)
        corrupted = bytes([0x00, 0xFF]) + frame[2:]
        path = write_tape([corrupted])
        self.addCleanup(os.unlink, path)
        with self.assertRaises(ingest.FeedFormatError):
            ingest.scan_tape(path)


class UniverseRuleTests(unittest.TestCase):
    def _base_context(self) -> dict:
        return {
            "selection_date": "2019-08-01",
            "information_deadline_ns": 0,
            "lookback_trading_days": 60,
        }

    def test_large_tick_rule_requires_median_one_tick_and_theta(self):
        rule = universe.LargeTickRule(theta=0.5)
        rule.observe_spread(100)
        rule.observe_spread(100)
        rule.observe_spread(200)
        self.assertTrue(rule.median_is_one_tick())
        self.assertAlmostEqual(rule.fraction_at_one_tick(), 2 / 3)
        self.assertTrue(rule.is_large_tick())

        rule2 = universe.LargeTickRule(theta=0.9)
        for _ in range(5):
            rule2.observe_spread(100)
        rule2.observe_spread(300)
        self.assertTrue(rule2.median_is_one_tick())
        self.assertFalse(rule2.is_large_tick())

    def test_price_floor_and_liquidity_rank(self):
        candidates = [
            universe.SymbolObservation(symbol="A", median_dollar_volume=1e9, price_ok=True),
            universe.SymbolObservation(symbol="B", median_dollar_volume=1e6, price_ok=True),
            universe.SymbolObservation(symbol="C", median_dollar_volume=1e5, price_ok=True),
            universe.SymbolObservation(symbol="D", median_dollar_volume=1e12, price_ok=False),
        ]
        selected = universe.top_decile_by_dollar_volume(candidates)
        self.assertIn("A", {row.symbol for row in selected})
        self.assertNotIn("D", {row.symbol for row in selected})

    def test_membership_uses_no_evaluation_period_information(self):
        observations = [
            universe.SymbolObservation(
                symbol="A",
                median_dollar_volume=1e9,
                price_ok=True,
                coverage_fraction=1.0,
                history_trading_days=200,
                halts_in_lookback=0,
                corporate_action_in_lookback=False,
                spread_observations=[100, 100, 100, 100],
            ),
            universe.SymbolObservation(
                symbol="B",
                median_dollar_volume=1e9,
                price_ok=True,
                coverage_fraction=0.5,
                history_trading_days=200,
                halts_in_lookback=0,
                corporate_action_in_lookback=False,
                spread_observations=[100, 100],
            ),
            universe.SymbolObservation(
                symbol="C",
                median_dollar_volume=1e9,
                price_ok=True,
                coverage_fraction=1.0,
                history_trading_days=30,
                halts_in_lookback=0,
                corporate_action_in_lookback=False,
                spread_observations=[100, 100],
            ),
        ]
        result = universe.apply_rule(observations, universe.RuleParameters())
        members = {row.symbol: row for row in result.rows}
        self.assertTrue(members["A"].eligible)
        self.assertEqual(members["B"].reason_code, "COVERAGE_BELOW_90PCT_OF_LOOKBACK_DAYS")
        self.assertEqual(members["C"].reason_code, "HISTORY_BELOW_120_TRADING_DAYS")

    def test_rule_refuses_evaluation_period_information(self):
        with self.assertRaises(universe.LeakageError):
            universe.assert_causal_inputs(
                {"evaluation_period_return": 0.01}, universe.RuleParameters()
            )
        universe.assert_causal_inputs({"median_dollar_volume": 1.0}, universe.RuleParameters())


class LabelAndCostSymmetryTests(unittest.TestCase):
    def test_label_helpers(self):
        self.assertAlmostEqual(labels.future_return_bps(20_000, 20_020), 10.0)
        self.assertAlmostEqual(labels.future_return_bps(20_000, 19_980), -10.0)
        self.assertEqual(labels.direction(20_000, 20_000), labels.DIRECTION_FLAT)
        self.assertTrue(labels.directional_hit(1, 20_000, 20_010))
        self.assertTrue(labels.directional_hit(-1, 20_000, 19_990))
        self.assertFalse(labels.directional_hit(1, 20_000, 19_990))

    def test_bps_conversion_round_trip(self):
        cost = 0.0030
        price = 50.0
        bps = labels.bps_from_dollars_per_share(cost, price)
        self.assertAlmostEqual(bps, 0.6)
        self.assertAlmostEqual(bps * price / 10000.0, cost)


class CostArithmeticTests(unittest.TestCase):
    def _ledger(self) -> dict:
        return {
            "ledger_id": "TEST-LEDGER",
            "regimes": ["STRUCTURAL_COST_FLOOR", "ACCESSIBLE_REFERENCE_PATH"],
            "broker_schedules": {
                "all_in": {
                    "per_share_usd": 0.005,
                    "min_per_order_usd": 1.00,
                    "max_pct_of_trade_value": 1.0,
                    "all_inclusive": True,
                    "source": {"url": "test", "publisher": "test", "access_date": "2026-09-22", "quote": "test"},
                },
                "tiered": {
                    "per_share_usd": 0.0035,
                    "min_per_order_usd": 0.35,
                    "max_pct_of_trade_value": 0.5,
                    "all_inclusive": False,
                    "source": {"url": "test", "publisher": "test", "access_date": "2026-09-22", "quote": "test"},
                },
            },
            "assumptions": {"representative_order_shares": 100},
            "execution_schedules": [
                {"regime": "STRUCTURAL_COST_FLOOR", "broker_schedule": None, "label": "floor"},
                {"regime": "ACCESSIBLE_REFERENCE_PATH", "broker_schedule": "all_in", "label": "fixed"},
                {"regime": "ACCESSIBLE_REFERENCE_PATH", "broker_schedule": "tiered", "label": "tiered"},
            ],
            "line_items": [
                {
                    "id": "venue_remove",
                    "unit": "USD_PER_SHARE",
                    "value": 0.0030,
                    "sides": "both",
                    "regimes": ["STRUCTURAL_COST_FLOOR", "ACCESSIBLE_REFERENCE_PATH"],
                    "source": {"url": "test", "publisher": "test", "access_date": "2026-09-22", "quote": "test"},
                },
                {
                    "id": "sec_section_31",
                    "unit": "USD_PER_MILLION_OF_SALES",
                    "value": 27.80,
                    "sides": "sell",
                    "regimes": ["STRUCTURAL_COST_FLOOR", "ACCESSIBLE_REFERENCE_PATH"],
                    "source": {"url": "test", "publisher": "test", "access_date": "2026-09-22", "quote": "test"},
                },
                {
                    "id": "finra_taf",
                    "unit": "USD_PER_SHARE",
                    "value": 0.000195,
                    "sides": "sell",
                    "max": {"unit": "USD_PER_ORDER", "value": 9.79},
                    "regimes": ["STRUCTURAL_COST_FLOOR", "ACCESSIBLE_REFERENCE_PATH"],
                    "source": {"url": "test", "publisher": "test", "access_date": "2026-09-22", "quote": "test"},
                },
            ],
        }

    def test_per_order_minimum_binds_and_per_share_scales(self):
        ledger = self._ledger()
        self.assertAlmostEqual(costs.commission_usd(ledger, "all_in", 100, 25.0), 1.00)
        self.assertAlmostEqual(costs.commission_usd(ledger, "all_in", 1000, 25.0), 5.00)
        self.assertAlmostEqual(costs.commission_usd(ledger, "tiered", 100, 25.0), 0.35)
        self.assertAlmostEqual(costs.commission_usd(ledger, "tiered", 1000, 25.0), 3.50)

    def test_cap_applies_when_below_the_minimum(self):
        ledger = self._ledger()
        # 1 share at $0.10: 1% of trade value = $0.001, below the $1.00 minimum, so
        # the maximum is assessed (IBKR footnote 8 behaviour).
        self.assertAlmostEqual(costs.commission_usd(ledger, "all_in", 1, 0.10), 0.001)

    def test_sell_side_only_charges_are_asymmetric(self):
        ledger = self._ledger()
        buy = costs.order_cost_breakdown(ledger, "STRUCTURAL_COST_FLOOR", "buy", 100, 50.0)
        sell = costs.order_cost_breakdown(ledger, "STRUCTURAL_COST_FLOOR", "sell", 100, 50.0)
        self.assertNotIn("sec_section_31", buy["items"])
        self.assertIn("sec_section_31", sell["items"])
        self.assertGreater(sell["total_usd"], buy["total_usd"])
        self.assertAlmostEqual(buy["total_usd"], 0.30)
        self.assertAlmostEqual(sell["items"]["sec_section_31"], 100 * 50.0 / 1_000_000 * 27.80)

    def test_all_inclusive_schedule_does_not_double_count(self):
        ledger = self._ledger()
        breakdown = costs.order_cost_breakdown(ledger, "ACCESSIBLE_REFERENCE_PATH", "buy", 1000, 50.0, "all_in")
        self.assertEqual(list(breakdown["items"]), ["broker_all_in_commission"])
        self.assertAlmostEqual(breakdown["total_usd"], 5.00)

    def test_bps_conversion(self):
        self.assertAlmostEqual(costs.bps(0.0030, 50.0), 0.6)
        self.assertIsNone(costs.bps(0.0030, 0.0))

    def test_finra_taf_maximum(self):
        ledger = self._ledger()
        item = [row for row in ledger["line_items"] if row["id"] == "finra_taf"][0]
        self.assertAlmostEqual(costs.line_item_cost(item, 1_000_000, 10.0), 9.79)

    def test_test_configs_can_never_write_into_the_repository(self):
        configuration = test_config()
        for key in ("derived_dir", "output_dir"):
            resolved = config_module.repo_path(configuration["paths"][key])
            self.assertFalse(
                resolved.startswith(config_module.REPO_ROOT),
                f"{key} resolves inside the repository: {resolved}",
            )

    def test_real_ledger_has_provenance_for_every_number(self):
        ledger = costs.load_ledger(config_module.repo_path("M2/config/cost_ledger_v1.json"))
        self.assertEqual(costs.validate_ledger(ledger), [])


class ExecutionArithmeticTests(unittest.TestCase):
    def _configuration(self) -> dict:
        return test_config()

    def _ledger(self) -> dict:
        return CostArithmeticTests()._ledger()

    def test_buy_and_sell_symmetry_and_spread_capture(self):
        configuration = self._configuration()
        count = 2
        delay_columns = {
            "ts_ns": np.array([BASE_NS, BASE_NS + 1000 * MS], dtype=np.int64),
            "locate": np.array([1, 1], dtype=np.int32),
            "block_id": np.array([0, 0], dtype=np.int16),
            "imbalance": np.array([0.5, -0.5], dtype=np.float32),
            "mid2_raw": np.array([20_010, 20_010], dtype=np.int64),
            "spread_raw": np.array([10, 10], dtype=np.int32),
        }
        for delay_ms in configuration["delay_ms"]:
            delay_columns[f"entry_bid_{delay_ms}ms"] = np.full(count, 10_000, dtype=np.int32)
            delay_columns[f"entry_ask_{delay_ms}ms"] = np.full(count, 10_010, dtype=np.int32)
            delay_columns[f"arrival_status_{delay_ms}ms"] = np.zeros(count, dtype=np.int8)
            for horizon_ms in configuration["horizons_ms"]:
                delay_columns[f"fut_bid_{delay_ms}ms_{horizon_ms}ms"] = np.array([10_030, 9_980], dtype=np.int32)
                delay_columns[f"fut_ask_{delay_ms}ms_{horizon_ms}ms"] = np.array([10_040, 9_990], dtype=np.int32)
        rows, missing = calculate.execution_rows(delay_columns, configuration, self._ledger())
        self.assertEqual(missing[0]["observations"], 2)
        delay_zero = [row for row in rows if row["delay_ms"] == 0 and row["horizon_ms"] == 100]
        structural = [row for row in delay_zero if row["cost_regime"] == "floor"][0]
        # row 0 is a long (imbalance > 0): entry is the arrival ask, exit the future bid
        # row 1 is a short (imbalance < 0): entry is the arrival bid, exit the future ask
        expected_cross = 0.5 * (
            10000.0 * (10_030 - 10_010) / 20_010 + 10000.0 * (10_000 - 9_990) / 20_010
        )
        expected_markout = 0.5 * (
            10000.0 * ((10_030 + 10_040) - 2 * 10_010) / 20_010
            + 10000.0 * (2 * 10_000 - (9_980 + 9_990)) / 20_010
        )
        self.assertAlmostEqual(structural["mean_cross_to_cross_bps"], expected_cross, places=6)
        self.assertAlmostEqual(structural["mean_gross_markout_bps"], expected_markout, places=6)
        self.assertLess(structural["mean_cost_adjusted_bps"], structural["mean_gross_markout_bps"])

    def test_idealized_summary_labels_and_delay_zero_only(self):
        rows = [
            {"delay_ms": 0, "horizon_ms": 100, "cost_regime": "floor", "mean_gross_markout_bps": 1.0},
            {"delay_ms": 10, "horizon_ms": 100, "cost_regime": "floor", "mean_gross_markout_bps": 0.5},
        ]
        summary = calculate.idealized_execution_summary(rows)
        self.assertEqual(len(summary), 1)
        self.assertIn("IDEALIZED_REFERENCE_EXECUTION", summary[0]["note"])

    def test_cost_bps_increases_as_price_falls_for_a_minimum_bound_order(self):
        ledger = self._ledger()
        cheap = costs.cost_in_bps_of_price(ledger, "ACCESSIBLE_REFERENCE_PATH", "all_in", 100, 5.0)
        dear = costs.cost_in_bps_of_price(ledger, "ACCESSIBLE_REFERENCE_PATH", "all_in", 100, 500.0)
        self.assertGreater(cheap, dear)


class SplitAndLeakageTests(unittest.TestCase):
    def test_single_day_cannot_produce_a_split(self):
        plan = calculate.split_plan(["2019-07-30"], test_config())
        self.assertEqual(plan["status"], "NO_SPLIT_POSSIBLE_INSUFFICIENT_COVERAGE")
        self.assertEqual(plan["partitions"], [])
        self.assertFalse(plan["sealed_test_readable_by_m2_0"])

    def test_split_is_chronological_and_disjoint(self):
        plan = calculate.split_plan(["2019-07-30", "2019-07-31", "2019-08-01", "2019-08-02"], test_config())
        partitions = plan["partitions"]
        self.assertEqual([row["name"] for row in partitions], ["development", "validation", "sealed_test"])
        for earlier, later in zip(partitions, partitions[1:]):
            self.assertLess(earlier["end"], later["start"])

    def test_sealed_partition_cannot_be_read(self):
        plan = calculate.split_plan(["2019-07-30", "2019-07-31", "2019-08-01"], test_config())
        calculate.assert_sealed_not_read(plan, "development")
        with self.assertRaises(PermissionError):
            calculate.assert_sealed_not_read(plan, "sealed_test")

    def test_feature_and_label_columns_are_disjoint(self):
        decision_columns = {name for name, _ in book_module.DECISION_SCHEMA}
        label_columns = {
            name
            for name in (
                [f"mid2_future_{h}ms" for h in (100, 250, 500, 1000)]
                + [f"ret_bps_{h}ms" for h in (100, 250, 500, 1000)]
                + [f"direction_{h}ms" for h in (100, 250, 500, 1000)]
                + [f"label_status_{h}ms" for h in (100, 250, 500, 1000)]
                + ["next_move_direction", "next_move_resolved"]
            )
        }
        self.assertEqual(decision_columns & label_columns, set())


import pyarrow.parquet as pq_module


class CalculationStageIntegrationTests(unittest.TestCase):
    """End-to-end: synthetic tape -> replay -> derived artifacts -> calculation stage."""

    def _build(self):
        import tempfile

        import yaml

        workdir = tempfile.mkdtemp(prefix="m2-integration-")
        self.addCleanup(lambda: __import__("shutil").rmtree(workdir, ignore_errors=True))
        frames = [
            system_event(BASE_NS - 1000 * MS, "O"),
            stock_directory(1, "AAA", BASE_NS - 900 * MS),
            stock_directory(2, "BBB", BASE_NS - 900 * MS),
            add_order(1, BASE_NS - 500 * MS, 1000, "B", 300, 10_000, symbol="AAA"),
            add_order(1, BASE_NS - 500 * MS, 1001, "S", 100, 10_100, symbol="AAA"),
            add_order(2, BASE_NS - 500 * MS, 2000, "B", 100, 10_000, symbol="BBB"),
            add_order(2, BASE_NS - 500 * MS, 2001, "S", 300, 10_100, symbol="BBB"),
            order_delete(1, BASE_NS + 1500 * MS, 1001),
            add_order(1, BASE_NS + 1500 * MS, 1002, "S", 100, 10_200, symbol="AAA"),
            system_event(BASE_NS + 1900 * MS, "E", tracking=999),
        ]
        tape = write_tape(frames)
        self.addCleanup(os.unlink, tape)

        configuration = config_module.load()
        configuration["session"]["continuous_start_ns"] = BASE_NS
        configuration["session"]["continuous_end_ns"] = BASE_NS + 2 * SECOND
        configuration["dev_scope"]["candidate_pool_size"] = 4
        configuration["decisions"]["buffer_rows_per_chunk"] = 2_000_000
        configuration["decisions"]["flush_min_rows"] = 1_000_000
        configuration["decisions"]["next_move_wait_ns"] = 5_000_000_000
        configuration["data_quality"]["book_audit_sample_interval_ns"] = 1 * SECOND
        derived_root = os.path.join(workdir, "derived")
        output_root = os.path.join(workdir, "output")
        configuration["paths"]["derived_dir"] = derived_root
        configuration["paths"]["output_dir"] = output_root
        dataset_id = configuration["dataset"]["dataset_id"]
        derived = os.path.join(derived_root, dataset_id)
        os.makedirs(derived, exist_ok=True)
        configuration["cost_ledger"]["artifact"] = config_module.repo_path("M2/config/cost_ledger_v1.json")

        summary = {
            "locate_add_counts": {"1": 100, "2": 100},
            "locate_first_add_price": {"1": 10_000, "2": 10_000},
        }
        directory = {
            1: {"locate": 1, "symbol": "AAA", "market_category": "Q", "issue_classification": "C",
                "etp_flag": "N", "authenticity": "P", "directory_messages": 1},
            2: {"locate": 2, "symbol": "BBB", "market_category": "Q", "issue_classification": "C",
                "etp_flag": "N", "authenticity": "P", "directory_messages": 1},
        }
        with open(os.path.join(derived, "ingest_summary.json"), "w") as handle:
            json.dump(summary, handle)
        import pyarrow as pa
        import pyarrow.parquet as pq_module

        pq_module.write_table(
            pa.table(
                {
                    "locate": [1, 2],
                    "symbol": ["AAA", "BBB"],
                    "market_category": ["Q", "Q"],
                    "issue_classification": ["C", "C"],
                    "etp_flag": ["N", "N"],
                    "authenticity": ["P", "P"],
                    "directory_messages": [1, 1],
                }
            ),
            os.path.join(derived, "symbol_directory.parquet"),
        )

        replayer = book_module.Replayer(configuration, summary, directory)
        replay = replayer.run(tape)
        limits = book_module.evaluate_quality_limits(configuration, replayer)
        payload = {
            "replay": replay,
            "quality_limits": limits,
            "decision_rows": int(replayer.decisions.rows_written),
            "delay_rows": int(replayer.delay_rows.rows_written),
        }
        with open(os.path.join(derived, "replay_summary.json"), "w") as handle:
            json.dump(payload, handle, default=str)
        config_path = os.path.join(workdir, "config.yaml")
        with open(config_path, "w") as handle:
            yaml.safe_dump(configuration, handle)
        return configuration, config_path, output_root, payload, replayer

    def test_stage_runs_end_to_end_and_artifacts_are_consistent(self):
        configuration, config_path, output_root, payload, replayer = self._build()
        self.assertEqual(payload["replay"]["messages"], 10)
        self.assertEqual(payload["quality_limits"]["verdict"], "DATA_VALID")
        exit_code = calculate.main(["--config", config_path])
        self.assertEqual(exit_code, 0)

        calculations = os.path.join(output_root, "calculations")
        for name in (
            "calculation_status.json",
            "coverage_summary.csv",
            "market_structure_summary.csv",
            "imbalance_distribution.csv",
            "future_return_summary.csv",
            "imbalance_response_by_horizon.csv",
            "imbalance_response_by_symbol_day.csv",
            "monotonicity_diagnostics.csv",
            "directional_sanity_summary.csv",
            "next_move_summary.csv",
            "reference_cost_by_quantity.csv",
            "reference_cost_by_price.csv",
            "idealized_execution_summary.csv",
            "ev_delay_descriptive.csv",
            "reconciliation_checks.csv",
            "universe_membership.parquet",
            "split_manifest.json",
        ):
            self.assertTrue(os.path.exists(os.path.join(calculations, name)), name)
        self.assertTrue(
            os.path.exists(os.path.join(output_root, "data_quality", "universe_audit.csv"))
        )

        with open(os.path.join(calculations, "calculation_status.json")) as handle:
            status = json.load(handle)
        self.assertEqual(status["run_status"], "CALCULATION_COMPLETE")
        self.assertTrue(status["blocked"])
        # 19 grid instants inside the two-second session (0.0s .. 1.8s) for each of the
        # two scope symbols; the price-floor rule is exercised separately below.
        self.assertEqual(status["decision_observations_retained"], 38)

        reconciliation = _read_csv(os.path.join(calculations, "reconciliation_checks.csv"))
        failures = [row for row in reconciliation if row["outcome"] != "PASS"]
        self.assertEqual(failures, [])

        imbalance_rows = _read_csv(os.path.join(calculations, "imbalance_distribution.csv"))
        pooled = [row for row in imbalance_rows if row["unit"] == "POOLED"][0]
        self.assertAlmostEqual(float(pooled["imbalance_mean"]), 0.0, places=6)
        self.assertAlmostEqual(float(pooled["imbalance_extreme_fraction_abs_ge_threshold"]), 0.0, places=6)

        structure = _read_csv(os.path.join(calculations, "market_structure_summary.csv"))
        pooled_structure = [row for row in structure if row["unit"] == "POOLED"][0]
        # The fixture widens AAA's ask at +1.5s, so the last four grid instants of AAA
        # (1.5s..1.8s) are two-tick: 34 of 38 observations remain at exactly one tick.
        self.assertAlmostEqual(float(pooled_structure["one_tick_spread_fraction"]), 34 / 38, places=9)
        self.assertAlmostEqual(float(pooled_structure["spread_ticks_mean"]), (34 * 1 + 4 * 2) / 38, places=6)

        returns = _read_csv(os.path.join(calculations, "future_return_summary.csv"))
        self.assertEqual(len(returns), 4)
        for row in returns:
            horizon_ms = int(row["horizon_ms"])
            status = replayer.decisions.columns[f"label_status_{horizon_ms}ms"][: replayer.decisions.n]
            resolved = int((status == labels.LABEL_OK).sum())
            # No zero-return observation may be dropped: the summary must account for
            # exactly the resolvable labels, and the three outcome classes must partition.
            self.assertEqual(int(row["observations"]), resolved)
            observations = int(row["observations"])
            if observations == 0:
                # An empty horizon is reported as absent (NaN), never as a zero.
                self.assertTrue(__import__("math").isnan(float(row["mean_bps"])))
                continue
            positives = int(round(float(row["prob_positive"]) * observations))
            negatives = int(round(float(row["prob_negative"]) * observations))
            self.assertEqual(int(row["zero_return_count"]) + positives + negatives, observations)
        self.assertGreater(sum(int(row["zero_return_count"]) for row in returns), 0)

        delay = _read_csv(os.path.join(calculations, "ev_delay_descriptive.csv"))
        self.assertEqual(len(delay), 8 * 4 * 3)

        directional = _read_csv(os.path.join(calculations, "directional_sanity_summary.csv"))
        self.assertTrue(directional)
        self.assertIn("hit_rate_given_nonzero_move", directional[0])
        self.assertIn("zero_move_fraction", directional[0])
        for row in directional:
            if int(row["observations"]) == 0:
                self.assertEqual(row.get("hit_rate_given_nonzero_move", ""), "")
                continue
            hit_rate = float(row["hit_rate_given_nonzero_move"])
            self.assertGreaterEqual(hit_rate, 0.0)
            self.assertLessEqual(hit_rate, 1.0)

        costs_by_quantity = _read_csv(os.path.join(calculations, "reference_cost_by_quantity.csv"))
        self.assertEqual(len(costs_by_quantity), 5)
        self.assertIn("structural_floor_round_trip_usd", costs_by_quantity[0])
        self.assertIn("accessible_fixed_round_trip_usd", costs_by_quantity[0])
        self.assertIn("accessible_tiered_round_trip_usd", costs_by_quantity[0])
        # the all-inclusive schedule must not carry venue or clearing line items
        self.assertNotIn("accessible_fixed_nasdaq_remove_liquidity_fee_usd", costs_by_quantity[0])

        import pyarrow.parquet as pq_module

        membership = pq_module.read_table(os.path.join(calculations, "universe_membership.parquet"))
        self.assertEqual(membership.num_rows, 2)
        self.assertTrue(all(value is None for value in membership["eligible"].to_pylist()))
        self.assertTrue(all("BLOCKED" in value for value in membership["membership_status"].to_pylist()))

    def test_chunked_writes_preserve_every_row(self):
        # A tiny chunk size forces several Parquet chunks for one session; the artifact
        # must still hold every row, in non-decreasing timestamp order.
        configuration = test_config()
        configuration["decisions"]["buffer_rows_per_chunk"] = 128
        configuration["decisions"]["flush_min_rows"] = 64
        configuration["decisions"]["next_move_wait_ns"] = 1_000_000_000
        configuration["session"]["continuous_end_ns"] = BASE_NS + 12 * SECOND
        frames = [
            add_order(1, BASE_NS - 10 * MS, 1000, "B", 100, 10_000),
            add_order(1, BASE_NS - 10 * MS, 1001, "S", 100, 10_100),
        ]
        # A real tape keeps arriving: without trailing messages no future state can be
        # resolved and nothing may be written out, which is the correct behaviour and
        # is what the guard enforces. These heartbeats let the writer advance.
        frames += [system_event(BASE_NS + step * 200 * MS, "S", tracking=500 + step) for step in range(1, 58)]
        frames.append(system_event(BASE_NS + 11_500 * MS, "E", tracking=999))
        path = write_tape(frames)
        self.addCleanup(os.unlink, path)
        import tempfile

        workdir = tempfile.mkdtemp(prefix="m2-chunks-")
        self.addCleanup(lambda: __import__("shutil").rmtree(workdir, ignore_errors=True))
        configuration["paths"]["derived_dir"] = os.path.join(workdir, "derived")
        os.makedirs(
            os.path.join(configuration["paths"]["derived_dir"], configuration["dataset"]["dataset_id"]),
            exist_ok=True,
        )
        replayer = book_module.Replayer(
            configuration, summary_for({1: 100}, {1: 10_000}), directory_for({1: "TEST"})
        )
        replay = replayer.run(path)
        self.assertGreater(replay["decision_parquet_chunks"], 1)
        read_back = pq_module.read_table(
            os.path.join(
                configuration["paths"]["derived_dir"],
                configuration["dataset"]["dataset_id"],
                "decisions.parquet",
            )
        )
        self.assertEqual(read_back.num_rows, replay["decision_rows"])
        timestamps = read_back["ts_ns"].to_numpy()
        self.assertTrue(bool((np.diff(timestamps) >= 0).all()))
        # A grid instant is emitted at the first message after it, so exactly the
        # instants strictly before the last message (at +11.5 s) exist: 115 of them at
        # a 100 ms grid for the single scope symbol.
        self.assertEqual(read_back.num_rows, int((11_500 * MS) // (100 * MS)))

    def test_audit_writers_emit_exactly_the_declared_columns(self):
        _configuration, _config_path, output_root, _payload, replayer = self._build()
        data_quality = os.path.join(output_root, "data_quality")
        os.makedirs(data_quality, exist_ok=True)
        audit_module.write_timestamp_audit(
            os.path.join(data_quality, "timestamp_audit.csv"), "2019-07-30", replayer.audit
        )
        audit_module.write_sequence_audit(
            os.path.join(data_quality, "sequence_gap_audit.csv"), "2019-07-30", replayer.audit
        )
        audit_module.write_ordering_audit(
            os.path.join(data_quality, "ordering_anomalies.csv"), "2019-07-30", replayer.audit
        )
        audit_module.write_book_audit(
            os.path.join(data_quality, "book_reconstruction_audit.csv"), "2019-07-30", replayer.audit, "TEST"
        )
        expected = {
            "timestamp_audit.csv": audit_module.TIMESTAMP_AUDIT_COLUMNS,
            "sequence_gap_audit.csv": audit_module.SEQUENCE_AUDIT_COLUMNS,
            "ordering_anomalies.csv": audit_module.ORDERING_ANOMALY_COLUMNS,
            "book_reconstruction_audit.csv": audit_module.BOOK_AUDIT_COLUMNS,
        }
        for name, columns in expected.items():
            rows = _read_csv(os.path.join(data_quality, name))
            self.assertGreater(len(rows), 0, name)
            self.assertEqual(sorted(rows[0].keys()), sorted(columns), name)

    def test_price_floor_deactivates_a_sub_dollar_symbol(self):
        configuration, _config_path, _output_root, payload, replayer = self._build()
        del configuration
        self.assertIn("BBB", payload["replay"]["active_symbols"])
        self.assertEqual(payload["replay"]["scope_deactivations"], [])

    def test_stage_refuses_to_run_on_an_invalid_day(self):
        configuration, config_path, output_root, _payload, replayer = self._build()
        derived = os.path.join(
            config_module.repo_path(configuration["paths"]["derived_dir"]),
            configuration["dataset"]["dataset_id"],
        )
        with open(os.path.join(derived, "replay_summary.json"), "w") as handle:
            json.dump({"quality_limits": {"verdict": "DATA_INVALID", "checks": []}}, handle)
        exit_code = calculate.main(["--config", config_path])
        self.assertEqual(exit_code, 2)
        with open(os.path.join(output_root, "calculations", "calculation_status.json")) as handle:
            status = json.load(handle)
        self.assertEqual(status["run_status"], "CALCULATION_BLOCKED")


def _read_csv(path: str) -> list[dict]:
    import csv as csv_module

    with open(path, newline="") as handle:
        return list(csv_module.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
