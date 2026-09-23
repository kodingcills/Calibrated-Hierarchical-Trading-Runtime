# M2-0 data acquisition plan

Status: **NO PURCHASE AUTHORIZED OR MADE.** This document exists so that the
research lead can decide, with numbers in front of them, what to buy. Nothing here
was acquired with money or credentials.

The engineering pipeline in this repository was validated on a **free, publicly
hosted Nasdaq sample day** (see section 7). That sample validates code; it cannot
answer the candidate's question, and it is never used to claim that the hypothesis
works.

---

## 1. What M2 needs and why the sample day is insufficient

The frozen candidate spec
(`M1/hypotheses/candidate_specs/NASDAQ_LARGETICK_QUEUE_IMBALANCE_UNIVERSE.json`,
rule `NASDAQ-LARGETICK-QIMB-UNIV-v1`) requires three things a single free day
cannot supply:

| requirement | why it is required | sample day |
|---|---|---|
| 60-trading-day causal lookback of order-level Nasdaq book state | the large-tick classification (`median spread == 1 tick` **and** `fraction at one tick >= THETA=0.50`) and the 90%-coverage rule are computed over the lookback; the monthly selection date consumes only strictly-earlier data | ✗ one day |
| ≥ 120 trading days of continuous listing/coverage history | history floor, twice the lookback | ✗ |
| point-in-time listing / security-type / corporate-action / halt reference | "a dataset that only exposes today's constituents cannot be used"; membership must be reconstructed as of each monthly selection date | ✗ none secured |
| the evaluation period itself (the money-making window), with modern regime | the mechanism must be measured in the period the result is claimed for | ✗ 2019 tape, development role only |

## 2. Intended dataset — option A (recommended): Databento `XNAS.ITCH` (MBO)

Verified from primary vendor pages on 2026-09-22:

* Dataset id `XNAS.ITCH`, Nasdaq TotalView-ITCH; **coverage from 2018-05-01 UTC**
  (`https://databento.com/datasets/XNAS.ITCH`).
* Schemas available include **MBO**, MBP-1, MBP-10, TBBO, Trades, Definition,
  Imbalance, Status.
* MBO record fields: `ts_recv`, `ts_event`, `rtype`, `publisher_id`,
  `instrument_id`, `action`, `side`, `price`, `size`, `channel_id`, `order_id`,
  `flags`, `ts_in_delta`, **`sequence`**
  (`https://databento.com/docs/schemas-and-data-formats/mbo`).

Why this matters beyond size: the free raw ITCH tape has **no receive clock, no
sequence number and no channel field** (see `schema_contract.md`, sections 0.3-0.5),
so two of the audits the handoff asks for are *impossible* on it. `XNAS.ITCH` MBO
carries `ts_recv`, `sequence` and `publisher_id`/`channel_id`, which makes the
receive-before-event, sequence-gap and cross-channel-ordering audits computable —
that is a data-quality advantage independent of the alpha question.

**Cost: UNKNOWN.** Databento bills historical time series on **uncompressed DBN
bytes** at a unit rate obtained from an authenticated metadata call
(`https://databento.com/docs/api-reference-historical/basics/metered-pricing`,
`.../metadata/metadata-list-unit-prices`). The public unit-price endpoint returned
HTTP 401 with no credentials, so no rate is quoted here. A free sample dataset
exists but requires a login; its public download URL, coverage and size were not
retrievable without an account. **Credentials required for purchase: yes.
Credentials required to decode already-downloaded local files: no. Minimum
purchase: UNKNOWN (not published).**

## 3. Intended dataset — option B: Nasdaq Historical TotalView-ITCH (direct, SFTP)

Verified in-repo (`SRC-0201`, `M1/data/venue_facts.csv`): order-level history from
**2007-08-13 to present**, SFTP delivery, **Nasdaq Global Data Agreement required**,
price **quote-only**. The current Nasdaq public price list does not publish a
per-day or per-year order-level history price (Nasdaq publishes a 2016 distributor
monthly fee schedule, which is not a current quote). **Cost: UNKNOWN.**

Option B is the more authoritative source; option A is the only one whose schema
adds the receive/sequence/channel fields the audit needs. A defensible plan is B
for provenance and A for causality auditing, or A alone if B cannot be quoted.

## 4. Exact scope to request

1. **Lookback window**: 60 trading days ending on the last trading day before the
   first selection date. For a selection on the first trading day of month `T`,
   request `[first trading day of T-3 months, last trading day before T]` — 60
   trading days plus a 20-trading-day buffer for holidays and half-days.
2. **Evaluation window**: at least two further calendar months after `T`
   (development and validation), plus a reserved sealed month that M2-0 must not
   read. Minimum viable set: **4 months of data** (3 lookback months + evaluation),
   **6 months** preferred so the walk-forward has more than one fold.
