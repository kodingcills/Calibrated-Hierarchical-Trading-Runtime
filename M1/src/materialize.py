#!/usr/bin/env python3
"""Materialise the M1-C data model and the M1-D0 derived outputs.

Run:  python3 M1/src/materialize.py

Reads the declarative corpus in ``M1/src/corpus/`` plus the computation modules, and writes:

  M1/data/*.csv                 canonical M1-C tables
  M1/output/*.csv|json|md       M1-D0 derived results
  <repo root>/*.csv|md          canonical root artifacts and generated registries

Nothing in this file decides anything that is not computed from the corpus. Re-running it is
safe and idempotent; every output is regenerated.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import candidate_gates  # noqa: E402
import coverage  # noqa: E402
import envelopes  # noqa: E402
import latency  # noqa: E402
import paper_arithmetic  # noqa: E402
import pareto  # noqa: E402
import readiness  # noqa: E402
import report  # noqa: E402
from corpus import (assumptions, constants, evidence, experiments, feasibility, gates,  # noqa: E402
                    mechanisms, sources, techfit, tuples, unknowns, venues)

M1 = SRC.parent
REPO = M1.parent
DATA = M1 / "data"
OUT = M1 / "output"
RAW = M1 / "raw"
MANIFEST = RAW / "source_manifest.json"

TOKEN_SOURCES = ("turn",)


# --------------------------------------------------------------------- derive
def horizon_bounds(band):
    if band in constants.HORIZON_BANDS:
        return constants.HORIZON_BANDS[band]
    if "-" in band:
        first, last = band.split("-", 1)
        if first in constants.HORIZON_BANDS and last in constants.HORIZON_BANDS:
            return constants.HORIZON_BANDS[first][0], constants.HORIZON_BANDS[last][1]
    return None, None


def candidate_rows():
    rows = []
    for row in tuples.ROWS:
        cand = dict(row)
        lo, hi = horizon_bounds(cand["horizon_band"])
        cand["horizon_min_us"] = lo
        cand["horizon_max_us"] = hi
        cand["horizon_taxonomy_source_id"] = (constants.HORIZON_TAXONOMY_ASSUMPTION
                                              if lo is not None else None)
        cand["economic_mechanism_status"] = cand["KG1_MECHANISM"]
        cand["data_status"] = cand["KG2_DATA"]
        cand["execution_status"] = cand["KG3_EXECUTION"]
        cand["half_life_status"] = cand["KG4_HALF_LIFE"]
        rows.append(cand)
    return rows


def attach_source_hashes():
    """Copy SHA-256 digests from the raw manifest into the source registry."""
    if not MANIFEST.exists():
        return
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_path = {entry["original_path"]: entry["sha256"] for entry in manifest["files"]}
    for row in sources.SOURCES:
        local = row.get("local_path")
        if local and local in by_path:
            row["sha256"] = by_path[local]


# ---------------------------------------------------------------------- main
def main():
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    attach_source_hashes()
    candidates = candidate_rows()
    cand_by_id = {c["candidate_id"]: c for c in candidates}
    apply_blocking_derivation(candidates)
    venue_by_id = {v["venue_id"]: v for v in venues.ROWS}
    ev_rows = evidence.EVIDENCE
    feas_by_id = {f["candidate_id"]: f for f in feasibility.ROWS}

    # ---- derived: fee envelopes, feasibility verdicts, coverage, gates, latency, pareto
    env_rows = envelopes.all_envelopes(candidates, venue_by_id)
    env_by_id = {r["candidate_id"]: r for r in env_rows}
    fee_floor_by_id = {cid: r["required_round_trip_fee_bps_for_style"]
                       for cid, r in env_by_id.items()}

    feas_rows = [coverage.feasibility_row(cand_by_id[f["candidate_id"]],
                                          venue_by_id.get(cand_by_id[f["candidate_id"]]["venue_id"]),
                                          f)
                 for f in feasibility.ROWS]
    feas_out_by_id = {r["candidate_id"]: r for r in feas_rows}

    gate_rows = candidate_gates.gate_status_rows(candidates)
    coverage_rows = coverage.coverage_rows(ev_rows, candidates, unknowns.DISCREPANCIES)

    kept, killed = pareto.survivors(candidates, feas_out_by_id, ev_rows, fee_floor_by_id)
    survivor_rows = pareto.survivor_rows(kept, cand_by_id)
    elimination_rows = pareto.elimination_rows(killed)
    dominance_rows = pareto.dominance_rows(candidates)

    latency_rows = latency.latency_feasibility_rows(candidates)

    count_rows = candidate_gates.gate_counts(candidates)
    for gate in gates.ROWS:
        counts = count_rows[gate["gate_id"]]
        gate["candidates_pass"] = counts["PASS"]
        gate["candidates_blocked"] = counts["BLOCKED"]
        gate["candidates_fail"] = counts["FAIL"]

    status_counts = candidate_gates.status_counts(candidates)
    ceiling_violations = candidate_gates.ceiling_violations(candidates)

    status_review = []
    for cand in candidates:
        status_review.append({
            "candidate_id": cand["candidate_id"],
            "candidate_class": cand["candidate_class"],
            "report_status": cand["overall_status"],
            "status_ceiling": candidate_gates.status_ceiling(cand),
            "ceiling_permits_status": (
                "YES" if status_review_ok(cand) else "NO"),
            "status_basis": cand["status_basis"],
        })

    dead_rows = build_dead_rows(candidates, ev_rows)

    candidate_ids = set(cand_by_id)
    blocker_rows = readiness.blocker_priority_rows(unknowns.DISCREPANCIES,
                                                   unknowns.OPEN_QUESTIONS, candidate_ids)

    # ---- canonical M1-C tables
    report.table(DATA / "source_registry.csv", sources.COLUMNS, sources.SOURCES,
                 constants.TABLE_SPECS["source_registry"]["numeric"])
    report.table(DATA / "evidence_ledger.csv", evidence.COLUMNS, ev_rows,
                 constants.TABLE_SPECS["evidence_ledger"]["numeric"])
    report.table(DATA / "venue_facts.csv", venues.COLUMNS, venues.ROWS,
                 constants.TABLE_SPECS["venue_facts"]["numeric"])
    report.table(DATA / "mechanisms.csv", mechanisms.COLUMNS, mechanisms.ROWS,
                 constants.TABLE_SPECS["mechanisms"]["numeric"])
    report.table(DATA / "candidate_tuples.csv", tuples.COLUMNS, candidates,
                 constants.TABLE_SPECS["candidate_tuples"]["numeric"])
    report.table(DATA / "data_feasibility.csv", feasibility.COLUMNS, feasibility.ROWS,
                 constants.TABLE_SPECS["data_feasibility"]["numeric"])
    report.table(DATA / "execution_envelopes.csv", envelopes.COLUMNS, env_rows,
                 constants.TABLE_SPECS["execution_envelopes"]["numeric"])
    report.table(DATA / "technology_fit.csv", techfit.COLUMNS, techfit.ROWS,
                 constants.TABLE_SPECS["technology_fit"]["numeric"])
    report.table(DATA / "discrepancies.csv", unknowns.DISCREPANCY_COLUMNS,
                 unknowns.DISCREPANCIES, constants.TABLE_SPECS["discrepancies"]["numeric"])
    report.table(DATA / "open_questions.csv", unknowns.OPEN_QUESTION_COLUMNS,
                 unknowns.OPEN_QUESTIONS, constants.TABLE_SPECS["open_questions"]["numeric"])
    report.table(DATA / "dead_candidates.csv", DEAD_COLUMNS, dead_rows,
                 constants.TABLE_SPECS["dead_candidates"]["numeric"])
    report.table(DATA / "assumptions.csv", assumptions.COLUMNS, assumptions.ROWS,
                 constants.TABLE_SPECS["assumptions"]["numeric"])
    report.table(DATA / "kill_gates.csv", gates.COLUMNS, gates.ROWS,
                 constants.TABLE_SPECS["kill_gates"]["numeric"])
    report.table(DATA / "experiments.csv", experiments.EXPERIMENT_COLUMNS,
                 experiments.EXPERIMENTS, constants.TABLE_SPECS["experiments"]["numeric"])
    report.table(DATA / "hypotheses.csv", experiments.HYPOTHESIS_COLUMNS,
                 experiments.HYPOTHESES, constants.TABLE_SPECS["hypotheses"]["numeric"])

    # ---- M1-D0 outputs
    report.table(OUT / "candidate_gate_status.csv", GATE_STATUS_COLUMNS, gate_rows)
    report.table(OUT / "evidence_coverage.csv", COVERAGE_COLUMNS, coverage_rows)
    report.table(OUT / "data_feasibility_verdicts.csv", FEAS_VERDICT_COLUMNS, feas_rows)
    report.table(OUT / "cost_envelopes.csv", envelopes.COLUMNS, env_rows,
                 constants.TABLE_SPECS["execution_envelopes"]["numeric"])
    report.table(OUT / "venue_cost_reference.csv", VENUE_COST_COLUMNS,
                 venue_cost_rows(venues.ROWS), VENUE_COST_NUMERIC)
    report.table(OUT / "latency_feasibility.csv", LATENCY_COLUMNS, latency_rows)
    report.table(OUT / "hard_constraint_survivors.csv", SURVIVOR_COLUMNS, survivor_rows)
    report.table(OUT / "hard_constraint_eliminations.csv", ELIMINATION_COLUMNS,
                 elimination_rows)
    report.table(OUT / "dominated_candidates.csv", DOMINANCE_COLUMNS, dominance_rows)
    report.table(OUT / "blocker_priority.csv", BLOCKER_COLUMNS, blocker_rows)
    report.table(OUT / "status_derivation_review.csv", STATUS_REVIEW_COLUMNS, status_review)

    state = {
        "generated_at": generated_at,
        "status_counts": status_counts,
        "m1b_eligible": candidate_gates.m1b_eligible(candidates),
        "blocker_rows": blocker_rows,
        "discrepancies": unknowns.DISCREPANCIES,
        "open_questions": unknowns.OPEN_QUESTIONS,
        "dead_rows": dead_rows,
    }

    (OUT / "M1_D0_READINESS.md").write_text(readiness.readiness_md(state), encoding="utf-8")
    (OUT / "M1_D1_BLOCKED.md").write_text(readiness.d1_blocked_md(state), encoding="utf-8")

    # ---- root canonical artifacts
    report.write_csv(REPO / "EVIDENCE_LEDGER.csv", evidence.COLUMNS, ev_rows)
    report.write_csv(REPO / "ASSUMPTIONS.csv", assumptions.COLUMNS, assumptions.ROWS)
    report.write_csv(REPO / "EXPERIMENTS.csv", experiments.EXPERIMENT_COLUMNS,
                     experiments.EXPERIMENTS)
    report.write_csv(REPO / "HYPOTHESES.csv", experiments.HYPOTHESIS_COLUMNS,
                     experiments.HYPOTHESES)
    (REPO / "DISCREPANCIES_AND_UNKNOWNS.md").write_text(report.discrepancies_md(state),
                                                         encoding="utf-8")
    (REPO / "DEAD_ENDS.md").write_text(report.dead_ends_md(state), encoding="utf-8")
    (REPO / "OPEN_QUESTIONS.md").write_text(report.open_questions_md(state), encoding="utf-8")
    (REPO / "WATCHLIST.md").write_text(report.watchlist_md(state), encoding="utf-8")

    (M1 / "hypotheses" / "README.md").write_text(HYPOTHESES_README, encoding="utf-8")

    sync_project_state_timestamp(generated_at)

    summary = {
        "generated_at": generated_at,
        "generated_by": "M1/src/materialize.py",
        "counts": {
            "source_registry": len(sources.SOURCES),
            "external_token_sources": len([s for s in sources.SOURCES
                                           if str(s["raw_citation_token"]).startswith("turn")]),
            "evidence_records": len(ev_rows),
            "venue_rows": len(venues.ROWS),
            "mechanisms": len(mechanisms.ROWS),
            "candidate_rows": len(candidates),
            "tradable_tuples": status_counts["TUPLE"]["total"],
            "non_tuple_rows": len(candidates) - status_counts["TUPLE"]["total"],
            "status": {k: status_counts["ALL"][k]
                       for k in ("total", "ALIVE", "WEAK", "UNKNOWN", "DEAD")},
            "status_by_class": status_counts,
            "discrepancies": len(unknowns.DISCREPANCIES),
            "open_issues": len(blocker_rows),
            "blocking_issues": len([b for b in blocker_rows
                                    if b["severity"] == "BLOCKING"]),
            "open_questions": len(unknowns.OPEN_QUESTIONS),
            "assumptions": len(assumptions.ROWS),
            "experiments_proposed_not_run": len(experiments.EXPERIMENTS),
            "hypotheses_registered": len(experiments.HYPOTHESES),
            "hard_constraint_eliminations": len({r["candidate_id"]
                                                 for r in elimination_rows}),
            "hard_constraint_survivors": len(survivor_rows),
            "m1b_eligible": candidate_gates.m1b_eligible(candidates),
            "ceiling_violations": len(ceiling_violations),
        },
        "gate_counts": count_rows,
        "pareto": {"executed": False, "reason": pareto.DOMINANCE_NOTE},
        "paper_arithmetic_check": paper_arithmetic.consistency_report(),
        "milestones": {
            "M1-A": "INCOMPLETE",
            "M1-B": "NOT_AUTHORIZED",
            "M1-C": "COMPLETE",
            "M1-D0": "COMPLETE",
            "M1-D1": "NOT_AUTHORIZED",
        },
        "artifact_hashes": artifact_hashes(DATA, OUT),
    }
    report.write_json(OUT / "M1_STATE_SUMMARY.json", summary)

    print(json.dumps(summary["counts"], indent=2, sort_keys=True))
    return 0


def sync_project_state_timestamp(generated_at):
    """Rewrite the `Last Updated` line of PROJECT_STATE.md so it cannot drift from the run."""
    path = REPO / "PROJECT_STATE.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        lines.append(f"Last Updated: {generated_at}" if line.startswith("Last Updated:")
                     else line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_blocking_derivation(candidates):
    """Make blocking_issue_ids the union of the candidate-local list and the registry.

    The authored per-candidate list stays visible in ``blocking_issue_ids_declared`` so the
    curation is auditable, while ``blocking_issue_ids`` is complete: a blocking unknown that
    names the candidate cannot be missing from its row (ASM-0010).
    """
    blocking = coverage.blocking_map(unknowns.DISCREPANCIES,
                                     [c["candidate_id"] for c in candidates])
    for cand in candidates:
        declared = cand["blocking_issue_ids"]
        cand["blocking_issue_ids_declared"] = declared
        union = {x for x in str(declared or "").split("|") if x}
        union |= blocking.get(cand["candidate_id"], set())
        cand["blocking_issue_ids"] = "|".join(sorted(union)) or "NONE"


def status_review_ok(cand):
    ceiling = candidate_gates.status_ceiling(cand)
    status = cand["overall_status"]
    if status == "ALIVE":
        return ceiling == "ELIGIBLE_FOR_M1B"
    if status == "DEAD":
        return ceiling == "DEAD"
    return ceiling == "NOT_ALIVE"


def build_dead_rows(candidates, ev_rows):
    rows = []
    for cand in candidates:
        if cand["overall_status"] != "DEAD":
            continue
        cid = cand["candidate_id"]
        linked = [r["evidence_id"] for r in ev_rows
                  if cid in str(r["candidate_ids"] or "").split("|")]
        rows.append({
            "candidate_id": cid,
            "candidate_class": cand["candidate_class"],
            "death_date": "2026-09-20",
            "death_date_basis": "date of the M1-A artifact (SRC-0011); individual deaths are not "
                                "separately timestamped",
            "kill_gate": cand["kill_gate"],
            "report_kill_gate": tuples.REPORT_KILL_GATE.get(cid),
            "cause": cand["kill_reason"],
            "evidence_ids": "|".join(linked) or "NONE",
            "resurrection_condition": cand["resurrection_condition"],
            "re_entry_policy": "Requires NEW_EVIDENCE plus an explicit resurrection decision "
                               "recorded in DECISIONS.md. Silent re-entry is prohibited.",
            "requires_new_evidence": "YES",
            "requires_explicit_resurrection_decision": "YES",
            "status": "DEAD",
        })
    return rows


def venue_cost_rows(venue_rows):
    rows = []
    for venue in venue_rows:
        ref = envelopes.venue_fee_reference(venue)
        ref["bps_conversion_requires_price"] = ref["bps_conversion_requires_price"]
        rows.append(ref)
    return rows


def artifact_hashes(*directories):
    out = {}
    for directory in directories:
        for path in sorted(Path(directory).glob("*.csv")):
            out[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


DEAD_COLUMNS = [
    "candidate_id", "candidate_class", "death_date", "death_date_basis", "kill_gate",
    "report_kill_gate", "cause", "evidence_ids", "resurrection_condition", "re_entry_policy",
    "requires_new_evidence", "requires_explicit_resurrection_decision", "status",
]

GATE_STATUS_COLUMNS = [
    "candidate_id", "candidate_class", "KG1_MECHANISM", "KG2_DATA", "KG3_EXECUTION",
    "KG4_HALF_LIFE", "KG5_FALSIFIABILITY", "overall_status", "status_ceiling",
    "blocking_issue_ids",
]

COVERAGE_COLUMNS = [
    "candidate_id", "consensus_fact_count", "supported_finding_count", "contested_count",
    "extrapolation_count", "unknown_class_count", "supports_count", "weakens_count",
    "neutral_count", "support_evidence_count", "venue_specific_support_count",
    "contrary_evidence_count", "blocking_unknown_count", "evidence_ids",
    "declared_blocking_issue_ids", "derived_blocking_issue_ids",
    "declared_is_subset_of_derived", "derived_not_declared", "note",
]

FEAS_VERDICT_COLUMNS = [
    "candidate_id", "live_feed", "historical_feed", "PIT_reconstructable", "L1_available",
    "L2_available", "L3_available", "queue_replay_possible", "timestamp_adequacy",
    "venue_live_feed_min_interval_us", "candidate_horizon_min_us", "cadence_vs_horizon",
    "depth_source_id", "history_source_id", "PIT_source_id", "timestamp_source_id",
    "feasibility_note", "consistency_note", "unknown_fields",
]

VENUE_COST_COLUMNS = [
    "venue_id", "instrument", "maker_fee_value", "maker_fee_unit", "taker_fee_value",
    "taker_fee_unit", "rebate_value", "rebate_unit", "perp_open_fee_value",
    "perp_open_fee_unit", "perp_close_fee_value", "perp_close_fee_unit",
    "one_way_maker_fee_bps", "one_way_taker_fee_bps", "round_trip_maker_maker_fee_bps",
    "round_trip_maker_taker_fee_bps", "round_trip_taker_taker_fee_bps",
    "round_trip_flat_fee_bps", "bps_conversion_requires_price", "fee_source_ids",
    "unknown_fields",
]

VENUE_COST_NUMERIC = {
    "maker_fee_value": "fee_source_ids",
    "taker_fee_value": "fee_source_ids",
    "rebate_value": "fee_source_ids",
    "perp_open_fee_value": "fee_source_ids",
    "perp_close_fee_value": "fee_source_ids",
    "one_way_maker_fee_bps": "fee_source_ids",
    "one_way_taker_fee_bps": "fee_source_ids",
    "round_trip_maker_maker_fee_bps": "fee_source_ids",
    "round_trip_maker_taker_fee_bps": "fee_source_ids",
    "round_trip_taker_taker_fee_bps": "fee_source_ids",
    "round_trip_flat_fee_bps": "fee_source_ids",
}

LATENCY_COLUMNS = [
    "candidate_id", "horizon_band", "horizon_min_us", "T_total_p50_ms", "T_total_p95_ms",
    "T_total_p99_ms", "measured_components", "half_life_ms", "latency_fit",
    "technology_status", "note", "blocking_issue_ids", "unknown_fields",
]

SURVIVOR_COLUMNS = [
    "candidate_id", "candidate_class", "venue_id", "horizon_band", "mechanism_id",
    "execution_style", "overall_status", "status_ceiling", "passed_hard_constraints",
    "blocking_issue_ids", "why_not_alive",
]

ELIMINATION_COLUMNS = ["candidate_id", "rule", "verdict", "basis", "detail", "source_id"]

DOMINANCE_COLUMNS = [
    "candidate_id", "dominance_status", "pareto_status", "comparable_measured_dimensions",
    "unknown_dimensions", "reason",
]

BLOCKER_COLUMNS = [
    "issue_id", "severity", "resolution_class", "resolution_class_meaning",
    "affected_candidate_count", "affected_candidate_ids", "decision_prevented",
    "specific_evidence_required", "web_research_resolvable", "requires_vendor_quote",
    "requires_m2_measurement", "branch_kill_potential", "linked_open_question_ids", "status",
]

STATUS_REVIEW_COLUMNS = [
    "candidate_id", "candidate_class", "report_status", "status_ceiling",
    "ceiling_permits_status", "status_basis",
]

HYPOTHESES_README = """# M1 hypotheses

No hypothesis is registered here. This directory is empty by design.

M1-D1 is NOT AUTHORIZED (see `M1/output/M1_D1_BLOCKED.md`): no candidate has all five kill
gates PASS, no CURRENT M1-B synthesis artifact exists, and the decision-critical dimensions
are UNKNOWN for every candidate. Generating `H1.md`/`H2.md`/`H3.md` here would manufacture a
shortlist from missing evidence, which the handoff prohibits.

The directory and this note exist so that a future session cannot mistake an empty directory
for an unfinished step.
"""

if __name__ == "__main__":
    raise SystemExit(main())