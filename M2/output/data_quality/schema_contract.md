# Schema contract — Nasdaq TotalView-ITCH 5.0, binary, sample day 2019-07-30

Dataset: `NASDAQ-ITCH50-PUBLIC-SAMPLE-20190730`
Product: Nasdaq TotalView-ITCH 5.0 (binary), publicly hosted sample file
`07302019.NASDAQ_ITCH50.gz`, retrieved 2026-09-22 from
`https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/07302019.NASDAQ_ITCH50.gz`
SHA-256: recorded in `M2/data/manifests/raw_manifest.json`.
Payload bytes: 3,662,140,094 compressed; 8,661,679,413 decompressed; 282,229,684 framed messages.

Schemas: `ITCH50-BINARY-V50-20230428` (message layouts), plus one
**container-level property established empirically in this pass** (see 0.2).

Every statement below is either

* **[SPEC]** — transcribed from the provider document: *Nasdaq TotalView-ITCH 5.0*,
  published by Nasdaq, retrieved 2026-09-22 from
  `https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf`
  (revision log entry 2023-04-28); or
* **[EMPIRICAL]** — validated against the actual bytes of this dataset, with the
  measurement stated; or
* **[ABSENT]** — the field does not exist in this product. Nothing is assumed in
  its place.

---

## 0. Container

### 0.1 File ⇒ message stream **[SPEC + EMPIRICAL]**
The file is a gzip member containing a contiguous stream of ITCH messages.
Framing is verified by the decoder: the declared frame length must equal the
documented length for the message-type byte, and any trailing bytes that do not
form a complete frame raise an error.
**[EMPIRICAL]** `frames_verified = 282,229,684`, framing mismatches `0`,
trailing bytes `0`.

### 0.2 Two-byte big-endian length prefix **[EMPIRICAL]**
Every message is preceded by a 2-byte big-endian length equal to the message
length. The ITCH specification document describes message payloads only and does
not describe this prefix; the property was established by inspecting the raw
bytes (first frame: `00 0c` then the 12-byte System Event message) and then
verified across the whole tape by the framing check. Any consumer that reads this
file without stripping the prefix desynchronises on the first message.

### 0.3 No sequence number **[ABSENT]**
The payload carries no sequence number. **[SPEC]** Sequencing is a property of the
transport wrapper (SoupBinTCP / MoldUDP64), which is not part of a captured file.
Consequence: a sequence-gap audit cannot be performed on this product. The
"Tracking Number" field ("Nasdaq internal tracking number", **[SPEC]**) is audited
in `sequence_gap_audit.csv` strictly as a **substitute**, and is explicitly not
claimed to be a sequence contract.

### 0.4 No receive clock **[ABSENT]**
There is no receive timestamp. Consequence: an event-vs-receive latency audit and a
receive-before-event anomaly audit are **not computable** from this product; both
are recorded as not-applicable rather than estimated. Any statement about
participant-observed latency requires a different measurement.

### 0.5 No channel / publisher field **[ABSENT]**
There is no publisher or channel identity in the message payload, and the file is a
single sequenced stream. Consequence: cross-channel ordering ambiguity is
not-applicable to this dataset; ordering is file order only (see 0.6).

### 0.6 Canonical order **[EMPIRICAL]**
Canonical order for this pass is **file order**, with the as-of rule
`FILE_ORDER_LAST_MESSAGE_WITH_TS_LE_DECISION_TS` (frozen in the config): a decision
at time `T` uses the state produced by every message that (i) precedes it in file
order and (ii) carries a timestamp `<= T`. Out-of-order messages are counted and
never sorted away, and are never retro-applied to an already-emitted decision.
Measured on this tape: `timestamp_reversals = 0`, `identical_timestamp_runs =
3,858,123`, adjacent duplicate keys `748,799` (see
`M2/output/data_quality/timestamp_audit.csv` and `ordering_anomalies.csv`).

---

## 1. Data types **[SPEC]**
* All integer fields are big-endian, unsigned unless stated.
* Alpha fields are ASCII, left-justified, right-padded with spaces.
* Prices are integers with implied precision: `Price(4)` carries 4 implied
  decimals. Representation used downstream: raw integer, `TICK_RAW = 100` raw
  units per cent, `PRICE_SCALE = 10000`. No floating-point equality is applied to
  a price level anywhere in this pass.
* Timestamps: nanoseconds since midnight (6-byte field). Range observed:
  `10,970,642,174,571` (03:02:50.2) to `72,300,000,037,782` (20:05:00.0).
  **[EMPIRICAL]** the observed range is consistent with a single trading day.

## 2. Instrument identification **[SPEC + EMPIRICAL]**
* **Stock locate code**: 2-byte integer, dynamically assigned per day starting at 1,
  communicated by Stock Directory, constant intraday, not stable across days.
  **[EMPIRICAL]** 8,849 directory records; 8,849 distinct locate codes with
  directory messages; 8,849 distinct symbols.
* **Symbol**: 8-byte ASCII field in Stock Directory, Trading Action, Add Order,
  Trade, NOII and others.
* **Locate 0** is used for messages that are not stock dependent (System Event,
  MWCB). **[EMPIRICAL]** all 6 system events carry locate 0.
