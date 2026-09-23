"""Implementation of the frozen universe rule ``NASDAQ-LARGETICK-QIMB-UNIV-v1``.

The rule is defined by ``M1/hypotheses/candidate_specs/NASDAQ_LARGETICK_QUEUE_IMBALANCE_UNIVERSE.json``
(status APPROVED, frozen 2026-09-20 before any M2 outcome inspection). This module
implements it; it does not reinterpret it. Parameters are passed in from the
configuration, whose values are copies of the frozen spec.

Two things the rule requires and this pass cannot supply are made explicit rather
than assumed:

* a 60-trading-day causal lookback over order-level book state;
* a point-in-time listing / security-type / corporate-action / halt reference.

When they are absent the branch is BLOCKED (the spec's own wording:
"if point-in-time membership cannot be obtained, the branch is BLOCKED on KG2
rather than run on survivor-biased symbols"). ``blocked_membership`` produces the
schema-conformant membership artifact with ``eligible`` left null and an explicit
reason code, plus whatever variables are computable from the sample day, flagged
as reporting-only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

# Reason codes, in the frozen order the rule applies them.
REASON_NOT_NASDAQ_LISTED = "NOT_NASDAQ_LISTED"
REASON_NON_COMMON_SECURITY_TYPE = "NON_COMMON_SECURITY_TYPE"
REASON_PRICE_BELOW_FLOOR = "PRICE_BELOW_1_USD"
REASON_COVERAGE = "COVERAGE_BELOW_90PCT_OF_LOOKBACK_DAYS"
REASON_HISTORY = "HISTORY_BELOW_120_TRADING_DAYS"
REASON_CORPORATE_ACTION = "CORPORATE_ACTION_INSIDE_LOOKBACK"
REASON_HALT_FREQUENCY = "HALT_FREQUENCY_ABOVE_95TH_PERCENTILE"
REASON_NOT_TOP_DECILE = "LIQUIDITY_OUTSIDE_TOP_DECILE"
REASON_ELIGIBLE = "ELIGIBLE"

BLOCKED_PIT = "BLOCKED_POINT_IN_TIME_REFERENCE_NOT_SECURED"
BLOCKED_LOOKBACK = "BLOCKED_ORDER_LEVEL_LOOKBACK_UNAVAILABLE"

PROHIBITED_INPUT_TOKENS = (
    "future",
    "evaluation_period",
    "post_selection",
    "pnl",
    "sharpe",
    "hit_rate",
    "signal_coefficient",
    "predictiveness",
    "markout",
    "profit",
)


class LeakageError(RuntimeError):
    """Raised when selection inputs contain evaluation-period information."""


@dataclass(frozen=True)
class RuleParameters:
    theta: float = 0.50
    liquidity_lookback_trading_days: int = 60
    minimum_history_trading_days: int = 120
    coverage_min_fraction: float = 0.90
    price_floor_usd: float = 1.00
    minimum_universe_size: int = 5
    minimum_pooled_events_per_month: int = 100_000
    halt_exclusion_percentile: int = 95
    tick_raw: int = 100
    liquidity_decile_fraction: float = 0.10


@dataclass
class SymbolObservation:
    """Ex-ante observables for one security over the lookback window."""

    symbol: str
    nasdaq_primary: bool = True
    common_stock: bool = True
    price_ok: bool = True
    median_dollar_volume: float = 0.0
    coverage_fraction: float = 0.0
    history_trading_days: int = 0
    halts_in_lookback: int = 0
    corporate_action_in_lookback: bool = False
    spread_observations: list[int] = field(default_factory=list)


@dataclass
class MembershipRow:
    symbol: str
    eligible: bool | None
    reason_code: str
    median_dollar_volume: float | None
    coverage_fraction: float | None
    history_trading_days: int | None
    halts_in_lookback: int | None
    corporate_action_in_lookback: bool | None
    median_spread_raw: float | None
    fraction_at_one_tick: float | None
    spread_observations: int
    reporting_only: bool = False


@dataclass
class RuleResult:
    rows: list[MembershipRow]
    eligible_count: int
    universe_size_feasible: bool
    pooled_events_sufficient: bool


class LargeTickRule:
    """The primary large-tick definition: median spread at one tick AND theta."""

    def __init__(self, theta: float, tick_raw: int = 100) -> None:
        self.theta = theta
        self.tick_raw = tick_raw
        self.observations: list[int] = []

    def observe_spread(self, spread_raw: int) -> None:
        self.observations.append(spread_raw)

    def median_spread_raw(self) -> float | None:
        return median(self.observations)

    def median_is_one_tick(self) -> bool:
        value = self.median_spread_raw()
        return value is not None and value == self.tick_raw

    def fraction_at_one_tick(self) -> float | None:
        if not self.observations:
            return None
        return sum(1 for spread in self.observations if spread == self.tick_raw) / len(self.observations)

    def is_large_tick(self) -> bool:
        fraction = self.fraction_at_one_tick()
        return self.median_is_one_tick() and fraction is not None and fraction >= self.theta


def median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def percentile(values: Sequence[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (percent / 100.0) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(ordered[int(rank)])
    weight = rank - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def top_decile_by_dollar_volume(
    observations: Iterable[SymbolObservation], fraction: float = 0.10
) -> list[SymbolObservation]:
    """Top decile of median daily dollar volume, by relative rank only."""
    eligible = [row for row in observations if row.price_ok]
    if not eligible:
        return []
    ranked = sorted(eligible, key=lambda row: (-row.median_dollar_volume, row.symbol))
    count = max(1, math.ceil(len(ranked) * fraction))
    return ranked[:count]


def assert_causal_inputs(variables: dict, parameters: RuleParameters) -> None:
    """Refuse any selection input that could contain evaluation-period information."""
    for name in variables:
        lowered = str(name).lower()
        for token in PROHIBITED_INPUT_TOKENS:
            if token in lowered:
                raise LeakageError(
                    f"selection input {name!r} matches prohibited token {token!r}: "
                    "the frozen rule may not consume evaluation-period information"
                )


def apply_rule(
    observations: Sequence[SymbolObservation],
    parameters: RuleParameters,
    halt_threshold: float | None = None,
) -> RuleResult:
    """Apply the frozen rule in its frozen order and label every decision.

    The liquidity rank is applied last because it is relative to the set that
    passes the other eligibility rules.
    """
    for row in observations:
        assert_causal_inputs({"median_dollar_volume": row.median_dollar_volume}, parameters)

    if halt_threshold is None:
        halt_threshold = percentile([row.halts_in_lookback for row in observations], parameters.halt_exclusion_percentile)

    survivors: list[SymbolObservation] = []
    rows: list[MembershipRow] = []
    for row in observations:
        reason = ""
        if not row.nasdaq_primary:
            reason = REASON_NOT_NASDAQ_LISTED
        elif not row.common_stock:
            reason = REASON_NON_COMMON_SECURITY_TYPE
        elif not row.price_ok:
            reason = REASON_PRICE_BELOW_FLOOR
        elif row.coverage_fraction < parameters.coverage_min_fraction:
            reason = REASON_COVERAGE
        elif row.history_trading_days < parameters.minimum_history_trading_days:
            reason = REASON_HISTORY
        elif row.corporate_action_in_lookback:
            reason = REASON_CORPORATE_ACTION
        elif halt_threshold is not None and row.halts_in_lookback > halt_threshold:
            reason = REASON_HALT_FREQUENCY
        if reason:
            rows.append(_membership_row(row, False, reason, parameters))
        else:
            survivors.append(row)

    decile = {row.symbol for row in top_decile_by_dollar_volume(survivors, parameters.liquidity_decile_fraction)}
    for row in survivors:
        if row.symbol in decile:
            rows.append(_membership_row(row, True, REASON_ELIGIBLE, parameters))
        else:
            rows.append(_membership_row(row, False, REASON_NOT_TOP_DECILE, parameters))

    rows.sort(key=lambda item: item.symbol)
    eligible_count = sum(1 for item in rows if item.eligible)
    return RuleResult(
        rows=rows,
        eligible_count=eligible_count,
        universe_size_feasible=eligible_count >= parameters.minimum_universe_size,
        pooled_events_sufficient=False,  # event counts need the evaluation period
    )


def _membership_row(
    observation: SymbolObservation, eligible: bool, reason: str, parameters: RuleParameters
) -> MembershipRow:
    rule = LargeTickRule(parameters.theta, parameters.tick_raw)
    for spread in observation.spread_observations:
        rule.observe_spread(spread)
    return MembershipRow(
        symbol=observation.symbol,
        eligible=eligible,
        reason_code=reason,
        median_dollar_volume=observation.median_dollar_volume,
        coverage_fraction=observation.coverage_fraction,
        history_trading_days=observation.history_trading_days,
        halts_in_lookback=observation.halts_in_lookback,
        corporate_action_in_lookback=observation.corporate_action_in_lookback,
        median_spread_raw=rule.median_spread_raw(),
        fraction_at_one_tick=rule.fraction_at_one_tick(),
        spread_observations=len(observation.spread_observations),
    )


def blocked_membership_rows(
    symbols: Sequence[dict],
    evaluation_date: str,
    sample_day_spreads: dict[str, list[int]] | None = None,
    parameters: RuleParameters | None = None,
) -> list[dict]:
    """Membership rows for a run where the rule's inputs are not procured.

    ``eligible`` is null (never false): the frozen rule has not been evaluated,
    because both required inputs are missing. The sample-day spread statistics are
    reported beside the row and are flagged ``reporting_only``, which is exactly
    the role the frozen spec gives the price-screen cross-check.
    """
    parameters = parameters or RuleParameters()
    sample_day_spreads = sample_day_spreads or {}
    rows = []
    for entry in symbols:
        rule = LargeTickRule(parameters.theta, parameters.tick_raw)
        for spread in sample_day_spreads.get(entry["symbol"], []):
            rule.observe_spread(spread)
        rows.append(
            {
                "evaluation_date": evaluation_date,
                "symbol": entry["symbol"],
                "eligible": None,
                "reason_codes": f"{BLOCKED_PIT}|{BLOCKED_LOOKBACK}",
                "median_dollar_volume": None,
                "coverage_fraction": None,
                "history_trading_days": None,
                "halts_in_lookback": None,
                "corporate_action_in_lookback": None,
                "median_spread_ticks_sample_day": (
                    None
                    if rule.median_spread_raw() is None
                    else rule.median_spread_raw() / parameters.tick_raw
                ),
                "fraction_one_tick_sample_day": rule.fraction_at_one_tick(),
                "spread_observations_sample_day": len(rule.observations),
                "lookback_start": None,
                "lookback_end": None,
                "membership_status": BLOCKED_PIT,
                "reporting_only": True,
            }
        )
    return rows


def audit_rows(rows: Sequence[dict]) -> list[dict]:
    """Eligible/excluded counts by reason code, for ``universe_audit.csv``."""
    counts: dict[str, int] = {}
    for row in rows:
        for code in str(row["reason_codes"]).split("|"):
            counts[code] = counts.get(code, 0) + 1
    return [
        {"reason_code": code, "symbols": count}
        for code, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
