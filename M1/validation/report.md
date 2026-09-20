# M1 validation report

Generated (UTC): 2026-09-20T17:38:19Z by `M1/src/validate.py`.

**Overall: PASS** - 0 failure(s) across 12 rule groups.

| rule | check | rows checked | result |
|---|---|---|---|
| V1 | provenance references resolve | 1303 | PASS |
| V2 | numeric facts carry sources or are declared UNKNOWN | 508 | PASS |
| V3 | gate ceiling and dead/ALIVE integrity | 28 | PASS |
| V4 | referential integrity | 778 | PASS |
| V5 | no scoring or ranking artifacts | 456 | PASS |
| V6 | stable ids unique | 338 | PASS |
| V7 | time-sensitive sources dated | 57 | PASS |
| V9 | no unperformed experiment claims a result | 9 | PASS |
| V10 | decision-critical values remain UNKNOWN | 280 | PASS |
| V11 | cross-file consistency | 14 | PASS |
| V12 | raw provenance chain intact | 42 | PASS |
| V13 | paper cost arithmetic reproduces | 2 | PASS |

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
