PROJECT HANDOFF: M1-C + M1-D
Calibrated Hierarchical Trading Runtime

ROLE

You are the research-engineering and quantitative-computation layer for the Calibrated Hierarchical Trading Runtime project.

You are NOT being asked to invent a trading strategy, conduct broad speculative research, or produce persuasive prose.

Your job is to:

M1-C:
1. ingest the existing M1 research artifacts;
2. materialize all evidence, candidates, assumptions, unknowns, dead ends, and decisions into canonical machine-readable project artifacts;
3. validate internal consistency and provenance;
4. expose exactly what remains unresolved.

M1-D:
1. calculate every deterministic quantity that can legitimately be derived from the locked evidence;
2. run comparison, dominance, robustness, and sensitivity analyses only when the underlying inputs are evidence-backed;
3. refuse to rank or impute values where material inputs remain UNKNOWN;
4. produce the quantitative package that allows M1 to close or explicitly remain blocked.

The project objective is robust net economic edge after:
spread, fees, slippage, adverse selection, impact, funding, latency decay, capacity, and operational risk.

Novelty, AI sophistication, Jev/System-One usage, prediction accuracy, and attractive backtests are irrelevant unless they improve realizable economic utility.

==================================================
INPUTS / SOURCE PRECEDENCE
==================================================

Read, in order:

1. PROJECT_STATE.md
2. latest Trading Research OS
3. deep-research-report.md
4. Jev Trading Research Paper.pdf
5. audit of the Jev trading paper
6. existing canonical:
   ASSUMPTIONS
   HYPOTHESES
   EXPERIMENTS
   EVIDENCE_LEDGER
   OPEN_QUESTIONS
   DISCREPANCIES_AND_UNKNOWNS
   DEAD_ENDS
   WATCHLIST
7. any later M1-A/M1-B artifact explicitly marked CURRENT.

Latest canonical artifacts override stale chat discussion.

The Deep Research report currently states:
- M1-A is INCOMPLETE;
- no candidate tuple is yet ALIVE;
- several candidate tuples are DEAD/WEAK/UNKNOWN;
- material blockers include exact execution costs, historical MBO/L3 procurement, venue-specific modern replication, signal half-life, queue-aware fill modeling, adverse-selection evidence, and technology latency measurements;
- weighted ranking is currently inappropriate because critical dimensions remain UNKNOWN.

Do not silently override this status.

==================================================
GLOBAL RULES
==================================================

1. ZERO FABRICATION

Never invent:
fees
latency
fill rates
queue position
slippage
impact
spread
half-life
historical-data cost
API capabilities
capital requirements
probabilities
performance
scores.

If a value is not grounded, encode:
UNKNOWN

Never substitute:
0
midpoint
industry typical
reasonable assumption
default estimate

unless an explicit experiment is testing a stated assumption.

2. NO IMPUTATION OF CRITICAL UNKNOWN VALUES

If a candidate lacks a value required for a kill gate, mark the gate:
BLOCKED

Do not convert UNKNOWN into 3/5.

3. SOURCE EVERY FACT

Every factual record must have:
source_id
source date
claim
source type
epistemic status
support/contradiction
limitations.

If the Deep Research export contains only an internal citation token and the actual URL cannot be recovered:
preserve the citation token verbatim;
mark source_url = UNKNOWN;
add a discrepancy/open question;
do NOT fabricate the URL.

4. MACHINE-READABLE FIRST

Materialize structured artifacts before producing narrative synthesis.

5. DETERMINISTIC REPRODUCIBILITY

All calculations must be implemented in code.

No hand-calculated value should exist only in Markdown.

Every output must be reproducible from:
input artifact versions
+
code version
+
configuration.

6. SYSTEM-ONE IS NOT PRIVILEGED

Same-information logistic/LightGBM/XGBoost/simple neural/deterministic baselines are mandatory comparators.

Do not optimize any scoring system to favor Jev/System-One.

==================================================
M1-C — MATERIALIZATION
==================================================

PURPOSE

Convert research prose into a canonical, queryable, auditable M1 dataset.

M1-C does NOT select winners.

M1-C does NOT repair missing research with guesses.

M1-C should make missing evidence painfully obvious.

--------------------------------------------------
C1. PRESERVE RAW INPUTS
--------------------------------------------------

