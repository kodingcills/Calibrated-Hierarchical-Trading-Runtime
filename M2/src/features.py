"""Feature definitions for the queue-imbalance candidate.

Only the canonical primary feature plus a small set of purely diagnostic
quantities live here. The canonical feature is frozen by the M1 candidate
specification (``m2_test_contract.signal``):

    I(t) = (Q_bid(t) - Q_ask(t)) / (Q_bid(t) + Q_ask(t))

with ``Q_bid``/``Q_ask`` the displayed quantity at the best bid/ask. It is
computed only when both sides are valid and the denominator is positive.

Prices are carried as ITCH ``Price(4)`` raw integers: one cent is 100 raw units.
Midpoints are carried as ``mid2 = bid + ask`` raw units (exactly twice the
midpoint) so that no floating-point equality is ever applied to a price level.
"""

from __future__ import annotations

from typing import Optional, Sequence

# Values used where a quantity could not be computed. Kept explicit so that a
# missing value can never be confused with a computed zero.
MISSING_RAW = -1


def imbalance(q_bid: int, q_ask: int, require_denominator_positive: bool = True) -> Optional[float]:
    """Canonical queue imbalance; ``None`` when the state is not computable."""
    if q_bid is None or q_ask is None:
        return None
    if q_bid < 0 or q_ask < 0:
        return None
    denominator = q_bid + q_ask
    if require_denominator_positive and denominator <= 0:
        return None
    if denominator == 0:
        return None
    return (q_bid - q_ask) / denominator


def mid2(best_bid_raw: int, best_ask_raw: int) -> int:
    """Twice the midpoint, in raw price units, as an exact integer."""
    return best_bid_raw + best_ask_raw


def spread_raw(best_bid_raw: int, best_ask_raw: int) -> int:
    return best_ask_raw - best_bid_raw


def spread_in_ticks(spread_raw_units: int, tick_raw: int = 100) -> float:
    """Spread expressed in ticks. Exact when the spread is a whole number of ticks."""
    return spread_raw_units / tick_raw


def is_one_tick(spread: int, tick_raw: int = 100) -> bool:
    """Integer test for 'quoted spread equals exactly one tick'."""
    return spread == tick_raw


def symbol_eligible_price_floor(best_bid_raw: int, best_ask_raw: int, floor_raw: int) -> bool:
    """Candidate spec eligibility: price floor applied to the quoted midpoint."""
    return mid2(best_bid_raw, best_ask_raw) >= 2 * floor_raw


def bin_edges(configuration: dict) -> list[float]:
    return list(configuration["imbalance"]["bins"]["edges"])


def bin_index(value: float, edges: Sequence[float]) -> int:
    """Ex-ante fixed bin index for an imbalance value.

    Bins are left-closed, right-open, except the last which is closed:
    ``[e0,e1) ... [e_{n-1}, e_n]``. Returns -1 when the value is outside the
    declared support (which would itself be a defect, since the canonical
    imbalance is bounded on [-1, 1]).
    """
    if value is None:
        return -1
    n = len(edges) - 1
    if value < edges[0] or value > edges[-1]:
        return -1
    if value == edges[-1]:
        return n - 1
    for index in range(n):
        if edges[index] <= value < edges[index + 1]:
            return index
    return -1


def bin_label(index: int, edges: Sequence[float]) -> str:
    if index < 0:
        return "out_of_support"
    left = edges[index]
    right = edges[index + 1]
    closing = "]" if index == len(edges) - 2 else ")"
    return f"[{left:.1f},{right:.1f}{closing}"
