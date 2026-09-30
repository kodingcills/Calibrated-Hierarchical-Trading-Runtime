"""Adversarial fixtures for the deterministic data-admission engine.

Every fixture below mutates exactly one declared property of a manifest that
otherwise passes, and pins BOTH the verdict and the check id that must fire.
Pinning the check id is what makes the suite load-bearing: if a check is removed
from ``admission.CHECKS`` its reason disappears and the fixture test fails.
``test_every_check_has_a_fixture`` additionally fails if any advertised check
loses its fixture, so the check inventory cannot silently shrink.

The fixtures are synthetic (small files in a temporary directory), so the suite
is deterministic and fast; the engine is exercised against real manifests by the
epoch runner, not here.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from M2.src import admission
from M2.src import ingest

SESSION_OPEN_NS = 34_200_000_000_000  # 09:30:00 ET
SESSION_CLOSE_NS = 57_600_000_000_000  # 16:00:00 ET
BASIS_START_UNIX = 1_688_515_200  # an exact UTC hour

FIXTURE_CONTRACT = {
    "contract_id": "ADMISSION-FIXTURE-v1",
    "branch": "AUCTION",
    "required_sections": [
        "source",
        "schema",
        "session",
        "files",
        "fields",
        "instrument",
        "universe",
        "records",
        "intervals",
        "coverage",
    ],
    "required_source_fields": ["source_id", "provider", "retrieved_at_utc", "access_terms"],
    "expected_schema": "ITCH50-BINARY-V50-20230428",
    "expected_format": "binary",
    "required_file_roles": ["raw", "noii_reads"],
    "require_hashes": True,
    "require_archive_status": True,
    "required_fields": ["timestamp_ns", "locate", "symbol", "imbalance_shares"],
    "field_types": {
        "timestamp_ns": "int64",
        "locate": "int32",
        "symbol": "utf8",
        "imbalance_shares": "int64",
    },
    "type_vocabulary": sorted(admission.TYPE_VOCABULARY),
    "timestamp_field": "timestamp_ns",
    "timestamp_semantics": "nanoseconds_since_midnight",
    "timestamp_identity": "message_timestamp",
    "timezone": "America/New_York",
    "expected_session_date": "2026-06-12",
    "require_terminating_frame": True,
    "required_final_event": "C",
    "require_records": True,
    "require_strict_timestamps": True,
    "require_sequence": True,
    "sequence_start": 1,
    "require_unique_keys": True,
    "required_intervals": ["15:50_ET_NOII", "15:55_ET_NOII"],
    "coverage_tolerance": 0.95,
    "instrument_required": True,
    "allowed_instruments": ["AAPL", "MSFT"],
    "allowed_instrument_prefixes": ["AAP", "MSF"],
    "allowed_venues": ["NASDAQ"],
    "instrument_must_match_universe": True,
    "require_pit_universe": True,
    "universe_rule_id": "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
    "required_objects": [{"id": "calendar", "path": "calendar.json", "min_bytes": 1}],
}


# Variants used by the feed-shape tests: a producer-declared sequence start
# (CME MDP3 packet sequence persists across sessions), a bounded sequence probe,
# and a contract that admits a streamed, unretained upstream source.
DECLARED_START_CONTRACT = {
    key: value for key, value in FIXTURE_CONTRACT.items() if key != "sequence_start"
}
DECLARED_START_CONTRACT["sequence_start_from_manifest"] = True
PROBE_CONTRACT = dict(
    DECLARED_START_CONTRACT, sequence_probe={"head_rows": 2, "tail_rows": 2}
)
UNRETAINED_CONTRACT = dict(FIXTURE_CONTRACT, allow_unretained_files=True)
# Stream completeness: the ITCH delivery carries no zero-length terminating
# frame, so the contract asks for container/parse markers instead, anchored to a
# retained artifact that carries them.
STREAM_CONTRACT = dict(
    FIXTURE_CONTRACT,
    require_terminating_frame=False,
    require_stream_completeness=True,
    stream_completeness_markers={"gzip_integrity": "PASS", "framing_errors": 0},
    completeness_evidence_role="admission_record",
)

PACKET_SEQUENCE_BASIS = (
    "CME MDP3 channel-310 packet sequence: per channel, persists across sessions"
)


def _write(root: str, name: str, payload: bytes) -> dict:
    path = os.path.join(root, name)
    with open(path, "wb") as handle:
        handle.write(payload)
    return {
        "path": name,
        "sha256": ingest.sha256_file(path),
        "bytes": os.path.getsize(path),
    }


def build_valid(root: str) -> dict:
    """A manifest that passes every check of FIXTURE_CONTRACT."""
    raw = _write(root, "raw.bin", b"fixture raw tape bytes")
    noii = _write(root, "noii.json", b'{"reads": 2}')
    admission_record = _write(root, "admission.json", b'{"artifact": "admission"}')
    _write(root, "calendar.json", b'{"sessions": ["2026-06-12"]}')
    return {
        "manifest_id": "FIXTURE-VALID-2026-06-12",
        "dataset_id": "FIXTURE-NASDAQ-2026-06-12",
        "branch": "AUCTION",
        "source": {
            "source_id": "NASDAQ-TOTALVIEW-2026-06-12",
            "provider": "Nasdaq",
            "retrieved_at_utc": "2026-09-29T00:00:00Z",
            "access_terms": "free public sample; no credential used",
        },
        "schema": {
            "contract_id": "ITCH50-BINARY-V50-20230428",
            "format": "binary",
            "version": "20230428",
        },
        "session": {
            "coverage_date": "2026-06-12",
            "timezone": "America/New_York",
            "session_open_ns": SESSION_OPEN_NS,
            "session_close_ns": SESSION_CLOSE_NS,
            "terminating_frame_present": True,
            "final_system_event": "C",
        },
        "files": [
            dict(raw, role="raw", status="complete"),
            dict(noii, role="noii_reads", status="complete"),
            dict(admission_record, role="admission_record", status="complete"),
        ],
        "fields": [
            {
                "name": "timestamp_ns",
                "type": "int64",
                "semantics": "nanoseconds_since_midnight",
                "identity": "message_timestamp",
                "timezone": "America/New_York",
            },
            {"name": "locate", "type": "int32"},
            {"name": "symbol", "type": "utf8"},
            {"name": "imbalance_shares", "type": "int64"},
        ],
        "instrument": {"symbol": "AAPL", "venue": "NASDAQ"},
        "universe": {
            "rule_id": "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
            "pit": True,
            "members": ["AAPL", "MSFT"],
        },
        "records": {
            "timestamps": [SESSION_OPEN_NS + 10, SESSION_OPEN_NS + 20, SESSION_OPEN_NS + 30],
            "sequence": [1, 2, 3],
            "keys": ["m1", "m2", "m3"],
            "symbols": ["AAPL", "AAPL", "AAPL"],
        },
        "intervals": [
            {"id": "15:50_ET_NOII", "present": True, "count": 1},
            {"id": "15:55_ET_NOII", "present": True, "count": 1},
        ],
        "coverage": {"qualified": 100, "admitted": 97, "ratio": 0.97},
    }


def build_valid_basis(root: str) -> dict:
    """A manifest that passes the frozen BASIS contract (100% hourly pairing)."""
    funding = _write(root, "hl_funding.json", b'[{"time": 1688515200000}]')
    mid = _write(root, "hl_mid.json", b'[{"time": 1688515200000, "mid": "0"}]')
    mark = _write(root, "binance_mark.csv", b"open_time,mark\n1688515200000,0\n")
    return {
        "manifest_id": "FIXTURE-BASIS-WINDOW",
        "dataset_id": "FIXTURE-HL-BINANCE-3H",
        "branch": "BASIS",
        "source": {
            "source_id": "HL-FUNDING+BINANCE-USDM-KLINES",
            "provider": "Hyperliquid public API + Binance public archive",
            "retrieved_at_utc": "2026-09-29T00:00:00Z",
            "access_terms": "public endpoints; no credential used",
        },
        "schema": {
            "contract_id": "HL-FUNDING-JSON+BINANCE-USD-M-KLINES",
            "format": "json+csv",
        },
        "session": {
            "coverage_date": "2023-07-05",
            "timezone": "UTC",
            "window_start_unix": BASIS_START_UNIX,
            "window_end_unix": BASIS_START_UNIX + 7200,
        },
        "files": [
            dict(funding, role="hl_funding", status="complete"),
            dict(mid, role="hl_mid", status="complete"),
            dict(mark, role="binance_mark", status="complete"),
        ],
        "fields": [
            {
                "name": "hour_unix",
                "type": "int64",
                "semantics": "unix_seconds_utc_hour_floor",
                "identity": "hour_bucket_start",
                "timezone": "UTC",
            },
            {"name": "hl_funding_rate", "type": "float64"},
            {"name": "hl_mid", "type": "float64"},
            {"name": "binance_mark", "type": "float64"},
        ],
        "instrument": {"symbol": "BTCUSDT", "venue": "BINANCE"},
        "records": {
            "timestamps": [BASIS_START_UNIX, BASIS_START_UNIX + 3600, BASIS_START_UNIX + 7200],
            "keys": ["h0", "h1", "h2"],
        },
        "intervals": [
            {"id": "2023-07-05T00Z", "present": True, "count": 1},
            {"id": "2023-07-05T01Z", "present": True, "count": 1},
            {"id": "2023-07-05T02Z", "present": True, "count": 1},
        ],
        "coverage": {"qualified": 3, "admitted": 3, "ratio": 1.0},
    }


def build_valid_basis_panel(root: str) -> dict:
    """A complete BASIS panel in the shape the real branch-C manifest uses.

    Unlike ``build_valid_basis`` (whose interval ids are free-form labels) this
    panel declares the grid the contract can pin: epoch-second bucket ids in both
    id domains, the redundant ISO-8601 window mirrors, the UTC coverage date and
    the coverage block's own counts.  It is the positive control for the
    identity checks and the base of the BASIS adversarial fixtures.
    """
    funding = _write(root, "hl_funding.json", b'[{"time": 1688515200000}]')
    mid = _write(root, "hl_mid.json", b'[{"time": 1688515200000, "mid": "0"}]')
    mark = _write(root, "binance_mark.csv", b"open_time,mark\n1688515200000,0\n")
    hours = [BASIS_START_UNIX + offset * 3600 for offset in range(3)]
    return {
        "manifest_id": "FIXTURE-BASIS-PANEL",
        "dataset_id": "FIXTURE-HL-BINANCE-3H-PANEL",
        "branch": "BASIS",
        "source": {
            "source_id": "HL-FUNDING+BINANCE-USDM-KLINES",
            "provider": "Hyperliquid public API + Binance public archive",
            "retrieved_at_utc": "2026-09-29T00:00:00Z",
            "access_terms": "public endpoints; no credential used",
        },
        "schema": {
            "contract_id": "HL-FUNDING-JSON+BINANCE-USD-M-KLINES",
            "format": "json+csv",
        },
        "session": {
            "coverage_date": "2023-07-05",
            "timezone": "UTC",
            "window_start_unix": hours[0],
            "window_end_unix": hours[-1],
            "window_start_utc": "2023-07-05T00:00:00Z",
            "window_end_utc": "2023-07-05T02:00:00Z",
        },
        "files": [
            dict(funding, role="hl_funding", status="complete"),
            dict(mid, role="hl_mid", status="complete"),
            dict(mark, role="binance_mark", status="complete"),
        ],
        "fields": [
            {
                "name": "hour_unix",
                "type": "int64",
                "semantics": "unix_seconds_utc_hour_floor",
                "identity": "hour_bucket_start",
                "timezone": "UTC",
            },
            {"name": "hl_funding_rate", "type": "float64"},
            {"name": "hl_mid", "type": "float64"},
            {"name": "binance_mark", "type": "float64"},
        ],
        "instrument": {"symbol": "BTCUSDT", "venue": "BINANCE"},
        "records": {
            "timestamps": list(hours),
            "keys": [f"h{index}" for index in range(len(hours))],
            "count": len(hours),
        },
        "intervals": [{"id": hour, "present": True, "count": 1} for hour in hours],
        "coverage": {
            "qualified": len(hours),
            "admitted": len(hours),
            "ratio": 1.0,
            "window_hours": len(hours),
            "missing_buckets": 0,
            "duplicate_buckets": 0,
        },
    }


# ---------------------------------------------------------------------------
# fixtures: exactly one defect each, with the verdict and check it must produce
# ---------------------------------------------------------------------------


def _missing_field(manifest, root):
    manifest["fields"] = [f for f in manifest["fields"] if f["name"] != "imbalance_shares"]


def _duplicate_sequence(manifest, root):
    manifest["records"]["sequence"] = [1, 2, 2, 4]


def _sequence_gap(manifest, root):
    manifest["records"]["sequence"] = [1, 2, 4]


def _out_of_order_event(manifest, root):
    manifest["records"]["timestamps"] = [
        SESSION_OPEN_NS + 10,
        SESSION_OPEN_NS + 30,
        SESSION_OPEN_NS + 20,
    ]


def _duplicate_timestamp(manifest, root):
    manifest["records"]["timestamps"] = [
        SESSION_OPEN_NS + 10,
        SESSION_OPEN_NS + 10,
        SESSION_OPEN_NS + 30,
    ]


def _missing_interval(manifest, root):
    manifest["intervals"] = [i for i in manifest["intervals"] if i["id"] != "15:55_ET_NOII"]


def _wrong_instrument(manifest, root):
    manifest["instrument"]["symbol"] = "ZZZZ"


def _wrong_session_date(manifest, root):
    manifest["session"]["coverage_date"] = "2026-06-11"


def _unexpected_timezone(manifest, root):
    manifest["session"]["timezone"] = "UTC"


def _wrong_timestamp_semantics(manifest, root):
    manifest["fields"][0]["semantics"] = "nanoseconds_since_unix_epoch"


def _hash_mismatch(manifest, root):
    with open(os.path.join(root, "raw.bin"), "wb") as handle:
        handle.write(b"different bytes than the manifest hashed")


def _missing_hash(manifest, root):
    manifest["files"][0].pop("sha256")


def _partial_archive(manifest, root):
    manifest["files"][0]["status"] = "partial"


def _missing_file_role(manifest, root):
    manifest["files"] = [f for f in manifest["files"] if f["role"] != "noii_reads"]


def _unmet_coverage(manifest, root):
    manifest["coverage"] = {"qualified": 100, "admitted": 10, "ratio": 0.10}


def _missing_terminating_frame(manifest, root):
    manifest["session"]["terminating_frame_present"] = False


def _event_outside_session(manifest, root):
    manifest["records"]["timestamps"] = [
        SESSION_OPEN_NS + 10,
        SESSION_OPEN_NS + 20,
        SESSION_CLOSE_NS + 1,
    ]


def _schema_mismatch(manifest, root):
    manifest["schema"]["contract_id"] = "ITCH50-BINARY-V49-20200101"


def _universe_not_pit(manifest, root):
    manifest["universe"]["pit"] = False


def _symbol_outside_universe(manifest, root):
    manifest["records"]["symbols"] = ["AAPL", "ZZZZ", "AAPL"]


def _secondary_instrument_outside_family(manifest, root):
    manifest["instrument"]["secondary_instruments"] = [{"symbol": "TSLA", "security_id": 7}]


def _duplicate_key(manifest, root):
    manifest["records"]["keys"] = ["m1", "m1", "m3"]


def _type_outside_vocabulary(manifest, root):
    manifest["fields"][2]["type"] = "string"


def _source_field_absent(manifest, root):
    manifest["source"].pop("provider")


def _section_absent(manifest, root):
    manifest.pop("coverage")


def _object_absent(manifest, root):
    os.remove(os.path.join(root, "calendar.json"))


FIXTURES = (
    ("missing_required_field", _missing_field, admission.DATA_INCOMPLETE, "fields.required"),
    ("duplicate_sequence", _duplicate_sequence, admission.DATA_INVALID, "sequence.integrity"),
    ("sequence_gap", _sequence_gap, admission.DATA_INVALID, "sequence.integrity"),
    ("out_of_order_event", _out_of_order_event, admission.DATA_INVALID, "ordering.causal"),
    ("duplicate_timestamp", _duplicate_timestamp, admission.DATA_INVALID, "timestamps.monotonic"),
    ("missing_interval", _missing_interval, admission.DATA_INCOMPLETE, "intervals.coverage"),
    ("wrong_instrument", _wrong_instrument, admission.DATA_INVALID, "instrument.identity"),
    ("symbol_outside_universe", _symbol_outside_universe, admission.DATA_INVALID, "instrument.identity"),
    ("secondary_instrument_outside_family", _secondary_instrument_outside_family, admission.DATA_INVALID, "instrument.identity"),
    ("wrong_session_date", _wrong_session_date, admission.DATA_INVALID, "session.identity"),
    ("unexpected_timezone", _unexpected_timezone, admission.DATA_INVALID, "timezone.contract"),
    ("wrong_timestamp_semantics", _wrong_timestamp_semantics, admission.DATA_INVALID, "timestamp.identity"),
    ("hash_mismatch", _hash_mismatch, admission.DATA_INVALID, "files.hash"),
    ("missing_hash", _missing_hash, admission.DATA_INCOMPLETE, "files.hash"),
    ("partial_archive", _partial_archive, admission.DATA_INVALID, "archive.completeness"),
    ("missing_file_role", _missing_file_role, admission.DATA_INCOMPLETE, "files.required"),
    ("unmet_coverage", _unmet_coverage, admission.DATA_INCOMPLETE, "coverage.contract"),
    ("missing_terminating_frame", _missing_terminating_frame, admission.DATA_INVALID, "session.completeness"),
    ("event_outside_session", _event_outside_session, admission.DATA_INVALID, "records.session_window"),
    ("schema_mismatch", _schema_mismatch, admission.DATA_INVALID, "schema.identity"),
    ("universe_not_pit", _universe_not_pit, admission.DATA_INVALID, "universe.pit"),
    ("duplicate_event_key", _duplicate_key, admission.DATA_INVALID, "records.duplicates"),
    ("type_outside_vocabulary", _type_outside_vocabulary, admission.DATA_INVALID, "fields.types"),
    ("source_field_absent", _source_field_absent, admission.DATA_INCOMPLETE, "source.identity"),
    ("section_absent", _section_absent, admission.DATA_INCOMPLETE, "manifest.sections"),
    ("required_object_absent", _object_absent, admission.DATA_INCOMPLETE, "objects.present"),
)


# ---------------------------------------------------------------------------
# BASIS fixtures: the adversarial attacks the count-identity check could not see
# ---------------------------------------------------------------------------
#
# Each mutates the complete panel above and is evaluated against the frozen
# BASIS contract.  All three attacks left the cardinality of the bucket set
# untouched, which is why the historical count comparison admitted them.


def _basis_global_shift_4h(manifest, root):
    """Attack 1: every epoch field shifted +4h, internally consistent.

    Data, interval ids and the declared window all move together, so ordering,
    monotonicity, window containment and grid identity all pass: the manifest is
    a valid panel of the *wrong* window.  Only the declared ISO-8601 mirror still
    names the original instants, which is what the alignment check reads.
    """
    delta = 4 * 3600
    manifest["session"]["window_start_unix"] += delta
    manifest["session"]["window_end_unix"] += delta
    manifest["records"]["timestamps"] = [
        timestamp + delta for timestamp in manifest["records"]["timestamps"]
    ]
    for entry in manifest["intervals"]:
        entry["id"] += delta


def _basis_records_shortened(manifest, root):
    """Attack 2: the record list shortened, the coverage claim left standing."""
    records = manifest["records"]
    records["timestamps"] = records["timestamps"][:1]
    records["keys"] = records["keys"][:1]


def _basis_interval_ids_shifted(manifest, root):
    """Attack 3: every interval/bucket id offset by exactly one hour."""
    for entry in manifest["intervals"]:
        entry["id"] += 3600


def _basis_midwindow_gap(manifest, root):
    """A genuine gap: the middle bucket absent, the claim honestly reduced."""
    manifest["intervals"] = [manifest["intervals"][0], manifest["intervals"][2]]
    records = manifest["records"]
    records["timestamps"] = [records["timestamps"][0], records["timestamps"][2]]
    records["keys"] = [records["keys"][0], records["keys"][2]]
    records["count"] = 2
    manifest["coverage"].update(
        qualified=3, admitted=2, ratio=2 / 3, window_hours=3, missing_buckets=1
    )


def _basis_window_moved_a_day(manifest, root):
    """Window, mirrors and data moved one day; the coverage date stays behind."""
    delta = 86_400
    manifest["session"]["window_start_unix"] += delta
    manifest["session"]["window_end_unix"] += delta
    manifest["records"]["timestamps"] = [
        timestamp + delta for timestamp in manifest["records"]["timestamps"]
    ]
    for entry in manifest["intervals"]:
        entry["id"] += delta
    manifest["session"]["window_start_utc"] = "2023-07-06T00:00:00Z"
    manifest["session"]["window_end_utc"] = "2023-07-06T02:00:00Z"


BASIS_FIXTURES = (
    (
        "basis_global_shift_4h",
        _basis_global_shift_4h,
        admission.DATA_INVALID,
        "session.window_alignment",
    ),
    (
        "basis_records_shortened_coverage_claim_intact",
        _basis_records_shortened,
        admission.DATA_INVALID,
        "coverage.claim",
    ),
    (
        "basis_interval_ids_shifted_one_hour",
        _basis_interval_ids_shifted,
        admission.DATA_INVALID,
        "intervals.grid_identity",
    ),
    ("basis_midwindow_gap", _basis_midwindow_gap, admission.DATA_INCOMPLETE, "intervals.grid_identity"),
    (
        "basis_window_moved_a_day_from_coverage_date",
        _basis_window_moved_a_day,
        admission.DATA_INVALID,
        "session.window_alignment",
    ),
)


class AdmissionFixtureTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.manifest = build_valid(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------

    def _evaluate(self, manifest, contract=FIXTURE_CONTRACT, checks=None):
        return admission.evaluate(
            manifest, contract, admission.Context(root=self.root), checks=checks
        )

    def _mutated(self, mutator):
        manifest = json.loads(json.dumps(self.manifest))
        mutator(manifest, self.root)
        return manifest

    def assertVerdict(self, result, state, check):
        fired = [reason["check"] for reason in result["reasons"]]
        self.assertEqual(result["state"], state, msg=admission.format_text(result))
        self.assertIn(check, fired, msg=admission.format_text(result))

    # -- the contract's own positive case --------------------------------

    def test_valid_manifest_is_admitted(self):
        result = self._evaluate(self.manifest)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))
        self.assertEqual(result["reasons"], [])
        self.assertTrue(admission.is_admitted(result))
        self.assertEqual(result["reason_counts"], {"INVALID": 0, "INCOMPLETE": 0})

    def test_reasons_are_machine_readable(self):
        result = self._evaluate(self._mutated(_unmet_coverage))
        self.assertEqual(result["state"], admission.DATA_INCOMPLETE)
        for reason in result["reasons"]:
            self.assertEqual(
                sorted(reason), ["check", "detail", "expected", "observed", "severity"]
            )
        contract_reason = [r for r in result["reasons"] if r["check"] == "coverage.contract"][0]
        self.assertEqual(contract_reason["severity"], "INCOMPLETE")
        self.assertEqual(contract_reason["expected"], {"tolerance": 0.95})
        self.assertAlmostEqual(contract_reason["observed"]["ratio"], 0.10)

    def test_missing_manifest_file_is_incomplete(self):
        result = admission.evaluate_path(
            os.path.join(self.root, "absent.json"),
            FIXTURE_CONTRACT,
            admission.Context(root=self.root),
        )
        self.assertEqual(result["state"], admission.DATA_INCOMPLETE)
        self.assertEqual([r["check"] for r in result["reasons"]], ["manifest.load"])

    # -- real feed shapes: declared starts, bounded probes, unretained sources

    def _with_declared_start(self, start=1_118_771, rows=3, drop=None):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["records"].update(
            sequence=list(range(start, start + rows)),
            sequence_start=start,
            sequence_start_basis=PACKET_SEQUENCE_BASIS,
        )
        if drop:
            manifest["records"].pop(drop, None)
        return manifest

    def _with_probe(self, start=1_118_771, total=121):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["records"].update(
            sequence=[start, start + 1],
            sequence_tail=[start + 119, start + 120],
            sequence_first=start,
            sequence_last=start + 120,
            sequence_count_total=total,
            sequence_start=start,
            sequence_start_basis=PACKET_SEQUENCE_BASIS,
        )
        return manifest

    def _with_unretained_source(self, drop=None):
        manifest = json.loads(json.dumps(self.manifest))
        entry = {
            "role": "upstream_sample",
            "retained": False,
            "upstream_url": "https://example.invalid/es-2023-07-17.pcap",
            "upstream_sha256": "a" * 64,
            "bytes": 6_817_448_746,
            "status": "complete",
        }
        if drop:
            entry.pop(drop)
        manifest["files"].append(entry)
        return manifest

    def test_declared_sequence_start_is_accepted_and_noted(self):
        result = self._evaluate(self._with_declared_start(), contract=DECLARED_START_CONTRACT)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))
        notes = [note["check"] for note in result["notes"]]
        self.assertIn("sequence.start", notes)

    def test_declared_sequence_start_missing_is_incomplete(self):
        result = self._evaluate(
            self._with_declared_start(drop="sequence_start"), contract=DECLARED_START_CONTRACT
        )
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "sequence.integrity")

    def test_declared_sequence_start_needs_a_basis(self):
        result = self._evaluate(
            self._with_declared_start(drop="sequence_start_basis"), contract=DECLARED_START_CONTRACT
        )
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "sequence.integrity")

    def test_declared_sequence_start_against_a_pinned_start_is_invalid(self):
        result = self._evaluate(self._with_declared_start(), contract=FIXTURE_CONTRACT)
        self.assertVerdict(result, admission.DATA_INVALID, "sequence.integrity")

    def test_sequence_probe_accepts_a_dense_series(self):
        result = self._evaluate(self._with_probe(), contract=PROBE_CONTRACT)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))
        self.assertIn("sequence.probe", [note["check"] for note in result["notes"]])

    def test_sequence_probe_detects_a_whole_window_gap(self):
        result = self._evaluate(self._with_probe(total=200), contract=PROBE_CONTRACT)
        self.assertVerdict(result, admission.DATA_INVALID, "sequence.integrity")

    def test_sequence_probe_shorter_than_the_probe_size_is_incomplete(self):
        manifest = self._with_probe()
        manifest["records"]["sequence"] = [manifest["records"]["sequence"][0]]
        result = self._evaluate(manifest, contract=PROBE_CONTRACT)
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "sequence.integrity")

    def test_unretained_source_allowed_is_admitted_with_a_note(self):
        result = self._evaluate(self._with_unretained_source(), contract=UNRETAINED_CONTRACT)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))
        notes = [note for note in result["notes"] if note["check"] == "files.retained"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["observed"]["bytes"], 6_817_448_746)
        self.assertEqual(notes[0]["observed"]["upstream_sha256"], "a" * 64)

    def test_unretained_source_is_refused_where_the_contract_forbids_it(self):
        result = self._evaluate(self._with_unretained_source(), contract=FIXTURE_CONTRACT)
        self.assertVerdict(result, admission.DATA_INVALID, "files.hash")

    def test_unretained_source_without_upstream_digest_is_incomplete(self):
        result = self._evaluate(
            self._with_unretained_source(drop="upstream_sha256"), contract=UNRETAINED_CONTRACT
        )
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "files.hash")

    def test_unretained_source_with_a_malformed_digest_is_invalid(self):
        manifest = self._with_unretained_source()
        manifest["files"][-1]["upstream_sha256"] = "not-a-digest"
        result = self._evaluate(manifest, contract=UNRETAINED_CONTRACT)
        self.assertVerdict(result, admission.DATA_INVALID, "files.hash")

    def test_declared_rows_are_checked_even_when_the_contract_does_not_require_them(self):
        # AUCTION has no payload sequence contract, but a sequence the producer
        # does declare must still be contiguous: declared implies checked.
        manifest = self._mutated(_sequence_gap)
        result = self._evaluate(
            manifest, contract=dict(FIXTURE_CONTRACT, require_sequence=False)
        )
        self.assertVerdict(result, admission.DATA_INVALID, "sequence.integrity")

    def test_named_secondary_instruments_are_accepted(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["instrument"]["secondary_instruments"] = [{"symbol": "MSFT", "security_id": 7}]
        result = self._evaluate(manifest)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))

    def test_secondary_instrument_without_a_symbol_is_incomplete(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["instrument"]["secondary_instruments"] = [{"security_id": 7}]
        result = self._evaluate(manifest)
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "instrument.identity")

    def _with_markers(self, markers=None, drop_block=False, drop=None):
        manifest = json.loads(json.dumps(self.manifest))
        if drop_block:
            manifest["session"].pop("completeness_markers", None)
        else:
            block = {"gzip_integrity": "PASS", "framing_errors": 0}
            block.update(markers or {})
            if drop:
                block.pop(drop, None)
            manifest["session"]["completeness_markers"] = block
        return manifest

    def test_stream_completeness_markers_are_admitted_and_noted(self):
        manifest = self._with_markers()
        manifest["session"]["terminating_frame_present"] = False
        result = self._evaluate(manifest, contract=STREAM_CONTRACT)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))
        notes = [note["check"] for note in result["notes"]]
        self.assertIn("session.completeness", notes)
        self.assertIn("session.terminating_frame", notes)

    def test_stream_completeness_marker_mismatch_is_invalid(self):
        result = self._evaluate(
            self._with_markers({"framing_errors": 3}), contract=STREAM_CONTRACT
        )
        self.assertVerdict(result, admission.DATA_INVALID, "session.completeness")

    def test_stream_completeness_marker_key_missing_is_incomplete(self):
        result = self._evaluate(self._with_markers(drop="gzip_integrity"), contract=STREAM_CONTRACT)
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "session.completeness")

    def test_stream_completeness_block_absent_is_incomplete(self):
        result = self._evaluate(self._with_markers(drop_block=True), contract=STREAM_CONTRACT)
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "session.completeness")

    def test_stream_completeness_evidence_must_be_a_retained_artifact(self):
        contract = dict(STREAM_CONTRACT, completeness_evidence_role="missing_role")
        result = self._evaluate(self._with_markers(), contract=contract)
        self.assertVerdict(result, admission.DATA_INCOMPLETE, "session.completeness")

    def test_terminating_frame_flag_is_not_required_where_the_product_has_none(self):
        manifest = self._mutated(lambda m, root: m["session"].update(terminating_frame_present=False))
        result = self._evaluate(
            manifest, contract=dict(FIXTURE_CONTRACT, require_terminating_frame=False)
        )
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))

    def test_contracts_pin_feed_shapes(self):
        self.assertFalse(admission.AUCTION_CONTRACT["require_sequence"])
        self.assertTrue(admission.AUCTION_CONTRACT["sequence_start_from_manifest"])
        self.assertTrue(admission.AUCTION_CONTRACT["allow_unretained_files"])
        self.assertFalse(admission.AUCTION_CONTRACT["require_terminating_frame"])
        self.assertTrue(admission.AUCTION_CONTRACT["require_stream_completeness"])
        self.assertEqual(admission.AUCTION_CONTRACT["completeness_evidence_role"], "admission_record")
        self.assertEqual(admission.AUCTION_CONTRACT["stream_completeness_markers"]["framing_errors"], 0)
        self.assertEqual(
            admission.ES_CONTRACT["required_file_roles"], ["raw_extract", "trades", "book"]
        )
        self.assertTrue(admission.ES_CONTRACT["sequence_start_from_manifest"])
        self.assertEqual(admission.ES_CONTRACT["sequence_probe"], {"head_rows": 64, "tail_rows": 64})
        self.assertTrue(admission.ES_CONTRACT["allow_unretained_files"])
        self.assertNotIn("sequence_probe", admission.BASIS_CONTRACT)

    def test_check_registry_is_load_bearing(self):
        manifest = self._mutated(_duplicate_sequence)
        self.assertEqual(self._evaluate(manifest)["state"], admission.DATA_INVALID)
        stripped = tuple((cid, fn) for cid, fn in admission.CHECKS if cid != "sequence.integrity")
        result = self._evaluate(manifest, checks=stripped)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))
        self.assertNotIn("sequence.integrity", [r["check"] for r in result["reasons"]])

    def test_every_check_has_a_fixture(self):
        fired = {"manifest.load"}
        for name, mutator, _state, _check in FIXTURES:
            result = self._evaluate(self._mutated(mutator))
            fired.update(reason["check"] for reason in result["reasons"])
            with self.subTest(fixture=name):
                self.assertNotEqual(result["state"], admission.DATA_VALID)
        for name, mutator, _state, _check in BASIS_FIXTURES:
            result = self._basis_panel(mutator)
            fired.update(reason["check"] for reason in result["reasons"])
            with self.subTest(fixture=name):
                self.assertNotEqual(result["state"], admission.DATA_VALID)
        self.assertEqual(fired, set(admission.CHECK_IDS))

    def test_engine_never_admits_without_hash_evidence(self):
        manifest = self._mutated(lambda m, root: m["files"][1].pop("sha256"))
        result = self._evaluate(manifest)
        self.assertEqual(result["state"], admission.DATA_INCOMPLETE)
        self.assertIn("files.hash", [r["check"] for r in result["reasons"]])

    def test_coverage_tolerance_boundary_is_inclusive(self):
        manifest = self._mutated(
            lambda m, root: m.update(coverage={"qualified": 100, "admitted": 95, "ratio": 0.95})
        )
        self.assertEqual(self._evaluate(manifest)["state"], admission.DATA_VALID)
        below = self._mutated(
            lambda m, root: m.update(coverage={"qualified": 100, "admitted": 94, "ratio": 0.94})
        )
        self.assertEqual(self._evaluate(below)["state"], admission.DATA_INCOMPLETE)

    # -- frozen BASIS rule: 100% paired hourly buckets -------------------

    def test_valid_basis_manifest_is_admitted(self):
        manifest = build_valid_basis(self.root)
        result = self._evaluate(manifest, contract=admission.BASIS_CONTRACT)
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))

    def test_basis_missing_hour_is_incomplete(self):
        manifest = build_valid_basis(self.root)
        manifest["intervals"] = manifest["intervals"][:-1]
        result = self._evaluate(manifest, contract=admission.BASIS_CONTRACT)
        self.assertEqual(result["state"], admission.DATA_INCOMPLETE, msg=admission.format_text(result))
        self.assertIn("intervals.coverage", [r["check"] for r in result["reasons"]])

    def test_basis_window_cannot_shrink_post_hoc(self):
        # The window is the availability-derived session window, not the set of
        # buckets the producer chose to keep: narrowing the interval list while
        # keeping the window is a coverage deficit, never a pass.
        manifest = build_valid_basis(self.root)
        manifest["intervals"] = manifest["intervals"][:1]
        manifest["coverage"] = {"qualified": 1, "admitted": 1, "ratio": 1.0}
        result = self._evaluate(manifest, contract=admission.BASIS_CONTRACT)
        self.assertEqual(result["state"], admission.DATA_INCOMPLETE, msg=admission.format_text(result))
        self.assertIn("intervals.coverage", [r["check"] for r in result["reasons"]])

    # -- frozen BASIS grid: identity, not cardinality ---------------------

    def _basis_panel(self, mutator=None):
        manifest = build_valid_basis_panel(self.root)
        if mutator is not None:
            mutator(manifest, self.root)
        return self._evaluate(manifest, contract=admission.BASIS_CONTRACT)

    def test_basis_complete_panel_is_admitted(self):
        # Positive control: a genuinely complete panel of the declared window is
        # still admitted, with nothing left unverified.
        result = self._basis_panel()
        self.assertEqual(result["state"], admission.DATA_VALID, msg=admission.format_text(result))
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["notes"], [])

    def test_basis_grid_identity_is_load_bearing(self):
        # Negative control: the shifted-id attack is admitted exactly when the
        # grid identity check is not run, which proves that check - not some
        # other reason - is what rejects it.
        self.assertEqual(
            self._basis_panel(_basis_interval_ids_shifted)["state"], admission.DATA_INVALID
        )
        stripped = tuple(
            (check_id, function)
            for check_id, function in admission.CHECKS
            if check_id != "intervals.grid_identity"
        )
        with_grid_disabled = admission.evaluate(
            self._shifted_ids_manifest(),
            admission.BASIS_CONTRACT,
            admission.Context(root=self.root),
            checks=stripped,
        )
        self.assertEqual(
            with_grid_disabled["state"],
            admission.DATA_VALID,
            msg=admission.format_text(with_grid_disabled),
        )

    def _shifted_ids_manifest(self):
        manifest = build_valid_basis_panel(self.root)
        _basis_interval_ids_shifted(manifest, self.root)
        return manifest

    def test_basis_shifted_ids_name_the_offset(self):
        result = self._basis_panel(_basis_interval_ids_shifted)
        reasons = [r for r in result["reasons"] if r["check"] == "intervals.grid_identity"]
        self.assertEqual(len(reasons), 1, msg=admission.format_text(result))
        self.assertEqual(reasons[0]["severity"], "INVALID")
        self.assertEqual(reasons[0]["observed"]["shifted_seconds"], 3600)
        self.assertEqual(reasons[0]["observed"]["domain"], "intervals.id")
        self.assertIn("+1h", reasons[0]["detail"])

    def test_basis_shortened_records_cannot_keep_the_coverage_claim(self):
        result = self._basis_panel(_basis_records_shortened)
        self.assertEqual(result["state"], admission.DATA_INVALID, msg=admission.format_text(result))
        claims = [r for r in result["reasons"] if r["check"] == "coverage.claim"]
        self.assertTrue(claims, msg=admission.format_text(result))
        self.assertTrue(all(r["severity"] == "INVALID" for r in claims))
        overstated = [
            r
            for r in claims
            if r["observed"].get("admitted") == 3 and r["expected"].get("admitted") == 1
        ]
        self.assertEqual(len(overstated), 1, msg=admission.format_text(result))

    def test_basis_midwindow_gap_records_the_missing_id(self):
        result = self._basis_panel(_basis_midwindow_gap)
        self.assertEqual(result["state"], admission.DATA_INCOMPLETE, msg=admission.format_text(result))
        reasons = [r for r in result["reasons"] if r["check"] == "intervals.grid_identity"]
        self.assertTrue(reasons, msg=admission.format_text(result))
        for reason in reasons:
            self.assertEqual(reason["severity"], "INCOMPLETE")
            self.assertEqual(reason["observed"]["missing_ids"], [BASIS_START_UNIX + 3600])
            self.assertEqual(reason["observed"]["missing_count"], 1)

    def test_basis_global_shift_is_caught_by_the_declared_mirror(self):
        result = self._basis_panel(_basis_global_shift_4h)
        self.assertEqual(result["state"], admission.DATA_INVALID, msg=admission.format_text(result))
        reasons = [r for r in result["reasons"] if r["check"] == "session.window_alignment"]
        self.assertTrue(reasons, msg=admission.format_text(result))
        self.assertEqual(
            reasons[0]["observed"]["window_start_unix"], BASIS_START_UNIX + 4 * 3600
        )
        self.assertEqual(reasons[0]["expected"]["window_start_utc"], "2023-07-05T00:00:00Z")
        self.assertIn("+4h", reasons[0]["detail"])

    def test_basis_new_checks_stay_inert_where_the_contract_does_not_pin_them(self):
        # The grid and coverage-claim checks are contract-gated: a contract whose
        # buckets are free-form labels or whose coverage counts something other
        # than records must not grow phantom findings.
        self.assertEqual(admission.BASIS_CONTRACT["coverage_units"], "records")
        self.assertEqual(admission.BASIS_CONTRACT["interval_period_seconds"], 3600)
        self.assertNotIn("coverage_units", admission.AUCTION_CONTRACT)
        self.assertNotIn("coverage_units", admission.ES_CONTRACT)
        self.assertNotIn("require_full_interval_coverage", admission.AUCTION_CONTRACT)
        result = self._evaluate(self._mutated(_unmet_coverage))
        self.assertEqual([r["check"] for r in result["reasons"]], ["coverage.contract"])

    # -- branch contracts: data requirements only ------------------------

    def test_builtin_contracts_pin_branch_data_rules(self):
        self.assertEqual(admission.AUCTION_CONTRACT["expected_session_date"], "2026-06-12")
        self.assertTrue(admission.AUCTION_CONTRACT["require_stream_completeness"])
        self.assertFalse(admission.AUCTION_CONTRACT["require_terminating_frame"])
        self.assertEqual(admission.AUCTION_CONTRACT["required_final_event"], "C")
        self.assertEqual(admission.AUCTION_CONTRACT["coverage_tolerance"], 0.95)
        self.assertEqual(
            admission.AUCTION_CONTRACT["candidate_id"], "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG"
        )
        self.assertEqual(admission.ES_CONTRACT["expected_session_date"], "2023-07-17")
        self.assertFalse(admission.ES_CONTRACT["require_terminating_frame"])
        self.assertEqual(
            sorted(admission.ES_CONTRACT["required_fields"]),
            ["instrument_id", "price", "side", "size", "ts_event_ns", "ts_recv_ns"],
        )
        self.assertEqual(admission.BASIS_CONTRACT["coverage_tolerance"], 1.0)
        self.assertTrue(admission.BASIS_CONTRACT["require_full_interval_coverage"])
        self.assertEqual(admission.BASIS_CONTRACT["interval_period_seconds"], 3600)
        self.assertNotIn("universe", admission.BASIS_CONTRACT["required_sections"])

    def test_contracts_carry_no_economics(self):
        forbidden = {
            "pnl",
            "markout",
            "hurdle",
            "hurdle_bps",
            "signal_bps",
            "carry",
            "kill_survive",
            "r_best_kill",
            "cost_ledger",
        }

        def keys(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield key
                    yield from keys(item)
            elif isinstance(value, list):
                for item in value:
                    yield from keys(item)

        for branch, contract in admission.BUILTIN_CONTRACTS.items():
            with self.subTest(branch=branch):
                self.assertEqual(forbidden.intersection(keys(contract)), set())

    def test_cli_returns_verdict_and_json(self):
        contract_path = os.path.join(self.root, "contract.json")
        manifest_path = os.path.join(self.root, "manifest.json")
        out_path = os.path.join(self.root, "verdict.json")
        with open(contract_path, "w", encoding="utf-8") as handle:
            json.dump(FIXTURE_CONTRACT, handle)
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(self.manifest, handle)
        code = admission.main(
            [
                "--manifest",
                manifest_path,
                "--contract",
                contract_path,
                "--root",
                self.root,
                "--json-out",
                out_path,
            ]
        )
        self.assertEqual(code, 0)
        with open(out_path, "r", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["state"], admission.DATA_VALID)


def _make_fixture_test(name, mutator, state, check):
    def test(self):
        result = self._evaluate(self._mutated(mutator))
        with self.subTest(fixture=name):
            self.assertVerdict(result, state, check)

    test.__name__ = f"test_fixture_{name}"
    test.__doc__ = f"{name}: {state} raised by {check}"
    return test


for _name, _mutator, _state, _check in FIXTURES:
    setattr(
        AdmissionFixtureTest,
        f"test_fixture_{_name}",
        _make_fixture_test(_name, _mutator, _state, _check),
    )


def _make_basis_fixture_test(name, mutator, state, check):
    def test(self):
        result = self._basis_panel(mutator)
        with self.subTest(fixture=name):
            self.assertVerdict(result, state, check)

    test.__name__ = f"test_basis_fixture_{name}"
    test.__doc__ = f"{name}: {state} raised by {check}"
    return test


for _name, _mutator, _state, _check in BASIS_FIXTURES:
    setattr(
        AdmissionFixtureTest,
        f"test_basis_fixture_{_name}",
        _make_basis_fixture_test(_name, _mutator, _state, _check),
    )


if __name__ == "__main__":  # pragma: no cover - direct invocation
    unittest.main()
