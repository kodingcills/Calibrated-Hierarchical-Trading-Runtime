"""Code-authored evidence patch P-0016: the three record defects verification wave V4 found.

Provenance: verification wave V4, `.research/m2_bridge_001/verification/V4/REPORT.md` §5.1-§5.3,
closed out by worker W11 in epoch 6 and receipted at
`.research/m2_bridge_001/epoch6/W11_REPORT.md`. No sealed artefact was written, no candidate
field, gate, count or verdict moves, and no superseded statement is deleted.

Three defects, all of them in this campaign's own record rather than in a measurement:

1. Misattributed drift (V4 §5.2, CONTESTED). EVD-0075 limitation (c) called the
   ``M1/src/materialize.py`` drift "PRE-EXISTING and unrelated to this repair - the pipeline file
   changed after the auction seal", which reads as an earlier pass outside this campaign. Git says
   otherwise: the AUCTION seal recorded ``bdec4cc1...``, that value still held at
   ``ba3705a``/``7b76e9f``/``c8fd95d``, and the file became ``ad1d18d2...`` in ``e64acb6``
   (2026-10-01T02:29:43-04:00) - this campaign's own canonical-application commit, the one that
   recorded the three M2-bridge branch verdicts, seven hours after the auction seal. The drift
   count (four) and both hash values are exact and are NOT changed; only the attribution was
   wrong. W9's repair did not touch the file, and that narrower fact is what remains true.

2. Stale present tense (V4 §5.1, SUPPORTED_SCOPED). EVD-0072 limitation (iii) states that the
   basis freeze "no longer verifies in place". That was true when written and is false now: W9
   restored the sealed module (P-0014, SRC-0250), ``M2/src/basis_materiality.py --check`` reports
   ``freeze_sha256_matches``/``code_unchanged``/``inputs_unchanged`` true with no drifted inputs,
   and all 155 recorded entries of the basis ``run_inputs.json`` resolve. P-0014 recorded the
   supersession on EVD-0075 and SRC-0247 but left the evidence row itself untouched (evidence rows
   are append-only in this corpus), so a reader of EVD-0072 (iii) alone still concluded the seal
   was broken. The row now carries the correction.

3. Pre-existing generator contradiction (V4 §5.3, observation; secondary finding).
   ``M1/output/status_derivation_review.csv`` reports ``ceiling_permits_status = NO`` for both
   bridge kills while the same artifact family reports ``ceiling_violations = 0``. V4 established
   the contradiction is systemic to every ``RECORDED_DECISION`` kill, is caused by none of this
   campaign's work, and is consumed by no rule or decision. It is registered as UNK-0036 rather
   than fixed: ``materialize._ceiling_ok`` and ``candidate_gates.ceiling_violations`` disagree in
   letter on purpose, and deciding which of them is right is a decision, not a row edit.

How the corrections are carried, append-only. This patch appends to the two evidence rows'
limitations through ``proposed_evidence_updates``, a section whose only expressible operation is
an append: the original text stays where it was written and the correction that names it follows
in the same cell. The corrections are also recorded as citable evidence (EVD-0076), a source
(SRC-0251) and three ``modified_claims`` entries, and the two source-registry limitations that
repeat the wrong attribution are brought into line by carrying every prior clause through and
naming what was corrected.

What this patch does NOT do: it changes no verdict, gate, status or count, it touches no sealed
artefact, it leaves the ``status_derivation_review`` generator's semantics exactly as they were,
and it deletes nothing.
"""

from __future__ import annotations

PATCH_ID = "P-0016"
ACCESS = "2026-10-01"

# The AUCTION seal's recorded value for the pipeline file, the value it holds on the tree, and the
# commit that produced the change. Both hashes are re-verified from the repository in this pass.
DRIFT_SEALED_SHA = "bdec4cc1ef1821a83210a646e041113b6fb6cdab75cb48d4de17d95fb971a08c"
DRIFT_TREE_SHA = "ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0"
DRIFT_COMMIT = "e64acb6"
DRIFT_COMMIT_TIME = "2026-10-01T02:29:43-04:00"
DRIFT_PRIOR_COMMITS = "ba3705a, 7b76e9f, c8fd95d"
RESTORED_ADMISSION_SHA = "9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477"

