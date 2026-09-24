# M2 AUTONOMOUS RUN — TERMINAL REPORT

Run: M2-0.6 universe-proxy falsification · date 2026-09-23 · candidate `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG`
Git SHA at start: `515d1d35c8f5433927aaa4ed6218ee709807878f` (M2 tree carried as working-tree content; every
artifact below is pinned by its own SHA-256, recorded in
`M2/experiments/M2-0-6-UNIVPROXY/run_inputs.json`).

---

## TERMINAL STATE

**KILLED**

The aggressive/abstain form of `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` is rejected. The rejection does not
depend on any model, threshold, feature or fitted parameter: it follows from the realised future quotes
and two cost schedules.

---

## CANDIDATE

| field | value |
|---|---|
| ID | `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` |
| mechanism | top-of-book displayed queue imbalance predicts the next midpoint move |
| market / venue | Nasdaq U.S. equities, Nasdaq-only reconstructed book |
| horizon | H2, 100 ms – 1 s |
| execution | aggressive cross-in / cross-out, 100-share representative size |
| universe rule | `NASDAQ-LARGETICK-QIMB-UNIV-v1` (frozen 2026-09-20, unmodified here) |
| signal | `I(t) = (Q_bid − Q_ask) / (Q_bid + Q_ask)`, side = sign(I) |

---

## STARTING EVIDENCE

Inherited and re-verified, not assumed:

1. **M2-0** (`M2/output/M2_0_STATUS.md`): a free Nasdaq TotalView-ITCH 5.0 sample day (2019-07-30,
   282,229,684 framed messages, raw sha256 `c65784c4…`) was replayed into a deterministic causal 100 ms
   decision grid for a 61-symbol *compute scope* ranked by order-add message count. Role: DEVELOPMENT
   forever, `holdout_eligible = false`. Point-in-time universe membership: BLOCKED.
2. **M2-0.5** (`M2/output/M2_0_5_FEASIBILITY.md`): conditioned the aggressive arithmetic on a declared
   state space. Finding: no declared state is positive; the pooled signal supplies 1.76% of the required
   move at 1000 ms (T = 56.9); spread 70% and the floor fee 30% of that required move; a clairvoyant
   oracle nets +0.0129 bps per observation.
3. **Defect M2-0-D1/D2/D3** (re-verified here by reading `M2/src/calculate.py:653,663-668`): the frozen
   cross-to-cross column is half the true basis-point value (a price difference divided by `mid2`) and
   the fee lookup used `entry_price = raw/2/10000`, i.e. half the true price. Both defects push the
   reported figure in the favourable direction; M2-0.5 reported the corrected quantities and left the
   frozen artifact untouched. The markout column is unaffected because its factor of two cancels.
4. **The scope/universe mismatch that motivated this experiment.** The M2-0 compute scope is *not* a
   population in which the candidate's own universe definition holds: mean quoted spread 4.82 ticks,
   observation-weighted one-tick fraction 0.587, mean price ≈ $43, and — decisively — it contains almost
   no high-priced one-tick names (the `$200+` × one-tick cells carry about a thousand observations).
   The frozen rule requires a one-tick **median** spread and the top decile of dollar volume, i.e. the
   busiest, high-priced, most tightly quoted names. If the M2-0.5 verdict were an artifact of that
   mismatch, the correct state would have been a pivot or a paid modern-regime test, not a kill.

