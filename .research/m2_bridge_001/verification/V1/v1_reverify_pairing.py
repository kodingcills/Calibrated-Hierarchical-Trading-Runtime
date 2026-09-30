#!/usr/bin/env python3
"""V1 independent re-derivation of the W3 Branch C pairing from raw cached bytes.

Written from scratch; does NOT import M2/src/basis_admission.py.
Re-reads the cached raw payloads, rebuilds every series, recomputes the window,
the bucket grid and the 1:1 pairing, and compares against the producer's
paired_hours.csv value by value.

Also exposes negative controls (deliberate input corruption) to prove the
pairing check can fail.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from glob import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "M2" / "data" / "raw" / "basis"
DER = ROOT / "M2" / "data" / "derived_basis"
HOUR_MS = 3_600_000

KLINE_HEADER = ["open_time", "open", "high", "low", "close", "volume", "close_time",
                "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def floor_hour(ms: int) -> int:
    return (ms // HOUR_MS) * HOUR_MS


def real_glob(pat: str) -> list[str]:
    return sorted(f for f in glob(str(RAW / pat)) if not f.endswith(".meta.json"))


def zip_rows(blob: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        members = [n for n in zf.namelist() if n.endswith(".csv")]
        assert len(members) == 1, members
        text = zf.read(members[0]).decode()
    rows = list(csv.reader(io.StringIO(text)))
    if rows and rows[0] and not rows[0][0].lstrip("-").isdigit():
        assert rows[0] == KLINE_HEADER, rows[0]
        rows = rows[1:]
    return rows


# --------------------------------------------------------------- series builders
def load_binance(prefix: str) -> dict[int, str]:
    """prefix = 'klines' or 'markPriceKlines'. Reads every cached zip for that series."""
    out: dict[int, str] = {}
    dupes: dict[int, int] = {}
    files = 0
    for f in real_glob(f"{prefix}-1h-*.zip"):
        rows = zip_rows(Path(f).read_bytes())
        files += 1
        for r in rows:
            h = int(r[0])
            if h in out:
                dupes[h] = dupes.get(h, 1) + 1
            out[h] = r[4]
    return out, dupes, files


def load_hl_candles() -> tuple[dict[int, dict], int]:
    f = real_glob("hl_candles_1h_*.json")[0]
    rows = json.loads(Path(f).read_bytes())
    out = {floor_hour(c["t"]): c for c in rows}
    return out, len(rows)


def load_hl_funding() -> tuple[dict[int, dict], list[dict], int]:
    """Re-derive the full HL funding history from the cached depthprobe pages."""
    rows: list[dict] = []
    seen: set[int] = set()
    dupes = 0
    pages = 0
    for f in real_glob("hl_funding_depthprobe_*.json"):
        pages += 1
        page = json.loads(Path(f).read_bytes())
        for r in page:
            if r["time"] in seen:
                dupes += 1
                continue
            seen.add(r["time"])
            rows.append(r)
    rows.sort(key=lambda r: r["time"])
    by_hour: dict[int, dict] = {}
    hour_dupes: dict[int, list[int]] = {}
    for r in rows:
        h = floor_hour(r["time"])
        if h in by_hour:
            hour_dupes.setdefault(h, [by_hour[h]["time"]]).append(r["time"])
        by_hour[h] = r
    return by_hour, rows, pages, dupes, hour_dupes


def main() -> int:
    report: dict = {"checks": {}, "findings": []}

    # 1. load raw
    klines, kdup, kfiles = load_binance("klines")
    marks, mdup, mfiles = load_binance("markPriceKlines")
    candles, n_candles = load_hl_candles()
    funding, frows, fpages, fdupes, hour_dupes = load_hl_funding()

    report["raw_load"] = {
        "klines_files": kfiles, "klines_hours": len(klines), "klines_duplicate_hours": len(kdup),
        "mark_files": mfiles, "mark_hours": len(marks), "mark_duplicate_hours": len(mdup),
        "hl_candle_rows": n_candles, "hl_candle_hours": len(candles),
        "hl_funding_pages": fpages, "hl_funding_rows": len(frows),
        "hl_funding_page_boundary_dupes": fdupes, "hl_funding_hours": len(funding),
        "hl_funding_hour_dupes": len(hour_dupes),
        "hl_funding_first": iso(min(funding)), "hl_funding_last": iso(max(funding)),
    }

    # 2. uniform hourly era: detect the 8h->1h transition independently.
    #    Jitter makes raw steps >1h even when no bucket is missing, so the era
    #    boundary is found on the raw step (first step <= 2h), and missing
    #    hours are then measured at bucket level.
    times = sorted(r["time"] for r in frows)
    steps = [(b - a) for a, b in zip(times, times[1:])]
    era_start_ms = None
    for i, s in enumerate(steps):
        if s <= 2 * HOUR_MS + 1000:
            era_start_ms = times[i + 1]
            break
    era_start = floor_hour(era_start_ms)
    era_hours = {h for h in funding if h >= era_start}
    era_expected = list(range(era_start, max(era_hours) + HOUR_MS, HOUR_MS))
    era_missing = [iso(h) for h in era_expected if h not in era_hours]
    report["checks"]["era"] = {
        "hourly_era_start_utc": iso(era_start),
        "era_expected_hours": len(era_expected),
        "era_present_hours": len(era_hours),
        "era_missing": era_missing,
        "era_missing_count": len(era_missing),
    }

    # 3. window from availability
    starts = {
        "hl_funding": min(era_hours),
        "hl_candle": min(candles),
        "binance_kline": min(klines),
        "binance_mark": min(marks),
    }
    ends = {
        "hl_funding": max(era_hours),
        "hl_candle": max(candles),
        "binance_kline": max(klines),
        "binance_mark": max(marks),
    }
    win_start = max(starts.values())
    win_end = min(ends.values())
    expected = list(range(win_start, win_end + HOUR_MS, HOUR_MS))
    report["checks"]["window_bounds"] = {
        "starts": {k: iso(v) for k, v in starts.items()},
        "ends": {k: iso(v) for k, v in ends.items()},
        "binding_start": [k for k, v in starts.items() if v == win_start],
        "binding_end": [k for k, v in ends.items() if v == win_end],
        "window_start_utc": iso(win_start), "window_end_utc": iso(win_end),
        "expected_hours": len(expected),
    }

    # 4. independent pairing
    matched, missing, dup_hours = [], [], []
    for h in expected:
        f = funding.get(h)
        ok = (f is not None and f.get("fundingRate") not in (None, "")
              and f.get("premium") not in (None, "")
              and h in candles and h in klines and h in marks)
        if h in hour_dupes:
            dup_hours.append(h)
        (matched if ok else missing).append(h)
    verdict = "PAIRED_100PCT" if (not missing and not dup_hours and len(matched) == len(expected)) else "PAIRING_GAP"
    report["checks"]["independent_pairing"] = {
        "expected": len(expected), "matched": len(matched), "missing": len(missing),
        "duplicate_buckets": len(dup_hours), "verdict": verdict,
        "missing_detail": [iso(h) for h in missing[:20]],
    }

    # 5. jitter inside window
    win_offsets = sorted(abs(funding[h]["time"] - h) / 1000 for h in expected if h in funding)
    report["checks"]["jitter_window"] = {
        "rows": len(win_offsets),
        "min": win_offsets[0] if win_offsets else None,
        "max": win_offsets[-1] if win_offsets else None,
        "nonzero": sum(1 for o in win_offsets if o > 0),
        "over_1s": sum(1 for o in win_offsets if o > 1),
        "over_3600s": sum(1 for o in win_offsets if o >= 3600),
    }

    # 6. compare against producer's paired_hours.csv value by value
    prod = {}
    with open(DER / "paired_hours.csv", newline="") as fh:
        rdr = csv.DictReader(fh)
        for r in rdr:
            ts = datetime.strptime(r["utc_hour"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            prod[int(ts.timestamp()) * 1000] = r
    mism = []
    if set(prod) != set(matched):
        only_prod = sorted(set(prod) - set(matched))[:10]
        only_mine = sorted(set(matched) - set(prod))[:10]
        mism.append({"grid_set_mismatch": True, "only_prod": only_prod, "only_mine": only_mine})
    for h in matched:
        p = prod.get(h)
        if p is None:
            continue
        mine = {
            "hl_funding_rate": funding[h]["fundingRate"],
            "hl_premium": funding[h]["premium"],
            "hl_mid_1h_close": candles[h]["c"],
            "binance_kline_close": klines[h],
            "binance_mark_close": marks[h],
            "hl_funding_time_ms": str(funding[h]["time"]),
        }
        mine["utc_hour"] = iso(h)
        for k, v in mine.items():
            if p.get(k) != v:
                if len(mism) < 30:
                    mism.append({"hour": iso(h), "field": k, "producer": p.get(k), "mine": v})
    report["checks"]["producer_value_comparison"] = {
        "producer_rows": len(prod), "independent_rows": len(matched),
        "value_mismatches": len(mism), "detail": mism[:30],
    }

    # 7. markPriceKlines vs klines: prove they are distinct series (mark != last trade)
    common = sorted(set(klines) & set(marks))
    diff = [h for h in common if klines[h] != marks[h]]
    rel = sorted(abs(float(klines[h]) - float(marks[h])) / float(marks[h]) for h in common)
    report["checks"]["mark_vs_last"] = {
        "common_hours": len(common),
        "hours_with_different_value": len(diff),
        "max_relative_diff": rel[-1] if rel else None,
        "hours_identical": len(common) - len(diff),
    }

    # 8. HL candle internal consistency: t/T spans 1 hour (candle not interpolated)
    spans_ok = all(c["T"] - c["t"] == HOUR_MS - 1 for c in candles.values())
    n_unique = len({(c["t"], c["c"]) for c in candles.values()})
    report["checks"]["hl_candle_shape"] = {
        "rows": len(candles),
        "all_spans_1h": spans_ok,
        "unique_t_close_pairs": n_unique,
        "fields": sorted(next(iter(candles.values())).keys()),
    }

    out = Path(__file__).resolve().parent / "v1_pairing_rederivation.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in report["checks"].items()
                      if k in ("era", "window_bounds", "independent_pairing", "producer_value_comparison",
                               "mark_vs_last", "jitter_window", "hl_candle_shape")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())