# 00 — Research Charter

## Objective

The project exists to discover and monetize **robust net trading edge**, not to demonstrate AI capability.

The economic target is:

`net edge = gross predictive/execution edge - spread - fees - slippage - impact - adverse selection - financing/funding`

A model can be directionally accurate, calibrated, novel, or fast and still have negative economic value.

## Epistemic rule

A trading strategy is a chain of claims:

`inefficiency -> observable state -> forecast -> decision -> execution -> realized P&L -> persistence`

Every arrow is an assumption. Every assumption must have:

- a mechanism,
- observable evidence,
- a falsifier,
- a test,
- uncertainty,
- and a status.

The system is designed so blind spots are forced to leave measurable residuals.

## Two research lanes

### Lane D — Rapid Discovery

Purpose: cheaply kill weak ideas.

Allowed:
- exploratory analysis,
- small retrospective slices,
- coarse simulation,
- weak labels,
- broad architecture comparison.

Not allowed:
- claims of robust alpha,
- final parameter selection,
- promotion to meaningful capital,
- repeated peeking at the sealed test set.

Output: a registered hypothesis worth deeper testing, or a killed idea.

### Lane P — Capital Promotion

Purpose: decide whether an idea may receive capital.

Requires:
- preregistered hypothesis,
- mechanism-specific nulls,
- simple baselines,
- point-in-time data lineage,
- leakage-aware validation,
- execution-aware economics,
- uncertainty/calibration diagnostics,
- stress surfaces,
- sealed out-of-sample evidence,
- shadow or micro-live reconciliation,
- explicit kill criteria.

High-decay alpha is not exempt from rigor. Instead, evidence can accumulate under tightly bounded capital while risk limits prevent a research mistake from becoming a catastrophic one.

## Source hierarchy

Two separate dimensions are recorded.

### Provenance
- `primary_official` — paper, official docs, repository, exchange specification, raw data.
- `independent_reproduction` — external reproduction using disclosed method/data.
- `secondary_analysis` — technical summary/review.
- `social_lead` — X/Reddit/Discord post that points to something worth checking.

### Evidence state
- `claim_only`
- `code_available`
- `data_available`
- `reproduced`
- `independently_reproduced`
- `peer_reviewed`
- `live_observed`

A primary source can still be only a self-reported claim. "Official" does not mean "independently verified."

## Research behavior

- Search deeper whenever a mechanism is unclear or a source conflicts with another.
- Do not replace missing evidence with plausible prose.
- Record unresolved gaps explicitly.
- Search for disconfirming evidence before promoting an idea.
- Treat surprise as an error signal in the mental model.
- Treat architecture novelty as a cost until incremental economic value is demonstrated.

## Separation of control plane and runtime

The Epistemic Control Plane is **not** a runtime dependency.

It produces a signed research artifact containing:
- approved model versions,
- feature contracts,
- calibration artifacts,
- decision thresholds,
- maximum decision age,
- risk limits,
- fallback policy,
- kill switches,
- and deployment scope.

The live runtime loads this artifact. It does not run literature review, PBO analysis, or evidence ledgers in the order path.
