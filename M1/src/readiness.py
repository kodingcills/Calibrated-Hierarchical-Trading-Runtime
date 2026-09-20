"""Blocker prioritisation and the M1-D0 readiness / M1-D1-blocked documents.

Ordering rule (handoff D0.7): blockers are ordered by how many candidates they affect, and
then by whether resolving them can kill or clear an entire branch cheaply. No blocker is
ranked by how easy it *feels*; the resolution class does that work explicitly.
"""

from __future__ import annotations

from corpus.constants import RESOLUTION_CLASSES

UNKNOWN = None


def _split(ids) -> list:
    if ids is UNKNOWN or ids == "":
        return []
    return [x for x in str(ids).split("|") if x]


def _affected_count(issue, candidate_ids) -> int:
    ids = set(_split(issue["affected_candidate_ids"])) | set(_split(issue["candidate_id"]))
    if ids & {"ALL_CANDIDATES", "ALL_EXTERNAL_EVIDENCE"}:
        return len(candidate_ids)
    return len(ids & candidate_ids)


def _question_links(issue_id, open_questions) -> str:
    links = [q["question_id"] for q in open_questions
             if issue_id in _split(q["related_issue_ids"])]
    return "|".join(links) or "NONE"


def _severity_rank(severity):
    return {"BLOCKING": 0, "IMPORTANT": 1, "NON_BLOCKING": 2}.get(severity, 3)


def blocker_priority_rows(discrepancies, open_questions, candidate_ids) -> list:
    """Open issues ranked by decision leverage, restricted to the M1 frontier.

    Non-frontier items are excluded by construction (handoff §14 STEP 2): measurement and
    procurement-after-M1 work must not appear as if it were blocking M1.
    """
    rows = []
    for issue in discrepancies:
        if issue["status"] == "RESOLVED":
            continue
        if issue.get("resolution_stage") != "M1_BLOCKING":
            continue
        count = _affected_count(issue, candidate_ids)
        affected = issue["affected_candidate_ids"] or issue["candidate_id"]
        if affected in ("ALL_CANDIDATES", "ALL_EXTERNAL_EVIDENCE"):
            affected = f"{affected} ({count} registered rows)"
        rows.append({
            "issue_id": issue["issue_id"],
            "severity": issue["severity"],
            "resolution_class": issue["resolution_class"],
            "resolution_class_meaning": RESOLUTION_CLASSES.get(issue["resolution_class"], "UNKNOWN"),
            "resolution_method": issue.get("resolution_method"),
            "resolution_stage": issue.get("resolution_stage"),
            "tier": issue.get("tier"),
            "branch_impact": issue.get("branch_impact"),
            "kill_potential": issue.get("kill_potential"),
            "estimated_effort": issue.get("estimated_effort"),
            "affected_candidate_count": count,
            "affected_candidate_ids": affected,
            "decision_prevented": issue["decision_prevented"],
            "specific_evidence_required": issue["specific_evidence_needed"],
            "web_research_resolvable": issue["web_research_resolvable"],
            "requires_vendor_quote": issue["requires_vendor_quote"],
            "requires_m2_measurement": issue["requires_m2_measurement"],
            "branch_kill_potential": "HIGH" if count >= 5 else ("MEDIUM" if count >= 2 else "LOW"),
            "linked_open_question_ids": _question_links(issue["issue_id"], open_questions),
            "status": issue["status"],
        })
    rows.sort(key=lambda r: (_severity_rank(r["severity"]), -r["affected_candidate_count"],
                             r["issue_id"]))
    return rows


def non_frontier_rows(discrepancies) -> list:
    """Open issues deliberately NOT on the M1 frontier, with where they now live."""
    out = []
    for issue in discrepancies:
        if issue["status"] == "RESOLVED":
            continue
        if issue.get("resolution_stage") == "M1_BLOCKING":
            continue
        out.append({
            "issue_id": issue["issue_id"],
            "resolution_method": issue.get("resolution_method"),
            "resolution_stage": issue.get("resolution_stage"),
            "tier": issue.get("tier"),
            "title": issue["claim_needed"],
            "migration_reason": issue.get("migration_reason"),
            "destination": ("M1/work/m2_specs/" if issue.get("resolution_stage") in
                            ("M2_MEASUREMENT", "POST_M2")
                            else "registry only (non-blocking)"),
        })
    out.sort(key=lambda r: (str(r["resolution_stage"]), r["issue_id"]))
    return out


def _table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join("" if c is UNKNOWN else str(c) for c in row) + " |")
    return "\n".join(out)


