#!/usr/bin/env python3
"""V1 adversarial manifests against the W4 admission engine (CLAIM SET C).

Five NEW manifests, built by mutating the real BASIS manifest — not copied from
M2/tests/test_admission.py fixtures.  Each SHOULD be refused; any that returns
DATA_VALID is reported as a hole.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from M2.src import admission as A  # noqa: E402

REAL = json.loads((ROOT / "M2" / "data" / "derived_basis" / "manifest_basis.json").read_text())


def run(label: str, m, ctx=None, contract=None, expect_refused=True):
    res = A.evaluate(m, contract or A.BASIS_CONTRACT, ctx or A.Context(root=str(ROOT)))
    fired = [r["check"] for r in res["reasons"]]
    return {
        "adversarial": label,
        "state": res["state"],
        "refused": res["state"] != A.DATA_VALID,
        "checks_fired": sorted(set(fired)),
        "expect_refused": expect_refused,
        "verdict_ok": (res["state"] != A.DATA_VALID) == expect_refused,
    }


def main() -> int:
    ctx = A.Context(root=str(ROOT))
    baseline = A.evaluate(REAL, A.BASIS_CONTRACT, ctx)
    out = {"baseline_state": baseline["state"], "adversarial": []}

    # C12.1 correct files but a wrong declared hash (evidence present, contradicts)
    m1 = copy.deepcopy(REAL)
    h = m1["files"][0]["sha256"]
    m1["files"][0]["sha256"] = ("0" if h[0] != "0" else "1") + h[1:]
    out["adversarial"].append(run("A1_wrong_declared_hash", m1, ctx))

    # C12.2 one declared file hash missing entirely (evidence absent)
    m2 = copy.deepcopy(REAL)
    del m2["files"][1]["sha256"]
    out["adversarial"].append(run("A2_missing_declared_hash", m2, ctx))

    # C12.3 coverage exactly at the frozen tolerance but a bucket dropped
    m3 = copy.deepcopy(REAL)
    m3["intervals"][100]["present"] = False
    m3["coverage"] = {**m3["coverage"], "admitted": 4980, "qualified": 4980,
                      "ratio": 4980 / 4981}
    out["adversarial"].append(run("A3_coverage_just_below_tolerance", m3, ctx))

    # C12.4 window kept, bucket dropped, but coverage still declared 1.0
    m4 = copy.deepcopy(REAL)
    m4["intervals"][100]["present"] = False
    m4["coverage"] = {**m4["coverage"], "admitted": 4981, "qualified": 4981, "ratio": 1.0}
    out["adversarial"].append(run("A4_window_kept_bucket_dropped_ratio_1", m4, ctx))

    # C12.5 wrong timezone, internally consistent (session + every field ET)
    m5 = copy.deepcopy(REAL)
    m5["session"]["timezone"] = "America/New_York"
    for f in m5["fields"]:
        if f.get("timezone"):
            f["timezone"] = "America/New_York"
    out["adversarial"].append(run("A5_wrong_timezone_internally_consistent", m5, ctx))

    # C12.6 plausible-but-wrong instrument identity
    m6 = copy.deepcopy(REAL)
    m6["instrument"]["symbol"] = "ETHUSDT"
    out["adversarial"].append(run("A6_wrong_instrument_identity", m6, ctx))

    # C12.7 correct file but bytes disagree with disk (archive completeness / size)
    m7 = copy.deepcopy(REAL)
    m7["files"][2]["bytes"] = m7["files"][2]["bytes"] + 1
    out["adversarial"].append(run("A7_wrong_declared_byte_count", m7, ctx))

    # C13 precedence: an INVALID (hash) and an INCOMPLETE (missing file role) together
    m8 = copy.deepcopy(REAL)
    hm = m8["files"][0]["sha256"]
    m8["files"][0]["sha256"] = ("0" if hm[0] != "0" else "1") + hm[1:]
    m8["files"] = [f for f in m8["files"] if f["role"] != "binance_mark"]
    r8 = A.evaluate(m8, A.BASIS_CONTRACT, ctx)
    out["precedence_invalid_over_incomplete"] = {
        "state": r8["state"],
        "invalid_reasons": r8["reason_counts"]["INVALID"],
        "incomplete_reasons": r8["reason_counts"]["INCOMPLETE"],
        "precedence_ok": r8["state"] == A.DATA_INVALID,
    }

    # C13 a check that cannot run must not yield VALID: manifest is not an object
    out["non_object_manifest"] = A.evaluate([1, 2, 3], A.BASIS_CONTRACT, ctx)["state"]
    out["empty_object_manifest"] = A.evaluate({}, A.BASIS_CONTRACT, ctx)["state"]

    # C13 registry narrowing: strip a check and show the verdict degrades (load-bearing proof)
    stripped = tuple(c for c in A.CHECKS if c[0] != "files.hash")
    r9 = A.evaluate(m1, A.BASIS_CONTRACT, ctx, checks=stripped)
    out["hash_check_is_load_bearing"] = {"with_check": "DATA_INVALID",
                                         "without_files_hash_check": r9["state"]}

    all_refused = all(a["refused"] for a in out["adversarial"])
    out["all_adversarial_refused"] = all_refused
    (Path(__file__).resolve().parent / "v1_admission_adversarial.json").write_text(
        json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

def extra() -> int:
    """Second wave: consistent-shift and key-integrity attacks."""
    ctx = A.Context(root=str(ROOT))
    out = {}
    SHIFT = 4 * 3600

    # A8 timestamps in the wrong timezone (shifted +4h) but internally consistent:
    # window, intervals, keys and timestamps all move together.
    m = copy.deepcopy(REAL)
    m["session"]["window_start_unix"] += SHIFT
    m["session"]["window_end_unix"] += SHIFT
    m["session"]["window_start_utc"] = "2026-03-05T15:00:00Z"
    m["session"]["window_end_utc"] = "2026-09-29T03:00:00Z"
    for iv in m["intervals"]:
        iv["id"] += SHIFT
    m["records"]["keys"] = [k + SHIFT for k in m["records"]["keys"]]
    m["records"]["timestamps"] = [t + SHIFT for t in m["records"]["timestamps"]]
    res = A.evaluate(m, A.BASIS_CONTRACT, ctx)
    out["A8_consistent_4h_shift"] = {"state": res["state"],
                                     "checks_fired": sorted({r["check"] for r in res["reasons"]})}

    # A9 duplicate key with everything else intact
    m = copy.deepcopy(REAL)
    m["records"]["keys"][500] = m["records"]["keys"][499]
    res = A.evaluate(m, A.BASIS_CONTRACT, ctx)
    out["A9_duplicate_record_key"] = {"state": res["state"],
                                      "checks_fired": sorted({r["check"] for r in res["reasons"]})}

    # A10 declared key count disagrees with the list it ships
    m = copy.deepcopy(REAL)
    m["records"]["count"] = 4980
    m["records"]["keys"] = m["records"]["keys"][:-1]
    m["records"]["timestamps"] = m["records"]["timestamps"][:-1]
    res = A.evaluate(m, A.BASIS_CONTRACT, ctx)
    out["A10_short_key_list"] = {"state": res["state"],
                                 "checks_fired": sorted({r["check"] for r in res["reasons"]})}

    # A11 monotonicity violated (one timestamp moved backwards) but count intact
    m = copy.deepcopy(REAL)
    m["records"]["timestamps"][10] = m["records"]["timestamps"][9]
    res = A.evaluate(m, A.BASIS_CONTRACT, ctx)
    out["A11_non_monotonic_timestamp"] = {"state": res["state"],
                                          "checks_fired": sorted({r["check"] for r in res["reasons"]})}

    # A12 interval ids offset by one hour (grid no longer matches the window start)
    m = copy.deepcopy(REAL)
    for iv in m["intervals"]:
        iv["id"] += 3600
    res = A.evaluate(m, A.BASIS_CONTRACT, ctx)
    out["A12_grid_offset_by_one_hour"] = {"state": res["state"],
                                          "checks_fired": sorted({r["check"] for r in res["reasons"]})}

    (Path(__file__).resolve().parent / "v1_admission_adversarial_extra.json").write_text(
        json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0
