"""Configuration loading and artifact hashing for the M2-0 pass."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def repo_path(relative: str) -> str:
    """Resolve a repository-relative path, or pass an absolute path through."""
    if os.path.isabs(relative):
        return relative
    return os.path.join(REPO_ROOT, relative)


def load(path: str = "M2/config/nasdaq_qimb_m2_0.yaml") -> dict[str, Any]:
    with open(repo_path(path), "r") as handle:
        return yaml.safe_load(handle)


def sha256_file(path: str, chunk: int = 1 << 22) -> str:
    digest = hashlib.sha256()
    with open(repo_path(path), "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: str, payload: Any) -> str:
    target = repo_path(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return target


def derived_dir(configuration: dict) -> str:
    return os.path.join(
        configuration["paths"]["derived_dir"], configuration["dataset"]["dataset_id"]
    )


def output_dir(configuration: dict, *parts: str) -> str:
    return os.path.join(configuration["paths"]["output_dir"], *parts)


def ensure_dirs(configuration: dict, *parts: str) -> str:
    target = output_dir(configuration, *parts)
    os.makedirs(target, exist_ok=True)
    return target
