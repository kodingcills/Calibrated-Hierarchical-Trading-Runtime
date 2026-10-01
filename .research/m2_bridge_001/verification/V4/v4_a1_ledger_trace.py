#!/usr/bin/env python3
"""V4 claim A1: trace every numeric quantity in EVD-0071..EVD-0075 to a cited artifact.

Read-only. For each asserted number this script either
  * reproduces it from a named field of a sealed artifact (explicit assertion table), or
  * reports it UNTRACEABLE.

A number is "reproduced" only if the artifact value, formatted at the same decimal
precision as the canonical claim, equals the claim string (round-half-even, i.e.
plain Python float formatting).  Counts are compared as exact integers.  Everything
that is a derived statistic (deltas, ratios, identities) is recomputed here from the
sealed record arrays rather than read back from a report.

Usage: .venv/bin/python3 v4_a1_ledger_trace.py
"""

from __future__ import annotations

import csv
import json
import os
import re
import statistics as st

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
V4 = os.path.dirname(os.path.abspath(__file__))

ES = os.path.join(REPO, "M2/experiments/M2-BRIDGE-ES-H3-OFI")
BAS = os.path.join(REPO, "M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS")
AUC = os.path.join(REPO, "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY")

RESULTS = {}
CHECKS = []  # (evd, label, ok, detail)


def load(path):
    if path not in RESULTS:
        with open(path) as fh:
            RESULTS[path] = json.load(fh)
    return RESULTS[path]


def numer(x, claim, tol_dp=None):
    """Reproduce claim (string) from the float x.  Returns (ok, rendered)."""
    c = claim.replace(",", "")
    if "." in c:
        dp = len(c.split(".")[1])
        rendered = f"{x:.{dp}f}"
        return rendered == c, rendered
    rendered = str(int(round(x)))
    return rendered == c, rendered


def chk(evd, label, ok, detail=""):
    CHECKS.append((evd, label, bool(ok), detail))
    return bool(ok)


def eqf(x, y, tol=1e-9):
    return abs(x - y) <= tol


