"""Code-authored evidence patch P-0014: the basis freeze-verifiability restoration.

Provenance: the project's own closeout repair, performed in epoch 6 and receipted at
`.research/m2_bridge_001/epoch6/W9_REPORT.md`. No sealed artefact was written.

The defect (V3, recorded on EVD-0072 limitation (iii) and SRC-0247): `M2/src/admission.py` is a
sealed input of the basis freeze, but the unrelated auction branch had added its v2 contract, two
contract-scoped checks and an `extra_checks` hook to that shared module AFTER the basis seal, so the
module on disk hashed ``00363c3a...`` against the sealed ``9f5862f7...`` and the basis freeze no
longer verified in place. V3 established the change was inert for the result (the gross reproduces
independently from the panel and the raw archives), but an unverifiable freeze is an
integrity-of-record failure regardless of whether the number moves.

The repair:

| file | change | sha256 before | sha256 after |
|---|---|---|---|
| `M2/src/admission.py` | restored byte-exactly | ``00363c3a...`` | ``9f5862f7...`` (the sealed value) |
| `M2/src/admission_auction.py` | NEW - the auction v2 contract, its two checks and the hook, moved verbatim; shared primitives imported, never copied | (absent) | ``84fd3270cc382248b6e57bd8111abc2fdb37f546150ea9f043df83fd47110caf`` |
| `M2/tests/test_auction_materiality.py` | v2 consumers re-pointed at the new module | ``940c5b61...`` | ``b08e79459cb780b412620364757049ffa615dd47567914ebed73b6e67f567675`` |
| `M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/seal_freeze.py` | new module added; recorded command re-pointed | ``813a1612...`` | ``e4e6e024f689a5c79fc16c9a44ab81c176141f2d191acfde0621adfe35dd9eb8`` |

Consequence, stated rather than hidden: the AUCTION seal was written while the drifted bytes were on
disk, so it recorded ``00363c3a...`` for `M2/src/admission.py`. Restoring the file makes the AUCTION
`run_inputs.json` drift in the OPPOSITE direction for that path, and the two consumer re-points drift
their own recorded hashes as well - one file cannot hash to two values, and the basis seal is the
one whose contract is still live. The auction branch was already invalidated by V3 (its freeze is an
INVALIDATED_FREEZE), so no live verdict depends on its seal verifying; until a re-seal (not
performed - sealed artefacts are read-only to the closeout pass) the AUCTION `run_inputs.json` is
historical, not a live verification.

Also recorded here from the same sweep: `M1/src/materialize.py`, sealed by the AUCTION experiment at
``bdec4cc1...``, hashes ``ad1d18d2...`` on the tree. That drift is PRE-EXISTING and unrelated to
this repair - the file was last changed by the epoch-6 canonical-application commit, after the
auction seal - and `materialize.py` is a pipeline rule, deliberately left unchanged.

What this patch does NOT do: it changes no verdict, no gate and no candidate field. The basis kill
stands exactly as recorded; the restoration only makes its frozen contract verifiable again.
"""

from __future__ import annotations

