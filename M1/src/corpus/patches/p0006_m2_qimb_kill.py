"""Code-authored evidence patch P-0006: the M2-0.6 falsification of the Nasdaq queue-imbalance
aggressive candidate.

Provenance: the project's own frozen experiment `M2-0-6-UNIVPROXY`, run on 2026-09-23 against the
free Nasdaq TotalView-ITCH 5.0 sample day 2019-07-30 (raw sha256
``c65784c4c28735901ae442dc00e215834218a359bc12a139ab4eec209bc2d4a``), with its contract sealed and
hashed before any proxy-run observation was inspected. Every number below is read from that run's
frozen artifacts; nothing is inferred from an external source and nothing is extrapolated.

What this patch establishes, in decision terms:

* In the candidate's **own** population (top-dollar-volume Nasdaq-listed common stock whose Nasdaq
  book has a one-tick median spread - the frozen rule's own sentences on a one-day proxy of its
  60-day lookback; 33 names, 737,768 decision observations), the mean side-signed mid move at
  1000 ms is 0.0794 bps against an executed round trip of 4.1011 bps (2.5730 spread paid plus
  1.5281 structural-floor fee). The signal supplies 1.94% of the hurdle; the ratio
  required/signal is 51.64 pooled and 10.69 in the best declared state.
* **0 of 356 declared states** (bin x spread class x price band x horizon, >= 100 observations)
  has a positive mean result under the structural cost floor; the best state loses 0.975 bps per
  trade.
* The bound that ends the argument: with **perfect foresight** of the future bid and ask at every
  decision instant (ORACLE_UPPER_BOUND), the aggressive round trip nets +0.822 bps per trade under
  the structural floor and +0.219 bps per trade under the accessible IBKR fixed schedule, on 1.18%
  of instants. Perfect abstention with the imbalance-dictated side (QIMB_CONSTRAINED_BOUND) is
  worth 0.0052 bps per observation - 0.13% of the required move.
* The result is **not** a population artifact: the inherited M2-0 compute scope (top 61 by
  order-add message count) gives 56.9x, statistically indistinguishable from 51.64x, and a broader
  115-name dollar-volume scope that contains the highest-priced names (AMZN at $1898, GOOGL at
  $1230, BKNG at $1915, ISRG at $533) gives 117.3x with a best cell of 6.55x.

Why this is a kill rather than a cost-level argument (the standard D-0022 sets): the record below
does not rest on a fee level or on absent evidence. It rests on a **measured upper bound on the
plausible gross effect** - a clairvoyant trade on the same instants at the same costs - which is
itself smaller than the friction the strategy must pay, together with a measured signal magnitude
that supplies under 2% of that friction. No predictor can exceed clairvoyance.

What it does NOT establish: modern-regime transfer (one 2019 low-volatility session; the kill is
robust to a move-scale multiplier of about 2.1x on the best-state condition and about 5x on the
pooled condition, and no further); passive execution, which is untested here because it requires a
queue-aware fill model; and universe membership, which remains blocked on the 60-day lookback and
the point-in-time reference.
"""

from __future__ import annotations

PATCH_ID = "P-0006"
ACCESS = "2026-09-23"

