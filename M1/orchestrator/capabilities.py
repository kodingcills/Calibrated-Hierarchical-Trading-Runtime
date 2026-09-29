"""Adaptive campaign capability and topology contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

TOPOLOGIES = frozenset({
    "DETERMINISTIC", "SERIAL_REASONING", "SERIAL_SEARCH", "PARALLEL_SEARCH",
    "DIVERSE_HYPOTHESIS", "ADVERSARIAL", "INDEPENDENT_REPLICATION", "EXTERNAL",
})

@dataclass(frozen=True)
class Capability:
    id: str
    purpose: str
    valid_input: str
    allowed_topologies: frozenset[str]
    default_verification: str
    can_modify_state: bool
    external_dependency_behavior: str
    expected_output_type: str
    state_write_policy: str

    def validate_topology(self, topology: str) -> None:
        if topology not in TOPOLOGIES:
            raise ValueError(f"unsupported topology: {topology}")
        if topology not in self.allowed_topologies:
            raise ValueError(f"{self.id} does not permit {topology}")


def _cap(capability_id: str, purpose: str, valid_input: str,
         topologies: set[str], verification: str, can_modify: bool,
         external: str, output: str, policy: str) -> Capability:
    return Capability(capability_id, purpose, valid_input, frozenset(topologies),
                      verification, can_modify, external, output, policy)


CAPABILITIES: Mapping[str, Capability] = {
    "DETERMINISTIC_ANALYSIS": _cap(
        "DETERMINISTIC_ANALYSIS", "Exact transformation, dependency, ranking, or validation.",
        "Canonical machine-readable state.", {"DETERMINISTIC"}, "deterministic_reproduction",
        False, "surface external prerequisites without assuming them", "analysis_record",
        "no_canonical_mutation"),
    "PRIMARY_SOURCE_SEARCH": _cap(
        "PRIMARY_SOURCE_SEARCH", "Resolve a specific factual uncertainty from an authoritative source.",
        "A bounded factual question and provenance target.", {"SERIAL_SEARCH", "PARALLEL_SEARCH"},
        "independent_source_verification", False, "remain blocked when access is unavailable",
        "provenance_evidence", "verified_evidence_only"),
    "DIVERSITY_SCOUT": _cap(
        "DIVERSITY_SCOUT", "Test an independent mechanism family against a decision-relevant question.",
        "A surviving, non-dead candidate family.", {"PARALLEL_SEARCH"},
        "independent_source_verification", False, "do not let an external block freeze other families",
        "scout_record", "verified_evidence_only"),
    "ADVERSARIAL_FALSIFY": _cap(
        "ADVERSARIAL_FALSIFY", "Attack an important active hypothesis or premise.",
        "An active hypothesis with a falsification condition.", {"ADVERSARIAL"},
        "independent_synthesis", False, "quarantine unresolved external facts", "adversarial_record",
        "verified_evidence_only"),
    "DERIVE_PRECURSOR": _cap(
        "DERIVE_PRECURSOR", "Resolve a cheaper neighboring question that changes parent investigation.",
        "A parent blocker and a cheaper measurable prerequisite.", {"DETERMINISTIC", "SERIAL_REASONING"},
        "deterministic_reproduction", False, "identify, never assume, missing inputs", "precursor_record",
        "no_canonical_mutation"),
    "EXPERIMENT": _cap(
        "EXPERIMENT", "Design or execute a frozen causal empirical test.",
        "A frozen experiment contract and valid data.", {"DETERMINISTIC", "SERIAL_REASONING"},
        "empirical_reproduction", True, "blocked until authorized inputs exist", "experiment_result",
        "verified_evidence_only"),
    "BUILD_TOOL": _cap(
        "BUILD_TOOL", "Build narrowly reusable instrumentation for a recurring uncertainty.",
        "A demonstrated recurring validation need.", {"SERIAL_REASONING", "DETERMINISTIC"},
        "deterministic_reproduction", True, "do not build speculative tooling", "tool_artifact",
        "authorized_file_only"),
    "EXTERNAL_REQUEST": _cap(
        "EXTERNAL_REQUEST", "Convert an external dependency into a precise sendable request.",
        "A blocked external prerequisite.", {"EXTERNAL"}, "request_contract_check", False,
        "surface without autonomous execution", "request_packet", "no_canonical_mutation"),
    "VERIFY": _cap(
        "VERIFY", "Independently validate a material result.", "A produced artifact and its contract.",
        {"DETERMINISTIC", "INDEPENDENT_REPLICATION", "ADVERSARIAL"}, "verification_hierarchy",
        False, "report unavailable dependency", "verification_record", "no_canonical_mutation"),
    "SYNTHESIZE": _cap(
        "SYNTHESIZE", "Reconcile verified evidence into canonical state.", "Verified evidence only.",
        {"DETERMINISTIC", "SERIAL_REASONING"}, "deterministic_reproduction", True,
        "do not synthesize missing evidence", "canonical_patch", "verified_evidence_only"),
    "STOP": _cap(
        "STOP", "Decline compute when remaining decision value is insufficient.",
        "A complete current frontier and explicit justification.", {"DETERMINISTIC"},
        "frontier_completeness_review", False, "external blocks remain visible", "stop_record",
        "no_canonical_mutation"),
}


def get(capability_id: str) -> Capability:
    try:
        return CAPABILITIES[capability_id]
    except KeyError as exc:
        raise ValueError(f"unknown capability: {capability_id}") from exc


def validate(capability_id: str, topology: str) -> None:
    get(capability_id).validate_topology(topology)
