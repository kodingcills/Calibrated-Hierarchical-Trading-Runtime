"""Evidence ledger (EVD-*).

Layout rule
-----------
EVD-0001..EVD-0016 mirror rows E-01..E-16 of the M1-A evidence ledger in SRC-0011
one-for-one, so every record is traceable back to the report row it came from.
EVD-0017 onward are claims that SRC-0011 asserts elsewhere (fact ledgers, coverage
map, mechanism taxonomy, dead-candidate cemetery) or claims about a project artifact.

``evidence_origin`` separates claims about the world from claims about our own
documents:
    EXTERNAL_VERIFIED   venue/academic source asserting an observable fact
    EXTERNAL_SELF_REPORTED  a party describing its own product or claims
    PROJECT_SOURCE      a claim made by a project artifact, carried forward unverified
    PROJECT_ARITHMETIC  arithmetic performed by a project artifact, reproducible here

``supports_or_weakens`` is relative to the candidate tuple named in ``candidate_ids``:
    SUPPORTS  the record is evidence *for* the candidate's mechanism or feasibility
    WEAKENS   the record constrains or contradicts the candidate
    NEUTRAL   the record is feasibility context (e.g. a feed exists) and does not by
              itself support an economic claim
Only SUPPORTS records are counted as candidate support evidence (ASM-0003).
"""

from .constants import UNKNOWN

COLUMNS = [
    "evidence_id",
    "claim",
    "source_id",
    "candidate_ids",
    "mechanism_id",
    "venue_id",
    "epistemic_class",
    "evidence_origin",
    "supports_or_weakens",
    "methodology",
    "sample",
    "temporal_scope",
    "gross_or_net",
    "evidence_state",
    "limitations",
    "decision_implication",
    "contradicts_mechanism",
    # Empirical scope. Candidate linkage is an administrative act; it must never create empirical
    # scope. These fields state what the study actually observed, and KG1 reads only these.
    "observed_market", "observed_venue", "observed_instrument_or_universe", "observed_period",
    "observed_horizon", "candidate_link_reason", "transfer_status",
    "verification_status",
]


def _row(**kw):
    row = {c: UNKNOWN for c in COLUMNS}
    row.update(kw)
    # Explicit, authored marker. A record weakens a candidate for many reasons (data scope,
    # cost, feed cadence) that are not mechanism contradictions. Only records marked YES here
    # can affect KG1's contradiction test, so no inference is made from supports_or_weakens.
    row.setdefault("contradicts_mechanism", "NO")
    row.setdefault("transfer_status", "UNKNOWN")
    return row


def _ev(n, **kw):
    kw["evidence_id"] = f"EVD-{n:04d}"
    return _row(**kw)


# Candidate shorthands
ES_H1 = "TUP-CME-ES-H1-QDEP-PAS"
ES_H3 = "TUP-CME-ES-H3-OFI-AGG"
NQ_H3 = "TUP-CME-NQ-H3-OFI-AGG"
TSY = "TUP-CME-TSY-H2-QREPL-MIX"
WTI = "TUP-CME-WTI-H4-FLOWVOL-AGG"
NQ_EQ_H2 = "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"
NQ_EQ_MICRO = "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG"
NQ_AUC = "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG"
BZX = "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS"
CB = "TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG"
KR = "TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG"
HL_H1 = "TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS"
HL_H3 = "TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG"
HL_H4 = "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"
EUREX = "TUP-EUREX-FESX-H2H3-OFIQ-MIX"
CBOE_OPT = "TUP-CBOE-USOPT-H5-SURFRV-MIX"
DERIBIT = "TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX"
KALSHI = "TUP-KALSHI-EVENT-H5-EVENTINF-AGG"
POLY = "TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG"
XV = "TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG"
FX_ECN = "TUP-FX-ECN-H2H3-LEADLAG-AGG"
FX_RET = "TUP-FX-RETAILBROKER-H3H4-FEEDLAG-AGG"
NQ_L1 = "TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG"
GEN_CRYPTO = "TUP-GENERIC-CRYPTO-MICRO"
GEN_CME = "TUP-GENERIC-CME-QUEUE"
S1_CORE = "TUP-SYSTEMONE-HARDCORE-ENGINE"
JEV_LAT = "TUP-JEV-HOSTED-LATENCY-UNMEASURED"

