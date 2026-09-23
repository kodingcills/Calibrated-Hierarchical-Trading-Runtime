# M2-0 STATUS — data integrity and deterministic calculation pass

Candidate: `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` — Nasdaq, H2 100 ms–1 s, queue imbalance, aggressive
Universe rule: `NASDAQ-LARGETICK-QIMB-UNIV-v1` (frozen 2026-09-20, not reinterpreted here)
Run: `M2-0-NASDAQ-QIMB-BASELINE`, 2026-09-23 · config sha256 `0f366bb4…ac13a16b` · ledger `M2-COST-LEDGER-v1`

---

## DATA

| item | value |
|---|---|
| provider | Nasdaq (public sample-file service, `emi.nasdaq.com`) — no credential, no cost, no agreement signed |
| dataset | Nasdaq TotalView-ITCH 5.0 (binary), sample day `2019-07-30` |
| schema | `ITCH50-BINARY-V50-20230428` plus an empirically established 2-byte length prefix — see `data_quality/schema_contract.md` |
| dates | tape `03:02:50.2` → `20:05:00.0`; reported session events `Q` (09:30:00.000075) and `M` (16:00:00.0000586) bracket the configured window exactly |
| symbols | 8,849 Stock Directory entries; **61** development-scope symbols (`data_quality/scope_manifest.csv`) |
| messages | **282,229,684**, every frame length-verified; 0 framing mismatches, 0 trailing bytes |
| decision observations | **14,274,000** (61 symbols × 234,000 causal 100 ms grid instants); delay rows **1,427,400** |
| raw hash manifest | `data/manifests/raw_manifest.json` — sha256 `c65784c4c28735901ae442dc00e215834218a359bc12a139ab4eec209bc2d4a`, md5 `8744aba2ea125bfdde1a340ee2cea924`, 3,662,140,094 bytes compressed (8,661,679,413 decompressed) |
| role | **DEVELOPMENT**, `holdout_eligible = false`, `outcome_claim_permitted = false` |

Reference document retained and hashed: the ITCH specification itself
(`M2/data/reference/NQTVITCHspecification.pdf`, sha256 `45e0531d…e68aacc3`).

## DATA QUALITY

| audit | result | artifact |
|---|---|---|
| timestamp integrity | 0 reversals, 0 identical-timestamp-induced reversals, 0 messages arriving behind an emitted decision, 3,858,123 identical-timestamp messages (report-only), 0 inter-message intervals > 1 s in the session | `timestamp_audit.csv` |
| duplicate integrity | **0** byte-identical adjacent payloads and **0** byte-identical payloads inside any 100 ms bucket, over the whole tape, by exact byte comparison | `timestamp_audit.csv` |
| sequence integrity | the product carries **no** sequence number, no receive clock, no channel id; the tracking-number substitute is monotone with 0 gaps (`MONOTONIC_SUBSTITUTE_OK`). Not computable here: sequence-gap, receive-before-event and cross-channel ordering audits | `sequence_gap_audit.csv` |
| book reconstruction | 25,000,688 scope book messages (11,580,868 adds, 823,449 executions, 12,085 priced executions, 72,536 cancels, 10,973,371 deletes, 1,538,379 replaces): **0** orphan executions/cancels/deletes/replaces, 0 reference-number collisions, 0 negative or oversized remaining size, 0 impossible replacements, 0 crossed, 0 locked, 0 empty-sided updates during continuous trading | `book_reconstruction_audit.csv` |
| book cross-check | 38,796 level reconciliations against a full rebuild of every price level from the order map: **bid 1.000, ask 1.000, spread 1.000** match rate, 0 unexplained mismatches, across all 61 symbols | `book_crosscheck.csv` |
| PIT universe | **BLOCKED** — not evaluated (see UNIVERSE) | `universe_audit.csv` |
| known exclusions | none: 0 crossed/locked decision states, 0 missing sides, 0 non-positive denominators | `calculation_status.json` |
| unresolved defects | (1) no vendor checksum exists — the published `md5sum` sibling returned HTTP 404 at access time, so integrity rests on this project's own SHA-256; (2) the product cannot support event-vs-receive latency or sequence audits; (3) one development day cannot support day-level dispersion, partitions or regime transfer | this report |

Binding data-quality limits (frozen in the config) were all met; the day is
**DATA_VALID** and the calculation stage was allowed to run.

Two writer contracts are worth stating because they bound what a written row means:

