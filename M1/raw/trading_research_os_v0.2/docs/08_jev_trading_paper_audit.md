# 08 — Audit: "How to Build a One-Person HFT Hedge Fund on Jev"

## Status

Treat this paper as an **architecture proposal / field report**, not proof of profitable trading or independent validation of Jev.

## What the paper contributes

The paper provides a concrete candidate system:

- deterministic state engine;
- compact point-in-time market snapshot;
- six typed Jev judgments in one call;
- deterministic confidence-gated policy;
- Avellaneda–Stoikov quoting math in code;
- hard deterministic risk vetoes;
- deadline/fallback ladder;
- local calibration checks using logged state–decision–outcome triples;
- baseline comparisons.

This is valuable because it gives the Research OS a specific architecture to falsify.

## Strong architectural decisions to retain

### 1. Computation vs judgment split
All exact arithmetic remains deterministic. Semantic/fuzzy judgments are delegated to a decision model.

### 2. Causal state construction
Every field in the model state must be timestamp-valid and computed only from information available before the decision time.

### 3. Atomic question decomposition
The six-question battery decomposes regime, direction, toxicity, liquidity, quote environment, and inventory pressure rather than asking a single monolithic "should I trade?" question.

### 4. Hard risk vetoes
The model cannot override deterministic position, leverage, drawdown, stale-data, API-error, or deadline controls.

### 5. Fallback ladder
Late/unavailable model decisions degrade to deterministic behavior rather than stale inference.

## Findings that require correction before any implementation

### A. Direct Kelly sizing from Jev probability is not justified

The paper claims RLCD calibration licenses fractional Kelly sizing directly from model output and uses:

`f = c * max(0, 2p - 1)`

This is only the classic even-money binary-bet Kelly form (scaled by `c`). A market-making trade is not an even-money binary bet: returns depend on fill probability, spread capture, adverse selection, inventory, fees, path, and exit mechanics.

Required replacement:

`System-One judgment -> locally calibrated outcome model -> execution-aware return distribution -> numerical sizing/risk code`

Native Jev probabilities must never be used directly as a capital fraction.

### B. The paper contradicts itself on calibration transport

Section II presents RLCD calibration as the property that makes model probabilities usable for sizing.

Section VII then correctly states that vendor training distribution != venue/instrument/question distribution and requires calibration on operator-logged data before capital is sized.

The latter must dominate. Vendor calibration is a prior claim, not production evidence.

### C. Brier/ECE treatment is underspecified for multiclass outputs

The paper presents the binary Brier formula, while the direction question is three-way (`up/down/neutral`) and Score questions are multiclass ordinal distributions.

The calibration framework must use the appropriate multiclass/ordinal scoring rule and classwise/reliability diagnostics rather than silently applying the binary formula.

### D. Platt scaling is not a universal recalibration method

The paper proposes Platt scaling when reliability departs from the diagonal. Platt scaling is naturally binary. Choice and Score outputs require an explicitly defined multiclass/ordinal calibration method (e.g. temperature/vector/Dirichlet-style approaches, depending on validation results).

No calibration method is selected in advance; methods compete out-of-sample.

### E. The stated monthly inference cost appears internally inconsistent

The paper gives:
- Jev price: $0.042 / million input tokens;
- snapshot: approximately 240 tokens;
- continuous block-cadence operation;
- stated decision-layer cost: roughly $10–25/month.

At a 300 ms cadence for 30 days:
- calls ≈ 8.64 million;
- state tokens alone ≈ 2.07 billion;
- state-only cost ≈ $87/month at $42/billion tokens.

This ignores question/schema tokens, so it is a lower bound.

At 500 ms cadence, state-only cost is still ≈ $52/month.

Therefore the $10–25/month figure is not compatible with a 300–500 ms 24/7 cadence using the paper's own 240-token state assumption unless additional pricing/caching/token-accounting details exist.

This is not economically important by itself, but it is a useful research-integrity signal: every claimed operating number should be reproducible from logged quantities.

### F. "HFT" is rhetorically broader than the demonstrated latency class

The paper itself concedes that the institutional microsecond moat remains. Hosted Jev's vendor-reported end-to-end range is 70–500 ms.

Therefore this architecture belongs to block-cadence / subsecond-to-second market making unless empirical signal half-life demonstrates otherwise. It should not be conflated with exchange-colocated microsecond HFT.

### G. Six questions are candidates, not canonical primitives

Each question must earn its place through ablation:
- does it add information beyond deterministic/quantitative features?
- does it improve execution-aware net utility?
- is it stable under paraphrase / option order / OOD?
- does it improve over a same-information LightGBM/logistic gate?

Questions that fail are removed.

### H. Avellaneda–Stoikov is a baseline, not the production quoting law

A-S is valuable as a transparent inventory-aware quoting baseline under stylized price/arrival assumptions.

The production quoter must be selected only after comparing:
- fixed symmetric quoting;
- A-S;
- empirically fitted deterministic quoting;
- tree/ML execution-aware quoting;
- any later learned execution policy.

## Experiment decomposition

The paper's architecture should be tested as nested arms:

- A0: no-trade / passive reference
- A1: fixed symmetric quotes
- A2: deterministic Avellaneda–Stoikov
- A3: A-S + deterministic toxicity/liquidity/regime rules
- A4: A-S + same-information LightGBM meta-policy
- A5: A-S + local System-One meta-policy
- A6: A-S + hosted Jev meta-policy
- A7: each model with/without explicit abstention/calibration layer

The primary System-One estimand is:

`incremental execution-aware net utility(A5/A6 - A4)`

not raw classification accuracy.

## New assumptions entered into the assumption graph

1. The chosen market-making edge survives the full decision-to-order delay.
2. A-S remains a competitive baseline after realistic queue/adverse-selection modeling.
3. Semantic regime/toxicity judgments contain information not already represented by local quantitative features.
4. Native or locally recalibrated Jev scores remain useful under regime shift.
5. The state representation contains enough information without excess context.
6. Six parallel questions do not create harmful common-mode errors.
7. Model gating improves quote quality after accounting for opportunity cost from abstention.
8. Real fill/markout economics remain positive after fees, gas, adverse selection, and queue effects.
9. Hosted model availability/jitter does not create stale-action risk because fallback logic is enforced.
10. Any sizing rule is based on execution-aware return distributions, not semantic confidence.

## Promotion rule for this paper

This paper does not move the strategy beyond G0/G1.

It creates a registered **candidate architecture hypothesis** that becomes eligible for testing only after:
1. market/venue/horizon selection;
2. edge-mechanism selection;
3. causal data pipeline;
4. execution/replay model;
5. deterministic and tree-model baselines.

Only then does Jev enter the experiment.
