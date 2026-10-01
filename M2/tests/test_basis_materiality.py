"""Deterministic tests for the frozen branch-C funding-basis measurement (C5).

Two subjects, both load-bearing:

* the additive ``envelope.perp_price_pnl`` helper and the hedged-pair identity it is used
  for (a sign error there flips the whole verdict);
* the frozen hold construction and gross identity of :mod:`M2.src.basis_materiality` —
  causal row alignment (entry on row J-1, exit on row J, carry on row J+1), the measured
  zero when no settlement instant lies inside a hold, the never-zero handling of an
  unobserved settlement rate, the boundary-staleness tolerance, the C0/C1 split and the
  coverage floor.

No economics are asserted here beyond hand-computed arithmetic on synthetic panels; the
one real-data test checks the admitted panel's structure against its raw payloads and
reads no outcome.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from M2.src import envelope as env
from M2.src import basis_materiality as bm

ROOT = Path(__file__).resolve().parents[2]
H0 = 1772668800  # 2026-03-05T00:00:00Z, on the 8h settlement grid


def rows(panel_rows):
    return tuple(r for r in panel_rows)


def make_row(hour, hl_mid, bin_close, hl_funding_rate=0.0, funding_offset_ms=0):
    return bm.PanelRow(
        hour_unix=hour,
        hl_funding_rate=hl_funding_rate,
        hl_mid=hl_mid,
        binance_kline_close=bin_close,
        binance_mark_close=bin_close + 0.5,
        hl_funding_time_ms=hour * 1000 + funding_offset_ms,
    )


def make_panel(panel_rows):
    panel_rows = tuple(panel_rows)
    return bm.Panel(
        rows=panel_rows,
        window_start_unix=panel_rows[0].hour_unix,
        window_end_unix=panel_rows[-1].hour_unix,
        path="synthetic",
        sha256="synthetic",
    )


def ramp_panel(hours: int, funding_offset_ms: int = 0):
    """Hourly HL/Binance closes that move +1% then +0.99% per hour, so a wrong row
    alignment cannot coincidentally produce the right return."""
    out = []
    for k in range(hours):
        step = 1.01 if k <= 1 else 1.0099
        out.append(
            make_row(
                H0 + k * 3600,
                hl_mid=100.0 * step ** k,
                bin_close=200.0 * step ** k,
                hl_funding_rate=0.0001 if k == 2 else 0.0,
                funding_offset_ms=funding_offset_ms,
            )
        )
    return out


class PerpPricePnlTests(unittest.TestCase):
    def test_signed_and_scaled_by_notional(self):
        self.assertAlmostEqual(
            env.perp_price_pnl(entry_price=100.0, exit_price=101.0, position="long",
                               notional_usd=1000.0),
            10.0,
        )
        self.assertAlmostEqual(
            env.perp_price_pnl(entry_price=100.0, exit_price=101.0, position="short",
                               notional_usd=1000.0),
            -10.0,
        )

    def test_refuses_unknown_price_and_bad_position(self):
        with self.assertRaises(env.MissingUnitInput):
            env.perp_price_pnl(entry_price=None, exit_price=101.0, position="long",
                               notional_usd=1.0)
        with self.assertRaises(env.MissingUnitInput):
            env.perp_price_pnl(entry_price=100.0, exit_price=101.0, position="long",
                               notional_usd=None)
        with self.assertRaises(ValueError):
            env.perp_price_pnl(entry_price=0.0, exit_price=101.0, position="long",
                               notional_usd=1.0)
        with self.assertRaises(ValueError):
            env.perp_price_pnl(entry_price=100.0, exit_price=101.0, position="sideways",
                               notional_usd=1.0)

    def test_equal_notional_pair_residual_is_long_return_minus_short_return(self):
        notional = 1.0
        residual = env.perp_price_pnl(entry_price=100.0, exit_price=103.0, position="short",
                                      notional_usd=notional) + env.perp_price_pnl(
            entry_price=200.0, exit_price=210.0, position="long", notional_usd=notional
        )
        expected = notional * ((210.0 / 200.0 - 1.0) - (103.0 / 100.0 - 1.0))
        self.assertAlmostEqual(residual, expected)


class HoldConstructionTests(unittest.TestCase):
    def test_hold_uses_the_previous_row_as_entry_and_the_next_row_as_carry(self):
        panel = make_panel(ramp_panel(4))
        holds = bm.build_holds(panel)
        self.assertEqual([h.decision_hour_unix for h in holds], [H0 + 3600, H0 + 7200])
        first = holds[0]
        self.assertEqual(first.entry_row_unix, H0)
        self.assertEqual(first.exit_row_unix, H0 + 3600)
        self.assertEqual(first.carry_row_unix, H0 + 7200)

        terms = bm.hold_terms(first, panel.by_hour(), {})
        # entry price must be row H0's close (100.0), not row J's (which would give 1.0099)
        self.assertAlmostEqual(terms["hl_return"], 101.0 / 100.0 - 1.0)
        self.assertAlmostEqual(terms["binance_return"], 202.0 / 200.0 - 1.0)

    def test_gross_is_carry_plus_hedge_residual(self):
        panel = make_panel(ramp_panel(4))
        holds = bm.build_holds(panel)
        terms = bm.hold_terms(holds[0], panel.by_hour(), {})
        # HL print of row J+1 = H0+2h is +0.0001, paid to the short: +1 bps.
        self.assertAlmostEqual(terms["hl_carry_bps"], 1.0)
        self.assertAlmostEqual(terms["hedge_residual_bps"], 0.0)
        self.assertAlmostEqual(terms["gross_bps"], 1.0)
        self.assertEqual(terms["binance_settlement_status"], "NO_SETTLEMENT_INSIDE_HOLD")
        self.assertFalse(terms["unresolved"])

    def test_both_carry_signs_flip_with_the_position(self):
        panel = make_panel(ramp_panel(18))
        settle = {H0 + 8 * 3600: {"rate": 0.0002}}
        by_hour = panel.by_hour()
        settled = [
            bm.hold_terms(h, by_hour, settle)
            for h in bm.build_holds(panel)
            if h.carry_row_unix == H0 + 8 * 3600
        ]
        self.assertEqual(len(settled), 1)
        # a positive Binance rate is paid BY the long leg: -2 bps.
        self.assertAlmostEqual(settled[0]["binance_carry_bps"], -2.0)
        self.assertEqual(settled[0]["binance_settlement_status"], "SETTLEMENT_OBSERVED")

    def test_an_archived_gap_is_unresolved_and_never_a_zero(self):
        panel = make_panel(ramp_panel(18))
        by_hour = panel.by_hour()
        settle = {H0 + 8 * 3600: {"rate": 0.0002}}
        terms = [bm.hold_terms(h, by_hour, settle) for h in bm.build_holds(panel)]
        agg = bm.aggregate(terms)
        self.assertEqual(agg["holds_with_unresolved_settlement"], 1)
        self.assertEqual(agg["holds_with_observed_settlement"], 1)
        self.assertEqual(agg["holds_without_settlement"], len(terms) - 2)

        bracket = bm.unresolved_bracket(agg)
        weight = 1 / len(terms)
        self.assertAlmostEqual(bracket["weight"], weight)
        self.assertAlmostEqual(bracket["contribution_bps_midpoint"], -0.0002 * weight * 1e4)
        self.assertNotAlmostEqual(bracket["contribution_bps_midpoint"], 0.0)
        # with both settlements archived the bracket is empty and the raw carry is complete
        terms_full = [bm.hold_terms(h, by_hour, {**settle, H0 + 16 * 3600: {"rate": 0.0003}})
                      for h in bm.build_holds(panel)]
        self.assertEqual(bm.aggregate(terms_full)["holds_with_unresolved_settlement"], 0)
        self.assertEqual(bm.unresolved_bracket(bm.aggregate(terms_full))["status"],
                         "NO_UNRESOLVED_HOLD")

    def test_hold_set_is_contiguous_and_skips_only_the_two_boundary_hours(self):
        panel = make_panel(ramp_panel(25))
        holds = bm.build_holds(panel)
        hours = [h.decision_hour_unix for h in holds]
        self.assertEqual(hours, list(range(H0 + 3600, H0 + 24 * 3600, 3600)))
        self.assertNotIn(panel.window_start_unix, hours)
        self.assertNotIn(panel.window_end_unix, hours)

    def test_a_hold_outside_the_panel_is_a_coverage_floor_error(self):
        panel = make_panel(ramp_panel(4))
        stray = bm.Hold(decision_hour_unix=H0 + 10 * 3600, entry_row_unix=H0 + 9 * 3600,
                        exit_row_unix=H0 + 10 * 3600, carry_row_unix=H0 + 11 * 3600)
        with self.assertRaises(bm.CoverageFloorError):
            bm.assert_hold_inputs(panel, [stray])

    def test_a_missing_interior_hour_fails_the_grid_identity(self):
        panel = make_panel(ramp_panel(4))
        holed = make_panel([r for r in panel.rows if r.hour_unix != H0 + 3600])
        report = bm.verify_panel(holed, {"session": {"window_start_unix": H0,
                                                     "window_end_unix": H0 + 3 * 3600}})
        self.assertFalse(report["grid_identity"])
        self.assertEqual(report["missing_buckets"], 1)
        self.assertFalse(report["pass"])


class StalenessTests(unittest.TestCase):
    def test_tolerance_is_compared_against_the_declared_bound(self):
        fresh = make_panel(ramp_panel(4, funding_offset_ms=100))
        report = bm.staleness_report(fresh, bm.build_holds(fresh))
        self.assertEqual(report["tolerance_seconds"], 1.0)
        self.assertEqual(report["fraction_stale_beyond_tolerance"], 0.0)
        self.assertAlmostEqual(report["entry"]["hyperliquid_reference"]["max_s"], 0.1)

        stale = make_panel(ramp_panel(4, funding_offset_ms=5000))
        report = bm.staleness_report(stale, bm.build_holds(stale))
        self.assertEqual(report["fraction_stale_beyond_tolerance"], 1.0)
        self.assertEqual(report["entry"]["hyperliquid_reference"]["exceeding_tolerance_count"], 2)
        self.assertEqual(report["exit"]["binance_reference"]["exceeding_tolerance_count"], 2)


class CostSplitTests(unittest.TestCase):
    def test_c0_is_the_lowest_published_rung_only(self):
        envelope = bm.cost_envelope()
        c0 = envelope.c0_items()
        self.assertEqual([item.id for item in c0], ["hl_perp_taker_lowest_published_rung"])
        env.assert_c0(c0[0])
        self.assertEqual(c0[0].cost_class(), env.CLASS_C0)
        basis = env.Basis(notional_usd=1.0)
        self.assertAlmostEqual(envelope.structural_c0_usd(basis), 0.00048)
        self.assertAlmostEqual(env.usd_to_bps(envelope.structural_c0_usd(basis), 1.0), 4.8)

    def test_state_dependent_and_unknown_charges_stay_in_c1(self):
        envelope = bm.cost_envelope()
        c1_ids = [item.id for item in envelope.c1_items()]
        self.assertIn("hl_perp_taker_state_dependent_uplift", c1_ids)
        self.assertIn("binance_usdm_taker_fee", c1_ids)
        report = bm.cost_report(envelope)
        self.assertEqual(report["c0_bps"], 4.8)
        self.assertIn("binance_usdm_taker_fee", report["c1_unknown_item_ids"])
        self.assertIsNone(report["c1_total_usd"])
        self.assertFalse(report["c1_bounded"])
        base = report["base_tier_scenario"]["hyperliquid"]
        self.assertEqual(base["class"], env.CLASS_C1)
        self.assertAlmostEqual(base["usd"], 0.0009)
        self.assertFalse(report["base_tier_scenario"]["may_decide_the_kill"])

    def test_decision_interval_is_widened_by_the_unresolved_bracket(self):
        panel = make_panel(ramp_panel(34))
        settled = {H0 + 8 * 3600: {"rate": 0.0002}, H0 + 24 * 3600: {"rate": -0.0001}}
        terms = [bm.hold_terms(h, panel.by_hour(), settled) for h in bm.build_holds(panel)]
        agg = bm.aggregate(terms)
        self.assertEqual(agg["holds_with_observed_settlement"], 2)
        self.assertEqual(agg["holds_with_unresolved_settlement"], 2)
        bracket = bm.unresolved_bracket(agg)
        self.assertGreater(bracket["bracket_width_bps"], 0.0)
        self.assertLess(bracket["contribution_bps_at_max_rate"],
                        bracket["contribution_bps_at_min_rate"])
        sampling = {"lo": -1.0, "hi": 1.0}
        lo = sampling["lo"] + bracket["contribution_bps_at_max_rate"]
        hi = sampling["hi"] + bracket["contribution_bps_at_min_rate"]
        self.assertLess(lo, sampling["lo"])
        self.assertGreater(hi, sampling["hi"])


class BootstrapTests(unittest.TestCase):
    def test_same_seed_same_interval_different_seed_moves_it(self):
        series = [((i * 7919) % 101 - 50) / 10.0 for i in range(200)]
        first = bm.interval(bm.bootstrap_means(series, resamples=500, seed=bm.BOOTSTRAP_SEED))
        again = bm.interval(bm.bootstrap_means(series, resamples=500, seed=bm.BOOTSTRAP_SEED))
        other = bm.interval(bm.bootstrap_means(series, resamples=500, seed=bm.BOOTSTRAP_SEED + 1))
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        self.assertLess(first["lo"], first["hi"])


class AdmittedPanelTests(unittest.TestCase):
    """The admitted panel is verified against its own raw payloads; no outcome is read."""

    def test_panel_matches_its_declared_window_hashes_and_raw_archives(self):
        panel = bm.load_panel(ROOT / "M2/data/derived_basis/paired_hours.csv")
        manifest = bm.load_json(ROOT / "M2/data/derived_basis/manifest_basis.json")
        self.assertTrue(bm.verify_panel(panel, manifest)["pass"])
        self.assertTrue(bm.verify_manifest_files(ROOT, manifest)["all_match"])
        rederived = bm.rederive_reference_prices(panel, ROOT / "M2/data/raw/basis")
        self.assertTrue(rederived["hyperliquid"]["match"])
        self.assertTrue(rederived["binance_kline"]["match"])
        self.assertEqual(rederived["binance_kline"]["checked"], len(panel.rows))

        archive = bm.load_binance_settlements(ROOT / "M2/data/raw/basis")
        self.assertEqual(archive["cadence_hours"], 8)
        self.assertEqual(len(archive["by_hour"]), archive["count"])
        self.assertTrue(all(h % (8 * 3600) == 0 for h in archive["by_hour"]))

        holds = bm.build_holds(panel)
        self.assertEqual(len(holds), 4979)
        bm.assert_hold_inputs(panel, holds)


if __name__ == "__main__":
    unittest.main()
