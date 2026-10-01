# W11 — three append-only record corrections, one regeneration, one validation pass (GOAL-M2-BRIDGE-001, epoch 6)

Role: record correction. Verification wave V4 found three defects in the campaign's **own records**
(`.research/m2_bridge_001/verification/V4/REPORT.md` §5.1-§5.3, all three treated as ground truth
here). This pass corrects them without rewriting history: no superseded sentence is deleted, no
sealed artefact is touched, no rule is weakened, no candidate status/gate/count/verdict moves, and
there is no commit and no push.

Deliverables: the corpus patch module `M1/src/corpus/patches/p0016_record_corrections.py` and its
emitted `M1/work/patches/P-0016.json`; the append-only evidence-amendment section of the patch
contract that carries the two in-row corrections; the regenerated canonical artifacts; this report.

---

## 1. What each correction had to satisfy

| defect | V4 class | wrong statement lives in | correction must | delivered as |
|---|---|---|---|---|
| misattributed `M1/src/materialize.py` drift | CONTESTED | `EVD-0075` limitation (c) | fix the attribution, keep the drift count (4) and both hashes exactly | clause appended to `EVD-0075.limitations`; `SRC-0250`, `SRC-0248` limitations corrected; `modified_claims[0]`; `EVD-0076`; `SRC-0251` |
| stale present tense on the branch-C freeze | SUPPORTED_SCOPED | `EVD-0072` limitation (iii) | keep the original text, add a cross-reference that a reader of that limitation alone sees | clause appended to `EVD-0072.limitations`; `modified_claims[1]`; `SRC-0247` points at the in-row correction |
| `ceiling_permits_status = NO` vs `ceiling_violations = 0` | observation (secondary) | generator output `M1/output/status_derivation_review.csv` | record the contradiction, do **not** silently change the generator | registered canonically as `UNK-0036` (`new_unknowns`); `modified_claims[2]`; generator untouched |

The one thing the repo could not do before this pass: put a correction **inside** the evidence row
that carries the wrong statement. Evidence rows are append-only in this corpus and a patch had no
way to express "append to this row" — which is exactly why P-0014's correction of EVD-0072 (iii)
sat *beside* the row and V4 still found a reader of the row alone misled. §4 records the narrow
contract addition that closes that gap.

---

## 2. Correction 1 — the misattributed `M1/src/materialize.py` drift

Re-established from git in this pass (not carried second-hand):

```
$ git log --oneline --format='%h %ad %s' --date=iso -3 -- M1/src/materialize.py
e64acb6 2026-10-01 02:29:43 -0400 feat(m1): record the three M2-bridge branch verdicts with scopes, limitations and resurrection conditions
ba3705a 2026-09-30 14:42:59 -0400 feat(m1): register Nasdaq closing-auction candidate and correct ES cost prerequisite
$ git show e64acb6:M1/src/materialize.py | shasum -a 256
ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0  -
$ git show e64acb6^:M1/src/materialize.py | shasum -a 256
bdec4cc1ef1821a83210a646e041113b6fb6cdab75cb48d4de17d95fb971a08c  -
$ shasum -a 256 M1/src/materialize.py
ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0  M1/src/materialize.py
```

`bdec4cc1...` is the value the AUCTION `run_inputs.json` sealed; `ad1d18d2...` is the tree value; the
change is this campaign's own canonical-application commit `e64acb6` (the three-branch-verdict
application), seven hours after the auction seal. The drift count (four) and both hash values are
therefore untouched — only the attribution was wrong.

Appended to `EVD-0075` limitation (c), verbatim as recorded (original sentence kept, unedited):

> `[CORRECTED 2026-10-01, patch P-0016: the words 'PRE-EXISTING and unrelated' above give the wrong attribution; the drift count (four) and both hash values are correct and unchanged. Git shows M1/src/materialize.py at bdec4cc1ef1821a83210a646e041113b6fb6cdab75cb48d4de17d95fb971a08c through ba3705a, 7b76e9f, c8fd95d, and at ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0 from e64acb6 (2026-10-01T02:29:43-04:00) onward - this campaign's own canonical-application commit, which recorded the three M2-bridge branch verdicts, seven hours after the auction seal. The drift is therefore this campaign's own and not an earlier unrelated pass; what remains true is the narrower fact that W9's repair did not touch the file, and that the pipeline rule is deliberately left unchanged. Recorded on SRC-0251, EVD-0076 and in this patch's modified_claims.]`

