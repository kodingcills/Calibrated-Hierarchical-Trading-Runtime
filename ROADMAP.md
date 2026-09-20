# ROADMAP

Generated context: `M1/output/M1_STATE_SUMMARY.json`. Milestone vocabulary and the promotion
ladder are the project's own (`trading_research_os_v0.2/docs/02_evidence_gates.md`,
`config/evidence_gates.yaml`); no dates or effort estimates appear here, because none are derivable
from evidence.

## Where the project is

**M1 - Market x Venue x Horizon x Edge-Mechanism Selection.** Not closed.

| substage | state | why |
|---|---|---|
| M1-A evidence discovery | INCOMPLETE | 22 blocking unknowns, 8 of them resolvable only by vendor or broker contact, 10 only by measurement |
| M1-B comparative synthesis | NOT_AUTHORIZED | 0 candidates have all five gates PASS; 0 PASS on KG1, KG2, KG3, KG4 |
| M1-C materialisation | COMPLETE | 51 sources, 29 evidence records, 19 venue rows, 25 mechanisms, 28 candidate rows, validator PASS |
| M1-D0 deterministic calculation | COMPLETE | gate vectors, cost floors, feasibility verdicts, coverage counts, hard eliminations, readiness report |
| M1-D1 final comparative analysis | NOT_AUTHORIZED | no CURRENT M1-B artifact; comparison dimensions UNKNOWN |

## M1 exit condition

M1 closes when either:

- a set of 0-3 candidates survives the hard filter, Pareto analysis and sensitivity analysis with
  measured, comparable dimensions, and is exported to `M1/hypotheses/`; or
- the evidence shows that no candidate survives, in which case **M1 FAILED or M1 PARTIAL is the
  correct result** and is recorded as such.

Both outcomes are acceptable. Manufacturing a shortlist is not.

## Ordered work required to close M1

Each item is a task that changes a gate vector or closes a blocker. Ordered by decision impact, not
by convenience.

1. **Lock account-level cost schedules** for the intended broker/venue path (UNK-0001, UNK-0005,
   UNK-0028). Cheapest branch-level kill or clearance available: a verified all-in floor already
   killed two crypto tuples without any modelling.
2. **Request historical order-level data quotes and sample files** for CME and Nasdaq equity venues
   (UNK-0003, UNK-0004, UNK-0020), then validate the samples' timestamp semantics against the
   project's contract (UNK-0018, OQ-0015).
3. **Resolve citation tokens to primary URLs** and snapshot each page (UNK-0023, OQ-0001), so the
   fee and feed facts that already decided candidate deaths are independently re-derived.
4. **Lock the CME matching rule per named contract**, recording its version (UNK-0002,
   OQ-0003).
5. **Narrow each surviving branch to one exact instrument** and lock its tick/lot/matching/fee
   facts (UNK-0027, OQ-0008).
6. **Search for modern venue-specific after-cost replication and for disconfirmation** of the
   OFI/queue-imbalance/microprice mechanisms (UNK-0009, OQ-0005).
7. **Instrument a shadow path** and measure decision-to-market latency (UNK-0016, OQ-0012), then
   design the EV-versus-delay sweep (UNK-0008, OQ-0006) to replace every "next tick" assumption
   with a measured curve.
8. **Build queue-aware fill modelling and fill-conditioned markout measurement** for every passive
   or crossing candidate (UNK-0007, UNK-0019, OQ-0007).
9. **Produce the M1-B synthesis** from whatever survives steps 1-8.
10. **Then, and only then, run M1-D1** (`M1/output/M1_D1_BLOCKED.md` lists the preconditions).

## What is explicitly out of scope until M1 closes

- M2 pipeline construction, dataset versioning, sealing and label design.
- Any model choice, including local tree/neural models and System-One/Jev.
- Latency budgeting or deployment-shape decisions.
- Capital, shadow trading or any live order path.

## Longer ladder (reference, not a plan)

The research OS defines G0..G8 (`IDEA -> REGISTERED -> BASELINED -> RETROSPECTIVE -> ROBUSTNESS ->
SHADOW -> MICRO_LIVE -> SCALE_LADDER -> PRODUCTION`). Every candidate row currently sits below G1:
no candidate has a dataset version, baseline set, null set or kill criterion, because several are
not yet specified down to an exact instrument. Capability milestones beyond M1 are not scheduled
here; they become schedulable only when M1 emits a survivor set with measured dimensions.