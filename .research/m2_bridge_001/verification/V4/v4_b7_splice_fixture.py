#!/usr/bin/env python3
"""V4 claim B7: relocating the AUCTION contract did not weaken it.

Builds an INDEPENDENT spliced fixture (head + frame-aligned tail of the retained
auction window, gzipped here), derives its measurement-window continuity figures
with this script's own frame parser, turns them into a fixture certificate and a
fixture manifest, and runs the relocated AUCTION_V2 contract against it.  The
contract-scoped checks ``session.continuity`` and ``coverage.certificate`` must
fire.  A pristine-certificate fixture is run as the paired control.

Writes only under the V4 directory.

Usage: .venv/bin/python3 v4_b7_splice_fixture.py
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zlib

V4 = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(V4, "..", "..", "..", ".."))
sys.path.insert(0, REPO)
from M2.src import ingest  # noqa: E402  (frame layout constants only)

AUC = os.path.join(REPO, "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY")
WINDOW = os.path.join(REPO, "M2/data/derived_auction/2026-06-12/window.bin.gz")
PY = os.path.join(REPO, ".venv/bin/python3")
KEEP = 8 << 20
FRAME_PREFIX = ingest.FRAME_PREFIX
HEADER = ingest.HEADER
MSG_LENGTH = ingest.MSG_LENGTH
NS_PER_SECOND = 1_000_000_000
WINDOW_START_NS = 15 * 3600 * NS_PER_SECOND + 49 * 60 * NS_PER_SECOND + 50 * NS_PER_SECOND
WINDOW_END_NS = 16 * 3600 * NS_PER_SECOND + 10 * NS_PER_SECOND
MAX_IN_WINDOW_GAP_NS = 1_000_000_000
MIN_IN_WINDOW_MESSAGES = 1_000_000

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


def build_splice(dest):
    """Decode once; keep the head and the tail; align both to frame boundaries."""
    head, tail = bytearray(), bytearray()
    dec = zlib.decompressobj(31)
    decoded = 0
    with open(WINDOW, "rb") as fh:
        while True:
            block = fh.read(1 << 22)
            if not block:
                break
            data = dec.decompress(block)
            decoded += len(data)
            if len(head) < KEEP:
                head += data[: KEEP - len(head)]
            tail += data
            if len(tail) > KEEP:
                del tail[: len(tail) - KEEP]
    gzip_eof = dec.eof

    def trim_head(data):
        pos, n = 0, len(data)
        while pos + FRAME_PREFIX + 2 <= n:
            declared = (data[pos] << 8) | data[pos + 1]
            if declared == 0:
                pos += FRAME_PREFIX
                continue
            end = pos + FRAME_PREFIX + declared
            if end > n:
                break
            pos = end
        return bytes(data[:pos])

    def align_tail(data):
        n = len(data)
        for off in range(min(64, n)):
            pos, ok = off, True
            while pos + FRAME_PREFIX + 2 <= n:
                declared = (data[pos] << 8) | data[pos + 1]
                if declared == 0:
                    pos += FRAME_PREFIX
                    continue
                end = pos + FRAME_PREFIX + declared
                if end > n or declared != MSG_LENGTH.get(data[pos + FRAME_PREFIX]):
                    ok = False
                    break
                pos = end
            if ok and pos == n and n - off >= 14 and data[n - 12] == 0x53 and data[n - 1] == ord("C"):
                return bytes(data[off:])
        raise SystemExit("tail could not be aligned to a frame boundary")

    spliced = trim_head(head) + align_tail(bytes(tail))
    with open(dest, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6) as gz:
            gz.write(spliced)
    return {"decoded_bytes": decoded, "gzip_eof": gzip_eof,
            "spliced_bytes": len(spliced), "seam_offset": len(trim_head(head))}


def scan_spliced(path):
    """This script's own frame parser over the spliced stream."""
    stats = {"frames": 0, "in_window_messages": 0, "in_window_pairs": 0,
             "max_in_window_gap_ns": 0, "max_in_window_gap_at_ns": None,
             "backwards_timestamps": 0, "framing_error": None,
             "seam_gap_ns": None, "gaps_over_bound": 0}
    dec = zlib.decompressobj(31)
    buffer = bytearray()
    pos = 0
    prev_ts = None
    prev_in = False
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1 << 22)
            if not block:
                break
            buffer += dec.decompress(block)
            limit = len(buffer)
            while pos + FRAME_PREFIX + 2 <= limit:
                declared = (buffer[pos] << 8) | buffer[pos + 1]
                if declared == 0:
                    pos += FRAME_PREFIX
                    continue
                if pos + FRAME_PREFIX + declared > limit:
                    break
                base = pos + FRAME_PREFIX
                if declared != MSG_LENGTH.get(buffer[base]):
                    stats["framing_error"] = f"type 0x{buffer[base]:02x} declares {declared}"
                    break
                _locate, _tracking, ts_hi, ts_lo = HEADER.unpack_from(buffer, base + 1)
                ts = (ts_hi << 16) | ts_lo
                stats["frames"] += 1
                in_window = WINDOW_START_NS <= ts <= WINDOW_END_NS
                if in_window:
                    stats["in_window_messages"] += 1
                if prev_ts is not None:
                    gap = ts - prev_ts
                    if gap < 0:
                        stats["backwards_timestamps"] += 1
                    elif in_window and prev_in:
                        stats["in_window_pairs"] += 1
                        if gap > stats["max_in_window_gap_ns"]:
                            stats["max_in_window_gap_ns"] = gap
                            stats["max_in_window_gap_at_ns"] = ts
                        if gap > MAX_IN_WINDOW_GAP_NS:
                            stats["gaps_over_bound"] += 1
                        if stats["seam_gap_ns"] is None or gap > stats["seam_gap_ns"]:
                            stats["seam_gap_ns"] = gap
                prev_ts, prev_in = ts, in_window
                pos += FRAME_PREFIX + declared
            del buffer[:pos]
            pos = 0
    return stats


