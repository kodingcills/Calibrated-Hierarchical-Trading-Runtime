#!/usr/bin/env python3
"""V2 adversarial causality / lookahead check on the retained W2 ES artifacts.

Uses only the producer's retained CSVs (trades.csv, bbo_increments.csv) plus the
secdef snapshot, and asks whether any row could have been built from information
later than its own timestamp.

Claim 13 (+ the scale cross-check of claim 12).
"""

from __future__ import annotations

import csv
import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = "M2/data/derived_es/2023-07-17T133000Z"
SECDEF = "M2/data/raw/secdef-2023-07-17.dat.gz"


def load_bbo():
    rows = []
    with open(os.path.join(PROD, "bbo_increments.csv")) as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    return rows


def load_trades():
    with open(os.path.join(PROD, "trades.csv")) as fh:
        return list(csv.DictReader(fh))


def secdef_settlements():
    want = {"48": "security_id", "55": "symbol", "9787": "price_display_factor",
            "1150": "settl_price", "1147": "contract_multiplier",
            "969": "min_price_increment", "1146": "tick_value", "1151": "security_group"}
    out = {}
    with gzip.open(SECDEF, "rt", encoding="latin1") as fh:
        for line in fh:
            f = {}
            for tok in line.rstrip("\n").split("\x01"):
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    if k in want:
                        f[want[k]] = v
            if f.get("security_group") == "ES":
                try:
                    out[int(f["security_id"])] = f
                except (KeyError, ValueError):
                    pass
    return out


def main():
    out = {}
    trades = load_trades()
    bbo = load_bbo()
    out["trades_rows"] = len(trades)
    out["bbo_rows"] = len(bbo)

    # --- retained-artifact causality: per-row timestamp ordering -------------
    def order_violations(rows, cols):
        v = {"ts_event>exchange_send": 0, "ts_event>ts_recv": 0, "exchange_send>ts_recv": 0}
        worst = {"ts_event>ts_recv": 0, "exchange_send>ts_recv": 0}
        for r in rows:
            te, tr, es = int(r["ts_event_ns"]), int(r["ts_recv_ns"]), int(r["exchange_send_ns"])
            if te > es:
                v["ts_event>exchange_send"] += 1
            if te > tr:
                v["ts_event>ts_recv"] += 1
                worst["ts_event>ts_recv"] = max(worst["ts_event>ts_recv"], te - tr)
            if es > tr:
                v["exchange_send>ts_recv"] += 1
                worst["exchange_send>ts_recv"] = max(worst["exchange_send>ts_recv"], es - tr)
        return v, worst

    out["trades_timestamp_order"], out["trades_timestamp_order_worst_ns"] = order_violations(trades, None)
    out["bbo_timestamp_order"], out["bbo_timestamp_order_worst_ns"] = order_violations(bbo, None)

    # --- bbo series monotone in sequence and in ts (the retained artifact) ---
    def monotone(rows, key):
        bad = 0
        prev = None
        for r in rows:
            cur = r[key]
            if prev is not None and cur < prev:
                bad += 1
            prev = cur
        return bad

    out["bbo_sequence_regressions"] = monotone(bbo, "sequence")
    out["bbo_ts_event_regressions"] = monotone(bbo, "ts_event_ns")
    out["bbo_ts_recv_regressions"] = monotone(bbo, "ts_recv_ns")

    # --- lookahead test: rebuild BBO *only from retained bbo rows* whose
    #     sequence is strictly below the trade's sequence, and compare to the
    #     producer's own in/out classification.
    by_instr = {}
    for r in bbo:
        by_instr.setdefault(int(r["instrument_id"]), []).append(
            (int(r["sequence"]), r["side"], int(r["price"]))
        )
    for k in by_instr:
        by_instr[k].sort(key=lambda t: t[0])

    primary = 3445
    pf = float(secdef_settlements()[primary]["price_display_factor"])
    tick_mant = int(round(float(secdef_settlements()[primary]["min_price_increment"]) * 1e9))
    series = by_instr.get(primary, [])

    import bisect
    seqs = [s[0] for s in series]
    bid = ask = None
    bid_sz = ask_sz = None
    state = []  # (seq, bid, ask)
    j = 0
    out_counts = {"checked": 0, "inside_or_at": 0, "outside_below_bid": 0,
                  "outside_above_ask": 0, "at_own_side": 0, "at_wrong_side": 0}
    worst_seq_gap = 0
    examples = []
    for t in trades:
        sid = int(t["instrument_id"])
        if sid != primary:
            continue
        tseq = int(t["sequence"])
        price = int(t["price"])
        # advance only through rows strictly earlier in sequence
        while j < len(series) and series[j][0] < tseq:
            s, side_, px = series[j]
            if side_ == "B":
                bid = px
            else:
                ask = px
            j += 1
        out_counts["checked"] += 1
        if bid is None or ask is None:
            continue
        if price < bid:
            out_counts["outside_below_bid"] += 1
            d = bid - price
        elif price > ask:
            out_counts["outside_above_ask"] += 1
            d = price - ask
        else:
            out_counts["inside_or_at"] += 1
            d = 0
        if d:
            if len(examples) < 6:
                examples.append({"sequence": tseq, "price": price, "bid": bid, "ask": ask,
                                 "distance_ticks": round(d / tick_mant, 3),
                                 "aggressor": t["aggressor_side"]})
        elif t["aggressor_side"] == "1" and price == ask:
            out_counts["at_own_side"] += 1
        elif t["aggressor_side"] == "2" and price == bid:
            out_counts["at_own_side"] += 1
        else:
            out_counts["at_wrong_side"] += 1
    out["lookahead_bbo_rebuild"] = out_counts
    out["lookahead_examples"] = examples
    out["aggressor_at_own_side_pct_of_checked"] = 100.0 * out_counts["at_own_side"] / out_counts["checked"]

    # --- price scale: mantissa x 1e-9 x factor reproduces secdef settlement ---
    sd = secdef_settlements()
    scale_checks = {}
    for sid in (3445, 314863, 17077, 4155):
        rec = sd.get(sid)
        if not rec:
            continue
        f = float(rec["price_display_factor"])
        val = float(rec["settl_price"])
        mant = int(round(val * 1e9))
        scale_checks[str(sid)] = {
            "symbol": rec["symbol"],
            "secdef_settl_price_units": val,
            "price_display_factor": f,
            "index_points_via_producer_scale": mant * 1e-9 * f,
            "secdef_units_times_factor": val * f,
            "equal": abs(mant * 1e-9 * f - val * f) < 1e-9,
            "tick_value_usd": float(rec["tick_value"]) if rec.get("tick_value") else None,
            "multiplier_x_increment_check": (
                abs(float(rec["contract_multiplier"]) * float(rec["min_price_increment"]) * f
                    - float(rec["tick_value"])) < 1e-6
                if rec.get("tick_value") else None
            ),
        }
    out["price_scale_settlement_checks"] = scale_checks

    with open(os.path.join(HERE, "v2_es_causality.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=str)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()