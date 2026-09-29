#!/usr/bin/env python3
"""No-purchase endpoint and timestamp-completeness check for the frozen pair."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

HL = "https://api.hyperliquid.xyz/info"
BN = "https://fapi.binance.com"


def hl_info(body: dict) -> object:
    req = Request(HL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=20) as response:
        return json.load(response)


def bn(path: str, query: dict) -> object:
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    with urlopen(f"{BN}{path}?{qs}", timeout=20) as response:
        return json.load(response)


def expected_hourly_times(start_ms: int, end_ms: int) -> list[int]:
    first = ((start_ms + 3_599_999) // 3_600_000) * 3_600_000
    return list(range(first, end_ms + 1, 3_600_000))


def hourly_complete(rows: list[dict], start_ms: int, end_ms: int) -> dict:
    times = [int(row["time"]) for row in rows]
    expected = expected_hourly_times(start_ms, end_ms)
    expected_buckets = {t: t // 3_600_000 * 3_600_000 for t in expected}
    observed_counts = {bucket: 0 for bucket in expected_buckets.values()}
    for timestamp in times:
        bucket = timestamp // 3_600_000 * 3_600_000
        if bucket in observed_counts:
            observed_counts[bucket] += 1
    missing = [t for t, bucket in expected_buckets.items() if observed_counts[bucket] == 0]
    duplicate = [t for t, bucket in expected_buckets.items() if observed_counts[bucket] > 1]
    return {
        "expected_hours": len(expected),
        "observed_rows": len(rows),
        "missing_times": missing,
        "duplicate_times": duplicate,
        "observed_timestamps_ms": times,
        "strict_hourly_complete": len(rows) == len(expected) and not missing and not duplicate,
        "timestamps_are_ms_epoch": all(t > 10**12 for t in times),
    }


def main() -> int:
    # One complete UTC hour ending before invocation; this is an endpoint smoke check,
    # not a performance sample and must not be interpreted as a pilot.
    now = int(time.time() * 1000)
    end = (now // 3_600_000 - 1) * 3_600_000
    start = end - 3_600_000
    out: dict = {
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "window": {"start_ms": start, "end_ms": end},
        "pair": {"hyperliquid": "BTC (first perp dex)", "binance": "BTCUSDT (USDⓈ-M perpetual)"},
        "no_purchase": True,
    }
    try:
        meta = hl_info({"type": "meta"})
        names = [x.get("name") for x in meta.get("universe", [])]
        out["hyperliquid_meta"] = {"btc_exists": "BTC" in names, "btc_record": next((x for x in meta["universe"] if x.get("name") == "BTC"), None)}
        ctx = hl_info({"type": "metaAndAssetCtxs"})
        out["hyperliquid_ctx_shape"] = {"is_two_part": isinstance(ctx, list) and len(ctx) == 2, "asset_context_count": len(ctx[1]) if isinstance(ctx, list) and len(ctx) == 2 else None}
        funding = hl_info({"type": "fundingHistory", "coin": "BTC", "startTime": start, "endTime": end})
        out["hyperliquid_funding"] = {"rows": funding, "completeness": hourly_complete(funding, start, end)}
    except Exception as exc:
        out["hyperliquid_error"] = repr(exc)
    try:
        info = bn("/fapi/v1/exchangeInfo", {})
        symbol = next((s for s in info.get("symbols", []) if s.get("symbol") == "BTCUSDT"), None)
        out["binance_exchange"] = {"btc_usdt_exists": symbol is not None, "record": symbol}
        funding = bn("/fapi/v1/fundingRate", {"symbol": "BTCUSDT", "startTime": start, "endTime": end, "limit": 1000})
        out["binance_funding"] = {"rows": funding, "observed_timestamps_ms": [int(x["fundingTime"]) for x in funding]}
        mark = bn("/fapi/v1/markPriceKlines", {"symbol": "BTCUSDT", "interval": "1h", "startTime": start, "endTime": end, "limit": 10})
        out["binance_mark_klines"] = {"rows": mark, "one_hour_rows": len(mark) == 1, "timestamps_ms": [int(x[0]) for x in mark]}
    except Exception as exc:
        out["binance_error"] = repr(exc)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
