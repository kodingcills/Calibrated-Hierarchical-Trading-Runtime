"""Code-authored evidence patch P-0007: queue identifiability on Nasdaq TotalView-ITCH.

Provenance: the provider's own TotalView-ITCH 5.0 specification (retained and hashed in this
repository) was read directly, and one primary regulatory filing was retrieved through the Federal
Register API on 2026-09-24. The filing is the Commission order approving Nasdaq's amendment to
Equity 4, Section 4703(h) concerning reserve orders (Release 34-91109, File SR-NASDAQ-2020-090,
86 FR 10141, published 2021-02-18).

What this patch establishes, in decision terms:

* Time priority among **displayed** orders at one price is reconstructible from the feed: the
  product carries per-order identity for every add, execution, partial cancel, delete and
  cancel-replace, and it disseminates payload messages in engine order. That is what makes a
  queue-aware passive fill model possible at all, and it is what the M2-1 candidate
  `TUP-NASDAQ-LARGETICK-H2-QIMB-PAS` needs before any fill, queue or markout number can be claimed.
* A cancel-replace carries a **new** order reference and the original's remaining shares become
  inaccessible, so a replacement cannot inherit the original's place in the queue.
* A reserve order's **replenished display receives a new timestamp** while the non-displayed
  portion keeps its timestamp, so a replenishment moves behind an order that was already resting.
* A match involving a **non-displayed** order is disseminated as a Trade (non-cross) message with
  no book identity, so hidden interest is not observable at the order level.

What it does NOT establish, and what the M2-1 model therefore does not assume:

* The verbatim text of Equity 4, Section 4703(h) as in force on 2019-07-30 could not be retrieved
  with the tooling available in this environment (the rulebook site is not fetchable, sec.gov
  returns HTTP 403, and the Federal Register API holds filings rather than the rulebook). The
  ranking of displayed against non-displayed interest at the same price is recorded as UNKNOWN.
  The fill model does not depend on it: it assumes displayed FIFO only and measures the residual
  through explicit priority-anomaly and hidden-flow counters, so a violation of that ranking can
  only make the measured fill count optimistic.
* No fill probability, adverse-selection or economic quantity follows from these facts.
"""

from __future__ import annotations

