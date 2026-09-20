"""Code-authored evidence patch P-0002: crypto and event-market primary sources.

Provenance: resolved by the `CryptoEventFacts` resolver on 2026-09-20 (all access dates
2026-09-20). Hyperliquid, Deribit, Kalshi and Polymarket/Polymarket-US documentation, terms,
regulator releases and court material.

What this patch changes, in decision terms:

* Hyperliquid perp fees are now verified at the base tier (taker 0.045%, maker 0.015%, with
  documented tier/staking/referral modifiers), and an official historical archive exists
  (requester-pays S3, hourly L2 plus fills), so the seconds-scale Hyperliquid tuples stop being
  fee-unknown and data-unknown. The archive's cadence is approximate and expressly not
  guaranteed, which is a limitation rather than a blocker.
* Market-wide liquidation observability on Hyperliquid is NOT officially provided: liquidation
  fields are user-scoped. The liquidation variant of the H3 tuple therefore loses its
  observability premise.
* Deribit publishes a bps fee table with premium caps, and documents public historical trade /
  funding / settlement backfill - but no bulk historical option-book archive.
* Event markets: Kalshi's fee is a price-dependent formula (taker multiplier times P(1-P)) with a
  zero default maker multiplier, and its restricted-jurisdiction list plus adverse Washington and
  Nevada orders mean state access is actively contested in both directions (the Third Circuit
  preemption holding cuts the other way).
* A new M1 blocker is registered that no research can resolve: the operator's own jurisdiction
  and client classification. Four venue families (Hyperliquid, Deribit, Kalshi, Polymarket) turn
  on it, and guessing it would be fabrication.
* A second new blocker records that several of these fee pages are dynamic with no published
  effective date or version archive, so a fee snapshot must be taken and version-controlled by
  the project rather than assumed stable.

It does NOT claim any candidate is viable: no fill model, markout, half-life or break-even
follows from these facts.
"""

from __future__ import annotations

PATCH_ID = "P-0002"
ACCESS = "2026-09-20"

_HL = "TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS|TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG|" \
      "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"
_KALSHI = "TUP-KALSHI-EVENT-H5-EVENTINF-AGG"
_POLY = "TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG"


def _source(source_id, title, org, pub, date_basis, url, stype, limitations, scope, status=None):
    return {
        "source_id": source_id, "title": title, "authors_or_org": org,
        "publication_date": pub, "access_date": ACCESS, "date_basis": date_basis, "url": url,
        "doi": None, "source_type": stype, "primary_or_secondary": "primary_official",
        "market": None, "venue": org, "sample_period": None, "sample_size": None,
        "methodology": "Official venue documentation / terms / regulator release",
        "gross_or_net": "N/A", "independent_replication": None, "limitations": limitations,
        "status": status or ("VERIFIED" if url else "PARTIAL"), "claim_scope": scope,
    }


