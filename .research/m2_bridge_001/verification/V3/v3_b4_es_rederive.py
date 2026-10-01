#!/usr/bin/env python3
"""V3 claim B4/B5/B6: independent re-derivation of the ES 1 s side-signed markout.

Does NOT import M2.src.es_materiality. Reads only the retained admitted artefacts
(trades.csv, bbo_increments.csv, spread_grid.csv) and re-implements the frozen
contract text from freeze.json:

  state     x(t) = (V_buy - V_sell) / D(t),  V_* = aggressor-signed size in (t-1s, t]
  outcome   direction * (M(t+h) - M(t)) / M(t) * 1e4
  friction  1/2 S_entry + 1/2 S_exit in bps of the entry midpoint
  grid      decisions at whole seconds k=0..600-h, censored k+h <= 599

Also rebuilds level 1 strictly-past from bbo_increments.csv for one 60 s block and
compares it with the admitted spread_grid (causality / no-lookahead check).

Interpreter: .venv/bin/python3
"""
import csv
import json

import numpy as np

D = "M2/data/derived_es/2023-07-17T133000Z/"
START = 1689600600000000000  # 2023-07-17T13:30:00Z
GRID_MS = 10
N_GRID = 60000  # 600 s at 10 ms
H = 1

# ---------- admitted grid ----------
g_idx, g_ts, g_bid, g_ask, g_bsz, g_asz = [], [], [], [], [], []
with open(D + "spread_grid.csv") as f:
    for r in csv.DictReader(f):
        g_idx.append(int(r["grid_index"]))
        g_ts.append(int(r["ts_ns"]))
        g_bid.append(float(r["bid_px"]) if r["bid_px"] else np.nan)
        g_ask.append(float(r["ask_px"]) if r["ask_px"] else np.nan)
        g_bsz.append(float(r["bid_sz"]) if r["bid_sz"] else 0.0)
        g_asz.append(float(r["ask_sz"]) if r["ask_sz"] else 0.0)
bid = np.array(g_bid)
ask = np.array(g_ask)
bsz = np.array(g_bsz)
asz = np.array(g_asz)
print("grid rows:", len(g_idx), "ts strictly 10 ms:", np.all(np.diff(np.array(g_ts)) == 10_000_000))

# ---------- trades ----------
tr_ts, tr_sz, tr_agg = [], [], []
with open(D + "trades.csv") as f:
    for r in csv.DictReader(f):
        if r["instrument_id"] != "3445":  # ESU3 only
            continue
        tr_ts.append(int(r["exchange_send_ns"]))
        tr_sz.append(float(r["size"]))
        tr_agg.append(int(r["aggressor_side"]))
tr_ts = np.array(tr_ts, dtype=np.int64)
tr_sz = np.array(tr_sz)
tr_agg = np.array(tr_agg)
print("trades:", len(tr_ts), "aggressor values:", sorted(set(tr_agg.tolist())))
order = np.argsort(tr_ts, kind="stable")
tr_ts, tr_sz, tr_agg = tr_ts[order], tr_sz[order], tr_agg[order]
signed = np.where(tr_agg == 1, tr_sz, -tr_sz)
csum = np.concatenate([[0.0], np.cumsum(signed)])

mid = np.where(np.isfinite(bid) & np.isfinite(ask), (bid + ask) / 2.0, np.nan)
spread = np.where(np.isfinite(bid) & np.isfinite(ask), ask - bid, np.nan)

quoted = (np.isfinite(mid) & (ask > bid) & (bsz > 0) & (asz > 0))


def v_of_window(lo_ns, hi_ns):
    """sum of aggressor-signed size with lo < ts <= hi"""
    a = np.searchsorted(tr_ts, lo_ns, side="right")
    b = np.searchsorted(tr_ts, hi_ns, side="right")
    return csum[b] - csum[a]


