"""Code-authored evidence patch P-0004: citation replacements for the literature claims.

Provenance: iteration-4 verification against author, repository and publisher metadata on
2026-09-20.

Gould & Bonart - VERIFIED. arXiv 1512.03492 exists with the exact title, both authors, the
2015-12-11 submission date and a q-fin.TR classification; its abstract states the sample (10
liquid stocks on Nasdaq), the method (logistic regression between queue imbalance and the
direction of the subsequent mid-price movement) and the result (considerable improvement for
large-tick stocks, moderate for small-tick). The claim previously recorded under a report token is
therefore re-derived from an identified source, and the token becomes LEGACY_REPORT_MEDIATED.

Stoikov - PARTIALLY VERIFIED, and deliberately not upgraded to venue-specific. CrossRef and RePEc
confirm the journal article (Quantitative Finance 18(12), 1959-1966, 2018-09-03,
DOI 10.1080/14697688.2018.1489139) and the claim that the micro-price is empirically a better
predictor of short-term prices than the mid-price or weighted mid-price. Neither publisher metadata,
RePEc, nor the accessible SSRN page (HTTP 403) states the dataset, venue, instrument universe or
sample period. Per the iteration-4 instruction, the mechanism-level claim is retained as support
with transfer_status = CROSS_VENUE_EXTRAPOLATION and observed_venue = UNKNOWN, so it can no longer
carry venue-specific KG1 credit for the Nasdaq micro-price tuple. Locating a full-text or author
version is registered as UNK-0009-MECH-NASDAQ-MICRO.

Neither replacement supplies after-cost evidence, and neither changes a fee, fill or break-even
value. Gate changes are not proposed: gates are computed, and the effect of this patch appears
there.
"""

from __future__ import annotations

PATCH_ID = "P-0004"
ACCESS = "2026-09-20"


def _source(source_id, title, org, pub, date_basis, url, stype, limitations, scope, status):
    return {
        "source_id": source_id, "title": title, "authors_or_org": org,
        "publication_date": pub, "access_date": ACCESS, "date_basis": date_basis, "url": url,
        "doi": None, "source_type": stype, "primary_or_secondary": "primary_official",
        "market": "US equities", "venue": org, "sample_period": None, "sample_size": None,
        "methodology": "Author repository record and publisher metadata",
        "gross_or_net": "GROSS / predictive", "independent_replication": None,
        "limitations": limitations, "status": status, "claim_scope": scope,
    }


