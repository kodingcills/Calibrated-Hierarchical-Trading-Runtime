# 02 — Evidence Gates

## Lifecycle

### G0 — IDEA
A mechanism or opportunity has been noticed.

Exit to REGISTERED requires:
- one-sentence economic mechanism,
- target market/horizon,
- what would make it false.

### G1 — REGISTERED
The hypothesis exists before results are observed.

Requires:
- primary outcome,
- baselines,
- null suite,
- dataset/version,
- planned split,
- allowed degrees of freedom,
- kill criteria.

### G2 — BASELINED
The hypothesis beats or fails to beat intentionally simple competitors.

Minimum baseline ladder:
1. no-trade / passive / exposure-matched baseline,
2. random-side or random-timing null as applicable,
3. linear/logistic model,
4. tree model (LightGBM/XGBoost/CatBoost),
5. simple hand-authored policy.

No advanced architecture proceeds merely because it beats a coin flip.

### G3 — RETROSPECTIVE
Historical evidence exists without obvious leakage.

Requires:
- point-in-time feature audit,
- label overlap audit,
- purged/walk-forward validation where applicable,
- transaction-cost assumptions,
- number of research trials recorded,
- no use of sealed holdout for tuning.

### G4 — ROBUSTNESS
The edge has a region of viability rather than a single parameter point.

Requires surfaces over:
- latency,
- spread,
- fees,
- slippage,
- depth,
- missing data,
- regime,
- threshold,
- holding period,
- model version,
- calibration method.

Also requires:
- mechanism-specific null tournament,
- DSR/PBO or other multiple-testing controls where appropriate,
- parameter stability,
- regime breakdown.

### G5 — SHADOW
Live data drives the system but no market-impacting order is required.

Validates:
- data timeliness,
- feature parity,
- decision age,
- model/runtime reliability,
- live calibration,
- live signal decay.

Does not validate real fills or own impact.

### G6 — MICRO_LIVE
Small real orders validate execution assumptions.

Measures:
- exchange/broker timestamps,
- queue/fill behavior,
- implementation shortfall,
- adverse selection,
- partial fills,
- operational failure modes.

Small size is not assumed to extrapolate linearly to larger size.

### G7 — SCALE_LADDER
Capital increases gradually.

Each step estimates:
- realized impact,
- fill degradation,
- capacity,
- concentration,
- portfolio interactions,
- live drawdown behavior.

### G8 — PRODUCTION
Production is conditional, not permanent.

Automatic demotion triggers include:
- calibration failure,
- reality-gap expansion,
- drift/OOD alarms,
- execution deterioration,
- risk-limit violation,
- mechanism evidence weakening,
- model/vendor version change without validation.

## Fast research without bureaucratic runtime latency

Research rigor and execution latency are orthogonal. Gate computation occurs offline/nearline. Production consumes a minimal deployment manifest.

No "14-layer control plane" is evaluated synchronously before an order.
