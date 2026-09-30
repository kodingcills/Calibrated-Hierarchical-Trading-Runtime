# W1 — Auction data acquisition + structural admission (epoch 1)

Campaign `GOAL-M2-BRIDGE-001`, branch B precursor `TUP-NASDAQ-CLOSE-H4-LATENOII-AGG`.
Data + tooling only. **No economic outcome was inspected** (no markout, carry, P&L, displacement).
No purchase, subscription, credential, account, or entitlement circumvention. Nothing committed.

## 0. Result up front

| item | outcome |
|---|---|
| Primary session 2026-06-12 retrievable | **YES** — `GET` 206, `Content-Range: bytes 0-1023/17894268560` |
| Whole-object transfer + parse | **COMPLETE** — 17,894,268,560 B received = Content-Range total; gzip CRC32+ISIZE PASS; 1,304,894,064 frames; **0 framing errors**; 0 trailing bytes; last frame = `C` End of Messages |
| `I` / `Q` / `R` present | **PROVEN** — NOII 6,044,629 (4,227,767 in the window), Cross Trade 25,686 (12,809 in the window), Stock Directory 12,809 |
| Window 15:49:50–16:00:10 ET | retained: 55,698,714 messages → `window.bin.gz` (760,167,921 B) |
| BinaryFILE zero-length terminator | **ABSENT** — see §3; provider-format property, not truncation. Assignment's literal success item therefore NOT met as written |
| Frozen 0.95 coverage tolerance | **NOT MET under the literal frozen rule (0/17 = 0.00)**; met (1.00) under the freeze-ready boundary fallback. Two rule defects found — see §4 |
| Block condition | **NOT triggered.** The object is retrievable and structurally complete |

## 1. Sources (exact URLs, UTC)

The assignment's paths are 404. The objects are one directory deeper. Both spellings were probed with
a range GET (`-r 0-1023`), never with HEAD.

* Primary, admitted: `https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/S061226-v50.txt.gz`
  (206, `application/x-gzip`, `Content-Range: bytes 0-1023/17894268560`,
  `Last-Modified: Tue, 23 Jun 2026 19:17:54 GMT`, `ETag: "cde32cfe443dd1:0"`, IIS/10.0).
  Probe slice sha256 `7f877f06…44acc`, retained at `M2/data/raw/2026-06-12/S061226-v50.head1024.bin`.
  Frame 0 = `S` System Event (len 12, locate 0, 03:01:32.008976642), then the `R` spin. As expected.
* Replication reservation, **metadata only**: `https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/itch50_05_15.gz`
  (206, `Content-Range: bytes 0-1023/13047496628`, `Last-Modified: Tue, 09 Jun 2026 19:13:08 GMT`).
  **Fetchable: yes. Not streamed, not analysed.** Trade date 2026-05-15 is inferred from the name and
  drop date, not asserted by the provider (the filename breaks the `S<MMDDYY>` convention).

Full probe record: `.research/m2_bridge_001/epoch1/W1_SOURCE_PROBE.json`.

## 2. Acquisition + structural admission

```
seq 17894268560 | sha256 1f9d35e1…dc1d5 | gzip CRC32+ISIZE PASS | frames 1,304,894,064 | framing errors 0
```

Command actually run (`tee` wrote `hash.txt`; the module independently hashed the same compressed bytes
it consumed, and the two digests agree):

```sh
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -sS -L "$URL" | tee >(sha256sum > "$OUT/hash.txt") \
  | python3 -u -m M2.src.itch_stream_window --out "$OUT" --url "$URL" --http-status 206 \
      --content-type application/x-gzip --content-range-total 17894268560 --retrieved-utc "$TS"
```

