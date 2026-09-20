"""Unresolved-issue registry: discrepancies/unknowns (UNK-*) and open questions (OQ-*).

Every UNK row is a *decision-blocking or decision-shaping* unknown, not a research
curiosity. ``web_research_resolvable`` / ``requires_vendor_quote`` /
``requires_m2_measurement`` are the axes the M1-D0 readiness report groups blockers by.
``resolution_class`` uses the readiness taxonomy: A public research, B vendor quote or
sample, C M2 measurement, D unresolved but non-blocking.

Conflicts are never resolved by averaging; a divergence in judgment is recorded as a
divergence (``conflict_type=DIVERGENCE_IN_JUDGMENT``) rather than silently smoothed.
"""

from .constants import UNKNOWN

DISCREPANCY_COLUMNS = [
    "issue_id", "candidate_id", "affected_candidate_ids", "claim_needed", "known_evidence",
    "source_A", "source_B", "conflict_type", "exact_conflict", "suspected_reason",
    "search_attempts", "specific_evidence_needed", "web_research_resolvable",
    "requires_vendor_quote", "requires_m2_measurement", "resolution_class",
    "decision_prevented", "can_M2_measure", "severity", "status", "evidence_ids",
    "last_updated",
    # Two-dimension issue model (handoff §3). Filled from M1/src/corpus/staging.py.
    "resolution_method", "resolution_stage", "tier", "branch_impact", "kill_potential",
    "estimated_effort", "migration_decision", "migration_reason", "migration_from",
    # Aggregate/child structure: a coarse blocker must not mechanically block unrelated
    # candidates, so scoping lives on children and the parent is a reporting object.
    "parent_issue_id", "is_aggregate_parent", "scope_venue", "scope_feed",
]

OPEN_QUESTION_COLUMNS = [
    "question_id", "question", "why_it_matters", "workstream", "priority",
    "answer_required_before_gate", "search_status", "current_best_answer", "unresolved_gap",
    "next_search", "related_issue_ids", "legacy_question_id", "last_updated",
]

_UPDATED = "2026-09-20"

DISCREPANCIES = []


def _agg(issue_id, *args, **kwargs):
    """Register an aggregate parent issue: a reporting object, never a candidate gate."""
    kwargs["is_aggregate_parent"] = "YES"
    return d(issue_id, *args, **kwargs)


def d(issue_id, claim_needed, known_evidence, specific_evidence_needed, decision_prevented,
      severity, resolution_class, candidate_id=UNKNOWN, affected=UNKNOWN,
      is_aggregate_parent="NO", parent_issue_id=UNKNOWN, scope_venue=UNKNOWN,
      scope_feed=UNKNOWN,
      source_A=UNKNOWN, source_B=UNKNOWN, conflict_type="NO_CONFLICT_INCOMPLETENESS",
      exact_conflict=UNKNOWN, suspected_reason=UNKNOWN,
      search_attempts=UNKNOWN, web_research_resolvable="UNKNOWN",
      requires_vendor_quote="UNKNOWN", requires_m2_measurement="UNKNOWN",
      can_M2_measure="UNKNOWN", evidence_ids=UNKNOWN, status="OPEN"):
    DISCREPANCIES.append(dict(
        issue_id=issue_id, candidate_id=candidate_id, affected_candidate_ids=affected,
        claim_needed=claim_needed, known_evidence=known_evidence, source_A=source_A,
        source_B=source_B, conflict_type=conflict_type, exact_conflict=exact_conflict,
        suspected_reason=suspected_reason, search_attempts=search_attempts,
        specific_evidence_needed=specific_evidence_needed,
        web_research_resolvable=web_research_resolvable,
        requires_vendor_quote=requires_vendor_quote,
        requires_m2_measurement=requires_m2_measurement, resolution_class=resolution_class,
        decision_prevented=decision_prevented, can_M2_measure=can_M2_measure,
        severity=severity, status=status, evidence_ids=evidence_ids, last_updated=_UPDATED,
        parent_issue_id=parent_issue_id, is_aggregate_parent=is_aggregate_parent,
        scope_venue=scope_venue, scope_feed=scope_feed))


_CME = "TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|" \
       "TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG"

d("UNK-0001",
  claim_needed="Exact project-level all-in per-contract cost for the CME candidates "
               "(exchange fee + clearing fee + NFA/FCM commission + market-data and connectivity).",
  known_evidence="CME market-data architecture and product structure are verified; no fee schedule "
                 "value was captured in the M1-A pass.",
  specific_evidence_needed="Current CME/FCM schedule for the exact account path, registered as an "
                           "immutable M2 cost configuration.",
  decision_prevented="Aggressive CME execution viability (KG3) for every CME tuple.",
  severity="BLOCKING", resolution_class="B", source_A="SRC-0107", affected=_CME,
  search_attempts="Two passes. M1-A searched CME product/MDP documentation and market-data "
                  "infrastructure. The M1-C CMEFacts resolver then targeted fee and clearing-fee "
                  "pages directly: both were blocked, no filed fee blackline was extracted, and "
                  "the one figure surfaced came from a non-primary article with no recoverable "
                  "URL, so it was rejected (see patch P-0003 modified_claims). Public search is "
                  "exhausted for this milestone.",
  web_research_resolvable="PARTIAL (public schedules exist; the project's own commission path does not)",
  requires_vendor_quote="YES", requires_m2_measurement="NO", can_M2_measure="NO",
  evidence_ids="EVD-0001|EVD-0002|EVD-0018")

