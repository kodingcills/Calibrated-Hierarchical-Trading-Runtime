# 06 — Metrics, Nulls, Baselines, and Kill Criteria

## Metric stack

### Predictive
- log loss
- Brier score
- calibration intercept/slope
- ECE plus classwise/reliability plots
- ranking/AUC only when relevant
- risk-coverage / selective risk
- OOD/regime-conditioned performance

### Economic
- gross and net P&L
- expected net return per decision/trade
- turnover
- implementation shortfall
- Sharpe / Sortino with confidence context
- maximum drawdown
- expected shortfall / tail loss
- hit rate and payoff distribution
- capacity / impact curve
- geometric growth / utility where appropriate

### Execution
- fill probability
- fill latency
- partial-fill rate
- maker/taker mix
- queue-position error
- spread capture
- post-fill adverse selection
- slippage
- market impact
- p50/p95/p99 decision age
- deadline miss rate

### Research integrity
- total trials
- parent/child experiment lineage
- sealed-holdout accesses
- number of model/feature/threshold choices considered
- PBO / DSR where applicable
- regime consistency
- parameter sensitivity
- live-vs-sim residual

## Null tournament

Do not use one universal coin-flip null.

Candidate nulls:
- random direction, same timestamps,
- random timing, same exposure/holding duration,
- block/bootstrap timing preserving local dependence,
- regime-conditioned randomization,
- same alpha with random sizing,
- same alpha with naive execution,
- simple linear/tree policy,
- passive/no-trade/exposure-matched policy.

Each claimed edge source gets its own null.

## Label audit

Never assume:
`price higher at horizon` == `profitable executable trade`.

Label candidates must model the object actually monetized:
- executable return after estimated costs,
- barrier/path outcomes,
- fill-conditioned return,
- adverse-selection-adjusted return,
- expected utility.

## Economic calibration

Maintain two separate diagnostics:

1. epistemic/statistical calibration:
   `score/probability -> empirical correctness`

2. economic calibration:
   `score/probability -> empirical net return / utility`

A model can be statistically calibrated and economically destructive.

## System-One kill criteria

Remove a System-One model from a path if any of the following persists after reasonable remediation:
- no incremental net utility over a same-information LightGBM/logistic baseline,
- p99 path latency consumes the usable signal half-life,
- probability/confidence cannot be made operationally reliable on current regimes,
- semantic perturbations cause unacceptable decision instability,
- vendor/version drift breaks prior validation,
- numerical logic is being delegated to the model,
- performance depends on hidden test reuse,
- output adds no information beyond predictors already available to the optimizer.

## Strategy kill criteria

A strategy is killed or demoted if:
- mechanism cannot be stated and evidence remains purely retrospective,
- edge disappears under realistic costs,
- viable region collapses under small perturbations,
- result vanishes under mechanism-appropriate nulls,
- multiple-testing-adjusted evidence is insufficient,
- reality gap cannot be reconciled,
- live calibration or execution residuals materially exceed preregistered tolerance,
- capacity is below economically relevant deployment size,
- production behavior violates hard risk assumptions.

Numerical thresholds are hypothesis-specific and must be preregistered before the relevant evaluation.
