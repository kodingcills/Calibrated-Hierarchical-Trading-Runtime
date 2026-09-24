# M2-1 PASSIVE EXECUTION FEASIBILITY — TERMINAL REPORT

Candidate: `TUP-NASDAQ-LARGETICK-H2-QIMB-PAS` (parent `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG`)
Experiment: `M2-1-PASSIVE-QIMB` · freeze sha256 `03efd04e032317a19c67105c35ab2196248d616507296246a18e46e52b83e7d0`
Data: free Nasdaq TotalView-ITCH 5.0 sample day 2019-07-30 (DEVELOPMENT, holdout-ineligible) ·
282,229,684 messages · 115 replayed names, 33 of them rule-conformant
As-run inputs and artifact hashes: `M2/experiments/M2-1-PASSIVE-QIMB/run_inputs.json`
Queue identifiability assessment: `M2/output/passive/QUEUE_IDENTIFIABILITY.md`

---

## TERMINAL STATE

**`KILLED`**

The passive monetization of this mechanism is economically dead on the available evidence. Two
precommitted kill conditions fire on the primary population (K2 starvation, K3 adverse-selection
dominance), a third (K6 negligible scale) corroborates, and the optimistic bound built precisely to
test whether the queue model was hiding a viable strategy is negative as well.

---

## PARENT RESULT

`TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` was killed by M2-0.6 (EVD-0067): in its own rule-conformant
population the mean 1000 ms side-signed mid move is **0.0794 bps** against an executed round trip of
**4.1011 bps** (2.5730 spread paid + 1.5281 exchange/statutory floor fee); 0 of 356 declared states
was net-positive; and a clairvoyant trader on the same instants nets only +0.822 bps per trade at the
structural floor and +0.219 bps per trade on the accessible broker path. That result killed the
*execution style*, not the information: the mechanism's directional content was measured and is real,
so a passive entry — which earns the spread instead of paying it — was the only registered,
evidence-backed pivot.

---

## PASSIVE HYPOTHESIS

> Once realistic queue position and fill-conditioned adverse selection are included, can a passive
> entry convert the measured queue-imbalance information into positive executable expected value?

Model: at each frozen M2-0.6 decision instant (one per symbol per second), submit a hypothetical
100-share limit order on the signal's side, **joining the back of the near touch** (best bid for a
buy, best ask for a sell), and let it rest. The question is not whether the signal predicts prices —
that is settled — but whether a real participant is *filled* in the states where the information has
value, and what is left after being selected for that fill.

---

## QUEUE IDENTIFIABILITY

Full assessment and per-component classification: `M2/output/passive/QUEUE_IDENTIFIABILITY.md`.

**Identifiable (`DETERMINISTIC_FROM_FEED`)**: every displayed order's arrival, execution, partial
cancel, delete and cancel-replace carries per-order identity, and the product disseminates payload
messages in engine order, so time priority among displayed orders at one price is reconstructible.
A cancel-replace retires the original and carries a new reference, so it cannot retain its place
(provider specification). A replenished reserve display receives a new timestamp while the
non-displayed portion keeps its timestamp (SEC Release 34-91109, quoted in the identifiability
document), so replenishment moves behind resting orders.

**Not identifiable (`UNOBSERVABLE` / `UNKNOWN`)**: non-displayed interest (no add messages are
published for it; matches appear as `P` prints with no book identity), any priority-preserving order
attribute that displays at one price and ranks at another, and the verbatim ranking rule in force on
the tape date (search exhausted across the rulebook, SEC filings and the Federal Register API). These
are **measured, not assumed**: the replay counts 27,627 priority anomalies (2,202 in the corrected
configuration, 0.81% of the shares executed at our price levels) and counts hidden flow at our level
(1.68M shares) without ever filling from it.

**Direction of the residual error**: ignoring non-displayed flow and requiring displayed FIFO both
make the model *wait longer* than reality, so the conservative fill count is an optimistic-in-the-
wrong-direction... concretely, it is a **lower bound on fills**, and the fills it misses are ones
obtained sooner — i.e. from the same aggressive flow that the optimistic bound shows is adversely
selected. The optimistic bound closes the gap from the other side.

