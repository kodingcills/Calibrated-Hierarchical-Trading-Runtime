# W2 — ES sample acquisition + structural admission (GOAL-M2-BRIDGE-001, epoch 1)

Scope: acquire the free, no-auth CME Globex MDP 3.0 sample capture for the 2023-07-17 RTH open
and produce an admitted, normalized ES event stream plus observed-spread cost inputs.
DATA AND TOOLING ONLY — no OFI state, no markout, no H3 evaluation, no P&L, no cost-ledger design.

**Verdict: admitted.** The 10-minute ES slice is retrieved, decoded, causally ordered, and
coverage-admitted (0.99998 of the 10 ms grid), with verified channel/instrument identity, trades
carrying aggressor side, top-of-book increments, and an observed-spread distribution ready to serve
as the frozen friction input. The independent admission engine (W4 `M2/src/admission.py`, contract
`ADMISSION-ES-H3-v1`) returns **DATA_VALID** on the produced `admission.json`.

## 1. Source and retrieval (every value observed)

| item | value |
|---|---|
| object | `dc3-glbx-ab-dedup-20230717T133000.pcap.zst` |
| URL | `https://sample-pcaps-dl.databento.com/glbx-all/20230717/dc3-glbx-ab-dedup-20230717T133000.pcap.zst` |
| probe | `curl -sS -r 0-1023 -D - -o -` -> **HTTP 206**, `content-range: bytes 0-1023/6817448746` |
| size | **6,817,448,746 B** (etag `"63b0cd00-1965a032a"`) |
| sha256 (full object, streamed) | `76170f3aadce97ab9b379b263e2fc979a7e52a884a79a509ff2c8fcff4c70053` |
| retrieval UTC | 2026-09-29T22:13:28Z (probe), acquisition pass 2026-09-29T22:13:2x-22:2xZ, wall 559.6 s (33,108,788 pcap records scanned, 382,893 ES packets admitted) |
| method | 1,626 ordered HTTP byte-range GETs (4 MiB chunks, 32 concurrent) -> single SHA-256 + `zstd -d -c` -> decode |
| provenance | `M2/data/derived_es/2023-07-17T133000Z/acquisition.json` (retained, hash-pinned) |

Two corrections to the work order, both discovered by probing:

1. The assignment URL omitted the date directory; `…/glbx-all/…` returns **404** while
   `…/glbx-all/20230717/…` returns 206. The directory index (`/glbx-all/20230717/`) is the
   authoritative name/size source.
2. The object is **6.8 GB**, not ~330 MB (330 MB is the *2023-07-16* Sunday-open slice,
   `dc3-glbx-a-20230716T220000.pcap.zst` = 329,701,340 B). Because it exceeds this epoch's 5 GB
   retention budget it was **streamed** — hashed and decoded on the fly, not retained. No purchase,
   subscription, key, account, or entitlement workaround was used.

## 2. What the bytes say (structure, not economics)

* pcap magic `0xa1b23c4d` = nanosecond pcap, version 2.4, link type 1 (Ethernet), snaplen 8174.
* MDP 3.0 framing: 12-byte packet header (`uint32` sequence + `uint64` ns exchange send time), then
  messages of `uint16 size` + SBE header (`blockLength`, `templateId`, `schemaId=1`, `version=9`).
* **33,108,788 pcap records** processed; **382,893** ES-channel packets; **449,990** messages;
  **0 message-tiling breaks** (every message ends exactly at its packet boundary).
* Templates on channel 310: 46 book 377,976 | 48 trade summary 18,092 | 47 order book 36,286 |
  37 volume 17,524 | 51 session statistics 111 | 49 daily statistics 1 (not decoded, reported).
* Layouts re-verified field-by-field against the CME-published SBE schema
  `Cme.Futures.Mdp3.Sbe.v1.9.xml` — `verify-layout` subcommand, `layout_verification` in the
  manifest (all six transcribed templates match: ids, block lengths, group dimensions, offsets).
* **Channel identity**: CME `config-2023-07-16.xml` channel **310** = "CME Globex Equity Futures",
  product `ES`, group `ES`, feed A 224.0.31.1:14310, feed B 224.0.32.1:15310. In-stream, all
  **497,636 entries carrying a SecurityID are channel-310 instruments** (0 off-channel), across
  **9 distinct ES SecurityIDs**; the secdef lists 37 instruments on channel 310.
  *Caveat:* template 30 `SecurityStatus` — the work order's suggested confirmation — **was not sent
  on this channel inside the window** (0 messages), so identity rests on the channel config, the
  per-instrument channel tag (1180=310), and the ES-group resolution of the decoded SecurityIDs.
