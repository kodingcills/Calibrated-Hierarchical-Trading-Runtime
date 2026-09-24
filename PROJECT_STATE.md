# PROJECT_STATE

Status: CURRENT
Version: 1.0.0
Last Updated: 2026-09-24T14:06:09Z

This is the canonical fast-orientation artifact. Read it before any other file. Its counts are
generated from `M1/output/M1_STATE_SUMMARY.json` and enforced against the machine-readable
artifacts by `M1/src/validate.py` (rule V11); do not hand-edit a number here.

## Mission

Discover, falsify, validate, and only then deploy robust trading edge that survives realistic
execution. The project's objective is net economic edge after spread, fees, slippage, adverse
selection, impact, funding, latency decay, capacity and operational risk. Novelty, model
sophistication, prediction accuracy and attractive backtests carry no weight unless they improve
realizable economic utility.

## Current Milestone

**M1 - Market x Venue x Horizon x Edge-Mechanism Selection.**

Substage state (from repository evidence, not from plan):

- M1-A evidence discovery is INCOMPLETE: the M1-A artifact itself concludes INCOMPLETE, and this
  materialisation found that its stated reasons need revision (one is now false - see below),
  while the empirical blockers it lists remain independently sufficient.
- M1-C materialisation is COMPLETE. Counts live in the generated Counts block below and are
  checked against the machine-readable summary by the validator, so they are not restated here.
- M1-D0 deterministic calculations are COMPLETE: gate vectors, status ceilings, cost floors,
  feasibility verdicts, coverage counts, hard-constraint eliminations, latency verdicts,
  blocker prioritisation. Full break-even remains UNKNOWN for every candidate, by construction.
- M1-B is not yet authorized (no candidate is gate-eligible).
- M1-D1 is not yet authorized (see `M1/output/M1_D1_BLOCKED.md`).

## M2 — Autonomous falsification run: TERMINAL STATE `KILLED`

Canonical detail: `M2/output/M2_AUTONOMOUS_STATUS.md`. Machine-readable verdict:
`M2/output/univproxy/M2_0_6_VERDICT.json`. Sealed contract:
`M2/experiments/M2-0-6-UNIVPROXY/freeze.json` (sha256 `4fc098a3…c32b38b`, hashed before any
proxy-run observation was inspected).

- **M2-0** (2026-09-22) replayed a free Nasdaq TotalView-ITCH 5.0 sample day (2019-07-30, raw
  sha256 `c65784c4…09bc2d4a`) into a deterministic causal decision grid and completed the
  calculation stage. Sample role: DEVELOPMENT, `holdout_eligible = false`,
  `outcome_claim_permitted = false` — it can never become a validation or sealed partition.
  Point-in-time universe membership: BLOCKED.
- **M2-0.5** conditioned the aggressive-execution arithmetic on a declared state space and found
  no positive state. It also found and recorded defects `M2-0-D1/D2/D3` in M2-0's frozen execution
  table (cross-to-cross reported at half its true bps value; the fee evaluated at half the true
  price). The frozen artifact was left untouched and the corrected quantities are the ones used
  downstream; both defects pushed the reported figure in the candidate's favour.
- **M2-0.6** (2026-09-23) tested whether the M2-0.5 verdict was an artifact of the M2-0 compute
  scope (top 61 by order-add message count: mean quoted spread 4.82 ticks, mean price ≈ $43, almost
  no high-priced one-tick names) rather than a property of the candidate's own population. It
  re-scoped the replay to the top 120 dollar-volume names inside a single-day proxy of the frozen
  rule's own liquidity decile, applied the rule's own large-tick sentence (33 of 115 replayed names
  pass), and evaluated the identical declared state space with the identical cost ledger.
- **Terminal state `KILLED`.** In the rule-conformant population the measured 1000 ms signal is
  0.0794 bps against a 4.1011 bps executed round trip (1.94% coverage; required/signal 51.64 pooled
  and 10.69 in the best of 356 declared states); 0 of 356 states is net-positive under the
  structural cost floor; and a **clairvoyant** trader on the same instants nets +0.822 bps per trade
  at the structural floor and +0.219 bps per trade on the accessible broker path, on 1.18% of
  instants. The M2-0 scope hypothesis was tested and rejected (56.9 vs 51.64), and a broader 115-name
  scope that contains the highest-priced names is worse (117.3). Registered dead in `DEAD_ENDS.md`
  and `M1/data/dead_candidates.csv` (KG3_EXECUTION FAIL; evidence `EVD-0067`; patch `P-0006`).
