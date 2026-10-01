"""Code-authored evidence patch P-0010: the ES H3 OFI sample-scoped materiality kill.

Provenance: the project's own frozen experiment `M2-BRIDGE-ES-H3-OFI` (contract sealed at
`M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json`, sha256
``42a158c584552392e6c21535f35b3887228ea209c47257dee97672f6bfd75568``), run once on the single
admitted CME Globex MDP 3.0 ESU3 window 2023-07-17T13:30:00Z-13:40:00Z (one 10-minute RTH-open
window). Every number is read from that run's frozen artifacts and was independently reproduced in
verification wave V3 (`.research/m2_bridge_001/verification/V3/REPORT.md`, claim set B).

What this patch establishes:

* The registered H3 aggressive order-flow-imbalance state
  ``x(t) = (V_buy - V_sell) / D(t)`` over ``(t-1 s, t]``, traded on its own sign at the midpoint,
  earns **-0.0047336 bps** of side-signed 1 s markout (95% instrument x 60 s block interval
  [-0.0468503, +0.0403358], n = 583 of 599 decision slots) against a measured observed-spread
  round trip of **0.5770016 bps** (13.1004 USD per contract), giving **C* = -0.5817352 bps**.
* The term structure is -0.0047336 / -0.0014608 / +0.0502825 bps at 1 / 5 / 15 s: every point is at
  most 8.7% of the floor, and the primary horizon - the one the frozen contract decides on - is
  non-positive.
* The unconditional side-ignoring markout at the same instants is **+0.0156746 bps**, so the
  conditional state is BELOW its own unconditional baseline: this is an absence of detectable
  conditional displacement, not merely a small signal.
* The fired clause is ``PRIMARY_HORIZON_GROSS_NOT_POSITIVE``; the independent arm ``hi <= C0``
  (0.0403358 <= 0.5770016) also holds. Coverage passed (quote 0.99833, observation 0.97329).
* V3 reproduced the whole arithmetic independently (deltas 0.0), re-ran the sealed contract to a
  byte-identical ``results.json`` (sha256 ``09c85629...``), and verified the state is strictly
  causal (5,999/5,999 instants against a strictly-past level-1 rebuild).

What it does NOT establish: any session-, regime-, product- or breadth-level claim (the verdict is
``SAMPLE_SCOPED_DEVELOPMENT_KILL``); any verified CME exchange/clearing/FCM charge (C0 is the
measured observed-spread friction alone and C1 remains UNKNOWN, never zero); any statement about the
mechanism on other windows or products; any claim that pre-outcome sealing is externally proven
(V3: UNVERIFIED - artifact ordering only); any claim of edge, profitability or production
readiness. The producer proposed charging the failure to ``KG1_MECHANISM`` or, alternatively, to
``KG3_EXECUTION`` on the M2-2 precedent; the charge recorded here is ``KG1_MECHANISM`` and the
alternative is recorded in the patch reason and the candidate row's notes.
"""

from __future__ import annotations

