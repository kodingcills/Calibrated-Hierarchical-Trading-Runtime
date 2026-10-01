# V3 — adversarial verification of the three bridge branch runs (GOAL-M2-BRIDGE-001)

**Wave:** V3 (final pre-adjudication wave). **Interpreter used for every computation:**
`.venv/bin/python3` (Python 3.14.7, numpy 2.5.3, pyarrow 25.0.1). System `python3` was never
used for a suite or a computation.

**Read-only compliance.** No file outside `.research/m2_bridge_001/verification/V3/` was created,
modified or deleted. No commit, no purchase, no credential, no network acquisition of the auction
source. Two frozen modules were executed; both were pointed at `--out` paths **inside V3**
(`M2.src.es_materiality run`, `M2.src.auction_materiality measure`) and neither writes anywhere
else. `M2.src.basis_materiality --check` is a verify-only path and writes nothing. The 17.9 GB
auction stream was not re-fetched; every auction claim below rests on the retained
`signal_extract.json`, `entry_prints.json`, `certificate.json` and `results.json`.

## 0. Scripts and their sha256

| script | sha256 | role |
|---|---|---|
| `v3_a1_freeze_hashes.py` | `63498cd94cf367426e55e8f09e99d28efec808a6acdc0e9a19799a71b004f43b` | claim A1: freeze seal + every declared hash vs disk |
| `v3_b4_es_rederive.py` | `0d7a3530dd34ce1303d28bbdb42e8015edcaea64e9f4bb8b0c403b728bc1db16` | claims B4/B5/B6: independent ES metric, strictly-past replay |
| `v3_c8_basis_rederive.py` | `fe2f6c5dd7d6874c784194a6f1937ebc7092f161c2ba4447450808307b92eb2c` | claims C8/C9/C10/C11: independent basis recomputation from panel + raw zips |
| `v3_d13_auction_capture.py` | `812f4c1fbea0983d35de67cd6ea6bb6826425ec7899ed5c5edb3984e4c251dc8` | claim D13: decomposition of the −108.9 bps |
| `v3_nc_controls.py` | `6bcc4cc6a3253f50c86a584b25a6556b952e21c3f13c7e2d5c3dba211449d8c5` | negative controls + B6/D13 support |
| `nc/tamper_freeze.json` | `e4f7f137ca57689154ffc8089c40dac4bc22d6e77f90344f40bfa46f6e20e15d` | NC1 tampered contract (sealed hash `42a158c5…`) |
| `es_rerun_results.json` | `09c8562999304072a5f5b5184bece3ba0588d1d57754ae776b3c6934f1487ac2` | re-run of the frozen ES contract |
| `auction_rerun_results.json` | `558e18bff14502683d4a33b0b27ea516d623c20fb10796cf880722c5f59fb1a5` | re-run of the frozen auction measurement |

## 1. Claim table

Verdict vocabulary: **VERIFIED** (independently reproduced) · **SUPPORTED_SCOPED** (true as far as
the retained evidence goes, with a named limit) · **CONTESTED** (the artifact's statement and the
evidence disagree) · **UNVERIFIED** (cannot be checked with retained evidence) · **REJECTED**
(contradicted by the evidence).

### CLAIM SET A — sealed-before-outcome discipline

| # | claim | verdict | independent check |
|---|---|---|---|
| A1a | freeze sha256 recomputes to the sealed value | **VERIFIED** | all three: recomputed = declared (`42a158c5…`, `389b8f4d…`, `9baff3dd…`) |
| A1b | freeze records the analysis-module hashes and they match disk | **VERIFIED** (A, B) / **SUPPORTED_SCOPED** (C) | A: 11/11 declared hashes match disk. B: 22/22 resolvable match. C: 154 match, **1 mismatch** — see below |
| A2 | the freeze was written and hashed **before** the results | **UNVERIFIED** (A, C) / **REJECTED** (B) | mtimes + seal enforcement (A, C); the sealed artefact set contains the exit price (B) |
| A3a | no producer edited canonical artifacts | **VERIFIED** | mtime census of `M1/**` + root registries; git per-file history |
| A3b | the three epoch-5 spec files record their frozen contracts accurately | **VERIFIED** | spec fields vs executed contract, freeze hashes, retained pre-edit blobs vs git |

