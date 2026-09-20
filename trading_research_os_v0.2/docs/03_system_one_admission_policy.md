# 03 — System-One / Jev Admission Policy

## Default stance

System-One is locked out by default.

The burden of proof is:

> Given the same information, does the candidate decision model add statistically and economically meaningful value over a local simple baseline after latency, cost, calibration error, and operational risk?

## Hosted Jev

Public TypeSafe material reports end-to-end Jev latency of roughly 70–500 ms and describes the service as an API. This range is vendor reported and should not be treated as a deterministic latency budget.

### Default allowed roles
- asynchronous news/text classification,
- semantic regime annotations,
- research feature generation,
- slow-horizon event interpretation,
- nearline monitoring,
- non-critical workflow triage.

### Default prohibited roles
- sub-10 ms execution path,
- exchange routing,
- hard risk controls,
- numerical expected-utility calculation,
- position sizing arithmetic,
- time/date arithmetic,
- direct order generation.

A hosted call may enter a trading decision path only if measured p99 end-to-end decision age is comfortably below the empirical signal half-life and it still adds net economic value over local alternatives.

## Local System-One / PCD models

Local open-weight models are separate candidates. They may enter lower-latency paths if they pass:
- local p50/p95/p99 latency measurement,
- jitter testing,
- same-information baseline comparison,
- calibration/selective-risk evaluation,
- semantic perturbation testing,
- OOD/regime-shift testing,
- hardware failure/fallback testing.

## Mathematical composition

TypeSafe's own Jev 1.13 documentation says:
- keep arithmetic in code,
- numeric precision is weak,
- Score should not be used to reconstruct exact quantities,
- complex judgments should be decomposed and composed in code.

Therefore the architecture is:

`semantic/typed judgments -> numerical optimizer/policy -> hard risk -> execution`

not:

`quantitative primitives -> Jev arithmetic -> order`

## Probability and confidence policy

Do not conflate:
- Choice/Score option probabilities,
- Choice/Score `confidence` (a statistic derived from the distribution),
- Noul probability,
- empirical probability of correctness,
- expected trade return.

All are different objects.

Vendor/native scores are recorded, then evaluated locally with:
- reliability diagrams,
- log loss,
- Brier score,
- classwise calibration,
- calibration slope/intercept,
- risk-coverage curves,
- regime-conditioned diagnostics.

Candidate probability calibration methods include beta/Dirichlet/Venn-Abers/other rolling methods depending on output structure. They must be tested, not assumed.

### Conformal is not probability calibration
Adaptive/online conformal methods can help create prediction sets, coverage guarantees, or abstention policies under drift. They do not automatically turn a raw score into a calibrated posterior probability.

## Semantic stability test battery

Every candidate schema gets:
- paraphrase invariance,
- semantic negation/complement tests,
- Choice-vs-Noul representation test,
- option-order permutation,
- irrelevant-context injection,
- missing-information tests,
- adversarial/instruction injection,
- numeric-representation substitution,
- regime/OOD slices,
- model-version canaries.

Jev 1.13's official jaggedness notes explicitly warn that:
- related primitives need not obey arithmetic identities,
- literal phrasing matters,
- adversarial content can move answers,
- irrelevant context reduces accuracy.

## Error dependence

Measure:
- marginal error by question,
- pairwise and higher-order joint failures,
- common-mode failure rate,
- conditional dependence by regime,
- perturbation-induced flip rate.

Do not assume independence because outputs are parallel. Do not assume perfect dependence because they share state.

## Kill rule

If a calibrated local logistic/tree policy using the same inputs matches or beats the System-One model on sealed, execution-aware out-of-sample utility and operational reliability, remove System-One from that path.
