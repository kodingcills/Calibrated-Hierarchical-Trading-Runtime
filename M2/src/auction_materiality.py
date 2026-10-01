"""Frozen materiality measurement for branch AUCTION (B5, GOAL-M2-BRIDGE-001 epoch 5).

Two stages, deliberately separated so that the expensive state reconstruction can be
admitted as a *data-quality* artefact before any economic quantity exists:

``extract``
    Reconstruct per-symbol displayed books from the retained window
    (``M2/data/derived_auction/2026-06-12/window.bin.gz``) and capture, for each
    universe-qualified symbol, the ENTRY print: the book state immediately after the
    first book-affecting message strictly after 15:55:00 ET that leaves a valid,
    non-crossed, two-sided quote, at or before the frozen entry deadline. It writes
    the entry prints and a book-reconstruction diagnostic. No cross price, no
    return, no cost and no P&L is computed here.

``measure``
    Pure computation from the frozen extracts: the secondary mechanism metric, the
    primary executable-capture gross, the structural cost floor, the break-even
    residual, the preregistered four-state partition, the symbol-clustered bootstrap
    interval and the preregistered verdict. It never re-reads the tape.

Economics are NOT re-implemented here: every conversion, spread, USD evaluation,
break-even and classification comes from ``M2.src.envelope``.

Reconstruction bias (stated before the run, not after): a book rebuilt from the
window alone cannot see orders that were added before 15:49:50 and still resting.
A missing resting order can only make the reconstructed best ask HIGHER or the best
bid LOWER than the truth, i.e. entry prices strictly worse and the embedded entry
spread strictly wider, so every gross capture this module reports is a LOWER bound
on the true one. The bias cannot manufacture a positive result.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import heapq
import json
import os
import struct
import sys
from typing import Mapping, Sequence

try:  # package import
    from . import auction_certificate as certificate
    from . import envelope
    from . import ingest as itch
    from . import itch_stream_window as window
except ImportError:  # direct script execution
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import auction_certificate as certificate  # type: ignore[no-redef]
    import envelope  # type: ignore[no-redef]
    import ingest as itch  # type: ignore[no-redef]
    import itch_stream_window as window  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Frozen measurement parameters. Declared once, before the run.
# ---------------------------------------------------------------------------

PRICE_SCALE = 10_000  # ITCH prices carry four implied decimals
BPS = 10_000.0

NS_1555 = window.NS_1555
# Entry: the first eligible post-15:55 quote. The deadline bounds how long a symbol
# may wait for one; a symbol without a valid two-sided quote by then is missing, and
# missingness is reported by identity and reason.
ENTRY_DEADLINE_NS = 15 * 3_600 * 1_000_000_000 + 59 * 60 * 1_000_000_000

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260612
BOOTSTRAP_PERCENTILES = (2.5, 97.5)
QUANTILE_EDGES = (0.25, 0.50, 0.75)
STATE_LABELS = ("Q1_LOWEST", "Q2", "Q3", "Q4_HIGHEST")

COVERAGE_FLOOR = certificate.COVERAGE_FLOOR
VERDICT_INDETERMINATE_COVERAGE = "INDETERMINATE_COVERAGE"

# Sanity floor for the mechanism metric: a reconstructed mid at 15:55 must be
# inside the exchange's own near/far band often enough for the book to be
# considered a faithful reconstruction of the displayed top of book.
RECONSTRUCTION_MIN_WITHIN_FAR_BAND = 0.90

BOOK_MODIFYING = itch.BOOK_MODIFYING
ADD_TYPES = itch.ADD_TYPES
HEADER = itch.HEADER
U64 = itch.U64
U32 = itch.U32
FRAME_PREFIX = itch.FRAME_PREFIX

SIDE_BID = 0
SIDE_ASK = 1
SIDE_OF_BYTE = {0x42: SIDE_BID, 0x53: SIDE_ASK}

# Cost provenance for the structural floor. Identical to
# ``M2/config/cost_ledger_v1.json`` (read-only): every field is copied from the
# ledger, nothing is re-derived. SEC Section 31 and FINRA TAF are sale-side.
C0_ITEM_SPECS = (
    {
        "id": "sec_section_31_fee",
        "name": "SEC Section 31 transaction fee (sale side only)",
        "unit": envelope.UNIT_PER_MILLION_OF_SALES,
        "value": 20.6,
        "side": "sell",
        "provenance": {
            "source_id": "SEC-RELEASE-34-104909",
            "url": "https://www.federalregister.gov/documents/full_text/text/2026/03/04/2026-04233.txt",
            "publisher": "U.S. Securities and Exchange Commission (Release No. 34-104909) via the Federal Register",
            "access_date": "2026-09-22",
            "effective_period": "effective 2026-04-04 (before the 2026-06-12 sample)",
            "quote": "20.60 per $1,000,000 of aggregate sales",
            "status": envelope.STATUS_VERIFIED,
        },
    },
    {
        "id": "finra_trading_activity_fee",
        "name": "FINRA Trading Activity Fee (sale side only)",
        "unit": envelope.UNIT_USD_PER_SHARE,
        "value": 0.000195,
        "side": "sell",
        "provenance": {
            "source_id": "SR-FINRA-2024-019",
            "url": "https://www.federalregister.gov/documents/full_text/text/2024/11/27/2024-27764.txt",
            "publisher": "FINRA via the SEC (Release No. 34-101696, File No. SR-FINRA-2024-019)",
            "access_date": "2026-09-22",
            "effective_period": "effective 2026-01-01 (before the 2026-06-12 sample)",
            "quote": "$0.000195 per share sold, capped at $9.79 per trade",
            "status": envelope.STATUS_VERIFIED,
        },
    },
)

# Reported, NOT admitted to C0: the Nasdaq remove-liquidity fee is applicability-
# limited to the continuous book, and no evidence exists that a Closing Cross exit
# pays it (V1 verification, finding F5/claim B9). It is carried only as a C1
# scenario, because the ENTRY leg of both directions is a continuous-book
# aggressive order and may plausibly pay it.
EXCLUDED_REFERENCE_PATH_ITEM = {
    "id": "nasdaq_remove_liquidity_fee",
    "name": "Nasdaq remove-liquidity fee (continuous book, aggressive order)",
    "unit": envelope.UNIT_USD_PER_SHARE,
    "value": 0.0030,
    "excluded_from_c0_reason": (
        "Ledger applicability is 'Nasdaq continuous book, displayed orders >= $1.00'; the W1/V1 "
        "verification found no evidence that a Closing Cross exit is charged it, so it is not a "
        "verified mandatory charge on the frozen exit path."
    ),
    "c1_role": (
        "Both signal directions ENTER with an aggressive continuous-book order, which may pay it; "
        "it is therefore carried as a C1 scenario on the entry leg."
    ),
    "provenance": {
        "source_id": "NASDAQ-TRADER-PRICE-LIST",
        "url": "https://www.nasdaqtrader.com/Trader.aspx?id=PriceListTrading2",
        "publisher": "Nasdaq Stock Market LLC (trading price list)",
        "access_date": "2026-09-22",
        "effective_period": "undated on the retrieved page",
        "quote": "$0.0030 per share removed, displayed orders >= $1.00",
        "status": envelope.STATUS_VERIFIED,
    },
}

# C1 levels for the sensitivity table, in USD per share (a scenario grid, no
# probability assigned): the excluded continuous-book remove fee, half a cent, one
# cent, and one cent plus the fee.
C1_SCENARIO_USD_PER_SHARE = (0.0, 0.0030, 0.0050, 0.0100, 0.0130)


class MeasurementError(RuntimeError):
    """Raised when the frozen measurement cannot be carried out as frozen."""


# ---------------------------------------------------------------------------
# C0 envelope (delegated to envelope.py)
# ---------------------------------------------------------------------------


def c0_envelope() -> envelope.Envelope:
    items = []
    for spec in C0_ITEM_SPECS:
        provenance = envelope.Provenance(**spec["provenance"])
        items.append(
            envelope.CostItem(
                id=spec["id"],
                name=spec["name"],
                unit=spec["unit"],
                value=spec["value"],
                side=spec["side"],
                provenance=provenance,
                mandatory=True,
            )
        )
    built = envelope.Envelope(envelope_id="AUCTION-C0-SELL-LEG-v1", items=tuple(items))
    for item in built.c0_items():
        envelope.assert_c0(item)  # the single gate into C0; raises if anything is unverified
    return built


# ---------------------------------------------------------------------------
# Displayed-book reconstruction (extract stage)
# ---------------------------------------------------------------------------


class Book:
    """Displayed book for one locate: price levels plus a lazy top-of-book index."""

    __slots__ = ("locate", "bids", "asks", "bid_heap", "ask_heap", "best_bid", "best_ask")

    def __init__(self, locate: int) -> None:
        self.locate = locate
        self.bids: dict[int, int] = {}
        self.asks: dict[int, int] = {}
        self.bid_heap: list[int] = []
        self.ask_heap: list[int] = []
        self.best_bid: int | None = None
        self.best_ask: int | None = None

    def add(self, side: int, price: int, size: int) -> None:
        if side == SIDE_BID:
            if self.bids.get(price, 0) == 0:
                heapq.heappush(self.bid_heap, -price)
            self.bids[price] = self.bids.get(price, 0) + size
            if self.best_bid is None or price > self.best_bid:
                self.best_bid = price
        else:
            if self.asks.get(price, 0) == 0:
                heapq.heappush(self.ask_heap, price)
            self.asks[price] = self.asks.get(price, 0) + size
            if self.best_ask is None or price < self.best_ask:
                self.best_ask = price

    def _refresh_bid(self) -> None:
        heap = self.bid_heap
        bids = self.bids
        while heap and bids.get(-heap[0], 0) <= 0:
            heapq.heappop(heap)
        self.best_bid = -heap[0] if heap else None

    def _refresh_ask(self) -> None:
        heap = self.ask_heap
        asks = self.asks
        while heap and asks.get(heap[0], 0) <= 0:
            heapq.heappop(heap)
        self.best_ask = heap[0] if heap else None

    def reduce(self, side: int, price: int, size: int) -> int:
        """Reduce a level; returns the overshoot (0 when consistent)."""
        levels = self.bids if side == SIDE_BID else self.asks
        remaining = levels.get(price, 0) - size
        if remaining > 0:
            levels[price] = remaining
            return 0
        levels.pop(price, None)
        if side == SIDE_BID:
            if self.best_bid == price:
                self._refresh_bid()
        else:
            if self.best_ask == price:
                self._refresh_ask()
        return -remaining if remaining < 0 else 0

    def valid(self) -> bool:
        return (
            self.best_bid is not None
            and self.best_ask is not None
            and self.best_bid < self.best_ask
        )

    def mid2(self) -> int | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_bid + self.best_ask


def replay_entry_prints(
    window_path: str,
    candidates: Mapping[int, str],
    *,
    entry_start_ns: int = NS_1555,
    deadline_ns: int = ENTRY_DEADLINE_NS,
) -> tuple[dict[int, dict], dict]:
    """Capture the entry print per candidate symbol from the retained window.

    The entry print is the book state immediately AFTER applying the first
    book-affecting message with exchange timestamp strictly greater than
    ``entry_start_ns`` that leaves a valid, non-crossed, two-sided quote, provided
    that message is at or before ``deadline_ns``. No message later than the entry
    instant is used for that symbol's entry print, and the Closing-Cross print is
    never used here at all.
    """
    books: dict[int, Book] = {locate: Book(locate) for locate in candidates}
    orders: dict[int, tuple[int, int, int, int]] = {}
    entries: dict[int, dict] = {}
    snapshot_mid2: dict[int, int] = {}
    snapshot_taken: set[int] = set()
    diagnostics = {
        "book_messages_in_scope": 0,
        "book_messages_out_of_scope": 0,
        "adds_in_scope": 0,
        "orphan_executes": 0,
        "orphan_cancels": 0,
        "orphan_deletes": 0,
        "orphan_replaces": 0,
        "level_overshoots": 0,
        "zero_price_adds": 0,
        "frames": 0,
        "candidates": len(candidates),
        "entries_captured": 0,
        "entries_captured_by_deadline": 0,
        "symbols_with_snapshot_at_1555": 0,
        "duplicate_add_refs": 0,
    }
    msg_length = itch.MSG_LENGTH
    unpack_header = HEADER.unpack_from
    heap_push = heapq.heappush

    with open(window_path, "rb") as raw:
        import zlib

        decompressor = zlib.decompressobj(window.GZIP_WINDOW)
        buffer = bytearray()
        position = 0
        while True:
            block = raw.read(itch.CHUNK)
            if not block:
                break
            data = decompressor.decompress(block)
            if not data:
                continue
            buffer += data
            view = memoryview(buffer)
            limit = len(view)
            while position + FRAME_PREFIX <= limit:
                declared = (view[position] << 8) | view[position + 1]
                if declared == 0:
                    position += FRAME_PREFIX
                    continue
                if position + FRAME_PREFIX + declared > limit:
                    break
                base = position + FRAME_PREFIX
                message_type = view[base]
                expected = msg_length.get(message_type)
                if expected is None or declared != expected:
                    raise MeasurementError(
                        f"framing error at window offset {position}: type 0x{message_type:02x} "
                        f"declares {declared}, documented {expected}"
                    )
                position += FRAME_PREFIX + declared
                if message_type not in BOOK_MODIFYING:
                    continue
                diagnostics["frames"] += 1
                locate, _tracking, ts_hi, ts_lo = unpack_header(buffer, base + 1)
                timestamp = (ts_hi << 16) | ts_lo
                book = books.get(locate)
                if book is None:
                    diagnostics["book_messages_out_of_scope"] += 1
                    continue
                diagnostics["book_messages_in_scope"] += 1
                if timestamp > entry_start_ns and locate not in snapshot_taken:
                    mid2 = book.mid2()
                    if mid2 is not None:
                        snapshot_mid2[locate] = mid2
                    snapshot_taken.add(locate)

                if message_type in ADD_TYPES:
                    ref = U64.unpack_from(buffer, base + 11)[0]
                    side = SIDE_OF_BYTE.get(view[base + 19])
                    size = U32.unpack_from(buffer, base + 20)[0]
                    price = U32.unpack_from(buffer, base + 32)[0]
                    if side is None or price <= 0:
                        diagnostics["zero_price_adds"] += 1
                        continue
                    if ref in orders:
                        diagnostics["duplicate_add_refs"] += 1
                    orders[ref] = (locate, price, side, size)
                    book.add(side, price, size)
                    diagnostics["adds_in_scope"] += 1
                elif message_type == 0x45 or message_type == 0x43:  # E, C
                    ref = U64.unpack_from(buffer, base + 11)[0]
                    executed = U32.unpack_from(buffer, base + 19)[0]
                    entry = orders.get(ref)
                    if entry is None:
                        diagnostics["orphan_executes"] += 1
                    else:
                        _locate, price, side, size = entry
                        if book.reduce(side, price, executed):
                            diagnostics["level_overshoots"] += 1
                        remaining = size - executed
                        if remaining > 0:
                            orders[ref] = (_locate, price, side, remaining)
                        else:
                            del orders[ref]
                elif message_type == 0x58:  # X cancel (partial)
                    ref = U64.unpack_from(buffer, base + 11)[0]
                    cancelled = U32.unpack_from(buffer, base + 19)[0]
                    entry = orders.get(ref)
                    if entry is None:
                        diagnostics["orphan_cancels"] += 1
                    else:
                        _locate, price, side, size = entry
                        if book.reduce(side, price, cancelled):
                            diagnostics["level_overshoots"] += 1
                        remaining = size - cancelled
                        if remaining > 0:
                            orders[ref] = (_locate, price, side, remaining)
                        else:
                            del orders[ref]
                elif message_type == 0x44:  # D delete
                    ref = U64.unpack_from(buffer, base + 11)[0]
                    entry = orders.get(ref)
                    if entry is None:
                        diagnostics["orphan_deletes"] += 1
                    else:
                        _locate, price, side, size = entry
                        if book.reduce(side, price, size):
                            diagnostics["level_overshoots"] += 1
                        del orders[ref]
                elif message_type == 0x55:  # U replace
                    ref = U64.unpack_from(buffer, base + 11)[0]
                    new_ref = U64.unpack_from(buffer, base + 19)[0]
                    shares = U32.unpack_from(buffer, base + 27)[0]
                    price = U32.unpack_from(buffer, base + 31)[0]
                    entry = orders.pop(ref, None)
                    if entry is None:
                        diagnostics["orphan_replaces"] += 1
                    else:
                        _locate, old_price, side, old_size = entry
                        if book.reduce(side, old_price, old_size):
                            diagnostics["level_overshoots"] += 1
                    if price > 0:
                        side = entry[2] if entry is not None else None
                        if side is None:
                            diagnostics["orphan_replaces"] += 1
                        else:
                            if new_ref in orders:
                                diagnostics["duplicate_add_refs"] += 1
                            orders[new_ref] = (locate, price, side, shares)
                            book.add(side, price, shares)

                if timestamp > entry_start_ns and locate not in entries and book.valid():
                    entries[locate] = {
                        "locate": locate,
                        "symbol": candidates[locate],
                        "entry_ts_ns": timestamp,
                        "entry_ts": window.format_ns(timestamp),
                        "best_bid_raw": book.best_bid,
                        "best_ask_raw": book.best_ask,
                        "within_deadline": timestamp <= deadline_ns,
                    }
            view.release()
            del buffer[:position]
            position = 0

    diagnostics["entries_captured"] = len(entries)
    diagnostics["entries_captured_by_deadline"] = sum(
        1 for entry in entries.values() if entry["within_deadline"]
    )
    diagnostics["symbols_with_snapshot_at_1555"] = len(snapshot_mid2)
    diagnostics["orphan_total"] = (
        diagnostics["orphan_executes"]
        + diagnostics["orphan_cancels"]
        + diagnostics["orphan_deletes"]
        + diagnostics["orphan_replaces"]
    )
    diagnostics["orphan_rate_of_in_scope_messages"] = (
        diagnostics["orphan_total"] / diagnostics["book_messages_in_scope"]
        if diagnostics["book_messages_in_scope"]
        else None
    )
    diagnostics["warmup_note"] = (
        "Orphan book messages reference an order added before the retained window opened at "
        "15:49:50: they are the direct, counted evidence of pre-window state the reconstruction "
        "cannot see. A missing resting order can only widen the reconstructed quote, so entry "
        "prices are biased away from the closing cross, never toward it."
    )
    return entries, snapshot_mid2, diagnostics


# ---------------------------------------------------------------------------
# Measure stage
# ---------------------------------------------------------------------------


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1 << 20)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


DIRECTION_SIGN = {"B": 1, "S": -1}


def per_symbol_rows(
    extract: Sequence[Mapping],
    entries: Mapping[int, Mapping],
    snapshot_mid2: Mapping[int, int],
    *,
    c0: envelope.Envelope,
) -> tuple[list[dict], list[dict]]:
    """Build one row per symbol: signal, mechanism displacement and executable capture."""
    rows: list[dict] = []
    excluded: list[dict] = []
    for record in extract:
        locate = int(record["locate"])
        symbol = record["symbol"]
        if not record.get("in_denominator"):
            excluded.append(
                {
                    "locate": locate,
                    "symbol": symbol,
                    "reason": record.get("exclusion_reason") or "not_in_denominator",
                    "detail": record.get("directory_failure") or "",
                }
            )
            continue
        early_sign = DIRECTION_SIGN.get(record["read_1550_direction"])
        late_sign = DIRECTION_SIGN.get(record["read_1555_direction"])
        if early_sign is None or late_sign is None:
            excluded.append(
                {"locate": locate, "symbol": symbol, "reason": "ineligible_imbalance_direction", "detail": ""}
            )
            continue
        signed_1550 = early_sign * int(record["read_1550_imbalance_shares"])
        signed_1555 = late_sign * int(record["read_1555_imbalance_shares"])
        delta = signed_1555 - signed_1550
        if delta == 0:
            excluded.append(
                {
                    "locate": locate,
                    "symbol": symbol,
                    "reason": "zero_signed_imbalance_change",
                    "detail": f"signed(15:50)={signed_1550} signed(15:55)={signed_1555}",
                }
            )
            continue
        paired = max(int(record["read_1555_paired_shares"]), 1)
        entry = entries.get(locate)
        if entry is None:
            excluded.append(
                {
                    "locate": locate,
                    "symbol": symbol,
                    "reason": "no_eligible_entry_quote_before_deadline",
                    "detail": (
                        "no book-affecting message strictly after 15:55:00 ET left a valid "
                        "two-sided non-crossed quote by 15:59:00 ET"
                    ),
                }
            )
            continue
        if not entry.get("within_deadline"):
            excluded.append(
                {
                    "locate": locate,
                    "symbol": symbol,
                    "reason": "entry_quote_after_deadline",
                    "detail": entry.get("entry_ts") or "",
                }
            )
            continue

        reference_price = int(record["read_1555_reference_price_raw"]) / PRICE_SCALE
        closing_cross_price = int(record["closing_cross_price_raw"]) / PRICE_SCALE
        if reference_price <= 0 or closing_cross_price <= 0:
            excluded.append(
                {
                    "locate": locate,
                    "symbol": symbol,
                    "reason": "non_positive_reference_or_cross_price",
                    "detail": f"reference={reference_price} cross={closing_cross_price}",
                }
            )
            continue
        best_bid = int(entry["best_bid_raw"]) / PRICE_SCALE
        best_ask = int(entry["best_ask_raw"]) / PRICE_SCALE
        signal = envelope.SIGNAL_POSITIVE if delta > 0 else envelope.SIGNAL_NEGATIVE
        gross = envelope.auction_executable_gross(
            signal,
            best_bid=best_bid,
            best_ask=best_ask,
            closing_cross_price=closing_cross_price,
            reference_price=reference_price,
        )
        # One sell leg per round trip: the Closing Cross exit for a positive signal,
        # the continuous-book entry for a negative one.
        sell_price = closing_cross_price if signal == envelope.SIGNAL_POSITIVE else best_bid
        basis = envelope.Basis(quantity=1.0, price_usd=sell_price)
        c0_usd = c0.structural_c0_usd(basis)
        # The same C0 expressed against the branch's own frozen reference price, so
        # the bps figure and the mechanism metric share one denominator. The USD ->
        # bps conversion is delegated to envelope.convert (unit-safe, refuses if the
        # price is unknown).
        c0_bps = envelope.convert(
            c0_usd,
            envelope.UNIT_USD,
            envelope.UNIT_BPS,
            envelope.Basis(quantity=1.0, price_usd=reference_price),
        )
        mechanisms = (closing_cross_price - reference_price) / reference_price * BPS
        direction_sign = 1.0 if signal == envelope.SIGNAL_POSITIVE else -1.0
        mid2 = snapshot_mid2.get(locate)
        reconstructed_mid = (mid2 / 2.0 / PRICE_SCALE) if mid2 is not None else None

        rows.append(
            {
                "locate": locate,
                "symbol": symbol,
                "signal": signal,
                "side_sign": direction_sign,
                "signed_imbalance_1550": signed_1550,
                "signed_imbalance_1555": signed_1555,
                "delta_imbalance": delta,
                "paired_shares_1555": paired,
                "scaled_delta_imbalance": delta / paired,
                "read_1550_ts_ns": record["read_1550_ts_ns"],
                "read_1555_ts_ns": record["read_1555_ts_ns"],
                "reference_price_usd": reference_price,
                "closing_cross_price_usd": closing_cross_price,
                "entry_ts_ns": entry["entry_ts_ns"],
                "entry_ts": entry["entry_ts"],
                "best_bid_usd": best_bid,
                "best_ask_usd": best_ask,
                "entry_spread_usd": gross["entry_spread_usd"],
                "entry_price_usd": gross["entry_price"],
                "sell_leg_price_usd": sell_price,
                "exit_price_usd": closing_cross_price,
                "mechanism_displacement_bps": mechanisms,
                "mechanism_side_signed_bps": direction_sign * mechanisms,
                "gross_usd_per_share": gross["gross_usd_per_share"],
                "gross_bps": gross["gross_bps"],
                "c0_usd_per_share": c0_usd,
                "c0_bps": c0_bps,
                "c_star_usd_per_share": envelope.break_even_residual(
                    gross["gross_usd_per_share"], c0_usd
                ),
                "c_star_bps": (gross["gross_usd_per_share"] - c0_usd) / reference_price * BPS,
                "reconstructed_mid_at_1555_usd": reconstructed_mid,
                "reconstructed_mid_minus_reference_bps": (
                    None
                    if reconstructed_mid is None
                    else (reconstructed_mid - reference_price) / reference_price * BPS
                ),
                "near_price_usd": int(record["read_1555_near_price_raw"]) / PRICE_SCALE,
                "far_price_usd": int(record["read_1555_far_price_raw"]) / PRICE_SCALE,
            }
        )
    return rows, excluded


def quartile_states(rows: Sequence[Mapping]) -> dict:
    """The preregistered 4-quantile partition, cut from signal-side data only."""
    import numpy as np

    values = np.array([row["scaled_delta_imbalance"] for row in rows], dtype=np.float64)
    if values.size == 0:
        return {"edges": [], "labels": list(STATE_LABELS), "assignment": {}}
    edges = [float(np.quantile(values, q)) for q in QUANTILE_EDGES]
    assignment = {}
    for row in rows:
        value = row["scaled_delta_imbalance"]
        index = 0
        for edge in edges:
            if value > edge:
                index += 1
        assignment[row["locate"]] = STATE_LABELS[min(index, len(STATE_LABELS) - 1)]
    return {
        "edges": edges,
        "edge_quantiles": list(QUANTILE_EDGES),
        "labels": list(STATE_LABELS),
        "definition": (
            "states partition delta_imbalance / max(PairedShares_15:55, 1) at its own 25/50/75 "
            "percentiles; only the signal side enters the cut points, no outcome or cost does. "
            "State rows are diagnostic and cannot rescue a pooled failure."
        ),
        "assignment": assignment,
    }


def cluster_bootstrap(
    rows: Sequence[Mapping],
    key: str,
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Symbol-clustered percentile bootstrap of the pooled mean of ``key``."""
    import numpy as np

    values = np.array([row[key] for row in rows], dtype=np.float64)
    n = values.size
    if n == 0:
        return {
            "key": key,
            "n": 0,
            "mean": None,
            "lo": None,
            "hi": None,
            "standard_error": None,
            "resamples": resamples,
            "seed": seed,
        }
    rng = np.random.default_rng(seed)
    means = np.empty(resamples, dtype=np.float64)
    for index in range(resamples):
        sample = rng.integers(0, n, n)
        means[index] = values[sample].mean()
    lo, hi = np.percentile(means, BOOTSTRAP_PERCENTILES)
    return {
        "key": key,
        "n": int(n),
        "mean": float(values.mean()),
        "lo": float(lo),
        "hi": float(hi),
        "standard_error": float(means.std(ddof=1)),
        "resamples": resamples,
        "seed": seed,
        "cluster": "symbol",
        "percentiles": list(BOOTSTRAP_PERCENTILES),
        "rng": "numpy.random.default_rng(PCG64)",
        "resample_means_percentiles": {
            str(p): float(np.percentile(means, p)) for p in (0.5, 2.5, 5.0, 50.0, 95.0, 97.5, 99.5)
        },
    }


