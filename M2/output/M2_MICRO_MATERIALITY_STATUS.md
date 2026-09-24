# M2-2 — MICROPRICE ECONOMIC-MATERIALITY GATE

Candidate `TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG` · experiment `M2-2-MICRO-MATERIALITY` · parent
`M2-0-6-UNIVPROXY` · development sample day `2019-07-30` · dataset `NASDAQ-ITCH50-PUBLIC-SAMPLE-20190730`
(raw sha256 `c65784c4…`, DEVELOPMENT, holdout-ineligible) · cost ledger `M2-COST-LEDGER-v1` ·
contract `M2/experiments/M2-2-MICRO-MATERIALITY/freeze.json`, sha256 `89f84b29…`, sealed before any
canonical economics were inspected.

**No data was acquired, no model was trained, no threshold or horizon was selected on an outcome, no
queue/fill/impact model was built, Jev was not used, and no M1 artifact or earlier M2 artifact was
rewritten.** This pass measures one thing: the realized predictive magnitude of the registered
microprice signal against the friction the same candidate would pay.

```text
TERMINAL STATE: KILLED

DATA
2019-07-30 Nasdaq TotalView-ITCH DEVELOPMENT tape
population: rule-conformant large-tick proxy subset (33 Nasdaq-listed names, one-tick median
            Nasdaq book spread, top-decile dollar volume), the same population M2-0.6 measured
observations: 772,200 decision instants (1 s grid, 09:30:00-16:00:00)
              of which 760,010 (98.42%) carry a causal microprice estimate
              of which 726,943 (94.14%) have a defined microprice DIRECTION
              next-mid-change calibration target resolved within 60 s on 99.28% of instants

MICROPRICE  (Stoikov first step, expanding prior-session calibration)

pooled, by horizon (side = sign(microprice - mid); bps of the arrival mid):
  100 ms  +0.0130   R = 307.26
  250 ms  +0.0266   R = 149.80
  500 ms  +0.0450   R =  88.65
  1000 ms +0.0745   R =  53.60
  2000 ms +0.1153   R =  34.61
  5000 ms +0.1772   R =  22.51
 10000 ms +0.2194   R =  18.17
 15000 ms +0.2333   R =  17.09   <- best preregistered horizon
pooled best horizon:
signal = 0.2333 bps   (95% block-bootstrap CI [0.2142, 0.2530])

best preregistered state ([0.8,1.0] | ONE_TICK, 15000 ms):
signal = 0.5836 bps   (95% CI [0.4842, 0.6831])
coverage = 2.98% of the direction-defined observations (21,653 instants)
R_best   = 5.015      (met by 0.3% of the frozen 5.0 bar; the CI implies R in [4.28, 6.04])
strongest magnitude band (|g1|/spread >= 0.20, 15000 ms): signal = 0.4403 bps, R = 7.32 (18.2%)

AGGRESSIVE STRUCTURAL HURDLE

round trip = 3.9875 bps at 15000 ms (3.9901 bps at 1000 ms)
          = quoted spread paid + STRUCTURAL_COST_FLOOR round-trip fee, 100-share representative
            order, recomputed on this pass's own observation set with the M2-0.6 arithmetic
cross-check: M2-0.6's all-instant figure at 1000 ms is 4.1011 bps; the 0.111 bps difference is the
5.86% of instants the causal estimator cannot yet price (the session's first 5-minute block), and it
moves the hurdle in the candidate's FAVOUR.

MATERIALITY

R_best   = 5.02
R_pooled = 17.09

ORACLE  (clairvoyant aggressive round trip, same entry/exit definition, same structural floor)

at 15000 ms: net EV / observation = +0.3176 bps
             net EV / trade       = +1.6275 bps at the structural floor
                                  = +0.7012 bps on the accessible broker path
             coverage             = 19.51% of instants
oracle / hurdle at the primary horizon = 0.0796, below the frozen 0.25 contradiction bar
by horizon the ceiling grows but never clears the friction: 1000 ms +0.8215 bps/trade (1.18%),
5000 ms +1.1332 (6.99%), 10000 ms +1.3952 (13.75%), 15000 ms +1.6275 (19.51%); at the floor, the
best possible trader on these instants never captures half of one structural round trip.

COMPARISON

QIMB  signal = 0.0794 bps   (M2-0.6, same population, 1000 ms, R = 51.64)
MICRO signal = 0.0745 bps   (same population, 1000 ms, R = 53.60)  -> uplift 0.94x
MICRO signal = 0.2333 bps   (best horizon, 15000 ms, R = 17.09)    -> uplift 2.94x vs QIMB at 1 s
best declared state: QIMB R = 10.69 (M2-0.6) vs MICRO R = 5.02 (this pass) - the selective state is
materially closer to its hurdle, and still 5x short.

DECISION

Microprice is 5.0x too small in its strongest preregistered state and 17.1x too small pooled, at the
longest horizon the candidate itself declares. The clairvoyant ceiling is the binding fact: even with
perfect foresight of the future executable quotes the aggressive round trip nets 1.63 bps per trade at
the structural floor (0.70 bps on the accessible path) against a 3.99 bps hurdle, so no predictor can
rescue this candidate on these observations. No execution model, no modern-data purchase, no ML, no
Jev and no passive pivot is justified for this candidate.

NEXT ACTION

Return to candidate selection. Do not test the next Nasdaq top-of-book row by adjacency: re-rank the
remaining WEAK and UNKNOWN candidates by expected decision value per unit research cost, preferring
mechanisms whose natural payoff scale can survive realistic friction.
```

