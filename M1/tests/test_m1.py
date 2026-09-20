"""Unit tests for the M1 computation layer and the artifact invariants.

Run:  python3 -m unittest discover -s M1/tests -t .     (from the repository root)

The tests assert the properties the handoff actually depends on: no missing value becomes a
number, gate states cannot promote a candidate, cost floors are not break-evens, latency fits
are refused without a measured curve, and the shipped artifacts still validate.
"""

from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "M1" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import candidate_gates  # noqa: E402
import costs  # noqa: E402
import coverage  # noqa: E402
import envelopes  # noqa: E402
import latency  # noqa: E402
import paper_arithmetic  # noqa: E402
import pareto  # noqa: E402
import validate  # noqa: E402
from corpus import constants, evidence, feasibility, sources, tuples, unknowns, venues  # noqa: E402


class FeeArithmetic(unittest.TestCase):
    def test_native_units_convert_only_when_the_unit_is_defined(self):
        self.assertEqual(costs.bps_from_native(0.80, "PERCENT"), 80.0)
        self.assertEqual(costs.bps_from_native(60, "BPS"), 60.0)

    def test_per_share_fee_has_no_bps_without_a_price(self):
        self.assertIsNone(costs.bps_from_native(0.0030, "USD_PER_SHARE"))
        self.assertAlmostEqual(costs.bps_from_native(0.0030, "USD_PER_SHARE", price=50.0), 0.6)

    def test_unknown_inputs_propagate_rather_than_defaulting(self):
        self.assertIsNone(costs.bps_from_native(None, "BPS"))
        self.assertIsNone(costs.round_trip(60.0, None))

    def test_round_trip_matrix_uses_only_verified_legs(self):
        rt = costs.round_trip_costs(40.0, 60.0)
        self.assertEqual(rt["round_trip_maker_maker_fee_bps"], 80.0)
        self.assertEqual(rt["round_trip_maker_taker_fee_bps"], 100.0)
        self.assertEqual(rt["round_trip_taker_taker_fee_bps"], 120.0)

    def test_mixed_style_has_no_single_required_round_trip(self):
        self.assertIsNone(costs.required_round_trip_fee_bps("MIXED", 40.0, 60.0))
        self.assertEqual(costs.required_round_trip_fee_bps("AGGRESSIVE", 40.0, 60.0), 120.0)
        self.assertEqual(costs.required_round_trip_fee_bps("PASSIVE", 40.0, 60.0), 80.0)

    def test_cost_floor_excludes_unknowns_and_names_them(self):
        floor = costs.known_cost_floor({"exchange_fee": 60.0, "clearing": None, "commission": None})
        self.assertEqual(floor["floor_value"], 60.0)
        self.assertEqual(floor["missing_components"], ["clearing", "commission"])

    def test_floor_with_no_verified_component_is_unknown_not_zero(self):
        floor = costs.known_cost_floor({"exchange_fee": None})
        self.assertIsNone(floor["floor_value"])

    def test_full_break_even_refuses_partial_inputs(self):
        be = costs.full_break_even({"spread": 1.0, "fees": 120.0, "slippage": None,
                                    "adverse_selection": None, "impact": None})
        self.assertIsNone(be["break_even_bps"])
        self.assertEqual(be["status"], "BLOCKED_UNKNOWN_COMPONENTS")
        full = costs.full_break_even({"spread": 1.0, "fees": 2.0, "slippage": 3.0,
                                      "adverse_selection": 4.0, "impact": 5.0})
        self.assertEqual(full["break_even_bps"], 15.0)

    def test_net_return_bound_is_not_a_realized_result(self):
        self.assertEqual(costs.net_return_bounds(200.0, 120.0), 80.0)
        self.assertIsNone(costs.net_return_bounds(None, 120.0))

    def test_passive_utility_requires_fill_probability_and_markout(self):
        blocked = costs.passive_utility_blocked(None, 2.0)
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["missing"], ["P(fill|queue,state)"])
        computed = costs.passive_utility_blocked(0.25, 2.0)
        self.assertEqual(computed["expected_passive_utility_bps"], 0.5)


