"""Code-authored evidence patch P-0003: CME cluster, partial resolution.

Provenance: `CMEFacts` resolver run on 2026-09-20 (access date 2026-09-20). The resolver
reported its own assignment as incomplete: fee-table reconstruction attempts failed on tooling
and the one fee figure it surfaced came from a non-primary source. That figure is **rejected**
here and recorded as a rejected claim rather than absorbed.

What this patch legitimately establishes:

* CME Globex matching is algorithm-based: the engine assigns one of nine documented algorithm
  codes per product, with split FIFO/pro-rata percentages set by product, and levels recomputed
  on a minute cycle. Product-level assignments were located for several products but **not** for
  ES or NQ, so the per-product rule for the project's two headline contracts stays unresolved.
* CME MDP 3.0 exposes two depth formats (10-deep MBP and full-depth MBOFD) and documents
  MDEntryTime and TransactTime tags, but does **not** document the clock domain (exchange event
  time versus receive time). That narrows the timestamp blocker to a question only the exchange
  can answer.
* DataMine publishes MBO FIX history from 2017-01-07, reported for COMEX/NYMEX; no price is
  published on the page. So historical order-level data exists for at least part of the complex,
  with coverage of CME/CBOT equity-index products unverified.
* iLink, colocation and latency figures are not published on the pages retrieved.

What this patch does NOT establish, and must not be read as establishing: any current CME fee
value. The public fee search is recorded as exhausted for this pass, and UNK-0001 becomes an
external request rather than continuing to be a research item.
"""

from __future__ import annotations

PATCH_ID = "P-0003"
ACCESS = "2026-09-20"

_CME_ALL = ("TUP-CME-ES-H1-QDEP-PAS|TUP-CME-ES-H3-OFI-AGG|TUP-CME-NQ-H3-OFI-AGG|"
            "TUP-CME-TSY-H2-QREPL-MIX|TUP-CME-WTI-H4-FLOWVOL-AGG")


def _source(source_id, title, org, pub, date_basis, url, stype, limitations, scope, status=None):
    return {
        "source_id": source_id, "title": title, "authors_or_org": org,
        "publication_date": pub, "access_date": ACCESS, "date_basis": date_basis, "url": url,
        "doi": None, "source_type": stype, "primary_or_secondary": "primary_official",
        "market": "Futures", "venue": org, "sample_period": None, "sample_size": None,
        "methodology": "Official client documentation (CME client wiki)",
        "gross_or_net": "N/A", "independent_replication": None, "limitations": limitations,
        "status": status or "VERIFIED", "claim_scope": scope,
    }


