"""Code-authored evidence patch P-0008: the M2-1 passive-execution result.

Provenance: the project's own frozen experiment `M2-1-PASSIVE-QIMB` (contract sealed at
`M2/experiments/M2-1-PASSIVE-QIMB/freeze.json`, sha256
``03efd04e032317a19c67105c35ab2196248d616507296246a18e46e52b83e7d0``), run on the same free
Nasdaq TotalView-ITCH 5.0 development day (2019-07-30) that produced EVD-0067. Every number is
read from that run's frozen artifacts; nothing is extrapolated.

What this patch establishes:

* A queue-aware deterministic replay of hypothetical passive orders (join the back of the touch,
  100 shares, 1 s TTL, no signal-cancel) over the 33 rule-conformant large-tick names yields
  **6,067 fills from 737,768 attempts (0.82%)**, at a median 537 ms to the first fill behind a
  median queue of 700 displayed shares.
* The fills are **adversely selected**: the side-signed midpoint move from the fill is
  **-0.97 bps at 1000 ms (95% block-bootstrap CI [-1.10, -0.87])** and **-0.88 bps already at
  10 ms**, against an unconditional post-decision response of +0.079 bps in the same direction
  (EVD-0067). The fill event selects the state in which the signal's direction reverses.
* The executable reference policy (passive entry, aggressive exit at the touch) is **negative
  before any cost**: -1.32 bps at 10 ms to -1.48 bps at 1000 ms gross. Net of the structural fee
  floor it is -2.02 bps per filled share; on the accessible broker path -2.92 bps. Zero of the
  five declared imbalance states and zero of the six queue-position bands has positive expected
  value per attempt; 3 of 33 symbols are positive against 30 negative.
* The **optimistic bound** (perfect queue position: any execution at our price reaches us, which
  is immune to any queue-attribution error) confirms the same verdict from the other side: 4.30%
  fill rate, -1.02 bps midpoint markout at 1000 ms (CI [-1.12, -0.93]), -1.73 bps net per filled
  share at the floor, and 0 of 5 states positive.
* The only configuration with a non-negative expected value is one in which the passive entry
  collects a venue add-liquidity credit: +$0.00014 per attempt with the conservative fill rate if
  the verified $0.0018/share credit (a 2026 rate card, SRC-0203) is credited, and +$0.0052 per
  attempt under the optimistic bound. That value is the exchange's liquidity subsidy, not the
  queue-imbalance information, whose own contribution is the adverse drift above.

What it does NOT establish: any modern-regime or out-of-sample result; any passive-exit or
inventory formulation (not tested, and explicitly out of scope for this experiment); any claim that
the mechanism is absent (it is present and weak, as EVD-0067 measures).
"""

from __future__ import annotations

