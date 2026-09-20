# CHANGELOG

## 1.1.0 - 2026-09-20 (M1 closure orchestrator; stage-semantics correction; first research iteration)

### Changed - M1 gate semantics (breaking, deliberate)

- Gates are now computed by `M1/src/gate_engine.py` with a rule id per verdict; the M1-A vectors
  are retained as `KG*_M1A`. KG4 no longer requires a measured half-life (it requires the absence
  of a physical contradiction plus a preregistered EV(delay) experiment); KG3 no longer requires
  measured fills; KG2 no longer requires purchased data. 22 rows move KG4 BLOCKED -> PASS as a
  result; no candidate becomes eligible because KG2 and KG3 remain unresolved (see DECISIONS D-0017).

### Added - two-dimension issue model

- `resolution_method` and `resolution_stage` on every issue, with an authored migration table in
  `M1/src/corpus/staging.py` and a per-issue reason. Migration: 9 to M2_MEASUREMENT, 1 to POST_M2,
  4 to NON_BLOCKING, 19 remain M1_BLOCKING. "BLOCKING" severity now means "blocks M1 closure".

### Added - closure orchestrator (`M1/orchestrator/`)

- `schemas.py` (closed enums, card/patch contracts), `blocker_card.py` (cards compiled from the
  registry), `priority.py` (deterministic leverage scoring and a tier guard), `frontier.py`
  (frontier + closure snapshot), `transitions.py` (legal state machine and adversarial patch
  verification), `patch.py` (build/verify/apply), `resolvers.py` (external-request and M2-spec
  generators), `controller.py` (CLI: `status`, `frontier`, `next`, `log`).
- Work artefacts: `M1/work/frontier.json`, `M1/work/cards/*.json`, `M1/work/patches/`,
  `M1/work/external_requests/*.md` (11 packets, ready to send), `M1/work/m2_specs/*.md` (7 specs
  with preregistration requirements).
- Status artefacts: `M1/output/M1_CLOSURE_STATUS.json`, `M1/output/M1_EXTERNAL_ACTION_QUEUE.md`,
  `M1/output/closure_loop_log.md`, `M1/output/gate_rule_trace.csv`, `M1/output/issue_migration.csv`,
  `M1/output/non_frontier_issues.csv`.

### Added - iteration 1 research (US equity cluster) via patch P-0001

- 12 primary sources (SRC-0201..SRC-0212) replace report-mediated or missing equity facts: the
  Nasdaq Historical TotalView-ITCH product with depth from 2007-08-13, NOII history included at no
  additional charge since 2010-01-04, Nasdaq base-tier add/remove rates, Cboe BZX base rates and
  Rule 11.12 priority class order, Nasdaq Rule 4757 price/display/time priority, NYSE and IEX
  comparators, and published small-participant data and connectivity prices.
- 12 new evidence records (EVD-0031..EVD-0042); 4 venue rows enriched; UNK-0020 resolved;
  UNK-0004/0022 now await quotes; UNK-0005/0023 in progress; new blocker UNK-0033 (sponsored-access
  commission) registered.
- No gate moved and no candidate was promoted: the facts narrow blockers and quantify mandatory
  costs, and none supplies a fill model, a markout or a break-even.

### Changed - validation and tests

- Validator now has 18 rule groups (V14 stage model, V15 frontier integrity, V16 eligibility
  independence and rule-trace validity, V17 patch integrity, V18 work-artefact validity); V5 now
  bans candidate scoring while explicitly permitting work-priority columns.
- Test suite 44 -> 76 tests (`M1/tests/test_orchestrator.py` added).
- PROJECT_STATE.md milestone, counts, stage and readiness blocks are now generated from state via
  markers, so the file cannot drift from `M1/output/M1_STATE_SUMMARY.json`.

### Verified numbers added this version

- Nasdaq base tier (securities >= $1): displayed-add rebate $0.0018/share (Tapes A and B),
  $0.0013/share (Tape C); remove fee $0.0030/share for all MPIDs.
- Cboe BZX standard rates effective 2026-09-01: displayed-add rebate $0.0016/share, remove fee
  $0.0030/share, tier rungs $0.0020-$0.0031/share requiring 0.06%-1.00% ADAV.
- NYSE 2026: non-tier add credit $0.0012/share, take charge $0.0030/share. IEX effective
  2026-09-01: base-tier displayed adds free, removes $0.0030/share, DEEP feed $2,500/month,
  10G port $7,000/month.
- Nasdaq Depth Non-Display $396/subscriber/month (1-39 tier, 2025) plus $3,190/firm/month direct
  access; Nasdaq 10Gb fibre hand-off $11,000/month.

### Not done, deliberately

- M1-B and M1-D1 remain NOT_AUTHORIZED: 0 candidates pass all five gates. The frontier holds 16
  actionable items, 11 of which need vendor/broker answers.

## 1.0.0 - 2026-09-20 (M1-C materialisation and M1-D0 deterministic calculation)

### Added - canonical state

- `PROJECT_STATE.md` - canonical current-state artifact (mission, milestone states, candidate
  counts by class, blockers by resolution class, readiness answers, canonical artifact index).
  Replaces `trading_research_os_v0.2/STATUS.md` in role; STATUS.md is retained as legacy.
