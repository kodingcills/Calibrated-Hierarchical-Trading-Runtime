# Branch C source ledger

Retrieved 2026-09-29.

### S1 — Hyperliquid funding
- URL: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding.md
- Official docs. Funding is paid hourly; formula is an 8-hour rate paid one eighth hourly; premium sampled every 5 seconds and averaged over the hour; payment uses position size × oracle price × funding rate; cap 4%/hour.
- Proves funding semantics, not complete historical availability or executable hedge costs.

### S2 — Hyperliquid fundingHistory and metadata
- URL: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals.md
- Official API docs. `meta` includes BTC universe metadata; `fundingHistory` accepts coin/startTime/endTime (milliseconds inclusive) and returns coin, fundingRate, premium, time. Retrieved endpoint returned BTC and one row for the smoke window.
- Proves endpoint shape and BTC existence, not guaranteed retention/completeness.

### S3 — Hyperliquid archive
- URL: https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data.md
- Official docs. Archive uploaded approximately monthly; no guarantee of timely updates and data may be missing. S3 provides L2 book snapshots under `market_data` and asset contexts under `asset_ctxs`; no candles or spot asset data; requester pays transfer costs. Fills and funding events are in the node-data buckets.
- Proves archive delay/missing-data warning and available object families; does not prove any selected date/object exists.

### S4 — Hyperliquid node schemas
- URL: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/nodes/l1-data-schemas.md
- Official docs. Trade records include coin/time/px/sz; misc events include funding with coin/usdc/szi/fundingRate/nSamples; raw book diffs and ledger updates are separate streams.
- Proves event fields and that funding can be represented in node archive, not full historical continuity.

### S5 — Hyperliquid perpetual metadata/asset contexts
- URL: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals.md
- Official API docs. `metaAndAssetCtxs` includes markPx, midPx, oraclePx, funding, premium, impact prices; BTC metadata record exists in returned live response (`szDecimals`: 5, `maxLeverage`: 40, `marginTableId`: 56).
- Proves current instrument and field availability, not historical archive completeness.

### S6 — Hyperliquid order book/mids/candles
- URL: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint.md
- Official API docs. `l2Book` returns timestamped book snapshots, up to 20 levels per side; `allMids` falls back to last trade if the book is empty; candles expose timestamp fields but only most recent 5000 are available.
- Proves live/public semantics and the fallback hazard. It does not supply historical mids through the API.

### S10 — Corrected completeness-check execution
- URL: local executable `.research/resolution/BRANCH_C/completeness_check.py`; output `.research/resolution/BRANCH_C/completeness_check_output.json`
- Retrieved/executed 2026-09-29T17:58:25.529956+00:00 UTC. The bucketed test maps event timestamps to UTC-hour buckets (the returned `...00109` timestamp belongs to the `...0000000` hour), then rejects missing or duplicate expected buckets. One of two expected buckets was missing; Binance returned HTTP 451.

### S7 — Hyperliquid oracle/index/contract specs
- URLs: https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/oracle.md ; https://hyperliquid.gitbook.io/hyperliquid-docs/trading/robust-price-indices.md ; https://hyperliquid.gitbook.io/hyperliquid-docs/trading/contract-specifications.md
- Official docs. BTC oracle is validator-weighted external spot median; oracle updates approximately every 3 seconds; mark price combines oracle/Hyperliquid book-trade/CEX perp inputs; BTC is a linear 1-unit underlying contract with $20,000 funding impact notional.
- Proves reference semantics and no equivalence between HL mid, oracle, and mark; does not resolve historical availability.

### S8 — Hyperliquid fees
- URL: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees.md
- Official fee table. Base tier perps taker 0.045% and maker 0.015%; tiers depend on rolling 14-day volume. No account-specific fee tier is assumed.
- Proves one documented HL cost floor only; Binance costs are unresolved.

### S9 — Binance public endpoint attempt
- URL: https://fapi.binance.com/fapi/v1/exchangeInfo (and `/fapi/v1/fundingRate`, `/fapi/v1/markPriceKlines`)
- Retrieved 2026-09-29 by `.research/resolution/BRANCH_C/completeness_check.py`; public no-key requests were attempted but this environment returned HTTP 451 before instrument/data response.
- This is direct execution evidence of an environment/access blocker, not proof that Binance globally lacks the instrument or public endpoints. Official Binance docs were not machine-readable in this run; therefore Binance historical field/cost claims remain unresolved rather than inferred.
