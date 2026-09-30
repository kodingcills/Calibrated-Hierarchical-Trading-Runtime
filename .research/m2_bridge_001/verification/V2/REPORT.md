# V2 — Adversarial verification of the W1 (auction) and W2 (ES) data admissions

Campaign `GOAL-M2-BRIDGE-001`. Verification wave **V2**, agent `V2DataVerification`.
Scope: the two admissions not previously verified — **W1** Nasdaq auction tape 2026-06-12 and
**W2** CME ES MDP 3.0 sample 2023-07-17T13:30:00Z.
Read-only on every producer artifact. No economics: no markout, displacement, carry or P&L.
No commit, no purchase, no credential, no re-stream of the 17.9 GB source.

## 0. Method and independence

| rule | how it was honoured |
|---|---|
| do not reuse the producer's code path | every number below comes from scripts in this directory that **import nothing** from `M2/src/itch_stream_window.py` or `M2/src/mdp_es_normalize.py` (the ES negative-control script imports only my own decoder) |
| re-derive from retained artifacts | W1 from `window.bin.gz` (760,167,921 B) only; W2 from the retained 66,692,366 B pcap extract + the retained secdef/schema/config reference objects |
| field offsets are not coded from memory | the ITCH 5.0 field tables were extracted from the in-repo spec PDF (`spec_text.txt`) and the SBE layouts were re-derived from `Cme.Futures.Mdp3.Sbe.v1.9.xml` at runtime (`layout_check.ok = true`, 22/22 checks) |
| negative controls | 8, on both sides (see §3) |
| scope limits | whole-tape (17.9 GB) totals are **not** re-derived; single-pass producer evidence only (SUPPORTED_SCOPED) |

### Scripts (sha256)

| script | sha256 |
|---|---|
| `v2_auction_scan.py` | `146ffe1cf383bea791c1cadce64b655d077a6da52021e0899e910561856ebb12` |
| `v2_auction_negative_controls.py` | `6051de611e004c45dd051b1dc3a9ce826716f193ea57152838502aeff19c5896` |
| `v2_auction_contract_attack.py` | `6d7b032c092ae2463e371664a2e54d52a6834057e357ec9001c1e96c52ba2f2e` |
| `v2_es_rederive.py` | `349b45255ffac9a6d486480f1ebdf85ed4bb3eba35087f85cd79f241d8bb2552` |
| `v2_es_causality.py` | `33908e82c70a3b8f6bd3eda4365efb9eb84c5eb7e42df5b9f2fece99ce2a2853` |
| `v2_es_negative_controls.py` | `20f1b0ce200c6b1388732886d9a886ef55bf02efa7a7bb82a28487cf1e431207` |

### Evidence files (sha256)

| file | sha256 |
|---|---|
| `v2_auction_scan.json` | `64397e7c2322eac2215cca0d2a647e3aac4a0bdbddc794b9969239314619ec13` |
| `v2_auction_negative_controls.json` | `89f1477bd940685bc46b48dd1a5a9635a02a06a103e56d9d2b97752f8b8fca78` |
| `v2_auction_contract_attack.json` | `e4c8a62637a978fa6593501424b45142de0e5bdc3c16f70046271f075771d3d8` |
| `v2_es_rederive.json` | `d1876db0605d0d9f21cf1761ecf9d5927ab64e35d67b1aef3f77c7cd4794e99b` |
| `v2_es_causality.json` | `32f3962596bda04256b60ee0a1a1c0e41035a50495d42f0143fb6761f59898ad` |
| `v2_es_negative_controls.json` | `e10c23b1d2223ae209f27b910cb2b3d1fe6c125f647387d7910eac76eb756666` |

Independent re-derivations retained for inspection: `rederived_trades.csv`,
`rederived_bbo_increments.csv`, `rederived_spread_grid.csv`.

---

## 1. Claim set A — W1 auction tape

