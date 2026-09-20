# Trading Research OS v0.1

A research and falsification system for developing a calibrated hierarchical trading runtime without confusing novelty, model sophistication, or backtest performance with tradable edge.

## Prime directive

> Maximize robust net economic edge. Every model, feature, architecture, and "AI" component must earn its place against simpler baselines using the same information.

The system separates:

1. **Research control plane** — offline/nearline evidence, hypothesis registration, validation, stress testing, calibration, simulation, and promotion decisions.
2. **Trading runtime** — the smallest compiled set of approved models, thresholds, risk constraints, and fallbacks. The research bureaucracy never runs in the order path.

## Non-negotiable architectural defaults

- Hosted Jev is **barred from sub-10 ms execution/routing paths by default**.
- Jev/System-One models do **not** perform arithmetic, expected-utility calculation, sizing, or hard risk logic.
- Vendor-reported probabilities/confidence are treated as **untrusted scores until locally validated**.
- Conformal prediction is treated as a coverage / prediction-set / selective-inference tool, **not as probability calibration**.
- Historical L3 replay is not assumed to model endogenous market impact from counterfactual orders.
- X/Twitter posts are **lead generation**, not evidence, until linked claims are verified against code, data, papers, or reproducible results.
- A local LightGBM/XGBoost/logistic baseline gets the same inputs as any System-One meta-policy.
- If a simpler model matches or beats System-One on sealed, execution-aware out-of-sample utility, System-One is removed from that path.

## Research lifecycle

`IDEA -> REGISTERED -> BASELINED -> RETROSPECTIVE -> ROBUSTNESS -> SHADOW -> MICRO_LIVE -> SCALE_LADDER -> PRODUCTION`

Every state has explicit evidence requirements and kill exits.

## Repository map

- `docs/00_research_charter.md` — objective, epistemic rules, and research lanes.
- `docs/01_assumption_graph.md` — how hidden assumptions are exposed and tested.
- `docs/02_evidence_gates.md` — promotion state machine and capital gates.
- `docs/03_system_one_admission_policy.md` — when Jev/PCD/local decision models are allowed.
- `docs/04_simulation_reality_gap.md` — replay/simulation/live ladder and reality-gap decomposition.
- `docs/05_literature_review_map.md` — literature workstreams and primary sources.
- `docs/06_metrics_and_kill_criteria.md` — metrics, nulls, baselines, and falsification rules.
- `docs/07_monitoring_and_source_policy.md` — fast-moving Jev/System-One monitoring policy.
- `docs/08_jev_trading_paper_audit.md` — line-by-line architectural audit of the Jev trading field report.
- `STATUS.md` — current knowns, unknowns, and next research questions.
- `templates/*.csv` — registries for assumptions, hypotheses, experiments, evidence, surprises, etc.
- `config/evidence_gates.yaml` — machine-readable gate definitions.
- `schemas/*.schema.json` — structured record contracts.
- `src/researchos.py` — zero-dependency CLI to validate registries and summarize status.

## First use

1. Register the economic thesis in `templates/hypotheses.csv`.
2. Decompose every arrow from market state -> forecast -> decision -> execution -> P&L into `templates/assumptions.csv`.
3. Register the simplest baselines before any advanced model.
4. Create immutable dataset/version identifiers.
5. Preregister the first experiment and kill criteria.
6. Run `python src/researchos.py validate`.
7. Do not open a sealed holdout without recording the access in the experiment ledger.

This repository is deliberately architecture-agnostic. Jev, PCD, RL, transformers, tree models, and handcrafted rules are candidates, not commitments.
