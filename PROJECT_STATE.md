# PROJECT_STATE

Status: CURRENT
Version: 1.0.0
Last Updated: 2026-09-20T17:37:42Z

This is the canonical fast-orientation artifact. Read it before any other file. Its counts are
generated from `M1/output/M1_STATE_SUMMARY.json` and enforced against the machine-readable
artifacts by `M1/src/validate.py` (rule V11); do not hand-edit a number here.

## Mission

Discover, falsify, validate, and only then deploy robust trading edge that survives realistic
execution. The project's objective is net economic edge after spread, fees, slippage, adverse
selection, impact, funding, latency decay, capacity and operational risk. Novelty, model
sophistication, prediction accuracy and attractive backtests carry no weight unless they improve
realizable economic utility.

## Current Milestone

**M1 - Market x Venue x Horizon x Edge-Mechanism Selection.**

Substage state (from repository evidence, not from plan):

- M1-A evidence discovery is INCOMPLETE: the M1-A artifact itself concludes INCOMPLETE, and this
  materialisation found that its stated reasons need revision (one is now false - see below),
  while the empirical blockers it lists remain independently sufficient.
- M1-C materialisation is COMPLETE: 51 sources, 29 evidence records, 19 venue rows, 25 mechanisms,
  28 candidate rows, 23 issues-registry rows, 16 open questions, 29 assumptions, 5 kill gates,
  9 proposed-not-run experiments.
- M1-D0 deterministic calculations are COMPLETE: gate vectors, status ceilings, cost floors,
  feasibility verdicts, coverage counts, hard-constraint eliminations, latency verdicts,
  blocker prioritisation. Full break-even remains UNKNOWN for every candidate, by construction.
- M1-B is not yet authorized (no candidate is gate-eligible).
- M1-D1 is not yet authorized (see `M1/output/M1_D1_BLOCKED.md`).

## Milestone Status

M1-A: INCOMPLETE
M1-B: NOT_AUTHORIZED
M1-C: COMPLETE
M1-D0: COMPLETE
M1-D1: NOT_AUTHORIZED

## Current Research Thesis

The project is searching for realizable trading edge. The candidate architecture in
`Jev Trading Research Paper.pdf` (Jev/System-One as a probabilistic judgment layer inside a
deterministic market-making loop) is a candidate component only. The architecture is not assumed
to require Jev, and no evidence in this repository shows that it improves execution-aware net
utility. System-One remains unadmitted: its own vendor documentation says arithmetic, counting,
numeric precision and date comparison should stay in code, and nothing external establishes an
exception.

## Active Candidate Hypotheses

**No candidate is ALIVE.** There is no active hypothesis tier. What exists is a survivor set that
has passed only hard constraints and still has every economic gate BLOCKED. Candidate rows and
their gate vectors are canonical in `M1/data/candidate_tuples.csv`; the surviving rows are listed
in `M1/output/hard_constraint_survivors.csv`.

The five WEAK rows (constraining evidence exists, nothing supports an upgrade):

| candidate | instrument | venue | horizon | mechanism | execution | blocking issue |
|---|---|---|---|---|---|---|
| TUP-CME-ES-H1-QDEP-PAS | ES future | CME | H1 10-100 ms | queue depletion | passive | matching rule, fill probability, all-in cost |
| TUP-NASDAQ-LARGETICK-H2-QIMB-AGG | large-tick stock | Nasdaq | H2 100 ms-1 s | queue imbalance | aggressive | 2015 gross evidence only; L3 history, fee tier |
| TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG | large-tick stock | Nasdaq | H2-H3 | microprice | aggressive | estimator evidence only; no profit evidence |
| TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS | stock >= $1 | Cboe BZX | H2-H3 | spread capture | passive | queue/adverse selection unmeasured |
| TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG | stock, national market | multi-venue | H1 | stale quote | aggressive | latency race unmeasured (label basis recorded in UNK-0024) |

Fourteen rows are UNKNOWN (no venue-specific evidence at all): ES H3 OFI, NQ H3 OFI, Treasury
queue/replenishment, WTI flow/volatility, Nasdaq auction imbalance, Hyperliquid H3 OFI/liquidation,
Hyperliquid H4 funding/basis, Eurex OFI/queue, Cboe options surface RV, Deribit options surface RV,
Kalshi event inference, Polymarket event inference, institutional FX lead-lag, retail FX feed lag.

## Killed Candidates

Nine registered rows are DEAD (4 tradable tuples, 5 non-tuple registrations). The ledger with
cause, evidence and resurrection condition is `DEAD_ENDS.md` (machine-readable:
`M1/data/dead_candidates.csv`). Re-entry requires NEW_EVIDENCE **and** an explicit resurrection
decision recorded in `DECISIONS.md`; silent re-entry is prohibited.

## Current Strongest Findings

Durable, evidence-backed, and still less than tradable alpha:

1. Short-horizon order-book variables (queue imbalance, order-flow imbalance, microprice) contain
   predictive information in some markets. That is not evidence of net tradable edge, and the
   strongest supporting samples are old and gross of costs.
