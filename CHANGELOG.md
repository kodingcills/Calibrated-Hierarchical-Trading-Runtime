# CHANGELOG

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