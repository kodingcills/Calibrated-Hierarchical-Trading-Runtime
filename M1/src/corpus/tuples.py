"""Candidate tuples and registered pseudo-candidates (TUP-*).

Twenty-two rows are the M1-A tuple ledger (SRC-0011). Six further rows are the
non-tuple entries the same artifact killed in its dead-candidate cemetery
(method rules, universe definitions, governance and technology admissions). Those are
registered with an explicit ``candidate_class`` so that "candidate count" never silently
mixes a tradable tuple with a governance rule.

Gate semantics (ASM-0008):
    FAIL    evidence shows the requirement cannot be met for this candidate as stated
    BLOCKED the requirement cannot be judged yet: missing evidence, not missing reality
    PASS    the requirement is met on cited evidence
Status ceiling: any FAIL forces DEAD; any BLOCKED forbids ALIVE. ``overall_status`` is
the M1-A judgment for a not-yet-dead candidate (WEAK vs UNKNOWN), recorded with an
explicit ``status_basis`` so the judgment is auditable rather than implicit.
"""

from .constants import UNKNOWN

COLUMNS = [
    "candidate_id", "candidate_class", "instrument", "venue_id", "horizon_band",
    "horizon_min_us", "horizon_max_us", "horizon_taxonomy_source_id",
    "mechanism_id", "execution_style",
    "required_data", "competitive_vector", "observability_status",
    "economic_mechanism_status", "data_status", "execution_status", "half_life_status",
    "persistence_status", "technology_status",
    "KG1_MECHANISM", "KG2_DATA", "KG3_EXECUTION", "KG4_HALF_LIFE", "KG5_FALSIFIABILITY",
    "overall_status", "status_source_id", "status_basis",
    "blocking_issue_ids", "blocking_issue_ids_declared", "kill_gate", "kill_reason",
    "resurrection_condition", "kill_status", "kill_superseded_by",
    "report_row_ref", "notes", "unknown_fields",
]

# Kills withdrawn under the current methodology (handoff §8). A recorded kill must satisfy the
# rules in force now, not the rules in force when it was made. Each row states the hypothesised
# mechanism and horizon, the verified fee floor, whether any sourced bound on the plausible gross
# effect exists, the original rationale, and the resulting state.
KILL_SUPERSESSIONS = [
    {
        "candidate_id": "TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG",
        "mechanism_id": "MECH-MICRO|MECH-OFI", "horizon_band": "H3",
        "fee_floor": "120 bps round trip (2 x 60 bps taker at the 0-10k tier), verified (SRC-0105)",
        "materiality_bound": "NONE FOUND",
        "original_rationale": "60 bps taker per fill gives 120 bps round-trip exchange trading fees "
                              "before spread/slippage/adverse selection; no venue-specific evidence "
                              "establishes the required seconds-scale gross edge.",
        "verdict": "SUPERSEDED",
        "superseding_decision": "DECISIONS D-0022 and D-0026",
        "reason": "The rationale is an evidence-absence argument at a cost level. Under D-0022 a "
                  "concentration of cost is not a kill absent a sourced bound on the plausible "
                  "gross effect, and no such bound exists for seconds-scale crypto spot signals. "
                  "The death is withdrawn rather than preserved on a pre-D-0022 rule.",
        "resulting_state": "Gate-derived: KG3 BLOCKED (verified floor, no venue-specific "
                           "gross-effect evidence); candidate returns to the not-dead set.",
        "re_kill_condition": "A documented upper bound on plausible seconds-scale gross movement "
                             "on this venue that sits below the verified floor resolves it as a "
                             "kill; that evidence need is registered as UNK-0009-ECON-CRYPTO-SPOT.",
    },
    {
        "candidate_id": "TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG",
        "mechanism_id": "MECH-MICRO|MECH-OFI", "horizon_band": "H3",
        "fee_floor": "160 bps round trip (2 x 80 bps taker at Tier 1), verified (SRC-0106)",
        "materiality_bound": "NONE FOUND",
        "original_rationale": "0.80% taker per fill implies 1.60% round-trip before all other "
                              "costs at Tier 1.",
        "verdict": "SUPERSEDED",
        "superseding_decision": "DECISIONS D-0022 and D-0026",
        "reason": "Same defect as the Coinbase row: a cost level with no sourced materiality bound.",
        "resulting_state": "Gate-derived: KG3 BLOCKED (verified floor, no venue-specific "
                           "gross-effect evidence); candidate returns to the not-dead set.",
        "re_kill_condition": "As above: a documented materiality bound (UNK-0009-ECON-CRYPTO-SPOT).",
    },
]

