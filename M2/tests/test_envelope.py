"""Deterministic tests for the W5 economic-envelope arithmetic.

The subject is arithmetic and its refusals: units, the C0/C1 split, C*, observed-spread
friction, executable auction capture, two-leg funding, and the preregistered
uncertainty-vs-C0 classification. No outcomes, no strategy logic, no distributions.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from M2.src import costs
from M2.src import envelope as env

_LEDGER_PATH = Path(__file__).resolve().parents[2] / "M2" / "config" / "cost_ledger_v1.json"


def verified() -> env.Provenance:
    return env.Provenance(
        source_id="SRC-TEST",
        url="https://example.invalid/verified",
        publisher="test",
        access_date="2026-09-29",
        effective_period="2026 rate card",
        quote="quoted",
        status=env.STATUS_VERIFIED,
    )


class UnitArithmeticTests(unittest.TestCase):
    def test_per_share_to_usd_and_bps(self):
        basis = env.Basis(quantity=100, price_usd=25.0)
        self.assertAlmostEqual(env.to_usd(0.003, env.UNIT_USD_PER_SHARE, basis), 0.3)
        self.assertAlmostEqual(env.usd_to_bps(0.3, 2500.0), 1.2)
        self.assertAlmostEqual(env.convert(0.003, env.UNIT_USD_PER_SHARE, env.UNIT_BPS, basis), 1.2)

    def test_per_share_to_bps_needs_only_price(self):
        self.assertAlmostEqual(
            env.convert(0.005, env.UNIT_USD_PER_SHARE, env.UNIT_BPS, env.Basis(price_usd=10.0)), 5.0
        )
        with self.assertRaises(env.MissingUnitInput):
            env.convert(0.005, env.UNIT_USD_PER_SHARE, env.UNIT_BPS, env.Basis(quantity=100))

    def test_ratio_units_convert_among_themselves(self):
        self.assertAlmostEqual(
            env.convert(20.6, env.UNIT_PER_MILLION_OF_SALES, env.UNIT_BPS), 0.206
        )
        self.assertAlmostEqual(env.convert(25.0, env.UNIT_BPS, env.UNIT_PCT_OF_TRADE_VALUE), 0.25)
        self.assertAlmostEqual(env.convert(0.0001, env.UNIT_FUNDING_RATE, env.UNIT_BPS), 1.0)

    def test_ticks_need_tick_value(self):
        basis = env.Basis(quantity=3, tick_value_usd=12.5)
        self.assertAlmostEqual(env.to_usd(2, env.UNIT_TICKS, basis), 75.0)
        with self.assertRaises(env.MissingUnitInput):
            env.to_usd(2, env.UNIT_TICKS, env.Basis(quantity=3))

    def test_contract_multiplier_sets_notional(self):
        basis = env.Basis(quantity=2, price_usd=5000.0, multiplier=50.0)
        self.assertAlmostEqual(basis.notional(), 500000.0)
        # 10 USD per contract on 2 contracts = 20 USD against 500,000 USD notional = 0.4 bps.
        self.assertAlmostEqual(env.convert(10.0, env.UNIT_USD_PER_CONTRACT, env.UNIT_BPS, basis), 0.4)

    def test_refuses_conversion_with_unknown_multiplier(self):
        # No multiplier -> notional is unknown -> bps conversion must refuse.
        with self.assertRaises(env.MissingUnitInput):
            env.convert(
                10.0, env.UNIT_USD_PER_CONTRACT, env.UNIT_BPS, env.Basis(quantity=2, price_usd=5000.0)
            )

    def test_unknown_value_is_never_zero(self):
        with self.assertRaises(env.MissingUnitInput):
            env.to_usd(None, env.UNIT_USD)
        with self.assertRaises(env.MissingUnitInput):
            env.convert(None, env.UNIT_USD_PER_SHARE, env.UNIT_USD, env.Basis(quantity=1))

    def test_unsupported_conversion_pair_refused(self):
        with self.assertRaises(env.UnsupportedUnitConversion):
            env.convert(1.0, "WIDGETS", env.UNIT_USD, env.Basis(quantity=1))
        with self.assertRaises(env.UnsupportedUnitConversion):
            env.to_usd(1.0, "WIDGETS")
        with self.assertRaises(env.UnsupportedUnitConversion):
            env.from_usd(1.0, "WIDGETS", env.Basis(quantity=1))
        # A funding rate to ticks is defined through USD, so it refuses on the missing
        # notional rather than pretending a value.
        with self.assertRaises(env.MissingUnitInput):
            env.convert(0.0001, env.UNIT_FUNDING_RATE, env.UNIT_TICKS)

    def test_multiplier_of_commission_needs_commission(self):
        self.assertAlmostEqual(
            env.to_usd(0.000565, env.UNIT_MULTIPLIER_OF_COMMISSION, env.Basis(commission_usd=1.0)),
            0.000565,
        )
        with self.assertRaises(env.MissingUnitInput):
            env.to_usd(0.000565, env.UNIT_MULTIPLIER_OF_COMMISSION, env.Basis())


class CostClassTests(unittest.TestCase):
    def test_verified_non_variable_item_is_c0(self):
        item = env.CostItem(
            id="nasdaq_remove", name="remove fee", unit=env.UNIT_USD_PER_SHARE,
            value=0.003, provenance=verified(),
        )
        self.assertEqual(item.cost_class(), env.CLASS_C0)
        self.assertIs(env.assert_c0(item), item)

    def test_variable_tier_fee_cannot_be_c0_through_standard_api(self):
        tier = env.CostItem(
            id="hl_taker", name="Hyperliquid taker fee (volume/staking tier)",
            unit=env.UNIT_BPS, value=1.5, provenance=verified(),
            varies_with_volume=True, varies_with_staking=True,
        )
        self.assertEqual(tier.cost_class(), env.CLASS_C1)
        with self.assertRaises(env.CostClassificationError):
            env.assert_c0(tier)
        scenario = env.reference_path_scenario(tier, env.Basis(notional_usd=1000.0))
        self.assertEqual(scenario["class"], env.CLASS_C1)
        self.assertEqual(scenario["scenario_role"], "REFERENCE_EXECUTION_PATH")
        self.assertAlmostEqual(scenario["usd"], 0.15)

    def test_variable_tier_can_be_justified_unavoidable(self):
        tier = env.CostItem(
            id="mandatory_venue_fee", name="venue fee", unit=env.UNIT_BPS, value=2.0,
            provenance=verified(), varies_with_account_state=True,
            unavoidable_on_frozen_path=True, justified_unavoidable="frozen path is fixed to this tier",
        )
        self.assertEqual(tier.cost_class(), env.CLASS_C0)

    def test_unverified_or_unknown_stays_c1(self):
        unverified = env.CostItem(
            id="broker_pass_through", name="pass-through", unit=env.UNIT_USD_PER_SHARE,
            value=0.0002, provenance=env.Provenance(source_id="x", url="", access_date=""),
        )
        self.assertEqual(unverified.cost_class(), env.CLASS_C1)
        unknown = env.CostItem(id="cme_fee", name="CME fee", unit="UNKNOWN", value=None,
                               provenance=verified())
        self.assertEqual(unknown.cost_class(), env.CLASS_C1)


class EnvelopeTests(unittest.TestCase):
    def _envelope(self) -> env.Envelope:
        return env.Envelope(
            envelope_id="test",
            items=(
                env.CostItem(id="remove", name="remove", unit=env.UNIT_USD_PER_SHARE, value=0.003,
                             provenance=verified()),
                env.CostItem(id="sec31", name="sec31", unit=env.UNIT_PER_MILLION_OF_SALES,
                             value=20.6, side="sell", provenance=verified()),
                env.CostItem(id="cme", name="cme 403", unit="UNKNOWN", value=None,
                             provenance=env.Provenance(status=env.STATUS_UNKNOWN)),
            ),
        )

    def test_c0_split_and_total(self):
        envelope = self._envelope()
        basis = env.Basis(quantity=100, price_usd=50.0)
        self.assertEqual([i.id for i in envelope.c0_items()], ["remove", "sec31"])
        # 0.003*100 shares = 0.30; 20.6 per million on 5000 USD = 0.103
        self.assertAlmostEqual(envelope.structural_c0_usd(basis), 0.403)

    def test_unknown_c1_total_is_none_not_zero(self):
        envelope = self._envelope()
        self.assertIsNone(envelope.unresolved_c1_total_usd(env.Basis(quantity=100, price_usd=50.0)))
        known = envelope.unresolved_c1_known_usd(env.Basis(quantity=100, price_usd=50.0))
        self.assertEqual(known["unknown_item_ids"], ["cme"])
        self.assertEqual(known["unevaluated_item_ids"], [])
        self.assertFalse(known["bounded"])
        self.assertAlmostEqual(known["known_usd"], 0.0)

    def test_envelope_from_existing_ledger(self):
        ledger = {
            "ledger_id": "TEST-LEDGER",
            "regimes": ["STRUCTURAL_COST_FLOOR"],
            "line_items": [
                {"id": "a", "name": "primary", "unit": env.UNIT_USD_PER_SHARE, "value": 0.003,
                 "sides": "both", "regimes": ["STRUCTURAL_COST_FLOOR"],
                 "cross_check_status": "PRIMARY_VERIFIED",
                 "source": {"url": "u", "publisher": "p", "access_date": "2026-09-29", "quote": "q"}},
                {"id": "b", "name": "broker only", "unit": env.UNIT_USD_PER_SHARE, "value": 0.0002,
                 "sides": "both", "regimes": ["STRUCTURAL_COST_FLOOR"],
                 "cross_check_status": "BROKER_PAGE_ONLY",
                 "source": {"url": "u", "publisher": "p", "access_date": "2026-09-29", "quote": "q"}},
            ],
        }
        envelope = env.envelope_from_ledger(ledger, "STRUCTURAL_COST_FLOOR")
        self.assertEqual([i.id for i in envelope.c0_items()], ["a"])
        self.assertEqual([i.id for i in envelope.c1_items()], ["b"])


class ResidualAndSensitivityTests(unittest.TestCase):
    def test_c_star_zero_crossing(self):
        self.assertAlmostEqual(env.break_even_residual(1.0, 0.4), 0.6)
        self.assertAlmostEqual(env.break_even_residual(0.4, 0.4), 0.0)
        self.assertAlmostEqual(env.break_even_residual(0.1, 0.4), -0.3)

    def test_c1_sensitivity_has_no_distribution(self):
        out = env.c1_sensitivity(1.0, 0.4, [0.0, 0.3, 0.6, 0.9])
        self.assertEqual(out["distribution_assumption"], "NONE")
        self.assertAlmostEqual(out["c1_breakeven_usd"], 0.6)
        rows = {row["c1_usd"]: row for row in out["rows"]}
        self.assertAlmostEqual(rows[0.3]["c_star_usd"], 0.3)
        self.assertTrue(rows[0.3]["survives_floor"])
        self.assertFalse(rows[0.9]["survives_floor"])

    def test_midpoint_friction_uses_observed_spreads(self):
        self.assertAlmostEqual(env.midpoint_markout_friction(0.02, 0.04), 0.03)
        self.assertAlmostEqual(env.midpoint_markout_friction_bps(0.02, 0.04, 10.0), 30.0)
        with self.assertRaises(env.MissingUnitInput):
            env.midpoint_markout_friction(None, 0.04)
        with self.assertRaises(ValueError):
            env.midpoint_markout_friction(-0.01, 0.04)

    def test_significance_is_reported_but_not_a_decision_input(self):
        reported = env.significance_against_zero(0.5, 0.1)
        self.assertAlmostEqual(reported["t_stat"], 5.0)
        self.assertEqual(reported["role"], "REPORTED_ONLY")
        # The classification cannot consult it: its signature has no significance argument.
        verdict = env.classify_materiality(1.0, 0.9, 1.1, 0.5)
        self.assertFalse(verdict["significance_is_decision_criterion"])


class AuctionCaptureTests(unittest.TestCase):
    def test_positive_signal_embeds_entry_spread_at_ask(self):
        out = env.auction_executable_gross(
            env.SIGNAL_POSITIVE, best_bid=10.00, best_ask=10.02,
            closing_cross_price=10.10, reference_price=10.00,
        )
        self.assertAlmostEqual(out["entry_price"], 10.02)
        self.assertAlmostEqual(out["gross_usd_per_share"], 0.08)
        self.assertAlmostEqual(out["entry_spread_usd"], 0.02)
        self.assertAlmostEqual(out["entry_slippage_vs_mid_usd"], 0.01)
        self.assertTrue(out["entry_spread_embedded"])
        self.assertAlmostEqual(out["gross_bps"], 80.0)

    def test_negative_signal_enters_at_bid_and_covers_at_close(self):
        out = env.auction_executable_gross(
            env.SIGNAL_NEGATIVE, best_bid=10.00, best_ask=10.02,
            closing_cross_price=9.90, reference_price=10.00,
        )
        self.assertAlmostEqual(out["entry_price"], 10.00)
        self.assertAlmostEqual(out["gross_usd_per_share"], 0.10)
        self.assertAlmostEqual(out["gross_bps"], 100.0)

    def test_ineligible_codes_refused(self):
        for code in env.INELIGIBLE_NOII_CODES + ("B*",):
            with self.assertRaises(ValueError):
                env.auction_executable_gross(
                    code, best_bid=1.0, best_ask=1.01, closing_cross_price=1.0
                )

    def test_bps_refused_without_reference_price(self):
        out = env.auction_executable_gross(
            env.SIGNAL_POSITIVE, best_bid=10.00, best_ask=10.02, closing_cross_price=10.10
        )
        self.assertIsNone(out["gross_bps"])
        self.assertTrue(out["bps_requires_reference_price"])

    def test_auction_residual_uses_c0(self):
        gross = env.auction_executable_gross(
            env.SIGNAL_POSITIVE, best_bid=10.0, best_ask=10.02, closing_cross_price=10.10
        )["gross_usd_per_share"]
        self.assertAlmostEqual(env.break_even_residual(gross, 0.0031), 0.0769)


class MultiLegTests(unittest.TestCase):
    def test_funding_direction_sign(self):
        # Positive funding: shorts receive, longs pay.
        self.assertAlmostEqual(env.funding_cashflow(0.0001, 100000.0, "short"), 10.0)
        self.assertAlmostEqual(env.funding_cashflow(0.0001, 100000.0, "long"), -10.0)
        self.assertAlmostEqual(env.funding_cashflow(-0.0001, 100000.0, "short"), -10.0)
        with self.assertRaises(ValueError):
            env.funding_cashflow(0.0001, 100000.0, "flat")
        with self.assertRaises(env.MissingUnitInput):
            env.funding_cashflow(None, 100000.0, "short")

    def test_per_side_vs_round_trip(self):
        leg = env.perp_leg(
            notional_usd=100000.0, position="short", fee_entry_bps=1.0, fee_exit_bps=2.0,
            funding_rate=0.00005, funding_intervals=1,
        )
        self.assertAlmostEqual(leg["fee_entry_usd"], 10.0)
        self.assertAlmostEqual(leg["fee_exit_usd"], 20.0)
        self.assertAlmostEqual(leg["fees_round_trip_usd"], 30.0)
        self.assertAlmostEqual(leg["fees_per_side_usd"], 15.0)
        self.assertAlmostEqual(leg["funding_usd"], 5.0)
        self.assertAlmostEqual(leg["net_usd"], -25.0)

    def test_two_leg_pair_aggregation(self):
        short_leg = env.perp_leg(
            notional_usd=100000.0, position="short", fee_entry_bps=1.5, fee_exit_bps=1.5,
            funding_rate=0.0001,
        )
        long_leg = env.perp_leg(
            notional_usd=100000.0, position="long", fee_entry_bps=2.0, fee_exit_bps=2.0,
            funding_rate=0.00004,
        )
        paired = env.two_leg_net([short_leg, long_leg])
        self.assertEqual(paired["leg_count"], 2)
        self.assertAlmostEqual(paired["fees_round_trip_usd"], 30.0 + 40.0)
        self.assertAlmostEqual(paired["funding_usd"], 10.0 - 4.0)
        self.assertAlmostEqual(paired["net_usd"], 6.0 - 70.0)

    def test_round_trip_helper(self):
        out = env.round_trip_usd(3.0, 7.0)
        self.assertAlmostEqual(out["round_trip_usd"], 10.0)
        self.assertAlmostEqual(out["per_side_usd"], 5.0)


class ClassificationTests(unittest.TestCase):
    def test_kill_when_gross_non_positive(self):
        for gross in (0.0, -1.0):
            out = env.classify_materiality(gross, -2.0, 2.0, 0.5)
            self.assertEqual(out["verdict"], env.VERDICT_KILL)

    def test_kill_when_uncertainty_wholly_below_hurdle(self):
        self.assertEqual(env.classify_materiality(1.0, 0.2, 0.5, 0.5)["verdict"], env.VERDICT_KILL)
        # boundary: hi == C0 is still KILL
        self.assertEqual(env.classify_materiality(1.0, 0.2, 0.5, 0.5)["verdict"], env.VERDICT_KILL)
        self.assertEqual(env.classify_materiality(1.0, 0.1, 0.5, 0.5)["verdict"], env.VERDICT_KILL)

    def test_survive_when_uncertainty_wholly_above_hurdle(self):
        self.assertEqual(env.classify_materiality(1.0, 0.6, 1.4, 0.5)["verdict"], env.VERDICT_SURVIVE)
        # boundary: lo == C0 is NOT survive
        self.assertEqual(
            env.classify_materiality(1.0, 0.5, 1.4, 0.5)["verdict"], env.VERDICT_INDETERMINATE
        )

    def test_indeterminate_when_interval_straddles_hurdle(self):
        self.assertEqual(
            env.classify_materiality(1.0, 0.3, 1.4, 0.5)["verdict"], env.VERDICT_INDETERMINATE
        )

    def test_kill_takes_precedence_over_survive(self):
        # lo > C0 but g <= 0: the rules must apply KILL first.
        out = env.classify_materiality(-0.1, -0.5, 0.9, -1.0)
        self.assertEqual(out["verdict"], env.VERDICT_KILL)

    def test_reports_c_star(self):
        out = env.classify_materiality(1.0, 0.6, 1.4, 0.5)
        self.assertAlmostEqual(out["c_star_usd"], 0.5)


class RealLedgerIntegrationTests(unittest.TestCase):
    """The envelope must consume the existing ledger read-only and classify it as declared."""

    def _ledger(self) -> dict:
        return costs.load_ledger(str(_LEDGER_PATH))

    def test_structural_floor_c0_set_matches_the_declared_regime(self):
        envelope = env.envelope_from_ledger(self._ledger(), "STRUCTURAL_COST_FLOOR")
        self.assertEqual(
            sorted(item.id for item in envelope.c0_items()),
            ["finra_trading_activity_fee", "nasdaq_remove_liquidity_fee", "sec_section_31_fee"],
        )
        for item in envelope.c0_items():
            self.assertTrue(item.provenance.verified(), item.id)

    def test_operating_economics_unknowns_never_reach_c0(self):
        envelope = env.envelope_from_ledger(self._ledger(), "STRUCTURAL_COST_FLOOR")
        c1_ids = [item.id for item in envelope.c1_items()]
        self.assertIn("databento_xnas_mbo_data_cost", c1_ids)
        self.assertIn("nasdaq_historical_itch_license_cost", c1_ids)
        self.assertIsNone(envelope.unresolved_c1_total_usd(env.Basis(quantity=100, price_usd=25.0)))

    def test_broker_pass_through_is_unevaluated_not_zero(self):
        envelope = env.envelope_from_ledger(self._ledger(), "ACCESSIBLE_REFERENCE_PATH")
        basis = env.Basis(quantity=100, price_usd=25.0)
        known = envelope.unresolved_c1_known_usd(basis)
        self.assertIn("nyse_pass_through_fee", known["unevaluated_item_ids"])
        self.assertIn("finra_pass_through_fee", known["unevaluated_item_ids"])
        self.assertFalse(known["bounded"])
        self.assertAlmostEqual(known["known_usd"], 0.0002 * 100 + 3e-06 * 100)


if __name__ == "__main__":
    unittest.main()