def bootstrap_c_star(rows: Sequence[Mapping], *, resamples: int, seed: int) -> dict:
    import numpy as np

    gross = np.array([row["gross_usd_per_share"] for row in rows], dtype=np.float64)
    c0 = np.array([row["c0_usd_per_share"] for row in rows], dtype=np.float64)
    n = gross.size
    if n == 0:
        return {"n": 0, "mean": None, "lo": None, "hi": None}
    rng = np.random.default_rng(seed)
    means = np.empty(resamples, dtype=np.float64)
    for index in range(resamples):
        sample = rng.integers(0, n, n)
        means[index] = (gross[sample] - c0[sample]).mean()
    lo, hi = np.percentile(means, BOOTSTRAP_PERCENTILES)
    return {
        "n": int(n),
        "mean": float((gross - c0).mean()),
        "lo": float(lo),
        "hi": float(hi),
        "resamples": resamples,
        "seed": seed,
        "role": "REPORTED_ONLY (the decision uses the interval on the gross capture)",
    }


def decision_for(
    rows: Sequence[Mapping],
    *,
    coverage: Mapping,
    reconstruction: Mapping,
    signal_scope: Mapping | None = None,
) -> dict:
    """The preregistered verdict, from the frozen rule in ``envelope`` only.

    Clause order, frozen before the run:

    1. Coverage floor on the input-availability ratio (the branch's own 0.95 floor,
       over the population the repo's coverage machinery defines). Failure ->
       ``INDETERMINATE_COVERAGE``; the statistical rule is still reported.
    2. Reconstruction validation: if the reconstructed top of book is not a
       faithful inside quote often enough, the PRIMARY metric is not measurable ->
       ``INDETERMINATE`` (named).
    3. Otherwise the frozen ``classify_materiality`` rule.

    The signal scope (symbols the frozen N/O/P direction rule removes) is attached
    as a named clause, never as a silent re-scope: a KILL verdict is unaffected by
    it in principle, because a symbol with no signed imbalance has no direction to
    act on and cannot raise the measured capture; a positive verdict carries it as
    an explicit population caveat.
    """
    pool_usd = cluster_bootstrap(rows, "gross_usd_per_share")
    pool_bps = cluster_bootstrap(rows, "gross_bps")
    c0_usd = float(sum(row["c0_usd_per_share"] for row in rows) / len(rows)) if rows else None
    classified = (
        envelope.classify_materiality(pool_usd["mean"], pool_usd["lo"], pool_usd["hi"], c0_usd)
        if rows
        else {
            "verdict": envelope.VERDICT_INDETERMINATE,
            "gross_usd": None,
            "uncertainty_lo_usd": None,
            "uncertainty_hi_usd": None,
            "c0_usd": None,
            "c_star_usd": None,
            "rule": "no analysable symbol",
            "significance_is_decision_criterion": False,
        }
    )
    verdict = classified["verdict"]
    clause = None
    clauses: list[str] = []
    input_ratio = coverage.get("input_availability_ratio")
    if input_ratio is None or input_ratio + 1e-12 < COVERAGE_FLOOR:
        verdict = VERDICT_INDETERMINATE_COVERAGE
        clause = "COVERAGE_FLOOR"
        clauses.append("COVERAGE_FLOOR")
    elif reconstruction.get("within_far_band_ratio") is not None and (
        reconstruction["within_far_band_ratio"] < RECONSTRUCTION_MIN_WITHIN_FAR_BAND
    ):
        verdict = envelope.VERDICT_INDETERMINATE
        clause = "ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED"
        clauses.append("ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED")
    if signal_scope is not None and signal_scope.get("subfloor"):
        clauses.append("SIGNAL_SCOPE_SUBFLOOR")
    return {
        "verdict": verdict,
        "clause": clause,
        "clauses": clauses,
        "signal_scope_clause_note": (
            None
            if not clauses or "SIGNAL_SCOPE_SUBFLOOR" not in clauses
            else (
                "The frozen sign rule removes symbols whose Closing-Cross reads carry direction "
                "N/O/P (measured: every such read carries ImbalanceShares == 0), so the decision "
                "rests on the signal-defined population, which is below the 0.95 coverage floor. "
                "This is a population-scope limitation, reported by identity, not a data hole: "
                "those symbols have no signed imbalance to act on and cannot raise the measured "
                "capture. A KILL verdict is therefore unaffected; a positive verdict is at most "
                "provisional on this scope."
            )
        ),
        "rule_verdict": classified["verdict"],
        "rule_clause": None if clause is None else "SUPERSEDED_BY_" + clause,
        "gross_usd_per_share_mean": classified["gross_usd"],
        "gross_bps_mean": pool_bps["mean"],
        "uncertainty_lo_usd": classified["uncertainty_lo_usd"],
        "uncertainty_hi_usd": classified["uncertainty_hi_usd"],
        "c0_usd_per_share_mean": classified["c0_usd"],
        "c_star_usd_per_share": classified["c_star_usd"],
        "rule": classified["rule"],
        "significance_is_decision_criterion": False,
    }


