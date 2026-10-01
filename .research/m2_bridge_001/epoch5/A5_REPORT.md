# A5 — CME ES H3 OFI materiality, frozen single-window measurement (GOAL-M2-BRIDGE-001, epoch 5)

Branch **A** — `TUP-CME-ES-H3-OFI-AGG`. Scope: **seal a preregistered freeze and then run the frozen
materiality measurement**, once, on the single admitted ESU3 window
`2023-07-17 13:30:00Z–13:40:00Z`. No purchase, no credentials, no network acquisition, no commit.
`M1/src/materialize.py` and `M1/src/validate.py` were **not** run (the controller runs them once).

**Verdict: `KILL_MATERIALITY` at the primary horizon, clause `PRIMARY_HORIZON_GROSS_NOT_POSITIVE`,
recorded as a `SAMPLE_SCOPED_DEVELOPMENT_KILL`.** The pooled side-signed 1 s markout is
**−0.0047336 bps** against a measured observed-spread round trip of **0.5770016 bps**
(C\* = **−0.5817352 bps**). Every term-structure point is at most 8.7 % of that floor. The coverage
floor passed, so the kill is not a coverage artifact; the scope rule nevertheless forbids reading it
as anything wider than this one window.

---

## 1. Files written (only these)

| file | sha256 | note |
| --- | --- | --- |
| `M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json` | `42a158c584552392e6c21535f35b3887228ea209c47257dee97672f6bfd75568` | sealed contract |
| `M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.sha256` | `d2a6fa7f7a4ee02fdd96efd5c598a0a37720268d585214b5534af899cdeaae12` | hash of the contract (`42a158c5…  freeze.json`) |
| `M2/experiments/M2-BRIDGE-ES-H3-OFI/run_inputs.json` | `581a219c7602f8b1300428c6c2581a6d2f993bbdc9345ac1a2abb4ad30a2408d` | as-run inputs/artifacts, written after the run |
| `M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json` | `09c8562999304072a5f5b5184bece3ba0588d1d57754ae776b3c6934f1487ac2` | the frozen result |
| `M2/experiments/M2-BRIDGE-ES-H3-OFI/proposal.json` | `c57c7d18d68e8c0725d471998cfda0ce67b51f6dcf6380cbfb7f6ac61f7b2d5b` | canonical-update PROPOSAL, not applied |
| `M2/src/es_materiality.py` | `2a07bbd45dc42dd6bd18d66d83563bbbf18dffd96b52dc6b1bd6824c27b3101c` | the analysis module |
| `M2/tests/test_es_materiality.py` | `ecfd95f0744c25be134cfa14353dd38a2646a67fa7aa256b0716722d0abc3e25` | 30 tests |
| `M1/work/reselection_specs/TUP-CME-ES-H3-OFI-AGG.json` | `385354abb32d989ec13d68a3f5cea7a216bf3da4402b0c00d83038c229836dc8` | additive frozen-measurement record |
| `.research/m2_bridge_001/epoch5/A5_REPORT.md` | this file | |

No other file was touched. `M2/src/admission.py` was **not** modified: the ES contract
`ADMISSION-ES-H3-v1` already admits this slice (`DATA_VALID`), the measurement consumes the admitted
artefacts directly, and the additive-contract-entry permission was not needed — so the sibling
working on that file could not be raced.

---

## 2. What was frozen, and when

Reused arithmetic (imported, never re-implemented): `M2/src/envelope.py`
(`midpoint_markout_friction_bps`, `break_even_residual`, `c1_sensitivity`, `CostItem` /
`Provenance` / `reference_path_scenario`, `classify_materiality`, `bps_to_usd`,
`significance_against_zero`) and `M2/src/calculate.py::block_bootstrap_ci`. **No extension to
`envelope.py` was needed**, so the module that owns the arithmetic is untouched by this branch.