# Verbatim kill-gate wording from the M1-A dead-candidate cemetery (SRC-0011), kept next to
# the mapped gate so the mapping can be audited rather than trusted.
REPORT_KILL_GATE = {
    "TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG": "Execution envelope",
    "TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG": "Execution envelope",
    "TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS": "Data feasibility / compute-fit boundary",
    "TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG": "Data feasibility",
    "TUP-METHOD-PASSIVE-TOUCHFILL": "Execution integrity",
    "TUP-GENERIC-CRYPTO-MICRO": "Universe-definition gate",
    "TUP-GENERIC-CME-QUEUE": "Market-structure definition",
    "TUP-SYSTEMONE-HARDCORE-ENGINE": "Project admission policy",
    "TUP-JEV-HOSTED-LATENCY-UNMEASURED": "Technology admission",
    # Not from the cemetery: this row's kill is the project's own M2 measurement, so the verbatim
    # column records that fact rather than a report phrasing that does not exist.
    "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG": "M2 measured execution economics (no M1-A cemetery row)",
    "TUP-NASDAQ-LARGETICK-H2-QIMB-PAS": "M2 measured passive-execution economics (no M1-A "
                                        "cemetery row)",
}

ROWS = []


def add(candidate_id, candidate_class, instrument, venue_id, horizon_band, mechanism_id,
        execution_style, required_data, competitive_vector, observability_status,
        persistence_status, technology_status, gates, overall_status, status_basis,
        blocking_issue_ids, report_row_ref, kill_gate=UNKNOWN, kill_reason=UNKNOWN,
        resurrection_condition=UNKNOWN, notes=UNKNOWN):
    kg1, kg2, kg3, kg4, kg5 = gates
    ROWS.append(dict(
        candidate_id=candidate_id,
        candidate_class=candidate_class,
        instrument=instrument,
        venue_id=venue_id,
        horizon_band=horizon_band,
        mechanism_id=mechanism_id,
        execution_style=execution_style,
        required_data=required_data,
        competitive_vector=competitive_vector,
        observability_status=observability_status,
        persistence_status=persistence_status,
        technology_status=technology_status,
        KG1_MECHANISM=kg1,
        KG2_DATA=kg2,
        KG3_EXECUTION=kg3,
        KG4_HALF_LIFE=kg4,
        KG5_FALSIFIABILITY=kg5,
        overall_status=overall_status,
        status_source_id="SRC-0011",
        status_basis=status_basis,
        blocking_issue_ids=blocking_issue_ids,
        kill_gate=kill_gate,
        kill_reason=kill_reason,
        resurrection_condition=resurrection_condition,
        kill_status=("SUPERSEDED"
                     if candidate_id in {r["candidate_id"] for r in KILL_SUPERSESSIONS}
                     else (UNKNOWN if overall_status != "DEAD" else "ACTIVE")),
        kill_superseded_by=next((r["superseding_decision"] for r in KILL_SUPERSESSIONS
                                 if r["candidate_id"] == candidate_id), UNKNOWN),
        report_row_ref=report_row_ref,
        notes=notes,
    ))


_B = "BLOCKED"
_P = "PASS"
_F = "FAIL"

# ------------------------------------------------------------------ CME tuples
add("TUP-CME-ES-H1-QDEP-PAS", "TUPLE", "ES (E-mini S&P 500 future)", "VEN-CME-ES", "H1",
    "MECH-QIMB", "PASSIVE",
    "Full-depth MBO (add/modify/delete/trade) with sequence numbers, security definitions, "
    "exchange and receive timestamps, own-order acknowledgements and fills",
    "Colocated market makers and queue-position specialists; own queue position determines whether "
    "a resting order ever fills",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "WEAK",
    "Mechanism class is supported in the published literature and live full-depth observability is "
    "verified (EVD-0001/EVD-0020), but the product matching rule, all-in cost, passive fill "
    "probability and delay-to-EV are all unknown and recorded as constraints (EVD-0003). The gate "
    "ceiling therefore forbids ALIVE.",
    "UNK-0001|UNK-0002|UNK-0003|UNK-0006|UNK-0007|UNK-0008|UNK-0016|UNK-0018",
    "SRC-0011 tuple ledger row 1")

add("TUP-CME-ES-H3-OFI-AGG", "TUPLE", "ES (E-mini S&P 500 future)", "VEN-CME-ES", "H3",
    "MECH-OFI", "AGGRESSIVE",
    "CME market data with trade prints and exchange timestamps (full depth not strictly required "
    "for an aggressive signal); own fill data with timestamps",
    "Cost- and latency-sensitive: the signal must exceed spread + fees + slippage; no queue "
    "advantage is claimed",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "UNKNOWN",
    "The OFI mechanism is evidenced in U.S. equities (EVD-0013) but that link is NEUTRAL for ES: "
    "transfer across venue and participant structure is an EXTRAPOLATION and no current ES "
    "replication exists. No evidence yet constrains ES specifically, so the tuple is UNKNOWN "
    "rather than WEAK.",
    "UNK-0001|UNK-0002|UNK-0006|UNK-0009|UNK-0016|UNK-0018",
    "SRC-0011 tuple ledger row 2")

add("TUP-CME-NQ-H3-OFI-AGG", "TUPLE", "NQ (E-mini Nasdaq-100 future)", "VEN-CME-NQ", "H3",
    "MECH-OFI", "AGGRESSIVE",
    "CME market data with trade prints and exchange timestamps; own fill data with timestamps",
    "Same cost/latency competition as ES H3; index-futures microstructure differs in tick and "
    "participant mix and must be measured separately",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Same cross-market extrapolation issue as the ES H3 tuple; no NQ-specific evidence exists in "
    "the M1-A package.",
    "UNK-0001|UNK-0002|UNK-0006|UNK-0009|UNK-0016|UNK-0018",
    "SRC-0011 tuple ledger row 3")