- **What is not dead**: the mechanism itself. A passive/queue formulation of the same signal
  remains open and requires a queue-aware fill model (`M1/work/m2_specs/PASSIVE_FILL_MODEL.md`,
  `FILL_CONDITIONED_MARKOUT.md`); it must be registered as its own candidate, never as an execution
  mode change on the killed row. **No modern dataset purchase is justified for the aggressive
  branch**: the friction is pinned by the Reg NMS minimum tick and the exchange/statutory fee floor,
  and the candidate's own literature defines its large-tick universe as names where the tick is
  economically large relative to price.
- **Boundary of the kill** (stated, not hedged): one 2019 low-volatility session (measured move
  scale 0.847 bps/s ≈ 20.6% annualised). The kill's best-state condition holds while a modern
  regime's move scale is below ≈ 2.1× that level and the pooled condition below ≈ 5×; beyond that
  only a modern-regime measurement could decide, which is the listed resurrection condition.

## M2-1 — Passive execution feasibility: TERMINAL STATE `KILLED`

Canonical detail: `M2/output/M2_PASSIVE_FEASIBILITY_STATUS.md`. Frozen contract:
`M2/experiments/M2-1-PASSIVE-QIMB/freeze.json` (sha256 `03efd04e…83e7d0`, sealed before the
canonical replay). As-run inputs, pre-result code corrections and artifact hashes:
`M2/experiments/M2-1-PASSIVE-QIMB/run_inputs.json`. Queue identifiability:
`M2/output/passive/QUEUE_IDENTIFIABILITY.md`.

- **Hypothesis** (`TUP-NASDAQ-LARGETICK-H2-QIMB-PAS`, parent the killed aggressive row): passive
  entry earns the spread the aggressive style paid, so the measured 0.0794 bps directional response
  might survive once realistic queue position and fill-conditioned adverse selection are included.
- **Model**: deterministic queue-aware replay of 100-share orders joining the back of the near touch
  at every frozen decision instant, filling only after the displayed quantity ahead is consumed and
  real executable flow reaches them; no probabilistic fills, no maker rebate in the primary result,
  1 s lifetime, aggressive exit at the far touch 10 ms–1 s after the fill.
- **Result**: 6,067 of 737,768 primary attempts fill (0.82%) at a median 537 ms behind a median
  700-share queue; the fill-conditioned midpoint move is **−0.973 bps at 1000 ms** (CI
  [−1.102, −0.867]) and −0.884 bps at 10 ms, against an **unconditional +0.079 bps** in the same
  direction; the reference policy is negative **before any fee** (−1.32 to −1.48 bps gross) and
  −2.02 bps per filled share at the structural floor; 0 of 5 states and 0 of 6 queue bands is
  positive; 30 of 33 symbols lose. The **optimistic bound** (perfect queue position) gives 4.30%
  fills and is more negative per attempt (−1.019 bps, CI [−1.116, −0.932]), so the verdict does not
  rest on the queue model's conservatism.
- **Terminal state `KILLED`** on the precommitted rule (K2 starvation, K3 adverse-selection
  dominance, K6 scale; K4's rebate clause documented as not met because the exchange credit — a 2026
  rate on a 2019 tape — would flip the sign of an exchange subsidy, not of the signal). Registered
  dead in `DEAD_ENDS.md` and `M1/data/dead_candidates.csv` (KG3_EXECUTION FAIL; evidence `EVD-0069`;
  patch `P-0008`).
- **Modern-data value of information: zero for this family.** The binding failures are the Reg NMS
  tick, the exchange/statutory fee floors and the fill-selection geometry; no purchasable parameter
  moves the decision, and the signal would have to be 30–50× larger.
- Also dead by the same standard: `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` (M2-0.6). The family
  (`H2 Nasdaq large-tick queue imbalance`) is therefore **stopped**; the reusable lesson is that an
  H2 top-of-book signal must show a magnitude of the same order as its round trip before an
  execution model is built for it (`DECISIONS.md` D-0037).

## M2-2 — Microprice economic-materiality gate: TERMINAL STATE `KILLED`

