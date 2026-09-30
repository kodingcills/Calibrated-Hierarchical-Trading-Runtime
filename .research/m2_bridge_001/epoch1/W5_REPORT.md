# W5 — Economic-envelope arithmetic (GOAL-M2-BRIDGE-001, Epoch 1)

Status: complete. `python3 -m unittest M2.tests.test_envelope -v` → **38 tests, OK** (2026-09-29).
Artefacts: `M2/src/envelope.py` (new), `M2/tests/test_envelope.py` (new). No existing module,
ledger or frozen artefact was modified. No data purchase, no credentials, no outcome inspection.

## API summary (`M2/src/envelope.py`)

Units: `USD`, `USD_PER_SHARE`, `USD_PER_CONTRACT`, `bps`, `TICKS`, `FUNDING_RATE`,
`PCT_OF_TRADE_VALUE`, `USD_PER_MILLION_OF_SALES`, `MULTIPLIER_OF_COMMISSION`.

| Object | Purpose |
|---|---|
| `Basis(quantity, price_usd, multiplier, tick_value_usd, notional_usd, commission_usd)` | Every input a conversion may need; a `None` field is *unknown*, never defaulted. `Basis.notional()` = explicit notional, else `qty*price*multiplier`. |
| `to_usd(value, unit, basis)` / `from_usd(usd, unit, basis)` / `convert(value, from, to, basis)` | Unit-safe normalisation. Raises `MissingUnitInput` when the price, tick value, multiplier, notional or commission it needs is unknown; `UnsupportedUnitConversion` for an unknown unit. |
| `Provenance(source_id, url, publisher, access_date, effective_period, quote, status)` | Per-item provenance; `verified()` requires source id + url + access date + `VERIFIED`. |
| `CostItem(id, name, unit, value, side, provenance, mandatory, varies_with_{volume,staking,account_state}, unavoidable_on_frozen_path, justified_unavoidable)` | One charge in one unit. `cost_class()` → `STRUCTURAL_C0` / `UNRESOLVED_C1`. `assert_c0(item)` is the only gate into C0. |
| `Envelope(items)` | `structural_c0_usd(basis)`, `unresolved_c1_total_usd(basis)` (→ `None` if unbounded), `unresolved_c1_known_usd(basis)`, `unresolved_c1_items()`, `c0_provenance()`. |
| `envelope_from_ledger(ledger, regime)` | Read-only mapping of `cost_ledger_v1.json` line items; primary-verified ⇒ eligible for C0, broker pass-through/page-only ⇒ C1. |
| `break_even_residual(g, C0)` | `C* = g − C0`. |
| `c1_sensitivity(g, C0, levels)` | `C*` across caller-supplied C1 levels, `distribution_assumption: "NONE"`; no probability model invented. |
| `midpoint_markout_friction(S_entry, S_exit)` / `_bps` | `½S_entry + ½S_exit` from **OBSERVED** spreads; `None` or negative spread is refused. |
| `auction_executable_gross(signal, best_bid, best_ask, closing_cross_price, reference_price=None)` | Positive ⇒ entry at post-15:55 ask, exit at Closing Cross; negative ⇒ entry at bid, cover at Closing Cross. `entry_spread_embedded=True`; `N/O/P` and any other code raise. `gross_bps=None` without a reference price (never a silent per-share→bps conversion). |
| `funding_cashflow(rate, notional, position)` | Signed: positive rate ⇒ short `+rate·notional`, long `−rate·notional`. |
| `perp_leg(...)` / `two_leg_net(legs)` / `round_trip_usd(entry, exit)` | Per-side vs round-trip fees, funding sign, two-leg aggregation. |
| `classify_materiality(g, lo, hi, C0)` | The preregistered rule (below). |
| `significance_against_zero(estimate, se)` | Reported quantity only, `role: REPORTED_ONLY`; not an argument of `classify_materiality`. |

### The C0 / C1 admission rule (exact)
`STRUCTURAL_C0` requires **all** of: value known; unit known; `mandatory`; provenance `verified()`;
and **not** (`varies_with_volume ∨ varies_with_staking ∨ varies_with_account_state`) — unless the
frozen implementation sets `unavoidable_on_frozen_path` **and** records `justified_unavoidable`.
A variable published tier is therefore returned as `reference_path_scenario(...)`
(`scenario_role: REFERENCE_EXECUTION_PATH`) with its unresolved component left in C1. A fee value
carried in a currency unit is never automatically C0; an unknown value is never zero
(`unresolved_c1_total_usd` returns `None`, and a C1 item whose USD needs a missing basis input, e.g.
`MULTIPLIER_OF_COMMISSION` without a commission, is reported under `unevaluated_item_ids`).

## Unit table (what each unit needs, and when a conversion is refused)