add("TUP-CME-TSY-H2-QREPL-MIX", "TUPLE",
    "Treasury future (exact contract UNSPECIFIED)", "VEN-CME-TSY", "H2-H3", "MECH-REPLEN", "MIXED",
    "Full-depth MBO/MBP with security definitions for the chosen contract, plus product-specific "
    "matching rule documentation",
    "Fixed-income futures have product-specific matching, including calendar-spread rules that CME "
    "has changed by notice (EVD-0003)",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _B), "UNKNOWN",
    "The replenishment mechanism is an EXTRAPOLATION from the order-flow literature, and the row "
    "does not name an exact contract, so no cost, matching rule or falsifier can yet be pinned down.",
    "UNK-0001|UNK-0002|UNK-0003|UNK-0006|UNK-0009|UNK-0016|UNK-0018|UNK-0027",
    "SRC-0011 tuple ledger row 4")

add("TUP-CME-WTI-H4-FLOWVOL-AGG", "TUPLE", "WTI crude oil future (contract month UNSPECIFIED)",
    "VEN-CME-WTI", "H4", "MECH-VOLREG", "AGGRESSIVE",
    "CME market data with trade prints, event/news timestamps and inventory/event calendars",
    "Energy futures respond to scheduled and unscheduled information events; competing "
    "participants include physical hedgers and macro funds",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "UNKNOWN",
    "No modern venue-specific edge evidence is locked and the economic payer is unstated; the "
    "volatility-transition mechanism is itself UNKNOWN in this package.",
    "UNK-0001|UNK-0002|UNK-0006|UNK-0009|UNK-0018|UNK-0027",
    "SRC-0011 tuple ledger row 5")

# --------------------------------------------------------------- Nasdaq tuples
add("TUP-NASDAQ-LARGETICK-H2-QIMB-AGG", "TUPLE", "Large-tick U.S. listed stock (symbol UNSPECIFIED)",
    "VEN-NASDAQ-CONT", "H2", "MECH-QIMB", "AGGRESSIVE",
    "TotalView-ITCH order events, executions and cancellations with timestamps; historical "
    "order-level data for validation; own fill data",
    "Crossing after imbalance selects into an already-moving price; the signal is public to anyone "
    "with the same feed",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _F, _B, _P), "DEAD",
    "KG3_EXECUTION fails on the project's own measured evidence (EVD-0067, patch P-0006): in the "
    "candidate's rule-conformant population the mean 1000 ms side-signed mid move is 0.0794 bps "
    "against a 4.1011 bps executed round trip, none of the 356 declared states is net-positive "
    "under the structural cost floor, and a clairvoyant trader on the same instants nets only "
    "0.219 bps per trade on the accessible broker path. Direct published support for the mechanism "
    "(EVD-0012) is unchanged and is why the same signal remains a live input to passive "
    "formulations; it is the aggressive execution style that fails.",
    "UNK-0004|UNK-0005|UNK-0006|UNK-0008|UNK-0009|UNK-0016|UNK-0018|UNK-0027",
    "SRC-0023 patch P-0006",
    kill_gate="KG3_EXECUTION",
    kill_reason="Aggressive execution cannot clear the tick-plus-fee friction: a measured signal of "
                "0.0794 bps against a 4.1011 bps round trip, with a measured clairvoyant ceiling of "
                "0.822 bps per trade at the structural floor and 0.219 bps per trade on the "
                "accessible reference path (M2-0-6-UNIVPROXY, freeze sha256 4fc098a3...c32b38b).",
    resurrection_condition="A rule-conformant modern measurement with a pooled required/signal "
                           "ratio at or below 5, which requires both a materially higher move scale "
                           "and a materially higher price level for the universe's names than the "
                           "measured 2019 session (M2/output/M2_AUTONOMOUS_STATUS.md).",
    notes="Killed by M2 evidence, not by an M1 inference: the experiment was designed to falsify "
          "the opposite hypothesis (that the M2-0 compute scope, rather than the mechanism, was the "
          "problem) and it rejected that hypothesis. Passive/queue monetization of the same signal "
          "is NOT killed by this record - it is untested and requires a queue-aware fill model "
          "(PASSIVE_FILL_MODEL, FILL_CONDITIONED_MARKOUT); it must be registered as its own "
          "candidate rather than as a mode change on this row.")

