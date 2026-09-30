# PROBE-B-FREE-ITCH-INVENTORY — free Nasdaq TotalView-ITCH 5.0 sample sessions

Probe: `PROBE-B-FREE-ITCH-INVENTORY` · capability `PRIMARY_SOURCE_SEARCH, DATA_PROBE`
Campaign: `GOAL-M2-BRIDGE-001` (read-only) · branch B second-session question
Probe window (UTC): **2026-09-29 21:34Z → 2026-09-29 21:40Z** (all retrievals below inside this window unless stated)
Local scratch for the few range-fetched byte slices: `/tmp/itchprobe/` (nothing downloaded was deleted; no file larger than ~300 KB was fetched per target; no multi-GB download was performed)

Constraints honoured: no purchase, no subscription, no credential, no API key, no account, no entitlement
circumvention. Every retrieval below is anonymous HTTP(S) or anonymous FTP. No file was written outside
`.research/m2_bridge_001/probes/`; no canonical artifact, code, or freeze was touched.

Canonical facts not contradicted: the repo's existing tape is the emi.nasdaq.com sample
`07302019.NASDAQ_ITCH50.gz` (3,662,140,094 B, sha256 `c65784c4…2d4a`, md5 `8744aba2…c924`, recorded in
`M2/data/manifests/raw_manifest.json`) covering **2019-07-30**, session span recorded there as
`coverage_start_ns = 10970642174571` (03:02:50.2 ET) → `coverage_end_ns = 72300000037782` (20:05:00.0 ET),
282,229,684 framed messages. Nothing in this probe contradicts that.

---

## 0. Answer up front

**A second free TotalView-ITCH 5.0 session (and many more) is published with no auth and no purchase.**
The block condition `EXTERNAL_DATA_BLOCK` is **NOT triggered**. Six additional dated binary blocks plus up to
eleven `S<MMDDYY>-v50` blocks are reachable at HTTP 200 on `emi.nasdaq.com`, none of them 2019-07-30.

Caveat carried forward verbatim into §5: the provider **does** state (BinaryFILE spec §1.1) that one file = one
session, but it states **no clock-hour coverage**, and the per-file completeness marker is **not** verified for
any file other than the one already on disk. Treat "contains 09:30–16:05 ET" for a *new* date as
*format-level stated + needs one-time confirmation*, not as observed.

---

## 1. What is actually listed — `https://emi.nasdaq.com/ITCH/` (IIS directory index, anonymous)

Root of the ITCH tree, retrieved 2026-09-29T21:34:19Z (HTTP 200, 733 B):

| entry | index mtime |
|---|---|
| `/ITCH/GIS/` | 2020-05-08 |
| `/ITCH/Nasdaq BX ITCH/` | 2021-07-21 |
| `/ITCH/Nasdaq ITCH/` | 2026-08-06 |
| `/ITCH/Nasdaq PSX ITCH/` | 2021-07-21 |
| `/ITCH/NOII Beta Files/` | 2019-03-28 |
| `/ITCH/Stock_Locate_Codes/` | 2026-09-29 |

Child directories enumerated in full (each listing retrieved once, complete — tails confirmed):

* `/ITCH/Nasdaq ITCH/` — the **only** directory holding Nasdaq-venue TotalView-ITCH 5.0 day files.
* `/ITCH/Nasdaq ITCH/FEB 2022 Files/` — **empty**.
* `/ITCH/Nasdaq ITCH/NOII/` — one file (`S050922-v50-NOII.txt.gz`).
* `/ITCH/Nasdaq BX ITCH/` (+ `March 20/`) — BX venue, ITCH 5.0.
* `/ITCH/Nasdaq PSX ITCH/` — PSX venue, ITCH 5.0.
* `/ITCH/GIS/Aug 5-9 2019/` — **empty**; `/ITCH/GIS/BX Jan 2020/` — 3 files; `/ITCH/GIS/NOII 2019/` — 1 file;
  `/ITCH/GIS/Nov 18, Dec 18, Jan 19/` — 3 files.
* `/ITCH/NOII Beta Files/` — **empty**.
* `/ITCH/Stock_Locate_Codes/` — not enumerated (out of scope: locate-code maps, not tapes).

