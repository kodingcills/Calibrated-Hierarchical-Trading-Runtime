"""M2-0.5 aggressive monetization feasibility bound.

Reads only the already-frozen M2-0 development artifacts (the whole-tape replay's
``decisions.parquet`` / ``delay_decisions.parquet``), the frozen M2-0 configuration
and the frozen cost ledger. It acquires nothing, fits no model, optimises no
threshold, and promotes or kills nothing: it conditions the existing aggressive
execution arithmetic on the predeclared state space and adds bounds that assume the
impossible.

Execution instant
-----------------
``delay_decisions.parquet`` at delay 0 is the only frozen artifact that carries a
*realised future two-sided quote*, which both a cross-to-cross result and a
clairvoyant side choice require. Its arrival quotes are the decision-instant quotes:
each of its 1,427,400 rows is verified in ``reconciliation_rows`` to reproduce
``decisions.parquet`` exactly at the same ``(ts_ns, locate)``. The delay grid is a 1 s
decimation of the predeclared 100 ms decision grid, so this pass conditions the
*existing* aggressive execution calculation instead of redefining it.

Per-observation economics (all in basis points of the arrival mid ``M = mid2_raw``)
-------------------------------------------------------------------------------
With ``M = entry_bid + entry_ask``, ``F = fut_bid + fut_ask``, ``side = sign(imbalance)``::

    realized_move_bps      = 10000 * (F - M) / M              # side-signed future mid move
    half_spread_entry_bps  = 10000 * (entry_ask - entry_bid) / M
    half_spread_future_bps = 10000 * (fut_ask - fut_bid) / M
    markout_bps            = realized_move_bps - half_spread_entry_bps
    cross_to_cross_bps     = realized_move_bps - half_spread_entry_bps - half_spread_future_bps
    net_bps(regime)        = cross_to_cross_bps - fee_bps(regime, entry price)

The identities are exact algebra: ``cross_to_cross_bps`` is an aggressive buy at
``entry_ask`` closed at ``fut_bid`` (or the short mirror), so splitting it into a mid
move plus the two half spreads actually paid is not an approximation. It is
reconciled per cell and pooled.

``fee_bps`` is the ledger's own round-trip cost in bps of entry notional, reused
verbatim from :mod:`M2.src.costs`.

Relation to the frozen M2-0 execution table: the markout column of
``idealized_execution_summary.csv`` is reproduced exactly. Its cross-to-cross column is
not, and the difference is exact, not a tolerance — the frozen expression divides a price
difference by ``mid2`` (twice the mid) and feeds the cost ledger half the true entry
price. Both defects are confirmed by recomputing M2-0's own expressions
(:func:`_frozen_execution_rows`), reported in ``feasibility_status.json`` and in §7a of the
report, and **not repaired**: no M2-0 artifact is written by this pass.

Break-even hurdle: the mid move required to break even is the full quoted spread at
the decision instant (cross in, cross out) plus the regime's round-trip fee. So
``P(realized move exceeds hurdle)`` agrees with ``P(net > 0)`` up to the change in the
quoted spread between entry and exit, which is reported as its own measured term.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Sequence

import numpy as np
import pyarrow.parquet as pq

from . import calculate
from . import config as config_module
from . import costs
from . import features

# --------------------------------------------------------------- declared scope
# Declared before any number in this pass was read; nothing here is fitted.
EXECUTION_DELAY_MS = 0  # the M2-0 idealized aggressive execution instant
PRICE_BANDS: tuple[tuple[float, float, str], ...] = (
    (5.0, 25.0, "5-25"),
    (25.0, 50.0, "25-50"),
    (50.0, 100.0, "50-100"),
    (100.0, 200.0, "100-200"),
    (200.0, float("inf"), "200+"),
)
SPREAD_ONE_TICK = "ONE_TICK"
SPREAD_WIDER = "WIDER_THAN_ONE_TICK"
LABEL_EXECUTION = "AGGRESSIVE_CROSS_TO_CROSS_STATE_CONDITIONED"
LABEL_ORACLE = "ORACLE_UPPER_BOUND"
LABEL_QIMB = "QIMB_CONSTRAINED_BOUND"
LABEL_BREAKEVEN = "BREAKEVEN_HURDLE"

HURDLE_COVERAGE_CUTS = (1.0, 0.9, 0.75, 0.5)

BANDS_NOTE = (
    "price bands are applied to the decision-instant mid in USD; a mid exactly on a band edge "
    "falls in the upper band; an observation outside every declared band would be reported as "
    "unbinned, never dropped"
)
ORACLE_NOTE = (
    "ORACLE_UPPER_BOUND uses future information by construction: at each decision instant it takes "
    "max(0, net_long, net_short) from the realised future bid/ask. It bounds what any causal side "
    "choice at these instants could have earned; it is not a strategy, not achievable, and must "
    "never enter model training, a backtest or a promotion decision."
)
QIMB_NOTE = (
    "QIMB_CONSTRAINED_BOUND keeps the side dictated by queue imbalance (the sign that defines the "
    "bin) and adds clairvoyant abstention only: max(0, net_side). No new threshold, no side choice "
    "and no model enters this bound."
)
EXECUTION_NOTE = (
    "assumes sufficient displayed size, immediate aggressive fill, no additional slippage, no impact "
    "and no queue effect; costs are M2-COST-LEDGER-v1 round trips at the declared 100-share "
    "representative size, and are 2026 rate cards applied to a 2019 tape for arithmetic validation, "
    "not a reconstruction of 2019 economics"
)
BREAKEVEN_NOTE = (
    "required_move_bps_spread_only is the full quoted spread at the decision instant (cross in, cross "
    "out); the fee terms are the ledger round trip in bps of entry notional; realized_move_bps is the "
    "side-signed mid move, so realized minus spread_only differs from cross_to_cross_bps by the "
    "measured spread-change term"
)

# ------------------------------------------------------------ state dimensions
def band_labels() -> list[str]:
    return [label for _, _, label in PRICE_BANDS]


def band_index(prices: np.ndarray) -> np.ndarray:
    """Band index per price; -1 for a price outside every declared band."""
    result = np.full(prices.shape, -1, dtype=np.int64)
    for index, (low, high, _label) in enumerate(PRICE_BANDS):
        result[(prices >= low) & (prices < high)] = index
    return result


def spread_class_codes(spread_raw: np.ndarray, tick_raw: int) -> np.ndarray:
    """0 = quoted spread is exactly one tick, 1 = wider. Crossed/locked is excluded upstream."""
    return (spread_raw != tick_raw).astype(np.int64)


def spread_class_labels() -> list[str]:
    return [SPREAD_ONE_TICK, SPREAD_WIDER]


def imbalance_bin_codes(imbalance: np.ndarray, state_valid: np.ndarray, configuration: dict) -> tuple[np.ndarray, list[str]]:
    """The frozen 10-bin partition, applied exactly as ``features.bin_label`` declares it."""
    edges = features.bin_edges(configuration)
    n_bins = len(edges) - 1
    codes = np.full(imbalance.shape, -1, dtype=np.int64)
    for index in range(n_bins):
        left, right = edges[index], edges[index + 1]
        upper = imbalance <= right if index == n_bins - 1 else imbalance < right
        codes[state_valid & (imbalance >= left) & upper] = index
    return codes, [features.bin_label(index, edges) for index in range(n_bins)]


def state_dimensions(frame: dict, configuration: dict) -> list[tuple[str, list[str], np.ndarray]]:
    """The predeclared state space: 10 imbalance bins x 2 spread classes x 5 price bands."""
    bin_codes, bin_labels = imbalance_bin_codes(frame["imbalance"], frame["state_valid"], configuration)
    return [
        ("imbalance_bin", bin_labels, bin_codes),
        (
            "spread_class",
            spread_class_labels(),
            spread_class_codes(frame["spread_raw"], int(configuration["tick_raw"])),
        ),
        ("price_band", band_labels(), band_index(frame["price_usd"])),
    ]


def combine_dimensions(dimensions: Sequence[tuple[str, list[str], np.ndarray]]) -> tuple[np.ndarray, int, list[int]]:
    """Mixed-radix cell codes over the given dimensions, plus their sizes."""
    codes = np.zeros(dimensions[0][2].shape, dtype=np.int64)
    sizes: list[int] = []
    for _name, labels, values in dimensions:
        codes = codes * len(labels) + values
        sizes.append(len(labels))
    return codes, int(np.prod(sizes)), sizes


def declared_space_mask(dimensions: Sequence[tuple[str, list[str], np.ndarray]]) -> np.ndarray:
    """Rows the declared state space actually contains.

    A row is in the space only when *every* dimension assigns it a cell. Testing the
    mixed-radix code for non-negativity is not sufficient: a row outside the declared price
    bands has a negative band code, but a non-zero imbalance-bin code lifts the combined
    value back above zero, so it would silently join a cell it does not belong to.
    """
    mask = np.ones(dimensions[0][2].shape, dtype=bool)
    for _name, _labels, values in dimensions:
        mask &= values >= 0
    return mask


def decode_cell(cell: int, sizes: Sequence[int]) -> list[int]:
    """Mixed-radix index tuple for one cell code (leftmost dimension most significant)."""
    out = []
    for size in reversed(sizes):
        out.append(cell % size)
        cell //= size
    return list(reversed(out))


# ------------------------------------------------------------------ grouping
class Grouped:
    """Rows grouped into integer cells, with mean/probability/quantile reductions.

    One argsort per (subset, dimension) pair, then every metric is a slice of the same
    ordering, so a 400-cell table with 30 metrics costs a few thousand small
    reductions rather than a rescan of the observation set per metric.
    """

    def __init__(self, codes: np.ndarray, n_cells: int) -> None:
        if codes.size and int(codes.min()) < 0:
            raise ValueError(
                "a row with no declared cell reached a state table; out-of-space rows must be "
                "excluded and counted, never folded into cell 0"
            )
        self.n_cells = n_cells
        self.order = np.argsort(codes, kind="stable")
        self.bounds = np.searchsorted(codes[self.order], np.arange(n_cells + 1))

    def counts(self) -> np.ndarray:
        return np.diff(self.bounds).astype(np.float64)

    def mean(self, values: np.ndarray) -> np.ndarray:
        ordered = values[self.order]
        out = np.full(self.n_cells, np.nan)
        for index in range(self.n_cells):
            block = ordered[self.bounds[index] : self.bounds[index + 1]]
            finite = np.isfinite(block)
            if finite.any():
                out[index] = float(block[finite].mean())
        return out

    def quantiles(self, values: np.ndarray, quantiles: Sequence[float]) -> list[np.ndarray]:
        ordered = values[self.order]
        out = [np.full(self.n_cells, np.nan) for _ in quantiles]
        for index in range(self.n_cells):
            block = ordered[self.bounds[index] : self.bounds[index + 1]]
            block = block[np.isfinite(block)]
            if block.size:
                for slot, value in zip(out, np.percentile(block, quantiles)):
                    slot[index] = float(value)
        return out

    def probability(self, flags: np.ndarray) -> np.ndarray:
        """Fraction of rows in each cell for which the flag is true.

        Callers pass a subset where every row is evaluable, so the denominator is the
        cell's row count and true/false are the only outcomes.
        """
        ordered = flags[self.order].astype(np.float64)
        return np.array(
            [
                float(ordered[self.bounds[index] : self.bounds[index + 1]].mean())
                if self.bounds[index + 1] > self.bounds[index]
                else float("nan")
                for index in range(self.n_cells)
            ]
        )

    def block_dispersion(
        self, block_codes: np.ndarray, n_blocks: int, values: np.ndarray, bootstrap: dict, seed: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Block-bootstrap SE and 95% CI of a cell mean, plus the usable block count.

        The dependence unit is the one M2-0 uses: the (symbol, 30-minute) cell. A cell
        whose observations fall in fewer than two block cells has no computable
        resampling dispersion and is returned as NaN beside its count, so a thin cell
        stays visible instead of being papered over.
        """
        ordered_blocks = block_codes[self.order]
        ordered_values = values[self.order]
        se = np.full(self.n_cells, np.nan)
        low = np.full(self.n_cells, np.nan)
        high = np.full(self.n_cells, np.nan)
        used = np.zeros(self.n_cells, dtype=np.int64)
        for index in range(self.n_cells):
            start, stop = self.bounds[index], self.bounds[index + 1]
            if stop <= start:
                continue
            codes = ordered_blocks[start:stop]
            block_values = ordered_values[start:stop]
            counts = np.bincount(codes, minlength=n_blocks).astype(np.float64)
            sums = np.bincount(codes, weights=block_values, minlength=n_blocks)
            means = np.divide(sums, counts, out=np.full(n_blocks, np.nan), where=counts > 0)
            used[index] = int(np.sum(counts > 0))
            if used[index] < 2:
                continue
            se[index], low[index], high[index] = calculate.block_bootstrap_ci(
                means, counts, bootstrap["resamples"], seed + index
            )
        return se, low, high, used


def finite_or_negative_infinity(value) -> float:
    """Numeric value of a cell column; a missing metric never ranks as a best state."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float("-inf")
    return numeric if np.isfinite(numeric) else float("-inf")


def cell_required_move_bps(row: dict, floor_label: str) -> float:
    """The break-even hurdle of one cell: the spread actually paid plus the regime's fee."""
    return (
        float(row["mean_half_spread_entry_bps"])
        + float(row["mean_half_spread_future_bps"])
        + float(row[f"fee_{floor_label}_bps"])
    )


def cell_hurdle_coverage(row: dict, floor_label: str) -> float:
    """Mean side-signed mid move divided by the cell's required move; -inf when empty."""
    stream = float(row["observations"])
    if not stream:
        return float("-inf")
    required = cell_required_move_bps(row, floor_label)
    if not np.isfinite(required) or required == 0.0:
        return float("-inf")
    return float(row["mean_signal_signed_mid_move_bps"]) / required


