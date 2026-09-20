"""Scoped child issues for the coarse cross-venue blockers (iteration 4, handoff §2).

Why this exists
---------------
Three blockers were formulated cross-venue ("timestamp semantics", "mechanism credibility",
"source integrity"). Left coarse, each mechanically blocked every candidate in the project, which
overstates what is actually unknown: a Nasdaq feed's timestamp question says nothing about CME's.

Structure:

* The parent (UNK-0018, UNK-0009, UNK-0023) becomes an aggregate reporting object. It is marked
  ``is_aggregate_parent = YES`` and is **excluded** from candidate blocking sets and from the
  autonomous frontier by construction.
* Children carry the scope: venue/feed, affected candidates, method, stage, tier and the specific
  evidence required to close them.

Scope discipline: children are created only for branches that survive hard constraints. Nothing is
created for the dead rows (the Hyperliquid H1 cadence kill, the Level-1-only queue variant, the
method rule, the universe definitions, the governance and technology admissions).

UNK-0009 is additionally split along the axis that was conflating two questions (handoff §7):
mechanism existence (feeds KG1) versus after-cost materiality (feeds KG3 or M2). Existing
after-cost profitability is explicitly *not* a requirement for KG1 to pass.
"""

from __future__ import annotations

UNKNOWN = None

COLUMNS = [
    "issue_id", "parent_issue_id", "claim_needed", "known_evidence",
    "specific_evidence_needed", "decision_prevented", "severity", "resolution_method",
    "resolution_stage", "tier", "branch_impact", "kill_potential", "estimated_effort",
    "migration_reason", "affected_candidate_ids", "scope_venue", "scope_feed",
    "source_A", "source_B", "conflict_type", "status",
]

_NASDAQ_ROWS = ("TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|"
                "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG")
_CME_ROWS = ("TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|"
             "TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG")
_CRYPTO_ROWS = ("TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG|TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG|"
                "TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|"
                "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX")


def _row(issue_id, parent, claim, known, needed, prevented, method, stage, tier, impact,
         kill, effort, reason, candidates, venue=UNKNOWN, feed=UNKNOWN,
         severity="BLOCKING", source_a=UNKNOWN, source_b=UNKNOWN):
    return {
        "issue_id": issue_id, "parent_issue_id": parent, "claim_needed": claim,
        "known_evidence": known, "specific_evidence_needed": needed,
        "decision_prevented": prevented, "severity": severity,
        "resolution_method": method, "resolution_stage": stage, "tier": tier,
        "branch_impact": impact, "kill_potential": kill, "estimated_effort": effort,
        "migration_reason": reason, "affected_candidate_ids": candidates,
        "scope_venue": venue, "scope_feed": feed, "source_A": source_a, "source_B": source_b,
        "conflict_type": "NO_CONFLICT_INCOMPLETENESS", "status": "OPEN",
    }