_CME_ALL = "|".join([ES_H1, ES_H3, NQ_H3, TSY, WTI, GEN_CME])
_NQ_ALL = "|".join([NQ_EQ_H2, NQ_EQ_MICRO, NQ_AUC, NQ_L1])
_HL_ALL = "|".join([HL_H1, HL_H3, HL_H4])

EVIDENCE = [
    _ev(1,
        claim="CME's current MDP supports event-based SBE market data; CME MDP Premium supports "
              "MBO Full Depth and MBP.",
        source_id="SRC-0107", candidate_ids=_CME_ALL, venue_id="VEN-CME-ES",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official technical specification; not an empirical sample",
        sample="n/a (specification)", temporal_scope="current as of M1-A pass",
        gross_or_net="N/A", evidence_state="OFFICIAL_DOCUMENT",
        limitations="Does not itself establish historical-data price or strategy economics.",
        decision_implication="Full-depth live observation is physically available for CME products; "
                             "it does not make any CME candidate economically viable.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(2,
        claim="CME's direct MDP uses dual-feed UDP multicast and MDP 3.0/SBE.",
        source_id="SRC-0115", candidate_ids=_CME_ALL, venue_id="VEN-CME-ES",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official systems specification", sample="n/a (specification)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Network availability is not the same as inexpensive retail/broker access.",
        decision_implication="Latency-relevant observation path exists in principle; project access "
                             "path and measured latency remain unverified.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(3,
        claim="CME matching behaviour is not safely modelled as one universal FIFO rule across all "
              "products, and Treasury calendar-spread matching algorithms have been changed by notice.",
        source_id="SRC-0112", candidate_ids="|".join([ES_H1, TSY, GEN_CME]), venue_id="VEN-CME-ES",
        mechanism_id="MECH-QIMB",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="WEAKENS",
        methodology="Official venue rules plus a change notice", sample="n/a (rule documents)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="The exact allocation rule must be looked up per candidate instrument; the "
                    "notice establishes only that rules can change.",
        decision_implication="A generic CME queue model is unjustified; passive CME candidates need a "
                             "product-specific matching rule before any fill model is credible.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(4,
        claim="Nasdaq TotalView exposes displayed depth/order information and NOII exposes auction "
              "imbalance information.",
        source_id="SRC-0108", candidate_ids=_NQ_ALL, venue_id="VEN-NASDAQ-CONT",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official feed description", sample="n/a (specification)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Feed availability does not establish a profitable imbalance strategy; a paired "
                    "token (SRC-0117) is not distinguished from this one by the report.",
        decision_implication="Nasdaq queue-imbalance and auction-imbalance candidates are observable; "
                             "observability is not evidence of net edge.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(5,
        claim="Nasdaq U.S. Equity Tick History is consolidated Level-1 tick data with history back "
              "to January 2014.",
        source_id="SRC-0109", candidate_ids=_NQ_ALL, venue_id="VEN-NASDAQ-CONT",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="WEAKENS",
        methodology="Official historical-data description", sample="n/a (product page)",
        temporal_scope="history from 2014-01; product current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Explicitly insufficient for individual-order queue reconstruction.",
        decision_implication="The easily accessible Nasdaq history cannot support queue-position or "
                             "passive-fill claims; L3/ITCH procurement is a separate requirement.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(6,
        claim="Cboe BZX standard rates for securities at or above $1 are a $0.0016/share displayed-add "
              "rebate and a $0.0030/share removal charge.",
        source_id="SRC-0114", candidate_ids=BZX, venue_id="VEN-CBOEBZX-EQ",
        mechanism_id="MECH-FEEREBATE",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official current exchange schedule effective 2026-09-01",
        sample="n/a (fee schedule)", temporal_scope="effective 2026-09-01", gross_or_net="N/A",
        evidence_state="OFFICIAL_SCHEDULE",
        limitations="Standard rates only: volume tiers, special fee codes, routing, CAT/broker/"
                    "clearing and realized fills still matter; $/share cannot be converted to bps "
                    "without a price.",
        decision_implication="BZX passive economics have a verified fee component, but the rebate is "
                             "not evidence of spread-capture profit.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(7,
        claim="Coinbase Exchange's $0-$10k 30-day-volume tier is 60 bps taker / 40 bps maker; the "
              "$400m+ tier is 4/0 bps outside its liquidity program.",
        source_id="SRC-0105", candidate_ids=CB, venue_id="VEN-COINBASE-BTCUSD",
        mechanism_id="MECH-MICRO",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="WEAKENS",
        methodology="Official current schedule accessed 2026-09-20", sample="n/a (fee schedule)",
        temporal_scope="accessed 2026-09-20", gross_or_net="N/A",
        evidence_state="OFFICIAL_SCHEDULE",
        limitations="Exchange fee only; account/program eligibility can change realized economics.",
        decision_implication="Two taker fills cost 120 bps in exchange fees before spread, slippage, "
                             "impact and adverse selection, which kills ordinary tiny-move aggressive "
                             "microstructure tuples at this tier.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(8,
        claim="Kraken Tier 1 spot rates are 0.40% maker and 0.80% taker, with reductions requiring "
              "high volume or assets.",
        source_id="SRC-0106", candidate_ids=KR, venue_id="VEN-KRAKEN-BTCUSD",
        mechanism_id="MECH-MICRO",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="WEAKENS",
        methodology="Official current schedule accessed 2026-09-20", sample="n/a (fee schedule)",
        temporal_scope="accessed 2026-09-20", gross_or_net="N/A",
        evidence_state="OFFICIAL_SCHEDULE",
        limitations="Platform fee only; excludes spread, slippage, impact and funding.",
        decision_implication="Two taker fills cost 160 bps before all other costs; aggressive Tier-1 "
                             "microstructure tuples are dead unless gross movement is implausibly large.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(9,
        claim="Hyperliquid's public WebSocket exposes BBO, trades and an L2 book (5 or 20 levels); the "
              "documented WsBook is a snapshot feed pushed on blocks at least 0.5 s apart, carrying "
              "price, aggregate size and order count.",
        source_id="SRC-0111", candidate_ids=_HL_ALL, venue_id="VEN-HYPERLIQUID-BTCPERP",
        mechanism_id="MECH-QIMB",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="WEAKENS",
        methodology="Official API schema accessed 2026-09-20", sample="n/a (specification)",
        temporal_scope="accessed 2026-09-20", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Aggregate L2 is not exchange-style MBO; the trading-fee schedule was not verified "
                    "in the same pass.",
        decision_implication="The public feed cannot support a 10-100 ms market-state reaction thesis; "
                             "seconds-to-minutes hypotheses remain open.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(10,
        claim="Hyperliquid info/API endpoints operate for spot and perpetuals, and some time-range "
               "responses require pagination.",
        source_id="SRC-0118", candidate_ids="|".join([HL_H3, HL_H4]),
        venue_id="VEN-HYPERLIQUID-BTCPERP",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official API specification", sample="n/a (specification)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Does not establish full historical L2 replay availability.",
        decision_implication="Observation and account data are accessible; historical replay remains "
                             "unverified.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(11,
        claim="Eurex T7 release 14.1 provides EOBI, market/reference-data interfaces and ETI "
               "documentation.",
        source_id="SRC-0110", candidate_ids=EUREX, venue_id="VEN-EUREX-FESX",
        mechanism_id="MECH-OFI",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official technical documentation (manuals Feb-Mar 2026; network docs Aug 2026)",
        sample="n/a (specification)", temporal_scope="T7 14.1, 2026", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Fee, matching-rule and historical replay economics still need instrument-specific "
                    "verification.",
        decision_implication="Eurex observation/trading is technically plausible; economic access is "
                             "unresolved.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(12,
        claim="Queue imbalance predicts the direction of the next mid-price movement for the studied "
              "Nasdaq stocks, especially large-tick stocks.",
        source_id="SRC-0101",
        candidate_ids="|".join([NQ_EQ_H2, ES_H1]),
        venue_id="VEN-NASDAQ-CONT", mechanism_id="MECH-QIMB",
        epistemic_class="SUPPORTED_FINDING", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="SUPPORTS",
        methodology="Logistic regression next-price-move prediction; ten liquid Nasdaq stocks",
        sample="10 liquid Nasdaq stocks, 2015 sample", temporal_scope="2015",
        gross_or_net="GROSS / primarily predictive",
        evidence_state="PUBLISHED",
        limitations="Old sample; venue and market regime changed; next-tick accuracy is not net P&L; "
                    "the report does not supply a resolvable citation URL; the ES tuple link is a "
                    "cross-venue/NOT-transferable association.",
        decision_implication="Justifies venue-specific execution-aware testing; does not justify an "
                             "ALIVE label, production architecture or capital.",
        observed_market="US equities", observed_venue="VEN-NASDAQ-CONT",
        observed_instrument_or_universe="10 liquid Nasdaq-listed stocks (large-tick emphasis)",
        observed_period=UNKNOWN, observed_horizon="one mid-price movement (tick-scale)",
        candidate_link_reason="Report-linked to the Nasdaq large-tick queue-imbalance tuple; the "
                              "cross-venue link to the CME tuple is an extrapolation.",
        transfer_status="CLOSE_TRANSFER",
        verification_status="REPORT_MEDIATED_UNVERIFIED_URL"),
    _ev(13,
        claim="Short-horizon price changes are strongly related to order-flow imbalance and inversely "
               "related to market depth.",
        source_id="SRC-0102",
        candidate_ids="|".join([ES_H3, NQ_H3, EUREX]),
        venue_id="VEN-CME-ES", mechanism_id="MECH-OFI",
        epistemic_class="SUPPORTED_FINDING", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Event/order-flow empirical analysis across stocks and time scales, 50 U.S. "
                    "equities using NYSE TAQ",
        sample="50 U.S. stocks (NYSE TAQ)", temporal_scope=UNKNOWN,
        gross_or_net="GROSS / price-impact relationship, not a sealed net strategy",
        evidence_state="PUBLISHED",
        limitations="An equity sample cannot be silently transferred to CME, Eurex or crypto; the "
                    "second token (SRC-0103) is not distinguished; no resolvable URL.",
        decision_implication="Forms an OFI hypothesis and mandates venue-specific replication; the "
                             "transfer to CME/Eurex is an EXTRAPOLATION.",
        verification_status="REPORT_MEDIATED_UNVERIFIED_URL"),
    _ev(14,
        claim="Microprice can improve on midpoint as an estimator by incorporating order-book imbalance.",
        source_id="SRC-0104", candidate_ids="|".join([NQ_EQ_MICRO, CB]),
        venue_id="VEN-NASDAQ-CONT", mechanism_id="MECH-MICRO",
        epistemic_class="SUPPORTED_FINDING", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="SUPPORTS",
        methodology="High-frequency price estimator", sample=UNKNOWN, temporal_scope="2018",
        gross_or_net="GROSS / estimator quality, not after-cost strategy evidence",
        evidence_state="PUBLISHED",
        limitations="No justification for treating microprice accuracy as economic edge; no resolvable "
                    "URL; the publisher metadata states no dataset, venue, universe or horizon.",
        decision_implication="Microprice may improve signal quality; profit evidence does not exist in "
                             "this package.",
        observed_market=UNKNOWN, observed_venue=UNKNOWN,
        observed_instrument_or_universe=UNKNOWN, observed_period=UNKNOWN,
        observed_horizon="short-term price prediction (unspecified)",
        candidate_link_reason="Administratively linked to the Nasdaq micro-price tuple and the "
                              "crypto spot tuple; no observed scope is stated in accessible "
                              "metadata.",
        transfer_status="UNKNOWN",
        verification_status="REPORT_MEDIATED_UNVERIFIED_URL"),
    _ev(15,
        claim="Nasdaq's IPO opening process includes a display-only period of at least ten minutes in "
               "which orders may be cancelled before the opening process.",
        source_id="SRC-0120", candidate_ids=NQ_AUC, venue_id="VEN-NASDAQ-AUCTION",
        mechanism_id="MECH-AUCTIONIMB",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official market-process documentation", sample="n/a (process document)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="IPO opening is a special event, not ordinary continuous trading, and the tuple "
                    "under consideration is the closing auction.",
        decision_implication="Auction mechanics are documented and order types can be specified; no "
                             "economic conclusion follows.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(16,
        claim="Event-market access cannot be assumed uniform across U.S. states; Washington obtained a "
               "2026 court order affecting Kalshi operations in the state.",
        source_id="SRC-0121", candidate_ids="|".join([KALSHI, POLY]),
        venue_id="VEN-KALSHI-EVENT", mechanism_id="MECH-EVENTLAT",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="WEAKENS",
        methodology="Government legal notice", sample="n/a (legal notice)",
        temporal_scope="2026", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Establishes one state-level restriction, not the nationwide status of any contract "
                    "or any statement about Polymarket.",
        decision_implication="Legal/access status is part of the tuple and blocks experiment until "
                             "resolved per jurisdiction.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(17,
        claim="Kraken states 0.25% of notional to open and 0.25% of closing notional for the "
               "referenced perpetual product, with availability depending on geography.",
        source_id="SRC-0106", candidate_ids=UNKNOWN, venue_id="VEN-KRAKEN-BTCPERP",
        mechanism_id="MECH-FUNDBASIS",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official platform documentation accessed 2026-09-20",
        sample="n/a (fee schedule)", temporal_scope="accessed 2026-09-20", gross_or_net="N/A",
        evidence_state="OFFICIAL_SCHEDULE",
        limitations="Flat per-side notional fee; maker/taker distinction not stated; no Kraken-perp "
                    "tuple exists in the M1-A tuple ledger.",
        decision_implication="Recorded as a venue fact; no candidate depends on it yet.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(18,
        claim="CME Data Services advertises historical and real-time data products including up to "
               "full order book.",
        source_id="SRC-0123", candidate_ids=_CME_ALL, venue_id="VEN-CME-ES",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official data-product listing", sample="n/a (product listing)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Exact history depth, licensing, delivery format and project cost were not locked; "
                    "marketing material is not a procurement quote.",
        decision_implication="Historical queue-data procurement remains a blocking unknown despite the "
                             "product existing.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(19,
        claim="CME MDP 3.0 documents fixed-income security definitions.",
        source_id="SRC-0124", candidate_ids=TSY, venue_id="VEN-CME-TSY",
        mechanism_id="MECH-REPLEN",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official technical documentation", sample="n/a (specification)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Security definitions only; observability does not establish economics; the "
                    "contract itself is not specified in the tuple.",
        decision_implication="Treasury-futures observation is technically anchored; the tuple still "
                             "fails to name an exact contract.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(20,
        claim="CME Globex hosts electronic equity-index futures whose market data flows through the MDP "
               "architecture.",
        source_id="SRC-0122", candidate_ids="|".join([ES_H1, ES_H3, NQ_H3]), venue_id="VEN-CME-ES",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official product/market-data listing", sample="n/a (product listing)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Does not establish fees or measurable edge.",
        decision_implication="Instrument class is confirmed electronic and observable.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(21,
        claim="Cboe operates BZX, BYX, EDGA and EDGX as separate U.S. equity venues.",
        source_id="SRC-0125", candidate_ids="|".join([BZX, CBOE_OPT]), venue_id="VEN-CBOEBZX-EQ",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="NEUTRAL",
        methodology="Official venue overview", sample="n/a (venue documentation)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Venue enumeration only; queue and fee-code specifics remain candidate-specific.",
        decision_implication="A 'Cboe equity' score would be invalid; one venue and one fee code must "
                             "be named.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(22,
        claim="Nasdaq NOII publicly disseminates auction imbalance information, so auction imbalance "
               "is observable to sophisticated competitors as well.",
        source_id="SRC-0108", candidate_ids=NQ_AUC, venue_id="VEN-NASDAQ-AUCTION",
        mechanism_id="MECH-AUCTIONIMB",
        epistemic_class="CONSENSUS_FACT", evidence_origin="EXTERNAL_VERIFIED",
        supports_or_weakens="WEAKENS",
        methodology="Official feed description", sample="n/a (specification)",
        temporal_scope="current as of M1-A pass", gross_or_net="N/A",
        evidence_state="OFFICIAL_DOCUMENT",
        limitations="Establishes observability for everyone; persistence must come from risk, capacity "
                    "or mandate constraints, none of which are evidenced here.",
        decision_implication="The candidate's persistence argument cannot rest on information "
                             "exclusivity.",
        verification_status="PRIMARY_DOCUMENT"),
    _ev(23,
        claim="TypeSafe publicly describes Jev as a System One model using a new architecture, a "
               "parallel sampler and RLCD training, and reports 70-500 ms end-to-end service latency.",
        source_id="SRC-0001", candidate_ids="|".join([S1_CORE, JEV_LAT]),
        venue_id=UNKNOWN, mechanism_id=UNKNOWN,
        epistemic_class="CONTESTED_HYPOTHESIS", evidence_origin="EXTERNAL_SELF_REPORTED",
        supports_or_weakens="NEUTRAL",
        methodology="Vendor blog and workflow evals", sample="Vendor-described evaluations",
        temporal_scope="2026 vendor material", gross_or_net="N/A", evidence_state="SELF_REPORTED",
        limitations="Vendor-reported range is not a deterministic network SLA; no architecture, "
                    "weights or RLCD objective are disclosed; not independently reproduced.",
        decision_implication="Hosted Jev cannot be assigned an H1-H3 role by assumption; measured "
                             "p50/p95/p99 is required.",
        verification_status="SELF_REPORTED_VENDOR"),
    _ev(24,
        claim="TypeSafe's own Jev 1.13 jaggedness notes state that arithmetic/counting/numeric "
               "precision and date comparison should be kept in code, that literal phrasing matters, "
               "and that structural identities across related questions are not guaranteed.",
        source_id="SRC-0002", candidate_ids="|".join([S1_CORE, JEV_LAT]),
        venue_id=UNKNOWN, mechanism_id=UNKNOWN,
        epistemic_class="SUPPORTED_FINDING", evidence_origin="EXTERNAL_SELF_REPORTED",
        supports_or_weakens="WEAKENS",
        methodology="Vendor failure-mode documentation", sample="version-specific (jev-1.13)",
        temporal_scope="Jev 1.13, 2026", gross_or_net="N/A", evidence_state="SELF_REPORTED",
        limitations="Self-reported; may change in later versions.",
        decision_implication="Supports the deterministic-computation/probabilistic-judgment split and "
                             "the prohibition on delegating arithmetic, sizing or hard risk to the model.",
        verification_status="SELF_REPORTED_VENDOR"),
    _ev(25,
        claim="The candidate architecture paper proposes a deterministic state engine plus six typed "
               "Jev judgments, confidence gating, Avellaneda-Stoikov quoting in code, hard risk vetoes "
               "and a fallback ladder, and assumes vendor calibration transfers sufficiently for "
               "sizing.",
        source_id="SRC-0010", candidate_ids="|".join([S1_CORE, JEV_LAT]),
        venue_id=UNKNOWN, mechanism_id=UNKNOWN,
        epistemic_class="EXTRAPOLATION", evidence_origin="PROJECT_SOURCE",
        supports_or_weakens="NEUTRAL",
        methodology="Eight-page architecture proposal/field report; no independent live-capital "
                    "dataset",
        sample="n/a (no empirical sample)", temporal_scope="2026", gross_or_net="N/A",
        evidence_state="SELF_REPORTED",
        limitations="Does not establish profitable alpha; the calibration-transport assumption is "
                    "contradicted by the paper's own later section; no backtest or fill data.",
        decision_implication="Treated as a candidate architecture specimen to be falsified, not as "
                             "proof of profitability.",
        verification_status="PROJECT_SOURCE_UNVERIFIED"),
    _ev(26,
        claim="Project audit findings: (a) direct Kelly sizing from a Jev probability is unjustified; "
               "(b) the paper's calibration-transport statements contradict each other; (c) binary "
               "Brier/Platt treatment is invalid for three-way/multiclass outputs; (d) the stated "
               "$10-25/month inference cost is incompatible with a 300-500 ms 24/7 cadence at the "
               "paper's own token accounting.",
        source_id="SRC-0020", candidate_ids="|".join([S1_CORE, JEV_LAT]),
        venue_id=UNKNOWN, mechanism_id=UNKNOWN,
        epistemic_class="SUPPORTED_FINDING", evidence_origin="PROJECT_ARITHMETIC",
        supports_or_weakens="WEAKENS",
        methodology="Document-level audit with reproduction of the paper's own arithmetic",
        sample="n/a (document audit)", temporal_scope=UNKNOWN, gross_or_net="N/A",
        evidence_state="NOT_AVAILABLE",
        limitations="Audits the document; does not independently verify any profitability, calibration "
                    "transfer or latency claim.",
        decision_implication="Sizing, calibration and cost claims from the paper cannot be carried into "
                             "M2 as premises.",
        verification_status="PROJECT_AUDIT"),
    _ev(27,
        claim="Candidate-architecture paper, first-party claim set read from the local PDF "
              "(image-only, 8 pages, rasterised and transcribed): vendor-reported Jev latency "
              "70-500 ms; price 0.042 USD per million input tokens with output billed at zero; "
              "32,000-token context; ~240-token state inside a 400-token budget; six-question "
              "battery (two Choice, two Noul, two Score) with thresholds toxic_flow > 0.6, "
              "liquidity_stressed > 0.7, quote_env score >= 2 with confidence > 0.80, "
              "inventory_pressure score >= 1; Equation (5) calibration target; Equation (7) "
              "fractional-Kelly sizing f = c*max(0, 2p-1) with c = 0.25; Avellaneda-Stoikov "
              "quoting in code (Equations 8-9); Brier and ECE diagnostics with 10-bin reliability "
              "and Platt scaling; four-baseline evaluation (deterministic rules, frontier LLM, "
              "Jev, Jev plus confidence gate); operating-cost claims of 10-25 USD/month and "
              "15 USD/month and a marginal cost near one hundred-thousandth of a dollar per "
              "block; explicit scope statements that Jev does not create edge and does not "
              "replace market data, numerical computation, connectivity or the risk engine, and "
              "that the microsecond lane remains defended by FPGA and colocation. Target market "
              "named only generically as a block-cadence on-chain venue (Monad); no venue, "
              "instrument, account or fee schedule is specified anywhere in the document.",
        source_id="SRC-0010", candidate_ids="|".join([S1_CORE, JEV_LAT]),
        venue_id=UNKNOWN, mechanism_id=UNKNOWN,
        epistemic_class="EXTRAPOLATION", evidence_origin="EXTERNAL_SELF_REPORTED",
        supports_or_weakens="NEUTRAL",
        methodology="Document-level transcription of rasterised pages (no text layer available); "
                    "page images retained under M1/derived/jev_paper_pages/",
        sample="8 pages, single document", temporal_scope="document dated 2026",
        gross_or_net="N/A", evidence_state="SELF_REPORTED",
        limitations="Self-reported throughout; no backtest, P&L, fill or latency measurement is "
                    "reported anywhere in the document; transcription fidelity is a residual risk "
                    "(UNK-0031).",
        decision_implication="The architecture specimen is now materially documented, which raises no "
                             "economic claim: the paper itself states it does not create edge.",
        verification_status="FIRST_PARTY_DOCUMENT_TRANSCRIPTION"),
    _ev(28,
        claim="Arithmetic reproduced by M1-C from the paper's own quantities: at its stated 300 ms "
              "block cadence with its own ~240-token state, the paper's own 0.042 USD per million "
              "input tokens implies roughly 87 USD per month of input cost; its own stated "
              "marginal cost of about one hundred-thousandth of a dollar per block implies roughly "
              "864 USD per month at the same cadence (equivalently ~2,381 input tokens per call); "
              "neither figure is compatible with the paper's stated 10-25 USD per month.",
        source_id="SRC-0010", candidate_ids="|".join([S1_CORE, JEV_LAT]),
        venue_id=UNKNOWN, mechanism_id=UNKNOWN,
        epistemic_class="SUPPORTED_FINDING", evidence_origin="PROJECT_ARITHMETIC",
        supports_or_weakens="WEAKENS",
        methodology="Closed-form arithmetic from the paper's own numbers, implemented in "
                    "M1/src/paper_arithmetic.py and unit-tested",
        sample="n/a (arithmetic on reported quantities)", temporal_scope="paper's 2026 quantities",
        gross_or_net="N/A", evidence_state="NOT_AVAILABLE",
        limitations="Confirms an internal inconsistency, not which of the paper's numbers is "
                    "correct; the true cadence and token accounting are not disclosed.",
        decision_implication="Operating-cost claims from the specimen cannot be used as premises; "
                             "any cost figure for the architecture must be measured, not quoted.",
        verification_status="PROJECT_ARITHMETIC_REPRODUCIBLE"),
    _ev(29,
        claim="The paper contradicts itself on calibration transport: Section II.D states that RLCD "
              "calibration is what licenses fractional Kelly sizing directly from model output, "
              "while Section VII requires calibration against the operator's own logged data "
              "before capital is sized.",
        source_id="SRC-0010", candidate_ids="|".join([S1_CORE, JEV_LAT]),
        venue_id=UNKNOWN, mechanism_id=UNKNOWN,
        epistemic_class="SUPPORTED_FINDING", evidence_origin="FIRST_PARTY_DOCUMENT",
        supports_or_weakens="WEAKENS",
        methodology="Cross-section reading of the transcribed document",
        sample="8 pages, single document", temporal_scope="document dated 2026",
        gross_or_net="N/A", evidence_state="SELF_REPORTED",
        limitations="Internal contradiction in a self-reported document; the later section is the "
                    "conservative statement and is the one the project adopts (SRC-0020, "
                    "correction B).",
        decision_implication="No sizing may be derived from vendor calibration; a local "
                             "execution-aware outcome model is required first.",
        verification_status="FIRST_PARTY_DOCUMENT_TRANSCRIPTION"),
]