d("UNK-0002",
  claim_needed="The product-specific CME matching/allocation rule for each named candidate contract.",
  known_evidence="CME documents product-specific matching processes and has changed Treasury "
                 "calendar-spread matching by notice.",
  specific_evidence_needed="The current rulebook/matching specification for the exact contract and "
                           "order type, plus its change history.",
  decision_prevented="Any queue-position or fill model for passive CME candidates (KG2/KG3).",
  severity="BLOCKING", resolution_class="A", source_A="SRC-0112", source_B="SRC-0113",
  affected="|".join([_CME, "TUP-GENERIC-CME-QUEUE"]),
  conflict_type="NO_CONFLICT_INCOMPLETENESS",
  exact_conflict="Not a contradiction: the two sources agree that rules are product-specific and "
                 "change over time; the current rule for a named contract is simply not captured.",
  web_research_resolvable="YES", evidence_ids="EVD-0003|EVD-0019")

d("UNK-0003",
  claim_needed="Whether a historical CME MBO/MBP package can be licensed at acceptable cost with "
               "usable timestamp semantics.",
  known_evidence="CME advertises historical/real-time products including up to full order book.",
  specific_evidence_needed="Vendor quote plus a sample file whose schema and timestamp fields are "
                           "validated against a live feed.",
  decision_prevented="Causal queue replay for CME candidates (KG2), and therefore M2 for them.",
  severity="BLOCKING", resolution_class="B", source_A="SRC-0123", affected=_CME,
  search_attempts="M1-A pass could not verify the exact historical MBO package and cost.",
  requires_vendor_quote="YES", can_M2_measure="NO", evidence_ids="EVD-0018")

d("UNK-0004",
  claim_needed="Whether order-level historical U.S. equity depth (ITCH/TotalView depth) can be "
               "procured at acceptable cost.",
  known_evidence="Consolidated Tick History is verified Level-1 only; TotalView live depth is "
                 "verified available; no paid order-level history was acquired in the M1-A pass.",
  specific_evidence_needed="Order-level historical product, license terms, sample and cost.",
  decision_prevented="Queue-aware backtesting of every Nasdaq equity tuple (KG2).",
  severity="BLOCKING", resolution_class="B", source_A="SRC-0109", source_B="SRC-0108",
  affected="TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|"
           "TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
  exact_conflict="Product-scope difference, not a contradiction: Tick History (L1) and TotalView "
                 "(full depth) are different products; the risk is backtesting a queue strategy on "
                 "the easier product.",
  requires_vendor_quote="YES", evidence_ids="EVD-0005|EVD-0004")

d("UNK-0005",
  claim_needed="Current U.S. equity fee tier and routing economics actually available to this "
               "project (Nasdaq main book, Cboe BZX fee codes, CAT/broker/clearing).",
  known_evidence="Cboe BZX standard displayed-add rebate and removal fee are verified; Nasdaq "
                 "main-book small-prop tier was not locked.",
  specific_evidence_needed="Broker/venue fee schedule for the project's exact routing and account "
                           "type, per fee code.",
  decision_prevented="Net-economics arithmetic for equity tuples (KG3).",
  severity="BLOCKING", resolution_class="B",
  source_A="SRC-0114", affected="TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|"
                                "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|"
                                "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|"
                                "TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG|"
                                "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
  web_research_resolvable="PARTIAL (published schedules exist; the project's routing outcome does not)",
  requires_vendor_quote="YES", evidence_ids="EVD-0006|EVD-0021")

d("UNK-0006",
  claim_needed="The full break-even cost envelope (spread, fees, slippage, adverse selection, "
               "impact) for each candidate.",
  known_evidence="Two crypto venues have verified exchange-fee floors; no spread/slippage/impact/"
                 "adverse-selection values are verified for any candidate.",
  specific_evidence_needed="Measured or explicitly parameterised values for every break-even "
                           "component, per candidate.",
  decision_prevented="Any statement that a candidate is net-profitable; the strongest permitted "
                     "statement is a known cost floor.",
  severity="BLOCKING", resolution_class="C", source_A="SRC-0105|SRC-0106|SRC-0114",
  affected="ALL_CANDIDATES",
  can_M2_measure="YES", requires_m2_measurement="YES", evidence_ids="EVD-0006|EVD-0007|EVD-0008")

