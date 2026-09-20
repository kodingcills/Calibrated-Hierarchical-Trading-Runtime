"""Evidence-coverage counts and data-feasibility verdicts.

Coverage counts are descriptive (ASM-0017). They expose evidence *density* and direction;
they are deliberately not combined into a score, because a weighted index would convert
absent evidence into apparent precision.

Data-feasibility verdicts are recomputed from tri-state inputs and cross-checked so that a
venue-level fact cannot be contradicted by a candidate-level claim.
"""

from __future__ import annotations

UNKNOWN = None

_SUPPORT_CLASSES = ("CONSENSUS_FACT", "SUPPORTED_FINDING")
_DIRECTIONS = ("SUPPORTS", "WEAKENS", "NEUTRAL")


def _split(ids) -> list:
    if ids is UNKNOWN or ids == "":
        return []
    return [x for x in str(ids).split("|") if x]


ALL_TOKENS = ("ALL_CANDIDATES", "ALL_EXTERNAL_EVIDENCE")


def blocking_map(discrepancies, all_candidate_ids):
    """Map candidate -> set of BLOCKING issue ids that name it.

    ``ALL_CANDIDATES`` expands to every registered candidate, so a venue-wide or
    method-wide blocker is visible on the rows it actually governs rather than sitting in a
    pseudo-bucket.
    """
    out = {}
    for issue in discrepancies:
        if issue["severity"] != "BLOCKING":
            continue
        tokens = set(_split(issue["affected_candidate_ids"])) | set(_split(issue["candidate_id"]))
        targets = set()
        if tokens & set(ALL_TOKENS):
            targets |= set(all_candidate_ids)
        targets |= tokens & set(all_candidate_ids)
        for cid in targets:
            out.setdefault(cid, set()).add(issue["issue_id"])
    return out


def candidate_evidence(evidence_rows, candidate_id) -> list:
    return [row for row in evidence_rows if candidate_id in _split(row["candidate_ids"])]


def coverage_row(evidence_rows, candidate_id, blocking_issue_ids) -> dict:
    rows = candidate_evidence(evidence_rows, candidate_id)
    counts = {
        "consensus_fact_count": 0,
        "supported_finding_count": 0,
        "contested_count": 0,
        "extrapolation_count": 0,
        "unknown_class_count": 0,
        "supports_count": 0,
        "weakens_count": 0,
        "neutral_count": 0,
    }
    for row in rows:
        cls = row["epistemic_class"]
        if cls == "CONSENSUS_FACT":
            counts["consensus_fact_count"] += 1
        elif cls == "SUPPORTED_FINDING":
            counts["supported_finding_count"] += 1
        elif cls == "CONTESTED_HYPOTHESIS":
            counts["contested_count"] += 1
        elif cls == "EXTRAPOLATION":
            counts["extrapolation_count"] += 1
        else:
            counts["unknown_class_count"] += 1

        direction = row["supports_or_weakens"]
        if direction == "SUPPORTS":
            counts["supports_count"] += 1
        elif direction == "WEAKENS":
            counts["weakens_count"] += 1
        else:
            counts["neutral_count"] += 1

    # Support requires both a support-strength class and a supporting direction (ASM-0003).
    counts["support_evidence_count"] = sum(
        1 for row in rows
        if row["supports_or_weakens"] == "SUPPORTS" and row["epistemic_class"] in _SUPPORT_CLASSES)
    counts["contrary_evidence_count"] = counts["weakens_count"]
    counts["blocking_unknown_count"] = len(_split(blocking_issue_ids))
    counts["evidence_ids"] = "|".join(row["evidence_id"] for row in rows) or "NONE"

    counts["note"] = ("Descriptive counts only. NEUTRAL records are feasibility context and are "
                      "not netted against SUPPORTS/WEAKENS; no evidence score is computed "
                      "(ASM-0017). blocking_unknown_count counts M1-blocking issues only: an "
                      "issue migrated to M2_MEASUREMENT stops blocking this candidate's M1 "
                      "status by design (handoff §3).")
    return counts


