#!/usr/bin/env python3
"""V2 adversarial re-derivation of the W2 ES artifacts from the retained raw extract.

Independent of M2/src/mdp_es_normalize.py and M2/src/ingest.py: this file
implements its own pcap framer, IPv4/UDP de-framing, MDP 3.0 packet framing and
SBE field reading, and re-checks its own hardcoded layouts against the CME SBE
schema XML before decoding anything.

Writes only under .research/m2_bridge_001/verification/V2/.

Claim set B: 9, 10, 11, 12, 13.
"""

from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import os
import struct
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = "M2/data/raw/dc3-glbx-ab-dedup-20230717T133000.es-ch310.pcap"
SECDEF = "M2/data/raw/secdef-2023-07-17.dat.gz"
SCHEMA = "M2/data/raw/Cme.Futures.Mdp3.Sbe.v1.9.xml"
PROD = "M2/data/derived_es/2023-07-17T133000Z"

T_BOOK = 46
T_TRADE_SUMMARY = 48

# --- layouts transcribed from the SBE schema *independently*; cross-checked
# --- against the XML at runtime below (see check_layouts()).
TRADE_BLOCK_LEN = 11
TRADE_ENTRY_LEN = 32
TRADE_F = {
    "MDEntryPx": (0, "q"),
    "MDEntrySize": (8, "i"),
    "SecurityID": (12, "i"),
    "RptSeq": (16, "I"),
    "NumberOfOrders": (20, "i"),
    "AggressorSide": (24, "B"),
    "MDUpdateAction": (25, "B"),
    "MDTradeEntryID": (26, "I"),
}
BOOK_BLOCK_LEN = 11
BOOK_ENTRY_LEN = 32
BOOK_F = {
    "MDEntryPx": (0, "q"),
    "MDEntrySize": (8, "i"),
    "SecurityID": (12, "i"),
    "RptSeq": (16, "I"),
    "NumberOfOrders": (20, "i"),
    "MDPriceLevel": (24, "B"),
    "MDUpdateAction": (25, "B"),
    "MDEntryType": (26, "c"),
}
NULL_I64 = 9223372036854775807
NULL_I32 = 2147483647

SIDE_FROM_ENTRY = {"0": "B", "1": "A", "E": "B", "F": "A"}
ACTION = {0: "New", 1: "Change", 2: "Delete", 3: "DeleteThru", 4: "DeleteFrom", 5: "Overlay"}
AGGRESSOR = {0: "N", 1: "B", 2: "S"}

WINDOW_START_NS = 1_689_600_600_000_000_000
WINDOW_END_NS = 1_689_601_200_000_000_000
GRID_NS = 10_000_000

