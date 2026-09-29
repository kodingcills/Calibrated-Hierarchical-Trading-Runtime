# Bounded edge-discovery campaign

## Result
ES remains one incumbent branch, not the only branch. The verification pass retained ES H3 OFI and ES H1 passive queue depletion separately, plus four structurally distinct conditional alternatives: Nasdaq closing-auction flow, Hyperliquid funding/basis, Deribit option-surface RV, and CME WTI volatility-transition flow. No candidate is promoted; canonical state remains `EXTERNAL_BLOCK` / `NOT_ALIVE`.

## Discovery groups
Seven independent contexts ran without cross-pollination: incumbent ES; forced flow; relative value; market design; horizon mismatch/capacity/persistence; search-process red team; cheap precursors. Full machine-readable outputs: `ROUND1_RESULTS.json` and `ROUND2_REALLOCATION.json`.

## Verified findings
- **ES incumbent pair.** H3 aggressive OFI's cheapest falsifier is a fixed-contract/roll causal gross-markout versus exact account-level round-trip friction screen. H1 passive queue depletion is not interchangeable: it requires product-specific matching, queue reconstruction, fills, and fill-conditioned markouts. Evidence: `M1/work/reselection_specs/TUP-CME-ES-H3-OFI-AGG.json`, `M1/data/candidate_tuples.csv`, `M1/output/M1_CANDIDATE_RESELECTION.json`.
- **Auction branch.** `TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG` is materially distinct from the closed Nasdaq continuous-book family: event-concentrated clearing and mandate flow, not continuous H1-H3 top-of-book prediction. It remains blocked pending exact universe/order type, NOII coverage/timestamps, and after-cost replay. Evidence: `M1/work/cards/UNK-0027-AUCTION.json`, `M1/data/mechanisms.csv`, `M1/data/evidence_ledger.csv`.
- **Relative-value branches.** Funding/basis and Deribit options RV remain conditional only. Their first checks are named instruments, point-in-time completeness, hedge/legging/borrow/margin/access terms, and conservative all-in residual-cost screens. Broad stale-quote and unspecified FX lead-lag forms were rejected before replay as underspecified, not canonically killed. Evidence: `M1/data/execution_envelopes.csv`, `M1/data/discrepancies.csv`, `M1/data/candidate_tuples.csv`.
- **WTI branch.** WTI volatility-transition/forced flow remains secondary pending exact contract/roll and a fixed gross-magnitude-versus-friction test. It does not inherit ES or Nasdaq evidence.
- **Market design.** Generic CME queue, generic rebate harvesting, and NOII observability-as-alpha were killed/deferred. Exact venue × instrument × order type × matching rule remains mandatory.
- **Process controls.** Best-cell/near-threshold claims, cross-venue or next-tick transfer, oracle-derived strategy metrics, duplicate branches counted as independent, proxy-universe transfer, and opaque citations are invalid evidence for promotion. The Nasdaq development tape remains development-only.

## Dynamic reallocation
The second allocation was derived after verification, not predefined. Highest alternative budget went to auction; medium budget to funding/basis; lower budget to Deribit RV; secondary budget to WTI; zero new budget to Eurex/BZX until their exact prerequisites appear. ES was preserved by policy as incumbent allocation. Follow-up questions are intentionally prerequisite-driven; no next round is predeclared.

## Kill / survivor policy
Kills apply to current formulations only unless canonical evidence records a terminal death. Existing Nasdaq continuous-book QIMB/passive/microprice kills remain closed. New research-screen kills do not mutate canonical candidate state. Missing evidence remains `BLOCKED`/`UNKNOWN`, never imputed.

## Unknowns

No ES account-level cost schedule, authorized historical sample, exact contract/roll/matching rule, ES-specific modern replication, EV(delay), passive fill/markout, or operator access class is present. Alternatives share unresolved data/access/cost and persistence constraints. No profitability claim is supported.

## Verification-driven follow-up

The reallocated follow-up did not unlock a replay branch. Auction, Hyperliquid funding/basis, and Deribit RV all remain `BLOCK`; the auction's broad ANYCAP/unspecified-order-type formulation is killed as stated, while a narrowly specified auction precursor remains possible. ES H3 remains the cheapest incumbent readiness chain; ES H1 remains separate and later. WTI is blocked in its current family-level form because contract month/roll is unspecified. Red-team controls partially pass for lineage/multiplicity, selector freeze, and oracle/leakage handling; survivorship, citation scope, and horizon/regime transfer remain blocked.

Budget was reallocated again toward primary-citation resolution and point-in-time universe/data-access closure, not more branch/model search. Exact results and paths are in `ROUND3_FOLLOWUP.json`. No candidate changed canonical state or became promotable.

## Reproducibility

The campaign used repository evidence only; no external URLs were cited. Re-run context and exact group outputs are captured in `.research/QUESTION.md`, `.research/ROUND1_RESULTS.json`, `.research/ROUND2_REALLOCATION.json`, and `.research/ROUND3_FOLLOWUP.json`.