d("UNK-0007",
  claim_needed="Passive fill probability conditional on queue state.",
  known_evidence="No defensible fill probability was found; the report explicitly declines to "
                 "estimate one; touch=fills is disallowed.",
  specific_evidence_needed="Queue-aware fill model validated against shadow/live observations, "
                           "including partial fills and cancellation distinction.",
  decision_prevented="Economic evaluation of every passive candidate (KG3).",
  severity="BLOCKING", resolution_class="C",
  affected="TUP-CME-ES-H1-QDEP-PAS|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|"
           "TUP-METHOD-PASSIVE-TOUCHFILL",
  can_M2_measure="YES", requires_m2_measurement="YES")

d("UNK-0008",
  claim_needed="Empirical signal half-life: the EV-versus-delay curve for each candidate signal.",
  known_evidence="'Next tick' and 'short horizon' results exist, but no candidate-specific EV(delay) "
                 "curve; the queue-imbalance study predicts a next-price move, not decay.",
  specific_evidence_needed="Delay-sweep measurement (e.g. 0/10/25/50/100/250/500 ms, 1/2/5 s where "
                           "physically appropriate) reporting gross conditional markout and "
                           "execution-aware EV.",
  decision_prevented="Latency budget allocation, model placement and any ALIVE label (KG4).",
  severity="BLOCKING", resolution_class="C", can_M2_measure="YES", requires_m2_measurement="YES",
  evidence_ids="EVD-0012|EVD-0013",
  affected="ALL_CANDIDATES")

_agg("UNK-0009",
  claim_needed="Modern, venue-specific, after-cost replication (or explicit disconfirmation) for "
               "the mechanism each candidate relies on. The only external mechanism evidence in "
               "this package is the U.S.-equity OFI/queue-imbalance/microprice literature; every "
               "other candidate borrows a mechanism that has no current, on-venue, after-cost "
               "replication at all.",
  known_evidence="Mechanism support exists for U.S. equities (2015 and earlier samples), primarily "
                 "predictive and gross.",
  specific_evidence_needed="Independent current replication on the exact venue/instrument including "
                           "realistic costs, or an explicit disconfirming study.",
  decision_prevented="Mechanism credibility (KG1) for every candidate whose mechanism has no "
                     "current, on-venue, after-cost replication.",
  severity="BLOCKING", resolution_class="A", web_research_resolvable="YES",
  source_A="SRC-0101|SRC-0102", evidence_ids="EVD-0012|EVD-0013|EVD-0014",
  affected="ALL_CANDIDATES")

d("UNK-0010",
  claim_needed="Hyperliquid trading-fee schedule, event-level historical L2 source and market-wide "
               "liquidation observability.",
  known_evidence="Live public l2Book/BBO/trades schema verified, including the >= 0.5 s snapshot "
                 "cadence; fee schedule and historical replay product not verified.",
  specific_evidence_needed="Current fee schedule, historical event-level L2 product with timestamps, "
                           "and the venue's liquidation-data surface.",
  decision_prevented="Net-edge feasibility for the Hyperliquid H3/H4 candidates.",
  severity="BLOCKING", resolution_class="A", web_research_resolvable="PARTIAL",
  source_A="SRC-0111", affected="TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|"
                                "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX|"
                                "TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS",
  search_attempts="M1-A pass could not verify the exact current fee schedule and historical replay "
                  "product.", requires_vendor_quote="PARTIAL", evidence_ids="EVD-0009|EVD-0010")

d("UNK-0011",
  claim_needed="Eurex execution fees, product allocation rule, historical EOBI acquisition cost and "
               "broker/participant access path.",
  known_evidence="T7 14.1 EOBI/EMDI/ETI documentation verified.",
  specific_evidence_needed="Instrument-specific fee schedule, matching rule, historical data quote "
                           "and access route.",
  decision_prevented="Any Eurex candidate progressing beyond universe status.",
  severity="BLOCKING", resolution_class="B", source_A="SRC-0110",
  affected="TUP-EUREX-FESX-H2H3-OFIQ-MIX", requires_vendor_quote="YES", evidence_ids="EVD-0011")

d("UNK-0012",
  claim_needed="Cboe options class/order-type fee decomposition plus historical surface/depth data "
               "and hedging mechanics for a named option tuple.",
  known_evidence="A Cboe options fee schedule effective 2026-09-01 was located; class/order-type "
                 "economics were not decomposed.",
  specific_evidence_needed="Fee codes for the exact order types, OPRA versus proprietary depth "
                           "history, and point-in-time surface data.",
  decision_prevented="Options tuples passing Gate 2 at all.",
  severity="BLOCKING", resolution_class="B", source_A="SRC-0116",
  affected="TUP-CBOE-USOPT-H5-SURFRV-MIX", requires_vendor_quote="YES")

d("UNK-0013",
  claim_needed="Deribit current access, fee, API semantics and historical book/surface data.",
  known_evidence="Venue relevance only; current primary specifications were not locked.",
  specific_evidence_needed="2026 access/fee schedule, API contract and historical book product.",
  decision_prevented="Gate 2 for the Deribit tuple.",
  severity="BLOCKING", resolution_class="B", affected="TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX",
  requires_vendor_quote="YES")

