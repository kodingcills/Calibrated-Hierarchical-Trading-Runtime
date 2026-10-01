"""Code-authored evidence patch P-0012: the Nasdaq late-NOII auction measurement and its limits.

Provenance: the project's own run `M2-BRIDGE-AUCTION-LATENOII-MATERIALITY` (contract at
`M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/freeze.json`, sha256
``9baff3dd69a08dfc2883e972cddda763666819b4e83234960ec0b72b19e91393``; results sha256
``15b7a3d51c1e6d0ce897ec31d63357657df47a9d59d8af6316b2a513c50d2f63``), run once on the Nasdaq
TotalView-ITCH 5.0 session 2026-06-12 over the retained window 15:49:50-16:00:10 ET. The producing
process died at its reporting step; every number below is read from its artifacts and was
independently verified in verification wave V3 (`.research/m2_bridge_001/verification/V3/REPORT.md`,
claim set D).

What this patch records (and what it deliberately does NOT):

* The recorded verdict is **INDETERMINATE** on ``ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED``
  (7,176,224 orphan book messages = 35.75% of in-scope book traffic, because the retained window
  opens at 15:49:50) and ``SIGNAL_SCOPE_SUBFLOOR`` (1,286 of 2,465 = 0.5217). It is NOT a kill and
  NOT a survival: no gate is changed and the parent auction row is untouched.
* The experiment's freeze is **INVALID as a preregistration**. Its sealed input
  ``signal_extract.json`` was written at 15:30:07, nine minutes BEFORE the seal at 15:39:08, and
  already contained ``closing_cross_price_raw`` valid for **4,281 of 12,809** records - the exit
  price of every analysed symbol - contradicting the freeze's own statement that its inputs "carry
  no outcome quantity".
* The headline economic figure is a reconstruction artifact, not a result: mean capture
  = mean mechanism (+6.5168 bps) - mean side-signed(entry - reference) (+115.4115 bps)
  = **-108.8946 bps exactly**; the worst 50 of 1,261 symbols carry **93.9%** of the loss; the
  largest reconstructed entry spread is **$11.64 on a $2.10 stock**; and restricted to the 348
  symbols whose reconstructed spread is <= 10 bps of price the figure is **-0.60 bps**.
* The preregistered near/far band diagnostic is **DEGENERATE**: near and far prices are 0 in all
  12,809 records, so that clause can never pass for any reconstruction (an absent-input condition,
  not a quality test).
* The reconstruction-free mechanism metric is **POSITIVE** (+6.5168 bps, CI [2.0026, 10.9985]) and
  above the 1.02 bps fee floor, but it assumes a non-executable reference-price entry: it is NOT
  evidence of tradability and MUST NOT be recorded as a survivor, a kill, or edge.
* The exact next action that would make the branch decidable is a re-extract with pre-15:49:50
  book warm-up (the 17.9 GB source was streamed and not retained) under a freeze whose inputs
  contain no outcome quantity and whose sealing is externally anchored; it is registered as
  OQ-0017 rather than as a verdict.

The universe transcription repair already recorded in the spec is kept: C = Common Shares,
Z = Not Applicable; corrected clause Authenticity = P, ETP Flag = N, Issue Classification = C,
Market Category in {Q,G,S}.
"""

from __future__ import annotations

