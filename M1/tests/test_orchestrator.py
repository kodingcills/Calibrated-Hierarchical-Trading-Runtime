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
import contextlib  # noqa: E402
import coverage  # noqa: E402
import io  # noqa: E402
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

    def test_shipped_patches_are_applied_and_their_sources_reached_canonical_state(self):
        """Every code-authored patch is applied, and its sources are in canonical state."""
        from corpus import patches as code_patches
        summary = load("M1/output/M1_STATE_SUMMARY.json")
        self.assertEqual(summary["patches"]["rejected"], 0)
        self.assertEqual(summary["patches"]["applied"], len(code_patches.CODE_PATCHES))
        source_ids = {r["source_id"] for r in _csv_rows("M1/data/source_registry.csv")}
        for sid in ("SRC-0201", "SRC-0203", "SRC-0206", "SRC-0208",
                    "SRC-0213", "SRC-0219", "SRC-0222", "SRC-0228"):
            self.assertIn(sid, source_ids)

    def test_every_applied_patch_is_audited(self):
        summary = load("M1/output/M1_STATE_SUMMARY.json")
        entries = [a for a in summary["patches"]["audit"] if a.get("kind") == "PATCH"]
        self.assertEqual(len([e for e in entries if e["applied"]]),
                         summary["patches"]["applied"])
        for patch in load("M1/work/patches/P-0001.json"), load("M1/work/patches/P-0002.json"):
            self.assertTrue(any(e["patch_id"] == patch["patch_id"] for e in entries))

    def test_rejected_patch_reasons_are_preserved(self):
        """A rejection is evidence too: it must not be silently dropped."""
        summary = load("M1/output/M1_STATE_SUMMARY.json")
        self.assertIn("rejections", summary["patches"])


class ResolutionSemantics(unittest.TestCase):
    """HUMAN_INPUT and DEFERRED are surfaced but never dispatched (handoff §1)."""

    def test_human_input_never_enters_the_autonomous_frontier(self):
        cards = {"UNK-H": {"blocker_id": "UNK-H", "resolution_stage": "M1_BLOCKING",
                           "resolution_method": "HUMAN_INPUT", "status": "OPEN",
                           "affected_candidates": ["TUP-X"], "affected_gates": "KG3_EXECUTION",
                           "tier": 1, "branch_impact": "GLOBAL", "kill_potential": "HIGH",
                           "estimated_effort": "SMALL", "title": "t", "required_answer": "a",
                           "decision_prevented": "d", "success_condition": "s",
                           "kill_condition": "k", "priority_reason": "r", "priority_score": None,
                           "last_updated": "2026-09-20", "acceptable_evidence": "e",
                           "disallowed_evidence": "d", "known_evidence_ids": [],
                           "known_source_ids": [], "contradictory_evidence_ids": [],
                           "resurrection_condition": None},
                 "UNK-D": {"blocker_id": "UNK-D", "resolution_stage": "M1_BLOCKING",
                           "resolution_method": "DEFERRED", "status": "OPEN",
                           "affected_candidates": ["TUP-X"], "affected_gates": "NONE",
                           "tier": 4, "branch_impact": "ONE", "kill_potential": "LOW",
                           "estimated_effort": "SMALL", "title": "t", "required_answer": "a",
                           "decision_prevented": "d", "success_condition": "s",
                           "kill_condition": "k", "priority_reason": "r", "priority_score": None,
                           "last_updated": "2026-09-20", "acceptable_evidence": "e",
                           "disallowed_evidence": "d", "known_evidence_ids": [],
                           "known_source_ids": [], "contradictory_evidence_ids": [],
                           "resurrection_condition": None},
                 "UNK-R": {"blocker_id": "UNK-R", "resolution_stage": "M1_BLOCKING",
                           "resolution_method": "PUBLIC_RESEARCH", "status": "OPEN",
                           "affected_candidates": ["TUP-X"], "affected_gates": "KG1_MECHANISM",
                           "tier": 1, "branch_impact": "SMALL", "kill_potential": "MEDIUM",
                           "estimated_effort": "SMALL", "title": "t", "required_answer": "a",
                           "decision_prevented": "d", "success_condition": "s",
                           "kill_condition": "k", "priority_reason": "r", "priority_score": None,
                           "last_updated": "2026-09-20", "acceptable_evidence": "e",
                           "disallowed_evidence": "d", "known_evidence_ids": [],
                           "known_source_ids": [], "contradictory_evidence_ids": [],
                           "resurrection_condition": None}}
        frontier = blocker_card.frontier_cards(cards)
        self.assertEqual([c["blocker_id"] for c in frontier], ["UNK-R"])

    def test_shipped_human_input_items_are_in_the_human_queue_not_the_frontier(self):
        status = load("M1/output/M1_CLOSURE_STATUS.json")
        frontier_ids = status["frontier"]["active_items"]
        queue = (REPO / "M1/output/M1_EXTERNAL_ACTION_QUEUE.md").read_text(encoding="utf-8")
        self.assertIn("Human input required", queue)
        self.assertIn("UNK-0034", queue)
        self.assertNotIn("UNK-0034", frontier_ids)

    def test_deferred_work_is_never_dispatched(self):
        cards = blocker_card.compile_all(_issue_dicts(), _candidates(), _evidence(), _sources(),
                                        "2026-09-20")
        for card in blocker_card.frontier_cards(cards):
            self.assertIn(card["resolution_method"], ("PUBLIC_RESEARCH", "EXTERNAL_ACTION"))