d("UNK-0014",
  claim_needed="Jurisdiction-by-jurisdiction access, fee schedule, matching/API semantics and "
               "historical data for Kalshi and Polymarket.",
  known_evidence="Washington obtained a 2026 court order affecting Kalshi in that state: state-level "
                 "restrictions demonstrably exist.",
  specific_evidence_needed="A current per-contract access matrix plus fee/API/history facts.",
  decision_prevented="Legality/access gate for both event-market tuples.",
  severity="BLOCKING", resolution_class="A", source_A="SRC-0121",
  affected="TUP-KALSHI-EVENT-H5-EVENTINF-AGG|TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG",
  web_research_resolvable="YES", evidence_ids="EVD-0016")

d("UNK-0015",
  claim_needed="An exact FX venue (ECN or broker), participant class, feed, order protocol and "
               "last-look/execution mechanics.",
  known_evidence="Nothing venue-specific: 'FX' was never a valid unit of analysis.",
  specific_evidence_needed="A named venue plus participant status and its published or contractual "
                           "execution policy.",
  decision_prevented="Defining the tuple at all (KG1/KG3/KG5).",
  severity="BLOCKING", resolution_class="A",
  affected="TUP-FX-ECN-H2H3-LEADLAG-AGG|TUP-FX-RETAILBROKER-H3H4-FEEDLAG-AGG",
  web_research_resolvable="PARTIAL (public institutional facts exist; participant status does not)",
  requires_vendor_quote="PARTIAL")

d("UNK-0016",
  claim_needed="Measured decision-to-market latency distribution (p50/p95/p99 plus jitter and "
               "deadline-miss rate) for this project's own stack.",
  known_evidence="No live path exists yet; the requirement is stated in the project's methods "
                 "(timestamp contract, decision-age metrics).",
  specific_evidence_needed="Instrumented shadow-run latency measurements.",
  decision_prevented="Placing any model at any horizon (KG3/KG4).",
  severity="BLOCKING", resolution_class="C", source_A="SRC-0016", source_B="SRC-0018",
  can_M2_measure="YES", requires_m2_measurement="YES", affected="ALL_CANDIDATES")

d("UNK-0017",
  claim_needed="Reproducible hosted-Jev/local-System-One latency profile and incremental "
               "execution-aware utility versus a same-information classical baseline.",
  known_evidence="Vendor-reported 70-500 ms end-to-end range only; no independent reproduction; no "
                 "sealed utility comparison exists.",
  specific_evidence_needed="Measured p50/p95/p99 under trading-like load plus sealed "
                           "same-information utility comparison.",
  decision_prevented="Any System-One admission decision; determines whether the Jev branch is worth "
                     "funding at all.",
  severity="BLOCKING", resolution_class="C", source_A="SRC-0001", source_B="SRC-0015",
  can_M2_measure="YES", requires_m2_measurement="YES",
  affected="TUP-SYSTEMONE-HARDCORE-ENGINE|TUP-JEV-HOSTED-LATENCY-UNMEASURED",
  evidence_ids="EVD-0023|EVD-0024|EVD-0026")

_agg("UNK-0018",
  claim_needed="Validated timestamp semantics for historical and live feeds (exchange/event time "
               "versus receive time, clock domain, sequence integrity) sufficient for causal "
               "replay.",
  known_evidence="The project's timestamp contract is defined in its methods (SRC-0016) and the "
                 "reality-gap decomposition depends on it, but no venue's feed or historical file "
                 "has been validated against that contract.",
  specific_evidence_needed="A sample historical file and a live capture per venue, with the "
                           "timestamp fields mapped and checked for ordering, duplication and "
                           "clock domain.",
  decision_prevented="Causal replay and therefore every queue, priority or fill claim; applies to "
                     "any candidate that reaches replay.",
  severity="BLOCKING", resolution_class="B", source_A="SRC-0111", source_B="SRC-0118",
  affected="ALL_CANDIDATES",
  web_research_resolvable="PARTIAL", requires_vendor_quote="YES", requires_m2_measurement="YES",
  can_M2_measure="YES", evidence_ids="EVD-0010|EVD-0018")

d("UNK-0032",
  claim_needed="Cost-sensitivity behaviour: does any surviving candidate remain viable under "
               "conservative fee/slippage assumptions?",
  known_evidence="The two crypto tuples die on the fee floor alone; no sensitivity surface exists "
                 "for any other candidate.",
  specific_evidence_needed="Cost-sensitivity surface over fee/slippage/spread assumptions per "
                           "candidate.",
  decision_prevented="Robustness judgment (required by the project's own G4 gate).",
  severity="IMPORTANT", resolution_class="C", source_A="SRC-0014",
  affected="ALL_CANDIDATES",
  can_M2_measure="YES", requires_m2_measurement="YES")

