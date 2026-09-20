"""Canonical constants, taxonomies and table schemas for M1.

Every value here is either:
  * a project convention explicitly registered in ASSUMPTIONS (id prefix ``ASM-``), or
  * a closed vocabulary used to keep the artifacts machine-checkable.

Nothing in this module asserts an external market fact.
"""

UNKNOWN = None
UNKNOWN_TOKEN = "UNKNOWN"

# ---------------------------------------------------------------- taxonomies
# H1..H5 horizon bands. The band *labels* and their millisecond ranges are
# taken from the M1-A evidence artifact (SRC-0011) where they appear as
# "H1 10-100ms", "H2 100ms-1s", "H3 1-15s", "H4 15s-5min", "H5 5min+".
# The microsecond endpoints are a project convention (ASM-0001).
HORIZON_BANDS = {
    "H1": (10_000, 100_000),
    "H2": (100_000, 1_000_000),
    "H3": (1_000_000, 15_000_000),
    "H4": (15_000_000, 300_000_000),
    "H5": (300_000_000, None),
}
HORIZON_TAXONOMY_ASSUMPTION = "ASM-0001"

CANDIDATE_STATUSES = ("ALIVE", "WEAK", "UNKNOWN", "DEAD")
CANDIDATE_CLASSES = (
    "TUPLE",
    "METHOD_RULE",
    "UNIVERSE_DEFINITION",
    "GOVERNANCE",
)
GATE_VALUES = ("PASS", "FAIL", "BLOCKED")
GATE_IDS = ("KG1_MECHANISM", "KG2_DATA", "KG3_EXECUTION", "KG4_HALF_LIFE", "KG5_FALSIFIABILITY")

EVIDENCE_CLASSES = ("CONSENSUS_FACT", "SUPPORTED_FINDING", "CONTESTED_HYPOTHESIS", "EXTRAPOLATION", "UNKNOWN")
SUPPORT_DIRECTIONS = ("SUPPORTS", "WEAKENS", "NEUTRAL")
SOURCE_STATUSES = ("VERIFIED", "PARTIAL", "UNRESOLVED", "SUPERSEDED")
SEVERITIES = ("BLOCKING", "IMPORTANT", "NON_BLOCKING")
ISSUE_STATUSES = ("OPEN", "PARTIAL", "RESOLVED", "SUPERSEDED")

# Resolution classes used by the M1-D0 readiness report (SRC-0026, D.1 readiness section).
RESOLUTION_CLASSES = {
    "A": "resolvable by additional public/web research",
    "B": "requires exchange/vendor/broker quote or sample",
    "C": "requires M2 empirical measurement",
    "D": "unresolved but non-blocking",
}

EXECUTION_STYLES = ("AGGRESSIVE", "PASSIVE", "MIXED", "AUCTION")

PASSIVE_EXECUTION_STYLES = ("PASSIVE",)

# ------------------------------------------------------------ fee machinery
FEE_UNITS = ("BPS", "PERCENT", "USD_PER_SHARE", "USD_PER_CONTRACT", "USD", "UNKNOWN")

# Cost components that must all be known/parameterised before a full break-even
# may be reported (SRC-0026, D0.1).
BREAK_EVEN_COMPONENTS = (
    "spread",
    "fees",
    "slippage",
    "adverse_selection",
    "impact",
)

# --------------------------------------------------------------- table specs
# ``numeric`` maps a column holding a machine-usable number to the column that
# must cite its provenance.  Validation fails when a numeric cell is populated
# without a resolvable source, or when an empty numeric cell is not declared in
# the row's ``unknown_fields`` column.
TABLE_SPECS = {
    "source_registry": {
        "id": "source_id",
        "numeric": {},
    },
    "evidence_ledger": {
        "id": "evidence_id",
        "numeric": {},
    },
    "venue_facts": {
        "id": "venue_id",
        "numeric": {
            "tick_size": "tick_size_source_id",
            "lot_size": "lot_size_source_id",
            "maker_fee_value": "maker_fee_source_id",
            "taker_fee_value": "taker_fee_source_id",
            "rebate_value": "rebate_source_id",
            "clearing_fee_value": "clearing_fee_source_id",
            "other_exchange_fee_value": "other_exchange_fee_source_id",
            "funding_value": "funding_source_id",
            "margin_requirement": "margin_requirement_source_id",
            "perp_open_fee_value": "perp_open_fee_source_id",
            "perp_close_fee_value": "perp_close_fee_source_id",
            "live_feed_min_interval_us": "live_feed_min_interval_source_id",
        },
    },
    "mechanisms": {"id": "mechanism_id", "numeric": {}},
    "candidate_tuples": {
        "id": "candidate_id",
        "numeric": {
            "horizon_min_us": "horizon_taxonomy_source_id",
            "horizon_max_us": "horizon_taxonomy_source_id",
        },
    },
    "data_feasibility": {"id": "candidate_id", "numeric": {}},
    "execution_envelopes": {
        "id": "candidate_id",
        "numeric": {
            "one_way_taker_fee_bps": "fee_source_ids",
            "one_way_maker_fee_bps": "fee_source_ids",
            "round_trip_maker_maker_fee_bps": "fee_source_ids",
            "round_trip_maker_taker_fee_bps": "fee_source_ids",
            "round_trip_taker_taker_fee_bps": "fee_source_ids",
            "known_cost_floor_bps": "fee_source_ids",
            "known_cost_floor_native_value": "fee_source_ids",
            "required_round_trip_fee_native_value": "fee_source_ids",
            "full_break_even_bps": "break_even_source_ids",
        },
    },
    "technology_fit": {"id": "fit_id", "numeric": {}},
    "discrepancies": {"id": "issue_id", "numeric": {}},
    "open_questions": {"id": "question_id", "numeric": {}},
    "dead_candidates": {"id": "candidate_id", "numeric": {}},
    "assumptions": {"id": "assumption_id", "numeric": {}},
    "kill_gates": {"id": "gate_id", "numeric": {}},
    "experiments": {"id": "experiment_id", "numeric": {}},
    "hypotheses": {"id": "hypothesis_id", "numeric": {}},
}
