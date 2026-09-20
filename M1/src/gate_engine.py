"""Computed kill-gate engine (handoff §13, §15).

Gate verdicts are computed from evidence-bearing inputs, not authored per candidate. The
M1-A artifact's original vectors are retained as `KG*_M1A` columns for audit, and every
divergence is reported in `M1/output/status_derivation_review.csv` with the rule that caused
it.

Revised M1 semantics (handoff §15) - what a PASS does NOT mean:

    KG1 mechanism       PASS = credible evidence the mechanism exists on this venue/instrument
                              and justifies quantitative testing. NOT proof of profitability.
    KG2 data            PASS = required data identified, plausibly obtainable, adequate
                              granularity, timestamp semantics supportive, no known fatal
                              limitation. NOT data already purchased.
    KG3 execution       PASS = known mechanics and costs do not already invalidate the thesis,
                              the execution style is physically plausible, and remaining
                              execution unknowns have explicit M2 measurement plans.
                              NOT fills or profitability measured.
    KG4 horizon         PASS = no known physical timing contradiction and a preregistered
                              EV(delay) experiment exists. NOT the empirical half-life.
    KG5 falsifiability  PASS = exact M2 nulls, data requirements, metric and kill criteria are
                              specifiable before results are seen.

Rule ids are stable and appear in every verdict so a reader can audit which rule decided it.
"""

from __future__ import annotations

from corpus.constants import GATE_IDS

UNKNOWN = None

QUEUE_DEPENDENT = ("MECH-QIMB", "MECH-QDEP")
PATIENT_STYLES = ("PASSIVE", "MIXED")

NON_TUPLE_CLASSES = ("UNIVERSE_DEFINITION", "METHOD_RULE", "GOVERNANCE",
                     "TECHNOLOGY_ADMISSION")

# Mechanism classes whose historical evaluation requires individual-order (queue-capable) data.
SPEC_IDS = ("EV_DELAY_SWEEP", "PASSIVE_FILL_MODEL", "FILL_CONDITIONED_MARKOUT",
            "LIVE_LATENCY", "COST_SENSITIVITY", "CAPACITY", "SYSTEM_ONE_INCREMENTAL_UTILITY")


def _split(value):
    if value is UNKNOWN or value == "":
        return []
    return [x for x in str(value).split("|") if x]


def _is_unspecified(text) -> bool:
    return "UNSPECIFIED" in str(text).upper()


def _support(evidence_rows, candidate):
    """Venue-specific supporting evidence at consensus/supported-finding strength."""
    out = []
    for row in evidence_rows:
        if row["supports_or_weakens"] != "SUPPORTS":
            continue
        if row["epistemic_class"] not in ("CONSENSUS_FACT", "SUPPORTED_FINDING"):
            continue
        if candidate["candidate_id"] not in _split(row["candidate_ids"]):
            continue
        if row["venue_id"] == candidate["venue_id"]:
            out.append(row["evidence_id"])
    return out


def _contradicted_by_strong_evidence(evidence_rows, candidate) -> list:
    """Records that explicitly contradict the candidate's *mechanism*.

    A record weakens a candidate for reasons that are not mechanism contradictions (data
    scope, fee level, feed cadence, procurement cost). Only records authored as
    ``contradicts_mechanism = YES`` - i.e. negative replications or structural disproofs - may
    influence KG1. Inferring a mechanism contradiction from ``supports_or_weakens`` alone would
    silently convert a procurement fact into a scientific verdict.
    """
    out = []
    for row in evidence_rows:
        if str(row.get("contradicts_mechanism", "NO")).upper() != "YES":
            continue
        if candidate["candidate_id"] in _split(row["candidate_ids"]):
            out.append(row["evidence_id"])
    return out


class Verdict:
    __slots__ = ("value", "rule", "reason")

    def __init__(self, value, rule, reason):
        self.value = value
        self.rule = rule
        self.reason = reason

    def as_dict(self):
        return {"value": self.value, "rule": self.rule, "reason": self.reason}


def kg1_mechanism(candidate, evidence_rows) -> Verdict:
    if candidate["candidate_class"] in ("GOVERNANCE", "TECHNOLOGY_ADMISSION"):
        return Verdict("FAIL", "KG1-R1",
                       "Admission-policy boundary: no evidenced economic mechanism is claimed "
                       "for this row, so no mechanism test exists to pass.")
    support = _support(evidence_rows, candidate)
    contrary = _contradicted_by_strong_evidence(evidence_rows, candidate)
    if support and not contrary:
        return Verdict("PASS", "KG1-R2",
                       f"Venue-specific supporting evidence exists ({', '.join(support)}) and no "
                       f"supported-finding record contradicts the mechanism. This justifies "
                       f"quantitative testing; it is not evidence of net edge.")
    if contrary:
        return Verdict("BLOCKED", "KG1-R3",
                       f"An explicit mechanism contradiction exists ({', '.join(contrary)}); "
                       f"mechanism credibility needs a venue-specific replication before it can "
                       f"pass.")
    return Verdict("BLOCKED", "KG1-R4",
                   "No venue-specific evidence that the mechanism operates on this "
                   "venue/instrument. Borrowed evidence from another market is an "
                   "extrapolation and cannot pass KG1.")


