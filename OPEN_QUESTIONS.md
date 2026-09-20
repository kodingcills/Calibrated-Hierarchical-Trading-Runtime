# OPEN QUESTIONS

Canonical machine-readable source: `M1/data/open_questions.csv`.
Question ids are stable; `legacy_question_id` preserves the original research-OS registry
identifier where one existed.

Open questions: 16

## OQ-0001 - priority HIGH

**Which of the M1-A external claims survive independent verification once every citation token resolves to a primary URL?**

- why it matters: The fee facts that already killed two candidates, and the feed-cadence fact that killed a third, are currently report-mediated rather than independently re-derived.
- workstream: Provenance
- answer required before gate: M1-A_CLOSE
- search status: not_started
- current best answer: Tokens preserved; no URLs recoverable from repository artifacts.
- unresolved gap: 25 tokens unresolved.
- next search: Resolve token by token against primary sources and snapshot each page.
- related issues: UNK-0023
- legacy id: None

## OQ-0002 - priority CRITICAL

**What is the project-level all-in per-contract cost for the CME candidates?**

- why it matters: It decides whether any CME tuple can survive aggressive execution.
- workstream: Venue economics
- answer required before gate: M1-B
- search status: not_started
- current best answer: UNKNOWN: only CME market-data architecture was verified.
- unresolved gap: No account-path fee schedule.
- next search: Obtain FCM/broker schedule for the intended account and register it as an immutable M2 cost configuration.
- related issues: UNK-0001|UNK-0028
- legacy id: None

## OQ-0003 - priority CRITICAL

**What is the current CME matching/allocation rule for each named candidate contract and order type?**

- why it matters: Without it, no passive CME fill model or queue claim is admissible.
- workstream: Market structure
- answer required before gate: M1-B
- search status: not_started
- current best answer: Only that rules are product-specific and can change by notice.
- unresolved gap: No contract-level rule locked.
- next search: Look up the rulebook per contract; record rule version.
- related issues: UNK-0002
- legacy id: None

## OQ-0004 - priority CRITICAL

**Can order-level historical data be licensed for CME, Nasdaq equities, Cboe BZX and Eurex at acceptable cost?**

- why it matters: Causal replay is a precondition for every passive or queue-dependent candidate.
- workstream: Data procurement
- answer required before gate: M2_ENTRY
- search status: not_started
- current best answer: Product existence verified for CME/Nasdaq; price, licence, schema and timestamps unverified.
- unresolved gap: No quote, no sample file.
- next search: Request vendor quotes and run a schema/timestamp validation on a sample for each venue.
- related issues: UNK-0003|UNK-0004|UNK-0020|UNK-0022|UNK-0011
- legacy id: None

## OQ-0005 - priority CRITICAL

**Is the published OFI/queue-imbalance/microprice predictability still present, after costs, on any candidate venue in 2026?**

- why it matters: This is the only external result that currently justifies running a venue-specific test at all.
- workstream: Mechanism replication
- answer required before gate: M1-B
- search status: not_started
- current best answer: Supported as information content in U.S. equities (2015 sample and earlier); no after-cost replication on any target venue.
- unresolved gap: No current venue-specific net measure.
- next search: Search for modern independent after-cost replications and for disconfirming studies; then design the venue-specific test.
- related issues: UNK-0009
- legacy id: None

## OQ-0006 - priority CRITICAL

**What is EV(delay) for each candidate signal?**

- why it matters: It determines the admissible compute/network budget and whether any model can be placed at the hypothesised horizon.
- workstream: Latency / half-life
- answer required before gate: M1-B
- search status: not_started
- current best answer: UNKNOWN for every candidate; the report forbids inferring decay from 'next tick'.
- unresolved gap: No curve exists.
- next search: Run a controlled delay sweep once replay data exists.
- related issues: UNK-0008|UNK-0016
- legacy id: None

## OQ-0007 - priority CRITICAL

**What is P(fill | queue state) and E(markout | fill, state) for each passive candidate?**

- why it matters: Passive economics are undefined without both.
- workstream: Execution
- answer required before gate: M2_ENTRY
- search status: not_started
- current best answer: UNKNOWN; touch=fills is disallowed.
- unresolved gap: No queue-aware simulator or shadow-fill process exists yet.
- next search: Build a queue-aware fill model under the venue's actual matching rule and validate against shadow observations.
- related issues: UNK-0007|UNK-0019
- legacy id: None

## OQ-0008 - priority HIGH

**Which exact instruments should the surviving branches be narrowed to?**

- why it matters: Several rows name a family, not a tradable contract, so no falsifier can be stated.
- workstream: Universe definition
- answer required before gate: M1-B
- search status: not_started
- current best answer: Family-level naming only.
- unresolved gap: No tick/lot/matching/fee facts at instrument level.
- next search: Pick one instrument per branch on liquidity and data grounds, then lock its facts.
- related issues: UNK-0027
- legacy id: None

