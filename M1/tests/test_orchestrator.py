"""Orchestrator-stage tests (handoff §23).

These pin the invariants that make the closure loop safe to operate: stage semantics cannot
re-block M1 with M2 work, a dead branch cannot silently re-enter, a malformed patch cannot move
state, and work ordering is deterministic.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "M1" / "src"
ORCH = REPO / "M1" / "orchestrator"
for _p in (str(SRC), str(ORCH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import blocker_card  # noqa: E402
import coverage  # noqa: E402
import frontier as frontier_mod  # noqa: E402
import gate_engine  # noqa: E402
import patch as patch_mod  # noqa: E402
import priority  # noqa: E402
import resolvers  # noqa: E402
import schemas  # noqa: E402
import transitions  # noqa: E402
import validate  # noqa: E402
from corpus import constants, staging, tuples, unknowns  # noqa: E402


def load(name):
    return json.loads((REPO / name).read_text(encoding="utf-8"))


class StageModel(unittest.TestCase):
    def test_every_authored_issue_has_a_valid_two_dimension_classification(self):
        rows = staging.rows()
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["resolution_method"], staging.RESOLUTION_METHODS, row["issue_id"])
            self.assertIn(row["resolution_stage"], staging.RESOLUTION_STAGES, row["issue_id"])
            self.assertIn(row["tier"], staging.TIER_DEFINITIONS, row["issue_id"])
            self.assertTrue(row["migration_reason"], row["issue_id"])

    def test_every_registry_issue_is_migrated(self):
        self.assertEqual(staging.unmapped([d["issue_id"] for d in unknowns.DISCREPANCIES]), [])

    def test_shipped_registry_has_no_blocking_issue_outside_the_m1_frontier(self):
        rows = list(_discrepancy_rows())
        for row in rows:
            if row["severity"] == "BLOCKING":
                self.assertEqual(row["resolution_stage"], "M1_BLOCKING", row["issue_id"])

    def test_m2_and_post_m2_issues_do_not_block_m1_eligibility(self):
        """The circularity fix: an M2 measurement must not appear as an M1 blocker."""
        rows = list(_discrepancy_rows())
        m2 = [r for r in rows if r["resolution_stage"] in ("M2_MEASUREMENT", "POST_M2")]
        self.assertTrue(m2, "expected migrated measurement issues")
        for row in m2:
            self.assertNotEqual(row["severity"], "BLOCKING", row["issue_id"])
        blocking = coverage.blocking_map(rows, ["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"])
        self.assertNotIn("UNK-0008", blocking.get("TUP-NASDAQ-LARGETICK-H2-QIMB-AGG", set()),
                         "signal half-life must no longer block M1")

    def test_m1_blocking_issue_still_blocks_its_candidates(self):
        rows = list(_discrepancy_rows())
        blocking = coverage.blocking_map(rows, ["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"])
        self.assertIn("UNK-0004", blocking["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"])


def _discrepancy_rows():
    import csv
    with (REPO / "M1/data/discrepancies.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class FrontierAndPriority(unittest.TestCase):
    def test_frontier_excludes_non_m1_issues(self):
        cards = blocker_card.compile_all([dict(r) for r in _issue_dicts()],
                                        _candidates(), _evidence(), _sources(), "2026-09-20")
        active = blocker_card.frontier_cards(cards)
        for card in active:
            self.assertEqual(card["resolution_stage"], "M1_BLOCKING")
            self.assertIn(card["status"], ("OPEN", "IN_PROGRESS"))

    def test_shipped_frontier_matches_the_registry(self):
        payload = load("M1/work/frontier.json")
        rows = {r["issue_id"]: r for r in _discrepancy_rows()}
        for item in payload["items"]:
            self.assertEqual(rows[item["blocker_id"]]["resolution_stage"], "M1_BLOCKING")
            self.assertIn(rows[item["blocker_id"]]["status"], ("OPEN", "IN_PROGRESS"))

    def test_priority_is_deterministic_under_equal_inputs(self):
        card_a = {"blocker_id": "UNK-9002", "tier": 1, "branch_impact": "HIGH",
                  "kill_potential": "HIGH", "estimated_effort": "SMALL"}
        card_b = dict(card_a, blocker_id="UNK-9001")
        first = [c["blocker_id"] for c in priority.rank([card_a, card_b])]
        second = [c["blocker_id"] for c in priority.rank([card_b, card_a])]
        self.assertEqual(first, second)
        self.assertEqual(first[0], "UNK-9001", "ties break on id, not on input order")

    def test_cheap_tiers_outrank_measurement_work(self):
        cheap = {"blocker_id": "UNK-A", "tier": 1, "branch_impact": "ONE",
                 "kill_potential": "HIGH", "estimated_effort": "SMALL"}
        measurement = {"blocker_id": "UNK-B", "tier": 4, "branch_impact": "GLOBAL",
                       "kill_potential": "LOW", "estimated_effort": "MEDIUM"}
        ranked = priority.rank([cheap, measurement])
        self.assertEqual(ranked[0]["blocker_id"], "UNK-A")

    def test_cluster_mapping_is_total(self):
        for cand in _candidates():
            self.assertNotEqual(frontier_mod.cluster_of(cand["candidate_id"]), "UNCLUSTERED")


class Transitions(unittest.TestCase):
    def test_dead_candidate_cannot_re_enter_without_a_resurrection_decision(self):
        allowed, reason = transitions.candidate_transition_allowed("DEAD", "WEAK")
        self.assertFalse(allowed)
        self.assertIn("resurrection", reason)
        allowed, _ = transitions.candidate_transition_allowed("DEAD", "WEAK",
                                                             resurrection_decision="DEC-XYZ")
        self.assertTrue(allowed)

    def test_illegal_issue_transition_is_refused(self):
        allowed, _ = transitions.legal_transition("SUPERSEDED", "OPEN")
        self.assertFalse(allowed)
        allowed, _ = transitions.legal_transition("OPEN", "RESOLVED_SUPPORTS")
        self.assertTrue(allowed)

    def test_gate_moves_are_whitelisted_per_decision(self):
        self.assertIn(("BLOCKED", "PASS"), transitions.ALLOWED_GATE_MOVES["SUPPORTS"])
        self.assertNotIn(("PASS", "PASS"), transitions.ALLOWED_GATE_MOVES["SUPPORTS"])
        self.assertIn(("PASS", "FAIL"), transitions.ALLOWED_GATE_MOVES["KILLS"])


class PatchIntegrity(unittest.TestCase):
    def _context(self):
        return patch_mod.canonical_context(_sources(), _evidence(), _candidates(),
                                           [dict(r) for r in _issue_dicts()])

    def _card(self):
        return {"blocker_id": "UNK-0004", "resolution_stage": "M1_BLOCKING",
                "affected_candidates": ["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"]}

    def test_invalid_patch_cannot_change_state(self):
        bad = {"patch_id": "P-BAD", "decision": "SUPPORTS"}
        result = transitions.verify_patch(bad, self._card(), self._context())
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("SCHEMA", result["rejected_claims"])

    def test_patch_with_unresolvable_references_is_rejected(self):
        builder = patch_mod.build_patch(
            "P-REF", ["UNK-0004"], "SUPPORTS", "test", "contrary evidence searched", "2026-09-20",
            new_evidence=[{"evidence_id": "EVD-9901", "claim": "x", "source_id": "SRC-9999",
                           "candidate_ids": "TUP-NOT-REAL", "epistemic_class": "CONSENSUS_FACT",
                           "evidence_origin": "EXTERNAL_VERIFIED", "supports_or_weakens": "SUPPORTS",
                           "methodology": "m", "sample": "s", "temporal_scope": "t",
                           "gross_or_net": "N/A", "limitations": "l",
                           "decision_implication": "i", "verification_status": "PRIMARY_DOCUMENT"}])
        result = transitions.verify_patch(builder, self._card(), self._context())
        self.assertEqual(result["status"], "REJECTED")
        self.assertTrue(any("not resolvable" in r for r in result["rejected_claims"]))
        self.assertTrue(any("unknown candidate" in r for r in result["rejected_claims"]))

    def test_extrapolation_cannot_be_recorded_as_support(self):
        builder = patch_mod.build_patch(
            "P-EXT", ["UNK-0004"], "SUPPORTS", "test", "contrary evidence searched", "2026-09-20",
            new_evidence=[{"evidence_id": "EVD-9902", "claim": "x", "source_id": "SRC-0201",
                           "candidate_ids": "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
                           "epistemic_class": "EXTRAPOLATION",
                           "evidence_origin": "EXTERNAL_VERIFIED",
                           "supports_or_weakens": "SUPPORTS", "methodology": "m", "sample": "s",
                           "temporal_scope": "t", "gross_or_net": "N/A", "limitations": "l",
                           "decision_implication": "i", "verification_status": "PRIMARY_DOCUMENT"}])
        result = transitions.verify_patch(builder, self._card(), self._context())
        self.assertEqual(result["status"], "REJECTED")

    def test_shipped_patch_is_applied_and_its_sources_reached_canonical_state(self):
        summary = load("M1/output/M1_STATE_SUMMARY.json")
        self.assertEqual(summary["patches"]["rejected"], 0)
        self.assertEqual(summary["patches"]["applied"], 1)
        source_ids = {r["source_id"] for r in
                      _csv_rows("M1/data/source_registry.csv")}
        for sid in ("SRC-0201", "SRC-0203", "SRC-0206", "SRC-0208"):
            self.assertIn(sid, source_ids)

    def test_rejected_patch_reasons_are_preserved(self):
        """A rejection is evidence too: it must not be silently dropped."""
        summary = load("M1/output/M1_STATE_SUMMARY.json")
        self.assertIn("rejections", summary["patches"])


class GateSemantics(unittest.TestCase):
    def test_kg4_passes_without_a_measured_half_life_but_requires_a_spec(self):
        cand = {"candidate_id": "TUP-X", "candidate_class": "TUPLE",
                "instrument": "ES (E-mini S&P 500 future)", "venue_id": "VEN-CME-ES",
                "mechanism_id": "MECH-OFI", "execution_style": "AGGRESSIVE",
                "horizon_band": "H3", "horizon_min_us": 1_000_000,
                "mechanism_id_x": None}
        feas = {"cadence_vs_horizon": "BLOCKED", "venue_live_feed_min_interval_us": None,
                "candidate_horizon_min_us": 1_000_000}
        without = gate_engine.kg4_horizon(cand, feas, [])
        self.assertEqual(without.value, "BLOCKED")
        self.assertEqual(without.rule, "KG4-R3")
        with_spec = gate_engine.kg4_horizon(cand, feas, ["EV_DELAY_SWEEP"])
        self.assertEqual(with_spec.value, "PASS")
        self.assertEqual(with_spec.rule, "KG4-R4")

    def test_kg4_fails_on_a_verified_physical_timing_contradiction(self):
        cand = {"candidate_id": "TUP-Y", "horizon_min_us": 10_000}
        feas = {"cadence_vs_horizon": "FAIL", "venue_live_feed_min_interval_us": 500_000,
                "candidate_horizon_min_us": 10_000}
        verdict = gate_engine.kg4_horizon(cand, feas, ["EV_DELAY_SWEEP"])
        self.assertEqual(verdict.value, "FAIL")
        self.assertEqual(verdict.rule, "KG4-R1")

    def test_kg5_blocks_on_a_family_level_instrument(self):
        blocked = gate_engine.kg5_falsifiability({
            "candidate_id": "T", "candidate_class": "TUPLE",
            "instrument": "Treasury future (exact contract UNSPECIFIED)",
            "horizon_min_us": 100_000, "mechanism_id": "MECH-REPLEN"})
        self.assertEqual(blocked.value, "BLOCKED")
        passed = gate_engine.kg5_falsifiability({
            "candidate_id": "T", "candidate_class": "TUPLE",
            "instrument": "ES (E-mini S&P 500 future)", "horizon_min_us": 100_000,
            "mechanism_id": "MECH-OFI"})
        self.assertEqual(passed.value, "PASS")

    def test_kg3_requires_a_verified_fee_component(self):
        cand = {"candidate_id": "T", "candidate_class": "TUPLE", "execution_style": "AGGRESSIVE",
                "mechanism_id": "MECH-OFI", "_venue_specific_support_ids": "EVD-1"}
        verdict = gate_engine.kg3_execution(
            cand, {"required_round_trip_fee_bps_for_style": None}, {}, {}, ["EV_DELAY_SWEEP"])
        self.assertEqual(verdict.value, "BLOCKED")
        self.assertEqual(verdict.rule, "KG3-R4")

    def test_gate_eligibility_requires_all_five(self):
        computed = {"TUP-X": {g: gate_engine.Verdict("PASS", "R", "r") for g in constants.GATE_IDS}}
        self.assertEqual(gate_engine.eligible(computed), ["TUP-X"])
        computed["TUP-X"]["KG4_HALF_LIFE"] = gate_engine.Verdict("BLOCKED", "R", "r")
        self.assertEqual(gate_engine.eligible(computed), [])

    def test_m1b_authorization_follows_eligibility(self):
        status = load("M1/output/M1_CLOSURE_STATUS.json")
        eligible = status["gate_eligible"]
        expected = "AUTHORIZED" if eligible else "NOT_AUTHORIZED"
        self.assertEqual(status["milestones"]["M1-B"], expected)
        self.assertEqual(status["milestones"]["M1-D1"], expected)


class ResolverArtefacts(unittest.TestCase):
    def test_every_external_action_blocker_has_a_complete_request(self):
        frontier_payload = load("M1/work/frontier.json")
        for item in frontier_payload["items"]:
            if item["resolution_method"] != "EXTERNAL_ACTION":
                continue
            content = resolvers.REQUEST_CONTENT.get(item["blocker_id"])
            self.assertIsNotNone(content, item["blocker_id"])
            for key in ("information", "product", "schema", "timestamps", "licensing", "sample",
                        "substitute", "contact"):
                self.assertTrue(content[key], f"{item['blocker_id']}.{key}")
            path = REPO / "M1" / "work" / "external_requests" / f"{item['blocker_id']}.md"
            self.assertTrue(path.exists(), item["blocker_id"])
            text = path.read_text(encoding="utf-8")
            for section in ("PURPOSE", "EXACT INFORMATION REQUIRED", "WHAT AN ANSWER KILLS",
                            "WHAT AN ANSWER CLEARS", "READY-TO-SEND TEXT"):
                self.assertIn(section, text)

    def test_every_m2_spec_has_the_required_sections_and_a_registry_entry(self):
        registry = load("M1/work/m2_specs/registry.json")
        for spec_id in registry["specs"]:
            path = REPO / "M1" / "work" / "m2_specs" / f"{spec_id}.md"
            self.assertTrue(path.exists(), spec_id)
            text = path.read_text(encoding="utf-8")
            for section in ("Question being answered", "Dataset required", "Primary metric",
                            "Null hypothesis", "Kill criterion", "How the result updates gates",
                            "Preregistration requirement"):
                self.assertIn(section, text)
        for cid, spec_ids in registry["by_candidate"].items():
            self.assertTrue(spec_ids, cid)
            self.assertIn("EV_DELAY_SWEEP", spec_ids)

    def test_spec_registry_excludes_non_tuple_rows(self):
        registry = load("M1/work/m2_specs/registry.json")
        for row in _candidates():
            if row["candidate_class"] != "TUPLE":
                self.assertNotIn(row["candidate_id"], registry["by_candidate"])


class NumericProvenance(unittest.TestCase):
    def test_numeric_value_without_a_source_fails_validation(self):
        tables = {"candidate_tuples": {"exists": True, "cols": ["candidate_id", "horizon_min_us",
                                                               "horizon_taxonomy_source_id",
                                                               "unknown_fields"],
                                       "rows": [{"candidate_id": "TUP-X",
                                                 "horizon_min_us": "1000",
                                                 "horizon_taxonomy_source_id": "UNKNOWN",
                                                 "unknown_fields": "NONE"}]}}
        saved = list(validate.FAILURES)
        validate.FAILURES.clear()
        validate.v2_numeric_sources(tables)
        failures = list(validate.FAILURES)
        validate.FAILURES[:] = saved
        self.assertTrue(any("without a source column" in f["detail"] for f in failures),
                        failures)

    def test_empty_numeric_cell_must_be_declared_unknown(self):
        tables = {"candidate_tuples": {"exists": True, "cols": ["candidate_id", "horizon_min_us",
                                                               "horizon_taxonomy_source_id",
                                                               "unknown_fields"],
                                       "rows": [{"candidate_id": "TUP-X",
                                                 "horizon_min_us": None,
                                                 "horizon_taxonomy_source_id": "UNKNOWN",
                                                 "unknown_fields": "NONE"}]}}
        saved = list(validate.FAILURES)
        validate.FAILURES.clear()
        validate.v2_numeric_sources(tables)
        failures = list(validate.FAILURES)
        validate.FAILURES[:] = saved
        self.assertTrue(any("not declared in unknown_fields" in f["detail"] for f in failures))

    def test_unknown_is_never_written_as_zero(self):
        import csv
        for row in _csv_rows("M1/output/cost_envelopes.csv"):
            for field in ("spread_bps", "slippage_bps", "impact_bps", "adverse_selection_bps",
                          "funding_bps", "full_break_even_bps"):
                self.assertNotEqual(row[field], "0", f"{row['candidate_id']}.{field}")

    def test_shipped_artifacts_pass_the_full_validator(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            code = validate.main()
        self.assertEqual(code, 0)

    def test_root_mirrors_match_canonical_tables(self):
        pairs = [("EVIDENCE_LEDGER.csv", "M1/data/evidence_ledger.csv"),
                 ("ASSUMPTIONS.csv", "M1/data/assumptions.csv"),
                 ("EXPERIMENTS.csv", "M1/data/experiments.csv"),
                 ("HYPOTHESES.csv", "M1/data/hypotheses.csv")]
        for root_name, canonical in pairs:
            self.assertEqual((REPO / root_name).read_bytes(),
                             (REPO / canonical).read_bytes(), root_name)


def _issue_dicts():
    import csv
    with (REPO / "M1/data/discrepancies.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _candidates():
    return [dict(r) for r in _csv_rows("M1/data/candidate_tuples.csv")]


def _evidence():
    return [dict(r) for r in _csv_rows("M1/data/evidence_ledger.csv")]


def _sources():
    return [dict(r) for r in _csv_rows("M1/data/source_registry.csv")]


def _csv_rows(path):
    import csv
    with (REPO / path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


if __name__ == "__main__":
    unittest.main(verbosity=2)