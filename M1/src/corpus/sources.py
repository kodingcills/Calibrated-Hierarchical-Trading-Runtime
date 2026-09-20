"""Source registry (SRC-*).

Three provenance families
-------------------------
SRC-0001..SRC-0010  canonical Trading Research OS literature registry
                    (trading_research_os_v0.2/templates/literature.csv). URLs and
                    metadata are copied verbatim from that repository artifact.
SRC-0011..SRC-0026  project artifacts that exist inside this repository, including the
                    M1-A external-evidence artifact and the handoff/governance documents.
SRC-0101..SRC-0125  external sources *referenced by* the M1-A report through opaque
                    internal citation tokens. The tokens are preserved verbatim in
                    ``raw_citation_token``. No URL for these sources is reconstructible
                    from repository artifacts, so ``url`` is UNKNOWN for every one of
                    them, exactly as required by the handoff (ZI-0.3.3 / C3). Resolving
                    token -> URL is registered as OQ-0012 / UNK-0023.

Token ids are assigned by first appearance of the token in
``deep-research-report.md`` (verified by a one-line grep, reproducible from the file).
"""

from .constants import UNKNOWN

COLUMNS = [
    "source_id",
    "title",
    "authors_or_org",
    "publication_date",
    "access_date",
    "date_basis",
    "url",
    "doi",
    "source_type",
    "primary_or_secondary",
    "market",
    "venue",
    "sample_period",
    "sample_size",
    "methodology",
    "gross_or_net",
    "independent_replication",
    "limitations",
    "raw_citation_token",
    "local_path",
    "sha256",
    "status",
    "claim_scope",
]

REPORT = "SRC-0011"


def _row(**kw):
    row = {c: UNKNOWN for c in COLUMNS}
    row.update(kw)
    return row


# --------------------------------------------------------------------------
# Canonical research-os literature registry (verbatim from templates/literature.csv)
# --------------------------------------------------------------------------
_OS_SOURCES = [
    (1, "Introducing System One Models & Jev", "TypeSafe AI", "2026",
     "https://typesafe.ai/blog/introducing-system-one-models-and-jev", "primary_official",
     "Vendor description of Jev/System-One architecture, parallel sampler, RLCD, and a "
     "vendor-reported 70-500 ms end-to-end latency range.",
     "No architecture, weights, or RLCD objective disclosed; not independently reproduced."),
    (2, "Jev 1.13 jaggedness", "TypeSafe AI", "2026",
     "https://docs.typesafe.ai/model-jaggedness/jev-1.13", "primary_official",
     "Vendor-reported failure modes: weak arithmetic/counting/numeric precision, literal "
     "phrasing sensitivity, no structural identities across related questions.",
     "Version-specific; may change in later versions."),
    (3, "Adaptive Conformal Inference Under Distribution Shift", "Gibbs & Candes", "2021",
     "https://arxiv.org/abs/2106.00170", "paper",
     "Adaptive conformal method targeting long-run coverage under drift.",
     "Does not itself calibrate posterior probabilities."),
    (4, "Beta calibration", "Kull, Silva Filho, Flach", "2017",
     "https://proceedings.mlr.press/v54/kull17a.html", "peer_reviewed",
     "Beta calibration improves on logistic recalibration in studied cases.",
     "Static method does not solve arbitrary nonstationarity."),
    (5, "JAX-LOB", "Frey et al.", "2023", "https://arxiv.org/abs/2308.13289", "paper",
     "GPU-accelerated limit-order-book simulation environment.",
     "Simulator fidelity must be independently assessed for a chosen venue."),
    (6, "Queue-Reactive Model", "Huang, Lehalle, Rosenbaum", "2013",
     "https://arxiv.org/abs/1312.0563", "paper",
     "Queue-conditioned event-intensity model of limit-order-book dynamics.",
     "May not capture all endogenous/adversarial effects."),
    (7, "LOB Simulation and Trade Evaluation with KNN Resampling",
     "Giegrich, Oomen, Reisinger", "2024", "https://arxiv.org/abs/2409.06514", "paper",
     "Resampling-based counterfactual limit-order-book simulator.",
     "Preprint; needs venue/horizon validation."),
    (8, "The Probability of Backtest Overfitting", "Bailey et al.", "2017",
     "https://escholarship.org/uc/item/4w1110bb", "peer_reviewed",
     "PBO/CSCV framework for selection-overfitting risk.",
     "Does not replace economic mechanism or live validation."),
    (9, "The Deflated Sharpe Ratio", "Bailey & Lopez de Prado", "2014",
     "https://doi.org/10.3905/jpm.2014.40.5.094", "peer_reviewed",
     "Sharpe adjustment for selection bias and non-normal returns.",
     "Not a substitute for execution realism."),
    (10, "How to Build a One-Person HFT Hedge Fund on Jev That Fires Calibrated Trades on "
         "Every Block 24/7", "Unverified field-report author / user-provided paper", "2026",
     UNKNOWN, "architecture_field_report",
     "Candidate market-making architecture: deterministic state engine, six typed Jev "
     "judgments, confidence-gated policy, Avellaneda-Stoikov quoting in code, hard risk "
     "vetoes, fallback ladder, local calibration checks.",
     "Does not establish profitable alpha; direct Kelly-from-Jev sizing unjustified; "
     "stated monthly inference cost appears internally inconsistent; calibration method "
     "underspecified; latencies are vendor-reported."),
]