* **Streaming, not preallocated.** Decision and delay rows are written to Parquet in
  bounded chunks (`decisions.buffer_rows_per_chunk = 262,144` rows, ~32 MB) rather than
  preallocating a table for every (symbol, grid instant) pair (~2.3 GB). The write frontier
  trails emission by the longest pending label request, so a row is written only once its
  100/250/500/1000 ms labels are final. `resolve()` refuses a late write into an
  already-written chunk, and the shifted-out tail of a chunk is cleared so a reused cell
  can never inherit an earlier row's value.
* **The next-move label has a declared deadline.** `next_mid_move_direction` resolves when
  the midpoint next changes, which has no natural bound, so `decisions.next_move_wait_ns =
  60 s` is declared: a row whose midpoint does not move inside that window is written with
  `next_move_resolved = false`. Measured: **13,970,273 of 14,274,000 rows resolved (98.80%)**,
  171,727 unresolved (1.20%, `late_watch_resolutions`), with the resolved rows splitting
  51.18% up / 48.82% down — the unresolved rows are concentrated where quoting thins out late
  in the session. Horizon and delay resolutions that arrive after their row was written are
  likewise counted rather than rewriting data (`late_label_resolutions = 0`,
  `late_delay_resolutions = 0` in `replay_summary.json`). Nothing is fabricated in place of a
  label the window did not capture.

The audits report **counts**, and every rate a reader may want is the count divided by the
denominator printed in the same table or in its sibling keyed by symbol
(`timestamp_audit.csv` carries `messages` and `book_messages` per symbol; the ordinary-event
totals are in `messages` of `ingest_summary.json`). Rates were deliberately left to the read
side rather than baked in, so that no denominator is hidden inside a rounded percentage.

## UNIVERSE

* rule version: `NASDAQ-LARGETICK-QIMB-UNIV-v1`, read from the frozen JSON, implemented in `M2/src/universe.py`, not reinterpreted.
* eligible symbol-days: **0 — the rule was not evaluated.** `universe_membership.parquet` carries all 8,849 symbols with `eligible = null` and
  `reason_codes = BLOCKED_POINT_IN_TIME_REFERENCE_NOT_SECURED | BLOCKED_ORDER_LEVEL_LOOKBACK_UNAVAILABLE`.
* major exclusion reasons: not applicable (blocked, not excluded). Sample-day spread statistics are
  reported beside each row and flagged `reporting_only = true`.
* the 61 symbols that carry the calculations are a **compute scope** (top order-add-message counts among
  Nasdaq-listed non-ETP common stocks with a ≥ $1 first quote, capped at the declared
  `dev_scope.candidate_pool_size = 61`), labelled
  `DEVELOPMENT_SCOPE_NOT_UNIVERSE_MEMBERSHIP` in `data_quality/scope_manifest.csv`. Selection used no
  return, no imbalance predictiveness and no P&L. No symbol was lost to the price floor, so no
  re-filling was needed (a loss is reported, never compensated).

**This is the pass's principal blocker and it is a stop condition under the handoff
(§29, "PIT universe cannot be constructed").** It was not worked around: no
survivor-biased substitution was made, and nothing that depends on membership was
computed.

## CALCULATIONS COMPLETED (development scope, 2019-07-30, 61 symbols, one day)

**Coverage** — 14,274,000 / 14,274,000 expected grid instants had a two-sided book:
valid book-state fraction **1.000**, missing-state fraction **0.000** (`coverage_summary.csv`).

**Market structure** (`market_structure_summary.csv`, pooled): mid-price median $69.885;
quoted spread mean $0.048169, median $0.010000 ⇒ mean **4.817 ticks**, median **1 tick**;
**one-tick spread fraction 0.5865**; top-of-book depth median 300 shares bid / 300 shares ask
(mean 773.5 / 730.2 shares); top-of-book staleness median 245.9 ms, p95 2,325.8 ms, max 24.7 s;
1.70 prior-bucket events on average.

**Imbalance** (`imbalance_distribution.csv`, pooled): mean +0.01239, median 0.00000,
std 0.48289, p05 −0.81818, p95 +0.83402, min −0.99985, max +0.99978;
|I| ≥ 0.8 in **11.56%** of observations; bin counts span 5.5% (strong sell) to 17.8% (weak buy).

**Unconditional future mid-price returns** (`future_return_summary.csv`) — zero returns are retained:

