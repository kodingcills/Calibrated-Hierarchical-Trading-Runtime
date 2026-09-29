# CME ES H3 OFI readiness — Branch A

**Retrieved/access date:** 2026-09-29. **Decision:** `ES_EXTERNAL_ONLY`.

This is a data-readiness decision, not an outcome result. No OFI outcomes, markouts, strategy tuning, paper trading, purchase, credentials, or canonical artifact changes were performed. The official CME API page establishes that real-time futures/options API data includes top-of-book prices, trade information and market statistics, and directs historical access to CME DataMine (S2). It does **not** establish that a no-purchase historical ES sample is available, nor does it establish the causal replay fields required below. Therefore the precursor is not frozen or runnable from the repository; it remains externally blocked.

## 1. Four allowed feed families

The table records what is required for an aggressive H3 OFI gross-markout precursor. “Expected” is an engineering interpretation, not an official CME claim; where the current official page does not expose the field definition, status is `UNKNOWN`/`PARTIAL` rather than promoted to verified.

| Feed | Product / fields / depth | Timestamp semantics | Trade + aggressor | Ordering / sequence | Date availability / access | No-purchase sample | Readiness implication |
|---|---|---|---|---|---|---|---|
| Time & Sales | ES outright trade prints: trade price, quantity, trade time/date; normally prints only, no resting depth. Exact CME historical schema and any trade-condition fields were not fetched. | Trade-event time and resolution are **UNKNOWN** from S2. Local receipt time is not an exchange event clock. | Trade price/size is **PARTIAL/UNKNOWN** as an official causal source; aggressor side is not verified. A last-price tape alone cannot prove whether buyer or seller initiated. | **UNKNOWN**: no official sequence-number/message-order evidence fetched. | Current official page proves real-time API exists and historical is via DataMine, not years/schema. | **UNKNOWN / not demonstrated**. | Insufficient by itself for OFI; could be a trade leg only if aggressor and ordering are externally proven. |
| Top of Book | ES best bid/ask and displayed bid/ask quantities (depth = one level); S2 explicitly says top-of-book prices. Exact field names and whether sizes are event snapshots or deltas are **UNKNOWN**. | **UNKNOWN** resolution, exchange-vs-receipt clock, and update semantics. | Trade information is advertised by S2, but linkage of a trade to quote/aggressor is **UNKNOWN**. | **UNKNOWN** sequence identity and gap/replay semantics. | Real-time JSON WebSocket is verified by S2; historical DataMine path is verified only at product level. | **UNKNOWN**. | Candidate minimal quote input, but not sufficient to reconstruct causal queue changes without sequence/timestamp/schema proof. |
| Market Depth | ES multi-level aggregated book (depth N/venue entitlement must be specified). Exact depth, level update model, and fields are **UNKNOWN** from fetched official material. | **UNKNOWN** resolution and clock domain; no official snapshot/update timestamp passage available in this environment. | Usually no order aggressor identity; trade linkage **UNKNOWN**. | **UNKNOWN** sequence, snapshot boundary, and recovery semantics. | S2 proves only that the API offers top-of-book/trade/statistics and historical DataMine; it does not prove depth-history availability. | **UNKNOWN**. | Could support depth-aware OFI only after entitlement/schema/replay evidence; not ready now. |
| MBO | ES order-level book; required fields would include add/modify/delete/trade, price, quantity, order identity and side, with full available depth. CME MBO availability and exact fields were not proven by accessible official source. | **UNKNOWN** exchange event resolution/clock and historical encoding. | Order events can in principle identify queue changes; aggressor/trade flags are **UNKNOWN** and must not be inferred from side alone. | **UNKNOWN** exchange sequence and order-id lifecycle from fetched sources. | No fetched official source proves historical ES MBO dates, DataMine product, or entitlement. | **UNKNOWN**. | The only plausible causal-replay family, but externally blocked until CME message specification and sample prove all fields. |

**Important distinction:** S2 is positive evidence for a current CME JSON API with top-of-book/trade information, not evidence that it is a lossless historical feed. CME technical-document URLs attempted on 2026-09-29 returned HTTP 403 or legacy Confluence Page Not Found (S5). No field, precision, sequence, MBO, depth-history, or sample claim is inferred from that failure.

## 2. Causal replay field map

Required causal replay fields are mapped against authoritative evidence actually fetched. `VERIFIED` means directly supported by a fetched official passage; `PARTIAL` means only a related fact is supported; `UNKNOWN` means not established.

| Required field | Status | Evidence and exact limitation |
|---|---|---|
| Event timestamp | `PARTIAL` | CME markets page gives trading hours and maintenance (S1); S2 advertises live API data, but neither fetched passage specifies exchange event timestamp field or resolution for any of the four feeds. |
| Ordering | `UNKNOWN` | No accessible official MDP/DataMine message specification proving total order or same-event ordering. |
| Sequence identity | `UNKNOWN` | No fetched official source proves packet/message sequence fields, reset behavior, or sequence scope. |
| Security identity | `PARTIAL` | S1 identifies ES product code `ES` and the page’s current example symbol; S4 identifies Rule 358 ES product. A replay-grade security ID/instrument definition and rollover mapping are not verified. |
| Session boundaries | `PARTIAL` | S1 directly provides Globex Sunday 18:00–Friday 17:00 ET and daily 17:00–18:00 ET maintenance. Holiday/early-close calendar and feed session markers remain unverified. |
| Clock domain | `UNKNOWN` | No fetched official source says whether timestamps are exchange matching-engine time, gateway time, UTC, CT, ET, or vendor receipt time. |
| Duplicate detection | `UNKNOWN` | No message identity/sequence specification fetched; cannot define dedupe from timestamp-price-size. |
| Gap detection | `UNKNOWN` | No sequence/recovery/snapshot specification fetched; cannot certify losslessness or gap handling. |

