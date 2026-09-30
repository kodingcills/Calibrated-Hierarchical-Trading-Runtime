# V1 — Independent adversarial verification of W3 / W4 / W5 / W6

Ticket: GOAL-M2-BRIDGE-001, verification operation V1. Adversarial, not collaborative.
Producer scripts were **not** used to check producer claims: every number below was
re-derived from the cached raw bytes (`M2/data/raw/basis/`), from the declared
artefacts, or from live public endpoints, with my own code under this directory.

Scope: data admission, cost arithmetic and canonical integrity only. No carry, P&L,
markout, displacement or any economic outcome was computed. Read-only on all
producer artefacts; the only writes are this directory. The one instructed mutation
(`python3 M1/src/materialize.py` for the idempotence test) was executed against a
byte-exact backup and the tree was restored afterwards — verified by re-hashing all
234 tracked M1 files + 5 root files and by an identical `git status --short`.
`NO commits were created. HEAD remains ccd637d.`

## Verdicts at a glance

| verdict | n | claims |
|---|---|---|
| VERIFIED | 14 | A1 A2 A3 A4 A5 A6 B10 B11 C13 C14 D15 D16 D17 D18 |
| SUPPORTED_SCOPED | 1 | B8 |
| CONTESTED | 2 | B9 C12 |
| REJECTED | 1 | A7 |
| UNVERIFIED | 0 | — |

**Most decision-relevant finding: A7/B9.** The Branch-C leg that the frozen state calls
`HL_BTC_mid` is, in the admitted artefact, a Hyperliquid **1h trade-derived candle close**
(5,003/5,003 closes are integers; every candle carries volume and a trade count) — i.e. the
last trade of the hour, which is exactly what the frozen kill rule excludes
("…or if any candle/book sample is stale or falls back to last trade"). Separately, mapping
Nasdaq's **continuous-book** remove-liquidity fee onto a **Closing Cross** exit has no
supporting evidence anywhere in the repo (B9).

## Claim table

Fields per row: **PROVES** = what the artefact establishes if read at face value;
**NOT PROVES** = the gap; **CHECK** = my independent check; **COUNTER** = counter-evidence hunted.