The index is **live and mutable** (the `/ITCH/` directory itself was modified 2026-08-06, and the `Nasdaq ITCH`
listing contains files deposited 2026-06-23 and 2026-08-05). **Today's listing is therefore not evidence of
historical retention**, and nothing here should be read as a retention guarantee: apart from one ITCH-2.0-era
zip (2003) there is **no pre-2018 ITCH tape published at all**.

---

## 2. Reachable Nasdaq-venue TotalView-ITCH 5.0 sessions (HTTP, anonymous, no auth)

URL template: `https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/<filename>`. `status`/`len` from HTTP HEAD
(`curl -I -L`), 2026-09-29 21:34–21:40Z.

### 2a. Binary `MMDDYYYY.NASDAQ_ITCH50.gz` blocks — second-session candidates

| filename | date decoded from name | HTTP | Content-Length (B) |
|---|---|---|---|
| `01302019.NASDAQ_ITCH50.gz` | 2019-01-30 | 200 | 4,764,426,091 |
| `03272019.NASDAQ_ITCH50.gz` | 2019-03-27 | 200 | 5,510,131,732 |
| **`07302019.NASDAQ_ITCH50.gz`** | **2019-07-30 — the tape already held; not a second session** | 200 | 3,662,140,094 |
| `08302019.NASDAQ_ITCH50.gz` | 2019-08-30 | 200 | 4,075,649,457 |
| `10302019.NASDAQ_ITCH50.gz` | 2019-10-30 | 200 | 3,872,931,242 |
| `12302019.NASDAQ_ITCH50.gz` | 2019-12-30 | 200 | 3,524,013,057 |
| `01302020.NASDAQ_ITCH50.gz` | 2020-01-30 | 200 | 5,597,158,940 |

⇒ **6 further dates** (2019-01-30, 2019-03-27, 2019-08-30, 2019-10-30, 2019-12-30, 2020-01-30).

### 2b. `S<MMDDYY>-v50[-…].txt.gz` blocks in the same directory — same container, misleading extension

| filename | date decoded from name | HTTP | Content-Length (B) |
|---|---|---|---|
| `S101819-v50.txt.gz` | 2019-10-18 | 200 | 3,951,201,663 |
| `S071321-v50.txt.gz` | 2021-07-13 | 200 | 5,996,745,270 |
| `S081321-v50.txt.gz` | 2021-08-13 | 200 | 4,889,328,604 |
| `S112825-v50.txt.gz` | 2025-11-28 | 200 | 4,735,308,661 |
| `S120825-v50.txt.gz` | 2025-12-08 | 200 | 8,775,891,119 |
| `S120925-v50.txt.gz` | 2025-12-09 | 200 | 7,929,915,419 |
| `S121025-v50.txt.gz` | 2025-12-10 | 200 | 11,557,662,295 |
| `S121125-v50.txt.gz` | 2025-12-11 | 200 | 10,471,034,001 |
| `S121225-v50.txt.gz` | 2025-12-12 | 200 | 12,551,644,054 |
| `S061226-v50.txt.gz` | 2026-06-12 | 200 | 17,894,268,560 |
| `S070?`—`itch50_05_15.gz` | 2026-05-15 *(name does not follow the `S<MMDDYY>` convention; date is inference from drop date 2026-06-09 + name)* | 200 | 13,047,496,628 |
| `itch50_05_18.gz` | 2026-05-18 *(same caveat)* | 200 | 16,150,095,810 |

The `.txt.gz` suffix is **not** a text feed. Decompressed, these files are the identical byte-level BinaryFILE
container as the `.NASDAQ_ITCH50.gz` blocks (verified in §4). Date decoding for every `S…` file is a
name-to-date decode, not a provider assertion; the server's `Last-Modified` header is consistent with it in
every case checked.

### 2c. Excluded from the candidate set, listed for completeness

