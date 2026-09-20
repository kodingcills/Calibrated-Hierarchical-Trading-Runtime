# DISCREPANCIES AND UNKNOWNS

Canonical machine-readable source: `M1/data/discrepancies.csv` (generated from `M1/src/corpus/unknowns.py`).
This file is a rendering of that registry; edit the corpus module, not this file.

Materialised (UTC): 2026-09-20T19:09:29Z

Registered issues: 50 | open: 30 | blocking: 29

Conflicts are never resolved by averaging. Where two sources genuinely disagree the row
carries `conflict_type=CONTRADICTION` and both statements are preserved; where the
divergence is a difference of judgment it carries `conflict_type=DIVERGENCE_IN_JUDGMENT`
and the judgment used is stated together with its basis.

## UNK-0001 - BLOCKING - EXTERNAL_REQUEST_READY

- claim needed: Exact project-level all-in per-contract cost for the CME candidates (exchange fee + clearing fee + NFA/FCM commission + market-data and connectivity).
- known evidence: CME market-data architecture and product structure are verified; no fee schedule value was captured in the M1-A pass.
- specific evidence required: Current CME/FCM schedule for the exact account path, registered as an immutable M2 cost configuration.
- decision prevented: Aggressive CME execution viability (KG3) for every CME tuple.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0107, B=None
- searches attempted: Two passes. M1-A searched CME product/MDP documentation and market-data infrastructure. The M1-C CMEFacts resolver then targeted fee and clearing-fee pages directly: both were blocked, no filed fee blackline was extracted, and the one figure surfaced came from a non-primary article with no recoverable URL, so it was rejected (see patch P-0003 modified_claims). Public search is exhausted for this milestone.
- resolvable by web research: PARTIAL (public schedules exist; the project's own commission path does not); vendor quote: YES; M2 measurement: NO
- resolution class: B
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG
- evidence: EVD-0001|EVD-0002|EVD-0018

## UNK-0002 - BLOCKING - IN_PROGRESS

- claim needed: The product-specific CME matching/allocation rule for each named candidate contract.
- known evidence: CME documents product-specific matching processes and has changed Treasury calendar-spread matching by notice.
- specific evidence required: The current rulebook/matching specification for the exact contract and order type, plus its change history.
- decision prevented: Any queue-position or fill model for passive CME candidates (KG2/KG3).
- conflict type: NO_CONFLICT_INCOMPLETENESS (Not a contradiction: the two sources agree that rules are product-specific and change over time; the current rule for a named contract is simply not captured.)
- sources: A=SRC-0112, B=SRC-0113
- searches attempted: None
- resolvable by web research: YES; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: A
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG|TUP-GENERIC-CME-QUEUE
- evidence: EVD-0003|EVD-0019

## UNK-0003 - BLOCKING - IN_PROGRESS

- claim needed: Whether a historical CME MBO/MBP package can be licensed at acceptable cost with usable timestamp semantics.
- known evidence: CME advertises historical/real-time products including up to full order book.
- specific evidence required: Vendor quote plus a sample file whose schema and timestamp fields are validated against a live feed.
- decision prevented: Causal queue replay for CME candidates (KG2), and therefore M2 for them.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0123, B=None
- searches attempted: M1-A pass could not verify the exact historical MBO package and cost.
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG
- evidence: EVD-0018

## UNK-0004 - BLOCKING - EXTERNAL_REQUEST_READY

- claim needed: Whether order-level historical U.S. equity depth (ITCH/TotalView depth) can be procured at acceptable cost.
- known evidence: Consolidated Tick History is verified Level-1 only; TotalView live depth is verified available; no paid order-level history was acquired in the M1-A pass.
- specific evidence required: Order-level historical product, license terms, sample and cost.
- decision prevented: Queue-aware backtesting of every Nasdaq equity tuple (KG2).
- conflict type: NO_CONFLICT_INCOMPLETENESS (Product-scope difference, not a contradiction: Tick History (L1) and TotalView (full depth) are different products; the risk is backtesting a queue strategy on the easier product.)
- sources: A=SRC-0109, B=SRC-0108
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG
- evidence: EVD-0005|EVD-0004

## UNK-0005 - BLOCKING - IN_PROGRESS

- claim needed: Current U.S. equity fee tier and routing economics actually available to this project (Nasdaq main book, Cboe BZX fee codes, CAT/broker/clearing).
- known evidence: Cboe BZX standard displayed-add rebate and removal fee are verified; Nasdaq main-book small-prop tier was not locked.
- specific evidence required: Broker/venue fee schedule for the project's exact routing and account type, per fee code.
- decision prevented: Net-economics arithmetic for equity tuples (KG3).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0114, B=None
- searches attempted: None
- resolvable by web research: PARTIAL (published schedules exist; the project's routing outcome does not); vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG
- evidence: EVD-0006|EVD-0021

## UNK-0006 - IMPORTANT - OPEN

- claim needed: The full break-even cost envelope (spread, fees, slippage, adverse selection, impact) for each candidate.
- known evidence: Two crypto venues have verified exchange-fee floors; no spread/slippage/impact/adverse-selection values are verified for any candidate.
- specific evidence required: Measured or explicitly parameterised values for every break-even component, per candidate.
- decision prevented: Any statement that a candidate is net-profitable; the strongest permitted statement is a known cost floor.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0105|SRC-0106|SRC-0114, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: ALL_CANDIDATES
- evidence: EVD-0006|EVD-0007|EVD-0008

## UNK-0007 - IMPORTANT - OPEN

- claim needed: Passive fill probability conditional on queue state.
- known evidence: No defensible fill probability was found; the report explicitly declines to estimate one; touch=fills is disallowed.
- specific evidence required: Queue-aware fill model validated against shadow/live observations, including partial fills and cancellation distinction.
- decision prevented: Economic evaluation of every passive candidate (KG3).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|TUP-METHOD-PASSIVE-TOUCHFILL
- evidence: None

## UNK-0008 - IMPORTANT - OPEN

- claim needed: Empirical signal half-life: the EV-versus-delay curve for each candidate signal.
- known evidence: 'Next tick' and 'short horizon' results exist, but no candidate-specific EV(delay) curve; the queue-imbalance study predicts a next-price move, not decay.
- specific evidence required: Delay-sweep measurement (e.g. 0/10/25/50/100/250/500 ms, 1/2/5 s where physically appropriate) reporting gross conditional markout and execution-aware EV.
- decision prevented: Latency budget allocation, model placement and any ALIVE label (KG4).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: ALL_CANDIDATES
- evidence: EVD-0012|EVD-0013

## UNK-0009 - BLOCKING - OPEN

- claim needed: Modern, venue-specific, after-cost replication (or explicit disconfirmation) for the mechanism each candidate relies on. The only external mechanism evidence in this package is the U.S.-equity OFI/queue-imbalance/microprice literature; every other candidate borrows a mechanism that has no current, on-venue, after-cost replication at all.
- known evidence: Mechanism support exists for U.S. equities (2015 and earlier samples), primarily predictive and gross.
- specific evidence required: Independent current replication on the exact venue/instrument including realistic costs, or an explicit disconfirming study.
- decision prevented: Mechanism credibility (KG1) for every candidate whose mechanism has no current, on-venue, after-cost replication.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0101|SRC-0102, B=None
- searches attempted: None
- resolvable by web research: YES; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: A
- affected: ALL_CANDIDATES
- evidence: EVD-0012|EVD-0013|EVD-0014

## UNK-0010 - BLOCKING - IN_PROGRESS

- claim needed: Hyperliquid trading-fee schedule, event-level historical L2 source and market-wide liquidation observability.
- known evidence: Live public l2Book/BBO/trades schema verified, including the >= 0.5 s snapshot cadence; fee schedule and historical replay product not verified.
- specific evidence required: Current fee schedule, historical event-level L2 product with timestamps, and the venue's liquidation-data surface.
- decision prevented: Net-edge feasibility for the Hyperliquid H3/H4 candidates.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0111, B=None
- searches attempted: M1-A pass could not verify the exact current fee schedule and historical replay product.
- resolvable by web research: PARTIAL; vendor quote: PARTIAL; M2 measurement: UNKNOWN
- resolution class: A
- affected: TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX|TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS
- evidence: EVD-0009|EVD-0010

## UNK-0011 - BLOCKING - OPEN

- claim needed: Eurex execution fees, product allocation rule, historical EOBI acquisition cost and broker/participant access path.
- known evidence: T7 14.1 EOBI/EMDI/ETI documentation verified.
- specific evidence required: Instrument-specific fee schedule, matching rule, historical data quote and access route.
- decision prevented: Any Eurex candidate progressing beyond universe status.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0110, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-EUREX-FESX-H2H3-OFIQ-MIX
- evidence: EVD-0011

## UNK-0012 - BLOCKING - OPEN

- claim needed: Cboe options class/order-type fee decomposition plus historical surface/depth data and hedging mechanics for a named option tuple.
- known evidence: A Cboe options fee schedule effective 2026-09-01 was located; class/order-type economics were not decomposed.
- specific evidence required: Fee codes for the exact order types, OPRA versus proprietary depth history, and point-in-time surface data.
- decision prevented: Options tuples passing Gate 2 at all.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0116, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-CBOE-USOPT-H5-SURFRV-MIX
- evidence: None

## UNK-0013 - BLOCKING - IN_PROGRESS

- claim needed: Deribit current access, fee, API semantics and historical book/surface data.
- known evidence: Venue relevance only; current primary specifications were not locked.
- specific evidence required: 2026 access/fee schedule, API contract and historical book product.
- decision prevented: Gate 2 for the Deribit tuple.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX
- evidence: None

## UNK-0014 - BLOCKING - IN_PROGRESS

- claim needed: Jurisdiction-by-jurisdiction access, fee schedule, matching/API semantics and historical data for Kalshi and Polymarket.
- known evidence: Washington obtained a 2026 court order affecting Kalshi in that state: state-level restrictions demonstrably exist.
- specific evidence required: A current per-contract access matrix plus fee/API/history facts.
- decision prevented: Legality/access gate for both event-market tuples.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0121, B=None
- searches attempted: None
- resolvable by web research: YES; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: A
- affected: TUP-KALSHI-EVENT-H5-EVENTINF-AGG|TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG
- evidence: EVD-0016

## UNK-0015 - BLOCKING - OPEN

- claim needed: An exact FX venue (ECN or broker), participant class, feed, order protocol and last-look/execution mechanics.
- known evidence: Nothing venue-specific: 'FX' was never a valid unit of analysis.
- specific evidence required: A named venue plus participant status and its published or contractual execution policy.
- decision prevented: Defining the tuple at all (KG1/KG3/KG5).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: PARTIAL (public institutional facts exist; participant status does not); vendor quote: PARTIAL; M2 measurement: UNKNOWN
- resolution class: A
- affected: TUP-FX-ECN-H2H3-LEADLAG-AGG|TUP-FX-RETAILBROKER-H3H4-FEEDLAG-AGG
- evidence: None

## UNK-0016 - IMPORTANT - OPEN

- claim needed: Measured decision-to-market latency distribution (p50/p95/p99 plus jitter and deadline-miss rate) for this project's own stack.
- known evidence: No live path exists yet; the requirement is stated in the project's methods (timestamp contract, decision-age metrics).
- specific evidence required: Instrumented shadow-run latency measurements.
- decision prevented: Placing any model at any horizon (KG3/KG4).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0016, B=SRC-0018
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: ALL_CANDIDATES
- evidence: None

## UNK-0017 - IMPORTANT - OPEN

- claim needed: Reproducible hosted-Jev/local-System-One latency profile and incremental execution-aware utility versus a same-information classical baseline.
- known evidence: Vendor-reported 70-500 ms end-to-end range only; no independent reproduction; no sealed utility comparison exists.
- specific evidence required: Measured p50/p95/p99 under trading-like load plus sealed same-information utility comparison.
- decision prevented: Any System-One admission decision; determines whether the Jev branch is worth funding at all.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0001, B=SRC-0015
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: TUP-SYSTEMONE-HARDCORE-ENGINE|TUP-JEV-HOSTED-LATENCY-UNMEASURED
- evidence: EVD-0023|EVD-0024|EVD-0026

## UNK-0018 - BLOCKING - IN_PROGRESS

- claim needed: Validated timestamp semantics for historical and live feeds (exchange/event time versus receive time, clock domain, sequence integrity) sufficient for causal replay.
- known evidence: The project's timestamp contract is defined in its methods (SRC-0016) and the reality-gap decomposition depends on it, but no venue's feed or historical file has been validated against that contract.
- specific evidence required: A sample historical file and a live capture per venue, with the timestamp fields mapped and checked for ordering, duplication and clock domain.
- decision prevented: Causal replay and therefore every queue, priority or fill claim; applies to any candidate that reaches replay.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0111, B=SRC-0118
- searches attempted: None
- resolvable by web research: PARTIAL; vendor quote: YES; M2 measurement: YES
- resolution class: B
- affected: ALL_CANDIDATES
- evidence: EVD-0010|EVD-0018

## UNK-0032 - IMPORTANT - OPEN

- claim needed: Cost-sensitivity behaviour: does any surviving candidate remain viable under conservative fee/slippage assumptions?
- known evidence: The two crypto tuples die on the fee floor alone; no sensitivity surface exists for any other candidate.
- specific evidence required: Cost-sensitivity surface over fee/slippage/spread assumptions per candidate.
- decision prevented: Robustness judgment (required by the project's own G4 gate).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0014, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: ALL_CANDIDATES
- evidence: None

## UNK-0019 - IMPORTANT - OPEN

- claim needed: Fill-conditioned markout distribution (adverse selection) for every passive or crossing candidate.
- known evidence: Mechanically uncontroversial but unmeasured in this evidence package.
- specific evidence required: Markouts conditional on own fills, from replay with a validated fill model and later from shadow/micro-live.
- decision prevented: Passive-candidate economics; also the crossing case where the signal selects into an already-moving price.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG
- evidence: None

## UNK-0020 - BLOCKING - RESOLVED_SUPPORTS

- claim needed: Historical NOII/auction execution data source and cost.
- known evidence: NOII existence and public dissemination verified; historical depth/cost not locked.
- specific evidence required: Historical auction-imbalance dataset with exact dissemination timestamps.
- decision prevented: Auction tuple feasibility (KG2): without it the auction candidate has no historical basis for testing.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0108, B=SRC-0120
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG
- evidence: None

## UNK-0021 - IMPORTANT - OPEN

- claim needed: Cross-venue source-to-decision-to-venue latency and stale-quote survival for a multi-venue U.S. equity tuple.
- known evidence: No evidence package establishes non-colocated feasibility; the report notes the obvious forms are contested by dedicated low-latency firms.
- specific evidence required: Measured cross-feed synchronization, decision age and the fraction of stale quotes still present at order arrival.
- decision prevented: Whether the cross-venue tuple is a real opportunity or an infrastructure race.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG
- evidence: None

## UNK-0022 - BLOCKING - EXTERNAL_REQUEST_READY

- claim needed: Cboe BZX proprietary depth availability, fee-code outcome and order-level history for this project's access path.
- known evidence: Standard rebate/remove rates verified; nothing about data access or realized fee codes.
- specific evidence required: Feed/data entitlement list and a sample of realized fee codes.
- decision prevented: BZX passive tuple feasibility (KG2/KG3).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0114, B=SRC-0125
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS
- evidence: EVD-0006|EVD-0021

## UNK-0023 - BLOCKING - IN_PROGRESS

- claim needed: Resolvable identities (URL/DOI) for the 25 external sources the M1-A report cites only through opaque internal citation tokens.
- known evidence: Tokens are preserved verbatim and the report names most sources descriptively (organisation, venue, sometimes author/year), but no URL is reconstructible from repository artifacts.
- specific evidence required: Token-by-token resolution to a primary URL with an access snapshot.
- decision prevented: Independent verification of any external claim, including fee schedules that already killed candidates; the arithmetic is unaffected, the auditability is.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0011, B=None
- searches attempted: None
- resolvable by web research: YES; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: A
- affected: ALL_EXTERNAL_EVIDENCE
- evidence: None

## UNK-0024 - NON_BLOCKING - OPEN

- claim needed: A candidate-specific measured basis for the WEAK label on the cross-venue stale-quote tuple.
- known evidence: The M1-A report assigns WEAK on structural reasoning (latency/routing demands) rather than on measured evidence for this candidate; its own text notes no evidence package establishes non-colocated feasibility.
- specific evidence required: Latency/stale-quote measurements (UNK-0021) before the label can rest on evidence.
- decision prevented: Nothing (the label is non-promoting); recorded so the judgment basis is not mistaken for evidence.
- conflict type: DIVERGENCE_IN_JUDGMENT (Report label WEAK versus gate-derived ceiling 'BLOCKED gates, no direct SUPPORTS evidence' would read as UNKNOWN. Resolved by keeping the report label and recording the basis, not by averaging.)
- sources: A=SRC-0011, B=SRC-0011
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: D
- affected: TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG
- evidence: None

## UNK-0025 - NON_BLOCKING - RESOLVED

- claim needed: An external basis for the H1..H5 horizon banding used to derive horizon_min_us and horizon_max_us.
- known evidence: The band labels and approximate ranges appear in the M1-A artifact; the millisecond-to-microsecond endpoints are a project convention.
- specific evidence required: None required for internal consistency; would only matter if bands were used to compare against external studies.
- decision prevented: Nothing; recorded so derived microsecond values are not read as measured market facts.
- conflict type: METHOD_NOTE
- sources: A=SRC-0011, B=ASM-0001
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: D
- affected: ALL_CANDIDATES
- evidence: None

## UNK-0026 - IMPORTANT - OPEN

- claim needed: Independent external verification of any System-One/Jev capability claim used as a premise (calibration transport, latency, cost of operation).
- known evidence: All available Jev material is vendor self-report or a project audit of a user-provided document; no independent reproduction exists in this repository.
- specific evidence required: Independent benchmark or reproduction, or a sealed same-information experiment performed by this project (UNK-0017).
- decision prevented: Any system-One admission; keeps the technology branch unfunded by default.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0001, B=SRC-0020
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: None
- evidence: EVD-0023|EVD-0024|EVD-0025|EVD-0026

## UNK-0027 - BLOCKING - OPEN

- claim needed: Exact instrument/contract/symbol specification for tuples that currently name a family rather than a tradable instrument (Treasury contract, WTI month, stock symbol, option class/expiry, event contract, FX pair/venue).
- known evidence: The M1-A tuple ledger deliberately uses family-level naming; several rows state that instrument-level economics remain locked.
- specific evidence required: One exact instrument per surviving branch, with its tick/lot/matching and fee facts.
- decision prevented: M2 registration and any falsifier (KG5) for the affected rows.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0011, B=None
- searches attempted: None
- resolvable by web research: YES; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: A
- affected: TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG|TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG|TUP-EUREX-FESX-H2H3-OFIQ-MIX|TUP-CBOE-USOPT-H5-SURFRV-MIX|TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX|TUP-KALSHI-EVENT-H5-EVENTINF-AGG|TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG
- evidence: None

## UNK-0028 - BLOCKING - OPEN

- claim needed: Capital requirement and account/tier eligibility for the venues named in the survivor set (institutional access, margin, minimum size).
- known evidence: Coinbase/Kraken tier eligibility affects realized fees; CME and Eurex access requires a broker/member path; no capital figures exist.
- specific evidence required: Broker/venue quotes for the intended account type plus margin and minimum-size terms.
- decision prevented: Deployment-shape decisions (not M1 selection); also drives which fee tier applies in M2 cost configuration.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: YES; M2 measurement: UNKNOWN
- resolution class: B
- affected: ALL_CANDIDATES
- evidence: None

## UNK-0029 - IMPORTANT - OPEN

- claim needed: Capacity and market-impact evidence at an economically meaningful size for any survivor.
- known evidence: Nothing: capacity is explicitly listed as unknown in the project status artifact.
- specific evidence required: Impact and capacity curves measured in M2/M6-style escalation.
- decision prevented: Any capital decision; a micro-capacity edge with no business case cannot be justified later without it.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0024, B=None
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: YES
- resolution class: C
- affected: ALL_CANDIDATES
- evidence: None

## UNK-0030 - NON_BLOCKING - RESOLVED

- claim needed: Confirmation that the M1-A state claim 'the Jev paper and the research OS were not retrievable' still holds.
- known evidence: Both artifacts are present in this repository and were ingested during M1-C; their SHA-256 hashes are recorded in M1/raw/source_manifest.json.
- specific evidence required: Nothing further; the artifact-level audit exists (SRC-0020) and the remaining gap is external verification of its premises (UNK-0026).
- decision prevented: Nothing now; it invalidates one of the two reasons the M1-A artifact gave for its own incompleteness, so the M1-A status must be re-derived from the remaining blockers rather than inherited.
- conflict type: CONTRADICTION (SRC-0011 states the paper and research OS were unavailable in its environment; both files exist in the repository handed to M1-C.)
- sources: A=SRC-0011, B=SRC-0020
- searches attempted: None
- resolvable by web research: UNKNOWN; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: D
- affected: None
- evidence: None

## UNK-0031 - NON_BLOCKING - OPEN

- claim needed: Transcription fidelity of the candidate-architecture paper's claim set.
- known evidence: The PDF has no text layer (image-only: 8 pages, 8 embedded images, zero fonts), so its claims were read from pages rasterised at 140 dpi and transcribed by a vision model. Every extracted number was cross-checked against the project audit (SRC-0020) and against closed-form arithmetic where the quantities interact (EVD-0028), but no second independent transcription exists.
- specific evidence required: A second independent transcription or an OCR pass over a higher-resolution rasterisation, for every numeric claim used downstream.
- decision prevented: Nothing blocking; it bounds confidence in EVD-0025/EVD-0027/EVD-0029, which are only used as premises about a candidate architecture, never as market evidence.
- conflict type: METHOD_NOTE
- sources: A=SRC-0010, B=SRC-0020
- searches attempted: None
- resolvable by web research: NO; vendor quote: UNKNOWN; M2 measurement: UNKNOWN
- resolution class: A
- affected: TUP-SYSTEMONE-HARDCORE-ENGINE|TUP-JEV-HOSTED-LATENCY-UNMEASURED
- evidence: None

## UNK-0018-CME - BLOCKING - OPEN

- claim needed: Timestamp semantics for CME market data: which field is exchange event time, which is receive time, the clock domain and the ordering guarantee.
- known evidence: MDP 3.0 documents MDEntryTime and TransactTime (nanosecond unit) but not the clock domain (SRC-0235); MDP uses dual-feed UDP multicast with sequence numbers (SRC-0115).
- specific evidence required: A written answer from CME market-data support, or a sample file whose sequence and timestamp fields are validated against the project's timestamp contract.
- decision prevented: Causal replay for every CME candidate (KG2).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0235, B=SRC-0115
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG
- evidence: None

## UNK-0018-NASDAQ - BLOCKING - OPEN

- claim needed: Timestamp semantics for Nasdaq order-level history and the live TotalView feed: event versus receive time, sequence integrity and clock domain for the historical files.
- known evidence: The historical product, its SFTP delivery and its depth are confirmed (SRC-0201); the message specification defines order-reference fields but the resolver did not extract timestamp-field semantics.
- specific evidence required: The ITCH message specification's timestamp section plus a sample day whose ordering and sequence fields validate against the project's contract.
- decision prevented: Causal replay and therefore queue/fill claims for the Nasdaq equity rows (KG2).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0201, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG
- evidence: None

## UNK-0018-BZX - BLOCKING - OPEN

- claim needed: Timestamp semantics for the Cboe BZX depth feed and any historical depth archive.
- known evidence: A historical depth archive is confirmed to exist (SRC-0205); no timestamp-field documentation was extracted.
- specific evidence required: Cboe depth-feed specification and a sample with field-level timestamp semantics.
- decision prevented: Causal replay for the BZX passive tuple (KG2).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0205, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS
- evidence: None

## UNK-0018-HYPERLIQUID - BLOCKING - OPEN

- claim needed: Timestamp semantics and completeness rules for the official Hyperliquid archive: block time fields, per-hour file coverage and how to detect missing data.
- known evidence: The archive layout is documented (SRC-0214) and the live feed is documented as block-cadenced with an at-least-0.5s snapshot rule (SRC-0216); field-level archive semantics and a completeness rule are not documented.
- specific evidence required: The archive's file schema and a sample hour, plus a stated rule for missing hours.
- decision prevented: Replay validity for the Hyperliquid seconds-scale tuples (KG2).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0214, B=SRC-0216
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX
- evidence: None

## UNK-0018-EUREX - BLOCKING - OPEN

- claim needed: Timestamp semantics for Eurex EOBI order-book messages.
- known evidence: EOBI/EMDI/ETI interfaces are documented (SRC-0110); no timestamp-field semantics or sample were extracted.
- specific evidence required: T7 EOBI message specification timestamp section, plus an access path to a sample.
- decision prevented: Causal replay for the Eurex tuple (KG2).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0110, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-EUREX-FESX-H2H3-OFIQ-MIX
- evidence: None

## UNK-0018-USSTOCK-CROSS - BLOCKING - OPEN

- claim needed: Cross-venue synchronisation for the national-market tuple: can several venue feeds be placed on one comparable timeline with the accuracy the hypothesis needs?
- known evidence: No multi-venue synchronised package is locked; NYSE/IEX direct-feed history was outside the M1-A coverage.
- specific evidence required: Per-feed timestamp semantics plus a documented synchronisation method and its error bound.
- decision prevented: Causal cross-venue comparison, and therefore the stale-quote tuple (KG2/KG3).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG
- evidence: None

## UNK-0009-MECH-CME - BLOCKING - OPEN

- claim needed: Does the order-flow-imbalance / queue mechanism have direct or closely comparable evidence on CME equity-index futures?
- known evidence: The mechanism is evidenced on US equities (SRC-0101, SRC-0102); CME matching is engine-assigned per product (SRC-0235). No CME-specific replication was located.
- specific evidence required: A study on CME index futures (or an exchange-documented equivalent) establishing short-horizon flow/price predictability, with its sample and horizon stated.
- decision prevented: KG1 for every CME candidate (mechanism plausibility, not profitability).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0102, B=SRC-0235
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG
- evidence: None

## UNK-0009-MECH-NASDAQ-MICRO - BLOCKING - OPEN

- claim needed: Is there venue-specific evidence for the micro-price mechanism on a named US equity venue, as opposed to a venue-unspecified estimator result?
- known evidence: The micro-price paper's publisher metadata establishes the estimator claim but its sample venue could not be established from accessible metadata (SSRN returned HTTP 403; no arXiv preprint; CrossRef and RePEc carry no venue).
- specific evidence required: An author or publisher version of the paper that states its dataset, venue, instrument universe and horizon, or a separate venue-specific micro-price study.
- decision prevented: KG1 for the Nasdaq micro-price tuple.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG
- evidence: None

## UNK-0009-ECON-CRYPTO-SPOT - BLOCKING - OPEN

- claim needed: Is there a documented upper bound on the plausible gross seconds-scale effect on large crypto spot venues that could be compared against a verified fee floor?
- known evidence: Verified round-trip exchange-fee floors: 120 bps on Coinbase at the 0-10k tier (SRC-0105) and 160 bps on Kraken Tier 1 (SRC-0106). No sourced bound on the plausible gross effect for a seconds-scale microprice/OFI signal on those venues exists in the package.
- specific evidence required: A venue-specific study (or an exchange-published statistic) bounding achievable short-horizon gross movement on Coinbase or Kraken, sufficient to decide whether a 120-160 bps round trip is arithmetically out of reach.
- decision prevented: Whether the crypto spot branch can be killed on materiality rather than left blocked: a cost level alone is not a kill (D-0022).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0105, B=SRC-0106
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG|TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG|TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX
- evidence: None

## UNK-0009-ECON-EQUITY-MEASURED - IMPORTANT - OPEN

- claim needed: After-cost replication of the equity mechanisms at the project's own fee tier.
- known evidence: Base-tier equity fees are verified in native units (SRC-0203, SRC-0206, SRC-0209) and the mechanism is evidenced pre-cost (SRC-0101).
- specific evidence required: Execution-aware replication on the project's own fill model.
- decision prevented: Whether the equity branch is profitable, which M2 exists to measure.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS
- evidence: None

## UNK-0009-ECON-CME-MEASURED - IMPORTANT - OPEN

- claim needed: After-cost replication on CME once the cost schedule and matching rule are known.
- known evidence: No CME fee value is verified; the public fee search is exhausted (patch P-0003).
- specific evidence required: Execution-aware replication after the cost configuration is locked.
- decision prevented: Whether the CME branch is profitable (M2).
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG
- evidence: None

## UNK-0023-LIT - BLOCKING - IN_PROGRESS

- claim needed: Independent verifiability of the microstructure literature claims that gates depend on (queue imbalance, order-flow imbalance, micro-price).
- known evidence: Gould & Bonart is now identified from author/arXiv/SSRN records (SRC-0238) and Stoikov from publisher metadata (SRC-0239); the Cont, Kukanov & Stoikov order-flow claim remains report-mediated with an unresolved token.
- specific evidence required: An authoritative record for the order-flow-imbalance claim (publisher metadata plus an author or repository version) establishing its sample and venue.
- decision prevented: KG1 for candidates that would borrow the order-flow mechanism, and auditability of the mechanism-evidence row already in the ledger.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0102, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG|TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG|TUP-EUREX-FESX-H2H3-OFIQ-MIX
- evidence: None

## UNK-0023-CME-DOCS - BLOCKING - OPEN

- claim needed: Independent verifiability of the CME technical claims used by CME gates (MDP capability, matching product-specificity, historical product advertising, fixed-income definitions).
- known evidence: Partially re-derived: matching algorithms and DataMine MBO FIX history now come from primary client-wiki sources (SRC-0235 to SRC-0237). MDP capability, the matching change notice and the historical-product claims still rest on report tokens.
- specific evidence required: Primary CME pages (MDP product documentation, rulebook chapter, data-services product page) captured with dates.
- decision prevented: KG1/KG2 evidence quality for the CME rows, and auditability of the MDP feasibility claim.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0107, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG
- evidence: None

## UNK-0023-EXCH-OTHER - BLOCKING - OPEN

- claim needed: Independent verifiability of the remaining exchange claims: Eurex T7 interfaces, the Cboe options fee schedule, and the Nasdaq IPO-process claim.
- known evidence: Eurex T7, the Cboe options schedule and the Nasdaq IPO display-only period still rest on report tokens; the Cboe equities schedule and Nasdaq products were re-derived in iteration 1.
- specific evidence required: Primary pages for each remaining claim, captured with dates.
- decision prevented: Evidence quality for the Eurex tuple and for the options candidate's Gate-2 status.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0110, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-EUREX-FESX-H2H3-OFIQ-MIX|TUP-CBOE-USOPT-H5-SURFRV-MIX|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG
- evidence: None

## UNK-0023-PAIRED-TOKENS - NON_BLOCKING - OPEN

- claim needed: Whether the paired citation tokens (turn10search28, turn16search20, turn20view3) refer to distinct sources or are duplicates of an already re-derived source.
- known evidence: In two of three cases a paired token accompanies an already-identified source in the same claim; the report does not distinguish them.
- specific evidence required: Nothing further is required for M1: the claims are covered by the identified source.
- decision prevented: Nothing decision-critical; recorded so the token inventory is complete.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=None, B=None
- searches attempted: None
- resolvable by web research: None; vendor quote: None; M2 measurement: None
- resolution class: None
- affected: TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG|TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG
- evidence: None

## UNK-0033 - BLOCKING - OPEN

- claim needed: Sponsored-access cost: broker commission/markup for routed order flow, which no exchange or regulator publishes.
- known evidence: Exchange-side fee schedules are published per venue; the sponsor's commission is a private contract, so the all-in cost of a sponsored path cannot be assembled from public sources.
- specific evidence required: A chosen sponsor's published commission schedule or a written quote for the intended order flow.
- decision prevented: All-in per-share cost for every equity tuple, and therefore the cost floor used in KG3.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0201, B=SRC-0202
- searches attempted: None
- resolvable by web research: None; vendor quote: YES; M2 measurement: None
- resolution class: None
- affected: TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG
- evidence: None

## UNK-0034 - BLOCKING - OPEN

- claim needed: The operator's jurisdiction and client classification.
- known evidence: Venue terms and regulations now specify explicit exclusions: Hyperliquid excludes US and Ontario persons; Deribit prohibits the US; Kalshi restricts many countries and faces active Washington and Nevada orders; international Polymarket blocks US persons while Polymarket US is a separate product.
- specific evidence required: Three facts stated by the operator: (1) legal domicile/jurisdiction of the operating person or entity; (2) entity/person classification, including professional versus non-professional status where a venue distinguishes; (3) intended account/entity type per venue if materially relevant to eligibility.
- decision prevented: Access legality for four venue families, and therefore KG3 and KG5 for their candidates: no fill or cost model matters for a venue the operator may not use.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0213, B=SRC-0214
- searches attempted: None
- resolvable by web research: None; vendor quote: NO; M2 measurement: None
- resolution class: None
- affected: TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS|TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX|TUP-KALSHI-EVENT-H5-EVENTINF-AGG|TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG|TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX|TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG|TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG
- evidence: None

## UNK-0035 - IMPORTANT - OPEN

- claim needed: Version control for venue fee schedules that publish no effective date or version archive.
- known evidence: Hyperliquid's fee page and Polymarket's fee documentation carry no effective date; Deribit's page gives one update date rather than per-row versions; Kalshi's schedule states an effective date but its production URL was rate-limited at access time.
- specific evidence required: A dated, hashed snapshot of each fee page taken by the project, re-taken on a fixed schedule, with the figure used by any cost model tied to the snapshot it came from.
- decision prevented: After-cost replication validity: a cost model built on an undated dynamic page cannot be shown to describe the period it is tested on.
- conflict type: NO_CONFLICT_INCOMPLETENESS
- sources: A=SRC-0213, B=SRC-0214
- searches attempted: None
- resolvable by web research: None; vendor quote: NO; M2 measurement: None
- resolution class: None
- affected: TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS|TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX|TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG
- evidence: None
