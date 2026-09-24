"""Tests for the M2-2 microprice estimator and the materiality arithmetic.

The properties that decide the gate, and therefore the properties worth pinning:

* the calibration is causal - the estimate attached to an observation is a function of
  strictly earlier session data, so a future observation can never change it;
* a cell without the frozen minimum of prior resolved observations carries NO estimate
  (it is never imputed, and never silently replaced by a zero adjustment);
* the strength bands fall on the frozen edges of ``abs(D)/half_spread``;
* the reported signal is exactly the mean side-signed mid move of the microprice's own
  direction, and the reported requirement is exactly ``hurdle / abs(signal)`` - with a
  zero, missing or wrongly-signed signal reported as failure rather than as a number;
* the replay carries the calibration target: the size of the next real mid-price
  change, in the same units as the midpoint, on the same event as its direction.
"""

from __future__ import annotations

import os
import unittest

import numpy as np
import pyarrow.parquet as pq

from M2.src import config as config_module
from M2.src import micro
from M2.tests.test_m2 import (
    BASE_NS,
    MS,
    add_order,
    directory_for,
    summary_for,
    test_config,
    write_tape,
)
from M2.src import book as book_module

SECOND = 1_000_000_000


class CalibrationTests(unittest.TestCase):
    def test_expanding_calibration_never_uses_the_current_or_later_block(self):
        # One cell, three blocks. Block 0 has no prior data; block 1 must see block 0
        # only; block 2 must see blocks 0-1 only.
        cell = np.array([0, 0, 0, 0])
        block = np.array([0, 1, 2, 2])
        delta = np.array([10.0, 20.0, 1000.0, 1000.0])
        usable = np.ones(4, dtype=bool)
        g1 = micro.expanding_calibration(cell, block, delta, usable, 1, 3, 1)
        self.assertTrue(np.isnan(g1[0, 0]))
        self.assertEqual(g1[0, 1], 10.0)
        self.assertEqual(g1[0, 2], 15.0)

    def test_a_later_block_cannot_change_an_earlier_estimate(self):
        cell = np.array([0, 0, 0])
        block = np.array([0, 1, 2])
        usable = np.ones(3, dtype=bool)
        before = micro.expanding_calibration(cell, block, np.array([1.0, 2.0, 3.0]), usable, 1, 3, 1)
        after = micro.expanding_calibration(cell, block, np.array([1.0, 2.0, 999.0]), usable, 1, 3, 1)
        self.assertEqual(before[0, 1], after[0, 1])
        self.assertEqual(before[0, 2], after[0, 2])

    def test_minimum_observations_is_enforced_and_never_imputed(self):
        cell = np.array([0, 0, 0])
        block = np.array([0, 0, 1])
        delta = np.array([5.0, 7.0, 0.0])
        usable = np.array([True, True, False])
        g1 = micro.expanding_calibration(cell, block, delta, usable, 1, 2, 3)
        self.assertTrue(np.isnan(g1[0, 1]))
        g1_loose = micro.expanding_calibration(cell, block, delta, usable, 1, 2, 2)
        self.assertEqual(g1_loose[0, 1], 6.0)

    def test_unresolved_observations_never_enter_the_calibration_mean(self):
        cell = np.array([0, 0])
        block = np.array([0, 0])
        delta = np.array([4.0, 400.0])  # the second row is unresolved and must be ignored
        usable = np.array([True, False])
        g1 = micro.expanding_calibration(cell, block, delta, usable, 1, 2, 1)
        self.assertEqual(g1[0, 1], 4.0)

    def test_pooled_calibration_is_the_whole_sample_mean_and_is_not_the_causal_rule(self):
        cell = np.array([0, 0, 1])
        delta = np.array([2.0, 4.0, 8.0])
        usable = np.ones(3, dtype=bool)
        pooled = micro.pooled_calibration(cell, delta, usable, 2)
        self.assertEqual(pooled[0], 3.0)
        self.assertEqual(pooled[1], 8.0)