# ---------------------------------------------------------------------------
# Stage entry points
# ---------------------------------------------------------------------------


def stage_extract(args: argparse.Namespace) -> int:
    extract = load_json(args.extract)
    candidates = {
        int(record["locate"]): record["symbol"]
        for record in extract
        if record.get("in_denominator")
    }
    print(f"candidates (universe-qualified with a valid Closing Cross): {len(candidates)}")
    entries, snapshot_mid2, diagnostics = replay_entry_prints(args.window, candidates)
    diagnostics["candidate_universe"] = "in_denominator of the certificate extract"
    diagnostics["entry_rule"] = (
        "book state immediately after the first book-affecting message strictly after 15:55:00 ET "
        "that leaves a valid non-crossed two-sided quote, at or before 15:59:00 ET"
    )
    diagnostics["reconstruction_bias_direction"] = (
        "LOWER-BOUND: missing pre-15:49:50 resting orders can only widen the reconstructed quote "
        "and worsen the entry price, never improve it"
    )
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_utc": datetime.datetime.now(datetime.timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "window_artifact": args.window,
                "entry_prints": [entries[key] for key in sorted(entries)],
                "snapshot_mid2_at_1555": {str(key): value for key, value in sorted(snapshot_mid2.items())},
                "diagnostics": diagnostics,
            },
            handle,
            indent=1,
            sort_keys=True,
        )
        handle.write("\n")
    print(json.dumps(diagnostics, indent=1, sort_keys=True))
    print(f"entries -> {args.out} sha256={_sha256_file(args.out)}")
    return 0


