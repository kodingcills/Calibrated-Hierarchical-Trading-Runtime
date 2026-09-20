"""Kill-gate state machine (KG1..KG5) and its derived counts.

The five gates are the M1-C materialisation gates (handoff C10). ``related_lifecycle_gate``
maps each onto the project's longer G0..G8 promotion ladder (SRC-0014) so the two vocabularies
stay reconcilable instead of competing.

The ``candidates_pass`` / ``candidates_blocked`` / ``candidates_fail`` columns are computed at
materialisation time from candidate_tuples and are never authored by hand.
"""

from .constants import UNKNOWN

COLUMNS = [
    "gate_id", "name", "question", "pass_criterion", "fail_criterion", "blocked_criterion",
    "required_evidence", "related_lifecycle_gate", "source_id",
    "candidates_pass", "candidates_blocked", "candidates_fail",
]

ROWS = [
    dict(
        gate_id="KG1_MECHANISM",
        name="Mechanism",
        question="Is there evidence that this mechanism produces the claimed effect on this "
                 "venue/instrument, with an economic payer who can be named and evidenced?",
        pass_criterion="Venue/instrument-specific evidence of the effect AND a payer whose "
                       "constraint is evidenced.",
        fail_criterion="Evidence shows the mechanism cannot operate for this candidate as stated.",
        blocked_criterion="Mechanism is plausible or supported elsewhere, or the payer "
                          "interpretation is an extrapolation, and no venue-specific evidence exists.",
        required_evidence="Mechanism evidence records with venue-specific sample; payer evidence.",
        related_lifecycle_gate="G0_IDEA -> G1_REGISTERED",
        source_id="SRC-0026|SRC-0013"),
    dict(
        gate_id="KG2_DATA",
        name="Data",
        question="Can the required observations be obtained live and historically with point-in-time "
                 "integrity and adequate timestamp semantics?",
        pass_criterion="Live feed, historical feed, PIT reconstruction and timestamp adequacy are "
                       "all verified, or procurement is contracted.",
        fail_criterion="A required data property is structurally absent (e.g. the accessible history "
                       "is Level 1 while individual order queues are required).",
        blocked_criterion="Data is advertised or technically feasible but licence, schema, cost or "
                          "timestamp semantics are unresolved.",
        required_evidence="Venue feed specification, historical product terms, sample-file schema and "
                          "timestamp validation.",
        related_lifecycle_gate="G3_RETROSPECTIVE (point-in-time audit)",
        source_id="SRC-0026|SRC-0014"),
    dict(
        gate_id="KG3_EXECUTION",
        name="Execution envelope",
        question="Does a verified cost/fill/latency envelope leave room for the hypothesised effect?",
        pass_criterion="All mandatory cost components verified or explicitly parameterised, fill "
                       "behaviour modelled under the venue's actual matching rule, and measured "
                       "decision-to-market latency inside the signal's usable life.",
        fail_criterion="A verified mandatory cost already exceeds the plausible gross effect, or the "
                       "required execution path is structurally inaccessible.",
        blocked_criterion="Fees, spread, slippage, impact, adverse selection, fill probability or "
                          "latency are unverified.",
        required_evidence="Fee schedule, fill model or shadow-fill evidence, markout distribution, "
                          "latency distribution.",
        related_lifecycle_gate="G3_RETROSPECTIVE -> G5_SHADOW",
        source_id="SRC-0026|SRC-0016"),
    dict(
        gate_id="KG4_HALF_LIFE",
        name="Signal half-life",
        question="Is the empirical EV-versus-delay curve known well enough to place a decision "
                 "deadline?",
        pass_criterion="A measured EV(delay) curve exists for this candidate's signal and the "
                       "permitted decision age sits inside its viable region.",
        fail_criterion="Measurement shows the signal has no viable region at any achievable delay.",
        blocked_criterion="No empirical curve exists; 'next tick' and 'short horizon' are not "
                          "substitutes.",
        required_evidence="Delay-sweep measurement reporting gross conditional markout and "
                          "execution-aware EV at controlled delays.",
        related_lifecycle_gate="G5_SHADOW (live signal decay)",
        source_id="SRC-0016|SRC-0011"),
    dict(
        gate_id="KG5_FALSIFIABILITY",
        name="Falsifiability",
        question="Can a pre-registerable falsifier be written for this candidate exactly as stated?",
        pass_criterion="Instrument, venue, horizon, mechanism and execution style are specified "
                       "tightly enough to state a measurable outcome, baseline set, null set and "
                       "kill criterion.",
        fail_criterion="The row is not a valid unit of analysis (generic universe, generic market "
                       "structure, or a governance rule masquerading as a strategy).",
        blocked_criterion="Specification gap that is resolvable by choosing one exact "
                          "instrument/venue/participant class.",
        required_evidence="A named instrument and venue, primary outcome, baselines, nulls, dataset "
                          "version, planned split, kill criteria.",
        related_lifecycle_gate="G1_REGISTERED",
        source_id="SRC-0026|SRC-0014"),
]

BY_ID = {row["gate_id"]: row for row in ROWS}