| file | why excluded |
|---|---|
| `S010303-v2.zip` (58,907,174 B, 200) | `-v2` ⇒ ITCH **2.0** era (2003-01-03), not ITCH 5.0 |
| `tvagg.gz` (294,755,242 B, 200) | name denotes an **aggregate**; a derived/aggregated product, not a raw order-by-order session. Not downloaded, not treated as raw ITCH. |
| `Nasdaq BX ITCH/20*.BX_ITCH_50.gz` (9 files, 391,242,214–1,657,609,465 B, all 200) | BX venue, not Nasdaq TotalView |
| `Nasdaq PSX ITCH/20*.PSX_ITCH_50.gz` (9 files + `S030220-v50-bx.txt.gz`), all 200 | PSX venue |
| `05302019.NASDAQ_ITCH50.gz` — **sits in the PSX directory**, 4,246,501,580 B, 200 | anomaly: a `NASDAQ`-labelled file inside `Nasdaq PSX ITCH/`, and 4.25 GB matches the TotalView size class, not the 2019 PSX class (~0.5 GB). Venue/product of this filename **must not be assumed**. |
| `Nasdaq ITCH/NOII/S050922-v50-NOII.txt.gz` (96,588,423 B, 200); `GIS/NOII 2019/12062019.NOII.gz` (53,963,965 B, 200); `/Nasdaq NOIView/NOIView_May_9_2022.gz` (79,316,194 B, 200) | NOII / NOIView products, reachable free and anonymous; **inventory only — no NOII analysis performed here** (out of scope). Recorded because they bear on branch B's NOII leg. |
| `GIS/Nov 18, Dec 18, Jan 19/S121318-v50.txt.gz`, `S121418-v50.txt.gz`, `S123118-v50.txt.gz` (4.93–5.24 GB, all 200) | same `S…-v50` product; dates decode to 2018-12-13, 2018-12-14, 2018-12-31. Additional free Nasdaq-venue sessions. |
| `GIS/BX Jan 2020/S012720,S012820,S013120-v50-bx.txt.gz` (481–866 MB, all 200) | BX venue |

---

## 3. Listed-but-not-retrievable, and other dead ends

