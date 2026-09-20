"""Resolver artefact generators: external requests (handoff §9B) and M2 specs (§9C).

An EXTERNAL_ACTION blocker must not be left as "we could not search it". It becomes a packet a
human can send without thinking. An EMPIRICAL_MEASUREMENT blocker must not be left as future
work. It becomes a preregistered specification with a null, a metric and a kill criterion.

Both generators are pure functions of the card plus the candidate set, so the artefacts are
reproducible and cannot drift from the frontier.
"""

from __future__ import annotations

UNKNOWN = None

# ----------------------------------------------------------------- M2 measurement specs
SPEC_DEFINITIONS = {
    "EV_DELAY_SWEEP": {
        "title": "EV versus delay response surface",
        "question": "How does execution-aware expected value decay as a function of decision-to-"
                    "market delay for this signal?",
        "why_not_public": "No public source supplies a venue-specific EV(delay) curve for these "
                          "signals; the literature reports next-tick predictability only.",
        "dataset": "Causal replay dataset for the candidate's venue with order-level events and "
                   "the project timestamp contract.",
        "primary_metric": "Execution-aware EV in bps by delay bucket",
        "null": "Delay-shuffled control: same signal values assigned to randomly shifted "
                "timestamps within the same regime block.",
        "baseline": "zero-delay gross markout; deterministic imbalance/microprice formula without "
                    "any learned model",
        "kill_criterion": "EV non-positive at every delay achievable by the measured p99 decision "
                          "age.",
        "output": "M1/output/specs/EV_DELAY_SWEEP.json plus a decay digression table",
        "gate_effect": "KG4_HALF_LIFE: supports PASS only through the existence of this "
                       "preregistered experiment; a FAIL here kills the candidate in M2.",
        "no_decay_assumption": "The measurement is a response surface. No exponential form is "
                               "imposed; a fitted decay family is reported only if the curve's "
                               "own residuals support it.",
    },
    "PASSIVE_FILL_MODEL": {
        "title": "Passive fill probability conditional on queue state",
        "question": "What is P(fill | queue position, book state) under the venue's actual "
                    "matching rule, including partial fills and cancels?",
        "why_not_public": "No venue publishes a fill-probability model; borrowed numbers would be "
                          "a different market's queue mechanics.",
        "dataset": "Order-level replay for the exact instrument plus live shadow order "
                   "acknowledgements from the project's own path.",
        "primary_metric": "Simulated versus observed fill rate",
        "null": "Touch=fills reference model, reported as an upper bound that must be rejected.",
        "baseline": "Fixed symmetric quoting with the venue's documented priority rule",
        "kill_criterion": "Realistic fill probability leaves the mechanism unable to amortise its "
                          "own costs.",
        "output": "M1/output/specs/PASSIVE_FILL_MODEL.json",
        "gate_effect": "KG3_EXECUTION for passive and queue-linked candidates.",
        "no_touch_fill": "touch=fills is disallowed as an estimator; it is retained only as a "
                         "reference upper bound for contrast.",
    },
    "FILL_CONDITIONED_MARKOUT": {
        "title": "Fill-conditioned markout distribution",
        "question": "What is E(markout | fill, state), and does adverse selection reverse the "
                    "apparent edge?",
        "why_not_public": "Conditional markouts require the project's own fills under its own "
                          "order placement; no public analogue exists for these tuples.",
        "dataset": "Simulated fills from PASSIVE_FILL_MODEL, later reconciled against shadow and "
                   "micro-live fills.",
        "primary_metric": "Median and tail markout conditional on fill, in bps after costs",
        "null": "Exposure-matched random fills at the same timestamps.",
        "baseline": "Unconditional markout over the same window",
        "kill_criterion": "Conditional markout is negative after costs at every queue position.",
        "output": "M1/output/specs/FILL_CONDITIONED_MARKOUT.json",
        "gate_effect": "KG3_EXECUTION; feeds the execution-cost envelope.",
    },
    "LIVE_LATENCY": {
        "title": "Own-stack decision-to-market latency",
        "question": "What are the p50/p95/p99 decision ages of this project's own path?",
        "why_not_public": "The pipeline does not exist yet; vendor latency claims are not an "
                          "acceptable substitute.",
        "dataset": "Instrumented shadow run logging source event, receive, feature-complete, model "
                   "start/end, decision, submit, ack and fill times.",
        "primary_metric": "Decision-to-market p99",
        "null": "Not applicable (measurement, not inference)",
        "baseline": "Deterministic formula-only path, which bounds the achievable floor",
        "kill_criterion": "p99 exceeds the viable delay ceiling measured in EV_DELAY_SWEEP.",
        "output": "M1/output/specs/LIVE_LATENCY.json",
        "gate_effect": "KG4/KG3 placement decisions; M2_entry precondition.",
    },
    "COST_SENSITIVITY": {
        "title": "Cost-sensitivity surface",
        "question": "Does the candidate's net-edge sign survive conservative fee, spread and "
                    "slippage assumptions?",
        "why_not_public": "It requires the candidate's own measured gross effect as an input.",
        "dataset": "Measured gross effect plus the venue's verified fee schedule for the "
                   "project's account path.",
        "primary_metric": "Sign stability of net edge across the preregistered cost range",
        "null": "Zero-cost counterfactual, reported only to quantify cost drag",
        "baseline": "Point-estimate cost assumption from the verified schedule",
        "kill_criterion": "Net-edge sign flips inside the plausible cost range.",
        "output": "M1/output/specs/COST_SENSITIVITY.json",
        "gate_effect": "Robustness requirement of the project's G4 gate.",
    },
    "CAPACITY": {
        "title": "Capacity and impact curve",
        "question": "At what size does the strategy stop paying for itself?",
        "why_not_public": "Capacity is a property of this participant's order flow and the "
                          "venue's depth at the time of trading.",
        "dataset": "Escalating-size experiments after M2 demonstrates positive net EV.",
        "primary_metric": "Net EV per unit size versus size",
        "null": "Exposure-matched passive benchmark at equal size",
        "baseline": "Smallest-size result",
        "kill_criterion": "Capacity below the minimum economically meaningful deployment size.",
        "output": "M1/output/specs/CAPACITY.json",
        "gate_effect": "POST_M2; no M1 gate depends on it, which is why it does not block now.",
    },
    "SYSTEM_ONE_INCREMENTAL_UTILITY": {
        "title": "System-One incremental utility",
        "question": "Does Delta_U = U_net(System-One | same information) - U_net(best classical "
                    "comparator | same information) exceed zero?",
        "why_not_public": "The estimand is defined on this project's sealed data and its own "
                          "execution model.",
        "dataset": "Sealed split from the chosen candidate's dataset, with identical information "
                   "state for every comparator.",
        "primary_metric": "Delta_U in bps of execution-aware net utility",
        "null": "Predictor-label permutation preserving regime blocks; randomized decision "
                "conditional on the same opportunity set",
        "baseline": "Deterministic rule policy, logistic, LightGBM/XGBoost, simple neural",
        "kill_criterion": "Delta_U <= 0, or p99 decision age consumes the measured viable delay.",
        "output": "M1/output/specs/SYSTEM_ONE_INCREMENTAL_UTILITY.json",
        "gate_effect": "Admission of any semantic model; not an M1 selection criterion.",
    },
}

