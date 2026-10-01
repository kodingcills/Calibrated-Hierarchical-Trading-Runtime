#!/usr/bin/env python3
"""V4 claims A2/A3/A4: canonical record vs the verification findings.

A2  the verifier-contested / rejected items were carried into canonical state as
    limitations rather than dropped.
A3  branches A and C are DEAD with an explicit scope and a resurrection condition,
    neither is ALIVE or gate-eligible, and the candidate counts are consistent.
A4  the auction candidate row carries no kill/survival verdict and the parent
    auction row is unrevived and substantively unchanged (git history).

Usage: .venv/bin/python3 v4_a2_a4_canonical.py
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
V4 = os.path.dirname(os.path.abspath(__file__))

CHECKS = []


def chk(item, label, ok, detail=""):
    CHECKS.append({"item": item, "label": label, "ok": bool(ok), "detail": str(detail)})
    return bool(ok)


def evd():
    return {r["evidence_id"]: r for r in
            csv.DictReader(open(os.path.join(REPO, "M1/data/evidence_ledger.csv")))}


def cands(path=None):
    p = path or os.environ.get("V4_CANDIDATES_PATH",
                               os.path.join(REPO, "M1/data/candidate_tuples.csv"))
    return {r["candidate_id"]: r for r in csv.DictReader(open(p))}


def git_rows(rev):
    out = subprocess.run(["git", "show", f"{rev}:M1/data/candidate_tuples.csv"],
                         capture_output=True, text=True, cwd=REPO)
    if out.returncode:
        return {}
    return {r["candidate_id"]: r for r in csv.DictReader(io.StringIO(out.stdout))}


def main() -> int:
    E = evd()
    C = cands()
    # ---------------- A2: limitations carried ----------------
    A = "A2"
    lim = {
        "auction freeze invalidated (sealed input predates the seal; holds the Closing Cross exit price)":
            ("EVD-0073", ["INVALID as a preregistration", "written before the seal",
                          "4,281 of 12,809", "Closing Cross exit price"]),
        "reconstruction-artifact decomposition":
            ("EVD-0073", ["reconstruction artifact", "115.4115", "93.9%"]),
        "degenerate near/far diagnostic":
            ("EVD-0073", ["DEGENERATE", "near and far prices are 0 in all 12,809 records"]),
        "basis module-hash drift":
            ("EVD-0072", ["9f5862f7", "00363c3a", "no longer verifies in place"]),
        "AUCTION drift fallout":
            ("EVD-0075", ["drifts in the OPPOSITE direction", "four drifted", "unavoidable"]),
        "unanchored sealing for A":
            ("EVD-0071", ["no external anchor", "UNVERIFIED"]),
        "unanchored sealing for C":
            ("EVD-0072", ["no external anchor", "UNVERIFIED"]),
        "ES instant-set addendum":
            ("EVD-0074", ["different instant sets", "matched-instant", "delta +0.0051255"]),
        "entry-book reconstruction coverage floor / scope subfloor":
            ("EVD-0073", ["ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED", "SIGNAL_SCOPE_SUBFLOOR", "0.5217"]),
        "basis 84 unresolved settlements bracketed not zeroed in the measured series":
            ("EVD-0072", ["exactly zero", "bracketed", "never treated as zero"]),
    }
    for name, (eid, needles) in lim.items():
        blob = json.dumps(E[eid])
        missing = [n for n in needles if n not in blob]
        chk(A, f"limitation present: {name}", not missing, f"EVD={eid} missing={missing}")
    # ES single-window scope present
    for needle in ["SAMPLE_SCOPED_DEVELOPMENT_KILL", "single window"]:
        chk(A, f"ES single-window scope recorded ({needle})",
            needle.lower() in (json.dumps(E["EVD-0071"]) + json.dumps(C["TUP-CME-ES-H3-OFI-AGG"])).lower())
    # the superseding repair is recorded rather than the EVD-0072 text rewritten
    chk(A, "EVD-0075 records the repair superseding EVD-0072(iii)",
        "EVD-0075" in json.dumps(E) and "9f5862f7" in E["EVD-0075"]["claim"])

    # ---------------- A2b: the limitations in the wider canonical corpus ----------------
    A = "A2"
    exp = {r["experiment_id"]: r for r in
           csv.DictReader(open(os.path.join(REPO, "M1/data/experiments.csv")))}
    e12 = [r for r in exp.values()
           if r.get("candidate_id") == "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG"] or \
          [r for r in csv.DictReader(open(os.path.join(REPO, "M1/data/experiments.csv")))
           if "LATENOII" in str(r.values())]
    chk(A, "experiments.csv carries the auction experiment as INVALIDATED_FREEZE",
        any("INVALIDATED_FREEZE" in " ".join(map(str, r.values())) for r in exp.values()),
        [r.get("experiment_id") for r in e12])
    oq = {r["question_id"]: r for r in
          csv.DictReader(open(os.path.join(REPO, "M1/data/open_questions.csv")))}
    oq17 = json.dumps(oq["OQ-0017"])
    for needle in ["warm-up", "7,176,224", "INVALID", "4,281", "externally anchored"]:
        chk(A, f"OQ-0017 carries '{needle}'", needle in oq17)
    src = {r["source_id"]: r for r in
           csv.DictReader(open(os.path.join(REPO, "M1/data/source_registry.csv")))}
    chk(A, "SRC-0248 records that the sealed input PREDATES the seal",
        "PREDATES the seal" in json.dumps(src["SRC-0248"]))
    chk(A, "SRC-0249 records the ES matched-instant addendum",
        "matched-instant" in json.dumps(src.get("SRC-0249", {}))
        or "instant set" in json.dumps(src.get("SRC-0249", {})))
    chk(A, "SRC-0250 records the basis freeze restoration",
        "9f5862f7" in json.dumps(src.get("SRC-0250", {})))
    for pid, needle in (("P-0013", "598 quote-available slots"),
                        ("P-0014", "9f5862f7"),
                        ("P-0015", "as_run_deviations_from_freeze")):
        pj = json.load(open(os.path.join(REPO, f"M1/work/patches/{pid}.json")))
        chk(A, f"{pid} carries its limitation", needle in json.dumps(pj),
            pj.get("decision"))
    for cid in ("TUP-CME-ES-H3-OFI-AGG", "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"):
        note = str(C[cid].get("notes", ""))
        chk(A, f"{cid} row carries the unanchored-sealing UNVERIFIED limitation",
            "no external anchor" in note and "UNVERIFIED" in note, note[:120])

    # ---------------- A3: DEAD + scope + resurrection, counts ----------------
    A = "A3"
    for cid in ("TUP-CME-ES-H3-OFI-AGG", "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"):
        r = C[cid]
        chk(A, f"{cid} DEAD", r["overall_status"] == "DEAD", r["overall_status"])
        chk(A, f"{cid} not ALIVE", r["overall_status"] != "ALIVE")
        chk(A, f"{cid} kill_gate KG3_EXECUTION", r["kill_gate"] == "KG3_EXECUTION", r["kill_gate"])
        chk(A, f"{cid} kill_status ACTIVE", r["kill_status"] == "ACTIVE", r["kill_status"])
        res = r["resurrection_condition"]
        chk(A, f"{cid} resurrection condition non-trivial",
            isinstance(res, str) and len(res) > 60 and res != "UNKNOWN", res[:60])
        reason = r["kill_reason"]
        chk(A, f"{cid} kill_reason names its measured scope",
            ("scoped to that single window" in reason)
            or ("Measured on the 2026-03-05..2026-09-28 panel" in reason), reason[-120:])
    dead = list(csv.DictReader(open(os.environ.get(
        "V4_DEAD_PATH", os.path.join(REPO, "M1/data/dead_candidates.csv")))))
    dd = {r["candidate_id"]: r for r in dead}
    for cid in ("TUP-CME-ES-H3-OFI-AGG", "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"):
        chk(A, f"{cid} in dead_candidates with re-entry policy",
            cid in dd and dd[cid]["status"] == "DEAD"
            and dd[cid]["requires_explicit_resurrection_decision"] == "YES",
            dd.get(cid, {}).get("re_entry_policy"))
    summary = json.load(open(os.path.join(REPO, "M1/output/M1_STATE_SUMMARY.json")))
    chk(A, "counts ALIVE0/WEAK3/UNKNOWN15/DEAD12 over 30",
        summary["counts"].get("candidate_rows") == 30
        and {k: v for k, v in summary["counts"].items() if k in ("candidate_rows",)} == {"candidate_rows": 30})
    closure = json.load(open(os.path.join(REPO, "M1/output/M1_CLOSURE_STATUS.json")))
    chk(A, "closure candidate_counts == expected",
        closure["candidate_counts"] == {"ALIVE": 0, "DEAD": 12, "UNKNOWN": 15, "WEAK": 3, "total": 30},
        closure["candidate_counts"])
    chk(A, "gate_eligible empty", closure["gate_eligible"] == [], closure["gate_eligible"])
    chk(A, "ceiling_violations 0", summary["counts"].get("ceiling_violations") == 0,
        summary["counts"].get("ceiling_violations"))
    chk(A, "recorded_kills list has both branches",
        {"TUP-CME-ES-H3-OFI-AGG", "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"}
        <= set(summary["recorded_kills"]))
    # cross-check the csv itself
    from collections import Counter
    ctr = Counter(r["overall_status"] for r in C.values())
    chk(A, "csv status counter matches 0/3/15/12",
        dict(ctr) == {"WEAK": 3, "DEAD": 12, "UNKNOWN": 15}, dict(ctr))
    gate_rows = list(csv.DictReader(open(os.environ.get(
        "V4_GATE_STATUS_PATH", os.path.join(REPO, "M1/output/candidate_gate_status.csv")))))
    ceilings = Counter(r["status_ceiling"] for r in gate_rows)
    chk(A, "no candidate row's status ceiling exceeds NOT_ALIVE",
        set(ceilings) <= {"NOT_ALIVE", "DEAD"}, dict(ceilings))
    chk(A, "gate-eligible set is empty in the state summary",
        summary["counts"].get("m1b_eligible") == [], summary["counts"].get("m1b_eligible"))

    # ---------------- A4: auction rows ----------------
    A = "A4"
    auc = C["TUP-NASDAQ-CLOSE-H4-LATENOII-AGG"]
    chk(A, "auction candidate carries no kill/survival verdict",
        auc["kill_status"] == "UNKNOWN" and auc["kill_gate"] == "UNKNOWN"
        and auc["overall_status"] == "UNKNOWN" and auc["resurrection_condition"] == "UNKNOWN",
        {k: auc[k] for k in ("overall_status", "kill_gate", "kill_status", "resurrection_condition")})
    dd_auc = {r["candidate_id"] for r in dead}
    chk(A, "auction candidate absent from dead_candidates", auc["candidate_id"] not in dd_auc)
    par = C["TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG"]
    chk(A, "auction parent unrevived",
        par["overall_status"] == "UNKNOWN" and par["kill_status"] == "UNKNOWN"
        and par["kill_gate"] == "UNKNOWN")
    # history: parent status vector identical in every revision that contains it
    hist = subprocess.run(["git", "log", "--format=%h", "--", "M1/data/candidate_tuples.csv"],
                          capture_output=True, text=True, cwd=REPO).stdout.split()
    pid = "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG"
    pre_bridge = "9e5026f"   # last revision touching candidate_tuples.csv before the bridge campaign
    prows = git_rows(pre_bridge)
    diffs = {k: (v, par.get(k)) for k, v in prows.get(pid, {}).items() if v != par.get(k)}
    chk(A, f"auction parent row unchanged since {pre_bridge} except gate_recompute_date",
        set(diffs) <= {"gate_recompute_date"}, diffs)
    status_hist = []
    for rev in hist:
        rows = git_rows(rev)
        if pid in rows and "kill_status" in rows[pid]:
            status_hist.append((rev, rows[pid]["overall_status"], rows[pid]["kill_status"],
                                rows[pid]["kill_gate"]))
    chk(A, "auction parent status vector UNKNOWN/UNKNOWN/UNKNOWN in every revision",
        all(s[1:] == ("UNKNOWN", "UNKNOWN", "UNKNOWN") for s in status_hist),
        [s for s in status_hist if s[1:] != ("UNKNOWN", "UNKNOWN", "UNKNOWN")])
    # OQ-0017 present
    oq = {r["question_id"]: r for r in
          csv.DictReader(open(os.path.join(REPO, "M1/data/open_questions.csv")))}
    chk(A, "OQ-0017 present and open as the auction next action",
        "OQ-0017" in oq and "warm-up" in oq["OQ-0017"]["question"],
        oq.get("OQ-0017", {}).get("question", "")[:100])
    chk(A, "OQ-0017 scoped as an M2_ENTRY gate question",
        str(oq["OQ-0017"].get("answer_required_before_gate", "")).strip() != ""
        and oq["OQ-0017"].get("answer_required_before_gate") != "UNKNOWN",
        oq["OQ-0017"].get("answer_required_before_gate"))

    out = {"total": len(CHECKS), "ok": sum(1 for c in CHECKS if c["ok"]),
           "failures": [c for c in CHECKS if not c["ok"]],
           "by_item": {i: {"n": sum(1 for c in CHECKS if c["item"] == i),
                           "ok": sum(1 for c in CHECKS if c["item"] == i and c["ok"])}
                       for i in ("A2", "A3", "A4")}}
    print(json.dumps(out, indent=1))
    with open(os.path.join(V4, "v4_a2_a4_canonical.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return 0 if not out["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())