"""Venue/instrument facts (VEN-*).

One row per instrument x venue pair actually referenced by the M1-A tuple ledger or
fact ledger. Verified exchange facts are cited; everything else is UNKNOWN. Zero is
never used as a substitute for a missing numeric field (ASM-0005).

Fee units are kept native (BPS / PERCENT / USD_PER_SHARE) because cross-venue
conversion is only legitimate once each venue's own unit is known; a $/share fee
cannot be expressed in bps without a price (ASM-0011).
"""

from .constants import UNKNOWN

COLUMNS = [
    "venue_id", "instrument", "asset_class", "venue",
    "market_structure", "structure_source_id",
    "matching_algorithm", "matching_algorithm_source_id", "matching_algorithm_status",
    "tick_size", "tick_size_unit", "tick_size_source_id",
    "lot_size", "lot_size_unit", "lot_size_source_id",
    "maker_fee_value", "maker_fee_unit", "maker_fee_source_id",
    "taker_fee_value", "taker_fee_unit", "taker_fee_source_id",
    "rebate_value", "rebate_unit", "rebate_source_id",
    "clearing_fee_value", "clearing_fee_unit", "clearing_fee_source_id",
    "other_exchange_fee_value", "other_exchange_fee_unit", "other_exchange_fee_source_id",
    "perp_open_fee_value", "perp_open_fee_unit", "perp_open_fee_source_id",
    "perp_close_fee_value", "perp_close_fee_unit", "perp_close_fee_source_id",
    "funding_value", "funding_unit", "funding_source_id",
    "margin_requirement", "margin_requirement_unit", "margin_requirement_source_id",
    "trading_hours", "trading_hours_source_id",
    "live_feed", "live_feed_source_id",
    "historical_feed", "historical_feed_source_id",
    "L1_available", "L2_available", "L3_MBO_available", "depth_source_id",
    "live_feed_min_interval_us", "live_feed_min_interval_source_id",
    "timestamp_semantics", "timestamp_semantics_source_id",
    "API_protocol", "API_protocol_source_id",
    "rate_limits", "rate_limits_source_id",
    "colocation_available", "colocation_source_id",
    "small_prop_access", "jurisdiction",
    "fee_notes", "access_notes",
    "unknown_fields",
    "status",
]


def _row(**kw):
    row = {c: UNKNOWN for c in COLUMNS}
    row.update(kw)
    return row


ROWS = []


def add(**kw):
    ROWS.append(_row(**kw))


# --------------------------------------------------------------- CME futures
_CME_COMMON = dict(
    asset_class="Futures",
    venue="CME Globex",
    market_structure="Electronic central limit order book; full-depth MBO/MBP disseminated "
                     "through CME MDP Premium (MDP 3.0/SBE, dual-feed UDP multicast)",
    structure_source_id="SRC-0107",
    matching_algorithm_source_id="SRC-0112",
    matching_algorithm_status="PRODUCT_SPECIFIC_UNRESOLVED",
    trading_hours="UNKNOWN (CME publishes per-product hours; not locked in the M1-A pass)",
    live_feed="MBO full depth + MBP available via MDP Premium",
    live_feed_source_id="SRC-0107",
    historical_feed="Advertised up to full order book; depth, licensing, delivery format and cost "
                    "not locked",
    historical_feed_source_id="SRC-0123",
    L1_available="TRUE", L2_available="TRUE", L3_MBO_available="TRUE",
    depth_source_id="SRC-0107",
    API_protocol="MDP 3.0 over SBE/UDP multicast (market data); trade/order protocol not locked",
    API_protocol_source_id="SRC-0115",
    colocation_available="UNKNOWN",
    small_prop_access="Economical broker/direct path unverified",
    jurisdiction="UNKNOWN",
    fee_notes="No CME exchange, clearing, NFA or FCM fee value was verified in the M1-A pass; all "
              "cost fields are therefore UNKNOWN rather than assumed.",
    access_notes="Direct CME connectivity exists; economical broker/direct path and measured latency "
                 "remain unverified.",
    status="PARTIAL",
)
add(venue_id="VEN-CME-ES", instrument="ES (E-mini S&P 500 future)", **_CME_COMMON)
add(venue_id="VEN-CME-NQ", instrument="NQ (E-mini Nasdaq-100 future)", **_CME_COMMON)

