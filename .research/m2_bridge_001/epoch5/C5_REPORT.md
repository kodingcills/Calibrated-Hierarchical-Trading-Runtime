# C5 — Hyperliquid/Binance funding-basis materiality (GOAL-M2-BRIDGE-001, epoch 5)

**Verdict: `KILL_MATERIALITY`** — scoped to the frozen one-hour formulation on the admitted
4,981-hour panel.  A longer-horizon, other-pair or state-conditioned reformulation would be a
**new candidate**, not a reinterpretation of this result.

Frozen contract sealed **before** any branch-C economics were computed:
`M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/freeze.json`
sha256 `389b8f4d65b1b2f54bf5eb29266c74c078ca7187e8c1b4455052fa52d780e3a7`
(`freeze.sha256` = `7d166927648ef8f7f5a92a75a1135e2abbf2811d11166f49f15123dddbaeff33`).
`--run` refuses to emit a result if `freeze.sha256`, the module hash or any sealed input hash
has moved; both re-runs produced byte-identical `results.json`.

## 1. Admission (step 1, read-only)

```
$ python3 -m M2.src.admission --manifest M2/data/derived_basis/manifest_basis.json --branch BASIS --root .
DATA_VALID  branch=BASIS  contract=ADMISSION-BASIS-C-v1  manifest=BASIS-FREE-PUBLIC-2026-03-05T11:00:00Z--2026-09-28T23:00:00Z
  no findings                                                       exit=0
```

W3's own module was **not** imported or re-run, and the manifest was not modified. The engine's
BASIS contract (`required_file_roles = hl_funding, hl_mid, binance_mark`) still declares the
Binance **mark** file; the operator amendment moves the *price term* to last-trade klines, so the
module additionally re-derives both reference series from the raw payloads whose sha256 are sealed
in the freeze (`klines-1h-*.zip`, `hl_candles_1h_0.json`) and refuses on any mismatch. No
`admission.py` change was needed or made.

## 2. Causal reference prices and boundary staleness (step 2)

Panel row `K` carries the candle covering `[K, K+1)` — verified directly from the raw bytes (HL
candle `t=1772708400000, T=1772711999999, c=72886.0`; Binance kline `open_time=1772708400000,
close_time=1772711999999, close=72879.90`). A decision at instant `h` may therefore use only the
row `K-1` reference, **not** row `K`. Both reference series were rebuilt from the raw archives and
diffed onto the panel: **4,981/4,981 rows, 0 missing, 0 value mismatches** for each leg.
`binance_mark_close` is excluded from the price term (it is a mark, not a last trade).

| staleness of the decision instant against the reference it may use | min | max | mean | p95 | p99 | non-zero | > 1.0 s tolerance |
|---|---|---|---|---|---|---|---|
| entry (row `J-1`), Hyperliquid leg | 0.000 s | 0.261 s | 0.0375 s | 0.081 | 0.118 | 4,913 / 4,979 | **0 (0.000)** |
| entry (row `J-1`), Binance leg | 0.000 s | 0.261 s | 0.0375 s | 0.081 | 0.118 | 4,913 / 4,979 | **0 (0.000)** |
| exit (row `J`), Hyperliquid leg | 0.000 s | 0.261 s | 0.0375 s | 0.081 | 0.118 | 4,913 / 4,979 | **0 (0.000)** |
| exit (row `J`), Binance leg | 0.000 s | 0.261 s | 0.0375 s | 0.081 | 0.118 | 4,913 / 4,979 | **0 (0.000)** |
| last-millisecond read of the same candles | 0.001 s | 0.262 s | 0.0385 s | 0.082 | 0.119 | 4,979 / 4,979 | 0 (0.000) |

Both legs share one distribution by construction: both series are UTC-hour-aligned candles whose
declared close time is the hour's final millisecond. The declared tolerance is **1.0 s** (it must
exceed the 0.261 s settlement jitter documented before the freeze and stay far below one hour);
**0.0 %** of decisions use a stale reference. Additional sub-second finding: the collected carry
print lands *after* the nominal one-hour mark in 2,450 holds and *before* it in 2,460 (max
deviation 0.212 s) — the freeze resolves that by declaring that the exit is taken **at the boundary
print**, so the carry is collectible in every hold; the degenerate alternative is reported in §6.

## 3. The frozen measurement (steps 3–4)

Trimmed exact wording lives in `freeze.json`. In short: **unconditional** SHORT Hyperliquid Core
BTC perp / LONG equal-notional Binance USD(S)-M BTCUSDT perp; decision at hour `J` immediately
after the bucket-`J` funding settlement; entry on the row `J-1` reference; exit one hour later on
the row `J` reference; carry collected = the print labelled `J+1` on each venue (Hyperliquid pays
the hour just elapsed; Binance settles 8-hourly). Holds `J ∈ [W0+1h, W1-1h]` = **4,979**, contiguous
tiling of the window, zero missing, zero duplicates. The two non-traded panel hours are structural
boundary hours, declared in the freeze before the run, not a window shrink.