rows = []
for k in range(0, 600 - H):  # k = 0..598 -> 599 slots
    ie = k * (1000 // GRID_MS)
    ix = (k + H) * (1000 // GRID_MS)
    if not quoted[ie] or not quoted[ix]:
        rows.append(None)
        continue
    t = START + k * 1_000_000_000
    v = v_of_window(t - 1_000_000_000, t)
    dd = bsz[ie] + asz[ie]
    x = v / dd
    if x == 0.0:
        rows.append(None)
        continue
    direction = 1.0 if x > 0 else -1.0
    gross = direction * (mid[ix] - mid[ie]) / mid[ie] * 1e4
    s_entry = spread[ie] / mid[ie] * 1e4
    s_exit = spread[ix] / mid[ie] * 1e4
    friction = 0.5 * s_entry + 0.5 * s_exit
    rows.append({"k": k, "dir": direction, "gross": gross, "friction": friction})

ev = [r for r in rows if r]
print("\n== independent re-derivation, PRIMARY h=1 s ==")
print("decision slots        :", 600 - H)
print("quote coverage        :", sum(1 for r in rows if r is not None or True) and
      (sum(1 for k in range(0, 600 - H)
           if quoted[k * 100] and quoted[(k + H) * 100]) / (600 - H)))
print("evaluated observations:", len(ev))
print("LONG / SHORT          :", sum(1 for r in ev if r["dir"] > 0), sum(1 for r in ev if r["dir"] < 0))
g = np.array([r["gross"] for r in ev])
fr = np.array([r["friction"] for r in ev])
print("pooled gross bps      : %.10f" % g.mean())
print("C0 (mean friction) bps: %.10f" % fr.mean())
print("C* = g - C0  bps      : %.10f" % (g.mean() - fr.mean()))
lo = np.array([r["gross"] for r in ev if r["dir"] > 0])
sh = np.array([r["gross"] for r in ev if r["dir"] < 0])
print("LONG  gross bps       : %.10f  (n=%d)" % (lo.mean(), len(lo)))
print("SHORT gross bps       : %.10f  (n=%d)" % (sh.mean(), len(sh)))

pub = json.load(open("M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json"))
h = pub["headline"]
print("\n== vs published ==")
print("published gross       :", h["gross_markout_bps"], " delta:", g.mean() - h["gross_markout_bps"])
print("published C0          :", h["c0_bps"], " delta:", fr.mean() - h["c0_bps"])
print("published C*          :", h["c_star_bps"], " delta:", (g.mean() - fr.mean()) - h["c_star_bps"])
print("published obs         :", h["observations"], " delta:", len(ev) - h["observations"])
ps = {p["state"]: p for p in pub["per_state"] if p["horizon_s"] == 1}
print("published LONG        :", ps["LONG"]["gross_markout_bps"], " delta:", lo.mean() - ps["LONG"]["gross_markout_bps"])
print("published SHORT       :", ps["SHORT"]["gross_markout_bps"], " delta:", sh.mean() - ps["SHORT"]["gross_markout_bps"])

# ---------- unconditional (side-ignoring) markout on the SAME instants ----------
uncond = []
for r in ev:
    k = r["k"]
    ie, ix = k * 100, (k + H) * 100
    uncond.append((mid[ix] - mid[ie]) / mid[ie] * 1e4)
print("\nunconditional markout on the SAME instants: %.10f" % np.mean(uncond))
print("published unconditional                   :",
      pub["null_baseline"]["unconditional_markout_bps_by_horizon"]["1"])

# ---------- B5: strictly-past level-1 rebuild for the first 60 s ----------
print("\n== B5 strictly-past level-1 replay, first 60 s ==")
last_px = {"B": None, "A": None}
last_sz = {"B": None, "A": None}
rowsb = []
with open(D + "bbo_increments.csv") as f:
    for r in csv.DictReader(f):
        if r["md_price_level"] != "1" or r["instrument_id"] != "3445":
            continue
        ts = int(r["exchange_send_ns"])
        if ts > START + 60_000_000_000:
            break
        rowsb.append((ts, r["side"], int(r["price"]), int(r["size"]), r["update_action"]))

mismatch = 0
checked = 0
j = 0
for i in range(0, 6000):  # 60 s at 10 ms
    tns = START + i * 10_000_000
    while j < len(rowsb) and rowsb[j][0] <= tns:
        _, side, px, sz, act = rowsb[j]
        last_px[side], last_sz[side] = px, sz
        j += 1
    if last_px["B"] is None or last_px["A"] is None:
        continue
    checked += 1
    if not (np.isfinite(bid[i]) and np.isfinite(ask[i])):
        continue
    if abs(bid[i] - last_px["B"]) > 1e-6 or abs(ask[i] - last_px["A"]) > 1e-6:
        mismatch += 1
print("replay points compared:", checked, " mismatch vs admitted grid:", mismatch)