PATCH_ID = "P-0012"
ACCESS = "2026-09-30"
FREEZE_SHA = "9baff3dd69a08dfc2883e972cddda763666819b4e83234960ec0b72b19e91393"
RESULTS_SHA = "15b7a3d51c1e6d0ce897ec31d63357657df47a9d59d8af6316b2a513c50d2f63"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0018-NASDAQ", "UNK-0027-AUCTION"],
        "candidate_ids": ["TUP-NASDAQ-CLOSE-H4-LATENOII-AGG"],
        "new_sources": [{
            "source_id": "SRC-0248",
            "title": "M2-BRIDGE-AUCTION-LATENOII-MATERIALITY - development-grade single-session "
                     "measurement of the Nasdaq late-NOII closing displacement signal "
                     "(project's own experiment, freeze invalidated)",
            "authors_or_org": "This project (GOAL-M2-BRIDGE-001, branch AUCTION; producer B5 failed "
                              "at its reporting step, artifacts complete)",
            "publication_date": "2026-09-30",
            "access_date": ACCESS,
            "date_basis": "signal extract written 2026-09-30T15:30:07 local, entry prints 15:31:02, "
                          "contract sealed 15:39:08, results 15:39:17 - the sealed input therefore "
                          "PREDATES the seal; the measured session is 2026-06-12",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "US equities (Nasdaq closing auction)",
            "venue": "Nasdaq (XNAS) Closing Cross; TotalView-ITCH 5.0 and NOII reads",
            "sample_period": "one session, 2026-06-12, retained window 15:49:50-16:00:10 ET",
            "sample_size": "12,809 session locates; 2,465 universe-qualified with a valid Closing "
                           "Cross; 1,261 signal-defined symbols analysed; 1,219 with a "
                           "reconstruction snapshot at 15:55",
            "methodology": "One frozen run: entry at the first eligible post-15:55 best ask "
                           "(positive signal) or best bid (negative), exit at the Closing Cross "
                           "print; entry books reconstructed from the retained window alone; "
                           "C0 = SEC Section 31 plus FINRA TAF on the sell leg; symbol-clustered "
                           "percentile bootstrap (10,000 resamples, seed 20260612); frozen clause "
                           "order coverage floor -> reconstruction validation -> "
                           "significance-vs-C0 rule.",
            "gross_or_net": "The primary figure is NET of the verified mandatory charges C0 and "
                            "excludes unresolved C1; the mechanism metric is GROSS and is not an "
                            "achievable return",
            "independent_replication": "V3 wave: independent re-run of the frozen measurement "
                                       "(identical modulo generated_utc) plus an independent "
                                       "decomposition of the headline figure from the per-symbol "
                                       "records",
            "limitations": "One session, one venue; the entry book is reconstructed from the "
                           "retained window alone and cannot see orders added before 15:49:50, so "
                           "the measured capture is a lower bound and the entry spread an upper "
                           "bound; the freeze is INVALID as a preregistration because its sealed "
                           "input already carried the Closing Cross exit price; the preregistered "
                           "near/far band diagnostic is degenerate; 47.8% of the "
                           "universe-qualified population is removed by the frozen N/O/P direction "
                           "rule.",
            "raw_citation_token": "code:P-0012",
            "local_path": "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/results.json",
            "sha256": RESULTS_SHA,
            "status": "PARTIAL",
            "claim_scope": "Measured executable capture and mechanism displacement of the frozen "
                           "late-NOII closing formulation on one session, together with the "
                           "verified reasons the executable figure is not a decision-grade "
                           "economic measurement.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0073",
            "claim": "On the single Nasdaq 2026-06-12 session the frozen late-NOII executable "
                     "capture reads -108.8946 bps pooled over 1,261 signal-defined symbols, but the "
                     "figure is a reconstruction artifact: mean capture = mean mechanism "
                     "(+6.5168 bps) - mean side-signed(entry - reference) (+115.4115 bps) exactly; "
                     "the worst 50 symbols carry 93.9% of the loss; the largest reconstructed entry "
                     "spread is $11.64 on a $2.10 stock; and on the 348 symbols whose reconstructed "
                     "spread is <= 10 bps of price the figure is only -0.60 bps (mechanism +3.55). "
                     "The recorded verdict is therefore INDETERMINATE on "
                     "ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED (7,176,224 orphan messages = 35.75% of "
                     "in-scope book traffic, the retained window opening at 15:49:50) and "
                     "SIGNAL_SCOPE_SUBFLOOR (1,286 of 2,465 = 0.5217), with the rule verdict "
                     "KILL_MATERIALITY retained only as an explicitly superseded field. The "
                     "preregistered near/far band diagnostic is DEGENERATE - near and far prices "
                     "are 0 in all 12,809 records - so that clause can never pass for any "
                     "reconstruction. The reconstruction-free mechanism metric is POSITIVE "
                     "(+6.5168 bps, CI [2.0026, 10.9985]) and above the 1.02 bps fee floor, but it "
                     "assumes a non-executable reference-price entry and is NOT evidence of "
                     "tradability. The experiment's freeze is INVALID as a preregistration: its "
                     "sealed input signal_extract.json was written before the seal and already "
                     "contained closing_cross_price_raw, valid for 4,281 of 12,809 records, "
                     "contradicting the freeze's own statement that its inputs carry no outcome "
                     "quantity.",
            "source_id": "SRC-0248",
            "candidate_ids": "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
            "mechanism_id": "MECH-AUCTIONIMB",
            "venue_id": "VEN-NASDAQ-AUCTION",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "WEAKENS",
            "methodology": "One frozen run on a retained ITCH 5.0 window, then independent "
                           "verification: V3 re-ran the frozen measurement (identical modulo "
                           "generated_utc), decomposed the headline figure from the per-symbol "
                           "records (identity exact to the printed precision), recomputed the "
                           "concentration and spread-restricted variants, applied the frozen rule "
                           "with the entry-book clause disabled as a negative control "
                           "(KILL_MATERIALITY vs the delivered INDETERMINATE, so the clause is "
                           "decision-changing and blocks a kill rather than creating one), and "
                           "compared the artifact times against the seal.",
            "sample": "1,261 signal-defined Nasdaq-listed common stocks with a valid Closing Cross "
                      "and a signed imbalance at both frozen reads; 12,809 session locates; 1,219 "
                      "reconstruction snapshots at 15:55",
            "temporal_scope": "2026-06-12, 15:50-16:00 ET (one session)",
            "gross_or_net": "The capture figure is net of the verified C0 (1.02 bps) and excludes "
                            "unresolved C1; the mechanism metric is gross and non-executable",
            "limitations": "(a) The freeze is INVALID as a preregistration: its sealed input was "
                           "written before the seal and already contained the Closing Cross exit "
                           "price for 4,281 of 12,809 records, so it does not establish "
                           "sealed-before-outcome discipline for this branch. (b) The "
                           "executable-capture figure is a reconstruction artifact of the "
                           "unvalidated entry book (identity, concentration and restriction all "
                           "say so) and is not a decision-grade economic measurement. (c) The "
                           "preregistered near/far band diagnostic is degenerate and could never "
                           "pass for any reconstruction. (d) The reconstruction-free mechanism "
                           "metric is positive but assumes a non-executable reference-price entry: "
                           "it is not evidence of tradability and is recorded neither as a "
                           "survivor, a kill, nor edge. (e) 47.8% of the universe-qualified "
                           "population is removed by the frozen N/O/P direction rule "
                           "(SIGNAL_SCOPE_SUBFLOOR). (f) One session, one venue; the producing "
                           "process died at its reporting step and its narration is not evidence.",
            "decision_implication": "The auction branch has an OPEN QUESTION, not a verdict: no "
                                    "KILL and no survival is recorded, no gate is changed, and the "
                                    "parent auction row is untouched. The exact next action that "
                                    "would make it decidable is a re-extract with pre-15:49:50 "
                                    "book warm-up under a freeze whose inputs contain no outcome "
                                    "quantity and whose sealing is externally anchored (OQ-0017).",
            "contradicts_mechanism": "NO",
            "observed_market": "US equities",
            "observed_venue": "VEN-NASDAQ-AUCTION",
            "observed_instrument_or_universe": "Nasdaq-listed common stock (Authenticity=P, ETP "
                                               "Flag=N, Issue Classification=C, Market Category in "
                                               "{Q,G,S}), 2,465 with a valid Closing Cross",
            "observed_period": "2026-06-12",
            "observed_horizon": "H4 (15:50 signal reads -> 16:00 Closing Cross)",
            "candidate_link_reason": "The experiment is the first measurement of this candidate's "
                                     "own frozen formulation; it is the only quantitative material "
                                     "that exists for the row, and it is recorded with its "
                                     "invalidation so no later reader mistakes it for a verdict.",
            "transfer_status": "SINGLE_SESSION",
            "verification_status": "VERIFIED_BY_INDEPENDENT_DECOMPOSITION_AND_NEGATIVE_CONTROL",
        }],
        "modified_claims": [
            {
                "claim": "The branch's freeze establishes that its measurement was sealed before "
                         "any outcome quantity existed for its inputs.",
                "status": "REJECTED",
                "reason": "V3 (claims A2 and D12): the freeze asserts its sealed admission artifacts "
                          "'carry no outcome quantity', but signal_extract.json - hashed by the "
                          "freeze and written at 15:30:07, nine minutes before the seal at "
                          "15:39:08 - already contains closing_cross_price_raw with "
                          "closing_cross_valid = true for 4,281 of 12,809 records, i.e. the exit "
                          "price of every analysed symbol. The whole measurement is derivable from "
                          "artifacts that existed before the seal, so the freeze does not "
                          "establish pre-outcome sealing for this branch.",
            },
            {
                "claim": "The preregistered entry-book reconstruction gate is a "
                         "reconstruction-quality test.",
                "status": "CORRECTED",
                "reason": "V3 (claim D12b): within_far_band_ratio = 0.0 is degenerate - "
                          "read_1555_near_price_raw and read_1555_far_price_raw are 0 in all "
                          "12,809 extract records and the code tests "
                          "'if far and near and near <= mid <= far', so the preregistered 0.9 "
                          "floor can never pass for any reconstruction, faithful or not. It is an "
                          "absent-input condition rather than a quality measurement. The clause's "
                          "substance survives on independent evidence (orphans, one-tick "
                          "agreement 506/1,219 = 0.415, median |mid - reference| 9.5 bps) and it "
                          "blocked a KILL rather than manufacturing one.",
            },
            {
                "claim": "The -108.89 bps executable capture can be read as a real economic result "
                         "for this formulation.",
                "status": "REJECTED",
                "reason": "V3 (claim D13): the entire loss is the gap between the reconstructed "
                          "entry price and the exchange's own reference price "
                          "(+6.5168 - 115.4115 = -108.8946 exactly), 50 of 1,261 symbols carry "
                          "93.9% of it, the worst reconstructed spread is $11.64 on a $2.10 stock, "
                          "entering at the reconstructed midpoint gives -6.98 bps, and on the 348 "
                          "symbols with a reconstructed spread <= 10 bps of price the figure is "
                          "-0.60 bps. The executable capture is not measurable on this tape with "
                          "this reconstruction, so neither a kill nor a capture estimate may be "
                          "recorded from it.",
            },
        ],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "WEAKENS",
        "reason": "The branch's only measurement is recorded with its freeze invalidated and its "
                  "headline economic figure identified as a reconstruction artifact. The recorded "
                  "verdict INDETERMINATE stands on the unvalidated entry-book reconstruction and "
                  "the signal-scope subfloor, so nothing is killed and nothing survives: no gate "
                  "is changed, no dead-end entry is created, the candidate row stays UNKNOWN and "
                  "blocked, and the parent auction row is untouched. The decidable next action is "
                  "registered as an open question (OQ-0017) rather than as a verdict, and the "
                  "positive reconstruction-free mechanism metric is explicitly not recorded as "
                  "evidence of tradability.",
        "verification_notes": "Contrary evidence was searched before this patch was written, and "
                              "the branch was attacked hardest of the three because its producer "
                              "died at its reporting step: V3 re-ran the frozen measurement from "
                              "the retained artifacts (identical modulo generated_utc), "
                              "independently decomposed the headline number from the per-symbol "
                              "records, recomputed the concentration (worst 50 = 93.9411%) and the "
                              "spread-restricted variants (348 symbols <= 10 bps: -0.6029 bps "
                              "gross, +3.5475 bps mechanism), checked the largest reconstructed "
                              "spread ($11.64 on SQFT at $2.10), ran the frozen rule with the "
                              "entry-book clause disabled as a negative control (the clause is "
                              "decision-changing and blocks a kill rather than creating one), "
                              "verified the coverage accounting by identity (input availability "
                              "1.0000 against the 0.95 floor; analysed ratio 0.5217), and verified "
                              "the universe transcription repair against the certificate counts. "
                              "The producer's preferred reading - a KILL on a -109 bps capture - "
                              "was explicitly tested and rejected because the reconstruction bias "
                              "can account for the whole gap, which is why INDETERMINATE and not "
                              "KILLS is recorded; equally, the positive mechanism metric is not "
                              "promoted to a survival claim because its entry is not executable. "
                              "No number was adjusted and no frozen parameter was touched.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
