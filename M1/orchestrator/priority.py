"""Deterministic priority ordering for the M1 frontier (handoff §7).

    DecisionLeverage = impact x kill_potential x work_tier / effort

Every factor is a small ordinal from the migration table, so the ordering is reproducible, has
no invented probabilities, and equal inputs break ties on issue id. The function exists to stop
blockers being processed by id or file order, and to prevent Tier-4 measurement work being
spent on a candidate that an unresolved Tier-1 fact might kill.
"""

from __future__ import annotations

IMPACT_WEIGHT = {"ONE": 1, "SMALL": 2, "MEDIUM": 3, "HIGH": 4, "GLOBAL": 5}
KILL_WEIGHT = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
EFFORT_WEIGHT = {"SMALL": 1, "MEDIUM": 2, "LARGE": 3}
# Tier 1 (cheap physical/economic killers) is weighted highest: a fact that can delete a
# branch beats a measurement that can refine it.
TIER_WEIGHT = {1: 4, 2: 3, 3: 2, 4: 1}


def leverage_score(card) -> float:
    return (IMPACT_WEIGHT[card["branch_impact"]]
            * KILL_WEIGHT[card["kill_potential"]]
            * TIER_WEIGHT[card["tier"]]
            / EFFORT_WEIGHT[card["estimated_effort"]])


def rank(cards) -> list:
    """Rank cards by leverage, descending; ties broken by blocker id for determinism."""
    scored = []
    for card in cards:
        card = dict(card)
        card["priority_score"] = round(leverage_score(card), 3)
        scored.append(card)
    scored.sort(key=lambda c: (-c["priority_score"], c["blocker_id"]))
    return scored


def ordering_rationale(card) -> str:
    return (f"tier {card['tier']} x impact {card['branch_impact']} x kill {card['kill_potential']}"
            f" / effort {card['estimated_effort']} = {card['priority_score']}")


def tier_guard(cards) -> list:
    """Report frontier entries that violate the tier rule.

    A Tier-4 (measurement) item is only legitimate when no cheaper unresolved fact could
    delete the same candidate. This returns the violations rather than silently reordering,
    because a violation is a modelling error worth seeing.
    """
    violations = []
    cheap_blockers = {}
    for card in cards:
        if card["tier"] in (1, 2, 3):
            for cid in card["affected_candidates"]:
                cheap_blockers.setdefault(cid, []).append(card["blocker_id"])
    for card in cards:
        if card["tier"] != 4:
            continue
        for cid in card["affected_candidates"]:
            if cid in cheap_blockers:
                violations.append({
                    "blocker_id": card["blocker_id"],
                    "candidate_id": cid,
                    "cheap_unresolved": "|".join(cheap_blockers[cid]),
                    "note": "Tier-4 work scheduled while a cheaper unresolved fact can still "
                            "delete this candidate.",
                })
    return violations