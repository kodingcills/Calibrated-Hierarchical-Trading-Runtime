# PROBE-C-CRYPTO-FREE-PATHS

**Ticket:** PROBE-C-CRYPTO-FREE-PATHS (GOAL-M2-BRIDGE-001, read-only campaign)
**Probe window:** 2026-09-29T21:34Z – 2026-09-29T21:38Z (per-request times given only where a `Date` header was captured)
**Frozen pair under test:** SHORT Hyperliquid Core BTC perp / LONG equal-notional Binance USD-M BTCUSDT perp
**Constraints honoured:** no purchase, no AWS credentials, no account signup, no geographic/entitlement circumvention, no keyed API, no paid tier. Every request below is an anonymous public GET/POST.

---

## 1. Bottom line

**Branch C is NOT EXTERNAL_DATA_BLOCK. A concrete, free, no-auth path exists and was executed end-to-end over a non-trivial window.**

A 3-month window (2026-06-01T00:00Z → 2026-08-31T16:00Z) yielded **276 / 276 synchronized same-UTC-hour observations** carrying every field the frozen pair names, drawn from two independent anonymous sources:

| Leg | Field | Free source | Status |
|---|---|---|---|
| HL | hourly funding rate | `POST api.hyperliquid.xyz/info {"type":"fundingHistory"}` | ✅ obtained |
| HL | hourly premium (mid-vs-oracle gap) | same response | ✅ obtained |
| HL | hourly mid | `POST .../info {"type":"candleSnapshot"}` (`1h`) | ✅ obtained (window-limited) |
| HL | hourly **oracle** price | none free — see §6 | ❌ **only missing object** |
| Binance | settled funding rate + interval | `data.binance.vision` monthly `fundingRate` zip | ✅ obtained |
| Binance | hourly price (close) | `data.binance.vision` monthly `klines` zip | ✅ obtained |
| Binance | hourly mark price | `data.binance.vision` monthly `markPriceKlines` zip | ✅ obtained |

Two distinct, independent residual limitations were **isolated** (neither is a global unavailability):

1. **Binance funding has ~1-month publication lag** through the free archive (monthly files are published "the first monday of the month"; no daily `fundingRate` variant exists in USD-M). At probe time the newest free Binance funding row was 2026-08-31T16:00Z. Closing the most recent ~1 month requires `fapi.binance.com`, which is 451 in this environment — **environment-specific, not global** (§3).
2. **Historical HL oracle price has no free path** — it exists only in the requester-pays S3 bucket (§6). HL *mid* is free but `candleSnapshot` truncates to the most recent ~5000 candles, so free 1h HL price covers roughly the last 208 days.

## 2. Environment observations (explicitly NOT global facts)

| Observation | Where | Handling in this probe |
|---|---|---|
| `data.binance.vision/.../BTCUSDT-1h-2021-01.zip` returned **404** on first probe, then **206** on re-probe ~2 min later | CDN edge | Treated as transient; a single negative probe is not evidence of absence. This is exactly the failure mode the ticket warns about. |
| `fapi.binance.com` → HTTP **451** | this network | Recorded as environment evidence only; no attempt at circumvention. |
| Prior probe's one missing HL hourly funding bucket | prior run | **Not reproduced.** 2208/2208 hourly buckets present across Jun–Aug 2026; 744/744 in Aug 2026. |

## 3. `fapi.binance.com` — keyless status (re-test)

```
2026-09-29 ~21:34Z  GET https://fapi.binance.com/fapi/v1/ping   -> HTTP 451
2026-09-29 ~21:34Z  GET https://fapi.binance.com/fapi/v1/time   -> HTTP 451
body: {"code":0,"msg":"Service unavailable from a restricted location according to 'b. Eligibility'
       in https://www.binance.com/en/terms. ..."}
```
HTTP 451 from this environment. **What this does NOT prove:** that Binance USD-M data is globally unavailable. A different host on the same provider — `data.binance.vision` — served every required Binance file over plain anonymous HTTPS in the same probe window, with no key and no account.

## 4. `data.binance.vision` — public archive (different host, works)

Root `GET https://data.binance.vision/` → **HTTP 200**, `remote_ip 108.138.64.50` (CDN; `fapi` resolved to a different IP `108.138.85.72`).

Bucket listing is **not** available (the `?list-type=2` S3-style query is answered by the web SPA with HTML, not XML), so keys were verified by direct fetch. Negative controls confirm the status codes are meaningful:

| Key | Status |
|---|---|
| `.../fundingRate/BTCUSDT/BTCUSDT-fundingRate-2099-99.zip` (bogus) | 404 |
| `.../nonsense/BTCUSDT/X.zip` (bogus path) | 404 |
| `.../monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2020-01.zip` | 206 |
| `.../monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2019-12.zip` | 404 (funding archive starts 2020-01) |
| `.../monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip` | 206 |
| `.../daily/klines/BTCUSDT/1h/BTCUSDT-1h-2026-09-28.zip` | 206 (daily lags ~1 day) |
| `.../daily/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2025-08-01.zip` | 404 — **no daily fundingRate variant in USD-M** |
| `.../daily/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-09-28.zip` | 404 |
| `.../monthly/{klines,markPriceKlines,fundingRate}/BTCUSDT/...-2026-09.zip` | 404 (current month not yet published) |
| `.../monthly/klines|markPriceKlines|fundingRate/BTCUSDT/...-2026-08.zip` | 206 |

**Field shapes (real samples, verbatim headers + first rows):**

`monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2025-08.zip` → `BTCUSDT-fundingRate-2025-08.csv` (94 rows = 93 settlements + header):
```
calc_time,funding_interval_hours,last_funding_rate
1754006400001,8,-0.00001408
1754035200003,8,0.00001549
```
`monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2025-08.zip` → 745 rows (744 closed hours + header):
```
open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore
1754006400000,115697.30,115877.80,114239.00,115366.90,21495.534,1754009999999,2473716709.55010,376124,9343.768,1075707468.51370,0
```
`monthly/markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2025-08.zip` → 745 rows; identical schema, `volume/quote_volume` are structurally `0` and `count` is 3600 (mark price is a computed index, not a traded series):
```
1754006400000,115702.16776087,115874.90000000,114272,115372.82535004,0,1754009999999,0,3600,0,0,0
```

**Timestamp semantics:** `open_time` = ms UTC, inclusive; `close_time` = `open_time + 3599999`. Funding `calc_time` is ms UTC of the settlement instant. **Binance BTCUSDT funding `funding_interval_hours` = 8 for the whole probe window**, settles at 00:00 / 08:00 / 16:00 UTC — i.e. 3 observations/day, not hourly. The `funding_interval_hours` column is self-describing, so any future cadence change is machine-detectable.

**Archive defect found (and worked around):** `monthly/markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2026-06.zip` is short by exactly 24 rows (696/720) — the whole of 2026-06-29 is absent, while the same month's `klines` file is complete (720/720). The **daily** file `daily/markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2026-06-29.zip` exists (25 rows) and repairs it. *Implication: monthly Binance files must be row-count-validated against the expected hour grid; daily files are the fallback.*

## 5. Hyperliquid `/info` — funding history depth and cadence

`POST https://api.hyperliquid.xyz/info`, no auth, `Content-Type: application/json`. Docs state the pagination rule: *"Responses that take a time range will only return 500 elements… use the last returned timestamp as the next `startTime`."*

**Depth.** `{"type":"fundingHistory","coin":"BTC","startTime":1}` → HTTP 200, 500 rows, oldest `2023-05-12T00:00:00.048Z`, newest `2023-06-25T10:00:00.201Z`. Requesting from time 0 returns HL's own earliest row: **HL funding history begins 2023-05-12 UTC.** Pagination with `startTime` (and optional `endTime`) reaches any later window directly; there is no depth ceiling other than request count.

**Cadence — an important empirical correction.** The first 500-row page spans 1066 hours, not 500: the deltas are ≈28,800,000 ms. **HL funding was 8-hourly, not hourly, in the early period.** Bisecting with bounded windowed requests:

```
T=2023-07-01T00:00Z window 2h -> rows at 00:00:00.189Z and 01:00:00.008Z   (1h apart)
T=2023-10-01T00:00Z window 2h -> rows at 00:00:00.135Z and 01:00:00.257Z   (1h apart)
T=2024-01-01T00:00Z window 2h -> rows at 00:00:00.151Z and 01:00:00.006Z   (1h apart)
startTime=2023-06-25T10:00:00.202Z -> first row 2023-06-25T11:00:00.134Z, then a 3,599,961 ms step
                                    500 rows, 0 steps >2h, 499 steps ≈1h
```
**HL funding is hourly from 2023-06-25T12:00Z onward; before that (2023-05-12T00:00Z → 2023-06-25T11:00Z) it is 8-hourly.** Any window used for the frozen pair must start **on or after 2023-06-25T12:00Z** if a uniform hourly HL grid is required.

**Full-window continuity test — 2026-06-01T00:00Z → 2026-09-01T00:00Z** (`startTime` chaining, 0.5 s spacing, 5 requests):
```
requests 5   rows 2208   distinct timestamps 2208
span 2026-06-01T00:00:00Z -> 2026-08-31T23:00:00Z
expected hours 2208   present 2208   non-1h steps 0   duplicate timestamps 0
```
**Row shape:**
```json
{"coin":"BTC","fundingRate":"0.0000025518","premium":"-0.0004795855","time":1785542400080}
```
**Timestamp semantics:** `time` = ms UTC of the funding settlement, nominally top-of-hour. It carries **sub-second settlement jitter** (observed offsets from the hour: `.003`, `.050`, `.080`, `.129`, `.134`, `.201` s). Joins **must floor to the hour**; exact-ms equality would silently drop rows. This is a plausible mechanical explanation for the prior probe's single missing bucket [INFERENCE — not reproduced here; a 2-hour window between settlements can legitimately contain 0 rows].

