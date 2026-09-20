"""Compile canonical issues into blocker cards (handoff §6).

A card is the unit of work. It is generated, never hand-written, so the frontier cannot drift
from the issue registry. Everything a resolver needs is on the card: what answer is required,
what evidence is acceptable, what is disallowed, and the conditions under which the work
succeeds or kills the branch.
"""

from __future__ import annotations

import schemas
from corpus.staging import BY_ID as STAGING_BY_ID

UNKNOWN = None

# Registry status -> card status. The registry keeps its own vocabulary (RESOLVED); a card must
# use the orchestrator's closed set, and only one mapping is faithful for a closed issue: it is
# no longer tracked. Nothing is silently upgraded to a "supports" resolution.
CARD_STATUS_MAP = {"RESOLVED": "SUPERSEDED"}

# Gate ids the issue can move, derived from its text-level scope rather than asserted.
GATE_HINTS = {
    "UNK-0001": "KG3_EXECUTION",
    "UNK-0002": "KG2_DATA|KG3_EXECUTION",
    "UNK-0003": "KG2_DATA",
    "UNK-0004": "KG2_DATA",
    "UNK-0005": "KG3_EXECUTION",
    "UNK-0006": "KG3_EXECUTION",
    "UNK-0007": "KG3_EXECUTION",
    "UNK-0008": "KG4_HALF_LIFE",
    "UNK-0009": "KG1_MECHANISM",
    "UNK-0010": "KG2_DATA|KG3_EXECUTION",
    "UNK-0011": "KG3_EXECUTION",
    "UNK-0012": "KG3_EXECUTION",
    "UNK-0013": "KG1_MECHANISM|KG3_EXECUTION",
    "UNK-0014": "KG1_MECHANISM|KG5_FALSIFIABILITY",
    "UNK-0015": "KG5_FALSIFIABILITY",
    "UNK-0016": "KG4_HALF_LIFE",
    "UNK-0017": "KG1_MECHANISM",
    "UNK-0018": "KG2_DATA",
    "UNK-0019": "KG3_EXECUTION",
    "UNK-0020": "KG2_DATA",
    "UNK-0021": "KG3_EXECUTION",
    "UNK-0022": "KG2_DATA|KG3_EXECUTION",
    "UNK-0023": "KG1_MECHANISM|KG3_EXECUTION",
    "UNK-0024": "NONE",
    "UNK-0025": "NONE",
    "UNK-0026": "NONE",
    "UNK-0027": "KG5_FALSIFIABILITY",
    "UNK-0028": "KG3_EXECUTION",
    "UNK-0029": "KG3_EXECUTION",
    "UNK-0030": "NONE",
    "UNK-0031": "NONE",
    "UNK-0032": "KG3_EXECUTION",
}


def _split(value) -> list:
    if value is UNKNOWN or value == "":
        return []
    return [x for x in str(value).split("|") if x]


def compile_card(issue, candidates, evidence_rows, sources, updated_at) -> dict:
    """Compile one card from the issue row, falling back to the authored staging table.

    Since the two-dimension model became part of the issue registry, a card must not depend on a
    second lookup table: a patch-added issue carries its own method/stage/tier, and a card
    compiled from a missing staging row would be a silent hole in the frontier.
    """
    issue_id = issue["issue_id"]
    stage_row = STAGING_BY_ID.get(issue_id)
    affected = _split(issue["affected_candidate_ids"]) or _split(issue["candidate_id"])
    title = stage_row[7] if stage_row else issue["claim_needed"][:90]
    required = stage_row[8] if stage_row else issue["specific_evidence_needed"]
    acceptable = stage_row[9] if stage_row else "Any primary source that answers the claim needed"
    disallowed = stage_row[10] if stage_row else "Assumed values, secondary summaries, social posts"
    success = stage_row[11] if stage_row else issue["specific_evidence_needed"]
    kill = stage_row[12] if stage_row else issue["decision_prevented"]
    reason = stage_row[13] if stage_row else issue.get("migration_reason")
    ticket = {
        "blocker_id": issue_id,
        "title": title,
        "resolution_method": issue["resolution_method"] or stage_row[1],
        "resolution_stage": issue["resolution_stage"] or stage_row[2],
        "tier": issue["tier"] or stage_row[3],
        "status": CARD_STATUS_MAP.get(issue["status"], issue["status"]),
        "affected_candidates": affected,
        "affected_gates": GATE_HINTS.get(issue_id, "NONE"),
        "decision_prevented": issue["decision_prevented"],
        "required_answer": required,
        "acceptable_evidence": acceptable,
        "disallowed_evidence": disallowed,
        "known_evidence_ids": _split(issue["evidence_ids"]),
        "known_source_ids": _split(issue["source_A"]) + _split(issue["source_B"]),
        "contradictory_evidence_ids": [
            row["evidence_id"] for row in evidence_rows
            if row["supports_or_weakens"] == "WEAKENS" and any(
                cid in _split(row["candidate_ids"]) for cid in affected)],
        "success_condition": success,
        "kill_condition": kill,
        "resurrection_condition": kill if issue_id in _DEAD_LINKED else UNKNOWN,
        "branch_impact": issue["branch_impact"] or stage_row[4],
        "kill_potential": issue["kill_potential"] or stage_row[5],
        "estimated_effort": issue["estimated_effort"] or stage_row[6],
        "priority_reason": reason,
        "priority_score": UNKNOWN,
        "last_updated": updated_at,
    }
    schemas.validate_card(ticket)
    return ticket


# Issues whose resolution can resurrect a dead row (their kill_condition doubles as the bar).
_DEAD_LINKED = {
    "UNK-0001", "UNK-0003", "UNK-0004", "UNK-0005", "UNK-0010", "UNK-0027",
}


def compile_all(issues, candidates, evidence_rows, sources, updated_at) -> dict:
    return {issue["issue_id"]: compile_card(issue, candidates, evidence_rows, sources, updated_at)
            for issue in issues}


def frontier_cards(cards) -> list:
    """Active frontier: M1_BLOCKING and still open. Never polluted with M2/POST_M2 work."""
    return [c for c in cards.values()
            if c["resolution_stage"] == "M1_BLOCKING" and c["status"] in ("OPEN", "IN_PROGRESS")]


def non_frontier(cards) -> list:
    return [c for c in cards.values()
            if c["resolution_stage"] != "M1_BLOCKING"
            or c["status"] not in ("OPEN", "IN_PROGRESS")]