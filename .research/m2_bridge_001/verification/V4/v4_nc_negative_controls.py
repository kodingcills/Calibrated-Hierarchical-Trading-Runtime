#!/usr/bin/env python3
"""V4 item 11: negative controls — prove the comparison machinery can fail.

NC1  a perturbed COPY of the canonical candidate tuples (one row flipped to ALIVE)
     must break the canonical-state checker's count/status checks.
NC2  a fabricated number injected into an EVD claim must be reported as untraceable
     by the reverse numeric trace.
NC3  a rounded/altered headline number in a COPY of the canonical ledger must be
     flagged by a claim-vs-artifact numeric comparison.

Every artefact written here lives under the V4 directory. The canonical files are
never touched.

Usage: .venv/bin/python3 v4_nc_negative_controls.py
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys

V4 = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(V4, "..", "..", "..", ".."))
PY = os.path.join(REPO, ".venv/bin/python3")

CHECKS = []


def chk(item, label, ok, detail=""):
    CHECKS.append({"item": item, "label": label, "ok": bool(ok), "detail": str(detail)})
    return bool(ok)


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)


def main() -> int:
    # ---------------- NC1: perturbed candidate tuples ----------------
    src = os.path.join(REPO, "M1/data/candidate_tuples.csv")
    rows = read_csv(src)
    fields = list(rows[0].keys())
    pert = json.loads(json.dumps(rows))
    target = "TUP-CME-NQ-H3-OFI-AGG"
    for r in pert:
        if r["candidate_id"] == target:
            r["overall_status"] = "ALIVE"
    nc_cands = os.path.join(V4, "nc_perturbed_candidate_tuples.csv")
    write_csv(nc_cands, pert, fields)
    env = {**os.environ, "V4_CANDIDATES_PATH": nc_cands}
    proc = subprocess.run([PY, os.path.join(V4, "v4_a2_a4_canonical.py")],
                          capture_output=True, text=True, env=env, cwd=REPO)
    baseline = subprocess.run([PY, os.path.join(V4, "v4_a2_a4_canonical.py")],
                              capture_output=True, text=True, cwd=REPO)
    chk("NC1", "checker passes on the canonical candidate tuples", baseline.returncode == 0)
    chk("NC1", "checker FAILS on the perturbed copy", proc.returncode != 0)
    chk("NC1", "the failure names the status/count check",
        "csv status counter" in proc.stdout or "closure candidate_counts" in proc.stdout,
        [l for l in proc.stdout.splitlines() if "count" in l.lower()][:3])

    # ---------------- NC2: fabricated evidence number ----------------
    src_led = os.path.join(REPO, "M1/data/evidence_ledger.csv")
    lrows = read_csv(src_led)
    lfields = list(lrows[0].keys())
    fabricated = "0.0314159"
    for r in lrows:
        if r["evidence_id"] == "EVD-0071":
            r["claim"] = r["claim"] + (
                f" The pooled markout is corroborated at {fabricated} bps by a second independent "
                "computation over 1,234,567 extra slots.")
    nc_led = os.path.join(V4, "nc_perturbed_evidence_ledger.csv")
    write_csv(nc_led, lrows, lfields)
    env = {**os.environ, "V4_LEDGER_PATH": nc_led}
    proc = subprocess.run([PY, os.path.join(V4, "v4_a1b_unmapped_tokens.py")],
                          capture_output=True, text=True, env=env, cwd=REPO)
    rep = json.load(open(os.path.join(V4, "v4_a1b_unmapped_tokens.json")))
    unmatched = rep["unmatched_by_evd"]["EVD-0071"]["unmatched_numbers"]
    baseline = subprocess.run([PY, os.path.join(V4, "v4_a1b_unmapped_tokens.py")],
                              capture_output=True, text=True, cwd=REPO)
    base_rep = json.load(open(os.path.join(V4, "v4_a1b_unmapped_tokens.json")))
    chk("NC2", "reverse trace passes on the canonical ledger",
        baseline.returncode == 0
        and all(not v["unmatched_numbers"] for v in base_rep["unmatched_by_evd"].values()),
        base_rep["unmatched_by_evd"]["EVD-0071"])
    chk("NC2", "reverse trace FLAGS the fabricated number",
        fabricated in unmatched, unmatched)
    chk("NC2", "reverse trace flags the fabricated count too",
        "1,234,567" in unmatched or "1234567" in unmatched, unmatched)

    # ---------------- NC3: perturbed headline number in the ledger ----------------
    #        (a claim -> artifact numeric comparison, same rule as the A1 table)
    es = json.load(open(os.path.join(REPO, "M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json")))
    truth = es["headline"]["gross_markout_bps"]
    perturbed_claim = "-0.0047436"          # one digit changed vs -0.0047336
    dp = len(perturbed_claim.split(".")[1])
    chk("NC3", "comparison rule accepts the true number",
        f"{truth:.{dp}f}" == "-0.0047336", f"{truth:.{dp}f}")
    chk("NC3", "comparison rule REJECTS the perturbed number",
        f"{truth:.{dp}f}" != perturbed_claim, {"claim": perturbed_claim, "artifact": f"{truth:.{dp}f}"})
    # and the same rule applied to the two-copy checking path end to end
    pert2 = json.loads(json.dumps(lrows))
    for r in pert2:
        if r["evidence_id"] == "EVD-0071":
            r["claim"] = r["claim"].replace("-0.0047336", perturbed_claim)
    nc_led2 = os.path.join(V4, "nc_perturbed_ledger_number.csv")
    write_csv(nc_led2, pert2, lfields)
    env = {**os.environ, "V4_LEDGER_PATH": nc_led2}
    subprocess.run([PY, os.path.join(V4, "v4_a1b_unmapped_tokens.py")],
                   capture_output=True, text=True, env=env, cwd=REPO)
    rep3 = json.load(open(os.path.join(V4, "v4_a1b_unmapped_tokens.json")))
    chk("NC3", "perturbed headline number is reported untraceable in the ledger copy",
        perturbed_claim in rep3["unmatched_by_evd"]["EVD-0071"]["unmatched_numbers"],
        rep3["unmatched_by_evd"]["EVD-0071"]["unmatched_numbers"])
    # restore the report from the canonical ledger for the file artefact
    subprocess.run([PY, os.path.join(V4, "v4_a1b_unmapped_tokens.py")],
                   capture_output=True, text=True, cwd=REPO)

    res = {"total": len(CHECKS), "ok": sum(1 for c in CHECKS if c["ok"]),
           "failures": [c for c in CHECKS if not c["ok"]],
           "controls": {i: {"n": sum(1 for c in CHECKS if c["item"] == i),
                            "ok": sum(1 for c in CHECKS if c["item"] == i and c["ok"])}
                        for i in ("NC1", "NC2", "NC3")}}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(V4, "v4_nc_negative_controls.json"), "w"), indent=1)
    return 0 if not res["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())