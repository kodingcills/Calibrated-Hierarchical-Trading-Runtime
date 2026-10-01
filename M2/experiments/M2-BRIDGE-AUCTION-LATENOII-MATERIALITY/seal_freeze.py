#!/usr/bin/env python3
"""Seal the B5 apex freeze: freeze.json, freeze.sha256, run_inputs.json.

Run BEFORE the measurement stage. Nothing here reads an outcome: every input is
either a data-admission artefact, the frozen contract text, or a hash.

Run: python3 M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/seal_freeze.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
EXPERIMENT_ID = "M2-BRIDGE-AUCTION-LATENOII-MATERIALITY"
CANDIDATE_ID = "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG"

MODULES = (
    "M2/src/auction_certificate.py",
    "M2/src/auction_materiality.py",
    "M2/src/admission.py",
    "M2/src/envelope.py",
    "M2/src/itch_stream_window.py",
    "M2/src/ingest.py",
    "M2/tests/test_auction_materiality.py",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/build_manifest.py",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/seal_freeze.py",
    "M1/work/reselection_specs/TUP-NASDAQ-CLOSING-AUCTION-LATE-NOII.json",
    "M1/src/materialize.py",
    "M1/src/validate.py",
)

INPUTS = (
    "M2/data/derived_auction/2026-06-12/window.bin.gz",
    "M2/data/derived_auction/2026-06-12/admission.json",
    "M2/data/derived_auction/2026-06-12/admission_manifest.json",
    "M2/config/cost_ledger_v1.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/spec_prev_retained.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/certificate.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/signal_extract.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/entry_prints.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/admission_manifest_v2.json",
    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/admission_v2_result.json",
)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1 << 20)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def hashes(paths) -> dict:
    return {path: sha256_file(os.path.join(REPO, path)) for path in paths}


def main() -> int:
    freeze = {
        "experiment_id": EXPERIMENT_ID,
        "candidate_id": CANDIDATE_ID,
        "parent_goal": "GOAL-M2-BRIDGE-001",
        "epoch": 5,
        "worker": "B5",
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "freeze_status": (
            "FROZEN_BEFORE_ANY_OUTCOME_QUANTITY_WAS_COMPUTED. The contract, horizon, universe, "
            "states, cost treatment, metric, kill rule, thresholds and seeds below were fixed "
            "before the measurement stage ran. No Closing Cross price was read, no return, "
            "cost-adjusted figure or P&L was computed for any symbol before this seal; the "
            "data-admission artefacts it hashes (certificate, signal extract, entry prints) "
            "carry no outcome quantity."
        ),
        "session_date": "2026-06-12",
        "measurement_window_et": {
            "retained": "15:49:50-16:00:10 (the only window the retained artefact carries)",
            "signal": "15:50:00 (or first read after) and 15:55:00 (last read at or before)",
            "entry": "first eligible book-affecting instant strictly after 15:55:00, deadline 15:59:00",
            "exit": "the Closing Cross print (Cross Trade Q, Cross Type C)",
        },
        "operator_authorized_contract_changes": {
            "authorization": (
                "GOAL-M2-BRIDGE-001 epoch 5 assignment, OPERATOR-AUTHORIZED CONTRACT CHANGES, "
                "versioned with the old text retained. No other clause of the frozen "
                "formulation was changed."
            ),
            "change_1_universe_transcription_repair": {
                "before": (
                    "Authenticity=P, ETP Flag=N, Issue Classification=C, Issue Sub-Type=C, Market "
                    "Category in {Q,G,S,N,A,P,Z,V}"
                ),
                "after": (
                    "Authenticity=P, ETP Flag=N, Issue Classification=C, Market Category in {Q,G,S}"
                ),
                "rule_id_before": "NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v1",
                "rule_id_after": "NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2",
                "evidence": (
                    "ITCH Appendix E defines Issue Sub-Type C='Common Shares', Z='Not Applicable'; "
                    "this session's dominant Nasdaq-listed pair is C/Z (4183 locates) against C/C "
                    "(31). v1 admitted 31 of 12809 locates; v2 admits 2483 locates, of which 2465 "
                    "carry a valid Closing Cross. Zero-share Closing Cross prints: 8528 of 12809 "
                    "overall, 18 inside v2."
                ),
                "old_text_retained_at": [
                    "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/spec_prev_retained.json",
                    "M1/work/reselection_specs/TUP-NASDAQ-CLOSING-AUCTION-LATE-NOII.json:universe.clause_v1_retained",
                    "certificate.json:universe_repair.clause_v1_retained",
                ],
                "previous_spec_sha256": sha256_file(
                    os.path.join(REPO, "M2/experiments", EXPERIMENT_ID, "spec_prev_retained.json")
                ),
                "previous_spec_byte_identical_to_pre_edit": True,
            },
            "change_2_completeness_contract": {
                "before": (
                    "A zero-length terminating message is expected as the end-of-session marker."
                ),
                "after": (
                    "Transport markers (gzip CRC32+ISIZE, received == Content-Range total, 0 "
                    "framing errors, 0 trailing bytes, terminal 'C' End of Messages) PLUS a "
                    "MEASUREMENT-WINDOW CONTINUITY + COVERAGE CERTIFICATE over 15:49:50-16:00:10 ET: "
                    "monotonic non-decreasing exchange timestamps; every inter-message gap whose "
                    "both endpoints lie inside the window <= 1 s; at least 1,000,000 in-window "
                    "messages and at least one in-window pair; per-symbol Closing-Cross NOII "
                    "cadence inside 15:50:00-15:55:00 ET with no missed dissemination cycle; "
                    "input-availability coverage >= 0.95 with the missingness audit by identity "
                    "and reason."
                ),
                "statement": (
                    "Transport markers do NOT prove original-session completeness: the known "
                    "splice attack passes every marker while holding 0.92% of the decoded session. "
                    "Out-of-window holes are declared non-material to this branch's inputs, "
                    "because no frozen signal instant, entry instant or exit print lies outside "
                    "the window and a book reconstructed from the window alone cannot observe "
                    "pre-window state in any case."
                ),
                "negative_control": (
                    "certificate.json:splice_negative_control re-runs the V2 attack construction "
                    "(.research/m2_bridge_001/verification/V2/v2_auction_contract_attack.py) and "
                    "must be flagged. Measured: transport markers PASS, continuity FAIL, "
                    "artefact identity FAIL."
                ),
                "old_text_retained_at": [
                    "M1/work/reselection_specs/TUP-NASDAQ-CLOSING-AUCTION-LATE-NOII.json:timestamp_contract.v1_retained"
                ],
            },
        },
        "contract": {
            "signal": {
                "definition": "signed_imbalance(15:55) - signed_imbalance(15:50)",
                "sign": "B = +ImbalanceShares, S = -ImbalanceShares; direction N/O/P is missing and ineligible (frozen, unchanged)",
                "reads": (
                    "15:50: last Closing-Cross NOII read at or before 15:50:00 ET, else the first "
                    "read after; 15:55: last read at or before 15:55:00 ET"
                ),
                "scale_for_states_only": "delta_imbalance / max(PairedShares_15:55, 1)",
            },
            "entry": (
                "book state immediately after the first book-affecting message strictly after "
                "15:55:00 ET that leaves a valid, non-crossed, two-sided quote, at or before "
                "15:59:00 ET; POSITIVE signal enters at the best ask, NEGATIVE at the best bid. "
                "No message after the entry instant is used for the entry print."
            ),
            "exit": "the symbol's Closing Cross print; the cross price is used for nothing else",
            "primary_metric": {
                "id": "EXECUTABLE_CAPTURE_GEXEC",
                "definition": (
                    "side-signed executable capture per share: POSITIVE = Closing Cross price - "
                    "entry best ask; NEGATIVE = entry best bid - Closing Cross price. The entry "
                    "spread is embedded by construction, not assumed free."
                ),
                "pooling": (
                    "equal weight over analysed symbols, one share per symbol: the pooled USD "
                    "figure is mean(gross_usd_per_share); the pooled bps figure is "
                    "mean(gross_bps), each symbol's bps being relative to its own "
                    "CurrentReferencePrice_15:55"
                ),
                "units": ["USD per share of the equal-share bundle", "bps of the symbol's frozen reference price"],
            },
            "secondary_metric": {
                "id": "MECHANISM_SIDE_SIGNED_DISPLACEMENT",
                "definition": (
                    "side-signed (ClosingCrossPrice - CurrentReferencePrice_15:55) / "
                    "CurrentReferencePrice_15:55, in bps; the raw (unsigned) displacement is "
                    "reported beside it"
                ),
                "role": "REPORTED_ONLY",
            },
            "states": {
                "partition": (
                    "one preregistered 4-quantile partition of delta_imbalance / "
                    "max(PairedShares_15:55, 1)"
                ),
                "cut_points": "the 0.25/0.50/0.75 quantiles (linear interpolation) of the scaled signal over the analysed set",
                "derived_from": "signal-side data ONLY; no outcome, cost or price level enters",
                "labels": ["Q1_LOWEST", "Q2", "Q3", "Q4_HIGHEST"],
                "role": "diagnostic; a state row can never rescue a pooled failure",
            },
            "cost_treatment": {
                "c0_items": [
                    {
                        "id": "sec_section_31_fee",
                        "unit": "USD_PER_MILLION_OF_SALES",
                        "value": 20.6,
                        "leg": "sell only",
                        "effective": "2026-04-04 (before the 2026-06-12 sample)",
                        "source": "SEC Release 34-104909 via the Federal Register",
                    },
                    {
                        "id": "finra_trading_activity_fee",
                        "unit": "USD_PER_SHARE",
                        "value": 0.000195,
                        "leg": "sell only",
                        "effective": "2026-01-01 (before the 2026-06-12 sample)",
                        "source": "SEC Release 34-101696 / SR-FINRA-2024-019 via the Federal Register",
                    },
                ],
                "sell_leg": (
                    "exactly one per round trip: the Closing Cross exit for a POSITIVE signal, the "
                    "continuous-book entry for a NEGATIVE one"
                ),
                "excluded_from_c0": {
                    "id": "nasdaq_remove_liquidity_fee",
                    "value": 0.0030,
                    "reason": (
                        "no evidence it applies to a Closing Cross exit (ledger applicability is "
                        "'Nasdaq continuous book, displayed orders >= $1.00'); it is therefore not "
                        "a verified mandatory charge on the frozen exit path. It stays in C1 as a "
                        "scenario, because the entry leg of BOTH directions is an aggressive "
                        "continuous-book order and may plausibly pay it."
                    ),
                },
                "not_embedded_check": "the entry spread is embedded in the gross; no embedded charge is added again",
                "unknown_is_never_zero": (
                    "databento_xnas_mbo_data_cost and nasdaq_historical_itch_license_cost stay "
                    "unresolved operating economics; they are named in the C1 table with a null "
                    "value rather than dropped"
                ),
            },
            "coverage_floor": {
                "value": 0.95,
                "denominator": "corrected-universe point-in-time Stock Directory symbols carrying a valid Closing Cross print",
                "numerator": (
                    "denominator symbols that also carry both frozen Closing-Cross NOII reads with "
                    "Closing-Cross NOII cadence inside the signal interval"
                ),
                "rationale": (
                    "this is the input-availability coverage the branch's own 0.95 floor and the "
                    "repo's established coverage machinery measure; direction ineligibility is a "
                    "market state (no imbalance), not a hole in the data, and is reported "
                    "separately as the signal scope"
                ),
                "failure": "INDETERMINATE_COVERAGE (named), never a silent re-scope",
            },
            "inference": {
                "interval": "symbol-clustered percentile bootstrap of the pooled mean",
                "resamples": 10000,
                "seed": 20260612,
                "percentiles": [2.5, 97.5],
                "rng": "numpy.random.default_rng(PCG64)",
                "cluster": "symbol (one observation per symbol, so clusters are the bootstrap unit)",
                "per_state_seed_rule": "seed + state index (Q1=20260612, Q2=20260613, ...)",
                "significance": (
                    "reported separately with significance_against_zero; REPORTED_ONLY, never an "
                    "input to the decision"
                ),
            },
            "kill_rule": (
                "KILL_MATERIALITY if g <= 0 OR the uncertainty upper bound hi <= C0; "
                "SURVIVE_PROVISIONAL if lo > C0; otherwise INDETERMINATE (named clause). "
                "Coverage-floor failure is INDETERMINATE_COVERAGE (named)."
            ),
            "clause_order": [
                "coverage floor (input availability) -> INDETERMINATE_COVERAGE",
                "reconstruction validation -> INDETERMINATE (ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED)",
                "significance_vs_c0 rule from envelope.classify_materiality",
            ],
            "reported_clause": (
                "SIGNAL_SCOPE_SUBFLOOR is attached when the signal-defined population is below "
                "the coverage floor. It never rescues a verdict and never hides one: symbols the "
                "frozen rule removes have no signed imbalance to act on, so they cannot raise the "
                "measured capture, and a positive verdict carries an explicit population caveat."
            ),
            "prohibited": [
                "post-close reversal measurement",
                "indicative-price strategy",
                "any tuning of contract, horizon, universe, states, cost treatment, metric, kill rule, thresholds or seeds after a result was seen",
                "re-scoping the universe to meet the coverage floor",
                "using the Closing Cross print for anything except the exit",
            ],
        },
        "thresholds": {
            "max_in_window_gap_ns": 1000000000,
            "min_in_window_messages": 1000000,
            "declared_message_tolerance": 0.99,
            "noii_cadence_bound_ns": 15000000000,
            "observed_noii_dissemination_period_ns": 10000000000,
            "coverage_floor": 0.95,
            "entry_deadline_ns": 57420000000000,
            "reconstruction_min_within_far_band_ratio": 0.90,
            "c1_scenario_usd_per_share": [0.0, 0.003, 0.005, 0.01, 0.013],
            "bootstrap_resamples": 10000,
            "bootstrap_seed": 20260612,
            "quantile_edges": [0.25, 0.5, 0.75],
        },
        "declared_limitations": {
            "book_reconstruction_warm_up": (
                "The book is rebuilt from the retained window alone, so orders added before "
                "15:49:50 and still resting are invisible; the extraction counts those orphan "
                "book messages explicitly. Direction of bias is one-way and conservative: a "
                "missing resting order can only widen the reconstructed quote and worsen the "
                "entry price, so every gross capture reported here is a LOWER bound on the true "
                "one. It cannot manufacture a positive result."
            ),
            "signal_scope": (
                "The frozen sign rule removes symbols whose reads carry direction N/O/P. Every "
                "such read in this session carries ImbalanceShares == 0, and a symbol whose reads "
                "are both N has delta_imbalance == 0 under any reading. The decision population "
                "is stated, with its liquidity comparison, in results.json."
            ),
            "development_grade_sample": (
                "One session, one venue, one time zone, low-priced and high-priced names pooled. "
                "A positive result on this material can be at most SURVIVE_PROVISIONAL."
            ),
            "producer_declared_fields": (
                "received_bytes == Content-Range total is a producer assertion, not recomputable "
                "from the retained artefact; the certificate labels it as such."
            ),
        },
        "as_run_deviations_from_freeze": (
            "recorded in results.json:as_run_deviations_from_freeze (none expected; any deviation "
            "is reported there rather than by editing this sealed file)"
        ),
        "frozen_module_and_input_sha256": {
            **hashes(MODULES),
            **hashes(INPUTS),
        },
        "run_commands": [
            (
                "python3 -m M2.src.auction_certificate --window "
                "M2/data/derived_auction/2026-06-12/window.bin.gz --out "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/certificate.json --extract "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/signal_extract.json "
                "--expected-sha256 "
                "28ed7b973807fdbfd3558dfbd2fdc5e1580a0227860d0f129ff6c67091d59597 "
                "--expected-decoded-bytes 1824239389 --declared-in-window-messages 55698714 "
                "--declared-received-bytes 17894268560 --declared-content-range-total "
                "17894268560 --negative-control"
            ),
            (
                "python3 M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/build_manifest.py"
            ),
            (
                "python3 -m M2.src.admission --manifest "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/admission_manifest_v2.json "
                "--branch AUCTION_V2 --root . --json-out "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/admission_v2_result.json"
            ),
            (
                "python3 -m M2.src.auction_materiality extract --window "
                "M2/data/derived_auction/2026-06-12/window.bin.gz --extract "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/signal_extract.json --out "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/entry_prints.json"
            ),
            (
                "python3 M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/seal_freeze.py"
            ),
            (
                "python3 -m M2.src.auction_materiality measure --extract "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/signal_extract.json "
                "--entries "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/entry_prints.json --out "
                "M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/results.json"
            ),
        ],
        "admission_verdict": {
            "contract_id": "ADMISSION-AUCTION-v2",
            "state": "DATA_VALID",
            "note": (
                "The v2 engine verdict is DATA_VALID with no findings; the v1 contract key is "
                "unchanged and is not what this branch runs. The operator's suggested "
                "'--branch AUCTION' would select the retained v1 contract, so the v2 key "
                "AUCTION_V2 is used and the deviation is recorded here."
            ),
        },
    }
    freeze_path = os.path.join(HERE, "freeze.json")
    with open(freeze_path, "w", encoding="utf-8") as handle:
        json.dump(freeze, handle, indent=1, sort_keys=True)
        handle.write("\n")
    digest = sha256_file(freeze_path)
    with open(os.path.join(HERE, "freeze.sha256"), "w", encoding="utf-8") as handle:
        handle.write(f"{digest}  freeze.json\n")

    run_inputs = {
        "experiment_id": EXPERIMENT_ID,
        "candidate_id": CANDIDATE_ID,
        "sealed_at_utc": freeze["frozen_at_utc"],
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
        ).stdout.strip(),
        "git_dirty_paths": sorted(
            line[3:]
            for line in subprocess.run(
                ["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True
            ).stdout.splitlines()
            if line.strip()
        ),
        "code_and_input_sha256": freeze["frozen_module_and_input_sha256"],
        "run_commands": freeze["run_commands"],
        "as_run_deviations_from_freeze": [],
        "note": (
            "Sealed with the freeze, before the measurement stage. Any deviation discovered "
            "while running is recorded in results.json:as_run_deviations_from_freeze so that "
            "this file and the freeze stay hash-stable."
        ),
    }
    with open(os.path.join(HERE, "run_inputs.json"), "w", encoding="utf-8") as handle:
        json.dump(run_inputs, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(f"freeze.json    sha256={digest}")
    print(f"freeze.sha256  {open(os.path.join(HERE, 'freeze.sha256')).read().strip()}")
    print(f"run_inputs.json sha256={sha256_file(os.path.join(HERE, 'run_inputs.json'))}")
    print(f"git HEAD {run_inputs['git_head']}  dirty paths {len(run_inputs['git_dirty_paths'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
