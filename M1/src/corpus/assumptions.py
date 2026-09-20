"""Assumption registry (ASM-*).

Two groups:

ASM-0001..ASM-0018  materialisation and computation conventions used by M1-C/M1-D0. These
                    are registered so that any number in the artifacts can be traced to the
                    convention that produced it. They are *method* assumptions, not market
                    claims.
ASM-0101..ASM-0110  the ten architecture assumptions the project audit derived from the
                    candidate-architecture paper (SRC-0020) plus the paper's own sizing
                    premise, kept in ProjectStatus vocabulary so they can be carried into a
                    single registry.

``confidence_state`` uses the research-OS vocabulary: unknown / weak / moderate / strong /
falsified. Method conventions are ``strong`` because they are enforced in code; market
assumptions are not.
"""

from .constants import UNKNOWN

COLUMNS = [
    "assumption_id", "hypothesis_id", "statement", "class", "why_required",
    "current_evidence", "confidence_state", "falsifier", "test", "observable_residual",
    "enforced_in_code", "owner", "last_reviewed", "source_id", "status",
]

ROWS = []

_OWNER = "research-engineering"
_DATE = "2026-09-20"


def add(assumption_id, statement, cls, why_required, current_evidence, confidence_state,
        falsifier, test, observable_residual, enforced_in_code, source_id,
        hypothesis_id=UNKNOWN, status="ACTIVE"):
    ROWS.append({
        "assumption_id": assumption_id, "hypothesis_id": hypothesis_id,
        "statement": statement, "class": cls, "why_required": why_required,
        "current_evidence": current_evidence, "confidence_state": confidence_state,
        "falsifier": falsifier, "test": test, "observable_residual": observable_residual,
        "enforced_in_code": enforced_in_code, "owner": _OWNER, "last_reviewed": _DATE,
        "source_id": source_id, "status": status,
    })


# ------------------------------------------------- method / computation conventions
add("ASM-0001",
    "Horizon bands H1..H5 label the ranges 10-100 ms, 100 ms-1 s, 1-15 s, 15 s-5 min and 5 min+, "
    "and those millisecond endpoints map to the microsecond endpoints used in candidate_tuples.",
    "timing / point-in-time availability",
    "Candidates are stored with machine-usable horizon bounds; the report expresses horizons as "
    "bands.",
    "Band labels appear in SRC-0011; the microsecond endpoints are this convention.",
    "strong", "A canonical artifact redefines the bands, or an external study is compared against "
             "them at a different resolution.",
    "Compare band endpoints against the source artifact whenever a candidate horizon is quoted.",
    "Candidate rows change horizon_min_us/horizon_max_us.",
    "YES", "SRC-0011")

add("ASM-0002",
    "Numeric venue-fact columns are nullable, and NULL is interpreted as UNKNOWN only when the "
    "row's status/unknown_fields declaration accounts for it.",
    "data integrity", "Prevents an empty cell from being read as zero or as verified.",
    "Handoff ZI-0.2 and SRC-0026 require NULL+UNKNOWN for missing values.", "strong",
    "A numeric fact is populated without a paired source column.", "Validator rule V1/V2.",
    "Validation failure count for missing provenance.",
    "YES", "SRC-0026")

add("ASM-0003",
    "Only evidence records whose direction is SUPPORTS count as candidate support evidence; "
    "WEAKENS and NEUTRAL records are counted separately and are never netted against each other.",
    "statistical identification",
    "Counting is descriptive and must not become a hidden score.",
    "Handoff D0.3 requires descriptive counts, not a quality score. Tier-2 audit found the "
    "M1-A artifact itself counting NEUTRAL feasibility facts as support for a candidate.",
    "strong", "A formal scoring rule is registered with its own evidence basis.", "validator rule "
    "V3 (support counts recomputed from direction).",
    "Support counts differ from a naive contains-id count.", "YES", "SRC-0026|SRC-0011")

