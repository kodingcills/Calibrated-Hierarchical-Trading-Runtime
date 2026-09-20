# DEAD ENDS

Canonical machine-readable source: `M1/data/dead_candidates.csv`.
Imported from the M1-A dead-candidate cemetery (SRC-0011) plus the two governance and
technology admissions registered by M1-C.

Registered dead rows: 9

Re-entry policy: a dead candidate cannot re-enter silently. It requires NEW_EVIDENCE plus
an explicit resurrection decision recorded in `DECISIONS.md`. The resurrection condition
is recorded per row so the decision can be made against a stated bar rather than a memory.

## TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG - killed by KG3_EXECUTION

- class: TUPLE
- report kill gate (verbatim): Execution envelope
- cause: 60 bps taker per fill gives 120 bps round-trip exchange trading fees before spread/slippage/adverse selection; no venue-specific evidence establishes the required seconds-scale gross edge.
- evidence: EVD-0007|EVD-0014
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: Materially lower verified fee tier AND sealed evidence that gross conditional movement clears total costs.

## TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG - killed by KG3_EXECUTION

- class: TUPLE
- report kill gate (verbatim): Execution envelope
- cause: 0.80% taker per fill implies 1.60% round-trip before all other costs at Tier 1.
- evidence: EVD-0008
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: Different verified fee economics plus evidence of enough gross edge.

## TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS - killed by KG2_DATA|KG4_HALF_LIFE

- class: TUPLE
- report kill gate (verbatim): Data feasibility / compute-fit boundary
- cause: Documented public book feed cadence is at least 0.5 s between pushes, which is slower than the 10-100 ms hypothesis horizon.
- evidence: EVD-0009
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: A materially different authenticated/direct feed with verified sub-100 ms state information would constitute a new tuple.

## TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG - killed by KG2_DATA

- class: TUPLE
- report kill gate (verbatim): Data feasibility
- cause: The historical product is Level 1; individual queue reconstruction is impossible from that dataset alone.
- evidence: EVD-0004|EVD-0005|EVD-0031|EVD-0032|EVD-0033|EVD-0034|EVD-0035|EVD-0041|EVD-0042
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: Acquire order-level historical TotalView/ITCH or equivalent.

## TUP-METHOD-PASSIVE-TOUCHFILL - killed by KG5_FALSIFIABILITY

- class: METHOD_RULE
- report kill gate (verbatim): Execution integrity
- cause: The proposed fill rule omits queue position and adverse selection, so it cannot answer the economic question it is used to answer.
- evidence: NONE
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: A validated queue-aware simulator or shadow-fill process replaces it.

## TUP-GENERIC-CRYPTO-MICRO - killed by KG5_FALSIFIABILITY

- class: UNIVERSE_DEFINITION
- report kill gate (verbatim): Universe-definition gate
- cause: Not a valid unit of analysis: venue-specific fees, data and matching mechanics differ materially across crypto venues.
- evidence: NONE
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: Reformulate as an exact instrument x venue x horizon x mechanism x execution tuple.

## TUP-GENERIC-CME-QUEUE - killed by KG5_FALSIFIABILITY

- class: UNIVERSE_DEFINITION
- report kill gate (verbatim): Market-structure definition
- cause: CME matching processes are product-specific, so a generic queue model is unjustified.
- evidence: EVD-0001|EVD-0002|EVD-0003|EVD-0018
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: Specify product/order type and implement the actual matching rule.

## TUP-SYSTEMONE-HARDCORE-ENGINE - killed by KG1_MECHANISM|KG3_EXECUTION|KG5_FALSIFIABILITY

- class: GOVERNANCE
- report kill gate (verbatim): Project admission policy
- cause: Violates the governing separation of deterministic computation/risk from probabilistic judgment; no external evidence supplies an exception.
- evidence: EVD-0023|EVD-0024|EVD-0025|EVD-0026|EVD-0027|EVD-0028|EVD-0029
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: A new governance decision plus overwhelming evidence; not an M1 trading hypothesis.

## TUP-JEV-HOSTED-LATENCY-UNMEASURED - killed by KG1_MECHANISM|KG3_EXECUTION|KG5_FALSIFIABILITY

- class: TECHNOLOGY_ADMISSION
- report kill gate (verbatim): Technology admission
- cause: Request-to-market p99 is unverified and no signal half-life is established against which to compare it.
- evidence: EVD-0023|EVD-0024|EVD-0025|EVD-0026|EVD-0027|EVD-0028|EVD-0029
- death date: 2026-09-20 (date of the M1-A artifact (SRC-0011) for the original kills; computed-gate kills are dated by gate_recompute_date)
- resurrection condition: Reproducible latency profile plus a candidate-specific EV-versus-delay curve.