def _evidence(evidence_id, claim, source_id, observed, direction, limitations, implication,
              cls="SUPPORTED_FINDING", transfer="CLOSE_TRANSFER"):
    return {
        "evidence_id": evidence_id, "claim": claim, "source_id": source_id,
        "candidate_ids": observed["candidate_ids"], "mechanism_id": observed.get("mechanism_id"),
        "venue_id": observed["venue_id"], "epistemic_class": cls,
        "evidence_origin": "EXTERNAL_VERIFIED", "supports_or_weakens": direction,
        "methodology": observed["methodology"], "sample": observed["sample"],
        "temporal_scope": observed["temporal_scope"], "gross_or_net": "GROSS / predictive",
        "limitations": limitations, "decision_implication": implication,
        "contradicts_mechanism": "NO",
        "observed_market": observed["market"], "observed_venue": observed["venue_id"],
        "observed_instrument_or_universe": observed["universe"],
        "observed_period": observed["period"], "observed_horizon": observed["horizon"],
        "candidate_link_reason": observed["link_reason"], "transfer_status": transfer,
        "verification_status": "VERIFIED_PRIMARY_METADATA",
    }


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0023-LIT", "UNK-0009-MECH-NASDAQ-MICRO"],
        "candidate_ids": ["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
                          "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
                          "TUP-CME-ES-H1-QDEP-PAS"],
        "new_sources": [
            _source("SRC-0238",
                    "Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book "
                    "(arXiv record)",
                    "Martin D. Gould; Julius Bonart", "2015-12-11",
                    "arXiv submission date 2015-12-11; record accessed 2026-09-20",
                    "https://arxiv.org/abs/1512.03492", "academic_paper",
                    "Preprint: the record does not state the sample period, and the paper reports "
                    "predictive/gross evidence only - no trading costs, fills or P&L.",
                    "Author-repository record establishing the queue-imbalance predictive claim, "
                    "its Nasdaq sample and its tick-scale horizon.", "VERIFIED_REPLACEMENT"),
            _source("SRC-0239",
                    "The micro-price: a high-frequency estimator of future prices (publisher and "
                    "bibliographic metadata)",
                    "Sasha Stoikov; Quantitative Finance 18(12) 1959-1966", "2018-09-03",
                    "CrossRef and RePEc report publication 2018-09-03; DOIs and volume/page data "
                    "verified; accessed 2026-09-20",
                    "https://doi.org/10.1080/14697688.2018.1489139", "academic_paper",
                    "Publisher metadata and the published abstract establish the estimator claim "
                    "only: no dataset, venue, instrument universe, sample period or horizon is "
                    "stated in any accessible metadata, so the claim cannot be given "
                    "venue-specific scope.",
                    "Establishes the micro-price claim at mechanism level, not for any venue.",
                    "VERIFIED_REPLACEMENT"),
            _source("SRC-0240",
                    "Micro-price working paper record (SSRN abstract page)",
                    "Sasha Stoikov; SSRN", None,
                    "SSRN record accessed 2026-09-20; the page returned HTTP 403 so no "
                    "publication date or abstract text could be captured",
                    "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694",
                    "academic_paper",
                    "Retrieval failed (HTTP 403) during this iteration; recorded so a later "
                    "session does not repeat the attempt without a different access path (for "
                    "example an institutional login or an author copy).",
                    "Documents the attempt to reach the working paper for its sample details.",
                    "UNRESOLVED"),
        ],
        "new_evidence": [
            _evidence(
                "EVD-0064",
                "In a limit order book, bid/ask queue imbalance has a strongly statistically "
                "significant relationship with the direction of the next mid-price movement: "
                "logistic regressions fitted to 10 liquid Nasdaq stocks improve substantially on "
                "a null model for large-tick stocks and moderately for small-tick stocks, with "
                "local logistic regression slightly outperforming the parametric fit.",
                "SRC-0238",
                {"candidate_ids": "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
                 "mechanism_id": "MECH-QIMB", "venue_id": "VEN-NASDAQ-CONT",
                 "methodology": "Logistic and local-logistic regression of next-mid-price-move "
                                "direction on queue imbalance, per stock",
                 "sample": "10 liquid Nasdaq-listed stocks (large-tick emphasis)",
                 "temporal_scope": "study submitted 2015-12-11; sample period not stated in the "
                                   "abstract",
                 "market": "US equities", "universe": "10 liquid Nasdaq-listed stocks",
                 "period": "UNKNOWN (not stated in the abstract)",
                 "horizon": "one mid-price movement (tick-scale, not a time-based horizon)",
                 "link_reason": "Same venue (Nasdaq), same instrument class (large-tick Nasdaq "
                                "names) and the same mechanism (queue imbalance) as the linked "
                                "candidate. The horizon is tick-scale rather than the candidate's "
                                "100 ms-1 s band, which is why the transfer is CLOSE_TRANSFER and "
                                "not DIRECT."},
                "SUPPORTS",
                "Preprint; sample period unstated; predictive and gross only - no costs, fills or "
                "P&L; horizon expressed as a move rather than as elapsed time, so it cannot be "
                "read as a measured 100 ms-1 s effect.",
                "Replaces the report-mediated citation with an identified source that carries "
                "venue, instrument and horizon scope, so KG1 for the Nasdaq queue-imbalance tuple "
                "rests on a verifiable record.",
                transfer="CLOSE_TRANSFER"),
            _evidence(
                "EVD-0065",
                "The micro-price estimated from high-frequency data is empirically a better "
                "predictor of short-term prices than the mid-price or the weighted mid-price.",
                "SRC-0239",
                {"candidate_ids": "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
                 "mechanism_id": "MECH-MICRO", "venue_id": "VEN-NASDAQ-CONT",
                 "methodology": "Estimator construction and empirical comparison against "
                                "mid-price and weighted mid-price",
                 "sample": "UNKNOWN (not stated in any accessible metadata)",
                 "temporal_scope": "published 2018-09-03; sample period not stated",
                 "market": "UNKNOWN", "universe": "UNKNOWN", "period": "UNKNOWN",
                 "horizon": "short-term price prediction (unspecified horizon)",
                 "link_reason": "Linked administratively to the Nasdaq micro-price tuple for "
                                "context only. No observed venue, universe or period is stated in "
                                "any accessible metadata, so this record cannot carry "
                                "venue-specific credit."},
                "SUPPORTS",
                "Publisher metadata and the published abstract only: no dataset, venue, universe "
                "or horizon is stated, and no full text was accessible (SSRN returned HTTP 403). "
                "It is also an estimator-quality result, not after-cost evidence.",
                "Retains the micro-price claim at mechanism level while removing the claim to "
                "venue-specific support: KG1 for the Nasdaq micro-price tuple can no longer pass "
                "on this record alone, and UNK-0009-MECH-NASDAQ-MICRO records what is needed.",
                transfer="CROSS_VENUE_EXTRAPOLATION"),
        ],
        "proposed_candidate_updates": [],
        "modified_claims": [
            {"claim": "EVD-0012 (queue imbalance predicts the next mid-price move on Nasdaq, "
                      "report-mediated)",
             "status": "SUPERSEDED_BY_REPLACEMENT",
             "reason": "Re-derived from an identified author-repository record (EVD-0064). The "
                       "original token is retained for provenance as LEGACY_REPORT_MEDIATED and "
                       "no longer blocks M1. The replacement URL is the source of the claim; it "
                       "is NOT asserted to be the page the original token referred to."},
            {"claim": "EVD-0014 (micro-price improves on midpoint, report-mediated)",
             "status": "SUPERSEDED_BY_REPLACEMENT",
             "reason": "Re-derived at mechanism level from publisher metadata (EVD-0065), which "
                       "does NOT establish venue scope. Venue-specific KG1 credit is withdrawn "
                       "rather than transferred."},
        ],
        "proposed_issue_updates": [
            {"issue_id": "UNK-0023-LIT", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Gould & Bonart and Stoikov are now identified from "
                                "author/publisher records and their claims are re-derived; the "
                                "order-flow-imbalance claim (Cont, Kukanov & Stoikov) remains "
                                "report-mediated with an unresolved token."},
        ],
        "proposed_source_updates": [
            {"source_id": "SRC-0101",
             "fields": {"status": "LEGACY_REPORT_MEDIATED"},
             "reason": "Queue-imbalance claim re-derived from SRC-0238; the token is kept for "
                       "provenance and no longer blocks M1."},
            {"source_id": "SRC-0104",
             "fields": {"status": "LEGACY_REPORT_MEDIATED"},
             "reason": "Micro-price claim re-derived at mechanism level from SRC-0239."},
        ],
        "proposed_venue_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "SUPPORTS",
        "reason": "Two literature claims are moved from report-mediated citation to identified "
                  "sources with recorded empirical scope, and one of them (micro-price) is "
                  "explicitly denied venue-specific scope because the metadata does not support "
                  "it.",
        "verification_notes": "Contrary evidence and scope limits were searched for: the SSRN "
                              "working-paper page was attempted and returned HTTP 403, and no "
                              "arXiv preprint of the micro-price paper exists, so its sample was "
                              "not established and venue-specific credit was withheld rather than "
                              "assumed. The Gould & Bonart record's sample period is unstated in "
                              "the abstract, so observed_period is UNKNOWN and the horizon is "
                              "recorded as tick-scale with a CLOSE_TRANSFER rather than DIRECT. No "
                              "gate change is proposed: gates are computed from the evidence, and "
                              "no after-cost, fill or fee value is affected by this patch.",
        "status": "PROPOSED",
        "created_at": created_at,
    }