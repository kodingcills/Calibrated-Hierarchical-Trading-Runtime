# Resolution sprint 001 — human action packet

No credentials, purchase, trade, paper trade, commit, or push is requested by this packet. These are the only remaining external actions needed to move a branch beyond `EXTERNAL_ONLY`.

## 1. CME ES H3 OFI — highest decision impact

Provide:

- operator jurisdiction/entity and intended account class;
- CME member/non-member and incentive status;
- target FCM/broker and permission to request its current ES commission, routing, platform, clearing pass-through, and data-access schedule;
- one complete regular Globex session of raw historical ES data for one quarterly contract, plus one quarterly roll boundary, covering the cheapest sufficient feed family for aggressive H3 OFI (Time & Sales + top-of-book is acceptable only if the schema proves causal trade/quote linkage; MBO is not required by hypothesis);
- field documentation and sample proving exchange event timestamp, clock domain/precision, message ordering, sequence identity/reset/recovery, security definitions, session markers, duplicate/gap detection, trade conditions/aggressor semantics, and date coverage;
- CME exchange, clearing, regulatory, and data-access charges effective for the selected participant status; do not substitute generic fees.

Acceptance: reproduce one known state from increments; detect a removed sequence item as a gap; detect a duplicate; preserve native contract IDs through the quarterly roll; prove one timestamp domain. Full details: `.research/resolution/BRANCH_A/REPORT.md`.

## 2. Nasdaq closing auction — historical replay request

Request one regular month or 20 consecutive regular sessions of raw Nasdaq TotalView-ITCH 5.0 captures, including:

- daily Stock Directory spin;
- all symbols, 15:49:50–16:00:10 ET;
- NOII `I` and Cross Trade `Q` messages;
- nanosecond exchange timestamps, sequence/packet identifiers, and gap/retransmission metadata;
- retention, correction, broken-cross handling, delivery format, entitlement, and price.

The intended frozen precursor is signed NOII imbalance change from 15:50 to 15:55 ET versus closing-cross displacement, with same-day point-in-time Stock Directory membership. Full details: `.research/resolution/BRANCH_B/REPORT.md` and `M1/work/reselection_specs/TUP-NASDAQ-CLOSING-AUCTION-LATE-NOII.json`.

## 3. Hyperliquid funding/basis — paired public-data unblock

Provide or authorize a no-purchase-accessible historical sample for:

- Hyperliquid Core `BTC` linear perpetual funding, mid/book/oracle fields and exact hourly timestamps;
- Binance USDⓈ-M `BTCUSDT` perpetual mark/funding/price fields for the same UTC hours;
- completeness and gap documentation for both sources;
- current effective Binance trading/funding/other mandatory costs and account-independent terms.

The frozen one-hour pair and strict kill gate are in `M1/work/reselection_specs/TUP-HYPERLIQUID-BTC-FUNDING-BASIS.json`. The current probe observed one of two expected Hyperliquid funding buckets and HTTP 451 from Binance in this environment; neither observation proves global data absence.
