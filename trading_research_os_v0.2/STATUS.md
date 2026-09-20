# Current Project Status — v0.1

## Known with strong public support

- TypeSafe publicly describes Jev as a System One model using a new architecture, parallel sampler, and RLCD training.
- TypeSafe reports 70–500 ms end-to-end service latency; this is vendor-reported, not a deterministic network SLA.
- Jev questions are evaluated in parallel and independently against the same state.
- TypeSafe explicitly recommends composing complex logic in code.
- Jev 1.13's official jaggedness notes say arithmetic/counting/numeric precision and date comparison should be kept in code.
- Jev 1.13 does not guarantee structural identities across related questions/primitives.
- Adaptive conformal inference exists for online prediction under distribution shift, but it addresses coverage/prediction sets rather than directly guaranteeing calibrated posterior probabilities.
- LOB simulation/replay has multiple levels of fidelity; historical replay and interactive simulation answer different counterfactual questions.
- Backtest model selection creates material data-snooping / multiple-testing risk.

## Known unknowns

- Whether any Jev/System-One model adds incremental trading utility over same-information local tree/linear baselines.
- Whether Jev's native probabilities remain calibrated on any chosen market/regime.
- Jev's actual internal architecture, parameter count, and reproducible RLCD objective.
- Best market and horizon for this research program.
- Which structural market inefficiency will be targeted.
- Required data resolution and venue coverage.
- Real signal half-life for candidate alphas.
- Best predictive primitives and labels.
- Whether local open-weight System-One models can outperform classical meta-policies.
- How much counterfactual fidelity is required before micro-live tests.
- Capacity at economically meaningful size.

## Claims explicitly NOT accepted as facts

- "Jev is PCD internally."
- "All parallel Jev outputs are perfectly correlated because they share one latent state."
- "Conformal prediction recalibrates Jev probabilities."
- "L3 replay completely solves counterfactual execution/impact."
- "Sub-100 ms Jev is HFT-ready."
- "A calibrated directional probability implies positive expected trade value."

## Immediate research queue

1. Select candidate markets/horizons by edge mechanism and data feasibility, not model preference.
2. Build literature matrix for microstructure, execution, calibration, counterfactual evaluation, and System-One.
3. Define label families tied to executable economics.
4. Build baseline ladder before advanced models.
5. Define simulator/replay fidelity requirements for the chosen market.
6. Measure candidate signal half-lives before assigning runtime model budgets.
7. Benchmark local tree/linear/MLP meta-policies.
8. Add System-One candidates only after the same-information baseline is established.