Canonical detail: `M2/output/M2_MICRO_MATERIALITY_STATUS.md`. Frozen contract:
`M2/experiments/M2-2-MICRO-MATERIALITY/freeze.json` (sha256 `89f84b29…`, sealed before any
canonical economics were inspected); as-run inputs and artifact hashes:
`M2/experiments/M2-2-MICRO-MATERIALITY/run_inputs.json`.

- **Purpose**: apply D-0037's own rule to the last aggressive Nasdaq large-tick row — measure the
  signal's realized magnitude against the friction before building any execution model for it.
- **Estimator**: the registered mechanism is the Stoikov micro-price, recovered from its own source
  material rather than substituted: `p_micro = mid + g(X)` with
  `g(X) = E[mid(τ₁) − mid(t) | X = (imbalance bin, spread class)]`, first step, calibrated on an
  **expanding prior-session window** (5-minute refit, 200 prior resolved observations per cell) so
  that no observation can see itself or any later one. The weighted mid-price (whose sign *is* the
  imbalance sign by construction) is excluded by the frozen contract.
- **Result**: on the same 33 rule-conformant names M2-0.6 measured, pooled over 726,943
  direction-defined decision instants and the candidate's **own H2-H3 band** the signal is
  **+0.2333 bps at 15 s** (CI [0.2142, 0.2530]) against a **3.9875 bps** structural round trip
  (**R_pooled = 17.09**); the strongest preregistered state — imbalance in `[0.8,1.0]`, one-tick
  spread, 15 s, 2.98% of instants — is **+0.5836 bps** (CI [0.4842, 0.6831], **R_best = 5.02**). At
  the queue-imbalance row's own horizon the microprice is **not** an uplift: 0.0745 bps against
  0.0794 bps at 1000 ms.
- **Clairvoyant ceiling**: with perfect foresight of the future executable quotes on the same
  instants the aggressive round trip nets **+1.6275 bps per trade at the structural floor**
  (+0.7012 bps on the accessible path) on 19.51% of instants. Prediction cannot exceed clairvoyance,
  and clairvoyance does not clear one round trip: the candidate is limited by friction, not by
  prediction quality.
- **Terminal state `KILLED`** on the precommitted rule (`R_best ≥ 5` and `R_pooled ≥ 10`, oracle
  contradiction not triggered at a 0.0796 ratio against a 0.25 bar). Registered dead in
  `DEAD_ENDS.md` and `M1/data/dead_candidates.csv` (KG3_EXECUTION FAIL; evidence `EVD-0070`; patch
  `P-0009`).
