# W3 — BRANCH C AVAILABILITY WINDOW + 100% HOURLY PAIRING ADMISSION

**Ticket:** GOAL-M2-BRIDGE-001 Epoch 1, worker W3. Data/availability only — no carry, no P&L, no
funding-differential magnitude, no fees, no freeze sealing. All work uncommitted.

## 1. Verdict

**PAIRED_100PCT over a contiguous 4,981-hour window: 2026-03-05T11:00:00Z → 2026-09-28T23:00:00Z.
expected_buckets = 4,981, matched = 4,981, missing = 0, duplicates = 0.** Not an
EXTERNAL_DATA_BLOCK; every required field has a free, anonymous, no-auth path.

Independent admission by the sibling engine (not my own code):
`python3 -m M2.src.admission --manifest M2/data/derived_basis/manifest_basis.json --branch BASIS --root .`
→ **DATA_VALID**, contract ADMISSION-BASIS-C-v1, zero INVALID and zero INCOMPLETE findings
(saved: `M2/data/derived_basis/manifest_engine_verdict.json`; same verdict recorded inside
`admission.json` / `FREEZE_INPUT_basis.json`). A second, separately written throwaway script
(`/tmp/verify_basis_pairing.py`, not imported from `M2/src/basis_admission.py`) re-extracted all four
fields straight from the cached raw payloads and reproduced 4,981/4,981 rows with 0 grid gaps,
0 duplicate hours, 0 value mismatches and matching hashes.

## 2. Required fields and per-source availability (hour buckets, [H, H+1h) UTC)

| Source / field | Earliest | Latest | Hours |
|---|---|---|---|
| HL `fundingRate` (+ `premium`) — uniform hourly era | 2023-06-25T12:00Z | 2026-09-29T22:00Z | 28,616 era hours |
| HL 1h candle close (`hl_mid`) — rolling ~5000-candle cap | 2026-03-05T11:00Z | 2026-09-29T21:00Z | 5,003 |
| Binance `markPriceKlines` 1h close | 2026-03-01T00:00Z | 2026-09-28T23:00Z | 5,088 loaded |
| Binance `klines` 1h close | 2026-03-01T00:00Z | 2026-09-28T23:00Z | 5,088 loaded |
| *aux* Binance `fundingRate` settlements (8-hourly) | 2026-03-01T00:00Z | 2026-08-31T16:00Z | 552 |

- **Binding start = HL 1h candle horizon** (the free `candleSnapshot` returns only the most recent
  5,003 candles; nothing older is reachable free). **Binding end = Binance archive lag** (the latest
  daily file pair present is 2026-09-28; the 2026-09 monthly file is not published yet). No month
  chosen by preference.
- Binance archive floor probed: monthly `klines`/`markPriceKlines` 2020-01 → HTTP 206, 2019-12 → 404.
- HL funding published history begins 2023-05-12T00:00Z, but it is **8-hourly before
  2023-06-25T12:00Z** (probe window rows 11:00 then 12:00,13:00,…); only the hourly era is a valid
  uniform grid.

## 3. Pairing repair (the point of this epoch)

Rule: `bucket = ts_ms // 3_600_000` (floor to the exact UTC hour) with exact 1:1 matching; a source
contributes at most one value per bucket; duplicates and missing buckets are reported, never imputed.
Why it matters: HL funding `time` carries sub-second settlement jitter — **in-window offsets 0.000 s
to 0.261 s, 4,915/4,981 rows non-zero**. Exact-millisecond equality silently drops those rows. Every
in-window settlement lies inside its own UTC hour (0 rows with offset > 1 s), so flooring can never
move a row across a bucket boundary. Whole-history max offset is 1433.04 s (one 8h-era row,
2023-05-23T08:23Z) with only 5 rows > 60 s, none inside the window.

**Prior failure explained, not excused.** Across the entire hourly era (2023-06-25T12:00Z → now,
28,619 expected hours) exactly **3 settlements are absent** — 2023-07-02T20:00Z, 2023-08-23T20:00Z,
2024-08-15T13:00Z (neighbours present with normal offsets) — and **none of them is inside the
admitted window**. So the earlier "expected 2, observed 1" was a timestamp/bucket artifact of the
un-repaired rule, not a systemic source gap. The specific prior 2-hour window was not re-identified.

## 4. Binance archive defect check (step 6)