| # | claim | verdict | independent evidence |
|---|---|---|---|
| A1 | declared sha256 + byte size of `window.bin.gz` | **VERIFIED** | re-hash `28ed7b973807fdbfd3558dfbd2fdc5e1580a0227860d0f129ff6c67091d59597`, 760,167,921 B — matches `admission.json:window_artifact_sha256` |
| A2 | window genuinely contains the frozen instants | **VERIFIED (on the window)** | own parse: first file frames `S,R,R,R…`; 12,809 Stock Directory in the 03:04:57.195–03:04:57.345 **spin** (outside the trading window, retained by design); 4,227,767 NOII `I`, **all Cross Type C**; 12,809 Cross Trade `Q`, **all Cross Type C**; NOII cadence first 15:50:00.000298551 → last 16:00:00.459966440; crosses 16:00:00.000315131–16:00:00.857985216; in-window frames **55,698,714**; retained frames **55,711,528** (= 55,698,714 + 12,809 R + 5 out-of-window S) |
| A2b | message-type histogram on the window | **VERIFIED** | my in-window histogram is **identical, key for key**, to `admission.json:message_type_histogram_window` (14 types, Σ 55,698,714) |
| A2c | I/Q/R totals (whole 17.9 GB tape) | **SUPPORTED_SCOPED** | producer's single pass attests NOII 6,044,629 / Cross Trade 25,686 / Directory 12,809. Not re-derived (source not re-streamed). The window values are independently confirmed; the whole-file values rest on one producer pass. |
| A3 | four-cell coverage matrix 0/17, 17/17, 0/2497, 2497/2497 | **VERIFIED** | my matrix reproduces **all six producer variants exactly**: (FROZEN, AT_OR_BEFORE) 0/17; (FROZEN, FROZEN_CONTRACT) 17/17; (CLASS_ONLY, AT_OR_BEFORE) 0/2497; (CLASS_ONLY, FROZEN_CONTRACT) 2497/2497; qualified 31 / 4,543; exclusion-reason counts identical |
| A4 | only 31 of 12,809 locates are Issue Classification `C` **and** Sub-Type `C`; what is the real common-stock sub-type | **VERIFIED** | own directory parse: `C/C = 31`, `C/Z = 4,183`; AAPL = classification `C`, sub-type `Z`, category `Q`, authenticity `P`, ETP `N`. Spec Appendix E: `C = Common Shares`, **`Z = Not Applicable`** → ordinary common stock carries sub-type `Z`, so the frozen clause admits 0.24 % of the directory |
| A5 | 8,528 of 12,809 cross prints are zero-shares *and* zero-price; zero population concentrated in N/A/P/Z | **VERIFIED (with scope)** | own parse: 8,528 zero-share of which **8,528 also zero-price**. Within the *universe-qualified* population: Q 4/1,149 · G 4/377 · S 10/957 zero vs N 1,791/1,819 · A 236/240 · Z 1/1 — i.e. ~99 % valid on Nasdaq-listed (Q/G/S) and ~1.6 % elsewhere. **Nuance:** across *all* 12,809 locates G and S also carry zero prints (932/2,391 and 290/1,670) because the non-common issues (ETPs, funds) are excluded by the classification/ETP clauses — the concentration statement is conditional on the universe filter, not on market category alone. Spec 1.5.2 confirms the mechanism ("may show the shares as zero") |
| A6 | the 2019 reference tape really ends with `C` and has no zero-length frame | **VERIFIED** | full local decompression of `07302019.NASDAQ_ITCH50.gz` (3,662,140,094 B → 8,661,679,413 B, gzip eof = true): last 12 decoded bytes `53 00 00 00 00 41 c1 a7 d1 cb 96 43` = length prefix 12, type `S`, category 0, Event Code `C`; 0 bytes after it; last 2 bytes ≠ `00 00`. Identical to the producer's quoted `d989000c530000000041c1a7d1cb9643` |
| A6b | is that "completeness contract" defensible? | **CONTESTED** (see §4) | the marker set passes on an artefact that contains **0.92 %** of the session. It is defensible as a *transport/structural* contract and is a **convenience relaxation** as a *session-completeness* contract |
| A7 | is the session DATE proven by tape content? | **INFERRED ONLY — not proven** | ITCH 5.0 messages carry nanoseconds-since-midnight and no trade date anywhere; the date comes from the object name `S061226-v50.txt.gz` and the provider index. The producer states this; the branch's "modern untouched session" claim therefore rests on filename provenance, not on tape content |
| A8 | ≥2 negative controls detect corruption | **VERIFIED** | NC1 truncation detected; NC2 byte flip detected; plus NC3/NC4/NC5/NC6/NC8 (§3) |