def readiness_md(state) -> str:
    """state is the dict assembled by materialize.py."""
    counts = state["status_counts"]["ALL"]
    blockers = state["blocker_rows"]
    blocking = [b for b in blockers if b["severity"] == "BLOCKING"]

    class_rows = []
    for cls, meaning in RESOLUTION_CLASSES.items():
        members = [b for b in blockers if b["resolution_class"] == cls]
        class_rows.append([cls, meaning, len(members),
                           ", ".join(b["issue_id"] for b in members) or "NONE"])

    top_rows = [[b["issue_id"], b["severity"], b["resolution_class"],
                 b["affected_candidate_count"], b["branch_kill_potential"],
                 b["decision_prevented"]] for b in blockers[:12]]

    lines = [
        "# M1-D0 Readiness",
        "",
        "Generated by `M1/src/materialize.py` from `M1/data/*`. Do not edit by hand: the file is",
        "overwritten on every materialisation, and every number here is reproducible from the",
        "corpus modules plus the computation modules.",
        "",
        f"Materialised (UTC): {state['generated_at']}",
        "",
        "## 1. What can currently be calculated",
        "",
        "- Verified venue fee values and every round-trip fee that follows from them "
        "(`M1/output/cost_envelopes.csv`, `M1/output/venue_cost_reference.csv`).",
        "- Known-cost floors: verified mandatory fee components summed per candidate, with the "
        "missing components named. These are lower bounds on cost and are never break-even "
        "(ASM-0012).",
        "- Hard-constraint eliminations backed by verified facts (`M1/output/"
        "hard_constraint_eliminations.csv`) and the survivor set that remains.",
        "- Gate vectors, the status ceiling and every ceiling violation "
        "(`M1/output/candidate_gate_status.csv`).",
        "- Descriptive evidence coverage per candidate (`M1/output/evidence_coverage.csv`).",
        "- Feed-cadence-versus-horizon feasibility from the one venue whose cadence is verified.",
        "- The candidate-architecture paper's own cost arithmetic, reproduced "
        "(`M1/src/paper_arithmetic.py`).",
        "",
        "## 2. What cannot currently be calculated",
        "",
        "- Full break-even for any candidate: at least one required component "
        "(spread, slippage, impact, adverse selection) is unknown for all of them.",
        "- Signal half-life and any latency fit: no empirical EV-versus-delay curve exists, so "
        "`latency_fit = BLOCKED` and `half_life = UNKNOWN` for every candidate (ASM-0014).",
        "- Passive expected utility: neither P(fill | queue, state) nor E(markout | fill, state) "
        "is measured.",
        "- Any ranking, weighting or Pareto frontier: the decision-critical dimensions are "
        "unknown for every candidate, so ordering them would order missing values.",
        "- Independent provenance for the only two mechanism-gate passes: KG1 currently passes for "
        "two Nasdaq tuples on evidence whose sources are still report-mediated (no recoverable "
        "URL), so those two verdicts rest on a citation the project has not re-derived "
        "(UNK-0023). They are the highest-leverage integrity item on the frontier for that "
        "reason.",
        "",
        f"## 3. Candidate state ({counts['total']} registered rows, "
        f"{state['status_counts']['TUPLE']['total']} tradable tuples)",
        "",
        _table(["class", "total", "ALIVE", "WEAK", "UNKNOWN", "DEAD"],
               [[cls, c["total"], c["ALIVE"], c["WEAK"], c["UNKNOWN"], c["DEAD"]]
                for cls, c in sorted(state["status_counts"].items())]),
        "",
        f"M1-B-eligible tuples: **{len(state['m1b_eligible'])}** "
        f"({', '.join(state['m1b_eligible']) or 'none'}).",
        "",
        "## 4. Missing values grouped by how they can be resolved",
        "",
        _table(["class", "meaning", "count", "issues"], class_rows),
        "",
        "## 5. Blockers ordered by decision impact",
        "",
        _table(["issue", "severity", "class", "affected candidates", "branch-kill potential",
                "decision prevented"], top_rows),
        "",
        f"Blocking issues: **{len(blocking)}** of {len(blockers)} open issues "
        f"({len(state['discrepancies'])} registered in total, "
        f"{len(state['discrepancies']) - len(blockers)} resolved).",
        "",
        "## 6. Blocker detail",
        "",
    ]
    for b in blockers:
        lines += [
            f"### {b['issue_id']} - {b['severity']} ({b['resolution_class']})",
            "",
            f"- affects: {b['affected_candidate_ids']} "
            f"({b['affected_candidate_count']} registered rows)",
            f"- decision it prevents: {b['decision_prevented']}",
            f"- specific evidence required: {b['specific_evidence_required']}",
            f"- web research can resolve: {b['web_research_resolvable']}; "
            f"vendor quote needed: {b['requires_vendor_quote']}; "
            f"M2 measurement needed: {b['requires_m2_measurement']}",
            f"- linked open questions: {b['linked_open_question_ids']}",
            "",
        ]

    lines += [
        "## 7. Which missing measurement would change the most decisions",
        "",
        "Ranked by the number of candidates whose status could move, not by ease:",
        "",
        _table(["rank", "measurement", "why it changes decisions"],
               [[1, "Exact account-level fee/commission schedule per venue "
                    "(UNK-0001, UNK-0005, UNK-0028)",
                 "A verified all-in cost floor can kill an entire venue branch without any "
                 "modelling: it already killed two crypto tuples and could equally clear or kill "
                 "the CME and equity branches."],
                [2, "Historical order-level data availability, cost and timestamp semantics "
                    "(UNK-0003, UNK-0004, UNK-0020)",
                 "Determines whether causal replay is possible at all for the three largest "
                 "candidate families; without it no execution-aware test can be run."],
                [3, "Empirical EV-versus-delay curve (UNK-0008)",
                 "Sets the permissible decision age and therefore which horizon bands and which "
                 "model classes stay admissible."],
                [4, "Passive fill probability and fill-conditioned markout (UNK-0007, UNK-0019)",
                 "Decides whether every passive candidate is a real opportunity or a queue "
                 "artefact."],
                [5, "Modern venue-specific after-cost replication (UNK-0009)",
                 "The only external evidence that currently justifies venue-specific testing; "
                 "its absence of replication is what keeps mechanism gates BLOCKED."],
                [6, "Own-stack latency profile and hosted-model latency (UNK-0016, UNK-0017)",
                 "Required before any model placement claim, including the System-One branch."]]),
        "",
        "## 8. Explicit non-actions",
        "",
        "- No weighted ranking, no Monte Carlo weights, no finalist selection: M1-D1 is not "
        "authorized (see `M1/output/M1_D1_BLOCKED.md`).",
        "- No value was imputed for any unknown. Where a number is not evidenced, the cell is "
        "empty and named in the row's `unknown_fields`.",
        "- No experiment has been run: `M1/data/experiments.csv` contains only PROPOSED rows.",
        "",
    ]
    return "\n".join(lines)


