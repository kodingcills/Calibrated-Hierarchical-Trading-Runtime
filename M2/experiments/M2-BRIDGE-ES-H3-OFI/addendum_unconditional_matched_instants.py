#!/usr/bin/env python3
"""Addendum to M2-BRIDGE-ES-H3-OFI: the unconditional markout on the conditional instants.

The frozen measurement ``M2/src/es_materiality.py`` reports two different things over two
different populations at each horizon:

* ``unconditional_markout_bps`` - the side-ignoring markout averaged over every slot with a
  quotable entry and exit (``quote_mask``), which at the 1 s primary horizon is 598 slots; and
* ``gross_markout_bps`` - the side-signed conditional markout averaged over the evaluated
  observations, which at 1 s is the 583 non-zero-state slots (``observation_mask``).

Reading those two numbers side by side invites a same-population comparison that the two
denominators do not support. Verification wave V3 measured the gap at the primary horizon
(+0.0208001 bps matched-instant vs the published +0.0156746 bps) and reported it as inert for
the decision.

This script closes the gap by RECOMPUTING the unconditional side-ignoring markout over EXACTLY
the conditional observation set (the same 583 / 579 / 569 instants), at every frozen horizon, and
reporting it next to the published quote-available-slot variant and the conditional figure. It
computes nothing new about the verdict: the fired clause is the primary-horizon gross being
non-positive and the independent arm ``hi <= C0``, and neither figure moves either arm.

It reads the sealed contract and the admitted inputs but NEVER writes to them, and it reuses the
frozen module's own loaders and masks so the addendum arithmetic is the frozen arithmetic.

Usage:
    .venv/bin/python3 M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.py \
        --freeze M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json \
        --results M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json \
        --out M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import numpy as np  # noqa: E402

from M2.src import es_materiality as materiality  # noqa: E402

BPS_PER_UNIT = 1.0e4


def _finite_mean(values):
    finite = values[np.isfinite(values)]
    return float(np.mean(finite)) if finite.size else None


def recompute(freeze_path: str, results_path: str) -> dict:
    with open(materiality.config_module.repo_path(freeze_path), "r") as handle:
        freeze = json.load(handle)
    with open(materiality.config_module.repo_path(results_path), "r") as handle:
        results = json.load(handle)

    data_dir = freeze["data"]["derived_dir"]
    manifest = materiality.load_manifest(data_dir)
    instrument_id = int(manifest["instrument"]["security_id"])
    price_scale = float(freeze["data"]["price_scale_index_points_per_mantissa_unit"])
    step_ns = int(freeze["grid_step_ns"])

    grid = materiality.load_spread_grid(os.path.join(data_dir, freeze["data"]["spread_grid"]))
    trades = materiality.load_trades(
        os.path.join(data_dir, freeze["data"]["trades"]), instrument_id, freeze["clock"]["primary"]
    )
    flow = materiality.cumulative_flow(trades)

    published = {int(row["horizon_s"]): row for row in results["per_horizon"]}
    rows = []
    for horizon_s in freeze["horizons_s"]:
        horizon_s = int(horizon_s)
        panel = materiality.build_panel(
            grid, flow, horizon_s, int(freeze["state"]["lookback_ns"]),
            int(freeze["statistics"]["block_slots"]), price_scale, step_ns,
        )
        direction = materiality.state_direction(panel)
        raw = (panel.mid_exit_points - panel.mid_entry_points) / panel.mid_entry_points * BPS_PER_UNIT

        quoted = materiality.quote_mask(panel)
        conditional = materiality.observation_mask(panel, direction)

        quote_variant = _finite_mean(raw[quoted])
        matched_variant = _finite_mean(raw[conditional])
        conditional_gross = _finite_mean(materiality.gross_markout_bps(panel, direction)[conditional])

        ref = published[horizon_s]
        rows.append(materiality.clean({
            "horizon_s": horizon_s,
            "slots_quote_available": int(quoted.sum()),
            "observations_conditional": int(conditional.sum()),
            "conditional_gross_bps": conditional_gross,
            "unconditional_bps_over_quote_available_slots": quote_variant,
            "unconditional_bps_over_conditional_instants": matched_variant,
            "delta_matched_minus_published_bps": (
                None if matched_variant is None or quote_variant is None
                else matched_variant - quote_variant
            ),
            "conditional_minus_unconditional_matched_bps": (
                None if conditional_gross is None or matched_variant is None
                else conditional_gross - matched_variant
            ),
            "published_results_json": {
                "observations": int(ref["observations"]),
                "gross_markout_bps": ref["gross_markout_bps"],
                "unconditional_markout_bps": ref["unconditional_markout_bps"],
                "quote_coverage": ref["quote_coverage"],
                "observation_coverage": ref["observation_coverage"],
            },
            "reproduces_published_conditional": np.isclose(
                conditional_gross, ref["gross_markout_bps"], rtol=0, atol=1e-12
            ),
            "reproduces_published_unconditional": np.isclose(
                quote_variant, ref["unconditional_markout_bps"], rtol=0, atol=1e-12
            ),
            "reproduces_published_observation_count": int(ref["observations"]) == int(conditional.sum()),
        }))

    return {
        "record": "ADDENDUM_UNCONDITIONAL_ON_MATCHED_INSTANTS",
        "experiment_id": freeze["experiment_id"],
        "candidate_id": freeze["candidate_id"],
        "addendum_reason": (
            "The frozen results report the unconditional side-ignoring markout over the "
            "quote-available slots (quote_mask) and the conditional side-signed gross over the "
            "evaluated observations (observation_mask). Those are different instant sets, so the "
            "two columns are not directly comparable as published. This addendum states the "
            "unconditional figure on the conditional instants as well, and carries both "
            "denominators next to every number."
        ),
        "recomputation": (
            "Reuses M2/src/es_materiality.py unchanged (its frozen loaders, build_panel, "
            "state_direction, quote_mask, observation_mask and gross_markout_bps) on the same "
            "sealed contract and the same admitted inputs; only the averaging set of the "
            "unconditional side-ignoring markout is changed, to observation_mask instead of "
            "quote_mask."
        ),
        "defect_closed": (
            "V3 claim B6': the published unconditional at the 1 s primary horizon is the mean over "
            "598 quote-available slots while the conditional gross is over 583 non-zero-state "
            "observations; the matched-instant unconditional is +0.0208001 bps, 0.0051 bps above "
            "the published +0.0156746."
        ),
        "verdict_unchanged": {
            "verdict": results.get("verdict"),
            "fired_clause": results["classification"]["clause"],
            "statement": (
                "Neither the matched-instant nor the quote-available-slot unconditional figure "
                "changes the verdict. The kill fires on the conditional primary-horizon gross "
                "being non-positive (g <= 0) and, independently, on hi <= C0. The unconditional "
                "markout is not an input to the classification at all: it is the side-ignoring "
                "null baseline, reported so the conditional figure can be read against it, and "
                "recording it on the conditional instants only sharpens that reading - the "
                "conditional state remains BELOW its own matched-instant baseline."
            ),
        },
        "freeze_sha256": materiality.sha256_file(freeze_path),
        "results_json_sha256": materiality.sha256_file(results_path),
        "horizons": rows,
        "inputs_sha256": {
            relative: materiality.sha256_file(relative)
            for relative in ("M2/src/es_materiality.py",)
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ES matched-instant unconditional addendum.")
    parser.add_argument("--freeze", default="M2/experiments/M2-BRIDGE-ES-H3-OFI/freeze.json")
    parser.add_argument("--results", default="M2/experiments/M2-BRIDGE-ES-H3-OFI/results.json")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    payload = recompute(args.freeze, args.results)
    payload["script"] = {
        "path": os.path.relpath(os.path.abspath(__file__), _REPO),
        "sha256": materiality.sha256_file(os.path.abspath(__file__)),
    }

    if args.out:
        target = materiality.config_module.repo_path(args.out)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w") as handle:
            json.dump(materiality.clean(payload), handle, indent=2, sort_keys=True)
            handle.write("\n")
    else:
        print(json.dumps(materiality.clean(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
