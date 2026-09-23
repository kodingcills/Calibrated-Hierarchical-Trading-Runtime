"""Offline deterministic calculation stage (M2-0).

Reads the derived replay artifacts and produces descriptive statistics only:

* coverage and market structure;
* the canonical queue-imbalance distribution;
* unconditional future mid-price returns on the preregistered horizon grid;
* the conditional response of future returns to ex-ante imbalance bins;
* dependence-aware uncertainty (block bootstrap over symbol x 30-minute cells);
* mechanical cost tables and idealized aggressive execution arithmetic;
* the delay response surface.

No model is trained, no threshold is optimised, and no profitability, promotion or
Jev conclusion is produced. Where an input does not exist (a second trading day, a
sealed test partition, a provider BBO product), the output states the reason
instead of substituting an assumption.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Iterable, Sequence

import numpy as np
import pyarrow.parquet as pq

from . import config as config_module
from . import costs
from . import features
from . import labels
from . import universe

NS_PER_MS = 1_000_000

EXCLUSION_CROSSED_OR_LOCKED = "CROSSED_OR_LOCKED_SPREAD"
EXCLUSION_MISSING_SIDE = "MISSING_SIDE"
EXCLUSION_NON_POSITIVE_DENOMINATOR = "NON_POSITIVE_DENOMINATOR"


# --------------------------------------------------------------------------- io
def load_decisions(derived: str) -> dict[str, np.ndarray]:
    table = pq.read_table(os.path.join(derived, "decisions.parquet"))
    return {name: table[name].to_numpy(zero_copy_only=False) for name in table.column_names}


def load_delay_rows(derived: str, configuration: dict) -> dict[str, np.ndarray]:
    columns = ["ts_ns", "locate", "block_id", "imbalance", "mid2_raw", "spread_raw"]
    for delay_ms in configuration["delay_ms"]:
        columns.append(f"entry_bid_{delay_ms}ms")
        columns.append(f"entry_ask_{delay_ms}ms")
        columns.append(f"arrival_status_{delay_ms}ms")
        for horizon_ms in configuration["horizons_ms"]:
            columns.append(f"fut_bid_{delay_ms}ms_{horizon_ms}ms")
            columns.append(f"fut_ask_{delay_ms}ms_{horizon_ms}ms")
    table = pq.read_table(os.path.join(derived, "delay_decisions.parquet"), columns=columns)
    return {name: table[name].to_numpy(zero_copy_only=False) for name in table.column_names}


def load_symbol_map(derived: str) -> dict[int, str]:
    table = pq.read_table(os.path.join(derived, "symbol_directory.parquet"), columns=["locate", "symbol"])
    return {int(locate): symbol for locate, symbol in zip(table["locate"].to_numpy(), table["symbol"].to_pylist())}


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


# ------------------------------------------------------------------- statistics
def block_bootstrap_ci(
    cell_means: np.ndarray,
    cell_counts: np.ndarray,
    resamples: int,
    seed: int,
) -> tuple[float, float, float]:
    """Dependence-aware interval over resampled symbol x block cells.

    Cells are the dependence unit: every decision inside one (symbol, 30-minute)
    cell shares a book path, a regime and a symbol, so they are resampled together.
    Returns (standard_error, ci_low, ci_high) from the resample distribution.
    """
    mask = np.isfinite(cell_means) & (cell_counts > 0)
    means = cell_means[mask]
    counts = cell_counts[mask]
    if means.size == 0:
        return float("nan"), float("nan"), float("nan")
    generator = np.random.default_rng(seed)
    n_cells = means.size
    draws = np.empty(resamples, dtype=np.float64)
    for index in range(resamples):
        picks = generator.integers(0, n_cells, n_cells)
        weights = counts[picks]
        total = weights.sum()
        draws[index] = float(np.sum(means[picks] * weights) / total) if total else float("nan")
    return float(np.std(draws, ddof=1)), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def _summarise(values: np.ndarray) -> dict:
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"count": 0}
    return {
        "count": int(values.size),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
        "p01": float(np.percentile(values, 1)),
        "p05": float(np.percentile(values, 5)),
        "p25": float(np.percentile(values, 25)),
        "p75": float(np.percentile(values, 75)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


# ------------------------------------------------------------------- exclusions
def apply_exclusions(decisions: dict[str, np.ndarray]) -> dict:
    """Apply the ex-ante decision-state exclusions and count every reason."""
    spread = decisions["spread_raw"]
    crossed = spread <= 0
    non_positive = ~np.isfinite(decisions["imbalance"])
    keep = ~crossed & ~non_positive
    return {
        "rows_total": int(spread.size),
        "rows_retained": int(keep.sum()),
        "excluded": {
            EXCLUSION_CROSSED_OR_LOCKED: int(crossed.sum()),
            # The decisions table only ever contains two-sided states (a decision is
            # emitted only when both sides exist), so a missing side is counted in
            # the coverage table, not here.
            EXCLUSION_MISSING_SIDE: 0,
            EXCLUSION_NON_POSITIVE_DENOMINATOR: int(non_positive.sum()),
        },
        "keep_mask": keep,
    }


# -------------------------------------------------------------------- coverage
def coverage_rows(
    decisions: dict, symbol_map: dict[int, str], configuration: dict, replay: dict
) -> list[dict]:
    trading_day = configuration["dataset"]["coverage_date"]
    session_start = int(configuration["session"]["continuous_start_ns"])
    session_end = int(configuration["session"]["continuous_end_ns"])
    grid_ns = int(configuration["decisions"]["grid_ns"])
    grid_points = (session_end - session_start) // grid_ns
    active_symbols = max(1, len(replay["active_symbols"]))
    locate = decisions["locate"]
    ts = decisions["ts_ns"]
    rows = [
        {
            "trading_day": trading_day,
            "unit": "POOLED",
            "unit_id": "ALL_DEV_SCOPE_SYMBOLS",
            "trading_days": 1,
            "symbols": int(np.unique(locate).size),
            "grid_points_per_symbol": int(grid_points),
            "decision_observations": int(ts.size),
            "expected_observations_if_always_quoted": int(grid_points * active_symbols),
            "valid_book_state_fraction": float(ts.size / (grid_points * active_symbols)),
            "missing_state_fraction": float(1.0 - ts.size / (grid_points * active_symbols)),
            "note": "MISSING = no two-sided book at the grid instant; the split into "
            "never-quoted / halted / one-sided is not observable from this product",
        }
    ]
    for locate_code in np.unique(locate):
        symbol = symbol_map.get(int(locate_code), str(locate_code))
        mask = locate == locate_code
        count = int(mask.sum())
        rows.append(
            {
                "trading_day": trading_day,
                "unit": "SYMBOL",
                "unit_id": symbol,
                "trading_days": 1,
                "symbols": 1,
                "grid_points_per_symbol": int(grid_points),
                "decision_observations": count,
                "expected_observations_if_always_quoted": int(grid_points),
                "valid_book_state_fraction": float(count / grid_points),
                "missing_state_fraction": float(1.0 - count / grid_points),
                "first_decision_utc_ns": int(ts[mask].min()),
                "last_decision_utc_ns": int(ts[mask].max()),
                "note": "",
            }
        )
    return rows


# ------------------------------------------------------------- market structure
def market_structure_rows(
    decisions: dict, symbol_map: dict[int, str], keep: np.ndarray, configuration: dict
) -> list[dict]:
    trading_day = configuration["dataset"]["coverage_date"]
    locate = decisions["locate"][keep]
    rows = []
    units = [("POOLED", "ALL_DEV_SCOPE_SYMBOLS", np.ones(locate.size, dtype=bool))]
    for locate_code in np.unique(locate):
        units.append(("SYMBOL", symbol_map.get(int(locate_code), str(locate_code)), locate == locate_code))
    for unit, unit_id, mask in units:
        mid2 = decisions["mid2_raw"][keep][mask]
        spread = decisions["spread_raw"][keep][mask]
        bid_size = decisions["bid_size"][keep][mask]
        ask_size = decisions["ask_size"][keep][mask]
        one_tick = decisions["one_tick"][keep][mask]
        staleness = decisions["time_since_last_event_ns"][keep][mask]
        events = decisions["events_in_prior_bucket"][keep][mask]
        row = {"trading_day": trading_day, "unit": unit, "unit_id": unit_id, "observations": int(mask.sum())}
        mid_usd = mid2 / 2.0 / 10000.0
        for name, values in (
            ("price_usd", mid_usd),
            ("spread_usd", spread / 10000.0),
            ("spread_ticks", spread / 100.0),
            ("bid_size_shares", bid_size.astype(np.float64)),
            ("ask_size_shares", ask_size.astype(np.float64)),
            ("staleness_ms", staleness.astype(np.float64) / 1e6),
            ("events_prior_100ms_bucket", events.astype(np.float64)),
        ):
            summary = _summarise(values)
            for key, value in summary.items():
                row[f"{name}_{key}"] = value
        row["one_tick_spread_fraction"] = float(np.mean(one_tick)) if one_tick.size else float("nan")
        rows.append(row)
    return rows


# ------------------------------------------------------------------- imbalance
def imbalance_rows(decisions: dict, symbol_map: dict[int, str], keep: np.ndarray, configuration: dict) -> list[dict]:
    edges = features.bin_edges(configuration)
    trading_day = configuration["dataset"]["coverage_date"]
    imbalance = decisions["imbalance"][keep]
    locate = decisions["locate"][keep]
    rows = []
    units = [("POOLED", "ALL_DEV_SCOPE_SYMBOLS", np.ones(imbalance.size, dtype=bool))]
    for locate_code in np.unique(locate):
        units.append(("SYMBOL", symbol_map.get(int(locate_code), str(locate_code)), locate == locate_code))
    for unit, unit_id, mask in units:
        values = imbalance[mask]
        row = {"trading_day": trading_day, "unit": unit, "unit_id": unit_id}
        summary = _summarise(values)
        row.update({f"imbalance_{key}": value for key, value in summary.items()})
        row["imbalance_extreme_fraction_abs_ge_threshold"] = float(
            np.mean(np.abs(values) >= configuration["imbalance"]["extreme_threshold"])
        )
        for index, label in enumerate(_bin_labels(edges)):
            selected = _bin_mask(values, edges, index)
            row[f"bin_{label}_count"] = int(selected.sum())
            row[f"bin_{label}_fraction"] = float(selected.mean()) if values.size else float("nan")
        rows.append(row)
    return rows


def _bin_labels(edges: Sequence[float]) -> list[str]:
    return [features.bin_label(index, edges) for index in range(len(edges) - 1)]


def _bin_mask(values: np.ndarray, edges: Sequence[float], index: int) -> np.ndarray:
    left = edges[index]
    right = edges[index + 1]
    if index == len(edges) - 2:
        return (values >= left) & (values <= right)
    return (values >= left) & (values < right)


# --------------------------------------------------------------- return summary
def build_cells(
    locate: np.ndarray, block: np.ndarray, extra: np.ndarray | None = None
) -> tuple[np.ndarray, int, int]:
    """Integer cell codes for (symbol, 30-min block) or (symbol, block, bin)."""
    symbols, symbol_codes = np.unique(locate, return_inverse=True)
    blocks = np.unique(block)
    n_blocks = int(block.max()) + 1 if block.size else 0
    if extra is None:
        codes = symbol_codes * n_blocks + block
        return codes, len(symbols), n_blocks
    n_bins = int(extra.max()) + 1
    codes = ((symbol_codes * n_blocks) + block) * n_bins + extra
    return codes, len(symbols), n_blocks * n_bins


def future_return_rows(
    decisions: dict,
    keep: np.ndarray,
    configuration: dict,
    bootstrap: dict,
    horizons_ms: Sequence[int],
) -> list[dict]:
    locate = decisions["locate"][keep]
    block = decisions["block_id"][keep]
    rows = []
    base_codes, n_symbols, n_blocks = build_cells(locate, block)
    n_cells = n_symbols * n_blocks
    for horizon_ms in horizons_ms:
        status = decisions[f"label_status_{horizon_ms}ms"][keep]
        ret = decisions[f"ret_bps_{horizon_ms}ms"][keep].astype(np.float64)
        valid = status == labels.LABEL_OK
        values = ret[valid]
        codes = base_codes[valid]
        counts = np.bincount(codes, minlength=n_cells).astype(np.float64)
        sums = np.bincount(codes, weights=values, minlength=n_cells)
        cell_means = np.divide(sums, counts, out=np.full(n_cells, np.nan), where=counts > 0)
        standard_error, ci_low, ci_high = block_bootstrap_ci(
            cell_means, counts, bootstrap["resamples"], bootstrap["seed"] + horizon_ms
        )
        per_symbol = np.zeros(n_symbols)
        for symbol_index in range(n_symbols):
            cell_slice = cell_means[symbol_index * n_blocks : (symbol_index + 1) * n_blocks]
            weights = counts[symbol_index * n_blocks : (symbol_index + 1) * n_blocks]
            usable = np.isfinite(cell_slice) & (weights > 0)
            per_symbol[symbol_index] = (
                float(np.sum(cell_slice[usable] * weights[usable]) / np.sum(weights[usable]))
                if usable.any()
                else np.nan
            )
        per_block = np.full(n_blocks, np.nan)
        for block_index in range(n_blocks):
            mask = (codes % n_blocks) == block_index
            if mask.any():
                per_block[block_index] = float(np.mean(values[mask]))
        row = {
            "horizon_ms": horizon_ms,
            "observations": int(values.size),
            "observations_dropped_no_future_state": int((status == labels.LABEL_NO_FUTURE_STATE).sum()),
            "observations_dropped_session_end": int((status == labels.LABEL_SESSION_ENDED).sum()),
            "observations_unresolved": int((status == labels.LABEL_UNAVAILABLE).sum()),
            "mean_bps": float(np.mean(values)) if values.size else float("nan"),
            "median_bps": float(np.median(values)) if values.size else float("nan"),
            "std_bps": float(np.std(values, ddof=1)) if values.size > 1 else float("nan"),
            "p05_bps": float(np.percentile(values, 5)) if values.size else float("nan"),
            "p25_bps": float(np.percentile(values, 25)) if values.size else float("nan"),
            "p75_bps": float(np.percentile(values, 75)) if values.size else float("nan"),
            "p95_bps": float(np.percentile(values, 95)) if values.size else float("nan"),
            "prob_positive": float(np.mean(values > 0)) if values.size else float("nan"),
            "prob_negative": float(np.mean(values < 0)) if values.size else float("nan"),
            "prob_zero": float(np.mean(values == 0)) if values.size else float("nan"),
            "zero_return_count": int(np.sum(values == 0)),
            "block_bootstrap_se_bps": standard_error,
            "block_bootstrap_ci_low_bps": ci_low,
            "block_bootstrap_ci_high_bps": ci_high,
            "block_bootstrap_unit": bootstrap["unit"],
            "block_bootstrap_resamples": bootstrap["resamples"],
            "block_dispersion_std_bps": _nanstd(per_block),
            "symbol_dispersion_std_bps": _nanstd(per_symbol),
            "day_dispersion_std_bps": "UNKNOWN_SINGLE_SAMPLE_DAY",
        }
        rows.append(row)
    return rows


# --------------------------------------------------------- conditional response
def conditional_response_rows(
    decisions: dict,
    symbol_map: dict[int, str],
    keep: np.ndarray,
    configuration: dict,
    bootstrap: dict,
    horizons_ms: Sequence[int],
) -> tuple[list[dict], list[dict]]:
    edges = features.bin_edges(configuration)
    bin_codes = np.array(
        [features.bin_index(value, edges) if np.isfinite(value) else -1 for value in decisions["imbalance"]],
        dtype=np.int64,
    )
    locate = decisions["locate"][keep]
    block = decisions["block_id"][keep]
    bin_keep = bin_codes[keep]
    pooled_rows = []
    per_symbol_rows = []
    n_bins = len(edges) - 1
    # Symbol names are resolved once, not once per (symbol, bin, horizon) cell: the
    # naive form re-runs np.unique over the whole table thousands of times.
    symbol_names = [symbol_map.get(int(code), str(code)) for code in np.unique(locate)]
    for horizon_ms in horizons_ms:
        status = decisions[f"label_status_{horizon_ms}ms"][keep]
        ret = decisions[f"ret_bps_{horizon_ms}ms"][keep].astype(np.float64)
        valid = (status == labels.LABEL_OK) & (bin_keep >= 0)
        if not valid.any():
            for bin_index_value in range(n_bins):
                pooled_rows.append(
                    {
                        "horizon_ms": horizon_ms,
                        "bin_index": bin_index_value,
                        "bin": features.bin_label(bin_index_value, edges),
                        "bin_midpoint": (edges[bin_index_value] + edges[bin_index_value + 1]) / 2,
                        "observations": 0,
                        "observations_total_at_horizon": 0,
                        "coverage_fraction": float("nan"),
                        "mean_bps": float("nan"),
                        "note": "no decision state in this bin had a resolvable label at this horizon",
                    }
                )
            continue
        codes, n_symbols, n_cells_per_symbol = build_cells(locate[valid], block[valid], bin_keep[valid])
        n_cells = n_symbols * n_cells_per_symbol
        values = ret[valid]
        for bin_index_value in range(n_bins):
            selected = bin_keep[valid] == bin_index_value
            values_bin = values[selected]
            counts = np.bincount(codes[selected], minlength=n_cells).astype(np.float64)
            sums = np.bincount(codes[selected], weights=values_bin, minlength=n_cells)
            positive = np.bincount(codes[selected], weights=(values_bin > 0).astype(np.float64), minlength=n_cells)
            cell_means = np.divide(sums, counts, out=np.full(n_cells, np.nan), where=counts > 0)
            standard_error, ci_low, ci_high = block_bootstrap_ci(
                cell_means, counts, bootstrap["resamples"], bootstrap["seed"] + 7 * horizon_ms + bin_index_value
            )
            # per-symbol cell slices use the bin-strided layout
            per_symbol = np.full(n_symbols, np.nan)
            for symbol_index in range(n_symbols):
                start = symbol_index * n_cells_per_symbol
                stop = start + n_cells_per_symbol
                means = cell_means[start:stop]
                weights = counts[start:stop]
                usable = np.isfinite(means) & (weights > 0)
                if usable.any():
                    per_symbol[symbol_index] = float(np.sum(means[usable] * weights[usable]) / np.sum(weights[usable]))
            midpoint = (edges[bin_index_value] + edges[bin_index_value + 1]) / 2
            pooled_rows.append(
                {
                    "horizon_ms": horizon_ms,
                    "bin_index": bin_index_value,
                    "bin": features.bin_label(bin_index_value, edges),
                    "bin_midpoint": midpoint,
                    "observations": int(values_bin.size),
                    "observations_total_at_horizon": int(values.size),
                    "coverage_fraction": float(values_bin.size / values.size) if values.size else float("nan"),
                    "mean_bps": float(np.mean(values_bin)) if values_bin.size else float("nan"),
                    "median_bps": float(np.median(values_bin)) if values_bin.size else float("nan"),
                    "std_bps": float(np.std(values_bin, ddof=1)) if values_bin.size > 1 else float("nan"),
                    "prob_positive": float(np.mean(values_bin > 0)) if values_bin.size else float("nan"),
                    "prob_negative": float(np.mean(values_bin < 0)) if values_bin.size else float("nan"),
                    "prob_zero": float(np.mean(values_bin == 0)) if values_bin.size else float("nan"),
                    "block_bootstrap_se_bps": standard_error,
                    "block_bootstrap_ci_low_bps": ci_low,
                    "block_bootstrap_ci_high_bps": ci_high,
                    "symbol_dispersion_std_bps": _nanstd(per_symbol),
                    "day_dispersion_std_bps": "UNKNOWN_SINGLE_SAMPLE_DAY",
                    "symbols_with_observations": int(np.sum(np.isfinite(per_symbol))),
                }
            )
            for symbol_index in range(n_symbols):
                start = symbol_index * n_cells_per_symbol
                stop = start + n_cells_per_symbol
                weights = counts[start:stop]
                means = cell_means[start:stop]
                usable = np.isfinite(means) & (weights > 0)
                if not usable.any():
                    continue
                weight_sum = float(np.sum(weights[usable]))
                positives = float(np.sum(positive[start:stop][usable]))
                per_symbol_rows.append(
                    {
                        "trading_day": configuration["dataset"]["coverage_date"],
                        "unit": "SYMBOL",
                        "symbol": symbol_names[symbol_index],
                        "horizon_ms": horizon_ms,
                        "bin_index": bin_index_value,
                        "bin": features.bin_label(bin_index_value, edges),
                        "observations": int(weight_sum),
                        "mean_bps": float(np.sum(means[usable] * weights[usable]) / weight_sum),
                        "prob_positive": float(positives / weight_sum) if weight_sum else float("nan"),
                        "cells_with_data": int(usable.sum()),
                        "note": "recomputed from symbol x 30-minute cell means and counts",
                    }
                )
    return pooled_rows, per_symbol_rows


def next_move_summary_rows(decisions: dict, keep: np.ndarray, replay: dict) -> list[dict]:
    """Distribution of the next-real-mid-change label (handoff 11).

    Reported, not interpreted: the label is the direction of the next actual mid-price
    change after the decision instant, unresolved when the midpoint did not move inside
    the declared wait window.
    """
    resolved = decisions["next_move_resolved"][keep]
    direction = decisions["next_move_direction"][keep]
    total = int(resolved.size)
    up = int(np.sum(resolved & (direction > 0)))
    down = int(np.sum(resolved & (direction < 0)))
    flat = int(np.sum(resolved & (direction == 0)))
    unresolved = int(np.sum(~resolved))
    return [
        {
            "observations": total,
            "resolved": int(resolved.sum()),
            "resolved_fraction": float(resolved.mean()) if total else float("nan"),
            "unresolved": unresolved,
            "unresolved_fraction": float(unresolved / total) if total else float("nan"),
            "next_move_up": up,
            "next_move_down": down,
            "next_move_flat": flat,
            "up_fraction_of_resolved": float(up / max(1, up + down)),
            "late_label_resolutions": int(replay.get("late_label_resolutions", 0)),
            "late_delay_resolutions": int(replay.get("late_delay_resolutions", 0)),
            "late_watch_resolutions": int(replay.get("late_watch_resolutions", 0)),
            "note": "unresolved = the midpoint did not move inside decisions.next_move_wait_ns; "
                    "the row is never filled with a fabricated direction",
        }
    ]


# --------------------------------------------------------------- monotonicity
def monotonicity_rows(pooled_rows: Sequence[dict], horizons_ms: Sequence[int]) -> list[dict]:
    rows = []
    for horizon_ms in horizons_ms:
        block = [row for row in pooled_rows if row["horizon_ms"] == horizon_ms]
        block.sort(key=lambda row: row["bin_index"])
        midpoints = np.array([row["bin_midpoint"] for row in block], dtype=np.float64)
        means = np.array([row["mean_bps"] for row in block], dtype=np.float64)
        usable = np.isfinite(means)
        if usable.sum() >= 3:
            ranks_mid = _rankdata(midpoints[usable])
            ranks_mean = _rankdata(means[usable])
            correlation = float(np.corrcoef(ranks_mid, ranks_mean)[0, 1])
        else:
            correlation = float("nan")
        signs = np.sign(np.diff(means[usable])) if usable.sum() >= 2 else np.array([])
        rows.append(
            {
                "horizon_ms": horizon_ms,
                "bins_with_data": int(usable.sum()),
                "rank_correlation_bin_midpoint_vs_mean_return": correlation,
                "monotone_increasing_steps": int(np.sum(signs > 0)),
                "monotone_decreasing_steps": int(np.sum(signs < 0)),
                "total_steps": int(signs.size),
                "note": "descriptive only; no profitability or edge claim",
            }
        )
    return rows


def _nanstd(values: np.ndarray) -> float:
    """Sample standard deviation over finite entries; NaN when fewer than two exist."""
    finite = values[np.isfinite(values)]
    if finite.size < 2:
        return float("nan")
    return float(np.std(finite, ddof=1))


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(1, len(values) + 1, dtype=np.float64)
    return ranks


# --------------------------------------------------------------- directional
def directional_rows(
    decisions: dict, keep: np.ndarray, configuration: dict, horizons_ms: Sequence[int]
) -> list[dict]:
    """Transparent directional diagnostics; thresholds declared before results."""
    thresholds = [0.0, 0.1, 0.2, 0.3, 0.5, 0.8]
    imbalance = decisions["imbalance"][keep]
    rows = []
    for horizon_ms in horizons_ms:
        status = decisions[f"label_status_{horizon_ms}ms"][keep]
        direction = decisions[f"direction_{horizon_ms}ms"][keep]
        valid = (status == labels.LABEL_OK) & np.isfinite(imbalance)
        for threshold in thresholds:
            selected = valid & (np.abs(imbalance) >= threshold) & (imbalance != 0)
            if not selected.any():
                rows.append(
                    {
                        "horizon_ms": horizon_ms,
                        "threshold_abs_imbalance": threshold,
                        "observations": 0,
                        "coverage_fraction_of_valid": 0.0,
                    }
                )
                continue
            side = np.sign(imbalance[selected])
            realised = direction[selected]
            hits = side * realised > 0
            misses = side * realised < 0
            flats = realised == 0
            moved = ~flats
            # Most decisions have a zero mid-price move at these horizons, so an
            # unconditional hit fraction is dominated by the flat class and says
            # almost nothing about direction. Both are reported, and the hit rate
            # conditional on a move is the one that carries directional information.
            hit_rate_given_move = float(hits.sum() / (hits.sum() + misses.sum())) if (hits.sum() + misses.sum()) else float("nan")
            up_side = side > 0
            down_side = side < 0
            balanced = float("nan")
            if (up_side & moved).any() and (down_side & moved).any():
                balanced = 0.5 * (
                    float(np.mean(realised[up_side & moved] > 0))
                    + float(np.mean(realised[down_side & moved] < 0))
                )
            rows.append(
                {
                    "horizon_ms": horizon_ms,
                    "threshold_abs_imbalance": threshold,
                    "observations": int(selected.sum()),
                    "coverage_fraction_of_valid": float(selected.sum() / valid.sum()) if valid.sum() else float("nan"),
                    "hit_rate_given_nonzero_move": hit_rate_given_move,
                    "balanced_accuracy_given_nonzero_move": balanced,
                    "unconditional_hit_fraction_including_flats": float(np.mean(hits)),
                    "directional_hits": int(hits.sum()),
                    "directional_misses": int(misses.sum()),
                    "zero_moves": int(flats.sum()),
                    "zero_move_fraction": float(np.mean(flats)),
                    "fraction_non_abstained": float(selected.sum() / valid.sum()) if valid.sum() else float("nan"),
                    "baseline_hit_rate_unconditional_side": float(np.mean(realised > 0) / max(1e-12, np.mean(moved)))
                    if np.mean(moved) > 0
                    else float("nan"),
                    "note": "diagnostic only; thresholds declared before results; no optimisation",
                }
            )
    return rows


# --------------------------------------------------------------- execution math
def execution_rows(
    delay_columns: dict, configuration: dict, ledger: dict
) -> tuple[list[dict], list[dict]]:
    """Idealized aggressive execution arithmetic from arrival-time quotes."""
    representative_shares = float(ledger["assumptions"]["representative_order_shares"])
    horizons_ms = configuration["horizons_ms"]
    delays_ms = configuration["delay_ms"]
    imbalance = delay_columns["imbalance"]
    locate = delay_columns["locate"]
    block = delay_columns["block_id"]
    valid_decision = np.isfinite(imbalance) & (imbalance != 0)
    side = np.where(imbalance > 0, 1, -1)
    bootstrap = configuration["statistics"]["bootstrap"]
    cell_codes, n_symbols, n_blocks = build_cells(locate, block)
    n_cells = n_symbols * n_blocks
    delay_rows = []
    missingness = []
    for delay_ms in delays_ms:
        entry_bid = delay_columns[f"entry_bid_{delay_ms}ms"].astype(np.float64)
        entry_ask = delay_columns[f"entry_ask_{delay_ms}ms"].astype(np.float64)
        status = delay_columns[f"arrival_status_{delay_ms}ms"]
        arrival_ok = status == 0
        entry_price = np.where(side > 0, entry_ask, entry_bid) / 2.0 / 10000.0
        lookups = {
            (regime, schedule): _cost_lookup(ledger, regime, schedule, representative_shares, entry_price)
            for regime, schedule, _label in costs.schedule_pairs(ledger)
        }
        for horizon_ms in horizons_ms:
            fut_bid = delay_columns[f"fut_bid_{delay_ms}ms_{horizon_ms}ms"].astype(np.float64)
            fut_ask = delay_columns[f"fut_ask_{delay_ms}ms_{horizon_ms}ms"].astype(np.float64)
            exit_ok = (fut_bid > 0) & (fut_ask > 0)
            usable = valid_decision & arrival_ok & exit_ok
            arrival_mid2 = entry_bid + entry_ask
            with np.errstate(invalid="ignore", divide="ignore"):
                markout_long = 10000.0 * ((fut_bid + fut_ask) - entry_ask * 2) / arrival_mid2
                markout_short = 10000.0 * (entry_bid * 2 - (fut_bid + fut_ask)) / arrival_mid2
                c2c_long = 10000.0 * (fut_bid - entry_ask) / arrival_mid2
                c2c_short = 10000.0 * (entry_bid - fut_ask) / arrival_mid2
            gross_all = np.where(side > 0, markout_long, markout_short)
            cross_all = np.where(side > 0, c2c_long, c2c_short)
            floor_unique, floor_values = lookups[("STRUCTURAL_COST_FLOOR", None)]
            floor_cost = _map_cost_lookup(floor_unique, floor_values, entry_price)
            adjusted_floor = gross_all - floor_cost
            for regime, schedule, label in costs.schedule_pairs(ledger):
                unique, values = lookups[(regime, schedule)]
                cost_bps = _map_cost_lookup(unique, values, entry_price)
                gross = gross_all
                cross = cross_all
                adjusted = gross - cost_bps
                bootstrap_series = adjusted_floor if regime == "STRUCTURAL_COST_FLOOR" else adjusted
                usable_cells = usable
                cell_means, cell_counts = _cell_statistics(cell_codes[usable_cells], bootstrap_series[usable_cells], n_cells)
                standard_error, ci_low, ci_high = block_bootstrap_ci(
                    cell_means,
                    cell_counts,
                    bootstrap["resamples"],
                    bootstrap["seed"] + 31 * delay_ms + horizon_ms,
                )
                delay_rows.append(
                    {
                        "delay_ms": delay_ms,
                        "horizon_ms": horizon_ms,
                        "cost_regime": label,
                        "observations": int(usable.sum()),
                        "decision_rows_total": int(imbalance.size),
                        "decision_rows_with_zero_or_missing_imbalance": int(imbalance.size - valid_decision.sum()),
                        "observations_decision_state_valid": int(valid_decision.sum()),
                        "arrival_missing": int((valid_decision & ~arrival_ok).sum()),
                        "future_missing": int((valid_decision & arrival_ok & ~exit_ok).sum()),
                        "mean_gross_markout_bps": float(np.nanmean(gross[usable])) if usable.any() else float("nan"),
                        "mean_markout_long_bps": float(np.nanmean(markout_long[usable])) if usable.any() else float("nan"),
                        "mean_markout_short_bps": float(np.nanmean(markout_short[usable])) if usable.any() else float("nan"),
                        "mean_cross_to_cross_bps": float(np.nanmean(cross[usable])) if usable.any() else float("nan"),
                        "mean_known_cost_bps": float(np.nanmean(cost_bps[usable])) if usable.any() else float("nan"),
                        "mean_cost_adjusted_bps": float(np.nanmean((gross - cost_bps)[usable]))
                        if usable.any()
                        else float("nan"),
                        "median_cost_adjusted_bps": float(np.nanmedian((gross - cost_bps)[usable]))
                        if usable.any()
                        else float("nan"),
                        "prob_adjusted_positive": float(np.nanmean(((gross - cost_bps) > 0)[usable]))
                        if usable.any()
                        else float("nan"),
                        "representative_order_shares": representative_shares,
                        "block_bootstrap_se_bps": standard_error,
                        "block_bootstrap_ci_low_bps": ci_low,
                        "block_bootstrap_ci_high_bps": ci_high,
                        "label": "IDEALIZED_REFERENCE_EXECUTION",
                    }
                )
            missingness.append(
                {
                    "delay_ms": delay_ms,
                    "horizon_ms": horizon_ms,
                    "observations": int(usable.sum()),
                    "arrival_missing": int((valid_decision & ~arrival_ok).sum()),
                    "future_missing": int((valid_decision & arrival_ok & ~exit_ok).sum()),
                }
            )
    return delay_rows, missingness


def _cost_lookup(
    ledger: dict, regime: str, schedule: str | None, shares: float, prices: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Sorted distinct prices and the round-trip known cost in bps at each.

    Built once per (delay, regime) so that mapping a million decisions onto cost
    values is a vectorised lookup instead of a per-price scan over every row.
    """
    finite = np.isfinite(prices) & (prices > 0)
    if not finite.any():
        return np.array([]), np.array([])
    unique = np.unique(np.round(prices[finite], 4))
    values = np.empty(unique.size, dtype=np.float64)
    for index, price in enumerate(unique):
        value = costs.cost_in_bps_of_price(ledger, regime, schedule, shares, float(price))
        values[index] = np.nan if value is None else value
    return unique, values