* **Order reference number**: 8-byte integer, "day-unique" **[SPEC]**. This pass
  treats a second Add with an existing reference as an anomaly and counts it
  (`order_id_collision`); it never silently overwrites.

## 3. Message inventory **[EMPIRICAL]**
| type | name | count | book-affecting |
|---|---|---|---|
| `A` | Add Order (no MPID) | 124,164,371 | yes |
| `F` | Add Order (MPID) | 1,296,379 | yes |
| `D` | Order Delete | 119,999,061 | yes |
| `U` | Order Replace | 21,253,951 | yes |
| `E` | Order Executed | 7,582,422 | yes |
| `X` | Order Cancel | 2,358,032 | yes |
| `C` | Order Executed With Price | 135,573 | yes |
| `P` | Trade (non-cross) | 1,461,010 | no **[SPEC]** |
| `Q` | Cross Trade | 17,700 | no (cross prints) |
| `B` | Broken Trade | 0 | no |
| `I` | NOII | 3,723,793 | no |
| `R` | Stock Directory | 8,849 | no |
| `H` | Stock Trading Action | 8,869 | no |
| `Y` | Reg SHO | 8,959 | no |
| `L` | Market Participant Position | 210,706 | no |
| `N` | Retail Price Improvement | 0 | no |
| `J` | LULD Auction Collar | 2 | no |
| `V` | MWCB Decline Level | 1 | no |
| `W` | MWCB Status | 0 | no |
| `K` | IPO Quoting Period Update | 0 | no |
| `O` | DLCR price discovery | 0 | no |
| `h` | Operational Halt | 0 | no |
| `S` | System Event | 6 | no |

System events observed: `O` (start of messages), `S`, `Q` (start of market hours),
`M` (end of market hours), `E`, `C` (end of messages) — the complete documented
daily set, which is evidence that the tape covers a whole trading day.

## 4. Action semantics actually used **[SPEC]**
* `A` / `F` — "a new order has been accepted by the Nasdaq system and was added to
  the displayable book". The two variants differ only in whether an MPID
  attribution field is present; both add displayable size at the stated price on
  the stated side. `B` = buy, `S` = sell.
* `E` — "sent whenever an order on the book is executed in whole or in part ...
  multiple Order Executed Messages on the same order are cumulative". Reduces the
  order's remaining displayed size at its **display price**.
* `C` — same as `E` but "executed ... at a price different from the initial display
  price". The order's displayed size decreases; its displayed level is unchanged.
  The `Printable` flag is recorded, not used for book state.
* `X` — "partial cancellation"; removes shares from the display size.
* `D` — "the order ... is being cancelled. All remaining shares are no longer
  accessible so the order must be removed from the book".
* `U` — cancel/replace: "all remaining shares from the original order are no longer
  accessible" and a new reference number takes over. Side, symbol and MPID are
  **not** repeated in the message and must be inherited from the original Add
  **[SPEC]** — this pass does exactly that.
* `P` — Trade (non-cross): "Trade Messages do not affect the book". Since
  2010-12-06 the Order Reference Number field is zero-filled, and since 2014-07-14
  the Buy/Sell field is always `B`. Excluded from book state, retained for
  off-book volume context only.
* `B` — Broken Trade: no impact on current book state; would only matter for
  time-and-sales. No such messages occur on this tape.

Anomalies a correct engine must therefore be able to see: an execution, cancel,
delete or replace whose reference number is not in the book ("orphan"), a cancel or
execution larger than the remaining size, a crossed or locked book, and a
replacement whose new reference already exists. All of them are counted per symbol
in `book_reconstruction_audit.csv`; none is repaired.

## 5. Stock Directory fields used for scope filtering **[SPEC + EMPIRICAL]**
* `Market Category` — `Q` Nasdaq Global Select, `G` Nasdaq Global Market, `S` Nasdaq
  Capital Market are Nasdaq-listed; `N` NYSE, `A` NYSE American, `P` NYSE Arca,
  `Z` BATS, `V` IEX are not.
* `Issue Classification` — allowed values are published in the specification's
  appendix; `C` is the ordinary common-stock class used by the development-scope
  filter.
* `ETP Flag` — `Y` denotes an exchange-traded product.
* `Authenticity` — `P` live/production, `T` test.
* `Round Lot Size` — **[EMPIRICAL]** 100 for the symbols inspected.
These are **not** the frozen universe rule's security-type screen (that rule also
excludes ADRs, preferreds, warrants, units and CEFs, which this single field does
not distinguish); they are a development-scope filter only, labelled as such.

## 6. Field semantics deliberately NOT established
* Whether Nasdaq's dissemination order equals its internal match order — a captured
  file cannot show this.
* Whether the tracking number is contiguous per feed or shared across feeds — it is
  documented only as an internal tracking number; the substitute audit reports the
  measurement without asserting a contract.
* Whether the sample file is byte-identical to the file Nasdaq distributed on
  2019-07-30: the vendor-published md5sum sibling returned HTTP 404 at access time,
  so no vendor checksum exists to compare against. The SHA-256 and md5 recorded in
  `raw_manifest.json` are this project's integrity record, computed at freeze time.
* Whether the sample day is representative of any other period. It is DEVELOPMENT
  data and no regime transfer is claimed.
