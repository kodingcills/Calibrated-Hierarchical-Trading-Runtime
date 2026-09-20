# M1 validation report

Generated (UTC): 2026-09-20T18:48:51Z by `M1/src/validate.py`.

**Overall: PASS** - 0 failure(s) across 38 rule groups.

| rule | check | rows checked | result |
|---|---|---|---|
| V1 | provenance references resolve | 1359 | PASS |
| V2 | numeric facts carry sources or are declared UNKNOWN | 536 | PASS |
| V3 | gate ceiling and dead/ALIVE integrity | 37 | PASS |
| V4 | referential integrity | 805 | PASS |
| V5 | no scoring or ranking artifacts | 526 | PASS |
| V6 | stable ids unique | 411 | PASS |
| V7 | time-sensitive sources dated | 100 | PASS |
| V9 | no unperformed experiment claims a result | 9 | PASS |
| V10 | decision-critical values remain UNKNOWN | 280 | PASS |
| V11 | cross-file consistency | 14 | PASS |
| V12 | raw provenance chain intact | 42 | PASS |
| V13 | paper cost arithmetic reproduces | 2 | PASS |
| V14 | two-dimension issue model complete | 35 | PASS |
| V15 | frontier restricted to open M1 blockers | 39 | PASS |
| V15 | frontier restricted to open M1 blockers | 39 | PASS |
| V16 | eligibility independent of non-M1 issues; every verdict rule-traced | 140 | PASS |
| V17 | patch integrity | 3 | PASS |
| V18 | work artefacts valid and complete | 72 | PASS |
| V2 | numeric facts carry sources or are declared UNKNOWN | 2 | PASS |
| V2 | numeric facts carry sources or are declared UNKNOWN | 2 | PASS |
| V1 | provenance references resolve | 1359 | PASS |
| V2 | numeric facts carry sources or are declared UNKNOWN | 536 | PASS |
| V3 | gate ceiling and dead/ALIVE integrity | 37 | PASS |
| V4 | referential integrity | 805 | PASS |
| V5 | no scoring or ranking artifacts | 526 | PASS |
| V6 | stable ids unique | 411 | PASS |
| V7 | time-sensitive sources dated | 100 | PASS |
| V9 | no unperformed experiment claims a result | 9 | PASS |
| V10 | decision-critical values remain UNKNOWN | 280 | PASS |
| V11 | cross-file consistency | 14 | PASS |
| V12 | raw provenance chain intact | 42 | PASS |
| V13 | paper cost arithmetic reproduces | 2 | PASS |
| V14 | two-dimension issue model complete | 35 | PASS |
| V15 | frontier restricted to open M1 blockers | 39 | PASS |
| V15 | frontier restricted to open M1 blockers | 39 | PASS |
| V16 | eligibility independent of non-M1 issues; every verdict rule-traced | 140 | PASS |
| V17 | patch integrity | 3 | PASS |
| V18 | work artefacts valid and complete | 72 | PASS |

## Failures

None.

## Rule set

- V1 provenance for every factual row
- V2 numeric facts carry a source or are declared UNKNOWN
- V3 gate ceiling, DEAD/ALIVE integrity, dead-ledger agreement
- V4 referential integrity across artifacts
- V5 no scoring or ranking artifact (M1-D1 not authorized)
- V6 unique stable ids
- V7 time-sensitive sources carry a date or date basis
- V9 no experiment claims a result it did not run
- V10 decision-critical values remain UNKNOWN (no imputation)
- V11 root artifacts agree with canonical artifacts and PROJECT_STATE.md
- V12 raw inputs still hash to the manifest
- V13 the candidate-architecture paper's cost arithmetic still fails to reconcile
- V14 two-dimension issue model complete and internally consistent
- V15 frontier restricted to open M1-blocking issues
- V16 gate eligibility independent of non-M1 issues; every verdict rule-traced
- V17 patch integrity: rejected patches never reach canonical state
- V18 work artefacts (cards, specs, request packets) valid and complete
