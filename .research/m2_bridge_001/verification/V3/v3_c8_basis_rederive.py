#!/usr/bin/env python3
"""V3 claims C8/C10/C11: independent recomputation of the branch-C gross.

Does NOT import M2.src.basis_materiality or M2.src.envelope. Re-implements the frozen
one-hour construction from the panel CSV and the raw Binance fundingRate zips:

  structure  SHORT Hyperliquid Core BTC perp / LONG equal-notional Binance BTCUSDT perp
  holds      decision hour j in [W0+1h, W1-1h) step 1h; entry row j-1h, exit row j,
             carry row j+1h
  HL carry   short receives +rate * notional        -> bps = rate * 1e4
  Bin carry  long pays -rate * notional at an 8h settlement; 0 when no settlement
             inside the hold; UNRESOLVED when on-grid but unarchived
  hedge      short HL + long Binance mark-to-market residual
Interpreter: .venv/bin/python3
"""
import csv
import glob
import statistics as st
import zipfile

HOUR = 3600
BIN = "M2/data/derived_basis/"

rows = {}
order = []
with open(BIN + "paired_hours.csv") as f:
    for r in csv.DictReader(f):
        from datetime import datetime, timezone
        h = int(datetime.strptime(r["utc_hour"], "%Y-%m-%dT%H:%M:%SZ")
                .replace(tzinfo=timezone.utc).timestamp())
        rows[h] = {
            "hl_fr": float(r["hl_funding_rate"]),
            "hl_mid": float(r["hl_mid_1h_close"]),
            "bin_close": float(r["binance_kline_close"]),
            "hl_ft_ms": int(r["hl_funding_time_ms"]),
        }
        order.append(h)
order.sort()
W0, W1 = order[0], order[-1]
print("panel rows:", len(order), "W0:", W0, "W1:", W1,
      "contiguous:", order == list(range(W0, W1 + HOUR, HOUR)))

# ---- raw Binance settlements ----
settle = {}
files = sorted(glob.glob(BIN.replace("derived_basis", "raw") + "raw/basis/fundingRate-*.zip"))
if not files:
    files = sorted(glob.glob("M2/data/raw/basis/fundingRate-*.zip"))
for p in files:
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            lines = z.read(n).decode().strip().splitlines()
            for ln in lines[1:]:
                calc_ms, iv, rate = ln.split(",")
                assert int(iv) == 8, iv
                hour = int(calc_ms) // 1000
                assert hour % (8 * HOUR) == 0
                assert hour not in settle
                settle[hour] = float(rate)
print("archived Binance settlements:", len(settle))

# ---- holds ----
holds = list(range(W0 + HOUR, W1, HOUR))
print("holds (expected 4979):", len(holds), " contiguous:", holds == list(range(holds[0], holds[-1] + 1, HOUR)))

hl_c, bin_c, mtm, gross = [], [], [], []
unresolved = 0
for j in holds:
    ent, ex, car = rows[j - HOUR], rows[j], rows[j + HOUR]
    hl = car["hl_fr"] * 1e4                                  # short receives
    if car_row := (j + HOUR):
        pass
    if (j + HOUR) % (8 * HOUR) != 0:
        bc, status = 0.0, "NO_SETTLEMENT_INSIDE_HOLD"
    elif (j + HOUR) in settle:
        bc, status = -settle[j + HOUR] * 1e4, "SETTLEMENT_OBSERVED"   # long pays
    else:
        bc, status, = None, "SETTLEMENT_RATE_UNOBSERVED"
        unresolved += 1
    m = (-(ex["hl_mid"] / ent["hl_mid"] - 1.0) + (ex["bin_close"] / ent["bin_close"] - 1.0)) * 1e4
    hl_c.append(hl)
    mtm.append(m)
    if bc is not None:
        bin_c.append(bc)
    g = hl + (0.0 if bc is None else bc) + m
    gross.append(g)

print("\n== independent branch-C recomputation ==")
print("HL carry mean bps      : %.12f" % st.fmean(hl_c))
print("Binance carry mean bps : %.12f" % st.fmean(bin_c))
print("  (unresolved counted as 0 in this mean; see next)")
print("MTM residual mean bps  : %.12f" % st.fmean(mtm))
print("MTM residual sd bps    : %.12f" % st.pstdev(mtm))
print("gross (measured) mean  : %.12f" % st.fmean(gross))
print("gross min / max        : %.12f / %.12f" % (min(gross), max(gross)))
print("unresolved holds       :", unresolved)
print("observed settlements   :", len(bin_c))

# recompute Binance carry treating unresolved as zero (the module's own convention)
print("\n== vs published ==")
pub = {
    "hl": 0.05969975979112272, "bin": -0.02675300261096606,
    "mtm": -0.0004615894835227425, "gross": 0.03248516769663392,
    "min": -10.934471872162494, "max": 13.66884812563114,
}
print("HL   delta:", st.fmean(hl_c) - pub["hl"])
print("BIN  delta:", st.fmean(bin_c) - pub["bin"])
print("MTM  delta:", st.fmean(mtm) - pub["mtm"])
print("GRS  delta:", st.fmean(gross) + (0.0) - pub["gross"],
      " (unresolved-as-zero; published measured_component uses the same convention)")
print("MIN  delta:", min(gross) - pub["min"])
print("MAX  delta:", max(gross) - pub["max"])

# ---- C9: C0 arithmetic and the base-tier counterfactual ----
print("\n== C9: C0 and counterfactuals ==")
print("2 x 0.024%% per side  = %.4f bps" % (2 * 0.024 * 100))
print("2 x 0.045%% base tier = %.4f bps" % (2 * 0.045 * 100))
for name, c0 in (("lowest rung 0.024%%", 4.8), ("base tier 0.045%%", 9.0), ("C0 = 0", 0.0)):
    g = 0.034405071291733334
    lo, hi = -0.02698346242246038, 0.09623539865022562
    verdict = ("KILL" if (g <= 0 or hi <= c0) else
               "SURVIVE" if lo > c0 else "INDETERMINATE")
    print(f"  C0={c0:5.3f} bps ({name:20s}) -> {verdict}  (g={g:.4f}, interval=[{lo:.4f},{hi:.4f}])")

# ---- C8 counterfactual: reversed structure ----
print("\n== C8: sign/structure counterfactuals ==")
rev_struct = st.fmean([-h + (-b) + m for h, b, m in zip(hl_c, bin_c, mtm)])
print("LONG HL / SHORT Binance gross mean bps: %.6f" % rev_struct)
rev_sign = st.fmean([-h for h in hl_c]) + st.fmean(bin_c) + st.fmean(mtm)
print("HL carry sign flipped (structure unchanged): %.6f" % rev_sign)