_TSY = {
    **_CME_COMMON,
    "market_structure": "Electronic central limit order book; fixed-income security definitions "
                        "documented in MDP 3.0; Treasury calendar-spread matching algorithms have "
                        "been changed by CME notice",
    "structure_source_id": "SRC-0124",
    "matching_algorithm_status": "CHANGED_BY_NOTICE_RULE_UNRESOLVED",
    "access_notes": "FCM/direct-feed arrangement required; instrument family not narrowed to an "
                    "exact contract, so no cost or rule can be looked up.",
    "status": "UNKNOWN",
}
add(venue_id="VEN-CME-TSY",
    instrument="Treasury future (exact contract UNSPECIFIED: contract family only)", **_TSY)

_WTI = {
    **_CME_COMMON,
    "access_notes": "Instrument family not narrowed to an exact contract month.",
    "status": "UNKNOWN",
}
add(venue_id="VEN-CME-WTI",
    instrument="WTI crude oil future (contract month UNSPECIFIED)", **_WTI)

# ------------------------------------------------------------- Nasdaq equities
add(venue_id="VEN-NASDAQ-CONT",
    instrument="Large-tick U.S. listed stock (symbol UNSPECIFIED)",
    asset_class="Equities", venue="Nasdaq (continuous book)",
    market_structure="Displayed-depth electronic limit order book; fragmented national market where "
                     "one venue book is not the whole market",
    structure_source_id="SRC-0108",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    trading_hours="UNKNOWN (U.S. equity session hours not locked in the M1-A pass)",
    live_feed="Nasdaq TotalView-ITCH displayed depth/order information",
    live_feed_source_id="SRC-0108",
    historical_feed="U.S. Equity Tick History is consolidated Level-1 only; order-level history "
                    "requires separate ITCH/TotalView-depth procurement",
    historical_feed_source_id="SRC-0109",
    L1_available="TRUE",
    L2_available="TRUE (displayed depth via TotalView)",
    L3_MBO_available="UNKNOWN (order-level live feed exists; historical package unresolved)",
    depth_source_id="SRC-0108",
    API_protocol="UNKNOWN (feed-level protocol not locked for this project's access path)",
    colocation_available="UNKNOWN",
    small_prop_access="Main-book small-prop fee tier UNKNOWN",
    jurisdiction="US",
    fee_notes="Nasdaq main-book fee tier, routing economics and CAT/broker/clearing costs were not "
              "locked; all cost fields are UNKNOWN.",
    access_notes="Fragmentation means a single-venue book is not the national market.",
    status="PARTIAL")
add(venue_id="VEN-NASDAQ-AUCTION",
    instrument="Nasdaq-listed stock (closing auction)",
    asset_class="Equities", venue="Nasdaq (auction)",
    market_structure="Auction with public NOII dissemination of indicative price and imbalance; IPO "
                     "opening additionally includes a display-only period of at least ten minutes",
    structure_source_id="SRC-0108",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="AUCTION_SPECIFIC_UNRESOLVED",
    live_feed="NOII auction imbalance information available",
    live_feed_source_id="SRC-0108",
    historical_feed="Historical NOII depth source and cost not locked",
    historical_feed_source_id=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN",
    L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    colocation_available="UNKNOWN",
    small_prop_access="UNKNOWN",
    jurisdiction="US",
    fee_notes="Cross/auction-specific fees were not verified for this tuple.",
    access_notes="Order-type replication point-in-time is unverified.",
    status="UNKNOWN")