add("ASM-0004",
    "Report-assigned candidate labels are treated as authoritative judgments of the M1-A artifact "
    "and are preserved, with the label's basis recorded in candidate_tuples.status_basis.",
    "policy composition",
    "Zero-fabrication rules forbid overriding a canonical artifact's judgment, but the judgment "
    "must remain auditable.",
    "SRC-0011 assigns WEAK/UNKNOWN/DEAD explicitly; the labels are carried verbatim.",
    "strong", "A later canonical artifact revises a label.", "Reconcile labels against report text "
    "at every ingest.", "A label exists whose basis is not recorded.", "YES", "SRC-0011")

add("ASM-0005",
    "A missing numeric value is recorded as NULL/UNKNOWN and is never substituted by zero, a "
    "midpoint, an industry-typical figure or a default estimate.",
    "data integrity", "Prevents fabricated precision in cost, latency and fee arithmetic.",
    "Handoff ZI-0.2; SRC-0018 label audit; SRC-0024 known-unknowns.", "strong",
    "Any artifact cell carries a placeholder number where evidence is absent.", "Validator rule "
    "V2 plus review of every numeric column.", "Count of non-null numeric cells without sources.",
    "YES", "SRC-0026|SRC-0018")

add("ASM-0006",
    "Identifier schemes are deterministic and stable: SRC-#### registry, EVD-#### evidence, "
    "VEN-*, MECH-*, TUP-*, UNK-#### issues, OQ-#### questions, ASM-#### assumptions, KG# gates.",
    "data integrity", "Cross-artifact references must remain resolvable between sessions.",
    "Handoff C2 example schemes.", "strong", "Two rows share an id, or an id is re-used after "
    "deletion.", "Validator rule V6 (uniqueness) and V4 (referential integrity).",
    "Duplicate-id and dangling-reference counts.", "YES", "SRC-0026")

add("ASM-0007",
    "The M1-A incompleteness verdict is not overridden by any later artifact; PROJECT_STATE.md "
    "records it until evidence actually changes it.",
    "policy composition", "Prevents an optimistic architecture proposal from silently closing M1-A.",
    "SRC-0011 states M1-A INCOMPLETE; the attachment and SRC-0026 both forbid overriding it.",
    "strong", "Decision-critical evidence for every blocked invariant is produced.",
    "PROJECT_STATE cross-check against M1/validation/report.json.", "M1-A status flips without new "
    "evidence.", "YES", "SRC-0011|SRC-0026")

add("ASM-0008",
    "Kill gates are tri-state: FAIL means evidence shows the requirement cannot be met; BLOCKED "
    "means it cannot yet be judged; PASS requires cited evidence that the requirement is met. Any "
    "FAIL forces DEAD and any BLOCKED forbids ALIVE.",
    "policy composition", "Makes partial evidence structurally unable to look like success.",
    "Handoff C10 and SRC-0026 D0.4.", "strong", "A candidate is ALIVE while a gate is BLOCKED.",
    "Validator rule V5.", "Gate table versus status column.", "YES", "SRC-0026")

add("ASM-0009",
    "Where the M1-A artifact assigns WEAK or UNKNOWN to a tuple, that label is preserved rather "
    "than recomputed from gate states, because WEAK encodes the existence of constraining "
    "evidence that gates alone do not express.",
    "policy composition", "WEAK and UNKNOWN differ in why they are not ALIVE; collapsing them "
    "would lose information.",
    "SRC-0011 explicitly warns that WEAK is not 'better' than UNKNOWN.", "strong",
    "A later artifact supplies a measured basis for relabelling.", "Compare label against "
    "status_basis text.", "Label/basis mismatch.", "YES", "SRC-0011")