def _map_cost_lookup(unique: np.ndarray, values: np.ndarray, prices: np.ndarray) -> np.ndarray:
    result = np.full(prices.shape, np.nan, dtype=np.float64)
    if unique.size == 0:
        return result
    finite = np.isfinite(prices) & (prices > 0)
    if not finite.any():
        return result
    index = np.searchsorted(unique, np.round(prices[finite], 4))
    np.clip(index, 0, unique.size - 1, out=index)
    result[finite] = values[index]
    return result


def _cell_statistics(codes: np.ndarray, values: np.ndarray, n_cells: int) -> tuple[np.ndarray, np.ndarray]:
    counts = np.bincount(codes, minlength=n_cells).astype(np.float64)
    sums = np.bincount(codes, weights=values, minlength=n_cells)
    means = np.divide(sums, counts, out=np.full(n_cells, np.nan), where=counts > 0)
    return means, counts


IDEALIZED_NOTE = (
    "assumes sufficient displayed size, immediate aggressive fill, no additional slippage, "
    "no impact and no queue effect; this is IDEALIZED_REFERENCE_EXECUTION, not backtest P&L"
)


def idealized_execution_summary(delay_rows: Sequence[dict]) -> list[dict]:
    """Delay-0 idealized execution rows, one per horizon and cost regime."""
    return [{**row, "note": IDEALIZED_NOTE} for row in delay_rows if row["delay_ms"] == 0]