CHILD_ISSUES = [
    # ---------------------------------------------------------------- UNK-0018 timestamp semantics
    _row("UNK-0018-CME", "UNK-0018",
         "Timestamp semantics for CME market data: which field is exchange event time, which is "
         "receive time, the clock domain and the ordering guarantee.",
         "MDP 3.0 documents MDEntryTime and TransactTime (nanosecond unit) but not the clock "
         "domain (SRC-0235); MDP uses dual-feed UDP multicast with sequence numbers (SRC-0115).",
         "A written answer from CME market-data support, or a sample file whose sequence and "
         "timestamp fields are validated against the project's timestamp contract.",
         "Causal replay for every CME candidate (KG2).",
         "EXTERNAL_ACTION", "M1_BLOCKING", 3, "SMALL", "HIGH", "SMALL",
         "Scoped child of the cross-venue timestamp blocker: the CME question is answerable by "
         "the exchange and does not depend on any other venue's feed.",
         _CME_ROWS, venue="VEN-CME-ES", feed="CME MDP 3.0 MBO/MBP",
         source_a="SRC-0235", source_b="SRC-0115"),
    _row("UNK-0018-NASDAQ", "UNK-0018",
         "Timestamp semantics for Nasdaq order-level history and the live TotalView feed: event "
         "versus receive time, sequence integrity and clock domain for the historical files.",
         "The historical product, its SFTP delivery and its depth are confirmed (SRC-0201); the "
         "message specification defines order-reference fields but the resolver did not extract "
         "timestamp-field semantics.",
         "The ITCH message specification's timestamp section plus a sample day whose ordering and "
         "sequence fields validate against the project's contract.",
         "Causal replay and therefore queue/fill claims for the Nasdaq equity rows (KG2).",
         "EXTERNAL_ACTION", "M1_BLOCKING", 3, "MEDIUM", "HIGH", "SMALL",
         "Scoped child: Nasdaq's timestamp question is settled by one product specification and a "
         "sample, independently of CME or Eurex.",
         _NASDAQ_ROWS, venue="VEN-NASDAQ-CONT", feed="Nasdaq TotalView-ITCH (live + historical)",
         source_a="SRC-0201"),
    _row("UNK-0018-BZX", "UNK-0018",
         "Timestamp semantics for the Cboe BZX depth feed and any historical depth archive.",
         "A historical depth archive is confirmed to exist (SRC-0205); no timestamp-field "
         "documentation was extracted.",
         "Cboe depth-feed specification and a sample with field-level timestamp semantics.",
         "Causal replay for the BZX passive tuple (KG2).",
         "EXTERNAL_ACTION", "M1_BLOCKING", 3, "ONE", "MEDIUM", "SMALL",
         "Scoped child: one venue, one product, one sample.",
         "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS", venue="VEN-CBOEBZX-EQ",
         feed="Cboe PITCH depth (live + DataShop archive)", severity="IMPORTANT",
         source_a="SRC-0205"),
    _row("UNK-0018-HYPERLIQUID", "UNK-0018",
         "Timestamp semantics and completeness rules for the official Hyperliquid archive: block "
         "time fields, per-hour file coverage and how to detect missing data.",
         "The archive layout is documented (SRC-0214) and the live feed is documented as block-"
         "cadenced with an at-least-0.5s snapshot rule (SRC-0216); field-level archive semantics "
         "and a completeness rule are not documented.",
         "The archive's file schema and a sample hour, plus a stated rule for missing hours.",
         "Replay validity for the Hyperliquid seconds-scale tuples (KG2).",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "SMALL", "HIGH", "SMALL",
         "Scoped child: the archive is the venue's own and the remaining question is its field "
         "semantics, which public documentation or one sample answers.",
         "TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
         venue="VEN-HYPERLIQUID-BTCPERP", feed="Hyperliquid S3 archive + WebSocket",
         source_a="SRC-0214", source_b="SRC-0216"),
    _row("UNK-0018-EUREX", "UNK-0018",
         "Timestamp semantics for Eurex EOBI order-book messages.",
         "EOBI/EMDI/ETI interfaces are documented (SRC-0110); no timestamp-field semantics or "
         "sample were extracted.",
         "T7 EOBI message specification timestamp section, plus an access path to a sample.",
         "Causal replay for the Eurex tuple (KG2).",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "ONE", "MEDIUM", "MEDIUM",
         "Scoped child: a public specification question for one venue.",
         "TUP-EUREX-FESX-H2H3-OFIQ-MIX", venue="VEN-EUREX-FESX", feed="Eurex T7 EOBI",
         severity="IMPORTANT", source_a="SRC-0110"),
    _row("UNK-0018-USSTOCK-CROSS", "UNK-0018",
         "Cross-venue synchronisation for the national-market tuple: can several venue feeds be "
         "placed on one comparable timeline with the accuracy the hypothesis needs?",
         "No multi-venue synchronised package is locked; NYSE/IEX direct-feed history was outside "
         "the M1-A coverage.",
         "Per-feed timestamp semantics plus a documented synchronisation method and its error "
         "bound.",
         "Causal cross-venue comparison, and therefore the stale-quote tuple (KG2/KG3).",
         "EXTERNAL_ACTION", "M1_BLOCKING", 3, "ONE", "MEDIUM", "MEDIUM",
         "Scoped child: this is a procurement and synchronisation question, not a per-venue one.",
         "TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG", venue="VEN-USSTOCK-MULTI",
         feed="multi-venue US equity depth", severity="IMPORTANT"),

    # ------------------------------------------------- UNK-0009 mechanism evidence (feeds KG1)
    _row("UNK-0009-MECH-CME", "UNK-0009",
         "Does the order-flow-imbalance / queue mechanism have direct or closely comparable "
         "evidence on CME equity-index futures?",
         "The mechanism is evidenced on US equities (SRC-0101, SRC-0102); CME matching is "
         "engine-assigned per product (SRC-0235). No CME-specific replication was located.",
         "A study on CME index futures (or an exchange-documented equivalent) establishing "
         "short-horizon flow/price predictability, with its sample and horizon stated.",
         "KG1 for every CME candidate (mechanism plausibility, not profitability).",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 2, "MEDIUM", "HIGH", "MEDIUM",
         "Split from the conflated UNK-0009: this asks only whether the mechanism exists on CME, "
         "not whether it is profitable there.",
         _CME_ROWS, venue="VEN-CME-ES", source_a="SRC-0102", source_b="SRC-0235"),
    _row("UNK-0009-MECH-NASDAQ-MICRO", "UNK-0009",
         "Is there venue-specific evidence for the micro-price mechanism on a named US equity "
         "venue, as opposed to a venue-unspecified estimator result?",
         "The micro-price paper's publisher metadata establishes the estimator claim but its "
         "sample venue could not be established from accessible metadata (SSRN returned HTTP 403; "
         "no arXiv preprint; CrossRef and RePEc carry no venue).",
         "An author or publisher version of the paper that states its dataset, venue, instrument "
         "universe and horizon, or a separate venue-specific micro-price study.",
         "KG1 for the Nasdaq micro-price tuple.",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 2, "ONE", "HIGH", "SMALL",
         "New child created by the iteration-4 citation replacement: the claim is verified but its "
         "venue scope is not, so venue-specific KG1 credit is withheld.",
         "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG", venue="VEN-NASDAQ-CONT"),

    # ------------------------------------------------ UNK-0009 economic materiality (feeds KG3/M2)
    _row("UNK-0009-ECON-CRYPTO-SPOT", "UNK-0009",
         "Is there a documented upper bound on the plausible gross seconds-scale effect on large "
         "crypto spot venues that could be compared against a verified fee floor?",
         "Verified round-trip exchange-fee floors: 120 bps on Coinbase at the 0-10k tier (SRC-0105) "
         "and 160 bps on Kraken Tier 1 (SRC-0106). No sourced bound on the plausible gross effect "
         "for a seconds-scale microprice/OFI signal on those venues exists in the package.",
         "A venue-specific study (or an exchange-published statistic) bounding achievable "
         "short-horizon gross movement on Coinbase or Kraken, sufficient to decide whether a "
         "120-160 bps round trip is arithmetically out of reach.",
         "Whether the crypto spot branch can be killed on materiality rather than left blocked: "
         "a cost level alone is not a kill (D-0022).",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "SMALL", "HIGH", "MEDIUM",
         "Split from UNK-0009 and promoted to M1 because it decides an open branch cheaply: it is "
         "the missing input that a kill would need.",
         "TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG|TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG|"
         + _CRYPTO_ROWS.replace("TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG|"
                                "TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG|", ""),
         venue="VEN-COINBASE-BTCUSD", source_a="SRC-0105", source_b="SRC-0106"),
    _row("UNK-0009-ECON-EQUITY-MEASURED", "UNK-0009",
         "After-cost replication of the equity mechanisms at the project's own fee tier.",
         "Base-tier equity fees are verified in native units (SRC-0203, SRC-0206, SRC-0209) and "
         "the mechanism is evidenced pre-cost (SRC-0101).",
         "Execution-aware replication on the project's own fill model.",
         "Whether the equity branch is profitable, which M2 exists to measure.",
         "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "MEDIUM", "LOW", "MEDIUM",
         "Split from UNK-0009: after-cost profitability is an M2 measurement and is explicitly "
         "not a precondition for KG1.",
         _NASDAQ_ROWS + "|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS"),
    _row("UNK-0009-ECON-CME-MEASURED", "UNK-0009",
         "After-cost replication on CME once the cost schedule and matching rule are known.",
         "No CME fee value is verified; the public fee search is exhausted (patch P-0003).",
         "Execution-aware replication after the cost configuration is locked.",
         "Whether the CME branch is profitable (M2).",
         "EMPIRICAL_MEASUREMENT", "M2_MEASUREMENT", 4, "MEDIUM", "LOW", "LARGE",
         "Split from UNK-0009 and parked at M2: it cannot start before the M1 cost items close.",
         _CME_ROWS),

    # ------------------------------------------------------------- UNK-0023 source integrity
    _row("UNK-0023-LIT", "UNK-0023",
         "Independent verifiability of the microstructure literature claims that gates depend on "
         "(queue imbalance, order-flow imbalance, micro-price).",
         "Gould & Bonart is now identified from author/arXiv/SSRN records (SRC-0238) and Stoikov "
         "from publisher metadata (SRC-0239); the Cont, Kukanov & Stoikov order-flow claim remains "
         "report-mediated with an unresolved token.",
         "An authoritative record for the order-flow-imbalance claim (publisher metadata plus an "
         "author or repository version) establishing its sample and venue.",
         "KG1 for candidates that would borrow the order-flow mechanism, and auditability of the "
         "mechanism-evidence row already in the ledger.",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "MEDIUM", "MEDIUM", "SMALL",
         "Child scoped to the literature claims only, and only for branches that would borrow the "
         "order-flow-imbalance claim: the Nasdaq queue-imbalance and micro-price rows no longer "
         "depend on it (their anchors are the verified Gould & Bonart and the venue-unresolved "
         "Stoikov record respectively), so they are not named here.",
         _CME_ROWS + "|TUP-EUREX-FESX-H2H3-OFIQ-MIX",
         source_a="SRC-0102"),
    _row("UNK-0023-CME-DOCS", "UNK-0023",
         "Independent verifiability of the CME technical claims used by CME gates (MDP capability, "
         "matching product-specificity, historical product advertising, fixed-income definitions).",
         "Partially re-derived: matching algorithms and DataMine MBO FIX history now come from "
         "primary client-wiki sources (SRC-0235 to SRC-0237). MDP capability, the matching change "
         "notice and the historical-product claims still rest on report tokens.",
         "Primary CME pages (MDP product documentation, rulebook chapter, data-services product "
         "page) captured with dates.",
         "KG1/KG2 evidence quality for the CME rows, and auditability of the MDP feasibility claim.",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "MEDIUM", "MEDIUM", "SMALL",
         "Child scoped to CME technical documentation; the fee question is an external action and "
         "is not part of this child.",
         _CME_ROWS, venue="VEN-CME-ES", severity="IMPORTANT", source_a="SRC-0107"),
    _row("UNK-0023-EXCH-OTHER", "UNK-0023",
         "Independent verifiability of the remaining exchange claims: Eurex T7 interfaces, the "
         "Cboe options fee schedule, and the Nasdaq IPO-process claim.",
         "Eurex T7, the Cboe options schedule and the Nasdaq IPO display-only period still rest on "
         "report tokens; the Cboe equities schedule and Nasdaq products were re-derived in "
         "iteration 1.",
         "Primary pages for each remaining claim, captured with dates.",
         "Evidence quality for the Eurex tuple and for the options candidate's Gate-2 status.",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "SMALL", "MEDIUM", "SMALL",
         "Child scoped to the three remaining venue claims; nothing else is attached to it.",
         "TUP-EUREX-FESX-H2H3-OFIQ-MIX|TUP-CBOE-USOPT-H5-SURFRV-MIX|"
         "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
         severity="IMPORTANT", source_a="SRC-0110"),
    # ------------------------------------------------- UNK-0027 exact instrument / universe rule
    _row("UNK-0027-NASDAQ-LARGETICK", "UNK-0027",
         "Exact universe rule for the Nasdaq large-tick queue-imbalance branch.",
         "Rule NASDAQ-LARGETICK-QIMB-UNIV-v1 defines large-tick structurally (median quoted spread "
         "equal to one tick and at least half of valid observations at one tick), eligibility "
         "(Nasdaq primary venue, common stock, price >= $1, top-decile liquidity rank, 120-day "
         "history, 90% lookback coverage), monthly causal selection with a 60-day lookback, "
         "point-in-time membership, and explicit anti-leakage rules.",
         "Nothing further for M1. The rule is frozen at M1/hypotheses/candidate_specs/ and its "
         "remaining data dependency (point-in-time membership) is a KG2 requirement, not a "
         "specification gap.",
         "KG5 falsifiability for the Nasdaq queue-imbalance branch.",
         "HUMAN_INPUT", "M1_BLOCKING", 1, "ONE", "LOW", "SMALL",
         "Resolved by this iteration's universe specification; the rule is machine-readable and "
         "approval is recorded before any M2 outcome inspection.",
         "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG", venue="VEN-NASDAQ-CONT",
         severity="NON_BLOCKING", source_a="SRC-0241"),
    _row("UNK-0027-NASDAQ-MICRO", "UNK-0027",
         "Exact universe rule for the Nasdaq large-tick micro-price branch.",
         "The queue-imbalance rule (NASDAQ-LARGETICK-QIMB-UNIV-v1) defines the same universe shape "
         "and could be extended, but this branch's KG1 is BLOCKED because the micro-price study's "
         "venue scope is not established, so specifying a universe would not move it.",
         "Nothing is required until KG1 resolves; then the universe rule can be adopted or versioned "
         "for this candidate.",
         "KG5 for the micro-price branch (currently gated behind KG1).",
         "DEFERRED", "M1_BLOCKING", 1, "ONE", "LOW", "SMALL",
         "Deliberately not specified now: a universe rule for a branch that cannot pass KG1 would be "
         "busywork, and the deferral is recorded rather than hidden.",
         "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG", venue="VEN-NASDAQ-CONT",
         severity="NON_BLOCKING"),
    _row("UNK-0027-CME-INDEX", "UNK-0027",
         "Exact contract specification for the CME equity-index branches.",
         "The rows name ES and NQ families; both are liquid and standard, but no contract month, "
         "roll rule or continuous-series construction has been fixed.",
         "A contract/roll specification: which expiry, the roll rule (volume or open-interest "
         "crossing, day offset) and how a continuous series is built without lookahead.",
         "KG5 for the ES H1, ES H3 and NQ H3 rows; also determines which historical data and fee "
         "line items apply.",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "MEDIUM", "MEDIUM", "SMALL",
         "Scoped child: the CME index branches need a roll rule, which is a public market-structure "
         "question, not a per-venue research project.",
         "TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG", venue="VEN-CME-ES"),
    _row("UNK-0027-CME-OTHER", "UNK-0027",
         "Exact contract specification for the CME Treasury and energy branches.",
         "Both rows name a contract family (Treasury future; WTI month) without fixing an expiry.",
         "One exact contract per branch plus its roll rule.",
         "KG5 for those rows.",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "SMALL", "MEDIUM", "SMALL",
         "Scoped child; cheap and public.",
         "TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG", severity="IMPORTANT"),
    _row("UNK-0027-AUCTION", "UNK-0027",
         "Exact mechanism and contract for the Nasdaq closing-auction branch.",
         "The row names closing-auction imbalance on Nasdaq-listed stocks but fixes neither the "
         "symbol set nor the auction order type it would place.",
         "A universe rule for the auction branch plus the exact auction order type.",
         "KG5 for the auction row.",
         "PUBLIC_RESEARCH", "M1_BLOCKING", 1, "ONE", "MEDIUM", "MEDIUM",
         "Scoped child; the auction universe can reuse the large-tick rule's structure once the "
         "mechanism gate resolves.",
         "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG", venue="VEN-NASDAQ-AUCTION", severity="IMPORTANT"),
    _row("UNK-0027-OPTIONS-EVENT-FX", "UNK-0027",
         "Exact instrument specification for the options, crypto-option, event-market and FX "
         "branches.",
         "These rows name instrument families (US option, BTC option, event contract, FX pair) with "
         "no underlying, expiry, contract or venue pairing fixed, and several also lack venue "
         "access.",
         "Per branch: one exact instrument (underlying, expiry/tenor) or a preregistered universe "
         "rule, after access is established.",
         "KG5 and KG2 for those rows.",
         "DEFERRED", "M1_BLOCKING", 1, "SMALL", "LOW", "MEDIUM",
         "Deferred as a group: each of these branches is currently blocked on access or mechanism, "
         "so instrument specification would not move them yet. Recorded so the group is visible "
         "rather than silently unscheduled.",
         "TUP-CBOE-USOPT-H5-SURFRV-MIX|TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX|"
         "TUP-KALSHI-EVENT-H5-EVENTINF-AGG|TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG|"
         "TUP-FX-ECN-H2H3-LEADLAG-AGG|TUP-FX-RETAILBROKER-H3H4-FEEDLAG-AGG",
         severity="NON_BLOCKING"),
    _row("UNK-0023-PAIRED-TOKENS", "UNK-0023",
         "Whether the paired citation tokens (turn10search28, turn16search20, turn20view3) refer "
         "to distinct sources or are duplicates of an already re-derived source.",
         "In two of three cases a paired token accompanies an already-identified source in the "
         "same claim; the report does not distinguish them.",
         "Nothing further is required for M1: the claims are covered by the identified source.",
         "Nothing decision-critical; recorded so the token inventory is complete.",
         "PUBLIC_RESEARCH", "NON_BLOCKING", 1, "ONE", "LOW", "SMALL",
         "Deliberately non-blocking: historical completeness of the token inventory is not a "
         "decision input.",
         _CME_ROWS + "|" + _NASDAQ_ROWS, severity="NON_BLOCKING"),
]

BY_ID = {row["issue_id"]: row for row in CHILD_ISSUES}


def children_of(parent_issue_id) -> list:
    return [row for row in CHILD_ISSUES if row["parent_issue_id"] == parent_issue_id]


def parent_ids() -> set:
    return {row["parent_issue_id"] for row in CHILD_ISSUES}