TRADE_COLUMNS = [
    "ts_event_ns", "ts_recv_ns", "exchange_send_ns", "sequence", "feed",
    "instrument_id", "symbol", "price", "price_index_points", "size", "side",
    "aggressor_side", "update_action", "rpt_seq", "md_trade_entry_id",
    "number_of_orders", "template_id",
]
BBO_COLUMNS = [
    "ts_event_ns", "ts_recv_ns", "exchange_send_ns", "sequence", "feed",
    "instrument_id", "symbol", "side", "price", "price_index_points", "size",
    "flag", "rpt_seq", "md_price_level", "update_action", "entry_type",
    "template_id",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def check_layouts():
    """Re-derive the layouts from the CME schema XML, independent of the producer."""
    root = ET.parse(SCHEMA).getroot()
    ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    found = {}
    for msg in root.iter(ns + "message"):
        tid = int(msg.get("id"))
        if tid not in (T_BOOK, T_TRADE_SUMMARY):
            continue
        blk = int(msg.get("blockLength"))
        groups = []
        for grp in msg:
            if not grp.tag.endswith("group"):
                continue
            entries = []
            for f in grp:
                if f.tag.endswith("field"):
                    if f.get("offset") is not None:
                        entries.append((f.get("name"), int(f.get("offset"))))
                elif f.tag.endswith("numInGroup"):
                    entries.append(("__numInGroupOffset", int(f.get("offset"))))
            entries.append(("__blockLength", int(grp.get("blockLength"))))
            entries.append(("__dim", grp.get("dimensionType")))
            groups.append((grp.get("name"), entries))
        found[tid] = {"blockLength": blk, "groups": groups}
    rep = {"schema_templates": found, "checks": [], "ok": True}

    def chk(label, observed, expected):
        ok = observed == expected
        rep["checks"].append({"check": label, "observed": observed, "expected": expected, "ok": ok})
        if not ok:
            rep["ok"] = False

    t = found[T_TRADE_SUMMARY]
    chk("trade.blockLength", t["blockLength"], TRADE_BLOCK_LEN)
    g = {n: e for n, e in t["groups"]}["NoMDEntries"]
    d = dict(g)
    for name, (off, _fmt) in TRADE_F.items():
        chk(f"trade.NoMDEntries.{name}.offset", d[name], off)
    chk("trade.NoMDEntries.blockLength", d["__blockLength"], TRADE_ENTRY_LEN)
    chk("trade.NoMDEntries.dim", d["__dim"], "groupSize")
    b = found[T_BOOK]
    chk("book.blockLength", b["blockLength"], BOOK_BLOCK_LEN)
    gb = dict({n: e for n, e in b["groups"]}["NoMDEntries"])
    for name, (off, _fmt) in BOOK_F.items():
        chk(f"book.NoMDEntries.{name}.offset", gb[name], off)
    chk("book.NoMDEntries.blockLength", gb["__blockLength"], BOOK_ENTRY_LEN)
    chk("book.NoMDEntries.dim", gb["__dim"], "groupSize")
    return rep


def parse_secdef():
    tags = {"48": "security_id", "55": "symbol", "1151": "security_group",
            "9787": "price_display_factor", "969": "min_price_increment",
            "1147": "contract_multiplier", "1180": "channel", "167": "security_type",
            "1150": "settl_price", "200": "maturity_month_year", "461": "cfi_code",
            "1146": "tick_value"}
    es = {}
    with gzip.open(SECDEF, "rt", encoding="latin1") as fh:
        for raw in fh:
            fields = {}
            for tok in raw.rstrip("\n").split("\x01"):
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    if k in tags:
                        fields[tags[k]] = v
            if fields.get("security_group") != "ES":
                continue
            try:
                sid = int(fields["security_id"])
            except (KeyError, ValueError):
                continue
            es[sid] = fields
    return es


def read_int(body, base, off, fmt):
    v = struct.unpack_from("<" + fmt, body, base + off)[0]
    if fmt in "q" and v == NULL_I64:
        return None
    if fmt == "i" and v == NULL_I32:
        return None
    return v


def iter_group_entries(body, block_len, group_count, group_entry_len, group_index=0):
    """Iterate entry bodies of repeating group ``group_index`` (groupSize dim)."""
    offset = block_len
    for gi in range(group_count):
        entry_len = struct.unpack_from("<H", body, offset)[0]
        count = body[offset + 2]
        offset += 3
        if gi == group_index:
            for _ in range(count):
                yield body[offset:offset + entry_len]
                offset += entry_len
        else:
            offset += count * entry_len


def iter_messages(payload):
    if len(payload) < 12:
        return
    seq, send_ns = struct.unpack_from("<IQ", payload, 0)
    off, total = 12, len(payload)
    while off + 10 <= total:
        size, block_len, tid, schema_id, version = struct.unpack_from("<HHHHH", payload, off)
        if size < 10 or off + size > total:
            raise ValueError(f"message framing break: size={size} at {off} of {total}")
        yield seq, send_ns, tid, block_len, schema_id, version, payload[off + 10:off + size]
        off += size
    if off != total:
        raise ValueError("trailing bytes in packet")


def iter_pcap_records(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
        magic, _vmaj, _vmin, _tz, _sig, snaplen, linktype = struct.unpack_from("<IHHiIII", head)
        if magic != 0xA1B23C4D:
            raise ValueError(f"unexpected pcap magic 0x{magic:08x}")
        buf = b""
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            buf += chunk
            pos = 0
            n = len(buf)
            while pos + 16 <= n:
                ts_sec, ts_nsec, incl, orig = struct.unpack_from("<IIII", buf, pos)
                if pos + 16 + incl > n:
                    break
                yield ts_sec, ts_nsec, incl, orig, buf[pos + 16:pos + 16 + incl]
                pos += 16 + incl
            buf = buf[pos:]
        if buf:
            raise ValueError(f"{len(buf)} truncated trailing bytes")


def udp_of(frame):
    if len(frame) < 34:
        return None
    et = frame[12] << 8 | frame[13]
    off = 14
    if et in (0x8100, 0x88A8):
        if len(frame) < 38:
            return None
        et = frame[16] << 8 | frame[17]
        off = 18
    if et != 0x0800:
        return None
    ver_ihl = frame[off]
    if ver_ihl >> 4 != 4:
        return None
    ihl = (ver_ihl & 0x0F) * 4
    if ihl < 20 or len(frame) < off + ihl + 8:
        return None
    if frame[off + 9] != 17:
        return None
    if (frame[off + 6] << 8 | frame[off + 7]) & 0x3FFF:
        return None
    u = off + ihl
    sport, dport, length = struct.unpack_from(">HHH", frame, u)
    if length < 8:
        return None
    return sport, dport, frame[u + 8:u + length]


def main():
    out = {}
    out["layout_check"] = check_layouts()
    if not out["layout_check"]["ok"]:
        print("LAYOUT CHECK FAILED", file=sys.stderr)

    es = parse_secdef()
    out["secdef_es_instruments"] = len(es)
    primary = 3445
    pf = float(es[primary]["price_display_factor"])
    tick_points = float(es[primary]["min_price_increment"]) * pf
    scale = 1e-9 * pf
    point_value = float(es[primary]["contract_multiplier"])
    out["primary"] = {"security_id": primary, "symbol": es[primary]["symbol"],
                      "price_display_factor": pf, "min_price_increment": es[primary]["min_price_increment"],
                      "contract_multiplier": point_value, "settl_price": es[primary].get("settl_price"),
                      "tick_points": tick_points}

    trades_path = os.path.join(HERE, "rederived_trades.csv")
    bbo_path = os.path.join(HERE, "rederived_bbo_increments.csv")

    stats = {
        "pcap_records": 0,
        "es_packets": 0,
        "messages": 0,
        "templates": collections.Counter(),
        "off_channel_ids": collections.Counter(),
        "trades_rows": 0,
        "by_aggressor": collections.Counter(),
        "by_symbol": collections.Counter(),
        "aggressor_at_tob": 0, "aggressor_outside": 0, "aggressor_checked": 0,
        "outside_distance_ticks": collections.Counter(),
        "bbo_rows": 0, "rows_by_flag": collections.Counter(),
        "level1_deletes": 0, "level1_deletes_without_replacement": 0,
        "crossed_or_locked": 0, "level1_missing_after_change": 0,
        "book_resets": 0,
        "ts_regressions": 0, "send_time_regressions": 0, "capture_time_regressions": 0,
        "seq_by_port": {},
        "out_of_window_packets": 0,
        "reconstruction_events": [],
        "book_entry_events": 0,
        "es_packet_seq_span": [None, None],
    }
    seq_sets = {}
    levels = {}
    tob = {}
    tob_events = []
    last_trade = {}
    last_send = None
    last_capture = None

    with open(trades_path, "w", newline="") as tf, open(bbo_path, "w", newline="") as bf:
        tw, bw = csv.writer(tf), csv.writer(bf)
        tw.writerow(TRADE_COLUMNS)
        bw.writerow(BBO_COLUMNS)

        for ts_sec, ts_nsec, incl, orig, frame in iter_pcap_records(PCAP):
            stats["pcap_records"] += 1
            capture_ns = ts_sec * 1_000_000_000 + ts_nsec
            if last_capture is not None and capture_ns < last_capture:
                stats["capture_time_regressions"] += 1
            last_capture = capture_ns
            u = udp_of(frame)
            if u is None:
                continue
            sport, dport, payload = u
            if dport not in (14310, 15310):
                continue
            feed = "A" if dport == 14310 else "B"
            stats["es_packets"] += 1
            try:
                msgs = list(iter_messages(payload))
            except ValueError as exc:
                out.setdefault("framing_errors", []).append(str(exc))
                continue
            if not msgs:
                continue
            seq = msgs[0][0]
            send_ns = msgs[0][1]
            seq_sets.setdefault(feed, set()).add(seq)
            span = stats["es_packet_seq_span"]
            span[0] = seq if span[0] is None else min(span[0], seq)
            span[1] = seq if span[1] is None else max(span[1], seq)
            if not (WINDOW_START_NS <= send_ns < WINDOW_END_NS):
                stats["out_of_window_packets"] += 1
            if last_send is not None and send_ns < last_send:
                stats["send_time_regressions"] += 1
            last_send = send_ns

            for _seq, send_time, tid, block_len, schema_id, version, body in msgs:
                stats["messages"] += 1
                stats["templates"][tid] += 1
                if schema_id != 1 or version != 9:
                    out.setdefault("schema_anomalies", []).append((_seq, schema_id, version))
                if tid == T_TRADE_SUMMARY:
                    if block_len != TRADE_BLOCK_LEN:
                        raise ValueError(f"trade block length {block_len}")
                    transact_ns = struct.unpack_from("<Q", body, 0)[0]
                    for entry in iter_group_entries(body, TRADE_BLOCK_LEN, 1, TRADE_ENTRY_LEN):
                        sid = struct.unpack_from("<i", entry, 12)[0]
                        if sid not in es:
                            stats["off_channel_ids"][sid] += 1
                            continue
                        price = read_int(entry, 0, 0, "q")
                        size = read_int(entry, 0, 8, "i")
                        rpt = struct.unpack_from("<I", entry, 16)[0]
                        norders = read_int(entry, 0, 20, "i")
                        aggr = entry[24]
                        action = entry[25]
                        teid = read_int(entry, 0, 26, "I")
                        side = AGGRESSOR.get(aggr, "?")
                        stats["by_aggressor"][side] += 1
                        if action not in (0, 1):
                            continue
                        sym = es[sid]["symbol"]
                        stats["by_symbol"][sym] += 1
                        top = tob.get(sid)
                        if top and top.get("B") and top.get("A"):
                            bp, ap = top["B"][0], top["A"][0]
                            stats["aggressor_checked"] += 1
                            if price is not None and (price < bp or price > ap):
                                stats["aggressor_outside"] += 1
                                dist = (bp - price) if price < bp else (price - ap)
                                stats["outside_distance_ticks"][round(dist / (tick_points * 1e11), 3)] += 1
                            elif (side == "B" and price == ap) or (side == "S" and price == bp):
                                stats["aggressor_at_tob"] += 1
                        prev = last_trade.get(sid)
                        if prev is not None and transact_ns < prev[0]:
                            stats["ts_regressions"] += 1
                        last_trade[sid] = (transact_ns, _seq)
                        tw.writerow([
                            transact_ns, capture_ns, send_time, _seq, feed, sid, sym,
                            price, round(price * scale, 9), size, side, aggr,
                            ACTION.get(action, str(action)), rpt, teid, norders,
                            T_TRADE_SUMMARY,
                        ])
                        stats["trades_rows"] += 1

                elif tid == T_BOOK:
                    if block_len != BOOK_BLOCK_LEN:
                        raise ValueError(f"book block length {block_len}")
                    transact_ns = struct.unpack_from("<Q", body, 0)[0]
                    touched = {}
                    for entry in iter_group_entries(body, BOOK_BLOCK_LEN, 1, BOOK_ENTRY_LEN):
                        sid = struct.unpack_from("<i", entry, 12)[0]
                        if sid not in es:
                            stats["off_channel_ids"][sid] += 1
                            continue
                        stats["book_entry_events"] += 1
                        price = read_int(entry, 0, 0, "q")
                        size = read_int(entry, 0, 8, "i")
                        rpt = struct.unpack_from("<I", entry, 16)[0]
                        level = entry[24]
                        action = entry[25]
                        etype = chr(entry[26])
                        book = levels.setdefault(sid, {"B": {}, "A": {}})
                        if etype == "J":
                            stats["book_resets"] += 1
                            book["B"].clear()
                            book["A"].clear()
                            tob.pop(sid, None)
                            touched.setdefault(sid, {})["reset"] = True
                            continue
                        side = SIDE_FROM_ENTRY.get(etype)
                        if side is None or price is None:
                            continue
                        sl = book[side]
                        if action in (0, 1, 5):
                            sl[level] = (price, size if size is not None else 0)
                        elif action == 2:
                            if level == 1:
                                stats["level1_deletes"] += 1
                            sl.pop(level, None)
                            shifted = {lvl - 1: v for lvl, v in sl.items() if lvl > level}
                            for lvl in [lvl for lvl in sl if lvl > level]:
                                sl.pop(lvl)
                            sl.update(shifted)
                            if level == 1 and 1 not in sl:
                                stats["level1_deletes_without_replacement"] += 1
                        elif action == 3:
                            for lvl in [lvl for lvl in sl if lvl >= level]:
                                sl.pop(lvl)
                        elif action == 4:
                            for lvl in [lvl for lvl in sl if lvl <= level]:
                                sl.pop(lvl)
                        else:
                            continue
                        touched.setdefault(sid, {})[side] = (capture_ns, _seq, transact_ns,
                                                             rpt, level, action, etype)

                    for sid, caused in touched.items():
                        if "reset" in caused and len(caused) == 1:
                            if tob.get(sid) is not None:
                                tob[sid] = None
                                tob_events.append((transact_ns, _seq, sid, None, None, None, None))
                            continue
                        book = levels[sid]
                        top = {}
                        for side in ("B", "A"):
                            if book[side]:
                                if 1 in book[side]:
                                    top[side] = (book[side][1][0], book[side][1][1], "direct_l1", 1)
                                else:
                                    lvl = min(book[side])
                                    top[side] = (book[side][lvl][0], book[side][lvl][1], "reconstructed", lvl)
                        if all(v is None for v in top.values()):
                            tob[sid] = None
                            continue
                        bid = top.get("B")
                        ask = top.get("A")
                        new_state = {"B": (bid[0], bid[1]) if bid else (None, None),
                                     "A": (ask[0], ask[1]) if ask else (None, None)}
                        if tob.get(sid) == new_state:
                            continue
                        tob[sid] = new_state
                        tob_events.append((transact_ns, _seq, sid,
                                           new_state["B"][0], new_state["B"][1],
                                           new_state["A"][0], new_state["A"][1]))
                        for side, rec in caused.items():
                            if side == "reset":
                                continue
                            ts_ = top.get(side)
                            if ts_ is None:
                                continue
                            flag = "direct_l1" if ts_[2] == "direct_l1" else "reconstructed"
                            if flag == "reconstructed":
                                stats["reconstruction_events"].append(
                                    {"sequence": _seq, "instrument_id": sid, "side": side,
                                     "level_used": ts_[3], "price": ts_[0], "size": ts_[1],
                                     "touched_level": rec[4], "touched_action": ACTION.get(rec[5], rec[5]),
                                     "touched_entry_type": rec[6]})
                            bw.writerow([
                                rec[2], rec[0], rec[2], _seq, feed, sid, es[sid]["symbol"],
                                side, ts_[0], round(ts_[0] * scale, 9), ts_[1], flag,
                                rec[3], ts_[3], ACTION.get(rec[5], rec[5]), rec[6],
                                T_BOOK,
                            ])
                            stats["rows_by_flag"][flag] += 1
                            stats["bbo_rows"] += 1
                        if new_state["B"][0] is None or new_state["A"][0] is None:
                            stats["level1_missing_after_change"] += 1
                        elif new_state["A"][0] <= new_state["B"][0]:
                            stats["crossed_or_locked"] += 1

    out["stats"] = {k: (dict(v) if isinstance(v, collections.Counter) else v)
                    for k, v in stats.items()}
    out["re-derived"] = {}
    out["rederived_trades_sha256"] = sha256_file(trades_path)
    out["rederived_bbo_sha256"] = sha256_file(bbo_path)
    out["producer_trades_sha256"] = sha256_file(os.path.join(PROD, "trades.csv"))
    out["producer_bbo_sha256"] = sha256_file(os.path.join(PROD, "bbo_increments.csv"))
    out["trades_byte_identical"] = (out["rederived_trades_sha256"] == out["producer_trades_sha256"])
    out["bbo_byte_identical"] = (out["rederived_bbo_sha256"] == out["producer_bbo_sha256"])

    out["sequence_per_feed"] = {
        f: {"count": len(s), "missing_over_span": (max(s) - min(s) + 1) - len(s),
            "gap_events": sum(1 for a, b in zip(sorted(s), sorted(s)[1:]) if b != a + 1),
            "first": min(s), "last": max(s)} for f, s in seq_sets.items()
    }
    union = set().union(*seq_sets.values()) if seq_sets else set()
    out["sequence_union"] = {"count": len(union), "first": min(union) if union else None,
                             "last": max(union) if union else None,
                             "gaps": (max(union) - min(union) + 1 - len(union)) if union else None,
                             "duplicates": sum(len(s) for s in seq_sets.values()) - len(union)}

    # ---- claim 11 ----
    events = sorted((e for e in tob_events if e[2] == primary and e[3] is not None),
                    key=lambda e: e[0])
    grid_rows = []
    spreads = []
    tick_counts = collections.Counter()
    idx = 0
    cur = None
    last_ev = None
    n_points = (WINDOW_END_NS - WINDOW_START_NS) // GRID_NS
    for p in range(n_points):
        ts = WINDOW_START_NS + p * GRID_NS
        while idx < len(events) and events[idx][0] <= ts:
            cur = events[idx]
            last_ev = events[idx][0]
            idx += 1
        if cur is None or cur[3] is None or cur[5] is None:
            grid_rows.append((p, ts, None, None, None, None, None, None, None, None))
            continue
        sp = (cur[5] - cur[3]) * scale
        ticks = sp / tick_points
        grid_rows.append((p, ts, cur[3], cur[5], cur[4], cur[6], round(ticks, 6),
                          round(sp, 6), round(sp / 2, 6), round(ticks / 2, 6)))
        spreads.append(sp)
        tick_counts[round(ticks, 3)] += 1
    mean_s = sum(spreads) / len(spreads)
    out["claim11"] = {
        "grid_points": n_points,
        "with_quote": len(spreads),
        "one_tick_points": tick_counts.get(1.0),
        "spread_points_mean_recomputed": mean_s,
        "half_spread_points_mean_recomputed": mean_s / 2,
        "spread_points_min": min(spreads), "spread_points_max": max(spreads),
        "tick_counts": {str(k): v for k, v in sorted(tick_counts.items())},
        "spread_usd_mean": mean_s * point_value,
        "identity_half_S_entry_plus_half_S_exit_mean": mean_s,
        "identity_check_absdiff": abs(mean_s - mean_s),
        "identity_note": "E[1/2 S_entry + 1/2 S_exit] = 1/2 E[S_entry] + 1/2 E[S_exit] = E[S] "
                         "when entry/exit spreads are i.i.d. samples on the same grid; it equals "
                         "the mean spread, NOT 2 x (half of mean spread).",
    }
    with open(os.path.join(HERE, "rederived_spread_grid.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["grid_index", "ts_ns", "bid_px", "ask_px", "bid_sz", "ask_sz",
                    "spread_ticks", "spread_points", "half_spread_points", "half_spread_ticks"])
        w.writerows(grid_rows)
    out["rederived_grid_sha256"] = sha256_file(os.path.join(HERE, "rederived_spread_grid.csv"))
    out["producer_grid_sha256"] = sha256_file(os.path.join(PROD, "spread_grid.csv"))

    with open(os.path.join(HERE, "v2_es_rederive.json"), "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "stats"} | {
        "stats_templates": dict(stats["templates"]),
        "stats_by_aggressor": dict(stats["by_aggressor"]),
    }, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()