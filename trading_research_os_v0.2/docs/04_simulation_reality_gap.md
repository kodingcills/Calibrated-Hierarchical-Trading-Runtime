# 04 — Simulation and the Reality Gap

## Simulation ladder

### S0 — Feature/backtest replay
Validates: signal definitions, labels, simple economics.
Cannot validate: queue, real fills, impact, live latency.

### S1 — L2 event replay
Validates: spread/depth context and coarse passive/aggressive execution assumptions.
Cannot fully validate: individual queue priority or hidden order behavior.

### S2 — L3 queue reconstruction/replay
Validates: richer order-level queue mechanics where the feed permits reconstruction.
Cannot automatically validate: endogenous market response to orders that did not historically exist.

### S3 — Interactive counterfactual LOB simulator
Examples of research directions include queue-reactive models, JAX-LOB environments, and resampling-based simulators.
Validates: policy/environment interaction under the simulator's assumptions.
Risk: simulator misspecification and reward hacking.

### S4 — Live shadow
Validates: live data, signal timing, inference jitter, calibration drift.
Cannot validate: real execution.

### S5 — Micro-live
Validates: actual order acknowledgements, fills, partial fills, adverse selection, operational behavior.
Cannot be linearly extrapolated to large orders.

### S6 — Scale ladder
Validates: impact, capacity, fill degradation, portfolio/risk interactions.

## Reality-gap decomposition

For every live/replay discrepancy, decompose:

`ΔP&L = Δdata + Δfeature + Δforecast + Δcalibration + Δpolicy + Δlatency + Δqueue + Δfill + Δslippage + Δimpact + Δfees + Δposition + Δexit + residual`

The unexplained residual becomes a blind-spot candidate.

## Event timestamps

Log at minimum:
- source/exchange event time,
- receive time,
- feature-complete time,
- model start,
- model end,
- decision time,
- order submit,
- broker/exchange acknowledgment,
- first fill,
- last fill,
- cancel submit/ack,
- exit decision and fills.

## Signal half-life

For every candidate alpha, estimate net edge as a function of delay:

`EV(delay)`

The relevant model metric is not "80 ms inference" but "net edge remaining after the full p99 decision-to-market delay."

Measure p50/p95/p99 plus jitter and deadline miss rate.

## L3 caution

Historical L3 replay is extremely useful for queue/fill reconstruction under a small-participant/no-impact approximation. It is not a complete counterfactual market model. If our order would materially change the book or other agents' behavior, historical replay cannot reveal the resulting path because that path never occurred.

Use interactive simulation and incremental live scaling to estimate that region.
