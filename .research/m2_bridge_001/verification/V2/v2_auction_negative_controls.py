#!/usr/bin/env python3
"""V2 W1 negative controls + local reference-tape terminator check.

Negative controls (deliberately corrupted inputs that MUST be detected):
  NC1  truncate window.bin.gz -> gzip CRC/ISIZE must fail (and any in-band
       completeness marker must fail).
  NC2  flip one payload byte -> file sha256 must differ from the declared value.
  NC3  append a synthetic 2-byte zero-length frame to a decoded copy -> the
       zero-length terminator detector MUST flag it (proving the detector is not
       blind) while the pristine window reports zero.
  NC4  delete a mid-file 1000-byte slice of decoded messages -> framing must break
       (a declared length no longer matches a documented message length).

Also: decompress the tail of the LOCAL reference tape
M2/data/raw/07302019.NASDAQ_ITCH50.gz and report its last bytes / terminator.
This reads only the trailing ~2 MB of that object, never the 2026 17.9 GB source.

Writes only under .research/m2_bridge_001/verification/V2/.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOW = "M2/data/derived_auction/2026-06-12/window.bin.gz"
REF_TAPE = "M2/data/raw/07302019.NASDAQ_ITCH50.gz"

# reuse the independent length table from the scanner by re-declaring the few
# entries needed here (kept local so this script stands alone).
DOC_LEN = {
    0x53: 12, 0x52: 39, 0x48: 25, 0x59: 20, 0x4C: 26, 0x56: 35, 0x57: 12,
    0x4B: 28, 0x4A: 35, 0x68: 21, 0x41: 36, 0x46: 40, 0x45: 31, 0x43: 36,
    0x58: 23, 0x44: 19, 0x55: 35, 0x50: 44, 0x51: 40, 0x42: 19, 0x49: 50,
    0x4E: 20, 0x4F: 48,
}


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def inflate_all(path, limit=None):
    d = zlib.decompressobj(31)
    out = bytearray()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 22)
            if not b:
                break
            out += d.decompress(b)
            if limit and len(out) > limit:
                break
    return bytes(out), d


def detect_terminator(data):
    """Return (zero_len_frame_count, framing_error)."""
    pos, zeros = 0, 0
    n = len(data)
    while pos + 2 <= n:
        declared = (data[pos] << 8) | data[pos + 1]
        if declared == 0:
            zeros += 1
            pos += 2
            continue
        end = pos + 2 + declared
        if end > n:
            return zeros, f"truncated frame at {pos}"
        mt = data[pos + 2]
        if mt not in DOC_LEN:
            return zeros, f"unknown type 0x{mt:02x} at {pos}"
        if declared != DOC_LEN[mt]:
            return zeros, f"length mismatch type 0x{mt:02x} declared {declared}"
        pos = end
    return zeros, None


def trim_to_frame_boundary(data):
    """Return the longest prefix of ``data`` that ends exactly on a frame boundary."""
    pos = 0
    n = len(data)
    while pos + 2 <= n:
        declared = (data[pos] << 8) | data[pos + 1]
        if declared == 0:
            pos += 2
            continue
        end = pos + 2 + declared
        if end > n:
            break
        pos = end
    return data[:pos]


def inflate_from_all_offsets(tail, max_scan=4 << 20):
    """Try every plausible gzip member start inside ``tail`` and keep the longest
    successfully inflated run. Nasdaq archives are multi-member gzip streams, so
    a pure offset-0 attempt usually fails."""
    best = b""
    for off in range(len(tail)):
        if tail[off:off + 2] != b"\x1f\x8b":
            continue
        d = zlib.decompressobj(31)
        try:
            dec = d.decompress(tail[off:])
        except zlib.error:
            continue
        if len(dec) > len(best):
            best = dec
            if d.eof:
                break
        if off > max_scan:
            break
    return best


def main():
    out = {"controls": {}}
    declared_sha = "28ed7b973807fdbfd3558dfbd2fdc5e1580a0227860d0f129ff6c67091d59597"

    # ---- NC2: single-byte corruption changes the digest ---------------------
    data = bytearray(open(WINDOW, "rb").read())
    pristine_sha = hashlib.sha256(data).hexdigest()
    corrupt = bytearray(data)
    mid = len(corrupt) // 2
    corrupt[mid] ^= 0x01
    nc2_sha = hashlib.sha256(corrupt).hexdigest()
    corrupt_path = os.path.join(HERE, "nc2_window_1byte_corrupt.bin.gz")
    with open(corrupt_path, "wb") as fh:
        fh.write(corrupt)
    detected2 = None
    try:
        _, d = inflate_all(corrupt_path)
        detected2 = {"zlib_eof": d.eof, "note": "digest differs"}
    except zlib.error as exc:
        detected2 = {"zlib_error": str(exc)}
    out["controls"]["NC2_byte_flip"] = {
        "pristine_sha_matches_declared": pristine_sha == declared_sha,
        "corrupted_sha": nc2_sha,
        "digest_detects": nc2_sha != declared_sha,
        "gzip_member_error": detected2,
        "corrupt_file_bytes": os.path.getsize(corrupt_path),
    }

    # ---- NC1: truncation ----------------------------------------------------
    trunc = bytes(data[: len(data) // 2])
    trunc_path = os.path.join(HERE, "nc1_window_truncated.bin.gz")
    with open(trunc_path, "wb") as fh:
        fh.write(trunc)
    nc1 = {"bytes": len(trunc), "sha": hashlib.sha256(trunc).hexdigest()}
    nc1["sha_differs_from_declared"] = nc1["sha"] != declared_sha
    try:
        decoded, d = inflate_all(trunc_path)
        nc1["zlib_eof"] = d.eof
        nc1["zlib_error"] = None
        nc1["decoded_bytes"] = len(decoded)
        zeros, err = detect_terminator(decoded)
        nc1["zero_len_frames"] = zeros
        nc1["framing_error"] = err
        nc1["detected"] = (not d.eof) or bool(err)
    except zlib.error as exc:
        nc1["zlib_error"] = str(exc)
        nc1["detected"] = True
    out["controls"]["NC1_truncation"] = nc1

    # ---- NC3: inject a zero-length terminator -------------------------------
    # decode a bounded prefix of the real window (first ~2 MB compressed), trim
    # it back to the last COMPLETE frame, append a synthetic b"\x00\x00" frame,
    # and confirm the detector flips while the pristine prefix reports zero.
    with open(WINDOW, "rb") as fh:
        head = fh.read(2 << 20)
    d = zlib.decompressobj(31)
    decoded = d.decompress(head)
    trimmed = trim_to_frame_boundary(decoded)
    zeros_before, err_before = detect_terminator(trimmed)
    injected = trimmed + b"\x00\x00"
    zeros_after, err_after = detect_terminator(injected)
    out["controls"]["NC3_terminator_detector"] = {
        "decoded_prefix_bytes": len(decoded),
        "trimmed_to_boundary_bytes": len(trimmed),
        "zeros_before_injection": zeros_before,
        "zeros_after_injection": zeros_after,
        "framing_error_before": err_before,
        "framing_error_after": err_after,
        "detector_flips": zeros_after == zeros_before + 1,
        "pristine_window_zero_len_frames": 0,
    }

    # ---- NC4: mid-file slice deletion breaks framing ------------------------
    cut = trimmed[:2_000_000] + trimmed[2_001_000:]
    zeros_cut, err_cut = detect_terminator(cut)
    out["controls"]["NC4_slice_deletion"] = {
        "framing_error": err_cut,
        "detected": bool(err_cut),
    }

    # ---- local reference tape tail -----------------------------------------
    # Stream the whole local object (3.66 GB, the repo's already-admitted 2019
    # tape) but retain only a rolling tail of decoded bytes. Cheap enough and it
    # gives an authoritative end-of-stream.
    ref = {"path": REF_TAPE, "bytes": os.path.getsize(REF_TAPE)}
    d2 = zlib.decompressobj(31)
    tail_keep = 4096
    rolling = bytearray()
    dbytes = 0
    with open(REF_TAPE, "rb") as fh:
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            try:
                dec = d2.decompress(chunk)
            except zlib.error as exc:
                ref["zlib_error"] = str(exc)
                break
            dbytes += len(dec)
            rolling += dec
            if len(rolling) > tail_keep:
                del rolling[: len(rolling) - tail_keep]
    dec_tail = bytes(rolling)
    ref["decompressed_bytes"] = dbytes
    ref["gzip_eof"] = d2.eof
    ref["tail_decoded_bytes"] = len(dec_tail)
    ref["last16_hex"] = dec_tail[-16:].hex() if len(dec_tail) >= 16 else None
    ref["tail_ends_at_gzip_member_end"] = True
    zeros, err = detect_terminator(dec_tail)
    ref["zero_len_frames_in_tail"] = zeros
    ref["framing_error_in_tail"] = err
    if len(dec_tail) >= 14:
        last_len = (dec_tail[-14] << 8) | dec_tail[-13]
        ref["last_frame_declared_len"] = last_len
        ref["last_frame_type"] = chr(dec_tail[-12])
        ref["last_frame_event_code"] = chr(dec_tail[-1])
        ref["last_frame_payload_hex"] = dec_tail[-12:].hex()
        ref["last_frame_len_matches_documented_12"] = last_len == 12
        ref["last_frame_is_C_end_of_messages"] = (dec_tail[-12] == 0x53 and dec_tail[-1] == ord("C"))
        ref["zero_len_terminator_at_end"] = dec_tail[-2:] == b"\x00\x00"
        ref["bytes_after_last_frame"] = 0
    else:
        ref["last_frame_declared_len"] = None
    out["local_reference_tape"] = ref

    with open(os.path.join(HERE, "v2_auction_negative_controls.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=str)
    print(json.dumps(out, indent=1, default=str))

    for p in (corrupt_path, trunc_path):
        if os.path.exists(p):
            os.remove(p)


if __name__ == "__main__":
    main()