EVD_0072_AMENDMENT = (
    "[CORRECTED 2026-10-01, patch P-0016: limitation (iii) above was true when it was written and "
    "is false now. The W9 restoration (patch P-0014, SRC-0250, EVD-0075) put the sealed module back "
    f"at {RESTORED_ADMISSION_SHA}, and the basis freeze verifies in place again: "
    "M2/src/basis_materiality.py --check reports freeze_sha256_matches, code_unchanged and "
    "inputs_unchanged all true with no drifted inputs, and every one of the 155 recorded code/input "
    "entries of the basis run_inputs.json resolves (re-verified 2026-10-01). The superseding record "
    "is EVD-0075 with SRC-0250 and P-0014; limitation (iii) is retained verbatim above as the "
    "record of what was true when it was written.]"
)

EVD_0075_AMENDMENT = (
    "[CORRECTED 2026-10-01, patch P-0016: the words 'PRE-EXISTING and unrelated' above give the "
    "wrong attribution; the drift count (four) and both hash values are correct and unchanged. Git "
    f"shows M1/src/materialize.py at {DRIFT_SEALED_SHA} through {DRIFT_PRIOR_COMMITS}, and at "
    f"{DRIFT_TREE_SHA} from {DRIFT_COMMIT} ({DRIFT_COMMIT_TIME}) onward - this campaign's own "
    "canonical-application commit, which recorded the three M2-bridge branch verdicts, seven hours "
    "after the auction seal. The drift is therefore this campaign's own and not an earlier "
    "unrelated pass; what remains true is the narrower fact that W9's repair did not touch the "
    "file, and that the pipeline rule is deliberately left unchanged. Recorded on SRC-0251, "
    "EVD-0076 and in this patch's modified_claims.]"
)

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
    "with the two auction consumers that had to be re-pointed - stated on SRC-0248. [P-0016: the "
    "superseded limitation is now corrected in its own row as well - EVD-0072 (iii) carries the "
    "cross-reference to EVD-0075 / SRC-0250 / P-0014, appended, with the original text kept.]"
)

AUCTION_SOURCE_LIMITATIONS = (
    "One session, one venue; the entry book is reconstructed from the retained window alone and "
    "cannot see orders added before 15:49:50, so the measured capture is a lower bound and the "
    "entry spread an upper bound; the freeze is INVALID as a preregistration because its sealed "
    "input already carried the Closing Cross exit price; the preregistered near/far band "
    "diagnostic is degenerate; 47.8% of the universe-qualified population is removed by the frozen "
    "N/O/P direction rule. Two record defects are additionally recorded. (1) The sealed freeze's "
    "'as_run_deviations_from_freeze' key points at 'results.json:as_run_deviations_from_freeze', a "
    "key that does not exist in results.json; the deviations are recorded in the standalone "
    "as_run_deviations.json beside the freeze, and the freeze was not edited to correct the "
    "pointer. (2) After the basis freeze-verifiability restoration the AUCTION run_inputs.json "
    "shows four drifted paths - M2/src/admission.py (sealed 00363c3a..., restored to the "
    "basis-sealed 9f5862f7...), seal_freeze.py and test_auction_materiality.py (re-pointed at the "
    "quarantined M2/src/admission_auction.py), and M1/src/materialize.py (pre-existing drift, "
    "unrelated to the repair) - so the seal must be read as historical, not as a live "
    "verification. [CORRECTED 2026-10-01, P-0016: the words in (2) that describe "
    "M1/src/materialize.py understate this campaign's own footprint. That path was changed by this "
    f"campaign's own canonical-application commit {DRIFT_COMMIT} ({DRIFT_COMMIT_TIME}), not by an "
    f"earlier unrelated pass; the sealed value ({DRIFT_SEALED_SHA[:8]}...) and the tree value "
    f"({DRIFT_TREE_SHA[:8]}...) are unchanged and the count (four) is unchanged. See SRC-0251, "
    "EVD-0076 and P-0016's modified_claims.]"
)

