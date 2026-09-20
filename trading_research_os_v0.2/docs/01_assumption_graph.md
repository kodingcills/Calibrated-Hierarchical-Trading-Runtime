# 01 — Assumption Graph

## Purpose

Unknown unknowns are exposed by decomposing the strategy into transitions and forcing each transition to state what must be true.

## Canonical graph

`market mechanism`
-> `observable information exists`
-> `data captures it point-in-time`
-> `features preserve it`
-> `label represents executable economics`
-> `predictor generalizes`
-> `uncertainty is usable`
-> `policy adds value`
-> `signal survives latency`
-> `execution realizes the edge`
-> `risk/sizing preserves utility`
-> `market impact stays tolerable`
-> `edge persists under adaptation/competition`

## Assumption classes

- economic mechanism
- observability
- data integrity
- timing / point-in-time availability
- label validity
- statistical identification
- model generalization
- calibration / uncertainty
- regime / distribution shift
- policy composition
- latency / signal half-life
- execution / fill
- queue position
- market impact
- capacity
- portfolio interaction
- operational reliability
- external/vendor dependency

## Required fields

Each assumption receives:
- `assumption_id`
- `parent_hypothesis_id`
- `statement`
- `class`
- `why_required`
- `current_evidence`
- `confidence_state` (`unknown`, `weak`, `moderate`, `strong`, `falsified`)
- `falsifier`
- `test`
- `observable_residual`
- `owner`
- `last_reviewed`
- `status`

## Blind-spot derivation procedures

### 1. Inversion
Define the perfect realized trade and work backward. Ask what must be true at each transition.

### 2. Premortem
Assume the strategy lost money despite a strong backtest. Generate failure mechanisms, then map each to an assumption class.

### 3. Residual analysis
For every stage, define a residual:
- forecast residual,
- calibration residual,
- decision residual,
- fill residual,
- latency residual,
- implementation shortfall,
- impact residual,
- live-vs-sim residual.

Unexplained persistent residuals are blind-spot candidates.

### 4. Counterfactual attack
Ask what would have happened under:
- opposite side,
- random side,
- random timing,
- no trade,
- naive sizing,
- naive execution,
- simpler model,
- different regime,
- delayed execution.

### 5. Surprise ledger
Every meaningful mismatch between predicted and observed behavior is registered and clustered. Repeated surprises indicate a missing assumption.

## Important correction: deterministic models still have measurable error dependence

A deterministic System-One model can produce deterministic outputs for a fixed input while still exhibiting correlated errors across a dataset. Determinism does not imply perfect error correlation across separate questions.

Therefore evaluate both:
1. empirical joint error behavior across observations/regimes; and
2. adversarial semantic perturbation stability.

Because Jev's underlying architecture is unpublished, claims about a "single collapsed attention state" are not treated as facts.