| ID | CLAIM | SOURCE | PROVES | NOT PROVES | INDEPENDENT CHECK | COUNTER | VERDICT |
|---|---|---|---|---|---|---|---|
| A1 | Window `2026-03-05T11:00Z→2026-09-28T23:00Z` is 4,981 hours, all matched, 0 missing, 0 duplicates | `admission.json`, `paired_hours.csv`, `W3_REPORT.md` | the producer's stated grid arithmetic | that the grid is right — until re-derived | my script rebuilt all 4 series from raw bytes → 4,981 expected / 4,981 matched / 0 missing / 0 dupes; CSV has 4,982 lines, 4,981 unique sorted hours; `(end−start)//3600+1 = 4,981` | tried to find an off-by-one (inclusive vs exclusive) and a re-indexed grid: none | **VERIFIED** |
| A2 | The join is a real 1:1 pairing (not a self-join / infallible re-index) | `M2/src/basis_admission.py`, raw HL+Binance bytes | a 4-way join over 4 independent series | that the join can fail | independent rebuild of HL funding (59 paged responses), HL candles, Binance `klines` and `markPriceKlines` → identical 4,981 rows, **0 value mismatches** vs `paired_hours.csv`; **negative controls NC1/NC2** (deleted Binance mark hour; shifted HL funding row) both produced `PAIRING_GAP`; **NC4** the naive exact-ms join pairs only **66 / 5,003** rows — the floor rule is load-bearing | looked for a self-join or a join keyed on the producer's own derived file: not present | **VERIFIED** |
| A3 | HL rows are hourly funding observations (not interpolated/duplicated); hour-flooring cannot cross a bucket in-window | raw `hl_funding_depthprobe_*.json` | settlement-level funding history | value correctness of the rates themselves | recomputed: 29,117 rows / 59 pages / **58 page-boundary duplicates** / **0 hour duplicates**; in-window offsets `min 0.0 s, max 0.261 s, nonzero 4,915, >1 s 0`; whole-history `max 1433.04 s` (2023-05-23T08:23Z), 5 rows >60 s, **0 rows ≥ 3600 s** — all identical to the report | checked whether the 58 dropped rows hide distinct settlements: they are page-boundary re-reads of the same `time` | **VERIFIED** |
| A4 | Exactly 3 absent HL settlements in the hourly era; none in the window | `admission.json → hl_funding_full_history` | the gap set | the era definition | independent bucket-level scan: missing = `2023-07-02T20:00Z, 2023-08-23T20:00Z, 2024-08-15T13:00Z`, none inside the window — reproduced **over a wider era than claimed** (see F1) | looked for further gaps via 2 h steps: found none beyond these 3 inside the hourly era | **VERIFIED** (era-start correction F1) |
| A5 | `binance_mark_1h_close` is a genuine mark series, not last-trade substituted | `markPriceKlines-*.zip`, `manifest_inputs/binance_mark_1h_close.csv` | a second Binance series exists | that Binance's mark is the "right" mark for the freeze | the zips' provenance URLs are `…/daily/markPriceKlines/BTCUSDT/1h/…` (not `klines`); **mark ≠ klines in 5,088 / 5,088 hours** (max relative difference 0.162 %); mark closes carry 8 decimals, kline closes 2; both columns reproduce from their respective archives with 0 mismatches | checked whether the mark column could be a copy of the kline column or of the HL candle: it is neither | **VERIFIED** |
| A6 | Window bounds are availability-derived, not chosen | `W3_REPORT.md §2`, `binance_archive_horizon_probes` | the producer's probe record | that the probe was correct — until re-probed | **live** re-probe: `candleSnapshot` with an explicitly older `startTime` (2025-01-01) still returns only the most recent ~5,003 candles starting 2026-03-05T11:00Z → the start is a hard API horizon; `data.binance.vision …/2026-09-29/…` → **HTTP 404** both series, `2026-09-28` → **206** both → the end is real archive lag | asked whether a free path to older HL candles exists: none found; the two binding endpoints behave as the report says | **VERIFIED** |
| A7 | The HL price field is a book mid ("HL_BTC_mid") | `hl_candles_1h_0.json`, `manifest_inputs/hl_mid_1h_close.csv`, `manifest_basis.json` | it is a Hyperliquid 1 h price series | that it is a **mid** | field set is `t,T,s,i,o,c,h,l,v,n`; **5,003 / 5,003 closes have fractional part exactly 0.0** (a mid on this tick grid would land on x.5); every candle has positive `v` and trade count `n` (e.g. 23,405 trades); the repo's own source note (`.research/resolution/BRANCH_C/SOURCES.md` S6) records that candles are the trade series and that **mids are not historically available** via the API | searched the manifests for any mid provenance: `manifest_basis.json` itself labels the field **"mid proxy"**, and `W3_REPORT.md §7` concedes it is "the 1h candle close" | **REJECTED** |
| B8 | The three STRUCTURAL-C0 ledger items carry primary provenance and the rate is effective for the relevant sample period | `M2/config/cost_ledger_v1.json` | primary sources + explicit effective dates | that the rates match the sample actually used | all three carry primary provenance (SEC Release 34-104909 via Federal Register, eff. **2026-04-04**; SEC Release 34-101696 / SR-FINRA-2024-019, eff. **2026-01-01**; Nasdaq Trader price list, **undated**, accessed 2026-09-22). The ledger's own `rates_apply_to_period` states these are **2026 rate cards** that "may not be applied to … the development sample day **2019-07-30**", and the M2 Nasdaq configs use `coverage_date: 2019-07-30` | checked for an earlier-rate provenance or a sample-binding: the ledger binds no sample, and no 2019-era rate is carried | **SUPPORTED_SCOPED** — primary provenance VERIFIED; period fit VERIFIED only for a sample on/after 2026-04-04, and **REJECTED** for the 2019-07-30 development tape; the remove-liquidity rate is undated |
| B9 | A Nasdaq Closing Cross exit is charged the remove-liquidity fee | ledger `nasdaq_remove_liquidity_fee`; W5 C0 map | a continuous-book remove fee exists | that a cross execution pays it | ledger applicability says "Nasdaq **continuous book**, displayed orders ≥ $1.00"; `EVIDENCE_LEDGER.csv` EVD-0033 is tagged `VEN-NASDAQ-CONT`; M1 `execution_envelopes.csv` for `…LATENOII-AGG`/`…AUCTION-AGG` has `fee_source_ids=NONE`, "Cross/auction-specific fees were not verified", `required_round_trip_fee_bps_for_style=UNKNOWN`, `full_break_even_status=BLOCKED_UNKNOWN_COMPONENTS`; `.research/resolution/BRANCH_B/REPORT.md` and `deep-research-report.md` both record auction fees as UNKNOWN | searched the repo for any closing-cross fee schedule: **none exists** | **CONTESTED** — no evidence; must not be usable in a freeze for the auction path |
| B10 | `classify_materiality` implements exactly KILL/SURVIVE/INDETERMINATE, significance separate; tests are load-bearing | `M2/src/envelope.py`, `M2/tests/test_envelope.py` | the frozen rule | that the inputs (g, C0) are correct | re-implemented the boundaries by hand: `g=0→KILL`, `g<0→KILL`, `hi==C0→KILL`, `lo==C0→INDETERMINATE`, `lo>C0→SURVIVE`, straddle→INDETERMINATE, `g≤0` with `lo>C0`→KILL (rule order), swapped interval sorted defensively; signature is `(gross_usd, uncertainty_lo_usd, uncertainty_hi_usd, c0_usd)` — significance is not a parameter and is flagged `REPORTED_ONLY` / `significance_is_decision_criterion: false`; suite 38 tests OK | tried to feed significance into the decision: impossible through the API | **VERIFIED** |
| B11 | Unknown-unit conversions are refused; C1 is never silently zero | `M2/src/envelope.py` | refusal semantics | that all callers respect them | forced `convert/to_usd/from_usd` with unit `"WIDGETS"` → `UnsupportedUnitConversion` in all three; `USD_PER_CONTRACT→bps` without a multiplier → `MissingUnitInput`; `None` value → `MissingUnitInput`; an envelope with a C1 unknown → `unresolved_c1_total_usd() = None` and `bounded: False`; an *unevaluable* C1 (multiplier-of-commission, no commission) → `None` + `unevaluated_item_ids`; grep for `or 0` / `default=0` in `envelope.py`: **none** | looked for a sum that absorbs unknowns as zero: none found; the C0 set from the real ledger is exactly the 3 declared floor items, with the two UNKNOWN operating-economics items correctly in C1 | **VERIFIED** |
| C12 | Every admission check is load-bearing; adversarial manifests are refused | `M2/src/admission.py`, `M2/tests/test_admission.py` | the engine refuses the 25 in-suite fixtures | that it refuses *new* attacks | built 7 new manifests: wrong declared hash → `DATA_INVALID`; missing hash → `DATA_INCOMPLETE`; coverage just below tolerance → INVALID; window kept + bucket dropped + ratio 1.0 → INCOMPLETE; wrong timezone (ET) internally consistent → INVALID; wrong instrument `ETHUSDT` → INVALID; wrong byte count → INVALID — **7/7 refused**. But **3 further attacks returned `DATA_VALID`**: (a) all timestamps shifted **+4 h consistently** (window, intervals, keys, records); (b) `records` list shortened to 4,980 while `coverage.admitted=4,981` and the intervals list still declares 4,981 present; (c) all interval **ids** offset by one hour (count preserved). The BASIS contract counts `present` interval entries and never compares ids/timestamps to the declared window, nor records to coverage | tried the doc's own claimed structural guarantee ("enforces the frozen 100 % hourly pairing structurally"): it enforces a **count**, not the grid geometry | **CONTESTED** — refused the enumerated attacks, but the 100 %-coverage check is a count identity, not a grid/timestamp identity |
| C13 | INVALID > INCOMPLETE > VALID holds; an un-runnable check never yields VALID | `M2/src/admission.py` | the precedence rule | that every check is reachable | manifest carrying both a hash mismatch (INVALID) and a missing required role (INCOMPLETE) → `DATA_INVALID` (1 INVALID, 1 INCOMPLETE); non-object manifest → `DATA_INCOMPLETE`; `{}` → `DATA_INCOMPLETE`; removing `files.hash` from the registry flips a real hash mismatch from `DATA_INVALID` to `DATA_VALID`, proving the check (not luck) does the work | looked for a path where a check that cannot run yields VALID: none | **VERIFIED** |
| C14 | A producer's narrative document cannot be admitted as evidence | `M2/data/derived_basis/admission.json` | the engine's refusal design | anything about the market data | ran the engine on `admission.json` → `DATA_INCOMPLETE`, exit 1, 27 findings, every required section absent; re-ran on the canonical `manifest_basis.json` → `DATA_VALID`, 23 checks, 0 findings | checked that the narrative file is not silently coerced into the manifest shape: it is not | **VERIFIED** |
| D15 | No validator rule or M1 test was weakened/added-tolerantly/deleted; the `materialize.py` hand edit changes no enforcement | `git diff` of M1 | a declarative-corpus change | that every rule still passes — until run | `git diff -- M1/src/validate.py` and `-- M1/tests` are **empty** (byte-identical to `ccd637d`); the `materialize.py` hunk is 5 insertions / 1 deletion and only chooses the `status_basis` provenance string from `status_source_id`; the gate computation above it is untouched. Ran `python3 M1/src/validate.py --strict` → **PASS, 19 checks, 0 failures** | diffed every other changed M1 source file for a relaxation: `readiness.py` / `campaign.py` / `resolvers.py` / `staging.py` / `unknowns.py` / `child_issues.py` / `tuples.py` / spec JSONs are text/taxonomy only | **VERIFIED** |
| D16 | `TUP-NASDAQ-CLOSE-H4-LATENOII-AGG` claims no readiness it lacks; the parent is not revived | `M1/data/candidate_tuples.csv`, `M1/output/*` | a registered, blocked row | that the row's universe rule is approved — it is not, and the row says so | new row: `overall_status=UNKNOWN`, `status_source_id=UNKNOWN`, `kill_status=UNKNOWN`, gates `BLOCKED/BLOCKED/BLOCKED/BLOCKED/PASS` with rules `KG1-R4/KG2-R0/KG3-R4/KG4-R5/KG5-R5`; `candidate_gate_status.csv` → `NOT_ALIVE`; row notes state KG5 is a computability verdict and that no approved universe-rule spec artifact exists. Parent row differs from `HEAD` **only** in `gate_recompute_date`; no `ALIVE` cell exists anywhere in `M1/output`; `ALIVE=0`, `gate_eligible=0` | searched all `M1/output/*.csv` for a bare `ALIVE`: **zero rows** | **VERIFIED** |
| D17 | `PROJECT_STATE.md` prose agrees with the generated blocks and `M1/data/*.csv`; the ES correction admits no verified cost | `PROJECT_STATE.md`, `DECISIONS.md`, ES spec | the canonical narrative | that the prose is complete | 6+ numbers re-checked against machine sources: candidate rows **30** (25 tuples + 5 non-tuple) ✓; `UNKNOWN 17 / WEAK 3 / DEAD 10` ✓ (`status` block + CSV); DEAD "5 tuples + 5 non-tuple" ✓; `UNK-0018-NASDAQ` affected 3→**4** ✓ (card `affected_candidates` now has 4, incl. the new row); external actions **14** ✓; ALIVE **0** ✓. ES: `execution_envelopes.csv` ES rows keep `known_cost_floor_bps` empty, `required_round_trip_fee_bps_for_style=UNKNOWN`, `full_break_even_status=BLOCKED_UNKNOWN_COMPONENTS`; the spec's `methodology_correction.note` states "no cost is verified"; D-0042 states C0 is still unverified for CME. The prose's "Fifteen rows are UNKNOWN" is a **curated 15-row enumeration** (the machine count is 17; the two extra are Coinbase/Kraken, which the doc separately marks DEPRIORITIZE with their own venue evidence) — consistent, not a contradiction | looked for an unverified claim entering canonical state: none via D-0042. One **stale pre-existing** line found (F6) | **VERIFIED** (caveat F6) |
| D18 | The regenerated artefacts are reproducible (idempotence) | `M1/src/materialize.py` | a deterministic generator | that no byte changes — it embeds wall-clock time | backed up the tree byte-exactly, re-ran `python3 M1/src/materialize.py` (exit 0; same 30 rows / ALIVE 0 / gate_eligible 0), hashed all 234 files: **74 of 75 changed files differ only in `20xx-xx-xxTxx:xx:xxZ` timestamp fields**; the 75th (`M1_STATE_SUMMARY.json`) differs only in its `artifact_hashes` of those timestamped files. `git status --short` **byte-identical** before/after. Tree restored from backup: all 234 hashes and the porcelain output match the pre-run state | tried to find a substantive content change under regeneration: none | **VERIFIED** (modulo the embedded generation timestamp) |