---

## 2. Claim set B — W2 ES admission

| # | claim | verdict | independent evidence |
|---|---|---|---|
| B9 | declared sha256 of the retained raw extract | **VERIFIED** | `c938273d6a17cd90b0f44b47a820f6567bb698ffbac50b6bc76052ae71b6c88e`, 66,692,366 B — matches `admission.json:files[role=raw_extract]` |
| B10 | `trades.csv` and `bbo_increments.csv` reproduce **byte-identically** | **VERIFIED** | my own pcap/IPv4/UDP/MDP-3.0/SBE decoder (layouts re-derived from the CME schema XML) emits `d3db3cd75e082196cac13c43f1220d117c1f9f2c98a0e49ec0559b22d183210e` (trades) and `937b0557a916cb30a3cae02753edff68604bcba59f9d1c76f07d0d0f176552e5` (book) — equal to both the on-disk files and the declared digests. `spread_grid.csv` is also byte-identical (`5f99dc16…`). 382,893 pcap records / 382,893 ES packets / 449,990 messages, **0 framing errors**, template mix 46:377,976 · 47:36,286 · 48:18,092 · 37:17,524 · 51:111 · 49:1 |
| B11 | spread distribution at 10 ms: 60,000 points / 59,999 quoted / 58,832 one-tick / mean 0.2584 / mean half 0.1292; friction = mean spread, not twice the half-spread of the mean | **VERIFIED (numbers) · CONTESTED (framing)** | recomputed independently: 60,000 grid points, 59,999 with a quote, 58,832 at one tick, mean spread **0.258446** pts ($12.92), mean half-spread **0.129223** pts, tick histogram {1:58,832 · 2:797 · 3:187 · 4:77 · 5:17 · 6:46 · 7:7 · 8:21 · 10:12 · 11:3}. The stated distinction is **vacuous**: `E[½S_entry + ½S_exit] = E[S]` and `2 × ½·mean(S) = mean(S)` are the same number by linearity — the equality is an identity, not evidence |
| B12 | 18,122 trades; aggressor B 9,009 / S 9,113; 99.4 % at the aggressor's own BBO side; price scale reproduces a settlement value | **VERIFIED** | my own replay: 18,122 trades, B 9,009 / S 9,113 (New 18,122); checked 18,122, **at own side 18,017 = 99.42 %**, outside 71 (66 exactly 1 tick, 4 at 2, 1 at 3) — identical to the producer's buckets; 0 crossed/locked books after any change. Scale: `mantissa × 1e-9 × PriceDisplayFactor` reproduces the secdef settlement for **4** instruments (ESU3 4536.75 · ESZ3 4586.25 · ESH4 4637.50 · ESM4-ESU4 43.00) and `multiplier × increment × factor = tick value 12.50` for all outrights |
| B13 | no lookahead; the 29 `reconstructed` L1 rows are justified, not silently imputed | **VERIFIED (with a caveat)** | every row satisfies `ts_event ≤ exchange_send ≤ ts_recv` (0 violations, both files); 0 sequence / ts_event / ts_recv regressions in `bbo_increments.csv`; 0 TransactTime regressions over trades; 0 capture-time and 0 send-time regressions over the pcap. An artefact-only replay (BBO rebuilt **only** from rows with a strictly smaller sequence) finds 18,035/18,104 prints inside-or-at the prevailing BBO — the same picture as the producer's streaming check, which is what a leak-free pipeline looks like. The 29 rows are explicitly flagged `reconstructed` in the CSV (a consumer can filter them), are emitted only where level 1 is absent but deeper levels exist, and take their price from a level **already received** — no future or imputed price. **Caveat:** the retained increment file alone cannot exactly reproduce the producer's runtime classification (artefact-only own-side 17,764/18,104 = 98.1 % vs 18,017/18,122), because the runtime check uses intra-packet book state; the 99.4 % figure is reproducible only by re-decoding the raw extract |
| B14 | what the 10-minute single window cannot support | **VERIFIED (statement)** | see §5 |

