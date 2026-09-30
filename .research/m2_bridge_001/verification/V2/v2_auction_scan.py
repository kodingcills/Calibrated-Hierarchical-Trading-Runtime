#!/usr/bin/env python3
"""V2 adversarial independent parse of the retained W1 auction window.

Does NOT import or execute M2/src/itch_stream_window.py or M2/src/ingest.py.
Framing, message lengths and field offsets are transcribed independently from the
in-repo Nasdaq TotalView-ITCH 5.0 specification PDF (M2/data/reference/
NQTVITCHspecification.pdf), extracted to spec_text.txt in this directory.

Re-derives, on window.bin.gz only:
  * the compressed byte size and sha256 (claim 1),
  * message-type histogram, total frame count, I/Q/R totals (claim 2),
  * the frozen instants and the four-cell coverage matrix (claims 2, 3),
  * the Issue Classification=C / Sub-Type=C count (claim 4),
  * the zero-share / zero-price cross-print population and its concentration by
    market category (claim 5),
  * the session-date provenance question (claim 7).

Writes only under .research/m2_bridge_001/verification/V2/.
"""

from __future__ import annotations

import collections
import gzip
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOW = "M2/data/derived_auction/2026-06-12/window.bin.gz"

# --- independently transcribed from the ITCH 5.0 spec PDF --------------------
# Message names -> payload length (excluding the 2-byte length prefix).
LENGTHS = {
    0x53: ("S", "system_event", 12),
    0x52: ("R", "stock_directory", 39),
    0x48: ("H", "stock_trading_action", 25),
    0x59: ("Y", "reg_sho", 20),
    0x4C: ("L", "market_participant_position", 26),
    0x56: ("V", "mwcb_decline_level", 35),
    0x57: ("W", "mwcb_status", 12),
    0x4B: ("K", "ipo_quoting_period", 28),
    0x4A: ("J", "luld_auction_collar", 35),
    0x68: ("h", "operational_halt", 21),
    0x41: ("A", "add_order", 36),
    0x46: ("F", "add_order_mpid", 40),
    0x45: ("E", "order_executed", 31),
    0x43: ("C", "order_executed_with_price", 36),
    0x58: ("X", "order_cancel", 23),
    0x44: ("D", "order_delete", 19),
    0x55: ("U", "order_replace", 35),
    0x50: ("P", "trade_non_cross", 44),
    0x51: ("Q", "cross_trade", 40),
    0x42: ("B", "broken_trade", 19),
    0x49: ("I", "noii", 50),
    0x4E: ("N", "retail_price_improvement", 20),
    0x4F: ("O", "dlcr_price_discovery", 48),
}

NS_PER_HOUR = 3_600_000_000_000
NS_PER_MIN = 60_000_000_000
NS_1550 = 15 * NS_PER_HOUR + 50 * NS_PER_MIN
NS_1555 = 15 * NS_PER_HOUR + 55 * NS_PER_MIN
WINDOW_START = 15 * NS_PER_HOUR + 49 * NS_PER_MIN + 50 * 1_000_000_000
WINDOW_END = 16 * NS_PER_HOUR + 10 * 1_000_000_000

R_STOCK, R_MARKET_CAT, R_CLASSIF, R_SUBTYPE, R_AUTH, R_ETP = 11, 19, 26, 27, 29, 33
I_PAIRED, I_IMB, I_DIR, I_STOCK, I_ALLOC, I_CRT, I_REFPX, I_CROSSTYPE, I_PVAR = (
    11, 19, 27, 28, 36, 40, 44, 48, 49,
)
Q_SHARES, Q_STOCK, Q_XPRICE, Q_MATCH, Q_CROSSTYPE = 11, 19, 27, 31, 39

UNIV_CATS = frozenset("Q G S N A P Z V".split())
CHUNK = 1 << 22


def alpha(raw):
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace").strip()


def ns_str(ns):
    if ns is None:
        return None
    h, rem = divmod(ns, NS_PER_HOUR)
    m, rem = divmod(rem, NS_PER_MIN)
    s, nsec = divmod(rem, 1_000_000_000)
    return f"{h:02d}:{m:02d}:{s:02d}.{nsec:09d}"


