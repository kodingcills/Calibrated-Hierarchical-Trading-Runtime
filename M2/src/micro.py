"""M2-2 microprice economic-materiality calculation.

Answers one question with the already-owned development tape: is the realized
predictive magnitude of the registered Nasdaq large-tick microprice signal large
enough to plausibly clear the aggressive execution friction measured in M2-0.6?

Estimator (frozen in ``M2/experiments/M2-2-MICRO-MATERIALITY/freeze.json``, sealed
before any canonical economics were inspected):

    p_micro(t) = mid(t) + g1(X_t)
    X_t        = (imbalance bin, spread class)              -- 10 x 2 cells
    g1(X)      = E[ mid2(tau1) - mid2(t) | X_t = X ]         -- Stoikov first step
    tau1       = the first mid-price change after t

``g1`` is estimated with an EXPANDING PRIOR-SESSION window: at every observation the
estimate uses only observations strictly earlier in the session, refitted on a fixed
5-minute cadence, and a cell with fewer than the frozen minimum of resolved prior
observations carries no estimate (the observation is then counted as undefined, never
imputed). Nothing in the estimator uses a future price.

The signal is the side-signed future mid move of the microprice's own direction:

    D_t         = p_micro(t) - mid(t) = g1(X_t)/2        (g1 is carried in mid2 units)
    side_t      = sign(D_t)
    signal(h)   = E[ side_t * (mid(t+h) - mid(t))/mid(t) * 10000 ]   bps

Everything else is reused, not rebuilt: the population and the declared imbalance
bins come from the M2-0.6 universe-proxy machinery, and the execution arithmetic --
the aggressive cross-to-cross round trip, the structural cost floor and the
clairvoyant oracle ceiling -- is ``M2/src/feasibility.py`` unchanged.

No model is trained, no threshold is optimised, no horizon or state is selected on
its result, and no profitability claim is produced.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Sequence

import numpy as np
import pyarrow.parquet as pq

from . import calculate
from . import config as config_module
from . import feasibility

PRIMARY_SUBSET = "M2/output/univproxy/data_quality/large_tick_proxy_subset.csv"
FREEZE_PATH = "M2/experiments/M2-2-MICRO-MATERIALITY/freeze.json"

DECISION_COLUMNS = [
    "ts_ns",
    "locate",
    "mid2_raw",
    "spread_raw",
    "imbalance",
    "next_move_delta_raw",
    "next_move_resolved",
]

BAND_LABELS = [
    "abs_dev_over_half_spread_lt_0.02",
    "0.02_to_0.05",
    "0.05_to_0.10",
    "0.10_to_0.20",
    "gte_0.20",
]


def write_csv(path: str, rows: Sequence[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", newline="") as handle:
            handle.write("empty:no_rows\n")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_decision_columns(derived: str) -> dict[str, np.ndarray]:
    table = pq.read_table(os.path.join(derived, "decisions.parquet"), columns=DECISION_COLUMNS)
    return {name: table[name].to_numpy(zero_copy_only=False) for name in table.column_names}


# ------------------------------------------------------------------- estimator
def state_cell(
    imbalance: np.ndarray,
    spread_raw: np.ndarray,
    state_valid: np.ndarray,
    configuration: dict,
) -> tuple[np.ndarray, list[str], list[str]]:
    """Mixed-radix cell code over (imbalance bin, spread class); -1 when undefined."""
    bin_codes, bin_labels = feasibility.imbalance_bin_codes(imbalance, state_valid, configuration)
    spread_labels = feasibility.spread_class_labels()
    spread_codes = np.where(
        state_valid, feasibility.spread_class_codes(spread_raw, int(configuration["tick_raw"])), -1
    )
    cell = np.where(
        (bin_codes >= 0) & (spread_codes >= 0),
        bin_codes * len(spread_labels) + np.maximum(spread_codes, 0),
        -1,
    )
    return cell, bin_labels, spread_labels


def expanding_calibration(
    cell: np.ndarray,
    block: np.ndarray,
    delta: np.ndarray,
    usable: np.ndarray,
    n_cells: int,
    n_blocks: int,
    minimum_observations: int,
) -> np.ndarray:
    """Exclusive-prefix mean of ``delta`` per (cell, block).

    ``g1[c, b]`` uses only observations in blocks ``< b``: the estimate attached to a
    block is a function of strictly earlier session data, so no observation can
    calibrate itself. A cell/block pair with fewer than ``minimum_observations`` prior
    resolved observations is NaN, which is never imputed.
    """
    sums = np.zeros(n_cells * n_blocks, dtype=np.float64)
    counts = np.zeros(n_cells * n_blocks, dtype=np.float64)
    selector = usable & (cell >= 0)
    flat = cell[selector] * n_blocks + block[selector]
    sums += np.bincount(flat, weights=delta[selector].astype(np.float64), minlength=sums.size)
    counts += np.bincount(flat, minlength=counts.size)
    sums = sums.reshape(n_cells, n_blocks)
    counts = counts.reshape(n_cells, n_blocks)
    prior_sums = np.cumsum(sums, axis=1) - sums
    prior_counts = np.cumsum(counts, axis=1) - counts
    with np.errstate(invalid="ignore", divide="ignore"):
        g1 = np.where(prior_counts >= minimum_observations, prior_sums / np.maximum(prior_counts, 1.0), np.nan)
    return g1


def pooled_calibration(
    cell: np.ndarray, delta: np.ndarray, usable: np.ndarray, n_cells: int
) -> np.ndarray:
    """Whole-day mean per cell: the OPTIMISTIC bound, never the causal estimate."""
    sums = np.zeros(n_cells, dtype=np.float64)
    counts = np.zeros(n_cells, dtype=np.float64)
    selector = usable & (cell >= 0)
    sums += np.bincount(cell[selector], weights=delta[selector].astype(np.float64), minlength=n_cells)
    counts += np.bincount(cell[selector], minlength=n_cells)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(counts > 0, sums / np.maximum(counts, 1.0), np.nan)


def lookup(table: np.ndarray, cell: np.ndarray, block: np.ndarray | None = None) -> np.ndarray:
    out = np.full(cell.shape, np.nan, dtype=np.float64)
    selector = cell >= 0
    if block is None:
        out[selector] = table[cell[selector]]
    else:
        out[selector] = table[cell[selector], block[selector]]
    return out


def strength_bands(ratio: np.ndarray, edges: Sequence[float]) -> np.ndarray:
    """Frozen magnitude bands over ``abs(D)/half_spread``; -1 where undefined."""
    bands = np.digitize(ratio, list(edges)[1:])
    return np.where(np.isfinite(ratio), bands, -1)


# --------------------------------------------------------------- statistics
def block_bootstrap(
    values: np.ndarray, locate: np.ndarray, block_id: np.ndarray, resamples: int, seed: int
) -> tuple[float, float, float]:
    """Dependence-aware interval over symbol x 30-minute cells (M2-0 machinery)."""
    keys = locate.astype(np.int64) * 1000 + block_id.astype(np.int64)
    _unique, inverse = np.unique(keys, return_inverse=True)
    counts = np.bincount(inverse).astype(np.float64)
    sums = np.bincount(inverse, weights=values)
    means = sums / np.maximum(counts, 1.0)
    return calculate.block_bootstrap_ci(means, counts, resamples, seed)


def _mean(values: np.ndarray) -> float:
    return float(np.mean(values)) if values.size else float("nan")


def _finite(value: float) -> float:
    return float(value) if value is not None and np.isfinite(value) else float("nan")


# ------------------------------------------------------------------- tables
def horizon_rows(
    frame: dict,
    side: np.ndarray,
    defined: np.ndarray,
    floor_label: str,
    horizons_ms: Sequence[int],
    resamples: int,
    seed: int,
) -> tuple[list[dict], dict]:
    """Table 1: the pooled microprice signal and the hurdle it must clear."""
    rows: list[dict] = []
    best = {"horizon_ms": None, "abs_signal_bps": -1.0}
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        usable = future["usable_state"]
        selected = usable & defined
        side_fee = np.where(side > 0, frame["fees"][floor_label]["long"], frame["fees"][floor_label]["short"])
        realized = side * future["future_mid_move_bps"]
        hurdle = frame["half_spread_entry_bps"] + future["half_spread_future_bps"] + side_fee
        n_selected = int(selected.sum())
        if n_selected:
            signal = _mean(realized[selected])
            se, low, high = block_bootstrap(
                realized[selected], frame["locate"][selected], frame["block_id"][selected], resamples, seed
            )
            hurdle_bps = _mean(hurdle[selected])
        else:
            signal = se = low = high = hurdle_bps = float("nan")
        ratio = _required_over_signal(hurdle_bps, signal)
        rows.append(
            {
                "horizon_ms": horizon_ms,
                "observations_valid_state": int(usable.sum()),
                "observations_defined_signal": n_selected,
                "coverage_fraction": (n_selected / int(usable.sum())) if usable.sum() else float("nan"),
                "mean_signed_mid_move_bps": signal,
                "block_bootstrap_se_bps": _finite(se),
                "ci_low_bps": _finite(low),
                "ci_high_bps": _finite(high),
                "hurdle_bps": hurdle_bps,
                "required_over_signal": ratio,
                "signal_sign_ok": bool(n_selected and signal > 0),
            }
        )
        if n_selected and np.isfinite(signal) and abs(signal) > best["abs_signal_bps"]:
            best = {"horizon_ms": horizon_ms, "abs_signal_bps": abs(signal)}
    return rows, best


def _required_over_signal(hurdle_bps: float, signal_bps: float) -> float:
    """``hurdle / abs(signal)``; a missing, zero or wrongly-signed signal is a failure."""
    if not np.isfinite(hurdle_bps) or not np.isfinite(signal_bps) or signal_bps <= 0.0:
        return float("inf")
    return float(abs(hurdle_bps / signal_bps))


def group_rows(
    frame: dict,
    codes: np.ndarray,
    labels: Sequence[str],
    dimension: str,
    side: np.ndarray,
    defined: np.ndarray,
    deviation: np.ndarray,
    floor_label: str,
    horizons_ms: Sequence[int],
    minimum_observations: int,
    resamples: int,
    seed: int,
) -> tuple[list[dict], dict]:
    """Signal, coverage and required/signal for every frozen state, every horizon."""
    rows: list[dict] = []
    best = {"dimension": None, "state": None, "horizon_ms": None, "required_over_signal": float("inf")}
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        usable = future["usable_state"]
        realized = side * future["future_mid_move_bps"]
        side_fee = np.where(side > 0, frame["fees"][floor_label]["long"], frame["fees"][floor_label]["short"])
        hurdle = frame["half_spread_entry_bps"] + future["half_spread_future_bps"] + side_fee
        for index, label in enumerate(labels):
            selected = usable & defined & (codes == index)
            n_selected = int(selected.sum())
            if not n_selected:
                continue
            signal = _mean(realized[selected])
            se, low, high = block_bootstrap(
                realized[selected], frame["locate"][selected], frame["block_id"][selected], resamples, seed
            )
            hurdle_bps = _mean(hurdle[selected])
            ratio = _required_over_signal(hurdle_bps, signal)
            rows.append(
                {
                    "dimension": dimension,
                    "state": label,
                    "horizon_ms": horizon_ms,
                    "observations": n_selected,
                    "mean_signed_mid_move_bps": signal,
                    "block_bootstrap_se_bps": _finite(se),
                    "ci_low_bps": _finite(low),
                    "ci_high_bps": _finite(high),
                    "hurdle_bps": hurdle_bps,
                    "required_over_signal": ratio,
                    "mean_abs_deviation_over_half_spread": _mean(np.abs(deviation[selected])),
                    "mean_abs_microprice_adjustment_bps": _mean(
                        np.abs(deviation[selected]) * frame["spread_bps"][selected] / 2.0
                    ),
                    "mean_price_usd": _mean(frame["price_usd"][selected]),
                    "mean_spread_bps": _mean(frame["spread_bps"][selected]),
                    "eligible_for_best": bool(n_selected >= minimum_observations),
                }
            )
            if n_selected >= minimum_observations and ratio < best["required_over_signal"]:
                best = {
                    "dimension": dimension,
                    "state": label,
                    "horizon_ms": horizon_ms,
                    "required_over_signal": float(ratio),
                }
    return rows, best


def oracle_rows(
    frame: dict, floor_label: str, horizons_ms: Sequence[int]
) -> list[dict]:
    """Table 3: the clairvoyant aggressive ceiling, reusing the M2-0.6 arithmetic."""
    rows: list[dict] = []
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        usable = future["usable_state"]
        n = int(usable.sum())
        if not n:
            continue
        net = future[f"oracle_net_{floor_label}_bps"][usable]
        gross = future["oracle_gross_bps"][usable]
        traded = gross > 0.0
        row = {
            "horizon_ms": horizon_ms,
            "observations": n,
            "oracle_net_floor_bps_per_observation": float(np.mean(net)),
            "oracle_trade_coverage": float(np.mean(traded)),
            "oracle_net_floor_bps_per_trade": float(np.mean(net[traded])) if traded.any() else float("nan"),
            "oracle_gross_bps_per_trade": float(np.mean(gross[traded])) if traded.any() else float("nan"),
        }
        for label in feasibility.accessible_labels(frame["ledger"]):
            net_label = future[f"oracle_net_{label}_bps"][usable]
            row[f"oracle_net_{label}_bps_per_observation"] = float(np.mean(net_label))
            row[f"oracle_net_{label}_bps_per_trade"] = (
                float(np.mean(net_label[traded])) if traded.any() else float("nan")
            )
        rows.append(row)
    return rows


# ---------------------------------------------------------------------- run
def evaluate(
    configuration: dict,
    ledger: dict,
    derived: str,
    subset_path: str | None,
    label: str,
) -> dict:
    decisions = load_decision_columns(derived)
    columns = feasibility.load_execution_columns(derived, configuration)
    if not np.array_equal(decisions["ts_ns"], columns["ts_ns"]) or not np.array_equal(
        decisions["locate"], columns["locate"]
    ):
        raise ValueError("decision rows and delay rows are not aligned; the calculation refuses to join them")
    if subset_path:
        locates = np.asarray(
            sorted(
                int(row["locate"])
                for row in csv.DictReader(open(config_module.repo_path(subset_path), newline=""))
                if row.get("locate")
            ),
            dtype=decisions["locate"].dtype,
        )
        columns, subset_info = feasibility.apply_symbol_subset(columns, subset_path)
        mask = np.isin(decisions["locate"], locates)
        decisions = {name: values[mask] for name, values in decisions.items()}
    else:
        subset_info = {"subset": None}

    frame = feasibility.build_frame(columns, configuration, ledger)
    frame["ledger"] = ledger

    estimator = configuration["microprice"]
    horizons_ms = list(configuration["horizons_ms"])
    resamples = int(configuration["statistics"]["bootstrap"]["resamples"])
    seed = int(configuration["statistics"]["bootstrap"]["seed"])
    minimum_calibration = int(estimator["minimum_calibration_observations"])
    minimum_state = int(estimator["minimum_state_observations"])
    frozen_thresholds = load_frozen_thresholds()
    if minimum_state != int(frozen_thresholds["minimum_state_observations"]):
        raise ValueError(
            "the config's minimum_state_observations disagrees with the sealed freeze; "
            "the calculation refuses to run under two different sample-size rules"
        )
    floor_label = feasibility.structural_label(ledger)
    refit_ns = int(estimator["refit_interval_ns"])
    session_start = int(configuration["session"]["continuous_start_ns"])
    session_end = int(configuration["session"]["continuous_end_ns"])
    n_blocks = int((session_end - session_start + refit_ns - 1) // refit_ns)

    state_valid = frame["state_valid"]
    cell, bin_labels, spread_labels = state_cell(
        frame["imbalance"], frame["spread_raw"], state_valid, configuration
    )
    n_cells = len(bin_labels) * len(spread_labels)
    block = np.clip(((decisions["ts_ns"] - session_start) // refit_ns).astype(np.int64), 0, n_blocks - 1)

    resolved = decisions["next_move_resolved"].astype(bool)
    delta = decisions["next_move_delta_raw"].astype(np.float64)
    calibration_usable = resolved & (cell >= 0) & state_valid
    g1 = expanding_calibration(
        cell, block, delta, calibration_usable, n_cells, n_blocks, minimum_calibration
    )
    g1_optimistic = pooled_calibration(cell, delta, calibration_usable, n_cells)
    adjustment_raw = lookup(g1, cell, block)
    optimistic_raw = lookup(g1_optimistic, cell)

    spread_raw = frame["spread_raw"].astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        deviation = adjustment_raw / np.maximum(spread_raw, 1.0)
    deviation_optimistic = optimistic_raw / np.maximum(spread_raw, 1.0)
    band = strength_bands(deviation, estimator["strength_band_edges"])
    band_optimistic = strength_bands(deviation_optimistic, estimator["strength_band_edges"])

    # A microprice direction exists only where the estimator has a non-zero calibrated
    # adjustment AND the arrival state carries a direction at all: an exactly balanced
    # book (imbalance == 0) has no side to trade, which is the M2-0.6 execution filter.
    side = np.where(adjustment_raw > 0, 1.0, np.where(adjustment_raw < 0, -1.0, np.nan))
    defined = state_valid & np.isfinite(side) & (frame["imbalance"] != 0.0)
    side_optimistic = np.where(optimistic_raw > 0, 1.0, np.where(optimistic_raw < 0, -1.0, np.nan))
    defined_optimistic = state_valid & np.isfinite(side_optimistic) & (frame["imbalance"] != 0.0)

    horizon_table, best_horizon = horizon_rows(
        frame, side, defined, floor_label, horizons_ms, resamples, seed
    )
    optimistic_horizon_table, _ = horizon_rows(
        frame, side_optimistic, defined_optimistic, floor_label, horizons_ms, resamples, seed + 1
    )

    band_table, best_band = group_rows(
        frame,
        band,
        BAND_LABELS,
        "strength_band",
        side,
        defined,
        deviation,
        floor_label,
        horizons_ms,
        minimum_state,
        resamples,
        seed + 2,
    )
    cell_table, best_cell = group_rows(
        frame,
        cell,
        [f"{bin_labels[c // len(spread_labels)]}|{spread_labels[c % len(spread_labels)]}" for c in range(n_cells)],
        "imbalance_x_spread",
        side,
        defined,
        deviation,
        floor_label,
        horizons_ms,
        minimum_state,
        resamples,
        seed + 3,
    )
    oracle = oracle_rows(frame, floor_label, horizons_ms)

    best_state = min(
        [entry for entry in (best_band, best_cell) if entry["dimension"]],
        key=lambda entry: entry["required_over_signal"],
        default={"dimension": None, "state": None, "horizon_ms": None, "required_over_signal": float("inf")},
    )
    pooled_by_horizon = {row["horizon_ms"]: row for row in horizon_table}

    diagnostics = {
        "population": label,
        "subset": subset_info,
        "observations_total": int(frame["state_valid"].size),
        "observations_valid_state": int(state_valid.sum()),
        "observations_in_state_space": int((cell >= 0).sum()),
        "observations_with_calibration": int(np.isfinite(adjustment_raw).sum()),
        "observations_with_calibration_optimistic": int(np.isfinite(optimistic_raw).sum()),
        "next_move_resolved_fraction": float(resolved.mean()),
        "next_move_resolved_and_cell_fraction": float(calibration_usable.mean()),
        "calibration_blocks": n_blocks,
        "state_cells": n_cells,
        "band_counts": {BAND_LABELS[i]: int((band == i).sum()) for i in range(len(BAND_LABELS))},
        "band_counts_optimistic": {
            BAND_LABELS[i]: int((band_optimistic == i).sum()) for i in range(len(BAND_LABELS))
        },
        "mean_abs_deviation_over_half_spread": _mean(np.abs(deviation[np.isfinite(deviation)])),
        "sign_agreement_with_imbalance": float(
            np.mean(np.sign(adjustment_raw[defined]) == np.sign(frame["imbalance"][defined]))
        )
        if defined.any()
        else float("nan"),
        "estimator_id": estimator["estimator_id"],
        "structural_floor_label": floor_label,
    }

    return {
        "population": label,
        "horizon_table": horizon_table,
        "optimistic_horizon_table": optimistic_horizon_table,
        "band_table": band_table,
        "cell_table": cell_table,
        "oracle_table": oracle,
        "best_horizon": best_horizon,
        "best_band": best_band,
        "best_cell": best_cell,
        "best_state": best_state,
        "diagnostics": diagnostics,
        "pooled_by_horizon": pooled_by_horizon,
        "bin_labels": bin_labels,
        "spread_labels": spread_labels,
        "band_labels": BAND_LABELS,
    }


def load_frozen_thresholds() -> dict:
    """The decision rule is read from the sealed contract, never from a code constant."""
    with open(config_module.repo_path(FREEZE_PATH), "r") as handle:
        freeze = json.load(handle)
    thresholds = dict(freeze["thresholds"])
    thresholds["freeze_sha256"] = config_module.sha256_file(FREEZE_PATH)
    thresholds["freeze_status"] = freeze["freeze_status"]
    return thresholds


def apply_frozen_rule(result: dict, thresholds: dict) -> dict:
    """Apply the precommitted kill/survive rule to one population's result.

    R_pooled is the requirement at the frozen best pooled horizon; R_best is the
    smallest requirement over the frozen states and horizons that clear the frozen
    minimum sample. The oracle contradiction test compares the clairvoyant net result
    per observation with the hurdle at the same horizon.
    """
    horizon = result["best_horizon"]["horizon_ms"]
    pooled = result["pooled_by_horizon"][horizon]
    r_pooled = float(pooled["required_over_signal"])
    r_best = float(result["best_state"]["required_over_signal"])
    oracle_by_horizon = {row["horizon_ms"]: row for row in result["oracle_table"]}
    oracle = oracle_by_horizon[horizon]
    hurdle = float(pooled["hurdle_bps"])
    oracle_ratio = (
        float(oracle["oracle_net_floor_bps_per_observation"]) / hurdle
        if np.isfinite(hurdle) and hurdle > 0.0
        else float("nan")
    )
    contradiction = bool(
        np.isfinite(oracle_ratio) and oracle_ratio >= float(thresholds["oracle_contradiction_ratio"])
    )
    killed = bool(
        r_best >= float(thresholds["r_best_kill"])
        and r_pooled >= float(thresholds["r_pooled_kill"])
        and not contradiction
    )
    if killed:
        state = "KILLED"
    elif contradiction and r_best >= float(thresholds["r_best_kill"]) and r_pooled >= float(thresholds["r_pooled_kill"]):
        state = "SURVIVES_PRE_GATE_ORACLE_CONTRADICTION"
    else:
        state = "SURVIVES_PRE_GATE"
    return {
        "population": result["population"],
        "primary_horizon_ms": horizon,
        "signal_bps_at_primary_horizon": float(pooled["mean_signed_mid_move_bps"]),
        "hurdle_bps_at_primary_horizon": hurdle,
        "R_pooled": r_pooled,
        "R_best": r_best,
        "best_state": result["best_state"],
        "oracle_ratio_at_primary_horizon": oracle_ratio,
        "oracle_contradiction": contradiction,
        "terminal_state": state,
        "thresholds": thresholds,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the M2-2 microprice materiality calculation (stage 3).")
    parser.add_argument("--config", default="M2/config/nasdaq_micro_m2_2.yaml")
    parser.add_argument("--corroborating", action="store_true", help="evaluate the 115-name liquidity scope")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    ledger = json.load(open(config_module.repo_path(configuration["cost_ledger"]["artifact"])))
    derived = config_module.repo_path(config_module.derived_dir(configuration))
    subset = None if arguments.corroborating else PRIMARY_SUBSET
    label = "liquidity_scope_115_symbols" if arguments.corroborating else "primary_population_33_symbols"
    out_dir = config_module.ensure_dirs(
        configuration, "calculations_liquidity_scope" if arguments.corroborating else "calculations"
    )

    result = evaluate(configuration, ledger, derived, subset, label)
    thresholds = load_frozen_thresholds()
    verdict = apply_frozen_rule(result, thresholds)

    write_csv(os.path.join(out_dir, "micro_signal_by_horizon.csv"), result["horizon_table"])
    write_csv(os.path.join(out_dir, "micro_signal_optimistic_by_horizon.csv"), result["optimistic_horizon_table"])
    write_csv(os.path.join(out_dir, "micro_signal_by_strength_band.csv"), result["band_table"])
    write_csv(os.path.join(out_dir, "micro_signal_by_imbalance_spread_cell.csv"), result["cell_table"])
    write_csv(os.path.join(out_dir, "micro_oracle_ceiling.csv"), result["oracle_table"])
    config_module.write_json(
        os.path.join(out_dir, "micro_materiality.json"),
        {
            "population": result["population"],
            "estimator_id": result["diagnostics"]["estimator_id"],
            "horizons_ms": list(configuration["horizons_ms"]),
            "signal_by_horizon": result["horizon_table"],
            "optimistic_signal_by_horizon": result["optimistic_horizon_table"],
            "best_horizon": result["best_horizon"],
            "best_state": result["best_state"],
            "oracle_ceiling": result["oracle_table"],
            "diagnostics": result["diagnostics"],
            "band_labels": result["band_labels"],
            "bin_labels": result["bin_labels"],
            "spread_labels": result["spread_labels"],
        },
    )
    config_module.write_json(os.path.join(out_dir, "micro_verdict.json"), verdict)
    config_module.write_json(
        os.path.join(out_dir, "calculation_status.json"),
        {
            "status": "CALCULATION_COMPLETE",
            "population": result["population"],
            "estimator_id": result["diagnostics"]["estimator_id"],
            "horizons_ms": list(configuration["horizons_ms"]),
            "structural_floor_label": result["diagnostics"]["structural_floor_label"],
            "freeze_sha256": thresholds["freeze_sha256"],
            "terminal_state": verdict["terminal_state"],
            "blockers": [],
            "note": "descriptive measurement on a single 2019 development day; no profitability claim and no current-market inference",
        },
    )
    print(json.dumps({"population": result["population"], "diagnostics": result["diagnostics"]}, indent=2, default=str))
    print(json.dumps({"best_horizon": result["best_horizon"], "best_state": result["best_state"]}, indent=2, default=str))
    print(json.dumps({"verdict": verdict}, indent=2, default=str))
    print(json.dumps({"horizons": result["horizon_table"], "oracle": result["oracle_table"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
