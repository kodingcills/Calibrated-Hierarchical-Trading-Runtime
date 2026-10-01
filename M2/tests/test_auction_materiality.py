"""Fixtures for the auction measurement-window certificate and the frozen measurement.

Three groups:

* ``CertificateContinuityTest`` — synthetic tapes (built frame by frame with the
  repo's own encoder) exercising the continuity rules, including a splice attack
  of exactly the shape the V2 verification script built against the real tape.
* ``MaterialityUnitTest`` / ``DecisionRuleTest`` — the frozen economics and the
  preregistered verdict clauses on hand-built samples, including the
  coverage-floor and reconstruction clauses and the "significance is reported
  only" invariant.
* ``RealArtefactTest`` — cross-implementation identity against the producer's own
  admission record, and the real splice negative control (the only heavy fixture:
  it re-decodes the retained window, about 40 s, and is skipped when the retained
  artefact is absent).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import struct
import tempfile
import unittest

from M2.src import admission as admission_module
from M2.src import auction_certificate as certificate
from M2.src import auction_materiality as materiality
from M2.src import envelope
from M2.src import ingest

NS = 1_000_000  # one millisecond
SEC = 1_000_000_000
T_1549_50 = certificate.WINDOW_START_NS
T_1550 = certificate.NS_1550
T_1555 = certificate.NS_1555
T_1559 = materiality.ENTRY_DEADLINE_NS

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WINDOW_PATH = os.path.join(REPO, certificate.WINDOW_ARTIFACT)
EXPERIMENT = os.path.join(
    REPO, "M2", "experiments", "M2-BRIDGE-AUCTION-LATENOII-MATERIALITY"
)


# ---------------------------------------------------------------------------
# frame builders (the header layout is ingest's, not re-invented here)
# ---------------------------------------------------------------------------


def make_frame(message_type: int, locate: int, ts_ns: int, fields: dict | None = None) -> bytes:
    length = ingest.MSG_LENGTH[message_type]
    payload = bytearray(length - 1)
    struct.pack_into(">HHIH", payload, 0, locate, 0, (ts_ns >> 16) & 0xFFFFFFFF, ts_ns & 0xFFFF)
    for body_index, data in (fields or {}).items():
        offset = body_index - 1  # body index 0 is the type byte, payload starts at 1
        payload[offset : offset + len(data)] = data
    return ingest.build_itch_frame(message_type, bytes(payload))


def directory_frame(
    locate: int,
    symbol: str = "TEST",
    *,
    ts_ns: int = 3 * 3_600 * NS,
    market_category: str = "Q",
    classification: str = "C",
    sub_type: str = "Z",
    authenticity: str = "P",
    etp_flag: str = "N",
) -> bytes:
    return make_frame(
        0x52,
        locate,
        ts_ns,
        {
            ingest.R_STOCK: symbol.ljust(8).encode("ascii"),
            ingest.R_MARKET_CATEGORY: market_category.encode(),
            ingest.R_FINANCIAL_STATUS: b" ",
            ingest.R_ISSUE_CLASSIFICATION: classification.encode(),
            ingest.R_ISSUE_SUB_TYPE: sub_type.ljust(2).encode(),
            ingest.R_AUTHENTICITY: authenticity.encode(),
            ingest.R_ETP_FLAG: etp_flag.encode(),
        },
    )


def noii_frame(
    locate: int,
    ts_ns: int,
    *,
    symbol: str = "TEST",
    paired: int = 1000,
    imbalance: int = 100,
    direction: str = "B",
    reference_price: int = 1_000_000,
    near_price: int = 995_000,
    far_price: int = 1_005_000,
    cross_type: str = "C",
) -> bytes:
    return make_frame(
        0x49,
        locate,
        ts_ns,
        {
            certificate.I_PAIRED_SHARES: struct.pack(">Q", paired),
            certificate.I_IMBALANCE_SHARES: struct.pack(">Q", imbalance),
            certificate.I_IMBALANCE_DIRECTION: direction.encode(),
            certificate.I_STOCK: symbol.ljust(8).encode("ascii"),
            certificate.I_FAR_PRICE: struct.pack(">I", far_price),
            certificate.I_NEAR_PRICE: struct.pack(">I", near_price),
            certificate.I_CURRENT_REFERENCE_PRICE: struct.pack(">I", reference_price),
            certificate.I_CROSS_TYPE: cross_type.encode(),
        },
    )


def cross_frame(
    locate: int, ts_ns: int, *, symbol: str = "TEST", shares: int = 5000, price: int = 1_010_000
) -> bytes:
    return make_frame(
        0x51,
        locate,
        ts_ns,
        {
            certificate.Q_SHARES: struct.pack(">Q", shares),
            certificate.Q_STOCK: symbol.ljust(8).encode("ascii"),
            certificate.Q_CROSS_PRICE: struct.pack(">I", price),
            certificate.Q_CROSS_TYPE: b"C",
        },
    )


def add_frame(
    locate: int, ts_ns: int, ref: int, side: str, shares: int, price: int, symbol: str = "TEST"
) -> bytes:
    return make_frame(
        0x41,
        locate,
        ts_ns,
        {
            11: struct.pack(">Q", ref),
            19: side.encode(),
            20: struct.pack(">I", shares),
            24: symbol.ljust(8).encode("ascii"),
            32: struct.pack(">I", price),
        },
    )


def delete_frame(locate: int, ts_ns: int, ref: int) -> bytes:
    return make_frame(0x44, locate, ts_ns, {11: struct.pack(">Q", ref)})


def system_event(locate: int, ts_ns: int, code: str = "C") -> bytes:
    return make_frame(0x53, locate, ts_ns, {11: code.encode()})


def frame_ts(frame: bytes) -> int:
    """The exchange timestamp an encoded frame carries."""
    _locate, _tracking, ts_hi, ts_lo = struct.unpack_from(">HHIH", frame, 3)
    return (ts_hi << 16) | ts_lo


def interval_reads(
    locate: int,
    symbol: str,
    *,
    early: tuple[str, int] = ("B", 10),
    late: tuple[str, int] = ("S", 40),
    skip_cycles: tuple[int, ...] = (),
    paired: int = 1000,
    reference: int = 1_000_000,
) -> list[bytes]:
    """A symbol's Closing-Cross reads at the feed's own 10 s cadence (15:50 -> 15:55)."""
    frames = []
    for cycle in range(31):
        if cycle in skip_cycles:
            continue
        direction, imbalance = late if cycle == 30 else early
        frames.append(
            noii_frame(
                locate,
                T_1550 + cycle * 10 * SEC,
                symbol=symbol,
                paired=paired,
                imbalance=imbalance,
                direction=direction,
                reference_price=reference,
            )
        )
    return frames


def write_tape(path: str, frames: list[bytes]) -> str:
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1) as handle:
            for frame in frames:
                handle.write(frame)
    return path


def steady_window(locate: int = 7, count: int = 6, step_ns: int = SEC // 5) -> list[bytes]:
    return [add_frame(locate, T_1549_50 + index * step_ns, 100 + index, "B", 100, 1_000_000) for index in range(count)]


def build_tape(tmp: str, frames: list[bytes]) -> tuple[dict, dict]:
    path = write_tape(os.path.join(tmp, "tape.bin.gz"), frames)
    return certificate.build_certificate(path, min_in_window_messages=1)


class TemporaryTapeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="auction-certificate-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# continuity
# ---------------------------------------------------------------------------


class CertificateContinuityTest(TemporaryTapeTest):
    def test_continuous_window_is_certified(self) -> None:
        frames = [system_event(0, T_1549_50 - 60 * NS, "O")]
        frames += steady_window()
        document, _states = build_tape(self.tmp, frames)
        continuity = document["measurement_window_continuity"]
        self.assertTrue(continuity["monotonic_non_decreasing_exchange_timestamps"])
        self.assertTrue(continuity["max_in_window_gap_within_bound"])
        self.assertEqual(continuity["in_window_message_pairs"], len(frames) - 2)
        self.assertEqual(continuity["max_in_window_gap_ns"], SEC // 5)
        self.assertEqual(document["verdict"]["measurement_window_continuity"], "PASS")

    def test_in_window_hole_is_not_certified(self) -> None:
        frames = steady_window(count=3)
        frames.append(add_frame(7, T_1549_50 + 5_000 * NS, 900, "B", 100, 1_000_000))
        document, _states = build_tape(self.tmp, frames)
        continuity = document["measurement_window_continuity"]
        self.assertGreater(continuity["max_in_window_gap_ns"], certificate.MAX_IN_WINDOW_GAP_NS)
        self.assertEqual(continuity["gaps_over_bound"], 1)
        self.assertEqual(document["verdict"]["measurement_window_continuity"], "FAIL")

    def test_out_of_window_separations_are_not_charged_to_the_window(self) -> None:
        # Stock Directory at 03:0x and the closing system events are ~6 h and ~4 h
        # from the window: legitimate, and out of scope for the in-window bound.
        frames = [directory_frame(7)]
        frames += steady_window()
        frames += [system_event(0, 20 * 3_600 * SEC, "C")]
        document, _states = build_tape(self.tmp, frames)
        continuity = document["measurement_window_continuity"]
        self.assertGreater(continuity["whole_retained_stream_max_gap_ns"], 3_600 * SEC * 3)
        self.assertTrue(continuity["max_in_window_gap_within_bound"])
        self.assertEqual(document["verdict"]["measurement_window_continuity"], "PASS")

    def test_backwards_timestamp_is_not_certified(self) -> None:
        frames = steady_window(count=3)
        frames.append(add_frame(7, T_1549_50 + 100 * NS, 901, "B", 100, 1_000_000))
        document, _states = build_tape(self.tmp, frames)
        self.assertEqual(document["measurement_window_continuity"]["backwards_timestamps"], 1)
        self.assertEqual(document["verdict"]["measurement_window_continuity"], "FAIL")

    def test_spliced_head_and_tail_is_refused_where_markers_pass(self) -> None:
        """The V2 attack shape: head + tail, frame aligned, terminal 'C' kept."""
        head = steady_window(count=3)
        tail = [
            add_frame(7, T_1555 + 400 * NS, 700, "B", 100, 1_000_000),
            add_frame(7, T_1555 + 500 * NS, 701, "B", 100, 1_000_000),
            system_event(0, 20 * 3_600 * SEC, "C"),
        ]
        document, _states = build_tape(self.tmp, head + tail)
        transport = document["transport_markers"]
        continuity = document["measurement_window_continuity"]
        self.assertEqual(transport["gzip_integrity"], "PASS")
        self.assertEqual(transport["framing_errors"], 0)
        self.assertEqual(transport["trailing_bytes_after_frames"], 0)
        self.assertTrue(transport["final_frame_is_C_end_of_messages"])
        self.assertGreater(continuity["max_in_window_gap_ns"], certificate.MAX_IN_WINDOW_GAP_NS)
        self.assertEqual(document["verdict"]["transport_markers"], "PASS")
        self.assertEqual(document["verdict"]["measurement_window_continuity"], "FAIL")
        self.assertEqual(document["verdict"]["overall"], "FAIL")

    def test_empty_measurement_window_is_not_certified(self) -> None:
        # A tape of directory messages and the closing event only: passes the
        # transport markers, carries nothing inside the window.
        frames = [directory_frame(7), directory_frame(8), system_event(0, 20 * 3_600 * SEC, "C")]
        document, _states = build_tape(self.tmp, frames)
        self.assertEqual(document["measurement_window_continuity"]["in_window_messages"], 0)
        self.assertEqual(document["verdict"]["measurement_window_continuity"], "FAIL")
        self.assertEqual(document["verdict"]["transport_markers"], "PASS")


class UniverseAndCoverageTest(TemporaryTapeTest):
    def _tape(self, symbols) -> tuple[dict, list[dict]]:
        frames = []
        for locate, kwargs in symbols:
            frames.append(directory_frame(locate, kwargs.pop("symbol"), **kwargs))
        document, states = build_tape(self.tmp, frames)
        return document, certificate.certificate_rows(states)

    def test_v2_clause_admits_nasdaq_listed_common_stock_only(self) -> None:
        document, rows = self._tape(
            [
                (1, {"symbol": "AAA"}),  # Q, C/Z, P, N -> admitted
                (2, {"symbol": "BBB", "market_category": "S"}),  # admitted
                (3, {"symbol": "CCC", "market_category": "G"}),  # admitted
                (4, {"symbol": "NYN", "market_category": "N"}),  # NYSE-listed -> refused
                (5, {"symbol": "ETF", "etp_flag": "Y"}),  # ETP -> refused
                (6, {"symbol": "SUB", "sub_type": "C"}),  # the old artefact clause
                (7, {"symbol": "WAR", "classification": "W"}),  # warrant -> refused
                (8, {"symbol": "FLG", "authenticity": "T"}),  # test issue -> refused
            ]
        )
        admitted = sorted(row["symbol"] for row in rows if row["universe_qualified"])
        self.assertEqual(admitted, ["AAA", "BBB", "CCC", "SUB"])
        repair = document["universe_repair"]
        self.assertEqual(repair["v1_clause_locates_admitted"], 1)  # only SUB
        self.assertEqual(repair["v2_clause_locates_admitted"], 4)
        self.assertEqual(repair["rule_id_v2"], "NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2")

    def test_direction_ineligibility_is_signal_scope_not_coverage(self) -> None:
        frames = [directory_frame(1, "AAA"), directory_frame(2, "BBB")]
        frames += interval_reads(1, "AAA")
        frames += interval_reads(2, "BBB", early=("N", 0), late=("N", 0))
        frames += [cross_frame(1, 16 * 3_600 * SEC, symbol="AAA")]
        frames += [cross_frame(2, 16 * 3_600 * SEC, symbol="BBB")]
        frames += [system_event(0, 20 * 3_600 * SEC, "C")]
        document, states = build_tape(self.tmp, frames)
        rows = certificate.certificate_rows(states)
        coverage = document["coverage_certificate"]
        self.assertEqual(coverage["denominator_symbols_with_valid_closing_cross_C"], 2)
        self.assertEqual(coverage["numerator_both_C_reads_and_valid_cross"], 2)
        self.assertEqual(coverage["coverage_ratio"], 1.0)
        self.assertTrue(coverage["tolerance_met"])
        scope = coverage["signal_scope"]
        self.assertEqual(scope["signal_defined_symbols"], 1)
        self.assertEqual(scope["signal_defined_ratio"], 0.5)
        self.assertTrue(scope["subfloor"])
        self.assertEqual(scope["exclusion_reason_counts"], {"ineligible_imbalance_direction": 1})
        by_symbol = {row["symbol"]: row for row in rows}
        self.assertTrue(by_symbol["AAA"]["in_numerator"])
        self.assertTrue(by_symbol["AAA"]["signal_defined"])
        self.assertTrue(by_symbol["BBB"]["in_numerator"])
        self.assertFalse(by_symbol["BBB"]["signal_defined"])
        self.assertEqual(by_symbol["BBB"]["signal_scope_reason"], "ineligible_imbalance_direction")

    def test_zero_share_cross_leaves_the_denominator(self) -> None:
        frames = [directory_frame(1, "AAA")]
        frames += interval_reads(1, "AAA")
        frames += [cross_frame(1, 16 * 3_600 * SEC, symbol="AAA", shares=0, price=0)]
        frames += [system_event(0, 20 * 3_600 * SEC, "C")]
        document, states = build_tape(self.tmp, frames)
        coverage = document["coverage_certificate"]
        self.assertEqual(coverage["denominator_symbols_with_valid_closing_cross_C"], 0)
        self.assertIsNone(coverage["coverage_ratio"])
        self.assertEqual(coverage["exclusion_reason_counts"], {"zero_share_closing_cross": 1})
        self.assertEqual(document["verdict"]["coverage_certificate"], "FAIL")
        self.assertIn("COVERAGE_CERTIFICATE", document["verdict"]["failed_checks"])

    def test_cadence_tolerates_the_dissemination_wobble_but_not_a_missed_cycle(self) -> None:
        # The feed disseminates a closing read per symbol every 10 s. A symbol read
        # every cycle passes; one missing a single cycle (a 20 s hole) fails.
        frames = [directory_frame(1, "AAA"), directory_frame(2, "BBB")]
        frames += interval_reads(1, "AAA", skip_cycles=(15,))
        frames += interval_reads(2, "BBB")
        frames += [cross_frame(1, 16 * 3_600 * SEC, symbol="AAA")]
        frames += [cross_frame(2, 16 * 3_600 * SEC, symbol="BBB")]
        frames += [system_event(0, 20 * 3_600 * SEC, "C")]
        _document, states = build_tape(self.tmp, frames)
        rows = {row["symbol"]: row for row in certificate.certificate_rows(states)}
        self.assertEqual(rows["BBB"]["c_reads_signal_interval"], 31)
        self.assertLessEqual(rows["BBB"]["c_max_gap_signal_interval_ns"], certificate.MAX_NOII_C_CADENCE_GAP_NS)
        self.assertTrue(rows["BBB"]["c_cadence_ok"])
        self.assertEqual(rows["AAA"]["c_reads_signal_interval"], 30)
        self.assertGreater(rows["AAA"]["c_max_gap_signal_interval_ns"], certificate.MAX_NOII_C_CADENCE_GAP_NS)
        self.assertFalse(rows["AAA"]["c_cadence_ok"])

    def test_read_selection_uses_the_frozen_fallback(self) -> None:
        frames = [
            directory_frame(1, "AAA"),
            noii_frame(1, T_1550 - 30 * NS, symbol="AAA", imbalance=5, direction="B"),
            noii_frame(1, T_1550 - 10 * NS, symbol="AAA", imbalance=9, direction="B"),
            noii_frame(1, T_1555 - 2 * NS, symbol="AAA", imbalance=20, direction="S"),
            noii_frame(1, T_1555 + NS, symbol="AAA", imbalance=99, direction="S"),
        ]
        _document, states = build_tape(self.tmp, frames)
        early, late = certificate.select_reads(states[1])
        self.assertEqual(early["imbalance_shares"], 9)  # last at or before 15:50
        self.assertEqual(late["imbalance_shares"], 20)  # last at or before 15:55, not the later one

        frames = [
            directory_frame(1, "AAA"),
            noii_frame(1, T_1550 + 3 * NS, symbol="AAA", imbalance=7, direction="B"),
            noii_frame(1, T_1555, symbol="AAA", imbalance=8, direction="B"),
        ]
        _document, states = build_tape(self.tmp, frames)
        early, _late = certificate.select_reads(states[1])
        self.assertEqual(early["imbalance_shares"], 7)  # first read after the boundary


# ---------------------------------------------------------------------------
# measurement: books, economics, states, bootstrap, verdict
# ---------------------------------------------------------------------------


def extract_row(
    locate: int,
    symbol: str,
    *,
    d1550: str = "S",
    imb1550: int = 100,
    d1555: str = "B",
    imb1555: int = 300,
    paired_1555: int = 1000,
    reference: int = 1_000_000,
    cross: int = 1_010_000,
    near: int = 995_000,
    far: int = 1_005_000,
    in_denominator: bool = True,
    reason: str = "",
) -> dict:
    return {
        "locate": locate,
        "symbol": symbol,
        "universe_qualified": True,
        "directory_failure": "",
        "closing_cross_valid": True,
        "closing_cross_shares": 5000,
        "closing_cross_price_raw": cross,
        "closing_cross_ts_ns": 16 * 3_600 * NS,
        "read_1550_ts_ns": T_1550 + NS,
        "read_1550_source": "FIRST_AFTER",
        "read_1550_paired_shares": 900,
        "read_1550_imbalance_shares": imb1550,
        "read_1550_direction": d1550,
        "read_1550_reference_price_raw": reference,
        "read_1550_near_price_raw": near,
        "read_1550_far_price_raw": far,
        "read_1555_ts_ns": T_1555,
        "read_1555_paired_shares": paired_1555,
        "read_1555_imbalance_shares": imb1555,
        "read_1555_direction": d1555,
        "read_1555_reference_price_raw": reference,
        "read_1555_near_price_raw": near,
        "read_1555_far_price_raw": far,
        "in_denominator": in_denominator,
        "in_numerator": in_denominator,
        "signal_defined": in_denominator,
        "exclusion_reason": reason,
        "signal_scope_reason": "",
    }


def entry(locate: int, symbol: str, bid: int, ask: int, ts: int | None = None) -> dict:
    ts = T_1555 + 200 * NS if ts is None else ts
    return {
        "locate": locate,
        "symbol": symbol,
        "entry_ts_ns": ts,
        "entry_ts": "15:55:00.000000200",
        "best_bid_raw": bid,
        "best_ask_raw": ask,
        "within_deadline": ts <= T_1559,
    }


class MaterialityCostTest(unittest.TestCase):
    def test_c0_contains_only_the_two_verified_sale_side_charges(self) -> None:
        envelope_c0 = materiality.c0_envelope()
        ids = sorted(item.id for item in envelope_c0.c0_items())
        self.assertEqual(ids, ["finra_trading_activity_fee", "sec_section_31_fee"])
        for item in envelope_c0.c0_items():
            envelope.assert_c0(item)
            self.assertEqual(item.side, "sell")
            self.assertTrue(item.provenance.effective_period)

    def test_remove_liquidity_fee_is_not_in_c0(self) -> None:
        envelope_c0 = materiality.c0_envelope()
        self.assertNotIn(
            "nasdaq_remove_liquidity_fee", [item.id for item in envelope_c0.items]
        )
        self.assertIn(
            "Closing Cross exit",
            materiality.EXCLUDED_REFERENCE_PATH_ITEM["excluded_from_c0_reason"],
        )

    def test_c0_is_the_sale_leg_only_and_scales_with_price(self) -> None:
        envelope_c0 = materiality.c0_envelope()
        low = envelope_c0.structural_c0_usd(envelope.Basis(quantity=1.0, price_usd=10.0))
        high = envelope_c0.structural_c0_usd(envelope.Basis(quantity=1.0, price_usd=100.0))
        taf = 0.000195
        self.assertAlmostEqual(low, 20.6e-6 * 10.0 + taf, places=12)
        self.assertAlmostEqual(high, 20.6e-6 * 100.0 + taf, places=12)
        # A 100-share order is far below the TAF cap, so the cap is inert here.
        self.assertLess(100 * taf, 9.79)

    def test_c0_to_bps_refuses_without_a_price(self) -> None:
        with self.assertRaises(envelope.MissingUnitInput):
            envelope.convert(
                0.001, envelope.UNIT_USD, envelope.UNIT_BPS, envelope.Basis(quantity=1.0)
            )


class SignalAndCaptureTest(unittest.TestCase):
    def rows(self, records, entries) -> list[dict]:
        rows, _excluded = materiality.per_symbol_rows(
            records, entries, {}, c0=materiality.c0_envelope()
        )
        return rows

    def test_positive_signal_buys_the_ask(self) -> None:
        record = extract_row(1, "AAA", d1550="S", imb1550=100, d1555="B", imb1555=300)
        rows = self.rows([record], {1: entry(1, "AAA", 999_000, 1_001_000)})
        row = rows[0]
        self.assertEqual(row["signal"], envelope.SIGNAL_POSITIVE)
        self.assertEqual(row["delta_imbalance"], 400)
        self.assertAlmostEqual(row["best_ask_usd"], 100.1)
        self.assertAlmostEqual(row["entry_price_usd"], 100.1)  # the ask, not the mid
        self.assertAlmostEqual(row["entry_spread_usd"], 0.2)
        self.assertAlmostEqual(row["gross_usd_per_share"], 101.0 - 100.1)
        # The sell leg is the Closing Cross exit, so C0 is charged on it.
        expected_c0 = 20.6e-6 * 101.0 + 0.000195
        self.assertAlmostEqual(row["c0_usd_per_share"], expected_c0, places=12)
        self.assertAlmostEqual(
            row["c_star_usd_per_share"], row["gross_usd_per_share"] - expected_c0, places=12
        )

    def test_negative_signal_sells_the_bid(self) -> None:
        record = extract_row(2, "BBB", d1550="B", imb1550=100, d1555="S", imb1555=300)
        rows = self.rows([record], {2: entry(2, "BBB", 999_000, 1_001_000)})
        row = rows[0]
        self.assertEqual(row["signal"], envelope.SIGNAL_NEGATIVE)
        self.assertAlmostEqual(row["entry_price_usd"], 99.9)  # the bid
        self.assertAlmostEqual(row["gross_usd_per_share"], 99.9 - 101.0)
        expected_c0 = 20.6e-6 * 99.9 + 0.000195  # the sell leg is the entry here
        self.assertAlmostEqual(row["c0_usd_per_share"], expected_c0, places=12)

    def test_mechanism_metric_is_side_signed(self) -> None:
        record = extract_row(3, "CCC", d1550="S", imb1550=50, d1555="S", imb1555=150)
        rows = self.rows([record], {3: entry(3, "CCC", 999_000, 1_001_000)})
        raw = (101.0 - 100.0) / 100.0 * 10_000
        self.assertAlmostEqual(rows[0]["mechanism_displacement_bps"], raw)
        self.assertAlmostEqual(rows[0]["mechanism_side_signed_bps"], -raw)

    def test_scaled_signal_uses_max_paired_shares_one(self) -> None:
        record = extract_row(4, "DDD", paired_1555=0, d1550="S", imb1550=0, d1555="B", imb1555=7)
        rows = self.rows([record], {4: entry(4, "DDD", 999_000, 1_001_000)})
        self.assertEqual(rows[0]["paired_shares_1555"], 1)
        self.assertEqual(rows[0]["scaled_delta_imbalance"], 7.0)

    def test_exclusions_are_named(self) -> None:
        records = [
            extract_row(1, "SAME", d1550="B", imb1550=10, d1555="B", imb1555=10),  # zero delta
            extract_row(2, "NODIR", d1550="N", imb1550=0, d1555="B", imb1555=10),
            extract_row(3, "NOENT", d1550="S", imb1550=1, d1555="B", imb1555=2),
            extract_row(4, "LATE", d1550="S", imb1550=1, d1555="B", imb1555=2),
            extract_row(5, "OUT", in_denominator=False, reason="zero_share_closing_cross"),
        ]
        entries = {
            3: entry(3, "NOENT", 999_000, 1_001_000, ts=T_1559 + NS),
            4: entry(4, "LATE", 999_000, 1_001_000, ts=T_1559 - NS),
        }
        rows, excluded = materiality.per_symbol_rows(
            records, entries, {}, c0=materiality.c0_envelope()
        )
        reasons = {row["symbol"]: row["reason"] for row in excluded}
        self.assertEqual(reasons["SAME"], "zero_signed_imbalance_change")
        self.assertEqual(reasons["NODIR"], "ineligible_imbalance_direction")
        self.assertEqual(reasons["NOENT"], "entry_quote_after_deadline")
        self.assertEqual(reasons["OUT"], "zero_share_closing_cross")
        self.assertEqual([row["symbol"] for row in rows], ["LATE"])


class QuartileStateTest(unittest.TestCase):
    def test_cut_points_come_from_the_signal_side_only(self) -> None:
        rows = [
            {"locate": index, "scaled_delta_imbalance": value}
            for index, value in enumerate([-3.0, -1.0, 0.5, 1.0, 2.0, 4.0])
        ]
        states = materiality.quartile_states(rows)
        import numpy as np

        values = np.array([row["scaled_delta_imbalance"] for row in rows])
        self.assertEqual(states["edges"], [float(np.quantile(values, q)) for q in (0.25, 0.5, 0.75)])
        self.assertEqual(sorted(states["assignment"].values()).count("Q1_LOWEST"), 2)
        self.assertEqual(sorted(states["assignment"].values()).count("Q4_HIGHEST"), 2)
        # An outcome column present on the rows changes nothing: no outcome enters.
        augmented = [dict(row, gross_bps=999.0) for row in rows]
        self.assertEqual(
            materiality.quartile_states(augmented)["edges"], states["edges"]
        )


class BootstrapTest(unittest.TestCase):
    def rows(self, count: int = 40) -> list[dict]:
        return [
            {
                "locate": index,
                "gross_usd_per_share": 0.01 * (index % 7) - 0.02,
                "gross_bps": float(index % 5),
                "mechanism_side_signed_bps": float(index % 11) - 5.0,
                "c0_usd_per_share": 0.0003,
            }
            for index in range(count)
        ]

    def test_bootstrap_is_deterministic_and_brackets_the_mean(self) -> None:
        rows = self.rows()
        first = materiality.cluster_bootstrap(rows, "gross_bps", resamples=500, seed=7)
        second = materiality.cluster_bootstrap(rows, "gross_bps", resamples=500, seed=7)
        self.assertEqual(first, second)
        self.assertLessEqual(first["lo"], first["mean"])
        self.assertGreaterEqual(first["hi"], first["mean"])
        other = materiality.cluster_bootstrap(rows, "gross_bps", resamples=500, seed=8)
        self.assertNotEqual(first["resample_means_percentiles"], other["resample_means_percentiles"])

    def test_more_resamples_shrink_the_percentile_noise(self) -> None:
        rows = self.rows(200)
        coarse = materiality.cluster_bootstrap(rows, "gross_bps", resamples=200, seed=7)
        fine = materiality.cluster_bootstrap(rows, "gross_bps", resamples=4000, seed=7)
        self.assertAlmostEqual(coarse["lo"], fine["lo"], delta=0.2)
        self.assertAlmostEqual(coarse["hi"], fine["hi"], delta=0.2)


class DecisionRuleTest(unittest.TestCase):
    def rows(self, values: list[float], c0: float = 0.0003) -> list[dict]:
        return [
            {
                "locate": index,
                "gross_usd_per_share": value,
                "gross_bps": value * 100.0,
                "mechanism_side_signed_bps": value * 100.0,
                "c0_usd_per_share": c0,
                "c0_bps": 0.0,
                "c_star_bps": 0.0,
            }
            for index, value in enumerate(values)
        ]

    def decision(
        self, rows, coverage_ratio: float = 1.0, far_ratio: float = 1.0, signal_subfloor: bool = False
    ) -> dict:
        return materiality.decision_for(
            rows,
            coverage={"ratio": coverage_ratio, "input_availability_ratio": coverage_ratio},
            reconstruction={"within_far_band_ratio": far_ratio},
            signal_scope={"ratio": 0.52 if signal_subfloor else 1.0, "subfloor": signal_subfloor},
        )

    def test_negative_capture_kills(self) -> None:
        decision = self.decision(self.rows([-0.02] * 30))
        self.assertEqual(decision["verdict"], envelope.VERDICT_KILL)
        self.assertLess(decision["c_star_usd_per_share"], 0)

    def test_tiny_positive_capture_kills_on_the_upper_bound(self) -> None:
        decision = self.decision(self.rows([0.0001] * 15 + [0.0002] * 15))
        self.assertGreater(decision["gross_usd_per_share_mean"], 0)
        self.assertEqual(decision["rule_verdict"], envelope.VERDICT_KILL)
        self.assertLessEqual(decision["uncertainty_hi_usd"], decision["c0_usd_per_share_mean"])

    def test_decisive_positive_capture_survives_provisionally(self) -> None:
        decision = self.decision(self.rows([0.05] * 30))
        self.assertEqual(decision["verdict"], envelope.VERDICT_SURVIVE)

    def test_coverage_floor_failure_is_named_and_supersedes_the_rule(self) -> None:
        decision = self.decision(self.rows([-0.02] * 30), coverage_ratio=0.52)
        self.assertEqual(decision["verdict"], "INDETERMINATE_COVERAGE")
        self.assertEqual(decision["clause"], "COVERAGE_FLOOR")
        self.assertEqual(decision["rule_verdict"], envelope.VERDICT_KILL)

    def test_unvalidated_reconstruction_is_named(self) -> None:
        decision = self.decision(self.rows([-0.02] * 30), far_ratio=0.10)
        self.assertEqual(decision["verdict"], envelope.VERDICT_INDETERMINATE)
        self.assertEqual(decision["clause"], "ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED")

    def test_signal_scope_subfloor_is_attached_without_rescuing_or_hiding(self) -> None:
        killed = self.decision(self.rows([-0.02] * 30), signal_subfloor=True)
        self.assertEqual(killed["verdict"], envelope.VERDICT_KILL)
        self.assertIn("SIGNAL_SCOPE_SUBFLOOR", killed["clauses"])
        self.assertIsNone(killed["clause"])
        self.assertIn("no signed imbalance", killed["signal_scope_clause_note"])
        clean = self.decision(self.rows([-0.02] * 30))
        self.assertEqual(clean["clauses"], [])

    def test_significance_never_moves_the_verdict(self) -> None:
        steady = self.rows([0.0004] * 30)
        wild = self.rows([0.0004] * 15 + [0.4] * 15)
        self.assertEqual(
            self.decision(steady)["verdict"], self.decision(wild)["verdict"]
        )
        self.assertNotEqual(
            envelope.significance_against_zero(1.0, 0.01), envelope.significance_against_zero(1.0, 1.0)
        )


# ---------------------------------------------------------------------------
# real artefacts
# ---------------------------------------------------------------------------


@unittest.skipUnless(os.path.exists(WINDOW_PATH), "retained window not present")
class RealWindowTest(unittest.TestCase):
    def test_real_splice_attack_is_refused_by_the_continuity_rules(self) -> None:
        control = certificate.splice_negative_control(WINDOW_PATH)
        self.assertEqual(control["transport_markers_verdict"], "PASS")
        self.assertEqual(control["transport_markers"]["gzip_integrity"], "PASS")
        self.assertFalse(control["transport_markers"]["framing_errors"])
        self.assertTrue(control["continuity_verdict"] == "FAIL")
        self.assertTrue(control["flagged"])
        self.assertLess(control["spliced_percent_of_pristine"], 1.0)
        self.assertIn("ARTEFACT_IDENTITY", control["failed_checks"])


@unittest.skipUnless(os.path.exists(EXPERIMENT), "sealed experiment artefacts not present")
class SealedArtefactTest(unittest.TestCase):
    def test_certificate_reproduces_the_producer_counters(self) -> None:
        with open(os.path.join(REPO, "M2/data/derived_auction/2026-06-12/admission.json")) as handle:
            producer = json.load(handle)
        with open(os.path.join(EXPERIMENT, "certificate.json")) as handle:
            document = json.load(handle)
        transport = document["transport_markers"]
        continuity = document["measurement_window_continuity"]
        self.assertEqual(transport["frames"], producer["retained_message_count"])
        self.assertEqual(continuity["in_window_messages"], producer["window_message_count"])
        self.assertEqual(
            document["universe_repair"]["counts"]["stock_directory_messages"],
            producer["message_type_histogram_whole"]["stock_directory"],
        )
        self.assertEqual(
            document["universe_repair"]["counts"]["closing_cross_prints"],
            producer["message_type_histogram_window"]["cross_trade"],
        )
        self.assertEqual(
            document["universe_repair"]["counts"]["noii_c_reads"],
            producer["message_type_histogram_window"]["noii"],
        )
        self.assertEqual(
            transport["window_artifact_sha256"], producer["window_artifact_sha256"]
        )
        self.assertTrue(transport["decoded_bytes"] > producer["window_artifact_bytes"])

    def test_named_coverage_clause_is_recorded(self) -> None:
        with open(os.path.join(EXPERIMENT, "certificate.json")) as handle:
            document = json.load(handle)
        coverage = document["coverage_certificate"]
        self.assertEqual(coverage["tolerance"], 0.95)
        self.assertTrue(coverage["tolerance_met"])
        scope = coverage["signal_scope"]
        self.assertLess(scope["signal_defined_ratio"], 1.0)
        self.assertEqual(
            scope["signal_defined_symbols"] + len(scope["excluded_by_identity"]),
            coverage["denominator_symbols_with_valid_closing_cross_C"],
        )




# ---------------------------------------------------------------------------
# AUCTION v2 contract fixtures (the engine checks the v2 key adds)
# ---------------------------------------------------------------------------


CONTRACT_CONTINUITY_MARKERS = admission_module.AUCTION_CONTRACT_V2["continuity_markers"]


def _role_file(root: str, name: str, role: str, payload: bytes = b"fixture") -> dict:
    path = os.path.join(root, name)
    with open(path, "wb") as handle:
        handle.write(payload)
    return {
        "role": role,
        "path": name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "status": "complete",
    }


def build_v2_manifest(root: str, certificate_document: dict, *, claim: str = "echo") -> dict:
    """A minimal AUCTION v2 manifest whose cited evidence is ``certificate_document``.

    ``claim`` selects what the manifest says about the window: ``echo`` repeats the
    certificate, ``tamper`` claims a clean window the certificate does not evidence.
    """
    with open(os.path.join(root, "certificate.json"), "w", encoding="utf-8") as handle:
        json.dump(certificate_document, handle)
    with open(os.path.join(root, "certificate.json"), "rb") as handle:
        certificate_bytes = handle.read()
    files = [_role_file(root, "certificate.json", "continuity_certificate", certificate_bytes)]
    for name, role in (
        ("raw.bin", "raw"),
        ("noii_reads.bin", "noii_reads"),
        ("cross_trades.bin", "cross_trades"),
        ("universe.bin", "universe"),
        ("admission.json", "admission_record"),
        ("missingness.json", "coverage_missingness"),
        ("entry_prints.bin", "entry_prints"),
    ):
        files.append(_role_file(root, name, role))

    continuity = certificate_document["measurement_window_continuity"]
    verdict = certificate_document["verdict"]
    declared_verdict = "PASS" if claim == "tamper" else verdict["measurement_window_continuity"]
    declared = {
        "window_start": continuity["window"]["start"],
        "window_end": continuity["window"]["end"],
        "monotonic_non_decreasing_exchange_timestamps": True if claim == "tamper" else continuity["monotonic_non_decreasing_exchange_timestamps"],
        "backwards_timestamps": 0 if claim == "tamper" else continuity["backwards_timestamps"],
        "in_window_messages": continuity["in_window_messages"],
        "in_window_message_pairs": continuity["in_window_message_pairs"],
        "max_in_window_gap_ns": 0 if claim == "tamper" else continuity["max_in_window_gap_ns"],
        "max_in_window_gap_bound_ns": CONTRACT_CONTINUITY_MARKERS["max_in_window_gap_bound_ns"],
        "in_window_messages_at_least": CONTRACT_CONTINUITY_MARKERS["in_window_messages_at_least"],
        "splice_negative_control": "FLAGGED",
        "transport_markers_prove_original_session_completeness": False,
        "out_of_window_holes": verdict["out_of_window_holes"],
        "certificate_verdict": declared_verdict,
    }
    coverage = certificate_document["coverage_certificate"]
    return {
        "manifest_id": "FIXTURE-AUCTION-V2",
        "dataset_id": "NASDAQ-TOTALVIEW-ITCH50-FIXTURE",
        "branch": "AUCTION",
        "source": {
            "source_id": "FIXTURE",
            "provider": "fixture",
            "retrieved_at_utc": "2026-09-30T00:00:00Z",
            "access_terms": "fixture",
        },
        "schema": {"contract_id": "ITCH50-BINARY-V50-20230428", "format": "binary"},
        "session": {
            "coverage_date": "2026-06-12",
            "timezone": "America/New_York",
            "session_open_ns": continuity["window"]["start_ns"],
            "session_close_ns": continuity["window"]["end_ns"],
            "window_start_unix": continuity["window"]["start_ns"],
            "window_end_unix": continuity["window"]["end_ns"],
            "terminating_frame_present": False,
            "final_system_event": "C",
            "completeness_markers": {
                "gzip_integrity": "PASS",
                "received_bytes_equals_content_range_total": True,
                "framing_errors": 0,
                "trailing_bytes_after_frames": 0,
                "final_frame_is_C_end_of_messages": True,
                "window_continuity_certificate": verdict["measurement_window_continuity"],
                "window_coverage_certificate": verdict["coverage_certificate"],
                "splice_negative_control": "FLAGGED",
                "transport_markers_prove_original_session_completeness": False,
                "out_of_window_holes": verdict["out_of_window_holes"],
            },
            "measurement_window_continuity": declared,
        },
        "files": files,
        "fields": [
            {"name": "timestamp_ns", "type": "int64", "semantics": "nanoseconds_since_midnight", "identity": "message_timestamp", "timezone": "America/New_York"},
            {"name": "locate", "type": "int32", "semantics": "day-unique Stock Locate code", "identity": "stock_locate", "timezone": "America/New_York"},
            {"name": "symbol", "type": "utf8", "semantics": "Stock Directory symbol", "identity": "same-day symbol", "timezone": "America/New_York"},
            {"name": "imbalance_shares", "type": "int64", "semantics": "NOII imbalance", "identity": "noii_imbalance_shares", "timezone": "America/New_York"},
            {"name": "cross_price", "type": "int64", "semantics": "Cross Trade price", "identity": "cross_trade_price", "timezone": "America/New_York"},
            {"name": "cross_type", "type": "utf8", "semantics": "Cross Type", "identity": "cross_type", "timezone": "America/New_York"},
            {"name": "reference_price", "type": "int64", "semantics": "NOII Current Reference Price", "identity": "noii_current_reference_price", "timezone": "America/New_York"},
        ],
        "instrument": {"symbol": "NASDAQ-CLOSE-CROSS-UNIVERSE", "venue": "NASDAQ", "members_count": 2},
        "universe": {
            "rule_id": "NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2",
            "pit": True,
            "members": ["AAA", "BBB"],
        },
        "records": {
            "timestamps": [T_1550, T_1555, 16 * 3_600 * SEC],
            "keys": ["AAA|1550", "AAA|1555", "AAA|CROSS"],
            "symbols": ["AAA", "AAA", "AAA"],
        },
        "intervals": [
            {"id": "15:50_ET_NOII", "present": True, "count": 2},
            {"id": "15:55_ET_NOII", "present": True, "count": 2},
            {"id": "CLOSING_CROSS_16:00_ET", "present": True, "count": 2},
        ],
        "coverage": {
            "qualified": coverage["denominator_symbols_with_valid_closing_cross_C"],
            "admitted": coverage["numerator_both_C_reads_and_valid_cross"],
            "ratio": coverage["coverage_ratio"],
            "tolerance": 0.95,
            "certificate_id": certificate_document["certificate_id"],
            "coverage_ratio": coverage["coverage_ratio"],
        },
    }


class AuctionV2ContractTest(TemporaryTapeTest):
    """The v2 key's own checks, including the splice attack as a fixture."""

    def evaluate(self, manifest: dict) -> dict:
        return admission_module.evaluate(
            manifest,
            admission_module.contract_for("AUCTION_V2"),
            admission_module.Context(root=self.tmp),
        )

    def clean_certificate(self) -> dict:
        """A tape that satisfies continuity AND coverage: dense book messages, reads
        at the feed's 10 s cadence, a valid cross per symbol."""
        events: dict[int, list[bytes]] = {}
        for locate, symbol in ((1, "AAA"), (2, "BBB")):
            for tick in range(0, 6100):  # to the closing cross, so no in-window hole
                ts = T_1549_50 + tick * 100 * NS
                events.setdefault(ts, []).append(
                    add_frame(locate, ts, 100 + tick, "B", 100, 1_000_000, symbol=symbol)
                )
            for frame in interval_reads(locate, symbol):
                events.setdefault(frame_ts(frame), []).append(frame)
            events.setdefault(16 * 3_600 * SEC, []).append(
                cross_frame(locate, 16 * 3_600 * SEC, symbol=symbol)
            )
        frames = [directory_frame(1, "AAA"), directory_frame(2, "BBB")]
        for ts in sorted(events):
            frames.extend(events[ts])
        frames.append(system_event(0, 20 * 3_600 * SEC, "C"))
        document, _states = build_tape(self.tmp, frames)
        return document

    def spliced_certificate(self) -> dict:
        head = steady_window(locate=1, count=3)
        tail = [
            add_frame(1, T_1555 + 400 * NS, 700, "B", 100, 1_000_000),
            system_event(0, 20 * 3_600 * SEC, "C"),
        ]
        document, _states = build_tape(self.tmp, head + tail)
        return document

    def test_valid_v2_manifest_is_admitted(self) -> None:
        result = self.evaluate(build_v2_manifest(self.tmp, self.clean_certificate()))
        self.assertEqual(result["state"], admission_module.DATA_VALID, result["reasons"])
        self.assertEqual(result["contract_id"], "ADMISSION-AUCTION-v2")

    def test_v1_contract_is_untouched_by_the_v2_key(self) -> None:
        self.assertIs(
            admission_module.BUILTIN_CONTRACTS["AUCTION"], admission_module.AUCTION_CONTRACT
        )
        self.assertNotIn(
            "require_measurement_window_continuity", admission_module.AUCTION_CONTRACT
        )
        self.assertNotIn("require_coverage_certificate", admission_module.AUCTION_CONTRACT)
        # The v2 key registers a new contract and extends the registry additively.
        self.assertEqual(
            admission_module.BUILTIN_CONTRACTS["AUCTION_V2"]["contract_id"],
            "ADMISSION-AUCTION-v2",
        )
        self.assertEqual(len(admission_module.CHECKS), len(admission_module.CHECK_IDS))

    def test_splice_attack_passes_the_transport_markers_and_is_still_refused(self) -> None:
        document = self.spliced_certificate()
        transport = document["transport_markers"]
        self.assertEqual(document["verdict"]["transport_markers"], "PASS")
        self.assertEqual(transport["gzip_integrity"], "PASS")
        self.assertEqual(transport["framing_errors"], 0)
        self.assertEqual(document["verdict"]["measurement_window_continuity"], "FAIL")
        result = self.evaluate(build_v2_manifest(self.tmp, document))
        self.assertNotEqual(result["state"], admission_module.DATA_VALID)
        checks = {(reason["check"], reason["severity"]) for reason in result["reasons"]}
        self.assertIn(("session.continuity", "INVALID"), checks)

    def test_manifest_claim_disagreeing_with_its_certificate_is_invalid(self) -> None:
        result = self.evaluate(
            build_v2_manifest(self.tmp, self.spliced_certificate(), claim="tamper")
        )
        self.assertEqual(result["state"], admission_module.DATA_INVALID)
        reasons = [reason for reason in result["reasons"] if reason["check"] == "session.continuity"]
        self.assertTrue(reasons)
        self.assertIn("differs from the certificate", " ".join(r["detail"] for r in reasons))

    def test_missing_certificate_object_is_incomplete(self) -> None:
        manifest = build_v2_manifest(self.tmp, self.clean_certificate())
        os.remove(os.path.join(self.tmp, "certificate.json"))
        result = self.evaluate(manifest)
        self.assertEqual(result["state"], admission_module.DATA_INCOMPLETE)
        checks = {reason["check"] for reason in result["reasons"]}
        self.assertIn("session.continuity", checks)
        self.assertIn("coverage.certificate", checks)

    def test_coverage_certificate_below_the_floor_is_refused(self) -> None:
        document = self.clean_certificate()
        document["coverage_certificate"]["coverage_ratio"] = 0.50
        document["coverage_certificate"]["tolerance_met"] = False
        manifest = build_v2_manifest(self.tmp, document)
        manifest["coverage"]["ratio"] = 0.50
        manifest["coverage"]["admitted"] = 1
        manifest["coverage"]["qualified"] = 2
        manifest["coverage"]["coverage_ratio"] = 0.50
        result = self.evaluate(manifest)
        self.assertNotEqual(result["state"], admission_module.DATA_VALID)
        reasons = {reason["check"] for reason in result["reasons"]}
        self.assertIn("coverage.certificate", reasons)
        self.assertIn("coverage.contract", reasons)


