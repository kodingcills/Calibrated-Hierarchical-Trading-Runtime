# 05 — Literature Review Map

The literature review is organized around unresolved mechanisms, not model brand names.

## Workstream A — Market microstructure and edge provenance
Questions:
- Which participant constraints create exploitable flow?
- What observable signatures precede returns?
- What is the information half-life?
- What limits capacity?
- How does queue position affect realized value?

Topics:
- order-flow imbalance,
- microprice,
- queue imbalance,
- adverse selection,
- informed flow,
- liquidity provision,
- forced/rebalancing/liquidation flows,
- cross-venue lead/lag,
- inventory and horizon mismatch.

## Workstream B — Predictive primitives
Compare:
- linear/logistic models,
- gradient boosting,
- temporal CNN/LSTM/Transformer/state-space models,
- LOB-specific architectures,
- multi-horizon probabilistic forecasting.

Output objects should be economically meaningful:
- return distribution,
- volatility,
- fill probability,
- adverse selection,
- regime transition,
- liquidity deterioration.

## Workstream C — Calibration and selective trading
Study:
- reliability metrics,
- beta/Dirichlet/Venn-Abers calibration,
- online/rolling calibration,
- conformal prediction,
- adaptive conformal inference,
- abstention/risk-coverage,
- regime-conditioned calibration.

Critical distinction:
`P(correct)` is not `E[net P&L]`.

## Workstream D — Regime and drift
Study:
- change-point detection,
- HMM/state-space models,
- Bayesian filtering,
- drift detectors,
- online adaptation,
- model ensembles,
- OOD detection.

## Workstream E — Execution and impact
Study:
- queue position,
- maker/taker choice,
- fill probability,
- adverse selection after fill,
- implementation shortfall,
- market impact,
- optimal execution,
- capacity.

## Workstream F — Counterfactual / off-policy evaluation
Study:
- logging-policy support,
- inverse propensity / doubly robust estimators,
- deficient support,
- historical replay limitations,
- counterfactual market simulation.

## Workstream G — Research-methodology defense
Study:
- White's Reality Check,
- data snooping,
- PBO / CSCV,
- Deflated Sharpe Ratio,
- purging and embargo,
- sealed holdouts,
- trial accounting,
- power / minimum track record length.

## Workstream H — System-One / Jev / PCD
Study:
- Jev public API behavior and jaggedness,
- RLCD claims,
- open-weight replicas,
- parallel constrained decoding,
- typed decision heads,
- calibration under task/domain shift,
- latency/jitter,
- semantic perturbation,
- incremental value over local tree/linear models.

## Seed primary sources

1. TypeSafe AI — "Introducing System One Models & Jev" (2026-09-15)
   https://typesafe.ai/blog/introducing-system-one-models-and-jev

2. TypeSafe AI docs — Introduction / primitives
   https://docs.typesafe.ai/introduction

3. TypeSafe AI — Jev 1.13 jaggedness
   https://docs.typesafe.ai/model-jaggedness/jev-1.13

4. TypeSafe AI — Confidence
   https://docs.typesafe.ai/confidence

5. Gibbs & Candès — Adaptive Conformal Inference Under Distribution Shift
   https://arxiv.org/abs/2106.00170

6. Gibbs & Candès — Conformal Inference for Online Prediction with Arbitrary Distribution Shifts
   https://jmlr.org/papers/v25/22-1218.html

7. Kull, Silva Filho, Flach — Beta calibration
   https://proceedings.mlr.press/v54/kull17a.html

8. Frey et al. — JAX-LOB
   https://arxiv.org/abs/2308.13289

9. Huang, Lehalle, Rosenbaum — Queue-Reactive model
   https://arxiv.org/abs/1312.0563

10. Giegrich, Oomen, Reisinger — LOB simulation / trade evaluation with KNN resampling
    https://arxiv.org/abs/2409.06514

11. Bailey et al. — Probability of Backtest Overfitting
    https://escholarship.org/uc/item/4w1110bb

12. Bailey & López de Prado — Deflated Sharpe Ratio
    https://doi.org/10.3905/jpm.2014.40.5.094

13. Sullivan, Timmermann, White — Data-Snooping, Technical Trading Rule Performance, and the Bootstrap
    https://doi.org/10.1111/0022-1082.00163

14. Uehara, Shi, Kallus — Review of Off-Policy Evaluation in Reinforcement Learning
    https://arxiv.org/abs/2212.06355

## Rule for literature ingestion

A paper does not become a design requirement because it is famous. For each source record:
- exact question answered,
- assumptions,
- dataset/population,
- evaluation horizon,
- what transfers to our problem,
- what does not transfer,
- reproduction status,
- contradictions with other evidence,
- unresolved questions it creates.