Every monthly file used was row-count-validated against its expected hour grid (header verified
against the 12-column kline schema): `klines` 2026-03…2026-08 all exactly 744/720/744/720/744/744 ✓.
`markPriceKlines` 2026-06 came back **696/720 — exactly the whole of 2026-06-29 absent**, all other
months exact. Repair: daily file `markPriceKlines/BTCUSDT/1h/BTCUSDT-1h-2026-06-29.zip` (24 rows,
sha256 122fd96f…4068) filled all 24 hours. September (monthly not yet published) is loaded from
**56 daily files** (2026-09-01…2026-09-28 × 2 series), every one 24/24 rows. Files actually used and
their hashes are enumerated in `admission.json → binance_file_validation` (75 archive objects).

## 5. Provenance

- Retrieval timestamps: 2026-09-29T21:59:35Z → 2026-09-29T22:09:06Z (then reused from cache).
- 144 requests total (61 api.hyperliquid.xyz, 83 data.binance.vision), 136 served from cache;
  HL funding paged 59× at 500 rows/request. Full request log with status/bytes/sha256 in
  `admission.json → request_summary`.
- All Binance monthly/daily zips: sha256 + bytes + HTTP status + retrieval time per file.
  HL API responses: raw sha256 **and** canonical (sorted-key) sha256 per page.
- Cross-check against the saved prior probe artefact `probe_c_join_2026-06_2026-08.csv`: 276/276
  rows inside the window, **0 value mismatches** on all five shared fields.
- Bucket arithmetic matches the engine's inclusive form: mine
  `len(range(start_ms, end_ms+3600000, 3600000)) = (end_ms-start_ms)//3600000 + 1` == the engine's
  `int((end-start)//3600)+1` == 4,981. A definitional mismatch here would void the claim; there is none.

## 6. Auxiliary window (reported, not the verdict)

If the *Binance funding settlement* series is treated as required (free archive lags ~1 month: last
row 2026-08-31T16:00Z; USD-M has no daily fundingRate directory; the 451 host is environment-only),
the intersection becomes **2026-03-05T11:00Z → 2026-08-31T16:00Z = 4,302 hours, 4,302/4,302 matched,
0 missing, 538 settlements inside**. Both windows are pure data facts; the frozen formulation's
state (HL fundingRate + HL mid / Binance mark − 1) needs no Binance funding, hence the primary call.

## 7. Caveats owned elsewhere

HL "mid" here is the 1h **candle close** (the only free historical HL price series) — whether that
satisfies the freeze's "no mid falls back to last trade" kill rule is a formulation question for the
main agent, not a data-availability one. HL historical **oracle** price remains free-path-absent
(requester-pays S3); it is not required by this leg's state. Binance fee arithmetic is explicitly a
separate workstream.

## 8. Artefacts

| Path | sha256 |
|---|---|
| M2/src/basis_admission.py (new module) | — |
| M2/data/derived_basis/paired_hours.csv (4,981 rows) | c95ac782…b562a3 |
| M2/data/derived_basis/admission.json | 6bc587b5…12dfd4 |
| M2/data/derived_basis/FREEZE_INPUT_basis.json | 0e7a5011…43295c |
| M2/data/derived_basis/manifest_basis.json (W4-canonical) | 7544020a…412d874d |
| M2/data/derived_basis/manifest_engine_verdict.json | DATA_VALID, 23 checks, no findings |
| manifest_inputs/{hl_funding_hourly,hl_mid_1h_close,binance_mark_1h_close}.csv | declared in the manifest, recomputed by the engine |

W4's engine owner separately re-ran the same manifest read-only and got DATA_VALID / 0 findings at
22:10Z, hashing the three role files from disk (recorded in epoch1/W4_REPORT.md). `manifest_basis.json`
carries `source.retrieved_at_utc`, so re-running changes its sha256 while every checked property stays
identical; the hash above is the post-cleanup instance on disk.

Raw bytes cached (gitignored) under `M2/data/raw/basis/` (4.9 MB). No freeze sealed, nothing written
under `M2/experiments/`, no existing frozen artefact touched. One shared-file edit: `.gitignore` gained
`M2/data/derived_basis/` (same policy line style as the other `derived_*` dirs) so the 1.5 MB of
admission artefacts stay uncommitted.

Reproduce: `python3 M2/src/basis_admission.py` (add `--refresh` to re-fetch) then the engine CLI in §1.