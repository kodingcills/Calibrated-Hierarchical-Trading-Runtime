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
  "Verified structural cost C0 schedule plus a declared unresolved cost C1 parameter range "
  "(exact account-level schedule is the pre-shadow gate, DECISIONS D-0042)",
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


def run(experiment_id, parent, registered_at, preregistered, dataset_version, feature_version,
        label_version, model_version, calibration_version, execution_model_version,
        change_from_parent, reason_before_result, primary_metric, secondary_metrics,
        result_summary, decision, artifact_hash, blocking_issue_ids, required_preconditions,
        notes, sealed_holdout_accessed="NO"):
    """Register an experiment that actually ran.

    A RUN row is the only place a result may appear, and it carries the frozen artifact's hash so
    the result is traceable rather than narrated. The M1 register holds the bridge campaign's
    branch measurements here; they are single-branch falsification measurements and cannot
    establish net edge.
    """
    EXPERIMENTS.append(dict(
        experiment_id=experiment_id,
        parent_experiment_id=parent,
        hypothesis_id=UNKNOWN,
        registered_at=registered_at,
        run_state="RUN",
        preregistered=preregistered,
        dataset_version=dataset_version,
        feature_version=feature_version,
        label_version=label_version,
        model_version=model_version,
        calibration_version=calibration_version,
        execution_model_version=execution_model_version,
        change_from_parent=change_from_parent,
        reason_before_result=reason_before_result,
        primary_metric=primary_metric,
        secondary_metrics=secondary_metrics,
        result_summary=result_summary,
        sealed_holdout_accessed=sealed_holdout_accessed,
        decision=decision,
        artifact_hash=artifact_hash,
        blocking_issue_ids=blocking_issue_ids,
        required_preconditions=required_preconditions,
        notes=notes,
    ))


# ---------------------------------------------------------------- GOAL-M2-BRIDGE-001 branch runs
# The three rows below are the bridge campaign's single-branch measurements. They are registered
# as RUN because each ran exactly once under its own frozen contract; none of them is a
# profitability test, and no row here may be read as evidence of edge. Row EXP-0012 records an
# INVALIDATED freeze: its sealed input was written before the seal and already carried the outcome
# quantity, so it is a measurement with a stated invalidation, not a preregistered result.

run("EXP-0010", "NONE (root)", "2026-09-30", "YES",
    "CME-GLOBEX-MDP3.0-ESU3-2023-07-17T133000Z (one admitted 10-minute RTH-open window)",
    "OFI-1S-SIGNED-DEPTH-NORMALIZED-v1 (x = (V_buy - V_sell)/D over (t-1s, t])",
    "SIDE-SIGNED-MIDPOINT-MARKOUT-1/5/15s (no executable-price substitution)",
    "NONE (no model and no threshold: the state's sign is the direction)",
    "NONE (no fitted parameter)",
    "OBSERVED-SPREAD-FRICTION-FLOOR-v1 (1/2 S_entry + 1/2 S_exit per observation; no execution "
    "model is built)",
    "FIRST_RUN (M2 bridge campaign; no M1 register parent)",
    "The frozen formulation had never been measured on ES. The branch's data prerequisite admitted "
    "exactly one window, and the campaign ran the gross-materiality precursor on it with the "
    "contract, horizons, state, friction treatment, coverage floor, metric, kill rule and seeds "
    "sealed before any gross markout was inspected.",
    "pooled side-signed 1 s midpoint markout versus the measured observed-spread structural cost "
    "C0, with the break-even residual C* reported",
    "1/5/15 s term structure; unconditional side-ignoring markout at the same instants; per-state "
    "LONG/SHORT; capture-clock robustness pass; significance against zero (reported only)",
    "KILL_MATERIALITY (PRIMARY_HORIZON_GROSS_NOT_POSITIVE), scope SAMPLE_SCOPED_DEVELOPMENT_KILL: "
    "-0.0047336 bps at the primary 1 s horizon (CI [-0.0468503, +0.0403358], n = 583 of 599 "
    "slots) against C0 = 0.5770016 bps; C* = -0.5817352 bps; the conditional state is below its "
    "own unconditional baseline (+0.0156746 bps over 598 quote-available slots, +0.0208001 bps "
    "over the 583 conditional instants)",
    "KILLS", "09c8562999304072a5f5b5184bece3ba0588d1d57754ae776b3c6934f1487ac2",
    "UNK-0009-MECH-CME|UNK-0018-CME",
    "Free no-auth CME Globex MDP 3.0 sample covering one ESU3 window with venue send timestamps; "
    "the slice admitted DATA_VALID with a byte-identical independent re-derivation",
    "Sealed before the outcome (freeze sha256 42a158c5...) and re-verified at run time against its "
    "own module, six input and three reused-module hashes; V3 reproduced the arithmetic "
    "independently and re-ran the contract to a byte-identical results.json. Limits recorded with "
    "the result: one 10-minute window (sample-scoped kill only); C0 contains no verified "
    "exchange/clearing/FCM charge and is a floor, not an all-in cost; sealing is asserted by "
    "artifact ordering only (UNVERIFIED); the published unconditional figure is over 598 "
    "quote-available slots while the conditional is over 583 (0.0051 bps apart).")

