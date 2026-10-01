"""AUCTION data-admission contract v2, quarantined out of the shared engine.

``M2.src.admission`` is a frozen input of the BASIS bridge freeze
(GOAL-M2-BRIDGE-001): ``M2-BRIDGE-HL-BINANCE-BASIS/freeze.json`` sealed its
sha256 and the basis experiment refuses to run once the file drifts. The AUCTION
v2 contract and its two contract-scoped checks were added to that shared module
*after* the basis seal was written, which broke the basis freeze's in-place
verifiability. This module is the W9 (epoch 6) repair: the same contract and the
same checks, moved out of the sealed engine so the sealed bytes could be
restored exactly (``M2/src/admission.py`` == 9f5862f7...).

Semantics are preserved. The checks keep their ids (``session.continuity``,
``coverage.certificate``), their severities and their ordering after the global
registry; ``evaluate`` below runs the sealed engine's own evaluation with the
contract-scoped checks appended through the engine's ``checks`` seam, which is
the same sequence the engine ran while the block still lived inside it. Shared
primitives are imported from ``M2.src.admission`` and never copied.

Importing this module registers ``AUCTION_V2`` in the engine's
``BUILTIN_CONTRACTS``, so the key keeps resolving from the engine too. Run the
CLI as::

    python3 -m M2.src.admission_auction --manifest <manifest> --branch AUCTION_V2 \
        --root . --json-out <result>
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

from .admission import (
    AUCTION_CONTRACT,
    BUILTIN_CONTRACTS,
    CHECKS,
    CHECK_IDS,
    REPO_ROOT,
    Context,
    DATA_VALID,
    Reason,
    _absent,
    _contradiction,
    _files,
    _is_number,
    _resolve,
    contract_for,
    evaluate as _evaluate,
    format_text,
    load_json,
)

# --------------------------------------------------------------------------
# W9 (epoch 6) note: the block below was moved verbatim out of
# ``M2/src/admission.py`` so that file could be restored byte-exactly to the
# sha256 the BASIS freeze sealed. It is unchanged apart from this note.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# AUCTION contract v2 (GOAL-M2-BRIDGE-001 epoch 5, worker B5) — additive only.
#
# Two operator-authorized contract changes, versioned with the v1 text retained:
#
# 1. Transport markers replace the zero-length-terminator expectation, and a
#    MEASUREMENT-WINDOW CONTINUITY + COVERAGE CERTIFICATE is required over the
#    retained window. The markers alone are not a completeness contract: the known
#    splice attack (.research/m2_bridge_001/verification/V2/
#    v2_auction_contract_attack.py) passes every one of them while holding 0.92% of
#    the decoded session. The two checks below therefore re-read the certificate
#    the manifest cites and refuse a manifest whose claim does not match its own
#    evidence.
# 2. The corrected point-in-time universe rule id
#    NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2.
#
# AUCTION_CONTRACT (v1) and BUILTIN_CONTRACTS["AUCTION"] are untouched, so no
# existing fixture changes verdict; the v2 contract is a separate key.
# --------------------------------------------------------------------------

CONTINUITY_FIGURES = (
    "in_window_messages",
    "in_window_message_pairs",
    "max_in_window_gap_ns",
    "backwards_timestamps",
    "monotonic_non_decreasing_exchange_timestamps",
)


def _role_entry(manifest: Mapping, role: Any) -> Mapping | None:
    for entry in _files(manifest):
        if entry.get("role") == role:
            return entry
    return None


def _load_declared_object(manifest: Mapping, role: Any, ctx: Context) -> tuple[Any, str | None]:
    entry = _role_entry(manifest, role)
    if entry is None:
        return None, None
    path = _resolve(ctx.root, entry.get("path"))
    if not path or not os.path.isfile(path):
        return None, path or None
    try:
        return load_json(path), path
    except (OSError, ValueError):
        return "UNREADABLE", path


def _check_measurement_window_continuity(
    manifest: Mapping, contract: Mapping, ctx: Context
) -> list[Reason]:
    """The window certificate the manifest cites must say what the manifest says.

    Contract-gated: a contract without ``require_measurement_window_continuity``
    runs nothing, so the v1 contract and every other branch are unaffected. The
    check is deliberately not a marker echo: it re-reads the retained certificate
    object the manifest names and requires the contract's markers, the manifest's
    declared figures and the certificate's own verdict to agree.
    """
    if not contract.get("require_measurement_window_continuity"):
        return []
    session = manifest.get("session")
    if not isinstance(session, Mapping):
        return [_absent("session.continuity", "session block absent", "session block")]
    block = session.get("measurement_window_continuity")
    if not isinstance(block, Mapping):
        return [
            _absent(
                "session.continuity",
                "session.measurement_window_continuity absent",
                "declared measurement-window continuity block",
            )
        ]
    reasons: list[Reason] = []
    for key, expected in (contract.get("continuity_markers") or {}).items():
        observed = block.get(key)
        if observed is None:
            reasons.append(_absent("session.continuity", {key: None}, {key: expected}))
        elif observed != expected:
            reasons.append(
                _contradiction(
                    "session.continuity",
                    {key: observed},
                    {key: expected},
                    "continuity marker differs from the contract",
                )
            )
    unset = [key for key, value in block.items() if value in (None, "", [])]
    if unset:
        reasons.append(
            _absent(
                "session.continuity",
                {"unset_markers": sorted(unset)},
                "every declared continuity marker has a value",
            )
        )
    role = contract.get("continuity_evidence_role")
    document, path = _load_declared_object(manifest, role, ctx)
    if document is None:
        reasons.append(
            _absent(
                "session.continuity",
                {"role": role, "path": path},
                f"retained artifact with role '{role}' carrying the certificate",
            )
        )
        return reasons
    if document == "UNREADABLE" or not isinstance(document, Mapping):
        reasons.append(
            _contradiction(
                "session.continuity",
                {"role": role, "path": path},
                "a readable JSON certificate",
                "the cited certificate cannot be read as JSON",
            )
        )
        return reasons
    evidenced = document.get("measurement_window_continuity")
    if not isinstance(evidenced, Mapping):
        reasons.append(
            _contradiction(
                "session.continuity",
                {"measurement_window_continuity": type(evidenced).__name__},
                "the certificate's own continuity block",
            )
        )
        return reasons
    certificate_verdict = (document.get("verdict") or {}).get("measurement_window_continuity")
    expected_verdict = contract.get("continuity_verdict", "PASS")
    if certificate_verdict != expected_verdict:
        reasons.append(
            _contradiction(
                "session.continuity",
                {"certificate_verdict": certificate_verdict},
                {"certificate_verdict": expected_verdict},
                "the cited certificate does not certify the measurement window",
            )
        )
    for key in CONTINUITY_FIGURES:
        declared = block.get(key)
        evidence = evidenced.get(key)
        if evidence is None:
            reasons.append(
                _absent("session.continuity", {key: None}, "the certificate records this figure")
            )
        elif declared != evidence:
            reasons.append(
                _contradiction(
                    "session.continuity",
                    {"declared": declared, "certificate": evidence},
                    "declared figure equals the certificate's",
                    "manifest claim differs from the certificate it cites",
                )
            )
    return reasons


def _check_coverage_certificate(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    """The coverage certificate behind the branch's 0.95 floor must be on disk.

    Contract-gated by ``require_coverage_certificate``. The numeric floor on the
    manifest's own coverage block is ``coverage.contract``; this check ties that
    block to the retained certificate, so a manifest cannot declare coverage its
    certificate does not evidence.
    """
    if not contract.get("require_coverage_certificate"):
        return []
    role = contract.get("coverage_certificate_role")
    document, path = _load_declared_object(manifest, role, ctx)
    if document is None:
        return [
            _absent(
                "coverage.certificate",
                {"role": role, "path": path},
                f"retained artifact with role '{role}' carrying the coverage certificate",
            )
        ]
    if document == "UNREADABLE" or not isinstance(document, Mapping):
        return [
            _contradiction(
                "coverage.certificate",
                {"role": role, "path": path},
                "a readable JSON certificate",
            )
        ]
    reasons: list[Reason] = []
    coverage = document.get("coverage_certificate")
    if not isinstance(coverage, Mapping):
        return [
            _contradiction(
                "coverage.certificate",
                {"coverage_certificate": type(coverage).__name__},
                "the certificate's own coverage block",
            )
        ]
    ratio = coverage.get("coverage_ratio")
    floor = contract.get("coverage_floor", contract.get("coverage_tolerance"))
    if coverage.get("tolerance_met") is not True:
        reasons.append(
            _contradiction(
                "coverage.certificate",
                {"tolerance_met": coverage.get("tolerance_met"), "ratio": ratio},
                {"tolerance_met": True},
                "the coverage certificate records an unmet floor",
            )
        )
    if not _is_number(ratio):
        reasons.append(
            _absent("coverage.certificate", {"coverage_ratio": ratio}, "a numeric coverage ratio")
        )
    elif floor is not None and ratio + 1e-12 < floor:
        reasons.append(
            _contradiction(
                "coverage.certificate",
                {"coverage_ratio": ratio},
                {"floor": floor},
                "certificate coverage is below the contract floor",
            )
        )
    declared_block = manifest.get("coverage")
    if isinstance(declared_block, Mapping):
        declared_ratio = declared_block.get("coverage_ratio")
        if declared_ratio is not None and _is_number(ratio) and declared_ratio != ratio:
            reasons.append(
                _contradiction(
                    "coverage.certificate",
                    {"declared": declared_ratio, "certificate": ratio},
                    "manifest coverage equals the certificate's",
                )
            )
        certificate_id = declared_block.get("certificate_id")
        if certificate_id is not None and certificate_id != document.get("certificate_id"):
            reasons.append(
                _contradiction(
                    "coverage.certificate",
                    {"certificate_id": certificate_id},
                    {"certificate_id": document.get("certificate_id")},
                    "manifest cites a different certificate",
                )
            )
    else:
        reasons.append(_absent("coverage.certificate", "coverage block absent", "coverage block"))
    return reasons


# Contract-scoped checks. They are NOT appended to the global registry: a contract
# names the extra checks it wants in ``extra_checks``, so the v1 contract, every
# other branch and every existing fixture see exactly the registry they saw before,
# while the v2 contract runs these two.
CONTRACT_CHECKS = {
    "session.continuity": _check_measurement_window_continuity,
    "coverage.certificate": _check_coverage_certificate,
}


AUCTION_CONTRACT_V2 = {
    **AUCTION_CONTRACT,
    "contract_id": "ADMISSION-AUCTION-v2",
    "universe_rule_id": "NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v2",
    "require_terminating_frame": False,
    "require_stream_completeness": True,
    "stream_completeness_markers": {
        "gzip_integrity": "PASS",
        "received_bytes_equals_content_range_total": True,
        "framing_errors": 0,
        "trailing_bytes_after_frames": 0,
        "final_frame_is_C_end_of_messages": True,
        "window_continuity_certificate": "PASS",
        "window_coverage_certificate": "PASS",
        "splice_negative_control": "FLAGGED",
        "transport_markers_prove_original_session_completeness": False,
        "out_of_window_holes": "DECLARED_NON_MATERIAL_TO_BRANCH_INPUTS",
    },
    "completeness_evidence_role": "admission_record",
    "continuity_verdict": "PASS",
    "continuity_evidence_role": "continuity_certificate",
    "continuity_markers": {
        "monotonic_non_decreasing_exchange_timestamps": True,
        "backwards_timestamps": 0,
        "window_start": "15:49:50.000000000",
        "window_end": "16:00:10.000000000",
        "max_in_window_gap_bound_ns": 1000000000,
        "in_window_messages_at_least": 1000000,
        "splice_negative_control": "FLAGGED",
        "transport_markers_prove_original_session_completeness": False,
        "out_of_window_holes": "DECLARED_NON_MATERIAL_TO_BRANCH_INPUTS",
    },
    "require_measurement_window_continuity": True,
    "require_coverage_certificate": True,
    "extra_checks": ["session.continuity", "coverage.certificate"],
    "coverage_certificate_role": "continuity_certificate",
    "coverage_floor": 0.95,
    "required_file_roles": [
        "raw",
        "noii_reads",
        "cross_trades",
        "universe",
        "admission_record",
        "continuity_certificate",
        "coverage_missingness",
        "entry_prints",
    ],
}

BUILTIN_CONTRACTS["AUCTION_V2"] = AUCTION_CONTRACT_V2


def evaluate(manifest: Any, contract: Mapping | None = None, ctx: Context | None = None) -> dict:
    """Evaluate a manifest with the contract's own scoped checks appended.

    The sealed engine's global registry runs first and unchanged; a contract that
    names ``extra_checks`` appends exactly those, in the order it names them. This
    is the same sequence ``M2.src.admission`` ran while the v2 block lived inside
    it, reproduced through the engine's own ``checks`` seam.
    """
    contract = contract or {}
    registry = CHECKS + tuple(
        (check_id, CONTRACT_CHECKS[check_id])
        for check_id in contract.get("extra_checks", ())
        if check_id in CONTRACT_CHECKS and check_id not in CHECK_IDS
    )
    return _evaluate(manifest, contract, ctx, checks=registry)


def evaluate_path(manifest_path: str, contract: Mapping, ctx: Context | None = None) -> dict:
    """Evaluate a manifest file; a missing file yields DATA_INCOMPLETE."""
    if not os.path.isfile(manifest_path):
        return evaluate(None, contract, ctx)
    return evaluate(load_json(manifest_path), contract, ctx)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate a data manifest against the AUCTION v2 contract."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--contract", default=None, help="path to a contract JSON file")
    parser.add_argument("--branch", default="AUCTION_V2", choices=["AUCTION_V2"])
    parser.add_argument("--root", default=REPO_ROOT)
    parser.add_argument("--json-out", default=None)
    arguments = parser.parse_args(argv)

    if arguments.contract:
        contract = load_json(arguments.contract)
    else:
        contract = contract_for(arguments.branch)

    ctx = Context(root=arguments.root)
    result = evaluate_path(arguments.manifest, contract, ctx)
    print(format_text(result))
    if arguments.json_out:
        with open(arguments.json_out, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return 0 if result["state"] == DATA_VALID else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
