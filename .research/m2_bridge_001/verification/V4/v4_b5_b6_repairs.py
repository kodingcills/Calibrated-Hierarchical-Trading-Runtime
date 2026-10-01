#!/usr/bin/env python3
"""V4 claims B5/B6: the repairs hold — independent re-derivation.

B5  hash M2/src/admission.py and compare with the BASIS freeze's sealed value, then
    re-resolve every one of the BASIS freeze's sealed code/input hashes.
B6  run the (relocated) AUCTION v2 CLI against the SEALED manifest and compare the
    canonicalised result with the sealed admission_v2_result.json.

Writes only under the V4 directory.

Usage: .venv/bin/python3 v4_b5_b6_repairs.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

V4 = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(V4, "..", "..", "..", ".."))
BASIS = os.path.join(REPO, "M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS")
AUC = os.path.join(REPO, "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY")
PY = os.path.join(REPO, ".venv/bin/python3")

CHECKS = []


def chk(item, label, ok, detail=""):
    CHECKS.append({"item": item, "label": label, "ok": bool(ok), "detail": str(detail)})
    return bool(ok)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    freeze = json.load(open(os.path.join(BASIS, "freeze.json")))
    sealed = freeze["inputs_sha256"]["code"]["M2/src/admission.py"]
    here = sha256(os.path.join(REPO, "M2/src/admission.py"))
    chk("B5", "admission.py matches the BASIS freeze's sealed hash",
        here == sealed == "9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477",
        here)
    chk("B5", "admission.py matches the freeze.sha256-sealed freeze.json",
        sha256(os.path.join(BASIS, "freeze.json"))
        == open(os.path.join(BASIS, "freeze.sha256")).read().split()[0])
    # independent git check: the sealed hash is the version committed at ac28929
    blob = subprocess.run(["git", "show", "ac28929:M2/src/admission.py"],
                          capture_output=True, cwd=REPO)
    chk("B5", "sealed hash equals the committed blob at ac28929",
        hashlib.sha256(blob.stdout).hexdigest() == sealed,
        hashlib.sha256(blob.stdout).hexdigest())
    # the whole BASIS sealed set resolves
    resolved, missing, bad = 0, [], []
    total = 0
    for group, entries in freeze["inputs_sha256"].items():
        for rel, want in entries.items():
            total += 1
            cand = os.path.join(REPO, rel)
            if not os.path.exists(cand):
                upper = os.path.join(BASIS, rel)
                if os.path.exists(upper):
                    cand = upper
            if not os.path.exists(cand):
                missing.append(rel)
                continue
            got = sha256(cand)
            if got == want:
                resolved += 1
            else:
                bad.append({"path": rel, "declared": want, "observed": got})
    chk("B5", "all 155 BASIS sealed entries resolve", total == 155 and resolved == 155,
        {"total": total, "resolved": resolved, "missing": missing, "drift": bad})
    # group breakdown (independently counted)
    chk("B5", "BASIS sealed groups sum to 155",
        sum(len(v) for v in freeze["inputs_sha256"].values()) == 155,
        {k: len(v) for k, v in freeze["inputs_sha256"].items()})
    # the restored module is the one the BASIS run actually consumed
    run_inputs = json.load(open(os.path.join(BASIS, "run_inputs.json")))
    chk("B5", "BASIS run_inputs records the same sealed value for admission.py",
        run_inputs["code_and_input_sha256"]["code"]["M2/src/admission.py"] == sealed,
        run_inputs["code_and_input_sha256"]["code"]["M2/src/admission.py"])

    # ---- B6: AUCTION v2 CLI on the SEALED manifest ----
    manifest = os.path.join(AUC, "admission_manifest_v2.json")
    out = os.path.join(V4, "auction_v2_rerun.json")
    proc = subprocess.run(
        [PY, "-m", "M2.src.admission_auction", "--manifest", manifest,
         "--branch", "AUCTION_V2", "--root", REPO, "--json-out", out],
        capture_output=True, text=True, cwd=REPO)
    chk("B6", "CLI exits 0 on the sealed manifest", proc.returncode == 0,
        proc.stdout.strip().splitlines()[:1] + proc.stderr.strip().splitlines()[-2:])
    rerun = json.load(open(out))
    sealed_res = json.load(open(os.path.join(AUC, "admission_v2_result.json")))
    chk("B6", "rerun state == sealed state",
        rerun["state"] == sealed_res["state"] == "DATA_VALID",
        (rerun["state"], sealed_res["state"]))
    chk("B6", "rerun checks_run == sealed checks_run (same set and order)",
        rerun["checks_run"] == sealed_res["checks_run"],
        [c for c in rerun["checks_run"] if c not in sealed_res["checks_run"]]
        + [c for c in sealed_res["checks_run"] if c not in rerun["checks_run"]])
    chk("B6", "rerun keeps both contract-scoped checks",
        "session.continuity" in rerun["checks_run"]
        and "coverage.certificate" in rerun["checks_run"])
    chk("B6", "rerun reasons == sealed reasons",
        rerun["reasons"] == sealed_res["reasons"], rerun["reasons"])
    chk("B6", "rerun reason_counts == sealed reason_counts",
        rerun["reason_counts"] == sealed_res["reason_counts"])
    chk("B6", "rerun notes == sealed notes",
        rerun["notes"] == sealed_res["notes"])
    chk("B6", "rerun contract/ids unchanged",
        (rerun["contract_id"], rerun["manifest_id"], rerun["dataset_id"])
        == (sealed_res["contract_id"], sealed_res["manifest_id"], sealed_res["dataset_id"]))
    chk("B6", "canonicalised rerun is byte-identical to the sealed result",
        json.dumps(rerun, sort_keys=True) == json.dumps(sealed_res, sort_keys=True),
        {"rerun_sha256": sha256(out),
         "sealed_sha256": sha256(os.path.join(AUC, "admission_v2_result.json"))})

    res = {"total": len(CHECKS), "ok": sum(1 for c in CHECKS if c["ok"]),
           "failures": [c for c in CHECKS if not c["ok"]],
           "by_item": {i: {"n": sum(1 for c in CHECKS if c["item"] == i),
                           "ok": sum(1 for c in CHECKS if c["item"] == i and c["ok"])}
                       for i in ("B5", "B6")}}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(V4, "v4_b5_b6_repairs.json"), "w"), indent=1)
    return 0 if not res["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())