| quantity | value |
|---|---|
| **gross (signed, bps of notional per one-hour hold)** | **+0.03441** (measured component +0.03249, unresolved-bracket midpoint +0.00192) |
| mean / median / sd / min / max | 0.03249 / 0.06151 / 1.53809 / −10.93447 / +13.66885 |
| Hyperliquid funding carry | **+0.05970 bps/h** |
| Binance funding carry | **−0.02675 bps/h** |
| hedge mark-to-market residual | **−0.00046 bps** (sd 1.51846) |
| carry per hour (for `T*`) | +0.03295 bps/h |
| **`T* = C0 / carry`** | **145.69 hours** (interpretive only) |
| coverage | panel 4,981/4,981 buckets, 0 missing, 0 duplicates; holds **4,979/4,979**; 4,895 holds with every required input; **84 holds (1.687 %) with an unobserved Binance settlement rate, bracketed, never zero** |
| hour-clustered bootstrap CI (10,000 resamples, seed 20260930, 2.5/97.5) | **[−0.01011, +0.07552] bps**, SE 0.02195 |
| decision interval (bootstrap ∪ unresolved bracket) | **[−0.02698, +0.09624] bps** |
| moving-block 24 h check (same seed) | [+0.01576, +0.04764] bps, SE 0.00810 |
| significance (reported, never a criterion) | t = 1.567 (hour-clustered), t = 4.247 (block) |
| **structural cost `C0`** | **4.8 bps/hold** = 2 executions × the lowest published Hyperliquid perp taker rung 0.024 % |
| **break-even residual `C*` = g − C0** | **−4.76559 bps/hold** |
| `C1` | 4.2 bps known (state-dependent uplift to the 0.045 % base tier) + three UNKNOWN items; `c1_total_usd = null` (unbounded) |
| **classification** | `hi` (0.09624) ≤ `C0` (4.8) → **`KILL_MATERIALITY`** |

The kill is decided by the **floor clause** (`hi ≤ C0`), not by the sign: the gross is positive but
~**50×** smaller than the cheapest unavoidable execution floor, and ~**140×** smaller than the
base-tier reference path. Significance is reported separately and is not an input
(`significance_is_decision_criterion: false`).

## 4. Cost treatment, provenance and the base-tier scenario (separate, not deciding)

`C0` = the **lowest rung** of the published Hyperliquid taker schedule, justified as unavoidable on
the frozen path (the leg must be opened and closed; a taker fill is the only guaranteed execution
at a reference price; no account state pays less than 0.024 %/side for it). Provenance for every
recorded fee value: `SRC-0213`, `https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees.md`,
publisher Hyperliquid documentation, **accessed 2026-09-20**, effective period "current schedule at
access", quote "base tier (< $5m 14-day volume) taker/maker 0.045 %/0.015 %, with tier rungs to
0.024 %/0 % above $7b" — contemporaneous with the 2026-03-05…2026-09-28 sample, so the 2026 rate
card is applicable to this window (unlike the Nasdaq 2019 case).

Reference execution path (`M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/base_tier_scenario.json`,
`may_decide_the_kill: false`): Hyperliquid base tier 0.045 %/side → **9.0 bps/hold** (verified,
`UNRESOLVED_C1`); **Binance base tier: no value asserted** — no verified Binance USD(S)-M schedule
exists in this repository (public host returns HTTP 451 here; the M1 evidence ledger carries no
Binance fee fact) and inventing one is out of scope. `C1` therefore stays unbounded and is reported
as a caller-supplied level table (0 → 38 bps), every row of which is negative (`survives_floor:
false`).

## 5. Independent verification

