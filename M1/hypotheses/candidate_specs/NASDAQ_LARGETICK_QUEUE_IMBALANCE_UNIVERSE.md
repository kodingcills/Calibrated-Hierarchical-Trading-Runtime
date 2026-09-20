# Candidate spec: Nasdaq large-tick queue imbalance, H2, aggressive

Machine-readable twin: `NASDAQ_LARGETICK_QUEUE_IMBALANCE_UNIVERSE.json` (this document is a rendering;
the JSON is authoritative and is what the gate engine reads).

Candidate: `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` · Universe rule: `NASDAQ-LARGETICK-QIMB-UNIV-v1` ·
Status: APPROVED, frozen 2026-09-20 **before any M2 outcome was inspected**.

## 1. Unit of analysis

`<preregistered Nasdaq large-tick universe, Nasdaq, H2 100 ms–1 s, queue imbalance, aggressive>`.

A universe rule is used rather than a single ticker. A fixed ticker would have to be chosen on some
criterion, and the only criteria available today are structural (fine) or performance-based
(forbidden). The rule below is deterministic and causal, so it can be applied identically in every
fold of the M2 walk-forward.

## 2. What "large-tick" means operationally

**Primary:** median quoted spread over the lookback window equals exactly one tick, **and** at least
`THETA = 0.50` of valid book observations have a quoted spread of exactly one tick.

**THETA is a preregistered design parameter, not a sourced value.** The literature does not publish a
fraction-of-time threshold. Gould & Bonart define large-tick by *relative tick size* (a price screen:
maximum trade price below $50 in 2014) and report mean spreads of $0.012–$0.015 against a $0.01 tick
for their large-tick names — their sample sits at roughly one tick on average, but they never state
how often that holds. THETA = 0.50 is the minimal structural statement the mechanism needs: queue
depletion at the touch governs price moves only when the spread is pinned at one tick more often
than not. It is frozen before M2 results and may not be tuned on them.

**Not used:** the $50 price screen as a binding selector (it selected a sample in 2014; $50 then is
not $50 now). The fraction of the eligible universe that would also pass that screen is **reported as
a cross-check only**.

**Rejected alternatives:** price-only definitions; any threshold chosen by maximising universe size,
event count, or observed predictiveness.

## 3. Eligibility

| rule | value | class |
|---|---|---|
| venue | Nasdaq must be the **primary** trading venue | data-quality (single-venue book reconstruction; the same restriction Gould & Bonart imposed) |
| security type | US common stock ordinary classes only; no ETF/ETN/ADR/preferred/warrant/right/unit/CEF/SPAC-shell/when-issued/sub-penny | market-structure (different tick, spread, corporate-action and listing regimes) |
| price floor | ≥ $1.00 | market-structure (sub-penny regime boundary) |
| liquidity | top **decile** of trailing 60-day median daily dollar volume among otherwise eligible names | relative percentile, so no absolute level is invented; same family as the literature's top-5-by-volume rule |
| history | ≥ 120 trading days of continuous listing and coverage (2× the lookback) | data-quality |
| coverage | valid order-level book observations on ≥ 90% of lookback trading days | data-quality |
| corporate actions | excluded for the cycle if an action falls inside the lookback | market-structure (spread/tick comparability) |
| halts | excluded for the cycle if halt frequency exceeds the eligible-set 95th percentile | execution (discontinuous book state, unusable fill semantics) |
| performance | **never** an exclusion criterion | prohibited |

**Sample-size feasibility (not optimisation):** ≥ 5 securities and ≥ 100,000 pooled one-tick-ahead
events per month. Basis: the literature's per-stock design used 25,200 events per stock-year, so the
pooled floor exceeds it by an order of magnitude. If the rule yields less, that is reported as an
underpowered test — not repaired by widening the rule.

## 4. Selection timing and anti-leakage

- **Selection date:** first trading day of each month T, using only data timestamped strictly before
  the open of T's first trading day.
