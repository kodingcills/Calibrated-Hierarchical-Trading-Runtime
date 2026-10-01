"""Deterministic data-admission engine for the M2 bridge epoch.

The generator of a data artifact must not be the judge of its validity. This
module is the objective evaluator: it takes a declarative *branch contract*
(what must be true of data that may enter a freeze) plus a *manifest* (what the
producing worker claims about its data, with the raw/derived hashes), and
returns exactly one of

    DATA_VALID | DATA_INVALID | DATA_INCOMPLETE

together with machine-readable reasons.  It contains no strategy logic and no
economics: it never reads a price series for its meaning, only its declared and
verifiable structure.

Severity rule, applied uniformly by every check:

* ``INVALID``    - the manifest carries evidence and that evidence *contradicts*
                   the contract (hash mismatch, wrong session date, out-of-order
                   event, duplicate or gapped sequence, wrong instrument, ...).
* ``INCOMPLETE`` - the evidence needed to make the comparison is *absent*
                   (missing required field, missing hash, missing interval,
                   declared partial archive, coverage below the declared
                   tolerance, missing object on disk, ...).

Verdict precedence: any INVALID reason wins; else any INCOMPLETE reason; else
DATA_VALID.  A check that cannot run never yields DATA_VALID, so an absent hash
or an unmet coverage contract is refused rather than silently accepted.

Manifest shape (all sections are contract-selected; extra keys are ignored)::

    {
      "manifest_id": str,
      "branch": str,
      "source": {"source_id", "provider", "retrieved_at_utc", "access_terms", ...},
      "schema": {"contract_id": str, "format": str, "version": str},
      "session": {"coverage_date", "timezone", "session_open_ns", "session_close_ns",
                  "terminating_frame_present": bool, "final_system_event": str,
                  "window_start_unix": int, "window_end_unix": int},
      "files": [{"role", "path", "sha256", "bytes", "expected_bytes",
                 "status": "complete"|"partial"|"truncated"|"incomplete",
                 "retained": bool, "upstream_url", "upstream_sha256"}],
      "fields": [{"name", "type", "semantics", "identity", "timezone"}],
      "instrument": {"symbol", "venue", "security_id", "identity_basis"},
      "universe": {"rule_id", "pit": bool, "members": [str]},
      "records": {"timestamps": [int], "sequence": [int], "sequence_tail": [int],
                  "sequence_start": int, "sequence_start_basis": str,
                  "sequence_first": int, "sequence_last": int,
                  "sequence_count_total": int, "keys": [...], "symbols": [str]},
      "intervals": [{"id", "present": bool, "count"}],
      "coverage": {"qualified": int, "admitted": int, "ratio": float}
    }

``files[].retained`` defaults to true, and a retained file is hashed from disk. A
file entry with ``retained: false`` is a source that was streamed and not kept:
it is admissible only where the contract sets ``allow_unretained_files``, it must
declare ``upstream_url`` / ``upstream_sha256`` / ``bytes``, and the verdict then
carries a note recording that its digest is a producer assertion. A contract that
pins ``sequence_start_from_manifest`` expects the producer to declare the
observed first sequence value and its basis (the only honest option for a feed
whose transport sequence persists across sessions), optionally with a bounded
``sequence_probe`` of a head run, a tail run and the declared first / last /
total values instead of a multi-million-row series.

Buckets are admitted on *identity*, not on count. Where a contract requires full
interval coverage (``interval_period_seconds`` plus declared session window
bounds) the engine derives the exact expected bucket id set from the declared
window and interval -- ``ids = ts_floor(window_start) + k * period`` for
``k`` in ``0 .. n-1``, ``ts_floor(t) = (t // period) * period``,
``n = (ts_floor(end) - ts_floor(start)) // period + 1`` -- and requires the
observed ids to equal it (``intervals.grid_identity``), separately reporting
missing, unexpected, shifted and duplicated ids. Where the contract also declares
``coverage_units: "records"`` the coverage block must be recomputable from the
record list (``coverage.claim``): a claimed count or ratio that the manifest's
own records do not support is a contradiction, not a pass. ``session.window_alignment``
cross-examines the declared window against the manifest's redundant anchors
(ISO-8601 mirrors, ``coverage_date``) so that a globally shifted but internally
consistent window is named rather than accepted.

``files[].path`` may be absolute or relative to the evaluation root (the repo
root by default); declared sha256 values are recomputed from disk.

Contract fields ``candidate_id``, ``descended_from`` and ``frozen_formulation``
are descriptive labels recorded in the verdict; no check reads them, and none of
them can change a verdict.
"""

from __future__ import annotations

import collections
import dataclasses
import datetime
import json
import os
from typing import Any, Callable, Mapping

from . import ingest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_VALID = "DATA_VALID"
DATA_INVALID = "DATA_INVALID"
DATA_INCOMPLETE = "DATA_INCOMPLETE"
STATES = (DATA_VALID, DATA_INVALID, DATA_INCOMPLETE)

SEV_INVALID = "INVALID"
SEV_INCOMPLETE = "INCOMPLETE"

# Closed type vocabulary a contract may pin with ``type_vocabulary``.
TYPE_VOCABULARY = frozenset(
    {
        "int8",
        "int16",
        "int32",
        "int64",
        "uint32",
        "uint64",
        "float32",
        "float64",
        "utf8",
        "bool",
        "timestamp_ns",
        "timestamp_s",
    }
)

ARCHIVE_STATUSES = frozenset({"complete", "partial", "truncated", "incomplete"})


@dataclasses.dataclass(frozen=True)
class Reason:
    """One machine-readable admission finding."""

    check: str
    severity: str
    observed: Any
    expected: Any
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "check": self.check,
            "severity": self.severity,
            "observed": self.observed,
            "expected": self.expected,
            "detail": self.detail,
        }


@dataclasses.dataclass(frozen=True)
class Note:
    """A non-blocking, machine-readable observation about what was NOT verified.

    Notes never change a verdict. They exist so that a checked pass cannot hide
    an unverifiable claim (a streamed source that was never retained, a bounded
    sequence probe standing in for the full series): the verdict says what was
    proven, the note says what was asserted.
    """

    check: str
    observed: Any
    detail: str = ""

    def as_dict(self) -> dict:
        return {"check": self.check, "observed": self.observed, "detail": self.detail}


@dataclasses.dataclass
class Context:
    """Where declared manifest paths are resolved from.

    There is deliberately no switch that skips hash recomputation: every declared
    ``sha256`` is verified against the bytes on disk, so no caller can turn a
    corrupt file into DATA_VALID by asking the engine not to look.
    """

    root: str = REPO_ROOT


def _absent(check: str, observed: Any, expected: Any, detail: str = "") -> Reason:
    return Reason(check, SEV_INCOMPLETE, observed, expected, detail)


def _contradiction(check: str, observed: Any, expected: Any, detail: str = "") -> Reason:
    return Reason(check, SEV_INVALID, observed, expected, detail)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _resolve(root: str, path: Any) -> str:
    if not isinstance(path, str) or not path:
        return ""
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)


def _files(manifest: Mapping) -> list[Mapping]:
    return [entry for entry in manifest.get("files", ()) if isinstance(entry, Mapping)]


def _declared_fields(manifest: Mapping) -> list[dict]:
    fields = []
    for entry in manifest.get("fields", ()):
        if isinstance(entry, Mapping):
            fields.append(dict(entry))
        elif isinstance(entry, str):
            fields.append({"name": entry})
    return fields


def _field_map(manifest: Mapping) -> dict[Any, dict]:
    return {field.get("name"): field for field in _declared_fields(manifest)}


def _timestamps(manifest: Mapping) -> Any:
    records = manifest.get("records")
    if not isinstance(records, Mapping):
        return None
    return records.get("timestamps")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_epoch_seconds(value: Any) -> int | None:
    """Place a declared bucket id on the epoch grid, when its domain allows it.

    Bucket ids are epoch seconds in a contract whose timestamps are epoch-based;
    a free-form label (``"15:50_ET_NOII"``) cannot be placed on that grid and
    yields ``None``, which is reported as a note rather than assumed to match.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def _iso8601_seconds(value: Any) -> int | None:
    """Parse a human-readable ISO-8601 instant as epoch seconds (UTC default)."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.timezone.utc)
    return int(moment.timestamp())


