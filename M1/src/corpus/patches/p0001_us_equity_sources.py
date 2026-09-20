"""Code-authored evidence patch P-0001: US equity primary sources (Nasdaq, Cboe, NYSE, IEX).

Provenance: resolved by the `USEquityFacts` resolver run on 2026-09-20 (all access dates
2026-09-20). Every source carries its exact URL and a date or an explicit date basis. Where the
resolver's capture truncated a URL, the URL is recorded as UNKNOWN and the corroborating docket
is named instead: a guessed URL would be fabricated attribution.

What this patch changes, in decision terms:

* "Does order-level Nasdaq history exist at usable granularity?" is answered YES, with product,
  delivery mechanism and depth (2007-08-13 to present). The remaining unknown narrows to price
  and licence terms, which is now an executable external ask.
* Auction-imbalance history is not a separate purchase: NOII files have been included at no
  additional charge for Historical TotalView-ITCH subscribers since 2010-01-04.
* Nasdaq and Cboe BZX base-tier add/remove economics are now verified from primary schedules,
  including the fact that in both cases the standard displayed-add rate is a credit.
* Nasdaq and Cboe BZX passive priority mechanics are documented (price/display/time, and the
  BZX class order), which is the M1 requirement for a buildable fill model.
* Small-participant data and connectivity costs are now quantified from published Nasdaq and
  IEX price lists, which is a mandatory cost component rather than an unknown.

It does NOT claim any candidate is viable: no fill model, no markout, no half-life and no
break-even follows from these facts.
"""

from __future__ import annotations

PATCH_ID = "P-0001"
ACCESS = "2026-09-20"


def _source(source_id, title, org, pub, date_basis, url, stype, limitations, scope):
    return {
        "source_id": source_id,
        "title": title,
        "authors_or_org": org,
        "publication_date": pub,
        "access_date": ACCESS,
        "date_basis": date_basis,
        "url": url,
        "doi": None,
        "source_type": stype,
        "primary_or_secondary": "primary_official",
        "market": "US equities",
        "venue": org,
        "sample_period": None,
        "sample_size": None,
        "methodology": "Official product specification / price list / rulebook",
        "gross_or_net": "N/A",
        "independent_replication": None,
        "limitations": limitations,
        "status": "PARTIAL" if url is None else "VERIFIED",
        "claim_scope": scope,
    }


def _evidence(evidence_id, claim, source_id, candidates, venue_id, direction, limitations,
              implication, cls="CONSENSUS_FACT", verification="PRIMARY_DOCUMENT"):
    return {
        "evidence_id": evidence_id,
        "claim": claim,
        "source_id": source_id,
        "candidate_ids": candidates,
        "mechanism_id": None,
        "venue_id": venue_id,
        "epistemic_class": cls,
        "evidence_origin": "EXTERNAL_VERIFIED",
        "supports_or_weakens": direction,
        "methodology": "Primary venue documentation retrieved by the USEquityFacts resolver",
        "sample": "n/a (product specification / schedule / rulebook)",
        "temporal_scope": f"accessed {ACCESS}",
        "gross_or_net": "N/A",
        "limitations": limitations,
        "decision_implication": implication,
        "contradicts_mechanism": "NO",
        "verification_status": verification,
    }


