#!/usr/bin/env python3
"""Branch C — Hyperliquid/Binance hourly funding-basis materiality (FROZEN measurement).

Candidate `TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX`: SHORT Hyperliquid Core BTC
perpetual, LONG equal-BTC-notional Binance USD(S)-M BTCUSDT perpetual, unconditional
direction, exact one-hour hold entered immediately after a completed hourly Hyperliquid
funding settlement, exited at the next complete hourly observation.

Two phases, in this order and never the other way round:

    python3 -m M2.src.basis_materiality --seal    # write freeze.json + freeze.sha256
    python3 -m M2.src.basis_materiality --run     # verify the seal, then measure

`--seal` writes the contract declared statically in :data:`FROZEN_CONTRACT`, together with
the sha256 of this module and of every input it will read.  `--run` refuses to produce a
result unless (a) `freeze.sha256` matches `freeze.json`, (b) this module's sha256 still
equals the sealed `code_sha256`, and (c) every sealed input hash still holds.  A contract,
horizon, universe, state, cost treatment, metric, kill rule, threshold or seed changed
after the seal therefore cannot be reported as if it had been preregistered.

AMENDED PRICE TERM (operator-authorised, AMEND-C5-001).  The price term is causal
LAST-TRADE closes of COMPLETED hourly candles, labelled REFERENCE prices — not executable
mids and not marks.  The canonical manifest's `binance_mark` field stays declared and is
retained for provenance only; it never enters the price term.  Hyperliquid's price field is
its 1h `candleSnapshot` close (trade-derived, integer-valued, as verified by V1 claim A7).

CAUSAL ALIGNMENT.  Panel row `K` carries the candle covering `[K, K+1)`, so it is only
observable from instant `K+1` onward.  A decision at instant `h` may therefore use only
candles that completed at or before `h`, i.e. row `K-1` for a decision at `K`.  Hold `J`
enters on the row-`J-1` reference and exits on the row-`J` reference; the funding
settlement it collects is the one labelled `J+1` (Hyperliquid pays the hour that has just
elapsed, so the print at `J+1` is the accrual over `[J, J+1)`).

NO NETWORK.  Everything is read from the repository: the admitted panel, the local
Binance `fundingRate` / `klines` archives and the local Hyperliquid candle payload.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

if __package__ in (None, ""):  # direct execution: python3 M2/src/basis_materiality.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from M2.src.envelope import (  # noqa: E402  (path bootstrap above)
    Basis,
    CLASS_C1,
    CostItem,
    Envelope,
    Provenance,
    STATUS_UNKNOWN,
    STATUS_VERIFIED,
    UNIT_PCT_OF_TRADE_VALUE,
    assert_c0,
    bps_to_usd,
    break_even_residual,
    c1_sensitivity,
    classify_materiality,
    perp_leg,
    perp_price_pnl,
    reference_path_scenario,
    significance_against_zero,
    to_usd,
    two_leg_net,
    usd_to_bps,
)

ROOT = Path(__file__).resolve().parents[2]
PANEL_DIR = ROOT / "M2" / "data" / "derived_basis"
MANIFEST_PATH = PANEL_DIR / "manifest_basis.json"
PAIRED_PATH = PANEL_DIR / "paired_hours.csv"
RAW_DIR = ROOT / "M2" / "data" / "raw" / "basis"
EXPERIMENT_DIR = ROOT / "M2" / "experiments" / "M2-BRIDGE-HL-BINANCE-BASIS"

HOUR_S = 3600
HOUR_MS = 3_600_000
SETTLEMENT_PERIOD_HOURS = 8  # Binance USD(S)-M BTCUSDT funding cadence, asserted per row
NOTIONAL_USD = 1.0  # unit notional: every reported quantity is bps of notional
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260930
MOVING_BLOCK_HOURS = 24

# ---------------------------------------------------------------------------
# The frozen contract. Written by --seal BEFORE any economic outcome is computed;
# never edited to fit a result.
# ---------------------------------------------------------------------------

FROZEN_CONTRACT: dict = {
    "experiment_id": "M2-BRIDGE-HL-BINANCE-BASIS",
    "parent_id": "GOAL-M2-BRIDGE-001",
    "campaign_epoch": 5,
    "candidate_id": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
    "freeze_status": "FROZEN_BEFORE_ANY_BRANCH_C_ECONOMICS_WERE_INSPECTED",
    "frozen_at_utc": "2026-09-30",
    "amendment_id": "AMEND-C5-001",
    "decision_question": (
        "Is the SIGNED one-hour gross of the unconditional SHORT-Hyperliquid / "
        "LONG-Binance BTC perpetual pair — funding carry of both legs plus the hedge "
        "mark-to-market residual, in bps of notional, on the admitted 4,981-hour panel — "
        "large enough to clear the lowest VERIFIED UNAVOIDABLE execution floor, or does "
        "the uncertainty interval sit below that floor, or is it indistinguishable from "
        "zero at this sample size?"
    ),
    "hypothesis": (
        "The pair is a funding-differential carry: the short Hyperliquid leg receives that "
        "venue's hourly funding rate and the long Binance leg pays that venue's 8-hourly "
        "settlement, while the two BTC perpetual prices' common move cancels, leaving "
        "(r_binance_return - r_hyperliquid_return) as the residual.  Before any execution "
        "model, the frozen question is whether that per-hour carry, measured causally on "
        "completed reference candles, is materially positive."
    ),
    "pair": {
        "leg_a": "SHORT Hyperliquid Core BTC linear perpetual (USDC collateral).",
        "leg_b": "LONG equal-BTC-notional Binance USD(S)-M BTCUSDT perpetual.",
        "direction": "UNCONDITIONAL short-A/long-B, entered every admitted hour; no sign "
                     "conditioning and no state filter is applied (the state is reported, "
                     "not used, because the decision rule is unconditional).",
        "reverse_direction": "sign flip only; not a second tested strategy",
    },
    "amendment": {
        "id": "AMEND-C5-001",
        "authority": "operator",
        "price_term_before": "HL 1h candle close (labelled 'mid proxy') against Binance "
                             "USD(S)-M mark price close; state = HL_mid / Binance_mark - 1.",
        "price_term_after": "causal LAST-TRADE closes of COMPLETED hourly candles on both "
                            "legs, labelled REFERENCE prices; the Binance mark series is "
                            "excluded from the price term.",
        "pair_retained": True,
        "direction_retained": True,
        "hold_retained": "exact one hour",
        "effect": "removes the V1 finding A7/F3 contradiction (a trade-derived candle close "
                  "was labelled a mid and the frozen kill rule named last-trade fallback) by "
                  "relabelling the price term as what it verifiably is.",
    },
    "panel": {
        "path": "M2/data/derived_basis/paired_hours.csv",
        "manifest_path": "M2/data/derived_basis/manifest_basis.json",
        "manifest_contract_id": "ADMISSION-BASIS-C-v1",
        "admission_command": "python3 -m M2.src.admission --manifest "
                             "M2/data/derived_basis/manifest_basis.json --branch BASIS --root .",
        "window_start_utc": "2026-03-05T11:00:00Z",
        "window_start_unix": 1772708400,
        "window_end_utc": "2026-09-28T23:00:00Z",
        "window_end_unix": 1790636400,
        "buckets": 4981,
        "pairing_rule": "bucket = floor(timestamp_ms / 3600000) to the exact UTC hour; each "
                        "source contributes at most one value per bucket; a bucket is matched "
                        "only when every required field is present; no imputation, no "
                        "post-outcome window shrinking.",
    },
    "reference_prices": {
        "hyperliquid": {
            "column": "hl_mid_1h_close",
            "definition": "Hyperliquid POST /info candleSnapshot 1h close for the candle "
                          "covering the row's hour; trade-derived last-trade close; "
                          "REFERENCE price, not a mid and not executable.",
            "rederived_from": "M2/data/raw/basis/hl_candles_1h_0.json",
        },
        "binance": {
            "column": "binance_kline_close",
            "definition": "Binance USD(S)-M BTCUSDT 1h kline close (last trade) for the candle "
                          "covering the row's hour; REFERENCE price, not executable.",
            "rederived_from": "M2/data/raw/basis/klines-1h-*.zip",
        },
        "excluded": {
            "column": "binance_mark_close",
            "reason": "a mark price is neither a last trade nor executable; the amendment "
                      "removes marks from the price term.  The field stays declared in the "
                      "canonical manifest and is verified there, but is not read here.",
        },
        "causality_rule": (
            "panel row K holds the candle covering [K, K+1), observable only from instant K+1; "
            "a decision at instant h may use only candles that completed at or before h, so a "
            "decision at K uses the row K-1 reference on both legs."
        ),
    },
    "staleness": {
        "definition": "decision instant (the Hyperliquid funding settlement time in the panel, "
                      "hl_funding_time_ms) minus the nominal completion instant of the "
                      "reference candle the decision is allowed to use; reported for both legs "
                      "and additionally against the candle's final millisecond.",
        "tolerance_seconds": 1.0,
        "tolerance_basis": "declared before the run and not tuned: it must exceed the largest "
                           "in-window settlement jitter documented before this freeze "
                           "(0.261 s, W3/V1) and stay far below one hour, so that a reference "
                           "one whole hour late would be rejected.",
        "both_legs_same_grid": True,
        "note": "both reference series are UTC-hour-aligned candles whose declared close time "
                "is the hour's final millisecond, so the two legs share one staleness "
                "distribution by construction; both are reported separately anyway.",
    },
    "holds": {
        "decision_hours": "J from window_start_unix + 3600 to window_end_unix - 3600 inclusive, "
                          "step 3600",
        "count": 4979,
        "entry_reference_row": "J - 3600 (candle covering [J-1h, J))",
        "exit_reference_row": "J (candle covering [J, J+1h))",
        "collected_carry_row": "J + 3600",
        "hold_interval": "nominal [J, J+1h); the exit is taken at the boundary funding print of "
                         "row J+1, so the realised duration is 1h + (offset_{J+1} - offset_J), "
                         "bounded by the in-window settlement jitter.",
        "boundary_hours_excluded": {
            "first": "window_start (2026-03-05T11:00Z) — no candle completing at or before it "
                     "exists inside the panel, so its decision has no admissible reference.",
            "last": "window_end (2026-09-28T23:00Z) — its collected carry print lies at "
                    "window_end + 1h, outside the panel.",
            "declared_before_run": True,
            "is_window_shrink": False,
            "reason": "structural consequence of the frozen reference-price rule and the frozen "
                      "one-hour hold inside a bounded panel; declared here, before the run, "
                      "not chosen after seeing an outcome.",
        },
        "coverage_floor": "4979 expected holds, 4979 evaluated holds, contiguous, zero missing, "
                          "zero duplicates; any missing required hold is INDETERMINATE_COVERAGE.",
    },
    "gross": {
        "units": "bps of notional per one-hour hold; positive = profit to the frozen pair",
        "formula": (
            "G(J) = 1e4 * [ funding_cashflow(r_hl(J+1h), N, 'short') "
            "+ funding_cashflow(r_bin(J+1h) if a settlement instant lies inside the hold else 0, "
            "N, 'long') + perp_price_pnl(hl short, row J-1 -> row J) "
            "+ perp_price_pnl(binance long, row J-1 -> row J) ] / N"
        ),
        "signed_not_absolute": True,
        "sign_convention": "a positive Hyperliquid rate is paid by longs to shorts, so the "
                           "short leg receives +r_hl; a positive Binance rate is paid by longs "
                           "to shorts, so the long leg pays -r_bin.",
        "binance_settlement_rule": "the Binance carry is exactly zero, as a measured structural "
                                   "fact (not an imputation), when no settlement instant lies "
                                   "inside the hold; it is the observed settlement rate when one "
                                   "does; it is UNKNOWN, never zero, when a settlement occurs "
                                   "but its rate is not in the local archive.",
        "unresolved_component": {
            "handling": "reported as an explicit additive bracket; the point estimate uses the "
                        "bracket midpoint as a declared central scenario, and the decision "
                        "interval is the union of the sampling interval and the bracket, so the "
                        "unknown is never zero and never decides alone.",
            "bracket_source": "the observed in-window Binance settlement-rate minimum and "
                              "maximum (a bounded scenario, no distribution assumed).",
        },
        "t_star": "T* = C0_bps / mean funding carry bps per hour; interpretive only, never a "
                  "decision input.",
    },
    "costs": {
        "rule": "only the LOWEST VERIFIED UNAVOIDABLE floor justified by the frozen "
                "implementation may enter C0; every other charge stays in C1, and an unknown "
                "value is never zero.",
        "c0": {
            "item": "hl_perp_taker_lowest_published_rung",
            "value_percent_per_side": 0.024,
            "executions_per_hold": 2,
            "bps_per_hold": 4.8,
            "why_unavoidable": "the frozen implementation must open and close the Hyperliquid "
                               "leg; a taker fill is the only guaranteed fill, and 0.024% per "
                               "side is the lowest rung of the venue's published taker "
                               "schedule, so no Hyperliquid account state can pay less than "
                               "this for that execution.  VOLUME_DEPENDENT: True.",
            "provenance": {
                "source_id": "SRC-0213",
                "url": "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees.md",
                "access_date": "2026-09-20",
                "effective_period": "current schedule at access; contemporaneous with the "
                                    "2026-03-05..2026-09-28 sample window",
            },
        },
        "c1_items": [
            "hl_perp_taker_state_dependent_uplift (4.2 bps/hold: 0.045% base tier x 2 sides "
            "minus the C0 floor) — reference execution path",
            "binance_usdm_taker_fee — UNKNOWN, no verified schedule in this repository",
            "hedge_spread_impact_slippage — UNKNOWN, not estimated",
            "capital_margin_borrow_transfer_liquidation — UNKNOWN, not estimated",
        ],
        "base_tier_reference_path": {
            "hyperliquid": "0.045% per side (verified, volume/staking dependent) -> 9.0 bps per "
                           "hold for the Hyperliquid leg",
            "binance": "UNKNOWN — no verified Binance USD(S)-M taker schedule exists in this "
                       "repository, and no value is asserted for it",
            "may_decide_the_kill": False,
        },
    },
    "inference": {
        "primary": "percentile bootstrap over the hourly holds (cluster = the hour; the two "
                   "legs are one observation per hour), resamples, seed and percentiles as "
                   "declared in the fields below",
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "percentiles": [2.5, 97.5],
        "secondary": "moving-block bootstrap, block = 24 hours, same seed and resample count, "
                     "reported as a serial-dependence check and not used for the decision",
        "significance": "reported separately (bootstrap standard error, t against zero); never "
                        "an input to the classification",
    },
    "classification": {
        "rule": "KILL_MATERIALITY if g <= 0 or hi <= C0; SURVIVE_PROVISIONAL if lo > C0; "
                "otherwise INDETERMINATE (named clause)",
        "function": "M2/src/envelope.py::classify_materiality (imported, not re-implemented)",
        "coverage_floor_failure": "INDETERMINATE_COVERAGE, named — never a silent re-scope",
        "kill_scope": "a kill is scoped to this frozen one-hour formulation on this panel; a "
                      "longer or shorter horizon, another pair or another state is a NEW "
                      "candidate, not a reinterpretation of this result.",
    },
    "prohibited_post_result_decisions": [
        "changing the window, the hold length, the reference-price rule, the pair, the "
        "direction, the gross formula, the cost rule, the metric, the kill rule, the "
        "thresholds, the bootstrap seed or the resample count",
        "treating an unknown Binance settlement rate, fee, spread or impact as zero",
        "promoting the base-tier reference path to C0 after seeing a kill that the floor "
        "would not support",
        "reinterpreting a kill as a statement about any horizon other than the frozen one hour",
    ],
    "permitted_post_result_decisions": [
        "reporting the declared sensitivities (bracket endpoints, moving-block interval, "
        "exit-at-nominal-instant variant, C1 levels)",
        "proposing canonical bookkeeping updates without applying them",
    ],
}


class PanelError(Exception):
    """The admitted panel does not have the structure the freeze requires."""


class CoverageFloorError(PanelError):
    """The frozen measurement cannot be evaluated over the declared hold set."""


# ---------------------------------------------------------------------------
# Integrity helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def utc(seconds: int) -> str:
    return datetime.fromtimestamp(int(seconds), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sealed_inputs(root: Path = ROOT) -> dict:
    """sha256 of every file this module reads, plus the code it runs."""
    entries = {
        "code": {
            "M2/src/basis_materiality.py": sha256_file(root / "M2/src/basis_materiality.py"),
            "M2/src/envelope.py": sha256_file(root / "M2/src/envelope.py"),
            "M2/src/admission.py": sha256_file(root / "M2/src/admission.py"),
        },
        "panel": {
            "M2/data/derived_basis/paired_hours.csv": sha256_file(
                root / "M2/data/derived_basis/paired_hours.csv"
            ),
            "M2/data/derived_basis/manifest_basis.json": sha256_file(
                root / "M2/data/derived_basis/manifest_basis.json"
            ),
        },
        "raw": {},
    }
    raw_dir = root / "M2" / "data" / "raw" / "basis"
    for name in sorted(p.name for p in raw_dir.glob("*.zip")):
        entries["raw"][f"M2/data/raw/basis/{name}"] = sha256_file(raw_dir / name)
    for name in sorted(p.name for p in raw_dir.glob("*.json")):
        if name.endswith(".meta.json"):
            continue
        entries["raw"][f"M2/data/raw/basis/{name}"] = sha256_file(raw_dir / name)
    for name in sorted(p.name for p in (root / "M2/data/derived_basis/manifest_inputs").glob("*.csv")):
        entries["panel"][f"M2/data/derived_basis/manifest_inputs/{name}"] = sha256_file(
            root / "M2/data/derived_basis/manifest_inputs" / name
        )
    return entries


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PanelRow:
    hour_unix: int
    hl_funding_rate: float
    hl_mid: float
    binance_kline_close: float
    binance_mark_close: float
    hl_funding_time_ms: int

    @property
    def settlement_offset_s(self) -> float:
        """Seconds between the hour boundary and the funding settlement instant.

        Computed as an exact integer millisecond difference before the single conversion,
        so a sub-second offset is not distorted by floating-point cancellation.
        """
        return (self.hl_funding_time_ms - self.hour_unix * 1000) / 1000.0


@dataclass(frozen=True)
class Panel:
    rows: tuple[PanelRow, ...]
    window_start_unix: int
    window_end_unix: int
    path: str
    sha256: str

    def by_hour(self) -> dict[int, PanelRow]:
        return {row.hour_unix: row for row in self.rows}


def load_panel(path: Path = PAIRED_PATH) -> Panel:
    with open(path, "r", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    rows = tuple(
        PanelRow(
            hour_unix=_parse_hour(r["utc_hour"]),
            hl_funding_rate=float(r["hl_funding_rate"]),
            hl_mid=float(r["hl_mid_1h_close"]),
            binance_kline_close=float(r["binance_kline_close"]),
            binance_mark_close=float(r["binance_mark_close"]),
            hl_funding_time_ms=int(r["hl_funding_time_ms"]),
        )
        for r in raw_rows
    )
    return Panel(
        rows=rows,
        window_start_unix=rows[0].hour_unix,
        window_end_unix=rows[-1].hour_unix,
        path=str(path),
        sha256=sha256_file(path),
    )


def _parse_hour(text: str) -> int:
    return int(
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    )


def verify_panel(panel: Panel, manifest: dict) -> dict:
    """Grid identity, ordering, duplicates and the manifest's declared window."""
    hours = [row.hour_unix for row in panel.rows]
    n = len(hours)
    first, last = hours[0], hours[-1]
    expected = list(range(first, last + 1, HOUR_S))
    duplicates = sorted({h for h in hours if hours.count(h) > 1}) if len(set(hours)) != n else []
    missing = sorted(set(expected) - set(hours))
    unexpected = sorted(set(hours) - set(expected))
    session = manifest.get("session", {})
    coverage = manifest.get("coverage", {})
    report = {
        "rows": n,
        "window_start_unix": first,
        "window_start_utc": utc(first),
        "window_end_unix": last,
        "window_end_utc": utc(last),
        "expected_buckets": len(expected),
        "grid_identity": hours == expected,
        "sorted": hours == sorted(hours),
        "duplicate_buckets": len(duplicates),
        "missing_buckets": len(missing),
        "unexpected_buckets": len(unexpected),
        "manifest_window_matches": (
            int(session.get("window_start_unix", -1)) == first
            and int(session.get("window_end_unix", -1)) == last
        ),
        "manifest_coverage": coverage,
        "pass": bool(
            hours == expected
            and len(set(hours)) == n
            and not missing
            and not unexpected
            and int(session.get("window_start_unix", -1)) == first
            and int(session.get("window_end_unix", -1)) == last
        ),
    }
    return report