run("EXP-0011", "NONE (root)", "2026-09-30", "YES",
    "HL-BINANCE-BASIS-2026-03-05T11:00:00Z..2026-09-28T23:00:00Z (availability-derived, 4,981 "
    "hourly buckets with exact grid identity; reference prices per AMEND-C5-001)",
    "FUNDING-CARRY-1H-UNCONDITIONAL-v1 (short Hyperliquid Core BTC perpetual / long "
    "equal-notional Binance USD(S)-M BTCUSDT perpetual)",
    "PER-HOLD SIGNED BPS OF NOTIONAL (venue funding carry plus hedge mark-to-market residual)",
    "NONE (unconditional; no state conditioning and no fitted parameter)",
    "NONE (no fitted parameter)",
    "REFERENCE-PRICE CARRY WITH THE PUBLISHED LOWEST-RUNG TAKER FLOOR-v1 (no fill model; C0 = "
    "2 x 0.024% per side)",
    "FIRST_RUN (M2 bridge campaign; no M1 register parent)",
    "The frozen one-hour formulation had never been measured; the branch's free-source prerequisite "
    "reached a 100%-paired panel and the campaign ran the materiality measurement on it with the "
    "cost rule, coverage floor, inference rule and seeds sealed before any economics were "
    "inspected.",
    "pooled signed gross carry per one-hour hold versus the published structural floor C0, with the "
    "break-even residual C* reported",
    "hour-clustered bootstrap interval and a 24 h moving-block variant; per-venue carry "
    "decomposition; unresolved-settlement bracket; staleness distribution; C1 sensitivity table; "
    "sign-robustness control",
    "KILL_MATERIALITY (hi 0.09624 <= C0 4.8): +0.0344051 bps per hold (hour-clustered CI "
    "[-0.0101126, +0.0755247], 10,000 resamples, seed 20260930; decision interval "
    "[-0.0269835, +0.0962354]) against C0 = 4.8 bps; C* = -4.7655949 bps; the kill is sign-robust "
    "(reversed structure -0.0330 bps, flipped HL carry -0.0874 bps)",
    "KILLS", "97a4d7acf71db4837ad2e8cf090350b5615c2716684df531e74a6ef7f550d722",
    "UNK-0010|UNK-0018-HYPERLIQUID",
    "Free Hyperliquid hourly funding/candle history plus free Binance 1h klines and funding "
    "archives covering one availability-derived window; the panel admitted DATA_VALID with "
    "4,981/4,981 hourly pairing",
    "Sealed before the outcome (freeze sha256 389b8f4d...) and re-verified at run time; V3 "
    "recomputed the whole gross from the panel and the raw archives with deltas 0.0 and confirmed "
    "the sign-robustness control. Limits recorded with the result: the 84 unresolved Binance "
    "settlements contribute exactly zero to the MEASURED series and are bracketed only in the "
    "decision quantity; sealing is asserted by artifact ordering only (UNVERIFIED); the freeze's "
    "recorded hash for M2/src/admission.py has drifted and the freeze no longer verifies in place; "
    "Binance's all-leg cost is UNKNOWN, so the true C* is more negative than reported; a zero-cost "
    "maker path would make the verdict INDETERMINATE. A longer-horizon or other-pair reformulation "
    "is a NEW candidate, never a reinterpretation of this row.")