SPEC_STAGE = {
    "EV_DELAY_SWEEP": "M2_MEASUREMENT",
    "PASSIVE_FILL_MODEL": "M2_MEASUREMENT",
    "FILL_CONDITIONED_MARKOUT": "M2_MEASUREMENT",
    "LIVE_LATENCY": "M2_MEASUREMENT",
    "COST_SENSITIVITY": "M2_MEASUREMENT",
    "CAPACITY": "POST_M2",
    "SYSTEM_ONE_INCREMENTAL_UTILITY": "M2_MEASUREMENT",
}

QUEUE_MECHANISMS = ("MECH-QIMB", "MECH-QDEP")

# Complexity class controls how much infrastructure a candidate needs beyond the shared harness.
_COMPLEXITY = {
    "EV_DELAY_SWEEP": "SHARED_HARNESS",
    "PASSIVE_FILL_MODEL": "REPLAY_PLUS_MATCHING_RULE",
    "FILL_CONDITIONED_MARKOUT": "REPLAY_PLUS_MATCHING_RULE",
    "LIVE_LATENCY": "SHADOW_PATH",
    "COST_SENSITIVITY": "SHARED_HARNESS",
    "CAPACITY": "ESCALATING_SIZE",
    "SYSTEM_ONE_INCREMENTAL_UTILITY": "SEALED_COMPARISON",
}

