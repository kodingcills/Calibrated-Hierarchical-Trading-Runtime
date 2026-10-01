"""Code-authored evidence patch P-0011: the Hyperliquid/Binance funding-basis materiality kill.

Provenance: the project's own frozen experiment `M2-BRIDGE-HL-BINANCE-BASIS` (contract sealed at
`M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/freeze.json`, sha256
``389b8f4d65b1b2f54bf5eb29266c74c078ca7187e8c1b4455052fa52d780e3a7``), run once on the
availability-derived panel 2026-03-05T11:00:00Z-2026-09-28T23:00:00Z. Every number is read from
that run's frozen artifacts and was independently recomputed in verification wave V3
(`.research/m2_bridge_001/verification/V3/REPORT.md`, claim set C).

The versioned amendment AMEND-C5-001 is part of the frozen construction, not a post-result change:
the state uses causal LAST-TRADE prices from COMPLETED hourly candles, labelled REFERENCE prices,
because no free historical book mid exists for either leg; the Binance mark series is excluded from
the price term.

What this patch establishes:

* The frozen unconditional short-Hyperliquid Core BTC perpetual / long equal-notional Binance
  USD(S)-M BTCUSDT perpetual formulation earns **+0.0344051 bps per one-hour hold** (measured
  component +0.0324852, unresolved-bracket midpoint +0.0019199; HL carry +0.0596998, Binance carry
  -0.0267530, hedge mark-to-market residual -0.0004616), with an hour-clustered bootstrap interval
  [-0.0101126, +0.0755247] (10,000 resamples, seed 20260930).
* The structural floor is **C0 = 4.8 bps** = 2 executions x the LOWEST published Hyperliquid perp
  taker rung (0.024%/side). The 0.045% base tier is a labelled REFERENCE EXECUTION PATH scenario
  with ``may_decide_the_kill: false``. Using the lowest rung rather than the base tier LOWERS C0
  from 9.0 to 4.8 bps and therefore makes the kill harder.
* The fired clause is ``hi (0.09624) <= C0 (4.8)``: **KILL_MATERIALITY**, with
  **C* = -4.7655949 bps** and T* = 145.6896 h (interpretive only).
* Coverage is exact: 4,981/4,981 panel buckets with grid identity, 4,979/4,979 one-hour holds,
  84 in-panel Binance settlements unresolved and carried as the bracket
  [-0.0168709, +0.0207107] bps; boundary staleness <= 0.261 s with 0% beyond the declared 1 s
  tolerance.
* V3 recomputed the entire gross from the panel and the raw archives (all components delta 0.0),
  confirmed the sign convention, and established the kill is **SIGN-ROBUST**: reversing the
  structure gives -0.033048 bps and flipping only the HL carry -0.087373 bps, both still
  satisfying the kill rule.

What it does NOT establish: any longer-horizon, other-pair or state-conditioned result (a
reformulation is a NEW candidate, never a reinterpretation of this row); any verified Binance
all-leg cost (fee, spread, impact and capital stay UNKNOWN and unbounded in C1, so the true C* is
MORE negative than reported); any claim that pre-outcome sealing is externally proven (V3:
ordering only, UNVERIFIED); any claim that the 2026 rate card's applicability window is
independently confirmable; any claim of edge, profitability or production readiness. A zero-cost
maker path would make the verdict INDETERMINATE, as the producer stated.
"""

from __future__ import annotations

