#!/usr/bin/env python3
"""V3 negative controls and the B6 / D13 supporting arithmetic.

NC2  ES: flip the side-signed direction -> what verdict would the frozen rule give?
NC3  Auction: apply the frozen rule WITHOUT the entry-book clause -> KILL; with it -> INDETERMINATE.
NC4  Auction: replace the entry price by the reconstructed midpoint (removing the
     reconstruction's half-spread and much of its error) -> residual loss.
B6   ES: is C0 an observed spread (per-observation) or a hard-coded tick?
D13  Auction: how much of the -108.9 bps is the entry-vs-reference gap?
Interpreter: .venv/bin/python3
"""
import csv
import json

# ---------- NC2 / B6 : ES ----------
D = "M2/data/derived_es/2023-07-17T133000Z/"
g = list(csv.DictReader(open(D + "spread_grid.csv")))
ticks = [float(r["spread_ticks"]) for r in g if r["spread_ticks"]]
import statistics as st
print("== B6: observed spread on the admitted ESU3 grid ==")
print("quoted grid points      :", len(ticks))
print("mean spread (ticks)     : %.6f" % st.fmean(ticks))
print("distribution (ticks)    :",
      {t: ticks.count(t) for t in sorted(set(ticks))})
print("implied C0 in ticks     : %.6f  (0.5770016233 / 0.551069... bps per tick)"
      % (0.5770016233430615 / (0.25 / 4536.75 * 1e4)))
print("  -> non-integer, so C0 is the per-observation observed 1/2 S_entry + 1/2 S_exit,")
print("     not a hard-coded one-tick-per-side (that would be 1.102 bps).")

g_bps = -0.004733612439280016
c0 = 0.5770016233430615
lo, hi = -0.046850251511832974, 0.04033579324042719


def verdict(gr, l, h, c):
    if gr <= 0 or h <= c:
        return "KILL_MATERIALITY"
    return "SURVIVE_PROVISIONAL" if l > c else "INDETERMINATE"


print("\n== NC2: ES sign flip ==")
print("as recorded              : g=%+.6f  [%+.6f, %+.6f]  C0=%.6f -> %s"
      % (g_bps, lo, hi, c0, verdict(g_bps, lo, hi, c0)))
print("every sign flipped       : g=%+.6f  [%+.6f, %+.6f]  C0=%.6f -> %s"
      % (-g_bps, -hi, -lo, c0, verdict(-g_bps, -hi, -lo, c0)))
print("  -> the verdict is sign-robust here (both arms kill); only the CLAUSE changes")
print("     (PRIMARY_HORIZON_GROSS_NOT_POSITIVE -> the floor arm hi<=C0).")
print("C0 = 0 (free execution)  : -> %s" % verdict(g_bps, lo, hi, 0.0))

# ---------- NC3 / NC4 / D13 : auction ----------
r = json.load(open("M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/results.json"))
ps = r["per_symbol"]
pooled = r["executable_capture"]["pooled_gross_usd_per_share"]
c0u = r["decision"]["c0_usd_per_share_mean"]
print("\n== NC3: frozen rule with and without the entry-book clause ==")
print("rule on the analysed sample (clause disabled): %s"
      % verdict(pooled["gross_usd_per_share_mean"], pooled["gross_usd_per_share_mean"],
                pooled["gross_usd_per_share_mean"], c0u))
print("delivered (clause order, gate unevaluable)   : %s" % r["decision"]["verdict"])
print("rule_verdict field                            : %s" % r["decision"]["rule_verdict"])

print("\n== D13: decomposition of the -108.9 bps ==")
gap = [x["side_sign"] * (x["entry_price_usd"] - x["reference_price_usd"])
       / x["reference_price_usd"] * 1e4 for x in ps]
mech = [x["mechanism_side_signed_bps"] for x in ps]
gro = [x["gross_bps"] for x in ps]
print("mean mechanism (ref -> cross)      : %+8.4f bps" % st.fmean(mech))
print("mean entry-vs-reference gap        : %+8.4f bps" % st.fmean(gap))
print("mean executable capture            : %+8.4f bps" % st.fmean(gro))
print("identity  mech - gap = capture     : %+8.4f bps" % (st.fmean(mech) - st.fmean(gap)))
worst = sorted(ps, key=lambda x: x["gross_usd_per_share"])[:50]
print("worst 50 of 1261 symbols carry     : %.1f%% of the total loss"
      % (sum(x["gross_usd_per_share"] for x in worst)
         / sum(x["gross_usd_per_share"] for x in ps) * 100))
print("largest reconstructed entry spread : $%.2f on a $%.2f name"
      % (max(x["entry_spread_usd"] for x in ps),
         max(ps, key=lambda x: x["entry_spread_usd"])["entry_price_usd"]))

print("\n== NC4: entry taken at the reconstructed MIDPOINT (spread removed) ==")
mid = [x["side_sign"] * (x["closing_cross_price_usd"] - x["reconstructed_mid_at_1555_usd"])
       / x["reconstructed_mid_at_1555_usd"] * 1e4
       for x in ps if x["reconstructed_mid_at_1555_usd"]]
print("mean %.4f bps over %d symbols" % (st.fmean(mid), len(mid)))
tight = [x for x in ps if x["entry_spread_usd"] / x["entry_price_usd"] <= 0.001]
print("restricted to the %d symbols whose RECONSTRUCTED spread is <=10 bps of price:"
      % len(tight))
print("  mean executable capture %.4f bps  (mechanism %.4f bps)"
      % (st.fmean(x["gross_bps"] for x in tight),
         st.fmean(x["mechanism_side_signed_bps"] for x in tight)))
