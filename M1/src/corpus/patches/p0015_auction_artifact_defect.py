"""Code-authored evidence patch P-0015: the AUCTION sealed-artefact pointer defect.

Provenance: verification wave V3, re-confirmed in the epoch-6 closeout pass by reading the sealed
artefacts. No sealed artefact was written.

The defect: `M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/freeze.json` carries the key
``as_run_deviations_from_freeze`` with the value

    "recorded in results.json:as_run_deviations_from_freeze (none expected; any deviation is
     reported there rather than by editing this sealed file)"

but the sealed ``results.json`` has no such key (``has("as_run_deviations_from_freeze") == false``).
The deviations are actually recorded in the standalone ``as_run_deviations.json`` written beside the
freeze, whose own statement explains why: the freeze is sealed and is not edited after the run, and
the sealed module does not emit a deviation field. So the pointer in the freeze is stale - it names
a location that has never existed, while the real record sits one file away.

Scope of the defect: it is a pointer/record defect, not a measurement defect. Nothing about the
verdict, the coverage accounting, the reconstruction finding or the analysed figures depends on it,
and the deviations themselves (B5-A1..A5) are complete and unmodified. The freeze is read-only to
this pass, so the pointer is NOT corrected in place; it is recorded here so a later reader who
follows the pointer finds the reason it is empty.

Recorded in the same entry, from the closeout seal sweep: after the basis freeze-verifiability
restoration the AUCTION ``run_inputs.json`` shows four drifted paths - ``M2/src/admission.py``
(``00363c3a...`` sealed against the restored ``9f5862f7...``), ``seal_freeze.py`` and
``test_auction_materiality.py`` (both re-pointed at the quarantined module), and
``M1/src/materialize.py``, whose drift is PRE-EXISTING and unrelated (the pipeline file changed
after the auction seal). The auction freeze was already invalidated as a preregistration by V3, so
these drifts retire a seal no live verdict depends on rather than invalidating a live one.

What this patch does NOT do: it changes no verdict, no gate and no candidate field, and it does not
touch the sealed freeze.
"""

from __future__ import annotations

PATCH_ID = "P-0015"
ACCESS = "2026-10-01"
AUCTION_SOURCE_LIMITATIONS = (
    "One session, one venue; the entry book is reconstructed from the retained window alone and "
    "cannot see orders added before 15:49:50, so the measured capture is a lower bound and the "
    "entry spread an upper bound; the freeze is INVALID as a preregistration because its sealed "
    "input already carried the Closing Cross exit price; the preregistered near/far band diagnostic "
    "is degenerate; 47.8% of the universe-qualified population is removed by the frozen N/O/P "
    "direction rule. Two record defects are additionally recorded. (1) The sealed freeze's "
    "'as_run_deviations_from_freeze' key points at 'results.json:as_run_deviations_from_freeze', a "
    "key that does not exist in results.json; the deviations are recorded in the standalone "
    "as_run_deviations.json beside the freeze, and the freeze was not edited to correct the pointer. "
    "(2) After the basis freeze-verifiability restoration the AUCTION run_inputs.json shows four "
    "drifted paths - M2/src/admission.py (sealed 00363c3a..., restored to the basis-sealed "
    "9f5862f7...), seal_freeze.py and test_auction_materiality.py (re-pointed at the quarantined "
    "M2/src/admission_auction.py), and M1/src/materialize.py (pre-existing drift, unrelated to the "
    "repair) - so the seal must be read as historical, not as a live verification."
)


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0018-NASDAQ", "UNK-0027-AUCTION"],
        "candidate_ids": ["TUP-NASDAQ-CLOSE-H4-LATENOII-AGG"],
        "new_sources": [],
        "new_evidence": [],
        "modified_claims": [
            {
                "claim": "The AUCTION freeze's pointer to its as-run deviation record resolves.",
                "status": "CORRECTED",
                "reason": "V3, re-confirmed in the closeout pass: freeze.json says the deviations are "
                          "'recorded in results.json:as_run_deviations_from_freeze', but results.json "
                          "has no such key. The actual record is the standalone as_run_deviations.json "
                          "beside the freeze (B5-A1..A5, complete and unmodified), which states why "
                          "it was written there rather than inside results.json. Recorded on SRC-0248 "
                          "as an artefact defect; the sealed freeze is read-only and is not corrected "
                          "in place, and no verdict, gate or figure depends on the pointer.",
            },
            {
                "claim": "The AUCTION run_inputs.json verifies as a live seal of the tree.",
                "status": "CORRECTED",
                "reason": "Four of its recorded paths drift. Three are the intended consequence of "
                          "the basis freeze-verifiability restoration (M2/src/admission.py restored "
                          "to the value the BASIS seal recorded; seal_freeze.py and "
                          "test_auction_materiality.py re-pointed at the quarantined "
                          "M2/src/admission_auction.py); one, M1/src/materialize.py, was already "
                          "drifted before the repair because the pipeline file changed after the "
                          "auction seal. The freeze was already invalidated as a preregistration by "
                          "V3, so no live verdict depends on it; the record is corrected to read as "
                          "historical rather than to imply a verifying seal.",
            },
        ],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "proposed_source_updates": [{
            "source_id": "SRC-0248",
            "fields": {"limitations": AUCTION_SOURCE_LIMITATIONS},
            "reason": "V3's artefact defect and the closeout seal sweep must be visible on the "
                      "source that holds this branch's record: the freeze's deviation pointer names "
                      "a results.json key that does not exist, and four paths of the AUCTION "
                      "run_inputs.json now drift, three of them as the intended consequence of the "
                      "basis restore. Every pre-existing limitation is carried through unchanged.",
        }],
        "decision": "NO_CHANGE",
        "reason": "A record-correction entry, not a verdict: the AUCTION freeze's pointer to its "
                  "as-run deviations names a results.json key that has never existed, the real "
                  "record being the standalone as_run_deviations.json, and the closeout seal sweep "
                  "shows four drifted paths in the AUCTION run_inputs.json. The auction branch was "
                  "already invalidated as a preregistration and recorded as INDETERMINATE, so "
                  "nothing is killed, nothing survives, no gate moves and the parent auction row is "
                  "untouched. The sealed freeze is read-only to this pass and is not edited; the "
                  "defect and the drifts are recorded on SRC-0248 so a later reader following the "
                  "pointer finds the reason it is empty.",
        "verification_notes": "Contrary readings were searched for. The pointer defect was checked "
                              "against the artefact rather than reported second-hand: "
                              "results.json has no 'as_run_deviations_from_freeze' key while "
                              "freeze.json contains the string naming it, and the standalone "
                              "as_run_deviations.json is present, complete (B5-A1..A5) and "
                              "unmodified. The tempting over-reading - that a stale pointer "
                              "invalidates the deviation record itself, and with it the branch's "
                              "already-shaky preregistration - was rejected: the deviations are "
                              "recorded in full one file away, and the freeze's "
                              "invalidated-preregistration status was established independently by "
                              "V3 from the sealed input's contents, not from this pointer. The four "
                              "drifted paths are enumerated with their causes rather than "
                              "summarised, including the one (M1/src/materialize.py) that this "
                              "pass did not cause; the pipeline rule is left unchanged. No sealed "
                              "artefact was written and no verdict was altered.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
