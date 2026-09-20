"""Technology-fit matrix (FIT-*), materialised from the M1-A matrix of the same name.

Rows are horizon band x technology class. The column ``physical_admissibility`` records
only what the evidence supports (can this class run at this horizon at all);
``admission_status`` records the project's governance stance (SRC-0015), which is
stricter than physics. No cell is a recommendation.
"""

from .constants import UNKNOWN

COLUMNS = [
    "fit_id", "horizon_band", "technology_class", "runtime_zone", "physical_admissibility",
    "admission_status", "assessment", "blocking_issue_ids", "source_id", "notes",
]

ROWS = []

_BANDS = ["H1", "H2", "H3", "H4", "H5"]
_CLASSES = [
    "RULES_DETERMINISTIC", "LOGISTIC_TREE_BOOST", "LOCAL_NEURAL", "LOCAL_SYSTEM_ONE",
    "HOSTED_JEV", "FRONTIER_LLM",
]

# (physical_admissibility, admission_status, assessment) per band, in _CLASSES order.
_CELLS = {
    "H1": [
        ("CANDIDATE_BASELINE", "BASELINE_REQUIRED",
         "Candidate baseline; actual runtime must be measured."),
        ("CANDIDATE_BASELINE_IF_ENGINEERED_LOCALLY", "BASELINE_REQUIRED",
         "Candidate baseline if engineered locally."),
        ("POSSIBLE_AFTER_LOCAL_P99_PROFILING", "GATED",
         "Possible only after local p99 profiling."),
        ("NOT_ADMITTED_WITHOUT_MEASURED_INCREMENTAL_VALUE", "LOCKED_OUT_BY_DEFAULT",
         "Not admitted without measured incremental value and latency."),
        ("NO_VERIFIED_P99_EVIDENCE", "LOCKED_OUT_BY_DEFAULT",
         "Not admitted; no verified p99 evidence."),
        ("NOT_ADMITTED", "LOCKED_OUT_BY_DEFAULT", "Not admitted."),
    ],
    "H2": [
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("CANDIDATE", "GATED", "Candidate."),
        ("CANDIDATE_AFTER_BASELINE_AND_CALIBRATION_TEST", "LOCKED_OUT_BY_DEFAULT",
         "Candidate only after baseline/calibration test."),
        ("UNKNOWN", "LOCKED_OUT_BY_DEFAULT", "UNKNOWN / locked out by default."),
        ("UNKNOWN", "LOCKED_OUT_BY_DEFAULT", "UNKNOWN / locked out by default."),
    ],
    "H3": [
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("PLAUSIBLE", "GATED", "Plausible."),
        ("POTENTIALLY_TESTABLE", "LOCKED_OUT_BY_DEFAULT", "Potentially testable."),
        ("PHYSICALLY_UNRESOLVED_UNTIL_P99_MEASURED", "LOCKED_OUT_BY_DEFAULT",
         "Physically unresolved until p99 is measured."),
        ("TESTABLE_ONLY_AS_NONCRITICAL_JUDGMENT", "LOCKED_OUT_BY_DEFAULT",
         "Potentially testable only as noncritical judgment."),
    ],
    "H4": [
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("PLAUSIBLE", "GATED", "Plausible."),
        ("PLAUSIBLE_EXPERIMENTAL_CHALLENGER", "LOCKED_OUT_BY_DEFAULT",
         "Plausible experimental challenger."),
        ("PLAUSIBLE_AFTER_REAL_LATENCY_AND_RELIABILITY_MEASUREMENT", "LOCKED_OUT_BY_DEFAULT",
         "Plausible only after real latency/reliability measurement."),
        ("SEMANTIC_EVENT_PROCESSING_ONLY", "LOCKED_OUT_BY_DEFAULT",
         "Plausible for semantic event processing, not hard execution."),
    ],
    "H5": [
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("STRONG_BASELINE", "BASELINE_REQUIRED", "Strong baseline."),
        ("PLAUSIBLE", "GATED", "Plausible."),
        ("PLAUSIBLE", "LOCKED_OUT_BY_DEFAULT", "Plausible."),
        ("PLAUSIBLE_LATENCY_WISE_ECONOMICALLY_UNPROVEN", "LOCKED_OUT_BY_DEFAULT",
         "Plausible from a latency standpoint, still economically unproven."),
        ("PLAUSIBLE_FOR_UNSTRUCTURED_INFORMATION", "LOCKED_OUT_BY_DEFAULT",
         "Plausible for unstructured information."),
    ],
}

_BAND_ASSESSMENT = {
    "H1": "Latency budget too tight to allocate to semantic sophistication without proof.",
    "H2": "Model complexity must justify decision-to-market delay.",
    "H3": "First horizon where semantic/selective inference could be experimentally considered "
          "without presuming value.",
    "H4": "Economic value rather than raw speed becomes easier to test.",
    "H5": "Execution/risk arithmetic remains deterministic regardless.",
}

for band in _BANDS:
    for cls, (admissibility, admission, assessment) in zip(_CLASSES, _CELLS[band]):
        ROWS.append(dict(
            fit_id=f"FIT-{band}-{cls}",
            horizon_band=band,
            technology_class=cls,
            runtime_zone=("ORDER_PATH" if band in ("H1", "H2") else
                          "NEAR_ORDER_PATH" if band == "H3" else "OFFLINE_OR_NEARLINE"),
            physical_admissibility=admissibility,
            admission_status=admission,
            assessment=assessment,
            blocking_issue_ids="UNK-0008|UNK-0016|UNK-0017",
            source_id="SRC-0011",
            notes=_BAND_ASSESSMENT[band] +
                  " Physical plausibility only; this matrix is not a recommendation. "
                  "Policy: hosted Jev is barred from sub-10 ms execution/routing paths, and "
                  "System-One models never perform arithmetic, expected-utility calculation, "
                  "sizing or hard risk logic (SRC-0015).",
        ))

BY_ID = {row["fit_id"]: row for row in ROWS}