FREEZE_SHA = "4fc098a36550854e93451e4d5408474fe771fc9ce9081d50ad0b71a20c32b38b"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0018-NASDAQ", "UNK-0027-NASDAQ-LARGETICK"],
        "candidate_ids": ["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"],
        "new_sources": [{
            "source_id": "SRC-0242",
            "title": "M2-0.6 universe-proxy falsification of TUP-NASDAQ-LARGETICK-H2-QIMB-AGG "
                     "(project's own frozen experiment M2-0-6-UNIVPROXY)",
            "authors_or_org": "This project (M2 autonomous run)",
            "publication_date": "2026-09-23",
            "access_date": ACCESS,
            "date_basis": "experiment run and frozen on 2026-09-23; freeze manifest sealed before "
                          "any proxy-run observation was inspected",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "US equities",
            "venue": "Nasdaq (XNAS), Nasdaq-only reconstructed book",
            "sample_period": "one trading day, 2019-07-30, 09:30:00-16:00:00",
            "sample_size": "115 replayed symbols (top-120 dollar volume inside the single-day top "
                           "liquidity decile, less 5 names lost to a reported price-floor guard); "
                           "primary population 33 one-tick names; 737,768 signal-defined decision "
                           "observations at a 1 s decision grid",
            "methodology": "Deterministic market-by-order replay of Nasdaq TotalView-ITCH 5.0 into "
                           "a causal 1 s decision grid with 100/250/500/1000 ms labels and a "
                           "0-1000 ms arrival-delay sweep; queue imbalance at the touch; aggressive "
                           "cross-to-cross execution at the far touch; the frozen cost ledger "
                           "M2-COST-LEDGER-v1; ORACLE_UPPER_BOUND and QIMB_CONSTRAINED_BOUND "
                           "computed from realised future quotes",
            "gross_or_net": "NET (after modelled spread, exchange and statutory costs)",
            "independent_replication": None,
            "limitations": "One 2019 development day, permanently non-holdout; the population is a "
                           "single-day proxy of two of the frozen rule's criteria, not universe "
                           "membership (the 60-day lookback and the point-in-time reference remain "
                           "unsecured); 2026 rate cards are applied to a 2019 tape to validate "
                           "arithmetic and component ordering, not to reconstruct 2019 economics; "
                           "idealized fills with no slippage, impact or queue effect, which makes "
                           "every number optimistic; no modern-regime claim transfers.",
            "raw_citation_token": "code:P-0006",
            "local_path": "M2/output/M2_AUTONOMOUS_STATUS.md",
            "sha256": FREEZE_SHA,
            "status": "PARTIAL",
            "claim_scope": "The measured aggressive-execution economics of the queue-imbalance "
                           "signal in the candidate's own population on one Nasdaq development "
                           "day, including the clairvoyant upper bound and the structural-cost-floor "
                           "verdict.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0067",
            "claim": "In the candidate's own population - Nasdaq-listed common stock with a "
                     "one-tick median Nasdaq book spread and top-decile dollar volume - the mean "
                     "side-signed mid move over 1000 ms is 0.0794 bps against an executed round "
                     "trip of 4.1011 bps, so the required/signal ratio is 51.64 pooled and 10.69 "
                     "in the best of 356 declared states; none of those states has a positive mean "
                     "result under the structural cost floor (best state -0.975 bps per trade). "
                     "With perfect foresight of the future quotes at every decision instant, the "
                     "aggressive round trip nets +0.822 bps per trade at the structural floor and "
                     "+0.219 bps per trade on the accessible broker path, on 1.18% of instants; "
                     "perfect abstention with the imbalance-dictated side is worth 0.0052 bps per "
                     "observation, 0.13% of the required move. The same verdict holds in the "
                     "inherited message-count scope (56.9x) and in a broader 115-name "
                     "dollar-volume scope that includes the highest-priced names (117.3x, best "
                     "cell 6.55x).",
            "source_id": "SRC-0242",
            "candidate_ids": "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
            "mechanism_id": "MECH-QIMB",
            "venue_id": "VEN-NASDAQ-CONT",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "WEAKENS",
            "methodology": "Deterministic replay and cost arithmetic; the ceiling is computed from "
                           "the realised future quotes themselves, so it does not depend on any "
                           "model, threshold or fitted parameter. 23 calculate-stage and 9 "
                           "feasibility reconciliation checks passed with 0 failures in each run.",
            "sample": "33 rule-conformant names, 737,768 signal-defined observations at 1000 ms; "
                      "115-name scope, 2,458,422 signal-defined observations",
            "temporal_scope": "2019-07-30 (DEVELOPMENT, holdout-ineligible); measured move scale "
                              "0.847 bps per second, about 20.6% annualised",
            "gross_or_net": "NET (after spread and the exchange/statutory fee floor)",
            "limitations": "One development day; idealized fills; 2026 fee cards on a 2019 tape; "
                           "the population is a proxy, not membership; the kill is robust to a "
                           "move-scale multiplier of about 2.1x on the best-state condition and "
                           "about 5x on the pooled condition, and beyond that only a modern-regime "
                           "measurement can decide. Passive execution is not tested and is not "
                           "falsified by this record.",
            "decision_implication": "KG3_EXECUTION fails for this candidate: the aggressive "
                                    "monetization of a signal whose measured information is about "
                                    "2% of the tick-plus-fee friction cannot be rescued by "
                                    "prediction, and the purchase of modern order-level data would "
                                    "not change that decision for this candidate.",
            "contradicts_mechanism": "NO",
            "observed_market": "US equities",
            "observed_venue": "VEN-NASDAQ-CONT",
            "observed_instrument_or_universe": "top-dollar-volume Nasdaq-listed common stock with a "
                                               "one-tick median Nasdaq book spread (one-day proxy "
                                               "of NASDAQ-LARGETICK-QIMB-UNIV-v1)",
            "observed_period": "2019-07-30",
            "observed_horizon": "H2 (100 ms - 1 s)",
            "candidate_link_reason": "Same venue, instrument class, mechanism, horizon and "
                                     "execution style as the linked candidate; the experiment was "
                                     "run specifically to test whether the candidate's own "
                                     "population changes its economics, and it does not.",
            "transfer_status": "SAME_POPULATION_PROXY",
            "verification_status": "FROZEN_PRECOMMITTED_REPRODUCIBLE",
        }],
        "modified_claims": [{
            "claim": "The M2-0 compute scope (top 61 by order-add message count) may have made the "
                     "aggressive candidate look worse than it is, because that scope is not "
                     "large-tick.",
            "status": "CORRECTED",
            "reason": "Tested directly and rejected: the rule-conformant population gives a "
                      "required/signal ratio of 51.64 against the inherited scope's 56.9, and a "
                      "broader 115-name scope is worse still (117.3). The scope was never the "
                      "binding issue; the tick-plus-fee friction is.",
        }],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [{
            "candidate_id": "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
            "fields": {
                "KG3_EXECUTION": "FAIL",
                "overall_status": "DEAD",
                "status_basis": "KG3_EXECUTION fails on the project's own measured evidence "
                                "(EVD-0067): in the candidate's rule-conformant population the "
                                "signal supplies 1.94% of the executed round trip, no declared "
                                "state is net-positive under the structural cost floor, and a "
                                "clairvoyant trader on the same instants nets 0.219 bps per trade "
                                "on the accessible broker path.",
                "kill_gate": "KG3_EXECUTION",
                "kill_reason": "Aggressive execution cannot clear the tick-plus-fee friction: "
                               "measured signal 0.0794 bps against a 4.1011 bps round trip, with a "
                               "measured clairvoyant ceiling of 0.219 bps per trade on the "
                               "accessible path. Predicted for this candidate by the frozen rule's "
                               "own literature, which defines its large-tick universe as names "
                               "where the tick is economically large relative to price.",
                "resurrection_condition": "A rule-conformant modern measurement in which the "
                                          "pooled required/signal ratio is at or below 5, which "
                                          "requires both a materially higher move scale and a "
                                          "materially higher price level for the universe's names "
                                          "than the measured 2019 session.",
            },
        }],
        "proposed_gate_changes": [{
            "candidate_id": "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
            "gates": ["KG3_EXECUTION"],
            "from_value": "BLOCKED",
            "to_value": "FAIL",
            "reason": "EVD-0067: the execution requirement is not merely unmeasured, it is measured "
                      "and failed in the candidate's own population.",
        }],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "KILLS",
        "reason": "The candidate's aggressive monetization is rejected on the project's own frozen "
                  "evidence, with a measured upper bound (perfect foresight) below the friction it "
                  "must pay.",
        "verification_notes": "Contrary evidence was searched before this patch was written: the "
                              "experiment was designed as a falsification of the opposite "
                              "hypothesis (that the M2-0 scope, and not the mechanism, was the "
                              "problem), the highest-priced and most favourable strata were "
                              "examined explicitly, the cost floor was used as the cheapest "
                              "achievable path, and the two known defects in the inherited M2-0 "
                              "execution table were corrected in the direction that is worse for "
                              "the candidate. Every number is reproduced from frozen artifacts "
                              "whose hashes are recorded in "
                              "M2/experiments/M2-0-6-UNIVPROXY/run_inputs.json.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
