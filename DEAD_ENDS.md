# DEAD ENDS

Canonical machine-readable source: `M1/data/dead_candidates.csv`.
Imported from the M1-A dead-candidate cemetery (SRC-0011) plus the two governance and
technology admissions registered by M1-C.

Registered dead rows: 8

Re-entry policy: a dead candidate cannot re-enter silently. It requires NEW_EVIDENCE plus
an explicit resurrection decision recorded in `DECISIONS.md`. The resurrection condition
is recorded per row so the decision can be made against a stated bar rather than a memory.

## TUP-NASDAQ-LARGETICK-H2-QIMB-AGG - killed by KG3_EXECUTION

- class: TUPLE
- report kill gate (verbatim): M2 measured execution economics (no M1-A cemetery row)
- cause: Aggressive execution cannot clear the tick-plus-fee friction: a measured signal of 0.0794 bps against a 4.1011 bps round trip, with a measured clairvoyant ceiling of 0.822 bps per trade at the structural floor and 0.219 bps per trade on the accessible reference path (M2-0-6-UNIVPROXY, freeze sha256 4fc098a3...c32b38b).
- evidence: EVD-0004|EVD-0005|EVD-0012|EVD-0031|EVD-0032|EVD-0033|EVD-0034|EVD-0035|EVD-0041|EVD-0042|EVD-0064|EVD-0066|EVD-0067
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: A rule-conformant modern measurement with a pooled required/signal ratio at or below 5, which requires both a materially higher move scale and a materially higher price level for the universe's names than the measured 2019 session (M2/output/M2_AUTONOMOUS_STATUS.md).

## TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS - killed by KG2_DATA|KG4_HALF_LIFE

- class: TUPLE
- report kill gate (verbatim): Data feasibility / compute-fit boundary
- cause: Documented public book feed cadence is at least 0.5 s between pushes, which is slower than the 10-100 ms hypothesis horizon.
- evidence: EVD-0009|EVD-0043|EVD-0044|EVD-0045|EVD-0047|EVD-0059
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: A materially different authenticated/direct feed with verified sub-100 ms state information would constitute a new tuple.

## TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG - killed by KG2_DATA

- class: TUPLE
- report kill gate (verbatim): Data feasibility
- cause: The historical product is Level 1; individual queue reconstruction is impossible from that dataset alone.
- evidence: EVD-0004|EVD-0005|EVD-0031|EVD-0032|EVD-0033|EVD-0034|EVD-0035|EVD-0041|EVD-0042
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: Acquire order-level historical TotalView/ITCH or equivalent.

## TUP-METHOD-PASSIVE-TOUCHFILL - killed by KG5_FALSIFIABILITY

- class: METHOD_RULE
- report kill gate (verbatim): Execution integrity
- cause: The proposed fill rule omits queue position and adverse selection, so it cannot answer the economic question it is used to answer.
- evidence: NONE
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: A validated queue-aware simulator or shadow-fill process replaces it.

## TUP-GENERIC-CRYPTO-MICRO - killed by KG5_FALSIFIABILITY

- class: UNIVERSE_DEFINITION
- report kill gate (verbatim): Universe-definition gate
- cause: Not a valid unit of analysis: venue-specific fees, data and matching mechanics differ materially across crypto venues.
- evidence: NONE
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: Reformulate as an exact instrument x venue x horizon x mechanism x execution tuple.

## TUP-GENERIC-CME-QUEUE - killed by KG5_FALSIFIABILITY

- class: UNIVERSE_DEFINITION
- report kill gate (verbatim): Market-structure definition
- cause: CME matching processes are product-specific, so a generic queue model is unjustified.
- evidence: EVD-0001|EVD-0002|EVD-0003|EVD-0018|EVD-0060
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: Specify product/order type and implement the actual matching rule.

## TUP-SYSTEMONE-HARDCORE-ENGINE - killed by KG1_MECHANISM|KG3_EXECUTION|KG5_FALSIFIABILITY

- class: GOVERNANCE
- report kill gate (verbatim): Project admission policy
- cause: Violates the governing separation of deterministic computation/risk from probabilistic judgment; no external evidence supplies an exception.
- evidence: EVD-0023|EVD-0024|EVD-0025|EVD-0026|EVD-0027|EVD-0028|EVD-0029
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: A new governance decision plus overwhelming evidence; not an M1 trading hypothesis.

## TUP-JEV-HOSTED-LATENCY-UNMEASURED - killed by KG1_MECHANISM|KG3_EXECUTION|KG5_FALSIFIABILITY

- class: TECHNOLOGY_ADMISSION
- report kill gate (verbatim): Technology admission
- cause: Request-to-market p99 is unverified and no signal half-life is established against which to compare it.
- evidence: EVD-0023|EVD-0024|EVD-0025|EVD-0026|EVD-0027|EVD-0028|EVD-0029
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; M1-D0 computed-gate kills are dated by gate_recompute_date; a kill recorded from M2 evidence carries its experiment date in the cause text and in its evidence rows rather than in this column)
- resurrection condition: Reproducible latency profile plus a candidate-specific EV-versus-delay curve.
