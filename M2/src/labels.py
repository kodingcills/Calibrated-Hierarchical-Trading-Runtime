"""Label definitions for the M2-0 pass.

Two labels are computed, both by exact causal as-of logic:

1. Future mid-price return on the preregistered horizon grid (100/250/500/1000 ms)
   plus its direction. Zero-return observations are preserved, never dropped.
2. The direction of the next actual mid-price change after the decision time.

Representation: the midpoint is carried as ``mid2 = best_bid + best_ask`` in raw
``Price(4)`` units, i.e. exactly twice the midpoint. This keeps every price
comparison in integer arithmetic. The bps conversion is invariant to the factor
of two, because it is a ratio:

    r_Delta = 10000 * (mid2_future - mid2_decision) / mid2_decision

A future state that does not exist is *not* replaced by interpolation or by the
decision-time quote. It is marked with a status code and the label is left null.
"""

from __future__ import annotations

MISSING_RAW = -1

# label_status codes
LABEL_OK = 0
LABEL_NO_FUTURE_STATE = 1  # no valid two-sided book at or after t + Delta
LABEL_NO_DECISION_STATE = 2  # decision state itself was not two-sided
LABEL_SESSION_ENDED = 3  # horizon extends past the evaluated session
LABEL_UNAVAILABLE = 4  # reserved: never silently filled

DIRECTION_DOWN = -1
DIRECTION_FLAT = 0
DIRECTION_UP = 1
DIRECTION_UNRESOLVED = -2


def future_return_bps(mid2_at_decision: int, mid2_future: int) -> float:
    """Return in basis points from the exact integer representation."""
    return 10000.0 * (mid2_future - mid2_at_decision) / mid2_at_decision


def direction(mid2_at_decision: int, mid2_future: int) -> int:
    if mid2_future > mid2_at_decision:
        return DIRECTION_UP
    if mid2_future < mid2_at_decision:
        return DIRECTION_DOWN
    return DIRECTION_FLAT


def next_mid_move_direction(mid2_at_decision: int, mid2_at_change: int) -> int:
    """Direction of the next real mid-price change (never zero by construction)."""
    return direction(mid2_at_decision, mid2_at_change)


def directional_hit(side: int, mid2_at_decision: int, mid2_future: int) -> bool:
    """True when the realised direction matches the assumed side (+1 long, -1 short)."""
    return side * (mid2_future - mid2_at_decision) > 0


def bps_from_dollars_per_share(dollars_per_share: float, price_usd: float) -> float:
    """Convert a per-share cost into basis points of notional at a given price."""
    return 10000.0 * dollars_per_share / price_usd


def raw_to_usd(raw_price: int, price_scale: int = 10000) -> float:
    return raw_price / price_scale


def mid_usd(mid2_raw: int, price_scale: int = 10000) -> float:
    return (mid2_raw / 2.0) / price_scale
