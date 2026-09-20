"""Stage-semantics migration for the issue registry (handoff §2, §3, §24).

Why this module exists
----------------------
The first M1-D0 pass classified every empirical unknown as an M1 blocker. That created a
circular dependency: M1 required measurements that only M2 can produce, while M2 required M1
to complete first. Under that scheme KG4 could never pass, so M1-B could never be authorized,
so M2 could never run. This module breaks the loop without weakening the standard.

Two independent classifications per issue (handoff §3):

RESOLUTION_METHOD   how the answer is obtained
    PUBLIC_RESEARCH | EXTERNAL_ACTION | EMPIRICAL_MEASUREMENT | DEFERRED

RESOLUTION_STAGE    when the answer is required
    M1_BLOCKING | M2_MEASUREMENT | POST_M2 | NON_BLOCKING

Only M1_BLOCKING issues enter the active frontier (handoff §14 STEP 2). M2_MEASUREMENT issues
become preregistered measurement specifications (`M1/work/m2_specs/`), EXTERNAL_ACTION issues
become executable request packets (`M1/work/external_requests/`).

Nothing here lowerers an evidential bar: every M2_MEASUREMENT issue still blocks *promotion
to capital*, and every candidate still needs a preregistered M2 test before any gate that
depends on it can pass.
"""

from .constants import UNKNOWN

RESOLUTION_METHODS = ("PUBLIC_RESEARCH", "EXTERNAL_ACTION", "EMPIRICAL_MEASUREMENT",
                      "HUMAN_INPUT", "DEFERRED")

# Methods the autonomous orchestrator may dispatch. HUMAN_INPUT requires a fact only the project
# operator holds; DEFERRED means genuinely postponed work. Neither is ever dispatched, and both
# are excluded from the frontier by construction rather than by convention.
AUTONOMOUS_METHODS = ("PUBLIC_RESEARCH", "EXTERNAL_ACTION")
NON_AUTONOMOUS_METHODS = ("HUMAN_INPUT", "DEFERRED", "EMPIRICAL_MEASUREMENT")
RESOLUTION_STAGES = ("M1_BLOCKING", "M2_MEASUREMENT", "POST_M2", "NON_BLOCKING")
EFFORTS = ("SMALL", "MEDIUM", "LARGE")
KILL_POTENTIALS = ("LOW", "MEDIUM", "HIGH")
BRANCH_IMPACTS = ("ONE", "SMALL", "MEDIUM", "HIGH", "GLOBAL")

# Frontier tiers (handoff §7). The tier is a *work class*, not a severity.
TIER_DEFINITIONS = {
    1: "cheap physical / economic killer resolved by public research",
    2: "mechanism credibility (venue-specific replication, payer, persistence)",
    3: "procurement feasibility (quotes, samples, entitlements, routing economics)",
    4: "empirical measurement (fill models, markouts, EV(delay), capacity, model utility)",
}

COLUMNS = [
    "issue_id", "resolution_method", "resolution_stage", "tier",
    "branch_impact", "kill_potential", "estimated_effort",
    "migration_decision", "migration_reason", "migration_from",
    "card_title", "card_required_answer", "card_acceptable_evidence",
    "card_disallowed_evidence", "card_success_condition", "card_kill_condition",
    "card_priority_reason",
]

