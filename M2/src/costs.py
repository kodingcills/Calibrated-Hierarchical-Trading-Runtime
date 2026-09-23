"""Deterministic cost ledger arithmetic.

Costs are never a single opaque number. The ledger (``M2/config/cost_ledger_v1.json``)
holds every charge as a separate line item with its own source, access date, unit,
formula, applicability and minimum/maximum. This module only does arithmetic on
those items.

Two regimes are kept strictly separate, as the handoff requires:

``STRUCTURAL_COST_FLOOR``
    Only unavoidable verified charges on the candidate's venue path: the Nasdaq
    remove-liquidity fee plus the statutory sale-side fees that any U.S. equity
    sale incurs. This is a floor, not an achievable execution path.

``ACCESSIBLE_REFERENCE_PATH``
    A named broker path actually available to this project (IBKR Pro, Fixed and
    Tiered). Its cost is what a participant would really pay, and it is labelled
    as such: a reference path, not a claim about realised slippage.

No profitability judgement is made anywhere in this module.
"""

from __future__ import annotations

import json
import math
import os
from typing import Iterable

UNIT_PER_SHARE = "USD_PER_SHARE"
UNIT_PER_ORDER_FLAT = "USD_PER_ORDER"
UNIT_PER_ORDER_MIN = "USD_PER_ORDER_MIN"
UNIT_PCT_OF_TRADE_VALUE = "PCT_OF_TRADE_VALUE"
UNIT_PER_MILLION_OF_SALES = "USD_PER_MILLION_OF_SALES"
UNIT_MULTIPLIER_OF_COMMISSION = "MULTIPLIER_OF_COMMISSION"

SIDE_BUY = "buy"
SIDE_SELL = "sell"


def load_ledger(path: str) -> dict:
    with open(path, "r") as handle:
        return json.load(handle)


def schedule_pairs(ledger: dict) -> list[tuple[str, str | None, str]]:
    """The regimes evaluated together, as (regime, broker schedule, label).

    Declared in the ledger so that the arithmetic never hard-codes a broker name.
    """
    return [
        (row["regime"], row.get("broker_schedule"), row["label"])
        for row in ledger["execution_schedules"]
    ]


def line_item_applies(item: dict, side: str, regime: str) -> bool:
    if item.get("regime") not in (None, regime):
        return False
    sides = item.get("sides", "both")
    if sides == "both":
        return True
    return sides == side


def line_item_cost(item: dict, quantity: float, price_usd: float, commission_usd: float = 0.0) -> float:
    """Evaluate one ledger line item in USD for one order."""
    unit = item["unit"]
    notional = quantity * price_usd
    if unit == UNIT_PER_SHARE:
        cost = item["value"] * quantity
    elif unit == UNIT_PER_ORDER_FLAT:
        cost = item["value"]
    elif unit == UNIT_PER_ORDER_MIN:
        cost = item["value"]
    elif unit == UNIT_PCT_OF_TRADE_VALUE:
        cost = item["value"] / 100.0 * notional
    elif unit == UNIT_PER_MILLION_OF_SALES:
        cost = item["value"] / 1_000_000.0 * notional
    elif unit == UNIT_MULTIPLIER_OF_COMMISSION:
        cost = item["value"] * commission_usd
    else:  # pragma: no cover - ledger validation guards this
        raise ValueError(f"unknown cost unit {unit!r} in item {item.get('id')}")
    maximum = item.get("max")
    if maximum is not None:
        if maximum.get("unit") == UNIT_PCT_OF_TRADE_VALUE:
            cost = min(cost, maximum["value"] / 100.0 * notional)
        elif maximum.get("unit") == UNIT_PER_ORDER_FLAT:
            cost = min(cost, maximum["value"])
    minimum = item.get("min")
    if minimum is not None:
        cost = max(cost, minimum["value"])
    return cost


def commission_usd(ledger: dict, schedule: str, quantity: float, price_usd: float) -> float:
    """Order commission for the named broker schedule, honouring min and cap."""
    definition = ledger["broker_schedules"][schedule]
    notional = quantity * price_usd
    cost = definition["per_share_usd"] * quantity
    cost = max(cost, definition["min_per_order_usd"])
    if definition.get("max_pct_of_trade_value") is not None:
        capped = definition["max_pct_of_trade_value"] / 100.0 * notional
        # IBKR footnote 8: when the calculated maximum is below the minimum, the
        # maximum is assessed.
        cost = min(cost, capped) if capped >= definition["min_per_order_usd"] else capped
    return cost


