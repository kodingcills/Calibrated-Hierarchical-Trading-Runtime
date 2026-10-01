#!/usr/bin/env python3
"""V3 claim D13: is the auction -108.9 bps executable capture an artifact of the
unvalidated book reconstruction, or a real economic result?

Read-only analysis of results.json per_symbol records. Interpreter: .venv/bin/python3
"""
import json
import statistics as st

P = "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/results.json"
r = json.load(open(P))
ps = r["per_symbol"]
n = len(ps)


def clean(v):
    return [x for x in v if x is not None]


def q(vals, p):
    vals = sorted(vals)
    if not vals:
        return float("nan")
    i = min(len(vals) - 1, max(0, int(round(p * (len(vals) - 1)))))
    return vals[i]


def summarize(name, vals):
    vals = clean(vals)
    print(f"{name:40s} n={len(vals):5d} mean={st.mean(vals):12.4f} med={q(vals,.5):12.4f} "
          f"p05={q(vals,.05):12.4f} p95={q(vals,.95):12.4f} min={min(vals):12.4f} max={max(vals):12.4f}")


print("== pooled means (recomputed from per_symbol) ==")
print("gross_usd_per_share mean      :", st.mean(x["gross_usd_per_share"] for x in ps))
print("gross_bps mean                :", st.mean(x["gross_bps"] for x in ps))
print("mechanism_side_signed_bps mean:", st.mean(x["mechanism_side_signed_bps"] for x in ps))
print("c0_usd_per_share mean         :", st.mean(x["c0_usd_per_share"] for x in ps))

print("\n== where does the loss live? ==")
longs = [x for x in ps if x["side_sign"] > 0]
shorts = [x for x in ps if x["side_sign"] < 0]
print("n LONG/SHORT:", len(longs), len(shorts))
print("gross bps LONG mean :", st.mean(x["gross_bps"] for x in longs))
print("gross bps SHORT mean:", st.mean(x["gross_bps"] for x in shorts))
print("mech  bps LONG mean :", st.mean(x["mechanism_side_signed_bps"] for x in longs))
print("mech  bps SHORT mean:", st.mean(x["mechanism_side_signed_bps"] for x in shorts))

print("\n== reconstruction quality (per-symbol) ==")
summarize("entry_spread_usd", [x["entry_spread_usd"] for x in ps])
summarize("entry_spread_bps",
          [x["entry_spread_usd"] / x["entry_price_usd"] * 1e4 for x in ps])
summarize("mid_minus_reference_bps", [x["reconstructed_mid_minus_reference_bps"] for x in ps])
summarize("entry_ask_minus_ref_bps",
          [(x["best_ask_usd"] - x["reference_price_usd"]) / x["reference_price_usd"] * 1e4 for x in ps])
summarize("entry_bid_minus_ref_bps",
          [(x["best_bid_usd"] - x["reference_price_usd"]) / x["reference_price_usd"] * 1e4 for x in ps])

print("\n== decomposition: mech = gross + side_signed(entry-ref) gap ==")
gap = [x["side_sign"] * (x["entry_price_usd"] - x["reference_price_usd"]) / x["reference_price_usd"] * 1e4
       for x in ps]
summarize("side_signed(entry - reference) bps", gap)
print("mean mech bps            :", st.mean(x["mechanism_side_signed_bps"] for x in ps))
print("mean gross bps           :", st.mean(x["gross_bps"] for x in ps))
print("mean gap (entry-ref) bps :", st.mean(gap))
print("mech - gap  =", st.mean(x["mechanism_side_signed_bps"] for x in ps) - st.mean(gap),
      "(should equal gross)")

print("\n== what if every entry were taken at the exchange reference (no recon error)? ==")
print("  gross would equal the mechanism metric:", st.mean(x["mechanism_side_signed_bps"] for x in ps))

print("\n== excluding poor reconstructions (spread as %% of price) ==")
for thr in (0.001, 0.002, 0.005, 0.01, 0.02, 0.05):
    keep = [x for x in ps if x["entry_spread_usd"] / x["entry_price_usd"] <= thr]
    if not keep:
        continue
    print(f"  spread <= {thr*100:5.2f}%: n={len(keep):5d} "
          f"mean gross_bps={st.mean(x['gross_bps'] for x in keep):10.3f} "
          f"mean mech_bps={st.mean(x['mechanism_side_signed_bps'] for x in keep):8.3f}")

print("\n== concentration of the loss ==")
tot = sum(x["gross_usd_per_share"] for x in ps)
c = sorted(ps, key=lambda x: x["gross_usd_per_share"])
for k in (1, 5, 10, 25, 50, 100):
    s = sum(x["gross_usd_per_share"] for x in c[:k])
    print(f"  worst {k:4d} symbols -> {s:9.4f} of {tot:9.4f} ({s/tot*100:6.1f}%)")

print("\n== negative control ==")
# Control 1: reverse the side sign -> should flip the sign of gross (a sign error would show here)
rev = st.mean(-x["side_sign"] * (x["exit_price_usd"] - x["entry_price_usd"]) / x["entry_price_usd"] * 1e4
              for x in ps)
print("mean gross with side_sign flipped:", rev)
# Control 2: replace the 15:55 ask entry by the reconstructed MIDPOINT (no half-spread cost);
# if the book were faithful this would recover roughly the mechanism metric.
mid = [x["side_sign"] * (x["closing_cross_price_usd"] - x["reconstructed_mid_at_1555_usd"])
       / x["reconstructed_mid_at_1555_usd"] * 1e4 for x in ps if x["reconstructed_mid_at_1555_usd"]]
print("mean gross at reconstructed MIDPOINT:", st.mean(mid), "n=", len(mid))
