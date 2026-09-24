"""Code-authored evidence patch P-0009: the M2-2 microprice materiality result.

Provenance: the project's own frozen experiment `M2-2-MICRO-MATERIALITY` (contract sealed at
`M2/experiments/M2-2-MICRO-MATERIALITY/freeze.json`, sha256
``89f84b29e0a509ee77838dcbddc8b57650bcf3ca4635fb75753445b3edf6a6ee``), run on the same free
Nasdaq TotalView-ITCH 5.0 development day (2019-07-30) as EVD-0067 and EVD-0069 but on the
candidate's own H2-H3 horizon band (100 ms - 15 s) rather than the 1 s grid the queue-imbalance
rows were measured on. Every number is read from that run's frozen artifacts.

What this patch establishes:

* The registered estimator was recovered from its own source material rather than substituted:
  the Stoikov micro-price ``p_micro = mid + g1(X)`` with ``g1(X) = E[mid(tau_1) - mid(t) | X]`` and
  ``X = (imbalance bin, spread class)``, estimated with an expanding prior-session window (5-minute
  refit, 200 prior resolved observations per cell). The weighted mid-price, raw imbalance and any
  learned predictor are excluded by the frozen contract.
* Pooled, the microprice direction earns **+0.2333 bps at 15000 ms** (95% block-bootstrap CI
  [0.2142, 0.2530]) against a **3.9875 bps** structural round trip: **R_pooled = 17.09**. The
  horizon term structure is monotone but decelerating (+0.0130 at 100 ms, +0.0745 at 1000 ms,
  +0.1772 at 5000 ms, +0.2194 at 10000 ms), and the required move is horizon-invariant because it is
  set by the tick and the fee floor.
* The strongest preregistered state is `imbalance in [0.8,1.0] x ONE_TICK` at 15000 ms:
  **+0.5836 bps** (CI [0.4842, 0.6831]) on **2.98%** of the direction-defined instants, giving
  **R_best = 5.02**. The strongest magnitude band (`abs(microprice-mid)/half_spread >= 0.20`,
  18.2% of instants) gives R = 7.32.
* The clairvoyant ceiling closes the escape route: with perfect foresight of the future executable
  quotes at every instant, the aggressive round trip nets **+1.6275 bps per trade at the structural
  floor** (+0.7012 bps on the accessible broker path) on 19.51% of instants, against the same
  3.9875 bps hurdle. Prediction cannot exceed clairvoyance, and clairvoyance captures 41% of one
  round trip at the floor.
* vs the queue-imbalance row it is **not an uplift at the shared horizon**: at 1000 ms the
  microprice direction is worth 0.0745 bps against QIMB's 0.0794 bps (0.94x). The microprice is
  materially larger only at the long end of its own band (2.94x at 15000 ms) and it is still 5x
  short of its own friction there.

What it does NOT establish: any modern-regime or out-of-sample result; any claim that the mechanism
carries no information (it predicts a real, statistically clear drift at long horizons - the
information is present, weak and not executable); any passive, inventory, queue-aware or learned
formulation (none was built or tested); any re-derivation of M2-0, M2-0.5, M2-0.6 or M2-1.
"""

from __future__ import annotations