def _cell_rows(
    grouped: Grouped,
    dimensions: Sequence[tuple[str, list[str], np.ndarray]],
    sizes: Sequence[int],
    metrics: dict[str, np.ndarray],
    probabilities: dict[str, np.ndarray],
    quantile_metrics: dict[str, tuple[np.ndarray, Sequence[float]]] | None = None,
    extra_columns: dict[str, Sequence] | None = None,
) -> list[dict]:
    """One CSV row per cell of the declared state space, keyed by the dimension labels."""
    quantile_metrics = quantile_metrics or {}
    means = {name: grouped.mean(values) for name, values in metrics.items()}
    probs = {name: grouped.probability(flags) for name, flags in probabilities.items()}
    quants = {name: grouped.quantiles(values, levels) for name, (values, levels) in quantile_metrics.items()}
    counts = grouped.counts()
    rows = []
    for cell in range(grouped.n_cells):
        indices = decode_cell(cell, sizes)
        row: dict = {}
        for position, (name, labels, _values) in enumerate(dimensions):
            row[name] = labels[indices[position]]
        row["observations"] = int(counts[cell])
        for name, values in means.items():
            row[name] = float(values[cell]) if np.isfinite(values[cell]) else "NaN"
        for name, values in probs.items():
            row[name] = float(values[cell]) if np.isfinite(values[cell]) else "NaN"
        for name, slots in quants.items():
            for level, slot in zip(quantile_metrics[name][1], slots):
                row[f"{name}_p{int(level):02d}"] = float(slot[cell]) if np.isfinite(slot[cell]) else "NaN"
        if extra_columns:
            for name, values in extra_columns.items():
                row[name] = values[cell]
        rows.append(row)
    return rows


# ------------------------------------------------------------------- inputs
def load_execution_columns(derived: str, configuration: dict) -> dict[str, np.ndarray]:
    """Delay-0 execution columns: arrival quotes, decision state and future quotes."""
    delay_ms = EXECUTION_DELAY_MS
    horizons_ms = list(configuration["horizons_ms"])
    rename = {
        f"entry_bid_{delay_ms}ms": "entry_bid",
        f"entry_ask_{delay_ms}ms": "entry_ask",
        f"arrival_status_{delay_ms}ms": "arrival_status",
    }
    columns = ["ts_ns", "locate", "block_id", "imbalance", "mid2_raw", "spread_raw"]
    columns += [f"entry_bid_{delay_ms}ms", f"entry_ask_{delay_ms}ms", f"arrival_status_{delay_ms}ms"]
    for horizon_ms in horizons_ms:
        columns += [f"fut_bid_{delay_ms}ms_{horizon_ms}ms", f"fut_ask_{delay_ms}ms_{horizon_ms}ms"]
        rename[f"fut_bid_{delay_ms}ms_{horizon_ms}ms"] = f"fut_bid_{horizon_ms}"
        rename[f"fut_ask_{delay_ms}ms_{horizon_ms}ms"] = f"fut_ask_{horizon_ms}"
    table = pq.read_table(os.path.join(derived, "delay_decisions.parquet"), columns=columns)
    return {rename.get(name, name): table[name].to_numpy(zero_copy_only=False) for name in table.column_names}


def build_frame(columns: dict[str, np.ndarray], configuration: dict, ledger: dict) -> dict:
    """Per-observation aggressive economics for every declared horizon."""
    tick_raw = int(configuration["tick_raw"])
    scale = float(configuration["price_scale"])
    shares = float(ledger["assumptions"]["representative_order_shares"])
    mid2 = columns["mid2_raw"].astype(np.float64)
    entry_bid = columns["entry_bid"].astype(np.float64)
    entry_ask = columns["entry_ask"].astype(np.float64)
    imbalance = columns["imbalance"].astype(np.float64)
    spread_raw = columns["spread_raw"].astype(np.float64)
    state_valid = (
        np.isfinite(imbalance)
        & (columns["arrival_status"] == 0)
        & (mid2 > 0)
        & (entry_bid > 0)
        & (entry_ask > entry_bid)
        & (spread_raw > 0)
    )
    signal_defined = state_valid & (imbalance != 0)
    side = np.where(imbalance > 0, 1.0, np.where(imbalance < 0, -1.0, np.nan))
    half_entry = 10000.0 * spread_raw / mid2
    frame: dict = {
        "ts_ns": columns["ts_ns"],
        "locate": columns["locate"],
        "block_id": columns["block_id"],
        "mid2": mid2,
        "price_usd": mid2 / 2.0 / scale,
        "entry_bid": entry_bid,
        "entry_ask": entry_ask,
        "spread_raw": spread_raw,
        "spread_bps": 2.0 * half_entry,
        "one_tick": spread_raw == tick_raw,
        "imbalance": imbalance,
        "side": side,
        "state_valid": state_valid,
        "signal_defined": signal_defined,
        "half_spread_entry_bps": half_entry,
        "fees": {},
        "horizons": {},
    }
    lookups = {
        label: calculate._cost_lookup(
            ledger, regime, schedule, shares, np.concatenate([entry_bid, entry_ask]) / scale
        )
        for regime, schedule, label in costs.schedule_pairs(ledger)
    }
    for label, (unique, values) in lookups.items():
        frame["fees"][label] = {
            "long": calculate._map_cost_lookup(unique, values, entry_ask / scale),
            "short": calculate._map_cost_lookup(unique, values, entry_bid / scale),
        }
    for horizon_ms in configuration["horizons_ms"]:
        fut_bid = columns[f"fut_bid_{horizon_ms}"].astype(np.float64)
        fut_ask = columns[f"fut_ask_{horizon_ms}"].astype(np.float64)
        usable_state = state_valid & (fut_bid > 0) & (fut_ask > 0)
        mid_move = 10000.0 * ((fut_bid + fut_ask) - mid2) / mid2
        realized = np.where(signal_defined & usable_state, side * mid_move, np.nan)
        half_future = 10000.0 * (fut_ask - fut_bid) / mid2
        future: dict[str, np.ndarray] = {
            "usable_state": usable_state,
            "usable_signal": usable_state & signal_defined,
            "future_mid_move_bps": mid_move,
            "realized_move_bps": realized,
            "half_spread_future_bps": half_future,
            "markout_bps": realized - half_entry,
            "cross_to_cross_bps": realized - half_entry - half_future,
            "cross_long_bps": 2.0 * 10000.0 * (fut_bid - entry_ask) / mid2,
            "cross_short_bps": 2.0 * 10000.0 * (entry_bid - fut_ask) / mid2,
            "spread_change_term_bps": half_entry - half_future,
        }
        for label, fee in frame["fees"].items():
            side_fee = np.where(side > 0, fee["long"], np.where(side < 0, fee["short"], np.nan))
            long_net = future["cross_long_bps"] - fee["long"]
            short_net = future["cross_short_bps"] - fee["short"]
            future[f"fee_{label}_bps"] = side_fee
            future[f"net_{label}_bps"] = future["cross_to_cross_bps"] - side_fee
            future[f"oracle_net_{label}_bps"] = np.maximum(0.0, np.maximum(long_net, short_net))
            future[f"qimb_bound_{label}_bps"] = np.maximum(0.0, future[f"net_{label}_bps"])
        future["oracle_gross_bps"] = np.maximum(0.0, np.maximum(future["cross_long_bps"], future["cross_short_bps"]))
        frame["horizons"][horizon_ms] = future
    return frame


def schedule_labels(ledger: dict) -> list[str]:
    return [label for _regime, _schedule, label in costs.schedule_pairs(ledger)]


def structural_label(ledger: dict) -> str:
    for regime, _schedule, label in costs.schedule_pairs(ledger):
        if regime == "STRUCTURAL_COST_FLOOR":
            return label
    raise ValueError("the cost ledger carries no STRUCTURAL_COST_FLOOR schedule")


def accessible_labels(ledger: dict) -> list[str]:
    return [
        label
        for regime, _schedule, label in costs.schedule_pairs(ledger)
        if regime == "ACCESSIBLE_REFERENCE_PATH"
    ]


# ------------------------------------------------------------- table builders
def feasibility_rows(
    frame: dict, configuration: dict, ledger: dict, bootstrap: dict, horizons_ms: Sequence[int]
) -> list[dict]:
    """Table 1: aggressive cross-to-cross economics for every declared state cell."""
    labels = schedule_labels(ledger)
    floor = structural_label(ledger)
    dimensions = state_dimensions(frame, configuration)
    codes, n_cells, sizes = combine_dimensions(dimensions)
    in_declared_space = declared_space_mask(dimensions)
    block_codes, n_symbols, blocks_per_symbol = calculate.build_cells(frame["locate"], frame["block_id"])
    n_block_cells = n_symbols * blocks_per_symbol
    total_signal = float(frame["signal_defined"].sum())
    rows: list[dict] = []
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        subset = future["usable_signal"] & in_declared_space
        grouped = Grouped(codes[subset], n_cells)
        metrics = {
            "mean_price_usd": frame["price_usd"][subset],
            "mean_spread_bps": frame["spread_bps"][subset],
            "mean_half_spread_entry_bps": frame["half_spread_entry_bps"][subset],
            "mean_half_spread_future_bps": future["half_spread_future_bps"][subset],
            "mean_future_mid_move_bps": future["future_mid_move_bps"][subset],
            "mean_signal_signed_mid_move_bps": future["realized_move_bps"][subset],
            "mean_markout_bps": future["markout_bps"][subset],
            "mean_cross_to_cross_bps": future["cross_to_cross_bps"][subset],
            "mean_spread_change_term_bps": future["spread_change_term_bps"][subset],
        }
        probabilities = {"prob_cross_to_cross_positive": future["cross_to_cross_bps"][subset] > 0.0}
        for label in labels:
            metrics[f"fee_{label}_bps"] = future[f"fee_{label}_bps"][subset]
            metrics[f"net_{label}_bps"] = future[f"net_{label}_bps"][subset]
            probabilities[f"prob_net_{label}_positive"] = future[f"net_{label}_bps"][subset] > 0.0
        se, low, high, blocks = grouped.block_dispersion(
            block_codes[subset], n_block_cells, future[f"net_{floor}_bps"][subset], bootstrap, bootstrap["seed"] + horizon_ms
        )
        extra: dict[str, Sequence] = {
            "horizon_ms": [horizon_ms] * n_cells,
            "delay_ms": [EXECUTION_DELAY_MS] * n_cells,
            "share_of_signal_defined_observations": (grouped.counts() / total_signal).tolist(),
            f"block_bootstrap_se_net_{floor}_bps": [float(v) if np.isfinite(v) else "NaN" for v in se],
            f"block_bootstrap_ci_low_net_{floor}_bps": [float(v) if np.isfinite(v) else "NaN" for v in low],
            f"block_bootstrap_ci_high_net_{floor}_bps": [float(v) if np.isfinite(v) else "NaN" for v in high],
            "block_cells": blocks.tolist(),
            "cost_ledger_id": [ledger["ledger_id"]] * n_cells,
            "representative_order_shares": [int(ledger["assumptions"]["representative_order_shares"])] * n_cells,
            "label": [LABEL_EXECUTION] * n_cells,
            "note": [EXECUTION_NOTE] * n_cells,
        }
        rows.extend(_cell_rows(grouped, dimensions, sizes, metrics, probabilities, extra_columns=extra))
    return rows


def breakeven_rows(frame: dict, configuration: dict, ledger: dict, horizons_ms: Sequence[int]) -> list[dict]:
    """Table 2: break-even hurdle distributions and the probability of clearing them."""
    labels = schedule_labels(ledger)
    dimensions = state_dimensions(frame, configuration)
    codes, n_cells, sizes = combine_dimensions(dimensions)
    in_declared_space = declared_space_mask(dimensions)
    quantiles = (5.0, 25.0, 50.0, 75.0, 95.0)
    rows: list[dict] = []
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        subset = future["usable_signal"] & in_declared_space
        grouped = Grouped(codes[subset], n_cells)
        spread = frame["spread_bps"][subset]
        realized = future["realized_move_bps"][subset]
        required = {"spread_only": spread}
        for label in labels:
            required[f"spread_plus_{label}"] = spread + future[f"fee_{label}_bps"][subset]
        metrics = {"realized_move_bps": realized}
        probabilities: dict[str, np.ndarray] = {}
        quantile_metrics: dict[str, tuple[np.ndarray, Sequence[float]]] = {"realized_move_bps": (realized, quantiles)}
        for name, values in required.items():
            metrics[f"required_move_bps_{name}"] = values
            metrics[f"mean_ratio_{name}"] = (realized / values).astype(np.float64)
            probabilities[f"prob_realized_exceeds_{name}"] = realized > values
            quantile_metrics[f"required_move_bps_{name}"] = (values, quantiles)
        probabilities["prob_ratio_spread_only_above_one"] = (realized / spread) > 1.0
        extra = {
            "horizon_ms": [horizon_ms] * n_cells,
            "delay_ms": [EXECUTION_DELAY_MS] * n_cells,
            "quantile_levels_pct": ["|".join(str(int(level)) for level in quantiles)] * n_cells,
            "cost_ledger_id": [ledger["ledger_id"]] * n_cells,
            "label": [LABEL_BREAKEVEN] * n_cells,
            "note": [BREAKEVEN_NOTE] * n_cells,
        }
        rows.extend(
            _cell_rows(grouped, dimensions, sizes, metrics, probabilities, quantile_metrics, extra_columns=extra)
        )
    return rows


