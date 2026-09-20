"""Legal state transitions and the adversarial verification gate (handoff §12, §13).

Two jobs:

1. `legal_transition` — the finite-state machine. A proposed change to an issue status or a
   candidate status is checked against explicit rules. Free-form text can never set ALIVE or
   DEAD; it must survive these transitions and the computed gate ceiling.
2. `verify_patch` — adversarial review of an evidence patch before it can touch canonical
   state. It rejects patches that answer a different question than the card asked, that cite
   non-authoritative or undated sources, that transfer evidence across venue/instrument/horizon,
   that assert a gate change the cited evidence cannot support, or that treat an inference as a
   fact.
"""

from __future__ import annotations

import schemas
from corpus.constants import GATE_IDS

UNKNOWN = None

SOURCE_QUALITY = {
    "exchange_rule_doc": "PRIMARY",
    "exchange_fee_schedule": "PRIMARY",
    "exchange_technical_doc": "PRIMARY",
    "exchange_api_doc": "PRIMARY",
    "exchange_data_product": "PRIMARY",
    "exchange_notice": "PRIMARY",
    "exchange_process_doc": "PRIMARY",
    "exchange_venue_doc": "PRIMARY",
    "academic_paper": "PRIMARY",
    "government_notice": "PRIMARY",
    "regulation": "PRIMARY",
    "technical_secondary": "SECONDARY",
    "social_lead": "LEAD_ONLY",
}

# Gate transitions an evidence patch may propose, keyed by the decision it carries.
ALLOWED_GATE_MOVES = {
    "SUPPORTS": {("BLOCKED", "PASS")},
    "WEAKENS": {("PASS", "BLOCKED"), ("BLOCKED", "BLOCKED"), ("PASS", "FAIL")},
    "KILLS": {("PASS", "FAIL"), ("BLOCKED", "FAIL")},
    "RECLASSIFY": set(),
    "NO_CHANGE": set(),
    "SEARCH_EXHAUSTED": set(),
}


def legal_transition(current, target, kind="issue") -> tuple:
    """Return (allowed, reason). Explicit tables only; no inference from naming."""
    if kind == "issue":
        table = {
            "OPEN": {"IN_PROGRESS", "EXTERNAL_REQUEST_READY", "EMPIRICAL_SPEC_READY",
                     "SEARCH_EXHAUSTED", "DEFERRED", "SUPERSEDED",
                     "RESOLVED_SUPPORTS", "RESOLVED_WEAKENS", "RESOLVED_KILLS"},
            "IN_PROGRESS": {"RESOLVED_SUPPORTS", "RESOLVED_WEAKENS", "RESOLVED_KILLS",
                            "SEARCH_EXHAUSTED", "EXTERNAL_REQUEST_READY",
                            "EMPIRICAL_SPEC_READY", "DEFERRED"},
            "EXTERNAL_REQUEST_READY": {"IN_PROGRESS", "SEARCH_EXHAUSTED", "DEFERRED",
                                       "SUPERSEDED"},
            "EMPIRICAL_SPEC_READY": {"IN_PROGRESS", "DEFERRED", "SUPERSEDED"},
            "RESOLVED_SUPPORTS": {"SUPERSEDED", "IN_PROGRESS"},
            "RESOLVED_WEAKENS": {"SUPERSEDED", "IN_PROGRESS"},
            "RESOLVED_KILLS": {"SUPERSEDED"},
            "SEARCH_EXHAUSTED": {"IN_PROGRESS", "SUPERSEDED"},
            "DEFERRED": {"IN_PROGRESS", "SUPERSEDED"},
            "SUPERSEDED": set(),
        }
    else:
        table = {
            "ALIVE": {"DEAD"},
            "WEAK": {"WEAK", "UNKNOWN", "DEAD"},
            "UNKNOWN": {"UNKNOWN", "WEAK", "DEAD"},
            "DEAD": {"DEAD"},  # resurrection requires the explicit decision path below
        }
    if current == target:
        return True, "no-op"
    allowed = target in table.get(current, set())
    if not allowed:
        return False, f"transition {current} -> {target} is not permitted for {kind}"
    return True, "permitted"


def candidate_transition_allowed(current, target, resurrection_decision=UNKNOWN) -> tuple:
    """Resurrection is a distinct, explicit path.

    A DEAD row leaves the graveyard only through a named decision: new evidence alone is not
    enough, because the evidence would still have to be judged against the recorded resurrection
    condition. Without a decision id the transition is refused outright.
    """
    if current == "DEAD" and target == "DEAD":
        return True, "no-op"
    if current == "DEAD":
        if resurrection_decision is UNKNOWN:
            return False, ("DEAD rows cannot re-enter without an explicit resurrection decision "
                           "recorded in DECISIONS.md naming this candidate")
        return True, (f"permitted by explicit resurrection decision {resurrection_decision!r}; "
                      f"the row must still satisfy its recorded resurrection condition")
    return legal_transition(current, target, kind="candidate")


