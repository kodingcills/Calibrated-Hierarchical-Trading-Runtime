"""Artifact writers: CSV tables, derived Markdown registries and the machine-readable state.

Everything written here is regenerated on every run of ``materialize.py``. Markdown
registries (discrepancies, dead ends, open questions) are generated from the same in-memory
rows as the CSVs so that prose and data cannot drift apart.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from corpus.constants import UNKNOWN, UNKNOWN_TOKEN


def cell(value, numeric):
    """Render one cell. Numeric unknowns are empty (and named in unknown_fields)."""
    if value is UNKNOWN:
        return "" if numeric else UNKNOWN_TOKEN
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def unknown_fields_for(row, numeric_map):
    missing = [field for field in numeric_map if row.get(field) is UNKNOWN]
    return "|".join(missing) if missing else "NONE"


def write_csv(path: Path, columns, rows, numeric_map=None):
    numeric_map = numeric_map or {}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            rendered = []
            for col in columns:
                numeric = col in numeric_map
                if numeric:
                    rendered.append(cell(row.get(col), True))
                else:
                    rendered.append(cell(row.get(col), False))
            writer.writerow(rendered)
    return path


def table(path: Path, columns, rows, numeric_map=None, unknown_field_column="unknown_fields"):
    numeric_map = numeric_map or {}
    if unknown_field_column in columns:
        for row in rows:
            row[unknown_field_column] = unknown_fields_for(row, numeric_map)
    return write_csv(path, columns, rows, numeric_map)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8")
    return path


# ------------------------------------------------------------------ md registries
def discrepancies_md(state) -> str:
    lines = [
        "# DISCREPANCIES AND UNKNOWNS",
        "",
        "Canonical machine-readable source: `M1/data/discrepancies.csv` "
        "(generated from `M1/src/corpus/unknowns.py`).",
        "This file is a rendering of that registry; edit the corpus module, not this file.",
        "",
        f"Materialised (UTC): {state['generated_at']}",
        "",
        f"Registered issues: {len(state['discrepancies'])} | "
        f"open: {len(state['blocker_rows'])} | "
        f"blocking: {len([b for b in state['blocker_rows'] if b['severity'] == 'BLOCKING'])}",
        "",
        "Conflicts are never resolved by averaging. Where two sources genuinely disagree the row",
        "carries `conflict_type=CONTRADICTION` and both statements are preserved; where the",
        "divergence is a difference of judgment it carries `conflict_type=DIVERGENCE_IN_JUDGMENT`",
        "and the judgment used is stated together with its basis.",
        "",
    ]
    for issue in state["discrepancies"]:
        lines += [
            f"## {issue['issue_id']} - {issue['severity']} - {issue['status']}",
            "",
            f"- claim needed: {issue['claim_needed']}",
            f"- known evidence: {issue['known_evidence']}",
            f"- specific evidence required: {issue['specific_evidence_needed']}",
            f"- decision prevented: {issue['decision_prevented']}",
            f"- conflict type: {issue['conflict_type']}"
            + (f" ({issue['exact_conflict']})" if issue["exact_conflict"] is not UNKNOWN else ""),
            f"- sources: A={issue['source_A']}, B={issue['source_B']}",
            f"- searches attempted: {issue['search_attempts']}",
            f"- resolvable by web research: {issue['web_research_resolvable']}; "
            f"vendor quote: {issue['requires_vendor_quote']}; "
            f"M2 measurement: {issue['requires_m2_measurement']}",
            f"- resolution class: {issue['resolution_class']}",
            f"- affected: {issue['affected_candidate_ids'] or issue['candidate_id']}",
            f"- evidence: {issue['evidence_ids']}",
            "",
        ]
    return "\n".join(lines)


def dead_ends_md(state) -> str:
    rows = state["dead_rows"]
    lines = [
        "# DEAD ENDS",
        "",
        "Canonical machine-readable source: `M1/data/dead_candidates.csv`.",
        "Imported from the M1-A dead-candidate cemetery (SRC-0011) plus the two governance and",
        "technology admissions registered by M1-C.",
        "",
        f"Registered dead rows: {len(rows)}",
        "",
        "Re-entry policy: a dead candidate cannot re-enter silently. It requires NEW_EVIDENCE plus",
        "an explicit resurrection decision recorded in `DECISIONS.md`. The resurrection condition",
        "is recorded per row so the decision can be made against a stated bar rather than a memory.",
        "",
    ]
    for row in rows:
        lines += [
            f"## {row['candidate_id']} - killed by {row['kill_gate']}",
            "",
            f"- class: {row['candidate_class']}",
            f"- report kill gate (verbatim): {row['report_kill_gate']}",
            f"- cause: {row['cause']}",
            f"- evidence: {row['evidence_ids']}",
            f"- death date: {row['death_date']} ({row['death_date_basis']})",
            f"- resurrection condition: {row['resurrection_condition']}",
            "",
        ]
    return "\n".join(lines)


def open_questions_md(state) -> str:
    lines = [
        "# OPEN QUESTIONS",
        "",
        "Canonical machine-readable source: `M1/data/open_questions.csv`.",
        "Question ids are stable; `legacy_question_id` preserves the original research-OS registry",
        "identifier where one existed.",
        "",
        f"Open questions: {len(state['open_questions'])}",
        "",
    ]
    for q in state["open_questions"]:
        lines += [
            f"## {q['question_id']} - priority {q['priority']}",
            "",
            f"**{q['question']}**",
            "",
            f"- why it matters: {q['why_it_matters']}",
            f"- workstream: {q['workstream']}",
            f"- answer required before gate: {q['answer_required_before_gate']}",
            f"- search status: {q['search_status']}",
            f"- current best answer: {q['current_best_answer']}",
            f"- unresolved gap: {q['unresolved_gap']}",
            f"- next search: {q['next_search']}",
            f"- related issues: {q['related_issue_ids']}",
            f"- legacy id: {q['legacy_question_id']}",
            "",
        ]
    return "\n".join(lines)


def watchlist_md(state) -> str:
    """What to watch, and only what current evidence makes worth watching."""
    cheap = [b for b in state["blocker_rows"]
             if b["resolution_class"] in ("A", "B") and b["severity"] == "BLOCKING"]
    lines = [
        "# WATCHLIST",
        "",
        "Generated from `M1/data/discrepancies.csv`. Items are here because a single external",
        "fact can change the candidate set, not because they are interesting.",
        "",
        "## External facts that can change the survivor set without any modelling",
        "",
    ]
    for b in cheap:
        lines.append(f"- **{b['issue_id']}** ({b['resolution_class']}): "
                     f"{b['specific_evidence_required']} -> prevents: {b['decision_prevented']}")
    lines += [
        "",
        "## Venue and product changes worth watching (they can invalidate a fact already used)",
        "",
        "- CME matching-rule changes: product-specific rules have already changed by notice "
        "(EVD-0003), so a queue model must record the rule version it assumes.",
        "- Cboe U.S. equities fee schedule revisions (the verified rebate/remove rates are dated "
        "2026-09-01).",
        "- Coinbase and Kraken fee-tier changes: the two current crypto kills depend on verified "
        "floors; a materially lower verified tier plus gross-edge evidence would reopen them.",
        "- Hyperliquid public feed changes: the 10-100 ms kill rests on a documented >= 0.5 s "
        "snapshot cadence; a direct order-level feed would constitute a new tuple.",
        "- Event-market jurisdictional changes: state-level access restrictions are live "
        "(EVD-0016), so any event-market work needs a current access matrix, not a memory.",
        "",
        "## Technology watch (admission-relevant, never admission-deciding)",
        "",
        "- Measured (not vendor-reported) hosted-Jev latency under trading-like load.",
        "- Any independent reproduction of System-One calibration or incremental utility.",
        "- Any release of order-level historical data at a cost that clears the data gate.",
        "",
    ]
    return "\n".join(lines)