SOURCES = []

for n, title, org, year, url, stype, claim_scope, limitations in _OS_SOURCES:
    SOURCES.append(_row(
        source_id=f"SRC-{n:04d}",
        title=title,
        authors_or_org=org,
        publication_date=year,
        access_date="2026-09-20",
        date_basis="Repository literature registry (templates/literature.csv); access date is "
                   "the M1-C materialisation date for registry entries",
        url=url,
        source_type=stype,
        primary_or_secondary="primary_official" if stype == "primary_official" else "secondary_analysis",
        limitations=limitations,
        raw_citation_token="templates/literature.csv",
        local_path="trading_research_os_v0.2/templates/literature.csv",
        status="VERIFIED" if url else "PARTIAL",
        claim_scope=claim_scope,
    ))

# SRC-0010 is the user-provided field report; its "url" is not a URL.
SOURCES[9]["url"] = UNKNOWN
SOURCES[9]["raw_citation_token"] = "user-provided PDF"
SOURCES[9]["local_path"] = "Jev Trading Research Paper.pdf"
SOURCES[9]["doi"] = UNKNOWN
SOURCES[9]["status"] = "VERIFIED"
SOURCES[9]["independent_replication"] = "not independently reproduced"
SOURCES[9]["sha256"] = UNKNOWN  # filled from M1/raw/source_manifest.json at materialisation
SOURCES[9]["sample_period"] = "8 pages, single document"
SOURCES[9]["limitations"] = (
    "Does not establish profitable alpha; direct Kelly-from-Jev sizing unjustified; the stated "
    "monthly inference cost is not reproducible from the paper's own token accounting; "
    "calibration methodology underspecified; latencies are vendor-reported. The PDF has no text "
    "layer (image-only, 8 pages), so its claim set was read from rasterised pages; transcription "
    "fidelity is a recorded residual risk (UNK-0031).")

