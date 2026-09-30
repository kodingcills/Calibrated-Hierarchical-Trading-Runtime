#!/usr/bin/env python3
"""Branch C availability-window + 100%-hourly-pairing admission (DATA ONLY).

Frozen pair under admission: SHORT Hyperliquid Core BTC linear perpetual /
LONG equal-BTC-notional Binance USD(S)-M BTCUSDT perpetual
(candidate TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX).

This module answers exactly two pre-economic questions:

  1. AVAILABILITY -- for which contiguous UTC hours do all required fields
     exist, per source?  Required fields (assignment W3 step 1):
        HL  fundingRate + premium   (POST /info type=fundingHistory, 500-row pages)
        HL  1h candle close (mid)   (POST /info type=candleSnapshot, ~5000-candle cap)
        BIN markPriceKlines 1h close (data.binance.vision archive)
        BIN klines 1h close          (data.binance.vision archive)
  2. PAIRING -- inside the availability-derived intersection, do the hourly
     buckets match 1:1 with zero missing and zero duplicates?

PAIRING REPAIR.  Hyperliquid funding `time` is a millisecond settlement instant
that carries sub-second jitter (observed 0.003-0.201 s).  Exact-millisecond
equality silently drops rows; the repaired rule floors every timestamp to the
exact UTC hour by integer division (ms // 3_600_000) before matching.

NO ECONOMIC OUTCOME IS COMPUTED OR INSPECTED HERE: no carry, no P&L, no
funding-differential magnitude, no fee arithmetic.  Only required-field presence,
row presence, hashes and pairing counts.

Anonymous public endpoints only: no credentials, no signup, no paid tier.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HL_INFO = "https://api.hyperliquid.xyz/info"
BINANCE_BASE = "https://data.binance.vision/data/futures/um"
COIN = "BTC"
SYMBOL = "BTCUSDT"
HOUR_MS = 3_600_000

RAW_DIR = ROOT / "M2" / "data" / "raw" / "basis"
OUT_DIR = ROOT / "M2" / "data" / "derived_basis"
PRIOR_PROBE_CSV = ROOT / ".research" / "m2_bridge_001" / "probes" / "probe_c_join_2026-06_2026-08.csv"

KLINE_HEADER = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]
FUNDING_HEADER = ["calc_time", "funding_interval_hours", "last_funding_rate"]

PAIRING_RULE = (
    "bucket_ms = timestamp_ms // 3600000 (integer division, i.e. floor to the exact UTC hour); "
    "each source contributes at most one value per bucket; a bucket is MATCHED only if every "
    "required field is present in it; duplicate bucket = a source yields two rows in one bucket; "
    "missing bucket = a bucket inside the window lacks at least one required field. "
    "No imputation, no post-hoc window shrinking."
)

REQUEST_LOG: list[dict] = []


# --------------------------------------------------------------------------- http

def _http(url, *, method="GET", payload=None, headers=None, attempts=4, timeout=90):
    """One anonymous request with bounded retries. 404 is returned, not retried blindly."""
    body = json.dumps(payload).encode() if payload is not None else None
    hdrs = {"User-Agent": "cht-runtime/epoch1-w3-admission"}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    last = None
    for k in range(attempts):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                blob = r.read()
                return {
                    "status": r.status,
                    "body": blob,
                    "content_range": r.headers.get("Content-Range"),
                    "elapsed_ms": int((time.time() - t0) * 1000),
                    "attempts": k + 1,
                }
        except urllib.error.HTTPError as e:
            blob = e.read()
            if e.code in (404, 416):
                return {
                    "status": e.code,
                    "body": blob,
                    "content_range": e.headers.get("Content-Range") if e.headers else None,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                    "attempts": k + 1,
                }
            last = f"HTTP {e.code}: {blob[:200]!r}"
        except Exception as e:  # noqa: BLE001 - network layer, retried below
            last = repr(e)
        if k + 1 < attempts:
            time.sleep(1.0 * (k + 1))
    raise RuntimeError(f"request failed after {attempts} attempts: {url} :: {last}")


def _record(meta: dict) -> dict:
    REQUEST_LOG.append({
        "name": meta["name"],
        "url": meta["url"],
        "method": meta["method"],
        "http_status": meta["http_status"],
        "bytes": meta["bytes"],
        "sha256": meta.get("sha256"),
        "retrieved_utc": meta.get("retrieved_utc"),
        "cache_reused": meta.get("cache_reused", False),
    })
    return meta


def fetch_cached(name: str, url: str, *, method="GET", payload=None) -> tuple[bytes, dict]:
    """Fetch once, cache raw bytes + provenance sidecar under the gitignored raw path."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cpath, mpath = RAW_DIR / name, RAW_DIR / f"{name}.meta.json"
    if cpath.exists() and mpath.exists():
        meta = json.loads(mpath.read_text())
        meta["cache_reused"] = True
        return cpath.read_bytes(), _record(meta)
    res = _http(url, method=method, payload=payload)
    blob = res["body"]
    meta = {
        "name": name,
        "url": url,
        "method": method,
        "payload": payload,
        "http_status": res["status"],
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_ms": res["elapsed_ms"],
        "attempts": res["attempts"],
        "cache_reused": False,
    }
    if res["status"] != 200:
        meta["note"] = "non-200; not cached"
        return blob, _record(meta)
    cpath.write_bytes(blob)
    mpath.write_text(json.dumps(meta, indent=2, sort_keys=True))
    return blob, _record(meta)