**Field note (documented, not inferred):** `fundingRate` is frequently pinned at exactly `0.0000125`. HL's funding doc fixes the interest-rate component at 0.01%/8h = 0.00125%/hour, and the closed-form rate `F = P + clamp(interest − P, −0.0005, 0.0005)` collapses to `F = interest` whenever `|interest − P| ≤ 0.0005`. The observed constant is that documented hourly interest component. **What this does NOT prove:** nothing about expected P&L; the value is recorded here only as a field-characteristic that any consumer must expect.

## 6. Hyperliquid S3 archive — exact access requirement (the only missing object)

Official docs (`hyperliquid.gitbook.io/hyperliquid-docs/historical-data`, read 2026-09-29): *"Historical data is uploaded to the bucket `hyperliquid-archive`… **Note that the requester of the data must pay for transfer costs.**"* Layout given: `s3://hyperliquid-archive/market_data/[date]/[hour]/[datatype]/[coin].lz4` (L2 book snapshots) and `s3://hyperliquid-archive/asset_ctxs/[date].csv.lz4`. Fills/trades/explorer/funding events live in `s3://hl-mainnet-node-data/…`. The docs also state: *"No other historical data sets are provided via S3 (e.g. candles or spot asset data)."*

Empirical confirmation, anonymous, no credentials:

```
2026-09-29T21:35:30Z  HEAD hyperliquid-archive.s3.ap-northeast-1.amazonaws.com/?list-type=2
                      -> 301, x-amz-bucket-region: ap-northeast-1
GET hyperliquid-archive.s3.amazonaws.com/?list-type=2&max-keys=2          -> 403
GET hyperliquid-archive.s3.amazonaws.com/asset_ctxs/20260101.csv.lz4      -> 403
GET same + x-amz-request-payer: requester (no creds)                      -> 403
GET hl-mainnet-node-data.s3.ap-northeast-1.amazonaws.com/?list-type=2     -> 403
GET hl-mainnet-node-data… + x-amz-request-payer: requester                -> 403

body (both buckets):
<Error><Code>AccessDenied</Code><Message>Anonymous users cannot invoke requests against
Requester Pays buckets. Please authenticate.</Message>…
```

**Exact access requirement:** an **authenticated AWS principal** (that is a credential) that accepts being billed for request + egress on a requester-pays bucket. **Listing is not free either** — the bucket refuses anonymous `ListObjectsV2` and anonymous object GET even when the caller offers the `x-amz-request-payer: requester` header, because there is no identity to bill. There is therefore **no free, no-auth path to this archive**, and per campaign constraints it is out of reach.

**The named missing object:** historical HL oracle price, obtainable free only from
`s3://hyperliquid-archive/asset_ctxs/[YYYYMMDD].csv.lz4` (**requester-pays**).

## 7. Synchronized same-UTC-hour join — executed, not asserted

Window **2026-06-01T00:00Z → 2026-08-31T16:00Z** (three months; fully inside the free HL 1h-candle horizon).

* HL funding: 5 bounded `/info` requests → 2208 hourly rows, zero gaps.
* Binance: 9 anonymous `data.binance.vision` monthly zips (3 × `klines`, 3 × `markPriceKlines`, 3 × `fundingRate`) + 1 daily `markPriceKlines` zip to repair the 2026-06-29 monthly hole.
* HL mid: 1 `/info` `candleSnapshot` request (`1h`) → 2209 candles, 2026-06-01T00:00Z → 2026-09-01T00:00Z.
* Alignment: floor `calc_time` / `time` to the hour; join on Binance's 8-hourly settlement grid (00/08/16 UTC).

```
Binance funding rows 276   span 2026-06-01T00:00:00.001Z -> 2026-08-31T16:00:00.001Z  (interval_hours all 8)
Binance 1h klines 2208 / markPriceKlines 2184 (+24 daily fallback = 2208) / both grids complete
HL hourly funding 2208     span 2026-06-01T00:00:00.050Z -> 2026-08-31T23:00:00.129Z
HL 1h candles 2209

FINAL JOIN 276 of 276   missing []   (hl mid missing 0)
```

Evidence file: `probes/probe_c_join_2026-06_2026-08.csv` (276 data rows).
Columns: `utc_hour, hl_funding_rate, hl_premium, hl_mid_1h_close, binance_funding_rate, binance_funding_interval_hours, binance_kline_close, binance_mark_close`.

