#!/usr/bin/env python3
"""M1 Closure Orchestrator - controller.

    python3 M1/orchestrator/controller.py compile    # rebuild frontier + work artefacts
    python3 M1/orchestrator/controller.py next       # highest-leverage frontier item
    python3 M1/orchestrator/controller.py status     # closure snapshot
    python3 M1/orchestrator/controller.py log "..."  # append an iteration record

The orchestrator is a state machine, not a recursive agent loop:

    COMPILE -> FRONTIER -> PRIORITIZE -> RESOLVE -> VERIFY -> PATCH -> MATERIALIZE -> VALIDATE
            -> RECOMPUTE

Only `frontier`-stage work is ever scheduled; measurement work becomes a preregistered spec and
procurement work becomes a sendable request packet, so neither pollutes the M1 frontier.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

M1 = Path(__file__).resolve().parents[1]
SRC = M1 / "src"
ORCH = Path(__file__).resolve().parent
for _p in (str(SRC), str(ORCH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import blocker_card  # noqa: E402
import frontier  # noqa: E402
import patch as patch_mod  # noqa: E402
import priority  # noqa: E402
import resolvers  # noqa: E402
import schemas  # noqa: E402
from corpus import staging  # noqa: E402

WORK = M1 / "work"
CARDS = WORK / "cards"
PATCHES = WORK / "patches"
REQUESTS = WORK / "external_requests"
SPECS = WORK / "m2_specs"
OUT = M1 / "output"
LOG = OUT / "closure_loop_log.md"
UNKNOWN = None


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_patches():
    return schemas.load_patch_files(PATCHES)


def build_closure(issue_rows, candidate_rows, evidence_rows, source_rows,
                  envelopes_by_id, venue_by_id, generated_at):
    """Compile cards, rank the frontier, generate specs and external requests."""
    spec_ids = resolvers.spec_registry(candidate_rows)
    for cid, ids in spec_ids.items():
        patch_candidates = None  # placeholder to keep the loop explicit
        del patch_candidates
        for spec_id in ids:
            assert spec_id in resolvers.SPEC_DEFINITIONS, spec_id

    cards = blocker_card.compile_all(issue_rows, candidate_rows, evidence_rows, source_rows,
                                     generated_at)
    active = blocker_card.frontier_cards(cards)
    ranked = priority.rank(active)
    inactive = blocker_card.non_frontier(cards)
    tier_violations = priority.tier_guard(ranked)

    frontier_payload = frontier.frontier_payload(ranked, None, candidate_rows,
                                                 _eligible_from(candidate_rows), generated_at)
    spec_registry = {"generated_at": generated_at, "by_candidate": spec_ids,
                     "specs": sorted(resolvers.SPEC_DEFINITIONS)}
    return {
        "generated_at": generated_at,
        "cards": cards,
        "frontier_cards": ranked,
        "non_frontier_cards": inactive,
        "frontier": frontier_payload,
        "spec_registry": spec_registry,
        "spec_ids_by_candidate": spec_ids,
        "tier_violations": tier_violations,
    }


def _eligible_from(candidate_rows) -> list:
    """Candidates whose gates are all PASS as recorded in the current registry snapshot."""
    from corpus.constants import GATE_IDS
    out = []
    for cand in candidate_rows:
        values = [str(cand.get(g, "")) for g in GATE_IDS]
        if values and all(v == "PASS" for v in values):
            out.append(cand["candidate_id"])
    return sorted(out)


def external_requests(closure) -> list:
    """Request packets for every EXTERNAL_ACTION M1_BLOCKING frontier card."""
    out = []
    candidate_cards = [c for c in closure["cards"].values()
                       if c["status"] in ("OPEN", "IN_PROGRESS", "EXTERNAL_REQUEST_READY")]
    for card in candidate_cards:
        if card["resolution_method"] != "EXTERNAL_ACTION":
            continue
        if card["resolution_stage"] != "M1_BLOCKING":
            continue
        if card["status"] == "SEARCH_EXHAUSTED":
            continue
        card = dict(card)
        if card.get("priority_score") is None:
            card["priority_score"] = priority.rank([card])[0]["priority_score"]
        if card["blocker_id"] not in resolvers.REQUEST_CONTENT:
            continue
        content = resolvers.REQUEST_CONTENT[card["blocker_id"]]
        out.append({
            "blocker_id": card["blocker_id"],
            "status": card["status"],
            "title": card["title"],
            "priority_score": card["priority_score"],
            "tier": card["tier"],
            "affected_candidates": card["affected_candidates"],
            "decision_prevented": card["decision_prevented"],
            "success_condition": card["success_condition"],
            "kill_condition": card["kill_condition"],
            "markdown": resolvers.external_request_md(card, **content),
        })
    out.sort(key=lambda r: (-r["priority_score"], r["blocker_id"]))
    return out


def deferred_cards(closure) -> list:
    """M1 blockers no resolver can answer: operator facts (HUMAN_INPUT) or postponed work.

    These are surfaced for a human but never dispatched autonomously. Their priority is computed
    for ordering the human queue only.
    

    These are surfaced separately: they require a human statement, not a search or a quote, and
    leaving them in the same list as vendor requests would hide that.
    """
    out = []
    for card in closure["cards"].values():
        if card["resolution_stage"] != "M1_BLOCKING":
            continue
        if card["resolution_method"] not in ("HUMAN_INPUT", "DEFERRED"):
            continue
        if card["status"] not in ("OPEN", "IN_PROGRESS"):
            continue
        out.append(card)
    out.sort(key=lambda c: (-(c.get("priority_score") or 0), c["blocker_id"]))
    return out


def deferred_md(cards) -> str:
    lines = [
        "",
        "## Human input required (not research, not vendor)",
        "",
        "These M1 blockers are facts about the operator, so no search or quote can resolve them.",
        "Each is stated so it can be answered in one line.",
        "",
    ]
    for card in cards:
        lines += [f"### {card['blocker_id']} - {card['title']}", "",
                  f"- question: {card['required_answer']}",
                  f"- why it blocks M1: {card['decision_prevented']}",
                  f"- affected rows: {len(card['affected_candidates'])}",
                  "- answer by writing the fact into `DECISIONS.md` and adding a patch row in "
                  "`M1/work/patches/` so the state change is recorded", ""]
    if not cards:
        lines.append("(none)")
    return "\n".join(lines)


def external_action_queue_md(requests, deferred=()) -> str:
    lines = [
        "# M1 external action queue",
        "",
        "Generated by `M1/orchestrator/controller.py`. Ordered by decision leverage. Each row is",
        "a packet a human can send without further thought: review, send, return the answer.",
        "",
        f"Open external requests: {len(requests)}",
        "",
        "| priority | blocker | what it decides | affected | packet |",
        "|---|---|---|---|---|",
    ]
    for req in requests:
        lines.append(
            f"| {req['priority_score']} | `{req['blocker_id']}` ({req['status']}) | "
            f"{req['decision_prevented']} | {len(req['affected_candidates'])} rows | "
            f"`M1/work/external_requests/{req['blocker_id']}.md` |")
    lines += ["", "## Detail", ""]
    for req in requests:
        lines += [
            f"### {req['blocker_id']} - {req['title']}",
            "",
            f"- send to: see `M1/work/external_requests/{req['blocker_id']}.md` section "
            f"`PURPOSE`",
            f"- exact ask: {req['decision_prevented']}",
            f"- answer that clears the branch: {req['success_condition']}",
            f"- answer that kills the branch: {req['kill_condition']}",
            f"- return the answer by writing a patch JSON into "
            f"`M1/work/patches/{req['blocker_id']}_response.json`, or copy the raw document into "
            f"`M1/work/external_requests/{req['blocker_id']}_received/`",
            "",
        ]
    lines.append(deferred_md(deferred))
    return "\n".join(lines)


def write_work(closure, requests, extra=None, deferred=()):
    CARDS.mkdir(parents=True, exist_ok=True)
    REQUESTS.mkdir(parents=True, exist_ok=True)
    SPECS.mkdir(parents=True, exist_ok=True)
    for card in closure["cards"].values():
        schemas.write_json(CARDS / f"{card['blocker_id']}.json", card)
    schemas.write_json(WORK / "frontier.json", closure["frontier"])
    schemas.write_json(SPECS / "registry.json", closure["spec_registry"])
    schemas.write_json(OUT / "M1_CLOSURE_STATUS.json",
                       extra or closure.get("closure_status", {}))
    for req in requests:
        (REQUESTS / f"{req['blocker_id']}.md").write_text(req["markdown"], encoding="utf-8")
    (OUT / "M1_EXTERNAL_ACTION_QUEUE.md").write_text(
        external_action_queue_md(requests, deferred), encoding="utf-8")
    if not LOG.exists():
        LOG.write_text(ITERATION_HEADER, encoding="utf-8")
    return {"cards": len(closure["cards"]), "requests": len(requests),
            "specs": len(closure["spec_registry"]["specs"])}


ITERATION_HEADER = """# Closure loop log