# --------------------------------------------------------------------------
# Repository artifacts
# --------------------------------------------------------------------------
_REPO_ARTIFACTS = [
    ("SRC-0011", "Calibrated Hierarchical Trading Runtime - M1-A Discovery, Evidence Lock, "
                 "and Candidate Elimination", "Project deep research run", "2026-09-20",
     UNKNOWN, "deep_research_report", "M1-A external-evidence artifact; current highest "
     "external-evidence authority until superseded.",
     "External sources are cited only through opaque internal citation tokens; URLs are not "
     "reconstructible from the artifact. Several decision-critical quantities remain UNKNOWN.",
     "deep-research-report.md"),
    ("SRC-0012", "00 - Research Charter", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_methodology",
     "Objective, epistemic rule, provenance/evidence-state vocabulary, Lane D/Lane P split.",
     "Methodology only; asserts no external market fact.", "trading_research_os_v0.2/docs/00_research_charter.md"),
    ("SRC-0013", "01 - Assumption Graph", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_methodology",
     "Canonical assumption chain and assumption-record schema.",
     "Methodology only.", "trading_research_os_v0.2/docs/01_assumption_graph.md"),
    ("SRC-0014", "02 - Evidence Gates", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_methodology",
     "G0..G8 promotion lifecycle and per-gate evidence requirements.",
     "Methodology only.", "trading_research_os_v0.2/docs/02_evidence_gates.md"),
    ("SRC-0015", "03 - System-One / Jev Admission Policy", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_policy",
     "Default System-One lockout; permitted/prohibited runtime roles; calibration and "
     "conformal policy; kill rule.",
     "Policy, not external evidence.", "trading_research_os_v0.2/docs/03_system_one_admission_policy.md"),
    ("SRC-0016", "04 - Simulation and the Reality Gap", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_methodology",
     "S0..S6 simulation ladder; reality-gap decomposition; timestamp logging contract; "
     "signal half-life requirement EV(delay).",
     "Methodology only.", "trading_research_os_v0.2/docs/04_simulation_reality_gap.md"),
    ("SRC-0017", "05 - Literature Review Map", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_methodology",
     "Workstreams A..H and seed primary sources with URLs.",
     "Methodology only; seed list is not an evidence lock.", "trading_research_os_v0.2/docs/05_literature_review_map.md"),
    ("SRC-0018", "06 - Metrics, Nulls, Baselines, and Kill Criteria",
     "Calibrated Hierarchical Trading Runtime", "2026-09-20", UNKNOWN, "project_methodology",
     "Metric stack, null tournament, label audit, System-One and strategy kill criteria.",
     "Thresholds are hypothesis-specific and must be preregistered.", "trading_research_os_v0.2/docs/06_metrics_and_kill_criteria.md"),
    ("SRC-0019", "07 - Monitoring and Source Policy", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_policy",
     "Monitoring/discovery order; social media is lead generation, not evidence.",
     "Methodology only.", "trading_research_os_v0.2/docs/07_monitoring_and_source_policy.md"),
    ("SRC-0020", "08 - Audit: How to Build a One-Person HFT Hedge Fund on Jev, 2nd revision: "
                 "project-owned document-level audit of SRC-0010",
     "Calibrated Hierarchical Trading Runtime", "2026-09-20", UNKNOWN, "project_audit",
     "Document-level audit of the Jev field report: architectural decisions to retain, "
     "eight required corrections (A..H), nested experiment arms A0..A7, ten new assumptions.",
     "Audits the document; does not independently verify any profitability or latency claim.",
     "trading_research_os_v0.2/docs/08_jev_trading_paper_audit.md"),
    ("SRC-0021", "Evidence gate configuration (machine-readable)",
     "Calibrated Hierarchical Trading Runtime", "2026-09-20", UNKNOWN, "project_config",
     "G0..G8 gate definitions with required evidence per gate.",
     "Configuration, not evidence.", "trading_research_os_v0.2/config/evidence_gates.yaml"),
    ("SRC-0022", "Research OS registry templates", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_registry",
     "Canonical column contracts for assumptions, hypotheses, experiments, evidence, "
     "literature, open questions, model candidates, reality gap, surprises.",
     "All templates are empty except literature.csv and open_questions.csv.",
     "trading_research_os_v0.2/templates/"),
    ("SRC-0023", "researchos.py - registry validator CLI", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_code",
     "Zero-dependency header validator and summary tool for the research registries.",
     "Validates headers only; performs no evidence or arithmetic checking.",
     "trading_research_os_v0.2/src/researchos.py"),
    ("SRC-0024", "Current Project Status v0.1", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_status",
     "Knowns, unknowns, explicitly-not-accepted claims, immediate research queue.",
     "Superseded in role by PROJECT_STATE.md; retained as reference.", "trading_research_os_v0.2/STATUS.md"),
    ("SRC-0025", "Trading Research OS README", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_overview",
     "Prime directive, non-negotiable architectural defaults, repository map.",
     "Overview only.", "trading_research_os_v0.2/README.md"),
    ("SRC-0026", "PROJECT HANDOFF: M1-C + M1-D", "Calibrated Hierarchical Trading Runtime",
     "2026-09-20", UNKNOWN, "project_handoff",
     "Execution contract for M1-C materialisation, M1-D0 derivable calculations, and the "
     "M1-D1 precondition; global zero-fabrication rules; required artifacts and validation rules.",
     "Instruction document; asserts no market fact.", "M1-C_M1-D_Handoff.md"),
]

