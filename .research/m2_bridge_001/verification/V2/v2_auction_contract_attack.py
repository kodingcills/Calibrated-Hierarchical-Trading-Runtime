#!/usr/bin/env python3
"""V2 attack on the W1 completeness contract (assignment item 6).

Question: is "gzip CRC/ISIZE PASS + received==Content-Range + 0 framing errors +
0 trailing bytes + terminal 'C' End-of-Messages" a defensible completeness
contract, or a convenience relaxation? What failure mode does it NOT catch?

Method: build a deliberately spliced tape from the REAL retained window
(first 8 MiB of decoded frames + last 8 MiB of decoded frames, cut on frame
boundaries and keeping the terminal 'C'), re-gzip it, and run the contract's
markers against it. If every marker passes while a large block of the session is
missing, the contract is a structural/transport contract, not a completeness
contract.

Reads only window.bin.gz; writes only under .../V2/.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOW = "M2/data/derived_auction/2026-06-12/window.bin.gz"

DOC_LEN = {
    0x53: 12, 0x52: 39, 0x48: 25, 0x59: 20, 0x4C: 26, 0x56: 35, 0x57: 12,
    0x4B: 28, 0x4A: 35, 0x68: 21, 0x41: 36, 0x46: 40, 0x45: 31, 0x43: 36,
    0x58: 23, 0x44: 19, 0x55: 35, 0x50: 44, 0x51: 40, 0x42: 19, 0x49: 50,
    0x4E: 20, 0x4F: 48,
}
KEEP = 8 << 20


def marker_report(data):
    """Run the contract's structural markers over decoded frame bytes."""
    rep = {"frames": 0, "framing_error": None, "trailing_bytes": 0,
           "zero_len_frames": 0, "last_frame_type": None, "last_event_code": None,
           "max_ts_gap_ns": 0, "ts_gap_at_frame": None}
    pos, n = 0, len(data)
    prev_ts = None
    while pos + 2 <= n:
        declared = (data[pos] << 8) | data[pos + 1]
        if declared == 0:
            rep["zero_len_frames"] += 1
            pos += 2
            continue
        end = pos + 2 + declared
        if end > n:
            rep["framing_error"] = f"truncated frame at {pos}"
            rep["trailing_bytes"] = n - pos
            break
        mt = data[pos + 2]
        if mt not in DOC_LEN or declared != DOC_LEN[mt]:
            rep["framing_error"] = f"type 0x{mt:02x} declared {declared} at {pos}"
            break
        rep["frames"] += 1
        ts = int.from_bytes(data[pos + 7:pos + 13], "big")
        if prev_ts is not None and ts - prev_ts > rep["max_ts_gap_ns"]:
            rep["max_ts_gap_ns"] = ts - prev_ts
            rep["ts_gap_at_frame"] = rep["frames"]
        prev_ts = ts
        rep["last_frame_type"] = chr(mt)
        if mt == 0x53:
            rep["last_event_code"] = chr(data[pos + 13])
        pos = end
    rep["terminal_C_is_last_frame"] = (rep["last_frame_type"] == "S"
                                       and rep["last_event_code"] == "C")
    return rep


def main():
    out = {}
    d = zlib.decompressobj(31)
    head = bytearray()
    tail = bytearray()
    total = 0
    with open(WINDOW, "rb") as fh:
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            dec = d.decompress(chunk)
            total += len(dec)
            if len(head) < KEEP:
                head += dec[: KEEP - len(head)]
            tail += dec
            if len(tail) > KEEP:
                del tail[: len(tail) - KEEP]
    out["pristine_decoded_bytes"] = total
    out["pristine_gzip_eof"] = d.eof

    def trim(data):
        pos, n = 0, len(data)
        while pos + 2 <= n:
            declared = (data[pos] << 8) | data[pos + 1]
            if declared == 0:
                pos += 2
                continue
            end = pos + 2 + declared
            if end > n:
                break
            pos = end
        return bytes(data[:pos])

    def trim_tail_aligned(data, window=64):
        """Find an offset such that data[off:] parses cleanly to the very end."""
        n = len(data)
        for off in range(min(window, n)):
            pos = off
            ok = True
            while pos + 2 <= n:
                declared = (data[pos] << 8) | data[pos + 1]
                if declared == 0:
                    pos += 2
                    continue
                end = pos + 2 + declared
                if end > n:
                    ok = False
                    break
                mt = data[pos + 2]
                if mt not in DOC_LEN or declared != DOC_LEN[mt]:
                    ok = False
                    break
                pos = end
            if ok and pos == n and n - off >= 14 and data[n - 12] == 0x53 and data[n - 1] == ord("C"):
                return bytes(data[off:])
        return None

    head_t = trim(head)
    tail_t = trim_tail_aligned(bytes(tail))
    if tail_t is None:
        raise SystemExit("could not align the decoded tail to a frame boundary")
    spliced = head_t + tail_t
    spliced_path = os.path.join(HERE, "nc8_spliced_window.bin.gz")
    with open(spliced_path, "wb") as fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fh, compresslevel=6) as gz:
            gz.write(spliced)
    out["spliced_percent_of_pristine"] = 100.0 * len(spliced) / total
    out["spliced_bytes"] = len(spliced)

    # --- contract markers on the spliced artefact ---------------------------
    dd = zlib.decompressobj(31)
    dec = b""
    with open(spliced_path, "rb") as fh:
        while True:
            b = fh.read(1 << 22)
            if not b:
                break
            dec += dd.decompress(b)
    # CRC/ISIZE of the spliced gzip member: zlib raises on mismatch; reaching eof
    # with eof=True is the pass condition.
    out["spliced_gzip_eof_crc_isize_pass"] = dd.eof
    rep = marker_report(dec)
    out["spliced_markers"] = rep
    out["spliced_sha256"] = hashlib.sha256(open(spliced_path, "rb").read()).hexdigest()
    out["spliced_contract_verdict"] = (
        "PASS" if (dd.eof and rep["framing_error"] is None and rep["trailing_bytes"] == 0
                   and rep["terminal_C_is_last_frame"]) else "FAIL")

    out["verdict_note"] = (
        "The spliced artefact keeps only ~{:.2%} of the decoded session, yet every marker of the "
        "declared contract (gzip CRC32/ISIZE, 0 framing errors, 0 trailing bytes, terminal 'C' as "
        "the last frame) passes. Only an unrequested heuristic (max inter-frame timestamp jump = "
        "{:.3f} s) reveals the hole. The contract therefore certifies transport/structural "
        "integrity, not session completeness.".format(
            len(spliced) / total, rep["max_ts_gap_ns"] / 1e9))

    with open(os.path.join(HERE, "v2_auction_contract_attack.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=str)
    print(json.dumps(out, indent=1, default=str))
    os.remove(spliced_path)


if __name__ == "__main__":
    main()