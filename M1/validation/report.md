# M1 validation report

Generated (UTC): 2026-09-24T13:33:32Z by `M1/src/validate.py`.

**Overall: PASS** - 0 failure(s) across 19 rule groups.

| rule | check | rows checked | result |
|---|---|---|---|
| V1 | provenance references resolve | 1283 | PASS |
| V2 | numeric facts carry sources or are declared UNKNOWN | 547 | PASS |
| V3 | gate ceiling and dead/ALIVE integrity | 38 | PASS |
| V4 | referential integrity | 933 | PASS |
| V5 | no scoring or ranking artifacts | 539 | PASS |
| V6 | stable ids unique | 447 | PASS |
| V7 | time-sensitive sources dated | 107 | PASS |
| V9 | no unperformed experiment claims a result | 9 | PASS |
| V10 | decision-critical values remain UNKNOWN | 290 | PASS |
| V11 | cross-file consistency | 14 | PASS |
| V12 | raw provenance chain intact | 42 | PASS |
| V13 | paper cost arithmetic reproduces | 2 | PASS |
| V14 | two-dimension issue model complete | 56 | PASS |
| V15 | frontier restricted to dispatchable M1 blockers | 63 | PASS |
| V15 | frontier restricted to open M1 blockers | 63 | PASS |
| V16 | eligibility independent of non-M1 issues; every verdict rule-traced | 145 | PASS |
| V17 | patch integrity | 8 | PASS |
| V18 | work artefacts valid and complete | 97 | PASS |
| V19 | PROJECT_STATE prose carries no stale state values | 0 | PASS |

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
- V19 PROJECT_STATE carries no stale state value outside generated blocks