add("TUP-NASDAQ-LARGETICK-H2-QIMB-PAS", "TUPLE",
    "Large-tick U.S. listed stock (symbol UNSPECIFIED)", "VEN-NASDAQ-CONT", "H2", "MECH-QIMB",
    "PASSIVE",
    "TotalView-ITCH order events with per-order identity, so a displayed queue can be "
    "reconstructed causally; a queue-truth source (the project's own shadow orders) for "
    "validation; own fill data for reconciliation",
    "Queue position at the touch is the scarce resource: the signal is public, and the participant "
    "ahead of us in the queue is the competition",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_P, _B, _F, _P, _P), "DEAD",
    "KG3_EXECUTION fails on the project's own measured evidence (EVD-0069, patch P-0008): over "
    "the rule-conformant large-tick names, queue-aware passive orders fill on 6,067 of 737,768 "
    "attempts (0.82%) at a median 537 ms behind a median queue of 700 displayed shares, and the "
    "fills are adversely selected - the side-signed midpoint move from the fill is -0.97 bps at "
    "1000 ms (95% CI [-1.10, -0.87]) and -0.88 bps already at 10 ms, against an unconditional "
    "post-decision response of +0.079 bps (EVD-0067). The passive-entry/aggressive-exit "
    "reference policy is negative before any cost (-1.32 to -1.48 bps gross) and -2.02 bps per "
    "filled share net of the structural floor; no declared imbalance state and no queue-position "
    "band has positive expected value per attempt. The optimistic bound that grants perfect "
    "queue position agrees (4.30% fills, -1.02 bps midpoint markout, 0 of 5 states positive).",
    "UNK-0028",
    "M2-1-PASSIVE-QIMB freeze + M2/output/M2_PASSIVE_FEASIBILITY_STATUS.md",
    kill_gate="KG3_EXECUTION",
    kill_reason="Passive monetization fails on both sides of the queue-position trade-off: "
                "patient orders are rarely reached by flow inside the signal's own 1 s horizon "
                "(0.82% of attempts, median 537 ms), and orders reached immediately - the "
                "optimistic bound - are selected against by -1.02 bps of midpoint drift, more "
                "than the entry spread they earn. Measured deterministically on the 2019-07-30 "
                "development tape (M2-1-PASSIVE-QIMB, freeze sha256 03efd04e...).",
    resurrection_condition="A rule-conformant measurement with non-negative fill-conditioned "
                           "midpoint markout and queue reachability inside the signal's horizon, "
                           "or a materially different formulation registered as its own candidate "
                           "(passive exit, inventory, or venue liquidity-credit capture with an "
                           "always-resting baseline).",
    notes="Declared blockers are limited to the issues the registry attributes to this row; the "
          "shared universe, point-in-time-reference and broker-cost items (UNK-0004, UNK-0005, "
          "UNK-0018-NASDAQ, UNK-0027-NASDAQ-LARGETICK, UNK-0033) are registered against the parent "
          "aggressive row and were inherited by this pivot. Candidate lineage stays explicit: "
          "QIMB mechanism -> aggressive monetization (DEAD, "
          "EVD-0067) -> passive monetization hypothesis (this row, DEAD, EVD-0069). The two "
          "execution styles were measured on the same tape and fail for opposite reasons, which "
          "is why the H2 Nasdaq large-tick QIMB family is recorded as stopped rather than as a "
          "candidate with a remaining untested execution mode. The only non-negative "
          "configuration credits a venue add-liquidity rebate: that is an exchange subsidy, not "
          "the signal, and it would be a different candidate with an always-resting baseline.")

add("TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG", "TUPLE",
    "Large-tick U.S. listed stock (symbol UNSPECIFIED)", "VEN-NASDAQ-CONT", "H2-H3", "MECH-MICRO",
    "AGGRESSIVE",
    "TotalView-ITCH order events for book-state reconstruction; historical order-level data; own "
    "fill data",
    "The estimator must be converted into an execution decision that beats the OFI/logistic "
    "baseline on net utility, not on estimator error",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _F, _B, _P), "DEAD",
    "KG3_EXECUTION fails on the project's own measured evidence (EVD-0070, patch P-0009): the "
    "registered Stoikov first-step microprice direction (estimated with an expanding "
    "prior-session calibration that cannot see its own or any later observation) earns 0.2333 bps "
    "of side-signed mid move at the longest horizon the candidate declares (15000 ms, 95% CI "
    "[0.2142, 0.2530]) against a 3.9875 bps structural round trip (R = 17.09), and its strongest "
    "declared state - imbalance in [0.8,1.0] with a one-tick spread - earns 0.5836 bps on 2.98% of "
    "instants (R = 5.02). With perfect foresight of the future executable quotes the same instants "
    "yield only +1.6275 bps per trade at the structural floor (+0.7012 bps on the accessible "
    "broker path) on 19.51% of instants, so the candidate is limited by friction rather than by "
    "prediction quality. The estimator evidence in EVD-0014 is unchanged and is not contradicted: "
    "the information is present, weak and not executable.",
    "UNK-0004|UNK-0005|UNK-0006|UNK-0008|UNK-0009|UNK-0016|UNK-0018|UNK-0027",
    "SRC-0023 patch P-0009",
    kill_gate="KG3_EXECUTION",
    kill_reason="The registered microprice direction is real but economically immaterial on this "
                "population: 0.2333 bps pooled at 15000 ms (R = 17.09) and 0.5836 bps in the best "
                "declared state (R = 5.02) against a 3.9875 bps round trip, with a clairvoyant "
                "ceiling of 1.63 bps per trade at the fee floor. It is not an uplift on the "
                "queue-imbalance row at the shared horizon (0.0745 bps against 0.0794 bps at "
                "1000 ms). Measured over 282,229,684 messages on the 2019-07-30 development tape "
                "(M2-2-MICRO-MATERIALITY, freeze sha256 89f84b29...).",
    resurrection_condition="A rule-conformant measurement in which the pooled required/signal "
                           "ratio at the candidate's own horizon is at or below 5, which requires "
                           "a materially larger per-second move scale or a materially higher price "
                           "level for the universe's names than the measured 2019 session; or a "
                           "materially different formulation (passive, inventory, or a state the "
                           "estimator does not currently use) registered as its own candidate and "
                           "friction-measured before any execution model is built for it.",
    notes="Killed by M2 evidence, not by an M1 inference, and killed at the gate that D-0037 "
          "installed: the signal's own realized magnitude was measured against the friction before "
          "any execution model was built for it, which is the order of work the queue-imbalance "
          "sibling's history made mandatory. Two limits are stated rather than hidden. First, the "
          "best-state clause clears its frozen 5x bar by 0.3% and the interval on that state's "
          "signal implies R in [4.28, 6.04], so the best-state condition is a point estimate and "
          "not a resolved separation; the pooled condition (17.09 against a bar of 10) and the "
          "clairvoyant ceiling are what make the verdict decisive, and the ceiling contains no "
          "estimator at all. Second, only the aggressive style is evaluated here; the passive "
          "formulation of this mechanism is not tested by this row and is not falsified by it, but "
          "it inherits the same one-tick/one-fee-floor geometry that killed the passive "
          "queue-imbalance pivot (EVD-0069) and would need its own candidate registration.")

