"""Analysis of the M2-1 passive replay: fills, adverse selection and executable economics.

This module reads the deterministic replay's attempt table and answers the five feasibility
questions in order:

    fill probability -> fill-conditioned adverse selection -> executable entry/exit economics
    -> expected value per attempt -> robustness across declared states

Nothing is fitted, nothing is optimised and no threshold is selected here. Cost accounting uses
the frozen ledger's own one-sided order breakdown, so the entry leg of a passive order is charged
no exchange fee (the ledger carries no add-liquidity item) and the aggressive exit leg is charged
its remove-liquidity fee, statutory charges and, on the accessible reference path, commission.
A separately labelled sensitivity credits the verified Nasdaq add-liquidity credit recorded in
``M1/output/venue_cost_reference.csv`` (SRC-0203), which is a 2026 rate card applied to a 2019
tape and therefore never the primary number.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os

import numpy as np
import pyarrow.parquet as pq

from . import calculate
from . import config as config_module
from . import costs

BLOCK_NS = 1800 * 1_000_000_000
IMBALANCE_EDGES = [-1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
QUEUE_POSITION_EDGES = [0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.01]
ADD_LIQUIDITY_CREDIT_USD_PER_SHARE = 0.0018  # SRC-0203, 2026 card: a labelled sensitivity only


def load_attempts(path: str) -> dict:
    table = pq.read_table(path)
    return {name: table[name].to_numpy(zero_copy_only=False) for name in table.column_names}


def bin_labels(values: np.ndarray, edges: list[float]) -> list[str]:
    labels = []
    for value in values:
        label = "OUT_OF_RANGE"
        for index in range(len(edges) - 1):
            low, high = edges[index], edges[index + 1]
            if index == len(edges) - 2:
                inside = low <= value <= high
            else:
                inside = low <= value < high
            if inside:
                label = f"[{low:g},{high:g})"
                break
        labels.append(label)
    return labels


def dependence_aware_ci(values: np.ndarray, cell_codes: np.ndarray, n_cells: int,
                        resamples: int, seed: int) -> tuple[float, float, float, int]:
    """Block-bootstrap CI over (symbol, 30-minute block) cells, reusing the project's routine."""
    finite = np.isfinite(values)
    if finite.sum() == 0:
        return float("nan"), float("nan"), float("nan"), 0
    sums = np.bincount(cell_codes[finite], weights=values[finite], minlength=n_cells)
    counts = np.bincount(cell_codes[finite], minlength=n_cells).astype(float)
    means = np.divide(sums, counts, out=np.zeros_like(sums), where=counts > 0)
    se, low, high = calculate.block_bootstrap_ci(means, counts, resamples, seed)
    return float(se), float(low), float(high), int(finite.sum())


def summarise(values: np.ndarray) -> dict:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"n": 0, "mean": None, "median": None, "p05": None, "p25": None, "p75": None,
                "p95": None, "share_positive": None}
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "p05": float(np.percentile(finite, 5)),
        "p25": float(np.percentile(finite, 25)),
        "p75": float(np.percentile(finite, 75)),
        "p95": float(np.percentile(finite, 95)),
        "share_positive": float(np.mean(finite > 0)),
    }


def one_leg_cost_bps(ledger: dict, regime: str, schedule: str | None, side: str, shares: float,
                     price_usd: float) -> float:
    breakdown = costs.order_cost_breakdown(ledger, regime, side, shares, price_usd, schedule)
    notional = shares * price_usd
    if notional <= 0:
        return float("nan")
    return 1e4 * breakdown["total_usd"] / notional