A replay cannot be called causal until the external request below supplies these missing proofs and a sample that exercises them.

## 3. Minimum exact instrument and pre-registered roll rule

**Instrument:** CME E-mini S&P 500 futures outright, product code `ES`, one quarterly contract at a time; exclude calendar spreads, BTIC/TACO/TMAC, options, and Micro E-mini. S1 verifies $50 × S&P 500 Index contract unit, 0.25 index-point ($12.50) outright tick, quarterly listing for 21 consecutive quarters, and termination at 09:30 ET on the third Friday.

**Rule (freeze before any outcome inspection):** For each event, retain the native CME security/instrument identifier and its quarterly contract month. Use the expiring quarterly contract through its final permitted trading time; at the first Globex session beginning at 18:00 ET after the third-Friday termination, switch to the next quarterly contract. Do not splice prices, quotes, order IDs, or sequences across contracts; mark the switch as a session boundary and require each contract’s first valid snapshot/replay state before calculating OFI. If a contract is suspended or an official early-close calendar applies, stop the session rather than inventing a timestamp. This is intentionally boring and implementable from S1; it does not claim that it is the only economically optimal roll.

**H3 definition for this branch:** H3 means a three-hour forward markout horizon; it is not a CME contract code. The horizon must remain within the same contract/session unless the frozen protocol explicitly marks a boundary as censored.

## 4. Public mandatory costs vs account-specific costs

### Verified public facts

* CME’s official fees page says exchange fees vary by membership/incentive status, product, volume, venue and transaction type (S3). It links the CME fee schedule effective 1 October 2026 and a non-member fee finder.
* S1 verifies the ES tick value: one outright tick is $12.50. That is contract economics, **not** a fee.

### Not resolved to an amount in this branch

The linked fee schedule’s ES rows could not be extracted in this environment, and the page itself is dated for a future effective schedule pending relevant CFTC review. Therefore do not hard-code a fee number. The following public mandatory categories need an effective-date and participant-status selection from the schedule:

1. CME exchange transaction fee, per side and round turn, for non-member/non-incentive ES;
2. CME clearing fee, if separately itemized for the selected customer class;
3. any publicly specified regulatory assessment applicable to the transaction (NFA/CFTC or other statutory line), with effective date;
4. exchange market-data licensing/subscription charge if the selected access path requires it (this is a data-access cost, not a per-contract execution fee).

Keep separate and do not silently substitute: FCM commission/markup, broker routing/platform fees, clearing-member pass-through, account/membership discounts, taxes, financing/margin carry, and any vendor redistribution charge. S3 expressly confirms participant/product/venue/transaction-type variation, so one universal “ES fee” is not justified.

## 5. Exact external request / unblock criteria

Request from CME/DataMine or an authorized distributor, in writing and for a specified entitlement/account:

1. The current ES MDP/DataMine schema for **each** supplied family (T&S, top-of-book, depth, MBO), including exact field names, units, nullable rules, and depth/entitlement.
2. A lossless historical ES sample covering at least one complete regular Globex session and one quarterly roll, with native raw files (not a chart/export), instrument/security definitions, snapshots, incremental messages, trade conditions, and any aggressor indicator.
3. Event timestamp definition, precision, timezone/clock domain, message and packet sequence fields, sequence-reset/recovery rules, order-id lifecycle, and documented ordering for same-timestamp messages.
4. Official DataMine availability dates for ES for every required feed, plus retention/completeness, corrections, late/out-of-order policy, and confirmation that historical sample access is permitted without purchase. If no no-purchase sample exists, state price/entitlement and do not treat the source as internally available.
5. Fee schedule rows/effective date for non-member ES exchange, clearing, regulatory and data-access charges; separately request the target FCM’s commission, routing, platform, and pass-through schedule.


## Sources

* **S1:** https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html — fetched 2026-09-29; snapshot `cme_es_contract_specs_2026-09-29.txt`. Official contract unit, tick, hours, quarterly listings and termination.
* **S2:** https://www.cmegroup.com/market-data/market-data-api.html — fetched 2026-09-29; snapshot `cme_market_data_api_2026-09-29.txt`. Official API access description: real-time WebSocket JSON with top-of-book/trade/statistics; historical via DataMine.
* **S3:** https://www.cmegroup.com/company/clearing-fees.html — fetched 2026-09-29; snapshot `cme_fees_page_2026-09-29.txt`. Official exchange-fee variation and schedule link.
* **S4:** https://www.cmegroup.com/market-regulation/rulebook.html and https://www.cmegroup.com/rulebook/CME/index.html — fetched 2026-09-29. Official index identifies Rule 358 as ES; direct linked rule URL is `https://www.cmegroup.com/rulebook/CME/IV/350/358/358.pdf`.
* **S5:** attempted official MDP technical PDF `https://www.cmegroup.com/content/dam/cmegroup/market-data/MDP-3.0/MDP-3.0-Core-Messaging-Reference.pdf` and legacy Confluence documentation on 2026-09-29; HTTP 403/Page Not Found, saved as a retrieval limitation in `SOURCES.md`, not used to infer semantics.