class GateCeiling(unittest.TestCase):
    def _cand(self, **gates):
        cand = {g: "PASS" for g in constants.GATE_IDS}
        cand.update(gates)
        cand["overall_status"] = "UNKNOWN"
        cand["candidate_id"] = "TUP-TEST"
        cand["candidate_class"] = "TUPLE"
        return cand

    def test_fail_forces_dead(self):
        cand = self._cand(KG3_EXECUTION="FAIL")
        self.assertEqual(candidate_gates.status_ceiling(cand), "DEAD")

    def test_blocked_forbids_alive(self):
        cand = self._cand(KG4_HALF_LIFE="BLOCKED")
        self.assertEqual(candidate_gates.status_ceiling(cand), "NOT_ALIVE")
        cand["overall_status"] = "ALIVE"
        violations = candidate_gates.ceiling_violations([cand])
        self.assertTrue(violations)

    def test_all_pass_is_the_only_route_to_eligibility(self):
        cand = self._cand()
        self.assertEqual(candidate_gates.status_ceiling(cand), "ELIGIBLE_FOR_M1B")

    def test_dead_without_a_fail_gate_is_a_violation(self):
        cand = self._cand(KG1_MECHANISM="BLOCKED")
        cand["overall_status"] = "DEAD"
        self.assertTrue(candidate_gates.ceiling_violations([cand]))

    def test_no_shipped_candidate_is_gate_eligible(self):
        rows = []
        for row in tuples.ROWS:
            cand = {g: row[g] for g in constants.GATE_IDS}
            cand["overall_status"] = row["overall_status"]
            cand["candidate_id"] = row["candidate_id"]
            cand["candidate_class"] = row["candidate_class"]
            rows.append(cand)
        self.assertEqual(candidate_gates.ceiling_violations(rows), [])
        self.assertEqual(candidate_gates.m1b_eligible(rows), [])

    def test_status_counts_separate_tuples_from_other_rows(self):
        rows = []
        for row in tuples.ROWS:
            cand = {g: row[g] for g in constants.GATE_IDS}
            cand["overall_status"] = row["overall_status"]
            cand["candidate_id"] = row["candidate_id"]
            cand["candidate_class"] = row["candidate_class"]
            rows.append(cand)
        counts = candidate_gates.status_counts(rows)
        self.assertEqual(counts["ALL"]["total"], len(tuples.ROWS))
        self.assertEqual(counts["ALL"]["total"],
                         sum(v["total"] for k, v in counts.items() if k != "ALL"))
        self.assertEqual(counts["ALL"]["ALIVE"], 0)


class CoverageAndBlockers(unittest.TestCase):
    def test_neutral_evidence_is_not_support(self):
        rows = [{"evidence_id": "EVD-X", "candidate_ids": "TUP-A", "epistemic_class":
                 "CONSENSUS_FACT", "supports_or_weakens": "NEUTRAL", "venue_id": "VEN-A"}]
        counts = coverage.coverage_row(rows, "TUP-A", "UNK-0001|UNK-0002")
        self.assertEqual(counts["consensus_fact_count"], 1)
        self.assertEqual(counts["support_evidence_count"], 0)
        self.assertEqual(counts["neutral_count"], 1)
        self.assertEqual(counts["blocking_unknown_count"], 2)

    def test_support_requires_both_class_and_direction(self):
        rows = [{"evidence_id": "EVD-Y", "candidate_ids": "TUP-A", "epistemic_class":
                 "EXTRAPOLATION", "supports_or_weakens": "SUPPORTS", "venue_id": "VEN-A"}]
        counts = coverage.coverage_row(rows, "TUP-A", "")
        self.assertEqual(counts["supports_count"], 1)
        self.assertEqual(counts["support_evidence_count"], 0)

    def test_all_candidates_token_expands(self):
        issues = [{"issue_id": "UNK-9", "severity": "BLOCKING", "candidate_id": None,
                   "affected_candidate_ids": "ALL_CANDIDATES"}]
        mapping = coverage.blocking_map(issues, ["TUP-A", "TUP-B"])
        self.assertEqual(mapping["TUP-A"], {"UNK-9"})
        self.assertEqual(mapping["TUP-B"], {"UNK-9"})

    def test_non_blocking_issues_never_enter_the_blocking_map(self):
        issues = [{"issue_id": "UNK-8", "severity": "IMPORTANT", "candidate_id": "TUP-A",
                   "affected_candidate_ids": "TUP-A"}]
        self.assertEqual(coverage.blocking_map(issues, ["TUP-A"]), {})

    def test_venue_specific_support_is_stricter_than_support(self):
        borrowed = [{"evidence_id": "EVD-Z", "candidate_ids": "TUP-A", "epistemic_class":
                     "SUPPORTED_FINDING", "supports_or_weakens": "SUPPORTS",
                     "venue_id": "VEN-OTHER"}]
        cand = {"candidate_id": "TUP-A", "venue_id": "VEN-A"}
        self.assertEqual(coverage.venue_specific_support_count(borrowed, cand), 0)

    def test_shipped_declared_blockers_are_all_registry_blockers(self):
        """Every declared blocker must exist in the registry, as a M1 blocker, for that row.

        Reads the shipped issue registry rather than the corpus parents, because the scoped child
        issues live there and the parent aggregates are deliberately not candidate blockers.
        """
        import csv
        with (REPO / "M1" / "data" / "discrepancies.csv").open(newline="", encoding="utf-8") as fh:
            issues = list(csv.DictReader(fh))
        rows = coverage.coverage_rows(evidence.EVIDENCE, _candidates(), issues)
        for row in rows:
            self.assertEqual(row["declared_is_subset_of_derived"], "YES", row["candidate_id"])