3. **Symbols**: the rule needs top-decile dollar volume by security, which is a
   *rank*, so the cheapest correct route is two-stage:
   * stage 1 (cheap): a low-precision product (e.g. `Trades` or `MBP-1`) for the
     **whole venue** over the lookback to compute per-symbol median daily dollar
     volume, the price floor and listing-age checks;
   * stage 2 (the expensive product): **MBO for the selected symbol set only**
     (top decile of eligible names, expected ~50-300 names), for the lookback and
     the evaluation window. Databento supports symbol-filtered historical
     requests, which is what makes this affordable at all.
4. **Reference data** (separate from the market feed): a point-in-time security
   master with security type, listing venue, listing start/end and corporate-action
   effective dates, plus a halt history. Candidate sources and their verification
   status are listed in section 6; **none is secured**.

## 5. Size, disk and cost estimate

Estimation basis, measured on the real tape in this pass (not guessed):

* whole-venue Nasdaq TotalView-ITCH for **one** trading day (2019-07-30):
  3,662,140,094 bytes compressed (gzip), **8,661,679,413 bytes decompressed**,
  282,229,684 messages;
* the 61-symbol development scope carries **9.03%** of the tape's book-modifying
  messages (25,000,688 scope messages of 277,005,526 book-modifying messages), so a
  symbol-filtered extract of a similar 61-name set is roughly **0.8 GB/day
  decompressed** in the ITCH binary layout.

Planning arithmetic, stated as an order-of-magnitude budget rather than a quote:

| item | estimate | basis |
|---|---|---|
| 60 trading days × ~60 symbols, MBO | order of 50 GB decompressed | 0.8 GB/day measured share × 60 days, 2019 message rates; **2026 rates are higher and this is not a quote** |
| whole-venue product for the same window (stage 1) | order of 500 GB decompressed | 8.66 GB/day venue-wide ITCH × 60 days; 2026 volumes are higher |
| local disk to keep raw + derived | 250 GB free recommended | raw extracts, DBN/ITCH files, derived Parquet, manifests |
| money | **UNKNOWN** | vendor unit rate is behind authenticated metadata; no purchase is authorized without explicit user approval |

## 6. Point-in-time reference: unmet, with candidate routes

`point_in_time_membership_status` in the frozen spec is already
`REQUIRED_DATA_NOT_SECURED`. Candidate routes, with what is actually verified:

| route | what it would supply | verification status |
|---|---|---|
| Commercial security master (CRSP / Compustat / FactSet / Bloomberg) | PIT listing, security type, corporate actions, delisting | **not priced, not procured** — cost UNKNOWN |
| Nasdaq Trader daily symbol directory files (`nasdaqlisted.txt`, `otherlisted.txt`) | security type flags, ETF flag, round lot, test-issue flag — but only *as of the day it was published* | current file verified to exist; historical snapshots are not published by Nasdaq, so PIT reconstruction would depend on third-party archives whose cadence and integrity are **unverified** |
| SEC EDGAR submissions/full-text | listing entity history, corporate-action filings | free, but security-type/venue classification is not directly expressed; a mapping would have to be constructed and verified |
| Exchange halt notices (Nasdaq trade-halt history) | halt events for the halt-frequency rule | historical coverage and machine readability **unverified** |

Until one of these is procured and verified, the universe branch stays **BLOCKED**
rather than being run on survivor-biased symbols.

## 7. What the free sample did and did not establish

Acquired without cost or credentials: Nasdaq's publicly hosted
`07302019.NASDAQ_ITCH50.gz` (2019-07-30), SHA-256 recorded in
`M2/data/manifests/raw_manifest.json`.

It established: the container framing, the field semantics against the provider
specification, framing integrity over all 282,229,684 messages, timestamp and
ordering behaviour, book reconstruction and its integrity counters, the causal
decision/label/delay machinery, and the whole calculation stage — end to end, on
real Nasdaq order-level data.

It did **not** establish: modern-regime behaviour, universe membership, any
statistic transferable to a decision, and it must never be renamed a test or
holdout partition (handoff 21/22).

## 8. Decision requested

One decision, with the exact question:

> Approve or reject a paid acquisition of modern Nasdaq order-level data — Databento
> `XNAS.ITCH` MBO (or Nasdaq Historical TotalView-ITCH), scope per section 4 — after
> obtaining a written quote for it, and separately approve or reject procurement of
> a point-in-time security master.

Until both are answered, M2 remains **CALCULATION_BLOCKED** on anything that
depends on the universe rule or on a modern evaluation window, and no money is
spent.