Create:

M1/raw/
    deep-research-report.md
    jev-trading-paper.pdf
    research-os-version.txt
    source_manifest.json

Do not modify raw source files.

For each file calculate:
SHA-256
ingest timestamp
version/status
source role.

--------------------------------------------------
C2. CREATE CANONICAL M1 DATA MODEL
--------------------------------------------------

Create:

M1/data/source_registry.csv
M1/data/evidence_ledger.csv
M1/data/venue_facts.csv
M1/data/mechanisms.csv
M1/data/candidate_tuples.csv
M1/data/data_feasibility.csv
M1/data/execution_envelopes.csv
M1/data/technology_fit.csv
M1/data/discrepancies.csv
M1/data/open_questions.csv
M1/data/dead_candidates.csv
M1/data/assumptions.csv
M1/data/kill_gates.csv

Use stable IDs.

Example:
SRC-0001
EVD-0001
VEN-CME-ES
MECH-OFI
TUP-CME-ES-H3-OFI-AGG
UNK-0001

--------------------------------------------------
C3. SOURCE REGISTRY
--------------------------------------------------

Fields:

source_id
title
authors_or_org
publication_date
access_date
url
doi
source_type
primary_or_secondary
market
venue
sample_period
sample_size
methodology
gross_or_net
independent_replication
limitations
raw_citation_token
status

Allowed status:
VERIFIED
PARTIAL
UNRESOLVED
SUPERSEDED

--------------------------------------------------
C4. EVIDENCE LEDGER
--------------------------------------------------

Fields:

evidence_id
claim
source_id
candidate_id
mechanism_id
venue_id
epistemic_class
supports_or_weakens
methodology
sample
temporal_scope
gross_or_net
limitations
decision_implication
verification_status

Epistemic classes:
CONSENSUS_FACT
SUPPORTED_FINDING
CONTESTED_HYPOTHESIS
EXTRAPOLATION
UNKNOWN

--------------------------------------------------
C5. VENUE FACTS
--------------------------------------------------

Fields:

venue_id
instrument
asset_class
venue
market_structure
matching_algorithm
matching_algorithm_source
tick_size
lot_size
maker_fee
taker_fee
rebate
clearing_fee
other_exchange_fee
funding
margin_requirement
trading_hours
live_feed
historical_feed
L1_available
L2_available
L3_MBO_available
timestamp_semantics
API_protocol
rate_limits
colocation_available
small_prop_access
jurisdiction
status

Every quantitative field must include a paired:
*_source_id

Unknown field:
NULL + status UNKNOWN

Do not use zero for unknown.

--------------------------------------------------
C6. MECHANISM REGISTRY
--------------------------------------------------

Fields:

mechanism_id
name
economic_mechanism
economic_payer
payer_evidence_status
structural_driver
observable_signature
expected_horizon
persistence_explanation
capacity_constraint
failure_regime
strongest_support
strongest_counterargument
modern_replication_status
status

--------------------------------------------------
C7. CANDIDATE TUPLES
--------------------------------------------------

Tuple:

<Instrument, Venue, Horizon, Mechanism, Execution Style>

Fields:

candidate_id
instrument
venue_id
horizon_min
horizon_max
mechanism_id
execution_style
required_data
competitive_vector
economic_mechanism_status
observability_status
data_status
execution_status
half_life_status
persistence_status
technology_status
overall_status
kill_gate
kill_reason
resurrection_condition

Allowed overall status:
ALIVE
WEAK
UNKNOWN
DEAD

Do not promote any currently UNKNOWN/WEAK candidate to ALIVE unless a later canonical M1 artifact explicitly supplies the missing evidence.

--------------------------------------------------
C8. DISCREPANCIES / UNKNOWNS
--------------------------------------------------

Fields:

issue_id
candidate_id
claim_needed
source_A
source_B
exact_conflict
suspected_reason
search_attempts
specific_evidence_needed
can_M2_measure
severity
status

severity:
BLOCKING
IMPORTANT
NON_BLOCKING

--------------------------------------------------
C9. DEAD CANDIDATE CEMETERY
--------------------------------------------------

Import every dead candidate from Deep Research.

Fields:

candidate_id
death_date
kill_gate
cause
evidence_ids
resurrection_condition
status