def _candidates():
    """Shipped candidate rows, whose blocking lists are already scoped and M1-filtered."""
    import csv
    path = REPO / "M1" / "data" / "candidate_tuples.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class Feasibility(unittest.TestCase):
    def test_cadence_rule_fails_a_horizon_faster_than_the_feed(self):
        cand = {"candidate_id": "TUP-A", "horizon_min_us": 10_000}
        venue = {"live_feed_min_interval_us": 500_000}
        feas = {"candidate_id": "TUP-A", "live_feed": "FAIL", "historical_feed": "BLOCKED",
                "PIT_reconstructable": "FAIL", "L1_available": "PASS", "L2_available": "PASS",
                "L3_available": "FAIL", "queue_replay_possible": "FAIL",
                "timestamp_adequacy": "BLOCKED", "depth_source_id": "SRC-0111",
                "history_source_id": "SRC-0118", "PIT_source_id": None,
                "timestamp_source_id": None, "feasibility_note": "test"}
        row = coverage.feasibility_row(cand, venue, feas)
        self.assertEqual(row["cadence_vs_horizon"], "FAIL")

    def test_cadence_rule_blocks_without_a_verified_cadence(self):
        cand = {"candidate_id": "TUP-A", "horizon_min_us": 10_000}
        feas = {"candidate_id": "TUP-A", "live_feed": "BLOCKED", "historical_feed": "BLOCKED",
                "PIT_reconstructable": "BLOCKED", "L1_available": "BLOCKED",
                "L2_available": "BLOCKED", "L3_available": "BLOCKED",
                "queue_replay_possible": "BLOCKED", "timestamp_adequacy": "BLOCKED",
                "depth_source_id": None, "history_source_id": None, "PIT_source_id": None,
                "timestamp_source_id": None, "feasibility_note": "test"}
        row = coverage.feasibility_row(cand, {}, feas)
        self.assertEqual(row["cadence_vs_horizon"], "BLOCKED")

    def test_contradiction_is_reported_not_hidden(self):
        cand = {"candidate_id": "TUP-A", "horizon_min_us": 10_000}
        feas = {"candidate_id": "TUP-A", "live_feed": "PASS", "historical_feed": "FAIL",
                "PIT_reconstructable": "PASS", "L1_available": "PASS", "L2_available": "PASS",
                "L3_available": "FAIL", "queue_replay_possible": "PASS",
                "timestamp_adequacy": "BLOCKED", "depth_source_id": None, "history_source_id": None,
                "PIT_source_id": None, "timestamp_source_id": None, "feasibility_note": "test"}
        row = coverage.feasibility_row(cand, {}, feas)
        self.assertIn("CONTRADICTION", row["consistency_note"])

    def test_shipped_feasibility_has_no_internal_contradiction(self):
        rows = [coverage.feasibility_row(dict(t), venues.BY_ID.get(t["venue_id"], {}), f)
                for t, f in zip(_candidates_full(), feasibility.ROWS)]
        for row in rows:
            self.assertEqual(row["consistency_note"], "NO_CONTRADICTION_DETECTED",
                             row["candidate_id"])


def _candidates_full():
    from materialize import candidate_rows  # noqa: WPS433 (test-local import)
    return candidate_rows()


