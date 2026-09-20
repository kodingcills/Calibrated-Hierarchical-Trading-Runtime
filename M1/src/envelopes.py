"""Execution-envelope derivation from verified venue facts.

Every number here is a function of a verified venue fee value plus the candidate's named
execution style. Where an input is UNKNOWN the output is UNKNOWN - never zero, never a
partial sum presented as a total (ASM-0011..ASM-0013).
"""

from __future__ import annotations

import costs
from corpus.constants import UNKNOWN

COLUMNS = [
    "candidate_id", "candidate_class", "venue_id", "execution_style",
    "fee_source_ids", "fee_unit_notes",
    "one_way_maker_fee_bps", "one_way_taker_fee_bps",
    "round_trip_maker_maker_fee_bps", "round_trip_maker_taker_fee_bps",
    "round_trip_taker_taker_fee_bps", "round_trip_flat_fee_bps",
    "required_round_trip_fee_bps_for_style",
    "known_cost_floor_bps", "known_cost_floor_native_value", "known_cost_floor_native_unit",
    "known_cost_floor_known_components", "known_cost_floor_missing_components",
    "spread_bps", "slippage_bps", "adverse_selection_bps", "impact_bps", "funding_bps",
    "clearing_broker_fees_bps",
    "full_break_even_bps", "full_break_even_status", "full_break_even_unknown_components",
    "break_even_source_ids", "envelope_note", "unknown_fields",
]

_NON_FEE_COMPONENTS = (
    "spread", "slippage", "adverse_selection", "impact", "funding", "clearing_broker_fees",
)


def _venue_fee_bps(venue, prefix, price=None):
    value = venue.get(f"{prefix}_value")
    unit = venue.get(f"{prefix}_unit")
    return costs.bps_from_native(value, unit, price=price)


def venue_fee_reference(venue) -> dict:
    """Round-trip fee arithmetic for any venue with at least one verified fee value."""
    maker = _venue_fee_bps(venue, "maker_fee")
    taker = _venue_fee_bps(venue, "taker_fee")
    flat_open = _venue_fee_bps(venue, "perp_open_fee")
    flat_close = _venue_fee_bps(venue, "perp_close_fee")
    flat = costs.round_trip(flat_open, flat_close)
    rt = costs.round_trip_costs(maker, taker, round_trip_flat_bps=UNKNOWN)
    if flat is not UNKNOWN:
        rt["round_trip_flat_fee_bps"] = flat
    return {
        "venue_id": venue["venue_id"],
        "instrument": venue["instrument"],
        "maker_fee_value": venue.get("maker_fee_value"),
        "maker_fee_unit": venue.get("maker_fee_unit"),
        "taker_fee_value": venue.get("taker_fee_value"),
        "taker_fee_unit": venue.get("taker_fee_unit"),
        "rebate_value": venue.get("rebate_value"),
        "rebate_unit": venue.get("rebate_unit"),
        "perp_open_fee_value": venue.get("perp_open_fee_value"),
        "perp_open_fee_unit": venue.get("perp_open_fee_unit"),
        "perp_close_fee_value": venue.get("perp_close_fee_value"),
        "perp_close_fee_unit": venue.get("perp_close_fee_unit"),
        "one_way_maker_fee_bps": maker,
        "one_way_taker_fee_bps": taker,
        **rt,
        "bps_conversion_requires_price": "YES" if (
            costs.unit_is_price_dependent(venue.get("taker_fee_unit") or "") or
            costs.unit_is_price_dependent(venue.get("maker_fee_unit") or "")) else "NO",
        "fee_source_ids": "|".join(sorted({
            s for s in (venue.get("maker_fee_source_id"), venue.get("taker_fee_source_id"),
                        venue.get("rebate_source_id"), venue.get("perp_open_fee_source_id"),
                        venue.get("perp_close_fee_source_id")) if s is not UNKNOWN})) or "NONE",
    }


