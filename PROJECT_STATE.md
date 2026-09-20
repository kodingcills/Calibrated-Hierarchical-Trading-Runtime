# PROJECT_STATE

Status: CURRENT
Version: 1.0.0
Last Updated: 2026-09-20T18:48:51Z

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

<!-- GENERATED:milestones -->
M1-A: INCOMPLETE
M1-B: NOT_AUTHORIZED
M1-C: COMPLETE
M1-D0: COMPLETE
M1-D1: NOT_AUTHORIZED
<!-- /GENERATED:milestones -->

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
6b. **Crypto and event-market venue facts are now verified, and the legal picture is two-sided.**
   Hyperliquid's perp base tier is 0.045% taker / 0.015% maker with documented tier, staking and
   referral modifiers, and an official historical archive exists (requester-pays S3: hourly L2
   books and per-block fills, updated approximately monthly with no completeness guarantee).
   Market-wide liquidation flow is *not* officially observable - liquidation surfaces are
   user-scoped - which removes the observability premise from the liquidation variant of the
   Hyperliquid H3 tuple. Deribit publishes a bps fee table with premium caps and documents
   trade/funding backfill but no bulk option-book archive; the US is a prohibited jurisdiction.
   Kalshi's taker fee is a price-dependent formula (round_up(M x 0.07 x C x P x (1-P))) with a
   zero default maker multiplier, and its state status is actively contested: Washington
   (2026-08-13) and Nevada (2026-07-24) orders restrict categories, while the Third Circuit
   upheld preemption against New Jersey (2026-04-06). International Polymarket blocks US persons;
   the accessible US product is a separate venue with participant-scoped reporting and a
   documented position/ledger floor of 2026-05-01.
6c. **Several venue fee pages are dynamic with no published effective date** (Hyperliquid,
   Polymarket; Deribit gives one update date). A cost model built on an undated page cannot be
   shown to describe the period it is tested on, so the project must snapshot and hash fee
   schedules itself (UNK-0035).
6d. **CME matching is engine-assigned and product-specific, and the public cost search is
   exhausted.** Nine documented algorithm codes are assigned per product with split
   FIFO/pro-rata parameters and minute-cycle level recalculation, but the ES/NQ assignment was
   not located, and the CME fee and clearing-fee pages could not be retrieved: no fee value
   entered canonical state, and one surfaced figure was rejected as non-primary (patch P-0003).
   Historical order-level data does exist for at least part of the complex (DataMine MBO FIX from
   2017-01-07, coverage as documented COMEX/NYMEX; no published price).
6e. **The only two mechanism-gate passes rest on report-mediated sources.** KG1 passes for the
   Nasdaq queue-imbalance and Nasdaq microprice tuples, and the supporting studies are named but
   their URLs are not recoverable from the repository (`EVD-0012`, `EVD-0014`). Re-deriving those
   two citations is the cheapest way to make the only positive gate results in the project
   independently checkable - which is why UNK-0023 still ranks first on the frontier.
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

Issue classification is two-dimensional (see Issue Stages below): a resolution *method* and a
resolution *stage*. Before this pass every empirical unknown was treated as M1-blocking, which
made M1 unclosable by construction - the milestone required measurements that only M2 can
produce. The migration moved 9 issues to M2_MEASUREMENT, 1 to POST_M2 and 4 to NON_BLOCKING,
leaving 19 M1-blocking issues.

