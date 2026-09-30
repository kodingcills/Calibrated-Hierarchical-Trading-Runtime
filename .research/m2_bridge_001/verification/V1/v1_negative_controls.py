#!/usr/bin/env python3
"""V1 negative controls for the W3 pairing claim.

A pairing test that cannot fail proves nothing.  These controls take the SAME
independent derivation machinery used in v1_reverify_pairing.py, deliberately
break one input at a time, and assert the check reports the failure.

Nothing on disk is modified: all corruption happens on in-memory copies.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

V1 = Path(__file__).resolve().parent
sys.path.insert(0, str(V1))
import v1_reverify_pairing as V  # noqa: E402

HOUR_MS = V.HOUR_MS


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pairing(candles, funding, klines, marks, hour_dupes=None):
    """Same 4-way 1:1 pairing rule as the independent re-derivation."""
    starts = [min(funding), min(candles), min(klines), min(marks)]
    ends = [max(funding), max(candles), max(klines), max(marks)]
    ws, we = max(starts), min(ends)
    expected = list(range(ws, we + HOUR_MS, HOUR_MS))
    matched, missing, dup = [], [], []
    for h in expected:
        f = funding.get(h)
        ok = (f is not None and f.get("fundingRate") not in (None, "")
              and f.get("premium") not in (None, "")
              and h in candles and h in klines and h in marks)
        if hour_dupes and h in hour_dupes:
            dup.append(h)
        (matched if ok else missing).append(h)
    verdict = "PAIRED_100PCT" if not missing and not dup and len(matched) == len(expected) else "PAIRING_GAP"
    return verdict, len(expected), len(matched), [iso(h) for h in missing[:5]], len(dup)


def exact_ms_pairing(candles, funding, klines, marks):
    """The rejected naive rule: join on exact millisecond equality."""
    cand_ms = {}
    for c in candles.values():
        cand_ms[c["t"]] = c["c"]
    ks_ms = {}
    for h, v in klines.items():
        ks_ms[h] = v
    hits = 0
    for h in funding:
        f = funding[h]
        if f["time"] in cand_ms:
            hits += 1
    return hits, len(funding)


def main() -> int:
    klines, _, _ = V.load_binance("klines")
    marks, _, _ = V.load_binance("markPriceKlines")
    candles, _ = V.load_hl_candles()
    funding, frows, _, _, hour_dupes = V.load_hl_funding()

    res = {}

    base = pairing(candles, funding, klines, marks, hour_dupes)
    res["baseline"] = {"verdict": base[0], "expected": base[1], "matched": base[2],
                       "missing": base[3], "dupes": base[4]}
    assert base[0] == "PAIRED_100PCT", base

    # NC1: delete one Binance mark hour inside the window -> must report a gap
    c = dict(marks)
    victim = min(c) + HOUR_MS * 1000  # a window hour
    del c[victim]
    r = pairing(candles, funding, klines, c, hour_dupes)
    res["NC1_missing_binance_mark_hour"] = {"victim": iso(victim), "verdict": r[0],
                                           "missing": r[3], "detected": r[0] != "PAIRED_100PCT"}

    # NC2: shift one HL funding settlement forward by 2h (crosses its bucket) ->
    #      its original bucket must become missing
    c2 = dict(funding)
    v2 = min(candles) + 5 * HOUR_MS   # inside the window
    row = dict(c2.pop(v2))
    row["time"] = row["time"] + 2 * HOUR_MS
    c2[V.floor_hour(row["time"])] = row
    r = pairing(candles, c2, klines, marks, hour_dupes)
    res["NC2_shifted_funding_row"] = {"victim": iso(v2), "verdict": r[0],
                                      "missing": r[3], "detected": r[0] != "PAIRED_100PCT"}

    # NC3: corrupt the value of one HL candle (price wrong) -> value comparison must fail
    c3 = {h: dict(v) for h, v in candles.items()}
    v3 = min(c3)
    c3[v3]["c"] = "1.0"
    prod = {}
    import csv
    with open(V.DER / "paired_hours.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            ts = datetime.strptime(row["utc_hour"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            prod[int(ts.timestamp()) * 1000] = row
    mismatch = prod[v3]["hl_mid_1h_close"] != c3[v3]["c"]
    res["NC3_corrupted_candle_value"] = {"victim": iso(v3), "value_mismatch_detected": mismatch}

    # NC4: the naive exact-ms join cannot pair the data -> proves floor rule is load-bearing
    hits, total = exact_ms_pairing(candles, funding, klines, marks)
    win_fund = [h for h in funding if min(candles) <= h <= max(candles)]
    res["NC4_exact_ms_join_drops_rows"] = {"funding_rows_compared": len(win_fund),
                                           "exact_ms_hits": hits,
                                           "drops": len(win_fund) - hits}

    # NC5: full-grid integrity -- every window hour present exactly once in each series
    win_start, win_end = max(min(x) for x in (candles, funding, klines, marks)), \
        min(max(x) for x in (candles, funding, klines, marks))
    grid = list(range(win_start, win_end + HOUR_MS, HOUR_MS))
    res["NC5_grid_integrity"] = {
        "hl_candle_missing": len([h for h in grid if h not in candles]),
        "hl_funding_missing": len([h for h in grid if h not in funding]),
        "binance_kline_missing": len([h for h in grid if h not in klines]),
        "binance_mark_missing": len([h for h in grid if h not in marks]),
    }

    all_detected = (res["NC1_missing_binance_mark_hour"]["detected"]
                    and res["NC2_shifted_funding_row"]["detected"]
                    and res["NC3_corrupted_candle_value"]["value_mismatch_detected"]
                    and res["NC4_exact_ms_join_drops_rows"]["drops"] > 0)
    res["all_negative_controls_detected"] = all_detected
    (V1 / "v1_negative_controls.json").write_text(json.dumps(res, indent=2, sort_keys=True))
    print(json.dumps(res, indent=2, sort_keys=True))
    assert all_detected
    return 0


if __name__ == "__main__":
    sys.exit(main())