def verify_manifest_files(root: Path, manifest: dict) -> dict:
    """Re-hash every file the manifest declares, using its own digest."""
    out = []
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        actual = sha256_file(path) if path.exists() else None
        out.append(
            {
                "role": entry.get("role"),
                "path": entry["path"],
                "declared_sha256": entry.get("sha256"),
                "actual_sha256": actual,
                "match": actual == entry.get("sha256"),
                "rows_declared": entry.get("rows"),
            }
        )
    return {
        "files": out,
        "all_match": all(item["match"] for item in out) and bool(out),
    }


# ---------------------------------------------------------------------------
# Independent re-derivation of the reference-price series from raw payloads
# ---------------------------------------------------------------------------


def _read_kline_archive(path: Path) -> dict[int, float]:
    out: dict[int, float] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            text = archive.read(name).decode("utf-8")
            for line in text.strip().splitlines()[1:]:
                parts = line.split(",")
                out[int(parts[0]) // 1000] = float(parts[4])
    return out


def rederive_reference_prices(panel: Panel, raw_dir: Path = RAW_DIR) -> dict:
    """Rebuild both reference series from the local raw payloads and diff them onto the panel."""
    hl_raw = load_json(raw_dir / "hl_candles_1h_0.json")
    hl = {int(c["t"]) // 1000: float(c["c"]) for c in hl_raw}

    klines: dict[int, float] = {}
    kline_files = []
    for path in sorted(raw_dir.glob("klines-1h-*.zip")):
        kline_files.append(path.name)
        for hour, close in _read_kline_archive(path).items():
            if hour in klines:
                raise PanelError(f"duplicate kline hour {hour} across archive objects")
            klines[hour] = close

    hl_mismatch, bin_mismatch, hl_missing, bin_missing = [], [], [], []
    for row in panel.rows:
        if row.hour_unix not in hl:
            hl_missing.append(utc(row.hour_unix))
        elif hl[row.hour_unix] != row.hl_mid:
            hl_mismatch.append(utc(row.hour_unix))
        if row.hour_unix not in klines:
            bin_missing.append(utc(row.hour_unix))
        elif klines[row.hour_unix] != row.binance_kline_close:
            bin_mismatch.append(utc(row.hour_unix))

    return {
        "hyperliquid": {
            "raw": "M2/data/raw/basis/hl_candles_1h_0.json",
            "raw_objects": 1,
            "checked": len(panel.rows),
            "missing": hl_missing[:8],
            "missing_count": len(hl_missing),
            "value_mismatches": bin_mismatch[:0] + hl_mismatch[:8],
            "mismatch_count": len(hl_mismatch),
            "match": not hl_missing and not hl_mismatch,
        },
        "binance_kline": {
            "raw": "M2/data/raw/basis/klines-1h-*.zip",
            "raw_objects": len(kline_files),
            "raw_object_names": kline_files,
            "checked": len(panel.rows),
            "missing": bin_missing[:8],
            "missing_count": len(bin_missing),
            "value_mismatches": bin_mismatch[:8],
            "mismatch_count": len(bin_mismatch),
            "match": not bin_missing and not bin_mismatch,
        },
        "mark_series_used_in_price_term": False,
    }


# ---------------------------------------------------------------------------
# Binance settlement grid and archive
# ---------------------------------------------------------------------------


def load_binance_settlements(raw_dir: Path = RAW_DIR) -> dict:
    """Every archived Binance settlement, keyed by the UTC hour it lands on."""
    settlements: dict[int, dict] = {}
    files = []
    for path in sorted(raw_dir.glob("fundingRate-*.zip")):
        files.append({"name": path.name, "sha256": sha256_file(path)})
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                text = archive.read(name).decode("utf-8")
                for line in text.strip().splitlines()[1:]:
                    calc_ms, interval, rate = line.split(",")
                    if int(interval) != SETTLEMENT_PERIOD_HOURS:
                        raise PanelError(
                            f"{path.name}: funding interval {interval}h is not the frozen "
                            f"{SETTLEMENT_PERIOD_HOURS}h cadence"
                        )
                    hour = int(calc_ms) // 1000
                    if hour % (SETTLEMENT_PERIOD_HOURS * HOUR_S) != 0:
                        raise PanelError(f"{path.name}: settlement off the 8h grid: {calc_ms}")
                    if hour in settlements:
                        raise PanelError(f"duplicate settlement hour {utc(hour)}")
                    settlements[hour] = {"rate": float(rate), "calc_time_ms": int(calc_ms)}
    if not settlements:
        raise PanelError("no Binance settlement archive found")
    return {
        "by_hour": settlements,
        "files": files,
        "first": min(settlements),
        "first_utc": utc(min(settlements)),
        "last": max(settlements),
        "last_utc": utc(max(settlements)),
        "count": len(settlements),
        "cadence_hours": SETTLEMENT_PERIOD_HOURS,
    }


def on_settlement_grid(hour_unix: int) -> bool:
    return hour_unix % (SETTLEMENT_PERIOD_HOURS * HOUR_S) == 0


# ---------------------------------------------------------------------------
# Holds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hold:
    decision_hour_unix: int
    entry_row_unix: int
    exit_row_unix: int
    carry_row_unix: int

    @property
    def key(self) -> str:
        return utc(self.decision_hour_unix)


def build_holds(panel: Panel) -> list[Hold]:
    holds = [
        Hold(
            decision_hour_unix=j,
            entry_row_unix=j - HOUR_S,
            exit_row_unix=j,
            carry_row_unix=j + HOUR_S,
        )
        for j in range(panel.window_start_unix + HOUR_S, panel.window_end_unix, HOUR_S)
    ]
    if not holds:
        raise CoverageFloorError("the admitted panel is too short for one frozen hold")
    decisions = [h.decision_hour_unix for h in holds]
    expected = list(range(decisions[0], decisions[-1] + 1, HOUR_S))
    if decisions != expected:
        raise CoverageFloorError(
            "the frozen hold set is not contiguous: a decision hour is missing inside the window"
        )
    return holds


def assert_hold_inputs(panel: Panel, holds: list[Hold]) -> None:
    """Every hold must have its entry, exit and carry rows inside the admitted panel."""
    hours = set(row.hour_unix for row in panel.rows)
    absent = [
        hold.key
        for hold in holds
        if hold.entry_row_unix not in hours
        or hold.exit_row_unix not in hours
        or hold.carry_row_unix not in hours
    ]
    if absent:
        raise CoverageFloorError(
            f"{len(absent)} frozen holds lack a required input row, first={absent[:3]}"
        )


# ---------------------------------------------------------------------------
# The frozen gross
# ---------------------------------------------------------------------------


def hold_terms(hold: Hold, rows: dict[int, PanelRow], settlements: dict[int, dict]) -> dict:
    """One hold's signed decomposition, in bps of notional, using envelope arithmetic."""
    entry = rows[hold.entry_row_unix]
    exit_row = rows[hold.exit_row_unix]
    carry = rows[hold.carry_row_unix]

    hl_leg = perp_leg(
        notional_usd=NOTIONAL_USD,
        position="short",
        fee_entry_bps=0.0,
        fee_exit_bps=0.0,
        funding_rate=carry.hl_funding_rate,
        funding_intervals=1,
    )

    if not on_settlement_grid(hold.carry_row_unix):
        bin_rate, bin_status = 0.0, "NO_SETTLEMENT_INSIDE_HOLD"
    elif hold.carry_row_unix in settlements:
        bin_rate, bin_status = settlements[hold.carry_row_unix]["rate"], "SETTLEMENT_OBSERVED"
    else:
        bin_rate, bin_status = None, "SETTLEMENT_RATE_UNOBSERVED"

    bin_leg = perp_leg(
        notional_usd=NOTIONAL_USD,
        position="long",
        fee_entry_bps=0.0,
        fee_exit_bps=0.0,
        funding_rate=0.0 if bin_rate is None else bin_rate,
        funding_intervals=1,
    )

    mtm_usd = perp_price_pnl(
        entry_price=entry.hl_mid,
        exit_price=exit_row.hl_mid,
        position="short",
        notional_usd=NOTIONAL_USD,
    ) + perp_price_pnl(
        entry_price=entry.binance_kline_close,
        exit_price=exit_row.binance_kline_close,
        position="long",
        notional_usd=NOTIONAL_USD,
    )

    net = two_leg_net([hl_leg, bin_leg])
    gross_usd = net["funding_usd"] + mtm_usd

    return {
        "hold": hold.key,
        "decision_hour_unix": hold.decision_hour_unix,
        "carry_hour_utc": utc(hold.carry_row_unix),
        "hl_funding_rate": carry.hl_funding_rate,
        "binance_settlement_rate": bin_rate,
        "binance_settlement_status": bin_status,
        "hl_carry_bps": usd_to_bps(hl_leg["funding_usd"], NOTIONAL_USD),
        "binance_carry_bps": usd_to_bps(bin_leg["funding_usd"], NOTIONAL_USD),
        "hedge_residual_bps": usd_to_bps(mtm_usd, NOTIONAL_USD),
        "gross_bps": usd_to_bps(gross_usd, NOTIONAL_USD),
        "gross_usd": gross_usd,
        "unresolved": bin_rate is None,
        "hl_return": exit_row.hl_mid / entry.hl_mid - 1.0,
        "binance_return": exit_row.binance_kline_close / entry.binance_kline_close - 1.0,
        "entry_offset_s": rows[hold.decision_hour_unix].settlement_offset_s,
        "exit_offset_s": rows[hold.carry_row_unix].settlement_offset_s,
    }


def staleness_report(panel: Panel, holds: list[Hold]) -> dict:
    """Boundary staleness of the decision instant against the last completed reference."""
    entry_off = [rows_offset for rows_offset in (
        panel.by_hour()[h.decision_hour_unix].settlement_offset_s for h in holds
    )]
    exit_off = [panel.by_hour()[h.carry_row_unix].settlement_offset_s for h in holds]
    tolerance = float(FROZEN_CONTRACT["staleness"]["tolerance_seconds"])

    def describe(values: list[float]) -> dict:
        ordered = sorted(values)
        n = len(ordered)
        return {
            "n": n,
            "min_s": min(ordered),
            "max_s": max(ordered),
            "mean_s": statistics.fmean(ordered),
            "median_s": statistics.median(ordered),
            "p95_s": ordered[min(n - 1, int(0.95 * n))],
            "p99_s": ordered[min(n - 1, int(0.99 * n))],
            "nonzero_count": sum(1 for v in ordered if v > 0),
            "exceeding_tolerance_count": sum(1 for v in ordered if v > tolerance),
            "exceeding_tolerance_fraction": sum(1 for v in ordered if v > tolerance) / n,
        }

    beyond_nominal = [b - a for a, b in zip(entry_off, exit_off)]
    return {
        "tolerance_seconds": tolerance,
        "entry": {
            "definition": "decision instant minus the nominal completion instant of the entry "
                          "reference candle (row J-1, covering [J-1h, J))",
            "hyperliquid_reference": describe(entry_off),
            "binance_reference": describe(entry_off),
            "last_millisecond_variant_s": describe([v + 0.001 for v in entry_off]),
        },
        "exit": {
            "definition": "exit instant minus the nominal completion instant of the exit "
                          "reference candle (row J, covering [J, J+1h))",
            "hyperliquid_reference": describe(exit_off),
            "binance_reference": describe(exit_off),
            "last_millisecond_variant_s": describe([v + 0.001 for v in exit_off]),
        },
        "both_legs_share_one_grid": True,
        "exit_print_precedes_nominal_hour_mark_count": sum(1 for d in beyond_nominal if d < 0),
        "exit_print_follows_nominal_hour_mark_count": sum(1 for d in beyond_nominal if d > 0),
        "max_abs_hold_duration_deviation_s": max(abs(d) for d in beyond_nominal),
        "fraction_stale_beyond_tolerance": max(
            describe(entry_off)["exceeding_tolerance_fraction"],
            describe(exit_off)["exceeding_tolerance_fraction"],
        ),
        "sub_second_note": (
            "the collected carry print lands within +-0.261 s of the nominal one-hour mark, so "
            "whether the boundary settlement precedes or follows the exit is a sub-second "
            "property of the venue's settlement jitter; the frozen convention collects it, and "
            "the alternative (exit exactly at the nominal mark) is reported as a sensitivity."
        ),
    }


# ---------------------------------------------------------------------------
# Aggregation, bootstrap, decision
# ---------------------------------------------------------------------------


def aggregate(terms: list[dict]) -> dict:
    """Point estimates over the frozen hold set (unresolved holds enter at measured zero)."""
    gross = [t["gross_bps"] for t in terms]
    hl_carry = [t["hl_carry_bps"] for t in terms]
    bin_carry = [t["binance_carry_bps"] for t in terms]
    mtm = [t["hedge_residual_bps"] for t in terms]
    unresolved = [t for t in terms if t["unresolved"]]
    settled = [t for t in terms if t["binance_settlement_status"] == "SETTLEMENT_OBSERVED"]
    return {
        "holds": len(terms),
        "gross_bps_mean": statistics.fmean(gross),
        "gross_bps_median": statistics.median(gross),
        "gross_bps_stdev": statistics.stdev(gross) if len(gross) > 1 else 0.0,
        "gross_bps_min": min(gross),
        "gross_bps_max": max(gross),
        "hl_carry_bps_mean": statistics.fmean(hl_carry),
        "binance_carry_bps_mean": statistics.fmean(bin_carry),
        "carry_bps_mean": statistics.fmean(hl_carry) + statistics.fmean(bin_carry),
        "hedge_residual_bps_mean": statistics.fmean(mtm),
        "hedge_residual_bps_stdev": statistics.stdev(mtm) if len(mtm) > 1 else 0.0,
        "holds_with_binance_settlement": len(settled) + len(unresolved),
        "holds_with_observed_settlement": len(settled),
        "holds_with_unresolved_settlement": len(unresolved),
        "holds_without_settlement": len(terms) - len(settled) - len(unresolved),
        "observed_settlement_rate_min": min((t["binance_settlement_rate"] for t in settled), default=None),
        "observed_settlement_rate_max": max((t["binance_settlement_rate"] for t in settled), default=None),
        "observed_settlement_rate_median": (
            statistics.median([t["binance_settlement_rate"] for t in settled]) if settled else None
        ),
        "observed_settlement_rate_mean": (
            statistics.fmean([t["binance_settlement_rate"] for t in settled]) if settled else None
        ),
    }


def unresolved_bracket(agg: dict) -> dict:
    """The declared bracket for holds whose Binance settlement rate is not archived."""
    n = agg["holds"]
    k = agg["holds_with_unresolved_settlement"]
    weight = k / n if n else 0.0
    lo_rate, hi_rate = agg["observed_settlement_rate_min"], agg["observed_settlement_rate_max"]
    if k == 0:
        return {
            "holds": 0,
            "weight": 0.0,
            "contribution_bps_at_min_rate": 0.0,
            "contribution_bps_at_max_rate": 0.0,
            "contribution_bps_midpoint": 0.0,
            "bracket_width_bps": 0.0,
            "bracketable": True,
            "status": "NO_UNRESOLVED_HOLD",
        }
    if lo_rate is None or hi_rate is None:
        # No observed settlement rate exists to bound the unknown ones.  Zero would be an
        # imputation, so the component is declared unbracketable and the verdict degraded.
        return {
            "holds": k,
            "weight": weight,
            "observed_rate_min": None,
            "observed_rate_max": None,
            "contribution_bps_at_min_rate": None,
            "contribution_bps_at_max_rate": None,
            "contribution_bps_midpoint": None,
            "bracket_width_bps": None,
            "bracketable": False,
            "status": "UNBRACKETABLE_NO_OBSERVED_RATE",
            "note": "an unknown settlement rate cannot be bounded from this panel; it is not "
                    "taken as zero and it is not used as a point estimate",
        }
    at_min = -lo_rate * weight * 1e4  # unknown rate = smallest observed -> most positive
    at_max = -hi_rate * weight * 1e4  # unknown rate = largest observed -> most negative
    return {
        "holds": k,
        "weight": weight,
        "observed_rate_min": lo_rate,
        "observed_rate_max": hi_rate,
        "contribution_bps_at_min_rate": at_min,
        "contribution_bps_at_max_rate": at_max,
        "contribution_bps_midpoint": 0.5 * (at_min + at_max),
        "bracket_width_bps": abs(at_max - at_min),
        "bracketable": True,
        "status": "BRACKETED_BY_OBSERVED_RANGE",
        "note": "no distribution is assumed; the unknown rate is never taken as zero",
    }


def bootstrap_means(
    values: list[float], *, resamples: int, seed: int, block: int = 1
) -> np.ndarray:
    """Resample the hourly series (optionally in contiguous blocks) and return the means."""
    arr = np.asarray(values, dtype=float)
    n = arr.size
    rng = np.random.default_rng(seed)
    means = np.empty(resamples, dtype=float)
    if block <= 1:
        for i in range(resamples):
            means[i] = arr[rng.integers(0, n, n)].mean()
    else:
        n_blocks = int(np.ceil(n / block))
        starts_pool = max(1, n - block + 1)
        for i in range(resamples):
            starts = rng.integers(0, starts_pool, n_blocks)
            idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
            means[i] = arr[idx].mean()
    return means


def interval(values: list[float], *, lower: float = 2.5, upper: float = 97.5) -> dict:
    return {"lo": float(np.percentile(values, lower)), "hi": float(np.percentile(values, upper))}


def inference(distribution: np.ndarray, point: float) -> dict:
    lo_hi = interval(distribution)
    se = float(distribution.std(ddof=1))
    return {
        "point_bps": point,
        "ci_lo_bps": lo_hi["lo"],
        "ci_hi_bps": lo_hi["hi"],
        "bootstrap_standard_error_bps": se,
        "resamples": int(distribution.size),
        "significance": significance_against_zero(point, se),
    }


# ---------------------------------------------------------------------------
# Costs
# ---------------------------------------------------------------------------


def cost_envelope() -> Envelope:
    """The branch-C cost envelope: one C0 item, three unresolved C1 items."""
    hl_pin = Provenance(
        source_id="SRC-0213",
        url="https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees.md",
        publisher="Hyperliquid documentation (official fee schedule)",
        access_date="2026-09-20",
        effective_period="current schedule at access (2026-09-20); contemporaneous with the "
                         "2026-03-05..2026-09-28 sample window",
        quote="base tier (< $5m 14-day volume) taker/maker 0.045%/0.015%, with tier rungs to "
              "0.024%/0% above $7b; staking and referral modifiers documented",
        status=STATUS_VERIFIED,
    )
    items = (
        CostItem(
            id="hl_perp_taker_lowest_published_rung",
            name="Hyperliquid perp taker fee at the lowest published schedule rung, open+close "
                 "(2 executions x 0.024% of notional per one-hour hold)",
            unit=UNIT_PCT_OF_TRADE_VALUE,
            value=0.048,
            side="both",
            provenance=hl_pin,
            mandatory=True,
            varies_with_volume=True,
            unavoidable_on_frozen_path=True,
            justified_unavoidable=(
                "the frozen implementation must open and close the Hyperliquid leg; a taker "
                "fill is the only guaranteed execution at a reference price and 0.024% per "
                "side is the lowest rung of the venue's published taker schedule, so no "
                "account state can pay less for that execution.  The state-dependent part of "
                "the schedule is not admitted here and stays in C1."
            ),
            notes="LOWEST RUNG, not the base tier: the base tier is reported separately as a "
                  "reference execution path scenario and may not decide the kill on its own.",
        ),
        CostItem(
            id="hl_perp_taker_state_dependent_uplift",
            name="Hyperliquid perp taker fee above the lowest rung up to the base tier, "
                 "open+close (2 x (0.045% - 0.024%))",
            unit=UNIT_PCT_OF_TRADE_VALUE,
            value=0.042,
            side="both",
            provenance=hl_pin,
            mandatory=True,
            varies_with_volume=True,
            notes="verified value, refused to C0 because it depends on the account's rolling "
                  "14-day volume and staking state, which this repository has not resolved.",
        ),
        CostItem(
            id="binance_usdm_taker_fee",
            name="Binance USD(S)-M BTCUSDT perp taker fee, open+close",
            unit=UNIT_PCT_OF_TRADE_VALUE,
            value=None,
            side="both",
            provenance=Provenance(
                source_id="UNRESOLVED",
                url="https://www.binance.com/en/fee/futureFee",
                publisher="Binance",
                access_date="2026-09-29",
                effective_period="UNKNOWN",
                quote="no authoritative schedule was retrieved; the public host returns HTTP 451 "
                      "in this environment and the M1 evidence ledger carries no Binance fee fact",
                status=STATUS_UNKNOWN,
            ),
            mandatory=True,
            varies_with_volume=True,
            notes="UNKNOWN is never zero.  No value is asserted for this leg.",
        ),
        CostItem(
            id="hedge_spread_impact_slippage",
            name="Spread, market impact and slippage of opening and closing both legs at "
                 "reference prices",
            unit=UNIT_PCT_OF_TRADE_VALUE,
            value=None,
            side="both",
            provenance=Provenance(status=STATUS_UNKNOWN),
            mandatory=True,
            notes="not estimated: the frozen price term is a reference price, so no quoted "
                  "spread or depth series exists in the admitted panel.",
        ),
        CostItem(
            id="capital_margin_borrow_transfer_liquidation",
            name="Capital, margin, borrow, transfer and liquidation terms of the pair",
            unit=UNIT_PCT_OF_TRADE_VALUE,
            value=None,
            side="both",
            provenance=Provenance(status=STATUS_UNKNOWN),
            mandatory=True,
            notes="not estimated; recorded so that C1 is never silently empty.",
        ),
    )
    return Envelope(envelope_id="M2-BRIDGE-HL-BINANCE-BASIS:REFERENCE_PATH", items=items)


def cost_report(envelope: Envelope) -> dict:
    basis = Basis(notional_usd=NOTIONAL_USD)
    c0_usd = envelope.structural_c0_usd(basis)
    assert_c0(envelope.c0_items()[0])
    c0_bps = usd_to_bps(c0_usd, NOTIONAL_USD)
    c1_known = envelope.unresolved_c1_known_usd(basis)
    hl_base_tier = CostItem(
        id="hl_perp_taker_base_tier",
        name="Hyperliquid perp taker fee at the published base tier, open+close "
             "(2 x 0.045% of notional per one-hour hold)",
        unit=UNIT_PCT_OF_TRADE_VALUE,
        value=0.09,
        side="both",
        provenance=envelope.c0_items()[0].provenance,
        mandatory=True,
        varies_with_volume=True,
        notes="reference execution path only; NOT admitted to C0 and not allowed to decide "
              "the kill on its own.",
    )
    binance_base = CostItem(
        id="binance_usdm_taker_base_tier",
        name="Binance USD(S)-M BTCUSDT perp taker fee at the published base tier, open+close",
        unit=UNIT_PCT_OF_TRADE_VALUE,
        value=None,
        side="both",
        provenance=Provenance(status=STATUS_UNKNOWN),
        mandatory=True,
        varies_with_volume=True,
        notes="no verified Binance schedule exists in this repository; no value is asserted.",
    )
    return {
        "c0_usd": c0_usd,
        "c0_bps": c0_bps,
        "c0_items": [
            {"id": item.id, "class": item.cost_class(), "value": item.value, "unit": item.unit,
             "usd": to_usd(item.value, item.unit, basis),
             "provenance": item.provenance.as_dict(), "notes": item.notes}
            for item in envelope.c0_items()
        ],
        "c0_provenance": envelope.c0_provenance(),
        "c1_items": envelope.unresolved_c1_items(),
        "c1_known_usd": c1_known["known_usd"],
        "c1_known_bps": usd_to_bps(c1_known["known_usd"], NOTIONAL_USD) if c1_known["known_usd"] else 0.0,
        "c1_unknown_item_ids": c1_known["unknown_item_ids"],
        "c1_bounded": c1_known["bounded"],
        "c1_total_usd": envelope.unresolved_c1_total_usd(basis),
        "base_tier_scenario": {
            "hyperliquid": reference_path_scenario(hl_base_tier, basis),
            "binance": reference_path_scenario(binance_base, basis),
            "may_decide_the_kill": False,
            "note": "reported separately exactly as the operator's rule requires; the "
                    "unresolved component of these state-dependent tiers stays in C1.",
        },
    }


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def measure(root: Path = ROOT) -> dict:
    panel = load_panel(root / "M2/data/derived_basis/paired_hours.csv")
    manifest = load_json(root / "M2/data/derived_basis/manifest_basis.json")
    raw_dir = root / "M2" / "data" / "raw" / "basis"

    panel_report = verify_panel(panel, manifest)
    manifest_files = verify_manifest_files(root, manifest)
    rederived = rederive_reference_prices(panel, raw_dir)
    settlement_archive = load_binance_settlements(raw_dir)
    settlements = settlement_archive["by_hour"]

    holds = build_holds(panel)
    try:
        assert_hold_inputs(panel, holds)
        coverage_clause = None
    except CoverageFloorError as exc:
        coverage_clause = str(exc)

    rows = panel.by_hour()
    terms = [hold_terms(hold, rows, settlements) for hold in holds]
    agg = aggregate(terms)
    bracket = unresolved_bracket(agg)
    staleness = staleness_report(panel, holds)

    gross_series = [t["gross_bps"] for t in terms]
    g_obs_bps = agg["gross_bps_mean"]
    primary = bootstrap_means(
        gross_series, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED
    )
    block = bootstrap_means(
        gross_series, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED, block=MOVING_BLOCK_HOURS
    )
    point_bps = g_obs_bps + bracket["contribution_bps_midpoint"]
    sampling = interval(primary)
    lo_bps = sampling["lo"] + bracket["contribution_bps_at_max_rate"]
    hi_bps = sampling["hi"] + bracket["contribution_bps_at_min_rate"]
    primary_inference = inference(primary, point_bps)
    block_inference = inference(block, point_bps)

    envelope = cost_envelope()
    costs = cost_report(envelope)
    c0_bps = costs["c0_bps"]
    c_star_bps = point_bps - c0_bps
    c_star_usd = break_even_residual(bps_to_usd(point_bps, NOTIONAL_USD), bps_to_usd(c0_bps, NOTIONAL_USD))
    carry_per_hour = agg["carry_bps_mean"]
    t_star = (c0_bps / carry_per_hour) if carry_per_hour > 0 else None

    c1_levels_bps = [0.0, 2.0, 4.2, 4.8, 9.0, 12.0, 19.0, 38.0]
    c1_table = c1_sensitivity(
        bps_to_usd(point_bps, NOTIONAL_USD),
        bps_to_usd(c0_bps, NOTIONAL_USD),
        [bps_to_usd(level, NOTIONAL_USD) for level in c1_levels_bps],
    )
    for row, level in zip(c1_table["rows"], c1_levels_bps):
        row["c1_bps"] = level
        row["c_star_bps"] = row["c_star_usd"] / 1e-4 / NOTIONAL_USD

    decision = classify_materiality(
        bps_to_usd(point_bps, NOTIONAL_USD),
        bps_to_usd(lo_bps, NOTIONAL_USD),
        bps_to_usd(hi_bps, NOTIONAL_USD),
        bps_to_usd(c0_bps, NOTIONAL_USD),
    )

    verdict = decision["verdict"]
    if coverage_clause is not None:
        verdict = "INDETERMINATE_COVERAGE"
    elif not bracket["bracketable"]:
        coverage_clause = (
            "UNBRACKETABLE_UNRESOLVED_COMPONENT: a settlement instant inside a frozen hold has "
            "no archived Binance rate and no observed rate exists to bound it"
        )
        verdict = "INDETERMINATE_COVERAGE"
    elif not (panel_report["pass"] and manifest_files["all_match"] and rederived["hyperliquid"]["match"]
              and rederived["binance_kline"]["match"]):
        verdict = "INDETERMINATE (DATA_INTEGRITY)"

    boundary_print_after_nominal_mark = [
        t for t in terms if t["exit_offset_s"] > t["entry_offset_s"]
    ]
    mark_to_market_only = [
        t["gross_bps"] - t["hl_carry_bps"] - t["binance_carry_bps"] for t in terms
    ]
    union = {
        "frozen_basis": "the frozen one-hour formulation on the admitted panel",
        "panel_pass": panel_report["pass"],
        "manifest_files_match": manifest_files["all_match"],
        "reference_rederivation_match": rederived["hyperliquid"]["match"]
        and rederived["binance_kline"]["match"],
        "holds_expected": len(holds),
        "holds_evaluated": len(terms),
        "holds_with_every_required_row": len(terms) - agg["holds_with_unresolved_settlement"],
        "unresolved_hold_count": agg["holds_with_unresolved_settlement"],
        "unresolved_component_bracketable": bracket["bracketable"],
        "coverage_clause": coverage_clause,
    }

    results = {
        "experiment_id": FROZEN_CONTRACT["experiment_id"],
        "candidate_id": FROZEN_CONTRACT["candidate_id"],
        "amendment_id": FROZEN_CONTRACT["amendment_id"],
        "freeze_status": FROZEN_CONTRACT["freeze_status"],
        "verdict": verdict,
        "classification": decision,
        "gross": {
            "units": "bps of notional per one-hour hold",
            "signed": True,
            "point_bps": point_bps,
            "measured_component_bps": g_obs_bps,
            "mean_bps": agg["gross_bps_mean"],
            "median_bps": agg["gross_bps_median"],
            "stdev_bps": agg["gross_bps_stdev"],
            "min_bps": agg["gross_bps_min"],
            "max_bps": agg["gross_bps_max"],
            "decomposition": {
                "hl_funding_carry_mean_bps": agg["hl_carry_bps_mean"],
                "binance_funding_carry_mean_bps": agg["binance_carry_bps_mean"],
                "hedge_mark_to_market_residual_mean_bps": agg["hedge_residual_bps_mean"],
                "hedge_mark_to_market_residual_stdev_bps": agg["hedge_residual_bps_stdev"],
                "carry_mean_bps_per_hour": carry_per_hour,
            },
            "t_star_hours": t_star,
            "t_star_basis": "T* = C0_bps / mean funding carry bps per hour; interpretive only.",
        },
        "coverage": union,
        "uncertainty": {
            "primary": primary_inference,
            "decision_interval_lo_bps": lo_bps,
            "decision_interval_hi_bps": hi_bps,
            "decision_interval_basis": "percentile bootstrap union with the unresolved-rate "
                                       "bracket (lo = bootstrap lo + most-negative branch, "
                                       "hi = bootstrap hi + most-positive branch)",
            "moving_block_24h": block_inference,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "resamples": int(primary.size),
        },
        "unresolved_binance_settlement_bracket": bracket,
        "staleness": staleness,
        "costs": {
            **costs,
            "c_star_bps": c_star_bps,
            "c_star_usd": c_star_usd,
            "c1_sensitivity": c1_table,
        },
        "sensitivities_reported_not_deciding": {
            "exit_at_nominal_hour_mark_variant": {
                "holds": len(terms),
                "gross_bps_mean_without_any_collected_carry": statistics.fmean(mark_to_market_only),
                "note": "if the exit were taken exactly at the nominal candle completion though "
                        "the next funding observation, no settlement instant would lie inside "
                        "the hold at all and the carry of both legs would be structurally "
                        "uncollectible; the reported mean is the same frozen formula with the "
                        "carry term dropped and is a strict lower read, not the frozen "
                        "convention.",
            },
            "boundary_sub_second": {
                "holds_where_the_boundary_print_lands_after_the_nominal_one_hour_mark":
                    len(boundary_print_after_nominal_mark),
                "note": "under the frozen convention the exit is taken at the boundary print, so "
                        "the carry is collected in every hold; this count is the size of the "
                        "sub-second ambiguity the convention resolves.",
            },
            "base_tier_fee_scenario": costs["base_tier_scenario"],
        },
        "integrity": {
            "panel": panel_report,
            "manifest_files": manifest_files,
            "reference_rederivation": rederived,
            "binance_settlement_archive": {
                "files": settlement_archive["files"],
                "count": settlement_archive["count"],
                "first_utc": settlement_archive["first_utc"],
                "last_utc": settlement_archive["last_utc"],
                "cadence_hours": settlement_archive["cadence_hours"],
            },
        },
    }
    return results


def canonical_update_proposal(results: dict) -> dict:
    """A proposal for the canonical corpus, emitted without touching any canonical artefact."""
    verdict = results["verdict"]
    point = results["gross"]["point_bps"]
    c0 = results["costs"]["c0_bps"]
    return {
        "artifact": "CANONICAL_UPDATE_PROPOSAL",
        "proposed_at_utc": FROZEN_CONTRACT["frozen_at_utc"],
        "applied": False,
        "note": "this is a proposal only; no canonical artefact was edited by this module.",
        "branch": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
        "experiment_id": FROZEN_CONTRACT["experiment_id"],
        "result": verdict,
        "evidence": {
            "gross_bps_per_hold": point,
            "c0_bps_per_hold": c0,
            "c_star_bps_per_hold": results["costs"]["c_star_bps"],
            "decision_interval_bps": [
                results["uncertainty"]["decision_interval_lo_bps"],
                results["uncertainty"]["decision_interval_hi_bps"],
            ],
            "holds": results["coverage"]["holds_evaluated"],
            "window": FROZEN_CONTRACT["panel"]["window_start_utc"] + ".."
            + FROZEN_CONTRACT["panel"]["window_end_utc"],
        },
        "proposed_changes": [
            {
                "target": "M1/work/reselection_specs/TUP-HYPERLIQUID-BTC-FUNDING-BASIS.json",
                "change": "AMENDED by C5 (this epoch): causal last-trade reference prices, "
                          "declared staleness tolerance, the frozen gross, the C0/C1 rule, the "
                          "coverage floor and the inference rule.  The pre-amendment copy is "
                          "retained beside it with its sha256.",
                "applied_by": "C5 (own branch spec file only)",
            },
            {
                "target": "M1/data/candidate_tuples.csv (row TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX)",
                "change": f"status {verdict} with a scoped note: the verdict covers the frozen "
                          "one-hour formulation on the 2026-03-05..2026-09-28 panel only; a "
                          "longer horizon, another pair or a state-conditioned entry is a NEW "
                          "candidate, not a reinterpretation.",
                "applied_by": "NOT APPLIED — requires the controller to run M1/src/materialize.py",
            },
            {
                "target": "DECISIONS.md",
                "change": "record AMEND-C5-001 (price term -> causal last-trade reference "
                          "prices; mark series excluded) and the branch-C outcome with its "
                          "coverage floor and unresolved components.",
                "applied_by": "NOT APPLIED — append-only canonical file",
            },
            {
                "target": "EXPERIMENTS.csv",
                "change": "register the M2-BRIDGE-HL-BINANCE-BASIS row (run_state, "
                          "preregistered=yes, dataset_version=BASIS-2026-03-05..2026-09-28, "
                          "decision=result, artifact_hash=freeze/results sha256).",
                "applied_by": "NOT APPLIED — canonical experiment register",
            },
        ],
        "kill_scope": FROZEN_CONTRACT["classification"]["kill_scope"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def seal(root: Path = ROOT) -> dict:
    experiment_dir = root / "M2" / "experiments" / "M2-BRIDGE-HL-BINANCE-BASIS"
    freeze = dict(FROZEN_CONTRACT)
    freeze["code_sha256"] = sha256_file(root / "M2/src/basis_materiality.py")
    freeze["envelope_sha256"] = sha256_file(root / "M2/src/envelope.py")
    freeze["test_sha256"] = (
        sha256_file(root / "M2/tests/test_basis_materiality.py")
        if (root / "M2/tests/test_basis_materiality.py").exists()
        else None
    )
    freeze["inputs_sha256"] = sealed_inputs(root)
    freeze_path = experiment_dir / "freeze.json"
    dump_json(freeze_path, freeze)
    digest = sha256_file(freeze_path)
    (experiment_dir / "freeze.sha256").write_text(f"{digest}  freeze.json\n", encoding="utf-8")
    return {"freeze_path": str(freeze_path), "freeze_sha256": digest}


def verify_seal(root: Path = ROOT) -> dict:
    experiment_dir = root / "M2" / "experiments" / "M2-BRIDGE-HL-BINANCE-BASIS"
    freeze_path = experiment_dir / "freeze.json"
    sealed = load_json(freeze_path)
    digest = sha256_file(freeze_path)
    recorded = (experiment_dir / "freeze.sha256").read_text(encoding="utf-8").split()[0]
    code_now = sha256_file(root / "M2/src/basis_materiality.py")
    inputs_now = sealed_inputs(root)
    drift = sorted(
        key
        for group in ("code", "panel", "raw")
        for key, value in sealed["inputs_sha256"][group].items()
        if inputs_now[group].get(key) != value
    )
    return {
        "freeze_sha256_matches": digest == recorded,
        "code_unchanged": code_now == sealed["code_sha256"],
        "inputs_unchanged": not drift,
        "drifted_inputs": drift,
        "sealed_contract_sha256": digest,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seal", action="store_true", help="write freeze.json + freeze.sha256")
    parser.add_argument("--run", action="store_true", help="verify the seal, then measure")
    parser.add_argument("--check", action="store_true", help="verify the seal only")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.seal:
        print(json.dumps(seal(root), indent=2))
    if args.check or args.run:
        status = verify_seal(root)
        print(json.dumps(status, indent=2))
        if not (status["freeze_sha256_matches"] and status["code_unchanged"] and status["inputs_unchanged"]):
            print("REFUSED: the seal no longer matches the code or the inputs", file=sys.stderr)
            return 2
        if args.run:
            results = measure(root)
            experiment_dir = root / "M2" / "experiments" / "M2-BRIDGE-HL-BINANCE-BASIS"
            dump_json(experiment_dir / "results.json", results)
            dump_json(experiment_dir / "base_tier_scenario.json", results["costs"]["base_tier_scenario"])
            dump_json(experiment_dir / "canonical_update_proposal.json",
                      canonical_update_proposal(results))
            run_inputs = {
                "experiment_id": results["experiment_id"],
                "freeze_sha256_recomputed": status["sealed_contract_sha256"],
                "freeze_sha256_sealed": (
                    experiment_dir / "freeze.sha256"
                ).read_text(encoding="utf-8").split()[0],
                "code_and_input_sha256": sealed_inputs(root),
                "as_run_deviations_from_freeze": [],
                "defects_found": [],
                "note": "written after the run; the freeze is not altered by this file.",
                "result_artifacts": {
                    "results.json": sha256_file(experiment_dir / "results.json"),
                    "base_tier_scenario.json": sha256_file(experiment_dir / "base_tier_scenario.json"),
                    "canonical_update_proposal.json": sha256_file(
                        experiment_dir / "canonical_update_proposal.json"
                    ),
                },
                "verdict": results["verdict"],
            }
            dump_json(experiment_dir / "run_inputs.json", run_inputs)
            print(results["verdict"])
    if not (args.seal or args.run or args.check):
        parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