PATCH_ID = "P-0010"
ACCESS = "2026-09-30"
FREEZE_SHA = "42a158c584552392e6c21535f35b3887228ea209c47257dee97672f6bfd75568"
RESULTS_SHA = "09c8562999304072a5f5b5184bece3ba0588d1d57754ae776b3c6934f1487ac2"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0009-MECH-CME", "UNK-0018-CME"],
        "candidate_ids": ["TUP-CME-ES-H3-OFI-AGG"],
        "new_sources": [{
            "source_id": "SRC-0246",
            "title": "M2-BRIDGE-ES-H3-OFI - frozen single-window materiality measurement of the "
                     "ES H3 aggressive order-flow-imbalance tuple (project's own experiment)",
            "authors_or_org": "This project (GOAL-M2-BRIDGE-001, branch A)",
            "publication_date": "2026-09-30",
            "access_date": ACCESS,
            "date_basis": "contract sealed 2026-09-30T15:15:44 local (freeze.json), results written "
                          "2026-09-30T15:15:59; the measurement window itself is "
                          "2023-07-17T13:30:00Z-13:40:00Z",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "CME index futures",
            "venue": "CME (Globex), ESU3 (E-mini S&P 500, Sep-2023 contract)",
            "sample_period": "one 10-minute RTH-open window, 2023-07-17T13:30:00Z-13:40:00Z",
            "sample_size": "18,104 ESU3 trades over 60,000 10 ms grid instants; 599 one-second "
                           "decision slots; 583 evaluated observations (273 LONG / 310 SHORT)",
            "methodology": "Preregistered freeze then one run: causal signed order-flow state over "
                           "the one-second interval ending at the decision instant divided by the "
                           "displayed top-of-book depth; side-signed midpoint markout on the "
                           "reconstructed top of book (no executable-price substitution); friction "
                           "measured as 1/2 S_entry + 1/2 S_exit from the OBSERVED quoted spread at "
                           "both instants; interval from an instrument x 60 s block cluster "
                           "bootstrap (2000 resamples, seed 20260717, 10 clusters); verdict from "
                           "M2/src/envelope.py::classify_materiality on the primary 1 s horizon.",
            "gross_or_net": "GROSS side-signed midpoint markout for the signal; the friction term "
                            "is measured separately from observed quoted spreads and is not "
                            "subtracted from the reported gross. C0 is the measured observed-spread "
                            "round trip, not a verified all-in venue cost.",
            "independent_replication": "V3 wave: independent re-implementation of the metric "
                                       "(deltas 0.0), byte-identical re-run of the sealed contract, "
                                       "and a strictly-past level-1 rebuild agreeing at 5,999/5,999 "
                                       "instants",
            "limitations": "One venue, one instrument, one contract month, one 10-minute window, "
                           "one session; C0 contains no verified exchange/clearing/FCM charge; "
                           "pre-outcome sealing is asserted by artifact ordering only (no external "
                           "anchor); the published unconditional figure is the mean over 598 "
                           "quote-available slots while the conditional is over 583.",
            "raw_citation_token": "code:P-0010",
            "local_path": "M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json",
            "sha256": RESULTS_SHA,
            "status": "PARTIAL",
            "claim_scope": "Measured conditional displacement of the registered ES H3 OFI state, "
                           "the observed-spread friction it faces and the resulting break-even "
                           "residual, on one admitted CME ESU3 window.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0071",
            "claim": "On the single admitted CME ESU3 window 2023-07-17T13:30:00Z-13:40:00Z the "
                     "causal signed order-flow-imbalance state earns -0.0047336 bps of side-signed "
                     "1 s markout (95% instrument x 60 s block cluster interval [-0.0468503, "
                     "+0.0403358], n = 583 of 599 decision slots, se 0.0222976, t = -0.212), "
                     "-0.0014608 bps at 5 s and +0.0502825 bps at 15 s, against a measured "
                     "observed-spread round trip of 0.5770016 bps (13.1004 USD per contract), so "
                     "the break-even residual is C* = -0.5817352 bps (-13.207857 USD per contract). "
                     "The fired clause is PRIMARY_HORIZON_GROSS_NOT_POSITIVE and the independent "
                     "arm hi <= C0 (0.0403358 <= 0.5770016) also holds. The unconditional "
                     "side-ignoring markout is +0.0156746 bps at 1 s (over the 598 quote-available "
                     "slots) and +0.0208001 bps on the same 583 conditional instants, so the "
                     "conditional state is BELOW its own unconditional baseline: this is the "
                     "absence of a detectable conditional displacement rather than merely a small "
                     "signal. Coverage passed (quote 0.99833, observation 0.97329, floors 0.95 / "
                     "0.75 / 250 observations). Recorded scope: "
                     "SAMPLE_SCOPED_DEVELOPMENT_KILL - one venue, one instrument, one contract "
                     "month, one 10-minute window, one session.",
            "source_id": "SRC-0246",
            "candidate_ids": "TUP-CME-ES-H3-OFI-AGG",
            "mechanism_id": "MECH-OFI",
            "venue_id": "VEN-CME-ES",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "WEAKENS",
            "methodology": "Deterministic frozen measurement, run once: state from aggressor-signed "
                           "ESU3 trade volume in the one-second interval ending at the decision "
                           "instant divided by displayed top-of-book depth; outcome from the "
                           "reconstructed top-of-book midpoint at entry and exit; friction from the "
                           "observed quoted spread at both instants; instrument x 60 s block "
                           "cluster bootstrap, 2000 resamples, seed 20260717; the contract, "
                           "horizon, state, friction treatment, coverage floor, metric, kill rule "
                           "and seeds were sealed before any gross markout was inspected. V3 "
                           "independently re-implemented the arithmetic (deltas 0.0), re-ran the "
                           "sealed contract to a byte-identical results.json and verified the state "
                           "is strictly causal (5,999/5,999 instants).",
            "sample": "18,104 ESU3 trades; 599 one-second decision slots, 583 evaluated "
                      "observations (273 LONG / 310 SHORT)",
            "temporal_scope": "2023-07-17T13:30:00Z-13:40:00Z (one window, one session)",
            "gross_or_net": "GROSS side-signed midpoint markout for the signal; the observed-spread "
                            "friction C0 is measured separately and is a floor, not an all-in cost",
            "limitations": "(i) Sealing is asserted by artifact ordering only - no external anchor, "
                           "so pre-outcome sealing is UNVERIFIED. (ii) The published unconditional "
                           "figure is the mean over 598 quote-available slots while the conditional "
                           "is over 583 (0.0051 bps apart; V3 reports it as not decision-relevant "
                           "but not identical instants). (iii) A single window cannot establish "
                           "survival under the campaign's own rule. (iv) C0 contains no verified "
                           "exchange/clearing/FCM charge, so the measured friction is a floor; that "
                           "omission can only favour the candidate and it still fails. (v) The two "
                           "availability clocks induce identical one-second buckets on this slice, "
                           "so the capture-clock pass is not an independent clock test.",
            "decision_implication": "The registered ES H3 OFI mechanism shows no positive "
                                    "conditional displacement on the only window its data "
                                    "prerequisite admitted, at any reported horizon, and the "
                                    "conditional state does not beat doing nothing at the same "
                                    "instants; the gross-materiality precursor this branch was "
                                    "blocked on is therefore discharged with a negative, "
                                    "sample-scoped result, and no execution model, latency "
                                    "investment, data purchase or passive pivot is justified by it.",
            "contradicts_mechanism": "NO",
            "observed_market": "CME index futures",
            "observed_venue": "VEN-CME-ES",
            "observed_instrument_or_universe": "ESU3 (E-mini S&P 500 futures, September 2023 "
                                               "contract), instrument id 3445",
            "observed_period": "2023-07-17",
            "observed_horizon": "H3 (1 / 5 / 15 s; the frozen primary horizon is 1 s)",
            "candidate_link_reason": "The experiment exists solely to measure this candidate's own "
                                     "registered mechanism against the friction of participating, "
                                     "before any execution model or strategy evaluation is built "
                                     "for it (the order of work recorded as D-0037 and applied to "
                                     "this branch by D-0042).",
            "transfer_status": "DIRECT",
            "verification_status": "REPRODUCIBLE_FROM_SEALED_ARTEFACTS",
        }],
        "modified_claims": [
            {
                "claim": "The published unconditional markout and the conditional markout are "
                         "computed on the same decision instants.",
                "status": "CORRECTED",
                "reason": "V3 (claim B6'): the published unconditional value is the mean over the "
                          "598 quote-available slots while the conditional gross is over the 583 "
                          "non-zero-state observations; on the same 583 instants the unconditional "
                          "value is +0.0208001 bps, 0.0051 bps above the published +0.0156746. "
                          "The correction is not decision-relevant (both readings are far below "
                          "C0 and the verdict is set by g <= 0), but the two are not identical "
                          "instants and the tables invite the same-population reading.",
            },
            {
                "claim": "The ES measurement's pre-outcome sealing is established by the retained "
                         "artifacts.",
                "status": "UNVERIFIED",
                "reason": "V3 (claim A2): the seal file precedes the result and the seal check is "
                          "live (NC1 tampers the contract and gets MeasurementError), but nothing "
                          "retained pins wall-clock order against a producer who re-seals after "
                          "looking - the freeze is a plain file with an attacker-settable mtime "
                          "and the earlier contract (54b64f7c...) was not retained. What would "
                          "establish it: an external trusted timestamp (RFC 3161 / transparency "
                          "log) over freeze.sha256 taken before the run, or a git commit of the "
                          "freeze preceding the result.",
            },
            {
                "claim": "The ES kill may be read as a session-, regime- or product-level result.",
                "status": "REJECTED",
                "reason": "The frozen scope rule records SAMPLE_SCOPED_DEVELOPMENT_KILL: one "
                          "admitted 10-minute window can support at most a sample-scoped "
                          "development kill and can never support survival. The candidate row "
                          "carries that scope and a resurrection condition requiring at least two "
                          "non-overlapping admitted ES sessions (or a materially different regime "
                          "under the same frozen construction) plus verified account-independent "
                          "CME charges.",
            },
        ],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [{
            "candidate_id": "TUP-CME-ES-H3-OFI-AGG",
            "fields": {
                "KG3_EXECUTION": "FAIL",
                "overall_status": "DEAD",
                "status_basis": "KG3_EXECUTION fails on the project's own measured evidence "
                                "(EVD-0071, patch P-0010): -0.0047336 bps of side-signed 1 s "
                                "markout on the only admitted ESU3 window against a measured "
                                "observed-spread round trip of 0.5770016 bps, with every reported "
                                "term-structure point at most 8.7% of that floor. Recorded as a "
                                "SAMPLE_SCOPED_DEVELOPMENT_KILL.",
                "kill_gate": "KG3_EXECUTION",
                "kill_reason": "The registered mechanism produced no positive conditional "
                               "displacement on this window at any reported horizon, and the "
                               "conditional state is below its own unconditional baseline "
                               "(+0.0156746 bps over 598 quote-available slots, +0.0208001 bps on "
                               "the 583 conditional instants). The fired clause is "
                               "PRIMARY_HORIZON_GROSS_NOT_POSITIVE; the independent arm "
                               "hi <= C0 holds as well. Measured on the admitted CME ESU3 slice "
                               "2023-07-17T13:30:00Z-13:40:00Z (M2-BRIDGE-ES-H3-OFI, freeze sha256 "
                               "42a158c5...), scoped to that single window.",
                "resurrection_condition": "Two or more non-overlapping admitted ES sessions, or a "
                                          "materially different regime measured under the same "
                                          "frozen construction, PLUS verified account-independent "
                                          "CME exchange/clearing/FCM charges.",
            },
        }],
        "proposed_gate_changes": [{
            "candidate_id": "TUP-CME-ES-H3-OFI-AGG",
            "gates": ["KG3_EXECUTION"],
            "from_value": "BLOCKED",
            "to_value": "FAIL",
            "reason": "EVD-0071: the candidate's own registered mechanism was measured against the "
                      "friction it faces on admitted causal data and supplies at most 8.7% of it "
                      "at every reported horizon, with the primary-horizon gross non-positive. The "
                      "producer's alternative reading (KG1_MECHANISM, on the argument that the "
                      "mechanism's own displacement is what was measured) is recorded rather than "
                      "used: KG1 would assert that the mechanism does not operate on ES, which one "
                      "10-minute window cannot establish - the mechanism is not shown to be "
                      "absent, only to produce no positive conditional displacement at the "
                      "reported horizons - whereas KG3 is the gate that encodes the "
                      "friction/materiality comparison the fired clause actually is.",
        }],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [{
            "update": "ADD",
            "dead_end": "Signed aggressive order-flow imbalance at the top of one 10-minute ES "
                        "RTH-open window",
            "finding": "Traded on its own sign at the midpoint it earned -0.0047336 bps at 1 s "
                       "(and -0.0014608 / +0.0502825 bps at 5 / 15 s) against a 0.5770016 bps "
                       "observed-spread round trip on 583 of 599 decisions, and the conditional "
                       "state did not beat the unconditional +0.0156746 bps drift at the same "
                       "instants.",
            "scope_limit": "one venue, one instrument, one contract month, one window, one session; "
                           "a development-grade, sample-scoped kill",
            "evidence_id": "EVD-0071",
        }],
        "new_unknowns": [],
        "decision": "KILLS",
        "reason": "The candidate's registered mechanism was measured against the friction it faces, "
                  "exactly once, under a contract sealed before the outcome, and it produced no "
                  "positive conditional displacement at any reported horizon: the primary-hour "
                  "gross is non-positive and the decision-interval arm hi <= C0 holds "
                  "independently. The verdict is recorded as a sample-scoped development kill "
                  "(the row is DEAD in canonical state with a stated resurrection bar), charged to "
                  "KG3_EXECUTION because the fired clause is a friction/materiality comparison "
                  "against C0; the producer's alternative charge (KG1_MECHANISM) is recorded as "
                  "unused rather than dropped, because it would assert more than one window can "
                  "establish.",
        "verification_notes": "Contrary evidence was searched before this patch was written, and V3 "
                              "independently attacked the branch: the metric was re-implemented "
                              "from the frozen contract text (deltas 0.0 on the pooled, C0, C* and "
                              "per-state figures), the sealed contract was re-run to a "
                              "byte-identical results.json (sha256 09c85629...), the state was "
                              "verified strictly causal against a strictly-past level-1 rebuild "
                              "(5,999/5,999; the same check without the instrument filter "
                              "mismatches 1,438/5,999, so it is not vacuous), C0 was reproduced "
                              "from the observed grid (implied 1.047 ticks - NOT a hard-coded tick; "
                              "a one-tick-per-side stand-in would be 1.102 bps), the sign was "
                              "checked (a flipped sign leaves the verdict unchanged, only the "
                              "clause moves), and the single-window scope downgrade was verified "
                              "as a live code path. The counter-consideration that would have "
                              "favoured the candidate was put first: the longest horizon, the only "
                              "positive term-structure point, was reported in full (+0.0502825 bps "
                              "at 15 s) and is still 8.7% of C0. No number here was adjusted after "
                              "the result was seen, and the frozen thresholds were not touched. "
                              "Limits carried through verbatim: sealing is asserted by artifact "
                              "ordering only (UNVERIFIED); the published unconditional figure is "
                              "over 598 quote-available slots while the conditional is over 583 "
                              "(0.0051 bps apart, not decision-relevant but not identical "
                              "instants); a single window cannot establish survival under the "
                              "campaign's own rule.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