def _iso8601_utc(seconds: Any) -> Any:
    if not _is_number(seconds):
        return None
    return (
        datetime.datetime.fromtimestamp(int(seconds), datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def _utc_date(seconds: Any) -> Any:
    if not _is_number(seconds):
        return None
    return datetime.datetime.fromtimestamp(int(seconds), datetime.timezone.utc).date().isoformat()


def _format_offset(seconds: int) -> str:
    sign = "+" if seconds >= 0 else "-"
    magnitude = abs(seconds)
    for unit, size in (("h", 3600), ("m", 60)):
        if magnitude % size == 0:
            return f"{sign}{magnitude // size}{unit}"
    return f"{sign}{magnitude}s"


def _grid_window(contract: Mapping, session: Any) -> tuple[int, int, int] | None:
    """The declared numeric bucket grid: ``(period, window_start, window_end)``."""
    period = contract.get("interval_period_seconds")
    if not _is_number(period) or period <= 0 or not isinstance(session, Mapping):
        return None
    start, end = session.get("window_start_unix"), session.get("window_end_unix")
    if not _is_number(start) or not _is_number(end):
        return None
    return int(period), int(start), int(end)


def _expected_bucket_ids(period: int, start: int, end: int) -> list[int]:
    """The exact bucket id set a declared window bounds + interval pins.

    Derivation rule (declarations only, never the observed ids)::

        ts_floor(t) = (t // period) * period          # floor onto the grid
        n           = (ts_floor(end) - ts_floor(start)) // period + 1
        ids         = [ts_floor(start) + k * period for k in 0 .. n-1]

    One id per period, both declared window ends inclusive.  A window whose bound
    is not grid-aligned is floored onto the grid, so the rule stays total while
    ``session.window_alignment`` reports the misalignment itself.
    """
    first = (start // period) * period
    last = (end // period) * period
    return [first + index * period for index in range((last - first) // period + 1)]


def _bucket_id_domains(manifest: Mapping) -> list[dict]:
    """Every declared bucket-id domain a grid identity can be checked against."""
    domains: list[dict] = []
    timestamps = _timestamps(manifest)
    if isinstance(timestamps, list):
        domains.append(
            {"name": "records.timestamps", "ids": list(timestamps), "unmaterialised": []}
        )
    intervals = manifest.get("intervals")
    if isinstance(intervals, list):
        present, absent = [], []
        for entry in intervals:
            if not isinstance(entry, Mapping):
                continue
            target = present if entry.get("present") is True else absent
            target.append(entry.get("id"))
        domains.append({"name": "intervals.id", "ids": present, "unmaterialised": absent})
    return domains


def _unplaceable_id_domains(manifest: Mapping, contract: Mapping) -> list[dict]:
    """Declared id domains whose values are not epoch seconds (nothing to compare)."""
    if not contract.get("require_full_interval_coverage"):
        return []
    findings = []
    for domain in _bucket_id_domains(manifest):
        values = domain["ids"] + domain["unmaterialised"]
        if values and not any(_as_epoch_seconds(value) is not None for value in values):
            findings.append({"domain": domain["name"], "sample_ids": values[:4], "count": len(values)})
    return findings


# --------------------------------------------------------------------------
# checks: each returns a (possibly empty) list of Reasons
# --------------------------------------------------------------------------


def _check_manifest_load(manifest: Any, contract: Mapping, ctx: Context) -> list[Reason]:
    if not isinstance(manifest, Mapping):
        return [_absent("manifest.load", type(manifest).__name__, "JSON object")]
    return []


def _check_sections(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    reasons = []
    for section in contract.get("required_sections", ()):
        value = manifest.get(section)
        empty = value is None or (isinstance(value, (dict, list, tuple, str)) and len(value) == 0)
        if empty:
            reasons.append(
                _absent(
                    "manifest.sections",
                    f"section '{section}' absent or empty",
                    f"section '{section}' present and non-empty",
                )
            )
    return reasons


def _check_source_identity(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    source = manifest.get("source")
    required = contract.get("required_source_fields", ())
    if not isinstance(source, Mapping):
        if not required:
            return []
        return [_absent("source.identity", "source block absent", "source block")]
    reasons = []
    for field in required:
        if source.get(field) in (None, "", []):
            reasons.append(
                _absent("source.identity", {field: source.get(field)}, f"non-empty source.{field}")
            )
    for field, expected in (contract.get("pinned_source") or {}).items():
        observed = source.get(field)
        if observed != expected:
            reasons.append(
                _contradiction(
                    "source.identity",
                    {field: observed},
                    {field: expected},
                    "source identity contradicts the pinned provenance",
                )
            )
    return reasons


def _check_schema_identity(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    expected = contract.get("expected_schema")
    expected_format = contract.get("expected_format")
    if not expected and not expected_format:
        return []
    schema = manifest.get("schema")
    if not isinstance(schema, Mapping):
        return [_absent("schema.identity", "schema block absent", "schema block")]
    reasons = []
    for key, expected_value, label in (
        ("contract_id", expected, "schema contract id"),
        ("format", expected_format, "container format"),
    ):
        if not expected_value:
            continue
        observed = schema.get(key)
        if observed is None:
            reasons.append(_absent("schema.identity", {key: None}, {key: expected_value}, label))
        elif observed != expected_value:
            reasons.append(
                _contradiction(
                    "schema.identity", {key: observed}, {key: expected_value}, f"{label} differs"
                )
            )
    return reasons


def _check_files_required(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    roles = [entry.get("role") for entry in _files(manifest)]
    reasons = []
    for role in contract.get("required_file_roles", ()):
        if role not in roles:
            reasons.append(
                _absent("files.required", f"declared roles={roles}", f"file with role '{role}'")
            )
    return reasons


def _check_files_hash(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    entries = _files(manifest)
    require = contract.get("require_hashes", False)
    pinned = contract.get("pinned_files") or {}
    reasons = []
    for entry in entries:
        role = entry.get("role")
        declared = entry.get("sha256")
        if entry.get("retained") is False:
            reasons.extend(_unretained_findings(entry, role, contract))
            continue
        if role in pinned and declared != pinned[role]:
            reasons.append(
                _contradiction(
                    "files.hash",
                    {role: declared},
                    {role: pinned[role]},
                    "declared hash differs from the pinned provenance hash",
                )
            )
            continue
        if not declared:
            if require or role in pinned:
                reasons.append(_absent("files.hash", {role: None}, {role: "sha256"}))
            continue
        path = _resolve(ctx.root, entry.get("path"))
        if not path or not os.path.isfile(path):
            reasons.append(
                _absent("files.hash", f"{role}: {entry.get('path')!r} not on disk", "file present")
            )
            continue
        observed = ingest.sha256_file(path)
        if observed != declared:
            reasons.append(
                _contradiction(
                    "files.hash",
                    {role: observed},
                    {role: declared},
                    f"recomputed sha256 of {entry.get('path')!r}",
                )
            )
            continue
        declared_bytes = entry.get("bytes")
        if declared_bytes is not None and declared_bytes != os.path.getsize(path):
            reasons.append(
                _contradiction(
                    "files.hash",
                    {f"{role}.bytes": os.path.getsize(path)},
                    {f"{role}.bytes": declared_bytes},
                    "declared byte count differs from disk",
                )
            )
    return reasons


def _unretained_findings(entry: Mapping, role: Any, contract: Mapping) -> list[Reason]:
    """A source that was streamed and not retained cannot be hashed from disk.

    Such an entry is admissible only where the contract allows it, and only when
    it declares the upstream provenance in full; the engine then records a note
    that the hash is a producer assertion (see _collect_notes).
    """
    if not contract.get("allow_unretained_files"):
        return [
            _contradiction(
                "files.hash",
                {role: "retained=false"},
                {role: "retained=true with a local sha256"},
                "unretained source declared where the contract requires retained inputs",
            )
        ]
    reasons = []
    for key in ("upstream_url", "upstream_sha256", "bytes"):
        if entry.get(key) in (None, ""):
            reasons.append(
                _absent("files.hash", {f"{role}.{key}": entry.get(key)}, f"non-empty {role}.{key}")
            )
    upstream = entry.get("upstream_sha256")
    if upstream not in (None, "") and not _is_sha256(upstream):
        reasons.append(
            _contradiction(
                "files.hash",
                {f"{role}.upstream_sha256": upstream},
                {"sha256": "64 hex characters"},
                "malformed upstream digest",
            )
        )
    size = entry.get("bytes")
    if size is not None and (not isinstance(size, int) or size <= 0):
        reasons.append(
            _contradiction("files.hash", {f"{role}.bytes": size}, {"bytes": "positive integer"})
        )
    return reasons


def _check_archive_completeness(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    entries = _files(manifest)
    require_status = contract.get("require_archive_status", False)
    reasons = []
    for entry in entries:
        role = entry.get("role")
        status = entry.get("status")
        complete = entry.get("complete")
        if status in ("partial", "truncated", "incomplete") or complete is False:
            reasons.append(
                _contradiction(
                    "archive.completeness",
                    {role: status if status is not None else complete},
                    {role: "complete"},
                    "declared object is not whole",
                )
            )
        elif status is None and complete is None:
            if require_status:
                reasons.append(_absent("archive.completeness", {role: None}, {role: "status"}))
        elif status is not None and status not in ARCHIVE_STATUSES:
            reasons.append(
                _contradiction(
                    "archive.completeness",
                    {role: status},
                    {role: sorted(ARCHIVE_STATUSES)},
                    "unrecognised archive status",
                )
            )
        expected_bytes = entry.get("expected_bytes")
        if expected_bytes is not None:
            path = _resolve(ctx.root, entry.get("path"))
            if path and os.path.isfile(path) and os.path.getsize(path) != expected_bytes:
                reasons.append(
                    _contradiction(
                        "archive.completeness",
                        {f"{role}.bytes": os.path.getsize(path)},
                        {f"{role}.expected_bytes": expected_bytes},
                        "object is shorter than its declared full length",
                    )
                )
    return reasons


def _check_fields_required(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    names = [field.get("name") for field in _declared_fields(manifest)]
    reasons = []
    for required in contract.get("required_fields", ()):
        if required not in names:
            reasons.append(
                _absent("fields.required", f"declared fields={names}", f"field '{required}'")
            )
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    if duplicates:
        reasons.append(
            _contradiction("fields.required", duplicates, "unique field names", "duplicate field")
        )
    return reasons


def _check_fields_types(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    expected_types = contract.get("field_types") or {}
    vocabulary = contract.get("type_vocabulary")
    vocabulary = frozenset(vocabulary) if vocabulary else None
    reasons = []
    for field in _declared_fields(manifest):
        name, declared = field.get("name"), field.get("type")
        if declared is None:
            reasons.append(
                _absent(
                    "fields.types",
                    {name: None},
                    {name: expected_types.get(name, "a declared type")},
                )
            )
            continue
        if vocabulary is not None and declared not in vocabulary:
            reasons.append(
                _contradiction(
                    "fields.types",
                    {name: declared},
                    {name: sorted(vocabulary)},
                    "type outside the contract's vocabulary",
                )
            )
        elif name in expected_types and declared != expected_types[name]:
            reasons.append(
                _contradiction(
                    "fields.types",
                    {name: declared},
                    {name: expected_types[name]},
                    "declared type differs from the contract",
                )
            )
    return reasons


def _check_timestamp_identity(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    name = contract.get("timestamp_field")
    if not name:
        return []
    field = _field_map(manifest).get(name)
    if field is None:
        return [
            _absent(
                "timestamp.identity",
                f"timestamp field '{name}' absent",
                f"'{name}' with {contract.get('timestamp_semantics')} semantics",
            )
        ]
    reasons = []
    for key, expected, label in (
        ("semantics", contract.get("timestamp_semantics"), "timestamp semantics"),
        ("identity", contract.get("timestamp_identity"), "timestamp identity field"),
        ("timezone", contract.get("timezone"), "timestamp timezone"),
    ):
        if not expected:
            continue
        observed = field.get(key)
        if observed is None:
            reasons.append(_absent("timestamp.identity", {name: {key: None}}, {key: expected}, label))
        elif observed != expected:
            reasons.append(
                _contradiction(
                    "timestamp.identity",
                    {name: {key: observed}},
                    {key: expected},
                    f"{label} differs from the contract",
                )
            )
    return reasons


def _check_timezone_contract(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    expected = contract.get("timezone")
    if not expected:
        return []
    session = manifest.get("session")
    if not isinstance(session, Mapping):
        return [_absent("timezone.contract", "session block absent", f"session.timezone == {expected}")]
    observed = session.get("timezone")
    if observed is None:
        return [_absent("timezone.contract", {"timezone": None}, {"timezone": expected})]
    if observed != expected:
        return [
            _contradiction(
                "timezone.contract",
                observed,
                expected,
                "session timezone differs from the contract's session timezone",
            )
        ]
    return []


def _check_session_identity(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    expected = contract.get("expected_session_date")
    allowed = contract.get("allowed_session_dates")
    require_window = contract.get("require_session_window", False)
    if expected is None and not allowed and not require_window:
        return []
    session = manifest.get("session")
    if not isinstance(session, Mapping):
        return [_absent("session.identity", "session block absent", "session block")]
    reasons = []
    observed = session.get("coverage_date")
    if expected is not None:
        if observed is None:
            reasons.append(_absent("session.identity", {"coverage_date": None}, {"coverage_date": expected}))
        elif observed != expected:
            reasons.append(
                _contradiction(
                    "session.identity",
                    observed,
                    expected,
                    "coverage date differs from the frozen session",
                )
            )
    elif allowed:
        if observed is None:
            reasons.append(
                _absent("session.identity", {"coverage_date": None}, {"coverage_date in": sorted(allowed)})
            )
        elif observed not in allowed:
            reasons.append(
                _contradiction(
                    "session.identity", observed, sorted(allowed), "coverage date outside the allowed set"
                )
            )
    if require_window:
        for key in ("window_start_unix", "window_end_unix"):
            if not isinstance(session.get(key), (int, float)):
                reasons.append(
                    _absent("session.identity", {key: session.get(key)}, f"numeric session.{key}")
                )
    return reasons


def _check_session_completeness(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    require_frame = contract.get("require_terminating_frame", False)
    require_stream = contract.get("require_stream_completeness", False)
    required_event = contract.get("required_final_event")
    if not require_frame and not require_stream and not required_event:
        return []
    session = manifest.get("session")
    if not isinstance(session, Mapping):
        return [_absent("session.completeness", "session block absent", "session block")]
    reasons = []
    if require_frame:
        flag = session.get("terminating_frame_present")
        if flag is None:
            reasons.append(
                _absent("session.completeness", {"terminating_frame_present": None}, "true")
            )
        elif flag is not True:
            reasons.append(
                _contradiction(
                    "session.completeness",
                    {"terminating_frame_present": flag},
                    "true",
                    "stream lacks the frame that proves it is complete",
                )
            )
    if require_stream:
        markers = session.get("completeness_markers")
        if not isinstance(markers, Mapping):
            reasons.append(
                _absent(
                    "session.completeness",
                    "session.completeness_markers absent",
                    "stream completeness markers",
                )
            )
        else:
            for key, expected in (contract.get("stream_completeness_markers") or {}).items():
                observed = markers.get(key)
                if observed is None:
                    reasons.append(
                        _absent("session.completeness", {key: None}, {key: expected})
                    )
                elif observed != expected:
                    reasons.append(
                        _contradiction(
                            "session.completeness",
                            {key: observed},
                            {key: expected},
                            "stream completeness marker differs from the contract",
                        )
                    )
            placeholders = [
                key for key, value in markers.items() if value in (None, "", [])
            ]
            if placeholders:
                reasons.append(
                    _absent("session.completeness", {"unset_markers": sorted(placeholders)}, "every declared marker has a value")
                )
        evidence_role = contract.get("completeness_evidence_role")
        if evidence_role and evidence_role not in [entry.get("role") for entry in _files(manifest)]:
            reasons.append(
                _absent(
                    "session.completeness",
                    {"completeness_evidence_role": evidence_role},
                    f"retained artifact with role '{evidence_role}' carrying the markers",
                )
            )
    if required_event:
        observed = session.get("final_system_event")
        if observed is None:
            reasons.append(
                _absent("session.completeness", {"final_system_event": None}, required_event)
            )
        elif observed != required_event:
            reasons.append(
                _contradiction(
                    "session.completeness",
                    observed,
                    required_event,
                    "final session event differs from the required terminating event",
                )
            )
    return reasons


def _check_records_session_window(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    if not contract.get("require_records"):
        return []
    session = manifest.get("session")
    timestamps = _timestamps(manifest)
    if not isinstance(session, Mapping) or timestamps is None:
        return []
    open_ns = session.get("session_open_ns")
    close_ns = session.get("session_close_ns")
    if open_ns is None or close_ns is None:
        open_ns = session.get("window_start_unix", open_ns)
        close_ns = session.get("window_end_unix", close_ns)
    if open_ns is None or close_ns is None:
        return [
            _absent(
                "records.session_window",
                {"session_open": session.get("session_open_ns"), "window_start_unix": session.get("window_start_unix")},
                "declared session bounds",
            )
        ]
    if not timestamps:
        return [_absent("records.session_window", "empty timestamp series", "at least one event")]
    first, last = min(timestamps), max(timestamps)
    if first < open_ns or last > close_ns:
        return [
            _contradiction(
                "records.session_window",
                {"first_ns": first, "last_ns": last},
                {"session_open_ns": open_ns, "session_close_ns": close_ns},
                "events fall outside the declared session window",
            )
        ]
    return []


def _check_session_window_alignment(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    """Declared session window against the redundant anchors the manifest carries.

    A consistent global shift of every epoch timestamp — every bucket moved to a
    different, equally regular window — is invisible to ordering, monotonicity
    and window-containment checks *when the manifest shifts its own declared
    window along with the data*: internally consistent, and wrong.  Nothing
    inside the shifted data can break that tie, so this check reads the
    manifest's redundant statements of the same fact:

    * ``session.window_start_utc`` / ``window_end_utc`` (human-readable ISO-8601
      mirrors of the epoch bounds) must name the same instants as
      ``session.window_start_unix`` / ``window_end_unix``;
    * ``session.coverage_date`` must be the UTC calendar date of
      ``window_start_unix``.

    A disagreement is INVALID — the manifest contradicts itself — and the offset
    is named in seconds so the shift is identifiable, not merely flagged.

    Limits, stated rather than pretended: a manifest that shifts the mirrors, the
    coverage date and the data together is not detectable from the manifest
    alone, because the declared contract pins no absolute clock independent of
    the window the data declares.  A contract whose timestamps are local
    wall-clock nanoseconds since midnight (AUCTION) carries no epoch to align at
    all; there the frozen coverage date and the declared session bounds are the
    only anchors, and only the manifest's own mirrors can expose a shift.
    """
    session = manifest.get("session")
    if not isinstance(session, Mapping):
        return []
    reasons = []
    for mirror_key, epoch_key in (
        ("window_start_utc", "window_start_unix"),
        ("window_end_utc", "window_end_unix"),
    ):
        declared, seconds = session.get(mirror_key), session.get(epoch_key)
        if declared is None or not _is_number(seconds):
            continue
        parsed = _iso8601_seconds(declared)
        if parsed is None:
            reasons.append(
                _absent(
                    "session.window_alignment",
                    {mirror_key: declared},
                    "an ISO-8601 instant matching the epoch bound",
                    "mirror of a declared epoch bound is unreadable",
                )
            )
        elif parsed != int(seconds):
            delta = int(seconds) - parsed
            reasons.append(
                _contradiction(
                    "session.window_alignment",
                    {epoch_key: int(seconds), "utc": _iso8601_utc(seconds)},
                    {mirror_key: declared},
                    f"epoch bound is displaced from its own declared mirror by "
                    f"{delta} seconds ({_format_offset(delta)})",
                )
            )
    if contract.get("timezone") == "UTC":
        declared_date, start = session.get("coverage_date"), session.get("window_start_unix")
        derived_date = _utc_date(start)
        if isinstance(declared_date, str) and derived_date and declared_date != derived_date:
            reasons.append(
                _contradiction(
                    "session.window_alignment",
                    {"coverage_date": declared_date, "window_start_unix": int(start)},
                    {"coverage_date": derived_date},
                    "declared coverage date is not the UTC date of the declared window start",
                )
            )
    return reasons


def _check_instrument_identity(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    instrument = manifest.get("instrument")
    reasons = []
    if contract.get("instrument_required") and not isinstance(instrument, Mapping):
        return [_absent("instrument.identity", "instrument block absent", "instrument block")]
    if isinstance(instrument, Mapping):
        expected = contract.get("required_instrument")
        if expected:
            observed = instrument.get("symbol")
            if observed is None:
                reasons.append(_absent("instrument.identity", {"symbol": None}, {"symbol": expected}))
            elif observed != expected:
                reasons.append(
                    _contradiction(
                        "instrument.identity", observed, expected, "instrument is not the contracted security"
                    )
                )
        allowed = contract.get("allowed_instruments")
        if allowed:
            observed = instrument.get("symbol")
            if observed is None:
                reasons.append(
                    _absent("instrument.identity", {"symbol": None}, {"symbol in": sorted(allowed)})
                )
            elif observed not in allowed:
                reasons.append(
                    _contradiction(
                        "instrument.identity",
                        observed,
                        sorted(allowed),
                        "instrument outside the contracted set",
                    )
                )
        venues = contract.get("allowed_venues")
        if venues:
            observed = instrument.get("venue")
            if observed is None:
                reasons.append(
                    _absent("instrument.identity", {"venue": None}, {"venue in": sorted(venues)})
                )
            elif observed not in venues:
                reasons.append(
                    _contradiction(
                        "instrument.identity", observed, sorted(venues), "venue outside the contracted set"
                    )
                )
        prefixes = contract.get("allowed_instrument_prefixes")
        secondaries = instrument.get("secondary_instruments")
        if prefixes or secondaries:
            declared = [instrument.get("symbol")]
            for entry in secondaries or ():
                declared.append(entry.get("symbol") if isinstance(entry, Mapping) else None)
            unnamed = [
                index
                for index, symbol in enumerate(declared)
                if not isinstance(symbol, str) or not symbol
            ]
            if unnamed:
                reasons.append(
                    _absent(
                        "instrument.identity",
                        {"unnamed_instruments": unnamed},
                        "every declared instrument carries a symbol",
                        "a declared instrument (primary or secondary) has no symbol",
                    )
                )
            elif prefixes:
                stray = sorted(
                    symbol for symbol in declared if not symbol.startswith(tuple(prefixes))
                )
                if stray:
                    reasons.append(
                        _contradiction(
                            "instrument.identity",
                            {"outside_prefixes": stray},
                            {"prefixes": sorted(prefixes)},
                            "a declared instrument lies outside the contracted product family",
                        )
                    )
    if contract.get("instrument_must_match_universe"):
        members = (manifest.get("universe") or {}).get("members") if isinstance(
            manifest.get("universe"), Mapping
        ) else None
        records = manifest.get("records")
        symbols = records.get("symbols") if isinstance(records, Mapping) else None
        if symbols is None:
            reasons.append(_absent("instrument.identity", "records.symbols absent", "symbol series"))
        elif not members:
            reasons.append(_absent("instrument.identity", "universe.members absent", "member set"))
        else:
            stray = sorted({symbol for symbol in symbols if symbol not in set(members)})
            if stray:
                reasons.append(
                    _contradiction(
                        "instrument.identity",
                        {"outside_universe": stray},
                        {"universe_size": len(members)},
                        "records contain instruments outside the point-in-time universe",
                    )
                )
    return reasons


def _check_universe_pit(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    if not contract.get("require_pit_universe"):
        return []
    universe = manifest.get("universe")
    if not isinstance(universe, Mapping):
        return [_absent("universe.pit", "universe block absent", "universe block with pit=true")]
    reasons = []
    pit = universe.get("pit")
    if pit is None:
        reasons.append(_absent("universe.pit", {"pit": None}, {"pit": True}))
    elif pit is not True:
        reasons.append(
            _contradiction(
                "universe.pit", {"pit": pit}, {"pit": True}, "universe is not point-in-time"
            )
        )
    rule = contract.get("universe_rule_id")
    if rule:
        observed = universe.get("rule_id")
        if observed is None:
            reasons.append(_absent("universe.pit", {"rule_id": None}, {"rule_id": rule}))
        elif observed != rule:
            reasons.append(
                _contradiction(
                    "universe.pit",
                    {"rule_id": observed},
                    {"rule_id": rule},
                    "universe rule differs from the frozen rule",
                )
            )
    if not universe.get("members"):
        reasons.append(_absent("universe.pit", "members absent or empty", "non-empty member set"))
    return reasons


def _check_ordering_causal(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    timestamps = _timestamps(manifest)
    if timestamps is None:
        if contract.get("require_records"):
            return [_absent("ordering.causal", "records.timestamps absent", "timestamp series")]
        return []
    for index in range(1, len(timestamps)):
        if timestamps[index] < timestamps[index - 1]:
            return [
                _contradiction(
                    "ordering.causal",
                    {"index": index, "timestamp_ns": timestamps[index], "previous_ns": timestamps[index - 1]},
                    "non-decreasing timestamps",
                    "event appears out of order",
                )
            ]
    return []


def _check_timestamps_monotonic(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    if not contract.get("require_strict_timestamps"):
        return []
    timestamps = _timestamps(manifest)
    if timestamps is None:
        return [_absent("timestamps.monotonic", "records.timestamps absent", "timestamp series")]
    for index in range(1, len(timestamps)):
        if timestamps[index] <= timestamps[index - 1]:
            return [
                _contradiction(
                    "timestamps.monotonic",
                    {"index": index, "timestamp_ns": timestamps[index]},
                    "strictly increasing timestamps",
                    "duplicate or repeated timestamp",
                )
            ]
    return []


def _sequence_declaration(manifest: Mapping, contract: Mapping) -> tuple[Any, list[Reason]]:
    """Resolve the expected first sequence value.

    A contract may pin the start (``sequence_start``) or require the producer to
    declare the observed start (``sequence_start_from_manifest``), which is the
    only honest option for feeds whose transport sequence persists across
    sessions (CME MDP3 packet sequence).  A declared start must carry a stated
    basis and must agree with a pinned start when both are present.
    """
    pin = contract.get("sequence_start")
    if not contract.get("sequence_start_from_manifest"):
        return (1 if pin is None else pin), []
    records = manifest.get("records") if isinstance(manifest.get("records"), Mapping) else {}
    declared = records.get("sequence_start")
    if not isinstance(declared, int) or isinstance(declared, bool):
        return None, [
            _absent("sequence.integrity", {"sequence_start": declared}, "integer records.sequence_start")
        ]
    basis = records.get("sequence_start_basis")
    if not isinstance(basis, str) or not basis.strip():
        return None, [
            _absent(
                "sequence.integrity",
                {"sequence_start_basis": basis},
                "non-empty records.sequence_start_basis",
            )
        ]
    if isinstance(pin, int) and not isinstance(pin, bool) and pin != declared:
        return None, [
            _contradiction(
                "sequence.integrity",
                {"sequence_start": declared},
                {"sequence_start": pin},
                "producer-declared sequence start differs from the pinned start",
            )
        ]
    return declared, []


def _check_sequence_run(run: Any, expected: Any, label: str) -> list[Reason]:
    seen = set()
    for index, value in enumerate(run):
        if value in seen:
            return [
                _contradiction(
                    "sequence.integrity",
                    {"run": label, "index": index, "value": value},
                    f"strictly increasing from {expected}",
                    f"duplicate sequence value in the {label} run",
                )
            ]
        seen.add(value)
        if value != expected:
            kind = "gap" if value > expected else "regression"
            return [
                _contradiction(
                    "sequence.integrity",
                    {"run": label, "index": index, "value": value},
                    expected,
                    f"sequence {kind} in the {label} run: expected {expected}",
                )
            ]
        expected += 1
    return []


def _check_sequence_probe(
    manifest: Mapping, contract: Mapping, head: Any, start: Any
) -> list[Reason]:
    """Bounded probe: two contiguous runs plus a whole-window density identity.

    The full packet series of a modern feed is millions of rows, far too large to
    carry in a manifest.  The contract may instead require a head run, a tail run
    and the declared first / last / total values: because the contract declares
    the series dense (step exactly one per row), ``last - first + 1 == total``
    proves the whole window has no gap, which the two runs alone could not.
    """
    probe = contract["sequence_probe"]
    records = manifest.get("records") if isinstance(manifest.get("records"), Mapping) else {}
    tail = records.get("sequence_tail")
    if not isinstance(tail, list) or not tail:
        return [_absent("sequence.integrity", {"sequence_tail": tail}, "tail run of the series")]
    for key in ("sequence_first", "sequence_last", "sequence_count_total"):
        value = records.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            return [_absent("sequence.integrity", {key: value}, f"integer records.{key}")]
    head_rows = probe.get("head_rows", 1)
    tail_rows = probe.get("tail_rows", 1)
    if len(head) < head_rows or len(tail) < tail_rows:
        return [
            _absent(
                "sequence.integrity",
                {"head_rows": len(head), "tail_rows": len(tail)},
                {"head_rows": head_rows, "tail_rows": tail_rows},
                "probe runs shorter than the contract's probe size",
            )
        ]
    findings = _check_sequence_run(head, start, "head")
    if findings:
        return findings
    findings = _check_sequence_run(tail, tail[0], "tail")
    if findings:
        return findings
    first, last, total = (
        records["sequence_first"],
        records["sequence_last"],
        records["sequence_count_total"],
    )
    if head[0] != first:
        return [
            _contradiction(
                "sequence.integrity",
                {"head_first": head[0]},
                {"sequence_first": first},
                "declared first value differs from the head run",
            )
        ]
    if tail[-1] != last:
        return [
            _contradiction(
                "sequence.integrity",
                {"tail_last": tail[-1]},
                {"sequence_last": last},
                "declared last value differs from the tail run",
            )
        ]
    if head[-1] >= tail[0]:
        return [
            _contradiction(
                "sequence.integrity",
                {"head_last": head[-1], "tail_first": tail[0]},
                "head run strictly before the tail run",
                "probe runs overlap or are inverted",
            )
        ]
    span = last - first + 1
    if span != total:
        return [
            _contradiction(
                "sequence.integrity",
                {"span": span, "sequence_count_total": total},
                {"sequence_count_total": span},
                "declared row count is inconsistent with the first/last span: the series is not dense",
            )
        ]
    return []


def _check_sequence_integrity(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    records = manifest.get("records")
    sequence = records.get("sequence") if isinstance(records, Mapping) else None
    required = contract.get("require_sequence", False)
    if sequence is None:
        if required:
            return [_absent("sequence.integrity", "records.sequence absent", "sequence series")]
        return []
    start, findings = _sequence_declaration(manifest, contract)
    if findings:
        return findings
    if contract.get("sequence_probe"):
        return _check_sequence_probe(manifest, contract, sequence, start)
    return _check_sequence_run(sequence, start, "declared")


def _check_records_duplicates(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    records = manifest.get("records")
    keys = records.get("keys") if isinstance(records, Mapping) else None
    if keys is None:
        if contract.get("require_unique_keys"):
            return [_absent("records.duplicates", "records.keys absent", "event key series")]
        return []
    seen = set()
    for index, key in enumerate(keys):
        marker = key if isinstance(key, (str, int, float, bool)) else json.dumps(key, sort_keys=True)
        if marker in seen:
            return [
                _contradiction(
                    "records.duplicates",
                    {"index": index, "key": key},
                    "unique event keys",
                    "duplicate event identity",
                )
            ]
        seen.add(marker)
    return []


def _check_intervals_coverage(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    required = contract.get("required_intervals") or []
    full = contract.get("require_full_interval_coverage", False)
    if not required and not full:
        return []
    intervals = manifest.get("intervals")
    if not isinstance(intervals, list) or not intervals:
        return [_absent("intervals.coverage", "intervals absent", "interval list")]
    by_id = {entry.get("id"): entry for entry in intervals if isinstance(entry, Mapping)}
    reasons = []
    for required_id in required:
        entry = by_id.get(required_id)
        if entry is None:
            reasons.append(
                _absent("intervals.coverage", f"interval '{required_id}' absent", f"'{required_id}' present")
            )
        elif entry.get("present") is not True:
            reasons.append(
                _absent(
                    "intervals.coverage",
                    {required_id: entry.get("present")},
                    {required_id: True},
                    "interval declared but not present in the data",
                )
            )
    if full:
        period = contract.get("interval_period_seconds")
        session = manifest.get("session") if isinstance(manifest.get("session"), Mapping) else {}
        start, end = session.get("window_start_unix"), session.get("window_end_unix")
        if not period or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            reasons.append(
                _absent(
                    "intervals.coverage",
                    {"period": period, "start": start, "end": end},
                    "interval period and session window",
                )
            )
        else:
            expected_count = int((end - start) // period) + 1
            present = sum(1 for entry in by_id.values() if entry.get("present") is True)
            if present < expected_count:
                missing = sorted(
                    entry.get("id")
                    for entry in by_id.values()
                    if entry.get("present") is not True
                )
                reasons.append(
                    _absent(
                        "intervals.coverage",
                        {"present": present, "declared": len(by_id), "missing": missing},
                        {"buckets_in_window": expected_count},
                        "hourly/periodic buckets missing from the availability-derived window",
                    )
                )
    return reasons


def _check_intervals_grid_identity(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    """Grid IDENTITY: the observed bucket ids must EQUAL the declared grid.

    A contract that requires full interval coverage (``interval_period_seconds``
    together with session window bounds) pins the exact expected id set by the
    derivation rule documented on :func:`_expected_bucket_ids`: floor the window
    onto the grid, step one period per bucket, both ends inclusive.

    Comparing cardinality — the historical check — cannot see a bucket set that
    is shifted by a whole period, nor one that trades a missing bucket for an
    extra bucket outside the window: both leave the count untouched.  This check
    compares the sets, per declared id domain (``records.timestamps`` and
    ``intervals[].id``, the latter restricted to ids declared present), and
    reports separate machine-readable reasons:

    * ``duplicated_ids``    — one bucket id claimed twice (INVALID);
    * ``shifted_seconds``   — the whole set is the expected grid displaced by one
      constant offset, which is named (INVALID): a shifted grid is a different
      window, not a pass;
    * ``missing_ids``       — expected buckets absent from the data (INCOMPLETE:
      the evidence is absent, which is exactly what a real gap looks like);
    * ``unexpected_ids``    — observed ids outside the declared window (INVALID).

    An id domain whose values are not epoch seconds cannot be placed on the grid
    at all; that is recorded as a note (see ``_collect_notes``), never counted as
    a pass.
    """
    if not contract.get("require_full_interval_coverage"):
        return []
    session = manifest.get("session")
    window = _grid_window(contract, session)
    if window is None:
        return [
            _absent(
                "intervals.grid_identity",
                {
                    "interval_period_seconds": contract.get("interval_period_seconds"),
                    "window_start_unix": session.get("window_start_unix")
                    if isinstance(session, Mapping)
                    else None,
                    "window_end_unix": session.get("window_end_unix")
                    if isinstance(session, Mapping)
                    else None,
                },
                "interval period and session window bounds to derive the expected bucket ids",
            )
        ]
    period, start, end = window
    expected = _expected_bucket_ids(period, start, end)
    expected_set = set(expected)
    reasons: list[Reason] = []
    for domain in _bucket_id_domains(manifest):
        placed = [value for value in (_as_epoch_seconds(raw) for raw in domain["ids"]) if value is not None]
        if not placed:
            # Nothing in this id domain can be placed on the epoch grid (free-form
            # labels, or no ids declared at all): the domain's own defect, if any,
            # is reported by intervals.coverage / records.session_window, and the
            # unreadable labels are recorded as a note rather than assumed equal.
            continue
        counts = collections.Counter(placed)
        duplicated = sorted(value for value, seen in counts.items() if seen > 1)
        if duplicated:
            reasons.append(
                _contradiction(
                    "intervals.grid_identity",
                    {
                        "domain": domain["name"],
                        "duplicated_ids": duplicated[:8],
                        "duplicated_count": len(duplicated),
                    },
                    {"period_seconds": period},
                    "the same bucket id is claimed more than once",
                )
            )
        observed = set(placed)
        if len(placed) == len(expected):
            deltas = {value - expected_id for value, expected_id in zip(sorted(placed), expected)}
            if len(deltas) == 1:
                delta = deltas.pop()
                if delta:
                    reasons.append(
                        _contradiction(
                            "intervals.grid_identity",
                            {"domain": domain["name"], "shifted_seconds": delta},
                            {
                                "window_start_unix": start,
                                "window_end_unix": end,
                                "period_seconds": period,
                            },
                            f"bucket ids are the declared grid displaced by {delta} seconds "
                            f"({_format_offset(delta)}): the observed set is a different window, "
                            "not the declared one",
                        )
                    )
                    continue
        missing = sorted(expected_set - observed)
        if missing:
            reasons.append(
                _absent(
                    "intervals.grid_identity",
                    {"domain": domain["name"], "missing_ids": missing[:8], "missing_count": len(missing)},
                    {"buckets_in_window": len(expected), "window_start_unix": start, "window_end_unix": end},
                    "bucket ids absent from the declared window grid",
                )
            )
        declared_absent = sorted(
            value
            for value in (_as_epoch_seconds(raw) for raw in domain["unmaterialised"])
            if value is not None and value in expected_set
        )
        if declared_absent:
            reasons.append(
                _absent(
                    "intervals.grid_identity",
                    {
                        "domain": domain["name"],
                        "declared_but_absent": declared_absent[:8],
                        "count": len(declared_absent),
                    },
                    "every declared bucket materialised in the data",
                    "bucket id declared in the interval list but not present in the data",
                )
            )
        extra = sorted(observed - expected_set)
        if extra:
            reasons.append(
                _contradiction(
                    "intervals.grid_identity",
                    {"domain": domain["name"], "unexpected_ids": extra[:8], "unexpected_count": len(extra)},
                    {"window_start_unix": start, "window_end_unix": end, "period_seconds": period},
                    "bucket ids outside the declared window grid",
                )
            )
    return reasons


def _check_coverage_claim(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    """A coverage count or ratio must be recomputable from the manifest's records.

    Contract-gated by ``coverage_units == "records"``: only where the contract
    says the coverage block counts records (one row per fully paired bucket) is
    the record list the unit the claim is about.  The claim is then checked
    against what the records can evidence, in the direction that hides a defect
    — overstating coverage:

    * ``admitted`` above the grid-aligned record buckets the list actually
      carries;
    * a ``ratio`` above what those records support (``available / qualified``);
    * fewer ``missing_buckets`` than the declared grid is short of;
    * fewer ``duplicate_buckets`` than the record list contains;
    * ``window_hours`` that is not the declared window's bucket count;
    * ``records.count`` that is not the length of the declared record list.

    Each is INVALID with the observed and claimed values recorded: a manifest may
    not assert a coverage claim its own records do not support.  A deliberately
    conservative claim *below* what the records support is not a contradiction —
    the deficit it hides is still reported as a gap by ``intervals.coverage`` and
    ``intervals.grid_identity`` (INCOMPLETE), never as a pass.
    """
    if contract.get("coverage_units") != "records":
        return []
    coverage = manifest.get("coverage")
    records = manifest.get("records")
    if not isinstance(coverage, Mapping) or not isinstance(records, Mapping):
        return []
    timestamps = _timestamps(manifest)
    if not isinstance(timestamps, list):
        return []
    placed = [value for value in (_as_epoch_seconds(raw) for raw in timestamps) if value is not None]
    distinct = set(placed)
    window = _grid_window(contract, manifest.get("session"))
    expected = _expected_bucket_ids(*window) if window else None
    if expected is not None:
        available, buckets = len(distinct & set(expected)), len(expected)
    else:
        available, buckets = len(distinct), None

    reasons: list[Reason] = []
    declared_count = records.get("count")
    if _is_number(declared_count) and int(declared_count) != len(timestamps):
        reasons.append(
            _contradiction(
                "coverage.claim",
                {"records.count": declared_count},
                {"timestamps_declared": len(timestamps)},
                "declared record count differs from the declared record list",
            )
        )
    admitted, qualified, ratio = (
        coverage.get("admitted"),
        coverage.get("qualified"),
        coverage.get("ratio"),
    )
    if _is_number(admitted) and admitted > available:
        reasons.append(
            _contradiction(
                "coverage.claim",
                {"admitted": admitted, "supported_by_records": available},
                {"admitted": available},
                "admitted coverage exceeds what the record list carries",
            )
        )
    if _is_number(ratio) and _is_number(qualified) and qualified > 0:
        supported_ratio = available / qualified
        if ratio > supported_ratio + 1e-9:
            reasons.append(
                _contradiction(
                    "coverage.claim",
                    {"ratio": ratio, "admitted": admitted, "qualified": qualified},
                    {"ratio": supported_ratio, "supported_by_records": available},
                    "declared coverage ratio exceeds what the record list supports",
                )
            )
    if buckets is not None:
        claimed_missing = coverage.get("missing_buckets")
        if _is_number(claimed_missing) and claimed_missing < buckets - available:
            reasons.append(
                _contradiction(
                    "coverage.claim",
                    {"missing_buckets": claimed_missing},
                    {"missing_buckets": buckets - available},
                    "declared missing bucket count is smaller than the declared grid is short of",
                )
            )
        claimed_hours = coverage.get("window_hours")
        if _is_number(claimed_hours) and int(claimed_hours) != buckets:
            reasons.append(
                _contradiction(
                    "coverage.claim",
                    {"window_hours": claimed_hours},
                    {"window_hours": buckets},
                    "declared window length is not the bucket count of the declared window",
                )
            )
    claimed_duplicates = coverage.get("duplicate_buckets")
    if _is_number(claimed_duplicates) and claimed_duplicates < len(placed) - len(distinct):
        reasons.append(
            _contradiction(
                "coverage.claim",
                {"duplicate_buckets": claimed_duplicates},
                {"duplicate_buckets": len(placed) - len(distinct)},
                "declared duplicate bucket count is smaller than the record list contains",
            )
        )
    return reasons


def _check_coverage_contract(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    tolerance = contract.get("coverage_tolerance")
    if tolerance is None:
        return []
    coverage = manifest.get("coverage")
    if not isinstance(coverage, Mapping):
        return [_absent("coverage.contract", "coverage block absent", f"coverage >= {tolerance}")]
    qualified, admitted = coverage.get("qualified"), coverage.get("admitted")
    if not isinstance(qualified, (int, float)) or not isinstance(admitted, (int, float)):
        return [
            _absent(
                "coverage.contract",
                {"qualified": qualified, "admitted": admitted},
                {"qualified": "number", "admitted": "number"},
            )
        ]
    if qualified <= 0:
        return [_absent("coverage.contract", {"qualified": qualified}, {"qualified": "> 0"})]
    ratio = admitted / qualified
    declared = coverage.get("ratio")
    if declared is not None and abs(declared - ratio) > 1e-9:
        return [
            _contradiction(
                "coverage.contract",
                {"ratio": declared},
                {"ratio": ratio},
                "declared coverage ratio is inconsistent with its own counts",
            )
        ]
    if ratio + 1e-12 < tolerance:
        return [
            _absent(
                "coverage.contract",
                {"ratio": ratio, "admitted": admitted, "qualified": qualified},
                {"tolerance": tolerance},
                "coverage below the preregistered tolerance",
            )
        ]
    return []


def _check_objects_present(manifest: Mapping, contract: Mapping, ctx: Context) -> list[Reason]:
    reasons = []
    for required in contract.get("required_objects", ()):
        if not isinstance(required, Mapping):
            continue
        label = required.get("id") or required.get("path")
        path = _resolve(ctx.root, required.get("path"))
        if not path or not os.path.isfile(path):
            reasons.append(_absent("objects.present", label, "object present on disk"))
            continue
        floor = required.get("min_bytes")
        size = os.path.getsize(path)
        if floor is not None and size < floor:
            reasons.append(
                _contradiction(
                    "objects.present",
                    {"bytes": size},
                    {"min_bytes": floor},
                    "required object is below the contract's size floor",
                )
            )
    return reasons


CHECKS: tuple[tuple[str, Callable[[Mapping, Mapping, Context], list[Reason]]], ...] = (
    ("manifest.load", _check_manifest_load),
    ("manifest.sections", _check_sections),
    ("source.identity", _check_source_identity),
    ("schema.identity", _check_schema_identity),
    ("files.required", _check_files_required),
    ("files.hash", _check_files_hash),
    ("archive.completeness", _check_archive_completeness),
    ("fields.required", _check_fields_required),
    ("fields.types", _check_fields_types),
    ("timestamp.identity", _check_timestamp_identity),
    ("timezone.contract", _check_timezone_contract),
    ("session.identity", _check_session_identity),
    ("session.completeness", _check_session_completeness),
    ("records.session_window", _check_records_session_window),
    ("session.window_alignment", _check_session_window_alignment),
    ("instrument.identity", _check_instrument_identity),
    ("universe.pit", _check_universe_pit),
    ("ordering.causal", _check_ordering_causal),
    ("timestamps.monotonic", _check_timestamps_monotonic),
    ("sequence.integrity", _check_sequence_integrity),
    ("records.duplicates", _check_records_duplicates),
    ("intervals.coverage", _check_intervals_coverage),
    ("intervals.grid_identity", _check_intervals_grid_identity),
    ("coverage.contract", _check_coverage_contract),
    ("coverage.claim", _check_coverage_claim),
    ("objects.present", _check_objects_present),
)

CHECK_IDS = tuple(check_id for check_id, _ in CHECKS)


def _collect_notes(manifest: Any, contract: Mapping) -> list[Note]:
    """Facts the engine recorded but could not verify — never a pass by itself."""
    notes: list[Note] = []
    if not isinstance(manifest, Mapping):
        return notes
    for entry in _files(manifest):
        if entry.get("retained") is False:
            notes.append(
                Note(
                    "files.retained",
                    {
                        "role": entry.get("role"),
                        "upstream_url": entry.get("upstream_url"),
                        "upstream_sha256": entry.get("upstream_sha256"),
                        "bytes": entry.get("bytes"),
                    },
                    "source streamed and not retained: its digest is a producer "
                    "assertion and was not recomputed from disk",
                )
            )
    records = manifest.get("records") if isinstance(manifest.get("records"), Mapping) else {}
    if contract.get("sequence_start_from_manifest") and records.get("sequence_start") is not None:
        notes.append(
            Note(
                "sequence.start",
                {
                    "declared_start": records.get("sequence_start"),
                    "basis": records.get("sequence_start_basis"),
                },
                "sequence start declared by the producer, not pinned by the contract",
            )
        )
    session = manifest.get("session") if isinstance(manifest.get("session"), Mapping) else {}
    markers = session.get("completeness_markers")
    if isinstance(markers, Mapping):
        notes.append(
            Note(
                "session.completeness",
                markers,
                "stream completeness is producer-declared evidence (counters and "
                "container checks), not recomputed by the engine from the source",
            )
        )
    if "terminating_frame_present" in session:
        notes.append(
            Note(
                "session.terminating_frame",
                {"terminating_frame_present": session.get("terminating_frame_present")},
                "declared frame marker recorded; this product carries no zero-length "
                "terminating frame, so completeness is carried by the markers above",
            )
        )
    if contract.get("sequence_probe") and records.get("sequence_tail"):
        notes.append(
            Note(
                "sequence.probe",
                {
                    "head_rows": len(records.get("sequence") or []),
                    "tail_rows": len(records.get("sequence_tail") or []),
                    "sequence_first": records.get("sequence_first"),
                    "sequence_last": records.get("sequence_last"),
                    "sequence_count_total": records.get("sequence_count_total"),
                },
                "bounded probe: two contiguous runs plus a whole-window density "
                "identity, not the full series",
            )
        )
    for domain in _unplaceable_id_domains(manifest, contract):
        notes.append(
            Note(
                "intervals.grid_identity",
                domain,
                "declared bucket ids are free-form labels, not epoch seconds: the "
                "declared grid could not be compared against this id domain",
            )
        )
    if contract.get("require_session_window") and isinstance(manifest.get("session"), Mapping):
        session = manifest["session"]
        anchored = any(
            session.get(key) is not None
            for key in ("window_start_utc", "window_end_utc", "coverage_date")
        )
        if not anchored:
            notes.append(
                Note(
                    "session.window_alignment",
                    {"window_start_unix": session.get("window_start_unix")},
                    "no redundant date/window anchor: a self-consistent global "
                    "shift of the epoch window is not detectable from this manifest",
                )
            )
    return notes


def evaluate(
    manifest: Any,
    contract: Mapping | None,
    ctx: Context | None = None,
    checks: tuple | None = None,
) -> dict:
    """Evaluate one manifest against one branch contract.

    ``checks`` may narrow the registry (used by the tests to prove that a
    named check is what produces a fixture's verdict).
    """
    ctx = ctx or Context()
    contract = contract or {}
    registry = CHECKS if checks is None else checks
    if checks is None:
        # A contract may name extra, contract-scoped checks (``extra_checks``). The
        # global registry is never widened by them, so a branch contract that does
        # not ask for them runs exactly what it ran before.
        seen = {check_id for check_id, _ in registry}
        registry = registry + tuple(
            (check_id, CONTRACT_CHECKS[check_id])
            for check_id in contract.get("extra_checks", ())
            if check_id in CONTRACT_CHECKS and check_id not in seen
        )
    reasons: list[Reason] = []
    for check_id, function in registry:
        if check_id == "manifest.load":
            if not isinstance(manifest, Mapping):
                reasons.append(_absent("manifest.load", type(manifest).__name__, "JSON object"))
                break
            continue
        reasons.extend(function(manifest, contract, ctx))

    state = DATA_VALID
    if any(reason.severity == SEV_INVALID for reason in reasons):
        state = DATA_INVALID
    elif any(reason.severity == SEV_INCOMPLETE for reason in reasons):
        state = DATA_INCOMPLETE

    manifest_map = manifest if isinstance(manifest, Mapping) else {}
    return {
        "state": state,
        "contract_id": contract.get("contract_id"),
        "branch": contract.get("branch", manifest_map.get("branch")),
        "candidate_id": contract.get("candidate_id"),
        "manifest_id": manifest_map.get("manifest_id"),
        "dataset_id": manifest_map.get("dataset_id"),
        "checks_run": [check_id for check_id, _ in registry],
        "reason_counts": {
            SEV_INVALID: sum(1 for r in reasons if r.severity == SEV_INVALID),
            SEV_INCOMPLETE: sum(1 for r in reasons if r.severity == SEV_INCOMPLETE),
        },
        "reasons": [reason.as_dict() for reason in reasons],
        "notes": [note.as_dict() for note in _collect_notes(manifest, contract)],
    }


def is_admitted(result: Mapping) -> bool:
    return result.get("state") == DATA_VALID


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def contract_for(branch: str) -> dict:
    try:
        return BUILTIN_CONTRACTS[branch]
    except KeyError:
        raise KeyError(f"no admission contract for branch {branch!r}; known: {sorted(BUILTIN_CONTRACTS)}")


def contract_for_manifest_path(path: str) -> dict:
    lowered = path.lower()
    for branch, token in (("AUCTION", "auction"), ("ES", "derived_es"), ("BASIS", "basis")):
        if token in lowered:
            return contract_for(branch)
    raise KeyError(f"cannot infer a branch contract from {path!r}; pass --branch or --contract")


def evaluate_path(manifest_path: str, contract: Mapping, ctx: Context | None = None) -> dict:
    """Evaluate a manifest file; a missing file yields DATA_INCOMPLETE."""
    if not os.path.isfile(manifest_path):
        return evaluate(None, contract, ctx)
    return evaluate(load_json(manifest_path), contract, ctx)


def format_text(result: Mapping) -> str:
    lines = [
        f"{result.get('state')}  branch={result.get('branch')}  "
        f"contract={result.get('contract_id')}  manifest={result.get('manifest_id')}"
    ]
    for reason in result.get("reasons", ()):
        lines.append(
            f"  [{reason['severity']}] {reason['check']}: observed={reason['observed']!r} "
            f"expected={reason['expected']!r} {reason.get('detail', '')}".rstrip()
        )
    if not result.get("reasons"):
        lines.append("  no findings")
    for note in result.get("notes", ()):
        lines.append(f"  [NOTE] {note['check']}: {note['detail']} observed={note['observed']!r}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate a data manifest against a branch contract.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--contract", default=None, help="path to a contract JSON file")
    parser.add_argument("--branch", default=None, choices=sorted(BUILTIN_CONTRACTS))
    parser.add_argument("--root", default=REPO_ROOT)
    parser.add_argument("--json-out", default=None)
    arguments = parser.parse_args(argv)

    if arguments.contract:
        contract = load_json(arguments.contract)
    elif arguments.branch:
        contract = contract_for(arguments.branch)
    else:
        contract = contract_for_manifest_path(arguments.manifest)

    ctx = Context(root=arguments.root)
    result = evaluate_path(arguments.manifest, contract, ctx)
    text = format_text(result)
    print(text)
    if arguments.json_out:
        with open(arguments.json_out, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return 0 if result["state"] == DATA_VALID else 1


# --------------------------------------------------------------------------
# branch contracts: data requirements only, no economics
# --------------------------------------------------------------------------

AUCTION_CONTRACT = {
    "contract_id": "ADMISSION-AUCTION-v1",
    "branch": "AUCTION",
    "candidate_id": "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
    "descended_from": "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
    "reformulation": "NARROW_REFORMULATION",
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
    "required_file_roles": ["raw", "noii_reads", "cross_trades", "universe"],
    "allow_unretained_files": True,
    "require_hashes": True,
    "require_archive_status": True,
    "required_fields": [
        "timestamp_ns",
        "locate",
        "symbol",
        "imbalance_shares",
        "cross_price",
        "cross_type",
        "reference_price",
    ],
    "field_types": {
        "timestamp_ns": "int64",
        "locate": "int32",
        "symbol": "utf8",
        "imbalance_shares": "int64",
        "cross_price": "int64",
        "cross_type": "utf8",
        "reference_price": "int64",
    },
    "type_vocabulary": sorted(TYPE_VOCABULARY),
    "timestamp_field": "timestamp_ns",
    "timestamp_semantics": "nanoseconds_since_midnight",
    "timestamp_identity": "message_timestamp",
    "timezone": "America/New_York",
    "expected_session_date": "2026-06-12",
    "require_terminating_frame": False,
    "require_stream_completeness": True,
    "stream_completeness_markers": {
        "gzip_integrity": "PASS",
        "received_bytes_equals_content_range_total": True,
        "framing_errors": 0,
        "trailing_bytes_after_frames": 0,
        "final_frame_is_C_end_of_messages": True,
    },
    "completeness_evidence_role": "admission_record",
    "required_final_event": "C",
    "require_records": True,
    "require_strict_timestamps": False,
    "require_sequence": False,
    "sequence_start_from_manifest": True,
    "require_unique_keys": True,
    "required_intervals": ["15:50_ET_NOII", "15:55_ET_NOII", "CLOSING_CROSS_16:00_ET"],
    "coverage_tolerance": 0.95,
    "instrument_required": True,
    "instrument_must_match_universe": True,
    "require_pit_universe": True,
    "universe_rule_id": "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
}

ES_CONTRACT = {
    "contract_id": "ADMISSION-ES-H3-v1",
    "branch": "ES",
    "candidate_id": "TUP-CME-ES-H3-MIDPOINT-FRICTION",
    "frozen_formulation": "H3 horizons 1s/5s/15s with 1s primary; midpoint friction from observed spreads plus independently verified mandatory charges",
    "required_sections": [
        "source",
        "schema",
        "session",
        "files",
        "fields",
        "instrument",
        "records",
        "intervals",
        "coverage",
    ],
    "required_source_fields": ["source_id", "provider", "retrieved_at_utc", "access_terms"],
    "expected_schema": "CME-MDP3.0-SAMPLE-CAPTURE",
    "required_file_roles": ["raw_extract", "trades", "book"],
    "allow_unretained_files": True,
    "require_hashes": True,
    "require_archive_status": True,
    "required_fields": [
        "ts_event_ns",
        "ts_recv_ns",
        "instrument_id",
        "price",
        "size",
        "side",
    ],
    "field_types": {
        "ts_event_ns": "int64",
        "ts_recv_ns": "int64",
        "instrument_id": "int32",
        "price": "int64",
        "size": "int32",
        "side": "utf8",
    },
    "type_vocabulary": sorted(TYPE_VOCABULARY),
    "timestamp_field": "ts_event_ns",
    "timestamp_semantics": "nanoseconds_since_unix_epoch_UTC",
    "timestamp_identity": "venue_event_timestamp",
    "timezone": "UTC",
    "expected_session_date": "2023-07-17",
    "require_terminating_frame": False,
    "require_records": True,
    "require_strict_timestamps": False,
    "require_sequence": True,
    "sequence_start_from_manifest": True,
    "sequence_probe": {"head_rows": 64, "tail_rows": 64},
    "require_unique_keys": True,
    "required_intervals": ["2023-07-17T13:30Z/2023-07-17T13:40Z"],
    "coverage_tolerance": 0.95,
    "instrument_required": True,
    "allowed_instruments": ["ES", "ESU3", "ESZ3"],
    "allowed_instrument_prefixes": ["ES"],
    "allowed_venues": ["CME", "GLOBEX"],
}

BASIS_CONTRACT = {
    "contract_id": "ADMISSION-BASIS-C-v1",
    "branch": "BASIS",
    "candidate_id": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
    "frozen_formulation": "SHORT Hyperliquid Core BTC perpetual, LONG equal-BTC-notional Binance USD(S)-M BTCUSDT perpetual; hourly funding state, exact one-hour hold, 100% paired hourly buckets",
    "required_sections": [
        "source",
        "schema",
        "session",
        "files",
        "fields",
        "instrument",
        "records",
        "intervals",
        "coverage",
    ],
    "required_source_fields": ["source_id", "provider", "retrieved_at_utc", "access_terms"],
    "expected_schema": "HL-FUNDING-JSON+BINANCE-USD-M-KLINES",
    "required_file_roles": ["hl_funding", "hl_mid", "binance_mark"],
    "require_hashes": True,
    "require_archive_status": True,
    "required_fields": ["hour_unix", "hl_funding_rate", "hl_mid", "binance_mark"],
    "field_types": {
        "hour_unix": "int64",
        "hl_funding_rate": "float64",
        "hl_mid": "float64",
        "binance_mark": "float64",
    },
    "type_vocabulary": sorted(TYPE_VOCABULARY),
    "timestamp_field": "hour_unix",
    "timestamp_semantics": "unix_seconds_utc_hour_floor",
    "timestamp_identity": "hour_bucket_start",
    "timezone": "UTC",
    "expected_session_date": None,
    "require_session_window": True,
    "require_terminating_frame": False,
    "require_records": True,
    "require_strict_timestamps": True,
    "require_sequence": False,
    "require_unique_keys": True,
    "require_full_interval_coverage": True,
    "interval_period_seconds": 3600,
    "coverage_units": "records",
    "coverage_tolerance": 1.0,
    "instrument_required": True,
    "allowed_instruments": ["BTC", "BTCUSDT", "BTC-PERP"],
}

BUILTIN_CONTRACTS = {
    "AUCTION": AUCTION_CONTRACT,
    "ES": ES_CONTRACT,
    "BASIS": BASIS_CONTRACT,
}

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


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
