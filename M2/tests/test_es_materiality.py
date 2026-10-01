"""Tests for the frozen branch-A ES H3 OFI measurement.

The properties that decide the gate, and therefore the properties worth pinning:

* the state is causal - the flow a decision sees is exactly the flow stamped in the
  half-open interval ending at that decision, so a message at or after the decision
  instant can never enter it;
* the direction convention is fixed (aggressor-buy imbalance is LONG) and a balanced or
  unquotable state is *no* observation rather than a zero-valued one;
* the outcome is the side-signed midpoint move and the friction is the observed
  1/2 S_entry + 1/2 S_exit - one tick of quoted spread cannot be silently replaced by a
  constant and a wider spread cannot be silently capped;
* the classification keeps envelope's rule verbatim, and the two campaign-level rules
  are applied in the frozen order: a coverage-floor failure is named
  INDETERMINATE_COVERAGE, and a nominal SURVIVE_PROVISIONAL from a single admitted
  window is downgraded rather than claimed;
* the frozen parameter set is read from the sealed contract and the sealed contract's
  hashes are enforced, so a post-result parameter change cannot produce a verdict.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest

import numpy as np

from M2.src import envelope
from M2.src import es_materiality as es

SECOND = 1_000_000_000
STEP = 10_000_000
START = 1_689_600_600 * SECOND
POINTS = 60_000  # the admitted window is 600 s of 10 ms grid instants
BID_MANTISSA = 4_536_750_000_000_00
SCALE = 1.0e-11


def _grid(mid_points_by_instant: np.ndarray) -> dict:
    """A synthetic admitted grid with a fixed one-tick spread around each mid."""
    ts = START + np.arange(POINTS, dtype=np.int64) * STEP
    half = 0.125
    return {
        "ts_ns": ts,
        "bid_mantissa": (mid_points_by_instant - half) / SCALE,
        "ask_mantissa": (mid_points_by_instant + half) / SCALE,
        "bid_sz": np.full(POINTS, 4.0),
        "ask_sz": np.full(POINTS, 6.0),
        "spread_points": np.full(POINTS, 0.25),
    }


def _trades(offsets_ms: list[float], sizes: list[float], aggressors: list[int]) -> dict:
    times = np.asarray([START + int(round(offset * 1e6)) for offset in offsets_ms], dtype=np.int64)
    order = np.argsort(times, kind="stable")
    return {
        "time_ns": times[order],
        "size": np.asarray(sizes, dtype=float)[order],
        "aggressor": np.asarray(aggressors, dtype=np.int8)[order],
    }


class FlowCausalityTests(unittest.TestCase):
    def test_lookback_is_half_open_at_both_edges(self):
        trades = _trades([0.0, 500.0, 1000.0, 1000.001, 1500.0], [1, 2, 4, 8, 16], [1, 1, 1, 1, 1])
        time_ns, buy, sell = es.cumulative_flow(trades)
        instant = np.asarray([START + 2 * SECOND])
        volume_buy, volume_sell = es.flow_between(time_ns, buy, sell, instant, SECOND)
        # (1000ms, 2000ms] excludes the trade stamped exactly at 1000 ms (the far edge)
        # and excludes 0 ms; it includes 1000.001 ms and 1500 ms.
        self.assertEqual(volume_buy[0], 24.0)
        self.assertEqual(volume_sell[0], 0.0)

    def test_a_message_at_the_decision_instant_is_available_and_a_later_one_is_not(self):
        trades = _trades([999.998, 1000.0, 1000.002], [3, 5, 7], [1, 1, 2])
        time_ns, buy, sell = es.cumulative_flow(trades)
        volume_buy, volume_sell = es.flow_between(
            time_ns, buy, sell, np.asarray([START + SECOND]), SECOND
        )
        self.assertEqual(volume_buy[0], 8.0)  # 999.998 ms and exactly 1000.000 ms
        self.assertEqual(volume_sell[0], 0.0)  # 1000.002 ms is after the decision

    def test_an_unrelated_aggressor_code_enters_neither_side(self):
        trades = _trades([100.0, 200.0], [5.0, 6.0], [0, 1])
        time_ns, buy, sell = es.cumulative_flow(trades)
        volume_buy, volume_sell = es.flow_between(
            time_ns, buy, sell, np.asarray([START + SECOND]), SECOND
        )
        self.assertEqual((volume_buy[0], volume_sell[0]), (6.0, 0.0))


class StateTests(unittest.TestCase):
    def _panel(self, buy: float, sell: float, depth: float) -> es.Panel:
        one = np.asarray([1])
        return es.Panel(
            slot=np.asarray([0]), block_id=np.asarray([0]),
            mid_entry_points=np.asarray([4536.75]), mid_exit_points=np.asarray([4536.75]),
            spread_entry_points=np.asarray([0.25]), spread_exit_points=np.asarray([0.25]),
            depth=np.asarray([depth]), volume_buy=np.asarray([buy]), volume_sell=np.asarray([sell]),
        )

    def test_buy_imbalance_is_long_and_sell_imbalance_is_short(self):
        self.assertEqual(es.state_direction(self._panel(10.0, 4.0, 20.0))[0], 1)
        self.assertEqual(es.state_direction(self._panel(4.0, 10.0, 20.0))[0], -1)

    def test_a_balanced_or_illiquid_state_is_no_position_not_a_zero(self):
        balanced = self._panel(5.0, 5.0, 20.0)
        self.assertEqual(es.state_direction(balanced)[0], 0)
        self.assertFalse(es.observation_mask(balanced, es.state_direction(balanced))[0])
        empty = self._panel(5.0, 5.0, 0.0)
        self.assertEqual(es.state_direction(empty)[0], 0)

    def test_the_state_is_signed_volume_per_unit_of_displayed_depth(self):
        panel = self._panel(30.0, 10.0, 20.0)
        direction = es.state_direction(panel)
        imbalance = (panel.volume_buy - panel.volume_sell) / panel.depth
        self.assertEqual(imbalance[0], 1.0)
        self.assertEqual(direction[0], 1)


class OutcomeTests(unittest.TestCase):
    def _panel(self, entry: float, exit_: float, spread_entry: float = 0.25, spread_exit: float = 0.25):
        return es.Panel(
            slot=np.asarray([0]), block_id=np.asarray([0]),
            mid_entry_points=np.asarray([entry]), mid_exit_points=np.asarray([exit_]),
            spread_entry_points=np.asarray([spread_entry]),
            spread_exit_points=np.asarray([spread_exit]),
            depth=np.asarray([10.0]), volume_buy=np.asarray([7.0]), volume_sell=np.asarray([3.0]),
        )

    def test_markout_is_the_side_signed_midpoint_move_in_bps(self):
        rising = self._panel(4536.75, 4537.75)
        self.assertAlmostEqual(es.gross_markout_bps(rising, np.asarray([1], dtype=np.int8))[0],
                               1.0 / 4536.75 * 1e4)
        self.assertAlmostEqual(es.gross_markout_bps(rising, np.asarray([-1], dtype=np.int8))[0],
                               -1.0 / 4536.75 * 1e4)

    def test_a_flat_midpoint_is_exactly_zero_for_either_direction(self):
        flat = self._panel(4536.75, 4536.75)
        self.assertEqual(es.gross_markout_bps(flat, np.asarray([1], dtype=np.int8))[0], 0.0)
        self.assertEqual(es.gross_markout_bps(flat, np.asarray([-1], dtype=np.int8))[0], 0.0)

    def test_friction_is_the_observed_half_spread_round_trip_and_never_a_constant(self):
        one_tick = es.friction_bps(self._panel(4536.75, 4536.75), np.asarray([1], dtype=np.int8), 50.0)[0]
        two_tick = es.friction_bps(
            self._panel(4536.75, 4536.75, 0.5, 0.5), np.asarray([1], dtype=np.int8), 50.0
        )[0]
        self.assertAlmostEqual(one_tick, 0.25 / 4536.75 * 1e4)
        self.assertAlmostEqual(two_tick, 2.0 * one_tick)
        self.assertAlmostEqual(
            one_tick,
            envelope.midpoint_markout_friction_bps(0.25 * 50.0, 0.25 * 50.0, 4536.75 * 50.0),
        )

    def test_an_unquoted_slot_is_not_an_observation(self):
        panel = self._panel(4536.75, 4536.75, spread_entry=float("nan"))
        direction = es.state_direction(panel)
        self.assertFalse(es.observation_mask(panel, direction)[0])

    def test_friction_is_attached_only_to_evaluated_slots(self):
        panel = es.Panel(
            slot=np.asarray([0, 1]), block_id=np.asarray([0, 0]),
            mid_entry_points=np.asarray([4536.75, float("nan")]),
            mid_exit_points=np.asarray([4536.75, 4536.75]),
            spread_entry_points=np.asarray([0.25, 0.25]), spread_exit_points=np.asarray([0.25, 0.25]),
            depth=np.asarray([10.0, 10.0]), volume_buy=np.asarray([7.0, 7.0]),
            volume_sell=np.asarray([3.0, 3.0]),
        )
        direction = es.state_direction(panel)
        cost = es.friction_bps(panel, direction, 50.0)
        self.assertTrue(np.isfinite(cost[0]))
        self.assertFalse(np.isfinite(cost[1]))


class PanelGeometryTests(unittest.TestCase):
    def test_the_exit_instant_is_exactly_the_frozen_horizon_and_the_tail_is_censored(self):
        flow = (np.asarray([], dtype=np.int64),
                np.asarray([0.0]), np.asarray([0.0]))
        window_slots = POINTS * STEP // SECOND
        for horizon in (1, 5, 15):
            panel = es.build_panel(_grid(np.full(POINTS, 4536.75)), flow, horizon, SECOND, 60, SCALE, STEP)
            self.assertEqual(panel.slot.size, window_slots - horizon)
            self.assertEqual(panel.slot[0], 0)
            self.assertEqual(panel.slot[-1], window_slots - horizon - 1)
        panel = es.build_panel(_grid(np.full(POINTS, 4536.75)), flow, 1, SECOND, 60, SCALE, STEP)
        self.assertEqual(panel.block_id[-1], (window_slots - 2) // 60)

    def test_grid_midpoint_scale_is_the_published_one(self):
        grid = _grid(np.full(POINTS, 4536.75))
        panel = es.build_panel(grid, (np.asarray([], dtype=np.int64), np.asarray([0.0]), np.asarray([0.0])),
                               1, SECOND, 60, SCALE, STEP)
        self.assertAlmostEqual(panel.mid_entry_points[0], 4536.75)


class ClusteredIntervalTests(unittest.TestCase):
    def test_the_interval_resamples_blocks_not_observations(self):
        values = np.asarray([1.0, 1.0, 1.0, 1.0, 9.0, 9.0, 9.0, 9.0])
        blocks = np.asarray([0, 0, 0, 0, 1, 1, 1, 1])
        interval = es.clustered_ci(values, blocks, 500, 7)
        self.assertEqual(interval["clusters"], 2)
        self.assertGreaterEqual(interval["ci_low_bps"], 1.0)
        self.assertLessEqual(interval["ci_high_bps"], 9.0)

    def test_an_empty_selection_is_reported_as_missing_rather_than_zero(self):
        interval = es.clustered_ci(np.asarray([np.nan, np.nan]), np.asarray([0, 1]), 100, 3)
        self.assertIsNone(interval["ci_low_bps"])
        self.assertEqual(interval["clusters"], 0)

    def test_the_interval_is_a_function_of_the_frozen_seed(self):
        values = np.asarray([1.0, 2.0, 3.0, 40.0])
        blocks = np.asarray([0, 0, 1, 1])
        self.assertEqual(es.clustered_ci(values, blocks, 100, 11), es.clustered_ci(values, blocks, 100, 11))

    def test_block_means_are_weighted_by_their_observation_counts(self):
        values = np.asarray([0.0, 10.0, 10.0, 10.0])
        blocks = np.asarray([0, 1, 1, 1])
        interval = es.clustered_ci(values, blocks, 400, 5)
        self.assertEqual(interval["clusters"], 2)
        # every resample is a weighted average of the two block means, so the interval
        # cannot leave [4.0, 10.0] ... it lies inside [mean of 0&10, 10].
        self.assertGreaterEqual(interval["ci_low_bps"], 0.0)
        self.assertLessEqual(interval["ci_high_bps"], 10.0)


def _classification_inputs(gross, low, high, c0, failures=()):
    freeze = {
        "candidate_id": "TUP-CME-ES-H3-OFI-AGG",
        "horizons": {"primary_s": 1},
        "scope": {"statement": "one admitted window"},
    }
    window = {"start_utc": "2023-07-17T13:30:00Z", "end_utc": "2023-07-17T13:40:00Z", "symbol": "ESU3"}
    return es.classify(gross, low, high, c0, 4536.75 * 50.0, failures, window, freeze)


class ClassificationTests(unittest.TestCase):
    def test_a_non_positive_gross_is_a_kill_named_by_its_clause(self):
        result = _classification_inputs(-0.5, -1.2, 0.1, 0.55)
        self.assertEqual(result["verdict"], envelope.VERDICT_KILL)
        self.assertEqual(result["clause"], es.CLAUSE_NON_POSITIVE_GROSS)
        self.assertEqual(result["scope"], es.SCOPE_SAMPLE_SCOPED_KILL)
        self.assertIn("round_trip_required_bps", result["scoped_boundary"])

    def test_an_upper_bound_inside_the_structural_floor_is_a_kill(self):
        result = _classification_inputs(0.4, 0.1, 0.5, 0.55)
        self.assertEqual(result["verdict"], envelope.VERDICT_KILL)
        self.assertEqual(result["clause"], es.CLAUSE_UPPER_AT_OR_BELOW_C0)

    def test_a_nominal_survival_is_downgraded_for_single_window_scope(self):
        result = _classification_inputs(3.0, 2.0, 4.0, 0.55)
        self.assertEqual(result["nominal_verdict_before_scope_and_coverage"], envelope.VERDICT_SURVIVE)
        self.assertEqual(result["verdict"], es.VERDICT_INDETERMINATE_COVERAGE)
        self.assertTrue(result["clause"].startswith(es.CLAUSE_SINGLE_WINDOW))
        self.assertEqual(result["scope"], es.SCOPE_SINGLE_WINDOW_ONLY)

    def test_an_interval_straddling_the_floor_is_indeterminate(self):
        result = _classification_inputs(0.7, 0.2, 1.2, 0.55)
        self.assertEqual(result["verdict"], envelope.VERDICT_INDETERMINATE)
        self.assertEqual(result["clause"], es.CLAUSE_STRADDLES_C0)

    def test_a_coverage_failure_names_the_metric_and_keeps_the_nominal_reading(self):
        result = _classification_inputs(-0.5, -1.2, 0.1, 0.55, failures=("observation_coverage",))
        self.assertEqual(result["verdict"], es.VERDICT_INDETERMINATE_COVERAGE)
        self.assertIn("observation_coverage", result["clause"])
        self.assertEqual(result["nominal_verdict_before_scope_and_coverage"], envelope.VERDICT_KILL)
        self.assertFalse(result["coverage_gate_passed"])

    def test_the_two_reported_units_agree_by_construction(self):
        result = _classification_inputs(0.4, 0.1, 0.5, 0.55)
        self.assertAlmostEqual(result["bps"]["c_star_bps"], 0.4 - 0.55)
        self.assertAlmostEqual(result["usd"]["c_star_usd"], -0.15 * 1e-4 * 4536.75 * 50.0)
        self.assertTrue(result["significance_is_decision_criterion"] is False)


class LoaderTests(unittest.TestCase):
    def test_a_quote_free_grid_instant_loads_as_nan_rather_than_zero(self):
        with tempfile.TemporaryDirectory() as root:
            head = ("grid_index,ts_ns,bid_px,ask_px,bid_sz,ask_sz,spread_ticks,spread_points,"
                    "half_spread_points,half_spread_ticks")
            with open(os.path.join(root, "spread_grid.csv"), "w", newline="") as handle:
                handle.write(head + "\n")
                handle.write(f"0,{START},,,,,,,,\n")
                handle.write(f"1,{START + STEP},453650000000000,453675000000000,26,70,1.0,0.25,0.125,0.5\n")
            grid = es.load_spread_grid(os.path.join(root, "spread_grid.csv"))
        self.assertTrue(np.isnan(grid["bid_mantissa"][0]))
        self.assertEqual(grid["spread_points"][1], 0.25)
        self.assertEqual(grid["ts_ns"][1] - grid["ts_ns"][0], STEP)

    def test_trades_are_restricted_to_one_instrument_and_sorted_on_the_availability_clock(self):
        with tempfile.TemporaryDirectory() as root:
            head = ("ts_event_ns,ts_recv_ns,exchange_send_ns,sequence,feed,instrument_id,symbol,price,"
                    "price_index_points,size,side,aggressor_side,update_action,rpt_seq,md_trade_entry_id,"
                    "number_of_orders,template_id")
            with open(os.path.join(root, "trades.csv"), "w", newline="") as handle:
                handle.write(head + "\n")
                handle.write(f"1,1,{START + 300},{2},A,3445,ESU3,453675000000000,4536.75,4,B,1,New,1,1,4,48\n")
                handle.write(f"1,1,{START + 100},{1},A,314863,ESZ3,458625000000000,4586.25,4,B,1,New,1,1,4,48\n")
                handle.write(f"1,1,{START + 200},{3},A,3445,ESU3,453675000000000,4536.75,9,S,2,New,1,1,9,48\n")
            trades = es.load_trades(os.path.join(root, "trades.csv"), 3445, "exchange_send_ns")
        self.assertEqual(list(trades["time_ns"]), [START + 200, START + 300])
        self.assertEqual(list(trades["aggressor"]), [2, 1])


class FreezeGateTests(unittest.TestCase):
    def _freeze(self, module_hash: str, input_hash: str) -> dict:
        return {
            "code_sha256": {"M2/src/es_materiality.py": module_hash},
            "input_sha256": {"M2/data/derived_es/2023-07-17T133000Z/trades.csv": input_hash},
            "reused_module_sha256": {},
        }

    def _seal(self, freeze: dict) -> tuple[str, str]:
        """Write contract + companion hash the way the campaign seals them."""
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "freeze.json")
        with open(path, "w") as handle:
            json.dump(freeze, handle, indent=2, sort_keys=True)
        digest = es.sha256_file(path)
        with open(os.path.join(directory, "freeze.sha256"), "w") as handle:
            handle.write(f"{digest}  freeze.json\n")
        return path, digest

    def test_the_module_hash_is_a_hard_gate(self):
        path, _ = self._seal(self._freeze("0" * 64, "irrelevant"))
        with self.assertRaises(es.MeasurementError):
            es.verify_freeze(self._freeze("0" * 64, "irrelevant"), path)

    def test_a_declared_input_that_changed_since_the_freeze_is_a_hard_gate(self):
        freeze = self._freeze(es.sha256_file("M2/src/es_materiality.py"), "0" * 64)
        path, _ = self._seal(freeze)
        with self.assertRaises(es.MeasurementError):
            es.verify_freeze(freeze, path)

    def test_a_contract_altered_after_the_seal_is_a_hard_gate(self):
        freeze = self._freeze(es.sha256_file("M2/src/es_materiality.py"), "irrelevant")
        path, _ = self._seal(freeze)
        tampered = dict(freeze, note="added after the seal")
        with open(path, "w") as handle:
            json.dump(tampered, handle, indent=2, sort_keys=True)
        with self.assertRaises(es.MeasurementError):
            es.verify_freeze(tampered, path)

    def test_a_matching_freeze_verifies_and_reports_every_hash(self):
        relative = "M2/src/es_materiality.py"
        freeze = {
            "code_sha256": {relative: es.sha256_file(relative)},
            "input_sha256": {},
            "reused_module_sha256": {"M2/src/envelope.py": es.sha256_file("M2/src/envelope.py")},
        }
        path, digest = self._seal(freeze)
        report = es.verify_freeze(freeze, path)
        self.assertTrue(report["analysis_module"]["unchanged"])
        self.assertTrue(report["sealed_contract"]["unchanged"])
        self.assertEqual(report["sealed_contract"]["declared"], digest)
        self.assertTrue(report["reused_modules"]["M2/src/envelope.py"]["unchanged"])


class EndToEndTests(unittest.TestCase):
    """``run()`` end-to-end on a synthetic 6-second tape, over the sealed key set.

    The freeze used here is a copy of the sealed contract with only the data paths, the
    hashes, the horizons and the floors replaced, so the wiring is exercised against the
    same key set the real measurement reads and the fixture cannot fall behind it.
    """

    FREEZE = "M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json"
    MID = 4536.75
    GRID_POINTS = 600

    def setUp(self):
        if not os.path.exists(es.config_module.repo_path(self.FREEZE)):
            self.skipTest("sealed contract not yet written; the sealed run is the end-to-end proof")
        with open(es.config_module.repo_path(self.FREEZE)) as handle:
            self.freeze = json.load(handle)
        self.root = tempfile.mkdtemp()
        self.start = START
        self.end = START + self.GRID_POINTS * STEP

    def _write_dataset(self) -> str:
        data_dir = os.path.join(self.root, "derived")
        os.makedirs(data_dir)
        half = 0.125
        mid = np.where(np.arange(self.GRID_POINTS) >= 300, self.MID + 0.25, self.MID)
        with open(os.path.join(data_dir, "spread_grid.csv"), "w", newline="") as handle:
            handle.write("grid_index,ts_ns,bid_px,ask_px,bid_sz,ask_sz,spread_ticks,spread_points,"
                         "half_spread_points,half_spread_ticks\n")
            for index, value in enumerate(mid):
                handle.write(f"{index},{self.start + index * STEP},{(value - half) / SCALE:.0f},"
                             f"{(value + half) / SCALE:.0f},4,6,1.0,0.25,0.125,0.5\n")
        with open(os.path.join(data_dir, "bbo_increments.csv"), "w", newline="") as handle:
            handle.write("ts_event_ns,ts_recv_ns,exchange_send_ns,sequence,feed,instrument_id,symbol,"
                         "side,price,price_index_points,size,flag,rpt_seq,md_price_level,update_action,"
                         "entry_type,template_id\n")
            for offset, value in ((0, self.MID), (300 * STEP, self.MID + 0.25)):
                for side, price in (("B", value - half), ("A", value + half)):
                    stamp = self.start + offset
                    handle.write(f"{stamp},{stamp + 1000},{stamp},1,A,3445,ESU3,{side},{price / SCALE:.0f},"
                                 f"{price},5,direct_l1,1,1,Change,1,46\n")
        with open(os.path.join(data_dir, "trades.csv"), "w", newline="") as handle:
            handle.write("ts_event_ns,ts_recv_ns,exchange_send_ns,sequence,feed,instrument_id,symbol,"
                         "price,price_index_points,size,side,aggressor_side,update_action,rpt_seq,"
                         "md_trade_entry_id,number_of_orders,template_id\n")
            offsets = [-500_000_000] + [k * SECOND + 500_000_000 for k in range(5)]
            for index, offset in enumerate(offsets):
                stamp = self.start + offset
                handle.write(f"{stamp},{stamp + 1000},{stamp},{index},A,3445,ESU3,"
                             f"{self.MID / SCALE:.0f},{self.MID},10,B,1,New,{index},{index},10,48\n")
        manifest = {
            "branch": "ES",
            "instrument": {"symbol": "ESU3", "venue": "CME", "security_id": 3445},
            "session": {"session_open_ns": int(self.start), "session_close_ns": int(self.end)},
            "coverage": {"ratio": 1.0},
        }
        with open(os.path.join(data_dir, "admission.json"), "w") as handle:
            json.dump(manifest, handle)
        return data_dir

    def test_run_reproduces_a_hand_computed_window(self):
        data_dir = self._write_dataset()
        freeze = json.loads(json.dumps(self.freeze))
        freeze["data"]["derived_dir"] = data_dir
        freeze["horizons_s"] = [1, 2]
        freeze["horizons"]["primary_s"] = 1
        freeze["coverage_floor"] = {"quote_coverage_min": 0.5, "observation_coverage_min": 0.5,
                                    "min_observations": 1}
        freeze["input_sha256"] = {
            os.path.join(data_dir, name): es.sha256_file(os.path.join(data_dir, name))
            for name in ("spread_grid.csv", "bbo_increments.csv", "trades.csv", "admission.json")
        }
        path = os.path.join(self.root, "freeze.json")
        with open(path, "w") as handle:
            json.dump(freeze, handle, indent=2, sort_keys=True)
        with open(os.path.join(self.root, "freeze.sha256"), "w") as handle:
            handle.write(f"{es.sha256_file(path)}  freeze.json\n")

        results = es.run(freeze, path)
        headline = results["headline"]
        one_tick_bps = 0.25 / self.MID * 1e4
        # The mid steps up by one tick at t = 3 s, so exactly the slot whose forward
        # window crosses that instant earns a markout, and the friction denominator is
        # the entry mid of each slot.
        entry_mids = [self.MID] * 3 + [self.MID + 0.25] * 2
        expected_c0 = sum(0.25 / value * 1e4 for value in entry_mids) / 5.0
        self.assertEqual(results["verdict"], envelope.VERDICT_KILL)
        self.assertEqual(results["classification"]["clause"], es.CLAUSE_UPPER_AT_OR_BELOW_C0)
        self.assertEqual(results["classification"]["scope"], es.SCOPE_SAMPLE_SCOPED_KILL)
        self.assertEqual(headline["observations"], 5)
        self.assertEqual(headline["horizon_s"], 1)
        self.assertAlmostEqual(headline["gross_markout_bps"], one_tick_bps / 5.0, places=12)
        self.assertAlmostEqual(headline["c0_bps"], expected_c0, places=12)
        self.assertAlmostEqual(headline["c_star_bps"], headline["gross_markout_bps"] - headline["c0_bps"])
        self.assertLess(headline["c_star_bps"], 0.0)
        self.assertEqual(headline["clusters"], 1)
        self.assertEqual(results["per_horizon"][0]["quote_coverage"], 1.0)
        self.assertEqual(results["per_horizon"][0]["state_long"], 5)
        self.assertEqual(results["per_horizon"][0]["state_short"], 0)
        self.assertEqual(results["validity_checks"]["grid_causality_audit"]["agreement_fraction"], 1.0)
        self.assertEqual(results["per_state"][0]["state"], es.STATE_LONG)
        self.assertIsNone(results["c0_c1"]["c1_value"])
        self.assertEqual(results["classification"]["coverage_gate_passed"], True)


if __name__ == "__main__":
    unittest.main()
