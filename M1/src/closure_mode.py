"""Candidate closure mode and distance-to-eligibility metrics (handoff §15, §16).

Why this exists: once a candidate's remaining unknowns are private facts (vendor quotes, sample
files, operator jurisdiction), continuing to "research around" it burns tokens on questions no
search can answer. This module names that state, stops autonomous dispatch to it, and keeps it
prominent in the human queue.

The two distance metrics are *counts and classes, never performance scores*: they schedule
research work and must not be used to rank strategy quality.
"""

from __future__ import annotations

UNKNOWN = None

# Only public research is work the orchestrator can still do by itself. An EXTERNAL_ACTION item
# has already been turned into a request packet (validator V18 enforces that every one has a
# packet), so from that moment it is a human action, not autonomous dispatch.
AUTONOMOUS_METHODS = ("PUBLIC_RESEARCH",)
AWAITING_METHODS = ("EXTERNAL_ACTION",)
NON_AUTONOMOUS_METHODS = ("HUMAN_INPUT", "DEFERRED")
PASS_THRESHOLD_FOR_FOCUS = 3

DISPATCHABLE = "DISPATCHABLE"
AWAITING_EXTERNAL_CLOSURE = "AWAITING_EXTERNAL_CLOSURE"
BLOCKED_NOT_CLOSE = "BLOCKED_NOT_CLOSE"
GATE_ELIGIBLE = "GATE_ELIGIBLE"


def _split(value) -> list:
    from coverage import _split as split_refs
    return split_refs(value)


def open_issues_naming(issue_rows, candidate_id) -> list:
    out = []
    for row in issue_rows:
        if row["status"] not in ("OPEN", "IN_PROGRESS", "EXTERNAL_REQUEST_READY",
                                 "EMPIRICAL_SPEC_READY"):
            continue
        if str(row.get("is_aggregate_parent", "NO")).upper() == "YES":
            continue
        named = (candidate_id in _split(row.get("affected_candidate_ids"))
                 or row.get("candidate_id") == candidate_id)
        if named:
            out.append(row)
    return out


def candidate_metrics(candidate, issue_rows, gate_values) -> dict:
    gates = list(gate_values)
    passed = [g for g in gates if gate_values[g] == "PASS"]
    blocked = [g for g in gates if gate_values[g] == "BLOCKED"]
    failed = [g for g in gates if gate_values[g] == "FAIL"]
    issues = open_issues_naming(issue_rows, candidate["candidate_id"])

    autonomous = [i for i in issues
                  if i["resolution_method"] in AUTONOMOUS_METHODS
                  and i["resolution_stage"] == "M1_BLOCKING"
                  and i["status"] in ("OPEN", "IN_PROGRESS")]
    awaiting = [i for i in issues
                if i["resolution_method"] in AWAITING_METHODS
                and i["resolution_stage"] == "M1_BLOCKING"]
    human = [i for i in issues
             if i["resolution_method"] == "HUMAN_INPUT" and i["resolution_stage"] == "M1_BLOCKING"]
    deferred = [i for i in issues
                if i["resolution_method"] == "DEFERRED" and i["resolution_stage"] == "M1_BLOCKING"
                and i["severity"] == "BLOCKING"]

    external_count = len(awaiting) + len(human) + len(deferred)
    if not blocked and not failed:
        mode = GATE_ELIGIBLE
    elif len(passed) >= PASS_THRESHOLD_FOR_FOCUS and not autonomous and external_count:
        mode = AWAITING_EXTERNAL_CLOSURE
    elif autonomous:
        mode = DISPATCHABLE
    else:
        mode = BLOCKED_NOT_CLOSE

    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_class": candidate["candidate_class"],
        "pass_count": len(passed),
        "pass_gates": "|".join(passed) or "NONE",
        "blocked_gates": "|".join(blocked) or "NONE",
        "failed_gates": "|".join(failed) or "NONE",
        "closure_mode": mode,
        "autonomous_distance_to_eligibility": len(autonomous),
        "external_distance_to_eligibility": external_count,
        "autonomous_blockers": "|".join(sorted(i["issue_id"] for i in autonomous)) or "NONE",
        "external_blockers": "|".join(sorted(i["issue_id"] for i in
                                             awaiting + human + deferred)) or "NONE",
        "tier1_autonomous_blockers": len([i for i in autonomous if int(i["tier"]) == 1]),
        "dispatch_note": _dispatch_note(mode, autonomous, external_count, len(passed)),
    }


def _dispatch_note(mode, autonomous, external_count, passed) -> str:
    if mode == GATE_ELIGIBLE:
        return "All five gates PASS: eligible for M1-B comparison (not a profitability claim)."
    if mode == AWAITING_EXTERNAL_CLOSURE:
        return (f"{passed} of 5 gates PASS with no autonomous blocker left; {external_count} "
                f"external/human item(s) decide the branch. Removed from autonomous dispatch and "
                f"kept in the human queue.")
    if mode == DISPATCHABLE:
        return (f"{passed} of 5 gates PASS; {len(autonomous)} autonomous blocker(s) remain: "
                f"{', '.join(sorted(i['issue_id'] for i in autonomous))}.")
    return (f"{passed} of 5 gates PASS with no autonomous blocker and no external item on the "
            f"candidate row itself; the deciding issues are scoped to its venue or family, or the "
            f"branch is waiting on another gate.")


def metrics_rows(candidates, issue_rows, gate_status_by_id) -> list:
    rows = []
    for cand in candidates:
        if cand["candidate_class"] != "TUPLE":
            continue
        gates = gate_status_by_id.get(cand["candidate_id"])
        if not gates:
            continue
        rows.append(candidate_metrics(cand, issue_rows, gates))
    rows.sort(key=lambda r: (-r["pass_count"], r["autonomous_distance_to_eligibility"],
                             r["external_distance_to_eligibility"], r["candidate_id"]))
    return rows


def next_autonomous_branch(rows) -> dict:
    """Next branch to work autonomously (handoff §16).

    Order: fewest autonomous blockers, then most gates passed, then most Tier-1 autonomous
    blockers (cheap kills first), then fewest external items. Candidate distance to closure, not
    raw issue breadth.
    """
    dispatchable = [r for r in rows if r["closure_mode"] == DISPATCHABLE
                    and r["autonomous_distance_to_eligibility"] > 0]
    if not dispatchable:
        return {"candidate_id": UNKNOWN,
                "reason": "No candidate has an autonomous blocker left: the frontier is external."}
    dispatchable.sort(key=lambda r: (r["autonomous_distance_to_eligibility"],
                                     -r["pass_count"],
                                     -r["tier1_autonomous_blockers"],
                                     r["external_distance_to_eligibility"],
                                     r["candidate_id"]))
    best = dispatchable[0]
    return {
        "candidate_id": best["candidate_id"],
        "pass_count": best["pass_count"],
        "autonomous_blockers": best["autonomous_blockers"],
        "external_blockers": best["external_blockers"],
        "reason": (f"{best['autonomous_distance_to_eligibility']} autonomous blocker(s) remain "
                   f"with {best['pass_count']} of 5 gates already PASS, and the fewest external "
                   f"items among equally close branches."),
    }


def mode_counts(rows) -> dict:
    out = {}
    for row in rows:
        out[row["closure_mode"]] = out.get(row["closure_mode"], 0) + 1
    return out