class ParentChildScope(unittest.TestCase):
    """A coarse blocker must not mechanically block unrelated candidates (handoff §2)."""

    def test_parents_are_aggregates_and_never_block(self):
        rows = _issue_dicts()
        parents = {r["issue_id"] for r in rows if r["is_aggregate_parent"] == "YES"}
        self.assertEqual(parents, {"UNK-0009", "UNK-0018", "UNK-0023"})
        mapping = coverage.blocking_map(rows, [c["candidate_id"] for c in _candidates()])
        for cid, issues in mapping.items():
            self.assertFalse(issues & parents, f"{cid} blocked by an aggregate parent")

    def test_children_carry_scope_and_candidates_name_children(self):
        rows = {r["candidate_id"]: r for r in _candidates()}
        cme = rows["TUP-CME-ES-H1-QDEP-PAS"]["blocking_issue_ids"]
        self.assertIn("UNK-0018-CME", cme)
        self.assertNotIn("UNK-0018-NASDAQ", cme)
        nasdaq = rows["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"]["blocking_issue_ids"]
        self.assertIn("UNK-0018-NASDAQ", nasdaq)
        self.assertNotIn("UNK-0018-CME", nasdaq)

    def test_candidate_blocking_lists_hold_m1_blockers_only(self):
        stages = {r["issue_id"]: r["resolution_stage"] for r in _issue_dicts()}
        for row in _candidates():
            for ref in str(row["blocking_issue_ids"]).split("|"):
                if ref in ("NONE", ""):
                    continue
                self.assertEqual(stages.get(ref), "M1_BLOCKING", f"{row['candidate_id']}: {ref}")


class EvidenceScope(unittest.TestCase):
    """Candidate linkage must never create empirical scope (handoff §5)."""

    def test_kg1_ignores_administratively_linked_evidence(self):
        cand = {"candidate_id": "TUP-X", "candidate_class": "TUPLE", "venue_id": "VEN-A"}
        mislinked = [{"evidence_id": "EVD-M", "supports_or_weakens": "SUPPORTS",
                      "epistemic_class": "SUPPORTED_FINDING", "candidate_ids": "TUP-X",
                      "venue_id": "VEN-A", "observed_venue": "VEN-B",
                      "transfer_status": "CLOSE_TRANSFER", "contradicts_mechanism": "NO"}]
        self.assertEqual(gate_engine._support(mislinked, cand), [])
        correct = [dict(mislinked[0], observed_venue="VEN-A", transfer_status="DIRECT")]
        self.assertEqual(gate_engine._support(correct, cand), ["EVD-M"])

    def test_supporting_records_are_consistent_between_scope_and_transfer(self):
        """A support may declare unknown scope only if it does not claim direct transfer."""
        for row in _csv_rows("M1/data/evidence_ledger.csv"):
            if row["supports_or_weakens"] != "SUPPORTS":
                continue
            direct = row["transfer_status"] in ("DIRECT", "CLOSE_TRANSFER")
            scope_known = all(row[f] not in ("", "UNKNOWN") for f in
                              ("observed_market", "observed_instrument_or_universe",
                               "observed_horizon"))
            self.assertTrue(row["candidate_link_reason"] not in ("", "UNKNOWN"),
                            row["evidence_id"])
            if direct:
                self.assertTrue(scope_known,
                                f"{row['evidence_id']} claims {row['transfer_status']} transfer "
                                f"without declaring observed scope")
            else:
                self.assertFalse(scope_known and row["transfer_status"] == "DIRECT")

    def test_kg4_requires_positive_horizon_evidence(self):
        cand = {"candidate_id": "TUP-X", "venue_id": "VEN-A", "horizon_min_us": 1_000_000,
                "candidate_class": "TUPLE", "instrument": "ES", "mechanism_id": "MECH-OFI"}
        feas = {"cadence_vs_horizon": "BLOCKED", "venue_live_feed_min_interval_us": None,
                "candidate_horizon_min_us": 1_000_000}
        without = gate_engine.kg4_horizon(cand, feas, ["EV_DELAY_SWEEP"], horizon_evidence=[])
        self.assertEqual(without.value, "BLOCKED")
        self.assertEqual(without.rule, "KG4-R5")
        with_evidence = gate_engine.kg4_horizon(cand, feas, ["EV_DELAY_SWEEP"],
                                                horizon_evidence=["EVD-1"])
        self.assertEqual(with_evidence.value, "PASS")