class Sym:
    __slots__ = ("locate", "symbol", "cat", "cls", "sub", "auth", "etp",
                 "read1550", "read1550_after", "read1555", "read1555_after",
                 "cross", "cross_count", "cross_all")

    def __init__(self, locate):
        self.locate = locate
        self.symbol = self.cat = self.cls = self.sub = self.auth = self.etp = None
        self.read1550 = self.read1550_after = self.read1555 = self.read1555_after = None
        self.cross = None
        self.cross_count = 0
        self.cross_all = 0


def main():
    out = {}
    h = hashlib.sha256()
    nbytes = 0
    with open(WINDOW, "rb") as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            nbytes += len(b)
            h.update(b)
    out["window_bytes"] = nbytes
    out["window_sha256"] = h.hexdigest()
    out["declared"] = {
        "bytes": 760167921,
        "sha256": "28ed7b973807fdbfd3558dfbd2fdc5e1580a0227860d0f129ff6c67091d59597",
    }
    out["bytes_match"] = nbytes == out["declared"]["bytes"]
    out["sha256_match"] = out["window_sha256"] == out["declared"]["sha256"]

    hist = collections.Counter()
    frames = 0
    zero_len_frames = 0
    trailing = 0
    framing_errors = []
    first_ts = last_ts = None
    first_file_frames = []
    backwards = 0
    system_events = []
    in_window_messages = 0
    window_hist = collections.Counter()
    window_first_ts = window_last_ts = None

    symbols = {}
    n_noii = 0
    noii_cross_types = collections.Counter()
    n_noii_first_ts = None
    n_noii_last_ts = None
    n_noii_at_or_before_1550 = 0
    n_noii_at_or_before_1555 = 0
    n_directory = 0
    dir_ts_min = dir_ts_max = None
    aapl_locate = None
    first_frames = []
    cls_counts = collections.Counter()
    sub_counts = collections.Counter()
    cat_counts = collections.Counter()
    auth_counts = collections.Counter()
    etp_counts = collections.Counter()
    pair_counts = collections.Counter()
    crosses_by_type = collections.Counter()
    zero_share = zero_share_zero_px = 0
    delegate = None
    try:
        import zlib
        delegate = zlib.decompressobj(31)
    except Exception:
        pass

    buf = bytearray()
    pos = 0
    decompressed_total = 0
    with open(WINDOW, "rb") as raw:
        dec = zlib.decompressobj(31)
        while True:
            chunk = raw.read(CHUNK)
            if not chunk:
                break
            data = dec.decompress(chunk)
            buf += data
            limit = len(buf)
            while pos + 2 <= limit:
                declared = (buf[pos] << 8) | buf[pos + 1]
                if declared == 0:
                    zero_len_frames += 1
                    pos += 2
                    continue
                end = pos + 2 + declared
                if end > limit:
                    break
                base = pos + 2
                mt = buf[base]
                info = LENGTHS.get(mt)
                if info is None:
                    framing_errors.append(f"unknown type 0x{mt:02x} at {pos}")
                    pos = end
                    continue
                if declared != info[2]:
                    framing_errors.append(
                        f"type {info[0]} declares {declared} documented {info[2]} at {pos}")
                frames += 1
                hist[info[1]] += 1
                if frames <= 4:
                    first_file_frames.append({"type": info[0], "name": info[1], "len": declared})
                hi, lo = struct.unpack_from(">IH", buf, base + 5)
                ts = (hi << 16) | lo
                if first_ts is None:
                    first_ts = ts
                if last_ts is not None and ts < last_ts:
                    backwards += 1
                last_ts = ts
                if WINDOW_START <= ts <= WINDOW_END:
                    in_window_messages += 1
                    window_hist[info[1]] += 1
                    if window_first_ts is None:
                        window_first_ts = ts
                    window_last_ts = ts

                if mt == 0x53:
                    system_events.append({"ts": ts, "ts_str": ns_str(ts),
                                          "code": chr(buf[base + 11])})
                elif mt == 0x52:
                    n_directory += 1
                    loc = (buf[base + 1] << 8) | buf[base + 2]
                    s = symbols.get(loc) or Sym(loc)
                    symbols[loc] = s
                    s.symbol = alpha(bytes(buf[base + R_STOCK:base + R_STOCK + 8]))
                    s.cat = chr(buf[base + R_MARKET_CAT])
                    s.cls = chr(buf[base + R_CLASSIF])
                    s.sub = alpha(bytes(buf[base + R_SUBTYPE:base + R_SUBTYPE + 2]))
                    s.auth = chr(buf[base + R_AUTH])
                    s.etp = chr(buf[base + R_ETP])
                    cls_counts[s.cls] += 1
                    sub_counts[s.sub] += 1
                    cat_counts[s.cat] += 1
                    auth_counts[s.auth] += 1
                    etp_counts[s.etp] += 1
                    pair_counts[f"{s.cls}/{s.sub}"] += 1
                    if dir_ts_min is None or ts < dir_ts_min:
                        dir_ts_min = ts
                    if dir_ts_max is None or ts > dir_ts_max:
                        dir_ts_max = ts
                    if s.symbol == "AAPL":
                        aapl_locate = loc
                    if len(first_frames) < 4:
                        first_frames.append({"type": "R", "ts": ns_str(ts), "symbol": s.symbol,
                                             "locate": loc})
                elif mt == 0x49:
                    n_noii += 1
                    ct = chr(buf[base + I_CROSSTYPE])
                    noii_cross_types[ct] += 1
                    if ct == "C":
                        loc = (buf[base + 1] << 8) | buf[base + 2]
                        s = symbols.get(loc) or Sym(loc)
                        symbols[loc] = s
                        rec = {"ts": ts, "dir": chr(buf[base + I_DIR]),
                               "imb": struct.unpack_from(">Q", buf, base + I_IMB)[0],
                               "refpx": struct.unpack_from(">I", buf, base + I_REFPX)[0]}
                        if ts <= NS_1550:
                            s.read1550 = rec
                            n_noii_at_or_before_1550 += 1
                        elif s.read1550_after is None:
                            s.read1550_after = rec
                        if ts <= NS_1555:
                            s.read1555 = rec
                            n_noii_at_or_before_1555 += 1
                        elif s.read1555_after is None:
                            s.read1555_after = rec
                        if n_noii_first_ts is None:
                            n_noii_first_ts = ts
                        n_noii_last_ts = ts
                elif mt == 0x51:
                    loc = (buf[base + 1] << 8) | buf[base + 2]
                    ct = chr(buf[base + Q_CROSSTYPE])
                    crosses_by_type[ct] += 1
                    s = symbols.get(loc) or Sym(loc)
                    symbols[loc] = s
                    s.cross_all += 1
                    shares = struct.unpack_from(">Q", buf, base + Q_SHARES)[0]
                    px = struct.unpack_from(">I", buf, base + Q_XPRICE)[0]
                    if ct == "C":
                        s.cross_count += 1
                        s.cross = {"ts": ts, "shares": shares, "px": px,
                                   "symbol": alpha(bytes(buf[base + Q_STOCK:base + Q_STOCK + 8]))}
                        if shares == 0:
                            zero_share += 1
                            if px == 0:
                                zero_share_zero_px += 1
                pos = end
            del buf[:pos]
            pos = 0
    trailing = len(buf)
    decompressed_total = dec.total_out if hasattr(dec, "total_out") else None
    out["gzip_eof"] = dec.eof
    out["zero_len_frames"] = zero_len_frames
    out["trailing_bytes"] = trailing
    out["framing_errors"] = framing_errors[:20]
    out["framing_error_count"] = len(framing_errors)
    out["frames_total"] = frames
    out["in_window_frames"] = in_window_messages
    out["first_file_frames"] = first_file_frames
    out["histogram_window"] = dict(sorted(hist.items()))
    out["histogram_in_window"] = dict(sorted(window_hist.items()))
    out["first_ts"] = ns_str(first_ts)
    out["last_ts"] = ns_str(last_ts)
    out["backwards_timestamps"] = backwards
    out["system_events"] = system_events
    out["last_message_is_C"] = bool(system_events and system_events[-1]["code"] == "C")
    out["directory_messages"] = n_directory
    out["directory_locates"] = len(symbols)
    out["noii_count"] = n_noii
    out["noii_cross_type_counts"] = dict(noii_cross_types)
    out["cross_trade_by_type"] = dict(crosses_by_type)
    out["noii_first_ts"] = ns_str(n_noii_first_ts)
    out["noii_last_ts"] = ns_str(n_noii_last_ts)
    out["noii_at_or_before_1550"] = n_noii_at_or_before_1550
    out["noii_at_or_before_1555"] = n_noii_at_or_before_1555
    out["directory_classification"] = dict(cls_counts)
    out["directory_subtype"] = dict(sub_counts)
    out["directory_market_category"] = dict(cat_counts)
    out["directory_authenticity"] = dict(auth_counts)
    out["directory_etp_flag"] = dict(etp_counts)
    out["classification_subtype_pairs"] = dict(pair_counts)
    out["classification_C_subtype_C"] = pair_counts.get("C/C")
    out["classification_C_subtype_Z"] = pair_counts.get("C/Z")
    out["cross_zero_share"] = zero_share
    out["cross_zero_share_zero_price"] = zero_share_zero_px
    out["locates_with_C_cross"] = sum(1 for s in symbols.values() if s.cross is not None)
    out["locates_with_any_cross"] = sum(1 for s in symbols.values() if s.cross_all)

    # --- coverage matrix ------------------------------------------------------
    def frozen_ok(s):
        return (s.auth == "P" and s.etp == "N" and s.cls == "C"
                and s.sub == "C" and s.cat in UNIV_CATS)

    def classonly_ok(s):
        return (s.auth == "P" and s.etp == "N" and s.cls == "C" and s.cat in UNIV_CATS)

    def valid_cross(s):
        return s.cross is not None and s.cross["shares"] > 0 and s.cross["px"] > 0

    def pick(s, instant, sem):
        before = s.read1550 if instant == "1550" else s.read1555
        after = s.read1550_after if instant == "1550" else s.read1555_after
        if sem == "AT_OR_BEFORE":
            return before
        if sem == "FROZEN_CONTRACT":
            return (before if before is not None else after) if instant == "1550" else before
        return after if after is not None else before

    def variant(univ, sem):
        qual = den = num = 0
        reasons = collections.Counter()
        for s in symbols.values():
            qualified = frozen_ok(s) if univ == "FROZEN_5_CLAUSE" else classonly_ok(s)
            if qualified:
                qual += 1
            r50, r55 = pick(s, "1550", sem), pick(s, "1555", sem)
            indent = qualified and valid_cross(s)
            innum = indent and r50 is not None and r55 is not None
            if not qualified:
                reasons["directory_ineligible"] += 1
            elif s.cross is None:
                reasons["no_cross"] += 1
            elif not valid_cross(s):
                reasons["zero_share_cross"] += 1
            elif r50 is None or r55 is None:
                reasons["no_read"] += 1
            elif r50["dir"] not in ("B", "S") or r55["dir"] not in ("B", "S"):
                reasons["ineligible_direction"] += 1
            if indent:
                den += 1
            if innum:
                num += 1
        return {"universe": univ, "read_semantics": sem, "qualified": qual,
                "denominator": den, "numerator": num,
                "ratio": (num / den) if den else None,
                "reasons": dict(reasons)}

    matrix = [variant(u, s) for u in ("FROZEN_5_CLAUSE", "CLASSIFICATION_ONLY")
              for s in ("AT_OR_BEFORE", "FROZEN_CONTRACT", "INSTANT_ALIGNED")]
    out["coverage_matrix"] = matrix

    # --- zero-print concentration by market category --------------------------
    conc = {}
    for label, pred in (("frozen_C_C", lambda s: frozen_ok(s)),
                        ("classification_only", lambda s: classonly_ok(s))):
        bucket = collections.defaultdict(lambda: {"with_valid_cross": 0, "zero_share_cross": 0,
                                                  "no_cross": 0})
        for s in symbols.values():
            if not pred(s):
                continue
            if s.cross is None:
                bucket[s.cat]["no_cross"] += 1
            elif s.cross["shares"] == 0:
                bucket[s.cat]["zero_share_cross"] += 1
            else:
                bucket[s.cat]["with_valid_cross"] += 1
        conc[label] = {k: dict(v) for k, v in sorted(bucket.items())}
    out["zero_print_concentration"] = conc

    # --- per-classification x sub-type zero-share table -----------------------
    tbl = collections.Counter()
    for s in symbols.values():
        if s.cross is not None:
            tbl[(s.cls, s.sub, "zero" if s.cross["shares"] == 0 else "nonzero")] += 1
    out["cross_validity_by_class_subtype"] = {
        f"{a}/{b}/{c}": v for (a, b, c), v in sorted(tbl.items())}

    # --- claim 2: frozen instants really present ------------------------------
    all_reads_1550 = [s.read1550 for s in symbols.values() if s.read1550]
    all_reads_1555 = [s.read1555 for s in symbols.values() if s.read1555]
    out["reads_1550_count"] = len(all_reads_1550)
    out["reads_1555_count"] = len(all_reads_1555)
    after50 = [s.read1550_after["ts"] for s in symbols.values() if s.read1550_after]
    after55 = [s.read1555_after["ts"] for s in symbols.values() if s.read1555_after]
    out["reads_after_1550_count"] = len(after50)
    out["reads_after_1555_count"] = len(after55)
    out["first_read_after_1550_ts"] = ns_str(min(after50)) if after50 else None
    out["first_read_after_1555_ts"] = ns_str(min(after55)) if after55 else None
    out["directory_ts_range"] = [ns_str(dir_ts_min), ns_str(dir_ts_max)]
    aapl = symbols.get(aapl_locate) if aapl_locate else None
    out["aapl_directory_record"] = (
        {"symbol": aapl.symbol, "market_category": aapl.cat, "issue_classification": aapl.cls,
         "issue_sub_type": aapl.sub, "authenticity": aapl.auth, "etp_flag": aapl.etp}
        if aapl else None
    )
    out["reads_1550_ts_range"] = (
        [ns_str(min(r["ts"] for r in all_reads_1550)), ns_str(max(r["ts"] for r in all_reads_1550))]
        if all_reads_1550 else None
    )
    out["reads_1555_ts_range"] = (
        [ns_str(min(r["ts"] for r in all_reads_1555)), ns_str(max(r["ts"] for r in all_reads_1555))]
        if all_reads_1555 else None
    )
    afters = [s.read1550_after["ts"] for s in symbols.values() if s.read1550_after]
    out["first_1550_after_ts"] = ns_str(min(afters)) if afters else None
    out["cross_ts_range"] = [ns_str(min(s.cross["ts"] for s in symbols.values() if s.cross)),
                             ns_str(max(s.cross["ts"] for s in symbols.values() if s.cross))]
    out["cross_symbols_match_directory"] = sum(
        1 for s in symbols.values()
        if s.cross and s.symbol and s.cross["symbol"] == s.symbol)

    # --- claim 7: session date provenance ------------------------------------
    # ITCH has no date field. The only in-band date-adjacent evidence is the
    # directory/NOII content and the clock domain (ns since midnight).
    out["session_date_evidence"] = {
        "in_band_date_field": False,
        "note": ("ITCH 5.0 messages carry nanoseconds-since-midnight only; no trade date is "
                 "encoded anywhere in the payload. The date is inferred from the object name "
                 "S061226-v50.txt.gz and the provider directory index, not proven by tape content."),
        "ns_domain_check": {"first_ts_lt_24h": first_ts < 86_400_000_000_000,
                            "last_ts_lt_24h": last_ts < 86_400_000_000_000},
    }

    with open(os.path.join(HERE, "v2_auction_scan.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=str)
    slim = {k: v for k, v in out.items() if k not in ("histogram_window", "system_events",
                                                      "cross_validity_by_class_subtype",
                                                      "zero_print_concentration")}
    print(json.dumps(slim, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()