* **Every companion metadata file is a 404.** The index lists `*.NASDAQ_ITCH50.gz.md5sum`, `*.BX_ITCH_50.gz.md5sum`,
  `*.PSX_ITCH_50.gz.md5sum` and `S…-v50.txt.done`, but all returns `404` (ASP.NET error page, 1,245 B):
  `07302019.NASDAQ_ITCH50.gz.md5sum` → 404; `01302019…md5sum` → 404; `20190730.BX_ITCH_50.gz.md5sum` → 404;
  `S112825-v50.txt.done` → 404. **Consequence: no provider-published checksum is retrievable, so the integrity of
  any new download cannot be checked against the provider** (the repo's 2019-07-30 hash is therefore local-only evidence).
* **Eight filename dates appear only as `… .gz.md5sum` entries with no `.gz` present, and both the listed `.gz` and the
  listed `.md5sum` return 404** (`01302018`, `03292018`, `05302018`, `05302019`, `07302018`, `08302018`, `10302018`,
  `12282018` → filename dates 2018-01-30, 2018-03-29, 2018-05-30, **2019-05-30**, 2018-07-30, 2018-08-30,
  2018-10-30, 2018-12-28). These are **stale index entries**: the 2018 dates and 2019-05-30 are not published.
  (2019-05-30 does exist in the *PSX* directory as `PSX ITCH/05302019.NASDAQ_ITCH50.gz`, 200 — see the anomaly note in §2c.)
* **Anonymous FTP on `emi.nasdaq.com` is not available** — `ftp://emi.nasdaq.com/ITCH/` timed out twice
  (22 s and 25 s). The working path to this content is `https://emi.nasdaq.com/…` only.
* **`ftp://ftp.nasdaqtrader.com/` is reachable anonymously** (FTP status 226) but carries **no order-by-order ITCH
  tapes**: root holds `atsactivity, Closingcross, Downloads, ETFData, Files, MonthlyShareVolume, Openingcross,
  OrderExecutionQuality{,BX,PSX}, PHLX, Symboldirectory`. `Downloads/` → empty (226, 0 B);
  `Files/marketdata/itch/` → **empty** (226, 0 B; the historical-ITCH shelf is bare);
  `Files/marketdata/` holds only `corrections/, itch/, sip/, TradeErrors/`; `Closingcross/` holds
  `ClosingcrosseligibilityMMDDYYYY.txt` files dated 2005–2006 only; `Files/crosses/` holds `CrossStats*.txt`
  derived cross summaries. **Nothing here is a raw ITCH session file.**
* **`https://www.nasdaqtrader.com/Trader.aspx?id=ITCH`** no longer serves ITCH sample data — it renders the
  Nasdaq Data Link (jsdelivr/CDN) application shell. `Trader.aspx?id=HistoricalData` returns
  "Page may have been moved or has been retired". Nasdaq's own site therefore does **not** expose a second
  sample-file directory; `emi.nasdaq.com` is the single provider-hosted source.
* Licenced/paid channels were **not** used and are out of scope by constraint: the SFTP historical service
  (`ITCHFTP.pdf`), Nasdaq Data Link, Databento, LOBSTER-style vendors. They are not free, not anonymous, and
  are not counted as availability.

---

## 4. Structural verification that these are raw ITCH 5.0 sessions, not derived products

Method: HTTP `Range: bytes=0-16383` (status `206`), raw-inflate the first 16 KB of the gzip member, walk the
BinaryFILE frame chain (2-byte big-endian payload length, per the BinaryFILE spec quoted in §5), decode message
type / Stock Locate / Tracking Number / 6-byte timestamp (offsets per TotalView-ITCH 5.0 §1.1 and §1.2.1).

| file | frame 0 | frame 0 len | frame 0 locate | frame 0 timestamp | next frames |
|---|---|---|---|---|---|
| `07302019.NASDAQ_ITCH50.gz` (held) | `S` | 12 | 0 | 10,970,642,174,571 ns (03:02:50.2) | `R R R …` |
| `01302019.NASDAQ_ITCH50.gz` | `S` | 12 | 0 | 11,039,687,760,787 ns (03:03:59.7) | `R R R …` |
| `03272019.NASDAQ_ITCH50.gz` | `S` | 12 | 0 | 10,951,068,525,924 ns (03:02:31.1) | `R R R …` |
| `08302019.NASDAQ_ITCH50.gz` | `S` | 12 | 0 | 11,046,036,981,912 ns (03:04:06.0) | `R R R …` |
| `10302019.NASDAQ_ITCH50.gz` | `S` | 12 | 0 | 10,951,647,283,487 ns (03:02:31.6) | `R R R …` |
| `12302019.NASDAQ_ITCH50.gz` | `S` | 12 | 0 | 11,072,057,543,747 ns (03:04:32.1) | `R R R …` |
| `01302020.NASDAQ_ITCH50.gz` | `S` | 12 | 0 | 10,953,404,452,051 ns (03:02:33.4) | `R R R …` |
| `S101819-v50.txt.gz` | `S` | 12 | 0 | 11,022,641,474,038 ns (03:03:44.1) | `R R R …` |
| `S112825-v50.txt.gz` | `S` | 12 | 0 | 10,889,349,046,735 ns (03:01:29.3) | `R R R …` |
| `S121225-v50.txt.gz` | `S` | 12 | 0 | 10,889,228,827,478 ns (03:01:29.2) | `R R R …` |
| `S061226-v50.txt.gz` | `S` | 12 | 0 | 10,892,008,976,642 ns (03:01:40.9) | `R R R …` |
| `itch50_05_15.gz` | `S` | 12 | 0 | 10,883,320,897,326 ns (03:01:23.2) | `R R R …` |

Also verified: `1f 8b` gzip magic at offset 0 for every one of these (HTTP 206, 2-byte range).

Consequences, all observed:
1. Every candidate is the **same BinaryFILE container as the tape already in the repo** — 2-byte big-endian
   length prefix, `S` System Event (12 B, locate 0) first, then the `R` Stock Directory spin. This is
   order-by-order ITCH 5.0, not a summary, not consolidated Level 1.
2. Every candidate **opens with Start of Messages in the 03:01–03:05 ET window**, not at 09:30. A
   regular-hours-only clip (09:30–16:00) is therefore **excluded for the front of every candidate**.
3. Gzip trailers (`Range: bytes=-8`, status 206) are single-member gzip whose `ISIZE` is the uncompressed size
   modulo 2³²: `07302019` → 71,744,821 ≡ 8,661,679,413 (mod 2³²), which reproduces the repo's recorded
   decompressed size exactly; `12302019` → 3,956,440,613 and `01302020` → 67,149,890, both consistent with a
   full-day volume at the ~2.3× compression ratio the held tape exhibits. Multi-member gzip was ruled out for
   the tail (zero `1f 8b 08` member headers in the last 64 KB of `12302019`), which is why a byte-range tail
   decode of the *last* messages is not possible without transferring most of the file.

---

## 5. Session coverage — what is STATED, and what is still an assumption

`[STATED]` **Nasdaq BinaryFILE, v1.00 (2010-03-30), §1.1** — `https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/binaryfile.pdf`,
retrieved 2026-09-29T21:39Z, HTTP 200:
> "Each BinaryFILE file corresponds to a single session. The session ID is not contained in the file since it
> is assumed that it will be included in the filename or externally if necessary."
> "The messages are variable length and include a two byte big-endian length that indicates the length of the
> payload and then the variable length payload itself."
> "A message of length zero is used to indicate the end of the session. If a BinaryFILE file does not end with an
> empty message, this indicates that the file is incomplete and there may be additional messages available in the session."

`[STATED]` **Nasdaq TotalView-ITCH 5.0 (§1.1), rev 2023-04-28** — file already in the repo at
`M2/data/reference/NQTVITCHspecification.pdf`, and republished at
`https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf`:
`"O" Start of Messages` is "the first message sent in any trading day"; `"C" End of Messages` is "always the last
message sent in any trading day". The spec also fixes the NOII windows relevant here: NOII is disseminated every
10 s between 09:25–09:28 and **15:50–15:55**, every 1 s between 09:28–09:30 and **15:55–16:00**, and an Extended
Trading Close NOII runs 16:00–16:05 (Cross Type `A`).

`[NOT STATED]` **No clock-hour coverage is stated anywhere.** Neither the BinaryFILE spec nor the ITCH 5.0 spec
says that a published file spans 09:30–16:05 ET. The BinaryFILE spec states *one file = one session* and that a
well-formed file terminates with a zero-length message; it does not state which wall-clock hours that session
covers, and the ITCH spec gives no file-level window at all. There is no README in any ITCH directory and **no
retrievable provider metadata** (§3), so a per-file coverage claim cannot be sourced from the provider.

`[OBSERVED, one file only]` For the tape already held — 2019-07-30 — the repo records
`coverage_start_ns = 10970642174571` (03:02:50.2 ET) and `coverage_end_ns = 72300000037782` (20:05:00.0 ET)
(`M2/data/manifests/raw_manifest.json`, `…/ingest_summary.json`). That window strictly contains 09:30–16:05 ET,
so the closing-cross window is present **for that date**.

`[ASSUMED for every other file]` For any *new* date, "the file contains 09:30–16:05 ET" is **assumed**, supported
by: (i) the format-level one-file-per-session statement; (ii) the observed ~03:02 ET Start-of-Messages front end in
all twelve heads decoded (§4), which already excludes a regular-hours trim at the front; (iii) uncompressed
volumes in the full-day range. It is **not** observed. The only decisive confirmation is the BinaryFILE
completeness rule — decode to the last frame and require a terminating zero-length message plus a `C` End of
Messages System Event — which requires a full-file transfer (3.5–17.9 GB per file) and was **deliberately not
performed** under this probe's small budget and its "do not download multi-GB unless a HEAD/range request is
insufficient" rule. Note the transfer cost is one-time per date, and the check yields a reusable, dated proof.

Recommendation (for the main agent, not executed here): on first acquisition of a second date, stream-decompress
and assert `last_frame_len == 0` and the final System Event code is `C`; record that as the coverage proof before
any branch-B number is computed on that date.

---

## 6. Bottom line for branch B

* Second free TotalView-ITCH 5.0 sessions, **all different from 2019-07-30**, reachable anonymously at HTTP 200:
  **2019-01-30, 2019-03-27, 2019-08-30, 2019-10-30, 2019-12-30, 2020-01-30** (binary) and
  **2019-10-18, 2021-07-13, 2021-08-13, 2025-11-28, 2025-12-08, 2025-12-09, 2025-12-10, 2025-12-11,
  2025-12-12, 2026-06-12, 2026-05-15, 2026-05-18** (`S…`/`itch50_…`), plus 2018-12-13, 2018-12-14, 2018-12-31.
* Same container and product as the held tape (verified by head decode on 12 files); raw order-by-order
  ITCH 5.0, `I` (NOII) messages are part of the ITCH 5.0 message set and therefore expected in these files, but
  **actual presence of `I`/`Q`/`P` messages in any specific new file was not verified here** (a head decode of
  16 KB only reaches the Stock Directory spin at ~03:02).
* Nearest-in-time same-era options for a branch-B second session: 2019-08-30 or 2019-10-30 (same year, same
  venue, comparable size class) — 2019-10-18 (`S101819`) is 3.95 GB and is the closest date to the held tape.
* Block condition: **not triggered**. One honest gap remains and it is not a data-access gap: per-file clock-hour
  coverage is format-level stated and *assumed* per date until the zero-length terminator is confirmed on
  first download.

---

## 7. Explicitly unverified

1. Per-file clock-hour coverage for every file except 2019-07-30 (see §5 for the confirmation recipe).
2. Presence of `I` (NOII), `Q` (Cross Trade) and `P` (Trade) message types in any new file — head decode does
   not reach the auction window.
3. Remote-file hashes: no provider checksum is retrievable (§3); only `Content-Length` equality with the index
   was checked. Bytes were verified only at offset 0 (gzip magic) and, for three files, the gzip trailer.
4. Exact date of `itch50_05_15.gz` / `itch50_05_18.gz` — names do not follow the `S<MMDDYY>` convention; dates
   2026-05-15 / 2026-05-18 are inferred from the drop date (2026-06-09) and name, not asserted.
5. Venue/product of `Nasdaq PSX ITCH/05302019.NASDAQ_ITCH50.gz` — flagged as an anomaly, not resolved.
6. Whether the `S…-v50.txt.gz` files are the Nasdaq-venue TotalView product under Nasdaq's internal "session"
   naming: the decoded Stock Directory header (locate 1 = `A`, market category `N`) is byte-identical to the
   held TotalView tape's, which is strong evidence of the same product, but the filename does not state a venue.
7. Retention: nothing here implies any of these files will still be present later; the index is actively mutated
   (2026-06-23 and 2026-08-05 deposits observed).

## 7b. Machine-readable evidence beside this file

* `PROBE_B_head_sweep.json` — per-file `{dir, file, status, content_length}` for all 56 HEAD requests.
* `PROBE_B_head_decode.json` — frame-0 decode (`type`, `len`, `locate`, `start_ts_ns`, next frame types) for the 12 files range-fetched and decoded.
* Raw byte slices used for the decodes remain at `/tmp/itchprobe/` (nothing deleted).

## 8. Sources

* `https://emi.nasdaq.com/ITCH/` and children — anonymous HTTP(S), 200, retrieved 2026-09-29T21:34–21:40Z.
* `https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/binaryfile.pdf` — BinaryFILE v1.00, 200, retrieved 2026-09-29T21:39Z.
* `https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf` — TotalView-ITCH 5.0, same document as `M2/data/reference/NQTVITCHspecification.pdf`.
* `ftp://ftp.nasdaqtrader.com/` (+ `Files/`, `Files/marketdata/`, `Files/marketdata/itch/`, `Downloads/`, `Closingcross/`, `Files/crosses/`) — anonymous FTP, status 226, retrieved 2026-09-29T21:38–21:40Z.
* `https://github.com/justinabate/nasdaq_itch_pcap` — third-party corroboration that `emi.nasdaq.com` sample files are BinaryFILE-format session captures; not used as a source of data.
* Repo references read (not modified): `M2/data/manifests/raw_manifest.json`,
  `M2/data/derived/NASDAQ-ITCH50-PUBLIC-SAMPLE-20190730/ingest_summary.json`,
  `M2/output/data_quality/schema_contract.md`.