PATCH_ID = "P-0009"
ACCESS = "2026-09-24"
FREEZE_SHA = "89f84b29e0a509ee77838dcbddc8b57650bcf3ca4635fb75753445b3edf6a6ee"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0018-NASDAQ", "UNK-0027-NASDAQ-LARGETICK"],
        "candidate_ids": ["TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG"],
        "new_sources": [{
            "source_id": "SRC-0245",
            "title": "M2-2 microprice economic-materiality gate for TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG "
                     "(project's own frozen experiment M2-2-MICRO-MATERIALITY)",
            "authors_or_org": "This project (M2 autonomous run)",
            "publication_date": "2026-09-24",
            "access_date": ACCESS,
            "date_basis": "experiment frozen and run 2026-09-24; the freeze manifest was sealed "
                          "before any canonical economics of this experiment were inspected",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "US equities",
            "venue": "Nasdaq (XNAS), Nasdaq-only reconstructed book",
            "sample_period": "one trading day, 2019-07-30, 09:30:00-16:00:00",
            "sample_size": "115 replayed symbols; primary population 33 one-tick rule-conformant "
                           "names; 772,200 decision instants at a 1 s grid, of which 726,943 carry "
                           "a causal microprice direction; horizons 100 ms - 15 s",
            "methodology": "The registered Stoikov first-step micro-price (p = mid + g1(X), "
                           "X = (imbalance bin, spread class)) with an expanding prior-session "
                           "calibration (5-minute refit, 200 prior resolved observations per cell, "
                           "no imputation), evaluated as the side-signed future mid move; the "
                           "M2-0.6 aggressive cross-to-cross arithmetic, structural cost floor and "
                           "clairvoyant oracle reused unchanged; the replay engine reused with one "
                           "added derived column (the size of the next mid-price change) and no "
                           "changed column",
            "gross_or_net": "NET (after spread, exchange and statutory costs) for the hurdle and "
                            "the oracle; the measured signal itself is a gross mid-to-mid move",
            "independent_replication": None,
            "limitations": "One 2019 low-volatility development day; a single-day proxy of the "
                           "universe rule rather than membership; 2026 rate cards on a 2019 tape; "
                           "only the first step of the Stoikov estimator is computed (the sign, on "
                           "which the measured quantity depends, is unchanged by the higher-order "
                           "terms); only the aggressive execution style is evaluated.",
            "raw_citation_token": "code:P-0009",
            "local_path": "M2/output/M2_MICRO_MATERIALITY_STATUS.md",
            "sha256": FREEZE_SHA,
            "status": "PARTIAL",
            "claim_scope": "Measured realized predictive magnitude of the registered microprice "
                           "signal, the structural hurdle it faces, and the clairvoyant ceiling on "
                           "the same instants, in the candidate's own population and horizon band.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0070",
            "claim": "The registered Stoikov-style microprice direction earns +0.2333 bps of "
                     "side-signed mid move at its best preregistered horizon (15000 ms, 95% CI "
                     "[0.2142, 0.2530]) against a 3.9875 bps structural round trip, i.e. 5.9% of "
                     "the friction (R_pooled = 17.09). The strongest declared state - imbalance in "
                     "[0.8,1.0] with a one-tick spread, at 15000 ms - earns +0.5836 bps (CI "
                     "[0.4842, 0.6831]) on 2.98% of the direction-defined instants "
                     "(R_best = 5.02). At the queue-imbalance row's own horizon the microprice is "
                     "not an uplift: 0.0745 bps at 1000 ms against 0.0794 bps for QIMB. With "
                     "perfect foresight of the future executable quotes the aggressive round trip "
                     "nets +1.6275 bps per trade at the structural floor and +0.7012 bps on the "
                     "accessible broker path, on 19.51% of instants, against the same 3.9875 bps "
                     "hurdle - the candidate is limited by friction, not by prediction quality. The "
                     "whole-day non-causal refit moves the 15000 ms figure only to +0.2520 bps "
                     "(R = 16.25), so causality is not what holds it back.",
            "source_id": "SRC-0245",
            "candidate_ids": "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
            "mechanism_id": "MECH-MICRO",
            "venue_id": "VEN-NASDAQ-CONT",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "WEAKENS",
            "methodology": "Deterministic replay and cost arithmetic; the estimator's calibration "
                           "uses only strictly earlier session data and cannot see its own or any "
                           "later observation; the oracle is computed from the realized future "
                           "quotes themselves and depends on no model, threshold or fitted "
                           "parameter; uncertainty is a block bootstrap over symbol x 30-minute "
                           "cells; 17 new unit tests plus the 119 pre-existing M2 tests pass, and "
                           "the replay reports DATA_VALID with 0 direction/delta sign mismatches.",
            "sample": "33 rule-conformant names, 726,943 direction-defined decision instants at the "
                      "primary population; 115-name scope, 2,425,329 for the corroborating "
                      "population",
            "temporal_scope": "2019-07-30 (DEVELOPMENT, holdout-ineligible)",
            "gross_or_net": "NET for the hurdle and the oracle; gross mid-to-mid for the signal",
            "limitations": "One development day; a single-day universe proxy; 2026 fee cards on a "
                           "2019 tape; first-step estimator only; the best-state clause clears its "
                           "frozen bar by 0.3% and its confidence interval on the signal implies R "
                           "in [4.28, 6.04], so the best-state condition is met at the point "
                           "estimate and is not resolved by this sample at conventional "
                           "confidence - the pooled condition (17.09 against a bar of 10) and the "
                           "clairvoyant ceiling are what make the verdict decisive. No passive or "
                           "inventory formulation is tested.",
            "decision_implication": "KG3_EXECUTION fails for the microprice candidate: neither its "
                                    "pooled behaviour nor its strongest preregistered state is "
                                    "within 5x of the structural friction, and perfect foresight "
                                    "on the same instants does not clear one round trip. No "
                                    "execution model, modern-data purchase, learned predictor or "
                                    "passive pivot is justified for this candidate.",
            "contradicts_mechanism": "NO",
            "observed_market": "US equities",
            "observed_venue": "VEN-NASDAQ-CONT",
            "observed_instrument_or_universe": "top-dollar-volume Nasdaq-listed common stock with a "
                                               "one-tick median Nasdaq book spread (one-day proxy "
                                               "of NASDAQ-LARGETICK-QIMB-UNIV-v1)",
            "observed_period": "2019-07-30",
            "observed_horizon": "H2-H3 (100 ms - 15 s)",
            "candidate_link_reason": "The experiment exists solely to measure this candidate's own "
                                     "registered estimator against the friction this same "
                                     "population was already measured to charge, before any "
                                     "execution model is built for it (the rule recorded as "
                                     "D-0037).",
            "transfer_status": "SAME_POPULATION_PROXY",
            "verification_status": "FROZEN_PRECOMMITTED_REPRODUCIBLE",
        }],
        "modified_claims": [{
            "claim": "The microprice candidate is a materially different and materially stronger "
                     "signal than the queue-imbalance row of the same family (MECH-MICRO vs "
                     "MECH-QIMB).",
            "status": "CORRECTED",
            "reason": "Measured. The calibrated microprice direction agrees with the imbalance sign "
                      "on 94.85% of instants (100% under a non-causal whole-day refit), so at the "
                      "shared 1000 ms horizon it is worth 0.0745 bps against QIMB's 0.0794 bps. It "
                      "is materially larger only at long horizons (0.2333 bps at 15000 ms, 2.94x "
                      "the QIMB 1 s figure) where its own requirement is still 17.09x.",
        }],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [{
            "candidate_id": "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
            "fields": {
                "KG3_EXECUTION": "FAIL",
                "overall_status": "DEAD",
                "status_basis": "KG3_EXECUTION fails on the project's own measured evidence "
                                "(EVD-0070): the pooled microprice signal supplies 5.9% of the "
                                "structural round trip at the longest horizon the candidate "
                                "declares, the strongest declared state still needs a 5x larger "
                                "signal, and a clairvoyant trader on the same instants nets 1.63 "
                                "bps per trade at the structural floor (0.70 bps on the accessible "
                                "path) against a 3.99 bps round trip.",
                "kill_gate": "KG3_EXECUTION",
                "kill_reason": "The registered microprice direction is real but far too small for "
                               "the friction of participating: +0.2333 bps pooled at 15000 ms "
                               "(R = 17.09) and +0.5836 bps in the best declared state "
                               "(R = 5.02) against a 3.9875 bps round trip, with a clairvoyant "
                               "ceiling of 1.63 bps per trade at the fee floor. Measured on "
                               "282,229,684 messages over the rule-conformant population "
                               "(M2-2-MICRO-MATERIALITY, freeze sha256 89f84b29...).",
                "resurrection_condition": "A rule-conformant measurement in which the pooled "
                                          "required/signal ratio at the candidate's own horizon is "
                                          "at or below 5 - which requires a materially larger "
                                          "per-second move scale or a materially higher price "
                                          "level for the universe's names than the measured 2019 "
                                          "session - or a materially different formulation "
                                          "(passive, inventory, or a state the estimator does not "
                                          "currently use) registered as its own candidate with its "
                                          "own friction measurement first.",
            },
        }],
        "proposed_gate_changes": [{
            "candidate_id": "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
            "gates": ["KG3_EXECUTION"],
            "from_value": "BLOCKED",
            "to_value": "FAIL",
            "reason": "EVD-0070: the execution requirement is measured on the candidate's own "
                      "population and horizon band, and it is failed by a factor of 5 in the "
                      "strongest declared state and 17 pooled.",
        }],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "KILLS",
        "reason": "The candidate's registered estimator carries real but economically immaterial "
                  "information on this population: it is rejected before any execution model is "
                  "built for it, which is exactly the order of work the family's own history "
                  "(EVD-0067, EVD-0069) made mandatory.",
        "verification_notes": "Contrary evidence was searched before this patch was written: the "
                              "estimator was reconstructed from its own source material rather "
                              "than substituted by the weighted mid-price (whose sign is the "
                              "imbalance sign by construction and which the frozen contract "
                              "prohibits); a non-causal whole-day refit was computed explicitly to "
                              "test whether causality was the binding limitation (it is not: 8.0% "
                              "of extra signal); every horizon of the candidate's own H2-H3 band "
                              "was reported rather than the one that looks best; the strongest "
                              "magnitude band and the strongest (imbalance x spread) cell were "
                              "both examined; the hurdle was recomputed on this pass's own "
                              "observation set (3.9901 bps at 1000 ms) rather than copied from "
                              "M2-0.6 (4.1011 bps), and the recomputed value is the SMALLER, i.e. "
                              "the reading more favourable to the candidate; and the best-state "
                              "clause's 0.3% margin and its confidence interval are recorded rather "
                              "than presented as a decisive separation. Every number is reproduced "
                              "from frozen artifacts whose hashes are recorded in "
                              "M2/experiments/M2-2-MICRO-MATERIALITY/run_inputs.json.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