| Unit | Meaning | Needs for USD | Refused when |
|---|---|---|---|
| `USD` | already absolute | — | value is `None` |
| `USD_PER_SHARE` | USD per share | `quantity` | quantity unknown |
| `USD_PER_CONTRACT` | USD per contract | `quantity` | quantity unknown |
| `TICKS` | contract ticks | `quantity`, `tick_value_usd` | either unknown |
| `bps` / `PCT_OF_TRADE_VALUE` | fraction of notional (1e-4 / 1e-2) | positive notional | notional unknown/zero; also when crossing a contract-scaled unit without `multiplier` |
| `USD_PER_MILLION_OF_SALES` | per $1,000,000 of sales (1e-6) | positive notional | notional unknown/zero |
| `FUNDING_RATE` | fraction of notional per interval | positive notional (USD) | notional unknown; converts to `bps` directly (×10000) |
| `MULTIPLIER_OF_COMMISSION` | × commission | `commission_usd` | commission unknown |

Ratio units convert among themselves directly. `USD_PER_SHARE → bps` needs **only** the price;
`USD_PER_CONTRACT → bps` and `TICKS → bps` additionally require `multiplier`, because the contract
notional is unknown and is never assumed to be one. Per-share, bps and ticks are never silently
interchanged.

## Verdict matrix (`classify_materiality(g, lo, hi, C0)`)

| Condition (evaluated in order) | Verdict | Tested boundary |
|---|---|---|
| `g <= 0` | `KILL_MATERIALITY` | `g = 0`, `g < 0` |
| `hi <= C0` | `KILL_MATERIALITY` | `hi == C0` ⇒ KILL |
| `lo > C0` | `SURVIVE_PROVISIONAL` | `lo == C0` ⇒ not SURVIVE |
| else | `INDETERMINATE` | interval straddles C0 |
| `g<=0` while `lo>C0` | `KILL_MATERIALITY` | rule order (KILL first) |

`[lo, hi]` is sorted defensively. `c_star_usd = g − C0` is returned with every verdict.
Statistical significance against zero is returned separately (`significance_against_zero`) and is
explicitly flagged `significance_is_decision_criterion: false`.

## C0 / C1 as mapped from the existing `M2/config/cost_ledger_v1.json` (read-only)

`STRUCTURAL_COST_FLOOR` — C0 (all primary-verified, non-variable, mandatory):
- `nasdaq_remove_liquidity_fee` $0.0030/share both sides; Nasdaq Trader price list, access 2026-09-22,
  `retrieval_status: PRIMARY_EXCHANGE_PAGE_RETRIEVED_2026-09-22_AND_REPO_VERIFIED`, base "All other
  firms" tier with no volume qualification, effective date undated on the retrieved page.
- `sec_section_31_fee` $20.60 per $1,000,000 of sales; SEC Release 34-104909 via Federal Register,
  access 2026-09-22, effective 2026-04-04 (`PRIMARY_REGULATOR_SOURCE_VERIFIED`).
- `finra_trading_activity_fee` $0.000195/share sold, max $9.79/order; SEC Release 34-101696 via
  Federal Register, access 2026-09-22, effective 2026-01-01
  (`PRIMARY_SRO_FILING_VERIFIED_WITH_LIVE_PAGE_DISCREPANCY`; the filed 2026 step is encoded).

C1, per branch (kept unresolved; no value invented):
- Auction: `databento_xnas_mbo_data_cost` (UNKNOWN) and `nasdaq_historical_itch_license_cost`
  (UNKNOWN), both operating economics; both force `unresolved_c1_total_usd → None`.
- Equity reference path (both regimes): `nscc_dtc_clearing_fee` ($0.00020/share, broker
  pass-through only; DTCC charges per account-month/item, underlying cost UNKNOWN),
  `cat_fee` (broker-page only), `nyse_pass_through_fee` and `finra_pass_through_fee`
  (multipliers of commission, broker-page only → `unevaluated_item_ids` without a commission).
- Broker schedules `ibkr_pro_fixed` / `ibkr_pro_tiered`: volume/account-dependent rate cards, so by
  the rule above they are reference execution path scenarios, not C0; the module's standard API
  cannot admit them, and this pass did not add them to the ledger.
- ES branch: CME/FCM charges are **not** primary-verifiable from this environment (CME's pages
  return 403), so no CME fee is admitted as C0 or asserted as a number; they remain C1, consistent
  with the frozen ES formulation.
- Branch C: Hyperliquid / Binance USDT-M taker fees depend on volume/staking/account state, so they
  are C1 reference-path scenarios. Funding is handled as a signed cashflow, not a cost guess.

## Evidence
- `python3 -m unittest M2.tests.test_envelope -v` — 38 tests, OK (includes the two ledger-integration
  tests that read `M2/config/cost_ledger_v1.json` and assert the C0 set equals the regime's declared
  floor plus that operating-economics unknowns never reach C0).
- `git status --porcelain` after the work: only `M2/src/envelope.py`, `M2/tests/test_envelope.py`
  (and peers' unrelated new files) are new; no frozen artefact is modified.