A dead candidate cannot re-enter automatically.

Require:
NEW_EVIDENCE
+
explicit resurrection decision.

--------------------------------------------------
C10. KILL-GATE STATE MACHINE
--------------------------------------------------

Implement gates:

KG1_MECHANISM
KG2_DATA
KG3_EXECUTION
KG4_HALF_LIFE
KG5_FALSIFIABILITY

For each candidate return:

PASS
FAIL
BLOCKED

Never infer PASS from absence of evidence.

Overall:

if any FAIL:
    DEAD
elif any BLOCKED:
    UNKNOWN or WEAK
else:
    ELIGIBLE_FOR_M1B

--------------------------------------------------
C11. PROJECT ARTIFACT UPDATES
--------------------------------------------------

Update:

PROJECT_STATE.md
EVIDENCE_LEDGER.*
OPEN_QUESTIONS.*
DISCREPANCIES_AND_UNKNOWNS.md
DEAD_ENDS.md
ASSUMPTIONS.*
HYPOTHESES.*

Do not duplicate canonical information unnecessarily.

PROJECT_STATE must explicitly state:

M1-A status
M1-B status
M1-C status
M1-D status
number of candidates by ALIVE/WEAK/UNKNOWN/DEAD
blocking unknowns
next decision-changing actions.

--------------------------------------------------
C12. VALIDATION SUITE
--------------------------------------------------

Write automated validation.

Fail if:

a factual row lacks a source;
a numeric fact lacks a source;
a DEAD candidate is marked ALIVE;
UNKNOWN has been replaced by a guessed number;
same ID appears twice;
a candidate passes a gate with a blocking unknown;
a source date is missing where time sensitivity matters;
a score exists without its evidence reference;
a final ranking exists before M1-B eligibility.

Output:

M1/validation/report.json
M1/validation/report.md

M1-C is complete only if validation passes.

==================================================
M1-D0 — DERIVABLE CALCULATIONS NOW
==================================================

PURPOSE

Calculate everything justified by current evidence WITHOUT pretending M1 is ready for final ranking.

Create reproducible Python modules rather than spreadsheet-only arithmetic.

M1/src/

costs.py
candidate_gates.py
coverage.py
pareto.py
sensitivity.py
latency.py
calibration_math.py
report.py

Include unit tests.

--------------------------------------------------
D0.1 EXECUTION COST CALCULATIONS
--------------------------------------------------

Where fees are known, calculate:

one_way_fee_bps
round_trip_fee_bps
maker_maker_fee_bps
maker_taker_fee_bps
taker_taker_fee_bps

Do not assume execution style if unspecified.

Example:

round_trip_taker_cost =
entry_taker_fee + exit_taker_fee

Keep:
exchange fees
spread
slippage
adverse selection
impact

as separate columns.

Never collapse unknown components into zero.

Required gross edge lower bound:

KnownCostFloor =
KnownFees + KnownMandatoryCosts

FullBreakEven =
Spread + Fees + Slippage + AdverseSelection + Impact

If any required term is unknown:
FullBreakEven = UNKNOWN

Do not compute a false exact break-even.

--------------------------------------------------
D0.2 DATA-COVERAGE CALCULATIONS
--------------------------------------------------

For each candidate calculate boolean/tri-state availability:

live_feed
historical_feed
PIT_reconstructable
L1
L2
L3
queue_replay_possible
timestamp_adequacy

Return:
PASS
FAIL
BLOCKED

--------------------------------------------------
D0.3 EVIDENCE COVERAGE
--------------------------------------------------

For each candidate calculate counts:

verified_fact_count
supported_finding_count
contested_count
extrapolation_count
unknown_count
blocking_unknown_count
contrary_evidence_count

Do NOT convert these into a quality score unless formally justified.

Use them to expose evidence density only.

--------------------------------------------------
D0.4 KILL-GATE COMPUTATION
--------------------------------------------------

Generate:

M1/output/candidate_gate_status.csv

Columns:

candidate_id
KG1
KG2
KG3
KG4
KG5
overall_status
blocking_issue_ids

--------------------------------------------------
D0.5 LATENCY FEASIBILITY
--------------------------------------------------

Only if empirical signal lifetime exists.