A separately written throwaway recomputation (raw CSV + raw `fundingRate` zips only, no import of
the module's measurement path) reproduces the series exactly: mean gross **0.032485167697** bps,
HL carry 0.059699759791, Binance carry −0.026753002611, MTM −0.000461589484, min/max
−10.934472/+13.668848, 4,979 holds, 538 observed + 84 unresolved. `python3 -m unittest
M2.tests.test_basis_materiality` → **16 tests OK** (causal alignment, gross identity, both carry
signs, measured-zero settlement absence, never-zero archive gap, bracket widening, staleness
tolerance, C0/C1 split, determinism, and the real panel's grid/hash/raw-archive agreement);
`M2.tests.test_envelope` → 38 tests OK (unchanged).

## 6. Reported sensitivities (declared, not deciding)

* **Exit at the nominal one-hour mark** (carry structurally uncollectible): mean −0.00046 bps —
  i.e. the pure hedge residual. This is a strict lower read, not the frozen convention.
* **`C0 = 0`** (were a free maker execution assumed): the verdict would be `INDETERMINATE`, since
  the decision interval [−0.02698, +0.09624] straddles zero and any positive floor kills. The
  frozen `C0` is the lowest *published taker* rung, never the base tier.
* **Binance-funding-constrained window** (W3/W4's 4,302 h alternative): not used for the verdict;
  the primary panel keeps 100 % of the availability-derived window and brackets the missing 84
  settlements instead of shrinking.

## 7. Proposed canonical update (emitted, not applied)

`M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/canonical_update_proposal.json`
(sha256 `9c45c91e83b2e683840089eb36ea228ea6fa7e6ad475ad6387db2a8f24d718b5`): record the amended
contract in the branch-C spec (done — own-branch file), and, for the controller to apply, register
`M2-BRIDGE-HL-BINANCE-BASIS` in `EXPERIMENTS.csv`, record `AMEND-C5-001` plus this outcome in
`DECISIONS.md`, and set the candidate row's scoped status. **No canonical artefact was edited.**

## 8. Limits and blocking findings

* **No `EXTERNAL_DATA_BLOCK`**: the causal construction satisfies admission.
* Binance funding is unarchived for 84 in-panel settlements (the 2026-09 monthly file is
  unpublished and the host is 451 here); handled as an explicit bracket [−0.01687, +0.02071] bps,
  width 0.0376 bps — an order of magnitude below the gap between the gross and the floor.
* The Binance leg's fee, spread, impact and capital terms remain UNKNOWN: the C1 subtotal is
  unbounded, and the true `C*` is **more negative** than −4.77 bps, never less.
* The measurement is one unconditional one-hour formulation on one development-grade window; the
  hedge residual is mean-zero (−0.00046 bps, sd 1.52 bps) and carries no drift, which is the
  internal validity check that the carry number is not contaminated by the price term.
* Pre-existing artefacts untouched; nothing committed; `M1/src/materialize.py` and
  `M1/src/validate.py` were deliberately **not** run (controller's final step).

## 9. Artifacts (sha256)

| path | sha256 |
|---|---|
| `M2/src/basis_materiality.py` (new) | `ad919f21abae3c845d8de1c2f64bcfeaa4b6c49e97957946ba9269438cf93fcf` |
| `M2/src/envelope.py` (one additive helper `perp_price_pnl`, +28 lines) | `a2777d0568a450e1ce48bc4becdcb3c49c7c3740a82da748ece31f223c7670c0` |
| `M2/tests/test_basis_materiality.py` (new, 16 tests) | `238b38d45db77d5ff2531f13b15908d8fbaa7e66bf2ad0bc62b1d14db6936824` |
| `M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/freeze.json` | `389b8f4d65b1b2f54bf5eb29266c74c078ca7187e8c1b4455052fa52d780e3a7` |
| `…/freeze.sha256` | `7d166927648ef8f7f5a92a75a1135e2abbf2811d11166f49f15123dddbaeff33` |
| `…/results.json` | `97a4d7acf71db4837ad2e8cf090350b5615c2716684df531e74a6ef7f550d722` |
| `…/run_inputs.json` | `d6f1ca96b395a7402e23712c44424a518142c566986bc4fd98c8be6040b7500a` |
| `…/base_tier_scenario.json` | `42393b027d0dcb8f426addd0d0d6ae81613e26b0a60440801048931ff7904eaa` |
| `…/canonical_update_proposal.json` | `9c45c91e83b2e683840089eb36ea228ea6fa7e6ad475ad6387db2a8f24d718b5` |
| `M1/work/reselection_specs/TUP-HYPERLIQUID-BTC-FUNDING-BASIS.json` (amended) | `53bbd8f22d5b45cb1d39db635b2182d44909d440ec5df05606fa41df59455d2b` |
| `M1/work/reselection_specs/TUP-HYPERLIQUID-BTC-FUNDING-BASIS.pre-C5.json` (retained) | `c48abbdc551a5aa7b1aa0842c531cdcbf2189e758660e3ef35c34a3fb3c76814` |
| `M2/data/derived_basis/paired_hours.csv` (input, unchanged) | `c95ac782670a6ea5cb0d57c243110948969566a988c02a10283aebe91cb562a3` |
| `M2/data/derived_basis/manifest_basis.json` (input, unchanged) | `7544020ab1bd041b7c3c50c9bdb1f4168e88fe0a72c56fe102b45495412d874d` |

Reproduce: `python3 -m M2.src.basis_materiality --seal && python3 -m M2.src.basis_materiality --run`
(the module refuses a run whose seal no longer matches its code or inputs).