d("UNK-0019",
  claim_needed="Fill-conditioned markout distribution (adverse selection) for every passive or "
               "crossing candidate.",
  known_evidence="Mechanically uncontroversial but unmeasured in this evidence package.",
  specific_evidence_needed="Markouts conditional on own fills, from replay with a validated fill "
                           "model and later from shadow/micro-live.",
  decision_prevented="Passive-candidate economics; also the crossing case where the signal selects "
                     "into an already-moving price.",
  severity="BLOCKING", resolution_class="C",
  affected="TUP-CME-ES-H1-QDEP-PAS|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|"
           "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
  can_M2_measure="YES", requires_m2_measurement="YES")

d("UNK-0020",
  claim_needed="Historical NOII/auction execution data source and cost.",
  known_evidence="NOII existence and public dissemination verified; historical depth/cost not "
                 "locked.",
  specific_evidence_needed="Historical auction-imbalance dataset with exact dissemination "
                           "timestamps.",
  decision_prevented="Auction tuple feasibility (KG2): without it the auction candidate has no "
                     "historical basis for testing.",
  severity="BLOCKING", resolution_class="B", source_A="SRC-0108", source_B="SRC-0120",
  affected="TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG", requires_vendor_quote="YES")

d("UNK-0021",
  claim_needed="Cross-venue source-to-decision-to-venue latency and stale-quote survival for a "
               "multi-venue U.S. equity tuple.",
  known_evidence="No evidence package establishes non-colocated feasibility; the report notes the "
                 "obvious forms are contested by dedicated low-latency firms.",
  specific_evidence_needed="Measured cross-feed synchronization, decision age and the fraction of "
                           "stale quotes still present at order arrival.",
  decision_prevented="Whether the cross-venue tuple is a real opportunity or an infrastructure race.",
  severity="BLOCKING", resolution_class="C", can_M2_measure="YES", requires_m2_measurement="YES",
  affected="TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG")

d("UNK-0022",
  claim_needed="Cboe BZX proprietary depth availability, fee-code outcome and order-level history "
               "for this project's access path.",
  known_evidence="Standard rebate/remove rates verified; nothing about data access or realized fee "
                 "codes.",
  specific_evidence_needed="Feed/data entitlement list and a sample of realized fee codes.",
  decision_prevented="BZX passive tuple feasibility (KG2/KG3).",
  severity="IMPORTANT", resolution_class="B", source_A="SRC-0114", source_B="SRC-0125",
  affected="TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS", requires_vendor_quote="YES",
  evidence_ids="EVD-0006|EVD-0021")

_agg("UNK-0023",
  claim_needed="Resolvable identities (URL/DOI) for the 25 external sources the M1-A report cites "
               "only through opaque internal citation tokens.",
  known_evidence="Tokens are preserved verbatim and the report names most sources descriptively "
                 "(organisation, venue, sometimes author/year), but no URL is reconstructible from "
                 "repository artifacts.",
  specific_evidence_needed="Token-by-token resolution to a primary URL with an access snapshot.",
  decision_prevented="Independent verification of any external claim, including fee schedules that "
                     "already killed candidates; the arithmetic is unaffected, the auditability is.",
  severity="IMPORTANT", resolution_class="A", source_A="SRC-0011", web_research_resolvable="YES",
  affected="ALL_EXTERNAL_EVIDENCE",
  suspected_reason="The M1-A export emitted citation tokens in place of links; the mapping lives "
                   "outside the artifact.")

d("UNK-0024",
  claim_needed="A candidate-specific measured basis for the WEAK label on the cross-venue "
               "stale-quote tuple.",
  known_evidence="The M1-A report assigns WEAK on structural reasoning (latency/routing demands) "
                 "rather than on measured evidence for this candidate; its own text notes no "
                 "evidence package establishes non-colocated feasibility.",
  specific_evidence_needed="Latency/stale-quote measurements (UNK-0021) before the label can rest on "
                           "evidence.",
  decision_prevented="Nothing (the label is non-promoting); recorded so the judgment basis is not "
                     "mistaken for evidence.",
  severity="NON_BLOCKING", resolution_class="D", source_A="SRC-0011", source_B="SRC-0011",
  conflict_type="DIVERGENCE_IN_JUDGMENT",
  exact_conflict="Report label WEAK versus gate-derived ceiling 'BLOCKED gates, no direct SUPPORTS "
                 "evidence' would read as UNKNOWN. Resolved by keeping the report label and "
                 "recording the basis, not by averaging.",
  affected="TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG", status="OPEN")

d("UNK-0025",
  claim_needed="An external basis for the H1..H5 horizon banding used to derive horizon_min_us and "
               "horizon_max_us.",
  known_evidence="The band labels and approximate ranges appear in the M1-A artifact; the "
                 "millisecond-to-microsecond endpoints are a project convention.",
  specific_evidence_needed="None required for internal consistency; would only matter if bands were "
                           "used to compare against external studies.",
  decision_prevented="Nothing; recorded so derived microsecond values are not read as measured "
                     "market facts.",
  severity="NON_BLOCKING", resolution_class="D", source_A="SRC-0011", source_B="ASM-0001",
  conflict_type="METHOD_NOTE", affected="ALL_CANDIDATES", status="RESOLVED")