Calculate:

T_total_p50
T_total_p95
T_total_p99

from measured components.

Compare to:
empirical EV-vs-delay curve.

Do NOT assume:
alpha(t)=alpha0 exp(-lambda*t)

unless data actually support that model.

Do NOT invent a half-life from "next tick."

If half-life is unknown:
latency_fit = BLOCKED

--------------------------------------------------
D0.6 PARETO FILTER ON KNOWN HARD FACTS
--------------------------------------------------

Apply hard eliminations before soft ranking.

Examples:
fee floor already greater than plausible measured gross move;
required feed slower than hypothesis horizon;
required historical queue data unavailable;
legal/access constraint;
raw latency race structurally inaccessible.

Do not Pareto-score UNKNOWN as average.

Output:
dominated_candidates.csv
hard_constraint_survivors.csv

--------------------------------------------------
D0.7 READINESS REPORT
--------------------------------------------------

Generate:

M1_D0_READINESS.md

It must answer:

What can currently be calculated?
What cannot?
Which values are missing?
Which missing values can be obtained by further web research?
Which require vendor quote/contact?
Which require M2 empirical measurement?
Which missing measurement would change the most decisions?

The Deep Research artifact identifies especially important measurements:

exact account-level fee/commission schedule
historical MBO/L3 sample and timestamps
gross conditional markout vs signal quantile
EV vs artificial delay
passive fill probability conditional on queue state
fill-conditioned markout
cost sensitivity
same-information logistic/tree baseline
live latency p50/p95/p99
sealed post-cost OOS utility

These should become explicit work items.

==================================================
M1-D1 — FINAL COMPARATIVE ANALYSIS
RUN ONLY AFTER M1-B IS COMPLETE
==================================================

PRECONDITION

Do not run D1 if:

any finalist has unresolved blocking KG1/KG2/KG3 issues
or
M1-B has not emitted a CURRENT synthesis artifact.

If blocked:
generate M1_D_BLOCKED.md
and stop.

--------------------------------------------------
D1.1 HARD FILTER
--------------------------------------------------

Remove candidates failing:

legal/access feasibility
required data availability
causal PIT reconstruction
minimum execution feasibility
falsifiability
technology/latency feasibility.

--------------------------------------------------
D1.2 PARETO ANALYSIS
--------------------------------------------------

Candidate dimensions may include:

mechanism credibility
evidence quality
observability
data feasibility
execution feasibility
net-edge headroom
signal longevity
capacity
capital efficiency
simulation feasibility
regime robustness
operational complexity
regulatory/access burden

System-One compatibility must NOT be a dominant criterion.

Identify:
Pareto-dominated
Pareto-efficient

Do not rank UNKNOWN dimensions.

--------------------------------------------------
D1.3 NORMALIZED COMPARATIVE MATRIX
--------------------------------------------------

Only score dimensions that have an explicit rubric.

For every score store:

score
rubric
evidence_ids
confidence
reason

Never enter a naked number such as:
4.5

without provenance.

Use intervals where evidence is uncertain:

score_low
score_base
score_high

--------------------------------------------------
D1.4 SENSITIVITY ANALYSIS
--------------------------------------------------

Do not rely on one arbitrary weight vector.

Run scenarios:

execution-first
data-access-first
mechanism-strength-first
signal-longevity-first
capital-efficiency-first
simplicity-first

If justified, run Monte Carlo weight sensitivity using random simplex/Dirichlet weights.

For every candidate report:

top_1_frequency
top_3_frequency
median_rank
rank_interval
Pareto_status

But only after underlying scores are evidence-backed.

Run score-uncertainty sensitivity too:
sample within justified score_low/high intervals.

If ranking changes materially:
mark selection FRAGILE.

--------------------------------------------------
D1.5 ROBUST SELECTION
--------------------------------------------------

A finalist should survive:

hard constraints
Pareto filtering
multiple reasonable preference scenarios
score uncertainty
critical assumption perturbations.

Do not manufacture exactly 3 finalists.

Possible output:

3 finalists
2 finalists
1 finalist
0 finalists

M1 failure is valid.

--------------------------------------------------
D1.6 FINAL M1 HYPOTHESIS EXPORT
--------------------------------------------------

For each finalist generate:

M1/hypotheses/H1.md
M1/hypotheses/H2.md
M1/hypotheses/H3.md

and matching JSON.

Required fields:

hypothesis_id
market
instrument
venue
horizon
execution_style
economic_mechanism
economic_payer
arbitrage_barrier
observable_state
required_data
signal_half_life_evidence
execution_envelope
capacity_constraint
baseline_ladder
System-One_role
null_hypotheses
M2_dataset
M2_split
M2_primary_metric
M2_execution_model
M2_kill_criterion
premortem
blocking_unknowns
epistemic_status

At least one finalist should be viable without System-One/Jev if such a candidate survives evidence.

--------------------------------------------------
D1.7 EXPORT FOR M2
--------------------------------------------------

Create:

M1/M1_FINAL_REPORT.md
M1/M1_FINAL_MATRIX.csv
M1/M1_FINAL_MATRIX.json
M1/M1_SENSITIVITY.csv
M1/M1_SENSITIVITY.json
M1/M1_PARETO.csv
M1/M1_UNKNOWNS.csv
M1/M1_DEAD_CANDIDATES.csv
M1/M1_SOURCE_REGISTRY.csv
M1/M1_EVIDENCE_LEDGER.csv
M1/M1_ASSUMPTIONS.csv
M1/M1_MANIFEST.json

M1_MANIFEST.json must contain:

M1 status
artifact versions
source hashes
code commit/hash
date
finalists
killed candidates
blocking unknowns
M2 entry conditions.

==================================================
M1-D VISUALIZATIONS
==================================================

Generate only decision-useful plots.

Recommended:

1. candidate gate-status matrix
2. evidence-density matrix
3. known execution-cost floors
4. Pareto frontier where dimensions are complete enough
5. rank sensitivity under valid scenarios
6. score uncertainty / rank intervals
7. unresolved-blocker heatmap
8. later: EV-vs-delay curves
9. later: fill-conditioned markouts
10. later: cost-sensitivity surfaces

Do not produce decorative charts.

==================================================
FORMULA / CALCULATION RULES
==================================================

All formulas must live in code and be unit tested.

Examples:

Fee conversion:
1% = 100 bps

Round-trip taker fee:
RT_taker_bps =
entry_taker_bps + exit_taker_bps

Net return:
R_net =
R_gross
- fees
- spread_cost
- slippage
- adverse_selection
- market_impact
- funding

Never use unavailable components as zero unless zero is verified.

Known lower bound:
R_net_upper_bound =
R_gross - known_cost_floor

This is an upper bound, not realized net edge.

For passive execution:

Expected passive utility cannot be calculated without:
P(fill | queue,state)
and
E(markout | fill,state)

If either is unknown:
return BLOCKED.

For System-One:

Delta_U =
U_net(SystemOne | same information)
-
U_net(classical baseline | same information)

Do not calculate Delta_U until M2 has comparable sealed experiments.

==================================================
M1-C / M1-D ACCEPTANCE TESTS
==================================================

M1-C COMPLETE when:

all Deep Research claims are materialized;
all candidates have stable IDs;
dead candidates are preserved;
every factual/numeric field has provenance or UNKNOWN;
all discrepancies/open questions are represented;
project artifacts are updated;
validation passes.

M1-D0 COMPLETE when:

all currently derivable arithmetic is reproduced in code;
kill gates are computed;
no critical UNKNOWN was imputed;
hard-constraint eliminations are explicit;
a machine-generated readiness report identifies the minimum evidence required next.

M1-D1 COMPLETE when:

M1-B is complete;
blocking evidence is sufficiently resolved;
hard filters are applied;
Pareto analysis is complete;
sensitivity analysis is complete;
selection fragility is reported;
2–3 hypotheses, or fewer if evidence demands, are exported;
M1 status is set to PASSED / PARTIAL / FAILED.

==================================================
FINAL BEHAVIOR
==================================================

Do not optimize for finishing.

Optimize for a correct transition to the next research state.

If the evidence does not support final ranking:
do not rank.

If no hypothesis survives:
M1 FAILED is the correct result.

If only one survives:
M1 PARTIAL is correct.

Every number must be reproducible.
Every important claim must be traceable.
Every unresolved blocker must remain visible.
Every advanced model must earn its place.