BASIS_RESTORE_SOURCE_LIMITATIONS = (
    "Infrastructure repair, not economic evidence: it changes no number and the basis kill stands "
    "exactly as recorded. It is not a re-seal - the AUCTION sealed artefacts are read-only to the "
    "closeout pass, so the AUCTION run_inputs.json remains historical and drifted for four paths "
    "until a future freeze. One of those four, M1/src/materialize.py, is pre-existing drift "
    "unrelated to this repair (the pipeline file changed after the auction seal) and the pipeline "
    "rule is deliberately left unchanged. [CORRECTED 2026-10-01, P-0016: that path's drift is this "
    f"campaign's own - M1/src/materialize.py changed to {DRIFT_TREE_SHA[:8]}... in {DRIFT_COMMIT} "
    f"({DRIFT_COMMIT_TIME}), this campaign's canonical-application commit, seven hours after the "
    "auction seal - so it is 'pre-existing' only relative to this repair, not to the campaign. The "
    f"sealed value {DRIFT_SEALED_SHA[:8]}..., the tree value {DRIFT_TREE_SHA[:8]}... and the count "
    "of four drifted paths are unchanged. See SRC-0251 and EVD-0076.]"
)


def build(created_at):
    return {
        "patch_id": PATCH_ID,
        "blocker_ids": ["UNK-0027-AUCTION", "UNK-0018-HYPERLIQUID"],
        "candidate_ids": ["TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX",
                          "TUP-NASDAQ-CLOSE-H4-LATENOII-AGG"],
        "new_sources": [{
            "source_id": "SRC-0251",
            "title": "Record corrections W11 - the M1/src/materialize.py drift attribution, the "
                     "EVD-0072 (iii) supersession and the status_derivation_review ceiling flag",
            "authors_or_org": "This project (GOAL-M2-BRIDGE-001, epoch-6 closeout pass, worker W11)",
            "publication_date": "2026-10-01",
            "access_date": ACCESS,
            "date_basis": "established 2026-10-01 from this repository's own history: git log/git "
                          "show over M1/src/materialize.py (the file hashes "
                          "bdec4cc1ef1821a83210a646e041113b6fb6cdab75cb48d4de17d95fb971a08c at "
                          "ba3705a/7b76e9f/c8fd95d and "
                          "ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0 from "
                          "e64acb6, 2026-10-01T02:29:43-04:00), a re-hash sweep of the three bridge "
                          "run_inputs.json hash sets (AUCTION 18/22 verify, 4 drift; ES 13/13; "
                          "BASIS 155/155), and M2/src/basis_materiality.py --check "
                          "(freeze_sha256_matches, code_unchanged and inputs_unchanged all true, "
                          "no drifted inputs), after verification wave V4 recorded the three "
                          "defects at .research/m2_bridge_001/verification/V4/REPORT.md "
                          "sections 5.1-5.3",
            "url": None,
            "doi": None,
            "source_type": "internal_measurement",
            "primary_or_secondary": "primary_own_measurement",
            "market": "not applicable: a record-correction source over this repository's own "
                      "artifacts and history; the artifacts it corrects concern crypto perpetual "
                      "futures (Hyperliquid Core BTC perpetual against Binance USD(S)-M BTCUSDT "
                      "perpetual) and US equities (Nasdaq closing cross)",
            "venue": "not applicable: repository record rather than a venue observation; the "
                     "corrected artifacts are the AUCTION and BASIS frozen-run records and the M1 "
                     "generated review tables",
            "sample_period": "not a sample period: the git history of M1/src/materialize.py "
                             "(ba3705a..HEAD) and the three bridge run_inputs.json hash sets, both "
                             "read on 2026-10-01",
            "sample_size": "1 file's git history over 4 commits; 190 recorded code/input hashes "
                           "re-checked (22 AUCTION + 13 ES + 155 BASIS); 2 evidence-row "
                           "limitations appended to; 3 source-registry limitations brought into "
                           "line; 1 discrepancy registered (UNK-0036)",
            "methodology": "Each correction was re-established from the repository rather than "
                           "carried second-hand: the drift attribution from git log/git show and a "
                           "working-tree hash, the freeze restoration from the basis CLI's own "
                           "--check and a full re-hash sweep of the basis run_inputs.json, and the "
                           "ceiling-flag contradiction from the generated tables themselves "
                           "(status_derivation_review.csv against M1_STATE_SUMMARY.json's "
                           "ceiling_violations and against the two code paths that compute them, "
                           "materialize._ceiling_ok and candidate_gates.ceiling_violations). The "
                           "corrections are then recorded append-only: the two evidence rows carry "
                           "their original text plus the correction that names it, the source rows "
                           "carry every prior clause plus the correction, and the generator that "
                           "produces status_derivation_review.csv is left untouched.",
            "gross_or_net": "Not applicable: a record correction produces no gross or net figure "
                            "and changes no measured quantity",
            "independent_replication": "Re-derived in this pass from git and from the sealed hash "
                                       "sets, independently of the V4 report that found the "
                                       "defects: the AUCTION hash sweep was recomputed over the "
                                       "tree (18/22 verify, the four drifts enumerated with their "
                                       "causes), the basis freeze was re-checked by the sealed "
                                       "module's own CLI, and the two code paths behind the "
                                       "ceiling flag were read rather than inferred.",
            "limitations": "A record-correction source, not evidence about a market: it changes no "
                           "number, gate, status, count or verdict, and it leaves every superseded "
                           "statement in place with the correction appended after it. It cannot "
                           "settle UNK-0036 - that needs a decision about what "
                           "ceiling_permits_status is meant to assert, or a generator fix, and "
                           "neither is taken here. It also does not establish what the AUCTION seal "
                           "intended: the seal's own record does not say whether it meant the pre- "
                           "or the post-e64acb6 pipeline, only that it sealed one of them.",
            "raw_citation_token": "code:P-0016",
            "local_path": None,
            "sha256": None,
            "status": "PARTIAL",
            "claim_scope": "Record-level corrections to this campaign's own artifacts: the drift "
                           "attribution in EVD-0075 (c) is corrected, EVD-0072 (iii) is marked "
                           "superseded as of the W9 restoration with the original text kept, and "
                           "the status_derivation_review ceiling-flag contradiction is registered "
                           "as UNK-0036. No verdict, gate or candidate field is touched.",
        }],
        "new_evidence": [{
            "evidence_id": "EVD-0076",
            "claim": "Three record defects in this campaign's own records are corrected in place, "
                     "append-only, with the drift accounting unchanged. (1) The M1/src/materialize."
                     "py drift inside the AUCTION seal is this campaign's own: the file hashed "
                     "bdec4cc1ef1821a83210a646e041113b6fb6cdab75cb48d4de17d95fb971a08c at "
                     "ba3705a, 7b76e9f and c8fd95d, and "
                     "ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0 from "
                     "e64acb6 (2026-10-01T02:29:43-04:00), the canonical-application commit that "
                     "recorded the three M2-bridge branch verdicts, seven hours after the auction "
                     "seal - not an earlier unrelated pass, although W9's repair did not touch the "
                     "file. The drift count (four paths) and both hashes are unchanged. (2) EVD-0072 "
                     "limitation (iii) is superseded as of the W9 restoration: M2/src/admission.py "
                     "is back at the basis-sealed 9f5862f7... , the basis freeze verifies in place "
                     "(code_unchanged true, no drifted inputs) and all 155 recorded entries of the "
                     "basis run_inputs.json resolve. (3) M1/output/status_derivation_review.csv "
                     "reports ceiling_permits_status = NO for all five RECORDED_DECISION kills "
                     "while M1/output/M1_STATE_SUMMARY.json reports ceiling_violations = 0; the "
                     "contradiction is systemic to those rows, is consumed by no rule or decision, "
                     "and is registered as UNK-0036 rather than fixed.",
            "source_id": "SRC-0251",
            "candidate_ids": "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX|TUP-NASDAQ-CLOSE-H4-LATENOII-AGG",
            "mechanism_id": None,
            "venue_id": None,
            "epistemic_class": "SUPPORTED_FINDING",
            "evidence_origin": "PROJECT_ARITHMETIC",
            "supports_or_weakens": "NEUTRAL",
            "methodology": "Record correction established from the repository itself: git log/git "
                           "show over M1/src/materialize.py (its hash at e64acb6 and at that "
                           "commit's parent ba3705a, plus 7b76e9f and c8fd95d, against the "
                           "working-tree hash); a re-hash sweep of all three bridge "
                           "run_inputs.json hash sets (AUCTION 22 recorded -> 18 verify / 4 drift, "
                           "ES 13/13, BASIS 155/155); M2/src/basis_materiality.py --check (all "
                           "three integrity flags true, no drifted inputs); and a direct read of "
                           "the two code paths behind the ceiling flag (materialize._ceiling_ok "
                           "against candidate_gates.ceiling_violations). The two evidence rows are "
                           "amended by appending to their limitations, and the "
                           "status_derivation_review generator is left untouched.",
            "sample": "1 file's git history over 4 commits; 190 recorded code/input hashes "
                      "re-checked (22 + 13 + 155); 2 evidence-row limitations appended to; 3 "
                      "source-registry limitations brought into line; 1 issue registered",
            "temporal_scope": "corrections established 2026-10-01, the same day as the W9 repair "
                              "and the V4 verification wave; the attributed code change is dated "
                              "2026-10-01T02:29:43-04:00",
            "gross_or_net": "Not applicable: a record correction produces no gross or net figure "
                            "and changes no measured quantity",
            "limitations": "(a) It is a record correction, not evidence about a market: it changes "
                           "no number, gate, status or verdict. (b) It corrects statements by "
                           "appending to them, so the superseded wording stays in the row and the "
                           "row must be read to the end. (c) It does not resolve the "
                           "status_derivation_review contradiction it registers (UNK-0036): that "
                           "needs a decision about what the column asserts, or a generator fix, "
                           "and neither is taken here. (d) The attribution rests on git, not on a "
                           "sealed statement of intent: whether the AUCTION seal meant the pre- or "
                           "the post-e64acb6 pipeline is still not recorded.",
            "decision_implication": "No decision changes: both bridge kills stay DEAD on their "
                                    "recorded grounds with their resurrection conditions, and the "
                                    "AUCTION freeze stays an INVALIDATED_FREEZE whose recorded "
                                    "paths must be read as historical. The corrections remove two "
                                    "ways a reader of a canonical row alone could be misled, and "
                                    "register a third as an open, non-blocking discrepancy.",
            "contradicts_mechanism": "NO",
            "candidate_link_reason": "The corrections concern the record of these two bridge "
                                     "branches: EVD-0072 belongs to the basis measurement whose "
                                     "limitation (iii) is superseded, and the M1/src/materialize.py "
                                     "drift sits inside the AUCTION freeze whose recorded-path "
                                     "account is corrected.",
            "transfer_status": "DIRECT",
            "verification_status": "VERIFIED_FROM_GIT_HISTORY_AND_RESEAL_CHECK",
        }],
        "modified_claims": [
            {
                "claim": "The M1/src/materialize.py drift inside the AUCTION seal is pre-existing "
                         "and unrelated to this campaign.",
                "status": "CORRECTED",
                "reason": "V4 section 5.2, re-established from git in this pass: M1/src/materialize"
                          ".py hashed bdec4cc1ef1821a83210a646e041113b6fb6cdab75cb48d4de17d95fb97"
                          "1a08c at ba3705a, 7b76e9f and c8fd95d and "
                          "ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0 from "
                          "e64acb6 (2026-10-01T02:29:43-04:00) - this campaign's own "
                          "canonical-application commit, seven hours after the auction seal. The "
                          "drift count (four) and both hash values are unchanged and correct; only "
                          "the attribution was wrong. W9's repair did not touch the file, and that "
                          "narrower fact is preserved. The correction is appended to EVD-0075 (c) "
                          "and recorded on SRC-0250, SRC-0248, SRC-0251 and EVD-0076; the wrong "
                          "wording is not deleted.",
            },
            {
                "claim": "The basis freeze no longer verifies in place (EVD-0072 limitation (iii)).",
                "status": "CORRECTED",
                "reason": "V4 section 5.1: the limitation was true when written and is false after "
                          "the W9 restoration (P-0014, SRC-0250, EVD-0075). Re-verified in this "
                          "pass: M2/src/basis_materiality.py --check returns freeze_sha256_matches, "
                          "code_unchanged and inputs_unchanged true with no drifted inputs, and all "
                          "155 recorded entries of the basis run_inputs.json resolve. P-0014 "
                          "recorded the supersession beside the row, which left a reader of "
                          "EVD-0072 (iii) alone misled; the cross-reference to EVD-0075 / SRC-0250 "
                          "/ P-0014 is now appended to the row itself, with the original text "
                          "kept.",
            },
            {
                "claim": "ceiling_permits_status = NO on a RECORDED_DECISION kill means the kill "
                         "was not permitted by its status ceiling.",
                "status": "CORRECTED",
                "reason": "V4 section 5.3, re-read from the code in this pass: M1/output/"
                          "status_derivation_review.csv reports NO for the five RECORDED_DECISION "
                          "kills (including both bridge kills) while M1/output/M1_STATE_SUMMARY.json "
                          "reports ceiling_violations = 0 and validate.py --strict passes, because "
                          "materialize._ceiling_ok requires ceiling == DEAD for any DEAD row while "
                          "candidate_gates.ceiling_violations deliberately exempts a recorded "
                          "decision. The reading is corrected by registering the contradiction as "
                          "UNK-0036 (systemic to those rows, consumed by nothing, unresolved by a "
                          "decision about the column's meaning or a generator fix). The "
                          "contradiction predates this campaign and the generator is deliberately "
                          "left unchanged.",
            },
        ],
        "proposed_issue_updates": [],
        "proposed_candidate_updates": [],
        "proposed_gate_changes": [],
        "proposed_assumption_updates": [],
        "proposed_dead_end_updates": [],
        "proposed_evidence_updates": [
            {
                "evidence_id": "EVD-0072",
                "field": "limitations",
                "append": EVD_0072_AMENDMENT,
                "reason": "V4 section 5.1: a reader who opens only EVD-0072 (iii) concludes the "
                          "basis seal is broken, which stopped being true when W9 restored the "
                          "sealed module. The cross-reference must sit on the row that carries the "
                          "stale present tense, so it is appended to it rather than recorded only "
                          "beside it; the original limitation stays in place, unedited.",
            },
            {
                "evidence_id": "EVD-0075",
                "field": "limitations",
                "append": EVD_0075_AMENDMENT,
                "reason": "V4 section 5.2: limitation (c) attributes the M1/src/materialize.py "
                          "drift to an earlier unrelated pass when git shows this campaign's own "
                          "canonical-application commit e64acb6 changed the file. Appended so the "
                          "misattributed sentence is corrected where it stands and the count and "
                          "both hashes stay exactly as recorded.",
            },
        ],
        "new_unknowns": [{
            "issue_id": "UNK-0036",
            "claim_needed": "What M1/output/status_derivation_review.csv's "
                            "ceiling_permits_status column is meant to assert, and whether the "
                            "column or the ceiling rule it is read against is the record that is "
                            "wrong.",
            "known_evidence": "M1/output/status_derivation_review.csv reports "
                              "ceiling_permits_status = NO for five rows - TUP-CME-ES-H3-OFI-AGG "
                              "and TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX (both DEAD under a "
                              "NOT_ALIVE ceiling on this campaign's recorded kills) and the three "
                              "pre-existing M2 RECORDED_DECISION kills "
                              "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG, TUP-NASDAQ-LARGETICK-H2-QIMB-PAS "
                              "and TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG - while the same artifact "
                              "family reports ceiling_violations = 0 in "
                              "M1/output/M1_STATE_SUMMARY.json and M1/src/validate.py --strict "
                              "passes (19 checks, 0 failures). V4 established from the code that "
                              "the pattern is systemic to RECORDED_DECISION kills and predates "
                              "this campaign: materialize._ceiling_ok requires ceiling == DEAD for "
                              "any DEAD row, while candidate_gates.ceiling_violations deliberately "
                              "exempts a death recorded as a decision with cause and resurrection "
                              "condition. Nothing consumes the column: no gate, count, verdict or "
                              "frontier item reads it, and the validator does not enforce it.",
            "specific_evidence_needed": "A decision about what the column asserts - if a NOT_ALIVE "
                                        "ceiling means 'the ceiling forbids ALIVE', the column is "
                                        "right and only its label invites a false reading; if it "
                                        "means 'the ceiling permits the recorded status', the "
                                        "column is wrong for a recorded kill - or a generator "
                                        "change to M1/src/materialize.py:_ceiling_ok that exempts "
                                        "recorded kills the way candidate_gates.ceiling_violations "
                                        "already does. Neither is taken by P-0016.",
            "decision_prevented": "Nothing. The contradiction blocks no gate, kills no candidate "
                                  "and prevents no decision; it is recorded because the column's "
                                  "letter disagrees with the rule the validator enforces and "
                                  "invites the reading that these kills were not permitted.",
            "severity": "NON_BLOCKING",
            "resolution_method": "HUMAN_INPUT",
            "resolution_stage": "NON_BLOCKING",
            "tier": 1,
            "branch_impact": "GLOBAL",
            "kill_potential": "LOW",
            "estimated_effort": "SMALL",
            "migration_reason": "Registered by patch P-0016 as a record discrepancy between two of "
                                "the campaign's own artifacts, not as work that gates a candidate: "
                                "nothing consumes the field and the generator's semantics are "
                                "deliberately left unchanged.",
            "conflict_type": "CONTRADICTION",
            "exact_conflict": "M1/output/status_derivation_review.csv reports "
                              "ceiling_permits_status = NO for TUP-CME-ES-H3-OFI-AGG and "
                              "TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX, while "
                              "M1/output/M1_STATE_SUMMARY.json reports ceiling_violations = 0 for "
                              "the same corpus and validate.py --strict passes.",
            "suspected_reason": "Two definitions of 'the ceiling permits'. materialize._ceiling_ok "
                                "requires ceiling == DEAD for every DEAD row; "
                                "candidate_gates.ceiling_violations exempts a candidate whose death "
                                "is a recorded decision (candidate_gates.ceiling_violations docstring: "
                                "those rows may be DEAD without a FAIL gate). Both are intentional; "
                                "only their letters disagree.",
            "search_attempts": "Read directly from the generated tables and from both code paths in "
                               "verification wave V4 and again in this pass; no further search is "
                               "needed to state the contradiction, only a decision to settle it.",
            "web_research_resolvable": "NO",
            "requires_vendor_quote": "NO",
            "requires_m2_measurement": "NO",
            "can_M2_measure": "NO",
            "resolution_class": "D",
            "evidence_ids": "EVD-0076",
            "source_A": "SRC-0251",
            "affected_candidate_ids":
                "TUP-CME-ES-H3-OFI-AGG|TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX|"
                "TUP-NASDAQ-LARGETICK-H2-QIMB-AGG|TUP-NASDAQ-LARGETICK-H2-QIMB-PAS|"
                "TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG",
        }],
        "proposed_source_updates": [
            {
                "source_id": "SRC-0247",
                "fields": {"limitations": BASIS_SOURCE_LIMITATIONS},
                "reason": "P-0016: the basis source must point at the in-row correction of its own "
                          "superseded limitation, so a reader who follows EVD-0072 (iii) to its "
                          "source is not sent back to text that only records the supersession "
                          "elsewhere. Every prior clause is carried through unchanged.",
            },
            {
                "source_id": "SRC-0248",
                "fields": {"limitations": AUCTION_SOURCE_LIMITATIONS},
                "reason": "P-0016: this source repeats the misattribution ('M1/src/materialize.py "
                          "(pre-existing drift, unrelated to the repair)'). The clause is kept and "
                          "the corrected attribution is appended after it, naming the campaign's "
                          "own commit e64acb6 and leaving the count and both hash values as "
                          "recorded. Every prior clause is carried through unchanged.",
            },
            {
                "source_id": "SRC-0250",
                "fields": {"limitations": BASIS_RESTORE_SOURCE_LIMITATIONS},
                "reason": "P-0016: the restoration source calls the same path 'pre-existing drift "
                          "unrelated to this repair', which understates the campaign's own "
                          "footprint on a path the AUCTION freeze sealed. The corrected "
                          "attribution is appended after the original clause, which is kept; the "
                          "count of four drifted paths and both hashes are unchanged.",
            },
        ],
        "decision": "NO_CHANGE",
        "reason": "A record-correction entry, not a verdict. Three defects in this campaign's own "
                  "records - the misattributed M1/src/materialize.py drift in EVD-0075 limitation "
                  "(c), the stale present tense in EVD-0072 limitation (iii), and the "
                  "ceiling_permits_status/ceiling_violations contradiction that is systemic to "
                  "RECORDED_DECISION kills - are corrected append-only: the two evidence rows keep "
                  "their original text and carry the correction after it, the three source rows "
                  "keep every prior clause and name what was corrected, and the third defect is "
                  "registered as UNK-0036 rather than fixed because the generator's semantics are "
                  "not this pass's to change. No candidate status, gate, count or verdict moves; "
                  "no sealed artefact is written; nothing is deleted.",
        "verification_notes": "Contrary readings were searched for before the corrections were "
                              "recorded, and each correction was re-established from the "
                              "repository rather than taken from the verification report. The "
                              "drift attribution was checked against git itself (git log and git "
                              "show over M1/src/materialize.py: bdec4cc1... at ba3705a/7b76e9f/"
                              "c8fd95d, ad1d18d2... from e64acb6 at 2026-10-01T02:29:43-04:00, and "
                              "the same value on the working tree), so the corrected attribution "
                              "does not rest on a second-hand summary. The freeze restoration was "
                              "re-checked by the sealed module's own CLI and by a full re-hash "
                              "sweep of the basis run_inputs.json (155/155), so the supersession "
                              "recorded for EVD-0072 (iii) is current rather than asserted. The "
                              "tempting over-readings were tested and rejected: (i) that a wrong "
                              "attribution somehow invalidates the drift accounting - it does not, "
                              "the count (four) and both hashes are exact and are left untouched; "
                              "(ii) that the stale limitation should be rewritten - it should not, "
                              "the row records what was true when written and the correction is "
                              "appended after it; (iii) that the ceiling contradiction should be "
                              "fixed while it is visible - it should not by this pass, since "
                              "materialize._ceiling_ok and candidate_gates.ceiling_violations "
                              "disagree deliberately and choosing between them is a decision "
                              "(UNK-0036), not a row edit. No evidence row was rewritten, no "
                              "superseded sentence was deleted, no sealed artefact was modified, "
                              "and no candidate field was touched.",
        "status": "PROPOSED",
        "created_at": created_at,
    }