* **Instrument identity (decoded, not inferred)**: `secdef-2023-07-17.dat.gz` (CME FIX tag=value,
  585,111 records) -> SecurityID **3445 = ESU3** (Sep 2023 front month), group `ES`, type `FUT`,
  CFI `FFIXSX`, maturity 202309, channel 310; 12 ES outrights + 20 ES calendar spreads.
  Activity: ESU3 408,395 messages / 18,104 trades; ESZ3 25,609 / 17; ESH4 1,005; spreads <= 204.
* **Price scale** (verified three ways, and a trap worth recording): `index_points =
  mantissa x 1e-9 x PriceDisplayFactor`; ES factor 0.01, so ESU3's wire mantissa is `points x 1e11`,
  not `x 1e9`. Evidence: (a) first quotes 4536.50/4536.75 bracket the instrument's own secdef
  settlement `453675.000000000` (2023-07-14) = 4536.75; (b) every observed ESU3 price lies on the
  0.25 tick grid at the settlement's tick offset and inside the secdef price band; (c) same-capture
  cross-check on other channels: ZN (factor 1.0) decodes to 113.1875 = its settlement, CL (factor
  0.01) to 73.67 = $73.67/bbl. Tick (0.25) and point value ($50) are taken from each instrument's
  own definition, not hardcoded.

## 3. Admission evidence

* **Sequence continuity**: per-feed series have gaps (A 19,511 / B 19,510) because each feed's
  capture is individually lossy, but the **deduplicated A/B union is dense**: 1,118,771 .. 1,501,663,
  count 382,893 = span, 0 gaps, 0 duplicates. Manifest carries a 64-row head and 64-row tail probe
  plus `sequence_count_total == last - first + 1`.
* **Ordering**: admitted-packet venue send times non-decreasing (0 violations); capture times
  non-decreasing (0 violations); 0 TransactTime regressions across the channel. Timestamp domain:
  capture 13:30:00.000444386Z..13:39:59.986885358Z; send 13:30:00.000424276Z..13:39:59.986864680Z;
  TransactTime 13:30:00.000020251Z..13:39:59.986777927Z.
* **Coverage**: 60,000 10 ms grid points; 59,999 carry a prevailing quote (1 point, the very first
  grid instant, precedes the first event); 59,999 have a quote updated within the preceding second.
  Ratio 0.99998 (tolerance 0.95).
* **Trade/book causal consistency**: of 18,122 trades, **18,017 (99.4%) print exactly at the
  aggressor's own side of the causally maintained BBO** and 0.39% (71) print outside it — 66 of
  those exactly one tick away, consistent with the matching book update following the trade summary
  inside the same packet (intra-event ordering), not with a book-maintenance fault. Other book
  invariants: 0 crossed/locked books after any change; 6,161 level-1 deletes of which 91 had no
  immediate level-1 replacement (compaction used, flagged `reconstructed`); 0 book resets.
* **BBO increments**: 312,358 rows (312,329 `direct_l1`, 29 `reconstructed`), 311,532 state changes
  from 399,843 book entries (Change 380,402 / Delete 6,680 / New 12,761; levels 1..10).
* Cross-check available but not relied on: template 47 (market-by-order) carries 62,145 entries and
  6,181 live order ids for 3 ES instruments — it is not used to rebuild the book because no snapshot
  exists for orders opened before the window.

## 4. Cost inputs (observed spreads; no outcome computed)

`spread_grid.csv` — 60,000 rows at 10 ms over [13:30:00Z, 13:40:00Z), ESU3, spread in ticks and
index points; `spread_distribution.json` — the distribution. Basis: **S = observed best ask - best
bid of the maintained MDP 3.0 market-by-price book at each grid instant**, converted with the
instrument's own display factor; **friction per round trip = 1/2 S_entry + 1/2 S_exit** in index
points — the half-spread paid on each leg relative to the midpoint. Ticks = S / (secdef
MinPriceIncrement x display factor).

| statistic | value |
|---|---|
| spread distribution (ticks) | 1: 58,832 | 2: 797 | 3: 187 | 4: 77 | 5: 17 | 6: 46 | 7: 7 | 8: 21 | 10: 12 | 11: 3 |
| mean spread | 0.2584 index points = **$12.92** (1 tick = $12.50) |
| mean half-spread (1/2 S) | 0.1292 index points = **$6.46** |
| quantiles (points) | p10/p25/p50/p75/p90 = 0.25, p99 = 0.5, max 2.75 |
| points per mantissa unit | 1.0e-11 (display factor 0.01) |

USD figures use the instrument's own ContractMultiplier (50). This is a cost input only; no
displacement, markout, or carry effect was measured anywhere in this epoch.

## 5. Artifacts

* `M2/src/mdp_es_normalize.py` (new) — subcommands `probe`, `stream`, `decode`, `secdef`,
  `manifest`, `verify-layout`. Reuse of existing engine: hashing via `M2/src/ingest.py`.