PATCH_ID = "P-0014"
ACCESS = "2026-10-01"
RESTORED_ADMISSION_SHA = "9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477"
DRIFTED_ADMISSION_SHA = "00363c3ac7e76366196581a254cb2b4baae73fcdeb69335da493d0b26f764c60"
AUCTION_MODULE = "M2/src/admission_auction.py"
AUCTION_MODULE_SHA = "84fd3270cc382248b6e57bd8111abc2fdb37f546150ea9f043df83fd47110caf"
BASIS_SOURCE_LIMITATIONS = (
    "One unconditional one-hour formulation on one development-grade panel; the 84 unresolved "
    "Binance settlements contribute exactly zero to the measured series and are bracketed only in "
    "the decision quantity; the Binance all-leg cost is UNKNOWN and unbounded, so the true C* is "
    "more negative than reported; pre-outcome sealing is asserted by artifact ordering only. The "
    "freeze's recorded hash for M2/src/admission.py (9f5862f7...) matches the tree again: the "
    "closeout pass restored the sealed module byte-exactly and moved the unrelated auction v2 "
    "contract to M2/src/admission_auction.py (84fd3270...), so this freeze now verifies in place "
    "and the drift limitation recorded on EVD-0072 (iii) is superseded. The same restore makes the "
    "(already invalidated) AUCTION seal drift in the opposite direction for admission.py, together "
    "with the two auction consumers that had to be re-pointed - stated on SRC-0248."
)


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0010", "UNK-0018-HYPERLIQUID"],
        "candidate_ids": ["TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX"],
        "new_sources": [{
            "source_id": "SRC-0250",
            "title": "M2-BRIDGE-HL-BINANCE-BASIS freeze-verifiability restoration - byte-exact "
                     "restore of the sealed admission module and quarantine of the auction v2 "
                     "contract",
            "authors_or_org": "This project (GOAL-M2-BRIDGE-001, epoch-6 closeout pass)",
            "publication_date": "2026-10-01",
            "access_date": ACCESS,
            "date_basis": "repair performed 2026-10-01 and receipted at "
                          ".research/m2_bridge_001/epoch6/W9_REPORT.md; the restored module "
                          "M2/src/admission.py hashes 9f5862f7... (the value the basis freeze "
                          "sealed) and the quarantined module M2/src/admission_auction.py hashes "
                          "84fd3270...",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "crypto perpetual futures (the basis panel whose seal was at issue)",
            "venue": "Hyperliquid Core BTC perpetual (short leg) against Binance USD(S)-M BTCUSDT "
                     "perpetual (long leg)",
            "sample_period": "not a sample period: a code-integrity repair over the basis "
                             "experiment's sealed hash set, whose measured panel is "
                             "2026-03-05T11:00:00Z-2026-09-28T23:00:00Z",
            "sample_size": "155 recorded code/input hashes in the basis run_inputs.json, all "
                           "verifying after the restore; one module restored byte-exactly and one "
                           "addition quarantined into a new module",
            "methodology": "M2/src/admission.py was restored byte-exactly from the sealed revision "
                           "and the auction v2 contract, its two contract-scoped checks and its "
                           "extra_checks hook were moved verbatim into M2/src/admission_auction.py "
                           "behind the engine's existing checks seam (shared primitives imported, "
                           "never copied). Verified by the basis materiality CLI's own --check "
                           "(freeze_sha256_matches, code_unchanged and inputs_unchanged all true, "
                           "no drifted inputs), by a full re-hash sweep of every recorded path of "
                           "all three bridge run_inputs.json files, by the 40-test auction suite "
                           "and by the full M2 suite (332 tests), and by re-pointing the auction "
                           "admission CLI and reproducing the sealed admission_v2_result.json "
                           "exactly (DATA_VALID, no findings).",
            "gross_or_net": "Not applicable: a freeze-verifiability repair produces no gross or "
                            "net figure and changes no measured quantity",
            "independent_replication": "The checks above were run against the tree, independently "
                                       "of the patch that records them; the auction CLI's output "
                                       "was canonicalised and diffed against the sealed "
                                       "admission_v2_result.json rather than compared by eye",
            "limitations": "Infrastructure repair, not economic evidence: it changes no number and "
                           "the basis kill stands exactly as recorded. It is not a re-seal - the "
                           "AUCTION sealed artefacts are read-only to the closeout pass, so the "
                           "AUCTION run_inputs.json remains historical and drifted for four paths "
                           "until a future freeze. One of those four, M1/src/materialize.py, is "
                           "pre-existing drift unrelated to this repair (the pipeline file changed "
                           "after the auction seal) and the pipeline rule is deliberately left "
                           "unchanged.",
            "raw_citation_token": "code:P-0014",
            "local_path": AUCTION_MODULE,
            "sha256": AUCTION_MODULE_SHA,
            "status": "PARTIAL",
            "claim_scope": "Integrity of record: the basis freeze's sealed module is restored "
                           "byte-exactly and the unrelated auction addition is quarantined, with "
                           "the opposite-direction consequence on the already-invalidated AUCTION "
                           "seal recorded rather than hidden.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0075",
            "claim": "The basis measurement's frozen contract verifies in place again. Its sealed "
                     "input M2/src/admission.py, recorded at "
                     "9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477, had drifted "
                     "to 00363c3ac7e76366196581a254cb2b4baae73fcdeb69335da493d0b26f764c60 because "
                     "an unrelated branch added the auction v2 contract, two contract-scoped checks "
                     "and an extra_checks hook to that shared module after the basis seal. The "
                     "closeout pass restored the sealed module byte-exactly and moved the auction "
                     "addition verbatim to M2/src/admission_auction.py "
                     "(84fd3270cc382248b6e57bd8111abc2fdb37f546150ea9f043df83fd47110caf), which "
                     "imports the shared primitives from M2.src.admission and re-registers "
                     "AUCTION_V2 on import; the engine file itself is byte-identical to the freeze, "
                     "so the basis freeze now verifies in place (code_unchanged true, no drifted "
                     "inputs) and the 40-test auction suite stays green. Stated consequence: the "
                     "AUCTION seal recorded the drifted bytes (00363c3a...), so it now drifts in the "
                     "OPPOSITE direction for admission.py, together with the two consumer files "
                     "that had to be re-pointed at the new module; this is unavoidable (one file "
                     "cannot hash to two values) and inert for the campaign because the auction "
                     "branch's freeze was already invalidated as a preregistration by V3. No "
                     "verdict, gate or candidate field changes.",
            "source_id": "SRC-0250",
            "candidate_ids": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
            "mechanism_id": "MECH-FUNDBASIS",
            "venue_id": "VEN-HYPERLIQUID-BTCPERP",
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "NEUTRAL",
            "methodology": "Integrity repair with a receipt: M2/src/admission.py was restored "
                           "byte-exactly from the sealed revision and the auction addition moved "
                           "verbatim into its own module behind the engine's existing checks "
                           "seam. Verified by re-hashing every recorded path of the basis "
                           "run_inputs.json (155/155 verify, including the restored module), by "
                           "the basis materiality CLI's own --check (freeze_sha256_matches true, "
                           "code_unchanged true, inputs_unchanged true, no drifted inputs), by the "
                           "40-test auction suite and by the full M2 suite (332 tests) - all run in "
                           "the closeout pass and receipted at "
                           ".research/m2_bridge_001/epoch6/W9_REPORT.md. A sealed-hash sweep "
                           "across all three bridge records shows exactly four remaining drifted "
                           "paths, all four inside the AUCTION seal.",
            "sample": "3 bridge experiments x their recorded code/input hash sets: AUCTION 22 entries "
                      "with 4 drifted after the repair, ES 13/13 verify, BASIS 155/155 verify",
            "temporal_scope": "repair performed 2026-10-01; the measured basis panel itself is "
                              "2026-03-05T11:00:00Z-2026-09-28T23:00:00Z",
            "gross_or_net": "Not applicable: a freeze-verifiability repair changes no measured "
                            "quantity, and no gross or net figure is produced or altered by it",
            "limitations": "(a) It is an infrastructure repair, not new economic evidence: it "
                           "changes no number, and the basis kill stands exactly as recorded. (b) "
                           "It is not a re-seal: the AUCTION sealed artefacts are read-only to the "
                           "closeout pass, so the AUCTION run_inputs.json remains historical and "
                           "drifted for four paths until a future freeze. (c) One of those four "
                           "drifted paths, M1/src/materialize.py, is PRE-EXISTING and unrelated to "
                           "this repair - the pipeline file changed after the auction seal - and "
                           "the pipeline rule is deliberately left unchanged.",
            "decision_implication": "No decision changes: the basis candidate stays DEAD on the "
                                    "recorded KILL_MATERIALITY with its resurrection condition. The "
                                    "repair restores the property the campaign's frozen-record "
                                    "doctrine requires - a sealed contract that verifies in place "
                                    "- without touching any result.",
            "contradicts_mechanism": "NO",
            "observed_market": "crypto perpetual futures",
            "observed_venue": "VEN-HYPERLIQUID-BTCPERP",
            "observed_instrument_or_universe": "Hyperliquid Core BTC perpetual against Binance "
                                               "USD(S)-M BTCUSDT perpetual",
            "observed_period": "2026-03-05..2026-09-28",
            "observed_horizon": "H4 (one-hour hold, unconditional)",
            "candidate_link_reason": "The restored module is a direct sealed input of this "
                                     "candidate's own frozen measurement, and the repair exists so "
                                     "that measurement's contract can be verified from the tree "
                                     "rather than taken on trust.",
            "transfer_status": "DIRECT",
            "verification_status": "VERIFIED_BY_INDEPENDENT_REHASH_AND_FULL_SUITE",
        }],
        "modified_claims": [
            {
                "claim": "The basis freeze no longer verifies in place because M2/src/admission.py "
                         "drifted after the seal.",
                "status": "CORRECTED",
                "reason": "Recorded as EVD-0072 limitation (iii) and on SRC-0247. The closeout "
                          "repair restored the sealed module byte-exactly (9f5862f7...) and moved "
                          "the unrelated auction addition to M2/src/admission_auction.py, so the "
                          "basis freeze verifies in place again and the limitation is superseded "
                          "(EVD-0075). The stale text is left on EVD-0072 because evidence rows "
                          "are append-only in this corpus; the correction is recorded rather than "
                          "the row rewritten.",
            },
        ],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "new_unknowns": [],
        "proposed_source_updates": [{
            "source_id": "SRC-0247",
            "fields": {"limitations": BASIS_SOURCE_LIMITATIONS},
            "reason": "EVD-0075: the source's limitations must stop asserting drift that the "
                      "closeout repair removed. The replacement records that the freeze verifies "
                      "in place again, names the quarantined module, and points at the "
                      "opposite-direction consequence recorded on SRC-0248; every other "
                      "limitation is carried through unchanged.",
        }],
        "decision": "NO_CHANGE",
        "reason": "An integrity-of-record repair, not a verdict: the basis freeze's sealed module "
                  "was restored byte-exactly so the contract verifies in place, with the unrelated "
                  "auction contract quarantined into its own module behind the engine's existing "
                  "checks seam. The measured gross, the fired clause, the C0 floor, the "
                  "sign-robustness controls and the DEAD status are all untouched, and the honest "
                  "consequence - the already-invalidated AUCTION seal now drifts in the opposite "
                  "direction - is recorded rather than hidden.",
        "verification_notes": "Contrary evidence and self-serving readings were searched for before "
                              "the repair was recorded. The strongest counter-argument - that "
                              "restoring the module merely moves the unverifiability to another "
                              "seal, so nothing is gained - was tested and rejected on two grounds: "
                              "the basis contract is live while the auction branch's freeze is "
                              "already INVALIDATED_FREEZE, and the restored module makes the "
                              "sealed-admission semantics of the ENGINE byte-exact again, which is "
                              "the property the campaign's frozen-record doctrine requires. The "
                              "moved auction code was verified to be character-for-character the "
                              "block that lived in the engine (same check ids, severities and "
                              "order) and the re-pointed CLI reproduces the sealed "
                              "admission_v2_result.json (DATA_VALID, no findings) exactly, so the "
                              "repair is behaviour-preserving rather than a silent redefinition. "
                              "The remaining drift is enumerated in full, including the one path "
                              "(M1/src/materialize.py) that this pass did not cause and did not "
                              "touch. No sealed artefact was modified and no number was adjusted.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
