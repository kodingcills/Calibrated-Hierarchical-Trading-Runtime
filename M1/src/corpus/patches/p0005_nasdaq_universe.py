"""Code-authored evidence patch P-0005: the Nasdaq large-tick universe rule.

Provenance: the full text of the verified Gould & Bonart preprint was retrieved on 2026-09-20
(arXiv PDF, converted with a text layer) and its sample-construction section read directly. That
section is what makes a *literature-anchored* universe rule possible: it states the venue
restriction, the dollar-volume rank rule used for selection, the tick size, the price screens that
separated large-tick from small-tick names, the 2014 sample window and the intraday window.

What this patch establishes:

* The paper's large-tick set was selected by relative tick size via price: the top five Nasdaq
  stocks by 2014 dollar volume whose maximum trade price was below $50 (MSFT, INTC, MU, CSCO,
  ORCL), against a $0.01 tick. Their mean quoted spreads were $0.012-$0.015, i.e. roughly one
  tick: the phenomenon they measure lives where the spread is pinned at the minimum tick.
* The paper's prediction target is the direction of the next mid-price movement, not a
  time-based horizon, and its sample window was calendar 2014 with 10:00-15:30 intraday
  restriction, 252 trading days, 100 subsampled observations per stock-day.
* The paper is predictive and gross only: no costs, fills or P&L.

Those facts anchor the project rule (median spread equal to one tick plus a preregistered
fraction-at-one-tick threshold) while making the divergence explicit: the project does not use the
$50 price screen as a selector, and it targets a 100 ms-1 s grid rather than a tick-scale move.

It does NOT establish that 2014 coefficients, decay or effect magnitudes transfer to a modern
venue, and no such claim is made.
"""

from __future__ import annotations