PATCH_ID = "P-0008"
ACCESS = "2026-09-24"
FREEZE_SHA = "03efd04e032317a19c67105c35ab2196248d616507296246a18e46e52b83e7d0"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0007", "UNK-0019"],
        "candidate_ids": ["TUP-NASDAQ-LARGETICK-H2-QIMB-PAS"],
        "new_sources": [{
            "source_id": "SRC-0244",
            "title": "M2-1 queue-aware passive execution feasibility for "
                     "TUP-NASDAQ-LARGETICK-H2-QIMB-PAS (project's own frozen experiment "
                     "M2-1-PASSIVE-QIMB)",
            "authors_or_org": "This project (M2 autonomous run)",
            "publication_date": "2026-09-24",
            "access_date": ACCESS,
            "date_basis": "experiment frozen and run 2026-09-24; the freeze manifest was sealed "
                          "before the canonical replay was executed",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "US equities",
            "venue": "Nasdaq (XNAS), Nasdaq-only reconstructed book",
            "sample_period": "one trading day, 2019-07-30, 09:30:00-16:00:00",
            "sample_size": "115 replayed symbols; primary population 33 one-tick names; "
                           "737,768 primary decision instants, one hypothetical 100-share order "
                           "per symbol-second",
            "methodology": "Deterministic market-by-order replay with per-order queue tracking "
                           "(displayed FIFO at the touch, cancel/delete/replace semantics, "
                           "execution-driven depletion), a five-per-side fill rule and no "
                           "probabilistic fill assumption; midpoint and fill-price markouts "
                           "anchored at the fill; passive-entry/aggressive-exit reference "
                           "economics against the frozen cost ledger",
            "gross_or_net": "NET (after spread, exchange and statutory costs)",
            "independent_replication": None,
            "limitations": "One 2019 low-volatility development day; a single-day proxy of the "
                           "universe rule rather than membership; 2026 rate cards on a 2019 tape; "
                           "the fill model's queue attribution is bounded by measured priority "
                           "anomalies (0.81% of executed shares at our price levels) and by the "
                           "optimistic no-queue bound, which is reported and is itself negative; "
                           "no passive exit, inventory or market-making formulation is tested.",
            "raw_citation_token": "code:P-0008",
            "local_path": "M2/output/M2_PASSIVE_FEASIBILITY_STATUS.md",
            "sha256": FREEZE_SHA,
            "status": "PARTIAL",
            "claim_scope": "Measured queue-aware fill probability, fill-conditioned adverse "
                           "selection and executable passive-entry economics on the development "
                           "tape, with an explicit optimistic queue bound.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0069",
            "claim": "A queue-aware passive order on the rule-conformant large-tick names fills "
                     "rarely (6,067 of 737,768 attempts, 0.82%, median 537 ms behind a median "
                     "queue of 700 displayed shares at a 1 s order lifetime), and the fills it "
                     "does obtain are adversely selected: the side-signed midpoint move from the "
                     "fill is -0.97 bps at 1000 ms (95% CI [-1.10, -0.87]) and -0.88 bps already "
                     "at 10 ms, against an unconditional post-decision response of +0.079 bps. "
                     "The passive-entry/aggressive-exit reference policy is negative before any "
                     "cost (-1.32 to -1.48 bps gross) and -2.02 bps per filled share net of the "
                     "structural floor (-2.92 bps on the accessible broker path); zero of five "
                     "declared imbalance states and zero of six queue-position bands has positive "
                     "expected value per attempt. The optimistic bound that grants perfect queue "
                     "position agrees: 4.30% fills, -1.02 bps midpoint markout at 1000 ms "
                     "(CI [-1.12, -0.93]), 0 of 5 states positive. The only non-negative "
                     "configuration credits a venue add-liquidity rebate, i.e. the value is the "
                     "exchange's liquidity subsidy rather than the queue-imbalance information.",
            "source_id": "SRC-0244",
            "candidate_ids": "TUP-NASDAQ-LARGETICK-H2-QIMB-PAS",
            "mechanism_id": "MECH-QIMB",
            "venue_id": "VEN-NASDAQ-CONT",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "WEAKENS",
            "methodology": "Deterministic queue-aware replay with per-order identity, five "
                           "per-side fill fixtures with exact expected outcomes, 20 unit tests, "
                           "and dependence-aware confidence intervals over symbol x 30-minute "
                           "cells; every reconciliation check passed with zero failures.",
            "sample": "33 rule-conformant names, 737,768 attempts, 6,067 fills; 115-name scope "
                      "for the secondary population",
            "temporal_scope": "2019-07-30 (DEVELOPMENT, holdout-ineligible)",
            "gross_or_net": "NET (after spread and the exchange/statutory fee floor)",
            "limitations": "One development day; a single-day universe proxy; 2026 fee cards on a "
                           "2019 tape; queue attribution bounded by the measured anomaly rate and "
                           "by the optimistic bound; no passive-exit or inventory formulation.",
            "decision_implication": "KG3_EXECUTION fails for the passive candidate: within the "
                                    "signal's own horizon the queue is not reached by flow, and "
                                    "when it is reached the fill is selected against us by more "
                                    "than the entry spread. Modern data would not change this "
                                    "decision, and no purchase is justified for this family.",
            "contradicts_mechanism": "NO",
            "observed_market": "US equities",
            "observed_venue": "VEN-NASDAQ-CONT",
            "observed_instrument_or_universe": "top-dollar-volume Nasdaq-listed common stock with "
                                               "a one-tick median Nasdaq book spread (one-day "
                                               "proxy of NASDAQ-LARGETICK-QIMB-UNIV-v1)",
            "observed_period": "2019-07-30",
            "observed_horizon": "H2 (100 ms - 1 s)",
            "candidate_link_reason": "The experiment exists solely to test whether the same signal "
                                     "survives a passive execution style after its aggressive "
                                     "sibling was killed by EVD-0067; it measures that candidate's "
                                     "own fill mechanics.",
            "transfer_status": "SAME_POPULATION_PROXY",
            "verification_status": "FROZEN_PRECOMMITTED_REPRODUCIBLE",
        }],
        "modified_claims": [],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [{
            "candidate_id": "TUP-NASDAQ-LARGETICK-H2-QIMB-PAS",
            "fields": {
                "KG3_EXECUTION": "FAIL",
                "overall_status": "DEAD",
                "status_basis": "KG3_EXECUTION fails on the project's own measured evidence "
                                "(EVD-0069): queue-aware passive orders fill on 0.82% of attempts "
                                "within the signal's own 1 s horizon, the fills are adversely "
                                "selected by -0.97 bps of midpoint drift, and the executable "
                                "reference policy is negative before costs and at every cost "
                                "floor, with no declared state or queue band positive.",
                "kill_gate": "KG3_EXECUTION",
                "kill_reason": "Passive monetization fails on both sides of the queue-position "
                               "trade-off: patient orders are rarely reached by flow inside the "
                               "signal's life, and orders that are reached immediately (the "
                               "optimistic bound) are selected against by -1.02 bps of midpoint "
                               "drift - more than the entry spread. Measured on 282,229,684 "
                               "messages over the rule-conformant population (M2-1-PASSIVE-QIMB, "
                               "freeze sha256 03efd04e...).",
                "resurrection_condition": "A rule-conformant measurement in which fill-conditioned "
                                          "midpoint markout is non-negative and the queue is "
                                          "reached inside the signal's horizon, or a materially "
                                          "different formulation registered as its own candidate "
                                          "(for example passive exit, inventory, or venue "
                                          "liquidity-credit capture with an always-resting "
                                          "baseline).",
            },
        }],
        "proposed_gate_changes": [{
            "candidate_id": "TUP-NASDAQ-LARGETICK-H2-QIMB-PAS",
            "gates": ["KG3_EXECUTION"],
            "from_value": "BLOCKED",
            "to_value": "FAIL",
            "reason": "EVD-0069: the execution requirement is measured and failed for the passive "
                      "style as well as the aggressive one.",
        }],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "KILLS",
        "reason": "The passive pivot is falsified on the same development tape that killed the "
                  "aggressive branch: the mechanism's information is real but is delivered "
                  "exactly when it is not tradeable.",
        "verification_notes": "Contrary evidence was searched before this patch was written: the "
                              "optimistic no-queue bound was added specifically to test whether "
                              "the queue model's conservatism was hiding a viable strategy, the "
                              "longer order lifetime diagnostic was run to test whether patience "
                              "helps, the highest-|I| states and the nearest queue positions were "
                              "examined for a favourable corner, per-symbol concentration was "
                              "measured, and two defects in the replay itself (executions not "
                              "reducing the quote book; level keys not scoped per symbol) were "
                              "found and fixed before any economic result was accepted.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