The same misattribution was repeated in two mutable source-registry limitations
(`SRC-0248` "(pre-existing drift, unrelated to the repair)", `SRC-0250` "pre-existing drift unrelated
to this repair"). Both were replaced by the corrected clause **with every prior clause carried
through unchanged and the wrong phrasing kept in place**, followed by a `[CORRECTED 2026-10-01,
P-0016: ...]` clause. The immutable patch records that carry the phrase — `P-0014`'s docstring and
`P-0015`'s — were **not** edited; the cross-reference to them lives in `P-0016` and in `EVD-0076`.

## 3. Correction 2 — the stale present tense in `EVD-0072` limitation (iii)

Re-verified in this pass:

```
$ .venv/bin/python3 -m M2.src.basis_materiality --check
{"freeze_sha256_matches": true, "code_unchanged": true, "inputs_unchanged": true,
 "drifted_inputs": [], "sealed_contract_sha256": "389b8f4d65b1b2f54bf5eb29266c74c078ca7187e8c1b4455052fa52d780e3a7"}
```

and a full re-hash sweep of the three bridge hash sets: AUCTION 22 recorded / 18 verify / 4 drift,
ES 13/13, **BASIS 155/155**.

Appended to `EVD-0072` limitation (iii), verbatim as recorded (original limitation kept, unedited):

> `[CORRECTED 2026-10-01, patch P-0016: limitation (iii) above was true when it was written and is false now. The W9 restoration (patch P-0014, SRC-0250, EVD-0075) put the sealed module back at 9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477, and the basis freeze verifies in place again: M2/src/basis_materiality.py --check reports freeze_sha256_matches, code_unchanged and inputs_unchanged all true with no drifted inputs, and every one of the 155 recorded code/input entries of the basis run_inputs.json resolves (re-verified 2026-10-01). The superseding record is EVD-0075 with SRC-0250 and P-0014; limitation (iii) is retained verbatim above as the record of what was true when it was written.]`

Success condition check: a reader who opens only `EVD-0072` (iii) — in `M1/data/evidence_ledger.csv`
or in the root `EVIDENCE_LEDGER.csv` — now reads the limitation **and** the correction that names
EVD-0075 / SRC-0250 / P-0014 in the same cell, and the original sentence is still there. The reader
is no longer misled. `SRC-0247` was also brought into line so following `source_id` does not lose
the pointer.

## 4. Correction 3 — the `status_derivation_review` contradiction, registered not fixed

Observed contradiction (exact values, unchanged from V4):

- `M1/output/status_derivation_review.csv` → `ceiling_permits_status = NO` for
  `TUP-CME-ES-H3-OFI-AGG`, `TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX`, `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG`,
  `TUP-NASDAQ-LARGETICK-H2-QIMB-PAS`, `TUP-NASDAQ-LARGETICK-H2H3-MICRO-AGG`;
- `M1/output/M1_STATE_SUMMARY.json` → `ceiling_violations = 0`; `validate.py --strict` → PASS, 0 failures;
- scope: systemic to **all `RECORDED_DECISION` kills** (both bridge kills plus the three pre-existing
  M2 kills), caused by none of this campaign's work;
- cause: `materialize._ceiling_ok` requires `ceiling == "DEAD"` for any DEAD row, while
  `candidate_gates.ceiling_violations` deliberately exempts a death recorded as a decision with a
  cause and a resurrection condition;
- consumers: **none** — no gate, count, verdict or frontier item reads the column.

Recorded as `UNK-0036` (`conflict_type = CONTRADICTION`, `severity = NON_BLOCKING`,
`resolution_stage = NON_BLOCKING`, `resolution_method = HUMAN_INPUT`, `resolution_class = D`,
`evidence_ids = EVD-0076`, `source_A = SRC-0251`, affected scope = the five rows), with what would
resolve it: a decision about what the column is meant to assert, or a generator fix to
`_ceiling_ok` mirroring the recorded-kill exemption. **The generator was not changed.**

## 5. How a correction is carried without rewriting history

`P-0016` is a normal code-authored patch (docstring + `build()`), emitted to
`M1/work/patches/P-0016.json` by the same path as `P-0001..P-0015`, with
`decision = "NO_CHANGE"`. It carries: `new_sources = [SRC-0251]`, `new_evidence = [EVD-0076]`,
three `modified_claims` entries marked `CORRECTED`, `new_unknowns = [UNK-0036]`, three
`proposed_source_updates`, and two `proposed_evidence_updates`.

The one contract addition (`M1/orchestrator/{patch,schemas,transitions}.py`) is deliberately
minimal and append-only by construction:

```
proposed_evidence_updates = [{"evidence_id", "field", "append", "reason"}, ...]   # fields:
                            # claim | limitations | decision_implication | methodology
```

- **replacement is inexpressible** — the entry has no `replace`/`value` form; `apply_verified`
  concatenates (`row[field] = original + " " + append`), so the superseded text stays where it was
  written;
- **fail-closed shape** — `schemas.validate_patch` rejects an unknown field, an unknown target
  field, an empty `append` and a missing `reason`;
- **adversarial gate** — `transitions.verify_patch` rejects an amendment that names a row no
  authored or patch-declared evidence row provides (`verify_all` folds this batch's declared ids
  into the canonical set so a patch may amend a row another patch declares, which is the case here);
- **audited** — every applied amendment produces an `EFFECT` entry in
  `M1_STATE_SUMMARY.json:patches.audit` (visible in §7's regeneration), and an already-applied
  amendment is a no-op rather than a duplicate append.

Why not simply edit `M1/work/patches/P-0011.json` / `P-0014.json` (whose `new_evidence` rows carry
the text)? Those files are the record of what was proposed and verified; editing them would rewrite
history and destroy the audit trail (`V17`), and editing the *emitted* JSON without the module would
leave the declarative source and the inbox disagreeing. The block condition did **not** arise: the
conventions can express the correction without deleting anything — the `append` clause is appended
to the row, the original text is preserved byte-for-byte, and the patch record names what was wrong.

Two tests were added to `M1/tests/test_orchestrator.py::PatchIntegrity` (99 → 101 tests):

- `test_evidence_amendment_appends_and_keeps_the_superseded_text` — the amended row starts with the
  original text, ends with the correction, and the amendment is audited;
- `test_evidence_amendment_for_a_row_nothing_declares_is_rejected` — unknown target, non-appendable
  field and empty append are all refused.

Both fail against the pre-change code, checked by loading the pre-change `HEAD` orchestrator modules
into a scratch interpreter:

```
old verify status: VERIFIED []            # the unknown-target amendment was accepted
old apply changed the row: False          # and silently never applied
amendments in audit: 0
```

i.e. before this pass the same correction would have been a **silent no-op** on an unchanged row.

## 6. Regeneration and validation

```
$ python3 M1/src/materialize.py                 # exit 0
$ python3 M1/src/validate.py --strict
{ "overall": "PASS", "failures": 0, "checks": 19 }
$ python3 -m unittest discover -s M1/tests -t .
Ran 101 tests in 0.121s
OK
```

Determinism: a second `materialize` run left `M1/data/evidence_ledger.csv` byte-identical (only
`generated_at`/`created_at` fields move, as for every other emitted artifact and patch).

Sealed-artefact boundary, re-checked after this pass: AUCTION 22 recorded / 18 verify / **4 drift**
(the same four as recorded: `M2/src/admission.py`, `seal_freeze.py`,
`test_auction_materiality.py`, `M1/src/materialize.py`), ES 13/13, BASIS 155/155. My edits sit in
`M1/orchestrator/**`, `M1/src/corpus/**` and `M1/tests/**`, none of which is a sealed path, so the
drift set is unchanged. `git status` shows no modified sealed artefact under `M2/experiments/**` or
`M2/src/**`: the only entries there are W9's disclosed repair (`M2/src/admission.py`,
`M2/tests/test_auction_materiality.py`, `.../seal_freeze.py` modified; `M2/src/admission_auction.py`
added) and W10's untracked ES addendum pair.

## 7. Counts before / after (candidate status, gates, accounting)

| counter | before | after |
|---|---|---|
| candidate status | ALIVE 0 / WEAK 3 / UNKNOWN 15 / DEAD 12 (total 30) | **identical** |
| status_by_class | identical | **identical** |
| gate counts | KG1 B27/F2/P1, KG2 B28/F2/P0, KG3 B28/F2/P0, KG4 B26/F1/P3, KG5 B14/F5/P11 | **identical** |
| `gate_rule_trace.csv`, `candidate_gate_status.csv`, `status_derivation_review.csv`, `candidate_closure_metrics.csv`, `hard_constraint_*`, `dominated_candidates.csv`, `latency_feasibility.csv` | — | **byte-identical** |
| patches proposed / applied / rejected | 15 / 15 / 0 | **16 / 16 / 0** |
| `ceiling_violations` | 0 | **0** |
| `recorded_kill_decisions` | 5 | **5** |
| `frontier_items` | 27 | **27** |
| `gate_eligible` / `m1b_eligible` | 0 / [] | **0 / []** |
| `blocking_issues` | 35 | **35** |
| `open_issues` | 50 | 51 (+UNK-0036) |
| `discrepancies` | 56 | 57 (+UNK-0036) |
| `non_frontier_issues` | 15 | 16 (+UNK-0036) |
| `evidence_records` | 74 | 75 (+EVD-0076) |
| `source_registry` | 101 | 102 (+SRC-0251) |
| migration `by_stage.NON_BLOCKING` | 5 | 6 (+UNK-0036) |
| migration `unmapped_issues` (issues with no authored staging row) | 24 | 25 (+UNK-0036; the patch-registered issues UNK-0033/0034/0035 are already listed there) |
| `closure_modes`, `pareto`, `migration.by_method`, `migration.migrated_count`, `migrated_out_of_m1_blocking` | — | **identical** |

No candidate status, gate, kill decision or verdict changed. The counters that moved are exactly
the registries the correction had to add to: one issue, one evidence row, one source.

Canonical **cells** that changed beyond timestamps: `dead_candidates.csv` evidence_ids for
`TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX` (gained `EVD-0076`), `evidence_coverage.csv` evidence
lists and neutral/supported counts for the two bridge branches (gained `EVD-0076`),
`candidate_tuples.csv` `gate_recompute_date` only (timestamp), the two amended limitations cells,
the three corrected source limitations, and the new rows. Kill bases, kill reasons, resurrection
conditions, `status_basis` and every gate vector are unchanged.

## 8. Files changed

- **new code**: `M1/src/corpus/patches/p0016_record_corrections.py`; registered in
  `M1/src/corpus/patches/__init__.py`; emitted `M1/work/patches/P-0016.json`.
- **contract**: `M1/orchestrator/schemas.py`, `M1/orchestrator/patch.py`,
  `M1/orchestrator/transitions.py` (append-only amendment section + its gate).
- **tests**: `M1/tests/test_orchestrator.py` (+2).
- **regenerated**: `M1/data/{evidence_ledger,source_registry,discrepancies,dead_candidates,candidate_tuples}.csv`,
  `M1/output/{M1_STATE_SUMMARY.json,M1_CLOSURE_STATUS.json,evidence_coverage.csv,issue_migration.csv,non_frontier_issues.csv,M1_D0_READINESS.md,M1_D1_BLOCKED.md}`,
  root `EVIDENCE_LEDGER.csv`, `DISCREPANCIES_AND_UNKNOWNS.md`, `PROJECT_STATE.md`, and
  `M1/validation/report.{json,md}` (rewritten by the instructed `validate.py` run).

## 9. Deliberately left unchanged

- **The generator's semantics.** `materialize._ceiling_ok` and
  `candidate_gates.ceiling_violations` are exactly as they were; the contradiction is registered as
  `UNK-0036`, not silently "fixed".
- **`M1/src/validate.py`** — untouched (it is also a path the AUCTION seal records).
- **All sealed artefacts** — nothing under `M2/experiments/**` frozen outputs, `run_inputs.json`,
  `freeze.json`, `results.json`, `certificate.json`, `entry_prints.json`, `signal_extract.json`,
  `admission_v2_result.json` was written; `M2/**` is untouched by this pass.
- **The original text of every superseded statement** — EVD-0072 (iii), EVD-0075 (c), the `SRC-0248`
  and `SRC-0250` clauses are all still present, with the correction appended after them.
- **The patch records `P-0011` / `P-0014` / `P-0015`** (modules and emitted JSON) — not edited;
  the corrections name them instead.
- **`M1/src/materialize.py`** — not edited (it is the drifted path itself; editing it would deepen
  the AUCTION drift for no benefit).
- **The drift accounting** — four drifted paths, `bdec4cc1...` sealed against `ad1d18d2...` on the
  tree, all unchanged.
- **No commit, no push.**

## 10. Verification boundary

Covered by this pass: the git attribution (re-derived from `git log`/`git show` and the working-tree
hash), the freeze restoration (the sealed module's own `--check` plus a 155/155 re-hash sweep), the
seal-drift set (recomputed for all three bridge experiments), the append-only property (test + a
pre-change demonstration that the old code silently ignored the same amendment), the generator
contradiction (read from the generated tables and both code paths), and the full M1 validation
(`validate.py --strict` PASS/19 checks, 101 tests green).

Not settled here, and recorded as such in `EVD-0076.limitations` and `UNK-0036`: whether the AUCTION
seal intended the pre- or the post-`e64acb6` pipeline (the seal does not say), and what
`ceiling_permits_status` is meant to assert — the latter is `UNK-0036` and needs a decision or a
generator fix, neither of which is this pass's to take.
