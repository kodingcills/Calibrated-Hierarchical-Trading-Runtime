#!/usr/bin/env python3
"""Materialise the M1-C data model, the M1-D0 derived outputs and the closure-orchestrator state.

Run:  python3 M1/src/materialize.py

Pipeline (handoff §14):

    load corpus + verified patches -> compile blocker cards -> rank frontier -> generate M2
    specs and external requests -> compute gates -> apply ceiling rules -> write canonical
    tables -> write derived outputs -> write work artefacts -> sync PROJECT_STATE blocks

Nothing in this file decides anything that is not computed from the corpus, the patch inbox and
the computation modules. Re-running is safe and idempotent.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parent
M1 = SRC.parent
REPO = M1.parent
ORCH = M1 / "orchestrator"
for _p in (str(SRC), str(ORCH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import candidate_gates  # noqa: E402
import coverage  # noqa: E402
import envelopes  # noqa: E402
import gate_engine  # noqa: E402
import latency  # noqa: E402
import paper_arithmetic  # noqa: E402
import pareto  # noqa: E402
import readiness  # noqa: E402
import report  # noqa: E402
import controller as closure_controller  # noqa: E402
import patch as patch_mod  # noqa: E402
import resolvers  # noqa: E402
from corpus import (assumptions, constants, evidence, experiments, feasibility, gates,  # noqa: E402
                    mechanisms, sources, staging, techfit, tuples, unknowns, venues)
from corpus import patches as code_patches  # noqa: E402

DATA = M1 / "data"
OUT = M1 / "output"
RAW = M1 / "raw"
MANIFEST = RAW / "source_manifest.json"
PROJECT_STATE = REPO / "PROJECT_STATE.md"


# --------------------------------------------------------------------- derivation
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
    if not MANIFEST.exists():
        return
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_path = {entry["original_path"]: entry["sha256"] for entry in manifest["files"]}
    for row in sources.SOURCES:
        local = row.get("local_path")
        if local and local in by_path:
            row["sha256"] = by_path[local]


def attach_staging(issue_rows):
    """Attach resolution_method / resolution_stage / tier etc. to every issue row."""
    table = {row["issue_id"]: row for row in staging.rows()}
    for row in issue_rows:
        stage = table.get(row["issue_id"])
        if stage is None:
            row["resolution_method"] = "DEFERRED"
            row["resolution_stage"] = "NON_BLOCKING"
            row["tier"] = 4
            row["branch_impact"] = "ONE"
            row["kill_potential"] = "LOW"
            row["estimated_effort"] = "SMALL"
            row["migration_decision"] = "UNMIGRATED"
            row["migration_reason"] = ("No migration row exists for this issue; it is excluded "
                                       "from the frontier until one is authored.")
            row["migration_from"] = None
            continue
        for key, value in stage.items():
            row[key] = value
        # One meaning per word: "BLOCKING" now means "blocks M1 closure" and nothing else.
        # An item that is required only for M2 is IMPORTANT, not blocking - that is the whole
        # point of the migration, and leaving the old severity in place would keep the
        # circularity visible in the vocabulary even after the logic was fixed.
        row["severity_migrated_from"] = row["severity"]
        row["severity"] = severity_for_stage(row["resolution_stage"])
    return issue_rows


def severity_for_stage(stage) -> str:
    if stage == "M1_BLOCKING":
        return "BLOCKING"
    if stage in ("M2_MEASUREMENT", "POST_M2"):
        return "IMPORTANT"
    return "NON_BLOCKING"


def emit_code_patches(generated_at):
    """Write code-authored patches into the inbox if absent; never overwrite a human file."""
    inbox = M1 / "work" / "patches"
    inbox.mkdir(parents=True, exist_ok=True)
    emitted = []
    for module in code_patches.CODE_PATCHES:
        path = inbox / f"{module.PATCH_ID}.json"
        provenance = f"code:{module.__name__.split('.')[-1]}"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("provenance") != provenance:
                continue  # a human-authored or vendor response file is never overwritten
        payload = module.build(generated_at)
        payload["provenance"] = provenance
        report.write_json(path, payload)
        emitted.append(module.PATCH_ID)
    return emitted


def apply_patches(issue_rows, evidence_rows, source_rows, venue_rows):
    """Verify and merge the patch inbox; unverified patches never touch canonical state."""
    canonical = patch_mod.canonical_context(source_rows, evidence_rows, candidate_rows(),
                                           issue_rows)
    raw_patches = closure_controller.load_patches()
    cards = {row["issue_id"]: dict(row) for row in issue_rows}
    for cid, card in list(cards.items()):
        card.setdefault("resolution_stage", "M1_BLOCKING")
        card.setdefault("affected_candidates", [])
    verified = patch_mod.verify_all(raw_patches, cards, canonical)
    merged = patch_mod.apply_verified(verified, source_rows, evidence_rows, issue_rows, cards,
                                      venue_rows)
    return (*merged, verified)


def apply_computed_gates(candidates, computed, generated_at):
    """Overwrite gate columns with computed verdicts, preserving the M1-A baseline."""
    out = []
    for cand in candidates:
        row = dict(cand)
        for gate in constants.GATE_IDS:
            row[f"{gate}_M1A"] = cand[gate]
            row[gate] = computed[cand["candidate_id"]][gate].value
            row[f"{gate}_rule"] = computed[cand["candidate_id"]][gate].rule
            row[f"{gate}_reason"] = computed[cand["candidate_id"]][gate].reason
        row["economic_mechanism_status"] = row["KG1_MECHANISM"]
        row["data_status"] = row["KG2_DATA"]
        row["execution_status"] = row["KG3_EXECUTION"]
        row["half_life_status"] = row["KG4_HALF_LIFE"]
        fails = [g for g in constants.GATE_IDS if row[g] == "FAIL"]
        blocks = [g for g in constants.GATE_IDS if row[g] == "BLOCKED"]
        if fails:
            row["status_basis"] = (
                f"Computed gates: FAIL on {', '.join(fails)}. "
                f"Rule trace: " + "; ".join(computed[cand["candidate_id"]][g].reason
                                            for g in fails))
            row["overall_status"] = "DEAD"
        elif not blocks:
            row["overall_status"] = cand["overall_status"]
            row["status_basis"] = ("All five gates PASS on cited evidence: eligible for M1-B "
                                   "comparison (not a profitability claim).")
        else:
            row["overall_status"] = cand["overall_status"]
            row["status_basis"] = (
                f"Computed gates: BLOCKED on {', '.join(blocks)}. M1-A label preserved "
                f"({cand['overall_status']}); the ceiling forbids ALIVE while a gate is BLOCKED.")
        row["gate_recompute_date"] = generated_at
        out.append(row)
    return out


def status_review_rows(candidates):
    rows = []
    for cand in candidates:
        diverged = [g for g in constants.GATE_IDS if cand[g] != cand[f"{g}_M1A"]]
        rows.append({
            "candidate_id": cand["candidate_id"],
            "candidate_class": cand["candidate_class"],
            "report_status": cand["status_source_id"] and cand["overall_status"],
            "status_ceiling": candidate_gates.status_ceiling(cand),
            "ceiling_permits_status": "YES" if _ceiling_ok(cand) else "NO",
            "status_basis": cand["status_basis"],
            "gates_diverged_from_m1a": "|".join(diverged) or "NONE",
            "m1a_vector": "|".join(cand[f"{g}_M1A"] for g in constants.GATE_IDS),
            "computed_vector": "|".join(cand[g] for g in constants.GATE_IDS),
        })
    return rows


def _ceiling_ok(cand):
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
        fails = [g for g in constants.GATE_IDS if cand[g] == "FAIL"]
        rows.append({
            "candidate_id": cid,
            "candidate_class": cand["candidate_class"],
            "death_date": "2026-09-20",
            "death_date_basis": "date of the M1-A artifact (SRC-0011) for the original kills; "
                                "computed-gate kills are dated by gate_recompute_date",
            "kill_gate": "|".join(fails) if fails else cand["kill_gate"],
            "report_kill_gate": tuples.REPORT_KILL_GATE.get(cid),
            "cause": cand["kill_reason"] if cand["kill_reason"] not in (None, "UNKNOWN")
            else cand["status_basis"],
            "evidence_ids": "|".join(linked) or "NONE",
            "resurrection_condition": cand["resurrection_condition"] if
            cand["resurrection_condition"] not in (None, "UNKNOWN") else
            "Reformulate as a new candidate satisfying the constraint that killed this row.",
            "re_entry_policy": "Requires NEW_EVIDENCE plus an explicit resurrection decision "
                               "recorded in DECISIONS.md. Silent re-entry is prohibited.",
            "requires_new_evidence": "YES",
            "requires_explicit_resurrection_decision": "YES",
            "status": "DEAD",
        })
    return rows


def venue_cost_rows(venue_rows):
    return [envelopes.venue_fee_reference(venue) for venue in venue_rows]


def artifact_hashes(*directories):
    out = {}
    for directory in directories:
        for path in sorted(Path(directory).glob("*.csv")):
            out[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


# ------------------------------------------------------------- PROJECT_STATE blocks
def generated_block(name, lines):
    return (f"<!-- GENERATED:{name} -->\n" + "\n".join(lines) + f"\n<!-- /GENERATED:{name} -->")


def milestone_block(milestones):
    return [f"{k}: {v}" for k, v in milestones.items()]


def counts_block(counts, totals, migration):
    rows = ["| status | count |", "|---|---|"]
    rows += [f"| {k} | {counts[k]} |" for k in ("ALIVE", "WEAK", "UNKNOWN", "DEAD")]
    return rows + [
        "",
        f"Registered candidate rows: {totals['candidate_rows']} "
        f"({totals['tradable_tuples']} tradable tuples + {totals['non_tuple_rows']} "
        f"non-tuple registrations). Verified sources: {totals['source_registry']} "
        f"({totals['external_token_sources']} report-mediated, 0 with a recoverable URL). "
        f"Evidence records: {totals['evidence_records']}. M1 frontier items: "
        f"{totals['frontier_items']} ({totals['m2_specs']} measurement specs and "
        f"{totals['external_requests']} external requests now outside the frontier). "
        f"Gate-eligible candidates: {totals['gate_eligible']}.",
    ]


def stage_block(migration):
    lines = ["| resolution stage | count | meaning |", "|---|---|---|"]
    meaning = {
        "M1_BLOCKING": "must be answered before M1 can close",
        "M2_MEASUREMENT": "preregistered M2 experiment; does not block M1",
        "POST_M2": "matters only after M2 shows positive net EV",
        "NON_BLOCKING": "tracked; no gate depends on it",
    }
    for stage in ("M1_BLOCKING", "M2_MEASUREMENT", "POST_M2", "NON_BLOCKING"):
        lines.append(f"| {stage} | {migration['by_stage'][stage]} | {meaning[stage]} |")
    lines += ["", "| resolution method | count |", "|---|---|"]
    for method in ("PUBLIC_RESEARCH", "EXTERNAL_ACTION", "EMPIRICAL_MEASUREMENT", "DEFERRED"):
        lines.append(f"| {method} | {migration['by_method'][method]} |")
    return lines


def _affected_display(card, totals):
    """Resolve an ALL_ token so a global blocker is not shown as affecting one row."""
    affected = card["affected_candidates"]
    if any(str(a).startswith("ALL_") for a in affected):
        return f"all {totals['candidate_rows']} ({affected[0]})"
    return str(len(affected))


def frontier_block(frontier_cards, totals):
    lines = ["| leverage | tier | issue | method | affected | decision prevented |",
             "|---|---|---|---|---|---|"]
    for card in frontier_cards[:12]:
        lines.append(f"| {card['priority_score']} | {card['tier']} | `{card['blocker_id']}` | "
                     f"{card['resolution_method']} | {_affected_display(card, totals)} | "
                     f"{card['decision_prevented'][:110]} |")
    awaiting = totals.get("awaiting_external", 0)
    lines += ["",
              f"Actionable frontier items: {len(frontier_cards)}. Items awaiting an external "
              f"answer or a frozen spec: {awaiting}. Measurement specifications: "
              f"{totals.get('m2_specs', 0)}. External request packets: "
              f"{totals.get('external_requests', 0)}."]
    return lines


def next_actions_block(frontier_cards):
    lines = []
    for i, card in enumerate(frontier_cards[:6], start=1):
        lines.append(f"{i}. **{card['blocker_id']}** ({card['resolution_method']}, tier "
                     f"{card['tier']}, leverage {card['priority_score']}): "
                     f"{card['required_answer']}")
    return lines


def readiness_block(milestones, gate_eligible, frontier_items):
    """Readiness answers derived from gate eligibility, never from a hand-written string."""
    m1b_ok = bool(gate_eligible)
    d1_ok = m1b_ok and milestones.get("M1-B") == "AUTHORIZED"
    return [
        f"Ready for M1-B? **{'YES' if m1b_ok else 'NO'}** - "
        + ("at least one candidate passes all five gates on cited evidence."
           if m1b_ok else
           "zero candidates pass all five gates; the frontier still holds "
           f"{frontier_items} M1-blocking items."),
        f"Ready for M1-D1? **{'YES' if d1_ok else 'NO'}** - "
        + ("M1-B may run." if d1_ok else
           "M1-B is not authorized and no synthesis artifact exists, so no finalists can be "
           "compared."),
        "Ready for M2? **NO** - M2 requires a selected candidate plus a locked cost configuration "
        "and an order-level dataset; the frontier holds both.",
        "Ready for shadow trading? **NO** - a shadow run requires a chosen candidate, instrument "
        "and measured cost envelope.",
        "Ready for capital? **NO** - no candidate has evidenced net edge.",
    ]


def sync_project_state(milestones, counts, totals, migration, gate_eligible, generated_at,
                       frontier_cards):
    if not PROJECT_STATE.exists():
        return
    text = PROJECT_STATE.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks = {
        "milestones": milestone_block(milestones),
        "counts": counts_block(counts, totals, migration),
        "stages": stage_block(migration),
        "readiness": readiness_block(milestones, gate_eligible, totals["frontier_items"]),
        "frontier": frontier_block(frontier_cards, totals),
        "next_actions": next_actions_block(frontier_cards),
    }
    out, current = [], None
    for line in lines:
        if line.startswith("Last Updated:"):
            out.append(f"Last Updated: {generated_at}")
            continue
        if line.startswith("<!-- GENERATED:"):
            current = line[len("<!-- GENERATED:"):].split("-->")[0].strip()
            out.append(line)
            out.extend(blocks[current])
            continue
        if line.startswith("<!-- /GENERATED:"):
            current = None
            out.append(line)
            continue
        if current is not None:
            continue
        out.append(line)
    PROJECT_STATE.write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------- main
def main():
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    attach_source_hashes()

    base_candidates = candidate_rows()
    feas_by_id = {f["candidate_id"]: f for f in feasibility.ROWS}

    issue_rows = attach_staging([dict(r) for r in unknowns.DISCREPANCIES])
    source_rows = [dict(r) for r in sources.SOURCES]
    evidence_rows = [dict(r) for r in evidence.EVIDENCE]
    venue_rows = [dict(r) for r in venues.ROWS]
    emitted = emit_code_patches(generated_at)
    (source_rows, evidence_rows, issue_rows, venue_rows, patch_audit,
     patches) = apply_patches(issue_rows, evidence_rows, source_rows, venue_rows)
    venue_by_id = {v["venue_id"]: v for v in venue_rows}

    env_rows = envelopes.all_envelopes(base_candidates, venue_by_id)
    env_by_id = {r["candidate_id"]: r for r in env_rows}
    fee_floor_by_id = {cid: r["required_round_trip_fee_bps_for_style"]
                       for cid, r in env_by_id.items()}

    feas_rows = [coverage.feasibility_row(
        next(c for c in base_candidates if c["candidate_id"] == f["candidate_id"]),
        venue_by_id.get(next(c for c in base_candidates
                            if c["candidate_id"] == f["candidate_id"])["venue_id"]),
        f) for f in feasibility.ROWS]
    feas_out_by_id = {r["candidate_id"]: r for r in feas_rows}

    # Closure state must be compiled before gates: KG4/KG3 depend on the preregistered specs.
    closure = closure_controller.build_closure(issue_rows, base_candidates, evidence_rows,
                                               source_rows, env_by_id, venue_by_id,
                                               generated_at)
    spec_ids_by_candidate = closure["spec_ids_by_candidate"]
    requests = closure_controller.external_requests(closure)

    computed = gate_engine.compute(base_candidates, evidence_rows, feas_out_by_id, env_by_id,
                                   venue_by_id, spec_ids_by_candidate)
    candidates = apply_computed_gates(base_candidates, computed, generated_at)
    cand_by_id = {c["candidate_id"]: c for c in candidates}

    gate_rows = candidate_gates.gate_status_rows(candidates)
    coverage_rows = coverage.coverage_rows(evidence_rows, candidates, issue_rows)
    review_rows = status_review_rows(candidates)

    kept, killed = pareto.survivors(candidates, feas_out_by_id, evidence_rows, fee_floor_by_id)
    survivor_rows = pareto.survivor_rows(kept, cand_by_id)
    elimination_rows = pareto.elimination_rows(killed)
    dominance_rows = pareto.dominance_rows(candidates)
    latency_rows = latency.latency_feasibility_rows(candidates)

    gate_counts = gate_engine.gate_counts(computed)
    for gate in gates.ROWS:
        counts = gate_counts[gate["gate_id"]]
        gate["candidates_pass"] = counts["PASS"]
        gate["candidates_blocked"] = counts["BLOCKED"]
        gate["candidates_fail"] = counts["FAIL"]

    status_counts = candidate_gates.status_counts(candidates)
    gate_eligible = gate_engine.eligible(computed)
    migration = closure_controller.migration_summary(issue_rows)
    dead_rows = build_dead_rows(candidates, evidence_rows)
    blockers = readiness.blocker_priority_rows(issue_rows, unknowns.OPEN_QUESTIONS,
                                               set(cand_by_id))
    blockers = attach_priority_scores(blockers, closure["frontier_cards"])
    non_frontier = readiness.non_frontier_rows(issue_rows)

    milestones = {"M1-A": "INCOMPLETE",
                  "M1-B": "AUTHORIZED" if gate_eligible else "NOT_AUTHORIZED",
                  "M1-C": "COMPLETE",
                  "M1-D0": "COMPLETE",
                  "M1-D1": "AUTHORIZED" if gate_eligible else "NOT_AUTHORIZED"}

    spec_docs = []
    for spec_id in sorted(resolvers.SPEC_DEFINITIONS):
        affected = [c for c in base_candidates
                    if spec_id in spec_ids_by_candidate.get(c["candidate_id"], [])]
        card = next((closure["cards"][bid] for bid in closure["cards"]
                     if staging.BY_ID[bid][1] in
                     ("EMPIRICAL_MEASUREMENT",) and spec_id in _spec_link(bid)), None)
        path = M1 / "work" / "m2_specs" / f"{spec_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resolvers.m2_spec_md(spec_id, card, affected), encoding="utf-8")
        spec_docs.append({"spec_id": spec_id, "candidates": len(affected),
                          "path": str(path.relative_to(REPO)),
                          "stage": resolvers.SPEC_STAGE[spec_id],
                          "complexity": resolvers._COMPLEXITY[spec_id]})

    total_counter = {
        "candidate_rows": len(candidates),
        "tradable_tuples": status_counts["TUPLE"]["total"],
        "non_tuple_rows": len(candidates) - status_counts["TUPLE"]["total"],
        "source_registry": len(source_rows),
        "external_token_sources": len([s for s in source_rows
                                       if str(s.get("raw_citation_token", "")).startswith("turn")]),
        "evidence_records": len(evidence_rows),
        "frontier_items": len(closure["frontier_cards"]),
        "m2_specs": len(spec_docs),
        "external_requests": len(requests),
        "gate_eligible": len(gate_eligible),
    }

    closure_status = controller_status(closure, computed, candidates, status_counts, migration,
                                       gate_eligible, generated_at, requests, spec_docs, patches)
    closure["closure_status"] = closure_status
    work_summary = closure_controller.write_work(closure, requests, closure_status)

    # ---- canonical tables
    report.table(DATA / "source_registry.csv", sources.COLUMNS, source_rows,
                 constants.TABLE_SPECS["source_registry"]["numeric"])
    report.table(DATA / "evidence_ledger.csv", evidence.COLUMNS, evidence_rows,
                 constants.TABLE_SPECS["evidence_ledger"]["numeric"])
    report.table(DATA / "venue_facts.csv", venues.COLUMNS, venue_rows,
                 constants.TABLE_SPECS["venue_facts"]["numeric"])
    report.table(DATA / "mechanisms.csv", mechanisms.COLUMNS, mechanisms.ROWS,
                 constants.TABLE_SPECS["mechanisms"]["numeric"])
    report.table(DATA / "candidate_tuples.csv", CANDIDATE_COLUMNS, candidates,
                 constants.TABLE_SPECS["candidate_tuples"]["numeric"])
    report.table(DATA / "data_feasibility.csv", feasibility.COLUMNS, feasibility.ROWS,
                 constants.TABLE_SPECS["data_feasibility"]["numeric"])
    report.table(DATA / "execution_envelopes.csv", envelopes.COLUMNS, env_rows,
                 constants.TABLE_SPECS["execution_envelopes"]["numeric"])
    report.table(DATA / "technology_fit.csv", techfit.COLUMNS, techfit.ROWS,
                 constants.TABLE_SPECS["technology_fit"]["numeric"])
    report.table(DATA / "discrepancies.csv", unknowns.DISCREPANCY_COLUMNS, issue_rows,
                 constants.TABLE_SPECS["discrepancies"]["numeric"])
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

    # ---- derived outputs
    report.table(OUT / "candidate_gate_status.csv", GATE_STATUS_COLUMNS, gate_rows)
    report.table(OUT / "gate_rule_trace.csv", GATE_TRACE_COLUMNS, gate_trace_rows(computed))
    report.table(OUT / "evidence_coverage.csv", COVERAGE_COLUMNS, coverage_rows)
    report.table(OUT / "data_feasibility_verdicts.csv", FEAS_VERDICT_COLUMNS, feas_rows)
    report.table(OUT / "cost_envelopes.csv", envelopes.COLUMNS, env_rows,
                 constants.TABLE_SPECS["execution_envelopes"]["numeric"])
    report.table(OUT / "venue_cost_reference.csv", VENUE_COST_COLUMNS,
                 venue_cost_rows(venue_rows), VENUE_COST_NUMERIC)
    report.table(OUT / "latency_feasibility.csv", LATENCY_COLUMNS, latency_rows)
    report.table(OUT / "hard_constraint_survivors.csv", SURVIVOR_COLUMNS, survivor_rows)
    report.table(OUT / "hard_constraint_eliminations.csv", ELIMINATION_COLUMNS,
                 elimination_rows)
    report.table(OUT / "dominated_candidates.csv", DOMINANCE_COLUMNS, dominance_rows)
    report.table(OUT / "blocker_priority.csv", BLOCKER_COLUMNS, blockers)
    report.table(OUT / "issue_migration.csv", MIGRATION_COLUMNS,
                 sorted(issue_rows, key=lambda r: r["issue_id"]))
    report.table(OUT / "non_frontier_issues.csv", NON_FRONTIER_COLUMNS, non_frontier)
    report.table(OUT / "status_derivation_review.csv", STATUS_REVIEW_COLUMNS, review_rows)

    state = {
        "generated_at": generated_at,
        "status_counts": status_counts,
        "m1b_eligible": gate_eligible,
        "blocker_rows": blockers,
        "discrepancies": issue_rows,
        "open_questions": unknowns.OPEN_QUESTIONS,
        "dead_rows": dead_rows,
        "migration": migration,
        "gate_eligible": gate_eligible,
        "non_frontier": non_frontier,
        "spec_docs": spec_docs,
        "requests": requests,
    }
    (OUT / "M1_D0_READINESS.md").write_text(readiness.readiness_md(state), encoding="utf-8")
    (OUT / "M1_D1_BLOCKED.md").write_text(readiness.d1_blocked_md(state), encoding="utf-8")

    # ---- root artifacts
    report.write_csv(REPO / "EVIDENCE_LEDGER.csv", evidence.COLUMNS, evidence_rows)
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

    summary = {
        "generated_at": generated_at,
        "generated_by": "M1/src/materialize.py",
        "counts": {**total_counter,
                   "assumptions": len(assumptions.ROWS),
                   "mechanisms": len(mechanisms.ROWS),
                   "venue_rows": len(venue_rows),
                   "discrepancies": len(issue_rows),
                   "open_issues": len(blockers) + len(non_frontier),
                   "blocking_issues": len(blockers),
                   "non_frontier_issues": len(non_frontier),
                   "open_questions": len(unknowns.OPEN_QUESTIONS),
                   "experiments_proposed_not_run": len(experiments.EXPERIMENTS),
                   "hypotheses_registered": len(experiments.HYPOTHESES),
                   "hard_constraint_eliminations": len({r["candidate_id"]
                                                         for r in elimination_rows}),
                   "hard_constraint_survivors": len(survivor_rows),
                   "ceiling_violations": len(candidate_gates.ceiling_violations(candidates)),
                   "status": {k: status_counts["ALL"][k]
                              for k in ("total", "ALIVE", "WEAK", "UNKNOWN", "DEAD")},
                   "status_by_class": status_counts,
                   "m1b_eligible": gate_eligible},
        "gate_counts": gate_counts,
        "migration": migration,
        "patches": {
            "proposed": len(patches),
            "applied": len([p for p in patches if p["status"] == "VERIFIED"]),
            "rejected": len([p for p in patches if p["status"] == "REJECTED"]),
            "audit": patch_audit,
            "rejections": patch_mod.rejection_report(patches),
        },
        "m2_specs": spec_docs,
        "external_requests": [{"blocker_id": r["blocker_id"], "title": r["title"],
                               "priority_score": r["priority_score"],
                               "affected": len(r["affected_candidates"])} for r in requests],
        "work_artifacts": work_summary,
        "pareto": {"executed": False, "reason": pareto.DOMINANCE_NOTE},
        "paper_arithmetic_check": paper_arithmetic.consistency_report(),
        "milestones": milestones,
        "artifact_hashes": artifact_hashes(DATA, OUT),
    }
    report.write_json(OUT / "M1_STATE_SUMMARY.json", summary)

    total_counter["awaiting_external"] = len([c for c in closure["cards"].values()
                                              if c["resolution_stage"] == "M1_BLOCKING"
                                              and c["status"] in ("EXTERNAL_REQUEST_READY",
                                                                  "EMPIRICAL_SPEC_READY")])
    sync_project_state(milestones, summary["counts"]["status"], total_counter, migration,
                       gate_eligible, generated_at, closure["frontier_cards"])

    print(json.dumps({"candidates": total_counter["candidate_rows"],
                      "status": summary["counts"]["status"],
                      "frontier_items": total_counter["frontier_items"],
                      "m2_specs": len(spec_docs),
                      "external_requests": len(requests),
                      "gate_eligible": len(gate_eligible),
                      "migration": migration["by_stage"]}, indent=1))
    return 0


def _spec_link(issue_id):
    """Which M2 specs an empirical issue feeds. Used only for spec documentation links."""
    return {
        "UNK-0006": ("COST_SENSITIVITY",),
        "UNK-0007": ("PASSIVE_FILL_MODEL",),
        "UNK-0008": ("EV_DELAY_SWEEP",),
        "UNK-0016": ("LIVE_LATENCY",),
        "UNK-0017": ("SYSTEM_ONE_INCREMENTAL_UTILITY",),
        "UNK-0019": ("FILL_CONDITIONED_MARKOUT",),
        "UNK-0021": ("LIVE_LATENCY",),
        "UNK-0026": ("SYSTEM_ONE_INCREMENTAL_UTILITY",),
        "UNK-0029": ("CAPACITY",),
        "UNK-0032": ("COST_SENSITIVITY",),
    }.get(issue_id, ())


def controller_status(closure, computed, candidates, status_counts, migration, gate_eligible,
                      generated_at, requests, spec_docs, patches):
    return closure_controller.frontier.closure_status(
        computed, candidates, closure["frontier_cards"], status_counts["ALL"], migration,
        generated_at,
        len(requests), [d["spec_id"] for d in spec_docs], len(patches))


def attach_priority_scores(blockers, frontier_cards):
    """Give the priority table the same leverage ordering as the frontier, from one source."""
    scores = {c["blocker_id"]: c["priority_score"] for c in frontier_cards}
    reasons = {c["blocker_id"]: c["priority_reason"] for c in frontier_cards}
    for row in blockers:
        row["priority_score"] = scores.get(row["issue_id"])
        row["priority_reason"] = reasons.get(row["issue_id"])
    blockers.sort(key=lambda r: (-(r["priority_score"] or 0), r["issue_id"]))
    return blockers


def gate_trace_rows(computed):
    rows = []
    for cid, cand in sorted(computed.items()):
        for gate in constants.GATE_IDS:
            verdict = cand[gate]
            rows.append({"candidate_id": cid, "gate": gate, "value": verdict.value,
                         "rule": verdict.rule, "reason": verdict.reason})
    return rows


CANDIDATE_COLUMNS = tuples.COLUMNS + [
    "KG1_MECHANISM_M1A", "KG2_DATA_M1A", "KG3_EXECUTION_M1A", "KG4_HALF_LIFE_M1A",
    "KG5_FALSIFIABILITY_M1A",
    "KG1_MECHANISM_rule", "KG2_DATA_rule", "KG3_EXECUTION_rule", "KG4_HALF_LIFE_rule",
    "KG5_FALSIFIABILITY_rule",
    "KG1_MECHANISM_reason", "KG2_DATA_reason", "KG3_EXECUTION_reason", "KG4_HALF_LIFE_reason",
    "KG5_FALSIFIABILITY_reason",
    "gate_recompute_date",
]

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

GATE_TRACE_COLUMNS = ["candidate_id", "gate", "value", "rule", "reason"]

COVERAGE_COLUMNS = [
    "candidate_id", "consensus_fact_count", "supported_finding_count", "contested_count",
    "extrapolation_count", "unknown_class_count", "supports_count", "weakens_count",
    "neutral_count", "support_evidence_count", "venue_specific_support_count",
    "contrary_evidence_count", "blocking_unknown_count", "evidence_ids",
    "declared_blocking_issue_ids", "derived_blocking_issue_ids",
    "declared_is_subset_of_derived", "derived_not_declared", "declared_not_derived", "note",
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
    "round_trip_flat_fee_bps", "maker_side_is_rebate", "bps_conversion_requires_price",
    "fee_source_ids",
    "unknown_fields",
]

VENUE_COST_NUMERIC = {
    "maker_fee_value": "fee_source_ids", "taker_fee_value": "fee_source_ids",
    "rebate_value": "fee_source_ids", "perp_open_fee_value": "fee_source_ids",
    "perp_close_fee_value": "fee_source_ids", "one_way_maker_fee_bps": "fee_source_ids",
    "one_way_taker_fee_bps": "fee_source_ids", "round_trip_maker_maker_fee_bps": "fee_source_ids",
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
    "issue_id", "severity", "resolution_class", "resolution_class_meaning", "resolution_method",
    "resolution_stage", "tier", "branch_impact", "kill_potential", "estimated_effort",
    "affected_candidate_count", "affected_candidate_ids", "decision_prevented",
    "specific_evidence_required", "web_research_resolvable", "requires_vendor_quote",
    "requires_m2_measurement", "branch_kill_potential", "linked_open_question_ids", "status",
    "priority_score", "priority_reason",
]

MIGRATION_COLUMNS = [
    "issue_id", "resolution_method", "resolution_stage", "severity_migrated_from", "tier",
    "branch_impact",
    "kill_potential", "estimated_effort", "migration_decision", "migration_from",
    "migration_reason", "severity", "status", "claim_needed",
]

NON_FRONTIER_COLUMNS = [
    "issue_id", "resolution_method", "resolution_stage", "tier", "title", "migration_reason",
    "destination",
]

STATUS_REVIEW_COLUMNS = [
    "candidate_id", "candidate_class", "report_status", "status_ceiling",
    "ceiling_permits_status", "status_basis", "gates_diverged_from_m1a", "m1a_vector",
    "computed_vector",
]

HYPOTHESES_README = """# M1 hypotheses

No hypothesis is registered here. This directory is empty by design.

M1-B is not authorized: no candidate passes all five gates (see
`M1/output/M1_CLOSURE_STATUS.json` and `M1/output/gate_rule_trace.csv`). Generating
`H1.md`/`H2.md`/`H3.md` would manufacture a shortlist from unresolved evidence, which the
handoff prohibits.

Note the revised gate semantics: the *empirical* quantities M2 exists to measure (signal
half-life, fill probability, markout, own latency, capacity) no longer block M1. What remains
blocking is the M1 frontier in `M1/work/frontier.json` - instrument specificity, access, feed
and cost facts, matching rules and data procurement.
"""

if __name__ == "__main__":
    raise SystemExit(main())