def order_cost_breakdown(
    ledger: dict,
    regime: str,
    side: str,
    quantity: float,
    price_usd: float,
    broker_schedule: str | None = None,
) -> dict:
    """Full line-item breakdown for one aggressive order."""
    commission = 0.0
    if broker_schedule:
        commission = commission_usd(ledger, broker_schedule, quantity, price_usd)
    items: dict[str, float] = {}
    if broker_schedule and ledger["broker_schedules"][broker_schedule].get("all_inclusive"):
        # The all-inclusive schedule already contains exchange, clearing and
        # regulatory fees; adding them again would double count.
        items[f"broker_{broker_schedule}_commission"] = commission
        return {
            "regime": regime,
            "side": side,
            "quantity": quantity,
            "price_usd": price_usd,
            "items": items,
            "total_usd": sum(items.values()),
            "total_bps": bps(sum(items.values()), quantity * price_usd),
            "double_counting_guard": "ALL_INCLUSIVE_SCHEDULE",
        }
    for item in ledger["line_items"]:
        if regime not in item.get("regimes", ledger["regimes"]):
            continue
        if not line_item_applies(item, side, regime):
            continue
        items[item["id"]] = line_item_cost(item, quantity, price_usd, commission)
    if broker_schedule:
        items[f"broker_{broker_schedule}_commission"] = commission
    total = sum(items.values())
    return {
        "regime": regime,
        "side": side,
        "quantity": quantity,
        "price_usd": price_usd,
        "items": items,
        "total_usd": total,
        "total_bps": bps(total, quantity * price_usd),
        "double_counting_guard": "LINE_ITEMS_SEPARATE",
    }


def round_trip_cost(ledger: dict, regime: str, quantity: float, price_usd: float, broker_schedule: str | None = None) -> dict:
    """Aggressive round trip: buy leg plus sell leg, each charged separately."""
    buy = order_cost_breakdown(ledger, regime, SIDE_BUY, quantity, price_usd, broker_schedule)
    sell = order_cost_breakdown(ledger, regime, SIDE_SELL, quantity, price_usd, broker_schedule)
    total = buy["total_usd"] + sell["total_usd"]
    return {
        "regime": regime,
        "broker_schedule": broker_schedule or "",
        "quantity": quantity,
        "price_usd": price_usd,
        "buy_usd": buy["total_usd"],
        "sell_usd": sell["total_usd"],
        "total_usd": total,
        "total_bps": bps(total, quantity * price_usd),
        "items": {f"buy_{k}": v for k, v in buy["items"].items()}
        | {f"sell_{k}": v for k, v in sell["items"].items()},
    }


def bps(cost_usd: float, notional_usd: float) -> float | None:
    """Convert USD cost to basis points of notional; None when notional is not positive."""
    if notional_usd <= 0:
        return None
    return 10000.0 * cost_usd / notional_usd


def reference_cost_by_quantity(
    ledger: dict, quantities: Iterable[float]
) -> list[dict]:
    """Per-order and round-trip arithmetic for representative share quantities."""
    rows = []
    for quantity in quantities:
        row = {
            "quantity": quantity,
            "assumed_price_usd_for_percentage_caps": 1.0,
            "note": "per-order minimums and percentage caps make the cost per share depend on order size "
                    "and price, so this table reports USD only; bps conversion is in reference_cost_by_price.csv",
        }
        for regime, schedule, label in schedule_pairs(ledger):
            buy = order_cost_breakdown(ledger, regime, SIDE_BUY, quantity, 1.0, schedule)
            sell = order_cost_breakdown(ledger, regime, SIDE_SELL, quantity, 1.0, schedule)
            trip = round_trip_cost(ledger, regime, quantity, 1.0, schedule)
            row[f"{label}_one_way_buy_usd"] = buy["total_usd"]
            row[f"{label}_one_way_sell_usd"] = sell["total_usd"]
            row[f"{label}_round_trip_usd"] = trip["total_usd"]
            for item_id, value in buy["items"].items():
                row[f"{label}_{item_id}_usd"] = value
        rows.append(row)
    return rows


def reference_cost_by_price(
    ledger: dict, prices: Iterable[float], quantities: Iterable[float]
) -> list[dict]:
    """Per-share cost expressed in bps for representative prices and order sizes."""
    rows = []
    for price in prices:
        for quantity in quantities:
            row = {"price_usd": price, "quantity": quantity}
            for regime, schedule, label in schedule_pairs(ledger):
                buy = order_cost_breakdown(ledger, regime, SIDE_BUY, quantity, price, schedule)
                sell = order_cost_breakdown(ledger, regime, SIDE_SELL, quantity, price, schedule)
                trip = round_trip_cost(ledger, regime, quantity, price, schedule)
                row[f"{label}_one_way_buy_bps"] = buy["total_bps"]
                row[f"{label}_one_way_sell_bps"] = sell["total_bps"]
                row[f"{label}_round_trip_bps"] = trip["total_bps"]
            rows.append(row)
    return rows


def cost_in_bps_of_price(ledger: dict, regime: str, schedule: str | None, quantity: float, price_usd: float) -> float | None:
    """Round-trip known cost in bps of notional, or None when it is not computable."""
    if quantity <= 0 or price_usd <= 0:
        return None
    return round_trip_cost(ledger, regime, quantity, price_usd, schedule)["total_bps"]


def validate_ledger(ledger: dict) -> list[str]:
    """Structural validation: every numeric line item must carry provenance."""
    problems = []
    for item in ledger["line_items"]:
        source = item.get("source", {})
        for field in ("url", "publisher", "access_date"):
            if not source.get(field):
                problems.append(f"{item.get('id')}: missing source.{field}")
        if item.get("value") is not None and not source.get("quote"):
            problems.append(f"{item.get('id')}: numeric value without a source quote")
    if not ledger.get("execution_schedules"):
        problems.append("ledger has no execution_schedules block")
    for name, schedule in ledger["broker_schedules"].items():
        source = schedule.get("source", {})
        for field in ("url", "publisher", "access_date"):
            if not source.get(field):
                problems.append(f"{name}: missing source.{field}")
    return problems
