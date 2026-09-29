#!/usr/bin/env python3
"""Validate an already-downloaded Hyperliquid archive stream; never downloads data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate(rows: list[dict], *, timestamp_key: str = "time", max_gap_ms: int = 3_600_000) -> dict:
    times = [int(row[timestamp_key]) for row in rows if timestamp_key in row]
    result = {
        "rows": len(rows),
        "rows_with_timestamp": len(times),
        "missing_timestamp_rows": len(rows) - len(times),
        "strictly_increasing": all(a < b for a, b in zip(times, times[1:])),
        "duplicate_timestamps": len(times) - len(set(times)),
        "max_gap_ms": max((b - a for a, b in zip(times, times[1:])), default=0),
        "gaps_over_limit": sum(1 for a, b in zip(times, times[1:]) if b - a > max_gap_ms),
    }
    result["complete_for_declared_gap_limit"] = bool(
        rows and result["rows_with_timestamp"] == result["rows"]
        and result["strictly_increasing"] and result["duplicate_timestamps"] == 0
        and result["gaps_over_limit"] == 0
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="newline-delimited JSON archive file already downloaded")
    parser.add_argument("--timestamp-key", default="time")
    parser.add_argument("--max-gap-ms", type=int, default=3_600_000)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.path.read_text().splitlines() if line.strip()]
    print(json.dumps(validate(rows, timestamp_key=args.timestamp_key, max_gap_ms=args.max_gap_ms), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