- **Lookback:** 60 trading days ending the last trading day before T.
- **Rebalance:** monthly.
- **Evaluation start:** the trading day after selection; no lookback observation enters the
  evaluation set.
- **Point-in-time membership:** required. Listing status, symbol and security type must come from a
  point-in-time reference. If that cannot be obtained, the branch is **BLOCKED on KG2** rather than run
  on survivor-biased symbols. Current status: `REQUIRED_DATA_NOT_SECURED`.
- **Survivorship:** delisted, acquired, renamed and halted securities stay in the universe for the
  period in which they were eligible.
- **Frozen rule:** any change to a threshold creates a new rule version and a new candidate id.

## 5. Relation to the verified literature

| dimension | Gould & Bonart (verified) | this rule |
|---|---|---|
| venue | Nasdaq, Nasdaq as primary venue | same requirement, same reason |
| sample | 10 liquid stocks; top 5 by 2014 dollar volume with max trade price < $50 (large-tick) and top 5 with min trade price > $100 (small-tick) | top-decile dollar-volume rank plus a tick-anchored spread criterion; no price screen |
| large-tick characterisation | relative tick size via price; mean spread $0.012–$0.015 vs $0.01 tick | fraction of observations at exactly one tick ≥ THETA, with median spread == one tick |
| target | direction of the next mid-price movement (one-tick-ahead), indicator y | same target, plus an explicit H2 delay grid |
| sample period | calendar year 2014, 10:00–15:30 each of 252 trading days | whatever window the procured data supports; the rule never assumes 2014 conditions |
| limitations carried forward | single venue; 2014; predictive/gross only; no costs, fills or P&L; horizon expressed as a move rather than elapsed time | identical limitations are recorded on `EVD-0064` and `EVD-0066`; nothing about 2014 coefficients or magnitudes is claimed to transfer |

**The claim this justifies:** the verified evidence justifies *testing* queue imbalance on an
appropriately defined Nasdaq large-tick universe. It does **not** prove modern profitability, and no
coefficient, decay or effect size is carried across.

## 6. KG5 test contract (falsifiability)

- **State:** causal Nasdaq order-book state; best bid/ask prices and best-queue sizes at decision time;
  no post-timestamp information.
- **Signal:** $I(t) = \dfrac{n^{b}(t)-n^{a}(t)}{n^{b}(t)+n^{a}(t)}$ at the best quotes, sampled at the
  decision time (Equation 7 of the verified paper), never from inside the forecast window.
- **Action:** aggressive directional trade when the signal exceeds the preregistered threshold,
  otherwise abstain.
- **Horizons:** 100, 250, 500 and 1000 ms — a grid inside H2, reported in full; no single horizon may be
  selected after seeing results.
- **Nulls:** constant ½ (the literature's reference model); direction permutation; timestamp-preserving
  side randomisation; same-information logistic baseline; deterministic imbalance threshold; no-trade;
  exposure-matched random side.
- **Primary predictive metric:** out-of-sample AUC of next-move direction, with log loss and reliability
  diagnostics alongside.
- **Primary economic metric:** execution-aware net utility after the **locked** cost configuration —
  currently UNKNOWN, because the equity fee/sponsor lock is incomplete (`UNK-0005`, `UNK-0033`).
- **Split:** sealed holdout; purged, month-blocked walk-forward with an embargo equal to the longest
  horizon; the universe rule is re-applied inside each fold using only that fold's lookback.
- **Kill criteria (stated before results):** no robust OOS information; effect disappears under the
  delay grid; measured gross edge cannot clear the locked cost envelope; a same-information logistic or
  deterministic-threshold baseline matches or beats it; instability across consecutive months in a
  majority of folds.
- **No numeric performance thresholds are set here.** The literature's 50–60% improvement over its own
  null is a reference point from a different era and cost regime, not a project threshold; numeric kill
  levels are set only after the cost lock and the delay sweep give a statistical basis.