**A1b, branch C — the one real hash drift.** `freeze.json` declares
`inputs_sha256.code["M2/src/admission.py"] = 9f5862f7…`; the file on disk is `00363c3a…`.
`run_inputs.json` (written by the run) records the **run-time** value as `9f5862f7…`, i.e. the file
was changed *after* branch C ran and *before* branch B sealed (B's freeze declares `00363c3a…`,
which matches disk). `M2.src.basis_materiality --check` today returns
`{"freeze_sha256_matches": true, "code_unchanged": true, "inputs_unchanged": false,
"drifted_inputs": ["M2/src/admission.py"]}` and refuses (exit 2). The drift is **inert**: the module
only *hashes* `admission.py` (it is not imported — imports are `argparse/csv/hashlib/json/statistics/
sys/zipfile/dataclasses/datetime/pathlib/numpy` + `M2.src.envelope`), and my independent
recomputation (C8) reproduces the entire gross from the panel and the raw zips. The drift does,
however, mean branch C's seal can no longer be verified in place.

**A2 — ordering.** Artifact mtimes (local, 2026-09-30):

```
ES      freeze.json 15:15:44   freeze.sha256 15:15:58   results.json 15:15:59
BASIS   freeze.json 15:21:16   freeze.sha256 15:21:16   results.json 15:22:17
AUCTION certificate+extract 15:30:07  entry_prints 15:31:02  seal_freeze.py 15:38:50
        freeze.json+sha 15:39:08     results.json 15:39:17   cli_transcript 15:39:17
```

- **A and C.** The seal file precedes the result, and the seal is *live* (NC1 proves the contract
  check is not dead code; `--check` proves the input check fires). But nothing retained pins the
  wall-clock order against a producer who re-seals after looking: the freeze is a plain file with an
  attacker-settable mtime, and A5's own "seal history" (an earlier contract `54b64f7c…` re-sealed as
  `42a158c5…`) is **producer narration with no retained earlier artifact**. Verdict: **UNVERIFIED**.
  *What would establish it:* an external trusted timestamp over `freeze.sha256` taken before the run
  (RFC 3161 token / transparency-log entry), or a git commit of `freeze.json` that precedes the
  commit or mtime of `results.json`.
- **B.** Strictly worse, and **REJECTED as stated**. The freeze asserts its sealed data-admission
  artefacts "carry no outcome quantity". `signal_extract.json` — sealed by the freeze, written
  **15:30:07, nine minutes before the seal** — contains `closing_cross_price_raw` non-zero with
  `closing_cross_valid = true` for **4,281 of 12,809 records**, i.e. the exit price of every
  analysed symbol. The producer acknowledges the pre-seal extraction (`as_run_deviations` B5-A2)
  but asserts "no Closing Cross price was read". That assertion is not checkable, and the
  artefact-level claim the freeze makes about its own inputs is false. The freeze therefore does
  **not** establish pre-outcome sealing for branch B; the whole measurement is derivable from
  artefacts that existed before the seal.

**A3 — canonical state.** Between 15:12 and 15:42 on 2026-09-30 the only writes under `M1/**` are
the four reselection spec files (15:19:35, 15:19:47, 15:20:07, 15:31:16). `M1/data` and `M1/output`
directories are untouched in that window (dir mtimes 2026-09-20 / 2026-09-28); the 128 `M1/**` files
that do carry a new mtime (126 at `2026-10-01T01:59:57`, 2 at `02:00:37`) and the root registries all
sit at the controller's regeneration (commits `7b76e9f`, `c8fd95d`), ~10 h after the runs.
No producer proposal reached canonical state: `EXPERIMENTS.csv` has **no** bridge row,
`EVIDENCE_LEDGER.csv` has **no** `EVD-0071`, `DECISIONS.md` has **no** `AMEND-C5-001`, and
`M1/work/patches/` stops at `P-0009`. Every branch marks its proposal `PROPOSED_NOT_APPLIED`.