| horizon | n | mean (bps) | median | P(r>0) | P(r<0) | P(r=0) | block-bootstrap SE | 95% CI | symbol dispersion |
|---|---|---|---|---|---|---|---|---|---|
| 100 ms | 14,274,000 | +0.000343 | 0 | 0.01529 | 0.01502 | 0.96970 | 0.000126 | [+0.00011, +0.00060] | 0.00116 |
| 250 ms | 14,273,878 | +0.000932 | 0 | 0.03350 | 0.03267 | 0.93383 | 0.000328 | [+0.00030, +0.00156] | 0.00323 |
| 500 ms | 14,273,756 | +0.001786 | 0 | 0.05812 | 0.05637 | 0.88551 | 0.000609 | [+0.00060, +0.00301] | 0.00576 |
| 1000 ms | 14,273,451 | +0.003654 | 0 | 0.09589 | 0.09263 | 0.81148 | 0.001189 | [+0.00134, +0.00618] | 0.01095 |

Horizon losses: 0 dropped for want of a future two-sided book; 122/244/549 rows at the session edge
marked `LABEL_SESSION_ENDED` and left null. Day-level dispersion is **UNKNOWN** (single day).

**Conditional response to ex-ante imbalance bins** (`imbalance_response_by_horizon.csv`,
`imbalance_response_by_symbol_day.csv`) — 40 pooled cells and 2,440 symbol-level cells.
Extreme bins, pooled mean future return in bps with block-bootstrap 95% CI:

| bin | 100 ms | 1000 ms |
|---|---|---|
| [−1.0,−0.8) | −0.02106 [−0.02382, −0.01836] | −0.12804 [−0.14716, −0.11046] |
| [−0.6,−0.4) | −0.01699 [−0.01861, −0.01552] | −0.11716 [−0.12673, −0.10839] |
| [−0.2, 0.0) | −0.00308 [−0.00366, −0.00253] | −0.02048 [−0.02511, −0.01597] |
| [ 0.0, 0.2) | +0.00187 [+0.00136, +0.00237] | +0.01508 [+0.01112, +0.01917] |
| [ 0.4, 0.6) | +0.01474 [+0.01360, +0.01594] | +0.10567 [+0.09791, +0.11434] |
| [ 0.8, 1.0] | +0.02370 [+0.02102, +0.02678] | +0.14824 [+0.13032, +0.16774] |

**Monotonicity** (`monotonicity_diagnostics.csv`): rank correlation between bin midpoint and mean
future return **0.9758** at every horizon; 7 increasing and 2 decreasing steps of 9.

**Directional diagnostics** (`directional_sanity_summary.csv`) — thresholds declared before results,
no optimisation, no model:

| |I| threshold | coverage | hit rate given a non-zero move (100 ms / 1000 ms) | zero-move fraction (100 ms / 1000 ms) | constant-side baseline |
|---|---|---|---|---|---|
| ≥ 0.0 | 0.939 | 0.6452 / 0.6265 | 0.9709 / 0.8177 | 0.505 / 0.509 |
| ≥ 0.2 | 0.711 | 0.6662 / 0.6466 | 0.9686 / 0.8057 | 0.506 / 0.510 |
| ≥ 0.5 | 0.347 | 0.6952 / 0.6748 | 0.9628 / 0.7774 | 0.508 / 0.512 |
| ≥ 0.8 | 0.116 | 0.6702 / 0.6486 | 0.9526 / 0.7245 | 0.510 / 0.516 |

No logistic regression or other learned baseline was fitted: with no sealed partition and a single
development day, §18's optional baseline would have produced an in-sample number with no out-of-sample
meaning. That is a deliberate omission, recorded here rather than hidden.

**Cost tables** (mechanical arithmetic only; `reference_cost_by_quantity.csv`,
`reference_cost_by_price.csv`) — three regimes kept separate, per line item, with source, access date,
effective date, unit, formula and minima/maxima in `M2/config/cost_ledger_v1.json`:

* `STRUCTURAL_COST_FLOOR` — Nasdaq remove-liquidity fee $0.0030/share plus statutory sale-side charges
  (SEC §31 $20.60 per $1m effective 2026-04-04, FINRA TAF $0.000195/share capped at $9.79 effective
  2026-01-01). Round trip at 100 shares: $0.6216 (2.684 bps at $25, 1.445 bps at $50, 0.825 bps at $100).