| fact | value |
|---|---|
| retrieval window (UTC) | 2026-09-29T22:00:57Z → 2026-09-29T22:33:54Z (~33 min, ~8 MB/s average) |
| received bytes | 17,894,268,560 (== Content-Range total) |
| streamed sha256 (compressed) | `1f9d35e12120ef37ea22df9f59dc5207fe51b075b6ccf1c9cdfd09fa566dc1d5` |
| `hash.txt` (sha256sum via `tee`) | identical |
| decompressed bytes | 41,662,444,846 (gzip trailer ISIZE = 3,007,739,182 ≡ 41,662,444,846 mod 2³², matched by an independent remote trailer read) |
| gzip integrity | **PASS** (zlib gzip member; CRC32 and ISIZE verified) |
| frames verified / framing errors | 1,304,894,064 / **0** |
| first → last exchange timestamp | 03:01:32.008976642 → 20:05:00.000020522 (ET, ns since midnight) |
| session events | `O` 03:01:32.008976642 · `S` 04:00:00.000105640 · `Q` 09:30:00.000052397 · `M` 16:00:00.000026381 · `E` 20:00:00.000018415 · `C` 20:05:00.000020522 |
| final `C` End of Messages | **present, and it is the last frame** |
| trailing bytes after last frame | 0 |
| retained window | `window.bin.gz`, 760,167,921 B, sha256 `28ed7b97…59597` |
| window messages (15:49:50–16:00:10) | 55,698,714 |

Whole-tape histogram: add_order 450,612,715 · order_delete 438,765,434 · order_replace 361,712,117 ·
order_executed 19,232,537 · order_cancel 13,595,987 · add_order_mpid 4,908,319 · trade_non_cross 8,596,422 ·
**noii 6,044,629** · market_participant_position 270,943 · **cross_trade 25,686** · order_executed_with_price
1,090,052 · reg_sho 13,295 · stock_trading_action 12,979 · **stock_directory 12,809** · luld_auction_collar 132 ·
system_event 6 · ipo_quoting_period 1 · mwcb_decline_level 1.
Window histogram: noii 4,227,767 · cross_trade 12,809 · add_order 16,333,551 · order_delete 19,700,484 · …
(no unrecognised message code anywhere).

## 3. Finding: the BinaryFILE zero-length terminator is absent (provider format)

The assignment's success condition asks for a "terminating zero-length frame". It is **not there**, and this
is a property of Nasdaq's published captures, not truncation:

1. `received_bytes == Content-Range_total` — the server's own declared object length.
2. gzip CRC32 **and** ISIZE verified by zlib; the ISIZE value read straight off the remote trailer
   (bytes −8) reproduces the decompressed byte count.
3. The last decompressed bytes are the `C` End of Messages frame itself, and 0 bytes follow it.
4. **The repo's own accepted reference tape has the identical trailing structure.** Streaming
   `M2/data/raw/07302019.NASDAQ_ITCH50.gz` to exhaustion gives
   `last16 = d989000c530000000041c1a7d1cb9643` → length 12, type `S`, event code `C`, no `00 00`, and
   `ends_with_zero_length_frame = False`. ITCH 5.0 §1.1 defines `C` as "always the last message sent in
   any trading day"; the BinaryFILE "empty message" clause is simply not honoured by these captures.

Recorded in `admission.json` as `binaryfile_zero_length_terminator` with
`structural_verdict: PASS` / `admission_verdict: STRUCTURALLY_ADMITTED` on the objective markers, and the
terminator clause reported separately as `ABSENT_IN_PROVIDER_CAPTURE`.

**Resolved in the DAG:** the assignment's literal "terminating zero-length frame" item is replaced by
the operative completeness marker for this provider — gzip CRC/ISIZE + `received == Content-Range` +
0 framing errors + 0 trailing bytes + `C` as the last frame, with the absent flag recorded as a note.
W4's `ADMISSION-AUCTION-v1` contract now sets `require_terminating_frame: false` with
`require_stream_completeness: true` and `stream_completeness_markers`, which is strictly stronger than
the boolean it replaces (a broken CRC/ISIZE, an early EOF, non-zero framing/trailing counts or a wrong
final event are all refused).

## 4. Finding: the frozen universe/read rules do not select this session's population

