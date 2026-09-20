"""Kill-gate computation and the status ceiling.

The ceiling rule (ASM-0008) is mechanical:

    any FAIL            -> DEAD
    else any BLOCKED    -> NOT_ALIVE (cannot be ALIVE; WEAK or UNKNOWN per the M1-A label)
    else all PASS       -> ELIGIBLE_FOR_M1B

``overall_status`` is the M1-A judgment for a not-yet-dead candidate; the ceiling exists so
no judgment can promote a candidate past the gates it actually passed.
"""

from __future__ import annotations

from corpus.constants import GATE_IDS

UNKNOWN = None

DEAD = "DEAD"
WEAK = "WEAK"
UNKNOWN_STATUS = "UNKNOWN"
ALIVE = "ALIVE"

_CEILING_FOR_STATUS = {
    DEAD: DEAD,
    WEAK: "NOT_ALIVE",
    UNKNOWN_STATUS: "NOT_ALIVE",
    ALIVE: "ELIGIBLE_FOR_M1B",
}


def gate_vector(candidate: dict) -> dict:
    return {gate: candidate[gate] for gate in GATE_IDS}


def status_ceiling(candidate: dict) -> str:
    """Highest status the gate vector permits, ignoring the M1-A label."""
    gates = gate_vector(candidate)
    if any(v == "FAIL" for v in gates.values()):
        return DEAD
    if any(v == "BLOCKED" for v in gates.values()):
        return "NOT_ALIVE"
    return "ELIGIBLE_FOR_M1B"


def ceiling_violations(candidates) -> list:
    """Return (candidate_id, status, ceiling, message) for every status/ceiling conflict."""
    problems = []
    for cand in candidates:
        ceiling = status_ceiling(cand)
        status = cand["overall_status"]
        if status not in _CEILING_FOR_STATUS:
            problems.append((cand["candidate_id"], status, ceiling,
                             "unknown overall_status value"))
            continue
        if _CEILING_FOR_STATUS[status] == DEAD and ceiling != DEAD and status == DEAD:
            problems.append((cand["candidate_id"], status, ceiling,
                             "DEAD without any FAIL gate"))
        if status == ALIVE and ceiling != "ELIGIBLE_FOR_M1B":
            problems.append((cand["candidate_id"], status, ceiling,
                             "ALIVE with a blocking or failing gate"))
        if status in (WEAK, UNKNOWN_STATUS) and ceiling == DEAD:
            problems.append((cand["candidate_id"], status, ceiling,
                             "non-DEAD status with a FAIL gate"))
    return problems


def gate_status_rows(candidates) -> list:
    rows = []
    for cand in candidates:
        rows.append({
            "candidate_id": cand["candidate_id"],
            "candidate_class": cand["candidate_class"],
            "KG1_MECHANISM": cand["KG1_MECHANISM"],
            "KG2_DATA": cand["KG2_DATA"],
            "KG3_EXECUTION": cand["KG3_EXECUTION"],
            "KG4_HALF_LIFE": cand["KG4_HALF_LIFE"],
            "KG5_FALSIFIABILITY": cand["KG5_FALSIFIABILITY"],
            "overall_status": cand["overall_status"],
            "status_ceiling": status_ceiling(cand),
            "blocking_issue_ids": cand["blocking_issue_ids"],
        })
    return rows


def gate_counts(candidates) -> dict:
    """Per-gate counts of PASS/BLOCKED/FAIL across candidates, for the kill_gates registry."""
    out = {}
    for gate in GATE_IDS:
        counts = {"PASS": 0, "BLOCKED": 0, "FAIL": 0}
        for cand in candidates:
            counts[cand[gate]] += 1
        out[gate] = counts
    return out


def status_counts(candidates) -> dict:
    """Candidate counts split by class, because tuples and non-tuple rows are not comparable."""
    out = {}
    for cand in candidates:
        cls = cand["candidate_class"]
        bucket = out.setdefault(cls, {"total": 0, ALIVE: 0, WEAK: 0,
                                      UNKNOWN_STATUS: 0, DEAD: 0})
        bucket["total"] += 1
        bucket[cand["overall_status"]] += 1
    total = {"total": 0, ALIVE: 0, WEAK: 0, UNKNOWN_STATUS: 0, DEAD: 0}
    for bucket in out.values():
        for key in total:
            total[key] += bucket[key]
    out["ALL"] = total
    return out


def m1b_eligible(candidates) -> list:
    """Candidates whose gates would permit M1-B comparison (none expected at this state)."""
    return [c["candidate_id"] for c in candidates if status_ceiling(c) == "ELIGIBLE_FOR_M1B"]