def envelope_row(cand, venue, price=None) -> dict:
    maker = _venue_fee_bps(venue, "maker_fee", price)
    taker = _venue_fee_bps(venue, "taker_fee", price)
    flat = costs.round_trip(
        _venue_fee_bps(venue, "perp_open_fee", price),
        _venue_fee_bps(venue, "perp_close_fee", price))
    rt = costs.round_trip_costs(maker, taker)
    if flat is not UNKNOWN:
        rt["round_trip_flat_fee_bps"] = flat

    style = cand["execution_style"]
    required = costs.required_round_trip_fee_bps(style, maker, taker)
    if required is UNKNOWN and flat is not UNKNOWN and style in ("AGGRESSIVE", "MIXED", "PASSIVE"):
        required = flat

    # Native floor: only components the venue row actually verifies, priced for the
    # candidate's style. A passive candidate needs the maker side, which for a
    # rebate-only schedule is not a fee and therefore stays UNKNOWN.
    if style in ("AGGRESSIVE", "AUCTION"):
        native_legs = {"taker_fee": venue.get("taker_fee_value"),
                       "taker_fee_second_leg": venue.get("taker_fee_value")}
    elif style == "PASSIVE":
        native_legs = {"maker_fee": venue.get("maker_fee_value"),
                       "maker_fee_second_leg": venue.get("maker_fee_value")}
    else:
        native_legs = {"maker_fee": UNKNOWN, "maker_fee_second_leg": UNKNOWN,
                       "taker_fee": venue.get("taker_fee_value"),
                       "taker_fee_second_leg": venue.get("taker_fee_value")}
    if flat is not UNKNOWN:
        native_legs["perp_flat_round_trip"] = flat
        if native_legs["taker_fee"] is UNKNOWN:
            native_legs["taker_fee"] = venue.get("perp_open_fee_value")
            native_legs["taker_fee_second_leg"] = venue.get("perp_close_fee_value")
    elif venue.get("perp_open_fee_value") is not UNKNOWN:
        native_legs["perp_open_fee"] = venue.get("perp_open_fee_value")
        native_legs["perp_close_fee"] = venue.get("perp_close_fee_value")

    floor = costs.known_cost_floor(native_legs)

    break_even_components = {
        "spread": UNKNOWN, "fees": required, "slippage": UNKNOWN,
        "adverse_selection": UNKNOWN, "impact": UNKNOWN,
    }
    be = costs.full_break_even(break_even_components)

    fee_sources = "|".join(sorted({s for s in (
        venue.get("maker_fee_source_id"), venue.get("taker_fee_source_id"),
        venue.get("perp_open_fee_source_id"), venue.get("perp_close_fee_source_id"))
        if s is not UNKNOWN})) or "NONE"
    if required is UNKNOWN:
        fee_sources = "NONE"

    note_parts = []
    if costs.unit_is_price_dependent(venue.get("taker_fee_unit") or ""):
        note_parts.append("Taker fee is quoted per share: its bps equivalent needs a price and is "
                          "therefore UNKNOWN here (ASM-0011).")
    if style == "PASSIVE" and venue.get("maker_fee_value") is UNKNOWN:
        note_parts.append("Passive candidate: the maker-side fee component is not verified for this "
                          "venue, so no cost floor is computed.")
    if style == "MIXED":
        note_parts.append("MIXED style: the maker/taker mix is a strategy choice that has not been "
                          "made, so the style-required round trip stays UNKNOWN.")
    if required is not UNKNOWN:
        note_parts.append(f"Round trip for {style} execution uses only verified fee legs; spread, "
                          "slippage, impact and adverse selection remain separate unknown columns.")
    if not note_parts:
        note_parts.append("No verified fee value exists for this venue, so every cost field is "
                          "UNKNOWN rather than zero.")

    return {
        "candidate_id": cand["candidate_id"],
        "candidate_class": cand["candidate_class"],
        "venue_id": cand["venue_id"],
        "execution_style": style,
        "fee_source_ids": fee_sources,
        "fee_unit_notes": venue.get("fee_notes"),
        "one_way_maker_fee_bps": maker,
        "one_way_taker_fee_bps": taker,
        "round_trip_maker_maker_fee_bps": rt["round_trip_maker_maker_fee_bps"],
        "round_trip_maker_taker_fee_bps": rt["round_trip_maker_taker_fee_bps"],
        "round_trip_taker_taker_fee_bps": rt["round_trip_taker_taker_fee_bps"],
        "round_trip_flat_fee_bps": rt.get("round_trip_flat_fee_bps", UNKNOWN),
        "required_round_trip_fee_bps_for_style": required,
        "known_cost_floor_bps": floor["floor_value"] if maker is not UNKNOWN or taker is not UNKNOWN
        else UNKNOWN,
        "known_cost_floor_native_value": floor["floor_value"],
        "known_cost_floor_native_unit": _native_floor_unit(venue, style),
        "known_cost_floor_known_components": "|".join(floor["known_components"]) or "NONE",
        "known_cost_floor_missing_components": "|".join(floor["missing_components"]) or "NONE",
        "spread_bps": UNKNOWN,
        "slippage_bps": UNKNOWN,
        "adverse_selection_bps": UNKNOWN,
        "impact_bps": UNKNOWN,
        "funding_bps": UNKNOWN,
        "clearing_broker_fees_bps": UNKNOWN,
        "full_break_even_bps": be["break_even_bps"],
        "full_break_even_status": be["status"],
        "full_break_even_unknown_components": "|".join(be["unknown_components"]) or "NONE",
        "break_even_source_ids": fee_sources if be["status"] == "COMPUTED" else "NONE",
        "envelope_note": " ".join(note_parts) +
                         " KnownCostFloor is a lower bound on cost, not break-even (ASM-0012).",
    }


def _native_floor_unit(venue, style):
    if style == "PASSIVE":
        return venue.get("maker_fee_unit")
    return venue.get("taker_fee_unit")


def all_envelopes(candidates, venues) -> list:
    rows = []
    for cand in candidates:
        venue = venues.get(cand["venue_id"])
        if venue is None:
            rows.append({col: UNKNOWN for col in COLUMNS} | {
                "candidate_id": cand["candidate_id"],
                "candidate_class": cand["candidate_class"],
                "venue_id": cand["venue_id"],
                "execution_style": cand["execution_style"],
                "envelope_note": "No venue row exists for this registration row (method rule, "
                                 "universe definition or governance entry), so no cost envelope is "
                                 "defined.",
            })
            continue
        rows.append(envelope_row(cand, venue))
    return rows