# ------------------------------------------------------------- Cboe equities
add(venue_id="VEN-CBOEBZX-EQ",
    instrument="U.S. listed stock >= $1 (symbol UNSPECIFIED)",
    asset_class="Equities", venue="Cboe BZX",
    market_structure="U.S. equity central limit order book; Cboe operates BZX, BYX, EDGA and EDGX "
                     "as separate venues",
    structure_source_id="SRC-0125",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed="UNKNOWN (proprietary depth feed availability for this project not locked)",
    historical_feed="UNKNOWN (order-level history source not locked)",
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, rate_limits=UNKNOWN, colocation_available=UNKNOWN,
    small_prop_access="Broker/membership routing determines realized fee codes",
    jurisdiction="US",
    taker_fee_value=0.0030, taker_fee_unit="USD_PER_SHARE", taker_fee_source_id="SRC-0114",
    rebate_value=0.0016, rebate_unit="USD_PER_SHARE", rebate_source_id="SRC-0114",
    fee_notes="Standard displayed-add rebate $0.0016/share and remove fee $0.0030/share for "
              "securities >= $1, effective 2026-09-01. Volume tiers, special fee codes, routing and "
              "CAT/broker/clearing are additional and unverified; maker_fee_value stays UNKNOWN "
              "because the standard displayed-add rate is a rebate, recorded in its own column.",
    access_notes="Realized economics depend on broker/membership routing.",
    status="PARTIAL")

# --------------------------------------------------------------- US options
add(venue_id="VEN-CBOE-OPT",
    instrument="U.S. listed option (underlying/expiry UNSPECIFIED)",
    asset_class="Listed options", venue="Cboe options venues",
    market_structure="Multiple options venues with complex order priority and class-specific "
                     "mechanics; a located schedule is effective 2026-09-01",
    structure_source_id="SRC-0116",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="CLASS_SPECIFIC_UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available=UNKNOWN, small_prop_access=UNKNOWN,
    jurisdiction="US",
    fee_notes="Options fee schedule exists (effective 2026-09-01) but class/order-type economics were "
              "not decomposed, so no fee value is recorded.",
    access_notes="OPRA versus proprietary depth history not locked.",
    status="UNKNOWN")

# ---------------------------------------------------------- crypto spot/perps
add(venue_id="VEN-COINBASE-BTCUSD",
    instrument="BTC-USD spot",
    asset_class="Crypto spot", venue="Coinbase Exchange",
    market_structure="Centralized maker-taker limit order book",
    structure_source_id="SRC-0105",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN",
    small_prop_access="U.S. access broadly practical; account/program eligibility determines realized "
                      "fees",
    jurisdiction="US (broadly practical per the M1-A pass)",
    maker_fee_value=40, maker_fee_unit="BPS", maker_fee_source_id="SRC-0105",
    taker_fee_value=60, taker_fee_unit="BPS", taker_fee_source_id="SRC-0105",
    fee_notes="0-10k USD 30-day-volume tier: 60 bps taker / 40 bps maker; 400m+ tier is 4/0 bps "
              "outside the liquidity program. Exchange fee only.",
    access_notes="Account/program eligibility can change realized economics.",
    status="PARTIAL")
add(venue_id="VEN-KRAKEN-BTCUSD",
    instrument="BTC/USD spot",
    asset_class="Crypto spot", venue="Kraken",
    market_structure="Centralized maker-taker market",
    structure_source_id="SRC-0106",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN",
    small_prop_access="Product availability varies by geography",
    jurisdiction="UNKNOWN (product availability varies by geography)",
    maker_fee_value=40, maker_fee_unit="BPS", maker_fee_source_id="SRC-0106",
    taker_fee_value=80, taker_fee_unit="BPS", taker_fee_source_id="SRC-0106",
    fee_notes="Tier 1 spot 0.40% maker / 0.80% taker; reductions require high volume/assets. "
              "Platform fee only.",
    access_notes="Kraken documents geography-dependent product availability.",
    status="PARTIAL")
