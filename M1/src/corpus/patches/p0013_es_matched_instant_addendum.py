"""Code-authored evidence patch P-0013: the ES matched-instant unconditional addendum.

Provenance: the project's own closeout addendum
`M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.json` (sha256
``ba3717274896f04100a2674e2735265e8ee76e179f11611b73c7078fba764cf1``), computed by
`M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.py` (sha256
``e7d8405b745063c0f004abbaba9ac0055f897d135aeb5ac7f609f5ad01979dd0``) from the sealed ES contract
(`42a158c5...`) and the admitted 2023-07-17 ESU3 slice, reusing `M2/src/es_materiality.py` at its
sealed hash ``2a07bbd4...`` unchanged.

The defect this closes (V3 claim B6'): the frozen `results.json` reports its unconditional
side-ignoring markout over the quote-available slots (``quote_mask``: 598 at 1 s) and its
conditional side-signed gross over the evaluated observations (``observation_mask``: 583 at 1 s).
Those are different instant sets, so the two published columns invite a same-population reading
they do not support. The addendum recomputes the unconditional figure on EXACTLY the conditional
instants at every frozen horizon and carries both denominators beside every number.

| horizon | quote-available slots | conditional observations | unconditional over quote-available | unconditional over the conditional instants | delta | conditional gross |
|---|---|---|---|---|---|---|
| 1 s (primary) | 598 | 583 | +0.0156746 bps | +0.0208001 bps | +0.0051255 | -0.0047336 bps |
| 5 s | 594 | 579 | +0.0631091 bps | +0.0547556 bps | -0.0083535 | -0.0014608 bps |
| 15 s | 584 | 569 | +0.1340817 bps | +0.1240628 bps | -0.0100189 | +0.0502825 bps |

The conditional state is BELOW its own matched-instant unconditional baseline at every horizon.

What this patch does NOT do: it changes no verdict. The kill fires on the conditional
primary-horizon gross being non-positive (``PRIMARY_HORIZON_GROSS_NOT_POSITIVE``) and,
independently, on ``hi`` (0.0403358) <= ``C0`` (0.5770016). The unconditional markout is the
side-ignoring null baseline, reported so the conditional figure can be read against it; it is not
an input to ``classify_materiality`` and the addendum cannot move either arm. No gate is proposed,
no candidate field is touched, and the addendum is explicitly not independent evidence: it is the
same arithmetic on the same inputs with one changed averaging set.
"""

from __future__ import annotations