def main() -> int:
    es = load(os.path.join(ES, "results.json"))
    esf = load(os.path.join(ES, "freeze.json"))
    esri = load(os.path.join(ES, "run_inputs.json"))
    esadd = load(os.path.join(ES, "addendum_unconditional_matched_instants.json"))
    bas = load(os.path.join(BAS, "results.json"))
    basf = load(os.path.join(BAS, "freeze.json"))
    basri = load(os.path.join(BAS, "run_inputs.json"))
    auc = load(os.path.join(AUC, "results.json"))
    aucf = load(os.path.join(AUC, "freeze.json"))
    auce = load(os.path.join(AUC, "entry_prints.json"))
    aucc = load(os.path.join(AUC, "certificate.json"))
    aucri = load(os.path.join(AUC, "run_inputs.json"))
    hub = es["headline"]
    ph = {h["horizon_s"]: h for h in es["per_horizon"]}
    nb = es["null_baseline"]["unconditional_markout_bps_by_horizon"]
    cc = es["classification"]

    # ---------------- EVD-0071 (ES kill) ----------------
    e = "EVD-0071"
    chk(e, "gross 1s -0.0047336", numer(hub["gross_markout_bps"], "-0.0047336"))
    chk(e, "CI lo -0.0468503", numer(hub["ci_low_bps"], "-0.0468503"))
    chk(e, "CI hi +0.0403358", numer(hub["ci_high_bps"], "0.0403358"))
    chk(e, "n=583", hub["observations"] == 583, hub["observations"])
    chk(e, "of 599 slots", ph[1]["decision_slots"] == 599, ph[1]["decision_slots"])
    chk(e, "se 0.0222976", numer(hub["se_bps"], "0.0222976"))
    chk(e, "t -0.212", numer(es["significance"]["t_stat"], "-0.212"))
    chk(e, "5s -0.0014608", numer(ph[5]["gross_markout_bps"], "-0.0014608"))
    chk(e, "15s +0.0502825", numer(ph[15]["gross_markout_bps"], "0.0502825"))
    chk(e, "C0 0.5770016 bps", numer(cc["bps"]["c0_bps"], "0.5770016"))
    chk(e, "C0 13.1004 USD", numer(cc["usd"]["c0_usd"], "13.1004"))
    chk(e, "C* -0.5817352", numer(cc["bps"]["c_star_bps"], "-0.5817352"))
    chk(e, "C* -13.207857 USD", numer(cc["usd"]["c_star_usd"], "-13.207857"))
    chk(e, "clause PRIMARY_HORIZON_GROSS_NOT_POSITIVE",
        cc["clause"] == "PRIMARY_HORIZON_GROSS_NOT_POSITIVE", cc["clause"])
    chk(e, "arm hi<=C0", cc["bps"]["uncertainty_hi_bps"] <= cc["bps"]["c0_bps"],
        f'{cc["bps"]["uncertainty_hi_bps"]}<={cc["bps"]["c0_bps"]}')
    chk(e, "uncond 1s +0.0156746", numer(nb["1"], "0.0156746"))
    chk(e, "uncond matched +0.0208001",
        numer(esadd["horizons"][0]["unconditional_bps_over_conditional_instants"], "0.0208001"))
    chk(e, "598 quote-available slots (1s)",
        round(ph[1]["quote_coverage"] * ph[1]["decision_slots"]) == 598,
        ph[1]["quote_coverage"] * ph[1]["decision_slots"])
    chk(e, "quote coverage 0.99833", numer(ph[1]["quote_coverage"], "0.99833"))
    chk(e, "observation coverage 0.97329", numer(ph[1]["observation_coverage"], "0.97329"))
    cf = es["contract"]["coverage_floor"]
    chk(e, "floors 0.95/0.75/250",
        (cf["quote_coverage_min"], cf["observation_coverage_min"], cf["min_observations"])
        == (0.95, 0.75, 250))
    chk(e, "18,104 trades", es["validity_checks"]["trades_used_primary"] == 18104)
    chk(e, "273 LONG / 310 SHORT",
        (ph[1]["state_long"], ph[1]["state_short"]) == (273, 310),
        (ph[1]["state_long"], ph[1]["state_short"]))
    chk(e, "scope SAMPLE_SCOPED_DEVELOPMENT_KILL",
        cc["scope"] == "SAMPLE_SCOPED_DEVELOPMENT_KILL", cc["scope"])
    # V3-sourced: 5,999/5,999 instants.  Re-derived here from the audit fields.
    gca = es["validity_checks"]["grid_causality_audit"]
    v3txt = open(os.path.join(REPO, ".research/m2_bridge_001/verification/V3/REPORT.md")).read()
    chk(e, "strictly causal (artifact audit 59,999 clean; V3 5,999/5,999 present)",
        gca["nonzero_deviations"] == 0 and gca["agreement_fraction"] == 1.0 and "5,999/5,999" in v3txt,
        gca["instants_compared"])

    # ---------------- EVD-0072 (basis kill) ----------------
    e = "EVD-0072"
    g = bas["gross"]
    u = bas["uncertainty"]
    cov = bas["coverage"]
    chk(e, "gross +0.0344051", numer(g["point_bps"], "0.0344051"))
    chk(e, "measured +0.0324852", numer(g["measured_component_bps"], "0.0324852"))
    chk(e, "HL carry +0.0596998", numer(g["decomposition"]["hl_funding_carry_mean_bps"], "0.0596998"))
    chk(e, "Binance carry -0.0267530", numer(g["decomposition"]["binance_funding_carry_mean_bps"], "-0.0267530"))
    chk(e, "hedge residual -0.0004616", numer(g["decomposition"]["hedge_mark_to_market_residual_mean_bps"], "-0.0004616"))
    chk(e, "CI lo -0.0101126", numer(u["primary"]["ci_lo_bps"], "-0.0101126"))
    chk(e, "CI hi +0.0755247", numer(u["primary"]["ci_hi_bps"], "0.0755247"))
    chk(e, "block lo 0.0157561", numer(u["moving_block_24h"]["ci_lo_bps"], "0.0157561"))
    chk(e, "block hi 0.0476396", numer(u["moving_block_24h"]["ci_hi_bps"], "0.0476396"))
    chk(e, "C0 4.8 bps", numer(bas["costs"]["c0_bps"], "4.8"))
    chk(e, "C0 = 2 x 0.024%",
        abs(bas["costs"]["c0_items"][0]["value"] - 0.048) < 1e-12
        and "0.024" in json.dumps(bas["costs"]["c0_items"]), bas["costs"]["c0_items"][0]["value"])
    chk(e, "hi 0.09624", numer(u["decision_interval_hi_bps"], "0.09624"))
    chk(e, "C* -4.7655949", numer(bas["costs"]["c_star_bps"], "-4.7655949"))
    chk(e, "T* 145.69", numer(g["t_star_hours"], "145.69"))
    chk(e, "base tier 0.045%", numer(bas["costs"]["base_tier_scenario"]["hyperliquid"]["value"], "0.09"),
        bas["costs"]["base_tier_scenario"]["hyperliquid"]["name"])
    chk(e, "4979 holds", cov["holds_evaluated"] == 4979, cov["holds_evaluated"])
    chk(e, "panel 4981 buckets", basf["panel"]["buckets"] == 4981, basf["panel"]["buckets"])
    chk(e, "4895 with every input", cov["holds_with_every_required_row"] == 4895)
    chk(e, "84 unresolved", cov["unresolved_hold_count"] == 84)
    chk(e, "roughly 140x (~139.5)", 130 < bas["costs"]["c0_bps"] / g["point_bps"] < 150,
        bas["costs"]["c0_bps"] / g["point_bps"])
    chk(e, "verdict KILL_MATERIALITY", bas["verdict"] == "KILL_MATERIALITY", bas["verdict"])

    # ---------------- EVD-0073 (auction indeterminate) ----------------
    e = "EVD-0073"
    d = auc["decision"]
    br = auc["book_reconstruction"]
    wd = br["window_diagnostics"]
    cvg = auc["coverage"]
    mm = auc["mechanism_metric"]
    ps = auc["per_symbol"]
    chk(e, "-108.8946", numer(d["gross_bps_mean"], "-108.8946"))
    chk(e, "1261 signal-defined symbols", cvg["analysed_symbols"] == 1261)
    chk(e, "mechanism +6.5168", numer(mm["pooled_side_signed_bps"]["mean"], "6.5168"))
    mech = st.mean(x["mechanism_side_signed_bps"] for x in ps)
    entrygap = st.mean(x["side_sign"] * (x["entry_price_usd"] - x["reference_price_usd"])
                       / x["reference_price_usd"] * 1e4 for x in ps)
    ident = st.mean(x["gross_bps"] for x in ps)
    chk(e, "identity capture = mech - gap (+115.4115)",
        numer(entrygap, "115.4115") and eqf(ident, mech - entrygap, 1e-9),
        f"{ident} vs {mech - entrygap}")
    tot = sum(x["gross_usd_per_share"] for x in ps)
    worst50 = sum(x["gross_usd_per_share"] for x in sorted(ps, key=lambda x: x["gross_usd_per_share"])[:50])
    chk(e, "worst 50 carry 93.9% (re-derived)", numer(worst50 / tot * 100, "93.9"),
        worst50 / tot * 100)
    mx = max(ps, key=lambda x: x["entry_spread_usd"])
    chk(e, "largest entry spread $11.64 on $2.10",
        numer(mx["entry_spread_usd"], "11.64") and numer(mx["entry_price_usd"], "2.10"),
        (mx["symbol"], mx["entry_spread_usd"], mx["entry_price_usd"]))
    sel = [x for x in ps if x["entry_spread_usd"] / x["entry_price_usd"] * 1e4 <= 10]
    chk(e, "348 symbols spread<=10bps", len(sel) == 348, len(sel))
    chk(e, "-0.60 bps restricted", numer(st.mean(x["gross_bps"] for x in sel), "-0.60"),
        st.mean(x["gross_bps"] for x in sel))
    chk(e, "mechanism +3.55 restricted", numer(st.mean(x["mechanism_side_signed_bps"] for x in sel), "3.55"),
        st.mean(x["mechanism_side_signed_bps"] for x in sel))
    chk(e, "orphans 7,176,224", wd["orphan_total"] == 7176224, wd["orphan_total"])
    chk(e, "orphan share 35.75%",
        wd["orphan_total"] == (wd["orphan_cancels"] + wd["orphan_deletes"] + wd["orphan_executes"] + wd["orphan_replaces"])
        and numer(wd["orphan_rate_of_in_scope_messages"] * 100, "35.75"),
        wd["orphan_rate_of_in_scope_messages"])
    chk(e, "window opens 15:49:50", auc["measurement_window"]["start"].startswith("15:49:50"),
        auc["measurement_window"]["start"])
    chk(e, "1286 signal-defined", cvg["signal_defined_symbols"] == 1286)
    chk(e, "2465 denominator", cvg["denominator_symbols_with_valid_closing_cross"] == 2465)
    chk(e, "0.5217", numer(cvg["signal_scope_ratio"], "0.5217"))
    chk(e, "clauses INDETERMINATE + ENTRY_BOOK + SIGNAL_SCOPE",
        d["verdict"] == "INDETERMINATE"
        and set(d["clauses"]) == {"ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED", "SIGNAL_SCOPE_SUBFLOOR"}, d["clauses"])
    chk(e, "near/far zero in all 12,809 records",
        br["within_far_band_ratio"] == 0.0 and br["within_exchange_near_far_band"] == 0)
    chk(e, "mech CI [2.0026, 10.9985]",
        numer(mm["pooled_side_signed_bps"]["lo"], "2.0026")
        and numer(mm["pooled_side_signed_bps"]["hi"], "10.9985"))
    chk(e, "1.02 bps fee floor", numer(auc["executable_capture"]["pooled_c0_bps"]["mean"], "1.02"))
    import json as _json
    with open(os.path.join(AUC, "signal_extract.json")) as _fh:
        _se = _json.load(_fh)
    chk(e, "12,809 session locates", len(_se) == 12809, len(_se))
    chk(e, "1,219 reconstruction snapshots at 15:55",
        br["symbols_with_snapshot_at_1555"] == 1219, br["symbols_with_snapshot_at_1555"])

    # ---------------- EVD-0072/0073 sealing-scope cross-check ----------------
    chk(e, "4,281 of 12,809 carry the Closing Cross exit price (independently counted)",
        sum(1 for r in _se if r.get("closing_cross_valid") is True) == 4281,
        sum(1 for r in _se if r.get("closing_cross_valid") is True))
    chk(e, "the freeze's own input holds the exit price (sealed-input contradiction)",
        "closing_cross_price_raw" in _se[0] and "signal_extract.json" in
        json.dumps(aucf.get("inputs_sha256", aucri.get("code_and_input_sha256", {}))))
    chk(e, "47.8% removed by N/O/P rule",
        numer(cvg["missingness_reason_counts"]["ineligible_imbalance_direction"]
              / cvg["denominator_symbols_with_valid_closing_cross"] * 100, "47.8"),
        cvg["missingness_reason_counts"]["ineligible_imbalance_direction"])

    # ---------------- EVD-0074 (ES addendum) ----------------
    e = "EVD-0074"
    add = {h["horizon_s"]: h for h in esadd["horizons"]}
    chk(e, "1s matched +0.0208001", numer(add[1]["unconditional_bps_over_conditional_instants"], "0.0208001"))
    chk(e, "1s published +0.0156746", numer(add[1]["unconditional_bps_over_quote_available_slots"], "0.0156746"))
    chk(e, "1s delta +0.0051255", numer(add[1]["delta_matched_minus_published_bps"], "0.0051255"))
    chk(e, "5s matched +0.0547556", numer(add[5]["unconditional_bps_over_conditional_instants"], "0.0547556"))
    chk(e, "5s published +0.0631091", numer(add[5]["unconditional_bps_over_quote_available_slots"], "0.0631091"))
    chk(e, "5s delta -0.0083535", numer(add[5]["delta_matched_minus_published_bps"], "-0.0083535"))
    chk(e, "15s matched +0.1240628", numer(add[15]["unconditional_bps_over_conditional_instants"], "0.1240628"))
    chk(e, "15s published +0.1340817", numer(add[15]["unconditional_bps_over_quote_available_slots"], "0.1340817"))
    chk(e, "15s delta -0.0100189", numer(add[15]["delta_matched_minus_published_bps"], "-0.0100189"))
    chk(e, "conditional -0.0047336/-0.0014608/+0.0502825",
        numer(add[1]["conditional_gross_bps"], "-0.0047336")
        and numer(add[5]["conditional_gross_bps"], "-0.0014608")
        and numer(add[15]["conditional_gross_bps"], "0.0502825"))
    chk(e, "obs 583/579/569",
        [add[h]["observations_conditional"] for h in (1, 5, 15)] == [583, 579, 569])
    chk(e, "quote slots 598/594/584",
        [add[h]["slots_quote_available"] for h in (1, 5, 15)] == [598, 594, 584])
    chk(e, "matched delta from addendum vs results (1s)",
        eqf(add[1]["unconditional_bps_over_conditional_instants"] - nb["1"],
            add[1]["delta_matched_minus_published_bps"], 1e-12))
    chk(e, "conditional below matched baseline at every horizon",
        all(add[h]["conditional_minus_unconditional_matched_bps"] < 0 for h in (1, 5, 15)))
    chk(e, "results.json unmodified by addendum (sealed hash matches)",
        esadd["results_json_sha256"] == "09c8562999304072a5f5b5184bece3ba0588d1d57754ae776b3c6934f1487ac2")

    # ---------------- EVD-0075 (restoration) ----------------
    e = "EVD-0075"
    import hashlib
    def sha(p, base=REPO):
        cand = os.path.join(base, p)
        if not os.path.exists(cand):
            cand = os.path.join(REPO, p)
        with open(cand, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    chk(e, "admission.py == sealed 9f5862f7", sha("M2/src/admission.py").startswith("9f5862f71efd7fec"))
    chk(e, "admission_auction.py == 84fd3270", sha("M2/src/admission_auction.py").startswith("84fd3270cc382248"))
    chk(e, "sealed hash recorded in basis freeze",
        basf["inputs_sha256"]["code"]["M2/src/admission.py"].startswith("9f5862f7"),
        basf["inputs_sha256"]["code"]["M2/src/admission.py"])
    chk(e, "basis freeze declares 155 entries",
        sum(len(v) for v in basf["inputs_sha256"].values()) == 155,
        {k: len(v) for k, v in basf["inputs_sha256"].items()})
    auc_hashes = aucri["code_and_input_sha256"]
    chk(e, "auction seal has 22 entries", len(auc_hashes) == 22, len(auc_hashes))
    drifted = [p for p, h in auc_hashes.items()
               if (sha(p) if os.path.exists(os.path.join(REPO, p)) else h) != h]
    chk(e, "auction drift == exactly 4 paths", len(drifted) == 4, drifted)
    chk(e, "ES seal 13/13 verify",
        all(sha(p, ES) == h for p, h in esri["code_and_input_sha256"].items()),
        sum(sha(p, ES) == h for p, h in esri["code_and_input_sha256"].items()))
    chk(e, "basis 155/155 verify",
        all(sha(p) == h for v in basf["inputs_sha256"].values() for p, h in v.items()))

    # ---------------- report ----------------
    by_evd = {}
    for evd, label, ok, detail in CHECKS:
        by_evd.setdefault(evd, []).append((label, ok, detail))
    failed = [c for c in CHECKS if not c[2]]
    out = {
        "total": len(CHECKS),
        "reproduced": sum(1 for c in CHECKS if c[2]),
        "failed": [{"evd": a, "label": b, "detail": str(c)} for a, b, ok, c in failed],
        "by_evd": {k: {"n": len(v), "ok": sum(1 for _, o, _ in v if o)} for k, v in by_evd.items()},
    }
    print(json.dumps(out, indent=1))
    for a, b, ok, det in failed:
        print("FAIL", a, b, det)
    with open(os.path.join(V4, "v4_a1_ledger_trace.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())