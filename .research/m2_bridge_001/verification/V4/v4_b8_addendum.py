#!/usr/bin/env python3
"""V4 claim B8: the ES addendum reproduces its committed JSON byte-identically
and modifies no sealed artefact.

Runs the committed addendum script twice (to a V4 path, and to stdout) and
compares both against the committed JSON; hashes every sealed ES artefact before
and after.

Usage: .venv/bin/python3 v4_b8_addendum.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

V4 = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(V4, "..", "..", "..", ".."))
ES = os.path.join(REPO, "M2/experiments/M2-BRIDGE-ES-H3-OFI")
PY = os.path.join(REPO, ".venv/bin/python3")
SCRIPT = os.path.join(ES, "addendum_unconditional_matched_instants.py")
COMMITTED = os.path.join(ES, "addendum_unconditional_matched_instants.json")
SEALED = ["freeze.json", "freeze.sha256", "run_inputs.json", "results.json", "proposal.json"]

CHECKS = []


def chk(item, label, ok, detail=""):
    CHECKS.append({"item": item, "label": label, "ok": bool(ok), "detail": str(detail)})
    return bool(ok)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def snapshot():
    snap = {name: sha256_file(os.path.join(ES, name)) for name in SEALED}
    snap["addendum.json"] = sha256_file(COMMITTED)
    snap["addendum.py"] = sha256_file(SCRIPT)
    return snap


def main() -> int:
    before = snapshot()
    # the addendum script's own seal: it records the results.json hash it read
    committed = json.load(open(COMMITTED))
    chk("B8", "addendum records the sealed results.json hash it used",
        committed["results_json_sha256"] == before["results.json"],
        {"recorded": committed["results_json_sha256"], "observed": before["results.json"]})
    chk("B8", "addendum records the freeze hash of the sealed freeze",
        committed["freeze_sha256"] == before["freeze.json"]
        == open(os.path.join(ES, "freeze.sha256")).read().split()[0],
        committed["freeze_sha256"])
    chk("B8", "addendum script sha256 matches the hash it records",
        committed["script"]["sha256"] == before["addendum.py"],
        {"recorded": committed["script"]["sha256"], "observed": before["addendum.py"]})

    out = os.path.join(V4, "v4_addendum_rerun.json")
    proc = subprocess.run([PY, SCRIPT, "--out", out], capture_output=True, text=True, cwd=REPO)
    chk("B8", "addendum re-run exits 0", proc.returncode == 0, proc.stderr.strip()[-300:])
    chk("B8", "addendum re-run is byte-identical to the committed JSON",
        sha256_file(out) == before["addendum.json"],
        {"rerun": sha256_file(out), "committed": before["addendum.json"]})

    proc2 = subprocess.run([PY, SCRIPT], capture_output=True, text=True, cwd=REPO)
    chk("B8", "addendum stdout path also reproduces the committed JSON",
        proc2.returncode == 0 and proc2.stdout == open(COMMITTED).read(),
        {"stdout_sha256": hashlib.sha256(proc2.stdout.encode()).hexdigest(),
         "committed_sha256": before["addendum.json"]})

    after = snapshot()
    changed = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
    chk("B8", "no sealed ES artefact changed across the re-run", not changed, changed)
    chk("B8", "addendum JSON itself unchanged by the re-run", before["addendum.json"] == after["addendum.json"])
    # git view of the experiment directory
    git = subprocess.run(["git", "status", "--porcelain", "--", "M2/experiments/M2-BRIDGE-ES-H3-OFI"],
                         capture_output=True, text=True, cwd=REPO).stdout.strip()
    lines = [l for l in git.splitlines() if l.strip()]
    chk("B8", "ES experiment directory has no modified/deleted sealed artefact in git status",
        all(l.startswith("??") for l in lines)
        and sorted(l[3:] for l in lines)
        == ["M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.json",
            "M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.py"],
        git)

    res = {"total": len(CHECKS), "ok": sum(1 for c in CHECKS if c["ok"]),
           "failures": [c for c in CHECKS if not c["ok"]], "item": "B8",
           "sealed_hashes": before}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(V4, "v4_b8_addendum.json"), "w"), indent=1)
    return 0 if not res["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())