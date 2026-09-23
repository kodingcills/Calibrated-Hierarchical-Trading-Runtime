"""Tests for the M2-0.5 aggressive feasibility bound.

The subject here is the arithmetic and the bookkeeping of the feasibility pass: the
per-observation decomposition of an aggressive round trip, the break-even hurdle and its
relation to the cross-to-cross result, the two labelled bounds, the declared state
partition, and the relation this pass claims to the frozen M2-0 execution table.

They deliberately do not re-test the M2-0 replay, the cost ledger's own line items or the
one-to-one comparison against the real frozen artifacts: that comparison runs on every
execution of the pass, is blocking, and is reported in `feasibility_status.json`.
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import tempfile
import unittest

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from M2.src import calculate
from M2.src import config as config_module
from M2.src import costs
from M2.src import feasibility
from M2.tests.test_m2 import CostArithmeticTests, test_config

_TEST_ROOT = tempfile.mkdtemp(prefix="m2-feasibility-root-")
atexit.register(shutil.rmtree, _TEST_ROOT, ignore_errors=True)

# Raw prices are ITCH Price(4): $1.00 is 10000 raw units, so one cent is 100.
# The pure-arithmetic tests use a $1.00 stock (outside the declared price bands, which is
# immaterial when no band is read); the state-space tests use a $50.00 stock so that every
# row lands inside a declared band.
ONE_DOLLAR = 10_000
FIFTY = 50 * 10_000


def ledger() -> dict:
    return CostArithmeticTests()._ledger()


def configuration() -> dict:
    settings = test_config()
    settings["statistics"]["bootstrap"]["resamples"] = 64
    return settings


def quote_columns(
    rows: list[dict], settings: dict, horizons_ms: tuple[int, ...] = (100, 250, 500, 1000)
) -> dict:
    """Build the delay-0 column dict `build_frame` consumes from explicit quotes."""
    count = len(rows)
    columns: dict = {
        "ts_ns": np.array([row.get("ts_ns", 36_000_000_000_000 + index) for index, row in enumerate(rows)], dtype=np.int64),
        "locate": np.array([row.get("locate", 1) for row in rows], dtype=np.int32),
        "block_id": np.array([row.get("block_id", 0) for row in rows], dtype=np.int16),
        "imbalance": np.array([row["imbalance"] for row in rows], dtype=np.float32),
        "mid2_raw": np.array([row["entry_bid"] + row["entry_ask"] for row in rows], dtype=np.int64),
        "spread_raw": np.array([row["entry_ask"] - row["entry_bid"] for row in rows], dtype=np.int32),
        "entry_bid": np.array([row["entry_bid"] for row in rows], dtype=np.int32),
        "entry_ask": np.array([row["entry_ask"] for row in rows], dtype=np.int32),
        "arrival_status": np.zeros(count, dtype=np.int8),
    }
    for horizon_ms in horizons_ms:
        columns[f"fut_bid_{horizon_ms}"] = np.array(
            [row.get(f"fut_bid_{horizon_ms}", row["entry_bid"]) for row in rows], dtype=np.int32
        )
        columns[f"fut_ask_{horizon_ms}"] = np.array(
            [row.get(f"fut_ask_{horizon_ms}", row["entry_ask"]) for row in rows], dtype=np.int32
        )
    return columns


def one_row(**overrides) -> dict:
    row = {
        "imbalance": 0.5,
        "entry_bid": ONE_DOLLAR,
        "entry_ask": ONE_DOLLAR + 10,
        "fut_bid_100": ONE_DOLLAR + 30,
        "fut_ask_100": ONE_DOLLAR + 40,
    }
    row.update(overrides)
    return row


class DecompositionTests(unittest.TestCase):
    def _frame(self, rows: list[dict]) -> dict:
        settings = configuration()
        return feasibility.build_frame(quote_columns(rows, settings), settings, ledger())

    def test_decomposition_is_an_exact_identity(self):
        frame = self._frame(
            [one_row(), one_row(imbalance=-0.5, fut_bid_100=ONE_DOLLAR - 20, fut_ask_100=ONE_DOLLAR - 10)]
        )
        horizon = frame["horizons"][100]
        mask = horizon["usable_signal"]
        half_entry = frame["half_spread_entry_bps"][mask]
        half_future = horizon["half_spread_future_bps"][mask]
        realized = horizon["realized_move_bps"][mask]
        self.assertTrue(np.allclose(horizon["markout_bps"][mask], realized - half_entry, atol=1e-12))
        self.assertTrue(
            np.allclose(horizon["cross_to_cross_bps"][mask], realized - half_entry - half_future, atol=1e-12)
        )
        for label in feasibility.schedule_labels(ledger()):
            fee = horizon[f"fee_{label}_bps"][mask]
            self.assertTrue(
                np.allclose(horizon[f"net_{label}_bps"][mask], horizon["cross_to_cross_bps"][mask] - fee, atol=1e-12)
            )

    def test_cross_to_cross_is_the_raw_quote_arithmetic_in_bps_of_the_mid(self):
        frame = self._frame([one_row(imbalance=0.25, fut_bid_100=ONE_DOLLAR + 40, fut_ask_100=ONE_DOLLAR + 50)])
        horizon = frame["horizons"][100]
        mask = horizon["usable_signal"]
        mid2 = float(frame["mid2"][mask][0])
        measured = float(horizon["cross_to_cross_bps"][mask][0])
        # An aggressive buy at the arrival ask closed at the future bid, in bps of the mid:
        # (fut_bid - entry_ask) / mid * 10000, with mid = mid2 / 2.
        expected_long = 20000.0 * ((ONE_DOLLAR + 40) - (ONE_DOLLAR + 10)) / mid2
        # The frozen M2-0 expression divides the same price difference by mid2 as if it were
        # the mid, so it reports exactly half of this.
        frozen_expression = 10000.0 * ((ONE_DOLLAR + 40) - (ONE_DOLLAR + 10)) / mid2
        self.assertAlmostEqual(measured, expected_long, places=10)
        self.assertAlmostEqual(measured, 2 * frozen_expression, places=10)

    def test_known_values_on_a_hand_checked_row(self):
        frame = self._frame([one_row()])
        horizon = frame["horizons"][100]
        mid2 = 2 * ONE_DOLLAR + 10
        self.assertAlmostEqual(float(horizon["realized_move_bps"][0]), 10000.0 * 60.0 / mid2, places=10)
        self.assertAlmostEqual(float(horizon["half_spread_future_bps"][0]), 10000.0 * 10.0 / mid2, places=10)
        self.assertAlmostEqual(float(horizon["markout_bps"][0]), 10000.0 * 50.0 / mid2, places=10)
        self.assertAlmostEqual(float(horizon["cross_to_cross_bps"][0]), 20000.0 * 20.0 / mid2, places=10)

    def test_side_dependent_quantities_are_undefined_without_a_signal_side(self):
        frame = self._frame([one_row(imbalance=0.0)])
        horizon = frame["horizons"][100]
        self.assertTrue(frame["state_valid"][0])
        self.assertFalse(frame["signal_defined"][0])
        self.assertTrue(np.isnan(horizon["realized_move_bps"][0]))
        self.assertTrue(np.isnan(horizon["cross_to_cross_bps"][0]))
        # The side-independent pieces stay defined, which is what the oracle set needs.
        self.assertTrue(np.isfinite(horizon["cross_long_bps"][0]))
        self.assertTrue(np.isfinite(horizon["cross_short_bps"][0]))

    def test_fee_is_the_ledger_at_the_true_entry_price(self):
        settings = configuration()
        book = ledger()
        frame = feasibility.build_frame(quote_columns([one_row(), one_row(imbalance=-0.5)], settings), settings, book)
        shares = float(book["assumptions"]["representative_order_shares"])
        long_fee = costs.cost_in_bps_of_price(
            book, "STRUCTURAL_COST_FLOOR", None, shares, (ONE_DOLLAR + 10) / 10000.0
        )
        short_fee = costs.cost_in_bps_of_price(book, "STRUCTURAL_COST_FLOOR", None, shares, ONE_DOLLAR / 10000.0)
        self.assertAlmostEqual(frame["fees"]["floor"]["long"][0], long_fee, places=10)
        self.assertAlmostEqual(frame["fees"]["floor"]["short"][0], short_fee, places=10)
        horizon = frame["horizons"][100]
        self.assertAlmostEqual(horizon["fee_floor_bps"][0], long_fee, places=10)
        self.assertAlmostEqual(horizon["fee_floor_bps"][1], short_fee, places=10)


class HurdleTests(unittest.TestCase):
    def test_hurdle_is_the_spread_and_the_realized_move_is_the_signed_mid_move(self):
        settings = configuration()
        rows = [
            one_row(entry_bid=ONE_DOLLAR, entry_ask=ONE_DOLLAR + 100, fut_bid_100=ONE_DOLLAR + 50, fut_ask_100=ONE_DOLLAR + 60),
            one_row(
                imbalance=-0.5,
                entry_bid=ONE_DOLLAR,
                entry_ask=ONE_DOLLAR + 100,
                fut_bid_100=ONE_DOLLAR - 50,
                fut_ask_100=ONE_DOLLAR - 40,
            ),
            one_row(entry_bid=ONE_DOLLAR, entry_ask=ONE_DOLLAR + 100, fut_bid_100=ONE_DOLLAR + 300, fut_ask_100=ONE_DOLLAR + 310),
        ]
        frame = feasibility.build_frame(quote_columns(rows, settings), settings, ledger())
        horizon = frame["horizons"][100]
        expected_spread = 20000.0 * 100.0 / frame["mid2"]
        self.assertTrue(np.allclose(frame["spread_bps"], expected_spread, atol=1e-9))
        # The spread is 99.5 bps of the mid: the first two rows move the mid by far less than
        # that and the third clears it, so the hurdle discriminates in both directions.
        self.assertTrue(np.all(horizon["realized_move_bps"][:2] < frame["spread_bps"][:2]))
        self.assertGreater(float(horizon["realized_move_bps"][2]), float(frame["spread_bps"][2]))

    def test_spread_hurdle_equals_cross_to_cross_when_the_future_spread_is_unchanged(self):
        settings = configuration()
        rows = [
            one_row(entry_bid=ONE_DOLLAR, entry_ask=ONE_DOLLAR + 20, fut_bid_100=ONE_DOLLAR + 40, fut_ask_100=ONE_DOLLAR + 60),
            one_row(
                imbalance=-0.5,
                entry_bid=ONE_DOLLAR,
                entry_ask=ONE_DOLLAR + 20,
                fut_bid_100=ONE_DOLLAR - 60,
                fut_ask_100=ONE_DOLLAR - 40,
            ),
        ]
        frame = feasibility.build_frame(quote_columns(rows, settings), settings, ledger())
        horizon = frame["horizons"][100]
        mask = horizon["usable_signal"]
        self.assertTrue(np.allclose(horizon["spread_change_term_bps"][mask], 0.0, atol=1e-12))
        exceeded = (horizon["realized_move_bps"][mask] > frame["spread_bps"][mask]).astype(int)
        crossed = (horizon["cross_to_cross_bps"][mask] > 0).astype(int)
        self.assertTrue(np.array_equal(exceeded, crossed))

    def test_breakeven_table_reports_ordered_hurdles_and_agrees_with_the_net_columns(self):
        settings = configuration()
        rows = [
            one_row(imbalance=0.9, entry_bid=FIFTY, entry_ask=FIFTY + 10),
            one_row(imbalance=-0.9, entry_bid=FIFTY, entry_ask=FIFTY + 10, fut_bid_100=FIFTY - 20, fut_ask_100=FIFTY - 10),
            one_row(imbalance=0.0, entry_bid=FIFTY, entry_ask=FIFTY + 10, fut_bid_100=FIFTY + 20, fut_ask_100=FIFTY + 30),
        ]
        frame = feasibility.build_frame(quote_columns(rows, settings), settings, ledger())
        book = ledger()
        table = feasibility.breakeven_rows(frame, settings, book, (100,))
        self.assertEqual(len(table), 100)
        populated = [row for row in table if row["observations"]]
        self.assertTrue(populated)
        for row in populated:
            self.assertLessEqual(row["required_move_bps_spread_only"], row["required_move_bps_spread_plus_floor"])
            for label in feasibility.schedule_labels(book):
                self.assertLessEqual(
                    row["required_move_bps_spread_plus_floor"], row["required_move_bps_spread_plus_" + label]
                )
            self.assertEqual(row["label"], feasibility.LABEL_BREAKEVEN)


class BoundTests(unittest.TestCase):
    def _frame(self, rows: list[dict]) -> dict:
        settings = configuration()
        return feasibility.build_frame(quote_columns(rows, settings), settings, ledger())

    def test_oracle_dominates_every_fixed_side_and_abstention(self):
        frame = self._frame(
            [
                one_row(),
                one_row(imbalance=-0.5, fut_bid_100=ONE_DOLLAR - 20, fut_ask_100=ONE_DOLLAR - 10),
                one_row(imbalance=0.0),
            ]
        )
        horizon = frame["horizons"][100]
        for label in feasibility.schedule_labels(ledger()):
            bound = horizon[f"oracle_net_{label}_bps"]
            long_net = horizon["cross_long_bps"] - frame["fees"][label]["long"]
            short_net = horizon["cross_short_bps"] - frame["fees"][label]["short"]
            self.assertTrue(np.all(bound >= np.maximum(0.0, np.maximum(long_net, short_net)) - 1e-12))
            self.assertTrue(np.all(bound >= 0.0))
            defined = np.isfinite(horizon[f"net_{label}_bps"])
            self.assertTrue(np.all(bound[defined] >= horizon[f"net_{label}_bps"][defined] - 1e-12))
            # A row with no signal side has no net to compare against, and the oracle still bounds it.
            self.assertTrue(np.all(np.isnan(horizon[f"net_{label}_bps"][~defined])))
            self.assertTrue(np.all(bound[defined] >= horizon[f"qimb_bound_{label}_bps"][defined] - 1e-12))

    def test_qimb_bound_keeps_the_side_the_bin_dictates(self):
        frame = self._frame(
            [
                one_row(imbalance=0.75),
                one_row(imbalance=-0.75, fut_bid_100=ONE_DOLLAR + 100, fut_ask_100=ONE_DOLLAR + 110),
            ]
        )
        horizon = frame["horizons"][100]
        for label in feasibility.schedule_labels(ledger()):
            net = horizon[f"net_{label}_bps"]
            bound = horizon[f"qimb_bound_{label}_bps"]
            # Row 0 is long: its bound is the long net when positive, zero otherwise.
            self.assertAlmostEqual(
                float(bound[0]),
                max(0.0, float(horizon["cross_long_bps"][0] - frame["fees"][label]["long"][0])),
                places=9,
            )
            # Row 1 is short and the short side loses: the bound abstains.
            self.assertLess(float(horizon["cross_short_bps"][1] - frame["fees"][label]["short"][1]), 0.0)
            self.assertAlmostEqual(float(bound[1]), 0.0, places=9)
            self.assertLessEqual(float(net[1]), 0.0)

    def test_oracle_rows_cover_all_valid_states_and_keep_the_signal_subset_separate(self):
        settings = configuration()
        frame = self._frame(
            [
                one_row(imbalance=0.0, entry_bid=FIFTY, entry_ask=FIFTY + 10, fut_bid_100=FIFTY + 400, fut_ask_100=FIFTY + 410),
                one_row(imbalance=0.5, entry_bid=FIFTY, entry_ask=FIFTY + 10, fut_bid_100=FIFTY + 400, fut_ask_100=FIFTY + 410),
            ]
        )
        table = feasibility.oracle_rows(frame, settings, ledger(), (100,))
        self.assertEqual(len(table), 100)
        populated = [row for row in table if row["observations"]]
        self.assertEqual(sum(row["observations"] for row in populated), 2)
        self.assertEqual(sum(row["observations_signal_defined"] for row in populated), 1)
        for row in table:
            self.assertEqual(row["label"], feasibility.LABEL_ORACLE)
            self.assertIn("ORACLE_UPPER_BOUND", row["note"])
            self.assertIn("never enter model training", row["note"])


class StatePartitionTests(unittest.TestCase):
    def _frame(self, rows: list[dict]) -> dict:
        settings = configuration()
        return feasibility.build_frame(quote_columns(rows, settings), settings, ledger())

    def test_price_band_edges_fall_in_the_upper_band(self):
        prices = np.array([4.99, 5.0, 24.99, 25.0, 49.99, 50.0, 99.99, 100.0, 199.99, 200.0, 1_000.0])
        codes = feasibility.band_index(prices)
        self.assertEqual(codes.tolist(), [-1, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
        self.assertEqual(feasibility.band_labels(), ["5-25", "25-50", "50-100", "100-200", "200+"])

    def test_the_state_partition_is_total_and_disjoint(self):
        settings = configuration()
        rows = [
            one_row(imbalance=value, entry_bid=FIFTY, entry_ask=FIFTY + (100 if index % 2 else 10))
            for index, value in enumerate(
                [-1.0, -0.9, -0.7, -0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 0.0]
            )
        ]
        frame = self._frame(rows)
        dimensions = feasibility.state_dimensions(frame, settings)
        codes, n_cells, sizes = feasibility.combine_dimensions(dimensions)
        self.assertEqual(n_cells, 100)
        self.assertEqual([len(labels) for _name, labels, _values in dimensions], sizes)
        masked = codes[frame["signal_defined"]]
        self.assertEqual(int(np.sum(masked >= 0)), int(frame["signal_defined"].sum()))
        counts = np.bincount(masked, minlength=n_cells)
        self.assertEqual(int(counts.sum()), int(frame["signal_defined"].sum()))
        decoded = [feasibility.decode_cell(cell, sizes) for cell in range(n_cells)]
        self.assertEqual(len({tuple(item) for item in decoded}), n_cells)

    def test_tick_classification_and_bin_labels_match_the_frozen_conventions(self):
        settings = configuration()
        rows = [
            one_row(imbalance=0.9, entry_bid=ONE_DOLLAR, entry_ask=ONE_DOLLAR + 100),
            one_row(imbalance=-0.9, entry_bid=ONE_DOLLAR, entry_ask=ONE_DOLLAR + 200),
        ]
        frame = self._frame(rows)
        dimensions = feasibility.state_dimensions(frame, settings)
        labels = {name: values for name, _labels, values in dimensions}
        self.assertEqual(labels["spread_class"].tolist(), [0, 1])
        self.assertEqual(int(labels["imbalance_bin"][0]), 9)
        self.assertEqual(int(labels["imbalance_bin"][1]), 0)


class TableTests(unittest.TestCase):
    def _frame(self, rows: list[dict]) -> dict:
        settings = configuration()
        return feasibility.build_frame(quote_columns(rows, settings), settings, ledger())

    def _rows(self) -> list[dict]:
        """Twenty rows spanning all ten bins, both spread classes and the $25-50 band."""
        rows = []
        for index in range(20):
            base = FIFTY + 100 * index
            rows.append(
                one_row(
                    imbalance=float(-0.95 + 0.1 * index),
                    entry_bid=base,
                    entry_ask=base + (100 if index % 3 else 10),
                    fut_bid_100=base + 20,
                    fut_ask_100=base + 30,
                    block_id=index % 3,
                    locate=1 + index % 2,
                    ts_ns=36_000_000_000_000 + index,
                )
            )
        return rows

    def test_feasibility_table_covers_every_declared_cell_and_accounts_for_every_row(self):
        settings = configuration()
        book = ledger()
        frame = self._frame(self._rows())
        table = feasibility.feasibility_rows(frame, settings, book, settings["statistics"]["bootstrap"], settings["horizons_ms"])
        self.assertEqual(len(table), 400)
        keys = [(row["imbalance_bin"], row["spread_class"], row["price_band"], row["horizon_ms"]) for row in table]
        self.assertEqual(len(set(keys)), 400)
        expected = int(frame["signal_defined"].sum()) * len(settings["horizons_ms"])
        self.assertEqual(sum(row["observations"] for row in table), expected)
        for row in table:
            self.assertEqual(row["label"], feasibility.LABEL_EXECUTION)
            self.assertEqual(row["delay_ms"], 0)
            self.assertEqual(row["cost_ledger_id"], book["ledger_id"])
            for label in feasibility.schedule_labels(book):
                self.assertIn(f"net_{label}_bps", row)
            self.assertIn("block_bootstrap_se_net_floor_bps", row)

    def test_qimb_table_reports_the_bound_at_or_above_the_sign_following_result(self):
        settings = configuration()
        book = ledger()
        frame = self._frame(self._rows())
        table = feasibility.qimb_rows(frame, settings, book, (100,))
        self.assertEqual(len(table), 100)
        for row in table:
            if not row["observations"]:
                continue
            for label in feasibility.schedule_labels(book):
                self.assertGreaterEqual(row[f"qimb_bound_{label}_bps"], row[f"net_{label}_bps"] - 1e-9)
                self.assertAlmostEqual(
                    row[f"abstention_gain_{label}_bps"],
                    row[f"qimb_bound_{label}_bps"] - row[f"net_{label}_bps"],
                    places=9,
                )
            self.assertEqual(row["side_dictated_by"], "SIGN(IMBALANCE)_AT_DECISION")


class FrozenRelationTests(unittest.TestCase):
    """The relation this pass claims to the frozen M2-0 execution table."""

    def _settings(self) -> dict:
        settings = configuration()
        settings["paths"]["output_dir"] = tempfile.mkdtemp(prefix="m2-feasibility-frozen-", dir=_TEST_ROOT)
        return settings

    def _frozen(self, settings: dict, markout: float, cross_frozen: float, cost: float) -> str:
        import csv

        directory = config_module.ensure_dirs(settings, "calculations")
        path = os.path.join(directory, "idealized_execution_summary.csv")
        with open(path, "w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["delay_ms", "horizon_ms", "cost_regime", "observations", "mean_gross_markout_bps",
                            "mean_cross_to_cross_bps", "mean_known_cost_bps", "mean_cost_adjusted_bps"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "delay_ms": 0,
                    "horizon_ms": 100,
                    "cost_regime": "floor",
                    "observations": 4,
                    "mean_gross_markout_bps": markout,
                    "mean_cross_to_cross_bps": cross_frozen,
                    "mean_known_cost_bps": cost,
                    "mean_cost_adjusted_bps": markout - cost,
                }
            )
        return path

    def test_missing_reference_is_not_evaluated_rather_than_passed(self):
        settings = self._settings()
        checks, discrepancies = feasibility._frozen_execution_rows(
            settings, {"side": np.array([]), "entry_ask": np.array([]), "entry_bid": np.array([])}, {}, ledger(), {100: {"observations": 0}}
        )
        self.assertTrue(checks)
        self.assertEqual(checks[0]["outcome"], "NOT_EVALUATED_REFERENCE_ABSENT")
        self.assertIn("no comparison is claimed", checks[0]["note"])
        self.assertEqual(discrepancies, [])

    def test_half_price_cost_and_half_bps_cross_are_detected_and_named(self):
        settings = self._settings()
        book = ledger()
        # A three-row sample whose pooled values are known exactly.
        rows = [
            one_row(entry_bid=ONE_DOLLAR, entry_ask=ONE_DOLLAR + 10, fut_bid_100=ONE_DOLLAR + 20, fut_ask_100=ONE_DOLLAR + 30),
            one_row(
                imbalance=-0.5,
                entry_bid=ONE_DOLLAR,
                entry_ask=ONE_DOLLAR + 10,
                fut_bid_100=ONE_DOLLAR - 30,
                fut_ask_100=ONE_DOLLAR - 20,
            ),
            one_row(imbalance=0.25, entry_bid=ONE_DOLLAR, entry_ask=ONE_DOLLAR + 10, fut_bid_100=ONE_DOLLAR, fut_ask_100=ONE_DOLLAR + 10),
        ]
        columns = quote_columns(rows, settings)
        frame = feasibility.build_frame(columns, settings, book)
        horizon = frame["horizons"][100]
        mask = horizon["usable_signal"]
        shares = float(book["assumptions"]["representative_order_shares"])
        true_price = np.where(frame["side"] > 0, frame["entry_ask"], frame["entry_bid"]) / 10000.0
        half_price = true_price / 2.0
        unique, values = calculate._cost_lookup(book, "STRUCTURAL_COST_FLOOR", None, shares, half_price)
        frozen_cost = float(np.nanmean(calculate._map_cost_lookup(unique, values, half_price)[mask]))
        frozen_cross = float(np.nanmean(horizon["cross_to_cross_bps"][mask])) / 2.0
        frozen_markout = float(np.nanmean(horizon["markout_bps"][mask]))
        self._frozen(settings, frozen_markout, frozen_cross, frozen_cost)
        pooled = {
            100: {
                "observations": int(mask.sum()),
                "mean_markout_bps": frozen_markout,
                "mean_cross_to_cross_bps": float(np.nanmean(horizon["cross_to_cross_bps"][mask])),
                "net_floor_bps": float(np.nanmean(horizon["net_floor_bps"][mask])),
            }
        }
        # The re-derivation runs on the full signal-defined set, so pool the same way here.
        pooled[100]["observations"] = int(frame["signal_defined"].sum())
        checks, discrepancies = feasibility._frozen_execution_rows(settings, frame, columns, book, pooled)
        by_name = {row["check"]: row for row in checks}
        self.assertEqual(by_name["frozen_execution_markout_reproduced_exactly"]["outcome"], "FAIL")  # observation totals differ
        self.assertEqual(by_name["frozen_cross_to_cross_is_half_of_true_bps"]["outcome"], "PASS")
        self.assertAlmostEqual(by_name["frozen_cross_to_cross_is_half_of_true_bps"]["max_ratio"], 2.0, places=9)
        self.assertEqual(by_name["frozen_cost_column_is_ledger_at_half_price"]["outcome"], "PASS")
        self.assertEqual(by_name["frozen_execution_adjusted_is_its_own_markout_minus_its_own_cost"]["outcome"], "PASS")
        self.assertEqual([row["id"] for row in discrepancies], ["M2-0-D1", "M2-0-D2", "M2-0-D3"])
        joined = " ".join(row["effect"] for row in discrepancies)
        self.assertIn("half the true basis-point value", joined)
        self.assertIn("half the true price", joined)


class MechanismTests(unittest.TestCase):
    def _bundle(self, signal: float, spread: float, fee: float, net: float, dispersion: float) -> dict:
        pooled = [
            {
                "horizon_ms": horizon_ms,
                "mean_signal_signed_mid_move_bps": signal,
                "mean_full_spread_paid_bps": spread,
                "fee_floor_bps": fee,
                "fee_fixed_bps": fee * 2,
                "fee_tiered_bps": fee * 1.5,
                "net_floor_bps": net,
                "net_fixed_bps": net - fee,
                "net_tiered_bps": net - fee / 2,
            }
            for horizon_ms in (100, 250, 500, 1000)
        ]
        states = [
            {"label_value": "a", "horizon_ms": 1000, "net_floor_bps": net + dispersion / 2},
            {"label_value": "b", "horizon_ms": 1000, "net_floor_bps": net - dispersion / 2},
        ]
        return {
            "schedule_labels": ["floor", "fixed", "tiered"],
            "structural_label": "floor",
            "pooled_by_horizon": pooled,
            "pooled_by_bin_horizon": states,
            "state_space_summary": {"cells_total": 400, "cells_with_positive_net": 0, "best_cell": {}},
            "oracle_pooled_by_horizon": [
                {"horizon_ms": 1000, "oracle_net_floor_bps": 0.01, "oracle_net_fixed_bps": 0.0, "oracle_net_tiered_bps": 0.0}
            ],
        }

    def test_spread_dominance_and_signal_shortfall_are_classified_from_the_decomposition(self):
        verdict = feasibility.mechanism_verdict(self._bundle(signal=0.1, spread=3.0, fee=1.0, net=-3.9, dispersion=0.5))
        self.assertTrue(verdict["flags"]["SPREAD_DOMINATES"])
        self.assertFalse(verdict["flags"]["FEES_DOMINATE"])
        self.assertTrue(verdict["flags"]["SIGNAL_MAGNITUDE_TOO_SMALL"])
        self.assertTrue(verdict["flags"]["POOLED_LOW_QUALITY_STATES"])
        self.assertFalse(verdict["flags"]["WRONG_HORIZON"])
        self.assertAlmostEqual(verdict["by_horizon"][-1]["spread_share_of_required"], 0.75, places=9)

    def test_fee_dominance_and_a_wide_state_space_flip_the_flags(self):
        verdict = feasibility.mechanism_verdict(self._bundle(signal=5.0, spread=1.0, fee=3.0, net=1.0, dispersion=20.0))
        self.assertFalse(verdict["flags"]["SPREAD_DOMINATES"])
        self.assertTrue(verdict["flags"]["FEES_DOMINATE"])
        self.assertFalse(verdict["flags"]["SIGNAL_MAGNITUDE_TOO_SMALL"])
        self.assertFalse(verdict["flags"]["POOLED_LOW_QUALITY_STATES"])

    def test_horizon_flag_requires_the_declared_grid_to_close_half_the_gap(self):
        flat = self._bundle(signal=0.1, spread=3.0, fee=1.0, net=-3.9, dispersion=0.5)
        self.assertFalse(feasibility.mechanism_verdict(flat)["flags"]["WRONG_HORIZON"])
        improving = self._bundle(signal=0.1, spread=3.0, fee=1.0, net=-3.9, dispersion=0.5)
        for index, row in enumerate(improving["pooled_by_horizon"]):
            row["net_floor_bps"] = -3.9 + index * 1.0
        self.assertTrue(feasibility.mechanism_verdict(improving)["flags"]["WRONG_HORIZON"])


class StageIntegrationTests(unittest.TestCase):
    """A synthetic derived directory through the whole pass, including the report."""

    def _derived(self, settings: dict) -> str:
        derived = os.path.join(settings["paths"]["derived_dir"], settings["dataset"]["dataset_id"])
        os.makedirs(derived, exist_ok=True)
        rows = []
        for index in range(12):
            imbalance = float(np.round(-0.9 + 0.15 * index, 2))
            base = ONE_DOLLAR + 50_000 * index
            rows.append(
                {
                    "imbalance": imbalance,
                    "entry_bid": base,
                    "entry_ask": base + (100 if index % 2 else 10),
                    "fut_bid_100": base + 20,
                    "fut_ask_100": base + 30,
                    "fut_bid_250": base + 40,
                    "fut_ask_250": base + 50,
                    "fut_bid_500": base + 60,
                    "fut_ask_500": base + 70,
                    "fut_bid_1000": base + 80,
                    "fut_ask_1000": base + 90,
                }
            )
        columns = quote_columns(rows, settings)
        table = pa.table(
            {
                "ts_ns": columns["ts_ns"],
                "locate": columns["locate"],
                "block_id": columns["block_id"],
                "imbalance": columns["imbalance"],
                "mid2_raw": columns["mid2_raw"],
                "spread_raw": columns["spread_raw"],
                "entry_bid_0ms": columns["entry_bid"],
                "entry_ask_0ms": columns["entry_ask"],
                "arrival_status_0ms": columns["arrival_status"],
                **{
                    f"fut_{side}_0ms_{horizon}ms": columns[f"fut_{side}_{horizon}"]
                    for horizon in (100, 250, 500, 1000)
                    for side in ("bid", "ask")
                },
            }
        )
        pq.write_table(table, os.path.join(derived, "delay_decisions.parquet"))
        decisions = pa.table(
            {
                "ts_ns": columns["ts_ns"],
                "locate": columns["locate"],
                "mid2_raw": columns["mid2_raw"],
                "spread_raw": columns["spread_raw"],
                "imbalance": columns["imbalance"],
                "best_bid_raw": columns["entry_bid"],
                "best_ask_raw": columns["entry_ask"],
            }
        )
        pq.write_table(decisions, os.path.join(derived, "decisions.parquet"))
        with open(os.path.join(derived, "replay_summary.json"), "w") as handle:
            json.dump({"quality_limits": {"verdict": "DATA_VALID"}, "replay": {}}, handle)
        return derived

    def test_stage_writes_every_declared_artifact_and_blocks_on_nothing(self):
        settings = configuration()
        settings["paths"]["derived_dir"] = os.path.join(_TEST_ROOT, "derived")
        settings["paths"]["output_dir"] = os.path.join(_TEST_ROOT, "output")
        self._derived(settings)
        config_path = os.path.join(_TEST_ROOT, "config.json")
        with open(config_path, "w") as handle:
            json.dump(settings, handle, default=str)
        import yaml

        yaml_path = os.path.join(_TEST_ROOT, "config.yaml")
        with open(yaml_path, "w") as handle:
            yaml.safe_dump(settings, handle)
        status = feasibility.main(["--config", yaml_path])
        self.assertEqual(status, 0)
        calculations = os.path.join(settings["paths"]["output_dir"], "calculations")
        for name, expected_rows in (
            ("aggressive_feasibility_by_state.csv", 400),
            ("breakeven_hurdle.csv", 400),
            ("oracle_upper_bound.csv", 400),
            ("qimb_constrained_bound.csv", 400),
        ):
            path = os.path.join(calculations, name)
            self.assertTrue(os.path.exists(path), name)
            with open(path) as handle:
                self.assertEqual(len(handle.readlines()) - 1, expected_rows, name)
        with open(os.path.join(calculations, "feasibility_status.json")) as handle:
            payload = json.load(handle)
        self.assertEqual(payload["run_status"], "CALCULATION_COMPLETE")
        self.assertEqual(payload["failed_checks"], [])
        self.assertEqual(payload["observation_sets"]["delay_rows_total"], 12)
        self.assertEqual(payload["observation_sets"]["signal_defined"], 11)
        self.assertEqual(payload["cell_dimensions"]["cells_per_horizon"], 100)
        # The synthetic tape spans $1.00-$56.00, so exactly one row falls below the declared
        # $5 band: it must be counted as out of space and kept out of every cell.
        self.assertEqual(payload["observation_sets"]["outside_declared_price_bands"], 1)
        for horizon_ms in ("100", "250", "500", "1000"):
            self.assertEqual(
                payload["observation_sets"]["outside_declared_state_space"][horizon_ms]["signal_defined"], 1
            )
        expectations = {row["check"]: row["outcome"] for row in payload["reconciliation"]}
        self.assertEqual(expectations["execution_instant_is_decision_instant"], "PASS")
        self.assertEqual(expectations["state_partition_covers_every_observation"], "PASS")
        report_path = os.path.join(settings["paths"]["output_dir"], "M2_0_5_FEASIBILITY.md")
        with open(report_path) as handle:
            report = handle.read()
        self.assertIn("ORACLE_UPPER_BOUND", report)
        self.assertIn("QIMB_CONSTRAINED_BOUND", report)
        self.assertIn("## 6. Answers", report)

    def test_blocked_day_produces_no_bound(self):
        settings = configuration()
        settings["paths"]["derived_dir"] = os.path.join(_TEST_ROOT, "derived_blocked")
        settings["paths"]["output_dir"] = os.path.join(_TEST_ROOT, "output_blocked")
        derived = self._derived(settings)
        with open(os.path.join(derived, "replay_summary.json"), "w") as handle:
            json.dump({"quality_limits": {"verdict": "DATA_INVALID"}, "replay": {}}, handle)
        import yaml

        yaml_path = os.path.join(_TEST_ROOT, "config_blocked.yaml")
        with open(yaml_path, "w") as handle:
            yaml.safe_dump(settings, handle)
        status = feasibility.main(["--config", yaml_path])
        self.assertEqual(status, 2)
        with open(os.path.join(settings["paths"]["output_dir"], "calculations", "feasibility_status.json")) as handle:
            payload = json.load(handle)
        self.assertEqual(payload["run_status"], "CALCULATION_BLOCKED")


if __name__ == "__main__":
    unittest.main()
