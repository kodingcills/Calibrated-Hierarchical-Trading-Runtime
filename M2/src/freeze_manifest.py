"""Freeze manifests for the M2-0 pass (handoff sections 0, 3 and 27).

Writes three artifacts:

* ``M2/config/experiment_manifest.json`` - the frozen experiment-preparation
  manifest: git commit, candidate and universe spec hashes, source-code version,
  dataset identity, freeze timestamp.
* ``M2/data/manifests/raw_manifest.json`` - one record per raw file with provider,
  dataset, schema, coverage, byte size, message count, SHA-256 and access time.
* ``M2/output/calculation_manifest.json`` - hashes and versions for every input,
  config and code artifact the calculation needs to be reproduced.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys

from . import config as config_module
from . import ingest

SOURCE_CODE_VERSION = "M2-0.1.0"


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=config_module.REPO_ROOT, text=True
        ).strip()
    except Exception:  # pragma: no cover - only when git is unavailable
        return "UNKNOWN"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _code_hashes() -> dict[str, str]:
    modules = [
        "M2/src/config.py",
        "M2/src/ingest.py",
        "M2/src/audit.py",
        "M2/src/book.py",
        "M2/src/universe.py",
        "M2/src/features.py",
        "M2/src/labels.py",
        "M2/src/costs.py",
        "M2/src/calculate.py",
        "M2/src/freeze_manifest.py",
        "M2/config/nasdaq_qimb_m2_0.yaml",
        "M2/config/cost_ledger_v1.json",
        "M2/tests/test_m2.py",
    ]
    return {
        path: config_module.sha256_file(path)
        for path in modules
        if os.path.exists(config_module.repo_path(path))
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Write the M2-0 freeze manifests.")
    parser.add_argument("--config", default="M2/config/nasdaq_qimb_m2_0.yaml")
    arguments = parser.parse_args(argv)

    configuration = config_module.load(arguments.config)
    derived = config_module.repo_path(config_module.derived_dir(configuration))
    raw_path = config_module.repo_path(
        os.path.join(configuration["paths"]["raw_dir"], configuration["dataset"]["raw_files"][0])
    )
    with open(os.path.join(derived, "ingest_summary.json")) as handle:
        summary = json.load(handle)
    with open(os.path.join(derived, "replay_summary.json")) as handle:
        replay = json.load(handle)
    config_hash = config_module.sha256_file(arguments.config)
    spec_hash = config_module.sha256_file(configuration["universe"]["spec_artifact"])
    ledger_path = configuration["cost_ledger"]["artifact"]
    ledger_hash = config_module.sha256_file(ledger_path)
    code_hashes = _code_hashes()

    experiment_manifest = {
        "manifest_version": "M2-0-EXPERIMENT-v1",
        "frozen_at_utc": utc_now(),
        "frozen_before_outcome_inspection": True,
        "candidate_id": configuration["run"]["candidate_id"],
        "universe_rule_id": configuration["run"]["universe_rule_id"],
        "git_commit_sha": git_commit(),
        "source_code_version": SOURCE_CODE_VERSION,
        "code_hashes": code_hashes,
        "config_path": arguments.config,
        "config_sha256": config_hash,
        "candidate_spec_path": configuration["universe"]["spec_artifact"],
        "candidate_spec_sha256": spec_hash,
        "cost_ledger_id": configuration["cost_ledger"]["ledger_id"],
        "cost_ledger_path": ledger_path,
        "cost_ledger_sha256": ledger_hash,
        "data_vendor": configuration["dataset"]["vendor"],
        "dataset_id": configuration["dataset"]["dataset_id"],
        "dataset_role": configuration["dataset"]["role"],
        "dataset_coverage_date": configuration["dataset"]["coverage_date"],
        "schema_id": configuration["dataset"]["schema_id"],
        "raw_files": [
            {
                "path": configuration["dataset"]["raw_files"][0],
                "bytes": summary["raw_bytes"],
                "sha256": summary["sha256"],
                "md5": summary["computed_md5"],
                "vendor_md5_available": False,
                "vendor_md5_note": (
                    "the vendor-hosted md5sum sibling returned HTTP 404 at access time; the "
                    "SHA-256 computed at freeze time is the integrity record for this pass"
                ),
                "messages": summary["total_messages"],
            }
        ],
        "reproduce_with": [
            "python -m M2.src.ingest --config M2/config/nasdaq_qimb_m2_0.yaml",
            "python -m M2.src.book --config M2/config/nasdaq_qimb_m2_0.yaml",
            "python -m M2.src.calculate --config M2/config/nasdaq_qimb_m2_0.yaml",
            "python -m M2.src.freeze_manifest --config M2/config/nasdaq_qimb_m2_0.yaml",
        ],
        "note": "no paid data acquisition is authorized by this manifest; the sample day is DEVELOPMENT data",
    }
    config_module.write_json("M2/config/experiment_manifest.json", experiment_manifest)

    raw_manifest = {
        "generated_at_utc": utc_now(),
        "records": [
            {
                "provider": configuration["dataset"]["vendor"],
                "dataset": configuration["dataset"]["product"],
                "schema": configuration["dataset"]["schema_id"],
                "dataset_id": configuration["dataset"]["dataset_id"],
                "source_url": (
                    "https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/07302019.NASDAQ_ITCH50.gz"
                ),
                "local_path": os.path.relpath(raw_path, config_module.REPO_ROOT),
                "instrument_mapping": "Stock Directory messages (locate code -> symbol), per trading day",
                "coverage_date": configuration["dataset"]["coverage_date"],
                "coverage_start_ns": summary["first_timestamp_ns"],
                "coverage_end_ns": summary["last_timestamp_ns"],
                "size_bytes": summary["raw_bytes"],
                "message_count": summary["total_messages"],
                "sha256": summary["sha256"],
                "md5": summary["computed_md5"],
                "download_access_timestamp_utc": "2026-09-22T14:29Z",
                "immutability": "raw file is never modified; all outputs are derived artifacts",
                "access_terms_note": (
                    "publicly hosted Nasdaq sample file; no credential used. The file is treated as "
                    "DEVELOPMENT data and no outcome claim is made from it."
                ),
            }
        ],
    }
    config_module.write_json("M2/data/manifests/raw_manifest.json", raw_manifest)

    summary_rows = [
        {
            "provider": record["provider"],
            "dataset": record["dataset"],
            "schema": record["schema"],
            "dataset_id": record["dataset_id"],
            "coverage_date": record["coverage_date"],
            "coverage_start_ns": record["coverage_start_ns"],
            "coverage_end_ns": record["coverage_end_ns"],
            "size_bytes": record["size_bytes"],
            "message_count": record["message_count"],
            "sha256": record["sha256"],
            "md5": record["md5"],
            "access_timestamp_utc": record["download_access_timestamp_utc"],
            "immutability": record["immutability"],
        }
        for record in raw_manifest["records"]
    ]
    import csv as csv_module

    summary_path = config_module.repo_path(
        config_module.output_dir(configuration, "data_quality", "raw_manifest_summary.csv")
    )
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", newline="") as handle:
        writer = csv_module.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)

    calculation_manifest = {
        "manifest_version": "M2-0-CALCULATION-v1",
        "generated_at_utc": utc_now(),
        "git_commit_sha": git_commit(),
        "source_code_version": SOURCE_CODE_VERSION,
        "code_hashes": code_hashes,
        "config_sha256": config_hash,
        "candidate_spec_sha256": spec_hash,
        "cost_ledger_sha256": ledger_hash,
        "raw_sha256": summary["sha256"],
        "reference_documents": _reference_documents(),
        "derived_artifacts": {
            name: {
                "path": os.path.relpath(os.path.join(derived, name), config_module.REPO_ROOT),
                "sha256": config_module.sha256_file(os.path.join(derived, name)),
            }
            for name in ("ingest_summary.json", "symbol_directory.parquet", "decisions.parquet",
                         "delay_decisions.parquet", "replay_summary.json")
            if os.path.exists(os.path.join(derived, name))
        },
        "output_artifacts": {
            name: config_module.sha256_file(path)
            for name, path in _output_artifacts(configuration)
        },
        "replay_summary": {
            "messages": replay["replay"]["messages"],
            "decision_rows": replay["decision_rows"],
            "delay_rows": replay["delay_rows"],
            "quality_verdict": replay["quality_limits"]["verdict"],
        },
        "python_version": sys.version.split()[0],
        "environment": _environment_versions(),
    }
    config_module.write_json("M2/output/calculation_manifest.json", calculation_manifest)
    print(json.dumps({"experiment_manifest": "M2/config/experiment_manifest.json",
                      "raw_manifest": "M2/data/manifests/raw_manifest.json",
                      "calculation_manifest": "M2/output/calculation_manifest.json"}, indent=2))
    return 0


def _reference_documents() -> dict:
    """Provider documents retained as evidence for the schema contract."""
    path = "M2/data/reference/source_manifest.json"
    if not os.path.exists(config_module.repo_path(path)):
        return {}
    with open(config_module.repo_path(path)) as handle:
        manifest = json.load(handle)
    return {
        row["id"]: {"sha256": row["sha256"], "url": row["url"], "local_path": row["local_path"]}
        for row in manifest["documents"]
    }


def _output_artifacts(configuration: dict) -> list[tuple[str, str]]:
    base = config_module.output_dir(configuration)
    found: list[tuple[str, str]] = []
    for root, _dirs, files in os.walk(config_module.repo_path(base)):
        if os.path.basename(root) == "tmp":
            continue
        for name in sorted(files):
            path = os.path.join(root, name)
            found.append((os.path.relpath(path, config_module.repo_path(base)), path))
    return found


def _environment_versions() -> dict:
    versions = {}
    for module in ("numpy", "pyarrow", "yaml"):
        try:
            imported = __import__(module)
            versions[module] = getattr(imported, "__version__", "UNKNOWN")
        except Exception:  # pragma: no cover - optional
            versions[module] = "ABSENT"
    return versions


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