add("TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG", "TUPLE", "U.S. listed stock (closing auction)",
    "VEN-NASDAQ-AUCTION", "H4", "MECH-AUCTIONIMB", "AUCTION",
    "NOII message state, indicative price, imbalance side/size, exact dissemination timestamps, "
    "auction execution prints, historical NOII records",
    "The imbalance is publicly disseminated, so persistence must come from risk, capacity or "
    "mandate constraints rather than information exclusivity (EVD-0022)",
    "PASS", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Observability is documented, but there is no locked current net-edge evidence and the "
    "historical NOII source, auction fees and order-type replication are unresolved.",
    "UNK-0004|UNK-0006|UNK-0009|UNK-0020|UNK-0027",
    "SRC-0011 tuple ledger row 8")

# ---------------------------------------------------------------- Cboe equity
add("TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS", "TUPLE",
    "U.S. listed stock >= $1 (symbol UNSPECIFIED)", "VEN-CBOEBZX-EQ", "H2-H3", "MECH-SPREADCAP",
    "PASSIVE",
    "Proprietary book events plus own-order acknowledgements for live fill reconstruction; fee "
    "code per fill; order-level history for validation",
    "First-order problem is queue position and adverse selection, not signal quality; the rebate is "
    "compensation for being selected against if markouts are adverse",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "WEAK",
    "The fee/rebate component is verified (EVD-0006) while queue economics and fill-conditioned "
    "markouts are unmeasured, and order-level history is not locked; the verified rebate constrains "
    "rather than supports the economic claim.",
    "UNK-0005|UNK-0006|UNK-0007|UNK-0008|UNK-0016|UNK-0018|UNK-0019",
    "SRC-0011 tuple ledger row 9")

# ------------------------------------------------------------------ dead rows
_CB_KILL = ("60 bps taker per fill gives 120 bps round-trip exchange trading fees before "
            "spread/slippage/adverse selection; no venue-specific evidence establishes the required "
            "seconds-scale gross edge.")
_CB_RESURRECT = ("Materially lower verified fee tier AND sealed evidence that gross conditional "
                 "movement clears total costs.")
add("TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG", "TUPLE", "BTC-USD spot", "VEN-COINBASE-BTCUSD", "H3",
    "MECH-MICRO|MECH-OFI", "AGGRESSIVE",
    "BBO/L2/trades with exchange timestamps and the exact account fee tier",
    "Minimal queue competition when marketable; the binding constraint is the venue fee tier",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Killed by the verified exchange fee floor at the named tier (EVD-0007).",
    "UNK-0006", "SRC-0011 tuple ledger row 10 / cemetery row 1",
    kill_gate="KG3_EXECUTION", kill_reason=_CB_KILL, resurrection_condition=_CB_RESURRECT,
    notes="Exchange fee schedule is verified; the residual gross edge needed is not evidenced by any "
          "source in this package.")

_KR_KILL = ("0.80% taker per fill implies 1.60% round-trip before all other costs at Tier 1.")
add("TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG", "TUPLE", "BTC/USD spot", "VEN-KRAKEN-BTCUSD", "H3",
    "MECH-MICRO|MECH-OFI", "AGGRESSIVE",
    "BBO/L2/trades with exchange timestamps and the exact account fee tier",
    "Same as the Coinbase tuple: marketable execution removes queue concerns and exposes the fee tier",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Killed by the verified platform fee floor at Tier 1 (EVD-0008).",
    "UNK-0006", "SRC-0011 tuple ledger row 11 / cemetery row 2",
    kill_gate="KG3_EXECUTION", kill_reason=_KR_KILL,
    resurrection_condition="Different verified fee economics plus evidence of enough gross edge.",
    notes="No evidence in this package establishes a seconds-scale gross edge of that size.")

