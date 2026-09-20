"""Frontier construction and the closure status snapshot (handoff §4, §14 STEP 2, §16).

The frontier is recomputed from canonical state on every pass. Nothing here caches a queue
between iterations: a stale queue is how a resolver ends up working on an item that a cheaper
fact already killed.
"""

from __future__ import annotations

UNKNOWN = None

CLUSTERS = {
    "CME": ("TUP-CME-ES-H1-QDEP-PAS", "TUP-CME-ES-H3-OFI-AGG", "TUP-CME-NQ-H3-OFI-AGG",
            "TUP-CME-TSY-H2-QREPL-MIX", "TUP-CME-WTI-H4-FLOWVOL-AGG", "TUP-GENERIC-CME-QUEUE"),
    "NASDAQ_EQUITY": ("TUP-NASDAQ-LARGETICK-H2-QIMB-AGG", "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
                      "TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG",
                      "TUP-NASDAQ-LARGETICK-H1H2-QUEUEPOS-L1ONLY-AGG"),
    "CBOE_EQUITY": ("TUP-CBOEBZX-LARGETICK-H2H3-SPREADCAP-PAS",),
    "HYPERLIQUID": ("TUP-HYPERLIQUID-BTCPERP-H1-QDEP-AGGPAS",
                    "TUP-HYPERLIQUID-BTCPERP-H3-OFILIQ-AGG",
                    "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"),
    "CBOE_OPTIONS": ("TUP-CBOE-USOPT-H5-SURFRV-MIX",),
    "EUREX": ("TUP-EUREX-FESX-H2H3-OFIQ-MIX",),
    "DERIBIT": ("TUP-DERIBIT-BTCOPT-H5-SURFRV-MIX",),
    "EVENT_MARKETS": ("TUP-KALSHI-EVENT-H5-EVENTINF-AGG",
                      "TUP-POLYMARKET-EVENT-H5-EVENTINF-AGG"),
    "CRYPTO_SPOT": ("TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG", "TUP-KRAKEN-BTCUSD-H3-MICROOFI-AGG"),
    "US_EQUITY_CROSS": ("TUP-USSTOCK-XVENUE-H1-STALEQUOTE-AGG",),
    "FX": ("TUP-FX-ECN-H2H3-LEADLAG-AGG", "TUP-FX-RETAILBROKER-H3H4-FEEDLAG-AGG"),
    "METHOD_OR_GOVERNANCE": ("TUP-METHOD-PASSIVE-TOUCHFILL", "TUP-GENERIC-CRYPTO-MICRO",
                             "TUP-SYSTEMONE-HARDCORE-ENGINE",
                             "TUP-JEV-HOSTED-LATENCY-UNMEASURED"),
}


def cluster_of(candidate_id) -> str:
    for name, members in CLUSTERS.items():
        if candidate_id in members:
            return name
    return "UNCLUSTERED"


def cluster_summary(cards) -> dict:
    """Group frontier cards into coherent evidence clusters (handoff §8)."""
    out = {}
    for card in cards:
        touched = {cluster_of(cid) for cid in card["affected_candidates"]
                   if not cid.startswith("ALL_")} or {"GLOBAL"}
        for cluster in touched:
            out.setdefault(cluster, []).append(card["blocker_id"])
    return {k: sorted(v) for k, v in sorted(out.items())}


def frontier_payload(cards_ranked, computed_gates, candidates, gate_eligible, generated_at):
    return {
        "generated_at": generated_at,
        "active_item_count": len(cards_ranked),
        "items": [
            {
                "blocker_id": c["blocker_id"],
                "title": c["title"],
                "resolution_method": c["resolution_method"],
                "resolution_stage": c["resolution_stage"],
                "tier": c["tier"],
                "status": c["status"],
                "priority_score": c["priority_score"],
                "priority_reason": c["priority_reason"],
                "affected_candidates": c["affected_candidates"],
                "affected_gates": c["affected_gates"],
                "decision_prevented": c["decision_prevented"],
                "success_condition": c["success_condition"],
                "kill_condition": c["kill_condition"],
            }
            for c in cards_ranked
        ],
        "clusters": cluster_summary(cards_ranked),
        "gate_eligible_candidates": gate_eligible,
        "next_item": cards_ranked[0]["blocker_id"] if cards_ranked else UNKNOWN,
    }


def closure_status(computed, candidates, cards, counts, migration_counts, generated_at,
                   external_queue, spec_ids, iterations, closure_modes=None,
                   awaiting_external=()) -> dict:
    """Machine-readable closure snapshot: everything the next session must not have to re-derive."""
    gate_vectors = {}
    for cid, cand in sorted(computed.items()):
        gate_vectors[cid] = {
            g: {"value": cand[g].value, "rule": cand[g].rule, "reason": cand[g].reason}
            for g in ("KG1_MECHANISM", "KG2_DATA", "KG3_EXECUTION", "KG4_HALF_LIFE",
                      "KG5_FALSIFIABILITY")
        }
    eligible = sorted(cid for cid, v in gate_vectors.items()
                      if all(g["value"] == "PASS" for g in v.values()))
    return {
        "generated_at": generated_at,
        "milestones": {
            "M1-A": "INCOMPLETE",
            "M1-B": "AUTHORIZED" if eligible else "NOT_AUTHORIZED",
            "M1-C": "COMPLETE",
            "M1-D0": "COMPLETE",
            "M1-D1": "AUTHORIZED" if eligible else "NOT_AUTHORIZED",
        },
        "terminal_state": terminal_state(eligible, counts),
        "candidate_counts": counts,
        "closure_modes": closure_modes or {},
        "awaiting_external_closure": list(awaiting_external),
        "gate_eligible": eligible,
        "migration": migration_counts,
        "frontier": {
            "active_items": [c["blocker_id"] for c in cards],
            "next_item": cards[0]["blocker_id"] if cards else UNKNOWN,
        },
        "external_actions_queued": external_queue,
        "m2_specs_generated": spec_ids,
        "iterations_recorded": iterations,
        "gate_vectors": gate_vectors,
    }


def terminal_state(eligible, counts) -> str:
    """One of the four legitimate M1 outcomes, or the open state that precedes them.

    ``counts`` must be the flat status counts; a nested mapping would compare None to None and
    silently report a terminal failure.
    """
    total = counts.get("total", 0)
    dead = counts.get("DEAD", 0)
    if not total:
        return "UNKNOWN"
    if eligible:
        return "M1_PASSED" if len(eligible) >= 2 else "M1_PARTIAL"
    if dead == total:
        return "M1_FAILED"
    return "M1_OPEN"