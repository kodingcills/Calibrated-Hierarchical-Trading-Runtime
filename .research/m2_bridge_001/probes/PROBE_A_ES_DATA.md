# PROBE-A-ES-FREE-DATA — Is there a free, no-auth, publicly retrievable CME ES historical object?

Assignment: PROBE-A-ES-FREE-DATA · Campaign: GOAL-M2-BRIDGE-001 · Probe window: 2026-09-29T21:34:20Z – 2026-09-29T21:45Z (per-URL re-verify 2026-09-29T21:42:11Z)
Constraints honored: no purchase, no trial signup, no key issuance, no login scraping, no entitlement circumvention, no credential use.
Method: plain unauthenticated HTTP (curl, no cookies, no keys) + headless rendering of public pages + binary decode of downloaded bytes.

## VERDICT (one paragraph)

**A free, no-auth ES historical object DOES exist: Databento's public CME Globex MDP 3.0 sample PCAPs** (`https://sample-pcaps-dl.databento.com/glbx-all/...`), fetchable with HTTP 200/206 and no credentials, containing **genuine ES order-by-order (MBO), book (MBP), and trade-summary MDP 3.0 messages** with nanosecond exchange send-times. Coverage is bounded to **two dates (2023-07-16, 2023-07-17)**, with full-day files for both plus 10-minute slices including the 2023-07-17 13:30:00Z US cash open (verified ≈4.9k ES messages/s). This is sufficient to **construct and validate a causal H3 (10–100 ms) OFI → gross-markout pipeline on ES**, but is **not** a materiality-grade multi-session/month sample, and Databento's ToU conditions downloading "Materials" on its User Agreement (see caveat 3). CME itself offers **nothing retrievable** by this campaign (403 IP block for cmegroup.com; DataMine unreachable at TLS). Every other "free" ES-named source found is either bars-only, account-walled, or **not ES futures at all** (index/ETF/CFD proxies).

Branch-A status: **NOT_EXTERNAL_DATA_BLOCK, but PARTIAL** — free ES data exists and H3 linkage is constructible; what is missing is *breadth* (multi-week/month, multi-session), not existence.

## Candidate table