---

## 3. Negative controls (deliberately corrupted inputs that MUST be detected)

| id | control | result |
|---|---|---|
| NC1 | `window.bin.gz` truncated to 50 % | **detected** — sha differs from declared; gzip eof = false; parsed 906,717,081 B then "truncated frame" |
| NC2 | one payload byte flipped mid-file | **detected** — sha `2cb8deaa…` ≠ declared; zlib raises "incorrect data check" (gzip CRC32 fails) |
| NC3 | synthetic `00 00` terminator appended to a frame-aligned decode prefix | **detected** — terminator counter flips 0 → 1 (proves the detector is not blind; the pristine window reports 0) |
| NC4 | 1,000-byte slice deleted mid-file (frame-unaligned) | **detected** — framing error "unknown type 0x2a" |
| NC5 | one byte flipped in the ES pcap extract | **detected** — sha ≠ declared; message count 449,990 → 449,989. *Honest limit:* the single-byte corruption did **not** break MDP framing on its own, which is precisely why the sha256/Content-Range chain and the gzip CRC matter |
| NC6 | ES pcap extract truncated to 50 % | **detected** — 29 trailing bytes that are not a complete pcap record |
| NC7 | positive control: pristine extract | 449,990 messages / 18,122 trades, no framing error — matches the producer |
| NC8 | **spliced tape**: first 8 MiB + last 8 MiB of the decoded window, cut on frame boundaries, terminal `C` kept, re-gzipped (0.92 % of the session) | **NOT detected by the declared contract** — gzip CRC32/ISIZE pass, 0 framing errors, 0 trailing bytes, terminal `C` is the last frame ⇒ contract PASS. Only an unrequested heuristic reveals it: a **22,790 s** inter-frame timestamp jump. See §4 |

---

## 4. Item 6 — is the contract a completeness contract? (the strongest attack)

The declared marker set is

```
gzip CRC32+ISIZE PASS · received == Content-Range · 0 framing errors
· 0 trailing bytes · terminal 'C' End-of-Messages is the last frame
```

**What it does certify** (transport/structural integrity of the delivered object): the object arrived
whole at the HTTP layer, decompresses cleanly, every length prefix equals its documented message
length, nothing follows the final message, and the session is closed by the spec-defined last message.
Given that ITCH 5.0 carries no sequence number and Nasdaq publishes no per-day message count or
checksum, this is close to the strongest statement obtainable from the artefact alone.

**What it does NOT catch** (each is a real, reachable failure mode):

1. **Internal loss.** A hole that begins and ends on frame boundaries — provider capture drop, a
   truncated range fetch that is then spliced, a partial re-download — leaves every marker green.
   **Demonstrated**: NC8 keeps 0.92 % of the session and passes the whole marker set. The only tell,
   a 22,790 s timestamp jump, is not part of the contract.
2. **Wrong object.** A different session's file, or a same-name file from another source, satisfies
   every marker. Nothing binds the bytes to the session date (item A7) or to the provider (ETag /
   Last-Modified are recorded but not part of the verdict).
3. **Partial trading day.** A file that legitimately begins after the opening spin, or lacks the
   `O/S/Q/M/E` session events, passes: the contract checks only that the **last** frame is `C`.
