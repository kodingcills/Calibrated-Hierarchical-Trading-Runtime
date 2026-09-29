# Hyperliquid funding/basis branch report

**Result: `FUNDING_EXTERNAL_ONLY`**

**Decision.** A precise public precursor is defined but not executable from the available evidence. The frozen pair is short Hyperliquid Core `BTC` linear perpetual and long equal-BTC-notional Binance USDⓈ-M `BTCUSDT` perpetual. Hyperliquid's official metadata endpoint confirms `BTC` exists (live response: `szDecimals=5`, `maxLeverage=40`, `marginTableId=56`); the Binance leg is explicitly named, but this run could not obtain a direct public response: the no-key request returned HTTP 451. No purchase, credentials, trade, paper trade, or sibling finding was used.

## Exact claims and evidence

- Hyperliquid funding is peer-to-peer, paid every hour; the formula is an 8-hour formula paid one eighth per hour. Premium is sampled every 5 seconds and averaged over the hour. The payment is position size × oracle price × funding rate. [S1]
- `fundingHistory` is a public POST `/info` request with `coin`, inclusive millisecond `startTime`, and optional inclusive `endTime`; rows expose `coin`, `fundingRate`, `premium`, and millisecond `time`. [S2]
- Hyperliquid's official archive is uploaded approximately monthly, has no guarantee of timely updates, and may be missing data. S3 provides L2 book snapshots (`market_data`) and asset contexts (`asset_ctxs`), but no candles or spot asset data. Requester pays transfer costs. Funding events exist in the node-data `misc_events_by_block` family. [S3, S4]
- Live `l2Book` is timestamped and up to 20 levels per side. `allMids` falls back to last-trade price when the book is empty, so it is not a sufficient historical mid definition without an explicit fallback exclusion. The candle API exposes timestamps but only the most recent 5000 candles. [S6]
- Oracle, mark, and mid are distinct: BTC oracle is a validator-weighted external spot median; mark combines oracle, Hyperliquid book/trade, and CEX-perp inputs. [S7]
- Official Hyperliquid base fee table gives 0.045% taker perps fee per side (0.015% maker at base tier), with fee tier determined by rolling 14-day volume. [S8]

## Completeness test and observed execution

`completeness_check.py` is a no-purchase live endpoint smoke/checker. It freezes a completed UTC-hour window, checks BTC metadata and context shape, requests Hyperliquid `fundingHistory`, and checks exact expected hourly timestamps (one row per expected hour, no duplicates, millisecond epoch). It also attempts Binance exchange info, funding rate, and mark-price klines.

Output: `completeness_check_output.json`, retrieved `2026-09-29T17:58:25.529956+00:00` UTC. Hyperliquid metadata and contexts succeeded; BTC exists and context shape is two-part with 234 asset contexts. The funding response contained one row (`time=1790694000109`, rate `0.0000106749`, premium `-0.0004146009`) against two expected hourly slots; the corrected bucketed strict completeness test therefore failed with missing slot `1790697600000`. The timestamp is millisecond epoch and the response is not a complete hourly panel. Binance requests failed with HTTP 451 before symbol/history responses.

`archive_completeness.py` implements an independent validator for any already-downloaded newline-delimited archive stream: every row must have a timestamp, timestamps must be strictly increasing and unique, and no gap may exceed the declared limit. It intentionally does not download S3 data or bypass requester-pays. The official archive's own missing/timeliness warning means existence and completeness must be checked per date/object; neither may be assumed.

## Cost floor and blockers

The only quantified structural floor is Hyperliquid base-tier taker fee: 0.045% × two HL executions = 0.090% notional for open/close if both are taker (or 0.030% if both base-tier maker, but maker fill is not assumed). This is optimistic and incomplete. Binance trading fee, funding payment, spread, impact, margin/capital, liquidation, borrow/financing, and transfer costs are not imputed because the authoritative Binance response and account-independent cost schedule were not resolved. The HL oracle/mark distinction also means a funding carry calculation must use the documented oracle-price notional, not an invented mark-price substitute.

Binding blockers are: (1) no complete paired Hyperliquid/Binance historical sample was obtained; (2) Hyperliquid API response failed the exact hourly completeness predicate; (3) Binance public endpoint access returned HTTP 451 in this environment, leaving existence/data/fees unverified; (4) Hyperliquid S3 archive is explicitly delayed/may be missing and requester-pays, so no archive completeness claim can be made without checking each object; and (5) all-leg executable costs are not resolved. These blockers prohibit a causal pilot and any net-performance claim.

## Frozen-before-results status

`frozen_spec.md` freezes pair, sample rule, one-hour holding horizon, state, optimistic cost floor, primary descriptive metric, kill rule, and continuation rule before any pilot result. Because prerequisites failed, no pilot was run and no result was inspected. The intended result is not `FUNDING_PRECURSOR_READY`.

## Reproducibility

From repository root:

```bash
python3 .research/resolution/BRANCH_C/completeness_check.py > .research/resolution/BRANCH_C/completeness_check_output.json
python3 .research/resolution/BRANCH_C/archive_completeness.py /path/to/already-downloaded.ndjson --timestamp-key time --max-gap-ms 3600000
```

The first command uses only public Hyperliquid and Binance market-data endpoints and no credentials. The second command performs no network access; it validates a supplied archive file. Source URLs and retrieved-date notes are in `SOURCES.md`.