_COMPLEXITY_RANK = {"SHARED_HARNESS": 1, "SHADOW_PATH": 2, "REPLAY_PLUS_MATCHING_RULE": 3,
                    "ESCALATING_SIZE": 4, "SEALED_COMPARISON": 5}


def spec_registry(candidates) -> dict:
    """Which M2 specs each candidate requires. Deterministic from candidate properties."""
    registry = {}
    for cand in candidates:
        cid = cand["candidate_id"]
        if cand["candidate_class"] != "TUPLE":
            continue
        needed = ["FILL_CONDITIONED_MARKOUT", "LIVE_LATENCY"]
        if cand["horizon_min_us"] is not UNKNOWN:
            needed.append("EV_DELAY_SWEEP")
        mechs = [m for m in str(cand["mechanism_id"] or "").split("|") if m]
        if cand["execution_style"] in ("PASSIVE", "MIXED") or any(
                m in QUEUE_MECHANISMS for m in mechs):
            needed.append("PASSIVE_FILL_MODEL")
        needed.append("COST_SENSITIVITY")
        if cand["technology_status"] != "INADMISSIBLE":
            needed.append("SYSTEM_ONE_INCREMENTAL_UTILITY")
        registry[cid] = sorted(needed)
    return registry


def m2_spec_md(spec_id, card, candidates) -> str:
    spec = SPEC_DEFINITIONS[spec_id]
    affected = ordered_candidates(candidates)
    lines = [
        f"# M2 specification: {spec['title']}",
        "",
        f"Spec id: `{spec_id}` | stage: `{SPEC_STAGE[spec_id]}` | "
        f"complexity: `{_COMPLEXITY[spec_id]}`",
        f"Source blocker: `{card['blocker_id'] if card else 'MULTIPLE'}` | "
        f"generated by `M1/orchestrator/resolvers.py`",
        "",
        "## Candidates",
        "",
        "\n".join(f"- `{cid}`" for cid in affected) or "- (none)",
        "",
        "## Question being answered",
        "",
        spec["question"],
        "",
        "## Why public evidence cannot answer it",
        "",
        spec["why_not_public"],
        "",
        "## Dataset required",
        "",
        spec["dataset"],
        "",
        "## Primary metric",
        "",
        spec["primary_metric"],
        "",
        "## Null hypothesis",
        "",
        spec["null"],
        "",
        "## Baselines",
        "",
        spec["baseline"],
        "",
        "## Kill criterion",
        "",
        spec["kill_criterion"],
        "",
        "## Output",
        "",
        spec["output"],
        "",
        "## How the result updates gates",
        "",
        spec["gate_effect"],
        "",
        "## Method constraints specific to this measurement",
        "",
    ]
    for key in ("no_decay_assumption", "no_touch_fill"):
        if key in spec:
            lines.append(f"- {spec[key]}")
    if "no_decay_assumption" not in spec and "no_touch_fill" not in spec:
        lines.append("- None beyond the project's standard evidence rules.")
    lines += [
        "",
        "## Preregistration requirement",
        "",
        "Before results are observed this file must be frozen: dataset version, feature version, "
        "label version, execution-model version, split rule and thresholds recorded in "
        "`M1/data/experiments.csv`. A measurement run without a frozen preregistration is not "
        "evidence.",
        "",
        "## Gate effect on M1",
        "",
        "This item does **not** block M1 eligibility. Under the revised semantics (handoff §15) "
        "the corresponding M1 gate passes on the existence of a preregistered experiment plus "
        "the absence of a known physical contradiction; the empirical value is an M2 output.",
        "",
    ]
    return "\n".join(lines)


def ordered_candidates(candidates) -> list:
    return sorted(c["candidate_id"] for c in candidates)


def spec_complexity(spec_ids) -> int:
    return max((_COMPLEXITY_RANK[_COMPLEXITY[s]] for s in spec_ids), default=0)