| # | Candidate object | URL | HTTP / bytes | Coverage | Native fields | Timestamp semantics | License / terms | What it does NOT prove |
|---|---|---|---|---|---|---|---|---|
| 1 | **Databento CME MDP 3.0 sample PCAP, full day A side** | `https://sample-pcaps-dl.databento.com/glbx-all/20230716/dc3-glbx-a-20230716.zip` | 206 / 1,673,726,954 | 2023-07-16 session (Sun open onward) | Raw MDP 3.0 SBE: MBO (47), MBP book (46), TradeSummary (48), Volume (37), SessionStatistics (51), SecurityStatus (30), Definitions (54) | pcap ts ns (`0xa1b23c4d`); per-packet 8-byte exchange send-time (ns since epoch); per-message TransactTime | Public download link, **no auth**; Databento ToU §General Use Provisions conditions copying/downloading Materials on entering the User Agreement; CME exchange-data terms apply | Multi-day/month breadth; ES-only scope (feed is market-wide); ready-to-use CSV; anything about markout economics |
| 2 | **Same, A & B sides deduplicated, full day** | `.../20230716/dc3-glbx-ab-dedup-20230716.zip` | 206 / 1,675,700,985 | 2023-07-16 | as above, both feeds (A ports 14xxx, B ports 15xxx) | as above | as above | as above |
| 3 | **A & B dedup full day (full RTH session)** | `.../20230717/dc3-glbx-ab-dedup-20230717.zip` | 206 / 144,637,439,344 | 2023-07-17 (Mon, full session) | as above | as above | as above | as above |
| 4 | **10-min slice, US cash open (highest value)** | `.../20230717/dc3-glbx-ab-dedup-20230717T133000.pcap.zst` | 206 / 6,817,448,746 | 2023-07-17 13:30:00Z (09:30 ET open) | as above; measured **3,351 ES-channel msgs in 0.68 s** (t46:2356, t47:525, t48:235, t37:235) ≈ **4.9k msg/s** | ns | as above | Breadth; decode remains the campaign's cost |
| 5 | 10-min slice, Sunday open | `.../20230716/dc3-glbx-a-20230716T220000.pcap.zst` | 206 / 329,322,493 | 2023-07-16 22:00:00Z (17:00 CT Sun open) | as above; measured 2,937 ES-channel packets / 3,378 msgs in 28.8 s (t46:1478, t47:1475, t48:197, t37:194, t51:34, t30:2×, SecurityGroup ASCII `ES`) | ns | as above | Breadth (thin Sunday session) |
| 6 | 10-min slice, market closed | `.../20230716/dc3-glbx-a-20230716T110000.pcap.zst` | 206 / 30,589,323 | 2023-07-16 11:00:00Z (closed) | heartbeat/keepalive class | ns | as above | Any ES order flow (market closed) |
| 7 | **CME channel config (authoritative channel→product map)** | `.../20230716/config-2023-07-16.xml` | 200 / 299,220 | config dated 2023/07/14, 39 channels, 2761 products | XML: channel 310 "CME Globex Equity Futures" → product `ES` → group `ES`; conn `310IA` feed A UDP 224.0.31.1:14310, `310IB` feed B :15310 | n/a | CME configuration file (published by CME, redistributed as part of sample set) | Proves mapping only, not data content by itself |
| 8 | **Databento public GitHub MDP3 fixtures (real ES)** | `https://raw.githubusercontent.com/databento/databento-python/main/tests/data/GLBX.MDP3/test_data.{mbo,mbp-10,tbbo,trades,definition}.dbn.zst` | 200 / 191, 422, 256, 217, 288 | `ESH1`, 2020-12-28T00:00:00Z, `limit 4` → **4 records/file** | DBN: `ts_event`(ns), `ts_recv`(ns), `ts_in_delta`, `sequence`, `order_id`, `side`, `price`, `size`, `action`, `flags`, bid/ask px/sz/ct ×10 (mbp-10) | ns event + capture timestamps, delta from ts_recv | Repo Apache-2.0 (test fixtures) | Any statistical measurement — 4 events only |
| 9 | Databento Historical API (`GLBX.MDP3`, schema `mbo`) | `https://hist.databento.com/v0/metadata.list_datasets` · `.../timeseries.get_range?dataset=GLBX.MDP3&schema=mbo&...` | **401** / 30 (both) `{"detail":"Not authenticated"}` | n/a | n/a | n/a | Free $125 credits require **signup** (catalog CTA "Sign up for $125 in free credits") | — retrieval blocked at auth wall |
| 10 | CME Group public pages / DataMine | `https://www.cmegroup.com/market-data/datamine-historical-data.html` · `/markets/equities/sp/e-mini-sandp500.html` · `/confluence/display/EPICSANDBOX/CME+DataMine` | **403** / 602 each (JSON: "This IP address is blocked due to suspected web scraping activity… Use of scripts, software, spiders, robots, avatars, agents, tools or other scraping mechanisms is strictly prohibited") | n/a | n/a | n/a | CME website Data Terms of Use **prohibit automated retrieval**; DataMine requires registration + per-file payment | Whether CME ships any free ES sample — **unverifiable by this campaign** |
| 11 | CME DataMine host | `https://datamine.cmegroup.com/` (and `/login`) | TLS handshake failure (`SSLV3_ALERT_HANDSHAKE_FAILURE`) — **no HTTP status obtainable** | n/a | n/a | n/a | Registration wall (documented product) | — |
| 12 | FirstRate Data free ES sample (futures) | `https://frd001.s3.us-east-2.amazonaws.com/frd_sample_futures_ES.zip` | 200 / 210,837 | ES bars 2026-09-13 → 2026-09-28 (paid history 2008-01-02→) | CSV `timestamp,open,high,low,close,volume` (+`open interest` daily); 1min/5/30/1hour/1day **samples** | US Eastern; bar-stamped at period start | FirstRate license: royalty-free, attribution required, **no redistribution** | H3: 1-minute minimum resolution → 10–100 ms OFI impossible |
| 13 | Kibot free samples | `https://www.kibot.com/free-historical-intraday-data.html` | 200 / (page) | IBM, OIH (1-min), IVE, WDC (tick+bid/ask) — **US equities/ETFs only**; "Futures and forex samples are available on request" | n/a for ES | seconds resolution for ticks | Free samples no registration; **no ES free sample exists** | ES anything |
| 14 | Dukascopy free tick (lookalike) | `https://datafeed.dukascopy.com/datafeed/USA500IDXUSD/2024/00/02/14h_ticks.bi5` | 200 / 16,284 | hourly tick files, index CFD | LZMA tick: ms offsets, bid/ask, volumes | ms since hour start | Free public endpoint | **NOT ES futures** — S&P 500 index CFD, no CME order book/trade side, no venue |
| 15 | SPY / index / ETF proxies (FirstRate SPY zip, Kibot IVE tick, index feeds) | see #13, `https://frd001.s3-us-east-2.amazonaws.com/SPY_FirstRateDatacom.zip` | 200 | US equity session | trades with NBBO | seconds | vendor terms | **NOT ES futures** — different venue, microstructure, no futures roll/CME book |
| 16 | Excluded walls (no bypass attempted) | Kaggle `kaggle.com/datasets/choweric/cme-es` (login) · Nasdaq Data Link `data.nasdaq.com/api/v3/datasets/CHRIS/CME_ES1.csv` (**403** Imperva) · Zenodo API (**403** bot protection) · Harvard Dataverse search (`limit order book`+futures → 0 hits) | — | — | — | — | Account/key or ToU gates | — |

## Evidence chain for the ES claim on object #1/#3–#6 (decoded from bytes, not marketing)

