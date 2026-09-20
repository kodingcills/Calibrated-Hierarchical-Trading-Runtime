"""Hard-constraint elimination and the dominance analysis that is *not* performed.

Hard eliminations are allowed because each one rests on a verified fact plus a mechanism
statement (handoff D0.6). No weighting, scoring or averaging is used anywhere in this module.

``HC1_FEE_FLOOR_WITHOUT_GROSS_EVIDENCE`` deserves an explicit statement of what it does and
does not claim. It fires when a candidate has a *verified* round-trip fee floor for its named
execution style and no venue-specific supporting evidence at consensus/supported-finding
strength. It therefore asserts: "this hypothesis needs a gross effect the evidence package
does not contain, to clear a cost that is verified." It does not assert a measured bound on
the size of the gross effect, and it is reported as an evidence-absence elimination so it can
be reversed by a single supporting venue-specific measurement.
"""

from __future__ import annotations

UNKNOWN = None

QUEUE_DEPENDENT_MECHANISMS = ("MECH-QIMB", "MECH-QIMB")

NOT_EVALUATED = "NOT_EVALUATED_UNKNOWN_DIMENSIONS"


def _split(ids) -> list:
    if ids is UNKNOWN or ids == "":
        return []
    return [x for x in str(ids).split("|") if x]


def _mechanisms(cand) -> list:
    return _split(cand["mechanism_id"])


def venue_specific_support(cand, evidence_rows) -> list:
    """Supporting evidence that actually names this candidate's venue."""
    out = []
    for row in evidence_rows:
        if row["supports_or_weakens"] != "SUPPORTS":
            continue
        if row["epistemic_class"] not in ("CONSENSUS_FACT", "SUPPORTED_FINDING"):
            continue
        if cand["candidate_id"] not in _split(row["candidate_ids"]):
            continue
        if row["venue_id"] == cand["venue_id"]:
            out.append(row["evidence_id"])
    return out


def hard_constraint_checks(cand, feas, evidence_rows, required_round_trip_fee_bps,
                           expected_gross_edge_bps=UNKNOWN):
    """Return a list of elimination records; empty means the candidate survives hard facts."""
    out = []
    cid = cand["candidate_id"]
    cls = cand["candidate_class"]

    # HC4/HC5/HC6: registration-class eliminations.
    if cls == "UNIVERSE_DEFINITION":
        out.append(dict(rule="HC4_UNIVERSE_DEFINITION", verdict="ELIMINATED",
                        basis="Named unit of analysis is not a valid candidate",
                        detail="Fees, data mechanics and matching differ materially inside the "
                               "named universe, so no measurable outcome can be attributed.",
                        source_id="SRC-0011"))
    if cls == "METHOD_RULE":
        out.append(dict(rule="HC5_METHOD_RULE", verdict="ELIMINATED",
                        basis="Not a strategy; a fill assumption",
                        detail="touch=fills omits queue position and adverse selection, so it "
                               "cannot answer the economic question.",
                        source_id="SRC-0011"))
    if cls in ("GOVERNANCE", "TECHNOLOGY_ADMISSION"):
        out.append(dict(rule="HC6_GOVERNANCE_OR_TECHNOLOGY_ADMISSION", verdict="ELIMINATED",
                        basis="Admission-policy boundary, not a tradable hypothesis",
                        detail="Entry is barred by project policy or by an unmeasured technology "
                               "premise, not by market evidence.",
                        source_id="SRC-0015|SRC-0011"))

    # HC7: a failing execution gate is already a hard fact.
    if cand["KG3_EXECUTION"] == "FAIL":
        out.append(dict(rule="HC7_EXECUTION_GATE_FAIL", verdict="ELIMINATED",
                        basis="KG3_EXECUTION = FAIL",
                        detail="The execution envelope is evidenced as unworkable as stated.",
                        source_id="SRC-0026"))
    if cand["KG5_FALSIFIABILITY"] == "FAIL":
        out.append(dict(rule="HC8_FALSIFIABILITY_GATE_FAIL", verdict="ELIMINATED",
                        basis="KG5_FALSIFIABILITY = FAIL",
                        detail="No pre-registerable falsifier can be written for this row. "
                               "A reformulation is a new candidate.",
                        source_id="SRC-0026"))

    # HC2: verified feed cadence slower than the hypothesis horizon.
    cadence = None
    if feas is not UNKNOWN:
        cadence = feas.get("venue_live_feed_min_interval_us")
    if cadence is not UNKNOWN and cand["horizon_min_us"] is not UNKNOWN:
        if cand["horizon_min_us"] < cadence:
            out.append(dict(rule="HC2_FEED_CADENCE_VS_HORIZON", verdict="ELIMINATED",
                            basis=f"verified feed interval {cadence} us > horizon floor "
                                  f"{cand['horizon_min_us']} us",
                            detail="The observation loop cannot run at the hypothesised horizon.",
                            source_id="SRC-0111"))

    # HC3: mechanism requires queue reconstruction that the data layer cannot support.
    if feas is not UNKNOWN and feas.get("queue_replay_possible") == "FAIL":
        if any(m in QUEUE_DEPENDENT_MECHANISMS for m in _mechanisms(cand)):
            out.append(dict(rule="HC3_QUEUE_REPLAY_UNSUPPORTED", verdict="ELIMINATED",
                            basis="queue reconstruction is a verified FAIL for this data layer",
                            detail="Queue-dependent mechanism cannot be evaluated on the available "
                                   "history.",
                            source_id="SRC-0109|SRC-0111"))

    # HC1: a verified fee floor eliminates only when a *sourced* bound on the plausible gross
    # effect shows the floor cannot be cleared. A cost level by itself is not a kill (D-0022), so
    # this rule now requires the bound as an input and cannot fire without one.
    if required_round_trip_fee_bps is not UNKNOWN and expected_gross_edge_bps is not UNKNOWN:
        if expected_gross_edge_bps < required_round_trip_fee_bps:
            out.append(dict(
                rule="HC1_FEE_FLOOR_EXCEEDS_SOURCED_GROSS_BOUND", verdict="ELIMINATED",
                basis=f"verified round-trip fee floor {required_round_trip_fee_bps:.1f} bps "
                      f"exceeds the sourced gross-effect bound {expected_gross_edge_bps:.1f} bps",
                detail="Materiality mismatch: the cost floor is above a documented upper bound on "
                       "the achievable gross effect, so the branch cannot clear its own costs.",
                source_id="SRC-0105|SRC-0106|SRC-0026"))

    return out


