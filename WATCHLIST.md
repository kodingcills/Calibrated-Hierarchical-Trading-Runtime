# WATCHLIST

Generated from `M1/data/discrepancies.csv`. Items are here because a single external
fact can change the candidate set, not because they are interesting.

## External facts that can change the survivor set without any modelling

- **UNK-0002** (A): The current rulebook/matching specification for the exact contract and order type, plus its change history. -> prevents: Any queue-position or fill model for passive CME candidates (KG2/KG3).
- **UNK-0027** (A): One exact instrument per surviving branch, with its tick/lot/matching and fee facts. -> prevents: M2 registration and any falsifier (KG5) for the affected rows.
- **UNK-0010** (A): Current fee schedule, historical event-level L2 product with timestamps, and the venue's liquidation-data surface. -> prevents: Net-edge feasibility for the Hyperliquid H3/H4 candidates.
- **UNK-0012** (B): Fee codes for the exact order types, OPRA versus proprietary depth history, and point-in-time surface data. -> prevents: Options tuples passing Gate 2 at all.
- **UNK-0013** (B): 2026 access/fee schedule, API contract and historical book product. -> prevents: Gate 2 for the Deribit tuple.
- **UNK-0014** (A): A current per-contract access matrix plus fee/API/history facts. -> prevents: Legality/access gate for both event-market tuples.
- **UNK-0015** (A): A named venue plus participant status and its published or contractual execution policy. -> prevents: Defining the tuple at all (KG1/KG3/KG5).
- **UNK-0028** (B): Broker/venue quotes for the intended account type plus margin and minimum-size terms. -> prevents: Deployment-shape decisions (not M1 selection); also drives which fee tier applies in M2 cost configuration.
- **UNK-0005** (B): Broker/venue fee schedule for the project's exact routing and account type, per fee code. -> prevents: Net-economics arithmetic for equity tuples (KG3).
- **UNK-0003** (B): Vendor quote plus a sample file whose schema and timestamp fields are validated against a live feed. -> prevents: Causal queue replay for CME candidates (KG2), and therefore M2 for them.
- **UNK-0011** (B): Instrument-specific fee schedule, matching rule, historical data quote and access route. -> prevents: Any Eurex candidate progressing beyond universe status.
- **UNK-0001** (B): Current CME/FCM schedule for the exact account path, registered as an immutable M2 cost configuration. -> prevents: Aggressive CME execution viability (KG3) for every CME tuple.
- **UNK-0004** (B): Order-level historical product, license terms, sample and cost. -> prevents: Queue-aware backtesting of every Nasdaq equity tuple (KG2).
- **UNK-0020** (B): Historical auction-imbalance dataset with exact dissemination timestamps. -> prevents: Auction tuple feasibility (KG2): without it the auction candidate has no historical basis for testing.
- **UNK-0022** (B): Feed/data entitlement list and a sample of realized fee codes. -> prevents: BZX passive tuple feasibility (KG2/KG3).

## Venue and product changes worth watching (they can invalidate a fact already used)

- CME matching-rule changes: product-specific rules have already changed by notice (EVD-0003), so a queue model must record the rule version it assumes.
- Cboe U.S. equities fee schedule revisions (the verified rebate/remove rates are dated 2026-09-01).
- Coinbase and Kraken fee-tier changes: the two current crypto kills depend on verified floors; a materially lower verified tier plus gross-edge evidence would reopen them.
- Hyperliquid public feed changes: the 10-100 ms kill rests on a documented >= 0.5 s snapshot cadence; a direct order-level feed would constitute a new tuple.
- Event-market jurisdictional changes: state-level access restrictions are live (EVD-0016), so any event-market work needs a current access matrix, not a memory.

## Technology watch (admission-relevant, never admission-deciding)

- Measured (not vendor-reported) hosted-Jev latency under trading-like load.
- Any independent reproduction of System-One calibration or incremental utility.
- Any release of order-level historical data at a cost that clears the data gate.