d("UNK-0026",
  claim_needed="Independent external verification of any System-One/Jev capability claim used as a "
               "premise (calibration transport, latency, cost of operation).",
  known_evidence="All available Jev material is vendor self-report or a project audit of a "
                 "user-provided document; no independent reproduction exists in this repository.",
  specific_evidence_needed="Independent benchmark or reproduction, or a sealed same-information "
                           "experiment performed by this project (UNK-0017).",
  decision_prevented="Any system-One admission; keeps the technology branch unfunded by default.",
  severity="IMPORTANT", resolution_class="C", source_A="SRC-0001", source_B="SRC-0020",
  can_M2_measure="YES", requires_m2_measurement="YES",
  evidence_ids="EVD-0023|EVD-0024|EVD-0025|EVD-0026")

_agg("UNK-0027",
  claim_needed="Exact instrument/contract/symbol specification for tuples that currently name a "
               "family rather than a tradable instrument (Treasury contract, WTI month, stock "
               "symbol, option class/expiry, event contract, FX pair/venue).",
  known_evidence="The M1-A tuple ledger deliberately uses family-level naming; several rows state "
                 "that instrument-level economics remain locked.",
  specific_evidence_needed="One exact instrument per surviving branch, with its tick/lot/matching "
                           "and fee facts.",
  decision_prevented="M2 registration and any falsifier (KG5) for the affected rows.",
  severity="BLOCKING", resolution_class="A", source_A="SRC-0011",
  affected="TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG|"
           "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|"
           "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG|TUP-EUREX-FESX-H2H3-OFIQ-MIX|"
           "TUP-CBOE-USOPT-H5-SURFRV-MIX|TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX|"
           "TUP-KALSHI-EVENT-H5-EVENTINF-AGG|TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG",
  web_research_resolvable="YES")

d("UNK-0028",
  claim_needed="Capital requirement and account/tier eligibility for the venues named in the "
               "survivor set (institutional access, margin, minimum size).",
  known_evidence="Coinbase/Kraken tier eligibility affects realized fees; CME and Eurex access "
                 "requires a broker/member path; no capital figures exist.",
  specific_evidence_needed="Broker/venue quotes for the intended account type plus margin and "
                           "minimum-size terms.",
  decision_prevented="Deployment-shape decisions (not M1 selection); also drives which fee tier "
                     "applies in M2 cost configuration.",
  severity="IMPORTANT", resolution_class="B", requires_vendor_quote="YES", affected="ALL_CANDIDATES")

d("UNK-0029",
  claim_needed="Capacity and market-impact evidence at an economically meaningful size for any "
               "survivor.",
  known_evidence="Nothing: capacity is explicitly listed as unknown in the project status artifact.",
  specific_evidence_needed="Impact and capacity curves measured in M2/M6-style escalation.",
  decision_prevented="Any capital decision; a micro-capacity edge with no business case cannot be "
                     "justified later without it.",
  severity="IMPORTANT", resolution_class="C", source_A="SRC-0024",
  can_M2_measure="YES", requires_m2_measurement="YES", affected="ALL_CANDIDATES")

d("UNK-0030",
  claim_needed="Confirmation that the M1-A state claim 'the Jev paper and the research OS were not "
               "retrievable' still holds.",
  known_evidence="Both artifacts are present in this repository and were ingested during M1-C; "
                 "their SHA-256 hashes are recorded in M1/raw/source_manifest.json.",
  specific_evidence_needed="Nothing further; the artifact-level audit exists (SRC-0020) and the "
                           "remaining gap is external verification of its premises (UNK-0026).",
  decision_prevented="Nothing now; it invalidates one of the two reasons the M1-A artifact gave for "
                     "its own incompleteness, so the M1-A status must be re-derived from the "
                     "remaining blockers rather than inherited.",
  severity="IMPORTANT", resolution_class="D", source_A="SRC-0011", source_B="SRC-0020",
  conflict_type="CONTRADICTION",
  exact_conflict="SRC-0011 states the paper and research OS were unavailable in its environment; "
                 "both files exist in the repository handed to M1-C.",
  suspected_reason="Different execution environments: the M1-A run did not have repository access.",
  status="RESOLVED")

