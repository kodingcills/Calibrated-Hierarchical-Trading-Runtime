#!/usr/bin/env python3
"""V1 independent adversarial checks for the W5 envelope (CLAIM SET B).

Does not import the W5 test module.  Exercises the public API directly and reports
raw observations for the claim table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from M2.src import envelope as env  # noqa: E402

LEDGER = json.loads((ROOT / "M2" / "config" / "cost_ledger_v1.json").read_text())


def out_of(fn, *a, **k):
    try:
        return {"ok": True, "value": fn(*a, **k)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "exc": type(exc).__name__, "msg": str(exc)[:160]}


def main() -> int:
    res: dict = {}

    # --- B10: classify_materiality exact rule, boundaries ---------------------
    cases = {
        "g=0": (0.0, -1.0, 1.0, 0.5),
        "g<0": (-0.001, -1.0, 1.0, 0.5),
        "hi==C0": (1.0, 0.1, 0.5, 0.5),
        "lo==C0": (1.0, 0.5, 0.9, 0.5),
        "lo>C0": (1.0, 0.500001, 0.9, 0.5),
        "straddle": (1.0, 0.2, 0.9, 0.5),
        "g<=0 and lo>C0 (precedence)": (-1.0, 0.9, 2.0, 0.5),
        "unsorted interval (hi,lo swapped)": (1.0, 0.9, 0.2, 0.5),
    }
    res["classify_cases"] = {k: env.classify_materiality(*v)["verdict"] for k, v in cases.items()}
    res["classify_cases_detail"] = {
        "hi_eq_c0_expected": "KILL_MATERIALITY", "lo_eq_c0_expected": "INDETERMINATE",
        "lo_gt_c0_expected": "SURVIVE_PROVISIONAL", "g_le_0_precedence_expected": "KILL_MATERIALITY",
    }

    # significance not an input: signature inspection
    import inspect
    sig = inspect.signature(env.classify_materiality)
    res["classify_signature"] = str(sig)
    res["significance_is_not_a_param"] = "signif" not in str(sig) and "p_value" not in str(sig)
    res["significance_role"] = env.significance_against_zero(3.0, 1.0)["role"]
    res["classify_flags_significance_not_criterion"] = env.classify_materiality(
        1.0, 0.1, 0.9, 0.5).get("significance_is_decision_criterion")

    # --- B11: unknown-unit refusal --------------------------------------------
    res["unknown_unit"] = {
        "to_usd": out_of(env.to_usd, 1.0, "WIDGETS"),
        "from_usd": out_of(env.from_usd, 1.0, "WIDGETS"),
        "convert": out_of(env.convert, 1.0, "WIDGETS", env.UNIT_USD),
        "convert_usd_to_widgets": out_of(env.convert, 1.0, env.UNIT_USD, "WIDGETS"),
        "contract_without_multiplier_to_bps": out_of(
            env.convert, 10.0, env.UNIT_USD_PER_CONTRACT, env.UNIT_BPS,
            env.Basis(quantity=2, price_usd=5000.0)),
        "unknown_value_to_usd": out_of(env.to_usd, None, env.UNIT_USD),
    }

    # --- B11: C1 is never silently zero ---------------------------------------
    env_floor = env.envelope_from_ledger(LEDGER, "STRUCTURAL_COST_FLOOR")
    res["c0_set_structural_floor"] = [i.id for i in env_floor.c0_items()]
    res["c1_set_structural_floor"] = [i.id for i in env_floor.c1_items()]
    res["structural_c0_usd_no_basis"] = out_of(env_floor.structural_c0_usd)
    res["c1_total_usd_with_unknown"] = env_floor.unresolved_c1_total_usd()
    res["c1_known_breakdown"] = env_floor.unresolved_c1_known_usd()

    ref = env.envelope_from_ledger(LEDGER, "ACCESSIBLE_REFERENCE_PATH")
    res["c0_set_reference_path"] = [i.id for i in ref.c0_items()]
    res["c1_set_reference_path"] = [i.id for i in ref.c1_items()]
    res["reference_path_c1_total"] = ref.unresolved_c1_total_usd()
    res["reference_path_c1_known"] = ref.unresolved_c1_known_usd()

    # adversarial: a C1 item whose value is unknown must never read as 0
    unknown_item = env.CostItem(id="cme", name="CME", unit="UNKNOWN", value=None,
                                provenance=env.Provenance(source_id="s", url="u", access_date="d",
                                                          status=env.STATUS_VERIFIED))
    e2 = env.Envelope(envelope_id="x", items=(unknown_item,))
    res["c1_unknown_total_is_none"] = e2.unresolved_c1_total_usd()
    res["c1_unknown_known_usd"] = e2.unresolved_c1_known_usd()

    # adversarial: an unevaluable C1 (known value, missing basis input) is also not zeroed
    pass_through = env.CostItem(id="pass", name="passthrough", unit=env.UNIT_MULTIPLIER_OF_COMMISSION,
                                value=0.000565, provenance=env.Provenance(
                                    source_id="s", url="u", access_date="d",
                                    status=env.STATUS_VERIFIED))
    e3 = env.Envelope(envelope_id="y", items=(pass_through,))
    res["c1_unevaluable_total"] = e3.unresolved_c1_total_usd()
    res["c1_unevaluable_known"] = e3.unresolved_c1_known_usd()

    # --- B8: ledger provenance + effective periods for the three C0 items -----
    by_id = {it["id"]: it for it in LEDGER["line_items"]}
    prov = {}
    for i in ("nasdaq_remove_liquidity_fee", "sec_section_31_fee", "finra_trading_activity_fee"):
        it = by_id[i]
        prov[i] = {
            "effective_date": it.get("effective_date"),
            "source_publisher": it.get("source", {}).get("publisher"),
            "source_url": it.get("source", {}).get("url"),
            "retrieval_status": it.get("source", {}).get("retrieval_status"),
            "cross_check_status": it.get("cross_check_status"),
            "applicability": it.get("applicability"),
            "value": it.get("value"), "unit": it.get("unit"),
        }
    res["c0_provenance"] = prov
    res["rates_apply_to_period"] = LEDGER.get("rates_apply_to_period")

    (Path(__file__).resolve().parent / "v1_envelope_checks.json").write_text(
        json.dumps(res, indent=2, sort_keys=True, default=str))
    print(json.dumps(res, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())