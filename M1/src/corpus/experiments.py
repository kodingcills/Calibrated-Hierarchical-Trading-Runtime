"""Experiment registry (EXP-*) and hypothesis registry (HYP-*).

Every row here is PROPOSED and NOT RUN. The validator fails any experiment row that claims a
result, a decision, a sealed-holdout access or an artifact hash without a run; that rule exists
so a planned measurement can never be mistaken for performed work.

The hypothesis registry is intentionally empty: M1-D1 is not authorized, so no candidate has
earned a registered M2 hypothesis (handoff: "The M2 experiment skeleton that is already
justified - but not yet a registered M2 hypothesis").
"""

from .constants import UNKNOWN

EXPERIMENT_COLUMNS = [
    "experiment_id", "parent_experiment_id", "hypothesis_id", "registered_at", "run_state",
    "preregistered", "dataset_version", "feature_version", "label_version", "model_version",
    "calibration_version", "execution_model_version", "change_from_parent", "reason_before_result",
    "primary_metric", "secondary_metrics", "result_summary", "sealed_holdout_accessed", "decision",
    "artifact_hash", "blocking_issue_ids", "required_preconditions", "notes",
]

_HYPOTHESIS_COLUMNS = [
    "hypothesis_id", "title", "economic_mechanism", "market", "instrument", "venue", "horizon",
    "execution_style", "primary_outcome", "baseline_set", "null_set", "dataset_version",
    "planned_split", "allowed_degrees_of_freedom", "kill_criteria", "created_at", "status",
    "source_id",
]

_REGISTERED_AT = "2026-09-20"

EXPERIMENTS = []


def e(experiment_id, parent, title_reason, primary_metric, secondary_metrics, preconditions,
      blocking, notes, hypothesis_id=UNKNOWN):
    EXPERIMENTS.append(dict(
        experiment_id=experiment_id,
        parent_experiment_id=parent,
        hypothesis_id=hypothesis_id,
        registered_at=_REGISTERED_AT,
        run_state="PROPOSED_NOT_RUN",
        preregistered="NO",
        dataset_version="UNKNOWN",
        feature_version="UNKNOWN",
        label_version="UNKNOWN",
        model_version="UNKNOWN",
        calibration_version="UNKNOWN",
        execution_model_version="UNKNOWN",
        change_from_parent=UNKNOWN,
        reason_before_result=title_reason,
        primary_metric=primary_metric,
        secondary_metrics=secondary_metrics,
        result_summary="NOT_RUN",
        sealed_holdout_accessed="NO",
        decision="PENDING",
        artifact_hash="NOT_RUN",
        blocking_issue_ids=blocking,
        required_preconditions=preconditions,
        notes=notes,
    ))


e("EXP-0001", "NONE (root)",
  "Measure whether the predictive information documented in the literature has economically "
  "relevant magnitude on a named venue: gross conditional markout versus signal quantile.",
  "gross conditional markout by signal quantile",
  "signal autocorrelation; quantile monotonicity; regime slices",
  "Named instrument, order-level historical data with validated timestamps, causal state builder",
  "UNK-0003|UNK-0004|UNK-0027",
  "Baseline ladder step 1 and 2 of the project's G2 gate. No model beyond deterministic "
  "imbalance/microprice formulas is required.",
  hypothesis_id=UNKNOWN)

e("EXP-0002", "EXP-0001",
  "Measure signal decay: execution-aware EV at controlled artificial delays, to replace every "
  "'next tick' assumption with a measured curve.",
  "execution-aware EV versus delay",
  "gross markout versus delay; implied break-even delay; delay-grid sensitivity",
  "EXP-0001 artifacts plus a conservative execution model",
  "UNK-0006|UNK-0008|UNK-0016",
  "Delay grid is an experiment design choice, not an asserted market half-life: "
  "0/10/25/50/100/250/500 ms and 1/2/5 s where physically appropriate.",
  hypothesis_id=UNKNOWN)