def survivors(candidates, feasibility_by_id, evidence_rows, fee_floor_by_id):
    """Partition candidates into hard-constraint survivors and eliminations."""
    kept, killed = [], []
    for cand in candidates:
        cid = cand["candidate_id"]
        checks = hard_constraint_checks(
            cand, feasibility_by_id.get(cid, UNKNOWN), evidence_rows,
            fee_floor_by_id.get(cid, UNKNOWN))
        if checks:
            killed.append({"candidate_id": cid, "checks": checks})
        else:
            kept.append(cand)
    return kept, killed


def survivor_rows(kept, candidates_by_id):
    rows = []
    for cand in kept:
        cid = cand["candidate_id"]
        rows.append({
            "candidate_id": cid,
            "candidate_class": cand["candidate_class"],
            "venue_id": cand["venue_id"],
            "horizon_band": cand["horizon_band"],
            "mechanism_id": cand["mechanism_id"],
            "execution_style": cand["execution_style"],
            "overall_status": cand["overall_status"],
            "status_ceiling": "NOT_ALIVE" if any(
                cand[g] == "BLOCKED" for g in
                ("KG1_MECHANISM", "KG2_DATA", "KG3_EXECUTION", "KG4_HALF_LIFE",
                 "KG5_FALSIFIABILITY")) else "ELIGIBLE_FOR_M1B",
            "passed_hard_constraints": "HC1|HC2|HC3|HC4|HC5|HC6|HC7|HC8",
            "blocking_issue_ids": cand["blocking_issue_ids"],
            "why_not_alive": "At least one gate is BLOCKED: no candidate has all five gates PASS "
                             "on cited evidence.",
        })
    return rows


def elimination_rows(killed):
    rows = []
    for entry in killed:
        for check in entry["checks"]:
            rows.append({"candidate_id": entry["candidate_id"], **check})
    return rows


def dominance_rows(candidates):
    """Dominance is not computed: state that explicitly rather than scoring UNKNOWNs.

    Two candidate rows can only be compared on dimensions that are both measured. At the
    current evidence state the shared measured dimensions are: the verified fee facts (3
    venue rows), the verified feed cadence (1 venue) and verified data-product scope (2
    products). Every economic, execution and lifetime dimension is UNKNOWN for every
    candidate, so a Pareto frontier would be a frontier over missing values.
    """
    rows = []
    for cand in candidates:
        rows.append({
            "candidate_id": cand["candidate_id"],
            "dominance_status": NOT_EVALUATED,
            "comparable_measured_dimensions": "verified_fee_unit_values|verified_feed_cadence|"
                                              "verified_data_product_scope",
            "unknown_dimensions": "mechanism_credibility|evidence_quality|observability|"
                                  "data_feasibility|execution_feasibility|net_edge_headroom|"
                                  "signal_longevity|capacity|capital_efficiency|"
                                  "simulation_feasibility|regime_robustness|"
                                  "operational_complexity|regulatory_burden",
            "reason": "Pareto analysis requires every compared dimension to be measured for both "
                      "candidates. The decision-critical dimensions are UNKNOWN for all candidates, "
                      "so no dominance statement is made and no UNKNOWN is scored as an average.",
            "pareto_status": "NOT_EVALUATED",
        })
    return rows


DOMINANCE_NOTE = (
    "Dominated/dominated-set analysis was NOT performed. At this evidence state every "
    "decision-critical dimension (net-edge headroom, signal longevity, fill quality, capacity, "
    "capital efficiency) is UNKNOWN for every candidate, so any frontier would order missing "
    "values. The only eliminations applied are hard constraints backed by verified facts "
    "(HC1..HC8). Re-run this analysis in M1-D1 once M1-B has emitted a CURRENT synthesis "
    "artifact and the blocking issues are resolved.")