<!-- GENERATED:frontier -->
| leverage | tier | issue | method | affected | decision prevented |
|---|---|---|---|---|---|
| 60.0 | 1 | `UNK-0023` | PUBLIC_RESEARCH | all 28 (ALL_EXTERNAL_EVIDENCE) | Independent verification of any external claim, including fee schedules that already killed candidates; the ar |
| 60.0 | 1 | `UNK-0034` | DEFERRED | 8 | Access legality for four venue families, and therefore KG3 and KG5 for their candidates: no fill or cost model |
| 30.0 | 3 | `UNK-0018` | EXTERNAL_ACTION | all 28 (ALL_CANDIDATES) | Causal replay and therefore every queue, priority or fill claim; applies to any candidate that reaches replay. |
| 24.0 | 1 | `UNK-0002` | PUBLIC_RESEARCH | 6 | Any queue-position or fill model for passive CME candidates (KG2/KG3). |
| 22.5 | 2 | `UNK-0009` | PUBLIC_RESEARCH | all 28 (ALL_CANDIDATES) | Mechanism credibility (KG1) for every candidate whose mechanism has no current, on-venue, after-cost replicati |
| 18.0 | 1 | `UNK-0027` | PUBLIC_RESEARCH | 10 | M2 registration and any falsifier (KG5) for the affected rows. |
| 18.0 | 3 | `UNK-0033` | EXTERNAL_ACTION | 4 | All-in per-share cost for every equity tuple, and therefore the cost floor used in KG3. |
| 12.0 | 3 | `UNK-0010` | EXTERNAL_ACTION | 3 | Net-edge feasibility for the Hyperliquid H3/H4 candidates. |
| 12.0 | 1 | `UNK-0012` | PUBLIC_RESEARCH | 1 | Options tuples passing Gate 2 at all. |
| 12.0 | 1 | `UNK-0013` | PUBLIC_RESEARCH | 1 | Gate 2 for the Deribit tuple. |
| 12.0 | 1 | `UNK-0014` | PUBLIC_RESEARCH | 2 | Legality/access gate for both event-market tuples. |
| 12.0 | 1 | `UNK-0015` | PUBLIC_RESEARCH | 2 | Defining the tuple at all (KG1/KG3/KG5). |

Actionable frontier items: 17. Items awaiting an external answer or a frozen spec: 3. Measurement specifications: 7. External request packets: 10.
<!-- /GENERATED:frontier -->

## Issue Stages

<!-- GENERATED:stages -->
| resolution stage | count | meaning |
|---|---|---|
| M1_BLOCKING | 21 | must be answered before M1 can close |
| M2_MEASUREMENT | 9 | preregistered M2 experiment; does not block M1 |
| POST_M2 | 1 | matters only after M2 shows positive net EV |
| NON_BLOCKING | 4 | tracked; no gate depends on it |

| resolution method | count |
|---|---|
| PUBLIC_RESEARCH | 10 |
| EXTERNAL_ACTION | 11 |
| EMPIRICAL_MEASUREMENT | 10 |
| DEFERRED | 4 |
<!-- /GENERATED:stages -->

## Immediate Next Actions

Ranked by decision leverage (impact x kill potential x work tier / effort), recomputed
every pass from `M1/work/frontier.json`:

<!-- GENERATED:next_actions -->
1. **UNK-0023** (PUBLIC_RESEARCH, tier 1, leverage 60.0): A resolvable URL plus snapshot for each of the 25 report-mediated external sources
2. **UNK-0034** (DEFERRED, tier 1, leverage 60.0): A statement of the operator's legal domicile, entity type and client classification, plus the per-venue eligibility determination that follows from it.
3. **UNK-0018** (EXTERNAL_ACTION, tier 3, leverage 30.0): Field-level timestamp semantics (event vs receive time, clock domain, sequence integrity)
4. **UNK-0002** (PUBLIC_RESEARCH, tier 1, leverage 24.0): The allocation algorithm that applies to the named product and order type, with its version
5. **UNK-0009** (PUBLIC_RESEARCH, tier 2, leverage 22.5): Current, venue-specific, after-cost evidence for the mechanism each candidate relies on
6. **UNK-0027** (PUBLIC_RESEARCH, tier 1, leverage 18.0): One exact contract/symbol per branch, or a causal selection rule with its variables
<!-- /GENERATED:next_actions -->

## Readiness