* `ACCESSIBLE_REFERENCE_PATH / IBKR Pro Fixed` — all-inclusive $0.005/share, $1.00 order minimum,
  1%-of-trade-value cap; round trip at 100 shares $2.0000 (4.000 bps at $50, 2.000 bps at $100).
  Venue, clearing and regulatory items are **not** added again for this schedule (double-count guard).
* `ACCESSIBLE_REFERENCE_PATH / IBKR Pro Tiered` — $0.0035/share, $0.35 minimum, plus venue, NSCC/DTC
  clearing ($0.0002/share, capped at 0.5% of trade value), CAT ($0.000003/share) and the two
  commission-proportional pass-throughs; round trip at 100 shares $1.3627 (2.927 bps at $50).
* Unknown and left unknown: clearing cost as seen by the utility (DTCC charges participants per
  account-month and per deliver item — no per-order pass-through is publicly derivable), Nasdaq
  historical order-level data price (quote-only) and Databento's unit rate (behind authenticated
  metadata). **2026 rate cards were not back-applied to the 2019 tape**; the cost-adjusted figures below
  validate arithmetic, they do not reconstruct 2019 economics.

**Idealized aggressive execution** (`idealized_execution_summary.csv`, labelled
`IDEALIZED_REFERENCE_EXECUTION`, delay 0, signal side = sign(imbalance), 1,340,431 observations at the
declared 100-share representative size):

| horizon | gross markout | cross-to-cross | known cost (floor) | cost-adjusted | P(adjusted > 0) |
|---|---|---|---|---|---|
| 100 ms | −1.6709 | −1.6774 | 2.6831 | −4.3540 | 0.0010 |
| 250 ms | −1.6548 | −1.6691 | 2.6831 | −4.3379 | 0.0024 |
| 500 ms | −1.6341 | −1.6586 | 2.6831 | −4.3172 | 0.0046 |
| 1000 ms | −1.6006 | −1.6413 | 2.6831 | −4.2837 | 0.0096 |

Assumptions stated in the artifact: sufficient displayed size, immediate aggressive fill, no additional
slippage, no impact, no queue effect. These are **not** backtest P&L.

**Delay response surface** (`ev_delay_descriptive.csv`, 8 delays × 4 horizons × 3 regimes, no smoothing
and no fitted decay): with the structural floor, mean cost-adjusted result moves from −4.3540 bps at
0 ms to −4.3585 bps at 1000 ms (100 ms horizon) and from −4.2837 to −4.3182 bps (1000 ms horizon) —
i.e. the arithmetic is essentially flat across the delay grid on this sample, and the table reports it
as measured rather than fitted. Gross markout decays from −1.6709 to −1.6754 bps (100 ms horizon).
Missingness is reported per cell (0 missing arrivals; 59 rows at the session edge for the longest
delay/horizon combinations).

**Next-mid-change label** (`next_move_summary.csv`): 14,274,000 observations, 13,970,273
resolved (98.80%), 171,727 unresolved (1.20%) with the midpoint not moving inside the declared
60 s window, resolved split 7,218,169 up / 6,884,104 down (no zero changes by construction).
Reported, not interpreted.

**Reconciliation** (`reconciliation_checks.csv`): **23 independent re-derivations, 0 failures** —
one-tick classification vs tick arithmetic (14,274,000 rows), mid = bid + ask (14,274,000), imbalance
formula vs its own definition (max deviation 3.0e-08), bps vs decimal conversion per horizon
(max 3.0e-05), direction sign vs mid difference, commission per share vs total/quantity and vs the
published rate card, arrival quotes not crossed. A derived number that could not be reconciled is
programmatically barred from the results.

## CALCULATIONS BLOCKED

| item | reason code |
|---|---|
| point-in-time universe membership | `BLOCKED_POINT_IN_TIME_REFERENCE_NOT_SECURED` |
| 60-trading-day causal lookback for the large-tick classification | `BLOCKED_ORDER_LEVEL_LOOKBACK_UNAVAILABLE` |
| book cross-check against a provider BBO/MBP representation | `SECOND_DATA_PRODUCT_REQUIRED` |
| day-level dispersion and day-block bootstrap | `SINGLE_SAMPLE_DAY` |
| development / validation / sealed partitions | `INSUFFICIENT_COVERAGE` (fewer than three trading days) |
| modern-regime transfer of any reported statistic | `SAMPLE_DAY_IS_NOT_THE_INTENDED_WINDOW` |
| economic conclusion, promotion, kill or Jev comparison | `M2_0_SCOPE` (not attempted by design) |