## Negative controls (deliberately corrupted inputs — all must fail)

`v1_negative_controls.py`, machine-readable in `v1_negative_controls.json`:

| control | corruption | expected | observed |
|---|---|---|---|
| NC1 | delete one in-window Binance mark hour | `PAIRING_GAP` | `PAIRING_GAP`, missing `2026-04-11T16:00Z` |
| NC2 | shift one in-window HL funding row forward 2 h (crosses its bucket) | `PAIRING_GAP` | `PAIRING_GAP`, missing `2026-03-05T16:00Z` |
| NC3 | corrupt one HL candle close to `1.0` | value mismatch vs `paired_hours.csv` | mismatch detected at `2026-03-05T11:00Z` |
| NC4 | use the rejected exact-millisecond join instead of the hour floor | large drops | only **66 / 5,003** rows pair → the floor rule is what makes the pairing work |
| C-adversarial A1–A7 | 7 new admission-manifest attacks | refused | 7/7 refused |
| C-adversarial A8/A10/A12 | consistent +4 h shift; short record list; interval-id offset | refused | **`DATA_VALID`** → recorded as a hole (C12) |

## Findings (non-claim, ordered by materiality)

- **F1 (moderate, data-accuracy).** The monthly-cadence transition is mis-stated. The
  producer probed a window starting 2023-06-25T10:30Z and concluded the uniform hourly era
  begins **2023-06-25T12:00Z**. The raw bytes show 24 settlements per day from
  **2023-06-08T01:00Z** (2023-06-07 has 3). The true hourly era is 29,038 expected /
  29,035 present hours, not 28,619 / 28,616. The missing-set claim (A4) survives unchanged
  over the wider era, and the admitted window is unaffected (it starts 2026-03-05), but
  `admission.json → hl_funding_full_history.hourly_era_start_utc` is wrong.