def probe_exists(url: str) -> dict:
    """Existence probe via range GET (this host rejects HEAD; range GET is authoritative)."""
    res = _http(url, headers={"Range": "bytes=0-1023"}, attempts=2)
    total = None
    cr = res["content_range"]
    if cr and "/" in cr:
        tail = cr.rsplit("/", 1)[1].strip()
        if tail.isdigit():
            total = int(tail)
    rec = {
        "url": url,
        "method": "GET (Range: bytes=0-1023)",
        "status": res["status"],
        "content_range": cr,
        "total_bytes": total,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    REQUEST_LOG.append({**rec, "name": "probe", "http_status": res["status"], "bytes": total,
                        "sha256": None, "cache_reused": False})
    return rec


# ------------------------------------------------------------------ time helpers

def floor_hour_ms(ms: int) -> int:
    return (ms // HOUR_MS) * HOUR_MS


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_ms(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)


# ------------------------------------------------------------- binance archive

def _zip_rows(blob: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        members = [n for n in zf.namelist() if n.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected exactly one csv member, got {members}")
        text = zf.read(members[0]).decode()
    return list(csv.reader(io.StringIO(text)))


def _strip_header(rows: list[list[str]], expected: list[str]) -> tuple[list[list[str]], list[str]]:
    if not rows:
        return [], []
    if rows[0] and not rows[0][0].lstrip("-").isdigit():
        header = rows[0]
        if header != expected:
            raise ValueError(f"unexpected csv header: {header}")
        return rows[1:], header
    return rows, []


def binance_url(kind: str, freq: str, ym_or_date: str) -> str:
    if kind == "fundingRate":
        return f"{BINANCE_BASE}/{freq}/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{ym_or_date}.zip"
    return f"{BINANCE_BASE}/{freq}/{kind}/{SYMBOL}/1h/{SYMBOL}-1h-{ym_or_date}.zip"


def month_hours(ym: str) -> list[int]:
    y, m = (int(x) for x in ym.split("-"))
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=timezone.utc)
    n = int((end - start).total_seconds() // 3600)
    return [int(start.timestamp() * 1000) + i * HOUR_MS for i in range(n)]


def day_hours(day: str) -> list[int]:
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return [int(start.timestamp() * 1000) + i * HOUR_MS for i in range(24)]


class BinanceHourlySeries:
    """A 1h Binance archive series keyed by floored UTC hour."""

    def __init__(self, kind: str):
        self.kind = kind
        self.hours: dict[int, str] = {}
        self.duplicate_hours: dict[int, list[str]] = {}
        self.files: list[dict] = []
        self.repairs: list[dict] = []

    def add_file(self, *, label: str, freq: str, tag: str, rows: list[list[str]], expect: list[int],
                 url: str, meta: dict, header: list[str]) -> None:
        values = {int(r[0]): r[4] for r in rows}
        got = sorted(values)
        exp_set, got_set = set(expect), set(got)
        contiguous = all(b - a == HOUR_MS for a, b in zip(got, got[1:]))
        record = {
            "label": label,
            "frequency": freq,
            "tag": tag,
            "url": url,
            "http_status": meta["http_status"],
            "bytes": meta["bytes"],
            "sha256": meta["sha256"],
            "retrieved_utc": meta["retrieved_utc"],
            "cache_reused": meta.get("cache_reused", False),
            "header_verified": header == KLINE_HEADER,
            "expected_rows": len(expect),
            "actual_rows": len(rows),
            "row_count_ok": len(rows) == len(expect),
            "missing_hours": [iso(h) for h in sorted(exp_set - got_set)],
            "unexpected_hours": [iso(h) for h in sorted(got_set - exp_set)],
            "grid_contiguous": contiguous,
        }
        self.files.append(record)
        for h, v in values.items():
            if h in self.hours:
                self.duplicate_hours.setdefault(h, [self.hours[h]]).append(v)
            self.hours[h] = v

    def missing_in(self, expected_hours: list[int]) -> list[int]:
        return [h for h in expected_hours if h not in self.hours]

    def repair_from_daily(self, missing: list[int]) -> None:
        """Fetch daily files for the dates of `missing` hours and fill the holes."""
        by_day: dict[str, list[int]] = {}
        for h in missing:
            by_day.setdefault(datetime.fromtimestamp(h / 1000, tz=timezone.utc).strftime("%Y-%m-%d"), []).append(h)
        for day in sorted(by_day):
            tag = f"{self.kind}-1h-{day}"
            url = binance_url(self.kind, "daily", day)
            blob, meta = fetch_cached(f"{tag}.zip", url)
            if meta["http_status"] != 200:
                self.repairs.append({"tag": tag, "url": url, "http_status": meta["http_status"],
                                     "filled": [], "note": "daily repair file unavailable"})
                continue
            rows, header = _strip_header(_zip_rows(blob), KLINE_HEADER)
            hours = set(by_day[day])
            filled = [r for r in rows if int(r[0]) in hours]
            for r in filled:
                self.hours[int(r[0])] = r[4]
            self.repairs.append({
                "tag": tag, "url": url, "http_status": meta["http_status"], "bytes": meta["bytes"],
                "sha256": meta["sha256"], "retrieved_utc": meta["retrieved_utc"],
                "header_verified": header == KLINE_HEADER,
                "daily_rows": len(rows),
                "hours_needed": [iso(h) for h in sorted(hours)],
                "filled": [iso(int(r[0])) for r in filled],
            })
            self.files.append({
                "label": f"daily-repair {tag}", "frequency": "daily", "tag": tag, "url": url,
                "http_status": meta["http_status"], "bytes": meta["bytes"], "sha256": meta["sha256"],
                "retrieved_utc": meta["retrieved_utc"], "cache_reused": meta.get("cache_reused", False),
                "header_verified": header == KLINE_HEADER, "expected_rows": 24, "actual_rows": len(rows),
                "row_count_ok": len(rows) == 24,
                "missing_hours": [iso(h) for h in sorted(set(day_hours(day)) - {int(r[0]) for r in rows})],
                "unexpected_hours": [], "grid_contiguous": True, "role": "repair",
            })

    def span(self, hours: list[int] | None = None) -> dict:
        pool = self.hours if hours is None else {h: self.hours[h] for h in hours if h in self.hours}
        if not pool:
            return {"available": False}
        keys = sorted(pool)
        return {
            "available": True,
            "earliest_hour_utc": iso(keys[0]),
            "latest_hour_utc": iso(keys[-1]),
            "hours_present": len(keys),
            "earliest_ms": keys[0],
            "latest_ms": keys[-1],
        }


# -------------------------------------------------------------- hyperliquid api

def hl_candles(start_ms: int = 0) -> tuple[list[dict], dict]:
    payload = {"type": "candleSnapshot", "req": {"coin": COIN, "interval": "1h", "startTime": start_ms}}
    blob, meta = fetch_cached(f"hl_candles_1h_{start_ms}.json", HL_INFO, method="POST", payload=payload)
    rows = json.loads(blob)
    meta["canonical_sha256"] = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return rows, meta


def hl_funding(start_ms: int, end_ms: int | None, tag: str) -> tuple[list[dict], list[dict], int]:
    """Page fundingHistory at 500 rows/request, chaining on the last returned timestamp.

    Returns (rows, page_metas, duplicate_rows_dropped).  Chaining on the last returned
    timestamp deliberately re-reads one row per page boundary; those repeats are counted.
    """
    rows: list[dict] = []
    metas: list[dict] = []
    seen: set[int] = set()
    dupes = 0
    cur = start_ms
    guard = 0
    while guard < 400:
        guard += 1
        payload = {"type": "fundingHistory", "coin": COIN, "startTime": cur}
        if end_ms is not None:
            payload["endTime"] = end_ms
        blob, meta = fetch_cached(f"hl_funding_{tag}_{cur}.json", HL_INFO, method="POST", payload=payload)
        page = json.loads(blob)
        meta["canonical_sha256"] = hashlib.sha256(
            json.dumps(page, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        meta["rows"] = len(page)
        metas.append(meta)
        if not page:
            break
        for r in page:
            if r["time"] not in seen:
                seen.add(r["time"])
                rows.append(r)
            else:
                dupes += 1
        if len(page) < 500:
            break
        nxt = page[-1]["time"]
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(0.4)
    rows.sort(key=lambda r: r["time"])
    return rows, metas, dupes


# ------------------------------------------------------------------- admission

def build(*, refresh: bool = False) -> dict:
    if refresh:
        for p in RAW_DIR.glob("*"):
            p.unlink()
    started = datetime.now(timezone.utc)

    # -- HL candles: cheapest constraint on the historical horizon -------------
    candles, candle_meta = hl_candles(0)
    now_ms = int(time.time() * 1000)
    complete = [c for c in candles if c["T"] < now_ms]
    hl_mid_hours = {floor_hour_ms(c["t"]): c["c"] for c in complete}

    # -- HL funding: one paginated pass over the entire published history ------
    history_rows, history_metas, history_page_dupes = hl_funding(1, None, "depthprobe")
    trans_page, trans_meta, _ = hl_funding(parse_iso_ms("2023-06-25T10:30:00Z"),
                                           parse_iso_ms("2023-06-26T02:00:00Z"), "cadence")
    steps = [(trans_page[i + 1]["time"] - trans_page[i]["time"]) for i in range(len(trans_page) - 1)]
    first_hourly_idx = next((i for i, s in enumerate(steps) if s <= 2 * HOUR_MS), None)
    cadence = {
        "rows": len(history_rows),
        "requests": len(history_metas),
        "first_row_utc": iso(history_rows[0]["time"]),
        "last_row_utc": iso(history_rows[-1]["time"]),
        "page_boundary_duplicate_rows_dropped": history_page_dupes,
        "transition_window_rows_utc": [iso(r["time"]) for r in trans_page],
        "transition_steps_ms": steps,
        "hourly_from_utc": iso(trans_page[first_hourly_idx + 1]["time"]) if first_hourly_idx is not None else None,
        "hourly_from_note": "first settlement followed by a <=1h step; earlier settlements are 8h-spaced",
    }

    # -- availability of the HL funding series on a uniform hourly grid --------
    funding_by_hour: dict[int, dict] = {}
    funding_dupes: dict[int, list[int]] = {}
    for r in history_rows:
        h = floor_hour_ms(r["time"])
        if h in funding_by_hour:
            funding_dupes.setdefault(h, [funding_by_hour[h]["time"]]).append(r["time"])
        funding_by_hour[h] = r
    offsets = sorted(abs(r["time"] - floor_hour_ms(r["time"])) / 1000 for r in history_rows)
    hourly_from_ms = parse_iso_ms(cadence["hourly_from_utc"])
    era_hours = {h for h in funding_by_hour if h >= hourly_from_ms}
    era_last = max(era_hours)
    era_expected = list(range(hourly_from_ms, era_last + HOUR_MS, HOUR_MS))
    era_missing = [iso(h) for h in era_expected if h not in era_hours]
    history_stats = {
        "rows": len(history_rows),
        "page_requests": len(history_metas),
        "page_boundary_duplicates_dropped": history_page_dupes,
        "distinct_settlement_ms": len({r["time"] for r in history_rows}),
        "first_row_utc": iso(history_rows[0]["time"]),
        "last_row_utc": iso(history_rows[-1]["time"]),
        "pre_hourly_era_hours": len([h for h in funding_by_hour if h < hourly_from_ms]),
        "hourly_era_start_utc": cadence["hourly_from_utc"],
        "hourly_era_end_utc": iso(era_last),
        "hourly_era_expected_hours": len(era_expected),
        "hourly_era_hours_present": len(era_hours),
        "hourly_era_missing_hours": era_missing[:50],
        "hourly_era_missing_count": len(era_missing),
        "hourly_era_max_step_ms": max(
            (b - a for a, b in zip(sorted(era_hours), sorted(era_hours)[1:])), default=None),
    }

    # -- provisional window start = earliest complete HL 1h candle -------------
    win_start_ms = min(hl_mid_hours)

    # -- Binance archive horizon (latest daily file present for both series) ---
    today = datetime.now(timezone.utc).date()
    latest_day = None
    latest_probes = []
    for back in range(0, 6):
        day = (today - timedelta(days=back)).strftime("%Y-%m-%d")
        p_k = probe_exists(binance_url("klines", "daily", day))
        p_m = probe_exists(binance_url("markPriceKlines", "daily", day))
        latest_probes.extend([
            {"series": "klines", **p_k}, {"series": "markPriceKlines", **p_m},
        ])
        if p_k["status"] in (200, 206) and p_m["status"] in (200, 206):
            latest_day = day
            break
    if latest_day is None:
        raise RuntimeError("no Binance daily file pair found in the last 6 days")

    # -- Binance archive earliest (informational, bounded probes) --------------
    earliest_probes = []
    for ym in ("2020-01", "2019-12"):
        for kind in ("klines", "markPriceKlines"):
            p = probe_exists(binance_url(kind, "monthly", ym))
            earliest_probes.append({"series": kind, "month": ym, **p})

    # -- load Binance hourly files covering [win_start, latest_day] ------------
    months = []
    y0, m0 = datetime.fromtimestamp(win_start_ms / 1000, tz=timezone.utc).year, \
        datetime.fromtimestamp(win_start_ms / 1000, tz=timezone.utc).month
    y1, m1 = (int(x) for x in latest_day.split("-")[:2])
    yy, mm = y0, m0
    while (yy, mm) <= (y1, m1):
        months.append(f"{yy:04d}-{mm:02d}")
        mm += 1
        if mm == 13:
            yy, mm = yy + 1, 1
    # the current (unpublished) month is served by daily files instead
    current_ym = f"{today.year:04d}-{today.month:02d}"
    monthly_months = [m for m in months if m != current_ym and m != f"{y1:04d}-{m1:02d}"]

    klines = BinanceHourlySeries("klines")
    marks = BinanceHourlySeries("markPriceKlines")
    for series in (klines, marks):
        for ym in monthly_months:
            tag = f"{series.kind}-1h-{ym}"
            url = binance_url(series.kind, "monthly", ym)
            blob, meta = fetch_cached(f"{tag}.zip", url)
            if meta["http_status"] != 200:
                series.files.append({"label": f"monthly {tag}", "tag": tag, "url": url,
                                     "http_status": meta["http_status"], "actual_rows": 0,
                                     "expected_rows": len(month_hours(ym)), "row_count_ok": False,
                                     "note": "monthly file unavailable"})
                continue
            rows, header = _strip_header(_zip_rows(blob), KLINE_HEADER)
            series.add_file(label=f"monthly {tag}", freq="monthly", tag=tag, rows=rows,
                            expect=month_hours(ym), url=url, meta=meta, header=header)
        # days not covered by published monthly files (trailing, not-yet-published month)
        need_days = []
        d = datetime(y1, m1, 1, tzinfo=timezone.utc).date()
        last_day = datetime.strptime(latest_day, "%Y-%m-%d").date()
        while d <= last_day:
            need_days.append(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
        for day in need_days:
            tag = f"{series.kind}-1h-{day}"
            url = binance_url(series.kind, "daily", day)
            blob, meta = fetch_cached(f"{tag}.zip", url)
            if meta["http_status"] != 200:
                series.files.append({"label": f"daily {tag}", "tag": tag, "url": url,
                                     "http_status": meta["http_status"], "actual_rows": 0,
                                     "expected_rows": 24, "row_count_ok": False,
                                     "note": "daily file unavailable"})
                continue
            rows, header = _strip_header(_zip_rows(blob), KLINE_HEADER)
            series.add_file(label=f"daily {tag}", freq="daily", tag=tag, rows=rows,
                            expect=day_hours(day), url=url, meta=meta, header=header)
        # repair holes inside the window using daily fallbacks
        probe_end = parse_iso_ms(latest_day + "T23:00:00Z")
        holes = series.missing_in([h for h in range(win_start_ms, probe_end + 1, HOUR_MS)])
        if holes:
            series.repair_from_daily(holes)

    # -- Binance funding (auxiliary axis; 8-hourly settlements) ----------------
    funding_settlements: dict[int, dict] = {}
    binance_funding_files: list[dict] = []
    for ym in monthly_months:
        tag = f"fundingRate-{ym}"
        url = binance_url("fundingRate", "monthly", ym)
        blob, meta = fetch_cached(f"{tag}.zip", url)
        entry = {"url": url, "http_status": meta["http_status"], "bytes": meta["bytes"],
                 "sha256": meta["sha256"], "retrieved_utc": meta["retrieved_utc"],
                 "cache_reused": meta.get("cache_reused", False)}
        if meta["http_status"] == 200:
            rows, header = _strip_header(_zip_rows(blob), FUNDING_HEADER)
            intervals = sorted({int(r[1]) for r in rows})
            for r in rows:
                funding_settlements[floor_hour_ms(int(r[0]))] = {"rate": r[2], "interval_h": int(r[1])}
            entry.update({"rows": len(rows), "header_verified": header == FUNDING_HEADER,
                          "funding_interval_hours_values": intervals,
                          "earliest_utc": iso(min(int(r[0]) for r in rows)),
                          "latest_utc": iso(max(int(r[0]) for r in rows))})
        else:
            entry["rows"] = 0
        binance_funding_files.append(entry)

    # -- availability spans ----------------------------------------------------
    hl_funding_hours = set(era_hours)  # uniform hourly support only
    hl_funding_span = _span(hl_funding_hours)
    hl_funding_span.update({
        "raw_first_row_utc": iso(funding_by_hour and min(funding_by_hour)),
        "uniform_hourly_from_utc": cadence["hourly_from_utc"],
        "pre_hourly_era_hours_excluded": len(funding_by_hour) - len(era_hours),
        "note": "uniform hourly grid support; earlier settlements are 8h-spaced and are excluded",
    })
    hl_premium_hours = {h for h in era_hours if funding_by_hour[h].get("premium") not in (None, "")}
    hl_mid_span = _span(set(hl_mid_hours))
    kline_span = _span(set(klines.hours))
    mark_span = _span(set(marks.hours))
    binance_funding_span = _span(set(funding_settlements))

    required = {
        "hl_funding_rate": hl_funding_span,
        "hl_funding_premium": _span(hl_premium_hours),
        "hl_mid_1h_candle_close": hl_mid_span,
        "binance_kline_1h_close": kline_span,
        "binance_mark_1h_close": mark_span,
    }
    window_start = max(s["earliest_ms"] for s in required.values())
    window_end = min(s["latest_ms"] for s in required.values())
    # never extend into an in-progress hour
    window_end = min(window_end, floor_hour_ms(now_ms) - HOUR_MS)
    if window_end < window_start:
        raise RuntimeError(f"empty availability intersection: {iso(window_start)} -> {iso(window_end)}")

    expected_hours = list(range(window_start, window_end + HOUR_MS, HOUR_MS))

    matched, missing, dupes = [], [], []
    for h in expected_hours:
        f = funding_by_hour.get(h)
        row_ok = (
            f is not None and f.get("fundingRate") not in (None, "")
            and f.get("premium") not in (None, "")
            and h in hl_mid_hours and h in klines.hours and h in marks.hours
        )
        if h in funding_dupes:
            dupes.append({"bucket_utc": iso(h), "hl_funding_time_ms": funding_dupes[h]})
        if row_ok:
            matched.append(h)
        else:
            missing.append({
                "bucket_utc": iso(h),
                "hl_funding_rate": f is not None,
                "hl_premium": bool(f and f.get("premium") not in (None, "")),
                "hl_mid_1h_close": h in hl_mid_hours,
                "binance_kline_close": h in klines.hours,
                "binance_mark_close": h in marks.hours,
            })

    coverage = len(matched) / len(expected_hours)
    win_offsets = sorted(abs(funding_by_hour[h]["time"] - h) / 1000 for h in expected_hours)
    verdict = "PAIRED_100PCT" if (not missing and not dupes and len(matched) == len(expected_hours)) \
        else "PAIRING_GAP"

    # -- auxiliary: Binance-funding-constrained sub-window ---------------------
    aux = {"definition": "required-field intersection further constrained by Binance funding "
                         "settlement availability in the free archive (lag ~1 month)"}
    if binance_funding_span["available"]:
        aux_start = max(window_start, binance_funding_span["earliest_ms"])
        aux_end = min(window_end, binance_funding_span["latest_ms"])
        aux_expected = list(range(aux_start, aux_end + HOUR_MS, HOUR_MS)) if aux_end >= aux_start else []
        aux_matched = [h for h in aux_expected if h in set(matched)]
        aux.update({
            "start_utc": iso(aux_start), "end_utc": iso(aux_end), "hours": len(aux_expected),
            "matched_buckets": len(aux_matched), "missing_buckets": len(aux_expected) - len(aux_matched),
            "coverage_ratio": (len(aux_matched) / len(aux_expected)) if aux_expected else None,
            "binance_funding_settlements_inside": sum(1 for h in aux_expected if h in funding_settlements),
            "verdict": "PAIRED_100PCT" if aux_expected and len(aux_matched) == len(aux_expected)
                       else ("PAIRING_GAP" if aux_expected else "EMPTY"),
        })
    else:
        aux.update({"verdict": "EMPTY", "reason": "no Binance funding rows"})

    # -- assemble -------------------------------------------------------------
    result = {
        "artifact": "BRANCH_C_AVAILABILITY_AND_PAIRING_ADMISSION",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_started_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidate_id": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
        "paired_instrument": "SHORT Hyperliquid Core BTC perp / LONG equal-BTC-notional "
                             "Binance USD(S)-M BTCUSDT perp",
        "scope": "REQUIRED_FIELD_AVAILABILITY_AND_HOURLY_PAIRING_ONLY_NO_ECONOMICS",
        "not_computed_here": ["carry", "P&L", "funding differential magnitude", "fee arithmetic",
                              "markout", "displacement", "slippage"],
        "required_fields": list(required.keys()),
        "pairing_rule": PAIRING_RULE,
        "window": {
            "start_utc": iso(window_start),
            "end_utc": iso(window_end),
            "start_ms": window_start,
            "end_ms": window_end,
            "hours": len(expected_hours),
            "expected_buckets": len(expected_hours),
            "matched_buckets": len(matched),
            "missing_buckets": len(missing),
            "duplicate_buckets": len(dupes),
            "coverage_ratio": coverage,
            "verdict": verdict,
            "binding_start_source": [k for k, v in required.items() if v["earliest_ms"] == window_start],
            "binding_end_source": [k for k, v in required.items() if v["latest_ms"] == window_end],
            "end_boundary_note": f"last complete UTC hour before the Binance archive lag "
                                 f"(latest daily file pair present: {latest_day})",
        },
        "availability_spans": {
            "hl_funding_rate": hl_funding_span,
            "hl_funding_premium": required["hl_funding_premium"],
            "hl_mid_1h_candle_close": hl_mid_span,
            "binance_kline_1h_close": kline_span,
            "binance_mark_1h_close": mark_span,
            "binance_funding_settlements_aux": binance_funding_span,
            "_units": "hour buckets; each hour covers [H, H+1h) UTC",
        },
        "row_counts": {
            "hl_funding_rows_fetched": len(history_rows),
            "hl_funding_hours_total": len(funding_by_hour),
            "hl_funding_hours_uniform_hourly_era": len(era_hours),
            "hl_funding_duplicate_hours": len(funding_dupes),
            "hl_candles_rows": len(candles),
            "hl_candles_complete_rows": len(complete),
            "hl_candles_in_progress_excluded": len(candles) - len(complete),
            "hl_funding_hours_inside_window": len(set(expected_hours) & set(funding_by_hour)),
            "binance_kline_hours_loaded": len(klines.hours),
            "binance_mark_hours_loaded": len(marks.hours),
            "binance_funding_settlements": len(funding_settlements),
        },
        "hl_funding_timestamp_jitter": {
            "rows": len(offsets),
            "min_offset_s": offsets[0] if offsets else None,
            "max_offset_s": offsets[-1] if offsets else None,
            "nonzero_offsets": sum(1 for o in offsets if o > 0),
            "rows_over_60s": sum(1 for o in offsets if o > 60),
            "pairing_implication": "exact-ms equality would drop rows; floor-to-hour repair required",
        },
        "hl_funding_timestamp_jitter_window": {
            "rows": len(win_offsets),
            "min_offset_s": win_offsets[0] if win_offsets else None,
            "max_offset_s": win_offsets[-1] if win_offsets else None,
            "nonzero_offsets": sum(1 for o in win_offsets if o > 0),
            "rows_over_1s": sum(1 for o in win_offsets if o > 1),
            "note": "every in-window settlement lies inside its own UTC hour, so flooring cannot "
                    "move a row across a bucket boundary",
        },
        "hl_funding_depth_and_cadence": cadence,
        "hl_funding_full_history": history_stats,
        "bucket_arithmetic": {
            "ours": "expected_buckets = len(range(start_ms, end_ms + 3600000, 3600000)) "
                    "= (end_ms - start_ms)//3600000 + 1, both endpoints inclusive",
            "engine": "int((window_end_unix - window_start_unix) // interval_period_seconds) + 1",
            "matches_engine_inclusive_arithmetic": len(expected_hours) == (window_end - window_start) // HOUR_MS + 1,
            "expected_buckets": len(expected_hours),
        },
        "missing_buckets_detail": missing[:200],
        "missing_buckets_truncated": len(missing) > 200,
        "duplicate_buckets_detail": dupes[:200],
        "auxiliary_funding_constrained_window": aux,
        "binance_file_validation": {
            "klines": klines.files,
            "markPriceKlines": marks.files,
            "repairs_applied": {"klines": klines.repairs, "markPriceKlines": marks.repairs},
            "monthly_row_count_all_ok": all(f.get("row_count_ok", False) for f in klines.files + marks.files
                                            if f.get("frequency") == "monthly"),
        },
        "binance_funding_files": binance_funding_files,
        "binance_archive_horizon_probes": {
            "latest_date_probe": latest_probes,
            "latest_daily_file_pair_date": latest_day,
            "earliest_probe": earliest_probes,
        },
        "hl_api_payloads": [
            {"name": candle_meta["name"], "url": candle_meta["url"], "method": "POST",
             "http_status": candle_meta["http_status"], "bytes": candle_meta["bytes"],
             "sha256": candle_meta["sha256"], "canonical_sha256": candle_meta["canonical_sha256"],
             "retrieved_utc": candle_meta["retrieved_utc"], "cache_reused": candle_meta.get("cache_reused", False),
             "rows": len(candles)},
        ] + [
            {"name": m["name"], "url": m["url"], "method": "POST", "payload": m["payload"],
             "http_status": m["http_status"], "bytes": m["bytes"], "sha256": m["sha256"],
             "canonical_sha256": m.get("canonical_sha256"), "retrieved_utc": m["retrieved_utc"],
             "cache_reused": m.get("cache_reused", False), "rows": m.get("rows")}
            for m in (history_metas + trans_meta)
        ],
        "request_summary": _request_summary(),
        "verdict": verdict,
    }

    result["paired_rows"] = [
        {
            "utc_hour": iso(h),
            "utc_hour_ms": h,
            "hl_funding_rate": funding_by_hour[h]["fundingRate"],
            "hl_premium": funding_by_hour[h]["premium"],
            "hl_mid_1h_close": hl_mid_hours[h],
            "binance_kline_close": klines.hours[h],
            "binance_mark_close": marks.hours[h],
            "hl_funding_time_ms": funding_by_hour[h]["time"],
        }
        for h in matched
    ]
    return result


def _span(hours: set[int]) -> dict:
    if not hours:
        return {"available": False}
    keys = sorted(hours)
    return {
        "available": True,
        "earliest_hour_utc": iso(keys[0]),
        "latest_hour_utc": iso(keys[-1]),
        "earliest_ms": keys[0],
        "latest_ms": keys[-1],
        "hours_present": len(keys),
    }


def _request_summary() -> dict:
    by_host: dict[str, int] = {}
    for r in REQUEST_LOG:
        host = r["url"].split("/")[2]
        by_host[host] = by_host.get(host, 0) + 1
    return {
        "total_requests": len(REQUEST_LOG),
        "by_host": by_host,
        "cached_reused": sum(1 for r in REQUEST_LOG if r.get("cache_reused")),
        "log": REQUEST_LOG,
    }


def crosscheck_values(admission: dict) -> dict:
    """Compare paired_hours values with the saved prior-probe join CSV, value by value."""
    if not PRIOR_PROBE_CSV.exists():
        return {"status": "prior_csv_absent"}
    ours = {r["utc_hour"]: r for r in admission["paired_rows"]}
    fields = ["hl_funding_rate", "hl_premium", "hl_mid_1h_close", "binance_kline_close", "binance_mark_close"]
    checked = 0
    mismatches = []
    outside = 0
    with PRIOR_PROBE_CSV.open() as fh:
        for row in csv.DictReader(fh):
            hour = row["utc_hour"]
            if hour not in ours:
                outside += 1
                continue
            checked += 1
            mine = ours[hour]
            for f in fields:
                a, b = row[f], str(mine[f])
                try:
                    same = float(a) == float(b)
                except ValueError:
                    same = a == b
                if not same:
                    mismatches.append({"utc_hour": hour, "field": f, "prior": a, "ours": b})
    return {
        "status": "compared",
        "prior_rows": checked + outside,
        "prior_rows_inside_our_window": checked,
        "prior_rows_outside_our_window": outside,
        "fields_compared": fields,
        "value_mismatches": mismatches[:50],
        "value_mismatch_count": len(mismatches),
    }


# ------------------------------------------------------------------------- emit

def emit(admission: dict) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    admission["crosscheck_prior_probe_csv"] = crosscheck_values(admission)

    paired_rows = admission.pop("paired_rows")
    csv_path = OUT_DIR / "paired_hours.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["utc_hour", "hl_funding_rate", "hl_premium", "hl_mid_1h_close",
                    "binance_kline_close", "binance_mark_close", "hl_funding_time_ms"])
        for r in paired_rows:
            w.writerow([r["utc_hour"], r["hl_funding_rate"], r["hl_premium"], r["hl_mid_1h_close"],
                        r["binance_kline_close"], r["binance_mark_close"], r["hl_funding_time_ms"]])

    admission["outputs"] = {
        "paired_hours_csv": str(csv_path.relative_to(ROOT)),
        "paired_hours_rows": len(paired_rows),
        "paired_hours_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    admission["artifact_hashes"] = {
        "binance_archive_files": _hash_index(admission),
        "hl_api_payloads": {p["name"]: p["sha256"] for p in admission["hl_api_payloads"]},
    }

    admission["source_urls_by_role"] = {
        "hl_funding": [HL_INFO],
        "hl_mid": [HL_INFO],
        "binance_mark": sorted(
            {f["url"] for f in admission["binance_file_validation"]["markPriceKlines"]}
            | {r["url"] for r in admission["binance_file_validation"]["repairs_applied"]["markPriceKlines"]}),
    }
    manifest_path = write_manifest(admission, paired_rows)
    admission["admission_manifest"] = {
        "path": str(manifest_path.relative_to(ROOT)),
        "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "shape": "W4-canonical (source/schema/session/files/fields/instrument/records/intervals/coverage)",
    }
    admission["independent_engine_evaluation"] = evaluate_with_engine(manifest_path)

    adm_path = OUT_DIR / "admission.json"
    adm_path.write_text(json.dumps(admission, indent=2, sort_keys=True))

    freeze_input = {
        "artifact": "FREEZE_INPUT_BASIS",
        "generated_utc": admission["generated_utc"],
        "candidate_id": admission["candidate_id"],
        "status": "FREEZE_INPUT_NOT_SEALED",
        "note": "Freeze INPUT for branch C; nothing is written under M2/experiments/ by this module.",
        "paired_instrument": admission["paired_instrument"],
        "window": admission["window"],
        "pairing_rule": admission["pairing_rule"],
        "window_definition": "maximal contiguous common window = intersection of per-source "
                             "required-field availability spans, ending at the last complete UTC hour "
                             "before the Binance archive lag; no month chosen by preference, no window "
                             "shrinking, no imputation",
        "bucket_arithmetic": admission["bucket_arithmetic"],
        "engine_verification_command": "python3 -m M2.src.admission --manifest "
                                       "M2/data/derived_basis/manifest_basis.json --branch BASIS --root . "
                                       "--json-out M2/data/derived_basis/manifest_engine_verdict.json",
        "required_fields": admission["required_fields"],
        "coverage_verdict": admission["window"]["verdict"],
        "availability_spans": admission["availability_spans"],
        "auxiliary_funding_constrained_window": admission["auxiliary_funding_constrained_window"],
        "source_urls": sorted({f["url"] for f in admission["binance_file_validation"]["klines"]
                               + admission["binance_file_validation"]["markPriceKlines"]}
                              | {p["url"] for p in admission["hl_api_payloads"]}
                              | {f["url"] for f in admission["binance_funding_files"]}),
        "artifact_hashes": admission["artifact_hashes"],
        "outputs": admission["outputs"],
        "missing_buckets": admission["window"]["missing_buckets"],
        "duplicate_buckets": admission["window"]["duplicate_buckets"],
        "crosscheck_prior_probe_csv": admission["crosscheck_prior_probe_csv"],
        "admission_manifest": admission["admission_manifest"],
        "independent_engine_evaluation": admission["independent_engine_evaluation"],
        "excluded_from_scope": admission["not_computed_here"],
    }
    freeze_path = OUT_DIR / "FREEZE_INPUT_basis.json"
    freeze_path.write_text(json.dumps(freeze_input, indent=2, sort_keys=True))
    return {"admission": str(adm_path.relative_to(ROOT)), "freeze_input": str(freeze_path.relative_to(ROOT)),
            "paired_hours": str(csv_path.relative_to(ROOT)),
            "manifest": str(manifest_path.relative_to(ROOT))}


def write_manifest(admission: dict, paired_rows: list[dict]) -> Path:
    """Emit a canonical admission manifest over the paired hours (unix_seconds hour grid)."""
    win = admission["window"]
    inputs = OUT_DIR / "manifest_inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    start_s, end_s = win["start_ms"] // 1000, win["end_ms"] // 1000
    rows = sorted(paired_rows, key=lambda r: r["utc_hour_ms"])

    specs = [
        ("hl_funding", "hl_funding_hourly.csv", "hl_funding_rate",
         "Hyperliquid POST /info fundingHistory (BTC hourly settlement), time floored to the UTC hour"),
        ("hl_mid", "hl_mid_1h_close.csv", "hl_mid_1h_close",
         "Hyperliquid POST /info candleSnapshot 1h close (mid proxy), t floored to the UTC hour"),
        ("binance_mark", "binance_mark_1h_close.csv", "binance_mark_close",
         "data.binance.vision markPriceKlines 1h close, open_time floored to the UTC hour"),
    ]
    files = []
    for role, fname, key, semantics in specs:
        path = inputs / fname
        with path.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["hour_unix", key])
            for r in rows:
                w.writerow([r["utc_hour_ms"] // 1000, r[key]])
        blob = path.read_bytes()
        files.append({
            "role": role,
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "bytes": len(blob),
            "status": "complete",
            "rows": len(rows),
            "semantics": semantics,
            "upstream_urls": admission["source_urls_by_role"][role],
        })

    hour_seconds = [r["utc_hour_ms"] // 1000 for r in rows]
    manifest = {
        "manifest_id": f"BASIS-FREE-PUBLIC-{win['start_utc']}--{win['end_utc']}",
        "branch": "BASIS",
        "candidate_id": admission["candidate_id"],
        "source": {
            "source_id": "W3-FREE-PUBLIC-HL-BINANCE",
            "provider": "Hyperliquid /info (api.hyperliquid.xyz) + Binance public archive (data.binance.vision)",
            "retrieved_at_utc": admission["generated_utc"],
            "access_terms": "anonymous public HTTPS GET/POST; no credentials, no signup, no paid tier; "
                            "Hyperliquid requester-pays S3 archive not used",
        },
        "schema": {"contract_id": "HL-FUNDING-JSON+BINANCE-USD-M-KLINES", "format": "csv"},
        "session": {
            "coverage_date": win["start_utc"][:10],
            "timezone": "UTC",
            "window_start_unix": start_s,
            "window_end_unix": end_s,
            "window_start_utc": win["start_utc"],
            "window_end_utc": win["end_utc"],
        },
        "files": files,
        "fields": [
            {"name": "hour_unix", "type": "int64", "semantics": "unix_seconds_utc_hour_floor",
             "identity": "hour_bucket_start", "timezone": "UTC"},
            {"name": "hl_funding_rate", "type": "float64",
             "semantics": "Hyperliquid hourly funding rate at the bucket's settlement", "timezone": "UTC"},
            {"name": "hl_mid", "type": "float64",
             "semantics": "Hyperliquid 1h candle close for the bucket (mid proxy)", "timezone": "UTC"},
            {"name": "binance_mark", "type": "float64",
             "semantics": "Binance USD-M BTCUSDT 1h mark price close for the bucket", "timezone": "UTC"},
        ],
        "instrument": {
            "symbol": "BTCUSDT",
            "venue": "hyperliquid+binance",
            "legs": ["Hyperliquid Core BTC perp", "Binance USD(S)-M BTCUSDT perp"],
        },
        "records": {
            "timestamps": hour_seconds,
            "keys": hour_seconds,
            "count": len(hour_seconds),
        },
        "intervals": [{"id": s, "present": True} for s in hour_seconds],
        "coverage": {
            "qualified": win["expected_buckets"],
            "admitted": win["matched_buckets"],
            "ratio": win["coverage_ratio"],
            "window_hours": win["hours"],
            "missing_buckets": win["missing_buckets"],
            "duplicate_buckets": win["duplicate_buckets"],
            "pairing_rule": admission["pairing_rule"],
        },
    }
    path = OUT_DIR / "manifest_basis.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return path


def evaluate_with_engine(manifest_path: Path) -> dict:
    """Read-only self-check against the W4 admission engine, if it is present."""
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from M2.src import admission as engine  # local import: sibling module, read-only use
        try:
            ctx = engine.Context(root=str(ROOT))
        except TypeError:  # older/newer Context signature
            ctx = engine.Context(root=str(ROOT), hash_files=True)
        result = engine.evaluate_path(str(manifest_path), engine.contract_for("BASIS"), ctx)
        return {"engine": "M2/src/admission.py", "contract_id": result.get("contract_id"),
                "state": result.get("state"), "reason_counts": result.get("reason_counts"),
                "reasons": result.get("reasons")}
    except Exception as exc:  # noqa: BLE001 - the engine is a sibling artefact, not a dependency
        return {"engine": "M2/src/admission.py", "state": "ENGINE_UNAVAILABLE", "error": repr(exc)}


def _hash_index(admission: dict) -> dict:
    out = {}
    for series in ("klines", "markPriceKlines"):
        for f in admission["binance_file_validation"][series]:
            out[f.get("tag") or f.get("label")] = f.get("sha256")
        for r in admission["binance_file_validation"]["repairs_applied"][series]:
            out[r["tag"]] = r.get("sha256")
    for f in admission["binance_funding_files"]:
        out[f["url"].rsplit("/", 1)[-1].replace(".zip", "")] = f.get("sha256")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Branch C availability + 100% hourly pairing admission")
    ap.add_argument("--refresh", action="store_true", help="ignore cached raw bytes and re-fetch")
    args = ap.parse_args(argv)
    admission = build(refresh=args.refresh)
    paths = emit(admission)
    print(json.dumps({
        "verdict": admission["verdict"],
        "window": admission["window"]["start_utc"] + " -> " + admission["window"]["end_utc"],
        "hours": admission["window"]["hours"],
        "matched": admission["window"]["matched_buckets"],
        "missing": admission["window"]["missing_buckets"],
        "duplicates": admission["window"]["duplicate_buckets"],
        "aux_funding_window_hours": admission["auxiliary_funding_constrained_window"].get("hours"),
        "requests": admission["request_summary"]["total_requests"],
        "paths": paths,
    }, indent=2))
    return 0 if admission["verdict"] == "PAIRED_100PCT" else 3


if __name__ == "__main__":
    raise SystemExit(main())