PATCH_ID = "P-0007"
ACCESS = "2026-09-24"


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0007", "UNK-0019"],
        "candidate_ids": ["TUP-NASDAQ-LARGETICK-H2-QIMB-PAS", "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG"],
        "new_sources": [{
            "source_id": "SRC-0243",
            "title": "Self-Regulatory Organizations; The Nasdaq Stock Market LLC; Order Approving "
                     "a Proposed Rule Change To Amend the Exchange's Rules at Equity 4, Section "
                     "4703(h) Relating to Reserve Orders (Release No. 34-91109; File No. "
                     "SR-NASDAQ-2020-090)",
            "authors_or_org": "U.S. Securities and Exchange Commission",
            "publication_date": "2021-02-18",
            "access_date": ACCESS,
            "date_basis": "Federal Register publication 2021-02-18 (86 FR 10141); retrieved "
                          "through the Federal Register API on the access date",
            "url": "https://www.federalregister.gov/documents/2021/02/18/2021-03214/"
                   "self-regulatory-organizations-the-nasdaq-stock-market-llc-order-approving-a-"
                   "proposed-rule-change-to",
            "doi": None,
            "source_type": "regulation",
            "primary_or_secondary": "primary_official",
            "market": "US equities",
            "venue": "Nasdaq",
            "sample_period": None,
            "sample_size": None,
            "methodology": "Commission order describing and approving the amended rule text for "
                           "reserve orders",
            "gross_or_net": "N/A",
            "independent_replication": None,
            "limitations": "Describes the rule as amended in 2021, which post-dates the 2019-07-30 "
                           "development tape. The behaviour it states (a replenished display "
                           "receives a new timestamp) is the long-standing one, and the amendment "
                           "it approves concerns locking behaviour rather than ranking, but the "
                           "rule text in force on the tape date was not independently retrieved.",
            "raw_citation_token": "code:P-0007",
            "local_path": None,
            "sha256": None,
            "status": "VERIFIED",
            "claim_scope": "Reserve-order replenishment ranking (new timestamp on the displayed "
                           "portion, retained timestamp on the non-displayed portion).",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0068",
            "claim": "Nasdaq's displayed order lifecycle is fully represented in TotalView-ITCH "
                     "with per-order identity (adds, executions, partial cancels, deletes, and "
                     "cancel-replaces that carry a new order reference and retire the original), "
                     "and the feed disseminates payload messages in engine order, so time priority "
                     "among displayed orders at one price is reconstructible. A replenished reserve "
                     "display receives a new timestamp while its non-displayed portion keeps its "
                     "timestamp (SEC Release 34-91109), and matches involving non-displayed orders "
                     "are disseminated as Trade (non-cross) messages carrying no book identity. "
                     "The verbatim ranking rule in force on the development tape date could not be "
                     "retrieved, so displayed-versus-non-displayed priority at one price remains "
                     "UNKNOWN and the queue model does not rely on it.",
            "source_id": "SRC-0243",
            "candidate_ids": "TUP-NASDAQ-LARGETICK-H2-QIMB-PAS|TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
            "mechanism_id": "MECH-QIMB",
            "venue_id": "VEN-NASDAQ-CONT",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "EXTERNAL_VERIFIED",
            "supports_or_weakens": "NEUTRAL",
            "methodology": "Direct reading of the provider specification retained in this "
                           "repository plus one primary Commission order retrieved through the "
                           "Federal Register API; the unverifiable component is recorded as "
                           "UNKNOWN rather than assumed.",
            "sample": "n/a (product specification and rule filing)",
            "temporal_scope": "specification revision of 2023-04-28 for the feed; rule amendment "
                              "approved 2021-02-11; tape date 2019-07-30",
            "gross_or_net": "N/A",
            "limitations": "Identifiability is a capability statement, not a fill or economic "
                           "result. The ranking of displayed against non-displayed interest at one "
                           "price is UNKNOWN for the tape date and is handled by measurement "
                           "counters, not by assumption.",
            "decision_implication": "A queue-aware passive fill model is identifiable from this "
                                    "feed for the axes that matter (displayed FIFO, cancel and "
                                    "replace semantics, reserve replenishment), which is the "
                                    "precondition for the M2-1 passive experiment to be evidence "
                                    "rather than assumption.",
            "contradicts_mechanism": "NO",
            "observed_market": "US equities",
            "observed_venue": "VEN-NASDAQ-CONT",
            "observed_instrument_or_universe": "Nasdaq-listed equity securities on the Nasdaq "
                                               "execution system",
            "observed_period": "product specification current at access; rule amendment 2021",
            "observed_horizon": "order lifetime",
            "candidate_link_reason": "Both the dead aggressive row and its passive pivot rest on "
                                     "the same feed and the same mechanism; this record states what "
                                     "the feed can and cannot support for queue reconstruction.",
            "transfer_status": "DIRECT_PRODUCT_SEMANTICS",
            "verification_status": "PRIMARY_DOCUMENT_PLUS_SPECIFICATION",
        }],
        "modified_claims": [],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "NO_CHANGE",
        "reason": "Queue identifiability is a precondition for measuring a passive fill model, not "
                  "an economic claim: no gate moves on this record.",
        "verification_notes": "Contrary evidence was searched before this patch: the possibility "
                              "that the feed omits displayed interest was checked against the "
                              "specification's own statement that Add Order messages are for the "
                              "displayable book, and the possibility that a replenishment or a "
                              "replace retains priority was checked against both the specification "
                              "(new reference, original inaccessible) and the Commission order "
                              "(new timestamp on the replenished display). The one component that "
                              "could not be verified (displayed-versus-non-displayed ranking on "
                              "the tape date) is recorded as UNKNOWN and is bounded by counters in "
                              "the experiment rather than assumed.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