# ----------------------------------------------------------------- external requests
REQUEST_TEMPLATE = """# External request {req_id}: {title}

Blocker: `{blocker_id}` | stage `M1_BLOCKING` | method `EXTERNAL_ACTION` | tier {tier}
Priority score: {score} | generated by `M1/orchestrator/resolvers.py`

## PURPOSE

{required_answer}

## CANDIDATES AFFECTED

{candidates}

## DECISION BLOCKED

{decision_prevented}

## EXACT INFORMATION REQUIRED

{information}

## EXACT PRODUCT / INSTRUMENT

{product}

## DATE RANGE

{date_range}

## REQUIRED SCHEMA AND FIELDS

{schema}

## REQUIRED TIMESTAMP FIELDS AND CLOCK DOMAIN

{timestamps}

## LICENSING, COST AND COMMITMENT QUESTIONS

{licensing}

## SAMPLE FILE REQUEST

{sample}

## ACCEPTABLE SUBSTITUTE

{substitute}

## WHAT AN ANSWER KILLS

{kills}

## WHAT AN ANSWER CLEARS

{clears}

## READY-TO-SEND TEXT

```
{email}
```

## WHERE TO RETURN THE ANSWER

Write the response into `M1/work/patches/{blocker_id}_response.json` using the patch schema in
`M1/orchestrator/schemas.py`, or paste the raw vendor document into
`M1/work/external_requests/{blocker_id}_received/` and record the patch by hand.
"""


def external_request_md(card, contact, information, product, date_range, schema, timestamps,
                        licensing, sample, substitute) -> str:
    candidates = ", ".join(f"`{c}`" for c in card["affected_candidates"]) or "(global)"
    email = (
        f"Subject: Request for {product} specification, fee schedule and sample data\n\n"
        f"Hello,\n\n"
        f"We are evaluating {product} for a systematic trading research programme. To decide "
        f"whether it is economically and technically feasible we need the following, in "
        f"writing:\n\n"
        f"1. {information}\n"
        f"2. The applicable fee schedule for our account type, with effective dates.\n"
        f"3. Confirmation of the historical data product that corresponds to this instrument, "
        f"including history depth, delivery format and price.\n"
        f"4. A sample file (one trading day is sufficient) so we can validate the schema and "
        f"timestamp semantics before purchase.\n"
        f"5. Any entitlement, membership or minimum-commitment requirement.\n\n"
        f"Please state explicitly if any of these is not published or not available, and what "
        f"the alternative would be. We would rather have an explicit 'not available' than an "
        f"approximation, because our feasibility decision depends on it.\n\n"
        f"Thank you."
    )
    return REQUEST_TEMPLATE.format(
        req_id=card["blocker_id"], title=card["title"], blocker_id=card["blocker_id"],
        tier=card["tier"], score=card["priority_score"], required_answer=card["required_answer"],
        candidates=candidates, decision_prevented=card["decision_prevented"],
        information=information, product=product, date_range=date_range, schema=schema,
        timestamps=timestamps, licensing=licensing, sample=sample, substitute=substitute,
        kills=card["kill_condition"], clears=card["success_condition"], email=email,
    )