PATCH_ID = "P-0011"
ACCESS = "2026-09-30"
FREEZE_SHA = "389b8f4d65b1b2f54bf5eb29266c74c078ca7187e8c1b4455052fa52d780e3a7"
RESULTS_SHA = "97a4d7acf71db4837ad2e8cf090350b5615c2716684df531e74a6ef7f550d722"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0010", "UNK-0018-HYPERLIQUID"],
        "candidate_ids": ["TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"],
        "new_sources": [{
            "source_id": "SRC-0247",
            "title": "M2-BRIDGE-HL-BINANCE-BASIS - frozen funding-basis materiality measurement of "
                     "the Hyperliquid/Binance BTC carry tuple (project's own experiment)",
            "authors_or_org": "This project (GOAL-M2-BRIDGE-001, branch C)",
            "publication_date": "2026-09-30",
            "access_date": ACCESS,
            "date_basis": "contract sealed 2026-09-30T15:21:16 local (freeze.json), results written "
                          "2026-09-30T15:22:17; the measured panel covers "
                          "2026-03-05T11:00:00Z-2026-09-28T23:00:00Z",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "crypto perpetual futures (cross-venue funding/basis carry)",
            "venue": "Hyperliquid Core BTC perpetual (short leg) against Binance USD(S)-M BTCUSDT "
                     "perpetual (long leg)",
            "sample_period": "2026-03-05T11:00:00Z-2026-09-28T23:00:00Z (availability-derived, "
                             "100% hourly pairing)",
            "sample_size": "4,981 hourly panel buckets with exact grid identity; 4,979 evaluated "
                           "one-hour holds; 4,895 holds with every required input; 84 unresolved "
                           "in-panel Binance settlements",
            "methodology": "Preregistered freeze then one run under AMEND-C5-001: unconditional "
                           "short-HL / long-equal-notional-Binance carry, decision at hour J "
                           "immediately after the bucket-J funding settlement, entry on the row J-1 "
                           "causal last-trade reference price, exit one hour later on the row J "
                           "reference, carry collected per venue; C0 = 2 executions x the lowest "
                           "published Hyperliquid perp taker rung; interval from an hour-clustered "
                           "percentile bootstrap (10,000 resamples, seed 20260930) unioned with the "
                           "unresolved-rate bracket; verdict from "
                           "M2/src/envelope.py::classify_materiality.",
            "gross_or_net": "GROSS signed bps of notional per one-hour hold (the measured series is "
                            "gross of unresolved C1); C0 is a verified structural floor for the "
                            "Hyperliquid leg only",
            "independent_replication": "V3 wave: full independent recomputation from the panel and "
                                       "the raw funding archives (every component and the gross "
                                       "reproduce to 0.0), plus the sign-robustness control",
            "limitations": "One unconditional one-hour formulation on one development-grade panel; "
                           "the 84 unresolved Binance settlements contribute exactly zero to the "
                           "measured series and are bracketed only in the decision quantity; the "
                           "Binance all-leg cost is UNKNOWN and unbounded, so the true C* is more "
                           "negative than reported; pre-outcome sealing is asserted by artifact "
                           "ordering only; the freeze's recorded hash for M2/src/admission.py has "
                           "drifted and the freeze no longer verifies in place.",
            "raw_citation_token": "code:P-0011",
            "local_path": "M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/results.json",
            "sha256": RESULTS_SHA,
            "status": "PARTIAL",
            "claim_scope": "Measured gross carry of the frozen one-hour Hyperliquid/Binance basis "
                           "formulation, the published-rung structural floor it faces and the "
                           "resulting break-even residual, on one admitted panel.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0072",
            "claim": "Over the admitted panel 2026-03-05T11:00:00Z-2026-09-28T23:00:00Z the frozen "
                     "one-hour formulation (SHORT Hyperliquid Core BTC perpetual / LONG "
                     "equal-notional Binance USD(S)-M BTCUSDT perpetual, causal last-trade "
                     "reference prices) earns +0.0344051 bps per hold (measured component "
                     "+0.0324852; HL carry +0.0596998, Binance carry -0.0267530, hedge "
                     "mark-to-market residual -0.0004616), hour-clustered bootstrap CI "
                     "[-0.0101126, +0.0755247] and a 24 h moving-block variant [0.0157561, "
                     "0.0476396], against a structural floor C0 = 4.8 bps = 2 executions x the "
                     "LOWEST published Hyperliquid perp taker rung 0.024%/side. The fired clause is "
                     "hi (0.09624) <= C0 (4.8): KILL_MATERIALITY, C* = -4.7655949 bps, T* = 145.69 h "
                     "(interpretive only). The 0.045% base tier is a labelled REFERENCE EXECUTION "
                     "PATH scenario that may not decide the kill. Binance fee, spread, impact and "
                     "capital remain UNKNOWN and unbounded in C1, so the true C* is MORE negative "
                     "than reported. V3 established the kill is SIGN-ROBUST: reversing the "
                     "structure gives -0.0330 bps and flipping only the HL carry -0.0874 bps, both "
                     "still satisfying the kill rule.",
            "source_id": "SRC-0247",
            "candidate_ids": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
            "mechanism_id": "MECH-FUNDBASIS",
            "venue_id": "VEN-HYPERLIQUID-BTCPERP",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "WEAKENS",
            "methodology": "Deterministic frozen measurement, run once: the contract, universe "
                           "window, cost rule, coverage floor, inference rule and seeds were sealed "
                           "before any branch-C economics were inspected; the module re-derives "
                           "both reference series from the raw payloads and refuses on any hash "
                           "mismatch. V3 independently recomputed the entire gross from the panel "
                           "and the raw funding archives (deltas 0.0), verified the sign convention "
                           "from envelope.funding_cashflow, reproduced the unresolved-rate bracket "
                           "by interval arithmetic, recomputed staleness and confirmed 4,979 "
                           "contiguous holds with no drop or duplicate.",
            "sample": "4,979 one-hour holds over a 4,981-bucket panel (4,895 with every required "
                      "input); 84 holds with an unobserved Binance settlement rate",
            "temporal_scope": "2026-03-05T11:00:00Z-2026-09-28T23:00:00Z",
            "gross_or_net": "GROSS signed bps of notional per hold (unresolved C1 not deducted); "
                            "C0 is a verified structural floor on the Hyperliquid leg only",
            "limitations": "(i) The 84 unresolved settlements contribute exactly zero to the "
                           "MEASURED series and are bracketed only in the DECISION quantity - "
                           "'never treated as zero' holds for the decision input, not the measured "
                           "series. (ii) Sealing is asserted by ordering only, no external anchor "
                           "(UNVERIFIED). (iii) The freeze's recorded hash for M2/src/admission.py "
                           "(9f5862f7) no longer matches the tree (00363c3a, drifted by an "
                           "unrelated branch's additive contract), so the freeze no longer verifies "
                           "in place - inert for the result because the gross reproduces "
                           "independently from the panel and raw archives. (iv) V3 established the "
                           "kill is SIGN-ROBUST (reversed structure -0.0330 bps, flipped HL carry "
                           "-0.0874 bps; both still KILL), which strengthens rather than weakens "
                           "the verdict and is recorded instead of the verification brief's premise "
                           "that a "
                           "reversed sign would change it. (v) A zero-cost maker path would make "
                           "the verdict INDETERMINATE, as the producer stated. (vi) The "
                           "Hyperliquid fee page carries no version archive or effective date, and "
                           "staking discounts (up to 40%) and HIP-3 growth-mode perps (5-10x lower) "
                           "mean the note 'no account state pays less than 0.024%/side' is not "
                           "literally true - the direction of that error only makes the kill "
                           "harder.",
            "decision_implication": "The frozen one-hour carry is roughly 140x smaller than the "
                                    "cheapest published execution floor it must clear, so the "
                                    "branch is killed on materiality for this formulation and "
                                    "panel; the result supports no longer-horizon, other-pair or "
                                    "state-conditioned reading, and every such reformulation is a "
                                    "new candidate with its own registration and friction "
                                    "measurement.",
            "contradicts_mechanism": "NO",
            "observed_market": "crypto perpetual futures",
            "observed_venue": "VEN-HYPERLIQUID-BTCPERP",
            "observed_instrument_or_universe": "Hyperliquid Core BTC perpetual against Binance "
                                               "USD(S)-M BTCUSDT perpetual",
            "observed_period": "2026-03-05..2026-09-28",
            "observed_horizon": "H4 (one-hour hold, unconditional)",
            "candidate_link_reason": "The experiment exists solely to measure this candidate's own "
                                     "frozen formulation against the structural floor it must "
                                     "clear, on the panel its data prerequisite admitted, before "
                                     "any execution model or capital is committed to it.",
            "transfer_status": "DIRECT",
            "verification_status": "REPRODUCIBLE_FROM_SEALED_ARTEFACTS",
        }],
        "modified_claims": [
            {
                "claim": "The unknown Binance funding rate for the 84 unresolved in-panel "
                         "settlements is never treated as zero.",
                "status": "CORRECTED",
                "reason": "V3 (claim C10): true of the DECISION input, false of the measured "
                          "series - hold_terms passes funding_rate = 0.0 when the settlement is "
                          "unobserved, so the 84 holds contribute exactly zero to "
                          "measured_component_bps and are bracketed only in the decision quantity. "
                          "The direction-of-bias claim ('the true C* is more negative than "
                          "reported') is supported only through the unresolved one-sided C1 items, "
                          "not by the funding bracket, which is two-sided "
                          "(-4.784 .. -4.747 bps around the reported -4.76559).",
            },
            {
                "claim": "No account state pays less than 0.024%/side on the Hyperliquid leg.",
                "status": "CORRECTED",
                "reason": "V3 (claim C9, named limits): not literally true against the live "
                          "schedule - staking discounts of up to 40% apply to every rung and HIP-3 "
                          "growth-mode perps are 5-10x lower. The direction of that error makes the "
                          "kill HARDER, not easier, so the recorded C0 stays the lowest published "
                          "base-rate taker rung. Separately, the live fee page carries no version "
                          "archive or effective date, so the 2026-03-05..2026-09-28 applicability of "
                          "the current schedule rests on the recorded provenance alone.",
            },
            {
                "claim": "The branch-C freeze verifies in place today.",
                "status": "REJECTED",
                "reason": "V3 (claim A1b, NC6): freeze.json declares "
                          "inputs_sha256.code['M2/src/admission.py'] = 9f5862f7... and the file on "
                          "disk is 00363c3a...; run_inputs.json records the run-time value as "
                          "9f5862f7..., so the file changed after branch C ran and before branch B "
                          "sealed. `basis_materiality --check` refuses (exit 2). The drift is inert "
                          "for the result (the module only hashes admission.py, does not import it, "
                          "and V3 reproduces the entire gross from the panel and raw archives), but "
                          "branch C's seal can no longer be verified in place and the drift is "
                          "recorded rather than dropped.",
            },
        ],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [{
            "candidate_id": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
            "fields": {
                "KG3_EXECUTION": "FAIL",
                "overall_status": "DEAD",
                "status_basis": "KG3_EXECUTION fails on the project's own measured evidence "
                                "(EVD-0072, patch P-0011): +0.0344051 bps per one-hour hold "
                                "against a structural floor C0 of 4.8 bps, with C* = -4.7656 bps on "
                                "4,979 of 4,979 holds. Scoped to this frozen one-hour formulation "
                                "on this panel.",
                "kill_gate": "KG3_EXECUTION",
                "kill_reason": "The frozen one-hour carry is roughly 140x smaller than the "
                               "cheapest published execution floor it must clear "
                               "(+0.0344051 bps against C0 = 4.8 bps, the lowest published "
                               "Hyperliquid taker rung), giving C* = -4.7655949 bps; the base-tier "
                               "0.045% path is a labelled reference scenario that may not decide "
                               "the kill, and Binance's all-leg cost stays UNKNOWN and unbounded in "
                               "C1, so the true C* is more negative than reported. Measured on the "
                               "2026-03-05..2026-09-28 panel (M2-BRIDGE-HL-BINANCE-BASIS, freeze "
                               "sha256 389b8f4d...), scoped to this formulation.",
                "resurrection_condition": "A longer-horizon carry reformulation registered as its "
                                          "OWN candidate (never a reinterpretation of this row), "
                                          "plus a verified Binance all-leg cost schedule and the "
                                          "missing monthly funding file.",
            },
        }],
        "proposed_gate_changes": [{
            "candidate_id": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
            "gates": ["KG3_EXECUTION"],
            "from_value": "BLOCKED",
            "to_value": "FAIL",
            "reason": "EVD-0072: the frozen formulation's own gross carry is measured against a "
                      "verified published structural floor and is ~140x smaller, so the execution "
                      "requirement fails on the candidate's own formulation and panel.",
        }],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [{
            "update": "ADD",
            "dead_end": "Unconditional one-hour Hyperliquid/Binance BTC funding-basis carry at the "
                        "reference execution path",
            "finding": "The frozen one-hour formulation earned +0.0344051 bps per hold (CI "
                       "[-0.0101126, +0.0755247]) against a structural floor of 4.8 bps, i.e. C* = "
                       "-4.7655949 bps; the kill is sign-robust (reversed structure -0.0330 bps) "
                       "and the true C* is more negative than reported because Binance's all-leg "
                       "cost is unresolved.",
            "scope_limit": "this frozen one-hour formulation on the 2026-03-05..2026-09-28 panel "
                           "only; a longer horizon, another pair or a state-conditioned entry is a "
                           "new candidate",
            "evidence_id": "EVD-0072",
        }],
        "new_unknowns": [],
        "decision": "KILLS",
        "reason": "The candidate's own frozen formulation was measured against the published "
                  "structural floor it must clear, exactly once, under a contract sealed before the "
                  "outcome and with every reference series re-derived from raw archives: the gross "
                  "carry is two orders of magnitude below the cheapest published execution path, "
                  "the kill is sign-robust, and the unresolved Binance all-leg cost can only make "
                  "the true break-even residual more negative. The verdict is scoped to this "
                  "formulation and panel; no longer-horizon or other-pair reading is transferred "
                  "from it.",
        "verification_notes": "Contrary evidence was searched before this patch was written, and V3 "
                              "independently attacked the branch: the whole gross was recomputed "
                              "from the panel and the six raw fundingRate archives with no import "
                              "of the measurement path (every component and the pooled gross "
                              "reproduce to 0.0), the sign convention was read out of "
                              "envelope.funding_cashflow and confirmed, the C0 rule was checked "
                              "against a live retrieval of SRC-0213 (lowest published base-rate "
                              "rung 0.024%, lower than the 0.045% base tier, i.e. the choice makes "
                              "the kill harder), the counterfactual C0 = 9.0 still kills and C0 = 0 "
                              "would be INDETERMINATE, the 84 unresolved settlements were checked "
                              "by interval arithmetic (bracket width 0.0376 bps, two orders below "
                              "the gap to the floor), staleness was recomputed (max 0.261 s, 0 "
                              "beyond the declared 1 s tolerance), and the sign-robustness control "
                              "was run rather than assumed. The assignment's premise that a "
                              "reversed sign would change the verdict is contradicted by that "
                              "control and is recorded as strengthening the kill instead of being "
                              "carried forward. Limits carried through verbatim: the 84 unresolved "
                              "settlements are zero in the measured series and bracketed only in the "
                              "decision quantity; sealing is ordering-only and UNVERIFIED; the "
                              "M2/src/admission.py hash drift is recorded and the freeze no longer "
                              "verifies in place.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
