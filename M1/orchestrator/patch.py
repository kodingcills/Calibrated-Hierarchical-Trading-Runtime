"""Evidence patches: construction, verification, application (handoff §12, §13).

A patch is the only path by which research can change canonical state. Flow:

    resolver -> patch (PROPOSED) -> verify_patch (VERIFIED | REJECTED)
             -> materialize merges VERIFIED patches into the registries
             -> gate engine recomputes -> ceiling rules decide status

A REJECTED patch is preserved with its rejection reasons: a refused claim is itself evidence
about the frontier, and deleting it would hide why a blocker stayed open.
"""

from __future__ import annotations

import transitions
import schemas

UNKNOWN = None

PATCH_DEFAULTS = {
    "modified_claims": [],
    "proposed_venue_updates": [],
    "proposed_source_updates": [],
    "proposed_issue_updates": [],
    "proposed_candidate_updates": [],
    "proposed_gate_changes": [],
    "proposed_assumption_updates": [],
    "proposed_dead_end_updates": [],
    "new_unknowns": [],
}


def build_patch(patch_id, blocker_ids, decision, reason, verification_notes, created_at,
                candidate_ids=None, new_sources=None, new_evidence=None,
                modified_claims=None, proposed_issue_updates=None,
                proposed_candidate_updates=None, proposed_gate_changes=None,
                proposed_assumption_updates=None, proposed_dead_end_updates=None,
                new_unknowns=None):
    patch = {
        "patch_id": patch_id,
        "blocker_ids": blocker_ids,
        "candidate_ids": candidate_ids or [],
        "new_sources": new_sources or [],
        "new_evidence": new_evidence or [],
        "modified_claims": modified_claims or [],
        "proposed_issue_updates": proposed_issue_updates or [],
        "proposed_candidate_updates": proposed_candidate_updates or [],
        "proposed_gate_changes": proposed_gate_changes or [],
        "proposed_assumption_updates": proposed_assumption_updates or [],
        "proposed_dead_end_updates": proposed_dead_end_updates or [],
        "new_unknowns": new_unknowns or [],
        "decision": decision,
        "reason": reason,
        "verification_notes": verification_notes,
        "status": "PROPOSED",
        "created_at": created_at,
    }
    for key, default in PATCH_DEFAULTS.items():
        patch.setdefault(key, default)
    return patch


def canonical_context(source_rows, evidence_rows, candidate_rows, issue_rows):
    return {
        "source_ids": {r["source_id"] for r in source_rows},
        "evidence_ids": {r["evidence_id"] for r in evidence_rows},
        "candidate_ids": {r["candidate_id"] for r in candidate_rows},
        "issue_ids": {r["issue_id"] for r in issue_rows},
        "lead_only_source_ids": {r["source_id"] for r in source_rows
                                 if r.get("source_type") in ("social_lead",)
                                 or str(r.get("raw_citation_token", "")).startswith("turn")},
    }


def verify_all(patches, cards_by_id, canonical) -> list:
    out = []
    for patch in patches:
        card = None
        for bid in patch["blocker_ids"]:
            if bid in cards_by_id:
                card = cards_by_id[bid]
                break
        result = transitions.verify_patch(patch, card, canonical)
        record = dict(patch)
        record["status"] = result["status"]
        record["verification_notes"] = "; ".join(result["notes"])
        record["rejected_claims"] = result["rejected_claims"]
        out.append(record)
    return out