PATCH_ID = "P-0013"
ACCESS = "2026-10-01"
ADDENDUM_PATH = "M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.json"
ADDENDUM_SHA = "ba3717274896f04100a2674e2735265e8ee76e179f11611b73c7078fba764cf1"
SCRIPT_PATH = "M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.py"
SCRIPT_SHA = "e7d8405b745063c0f004abbaba9ac0055f897d135aeb5ac7f609f5ad01979dd0"
ES_SOURCE_LIMITATIONS = (
    "One venue, one instrument, one contract month, one 10-minute window, one session; C0 contains "
    "no verified exchange/clearing/FCM charge, so the measured friction is a floor and not an "
    "all-in cost; pre-outcome sealing is asserted by artifact ordering only (no external anchor), "
    "so sealing is UNVERIFIED. The published unconditional markout is the mean over the "
    "quote-available slots while the conditional gross is over the evaluated observations - two "
    "different instant sets, stated side by side in the closeout addendum "
    "(M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.json, sha256 "
    "ba371727...), which recomputes the unconditional on exactly the conditional instants "
    "(+0.0208001 / +0.0547556 / +0.1240628 bps at 1 / 5 / 15 s against the published +0.0156746 / "
    "+0.0631091 / +0.1340817) and records that neither figure changes the verdict."
)


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0009-MECH-CME", "UNK-0018-CME"],
        "candidate_ids": ["TUP-CME-ES-H3-OFI-AGG"],
        "new_sources": [{
            "source_id": "SRC-0249",
            "title": "M2-BRIDGE-ES-H3-OFI closeout addendum - the unconditional markout recomputed "
                     "on the conditional instants",
            "authors_or_org": "This project (GOAL-M2-BRIDGE-001, epoch-6 closeout pass)",
            "publication_date": "2026-10-01",
            "access_date": ACCESS,
            "date_basis": "computed 2026-10-01 from the sealed ES contract (freeze sha256 "
                          "42a158c584552392e6c21535f35b3887228ea209c47257dee97672f6bfd75568) and the "
                          "admitted 2023-07-17T133000Z slice, after verification wave V3 recorded "
                          "the instant-set inconsistency; the measured window itself is "
                          "2023-07-17T13:30:00Z-13:40:00Z",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "CME index futures",
            "venue": "CME (Globex), ESU3 (E-mini S&P 500, Sep-2023 contract)",
            "sample_period": "one 10-minute RTH-open window, 2023-07-17T13:30:00Z-13:40:00Z",
            "sample_size": "599 one-second decision slots; 598 quote-available at the 1 s primary "
                           "horizon against 583 evaluated (non-zero-state) observations",
            "methodology": "Recomputes the unconditional side-ignoring midpoint markout over the "
                           "same instants as the conditional statistic, at every frozen horizon, "
                           "reusing M2/src/es_materiality.py unchanged (its loaders, build_panel, "
                           "state_direction, quote_mask, observation_mask and gross_markout_bps) on "
                           "the sealed contract and the admitted inputs; the single change is that "
                           "the unconditional mean is taken over observation_mask instead of "
                           "quote_mask. The script reproduces the published conditional, "
                           "unconditional and observation-count fields of results.json before "
                           "reporting the matched-instant variant, and the addendum JSON records "
                           "the script's own sha256.",
            "gross_or_net": "GROSS side-ignoring midpoint markout in bps of the entry midpoint; no "
                            "cost is deducted and the quantity is not used in any decision",
            "independent_replication": "Reproduces the published results.json fields exactly "
                                       "(conditional gross, unconditional markout and observation "
                                       "count at 1 / 5 / 15 s; agreement asserted at 1e-12 in the "
                                       "addendum artifact); it is a recomputation of the frozen "
                                       "arithmetic, not an independent re-derivation of the book",
            "limitations": "Not independent evidence: the same arithmetic on the same inputs with "
                           "one changed averaging set, carrying no new economic content. It is not "
                           "an input to classify_materiality and cannot move the verdict. It "
                           "re-derives no order book, quote or trade.",
            "raw_citation_token": "code:P-0013",
            "local_path": ADDENDUM_PATH,
            "sha256": ADDENDUM_SHA,
            "status": "PARTIAL",
            "claim_scope": "Record-level correction to the ES measurement: the unconditional "
                           "side-ignoring markout on the same instants as the conditional "
                           "statistic, at 1 / 5 / 15 s, with both denominators stated, and the "
                           "explicit finding that the correction changes no verdict.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0074",
            "claim": "The ES record's published unconditional side-ignoring markout and its "
                     "conditional side-signed gross are computed on different instant sets: at the "
                     "1 s primary horizon the unconditional is the mean over the 598 quote-available "
                     "slots while the conditional is over the 583 non-zero-state observations. "
                     "Recomputed on EXACTLY the conditional instants the unconditional reads "
                     "+0.0208001 bps at 1 s (published +0.0156746, delta +0.0051255), +0.0547556 bps "
                     "at 5 s (published +0.0631091 over 594 slots, delta -0.0083535) and +0.1240628 "
                     "bps at 15 s (published +0.1340817 over 584 slots, delta -0.0100189), against "
                     "conditional grosses of -0.0047336 / -0.0014608 / +0.0502825 bps. The "
                     "conditional state is BELOW its own matched-instant baseline at every horizon. "
                     "The correction changes no verdict: the fired clause is the conditional "
                     "primary-horizon gross being non-positive "
                     "(PRIMARY_HORIZON_GROSS_NOT_POSITIVE) and the independent arm hi (0.0403358) "
                     "<= C0 (0.5770016) also holds; the unconditional markout is the side-ignoring "
                     "null baseline, is not an input to classify_materiality, and the verdict stays "
                     "KILL_MATERIALITY with scope SAMPLE_SCOPED_DEVELOPMENT_KILL.",
            "source_id": "SRC-0249",
            "candidate_ids": "TUP-CME-ES-H3-OFI-AGG",
            "mechanism_id": "MECH-OFI",
            "venue_id": "VEN-CME-ES",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "NEUTRAL",
            "methodology": "Addendum recomputation against the sealed contract and admitted inputs: "
                           "the frozen module's own loaders, build_panel, state_direction, "
                           "quote_mask, observation_mask and gross_markout_bps are reused unchanged; "
                           "the unconditional side-ignoring markout is averaged over "
                           "observation_mask instead of quote_mask. The published conditional, "
                           "unconditional and observation-count fields reproduce exactly before the "
                           "matched-instant variant is reported.",
            "sample": "599 one-second decision slots; 583 evaluated observations at 1 s, 579 at 5 s "
                      "and 569 at 15 s; 598 / 594 / 584 quote-available slots at the same horizons",
            "temporal_scope": "2023-07-17T13:30:00Z-13:40:00Z (one window, one session)",
            "gross_or_net": "GROSS side-ignoring midpoint markout in bps of the entry midpoint; no "
                            "cost is deducted and this quantity is not an input to any decision",
            "limitations": "(a) It is not independent evidence: it is the same arithmetic on the "
                           "same inputs with one changed averaging set, and it re-derives no book, "
                           "quote or trade. (b) It cannot move the verdict by construction - both "
                           "fired arms concern the conditional gross and C0, and the unconditional "
                           "is the side-ignoring null baseline. (c) It corrects the published "
                           "comparison, not the published measurement: the frozen results.json "
                           "still carries the quote-available-slot variant in the field it was "
                           "computed for, and is not modified.",
            "decision_implication": "No decision changes. The ES H3 OFI row stays DEAD as a "
                                    "SAMPLE_SCOPED_DEVELOPMENT_KILL with its recorded resurrection "
                                    "condition; the addendum only removes the risk that a later "
                                    "reader compares the published unconditional and conditional "
                                    "figures as if they shared an instant set.",
            "contradicts_mechanism": "NO",
            "observed_market": "CME index futures",
            "observed_venue": "VEN-CME-ES",
            "observed_instrument_or_universe": "ESU3 (E-mini S&P 500 futures, September 2023 "
                                               "contract), instrument id 3445",
            "observed_period": "2023-07-17",
            "observed_horizon": "H3 (1 / 5 / 15 s; the frozen primary horizon is 1 s)",
            "candidate_link_reason": "The addendum corrects a record-level comparison inside this "
                                     "candidate's own frozen measurement; it exists so the row's "
                                     "recorded null baseline and conditional gross cannot be "
                                     "misread as sharing an instant set.",
            "transfer_status": "DIRECT",
            "verification_status": "REPRODUCIBLE_FROM_SEALED_ARTEFACTS",
        }],
        "modified_claims": [
            {
                "claim": "The ES record's published unconditional and conditional markouts may be "
                         "read as one population.",
                "status": "CORRECTED",
                "reason": "V3 claim B6' identified the two denominators (598 quote-available slots "
                          "against 583 evaluated observations at 1 s). The closeout addendum "
                          "(SRC-0249, EVD-0074) recomputes the unconditional on exactly the "
                          "conditional instants at every frozen horizon and the corrected figures "
                          "now stand beside the published ones in the SRC-0246 limitations; the "
                          "verdict is explicitly unaffected. Nothing is deleted: the frozen "
                          "results.json keeps the quote-available-slot variant in the field it was "
                          "computed for.",
            },
        ],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "proposed_source_updates": [{
            "source_id": "SRC-0246",
            "fields": {"limitations": ES_SOURCE_LIMITATIONS},
            "reason": "EVD-0074 / SRC-0249: the ES source's limitations must state that its "
                      "published unconditional and conditional figures use different instant sets, "
                      "name the addendum that recomputes the unconditional on the conditional "
                      "instants, and record that neither figure changes the verdict. Replaces the "
                      "clause that only flagged the gap without the matched-instant numbers.",
        }],
        "decision": "NO_CHANGE",
        "reason": "A record-level integrity repair, not a verdict: the ES branch's frozen "
                  "measurement compared an unconditional figure over 598 quote-available slots with "
                  "a conditional figure over 583 observations. The addendum recomputes the "
                  "unconditional on exactly the conditional instants (+0.0208001 / +0.0547556 / "
                  "+0.1240628 bps at 1 / 5 / 15 s), states both denominators beside every number "
                  "and records that the verdict is unchanged because the kill fires on the "
                  "conditional primary-horizon gross being non-positive and independently on "
                  "hi <= C0. No gate is proposed, no candidate field moves, and the frozen "
                  "artifacts are untouched.",
        "verification_notes": "Contrary evidence and self-serving readings were searched for before "
                              "the correction was recorded. The addendum was checked to reproduce "
                              "the published conditional gross, the published unconditional markout "
                              "and the published observation counts at all three horizons "
                              "(agreement asserted at 1e-12), so the recomputation is anchored to "
                              "the frozen record rather than to a re-implementation. The strongest "
                              "counter-reading - that the matched-instant figure is above the "
                              "published one at the primary horizon (+0.0208001 vs +0.0156746) and "
                              "might therefore matter - was tested and rejected: the unconditional "
                              "is the side-ignoring null baseline, is not consumed by "
                              "envelope.classify_materiality, and both fired arms (g <= 0 and "
                              "hi <= C0) concern the conditional gross and C0 alone. The value "
                              "that would have been most convenient to hide (the 5 s and 15 s "
                              "deltas move the other way) is reported in full. No frozen "
                              "parameter, artifact or sealed hash was touched.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