class Latency(unittest.TestCase):
    def test_totals_require_every_stage(self):
        stages = {s: {"p50": 1.0, "p95": 2.0, "p99": 3.0} for s in latency.LATENCY_STAGES}
        totals = latency.aggregate_latency(stages)
        self.assertEqual(totals["T_total_p50_ms"], len(latency.LATENCY_STAGES) * 1.0)
        stages.pop("order_submit_to_ack")
        totals = latency.aggregate_latency(stages)
        self.assertIsNone(totals["T_total_p50_ms"])
        self.assertIn("order_submit_to_ack", totals["T_total_p50_missing_stages"])

    def test_fit_is_blocked_without_a_curve(self):
        fit = latency.latency_fit(None)
        self.assertEqual(fit["latency_fit"], "BLOCKED")
        self.assertIsNone(fit["half_life_ms"])

    def test_curve_is_used_descriptively_without_assuming_a_decay_form(self):
        curve = {0: 10.0, 50: 6.0, 100: 3.0, 250: 0.5, 500: -1.0}
        fit = latency.latency_fit(curve, measured_total_p99_ms=100)
        self.assertEqual(fit["latency_fit"], "PASS")
        self.assertEqual(fit["half_life_ms"], 100)
        self.assertEqual(fit["viable_delay_ceiling_ms"], 250)
        self.assertIn("no decay form assumed", fit["fit_family"])

    def test_fit_fails_when_the_achievable_delay_has_negative_ev(self):
        curve = {0: 10.0, 100: -0.5}
        fit = latency.latency_fit(curve, measured_total_p99_ms=100)
        self.assertEqual(fit["latency_fit"], "FAIL")

    def test_exponential_diagnostic_refuses_degenerate_curves(self):
        self.assertIsNone(latency.log_likelihood_exponential({0: 1.0}))
        self.assertIsNone(latency.geomean_decay_check({0: 1.0, 1: 0.5}))


class HardConstraints(unittest.TestCase):
    def _floor_case(self):
        cand = {"candidate_id": "TUP-CB", "candidate_class": "TUPLE", "venue_id": "VEN-CB",
                "mechanism_id": "MECH-MICRO", "horizon_min_us": 1_000_000,
                "KG3_EXECUTION": "FAIL", "KG5_FALSIFIABILITY": "PASS",
                "execution_style": "AGGRESSIVE", "horizon_band": "H3"}
        ev = [{"evidence_id": "EVD-1", "candidate_ids": "TUP-CB", "supports_or_weakens": "WEAKENS",
               "epistemic_class": "CONSENSUS_FACT", "venue_id": "VEN-CB"}]
        return cand, ev

    def test_fee_floor_elimination_requires_a_sourced_gross_bound(self):
        """A cost level alone is not a kill (D-0022/D-0026)."""
        cand, ev = self._floor_case()
        checks = pareto.hard_constraint_checks(cand, None, ev, required_round_trip_fee_bps=None)
        self.assertEqual([c["rule"] for c in checks], ["HC7_EXECUTION_GATE_FAIL"])
        without_bound = pareto.hard_constraint_checks(cand, None, ev,
                                                     required_round_trip_fee_bps=120.0)
        self.assertEqual([c["rule"] for c in without_bound], ["HC7_EXECUTION_GATE_FAIL"])
        with_bound = pareto.hard_constraint_checks(cand, None, ev,
                                                   required_round_trip_fee_bps=120.0,
                                                   expected_gross_edge_bps=20.0)
        self.assertIn("HC1_FEE_FLOOR_EXCEEDS_SOURCED_GROSS_BOUND",
                      [c["rule"] for c in with_bound])

    def test_a_sourced_bound_below_the_floor_still_eliminates(self):
        cand, ev = self._floor_case()
        checks = pareto.hard_constraint_checks(cand, None, ev,
                                               required_round_trip_fee_bps=120.0,
                                               expected_gross_edge_bps=120.0)
        self.assertNotIn("HC1_FEE_FLOOR_EXCEEDS_SOURCED_GROSS_BOUND",
                         [c["rule"] for c in checks])

    def test_queue_mechanism_needs_queue_capable_data(self):
        cand, ev = self._floor_case()
        cand["mechanism_id"] = "MECH-QIMB"
        cand["KG3_EXECUTION"] = "BLOCKED"
        feas = {"queue_replay_possible": "FAIL", "venue_live_feed_min_interval_us": None}
        checks = pareto.hard_constraint_checks(cand, feas, ev, required_round_trip_fee_bps=None)
        self.assertIn("HC3_QUEUE_REPLAY_UNSUPPORTED", [c["rule"] for c in checks])

    def test_dominance_is_refused_rather_than_scored(self):
        rows = pareto.dominance_rows([{"candidate_id": "TUP-A", "candidate_class": "TUPLE"}])
        self.assertEqual(rows[0]["dominance_status"], "NOT_EVALUATED_UNKNOWN_DIMENSIONS")
        self.assertEqual(rows[0]["pareto_status"], "NOT_EVALUATED")

    def test_shipped_survivors_and_eliminations_partition_the_candidates(self):
        candidates = _candidates_full()
        feas = {r["candidate_id"]: coverage.feasibility_row(
            c, venues.BY_ID.get(c["venue_id"], {}), r)
            for c, r in zip(candidates, feasibility.ROWS)}
        env = envelopes.all_envelopes(candidates, venues.BY_ID)
        floors = {r["candidate_id"]: r["required_round_trip_fee_bps_for_style"] for r in env}
        kept, killed = pareto.survivors(candidates, feas, evidence.EVIDENCE, floors)
        self.assertEqual(len(kept) + len(killed), len(candidates))
        for cand in kept:
            self.assertNotEqual(cand["overall_status"], "DEAD")