| frozen element | value |
| --- | --- |
| horizons | H3 = 1 s, 5 s, 15 s; **PRIMARY = 1 s**; the verdict is computed at the primary horizon only and the term structure is reported |
| clock | availability = venue send time (`exchange_send_ns`); a decision consumes only messages stamped `<= t`; a capture-receipt pass (`ts_recv_ns`) is reported as robustness and is never the verdict |
| state | `x(t) = (V_buy − V_sell) / D(t)`; `V_*` = aggressor-signed ESU3 size in `(t−1 s, t]`; `D` = `bid_sz + ask_sz` displayed at `t`; sign is the direction; balanced / unquotable ⇒ **no position**; **no thresholds exist** |
| outcome | side-signed midpoint markout in bps of the entry midpoint on the reconstructed top of book, no executable-price substitution |
| friction | `1/2 S_entry + 1/2 S_exit` from the **observed** quoted spread at both instants, per observation; no one-tick stand-in, no `2 × C0` safety factor |
| C0 / C1 | C0 = the measured friction only (no verified account-independent mandatory charge exists); C1 = CME exchange / clearing / FCM declared with **UNKNOWN** value, never zero |
| coverage floor | quote coverage ≥ 0.95, observation coverage ≥ 0.75, ≥ 250 observations, at the primary horizon |
| inference | instrument × contiguous 60 s block cluster bootstrap, 2000 resamples, seed `20260717` (stride 3 per horizon/state), percentile 2.5/97.5 |
| metric / kill rule | pooled primary-horizon gross vs C0; `KILL` if `g ≤ 0` or `hi ≤ C0`; `SURVIVE` if `lo > C0`; else `INDETERMINATE`; coverage failure ⇒ `INDETERMINATE_COVERAGE`; a nominal survive from one window is downgraded |
| decision grid | 1 s slots `k = 0 … 600 − h` over the admitted window, censored so that `k + h ≤ 599` (the exit instant must lie inside the admitted 10 ms grid); 599 / 595 / 585 slots for 1 s / 5 s / 15 s |
| excluded slots | an unquoted, zero-depth or balanced entry, or an unquoted exit ⇒ **not** an observation; counted in coverage, never imputed |

**Seal history (honest, both seals precede any real outcome).** The contract was written once
(`54b64f7c…`) with the module hash `2a07bbd4…` and the then-current test-file hash; the unit tests
then exposed a **wrong expectation in the test** (not a module defect), the test file changed, only
its recorded hash was updated, and the contract was re-sealed as `42a158c5…` **before** the first
real computation. The measured module hash never changed. No post-result parameter was ever touched:
the result comes from exactly one run of the sealed contract.

**Freeze enforcement at run time.** `es_materiality.py` re-hashes itself, the six declared inputs,
the three reused modules and the sealed contract, and **refuses to run** on any mismatch
(`MeasurementError`). All were unchanged at run time (see `results.json:validity_checks`).

---

## 3. Block-condition check (the named defect that would have stopped this)

Not triggered, and the check is positive rather than assumed:

* the state is structurally causal — `(t − 1 s, t]` with `≤` at the decision instant and `<` at the
  far edge, so a message stamped after the decision can never enter it (pinned by three tests);
* an **independent strictly-past replay** of level 1 (only `direct_l1`, `md_price_level == 1` rows
  with `exchange_send_ns <= t`, artefact-only) reproduces the admitted grid **midpoint exactly at
  59,999 / 59,999 quoted instants** (`max_abs_deviation_points = 0.0`, `agreement_fraction = 1.0`).
  A grid containing lookahead could not agree with a strictly-past reconstruction, so the
  reconstructed top of book this measurement uses is a function of past messages only;
