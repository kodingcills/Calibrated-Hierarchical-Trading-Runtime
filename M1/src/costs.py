"""Execution-cost arithmetic.

Rules enforced here, not in prose (ASM-0011..ASM-0013):

* Fees stay in their native unit. ``bps_from_native`` refuses to convert a per-share or
  per-contract fee without a price, because that conversion would invent a number.
* A round trip sums the *verified* one-way components for the named execution styles.
* ``known_cost_floor`` sums only verified mandatory components and is a LOWER BOUND on
  costs. It is never a break-even and never an expected value.
* ``full_break_even`` returns ``None`` (UNKNOWN) unless every required component is known
  or explicitly parameterised.

Nothing in this module estimates, interpolates or defaults a missing value.
"""

from __future__ import annotations

from corpus.constants import BREAK_EVEN_COMPONENTS

UNKNOWN = None

# Conversion factors to basis points for units that need no price.
_UNIT_TO_BPS = {
    "BPS": 1.0,
    "PERCENT": 100.0,
}

# Units whose bps equivalent requires a price (per-share / per-contract economics).
PRICE_DEPENDENT_UNITS = ("USD_PER_SHARE", "USD_PER_CONTRACT", "USD")


class UnknownFee(ValueError):
    """Raised when an operation would require a value that is not evidenced."""


def unit_is_price_dependent(unit: str) -> bool:
    return unit in PRICE_DEPENDENT_UNITS


def bps_from_native(value, unit, price=None):
    """Convert a native fee value to basis points, or return UNKNOWN.

    ``value`` is the fee in ``unit``. ``price`` is required for price-dependent units.
    Returns ``None`` (UNKNOWN) rather than a guess.
    """
    if value is UNKNOWN or unit is UNKNOWN:
        return UNKNOWN
    if unit in _UNIT_TO_BPS:
        return float(value) * _UNIT_TO_BPS[unit]
    if unit in PRICE_DEPENDENT_UNITS:
        if price is UNKNOWN:
            return UNKNOWN
        if price <= 0:
            raise UnknownFee("price must be positive to convert a per-unit fee to bps")
        return float(value) / float(price) * 10_000.0
    raise UnknownFee(f"unrecognised fee unit: {unit!r}")


def one_way_fee_bps(value, unit, price=None):
    return bps_from_native(value, unit, price)


def round_trip(*legs):
    """Sum per-leg bps costs. Any unknown leg makes the round trip UNKNOWN.

    This is deliberately not a partial sum: a partial round trip would read as a complete
    one.
    """
    total = 0.0
    for leg in legs:
        if leg is UNKNOWN:
            return UNKNOWN
        total += float(leg)
    return total


def round_trip_costs(one_way_maker_bps, one_way_taker_bps, round_trip_flat_bps=UNKNOWN):
    """Return the four named round-trip costs plus the flat variant when applicable."""
    out = {
        "round_trip_maker_maker_fee_bps": round_trip(one_way_maker_bps, one_way_maker_bps),
        "round_trip_maker_taker_fee_bps": round_trip(one_way_maker_bps, one_way_taker_bps),
        "round_trip_taker_taker_fee_bps": round_trip(one_way_taker_bps, one_way_taker_bps),
    }
    if round_trip_flat_bps is not UNKNOWN:
        out["round_trip_flat_fee_bps"] = 2.0 * float(round_trip_flat_bps)
    return out


def required_round_trip_fee_bps(style, one_way_maker_bps, one_way_taker_bps):
    """Round-trip fee leg implied by an execution style, or UNKNOWN if it cannot be known.

    MIXED stays UNKNOWN: the maker/taker mix is a strategy choice that has not been made,
    so any single number would be an assumption dressed as a fact.
    """
    if style == "AGGRESSIVE":
        return round_trip(one_way_taker_bps, one_way_taker_bps)
    if style == "PASSIVE":
        return round_trip(one_way_maker_bps, one_way_maker_bps)
    if style == "AUCTION":
        return round_trip(one_way_taker_bps, one_way_maker_bps)
    return UNKNOWN


def known_cost_floor(components: dict):
    """Lower bound on cost from verified mandatory components.

    ``components`` maps component name -> verified native value. Unknown (``None``)
    components are excluded from the sum and returned in the missing list. The caller must
    present the result as a floor, never as break-even.
    """
    known = {k: v for k, v in components.items() if v is not UNKNOWN}
    missing = sorted(k for k, v in components.items() if v is UNKNOWN)
    if not known:
        return {"floor_value": UNKNOWN, "known_components": [], "missing_components": missing}
    return {"floor_value": sum(float(v) for v in known.values()),
            "known_components": sorted(known),
            "missing_components": missing}


def full_break_even(components: dict):
    """Full break-even in bps, or UNKNOWN if any required component is unknown (ASM-0013)."""
    missing = [c for c in BREAK_EVEN_COMPONENTS
               if components.get(c) is UNKNOWN or c not in components]
    if missing:
        return {"break_even_bps": UNKNOWN, "status": "BLOCKED_UNKNOWN_COMPONENTS",
                "unknown_components": missing}
    return {"break_even_bps": float(sum(components[c] for c in BREAK_EVEN_COMPONENTS)),
            "status": "COMPUTED", "unknown_components": []}


def net_return_bounds(gross_return_bps, known_cost_floor_bps):
    """Upper bound on net return given only a lower bound on cost."""
    if gross_return_bps is UNKNOWN or known_cost_floor_bps is UNKNOWN:
        return UNKNOWN
    return float(gross_return_bps) - float(known_cost_floor_bps)


def passive_utility_blocked(fill_probability, markout_bps):
    """Passive expected utility requires both terms; either unknown => BLOCKED."""
    if fill_probability is UNKNOWN or markout_bps is UNKNOWN:
        return {"expected_passive_utility_bps": UNKNOWN, "status": "BLOCKED",
                "missing": [name for name, v in
                            (("P(fill|queue,state)", fill_probability),
                             ("E(markout|fill,state)", markout_bps)) if v is UNKNOWN]}
    return {"expected_passive_utility_bps": float(fill_probability) * float(markout_bps),
            "status": "COMPUTED", "missing": []}
