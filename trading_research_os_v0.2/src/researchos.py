#!/usr/bin/env python3
"""Tiny zero-dependency utility for the Trading Research OS registries."""
from pathlib import Path
import csv, sys, hashlib

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

REQUIRED = {
    "assumptions.csv": ["assumption_id","hypothesis_id","statement","class","falsifier","test","status"],
    "hypotheses.csv": ["hypothesis_id","title","economic_mechanism","primary_outcome","baseline_set","null_set","kill_criteria","status"],
    "experiments.csv": ["experiment_id","hypothesis_id","dataset_version","change_from_parent","reason_before_result","primary_metric","decision"],
    "evidence.csv": ["evidence_id","observed_at","title","url","provenance","evidence_state"],
    "surprises.csv": ["surprise_id","observed_at","expected","observed","stage","resolution_status"],
    "reality_gap.csv": ["event_id","trade_id","predicted_fill","actual_fill","unexplained_residual"],
    "model_candidates.csv": ["candidate_id","name","class","hosted_or_local","allowed_runtime_zone","status"],
    "literature.csv": ["source_id","title","url","workstream","exact_question","review_status"],
    "open_questions.csv": ["question_id","question","why_it_matters","priority","search_status","unresolved_gap"],
}

def read_header(path):
    with path.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f), [])

def validate():
    failures = []
    for fname, needed in REQUIRED.items():
        path = TEMPLATES / fname
        if not path.exists():
            failures.append(f"{fname}: missing")
            continue
        header = read_header(path)
        missing = [x for x in needed if x not in header]
        if missing:
            failures.append(f"{fname}: missing columns {missing}")
    if failures:
        print("VALIDATION FAILED")
        for x in failures:
            print(" -", x)
        return 1
    print("VALIDATION PASSED")
    print(f"Validated {len(REQUIRED)} research registries.")
    return 0

def status():
    for fname in REQUIRED:
        path = TEMPLATES / fname
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        print(f"{fname:24s} {len(rows):5d} records")

def hash_file(path_str):
    p = Path(path_str)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    print(h.hexdigest())

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "validate":
        raise SystemExit(validate())
    if cmd == "status":
        status(); return
    if cmd == "hash" and len(sys.argv) == 3:
        hash_file(sys.argv[2]); return
    print("Usage: researchos.py [validate|status|hash FILE]")
    raise SystemExit(2)

if __name__ == "__main__":
    main()