4. **Provider-side completeness.** `received == Content-Range` and the gzip trailer merely restate
   "what the server sent arrives intact"; neither can attest that the server's object is the true
   exchange record. A server-side truncation that happens to land on a frame boundary is invisible
   unless it cuts away the terminal `C`.
5. **The terminator clause itself.** "Terminator absent" is now unfalsifiable for this feed
   format: both ITCH captures available in this repo (2026-06-12 and the 2019-07-30 reference)
   lack it (n = 2, both independently decompressed here). The relaxation is empirically motivated
   but cannot be distinguished from a loss event by this artefact.

**Judgment:** the marker set is a defensible **transport/structural** contract and a **convenience
relaxation** with respect to the frozen BinaryFILE clause; calling it `session.completeness` (as W4's
engine does) overstates it, because it cannot detect internal loss or wrong-object delivery. Two
concrete improvements: (i) add the session-event sequence (`O→S→Q→M→E→C` present, ordered) and a
timestamp-continuity bound; (ii) rename the check to `transport_integrity` and record
`internal_loss_undetectable: true` so the campaign does not read a PASS as "the session is all there".
Also note the consequence already found by W1: pinning `require_terminating_frame: true` rejects
**both** ITCH captures available in this repo, so that clause is not a data-quality signal at all.

---

## 5. Item B14 — what the 10-minute single window cannot support

The sample is one venue (CME Globex), one channel (310), one instrument (ESU3), one 10-minute
opening window, one session. Therefore it cannot support anything beyond a **sample-scoped
development kill** for branch A:

* no session-level or regime-level inference, no breadth across products/days;
* the dedup A/B union is dense (382,893 = span, 0 gaps) but that is a *union*: feed A alone has
  19,511 gap events and feed B 19,510, and **a message lost on both feeds simultaneously is
  invisible** to deduplication — the union is a lower bound on the venue's stream, not proof of it;
* the book is rebuilt from in-window increments only (no snapshot): 91 level-1 deletes had no
  immediate replacement and 28 recomputations ended with a missing L1, so the maintained book is
  demonstrably incomplete at the edges; the market-by-price level-compaction rule is an
  **assumption** (CME's own documentation is not in the repo) that the 0.39 % outside-BBO tail
  bounds but does not eliminate;
* instrument identity rests on the channel config + secdef, not on an in-stream `SecurityStatus`
  (0 messages on this channel in-window), so a mis-mapped SecurityID would not be caught by the tape;
* the spread distribution is a cost input, not an outcome; no markout/P&L exists in it, and the
  "friction = mean spread" arithmetic is an identity (§B11), so it cannot discriminate models;
* nothing here can turn a positive result into anything other than INDETERMINATE_COVERAGE.

---

## 6. Most decision-relevant finding

**The frozen candidate rule is degenerate on this session as literally written.** The literal
selection `Issue Sub-Type = C` admits 31/12,809 locates and the literal "at/before 15:50" read finds
**0** reads for every symbol (the first Closing-Cross NOII read is published 0.3 µs *after* the
boundary), so the frozen configuration scores **0/17 = 0.00** against a 0.95 tolerance. Full coverage
(1.00) exists only after **two** rule amendments — drop the sub-type clause and add the boundary
fallback — which are exactly the amendments the freeze was meant to preclude. Any evidence this
branch produces is therefore conditioned on a post-freeze rule change, and the bridge cannot be
certified as a test of the frozen rule. The expected `C/C` pair is also a spec-reading error:
per Appendix E, `C` means "Common Shares" while ordinary common stock is published as `C/Z`
(`Z = Not Applicable`) — the repo's own `universe_proxy.py` never constrains the sub-type, so the
producer's Defect-1 diagnosis is corroborated by the specification itself.

Second-order but campaign-wide: the W1 "completeness" contract passes an artefact containing 0.92 %
of the session (NC8), so a PASS from W4's engine must not be read as "no data is missing".