# ROADMAP

Generated context: `M1/output/M1_STATE_SUMMARY.json`. Milestone vocabulary and the promotion
ladder are the project's own (`trading_research_os_v0.2/docs/02_evidence_gates.md`,
`config/evidence_gates.yaml`); exact volatile counts are canonical in generated artifacts.

## Where the project is

**M1 - Market x Venue x Horizon x Edge-Mechanism Selection.** Not closed.

| substage | state | why |
|---|---|---|
| M1-A evidence discovery | INCOMPLETE | canonical blocker state is generated in `M1/output/M1_STATE_SUMMARY.json` and `PROJECT_STATE.md` |
| M1-B comparative synthesis | NOT_AUTHORIZED | no candidate has all five gates PASS |
| M1-C materialisation | COMPLETE | canonical counts are generated in `M1/output/M1_STATE_SUMMARY.json` and `PROJECT_STATE.md` |
| M1-D0 deterministic calculation | COMPLETE | gate vectors, cost floors, feasibility verdicts, coverage counts, hard eliminations, latency verdicts and blocker prioritisation |
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
   UNK-0028).
2. **Request historical order-level data quotes and sample files** for CME and Nasdaq equity venues
   (UNK-0003, UNK-0004, UNK-0020), then validate timestamp semantics against the project's contract.
3. **Resolve citation tokens to primary URLs** and snapshot each page (UNK-0023, OQ-0001).
4. **Lock the CME matching rule per named contract**, recording its version (UNK-0002, OQ-0003).
5. **Narrow each surviving branch to one exact instrument** and lock its tick/lot/matching/fee facts
   (UNK-0027, OQ-0008).
6. **Search for modern venue-specific after-cost replication and disconfirmation** of the
   OFI/queue-imbalance/microprice mechanisms (UNK-0009, OQ-0005).
7. **Instrument a shadow path** and measure decision-to-market latency (UNK-0016, OQ-0012), then
   design the EV-versus-delay sweep (UNK-0008, OQ-0006).
8. **Build queue-aware fill modelling and fill-conditioned markout measurement** for passive or
   crossing candidates (UNK-0007, UNK-0019, OQ-0007).
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

## GOAL-001 candidate reselection (2026-09-28)

Terminal state: **EXTERNAL_BLOCK**. No surviving tuple is `TEST_NOW`. The **conditional economic
frontier** is `TUP-CME-ES-H3-OFI-AGG`; its minimum experiment requires an operator-selected account
path, an exact all-in CME/FCM cost schedule, and a validated historical event sample. No purchase or
external account action is authorized. Coinbase and Kraken remain `DEPRIORITIZE`, not dead. The
generic closure orchestrator's `next_autonomous_branch` is a mechanical blocker-dispatch field, not
the strategic reselection frontier; it must not override this decision. See the reselection artifacts.