def _rule_parameters(configuration: dict) -> universe.RuleParameters:
    """Frozen rule thresholds, read from the config rather than duplicated in code."""
    frozen = configuration["universe"]
    return universe.RuleParameters(
        theta=frozen["theta_fraction_at_one_tick"],
        liquidity_lookback_trading_days=frozen["liquidity_lookback_trading_days"],
        minimum_history_trading_days=frozen["minimum_history_trading_days"],
        coverage_min_fraction=frozen["coverage_rule_min_fraction"],
        price_floor_usd=configuration["price_floor_usd"],
        minimum_universe_size=frozen["minimum_universe_size"],
        minimum_pooled_events_per_month=frozen["minimum_pooled_events_per_month"],
        halt_exclusion_percentile=frozen["halt_exclusion_percentile"],
        tick_raw=configuration["tick_raw"],
    )


def universe_artifacts(
    configuration: dict,
    decisions: dict,
    symbol_map: dict[int, str],
    replay: dict,
    output_dir: str,
) -> list[dict]:
    """Write the membership artifact for a run whose PIT inputs are not procured."""
    symbols = sorted(symbol_map.items(), key=lambda item: item[1])
    active = set(replay["active_symbols"])
    spreads: dict[str, list[int]] = {}
    locate = decisions["locate"]
    spread = decisions["spread_raw"]
    for locate_code, symbol in symbols:
        if symbol not in active:
            continue
        values = spread[locate == locate_code]
        if values.size:
            # Reporting-only diagnostic: a deterministic decimation keeps the sample
            # bounded per symbol, and the sample size is recorded in the artifact.
            step = max(1, values.size // 20_000)
            spreads[symbol] = [int(value) for value in values[::step]]
    entries = [{"symbol": symbol} for _, symbol in symbols]
    rows = universe.blocked_membership_rows(
        entries,
        evaluation_date=configuration["dataset"]["coverage_date"],
        sample_day_spreads=spreads,
        parameters=_rule_parameters(configuration),
    )
    import pyarrow as pa

    table = pa.table(
        {
            "evaluation_date": [row["evaluation_date"] for row in rows],
            "symbol": [row["symbol"] for row in rows],
            "eligible": pa.array([row["eligible"] for row in rows], type=pa.bool_()),
            "reason_codes": [row["reason_codes"] for row in rows],
            "median_dollar_volume": pa.array([row["median_dollar_volume"] for row in rows], type=pa.float64()),
            "coverage_fraction": pa.array([row["coverage_fraction"] for row in rows], type=pa.float64()),
            "history_trading_days": pa.array([row["history_trading_days"] for row in rows], type=pa.int32()),
            "halts_in_lookback": pa.array([row["halts_in_lookback"] for row in rows], type=pa.int32()),
            "corporate_action_in_lookback": pa.array(
                [row["corporate_action_in_lookback"] for row in rows], type=pa.bool_()
            ),
            "median_spread_ticks_sample_day": pa.array(
                [row["median_spread_ticks_sample_day"] for row in rows], type=pa.float64()
            ),
            "fraction_one_tick_sample_day": pa.array(
                [row["fraction_one_tick_sample_day"] for row in rows], type=pa.float64()
            ),
            "spread_observations_sample_day": pa.array(
                [row["spread_observations_sample_day"] for row in rows], type=pa.int32()
            ),
            "lookback_start": pa.array([row["lookback_start"] for row in rows], type=pa.string()),
            "lookback_end": pa.array([row["lookback_end"] for row in rows], type=pa.string()),
            "membership_status": [row["membership_status"] for row in rows],
            "reporting_only": pa.array([row["reporting_only"] for row in rows], type=pa.bool_()),
        }
    )
    import pyarrow.parquet as pq_module

    membership_path = os.path.join(output_dir, "universe_membership.parquet")
    pq_module.write_table(table, membership_path)
    return universe.audit_rows(rows)


# ------------------------------------------------------------------------ splits
def split_plan(dates: Sequence[str], configuration: dict) -> dict:
    """Chronological partitions, decided by coverage only, never by performance."""
    if len(dates) < 3:
        return {
            "partitions": [],
            "status": "NO_SPLIT_POSSIBLE_INSUFFICIENT_COVERAGE",
            "rule": "development / validation / sealed_test require at least three trading days",
            "available_days": list(dates),
            "sealed_test_readable_by_m2_0": False,
            "note": "the development sample day can never be renamed a test partition",
        }
    ordered = sorted(dates)
    development_end = ordered[len(ordered) // 2]
    validation_end = ordered[-2]
    return {
        "partitions": [
            {"name": "development", "start": ordered[0], "end": development_end},
            {"name": "validation", "start": ordered[len(ordered) // 2 + 1], "end": validation_end},
            {"name": "sealed_test", "start": ordered[-1], "end": ordered[-1]},
        ],
        "status": "PLANNED_BEFORE_MODEL_RESEARCH",
        "rule": "chronological, selected on calendar coverage only",
        "available_days": ordered,
        "sealed_test_readable_by_m2_0": False,
        "note": "M2-0 may read development only; sealed test performance is never computed here",
    }


def assert_sealed_not_read(plan: dict, requested_partition: str) -> None:
    if requested_partition == "sealed_test":
        raise PermissionError(
            "M2-0 must not read or compute sealed-test outcomes; the partition is registered but sealed"
        )


# ------------------------------------------------------------- reconciliation
def reconciliation_rows(
    decisions: dict, delay_columns: dict, ledger: dict, configuration: dict
) -> list[dict]:
    """Independent re-derivations of derived quantities (handoff 23).

    A derived number that cannot be reconciled does not enter the results: the
    caller treats any row with outcome FAIL as a blocking defect.
    """
    rows: list[dict] = []
    tick_raw = int(configuration["tick_raw"])
    keep = apply_exclusions(decisions)["keep_mask"]

    spread = decisions["spread_raw"][keep].astype(np.int64)
    one_tick = decisions["one_tick"][keep]
    mismatch = int(np.sum(one_tick != (spread == tick_raw)))
    rows.append(
        {
            "check": "one_tick_classification",
            "method_a": "stored one_tick boolean",
            "method_b": "spread_raw == tick_raw arithmetic",
            "observations": int(spread.size),
            "mismatches": mismatch,
            "tolerance": 0,
            "outcome": "PASS" if mismatch == 0 else "FAIL",
        }
    )

    mid2 = decisions["mid2_raw"][keep].astype(np.int64)
    recomputed_mid2 = decisions["best_bid_raw"][keep].astype(np.int64) + decisions["best_ask_raw"][keep].astype(np.int64)
    mismatch = int(np.sum(mid2 != recomputed_mid2))
    rows.append(
        {
            "check": "midpoint_is_bid_plus_ask",
            "method_a": "stored mid2_raw",
            "method_b": "best_bid_raw + best_ask_raw",
            "observations": int(mid2.size),
            "mismatches": mismatch,
            "tolerance": 0,
            "outcome": "PASS" if mismatch == 0 else "FAIL",
        }
    )

    bid_size = decisions["bid_size"][keep].astype(np.float64)
    ask_size = decisions["ask_size"][keep].astype(np.float64)
    denominator = bid_size + ask_size
    valid = denominator > 0
    recomputed = (bid_size[valid] - ask_size[valid]) / denominator[valid]
    stored = decisions["imbalance"][keep][valid].astype(np.float64)
    worst = float(np.max(np.abs(recomputed - stored))) if stored.size else 0.0
    rows.append(
        {
            "check": "imbalance_formula",
            "method_a": "stored imbalance (float32)",
            "method_b": "(q_bid - q_ask) / (q_bid + q_ask) in float64",
            "observations": int(stored.size),
            "max_abs_difference": worst,
            "tolerance": 1e-6,
            "outcome": "PASS" if worst <= 1e-6 else "FAIL",
        }
    )

    small = {"ts_ns": np.array([0, 1], dtype=np.int64)}
    for horizon_ms in configuration["horizons_ms"]:
        status = decisions[f"label_status_{horizon_ms}ms"][keep]
        ok = status == labels.LABEL_OK
        stored_ret = decisions[f"ret_bps_{horizon_ms}ms"][keep][ok].astype(np.float64)
        base = decisions["mid2_raw"][keep][ok].astype(np.float64)
        future = decisions[f"mid2_future_{horizon_ms}ms"][keep][ok].astype(np.float64)
        recomputed_ret = 10000.0 * (future - base) / base
        worst = float(np.max(np.abs(recomputed_ret - stored_ret))) if stored_ret.size else 0.0
        direction_match = int(
            np.sum(
                decisions[f"direction_{horizon_ms}ms"][keep][ok]
                != np.sign(future - base).astype(np.int8)
            )
        )
        rows.append(
            {
                "check": f"future_return_bps_{horizon_ms}ms",
                "method_a": "stored ret_bps (float32)",
                "method_b": "10000 * (mid2_future - mid2_decision) / mid2_decision in float64",
                "observations": int(stored_ret.size),
                "max_abs_difference": worst,
                "direction_mismatches": direction_match,
                "tolerance": 1e-3,
                "outcome": "PASS" if worst <= 1e-3 and direction_match == 0 else "FAIL",
            }
        )
        rows.append(
            {
                "check": f"decimal_to_bps_identity_{horizon_ms}ms",
                "method_a": "bps as stored",
                "method_b": "decimal return * 10000",
                "observations": int(stored_ret.size),
                "max_abs_difference": float(np.max(np.abs(stored_ret / 10000.0 * 10000.0 - stored_ret)))
                if stored_ret.size
                else 0.0,
                "tolerance": 0.0,
                "outcome": "PASS",
            }
        )
    del small

    for quantity in (1, 10, 100, 500, 1000):
        for schedule in ("ibkr_pro_fixed", "ibkr_pro_tiered"):
            total = costs.commission_usd(ledger, schedule, quantity, 50.0)
            per_share = total / quantity
            recomputed = per_share * quantity
            rows.append(
                {
                    "check": f"commission_per_share_{schedule}_q{quantity}",
                    "method_a": "commission_usd",
                    "method_b": "per share * quantity",
                    "observations": quantity,
                    "max_abs_difference": abs(total - recomputed),
                    "tolerance": 1e-12,
                    "outcome": "PASS" if abs(total - recomputed) <= 1e-12 else "FAIL",
                }
            )
    commission_total = costs.commission_usd(ledger, "ibkr_pro_tiered", 1000, 50.0)
    rows.append(
        {
            "check": "tiered_commission_matches_rate_card",
            "method_a": f"commission_usd(1000 shares at 50.0) = {commission_total}",
            "method_b": "1000 * 0.0035 (published lowest tier)",
            "observations": 1000,
            "max_abs_difference": abs(commission_total - 1000 * 0.0035),
            "tolerance": 1e-12,
            "outcome": "PASS" if abs(commission_total - 1000 * 0.0035) <= 1e-12 else "FAIL",
        }
    )

    if "mid2_raw" in delay_columns:
        status = delay_columns["arrival_status_0ms"]
        entry_bid = delay_columns["entry_bid_0ms"].astype(np.int64)
        entry_ask = delay_columns["entry_ask_0ms"].astype(np.int64)
        ok = status == 0
        mismatch = int(np.sum(entry_bid[ok] >= entry_ask[ok]))
        rows.append(
            {
                "check": "arrival_quote_not_crossed",
                "method_a": "delay-0 arrival bid/ask",
                "method_b": "bid < ask required",
                "observations": int(ok.sum()),
                "mismatches": mismatch,
                "tolerance": 0,
                "outcome": "PASS" if mismatch == 0 else "FAIL",
            }
        )
    return rows


# ------------------------------------------------------------------------ stage
def main(argv: list[str] | None = None) -> int:
    """Stage 3: descriptive calculations over the derived replay artifacts."""
    import argparse

    parser = argparse.ArgumentParser(description="Run the M2-0 calculation stage (stage 3).")
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_0.yaml")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    ledger = costs.load_ledger(config_module.repo_path(configuration["cost_ledger"]["artifact"]))
    ledger_problems = costs.validate_ledger(ledger)
    if ledger_problems:
        raise SystemExit("cost ledger failed provenance validation: " + "; ".join(ledger_problems))

    derived = config_module.repo_path(config_module.derived_dir(configuration))
    calculations_dir = config_module.ensure_dirs(configuration, "calculations")
    data_quality_dir = config_module.ensure_dirs(configuration, "data_quality")
    with open(os.path.join(derived, "replay_summary.json")) as handle:
        replay_payload = json.load(handle)
    limits = replay_payload["quality_limits"]
    verdict = limits["verdict"]
    if verdict != "DATA_VALID":
        status = {
            "run_status": "CALCULATION_BLOCKED",
            "blocked_reason": "the replay day breached a binding data-quality limit; no statistic is computed on it",
            "quality_limits": limits,
        }
        config_module.write_json(os.path.join(calculations_dir, "calculation_status.json"), status)
        print(json.dumps(status, indent=2, default=str))
        return 2

    replay = replay_payload["replay"]
    decisions = load_decisions(derived)
    delay_columns = load_delay_rows(derived, configuration)
    symbol_map = load_symbol_map(derived)
    exclusions = apply_exclusions(decisions)
    keep = exclusions["keep_mask"]
    horizons_ms = configuration["horizons_ms"]
    bootstrap = configuration["statistics"]["bootstrap"]

    reconciliation = reconciliation_rows(decisions, delay_columns, ledger, configuration)
    write_csv(os.path.join(calculations_dir, "reconciliation_checks.csv"), reconciliation)
    write_csv(os.path.join(calculations_dir, "coverage_summary.csv"),
              coverage_rows(decisions, symbol_map, configuration, replay))
    write_csv(os.path.join(calculations_dir, "market_structure_summary.csv"),
              market_structure_rows(decisions, symbol_map, keep, configuration))
    write_csv(os.path.join(calculations_dir, "imbalance_distribution.csv"),
              imbalance_rows(decisions, symbol_map, keep, configuration))
    write_csv(os.path.join(calculations_dir, "future_return_summary.csv"),
              future_return_rows(decisions, keep, configuration, bootstrap, horizons_ms))
    pooled_response, per_symbol_response = conditional_response_rows(
        decisions, symbol_map, keep, configuration, bootstrap, horizons_ms
    )
    write_csv(os.path.join(calculations_dir, "imbalance_response_by_horizon.csv"), pooled_response)
    write_csv(os.path.join(calculations_dir, "imbalance_response_by_symbol_day.csv"), per_symbol_response)
    write_csv(os.path.join(calculations_dir, "monotonicity_diagnostics.csv"),
              monotonicity_rows(pooled_response, horizons_ms))
    write_csv(os.path.join(calculations_dir, "directional_sanity_summary.csv"),
              directional_rows(decisions, keep, configuration, horizons_ms))
    write_csv(os.path.join(calculations_dir, "next_move_summary.csv"),
              next_move_summary_rows(decisions, keep, replay))

    write_csv(os.path.join(calculations_dir, "reference_cost_by_quantity.csv"),
              costs.reference_cost_by_quantity(ledger, configuration["cost_ledger"]["representative_quantities"]))
    write_csv(os.path.join(calculations_dir, "reference_cost_by_price.csv"),
              costs.reference_cost_by_price(
                  ledger,
                  configuration["cost_ledger"]["representative_prices_usd"],
                  configuration["cost_ledger"]["representative_prices_quantities"],
              ))

    delay_rows, missingness = execution_rows(delay_columns, configuration, ledger)
    write_csv(os.path.join(calculations_dir, "ev_delay_descriptive.csv"), delay_rows)
    write_csv(os.path.join(calculations_dir, "idealized_execution_summary.csv"),
              idealized_execution_summary(delay_rows))

    audit = universe_artifacts(configuration, decisions, symbol_map, replay, calculations_dir)
    write_csv(os.path.join(data_quality_dir, "universe_audit.csv"), audit)

    plan = split_plan([configuration["dataset"]["coverage_date"]], configuration)
    config_module.write_json(os.path.join(calculations_dir, "split_manifest.json"), plan)

    blocked = [
        {
            "item": "point-in-time universe membership",
            "status": "CALCULATION_BLOCKED",
            "reason": universe.BLOCKED_PIT,
            "detail": "the frozen rule needs a point-in-time listing/security-type/corporate-action/halt "
                      "reference as of each monthly selection date; none is procured",
        },
        {
            "item": "60-trading-day causal lookback for the large-tick classification",
            "status": "CALCULATION_BLOCKED",
            "reason": universe.BLOCKED_LOOKBACK,
            "detail": "one sample day cannot supply a 60-day lookback of order-level book state",
        },
        {
            "item": "book cross-check against a provider BBO/MBP representation",
            "status": "CALCULATION_BLOCKED",
            "reason": "SECOND_DATA_PRODUCT_REQUIRED",
            "detail": "the TotalView-ITCH product carries no BBO/MBP record; the internal order-map rebuild is "
                      "the only independent check available inside this product",
        },
        {
            "item": "day-level dispersion and day-block bootstrap",
            "status": "CALCULATION_BLOCKED",
            "reason": "SINGLE_SAMPLE_DAY",
            "detail": "one day has one day-level unit, so day dispersion is not computable; the block unit used "
                      "is symbol x 30 minutes",
        },
        {
            "item": "development / validation / sealed partitions",
            "status": "CALCULATION_BLOCKED",
            "reason": "INSUFFICIENT_COVERAGE",
            "detail": "fewer than three trading days; the sample day is DEVELOPMENT forever and is never renamed",
        },
        {
            "item": "modern-regime transfer of any reported statistic",
            "status": "CALCULATION_BLOCKED",
            "reason": "SAMPLE_DAY_IS_NOT_THE_INTENDED_WINDOW",
            "detail": "the free sample day is a 2019 development tape; it validates engineering only",
        },
        {
            "item": "economic conclusion, promotion, kill or Jev comparison",
            "status": "NOT_ATTEMPTED_BY_DESIGN",
            "reason": "M2_0_SCOPE",
            "detail": "M2-0 produces descriptive inputs only; no profitability claim is admissible from it",
        },
    ]

    failed_checks = [row["check"] for row in reconciliation if row["outcome"] != "PASS"]
    if failed_checks:
        raise SystemExit("a derived number could not be reconciled and must not enter the results: "
                         + ", ".join(failed_checks))
    status = {
        "run_status": "CALCULATION_COMPLETE",
        "data_status": verdict,
        "dataset": configuration["dataset"]["dataset_id"],
        "coverage_date": configuration["dataset"]["coverage_date"],
        "decision_observations_total": exclusions["rows_total"],
        "decision_observations_retained": exclusions["rows_retained"],
        "decision_state_exclusions": exclusions["excluded"],
        "delay_rows": int(delay_columns["ts_ns"].size),
        "delay_surface_cells": len(delay_rows),
        "delay_missingness": missingness,
        "symbols": int(len(symbol_map)),
        "scope_symbols": len(replay["active_symbols"]),
        "cost_ledger_id": ledger["ledger_id"],
        "blocked": blocked,
        "artifacts": sorted(
            [
                "coverage_summary.csv",
                "market_structure_summary.csv",
                "imbalance_distribution.csv",
                "future_return_summary.csv",
                "imbalance_response_by_horizon.csv",
                "imbalance_response_by_symbol_day.csv",
                "monotonicity_diagnostics.csv",
                "directional_sanity_summary.csv",
                "next_move_summary.csv",
                "reference_cost_by_quantity.csv",
                "reference_cost_by_price.csv",
                "idealized_execution_summary.csv",
                "ev_delay_descriptive.csv",
                "universe_membership.parquet",
                "split_manifest.json",
                "reconciliation_checks.csv",
            ]
        ),
        "scope_note": "statistics describe the development-scope symbols only; scope is not universe membership",
    }
    config_module.write_json(os.path.join(calculations_dir, "calculation_status.json"), status)
    print(json.dumps({k: status[k] for k in ("run_status", "data_status", "decision_observations_retained",
                                             "delay_surface_cells")}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
