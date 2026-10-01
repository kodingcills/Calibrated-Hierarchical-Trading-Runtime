"""Broker-agnostic deterministic materiality arithmetic for the W5 envelope.

This module owns the *arithmetic* of the economic-materiality decision and nothing
else: unit-safe cost normalisation, the structural/unresolved cost split (``C0`` /
``C1``), the break-even residual ``C* = g - C0``, the observed-spread friction term,
the executable-capture gross for the Nasdaq closing auction, two-leg perp pairing
and the preregistered uncertainty-vs-``C0`` classification. No strategy logic, no
outcome computation, no probability model for ``C1``.

Design rules enforced here:

* Every cost value carries a unit, a provenance record (source id/url/access date/
  effective period) and a class. A cost is never a single opaque number.
* A published fee tier that varies with volume, staking or account state is **not**
  automatically structural: it becomes a *reference execution path scenario* and its
  unresolved component stays in ``C1`` unless the frozen implementation justifies it
  as unavoidable on that path.
* A missing input is never defaulted. Converting to a unit whose required input
  (price, tick value, multiplier, notional, commission) is unknown raises
  :class:`MissingUnitInput`; ``C1`` with an unknown value propagates as ``None``,
  never as zero.
* Statistical significance against zero is reported as a separate quantity and is
  never an input to :func:`classify_materiality`.

The existing conventions in ``M2/src/costs.py`` and ``M2/config/cost_ledger_v1.json``
are reused: this module consumes that ledger read-only and adds no second cost store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

# ---------------------------------------------------------------------------
# Units. Every unit is distinct; a conversion that would need an unknown input is
# refused rather than fudged.
# ---------------------------------------------------------------------------

UNIT_USD = "USD"
UNIT_USD_PER_SHARE = "USD_PER_SHARE"
UNIT_USD_PER_CONTRACT = "USD_PER_CONTRACT"
UNIT_BPS = "bps"
UNIT_TICKS = "TICKS"
UNIT_FUNDING_RATE = "FUNDING_RATE"
UNIT_PCT_OF_TRADE_VALUE = "PCT_OF_TRADE_VALUE"
UNIT_PER_MILLION_OF_SALES = "USD_PER_MILLION_OF_SALES"
UNIT_MULTIPLIER_OF_COMMISSION = "MULTIPLIER_OF_COMMISSION"

# Units that measure a fraction of notional. Their value is the multiplier onto
# notional (1 bps = 1e-4, 1 percent = 1e-2, USD-per-million = 1e-6, a funding rate
# is already expressed as a fraction).
RATIO_UNITS: dict[str, float] = {
    UNIT_BPS: 1e-4,
    UNIT_PCT_OF_TRADE_VALUE: 1e-2,
    UNIT_PER_MILLION_OF_SALES: 1e-6,
    UNIT_FUNDING_RATE: 1.0,
}

UNITS_REQUIRING_QUANTITY = (UNIT_USD_PER_SHARE, UNIT_USD_PER_CONTRACT)
UNITS_REQUIRING_TICK_VALUE = (UNIT_TICKS,)
# Units whose notional depends on the contract multiplier rather than being a
# one-for-one share amount. Crossing these with a notional-relative unit requires an
# explicit multiplier; defaulting it to 1 would silently misprice a contract.
CONTRACT_SCALED_UNITS = (UNIT_USD_PER_CONTRACT, UNIT_TICKS)

# Cost classes.
CLASS_C0 = "STRUCTURAL_C0"
CLASS_C1 = "UNRESOLVED_C1"

# Provenance statuses.
STATUS_VERIFIED = "VERIFIED"
STATUS_UNVERIFIED = "UNVERIFIED"
STATUS_UNKNOWN = "UNKNOWN"

# Auction signal and ineligible NOII codes for the frozen formulation.
SIGNAL_POSITIVE = "POSITIVE"
SIGNAL_NEGATIVE = "NEGATIVE"
INELIGIBLE_NOII_CODES = ("N", "O", "P")

# Preregistered materiality verdicts.
VERDICT_KILL = "KILL_MATERIALITY"
VERDICT_SURVIVE = "SURVIVE_PROVISIONAL"
VERDICT_INDETERMINATE = "INDETERMINATE"


class EnvelopeError(Exception):
    """Base class for envelope arithmetic failures."""


class MissingUnitInput(EnvelopeError, ValueError):
    """A conversion or evaluation needs an input that is unknown; refuse, never default."""


class UnsupportedUnitConversion(EnvelopeError, ValueError):
    """The requested unit conversion is not defined for this pair of units."""


class CostClassificationError(EnvelopeError, ValueError):
    """An item was forced into a class it is not eligible for."""


# ---------------------------------------------------------------------------
# Execution basis: the facts a conversion may need.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Basis:
    """What a cost is expressed against for one order or leg.

    Any field left ``None`` is *unknown*; arithmetic that needs it raises
    :class:`MissingUnitInput` instead of assuming a value.
    """

    quantity: float | None = None
    price_usd: float | None = None
    multiplier: float | None = None
    tick_value_usd: float | None = None
    notional_usd: float | None = None
    commission_usd: float | None = None

    def notional(self) -> float | None:
        """Explicit notional, else ``quantity * price * multiplier`` (multiplier 1 if unset)."""
        if self.notional_usd is not None:
            return self.notional_usd
        if self.quantity is None or self.price_usd is None:
            return None
        multiplier = 1.0 if self.multiplier is None else self.multiplier
        return self.quantity * self.price_usd * multiplier


def _require_value(value: float | None, unit: str) -> float:
    if value is None:
        raise MissingUnitInput(f"{unit} value is UNKNOWN; an unknown cost is never treated as zero")
    return float(value)


def to_usd(value: float | None, unit: str, basis: Basis | None = None) -> float:
    """Evaluate a value in ``unit`` as USD for one order/leg of ``basis``."""
    basis = basis or Basis()
    value = _require_value(value, unit)
    if unit == UNIT_USD:
        return value
    if unit in UNITS_REQUIRING_QUANTITY:
        if basis.quantity is None:
            raise MissingUnitInput(f"quantity required to evaluate {unit} in USD")
        return value * basis.quantity
    if unit in UNITS_REQUIRING_TICK_VALUE:
        if basis.quantity is None:
            raise MissingUnitInput("quantity (contracts) required to evaluate TICKS in USD")
        if basis.tick_value_usd is None:
            raise MissingUnitInput("tick_value_usd required to evaluate TICKS in USD")
        return value * basis.quantity * basis.tick_value_usd
    if unit in RATIO_UNITS:
        notional = basis.notional()
        if notional is None:
            raise MissingUnitInput(f"notional (price and quantity) required to evaluate {unit} in USD")
        return value * RATIO_UNITS[unit] * notional
    if unit == UNIT_MULTIPLIER_OF_COMMISSION:
        if basis.commission_usd is None:
            raise MissingUnitInput("commission_usd required to evaluate MULTIPLIER_OF_COMMISSION in USD")
        return value * basis.commission_usd
    raise UnsupportedUnitConversion(f"no USD evaluation defined for unit {unit!r}")


def from_usd(usd: float, unit: str, basis: Basis | None = None) -> float:
    """Express a USD amount in ``unit`` for one order/leg of ``basis``."""
    basis = basis or Basis()
    usd = float(usd)
    if unit == UNIT_USD:
        return usd
    if unit in UNITS_REQUIRING_QUANTITY:
        if basis.quantity is None:
            raise MissingUnitInput(f"quantity required to express USD in {unit}")
        if basis.quantity == 0:
            raise MissingUnitInput(f"zero quantity cannot express USD in {unit}")
        return usd / basis.quantity
    if unit in UNITS_REQUIRING_TICK_VALUE:
        if basis.quantity is None or basis.tick_value_usd is None:
            raise MissingUnitInput("quantity and tick_value_usd required to express USD in TICKS")
        denominator = basis.quantity * basis.tick_value_usd
        if denominator == 0:
            raise MissingUnitInput("zero quantity or tick value cannot express USD in TICKS")
        return usd / denominator
    if unit in RATIO_UNITS:
        notional = basis.notional()
        if notional is None or notional == 0:
            raise MissingUnitInput(f"positive notional required to express USD in {unit}")
        return usd / (notional * RATIO_UNITS[unit])
    if unit == UNIT_MULTIPLIER_OF_COMMISSION:
        if basis.commission_usd is None or basis.commission_usd == 0:
            raise MissingUnitInput("non-zero commission_usd required to express USD in MULTIPLIER_OF_COMMISSION")
        return usd / basis.commission_usd
    raise UnsupportedUnitConversion(f"no {unit!r} expression defined for a USD amount")


def convert(value: float | None, from_unit: str, to_unit: str, basis: Basis | None = None) -> float:
    """Unit-safe conversion.

    Ratio units convert among themselves directly. A per-share cost converts to a
    ratio only when the price is known (never silently, and never through a guessed
    quantity). Everything else goes through USD and therefore refuses when the price,
    multiplier, tick value, notional or commission it needs is unknown.
    """
    basis = basis or Basis()
    value = _require_value(value, from_unit)
    if from_unit == to_unit:
        return value
    if from_unit in RATIO_UNITS and to_unit in RATIO_UNITS:
        return value * RATIO_UNITS[from_unit] / RATIO_UNITS[to_unit]
    if from_unit == UNIT_USD_PER_SHARE and to_unit in RATIO_UNITS:
        if basis.price_usd is None or basis.price_usd == 0:
            raise MissingUnitInput(f"price_usd required to convert USD_PER_SHARE to {to_unit}")
        return value / (basis.price_usd * RATIO_UNITS[to_unit])
    if from_unit in RATIO_UNITS and to_unit == UNIT_USD_PER_SHARE:
        if basis.price_usd is None:
            raise MissingUnitInput(f"price_usd required to convert {from_unit} to USD_PER_SHARE")
        return value * RATIO_UNITS[from_unit] * basis.price_usd
    notional_relative = from_unit in RATIO_UNITS or to_unit in RATIO_UNITS
    if notional_relative and (from_unit in CONTRACT_SCALED_UNITS or to_unit in CONTRACT_SCALED_UNITS):
        if basis.multiplier is None:
            raise MissingUnitInput(
                f"multiplier required to convert {from_unit} to {to_unit}: "
                "the contract notional is unknown and must not be assumed to be one"
            )
    return from_usd(to_usd(value, from_unit, basis), to_unit, basis)


def bps_to_usd(bps: float, notional_usd: float | None) -> float:
    if notional_usd is None:
        raise MissingUnitInput("notional_usd required to convert bps to USD")
    return float(bps) * 1e-4 * float(notional_usd)


def usd_to_bps(usd: float, notional_usd: float | None) -> float:
    if notional_usd is None or notional_usd == 0:
        raise MissingUnitInput("positive notional_usd required to convert USD to bps")
    return float(usd) / (1e-4 * float(notional_usd))


# ---------------------------------------------------------------------------
# Cost items, provenance and the C0/C1 rule.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provenance:
    """Where a number comes from. Blank fields mean the fact was not verified."""

    source_id: str = ""
    url: str = ""
    publisher: str = ""
    access_date: str = ""
    effective_period: str = ""
    quote: str = ""
    status: str = STATUS_UNVERIFIED

    def verified(self) -> bool:
        return (
            self.status == STATUS_VERIFIED
            and bool(self.source_id)
            and bool(self.url)
            and bool(self.access_date)
        )

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "publisher": self.publisher,
            "access_date": self.access_date,
            "effective_period": self.effective_period,
            "quote": self.quote,
            "status": self.status,
        }


@dataclass(frozen=True)
class CostItem:
    """One charge, in one unit, with one provenance record and one eligibility shape.

    ``varies_with_*`` marks a published tier whose rate depends on volume, staking or
    account state. Such an item is not structural by default: it is reported as a
    reference execution path and stays unresolved unless the frozen implementation
    justifies it as unavoidable (``unavoidable_on_frozen_path`` plus
    ``justified_unavoidable``).
    """

    id: str
    name: str
    unit: str
    value: float | None
    side: str = "both"
    provenance: Provenance = field(default_factory=Provenance)
    mandatory: bool = True
    varies_with_volume: bool = False
    varies_with_staking: bool = False
    varies_with_account_state: bool = False
    unavoidable_on_frozen_path: bool = False
    justified_unavoidable: str | None = None
    notes: str = ""

    def varies(self) -> bool:
        return self.varies_with_volume or self.varies_with_staking or self.varies_with_account_state

    def cost_class(self) -> str:
        """STRUCTURAL_C0 only when verified, mandatory, non-variable (or explicitly justified)."""
        if self.value is None or self.unit in (None, "UNKNOWN"):
            return CLASS_C1
        if not self.mandatory:
            return CLASS_C1
        if not self.provenance.verified():
            return CLASS_C1
        if self.varies() and not (self.unavoidable_on_frozen_path and self.justified_unavoidable):
            return CLASS_C1
        return CLASS_C0


def assert_c0(item: CostItem) -> CostItem:
    """Return ``item`` or raise: the single gate that admits a value into ``C0``."""
    cls = item.cost_class()
    if cls != CLASS_C0:
        raise CostClassificationError(
            f"item {item.id!r} is {cls}, not {CLASS_C0}: "
            f"value={item.value!r} unit={item.unit!r} mandatory={item.mandatory} "
            f"varies={item.varies()} verified={item.provenance.verified()}"
        )
    return item


def reference_path_scenario(item: CostItem, basis: Basis | None = None) -> dict:
    """Describe a non-structural (typically variable-tier) charge as a scenario.

    The value is reported, not admitted: the unresolved component stays in ``C1``.
    """
    row = {
        "id": item.id,
        "name": item.name,
        "unit": item.unit,
        "value": item.value,
        "class": item.cost_class(),
        "scenario_role": "REFERENCE_EXECUTION_PATH",
        "varies_with_volume": item.varies_with_volume,
        "varies_with_staking": item.varies_with_staking,
        "varies_with_account_state": item.varies_with_account_state,
        "provenance": item.provenance.as_dict(),
        "usd": None,
        "usd_status": "NOT_EVALUATED",
    }
    if item.value is not None:
        try:
            row["usd"] = to_usd(item.value, item.unit, basis or Basis())
            row["usd_status"] = "EVALUATED"
        except MissingUnitInput as exc:
            row["usd_status"] = f"MISSING_INPUT: {exc}"
    return row


@dataclass(frozen=True)
class Envelope:
    """A named set of cost items with the C0/C1 split kept explicit."""

    envelope_id: str
    items: tuple[CostItem, ...]

    def c0_items(self) -> list[CostItem]:
        return [item for item in self.items if item.cost_class() == CLASS_C0]

    def c1_items(self) -> list[CostItem]:
        return [item for item in self.items if item.cost_class() == CLASS_C1]

    def structural_c0_usd(self, basis: Basis | None = None) -> float:
        """Sum of the structurally-verified charges, in USD, for one leg of ``basis``."""
        total = 0.0
        for item in self.c0_items():
            total += to_usd(assert_c0(item).value, item.unit, basis)
        return total

    def unresolved_c1_total_usd(self, basis: Basis | None = None) -> float | None:
        """Sum of known and evaluable C1 charges, or ``None`` when the envelope is unbounded.

        A C1 item with an unknown value, or one whose USD cannot be evaluated for want
        of a basis input, makes the whole subtotal unknown. It is never coerced to 0.
        """
        total = 0.0
        for item in self.c1_items():
            if item.value is None:
                return None
            try:
                total += to_usd(item.value, item.unit, basis)
            except MissingUnitInput:
                return None
        return total

    def unresolved_c1_known_usd(self, basis: Basis | None = None) -> dict:
        """Known and evaluable C1 subtotal, with unknown and unevaluable item ids named."""
        known = 0.0
        unknown_ids: list[str] = []
        unevaluated_ids: list[str] = []
        for item in self.c1_items():
            if item.value is None:
                unknown_ids.append(item.id)
                continue
            try:
                known += to_usd(item.value, item.unit, basis)
            except MissingUnitInput:
                unevaluated_ids.append(item.id)
        return {
            "known_usd": known,
            "unknown_item_ids": unknown_ids,
            "unevaluated_item_ids": unevaluated_ids,
            "bounded": not (unknown_ids or unevaluated_ids),
        }

    def unresolved_c1_items(self) -> list[dict]:
        return [
            {
                "id": item.id,
                "name": item.name,
                "unit": item.unit,
                "value": item.value,
                "status": STATUS_UNKNOWN if item.value is None else "KNOWN",
                "varies_with": {
                    "volume": item.varies_with_volume,
                    "staking": item.varies_with_staking,
                    "account_state": item.varies_with_account_state,
                },
                "provenance": item.provenance.as_dict(),
            }
            for item in self.c1_items()
        ]

    def c0_provenance(self) -> list[dict]:
        return [{"id": item.id, **item.provenance.as_dict()} for item in self.c0_items()]


def cost_item_from_ledger_entry(entry: Mapping) -> CostItem:
    """Map one ``cost_ledger_v1.json`` line item onto a :class:`CostItem`.

    Reuses the ledger's own provenance tags. A broker pass-through or broker-page-only
    cross-check is not primary-verified, so it cannot be C0.
    """
    source = entry.get("source", {}) or {}
    cross_check = str(entry.get("cross_check_status", ""))
    retrieval = str(source.get("retrieval_status", ""))
    primary_marker = f"{cross_check} {retrieval}"
    if entry.get("value") is None or entry.get("unit") in (None, "UNKNOWN"):
        status = STATUS_UNKNOWN
    elif "PRIMARY" in primary_marker:
        status = STATUS_VERIFIED
    else:
        status = STATUS_UNVERIFIED
    provenance = Provenance(
        source_id=entry.get("source_id", entry.get("id", "")),
        url=source.get("url", ""),
        publisher=source.get("publisher", ""),
        access_date=source.get("access_date", ""),
        effective_period=str(entry.get("effective_date", source.get("effective_period", ""))),
        quote=source.get("quote", ""),
        status=status,
    )
    return CostItem(
        id=entry.get("id", ""),
        name=entry.get("name", ""),
        unit=entry.get("unit", "UNKNOWN"),
        value=entry.get("value"),
        side=entry.get("sides", "both"),
        provenance=provenance,
        mandatory=True,
        notes=str(entry.get("cross_check_note", "")),
    )


def envelope_from_ledger(ledger: Mapping, regime: str, envelope_id: str | None = None) -> Envelope:
    """Build an :class:`Envelope` from the existing ledger, read-only, for one regime."""
    items = tuple(
        cost_item_from_ledger_entry(entry)
        for entry in ledger.get("line_items", [])
        if regime in entry.get("regimes", ledger.get("regimes", []))
    )
    return Envelope(envelope_id=envelope_id or f"{ledger.get('ledger_id', 'ledger')}:{regime}", items=items)


# ---------------------------------------------------------------------------
# Break-even residual, C1 sensitivity, friction.
# ---------------------------------------------------------------------------


def break_even_residual(gross_usd: float, c0_usd: float) -> float:
    """``C* = g - C0``: what the strategy must clear after the structural floor."""
    return float(gross_usd) - float(c0_usd)


def c1_sensitivity(gross_usd: float, c0_usd: float, c1_levels: Sequence[float]) -> dict:
    """Report ``C*`` across assumed C1 levels without inventing a distribution.

    The levels are supplied by the caller; this function assigns them no probability.
    """
    gross = float(gross_usd)
    c0 = float(c0_usd)
    rows = [
        {
            "c1_usd": float(level),
            "c_star_usd": gross - c0 - float(level),
            "survives_floor": (gross - c0 - float(level)) > 0,
        }
        for level in c1_levels
    ]
    return {
        "gross_usd": gross,
        "c0_usd": c0,
        "c1_breakeven_usd": gross - c0,
        "rows": rows,
        "distribution_assumption": "NONE",
        "note": "C1 has no assigned probability distribution; levels are caller-supplied scenarios.",
    }


def _require_observed_spread(spread: float | None, label: str) -> float:
    if spread is None:
        raise MissingUnitInput(f"{label} spread must be an OBSERVED value; None is not a spread")
    if spread < 0:
        raise ValueError(f"{label} spread cannot be negative: {spread}")
    return float(spread)


def midpoint_markout_friction(spread_entry_usd: float | None, spread_exit_usd: float | None) -> float:
    """``1/2 S_entry + 1/2 S_exit`` from OBSERVED spreads, in USD per unit."""
    return 0.5 * _require_observed_spread(spread_entry_usd, "entry") + 0.5 * _require_observed_spread(
        spread_exit_usd, "exit"
    )


def midpoint_markout_friction_bps(
    spread_entry_usd: float | None, spread_exit_usd: float | None, price_usd: float | None
) -> float:
    """The same friction expressed in bps; refuses without a price."""
    if price_usd is None or price_usd == 0:
        raise MissingUnitInput("price_usd required to express midpoint friction in bps")
    return midpoint_markout_friction(spread_entry_usd, spread_exit_usd) / price_usd * 10000.0


# ---------------------------------------------------------------------------
# Executable capture: Nasdaq closing auction.
# ---------------------------------------------------------------------------


def auction_executable_gross(
    signal: str,
    *,
    best_bid: float,
    best_ask: float,
    closing_cross_price: float,
    reference_price: float | None = None,
) -> dict:
    """Executable-capture gross for the frozen auction formulation.

    A positive NOII signal buys the first eligible post-15:55 best ask and exits at the
    Closing Cross; a negative signal sells the best bid and covers at the Closing Cross.
    Contracting at the ask (or bid) embeds the entry spread in the gross by construction.
    """
    if signal in INELIGIBLE_NOII_CODES or signal not in (SIGNAL_POSITIVE, SIGNAL_NEGATIVE):
        raise ValueError(f"signal {signal!r} is ineligible; Direction B/S only (N/O/P ineligible)")
    if best_ask < best_bid:
        raise ValueError(f"crossed quote: bid {best_bid} > ask {best_ask}")
    entry_spread = float(best_ask) - float(best_bid)
    if signal == SIGNAL_POSITIVE:
        entry_price = float(best_ask)
        gross_per_share = float(closing_cross_price) - entry_price
        side = "buy_at_ask"
    else:
        entry_price = float(best_bid)
        gross_per_share = entry_price - float(closing_cross_price)
        side = "sell_at_bid"
    mid = 0.5 * (float(best_bid) + float(best_ask))
    gross_bps = (
        None
        if reference_price is None or reference_price == 0
        else gross_per_share / float(reference_price) * 10000.0
    )
    return {
        "signal": signal,
        "side": side,
        "entry_price": entry_price,
        "exit_price": float(closing_cross_price),
        "entry_spread_usd": entry_spread,
        "entry_spread_embedded": True,
        "mid_at_entry": mid,
        "entry_slippage_vs_mid_usd": entry_price - mid,
        "gross_usd_per_share": gross_per_share,
        "gross_bps": gross_bps,
        "bps_basis": None if gross_bps is None else "reference_price",
        "bps_requires_reference_price": gross_bps is None,
    }


# ---------------------------------------------------------------------------
# Multi-leg arithmetic: perp legs, funding direction, per-side vs round-trip.
# ---------------------------------------------------------------------------


def funding_cashflow(funding_rate: float | None, notional_usd: float | None, position: str) -> float:
    """Signed funding cashflow for one leg of ``notional_usd``.

    A positive ``funding_rate`` is paid by longs to shorts, so a short receives
    ``+rate * notional`` and a long pays ``-rate * notional``.
    """
    if funding_rate is None:
        raise MissingUnitInput("funding_rate is UNKNOWN")
    if notional_usd is None:
        raise MissingUnitInput("notional_usd required to evaluate funding")
    if position == "short":
        sign = 1.0
    elif position == "long":
        sign = -1.0
    else:
        raise ValueError(f"position must be 'long' or 'short', got {position!r}")
    return sign * float(funding_rate) * float(notional_usd)


def round_trip_usd(entry_usd: float, exit_usd: float) -> dict:
    """Explicit per-side vs round-trip decomposition."""
    total = float(entry_usd) + float(exit_usd)
    return {
        "entry_usd": float(entry_usd),
        "exit_usd": float(exit_usd),
        "round_trip_usd": total,
        "per_side_usd": total / 2.0,
    }


def perp_leg(
    *,
    notional_usd: float | None,
    position: str,
    fee_entry_bps: float,
    fee_exit_bps: float,
    funding_rate: float = 0.0,
    funding_intervals: int = 1,
) -> dict:
    """One perpetual leg: entry+exit fees (round-trip) and signed funding cashflow."""
    if notional_usd is None:
        raise MissingUnitInput("notional_usd required to evaluate a perp leg")
    if funding_intervals < 0:
        raise ValueError("funding_intervals cannot be negative")
    fee_entry = bps_to_usd(fee_entry_bps, notional_usd)
    fee_exit = bps_to_usd(fee_exit_bps, notional_usd)
    fees = round_trip_usd(fee_entry, fee_exit)
    funding = funding_cashflow(funding_rate, notional_usd, position) * funding_intervals
    return {
        "position": position,
        "notional_usd": float(notional_usd),
        "fee_entry_usd": fee_entry,
        "fee_exit_usd": fee_exit,
        "fees_round_trip_usd": fees["round_trip_usd"],
        "fees_per_side_usd": fees["per_side_usd"],
        "funding_rate": float(funding_rate),
        "funding_intervals": funding_intervals,
        "funding_usd": funding,
        "net_usd": funding - fees["round_trip_usd"],
    }


def two_leg_net(legs: Sequence[Mapping]) -> dict:
    """Aggregate a two-leg (or N-leg) pair: fees, signed funding, net."""
    fees = sum(float(leg["fees_round_trip_usd"]) for leg in legs)
    funding = sum(float(leg["funding_usd"]) for leg in legs)
    return {
        "leg_count": len(legs),
        "fees_round_trip_usd": fees,
        "funding_usd": funding,
        "net_usd": funding - fees,
        "legs": [dict(leg) for leg in legs],
    }


def perp_price_pnl(
    *,
    entry_price: float | None,
    exit_price: float | None,
    position: str,
    notional_usd: float | None,
) -> float:
    """Signed mark-to-market P&L of ONE perpetual leg sized at ``notional_usd`` at entry.

    The leg holds ``notional_usd / entry_price`` units. A ``short`` loses when the price
    rises, a ``long`` loses when it falls. The result is USD and is price only: no fee and
    no funding enters it, so a hedged pair's mark-to-market residual is the SUM of its two
    legs' values (a pair of equal notional has residual ``notional * (r_long - r_short)``).
    An unknown price is refused, never defaulted.
    """
    if entry_price is None or exit_price is None:
        raise MissingUnitInput("entry_price and exit_price required to evaluate a price P&L")
    if float(entry_price) <= 0:
        raise ValueError(f"entry_price must be positive: {entry_price}")
    if notional_usd is None:
        raise MissingUnitInput("notional_usd required to evaluate a perp leg")
    if position == "short":
        sign = -1.0
    elif position == "long":
        sign = 1.0
    else:
        raise ValueError(f"position must be 'long' or 'short', got {position!r}")
    return sign * float(notional_usd) * (float(exit_price) / float(entry_price) - 1.0)


# ---------------------------------------------------------------------------
# Preregistered classification.
# ---------------------------------------------------------------------------


def classify_materiality(
    gross_usd: float, uncertainty_lo_usd: float, uncertainty_hi_usd: float, c0_usd: float
) -> dict:
    """The preregistered uncertainty-vs-C0 rule, exactly as frozen.

    ``KILL_MATERIALITY`` when ``g <= 0`` or ``hi <= C0``;
    ``SURVIVE_PROVISIONAL`` when ``lo > C0``; otherwise ``INDETERMINATE``.
    Statistical significance against zero is never consulted here.
    """
    gross = float(gross_usd)
    c0 = float(c0_usd)
    lo = min(float(uncertainty_lo_usd), float(uncertainty_hi_usd))
    hi = max(float(uncertainty_lo_usd), float(uncertainty_hi_usd))
    if gross <= 0 or hi <= c0:
        verdict = VERDICT_KILL
    elif lo > c0:
        verdict = VERDICT_SURVIVE
    else:
        verdict = VERDICT_INDETERMINATE
    return {
        "verdict": verdict,
        "gross_usd": gross,
        "uncertainty_lo_usd": lo,
        "uncertainty_hi_usd": hi,
        "c0_usd": c0,
        "c_star_usd": gross - c0,
        "rule": "KILL if g<=0 or hi<=C0; SURVIVE_PROVISIONAL if lo>C0; else INDETERMINATE",
        "significance_is_decision_criterion": False,
    }


def significance_against_zero(estimate: float | None, standard_error: float | None) -> dict:
    """Separate reported quantity only; never an input to :func:`classify_materiality`."""
    if estimate is None or standard_error is None or standard_error == 0:
        t_stat = None
    else:
        t_stat = float(estimate) / float(standard_error)
    return {
        "estimate": estimate,
        "standard_error": standard_error,
        "t_stat": t_stat,
        "role": "REPORTED_ONLY",
        "note": "statistical significance against zero is not the materiality decision criterion",
    }