2. Venue fee economics can dominate model quality. Verified at the named tiers, two taker fills
   cost 120 bps on Coinbase (0-10k tier) and 160 bps on Kraken (Tier 1) before spread, slippage,
   impact and adverse selection - which is why those tuples are dead on arithmetic alone.
3. Data availability is not replay sufficiency. Nasdaq's easily accessible U.S. Equity Tick History
   is consolidated Level 1 and cannot reconstruct individual order queues.
4. The Hyperliquid public book feed is documented at a >= 0.5 s snapshot cadence with aggregate
   levels, so a 10-100 ms public-feed reaction thesis is structurally impossible as specified.
5. CME matching is product-specific and has changed by notice, so a generic CME queue model is
   unjustified and any queue study must record the rule version it assumes.
6. System-One remains unadmitted: no external evidence establishes incremental execution-aware
   utility, and hosted latency is vendor-reported only (70-500 ms).
7. The candidate architecture paper has no text layer (image-only PDF); its claim set was
   transcribed from rasterised pages. It reports no backtest, P&L, fill or latency measurement, and
   its own three cost statements do not reconcile with each other: at its stated 300 ms cadence and
   its own ~240-token state, $0.042 per million input tokens implies ~$87/month, while its stated
   "near one hundred-thousandth of a dollar per block" implies ~$864/month, neither compatible with
   its stated $10-25/month.
8. M1-A's stated reason "the paper and research OS were not retrievable" is now false: both are in
   this repository, hashed in `M1/raw/source_manifest.json`. The verdict is unchanged because the
   empirical blockers are independently sufficient (UNK-0030, ASM-0018).

## Critical Unknowns / Blockers

32 issues are registered in `M1/data/discrepancies.csv`; 22 are BLOCKING (30 remain open,
`M1/output/blocker_priority.csv`). Grouped by how they can be cleared (counts are generated):

- **A - public research can resolve (8)**: modern venue-specific after-cost replication (UNK-0009),
  instrument-level specificity (UNK-0027), CME matching rules (UNK-0002), Hyperliquid fees/replay
  partially (UNK-0010), event-market jurisdiction matrices (UNK-0014), FX venue definition
  (UNK-0015), citation-token to URL resolution (UNK-0023), OCR transcription fidelity (UNK-0031).
- **B - requires exchange/vendor/broker quote or sample (11)**: feed timestamp semantics (UNK-0018),
  CME all-in cost (UNK-0001), CME historical MBO (UNK-0003), Nasdaq fee tier (UNK-0005), Nasdaq
  order-level history (UNK-0004), Eurex economics and access (UNK-0011), Cboe options fee
  decomposition (UNK-0012), Deribit access/fees/data (UNK-0013), auction history (UNK-0020),
  capital/tier eligibility (UNK-0028), BZX feed/fee-code access (UNK-0022).
- **C - only M2 measurement can resolve (10)**: full break-even envelope (UNK-0006), signal
  half-life (UNK-0008), own-stack latency (UNK-0016), fill-conditioned markout (UNK-0019), passive
  fill probability (UNK-0007), hosted-model latency and incremental utility (UNK-0017), cross-venue
  stale-quote survival (UNK-0021), capacity (UNK-0029), cost sensitivity (UNK-0032), independent
  verification of architecture claims (UNK-0026).
- **D - unresolved but non-blocking (1)**: the basis of the WEAK label on the cross-venue
  stale-quote tuple (UNK-0024). Three further non-blocking issues are already RESOLVED:
  horizon-band convention (UNK-0025) and the paper/research-OS retrievability contradiction
  (UNK-0030).

Top decision-changing blockers, by number of candidates affected and branch-kill potential
(`M1/output/M1_D0_READINESS.md` section 5):

1. UNK-0008 signal half-life - affects all 28 rows - class C.
2. UNK-0016 own-stack latency - affects all 28 rows - class C.
3. UNK-0009 modern venue-specific after-cost replication - affects all 28 rows - class A.
4. UNK-0006 full break-even envelope - affects all 23 tuples - class C.
5. UNK-0018 feed timestamp semantics - affects all rows that reach replay - class B.
6. UNK-0027 instrument-level specificity - affects 10 rows - class A.

## Immediate Next Actions

Ordered by decision impact (each is a concrete task, not a roadmap sentence):

1. Lock exact account-level cost schedules for the intended broker/venue path
   (UNK-0001, UNK-0005, UNK-0028) and register them as an immutable M2 cost configuration. Cheapest
   way to kill or clear an entire branch without modelling.
2. Request historical order-level data quotes plus sample files for CME and Nasdaq equity venues
   (UNK-0003, UNK-0004, UNK-0020) and validate timestamp semantics against the project's contract
   (UNK-0018, OQ-0015).
3. Resolve citation tokens to primary URLs and snapshot each page (UNK-0023), so the fee facts that
   already killed candidates are independently re-derived rather than report-mediated.