d("UNK-0031",
  claim_needed="Transcription fidelity of the candidate-architecture paper's claim set.",
  known_evidence="The PDF has no text layer (image-only: 8 pages, 8 embedded images, zero fonts), "
                 "so its claims were read from pages rasterised at 140 dpi and transcribed by a "
                 "vision model. Every extracted number was cross-checked against the project audit "
                 "(SRC-0020) and against closed-form arithmetic where the quantities interact "
                 "(EVD-0028), but no second independent transcription exists.",
  specific_evidence_needed="A second independent transcription or an OCR pass over a higher-"
                           "resolution rasterisation, for every numeric claim used downstream.",
  decision_prevented="Nothing blocking; it bounds confidence in EVD-0025/EVD-0027/EVD-0029, which "
                     "are only used as premises about a candidate architecture, never as market "
                     "evidence.",
  severity="NON_BLOCKING", resolution_class="A", source_A="SRC-0010", source_B="SRC-0020",
  conflict_type="METHOD_NOTE", affected="TUP-SYSTEMONE-HARDCORE-ENGINE|"
                                         "TUP-JEV-HOSTED-LATENCY-UNMEASURED",
  web_research_resolvable="NO", status="OPEN")

DISCREPANCY_BY_ID = {row["issue_id"]: row for row in DISCREPANCIES}

OPEN_QUESTIONS = []


def q(question_id, question, why_it_matters, workstream, priority, gate, search_status,
      current_best_answer, unresolved_gap, next_search, related_issue_ids,
      legacy_question_id=UNKNOWN):
    OPEN_QUESTIONS.append(dict(
        question_id=question_id, question=question, why_it_matters=why_it_matters,
        workstream=workstream, priority=priority, answer_required_before_gate=gate,
        search_status=search_status, current_best_answer=current_best_answer,
        unresolved_gap=unresolved_gap, next_search=next_search,
        related_issue_ids=related_issue_ids, legacy_question_id=legacy_question_id,
        last_updated=_UPDATED))


q("OQ-0001", "Which of the M1-A external claims survive independent verification once every citation "
             "token resolves to a primary URL?",
  "The fee facts that already killed two candidates, and the feed-cadence fact that killed a third, "
  "are currently report-mediated rather than independently re-derived.",
  "Provenance", "HIGH", "M1-A_CLOSE", "not_started", "Tokens preserved; no URLs recoverable from "
  "repository artifacts.", "25 tokens unresolved.", "Resolve token by token against primary sources "
  "and snapshot each page.", "UNK-0023")

q("OQ-0002", "What is the project-level all-in per-contract cost for the CME candidates?",
  "It decides whether any CME tuple can survive aggressive execution.",
  "Venue economics", "CRITICAL", "M1-B", "not_started",
  "UNKNOWN: only CME market-data architecture was verified.", "No account-path fee schedule.",
  "Obtain FCM/broker schedule for the intended account and register it as an immutable M2 cost "
  "configuration.", "UNK-0001|UNK-0028")

q("OQ-0003", "What is the current CME matching/allocation rule for each named candidate contract "
             "and order type?",
  "Without it, no passive CME fill model or queue claim is admissible.",
  "Market structure", "CRITICAL", "M1-B", "not_started",
  "Only that rules are product-specific and can change by notice.", "No contract-level rule locked.",
  "Look up the rulebook per contract; record rule version.", "UNK-0002")

q("OQ-0004", "Can order-level historical data be licensed for CME, Nasdaq equities, Cboe BZX and "
             "Eurex at acceptable cost?",
  "Causal replay is a precondition for every passive or queue-dependent candidate.",
  "Data procurement", "CRITICAL", "M2_ENTRY", "not_started",
  "Product existence verified for CME/Nasdaq; price, licence, schema and timestamps unverified.",
  "No quote, no sample file.", "Request vendor quotes and run a schema/timestamp validation on a "
  "sample for each venue.", "UNK-0003|UNK-0004|UNK-0020|UNK-0022|UNK-0011")

q("OQ-0005", "Is the published OFI/queue-imbalance/microprice predictability still present, "
             "after costs, on any candidate venue in 2026?",
  "This is the only external result that currently justifies running a venue-specific test at all.",
  "Mechanism replication", "CRITICAL", "M1-B", "not_started",
  "Supported as information content in U.S. equities (2015 sample and earlier); no after-cost "
  "replication on any target venue.", "No current venue-specific net measure.",
  "Search for modern independent after-cost replications and for disconfirming studies; then design "
  "the venue-specific test.", "UNK-0009", legacy_question_id=UNKNOWN)

q("OQ-0006", "What is EV(delay) for each candidate signal?",
  "It determines the admissible compute/network budget and whether any model can be placed at the "
  "hypothesised horizon.",
  "Latency / half-life", "CRITICAL", "M1-B", "not_started",
  "UNKNOWN for every candidate; the report forbids inferring decay from 'next tick'.", "No curve "
  "exists.", "Run a controlled delay sweep once replay data exists.", "UNK-0008|UNK-0016")

q("OQ-0007", "What is P(fill | queue state) and E(markout | fill, state) for each passive candidate?",
  "Passive economics are undefined without both.",
  "Execution", "CRITICAL", "M2_ENTRY", "not_started", "UNKNOWN; touch=fills is disallowed.",
  "No queue-aware simulator or shadow-fill process exists yet.",
  "Build a queue-aware fill model under the venue's actual matching rule and validate against shadow "
  "observations.", "UNK-0007|UNK-0019")