# --- authored migration table -------------------------------------------------
# (issue, method, stage, tier, impact, kill, effort, title, required_answer,
#  acceptable_evidence, disallowed_evidence, success_condition, kill_condition, reason)
_T = [
    ("UNK-0001", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "SMALL", "HIGH", "MEDIUM",
     "Exact project-level CME all-in execution cost",
     "Per-contract exchange, clearing and commission cost for the exact account path",
     "Broker/FCM schedule plus published CME and clearing fee pages, dated",
     "An assumed or industry-typical per-contract cost; a member rate applied to a non-member path",
     "A dated all-in cost per contract for the intended account type",
     "Verified all-in cost implies the hypothesised gross effect cannot cover round-trip cost",
     "M1-BLOCKING retained: a known mandatory cost is a cheap killer and cannot be deferred."),

    ("UNK-0002", "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "SMALL", "HIGH", "SMALL",
     "Exact CME matching/allocation rule per candidate contract",
     "The allocation algorithm that applies to the named product and order type, with its version",
     "CME rulebook/technical documentation stating the algorithm per product, and change notices",
     "A generic FIFO assumption or another venue's queue model",
     "Algorithm identified and the queue/fill model is consistent with it",
     "Rule shows the proposed execution style cannot obtain the assumed queue behaviour",
     "M1-BLOCKING retained: matching mechanics are a Tier-1 fact and a queue model cannot be "
     "built without it."),

    ("UNK-0003", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "SMALL", "HIGH", "MEDIUM",
     "CME historical order-level data procurement",
     "Product, history depth, schema, timestamp fields, licence and price",
     "Vendor/exchange quote plus a sample file whose schema and timestamps are validated",
     "Marketing material claiming 'up to full order book' without schema or price",
     "Sample validates against the project timestamp contract and the licence is affordable",
     "No historical order-level product exists at any usable cost",
     "M1-BLOCKING retained: data procurement feasibility is an M1 question (handoff §15 KG2)."),

    ("UNK-0004", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "MEDIUM", "HIGH", "MEDIUM",
     "US equity historical order-level depth procurement",
     "ITCH/TotalView-depth history: product, depth, fields, licence, price",
     "Vendor quote and sample file; explicit distinction from the Level-1 product",
     "Treating consolidated Level-1 history as order-level data",
     "Order-level history obtainable at a cost consistent with the proposed capacity",
     "Only Level-1 history is realistically obtainable for a queue-dependent mechanism",
     "M1-BLOCKING retained: granularity sufficiency is an M1 gate (measured against the "
     "mechanism's requirement), while fill rates themselves move to M2."),

    ("UNK-0005", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "MEDIUM", "HIGH", "MEDIUM",
     "US equity fee tier and routing economics for this project",
     "Realized add/remove rates and fee codes for the intended routing and account type",
     "Published venue schedules plus broker routing/quotes for the intended order types",
     "Published headline rates assumed to be the realized rates",
     "Verified realized fee schedule exists for the intended path",
     "Verified realized fees leave no headroom for the hypothesised effect",
     "M1-BLOCKING retained: known costs are Tier-1 killers."),

    ("UNK-0006", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "GLOBAL", "LOW", "MEDIUM",
     "Realized spread, slippage, impact and adverse-selection envelope",
     "Realized execution cost distribution per candidate, conditional on its own fills",
     "Measured execution cost from replay with a validated fill model, then shadow/live",
     "Parameterising an unknown component with an industry-typical value",
     "Measured envelope leaves the candidate's sign intact under conservative assumptions",
     "Measured envelope exceeds the measured gross effect on every reasonable assumption",
     "MIGRATED from M1_BLOCKING (it was UNK-0006 there). Split: known mandatory cost floors "
     "remain M1-blocking (UNK-0001/0005/0011/0012/0013/0022/0028); realized slippage, impact "
     "and adverse selection are, by construction, measurement outputs of M2. Keeping them in "
     "M1 made M1 unclosable."),

    ("UNK-0007", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "SMALL", "LOW", "MEDIUM",
     "Passive fill probability conditional on queue state",
     "P(fill | queue, state) under the venue's actual matching rule",
     "Queue-aware replay validated against shadow fills; partial fills and cancels handled",
     "Touch=fills, or a fill probability imported from another venue",
     "Fill model validated within a preregistered tolerance against shadow observations",
     "Fill probability is low enough that the mechanism cannot amortise its own costs",
     "MIGRATED from M1_BLOCKING. Fill rates are an M2 output; the M1-relevant part (does an "
     "order-level feed exist to model them at all) is KG2 / UNK-0003 / UNK-0004."),

    ("UNK-0008", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "GLOBAL", "LOW", "MEDIUM",
     "Signal half-life: EV versus delay response surface",
     "Execution-aware EV at controlled artificial delays for each candidate signal",
     "Delay sweep on causal replay data with the project's timestamp contract",
     "An exponential decay constant inferred from 'next tick' or 'short horizon' language",
     "Measured EV(delay) remains positive at the achievable p99 decision age",
     "Measured EV(delay) is non-positive at every achievable delay",
     "MIGRATED from M1_BLOCKING, and this is the single most important migration: requiring a "
     "measured half-life inside M1 made KG4 unpassable, which made M1-B impossible, which made "
     "M2 impossible. M1 now requires only that no *known physical* timing contradiction exists "
     "and that the delay experiment is preregistered."),

    ("UNK-0009", "PUBLIC_RESEARCH", "M1_BLOCKING", 2, "GLOBAL", "HIGH", "MEDIUM",
     "Modern venue-specific replication (or disconfirmation) of the borrowed mechanisms",
     "Current, venue-specific, after-cost evidence for the mechanism each candidate relies on",
     "Primary peer-reviewed or exchange-documented replication on the exact venue/instrument",
     "Transfer of another venue's coefficients, decay or sample; marketing material",
     "Venue-specific after-cost evidence exists, or a credible structural argument for transfer",
     "Venue-specific evidence contradicts the mechanism, or a negative replication is found",
     "M1-BLOCKING retained: mechanism credibility is the core M1 question (handoff §15 KG1)."),

    ("UNK-0010", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "SMALL", "HIGH", "SMALL",
     "Hyperliquid economics and replay surface",
     "Current fee schedule, historical event-level book/trade source, liquidation data surface",
     "Official fee page and API documentation with dates; archival product terms",
     "Assuming public API pagination equals event-level historical replay",
     "Fee schedule and an event-level historical source are both identified and affordable",
     "Fees or the absence of event-level history make the seconds-scale tuples uneconomic",
     "M1-BLOCKING retained; fee and liquidation facts are public research, replay procurement "
     "needs a vendor/data request, so the binding method is EXTERNAL_ACTION."),

    ("UNK-0011", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "ONE", "HIGH", "MEDIUM",
     "Eurex execution economics, matching rule and access path",
     "Participant route, fee schedule, allocation rule, historical EOBI availability",
     "Exchange fee schedule and rulebook; broker/participant requirements",
     "Assumed member pricing for a non-member path",
     "A viable participant route with dated fees exists",
     "No economic participant route exists for the project at any usable size",
     "M1-BLOCKING retained: access and cost are Tier-1/Tier-3 facts."),

    ("UNK-0012", "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "ONE", "HIGH", "SMALL",
     "Cboe options fee decomposition for a named tuple",
     "Class/order-type fee codes, effective dates, and the historical surface data source",
     "Official Cboe options fee schedule decomposed to the exact order types",
     "A headline rate applied to a different order type or class",
     "Fee codes and a surface-data source are identified for one exact option tuple",
     "Fee structure alone makes an options tuple uneconomic at the proposed size",
     "M1-BLOCKING retained: the schedule is public, so this is cheap public research."),

    ("UNK-0013", "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "ONE", "HIGH", "SMALL",
     "Deribit current access, fee and data facts",
     "2026 access status, fee schedule, API and historical data availability",
     "Venue documentation with dates; regulatory sources for access",
     "Pre-2026 memory of venue terms",
     "Access, fees and a historical data path are all documented as currently available",
     "Access is legally unavailable to the project, or fees dominate the effect",
     "M1-BLOCKING retained: cheap public research, high kill potential."),

    ("UNK-0014", "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "SMALL", "HIGH", "MEDIUM",
     "Event-market legality and access matrix",
     "Jurisdiction-by-jurisdiction access for Kalshi/Polymarket plus fees, API and history",
     "Regulator/court documents, venue terms of service with dates",
     "A nationwide-access assumption in either direction",
     "A per-jurisdiction access determination exists for the project's operator base",
     "Access is unavailable in the relevant jurisdictions, killing the branch",
     "M1-BLOCKING retained: legality is explicitly an M1 gate (handoff §2)."),

    ("UNK-0015", "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "SMALL", "HIGH", "MEDIUM",
     "FX universe definition and venue facts",
     "One exact venue/participant class with its execution policy, fees and feed",
     "Venue documentation, participant requirements, published execution policy",
     "Treating 'FX' or a broker feed as a defined universe",
     "A single venue and participant class is specified with documented execution semantics",
     "No accessible venue/participant class exists for the project",
     "M1-BLOCKING retained: 'no exact instrument definition' is an explicit M1 blocker."),

    ("UNK-0016", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "GLOBAL", "LOW", "SMALL",
     "Own-stack decision-to-market latency distribution",
     "p50/p95/p99 decision age measured on an instrumented path for the chosen candidate",
     "Instrumented shadow run logging the full timestamp contract",
     "Vendor-reported latency, or a latency budget asserted without measurement",
     "Measured p99 sits inside the candidate's measured viable delay region",
     "Measured p99 exceeds the viable delay region at every achievable architecture",
     "MIGRATED from M1_BLOCKING. The M1-relevant part is a *physical* check (feed cadence versus "
     "hypothesis horizon), which is computed in KG2/KG4 from verified venue facts. The latency "
     "of a pipeline that does not exist yet cannot be an M1 gate."),

    ("UNK-0017", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "GLOBAL", "LOW", "MEDIUM",
     "System-One incremental utility estimand",
     "Delta_U = U_net(System-One | same information) - U_net(best classical comparator)",
     "Sealed same-information comparison on a completed baseline ladder",
     "Vendor-reported capability, calibration transfer assumptions, or a different-information "
     "comparison",
     "Delta_U robustly positive after latency and cost, with operational reliability",
     "Delta_U non-positive: System-One is removed from that path",
     "MIGRATED from M1_BLOCKING to M2_MEASUREMENT: this is an empirical estimand, and "
     "requiring it inside M1 would have made the technology branch unfalsifiable rather than "
     "merely unfunded."),

    ("UNK-0018", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "GLOBAL", "HIGH", "SMALL",
     "Historical and live feed timestamp semantics",
     "Field-level timestamp semantics (event vs receive time, clock domain, sequence integrity)",
     "Sample file plus field documentation, validated against the project timestamp contract",
     "Assuming vendor timestamps are exchange event times without evidence",
     "Samples validate: monotonic ordering, sequence integrity, documented clock domain",
     "Timestamps cannot support causal ordering, invalidating replay for that feed",
     "M1-BLOCKING retained: this is a data-adequacy fact, not a measurement."),

    ("UNK-0019", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "MEDIUM", "LOW", "MEDIUM",
     "Fill-conditioned markout (adverse selection)",
     "E(markout | fill, state) distribution per candidate",
     "Markouts conditional on own simulated fills, then on shadow/live fills",
     "Unconditional markouts, or mid-price paths used as a fill proxy",
     "Conditional markout leaves positive net edge after costs",
     "Conditional markouts show structural adverse selection against the strategy",
     "MIGRATED from M1_BLOCKING: markout is an M2 output; the M1 question is whether the data "
     "to measure it exists (KG2)."),

    ("UNK-0020", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "ONE", "MEDIUM", "SMALL",
     "Historical auction imbalance data source",
     "Historical NOII / auction execution data with exact dissemination timestamps",
     "Vendor product terms and sample",
     "Live NOII existence treated as historical availability",
     "A historical auction dataset with timestamps is obtainable",
     "No historical auction dataset exists at usable granularity",
     "M1-BLOCKING retained: data existence is Tier 1/3."),

    ("UNK-0021", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "ONE", "MEDIUM", "MEDIUM",
     "Cross-venue stale-quote survival",
     "Fraction of stale quotes still present at order arrival, measured end to end",
     "Measured cross-feed synchronisation and decision age plus quote-survival statistics",
     "Assuming stale quotes persist; treating theoretical latency as achievable latency",
     "Stale quotes survive long enough to be captured at the achievable latency",
     "Quotes vanish before arrival, making the branch an infrastructure race the project loses",
     "MIGRATED from M1_BLOCKING. M1 keeps the *structural* part via a physical latency check; "
     "the survival measurement itself is M2."),

    ("UNK-0022", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "ONE", "MEDIUM", "SMALL",
     "Cboe BZX proprietary depth, fee-code outcome and history access",
     "Feed entitlements, realized fee codes, order-level history availability",
     "Entitlement list and fee-code sample from the venue/broker",
     "Standard published rebate treated as the realized rate",
     "Entitlements and order-level history are obtainable at usable cost",
     "Access economics make the passive tuple uneconomic",
     "M1-BLOCKING retained: cost and data existence are Tier-1/Tier-3."),

    ("UNK-0023", "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "GLOBAL", "HIGH", "SMALL",
     "Citation-token to primary-URL resolution",
     "A resolvable URL plus snapshot for each of the 25 report-mediated external sources",
     "Primary pages with exact effective/access dates",
     "A URL for a different page, version or product family than the token refers to",
     "Every decision-relevant external fact is re-derived from a primary page",
     "A re-derived fact contradicts the report-mediated value (that is a finding, not a failure)",
     "M1-BLOCKING retained: decisions already rest on these facts, and re-derivation is the "
     "cheapest available integrity upgrade."),

    ("UNK-0024", "DEFERRED", "NON_BLOCKING", 4, "ONE", "LOW", "SMALL",
     "Basis of the WEAK label on the cross-venue stale-quote tuple",
     "A measured basis for the label",
     "Latency and quote-survival measurements (UNK-0021)",
     "Restating structural reasoning as evidence",
     "Label is replaced by a measured basis",
     "Not applicable to M1 progress; the label is non-promoting",
     "NON_BLOCKING retained: recorded so judgment is not mistaken for evidence."),

    ("UNK-0025", "DEFERRED", "NON_BLOCKING", 4, "GLOBAL", "LOW", "SMALL",
     "Externally anchored horizon banding",
     "An external basis for the H1..H5 bands",
     "A published horizon taxonomy, if one is ever needed for cross-study comparison",
     "Presenting project-defined microsecond endpoints as measured market facts",
     "Derived microsecond bounds are labelled as convention",
     "Not applicable",
     "NON_BLOCKING (already RESOLVED): internal consistency is what matters."),

    ("UNK-0026", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "GLOBAL", "LOW", "MEDIUM",
     "Independent verification of architecture claims",
     "External reproduction or a sealed same-information experiment",
     "Independent benchmark or the project's own sealed comparison",
     "Vendor material treated as independent verification",
     "A claim is either reproduced or removed from the premise set",
     "Not applicable to M1 selection; it bounds the technology branch",
     "MIGRATED to M2_MEASUREMENT; tracked because SUNK premises must not leak into M2 designs."),

    ("UNK-0027", "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "MEDIUM", "HIGH", "MEDIUM",
     "Exact instrument or preregistered universe rule per surviving branch",
     "One exact contract/symbol per branch, or a causal selection rule with its variables",
     "Contract specification; or a universe rule with selection variables and date",
     "Choosing the instrument with the best historical performance (selection leakage)",
     "Every finalist names an exact instrument or a leakage-free universe rule",
     "A branch cannot be specified exactly without performance-based selection, so it dies",
     "M1-BLOCKING retained: handoff §11 makes exact-instrument definition an M1 requirement."),

    ("UNK-0028", "EXTERNAL_ACTION", "M1_BLOCKING", 3, "GLOBAL", "MEDIUM", "MEDIUM",
     "Capital requirement, margin and account/tier eligibility",
     "Minimum capital, margin terms and fee tier available to the project per venue",
     "Broker/venue terms for the intended account type",
     "Assuming the best published tier is available",
     "A viable account configuration exists with documented terms",
     "Capital or entitlement requirements put every venue out of reach",
     "M1-BLOCKING retained: it determines which cost schedule applies, which is Tier 1."),

    ("UNK-0029", "EMPIRICAL_MEASUREMENT", "POST_M2", 4, "GLOBAL", "LOW", "LARGE",
     "Capacity at economically meaningful size",
     "Impact and capacity curves at increasing size",
     "Escalating size experiments after M2 demonstrates positive net EV",
     "Extrapolating small-size fills linearly",
     "Capacity at a deployable size remains profitable after impact",
     "Capacity is too small to justify the operation",
     "MIGRATED to POST_M2: capacity is only meaningful for a strategy that has already shown "
     "positive net EV; it cannot gate selection among candidates with unknown EV."),

    ("UNK-0030", "DEFERRED", "NON_BLOCKING", 4, "GLOBAL", "LOW", "SMALL",
     "Retrievability premise of the M1-A artifact",
     "Confirmation that the premise no longer holds",
     "Repository file hashes (already captured)",
     "Re-litigating the premise",
     "Premise recorded as false, verdict re-derived from remaining blockers",
     "Not applicable",
     "NON_BLOCKING (already RESOLVED): verdict re-derived under ASM-0018."),

    ("UNK-0031", "PUBLIC_RESEARCH", "NON_BLOCKING", 1, "GLOBAL", "LOW", "SMALL",
     "Transcription fidelity of the architecture specimen",
     "A second independent transcription of every numeric claim",
     "A second OCR pass at higher resolution, or a text-layer source",
     "Treating one transcription as verified",
     "Numeric claims used as premises are independently confirmed",
     "A transcription error is found that changes a recorded claim",
     "NON_BLOCKING: the specimen supplies no economic premise; it bounds confidence only."),

    ("UNK-0032", "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "GLOBAL", "LOW", "MEDIUM",
     "Cost-sensitivity surface",
     "Sign stability of net edge across conservative fee/slippage/spread assumptions",
     "Sensitivity surface computed on the M2 execution model",
     "A single point-estimate cost assumption",
     "Net edge keeps its sign across the preregistered conservative range",
     "Net edge flips sign inside the plausible cost range",
     "MIGRATED to M2_MEASUREMENT: it is a robustness output over measured inputs, and the "
     "project's own G4 gate places it after baseline evidence exists."),
]

BY_ID = {row[0]: row for row in _T}


def rows():
    """Migration table as dicts, with the migration provenance made explicit."""
    out = []
    for (issue_id, method, stage, tier, impact, kill, effort, title, required, acceptable,
         disallowed, success, killc, reason) in _T:
        out.append({
            "issue_id": issue_id,
            "resolution_method": method,
            "resolution_stage": stage,
            "tier": tier,
            "branch_impact": impact,
            "kill_potential": kill,
            "estimated_effort": effort,
            "migration_decision": f"STAGE_{stage}",
            "migration_reason": reason,
            "migration_from": "M1_BLOCKING" if stage != "M1_BLOCKING" else UNKNOWN,
            "card_title": title,
            "card_required_answer": required,
            "card_acceptable_evidence": acceptable,
            "card_disallowed_evidence": disallowed,
            "card_success_condition": success,
            "card_kill_condition": killc,
            "card_priority_reason": f"tier {tier} ({TIER_DEFINITIONS[tier]}); "
                                    f"impact {impact}; kill potential {kill}; effort {effort}",
        })
    return out


def unmapped(discrepancy_ids) -> list:
    """Registry ids with no migration row: catches a new issue being added without a stage."""
    return sorted(set(discrepancy_ids) - set(BY_ID))