def stage_measure(args: argparse.Namespace) -> int:
    extract = load_json(args.extract)
    entry_payload = load_json(args.entries)
    entries = {int(entry["locate"]): entry for entry in entry_payload["entry_prints"]}
    snapshot_mid2 = {int(key): value for key, value in entry_payload["snapshot_mid2_at_1555"].items()}
    c0 = c0_envelope()

    rows, excluded = per_symbol_rows(extract, entries, snapshot_mid2, c0=c0)
    states = quartile_states(rows)
    denominator = sum(1 for record in extract if record.get("in_denominator"))
    inputs_present = sum(1 for record in extract if record.get("in_numerator"))
    signal_defined = sum(1 for record in extract if record.get("signal_defined"))
    analysed_ratio = (len(rows) / denominator) if denominator else None
    signal_ratio = (signal_defined / denominator) if denominator else None
    coverage = {
        "denominator_symbols_with_valid_closing_cross": denominator,
        "input_availability_numerator": inputs_present,
        "input_availability_ratio": (inputs_present / denominator) if denominator else None,
        "signal_defined_symbols": signal_defined,
        "signal_scope_ratio": signal_ratio,
        "signal_scope_subfloor": None if signal_ratio is None else signal_ratio < COVERAGE_FLOOR,
        "analysed_symbols": len(rows),
        "analysed_ratio_of_denominator": analysed_ratio,
        "ratio": analysed_ratio,
        "floor": COVERAGE_FLOOR,
        "floor_applies_to": "input_availability_ratio (the frozen 0.95 floor)",
        "missingness": excluded,
        "missingness_reason_counts": _count_reasons(excluded),
        "signal_scope_note": (
            "signal_scope_ratio = symbols for which the FROZEN sign rule yields a signed "
            "imbalance at both reads, over universe-qualified symbols with a valid Closing Cross. "
            "It is reported separately because direction N/O/P is a market state (no imbalance), "
            "not absent data; every such read in this session carries ImbalanceShares == 0 and "
            "symbols whose reads are both N have delta_imbalance == 0 under any reading."
        ),
    }

    within_far = 0
    within_tick = 0
    deviations = []
    for row in rows:
        deviation = row["reconstructed_mid_minus_reference_bps"]
        if deviation is None:
            continue
        deviations.append(abs(deviation))
        far = row["far_price_usd"]
        near = row["near_price_usd"]
        mid = row["reconstructed_mid_at_1555_usd"]
        if far and near and near <= mid <= far:
            within_far += 1
        if abs(mid - row["reference_price_usd"]) <= 0.01:
            within_tick += 1
    analysed_with_snapshot = sum(
        1 for row in rows if row["reconstructed_mid_at_1555_usd"] is not None
    )
    reconstruction = {
        "symbols_with_snapshot_at_1555": analysed_with_snapshot,
        "within_exchange_near_far_band": within_far,
        "within_far_band_ratio": (within_far / analysed_with_snapshot) if analysed_with_snapshot else None,
        "min_within_far_band_ratio": RECONSTRUCTION_MIN_WITHIN_FAR_BAND,
        "within_one_tick_of_reference_price": within_tick,
        "within_one_tick_ratio": (within_tick / analysed_with_snapshot) if analysed_with_snapshot else None,
        "median_abs_deviation_bps": _median(deviations),
        "p90_abs_deviation_bps": _percentile(deviations, 90.0),
        "note": (
            "The reconstructed midpoint at 15:55 is compared with the exchange's own Current "
            "Reference Price and with the near/far band from the same NOII read. These are related "
            "but not identical constructs (the reference price is the price at which the cross "
            "would clear), so this is a diagnostic, and its preregistered floor only guards "
            "against a reconstruction that is not a faithful displayed top of book."
        ),
    }

    decision = decision_for(
        rows,
        coverage=coverage,
        reconstruction=reconstruction,
        signal_scope={"ratio": signal_ratio, "subfloor": coverage["signal_scope_subfloor"]},
    )
    scope_comparison = liquidity_comparison(extract)

    by_state = []
    for index, label in enumerate(STATE_LABELS):
        subset = [row for row in rows if states["assignment"].get(row["locate"]) == label]
        state_usd = cluster_bootstrap(subset, "gross_usd_per_share", seed=BOOTSTRAP_SEED + index)
        state_bps = cluster_bootstrap(subset, "gross_bps", seed=BOOTSTRAP_SEED + index)
        state_mechanism = cluster_bootstrap(
            subset, "mechanism_side_signed_bps", seed=BOOTSTRAP_SEED + index
        )
        state_c0 = (
            float(sum(row["c0_usd_per_share"] for row in subset) / len(subset)) if subset else None
        )
        by_state.append(
            {
                "state": label,
                "n": len(subset),
                "gross_usd_per_share": state_usd,
                "gross_bps": state_bps,
                "mechanism_side_signed_bps": state_mechanism,
                "c0_usd_per_share_mean": state_c0,
                "c_star_usd_per_share": (
                    None if not subset else state_usd["mean"] - state_c0
                ),
                "scaled_delta_range": _range_of(subset, "scaled_delta_imbalance"),
                "diagnostic_only": True,
            }
        )

    mechanism = cluster_bootstrap(rows, "mechanism_side_signed_bps")
    raw_mechanism = cluster_bootstrap(rows, "mechanism_displacement_bps")
    c1 = _c1_table(rows, decision) if rows else {"rows": [], "note": "no analysable symbol"}
    significance = envelope.significance_against_zero(
        mechanism["mean"], mechanism["standard_error"]
    )
    gross_significance = envelope.significance_against_zero(
        None if not rows else decision["gross_usd_per_share_mean"],
        None if not rows else cluster_bootstrap(rows, "gross_usd_per_share")["standard_error"],
    )

    results = {
        "experiment_id": "M2-BRIDGE-AUCTION-LATENOII-MATERIALITY",
        "candidate_id": "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
        "branch": "AUCTION",
        "session_date": "2026-06-12",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "measurement_window": {
            "start": window.format_ns(window.WINDOW_START_NS),
            "end": window.format_ns(window.WINDOW_END_NS),
            "entry_start": window.format_ns(NS_1555),
            "entry_deadline": window.format_ns(ENTRY_DEADLINE_NS),
            "exit": "Closing Cross print (Cross Trade Q, Cross Type C)",
        },
        "universe": {
            "rule_id": certificate.UNIVERSE_RULE_ID_V2,
            "clause": certificate.UNIVERSE_RULE_ID_V2 and {
                "Authenticity": certificate.UNIVERSE_AUTHENTICITY,
                "ETP Flag": certificate.UNIVERSE_ETP_FLAG,
                "Issue Classification": certificate.UNIVERSE_ISSUE_CLASSIFICATION,
                "Market Category": sorted(certificate.UNIVERSE_MARKET_CATEGORIES),
                "Issue Sub-Type": certificate.UNIVERSE_ISSUE_SUB_TYPE,
            },
            "extract_sha256": _sha256_file(args.extract),
            "entry_prints_sha256": _sha256_file(args.entries),
        },
        "signal": {
            "definition": "signed_imbalance(15:55) - signed_imbalance(15:50), B=+shares, S=-shares",
            "scale": "delta_imbalance / max(PairedShares_15:55, 1)",
            "read_semantics": (
                "15:50: last eligible Cross-Type-C read at or before 15:50:00 ET, else the first "
                "read after it; 15:55: last eligible Cross-Type-C read at or before 15:55:00 ET"
            ),
            "signal_counts": _count_field(rows, "signal"),
        },
        "mechanism_metric": {
            "definition": (
                "side-signed (ClosingCrossPrice - CurrentReferencePrice_15:55) / "
                "CurrentReferencePrice_15:55, in bps; secondary and REPORTED_ONLY"
            ),
            "pooled_side_signed_bps": mechanism,
            "pooled_raw_displacement_bps": raw_mechanism,
            "by_state": [
                {
                    "state": entry["state"],
                    "n": entry["n"],
                    "mechanism_side_signed_bps": entry["mechanism_side_signed_bps"],
                }
                for entry in by_state
            ],
        },
        "executable_capture": {
            "definition": (
                "POSITIVE signal: entry at the first eligible post-15:55 best ask, exit at the "
                "Closing Cross; NEGATIVE signal: entry at the best bid, cover at the Closing "
                "Cross. The entry spread is embedded in the gross by construction."
            ),
            "pooled_gross_usd_per_share": decision,
            "pooled_gross_bps": cluster_bootstrap(rows, "gross_bps"),
            "pooled_c0_bps": cluster_bootstrap(rows, "c0_bps"),
            "pooled_c_star_bps": cluster_bootstrap(rows, "c_star_bps"),
            "c_star_usd_per_share_bootstrap": bootstrap_c_star(
                rows, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED
            ),
            "by_state": by_state,
        },
        "structural_cost_c0": {
            "envelope_id": c0.envelope_id,
            "items": [dict(spec) for spec in C0_ITEM_SPECS],
            "c0_provenance": c0.c0_provenance(),
            "per_share_formula": (
                "SEC Section 31 = 20.6e-6 x sell-leg price; FINRA TAF = 0.000195 per share sold; "
                "one sell leg per round trip (the Closing Cross exit for a positive signal, the "
                "continuous-book entry for a negative one)"
            ),
            "excluded_items": [dict(EXCLUDED_REFERENCE_PATH_ITEM)],
            "taf_cap_check": (
                "the $9.79 per-trade TAF cap does not bind at the declared representative order "
                "size of 100 shares (100 x 0.000195 = $0.0195); the measurement is per share and "
                "the cap is inert"
            ),
        },
        "c1_sensitivity": c1,
        "uncertainty": {
            "bootstrap": {
                "cluster": "symbol",
                "resamples": BOOTSTRAP_RESAMPLES,
                "seed": BOOTSTRAP_SEED,
                "percentiles": list(BOOTSTRAP_PERCENTILES),
                "rng": "numpy.random.default_rng(PCG64)",
                "per_state_seed_rule": "BOOTSTRAP_SEED + state_index (Q1=...012, Q2=...013, ...)",
            },
            "deterministic": True,
        },
        "coverage": coverage,
        "signal_scope_liquidity_comparison": scope_comparison,
        "book_reconstruction": {
            **reconstruction,
            "window_diagnostics": entry_payload["diagnostics"],
        },
        "significance_reported_only": {
            "mechanism_side_signed_bps": significance,
            "gross_usd_per_share": gross_significance,
            "note": "never an input to the decision rule (envelope.classify_materiality)",
        },
        "decision": {
            **decision,
            "coverage_floor": COVERAGE_FLOOR,
            "coverage_ratio": coverage["ratio"],
            "significance_is_decision_criterion": False,
            "named_clause_vocabulary": [
                "KILL_MATERIALITY",
                "SURVIVE_PROVISIONAL",
                "INDETERMINATE",
                VERDICT_INDETERMINATE_COVERAGE,
                "ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED",
            ],
        },
        "per_symbol": rows,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=1, sort_keys=True)
        handle.write("\n")
    _print_summary(results)
    print(f"results -> {args.out} sha256={_sha256_file(args.out)}")
    return 0