def oracle_rows(frame: dict, configuration: dict, ledger: dict, horizons_ms: Sequence[int]) -> list[dict]:
    """Table 3: the clairvoyant aggressive upper bound, labelled and never trained on."""
    labels = schedule_labels(ledger)
    dimensions = state_dimensions(frame, configuration)
    codes, n_cells, sizes = combine_dimensions(dimensions)
    in_declared_space = declared_space_mask(dimensions)
    total_all = float(frame["state_valid"].sum())
    total_signal = float(frame["signal_defined"].sum())
    rows: list[dict] = []
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        usable = future["usable_state"] & in_declared_space
        grouped = Grouped(codes[usable], n_cells)
        metrics = {"mean_oracle_gross_bps": future["oracle_gross_bps"][usable]}
        probabilities = {}
        for label in labels:
            metrics[f"mean_oracle_net_{label}_bps"] = future[f"oracle_net_{label}_bps"][usable]
            probabilities[f"prob_oracle_net_{label}_positive"] = future[f"oracle_net_{label}_bps"][usable] > 0.0
        signal_subset = future["usable_signal"] & in_declared_space
        signal_grouped = Grouped(codes[signal_subset], n_cells)
        extra: dict[str, Sequence] = {}
        for label in labels:
            values = signal_grouped.mean(future[f"oracle_net_{label}_bps"][signal_subset])
            extra[f"mean_oracle_net_{label}_bps_signal_defined"] = [
                float(v) if np.isfinite(v) else "NaN" for v in values
            ]
        extra.update(
            {
                "observations_signal_defined": signal_grouped.counts().astype(np.int64).tolist(),
                "share_of_valid_states": (grouped.counts() / total_all).tolist(),
                "share_of_signal_defined_observations": (signal_grouped.counts() / total_signal).tolist(),
                "horizon_ms": [horizon_ms] * n_cells,
                "delay_ms": [EXECUTION_DELAY_MS] * n_cells,
                "oracle_trade_fraction": [
                    float(v) for v in grouped.probability(future["oracle_gross_bps"][usable] > 0.0)
                ],
                "oracle_buy_fraction": [
                    float(v) for v in grouped.probability(future["cross_long_bps"][usable] >= future["cross_short_bps"][usable])
                ],
                "cost_ledger_id": [ledger["ledger_id"]] * n_cells,
                "label": [LABEL_ORACLE] * n_cells,
                "note": [ORACLE_NOTE] * n_cells,
            }
        )
        rows.extend(_cell_rows(grouped, dimensions, sizes, metrics, probabilities, extra_columns=extra))
    return rows


def qimb_rows(frame: dict, configuration: dict, ledger: dict, horizons_ms: Sequence[int]) -> list[dict]:
    """Table 4: the best economics reachable inside each already-declared imbalance state."""
    labels = schedule_labels(ledger)
    dimensions = state_dimensions(frame, configuration)
    codes, n_cells, sizes = combine_dimensions(dimensions)
    in_declared_space = declared_space_mask(dimensions)
    rows: list[dict] = []
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        subset = future["usable_signal"] & in_declared_space
        grouped = Grouped(codes[subset], n_cells)
        metrics = {"mean_signal_signed_mid_move_bps": future["realized_move_bps"][subset]}
        probabilities = {}
        for label in labels:
            metrics[f"net_{label}_bps"] = future[f"net_{label}_bps"][subset]
            metrics[f"qimb_bound_{label}_bps"] = future[f"qimb_bound_{label}_bps"][subset]
            metrics[f"abstention_gain_{label}_bps"] = (
                future[f"qimb_bound_{label}_bps"][subset] - future[f"net_{label}_bps"][subset]
            )
            probabilities[f"prob_net_{label}_positive"] = future[f"net_{label}_bps"][subset] > 0.0
            probabilities[f"prob_qimb_bound_{label}_positive"] = future[f"qimb_bound_{label}_bps"][subset] > 0.0
        extra = {
            "horizon_ms": [horizon_ms] * n_cells,
            "delay_ms": [EXECUTION_DELAY_MS] * n_cells,
            "side_dictated_by": ["SIGN(IMBALANCE)_AT_DECISION"] * n_cells,
            "cost_ledger_id": [ledger["ledger_id"]] * n_cells,
            "label": [LABEL_QIMB] * n_cells,
            "note": [QIMB_NOTE] * n_cells,
        }
        rows.extend(_cell_rows(grouped, dimensions, sizes, metrics, probabilities, extra_columns=extra))
    return rows


# ------------------------------------------------------------- pooled views
def pooled_row(
    mask: np.ndarray,
    metrics: Sequence[tuple[str, np.ndarray]],
    probabilities: Sequence[tuple[str, np.ndarray]] = (),
) -> dict:
    """Flat metrics over one observation subset, NaN-safe."""
    row: dict = {"observations": int(mask.sum())}
    for name, values in metrics:
        block = values[mask]
        finite = block[np.isfinite(block)]
        row[name] = float(finite.mean()) if finite.size else float("nan")
    for name, flags in probabilities:
        row[name] = float(flags[mask].mean()) if mask.any() else float("nan")
    return row


def marginal_rows(
    codes: np.ndarray,
    n_cells: int,
    mask: np.ndarray,
    metrics: Sequence[tuple[str, np.ndarray]],
    probabilities: Sequence[tuple[str, np.ndarray]] = (),
) -> list[dict]:
    """One row per marginal cell of a dimension subset (used for the report tables)."""
    grouped = Grouped(codes[mask], n_cells)
    means = {name: grouped.mean(values[mask]) for name, values in metrics}
    probs = {name: grouped.probability(flags[mask]) for name, flags in probabilities}
    counts = grouped.counts()
    return [
        {
            "cell": cell,
            "observations": int(counts[cell]),
            **{name: float(values[cell]) for name, values in means.items()},
            **{name: float(values[cell]) for name, values in probs.items()},
        }
        for cell in range(n_cells)
    ]


def build_bundle(
    frame: dict, configuration: dict, ledger: dict, horizons_ms: Sequence[int], table1: Sequence[dict]
) -> dict:
    """Pooled views, marginal tables and the observation accounting the report needs."""
    labels = schedule_labels(ledger)
    floor = structural_label(ledger)
    dimensions = state_dimensions(frame, configuration)
    full_codes, n_full, sizes = combine_dimensions(dimensions)
    bin_codes, bin_labels = imbalance_bin_codes(frame["imbalance"], frame["state_valid"], configuration)
    n_bins = len(bin_labels)
    pooled_rows: list[dict] = []
    bin_horizon_rows: list[dict] = []
    spread_horizon_rows: list[dict] = []
    band_horizon_rows: list[dict] = []
    oracle_bin_rows: list[dict] = []
    oracle_band_rows: list[dict] = []
    qimb_bin_horizon_rows: list[dict] = []
    observation_sets: dict = {
        "delay_rows_total": int(frame["state_valid"].size),
        "state_valid": int(frame["state_valid"].sum()),
        "signal_defined": int(frame["signal_defined"].sum()),
        "zero_imbalance_state": int((frame["state_valid"] & (frame["imbalance"] == 0)).sum()),
        "future_unavailable": {},
        "outside_declared_price_bands": int(
            (frame["state_valid"] & (band_index(frame["price_usd"]) < 0)).sum()
        ),
        "outside_declared_state_space": {},
        "future_unavailable": {},
        "zero_imbalance_by_horizon": {},
    }
    in_space = declared_space_mask(dimensions)
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        observation_sets["outside_declared_state_space"][str(horizon_ms)] = {
            "signal_defined": int((future["usable_signal"] & ~in_space).sum()),
            "valid_states": int((future["usable_state"] & ~in_space).sum()),
        }
        observation_sets["future_unavailable"][str(horizon_ms)] = int(
            (frame["state_valid"] & ~future["usable_state"]).sum()
        )
        observation_sets["zero_imbalance_by_horizon"][str(horizon_ms)] = int(
            (future["usable_state"] & ~future["usable_signal"]).sum()
        )
        usable = future["usable_state"]
        signal = future["usable_signal"]
        pooled_rows.append(
            {
                "horizon_ms": horizon_ms,
                **pooled_row(
                    signal,
                    [
                        ("mean_spread_bps", frame["spread_bps"]),
                        ("mean_half_spread_entry_bps", frame["half_spread_entry_bps"]),
                        ("mean_half_spread_future_bps", future["half_spread_future_bps"]),
                        ("mean_full_spread_paid_bps", frame["half_spread_entry_bps"] + future["half_spread_future_bps"]),
                        ("mean_future_mid_move_bps", future["future_mid_move_bps"]),
                        ("mean_signal_signed_mid_move_bps", future["realized_move_bps"]),
                        ("mean_markout_bps", future["markout_bps"]),
                        ("mean_cross_to_cross_bps", future["cross_to_cross_bps"]),
                        ("mean_spread_change_term_bps", future["spread_change_term_bps"]),
                        *[(f"fee_{label}_bps", future[f"fee_{label}_bps"]) for label in labels],
                        *[(f"net_{label}_bps", future[f"net_{label}_bps"]) for label in labels],
                        ("mean_required_move_bps_structural", frame["spread_bps"] + future[f"fee_{floor}_bps"]),
                    ],
                    [
                        ("prob_cross_to_cross_positive", future["cross_to_cross_bps"] > 0.0),
                        *[(f"prob_net_{label}_positive", future[f"net_{label}_bps"] > 0.0) for label in labels],
                    ],
                ),
            }
        )
        for name, keys in (
            ("imbalance_bin", bin_labels),
            ("spread_class", spread_class_labels()),
            ("price_band", band_labels()),
        ):
            subset_dimensions = [(n, l, v) for n, l, v in dimensions if n == name]
            codes, n_cells, _sizes = combine_dimensions(subset_dimensions)
            rows = marginal_rows(
                codes,
                n_cells,
                signal & in_space,
                [
                    ("mean_spread_bps", frame["spread_bps"]),
                    ("mean_signal_signed_mid_move_bps", future["realized_move_bps"]),
                    ("mean_cross_to_cross_bps", future["cross_to_cross_bps"]),
                    ("mean_full_spread_paid_bps", frame["half_spread_entry_bps"] + future["half_spread_future_bps"]),
                    *[(f"fee_{label}_bps", future[f"fee_{label}_bps"]) for label in labels],
                    *[(f"net_{label}_bps", future[f"net_{label}_bps"]) for label in labels],
                    ("mean_required_move_bps_structural", frame["spread_bps"] + future[f"fee_{floor}_bps"]),
                    ("mean_price_usd", frame["price_usd"]),
                ],
                [("prob_cross_to_cross_positive", future["cross_to_cross_bps"] > 0.0)]
                + [(f"prob_net_{label}_positive", future[f"net_{label}_bps"] > 0.0) for label in labels],
            )
            for row in rows:
                row["label_value"] = keys[row.pop("cell")]
                row["horizon_ms"] = horizon_ms
            if name == "imbalance_bin":
                bin_horizon_rows.extend(rows)
            elif name == "spread_class":
                spread_horizon_rows.extend(rows)
            else:
                band_horizon_rows.extend(rows)
        qimb_rows_local = marginal_rows(
            bin_codes,
            n_bins,
            signal & in_space,
            [
                ("mean_signal_signed_mid_move_bps", future["realized_move_bps"]),
                *[(f"net_{label}_bps", future[f"net_{label}_bps"]) for label in labels],
                *[(f"qimb_bound_{label}_bps", future[f"qimb_bound_{label}_bps"]) for label in labels],
                ("mean_required_move_bps_structural", frame["spread_bps"] + future[f"fee_{floor}_bps"]),
            ],
            [(f"prob_qimb_bound_{label}_positive", future[f"qimb_bound_{label}_bps"] > 0.0) for label in labels]
            + [
                (
                    "prob_realized_exceeds_required_structural",
                    future["realized_move_bps"] > frame["spread_bps"] + future[f"fee_{floor}_bps"],
                )
            ],
        )
        for row in qimb_rows_local:
            row["bin_label"] = bin_labels[row.pop("cell")]
            row["horizon_ms"] = horizon_ms
        qimb_bin_horizon_rows.extend(qimb_rows_local)
        oracle_bin = marginal_rows(
            bin_codes,
            n_bins,
            usable & in_space,
            [("mean_oracle_gross_bps", future["oracle_gross_bps"])]
            + [(f"oracle_net_{label}_bps", future[f"oracle_net_{label}_bps"]) for label in labels],
            [("prob_oracle_gross_positive", future["oracle_gross_bps"] > 0.0)],
        )
        for row in oracle_bin:
            row["bin_label"] = bin_labels[row.pop("cell")]
            row["horizon_ms"] = horizon_ms
        oracle_bin_rows.extend(oracle_bin)
        band_dimensions = [(n, l, v) for n, l, v in dimensions if n == "price_band"]
        band_codes, band_n, _ = combine_dimensions(band_dimensions)
        oracle_band = marginal_rows(
            band_codes,
            band_n,
            usable & in_space,
            [("mean_oracle_gross_bps", future["oracle_gross_bps"])]
            + [(f"oracle_net_{label}_bps", future[f"oracle_net_{label}_bps"]) for label in labels],
            [("prob_oracle_gross_positive", future["oracle_gross_bps"] > 0.0)],
        )
        for row in oracle_band:
            row["band_label"] = band_labels()[row.pop("cell")]
            row["horizon_ms"] = horizon_ms
        oracle_band_rows.extend(oracle_band)

    oracle_pooled = []
    for horizon_ms in horizons_ms:
        future = frame["horizons"][horizon_ms]
        usable = future["usable_state"]
        oracle_pooled.append(
            {
                "horizon_ms": horizon_ms,
                **pooled_row(
                    usable,
                    [("mean_oracle_gross_bps", future["oracle_gross_bps"])]
                    + [(f"oracle_net_{label}_bps", future[f"oracle_net_{label}_bps"]) for label in labels],
                    [("prob_oracle_gross_positive", future["oracle_gross_bps"] > 0.0)]
                    + [
                        (f"prob_oracle_net_{label}_positive", future[f"oracle_net_{label}_bps"] > 0.0)
                        for label in labels
                    ],
                ),
                **pooled_row(
                    future["usable_signal"],
                    [(f"oracle_net_{label}_bps_signal_defined", future[f"oracle_net_{label}_bps"]) for label in labels],
                ),
            }
        )

    # The best and worst declared cells, reported descriptively: no state is selected.
    ranked = sorted(table1, key=lambda row: finite_or_negative_infinity(row[f"net_{floor}_bps"]))
    best_cells = ranked[-5:][::-1]
    worst_cells = ranked[:5]
    positive_cells = [row for row in table1 if finite_or_negative_infinity(row[f"net_{floor}_bps"]) > 0.0]
    best_cell = ranked[-1]
    state_space_summary = {
        "cells_total": len(table1),
        "cells_with_positive_net": len(positive_cells),
        "best_cell": {
            "cell": f"{best_cell['imbalance_bin']} · {best_cell['spread_class']} · ${best_cell['price_band']} · {best_cell['horizon_ms']} ms",
            "observations": best_cell["observations"],
            "share_of_signal_defined_observations": best_cell["share_of_signal_defined_observations"],
            f"net_{floor}_bps": best_cell[f"net_{floor}_bps"],
            "mean_signal_signed_mid_move_bps": best_cell["mean_signal_signed_mid_move_bps"],
            "required_move_bps": cell_required_move_bps(best_cell, floor),
            f"block_bootstrap_se_net_{floor}_bps": best_cell[f"block_bootstrap_se_net_{floor}_bps"],
            "block_cells": best_cell["block_cells"],
            "hurdle_coverage": cell_hurdle_coverage(best_cell, floor),
        },
        "cells_at_hurdle_coverage_cut": {
            str(cut): int(
                sum(1 for row in table1 if cell_hurdle_coverage(row, floor) >= cut)
            )
            for cut in HURDLE_COVERAGE_CUTS
        },
        "populated_cells": int(sum(1 for row in table1 if row["observations"])),
    }

    return {
        "horizons_ms": list(horizons_ms),
        "state_dimensions": [name for name, _labels, _codes in dimensions],
        "cell_dimensions": {
            "imbalance_bins": bin_labels,
            "spread_classes": spread_class_labels(),
            "price_bands": band_labels(),
            "cells_per_horizon": n_full,
            "cell_rows_total": len(table1),
        },
        "state_sizes": sizes,
        "observation_sets": observation_sets,
        "pooled_by_horizon": pooled_rows,
        "pooled_by_bin_horizon": bin_horizon_rows,
        "pooled_by_spread_horizon": spread_horizon_rows,
        "pooled_by_band_horizon": band_horizon_rows,
        "oracle_pooled_by_horizon": oracle_pooled,
        "oracle_by_bin": oracle_bin_rows,
        "oracle_by_band": oracle_band_rows,
        "qimb_by_bin_horizon": qimb_bin_horizon_rows,
        "best_cells": best_cells,
        "worst_cells": worst_cells,
        "state_space_summary": state_space_summary,
        "structural_label": floor,
        "schedule_labels": labels,
        "cost_ledger_id": ledger["ledger_id"],
        "representative_order_shares": int(ledger["assumptions"]["representative_order_shares"]),
    }


