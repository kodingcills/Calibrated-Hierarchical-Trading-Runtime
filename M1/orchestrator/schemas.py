"""Orchestrator schemas: enums, card/patch contracts and their validation.

Kept dependency-free and explicit. A schema violation is an error, never a warning: the
orchestrator fails closed, because a malformed work item or patch silently accepted is how a
fabricated fact enters canonical state.
"""

from __future__ import annotations

import json
from pathlib import Path

from corpus.staging import (BRANCH_IMPACTS, EFFORTS, KILL_POTENTIALS, RESOLUTION_METHODS,
                            RESOLUTION_STAGES, TIER_DEFINITIONS)

UNKNOWN = None

ISSUE_STATUSES = (
    "OPEN", "IN_PROGRESS", "RESOLVED_SUPPORTS", "RESOLVED_WEAKENS", "RESOLVED_KILLS",
    "EXTERNAL_REQUEST_READY", "EMPIRICAL_SPEC_READY", "SEARCH_EXHAUSTED", "DEFERRED",
    "SUPERSEDED",
)

TERMINAL_ISSUE_STATUSES = ("RESOLVED_SUPPORTS", "RESOLVED_WEAKENS", "RESOLVED_KILLS",
                           "SEARCH_EXHAUSTED", "SUPERSEDED", "DEFERRED")

PATCH_DECISIONS = ("SUPPORTS", "WEAKENS", "KILLS", "RECLASSIFY", "NO_CHANGE", "SEARCH_EXHAUSTED")
PATCH_STATUSES = ("PROPOSED", "VERIFIED", "REJECTED", "APPLIED")

CARD_FIELDS = (
    "blocker_id", "title", "resolution_method", "resolution_stage", "tier", "status",
    "affected_candidates", "affected_gates", "decision_prevented", "required_answer",
    "acceptable_evidence", "disallowed_evidence", "known_evidence_ids", "known_source_ids",
    "contradictory_evidence_ids", "success_condition", "kill_condition",
    "resurrection_condition", "branch_impact", "kill_potential", "estimated_effort",
    "priority_reason", "priority_score", "last_updated",
)

PATCH_FIELDS = (
    "patch_id", "blocker_ids", "candidate_ids", "new_sources", "new_evidence",
    "modified_claims", "proposed_issue_updates", "proposed_candidate_updates",
    "proposed_gate_changes", "proposed_assumption_updates", "proposed_dead_end_updates",
    "new_unknowns", "decision", "reason", "verification_notes", "status", "created_at",
)

NEW_UNKNOWN_FIELDS = ("issue_id", "claim_needed", "known_evidence", "specific_evidence_needed",
                      "decision_prevented", "severity", "resolution_method", "resolution_stage",
                      "tier", "branch_impact", "kill_potential", "estimated_effort",
                      "migration_reason")

NEW_SOURCE_FIELDS = ("source_id", "title", "authors_or_org", "publication_date", "access_date",
                     "date_basis", "url", "source_type", "primary_or_secondary", "limitations",
                     "status")

VENUE_UPDATE_FIELDS = ("venue_id", "fields", "source_ids", "reason")
NEW_EVIDENCE_FIELDS = ("evidence_id", "claim", "source_id", "candidate_ids", "epistemic_class",
                       "evidence_origin", "supports_or_weakens", "methodology", "sample",
                       "temporal_scope", "gross_or_net", "limitations", "decision_implication",
                       "verification_status")


class SchemaError(ValueError):
    pass


def _require(record, fields, kind, where):
    missing = [f for f in fields if f not in record]
    if missing:
        raise SchemaError(f"{kind} {where}: missing fields {missing}")


def validate_card(card) -> None:
    _require(card, CARD_FIELDS, "card", card.get("blocker_id", "?"))
    if card["resolution_method"] not in RESOLUTION_METHODS:
        raise SchemaError(f"card {card['blocker_id']}: bad resolution_method")
    if card["resolution_stage"] not in RESOLUTION_STAGES:
        raise SchemaError(f"card {card['blocker_id']}: bad resolution_stage")
    try:
        card["tier"] = int(card["tier"])
    except (TypeError, ValueError):
        raise SchemaError(f"card {card['blocker_id']}: bad tier {card['tier']!r}")
    if card["tier"] not in TIER_DEFINITIONS:
        raise SchemaError(f"card {card['blocker_id']}: bad tier")
    if card["branch_impact"] not in BRANCH_IMPACTS:
        raise SchemaError(f"card {card['blocker_id']}: bad branch_impact")
    if card["kill_potential"] not in KILL_POTENTIALS:
        raise SchemaError(f"card {card['blocker_id']}: bad kill_potential")
    if card["estimated_effort"] not in EFFORTS:
        raise SchemaError(f"card {card['blocker_id']}: bad estimated_effort")
    if card["status"] not in ISSUE_STATUSES:
        raise SchemaError(f"card {card['blocker_id']}: bad status {card['status']!r}")


def validate_patch(patch) -> None:
    _require(patch, PATCH_FIELDS, "patch", patch.get("patch_id", "?"))
    if patch["decision"] not in PATCH_DECISIONS:
        raise SchemaError(f"patch {patch['patch_id']}: bad decision")
    if patch["status"] not in PATCH_STATUSES:
        raise SchemaError(f"patch {patch['patch_id']}: bad status")
    for src in patch["new_sources"]:
        _require(src, NEW_SOURCE_FIELDS, "new_source", f"in {patch['patch_id']}")
        if src["url"] in (None, "", "UNKNOWN") and src["status"] == "VERIFIED":
            raise SchemaError(f"patch {patch['patch_id']}: source {src['source_id']} claims "
                              f"VERIFIED with no URL")
    for ev in patch["new_evidence"]:
        _require(ev, NEW_EVIDENCE_FIELDS, "new_evidence", f"in {patch['patch_id']}")
        if ev["epistemic_class"] not in ("CONSENSUS_FACT", "SUPPORTED_FINDING",
                                         "CONTESTED_HYPOTHESIS", "EXTRAPOLATION", "UNKNOWN"):
            raise SchemaError(f"patch {patch['patch_id']}: bad epistemic_class")
        if ev["supports_or_weakens"] not in ("SUPPORTS", "WEAKENS", "NEUTRAL"):
            raise SchemaError(f"patch {patch['patch_id']}: bad supports_or_weakens")
        if ev["supports_or_weakens"] == "SUPPORTS" and ev["gross_or_net"] in (None, "", "UNKNOWN"):
            raise SchemaError(f"patch {patch['patch_id']}: supporting evidence must declare "
                              f"gross_or_net")


def load_patch_files(directory: Path) -> list:
    out = []
    if not directory.exists():
        return out
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = str(path)
        out.append(data)
    return out


def write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8")
    return path