e("EXP-0003", "EXP-0001",
  "Estimate passive fill probability conditional on queue state under the venue's actual matching "
  "rule, and validate the simulator against shadow observations.",
  "simulated-versus-observed fill rate",
  "partial-fill rate; queue-position error; fill latency",
  "Order-level replay data, written matching rule for the exact contract, live shadow path",
  "UNK-0002|UNK-0003|UNK-0004|UNK-0007",
  "Touch=fills is disallowed as a baseline; the simulator must distinguish executions from "
  "cancellations where the feed allows it.",
  hypothesis_id=UNKNOWN)

e("EXP-0004", "EXP-0003",
  "Measure adverse selection: markout distribution conditional on own fills, for passive and "
  "crossing execution.",
  "fill-conditioned markout distribution",
  "expected markout by queue position; toxicity-conditioned markout",
  "EXP-0003 validated fill model",
  "UNK-0008|UNK-0019",
  "This is the measurement that decides whether an apparent spread capture is real.",
  hypothesis_id=UNKNOWN)

e("EXP-0005", "EXP-0001",
  "Produce a cost-sensitivity surface: does the candidate's sign survive conservative "
  "fee/slippage/spread assumptions?",
  "sign stability of execution-aware net edge",
  "break-even fee level; break-even spread level",
  "Verified venue fee schedule for the project's account path",
  "UNK-0001|UNK-0005|UNK-0006|UNK-0018",
  "Required by the project's own G4 robustness gate; cheap and can kill a branch.",
  hypothesis_id=UNKNOWN)

e("EXP-0006", "EXP-0002",
  "Run the same-information baseline ladder (no-trade/passive, random-side, logistic, "
  "LightGBM/XGBoost, hand-authored rule) on the measured signal.",
  "sealed execution-aware out-of-sample utility",
  "log loss; Brier; calibration slope/intercept; risk-coverage",
  "EXP-0002 artifacts",
  "UNK-0008",
  "Mandatory comparator set before any neural or System-One variant may be considered.",
  hypothesis_id=UNKNOWN)

e("EXP-0007", "NONE (root)",
  "Profile this project's own shadow path: source event, receive, feature-complete, model start "
  "and end, decision, submit, ack, fills.",
  "decision-to-market latency p50/p95/p99",
  "jitter; deadline-miss rate; per-stage residuals",
  "Instrumented shadow runtime with the project's timestamp contract",
  "UNK-0016",
  "Measurement only; no order is sent.",
  hypothesis_id=UNKNOWN)

e("EXP-0008", "EXP-0006",
  "Sealed post-cost out-of-sample utility test of the surviving candidate against the baseline "
  "ladder, with a preregistered kill criterion.",
  "sealed net utility versus baseline ladder",
  "multiple-testing controls (PBO/DSR where applicable); regime breakdown",
  "M1-B completion, frozen dataset version, preregistered thresholds",
  "UNK-0006|UNK-0008|UNK-0016",
  "Cannot be registered until M1-B selects a finalist and M1-D1 is authorized.",
  hypothesis_id=UNKNOWN)

e("EXP-0009", "EXP-0006",
  "Measure incremental execution-aware utility of a System-One/Jev policy over the "
  "same-information classical baseline on sealed data.",
  "incremental net utility (System-One minus classical baseline)",
  "p50/p95/p99 decision age; calibration diagnostics; semantic perturbation stability",
  "A funded, measured System-One path and a completed baseline ladder",
  "UNK-0017|UNK-0026",
  "Locked out by default; this row exists so the burden of proof is explicit. Vendor-reported "
  "latency is not an input.",
  hypothesis_id=UNKNOWN)

HYPOTHESIS_COLUMNS = _HYPOTHESIS_COLUMNS
HYPOTHESES = []  # empty by design: M1-D1 is NOT_AUTHORIZED