def venue_specific_support_count(evidence_rows, candidate) -> int:
    """Support records that actually name this candidate's venue (loan of another venue's
    evidence does not count as venue-specific support)."""
    cid, venue = candidate["candidate_id"], candidate["venue_id"]
    return sum(
        1 for row in evidence_rows
        if row["supports_or_weakens"] == "SUPPORTS"
        and row["epistemic_class"] in _SUPPORT_CLASSES
        and cid in _split(row["candidate_ids"])
        and row["venue_id"] == venue)


def coverage_rows(evidence_rows, candidates, discrepancies) -> list:
    all_ids = [c["candidate_id"] for c in candidates]
    blocking_by_candidate = blocking_map(discrepancies, all_ids)

    rows = []
    for cand in candidates:
        cid = cand["candidate_id"]
        declared = set(_split(cand.get("blocking_issue_ids_declared")
                              if cand.get("blocking_issue_ids_declared") is not UNKNOWN
                              else cand["blocking_issue_ids"]))
        derived = blocking_by_candidate.get(cid, set())
        row = coverage_row(evidence_rows, cid, "|".join(sorted(declared | derived)))
        row["candidate_id"] = cid
        row["venue_specific_support_count"] = venue_specific_support_count(evidence_rows, cand)
        row["declared_blocking_issue_ids"] = "|".join(sorted(declared)) or "NONE"
        row["derived_blocking_issue_ids"] = "|".join(sorted(derived)) or "NONE"
        row["declared_is_subset_of_derived"] = (
            "YES" if declared <= derived else "NO")
        row["derived_not_declared"] = "|".join(sorted(derived - declared)) or "NONE"
        row["declared_not_derived"] = "|".join(sorted(declared - derived)) or "NONE"
        rows.append(row)
    return rows


# --------------------------------------------------------------------- feasibility
def feasibility_row(candidate, venue, feas) -> dict:
    """Recompute derived feasibility flags and flag internal contradictions."""
    notes = []
    live = feas["live_feed"]
    historical = feas["historical_feed"]
    l3 = feas["L3_available"]

    queue_replay = feas["queue_replay_possible"]
    if l3 == "FAIL" and queue_replay == "PASS":
        notes.append("CONTRADICTION: queue replay PASS while order-level data is FAIL")
    if historical == "FAIL" and queue_replay == "PASS":
        notes.append("CONTRADICTION: queue replay PASS with no historical feed")

    pit = feas["PIT_reconstructable"]
    if pit == "PASS" and (live == "FAIL" or historical == "FAIL"):
        notes.append("CONTRADICTION: PIT reconstruction PASS without both feeds")

    # Feed cadence versus hypothesis horizon: a verified cadence can fail a candidate
    # structurally, and that is a computation, not a judgement.
    cadence = venue.get("live_feed_min_interval_us") if venue else UNKNOWN
    horizon_min = candidate.get("horizon_min_us")
    cadence_verdict = "BLOCKED"
    if cadence is not UNKNOWN and horizon_min is not UNKNOWN:
        cadence_verdict = "FAIL" if horizon_min < cadence else "PASS"

    return {
        "candidate_id": feas["candidate_id"],
        "live_feed": live,
        "historical_feed": historical,
        "PIT_reconstructable": pit,
        "L1_available": feas["L1_available"],
        "L2_available": feas["L2_available"],
        "L3_available": l3,
        "queue_replay_possible": queue_replay,
        "timestamp_adequacy": feas["timestamp_adequacy"],
        "venue_live_feed_min_interval_us": cadence,
        "candidate_horizon_min_us": horizon_min,
        "cadence_vs_horizon": cadence_verdict,
        "depth_source_id": feas["depth_source_id"],
        "history_source_id": feas["history_source_id"],
        "PIT_source_id": feas["PIT_source_id"],
        "timestamp_source_id": feas["timestamp_source_id"],
        "feasibility_note": feas["feasibility_note"],
        "consistency_note": "; ".join(notes) if notes else "NO_CONTRADICTION_DETECTED",
    }