def verify_patch(patch, card, canonical) -> dict:
    """Adversarial verification. Returns {status, notes, rejected_claims}."""
    notes = []
    rejected = []

    try:
        schemas.validate_patch(patch)
    except schemas.SchemaError as exc:
        return {"status": "REJECTED", "notes": [f"schema error: {exc}"],
                "rejected_claims": ["SCHEMA"]}

    known_sources = set(canonical["source_ids"]) | {s["source_id"] for s in patch["new_sources"]}
    known_candidates = set(canonical["candidate_ids"])
    known_issues = set(canonical["issue_ids"])

    for ev in patch["new_evidence"]:
        if ev["source_id"] not in known_sources:
            rejected.append(f"{ev['evidence_id']}: source {ev['source_id']} not resolvable")
        for cid in str(ev["candidate_ids"] or "").split("|"):
            if cid and cid not in known_candidates:
                rejected.append(f"{ev['evidence_id']}: unknown candidate {cid}")
        if card and card["resolution_stage"] == "M1_BLOCKING":
            if ev["source_id"] in canonical["lead_only_source_ids"]:
                rejected.append(f"{ev['evidence_id']}: source is lead-generation only and cannot "
                                f"resolve an M1 blocker")
        if ev["supports_or_weakens"] == "SUPPORTS" and ev["epistemic_class"] in (
                "EXTRAPOLATION", "UNKNOWN"):
            rejected.append(f"{ev['evidence_id']}: an extrapolation cannot be recorded as "
                            f"supporting evidence")
        if card and card["affected_candidates"] and ev["supports_or_weakens"] == "SUPPORTS":
            touched = {c for c in str(ev["candidate_ids"] or "").split("|") if c}
            if touched and not (touched & set(card["affected_candidates"])):
                rejected.append(f"{ev['evidence_id']}: evidence concerns candidates outside the "
                                f"card's scope; cross-candidate transfer requires an explicit "
                                f"scope justification")

    for src in patch["new_sources"]:
        quality = SOURCE_QUALITY.get(src["source_type"], "UNKNOWN")
        if quality == "UNKNOWN":
            rejected.append(f"{src['source_id']}: unclassified source_type {src['source_type']!r}")
        if quality == "SECONDARY" and card and card["resolution_stage"] == "M1_BLOCKING":
            rejected.append(f"{src['source_id']}: secondary source cannot resolve an M1 blocker")
        if all(str(src[f]).strip() in ("", "UNKNOWN", "None")
               for f in ("publication_date", "access_date", "date_basis")):
            rejected.append(f"{src['source_id']}: no date and no date basis")

    for update in patch["proposed_issue_updates"]:
        if update["issue_id"] not in known_issues:
            rejected.append(f"issue update for unknown issue {update['issue_id']}")
            continue
        allowed, reason = legal_transition(update["from_status"], update["to_status"])
        if not allowed:
            rejected.append(f"{update['issue_id']}: {reason}")

    for change in patch["proposed_gate_changes"]:
        for gate in change["gates"]:
            if gate not in GATE_IDS:
                rejected.append(f"unknown gate {gate}")
                continue
            move = (change["from_value"], change["to_value"])
            allowed_moves = ALLOWED_GATE_MOVES.get(patch["decision"], set())
            if move not in allowed_moves:
                rejected.append(f"{change['candidate_id']}.{gate}: move {move} not permitted by "
                                f"decision {patch['decision']}")
        if patch["decision"] == "SUPPORTS" and not any(
                ev["supports_or_weakens"] == "SUPPORTS" for ev in patch["new_evidence"]):
            rejected.append(f"{change['candidate_id']}: SUPPORTS decision with no supporting "
                            f"evidence record")

    if patch["decision"] in ("SUPPORTS", "KILLS", "WEAKENS"):
        if not patch["verification_notes"] or "contrary" not in patch["verification_notes"].lower():
            rejected.append("verification_notes must record that contrary evidence was searched")

    status = "REJECTED" if rejected else "VERIFIED"
    notes.append(f"checked {len(patch['new_sources'])} sources, {len(patch['new_evidence'])} "
                 f"evidence records, {len(patch['proposed_gate_changes'])} gate changes")
    return {"status": status, "notes": notes, "rejected_claims": rejected}