def liquidity_comparison(extract: Sequence[Mapping]) -> dict:
    """Do the symbols the frozen direction rule removes differ in size?

    Reported, not used: it tells a reader how far the decision population differs
    from the universe it is drawn from. Paired shares at 15:55 and the Closing
    Cross print size are the two size measures the frozen reads carry.
    """
    import numpy as np

    denominator = [record for record in extract if record.get("in_denominator")]
    defined = [record for record in denominator if record.get("signal_defined")]
    removed = [
        record
        for record in denominator
        if not record.get("signal_defined")
        and record.get("exclusion_reason") in ("", None)
    ]

    def summarize(group: Sequence[Mapping]) -> dict:
        if not group:
            return {"n": 0, "median_paired_shares_1555": None, "median_cross_shares": None}
        paired = np.array([float(record["read_1555_paired_shares"]) for record in group])
        cross = np.array([float(record["closing_cross_shares"]) for record in group])
        return {
            "n": len(group),
            "median_paired_shares_1555": float(np.median(paired)),
            "median_cross_shares": float(np.median(cross)),
            "mean_paired_shares_1555": float(paired.mean()),
        }

    return {
        "signal_defined": summarize(defined),
        "removed_by_direction_rule": summarize(removed),
        "role": "REPORTED_ONLY",
        "note": (
            "Both groups are Nasdaq-listed common stock carrying a valid Closing Cross; the "
            "comparison states how the decision population differs from the universe it is drawn "
            "from. It never enters the verdict."
        ),
    }