_HL_KILL = ("Documented public book feed cadence is at least 0.5 s between pushes, which is slower "
            "than the 10-100 ms hypothesis horizon.")
add("TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS", "TUPLE", "BTC perpetual",
    "VEN-HYPERLIQUID-BTCPERP", "H1", "MECH-QIMB", "MIXED",
    "Sub-100 ms order-level book state with individual order identifiers",
    "The public feed itself is too coarse for the hypothesised observation loop, independent of "
    "competition",
    "FAIL", "MOOT_DEAD", "LATENCY_UNMEASURED", (_B, _F, _B, _B, _P), "DEAD",
    "Killed by verified feed cadence versus the hypothesis horizon (EVD-0009).",
    "UNK-0010", "SRC-0011 tuple ledger row 12 / cemetery row 3",
    kill_gate="KG2_DATA", kill_reason=_HL_KILL,
    resurrection_condition="A materially different authenticated/direct feed with verified sub-100 ms "
                           "state information would constitute a new tuple.",
    notes="Aggregate L2 levels carry no individual-order queue identifiers.")

add("TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG", "TUPLE", "BTC perpetual",
    "VEN-HYPERLIQUID-BTCPERP", "H3", "MECH-OFI|MECH-LIQCASCADE", "AGGRESSIVE",
    "L2/trades with exchange timestamps, market-wide liquidation observability, event-by-event "
    "historical replay",
    "Fee schedule, historical replay and liquidation observability are all currently unverified; "
    "competition is unmeasured",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Observable at the documented seconds-scale cadence, but fee schedule, historical replay, "
    "market-wide liquidation observability and effect size are all unverified (EVD-0009, EVD-0010).",
    "UNK-0006|UNK-0009|UNK-0010|UNK-0018",
    "SRC-0011 tuple ledger row 13")

add("TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX", "TUPLE", "BTC perpetual / spot hedge",
    "VEN-HYPERLIQUID-BTCPERP", "H4", "MECH-FUNDBASIS", "MIXED",
    "Funding-rate history, basis history, cross-venue hedge instrument data, capital and borrow "
    "constraints",
    "Carry trades are widely known; the question is whether the wedge survives funding, borrow and "
    "venue risk",
    "PASS", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _P), "UNKNOWN",
    "API infrastructure is usable but the economic evidence, fee schedule and cross-venue hedge "
    "mechanics are incomplete.",
    "UNK-0006|UNK-0010|UNK-0018", "SRC-0011 tuple ledger row 14")

add("TUP-EUREX-FESX-H2H3-OFIQ-MIX", "TUPLE", "FESX/DAX equity-index future (contract UNSPECIFIED)",
    "VEN-EUREX-FESX", "H2-H3", "MECH-OFI|MECH-QIMB", "MIXED",
    "EOBI order-book messages, instrument reference data, ETI trading messages, historical "
    "order-level data",
    "European index futures are heavily competed by participant firms with direct T7 access",
    "PASS", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _P), "UNKNOWN",
    "EOBI/ETI make observation and trading technically plausible (EVD-0011), but fees, matching "
    "rule, historical data, broker access and current signal replication are unverified.",
    "UNK-0006|UNK-0009|UNK-0011|UNK-0016|UNK-0018|UNK-0027",
    "SRC-0011 tuple ledger row 15")

add("TUP-CBOE-USOPT-H5-SURFRV-MIX", "TUPLE", "U.S. listed option (underlying/expiry UNSPECIFIED)",
    "VEN-CBOE-OPT", "H5", "MECH-OPTSURFRV", "MIXED",
    "Quotes across strikes/expiries, trades, NBBO and proprietary depth, point-in-time greeks "
    "derived from contemporaneous state, class-specific fee codes",
    "Model risk, spreads, legging, vol/spot hedging and fee complexity; the schedule exists but "
    "class economics are not decomposed",
    "BLOCKED", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _P), "UNKNOWN",
    "No options tuple-specific economics or historical surface data are locked; the candidate cannot "
    "pass Gate 2 in its current form.",
    "UNK-0006|UNK-0012|UNK-0027", "SRC-0011 tuple ledger row 16")

add("TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX", "TUPLE", "BTC option (strike/expiry UNSPECIFIED)",
    "VEN-DERIBIT-BTCOPT", "H5", "MECH-OPTSURFRV", "MIXED",
    "Current access/fee facts, API semantics, historical book/surface data",
    "Venue relevance alone is not enough; access, fee and data facts are unverified",
    "BLOCKED", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Gate 2 is not passed: required current access, fee and data facts were not verified.",
    "UNK-0006|UNK-0013|UNK-0027", "SRC-0011 tuple ledger row 17")

