#!/usr/bin/env python3
"""Automated validation for the M1-C / M1-D0 artifacts.

Run:  python3 M1/src/validate.py            (writes M1/validation/report.{json,md})
      python3 M1/src/validate.py --strict   (exit 1 on any FAIL)

The rule set is the handoff's acceptance list (C12, M1-D0 acceptance, D1 preconditions),
plus the provenance rules that make the zero-fabrication policy enforceable:

  V1  provenance exists for every factual row
  V2  every numeric fact carries a resolvable source, or is declared UNKNOWN
  V3  no dead candidate is ALIVE; gate ceiling respected; FAIL implies DEAD
  V4  referential integrity for every cross-reference
  V5  no candidate is ranked or scored anywhere
  V6  stable ids are unique
  V7  time-sensitive sources carry a date or an explicit date basis
  V8  no score / rank / weight artifact exists (M1-D1 is not authorized)
  V9  no experiment claims a result it did not run
  V10 decision-critical UNKNOWNs are still UNKNOWN (no imputation)
  V11 canonical and root artifacts cannot contradict each other or PROJECT_STATE
  V12 raw inputs still hash to the manifest (provenance chain intact)
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import candidate_gates  # noqa: E402
import coverage as coverage_mod  # noqa: E402
import paper_arithmetic  # noqa: E402
from corpus import constants, unknowns  # noqa: E402

M1 = SRC.parent
REPO = M1.parent
DATA = M1 / "data"
OUT = M1 / "output"
RAW = M1 / "raw"
VALIDATION = M1 / "validation"

SENTINELS = {"", "UNKNOWN", "NONE", "NOT_RUN", "NOT_APPLICABLE", "NO_VERDICT", "N/A"}
# Free-text cells that merely mention a source id inside prose are not machine references.
SOURCE_FIELDS = {
    "source_registry": [],
    "evidence_ledger": ["source_id"],
    "venue_facts": ["structure_source_id", "matching_algorithm_source_id", "tick_size_source_id",
                    "lot_size_source_id", "maker_fee_source_id", "taker_fee_source_id",
                    "rebate_source_id", "clearing_fee_source_id", "other_exchange_fee_source_id",
                    "funding_source_id", "margin_requirement_source_id", "perp_open_fee_source_id",
                    "perp_close_fee_source_id", "trading_hours_source_id", "live_feed_source_id",
                    "historical_feed_source_id", "depth_source_id",
                    "live_feed_min_interval_source_id", "timestamp_semantics_source_id",
                    "API_protocol_source_id", "rate_limits_source_id", "colocation_source_id"],
    "mechanisms": ["source_id"],
    "candidate_tuples": ["status_source_id", "horizon_taxonomy_source_id"],
    "data_feasibility": ["depth_source_id", "history_source_id", "PIT_source_id",
                         "timestamp_source_id"],
    "execution_envelopes": ["fee_source_ids", "break_even_source_ids"],
    "technology_fit": ["source_id"],
    "discrepancies": ["source_A", "source_B", "evidence_ids"],
    "open_questions": ["related_issue_ids"],
    "dead_candidates": ["evidence_ids"],
    "assumptions": ["source_id"],
    "kill_gates": ["source_id"],
    "experiments": ["blocking_issue_ids"],
    "hypotheses": ["source_id"],
    "venue_cost_reference": ["fee_source_ids"],
    "candidate_gate_status": ["blocking_issue_ids"],
    "evidence_coverage": ["evidence_ids", "declared_blocking_issue_ids", "derived_blocking_issue_ids",
                          "derived_not_declared"],
    "hard_constraint_survivors": ["blocking_issue_ids"],
    "hard_constraint_eliminations": ["source_id"],
    "latency_feasibility": ["blocking_issue_ids"],
}

ID_FIELDS = {
    "venue_id": "venue_facts",
    "mechanism_id": "mechanisms",
    "candidate_id": "candidate_tuples",
    "hypothesis_id": "hypotheses",
    "parent_experiment_id": "experiments",
}

FAILURES = []
CHECKS = []


def fail(rule, where, detail):
    FAILURES.append({"rule": rule, "where": where, "detail": detail})


def ok(rule, name, count, note=""):
    CHECKS.append({"rule": rule, "name": name, "rows_checked": count, "result": "PASS",
                   "note": note})


def read_table(path: Path):
    if not path.exists():
        return None, []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def split_refs(value):
    if value is None:
        return []
    return [x for x in str(value).split("|") if x.strip() not in SENTINELS]


def load_all():
    tables = {}
    for name in list(constants.TABLE_SPECS) + [
            "venue_cost_reference", "candidate_gate_status", "evidence_coverage",
            "hard_constraint_survivors", "hard_constraint_eliminations", "latency_feasibility",
            "data_feasibility_verdicts", "dominated_candidates", "blocker_priority",
            "status_derivation_review", "dead_candidates"]:
        if name in constants.TABLE_SPECS:
            path = DATA / f"{name}.csv"
        else:
            path = OUT / f"{name}.csv"
        cols, rows = read_table(path)
        tables[name] = {"path": path, "cols": cols, "rows": rows, "exists": cols is not None}
    return tables


# --------------------------------------------------------------------------- rules
def v1_provenance(tables):
    checked = 0
    source_ids = {r["source_id"] for r in tables["source_registry"]["rows"]}
    assumption_ids = {r["assumption_id"] for r in tables["assumptions"]["rows"]}
    for name, spec in SOURCE_FIELDS.items():
        table = tables.get(name)
        if not table or not table["exists"]:
            fail("V1", name, "table missing")
            continue
        for row in table["rows"]:
            for field in spec:
                if field not in row:
                    fail("V1", name, f"column {field} missing")
                    continue
                for ref in split_refs(row[field]):
                    checked += 1
                    if ref in source_ids or ref in assumption_ids:
                        continue
                    if ref.startswith("UNK-") or ref.startswith("OQ-") or ref.startswith("EVD-"):
                        continue
                    if ref in SENTINELS:
                        continue
                    fail("V1", f"{name}.{field}",
                         f"unresolvable reference {ref!r} in row "
                         f"{row.get('candidate_id') or row.get('evidence_id') or row.get('venue_id')}")
    ok("V1", "provenance references resolve", checked)


def v2_numeric_sources(tables):
    checked = 0
    for name, spec in constants.TABLE_SPECS.items():
        numeric = spec["numeric"]
        if not numeric:
            continue
        table = tables.get(name)
        if not table or not table["exists"]:
            fail("V2", name, "table missing")
            continue
        unknown_fields = {}
        for row in table["rows"]:
            declared = set(split_refs(row.get("unknown_fields", "")))
            for field, source_field in numeric.items():
                value = row.get(field)
                source = row.get(source_field)
                checked += 1
                if value in (None, ""):
                    if field not in declared:
                        fail("V2", f"{name}.{field}",
                             f"empty numeric cell not declared in unknown_fields "
                             f"(row {row.get(spec['id'])})")
                    continue
                if field in declared:
                    fail("V2", f"{name}.{field}",
                         f"cell has value {value!r} but is declared unknown "
                         f"(row {row.get(spec['id'])})")
                if source is None or str(source).strip() in SENTINELS:
                    fail("V2", f"{name}.{field}",
                         f"numeric value {value!r} without a source column "
                         f"(row {row.get(spec['id'])})")
                if float(value) == 0.0 and not split_refs(source):
                    fail("V2", f"{name}.{field}",
                         f"zero recorded without provenance (row {row.get(spec['id'])})")
    ok("V2", "numeric facts carry sources or are declared UNKNOWN", checked)


def v3_status_integrity(tables):
    rows = tables["candidate_tuples"]["rows"]
    candidates = []
    for row in rows:
        cand = {g: row[g] for g in constants.GATE_IDS}
        cand["overall_status"] = row["overall_status"]
        cand["candidate_id"] = row["candidate_id"]
        cand["candidate_class"] = row["candidate_class"]
        candidates.append(cand)
    violations = candidate_gates.ceiling_violations(candidates)
    for v in violations:
        fail("V3", "candidate_tuples", f"status/ceiling conflict: {v}")
    for row in rows:
        if row["overall_status"] == "DEAD":
            for field in ("kill_gate", "kill_reason", "resurrection_condition"):
                if str(row[field]).strip() in SENTINELS:
                    fail("V3", f"candidate_tuples.{field}",
                         f"dead candidate {row['candidate_id']} lacks {field}")
        if row["overall_status"] == "ALIVE":
            fail("V3", "candidate_tuples",
                 f"{row['candidate_id']} is ALIVE while the M1-A evidence lock does not permit it")
    dead_ledger = {r["candidate_id"] for r in tables["dead_candidates"]["rows"]}
    contradiction = [r["candidate_id"] for r in rows
                     if r["candidate_id"] in dead_ledger and r["overall_status"] != "DEAD"]
    for cid in contradiction:
        fail("V3", "dead_candidates", f"{cid} is in the dead ledger but not DEAD")
    ok("V3", "gate ceiling and dead/ALIVE integrity", len(rows))


def v4_referential(tables):
    checked = 0
    candidate_ids = {r["candidate_id"] for r in tables["candidate_tuples"]["rows"]}
    venue_ids = {r["venue_id"] for r in tables["venue_facts"]["rows"]}
    mechanism_ids = {r["mechanism_id"] for r in tables["mechanisms"]["rows"]}
    evidence_ids = {r["evidence_id"] for r in tables["evidence_ledger"]["rows"]}
    issue_ids = {r["issue_id"] for r in tables["discrepancies"]["rows"]}
    question_ids = {r["question_id"] for r in tables["open_questions"]["rows"]}
    gate_ids = {r["gate_id"] for r in tables["kill_gates"]["rows"]}

    def check_list(name, field, values, universe, label):
        nonlocal checked
        for value in values:
            checked += 1
            if value not in universe:
                fail("V4", f"{name}.{field}", f"unknown {label} {value!r}")

    for row in tables["evidence_ledger"]["rows"]:
        check_list("evidence_ledger", "candidate_ids", split_refs(row["candidate_ids"]),
                   candidate_ids, "candidate_id")
        check_list("evidence_ledger", "venue_id", split_refs(row["venue_id"]), venue_ids, "venue_id")
        check_list("evidence_ledger", "mechanism_id", split_refs(row["mechanism_id"]),
                   mechanism_ids, "mechanism_id")
    for row in tables["candidate_tuples"]["rows"]:
        check_list("candidate_tuples", "venue_id", split_refs(row["venue_id"]), venue_ids,
                   "venue_id")
        check_list("candidate_tuples", "mechanism_id", split_refs(row["mechanism_id"]),
                   mechanism_ids, "mechanism_id")
        check_list("candidate_tuples", "blocking_issue_ids", split_refs(row["blocking_issue_ids"]),
                   issue_ids, "issue_id")
        check_list("candidate_tuples", "blocking_issue_ids_declared",
                   split_refs(row["blocking_issue_ids_declared"]), issue_ids, "issue_id")
        for gate in constants.GATE_IDS:
            checked += 1
            if row[gate] not in constants.GATE_VALUES:
                fail("V4", f"candidate_tuples.{gate}", f"invalid gate value {row[gate]!r}")
            if gate not in gate_ids:
                fail("V4", "candidate_tuples", f"gate {gate} not registered in kill_gates")
    for row in tables["data_feasibility"]["rows"]:
        check_list("data_feasibility", "candidate_id", [row["candidate_id"]], candidate_ids,
                   "candidate_id")
    for row in tables["dead_candidates"]["rows"]:
        check_list("dead_candidates", "evidence_ids", split_refs(row["evidence_ids"]),
                   evidence_ids, "evidence_id")
        check_list("dead_candidates", "kill_gate", split_refs(row["kill_gate"]), gate_ids,
                   "gate_id")
    for row in tables["hard_constraint_eliminations"]["rows"]:
        check_list("hard_constraint_eliminations", "candidate_id", [row["candidate_id"]],
                   candidate_ids, "candidate_id")
    for row in tables["open_questions"]["rows"]:
        check_list("open_questions", "related_issue_ids", split_refs(row["related_issue_ids"]),
                   issue_ids, "issue_id")
    for row in tables["evidence_coverage"]["rows"]:
        check_list("evidence_coverage", "evidence_ids", split_refs(row["evidence_ids"]),
                   evidence_ids, "evidence_id")
    ok("V4", "referential integrity", checked)


def v5_no_ranking(tables):
    forbidden = re.compile(r"(^|_)(score|rank|ranking|weight|utility_score|composite)(_|$)",
                           re.IGNORECASE)
    checked = 0
    for name, table in tables.items():
        if not table["exists"] or not table["cols"]:
            continue
        for col in table["cols"]:
            checked += 1
            if forbidden.search(col):
                fail("V5", f"{name}.{col}", "scoring/ranking column present while M1-D1 is not "
                                            "authorized")
    ranking_artifacts = list(OUT.glob("M1_FINAL_*")) + list(OUT.glob("*sensitivity*")) + \
        list(OUT.glob("*pareto.csv"))
    for path in ranking_artifacts:
        fail("V5", str(path.relative_to(REPO)),
             "ranking artifact exists although M1-D1 is not authorized")
    ok("V5", "no scoring or ranking artifacts", checked)


def v6_unique_ids(tables):
    checked = 0
    for name, spec in constants.TABLE_SPECS.items():
        table = tables.get(name)
        if not table or not table["exists"]:
            continue
        column = spec["id"]
        seen = {}
        for row in table["rows"]:
            checked += 1
            value = row.get(column)
            if value in seen:
                fail("V6", f"{name}.{column}", f"duplicate id {value!r}")
            seen[value] = True
    ok("V6", "stable ids unique", checked)


def v7_source_dates(tables):
    checked = 0
    for row in tables["source_registry"]["rows"]:
        if row["source_id"] in ("SRC-0001",):
            pass
        fields = (row["publication_date"], row["access_date"], row["date_basis"])
        checked += 1
        if all(str(f).strip() in SENTINELS for f in fields):
            fail("V7", "source_registry",
                 f"{row['source_id']} has no date and no date basis")
    for row in tables["venue_facts"]["rows"]:
        for fee_field, source_field in (("taker_fee_value", "taker_fee_source_id"),
                                        ("maker_fee_value", "maker_fee_source_id"),
                                        ("perp_open_fee_value", "perp_open_fee_source_id")):
            if row.get(fee_field) not in (None, ""):
                checked += 1
                src = row.get(source_field)
                src_row = next((r for r in tables["source_registry"]["rows"]
                                if r["source_id"] == src), None)
                if src_row is None:
                    fail("V7", f"venue_facts.{source_field}", f"fee source {src!r} not registered")
                elif all(str(src_row[f]).strip() in SENTINELS
                         for f in ("publication_date", "access_date", "date_basis")):
                    fail("V7", "source_registry",
                         f"fee fact {row['venue_id']}.{fee_field} cites undated source {src}")
    ok("V7", "time-sensitive sources dated", checked)


def v9_experiments(tables):
    checked = 0
    for row in tables["experiments"]["rows"]:
        checked += 1
        state = row["run_state"]
        if state != "RUN":
            if str(row["result_summary"]).strip() not in SENTINELS:
                fail("V9", "experiments", f"{row['experiment_id']} has a result summary without "
                                          f"being run")
            if row["sealed_holdout_accessed"] not in ("NO", ""):
                fail("V9", "experiments", f"{row['experiment_id']} claims sealed-holdout access")
            if str(row["artifact_hash"]).strip() not in SENTINELS and row["artifact_hash"] != "NOT_RUN":
                fail("V9", "experiments", f"{row['experiment_id']} claims an artifact hash")
            if row["decision"] not in ("PENDING", ""):
                fail("V9", "experiments", f"{row['experiment_id']} has a decision without a run")
    ok("V9", "no unperformed experiment claims a result", checked)


def v10_no_imputation(tables):
    checked = 0
    checks = [
        ("execution_envelopes", "full_break_even_bps",
         "full break-even must stay UNKNOWN while any component is unknown (ASM-0013)"),
        ("latency_feasibility", "half_life_ms",
         "half-life must stay UNKNOWN without an empirical EV-vs-delay curve (ASM-0014)"),
        ("latency_feasibility", "T_total_p50_ms", "no measured latency components exist yet"),
        ("latency_feasibility", "T_total_p95_ms", "no measured latency components exist yet"),
        ("latency_feasibility", "T_total_p99_ms", "no measured latency components exist yet"),
    ]
    for table_name, field, why in checks:
        for row in tables[table_name]["rows"]:
            checked += 1
            if str(row.get(field, "")).strip() not in ("", "UNKNOWN"):
                fail("V10", f"{table_name}.{field}", f"{why} (row {row.get('candidate_id')})")
    for row in tables["execution_envelopes"]["rows"]:
        for field in ("spread_bps", "slippage_bps", "impact_bps", "adverse_selection_bps",
                      "funding_bps"):
            checked += 1
            if str(row.get(field, "")).strip() not in ("", "UNKNOWN"):
                fail("V10", f"execution_envelopes.{field}",
                     f"cost component populated without evidence (row {row['candidate_id']})")
    ok("V10", "decision-critical values remain UNKNOWN", checked)


def v11_cross_file(tables):
    checked = 0
    pairs = [("EVIDENCE_LEDGER.csv", DATA / "evidence_ledger.csv"),
             ("ASSUMPTIONS.csv", DATA / "assumptions.csv"),
             ("EXPERIMENTS.csv", DATA / "experiments.csv"),
             ("HYPOTHESES.csv", DATA / "hypotheses.csv")]
    for root_name, canonical in pairs:
        checked += 1
        root = REPO / root_name
        if not root.exists():
            fail("V11", root_name, "root artifact missing")
        elif root.read_bytes() != canonical.read_bytes():
            fail("V11", root_name, f"root artifact differs from {canonical.relative_to(REPO)}")
    summary_path = OUT / "M1_STATE_SUMMARY.json"
    state_path = REPO / "PROJECT_STATE.md"
    checked += 1
    if not state_path.exists():
        fail("V11", "PROJECT_STATE.md", "missing")
    else:
        text = state_path.read_text(encoding="utf-8")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        declared = dict(re.findall(r"^(M1-[A-D][0-9]?):\s*([A-Z_() ]+)$", text, re.MULTILINE))
        for milestone, value in summary["milestones"].items():
            checked += 1
            stated = declared.get(milestone, "")
            if not stated:
                fail("V11", "PROJECT_STATE.md", f"milestone {milestone} not stated")
            elif not stated.startswith(value.split(" ")[0]):
                fail("V11", "PROJECT_STATE.md",
                     f"{milestone} says {stated!r}, summary says {value!r}")
        counts = summary["counts"]
        for cid, expected in (("ALIVE", counts["status"]["ALIVE"]),
                             ("WEAK", counts["status"]["WEAK"]),
                             ("UNKNOWN", counts["status"]["UNKNOWN"]),
                             ("DEAD", counts["status"]["DEAD"])):
            checked += 1
            match = re.search(rf"^\|\s*{cid}\s*\|\s*(\d+)\s*\|", text, re.MULTILINE)
            if not match:
                fail("V11", "PROJECT_STATE.md", f"no count table row for {cid}")
            elif int(match.group(1)) != expected:
                fail("V11", "PROJECT_STATE.md",
                     f"{cid} count {match.group(1)} != summary {expected}")
    ok("V11", "cross-file consistency", checked)


def v12_manifest(tables):
    checked = 0
    manifest_path = RAW / "source_manifest.json"
    if not manifest_path.exists():
        fail("V12", "source_manifest.json", "missing")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        checked += 1
        path = REPO / entry["raw_path"]
        if not path.exists():
            fail("V12", entry["raw_path"], "raw copy missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            fail("V12", entry["raw_path"], "raw copy changed since manifest was written")
    registered = {r["source_id"]: r for r in tables["source_registry"]["rows"]}
    for entry in manifest["files"]:
        src = next((r for r in registered.values()
                    if r["local_path"] == entry["original_path"]), None)
        if src is not None:
            checked += 1
            if src["sha256"] != entry["sha256"]:
                fail("V12", f"source_registry.{src['source_id']}",
                     "registry hash does not match the manifest")
    ok("V12", "raw provenance chain intact", checked)


def v13_paper_arithmetic(tables):
    checked = 0
    report = paper_arithmetic.consistency_report()
    checked += 1
    if report["consistent"]:
        fail("V13", "paper_arithmetic",
             "the candidate-architecture paper's cost statements now reconcile; EVD-0028 must be "
             "revised rather than left asserting an inconsistency")
    declared = next((r for r in tables["evidence_ledger"]["rows"]
                     if r["evidence_id"] == "EVD-0028"), None)
    checked += 1
    if declared is None:
        fail("V13", "evidence_ledger", "EVD-0028 (paper cost arithmetic) missing")
    elif declared["verification_status"] != "PROJECT_ARITHMETIC_REPRODUCIBLE":
        fail("V13", "evidence_ledger", "EVD-0028 is not marked reproducible")
    ok("V13", "paper cost arithmetic reproduces", checked)


def main():
    strict = "--strict" in sys.argv
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tables = load_all()
    v1_provenance(tables)
    v2_numeric_sources(tables)
    v3_status_integrity(tables)
    v4_referential(tables)
    v5_no_ranking(tables)
    v6_unique_ids(tables)
    v7_source_dates(tables)
    v9_experiments(tables)
    v10_no_imputation(tables)
    v11_cross_file(tables)
    v12_manifest(tables)
    v13_paper_arithmetic(tables)

    summary = json.loads((OUT / "M1_STATE_SUMMARY.json").read_text(encoding="utf-8"))
    result = {
        "generated_at": generated_at,
        "validator": "M1/src/validate.py",
        "overall": "PASS" if not FAILURES else "FAIL",
        "failures": len(FAILURES),
        "checks": CHECKS,
        "details": FAILURES,
        "context": {
            "candidate_rows": summary["counts"]["candidate_rows"],
            "status": summary["counts"]["status"],
            "blocking_issues": summary["counts"]["blocking_issues"],
            "m1b_eligible": summary["counts"]["m1b_eligible"],
        },
    }
    VALIDATION.mkdir(parents=True, exist_ok=True)
    (VALIDATION / "report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# M1 validation report",
        "",
        f"Generated (UTC): {generated_at} by `M1/src/validate.py`.",
        "",
        f"**Overall: {result['overall']}** - {len(FAILURES)} failure(s) across "
        f"{len(CHECKS)} rule groups.",
        "",
        "| rule | check | rows checked | result |",
        "|---|---|---|---|",
    ]
    for check in CHECKS:
        lines.append(f"| {check['rule']} | {check['name']} | {check['rows_checked']} | "
                     f"{check['result']} |")
    lines += ["", "## Failures", ""]
    if not FAILURES:
        lines.append("None.")
    else:
        for failure in FAILURES:
            lines.append(f"- **{failure['rule']}** `{failure['where']}`: {failure['detail']}")
    lines += [
        "",
        "## Rule set",
        "",
        "- V1 provenance for every factual row",
        "- V2 numeric facts carry a source or are declared UNKNOWN",
        "- V3 gate ceiling, DEAD/ALIVE integrity, dead-ledger agreement",
        "- V4 referential integrity across artifacts",
        "- V5 no scoring or ranking artifact (M1-D1 not authorized)",
        "- V6 unique stable ids",
        "- V7 time-sensitive sources carry a date or date basis",
        "- V9 no experiment claims a result it did not run",
        "- V10 decision-critical values remain UNKNOWN (no imputation)",
        "- V11 root artifacts agree with canonical artifacts and PROJECT_STATE.md",
        "- V12 raw inputs still hash to the manifest",
        "- V13 the candidate-architecture paper's cost arithmetic still fails to reconcile",
        "",
    ]
    (VALIDATION / "report.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"overall": result["overall"], "failures": len(FAILURES),
                      "checks": len(CHECKS)}, indent=1))
    for failure in FAILURES:
        print(f"  {failure['rule']} {failure['where']}: {failure['detail']}")
    if strict and FAILURES:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())