1. **Config**: channel 310 = "CME Globex Equity Futures", product `ES` → group `ES`; feed A = UDP port 14310, feed B = 15310 (config XML, 299,220 B, HTTP 200).
2. **Traffic present**: 2,937 MDP 3.0 packets on dst port **14310** in the 2023-07-16 22:00:00.018507Z–22:00:28.805834Z window (26,214,400 compressed B → 103,677,952 decompressed B); header = 4-byte sequence + 8-byte nanosecond exchange send-time, then SBE `blockLength/schemaID/templateID/version`; message tiling clean on 2,937/2,937 packets.
3. **Group identity on that channel**: two `SecurityStatus` messages decode to body bytes containing ASCII SecurityGroup `ES` (`…0b 78 72 17 45 53 00 00 00 00…`).
4. **Message mix proves the schema needed for OFI**: template IDs observed = 46 `MdIncrementalRefreshBook`, 47 `MdIncrementalRefreshOrderBook` (order-by-order), 48 `MdIncrementalRefreshTradeSummary`, 37 `MdIncrementalRefreshVolume`, 51 `MdIncrementalRefreshSessionStatistics`, 30 `SecurityStatus` (IDs per public MDP 3.0 SBE template enum, Open-Markets-Initiative v1.10).
5. **Rate at the most informative window**: 2023-07-17 13:30:00.000010Z–13:30:00.677593Z → 2,454 ES-channel packets (14310: 2,246 / 15310: 208), 3,351 messages ≈ 4.9k msg/s → ~49 ES messages per 10 ms bucket (H3 resolution is *not* message-starved).
6. **Precision**: pcap magic `0xa1b23c4d` = nanosecond-resolution pcap; Databento documents DC3 capture via FPGA NIC + PTP hardware timestamping (pre-2017-05-21 legacy = FIX flat files, no capture ts — irrelevant for 2023 samples).

## Explicit non-claims

- These samples are **market-wide CME Globex MDP 3.0**, not ES-only extracts; ES is a subset (channel 310).
- **No decode/OFI computation was performed** (out of scope). ES SecurityIDs were not enumerated; group identity was established via SecurityStatus + CME channel config.
- **No claim** that CME itself publishes free ES data (unverifiable here) or that any other free ES tick source exists.
- **No entitlement/bypass used**: URLs answered without cookies, keys, accounts, or geo change.
- Coverage is **2 dates in July 2023** (+ 10-min slices); this cannot support a materiality verdict on its own.

## Caveats that must be signed off before campaign use

1. **Breadth**: free coverage = 2023-07-16 (Sun open, 1.67 GB A-side; also A&B dedup 1.68 GB) + 2023-07-17 (full day A&B dedup 144.64 GB) + 10-min slices (2023-07-17 13:30Z = US cash open, 6.82 GB; 2023-07-16 22:00Z, 329.70 MB A&B / 329.32 MB A-side). Multi-session/month coverage would require purchase — no budget authorized here.
2. **Engineering cost**: raw SBE + channel-config decode (packet reassembly, template 46/47/48 parsing, book reconstruction) is the campaign's own work; the sample is not CSV/DBN.
3. **Terms**: sample links are public with no auth, but Databento ToU ("General Use Provisions") restricts copying/downloading Materials outside the User Agreement, and CME exchange-data licensing (ILA / redistribution) governs downstream use. Recommend the campaign record a use decision (internal evaluation only, no redistribution) before ingesting.
4. **Sunday-side nuance**: the 2023-07-16 A-side files provide one feed; the A&B deduplicated variant (or the 2023-07-17 full day) is the safer base for lossless book reconstruction.

## Repro (bounded, no credentials)

```bash
# confirm no-auth retrieval + exact byte counts (206 partial content)
curl -sS -r 0-0 -D - -o /dev/null \
  https://sample-pcaps-dl.databento.com/glbx-all/20230717/dc3-glbx-ab-dedup-20230717T133000.pcap.zst | grep -i content-range
# fetch config + a bounded prefix of a slice, then decode
curl -sS -o cfg.xml https://sample-pcaps-dl.databento.com/glbx-all/20230716/config-2023-07-16.xml
curl -sS -r 0-20971519 -o part.zst \
  https://sample-pcaps-dl.databento.com/glbx-all/20230717/dc3-glbx-ab-dedup-20230717T133000.pcap.zst
# python: zstandard stream-decompress the truncation, walk pcap (magic 0xa1b23c4d, linktype 1, ns),
# IPv4/UDP where dport in {14310,15310}; skip 12-byte MDP3 packet header; read SBE blockLength/schemaID/templateID/version; count templateID
# (auth-wall proof) curl -sS -o /dev/null -w '%{http_code}\n' https://hist.databento.com/v0/metadata.list_datasets  -> 401
```

## Block statement (what is still missing, and what would resolve it)

Not a hard EXTERNAL_DATA_BLOCK: free ES data exists (objects #1–#7 above). What remains blocked is **breadth**: the smallest object that would settle materiality is **one month of CME MDP 3.0 MBO/MBP-10 + TradeSummary for the ES group, RTH, all sessions, with exchange send-times and a channel config** (e.g. Databento `GLBX.MDP3` `mbo`/`mbp-10`+`trades` for ES over ≥20 sessions). Resolution paths: (a) authorize a free-credit account (signup currently forbidden) or a purchase; (b) accept the 2023-07-16/17 sample as pipeline-validation-only evidence and downgrade the materiality claim accordingly.