def kg2_data(candidate, feas, venue) -> Verdict:
    if feas is UNKNOWN:
        return Verdict("BLOCKED", "KG2-R0", "No data-feasibility assessment authored for this row.")
    cadence = feas.get("cadence_vs_horizon")
    if cadence == "FAIL":
        return Verdict("FAIL", "KG2-R1",
                       f"Verified feed interval {feas.get('venue_live_feed_min_interval_us')} us "
                       f"exceeds the hypothesis horizon floor "
                       f"{feas.get('candidate_horizon_min_us')} us: the observation loop cannot "
                       f"run at the hypothesised horizon.")
    if feas["historical_feed"] == "FAIL":
        return Verdict("FAIL", "KG2-R2",
                       "The only historical product available for this row's stated requirement "
                       "is structurally insufficient, so causal replay is impossible as written.")
    queue_mech = any(m in QUEUE_DEPENDENT for m in _split(candidate["mechanism_id"]))
    if queue_mech and feas["queue_replay_possible"] == "FAIL":
        return Verdict("FAIL", "KG2-R3",
                       "Mechanism requires individual-order queue state, which the available "
                       "data cannot reconstruct.")
    missing = [k for k in ("live_feed", "historical_feed", "PIT_reconstructable",
                           "timestamp_adequacy") if feas[k] != "PASS"]
    if missing:
        return Verdict("BLOCKED", "KG2-R4",
                       f"Data adequacy not established: {', '.join(missing)} are not verified."
                       + ("" if not queue_mech else
                          " A queue-dependent mechanism additionally needs order-level history."))
    if queue_mech and feas["L3_available"] != "PASS":
        return Verdict("BLOCKED", "KG2-R5",
                       "Queue-dependent mechanism with order-level data availability unverified.")
    return Verdict("PASS", "KG2-R6",
                   "Required live and historical data are identified as obtainable with adequate "
                   "granularity, PIT reconstruction and timestamp semantics. Acquisition itself "
                   "is not required for a KG2 pass.")


def kg3_execution(candidate, envelope, feas, venue, specs, kg1_value=UNKNOWN) -> Verdict:
    if candidate["candidate_class"] in NON_TUPLE_CLASSES and envelope is not UNKNOWN:
        pass  # non-tuple rows still carry a cost envelope shape; handled by KG3-R1 below
    if envelope is UNKNOWN:
        return Verdict("BLOCKED", "KG3-R0", "No cost envelope exists for this row.")
    if candidate["candidate_class"] in ("GOVERNANCE", "TECHNOLOGY_ADMISSION"):
        return Verdict("FAIL", "KG3-R1",
                       "Admission-policy boundary: the row asserts a technology capability that "
                       "is unmeasured and barred from the execution path by policy.")
    floor = envelope["required_round_trip_fee_bps_for_style"]
    support = _support_evidence_ids(candidate, envelope)
    if kg1_value == "FAIL":
        return Verdict("FAIL", "KG3-R2", "Mechanism gate already fails for this row.")
    if floor is not UNKNOWN and not support:
        return Verdict("BLOCKED", "KG3-R3",
                       f"Verified round-trip fee floor of {floor:.1f} bps and no venue-specific "
                       f"gross-effect evidence. Whether that floor is material cannot be decided "
                       f"from the evidence package: it needs either a documented materiality "
                       f"bound for this mechanism class or a venue-specific after-cost "
                       f"replication (UNK-0009). A cost level alone is not a kill: the kills "
                       f"recorded in the dead ledger were decisions with stated reasoning, not "
                       f"emergent arithmetic.")
    if floor is UNKNOWN:
        return Verdict("BLOCKED", "KG3-R4",
                       "No verified fee component exists for this venue, so the platform cannot "
                       "assert that known costs do not already invalidate the thesis. Known "
                       "mandatory cost is an M1 fact (UNK-0001/0005/0011/0012/0013/0022/0028).")
    style = candidate["execution_style"]
    matching_locked = venue is not UNKNOWN and venue.get("matching_algorithm_status") in (
        "LOCKED", "PUBLISHED")
    queue_mech = any(m in QUEUE_DEPENDENT for m in _split(candidate["mechanism_id"]))
    if (style in PATIENT_STYLES or queue_mech) and not matching_locked:
        return Verdict("BLOCKED", "KG3-R5",
                       "Queue-linked execution with an unresolved matching/allocation rule: the "
                       "fill model cannot be shown to be valid (UNK-0002).")
    if feas is not UNKNOWN and feas.get("cadence_vs_horizon") == "FAIL":
        return Verdict("FAIL", "KG3-R6",
                       "Execution horizon is physically unreachable on the available feed.")
    if not specs:
        return Verdict("BLOCKED", "KG3-R7",
                       "No preregistered M2 measurement plan exists for the remaining execution "
                       "unknowns.")
    return Verdict("PASS", "KG3-R8",
                   "Known venue mechanics and costs do not invalidate the thesis, the execution "
                   "style is physically plausible, and every remaining execution unknown has a "
                   "preregistered M2 plan.")