First and last rows, verbatim:
```
utc_hour,hl_funding_rate,hl_premium,hl_mid_1h_close,binance_funding_rate,binance_funding_interval_hours,binance_kline_close,binance_mark_close
2026-06-01T00:00:00Z,0.0000125,-0.0002835026,73870.0,0.00005703,8,73855.00,73855.00000000
2026-06-01T08:00:00Z,0.0000125,-0.0002425802,73906.0,0.00004438,8,72875.70,72875.70000000
2026-06-01T16:00:00Z,0.0000125,-0.0000688623,73319.0,0.00010000,8,71537.70,71538.00284858
…
2026-08-31T16:00:00Z,0.0000125,-0.000124347,78520.0,0.00010000,8,78600.70,78608.41398551
```

**Free HL price horizon (measured, not quoted).** `candleSnapshot` truncates to the most recent ~5000 candles:
```
1h: requested start 2025-01-01, got 4982 candles, oldest 2026-03-05T11:00Z, newest 2026-09-29T00:00Z
1d: requested start 2020-01-01, got 2233 candles, oldest 2020-08-19T00:00Z (= HL launch), newest 2026-09-29T00:00Z
```
So free HL *intraday* price reaches back ≈208 days; free HL funding reaches back to 2023-05-12 (hourly from 2023-06-25T12:00Z). The two horizons do not coincide.

For completeness, HL's live context endpoint (`metaAndAssetCtxs`, HTTP 200, current values only — **no historical parameter**) exposes for BTC:
```json
{"funding":"0.0000081998","openInterest":"35498.09446","prevDayPx":"83380.0",
 "dayNtlVlm":"2137421144.3379197192","premium":"-0.0004540608","oraclePx":"83469.0",
 "markPx":"83430.0","midPx":"83428.5","impactPxs":["83428.0","83431.1"],"dayBaseVlm":"25555.73209"}
```
`oraclePx`/`markPx` are present **only for the current instant**, which is why the historical oracle price remains the single missing object.

## 8. What each probe does NOT prove

| Probe | Does not prove |
|---|---|
| `data.binance.vision` fetch | that any *arbitrary* key exists (no anonymous listing) — only that the keys tested exist and 404 is returned for bogus keys. |
| `fapi.binance.com` 451 | global unavailability of Binance USD-M data. Same-provider archive host served all required files. |
| HL `fundingHistory` depth | that every historical hour is populated — continuity was verified only for 2026-06-01→2026-08-31 (2208/2208) and 2023-05-12→2023-06-25 (500/500); the 2023-06-25→2026-06-01 span was *not* pulled in full (≈57 requests). Its availability is inferred from the endpoints' 500-row pagination rule, not executed end-to-end. |
| HL cadence transition | the exact reason HL switched 8h → 1h; only that the last 8h-spaced row is 2023-06-25T11:00:00Z and the first 1h-spaced row is 2023-06-25T12:00:00Z. |
| HL S3 403 | that the data is absent — it exists and is documented; it is only *paid* to read. |
| 276/276 join | anything economic: no fees, no funding-differential magnitude, no P&L, no strategy. Only that the named fields exist and align on the same UTC hour. |
| `0.0000125` pinning | the distribution of HL funding generally; it was observed in the Jun–Aug 2026 window only. |

## 9. Residual gaps (exact, actionable)

1. **Binance funding for the most recent ~1 month** is not on the free archive (monthly files publish "the first monday of the month"; USD-M has **no** daily `fundingRate` directory). At probe time free Binance funding ended at **2026-08-31T16:00Z**. Covering 2026-09-01→now requires `fapi.binance.com` (`/fapi/v1/fundingRate`), which is **451 in this environment only**. `klines` and `markPriceKlines` for September *are* free (daily files, ~1-day lag), so only the funding series has this lag.
2. **HL historical oracle price** — no free path; requester-pays only (§6).

## 10. Reproduce

```bash
# Binance archive (anonymous)
curl -sS -o fr.zip "https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-08.zip"
curl -sS -o kl.zip "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2026-08.zip"
curl -sS -o mp.zip "https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2026-08.zip"
# HL hourly funding, paged at 500 rows; floor `time` to the hour before joining
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"type":"fundingHistory","coin":"BTC","startTime":1780272000000,"endTime":1788220800000}' \
  https://api.hyperliquid.xyz/info
# HL hourly mid (most recent ~5000 candles only)
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"type":"candleSnapshot","req":{"coin":"BTC","interval":"1h","startTime":1780272000000,"endTime":1788220800000}}' \
  https://api.hyperliquid.xyz/info
# S3 access requirement (expected: 403 Anonymous users cannot invoke requests against Requester Pays buckets)
curl -sS "https://hyperliquid-archive.s3.amazonaws.com/?list-type=2&max-keys=2"
```