run("EXP-0012", "NONE (root)", "2026-09-30", "INVALIDATED_FREEZE",
    "NASDAQ-TOTALVIEW-ITCH50-2026-06-12 (retained window 15:49:50-16:00:10 ET; 17.89 GB streamed, "
    "retained artifact 760,167,921 bytes, sha256 28ed7b97...59597)",
    "NOII-CLOSING-CROSS READS AT 15:50 AND 15:55 (signed imbalance delta scaled by "
    "PairedShares_15:55)",
    "CLOSING CROSS PRINT (Cross Trade Q, Cross Type C) against the 15:55 Current Reference Price",
    "NONE (deterministic frozen signal)",
    "NONE (no fitted parameter)",
    "EXECUTABLE-CAPTURE POST-15:55 QUOTE ENTRY-v1 (entry prints sha256 9f52149c...474d4f2; entry "
    "book reconstructed from the retained window alone, with no pre-15:49:50 warm-up)",
    "FIRST_RUN (new candidate row)",
    "The frozen formulation had never been measured; the campaign ran one development-grade "
    "single-session measurement with a preregistered clause order. The preregistration is recorded "
    "as INVALID because the freeze's own sealed input was written before the seal and already "
    "carried the outcome quantity.",
    "executable capture g_exec in bps, side-signed (frozen primary metric)",
    "reconstruction-free mechanism displacement versus the 15:55 reference price; four-quantile "
    "state partition of the scaled imbalance delta; symbol-clustered bootstrap; C1 sensitivity",
    "INDETERMINATE (ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED; SIGNAL_SCOPE_SUBFLOOR) with the freeze "
    "invalid as a preregistration. The frozen executable capture reads -108.8946 bps pooled but V3 "
    "verified it is a reconstruction artifact (mean capture = mean mechanism +6.5168 bps - mean "
    "side-signed(entry - reference) +115.4115 bps exactly; worst 50 of 1,261 symbols carry 93.9% "
    "of the loss; largest reconstructed entry spread $11.64 on a $2.10 stock; -0.60 bps on the 348 "
    "symbols whose reconstructed spread is <= 10 bps of price). The reconstruction-free mechanism "
    "metric is POSITIVE (+6.5168 bps, CI [2.0026, 10.9985]) and above the 1.02 bps fee floor, but "
    "it assumes a non-executable reference-price entry and is NOT evidence of tradability.",
    "INDETERMINATE", "15b7a3d51c1e6d0ce897ec31d63357657df47a9d59d8af6316b2a513c50d2f63",
    "UNK-0018-NASDAQ|UNK-0027-AUCTION",
    "Free public ITCH session tape including 15:49:50-16:00:10 ET, with verified SEC Section 31 "
    "and FINRA TAF rates effective for the sample date",
    "Freeze sha256 9baff3dd... (results 15b7a3d5...). The producing worker failed with exit 1 "
    "after 54 minutes while writing its report, so no producer narration exists for this branch and "
    "its verdict was verified separately in V3 before any canonical mutation. The freeze is "
    "INVALID as a preregistration: signal_extract.json, hashed by the freeze and written at "
    "15:30:07 (nine minutes before the seal at 15:39:08), already contained "
    "closing_cross_price_raw with closing_cross_valid = true for 4,281 of 12,809 records - the "
    "exit price of every analysed symbol - contradicting the freeze's own statement that its "
    "inputs carry no outcome quantity. The preregistered near/far band diagnostic is DEGENERATE "
    "(near and far prices are 0 in all 12,809 records), so that clause can never pass for any "
    "reconstruction. No gate is changed and no dead-end entry is created by this row: the "
    "candidate keeps an OPEN QUESTION (OQ-0017) naming the decidable next action - a re-extract "
    "with pre-15:49:50 book warm-up (the source was streamed and not retained) under a freeze "
    "whose inputs contain no outcome quantity and whose sealing is externally anchored. The "
    "universe transcription repair already recorded in the spec is kept (C = Common Shares, "
    "Z = Not Applicable; Authenticity = P, ETP Flag = N, Issue Classification = C, Market "
    "Category in {Q,G,S}).")