- `ROADMAP.md` - M1 exit condition, ordered work required to close it, and explicit out-of-scope.
- `DECISIONS.md` - 16 decisions with reasoning and the artifact that enforces each.
- `CHANGELOG.md` - this file.

### Added - generated registries (root, byte-identical mirrors of the canonical M1 tables)

- `EVIDENCE_LEDGER.csv`, `ASSUMPTIONS.csv`, `HYPOTHESES.csv` (empty by design), `EXPERIMENTS.csv`
  (9 PROPOSED, none run), `DISCREPANCIES_AND_UNKNOWNS.md`, `DEAD_ENDS.md`, `OPEN_QUESTIONS.md`,
  `WATCHLIST.md`.

### Added - M1 workspace

- `M1/raw/` - unmodified copies of the two research artifacts, the handoff, and the research OS
  (25 files), plus `source_manifest.json` with SHA-256, size, ingest time and role per file. The
  repository originals were not modified.
- `M1/data/` - 15 canonical tables: source_registry (51), evidence_ledger (29), venue_facts (19),
  mechanisms (25), candidate_tuples (28), data_feasibility (28), execution_envelopes (28),
  technology_fit (30), discrepancies (32), open_questions (16), dead_candidates (9), assumptions
  (29), kill_gates (5), experiments (9), hypotheses (0).
- `M1/output/` - 12 derived artifacts plus `M1_D0_READINESS.md`, `M1_D1_BLOCKED.md` and
  `M1_STATE_SUMMARY.json`.
- `M1/validation/report.{json,md}` - validator output, rules V1-V13, overall PASS.
- `M1/derived/jev_paper_pages/` - 8 rasterised pages of the image-only paper, used to read its
  claim set.
- `M1/src/` - declarative corpus (`corpus/*`) plus `costs.py`, `candidate_gates.py`, `coverage.py`,
  `latency.py`, `pareto.py`, `envelopes.py`, `paper_arithmetic.py`, `readiness.py`, `report.py`,
  `materialize.py`, `validate.py`, `build_manifest.py`, and `tests/` (44 tests).

### Findings that changed the state

- The candidate-architecture paper is image-only (no text layer). Its claim set was transcribed
  from rasterised pages and registered as first-party evidence (EVD-0027); its own three operating
  cost statements do not reconcile: ~87 USD/month from its token price and ~240-token state at a
  300 ms cadence, ~864 USD/month from its stated per-block marginal cost, against a stated
  10-25 USD/month (EVD-0028, reproducible in `M1/src/paper_arithmetic.py`).
- The paper contradicts itself on calibration transport (EVD-0029): Section II.D claims RLCD
  calibration licenses direct fractional-Kelly sizing, while Section VII requires calibration on the
  operator's own logged data first.
- The M1-A artifact's stated reason "the paper and research OS were not retrievable" is false in
  this repository; both are present and hashed (UNK-0030). The incompleteness verdict is retained
  and re-derived from its remaining blockers (ASM-0018).
- Materialising the mechanism taxonomy exposed an inconsistency in the M1-A accounting: NEUTRAL
  feasibility facts (for example "CME supports full-depth MBO") were being counted as support for
  candidates. M1-C counts only SUPPORTS-direction evidence at consensus/supported-finding strength,
  and counts venue-specific support separately (ASM-0003).
- No candidate passes any economic gate: KG1 PASS 0/28, KG2 PASS 0/28, KG3 PASS 0/28, KG4 PASS
  0/28, KG5 PASS 22/28. Zero candidates are ALIVE.

### Verified numbers carried into machine-readable form

- Coinbase 0-10k tier 60 bps taker / 40 bps maker; round-trip taker-taker 120 bps.
- Kraken Tier 1 40 bps maker / 80 bps taker; round-trip taker-taker 160 bps. Kraken perp: 0.25%
  notional to open, 0.25% on close, maker/taker not distinguished.
- Cboe BZX standard displayed-add rebate 0.0016 USD/share and removal charge 0.0030 USD/share for
  securities at or above $1 (effective 2026-09-01); kept in native units, no bps conversion without
  a price.
- Hyperliquid public book cadence at least 0.5 s, aggregate levels only; 10-100 ms observation is a
  verified structural FAIL.
- Nasdaq U.S. Equity Tick History is consolidated Level 1.
- CME MDP supports MBO full depth and MBP; matching is product-specific and has changed by notice.

### Changes to existing files

- None. `deep-research-report.md`, `Jev Trading Research Paper.pdf`, `M1-C_M1-D_Handoff.md` and the
  entire `trading_research_os_v0.2/` tree are unmodified; hashes are recorded in the raw manifest.

### Validation

`python3 M1/src/validate.py` - PASS, 0 failures across 12 rule groups (V1-V13).
`python3 -m unittest discover -s M1/tests -t .` - 44 tests, OK.

### Not done, deliberately

- M1-D1 (final ranking, Pareto comparison, sensitivity analysis, finalist export): refused, with
  reasons in `M1/output/M1_D1_BLOCKED.md`. `M1/hypotheses/` contains only a README explaining why
  it is empty.
- M1-B: not authorized; no gate-eligible candidate exists.
- No value was imputed for any unknown; no experiment was run; no model was selected.