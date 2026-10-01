#!/usr/bin/env python3
"""V4 claim A1b: every numeric token in the EVD-0071..0075 claim text must be
recoverable from the cited artifacts or from an explicit derivation.

The forward table in v4_a1_ledger_trace.py proves a chosen set of numbers.  This
script is the reverse direction: it tokenises the raw canonical text, and for each
token asks whether *any* scalar in the cited artifact set (sealed JSON files, plus
the V1/V2/V3 verification reports) reproduces it at that token's precision, or
whether it is one of the explicitly enumerated derived quantities.  Anything left
is printed for manual review.

Usage: .venv/bin/python3 v4_a1b_unmapped_tokens.py
"""

from __future__ import annotations

import csv
import json
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
V4 = os.path.dirname(os.path.abspath(__file__))

ARTIFACTS = [
    "M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json",
    "M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json",
    "M2/experiments/M2-BRIDGE-ES-H3-OFI/run_inputs.json",
    "M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.json",
    "M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/freeze.json",
    "M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/results.json",
    "M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/run_inputs.json",
    "M2/experiments/M2-BRIDGE-HL-BINANCE-BASIS/base_tier_scenario.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/freeze.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/results.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/run_inputs.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/admission_v2_result.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/certificate.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/proposal.json",
]
REPORTS = [
    ".research/m2_bridge_001/verification/V1/REPORT.md",
    ".research/m2_bridge_001/verification/V2/REPORT.md",
    ".research/m2_bridge_001/verification/V3/REPORT.md",
]

NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
HEX = re.compile(r"\b[0-9a-f]{8,64}\b")
MINUS = "\u2212"  # U+2212 MINUS SIGN is used in the verification reports


def scalars(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            scalars(v, out)
    elif isinstance(obj, list):
        for v in obj:                      # per-record arrays ARE in scope: the EVD
            scalars(v, out)                # cites counts derived from them
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, str):
        for m in NUM.finditer(obj):
            try:
                out.append(float(m.group().replace(",", "")))
            except ValueError:
                pass


def main() -> int:
    universe = []
    for rel in ARTIFACTS:
        with open(os.path.join(REPO, rel)) as fh:
            scalars(json.load(fh), universe)
    for rel in REPORTS:
        with open(os.path.join(REPO, rel)) as fh:
            for m in NUM.finditer(fh.read().replace(MINUS, "-")):
                try:
                    universe.append(float(m.group().replace(",", "")))
                except ValueError:
                    pass
    universe = sorted(set(universe))

    rows = {r["evidence_id"]: r for r in
            csv.DictReader(open(os.environ.get(
                "V4_LEDGER_PATH", os.path.join(REPO, "M1/data/evidence_ledger.csv"))))}
    # quantities the ledger states as derived/directional rather than quoted, or that
    # name a source field that is not a scalar (checked by hand in the REPORT):
    ALLOW_NON_NUMERIC = set()
    results = {}
    for eid in ["EVD-0071", "EVD-0072", "EVD-0073", "EVD-0074", "EVD-0075"]:
        text = " ".join(rows[eid][k] for k in
                        ("claim", "methodology", "sample", "limitations", "decision_implication"))
        text = text.replace(MINUS, "-")
        hexes = set(HEX.findall(text))
        text = HEX.sub(" HASH ", text)
        tokens = []
        for m in NUM.finditer(text):
            tok = m.group()
            tokens.append(tok)
        unmatched = set()
        for tok in tokens:
            t = tok.replace(",", "")
            if "." in t:
                dp = len(t.split(".")[1])
                want = f"{float(t):.{dp}f}"
                if any(f"{u:.{dp}f}" == want for u in universe):
                    continue
            else:
                if float(t) in universe:
                    continue
            unmatched.add(tok)
        results[eid] = {"unmatched_numbers": sorted(unmatched), "hex_tokens": sorted(hexes)}
    print(json.dumps(results, indent=1))
    with open(os.path.join(V4, "v4_a1b_unmapped_tokens.json"), "w") as fh:
        json.dump({"unmatched_by_evd": results, "universe_size": len(universe)}, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())