4. Lock the CME matching rule for each named contract and record its version (UNK-0002).
5. Narrow each surviving branch to one exact instrument, then lock tick/lot/fee facts (UNK-0027).
6. Only then instrument a shadow path to measure decision-to-market latency (UNK-0016) and design
   the EV-versus-delay sweep (UNK-0008).
7. Do not run M1-B or M1-D1 before 1-5 change the gate vectors.

## Readiness

Ready for M1-B? **NO** - zero candidates have all five gates PASS on cited evidence; 0 PASS on
KG1, KG2, KG3 and KG4 across all 28 rows.
Ready for M1-D1? **NO** - no CURRENT M1-B artifact exists and every decision-critical comparison
dimension is UNKNOWN; ranking would order missing values.
Ready for M2? **NO** - M2 requires the M1-B selection and, for every candidate, order-level data
plus a cost configuration; neither is locked.
Ready for shadow trading? **NO** - a shadow run requires a chosen candidate, instrument and a
measured cost envelope; none exists.
Ready for capital? **NO** - no candidate has evidenced net edge, and the project's own promotion
ladder places capital far beyond the current gate.

## Canonical Artifacts

Machine-readable M1 state (canonical; regenerate with `python3 M1/src/materialize.py`):

- `M1/data/` - source_registry, evidence_ledger, venue_facts, mechanisms, candidate_tuples,
  data_feasibility, execution_envelopes, technology_fit, discrepancies, open_questions,
  dead_candidates, assumptions, kill_gates, experiments, hypotheses.
- `M1/output/` - candidate_gate_status, evidence_coverage, data_feasibility_verdicts,
  cost_envelopes, venue_cost_reference, latency_feasibility, hard_constraint_survivors,
  hard_constraint_eliminations, dominated_candidates, blocker_priority, status_derivation_review,
  M1_D0_READINESS.md, M1_D1_BLOCKED.md, M1_STATE_SUMMARY.json.
- `M1/validation/report.{json,md}` - validator output (rules V1-V13).
- `M1/raw/source_manifest.json` - SHA-256 of every raw input; copies under `M1/raw/`.
- `M1/derived/jev_paper_pages/` - rasterised paper pages used to read an image-only PDF.
- Code: `M1/src/corpus/*` (declarative data), `M1/src/{costs,candidate_gates,coverage,latency,
  pareto,envelopes,readiness,report,paper_arithmetic,materialize,validate,build_manifest}.py`,
  tests under `M1/tests/`.
- Root registries: `EVIDENCE_LEDGER.csv`, `ASSUMPTIONS.csv`, `HYPOTHESES.csv`, `EXPERIMENTS.csv`,
  `DISCREPANCIES_AND_UNKNOWNS.md`, `DEAD_ENDS.md`, `OPEN_QUESTIONS.md`, `WATCHLIST.md`,
  `ROADMAP.md`, `DECISIONS.md`, `CHANGELOG.md` (generated files are byte-identical to their
  canonical counterparts and validated so).
- Methodology source of truth: `trading_research_os_v0.2/` (README, docs/00-08, config, templates),
  unchanged by this materialisation.

## Counts

| status | count |
|---|---|
| ALIVE | 0 |
| WEAK | 5 |
| UNKNOWN | 14 |
| DEAD | 9 |

Registered candidate rows: 28 (23 tradable tuples + 5 non-tuple registrations). Verified sources:
51 (26 repository artifacts + 25 external sources cited by token, of which 0 have a recoverable
URL). Evidence records: 29. Blocking unknowns: 22. Open questions: 16. Assumptions: 29.
Hard-constraint survivors: 19. Hard-constraint eliminations: 9.

## Validation and reproduction

- `python3 M1/src/build_manifest.py` - hashes raw inputs (only needed if raw inputs change).
- `python3 M1/src/materialize.py` - regenerates every artifact listed above and this file's
  `Last Updated` line.
- `python3 M1/src/validate.py --strict` - rules V1-V13: provenance, numeric provenance, gate
  ceiling and dead/ALIVE integrity, referential integrity, no scoring artifacts, id uniqueness,
  source dates, experiment integrity, no imputation, cross-file consistency, raw-manifest hash
  integrity, paper-arithmetic reproducibility. Last run: **PASS**, 0 failures.
- `python3 -m unittest discover -s M1/tests -t .` - 44 tests, OK.
- Validator report: `M1/validation/report.md`.

## Superseded / Legacy Artifacts

- `trading_research_os_v0.2/STATUS.md` - legacy/reference. Its knowns/unknowns remain valid in
  substance, but counts and current state now live here; it is no longer updated.
- `deep-research-report.md` - remains the M1 external-evidence artifact and is not superseded, but
  its self-reported reason for incompleteness has been partially invalidated (UNK-0030) and its
  citation tokens are unresolved (UNK-0023).
- `M1-C_M1-D_Handoff.md` - instruction document; its requirements are executed and tracked in
  `M1/output/`, not restated here.
