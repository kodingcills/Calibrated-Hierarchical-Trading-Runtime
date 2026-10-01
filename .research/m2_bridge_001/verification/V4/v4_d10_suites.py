#!/usr/bin/env python3
"""V4 claim C10: the project's own gates still pass.

Runs the M2 unit-test discovery and the M1 strict validator and records their
verbatim tail output. NOTE: ``M1/src/validate.py`` rewrites
``M1/validation/report.{json,md}`` with a fresh ``generated_at`` as a side effect;
this script records that, and the report body is shown to be deterministic by
re-running the validator and diffing the two reports modulo that field.

Usage: .venv/bin/python3 v4_d10_suites.py
"""

from __future__ import annotations

import hashlib
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


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    return p.returncode, p.stdout, p.stderr


def report_body(path):
    d = json.load(open(path))
    d.pop("generated_at", None)
    return json.dumps(d, sort_keys=True, indent=1)


def main() -> int:
    rc, out, err = run([PY, "-m", "unittest", "discover", "-s", "M2/tests", "-t", "."])
    tail = "\n".join(err.strip().splitlines()[-3:])
    chk("C10", "M2 unittest discovery passes in full",
        rc == 0 and "\nOK" in err and "Ran 332 tests" in err, tail)

    rc2, out2, err2 = run([PY, "M1/src/validate.py", "--strict"])
    chk("C10", "M1 validate --strict returns PASS with 0 failures",
        rc2 == 0 and '"overall": "PASS"' in out2 and '"failures": 0' in out2, out2.strip())
    body1 = report_body(os.path.join(REPO, "M1/validation/report.json"))
    rc3, out3, _ = run([PY, "M1/src/validate.py", "--strict"])
    body2 = report_body(os.path.join(REPO, "M1/validation/report.json"))
    chk("C10", "validator report body is deterministic modulo generated_at",
        body1 == body2, {"run1_rc": rc2, "run2_rc": rc3})
    chk("C10", "validator side effect disclosed: generated_at is rewritten",
        '"generated_at"' in open(os.path.join(REPO, "M1/validation/report.json")).read(),
        "M1/validation/report.{json,md} are outputs of validate.py")

    res = {"total": len(CHECKS), "ok": sum(1 for c in CHECKS if c["ok"]),
           "failures": [c for c in CHECKS if not c["ok"]], "item": "C10",
           "m2_suite_tail": tail, "m1_validate": out2.strip()}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(V4, "v4_d10_suites.json"), "w"), indent=1)
    return 0 if not res["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())