# Source ledger — independent verification

All entries were accessed 2026-09-29 unless noted. Official pages/endpoints only; failed retrievals are retained as limitations and not semantic evidence.

- A1 — https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html — CME ES contract specs snapshot; contract unit, tick, hours, quarterly listings, termination.
- A2 — https://www.cmegroup.com/market-data/market-data-api.html — CME API page; real-time WebSocket product-level scope and historical DataMine distinction.
- A3 — https://www.cmegroup.com/company/clearing-fees.html — CME fees snapshot; variation by status/product/volume/venue/type; schedule/finder links. Direct reader attempt returned 403.
- A4 — https://www.cmegroup.com/content/dam/cmegroup/market-data/MDP-3.0/MDP-3.0-Core-Messaging-Reference.pdf — attempted MDP reference; branch retrieval returned 403/Page Not Found; no semantic inference.
- B1 — https://www.nasdaqtrader.com/Trader.aspx?id=OpenClose — official opening/closing cross page; eligibility, NOII window, close order types.
- B2 — https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2026-32 — official 2026-06-23 alert; 15:50/15:55/15:58/16:00 timeline.
- B3 — https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf — TotalView-ITCH 5.0 PDF; sequenced direct feed, timestamps, directory, I/Q fields.
- B4 — https://www.nasdaq.com/products/data/equities/nasdaq-totalview — TotalView product page; real-time NOII and access channels, no replay guarantee.
- B5 — https://data.nasdaq.com/databases/NTV/documentation — NTV landing page; generic Data Link metadata only in this access path.
- C1 — https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding.md — hourly funding, formula, premium, sign, oracle notional, cap.
- C2 — https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals.md — meta/fundingHistory docs and BTC example.
- C3 — https://api.hyperliquid.xyz/info (POST) — direct live checks: meta BTC and fundingHistory row; no credentials.
- C4 — https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data.md — monthly archive cadence, missing-data warning, object families, requester-pays.
- C5 — https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint.md — allMids last-trade fallback when book empty.
- C6 — https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees.md — base perp taker/maker rates and rolling 14-day tiers.
- C7 — https://fapi.binance.com/fapi/v1/exchangeInfo — direct keyless request returned HTTP 451 in this environment on 2026-09-29; environment observation only.
- C8 — .research/resolution/BRANCH_C/completeness_check_output.json — saved branch output; one of two expected hourly HL buckets missing, strict predicate false; local observation, not official source.