class PassiveAnalysis:
    def __init__(self, configuration: dict, attempts_path: str, ledger: dict, membership: dict):
        self.configuration = configuration
        self.ledger = ledger
        self.attempts = load_attempts(attempts_path)
        self.membership = membership
        scale = float(configuration["price_scale"])
        self.scale = scale
        a = self.attempts
        self.side = a["side"].astype(float)
        self.filled = a["filled_shares"].astype(float)
        self.has_fill = self.filled > 0
        self.price = a["price_raw"].astype(float) / scale
        self.price = np.where(self.price > 0, self.price, np.nan)
        self.fill_price = np.where(a["filled_price_raw"] > 0,
                                  a["filled_price_raw"].astype(float) / scale, np.nan)
        self.mid_fill = np.where(a["mid2_at_fill"] > 0,
                                 a["mid2_at_fill"].astype(float) / 2.0 / scale, np.nan)
        self.size = a["size"].astype(float)
        self.locate = a["locate"].astype(int)
        self.ts = a["ts_ns"].astype(np.int64)
        self.block = (self.ts // BLOCK_NS).astype(np.int64)
        self.symbol = np.array([str(s) for s in a["symbol"]])
        self.large_tick = np.array([membership.get(s, False) for s in self.symbol])
        cells, n_symbols, n_blocks = calculate.build_cells(self.locate, self.block)
        self.cells = cells
        self.n_cells = n_symbols * n_blocks
        self.exits = {}
        for horizon in (10, 25, 50, 100, 250, 500, 1000):
            bid = a.get(f"exit_bid_{horizon}ms").astype(float) / scale
            ask = a.get(f"exit_ask_{horizon}ms").astype(float) / scale
            # an unresolved exit is a zero in the attempt table; keep it as missing, never as 0
            self.exits[horizon] = (np.where(bid > 0, bid, np.nan), np.where(ask > 0, ask, np.nan))
        self.path = attempts_path

    # ------------------------------------------------------------------ derived series
    def mid_markout_bps(self, horizon: int) -> np.ndarray:
        bid, ask = self.exits[horizon]
        mid = (bid + ask) / 2.0
        valid = np.isfinite(mid) & (mid > 0) & np.isfinite(self.mid_fill)
        out = np.full(self.filled.shape, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[valid] = self.side[valid] * 1e4 * (mid[valid] - self.mid_fill[valid]) / self.mid_fill[valid]
        return out

    def fill_price_markout_bps(self, horizon: int) -> np.ndarray:
        bid, ask = self.exits[horizon]
        mid = (bid + ask) / 2.0
        valid = np.isfinite(mid) & (mid > 0) & np.isfinite(self.fill_price)
        out = np.full(self.filled.shape, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[valid] = self.side[valid] * 1e4 * (mid[valid] - self.fill_price[valid]) / self.fill_price[valid]
        return out

    def gross_exit_bps(self, horizon: int) -> np.ndarray:
        """Passive entry, aggressive exit: sell at the bid after a buy, buy at the ask after a sell."""
        bid, ask = self.exits[horizon]
        valid = np.isfinite(self.fill_price) & (self.fill_price > 0)
        out = np.full(self.filled.shape, np.nan)
        long_side = self.side > 0
        with np.errstate(invalid="ignore", divide="ignore"):
            out[valid & long_side] = (
                1e4 * (bid[valid & long_side] - self.fill_price[valid & long_side])
                / self.fill_price[valid & long_side]
            )
            out[valid & ~long_side] = (
                1e4 * (self.fill_price[valid & ~long_side] - ask[valid & ~long_side])
                / self.fill_price[valid & ~long_side]
            )
        return out

    def exit_cost_bps(self, regime: str, schedule: str | None, horizon: int) -> np.ndarray:
        bid, ask = self.exits[horizon]
        out = np.full(self.filled.shape, np.nan)
        exit_side = np.where(self.side > 0, "sell", "buy")
        prices = np.where(self.side > 0, bid, ask)
        valid = self.has_fill & np.isfinite(prices) & (prices > 0)
        for label in ("sell", "buy"):
            mask = valid & (exit_side == label)
            if not mask.any():
                continue
            sample = np.unique(np.round(prices[mask], 4))
            lookup = {}
            stride = max(1, sample.size // 400)
            for price in sample[::stride]:
                lookup[round(float(price), 4)] = one_leg_cost_bps(
                    self.ledger, regime, schedule, label, float(self.size[mask][0]), float(price)
                )
            keys = np.round(prices[mask], 4)
            out[mask] = np.array([lookup.get(round(float(k), 4), float("nan")) for k in keys])
        return out

    # ------------------------------------------------------------------ tables
    def fill_summary_row(self, subset: str, mask: np.ndarray) -> dict:
        attempts = int(mask.sum())
        filled_attempts = int((mask & self.has_fill).sum())
        filled_shares = float(self.filled[mask].sum())
        partial = int(((mask & self.has_fill) & (self.filled < self.size)).sum())
        complete = int(((mask & self.has_fill) & (self.filled >= self.size)).sum())
        ttf = self.attempts["time_to_first_fill_ns"][mask & self.has_fill].astype(float)
        ttf = ttf[np.isfinite(ttf)]
        ahead = self.attempts["queue_ahead_shares"][mask].astype(float)
        return {
            "subset": subset,
            "attempts": attempts,
            "filled_attempts": filled_attempts,
            "fill_rate": (filled_attempts / attempts) if attempts else None,
            "filled_shares": filled_shares,
            "shares_per_attempt": (filled_shares / attempts) if attempts else None,
            "partial_fill_attempts": partial,
            "complete_fill_attempts": complete,
            "partial_fill_share_of_fills": (partial / filled_attempts) if filled_attempts else None,
            "median_time_to_first_fill_ms": (float(np.median(ttf)) / 1e6) if ttf.size else None,
            "p90_time_to_first_fill_ms": (float(np.percentile(ttf, 90)) / 1e6) if ttf.size else None,
            "median_queue_ahead_shares": float(np.median(ahead)) if ahead.size else None,
            "median_queue_ahead_orders": float(np.median(self.attempts["queue_ahead_orders"][mask])),
            "queue_ahead_zero_share": float(np.mean(ahead == 0)) if ahead.size else None,
        }

    def state_table(self, mask: np.ndarray) -> list[dict]:
        imbalance = self.attempts["imbalance"].astype(float)
        labels = np.array(bin_labels(np.abs(imbalance), [0.0, 0.2, 0.4, 0.6, 0.8, 1.0001]))
        rows = []
        for label in sorted(set(labels)):
            cell = mask & (labels == label)
            if not cell.any():
                continue
            row = self.fill_summary_row(f"|I|{label}", cell)
            row.update(self.economics_row(cell))
            rows.append(row)
        return rows

    def queue_position_table(self, mask: np.ndarray) -> list[dict]:
        position = self.attempts["queue_position_percentile"].astype(float)
        labels = np.array(bin_labels(position, QUEUE_POSITION_EDGES))
        rows = []
        for label in sorted(set(labels)):
            cell = mask & (labels == label)
            if not cell.any():
                continue
            row = self.fill_summary_row(f"qp{label}", cell)
            row.update(self.economics_row(cell))
            rows.append(row)
        return rows

    def economics_row(self, mask: np.ndarray) -> dict:
        """Per-attempt and per-fill economics at the frozen 1000 ms exit, floor and fixed path.

        Units are explicit: `ev_per_attempt_usd` is executable dollars per submission including
        no-fills, `ev_per_attempt_bps` expresses the same number per unit of one order's notional,
        and `ev_per_filled_share_bps` is the share-weighted net return of a filled share.
        """
        horizon = 1000
        gross = self.gross_exit_bps(horizon)
        floor_cost = self.exit_cost_bps("STRUCTURAL_COST_FLOOR", None, horizon)
        fixed_cost = self.exit_cost_bps("ACCESSIBLE_REFERENCE_PATH", "ibkr_pro_fixed", horizon)
        filled_mask = mask & self.has_fill
        shares = self.filled[filled_mask]
        total_shares = float(np.sum(shares))
        attempts = int(mask.sum())
        gross_bps = gross[filled_mask]
        net_floor = gross_bps - floor_cost[filled_mask]
        net_fixed = gross_bps - fixed_cost[filled_mask]
        notional = self.size[filled_mask] * self.fill_price[filled_mask]
        mean_notional = float(np.mean(self.size[mask] * self.price[mask])) if attempts else None
        def to_usd(net_bps):
            if total_shares == 0:
                return 0.0
            return float(np.nansum(net_bps * 1e-4 * notional))
        ev_floor_usd = to_usd(net_floor) / attempts if attempts else None
        ev_fixed_usd = to_usd(net_fixed) / attempts if attempts else None
        rebate_usd = (ADD_LIQUIDITY_CREDIT_USD_PER_SHARE * total_shares / attempts
                      if attempts else None)
        return {
            "filled_share_of_attempts": (total_shares / attempts) if attempts else None,
            "gross_bps_per_filled_share": (
                float(np.nansum(gross_bps * shares) / total_shares) if total_shares else None
            ),
            "net_floor_bps_per_filled_share": (
                float(np.nansum(net_floor * shares) / total_shares) if total_shares else None
            ),
            "net_fixed_bps_per_filled_share": (
                float(np.nansum(net_fixed * shares) / total_shares) if total_shares else None
            ),
            "ev_per_attempt_usd_floor": ev_floor_usd,
            "ev_per_attempt_usd_fixed": ev_fixed_usd,
            "ev_per_attempt_bps_floor": (
                1e4 * ev_floor_usd / mean_notional if (ev_floor_usd is not None and mean_notional)
                else None
            ),
            "ev_per_attempt_bps_fixed": (
                1e4 * ev_fixed_usd / mean_notional if (ev_fixed_usd is not None and mean_notional)
                else None
            ),
            "rebate_sensitivity_ev_per_attempt_usd": (
                (ev_floor_usd or 0.0) + (rebate_usd or 0.0) if attempts else None
            ),
        }

    # ------------------------------------------------------------------ main tables
    def run(self) -> dict:
        mask_all = np.ones(self.filled.shape, dtype=bool)
        mask_primary = self.large_tick.copy()
        mask_secondary = ~self.large_tick
        summary_rows = [
            self.fill_summary_row("primary_large_tick_proxy", mask_primary),
            self.fill_summary_row("secondary_other_scope_names", mask_secondary),
            self.fill_summary_row("all_replayed_names", mask_all),
        ]
        horizon_rows = []
        for horizon in (10, 25, 50, 100, 250, 500, 1000):
            for subset, mask in (("primary", mask_primary), ("all", mask_all)):
                filled_mask = mask & self.has_fill
                mid = self.mid_markout_bps(horizon)
                fill_mark = self.fill_price_markout_bps(horizon)
                gross = self.gross_exit_bps(horizon)
                row = {"subset": subset, "horizon_ms": horizon,
                       "filled_attempts": int(filled_mask.sum())}
                for name, series in (("mid_markout_bps", mid), ("fill_price_markout_bps", fill_mark),
                                     ("gross_exit_bps", gross)):
                    stats = summarise(series[filled_mask])
                    for key in ("n", "mean", "median", "p05", "p25", "p75", "p95", "share_positive"):
                        row[f"{name}_{key}"] = stats[key]
                se, low, high, n = dependence_aware_ci(
                    mid[filled_mask], self.cells[filled_mask], self.n_cells,
                    int(self.configuration["statistics"]["bootstrap"]["resamples"]),
                    int(self.configuration["statistics"]["bootstrap"]["seed"]) + horizon,
                )
                row.update({"mid_markout_bps_block_se": se, "mid_markout_bps_ci_low": low,
                            "mid_markout_bps_ci_high": high})
                horizon_rows.append(row)

        # execution economics on the frozen exit horizon
        exit_rows = []
        for subset, mask in (("primary", mask_primary), ("all", mask_all)):
            filled_mask = mask & self.has_fill
            gross = self.gross_exit_bps(1000)
            attempts = int(mask.sum())
            shares = self.filled[filled_mask]
            total_shares = float(np.sum(shares))
            notional = self.size[filled_mask] * self.fill_price[filled_mask]
            mean_notional = float(np.mean(self.size[mask] * self.price[mask])) if attempts else None
            for regime, schedule, label in (("STRUCTURAL_COST_FLOOR", None, "structural_floor"),
                                            ("ACCESSIBLE_REFERENCE_PATH", "ibkr_pro_fixed", "accessible_fixed"),
                                            ("ACCESSIBLE_REFERENCE_PATH", "ibkr_pro_tiered", "accessible_tiered")):
                cost = self.exit_cost_bps(regime, schedule, 1000)
                net = np.where(filled_mask, gross - cost, np.nan)
                net_filled = net[filled_mask]
                stats = summarise(net_filled)
                ev_usd = (float(np.nansum(net_filled * 1e-4 * notional)) / attempts
                          if attempts else None)
                share_of_attempts = (total_shares / attempts) if attempts else 0.0
                exit_rows.append({
                    "subset": subset, "cost_regime": label, "horizon_ms": 1000,
                    "attempts": attempts,
                    "filled_attempts": int(filled_mask.sum()),
                    "net_bps_mean": stats["mean"], "net_bps_median": stats["median"],
                    "net_bps_p05": stats["p05"], "net_bps_p95": stats["p95"],
                    "share_positive": stats["share_positive"],
                    "exit_cost_bps_mean": float(np.nanmean(cost[filled_mask])) if filled_mask.any() else None,
                    "ev_per_filled_share_bps": (
                        float(np.nansum(net_filled * shares) / total_shares) if total_shares else None
                    ),
                    "ev_per_attempt_usd": ev_usd,
                    "ev_per_attempt_bps": (
                        1e4 * ev_usd / mean_notional if (ev_usd is not None and mean_notional) else None
                    ),
                    "rebate_sensitivity_ev_per_attempt_usd": (
                        (ev_usd or 0.0) + ADD_LIQUIDITY_CREDIT_USD_PER_SHARE * share_of_attempts
                        if attempts else None
                    ),
                    "rebate_sensitivity_ev_per_attempt_bps": (
                        1e4 * ((ev_usd or 0.0) + ADD_LIQUIDITY_CREDIT_USD_PER_SHARE * share_of_attempts)
                        / mean_notional if (attempts and mean_notional) else None
                    ),
                })
        return {
            "fill_summary": summary_rows,
            "horizon_rows": horizon_rows,
            "exit_rows": exit_rows,
            "state_rows": self.state_table(mask_primary),
            "queue_rows": self.queue_position_table(mask_primary),
        }


def write_csv(path: str, rows: list[dict]) -> None:
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


# ---------------------------------------------------------------------- verdict
def build_verdict(analysis: PassiveAnalysis, result: dict, audit: dict, model: dict) -> dict:
    primary_fill = result["fill_summary"][0]
    primary_exit = [row for row in result["exit_rows"]
                    if row["subset"] == "primary" and row["cost_regime"] == "structural_floor"][0]
    primary_exit_fixed = [row for row in result["exit_rows"]
                          if row["subset"] == "primary" and row["cost_regime"] == "accessible_fixed"][0]
    mid_1000 = [row for row in result["horizon_rows"]
                if row["subset"] == "primary" and row["horizon_ms"] == 1000][0]
    metrics = {
        "m1_fill_probability": primary_fill["fill_rate"],
        "m1_filled_attempts": primary_fill["filled_attempts"],
        "m1_attempts": primary_fill["attempts"],
        "m1_median_time_to_first_fill_ms": primary_fill["median_time_to_first_fill_ms"],
        "m2_fill_conditioned_mid_markout_bps_1000ms_mean": mid_1000["mid_markout_bps_mean"],
        "m2_fill_conditioned_mid_markout_bps_1000ms_median": mid_1000["mid_markout_bps_median"],
        "m2_fill_conditioned_mid_markout_bps_1000ms_ci": [
            mid_1000["mid_markout_bps_ci_low"], mid_1000["mid_markout_bps_ci_high"]],
        "m2_fill_price_markout_bps_1000ms_mean": mid_1000["fill_price_markout_bps_mean"],
        "m3_executable_net_bps_per_filled_share_floor": primary_exit["net_bps_mean"],
        "m3_executable_net_bps_per_filled_share_fixed": primary_exit_fixed["net_bps_mean"],
        "m3_share_of_fills_positive_floor": primary_exit["share_positive"],
        "m4_ev_per_attempt_bps_floor": primary_exit["ev_per_attempt_bps"],
        "m4_ev_per_filled_share_bps_floor": primary_exit["ev_per_filled_share_bps"],
        "m4_ev_per_attempt_bps_fixed": primary_exit_fixed["ev_per_attempt_bps"],
        "m4_ev_per_attempt_usd_floor": primary_exit["ev_per_attempt_usd"],
        "m5_state_dispersion": {
            "states": len(result["state_rows"]),
            "max_ev_per_attempt_bps_floor": max(
                (row.get("ev_per_attempt_bps_floor") or float("-inf")) for row in result["state_rows"]),
            "min_ev_per_attempt_bps_floor": min(
                (row.get("ev_per_attempt_bps_floor") or float("inf")) for row in result["state_rows"]),
            "states_with_positive_ev": sum(
                1 for row in result["state_rows"] if (row.get("ev_per_attempt_bps_floor") or 0) > 0),
            "queue_position_states_with_positive_ev": sum(
                1 for row in result["queue_rows"] if (row.get("ev_per_attempt_bps_floor") or 0) > 0),
        },
        "rebate_sensitivity_ev_per_attempt_usd_floor": primary_exit["rebate_sensitivity_ev_per_attempt_usd"],
        "rebate_sensitivity_ev_per_attempt_bps_floor": primary_exit["rebate_sensitivity_ev_per_attempt_bps"],
    }
    checks = {
        "K1_queue_identifiable": not (
            audit.get("priority_anomalies", 0) > 0.01 * max(1, audit.get("fill_events", 1))
            or audit.get("orphan_executes", 0) > 0
        ),
        "K2_fill_starvation": (metrics["m1_fill_probability"] or 0) < 0.01,
        "K3_adverse_selection": (metrics["m2_fill_conditioned_mid_markout_bps_1000ms_mean"] or 0) < 0,
        "K4_executable_net_negative": (metrics["m3_executable_net_bps_per_filled_share_floor"] or 0) <= 0
                                     and (metrics["m4_ev_per_attempt_bps_floor"] or 0) <= 0,
        "K5_only_unrealistic_queue_positions": (
            metrics["m5_state_dispersion"]["states_with_positive_ev"] > 0
            and (primary_fill["fill_rate"] or 0) > 0
        ),
        "K6_economic_scale_negligible": (metrics["m4_ev_per_attempt_usd_floor"] or 0) < 0.01,
    }
    return {
        "metrics": metrics,
        "kill_checks": checks,
        "audit": audit,
        "model": model,
        "interpretation_notes": [
            "The primary model never fills from non-displayed prints and never assumes a maker "
            "rebate: the entry leg is charged no exchange fee because the frozen ledger has no "
            "add-liquidity item, and the labelled rebate sensitivity is a 2026 rate card applied "
            "to a 2019 tape.",
            "Midpoint adverse-selection markout and fill-price markout are reported separately: "
            "the first isolates post-fill directional movement, the second includes the entry's "
            "price relative to the midpoint.",
            "Per-attempt expected value multiplies the fill probability by the per-fill result, "
            "so an attractive per-fill figure with a near-zero fill rate cannot be mistaken for a "
            "strategy.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M2-1 passive analysis.")
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_1_passive.yaml")
    parser.add_argument("--label", required=True,
                        help="attempt-table label produced by the replay stage, e.g. "
                             "fifo_ttl1000ms_secondary")
    parser.add_argument("--out-subdir", default=None,
                        help="output subdirectory; defaults to the label so that the "
                             "conservative model, the optimistic bound and each TTL diagnostic "
                             "keep separate numbers and can never overwrite one another")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    ledger = costs.load_ledger(config_module.repo_path(configuration["cost_ledger"]["artifact"]))
    problems = costs.validate_ledger(ledger)
    if problems:
        raise SystemExit("cost ledger failed provenance validation: " + "; ".join(problems))
    derived = config_module.repo_path(config_module.derived_dir(configuration))
    attempts_path = os.path.join(derived, f"passive_attempts_{arguments.label}.parquet")
    summary_path = os.path.join(derived, f"passive_run_summary_{arguments.label}.json")
    membership_rows = list(csv.DictReader(open(config_module.repo_path(
        configuration["passive"]["large_tick_membership"]), newline="")))
    membership = {row["symbol"]: row["large_tick_proxy"] == "True" for row in membership_rows}

    analysis = PassiveAnalysis(configuration, attempts_path, ledger, membership)
    result = analysis.run()
    with open(summary_path) as handle:
        run_summary = json.load(handle)
    audit = run_summary["audit"]
    model = run_summary["model"]
    out = config_module.ensure_dirs(configuration, arguments.out_subdir or arguments.label)
    write_csv(os.path.join(out, "fill_summary.csv"), result["fill_summary"])
    write_csv(os.path.join(out, "fill_conditioned_mid_markout.csv"), result["horizon_rows"])
    write_csv(os.path.join(out, "passive_entry_aggressive_exit.csv"), result["exit_rows"])
    write_csv(os.path.join(out, "fill_by_imbalance_state.csv"), result["state_rows"])
    write_csv(os.path.join(out, "fill_by_queue_position.csv"), result["queue_rows"])

    exit_lag_mean_ns = (audit["exit_lag_ns_sum"] / audit["exit_lag_count"]) if audit.get("exit_lag_count") else 0
    queue_audit = [{
        "attempts": audit["attempts"],
        "attempts_skipped_no_quote": audit["attempts_skipped_no_quote"],
        "attempts_skipped_zero_imbalance": audit["attempts_skipped_zero_imbalance"],
        "fill_events": audit["fill_events"],
        "attempts_with_fill": audit["attempts_with_fill"],
        "attempts_no_fill": audit["attempts_no_fill"],
        "attempts_complete": audit["attempts_complete"],
        "attempts_partial_only": audit["attempts_partial_only"],
        "ttl_expired": audit["ttl_expired"],
        "session_end_open": audit["session_end_open"],
        "orphan_executes": audit["orphan_executes"],
        "orphan_cancels": audit["orphan_cancels"],
        "orphan_deletes": audit["orphan_deletes"],
        "orphan_replaces": audit["orphan_replaces"],
        "duplicate_add_refs": audit["duplicate_add_refs"],
        "level_aggregate_mismatches": audit["level_aggregate_mismatches"],
        "priority_anomalies": audit["priority_anomalies"],
        "priority_anomaly_shares": audit["priority_anomaly_shares"],
        "hidden_flow_shares": audit["hidden_flow_shares"],
        "executed_shares_at_level": audit["executed_shares_at_level"],
        "exits_resolved": audit["exits_resolved"],
        "exits_unavailable": audit["exits_unavailable"],
        "exit_lag_mean_ns": exit_lag_mean_ns,
        "exit_lag_max_ns": audit["exit_lag_ns_max"],
        "halts": audit["halts"],
        "cross_messages": audit["cross_messages"],
        "frames_verified": audit["frames_verified"],
    }]
    write_csv(os.path.join(out, "queue_model_audit.csv"), queue_audit)

    verdict = build_verdict(analysis, result, audit, model)
    verdict["label"] = arguments.label
    verdict["scope_primary_symbols"] = int(len(set(analysis.symbol[analysis.large_tick])))
    config_module.write_json(os.path.join(out, "passive_feasibility_verdict.json"), verdict)
    config_module.write_json(
        os.path.join(out, "passive_run_manifest.json"),
        {
            "label": arguments.label,
            "attempts_parquet": os.path.relpath(attempts_path, config_module.REPO_ROOT),
            "attempts_parquet_sha256": config_module.sha256_file(attempts_path),
            "run_summary_sha256": config_module.sha256_file(summary_path),
            "config_sha256": config_module.sha256_file(arguments.config),
            "cost_ledger_sha256": config_module.sha256_file(
                configuration["cost_ledger"]["artifact"]),
            "code_sha256": {
                "M2/src/passive.py": config_module.sha256_file("M2/src/passive.py"),
                "M2/src/passive_analysis.py": config_module.sha256_file(
                    "M2/src/passive_analysis.py"),
            },
            "model": model,
        },
    )
    print(json.dumps(verdict["metrics"], indent=1, default=str))
    print(json.dumps(verdict["kill_checks"], indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