add(venue_id="VEN-KRAKEN-BTCPERP",
    instrument="Perpetual futures (referenced product)",
    asset_class="Crypto perpetuals", venue="Kraken",
    market_structure="UNKNOWN (perp book structure not locked in the M1-A pass)",
    structure_source_id=UNKNOWN,
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN",
    small_prop_access=UNKNOWN,
    jurisdiction="UNKNOWN (availability geography-dependent)",
    perp_open_fee_value=0.25, perp_open_fee_unit="PERCENT", perp_open_fee_source_id="SRC-0106",
    perp_close_fee_value=0.25, perp_close_fee_unit="PERCENT", perp_close_fee_source_id="SRC-0106",
    fee_notes="Platform states 0.25% of notional to open and 0.25% of closing notional for the "
              "referenced perp product; maker/taker distinction not stated, so maker/taker fee "
              "columns stay UNKNOWN. No Kraken-perp tuple exists in the M1-A tuple ledger.",
    access_notes="Geography-dependent; no candidate depends on this venue row yet.",
    status="PARTIAL")
add(venue_id="VEN-HYPERLIQUID-BTCPERP",
    instrument="BTC perpetual",
    asset_class="Crypto perpetuals", venue="Hyperliquid",
    market_structure="Public WebSocket exposes BBO, trades and an L2 book (5 or 20 levels); the "
                     "documented book feed is block-cadenced snapshots with price, aggregate size and "
                     "order count rather than exchange-style individual-order queue identifiers",
    structure_source_id="SRC-0111",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed="Public l2Book/BBO/trades; snapshot cadence documented at >= 0.5 s between pushes",
    live_feed_source_id="SRC-0111",
    historical_feed="Info endpoints paginate some time-range responses; event-by-event historical "
                    "L2/MBO source not verified",
    historical_feed_source_id="SRC-0118",
    L1_available="TRUE (BBO)", L2_available="TRUE (aggregate levels 5/20)",
    L3_MBO_available="FALSE (aggregate levels, no per-order queue identifiers)",
    depth_source_id="SRC-0111",
    live_feed_min_interval_us=500000,
    live_feed_min_interval_source_id="SRC-0111",
    API_protocol="Public WebSocket + info endpoints",
    API_protocol_source_id="SRC-0111",
    colocation_available="UNKNOWN",
    small_prop_access="UNKNOWN",
    jurisdiction="UNKNOWN (legal/account/access assessment not completed)",
    fee_notes="Trading-fee schedule was not verified in the M1-A pass; no fee value is recorded.",
    access_notes="Public API is usable; legal/account status unresolved.",
    status="PARTIAL")

# ------------------------------------------------------------------- Eurex
add(venue_id="VEN-EUREX-FESX",
    instrument="FESX/DAX equity-index future (contract UNSPECIFIED)",
    asset_class="Futures", venue="Eurex T7",
    market_structure="T7 14.1 provides EOBI order-book interface, EMDI/MDI market-data interfaces and "
                     "ETI trading interface",
    structure_source_id="SRC-0110",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="PRODUCT_ALLOCATION_UNRESOLVED",
    live_feed="EOBI order-book messages plus instrument reference data",
    live_feed_source_id="SRC-0110",
    historical_feed="Historical EOBI/order-level acquisition and cost UNKNOWN",
    historical_feed_source_id=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN",
    L3_MBO_available="UNKNOWN (EOBI order-book interface exists; historical package unresolved)",
    depth_source_id="SRC-0110",
    API_protocol="EOBI/EMDI/ETI (T7 14.1)",
    API_protocol_source_id="SRC-0110",
    colocation_available="UNKNOWN",
    small_prop_access="Participant/broker route and economic feasibility UNKNOWN",
    jurisdiction="UNKNOWN",
    fee_notes="Eurex execution fees were not verified; no fee value is recorded.",
    access_notes="Fees, matching rule and broker/participant access path unresolved.",
    status="UNKNOWN")

# ------------------------------------------------------- crypto options venue
add(venue_id="VEN-DERIBIT-BTCOPT",
    instrument="BTC option (strike/expiry UNSPECIFIED)",
    asset_class="Crypto options", venue="Deribit",
    market_structure="UNKNOWN (current primary specifications not locked)",
    structure_source_id=UNKNOWN,
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN", small_prop_access=UNKNOWN,
    jurisdiction="UNKNOWN (current jurisdictional/access state not locked)",
    fee_notes="Fees not verified; no fee value is recorded.",
    access_notes="Gate 2 not passed.",
    status="UNKNOWN")

