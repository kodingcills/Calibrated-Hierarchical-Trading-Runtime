#!/usr/bin/env python3
"""Build the AUCTION v2 admission manifest for the B5 frozen measurement.

Reads (read-only, never rewritten):

* ``M2/data/derived_auction/2026-06-12/admission.json`` — the producer's own
  structural admission record (source identity, transport counters, session
  events, the declared in-window message count).
* ``M2/data/derived_auction/2026-06-12/admission_manifest.json`` — the producer's
  v1 manifest, which the v2 manifest reuses for the sections v2 does not change
  (source, schema, fields).
* ``certificate.json`` / ``signal_extract.json`` / ``entry_prints.json`` — this
  worker's own measurement-window certificate, per-symbol coverage extract and
  entry prints.

Writes ``admission_manifest_v2.json`` in the same directory.

Run: python3 M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/build_manifest.py
"""

from __future__ import annotations

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
DATA = os.path.join(REPO, "M2", "data", "derived_auction", "2026-06-12")
WINDOW = "M2/data/derived_auction/2026-06-12/window.bin.gz"
WINDOW_START_NS = 56990000000000
WINDOW_END_NS = 57610000000000


def load(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1 << 20)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def entry(role: str, relative: str, **extra) -> dict:
    path = os.path.join(REPO, relative)
    row = {
        "role": role,
        "path": relative,
        "sha256": sha256_file(path),
        "bytes": os.path.getsize(path),
        "status": "complete",
    }
    row.update(extra)
    return row