## What was measured, exactly

**The registered estimator (§4).** The candidate's mechanism is the Stoikov micro-price — a
mid-price adjusted by the *expected* mid-price move conditional on the top-of-book state — not the
weighted mid-price (`I·P_ask + (1−I)·P_bid`), which has no calibration, and not raw queue
imbalance. Reconstructed from the mechanism's own source material (Stoikov 2018,
doi 10.1080/14697688.2018.1489139, `SRC-0239`; the author's framework slides give the operative
theorem):

```text
p_micro(t) = lim p_i,   p_i = E[M(tau_i) | F_t],   F_t = (M_t, I_t, S_t)
first step:  p_1 = M_t + g1(I_t, S_t)
             g1(I,S) = E[ M(tau_1) - M_t | I_t = I, S_t = S ],  tau_1 = first mid-price change
```

**Implemented form.** `g1` is estimated in exact integer `mid2 = best_bid + best_ask` units (twice
the price move) so that `abs(g1)/spread_raw` is *exactly* `abs(microprice − mid)/half_spread`. The
state is the candidate's own declared 10 imbalance bins × 2 spread classes = 20 cells. Only the first
step is computed: the higher-order Stoikov terms change the *size* of the adjustment but not its
sign, and the gate's primary quantity depends on the estimator through the sign alone
(`side_t = sign(D_t)`), so the pooled and best-state results are unchanged by a converged
micro-price. The omission is stated rather than hidden, and the whole-day *in-sample* refit is
reported below as the bound it implies.

**Causality (§6).** One rule, frozen before the result: an expanding prior-session window, refitted
on a fixed 5-minute cadence, requiring 200 prior resolved observations in the cell. The estimate
attached to an instant uses only strictly earlier session data; the whole-day estimator is labelled
`optimistic_full_day_estimator` and can never be presented as causal performance.
`sign_agreement_with_imbalance` = 94.85%, i.e. 5.15% of instants the calibrated direction disagrees
with the imbalance sign — this is the only way the estimator differs in *direction* from the queue
imbalance row that M2-0.6 killed.

**The optimistic (non-causal) bound, for reference only.**

| horizon ms | in-sample signal bps | R |
|---|---|---|
| 1000 | +0.0794 | 51.64 |
| 15000 | +0.2520 | 16.25 |

The in-sample refit buys 8.0% more signal than the causal rule at 15 s and reproduces the QIMB
pooled figure at 1 s to four decimals. Causality is therefore *not* what holds this candidate back;
the friction is.

**Signal-strength states (§9).** Frozen before the result: five bands on `abs(microprice − mid) /
half_spread` with edges `[0.00, 0.02, 0.05, 0.10, 0.20]`, last band open-ended; plus the 20
`(imbalance bin × spread class)` cells. A state is eligible as "best" only with at least 10,000
evaluated observations.

| band (15000 ms) | observations | signal bps | hurdle bps | R |
|---|---|---|---|---|
| < 0.02 | 361,596 | +0.2067 | 4.3057 | 20.83 |
| 0.02 – 0.05 | 42,227 | +0.0941 | 4.6477 | 49.38 |
| 0.05 – 0.10 | 93,462 | +0.1172 | 4.1067 | 35.03 |
| 0.10 – 0.20 | 96,989 | +0.2227 | 3.4404 | 15.45 |
| >= 0.20 | 132,214 | +0.4403 | 3.2236 | 7.32 |