q("OQ-0008", "Which exact instruments should the surviving branches be narrowed to?",
  "Several rows name a family, not a tradable contract, so no falsifier can be stated.",
  "Universe definition", "HIGH", "M1-B", "not_started",
  "Family-level naming only.", "No tick/lot/matching/fee facts at instrument level.",
  "Pick one instrument per branch on liquidity and data grounds, then lock its facts.", "UNK-0027",)

q("OQ-0009", "What are the fee, access and historical-data facts for Kalshi/Polymarket, Deribit, "
             "Eurex, Cboe options and the FX venues?",
  "These are the tuples whose entire feasibility is currently unverified.",
  "Venue economics", "HIGH", "M1-B", "not_started", "UNKNOWN across all five venue families.",
  "No primary-source lock.", "Per-venue primary research; jurisdiction matrix for event contracts.",
  "UNK-0011|UNK-0012|UNK-0013|UNK-0014|UNK-0015")

q("OQ-0010", "Are the venue fee facts that killed the crypto tuples current and correctly read?",
  "Two candidate deaths depend on verified fee schedules; misreading them would be a false kill.",
  "Venue economics", "HIGH", "M1-B", "not_started",
  "60/40 bps (Coinbase 0-10k), 40/80 bps (Kraken Tier 1) as reported.", "URL-level verification "
  "pending.", "Re-verify both schedules from primary pages and record snapshots.", "UNK-0023")

q("OQ-0011", "Does hosted Jev or a local System-One model add execution-aware net utility over a "
             "same-information logistic/tree baseline?",
  "This is the central falsification test for the paper's claimed architectural advantage and the "
  "only admissible basis for admitting System-One.",
  "System-One / Trading Architecture", "CRITICAL", "G4_ROBUSTNESS", "not_started",
  "No same-information controlled benchmark exists.", "No measured latency profile, no sealed "
  "utility comparison.", "Run only after market/horizon/data/execution baseline are fixed.",
  "UNK-0017|UNK-0026", legacy_question_id="Q-010")

q("OQ-0012", "What are this project's own live decision-to-market latency p50/p95/p99?",
  "Model placement, venue choice and horizon viability all depend on it.",
  "Latency", "CRITICAL", "M2_ENTRY", "not_started", "No instrumented path exists.",
  "No measurement.", "Instrument the shadow path and log the full timestamp contract.",
  "UNK-0016")

q("OQ-0013", "Which cost components can be parameterised conservatively rather than measured, and "
             "at what values?",
  "A cost-sensitivity surface is required by the project's own G4 gate and may kill branches cheaply.",
  "Execution economics", "MEDIUM", "G4_ROBUSTNESS", "not_started",
  "Only exchange fees are verified for two crypto venues and one equity venue.",
  "No spread/slippage/impact parameterisation.", "Define preregistered conservative ranges per venue "
  "and run the surface.", "UNK-0006|UNK-0032")

q("OQ-0014", "What evidence supports the persistence argument for each surviving mechanism "
             "(who keeps paying, and why do they not stop)?",
  "Persistence is a required invariant; 'it worked in 2015' is not a persistence argument.",
  "Edge provenance", "HIGH", "M1-B", "not_started",
  "Report gives payer interpretations that are EXTRAPOLATIONS; no persistence evidence.",
  "No risk/capacity/mandate evidence for any candidate.",
  "For each survivor, find evidence on payer constraints (mandates, balance sheet, latency budgets) "
  "or mark the persistence step UNKNOWN.", "UNK-0009|UNK-0029")

q("OQ-0015", "What historical-data timestamp semantics (exchange vs receive time, clock domain) can "
             "be relied upon for causal replay?",
  "A replay that cannot order events causally cannot be used to claim priority or fills.",
  "Data integrity", "HIGH", "M2_ENTRY", "not_started",
  "The project's timestamp contract is defined in methods; no vendor feed has been validated against "
  "it.", "No feed-level validation.", "Validate a sample file against the timestamp contract per "
  "venue.", "UNK-0003|UNK-0004")

q("OQ-0016", "Is the candidate architecture's target market actually inside the M1 candidate set?",
  "The paper targets a generic block-cadence on-chain venue and names no venue, instrument, "
  "account or fee schedule. If that market class is not among the M1 tuples, the System-One branch "
  "has no venue to be tested on, which changes what M1-B could even consider.",
  "Universe definition", "HIGH", "M1-B", "not_started",
  "No named venue in the paper; the M1 tuple ledger contains no block-cadence on-chain venue.",
  "No tuple exists for the architecture's own target market.",
  "Decide explicitly whether to add such a tuple (with its own fee/data/access lock) or to keep the "
  "architecture as an unhosted specimen.", "UNK-0023|UNK-0026", legacy_question_id=UNKNOWN)

QUESTION_BY_ID = {row["question_id"]: row for row in OPEN_QUESTIONS}