class MeasureStageEndToEndTest(TemporaryTapeTest):
    """The frozen measurement runs end to end on a hand-built extract."""

    def write_inputs(self, records, entries, snapshot) -> tuple[str, str]:
        extract_path = os.path.join(self.tmp, "extract.json")
        entries_path = os.path.join(self.tmp, "entries.json")
        with open(extract_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle)
        with open(entries_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "generated_utc": "2026-09-30T00:00:00Z",
                    "window_artifact": "fixture",
                    "entry_prints": entries,
                    "snapshot_mid2_at_1555": {str(k): v for k, v in snapshot.items()},
                    "diagnostics": {"fixture": True},
                },
                handle,
            )
        return extract_path, entries_path

    def test_measure_stage_reports_the_frozen_fields_deterministically(self) -> None:
        records = []
        entries = []
        snapshot = {}
        for index in range(6):
            locate = index + 1
            symbol = f"SYM{index}"
            records.append(
                extract_row(
                    locate,
                    symbol,
                    d1550="S",
                    imb1550=100 + index,
                    d1555="B",
                    imb1555=300 + index * 50,
                    paired_1555=1000 + index,
                    cross=1_010_000 + index * 1000,
                )
            )
            entries.append(entry(locate, symbol, 999_000, 1_001_000))
            snapshot[locate] = 2_000_000 + index  # mid 100.000x, inside the near/far band
        extract_path, entries_path = self.write_inputs(records, entries, snapshot)
        out = os.path.join(self.tmp, "results.json")
        self.assertEqual(
            materiality.main(
                ["measure", "--extract", extract_path, "--entries", entries_path, "--out", out]
            ),
            0,
        )
        with open(out, encoding="utf-8") as handle:
            results = json.load(handle)
        self.assertEqual(len(results["per_symbol"]), 6)
        self.assertEqual(results["coverage"]["input_availability_ratio"], 1.0)
        self.assertEqual(results["coverage"]["analysed_symbols"], 6)
        self.assertAlmostEqual(
            results["decision"]["gross_usd_per_share_mean"],
            sum(row["gross_usd_per_share"] for row in results["per_symbol"]) / 6,
            places=12,
        )
        self.assertIn(
            results["decision"]["verdict"],
            {
                envelope.VERDICT_KILL,
                envelope.VERDICT_SURVIVE,
                envelope.VERDICT_INDETERMINATE,
            },
        )
        self.assertEqual(sum(state["n"] for state in results["executable_capture"]["by_state"]), 6)
        c1 = results["c1_sensitivity"]["rows"]
        self.assertEqual([row["c1_usd"] for row in c1], list(materiality.C1_SCENARIO_USD_PER_SHARE))
        self.assertTrue(all(row["survives_floor"] for row in c1))
        self.assertIn("signal_defined", results["signal_scope_liquidity_comparison"])
        self.assertEqual(results["book_reconstruction"]["within_far_band_ratio"], 1.0)
        self.assertIn("clauses", results["decision"])
        out2 = os.path.join(self.tmp, "results2.json")
        materiality.main(
            ["measure", "--extract", extract_path, "--entries", entries_path, "--out", out2]
        )
        with open(out2, encoding="utf-8") as handle:
            second = json.load(handle)
        self.assertEqual(second["decision"]["gross_usd_per_share_mean"], results["decision"]["gross_usd_per_share_mean"])
        self.assertEqual(second["decision"]["uncertainty_lo_usd"], results["decision"]["uncertainty_lo_usd"])
        self.assertEqual(second["executable_capture"]["by_state"], results["executable_capture"]["by_state"])


if __name__ == "__main__":  # pragma: no cover - direct invocation
    unittest.main()
