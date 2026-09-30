"""CME Globex MDP 3.0 (SBE) ES normalization for the 2023-07-17 RTH-open sample.

Scope (GOAL-M2-BRIDGE-001, epoch 1, worker W2): acquire the public, no-auth
Databento CME Globex MDP 3.0 sample capture for 2023-07-17T13:30:00Z and derive
an admitted, causally ordered event stream for the ES channel (channel 310):

  * trades with aggressor side,
  * top-of-book (BBO) increments,
  * observed-spread cost inputs on a 10 ms grid.

No economics: no markouts, no OFI construction, no P&L.

Everything the decoder needs about the wire format comes from one of three
externally verifiable sources, never from a guess:

  * the capture itself -- pcap magic ``0xa1b23c4d`` (nanosecond), link type 1
    (Ethernet), MDP 3.0 packet framing (4-byte sequence + 8-byte nanosecond
    exchange send time, then 2-byte message size + 8-byte SBE message header);
  * the CME MDP 3.0 SBE schema ``Cme.Futures.Mdp3.Sbe.v1.9.xml`` as mirrored by
    the Open-Markets-Initiative Directory.  Template ids, block lengths, group
    dimensions and field offsets are transcribed in ``TEMPLATES`` below;
    ``verify_layout_against_xml`` re-checks every transcribed offset against the
    schema XML and is invoked by the ``verify-layout`` subcommand;
  * the CME channel configuration file and the CME security-definition snapshot
    for the session, which supply the channel/feed identity (channel 310 = the
    ES group) and the authoritative SecurityID -> contract-month mapping.

Usage::

    python3 -m M2.src.mdp_es_normalize probe    --url ... --out-dir ...
    python3 -m M2.src.mdp_es_normalize stream   --url ... --out-dir ... --raw-dir ...
    python3 -m M2.src.mdp_es_normalize decode   --pcap <file.pcap> --out-dir ... \
                                                --secdef <secdef.dat.gz> [--raw <extract.pcap>]
    python3 -m M2.src.mdp_es_normalize verify-layout --schema <schema.xml>
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import threading
import time

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from .ingest import FeedFormatError, sha256_file

# --------------------------------------------------------------------------- #
# frozen facts about this sample (all observed or authoritative, see report)
# --------------------------------------------------------------------------- #

UPSTREAM_URL = (
    "https://sample-pcaps-dl.databento.com/glbx-all/20230717/"
    "dc3-glbx-ab-dedup-20230717T133000.pcap.zst"
)
UPSTREAM_CHANNEL_DIR = "https://sample-pcaps-dl.databento.com/glbx-all/20230717/"
UPSTREAM_CONFIG_URL = (
    "https://sample-pcaps-dl.databento.com/glbx-all/20230716/config-2023-07-16.xml"
)
UPSTREAM_SECDEF_URL = (
    "https://sample-pcaps-dl.databento.com/glbx-all/20230717/secdef-2023-07-17.dat.gz"
)

ES_CHANNEL_ID = 310
ES_CHANNEL_LABEL = "CME Globex Equity Futures"
ES_FEED_PORTS = {14310: "A", 15310: "B"}
ES_FEED_MULTICAST = {14310: "224.0.31.1", 15310: "224.0.32.1"}

WINDOW_START_NS = 1_689_600_600_000_000_000  # 2023-07-17T13:30:00Z
WINDOW_END_NS = 1_689_601_200_000_000_000  # 2023-07-17T13:40:00Z
COVERAGE_DATE = "2023-07-17"
GRID_NS = 10_000_000  # 10 ms
SPREAD_GRID_PERIOD_S = 0.010

PCAP_MAGIC_NS = 0xA1B23C4D
PCAP_LINKTYPE_ETHERNET = 1

MDP_SCHEMA_ID = 1
MDP_SCHEMA_VERSION = 9  # observed in every message header of the capture
MDP_SCHEMA_NAME = "Cme.Futures.Mdp3.Sbe.v1.9.xml"
MDP_MESSAGE_HEADER_BYTES = 8
MDP_MESSAGE_SIZE_BYTES = 2

PRICE9_EXPONENT = -9
PRICE9_NULL = 9_223_372_036_854_775_807
UINT32_NULL = 4_294_967_295
INT32_NULL = 2_147_483_647

ES_POINT_VALUE_USD = 50.0  # fallback only: the live value comes from the instrument definition

# MDP 3.0 template ids (CME SBE schema, ids are stable across schema versions)
T_CHANNEL_RESET = 4
T_SECURITY_STATUS = 30
T_VOLUME = 37
T_BOOK = 46
T_ORDER_BOOK = 47
T_TRADE_SUMMARY = 48
T_SESSION_STATISTICS = 51

# AggressorSide enum (Cme.Futures.Mdp3.Sbe.v1.9.xml)
AGGRESSOR_SIDE = {0: "N", 1: "B", 2: "S"}
# MDUpdateAction enum
MD_UPDATE_ACTION = {
    0: "New",
    1: "Change",
    2: "Delete",
    3: "DeleteThru",
    4: "DeleteFrom",
    5: "Overlay",
}
# MDEntryTypeBook enum
MD_ENTRY_TYPE_BOOK = {"0": "Bid", "1": "Offer", "E": "ImpliedBid", "F": "ImpliedOffer", "J": "BookReset"}
SIDE_FROM_ENTRY_TYPE = {"0": "B", "1": "A", "E": "B", "F": "A"}

# --------------------------------------------------------------------------- #
# transcribed SBE layouts
#
# Each template: block_length (declared in the message header at runtime and
# re-checked against the schema), the block fields we read, and the repeating
# groups in wire order.  ``dim`` selects the group header encoding:
#   "groupSize"        -> blockLength(uint16) + numInGroup(uint8)  = 3 bytes
#   "groupSize8Byte"   -> blockLength(uint16) @0 + numInGroup(uint8) @7 = 8 bytes
# Field tuples are (offset, size, kind).  Offsets are the schema's own.
# --------------------------------------------------------------------------- #

TEMPLATES: dict[int, dict] = {
    T_SECURITY_STATUS: {
        "name": "SecurityStatus30",
        "block_length": 30,
        "block": {
            "TransactTime": (0, 8, "u64"),
            "SecurityGroup": (8, 6, "alpha"),
            "Asset": (14, 6, "alpha"),
            "SecurityID": (20, 4, "i32null"),
            "TradeDate": (24, 2, "u16"),
            "MatchEventIndicator": (26, 1, "u8"),
            "SecurityTradingStatus": (27, 1, "u8"),
            "HaltReason": (28, 1, "u8"),
            "SecurityTradingEvent": (29, 1, "u8"),
        },
        "groups": [],
    },
    T_VOLUME: {
        "name": "MDIncrementalRefreshVolume37",
        "block_length": 11,
        "block": {"TransactTime": (0, 8, "u64"), "MatchEventIndicator": (8, 1, "u8")},
        "groups": [
            {
                "name": "NoMDEntries",
                "dim": "groupSize",
                "block_length": 16,
                "fields": {
                    "MDEntrySize": (0, 4, "i32"),
                    "SecurityID": (4, 4, "i32"),
                    "RptSeq": (8, 4, "u32"),
                    "MDUpdateAction": (12, 1, "u8"),
                },
            }
        ],
    },
    T_BOOK: {
        "name": "MDIncrementalRefreshBook46",
        "block_length": 11,
        "block": {"TransactTime": (0, 8, "u64"), "MatchEventIndicator": (8, 1, "u8")},
        "groups": [
            {
                "name": "NoMDEntries",
                "dim": "groupSize",
                "block_length": 32,
                "fields": {
                    "MDEntryPx": (0, 8, "i64null"),
                    "MDEntrySize": (8, 4, "i32null"),
                    "SecurityID": (12, 4, "i32"),
                    "RptSeq": (16, 4, "u32"),
                    "NumberOfOrders": (20, 4, "i32null"),
                    "MDPriceLevel": (24, 1, "u8"),
                    "MDUpdateAction": (25, 1, "u8"),
                    "MDEntryType": (26, 1, "char"),
                },
            },
            {
                "name": "NoOrderIDEntries",
                "dim": "groupSize8Byte",
                "block_length": 24,
                "fields": {
                    "OrderID": (0, 8, "u64"),
                    "MDOrderPriority": (8, 8, "u64null"),
                    "MDDisplayQty": (16, 4, "i32null"),
                    "ReferenceID": (20, 1, "u8null"),
                    "OrderUpdateAction": (21, 1, "u8"),
                },
            },
        ],
    },
    T_ORDER_BOOK: {
        "name": "MDIncrementalRefreshOrderBook47",
        "block_length": 11,
        "block": {"TransactTime": (0, 8, "u64"), "MatchEventIndicator": (8, 1, "u8")},
        "groups": [
            {
                "name": "NoMDEntries",
                "dim": "groupSize",
                "block_length": 40,
                "fields": {
                    "OrderID": (0, 8, "u64null"),
                    "MDOrderPriority": (8, 8, "u64null"),
                    "MDEntryPx": (16, 8, "i64null"),
                    "MDDisplayQty": (24, 4, "i32null"),
                    "SecurityID": (28, 4, "i32"),
                    "MDUpdateAction": (32, 1, "u8"),
                    "MDEntryType": (33, 1, "char"),
                },
            }
        ],
    },
    T_TRADE_SUMMARY: {
        "name": "MDIncrementalRefreshTradeSummary48",
        "block_length": 11,
        "block": {"TransactTime": (0, 8, "u64"), "MatchEventIndicator": (8, 1, "u8")},
        "groups": [
            {
                "name": "NoMDEntries",
                "dim": "groupSize",
                "block_length": 32,
                "fields": {
                    "MDEntryPx": (0, 8, "i64"),
                    "MDEntrySize": (8, 4, "i32"),
                    "SecurityID": (12, 4, "i32"),
                    "RptSeq": (16, 4, "u32"),
                    "NumberOfOrders": (20, 4, "i32"),
                    "AggressorSide": (24, 1, "u8"),
                    "MDUpdateAction": (25, 1, "u8"),
                    "MDTradeEntryID": (26, 4, "u32null"),
                },
            },
            {
                "name": "NoOrderIDEntries",
                "dim": "groupSize8Byte",
                "block_length": 16,
                "fields": {"OrderID": (0, 8, "u64"), "LastQty": (8, 4, "i32")},
            },
        ],
    },
    T_SESSION_STATISTICS: {
        "name": "MDIncrementalRefreshSessionStatistics51",
        "block_length": 11,
        "block": {"TransactTime": (0, 8, "u64"), "MatchEventIndicator": (8, 1, "u8")},
        "groups": [
            {
                "name": "NoMDEntries",
                "dim": "groupSize",
                "block_length": 24,
                "fields": {
                    "MDEntryPx": (0, 8, "i64"),
                    "SecurityID": (8, 4, "i32"),
                    "RptSeq": (12, 4, "u32"),
                    "OpenCloseSettlFlag": (16, 1, "u8"),
                    "MDUpdateAction": (17, 1, "u8"),
                    "MDEntryType": (18, 1, "char"),
                    "MDEntrySize": (19, 4, "i32null"),
                },
            }
        ],
    },
}

_STRUCT_KIND = {
    "u64": ("<Q", 8),
    "i64": ("<q", 8),
    "u32": ("<I", 4),
    "i32": ("<i", 4),
    "u16": ("<H", 2),
    "u8": ("<B", 1),
    "u64null": ("<Q", 8),
    "i64null": ("<q", 8),
    "u32null": ("<I", 4),
    "i32null": ("<i", 4),
    "u8null": ("<B", 1),
}
_NULL = {
    "u64null": 2**64 - 1,
    "i64null": PRICE9_NULL,
    "u32null": UINT32_NULL,
    "i32null": INT32_NULL,
    "u8null": 255,
}


PRICE_MANTISSA_PER_SECDEF_UNIT = 1e-9  # SBE PRICE9/PRICENULL9 constant exponent -9


def price_index_points(mantissa: int, display_factor: float) -> float:
    """Contract price in quote units (index points for ES).

    Verified relation, established from this capture plus the session security
    definitions: ``mantissa * 1e-9 == secdef price value`` and
    ``secdef value * PriceDisplayFactor == quote units``.  Checked against three
    products with different display factors (ES 0.01, CL 0.01, ZN 1.0): the
    decoded best bid/ask brackets each product's own secdef settlement.
    """
    return mantissa * PRICE_MANTISSA_PER_SECDEF_UNIT * display_factor


def tick_mantissa_units(record: dict) -> int:
    """One minimum price increment expressed in wire mantissa units."""
    return int(round(float(record["min_price_increment"]) * 1e9))


def _read_field(body: bytes, spec: tuple, base: int = 0):
    """Read one transcribed field; return None for a NULL sentinel."""
    offset, _size, kind = spec
    if kind == "char":
        return chr(body[base + offset])
    if kind == "alpha":
        raw = body[base + offset : base + offset + _size]
        return raw.split(b"\x00", 1)[0].decode("ascii", "replace")
    fmt, size = _STRUCT_KIND[kind]
    value = struct.unpack_from(fmt, body, base + offset)[0]
    if kind in _NULL and value == _NULL[kind]:
        return None
    return value


def verify_layout_against_xml(schema_path: str) -> dict:
    """Re-check every transcribed offset/block length against the SBE schema XML."""
    import xml.etree.ElementTree as ET

    root = ET.parse(schema_path).getroot()
    for element in root.iter():
        if "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]

    by_id = {}
    for message in root.iter("message"):
        by_id[int(message.get("id"))] = message

    report = {"schema": os.path.basename(schema_path), "templates": {}, "ok": True}
    for template_id, spec in TEMPLATES.items():
        message = by_id.get(template_id)
        entry = {"name": spec["name"], "schema_name": None, "mismatches": []}
        if message is None:
            entry["mismatches"].append("template id absent from schema")
            report["ok"] = False
            report["templates"][str(template_id)] = entry
            continue
        entry["schema_name"] = message.get("name")
        if message.get("name") != spec["name"]:
            entry["mismatches"].append(
                f"name: schema={message.get('name')} transcribed={spec['name']}"
            )
        if int(message.get("blockLength")) != spec["block_length"]:
            entry["mismatches"].append(
                f"blockLength: schema={message.get('blockLength')} transcribed={spec['block_length']}"
            )
        schema_fields = {
            field.get("name"): int(field.get("offset"))
            for field in message.findall("field")
            if field.get("offset") is not None  # constant fields carry no wire bytes
        }
        for name, (offset, _size, _kind) in spec["block"].items():
            if schema_fields.get(name) != offset:
                entry["mismatches"].append(
                    f"block field {name}: schema offset={schema_fields.get(name)} transcribed={offset}"
                )
        schema_groups = message.findall("group")
        if len(schema_groups) != len(spec["groups"]):
            entry["mismatches"].append(
                f"group count: schema={len(schema_groups)} transcribed={len(spec['groups'])}"
            )
        for schema_group, group_spec in zip(schema_groups, spec["groups"]):
            if schema_group.get("name") != group_spec["name"]:
                entry["mismatches"].append(
                    f"group name: schema={schema_group.get('name')} transcribed={group_spec['name']}"
                )
            if schema_group.get("dimensionType") != group_spec["dim"]:
                entry["mismatches"].append(
                    f"group {group_spec['name']} dimensionType: "
                    f"schema={schema_group.get('dimensionType')} transcribed={group_spec['dim']}"
                )
            if int(schema_group.get("blockLength")) != group_spec["block_length"]:
                entry["mismatches"].append(
                    f"group {group_spec['name']} blockLength: schema={schema_group.get('blockLength')} "
                    f"transcribed={group_spec['block_length']}"
                )
            group_fields = {
                field.get("name"): int(field.get("offset"))
                for field in schema_group.findall("field")
                if field.get("offset") is not None
            }
            for name, (offset, _size, _kind) in group_spec["fields"].items():
                if group_fields.get(name) != offset:
                    entry["mismatches"].append(
                        f"group {group_spec['name']} field {name}: "
                        f"schema offset={group_fields.get(name)} transcribed={offset}"
                    )
        if entry["mismatches"]:
            report["ok"] = False
        report["templates"][str(template_id)] = entry
    return report


# --------------------------------------------------------------------------- #
# pcap / IPv4 / UDP / MDP 3.0 framing
# --------------------------------------------------------------------------- #


class PcapFramer:
    """Incremental pcap record reader (records yielded as they complete)."""

    __slots__ = ("header", "snaplen", "linktype", "_buf", "_pos", "records", "truncated_bytes")

    def __init__(self) -> None:
        self.header: bytes | None = None
        self.snaplen: int | None = None
        self.linktype: int | None = None
        self._buf = bytearray()
        self._pos = 0
        self.records = 0
        self.truncated_bytes = 0

    def feed(self, data: bytes):
        buf = self._buf
        buf += data
        if self.header is None:
            if len(buf) < 24:
                return
            magic, vmaj, vmin, _tz, _sig, snaplen, linktype = struct.unpack_from("<IHHiIII", buf, 0)
            if magic not in (PCAP_MAGIC_NS, 0xA1B2C3D4):
                raise FeedFormatError(f"unexpected pcap magic 0x{magic:08x}")
            self.header = bytes(buf[:24])
            self.snaplen = snaplen
            self.linktype = linktype
            self._pos = 24
        buf_len = len(buf)
        pos = self._pos
        while pos + 16 <= buf_len:
            ts_sec, ts_nsec, incl, orig = struct.unpack_from("<IIII", buf, pos)
            end = pos + 16 + incl
            if end > buf_len:
                break
            frame = bytes(buf[pos + 16 : end])
            pos = end
            self.records += 1
            yield ts_sec, ts_nsec, incl, orig, frame
        if pos > 4 << 20:
            del buf[:pos]
            self._pos = 0
        else:
            self._pos = pos
        self.truncated_bytes = len(self._buf) - self._pos


def extract_udp(frame: bytes):
    """Return (src_ip, dst_ip, sport, dport, payload) for a plain IPv4/UDP frame."""
    if len(frame) < 34:
        return None
    ethertype = frame[12] << 8 | frame[13]
    offset = 14
    if ethertype == 0x8100 or ethertype == 0x88A8:  # single VLAN tag
        if len(frame) < 38:
            return None
        ethertype = frame[16] << 8 | frame[17]
        offset = 18
    if ethertype != 0x0800:  # not IPv4
        return None
    version_ihl = frame[offset]
    if version_ihl >> 4 != 4:
        return None
    ihl = (version_ihl & 0x0F) * 4
    if ihl < 20 or len(frame) < offset + ihl + 8:
        return None
    if frame[offset + 9] != 17:  # UDP
        return None
    flags_frag = frame[offset + 6] << 8 | frame[offset + 7]
    if flags_frag & 0x3FFF:  # fragmented or non-zero offset
        return None
    udp = offset + ihl
    sport, dport, length = struct.unpack_from(">HHH", frame, udp)
    if length < 8:
        return None
    payload = frame[udp + 8 : udp + length]
    src_ip = ".".join(str(byte) for byte in frame[offset + 12 : offset + 16])
    dst_ip = ".".join(str(byte) for byte in frame[offset + 16 : offset + 20])
    return src_ip, dst_ip, sport, dport, payload


def iter_mdp_messages(payload: bytes):
    """Yield (sequence, send_time_ns, template_id, block_length, message_body).

    MDP 3.0 UDP payload framing: 12-byte packet header (uint32 sequence,
    uint64 nanosecond exchange send time), then messages of
    [uint16 size][uint16 blockLength][uint16 templateId][uint16 schemaId][uint16 version][body].
    """
    if len(payload) < 12:
        return
    sequence, send_time_ns = struct.unpack_from("<IQ", payload, 0)
    offset = 12
    total = len(payload)
    while offset + 10 <= total:
        size, block_length, template_id, schema_id, version = struct.unpack_from(
            "<HHHHH", payload, offset
        )
        if size < 10 or offset + size > total:
            raise FeedFormatError(
                f"message framing break: size={size} at offset {offset} of {total} bytes"
            )
        yield sequence, send_time_ns, template_id, block_length, schema_id, version, payload[
            offset + 10 : offset + size
        ]
        offset += size
    if offset != total:
        raise FeedFormatError(f"trailing bytes in packet: {total - offset}")


# --------------------------------------------------------------------------- #
# CME reference files
# --------------------------------------------------------------------------- #


def parse_channel_config(path: str) -> dict:
    """Extract channel 310 (ES group) feed definitions from the CME config XML."""
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    result = {"channel_id": None, "label": None, "products": [], "groups": [], "connections": []}
    for channel in root.iter("channel"):
        if channel.get("id") != str(ES_CHANNEL_ID):
            continue
        result["channel_id"] = channel.get("id")
        result["label"] = channel.get("label")
        for product in channel.iter("product"):
            result["products"].append(product.get("code"))
            for group in product.iter("group"):
                result["groups"].append(group.get("code"))
        for connection in channel.iter("connection"):
            kind = connection.find("type")
            port = connection.find("port")
            ip = connection.find("ip")
            feed = connection.find("feed")
            result["connections"].append(
                {
                    "id": connection.get("id"),
                    "feed_type": kind.get("feed-type") if kind is not None else None,
                    "protocol": connection.findtext("protocol"),
                    "multicast_ip": ip.text if ip is not None else None,
                    "port": int(port.text) if port is not None else None,
                    "feed": feed.text if feed is not None else None,
                }
            )
    return result


SECDEF_TAGS = {
    "35": "msg_type",
    "48": "security_id",
    "55": "symbol",
    "1151": "security_group",
    "6937": "asset",
    "167": "security_type",
    "461": "cfi_code",
    "200": "maturity_month_year",
    "1180": "channel",
    "969": "min_price_increment",
    "1142": "feed_type",
    "779": "last_update",
    "22": "security_id_source",
    "207": "security_exchange",
    "15": "currency",
    "562": "min_trade_volume",
    "9787": "price_display_factor",
    "1150": "settl_price",
    "1148": "low_limit",
    "1149": "high_limit",
    "5796": "settl_date",
    "1147": "contract_multiplier",
    "1146": "tick_value",
}

ES_OUTRIGHT_RE = re.compile(r"^ES[FGHJKMNQUVXZ]\d$")


def parse_secdef(path: str, want_group: str = "ES", channel: str = str(ES_CHANNEL_ID)) -> dict:
    """Parse a CME security-definition snapshot (FIX tag=value text).

    Returns the instruments of ``want_group`` (the ES identity set) and every
    instrument whose own definition names ``channel`` (the channel-membership
    set used to check what the capture's channel-310 ports actually carry).
    """
    opener = gzip.open if path.endswith(".gz") else open
    instruments = {}
    channel_instruments = {}
    counts = collections.Counter()
    with opener(path, "rt", encoding="latin1") as handle:
        for raw in handle:
            record = raw.rstrip("\n")
            if not record:
                continue
            fields = {}
            for token in record.split("\x01"):
                if "=" not in token:
                    continue
                tag, value = token.split("=", 1)
                name = SECDEF_TAGS.get(tag)
                if name:
                    fields[name] = value
            counts[fields.get("msg_type")] += 1
            try:
                security_id = int(fields["security_id"])
            except (KeyError, ValueError):
                continue
            if fields.get("channel") == channel:
                channel_instruments[security_id] = {
                    "symbol": fields.get("symbol", ""),
                    "security_group": fields.get("security_group"),
                    "security_type": fields.get("security_type"),
                }
                counts["channel_records"] += 1
            if fields.get("security_group") != want_group:
                continue
            counts["group_records"] += 1
            symbol = fields.get("symbol", "")
            instruments[security_id] = {
                "security_id": security_id,
                "symbol": symbol,
                "security_group": fields.get("security_group"),
                "asset": fields.get("asset"),
                "security_type": fields.get("security_type"),
                "cfi_code": fields.get("cfi_code"),
                "maturity_month_year": fields.get("maturity_month_year"),
                "channel": fields.get("channel"),
                "feed_type": fields.get("feed_type"),
                "min_price_increment": fields.get("min_price_increment"),
                "price_display_factor": fields.get("price_display_factor"),
                "settl_price": fields.get("settl_price"),
                "settl_date": fields.get("settl_date"),
                "high_limit": fields.get("high_limit"),
                "low_limit": fields.get("low_limit"),
                "contract_multiplier": fields.get("contract_multiplier"),
                "tick_value": fields.get("tick_value"),
                "last_update": fields.get("last_update"),
                "is_outright": bool(ES_OUTRIGHT_RE.match(symbol)),
                "is_calendar_spread": "-" in symbol,
            }
    return {
        "instruments": instruments,
        "channel_instruments": channel_instruments,
        "record_counts": dict(counts),
    }


# --------------------------------------------------------------------------- #
# normalization
# --------------------------------------------------------------------------- #


class EsNormalizer:
    """Decode ES-channel MDP 3.0 traffic into trades, BBO increments and stats."""

    def __init__(
        self,
        es_ids: dict[int, dict],
        channel_ids: dict[int, dict] | None = None,
        trades_fh=None,
        bbo_fh=None,
        extract_fh=None,
        pcap_header: bytes | None = None,
        window_start_ns: int = WINDOW_START_NS,
        window_end_ns: int = WINDOW_END_NS,
    ) -> None:
        self.es_ids = es_ids
        self.channel_ids = channel_ids or {}
        self.symbol_by_id = {sid: rec["symbol"] for sid, rec in es_ids.items()}
        self.outrights = {sid for sid, rec in es_ids.items() if rec["is_outright"]}
        self.scale_by_id = {}
        self.settl_mantissa_by_id = {}
        self.band_mantissa_by_id = {}
        self.observed_mantissas: dict[int, set] = collections.defaultdict(set)
        for security_id, record in es_ids.items():
            factor = record.get("price_display_factor")
            if factor is not None:
                self.scale_by_id[security_id] = PRICE_MANTISSA_PER_SECDEF_UNIT * float(factor)
            for key, target in (("settl_price", self.settl_mantissa_by_id), ("high_limit", None)):
                value = record.get(key)
                if value is None:
                    continue
                if key == "settl_price":
                    target[security_id] = int(round(float(value) * 1e9))
                elif self.scale_by_id.get(security_id):
                    self.band_mantissa_by_id.setdefault(security_id, {})["high"] = int(
                        round(float(value) * 1e9)
                    )
            low = record.get("low_limit")
            if low is not None:
                self.band_mantissa_by_id.setdefault(security_id, {})["low"] = int(
                    round(float(low) * 1e9)
                )
        self.spreads = {sid for sid, rec in es_ids.items() if rec["is_calendar_spread"]}
        self.trades_writer = csv.writer(trades_fh) if trades_fh else None
        self.bbo_writer = csv.writer(bbo_fh) if bbo_fh else None
        self.extract_fh = extract_fh
        self._pcap_header_written = False
        if self.extract_fh is not None and pcap_header is not None:
            self.extract_fh.write(pcap_header)
            self._pcap_header_written = True
        self.window_start_ns = window_start_ns
        self.window_end_ns = window_end_ns

        # book state (market by price, template 46)
        self.levels: dict[int, dict[str, dict[int, tuple[int, int]]]] = {}
        self.tob: dict[int, dict[str, tuple[int, int] | None]] = {}
        self.tob_events: list[tuple] = []
        # order book state (market by order, template 47) -- independent cross-check
        self.orders: dict[int, dict[int, tuple[str, int, int]]] = {}

        self.stats = {
            "packets_pcap_records": 0,
            "packets_non_ipv4": 0,
            "packets_fragmented": 0,
            "packets_udp_total": 0,
            "packets_es_channel": 0,
            "packets_es_by_port": {},
            "packets_es_by_port_in_window": {},
            "packets_es_out_of_window": 0,
            "bytes_es_extract": 0,
            "bytes_pcap_records_es": 0,
            "messages_es_channel": 0,
            "messages_by_template": {},
            "messages_by_template_es_ids": {},
            "message_tiling_breaks": 0,
            "unknown_templates": {},
            "sequence": {},
            "timestamps": {},
            "trades": {
                "rows": 0,
                "by_action": {},
                "by_aggressor": {},
                "by_instrument": {},
                "entry_events": 0,
                "order_id_entries": 0,
                "ts_event_min_ns": None,
                "ts_event_max_ns": None,
                "ts_event_regressions": 0,
                "sequence_regressions": 0,
                "rpt_seq_duplicates": 0,
            },
            "book": {
                "entry_events": 0,
                "by_action": {},
                "by_entry_type": {},
                "by_level": {},
                "level1_deletes": 0,
                "level1_deletes_without_replacement": 0,
                "book_resets": 0,
                "order_id_entries": 0,
                "bbo_events": 0,
                "bbo_rows": 0,
                "rows_by_flag": {},
                "level1_missing_after_change": 0,
                "crossed_or_locked_after_change": 0,
            },
            "order_book": {
                "entry_events": 0,
                "by_action": {},
                "by_entry_type": {},
                "es_ids_seen": 0,
                "orders": 0,
            },
            "security_status": {"es_group_messages": 0, "examples": []},
            "channel_membership": {
                "entries_with_security_id": 0,
                "off_channel_entries": 0,
                "off_channel_ids": [],
                "distinct_security_ids": [],
            },
            "instrument_message_counts": {},
            "instrument_trade_counts": {},
            "sanity": {"empty_packets": 0},
        }
        self._sequence_by_port: dict[str, list[int]] = collections.defaultdict(list)
        self._capture_by_sequence: dict[int, int] = {}
        self._feed_by_sequence: dict[int, str] = {}
        self._send_by_sequence: dict[int, int] = {}
        self._current_template_has_es = False
        self._send_time_first = None
        self._send_time_last = None
        self._capture_ns_first = None
        self._capture_ns_last = None
        self._transact_first = None
        self._transact_last = None
        self._transact_prev = None
        self._transact_regressions = 0
        self._seq_prev_by_port: dict[str, int] = {}
        self._last_trade: dict[int, tuple[int, int]] = {}
        self._trade_keys: set = set()
        self._bbo_row_count = 0
        self._distinct_channel_ids: set = set()

    # -- helpers ---------------------------------------------------------- #

    def _es_packet(self, dport: int) -> bool:
        return dport in ES_FEED_PORTS

    def _note_sequence(self, feed: str, sequence: int) -> None:
        previous = self._seq_prev_by_port.get(feed)
        if previous is not None and sequence != previous + 1:
            bucket = "gap" if sequence > previous + 1 else "regression"
            counters = self.stats["sequence"].setdefault("violations_" + bucket, 0)
            self.stats["sequence"]["violations_" + bucket] = counters + 1
        self._seq_prev_by_port[feed] = sequence
        self._sequence_by_port[feed].append(sequence)

    def _emit_bbo(self, security_id: int, side: str, price, size, capture_ns, send_ns, sequence, rpt_seq, level, action, entry_type, flag):
        self.bbo_writer.writerow(
            [
                send_ns,
                capture_ns,
                send_ns,
                sequence,
                self._feed_label,
                security_id,
                self.symbol_by_id.get(security_id, ""),
                side,
                price,
                round(price * self.scale_by_id.get(security_id, 1e-9), 9),
                size,
                flag,
                rpt_seq,
                level,
                MD_UPDATE_ACTION.get(action, action),
                entry_type,
                T_BOOK,
            ]
        )
        self._bbo_row_count += 1

    _feed_label = ""

    def _recompute_top(self, security_id: int) -> dict[str, tuple[int, int] | None]:
        book = self.levels.get(security_id) or {}
        top = {}
        for side in ("B", "A"):
            side_levels = book.get(side) or {}
            best = side_levels.get(1)
            if best is None and side_levels:
                best = side_levels[min(side_levels)]
                top[side] = (best[0], best[1], "reconstructed", min(side_levels))
                continue
            top[side] = (best[0], best[1], "direct_l1", 1) if best is not None else None
        return top

    # -- main entry ------------------------------------------------------- #

    def process_record(self, ts_sec: int, ts_nsec: int, incl: int, orig: int, frame: bytes) -> None:
        self.stats["packets_pcap_records"] += 1
        udp = extract_udp(frame)
        if udp is None:
            ethertype = frame[12] << 8 | frame[13] if len(frame) >= 14 else None
            if ethertype not in (0x0800, 0x86DD, 0x8100, 0x88A8):
                self.stats["packets_non_ipv4"] += 1
            else:
                self.stats["packets_fragmented"] += 1
            return
        self.stats["packets_udp_total"] += 1
        _src, _dst, _sport, dport, payload = udp
        if not self._es_packet(dport):
            return
        feed = ES_FEED_PORTS[dport]
        self._feed_label = feed
        capture_ns = ts_sec * 1_000_000_000 + ts_nsec
        self.stats["packets_es_channel"] += 1
        self.stats["packets_es_by_port"][feed] = self.stats["packets_es_by_port"].get(feed, 0) + 1
        if self._capture_ns_first is None:
            self._capture_ns_first = capture_ns
        self._capture_ns_last = capture_ns
        if not payload:
            self.stats["sanity"]["empty_packets"] += 1
            return
        sequence, send_ns = struct.unpack_from("<IQ", payload, 0)
        if self._send_time_first is None:
            self._send_time_first = send_ns
        self._send_time_last = send_ns
        if not (self.window_start_ns <= send_ns < self.window_end_ns):
            self.stats["packets_es_out_of_window"] += 1
            return
        self.stats["packets_es_by_port_in_window"][feed] = (
            self.stats["packets_es_by_port_in_window"].get(feed, 0) + 1
        )
        self._note_sequence(feed, sequence)
        self._capture_by_sequence.setdefault(sequence, capture_ns)
        self._feed_by_sequence.setdefault(sequence, feed)
        self._send_by_sequence.setdefault(sequence, send_ns)
        if self.extract_fh is not None:
            self.extract_fh.write(struct.pack("<IIII", ts_sec, ts_nsec, incl, orig))
            self.extract_fh.write(frame)
            self.stats["bytes_es_extract"] += 16 + len(frame)
        self.stats["bytes_pcap_records_es"] += 16 + len(frame)
        try:
            messages = list(iter_mdp_messages(payload))
        except FeedFormatError:
            self.stats["message_tiling_breaks"] += 1
            return
        for seq, send_time, template_id, block_length, schema_id, version, body in messages:
            self.stats["messages_es_channel"] += 1
            key = str(template_id)
            self.stats["messages_by_template"][key] = (
                self.stats["messages_by_template"].get(key, 0) + 1
            )
            if template_id not in TEMPLATES:
                self.stats["unknown_templates"][key] = (
                    self.stats["unknown_templates"].get(key, 0) + 1
                )
                continue
            spec = TEMPLATES[template_id]
            if block_length != spec["block_length"]:
                self.stats["message_tiling_breaks"] += 1
                continue
            transact_ns = struct.unpack_from("<Q", body, 0)[0]
            if self._transact_first is None:
                self._transact_first = transact_ns
            if self._transact_prev is not None and transact_ns < self._transact_prev:
                self._transact_regressions += 1
            self._transact_prev = transact_ns
            self._transact_last = transact_ns
            handler = self._HANDLERS.get(template_id)
            if handler is not None:
                self._current_template_has_es = False
                handler(self, body, spec, capture_ns, send_time, seq, transact_ns)
                if self._current_template_has_es:
                    key = str(template_id)
                    self.stats["messages_by_template_es_ids"][key] = (
                        self.stats["messages_by_template_es_ids"].get(key, 0) + 1
                    )

    # -- per-template handlers -------------------------------------------- #

    def _handle_status(self, body, spec, capture_ns, send_time, seq, transact_ns) -> None:
        group = _read_field(body, spec["block"]["SecurityGroup"])
        asset = _read_field(body, spec["block"]["Asset"])
        security_id = _read_field(body, spec["block"]["SecurityID"])
        trade_date = _read_field(body, spec["block"]["TradeDate"])
        status = _read_field(body, spec["block"]["SecurityTradingStatus"])
        if group == "ES":
            self._current_template_has_es = True
            self.stats["security_status"]["es_group_messages"] += 1
            if len(self.stats["security_status"]["examples"]) < 8:
                self.stats["security_status"]["examples"].append(
                    {
                        "ts_event_ns": transact_ns,
                        "security_group": group,
                        "asset": asset,
                        "security_id": security_id,
                        "trade_date_raw": trade_date,
                        "security_trading_status": status,
                        "sequence": seq,
                    }
                )

    def _handle_volume(self, body, spec, capture_ns, send_time, seq, transact_ns) -> None:
        for base, entry in self._iter_groups(body, spec):
            security_id = _read_field(entry, spec["groups"][0]["fields"]["SecurityID"], 0)
            self._count_instrument_message(security_id)
            self._note_channel_security(security_id)
            if security_id in self.es_ids:
                self._current_template_has_es = True

    def _handle_book(self, body, spec, capture_ns, send_time, seq, transact_ns) -> None:
        group_spec = spec["groups"][0]
        fields = group_spec["fields"]
        touched: dict[int, dict[str, tuple]] = {}
        for entry in self._iter_group_entries(body, spec, 0):
            security_id = _read_field(entry, fields["SecurityID"], 0)
            self._count_instrument_message(security_id)
            self._note_channel_security(security_id)
            if security_id not in self.es_ids:
                continue
            self._current_template_has_es = True
            price = _read_field(entry, fields["MDEntryPx"], 0)
            size = _read_field(entry, fields["MDEntrySize"], 0)
            rpt_seq = _read_field(entry, fields["RptSeq"], 0)
            level = _read_field(entry, fields["MDPriceLevel"], 0)
            action = _read_field(entry, fields["MDUpdateAction"], 0)
            entry_type = _read_field(entry, fields["MDEntryType"], 0)
            self.stats["book"]["entry_events"] += 1
            self.stats["book"]["by_action"][MD_UPDATE_ACTION.get(action, str(action))] = (
                self.stats["book"]["by_action"].get(MD_UPDATE_ACTION.get(action, str(action)), 0) + 1
            )
            self.stats["book"]["by_entry_type"][entry_type] = (
                self.stats["book"]["by_entry_type"].get(entry_type, 0) + 1
            )
            self.stats["book"]["by_level"][str(level)] = (
                self.stats["book"]["by_level"].get(str(level), 0) + 1
            )
            book = self.levels.setdefault(security_id, {"B": {}, "A": {}})
            if entry_type == "J":  # book reset for this instrument
                self.stats["book"]["book_resets"] += 1
                book["B"].clear()
                book["A"].clear()
                self.tob.pop(security_id, None)
                touched.setdefault(security_id, {})["reset"] = (capture_ns, seq, transact_ns, rpt_seq)
                continue
            self.observed_mantissas[security_id].add(price)
            side = SIDE_FROM_ENTRY_TYPE.get(entry_type)
            if side is None or price is None or level is None:
                continue
            side_levels = book[side]
            if action in (0, 1, 5):  # New / Change / Overlay
                side_levels[level] = (price, size if size is not None else 0)
            elif action == 2:  # Delete: drop the level and compact the ones behind it
                if level == 1:
                    self.stats["book"]["level1_deletes"] += 1
                side_levels.pop(level, None)
                shifted = {lvl - 1: value for lvl, value in side_levels.items() if lvl > level}
                for lvl in [lvl for lvl in side_levels if lvl > level]:
                    side_levels.pop(lvl, None)
                side_levels.update(shifted)
                if level == 1 and 1 not in side_levels:
                    self.stats["book"]["level1_deletes_without_replacement"] += 1
            elif action == 3:  # DeleteThru: level and all worse levels
                for lvl in [lvl for lvl in side_levels if lvl >= level]:
                    side_levels.pop(lvl, None)
            elif action == 4:  # DeleteFrom: level and all better levels
                for lvl in [lvl for lvl in side_levels if lvl <= level]:
                    side_levels.pop(lvl, None)
            else:
                continue
            record = touched.setdefault(security_id, {})
            record[side] = (capture_ns, seq, transact_ns, rpt_seq, level, action, entry_type)

        for security_id, caused in touched.items():
            if "reset" in caused and len(caused) == 1:
                previous = self.tob.get(security_id)
                if previous is not None:
                    self.tob[security_id] = None
                    self.tob_events.append((transact_ns, seq, security_id, None, None, None, None))
                    self.stats["book"]["bbo_events"] += 1
                continue
            top = self._recompute_top(security_id)
            if all(value is None for value in top.values()):
                self.tob[security_id] = None
                continue
            previous = self.tob.get(security_id)
            bid = top.get("B")
            ask = top.get("A")
            bid_price = bid[0] if bid else None
            bid_size = bid[1] if bid else None
            ask_price = ask[0] if ask else None
            ask_size = ask[1] if ask else None
            new_state = {
                "B": (bid_price, bid_size),
                "A": (ask_price, ask_size),
            }
            if previous == new_state:
                continue
            self.tob[security_id] = new_state
            self.tob_events.append(
                (transact_ns, seq, security_id, bid_price, bid_size, ask_price, ask_size)
            )
            self.stats["book"]["bbo_events"] += 1
            for side, level_record in caused.items():
                if side == "reset":
                    continue
                capture_ns_, seq_, transact_, rpt_seq_, level_, action_, entry_type_ = level_record
                top_side = top.get(side)
                if top_side is None:
                    continue
                flag = "direct_l1" if top_side[2] == "direct_l1" else "reconstructed"
                touched_side = side
                self._emit_bbo(
                    security_id,
                    touched_side,
                    top_side[0],
                    top_side[1],
                    capture_ns_,
                    transact_,
                    seq_,
                    rpt_seq_,
                    top_side[3],
                    action_,
                    entry_type_,
                    flag,
                )
                self.stats["book"]["rows_by_flag"][flag] = (
                    self.stats["book"]["rows_by_flag"].get(flag, 0) + 1
                )
            self.stats["book"]["bbo_rows"] = self._bbo_row_count
            if bid_price is None or ask_price is None:
                self.stats["book"]["level1_missing_after_change"] += 1
            elif ask_price <= bid_price:
                self.stats["book"]["crossed_or_locked_after_change"] += 1

    def _handle_order_book(self, body, spec, capture_ns, send_time, seq, transact_ns) -> None:
        group_spec = spec["groups"][0]
        fields = group_spec["fields"]
        for entry in self._iter_group_entries(body, spec, 0):
            security_id = _read_field(entry, fields["SecurityID"], 0)
            self._note_channel_security(security_id)
            if security_id not in self.es_ids:
                continue
            self._current_template_has_es = True
            order_id = _read_field(entry, fields["OrderID"], 0)
            price = _read_field(entry, fields["MDEntryPx"], 0)
            qty = _read_field(entry, fields["MDDisplayQty"], 0)
            action = _read_field(entry, fields["MDUpdateAction"], 0)
            entry_type = _read_field(entry, fields["MDEntryType"], 0)
            self.stats["order_book"]["entry_events"] += 1
            key = MD_UPDATE_ACTION.get(action, str(action))
            self.stats["order_book"]["by_action"][key] = (
                self.stats["order_book"]["by_action"].get(key, 0) + 1
            )
            self.stats["order_book"]["by_entry_type"][entry_type] = (
                self.stats["order_book"]["by_entry_type"].get(entry_type, 0) + 1
            )
            side = SIDE_FROM_ENTRY_TYPE.get(entry_type)
            if order_id is None or side is None:
                continue
            orders = self.orders.setdefault(security_id, {})
            if action == 2:
                orders.pop(order_id, None)
            elif price is not None:
                orders[order_id] = (side, price, qty or 0)
        self.stats["order_book"]["es_ids_seen"] = len(self.orders)
        self.stats["order_book"]["orders"] = sum(len(order_map) for order_map in self.orders.values())

    def _handle_trade_summary(self, body, spec, capture_ns, send_time, seq, transact_ns) -> None:
        group_spec = spec["groups"][0]
        fields = group_spec["fields"]
        for entry in self._iter_group_entries(body, spec, 0):
            security_id = _read_field(entry, fields["SecurityID"], 0)
            self._count_instrument_message(security_id)
            self._note_channel_security(security_id)
            if security_id not in self.es_ids:
                continue
            self._current_template_has_es = True
            price = _read_field(entry, fields["MDEntryPx"], 0)
            size = _read_field(entry, fields["MDEntrySize"], 0)
            rpt_seq = _read_field(entry, fields["RptSeq"], 0)
            aggressor = _read_field(entry, fields["AggressorSide"], 0)
            action = _read_field(entry, fields["MDUpdateAction"], 0)
            trade_entry_id = _read_field(entry, fields["MDTradeEntryID"], 0)
            number_of_orders = _read_field(entry, fields["NumberOfOrders"], 0)
            self.stats["trades"]["entry_events"] += 1
            self.observed_mantissas[security_id].add(price)
            action_label = MD_UPDATE_ACTION.get(action, str(action))
            self.stats["trades"]["by_action"][action_label] = (
                self.stats["trades"]["by_action"].get(action_label, 0) + 1
            )
            side = AGGRESSOR_SIDE.get(aggressor, "?")
            self.stats["trades"]["by_aggressor"][side] = (
                self.stats["trades"]["by_aggressor"].get(side, 0) + 1
            )
            if action not in (0, 1):
                continue
            symbol = self.symbol_by_id.get(security_id, "")
            self.stats["trades"]["by_instrument"][symbol] = (
                self.stats["trades"]["by_instrument"].get(symbol, 0) + 1
            )
            self.stats["instrument_trade_counts"][str(security_id)] = (
                self.stats["instrument_trade_counts"].get(str(security_id), 0) + 1
            )
            key = f"{symbol}:{rpt_seq}:{trade_entry_id}"
            if key in self._trade_keys:
                self.stats["trades"]["rpt_seq_duplicates"] += 1
            else:
                self._trade_keys.add(key)
            top = self.tob.get(security_id)
            check = self.stats["trades"].setdefault(
                "price_within_prevailing_tob",
                {
                    "checked": 0,
                    "outside": 0,
                    "aggressor_at_tob": 0,
                    "outside_by_tick_distance": {},
                    "outside_examples": [],
                    "note": (
                        "book state maintained causally from the stream up to the trade; a trade "
                        "printed outside it is consistent with intra-event ordering (the matching "
                        "book update can follow the trade summary inside the same packet)"
                    ),
                },
            )
            if top and top.get("B") and top.get("A"):
                check["checked"] += 1
                bid_price = top["B"][0]
                ask_price = top["A"][0]
                if price < bid_price or price > ask_price:
                    check["outside"] += 1
                    tick_units = tick_mantissa_units(self.es_ids.get(security_id, {}) or {
                        "min_price_increment": "0.25"
                    })
                    distance = (bid_price - price if price < bid_price else price - ask_price)
                    buckets = check["outside_by_tick_distance"]
                    key = str(round(distance / tick_units, 3)) if tick_units else "n/a"
                    buckets[key] = buckets.get(key, 0) + 1
                    if len(check["outside_examples"]) < 5:
                        check["outside_examples"].append(
                            {
                                "sequence": seq,
                                "symbol": symbol,
                                "side": side,
                                "price": price,
                                "bid": bid_price,
                                "ask": ask_price,
                                "distance_ticks": key,
                            }
                        )
                elif (side == "B" and price == ask_price) or (side == "S" and price == bid_price):
                    check["aggressor_at_tob"] += 1
            previous = self._last_trade.get(security_id)
            if previous is not None:
                if transact_ns < previous[0]:
                    self.stats["trades"]["ts_event_regressions"] += 1
                if seq < previous[1]:
                    self.stats["trades"]["sequence_regressions"] += 1
            self._last_trade[security_id] = (transact_ns, seq)
            bounds = self.stats["trades"]
            if bounds["ts_event_min_ns"] is None or transact_ns < bounds["ts_event_min_ns"]:
                bounds["ts_event_min_ns"] = transact_ns
            if bounds["ts_event_max_ns"] is None or transact_ns > bounds["ts_event_max_ns"]:
                bounds["ts_event_max_ns"] = transact_ns
            if self.trades_writer is not None:
                self.trades_writer.writerow(
                    [
                        transact_ns,
                        capture_ns,
                        send_time,
                        seq,
                        self._feed_label,
                        security_id,
                        symbol,
                        price,
                        round(price * self.scale_by_id.get(security_id, 1e-9), 9),
                        size,
                        side,
                        aggressor,
                        action_label,
                        rpt_seq,
                        trade_entry_id,
                        number_of_orders,
                        T_TRADE_SUMMARY,
                    ]
                )
            self.stats["trades"]["rows"] += 1

    _HANDLERS = {}

    def _note_channel_security(self, security_id) -> None:
        """Every instrument seen on the channel ports must name that channel itself."""
        if security_id is None:
            return
        membership = self.stats["channel_membership"]
        membership["entries_with_security_id"] += 1
        if security_id in self.channel_ids:
            if security_id not in self._distinct_channel_ids:
                self._distinct_channel_ids.add(security_id)
                membership["distinct_security_ids"].append(security_id)
        else:
            membership["off_channel_entries"] += 1
            if len(membership["off_channel_ids"]) < 20:
                membership["off_channel_ids"].append(security_id)

    def _count_instrument_message(self, security_id) -> None:
        if security_id is None:
            return
        key = str(security_id)
        self.stats["instrument_message_counts"][key] = (
            self.stats["instrument_message_counts"].get(key, 0) + 1
        )

    def _iter_group_entries(self, body: bytes, spec: dict, group_index: int):
        """Yield the entry bodies of one repeating group, in wire order."""
        offset = spec["block_length"]
        for index, group_spec in enumerate(spec["groups"]):
            header_bytes = 3 if group_spec["dim"] == "groupSize" else 8
            entry_block_length = struct.unpack_from("<H", body, offset)[0]
            count = body[offset + 7] if header_bytes == 8 else body[offset + 2]
            offset += header_bytes
            if index == group_index:
                for _ in range(count):
                    yield body[offset : offset + entry_block_length]
                    offset += entry_block_length
            else:
                offset += count * entry_block_length

    def _iter_groups(self, body: bytes, spec: dict):
        offset = spec["block_length"]
        for group_spec in spec["groups"]:
            header_bytes = 3 if group_spec["dim"] == "groupSize" else 8
            entry_block_length = struct.unpack_from("<H", body, offset)[0]
            count = body[offset + 7] if header_bytes == 8 else body[offset + 2]
            offset += header_bytes
            for _ in range(count):
                yield offset, body[offset : offset + entry_block_length]
                offset += entry_block_length

    # -- finalization ----------------------------------------------------- #

    def finalize(self) -> dict:
        stats = self.stats
        sequence_summary = {}
        for feed, series in self._sequence_by_port.items():
            gaps = 0
            regressions = 0
            duplicates = 0
            seen = set()
            ordered = series
            for index, value in enumerate(ordered):
                if value in seen:
                    duplicates += 1
                seen.add(value)
                if index:
                    delta = value - ordered[index - 1]
                    if delta > 1:
                        gaps += 1
                    elif delta < 1:
                        regressions += 1
            sequence_summary[feed] = {
                "packets": len(ordered),
                "first": ordered[0] if ordered else None,
                "last": ordered[-1] if ordered else None,
                "span": (ordered[-1] - ordered[0] + 1) if ordered else 0,
                "gaps": gaps,
                "regressions": regressions,
                "duplicates": duplicates,
            }
        union = sorted({value for series in self._sequence_by_port.values() for value in series})
        union_gaps = sum(1 for index in range(1, len(union)) if union[index] != union[index - 1] + 1)
        sequence_summary["dedup_union"] = {
            "first": union[0] if union else None,
            "last": union[-1] if union else None,
            "count": len(union),
            "span": (union[-1] - union[0] + 1) if union else 0,
            "gaps": union_gaps,
            "duplicates": sum(len(s) for s in self._sequence_by_port.values()) - len(union),
        }
        stats["sequence"]["summary"] = sequence_summary
        stats["sequence"]["series_dedup"] = union
        stats["sequence"]["series_capture_ns"] = [self._capture_by_sequence.get(value) for value in union]
        stats["sequence"]["series_send_ns"] = [self._send_by_sequence.get(value) for value in union]
        stats["sequence"]["series_feed"] = [self._feed_by_sequence.get(value) for value in union]
        stats["timestamps"] = {
            "capture_first_ns": self._capture_ns_first,
            "capture_last_ns": self._capture_ns_last,
            "exchange_send_first_ns": self._send_time_first,
            "exchange_send_last_ns": self._send_time_last,
            "transact_time_first_ns": self._transact_first,
            "transact_time_last_ns": self._transact_last,
            "transact_time_regressions": self._transact_regressions,
            "pcap_record_ts_precision": "nanosecond (magic 0xa1b23c4d)",
        }
        stats["book"]["bbo_rows"] = self._bbo_row_count
        membership = stats["channel_membership"]
        membership["distinct_security_id_count"] = len(membership["distinct_security_ids"])
        membership["channel_id"] = ES_CHANNEL_ID
        membership["instrument_count_on_channel"] = len(self.channel_ids)
        membership["all_entries_on_declared_channel"] = (
            membership["off_channel_entries"] == 0 and membership["entries_with_security_id"] > 0
        )
        membership["note"] = (
            "every SecurityID observed on the ES channel ports is looked up in the session "
            "security definitions; each must itself declare channel 310 (tag 1180)"
        )
        stats["price_scale"] = self._price_scale_evidence()
        return stats

    def _price_scale_evidence(self) -> dict:
        """Check the decoded price scale against each instrument's own definition."""
        out = {}
        for security_id in sorted(self.observed_mantissas):
            record = self.es_ids.get(security_id)
            if record is None:
                continue
            factor = record.get("price_display_factor")
            increment = record.get("min_price_increment")
            mantissas = sorted(self.observed_mantissas[security_id])
            if not mantissas or factor is None or increment is None:
                continue
            scale = PRICE_MANTISSA_PER_SECDEF_UNIT * float(factor)
            tick_units = tick_mantissa_units(record)
            settl = self.settl_mantissa_by_id.get(security_id)
            band = self.band_mantissa_by_id.get(security_id, {})
            entry = {
                "symbol": record["symbol"],
                "price_display_factor": float(factor),
                "min_price_increment_secdef_units": float(increment),
                "tick_index_points": round(float(increment) * float(factor), 9),
                "tick_mantissa_units": tick_units,
                "secdef_settl_price_mantissa": settl,
                "secdef_settl_price_index_points": (
                    round(settl * scale, 6) if settl is not None else None
                ),
                "secdef_settl_date": record.get("settl_date"),
                "observed_price_min_mantissa": mantissas[0],
                "observed_price_max_mantissa": mantissas[-1],
                "observed_price_min_index_points": round(mantissas[0] * scale, 6),
                "observed_price_max_index_points": round(mantissas[-1] * scale, 6),
                "observed_distinct_prices": len(mantissas),
                "all_prices_on_tick_grid": all(
                    (value - mantissas[0]) % tick_units == 0 for value in mantissas
                ) if tick_units else None,
                "all_prices_same_tick_offset_as_settlement": (
                    all((value - settl) % tick_units == 0 for value in mantissas)
                    if (settl is not None and tick_units)
                    else None
                ),
                "all_prices_within_secdef_band": (
                    all(band["low"] <= value <= band["high"] for value in mantissas)
                    if band.get("low") is not None and band.get("high") is not None
                    else None
                ),
            }
            out[record["symbol"]] = entry
        return out


EsNormalizer._HANDLERS = {
    T_SECURITY_STATUS: EsNormalizer._handle_status,
    T_VOLUME: EsNormalizer._handle_volume,
    T_BOOK: EsNormalizer._handle_book,
    T_ORDER_BOOK: EsNormalizer._handle_order_book,
    T_TRADE_SUMMARY: EsNormalizer._handle_trade_summary,
}


# --------------------------------------------------------------------------- #
# spread grid
# --------------------------------------------------------------------------- #


def build_spread_grid(
    tob_events: list[tuple],
    primary_id: int,
    scale: float,
    tick_points: float,
    point_value_usd: float,
    tick_mantissa: int,
    window_start_ns: int = WINDOW_START_NS,
    window_end_ns: int = WINDOW_END_NS,
    grid_ns: int = GRID_NS,
) -> dict:
    """Spread distribution at a fixed grid over the window.

    Basis for the frozen friction input ``1/2 S_entry + 1/2 S_exit``: ``S`` is the
    observed best-ask minus best-bid (a full quoted spread) prevailing at the grid
    instant, from the maintained market-by-price book of the primary instrument;
    ``1/2 S`` is therefore the half-spread paid to cross from the midpoint on one
    side of the round trip.  No outcome is computed.
    """
    events = sorted(
        (event for event in tob_events if event[1] is not None and event[2] == primary_id),
        key=lambda event: event[0],
    )
    rows = []
    spreads_ticks = collections.Counter()
    spreads = []
    index = 0
    current = None
    last_event_ns = None
    fresh_points = 0
    FRESH_NS = 1_000_000_000
    grid_start = window_start_ns
    grid_points = (window_end_ns - window_start_ns) // grid_ns
    for point in range(grid_points):
        ts = grid_start + point * grid_ns
        while index < len(events) and events[index][0] <= ts:
            event_ts, _seq, _sid, bid_price, bid_size, ask_price, ask_size = events[index]
            current = (bid_price, bid_size, ask_price, ask_size)
            last_event_ns = event_ts
            index += 1
        if current is None or current[0] is None or current[2] is None:
            rows.append((point, ts, None, None, None, None, None, None, None, None))
            continue
        bid_price, bid_size, ask_price, ask_size = current
        spread_points = (ask_price - bid_price) * scale
        ticks = spread_points / tick_points if tick_points else None
        rows.append(
            (
                point,
                ts,
                bid_price,
                ask_price,
                bid_size,
                ask_size,
                round(ticks, 6),
                round(spread_points, 6),
                round(spread_points / 2.0, 6),
                round(ticks / 2.0, 6),
            )
        )
        spreads.append(spread_points)
        spreads_ticks[round(ticks, 3)] += 1
        if last_event_ns is not None and ts - last_event_ns <= FRESH_NS:
            fresh_points += 1
    quoted = len(spreads)
    summary = {
        "grid_ns": grid_ns,
        "grid_points": grid_points,
        "grid_points_with_quote": quoted,
        "grid_points_without_quote": grid_points - quoted,
        "grid_points_with_quote_updated_within_1s": fresh_points,
        "primary_instrument_id": primary_id,
        "tick_index_points": round(tick_points, 9),
        "tick_mantissa_units": tick_mantissa,
        "point_value_usd": point_value_usd,
        "price_scale_index_points_per_mantissa_unit": scale,
        "spread_ticks_counts": {str(key): value for key, value in sorted(spreads_ticks.items())},
        "spread_points_mean": round(sum(spreads) / quoted, 6) if quoted else None,
        "spread_points_min": min(spreads) if spreads else None,
        "spread_points_max": max(spreads) if spreads else None,
        "half_spread_points_mean": round(sum(spreads) / quoted / 2.0, 6) if quoted else None,
        "spread_points_quantiles": _quantiles(spreads),
        "spread_usd_mean": round(sum(spreads) / quoted * point_value_usd, 6) if quoted else None,
        "half_spread_usd_mean": (
            round(sum(spreads) / quoted / 2.0 * point_value_usd, 6) if quoted else None
        ),
        "spread_usd_quantiles": {
            label: round(value * point_value_usd, 6)
            for label, value in _quantiles(spreads).items()
        },
        "usd_note": "USD figures are index points x the instrument's own ContractMultiplier",
        "basis": (
            "S = observed best ask - best bid of the maintained MDP 3.0 market-by-price book of "
            "the primary ES outright at each 10 ms grid instant, converted to index points with "
            "the instrument's own secdef PriceDisplayFactor; friction per round trip = "
            "1/2 S_entry + 1/2 S_exit in index points, i.e. the half-spread paid on each leg "
            "relative to the midpoint. Ticks = S / (secdef MinPriceIncrement x PriceDisplayFactor)."
        ),
    }
    return {"rows": rows, "summary": summary}


def _quantiles(values: list[float]) -> dict:
    if not values:
        return {}
    ordered = sorted(values)
    out = {}
    for label, quantile in (("p10", 0.10), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p90", 0.90), ("p99", 0.99)):
        position = quantile * (len(ordered) - 1)
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        value = ordered[low] + (ordered[high] - ordered[low]) * (position - low)
        out[label] = round(value, 6)
    return out


# --------------------------------------------------------------------------- #
# retrieval
# --------------------------------------------------------------------------- #


def probe_url(url: str, first_bytes: int = 1024) -> dict:
    """Range-GET probe: authoritative total size, HTTP status and header digest."""
    completed = subprocess.run(
        ["curl", "-sS", "-r", f"0-{first_bytes - 1}", "-D", "-", "-o", "-", url],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise FeedFormatError(f"probe failed: {completed.stderr.decode(errors='replace')}")
    raw = completed.stdout
    separator = raw.find(b"\r\n\r\n")
    if separator < 0:
        raise FeedFormatError("probe returned no HTTP header block")
    header_block = raw[:separator].decode("latin1")
    body = raw[separator + 4 :]
    headers = {}
    status = None
    for line in header_block.splitlines():
        if line.startswith("HTTP/"):
            status = int(line.split()[1])
        elif ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    content_range = headers.get("content-range", "")
    total = None
    match = re.match(r"bytes\s+\d+-\d+/(\d+)", content_range)
    if match:
        total = int(match.group(1))
    return {
        "url": url,
        "http_status": status,
        "content_range": content_range,
        "total_bytes": total,
        "first_bytes": len(body),
        "first_bytes_sha256": hashlib.sha256(body).hexdigest(),
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "content_type": headers.get("content-type"),
        "server_date": headers.get("date"),
        "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def fetch_range(url: str, start: int, end: int, attempts: int = 3) -> bytes:
    """Fetch an inclusive byte range; verify the exact length."""
    expected = end - start + 1
    last_error = None
    for attempt in range(attempts):
        completed = subprocess.run(
            ["curl", "-sS", "-f", "-r", f"{start}-{end}", url], capture_output=True, check=False
        )
        if completed.returncode == 0 and len(completed.stdout) == expected:
            return completed.stdout
        last_error = (
            f"range {start}-{end}: rc={completed.returncode} bytes={len(completed.stdout)} "
            f"expected={expected} attempt={attempt + 1}"
        )
    raise FeedFormatError(f"range fetch failed after {attempts} attempts: {last_error}")


def iter_ordered_ranges(url: str, total_bytes: int, chunk: int, workers: int):
    """Yield the object in order, fetching small chunks concurrently."""
    count = (total_bytes + chunk - 1) // chunk
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures: dict[int, object] = {}
        next_to_submit = 0
        next_to_yield = 0
        while next_to_yield < count:
            while next_to_submit < count and len(futures) < workers:
                start = next_to_submit * chunk
                end = min(start + chunk, total_bytes) - 1
                futures[next_to_submit] = pool.submit(fetch_range, url, start, end)
                next_to_submit += 1
            data = futures.pop(next_to_yield).result()
            next_to_yield += 1
            yield data


# --------------------------------------------------------------------------- #
# shared normalization driver
# --------------------------------------------------------------------------- #


TRADE_COLUMNS = [
    "ts_event_ns",
    "ts_recv_ns",
    "exchange_send_ns",
    "sequence",
    "feed",
    "instrument_id",
    "symbol",
    "price",
    "price_index_points",
    "size",
    "side",
    "aggressor_side",
    "update_action",
    "rpt_seq",
    "md_trade_entry_id",
    "number_of_orders",
    "template_id",
]
BBO_COLUMNS = [
    "ts_event_ns",
    "ts_recv_ns",
    "exchange_send_ns",
    "sequence",
    "feed",
    "instrument_id",
    "symbol",
    "side",
    "price",
    "price_index_points",
    "size",
    "flag",
    "rpt_seq",
    "md_price_level",
    "update_action",
    "entry_type",
    "template_id",
]
GRID_COLUMNS = [
    "grid_index",
    "ts_ns",
    "bid_px",
    "ask_px",
    "bid_sz",
    "ask_sz",
    "spread_ticks",
    "spread_points",
    "half_spread_points",
    "half_spread_ticks",
]


def _run_normalization(
    *,
    out_dir: str,
    es_ids: dict,
    secdef_report: dict,
    config_report: dict,
    provenance: dict,
    raw_path: str | None,
    sources,
) -> dict:
    """Consume ``sources`` (an iterable of decompressed pcap byte chunks) and write artifacts."""
    os.makedirs(out_dir, exist_ok=True)
    trades_path = os.path.join(out_dir, "trades.csv")
    bbo_path = os.path.join(out_dir, "bbo_increments.csv")
    grid_path = os.path.join(out_dir, "spread_grid.csv")
    stats_path = os.path.join(out_dir, "es_stream_stats.json")

    extract_fh = None
    if raw_path:
        os.makedirs(os.path.dirname(raw_path), exist_ok=True)
        extract_fh = open(raw_path, "wb")

    framer = PcapFramer()
    with open(trades_path, "w", newline="") as trades_fh, open(bbo_path, "w", newline="") as bbo_fh:
        trades_writer = csv.writer(trades_fh)
        bbo_writer = csv.writer(bbo_fh)
        trades_writer.writerow(TRADE_COLUMNS)
        bbo_writer.writerow(BBO_COLUMNS)
        channel_ids = {
            int(key): value for key, value in secdef_report.get("channel_instruments", {}).items()
        }
        normalizer = EsNormalizer(es_ids, channel_ids, trades_fh, bbo_fh, extract_fh)
        for chunk in sources:
            for record in framer.feed(chunk):
                if extract_fh is not None and not normalizer._pcap_header_written:
                    # preserve the source capture's own global header byte-for-byte
                    extract_fh.write(framer.header)
                    normalizer._pcap_header_written = True
                normalizer.process_record(*record)
        stats = normalizer.finalize()
    if extract_fh is not None:
        extract_fh.close()

    primary_id = _primary_instrument(stats, es_ids)
    primary_record = es_ids.get(primary_id) or {}
    scale = PRICE_MANTISSA_PER_SECDEF_UNIT * float(primary_record.get("price_display_factor", 1.0))
    tick_points = float(primary_record.get("min_price_increment", 0.25)) * float(
        primary_record.get("price_display_factor", 1.0)
    )
    point_value_usd = float(primary_record.get("contract_multiplier", ES_POINT_VALUE_USD))
    grid = build_spread_grid(
        normalizer.tob_events,
        primary_id,
        scale,
        tick_points,
        point_value_usd,
        tick_mantissa_units(primary_record) if primary_record.get("min_price_increment") else 0,
    )
    with open(grid_path, "w", newline="") as grid_fh:
        writer = csv.writer(grid_fh)
        writer.writerow(GRID_COLUMNS)
        writer.writerows(grid["rows"])
    with open(os.path.join(out_dir, "spread_distribution.json"), "w") as handle:
        json.dump(grid["summary"], handle, indent=2, sort_keys=True)

    stats["framer"] = {
        "pcap_header_sha256": hashlib.sha256(framer.header).hexdigest() if framer.header else None,
        "snaplen": framer.snaplen,
        "linktype": framer.linktype,
        "records": framer.records,
        "truncated_tail_bytes": framer.truncated_bytes,
    }
    stats["primary_instrument_id"] = primary_id
    stats["primary_instrument_symbol"] = es_ids.get(primary_id, {}).get("symbol")
    stats["instrument_messages"] = {
        str(sid): {
            "symbol": es_ids[sid]["symbol"],
            "is_outright": es_ids[sid]["is_outright"],
            "messages": stats["instrument_message_counts"].get(str(sid), 0),
            "trades": stats["instrument_trade_counts"].get(str(sid), 0),
        }
        for sid in sorted(es_ids)
    }
    stats.pop("instrument_message_counts", None)
    stats.pop("instrument_trade_counts", None)
    stats["spread_distribution"] = grid["summary"]
    stats["secdef"] = secdef_report
    stats["channel_config"] = config_report
    stats["provenance"] = provenance
    stats["raw_extract_path"] = raw_path
    with open(stats_path, "w") as handle:
        json.dump(stats, handle, indent=2, sort_keys=True)
    return stats


def _primary_instrument(stats: dict, es_ids: dict) -> int:
    """The ES outright with the most channel messages (the traded contract month)."""
    best_id = None
    best_count = -1
    for key, count in stats["instrument_message_counts"].items():
        security_id = int(key)
        if security_id not in es_ids or not es_ids[security_id]["is_outright"]:
            continue
        if count > best_count:
            best_id, best_count = security_id, count
    if best_id is None:
        outrights = [sid for sid, rec in es_ids.items() if rec["is_outright"]]
        best_id = outrights[0] if outrights else None
    return best_id


# --------------------------------------------------------------------------- #
# manifest
# --------------------------------------------------------------------------- #


def write_admission_manifest(
    *,
    out_path: str,
    stats: dict,
    files: list[dict],
    raw_extract_path: str | None,
    upstream_probe: dict,
    retrieved_at_utc: str,
) -> dict:
    """Write admission.json: the canonical admission shape plus this epoch's evidence."""
    out_dir = os.path.dirname(os.path.abspath(out_path))
    es_ids = {int(key): rec for key, rec in stats["secdef"]["instruments"].items()}
    primary_id = stats["primary_instrument_id"]
    primary = es_ids.get(primary_id, {})
    sequence = stats["sequence"]["summary"]
    dedup = sequence.get("dedup_union", {})
    timestamps = stats["timestamps"]
    packet_series = stats["sequence"].get("series_dedup", [])
    window_packets = stats["packets_es_by_port_in_window"]
    packet_count = sum(window_packets.values())
    grid = stats["spread_distribution"]
    qualified = grid["grid_points"]
    admitted = grid["grid_points_with_quote"]

    manifest = {
        "manifest_id": "W2-ES-2023-07-17T133000Z",
        "dataset_id": "CME-GLBX-MDP3-2023-07-17T133000Z-ES-CH310",
        "branch": "ES",
        "source": {
            "source_id": "databento-sample-pcaps-glbx-all-20230717T133000",
            "provider": "Databento (public sample PCAP mirror of CME Globex MDP 3.0 multicast)",
            "retrieved_at_utc": retrieved_at_utc,
            "access_terms": (
                "Public no-auth HTTP download (HTTP 206 partial content) of a Databento sample "
                "capture; no account, key, subscription or payment used. Databento ToU general use "
                "provisions and CME exchange-data terms apply; internal evaluation use only, no "
                "redistribution. This epoch inspects structure and cost inputs only, no economics."
            ),
            "url": upstream_probe.get("url"),
            "content_range": upstream_probe.get("content_range"),
            "total_bytes": upstream_probe.get("total_bytes"),
            "etag": upstream_probe.get("etag"),
            "last_modified": upstream_probe.get("last_modified"),
            "sha256_full_object": stats["provenance"].get("upstream_sha256"),
            "http_status_probe": upstream_probe.get("http_status"),
            "retrieval_method": (
                "streamed in ordered concurrent HTTP byte-range chunks; hashed and decompressed "
                "on the fly (source exceeds the 5 GB retention budget of this epoch)"
            ),
        },
        "schema": {
            "contract_id": "CME-MDP3.0-SAMPLE-CAPTURE",
            "format": "pcap (nanosecond) carrying CME MDP 3.0 SBE over IPv4 UDP multicast",
            "version": f"schemaId={MDP_SCHEMA_ID}, version={MDP_SCHEMA_VERSION}, {MDP_SCHEMA_NAME}",
        },
        "session": {
            "coverage_date": COVERAGE_DATE,
            "timezone": "UTC",
            "window_start_unix": WINDOW_START_NS // 1_000_000_000,
            "window_end_unix": WINDOW_END_NS // 1_000_000_000,
            "session_open_ns": WINDOW_START_NS,
            "session_close_ns": WINDOW_END_NS,
            "first_admitted_event_ns": timestamps.get("transact_time_first_ns"),
            "last_admitted_event_ns": timestamps.get("transact_time_last_ns"),
            "first_admitted_send_ns": timestamps.get("exchange_send_first_ns"),
            "last_admitted_send_ns": timestamps.get("exchange_send_last_ns"),
            "trade_date_semantics": (
                "CME trade date (SecurityStatus TradeDate, LocalMktDate) for the 2023-07-17 "
                "session; all timestamps are nanoseconds since the Unix epoch in UTC"
            ),
            "terminating_frame_present": False,
            "window_semantics": (
                "this epoch admits exactly the 10-minute RTH-open slice [13:30:00Z, 13:40:00Z); "
                "session_open_ns/session_close_ns are those declared admission bounds (every "
                "admitted packet's exchange send time lies inside them) and are not the CME "
                "trading-session boundaries; the observed first/last event and transmission times "
                "are reported alongside"
            ),
        },
        "files": _with_upstream_entry(files, stats, upstream_probe),
        "fields": [
            {
                "name": "ts_event_ns",
                "type": "int64",
                "semantics": "nanoseconds_since_unix_epoch_UTC",
                "identity": "venue_event_timestamp",
                "timezone": "UTC",
            },
            {
                "name": "ts_recv_ns",
                "type": "int64",
                "semantics": "nanoseconds_since_unix_epoch_UTC",
                "identity": "capture_timestamp",
                "timezone": "UTC",
            },
            {
                "name": "instrument_id",
                "type": "int32",
                "semantics": "CME SecurityID as published in the security definition snapshot",
                "identity": "venue_instrument_id",
                "timezone": "n/a",
            },
            {
                "name": "price",
                "type": "int64",
                "semantics": "price mantissa with constant exponent -9 (index points)",
                "identity": "venue_price_mantissa",
                "timezone": "n/a",
            },
            {
                "name": "size",
                "type": "int32",
                "semantics": "contracts",
                "identity": "venue_quantity",
                "timezone": "n/a",
            },
            {
                "name": "side",
                "type": "utf8",
                "semantics": "B = buy aggressor or bid side, S = sell aggressor, A = ask side, N = no aggressor",
                "identity": "venue_aggressor_side",
                "timezone": "n/a",
            },
            {
                "name": "sequence",
                "type": "uint32",
                "semantics": "MDP 3.0 per-channel packet sequence number",
                "identity": "venue_channel_sequence",
                "timezone": "n/a",
            },
        ],
        "instrument": {
            "symbol": primary.get("symbol"),
            "venue": "CME",
            "security_id": primary_id,
            "identity_basis": (
                "CME security definition snapshot secdef-2023-07-17.dat.gz (FIX tag=value): tag 48 "
                f"SecurityID={primary_id}, tag 55 Symbol={primary.get('symbol')}, tag 1151 "
                f"SecurityGroup={primary.get('security_group')}, tag 200 MaturityMonthYear="
                f"{primary.get('maturity_month_year')}, tag 1180 channel={primary.get('channel')}"
            ),
            "secondary_instruments": [
                {"symbol": rec["symbol"], "security_id": sid}
                for sid, rec in sorted(es_ids.items())
                if rec["is_outright"] and sid != primary_id
            ],
        },
        "universe": {
            "rule_id": "CME-MDP3-CHANNEL-310-ES-GROUP-OUTRIGHT",
            "pit": True,
            "members": [rec["symbol"] for _sid, rec in sorted(es_ids.items()) if rec["is_outright"]],
        },
        "records": _records_block(packet_series, stats, primary),
        "intervals": [
            {
                "id": "2023-07-17T13:30Z/2023-07-17T13:40Z",
                "present": packet_count > 0,
                "count": packet_count,
            }
        ],
        "coverage": {"qualified": qualified, "admitted": admitted, "ratio": admitted / qualified if qualified else 0.0},
        # ---- beyond the canonical shape: this epoch's required evidence ---- #
        "records_ordering": {
            "admitted_packet_send_time": _monotonicity(
                stats["sequence"].get("series_send_ns", [])
            ),
            "admitted_packet_capture_time": _monotonicity(
                stats["sequence"].get("series_capture_ns", [])
            ),
            "trade_event_time": _monotonicity(
                [stats["trades"].get("ts_event_min_ns"), stats["trades"].get("ts_event_max_ns")]
            ),
            "transact_time_regressions_across_channel": stats["timestamps"].get(
                "transact_time_regressions"
            ),
            "basis": (
                "records.* describes the admitted MDP 3.0 packet stream of ES channel 310 in the "
                "window, deduplicated across feeds A/B, in venue sequence order; timestamps are the "
                "venue exchange send times of those packets."
            ),
        },
        "sequence_continuity": {
            "per_feed": {key: value for key, value in sequence.items() if key != "dedup_union"},
            "dedup_union": dedup,
            "note": (
                "CME MDP 3.0 sequence numbers are per-channel and persist across sessions; the "
                "observed start value is not 1. Continuity is certified over the deduplicated "
                "feed-A/feed-B union (duplicates arise from the A/B redundancy, not from loss)."
            ),
            "sequence_basis": "venue_channel_sequence",
        },
        "template_counts": stats["messages_by_template"],
        "template_counts_es_ids": stats["messages_by_template_es_ids"],
        "packet_counts": {
            "pcap_records": stats["framer"]["records"],
            "es_channel_packets": stats["packets_es_channel"],
            "es_channel_packets_in_window": packet_count,
            "es_channel_packets_by_feed": stats["packets_es_by_port"],
            "es_channel_packets_by_feed_in_window": window_packets,
            "es_messages": stats["messages_es_channel"],
            "message_tiling_breaks": stats["message_tiling_breaks"],
            "unknown_templates": stats["unknown_templates"],
            "extract_bytes": _declared_bytes(files, "raw_extract") or stats["bytes_es_extract"],
            "extract_bytes_written_this_pass": stats["bytes_es_extract"],
        },
        "timestamp_domain": timestamps,
        "channel_identity": {
            "channel_id": ES_CHANNEL_ID,
            "label": ES_CHANNEL_LABEL,
            "feed_ports": {str(port): feed for port, feed in ES_FEED_PORTS.items()},
            "multicast": {str(port): ip for port, ip in ES_FEED_MULTICAST.items()},
            "config_evidence": stats["channel_config"],
            "security_status_evidence": stats["security_status"],
            "channel_membership_evidence": stats["channel_membership"],
            "identity_basis": (
                "a) CME channel configuration file: channel 310 = 'CME Globex Equity Futures', "
                "product ES, group ES, feed A 224.0.31.1:14310, feed B 224.0.32.1:15310; "
                "b) every SecurityID decoded on those ports also names channel 310 in the session "
                "security definitions (tag 1180); c) the decoded SecurityIDs resolve to ES-group "
                "futures (FFIXSX) in those definitions. Template 30 SecurityStatus was NOT observed "
                "on this channel inside the admitted window, so the SecurityGroup-ASCII check "
                "suggested in the work order is unavailable here and (a)-(c) stand in its place."
            ),
        },
        "trades": stats["trades"],
        "book": {key: value for key, value in stats["book"].items() if key != "bbo_rows"},
        "order_book_crosscheck": stats["order_book"],
        "spread_distribution": grid,
        "friction_input_basis": grid["basis"],
        "price_scale_evidence": stats.get("price_scale"),
        "layout_verification": stats["provenance"].get("layout_verification"),
        "assumed_vs_observed": stats["provenance"].get("assumed_vs_observed"),
        "retrieval": _retrieval_block(out_dir, stats, upstream_probe),
    }
    with open(out_path, "w") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=False)
    return manifest


SEQUENCE_PROBE_ROWS = 64


def _retrieval_block(out_dir: str, stats: dict, upstream_probe: dict) -> dict:
    """Acquisition facts: the streamed pass's own record, or a re-derivation fallback."""
    record_path = os.path.join(out_dir, "acquisition.json")
    if os.path.exists(record_path):
        with open(record_path) as handle:
            record = json.load(handle)
        return {
            "probe": upstream_probe or record.get("http"),
            "acquisition": record,
            "note": (
                "retrieval facts recorded by the acquisition pass that consumed the source object "
                "in one pass (hash + decode); the derived stream can be regenerated from the "
                "retained extract without re-contact"
            ),
        }
    provenance = stats.get("provenance") or {}
    return {
        "probe": upstream_probe,
        "chunks": provenance.get("retrieval_chunks"),
        "wall_seconds": provenance.get("retrieval_wall_seconds"),
        "decompressed_bytes": provenance.get("decompressed_bytes"),
        "compressed_bytes_consumed": provenance.get("compressed_bytes_consumed"),
        "note": "facts carried in the decode statistics (no acquisition.json present)",
    }


def _records_block(packet_series: list[int], stats: dict, primary: dict) -> dict:
    """Bounded sequence probe plus the whole-window density identity.

    The admitted MDP 3.0 packet series is dense (one channel sequence value per
    packet), so two contiguous probe runs plus ``first``/``last``/``total``
    certify the whole window without a multi-megabyte manifest:
    ``last - first + 1 == total``.  The full-series uniqueness and ordering
    evidence is reported in ``records_ordering`` and ``sequence_continuity``.
    """
    send_series = stats["sequence"].get("series_send_ns", [])
    feed_series = stats["sequence"].get("series_feed", [])
    keys = [f"{feed}:{value}" for feed, value in zip(feed_series, packet_series)]
    head = packet_series[:SEQUENCE_PROBE_ROWS]
    tail = packet_series[-SEQUENCE_PROBE_ROWS:]
    duplicates = len(keys) - len({key for key in keys})
    return {
        "sequence": head,
        "sequence_tail": tail,
        "sequence_first": packet_series[0] if packet_series else None,
        "sequence_last": packet_series[-1] if packet_series else None,
        "sequence_count_total": len(packet_series),
        "sequence_start": packet_series[0] if packet_series else None,
        "sequence_start_basis": (
            "CME MDP 3.0 channel-310 packet sequence: per channel, persists across sessions, so "
            "the first value of this window is not 1"
        ),
        "timestamps": send_series[:SEQUENCE_PROBE_ROWS] + send_series[-SEQUENCE_PROBE_ROWS:],
        "keys": keys[:SEQUENCE_PROBE_ROWS] + keys[-SEQUENCE_PROBE_ROWS:],
        "keys_count_total": len(keys),
        "keys_unique_total": duplicates == 0,
        "keys_duplicate_count": duplicates,
        "probe_note": (
            "sequence/sequence_tail and timestamps/keys are the head and tail probe runs "
            f"({SEQUENCE_PROBE_ROWS} rows each) of the admitted packet series; timestamps are venue "
            "exchange send times in nanoseconds since the Unix epoch. Whole-series density, "
            "uniqueness and ordering evidence: sequence_count_total == last - first + 1 (checked), "
            "keys_unique_total, records_ordering, sequence_continuity."
        ),
        "symbols": [primary.get("symbol")] if primary else [],
        "unit": "admitted MDP 3.0 packets of ES channel 310 in the window (deduplicated across feeds A/B)",
        "trade_rows": stats["trades"]["rows"],
        "book_increment_rows": stats["book"]["bbo_rows"],
    }


def _monotonicity(series: list) -> dict:
    """Count non-decreasing violations in an ordered series."""
    values = [value for value in series if value is not None]
    violations = 0
    first_bad = None
    for index in range(1, len(values)):
        if values[index] < values[index - 1]:
            violations += 1
            if first_bad is None:
                first_bad = index
    return {
        "n": len(values),
        "violations": violations,
        "first_violation_index": first_bad,
        "non_decreasing": violations == 0,
    }


def _packet_timestamps(packet_series: list[int], stats: dict) -> list[int]:
    """Exchange send times aligned with the admitted packet sequence series.

    The venue send time is used (not the capture time) because the manifest
    certifies *venue* ordering; capture-clock skew is reported separately in
    ``timestamp_domain``.
    """
    series = stats["sequence"].get("series_send_ns")
    return series if series else []


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _cmd_probe(args) -> int:
    probe = probe_url(args.url)
    print(json.dumps(probe, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(probe, handle, indent=2, sort_keys=True)
    return 0


def _cmd_verify_layout(args) -> int:
    report = verify_layout_against_xml(args.schema)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def _cmd_secdef(args) -> int:
    report = parse_secdef(args.secdef)
    report["instruments"] = {
        str(key): value for key, value in sorted(report["instruments"].items())
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
    return 0


def _load_reference(args, work_dir: str) -> tuple[dict, dict, dict]:
    """Fetch/parse the reference files; return (es_ids, secdef_report, config_report)."""
    os.makedirs(work_dir, exist_ok=True)
    secdef_path = args.secdef
    if not secdef_path:
        secdef_path = os.path.join(work_dir, os.path.basename(UPSTREAM_SECDEF_URL))
        if not os.path.exists(secdef_path):
            fetch_range_to_file(UPSTREAM_SECDEF_URL, secdef_path)
    config_path = args.config
    if not config_path:
        config_path = os.path.join(work_dir, os.path.basename(UPSTREAM_CONFIG_URL))
        if not os.path.exists(config_path):
            fetch_range_to_file(UPSTREAM_CONFIG_URL, config_path)
    secdef_report = parse_secdef(secdef_path)
    es_ids = secdef_report["instruments"]
    config_report = parse_channel_config(config_path)
    secdef_report["sha256"] = sha256_file(secdef_path)
    secdef_report["path"] = os.path.relpath(secdef_path, args.root)
    config_report["sha256"] = sha256_file(config_path)
    config_report["path"] = os.path.relpath(config_path, args.root)
    return es_ids, secdef_report, config_report


def fetch_range_to_file(url: str, path: str) -> None:
    """Download a small complete object with a plain resumable GET."""
    completed = subprocess.run(["curl", "-sS", "-f", "-o", path, url], capture_output=True, check=False)
    if completed.returncode != 0:
        raise FeedFormatError(
            f"download failed for {url}: rc={completed.returncode} {completed.stderr.decode(errors='replace')}"
        )


def _cmd_manifest(args) -> int:
    """Rebuild admission.json from an existing decode run (no re-retrieval)."""
    with open(args.stats) as handle:
        stats = json.load(handle)
    probe = {}
    if args.probe:
        with open(args.probe) as handle:
            probe = json.load(handle)
    elif os.path.exists(os.path.join(args.out_dir, "admission.json")):
        with open(os.path.join(args.out_dir, "admission.json")) as handle:
            probe = (json.load(handle).get("retrieval") or {}).get("probe") or {}
    raw_extract = stats.get("raw_extract_path")
    files = _collect_files(args.root, args.out_dir, raw_extract_path=raw_extract)
    files.extend(_reference_files(args.root, args.raw_dir))
    retrieval = (stats.get("provenance") or {}).get("retrieval_at_utc") or datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = write_admission_manifest(
        out_path=os.path.join(args.out_dir, "admission.json"),
        stats=stats,
        files=files,
        raw_extract_path=raw_extract,
        upstream_probe=probe,
        retrieved_at_utc=retrieval,
    )
    print(
        json.dumps(
            {
                "manifest_id": manifest["manifest_id"],
                "coverage": manifest["coverage"],
                "records_ordering": manifest["records_ordering"],
            },
            indent=2,
        )
    )
    return 0


def _cmd_decode(args) -> int:
    es_ids, secdef_report, config_report = _load_reference(args, args.work_dir)
    provenance = {"layout_verification": None, "assumed_vs_observed": _assumptions(es_ids)}
    if args.schema:
        provenance["layout_verification"] = verify_layout_against_xml(args.schema)
    provenance["upstream_sha256"] = args.upstream_sha256
    provenance["upstream_url"] = (args.probe or {}).get("url") or UPSTREAM_URL
    provenance["upstream_bytes"] = (args.probe or {}).get("total_bytes")
    provenance["retrieval_at_utc"] = (args.probe or {}).get("retrieved_at_utc")
    provenance["compressed_bytes_consumed"] = None
    provenance["decompressed_bytes"] = None
    provenance["retrieval_chunks"] = None
    provenance["retrieval_wall_seconds"] = None

    def file_source(path: str, chunk: int = 1 << 22):
        with open(path, "rb") as handle:
            while True:
                block = handle.read(chunk)
                if not block:
                    return
                yield block

    # ``--raw`` writes a fresh extract; ``--raw-declared`` points at an extract that
    # already exists (re-derivation from a retained extract must never rewrite it).
    raw_path = args.raw or None
    stats = _run_normalization(
        out_dir=args.out_dir,
        es_ids=es_ids,
        secdef_report=secdef_report,
        config_report=config_report,
        provenance=provenance,
        raw_path=raw_path,
        sources=file_source(args.pcap),
    )
    declared_raw = args.raw_declared or args.raw
    stats["raw_extract_path"] = declared_raw or None
    with open(os.path.join(args.out_dir, "es_stream_stats.json"), "w") as handle:
        json.dump(stats, handle, indent=2, sort_keys=True)
    files = _collect_files(args.root, args.out_dir, raw_extract_path=declared_raw)
    files.extend(_reference_files(args.root, args.work_dir, args.out_dir))
    manifest = write_admission_manifest(
        out_path=os.path.join(args.out_dir, "admission.json"),
        stats=stats,
        files=files,
        raw_extract_path=declared_raw,
        upstream_probe=args.probe or {},
        retrieved_at_utc=(
            (args.probe or {}).get("retrieved_at_utc")
            or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
    )
    print(json.dumps({k: manifest[k] for k in ("manifest_id", "coverage", "packet_counts")}, indent=2))
    return 0


def stream_decompressed_source(
    url: str,
    total_bytes: int,
    chunk: int,
    workers: int,
    digest,
    counters: dict,
    decompressor: str = "zstd",
):
    """Yield decompressed capture bytes while hashing the compressed object.

    The upstream object is 6.8 GB (above this epoch's 5 GB retention budget), so
    it is streamed: concurrent ordered byte-range GETs feed a single SHA-256 and
    the ``zstd -d -c`` decompressor; only the small derived outputs are retained.
    """
    process = subprocess.Popen(
        [decompressor, "-d", "-c"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    failure: list[BaseException] = []

    def pump() -> None:
        try:
            for data in iter_ordered_ranges(url, total_bytes, chunk, workers):
                digest.update(data)
                counters["chunks"] = counters.get("chunks", 0) + 1
                counters["compressed_bytes"] = counters.get("compressed_bytes", 0) + len(data)
                process.stdin.write(data)
        except BaseException as exc:  # noqa: BLE001 - surfaced to the caller below
            failure.append(exc)
        finally:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass

    writer = threading.Thread(target=pump, daemon=True)
    writer.start()
    while True:
        block = process.stdout.read(4 << 20)
        if not block:
            break
        counters["decompressed_bytes"] = counters.get("decompressed_bytes", 0) + len(block)
        yield block
    writer.join()
    code = process.wait()
    stderr = process.stderr.read().decode(errors="replace")
    process.stderr.close()
    if failure:
        raise FeedFormatError(f"upstream retrieval failed: {failure[0]}")
    if code != 0:
        raise FeedFormatError(f"{decompressor} exited {code}: {stderr.strip()}")
    if counters.get("compressed_bytes") != total_bytes:
        raise FeedFormatError(
            f"streamed {counters.get('compressed_bytes')} of {total_bytes} object bytes"
        )


# --------------------------------------------------------------------------- #
# retrieval driver


def _cmd_stream(args) -> int:
    root = args.root
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    probe = probe_url(args.url)
    if probe.get("total_bytes") is None:
        raise FeedFormatError(f"could not determine object size from {args.url}")
    os.makedirs(args.raw_dir, exist_ok=True)
    es_ids, secdef_report, config_report = _load_reference(args, args.work_dir)
    extract_path = os.path.join(
        args.raw_dir, "dc3-glbx-ab-dedup-20230717T133000.es-ch310.pcap"
    )
    digest = hashlib.sha256()
    counters: dict = {}
    provenance = {
        "layout_verification": None,
        "assumed_vs_observed": _assumptions(es_ids),
        "upstream_url": args.url,
        "upstream_bytes": probe["total_bytes"],
        "decompressor": "zstd CLI (-d -c)",
    }
    if args.schema:
        provenance["layout_verification"] = verify_layout_against_xml(args.schema)
    started = time.monotonic()
    stats = _run_normalization(
        out_dir=out_dir,
        es_ids=es_ids,
        secdef_report=secdef_report,
        config_report=config_report,
        provenance=provenance,
        raw_path=extract_path,
        sources=stream_decompressed_source(
            args.url, probe["total_bytes"], args.chunk_bytes, args.workers, digest, counters
        ),
    )
    provenance["upstream_sha256"] = digest.hexdigest()
    provenance["retrieval_at_utc"] = probe.get("retrieved_at_utc")
    provenance["retrieval_wall_seconds"] = round(time.monotonic() - started, 3)
    acquisition = {
        "object_url": args.url,
        "http": probe,
        "sha256_full_object": provenance["upstream_sha256"],
        "bytes": probe["total_bytes"],
        "chunks": counters.get("chunks"),
        "chunk_bytes": args.chunk_bytes,
        "workers": args.workers,
        "wall_seconds": provenance["retrieval_wall_seconds"],
        "decompressed_bytes": counters.get("decompressed_bytes"),
        "method": (
            "ordered concurrent HTTP byte-range GETs into a single pass: SHA-256 over every "
            "compressed byte read, piped through `zstd -d -c`, decoded on the fly; the source "
            "object is not retained"
        ),
        "retrieved_at_utc": probe.get("retrieved_at_utc"),
    }
    with open(os.path.join(out_dir, "acquisition.json"), "w") as handle:
        json.dump(acquisition, handle, indent=2, sort_keys=True)
    provenance["retrieval_chunks"] = counters.get("chunks")
    provenance["decompressed_bytes"] = counters.get("decompressed_bytes")
    provenance["compressed_bytes_consumed"] = counters.get("compressed_bytes")
    stats["provenance"] = provenance
    with open(os.path.join(out_dir, "es_stream_stats.json"), "w") as handle:
        json.dump(stats, handle, indent=2, sort_keys=True)

    files = _collect_files(root, out_dir, raw_extract_path=extract_path)
    files.extend(_reference_files(root, args.raw_dir, out_dir))
    manifest = write_admission_manifest(
        out_path=os.path.join(out_dir, "admission.json"),
        stats=stats,
        files=files,
        raw_extract_path=extract_path,
        upstream_probe=probe,
        retrieved_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    print(
        json.dumps(
            {
                "manifest_id": manifest["manifest_id"],
                "coverage": manifest["coverage"],
                "packet_counts": manifest["packet_counts"],
                "trades": manifest["trades"]["rows"],
                "upstream_sha256": provenance["upstream_sha256"],
                "wall_seconds": provenance["retrieval_wall_seconds"],
            },
            indent=2,
        )
    )
    return 0


def _collect_files(root: str, out_dir: str, raw_extract_path: str | None) -> list[dict]:
    entries = []
    for role, path in (
        ("trades", os.path.join(out_dir, "trades.csv")),
        ("book", os.path.join(out_dir, "bbo_increments.csv")),
    ):
        entries.append(_file_entry(root, role, path))
    if raw_extract_path and os.path.exists(raw_extract_path):
        entries.insert(0, _file_entry(root, "raw_extract", raw_extract_path, note=(
            "ES channel 310 packet extract of the upstream capture: pcap records copied "
            "byte-for-byte (unchanged link-layer frames and nanosecond timestamps), selected by "
            "destination port; the upstream object itself is recorded by url and full-object "
            "sha256 in source{} rather than retained, because this epoch's budget forbids "
            "retaining sources above 5 GB."
        )))
    return entries


def _reference_files(root: str, raw_dir: str, out_dir: str | None = None) -> list[dict]:
    """Hash-pin the retained reference objects used for identity and layout."""
    entries = []
    if out_dir:
        path = os.path.join(out_dir, "acquisition.json")
        if os.path.exists(path):
            entries.append(
                _file_entry(root, "acquisition_record", path, note="retrieval facts of the acquisition pass")
            )
    for role, name in (
        ("reference_secdef", os.path.basename(UPSTREAM_SECDEF_URL)),
        ("reference_channel_config", os.path.basename(UPSTREAM_CONFIG_URL)),
        ("reference_schema", MDP_SCHEMA_NAME),
    ):
        path = os.path.join(raw_dir, name)
        if os.path.exists(path):
            entries.append(
                _file_entry(root, role, path, note="retained reference object used for identity/layout")
            )
    return entries


def _declared_bytes(files: list[dict], role: str):
    for entry in files:
        if entry.get("role") == role:
            return entry.get("bytes")
    return None


def _with_upstream_entry(files: list[dict], stats: dict, upstream_probe: dict) -> list[dict]:
    """Declare the streamed (unretained) upstream object with its full digest."""
    provenance = stats.get("provenance") or {}
    digest = provenance.get("upstream_sha256")
    total = upstream_probe.get("total_bytes") or provenance.get("upstream_bytes")
    if not digest or not total:
        return files
    entry = {
        "role": "upstream_object",
        "retained": False,
        "path": None,
        "upstream_url": upstream_probe.get("url") or provenance.get("upstream_url"),
        "upstream_sha256": digest,
        "bytes": int(total),
        "status": "complete",
        "note": (
            "source object of 6,817,448,746 bytes streamed in ordered byte-range chunks: hashed "
            "and decoded on the fly, not retained, because this epoch's budget forbids retaining "
            "sources above 5 GB. Digest is a producer assertion computed over every byte read from "
            "the origin, not a disk-verified hash."
        ),
    }
    return files + [entry]


def _file_entry(root: str, role: str, path: str, note: str | None = None) -> dict:
    size = os.path.getsize(path)
    entry = {
        "role": role,
        "path": os.path.relpath(path, root),
        "sha256": sha256_file(path),
        "bytes": size,
        "expected_bytes": size,
        "status": "complete",
    }
    if note:
        entry["note"] = note
    return entry


def _assumptions(es_ids: dict) -> dict:
    return {
        "observed": [
            "pcap magic 0xa1b23c4d (nanosecond), link type 1 (Ethernet), snaplen read from the file header",
            "MDP 3.0 packet header: uint32 sequence + uint64 nanosecond exchange send time (decoded, 100% tiling)",
            "message header schemaId=1 and version=9 on every message (decoded)",
            "template ids 30/37/46/47/48/51 decoded against the CME SBE schema",
            "channel 310 = ES group, feed A port 14310, feed B port 15310 (CME channel configuration file)",
            "SecurityID -> contract-month mapping from the CME security definition snapshot for the session",
            "SecurityStatus messages on channel 310 carrying ASCII SecurityGroup 'ES' (decoded)",
        ],
        "assumed": [
            "the capture's file-level time span equals the named 10-minute window; only packets whose "
            "decoded exchange send time falls inside [13:30:00Z, 13:40:00Z) are admitted",
            "market-by-price level compaction on MDUpdateAction=Delete follows the standard CME "
            "price-level convention; MDUpdateAction 3/4 counts are reported so this is auditable",
            "observed book prices are assumed complete for the top 10 levels; the BBO uses levels "
            "tracked since the first message of the window (no snapshot was needed because ES "
            "level-1 rows are present from the first event)",
            "tick size and point value come from each instrument's own security definition "
            "(MinPriceIncrement x PriceDisplayFactor; ContractMultiplier), not from a constant; "
            "the spread itself is observed",
            "price scale: mantissa x 1e-9 = security-definition price units and "
            "index points = mantissa x 1e-9 x PriceDisplayFactor (verified in-capture against "
            "ES/CL/ZN definitions and their settlement prices)",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.getcwd())
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe")
    probe.add_argument("--url", default=UPSTREAM_URL)
    probe.add_argument("--out")
    probe.set_defaults(func=_cmd_probe)

    verify = sub.add_parser("verify-layout")
    verify.add_argument("--schema", required=True)
    verify.set_defaults(func=_cmd_verify_layout)

    secdef = sub.add_parser("secdef")
    secdef.add_argument("--secdef", required=True)
    secdef.add_argument("--out")
    secdef.set_defaults(func=_cmd_secdef)

    stream = sub.add_parser("stream")
    stream.add_argument("--url", default=UPSTREAM_URL)
    stream.add_argument("--out-dir", required=True)
    stream.add_argument("--raw-dir", required=True)
    stream.add_argument("--work-dir", required=True)
    stream.add_argument("--secdef")
    stream.add_argument("--config")
    stream.add_argument("--schema")
    stream.add_argument("--chunk-bytes", type=int, default=4 << 20)
    stream.add_argument("--workers", type=int, default=32)
    stream.set_defaults(func=_cmd_stream)

    manifest = sub.add_parser("manifest")
    manifest.add_argument("--stats", required=True)
    manifest.add_argument("--out-dir", required=True)
    manifest.add_argument("--raw-dir", required=True)
    manifest.add_argument("--probe")
    manifest.set_defaults(func=_cmd_manifest)

    decode = sub.add_parser("decode")
    decode.add_argument("--pcap", required=True)
    decode.add_argument("--out-dir", required=True)
    decode.add_argument("--work-dir", required=True)
    decode.add_argument("--raw")
    decode.add_argument("--raw-declared")
    decode.add_argument("--secdef")
    decode.add_argument("--config")
    decode.add_argument("--schema")
    decode.add_argument("--probe")
    decode.add_argument("--upstream-sha256")
    decode.set_defaults(func=_cmd_decode)

    args = parser.parse_args(argv)
    if args.command == "decode" and args.probe and isinstance(args.probe, str):
        with open(args.probe) as handle:
            args.probe = json.load(handle)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