def _count_reasons(excluded: Sequence[Mapping]) -> dict:
    counts: dict[str, int] = {}
    for row in excluded:
        counts[row["reason"]] = counts.get(row["reason"], 0) + 1
    return counts


def _count_field(rows: Sequence[Mapping], field: str) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row[field])
        counts[key] = counts.get(key, 0) + 1
    return counts


def _median(values: Sequence[float]) -> float | None:
    import numpy as np

    return float(np.median(values)) if len(values) else None


def _percentile(values: Sequence[float], q: float) -> float | None:
    import numpy as np

    return float(np.percentile(values, q)) if len(values) else None


def _range_of(rows: Sequence[Mapping], field: str) -> dict:
    if not rows:
        return {"min": None, "max": None}
    values = [row[field] for row in rows]
    return {"min": min(values), "max": max(values)}


def _c1_table(rows: Sequence[Mapping], decision: Mapping) -> dict:
    """C* across C1 scenarios, in USD per share, plus the frozen bps basis."""
    levels_usd = list(C1_SCENARIO_USD_PER_SHARE)
    gross = decision["gross_usd_per_share_mean"]
    c0 = decision["c0_usd_per_share_mean"]
    table = envelope.c1_sensitivity(gross, c0, levels_usd)
    mean_reference = sum(row["reference_price_usd"] for row in rows) / len(rows)
    rows_out = []
    for row in table["rows"]:
        rows_out.append(
            {
                **row,
                "c1_bps": row["c1_usd"] / mean_reference * BPS,
                "c_star_bps": (row["c_star_usd"] / mean_reference) * BPS,
            }
        )
    table["rows"] = rows_out
    table["mean_reference_price_usd"] = mean_reference
    table["named_c1_items"] = [
        {
            "id": EXCLUDED_REFERENCE_PATH_ITEM["id"],
            "reason": "excluded from C0 (continuous-book applicability only)",
            "usd_per_share_if_it_applies": EXCLUDED_REFERENCE_PATH_ITEM["value"],
        },
        {
            "id": "databento_xnas_mbo_data_cost",
            "reason": "operating economics, value UNKNOWN (never zero)",
            "usd_per_share_if_it_applies": None,
        },
        {
            "id": "nasdaq_historical_itch_license_cost",
            "reason": "operating economics, value UNKNOWN (never zero)",
            "usd_per_share_if_it_applies": None,
        },
    ]
    table["note"] = (
        "C1 has no assigned probability distribution. Unknown is never zero: the two operating-"
        "economics items stay unresolved and are named, not dropped."
    )
    return table