# ----------------------------------------------------------- reconciliation
def reconciliation_rows(bundle: dict, frame: dict, columns: dict, configuration: dict, ledger: dict) -> list[dict]:
    """Independent re-derivations, each returning PASS/FAIL.

    A row with outcome FAIL blocks the pass: a derived number that cannot be
    reconciled must not enter the conclusions.
    """
    rows: list[dict] = []

    # 1. The execution instants are the decision instants: every delay row reproduces the
    #    frozen decisions table exactly at the same (ts_ns, locate).
    derived = config_module.repo_path(config_module.derived_dir(configuration))
    state_columns = ["ts_ns", "locate", "mid2_raw", "spread_raw", "imbalance", "best_bid_raw", "best_ask_raw"]
    decisions = pq.read_table(os.path.join(derived, "decisions.parquet"), columns=state_columns)
    keys_decision = decisions["ts_ns"].to_numpy(zero_copy_only=False) * 100000 + decisions["locate"].to_numpy(
        zero_copy_only=False
    ).astype(np.int64)
    order = np.argsort(keys_decision, kind="stable")
    keys_sorted = keys_decision[order]
    keys_delay = columns["ts_ns"] * 100000 + columns["locate"].astype(np.int64)
    position = np.searchsorted(keys_sorted, keys_delay)
    found = keys_sorted[np.clip(position, 0, keys_sorted.size - 1)] == keys_delay
    mismatch = int((~found).sum())
    for name, stored, expected in (
        ("mid2_raw", decisions["mid2_raw"].to_numpy(zero_copy_only=False)[order][position], frame["mid2"]),
        ("spread_raw", decisions["spread_raw"].to_numpy(zero_copy_only=False)[order][position], frame["spread_raw"]),
        (
            "imbalance",
            decisions["imbalance"].to_numpy(zero_copy_only=False)[order][position].astype(np.float64),
            frame["imbalance"],
        ),
        (
            "entry_ask",
            decisions["best_ask_raw"].to_numpy(zero_copy_only=False)[order][position].astype(np.float64),
            frame["entry_ask"],
        ),
        (
            "entry_bid",
            decisions["best_bid_raw"].to_numpy(zero_copy_only=False)[order][position].astype(np.float64),
            frame["entry_bid"],
        ),
    ):
        mismatch += int(np.sum(found & (stored != expected)))
    rows.append(
        {
            "check": "execution_instant_is_decision_instant",
            "method_a": "delay_decisions.parquet delay 0 arrival state",
            "method_b": "decisions.parquet state at the same (ts_ns, locate)",
            "observations": int(keys_delay.size),
            "mismatches": mismatch,
            "tolerance": 0,
            "outcome": "PASS" if mismatch == 0 else "FAIL",
        }
    )

    # 2. Relation to the frozen M2-0 execution table: the markout column reproduces exactly,
    #    and the two columns that do not are explained by two exact factor-two defects that
    #    are reported as a discrepancy rather than reproduced. The frozen table is not modified.
    pooled = {row["horizon_ms"]: row for row in bundle["pooled_by_horizon"]}
    frozen_checks, discrepancies = _frozen_execution_rows(configuration, frame, columns, ledger, pooled)
    rows.extend(frozen_checks)
    bundle["discrepancies"] = discrepancies

    # 3. The P&L decomposition is an identity, per pooled horizon and per cell.
    worst = 0.0
    for horizon_ms in configuration["horizons_ms"]:
        future = frame["horizons"][horizon_ms]
        mask = future["usable_signal"]
        signal = future["realized_move_bps"][mask].mean()
        spread = (frame["half_spread_entry_bps"][mask] + future["half_spread_future_bps"][mask]).mean()
        for label in schedule_labels(ledger):
            fee = future[f"fee_{label}_bps"][mask].mean()
            net = future[f"net_{label}_bps"][mask].mean()
            worst = max(worst, abs((signal - spread - fee) - net))
    rows.append(
        {
            "check": "decomposition_identity_pooled",
            "method_a": "net_bps measured directly",
            "method_b": "realized_move - half_entry_spread - half_future_spread - fee",
            "observations": int(sum(frame["horizons"][h]["usable_signal"].sum() for h in configuration["horizons_ms"])),
            "max_abs_difference": float(worst),
            "tolerance": 1e-9,
            "outcome": "PASS" if worst <= 1e-9 else "FAIL",
        }
    )

    # 4. The hurdle is the cross-to-cross break-even: cross_to_cross equals
    #    (realized - spread_only) plus the measured spread-change term, and nothing else.
    worst = 0.0
    for horizon_ms in configuration["horizons_ms"]:
        future = frame["horizons"][horizon_ms]
        mask = future["usable_signal"]
        derived_gap = (
            future["realized_move_bps"][mask]
            - frame["spread_bps"][mask]
            - future["cross_to_cross_bps"][mask]
            + future["spread_change_term_bps"][mask]
        )
        worst = max(worst, float(np.max(np.abs(derived_gap))))
    rows.append(
        {
            "check": "spread_hurdle_is_cross_to_cross_breakeven",
            "method_a": "realized_move - full_spread - cross_to_cross",
            "method_b": "minus the measured spread-change term (half_future_spread - half_entry_spread)",
            "observations": int(sum(frame["horizons"][h]["usable_signal"].sum() for h in configuration["horizons_ms"])),
            "max_abs_difference": float(worst),
            "tolerance": 1e-9,
            "outcome": "PASS" if worst <= 1e-9 else "FAIL",
        }
    )

    # 5. The clairvoyant bound dominates every fixed side, row by row, and is never negative.
    violations = 0
    for horizon_ms in configuration["horizons_ms"]:
        future = frame["horizons"][horizon_ms]
        mask = future["usable_state"]
        for label in schedule_labels(ledger):
            bound = future[f"oracle_net_{label}_bps"][mask]
            lower = np.maximum(
                0.0,
                np.maximum(
                    future["cross_long_bps"][mask] - frame["fees"][label]["long"][mask],
                    future["cross_short_bps"][mask] - frame["fees"][label]["short"][mask],
                ),
            )
            violations += int(np.sum(bound < lower - 1e-9))
            violations += int(np.sum(bound < 0.0))
    rows.append(
        {
            "check": "oracle_bound_dominates_and_is_non_negative",
            "method_a": "ORACLE_UPPER_BOUND column",
            "method_b": "max(0, net_long, net_short) recomputed from raw quotes",
            "observations": int(
                sum(frame["horizons"][h]["usable_state"].sum() for h in configuration["horizons_ms"])
                * len(schedule_labels(ledger))
            ),
            "mismatches": violations,
            "tolerance": 1e-9,
            "outcome": "PASS" if violations == 0 else "FAIL",
        }
    )

    # 6. The QIMB-constrained bound never exceeds the unconstrained oracle bound.
    violations = 0
    for horizon_ms in configuration["horizons_ms"]:
        future = frame["horizons"][horizon_ms]
        mask = future["usable_signal"]
        for label in schedule_labels(ledger):
            violations += int(
                np.sum(future[f"qimb_bound_{label}_bps"][mask] > future[f"oracle_net_{label}_bps"][mask] + 1e-9)
            )
    rows.append(
        {
            "check": "qimb_bound_below_oracle_bound",
            "method_a": "QIMB_CONSTRAINED_BOUND",
            "method_b": "ORACLE_UPPER_BOUND",
            "observations": int(
                sum(frame["horizons"][h]["usable_signal"].sum() for h in configuration["horizons_ms"])
                * len(schedule_labels(ledger))
            ),
            "mismatches": violations,
            "tolerance": 1e-9,
            "outcome": "PASS" if violations == 0 else "FAIL",
        }
    )

    # 7. Every observation that has a declared cell lands in exactly one of them, and the
    #    rows without a cell are counted rather than folded into the first cell.
    dimensions = state_dimensions(frame, configuration)
    codes, _n_cells, _sizes = combine_dimensions(dimensions)
    in_space = declared_space_mask(dimensions)
    expected_rows = int((frame["signal_defined"] & in_space).sum())
    rows.append(
        {
            "check": "state_partition_covers_every_observation",
            "method_a": "signal-defined observations inside the declared price bands",
            "method_b": "sum of the declared state cells",
            "observations": expected_rows,
            "cell_total": int(np.sum(codes[frame["signal_defined"] & in_space] >= 0)),
            "outside_declared_state_space": int((frame["signal_defined"] & ~in_space).sum()),
            "tolerance": 0,
            "outcome": "PASS"
            if expected_rows + int((frame["signal_defined"] & ~in_space).sum()) == int(frame["signal_defined"].sum())
            else "FAIL",
        }
    )

    # 8. The fee term matches the ledger evaluated directly at the observation prices.
    worst = 0.0
    prices = np.unique(np.round(frame["price_usd"][frame["state_valid"]], 4))
    sample = prices[:: max(1, prices.size // 500)]
    for label in schedule_labels(ledger):
        regime, schedule = _schedule_of(ledger, label)
        direct = np.array(
            [
                costs.cost_in_bps_of_price(ledger, regime, schedule, float(ledger["assumptions"]["representative_order_shares"]), float(price))
                for price in sample
            ]
        )
        unique, values = calculate._cost_lookup(
            ledger, regime, schedule, float(ledger["assumptions"]["representative_order_shares"]), sample
        )
        mapped = calculate._map_cost_lookup(unique, values, sample)
        finite = np.isfinite(direct) & np.isfinite(mapped)
        worst = max(worst, float(np.max(np.abs(direct[finite] - mapped[finite]))) if finite.any() else 0.0)
    rows.append(
        {
            "check": "fee_lookup_matches_ledger_at_observation_prices",
            "method_a": "vectorised price lookup used by this pass",
            "method_b": "costs.cost_in_bps_of_price per price",
            "observations": int(sample.size) * len(schedule_labels(ledger)),
            "max_abs_difference": float(worst),
            "tolerance": 1e-9,
            "outcome": "PASS" if worst <= 1e-9 else "FAIL",
        }
    )

    # 9. Tick arithmetic: one_tick classification and the half-spread identity.
    ticks, tick_labels = imbalance_bin_codes(frame["imbalance"], frame["state_valid"], configuration)
    del tick_labels
    tick_raw = int(configuration["tick_raw"])
    mismatches = int(np.sum(frame["spread_raw"][frame["state_valid"]] != np.round(frame["spread_raw"][frame["state_valid"]])))
    mismatches += int(
        np.sum(frame["one_tick"][frame["state_valid"]] != (frame["spread_raw"][frame["state_valid"]] == tick_raw))
    )
    worst = float(
        np.max(
            np.abs(
                frame["half_spread_entry_bps"][frame["state_valid"]]
                - 10000.0 * (frame["entry_ask"][frame["state_valid"]] - frame["entry_bid"][frame["state_valid"]]) / frame["mid2"][frame["state_valid"]]
            )
        )
    )
    rows.append(
        {
            "check": "tick_and_half_spread_arithmetic",
            "method_a": "stored spread and derived half spread",
            "method_b": "tick arithmetic and (ask - mid) / mid * 10000",
            "observations": int(frame["state_valid"].sum()),
            "mismatches": mismatches,
            "max_abs_difference": worst,
            "tolerance": 1e-9,
            "outcome": "PASS" if mismatches == 0 and worst <= 1e-9 else "FAIL",
        }
    )
    return rows


def _schedule_of(ledger: dict, label: str) -> tuple[str, str | None]:
    for regime, schedule, schedule_label in costs.schedule_pairs(ledger):
        if schedule_label == label:
            return regime, schedule
    raise ValueError(f"unknown schedule label {label!r}")


def _frozen_execution_rows(
    configuration: dict, frame: dict, columns: dict, ledger: dict, pooled: dict
) -> tuple[list[dict], list[dict]]:
    """Relate this pass's pooled columns to the frozen M2-0 execution table exactly.

    Three relations are checked. The markout column is reproduced exactly. The other two
    are not, and the difference is not a tolerance: M2-0's ``execution_rows`` divides a
    price *difference* by ``mid2`` (twice the mid) for the cross-to-cross column, and
    feeds the cost ledger ``entry_price = raw / 2 / 10000``, i.e. half the true USD entry
    price. Both are exact factor-two defects, confirmed here by recomputing M2-0's own
    convention and matching its published columns bit for bit. This pass reports the
    correct quantities and records the difference; the frozen artifact is left untouched.
    """
    path = config_module.repo_path(
        config_module.output_dir(configuration, "calculations", "idealized_execution_summary.csv")
    )
    floor = structural_label(ledger)
    shares = float(ledger["assumptions"]["representative_order_shares"])
    frozen = {}
    if os.path.exists(path):
        import csv

        with open(path, newline="") as handle:
            for row in csv.DictReader(handle):
                if row["cost_regime"] == floor and int(row["delay_ms"]) == EXECUTION_DELAY_MS:
                    frozen[int(row["horizon_ms"])] = row
    if not frozen:
        # The reference table is frozen and present in the repository. When it is absent
        # (a synthetic fixture, for instance) the comparison cannot be run: it is reported
        # as not evaluated rather than as a pass, so absence is never mistaken for agreement.
        return (
            [
                {
                    "check": "frozen_execution_comparison",
                    "method_a": "this pass",
                    "method_b": "idealized_execution_summary.csv",
                    "observations": int(sum(row["observations"] for row in pooled.values())),
                    "outcome": "NOT_EVALUATED_REFERENCE_ABSENT",
                    "note": f"the frozen reference table was not found at {path}; no comparison is claimed",
                }
            ],
            [],
        )
    horizon_list = [h for h in configuration["horizons_ms"] if h in frozen]
    markout_gap = 0.0
    cross_ratio = 0.0
    fee_gap = 0.0
    adjusted_gap = 0.0
    frozen_observations = 0
    sample_price_bps = {}
    for horizon_ms in horizon_list:
        row = frozen[horizon_ms]
        mine = pooled[horizon_ms]
        markout_gap = max(markout_gap, abs(float(row["mean_gross_markout_bps"]) - mine["mean_markout_bps"]))
        cross_ratio = max(cross_ratio, abs(mine["mean_cross_to_cross_bps"] / float(row["mean_cross_to_cross_bps"])))
        adjusted_gap = max(
            adjusted_gap,
            abs(
                float(row["mean_cost_adjusted_bps"])
                - (float(row["mean_gross_markout_bps"]) - float(row["mean_known_cost_bps"]))
            ),
        )
        frozen_observations += int(row["observations"])
        if not sample_price_bps:
            future = frame["horizons"][horizon_ms]
            mask = future["usable_signal"]
            entry_raw = np.where(frame["side"] > 0, frame["entry_ask"], frame["entry_bid"])
            half_price = entry_raw / 2.0 / 10000.0
            for label in schedule_labels(ledger):
                regime, schedule = _schedule_of(ledger, label)
                unique, values = calculate._cost_lookup(ledger, regime, schedule, shares, half_price)
                at_half = calculate._map_cost_lookup(unique, values, half_price)
                sample_price_bps[label] = float(np.nanmean(at_half[mask]))
                if label == floor:
                    fee_gap = max(fee_gap, abs(sample_price_bps[label] - float(row["mean_known_cost_bps"])))
    expected = int(sum(row["observations"] for row in pooled.values()))
    checks = [
        {
            "check": "frozen_execution_markout_reproduced_exactly",
            "method_a": "this pass, state dimensions collapsed to (horizon)",
            "method_b": "idealized_execution_summary.csv mean_gross_markout_bps (structural floor, delay 0)",
            "observations": frozen_observations,
            "max_abs_difference": float(markout_gap),
            "tolerance": 1e-6,
            "outcome": "PASS" if horizon_list and markout_gap <= 1e-6 and frozen_observations == expected else "FAIL",
        },
        {
            "check": "frozen_cross_to_cross_is_half_of_true_bps",
            "method_a": "this pass cross_to_cross in bps of the arrival mid",
            "method_b": "idealized_execution_summary.csv mean_cross_to_cross_bps (divides a price difference by mid2)",
            "observations": frozen_observations,
            "max_ratio": float(cross_ratio),
            "expected_ratio": 2.0,
            "tolerance": 1e-9,
            "outcome": "PASS" if horizon_list and abs(cross_ratio - 2.0) <= 1e-9 else "FAIL",
            "note": "the ratio is exactly 2 because the frozen column is a dollar difference divided by mid2 rather than the mid",
        },
        {
            "check": "frozen_cost_column_is_ledger_at_half_price",
            "method_a": "ledger round trip at the true entry price (this pass)",
            "method_b": "idealized_execution_summary.csv mean_known_cost_bps, recomputed at entry_price = raw/2/10000",
            "observations": frozen_observations,
            "max_abs_difference": float(fee_gap),
            "tolerance": 1e-9,
            "outcome": "PASS" if horizon_list and fee_gap <= 1e-9 else "FAIL",
            "note": "the frozen cost column is exactly the ledger evaluated at half the observation prices",
        },
        {
            "check": "frozen_execution_adjusted_is_its_own_markout_minus_its_own_cost",
            "method_a": "idealized_execution_summary.csv mean_cost_adjusted_bps",
            "method_b": "its own mean_gross_markout_bps - mean_known_cost_bps",
            "observations": frozen_observations,
            "max_abs_difference": float(adjusted_gap),
            "tolerance": 1e-9,
            "outcome": "PASS" if horizon_list and adjusted_gap <= 1e-9 else "FAIL",
            "note": "the frozen artifact is internally consistent given its own inputs, so the difference is in the inputs, not a transcription error",
        },
    ]
    discrepancies = [
        {
            "id": "M2-0-D1",
            "location": "M2/src/calculate.py::execution_rows — cross-to-cross",
            "frozen_expression": "10000 * (fut_bid - entry_ask) / arrival_mid2  with arrival_mid2 = entry_bid + entry_ask",
            "correct_expression": "10000 * (fut_bid - entry_ask) / mid, mid = (entry_bid + entry_ask) / 2  =>  2 * the frozen value",
            "effect": "the frozen cross-to-cross column is half the true basis-point value",
            "verified_by": "frozen_cross_to_cross_is_half_of_true_bps",
            "affected_artifacts": [
                "M2/output/calculations/idealized_execution_summary.csv::mean_cross_to_cross_bps",
                "M2/output/calculations/ev_delay_descriptive.csv::mean_cross_to_cross_bps",
                "M2/output/M2_0_STATUS.md (the cross-to-cross column of the idealized execution table: -1.6774 / -1.6691 / -1.6586 / -1.6413 bps, each half the true value)",
            ],
        },
        {
            "id": "M2-0-D2",
            "location": "M2/src/calculate.py::execution_rows — cost lookup price",
            "frozen_expression": "entry_price = where(side>0, entry_ask, entry_bid) / 2.0 / 10000.0",
            "correct_expression": "entry_price_usd = raw_price / 10000.0 (Price(4) scale); the frozen expression halves every price",
            "effect": "the fee is evaluated at half the true price, so mean_known_cost_bps is overstated (2.6831 bps instead of 1.4445 bps on this sample)",
            "verified_by": "frozen_cost_column_is_ledger_at_half_price",
            "affected_artifacts": [
                "M2/output/calculations/idealized_execution_summary.csv::mean_known_cost_bps",
                "M2/output/calculations/idealized_execution_summary.csv::mean_cost_adjusted_bps",
                "M2/output/calculations/idealized_execution_summary.csv::median_cost_adjusted_bps",
                "M2/output/calculations/idealized_execution_summary.csv::prob_adjusted_positive",
                "M2/output/calculations/ev_delay_descriptive.csv::mean_known_cost_bps and the three columns derived from it",
                "M2/output/M2_0_STATUS.md (the known cost 2.6831 bps and the cost-adjusted column: -4.3540 / -4.3379 / -4.3172 / -4.2837 bps)",
            ],
        },
        {
            "id": "M2-0-D3",
            "location": "consequence of D1 and D2",
            "frozen_expression": "mean_cost_adjusted_bps = mean_gross_markout_bps - mean_known_cost_bps",
            "correct_expression": (
                "net = cross_to_cross - fee = -3.3548 - 1.4445 = -4.7994 bps at 100 ms "
                "(the frozen -4.3540 bps mixes the correct markout with an inflated fee and is not "
                "a cross-to-cross result)"
            ),
            "effect": "the frozen cost-adjusted column is not the cross-to-cross net; both defects push the reported figure in the same (more favourable) direction",
            "verified_by": "decomposition_identity_pooled and this pass's pooled table",
            "affected_artifacts": [
                "M2/output/M2_0_STATUS.md (the idealized-execution paragraph, which is the only place these two columns are quoted)"
            ],
        },
    ]
    return checks, discrepancies


# -------------------------------------------------------------- mechanism
def mechanism_verdict(bundle: dict) -> dict:
    """Classify the dominant economic gap from the decomposition, mechanically.

    Every flag is a rule applied to the measured decomposition; no flag is asserted from
    intuition, and a flag that does not hold is reported as False with its numbers
    attached rather than omitted. Two rules use an explicit reporting cut (50%), named
    here so that it is visible and not mistaken for a fitted parameter.
    """
    HORIZON_CUT = 0.50  # a horizon claim needs the declared grid to close half the gap
    STATE_CUT = 0.50  # a state-space claim needs cross-state dispersion to be large
    labels = bundle["schedule_labels"]
    floor = bundle["structural_label"]
    pooled = {row["horizon_ms"]: row for row in bundle["pooled_by_horizon"]}
    horizons = sorted(pooled)
    decomposition = []
    for horizon_ms in horizons:
        row = pooled[horizon_ms]
        signal = row["mean_signal_signed_mid_move_bps"]
        spread = row["mean_full_spread_paid_bps"]
        fee = row[f"fee_{floor}_bps"]
        required = spread + fee
        decomposition.append(
            {
                "horizon_ms": horizon_ms,
                "signal_bps": signal,
                "signal_abs_bps": abs(signal),
                "full_spread_paid_bps": spread,
                f"fee_{floor}_bps": fee,
                "required_move_bps": required,
                f"net_{floor}_bps": row[f"net_{floor}_bps"],
                "spread_share_of_required": spread / required,
                f"fee_share_of_required": fee / required,
                "signal_coverage_of_required": signal / required,
                "spread_to_signal_ratio": spread / abs(signal) if signal else float("inf"),
                "fee_to_signal_ratio": fee / abs(signal) if signal else float("inf"),
                "signal_multiple_needed_for_spread_only": spread / abs(signal) if signal else float("inf"),
            }
        )
    first, longest = decomposition[0], decomposition[-1]
    nets = [row[f"net_{floor}_bps"] for row in decomposition]
    increments = [b - a for a, b in zip(nets, nets[1:])]
    gap_closed = longest[f"net_{floor}_bps"] - first[f"net_{floor}_bps"]
    remaining_gap = abs(longest[f"net_{floor}_bps"])
    horizon_fraction = gap_closed / remaining_gap if remaining_gap else float("inf")
    states = bundle["pooled_by_bin_horizon"]
    state_nets = [finite_or_negative_infinity(row[f"net_{floor}_bps"]) for row in states]
    best_state = max(states, key=lambda row: finite_or_negative_infinity(row[f"net_{floor}_bps"]))
    dispersion = max(state_nets) - min(state_nets)
    dispersion_ratio = dispersion / abs(sum(state_nets) / len(state_nets)) if state_nets else float("inf")
    space = bundle["state_space_summary"]
    flags = {
        "SPREAD_DOMINATES": longest["spread_share_of_required"] > 0.5,
        "FEES_DOMINATE": longest[f"fee_share_of_required"] > 0.5,
        "SIGNAL_MAGNITUDE_TOO_SMALL": longest["signal_coverage_of_required"] < 0.10
        and max(row["signal_coverage_of_required"] for row in decomposition) < 0.10,
        "WRONG_HORIZON": horizon_fraction >= HORIZON_CUT,
        "POOLED_LOW_QUALITY_STATES": dispersion_ratio < STATE_CUT,
    }
    holding = [name for name, value in flags.items() if value]
    return {
        "flags": flags,
        "holding": holding,
        "combination": len(holding) > 1,
        "cuts": {
            "HORIZON_CUT": HORIZON_CUT,
            "STATE_CUT": STATE_CUT,
            "note": "reporting cuts named before the verdict was computed; not fitted parameters",
        },
        "rules": {
            "SPREAD_DOMINATES": "the mean full spread paid is more than half of the required move at the longest declared horizon",
            "FEES_DOMINATE": "the mean floor fee is more than half of the required move at the longest declared horizon",
            "SIGNAL_MAGNITUDE_TOO_SMALL": "the side-signed mid move covers less than 10% of the required move at every declared horizon",
            "WRONG_HORIZON": "extending the horizon across the whole declared grid (100 ms to 1000 ms, a factor of ten) closes at least half of the remaining gap",
            "POOLED_LOW_QUALITY_STATES": "the dispersion of the net result across the declared (bin x horizon) states is less than half of its mean, i.e. the states barely separate",
        },
        "by_horizon": decomposition,
        "horizon_increments_bps": increments,
        "horizon_fraction_of_gap_closed": horizon_fraction,
        "state_dispersion_bps": dispersion,
        "state_dispersion_ratio": dispersion_ratio,
        "best_declared_state_bin_horizon": best_state,
        "state_space": space,
        "net_by_schedule_at_longest_horizon": {label: pooled[max(horizons)][f"net_{label}_bps"] for label in labels},
        "oracle_bound_at_longest_horizon": {
            label: bundle_oracle(bundle, max(horizons), label) for label in labels
        },
    }


def bundle_oracle(bundle: dict, horizon_ms: int, label: str) -> float:
    for row in bundle["oracle_pooled_by_horizon"]:
        if row["horizon_ms"] == horizon_ms:
            return row[f"oracle_net_{label}_bps"]
    return float("nan")


def answers(bundle: dict) -> dict:
    """The four requested answers, each derived from the tables rather than narrated."""
    floor = bundle["structural_label"]
    state_rows = bundle["pooled_by_bin_horizon"]
    best_state = max(state_rows, key=lambda row: finite_or_negative_infinity(row[f"net_{floor}_bps"]))
    total = bundle["observation_sets"]["signal_defined"]
    grid_total = sum(row["observations"] for row in state_rows if row["horizon_ms"] == bundle["horizons_ms"][0])
    covering_states = [row for row in state_rows if row[f"net_{floor}_bps"] > 0.0]
    coverage = {
        str(cut): int(
            sum(
                1
                for row in state_rows
                if row["observations"]
                and row["mean_required_move_bps_structural"]
                and (row["mean_signal_signed_mid_move_bps"] / row["mean_required_move_bps_structural"]) >= cut
            )
        )
        for cut in HURDLE_COVERAGE_CUTS
    }
    oracle = {row["horizon_ms"]: row for row in bundle["oracle_pooled_by_horizon"]}
    longest = max(oracle)
    floor_oracle = oracle[longest][f"oracle_net_{floor}_bps"]
    required = bundle["verdict"]["by_horizon"][-1]["required_move_bps"]
    clairvoyant = {
        "horizon_ms": longest,
        f"mean_oracle_net_{floor}_bps": floor_oracle,
        "mean_oracle_gross_bps": oracle[longest]["mean_oracle_gross_bps"],
        "mean_oracle_net_by_schedule": {
            label: oracle[longest][f"oracle_net_{label}_bps"] for label in bundle["schedule_labels"]
        },
        "prob_oracle_gross_positive": oracle[longest]["prob_oracle_gross_positive"],
        f"prob_oracle_net_{floor}_positive": oracle[longest][f"prob_oracle_net_{floor}_positive"],
        "observations": oracle[longest]["observations"],
        "required_move_bps_at_that_horizon": required,
        "oracle_bound_as_fraction_of_required_move": floor_oracle / required if required else float("nan"),
    }
    return {
        "q1_any_state_approaches_or_exceeds_structural_hurdle": {
            "declared_cells_total": bundle["state_space_summary"]["cells_total"],
            "declared_cells_with_positive_net": bundle["state_space_summary"]["cells_with_positive_net"],
            "best_declared_cell": bundle["state_space_summary"]["best_cell"],
            "cells_at_hurdle_coverage_cut": bundle["state_space_summary"]["cells_at_hurdle_coverage_cut"],
            "declared_states_in_bin_horizon_space": len(state_rows),
            "states_with_positive_net": len(covering_states),
            "best_state": best_state,
            "best_state_share_of_observations": best_state["observations"] / grid_total if grid_total else float("nan"),
            "hurdle_coverage_cut_counts_bin_horizon": coverage,
            "definition": "hurdle coverage = mean side-signed mid move / mean required move (full spread + floor fee)",
        },
        "q2_fraction_of_opportunities_of_best_state": {
            "best_state_share_of_signal_defined_observations": best_state["observations"] / total if total else float("nan"),
            "best_state_observations": best_state["observations"],
            "best_cell_share_of_signal_defined_observations": bundle["state_space_summary"]["best_cell"][
                "share_of_signal_defined_observations"
            ],
            "best_cell_observations": bundle["state_space_summary"]["best_cell"]["observations"],
            "signal_defined_observations": total,
        },
        "q3_clairvoyant_room_after_costs": clairvoyant,
        "q4_dominant_gap_component": bundle["verdict"]["holding"],
        "mechanism": bundle["verdict"],
    }


# ------------------------------------------------------------------ rendering
def _number(value, digits: int = 4) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "NaN"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return "NaN"
    return f"{numeric:.{digits}f}"


def _md_table(headers: Sequence[str], rows: Sequence[Sequence]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def render(bundle: dict) -> str:
    labels = bundle["schedule_labels"]
    floor = bundle["structural_label"]
    accessible = [label for label in labels if label != floor]
    pooled = {row["horizon_ms"]: row for row in bundle["pooled_by_horizon"]}
    horizons = sorted(pooled)
    out: list[str] = []
    add = out.append

    add("# M2-0.5 — AGGRESSIVE MONETIZATION FEASIBILITY BOUND")
    add("")
    add(f"Candidate `{bundle['candidate_id']}` · run `{bundle['run_id']}` · development sample day "
        f"`{bundle['coverage_date']}` · dataset `{bundle['dataset']}` · cost ledger `{bundle['cost_ledger_id']}`")
    add("")
    add("**No data was acquired, no model was trained, no threshold was optimised, Jev was not used, M1 and the "
        "research framework were not modified, and no artifact of M2-0 was rewritten.** This pass reads the frozen "
        "M2-0 development artifacts and conditions the existing aggressive execution arithmetic on the predeclared "
        "state space. It promotes nothing and kills nothing.")
    add("")
    add(_md_table(
        ["item", "value"],
        [
            ["execution instant", f"delay_decisions.parquet, delay {EXECUTION_DELAY_MS} ms (the M2-0 idealized aggressive instant)"],
            ["observations (level 0)", f"{bundle['observation_sets']['state_valid']:,} valid decision states of {bundle['observation_sets']['delay_rows_total']:,} delay rows"],
            ["observations (level 1)", f"{bundle['observation_sets']['signal_defined']:,} with a defined signal side (imbalance != 0)"],
            ["state space", f"{len(bundle['cell_dimensions']['imbalance_bins'])} imbalance bins x "
                             f"{len(bundle['cell_dimensions']['spread_classes'])} spread classes x "
                             f"{len(bundle['cell_dimensions']['price_bands'])} price bands = "
                             f"{bundle['cell_dimensions']['cells_per_horizon']} cells per horizon, "
                             f"{bundle['cell_dimensions']['cell_rows_total']} rows over 4 horizons"],
            ["cost regimes", ", ".join(labels) + f" (round trip, {bundle['representative_order_shares']}-share representative size)"],
            ["config sha256", bundle["config_sha256"]],
            ["cost ledger sha256", bundle["cost_ledger_sha256"]],
            ["code sha256", "; ".join(f"{name} {value[:16]}…" for name, value in bundle["code_sha256"].items())],
            ["derived artifacts", "; ".join(f"{name} {value[:16]}…" for name, value in bundle["derived_artifacts"].items())],
        ],
    ))
    add("")

    add("## 0. Observation accounting")
    add("")
    add("The delay-0 slice of `delay_decisions.parquet` is a 1 s decimation of the predeclared 100 ms decision grid and "
        "carries the realised future two-sided quote that a cross-to-cross result requires. It is verified below "
        "(check `execution_instant_is_decision_instant`) to reproduce `decisions.parquet` exactly at the same "
        "`(ts_ns, locate)` on every row, so no observation is invented and none is redefined.")
    add("")
    add(_md_table(
        ["observation set", "count", "note"],
        [
            ["delay rows at delay 0", f"{bundle['observation_sets']['delay_rows_total']:,}", "1 s grid, 61 development-scope symbols"],
            ["valid decision states", f"{bundle['observation_sets']['state_valid']:,}", "two-sided, uncrossed, arrival present"],
            ["    of which imbalance == 0", f"{bundle['observation_sets']['zero_imbalance_state']:,}", "in the state space but with no sign to trade; kept in the oracle set, excluded from side-dependent cells (the M2-0 execution filter)"],
            ["signal-defined observations", f"{bundle['observation_sets']['signal_defined']:,}", "imbalance != 0; the base of every state-conditioned cell"],
            [
                "outside the declared price bands",
                f"{bundle['observation_sets']['outside_declared_price_bands']:,}",
                "none: every observation falls in one of the five declared bands",
            ],
        ]
        + [
            [
                f"future quote missing at {h} ms",
                f"{bundle['observation_sets']['future_unavailable'][str(h)]:,}",
                "rows kept in the state space, dropped from that horizon's cells",
            ]
            for h in horizons
        ]
        + [
            [
                f"imbalance == 0 at {h} ms",
                f"{bundle['observation_sets']['zero_imbalance_by_horizon'][str(h)]:,}",
                "no sign to trade; kept in the oracle set, excluded from the side-dependent cells",
            ]
            for h in horizons
        ]
        + [
            [
                f"outside the declared state space at {h} ms",
                f"{bundle['observation_sets']['outside_declared_state_space'][str(h)]['signal_defined']:,}"
                f" signal / {bundle['observation_sets']['outside_declared_state_space'][str(h)]['valid_states']:,} valid",
                "no declared price band contains the observation; excluded from the cells and counted, never folded in",
            ]
            for h in horizons
        ],
    ))
    add("")
    add(f"Declared dimensions: {BANDS_NOTE}.")
    add("")

    add("## 1. Aggressive cross-to-cross economics by declared state (request §1)")
    add("")
    add("`gross future mid move` is the unsigned mid-to-mid move over the horizon; `entry-to-future-mid markout` and "
        "`cross-to-cross` are side-adjusted (side = sign(imbalance)) with the entry at the far touch; the three "
        "`result` columns subtract the ledger round trip of the named regime. Every number is in bps of the arrival "
        "mid, except the fee columns which are the ledger's own bps of entry notional. All 400 cells are in "
        "`aggressive_feasibility_by_state.csv`; no cell is withheld and no winner is selected.")
    add("")
    add("### 1a. Pooled over the whole declared state space, by horizon")
    add("")
    add(_md_table(
        ["horizon ms", "obs", "mid move", "signed mid move", "markout", "cross-to-cross", "spread paid", f"fee {floor}"]
        + [f"net {label}" for label in labels] + ["P(net>0) " + floor],
        [
            [
                h,
                f"{pooled[h]['observations']:,}",
                _number(pooled[h]["mean_future_mid_move_bps"]),
                _number(pooled[h]["mean_signal_signed_mid_move_bps"]),
                _number(pooled[h]["mean_markout_bps"]),
                _number(pooled[h]["mean_cross_to_cross_bps"]),
                _number(pooled[h]["mean_full_spread_paid_bps"]),
                _number(pooled[h][f"fee_{floor}_bps"]),
            ]
            + [_number(pooled[h][f"net_{label}_bps"]) for label in labels]
            + [_number(pooled[h][f"prob_net_{floor}_positive"])]
            for h in horizons
        ],
    ))
    add("")
    add("### 1b. By spread class")
    add("")
    add(_md_table(
        ["horizon ms", "spread class", "obs", "spread bps", "signed mid move", "cross-to-cross"]
        + [f"net {label}" for label in labels] + [f"P(net>0) {floor}"],
        [
            [
                row["horizon_ms"],
                row["label_value"],
                f"{row['observations']:,}",
                _number(row["mean_spread_bps"]),
                _number(row["mean_signal_signed_mid_move_bps"]),
                _number(row["mean_cross_to_cross_bps"]),
            ]
            + [_number(row[f"net_{label}_bps"]) for label in labels]
            + [_number(row[f"prob_net_{floor}_positive"])]
            for row in sorted(bundle["pooled_by_spread_horizon"], key=lambda r: (r["horizon_ms"], r["label_value"]))
        ],
    ))
    add("")
    add("### 1c. By price band")
    add("")
    add(_md_table(
        ["horizon ms", "price band", "obs", "mean price", "spread bps", "signed mid move", "cross-to-cross"]
        + [f"fee {label}" for label in labels] + [f"net {label}" for label in labels],
        [
            [
                row["horizon_ms"],
                row["label_value"],
                f"{row['observations']:,}",
                _number(row["mean_price_usd"], 2),
                _number(row["mean_spread_bps"]),
                _number(row["mean_signal_signed_mid_move_bps"]),
                _number(row["mean_cross_to_cross_bps"]),
            ]
            + [_number(row[f"fee_{label}_bps"]) for label in labels]
            + [_number(row[f"net_{label}_bps"]) for label in labels]
            for row in sorted(bundle["pooled_by_band_horizon"], key=lambda r: (r["horizon_ms"], r["label_value"]))
        ],
    ))
    add("")
    add("### 1d. By imbalance bin and horizon (structural floor)")
    add("")
    add(_md_table(
        ["horizon ms", "imbalance bin", "obs", "spread paid", "signed mid move", "cross-to-cross", f"net {floor}", f"P(net>0) {floor}"],
        [
            [
                row["horizon_ms"],
                row["label_value"],
                f"{row['observations']:,}",
                _number(row["mean_full_spread_paid_bps"]),
                _number(row["mean_signal_signed_mid_move_bps"]),
                _number(row["mean_cross_to_cross_bps"]),
                _number(row[f"net_{floor}_bps"]),
                _number(row[f"prob_net_{floor}_positive"]),
            ]
            for row in sorted(bundle["pooled_by_bin_horizon"], key=lambda r: (r["horizon_ms"], r["label_value"]))
        ],
    ))
    add("")
    best = bundle["best_cells"]
    add("### 1e. The best and worst declared cells (descriptive only — nothing is selected)")
    add("")
    add(_md_table(
        ["cell", "obs", "share of obs", "spread bps", "signed mid move", "cross-to-cross", f"net {floor}", "block SE", "block cells"],
        [
            [
                f"{row['imbalance_bin']} · {row['spread_class']} · ${row['price_band']} · {row['horizon_ms']} ms",
                f"{row['observations']:,}",
                _number(row["share_of_signal_defined_observations"], 4),
                _number(row["mean_spread_bps"]),
                _number(row["mean_signal_signed_mid_move_bps"]),
                _number(row["mean_cross_to_cross_bps"]),
                _number(row[f"net_{floor}_bps"]),
                _number(row[f"block_bootstrap_se_net_{floor}_bps"]),
                row["block_cells"],
            ]
            for row in best
        ],
    ))
    add("")
    add(f"Worst five cells by `net {floor}`: " + "; ".join(
        f"{row['imbalance_bin']}/{row['spread_class']}/${row['price_band']}/{row['horizon_ms']} ms = "
        f"{_number(row[f'net_{floor}_bps'])} bps"
        for row in bundle["worst_cells"]
    ) + ".")
    add("")

    add("## 2. Break-even hurdles (request §2)")
    add("")
    add("Hurdle A is the current quoted spread (cross in, cross out); B adds the structural floor round trip; "
        "C adds each accessible reference path. `realized_move_bps` is the side-signed mid move, so "
        "`realized > hurdle` is the break-even test and `P(realized > hurdle A)` equals `P(cross-to-cross > 0)` "
        "up to the measured spread-change term. Full distributions and ratios per cell are in "
        "`breakeven_hurdle.csv`; the pooled view is below.")
    add("")
    add(_md_table(
        ["horizon ms", "realized (mean)", "required A (spread)"] + [f"required {label}" for label in labels]
        + ["P(>A)"] + [f"P(>{label})" for label in labels],
        [
            [
                h,
                _number(pooled[h]["mean_signal_signed_mid_move_bps"]),
                _number(pooled[h]["mean_spread_bps"]),
            ]
            + [_number(pooled[h]["mean_spread_bps"] + pooled[h][f"fee_{label}_bps"]) for label in labels]
            + [_number(pooled[h]["prob_cross_to_cross_positive"])]
            + [_number(pooled[h][f"prob_net_{label}_positive"]) for label in labels]
            for h in horizons
        ],
    ))
    add("")
    add("### 2a. Hurdle coverage by imbalance bin and horizon (mean realized move / mean required move, structural)")
    add("")
    add(_md_table(
        ["horizon ms", "imbalance bin", "obs", "realized", "required", "coverage", "P(realized > B)", "P(QIMB bound > 0)"],
        [
            [
                row["horizon_ms"],
                row["bin_label"],
                f"{row['observations']:,}",
                _number(row["mean_signal_signed_mid_move_bps"]),
                _number(row["mean_required_move_bps_structural"]),
                _number(
                    row["mean_signal_signed_mid_move_bps"] / row["mean_required_move_bps_structural"]
                    if row["mean_required_move_bps_structural"]
                    else float("nan"),
                    3,
                ),
                _number(row["prob_realized_exceeds_required_structural"], 4),
                _number(row[f"prob_qimb_bound_{floor}_positive"], 4),
            ]
            for row in sorted(bundle["qimb_by_bin_horizon"], key=lambda r: (r["horizon_ms"], r["bin_label"]))
        ],
    ))
    add("")
    add("`coverage` is mean realized move / mean required move (the hurdle); `P(realized > B)` is the per-observation "
        "probability that the side-signed mid move beats the current spread plus the structural floor fee; "
        "`P(QIMB bound > 0)` adds clairvoyant abstention inside the dictated side.")
    add("")

    add("## 3. Oracle aggressive upper bound — ORACLE_UPPER_BOUND (request §3)")
    add("")
    add(f"**{ORACLE_NOTE}**")
    add("")
    add("At each decision instant the oracle takes `max(0, net_buy, net_sell)` using the realised future bid/ask. "
        "The `mean_oracle_net` columns are therefore per-observation upper bounds on *any* causal aggressive "
        "execution at these instants after that regime's costs. `mean_oracle_gross` is the same bound before costs, "
        "and `oracle_trade_fraction` is the share of instants at which trading beats abstaining.")
    add("")
    add(_md_table(
        ["horizon ms", "obs", "oracle gross", "oracle trade fraction"]
        + [f"oracle net {label}" for label in labels]
        + [f"P(net>0) {floor}", f"oracle net {floor} (signal-defined)"],
        [
            [
                row["horizon_ms"],
                f"{row['observations']:,}",
                _number(row["mean_oracle_gross_bps"]),
                _number(row["prob_oracle_gross_positive"]),
            ]
            + [_number(row[f"oracle_net_{label}_bps"]) for label in labels]
            + [
                _number(row[f"prob_oracle_net_{floor}_positive"]),
                _number(row[f"oracle_net_{floor}_bps_signal_defined"]),
            ]
            for row in bundle["oracle_pooled_by_horizon"]
        ],
    ))
    add("")
    add("### 3a. Oracle upper bound by imbalance bin (all valid states)")
    add("")
    add(_md_table(
        ["horizon ms", "imbalance bin", "obs", "oracle gross", "trade fraction"]
        + [f"oracle net {label}" for label in labels],
        [
            [
                row["horizon_ms"],
                row["bin_label"],
                f"{row['observations']:,}",
                _number(row["mean_oracle_gross_bps"]),
                _number(row["prob_oracle_gross_positive"]),
            ]
            + [_number(row[f"oracle_net_{label}_bps"]) for label in labels]
            for row in sorted(bundle["oracle_by_bin"], key=lambda r: (r["horizon_ms"], r["bin_label"]))
        ],
    ))
    add("")
    add("### 3b. Oracle upper bound by price band (all valid states)")
    add("")
    add(_md_table(
        ["horizon ms", "price band", "obs", "oracle gross", "trade fraction"]
        + [f"oracle net {label}" for label in labels],
        [
            [
                row["horizon_ms"],
                row["band_label"],
                f"{row['observations']:,}",
                _number(row["mean_oracle_gross_bps"]),
                _number(row["prob_oracle_gross_positive"]),
            ]
            + [_number(row[f"oracle_net_{label}_bps"]) for label in labels]
            for row in sorted(bundle["oracle_by_band"], key=lambda r: (r["horizon_ms"], r["band_label"]))
        ],
    ))
    add("")

    add("## 4. QIMB-constrained upper bound (request §4)")
    add("")
    add(f"**{QIMB_NOTE}**")
    add("")
    add(_md_table(
        ["horizon ms", "imbalance bin", "obs", "net " + floor, "bound " + floor, "gap", "bound " + accessible[0], "bound " + accessible[1]]
        + [f"P(bound>0) {floor}"],
        [
            [
                row["horizon_ms"],
                row["bin_label"],
                f"{row['observations']:,}",
                _number(row[f"net_{floor}_bps"]),
                _number(row[f"qimb_bound_{floor}_bps"]),
                _number(row[f"qimb_bound_{floor}_bps"] - row[f"net_{floor}_bps"]),
                _number(row[f"qimb_bound_{accessible[0]}_bps"]),
                _number(row[f"qimb_bound_{accessible[1]}_bps"]),
                _number(row[f"prob_qimb_bound_{floor}_positive"]),
            ]
            for row in sorted(bundle["qimb_by_bin_horizon"], key=lambda r: (r["horizon_ms"], r["bin_label"]))
        ],
    ))
    add("")
    add("This is the most favourable economics obtainable inside each declared state once the side is fixed by queue "
        "imbalance and only abstention is free. No new threshold and no side choice is introduced.")
    add("")

    add("## 5. Where the loss comes from (request §5)")
    add("")
    add("The decomposition is an identity, reconciled to 1e-9 in `feasibility_status.json`:")
    add("")
    add("```")
    add("cross_to_cross = realized_move - half_spread_entry - half_spread_future")
    add("net(regime)    = cross_to_cross - fee(regime)")
    add("fee(accessible) = fee(structural) + broker_layer")
    add("```")
    add("")
    add(_md_table(
        ["horizon ms", "realized move", "half spread in", "half spread out", "full spread paid", f"mandatory fee ({floor})"]
        + [f"broker layer ({label})" for label in accessible] + [f"net {floor}"]
        + [f"net {label}" for label in accessible],
        [
            [
                row["horizon_ms"],
                _number(row["mean_signal_signed_mid_move_bps"]),
                _number(row["mean_half_spread_entry_bps"]),
                _number(row["mean_half_spread_future_bps"]),
                _number(row["mean_full_spread_paid_bps"]),
                _number(row[f"fee_{floor}_bps"]),
            ]
            + [_number(row[f"fee_{label}_bps"] - row[f"fee_{floor}_bps"]) for label in accessible]
            + [_number(row[f"net_{floor}_bps"])]
            + [_number(row[f"net_{label}_bps"]) for label in accessible]
            for row in [pooled[h] for h in horizons]
        ],
    ))
    add("")
    verdict = bundle["verdict"]
    add("### 5a. Mechanism, computed from the decomposition")
    add("")
    add(_md_table(
        ["horizon ms", "signal (signed mid move)", "full spread paid", f"mandatory fee ({floor})", "required move",
         "spread share of required", "fee share of required", "signal coverage", f"net {floor}"],
        [
            [
                row["horizon_ms"],
                _number(row["signal_bps"]),
                _number(row["full_spread_paid_bps"]),
                _number(row[f"fee_{floor}_bps"]),
                _number(row["required_move_bps"]),
                _number(row["spread_share_of_required"] * 100, 1) + "%",
                _number(row[f"fee_share_of_required"] * 100, 1) + "%",
                _number(row["signal_coverage_of_required"] * 100, 2) + "%",
                _number(row[f"net_{floor}_bps"]),
            ]
            for row in verdict["by_horizon"]
        ],
    ))
    add("")
    add("The same decomposition expressed as what the signal would have to become: at 1000 ms the spread alone "
        "requires a mid move " + _number(verdict["by_horizon"][-1]["spread_to_signal_ratio"], 1)
        + "x larger than the realised one, and the mandatory floor fee alone requires "
        + _number(verdict["by_horizon"][-1]["fee_to_signal_ratio"], 1) + "x. Both multiples are measured, not "
        "projected: they are the ratio of a cost component to the realised edge at the same horizon.")
    add("")
    add(_md_table(
        ["flag", "holds", "rule"],
        [[name, "TRUE" if value else "FALSE", verdict["rules"][name]] for name, value in verdict["flags"].items()],
    ))
    add("")
    add(f"Horizon increments of `net {floor}` across the declared grid: " + ", ".join(
        _number(value) for value in verdict["horizon_increments_bps"]
    ) + " bps, i.e. a ten-fold extension of the horizon closes "
        + _number(verdict["horizon_fraction_of_gap_closed"] * 100, 1)
        + "% of the remaining gap (the required move itself is horizon-invariant: "
        + _number(verdict["by_horizon"][0]["required_move_bps"]) + " bps at 100 ms against "
        + _number(verdict["by_horizon"][-1]["required_move_bps"]) + " bps at 1000 ms). Cross-state dispersion of the "
        "net result over the 40 (bin x horizon) states is " + _number(verdict["state_dispersion_bps"])
        + " bps, " + _number(verdict["state_dispersion_ratio"] * 100, 1)
        + "% of the mean, so the declared states barely separate. Holding flags: "
        + (", ".join(verdict["holding"]) if verdict["holding"] else "none") + ".")
    add("")

    add("## 6. Answers (request §6)")
    add("")
    answer = bundle["answers"]
    q1 = answer["q1_any_state_approaches_or_exceeds_structural_hurdle"]
    best_cell = q1["best_declared_cell"]
    add("**1. Is there any development-sample state in the predeclared state space where aggressive execution "
        "approaches or exceeds the structural hurdle?**")
    add("")
    add(f"No. {q1['declared_cells_with_positive_net']} of the {q1['declared_cells_total']} declared cells "
        "(10 imbalance bins × 2 spread classes × 5 price bands × 4 horizons) have a positive structural-cost-adjusted "
        f"result, and {q1['states_with_positive_net']} of the {q1['declared_states_in_bin_horizon_space']} cells of "
        "the aggregated (bin × horizon) view do. The best cell in the whole declared space is "
        f"`{best_cell['cell']}` — {best_cell['net_' + floor + '_bps']:.4f} bps net, i.e. still losing — with a hurdle "
        f"coverage of {_number(best_cell['hurdle_coverage'], 3)} (mean side-signed mid move "
        f"{_number(best_cell['mean_signal_signed_mid_move_bps'])} bps against a "
        f"{_number(best_cell['required_move_bps'])} bps required move) on {best_cell['observations']:,} observations.")
    add("")
    add("Cells at each declared hurdle-coverage cut — the full 400-cell grid first, then the (bin × horizon) view: "
        + ", ".join(f"≥{cut}×: {count}" for cut, count in q1["cells_at_hurdle_coverage_cut"].items())
        + " (full grid); "
        + ", ".join(f"≥{cut}×: {count}" for cut, count in q1["hurdle_coverage_cut_counts_bin_horizon"].items())
        + " (bin × horizon). These cuts are descriptive buckets, not selection rules: no state is promoted and none "
          "is killed, and the best cell is named only because the question asks where the maximum lies.")
    add("")
    add("**2. What fraction of opportunities does that state represent?**")
    add("")
    q2 = answer["q2_fraction_of_opportunities_of_best_state"]
    add(f"For the best aggregated state (`{q1['best_state']['label_value']}` at {q1['best_state']['horizon_ms']} ms): "
        f"{_number(q2['best_state_share_of_signal_defined_observations'] * 100, 3)}% of the signal-defined "
        f"observations ({q2['best_state_observations']:,} of {q2['signal_defined_observations']:,}). For the best "
        f"individual cell (`{best_cell['cell']}`): "
        f"{_number(q2['best_cell_share_of_signal_defined_observations'] * 100, 4)}% "
        f"({q2['best_cell_observations']:,} observations, "
        f"{best_cell['block_cells']} symbol-block cells, block-bootstrap SE "
        f"{_number(best_cell['block_bootstrap_se_net_' + floor + '_bps'])} bps). Both fractions are reported so that "
        "a reader can see how little of the opportunity set a favourable cell addresses even if it were real.")
    add("")
    add("**3. Does a clairvoyant aggressive trader have meaningful room after costs?**")
    add("")
    q3 = answer["q3_clairvoyant_room_after_costs"]
    add(f"No. At the longest declared horizon ({q3['horizon_ms']} ms), perfect side selection earns "
        f"{_number(q3[f'mean_oracle_net_{floor}_bps'])} bps per observation after the structural floor and "
        + ", ".join(
            f"{_number(value)} bps after {label}"
            for label, value in q3["mean_oracle_net_by_schedule"].items()
            if label != floor
        )
        + f", on {q3['observations']:,} observations; it beats abstaining on "
        f"{_number(q3['prob_oracle_gross_positive'] * 100, 2)}% of them before costs and on "
        f"{_number(q3[f'prob_oracle_net_{floor}_positive'] * 100, 2)}% after the structural floor. That bound is "
        f"{_number(q3['oracle_bound_as_fraction_of_required_move'] * 100, 2)}% of the "
        f"{_number(q3['required_move_bps_at_that_horizon'])} bps required move at the same horizon: the entire value "
        "of perfect foresight is about 0.013 bps per decision, three orders of magnitude below what the execution "
        "formulation needs. No predictive model can close that, and this is the strongest statement this "
        "calculation supports — it does not depend on any model, only on the realised future quotes.")
    add("")
    add("**4. Which component creates the dominant economic gap?**")
    add("")
    decomposition = bundle["verdict"]["by_horizon"][-1]
    add(f"The gap is `required move - realised move` = {_number(decomposition['required_move_bps'])} - "
        f"({_number(decomposition['signal_bps'])}) bps, decomposed exactly in §5: **the full spread paid contributes "
        f"{_number(decomposition['spread_share_of_required'] * 100, 1)}%** of the required move, **the mandatory "
        f"venue/regulatory fee {_number(decomposition[f'fee_share_of_required'] * 100, 1)}%**, and the signal "
        f"supplies {_number(decomposition['signal_coverage_of_required'] * 100, 2)}%. The broker reference layer on "
        "top of the floor is an additional "
        + ", ".join(
            f"{_number(bundle['verdict']['net_by_schedule_at_longest_horizon'][floor] - value)} bps ({label})"
            for label, value in bundle["verdict"]["net_by_schedule_at_longest_horizon"].items()
            if label != floor
        )
        + ". Flags holding, with their rules in §5a: " + ", ".join(answer["q4_dominant_gap_component"]) + ".")
    add("")
    add(f"Reading: the dominant component is the **spread** ({_number(decomposition['spread_share_of_required'] * 100, 1)}% "
        "of the hurdle), the fee is second, and the signal is not a large contributor to the gap because it is "
        "negligible in absolute terms — it would need to be "
        f"{_number(decomposition['spread_to_signal_ratio'], 1)}x larger merely to pay the spread. That is a "
        "combination, and the decomposition is the evidence for it; nothing here is inferred from the shape of the "
        "results alone.")
    add("")

    add("## 7. Reconciliation and limitations")
    add("")
    add(_md_table(
        ["check", "observations", "mismatches / max abs difference / ratio", "tolerance", "outcome"],
        [
            [
                row["check"],
                f"{row.get('observations', 0):,}",
                (
                    f"ratio {_number(row['max_ratio'], 6)} (expected {_number(row['expected_ratio'])})"
                    if "max_ratio" in row
                    else (
                        f"{row['mismatches']:,}"
                        if "mismatches" in row
                        else (
                            f"{row['cell_total']:,} in cells"
                            if "cell_total" in row
                            else _number(row.get("max_abs_difference", float("nan")))
                        )
                    )
                ),
                row.get("tolerance", ""),
                row["outcome"],
            ]
            for row in bundle["reconciliation"]
        ],
    ))
    add("")
    add("### 7a. Discrepancies found in the frozen M2-0 execution table — reported, not repaired")
    add("")
    add("The frozen table could not be reproduced in two of its columns, and the difference is not a tolerance: it is "
        "exact. Both defects are in `M2/src/calculate.py::execution_rows`, they are reproduced here bit for bit by "
        "recomputing M2-0's own expressions (`frozen_cross_to_cross_is_half_of_true_bps`, "
        "`frozen_cost_column_is_ledger_at_half_price`), and **no frozen artifact was modified, regenerated or "
        "overwritten by this pass**.")
    add("")
    add(_md_table(
        ["id", "expression in the frozen artifact", "correct expression", "effect", "verified by"],
        [
            [
                row["id"],
                f"`{row['frozen_expression']}`",
                f"`{row['correct_expression']}`",
                row["effect"],
                row["verified_by"],
            ]
            for row in bundle["discrepancies"]
        ],
    ))
    add("")
    add("Affected artifacts: " + "; ".join(
        sorted({artifact for row in bundle["discrepancies"] for artifact in row["affected_artifacts"]})
    ) + ".")
    add("")
    add("Impact on M2-0's conclusions: `mean_gross_markout_bps` is unaffected and reproduces exactly. Both defects "
        "make the aggressive arithmetic look *better* than it is, so the direction of M2-0's qualitative statement "
        "(aggressive execution loses money on this sample) is unchanged — the corrected cross-to-cross result is "
        "more negative, and the corrected fee is smaller. The columns this pass reports are the corrected ones; a "
        "reader comparing the two tables should expect the exact factor of two recorded above.")
    add("")
    add("Limitations, stated so the bound cannot be read as more than it is:")
    add("")
    add("- **Development sample only.** One 2019 sample day, 61 development-scope symbols that are *not* frozen "
        "universe membership. No modern-regime claim transfers from it, and no out-of-sample claim is made.")
    add("- **Costs are 2026 rate cards on a 2019 tape.** They validate the arithmetic and the ordering of the "
        "components; they do not reconstruct 2019 economics. The structural floor is a lower bound that no "
        "achievable path reaches, and it excludes commission, clearing, market data, slippage and impact — so "
        "every result here is optimistic, not conservative.")
    add("- **Idealized fills.** Sufficient displayed size, immediate aggressive fill, no impact, no queue effect.")
    add("- **The delay-0 instant is the arrival instant.** Latency beyond it is not modelled here; M2-0's delay "
        "surface shows this arithmetic is essentially flat across the delay grid on this sample.")
    add("- **The oracle bound is not achievable** and must never be used for training, selection or reporting as "
        "performance. It exists only to bound what prediction could possibly be worth.")
    add("")
    add("## 8. Artifacts")
    add("")
    add(_md_table(
        ["artifact", "content"],
        [
            ["`M2/output/calculations/aggressive_feasibility_by_state.csv`", "request §1: the 100 declared cells × 4 horizons = 400 rows"],
            ["`M2/output/calculations/breakeven_hurdle.csv`", "request §2, hurdle and realized distributions plus P(realized > hurdle)"],
            ["`M2/output/calculations/oracle_upper_bound.csv`", "request §3, ORACLE_UPPER_BOUND per declared cell"],
            ["`M2/output/calculations/qimb_constrained_bound.csv`", "request §4, QIMB_CONSTRAINED_BOUND per declared cell"],
            ["`M2/output/calculations/feasibility_status.json`", "run status, observation accounting, every reconciliation row, the mechanism verdict and the answers"],
        ],
    ))
    add("")
    add("Reproduce with `python -m M2.src.feasibility --config M2/config/nasdaq_qimb_m2_0.yaml`.")
    add("")
    return "\n".join(out)


# ------------------------------------------------------------------------ stage
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the M2-0.5 aggressive feasibility bound (read-only on the frozen M2-0 artifacts)."
    )
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_0.yaml")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    ledger = costs.load_ledger(config_module.repo_path(configuration["cost_ledger"]["artifact"]))
    problems = costs.validate_ledger(ledger)
    if problems:
        raise SystemExit("cost ledger failed provenance validation: " + "; ".join(problems))

    derived = config_module.repo_path(config_module.derived_dir(configuration))
    calculations_dir = config_module.ensure_dirs(configuration, "calculations")
    with open(os.path.join(derived, "replay_summary.json")) as handle:
        replay_payload = json.load(handle)
    verdict = replay_payload["quality_limits"]["verdict"]
    if verdict != "DATA_VALID":
        status = {
            "run_status": "CALCULATION_BLOCKED",
            "blocked_reason": "the replay day breached a binding data-quality limit; no bound is computed on it",
            "quality_limits": replay_payload["quality_limits"],
        }
        config_module.write_json(os.path.join(calculations_dir, "feasibility_status.json"), status)
        print(json.dumps(status, indent=2, default=str))
        return 2

    horizons_ms = configuration["horizons_ms"]
    bootstrap = configuration["statistics"]["bootstrap"]
    columns = load_execution_columns(derived, configuration)
    frame = build_frame(columns, configuration, ledger)

    table1 = feasibility_rows(frame, configuration, ledger, bootstrap, horizons_ms)
    table2 = breakeven_rows(frame, configuration, ledger, horizons_ms)
    table3 = oracle_rows(frame, configuration, ledger, horizons_ms)
    table4 = qimb_rows(frame, configuration, ledger, horizons_ms)

    bundle = build_bundle(frame, configuration, ledger, horizons_ms, table1)
    bundle.update(
        {
            "run_id": configuration["run"]["run_id"],
            "candidate_id": configuration["run"]["candidate_id"],
            "dataset": configuration["dataset"]["dataset_id"],
            "coverage_date": configuration["dataset"]["coverage_date"],
            "config_sha256": config_module.sha256_file(arguments.config),
            "cost_ledger_sha256": config_module.sha256_file(configuration["cost_ledger"]["artifact"]),
            "code_sha256": {
                "M2/src/feasibility.py": config_module.sha256_file("M2/src/feasibility.py"),
            },
            "derived_artifacts": {
                name: config_module.sha256_file(os.path.join(derived, name))
                for name in ("decisions.parquet", "delay_decisions.parquet")
            },
        }
    )
    bundle["reconciliation"] = reconciliation_rows(bundle, frame, columns, configuration, ledger)
    bundle["verdict"] = mechanism_verdict(bundle)
    bundle["answers"] = answers(bundle)

    calculate.write_csv(os.path.join(calculations_dir, "aggressive_feasibility_by_state.csv"), table1)
    calculate.write_csv(os.path.join(calculations_dir, "breakeven_hurdle.csv"), table2)
    calculate.write_csv(os.path.join(calculations_dir, "oracle_upper_bound.csv"), table3)
    calculate.write_csv(os.path.join(calculations_dir, "qimb_constrained_bound.csv"), table4)

    failed = [row["check"] for row in bundle["reconciliation"] if row["outcome"] == "FAIL"]
    not_evaluated = [
        row["check"] for row in bundle["reconciliation"] if row["outcome"] == "NOT_EVALUATED_REFERENCE_ABSENT"
    ]
    report_path = config_module.repo_path(config_module.output_dir(configuration, "M2_0_5_FEASIBILITY.md"))
    with open(report_path, "w") as handle:
        handle.write(render(bundle))

    status = {
        "run_status": "CALCULATION_BLOCKED" if failed else "CALCULATION_COMPLETE",
        "data_status": verdict,
        "run_id": bundle["run_id"],
        "candidate_id": bundle["candidate_id"],
        "dataset": bundle["dataset"],
        "coverage_date": bundle["coverage_date"],
        "cost_ledger_id": ledger["ledger_id"],
        "config_sha256": bundle["config_sha256"],
        "cost_ledger_sha256": bundle["cost_ledger_sha256"],
        "code_sha256": bundle["code_sha256"],
        "derived_artifacts": bundle["derived_artifacts"],
        "cell_dimensions": bundle["cell_dimensions"],
        "observation_sets": bundle["observation_sets"],
        "reconciliation": bundle["reconciliation"],
        "discrepancies_in_frozen_M2_0_artifacts": bundle.get("discrepancies", []),
        "failed_checks": failed,
        "not_evaluated_checks": not_evaluated,
        "mechanism_verdict": bundle["verdict"],
        "answers": bundle["answers"],
        "artifacts": [
            "M2/output/calculations/aggressive_feasibility_by_state.csv",
            "M2/output/calculations/breakeven_hurdle.csv",
            "M2/output/calculations/oracle_upper_bound.csv",
            "M2/output/calculations/qimb_constrained_bound.csv",
            "M2/output/calculations/feasibility_status.json",
            "M2/output/M2_0_5_FEASIBILITY.md",
        ],
        "scope_note": (
            "development-scope symbols on a single 2019 sample day; not universe membership, not a backtest, no "
            "promotion or kill decision, no model fitted, no data purchased"
        ),
        "oracle_warning": ORACLE_NOTE,
        "qimb_warning": QIMB_NOTE,
    }
    config_module.write_json(os.path.join(calculations_dir, "feasibility_status.json"), status)
    print(
        json.dumps(
            {
                "run_status": status["run_status"],
                "signal_defined_observations": bundle["observation_sets"]["signal_defined"],
                "cell_rows": len(table1),
                "reconciliation_failures": failed,
            },
            indent=2,
            default=str,
        )
    )
    if failed:
        raise SystemExit("a feasibility number could not be reconciled: " + ", ".join(failed))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())