for sid, title, org, date, url, stype, scope, limitations, path in _REPO_ARTIFACTS:
    SOURCES.append(_row(
        source_id=sid,
        title=title,
        authors_or_org=org,
        publication_date=date,
        access_date="2026-09-20",
        date_basis="Repository file timestamp / artifact header",
        url=url,
        source_type=stype,
        primary_or_secondary="primary_official",
        limitations=limitations,
        raw_citation_token=path,
        local_path=path,
        status="VERIFIED",
        claim_scope=scope,
    ))

# --------------------------------------------------------------------------
# External sources referenced by tokens (SRC-0101..).  Order = first appearance.
# --------------------------------------------------------------------------
# (token, title, org, publication_date, date_basis, source_type, venue, market,
#  limitations, claim_scope)
_TOKENS = [
    ("turn9academia36", "Study reporting that queue imbalance predicts the direction of the "
     "next mid-price movement for ten liquid Nasdaq stocks (authors stated as Gould & Bonart, 2015)",
     "Gould & Bonart", "2015", "Report states publication year only",
     "academic_paper", "Nasdaq", "US equities",
     "Old sample (2015); next-tick directional accuracy is not net profitability; authors/title "
     "not fully identified by the report; token not resolvable to a URL from repository artifacts.",
     "E-12 in SRC-0011: queue-imbalance predictability in the studied Nasdaq names, especially large-tick stocks."),
    ("turn10search24", "Study reporting a robust short-horizon relationship between order-flow "
     "imbalance and price changes across 50 U.S. equities (authors stated as Cont, Kukanov & Stoikov)",
     "Cont, Kukanov & Stoikov", UNKNOWN, "Report does not state a date for this source",
     "academic_paper", "NYSE", "US equities",
     "Uses NYSE TAQ equities; price-impact relationship rather than a sealed net strategy; "
     "coefficients/decay are not transferable across venues; token not resolvable to a URL.",
     "E-13 in SRC-0011: OFI/price relationship and inverse relation to market depth."),
    ("turn10search28", "Second token attached to the same order-flow-imbalance evidence as turn10search24",
     "Cont, Kukanov & Stoikov", UNKNOWN, "Report does not state a date for this source",
     "academic_paper", "NYSE", "US equities",
     "Two distinct tokens cite one paper family; the report does not separate them; token not "
     "resolvable to a URL.",
     "E-13 in SRC-0011 (paired citation)."),
    ("turn10search5", "Microprice literature: imbalance-adjusted estimator of future price "
     "(author stated as Stoikov, 2018)", "Stoikov", "2018", "Report states publication year only",
     "academic_paper", UNKNOWN, "US equities",
     "Estimator accuracy is not after-cost strategy evidence; token not resolvable to a URL.",
     "E-14 in SRC-0011: microprice improves on midpoint by incorporating order-book imbalance."),
    ("turn20view0", "Coinbase Exchange fee schedule as accessed on 2026-09-20, including the "
     "0-10k USD 30-day-volume tier and the 400m+ tier", "Coinbase", "2026-09-20",
     "Report states 'accessed Sept. 20, 2026'", "exchange_fee_schedule", "Coinbase Exchange",
     "Crypto spot",
     "Exchange fee only; excludes spread, slippage, impact, funding; account/program eligibility "
     "can change realized economics; token not resolvable to a URL.",
     "E-07 in SRC-0011: 60 bps taker / 40 bps maker at the 0-10k tier; 4/0 bps at 400m+ outside the liquidity program."),
    ("turn18view2", "Kraken fee schedule as accessed on 2026-09-20, including Tier 1 spot rates "
     "and a perpetual-futures per-side notional fee", "Kraken", "2026-09-20",
     "Report states 'accessed Sept. 20, 2026'", "exchange_fee_schedule", "Kraken", "Crypto spot / perps",
     "Platform fee only; excludes spread, slippage, impact, funding; product availability varies by "
     "geography; token not resolvable to a URL.",
     "E-08 in SRC-0011: Tier 1 spot 0.40% maker / 0.80% taker; perp 0.25% notional to open and 0.25% on close."),
    ("turn17view6", "CME MDP Premium product documentation describing full-depth Market-by-Order "
     "(MBOFD) and Market-by-Price (MBP) services", "CME Group", UNKNOWN,
     "Report describes the documentation as current; no date asserted", "exchange_technical_doc",
     "CME Globex", "Futures",
     "Establishes feed capability only; does not establish historical-data price, licensing, or "
     "strategy economics; token not resolvable to a URL.",
     "E-01 in SRC-0011: MDP supports event-based SBE market data with MBO Full Depth and MBP."),
    ("turn12search8", "Nasdaq TotalView-ITCH product documentation (displayed depth/order "
     "information) and NOII auction-imbalance dissemination", "Nasdaq", UNKNOWN,
     "Report describes the documentation as current; no date asserted", "exchange_technical_doc",
     "Nasdaq", "US equities",
     "Feed availability does not establish a profitable imbalance strategy; token not resolvable to a URL.",
     "E-04 in SRC-0011: TotalView exposes displayed depth/order information; NOII exposes auction imbalance."),
    ("turn16search12", "Nasdaq U.S. Equity Tick History product page (consolidated Level-1 tick "
     "data, history back to January 2014)", "Nasdaq", UNKNOWN,
     "Report describes the page as current; no date asserted", "exchange_data_product",
     "Nasdaq", "US equities",
     "Explicitly Level 1: insufficient for individual-order queue reconstruction; token not "
     "resolvable to a URL.",
     "E-05 in SRC-0011: Tick History is consolidated Level-1 history."),
    ("turn17view7", "Eurex T7 release 14.1 documentation: EOBI order-book interface, EMDI/MDI "
     "market-data interfaces and ETI trading interface (manuals dated Feb-Mar 2026; network "
     "documentation updated Aug 2026)", "Eurex", "2026-03-31",
     "Report states manual dates Feb-Mar 2026 and network docs updated Aug 2026",
     "exchange_technical_doc", "Eurex T7", "Futures/options",
     "Technical feasibility only; fees, matching rules, historical replay economics and broker "
     "access remain unverified; token not resolvable to a URL.",
     "E-11 in SRC-0011: T7 14.1 provides EOBI, market/reference-data interfaces and ETI documentation."),
    ("turn20view1", "Hyperliquid public WebSocket documentation: BBO, trades and an l2Book feed "
     "with 5 or 20 levels; WsBook documented as a snapshot feed pushed on blocks at least 0.5 s "
     "apart, carrying price, aggregate size and order count", "Hyperliquid", "2026-09-20",
     "Report states 'accessed Sept. 20, 2026'", "exchange_api_doc", "Hyperliquid", "Crypto perps/spot",
     "Aggregate levels are not exchange-style MBO queue identifiers; cadence is incompatible with "
     "sub-100 ms state reaction; trading-fee schedule not verified in the same pass; token not "
     "resolvable to a URL.",
     "E-09 in SRC-0011: public book feed cadence and level composition."),
    ("turn1search35", "CME matching-process materials showing that matching behaviour is not one "
     "universal FIFO rule across products", "CME Group", UNKNOWN,
     "Report describes the materials as current; no date asserted", "exchange_rule_doc",
     "CME Globex", "Futures",
     "Exact allocation rule must be looked up per candidate instrument; token not resolvable to a URL.",
     "E-03 in SRC-0011: product-specific matching processes."),
    ("turn1search3", "CME service notice demonstrating that Treasury calendar-spread matching "
     "algorithms can change", "CME Group", UNKNOWN,
     "Report describes the notice as current; no date asserted", "exchange_notice",
     "CME (CBOT)", "Treasury futures",
     "Single notice; establishes changeability of matching rules, not the current rule for a "
     "specific contract; token not resolvable to a URL.",
     "E-03 in SRC-0011 (paired citation): matching rules can change mid-product-family."),
    ("turn18view0", "Cboe U.S. Equities fee schedule (BZX) effective 2026-09-01: standard "
     "displayed-add rebate of $0.0016/share and removal charge of $0.0030/share for securities "
     "priced at or above $1", "Cboe", "2026-09-01",
     "Report states 'Fee schedule effective Sept. 1, 2026'", "exchange_fee_schedule", "Cboe BZX",
     "US equities",
     "Standard rates only: volume tiers, special fee codes, routing, CAT/broker/clearing and "
     "realized fills still matter; token not resolvable to a URL.",
     "E-06 in SRC-0011: standard BZX displayed-add rebate and removal fee."),
    ("turn17view5", "CME Market Data Platform systems documentation: direct MDP uses dual-feed "
     "UDP multicast and MDP 3.0/SBE", "CME Group", UNKNOWN,
     "Report describes the documentation as current; no date asserted", "exchange_technical_doc",
     "CME Globex", "Futures",
     "Network availability is not the same as inexpensive retail/broker access; token not "
     "resolvable to a URL.",
     "E-02 in SRC-0011: dual-feed UDP multicast with MDP 3.0/SBE."),
    ("turn16search30", "Cboe U.S. Options fee schedule located with effectiveness 2026-09-01, but "
     "class- and order-type-specific economics not decomposed", "Cboe", "2026-09-01",
     "Report states the located schedule is effective September 1, 2026", "exchange_fee_schedule",
     "Cboe options venues", "US listed options",
     "Fee codes not decomposed far enough for an options tuple to clear an execution gate; token "
     "not resolvable to a URL.",
     "Coverage note in SRC-0011: options fee schedule exists but tuple economics are unresolved."),
    ("turn16search20", "Nasdaq documentation page cited alongside TotalView-ITCH for displayed "
     "depth/order information", "Nasdaq", UNKNOWN,
     "Report describes the page as current; no date asserted", "exchange_technical_doc",
     "Nasdaq", "US equities",
     "Paired citation with turn12search8; the report does not distinguish the two pages; token not "
     "resolvable to a URL.",
     "E-04 in SRC-0011 (paired citation)."),
    ("turn20view2", "Hyperliquid info/API endpoint documentation for spot and perpetuals, "
     "including accounts and pagination of time-range responses", "Hyperliquid", UNKNOWN,
     "Report describes the documentation as current; no date asserted", "exchange_api_doc",
     "Hyperliquid", "Crypto perps/spot",
     "Does not establish full historical L2 replay availability; token not resolvable to a URL.",
     "E-10 in SRC-0011: info endpoints operate for spot and perps; some time-range responses paginate."),
    ("turn20view3", "Hyperliquid API documentation describing pagination / time-range response "
     "mechanics", "Hyperliquid", UNKNOWN,
     "Report describes the documentation as current; no date asserted", "exchange_api_doc",
     "Hyperliquid", "Crypto perps/spot",
     "Paired citation with turn20view2; token not resolvable to a URL.",
     "E-10 in SRC-0011 (paired citation)."),
    ("turn16search16", "Nasdaq IPO opening-process documentation: display-only period of at least "
     "ten minutes during which orders may be cancelled before the opening process",
     "Nasdaq", UNKNOWN, "Report describes the documentation as current; no date asserted",
     "exchange_process_doc", "Nasdaq", "US equities",
     "IPO opening is a special event, not ordinary continuous trading; token not resolvable to a URL.",
     "E-15 in SRC-0011: IPO display-only period."),
    ("turn7search32", "State attorney-general notice: Washington obtained a 2026 court order "
     "affecting Kalshi operations in the state", "Washington Attorney General", "2026",
     "Report states the court order is from 2026", "government_notice", "Kalshi", "Event contracts",
     "Establishes a state-level restriction only; does not establish the nationwide status of any "
     "Kalshi contract; token not resolvable to a URL.",
     "E-16 in SRC-0011: state-level access constraints exist."),
    ("turn14search1", "CME product/market-data listing cited for electronic equity-index futures "
     "structure", "CME Group", UNKNOWN, "Report does not state a date for this source",
     "exchange_product_doc", "CME Globex", "Equity-index futures",
     "Does not establish fees or measurable edge; token not resolvable to a URL.",
     "Fact-ledger row for ES/NQ/CME Globex structure and live observability."),
    ("turn14search6", "CME Data Services page advertising historical and real-time data products "
     "including up to full order book", "CME Group", UNKNOWN,
     "Report does not state a date for this source", "exchange_data_product", "CME Globex", "Futures",
     "Marketing/product listing only: exact history depth, licensing, delivery format and project "
     "cost were not locked; token not resolvable to a URL.",
     "Fact-ledger row for CME historical/replay state."),
    ("turn14search0", "CME MDP 3.0 fixed-income security-definition documentation", "CME Group",
     UNKNOWN, "Report does not state a date for this source", "exchange_technical_doc",
     "CME (CBOT)", "Treasury futures",
     "Security definitions only; establishes observability, not economics; token not resolvable to a URL.",
     "Fact-ledger row for Treasury futures data architecture."),
    ("turn16search26", "Cboe U.S. equities venue overview: BZX, BYX, EDGA and EDGX operate as "
     "separate venues", "Cboe", UNKNOWN, "Report describes the overview as current; no date asserted",
     "exchange_venue_doc", "Cboe", "US equities",
     "Venue enumeration only; queue and fee-code specifics remain candidate-specific; token not "
     "resolvable to a URL.",
     "Fact-ledger row for Cboe BZX equities venue class."),
]

for i, (token, title, org, pub, date_basis, stype, venue, market, limitations, scope) in enumerate(_TOKENS):
    sid = f"SRC-{101 + i:04d}"
    SOURCES.append(_row(
        source_id=sid,
        title=title,
        authors_or_org=org,
        publication_date=pub,
        access_date="2026-09-20" if "accessed" in date_basis else UNKNOWN,
        date_basis=date_basis,
        url=UNKNOWN,
        source_type=stype,
        primary_or_secondary="primary_official" if stype not in (
            "academic_paper", "government_notice") else "primary_official",
        market=market,
        venue=venue,
        limitations=limitations,
        raw_citation_token=token,
        status="PARTIAL",
        claim_scope=scope,
    ))

BY_ID = {row["source_id"]: row for row in SOURCES}
TOKEN_TO_ID = {row["raw_citation_token"]: row["source_id"] for row in SOURCES if row["raw_citation_token"].startswith("turn")}