#!/usr/bin/env python3
"""V3 claim A1 (v2): recompute freeze sha256 and verify declared code/input hashes vs disk.

Read-only. For each declared 64-hex hash, resolve the file by trying successively
shorter suffixes of the key path against ROOT (longest suffix first). Prints JSON.
Interpreter: .venv/bin/python3
"""
import hashlib
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
EXP = os.path.join(ROOT, "M2", "experiments")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_hashes(obj, path=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(walk_hashes(v, f"{path}/{k}" if path else k))
    elif isinstance(obj, str) and len(obj) == 64:
        try:
            int(obj, 16)
        except ValueError:
            return out
        out.append((path, obj))
    return out


def resolve(key):
    parts = key.split("/")
    seen = []
    for i in range(len(parts)):
        cand = os.path.join(ROOT, *parts[i:])
        seen.append(cand)
        if os.path.isfile(cand):
            return cand, seen
    return None, seen


REPORT = {}
for d in ["M2-BRIDGE-ES-H3-OFI", "M2-BRIDGE-HL-BINANCE-BASIS",
          "M2-BRIDGE-AUCTION-LATENOII-MATERIALITY"]:
    ed = os.path.join(EXP, d)
    frz = os.path.join(ed, "freeze.json")
    sealf = os.path.join(ed, "freeze.sha256")
    rec = {"freeze_sha256_recomputed": sha256_file(frz)}
    with open(sealf) as fh:
        declared = fh.read().split()[0]
    rec["freeze_sha256_declared"] = declared
    rec["freeze_seal_match"] = (rec["freeze_sha256_recomputed"] == declared)
    f = json.load(open(frz))
    entries = walk_hashes(f)
    rec["declared_hash_entries"] = len(entries)
    mism, missing, ok = [], [], []
    for p, h in entries:
        cand, _ = resolve(p)
        if not cand:
            missing.append(p)
            continue
        got = sha256_file(cand)
        rel = os.path.relpath(cand, ROOT)
        if got == h:
            ok.append(rel)
        else:
            mism.append({"key": p, "file": rel, "declared": h, "ondisk": got})
    rec["ok_count"] = len(ok)
    rec["ok_files"] = sorted(set(ok))
    rec["mismatched"] = mism
    rec["not_found_on_disk"] = missing
    REPORT[d] = rec

print(json.dumps(REPORT, indent=1))