Spec accuracy: the ES spec records freeze `42a158c5…`, module `2a07bbd4…`, horizons `[1,5,15]`
primary 1, the state/outcome/friction text and the forbidden list — all matching what executed.
The basis spec records `AMEND-C5-001` with `previous_spec_sha256 = c48abbdc…`, which equals both the
retained `.pre-C5.json` **and** the pre-edit git blob at `ac28929`; its `cost_floor` (lowest rung
0.024 % = 4.8 bps) and `reference_prices` (Binance mark excluded) match the run. The auction spec
records the v2 clause plus `clause_v1_retained` (31 locates); `spec_prev_retained.json`
(`5ef1dcac…`) equals the git blob at `ac28929`/`ba3705a`.

### CLAIM SET B — branch A (ES) kill

| # | claim | verdict | independent check |
|---|---|---|---|
| B4 | the 1 s side-signed markout arithmetic and sign convention | **VERIFIED** | independent re-implementation, deltas 0.0; frozen module re-run is **byte-identical** |
| B5 | causality: no future message, no exit-in-entry, no whole-window calibration | **VERIFIED** | strictly-past level-1 replay, 5,999/5,999 instants in the first 60 s, 0 mismatches |
| B6 | C0 is the observed-spread half-sum, not a hard-coded tick | **VERIFIED** | C0 reproduced from the observed grid; implied 1.047 ticks |
| B6′ | the unconditional/conditional comparison is on the same instants | **CONTESTED** | 598 quoted slots vs 583 non-zero-state observations |
| B7 | the single-window scope downgrade is present and honest | **VERIFIED** | `es_materiality.classify` code path + recorded values |

**B4.** Written from the frozen contract text, importing nothing from `M2.src.es_materiality`:
state `x(t) = (V_buy − V_sell)/D(t)` over `(t−1 s, t]` with aggressor 1 = buy; outcome
`direction·(M(t+h) − M(t))/M(t)·1e4`; friction `½S_entry + ½S_exit` per observation in bps of the
entry midpoint; 599 slots, censored at `k+h ≤ 599`.

| quantity | my independent value | published | Δ |
|---|---|---|---|
| pooled gross (1 s) | −0.0047336124 | −0.004733612439280016 | 0.0 |
| C0 | 0.5770016233 | 0.5770016233430615 | 0.0 |
| C* | −0.5817352358 | −0.5817352357823415 | 0.0 |
| observations / LONG / SHORT | 583 / 273 / 310 | 583 / 273 / 310 | 0 |
| LONG gross | +0.0171552482 | +0.017155248190908367 | 0.0 |
| SHORT gross | −0.0240099316 | −0.02400993163941367 | 0.0 |

A full re-run of the sealed contract on the retained inputs produced a **byte-identical**
`results.json` (sha256 `09c85629…`, equal to the published file). No sign error exists, and none
would have been invisible: the ES module evaluates the classification in both bps and USD and
raises if the unit conversion changes the verdict.