def _evidence(evidence_id, claim, source_id, candidates, venue_id, direction, limitations,
              implication, cls="CONSENSUS_FACT"):
    return {
        "evidence_id": evidence_id, "claim": claim, "source_id": source_id,
        "candidate_ids": candidates, "mechanism_id": None, "venue_id": venue_id,
        "epistemic_class": cls, "evidence_origin": "EXTERNAL_VERIFIED",
        "supports_or_weakens": direction,
        "methodology": "Primary venue documentation retrieved by the CMEFacts resolver",
        "sample": "n/a (documentation)", "temporal_scope": f"accessed {ACCESS}",
        "gross_or_net": "N/A", "limitations": limitations,
        "decision_implication": implication, "contradicts_mechanism": "NO",
        "verification_status": "PRIMARY_DOCUMENT",
    }


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0001", "UNK-0002", "UNK-0003", "UNK-0018"],
        "candidate_ids": _CME_ALL.split("|") + ["TUP-GENERIC-CME-QUEUE"],
        "new_sources": [
            _source("SRC-0235", "CME supported matching algorithms (nine algorithm codes)",
                    "CME Group", "2025-02-11",
                    "Client wiki page history shows an update dated 2025-02-11",
                    "https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/"
                    "457218479/Supported%2BMatching%2BAlgorithms",
                    "exchange_rule_doc",
                    "An official client wiki, not the rulebook; it names the algorithm codes and "
                    "the tags that carry them but does not state the per-product assignment for "
                    "every product, and does not state aggressor or priority semantics.",
                    "Establishes that CME matching is engine-assigned and product-specific, at "
                    "algorithm level."),
            _source("SRC-0236", "CME matching algorithm step matrix and split parameters",
                    "CME Group", None,
                    "Page history reports an update on 02-Jun with the year unverified by the "
                    "resolver",
                    "https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/"
                    "457218521",
                    "exchange_rule_doc",
                    "Same client-wiki caveat; the resolver flagged that the year of the update is "
                    "unverified, and that priority/aggressor semantics are not stated on the page.",
                    "Documents the split-parameter mechanism (FIFO share versus pro-rata share) "
                    "and the minute-cycle level recalculation."),
            _source("SRC-0237", "CME DataMine MBO FIX files (historical market-by-order)",
                    "CME Group", None,
                    "Page states the archive start date 2017-01-07; no update date captured",
                    "https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/"
                    "457223111/MBO+FIX",
                    "exchange_data_product",
                    "The resolver's capture states the coverage as COMEX/NYMEX; coverage of "
                    "CME/CBOT equity-index products was not verified, and no price is published "
                    "on the page.",
                    "Confirms historical order-level data exists for at least part of the CME "
                    "complex, with scope and price unresolved."),
        ],
        "new_evidence": [
            _evidence("EVD-0060",
                      "CME Globex assigns one of nine documented matching algorithm codes "
                      "(A, C, F, T, S, K, O, Q, V) per product; split algorithms carry a FIFO "
                      "share and a pro-rata share set by product, levels are recalculated on a "
                      "minute cycle, and an aggressor exceeding available quantity executes the "
                      "rest under FIFO even in a pro-rata market. Product-level assignments were "
                      "located for several products (for example an F-FIFO 100% assignment for a "
                      "Treasury-roll product and an F-FIFO assignment for EWF), but not for ES "
                      "or NQ.",
                      "SRC-0235", _CME_ALL + "|TUP-GENERIC-CME-QUEUE", "VEN-CME-ES", "NEUTRAL",
                      "Product-level assignment for ES and NQ was not located; aggressor and "
                      "priority semantics are not stated on the retrieved pages; a cited "
                      "Treasury-spread assignment dates from 2014 and later changes were not "
                      "located.",
                      "Upgrades the CME matching question from 'not researched' to 'engine-level "
                      "mechanism documented, product assignment missing'. A CME queue model "
                      "remains unimplementable for ES/NQ until the assignment is confirmed."),
            _evidence("EVD-0061",
                      "CME MDP 3.0 provides two market-data formats - 10-deep market-by-price and "
                      "full-depth market-by-order - and its documentation defines MDEntryTime and "
                      "TransactTime (nanosecond unit) tags, but does not state the clock domain "
                      "(exchange event time versus receive time) for either.",
                      "SRC-0235", _CME_ALL, "VEN-CME-ES", "NEUTRAL",
                      "The resolver's capture did not locate clock-domain documentation; tag "
                      "semantics alone do not establish ordering guarantees.",
                      "Narrows the timestamp blocker (UNK-0018) to a specific question for the "
                      "exchange: which field is exchange event time, and what ordering does it "
                      "guarantee?"),
            _evidence("EVD-0062",
                      "CME DataMine publishes market-by-order FIX history from 2017-01-07 "
                      "(coverage as captured: COMEX/NYMEX); no price is published on the "
                      "documentation page.",
                      "SRC-0237", _CME_ALL, "VEN-CME-ES", "NEUTRAL",
                      "Equity-index coverage (CME/CBOT) was not verified; pricing, licence terms "
                      "and delivery format are not published; the resolver's capture is on an "
                      "official client wiki rather than a commercial price page.",
                      "Historical order-level data exists for at least part of the complex, so "
                      "the CME replay blocker narrows from 'does such data exist' to 'does it "
                      "cover the exact contracts and at what cost' (UNK-0003)."),
            _evidence("EVD-0063",
                      "CME order-entry (iLink) fees, colocation requirements beyond a same-data-"
                      "centre-row statement, latency figures, and current fee-schedule values "
                      "were not retrievable from public pages during this resolution attempt; the "
                      "clearing-fee and fee-schedule pages were blocked and the one fee figure "
                      "surfaced came from a non-primary source.",
                      "SRC-0235", _CME_ALL, "VEN-CME-ES", "NEUTRAL",
                      "This is a negative result about publication and retrieval, not about CME: "
                      "the resolver reports its own fee-table reconstruction attempts failed on "
                      "tooling and describes the assignment as incomplete.",
                      "The CME cost and access questions cannot be closed from public sources in "
                      "this pass, so UNK-0001 becomes a vendor/broker request rather than a "
                      "continuing search item."),
        ],
        "modified_claims": [
            {"claim": "ES/NQ non-member per-side exchange fee is $1.28 per contract",
             "status": "REJECTED",
             "reason": "Sourced from a non-primary third-party article (dated 2026-06-11) during "
                       "a failed tool-assisted fee-table reconstruction; no primary fee schedule "
                       "or filed blackline was retrieved and no URL for the figure could be "
                       "recovered. Rejected rather than absorbed: a fee value that decides a "
                       "branch cannot come from an unverifiable secondary extraction."},
            {"claim": "COMEX/NYMEX MBOFIX coverage extends to CME/CBOT equity-index products",
             "status": "NOT_ASSERTED",
             "reason": "The resolver's capture states COMEX/NYMEX; extending it to ES/NQ would be "
                       "an inference about scope, so it is recorded as unverified instead."},
        ],
        "proposed_candidate_updates": [],
        "proposed_issue_updates": [
            {"issue_id": "UNK-0001", "from_status": "OPEN",
             "to_status": "EXTERNAL_REQUEST_READY",
             "resolution_note": "Public search exhausted for this pass: CME fee and "
                                "clearing-fee pages were blocked, no filed fee blackline was "
                                "extracted, and the single figure found was rejected as "
                                "non-primary. Requires a broker/FCM schedule for the project's "
                                "account path (packet in M1/work/external_requests/UNK-0001.md)."},
            {"issue_id": "UNK-0002", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Engine-level mechanism now documented: nine algorithm codes "
                                "assigned per product with split FIFO/pro-rata parameters and "
                                "minute-cycle level recalculation. Outstanding: the per-product "
                                "assignment for ES and NQ, and the aggressor/priority semantics "
                                "not stated on the retrieved pages."},
            {"issue_id": "UNK-0003", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Historical order-level data confirmed to exist (DataMine MBO FIX "
                                "from 2017-01-07, coverage as captured COMEX/NYMEX). "
                                "Outstanding: equity-index coverage, licence terms, delivery "
                                "format, timestamp fields and price."},
            {"issue_id": "UNK-0018", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Narrowed for CME: MDEntryTime and TransactTime tags are "
                                "documented with nanosecond units, but the clock domain and "
                                "ordering guarantees are not published. This is now a specific "
                                "question for CME market-data support rather than an open search."},
        ],
        "proposed_venue_updates": [
            {"venue_id": "VEN-CME-ES",
             "fields": {
                 "matching_algorithm_status": "ENGINE_ASSIGNED_PER_PRODUCT_ES_NQ_UNRESOLVED",
                 "matching_algorithm_source_id": "SRC-0235",
                 "historical_feed": "DataMine market-by-order FIX history from 2017-01-07 "
                                    "(coverage as documented: COMEX/NYMEX; equity-index coverage "
                                    "unverified); CME also advertises historical/real-time "
                                    "products up to full order book. No price published.",
                 "historical_feed_source_id": "SRC-0237",
                 "fee_notes": "Public fee search exhausted in this pass: fee and clearing-fee "
                              "pages blocked, no filed blackline extracted, one non-primary "
                              "figure rejected. All cost fields remain UNKNOWN pending a "
                              "broker/FCM quote for the project's account path.",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0235", "SRC-0237"],
             "reason": "Engine-level matching documented, MBO history located, fee search "
                       "recorded as exhausted."},
            {"venue_id": "VEN-CME-NQ",
             "fields": {
                 "matching_algorithm_status": "ENGINE_ASSIGNED_PER_PRODUCT_ES_NQ_UNRESOLVED",
                 "matching_algorithm_source_id": "SRC-0235",
                 "historical_feed": "DataMine market-by-order FIX history from 2017-01-07 "
                                    "(coverage as documented: COMEX/NYMEX; equity-index coverage "
                                    "unverified). No price published.",
                 "historical_feed_source_id": "SRC-0237",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0235", "SRC-0237"],
             "reason": "Same state as ES: no NQ-specific assignment was located."},
            {"venue_id": "VEN-CME-TSY",
             "fields": {
                 "matching_algorithm_status": "ENGINE_ASSIGNED_PER_PRODUCT_UNRESOLVED",
                 "matching_algorithm_source_id": "SRC-0235",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0235", "SRC-0236"],
             "reason": "Split-parameter mechanism documented; the current Treasury-spread "
                       "assignment was not located (the cited notice dates from 2014)."},
            {"venue_id": "VEN-CME-WTI",
             "fields": {
                 "matching_algorithm_status": "ENGINE_ASSIGNED_PER_PRODUCT_UNRESOLVED",
                 "matching_algorithm_source_id": "SRC-0235",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0235"],
             "reason": "Engine-level mechanism documented for the complex; product assignment "
                       "unresolved."},
        ],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "decision": "WEAKENS",
        "reason": "Partial resolution: the CME matching mechanism, MDP formats and MBO history "
                  "existence are now documented from primary client documentation, while the "
                  "product-level assignment for ES/NQ, the clock domain, and every fee value "
                  "remain unresolved. The resolver reported its own fee extraction as failed, so "
                  "the patch weakens the 'this is cheaply researchable' assumption for CME costs "
                  "rather than pretending the search succeeded.",
        "verification_notes": "Contrary evidence and failure were searched for and recorded: the "
                              "resolver reports tooling failure on fee-table reconstruction and "
                              "describes its own assignment as incomplete, so the single fee "
                              "figure it surfaced was placed in modified_claims as REJECTED and no "
                              "fee value entered the venue rows. The MBOFIX coverage was not "
                              "extended from COMEX/NYMEX to CME/CBOT without evidence. No gate "
                              "change is proposed: with the per-product matching assignment "
                              "unresolved for ES/NQ, KG3 stays BLOCKED for the passive CME tuple "
                              "and KG2 stays BLOCKED for all CME rows.",
        "status": "PROPOSED",
        "created_at": created_at,
    }