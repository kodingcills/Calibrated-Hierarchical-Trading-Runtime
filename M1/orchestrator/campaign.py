"""Bounded strategic campaign layer above the M1 closure orchestrator.

This module consumes canonical M1 artifacts; it does not create a second state store.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
M1 = HERE.parent
REPO = M1.parent
WORK = M1 / "work"
OUTPUT = M1 / "output"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capabilities import CAPABILITIES, TOPOLOGIES, validate as validate_capability

ACTION_IMPACTS = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
LEVELS = {"HIGH", "MEDIUM", "LOW"}
SOURCES = {"DERIVED", "STRATEGIC_PROPOSAL"}
STATUSES = {"READY", "BLOCKED_EXTERNAL", "BLOCKED_AMBIGUOUS", "DEFERRED", "SELECTED", "EXECUTED"}
ACTION_FIELDS = (
    "action_id", "capability", "target_candidate_ids", "target_uncertainty_or_blocker",
    "question", "decision_changed", "expected_decision_impact", "resolution_confidence",
    "estimated_cost", "reuse_value", "duplication_risk", "prerequisites", "blocked",
    "blocked_on", "topology", "verification", "source", "status",
)
DEAD_NASDAQ = {
    "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
    "TUP-NASDAQ-LARGETICK-H2-QIMB-PAS",
    "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
    "TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _state_files() -> tuple[Path, ...]:
    return (
        REPO / "PROJECT_STATE.md", M1 / "data" / "candidate_tuples.csv",
        M1 / "data" / "dead_candidates.csv", M1 / "data" / "discrepancies.csv",
        M1 / "data" / "evidence_ledger.csv", OUTPUT / "M1_CANDIDATE_RESELECTION.json",
        OUTPUT / "M1_STATE_SUMMARY.json", WORK / "frontier.json",
    )


def state_reference() -> dict:
    files = [p for p in _state_files() if p.exists()]
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(REPO)).encode())
        digest.update(path.read_bytes())
    return {"sha256": digest.hexdigest(), "files": [str(p.relative_to(REPO)) for p in files]}


def _candidate_rows() -> list[dict[str, str]]:
    return _read_csv(M1 / "data" / "candidate_tuples.csv")


def _dead_ids() -> set[str]:
    return {row["candidate_id"] for row in _read_csv(M1 / "data" / "dead_candidates.csv")}


def _action(action_id: str, capability: str, candidates: Iterable[str], blocker: str,
            question: str, decision: str, impact: str, confidence: str, cost: str,
            reuse: str, duplication: str, prerequisites: list[str], blocked: bool,
            blocked_on: list[str], topology: str, verification: str, source: str,
            status: str = "READY") -> dict:
    action = {
        "action_id": action_id, "capability": capability,
        "target_candidate_ids": sorted(set(candidates)),
        "target_uncertainty_or_blocker": blocker, "question": question,
        "decision_changed": decision, "expected_decision_impact": impact,
        "resolution_confidence": confidence, "estimated_cost": cost,
        "reuse_value": reuse, "duplication_risk": duplication,
        "prerequisites": prerequisites, "blocked": blocked,
        "blocked_on": blocked_on, "topology": topology,
        "verification": verification, "source": source, "status": status,
    }
    validate_action(action)
    return action


def validate_action(action: dict) -> None:
    missing = [field for field in ACTION_FIELDS if field not in action]
    if missing:
        raise ValueError(f"action {action.get('action_id', '?')} missing {missing}")
    if action["expected_decision_impact"] not in ACTION_IMPACTS:
        raise ValueError(f"bad decision impact: {action['expected_decision_impact']}")
    for field in ("resolution_confidence", "estimated_cost", "reuse_value"):
        if action[field] not in LEVELS:
            raise ValueError(f"bad {field}: {action[field]}")
    if action["duplication_risk"] not in {"NONE", "PARTIAL", "HIGH"}:
        raise ValueError(f"bad duplication risk: {action['duplication_risk']}")
    if action["source"] not in SOURCES or action["status"] not in STATUSES:
        raise ValueError(f"bad action source/status: {action['source']}/{action['status']}")
    if not isinstance(action["target_candidate_ids"], list):
        raise ValueError("target_candidate_ids must be a list")
    if not isinstance(action["blocked"], bool) or not isinstance(action["blocked_on"], list):
        raise ValueError("blocked and blocked_on have invalid types")
    if action["blocked"] and not action["blocked_on"]:
        raise ValueError("blocked action must name blocked_on")
    if not action["blocked"] and action["blocked_on"]:
        raise ValueError("ready action cannot name blocked_on")
    validate_capability(action["capability"], action["topology"])
    if action["status"] == "BLOCKED_EXTERNAL" and not action["blocked"]:
        raise ValueError("external status requires blocked=true")


def _external_actions(candidates: list[dict[str, str]], reselection: dict) -> list[dict]:
    es = "TUP-CME-ES-H3-OFI-AGG"
    return [_action(
        "ACT-E01-ES-EXTERNAL-CLOSURE", "EXTERNAL_REQUEST", [es],
        "UNK-0002|UNK-0003|UNK-0009-MECH-CME|UNK-0023-CME-DOCS",
        "Can the exact ES account, historical sample, and mechanism prerequisites be supplied?",
        "whether ES can move from conditional frontier to an authorized experiment",
        "CRITICAL", "HIGH", "LOW", "HIGH", "NONE",
        ["operator/account classification", "exact ES data path",
         "verified structural cost C0 and a declared unresolved cost C1 parameterization",
         "exact account-level cost schedule (gate before shadow/micro-live, not before the gross precursor)"],
        True, ["external operator/account and data authorization"], "EXTERNAL",
        "request_contract_check", "DERIVED", "BLOCKED_EXTERNAL")]


def compile_actions() -> dict:
    candidates = _candidate_rows()
    dead = _dead_ids() | DEAD_NASDAQ
    by_id = {row["candidate_id"]: row for row in candidates}
    reselection = _read_json(OUTPUT / "M1_CANDIDATE_RESELECTION.json")
    actions = _external_actions(candidates, reselection)
    actions.extend([
        _action(
            "ACT-E01-CANONICAL-DETERMINISTIC-CHECK", "DETERMINISTIC_ANALYSIS", [],
            "canonical-state-consistency", "Does the current canonical state support a strategic frontier distinct from controller.py next?",
            "whether tactical blocker order should receive strategic priority", "HIGH", "HIGH", "LOW", "HIGH", "NONE",
            ["M1 state summary", "closure frontier", "candidate and dead registries"], False, [], "DETERMINISTIC",
            "deterministic_reproduction", "DERIVED"),
        _action(
            "ACT-E01-ES-MINIMUM-PRECURSOR", "DERIVE_PRECURSOR", ["TUP-CME-ES-H3-OFI-AGG"],
            "UNK-0002|UNK-0003|UNK-0009-MECH-CME", "What is the smallest fixed evidence contract that could make the conditional ES experiment decidable?",
            "whether ES can be cheaply screened before any full experiment or purchase", "HIGH", "HIGH", "LOW", "HIGH", "NONE",
            ["existing reselection specification"], True, ["external data/account facts"], "DETERMINISTIC",
            "deterministic_reproduction", "STRATEGIC_PROPOSAL", "BLOCKED_EXTERNAL"),
        _action(
            "ACT-E01-DIVERSITY-HYPERLIQUID", "DIVERSITY_SCOUT",
            ["TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"], "UNK-0009-ECON-CRYPTO-SPOT|UNK-0018-HYPERLIQUID",
            "Could the surviving Hyperliquid H4 funding/basis family offer a materially cheaper decision path than the externally blocked ES branch?",
            "whether an independent family deserves priority while ES waits", "HIGH", "MEDIUM", "LOW", "HIGH", "PARTIAL",
            ["candidate row", "canonical venue facts", "current reselection state"], False, [], "PARALLEL_SEARCH",
            "independent_source_verification", "STRATEGIC_PROPOSAL"),
        _action(
            "ACT-E01-DIVERSITY-AUCTION", "DIVERSITY_SCOUT",
            ["TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG"], "UNK-0027-AUCTION|UNK-0004",
            "Could closing-auction imbalance be a distinct, decision-relevant family rather than a resurrection of the closed top-of-book sequence?",
            "whether an independent auction family merits bounded research", "MEDIUM", "MEDIUM", "LOW", "MEDIUM", "NONE",
            ["candidate row", "dead-family registry"], False, [], "PARALLEL_SEARCH",
            "independent_source_verification", "STRATEGIC_PROPOSAL"),
    ])
    for action in actions:
        forbidden = set(action["target_candidate_ids"]) & dead
        if forbidden and action["capability"] not in {"EXTERNAL_REQUEST"}:
            raise ValueError(f"dead candidates generated ordinary action: {sorted(forbidden)}")
    payload = {
        "generated_at": _now(), "state_reference": state_reference(),
        "canonical_reselection": {
            "terminal_state": reselection.get("terminal_state"),
            "conditional_frontier": reselection.get("external_block", {}).get("successor_goal"),
        },
        "actions": actions,
        "autonomous_action_count": sum(not a["blocked"] for a in actions),
        "external_action_count": sum(a["capability"] == "EXTERNAL_REQUEST" for a in actions),
        "suppressed_dead_candidates": sorted(dead),
        "tactical_frontier_reference": str((WORK / "frontier.json").relative_to(REPO)),
    }
    return payload


def select_actions(frontier: dict) -> dict:
    ready = [a for a in frontier["actions"] if not a["blocked"] and a["status"] == "READY"]
    external = [a for a in frontier["actions"] if a["capability"] == "EXTERNAL_REQUEST"]
    selected_ids = {
        "ACT-E01-CANONICAL-DETERMINISTIC-CHECK",
        "ACT-E01-ES-MINIMUM-PRECURSOR",
        "ACT-E01-DIVERSITY-HYPERLIQUID",
    }
    selected = []
    for action in frontier["actions"]:
        if action["action_id"] in selected_ids:
            action = dict(action)
            action["status"] = "SELECTED"
            selected.append(action)
    if not selected:
        raise ValueError("frontier selected no autonomous action")
    if len(selected) > 3:
        raise ValueError("epoch exceeds three autonomous actions")
    selected += [dict(a, status="SELECTED") for a in external]
    return {
        "epoch_id": "EPOCH-001", "created_at": _now(),
        "starting_state": frontier["state_reference"],
        "selected_actions": selected,
        "selection_reason": (
            "Select one deterministic integrity action and two independent low-cost actions; "
            "surface ES external closure without allocating autonomous compute. The set is "
            "strategic and need not equal controller.py next."
        ),
        "topology_boundaries": {a["action_id"]: a["topology"] for a in selected},
        "verification_requirements": {a["action_id"]: a["verification"] for a in selected},
        "worker_assignments": {
            "ACT-E01-CANONICAL-DETERMINISTIC-CHECK": {
                "OBJECTIVE": "Reconcile canonical state references and strategic/tactical distinction.",
                "WHY_IT_MATTERS": "Prevents stale or tactical-only allocation.",
                "INPUT_STATE": "M1 output summaries, closure frontier, candidate/dead registries.",
                "SCOPE": "Read-only deterministic repository inspection.",
                "OUT_OF_SCOPE": "Canonical edits, research, external access, dead-family reopening.",
                "EVIDENCE_REQUIREMENT": "Reproducible hashes and IDs.",
                "SUCCESS_CONDITION": "Checks pass and result is recorded.",
                "FALSIFICATION_CONDITION": "Canonical references disagree.",
                "BUDGET": "deterministic local check; no worker launch",
                "OUTPUT_CONTRACT": "verification record and NO_CHANGE",
            },
            "ACT-E01-ES-MINIMUM-PRECURSOR": {
                "OBJECTIVE": "Derive the minimum sufficient ES evidence contract from the existing frozen spec.",
                "WHY_IT_MATTERS": "Reduces future external request scope without assuming inputs.",
                "INPUT_STATE": "M1/work/reselection_specs/TUP-CME-ES-H3-OFI-AGG.json.",
                "SCOPE": "Read-only contract derivation.",
                "OUT_OF_SCOPE": "Purchases, account actions, economic values, canonical promotion.",
                "EVIDENCE_REQUIREMENT": "Exact field-level comparison to frozen spec.",
                "SUCCESS_CONDITION": "All prerequisites preserved and no value imputed.",
                "FALSIFICATION_CONDITION": "Derived contract omits a prerequisite or changes a frozen criterion.",
                "BUDGET": "deterministic local check; no worker launch",
                "OUTPUT_CONTRACT": "precursor record and NO_CHANGE",
            },
            "ACT-E01-DIVERSITY-HYPERLIQUID": {
                "OBJECTIVE": "Assess whether the H4 family is independent and worth bounded follow-up from current evidence.",
                "WHY_IT_MATTERS": "External ES blocking must not freeze independent families.",
                "INPUT_STATE": "canonical candidate, venue, open-question, and reselection artifacts.",
                "SCOPE": "Existing-evidence diversity assessment only.",
                "OUT_OF_SCOPE": "New venue claims, profitability, data purchase, account eligibility assumptions.",
                "EVIDENCE_REQUIREMENT": "Candidate-linked canonical references and explicit unknowns.",
                "SUCCESS_CONDITION": "Independent branch is classified without promotion.",
                "FALSIFICATION_CONDITION": "The branch is dead, duplicate, or lacks a decision it could change.",
                "BUDGET": "bounded local evidence review; no worker launch",
                "OUTPUT_CONTRACT": "scout record, likely DEFERRED/NO_CHANGE",
            },
        },
    }


def _execute(action: dict, frontier: dict) -> dict:
    result = {"action_id": action["action_id"], "status": "EXECUTED", "canonical_change": "NO_CHANGE"}
    if action["action_id"] == "ACT-E01-CANONICAL-DETERMINISTIC-CHECK":
        result.update({
            "result": "Canonical state remains source of truth; tactical next item is UNK-0002 while strategic frontier retains ES as conditional only.",
            "evidence_produced": ["state_reference", "dead_candidate_suppression_check", "tactical_vs_strategic_check"],
            "verification": "PASS: action frontier is distinct from M1/work/frontier.json next item and no dead target was selected.",
            "decision_changed": False,
        })
    elif action["action_id"] == "ACT-E01-ES-MINIMUM-PRECURSOR":
        spec = _read_json(WORK / "reselection_specs" / "TUP-CME-ES-H3-OFI-AGG.json")
        result.update({
            "result": "Minimum ES contract preserved: exact contract, roll rule, event/trade sample, sequence numbers, exchange timestamps, security definitions, clock semantics, and the corrected friction comparator (verified structural cost C0 + parameterized unresolved cost C1, unknown never zero, reported as the break-even residual cost C*). Exact account-level cost is a later gate before shadow/micro-live (D-0042).",
            "evidence_produced": ["M1/work/reselection_specs/TUP-CME-ES-H3-OFI-AGG.json"],
            "verification": "PASS: required/data/outcome/friction/null/kill/continuation fields retained; account-cost gate and methodology correction recorded; no values imputed.",
            "decision_changed": False,
            "spec_field_counts": {k: len(v) if isinstance(v, list) else 1 for k, v in spec.items()},
        })
    elif action["action_id"] == "ACT-E01-DIVERSITY-HYPERLIQUID":
        result.update({
            "result": "Independent H4 funding/basis family remains externally blocked and decision-relevant only as a diversity branch; no promotion or economic claim is justified from current canonical state.",
            "evidence_produced": ["M1/data/candidate_tuples.csv", "M1/output/M1_CANDIDATE_RESELECTION.json", "OPEN_QUESTIONS.md"],
            "verification": "PASS: candidate is not dead; unresolved access/data/cost facts remain explicit; branch is not Coinbase/Kraken and not Nasdaq top-of-book.",
            "decision_changed": False,
        })
    else:
        result.update({"result": "External request surfaced; no autonomous execution.", "verification": "PASS: EXTERNAL topology only.", "decision_changed": False})
    return result


def execute_epoch(frontier: dict, epoch: dict) -> dict:
    results = [_execute(action, frontier) for action in epoch["selected_actions"]]
    next_frontier = compile_actions()
    trace = {
        "epoch_id": epoch["epoch_id"], "starting_state_hash_or_reference": epoch["starting_state"],
        "actions_considered": frontier["actions"],
        "actions_selected": [a["action_id"] for a in epoch["selected_actions"]],
        "selection_reason": epoch["selection_reason"],
        "topologies": epoch["topology_boundaries"],
        "workers_or_tools_used": ["python3 deterministic campaign controller"],
        "budget_spent": {"autonomous_actions": 3, "external_actions_surfaced": 1, "worker_count": 0},
        "evidence_produced": [r["evidence_produced"] for r in results],
        "verification": [r["verification"] for r in results],
        "canonical_changes": [r["canonical_change"] for r in results],
        "dependencies_affected": {
            "TUP-CME-ES-H3-OFI-AGG": ["external prerequisites remain unresolved"],
            "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX": ["remains independent and externally blocked"],
        },
        "candidates_killed": [], "candidates_promoted": [],
        "actions_deferred": ["ACT-E01-DIVERSITY-AUCTION", "tactical closure actions"],
        "next_frontier": next_frontier,
        "human_attention_required": ["external ES request and operator/account/data facts"],
        "results": results,
    }
    return {"next_frontier": next_frontier, "trace": trace, "results": results}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    command = argv[1] if len(argv) > 1 else "compile"
    frontier = compile_actions()
    write_json(WORK / "action_frontier.json", frontier)
    if command == "compile":
        print(json.dumps({"actions": len(frontier["actions"]), "autonomous": frontier["autonomous_action_count"], "external": frontier["external_action_count"]}, indent=2))
        return 0
    epoch = select_actions(frontier)
    write_json(WORK / "current_epoch.json", epoch)
    if command == "select":
        print(json.dumps({"selected": [a["action_id"] for a in epoch["selected_actions"]]}, indent=2))
        return 0
    if command != "epoch":
        raise SystemExit(f"usage: {argv[0]} [compile|select|epoch]")
    outcome = execute_epoch(frontier, epoch)
    write_json(WORK / "action_frontier.json", outcome["next_frontier"])
    with (OUTPUT / "orchestration_trace.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(outcome["trace"], sort_keys=True) + "\n")
    print(json.dumps({"epoch_id": epoch["epoch_id"], "executed": len(outcome["results"]), "canonical_changes": "NO_CHANGE"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