**B5.** Rebuilding level 1 from `bbo_increments.csv` (instrument 3445 only, `exchange_send_ns ≤ t`)
and comparing with the admitted `spread_grid.csv` gives **0 mismatches at 5,999 compared instants**
over the first 60 s; the module's own audit reports 59,999/59,999 with `max_abs_deviation_points =
0.0`. A grid containing lookahead cannot agree with a strictly-past reconstruction, so the state is
causal. The state window `(t−1 s, t]` never reaches forward, the exit consumes quotes `≤ t+h`, the
entry never consumes the exit, and there is no whole-window calibration to leak (no thresholds
exist; the friction is per-observation). Sensitivity control: dropping the instrument filter makes
the same replay mismatch **1,438 / 5,999** — the check is not vacuous.

**B6.** C0 reproduced independently as the mean over the 583 evaluated observations of
`½S_entry + ½S_exit` in bps of the entry midpoint, from the observed grid. The grid's observed
spreads are 1–11 ticks (58,832 of 59,999 points at 1 tick, mean 1.0338 ticks), so the implied C0 is
**1.047 ticks** — non-integer. A hard-coded one-tick-per-side would be 1.102 bps. **CONTESTED
sub-item:** the published unconditional markout (+0.015674606811580484) is `_mean(unconditional
[quote_mask(panel)])` (`es_materiality.py:401`), i.e. the mean over the **598 quote-available
slots**, while the conditional gross is over the **583 non-zero-state** observations. On the same
583 instants the unconditional value is **+0.0208001** (Δ = 0.0051 bps). The two are therefore *not*
computed on the same instants. This is not decision-relevant (both are far below C0 and the verdict
is set by `g ≤ 0`), but the report's table invites the same-population reading.

**B7.** `es_materiality.classify` applies, in frozen order: coverage failure →
`INDETERMINATE_COVERAGE`; nominal `SURVIVE_PROVISIONAL` → `INDETERMINATE_COVERAGE` with
`SINGLE_ADMITTED_WINDOW_SCOPE` ("not admissible from one window"); nominal `KILL_MATERIALITY` →
`scope = SAMPLE_SCOPED_DEVELOPMENT_KILL`. The recorded object matches exactly
(`verdict = KILL_MATERIALITY`, `clause = PRIMARY_HORIZON_GROSS_NOT_POSITIVE`,
`scope = SAMPLE_SCOPED_DEVELOPMENT_KILL`, `nominal_verdict_before_scope_and_coverage` present).
A single window can indeed never yield survival.

### CLAIM SET C — branch C (basis) kill

| # | claim | verdict | independent check |
|---|---|---|---|
| C8 | sign convention of the signed strategy P&L | **VERIFIED** | independent recomputation from panel + raw zips, deltas 0.0 |
| C8′ | a reversed sign would change the verdict | **CONTESTED** | reversed structure −0.0330 bps, flipped HL carry −0.0874 bps; both still KILL |
| C9 | C0 = 2 × 0.024 %, lowest published rung, rule honoured | **SUPPORTED_SCOPED** | live retrieval of SRC-0213; counterfactual C0 = 9.0 / 0 |
| C10 | the 84 unresolved settlements are bracketed, never zeroed; bias direction | **SUPPORTED_SCOPED** | interval arithmetic reproduced; measured component *does* carry zeros |
| C11 | one-hour hold construction, staleness, no drop/dup | **VERIFIED** | 4,979 contiguous holds; staleness recomputed |

**C8.** `envelope.funding_cashflow` is explicit: a short receives `+rate·notional`, a long pays
`−rate·notional`; the structure is short-HL / long-Binance. Recomputing from `paired_hours.csv` plus
the six raw `fundingRate-*.zip` archives (no import of the module):

| component | mine | published | Δ |
|---|---|---|---|
| Hyperliquid funding carry | +0.059699759791 | +0.05969975979112272 | 0.0 |
| Binance funding carry | −0.026753002611 | −0.02675300261096606 | 0.0 |
| hedge MTM residual | −0.000461589484 | −0.0004615894835227425 | 0.0 |
| gross (measured) | +0.032485167697 | +0.03248516769663392 | 7e−18 |
| min / max | −10.934471872162 / +13.668848125631 | identical | 0.0 |
| holds / unresolved | 4,979 / 84 | 4,979 / 84 | 0 |

(The Binance mean is over all 4,979 holds with the 84 unresolved carried at 0.0, which is the
module's own `measured_component` convention — see C10.) **CONTESTED sub-item:** the assignment's
premise that a reversed sign would change the verdict is not supported. Reversing the structure
gives −0.033048 bps and flipping only the HL carry gives −0.087373 bps; in both cases `g ≤ 0` and
`hi ≤ C0` still hold, so the verdict stays `KILL_MATERIALITY`. The kill is **sign-robust**; the sign
matters for interpretation (`T* = 145.69 h`) and for the clause, not for the decision.

**C9.** 2 × 0.024 % = **4.8 bps**, and the artifact's `c0_usd` is 0.00048 with the lowest-rung item.
SRC-0213 was retrieved live during this verification: the Hyperliquid perps fee table shows tier 0
base rate taker **0.045 %** and tier 6 (> $7 B 14-day volume) base rate taker **0.024 %** — the
lowest published base-rate taker rung, exactly as recorded (access 2026-09-20, publisher and quote
in the freeze). Using 0.024 % rather than the 0.045 % base tier **lowers** C0 from 9.0 to 4.8 bps,
which makes the kill **harder**; the counterfactual table confirms (C0 = 9.0 → KILL, C0 = 0 →
INDETERMINATE). `base_tier_scenario.json` carries `may_decide_the_kill: false`, the classifier never
consults it, and `c0_items` notes "LOWEST RUNG, not the base tier". The operator's rule is honoured.
Named limits: (i) the c0 note "no account state pays less than 0.024 %/side" is not literally true
against the live schedule — staking discounts of up to 40 % apply to every rung and HIP-3
growth-mode perps are 5–10× lower — but that direction only makes the kill harder still; (ii) the
live page carries no version archive or effective date (recorded as a limitation in `EVD-0043`), so
the 2026 rate card's applicability to the 2026-03…09 sample is not independently confirmable.

**C10.** The count (84) and the interval arithmetic are exact: `lo = −0.0101126048 + (−0.0168708576)
= −0.0269834624`, `hi = +0.0755247339 + 0.0207106648 = +0.0962353987`, and the point estimate adds
the bracket midpoint +0.0019199036 to the measured component. **Named limit (CONTESTED in wording,
not in substance):** `hold_terms` passes `funding_rate = 0.0` when the settlement is unobserved, so
the 84 holds contribute **exactly zero** to `measured_component_bps` — they are bracketed, not
zeroed, only in the *decision* quantity. The artifact's "the unknown rate is never taken as zero" is
true of the decision input and false of the measured series. The direction-of-bias claim ("the true
C* is more negative than reported") is supported **only through the unresolved C1 items**
(Binance fee/spread/impact/capital, all `null`), which are one-sided; the funding bracket itself is
two-sided (−4.784 … −4.747 bps around the reported −4.76559), so it does not by itself establish a
more-negative true C*.

**C11.** Holds `j ∈ [W0+1h, W1−1h)` are 4,979, contiguous, with every entry/exit/carry row present
(no drop, no duplicate); the panel is 4,981 contiguous hourly rows with the two structural boundary
hours declared in the freeze. Staleness recomputed from `hl_funding_time_ms`: entry and exit
reference offsets 0.000–**0.261 s**, 4,913 non-zero, **0 beyond the 1.0 s tolerance** on both legs.
The report's sub-second narrative reproduces exactly: relative to the *decision instant + 1 h*, the
carry print lands after in **2,450** holds, before in **2,460**, max deviation **0.212 s** (69 ties).

### CLAIM SET D — branch B (auction) INDETERMINATE

| # | claim | verdict | independent check |
|---|---|---|---|
| D12a | orphan-message evidence (7,176,224 = 35.75 %) | **VERIFIED** | components sum exactly; 7,176,224/20,072,550 = 0.357514 |
| D12b | the reconstruction diagnostic | **CONTESTED** | the far-band gate is structurally 0 (near/far ≡ 0 in all 12,809 reads) |
| D12c | the entry books genuinely cannot be validated | **SUPPORTED_SCOPED** | orphans + one-tick + mid deviation + the D13 decomposition |
| D13 | is −108.9 bps an artifact or a real result | **VERIFIED (as artifact)** | identity decomposition; concentration; spread-restricted reruns |
| D14 | no KILL recorded; no quiet substitution of the mechanism metric | **VERIFIED** | verdict field, CLI transcript, proposal decision `WEAKENED`; classifier input is `gross_usd_per_share` |
| D15 | coverage accounting and the subfloor clause by identity | **VERIFIED** | coverage block, clauses list, missingness by identity and reason |
| D16 | universe v2 is a transcription repair; pre-repair spec byte-identical | **VERIFIED** | certificate counts; retained spec == git blob `5ef1dcac…` |

**D12.** `orphan_total = 7,176,224` = 4,623 cancels + 3,703,481 deletes + 30,676 executes +
3,437,444 replaces, over 20,072,550 in-scope book messages → **0.357514**. One-tick agreement
506/1,219 = **0.41509**; median |reconstructed mid − reference| **9.5 bps**, p90 **50 bps**
(≈6.5 and ≈34 ticks on a $68.12 mean name). **CONTESTED:** `within_far_band_ratio = 0.0` is
degenerate. `read_1555_near_price_raw` and `read_1555_far_price_raw` are **0 in all 12,809 extract
records**, and the code tests `if far and near and near <= mid <= far`, so the preregistered gate
(`reconstruction_min_within_far_band_ratio = 0.9`) **cannot pass for any reconstruction, faithful or
not**. It is an absent-input condition masquerading as a quality measurement. This is *disclosed*
by the producer in `as_run_deviations` B5-A4 and `proposal.json` B5-D2 ("0/1219 evaluable"), so it
is not hidden — but `results.json:book_reconstruction` presents the 0.0 beside a
reconstruction-quality note, and the V3 brief's framing of it as a diagnostic is not what the
number is. The clause's *substance* survives on independent evidence, and the clause blocked a KILL
rather than manufacturing one.

**D13 — the critical attack.** The −108.89 bps is **predominantly an artifact of the unvalidated
reconstruction**, and the evidence says so four ways:

1. **Exact identity.** `mean capture = mean mechanism − mean side-signed(entry − reference)` =
   `+6.5168 − 115.4115 = −108.8946` bps. The entire loss *is* the gap between the reconstructed
   entry price and the exchange's own 15:55 reference price.
2. **Concentration.** The worst 50 of 1,261 symbols carry **93.9 %** of the total loss; the worst
   single symbol carries 12.9 %; the largest reconstructed entry spread is **$11.64 on a $2.10
   stock** (a book 5.5× the price — not a displayed top of book under any reading).
3. **Restriction.** On the 348 symbols whose reconstructed spread is ≤ 10 bps of price the capture
   is **−0.60 bps** (mechanism +3.55); at ≤ 5 % spread it is −15.7 bps; entering at the
   reconstructed **midpoint** gives −6.98 bps instead of −108.89 bps.
4. **The gate could not discriminate** (D12).

*What the evidence supports:* the reconstruction-free mechanism displacement, exchange reference →
closing cross, is **positive: +6.52 bps, CI [2.00, 11.00]** — above the 1.02 bps floor; and the
executable capture is **not measurable on this tape**. *What it does not support:* any estimate of
realizable capture, and therefore **any KILL**. The producer's own
`proposal.json:decision_implication` says a kill is warranted "only if the operator accepts that the
reconstruction bias cannot account for a −109 bps gap" — it can, so the recorded INDETERMINATE is
the correct outcome. Note the inversion: the *secondary* mechanism metric is the trustworthy,
reconstruction-free reading and it is positive; the *primary* economic metric is the untrustworthy
one. A positive mechanism metric is not a survival claim either (it assumes entry at the reference
price, which is not executable), and the branch does not claim otherwise.

**D14.** No KILL is recorded. `results.json:decision.verdict = INDETERMINATE`, clause
`ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED`; `rule_verdict = KILL_MATERIALITY` is kept as an explicitly
named, superseded field (`rule_clause = SUPERSEDED_BY_ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED`); the
CLI transcript prints `DECISION: INDETERMINATE`; `proposal.json:experiment_row.decision =
INDETERMINATE` and the patch decision is `WEAKENS`, not `KILLS`. The classifier is called on
`gross_usd_per_share` (economic), never on the mechanism metric — no quiet substitution.

**D15.** `coverage.floor_applies_to = "input_availability_ratio"` with value **1.0** against the
0.95 floor; `signal_scope_ratio = 0.5217` (1,286 of 2,465) with `signal_scope_subfloor = true`,
reported **by identity** in the coverage block, the missingness audit (by symbol and reason), the
CLI transcript and `decision.clauses` (which lists *both*
`ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED` and `SIGNAL_SCOPE_SUBFLOOR`). Nothing is hidden.

**D16.** The repair is a transcription fix and is documented as such: the certificate's own counts
give classification/subtype pairs **C/Z = 4,183** vs **C/C = 31**, and the v1 clause
(`Issue Sub-Type = C`) admitted **31** locates; v2 drops the sub-type constraint and restricts
Market Category to Q/G/S, admitting **2,483**, of which **2,465** carry a valid Closing Cross.
`spec_prev_retained.json` sha256 `5ef1dcac96e80847069006d24477dc12226f4d907b8798a522c63c14ff6e8694`
equals the git blob at `ac28929` **and** at `ba3705a` (byte-identical to the pre-edit committed
version) and equals the freeze's declared `previous_spec_sha256`; the current spec carries the same
text in `universe.clause_v1_retained`. Named limits: the gloss "Appendix E defines C = Common
Shares, Z = Not Applicable" is an external-source claim with no retained copy of Appendix E in the
repo; and the manifest retains only marginal counts, so 2,483 cannot be recomputed from the
retained artifact alone.

**Incidental defect (branch B).** The freeze states deviations are "recorded in
`results.json:as_run_deviations_from_freeze`"; **no such key exists** in `results.json`. The
deviations live in a sibling file, as that file's own statement discloses. Dangling reference only.

## 2. Negative controls

| id | control | result |
|---|---|---|
| NC1 | ES contract tampered (primary horizon 1 s → 5 s), genuine seal left in place | `MeasurementError: sealed contract changed since the freeze: e4f7f137… != 42a158c5…`, **no output written** — the seal check is live, not dead code |
| NC2 | ES: flip the side-signed direction | verdict unchanged (`KILL_MATERIALITY` both ways; only the clause moves from the gross arm to the floor arm); `C0 = 0` also kills — the ES kill is sign- and floor-robust |
| NC3 | auction: apply the frozen rule with the entry-book clause **disabled** | `KILL_MATERIALITY` vs the delivered `INDETERMINATE` — the clause is decision-changing, and it blocks a kill rather than creating one |
| NC4 | auction: enter at the reconstructed **midpoint** (remove the half-spread and most of the reconstruction error) | −6.98 bps over 1,219 symbols instead of −108.89 — a 15× shrink from a single substitution |
| NC5 | ES replay without the instrument filter (natural control) | 1,438/5,999 mismatches — the strictly-past replay is sensitive, so its 0-mismatch result is informative |
| NC6 | `basis_materiality --check` today | `inputs_unchanged: false`, `drifted_inputs: ["M2/src/admission.py"]`, REFUSED — the drift detector fires |

## 3. Most decision-relevant findings

1. **Branch B's verdict is right, and its headline economic number is not.** The −108.89 bps is
   ~100 % a reconstruction artifact (the entry sits 115 bps away from the exchange's own reference;
   50 of 1,261 garbage books carry 94 % of the loss; the worst book is $11.64 wide on a $2.10
   stock). The reconstruction-free mechanism displacement is **positive, +6.52 bps [2.00, 11.00]**,
   above the 1.02 bps floor. `INDETERMINATE` is therefore correct, and the branch must not be read
   as a kill — nor as a survival.
2. **Branch B does not have a valid sealed-before-outcome claim.** `signal_extract.json`, sealed by
   the freeze, was written nine minutes *before* the seal and already contains the Closing Cross
   price for 4,281 symbols. The freeze's assertion that its inputs "carry no outcome quantity" is
   false.
3. **Branch C's seal no longer verifies in place.** `M2/src/admission.py` drifted after the run
   (branch B's `AUCTION_V2` addition); the run-time value is recorded in `run_inputs.json` and the
   measurement is unaffected (verified by full independent recomputation), but the seal is stale.
4. **Branches A and C are reproducible and internally exact.** The ES contract re-runs to a
   byte-identical `results.json`; the auction measurement re-runs to an identical result modulo
   `generated_utc`; every branch-C component reproduces to 0.0.
5. **No producer touched canonical state**, and no proposal was applied.

## 4. UNVERIFIED items and what would establish them

- **Pre-outcome sealing for A and C** — needs an external trusted timestamp over `freeze.sha256`
  (RFC 3161 / transparency log) or a git commit of the freeze preceding the result. Retained
  evidence is mtimes and a live self-check, neither of which resists a re-seal.
- **A5's "seal history"** (an earlier contract `54b64f7c…` superseded before the first real
  computation) — the earlier artifact was not retained; the narration is unverifiable.
- **Branch B's "no Closing Cross price was read before the seal"** — unverifiable by construction;
  the artefact-level claim is already contradicted (see above).
- **The ITCH Appendix E gloss** (`C = Common Shares`, `Z = Not Applicable`) — no copy of Appendix E
  is retained in the repository; only the session's own classification/subtype counts can be checked.
- **The Hyperliquid rate card's applicability window** — the live page carries no version archive or
  effective date; the 2026-03…09 applicability of the current schedule rests on the recorded
  provenance alone.
