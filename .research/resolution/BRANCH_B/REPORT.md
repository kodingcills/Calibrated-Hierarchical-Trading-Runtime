# Branch B — Nasdaq closing-auction precursor

**Result: `AUCTION_EXTERNAL_ONLY`.** One mechanism survives definition: **signed late NOII imbalance change (15:50→15:55 ET) as pressure on the Nasdaq Closing Cross clearing displacement**. This is a causal market-design hypothesis, not an outcome-selected strategy: late eligible order-flow revisions change the auction supply/demand intersection, so the 15:55 signed imbalance revision should be related to the eventual cross price relative to the 15:55 reference price. I did not inspect performance/outcomes.

## Freeze-ready causal contract (pending historical tape)

- **Freeze time:** 15:55:00 ET on each regular close. Use the last NOII `I` message with `Cross Type=C` and exchange timestamp `t <= 15:55:00 ET`, and the last such message with `t < 15:50:00 ET` (or the first message at/after 15:50:00 if no exact boundary message). Preserve exchange timestamp, sequence/tracking metadata, and raw fields; do not forward-fill across a feed gap.
- **Signal:** `signed_imbalance(t) = +ImbalanceShares` for direction `B`, `-ImbalanceShares` for `S`; `N`, `O`, or `P` is missing/not eligible. The sole precursor is `ΔI = signed_imbalance(15:55) - signed_imbalance(15:50)`, with optional predeclared scale `ΔI / max(PairedShares_15:55,1)` for cross-security comparability. No threshold, bucket, side selection, or tuning is specified.
- **Materiality target:** `Y = (ClosingCrossPrice - CurrentReferencePrice_15:55) / CurrentReferencePrice_15:55`; use the `Q` Cross Trade with `Cross Type=C`. This is gross auction displacement, not a fill-conditioned return, and must be measured only after the 16:00 cross.
- **Timestamp semantics:** ITCH timestamps are Nasdaq exchange-generated nanoseconds since midnight; they are not local receipt timestamps. Replay must retain message ordering/sequence and packet-gap status. Session times above are ET. A day is incomplete if required NOII or cross messages are missing, duplicated without sequence resolution, or a feed gap cannot be repaired.

## Point-in-time universe and identity

For each date, include only instruments present in that date's Nasdaq TotalView-ITCH Stock Directory day spin, with `Authenticity=P` (live/production), `ETP Flag=N`, `Issue Classification=C` (common stock), `Issue Sub-Type=C` (common shares), and Market Category in `{Q,G,S,N,A,P,Z,V}` (the listed-market codes in the specification). Require a Closing Cross NOII (`I`, `Cross Type=C`) and a closing Cross Trade (`Q`, `Cross Type=C`) for that same date/security. Identity is the date-specific Stock symbol plus that day's Stock Locate; never carry membership, symbols, classifications, or a survivor list from another date. This avoids ANYCAP and survivorship leakage; no index membership is used.

## Participation/order semantics

The precursor is observation-only: no account, route, order, or paper trade is authorized. If a later, separately approved execution test is needed, predeclare a **Market-On-Close (MOC)** order submitted after the 15:55 freeze through an exchange-member route, participating in the Nasdaq Closing Cross; it accepts the cross price and is exposed to auction price risk. A Limit-On-Close alternative must be a separate protocol (Nasdaq permits LOC entry through 15:58 ET, with no cancellation/modification after 15:55 per S4). Gross displacement must be evaluated before any fill/routing analysis; account access, broker support, acknowledgements, rejects, and actual fill are unknown.

## What official sources establish

- **S1** (`https://www.nasdaqtrader.com/Trader.aspx?id=OpenClose`, retrieved 2026-09-29): all nationally listed securities are eligible; Nasdaq disseminates closing NOII 15:50–16:00 ET; accepted close participation includes ON-CLOSE and IMBALANCE-ONLY CLOSE. It does not establish a historical archive or replay entitlement.
- **S2** (`https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf`, retrieved 2026-09-29): live TotalView-ITCH is a direct outbound feed. NOII `I` contains timestamp, paired shares, imbalance shares/direction, symbol, far/near/current-reference prices, cross type; `Q` contains timestamp, shares, symbol, cross price, and cross type. The Stock Directory supplies the daily symbol/locate, listing category, issue class/subtype, authenticity, and ETP flag. This proves field availability in the live protocol, not historical retention.
- **S3** (`https://www.nasdaq.com/products/data/equities/nasdaq-totalview`, retrieved 2026-09-29): Nasdaq advertises real-time NOII before the official Open/Close and access through direct feeds, Data Link, web products, or vendors; it does not claim that historical NOII/ITCH captures are downloadable/replayable.
- **S4** (`https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2026-32`, 2026-06-23): early close dissemination begins 15:50, full dissemination 15:55, MOC entry stops 15:55, LOC entry ends 15:58, and the close begins 16:00. It is an operational schedule, not a historical-data product.

## Blocker and smallest external request

Search of the official Open/Close page, TotalView product page, Data Link NTV documentation landing page, and current ITCH specification found no verifiable historical NOII replay/archive product, retention, or completeness guarantee. Therefore this is `AUCTION_EXTERNAL_ONLY`, not `AUCTION_PRECURSOR_READY`. Request the smallest no-outcome sample: **one regular month (or 20 consecutive regular sessions) of raw Nasdaq TotalView-ITCH 5.0 captures**, including the full daily spin and 15:49:50–16:00:10 ET for all symbols, with `I`/`Q` messages, nanosecond exchange timestamps, feed sequence/packet identifiers, and gap/retransmission metadata; include delivery format, retention, historical corrections/broken-cross handling, and entitlement/price. No purchase or credentials were obtained.

## Reproducibility

```sh
curl -L 'https://www.nasdaqtrader.com/Trader.aspx?id=OpenClose'
curl -L 'https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf' -o /tmp/NQTVITCHSpecification.pdf
curl -L 'https://www.nasdaq.com/products/data/equities/nasdaq-totalview'
curl -L 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2026-32'
```
Raw source extracts and retrieval metadata are in `SOURCES.txt` in this directory. Canonical root artifacts were not edited.