# ------------------------------------------------------------ event markets
add(venue_id="VEN-KALSHI-EVENT",
    instrument="Event contract (contract UNSPECIFIED)",
    asset_class="Event contracts", venue="Kalshi",
    market_structure="UNKNOWN (API/fee schema not locked)",
    structure_source_id=UNKNOWN,
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="CONTRACT_SPECIFIC_UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN", small_prop_access=UNKNOWN,
    jurisdiction="State-dependent; Washington obtained a 2026 court order affecting Kalshi "
                 "operations in the state",
    fee_notes="Fees not verified; no fee value is recorded.",
    access_notes="Nationwide access cannot be assumed; per-jurisdiction verification required.",
    status="UNKNOWN")
add(venue_id="VEN-POLYMARKET-EVENT",
    instrument="Event contract (contract UNSPECIFIED)",
    asset_class="Event contracts", venue="Polymarket",
    market_structure="UNKNOWN (current primary schemas not locked)",
    structure_source_id=UNKNOWN,
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN", small_prop_access=UNKNOWN,
    jurisdiction="UNKNOWN (current U.S. access requires fresh primary verification)",
    fee_notes="Fees not verified; no fee value is recorded.",
    access_notes="Regulatory and venue-data lock required before any experiment.",
    status="UNKNOWN")

# ------------------------------------------------------------ FX + cross-venue
add(venue_id="VEN-USSTOCK-MULTI",
    instrument="U.S. listed stock (symbol UNSPECIFIED), national market",
    asset_class="Equities", venue="Multi-venue U.S. equities (Nasdaq/NYSE/IEX/Cboe)",
    market_structure="Fragmented national market with several protected and non-protected venues",
    structure_source_id="SRC-0108",
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="VENUE_SPECIFIC_UNRESOLVED",
    live_feed="Aggregated multi-venue observation required; no single-feed package locked",
    live_feed_source_id=UNKNOWN,
    historical_feed="No consolidated order-level historical package locked",
    historical_feed_source_id=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN",
    small_prop_access="NYSE/IEX exact 2026 fees and direct-feed history were not covered in the "
                      "M1-A pass",
    jurisdiction="US",
    fee_notes="No venue-specific fee values were verified for a cross-venue tuple.",
    access_notes="Routing and stale-quote survival are part of the hypothesis itself.",
    status="UNKNOWN")
add(venue_id="VEN-FX-ECN-UNSPEC",
    instrument="Spot FX pair (pair and ECN UNSPECIFIED)",
    asset_class="FX", venue="Unspecified institutional ECN",
    market_structure="UNKNOWN (institutional venues differ: CLOB / RFQ / last-look behaviour)",
    structure_source_id=UNKNOWN,
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN",
    small_prop_access="Institutional onboarding and capital requirements may dominate feasibility",
    jurisdiction="UNKNOWN",
    fee_notes="No fee values verified.",
    access_notes="'FX' is not a candidate: an exact ECN, participant status and protocol are required "
                 "before any cost or rule can be looked up.",
    status="UNKNOWN")
add(venue_id="VEN-FX-RETAILBROKER-UNSPEC",
    instrument="Spot FX pair (pair and broker UNSPECIFIED)",
    asset_class="FX", venue="Unspecified retail broker",
    market_structure="Broker-specific price/execution, potentially last-look; not safely treated as "
                     "institutional price discovery",
    structure_source_id=UNKNOWN,
    matching_algorithm_source_id=UNKNOWN, matching_algorithm_status="BROKER_SPECIFIC_UNRESOLVED",
    live_feed=UNKNOWN, historical_feed=UNKNOWN,
    L1_available="UNKNOWN", L2_available="UNKNOWN", L3_MBO_available="UNKNOWN",
    depth_source_id=UNKNOWN,
    API_protocol=UNKNOWN, colocation_available="UNKNOWN",
    small_prop_access=UNKNOWN,
    jurisdiction="UNKNOWN",
    fee_notes="No fee values verified.",
    access_notes="The broker's execution policy is part of the hypothesis and is currently undefined.",
    status="UNKNOWN")

BY_ID = {row["venue_id"]: row for row in ROWS}