`calculations/split_manifest.json`: `NO_SPLIT_POSSIBLE_INSUFFICIENT_COVERAGE`, no partitions,
`sealed_test_readable_by_m2_0 = false`. The sample day is DEVELOPMENT forever and can never be renamed
a test partition.

## NO CONCLUSIONS

**No strategy profitability, M1/M2 promotion, or Jev conclusion is made in M2-0. These artifacts are
quantitative inputs to the subsequent falsification decision.**

No candidate status in `M1/output/candidate_gate_status.csv` was changed, no gate was re-scored, Jev and
System-One were not used, and no threshold was optimised. Where the numbers above invite an economic
reading, the cost tables are printed beside the response tables precisely so that the research lead
makes that call, not this pass.

## VALIDATION

| item | value |
|---|---|
| tests | `python -m unittest discover -s M2/tests -t .` → **53 tests, 0 failures** (book lifecycle, orphans fail-closed, tick arithmetic, causal as-of labels, per-horizon label provenance, zero-return preservation, arrival-time delay book, streamed chunk writer incl. a guard that tests can never write into the repository's data directories, splits and sealed-partition guard, cost minima/caps/asymmetry, audit-writer column contract, end-to-end synthetic tape → replay → calculations) |
| reconciliation checks | 23, failures 0 |
| reproducibility | three independent lines of evidence: (1) **the replay is bit-reproducible** — two independent whole-tape runs of the same code produced **byte-identical** `decisions.parquet` (sha256 `d1943b46a0e5…`) and `delay_decisions.parquet` (sha256 `c98c41709609…`); (2) **the calculation stage is bit-reproducible** — re-running it from the same derived artifacts reproduces all **18 output files byte-for-byte** (`data_quality/calculation_reproducibility_check.json`, `identical = true`); (3) a **cross-layout check** — the earlier preallocated-table replay and the streaming replay produced identical aggregates (14,274,000 decision rows, one-tick fraction 0.586461, imbalance mean +0.012390, all 100 ms labels resolved, identical delay arrival statuses). Every input, config and code hash is pinned in `output/calculation_manifest.json`, so a full re-run is one command per stage |
| replay cost profile | measured, so a re-runner can size the work: the decode path runs at ~725k messages/s unprofiled (10M messages in 13.8 s); a profiled window covering 09:30–09:33 (15.4M messages, 38.3 s) attributes 0.28 µs/message to the label/resolution heap, 0.52 µs/message to the exact-duplicate detector, 0.51 s per 1,800 grid emissions, and 0.08 s per reconciliation call at 284k live orders. The final whole-tape replay took 721 s of process time on a host that was simultaneously indexing and running other applications; it writes 151 decision row groups and 12 delay row groups (202 MB and 119 MB, zstd) with a resident set of a few hundred megabytes |
| git commit | `894c814dcc761e3de966f511459b1872e2291171`; the M2 tree is uncommitted working-tree content, so the pass is pinned by the per-file code hashes in `config/experiment_manifest.json` and `output/calculation_manifest.json` rather than by the commit alone |
| config hash | `0f366bb445418a85ca001a290006531a0bb6ca2cb759b7a11694030dac13a16b` |
| candidate spec hash | `9ff81b4f5bc92687840ac4f568cf167afc1b470204919d2f0af236feec30a7dd` |
| cost ledger hash | `52ce785fc7210138af4059e327fc7101dff7f78dff3f5156c045973c1ed4cb17` |
| data hashes | raw sha256 `c65784c4…09bc2d4a` (md5 `8744aba2…2cea924`); derived artifact hashes in `output/calculation_manifest.json` |

Reproduce with:

```
python -m M2.src.ingest      --config M2/config/nasdaq_qimb_m2_0.yaml
python -m M2.src.book        --config M2/config/nasdaq_qimb_m2_0.yaml
python -m M2.src.calculate   --config M2/config/nasdaq_qimb_m2_0.yaml
python -m M2.src.freeze_manifest --config M2/config/nasdaq_qimb_m2_0.yaml
```

## NEXT REQUIRED DECISION

**Whether to authorize (a) a quote for modern Nasdaq order-level data and (b) procurement of a
point-in-time security master, since those two purchases are the only things now standing between M2-0
and a universe-valid, modern-regime falsification run.**