A classifier applied to the inherited M2-0 rows (the rule's own large-tick sentence, one day) shows
40 of the 61 inherited symbols pass the screen — but the *low-priced* ones dominate their observation
counts. This is why the pooled friction there (4.81 bps) is not the friction of the intended population.

---

## EXPERIMENTS RUN

### M2-0-6-UNIVPROXY — does the intended population rescue the aggressive branch?

* **Freeze**: `M2/experiments/M2-0-6-UNIVPROXY/freeze.json`, sha256 `4fc098a3…c32b38b`, sealed and
  hashed **before any proxy-run observation was inspected**; the hash was recomputed after the run and
  matches. The freeze contains the population definition, the sampling grid, the metrics, the
  precommitted decision rule (G1_best ≥ 5.0 **and** G1_pooled ≥ 10.0 → KILL), the corroboration rule,
  the allowed exclusions and the permitted post-result decisions.
* **Question**: in a single-day proxy of the frozen rule's own population, does aggressive monetization
  retain enough economic room to justify buying modern data, or is it structurally dead?
* **Population** (no outcome information enters either screen):
  * liquidity proxy — top 120 by same-day venue trade-tape dollar volume (order executions priced at the
    resting order, executions-with-price at their own price, non-cross trades; crosses counted, never
    priced) inside the single-day top decile computed with the rule's own primitive
    (`universe.top_decile_by_dollar_volume`); decile = 220 of 2,387 security-type-eligible names;
  * rule-conformant screen — per symbol, median quoted spread over the day's 1 s grid observations equal
    to exactly one tick **and** at least THETA = 0.50 of valid observations at one tick (the rule's own
    sentences on a one-day proxy of its 60-day lookback). **33 of the 115 replayed names pass.**
* **Run**: same replay engine, same cost ledger, same horizons and delays, 1 s decision grid (so label
  windows do not overlap and the observation set matches the M2-0.5 pass). Two feasibility runs: the
  rule-conformant population (primary) and the whole liquidity scope (corroborating).

**Result — the precommitted rule fires on both conditions, in the intended population:**

| gate | definition | threshold | observed | satisfied |
|---|---|---|---|---|
| `G1_best` | min over declared cells (≥100 obs) of required_move / signal, structural floor | ≥ 5.0 | **10.69** | yes |
| `G1_pooled` | same ratio pooled, best of the four preregistered horizons | ≥ 10.0 | **51.64** | yes |
| `G2` | ORACLE net per trade at the same horizon (downgrade rule: > 5 bps) | ≤ 5.0 to keep the kill | **0.822** (floor) / 0.219 (accessible) | no downgrade |

Machine-readable: `M2/output/univproxy/M2_0_6_VERDICT.json`.

Supporting facts from the same frozen artifacts:

| quantity | primary population (33 names) | whole liquidity scope (115 names) | inherited M2-0 scope (61 names) |
|---|---|---|---|
| pooled signal @1000 ms | 0.0794 bps | 0.0578 bps | 0.0846 bps |
| pooled required move @1000 ms | 4.1011 bps | 6.7744 bps | 4.8117 bps |
| pooled **T** @1000 ms | **51.64** | **117.30** | **56.9** |
| declared states with positive net (structural floor) | **0 of 356** | **0 of 400** | 0 of 40 (bin × horizon) |
| best state, net after structural floor | −0.975 bps/trade | −0.951 bps/trade | −4.33 bps (best bin) |
| clairvoyant ORACLE net per trade (floor / accessible fixed) | +0.822 / +0.219 bps | +1.392 / +0.793 bps | +1.36 / — |
| clairvoyant ORACLE net per observation (floor) | 0.0097 bps | 0.0114 bps | 0.0129 bps |
| QIMB bound (imbalance side + perfect abstention), pooled / best cell | 0.0052 / 0.127 bps per obs | 0.0061 / 0.088 bps per obs | 0.008 (best bin) |
| P(a trade clears its own hurdle): unconditional → best state | 0.279% → 3.94% (14.2×) | 0.235% → 4.29% (18.3×) | — |

The **scope mismatch hypothesis was tested and rejected**: the intended population shows the same
50–120× friction-to-signal gap as the scope it replaced. The population was not the explanation.

### Post-freeze diagnostics (clearly labelled; they informed interpretation, not the gate)

* **Price-band aggregation** (declared dimensions of the frozen state space): in the primary population
  the best band is `200+` at 29.8× (signal 0.0413 bps against a 1.228 bps hurdle, n = 22,373), then
  `100–200` at 34.6×, `50–100` at 45.0×, `25–50` at 39.3×, `5–25` at 586.7×. The high-price band is the
  most favourable and is still 30× short.
* **Independent re-derivation** (§31): the primary population's pooled signal (0.0794 bps), required move
  (4.1010 bps) and row count (737,768) were recomputed outside the feasibility module before reading its
  numbers. Two errors in that independent script were found and fixed during the check — a missing
  `sign(side)` on the short leg and a missing exit half-spread — which is recorded because it is the
  reason the module's numbers, and not the script's, are quoted here.
* **Regime sensitivity** (arithmetic, not a model): the measured 1 s move scale in the primary population
  is 0.847 bps (≈ 20.6% annualised). The kill's best-cell condition holds while a modern regime's move
  scale stays below ≈ 2.1× that level (≈ 43% annualised); the pooled condition holds below ≈ 5× (≈ 103%
  annualised). The rule requires both. Beyond ≈ 2.1× the best-declared-state condition would not have
  been met and the correct state would have been EXTERNAL_BLOCK rather than KILLED. Two facts bound this
  optimism: stressed regimes widen the quoted spread, so the friction in bps is not constant; and a
  larger move scale raises the clairvoyant ceiling in the same proportion while leaving the causal
  signal's share of it unchanged.

---

## DATA VALIDITY

| item | value |
|---|---|
| dataset | Nasdaq TotalView-ITCH 5.0 public sample day 2019-07-30 (`NASDAQ-ITCH50-PUBLIC-SAMPLE-20190730`), raw sha256 `c65784c4…09bc2d4a`, unchanged |
| role | DEVELOPMENT, `holdout_eligible = false`, `outcome_claim_permitted = false`; one day cannot support partitions (`NO_SPLIT_POSSIBLE_INSUFFICIENT_COVERAGE`) |
| re-ingest | independent second ingest into a separate derived root reproduced 282,229,684 messages, 8,849 directory entries, 0 backwards timestamps, 748,799 adjacent duplicates |
| replay | DATA_VALID; 29,175,488 scope book messages; 0 orphan executions/cancels/deletes/replaces; 0 crossed or locked states; 0 missing sides; 0 late label or delay resolutions; 0 scope deactivations |
| coverage | 2,691,000 / 2,691,000 grid instants two-sided (valid-book fraction 1.000) |
| reconciliations | calculate stage 23 checks / 0 failures; feasibility 9 checks / 0 failures in each run; `frozen_execution_comparison` NOT_EVALUATED by config (a run-specific re-derivation of M2-0's own columns cannot apply to a re-scoped run) |
| tests | `python -m unittest discover -s M2/tests -t .` → **99 tests, 0 failures** (84 inherited + 15 new: 10 for the proxy scan and scope path, 3 for the population subset filter, 2 for the run-specific frozen reference) |
| known exclusions | crossed/locked, missing side, non-positive denominator (the M2-0 declared set); `imbalance == 0` rows are counted and excluded from side-dependent cells |
| unresolved defects | no vendor checksum exists for the raw tape (M2-0 finding, unchanged); the product carries no sequence number, receive clock or channel id, so receive-vs-event latency and sequence audits remain non-computable; the 60-day lookback and the point-in-time reference remain unsecured, so **universe membership is still BLOCKED and is not claimed by this run** |

New defects found and recorded (not repaired — a repair would invalidate a frozen run):

* **M2-0-D4** `M2/src/book.py::select_candidates`: the `$1` price floor is tested against the *first ADD
  message of the day*, which for 762 symbols is a pre-open stub order priced at about one cent. Five of
  the 120 intended scope names (CDW, CHRW, CRWD, PCAR, SBGI) were excluded on that basis; the loss is
  reported and not compensated, and the five are mid-priced names whose absence does not favour the
  verdict. No M2-0 number changes (its own scope recorded no price-floor loss).
* **Methodology note** (not a defect): the Nasdaq-only book's touch is not the NBBO. 82 of the 115
  largest names have a median Nasdaq-book spread above one tick (FB 2 ticks, NVDA 4 ticks), so the
  frozen rule's one-tick screen selects 33 of the 115. This is the candidate's own one-venue design.

---

## SIGNAL

* The mechanism is present and weak, exactly as the literature describes: at 1000 ms the pooled
  imbalance-signed mid move is 0.0794 bps in the rule-conformant population (0.0578 bps over the whole
  liquidity scope) against an unconditional mean of ≈ 0.001 bps; the response is monotone in the
  imbalance bin (rank correlation 0.976 at 100 ms, 0.952 at 500 ms over the 115-name scope, 7 increasing
  and 2 decreasing steps of 9).
* Directional accuracy given a non-zero move rises from 62.04% to 65.72% at 100 ms and from 60.80% to
  64.61% at 1000 ms as the declared `|I|` threshold increases from 0.0 to 0.8. It is computed on the
  minority of rows that move at all: 96.0–96.7% of instants at 100 ms and 81.2–82.9% at 1000 ms have
  no mid move.
* **The signal's magnitude is the binding fact**: 0.0794 bps of expected directional move against 4.10
  bps of executed friction — 1.94% coverage. Extending the horizon from 100 ms to 1000 ms improves the
  ratio by 5.7× (T: 292.6 → 51.6) and closes none of the gap, because the required move is
  horizon-invariant: it is the tick plus the fee floor.
* Uncertainty is dependence-aware throughout: block bootstrap over symbol × 30-minute blocks, 2,000
  resamples; the best-cell standard error (0.0738 bps) is reported beside the cell's −1.3628 bps mean.

## EXECUTION

* Access path modelled: `STRUCTURAL_COST_FLOOR` (Nasdaq remove-liquidity $0.0030/share each way plus
  SEC §31 and FINRA TAF) and `ACCESSIBLE_REFERENCE_PATH` (IBKR Pro Fixed $1.00/order minimum, and IBKR
  Pro Tiered), all from the frozen ledger `M2-COST-LEDGER-v1` (sha256 `52ce785f…`) with per-line-item
  provenance. 2026 rate cards applied to a 2019 tape: this validates the arithmetic and the ordering of
  the components, it does not reconstruct 2019 economics.
* Arrival-time quotes are used for every delayed scenario; the delay grid is 0–1000 ms; the M2-0 result
  that the arithmetic is essentially flat across that grid on this tape is preserved here.
* Displayed liquidity is not the binding constraint at 100 shares, and no capacity claim is made.
* No fill or queue assumption is made anywhere: the aggressive leg is a cross at the far touch, so the
  reconstruction's touch is the executable price by construction; slippage and impact are explicitly
  excluded, which makes every number here optimistic.

## ECONOMICS

| regime | pooled net per observation (primary, 737,768 obs) | best declared state | clairvoyant net per trade |
|---|---|---|---|
| STRUCTURAL_COST_FLOOR | −4.0217 bps | −0.975 bps | +0.822 bps on 1.18% of instants |
| IBKR Pro Fixed (accessible) | −6.7618 bps | −1.431 bps | +0.219 bps on 1.18% of instants |
| IBKR Pro Tiered (accessible) | −5.6033 bps | — | +0.365 bps on 1.18% of instants |

The decomposition (an identity, reconciled to 1e-9): required move = full quoted spread paid + floor fee
= 2.5730 + 1.5281 = 4.1011 bps pooled in the primary population, against a 0.0794 bps signal — a
62.7% spread / 37.3% fee split of the hurdle, with the signal supplying 1.94% of it. (The 70/30 split
M2-0.5 reported belongs to the lower-priced scope it examined; in the rule-conformant, higher-priced
population the spread share is lower, as expected, and the verdict is unchanged.)

## ROBUSTNESS

| axis | finding |
|---|---|
| population | two independent populations agree (T 51.6 vs 56.9); a third, broader population (115 names incl. the highest-priced multi-tick names) is worse (117.3) |
| price band | the most favourable band (`200+`, mean price $208) is 29.8× short; frictions fall with price but the signal falls with them |
| latency | flat across 0–1000 ms on this tape (250 ms–1 s horizons all lose by ≥0.95 bps in the best state) |
| horizon | extending 100 ms → 1000 ms reduces T by 5.7× and still leaves 51.6× |
| cost | the structural floor is the *cheapest* achievable path; the accessible broker paths are 1.3–1.8 bps/trade worse |
| selectivity | P(clearing the hurdle) rises only from 0.279% to 3.94% across 356 declared states, and no state has positive mean net |
| clairvoyance | the ceiling itself is 0.219 bps/trade under the accessible path — 1/19th of the friction it must overcome |
| data leakage / artifact | none found; the replay, book and label machinery is the same one M2-0 validated, re-ingested independently, with 0 reconciliation failures |
| simpler explanation | the mechanism is not claimed to be absent — it is claimed to be ~50× too small to pay a tick; the pre-registered simple baselines (always-long, sign(I), fixed `|I|` thresholds) all lose by 4–5 bps per trade |

## BASELINES

* deterministic: trade every non-zero imbalance (−4.0 to −4.5 bps/trade); fixed `|I| ≥ 0.2 / 0.5 / 0.8`
  thresholds (all negative, coverage 0.72/0.39/0.17); always-long (the unconditional drift, ≈ +0.001 bps).
* the same-information selective bound: QIMB_CONSTRAINED_BOUND, which is *perfect abstention* with the
  imbalance-dictated side, is worth 0.0052 bps per observation — 0.13% of the hurdle.
* no learned baseline is fitted: there is no sealed partition and one development day, so a fitted model
  would be an in-sample number with no out-of-sample meaning. This is a deliberate omission, and it is
  also unnecessary: the ceiling that any model must beat is measured directly and is far below cost.
* Jev/System-One was not used and is not admissible here: the estimand requires a classical
  same-information policy to have established an economically credible problem first.

## FALSIFICATION ATTEMPTS

The candidate was attacked in the order that would have killed it cheapest:

1. *"The M2-0 scope is the wrong population."* — Tested by re-scoping to the rule's own population
   (top-dollar-volume ∩ one-tick median spread). **Rejected**: the intended population is not better
   (T 51.6 vs 56.9).
2. *"Some declared state is positive."* — Tested over 356 (primary) and 400 (scope) declared states.
   **Rejected**: 0 positive in either.
3. *"Selectivity rescues it."* — Tested by the hurdle-clearing probability and by the QIMB bound
   (perfect abstention). **Rejected**: the state lifts P(clear) only 14× to 3.9%, and perfect abstention
   is worth 0.13% of the hurdle.
4. *"A model could find the tail."* — Bounded by ORACLE_UPPER_BOUND, which uses future information.
   **Rejected**: perfect foresight nets 0.822 bps/trade at the structural floor and 0.219 bps/trade at
   the accessible path.
5. *"Costs are the artifact (the fee was doubled by defect D2)."* — Corrected and re-run; the corrected
   fee is *smaller* and the corrected cross-to-cross is *more* negative. **Rejected**: the verdict is
   unchanged and strictly worse for the candidate than the frozen artifact suggested.
6. *"The universe rule itself is the problem; high-priced names with a multi-tick Nasdaq book have a
   tiny friction in bps."* — Tested on the 115-name scope, which contains AMZN ($1898), GOOGL ($1230),
   BKNG ($1915), ISRG ($533), EQIX ($495) and 25 more names above $200. **Rejected**: that population's
   pooled T is 117.3 and its best cell needs 6.55×, because their quoted spreads on the Nasdaq-only book
   are wide in dollars (the `200+` band's mean spread there is 7.22 bps).

Three strong failure explanations survive all of this and are the reason for the verdict: (i) the
friction is a *tick plus a fee floor*, i.e. a lower bound that no execution improvement can go below for
a taker; (ii) the mechanism's measured information at this horizon is a small fraction of a tick, which
is what the queue-imbalance literature predicts; (iii) aggressive execution pays that tick on both legs
while the information moves the mid by ~2% of it.

## WHY THE TERMINAL STATE WAS CHOSEN

The precommitted rule was applied as written: `G1_best = 10.69 ≥ 5.0` **and** `G1_pooled = 51.64 ≥ 10.0`,
with the corroboration check satisfied (`G2 = 0.822 bps` per trade, so no downgrade). No threshold, cell,
horizon, population or cost assumption was changed after the result was seen; the two post-freeze
diagnostics are labelled and did not enter the gate.

Beyond the rule, the decision is supported by the fact that the *ceiling* — a clairvoyant trade on the
same instants, at the same costs — earns 0.219 bps per trade under the accessible path, i.e. less than a
quarter of one basis point on 1.18% of instants, while the strategy must pay a 4.10 bps hurdle to
participate at all. Prediction cannot exceed clairvoyance, and clairvoyance cannot pay.

**The economic consequence is the point**: the purchase of modern Nasdaq order-level data and a
point-in-time security master would not change this decision for this candidate. Priority 1 of the
handoff is answered negatively for the aggressive branch.

## WHAT WAS NOT ESTABLISHED

* **Universe membership**: the frozen rule's 60-trading-day lookback, 120-day history floor and
  point-in-time listing/security-type/corporate-action/halt reference remain unsecured. The population
  used here is a *single-day proxy* of two of the rule's criteria, labelled as such everywhere.
  `universe_membership.parquet` still carries `eligible = null`.
* **A modern regime**: one 2019 low-volatility session (measured move scale 0.847 bps/s ≈ 20.6%
  annualised) cannot speak for 2020–2026. The kill is robust to a regime multiplier of ~2.1× on the
  best-cell condition and ~5× on the pooled condition, and *no further*.
* **Passive execution remains untested.** Nothing here measures queue position, fill probability,
  adverse selection or cancel latency, and the mechanism itself is not falsified — only its aggressive
  monetization. A passive variant's economics turn on fill-conditioned markout, which this experiment
  cannot see. (The registered specs `PASSIVE_FILL_MODEL` and `FILL_CONDITIONED_MARKOUT` forbid
  `touch = fills` as an estimator, so a passive test requires a queue-aware fill model.)
* **Day-level dispersion, symbol-level robustness and multi-day stability** are unmeasurable on one day.
* **Capacity and broker-path economics** were not needed: the candidate fails before them.

## NEXT ACTION

**Register the passive pivot and build its fill model — or stop.**

Concretely, the one action named here: open hypothesis/candidate `TUP-NASDAQ-LARGETICK-H2-QIMB-PAS`
(passive/queue monetization of the same signal, same universe rule, *new* candidate and *new* freeze —
never a mode change on the killed row), with its first frozen experiment being the already-registered
`PASSIVE_FILL_MODEL` measurement (queue-position fill probability under Nasdaq's actual priority rules)
followed by `FILL_CONDITIONED_MARKOUT` (E[markout | fill, queue position] after costs, with an
exposure-matched random-fill null). The discriminating quantity is the sign of fill-conditioned markout:
if a resting order at the touch is adversely selected by more than the 0.0794 bps directional edge, the
mechanism family is dead for passive execution too and no data purchase is warranted. That experiment
requires an order-level replay with order-identity tracking and a shadow-fill reconciliation — it is a
build, not a measurement on hand data, and it is therefore **not** started in this run.

Explicitly **not** authorised or recommended by this run: spending money on modern Nasdaq order-level
data or a point-in-time security master *for the aggressive branch*; further threshold, horizon, feature
or universe search on the 2019 day; and any use of Jev/System-One to rescue this candidate.
