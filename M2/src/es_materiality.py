"""Frozen H3 order-flow-imbalance gross-markout measurement for branch A (CME ES).

This module is the *whole* of the branch-A measurement: it reads the admitted ESU3
10-minute RTH-open slice, builds a causal signed order-flow-imbalance state, marks the
side-signed midpoint out at the frozen H3 horizons, measures the observed-spread
friction and applies the preregistered materiality classification.

It owns no arithmetic that :mod:`M2.src.envelope` already owns. Friction is
``envelope.midpoint_markout_friction_bps`` (``1/2 S_entry + 1/2 S_exit``), the
break-even residual is ``envelope.break_even_residual``, the C1 sensitivity is
``envelope.c1_sensitivity``, the C0/C1 split is ``envelope.CostItem.cost_class()`` and
the verdict is ``envelope.classify_materiality``. The clustered interval reuses
``M2.src.calculate.block_bootstrap_ci``.

Every parameter that could be tuned is read from the sealed contract
(``M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json``), never from a code constant, so a
post-result change to a horizon, state, lookback, block length, seed, floor or friction
treatment cannot be made without invalidating the frozen hash. Before any number is
computed the module re-hashes itself, the sealed contract and every declared input, and
refuses to run on a mismatch.

Frozen design, in one place:

* **Clock.** A decision at instant ``t`` may use only messages whose venue transmission
  time is ``<= t`` (``exchange_send_ns``); the admitted slice satisfies
  ``transact_time <= exchange_send <= ts_recv`` for every row. A fully
  capture-conservative variant (``ts_recv_ns``) is carried as a declared robustness
  pass and is never the reported verdict.
* **State.** Take the one-second lookback ``(t - W, t]``. ``V_buy`` / ``V_sell`` are the
  aggressor-signed ESU3 trade sizes in that interval; ``D_t`` is the displayed
  top-of-book depth (``bid_sz + ask_sz``) prevailing at ``t``. The state is
  ``x_t = (V_buy - V_sell) / D_t`` in units of the visible book, and its *sign* is the
  direction: ``x_t > 0`` is LONG, ``x_t < 0`` is SHORT, and a balanced or undefined
  state is no position. No threshold exists to tune.
* **Outcome.** Side-signed midpoint markout in bps on the reconstructed top of book
  (no executable-price substitution), at H3 = 1 s / 5 s / 15 s, PRIMARY = 1 s.
* **Friction.** ``1/2 S_entry + 1/2 S_exit`` from the *observed* quoted spread at the
  entry and the exit instant, in bps of the entry midpoint; no one-tick stand-in and no
  arbitrary safety multiple.
* **C0 / C1.** ``C0`` is the observed-spread friction term plus verified
  account-independent mandatory charges; for this branch the exchange/clearing/FCM
  amounts are unverified (the CME fee schedule is not retrievable in this environment
  and the one third-party figure that was found has been rejected), so they carry no
  value and stay in ``C1`` as UNKNOWN -- never zero.
* **Scope.** One admitted 10-minute window. The measurement can therefore produce at
  most a SAMPLE-SCOPED DEVELOPMENT KILL; a nominal SURVIVE_PROVISIONAL is downgraded to
  ``INDETERMINATE_COVERAGE`` with the scope clause, never claimed as survival.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from M2.src import calculate
from M2.src import config as config_module
from M2.src import envelope

NS_PER_SECOND = 1_000_000_000
BPS_PER_UNIT = 1.0e4

# ``INDETERMINATE_COVERAGE`` is the coverage-floor / sample-scope outcome named by the
# campaign contract; it is this module's only addition to envelope's three literals.
VERDICT_INDETERMINATE_COVERAGE = "INDETERMINATE_COVERAGE"

STATE_LONG = "LONG"
STATE_SHORT = "SHORT"

CLAUSE_NON_POSITIVE_GROSS = "PRIMARY_HORIZON_GROSS_NOT_POSITIVE"
CLAUSE_UPPER_AT_OR_BELOW_C0 = "UNCERTAINTY_UPPER_BOUND_AT_OR_BELOW_C0"
CLAUSE_LOWER_ABOVE_C0 = "UNCERTAINTY_LOWER_BOUND_ABOVE_C0"
CLAUSE_STRADDLES_C0 = "INTERVAL_STRADDLES_C0"
CLAUSE_COVERAGE_FLOOR = "COVERAGE_FLOOR_FAILED"
CLAUSE_SINGLE_WINDOW = "SINGLE_ADMITTED_WINDOW_SCOPE"

SCOPE_SAMPLE_SCOPED_KILL = "SAMPLE_SCOPED_DEVELOPMENT_KILL"
SCOPE_SINGLE_WINDOW_ONLY = "SINGLE_ADMITTED_WINDOW_ONLY"

SURVIVE = envelope.VERDICT_SURVIVE
KILL = envelope.VERDICT_KILL
INDETERMINATE = envelope.VERDICT_INDETERMINATE

_MODULE_PATH = "M2/src/es_materiality.py"


class MeasurementError(Exception):
    """A frozen precondition was violated; refuse to produce a number."""


# --------------------------------------------------------------------------- hashing


def sha256_file(path: str) -> str:
    """Hash any path (absolute or repository-relative) without loading it."""
    digest = hashlib.sha256()
    with open(config_module.repo_path(path), "rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""):
            digest.update(block)
    return digest.hexdigest()


def clean(value):
    """JSON-safe: a non-finite float is not a measurement, so it becomes ``null``."""
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


# ------------------------------------------------------------------------ data load


def _number(text: str | None) -> float:
    value = (text or "").strip()
    return float(value) if value else float("nan")


def load_manifest(data_dir: str) -> dict:
    with open(os.path.join(data_dir, "admission.json"), "r") as handle:
        return json.load(handle)


def load_spread_grid(path: str) -> dict[str, np.ndarray]:
    """The admitted 10 ms prevailing-quote grid, as arrays.

    ``bid_mantissa``/``ask_mantissa`` are the venue mantissas exactly as published and
    ``price_scale`` turns them into index points. A grid instant with no prevailing
    quote carries NaN in every quote column (the admitted slice has exactly one).
    """
    keys = ("ts_ns", "bid_mantissa", "ask_mantissa", "bid_sz", "ask_sz", "spread_points")
    columns: dict[str, list] = {key: [] for key in keys}
    with open(path, "r", newline="") as handle:
        for row in csv.DictReader(handle):
            columns["ts_ns"].append(int(row["ts_ns"]))
            columns["bid_mantissa"].append(_number(row["bid_px"]))
            columns["ask_mantissa"].append(_number(row["ask_px"]))
            columns["bid_sz"].append(_number(row["bid_sz"]))
            columns["ask_sz"].append(_number(row["ask_sz"]))
            columns["spread_points"].append(_number(row["spread_points"]))
    grid = {key: np.asarray(values) for key, values in columns.items()}
    grid["ts_ns"] = grid["ts_ns"].astype(np.int64)
    return grid


def load_trades(path: str, instrument_id: int, clock: str) -> dict[str, np.ndarray]:
    """Single-instrument aggressor-signed trades stamped on the requested clock."""
    times: list[int] = []
    sizes: list[float] = []
    aggressors: list[int] = []
    with open(path, "r", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["instrument_id"]) != instrument_id:
                continue
            times.append(int(row[clock]))
            sizes.append(float(row["size"]))
            aggressors.append(int(row["aggressor_side"]))
    order = np.argsort(np.asarray(times, dtype=np.int64), kind="stable")
    return {
        "time_ns": np.asarray(times, dtype=np.int64)[order],
        "size": np.asarray(sizes, dtype=float)[order],
        "aggressor": np.asarray(aggressors, dtype=np.int8)[order],
    }


def load_level_one(path: str, instrument_id: int) -> dict[str, np.ndarray]:
    """Direct level-1 book rows, used only by the independent causality audit."""
    times: list[int] = []
    prices: list[float] = []
    sides: list[str] = []
    with open(path, "r", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["instrument_id"]) != instrument_id:
                continue
            if row["flag"] != "direct_l1" or int(row["md_price_level"]) != 1:
                continue
            times.append(int(row["exchange_send_ns"]))
            prices.append(float(row["price"]))
            sides.append(row["side"])
    order = np.argsort(np.asarray(times, dtype=np.int64), kind="stable")
    return {
        "time_ns": np.asarray(times, dtype=np.int64)[order],
        "price": np.asarray(prices, dtype=float)[order],
        "side": np.asarray(sides)[order],
    }


# ---------------------------------------------------------------------- state build


@dataclass(frozen=True)
class Panel:
    """One horizon's aligned decision-slot arrays.

    Every array has one entry per decision slot; ``NaN`` marks a slot where the
    quantity does not exist (no prevailing quote, no displayed depth).
    """

    slot: np.ndarray
    block_id: np.ndarray
    mid_entry_points: np.ndarray
    mid_exit_points: np.ndarray
    spread_entry_points: np.ndarray
    spread_exit_points: np.ndarray
    depth: np.ndarray
    volume_buy: np.ndarray
    volume_sell: np.ndarray


def cumulative_flow(trades: Mapping[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Prefix sums of aggressor-classified size over the time-sorted trade tape."""
    size = trades["size"]
    aggressor = trades["aggressor"]
    buy = np.concatenate(([0.0], np.cumsum(np.where(aggressor == 1, size, 0.0))))
    sell = np.concatenate(([0.0], np.cumsum(np.where(aggressor == 2, size, 0.0))))
    return trades["time_ns"], buy, sell