| cell (15000 ms, top four by R) | observations | signal bps | R |
|---|---|---|---|
| `[0.8,1.0]` \| ONE_TICK | 21,653 | +0.5836 | 5.02 |
| `[-1.0,-0.8)` \| ONE_TICK | 17,470 | +0.5851 | 5.28 |
| `[0.6,0.8)` \| ONE_TICK | 46,486 | +0.4735 | 6.82 |
| `[-0.8,-0.6)` \| ONE_TICK | 43,822 | +0.4392 | 7.79 |

**The corroborating population** (the full 115-name liquidity scope, reported separately and never
pooled with the primary) gives the same terminal state on the same rule: pooled best horizon 15 s at
+0.1999 bps against a 6.4942 bps hurdle (R = 32.48), best eligible cell `[-1.0,-0.8)` | ONE_TICK at
15 s (R = 5.22), oracle/hurdle ratio 0.0601 — `KILLED`.

## Reading the margin honestly

`R_best = 5.015` clears the frozen bar by 0.3%, and the same cell's 95% bootstrap interval on the
signal ([0.4842, 0.6831] bps) implies `R_best ∈ [4.28, 6.04]`. The best-state clause is therefore met
at the point estimate and **not** resolved by this sample at conventional confidence. Two things
follow, and neither is hedged:

1. The kill does not depend on that clause. `R_pooled = 17.09` clears its own bar by 71%, and the
   clairvoyant ceiling — which contains no estimator, no calibration and no mapping choice — leaves
   +1.63 bps per trade at the structural floor and +0.70 bps on the accessible path against a
   3.99 bps round trip. Perfect foresight cannot clear this friction, so no signal mapping can.
2. The honest statement of the best-state result is "5.0× too small, measured to a precision of
   about ±20%", not "5.0× too small exactly". Even the most favourable reading in the interval
   (R = 4.28) is not "genuinely comparable economic magnitude": the candidate's own strongest corner
   still needs its signal to be four times larger.

The one number that *is* decisive is the pooled one, and it is decisive in the direction that
matters: at the longest horizon the candidate declares, the signal supplies 5.9% of the structural
round trip. The horizon term structure shows why extending the horizon does not rescue it — the
signal grows 18× from 100 ms to 15 s while the hurdle is horizon-invariant, and the growth is
already flat (10 s → 15 s adds 0.014 bps).

## What this does not say

- Not a claim that microprice carries no information: at 15 s it predicts a real +0.233 bps of
  mid drift (CI [0.214, 0.253]), roughly 3× the queue-imbalance response measured at 1 s. The
  information is present and weak, exactly as `EVD-0014` claims; it is not executable.
- Not a current-market claim. One 2019 low-volatility session, a single-day proxy of the universe
  rule rather than membership, 2026 rate cards applied to a 2019 tape for arithmetic validation.
- Not a claim about a passive formulation, an inventory/market-making formulation, a queue-aware
  fill model, or any learned predictor of the same state — none of those was built or tested here,
  and none is authorised by this result. The mechanism's *passive* form on this population is
  already dead for its own structural reason (M2-1, `EVD-0069`).
- Not a re-derivation of the M2-0, M2-0.5, M2-0.6 or M2-1 measurements; those artifacts are
  untouched.

## Reproduction

```bash
python3 -m M2.src.ingest --config M2/config/nasdaq_micro_m2_2.yaml
python3 -m M2.src.book   --config M2/config/nasdaq_micro_m2_2.yaml
python3 -m M2.src.micro  --config M2/config/nasdaq_micro_m2_2.yaml
python3 -m M2.src.micro  --config M2/config/nasdaq_micro_m2_2.yaml --corroborating
python3 -m unittest M2.tests.test_micro
```

Artifacts: `M2/output/micro/calculations/micro_materiality.json` (primary),
`…/micro_verdict.json`, `…/micro_signal_by_horizon.csv`, `…/micro_signal_by_strength_band.csv`,
`…/micro_signal_by_imbalance_spread_cell.csv`, `…/micro_oracle_ceiling.csv`,
`…/micro_signal_optimistic_by_horizon.csv`, `…/calculation_status.json`; the corroborating scope
under `M2/output/micro/calculations_liquidity_scope/`; inputs and code hashes in
`M2/experiments/M2-2-MICRO-MATERIALITY/run_inputs.json`.