add("ASM-0010",
    "candidate_tuples.blocking_issue_ids is derived from the issue registry (severity=BLOCKING and "
    "the candidate named in candidate_id or affected_candidate_ids), plus explicitly declared "
    "candidate-local entries; it is not hand-maintained prose.",
    "data integrity", "Blockers must stay visible and recomputable after edits.",
    "Handoff D0.4 requires blocking_issue_ids in the gate output.", "strong",
    "An issue blocks a candidate but is absent from the candidate's list, or vice versa.",
    "Recompute lists from the registry and diff.", "Diff count between declared and derived.",
    "PARTIAL", "SRC-0026")

add("ASM-0011",
    "Fees are stored in their native unit (bps, percent, USD/share, USD/contract) and are not "
    "converted across units unless the conversion inputs are present (for USD/share, a price).",
    "execution / fill", "A $/share fee has no bps equivalent without a price; converting anyway "
    "would invent a number.",
    "Cboe BZX rates are USD/share; Coinbase/Kraken are percentage-based.", "strong",
    "A conversion is published without its inputs.", "Inspector of execution_envelopes fee-unit "
    "columns.", "bps columns populated for a USD/share venue.", "YES", "SRC-0114|SRC-0105|SRC-0106")

add("ASM-0012",
    "KnownCostFloor is the sum of verified mandatory cost components only, and is reported as a "
    "lower bound on costs, never as a break-even or an expected value.",
    "execution / fill", "Prevents a partial cost table from being read as full economics.",
    "Handoff D0.1 defines the two quantities separately.", "strong",
    "KnownCostFloor is quoted as break-even.", "Cost module unit tests plus readiness report "
    "wording.", "Misuse of the floor in any downstream artifact.", "YES", "SRC-0026")

add("ASM-0013",
    "FullBreakEven is computed only when every required component (spread, fees, slippage, adverse "
    "selection, impact) is known or explicitly parameterised; otherwise it stays UNKNOWN.",
    "execution / fill", "An incomplete break-even would misstate viability in both directions.",
    "Handoff D0.1 formula rule.", "strong", "A full break-even is published with an unknown term.",
    "Cost module unit tests.", "Non-null FullBreakEven while a component is unset.", "YES",
    "SRC-0026")

add("ASM-0014",
    "No half-life is inferred from 'next tick', 'short horizon' or 'predictive'; without an "
    "empirical EV-versus-delay curve the half-life stays UNKNOWN and latency_fit stays BLOCKED.",
    "latency / signal half-life", "A fabricated decay constant would drive model and venue choices.",
    "SRC-0011 states this explicitly for every serious candidate; SRC-0016 requires EV(delay).",
    "strong", "An EV(delay) curve is measured and the fit family justified by that data.",
    "Latency module refuses to emit a fit without curve inputs.", "half_life or latency_fit "
    "populated without curve evidence.", "YES", "SRC-0011|SRC-0016")

add("ASM-0015",
    "Non-blocking unknowns are still registered, because an unrecorded unknown becomes a hidden "
    "assumption; they are excluded from the blocking set but never dropped.",
    "data integrity", "Keeps the residual visible without inflating the blocker count.",
    "Handoff C8 severity vocabulary includes NON_BLOCKING.", "strong",
    "A non-blocking unknown disappears from the registry.", "Registry diff between runs.",
    "Issue count by severity.", "YES", "SRC-0026")

add("ASM-0016",
    "Candidate counts are reported separately for tradable tuples and for non-tuple registration "
    "rows (method rules, universe definitions, governance and technology admissions).",
    "policy composition", "'0 ALIVE of 28 candidates' would otherwise be ambiguous about what was "
    "being counted.",
    "The M1-A cemetery mixes tuples with method, universe and governance kills.",
    "strong", "A count is published that mixes the two classes.", "Report module asserts both "
    "counts.", "Ambiguous candidate totals.", "YES", "SRC-0011")