def flow_between(
    time_ns: np.ndarray, buy: np.ndarray, sell: np.ndarray, instants: np.ndarray, lookback_ns: int
) -> tuple[np.ndarray, np.ndarray]:
    """Aggressor-signed volume in the half-open interval ``(instant - lookback, instant]``.

    Inclusive at the decision instant and exclusive at the window's far edge, so a
    message stamped exactly at the decision instant belongs to the decision and a
    message stamped after it never does. That inequality is the whole causal guarantee
    of the state.
    """
    at_or_before = np.searchsorted(time_ns, instants, side="right")
    before = np.searchsorted(time_ns, instants - lookback_ns, side="right")
    return buy[at_or_before] - buy[before], sell[at_or_before] - sell[before]


def build_panel(
    grid: Mapping[str, np.ndarray],
    flow: tuple[np.ndarray, np.ndarray, np.ndarray],
    horizon_s: int,
    lookback_ns: int,
    block_slots: int,
    price_scale: float,
    grid_step_ns: int,
) -> Panel:
    """Align one horizon's entry/exit instants and the state that is known at entry."""
    per_second = NS_PER_SECOND // grid_step_ns
    shift = horizon_s * per_second
    slots = np.arange(0, grid["ts_ns"].size // per_second - horizon_s, dtype=np.int64)
    entry = slots * per_second
    exit_ = entry + shift

    mid = (grid["bid_mantissa"] + grid["ask_mantissa"]) * 0.5 * price_scale
    volume_buy, volume_sell = flow_between(
        flow[0], flow[1], flow[2], grid["ts_ns"][entry], lookback_ns
    )
    return Panel(
        slot=slots,
        block_id=slots // block_slots,
        mid_entry_points=mid[entry],
        mid_exit_points=mid[exit_],
        spread_entry_points=grid["spread_points"][entry],
        spread_exit_points=grid["spread_points"][exit_],
        depth=(grid["bid_sz"] + grid["ask_sz"])[entry],
        volume_buy=volume_buy,
        volume_sell=volume_sell,
    )


def state_direction(panel: Panel) -> np.ndarray:
    """+1 LONG, -1 SHORT, 0 for a balanced or undefined state (no position)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        imbalance = (panel.volume_buy - panel.volume_sell) / panel.depth
    direction = np.zeros(panel.slot.shape, dtype=np.int8)
    defined = np.isfinite(imbalance) & np.isfinite(panel.depth) & (panel.depth > 0)
    direction[defined & (imbalance > 0)] = 1
    direction[defined & (imbalance < 0)] = -1
    return direction


def quote_mask(panel: Panel) -> np.ndarray:
    """Slots with a two-sided, strictly positive, uncrossed quote at entry and exit."""
    return (
        np.isfinite(panel.mid_entry_points)
        & np.isfinite(panel.mid_exit_points)
        & (panel.mid_entry_points > 0)
        & (panel.mid_exit_points > 0)
        & (panel.spread_entry_points > 0)
        & (panel.spread_exit_points > 0)
    )


def observation_mask(panel: Panel, direction: np.ndarray) -> np.ndarray:
    """Slots carrying an evaluated decision: a state AND a markable exit."""
    return quote_mask(panel) & (direction != 0)


def gross_markout_bps(panel: Panel, direction: np.ndarray) -> np.ndarray:
    """Side-signed midpoint return in bps of the entry midpoint."""
    raw = (panel.mid_exit_points - panel.mid_entry_points) / panel.mid_entry_points * BPS_PER_UNIT
    return raw * direction


def friction_bps(panel: Panel, direction: np.ndarray, multiplier: float) -> np.ndarray:
    """Observed-spread round-trip friction in bps, via the envelope's own arithmetic.

    ``1/2 S_entry + 1/2 S_exit`` in USD per contract over the entry price in USD per
    contract. The contract multiplier is carried on the spreads and the price alike
    (they are the instrument's own ``USD = index points x ContractMultiplier``
    conversion) and cancels in the ratio, so the result is exactly the quoted-spread
    friction in bps while ``envelope`` still owns the arithmetic.
    """
    out = np.full(panel.slot.shape, np.nan, dtype=float)
    usable = quote_mask(panel) & (direction != 0)
    for index in np.flatnonzero(usable):
        out[index] = envelope.midpoint_markout_friction_bps(
            panel.spread_entry_points[index] * multiplier,
            panel.spread_exit_points[index] * multiplier,
            panel.mid_entry_points[index] * multiplier,
        )
    return out


# ----------------------------------------------------------------------- statistics


def clustered_ci(values: np.ndarray, block_id: np.ndarray, resamples: int, seed: int) -> dict:
    """Instrument x contiguous-time-block cluster bootstrap of the mean.

    The block (``block_slots`` decision instants long) is the declared dependence unit:
    overlapping forward returns inside one block share a price path, so they are
    resampled together by ``calculate.block_bootstrap_ci`` rather than as independent
    draws.
    """
    valid = np.isfinite(values)
    if not valid.any():
        return {"se_bps": None, "ci_low_bps": None, "ci_high_bps": None, "clusters": 0}
    labels, inverse = np.unique(block_id[valid], return_inverse=True)
    weights = np.bincount(inverse)
    cell_means = np.bincount(inverse, weights=values[valid]) / weights
    se, low, high = calculate.block_bootstrap_ci(
        cell_means, weights.astype(float), resamples, seed
    )
    return {
        "se_bps": float(se),
        "ci_low_bps": float(low),
        "ci_high_bps": float(high),
        "clusters": int(labels.size),
    }


def _mean(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    return float(np.mean(finite)) if finite.size else None


def seed_for(freeze: Mapping, horizon_s: int, state_index: int = 0) -> int:
    """The frozen seed schedule: base + horizon x stride + state index."""
    return (
        int(freeze["statistics"]["seed"])
        + int(horizon_s) * int(freeze["statistics"]["seed_stride"])
        + int(state_index)
    )


def summarise(panel: Panel, direction: np.ndarray, horizon_s: int, freeze: Mapping) -> dict:
    """One horizon's evaluated figures: coverage, gross, friction, interval and null."""
    valid = observation_mask(panel, direction)
    gross = gross_markout_bps(panel, direction)[valid]
    cost = friction_bps(panel, direction, 1.0)[valid]
    if valid.any():
        interval = clustered_ci(gross, panel.block_id[valid], int(freeze["statistics"]["resamples"]),
                               seed_for(freeze, horizon_s))
    else:
        interval = {"se_bps": None, "ci_low_bps": None, "ci_high_bps": None, "clusters": 0}
    unconditional = (panel.mid_exit_points - panel.mid_entry_points) / panel.mid_entry_points * BPS_PER_UNIT
    return {
        "horizon_s": int(horizon_s),
        "decision_slots": int(panel.slot.size),
        "quote_coverage": float(quote_mask(panel).mean()),
        "observation_coverage": float(valid.mean()),
        "observations": int(valid.sum()),
        "state_long": int(((direction > 0) & valid).sum()),
        "state_short": int(((direction < 0) & valid).sum()),
        "gross_markout_bps": _mean(gross),
        "gross_se_bps": interval["se_bps"],
        "gross_ci_low_bps": interval["ci_low_bps"],
        "gross_ci_high_bps": interval["ci_high_bps"],
        "clusters": interval["clusters"],
        "unconditional_markout_bps": _mean(unconditional[quote_mask(panel)]),
        "friction_c0_bps": _mean(cost),
    }


# -------------------------------------------------------------------- classification


def classify(
    gross_bps: float,
    low_bps: float,
    high_bps: float,
    c0_bps: float,
    notional_usd: float,
    coverage_failures: Sequence[str],
    window: Mapping,
    freeze: Mapping,
) -> dict:
    """Apply the preregistered rule, then the coverage gate, then the sample-scope rule.

    The materiality rule itself is ``envelope.classify_materiality`` -- not restated
    here in any other form, and evaluated in both reported units so that a unit mistake
    cannot pass silently. Order is frozen: the coverage floor is a *precondition* (a
    window that is not covered is not measured, and its figures are reported as context
    only), and a nominal SURVIVE_PROVISIONAL is downgraded for scope because one
    admitted 10-minute window cannot carry survival.
    """
    gross_usd = envelope.bps_to_usd(gross_bps, notional_usd)
    c0_usd = envelope.bps_to_usd(c0_bps, notional_usd)
    in_usd = envelope.classify_materiality(
        gross_usd, envelope.bps_to_usd(low_bps, notional_usd), envelope.bps_to_usd(high_bps, notional_usd), c0_usd
    )
    in_bps = envelope.classify_materiality(gross_bps, low_bps, high_bps, c0_bps)
    if in_usd["verdict"] != in_bps["verdict"]:
        raise MeasurementError("unit conversion changed the verdict; refusing to report")

    nominal = in_usd["verdict"]
    if nominal == KILL:
        clause = CLAUSE_NON_POSITIVE_GROSS if gross_bps <= 0 else CLAUSE_UPPER_AT_OR_BELOW_C0
    elif nominal == SURVIVE:
        clause = CLAUSE_LOWER_ABOVE_C0
    else:
        clause = CLAUSE_STRADDLES_C0

    verdict, scope = nominal, SCOPE_SINGLE_WINDOW_ONLY
    if coverage_failures:
        verdict = VERDICT_INDETERMINATE_COVERAGE
        clause = f"{CLAUSE_COVERAGE_FLOOR}:{','.join(coverage_failures)}"
    elif nominal == SURVIVE:
        verdict = VERDICT_INDETERMINATE_COVERAGE
        clause = f"{CLAUSE_SINGLE_WINDOW}: nominal SURVIVE_PROVISIONAL is not admissible from one window"
    elif nominal == KILL:
        scope = SCOPE_SAMPLE_SCOPED_KILL

    return {
        "verdict": verdict,
        "nominal_verdict_before_scope_and_coverage": nominal,
        "clause": clause,
        "scope": scope,
        "scope_statement": freeze["scope"]["statement"],
        "coverage_gate_passed": not coverage_failures,
        "coverage_failures": list(coverage_failures),
        "primary_horizon_s": int(freeze["horizons"]["primary_s"]),
        "rule": in_usd["rule"],
        "significance_is_decision_criterion": False,
        "usd": {
            "gross_usd": gross_usd,
            "uncertainty_lo_usd": in_usd["uncertainty_lo_usd"],
            "uncertainty_hi_usd": in_usd["uncertainty_hi_usd"],
            "c0_usd": c0_usd,
            "c_star_usd": in_usd["c_star_usd"],
            "notional_usd_per_contract": notional_usd,
        },
        "bps": {
            "gross_bps": gross_bps,
            "uncertainty_lo_bps": in_bps["uncertainty_lo_usd"],
            "uncertainty_hi_bps": in_bps["uncertainty_hi_usd"],
            "c0_bps": c0_bps,
            "c_star_bps": in_bps["c_star_usd"],
        },
        "scoped_boundary": {
            "round_trip_required_bps": c0_bps,
            "window": f"{window['start_utc']}..{window['end_utc']}",
            "contract": window["symbol"],
            "horizon_s": int(freeze["horizons"]["primary_s"]),
            "candidate_id": freeze["candidate_id"],
        },
    }


# ------------------------------------------------------------------ C0 / C1 envelope


def c0_items(freeze: Mapping) -> list[dict]:
    """The declared mandatory charges, each classified by the envelope's own rule.

    Every declared item that has no verified amount lands in ``C1`` through
    ``CostItem.cost_class()`` -- an unknown cost is never zero.
    """
    rows = []
    for declared in freeze["cost_items"]:
        item = envelope.CostItem(
            id=declared["id"],
            name=declared["name"],
            unit=declared["unit"],
            value=declared["value"],
            side=declared.get("side", "both"),
            provenance=envelope.Provenance(**declared["provenance"]),
            mandatory=declared.get("mandatory", True),
            varies_with_volume=declared.get("varies_with_volume", False),
            varies_with_account_state=declared.get("varies_with_account_state", False),
            notes=declared.get("notes", ""),
        )
        row = envelope.reference_path_scenario(item)
        row["c0_eligible"] = item.cost_class() == envelope.CLASS_C0
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- audit


def grid_causality_audit(data_dir: str, instrument_id: int, price_scale: float) -> dict:
    """Independent check that the admitted grid is a *prevailing* (causal) quote state.

    Rebuilds level 1 from the direct level-1 increment rows whose venue send time is
    ``<= t`` -- an artefact-only, strictly-past replay -- and compares its midpoint with
    the admitted grid at the same instants. A grid built with any lookahead cannot
    agree with a strictly-past reconstruction.
    """
    grid = load_spread_grid(os.path.join(data_dir, "spread_grid.csv"))
    level_one = load_level_one(os.path.join(data_dir, "bbo_increments.csv"), instrument_id)
    mid = (grid["bid_mantissa"] + grid["ask_mantissa"]) * 0.5 * price_scale
    rebuilt_side = {}
    for side in ("B", "A"):
        mask = level_one["side"] == side
        times = level_one["time_ns"][mask]
        prices = level_one["price"][mask]
        at_or_before = np.searchsorted(times, grid["ts_ns"], side="right") - 1
        values = np.full(grid["ts_ns"].shape, np.nan)
        found = at_or_before >= 0
        values[found] = prices[at_or_before[found]]
        rebuilt_side[side] = values
    rebuilt = (rebuilt_side["B"] + rebuilt_side["A"]) * 0.5 * price_scale
    compared = np.isfinite(rebuilt) & np.isfinite(mid)
    delta = np.abs(rebuilt[compared] - mid[compared])
    return {
        "instants_compared": int(compared.sum()),
        "instants_grid_only": int((np.isfinite(mid) & ~np.isfinite(rebuilt)).sum()),
        "instants_rebuild_only": int((np.isfinite(rebuilt) & ~np.isfinite(mid)).sum()),
        "agreement_fraction": float((delta == 0).mean()) if delta.size else None,
        "nonzero_deviations": int((delta > 0).sum()),
        "max_abs_deviation_points": float(delta.max()) if delta.size else None,
        "note": (
            "strictly-past direct level-1 replay vs the admitted grid; a non-zero deviation marks "
            "an instant where the producer's maintained book used a deeper level or a compaction "
            "step that direct level-1 rows alone do not express"
        ),
    }


# ----------------------------------------------------------------------------- run


def declared_freeze_sha256(freeze_path: str) -> str:
    """The hash sealed beside the contract, in the campaign's ``freeze.sha256`` form."""
    companion = (
        freeze_path[: -len(".json")] + ".sha256"
        if freeze_path.endswith(".json")
        else freeze_path + ".sha256"
    )
    if not os.path.exists(config_module.repo_path(companion)):
        raise MeasurementError(f"sealed contract hash file is missing: {companion}")
    with open(config_module.repo_path(companion), "r") as handle:
        return handle.read().split()[0]


def verify_freeze(freeze: Mapping, freeze_path: str) -> dict:
    """Re-hash the sealed contract, this module and every declared input."""
    sealed = freeze["code_sha256"][_MODULE_PATH]
    observed_module = sha256_file(_MODULE_PATH)
    if observed_module != sealed:
        raise MeasurementError(
            f"analysis module hash does not match the sealed contract: {observed_module} != {sealed}"
        )
    inputs = {}
    for relative, declared in freeze["input_sha256"].items():
        current = sha256_file(relative)
        inputs[relative] = {"declared": declared, "observed": current, "unchanged": current == declared}
        if current != declared:
            raise MeasurementError(f"declared input changed since the freeze: {relative}")
    reuse = {}
    for relative, declared in freeze["reused_module_sha256"].items():
        current = sha256_file(relative)
        reuse[relative] = {"declared": declared, "observed": current, "unchanged": current == declared}
    observed_contract = sha256_file(freeze_path)
    declared_contract = declared_freeze_sha256(freeze_path)
    if observed_contract != declared_contract:
        raise MeasurementError(
            f"sealed contract changed since the freeze: {observed_contract} != {declared_contract}"
        )
    return {
        "analysis_module": {"path": _MODULE_PATH, "declared": sealed, "observed": observed_module,
                            "unchanged": True},
        "inputs": inputs,
        "reused_modules": reuse,
        "sealed_contract": {
            "path": freeze_path,
            "declared": declared_contract,
            "observed": observed_contract,
            "unchanged": True,
        },
    }


def run(freeze: Mapping, freeze_path: str) -> dict:
    """Execute the frozen measurement once. Every parameter comes from the freeze."""
    integrity = verify_freeze(freeze, freeze_path)
    data_dir = freeze["data"]["derived_dir"]
    manifest = load_manifest(data_dir)
    instrument_id = int(manifest["instrument"]["security_id"])
    price_scale = float(freeze["data"]["price_scale_index_points_per_mantissa_unit"])
    multiplier = float(freeze["data"]["point_value_usd"])
    step_ns = int(freeze["grid_step_ns"])
    start_ns = int(manifest["session"]["session_open_ns"])
    end_ns = int(manifest["session"]["session_close_ns"])

    grid = load_spread_grid(os.path.join(data_dir, freeze["data"]["spread_grid"]))
    if int(grid["ts_ns"][0]) != start_ns:
        raise MeasurementError("grid does not start at the admitted session open")
    if int(grid["ts_ns"][1] - grid["ts_ns"][0]) != step_ns:
        raise MeasurementError("grid step does not match the frozen grid step")
    if int(grid["ts_ns"][-1]) + step_ns != end_ns:
        raise MeasurementError("grid does not span the admitted window")

    passes = {}
    for label, clock in (("primary", freeze["clock"]["primary"]),
                         ("capture_conservative", freeze["clock"]["robustness"])):
        trades = load_trades(os.path.join(data_dir, freeze["data"]["trades"]), instrument_id, clock)
        flow = cumulative_flow(trades)
        panels, rows = {}, []
        for horizon_s in freeze["horizons_s"]:
            panel = build_panel(grid, flow, int(horizon_s), int(freeze["state"]["lookback_ns"]),
                                int(freeze["statistics"]["block_slots"]), price_scale, step_ns)
            direction = state_direction(panel)
            panels[int(horizon_s)] = (panel, direction)
            rows.append(summarise(panel, direction, int(horizon_s), freeze))
        passes[label] = {"trades": int(trades["time_ns"].size), "rows": rows, "panels": panels}

    primary = passes["primary"]
    by_horizon = {row["horizon_s"]: row for row in primary["rows"]}
    primary_s = int(freeze["horizons"]["primary_s"])
    headline = by_horizon[primary_s]
    if not headline["observations"]:
        raise MeasurementError("no evaluated observation at the primary horizon")

    floors = freeze["coverage_floor"]
    coverage_failures = []
    if headline["quote_coverage"] < float(floors["quote_coverage_min"]):
        coverage_failures.append("quote_coverage")
    if headline["observation_coverage"] < float(floors["observation_coverage_min"]):
        coverage_failures.append("observation_coverage")
    if headline["observations"] < int(floors["min_observations"]):
        coverage_failures.append("observations")

    panel, direction = primary["panels"][primary_s]
    evaluated_mid = panel.mid_entry_points[observation_mask(panel, direction)]
    notional_usd = float(np.mean(evaluated_mid)) * multiplier

    classification = classify(
        headline["gross_markout_bps"], headline["gross_ci_low_bps"], headline["gross_ci_high_bps"],
        headline["friction_c0_bps"], notional_usd, coverage_failures,
        {"start_utc": freeze["window"]["start_utc"], "end_utc": freeze["window"]["end_utc"],
         "symbol": manifest["instrument"]["symbol"]},
        freeze,
    )

    states = []
    for horizon_s, (panel_h, direction_h) in sorted(primary["panels"].items()):
        for index, (name, selector) in enumerate(((STATE_LONG, direction_h > 0),
                                                  (STATE_SHORT, direction_h < 0)), start=1):
            valid = observation_mask(panel_h, direction_h) & selector
            gross = gross_markout_bps(panel_h, direction_h)[valid]
            if valid.sum() < int(freeze["statistics"]["min_state_observations"]):
                states.append({"horizon_s": horizon_s, "state": name, "observations": int(valid.sum()),
                               "reported": False,
                               "reason": "below the frozen minimum state observations",
                               "gross_markout_bps": _mean(gross)})
                continue
            interval = clustered_ci(gross, panel_h.block_id[valid], int(freeze["statistics"]["resamples"]),
                                    seed_for(freeze, horizon_s, index))
            states.append({"horizon_s": horizon_s, "state": name, "reported": True,
                           "observations": int(valid.sum()), "gross_markout_bps": _mean(gross),
                           "gross_se_bps": interval["se_bps"],
                           "gross_ci_low_bps": interval["ci_low_bps"],
                           "gross_ci_high_bps": interval["ci_high_bps"],
                           "clusters": interval["clusters"]})

    items = c0_items(freeze)
    return clean({
        "experiment_id": freeze["experiment_id"],
        "candidate_id": freeze["candidate_id"],
        "branch": freeze["branch"],
        "verdict": classification["verdict"],
        "contract": {
            "consume_rule": freeze["clock"]["consume_rule"],
            "horizons_s": list(freeze["horizons_s"]),
            "primary_horizon_s": primary_s,
            "state": dict(freeze["state"]),
            "friction": dict(freeze["friction"]),
            "outcome": freeze["outcome"],
            "coverage_floor": dict(floors),
            "statistics": dict(freeze["statistics"]),
        },
        "window": {
            "start_utc": freeze["window"]["start_utc"],
            "end_utc": freeze["window"]["end_utc"],
            "session_open_ns": start_ns,
            "session_close_ns": end_ns,
            "instrument": manifest["instrument"]["symbol"],
            "instrument_id": instrument_id,
            "venue": manifest["instrument"]["venue"],
            "admitted_grid_coverage": manifest["coverage"]["ratio"],
            "grid_points": int(grid["ts_ns"].size),
        },
        "headline": {
            "horizon_s": primary_s,
            "gross_markout_bps": headline["gross_markout_bps"],
            "ci_low_bps": headline["gross_ci_low_bps"],
            "ci_high_bps": headline["gross_ci_high_bps"],
            "se_bps": headline["gross_se_bps"],
            "c0_bps": headline["friction_c0_bps"],
            "c_star_bps": headline["gross_markout_bps"] - headline["friction_c0_bps"],
            "observations": headline["observations"],
            "clusters": headline["clusters"],
        },
        "per_horizon": primary["rows"],
        "per_state": states,
        "null_baseline": {
            "unconditional_markout_bps_by_horizon": {
                str(row["horizon_s"]): row["unconditional_markout_bps"] for row in primary["rows"]
            },
            "note": ("the side-ignoring unconditional markout is reported so the conditional gross can "
                     "be read against it; it is not an input to the classification"),
        },
        "c0_c1": {
            "friction_c0_bps": headline["friction_c0_bps"],
            "friction_basis": freeze["friction"]["basis"],
            "verified_mandatory_charge_items": [row for row in items if row["c0_eligible"]],
            "unresolved_c1_items": [row for row in items if not row["c0_eligible"]],
            "c1_value": None,
            "c1_status": envelope.STATUS_UNKNOWN,
            "note": ("no independently verified account-independent mandatory charge exists for this "
                     "contract in this environment, so C0 is the measured observed-spread friction "
                     "alone and every declared venue/clearing/FCM charge stays in C1 with an UNKNOWN "
                     "value; an unknown cost is never added as zero"),
            "c_star_usd": envelope.break_even_residual(
                envelope.bps_to_usd(headline["gross_markout_bps"], notional_usd),
                envelope.bps_to_usd(headline["friction_c0_bps"], notional_usd)),
            "c_star_bps": headline["gross_markout_bps"] - headline["friction_c0_bps"],
            "c1_sensitivity": envelope.c1_sensitivity(
                envelope.bps_to_usd(headline["gross_markout_bps"], notional_usd),
                envelope.bps_to_usd(headline["friction_c0_bps"], notional_usd),
                [float(level) for level in freeze["unresolved_c1_scenarios_usd"]]),
            "c1_scenarios_usd": [float(level) for level in freeze["unresolved_c1_scenarios_usd"]],
            "c1_scenario_basis": freeze["unresolved_c1_scenarios_basis"],
        },
        "classification": classification,
        "significance": envelope.significance_against_zero(headline["gross_markout_bps"],
                                                          headline["gross_se_bps"]),
        "robustness": {
            "clock": freeze["clock"]["robustness"],
            "reason": freeze["clock"]["robustness_reason"],
            "rows": passes["capture_conservative"]["rows"],
        },
        "validity_checks": {
            "freeze_integrity": integrity,
            "grid_causality_audit": grid_causality_audit(data_dir, instrument_id, price_scale),
            "trades_used_primary": primary["trades"],
            "trades_used_robustness": passes["capture_conservative"]["trades"],
            "causal_consumption": ("the state uses only trades stamped at or before the decision "
                                   "instant and the outcome only quotes stamped at or before the exit "
                                   "instant; no future message enters either side"),
        },
    })


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen CME ES H3 OFI materiality measurement (branch A).")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="execute the sealed measurement")
    run_parser.add_argument("--freeze", required=True)
    run_parser.add_argument("--out", required=True)
    audit_parser = sub.add_parser("audit", help="independent grid-causality audit (no outcome)")
    audit_parser.add_argument("--data-dir", default="M2/data/derived_es/2023-07-17T133000Z")
    args = parser.parse_args(argv)

    if args.command == "audit":
        manifest = load_manifest(args.data_dir)
        report = grid_causality_audit(
            args.data_dir, int(manifest["instrument"]["security_id"]),
            float(manifest["spread_distribution"]["price_scale_index_points_per_mantissa_unit"]))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    with open(config_module.repo_path(args.freeze), "r") as handle:
        freeze = json.load(handle)
    results = run(freeze, args.freeze)
    target = config_module.repo_path(args.out)
    with open(target, "w") as handle:
        json.dump(results, handle, indent=2, sort_keys=True)
        handle.write("\n")
    headline = results["headline"]
    print(f"{results['verdict']}  {results['candidate_id']}  h={headline['horizon_s']}s  "
          f"g={headline['gross_markout_bps']:.4f} bps  C0={headline['c0_bps']:.4f} bps  "
          f"C*={headline['c_star_bps']:.4f} bps  n={headline['observations']}")
    print(f"[{ ', '.join(f'{h}s={by_h:.4f}' for h, by_h in ((r['horizon_s'], r['gross_markout_bps']) for r in results['per_horizon']))} ]")
    print(f"written: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