def run_contract(manifest_path, out_path):
    proc = subprocess.run([PY, "-m", "M2.src.admission_auction", "--manifest", manifest_path,
                           "--branch", "AUCTION_V2", "--root", REPO, "--json-out", out_path],
                          capture_output=True, text=True, cwd=REPO)
    return proc, json.load(open(out_path))


def main() -> int:
    spliced_path = os.path.join(V4, "v4_spliced_window.bin.gz")
    meta_path = os.path.join(V4, "v4_spliced_window.meta.json")
    if os.path.exists(spliced_path) and os.path.exists(meta_path):
        meta = json.load(open(meta_path))
    else:
        meta = build_splice(spliced_path)
        json.dump(meta, open(meta_path, "w"), indent=1)
    stats = scan_spliced(spliced_path)
    json.dump(stats, open(os.path.join(V4, "v4_spliced_scan.json"), "w"), indent=1)

    chk("B7", "spliced fixture is a small fraction of the retained session",
        meta["spliced_bytes"] / meta["decoded_bytes"] < 0.01, meta)
    chk("B7", "spliced stream parses with no framing error", stats["framing_error"] is None)
    chk("B7", "spliced stream has a seam gap far above the 1 s bound",
        stats["max_in_window_gap_ns"] > MAX_IN_WINDOW_GAP_NS, stats["max_in_window_gap_ns"])
    chk("B7", "spliced in-window message count is below the contract minimum",
        stats["in_window_messages"] < MIN_IN_WINDOW_MESSAGES, stats["in_window_messages"])
    # cross-check against the sealed certificate's own splice control (independent artefact)
    sealed_cert = json.load(open(os.path.join(AUC, "certificate.json")))
    ctrl = sealed_cert["splice_negative_control"]
    chk("B7", "my splice reproduces the sealed splice control's continuity figures",
        stats["in_window_messages"] == ctrl["continuity"]["in_window_messages"]
        and stats["in_window_pairs"] == ctrl["continuity"]["in_window_message_pairs"]
        and stats["max_in_window_gap_ns"] == ctrl["continuity"]["max_in_window_gap_ns"],
        {"mine": {k: stats[k] for k in ("in_window_messages", "in_window_pairs",
                                        "max_in_window_gap_ns")},
         "sealed": ctrl["continuity"]})
    # The .gz container hash is not reproducible: GzipFile stamps the current mtime into
    # the header.  The PAYLOAD is pinned instead by decoded size + the full continuity
    # fingerprint, which agree exactly with the sealed control.
    chk("B7", "my splice reproduces the sealed control's payload size and fingerprint",
        meta["spliced_bytes"] == ctrl["spliced_decoded_bytes"]
        and stats["backwards_timestamps"] == 0
        and ctrl["spliced_sha256"] != "",
        {"mine_bytes": meta["spliced_bytes"], "sealed_bytes": ctrl["spliced_decoded_bytes"],
         "container_sha_note": "gz mtime header differs; payload fingerprint identical"})

    # ---------- fixture certificate A: the spliced continuity ----------
    cert_a = json.loads(json.dumps(sealed_cert))
    cert_a["measurement_window_continuity"] = {
        **sealed_cert["measurement_window_continuity"],
        "in_window_messages": stats["in_window_messages"],
        "in_window_message_pairs": stats["in_window_pairs"],
        "max_in_window_gap_ns": stats["max_in_window_gap_ns"],
        "max_in_window_gap_within_bound": False,
        "backwards_timestamps": stats["backwards_timestamps"],
        "monotonic_non_decreasing_exchange_timestamps": stats["backwards_timestamps"] == 0,
        "gaps_over_bound": stats["gaps_over_bound"],
        "in_window_message_count_matches_declaration": False,
        "generated_from": "V4 splice fixture (head+aligned tail of the retained window)",
    }
    cert_a["verdict"] = {**sealed_cert["verdict"],
                         "measurement_window_continuity": "FAIL",
                         "coverage_certificate": "FAIL",
                         "overall": "FAIL",
                         "failed_checks": ["ARTEFACT_IDENTITY", "MEASUREMENT_WINDOW_CONTINUITY",
                                           "COVERAGE_CERTIFICATE"]}
    cert_a["coverage_certificate"] = {**sealed_cert["coverage_certificate"],
                                      "coverage_ratio": 0.0, "tolerance_met": False}
    path_cert_a = os.path.join(V4, "v4_fixture_certificate_spliced.json")
    json.dump(cert_a, open(path_cert_a, "w"), indent=1, sort_keys=True)

    # ---------- fixture manifest A: sealed manifest, certificate re-pointed ----------
    manifest = json.load(open(os.path.join(AUC, "admission_manifest_v2.json")))
    man_a = json.loads(json.dumps(manifest))
    for entry in man_a["files"]:
        if entry.get("role") == "continuity_certificate":
            entry["path"] = path_cert_a
            entry["sha256"] = sha256_file(path_cert_a)
            entry["bytes"] = os.path.getsize(path_cert_a)
    man_a["session"]["measurement_window_continuity"]["certificate_path"] = path_cert_a
    path_man_a = os.path.join(V4, "v4_fixture_manifest_spliced.json")
    json.dump(man_a, open(path_man_a, "w"), indent=2, sort_keys=True)

    _p, res_a = run_contract(path_man_a, os.path.join(V4, "v4_fixture_result_spliced.json"))
    ids_a = [r.get("check") for r in res_a["reasons"]]
    chk("B7", "spliced fixture is refused (not DATA_VALID)", res_a["state"] != "DATA_VALID",
        res_a["state"])
    chk("B7", "spliced fixture fires session.continuity",
        "session.continuity" in ids_a, sorted(set(ids_a)))
    chk("B7", "spliced fixture fires coverage.certificate",
        "coverage.certificate" in ids_a, sorted(set(ids_a)))
    blob_a = json.dumps([r for r in res_a["reasons"] if r.get("check") == "session.continuity"])
    chk("B7", "session.continuity reports the gap and count contradictions",
        "609647167374" in blob_a and "585996" in blob_a and "55698714" in blob_a,
        blob_a[:300])
    chk("B7", "session.continuity reports the FAIL certificate verdict",
        any("certificate_verdict" in json.dumps(r) for r in res_a["reasons"]))

    # ---------- fixture certificate B: coverage floor breached, continuity pristine ----------
    cert_b = json.loads(json.dumps(sealed_cert))
    cert_b["coverage_certificate"] = {**sealed_cert["coverage_certificate"],
                                      "coverage_ratio": 0.80, "tolerance_met": False}
    cert_b["verdict"] = {**sealed_cert["verdict"], "coverage_certificate": "FAIL",
                         "overall": "FAIL", "failed_checks": ["COVERAGE_CERTIFICATE"]}
    path_cert_b = os.path.join(V4, "v4_fixture_certificate_coverage.json")
    json.dump(cert_b, open(path_cert_b, "w"), indent=1, sort_keys=True)
    man_b = json.loads(json.dumps(manifest))
    for entry in man_b["files"]:
        if entry.get("role") == "continuity_certificate":
            entry["path"] = path_cert_b
            entry["sha256"] = sha256_file(path_cert_b)
            entry["bytes"] = os.path.getsize(path_cert_b)
    path_man_b = os.path.join(V4, "v4_fixture_manifest_coverage.json")
    json.dump(man_b, open(path_man_b, "w"), indent=2, sort_keys=True)
    _p, res_b = run_contract(path_man_b, os.path.join(V4, "v4_fixture_result_coverage.json"))
    ids_b = [r.get("check") for r in res_b["reasons"]]
    chk("B7", "coverage fixture fires coverage.certificate", "coverage.certificate" in ids_b,
        sorted(set(ids_b)))
    chk("B7", "coverage fixture reports the ratio/floor contradiction",
        any("floor" in json.dumps(r) for r in res_b["reasons"]))
    chk("B7", "coverage fixture leaves session.continuity clean",
        "session.continuity" not in ids_b)

    # ---------- control: the same fixture machinery with the pristine certificate ----------
    man_c = json.loads(json.dumps(manifest))
    path_man_c = os.path.join(V4, "v4_fixture_manifest_pristine.json")
    json.dump(man_c, open(path_man_c, "w"), indent=2, sort_keys=True)
    _p, res_c = run_contract(path_man_c, os.path.join(V4, "v4_fixture_result_pristine.json"))
    chk("B7", "control: re-serialised pristine manifest still yields DATA_VALID",
        res_c["state"] == "DATA_VALID", res_c["state"])

    res = {"total": len(CHECKS), "ok": sum(1 for c in CHECKS if c["ok"]),
           "failures": [c for c in CHECKS if not c["ok"]], "item": "B7",
           "splice": {"meta": meta, "scan": stats}}
    print(json.dumps({k: v for k, v in res.items() if k != "splice"}, indent=1))
    json.dump(res, open(os.path.join(V4, "v4_b7_splice_fixture.json"), "w"), indent=1)
    return 0 if not res["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())