def main() -> int:
    producer = load(os.path.join(DATA, "admission.json"))
    producer_manifest = load(os.path.join(DATA, "admission_manifest.json"))
    certificate = load(os.path.join(HERE, "certificate.json"))
    extract = load(os.path.join(HERE, "signal_extract.json"))
    entries = load(os.path.join(HERE, "entry_prints.json"))

    transport = certificate["transport_markers"]
    continuity = certificate["measurement_window_continuity"]
    coverage_certificate = certificate["coverage_certificate"]
    verdict = certificate["verdict"]
    control = certificate["splice_negative_control"]
    universe = certificate["universe_repair"]

    denominator = [row for row in extract if row.get("in_denominator")]
    numerator = [row for row in extract if row.get("in_numerator")]
    signal_rows = [row for row in extract if row.get("signal_defined")]
    coverage_ratio = len(numerator) / len(denominator)

    records = []
    for row in sorted(denominator, key=lambda item: item["locate"]):
        symbol = row["symbol"]
        records.append(
            {
                "timestamp": row["read_1550_ts_ns"],
                "key": f"{symbol}|1550|{row['read_1550_ts_ns']}",
                "symbol": symbol,
            }
        )
        records.append(
            {
                "timestamp": row["read_1555_ts_ns"],
                "key": f"{symbol}|1555|{row['read_1555_ts_ns']}",
                "symbol": symbol,
            }
        )
        records.append(
            {
                "timestamp": row["closing_cross_ts_ns"],
                "key": f"{symbol}|CROSS|{row['closing_cross_ts_ns']}",
                "symbol": symbol,
            }
        )
    records.sort(key=lambda item: item["timestamp"])

    manifest = {
        "manifest_id": "M2-BRIDGE-AUCTION-LATENOII-AGG-2026-06-12-v2",
        "dataset_id": producer_manifest["dataset_id"],
        "branch": "AUCTION",
        "notes": {
            "candidate_id": "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
            "descended_from": "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
            "reformulation": "NARROW_REFORMULATION",
            "supersedes": (
                "W1-AUCTION-NASDAQ-CLOSE-H4-LATENOII-AGG-2026-06-12 (contract v1). The v1 "
                "manifest is retained unmodified as the producer's own record; this v2 manifest "
                "applies the two operator-authorized contract changes of GOAL-M2-BRIDGE-001 "
                "epoch 5 (universe transcription repair, transport markers + measurement-window "
                "certificate) and adds this worker's own evidence objects."
            ),
            "retention": producer_manifest["notes"]["retention"],
            "terminator": (
                "session.terminating_frame_present is FALSE and is no longer the completeness "
                "test: the published object ends on the ITCH 5.0 'C' End of Messages system "
                "event, which the repo's own accepted reference tape shares. Completeness is "
                "carried by the transport markers plus the measurement-window continuity and "
                "coverage certificate (see session.measurement_window_continuity and "
                "files[role=continuity_certificate])."
            ),
            "transport_is_not_completeness": (
                "Transport markers prove the retained object is intact; they do NOT prove the "
                "original session was captured whole. The known splice attack passes every "
                "marker while holding 0.92% of the decoded session, so the certificate states "
                "its rules over retained messages INSIDE 15:49:50-16:00:10 ET and the engine "
                "re-reads the cited certificate."
            ),
            "universe_repair": (
                "universe.rule_id is NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2: "
                "Authenticity=P, ETP Flag=N, Issue Classification=C, Market Category in {Q,G,S}. "
                "The v1 clause text (which also required Issue Sub-Type=C and admitted 31 of "
                "12809 locates) is retained in the certificate at "
                "universe_repair.clause_v1_retained and in the reselection spec at "
                "universe.clause_v1_retained."
            ),
            "no_economics": (
                "This manifest declares structural identity, the measurement window and "
                "coverage only. No price level, markout, cost or displacement quantity is part "
                "of it; the Closing Cross price appears only through the certificate's "
                "zero-share-print validity marker."
            ),
        },
        "source": producer_manifest["source"],
        "schema": producer_manifest["schema"],
        "session": {
            "coverage_date": "2026-06-12",
            "timezone": "America/New_York",
            "session_open_ns": WINDOW_START_NS,
            "session_close_ns": WINDOW_END_NS,
            "window_start_unix": WINDOW_START_NS,
            "window_end_unix": WINDOW_END_NS,
            "terminating_frame_present": False,
            "final_system_event": "C",
            "completeness_markers": {
                "gzip_integrity": transport["gzip_integrity"],
                "received_bytes_equals_content_range_total": transport[
                    "received_bytes_equals_content_range_total"
                ],
                "framing_errors": transport["framing_errors"],
                "trailing_bytes_after_frames": transport["trailing_bytes_after_frames"],
                "final_frame_is_C_end_of_messages": transport["final_frame_is_C_end_of_messages"],
                "window_continuity_certificate": verdict["measurement_window_continuity"],
                "window_coverage_certificate": verdict["coverage_certificate"],
                "splice_negative_control": "FLAGGED" if control["flagged"] else "NOT_FLAGGED",
                "transport_markers_prove_original_session_completeness": False,
                "out_of_window_holes": verdict["out_of_window_holes"],
            },
            "measurement_window_continuity": {
                "certificate_id": certificate["certificate_id"],
                "certificate_path": "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/certificate.json",
                "window_start": continuity["window"]["start"],
                "window_end": continuity["window"]["end"],
                "monotonic_non_decreasing_exchange_timestamps": continuity[
                    "monotonic_non_decreasing_exchange_timestamps"
                ],
                "backwards_timestamps": continuity["backwards_timestamps"],
                "in_window_messages": continuity["in_window_messages"],
                "in_window_message_pairs": continuity["in_window_message_pairs"],
                "max_in_window_gap_ns": continuity["max_in_window_gap_ns"],
                "max_in_window_gap_bound_ns": continuity["bounds"]["max_in_window_gap_ns"],
                "in_window_messages_at_least": continuity["bounds"]["min_in_window_messages"],
                "splice_negative_control": "FLAGGED" if control["flagged"] else "NOT_FLAGGED",
                "transport_markers_prove_original_session_completeness": False,
                "out_of_window_holes": verdict["out_of_window_holes"],
                "certificate_verdict": verdict["measurement_window_continuity"],
                "negative_control_transport_markers": control["transport_markers_verdict"],
                "negative_control_spliced_sha256": control["spliced_sha256"],
            },
            "full_stream_first_exchange_timestamp_ns": producer["first_exchange_timestamp_ns"],
            "full_stream_last_exchange_timestamp_ns": producer["last_exchange_timestamp_ns"],
            "system_events": {
                event["event_code"]: event["timestamp_ns"] for event in producer["session_events"]
            },
            "frames_total": producer["frame_count"],
        },
        "files": [
            producer_manifest["files"][0],
            producer_manifest["files"][1],
            entry("noii_reads", WINDOW, covers="NOII I messages, Cross Type C, 15:50 and 15:55 ET"),
            entry("cross_trades", WINDOW, covers="Cross Trade Q prints, Cross Type C"),
            entry("universe", WINDOW, covers="date-specific Stock Directory spin"),
            entry("admission_record", "M2/data/derived_auction/2026-06-12/admission.json"),
            entry(
                "continuity_certificate",
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/certificate.json",
                covers=(
                    "transport markers, measurement-window continuity certificate, universe "
                    "repair evidence and coverage certificate"
                ),
            ),
            entry(
                "coverage_missingness",
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/signal_extract.json",
                covers="per-symbol coverage rows with the exclusion and signal-scope reason",
            ),
            entry(
                "entry_prints",
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/entry_prints.json",
                covers=(
                    "per-symbol post-15:55 entry print plus the book-reconstruction diagnostic"
                ),
            ),
        ],
        "fields": producer_manifest["fields"],
        "instrument": {
            "symbol": "NASDAQ-CLOSE-CROSS-UNIVERSE",
            "venue": "NASDAQ",
            "identity_basis": producer_manifest["instrument"]["identity_basis"],
            "members_count": len(denominator),
        },
        "universe": {
            "rule_id": "NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2",
            "candidate_id": "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
            "pit": True,
            "members": [row["symbol"] for row in sorted(denominator, key=lambda item: item["locate"])],
            "operative_rule": (
                "same-day Stock Directory; Authenticity=P; ETP Flag=N; Issue Classification=C; "
                "Market Category in {Q,G,S}; plus a valid Closing Cross print and both frozen "
                "Closing-Cross NOII reads"
            ),
            "clause_v1_locates": universe["v1_clause_locates_admitted"],
            "v2_directory_qualified_locates": universe["v2_clause_locates_admitted"],
            "v2_qualified_with_valid_cross": len(denominator),
            "record_covered_count": len(denominator),
        },
        "records": {
            "timestamps": [row["timestamp"] for row in records],
            "keys": [row["key"] for row in records],
            "symbols": [row["symbol"] for row in records],
            "counts": {
                "events": len(records),
                "members": len(denominator),
                "window_noii_c_messages": universe["counts"]["noii_c_reads"],
                "window_cross_trade_c_messages": universe["counts"]["closing_cross_prints"],
            },
            "note": (
                "One eligible NOII read at/before 15:50 ET (frozen fallback: the first read after "
                "15:50 when no boundary message exists), one at/before 15:55 ET, and one valid "
                "Closing Cross 'Q' (Cross Type C) print per covered member; ordered by exchange "
                "timestamp. records.keys is symbol|instant|timestamp_ns. No payload sequence is "
                "declared: a captured ITCH file carries none."
            ),
        },
        "intervals": [
            {
                "id": "15:50_ET_NOII",
                "present": True,
                "count": universe["counts"]["noii_c_reads"],
                "note": "Closing-Cross NOII 'I' reads disseminated 15:50:00-16:00:00 ET at 10 s cadence",
            },
            {
                "id": "15:55_ET_NOII",
                "present": True,
                "count": universe["counts"]["noii_c_reads"],
                "note": "same dissemination stream; the 15:55 read is the last at or before 15:55:00 ET",
            },
            {
                "id": "CLOSING_CROSS_16:00_ET",
                "present": True,
                "count": universe["counts"]["closing_cross_prints"],
                "note": f"{universe['counts']['closing_cross_zero_share']} of these are zero-share prints",
            },
        ],
        "coverage": {
            "qualified": len(denominator),
            "admitted": len(numerator),
            "ratio": coverage_ratio,
            "tolerance": 0.95,
            "certificate_id": certificate["certificate_id"],
            "coverage_ratio": coverage_certificate["coverage_ratio"],
            "definition": coverage_certificate["definition"],
            "variants": [
                {
                    "universe": "V1_LITERAL_CLAUSE",
                    "universe_qualified_symbols": universe["v1_clause_locates_admitted"],
                    "note": (
                        "the superseded clause (Issue Sub-Type=C). Retained for provenance only: "
                        "it admits a transcription artefact, not a universe."
                    ),
                },
                {
                    "universe": "V2_CORRECTED_CLAUSE",
                    "read_semantics": "FROZEN_CONTRACT",
                    "universe_qualified_symbols": universe["v2_clause_locates_admitted"],
                    "denominator_symbols_with_valid_closing_cross_C": len(denominator),
                    "numerator_both_C_reads_and_valid_cross": len(numerator),
                    "coverage_ratio": coverage_ratio,
                    "tolerance": 0.95,
                    "tolerance_met": coverage_certificate["tolerance_met"],
                    "exclusion_reason_counts": coverage_certificate["exclusion_reason_counts"],
                },
                {
                    "universe": "V2_CORRECTED_CLAUSE",
                    "read_semantics": "SIGNAL_DEFINED",
                    "denominator_symbols_with_valid_closing_cross_C": len(denominator),
                    "numerator_signal_defined": len(signal_rows),
                    "signal_defined_ratio": coverage_certificate["signal_scope"][
                        "signal_defined_ratio"
                    ],
                    "exclusion_reason_counts": coverage_certificate["signal_scope"][
                        "exclusion_reason_counts"
                    ],
                    "note": (
                        "NOT the coverage floor: direction N/O/P is a market state (no imbalance), "
                        "not absent data. Reported so the decision population is never implicit."
                    ),
                },
            ],
            "diagnostics": {
                "noii_cadence": coverage_certificate["noii_cadence"],
                "missingness_audit_count": coverage_certificate["missingness_audit_count"],
                "signal_scope_subfloor": coverage_certificate["signal_scope"]["subfloor"],
            },
        },
    }
    out = os.path.join(HERE, "admission_manifest_v2.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(f"{out} sha256={sha256_file(out)}")
    print(
        "members={} records={} coverage={:.4f} signal_scope={:.4f} entries={}".format(
            len(denominator),
            len(records),
            coverage_ratio,
            coverage_certificate["signal_scope"]["signal_defined_ratio"],
            len(entries["entry_prints"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
