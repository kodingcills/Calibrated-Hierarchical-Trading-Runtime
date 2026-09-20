"""Latency and signal-half-life feasibility.

There is no empirical EV-versus-delay curve anywhere in the current evidence package, so
this module's honest output for every candidate is ``latency_fit = BLOCKED`` and
``half_life = UNKNOWN`` (ASM-0014).

The module still implements the arithmetic that becomes usable once M2 measures the
components, so the measurement plan is executable rather than aspirational:

* ``aggregate_latency`` sums measured per-stage components into p50/p95/p99 totals.
* ``ev_vs_delay_fit`` reports a fitted decay ONLY when a curve is supplied, and reports the
  fit family it used rather than assuming exponential decay.
"""

from __future__ import annotations

import math

UNKNOWN = None

LATENCY_STAGES = (
    "source_event_to_receive",
    "receive_to_feature_complete",
    "feature_complete_to_model_start",
    "model_start_to_model_end",
    "model_end_to_decision",
    "decision_to_order_submit",
    "order_submit_to_ack",
)


def aggregate_latency(stage_quantiles, quantiles=("p50", "p95", "p99")):
    """Sum per-stage latency quantiles into a total per quantile.

    ``stage_quantiles`` maps stage name -> {p50, p95, p99} in milliseconds. Any missing
    stage or quantile makes the corresponding total UNKNOWN: an incomplete path is not a
    latency measurement.
    """
    out = {}
    for q in quantiles:
        total = 0.0
        missing = []
        for stage in LATENCY_STAGES:
            values = stage_quantiles.get(stage)
            if values is UNKNOWN or values.get(q) is UNKNOWN:
                missing.append(stage)
            else:
                total += float(values[q])
        out[f"T_total_{q}_ms"] = UNKNOWN if missing else total
        out[f"T_total_{q}_missing_stages"] = "|".join(missing) if missing else "NONE"
    return out


def latency_fit(ev_curve, measured_total_p99_ms=UNKNOWN):
    """Compare a measured EV-versus-delay curve against the achieved decision age.

    ``ev_curve`` maps delay in milliseconds -> execution-aware EV in bps. Without a curve
    the fit is BLOCKED; with one, the reported metrics stay descriptive (no exponential
    model is imposed).
    """
    if not ev_curve:
        return {
            "latency_fit": "BLOCKED",
            "half_life_ms": UNKNOWN,
            "reason": "No empirical EV-versus-delay curve exists; decay cannot be inferred from "
                      "'next tick' or 'short horizon' claims (ASM-0014).",
            "fit_family": "NONE",
            "ev_at_measured_p99_bps": UNKNOWN,
            "viable_delay_ceiling_ms": UNKNOWN,
        }

    delays = sorted(ev_curve)
    evs = [ev_curve[d] for d in delays]
    ceiling = UNKNOWN
    for delay, ev in zip(delays, evs):
        if ev > 0:
            ceiling = delay
        else:
            break

    half_life = UNKNOWN
    if evs[0] > 0:
        for delay, ev in zip(delays, evs):
            if ev <= evs[0] / 2.0:
                half_life = delay
                break

    ev_at_p99 = UNKNOWN
    if measured_total_p99_ms is not UNKNOWN:
        ev_at_p99 = ev_curve.get(measured_total_p99_ms)
        if ev_at_p99 is UNKNOWN:
            lower = [d for d in delays if d <= measured_total_p99_ms]
            ev_at_p99 = ev_curve[lower[-1]] if lower else evs[0]

    return {
        "latency_fit": "PASS" if ev_at_p99 is not UNKNOWN and ev_at_p99 > 0 else "FAIL",
        "half_life_ms": half_life,
        "reason": "Measured curve supplied; metrics are descriptive of the supplied curve.",
        "fit_family": "NONPARAMETRIC_PIECEWISE (no decay form assumed)",
        "ev_at_measured_p99_bps": ev_at_p99,
        "viable_delay_ceiling_ms": ceiling,
    }


def half_life_candidates(ev_curve, threshold_fraction=0.5):
    """Delays at which EV has fallen to ``threshold_fraction`` of the first measured value."""
    if not ev_curve:
        return UNKNOWN
    delays = sorted(ev_curve)
    first = ev_curve[delays[0]]
    if first <= 0:
        return UNKNOWN
    target = first * threshold_fraction
    out = []
    for delay in delays:
        if ev_curve[delay] <= target:
            out.append(delay)
    return out or UNKNOWN


def delay_sweep_recommendation():
    """The preregistered delay grid proposed for M2 (experiment design, not a measurement)."""
    return {
        "grid_ms": [0, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000],
        "note": "Grid is an experiment-design proposal from the M1-A artifact; it asserts no "
                "market half-life and must be re-scoped per venue where sub-100 ms observation is "
                "physically impossible.",
        "required_outputs": ["gross conditional markout by delay",
                             "execution-aware EV by delay",
                             ".05/.25/.50/.75/.95 quantile bands"],
        "no_exponential_assumption": True,
        "exp_decay_model_allowed_only_if": "the measured curve's own residuals support it",
    }


def geomean_decay_check(ev_curve):
    """Diagnostic only: geometric mean decay ratio per step, to test an exponential reading.

    Returns UNKNOWN when the curve has fewer than three points or any non-positive EV,
    because a ratio is undefined across a sign change.
    """
    if not ev_curve or len(ev_curve) < 3:
        return UNKNOWN
    delays = sorted(ev_curve)
    evs = [ev_curve[d] for d in delays]
    if any(ev <= 0 for ev in evs):
        return UNKNOWN
    ratios = [evs[i + 1] / evs[i] for i in range(len(evs) - 1)]
    prod = 1.0
    for r in ratios:
        prod *= r
    return prod ** (1.0 / len(ratios))


def log_likelihood_exponential(ev_curve):
    """Goodness-of-fit helper placeholder: returns UNKNOWN until a curve exists.

    Kept explicit so no caller can silently obtain a lambda from no data.
    """
    if not ev_curve:
        return UNKNOWN
    delays = sorted(ev_curve)
    evs = [ev_curve[d] for d in delays]
    if any(ev <= 0 for ev in evs):
        return UNKNOWN
    xs = [d for d in delays]
    ys = [math.log(ev) for ev in evs]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return UNKNOWN
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else UNKNOWN
    return {"lambda_per_ms": -slope, "intercept": intercept, "r_squared": r2,
            "family": "EXPONENTIAL (diagnostic only)"}


def latency_feasibility_rows(tuples, known_totals=None):
    known_totals = known_totals or {}
    rows = []
    for cand in tuples:
        cid = cand["candidate_id"]
        total = known_totals.get(cid)
        fit = latency_fit(UNKNOWN, measured_total_p99_ms=UNKNOWN)
        rows.append({
            "candidate_id": cid,
            "horizon_band": cand["horizon_band"],
            "horizon_min_us": cand["horizon_min_us"],
            "T_total_p50_ms": UNKNOWN,
            "T_total_p95_ms": UNKNOWN,
            "T_total_p99_ms": UNKNOWN,
            "measured_components": "NONE" if total is UNKNOWN else str(total),
            "half_life_ms": fit["half_life_ms"],
            "latency_fit": fit["latency_fit"],
            "technology_status": cand["technology_status"],
            "note": fit["reason"],
            "blocking_issue_ids": "UNK-0008|UNK-0016",
        })
    return rows