_NASDAQ_CANDS = ("TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|"
                 "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG|"
                 "TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG")


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0004", "UNK-0005", "UNK-0020", "UNK-0022", "UNK-0023"],
        "candidate_ids": ["TUP-NASDAQ-LARGETICK-H2-QIMB-AGG",
                          "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
                          "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
                          "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS",
                          "TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG"],
        "new_sources": [
            _source("SRC-0201",
                    "NASDAQ Historical TotalView-ITCH - SFTP access specification",
                    "Nasdaq", None,
                    "Specification document is undated internally; directory layout reflects "
                    "current practice",
                    "https://www.nasdaqtrader.com/content/technicalSupport/specifications/"
                    "dataproducts/ITCHFTP.pdf",
                    "exchange_data_product",
                    "Price is not published in this document; access requires a Nasdaq Global "
                    "Data Agreement and a Data Feed Request Form; directory layout may lag "
                    "current practice.",
                    "Establishes the exact historical order-level product, its delivery path and "
                    "its depth for the Nasdaq book."),
            _source("SRC-0202",
                    "Nasdaq U.S. Equities Price List 2025/2026/2027 (display, non-display and "
                    "connectivity entitlements)",
                    "Nasdaq", "2024-12-31",
                    "Fee pages state effectiveness Jan 1 2025 / Jan 1 2026 / Jan 1 2027",
                    "https://www.nasdaqtrader.com/content/ProductsServices/PriceList/"
                    "Nasdaq_US_Equities_Price_List_2025_2026_2027.pdf",
                    "exchange_fee_schedule",
                    "Covers display and non-display entitlements and connectivity, not the "
                    "historical data files; monthly administration and connectivity are billed "
                    "separately.",
                    "Quantifies the small-participant market-data and connectivity cost floor."),
            _source("SRC-0203",
                    "Nasdaq trading price list (add/remove rates per share, equities >= $1)",
                    "Nasdaq", None,
                    "Page states the abbreviated schedule and cites Nasdaq Rulebook Equity 7 "
                    "Section 122 as the authoritative text; accessed 2026-09-20",
                    "https://www.nasdaqtrader.com/Trader.aspx?id=PriceListTrading2",
                    "exchange_fee_schedule",
                    "The page is explicitly abbreviated; several tier rungs are keyed to fixed "
                    "historical volume baselines that decay in relevance; the authoritative "
                    "text is the rulebook.",
                    "Supplies the first verified Nasdaq add/remove rates for the base tier."),
            _source("SRC-0204",
                    "Nasdaq Data Technical News #2009-59: NOII historical files provided with "
                    "Historical TotalView-ITCH",
                    "Nasdaq OMX Global Data Products", "2009-12-11",
                    "Notice dated Friday December 11, 2009; effective January 4, 2010",
                    "https://www.nasdaqtrader.com/TraderNews.aspx?id=dtn2009-059",
                    "exchange_notice",
                    "Free NOII files are conditional on a Historical TotalView-ITCH "
                    "subscription, which is quote-only; covers the Nasdaq book, not BX/PSX.",
                    "Resolves whether historical auction-imbalance data exists as a purchasable "
                    "product: it does, at no additional charge alongside the order-level "
                    "subscription."),
            _source("SRC-0205",
                    "Cboe U.S. Equities PITCH - historical depth-of-book archive (DataShop)",
                    "Cboe Global Markets", None,
                    "Product page current at access; history depth stated per exchange",
                    "https://datashop.cboe.com/cboe-us-equities-pitch",
                    "exchange_data_product",
                    "Price is not shown on the product page; purchase or a quote is required.",
                    "Confirms a Cboe depth-of-book historical product exists per exchange."),
            _source("SRC-0206",
                    "Cboe BZX U.S. Equities fee schedule (standard rates)",
                    "Cboe BZX Exchange, Inc.", "2026-09-01",
                    "Page banner states effective September 1, 2026; earlier updates noted "
                    "effective Feb 9 2026 and Jun 1 2026",
                    "https://www.cboe.com/us/equities/membership/fee_schedule/bzx",
                    "exchange_fee_schedule",
                    "Rebates shown in parentheses; tier qualification uses prior-month volume; "
                    "a pending FR-noticed change (SR-CboeBZX-2026-063, FR 91 No. 157, "
                    "2026-08-17) alters tiers.",
                    "Supplies verified BZX base add/remove rates and the tier structure."),
            _source("SRC-0207",
                    "Rules of Cboe BZX Exchange - Rule 11.12 Priority of Orders",
                    "Cboe BZX Exchange, Inc.", "2020-06-05",
                    "Rulebook PDF states update as of June 5, 2020 (transitional posting); rule "
                    "text confirmed against current-rule citations",
                    "https://cdn.cboe.com/resources/regulation/rule_book/transitional/"
                    "BATS_Exchange_Rulebook.pdf",
                    "exchange_rule_doc",
                    "Transitional posting; later amendments were reviewed through SEC filings and "
                    "did not change the class order of equal-priced interest.",
                    "Documents BZX passive priority (displayed before non-displayed at equal "
                    "price, then time), which a fill model depends on."),
            _source("SRC-0208",
                    "IEX fee schedule effective September 1, 2026",
                    "Investors Exchange LLC", "2026-09-01",
                    "Schedule states effective September 1, 2026 (October 1, 2026 version also "
                    "linked)",
                    "https://cdn.prod.website-files.com/696f8ac812dcabe749e3aa49/"
                    "6a95f612f0b949da3532ae49_Fee_Schedule_as_of_September%201%202026%20"
                    "(with%20revised%20external%20dist%20rebate%20%2B%20Oct%20link).pdf",
                    "exchange_fee_schedule",
                    "Tier thresholds are absolute share counts rather than consolidated-volume "
                    "shares, which is unusual and must not be compared across venues as if "
                    "equivalent.",
                    "Gives the one venue where a modest-size passive participant reaches a "
                    "rebate tier, plus published feed and connectivity prices."),
            _source("SRC-0209",
                    "NYSE Price List 2026",
                    "New York Stock Exchange LLC", "2026-08-11",
                    "Price list states last updated August 11, 2026",
                    "https://www.nyse.com/publicdocs/nyse/markets/nyse/NYSE_Price_List.pdf",
                    "exchange_fee_schedule",
                    "Tier criteria are prior-billing-month based and reference firm-specific "
                    "historical baselines.",
                    "Supplies the NYSE non-tier add credit and take charge for cross-venue "
                    "comparison."),
            _source("SRC-0210",
                    "Nasdaq NOIView specification (net order imbalance direct feed)",
                    "Nasdaq", None,
                    "Specification version 3.0 per index; accessed 2026-09-20",
                    "https://www.nasdaqtrader.com/content/technicalsupport/specifications/"
                    "dataproducts/NOIViewSpecification.pdf",
                    "exchange_api_doc",
                    "Real-time feed specification; real-time entitlement pricing is not "
                    "historical file pricing.",
                    "Documents the live auction-imbalance message set."),
            _source("SRC-0211",
                    "SEC notice: Extended Life Order exception to Nasdaq price/display/time "
                    "priority (FR 2017-22392)",
                    "SEC / The Nasdaq Stock Market LLC", "2017-10-17",
                    "Federal Register publication date",
                    "https://www.govinfo.gov/content/pkg/FR-2017-10-17/pdf/2017-22392.pdf",
                    "regulation",
                    "Establishes one documented exception to the priority algorithm (designated "
                    "retail ELO), not the general ranking rule.",
                    "Corroborates that the general Nasdaq ranking is price/display/time with "
                    "narrow exceptions."),
            _source("SRC-0212",
                    "Nasdaq Equity 4 Rule 4757 (Book Processing) - price/display/time priority",
                    "The Nasdaq Stock Market LLC / SEC", "2018-12-04",
                    "Corroborating Federal Register notice dated December 4, 2018 quoting the "
                    "ranking; direct rulebook fetch returned HTTP 403 and the exact URL is not "
                    "reproducible from the resolver capture",
                    None,
                    "exchange_rule_doc",
                    "URL NOT CAPTURED: the resolver's link was truncated, and the direct rulebook "
                    "fetch was blocked (HTTP 403). Recorded as PARTIAL with no URL rather than "
                    "guessing one; a browser-session fetch of the Nasdaq Equity 4 chapter is "
                    "required to confirm verbatim wording.",
                    "Supports the Nasdaq priority model but cannot be treated as verbatim until "
                    "the rulebook page is captured."),
        ],
        "new_evidence": [
            _evidence("EVD-0031",
                      "Nasdaq Historical TotalView-ITCH is a full-depth, order-level historical "
                      "product for the Nasdaq book: files from 2007-08-13 (ITCH v3.0) to present, "
                      "v5.0 from 2014-04-08, distributed over SFTP in BinaryFile format, "
                      "requiring a Nasdaq Global Data Agreement and a Data Feed Request Form. "
                      "Price is not published.",
                      "SRC-0201", _NASDAQ_CANDS, "VEN-NASDAQ-CONT", "NEUTRAL",
                      "Price/licence terms are not public; directory layout may lag practice; "
                      "delivery is T+1 for archived files.",
                      "Closes the 'does order-level Nasdaq history exist at usable granularity?' "
                      "question and narrows the blocker to price and licence terms."),
            _evidence("EVD-0032",
                      "Nasdaq publishes historical NOII auction-imbalance files (message types "
                      "I/T/S) on the Historical TotalView-ITCH SFTP, and states they are provided "
                      "at no additional charge to Historical TotalView-ITCH subscribers; "
                      "NOII-only history is supported from 2010-01-04 forward.",
                      "SRC-0204", "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG|" + _NASDAQ_CANDS,
                      "VEN-NASDAQ-AUCTION", "NEUTRAL",
                      "The zero-marginal-charge claim is conditional on the order-level "
                      "subscription whose price is quote-only; earlier history requires "
                      "processing the full ITCH log; Nasdaq book only.",
                      "Removes 'auction history is not sold separately' as a branch risk and "
                      "re-points the auction tuple's cost dependency at the ITCH subscription."),
            _evidence("EVD-0033",
                      "Nasdaq base-tier equity trading fees for securities >= $1: rebate to add "
                      "displayed liquidity of $0.0018/share (Tapes A and B) and $0.0013/share "
                      "(Tape C) for all other firms; fee to remove liquidity of $0.0030/share for "
                      "all MPIDs.",
                      "SRC-0203", _NASDAQ_CANDS, "VEN-NASDAQ-CONT", "WEAKENS",
                      "Page is abbreviated and the authoritative text is Nasdaq Equity 7 "
                      "section 122; remove-midpoint and M-ELO codes have their own rates; not "
                      "adjusted for broker/clearing pass-through.",
                      "Gives a verified mandatory cost component for the Nasdaq tuples: a passive "
                      "round trip is a credit of $0.0036/share at base tier, while a taker round "
                      "trip costs $0.0060/share, before spread, slippage and adverse selection."),
            _evidence("EVD-0034",
                      "Nasdaq displayed-add rebate tiers above the base rate require a firm "
                      "added-volume share of consolidated volume, with the published rungs "
                      "spanning roughly $0.0027-$0.00305/share and tier qualification criteria "
                      "keyed to fixed historical volume baselines.",
                      "SRC-0203", _NASDAQ_CANDS, "VEN-NASDAQ-CONT", "WEAKENS",
                      "The page states it is abbreviated; composite tier criteria are numerous "
                      "and several baselines expire.",
                      "A small participant should assume the base rate, not a mid-tier rate: "
                      "assuming an unreachable tier would understate costs."),
            _evidence("EVD-0035",
                      "Nasdaq Book orders are ranked by price, then display, then time (Rule "
                      "4757), with narrow exceptions such as the Extended Life Order for "
                      "designated retail orders; no 2024-2026 filing retrieved changes "
                      "displayed-versus-hidden ranking for regular securities.",
                      "SRC-0212", _NASDAQ_CANDS + "|TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG",
                      "VEN-NASDAQ-CONT", "NEUTRAL",
                      "Verbatim rulebook text was not captured (HTTP 403; URL not reproducible "
                      "from the capture), so this is corroborated rather than quoted.",
                      "A passive fill model for Nasdaq has a documented priority rule to "
                      "implement, and hidden orders never jump displayed interest at equal price."),
            _evidence("EVD-0036",
                      "Cboe BZX Rule 11.12 ranks equal-priced interest as displayed limit size, "
                      "then non-displayed limit, then non-displayed pegged, mid-point peg, "
                      "reserve size, discretionary, supplemental peg; any modification other "
                      "than a size decrease, Max Floor change, stop-price change or position "
                      "flip loses time priority.",
                      "SRC-0207", "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS", "VEN-CBOEBZX-EQ",
                      "NEUTRAL",
                      "Rulebook copy is a 2020 transitional posting; no later retrieved filing "
                      "changed the class order.",
                      "BZX queue modelling must treat replaces as queue loss and must rank "
                      "displayed size ahead of hidden interest."),
            _evidence("EVD-0037",
                      "Cboe BZX standard rates for securities >= $1, effective 2026-09-01: "
                      "displayed-add rebate of $0.0016/share, remove fee of $0.0030/share, with "
                      "codes B/V/Y tiered from $0.0020/share (>=0.06% ADAV) up to $0.0031/share "
                      "(>=1.00%).",
                      "SRC-0206", "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS", "VEN-CBOEBZX-EQ",
                      "WEAKENS",
                      "Tier qualification is prior-month based and a pending filing "
                      "(SR-CboeBZX-2026-063) changes tiers; realized codes depend on routing.",
                      "Confirms the BZX base-tier economics already recorded in EVD-0006 and adds "
                      "the tier structure and its inaccessibility at small size."),
            _evidence("EVD-0038",
                      "Cboe DataShop sells a historical daily depth-of-book archive of the PITCH "
                      "feed per exchange (BZX from January 2010, BYX from October 2010, "
                      "EDGA/EDGX from February 2011); price is not shown and requires a quote.",
                      "SRC-0205", "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS", "VEN-CBOEBZX-EQ",
                      "NEUTRAL",
                      "Price quote-only; archive contents are daily files rather than a "
                      "replay service.",
                      "Confirms a BZX depth archive exists, narrowing UNK-0022 to cost and "
                      "entitlement terms."),
            _evidence("EVD-0039",
                      "IEX fee schedule effective 2026-09-01: displayed adds are free at the base "
                      "tier (<3M displayed-add ADV) and rebated up to $0.0023/share at the top "
                      "tier; displayed removes are $0.0030/share ($0.0024 with >=25,000 "
                      "displayed-add ADV); DEEP full-depth real-time feed is priced at "
                      "$2,500/month and a 10G primary port at $7,000/month.",
                      "SRC-0208", "TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG", "VEN-USSTOCK-MULTI",
                      "NEUTRAL",
                      "Absolute-share tier thresholds are not comparable with "
                      "consolidated-volume thresholds at other venues; delayed feeds are free "
                      "but unusable for the hypothesised horizons.",
                      "Quantifies a transparent direct-feed path and shows a venue where the "
                      "base passive tier is not a cost, which matters for cross-venue routing "
                      "arithmetic rather than for any single-venue tuple."),
            _evidence("EVD-0040",
                      "NYSE Price List 2026 (last updated 2026-08-11): non-tier displayed-add "
                      "credit of $0.0012/share and take-liquidity charge of $0.0030/share for "
                      "securities >= $1, with tiered credits requiring >=0.22% adding ADV.",
                      "SRC-0209", "TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG", "VEN-USSTOCK-MULTI",
                      "NEUTRAL",
                      "Tier criteria reference firm-specific historical baselines; route and "
                      "fee-code specifics apply.",
                      "Provides the NYSE comparator needed before any cross-venue routing "
                      "assumption is written into a cost model."),
            _evidence("EVD-0041",
                      "Nasdaq market-data entitlements for a small direct recipient: Nasdaq Depth "
                      "Non-Display at $396 per subscriber per month at the 1-39 subscriber tier "
                      "(2025 schedule, $412 in 2026) plus a direct-access distribution fee of "
                      "$3,190 per firm per month (2025, $3,340 in 2026), with administration and "
                      "connectivity billed separately.",
                      "SRC-0202", _NASDAQ_CANDS, "VEN-NASDAQ-CONT", "WEAKENS",
                      "Per-subscriber tiers are by recipient count, not usage; connectivity and "
                      "administration are additional; prices are schedule values, not a quote.",
                      "Adds a mandatory recurring cost of roughly $3.6k/month before "
                      "connectivity, which any Nasdaq candidate must clear."),
            _evidence("EVD-0042",
                      "Nasdaq publishes connectivity and colocation prices, including a shared "
                      "4U cabinet block at $660/month (Nasdaq personnel access only), fibre "
                      "hand-off to Nasdaq 10Gb at $11,000/month plus $1,100 install, and "
                      "order-entry ports at $575/port/month.",
                      "SRC-0203",
                      "TUP-CME-ES-H1-QDEP-PAS|TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG|"
                      + _NASDAQ_CANDS,
                      "VEN-NASDAQ-CONT", "WEAKENS",
                      "Published prices for the named facilities; a colocated deployment "
                      "requirement would follow from the candidate's latency class, not from "
                      "this schedule alone.",
                      "Prices the infrastructure a latency-sensitive Nasdaq tuple would need, "
                      "which is a mandatory cost component rather than an unknown."),
        ],
        "modified_claims": [],
        "proposed_candidate_updates": [],
        "proposed_issue_updates": [
            {"issue_id": "UNK-0004", "from_status": "OPEN", "to_status": "EXTERNAL_REQUEST_READY",
             "resolution_note": "Product, granularity, delivery and depth confirmed from primary "
                                "sources (SRC-0201). Remaining unknown: price and licence terms, "
                                "which require a Nasdaq data quote."},
            {"issue_id": "UNK-0005", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Nasdaq base-tier add/remove rates verified (SRC-0203) and BZX "
                                "base rates confirmed (SRC-0206). Outstanding: broker routing "
                                "markup, realized fee codes, clearing/CAT pass-through."},
            {"issue_id": "UNK-0020", "from_status": "OPEN", "to_status": "RESOLVED_SUPPORTS",
             "resolution_note": "Historical NOII files are published and provided at no additional "
                                "charge for Historical TotalView-ITCH subscribers since "
                                "2010-01-04 (SRC-0204). The remaining cost dependency is the "
                                "order-level subscription recorded in UNK-0004."},
            {"issue_id": "UNK-0022", "from_status": "OPEN", "to_status": "EXTERNAL_REQUEST_READY",
             "resolution_note": "Cboe U.S. Equities PITCH depth archive confirmed per exchange "
                                "(BZX from January 2010); price and entitlements require a Cboe "
                                "quote (SRC-0205)."},
            {"issue_id": "UNK-0023", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Equities cluster resolved to primary URLs this iteration (12 "
                                "sources); CME, Hyperliquid, Eurex, Deribit and event-market "
                                "clusters remain report-mediated."},
        ],
        "proposed_venue_updates": [
            {"venue_id": "VEN-NASDAQ-CONT",
             "fields": {
                 "rebate_value": 0.0018, "rebate_unit": "USD_PER_SHARE",
                 "rebate_source_id": "SRC-0203",
                 "maker_side_is_rebate": "YES",
                 "maker_side_is_rebate_source_id": "SRC-0203",
                 "taker_fee_value": 0.0030, "taker_fee_unit": "USD_PER_SHARE",
                 "taker_fee_source_id": "SRC-0203",
                 "matching_algorithm_status": "PUBLISHED",
                 "matching_algorithm_source_id": "SRC-0212",
                 "historical_feed": "Order-level history confirmed: NASDAQ Historical "
                                    "TotalView-ITCH, files from 2007-08-13 to present, SFTP "
                                    "delivery, Nasdaq Global Data Agreement required; price "
                                    "quote-only.",
                 "historical_feed_source_id": "SRC-0201",
                 "L3_MBO_available": "TRUE",
                 "L2_available": "TRUE (displayed depth via TotalView); order-level history "
                                 "available for replay",
                 "fee_notes": "Base tier for securities >= $1: displayed-add rebate $0.0018/share "
                              "(Tapes A and B) and $0.0013/share (Tape C); remove fee "
                              "$0.0030/share for all MPIDs (SRC-0203, abbreviated page, "
                              "authoritative text Nasdaq Equity 7 s.122). Higher rebate tiers "
                              "require a consolidated-volume share unavailable to a small "
                              "participant.",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0201", "SRC-0203", "SRC-0212"],
             "reason": "Verified product existence, priority rule and base-tier fee schedule."},
            {"venue_id": "VEN-NASDAQ-AUCTION",
             "fields": {
                 "historical_feed": "NOII files (message types I/T/S) published on the "
                                    "Historical TotalView-ITCH SFTP at no additional charge to "
                                    "subscribers, supported from 2010-01-04 forward; earlier "
                                    "period requires processing the full ITCH log.",
                 "historical_feed_source_id": "SRC-0204",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0204"],
             "reason": "Auction-imbalance history is not a separate purchase."},
            {"venue_id": "VEN-CBOEBZX-EQ",
             "fields": {
                 "maker_side_is_rebate": "YES",
                 "maker_side_is_rebate_source_id": "SRC-0206",
                 "matching_algorithm_status": "PUBLISHED",
                 "matching_algorithm_source_id": "SRC-0207",
                 "historical_feed": "Cboe U.S. Equities PITCH daily depth-of-book archive per "
                                    "exchange (BZX from January 2010); price quote-only via "
                                    "DataShop.",
                 "historical_feed_source_id": "SRC-0205",
                 "fee_notes": "Standard rates effective 2026-09-01 for securities >= $1: "
                              "displayed-add rebate $0.0016/share, remove fee $0.0030/share; "
                              "codes B/V/Y tiered $0.0020-$0.0031/share at >=0.06%-1.00% ADAV "
                              "(SRC-0206).",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0205", "SRC-0206", "SRC-0207"],
             "reason": "Verified priority class order, base fee rates and the existence of a "
                       "depth archive."},
            {"venue_id": "VEN-USSTOCK-MULTI",
             "fields": {
                 "fee_notes": "Per-venue comparator rates, deliberately NOT collapsed into one "
                              "multi-venue fee value: NYSE non-tier add credit $0.0012/share and "
                              "take charge $0.0030/share (SRC-0209); IEX base tier displayed "
                              "adds free, removes $0.0030/share, DEEP feed $2,500/month and 10G "
                              "port $7,000/month (SRC-0208); Cboe BZX and Nasdaq as recorded on "
                              "their own rows.",
                 "access_notes": "A cross-venue tuple must be priced per venue; a single "
                                 "multi-venue fee number would be meaningless.",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0208", "SRC-0209"],
             "reason": "Comparator economics recorded without collapsing them into a false "
                       "single-venue value."},
        ],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [
            {"issue_id": "UNK-0033",
             "claim_needed": "Sponsored-access cost: broker commission/markup for routed order "
                             "flow, which no exchange or regulator publishes.",
             "known_evidence": "Exchange-side fee schedules are published per venue; the sponsor's "
                               "commission is a private contract, so the all-in cost of a "
                               "sponsored path cannot be assembled from public sources.",
             "specific_evidence_needed": "A chosen sponsor's published commission schedule or a "
                                         "written quote for the intended order flow.",
             "decision_prevented": "All-in per-share cost for every equity tuple, and therefore "
                                   "the cost floor used in KG3.",
             "severity": "BLOCKING", "resolution_method": "EXTERNAL_ACTION",
             "resolution_stage": "M1_BLOCKING", "tier": 3, "branch_impact": "MEDIUM",
             "kill_potential": "HIGH", "estimated_effort": "SMALL",
             "can_M2_measure": "NO", "requires_vendor_quote": "YES",
             "affected_candidate_ids": "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|"
                                       "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG|"
                                       "TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS|"
                                       "TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG",
             "migration_reason": "New blocker surfaced by primary-source research: the exchange "
                                 "side of equity cost is public, the sponsored-access side is "
                                 "not, and the project cannot trade directly on these venues."},
        ],
        "decision": "SUPPORTS",
        "reason": "Twelve primary sources replace report-mediated or missing equity facts: the "
                  "order-level Nasdaq product and its depth, the zero-marginal-charge NOII "
                  "history, base-tier add/remove schedules for Nasdaq and BZX, the documented "
                  "priority rules for both venues, NYSE/IEX comparators, and published "
                  "small-participant data and connectivity prices.",
        "verification_notes": "Contrary evidence was searched: no primary source indicates the "
                              "Nasdaq or Cboe order-level historical products have been withdrawn "
                              "or replaced, and no retrieved 2024-2026 filing changes displayed "
                              "versus hidden ranking at Nasdaq or BZX. The Nasdaq Rule 4757 "
                              "rulebook fetch returned HTTP 403 and its URL was truncated in the "
                              "capture, so that source is recorded as PARTIAL with url UNKNOWN "
                              "rather than given a guessed link. No gate change is proposed: the "
                              "facts narrow blockers and quantify mandatory costs, and none of "
                              "them supplies a fill model, a markout or a break-even.",
        "status": "PROPOSED",
        "created_at": created_at,
    }