- **F2 (minor).** `W3_REPORT.md §8` lists `M2/src/basis_admission.py` with **no sha256**
  ("—"). Every other artefact hash in that table matches disk (I recomputed all four).
- **F3 (material — see A7).** The admitted price leg is a trade candle close labelled a
  "mid proxy". The frozen spec's state is `HL_BTC_mid / Binance_BTCUSDT_mark − 1`, and its
  kill rule names "falls back to last trade"; hourly bucket stamps also do not satisfy the
  spec's "paired within 5 seconds" condition in any causal sense.
- **F4 (material — see C12).** The BASIS contract's "100 % hourly pairing" is a **count**
  identity (`(end−start)//3600+1` present entries), not a grid identity: interval ids,
  record timestamps and record counts are never compared to the declared window or to each
  other, so a consistent 4 h shift, an hour-offset grid, or a shortened record list pass.
- **F5 (material — see B8/B9).** `nasdaq_remove_liquidity_fee` has no effective date and is
  applicability-limited to the continuous book; the 2026 SEC/TAF rates cannot be applied to
  the 2019-07-30 M2 development tape (the ledger says so itself).
- **F6 (minor, pre-existing).** `PROJECT_STATE.md` line 349 ("leaving 19 M1-blocking
  issues") was not touched by W6 but no longer matches the registry (21 distinct base issues
  at stage `M1_BLOCKING`; 39 cards). Pre-existing prose drift, not a W6 regression.