add("ASM-0017",
    "Evidence-class counts per candidate are descriptive only; no evidence score, weight vector or "
    "quality index is constructed at M1-D0.",
    "statistical identification", "A score would convert missing evidence into apparent precision.",
    "Handoff D0.3.", "strong", "A scoring rule is registered with an explicit rubric and "
    "evidence basis.", "Coverage module emits counts only.", "Any score column appearing in M1 "
    "outputs.", "YES", "SRC-0026")

add("ASM-0018",
    "Where the M1-A artifact gave two reasons for its own incompleteness and one is now false in "
    "this repository (the source files are present), the verdict is re-derived from the remaining "
    "blockers rather than inherited; the verdict itself is unchanged because the remaining blockers "
    "are sufficient.",
    "policy composition", "Prevents an inherited verdict from surviving on a stale premise.",
    "SRC-0011's retrievability premise is contradicted by the repository contents; the empirical "
    "blockers (UNK-0001..UNK-0009, UNK-0016) are independently sufficient.",
    "strong", "All remaining blockers close without new evidence.", "Readiness report recomputes "
    "M1-A status from open blockers.", "M1-A status and blocker list disagree.", "YES",
    "SRC-0011|SRC-0026")

# ------------------------------------------- architecture assumptions (SRC-0020)
_ARCH = [
    (1, "The chosen market-making edge survives the full decision-to-order delay."),
    (2, "Avellaneda-Stoikov remains a competitive baseline after realistic queue and "
        "adverse-selection modelling."),
    (3, "Semantic regime/toxicity judgments contain information not already represented by local "
        "quantitative features."),
    (4, "Native or locally recalibrated Jev scores remain useful under regime shift."),
    (5, "The state representation contains enough information without excess context."),
    (6, "Six parallel questions do not create harmful common-mode errors."),
    (7, "Model gating improves quote quality after accounting for opportunity cost from abstention."),
    (8, "Real fill/markout economics remain positive after fees, gas, adverse selection and queue "
        "effects."),
    (9, "Hosted model availability/jitter does not create stale-action risk because fallback logic "
        "is enforced."),
    (10, "Any sizing rule is based on execution-aware return distributions, not semantic confidence."),
]
for n, statement in _ARCH:
    add(f"ASM-{100 + n:04d}", statement,
        "calibration / uncertainty" if n in (3, 4, 6, 7) else
        "latency / signal half-life" if n in (1, 9) else
        "execution / fill" if n in (2, 8) else
        "policy composition" if n == 10 else "model generalization",
        "Derived by the project audit as a required premise of the candidate architecture "
        "(SRC-0020).",
        "None of these is evidenced; each is a premise the architecture needs in order to work.",
        "unknown",
        "A same-information classical policy matches or beats the architecture on sealed, "
        "execution-aware utility, or the premise fails its own test.",
        "Nested experiment arms A0..A7 from SRC-0020, each with a same-information control.",
        "incremental execution-aware net utility of A5/A6 over A4.",
        "NO", "SRC-0020",
        hypothesis_id="TUP-SYSTEMONE-HARDCORE-ENGINE",
        status="UNKNOWN_PREMISE")

add("ASM-0111",
    "Sizing may be computed directly from a model probability via f = c * max(0, 2p - 1).",
    "policy composition",
    "Registered because the candidate-architecture paper asserts it; it is the paper's premise, "
    "not a project assumption.",
    "The project audit shows this is the even-money binary-bet Kelly form, which does not describe "
    "a market-making trade (fill probability, spread capture, adverse selection, inventory, fees "
    "and exit mechanics all matter).",
    "falsified",
    "An execution-aware return distribution reproduces the same sizing rule.",
    "Compare sizing from the paper's formula against sizing from a fitted execution-aware outcome "
    "distribution on the same states.",
    "divergence in position size and realized utility.",
    "NO", "SRC-0020|SRC-0010",
    hypothesis_id="TUP-SYSTEMONE-HARDCORE-ENGINE", status="FALSIFIED")

BY_ID = {row["assumption_id"]: row for row in ROWS}