add("TUP-KALSHI-EVENT-H5-EVENTINF-AGG", "TUPLE", "Event contract (contract UNSPECIFIED)",
    "VEN-KALSHI-EVENT", "H5", "MECH-EVENTLAT", "AGGRESSIVE",
    "Per-contract legality/access, API timing semantics, fee schedule, matching and fill mechanics, "
    "historical contract data",
    "Legal access is part of the tuple; state-level restrictions are documented (EVD-0016)",
    "BLOCKED", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Access cannot be assumed nationally and no fee/API/history facts are locked; blocking before "
    "experiment rather than dead.",
    "UNK-0006|UNK-0014|UNK-0027", "SRC-0011 tuple ledger row 18")

add("TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG", "TUPLE", "Event contract (contract UNSPECIFIED)",
    "VEN-POLYMARKET-EVENT", "H5", "MECH-EVENTLAT", "AGGRESSIVE",
    "Current primary access, regulatory status, venue data and execution mechanics",
    "Regulatory and venue-data lock required before any experiment",
    "BLOCKED", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _P), "UNKNOWN",
    "Current primary access and execution facts are insufficient to specify the tuple.",
    "UNK-0006|UNK-0014|UNK-0027", "SRC-0011 tuple ledger row 19")

add("TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG", "TUPLE",
    "U.S. listed stock (symbol UNSPECIFIED), national market", "VEN-USSTOCK-MULTI", "H1",
    "MECH-STALEQUOTE", "AGGRESSIVE",
    "Simultaneous multi-venue books with synchronized receive timestamps, smart-order-routing "
    "behaviour, own order/fill records",
    "Attractive in theory but likely demands fast cross-feed processing and routing; dedicated "
    "low-latency firms contest the obvious forms",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "WEAK",
    "The M1-A report assigns WEAK on structural reasoning (latency/routing demands) rather than on "
    "candidate-specific measured evidence; the gate ceiling permits WEAK/UNKNOWN and no evidence "
    "supports an upgrade. Divergence recorded as UNK-0024.",
    "UNK-0005|UNK-0006|UNK-0009|UNK-0016|UNK-0018|UNK-0021",
    "SRC-0011 tuple ledger row 20")

add("TUP-FX-ECN-H2H3-LEADLAG-AGG", "TUPLE", "Spot FX pair (pair and ECN UNSPECIFIED)",
    "VEN-FX-ECN-UNSPEC", "H2-H3", "MECH-LEADLAG", "AGGRESSIVE",
    "Exact ECN identification, participant status, feed, order protocol, last-look/execution "
    "mechanics, historical tick data",
    "Institutional venues differ in RFQ/last-look behaviour; onboarding and capital may dominate "
    "feasibility",
    "BLOCKED", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _B), "UNKNOWN",
    "'FX' is not a valid unit of analysis: an exact ECN and participant class must be defined before "
    "any cost, rule or falsifier can be stated.",
    "UNK-0006|UNK-0015", "SRC-0011 tuple ledger row 21")

add("TUP-FX-RETAILBROKER-H3H4-FEEDLAG-AGG", "TUPLE", "Spot FX pair (pair and broker UNSPECIFIED)",
    "VEN-FX-RETAILBROKER-UNSPEC", "H3-H4", "MECH-LEADLAG", "AGGRESSIVE",
    "Broker identity, feed semantics, execution policy and spread history",
    "The broker's execution policy is part of the hypothesis; retail feeds are not institutional "
    "price discovery",
    "BLOCKED", "UNKNOWN", "PHYSICALLY_PLAUSIBLE_ONLY", (_B, _B, _B, _B, _B), "UNKNOWN",
    "The tuple cannot be stated without a named broker and its execution policy.",
    "UNK-0006|UNK-0015", "SRC-0011 tuple ledger row 22")

# ------------------------------------------------- non-tuple registered kills
add("TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG", "TUPLE",
    "U.S. listed stock (symbol UNSPECIFIED)", "VEN-NASDAQ-CONT", "H1-H2", "MECH-QIMB", "PASSIVE",
    "Individual-order queue state (order-level history)",
    "Queue position is the mechanism; the easily accessible history cannot represent it",
    "FAIL", "MOOT_DEAD", "LATENCY_UNMEASURED", (_B, _F, _B, _B, _P), "DEAD",
    "Killed by verified product scope: consolidated Tick History is Level 1 (EVD-0005).",
    "UNK-0004", "SRC-0011 cemetery row 4",
    kill_gate="KG2_DATA",
    kill_reason="The historical product is Level 1; individual queue reconstruction is impossible "
                "from that dataset alone.",
    resurrection_condition="Acquire order-level historical TotalView/ITCH or equivalent.",
    notes="Distinct from the H2 queue-imbalance tuple, which is not dead: this row is specifically "
          "the L1-only variant.")