class StateAndBandTests(unittest.TestCase):
    def test_strength_bands_follow_the_frozen_edges(self):
        edges = [0.0, 0.02, 0.05, 0.10, 0.20]
        ratio = np.array([0.0, 0.019, 0.02, 0.049, 0.05, 0.099, 0.10, 0.199, 0.20, 5.0, np.nan])
        bands = micro.strength_bands(ratio, edges)
        self.assertEqual(list(bands[:10]), [0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
        self.assertEqual(bands[10], -1)

    def test_state_cell_is_a_mixed_radix_pair_and_undefined_outside(self):
        configuration = config_module.load()
        imbalance = np.array([-0.9, 0.9, 0.0, 0.5])
        spread = np.array([100, 200, 100, 100], dtype=np.int64)
        valid = np.array([True, True, True, False])
        cell, bin_labels, spread_labels = micro.state_cell(imbalance, spread, valid, configuration)
        n_spread = len(spread_labels)
        self.assertEqual(cell[0], 0 * n_spread + 0)
        self.assertEqual(cell[1], 9 * n_spread + 1)
        self.assertEqual(cell[2], 5 * n_spread + 0)
        self.assertEqual(cell[3], -1)
        self.assertEqual(len(bin_labels), 10)

    def test_lookup_returns_nan_where_the_cell_or_the_block_has_no_estimate(self):
        table = np.array([[1.0, np.nan], [2.0, 3.0]])
        cell = np.array([0, 0, -1])
        block = np.array([0, 1, 0])
        out = micro.lookup(table, cell, block)
        self.assertEqual(out[0], 1.0)
        self.assertTrue(np.isnan(out[1]))  # the cell exists, this block has no estimate
        self.assertTrue(np.isnan(out[2]))  # no state code at all


class MaterialityTests(unittest.TestCase):
    def _frame(self, moves, half_entry, half_future, fee_long, fee_short):
        future = {
            "usable_state": np.ones(len(moves), dtype=bool),
            "future_mid_move_bps": np.asarray(moves, dtype=float),
            "half_spread_future_bps": np.full(len(moves), half_future),
        }
        return {
            "horizons": {1000: future},
            "fees": {"STRUCTURAL": {"long": np.full(len(moves), fee_long), "short": np.full(len(moves), fee_short)}},
            "half_spread_entry_bps": np.full(len(moves), half_entry),
            "spread_bps": np.full(len(moves), 4.0),
            "price_usd": np.full(len(moves), 50.0),
            "locate": np.zeros(len(moves), dtype=np.int64),
            "block_id": np.zeros(len(moves), dtype=np.int64),
        }

    def test_signal_is_the_mean_side_signed_move_and_required_is_hurdle_over_signal(self):
        # Two long and two short observations: the signal is the mean of the signed moves.
        frame = self._frame([10.0, -6.0, 2.0, -2.0], half_entry=3.0, half_future=1.0, fee_long=1.5, fee_short=1.5)
        side = np.array([1.0, -1.0, 1.0, -1.0])
        defined = np.ones(4, dtype=bool)
        rows, best = micro.horizon_rows(frame, side, defined, "STRUCTURAL", [1000], 50, 7)
        row = rows[0]
        self.assertAlmostEqual(row["mean_signed_mid_move_bps"], (10.0 + 6.0 + 2.0 + 2.0) / 4.0)
        self.assertAlmostEqual(row["hurdle_bps"], 5.5)
        self.assertAlmostEqual(row["required_over_signal"], 5.5 / 5.0)
        self.assertEqual(best["horizon_ms"], 1000)

    def test_a_wrongly_signed_or_empty_signal_is_a_failure_not_a_number(self):
        self.assertEqual(micro._required_over_signal(4.0, -0.1), float("inf"))
        self.assertEqual(micro._required_over_signal(4.0, 0.0), float("inf"))
        self.assertEqual(micro._required_over_signal(4.0, float("nan")), float("inf"))
        self.assertAlmostEqual(micro._required_over_signal(4.0, 0.25), 16.0)

    def test_fee_and_spread_terms_are_side_dependent_in_the_hurdle(self):
        frame = self._frame([1.0, 1.0], half_entry=2.0, half_future=2.0, fee_long=1.0, fee_short=3.0)
        side = np.array([1.0, -1.0])
        rows, _ = micro.horizon_rows(frame, side, np.ones(2, dtype=bool), "STRUCTURAL", [1000], 50, 7)
        self.assertAlmostEqual(rows[0]["hurdle_bps"], (2.0 + 2.0 + 1.0 + 2.0 + 2.0 + 3.0) / 2.0)

    def test_group_rows_requires_the_frozen_minimum_sample_to_be_eligible(self):
        frame = self._frame([4.0, 4.0, 4.0, 4.0], half_entry=2.0, half_future=0.0, fee_long=0.0, fee_short=0.0)
        codes = np.array([0, 0, 0, 1])
        side = np.ones(4)
        rows, best = micro.group_rows(
            frame, codes, ["a", "b"], "dimension", side, np.ones(4, dtype=bool),
            np.ones(4), "STRUCTURAL", [1000], 3, 50, 7,
        )
        eligibility = {row["state"]: row["eligible_for_best"] for row in rows}
        self.assertTrue(eligibility["a"])
        self.assertFalse(eligibility["b"])
        self.assertEqual(best["state"], "a")


class VerdictRuleTests(unittest.TestCase):
    def _result(self, r_pooled, r_best, oracle_per_observation, hurdle=4.0):
        return {
            "population": "synthetic",
            "best_horizon": {"horizon_ms": 5000},
            "best_state": {"dimension": "strength_band", "state": "gte_0.20", "horizon_ms": 5000,
                           "required_over_signal": r_best},
            "pooled_by_horizon": {5000: {"required_over_signal": r_pooled, "hurdle_bps": hurdle,
                                         "mean_signed_mid_move_bps": hurdle / r_pooled}},
            "oracle_table": [{"horizon_ms": 5000, "oracle_net_floor_bps_per_observation": oracle_per_observation}],
        }

    def _thresholds(self):
        return {"r_best_kill": 5.0, "r_pooled_kill": 10.0, "minimum_state_observations": 10000,
                "oracle_contradiction_ratio": 0.25, "freeze_sha256": "x", "freeze_status": "y"}

    def test_kill_needs_both_conditions(self):
        verdict = micro.apply_frozen_rule(self._result(51.6, 10.7, 0.0097), self._thresholds())
        self.assertEqual(verdict["terminal_state"], "KILLED")
        self.assertFalse(verdict["oracle_contradiction"])

    def test_one_loose_condition_survives(self):
        self.assertEqual(
            micro.apply_frozen_rule(self._result(51.6, 4.9, 0.0097), self._thresholds())["terminal_state"],
            "SURVIVES_PRE_GATE",
        )
        self.assertEqual(
            micro.apply_frozen_rule(self._result(9.9, 10.7, 0.0097), self._thresholds())["terminal_state"],
            "SURVIVES_PRE_GATE",
        )

    def test_a_wrongly_signed_signal_is_a_failure_and_is_killed(self):
        # A zero, missing or negative signal is worse than a small positive one: the
        # frozen rule treats it as failure (infinite requirement), so it can never be
        # read as a passing state.
        result = self._result(float("inf"), 10.7, 0.0097)
        verdict = micro.apply_frozen_rule(result, self._thresholds())
        self.assertEqual(verdict["terminal_state"], "KILLED")
        self.assertEqual(verdict["R_pooled"], float("inf"))

    def test_large_clairvoyant_room_is_reported_as_a_contradiction_not_a_kill(self):
        verdict = micro.apply_frozen_rule(self._result(51.6, 10.7, 1.5), self._thresholds())
        self.assertEqual(verdict["terminal_state"], "SURVIVES_PRE_GATE_ORACLE_CONTRADICTION")
        self.assertTrue(verdict["oracle_contradiction"])
        self.assertAlmostEqual(verdict["oracle_ratio_at_primary_horizon"], 0.375)


class ReplayLabelTests(unittest.TestCase):
    def test_next_move_delta_is_the_size_of_the_next_mid_change(self):
        frames = [
            add_order(1, BASE_NS + 1 * MS, 1000, "B", 500, 10_000),
            add_order(1, BASE_NS + 1 * MS, 1001, "S", 500, 10_100),
            # A better ask arrives mid-session: mid2 falls from 20,100 to 20,050.
            add_order(1, BASE_NS + 350 * MS, 1002, "S", 500, 10_050),
        ]
        path = write_tape(frames)
        self.addCleanup(os.unlink, path)
        configuration = test_config(horizons_ms=[1000], delay_ms=[0], buffer_rows_per_chunk=2_000_000)
        replayer = book_module.Replayer(
            configuration,
            summary_for({1: 100}, {1: 12_000}),
            directory_for({1: "TEST"}),
        )
        replayer.run(path)
        derived = config_module.repo_path(config_module.derived_dir(configuration))
        table = pq.read_table(
            os.path.join(derived, "decisions.parquet"),
            columns=["next_move_direction", "next_move_delta_raw", "next_move_resolved", "mid2_raw"],
        )
        direction = table["next_move_direction"].to_numpy(zero_copy_only=False)
        delta = table["next_move_delta_raw"].to_numpy(zero_copy_only=False)
        resolved = table["next_move_resolved"].to_numpy(zero_copy_only=False)
        mid2 = table["mid2_raw"].to_numpy(zero_copy_only=False)
        self.assertTrue(resolved.any())
        self.assertTrue(np.all(delta[resolved] == -50))
        self.assertTrue(np.all(direction[resolved] == -1))
        # Every row that resolved before the move carries the pre-move midpoint.
        self.assertTrue(np.all(mid2[resolved] == 20_100))


if __name__ == "__main__":  # pragma: no cover - test runner entry point
    unittest.main()