- **Margin, stated rather than smoothed** (see the status artifact's own section): `R_best = 5.015`
  clears its bar by 0.3%, and that state's interval implies `R_best ∈ [4.28, 6.04]`, so the
  best-state clause is a point estimate and not a resolved separation. The kill does not rest on it:
  `R_pooled = 17.09` clears its own bar by 71%, and the oracle ceiling — which contains no
  estimator, no calibration and no mapping choice — leaves 41% of a round trip to the best possible
  trader even at the cheapest fee path.
- **The whole H1–H3 Nasdaq large-tick top-of-book sequence is now closed.** Three measurements, one
  direction of answer: an aggressive round trip that costs 4.1 bps, a passive fill selected against
  by 1.0 bps of drift, and now a long-horizon signal of 0.23 bps against a 4.0 bps round trip with a
  1.63 bps clairvoyant ceiling. Modern data value of information: **zero** — the friction is pinned
  by the Reg NMS tick and the exchange/statutory fee floor, and the signal would have to be 5–17×
  larger.

## Milestone Status

<!-- GENERATED:milestones -->
M1-A: INCOMPLETE
M1-B: NOT_AUTHORIZED
M1-C: COMPLETE
M1-D0: COMPLETE
M1-D1: NOT_AUTHORIZED
<!-- /GENERATED:milestones -->

## Current Research Thesis

The project is searching for realizable trading edge. The candidate architecture in
`Jev Trading Research Paper.pdf` (Jev/System-One as a probabilistic judgment layer inside a
deterministic market-making loop) is a candidate component only. The architecture is not assumed
to require Jev, and no evidence in this repository shows that it improves execution-aware net
utility. System-One remains unadmitted: its own vendor documentation says arithmetic, counting,
numeric precision and date comparison should stay in code, and nothing external establishes an
exception.

## Active Candidate Hypotheses

**No candidate is ALIVE.** There is no active hypothesis tier. What exists is a survivor set that
has passed only hard constraints and still has every economic gate BLOCKED. Candidate rows and
their gate vectors are canonical in `M1/data/candidate_tuples.csv`; the surviving rows are listed
in `M1/output/hard_constraint_survivors.csv`.

`TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` left this set on 2026-09-23 (M2-0.6: aggressive execution
economics measured and failed in the candidate's own population) and its passive pivot
`TUP-NASDAQ-LARGETICK-H2-QIMB-PAS` followed on 2026-09-24 (M2-1: starvation inside the signal's own
horizon plus adverse-selection dominance). `TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG` left it on
2026-09-24 as well (M2-2: its registered estimator's realized magnitude measured against the same
friction, 5× short in the strongest declared state and 17× pooled). The three remaining WEAK rows
(constraining evidence exists, nothing supports an upgrade):

| candidate | instrument | venue | horizon | mechanism | execution | blocking issue |
|---|---|---|---|---|---|---|
| TUP-CME-ES-H1-QDEP-PAS | ES future | CME | H1 10-100 ms | queue depletion | passive | matching rule, fill probability, all-in cost |
| TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS | stock >= $1 | Cboe BZX | H2-H3 | spread capture | passive | queue/adverse selection unmeasured |
| TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG | stock, national market | multi-venue | H1 | stale quote | aggressive | latency race unmeasured (label basis recorded in UNK-0024) |

**Reusable lesson now on record (and now a gate on how candidates are admitted to M2)**: every
measurement on this venue family — an aggressive round trip of 4.1 bps, a passive fill selected
against by 1.0 bps of midpoint drift, a clairvoyant ceiling of 0.22 bps per trade at 1 s, and now a
0.23 bps long-horizon microprice response against the same 4.0 bps round trip — points the same way,
so a top-of-book signal at H2 must show a magnitude of the same order as the round trip it faces
*before* an execution model is built for it. That test has now been applied to both aggressive rows
of the Nasdaq large-tick ledger and both failed it on measurement, which is why the sequence is
closed rather than continued (`DECISIONS.md` D-0037, D-0038).

Fourteen rows are UNKNOWN (no venue-specific evidence at all): ES H3 OFI, NQ H3 OFI, Treasury
queue/replenishment, WTI flow/volatility, Nasdaq auction imbalance, Hyperliquid H3 OFI/liquidation,
Hyperliquid H4 funding/basis, Eurex OFI/queue, Cboe options surface RV, Deribit options surface RV,
Kalshi event inference, Polymarket event inference, institutional FX lead-lag, retail FX feed lag.

## Killed Candidates

Ten registered rows are DEAD: 5 tradable tuples and 5 non-tuple registrations. The ledger with
cause, evidence and resurrection condition is `DEAD_ENDS.md` (machine-readable:
`M1/data/dead_candidates.csv`). Three of the ten are M2 kills rather than M1 kills:
`TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` (measured aggressive execution economics, EVD-0067, patch
P-0006), its passive pivot `TUP-NASDAQ-LARGETICK-H2-QIMB-PAS` (measured passive fill and
adverse-selection economics, EVD-0069, patch P-0008), and `TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG`
(measured microprice magnitude, EVD-0070, patch P-0009). Re-entry requires NEW_EVIDENCE **and** an
explicit resurrection decision recorded in `DECISIONS.md`; silent re-entry is prohibited.

## Current Strongest Findings

Durable, evidence-backed, and still less than tradable alpha:

1. Short-horizon order-book variables (queue imbalance, order-flow imbalance, microprice) contain
   predictive information in some markets. That is not evidence of net tradable edge, and the
   strongest supporting samples are old and gross of costs.
2. Venue fee economics can dominate model quality. Verified at the named tiers, two taker fills
   cost 120 bps on Coinbase (0-10k tier) and 160 bps on Kraken (Tier 1) before spread, slippage,
   impact and adverse selection - which is why those tuples are dead on arithmetic alone.
3. Data availability is not replay sufficiency. Nasdaq's easily accessible U.S. Equity Tick History
   is consolidated Level 1 and cannot reconstruct individual order queues.
4. The Hyperliquid public book feed is documented at a >= 0.5 s snapshot cadence with aggregate
   levels, so a 10-100 ms public-feed reaction thesis is structurally impossible as specified.
5. CME matching is product-specific and has changed by notice, so a generic CME queue model is
   unjustified and any queue study must record the rule version it assumes.
6. System-One remains unadmitted: no external evidence establishes incremental execution-aware
   utility, and hosted latency is vendor-reported only (70-500 ms).
6b. **Crypto and event-market venue facts are now verified, and the legal picture is two-sided.**
   Hyperliquid's perp base tier is 0.045% taker / 0.015% maker with documented tier, staking and
   referral modifiers, and an official historical archive exists (requester-pays S3: hourly L2
   books and per-block fills, updated approximately monthly with no completeness guarantee).
   Market-wide liquidation flow is *not* officially observable - liquidation surfaces are
   user-scoped - which removes the observability premise from the liquidation variant of the
   Hyperliquid H3 tuple. Deribit publishes a bps fee table with premium caps and documents
   trade/funding backfill but no bulk option-book archive; the US is a prohibited jurisdiction.
   Kalshi's taker fee is a price-dependent formula (round_up(M x 0.07 x C x P x (1-P))) with a
   zero default maker multiplier, and its state status is actively contested: Washington
   (2026-08-13) and Nevada (2026-07-24) orders restrict categories, while the Third Circuit
   upheld preemption against New Jersey (2026-04-06). International Polymarket blocks US persons;
   the accessible US product is a separate venue with participant-scoped reporting and a
   documented position/ledger floor of 2026-05-01.
6c. **Several venue fee pages are dynamic with no published effective date** (Hyperliquid,
   Polymarket; Deribit gives one update date). A cost model built on an undated page cannot be
   shown to describe the period it is tested on, so the project must snapshot and hash fee
   schedules itself (UNK-0035).
6d. **CME matching is engine-assigned and product-specific, and the public cost search is
   exhausted.** Nine documented algorithm codes are assigned per product with split
   FIFO/pro-rata parameters and minute-cycle level recalculation, but the ES/NQ assignment was
   not located, and the CME fee and clearing-fee pages could not be retrieved: no fee value
   entered canonical state, and one surfaced figure was rejected as non-primary (patch P-0003).
   Historical order-level data does exist for at least part of the complex (DataMine MBO FIX from
   2017-01-07, coverage as documented COMEX/NYMEX; no published price).
6e. **The only two mechanism-gate passes rest on report-mediated sources.** KG1 passes for the
   Nasdaq queue-imbalance and Nasdaq microprice tuples, and the supporting studies are named but
   their URLs are not recoverable from the repository (`EVD-0012`, `EVD-0014`). Re-deriving those
   two citations is the cheapest way to make the only positive gate results in the project
   independently checkable - which is why UNK-0023 still ranks first on the frontier.
7. The candidate architecture paper has no text layer (image-only PDF); its claim set was
   transcribed from rasterised pages. It reports no backtest, P&L, fill or latency measurement, and
   its own three cost statements do not reconcile with each other: at its stated 300 ms cadence and
   its own ~240-token state, $0.042 per million input tokens implies ~$87/month, while its stated
   "near one hundred-thousandth of a dollar per block" implies ~$864/month, neither compatible with
   its stated $10-25/month.
8. M1-A's stated reason "the paper and research OS were not retrievable" is now false: both are in
   this repository, hashed in `M1/raw/source_manifest.json`. The verdict is unchanged because the
   empirical blockers are independently sufficient (UNK-0030, ASM-0018).
9. **Both execution styles of a top-of-book H2 signal are now measured on Nasdaq large-tick names,
   and both are negative for structural reasons rather than for want of a better model.** Aggressive:
   a 4.1011 bps executed round trip against a 0.0794 bps directional response, with a clairvoyant
   ceiling of only 0.822/0.219 bps per trade (floor/accessible). Passive (M2-1, EVD-0069): 0.82% of
   attempts fill inside the signal's own 1 s life, the fills are selected against by −0.973 bps of
   midpoint drift at 1000 ms and −0.884 bps already at 10 ms (against an unconditional +0.079 bps),
   the reference policy is negative before any fee, no declared state or queue band is positive, and
   the optimistic bound that grants perfect queue position is worse. The two failures are the two
   sides of one geometry: the friction of participating is a tick plus a fee floor, and the flow that
   reaches a resting order is the flow that is moving the price through it.
10. **The aggressive-execution friction of a Nasdaq large-tick round trip is measured, and it
   dominates every top-of-book signal that has been assembled so far.** On the 2019-07-30
   development day, in the candidate's own population (one-tick median Nasdaq book spread,
   top-decile dollar volume, 33 names, 737,768 decisions at a 1 s grid), the executed round trip is
   4.1011 bps (2.5730 spread paid + 1.5281 exchange/statutory floor fee) against a 0.0794 bps mean
   side-signed mid move at 1000 ms. Two model-free facts make this decisive rather than merely
   discouraging: (a) with **perfect foresight** of the future quotes at every instant the aggressive
   round trip nets +0.822 bps per trade at the structural floor and +0.219 bps per trade on the
   accessible broker path, on 1.18% of instants — prediction cannot exceed clairvoyance; and
   (b) perfect abstention with the imbalance-dictated side is worth 0.0052 bps per observation,
   0.13% of the required move. The registry of these quantities is
   `M2/output/univproxy/M2_0_6_VERDICT.json`; the durable consequence for M1 is that any aggressive
   Nasdaq row must now evidence a signal of the same order as its friction before it is treated as
   pending rather than pre-falsified.
11. **The microprice row was put through that test and failed it: the top-of-book Nasdaq large-tick
   sequence is closed.** The registered Stoikov micro-price — recovered from source material and
   estimated causally (expanding prior-session window, no imputation) rather than substituted by the
   weighted mid-price — earns **+0.2333 bps** of side-signed mid move at the longest horizon the
   candidate declares (15 s, CI [0.214, 0.253]) against a **3.9875 bps** structural round trip, and
   **+0.5836 bps** in its strongest preregistered state (2.98% of instants, CI [0.484, 0.683]): 17×
   and 5× too small respectively. Three readings fix the interpretation. It is *not* an uplift on the
   queue-imbalance row at the shared horizon (0.0745 vs 0.0794 bps at 1 s), because the calibrated
   direction agrees with the imbalance sign on 94.85% of instants. The limitation is *not* the
   cascade's causality: a non-causal whole-day refit buys 8.0% more signal. And it is *not* a
   prediction-quality problem: with **perfect foresight** of the future executable quotes the same
   instants net only +1.6275 bps per trade at the structural floor (+0.7012 bps on the accessible
   path) on 19.51% of instants. Friction, not forecasting, closes this venue family. Detail:
   `M2/output/M2_MICRO_MATERIALITY_STATUS.md`; machine-readable registry
   `M2/output/micro/calculations/micro_materiality.json`.

## Critical Unknowns / Blockers

Issue classification is two-dimensional (see Issue Stages below): a resolution *method* and a
resolution *stage*. Before this pass every empirical unknown was treated as M1-blocking, which
made M1 unclosable by construction - the milestone required measurements that only M2 can
produce. The migration moved 9 issues to M2_MEASUREMENT, 1 to POST_M2 and 4 to NON_BLOCKING,
leaving 19 M1-blocking issues.

<!-- GENERATED:frontier -->
| leverage | tier | issue | method | affected | decision prevented |
|---|---|---|---|---|---|
| 24.0 | 1 | `UNK-0002` | PUBLIC_RESEARCH | 6 | Any queue-position or fill model for passive CME candidates (KG2/KG3). |
| 24.0 | 1 | `UNK-0018-HYPERLIQUID` | PUBLIC_RESEARCH | 2 | Replay validity for the Hyperliquid seconds-scale tuples (KG2). |
| 24.0 | 1 | `UNK-0023-CME-DOCS` | PUBLIC_RESEARCH | 5 | KG1/KG2 evidence quality for the CME rows, and auditability of the MDP feasibility claim. |
| 24.0 | 1 | `UNK-0023-LIT` | PUBLIC_RESEARCH | 6 | KG1 for candidates that would borrow the order-flow mechanism, and auditability of the mechanism-evidence row  |
| 24.0 | 1 | `UNK-0027-CME-INDEX` | PUBLIC_RESEARCH | 3 | KG5 for the ES H1, ES H3 and NQ H3 rows; also determines which historical data and fee line items apply. |
| 18.0 | 3 | `UNK-0018-NASDAQ` | EXTERNAL_ACTION | 3 | Causal replay and therefore queue/fill claims for the Nasdaq equity rows (KG2). |
| 18.0 | 3 | `UNK-0033` | EXTERNAL_ACTION | 4 | All-in per-share cost for every equity tuple, and therefore the cost floor used in KG3. |
| 16.0 | 1 | `UNK-0023-EXCH-OTHER` | PUBLIC_RESEARCH | 3 | Evidence quality for the Eurex tuple and for the options candidate's Gate-2 status. |
| 16.0 | 1 | `UNK-0027-CME-OTHER` | PUBLIC_RESEARCH | 2 | KG5 for those rows. |
| 13.5 | 2 | `UNK-0009-MECH-CME` | PUBLIC_RESEARCH | 5 | KG1 for every CME candidate (mechanism plausibility, not profitability). |
| 12.0 | 1 | `UNK-0009-ECON-CRYPTO-SPOT` | PUBLIC_RESEARCH | 4 | Whether the crypto spot branch can be killed on materiality rather than left blocked: a cost level alone is no |
| 12.0 | 3 | `UNK-0010` | EXTERNAL_ACTION | 3 | Net-edge feasibility for the Hyperliquid H3/H4 candidates. |

Actionable frontier items: 27. Items awaiting an external answer or a frozen spec: 3. Measurement specifications: 7. External request packets: 14.
<!-- /GENERATED:frontier -->

## Issue Stages

<!-- GENERATED:stages -->
| resolution stage | count | meaning |
|---|---|---|
| M1_BLOCKING | 39 | must be answered before M1 can close |
| M2_MEASUREMENT | 11 | preregistered M2 experiment; does not block M1 |
| POST_M2 | 1 | matters only after M2 shows positive net EV |
| NON_BLOCKING | 5 | tracked; no gate depends on it |

| resolution method | count |
|---|---|
| PUBLIC_RESEARCH | 22 |
| EXTERNAL_ACTION | 15 |
| EMPIRICAL_MEASUREMENT | 12 |
| DEFERRED | 5 |
<!-- /GENERATED:stages -->

## Immediate Next Actions

Ranked by decision leverage (impact x kill potential x work tier / effort), recomputed
every pass from `M1/work/frontier.json`:

<!-- GENERATED:next_actions -->
1. **UNK-0002** (PUBLIC_RESEARCH, tier 1, leverage 24.0): The allocation algorithm that applies to the named product and order type, with its version
2. **UNK-0018-HYPERLIQUID** (PUBLIC_RESEARCH, tier 1, leverage 24.0): The archive's file schema and a sample hour, plus a stated rule for missing hours.
3. **UNK-0023-CME-DOCS** (PUBLIC_RESEARCH, tier 1, leverage 24.0): Primary CME pages (MDP product documentation, rulebook chapter, data-services product page) captured with dates.
4. **UNK-0023-LIT** (PUBLIC_RESEARCH, tier 1, leverage 24.0): An authoritative record for the order-flow-imbalance claim (publisher metadata plus an author or repository version) establishing its sample and venue.
5. **UNK-0027-CME-INDEX** (PUBLIC_RESEARCH, tier 1, leverage 24.0): A contract/roll specification: which expiry, the roll rule (volume or open-interest crossing, day offset) and how a continuous series is built without lookahead.
6. **UNK-0018-NASDAQ** (EXTERNAL_ACTION, tier 3, leverage 18.0): The ITCH message specification's timestamp section plus a sample day whose ordering and sequence fields validate against the project's contract.
<!-- /GENERATED:next_actions -->

## Readiness

<!-- GENERATED:readiness -->
Ready for M1-B? **NO** - zero candidates pass all five gates; the frontier still holds 27 M1-blocking items.
Ready for M1-D1? **NO** - M1-B is not authorized and no synthesis artifact exists, so no finalists can be compared.
Ready for M2? **NO** - M2 requires a selected candidate plus a locked cost configuration and an order-level dataset; the frontier holds both.
Ready for shadow trading? **NO** - a shadow run requires a chosen candidate, instrument and measured cost envelope.
Ready for capital? **NO** - no candidate has evidenced net edge.
<!-- /GENERATED:readiness -->

## Canonical Artifacts

Machine-readable M1 state (canonical; regenerate with `python3 M1/src/materialize.py`):

- `M1/data/` - source_registry, evidence_ledger, venue_facts, mechanisms, candidate_tuples,
  data_feasibility, execution_envelopes, technology_fit, discrepancies, open_questions,
  dead_candidates, assumptions, kill_gates, experiments, hypotheses.
- `M1/output/` - candidate_gate_status, evidence_coverage, data_feasibility_verdicts,
  cost_envelopes, venue_cost_reference, latency_feasibility, hard_constraint_survivors,
  hard_constraint_eliminations, dominated_candidates, blocker_priority, status_derivation_review,
  M1_D0_READINESS.md, M1_D1_BLOCKED.md, M1_STATE_SUMMARY.json.
- `M1/validation/report.{json,md}` - validator output (rules V1-V13).
- `M1/raw/source_manifest.json` - SHA-256 of every raw input; copies under `M1/raw/`.
- `M1/derived/jev_paper_pages/` - rasterised paper pages used to read an image-only PDF.
- Closure orchestrator: `M1/orchestrator/{schemas,blocker_card,priority,frontier,transitions,
  patch,resolvers,controller}.py`; work artefacts under `M1/work/` (frontier.json, cards/,
  patches/, external_requests/, m2_specs/); `M1/output/M1_CLOSURE_STATUS.json`,
  `M1/output/M1_EXTERNAL_ACTION_QUEUE.md`, `M1/output/closure_loop_log.md`.
- Code: `M1/src/corpus/*` (declarative data incl. `corpus/staging.py` and
  `corpus/patches/*`), `M1/src/{costs,candidate_gates,coverage,latency,pareto,envelopes,
  gate_engine,readiness,report,paper_arithmetic,materialize,validate,build_manifest}.py`,
  tests under `M1/tests/`.
- Root registries: `EVIDENCE_LEDGER.csv`, `ASSUMPTIONS.csv`, `HYPOTHESES.csv`, `EXPERIMENTS.csv`,
  `DISCREPANCIES_AND_UNKNOWNS.md`, `DEAD_ENDS.md`, `OPEN_QUESTIONS.md`, `WATCHLIST.md`,
  `ROADMAP.md`, `DECISIONS.md`, `CHANGELOG.md` (generated files are byte-identical to their
  canonical counterparts and validated so).
- Methodology source of truth: `trading_research_os_v0.2/` (README, docs/00-08, config, templates),
  unchanged by this materialisation.

## Counts

<!-- GENERATED:counts -->
| status | count |
|---|---|
| ALIVE | 0 |
| WEAK | 3 |
| UNKNOWN | 16 |
| DEAD | 10 |

Registered candidate rows: 29 (24 tradable tuples + 5 non-tuple registrations). Verified sources: 96 (25 report-mediated, 0 with a recoverable URL). Evidence records: 69. M1 frontier items: 27 (7 measurement specs and 14 external requests now outside the frontier). Gate-eligible candidates: 0.
<!-- /GENERATED:counts -->



- `python3 M1/src/build_manifest.py` - hashes raw inputs (only needed if raw inputs change).
- `python3 M1/src/materialize.py` - regenerates every artifact listed above and this file's
  `Last Updated` line.
- `python3 M1/src/validate.py --strict` - rules V1-V18: provenance, numeric provenance, gate
  ceiling and dead/ALIVE integrity, referential integrity, no candidate scoring, id uniqueness,
  source dates, experiment integrity, no imputation, cross-file consistency, raw-manifest hash
  integrity, paper-arithmetic reproducibility, two-dimension issue model, frontier integrity,
  eligibility independence, patch integrity, work-artefact validity. Last run: **PASS**, 0
  failures across 18 rule groups.
- `python3 -m unittest discover -s M1/tests -t .` - 76 tests, OK.
- `python3 M1/orchestrator/controller.py status|frontier|next` - closure orchestration.
- Validator report: `M1/validation/report.md`.

## Superseded / Legacy Artifacts

- `trading_research_os_v0.2/STATUS.md` - legacy/reference. Its knowns/unknowns remain valid in
  substance, but counts and current state now live here; it is no longer updated.
- `deep-research-report.md` - remains the M1 external-evidence artifact and is not superseded, but
  its self-reported reason for incompleteness has been partially invalidated (UNK-0030) and its
  citation tokens are unresolved (UNK-0023).
- `M1-C_M1-D_Handoff.md` - instruction document; its requirements are executed and tracked in
  `M1/output/`, not restated here.