## OQ-0009 - priority HIGH

**What are the fee, access and historical-data facts for Kalshi/Polymarket, Deribit, Eurex, Cboe options and the FX venues?**

- why it matters: These are the tuples whose entire feasibility is currently unverified.
- workstream: Venue economics
- answer required before gate: M1-B
- search status: not_started
- current best answer: UNKNOWN across all five venue families.
- unresolved gap: No primary-source lock.
- next search: Per-venue primary research; jurisdiction matrix for event contracts.
- related issues: UNK-0011|UNK-0012|UNK-0013|UNK-0014|UNK-0015
- legacy id: None

## OQ-0010 - priority HIGH

**Are the venue fee facts that killed the crypto tuples current and correctly read?**

- why it matters: Two candidate deaths depend on verified fee schedules; misreading them would be a false kill.
- workstream: Venue economics
- answer required before gate: M1-B
- search status: not_started
- current best answer: 60/40 bps (Coinbase 0-10k), 40/80 bps (Kraken Tier 1) as reported.
- unresolved gap: URL-level verification pending.
- next search: Re-verify both schedules from primary pages and record snapshots.
- related issues: UNK-0023
- legacy id: None

## OQ-0011 - priority CRITICAL

**Does hosted Jev or a local System-One model add execution-aware net utility over a same-information logistic/tree baseline?**

- why it matters: This is the central falsification test for the paper's claimed architectural advantage and the only admissible basis for admitting System-One.
- workstream: System-One / Trading Architecture
- answer required before gate: G4_ROBUSTNESS
- search status: not_started
- current best answer: No same-information controlled benchmark exists.
- unresolved gap: No measured latency profile, no sealed utility comparison.
- next search: Run only after market/horizon/data/execution baseline are fixed.
- related issues: UNK-0017|UNK-0026
- legacy id: Q-010

## OQ-0012 - priority CRITICAL

**What are this project's own live decision-to-market latency p50/p95/p99?**

- why it matters: Model placement, venue choice and horizon viability all depend on it.
- workstream: Latency
- answer required before gate: M2_ENTRY
- search status: not_started
- current best answer: No instrumented path exists.
- unresolved gap: No measurement.
- next search: Instrument the shadow path and log the full timestamp contract.
- related issues: UNK-0016
- legacy id: None

## OQ-0013 - priority MEDIUM

**Which cost components can be parameterised conservatively rather than measured, and at what values?**

- why it matters: A cost-sensitivity surface is required by the project's own G4 gate and may kill branches cheaply.
- workstream: Execution economics
- answer required before gate: G4_ROBUSTNESS
- search status: not_started
- current best answer: Only exchange fees are verified for two crypto venues and one equity venue.
- unresolved gap: No spread/slippage/impact parameterisation.
- next search: Define preregistered conservative ranges per venue and run the surface.
- related issues: UNK-0006|UNK-0032
- legacy id: None

## OQ-0014 - priority HIGH

**What evidence supports the persistence argument for each surviving mechanism (who keeps paying, and why do they not stop)?**

- why it matters: Persistence is a required invariant; 'it worked in 2015' is not a persistence argument.
- workstream: Edge provenance
- answer required before gate: M1-B
- search status: not_started
- current best answer: Report gives payer interpretations that are EXTRAPOLATIONS; no persistence evidence.
- unresolved gap: No risk/capacity/mandate evidence for any candidate.
- next search: For each survivor, find evidence on payer constraints (mandates, balance sheet, latency budgets) or mark the persistence step UNKNOWN.
- related issues: UNK-0009|UNK-0029
- legacy id: None

## OQ-0015 - priority HIGH

**What historical-data timestamp semantics (exchange vs receive time, clock domain) can be relied upon for causal replay?**

- why it matters: A replay that cannot order events causally cannot be used to claim priority or fills.
- workstream: Data integrity
- answer required before gate: M2_ENTRY
- search status: not_started
- current best answer: The project's timestamp contract is defined in methods; no vendor feed has been validated against it.
- unresolved gap: No feed-level validation.
- next search: Validate a sample file against the timestamp contract per venue.
- related issues: UNK-0003|UNK-0004
- legacy id: None

## OQ-0016 - priority HIGH

**Is the candidate architecture's target market actually inside the M1 candidate set?**

- why it matters: The paper targets a generic block-cadence on-chain venue and names no venue, instrument, account or fee schedule. If that market class is not among the M1 tuples, the System-One branch has no venue to be tested on, which changes what M1-B could even consider.
- workstream: Universe definition
- answer required before gate: M1-B
- search status: not_started
- current best answer: No named venue in the paper; the M1 tuple ledger contains no block-cadence on-chain venue.
- unresolved gap: No tuple exists for the architecture's own target market.
- next search: Decide explicitly whether to add such a tuple (with its own fee/data/access lock) or to keep the architecture as an unhosted specimen.
- related issues: UNK-0023|UNK-0026
- legacy id: None