class DeathAudit(unittest.TestCase):
    def test_supersessions_are_recorded_with_a_re_kill_condition(self):
        rows = _csv_rows("M1/output/kill_supersessions.csv")
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["verdict"], "SUPERSEDED")
            self.assertEqual(row["materiality_bound"], "NONE FOUND")
            self.assertTrue(row["re_kill_condition"])
            self.assertTrue(row["original_rationale"])

    def test_superseded_candidates_are_no_longer_dead(self):
        rows = {r["candidate_id"]: r for r in _candidates()}
        for cid in ("TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG", "TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG"):
            self.assertNotEqual(rows[cid]["overall_status"], "DEAD")
            self.assertEqual(rows[cid]["kill_status"], "SUPERSEDED")

    def test_no_candidate_is_killed_on_a_cost_level_alone(self):
        table = {r["candidate_id"]: r for r in _csv_rows("M1/output/cost_envelopes.csv")}
        for row in _candidates():
            floor = table[row["candidate_id"]]["required_round_trip_fee_bps_for_style"]
            if floor in ("", "UNKNOWN", None):
                continue
            self.assertNotEqual(row["KG3_EXECUTION"], "FAIL",
                                f"{row['candidate_id']} killed on a floor of {floor} bps alone")

    def test_eliminations_never_use_the_removed_rule(self):
        rules = {r["rule"] for r in _csv_rows("M1/output/hard_constraint_eliminations.csv")}
        self.assertNotIn("HC1_FEE_FLOOR_WITHOUT_GROSS_EVIDENCE", rules)


class ProjectStateProse(unittest.TestCase):
    def test_stale_state_values_fail_validation(self):
        """Regression for the exact 51/29 vs current-state failure (handoff §9)."""
        text = ("# PROJECT_STATE\n\nM1-C materialisation is COMPLETE: 51 sources, 29 evidence "
                "records, 19 venue rows.\n")
        stripped = validate.re.sub(r"<!-- GENERATED:.*?<!-- /GENERATED:[\w-]+ -->", "", text,
                                   flags=validate.re.DOTALL)
        found = validate.re.findall(r"(\d[\d,]*)\s+(?:verified\s+)?sources\b", stripped,
                                    flags=validate.re.IGNORECASE)
        self.assertEqual(found, ["51"])
        summary = load("M1/output/M1_STATE_SUMMARY.json")
        self.assertNotEqual(int(found[0]), summary["counts"]["source_registry"])
        self.assertEqual(validate.main.__name__, "main")

    def test_shipped_project_state_has_no_stale_values(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(validate.main(), 0)


class GateSemantics(unittest.TestCase):
    def test_kg4_requires_spec_and_positive_horizon_evidence(self):
        cand = {"candidate_id": "TUP-X", "candidate_class": "TUPLE",
                "instrument": "ES (E-mini S&P 500 future)", "venue_id": "VEN-CME-ES",
                "mechanism_id": "MECH-OFI", "execution_style": "AGGRESSIVE",
                "horizon_band": "H3", "horizon_min_us": 1_000_000,
                "mechanism_id_x": None}
        feas = {"cadence_vs_horizon": "BLOCKED", "venue_live_feed_min_interval_us": None,
                "candidate_horizon_min_us": 1_000_000}
        without_spec = gate_engine.kg4_horizon(cand, feas, [], horizon_evidence=["EVD-1"])
        self.assertEqual(without_spec.rule, "KG4-R3")
        # Spec present but no positive horizon evidence: blocked on C, not passed on silence.
        without_evidence = gate_engine.kg4_horizon(cand, feas, ["EV_DELAY_SWEEP"],
                                                   horizon_evidence=[])
        self.assertEqual(without_evidence.value, "BLOCKED")
        self.assertEqual(without_evidence.rule, "KG4-R5")
        complete = gate_engine.kg4_horizon(cand, feas, ["EV_DELAY_SWEEP"],
                                           horizon_evidence=["EVD-1"])
        self.assertEqual(complete.value, "PASS")
        self.assertEqual(complete.rule, "KG4-R4")

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