def apply_verified(patches, source_rows, evidence_rows, issue_rows, cards_by_id,
                   venue_rows=None):
    """Merge VERIFIED patches into materialised rows. Returns merged rows plus an audit trail."""
    sources = list(source_rows)
    evidence = list(evidence_rows)
    issues = [dict(r) for r in issue_rows]
    venues = [dict(r) for r in (venue_rows or [])]
    venue_index = {r["venue_id"]: r for r in venues}
    audit = []
    issue_index = {r["issue_id"]: r for r in issues}

    for patch in patches:
        if patch["status"] != "VERIFIED":
            audit.append({"kind": "PATCH", "patch_id": patch["patch_id"], "applied": False,
                          "reason": f"status {patch['status']}"})
            continue
        added_sources = []
        for src in patch["new_sources"]:
            if any(s["source_id"] == src["source_id"] for s in sources):
                audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": False,
                              "reason": f"duplicate source id {src['source_id']}"})
                continue
            src = dict(src)
            src["raw_citation_token"] = f"patch:{patch['patch_id']}"
            src.setdefault("local_path", UNKNOWN)
            src.setdefault("sha256", UNKNOWN)
            src.setdefault("independent_replication", UNKNOWN)
            src.setdefault("sample_period", UNKNOWN)
            src.setdefault("sample_size", UNKNOWN)
            src.setdefault("market", UNKNOWN)
            src.setdefault("venue", UNKNOWN)
            src.setdefault("claim_scope", patch["reason"])
            sources.append(src)
            added_sources.append(src["source_id"])

        added_evidence = []
        for ev in patch["new_evidence"]:
            if any(e["evidence_id"] == ev["evidence_id"] for e in evidence):
                audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": False,
                              "reason": f"duplicate evidence id {ev['evidence_id']}"})
                continue
            ev = dict(ev)
            ev.setdefault("mechanism_id", UNKNOWN)
            ev.setdefault("venue_id", UNKNOWN)
            for field in ("observed_market", "observed_venue",
                          "observed_instrument_or_universe", "observed_period",
                          "observed_horizon"):
                ev.setdefault(field, UNKNOWN)
            ev.setdefault("transfer_status", "UNKNOWN")
            ev.setdefault("candidate_link_reason", patch["reason"])
            ev.setdefault("evidence_state", "PATCH_SUPPLIED")
            evidence.append(ev)
            added_evidence.append(ev["evidence_id"])

        for update in patch["proposed_issue_updates"]:
            row = issue_index.get(update["issue_id"])
            if row is None:
                continue
            row["status"] = update["to_status"]
            if update.get("resolution_note"):
                row["notes"] = update["resolution_note"]
            row["last_updated"] = patch["created_at"]

        for update in patch.get("proposed_source_updates", []):
            target = next((s for s in sources if s["source_id"] == update["source_id"]), None)
            if target is None:
                audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": False,
                              "reason": f"unknown source {update['source_id']}"})
                continue
            for field, value in update["fields"].items():
                target[field] = value
            audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": True,
                          "source_update": update["source_id"],
                          "fields": sorted(update["fields"]),
                          "reason": update["reason"]})

        venue_changes = []
        for update in patch.get("proposed_venue_updates", []):
            venue = venue_index.get(update["venue_id"])
            if venue is None:
                audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": False,
                              "reason": f"unknown venue {update['venue_id']}"})
                continue
            for field, value in update["fields"].items():
                venue[field] = value
            venue_changes.append(update["venue_id"])
            audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": True,
                          "venue_update": update["venue_id"],
                          "fields": sorted(update["fields"]),
                          "sources": update["source_ids"]})

        for entry in patch["new_unknowns"]:
            if any(r["issue_id"] == entry["issue_id"] for r in issues):
                audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": False,
                              "reason": f"duplicate issue id {entry['issue_id']}"})
                continue
            issues.append(new_issue_row(entry, patch,
                                        patch_source_ids=[s["source_id"]
                                                          for s in patch["new_sources"]]))
            audit.append({"kind": "EFFECT", "patch_id": patch["patch_id"], "applied": True,
                          "new_unknown": entry["issue_id"]})

        audit.append({"kind": "PATCH", "patch_id": patch["patch_id"], "applied": True,
                      "sources_added": added_sources, "evidence_added": added_evidence,
                      "issue_updates": [u["issue_id"] for u in patch["proposed_issue_updates"]],
                      "decision": patch["decision"]})

    return sources, evidence, issues, venues, audit


def new_issue_row(entry, patch, columns=None, patch_source_ids=None):
    """Expand a proposed unknown into a full issue row, defaulting every unset column to UNKNOWN.

    A defaulted column is visible as UNKNOWN, never as a plausible value: an unknown entering the
    registry through a patch is held to exactly the same provenance rules as an authored one.
    """
    from corpus.unknowns import DISCREPANCY_COLUMNS
    row = {col: None for col in (columns or DISCREPANCY_COLUMNS)}
    row.update({k: v for k, v in entry.items() if k in row})
    row.setdefault("severity", "BLOCKING")
    row["status"] = "OPEN"
    row["conflict_type"] = row.get("conflict_type") or "NO_CONFLICT_INCOMPLETENESS"
    row["last_updated"] = patch["created_at"]
    row["candidate_id"] = row.get("candidate_id")
    row["resolution_method"] = entry["resolution_method"]
    row["resolution_stage"] = entry["resolution_stage"]
    row["tier"] = entry["tier"]
    row["branch_impact"] = entry["branch_impact"]
    row["kill_potential"] = entry["kill_potential"]
    row["estimated_effort"] = entry["estimated_effort"]
    row["migration_decision"] = f"STAGE_{entry['resolution_stage']}"
    row["migration_from"] = None
    ids = list(patch_source_ids or [])
    row["source_A"] = row.get("source_A") or (ids[0] if ids else None)
    row["source_B"] = row.get("source_B") or (ids[1] if len(ids) > 1 else None)
    row["notes"] = row.get("notes") or f"Registered by evidence patch {patch['patch_id']}."
    return row


def rejection_report(patches) -> list:
    return [{"patch_id": p["patch_id"], "rejected_claims": p.get("rejected_claims", []),
             "notes": p.get("verification_notes")}
            for p in patches if p["status"] == "REJECTED"]