## Provenance-chain integrity (all pass)

`v1_integrity_chain.py`, results in `v1_integrity_chain.json`:

- **61/61** Hyperliquid API pages: recorded raw sha256 **and** canonical (sorted-key)
  sha256 both recomputed from disk and matching.
- **70/70** Binance kline/mark archive zips + **6/6** `fundingRate` zips matching their
  recorded sha256 (75 archive objects, matching the report); the 69 kline zips on disk are
  exactly the 69 recorded.
- Prior-probe cross-check recomputed from the CSV itself: **276/276** rows inside the
  window, **0** value mismatches on all five shared fields.
- `request_summary`: 144 requests, `api.hyperliquid.xyz` 61 / `data.binance.vision` 83,
  136 cache-served — matches the report.

## Method notes

- Scripts (all under this directory, none importing `M2/src/basis_admission.py`):
  `v1_reverify_pairing.py`, `v1_negative_controls.py`, `v1_integrity_chain.py`,
  `v1_envelope_checks.py`, `v1_admission_adversarial.py` (+ `_extra`).
- Machine-readable evidence: `v1_pairing_rederivation.json`, `v1_negative_controls.json`,
  `v1_integrity_chain.json`, `v1_envelope_checks.json`, `v1_admission_adversarial.json`,
  `v1_admission_adversarial_extra.json`.
- Live probes (public, anonymous, read-only): Hyperliquid `candleSnapshot` with an older
  `startTime`; Binance `data.binance.vision` daily range-GETs for 2026-09-27/28/29.
- The M1 tree was snapshotted to `/tmp/v1_backup/tree.tgz` before the instructed
  `materialize.py` re-run and restored byte-exactly afterwards; `git status --short` is
  identical to the pre-run state and the M1 validator was re-run read-only before restore.