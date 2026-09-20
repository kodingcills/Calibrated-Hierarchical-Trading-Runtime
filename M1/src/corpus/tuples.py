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
    "blocking_issue_ids", "blocking_issue_ids_declared", "kill_gate", "kill_reason", "resurrection_condition",
    "report_row_ref", "notes", "unknown_fields",
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
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "WEAK",
    "Direct published support exists for the venue and instrument class (EVD-0012) and live "
    "full-depth observability is verified (EVD-0004), but the result is old, gross/predictive only, "
    "and the historical L3 procurement, current fee tier and after-cost replication are unresolved "
    "(EVD-0005).",
    "UNK-0004|UNK-0005|UNK-0006|UNK-0008|UNK-0009|UNK-0016|UNK-0018|UNK-0027",
    "SRC-0011 tuple ledger row 6")

add("TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG", "TUPLE",
    "Large-tick U.S. listed stock (symbol UNSPECIFIED)", "VEN-NASDAQ-CONT", "H2-H3", "MECH-MICRO",
    "AGGRESSIVE",
    "TotalView-ITCH order events for book-state reconstruction; historical order-level data; own "
    "fill data",
    "The estimator must be converted into an execution decision that beats the OFI/logistic "
    "baseline on net utility, not on estimator error",
    "PASS", "UNKNOWN", "LATENCY_UNMEASURED", (_B, _B, _B, _B, _P), "WEAK",
    "Estimator evidence exists (EVD-0014) but profit evidence does not; the same unresolved "
    "historical-data, fee-tier and after-cost replication gaps constrain it.",
    "UNK-0004|UNK-0005|UNK-0006|UNK-0008|UNK-0009|UNK-0016|UNK-0018|UNK-0027",
    "SRC-0011 tuple ledger row 7")

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
    "PASS", "MOOT_DEAD", "LATENCY_UNMEASURED", (_B, _B, _F, _B, _P), "DEAD",
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
    "PASS", "MOOT_DEAD", "LATENCY_UNMEASURED", (_B, _B, _F, _B, _P), "DEAD",
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