def _print_summary(results: Mapping) -> None:
    decision = results["decision"]
    coverage = results["coverage"]
    print("== frozen auction materiality (branch B, TUP-NASDAQ-CLOSE-H4-LATENOII-AGG) ==")
    print(
        "coverage (input availability): {:.4f}  (floor {}, {} of {} universe-qualified symbols "
        "with a valid Closing Cross)".format(
            coverage["input_availability_ratio"] or 0.0,
            coverage["floor"],
            coverage["input_availability_numerator"],
            coverage["denominator_symbols_with_valid_closing_cross"],
        )
    )
    print(
        "signal-defined population     : {:.4f}  ({} symbols; frozen N/O/P direction rule)".format(
            coverage["signal_scope_ratio"] or 0.0, coverage["signal_defined_symbols"]
        )
    )
    print(
        "analysed symbols              : {}  (of {} in the denominator)".format(
            coverage["analysed_symbols"], coverage["denominator_symbols_with_valid_closing_cross"]
        )
    )
    print(
        "gross executable capture    : {:.4f} bps (mean), {:.6f} USD/share".format(
            decision["gross_bps_mean"] or 0.0, decision["gross_usd_per_share_mean"] or 0.0
        )
    )
    print(
        "uncertainty (clustered CI)  : [{:.6f}, {:.6f}] USD/share".format(
            decision["uncertainty_lo_usd"] or 0.0, decision["uncertainty_hi_usd"] or 0.0
        )
    )
    print(
        "structural cost C0          : {:.6f} USD/share ({:.4f} bps)".format(
            decision["c0_usd_per_share_mean"] or 0.0,
            results["executable_capture"]["pooled_c0_bps"]["mean"] or 0.0,
        )
    )
    print(
        "break-even residual C*      : {:.6f} USD/share ({:.4f} bps)".format(
            decision["c_star_usd_per_share"] or 0.0,
            results["executable_capture"]["pooled_c_star_bps"]["mean"] or 0.0,
        )
    )
    print(
        "mechanism (side-signed)     : {:.4f} bps".format(
            results["mechanism_metric"]["pooled_side_signed_bps"]["mean"] or 0.0
        )
    )
    print("DECISION                    : {}".format(decision["verdict"]))
    if decision.get("clauses"):
        print("                              clauses={}".format(",".join(decision["clauses"])))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="stage", required=True)
    extract = sub.add_parser("extract", help="reconstruct entry prints from the retained window")
    extract.add_argument("--window", default=certificate.WINDOW_ARTIFACT)
    extract.add_argument("--extract", required=True, help="certificate per-symbol extract JSON")
    extract.add_argument("--out", required=True)
    extract.set_defaults(func=stage_extract)
    measure = sub.add_parser("measure", help="compute the frozen measurement")
    measure.add_argument("--extract", required=True, help="certificate per-symbol extract JSON")
    measure.add_argument("--entries", required=True, help="entry-print JSON from the extract stage")
    measure.add_argument("--out", required=True)
    measure.set_defaults(func=stage_measure)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