PATCH_ID = "P-0005"
ACCESS = "2026-09-20"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0027-NASDAQ-LARGETICK"],
        "candidate_ids": ["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"],
        "new_sources": [{
            "source_id": "SRC-0241",
            "title": "Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book "
                     "(author full text, arXiv PDF)",
            "authors_or_org": "Martin D. Gould; Julius Bonart",
            "publication_date": "2015-12-11",
            "access_date": ACCESS,
            "date_basis": "arXiv submission 2015-12-11; full text retrieved and parsed 2026-09-20",
            "url": "https://arxiv.org/pdf/1512.03492",
            "doi": None,
            "source_type": "academic_paper",
            "primary_or_secondary": "primary_official",
            "market": "US equities",
            "venue": "Nasdaq",
            "sample_period": "calendar year 2014, 252 trading days, 10:00-15:30 intraday window",
            "sample_size": "10 Nasdaq-listed stocks (5 large-tick, 5 small-tick); 25,200 "
                           "subsampled observations per stock; 80/20 in-sample/out-of-sample split",
            "methodology": "Logistic and local-logistic regression of next-mid-price-move "
                           "direction on best-quote queue imbalance, with ROC/AUC and mean-square "
                           "residual out-of-sample assessment against a constant-1/2 null",
            "gross_or_net": "GROSS / predictive only",
            "independent_replication": None,
            "limitations": "Single venue (Nasdaq, and the authors require Nasdaq to be the primary "
                           "trading venue); 2014 sample; LOBSTER data captures only Nasdaq order "
                           "flow; predictive and gross with no costs, fills or P&L; the horizon is "
                           "expressed as the next mid-price move rather than elapsed time.",
            "raw_citation_token": "code:P-0005",
            "local_path": None,
            "sha256": None,
            "status": "VERIFIED",
            "claim_scope": "Sample construction, large-tick characterisation, prediction target and "
                           "limitations of the verified preprint, read from the full text.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0066",
            "claim": "The verified preprint's large-tick sample was selected by relative tick size: "
                     "the top five Nasdaq stocks by total 2014 dollar volume whose maximum trade "
                     "price was below $50 (MSFT, INTC, MU, CSCO, ORCL) against a $0.01 tick, with "
                     "mean quoted spreads of $0.012-$0.015 - roughly one tick. Its small-tick set "
                     "used the top five names whose minimum trade price exceeded $100, where mean "
                     "spreads were $0.195-$1.111. The prediction target is the direction of the "
                     "next mid-price movement, and the authors restricted the sample to stocks for "
                     "which Nasdaq is the primary trading venue.",
            "source_id": "SRC-0241",
            "candidate_ids": "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
            "mechanism_id": "MECH-QIMB",
            "venue_id": "VEN-NASDAQ-CONT",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "EXTERNAL_VERIFIED",
            "supports_or_weakens": "SUPPORTS",
            "methodology": "Direct reading of the sample-construction section and summary-statistics "
                           "table of the verified preprint",
            "sample": "10 Nasdaq-listed stocks, calendar 2014",
            "temporal_scope": "2014 sample; full text read 2026-09-20",
            "gross_or_net": "GROSS / predictive only",
            "limitations": "The paper states a price screen and a dollar-volume rank; it does not "
                           "state a fraction-of-time-at-one-tick criterion, so the project's THETA "
                           "parameter cannot be sourced from it and is recorded as a preregistered "
                           "design parameter. 2014 prices are not 2026 prices, so the $50 screen is "
                           "not used as a selector. The horizon is a move, not an elapsed time.",
            "decision_implication": "Anchors the project's universe rule in verified literature "
                                    "(tick-pinned spread plus liquidity rank, Nasdaq-primary "
                                    "venue) while making each divergence explicit.",
            "contradicts_mechanism": "NO",
            "observed_market": "US equities",
            "observed_venue": "VEN-NASDAQ-CONT",
            "observed_instrument_or_universe": "top-5 Nasdaq by 2014 dollar volume with maximum "
                                               "trade price below $50 (large-tick set)",
            "observed_period": "calendar year 2014",
            "observed_horizon": "one mid-price movement (tick-scale)",
            "candidate_link_reason": "Same venue, same instrument class and same mechanism as the "
                                     "linked candidate; the divergence in universe definition and "
                                     "horizon is recorded in the universe spec.",
            "transfer_status": "CLOSE_TRANSFER",
            "verification_status": "VERIFIED_PRIMARY_FULL_TEXT",
        }],
        "modified_claims": [{
            "claim": "The project's large-tick threshold is literature-prescribed.",
            "status": "CORRECTED",
            "reason": "The literature prescribes a price screen for sample selection, not a "
                      "fraction-of-time-at-one-tick threshold. THETA=0.50 is recorded as a "
                      "preregistered design parameter with its basis stated and a prohibition on "
                      "tuning it against M2 outcomes.",
        }],
        "proposed_issue_updates": [{
            "issue_id": "UNK-0027-NASDAQ-LARGETICK",
            "from_status": "OPEN",
            "to_status": "RESOLVED_SUPPORTS",
            "resolution_note": "Universe rule NASDAQ-LARGETICK-QIMB-UNIV-v1 is specified, frozen "
                               "and approved: deterministic structural large-tick definition, "
                               "explicit eligibility rules with reason classes, monthly causal "
                               "selection with a 60-day lookback, point-in-time membership "
                               "requirement, prohibited selection variables and anti-leakage "
                               "controls. Specification artifact: "
                               "M1/hypotheses/candidate_specs/"
                               "NASDAQ_LARGETICK_QUEUE_IMBALANCE_UNIVERSE.json",
        }],
        "proposed_candidate_updates": [],
        "proposed_venue_updates": [],
        "proposed_source_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "SUPPORTS",
        "reason": "The branch's specification gap is closed by a causal, leakage-controlled "
                  "universe rule anchored in the verified literature, with every divergence from "
                  "that literature stated and every unsourced threshold labelled as a "
                  "preregistered design parameter.",
        "verification_notes": "Contrary checks performed: the paper was read in full rather than "
                              "relied on through its abstract, precisely to test whether a "
                              "literature-sourced threshold existed for the tick-pinned criterion; "
                              "it does not, so THETA was labelled a design parameter instead of "
                              "being presented as evidence-backed. The 2014 $50 price screen was "
                              "rejected as a selector for comparability reasons. The point-in-time "
                              "membership requirement is recorded as a KG2 data dependency rather "
                              "than silently substituting today's constituent list. No gate change "
                              "is proposed: the effect on KG5 is computed from the approved spec.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