* V2 independently re-derived `trades.csv` and `bbo_increments.csv` byte-identically
  (`d3db3cd7…`, `937b0557…` — equal to this freeze's declared input hashes).

So the admitted stream **does** support a causal OFI state at 1 s, and no proxy was substituted.

---

## 4. Coverage, and the floor declared before the run

| metric (primary horizon, 1 s) | value | floor | pass |
| --- | --- | --- | --- |
| decision slots | 599 | — | — |
| quote coverage (two-sided, uncrossed, at entry) | 0.99833 | ≥ 0.95 | ✅ |
| observation coverage (quote at entry **and** exit **and** a non-zero state) | 0.97329 | ≥ 0.75 | ✅ |
| evaluated observations | 583 (LONG 273 / SHORT 310) | ≥ 250 | ✅ |
| admitted grid coverage (from `admission.json`) | 0.99998 | contextual | ✅ |

The 16 unevaluated slots are balanced-state or edge instants, not missing quotes; they are counted
in the coverage denominators and excluded from the outcome, never imputed as zero.

Only **one instrument** exists on this slice, so the instrument-level cluster is the window itself;
the 60 s block (4× the longest horizon) is the finest declared dependence unit that leaves more than
one cluster, and the interval is reported with its cluster count (10) as a development-grade
interval. That limit is stated rather than hidden.

---

## 5. Result

```
$ .venv/bin/python -m M2.src.es_materiality run \
    --freeze M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json \
    --out    M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json
KILL_MATERIALITY  TUP-CME-ES-H3-OFI-AGG  h=1s  g=-0.0047 bps  C0=0.5770 bps  C*=-0.5817 bps  n=583
[1s=-0.0047, 5s=-0.0015, 15s=0.0503]
```

| horizon | n | gross bps | 95 % cluster interval | se | C0 bps (observed ½S round trip) | C\* bps | unconditional bps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1 s (primary)** | 583 | **−0.0047336** | [−0.0468503, +0.0403358] | 0.0222976 | **0.5770016** | **−0.5817352** | +0.0156746 |
| 5 s | 579 | −0.0014608 | [−0.0895834, +0.0807151] | 0.0443986 | 0.5776599 | −0.5791207 | +0.0631091 |
| 15 s | 569 | +0.0502825 | [−0.0435565, +0.1549833] | 0.0513751 | 0.5776521 | −0.5273696 | +0.1340817 |

Per state (reported separately, never the decision input):

| horizon | state | n | gross bps | 95 % interval |
| --- | --- | --- | --- | --- |
| 1 s | LONG | 273 | +0.0171552 | [−0.0407500, +0.0761541] |
| 1 s | SHORT | 310 | −0.0240099 | [−0.0951536, +0.0442269] |
| 5 s | LONG / SHORT | 271 / 308 | +0.0569329 / −0.0528398 | [−0.1454174, +0.2326279] / [−0.3326143, +0.1778376] |
| 15 s | LONG / SHORT | 266 / 303 | +0.1864708 / −0.0692755 | [−0.3494226, +0.6488019] / [−0.6541693, +0.4402079] |

Significance against zero: `t = −0.212` at the primary horizon — reported **only**, never a decision
input.

**Classification.** `envelope.classify_materiality` on the pooled primary figures returns
`KILL_MATERIALITY` because `g ≤ 0` (the stronger of the two kill arms; the other arm `hi ≤ C0` also
holds: `0.0403 ≤ 0.5770`). The clause is `PRIMARY_HORIZON_GROSS_NOT_POSITIVE`. The coverage gate
passed, so no `INDETERMINATE_COVERAGE` applies; and because the arm is a kill rather than a nominal
survival, the single-window rule records the boundary instead of downgrading: **scope =
`SAMPLE_SCOPED_DEVELOPMENT_KILL`, round trip required 0.5770016 bps, window
2023-07-17T13:30:00Z..2023-07-17T13:40:00Z, contract ESU3, horizon 1 s.** The verdict was computed in
both reported units (bps and USD per contract) and the two agree; a unit error would raise rather
than report.

**C0 / C\* / C1.** C0 = **0.5770016 bps** = **13.10 USD per contract** on the evaluated pairs
(mean evaluated quoted spread ≈ 1.05 ticks = 0.262 points, against 1.034 ticks for the whole
window; the reported quantity is the mean of the per-observation `1/2 S_entry + 1/2 S_exit` ratios,
not a pooled mean spread). The three declared
mandatory charges (CME exchange, CME clearing, FCM commission/routing) each carry `value = null` and
land in `C1` through `CostItem.cost_class()` with `UNRESOLVED_C1`; there is **no** verified
account-independent mandatory charge, so nothing was added to C0 and nothing was assumed to be zero.
C\* = **−0.5817352 bps = −13.207857 USD per contract**: the largest unresolved cost per round trip
at which the measured displacement vanishes, and it is negative, i.e. the candidate needs a
*subsidy* of that size. The C1 sensitivity lattice (0.25/0.5/1/2/4 × the verified one-tick value
12.50 USD — a display lattice anchored on contract economics, explicitly **not** a fee estimate, with
`distribution_assumption: NONE`) shows `survives_floor: false` at every level.

**Robustness pass.** The capture-receipt clock (`ts_recv_ns`) produces bit-identical rows at all
three horizons. That is not a code path silently doing nothing: of the 18,104 ESU3 trades, **zero**
cross a 1 s bucket boundary when moving from the venue send stamp to the capture stamp (worst
capture lag 89,153 ns), so on this slice the two availability clocks induce exactly the same state.
It is therefore an honest statement that the result is clock-insensitive *here* — and equally a
statement that it is **not** an independent clock test.

---

## 6. Limits, stated rather than hidden

* **Breadth.** One venue, one channel, one instrument, one contract month, one 10-minute RTH-open
  window, one session. The kill is a *development* kill.
* **C0 is a floor.** No exchange/clearing/FCM charge is verified; the CME fee schedule is unreachable
  from this environment and the one third-party figure found was already rejected (`P-0003`). The
  omission can only make the candidate look **better**, and it still fails.
* **Book.** The top of book is a reconstruction from in-window increments (no snapshot). V2's
  audit bounds the effect at 0.39 % of prints; the strictly-past replay above shows the reconstruction
  agrees exactly with the direct level-1 rows at every grid instant.
* **Inference.** One instrument ⇒ the instrument cluster is the window; the reported interval rests
  on 10 time blocks and is development-grade. Significance is reported and is not the criterion.
* **Sign/identity.** The state's direction convention is fixed (`x > 0` ⇒ LONG) and was never
  flipped; the failure is therefore a property of the measured mechanism, not of an unlucky sign.
  All three term-structure points and both per-state readings are reported, including the only
  positive one (15 s), so the reader can see the most favourable reading: it is still 8.7 % of C0.
* **Nothing here is survival.** Even had the numbers been positive, a single window could only have
  produced `INDETERMINATE_COVERAGE`.

---

## 7. What was deliberately not done

No `materialize.py` / `validate.py` / project-wide test suite (controller-owned, sibling-racing); no
commit; no edit to another branch's files, frozen artefacts or `M2/src/admission.py`; no MBO
requirement, feature search, horizon search, threshold tuning, sign flip, re-scope, second pass, or
any post-result change to a frozen parameter; no canonical corpus edit — the desired canonical
update is emitted as `proposal.json` (`P-0010` / `EVD-0071` proposed, `KG1_MECHANISM → FAIL`,
`overall_status → DEAD`, operator decision on whether a one-window development kill may transition
the row).

---

## 8. Summary (field order)

- **Gross magnitude** — pooled side-signed midpoint markout at the primary 1 s horizon
  **−0.0047336 bps** (5 s −0.0014608; 15 s +0.0502825); USD per contract −0.107473 / −0.033167 / +1.141626.
- **Coverage** — 583 evaluated decisions of 599 slots (LONG 273 / SHORT 310); quote coverage 0.99833,
  observation coverage 0.97329; floors ≥ 0.95 / ≥ 0.75 / ≥ 250 all passed; admitted grid coverage
  0.99998; strictly-past level-1 replay agreement 59,999/59,999 instants.
- **Confidence interval** — 95 % instrument × 60 s block cluster bootstrap [−0.0468503, +0.0403358]
  bps (se 0.0222976, 10 clusters, seed 20260717); significance t = −0.212, reported only.
- **Structural cost C0** — **0.5770016 bps** (13.10 USD per contract) = the measured observed-spread
  `1/2 S_entry + 1/2 S_exit` alone; no verified account-independent mandatory charge exists, and all
  three declared venue/clearing/FCM charges stay in **C1** with `UNKNOWN` value (never zero).
- **Break-even residual C\*** — **−0.5817352 bps** (**−13.207857 USD per contract**); the C1 lattice
  shows `survives_floor: false` at every level, and `hi ≤ C0` independently holds.
- **Decision** — **`KILL_MATERIALITY`, clause `PRIMARY_HORIZON_GROSS_NOT_POSITIVE`, scope
  `SAMPLE_SCOPED_DEVELOPMENT_KILL`** (round trip 0.5770016 bps, ESU3, 2023-07-17 13:30:00Z–13:40:00Z,
  1 s). Freeze `42a158c5…` sealed before the outcome and re-verified at run time; module
  `2a07bbd4…`; results `09c85629…`; exactly one run.
- **Blocking finding** — none. The block condition was checked positively (causal state at 1 s
  demonstrated without lookahead), and no other branch-A step was blocked.