def _evidence(evidence_id, claim, source_id, candidates, venue_id, direction, limitations,
              implication, cls="CONSENSUS_FACT", verification="PRIMARY_DOCUMENT"):
    return {
        "evidence_id": evidence_id, "claim": claim, "source_id": source_id,
        "candidate_ids": candidates, "mechanism_id": None, "venue_id": venue_id,
        "epistemic_class": cls, "evidence_origin": "EXTERNAL_VERIFIED",
        "supports_or_weakens": direction,
        "methodology": "Primary venue documentation retrieved by the CryptoEventFacts resolver",
        "sample": "n/a (documentation / terms / regulator release)",
        "temporal_scope": f"accessed {ACCESS}", "gross_or_net": "N/A",
        "limitations": limitations, "decision_implication": implication,
        "contradicts_mechanism": "NO", "verification_status": verification,
    }


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0010", "UNK-0013", "UNK-0014"],
        "candidate_ids": _HL.split("|") + [_KALSHI, _POLY, "TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX"],
        "new_sources": [
            _source("SRC-0213", "Hyperliquid trading fees (perps, HIP-3 perps, spot)",
                    "Hyperliquid documentation", None,
                    "Page states no explicit effective date; rates are volume/tier dependent and "
                    "accessed 2026-09-20",
                    "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees",
                    "exchange_fee_schedule",
                    "The page is dynamic with no published effective date or version archive; "
                    "named referral tiers, staking multipliers, aligned quote assets and HIP-3 "
                    "settings change the displayed base rate.",
                    "Gives a verified base-tier fee for the Hyperliquid perp tuples."),
            _source("SRC-0214", "Hyperliquid historical data (official archive)",
                    "Hyperliquid documentation", None,
                    "Page states no date; access 2026-09-20",
                    "https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data.md",
                    "exchange_data_product",
                    "S3 is requester-pays so transfer cost is borne by the requester; updates are "
                    "approximately monthly with no timeliness or completeness guarantee; the page "
                    "states no other datasets (candles, spot asset data) are provided.",
                    "Confirms an official event-level archive exists for L2 and fills, with "
                    "cadence caveats."),
            _source("SRC-0215", "Hyperliquid info endpoint (l2Book, userFillsByTime)",
                    "Hyperliquid documentation", None, "Page states no date; access 2026-09-20",
                    "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/"
                    "info-endpoint.md",
                    "exchange_api_doc",
                    "l2Book returns at most 20 levels per side and reports an order COUNT per "
                    "level, not order identifiers; userFillsByTime is user-scoped with only the "
                    "10,000 most recent fills.",
                    "Bounds what can be reconstructed: market-by-price, not market-by-order."),
            _source("SRC-0216", "Hyperliquid WebSocket subscriptions (l2Book, bbo, trades)",
                    "Hyperliquid documentation", None, "Page states no date; access 2026-09-20",
                    "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/"
                    "websocket/subscriptions.md",
                    "exchange_api_doc",
                    "The documented snapshot rule is 'at least 0.5 seconds' between pushes and "
                    "does not promise every block is delivered; fast is 5 levels; the trades "
                    "schema documents no liquidation flag.",
                    "Confirms the feed cadence and level semantics that the H1 kill rests on."),
            _source("SRC-0217", "Hyperliquid liquidation mechanics",
                    "Hyperliquid documentation", None, "Page states no date; access 2026-09-20",
                    "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/liquidations.md",
                    "exchange_api_doc",
                    "Documents mechanics (partial liquidation of large positions, backstop vault) "
                    "but the only liquidation surfaces found are user-scoped.",
                    "Mechanics are documented; a complete market-wide liquidation tape is not."),
            _source("SRC-0218", "Hyperliquid terms of use (Restricted Persons)",
                    "Hyperliquid Corp.", None,
                    "Terms page shows no last-updated date; accessed 2026-09-20",
                    "https://app.hyperliquid.xyz/terms", "regulation",
                    "Concerns the interface and interaction through it; the terms state the "
                    "interface is not the exclusive means of access, so direct protocol "
                    "interaction is not resolved by this document.",
                    "Documents that interface access is unavailable to US and Ontario persons."),
            _source("SRC-0219", "Deribit fees (futures, perps, options, delivery, liquidation)",
                    "Deribit Support", "2026-09-14",
                    "Support page updated 2026-09-14; fee rates labelled upcoming with an "
                    "announced effective date of 2026-08-01",
                    "https://support.deribit.com/hc/en-us/articles/25944746248989-Fees",
                    "exchange_fee_schedule",
                    "The page gives one update date rather than a versioned effective-date table "
                    "per row; spot-book pairs are 0/0 while routed pairs use the table; "
                    "liquidation fees are fixed and not discounted.",
                    "Supplies a bps fee table with premium caps for an options tuple."),
            _source("SRC-0220", "Deribit market-data collection best practices",
                    "Deribit API documentation", None, "Page states no date; access 2026-09-20",
                    "https://docs.deribit.com/articles/market-data-collection-best-practices.md",
                    "exchange_api_doc",
                    "Subscriptions deliver only from subscription time; raw channels may be "
                    "coalesced under load; 100ms and agg2 are not raw L2; Starbase L3 is "
                    "selected-client only.",
                    "Bounds replay fidelity and forces channel accounting."),
            _source("SRC-0221", "Deribit restricted jurisdictions",
                    "Deribit Support", "2026-03-19",
                    "Support page updated 2026-03-19", 
                    "https://support.deribit.com/hc/en-us/articles/25944487427741-Restricted-"
                    "Jurisdictions",
                    "regulation",
                    "The list prohibits the United States and other named jurisdictions and does "
                    "not list EU/EEA countries generally, but 'EU-based' is not a single legal "
                    "classification and product/client classification rules apply.",
                    "Documents a hard access blocker for a US operator and an unresolved "
                    "eligibility question otherwise."),
            _source("SRC-0222", "Kalshi fee schedule (event contracts and perpetual futures)",
                    "Kalshi", "2026-07-07",
                    "Schedule states effective 2026-07-07",
                    "https://demo.kalshi.co/docs/kalshi-fee-schedule.pdf",
                    "exchange_fee_schedule",
                    "The production URL returned HTTP 429 at access time; this is the same titled "
                    "schedule on the official demo host and links the production fee page. "
                    "Non-standard series multipliers change the formula.",
                    "Supplies the fee formula shape: price-dependent, not a flat rate."),
            _source("SRC-0223", "Kalshi historical data endpoints and cutoffs",
                    "Kalshi API documentation", None, "Page states no date; access 2026-09-20",
                    "https://docs.kalshi.com/getting_started/historical_data.md",
                    "exchange_api_doc",
                    "Historical access is trade-level with cutoff mechanics that move over time; "
                    "no documented full-depth order-book event archive; retention beyond the "
                    "cutoff is not guaranteed.",
                    "Clears trade-based backtesting and leaves book replay unresolved."),
            _source("SRC-0224", "Kalshi member agreement (restricted jurisdictions)",
                    "Kalshi", None,
                    "Agreement copy carries no visible version date; accessed 2026-09-20",
                    "https://kalshi-public-docs.s3.amazonaws.com/kalshi-member-agreement.pdf",
                    "regulation",
                    "Lists many restricted countries (including the UK, France, Poland, Canada and "
                    "Australia) but does not itself list US states.",
                    "Shows that non-US access is narrower than assumed, while US state status "
                    "needs separate sources."),
            _source("SRC-0225", "Washington Attorney General release: court order affecting "
                                "Kalshi operations",
                    "Washington State Attorney General", "2026-08-13",
                    "Release dated 2026-08-13 describing a King County Superior Court order",
                    "https://www.atg.wa.gov/news/news-releases/judge-orders-kalshi-cease-"
                    "numerous-washington-operations",
                    "government_notice",
                    "Describes an order with geofencing deadlines, not a final merits judgment, "
                    "and applies to specified contract categories in one state.",
                    "Documents an active state-level access restriction despite federal-preemption "
                    "litigation elsewhere."),
            _source("SRC-0226", "Nevada Gaming Control Board release: Kalshi sports-prediction "
                                "business halted in Nevada",
                    "Nevada Gaming Control Board", "2026-07-24",
                    "Release dated 2026-07-24 describing a 2026-05-18 preliminary injunction and "
                    "geofencing agreement with penalty exposure",
                    "https://www.gaming.nv.gov/siteassets/content/about/press-release/"
                    "nevada-gaming-control-board-shuts-down-kalshis-sports-prediction-market-"
                    "business-in-nevada.pdf",
                    "government_notice",
                    "Category-specific (sports/election/entertainment contracts) and single-state; "
                    "penalty figures are enforcement terms, not costs of trading.",
                    "Second active adverse state restriction: state access cannot be assumed."),
            _source("SRC-0227", "Third Circuit opinion on New Jersey enforcement against "
                                "CFTC-licensed sports contracts",
                    "US Court of Appeals for the Third Circuit", "2026-04-06",
                    "Opinion dated 2026-04-06; retrieved from a public case-law host rather than "
                    "the court's own domain",
                    "https://law.justia.com/cases/federal/appellate-courts/ca3/25-1922/"
                    "25-1922-2026-04-06.html",
                    "regulation",
                    "The host is a reprint service; the holding concerns sports-related contracts "
                    "and state-law enforcement, and is not a nationwide determination.",
                    "The legal picture is genuinely two-sided: preemption has been upheld in one "
                    "circuit while state injunctions are active elsewhere."),
            _source("SRC-0228", "Polymarket fee schedule (category-specific, takers only)",
                    "Polymarket", None, "Page states no date; access 2026-09-20",
                    "https://docs.polymarket.com/trading/fees", "exchange_fee_schedule",
                    "Rates are per category and per market configuration; the market object is "
                    "authoritative; no dated fee-version archive is published; makers are never "
                    "charged and some categories are fee-free.",
                    "A single fee number would be wrong: cost must be joined per market."),
            _source("SRC-0229", "Polymarket terms of service (US blocking, circumvention "
                                "prohibition)",
                    "Polymarket", None, "Page states no date; access 2026-09-20",
                    "https://polymarket.com/tos", "regulation",
                    "Refers to the international service; the separate US product is documented "
                    "elsewhere and has its own eligibility rules.",
                    "Documents that a US person cannot use the international venue."),
            _source("SRC-0230", "Polymarket US product description (CFTC-regulated DCM/DCO)",
                    "QCX LLC d/b/a Polymarket US", None,
                    "Docs page states no date; metadata indicates 2026 content; accessed 2026-09-20",
                    "https://docs.polymarket.us/getting-started/what-is-polymarket-us.md",
                    "regulation",
                    "States sports markets are available and other categories are coming soon; "
                    "does not publish a complete state-by-state eligibility list.",
                    "Establishes that the US-accessible product is a different venue with "
                    "different instruments."),
            _source("SRC-0231", "CFTC settlement with Blockratize/Polymarket.com",
                    "US Commodity Futures Trading Commission", "2022-01-03",
                    "CFTC release and order dated 2022-01-03",
                    "https://www.cftc.gov/PressRoom/PressReleases/8478-22", "regulation",
                    "Concerns the prior international operator and the historical contract "
                    "wind-down; it does not certify current US product access.",
                    "Any historical Polymarket dataset must be labelled by entity and era."),
            _source("SRC-0232", "Polymarket public API reference and rate limits",
                    "Polymarket", None, "Pages state no date; access 2026-09-20",
                    "https://docs.polymarket.com/api-reference/rate-limits.md",
                    "exchange_api_doc",
                    "Documents price-history and trade endpoints with IP-based limits plus a "
                    "per-signer order limiter; the available history window is not stated; price "
                    "history is aggregated, not a full book replay.",
                    "Clears trade/price studies and leaves book replay unresolved."),
            _source("SRC-0233", "Polymarket US reporting documentation (historical floor)",
                    "Polymarket US", None,
                    "Reporting docs state a historical floor of 2026-05-01; accessed 2026-09-20",
                    "https://docs.polymarket.us/trader-guide/reporting.md",
                    "exchange_api_doc",
                    "Reports are authenticated and participant-scoped; retention beyond the "
                    "documented floor is described only as 'according to regulatory "
                    "requirements'.",
                    "Bounds what a US-product study could reconstruct from official data."),
            _source("SRC-0234", "Tardis.dev published data-plan prices (third-party vendor)",
                    "Tardis.dev", None,
                    "Pricing page carries no explicit date; coverage dates stated per venue; "
                    "accessed 2026-09-20",
                    "https://tardis.dev/", "vendor_price_list",
                    "A vendor's own published price list, not a venue fact: plans are not "
                    "venue-only, symbol/date inclusion is not proven, and coverage dates differ "
                    "per venue (Hyperliquid from 2024-10-29, Deribit from 2019-03-30).",
                    "Gives an order-of-magnitude vendor cost for replay data without pretending "
                    "it is a venue quote."),
        ],
        "new_evidence": [
            _evidence("EVD-0043",
                      "Hyperliquid perp fees are assessed on rolling 14-day volume; base tier "
                      "(< $5m) taker/maker 0.045%/0.015%, with tier rungs to 0.024%/0% above $7b "
                      "and documented staking (5%-40%) and referral modifiers; maker-volume "
                      "rebates of 0.001%-0.003% apply above 0.5%-3.0% maker share.",
                      "SRC-0213", _HL, "VEN-HYPERLIQUID-BTCPERP", "WEAKENS",
                      "Page has no published effective date or version archive; referral, "
                      "staking, quote-asset and HIP-3 settings change the applicable rate.",
                      "Removes 'fee schedule unknown' as a blocker for the Hyperliquid tuples: a "
                      "small account's aggressive round trip is 9 bps before spread and slippage."),
            _evidence("EVD-0044",
                      "Hyperliquid publishes an official historical archive at requester-pays S3 "
                      "with hourly L2 book files, asset contexts, and per-block node fills/trades; "
                      "updates are approximately monthly with no timeliness or completeness "
                      "guarantee, and no candle or spot-asset dataset is provided.",
                      "SRC-0214", _HL, "VEN-HYPERLIQUID-BTCPERP", "NEUTRAL",
                      "Requester-pays transfer cost is a variable cost with no published fixed "
                      "price; completeness per hour/symbol is not guaranteed; the archive is "
                      "market-by-price.",
                      "Clears the 'no historical replay source' blocker while leaving cadence and "
                      "cost as recorded risks; a replay study must state its missing-data rule."),
            _evidence("EVD-0045",
                      "Hyperliquid's l2Book returns at most 20 levels per side and reports an "
                      "order count per level rather than order identifiers; the documented "
                      "WebSocket snapshot rule is at least 0.5 seconds between pushes and does "
                      "not promise every block is delivered.",
                      "SRC-0216", _HL, "VEN-HYPERLIQUID-BTCPERP", "WEAKENS",
                      "At-least-0.5s is a snapshot rule, not a guaranteed rate; fast mode is only "
                      "5 levels; order counts cannot reconstruct queue position.",
                      "Confirms market-by-price only: queue-position and full-depth hypotheses are "
                      "unsupported by the public feed, which is why the H1 tuple stays dead."),
            _evidence("EVD-0046",
                      "Hyperliquid documents liquidation mechanics (partial liquidation of "
                      "positions above 100k USDC at 20%, backstop liquidation via the vault) and "
                      "exposes liquidation fields only in user-scoped surfaces "
                      "(userEvents, userNonFundingLedgerUpdates, fill markers).",
                      "SRC-0217", "TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG",
                      "VEN-HYPERLIQUID-BTCPERP", "WEAKENS",
                      "No official endpoint emits a complete market-wide liquidation tape; a "
                      "market-wide reconstruction from public fills is not guaranteed complete.",
                      "The liquidation variant of the H3 tuple loses its observability premise: "
                      "market-wide liquidation flow is not officially observable."),
            _evidence("EVD-0047",
                      "Hyperliquid's interface terms exclude Restricted Persons, explicitly "
                      "including persons or entities residing, located, incorporated or "
                      "registered in the United States or Ontario, Canada; outcome markets add a "
                      "separate Excluded Persons list.",
                      "SRC-0218", _HL, "VEN-HYPERLIQUID-BTCPERP", "WEAKENS",
                      "Concerns the interface; the terms state the interface is not the exclusive "
                      "means of access, so direct protocol interaction is not resolved.",
                      "Turns the project's own jurisdiction into a binding M1 input for this "
                      "venue family rather than a footnote."),
            _evidence("EVD-0048",
                      "Deribit's published fee table (updated 2026-09-14, rates effective "
                      "2026-08-01) quotes perps/futures maker/taker at 1.5/3.5 bps at the "
                      "standard tier and options at 3/3 bps, with option fees capped as a "
                      "percentage of premium and a fixed 1% liquidation fee on "
                      "BTC/ETH/USDC futures and perps.",
                      "SRC-0219", "TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX", "VEN-DERIBIT-BTCOPT",
                      "WEAKENS",
                      "One update date rather than a per-row versioned table; delivery, combo and "
                      "product-specific liquidation formulas also apply.",
                      "Supplies a bps fee basis for an options tuple, including the premium cap "
                      "that a naive per-contract fee would miss."),
            _evidence("EVD-0049",
                      "Deribit documents official public historical backfill for trades, funding, "
                      "mark price and settlements, and states that WebSocket subscriptions "
                      "deliver only from subscription time; raw, 100ms and agg2 channels differ, "
                      "with coalescing possible under load and change_id continuity fields "
                      "available.",
                      "SRC-0220", "TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX", "VEN-DERIBIT-BTCOPT",
                      "NEUTRAL",
                      "No official bulk historical option-book archive is documented; own-trade "
                      "history is not market-wide; channel choice changes replay fidelity.",
                      "Trade-based studies are officially supported; full book reconstruction "
                      "requires recording or a vendor archive (see EVD-0059)."),
            _evidence("EVD-0050",
                      "Deribit's restricted-jurisdiction page (updated 2026-03-19) prohibits use "
                      "where located, incorporated, established or resident in listed "
                      "jurisdictions including the United States, and does not list EU/EEA "
                      "countries generally; client classification alters product access in some "
                      "listed countries.",
                      "SRC-0221", "TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX", "VEN-DERIBIT-BTCOPT",
                      "WEAKENS",
                      "'EU-based' is not a single legal classification, and the page certifies "
                      "neither every member state nor server versus entity location.",
                      "A US operator faces a documented hard block; any other operator needs an "
                      "entity/client compliance check before the venue can be used."),
            _evidence("EVD-0051",
                      "Kalshi's event-contract taker fee is round_up(M x 0.07 x C x P x (1-P)) "
                      "with the maker multiplier defaulting to zero unless a product-specific "
                      "table indicates otherwise; settlement and membership fees are zero, and a "
                      "separate perpetual-futures schedule runs 12.0 to 2.6 bps by volume tier.",
                      "SRC-0222", _KALSHI, "VEN-KALSHI-EVENT", "WEAKENS",
                      "Production fee page returned HTTP 429 at access time and this is the "
                      "demo-hosted copy; non-standard series multipliers can change the formula.",
                      "Cost is price-dependent rather than a flat bps: every event-market cost "
                      "model must carry the multiplier and the rounding rule."),
            _evidence("EVD-0052",
                      "Kalshi publishes official historical endpoints (cutoff, markets, "
                      "candlesticks, trades) with per-data-type live/history boundaries and "
                      "cursor pagination, and publishes token-bucket rate limits "
                      "per account tier; no official full-depth order-book archive is documented.",
                      "SRC-0223", _KALSHI, "VEN-KALSHI-EVENT", "NEUTRAL",
                      "Cutoffs move over time and retention beyond them is not guaranteed; "
                      "trade-level history is not queue-level replay.",
                      "Trade-based backtesting is available without a purchase; queue modelling "
                      "is not cleared by official sources."),
            _evidence("EVD-0053",
                      "Kalshi's member agreement lists extensive non-US restricted jurisdictions "
                      "(including the UK, France, Poland, Canada, Australia, Singapore and "
                      "Thailand) and defers US state restrictions to applicable law.",
                      "SRC-0224", _KALSHI, "VEN-KALSHI-EVENT", "WEAKENS",
                      "Agreement copy carries no visible version date; it does not itself list US "
                      "states.",
                      "Non-US operation is narrower than commonly assumed, and the US question "
                      "must be answered from state-level sources."),
            _evidence("EVD-0054",
                      "Active US state restrictions exist against Kalshi: Washington's Attorney "
                      "General announced a King County Superior Court order (2026-08-13) covering "
                      "sports, elections, politics, entertainment, culture, technology and "
                      "mentions contracts with geofencing deadlines, and Nevada's Gaming Control "
                      "Board announced (2026-07-24) a 2026-05-18 injunction halting "
                      "sports/election/entertainment contracts with penalty exposure.",
                      "SRC-0225", _KALSHI, "VEN-KALSHI-EVENT", "WEAKENS",
                      "Both are category- and state-specific orders rather than final merits "
                      "judgments, and the sources do not establish every other state's status.",
                      "State access cannot be assumed; an access matrix must be maintained, and "
                      "the event-market branch carries a live legal risk rather than a settled "
                      "status."),
            _evidence("EVD-0055",
                      "The Third Circuit affirmed an injunction against New Jersey's enforcement "
                      "of gambling laws against CFTC-licensed sports contracts, holding that "
                      "federal preemption likely applies.",
                      "SRC-0227", _KALSHI, "VEN-KALSHI-EVENT", "NEUTRAL",
                      "Single circuit, sports-related contracts, and the cited copy is a reprint "
                      "host rather than the court's own publication.",
                      "The legal position is genuinely two-sided: preemption has been upheld while "
                      "state injunctions are active elsewhere, so neither 'open' nor 'closed' is "
                      "an evidence-backed characterization."),
            _evidence("EVD-0056",
                      "Polymarket's international fee schedule is category-specific and charged "
                      "only to takers: fee = C x rate x p x (1-p) with category rates from 0 "
                      "(geopolitics) to 0.07 (crypto) and maker rebate programs up to 25%; makers "
                      "are never charged.",
                      "SRC-0228", _POLY, "VEN-POLYMARKET-EVENT", "WEAKENS",
                      "Per-market configuration is authoritative and no dated fee-version archive "
                      "is published; rebates depend on program participation.",
                      "Any event-market cost model must join the market's own fee configuration "
                      "rather than assume a platform-wide rate."),
            _evidence("EVD-0057",
                      "Polymarket's international service blocks United States persons and "
                      "prohibits circumvention, while the separately documented Polymarket US is a "
                      "CFTC-regulated DCM/DCO with a different product set and authenticated, "
                      "participant-scoped reporting whose position/ledger history documents a "
                      "floor of 2026-05-01; no market-wide historical L2 archive is published for "
                      "either product.",
                      "SRC-0229", _POLY, "VEN-POLYMARKET-EVENT", "WEAKENS",
                      "State-by-state eligibility for the US product is not published in the "
                      "cited material; retention beyond the documented floor is unspecified.",
                      "The event-market branch is only usable through the US product for a US "
                      "operator, with a materially shorter and participant-scoped data history."),
            _evidence("EVD-0058",
                      "The CFTC's 2022 settlement required Blockratize/Polymarket.com to pay "
                      "$1.4m and wind down noncompliant event contracts.",
                      "SRC-0231", _POLY, "VEN-POLYMARKET-EVENT", "NEUTRAL",
                      "Concerns the prior international operator; does not certify current US "
                      "product access.",
                      "Historical event-market datasets must be labelled by entity and era before "
                      "any cross-era comparison."),
            _evidence("EVD-0059",
                      "A third-party vendor publishes general data-plan prices of $650, $1,200, "
                      "$2,200 and $6,000 per month with venue coverage including Hyperliquid "
                      "(from 2024-10-29) and Deribit (from 2019-03-30), and documents that "
                      "Deribit's public liquidation feed was removed after 2023-10-03.",
                      "SRC-0234", _HL + "|" + "TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX",
                      "VEN-HYPERLIQUID-BTCPERP", "NEUTRAL",
                      "Vendor pricing is not a venue quote and plans are not venue-only; symbol "
                      "and date inclusion is not proven; the liquidation cutoff splits any study "
                      "period.",
                      "Gives an order-of-magnitude price for replay data while leaving the "
                      "venue-specific price UNKNOWN, and shows liquidation studies must segment "
                      "before and after 2023-10-03."),
        ],
        "modified_claims": [],
        "proposed_candidate_updates": [],
        "proposed_issue_updates": [
            {"issue_id": "UNK-0010", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Fee schedule verified at the base tier (SRC-0213) and an "
                                "official event-level archive confirmed (SRC-0214), with cadence, "
                                "cost and completeness caveats. Outstanding: market-wide "
                                "liquidation observability (user-scoped only, SRC-0217), a fixed "
                                "archive cost, and the fee page's missing effective date."},
            {"issue_id": "UNK-0013", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Fee table with premium caps verified (SRC-0219) and official "
                                "trade/funding backfill documented (SRC-0220); no bulk historical "
                                "option-book archive exists officially, and a vendor archive is "
                                "available at an unquoted venue-specific price (SRC-0234). "
                                "Jurisdiction: US prohibited (SRC-0221); other operators need an "
                                "entity/client review."},
            {"issue_id": "UNK-0014", "from_status": "OPEN", "to_status": "IN_PROGRESS",
             "resolution_note": "Substantially narrowed: restricted-country lists (SRC-0224), "
                                "active adverse state orders in Washington and Nevada "
                                "(SRC-0225, SRC-0226), a contrary preemption holding in the Third "
                                "Circuit (SRC-0227), the international/US product split for "
                                "Polymarket (SRC-0229, SRC-0230) and the 2022 CFTC settlement "
                                "(SRC-0231). Outstanding: a complete US state-by-state matrix and "
                                "the operator's own jurisdiction."},
        ],
        "proposed_venue_updates": [
            {"venue_id": "VEN-HYPERLIQUID-BTCPERP",
             "fields": {
                 "maker_fee_value": 0.015, "maker_fee_unit": "PERCENT",
                 "maker_fee_source_id": "SRC-0213",
                 "taker_fee_value": 0.045, "taker_fee_unit": "PERCENT",
                 "taker_fee_source_id": "SRC-0213",
                 "fee_notes": "Perp base tier (< $5m 14-day volume): taker 0.045%, maker 0.015%; "
                              "tiers fall to 0.024%/0% above $7b; staking (5%-40%) and referral "
                              "modifiers apply, and maker-volume rebates of 0.001%-0.003% exist "
                              "above 0.5%-3.0% maker share (SRC-0213). The page publishes no "
                              "effective date, so the snapshot date must be recorded with the "
                              "figure.",
                 "historical_feed": "Official requester-pays S3 archive: hourly L2 book files, "
                                    "asset contexts, and per-block node fills/trades; updates "
                                    "approximately monthly with no timeliness or completeness "
                                    "guarantee, and no candle or spot dataset.",
                 "historical_feed_source_id": "SRC-0214",
                 "timestamp_semantics": "Block time on the feed; documented snapshot rule of at "
                                        "least 0.5 seconds between book pushes; order count per "
                                        "level rather than order identifiers.",
                 "timestamp_semantics_source_id": "SRC-0216",
                 "jurisdiction": "Interface terms exclude Restricted Persons resident, located, "
                                 "incorporated or registered in the United States or Ontario, "
                                 "Canada; direct protocol interaction is not resolved by the "
                                 "terms.",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0213", "SRC-0214", "SRC-0216", "SRC-0218"],
             "reason": "Verified base-tier fees, an official historical archive with caveats, "
                       "feed semantics, and the interface access restriction."},
            {"venue_id": "VEN-DERIBIT-BTCOPT",
             "fields": {
                 "maker_fee_value": 3, "maker_fee_unit": "BPS", "maker_fee_source_id": "SRC-0219",
                 "taker_fee_value": 3, "taker_fee_unit": "BPS", "taker_fee_source_id": "SRC-0219",
                 "fee_notes": "Options standard tier 3/3 bps with per-tier reductions and fees "
                              "capped as a percentage of premium; perps/futures 1.5/3.5 bps at "
                              "the standard tier; fixed 1% liquidation fee on BTC/ETH/USDC "
                              "futures and perps; delivery fee 0.015% capped at 12.5% of option "
                              "value (SRC-0219, updated 2026-09-14, rates effective 2026-08-01).",
                 "historical_feed": "Official public backfill for trades, funding, mark price and "
                                    "settlements; no official bulk option-book archive. A vendor "
                                    "archive exists with coverage from 2019-03-30 at a "
                                    "venue-unquoted plan price.",
                 "historical_feed_source_id": "SRC-0220",
                 "timestamp_semantics": "Channel-dependent: raw delivers every update in normal "
                                        "operation but may coalesce under load; 100ms and agg2 "
                                        "are aggregated; change_id/prev_change_id allow continuity "
                                        "checking; subscriptions do not backfill.",
                 "timestamp_semantics_source_id": "SRC-0220",
                 "jurisdiction": "Restricted-jurisdiction page (updated 2026-03-19) prohibits the "
                                 "United States and other named jurisdictions; EU/EEA countries "
                                 "are not listed generally, and client classification alters "
                                 "product access in some countries.",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0219", "SRC-0220", "SRC-0221", "SRC-0234"],
             "reason": "Verified fee table, replay fidelity constraints, the access restriction "
                       "and the vendor archive path."},
            {"venue_id": "VEN-KALSHI-EVENT",
             "fields": {
                 "maker_fee_value": 0, "maker_fee_unit": "PERCENT",
                 "maker_fee_source_id": "SRC-0222",
                 "fee_notes": "Taker fee = round_up(M x 0.07 x C x P x (1-P)) with a "
                              "product-specific multiplier M; maker multiplier defaults to zero "
                              "unless a product table indicates otherwise, so the ordinary maker "
                              "fee is recorded as verified zero while product-specific series can "
                              "differ. Settlement and membership fees are zero; a separate "
                              "perpetual-futures schedule runs 12.0 to 2.6 bps by tier "
                              "(SRC-0222, effective 2026-07-07).",
                 "historical_feed": "Official historical trade and candlestick endpoints with "
                                    "per-data-type live/history cutoffs and cursor pagination; no "
                                    "official full-depth order-book archive is documented.",
                 "historical_feed_source_id": "SRC-0223",
                 "API_protocol": "REST v2 plus WebSocket and FIX, token-bucket rate limits per "
                                 "account tier.",
                 "API_protocol_source_id": "SRC-0223",
                 "jurisdiction": "Extensive non-US restricted-country list in the member "
                                 "agreement; active state-level orders in Washington "
                                 "(2026-08-13) and Nevada (2026-07-24) for sports, election, "
                                 "entertainment and related categories, against a contrary Third "
                                 "Circuit preemption holding (2026-04-06).",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0222", "SRC-0223", "SRC-0224", "SRC-0225", "SRC-0226",
                            "SRC-0227"],
             "reason": "Fee formula shape, data endpoints, and a two-sided legal picture."},
            {"venue_id": "VEN-POLYMARKET-EVENT",
             "fields": {
                 "fee_notes": "International schedule is taker-only and category-specific: "
                              "fee = C x rate x p x (1-p), category rates 0 to 0.07 with maker "
                              "rebate programs up to 25%; makers are never charged; the market's "
                              "own configuration is authoritative (SRC-0228). No venue-wide fee "
                              "value is recorded because no single value is correct.",
                 "historical_feed": "International: public price-history and trade endpoints "
                                    "within published rate limits; no market-wide historical L2 "
                                    "archive. US product: authenticated participant-scoped reports "
                                    "with a documented position/ledger floor of 2026-05-01.",
                 "historical_feed_source_id": "SRC-0232",
                 "API_protocol": "Gamma/Data public APIs plus an authenticated CLOB; IP-based "
                                 "limits and a per-signer order limiter.",
                 "API_protocol_source_id": "SRC-0232",
                 "jurisdiction": "The international service blocks United States persons and "
                                 "prohibits circumvention; US persons must use the separately "
                                 "documented CFTC-regulated Polymarket US product, whose "
                                 "state-by-state eligibility is not published in the cited "
                                 "material.",
                 "status": "PARTIAL",
             },
             "source_ids": ["SRC-0228", "SRC-0229", "SRC-0230", "SRC-0231", "SRC-0232",
                            "SRC-0233"],
             "reason": "Category-specific fee model, data surface, and the international/US "
                       "product split with its legal history."},
        ],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [
            {"issue_id": "UNK-0034",
             "claim_needed": "The operator's jurisdiction and client classification.",
             "known_evidence": "Venue terms and regulations now specify explicit exclusions: "
                               "Hyperliquid excludes US and Ontario persons; Deribit prohibits "
                               "the US; Kalshi restricts many countries and faces active "
                               "Washington and Nevada orders; international Polymarket blocks US "
                               "persons while Polymarket US is a separate product.",
             "specific_evidence_needed": "Three facts stated by the operator: (1) legal domicile/"
                                         "jurisdiction of the operating person or entity; (2) "
                                         "entity/person classification, including professional "
                                         "versus non-professional status where a venue "
                                         "distinguishes; (3) intended account/entity type per "
                                         "venue if materially relevant to eligibility.",
             "decision_prevented": "Access legality for four venue families, and therefore KG3 "
                                   "and KG5 for their candidates: no fill or cost model matters "
                                   "for a venue the operator may not use.",
             "severity": "BLOCKING", "resolution_method": "HUMAN_INPUT",
             "resolution_stage": "M1_BLOCKING", "tier": 1, "branch_impact": "GLOBAL",
             "kill_potential": "HIGH", "estimated_effort": "SMALL", "can_M2_measure": "NO",
             "requires_vendor_quote": "NO",
             "affected_candidate_ids": _HL + "|" + _KALSHI + "|" + _POLY + "|" +
                                       "TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX|" +
                                       "TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG|" +
                                       "TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG",
             "migration_reason": "Not resolvable by research: it is a fact about the operator, "
                                 "not about the market. Classified HUMAN_INPUT so it is surfaced "
                                 "in the human queue and never dispatched to a resolver."},
            {"issue_id": "UNK-0035",
             "claim_needed": "Version control for venue fee schedules that publish no effective "
                             "date or version archive.",
             "known_evidence": "Hyperliquid's fee page and Polymarket's fee documentation carry no "
                               "effective date; Deribit's page gives one update date rather than "
                               "per-row versions; Kalshi's schedule states an effective date but "
                               "its production URL was rate-limited at access time.",
             "specific_evidence_needed": "A dated, hashed snapshot of each fee page taken by the "
                                         "project, re-taken on a fixed schedule, with the figure "
                                         "used by any cost model tied to the snapshot it came "
                                         "from.",
             "decision_prevented": "After-cost replication validity: a cost model built on an "
                                   "undated dynamic page cannot be shown to describe the period "
                                   "it is tested on.",
             "severity": "IMPORTANT", "resolution_method": "PUBLIC_RESEARCH",
             "resolution_stage": "M1_BLOCKING", "tier": 1, "branch_impact": "MEDIUM",
             "kill_potential": "LOW", "estimated_effort": "SMALL", "can_M2_measure": "NO",
             "requires_vendor_quote": "NO",
             "affected_candidate_ids": _HL + "|" + _POLY,
             "migration_reason": "Surfaced by primary research: several venues publish fees "
                                 "without dates, so the project must create the version record "
                                 "the venue does not."},
        ],
        "decision": "SUPPORTS",
        "reason": "Twenty-two primary sources close the crypto and event-market fee/data gaps: "
                  "Hyperliquid base-tier fees and an official historical archive, Deribit's fee "
                  "table with premium caps plus documented trade backfill, Kalshi's fee formula "
                  "and historical endpoints, Polymarket's taker-only category fee model and the "
                  "international/US product split, and the regulatory record including active "
                  "adverse state orders and a contrary preemption holding.",
        "verification_notes": "Contrary evidence was searched and found, which is why it is "
                              "recorded rather than smoothed: the Third Circuit preemption "
                              "holding (EVD-0055) contradicts the state-injunction picture, and "
                              "the two positions are preserved side by side instead of being "
                              "averaged. Vendor pricing (SRC-0234) is recorded as a vendor fact "
                              "with its coverage limits, never as a venue fee or a venue dataset "
                              "price. Hyperliquid's fee page has no effective date, so the figure "
                              "is marked as undated and a new blocker (UNK-0035) records that the "
                              "project must snapshot it. No gate change is proposed: fees and "
                              "data existence are now known, but no fill model, markout or "
                              "break-even follows, and the operator's jurisdiction (UNK-0034) is "
                              "unknown.",
        "status": "PROPOSED",
        "created_at": created_at,
    }