Append-only. One block per iteration. No narrative: the format exists so a later session can
reconstruct why state changed without re-reading the repository.

"""


def append_iteration(entry) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if not LOG.exists():
        LOG.write_text(ITERATION_HEADER, encoding="utf-8")
    block = ["", f"ITERATION: {entry.get('iteration')}",
             f"UTC: {entry.get('utc', now())}",
             f"BLOCKER CLUSTER: {entry.get('cluster')}",
             f"WHY SELECTED: {entry.get('why')}",
             f"RESOLUTION METHOD: {entry.get('method')}",
             f"SOURCES ADDED: {entry.get('sources_added')}",
             f"DECISION: {entry.get('decision')}",
             f"GATES BEFORE: {entry.get('gates_before')}",
             f"GATES AFTER: {entry.get('gates_after')}",
             f"CANDIDATES KILLED: {entry.get('killed')}",
             f"CANDIDATES PROMOTED: {entry.get('promoted')}",
             f"ISSUES RECLASSIFIED: {entry.get('reclassified')}",
             f"NEW ISSUES: {entry.get('new_issues')}",
             f"VALIDATION: {entry.get('validation')}",
             f"NEXT FRONTIER ITEM: {entry.get('next_item')}",
             ""]
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(block))


def migration_summary(issue_rows) -> dict:
    counts = {"M1_BLOCKING": 0, "M2_MEASUREMENT": 0, "POST_M2": 0, "NON_BLOCKING": 0}
    methods = {"PUBLIC_RESEARCH": 0, "EXTERNAL_ACTION": 0, "EMPIRICAL_MEASUREMENT": 0,
               "DEFERRED": 0}
    migrated = []
    for row in issue_rows:
        stage = row.get("resolution_stage")
        method = row.get("resolution_method")
        if stage in counts:
            counts[stage] += 1
        if method in methods:
            methods[method] += 1
        if row.get("migration_from") == "M1_BLOCKING":
            migrated.append(row["issue_id"])
    return {"by_stage": counts, "by_method": methods,
            "migrated_out_of_m1_blocking": sorted(migrated),
            "migrated_count": len(migrated),
            "unmapped_issues": staging.unmapped([r["issue_id"] for r in issue_rows])}


def main(argv) -> int:
    command = argv[1] if len(argv) > 1 else "status"
    status_path = OUT / "M1_CLOSURE_STATUS.json"
    frontier_path = WORK / "frontier.json"
    if command == "status":
        if not status_path.exists():
            print("no closure status yet: run materialize.py first")
            return 1
        data = json.loads(status_path.read_text(encoding="utf-8"))
        print(json.dumps({"terminal_state": data["terminal_state"],
                          "milestones": data["milestones"],
                          "candidate_counts": data["candidate_counts"],
                          "migration": data["migration"]["by_stage"],
                          "frontier_items": len(data["frontier"]["active_items"]),
                          "next_item": data["frontier"]["next_item"],
                          "gate_eligible": data["gate_eligible"]}, indent=1))
        return 0
    if command == "next":
        if not frontier_path.exists():
            print("no frontier yet: run materialize.py first")
            return 1
        data = json.loads(frontier_path.read_text(encoding="utf-8"))
        if not data["items"]:
            print("frontier empty: no M1_BLOCKING item is open")
            return 0
        item = data["items"][0]
        print(json.dumps(item, indent=1))
        return 0
    if command == "frontier":
        if not frontier_path.exists():
            print("no frontier yet: run materialize.py first")
            return 1
        data = json.loads(frontier_path.read_text(encoding="utf-8"))
        for item in data["items"]:
            print(f"{item['priority_score']:6.2f}  tier {item['tier']}  {item['blocker_id']:9s} "
                  f"{item['title']}")
        return 0
    if command == "log" and len(argv) > 2:
        append_iteration({"iteration": "manual", "cluster": argv[2]})
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except BrokenPipeError:  # paging the output must not look like a failure
        raise SystemExit(0)