class PaperArithmetic(unittest.TestCase):
    def test_monthly_cost_from_the_papers_own_quantities(self):
        self.assertAlmostEqual(paper_arithmetic.blocks_per_month(), 8_640_000.0)
        self.assertAlmostEqual(
            paper_arithmetic.monthly_input_cost_usd(), 87.0912, places=3)
        self.assertAlmostEqual(
            paper_arithmetic.monthly_cost_from_stated_marginal(), 864.0, places=3)

    def test_the_three_cost_statements_do_not_reconcile(self):
        report = paper_arithmetic.consistency_report()
        self.assertFalse(report["consistent"])
        self.assertGreater(report["ratio_token_path_to_stated_point"], 5.0)
        self.assertGreater(report["ratio_block_path_to_stated_point"], 50.0)


class ShippedArtifacts(unittest.TestCase):
    def test_cost_envelope_uses_only_verified_fee_facts(self):
        env = {r["candidate_id"]: r for r in
               envelopes.all_envelopes(_candidates_full(), venues.BY_ID)}
        cb = env["TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG"]
        self.assertEqual(cb["known_cost_floor_bps"], 120.0)
        self.assertEqual(cb["known_cost_floor_known_components"],
                         "taker_fee|taker_fee_second_leg")
        self.assertEqual(cb["full_break_even_status"], "BLOCKED_UNKNOWN_COMPONENTS")
        kr = env["TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG"]
        self.assertEqual(kr["known_cost_floor_bps"], 160.0)
        cme = env["TUP-CME-ES-H1-QDEP-PAS"]
        self.assertIsNone(cme["known_cost_floor_bps"])
        self.assertIsNone(cme["required_round_trip_fee_bps_for_style"])
        bzx = env["TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS"]
        self.assertIsNone(bzx["one_way_taker_fee_bps"],
                          "a per-share fee must not be converted to bps without a price")
        hl = env["TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG"]
        self.assertIsNone(hl["required_round_trip_fee_bps_for_style"],
                          "MIXED style has no single required round trip")

    def test_verified_fee_numbers_match_the_registry_units(self):
        coinbase = venues.BY_ID["VEN-COINBASE-BTCUSD"]
        self.assertEqual((coinbase["maker_fee_value"], coinbase["maker_fee_unit"]), (40, "BPS"))
        kraken = venues.BY_ID["VEN-KRAKEN-BTCUSD"]
        self.assertEqual(kraken["taker_fee_value"], 80)
        bzx = venues.BY_ID["VEN-CBOEBZX-EQ"]
        self.assertEqual(bzx["taker_fee_unit"], "USD_PER_SHARE")
        self.assertEqual(bzx["rebate_value"], 0.0016)

    def test_every_external_source_token_is_preserved_with_url_unknown(self):
        external = [s for s in sources.SOURCES if str(s["raw_citation_token"]).startswith("turn")]
        self.assertEqual(len(external), 25)
        for src in external:
            self.assertIsNone(src["url"], src["source_id"])
            self.assertEqual(src["status"], "PARTIAL")

    def test_unknown_registry_ids_are_unique_and_referenced(self):
        ids = [d["issue_id"] for d in unknowns.DISCREPANCIES]
        self.assertEqual(len(ids), len(set(ids)))
        referenced = set()
        for row in tuples.ROWS:
            for ref in str(row["blocking_issue_ids"]).split("|"):
                if ref.startswith("UNK-"):
                    referenced.add(ref)
        for ref in sorted(referenced):
            self.assertIn(ref, set(ids))

    def test_dead_rows_record_a_resurrection_condition(self):
        for row in tuples.ROWS:
            if row["overall_status"] != "DEAD":
                continue
            for field in ("kill_gate", "kill_reason", "resurrection_condition"):
                self.assertFalse(str(row[field]).startswith("UNKNOWN"),
                                 f"{row['candidate_id']}.{field}")
            self.assertEqual(row["kill_gate"], tuples.REPORT_KILL_GATE and row["kill_gate"])

    def test_validator_passes_on_the_shipped_artifacts(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = validate.main()
        self.assertEqual(code, 0, "shipped artifacts failed validation")


if __name__ == "__main__":
    unittest.main(verbosity=2)