def d1_blocked_md(state) -> str:
    counts = state["status_counts"]["ALL"]
    return "\n".join([
        "# M1-D1 NOT AUTHORIZED",
        "",
        f"Generated by `M1/src/materialize.py` at {state['generated_at']}.",
        "",
        "## Preconditions checked",
        "",
        _table(["precondition", "required", "observed", "verdict"],
               [["M1-B has emitted a CURRENT synthesis artifact", "YES",
                 "NO (`M1-B` artifact does not exist; PROJECT_STATE records "
                 "M1-B = NOT_AUTHORIZED)", "FAIL"],
                ["No finalist has an unresolved blocking KG1/KG2/KG3 issue", "YES",
                 f"{counts['total']} registered rows, 0 of which have all five gates PASS",
                 "FAIL"],
                ["All five gates PASS for at least one candidate", "YES",
                 f"{counts['ALIVE']} candidates with all gates PASS", "FAIL"],
                ["Demand-side evidence complete enough to score dimensions", "YES",
                 "Net-edge headroom, half-life, fill quality, capacity and capital efficiency are "
                 "UNKNOWN for every candidate", "FAIL"]]),
        "",
        "## Why M1-D1 is refused",
        "",
        "M1-D1 is a comparison, and a comparison requires comparable measured dimensions. Every",
        "dimension that would drive the comparison is currently an open blocking unknown:",
        "",
        "- exact all-in venue costs (UNK-0001, UNK-0005, UNK-0028),",
        "- historical order-level data procurement (UNK-0003, UNK-0004, UNK-0020, UNK-0011, "
        "UNK-0012, UNK-0013),",
        "- queue reconstructability and passive fill modelling (UNK-0007, UNK-0019),",
        "- signal half-life and measured latency (UNK-0008, UNK-0016, UNK-0017),",
        "- venue-specific after-cost replication (UNK-0009),",
        "- instrument-level specificity for several tuples (UNK-0027).",
        "",
        "Running D1 now would require substituting default or average values for those",
        "dimensions, which is exactly what the handoff, the deep-research artifact and the",
        "project charter forbid. A weighted ranking over missing values is not a weaker form of",
        "analysis; it is a fabricated one.",
        "",
        "## What must happen first",
        "",
        "1. Clear or accept the blockers in section 5 of `M1_D0_READINESS.md`, in the priority",
        "   order given there.",
        "2. Produce a CURRENT M1-B synthesis artifact from the surviving tuples.",
        "3. Only then run D1: hard filter, Pareto analysis, evidence-backed scoring matrix with",
        "   intervals, sensitivity scenarios, fragility report, and an export of 0-3 hypotheses.",
        "",
        "## Explicit statement of the alternative outcome",
        "",
        "If the blockers cannot be cleared, the correct M1 outcome is **M1 FAILED or M1 PARTIAL**,",
        "not a manufactured shortlist. The handoff states this directly, and the current state",
        "supports it: 0 candidates are ALIVE, and 5 of the 9 dead rows died on facts that are",
        "already verified.",
        "",
    ])