# Per-blocker request content: contact class, ask, product, schema, timestamps, licensing.
REQUEST_CONTENT = {
    "UNK-0001": {
        "contact": "The intended FCM / introducing broker for the account, plus CME's published "
                   "fee and clearing schedule.",
        "information": "Per-contract exchange fee, clearing fee, NFA/regulatory fee and your "
                       "commission for ES and NQ, for our account type, with effective dates.",
        "product": "CME Globex ES and NQ futures, round-turn",
        "date_range": "Current schedule plus the previous schedule if a change occurred in 2026",
        "schema": "Fee per contract by product, member/non-member, with effective date and any "
                  "tier or volume qualifier",
        "timestamps": "Not applicable to fees; state the effective date and the schedule version",
        "licensing": "Any minimum monthly volume, seat, membership or market-data entitlement "
                     "bundled with these fees",
        "sample": "A redacted statement or fee confirmation for one month at our expected size",
        "substitute": "CME's public fee schedule plus a written broker commission quote is "
                      "sufficient; an estimate is not.",
    },
    "UNK-0003": {
        "contact": "CME Data Services / Market Data Platform licensing, and any licensed "
                   "redistributor (for example BMLL, LSEG/MayStreet) if direct licensing is "
                   "impractical.",
        "information": "Whether historical Market-by-Order (MDP Premium) data for ES/NQ can be "
                       "licensed, at what history depth, in what format, at what price.",
        "product": "CME MDP 3.0 MBO Full Depth, historical archive",
        "date_range": "Sample: one continuous trading day. Quote: full available history and any "
                      "rolling window option.",
        "schema": "Per-message field list (add/modify/delete/trade), security definition mapping, "
                  "sequence numbers, and whether own-order messages are included",
        "timestamps": "Which fields carry exchange event time versus receive time; clock source "
                      "and precision; whether packet/send timestamps are included. Explicitly: "
                      "can two messages on the same nanosecond be ordered?",
        "licensing": "Internal research versus production use, redistribution limits, per-user or "
                     "per-server entitlement, minimum commitment, and storage restrictions",
        "sample": "One trading day of MBO for one liquid contract, in the production format",
        "substitute": "A schema document plus per-message field semantics is acceptable for the "
                      "M1 decision if a sample is impossible before purchase; price is mandatory.",
    },
    "UNK-0004": {
        "contact": "Nasdaq Data Link / Nasdaq market data licensing, and a broker or market-data "
                   "vendor if the direct route is impractical.",
        "information": "Whether historical full-depth order-level equity data (ITCH/TotalView "
                       "depth) can be licensed with the fields needed to reconstruct individual "
                       "order queues.",
        "product": "Historical TotalView-ITCH (or equivalent order-level product) for US listed "
                   "equities",
        "date_range": "Sample: one trading day. Quote: full available history and rolling options.",
        "schema": "Add order, execute order, cancel order, delete order, replace order, trade "
                  "messages with order reference numbers and MPIDs",
        "timestamps": "Exchange event time versus feed receive time; clock domain; sequence "
                      "numbering and gap-fill semantics",
        "licensing": "Research versus production use, redistribution, per-user entitlement, "
                     "minimum commitment, and the price difference versus the consolidated "
                     "Level-1 product",
        "sample": "One session of order-level data for a liquid symbol, or the message "
                  "specification plus a redacted extract",
        "substitute": "An explicit written statement that no order-level product is available at "
                      "usable cost is an acceptable (and branch-killing) answer.",
    },
    "UNK-0005": {
        "contact": "The intended executing broker and clearing firm, plus the venues' published "
                   "schedules.",
        "information": "Realized add/remove fee codes and per-share rates for our anticipated "
                       "order types and routing, including CAT, clearing and pass-through fees.",
        "product": "US equity routing: Nasdaq main book, Cboe BZX, NYSE, IEX",
        "date_range": "Current 2026 schedules with effective dates",
        "schema": "Fee per share by order type and venue, with tier qualifiers and any "
                  "special fee codes that apply to our order flow",
        "timestamps": "Not applicable; state effective dates and schedule versions",
        "licensing": "Volume tiers, membership requirements, and whether rebates are passed "
                     "through in full",
        "sample": "One month of realized fee codes from a comparable account, redacted",
        "substitute": "Published venue schedules plus a broker statement of pass-through policy "
                      "is sufficient.",
    },
    "UNK-0010": {
        "contact": "Hyperliquid documentation plus any archival data provider that mirrors its "
                   "book and trade history.",
        "information": "Current maker/taker fee schedule including tiers and staking discounts; "
                       "whether an event-level historical L2/trade archive exists and its terms; "
                       "how market-wide liquidations are published and whether they are "
                       "retrievable historically.",
        "product": "Hyperliquid perpetuals (BTC perp) historical event-level book and trades, "
                   "plus liquidation records",
        "date_range": "Sample: one day of event-level data. Quote: full history with any archive "
                      "limits.",
        "schema": "Snapshot versus delta messages, level composition, order count semantics, and "
                  "whether individual order identifiers exist anywhere",
        "timestamps": "Block time versus message time; the documented minimum interval between "
                      "book pushes; clock domain",
        "licensing": "Whether historical event-level data is available at all, at what cost, and "
                     "under what redistribution terms",
        "sample": "One day of event-level book deltas, or an explicit statement that only "
                  "snapshot-cadence data exists",
        "substitute": "A written statement of the archive's existence and cadence is sufficient "
                      "for M1; the fee schedule must be exact.",
    },
    "UNK-0011": {
        "contact": "Eurex participant services and a clearing member willing to sponsor access.",
        "information": "Fee schedule for our participant class, the applicable allocation rule "
                       "per product, and whether historical EOBI order-level data can be "
                       "obtained.",
        "product": "Eurex T7 equity-index futures (FESX/FDAX) and their order-book data",
        "date_range": "Current schedules; history depth as published",
        "schema": "EOBI message types and fields, including order-level identifiers and priority "
                  "semantics",
        "timestamps": "Exchange event time versus gateway receive time; precision and ordering "
                      "guarantees",
        "licensing": "Participant versus non-participant data licensing, clearing membership, "
                     "minimum commitments",
        "sample": "One day of EOBI data or a schema extract",
        "substitute": "A written statement that non-participant access is unavailable is an "
                      "acceptable branch-killing answer.",
    },
    "UNK-0033": {
        "contact": "The proposed executing broker(s)/sponsor for US equity routing, and the "
                   "clearing firm.",
        "information": "Commission per share and any markup over exchange fees for our order "
                       "flow, plus how exchange rebates and charges are passed through, plus CAT "
                       "and clearing fees.",
        "product": "Sponsored/routed US equity order flow (Nasdaq, Cboe BZX, NYSE, IEX)",
        "date_range": "Current rate card and the previous one if it changed in 2026",
        "schema": "Fee per share by order type and destination, with rebate pass-through policy "
                  "and any per-trade or monthly minimum",
        "timestamps": "Not applicable; state effective dates and rate-card version",
        "licensing": "Minimum monthly activity, technology fees, market-data entitlement "
                     "requirements bundled with the relationship",
        "sample": "One month of a comparable account's realized per-share cost, redacted",
        "substitute": "A rate card plus a written pass-through policy is sufficient; an "
                      "indicative estimate is not.",
    },
    "UNK-0018": {
        "contact": "Each venue's market-data support desk, or the data vendor supplying the "
                   "sample.",
        "information": "Field-level timestamp semantics for the sample files: which field is the "
                       "exchange event time, which is receive time, the clock domain, and whether "
                       "ordering is guaranteed by sequence number.",
        "product": "Every feed entering the M2 replay: CME MBO/MBP, Nasdaq order-level, and any "
                   "other candidate feed",
        "date_range": "Sample: one trading day per feed",
        "schema": "Field-by-field semantics with units and precision",
        "timestamps": "Explicit answers: monotonic ordering within a channel, cross-channel "
                      "ordering, duplication, gap-fill, and clock synchronisation requirements",
        "licensing": "Not applicable beyond the enclosing data licence",
        "sample": "One day of data with a field dictionary",
        "substitute": "A written protocol specification answering the ordering questions is "
                      "acceptable if a sample cannot be released.",
    },
    "UNK-0020": {
        "contact": "Nasdaq market data licensing and any auction-data vendor.",
        "information": "Whether a historical NOII / auction-imbalance dataset exists with exact "
                       "dissemination timestamps and execution prints.",
        "product": "Nasdaq closing auction imbalance and execution history",
        "date_range": "Sample: one month. Quote: full history.",
        "schema": "NOII message fields, indicative price, imbalance side and size, paired shares, "
                  "and auction execution prints",
        "timestamps": "Dissemination timestamp semantics and whether the auction print carries an "
                      "auction reference price",
        "licensing": "Research versus production use, redistribution, cost",
        "sample": "One month of auction data for a liquid symbol set",
        "substitute": "An explicit statement that no historical auction dataset is sold "
                      "separately is acceptable.",
    },
    "UNK-0022": {
        "contact": "Cboe market data services and the executing broker.",
        "information": "Proprietary depth feed entitlements, the fee codes that will apply to our "
                       "passive order flow, and order-level historical availability for BZX.",
        "product": "Cboe BZX displayed depth and order-level history",
        "date_range": "Current entitlements and schedules",
        "schema": "Order-level message specification and fee-code mapping",
        "timestamps": "Event versus receive time semantics for the depth feed",
        "licensing": "Per-user entitlements, redistribution, minimum commitments, history cost",
        "sample": "One day of depth data or the specification plus a redacted fee-code extract",
        "substitute": "A statement of entitlement and realized fee codes is sufficient.",
    },
    "UNK-0028": {
        "contact": "The intended broker(s) and clearing firm(s) for each candidate venue.",
        "information": "Minimum capital, margin methodology, account type eligibility, and the "
                       "fee tier that applies at our expected size.",
        "product": "Account configuration across the candidate venues",
        "date_range": "Current terms",
        "schema": "Margin schedule, minimum equity, and tier thresholds with the qualifying "
                  "metric defined",
        "timestamps": "Not applicable",
        "licensing": "Professional versus non-professional data status and its cost",
        "sample": "Account agreement and tier schedule",
        "substitute": "A written summary of minimum capital and the applicable tier is "
                      "sufficient; no estimate.",
    },
}