def _support_evidence_ids(candidate, envelope) -> list:
    """Support identity is carried on the candidate row by the materialiser (see gate_inputs)."""
    return _split(candidate.get("_venue_specific_support_ids"))


def kg4_horizon(candidate, feas, specs) -> Verdict:
    if feas is not UNKNOWN and feas.get("cadence_vs_horizon") == "FAIL":
        return Verdict("FAIL", "KG4-R1",
                       "Verified feed cadence is slower than the hypothesis horizon: a physical "
                       "timing contradiction, not a missing measurement.")
    if candidate["horizon_min_us"] is UNKNOWN:
        return Verdict("BLOCKED", "KG4-R2",
                       "Horizon is not banded, so no timing comparison is possible.")
    if "EV_DELAY_SWEEP" not in specs:
        return Verdict("BLOCKED", "KG4-R3",
                       "No preregistered EV(delay) experiment exists, so the horizon claim could "
                       "not be tested even if funded.")
    return Verdict("PASS", "KG4-R4",
                   "No known physical timing contradiction, and the delay experiment is "
                   "preregistered. The empirical half-life is an M2 output by design "
                   "(UNK-0008), not an M1 requirement.")


def kg5_falsifiability(candidate) -> Verdict:
    if candidate["candidate_class"] in NON_TUPLE_CLASSES:
        return Verdict("FAIL", "KG5-R1",
                       "Not a valid unit of analysis: a universe definition, method rule, "
                       "governance boundary or technology admission cannot carry a measurable "
                       "outcome. A reformulation is a new candidate.")
    if _is_unspecified(candidate["instrument"]) and candidate["candidate_class"] == "TUPLE":
        return Verdict("BLOCKED", "KG5-R2",
                       "Instrument is a family rather than an exact contract/symbol, so no "
                       "measurable outcome can be attributed (UNK-0027).")
    if candidate["horizon_min_us"] is UNKNOWN and candidate["candidate_class"] == "TUPLE":
        return Verdict("BLOCKED", "KG5-R3", "Horizon is not banded, so no test horizon exists.")
    if candidate["mechanism_id"] is UNKNOWN and candidate["candidate_class"] == "TUPLE":
        return Verdict("BLOCKED", "KG5-R4", "No mechanism is named, so no mechanism test exists.")
    return Verdict("PASS", "KG5-R5",
                   "Exact nulls, dataset requirements, metric and kill criteria are specifiable "
                   "before results are observed.")


def compute(candidates, evidence_rows, feas_by_id, envelope_by_id, venue_by_id, specs_by_id):
    """Compute every gate for every candidate, with rule traces."""
    out = {}
    for cand in candidates:
        cid = cand["candidate_id"]
        cand = dict(cand)
        cand["_venue_specific_support_ids"] = "|".join(_support(evidence_rows, cand))
        feas = feas_by_id.get(cid, UNKNOWN)
        envelope = envelope_by_id.get(cid, UNKNOWN)
        venue = venue_by_id.get(cand["venue_id"], UNKNOWN)
        specs = specs_by_id.get(cid, [])
        v1 = kg1_mechanism(cand, evidence_rows)
        v2 = kg2_data(cand, feas, venue)
        v3 = kg3_execution(cand, envelope, feas, venue, specs, kg1_value=v1.value)
        v4 = kg4_horizon(cand, feas, specs)
        v5 = kg5_falsifiability(cand)
        cand["KG1_MECHANISM"], cand["KG2_DATA"] = v1, v2
        cand["KG3_EXECUTION"], cand["KG4_HALF_LIFE"] = v3, v4
        cand["KG5_FALSIFIABILITY"] = v5
        out[cid] = cand
    return out


def gate_counts(computed) -> dict:
    counts = {}
    for gate in GATE_IDS:
        bucket = {"PASS": 0, "BLOCKED": 0, "FAIL": 0}
        for cand in computed.values():
            bucket[cand[gate].value] += 1
        counts[gate] = bucket
    return counts


def eligible(computed) -> list:
    return sorted(cid for cid, cand in computed.items()
                  if all(cand[g].value == "PASS" for g in GATE_IDS))