---

## FROZEN MODEL

| element | value |
|---|---|
| order side | `sign(queue imbalance)`; no order when the imbalance is zero |
| order price | join the near touch: best bid for a buy, best ask for a sell |
| size | 100 shares (the ledger's representative order size) |
| queue rule | every displayed order resting at that level at submission is ahead; nothing arriving later is; position tracked per reference through a global arrival sequence, so a later order can never advance us and a cancel-replace moves behind us |
| fill criterion | fill only against executions (E/C) at our price level, in file order, once the displayed quantity ahead is exhausted and the aggressor's executed quantity reaches our position; fill quantity = min(executed, our remaining) |
| partial fills | accumulate on the same order; the first fill anchors the markout and exit clocks |
| TTL | 1000 ms (the mechanism's own H2 horizon) |
| cancellation | none beyond TTL: no signal-based cancel, so no cancel-latency assumption enters the result |
| markouts | 10/25/50/100/250/500/1000 ms from the **fill** timestamp, mid measured after the execution that filled us |
| exit | aggressive at fill + horizon: sell at the best bid after a buy, buy at the best ask after a sell |
| fees | one-sided ledger breakdown; the entry leg is charged no exchange fee (the frozen ledger has no add-liquidity item) and the exit leg is charged remove-liquidity plus statutory charges, plus commission on the accessible path. A verified $0.0018/share add-liquidity credit (SRC-0203, a 2026 card) is reported as a labelled sensitivity only |
| alternative model | `no_queue`: the optimistic upper bound, where any execution at our price reaches us immediately (queue-position penalty set to zero) |

---

## FILL RESULTS

Primary population (33 rule-conformant large-tick names), 737,768 attempts, TTL 1000 ms:

| model | filled attempts | fill rate | filled shares | partial share | median time to fill | median queue ahead |
|---|---|---|---|---|---|---|
| conservative (`fifo`) | **6,067** | **0.822%** | 538,672 | 17.3% | **537 ms** | 700 shares / 5 orders |
| optimistic (`no_queue`) | 31,737 | 4.302% | 2,886,022 | 13.4% | 440 ms | — (position ignored) |

Whole 115-name scope, conservative: 15,768 fills of 2,458,422 attempts (0.641%).

The mechanism of the starvation result, measured rather than inferred: **95.7% of primary attempts
see zero displayed execution at their quoted price level during the order's entire 1 s life**
(median 0 shares, p75 0, p90 0, mean 24.2), and only **1.47%** of attempts receive enough flow at
their price to reach through the queue ahead of them. Hidden (non-displayed) flow at the quoted
level is negligible: mean 1.1 shares, present in 0.5% of attempts. The order quotes the touch, and on
these names the touch is a moving target whose lifetime is comparable to the signal's, so the queue
in front of a resting order is usually never reached at all — let alone before the signal that
motivated the order has decayed.

---

## ADVERSE SELECTION

Primary population, conservative model, side-signed midpoint move measured **from the fill**:

| horizon | mean (bps) | median | 95% CI (block bootstrap) | share > 0 | fill-price markout | gross exit |
|---|---|---|---|---|---|---|
| 10 ms | −0.884 | −0.668 | [−0.991, −0.785] | 10.6% | −0.395 | −1.322 |
| 50 ms | −0.893 | −0.667 | [−0.994, −0.796] | 12.4% | −0.404 | −1.356 |
| 100 ms | −0.907 | −0.668 | [−1.007, −0.816] | 12.7% | −0.419 | −1.382 |
| 250 ms | −0.919 | −0.670 | [−1.039, −0.812] | 14.0% | −0.431 | −1.409 |
| 500 ms | −0.946 | −0.709 | [−1.068, −0.833] | 15.9% | −0.458 | −1.443 |
| 1000 ms | **−0.973** | −0.711 | **[−1.102, −0.867]** | 18.4% | −0.486 | −1.478 |

Optimistic bound, same population: **−0.933 bps at 10 ms**, **−1.019 bps at 1000 ms**
(CI [−1.116, −0.932]), fill-price markout −0.179 bps, gross exit −1.160 bps.

**The controlling comparison** (requested explicitly): the *unconditional* post-decision response in
the signal's direction is **+0.079 bps** at 1000 ms (EVD-0067). The *post-fill* response is
**−0.97 bps**. The fill event does not sample that distribution at random — it selects the states in
which the signal's direction reverses, and the reversal is already complete at 10 ms. This is
fill-conditioned adverse selection, measured deterministically rather than assumed.

Both markouts are reported separately as required: the midpoint markout isolates post-fill drift; the
fill-price markout additionally contains the entry's position relative to the midpoint.

---

## EXECUTION ECONOMICS

`PASSIVE_ENTRY_AGGRESSIVE_EXIT_REFERENCE` — passive entry at the touch, aggressive exit at
fill + horizon. Primary population, 1000 ms exit horizon:

| cost regime | net per filled share (mean) | net per filled share (median) | share of fills positive | EV per attempt (bps) | EV per attempt (USD) |
|---|---|---|---|---|---|
| structural floor | **−2.019 bps** | — | 7.6% | −0.00167 | **−$0.00118** |
| IBKR Pro Fixed (accessible) | −2.924 bps | — | — | −0.00232 | −$0.00164 |
| IBKR Pro Tiered (accessible) | −2.540 bps | — | — | −0.00186 | −$0.00131 |

Optimistic bound at the floor: −1.725 bps per filled share, EV per attempt −$0.00182.

**The policy is negative before any cost**: the gross round trip (no fees at all) is −1.32 bps at
10 ms and −1.48 bps at 1000 ms, because the entry earns roughly a quarter basis point of spread and
gives up roughly a basis point of midpoint.

Aggregate over the primary population's 6,067 fills: gross −$12,574, exit costs $2,176, **net
−$14,750**. Every attempt in the whole day, including the 731,701 that were never filled, is
included in the per-attempt figures above.

**Rebate sensitivity** (labelled, never primary): crediting the verified $0.0018/share Nasdaq
add-liquidity credit changes the conservative per-attempt value from −$0.00118 to **+$0.00014**, and
the optimistic bound from −$0.00182 to +$0.00522. That residual is the exchange's liquidity subsidy,
not the queue-imbalance information: the signal's own contribution to a fill is the −0.97 bps of
midpoint drift. It is also a 2026 rate card applied to a 2019 tape, at a tier the project has not
verified.

---

## ROBUSTNESS

| axis | finding |
|---|---|
| imbalance state | all five declared `\|I\|` bins negative (EV per attempt −$0.00083 to −$0.00161); the extreme bin `\|I\| ≥ 0.8` is the *least* favourable per attempt despite the highest fill rate |
| queue position | all six queue-position bands negative; the nearest band carries only 6 fills and the second 15, so no "front of the queue" corner exists to prefer |
| symbol concentration | fills occur on all 33 names; top-5 names carry 40.9% of filled shares; **3 of 33 symbols positive** (AAL +$2.9k, CTXS +$9.4k, CSCO +$5.5k) against 30 negative — i.e. the losses are broad, not one accident |
| time of day | fills concentrate at the open and close (2,513 of 6,067 in the 09:00 and 15:00 hours) — the two windows where flow is driven at the touch |
| cost sensitivity | the structural floor is the cheapest achievable path and it is already negative; the accessible broker paths add 0.5–0.9 bps per round trip |
| queue-model sensitivity | the optimistic bound, which removes the queue-position penalty entirely, is *more* negative per attempt than the conservative model, not less |
| data/leakage | deterministic replay with 0 orphan events, 0 duplicate references, 0 level-accounting mismatches, 0 exits unavailable; the speculative fixtures (20 unit tests) pin the fill mechanics |

---

## FAILURE MODES TESTED

1. **Starvation (K2)** — fires. 0.822% of attempts fill inside the mechanism's own 1 s horizon; the
   median attempt sees no executed flow at its quoted price at all. Passive execution cannot
   monetize an H2 signal whose horizon expires before the queue is reached.
2. **Adverse-selection dominance (K3)** — fires, in both models. The midpoint moves −0.97 to
   −1.02 bps against the fill (CIs exclude zero), against a +0.079 bps unconditional response in the
   same direction. This is the classic passive failure mode and it is measured, not assumed.
3. **Unrealistic priority dependency (K5)** — tested and *rejected as the explanation*: the
   optimistic bound grants perfect queue position and is worse, so the strategy does not depend on
   an inaccessible queue position; it fails with one.
4. **Executable net negative (K4)** — the per-share and per-attempt quantities are negative at the
   structural floor on the conservative model. On the optimistic bound the *rebate-adjusted*
   per-attempt figure turns positive, so K4's third clause (the rebate failing to flip the sign) is
   not met there; K4 is therefore **not** the basis of the verdict — K2, K3 and K6 are.
5. **Economic scale (K6)** — fires: expected value is negative and, even in the most favourable
   configuration measured, is a fraction of a cent per attempt.
6. **Identifiability (K1)** — tripped by the letter of the precommitted clause (priority anomalies
   exceed 1% of fill events) and resolved as **bounded, not blocking**: the anomalous events are
   executions of later-arriving orders while earlier quantity still rests, which can only make this
   model wait longer; the optimistic bound is immune to that error and is negative; and
   `level_state_mismatches` — the check that catches queue-accounting defects — is 0 across the
   whole tape.

**Not tested, and deliberately so**: passive exit (a second queue problem), inventory management or
market making (a different mechanism), any fitted or learned fill model, any threshold selection,
and Jev/System-One (inadmissible here: a classical same-information policy has not established a
credible problem).

---

## DECISION

**`KILLED`**, on the precommitted rule, in the primary population, under the primary (conservative)
model: `K2` fires (0.822% fill rate against a 1% threshold), `K3` fires (−0.973 bps midpoint markout,
CI [−1.102, −0.867]), `K6` fires (negative expected value below a cent per attempt), and `K4` fires
on its first two clauses. The optimistic bound independently fires `K3` (−1.019 bps, CI
[−1.116, −0.932]), so the verdict does not rest on the queue model's conservatism.

The economics are not marginal, and they are not a regime artifact in the way that matters: the gross
passive-entry/aggressive-exit result is negative *before any fee*, the selection is complete within
10 ms of the fill, no declared state or queue band is positive, and 30 of 33 symbols lose. The
mechanism's information is real — 0.0794 bps at 1000 ms — but that is two orders of magnitude below
the friction of either execution style.

**Modern-data value of information (§32): zero for this candidate.** No purchasable parameter could
move the decision: the signal would have to be 30–50× larger (no modern regime provides that), the
fill selection would have to reverse sign (a market-structure change that measured data contradict),
and the friction components are the Reg NMS tick and the exchange/statutory fee floors, which are not
regime-dependent. The one remaining external fact — whether a Nasdaq add-liquidity credit was in
force on the tape date — is a published fee schedule, not a data purchase, and even verified it buys
a venue subsidy rather than an edge from this signal.

---

## NEXT ACTION

**Stop the H2 Nasdaq large-tick queue-imbalance family and return to candidate selection.**

Both execution styles of `TUP-NASDAQ-LARGETICK-H2-QIMB-*` are now dead on measured evidence —
aggressive by EVD-0067 (friction 52× the signal), passive by EVD-0069 (starvation plus
adverse-selection dominance). The next action is not another formulation of this mechanism: it is to
resume M1 candidate selection with the reusable lesson this pair of experiments has produced, namely
that a top-of-book signal at H2 must demonstrate a magnitude of the same order as the round trip it
faces *before* any execution model is built for it. If the project wants to test venue
liquidity-credit capture, that is a different candidate requiring its own registration, its own
always-resting baseline, and verification of the 2019 fee schedule first.