<!-- GENERATED:readiness -->
Ready for M1-B? **NO** - zero candidates pass all five gates; the frontier still holds 17 M1-blocking items.
Ready for M1-D1? **NO** - M1-B is not authorized and no synthesis artifact exists, so no finalists can be compared.
Ready for M2? **NO** - M2 requires a selected candidate plus a locked cost configuration and an order-level dataset; the frontier holds both.
Ready for shadow trading? **NO** - a shadow run requires a chosen candidate, instrument and measured cost envelope.
Ready for capital? **NO** - no candidate has evidenced net edge.
<!-- /GENERATED:readiness -->

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
- Closure orchestrator: `M1/orchestrator/{schemas,blocker_card,priority,frontier,transitions,
  patch,resolvers,controller}.py`; work artefacts under `M1/work/` (frontier.json, cards/,
  patches/, external_requests/, m2_specs/); `M1/output/M1_CLOSURE_STATUS.json`,
  `M1/output/M1_EXTERNAL_ACTION_QUEUE.md`, `M1/output/closure_loop_log.md`.
- Code: `M1/src/corpus/*` (declarative data incl. `corpus/staging.py` and
  `corpus/patches/*`), `M1/src/{costs,candidate_gates,coverage,latency,pareto,envelopes,
  gate_engine,readiness,report,paper_arithmetic,materialize,validate,build_manifest}.py`,
  tests under `M1/tests/`.
- Root registries: `EVIDENCE_LEDGER.csv`, `ASSUMPTIONS.csv`, `HYPOTHESES.csv`, `EXPERIMENTS.csv`,
  `DISCREPANCIES_AND_UNKNOWNS.md`, `DEAD_ENDS.md`, `OPEN_QUESTIONS.md`, `WATCHLIST.md`,
  `ROADMAP.md`, `DECISIONS.md`, `CHANGELOG.md` (generated files are byte-identical to their
  canonical counterparts and validated so).
- Methodology source of truth: `trading_research_os_v0.2/` (README, docs/00-08, config, templates),
  unchanged by this materialisation.

## Counts

<!-- GENERATED:counts -->
| status | count |
|---|---|
| ALIVE | 0 |
| WEAK | 5 |
| UNKNOWN | 14 |
| DEAD | 9 |

Registered candidate rows: 28 (23 tradable tuples + 5 non-tuple registrations). Verified sources: 88 (25 report-mediated, 0 with a recoverable URL). Evidence records: 62. M1 frontier items: 17 (7 measurement specs and 10 external requests now outside the frontier). Gate-eligible candidates: 0.
<!-- /GENERATED:counts -->



- `python3 M1/src/build_manifest.py` - hashes raw inputs (only needed if raw inputs change).
- `python3 M1/src/materialize.py` - regenerates every artifact listed above and this file's
  `Last Updated` line.
- `python3 M1/src/validate.py --strict` - rules V1-V18: provenance, numeric provenance, gate
  ceiling and dead/ALIVE integrity, referential integrity, no candidate scoring, id uniqueness,
  source dates, experiment integrity, no imputation, cross-file consistency, raw-manifest hash
  integrity, paper-arithmetic reproducibility, two-dimension issue model, frontier integrity,
  eligibility independence, patch integrity, work-artefact validity. Last run: **PASS**, 0
  failures across 18 rule groups.
- `python3 -m unittest discover -s M1/tests -t .` - 76 tests, OK.
- `python3 M1/orchestrator/controller.py status|frontier|next` - closure orchestration.
- Validator report: `M1/validation/report.md`.

## Superseded / Legacy Artifacts

- `trading_research_os_v0.2/STATUS.md` - legacy/reference. Its knowns/unknowns remain valid in
  substance, but counts and current state now live here; it is no longer updated.
- `deep-research-report.md` - remains the M1 external-evidence artifact and is not superseded, but
  its self-reported reason for incompleteness has been partially invalidated (UNK-0030) and its
  citation tokens are unresolved (UNK-0023).
- `M1-C_M1-D_Handoff.md` - instruction document; its requirements are executed and tracked in
  `M1/output/`, not restated here.