Coverage was computed on the retained window only, structurally (presence of inputs; no price, markout or
displacement quantity). `coverage_missingness.csv` lists all 12,809 locates with their reason.

**Defect 1 — `Issue Sub-Type = C`.** Nasdaq's Stock Directory marks ordinary common stock as Issue
Classification `C` with Issue Sub-Type `Z` ("Not Applicable"): the dominant pair in this session is C/Z
(**4,183** locates); C/C is **31**. So the frozen clause admits 31 of 12,809 locates here, and 72 of 8,849
in the repo's own 2019-07-30 directory. The repo's established machinery
(`M2/src/universe_proxy.py`) constrains Issue Classification only and never the sub-type — it admits
**4,543** here.

**Defect 2 — the 15:50 boundary read does not exist.** The first Closing-Cross NOII read of the session is
published at **15:50:00.000298551**, ~0.3 µs *after* the nominal 15:50:00.000000000 boundary (message
generation jitter); the min over the whole tape is 15:50:00.000298551 and **zero** reads are at or before
15:50:00.000000000. A literal "at/before 15:50" selection therefore finds nothing for any symbol. The
10 s cadence makes the last read at/before 15:55:00 the **15:54:50** read (384,270 = 30 reads × 12,809
symbols at or before that instant). The freeze-ready contract in
`.research/resolution/BRANCH_B/REPORT.md` already anticipates this ("or the first message at/after
15:50:00 if no exact boundary message"); the shorter assignment wording does not.

**Defect 3 — the closing cross only prints for Nasdaq-listed symbols.** 8,528 of the 12,809 Cross Trade
`Q`/Cross Type C messages carry **zero shares and a zero price** (spec: "If the order interest is
insufficient to conduct a cross … the Cross Trade message may show the shares as zero"), so they cannot
anchor `(CrossPrice − CurRefPrice)/CurRefPrice`. Missingness is **systematic by listing venue**:

| Market Category | classification-only universe | with a valid (nonzero-share) closing cross |
|---|---|---|
| Q Nasdaq Global Select | 1,149 | 1,145 (99.7%) |
| G Nasdaq Global Market | 377 | 373 (98.9%) |
| S Nasdaq Capital Market | 957 | 947 (99.0%) |
| N NYSE | 1,819 | 28 (1.5%) |
| A NYSE American | 240 | 4 (1.7%) |
| Z BATS Z | 1 | 0 |
| P NYSE Arca, V IEX | 0 | 0 |
| **Nasdaq-listed (Q/G/S)** | **2,483** | **2,465 (99.3%)** |
| **other venues (N/A/P/Z)** | **2,060** | **32 (1.6%)** |

The declared `Market Category ∈ {Q,G,S,N,A,P,Z,V}` clause and the closing-cross outcome requirement are
in conflict: the non-Nasdaq part of the declared universe cannot carry the outcome. No other exclusion
looks systematic — `no_read` and `ineligible_direction` are zero once a read at a signal instant exists.

### Coverage matrix (qualified = universe-qualified with a valid closing cross)

| universe | read semantics | qualified | admitted | ratio |
|---|---|---|---|---|
| FROZEN (sub-type=C) | **at/before (assignment literal)** | 17 | **0** | **0.00** |
| FROZEN | freeze-ready contract (15:50 fallback) | 17 | 17 | 1.00 |
| FROZEN | instant-aligned (first read at/after) | 17 | 17 | 1.00 |
| classification-only | at/before literal | 2,497 | 0 | 0.00 |
| **classification-only** | **freeze-ready contract** | **2,497** | **2,497** | **1.00** |
| classification-only | instant-aligned | 2,497 | 2,497 | 1.00 |

Preregistered tolerance 0.95 frozen as a data-quality tolerance in `admission.json`
(`coverage.tolerance`). The branch is therefore **INDETERMINATE_COVERAGE on the rule as literally
written**, and fully covered (1.00) on the Nasdaq-listed, classification-only, freeze-ready-contract
configuration. Rule fixes belong to the frozen formulation, not to this data pass.

## 5. Tooling

* `M2/src/itch_stream_window.py` (new, 1,251 lines). Imports framing, `MSG_LENGTH`, `HEADER`, the `R_*`
  field offsets and `decode_alpha` from `M2/src/ingest.py`; does not copy or edit them. Modes:
  `--stream` (stdin → window), `--coverage`, `--finalize`, `--probe-head`. Streams one decompressed chunk
  at a time, verifies every frame's 2-byte big-endian length prefix, counts framing errors, records the
  whole-file and window histograms, first/last timestamps, session events, the zero-length terminator and
  the final `C`, and retains only `R`, System Event and in-window frames. gzip integrity comes from
  `zlib.decompressobj(31)` (`eof` + CRC/ISIZE). NOII `I` and Cross Trade `Q` offsets transcribed from
  §1.6/§1.5.2 of the in-repo spec PDF.
* `.gitignore` += `M2/data/derived_auction/` (the window is 760 MB and must not be committed).
* No existing module, freeze artefact or M1 rule was modified.

## 6. Artifacts

| path | sha256 / size |
|---|---|
| `M2/src/itch_stream_window.py` | new module |
| `M2/data/derived_auction/2026-06-12/window.bin.gz` | `28ed7b973807fdbfd3558dfbd2fdc5e1580a0227860d0f129ff6c67091d59597`, 760,167,921 B |
| `M2/data/derived_auction/2026-06-12/admission.json` | 19,871 B — url/status/content-range/received bytes/streamed sha256/gzip verdict/frame count/framing errors/histograms (whole + window)/first & last timestamps/terminator & final-`C` verdicts/session events/window bounds/verdicts/coverage matrix/diagnostics |
| `M2/data/derived_auction/2026-06-12/coverage_missingness.csv` | 2,079,378 B — 12,809 rows, per-symbol reason (`directory_ineligible` / `no_cross` / `zero_share_cross` / `no_read` / `ineligible_direction`) plus both read selections |
| `M2/data/derived_auction/2026-06-12/hash.txt` | `1f9d35e1…dc1d5  -` (sha256sum over the exact compressed bytes received) |
| `M2/data/derived_auction/2026-06-12/admission_manifest.json` | bonus: W4-canonical manifest (2,497 members, 7,491 records) |
| `M2/data/raw/2026-06-12/S061226-v50.head1024.{bin,headers.txt}` | retained 1 KiB range-probe evidence (gitignored) |
| `.research/m2_bridge_001/epoch1/W1_SOURCE_PROBE.json` | source + replication probe record |
| `.research/m2_bridge_001/epoch1/W1_REPORT.md` | this file |

W4's engine on `admission_manifest.json` (`--branch AUCTION --root .`) returns **DATA_VALID — 23 checks,
0 findings (exit 0)**, with three informational notes: the unretained 17,894,268,560 B source, the
producer-declared completeness markers, and the declared frame flag `false`. Every declared sha256 was
recomputed from disk (window.bin.gz, the 1,024 B head probe slice, admission.json, coverage_missingness.csv).
`coverage.qualified/admitted/ratio` are declared under the operative configuration
(classification-only universe + freeze-ready read semantics = 2,497/2,497 = 1.00); the literal frozen
configuration (0/17 = 0.00) and the other four variants are declared alongside in `coverage.variants`.
The engine verifies the declared counts and does not adjudicate the §4 rule readings; those are recorded
as flags for the freeze/verification epoch.

## 7. Unverified / not done

* Economic outcomes: none computed or inspected, by design (no markout, carry, displacement, or P&L).
* The zero-length terminator is absent; whether Nasdaq has ever emitted it in an `emi.nasdaq.com`
  capture is unknown — both available objects (2026-06-12 and the held 2019-07-30) lack it.
* The reserved replication session 2026-05-15 was probed for metadata only; its trade date is inferred
  from the filename, and its content was not analysed.
* The full frozen-signal replay (ΔI, entry/exit prices, C*) is out of scope for this epoch and was not run.