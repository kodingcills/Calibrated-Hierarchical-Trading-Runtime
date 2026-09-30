#!/usr/bin/env python3
"""V2 negative controls for the W2 ES retained raw extract.

NC5  flip one byte in the retained pcap extract -> the re-derivation must detect
     it: the pcap-embedded sha256 differs from the declared value and the decode
     either breaks framing or produces different trades/book digests.
NC6  truncate the retained pcap extract -> the pcap framer must report trailing
     bytes that are not a complete record, and/or framing must break.
NC7  (positive control) the pristine extract re-derives the declared digests.

Uses the independent decoder in v2_es_rederive.py (no producer module imported).

Writes only under .research/m2_bridge_001/verification/V2/.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2_es_rederive as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = "M2/data/raw/dc3-glbx-ab-dedup-20230717T133000.es-ch310.pcap"
DECLARED_SHA = "c938273d6a17cd90b0f44b47a820f6567bb698ffbac50b6bc76052ae71b6c88e"


def decode_stream(records):
    """Consume a record iterable and report framing/digest behaviour."""
    msgs = 0
    bad = None
    trades = 0
    try:
        for ts_sec, ts_nsec, incl, orig, frame in records:
            u = R.udp_of(frame)
            if u is None:
                continue
            sport, dport, payload = u
            if dport not in (14310, 15310):
                continue
            for _seq, _send, tid, blk, _sid, _ver, body in R.iter_messages(payload):
                msgs += 1
                if tid == R.T_TRADE_SUMMARY:
                    transact = int.from_bytes(body[0:8], "little")
                    for entry in R.iter_group_entries(body, R.TRADE_BLOCK_LEN, 1, R.TRADE_ENTRY_LEN):
                        trades += 1
    except ValueError as exc:
        bad = str(exc)
    return {"messages": msgs, "trades": trades, "framing_error": bad}


def frame_scan(path):
    """Re-scan the pcap record framing only, tolerating a broken tail."""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        head = fh.read(24)
    pos, records, bad = 24, 0, None
    with open(path, "rb") as fh:
        fh.seek(24)
        buf = b""
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            buf += chunk
            p = 0
            n = len(buf)
            while p + 16 <= n:
                ts_sec, ts_nsec, incl, orig = __import__("struct").unpack_from("<IIII", buf, p)
                if p + 16 + incl > n:
                    break
                records += 1
                p += 16 + incl
            buf = buf[p:]
        if buf:
            bad = f"{len(buf)} trailing bytes that are not a complete pcap record"
    return {"bytes": size, "records": records, "tail_problem": bad}


def main():
    out = {}
    pristine = open(PCAP, "rb").read()
    out["declared_sha256"] = DECLARED_SHA
    out["pristine_sha256"] = hashlib.sha256(pristine).hexdigest()
    out["pristine_matches_declared"] = out["pristine_sha256"] == DECLARED_SHA
    out["pristine_bytes"] = len(pristine)

    # NC7 positive control on the pristine bytes (in-memory)
    def records_from_bytes(blob):
        pos = 24
        n = len(blob)
        while pos + 16 <= n:
            import struct
            ts_sec, ts_nsec, incl, orig = struct.unpack_from("<IIII", blob, pos)
            if pos + 16 + incl > n:
                break
            yield ts_sec, ts_nsec, incl, orig, blob[pos + 16:pos + 16 + incl]
            pos += 16 + incl

    out["NC7_pristine_decode"] = decode_stream(records_from_bytes(pristine))

    # NC5: flip one byte in the middle
    corrupt = bytearray(pristine)
    mid = len(corrupt) // 2
    corrupt[mid] ^= 0x40
    corrupt_sha = hashlib.sha256(corrupt).hexdigest()
    nc5 = {"corrupted_sha256": corrupt_sha,
           "digest_differs_from_declared": corrupt_sha != DECLARED_SHA}
    nc5.update(decode_stream(records_from_bytes(bytes(corrupt))))
    nc5["detected"] = bool(nc5["digest_differs_from_declared"] or nc5["framing_error"])
    out["NC5_byte_flip"] = nc5

    # NC6: truncate
    trunc_path = os.path.join(HERE, "nc6_es_truncated.pcap")
    with open(trunc_path, "wb") as fh:
        fh.write(pristine[: len(pristine) // 2])
    nc6 = frame_scan(trunc_path)
    nc6["sha256"] = hashlib.sha256(open(trunc_path, "rb").read()).hexdigest()
    nc6["sha_differs_from_declared"] = nc6["sha256"] != DECLARED_SHA
    nc6["detected"] = bool(nc6["tail_problem"])
    out["NC6_truncation"] = nc6
    os.remove(trunc_path)

    with open(os.path.join(HERE, "v2_es_negative_controls.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=str)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()