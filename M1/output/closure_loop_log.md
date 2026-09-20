# Closure loop log

Append-only. One block per iteration. No narrative: the format exists so a later session can
reconstruct why state changed without re-reading the repository.


ITERATION: 1
UTC: 2026-09-20T18:27:04Z
BLOCKER CLUSTER: NASDAQ_EQUITY + CBOE_EQUITY (Tier-1 primary research; UNK-0004, UNK-0005, UNK-0020, UNK-0022, UNK-0023)
WHY SELECTED: Highest leverage on the recomputed frontier after the stage-semantics fix: GLOBAL impact, HIGH kill potential, and the cheapest available class of fact (published venue documentation).
RESOLUTION METHOD: PUBLIC_RESEARCH (researcher: USEquityFacts resolver)
SOURCES ADDED: 12 primary sources SRC-0201..SRC-0212 (Nasdaq ITCH SFTP spec, Nasdaq price lists, Nasdaq trading price list, Nasdaq NOII notice dtn2009-059, Cboe DataShop PITCH, Cboe BZX fee schedule, Cboe BZX Rule 11.12, IEX fee schedule, NYSE price list, Nasdaq NOIView spec, FR ELO notice, Nasdaq Equity 4 Rule 4757 corroboration)
DECISION: SUPPORTS (patch P-0001 applied after adversarial verification)
GATES BEFORE: KG1 PASS 2 / KG2 PASS 0 / KG3 PASS 0 / KG4 PASS 22 / KG5 PASS 9; eligible 0
GATES AFTER: unchanged: no gate moved, because the new facts narrow blockers and quantify mandatory costs rather than supplying fills, markouts or a break-even
CANDIDATES KILLED: None
CANDIDATES PROMOTED: None
ISSUES RECLASSIFIED: UNK-0004 and UNK-0022 -> EXTERNAL_REQUEST_READY; UNK-0020 -> RESOLVED_SUPPORTS (NOII history is included with the order-level subscription at no additional charge); UNK-0005 and UNK-0023 -> IN_PROGRESS
NEW ISSUES: UNK-0033 (sponsored-access commission has no public source; new M1-blocking Tier-3 external action)
VALIDATION: PASS 0 failures / 18 rule groups; 76 unit tests OK
NEXT FRONTIER ITEM: UNK-0009 (modern venue-specific replication) by leverage, or UNK-0027/UNK-0002 by tier-1 cheapness; see M1/work/frontier.json

ITERATION: 2
UTC: 2026-09-20T18:48:01Z
BLOCKER CLUSTER: HYPERLIQUID + DERIBIT + EVENT_MARKETS (UNK-0010, UNK-0013, UNK-0014)
WHY SELECTED: Second tier-1 batch already in flight from the same resolver wave; cheapest class of fact for the remaining venue families and high kill potential.
RESOLUTION METHOD: PUBLIC_RESEARCH (researcher: CryptoEventFacts resolver)
SOURCES ADDED: 22 primary sources SRC-0213..SRC-0234 (Hyperliquid fees/historical data/API/WS/liquidations/terms; Deribit fees, market-data practices, restricted jurisdictions; Kalshi fee schedule, historical endpoints, member agreement, WA AG release, NV GCB release, Third Circuit opinion; Polymarket fees, TOS, Polymarket US docs, CFTC settlement, API limits, reporting docs; Tardis vendor price list)
DECISION: SUPPORTS (patch P-0002 applied after adversarial verification)
GATES BEFORE: KG1 PASS 2 / KG2 PASS 0 / KG3 PASS 0 / KG4 PASS 22 / KG5 PASS 9; eligible 0
GATES AFTER: unchanged counts; KG3 for Hyperliquid stays BLOCKED but now because a verified 9 bps floor has no venue-specific gross-effect evidence rather than because the fee was unknown
CANDIDATES KILLED: None
CANDIDATES PROMOTED: None
ISSUES RECLASSIFIED: UNK-0010, UNK-0013, UNK-0014 -> IN_PROGRESS with narrowed residual questions; UNK-0020 previously resolved
NEW ISSUES: UNK-0034 (operator jurisdiction and client classification: not researchable, requires a human statement, gates 8 rows across four venue families); UNK-0035 (fee-page version control: several venues publish fees with no effective date, so the project must snapshot them)
VALIDATION: PASS 0 failures / 18 rule groups; 77 unit tests OK
NEXT FRONTIER ITEM: UNK-0018 (feed timestamp semantics) by leverage; UNK-0002 (CME product assignment) by tier-1 cheapness

ITERATION: 3
UTC: 2026-09-20T18:48:01Z
BLOCKER CLUSTER: CME (UNK-0001, UNK-0002, UNK-0003, UNK-0018)
WHY SELECTED: Largest remaining candidate family with no fee or matching facts; selected on tier-1 leverage before any measurement work.
RESOLUTION METHOD: PUBLIC_RESEARCH (researcher: CMEFacts resolver) - PARTIAL, with self-reported tooling failure
SOURCES ADDED: 3 primary client-wiki sources SRC-0235..SRC-0237 (supported matching algorithms; matching step matrix; DataMine MBO FIX)
DECISION: WEAKENS (patch P-0003 applied after adversarial verification): the resolver reported its own assignment incomplete and its fee-table reconstruction failed
GATES BEFORE: unchanged from iteration 2
GATES AFTER: unchanged: engine-level matching documented but the ES/NQ product assignment is unresolved, so KG3 stays BLOCKED for the passive CME tuple and KG2 stays BLOCKED for every CME row
CANDIDATES KILLED: None
CANDIDATES PROMOTED: None
ISSUES RECLASSIFIED: UNK-0002, UNK-0003, UNK-0018 -> IN_PROGRESS (narrowed); UNK-0001 -> EXTERNAL_REQUEST_READY with the public search recorded as exhausted in the issue registry
NEW ISSUES: none
VALIDATION: PASS 0 failures / 18 rule groups; 77 unit tests OK
NEXT FRONTIER ITEM: UNK-0018 or UNK-0002 per M1/work/frontier.json; the CME cost question is now an external boundary item, not a search item
REJECTED CLAIM (iteration 3): 'ES/NQ non-member per-side exchange fee is $1.28' - non-primary source, no recoverable URL, surfaced during a failed tool-assisted fee-table reconstruction. Not absorbed into any venue fact. Recorded in M1/work/patches/P-0003.json modified_claims.