* `M2/data/raw/dc3-glbx-ab-dedup-20230717T133000.es-ch310.pcap` — ES channel-310 packet extract,
  66,692,366 B, sha256 `c938273d6a17…`: pcap records copied byte-for-byte (frames and timestamps
  unchanged), selected by destination port; validated independently with `tcpdump -r` -> 382,893
  packets, link-type EN10MB.
* `M2/data/raw/{secdef-2023-07-17.dat.gz, config-2023-07-16.xml, Cme.Futures.Mdp3.Sbe.v1.9.xml}` —
  retained, hash-pinned reference objects (identity, channel map, layout).
* `M2/data/derived_es/2023-07-17T133000Z/` — `trades.csv` (18,122 rows, sha256 `d3db3cd75e08…`),
  `bbo_increments.csv` (312,358 rows, sha256 `937b0557a916…`), `spread_grid.csv`,
  `spread_distribution.json`, `es_stream_stats.json` (full-series evidence),
  `acquisition.json`, `admission.json` (DATA_VALID).
* `M2/data/derived_es/` added to `.gitignore` (same policy as the other derived dirs). No commits;
  nothing frozen (`M2/experiments/*`, `M1/src/validate.py`, the hashed `M2/src` modules) was touched.

Reproduction:

```bash
# acquisition (streams the 6.8 GB object; hash + decode on the fly, no retention)
python3 -m M2.src.mdp_es_normalize stream \
  --url https://sample-pcaps-dl.databento.com/glbx-all/20230717/dc3-glbx-ab-dedup-20230717T133000.pcap.zst \
  --out-dir M2/data/derived_es/2023-07-17T133000Z --raw-dir M2/data/raw --work-dir M2/data/raw \
  --schema M2/data/raw/Cme.Futures.Mdp3.Sbe.v1.9.xml --chunk-bytes 4194304 --workers 32
# re-derivation from the retained extract (no network); byte-identical trades/book
python3 -m M2.src.mdp_es_normalize decode \
  --pcap M2/data/raw/dc3-glbx-ab-dedup-20230717T133000.es-ch310.pcap \
  --out-dir M2/data/derived_es/2023-07-17T133000Z --work-dir M2/data/raw \
  --raw-declared M2/data/raw/dc3-glbx-ab-dedup-20230717T133000.es-ch310.pcap
python3 -m M2.src.admission --manifest M2/data/derived_es/2023-07-17T133000Z/admission.json \
  --branch ES --root .
```

**Re-derivation determinism**: the trades and book CSVs produced by the one-pass 6.8 GB streaming
run and by the local re-derivation from the retained extract have identical SHA-256
(`d3db3cd75e08…`, `937b0557a916…`), and the extract itself was unchanged. The `stream` path was
additionally exercised end-to-end against a local range-capable server on a small object (probe ->
chunked fetch -> decode -> manifest, DATA_VALID).

## 6. Assumed vs observed (also machine-readable in `admission.json`)

Observed/decoded: pcap magic/link/precision; MDP packet and message framing; `schemaId=1,
version=9`; template ids, block lengths, group dims and field offsets (schema-verified); channel
310 -> ES group and its ports (CME config); SecurityID -> contract month (CME secdef); price scale,
tick and point value (secdef, cross-checked on ES/CL/ZN); sequence density; timestamps; spreads.

Assumed: (i) market-by-price level compaction on `MDUpdateAction=Delete` follows the standard CME
price-level convention — all action counts are reported so this is auditable, and the
trade-vs-BBO check bounds its effect at 0.39% of trades; (ii) that the capture's file span is the
named 10-minute window — enforced rather than assumed, since only packets whose decoded exchange
send time lies inside [13:30:00Z, 13:40:00Z) are admitted, and the out-of-window count is reported
(0 here: all 382,893 ES packets fall inside); (iii) that retained levels 1..10 suffice for BBO
(level-1 rows are present from the first event onward; 0 crossed books).

## 7. Limits and hand-off

* **Breadth**: one session, one 10-minute RTH-open window, one venue. Per the frozen formulation
  this sample can support at most a **sample-scoped development kill** for branch A
  (`TUP-CME-ES-H3-OFI-AGG`); a positive result would still be INDETERMINATE_COVERAGE. Nothing here
  claims otherwise, and no effect was measured.
* The manifest declares the 6.8 GB upstream object as a **non-retained** entry (url + full-object
  sha256 + byte count) and the retained extract as `raw_extract`; the admission engine records that
  the upstream digest is a producer assertion, not a disk-verified hash.
* Contract interaction: the ES contract's original `sequence_start = 1` pin was unsatisfiable for
  CME MDP3 (per-channel sequence persists across sessions); W4 extended the engine
  (`sequence_start_from_manifest`, bounded `sequence_probe`, `raw_extract` role,
  `allow_unretained_files`) without weakening any check, and the verdict is DATA_VALID.