add("TUP-METHOD-PASSIVE-TOUCHFILL", "METHOD_RULE",
    "ANY instrument with passive execution (method rule)", "UNKNOWN", "ANY", "MECH-SPREADCAP",
    "PASSIVE",
    "Validated queue-aware fill model and fill-conditioned markouts",
    "Not a candidate; a fill assumption that silently determines the answer",
    "FAIL", "MOOT_DEAD", "LATENCY_UNMEASURED", (_B, _B, _F, _B, _P), "DEAD",
    "Killed as an execution-integrity violation: the proposed fill rule omits queue and adverse "
    "selection, so it cannot answer the economic question.",
    UNKNOWN, "SRC-0011 cemetery row 5",
    kill_gate="KG3_EXECUTION",
    kill_reason="The proposed fill rule omits queue position and adverse selection, so it cannot "
                "answer the economic question it is used to answer.",
    resurrection_condition="A validated queue-aware simulator or shadow-fill process replaces it.",
    notes="Registered so that any later passive backtest using touch=fills cannot silently re-enter.")

add("TUP-GENERIC-CRYPTO-MICRO", "UNIVERSE_DEFINITION",
    "Generic 'crypto microstructure' (no exact instrument/venue)", UNKNOWN, "H1-H4", "MECH-MICRO",
    "AGGRESSIVE",
    "n/a (not a valid unit of analysis)",
    "Coinbase, Kraken and Hyperliquid have materially different fees, data mechanics and matching",
    "FAIL", "MOOT_DEAD", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _F), "DEAD",
    "Killed at the universe-definition gate: not a valid unit of analysis.",
    UNKNOWN, "SRC-0011 cemetery row 6",
    kill_gate="KG5_FALSIFIABILITY",
    kill_reason="Not a valid unit of analysis: venue-specific fees, data and matching mechanics "
                "differ materially across crypto venues.",
    resurrection_condition="Reformulate as an exact instrument x venue x horizon x mechanism x "
                           "execution tuple.",
    notes="The two crypto venue tuples above are the reformulations; this row stays dead.")

add("TUP-GENERIC-CME-QUEUE", "UNIVERSE_DEFINITION",
    "Generic 'CME queue strategy' (no product or order type)", UNKNOWN, "H1-H3", "MECH-QIMB",
    "PASSIVE",
    "n/a (not a valid unit of analysis)",
    "CME matching processes are product-specific and have changed by notice (EVD-0003)",
    "FAIL", "MOOT_DEAD", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _F), "DEAD",
    "Killed at the market-structure definition gate: a generic queue model is unjustified.",
    UNKNOWN, "SRC-0011 cemetery row 7",
    kill_gate="KG5_FALSIFIABILITY",
    kill_reason="CME matching processes are product-specific, so a generic queue model is unjustified.",
    resurrection_condition="Specify product/order type and implement the actual matching rule.",
    notes="ES H1 is the near-reformulation and remains WEAK, not dead.")

add("TUP-SYSTEMONE-HARDCORE-ENGINE", "GOVERNANCE",
    "System-One/Jev used as arithmetic, sizing, queue-math or hard-risk engine", UNKNOWN, "ANY",
    UNKNOWN, "MIXED",
    "n/a (governance boundary, not a data requirement)",
    "Violates the governing separation of deterministic computation and risk from probabilistic "
    "judgment (SRC-0015)",
    "FAIL", "MOOT_DEAD", "INADMISSIBLE", (_F, _B, _B, _B, _F), "DEAD",
    "Killed by project admission policy; the vendor's own documentation says arithmetic, counting, "
    "numeric precision and date comparison should stay in code (EVD-0024).",
    UNKNOWN, "SRC-0011 cemetery row 8",
    kill_gate="KG1_MECHANISM",
    kill_reason="Violates the governing separation of deterministic computation/risk from "
                "probabilistic judgment; no external evidence supplies an exception.",
    resurrection_condition="A new governance decision plus overwhelming evidence; not an M1 trading "
                           "hypothesis.",
    notes="Kill-gate mapping note: a governance-admission kill is recorded against KG1_MECHANISM "
          "because no evidenced economic mechanism supports the assignment; the original kill-gate "
          "wording is preserved in dead_candidates.report_kill_gate.")

add("TUP-JEV-HOSTED-LATENCY-UNMEASURED", "TECHNOLOGY_ADMISSION",
    "Hosted Jev assumed latency-feasible without measurement", UNKNOWN, "H1-H3", "MECH-OFI|MECH-QIMB",
    "MIXED",
    "Reproducible request-to-decision latency profile and a candidate-specific EV-vs-delay curve",
    "Vendor-reported 70-500 ms end-to-end range is not a deterministic SLA (EVD-0023)",
    "BLOCKED", "MOOT_DEAD", "INADMISSIBLE", (_B, _B, _F, _B, _P), "DEAD",
    "Killed by technology admission: request-to-market p99 is unverified and no signal half-life "
    "exists against which to compare it.",
    "UNK-0016|UNK-0017", "SRC-0011 cemetery row 9",
    kill_gate="KG3_EXECUTION",
    kill_reason="Request-to-market p99 is unverified and no signal half-life is established against "
                "which to compare it.",
    resurrection_condition="Reproducible latency profile plus a candidate-specific EV-versus-delay "
                           "curve.",
    notes="Kill-gate mapping note: technology-admission kill recorded against KG3_EXECUTION (the "
          "execution/latency envelope); original wording preserved in dead_candidates.report_kill_gate.")

BY_ID = {row["candidate_id"]: row for row in ROWS}