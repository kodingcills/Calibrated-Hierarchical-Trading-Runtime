#!/usr/bin/env python3
"""Build M1/raw/source_manifest.json: SHA-256, size, ingest time and role per raw input.

Run:  python3 M1/src/build_manifest.py

Raw inputs are never modified. The manifest is what makes every claim in the M1 corpus
traceable to an immutable byte sequence, and it is the file the source registry reads its
hashes from.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

M1 = Path(__file__).resolve().parents[1]
REPO = M1.parent
RAW = M1 / "raw"

# (path under M1/raw, original repository path, role)
FILES = [
    ("deep-research-report.md", "deep-research-report.md",
     "M1-A external-evidence artifact (current evidence lock until superseded)"),
    ("jev-trading-paper.pdf", "Jev Trading Research Paper.pdf",
     "candidate-architecture specimen (project source, not external evidence)"),
    ("M1-C_M1-D_Handoff.md", "M1-C_M1-D_Handoff.md",
     "execution contract for M1-C / M1-D0 / M1-D1 preconditions (instruction document)"),
    ("trading_research_os_v0.2/README.md", "trading_research_os_v0.2/README.md",
     "research-OS overview and architectural defaults"),
    ("trading_research_os_v0.2/STATUS.md", "trading_research_os_v0.2/STATUS.md",
     "prior current-status artifact (superseded in role by PROJECT_STATE.md)"),
    ("trading_research_os_v0.2/config/evidence_gates.yaml",
     "trading_research_os_v0.2/config/evidence_gates.yaml",
     "machine-readable G0..G8 promotion gates"),
    ("trading_research_os_v0.2/src/researchos.py", "trading_research_os_v0.2/src/researchos.py",
     "registry header validator (no evidence or arithmetic checking)"),
    ("trading_research_os_v0.2/templates/literature.csv",
     "trading_research_os_v0.2/templates/literature.csv",
     "canonical literature registry with URLs (SRC-0001..SRC-0010)"),
    ("trading_research_os_v0.2/templates/open_questions.csv",
     "trading_research_os_v0.2/templates/open_questions.csv",
     "prior open-question registry (Q-010 preserved as OQ-0011.legacy_question_id)"),
]

DOCS = [
    "00_research_charter.md", "01_assumption_graph.md", "02_evidence_gates.md",
    "03_system_one_admission_policy.md", "04_simulation_reality_gap.md",
    "05_literature_review_map.md", "06_metrics_and_kill_criteria.md",
    "07_monitoring_and_source_policy.md", "08_jev_trading_paper_audit.md",
]
for doc in DOCS:
    FILES.append((f"trading_research_os_v0.2/docs/{doc}",
                  f"trading_research_os_v0.2/docs/{doc}", "research-OS methodology/policy"))

TEMPLATES = ["assumptions.csv", "hypotheses.csv", "experiments.csv", "evidence.csv",
             "model_candidates.csv", "reality_gap.csv", "surprises.csv"]
for tmpl in TEMPLATES:
    FILES.append((f"trading_research_os_v0.2/templates/{tmpl}",
                  f"trading_research_os_v0.2/templates/{tmpl}",
                  "research-OS registry template (empty contract)"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    for rel, original, role in FILES:
        path = RAW / rel
        if not path.exists():
            raise SystemExit(f"missing raw copy: {path}")
        entries.append({
            "raw_path": str(path.relative_to(REPO)),
            "original_path": original,
            "role": role,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
            "ingested_at_utc": ingested_at,
        })

    paper = next(e for e in entries if e["original_path"] == "Jev Trading Research Paper.pdf")
    manifest = {
        "manifest_version": "1.0",
        "generated_by": "M1/src/build_manifest.py",
        "ingested_at_utc": ingested_at,
        "raw_inputs_modified": False,
        "note": "Copies preserve the originals; the repository originals were never modified. "
                "Hashes are of the copies and are re-checked by M1/src/validate.py.",
        "files": entries,
        "derived_artifacts": [
            {"path": "M1/derived/jev_paper_pages/page-01.png .. page-08.png",
             "role": "140 dpi rasterisation of the image-only paper, used to read its claim set "
                     "because the PDF has no text layer (UNK-0031)",
             "generated_by": "ghostscript -sDEVICE=png16m -r140"},
        ],
        "paper_text_layer": {
            "available": False,
            "evidence": "0 /Font objects, 0 /ToUnicode tables, 8 /Image objects, 8 pages",
            "consequence": "claim set read by rasterising and transcribing pages; recorded as "
                           "UNK-0031 (transcription fidelity residual risk)",
            "sha256": paper["sha256"],
        },
    }
    out = RAW / "source_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)} with {len(entries)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())