# V4 — canonical record, two closeout repairs, and sealed-artefact integrity

**Goal:** GOAL-M2-BRIDGE-001, verification wave V4 (closing check).
**Interpreter:** `/Users/tofuinparis/Projects/Calibrated-Hierarchical-Trading-Runtime/.venv/bin/python3`
(Python 3.14, numpy in-tree). **Date:** 2026-10-01.
**Posture:** adversary. The appliers of canonical state (W8) and the two repair passes (W9, W10)
did not certify themselves; every claim below is re-derived from the sealed artifacts.

**Read-only compliance.** Nothing outside `.research/m2_bridge_001/verification/V4/` was authored.
No commit, no purchase, no credential, no network fetch, `python3 M1/src/materialize.py` never run.
Two commands with disclosed, unavoidable side effects are listed in §7.

**Headline:** 11/11 items VERIFIED; **0 REJECTED, 0 UNVERIFIED**. Two sub-items are
**CONTESTED**/**SUPPORTED_SCOPED** at the level of a *wording*, not of a number or a verdict
(§5). Every numeric quantity asserted by EVD-0071..EVD-0075 was reproduced from the artifact it
cites; the reverse trace finds **zero untraceable numbers**.

---

## 1. Scripts and their sha256

| script | sha256 | covers |
|---|---|---|
| `v4_a1_ledger_trace.py` | `63d2c23fa9ce49a5a0d685a32fa47a056a5b563b959fae31221beffa17c74744` | A1 forward assertions (93) |
| `v4_a1b_unmapped_tokens.py` | `219b11f8aef0cd8db99f974ac06bbde6ed7f25e8ad7b0bfcf0bb5f78de3cda38` | A1 reverse trace |
| `v4_a2_a4_canonical.py` | `050f4eb7577cf96a2b1c429bbba1f1e75ad96151672d3f737ce6e8270eafab75` | A2/A3/A4 (56) |
| `v4_b5_b6_repairs.py` | `b98efddbc0711ab090670e30bd01204942f93e3f8c62422ccddbbb9a622caaa6` | B5/B6 (15) |
| `v4_b7_splice_fixture.py` | `d14b71a40bf820f95b8011fd6fe1f2fa14d5dbe045257a2f5b468c3a0db575a1` | B7 (15) |
| `v4_b8_addendum.py` | `b82d81ad7d69a4f2bf35d2b2f73771973cd197834c5e978e788b7d4344cfc7eb` | B8 (9) |
| `v4_c9_seal_sweep.py` | `3bc6942228d7f79007b04fd053bfdd9ebbddb8a44ccc0d13daca2f43e850c523` | C9 (19) |
| `v4_d10_suites.py` | `c32660c4c75448781f77f10f646bec536d2ad6b549766cfd2b603059f33d5758` | C10 (4) |
| `v4_nc_negative_controls.py` | `250d0a84355daa74eaf50e9cc4fb8641ae3bcb4d0c123cf0c170d151a88630aa` | NC1–NC3 (9) |

**220 assertions, 220 pass, 0 fail** (93 + 56 + 15 + 15 + 9 + 19 + 4 + 9; `v4_a1b` is the reverse
trace and reports 0 unmatched numbers instead of a pass count). Per-item JSON receipts sit beside
each script (`v4_a1_ledger_trace.json`, …). Fixture artefacts written under V4 only:
`v4_spliced_window.bin.gz`, `v4_splice*`, `v4_fixture_manifest_*.json`,
`v4_fixture_certificate_*.json`, `v4_fixture_result_*.json`, `auction_v2_rerun.json`,
`v4_addendum_rerun.json`, `nc_perturbed_*.csv`, `_validate_run{1,2}.json`.

---

## 2. CLAIM SET A — canonical records vs the artefacts

### A1 — every number in EVD-0071..EVD-0075 (VERIFIED)

Two directions, not one:

* **Forward (93 assertions).** Each asserted quantity is read from a named field of the cited
  sealed artifact and compared as a *rendering*: the artifact float formatted at the claim's own
  decimal count must equal the claim string (so a one-digit change or a changed rounding fails).
  Counts are exact integers. Verdicts 93/93: EVD-0071 25, EVD-0072 21, EVD-0073 24, EVD-0074 15,
  EVD-0075 8.
* **Reverse (`v4_a1b`).** Every numeric token in the five rows' claim/methodology/sample/
  limitations/decision-implication text is matched against a 37,779-value universe built only from
  the cited artifacts (the three experiment directories + the V1/V2/V3 reports; the canonical CSVs
  and `FINAL_REPORT.md` are deliberately **excluded** so the record cannot cite itself). Result:
  **zero unmatched numbers in all five rows.** The only non-numeric tokens are three hex prefixes
  (`9f5862f7`, `00363c3a`, `84fd3270`) and the seed `20260717`; all four were located by hand —
  `9f5862f7` = BASIS `inputs_sha256.code["M2/src/admission.py"]` and the `ac28929` git blob;
  `00363c3a` = the AUCTION seal's recorded value for the same path; `84fd3270` = the current
  `M2/src/admission_auction.py`; `20260717` = the ES contract's bootstrap seed.

Numbers that required **independent re-derivation** rather than a read-back (nothing was taken
from V3 prose): the auction decomposition
`mean capture = mean mechanism − mean side-signed(entry − reference)` = `6.5168433 − 115.4114632
= −108.8946198` (Δ = 0); the concentration `worst 50 / total net loss = 93.9 %` (my value
122.7540/130.6712 = 93.91 %, and the worst single symbol 12.9 %); the restriction `348 symbols with
reconstructed spread ≤ 10 bps → −0.6029 bps capture, +3.5475 bps mechanism`; the maximum
reconstructed entry spread `$11.64` on an entry price of `$2.10` (symbol SQFT); `4,281 of 12,809`
records carrying `closing_cross_valid = true` and `closing_cross_price_raw ≠ 0` (counted from
`signal_extract.json`); near and far prices are `0` in **all** 12,809 records; the orphan identity
4,623 + 3,703,481 + 30,676 + 3,437,444 = 7,176,224 over 20,072,550 in-scope messages = 35.75 %;
the 47.8 % direction-rule removal (1,179/2,465); the ES 598/594/584 quote-available slots vs
583/579/569 evaluated observations; and the addendum's deltas (+0.0051255 / −0.0083535 /
−0.0100189) recomputed from the matched-instant and published values.

**No fabricated number, no rounding that changes a value, and no claim stated more strongly than
its source was found.** Three specific over-claim risks were tested and cleared:
(i) EVD-0072's "true C\* is MORE negative than reported" is attributed to the one-sided unresolved
C1 items exactly as V3's C10 requires, not to the two-sided funding bracket;
(ii) EVD-0073's "mechanism metric is POSITIVE and above the 1.02 bps floor" is accompanied by the
non-executability caveat in the same field and in the candidate row, so it is not promoted to edge;
(iii) EVD-0071's "coverage passed" matches `coverage_gate_passed = true` and the three recorded
floors (0.95 / 0.75 / 250).

### A2 — the contested/rejected findings survived as limitations (VERIFIED, 27 checks)

| finding | carried into canonical state as | state |
|---|---|---|
| auction freeze invalid as a preregistration (sealed input predating the seal, holding the Closing Cross exit price) | EVD-0073 claim + limitation (a); `experiments.csv` EXP-0012 `INVALIDATED_FREEZE`; SRC-0248 ("the sealed input therefore PREDATES the seal"); OQ-0017 `unresolved_gap` (4,281 of 12,809) | **PRESENT** |
| reconstruction-artifact decomposition of −108.8946 bps | EVD-0073 claim + limitation (b); OQ-0017 `current_best_answer` (identity + 93.9 % + −0.60 bps) | **PRESENT** |
| degenerate near/far diagnostic | EVD-0073 claim + limitation (c); `experiments.csv`, P-0012 | **PRESENT** |
| basis module-hash drift | EVD-0072 limitation (iii); P-0014 `modified_claims` (status CORRECTED) | **PRESENT but STALE** — see §5 |
| AUCTION drift fallout after the repair | EVD-0075 claim + limitation (b); P-0015; `run_inputs` historical-drift note | **PRESENT** |
| unanchored sealing, branch A | EVD-0071 limitation (i); candidate row `notes` ("freeze 15:15:44 precedes results 15:15:59 … no external anchor … UNVERIFIED"); resurrection condition requires externally anchored sealing | **PRESENT** |
| unanchored sealing, branch C | EVD-0072 limitation (ii); candidate row `notes` ("freeze 15:21:16 precedes results 15:22:17 … UNVERIFIED") | **PRESENT** |
| ES instant-set addendum | EVD-0074; `addendum_unconditional_matched_instants.{json,py}`; SRC-0249; P-0013 | **PRESENT** |
| unvalidated entry book / signal-scope subfloor | EVD-0073 clauses; OQ-0017; proposal decision `WEAKENED` | **PRESENT** |
| 84 unresolved settlements bracketed, not zeroed, in the measured series | EVD-0072 limitation (i) | **PRESENT** |

### A3 — branches A and C (VERIFIED, 22 checks)

Both `TUP-CME-ES-H3-OFI-AGG` and `TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX` are
`overall_status = DEAD`, `kill_gate = KG3_EXECUTION`, `kill_status = ACTIVE`,
`kill_superseded_by = UNKNOWN`, with a non-trivial `resurrection_condition` and a
`re_entry_policy` requiring NEW_EVIDENCE plus an explicit decision in `DECISIONS.md`
(`dead_candidates.csv`, 12 rows). A's cause is explicitly scoped ("scoped to that single window");
C's cause names the measured panel and formulation — the corpus's own convention for a recorded
kill (the three pre-existing M2 kills state their tape the same way). **Neither is ALIVE; neither
is gate-eligible** (`gate_eligible: []`, `m1b_eligible: []`, and no row's `status_ceiling` exceeds
`NOT_ALIVE` — 23 `NOT_ALIVE`, 7 `DEAD`). Counts are internally consistent in three independent places — `candidate_tuples.csv`
(30 rows: 0/3/15/12), `M1_CLOSURE_STATUS.json:candidate_counts` (identical), and
`M1_STATE_SUMMARY.json` (`recorded_kills` = the same 12 ids). `ceiling_violations = 0`.

### A4 — the auction rows (VERIFIED, 7 checks)

`TUP-NASDAQ-CLOSE-H4-LATENOII-AGG` carries **no kill and no survival verdict**:
`overall_status = kill_gate = kill_status = resurrection_condition = UNKNOWN`, absent from
`dead_candidates.csv`, present in no recorded-kill list. The parent
`TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG` is **unrevived**: identical to its pre-bridge revision
(`9e5026f`, 2026-09-29) in every field except `gate_recompute_date`, and its
`overall_status/kill_status/kill_gate` were `UNKNOWN/UNKNOWN/UNKNOWN` in **every** revision in git
history that contains it. OQ-0017 records the named next action (warm-up re-extract under a freeze
whose inputs carry no outcome quantity and whose sealing is anchored), gated `M2_ENTRY`.

---

## 3. CLAIM SET B — the repairs hold

### B5 — the basis freeze verifies in place again (VERIFIED, 6 checks)

* `sha256(M2/src/admission.py)` = `9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477`
  = the value in `M2-BRIDGE-HL-BINANCE-BASIS/freeze.json` = the value in `run_inputs.json`
  = the value of the git blob at `ac28929`. (The committed blob check is independent of the
  freeze: `git show ac28929:M2/src/admission.py`.)
* **All 155** of the BASIS freeze's sealed entries re-resolve from disk (3 code, 5 panel, 147 raw).
  The BASIS CLI's own `--check` agrees
  (`freeze_sha256_matches / code_unchanged / inputs_unchanged = true`, `drifted_inputs: []`) — used
  only as corroboration; the hash loop is the primary evidence.
* `sha256(M2/src/admission_auction.py)` = `84fd3270cc382248b6e57bd8111abc2fdb37f546150ea9f043df83fd47110caf`,
  the value EVD-0075 records.

### B6 — the relocation changed no behaviour (VERIFIED, 9 checks)

`python3 -m M2.src.admission_auction --manifest admission_manifest_v2.json --branch AUCTION_V2
--root .` on the **sealed** manifest exits 0, returns `DATA_VALID`, and its 28-entry `checks_run`
(including `session.continuity` and `coverage.certificate`), `reasons`, `reason_counts`, `notes`
and identity fields are **byte-identical** to the sealed `admission_v2_result.json`
(sha256 `5bb8d79cd84ea61a3fb707e6b537f56218e798508ffa0fef7937ebf3e25a4c9a` on both). No verdict,
check set or finding moved.

### B7 — the contract is not weaker after the move (VERIFIED, 15 checks)

I built **my own** spliced fixture: the retained `window.bin.gz` decoded once, first 8 MiB kept,
last 8 MiB kept and frame-aligned with the documented message-length table, re-gzipped under V4
(payload 16,777,206 B = 0.9197 % of the 1,824,239,389 decoded bytes). My own frame parser then
measured the spliced stream: 585,996 in-window messages, 585,995 in-window pairs, largest
in-window inter-message gap **609,647,167,374 ns** against the 1 s bound, 0 backwards timestamps —
matching the sealed certificate's retained `splice_negative_control` block exactly
(messages, pairs and gap all equal; the `.gz` container hash differs only by the gzip mtime header
field, so payload identity is pinned by size + fingerprint instead).

Contract results on fixtures:

| fixture | state | `session.continuity` | `coverage.certificate` |
|---|---|---|---|
| spliced certificate (gap/counts from my tape, verdict FAIL, coverage 0.0) | `DATA_INVALID` | **fires** (gap 609647167374 vs declared 3625332; counts 585996 vs 55698714; certificate verdict FAIL) | **fires** (ratio 0.0 < floor 0.95; manifest 1.0 ≠ certificate 0.0) |
| coverage-floor fixture (pristine continuity, ratio 0.80) | `DATA_INVALID` | clean | **fires** |
| pristine control (re-serialised sealed manifest) | `DATA_VALID` | clean | clean |

The two contract-scoped checks still refuse a spliced input, and they are not dead code: the
control on the same machinery passes.

### B8 — the ES addendum reproduces byte-identically (VERIFIED, 9 checks)

Running the committed `addendum_unconditional_matched_instants.py --out <V4>` reproduces
`addendum_unconditional_matched_instants.json` **byte-identically** (sha256
`ba3717274896f04100a2674e2735265e8ee76e179f11611b73c7078fba764cf1`), as does its stdout path. All
five sealed ES artefacts (`freeze.json` `42a158c5…`, `freeze.sha256`, `run_inputs.json`,
`results.json` `09c85629…`, `proposal.json`) hash identically before and after; the addendum's own
recorded `results_json_sha256` and script sha256 (`e7d8405b745063c0f004abbaba9ac0055f897d135aeb5ac7f609f5ad01979dd0`)
match. The only working-tree additions in that directory are the two new untracked addendum files.

---

## 4. CLAIM SET C — no sealed artefact moved

### C9 (VERIFIED, 19 checks) — with one attribution defect (§5.2)

| experiment | sealed entries | resolve now | drift |
|---|---|---|---|
| ES | 13 | 13 | **0** |
| BASIS | 155 | 155 | **0** |
| AUCTION | 22 | 18 | **4**, all disclosed |

Recomputed values (all match the values recorded in the artefacts themselves): ES `freeze.json`
`42a158c5…`, `results.json` `09c85629…`; BASIS `freeze.json` `389b8f4d…`, `results.json` `97a4d7ac…`;
AUCTION `freeze.json` `9baff3dd…`, `results.json` `15b7a3d5…`, `certificate.json` `6e4b257e…`,
`entry_prints.json` `9f52149c…`, `signal_extract.json` `463663463ab3ab4eb34cae2a2927584bfd099515445af36d28f89fd9ce5d5889`,
`admission_v2_result.json` `5bb8d79c…`, `spec_prev_retained.json` `5ef1dcac…`. Each `freeze.sha256`
equals the recomputed hash of its `freeze.json`; each `run_inputs.json` `freeze_sha256_sealed`
equals it too; ES's addendum cross-references `results.json` and `freeze.json` correctly; BASIS
`results.json:integrity` shows `panel.grid_identity`, `panel.manifest_window_matches` and
`manifest_files.all_match` all true. **Every tracked sealed artefact matches its committed `HEAD`
blob in all three experiments**; the only tracked modification anywhere under those directories is
`…/seal_freeze.py`, the disclosed W9 re-point.

The four AUCTION drifts and their attribution:

| path | sealed | observed | attribution |
|---|---|---|---|
| `M2/src/admission.py` | `00363c3a…` | `9f5862f7…` | W9 repair (intended, disclosed) |
| `…/seal_freeze.py` | `813a1612…` | `e4e6e024…` | W9 repair (intended, disclosed) |
| `M2/tests/test_auction_materiality.py` | `940c5b61…` | `b08e7945…` | W9 repair (intended, disclosed) |
| `M1/src/materialize.py` | `bdec4cc1…` | `ad1d18d2…` | **this campaign's own W8 commit `e64acb6` (2026-10-01T02:29:43-04:00)** — not an unrelated earlier pass |

`entry_prints.json` links to its inputs by path and diagnostics, **not** by content hash (recorded
as an observation; the freeze seals both files, so the chain is not broken).

### C10 (VERIFIED, 4 checks)

* `.venv/bin/python3 -m unittest discover -s M2/tests -t .` → **Ran 332 tests … OK**.
* `.venv/bin/python3 M1/src/validate.py --strict` → `{"overall": "PASS", "failures": 0, "checks": 19}`.
* The validator's report body is byte-deterministic modulo `generated_at` across two runs.
* `M2.tests.test_auction_materiality` alone → **Ran 40 tests … OK**, matching EVD-0075's count.

---

## 5. Findings that are not clean VERIFIED

### 5.1 [`SUPPORTED_SCOPED`] EVD-0072 limitation (iii) is stale present-tense text

EVD-0072 states the freeze "no longer verifies in place" because `M2/src/admission.py`
"had drifted". That is **no longer true after W9**: the file hashes to the sealed value and the
BASIS CLI's `--check` passes. The correction is recorded (EVD-0075, SRC-0250, P-0014's
`modified_claims` entry marked `CORRECTED`, and the candidate row cites EVD-0075), and P-0014 states
explicitly that evidence rows are append-only and the stale text is left in place. So the record is
*internally resolved* but *locally contradictory*: a reader who opens only EVD-0072(iii) concludes
the seal is broken. **Decision impact: none** (the basis kill does not rest on it and the row
carries the superseding row). Not a rejection — the limitation was carried, not dropped, and the
repair supersedes it on the record.

### 5.2 [`CONTESTED`] attribution of the `M1/src/materialize.py` drift

EVD-0075 limitation (c) calls that drift "PRE-EXISTING and unrelated to this repair - the pipeline
file changed after the auction seal"; W9's report adds that "the working tree is clean at HEAD …
so an earlier pass changed `materialize.py` after the auction seal". Git says otherwise:
`M1/src/materialize.py` is `bdec4cc1…` at `ba3705a`/`7b76e9f`/`c8fd95d` and `ad1d18d2…` from
**`e64acb6`** onward — i.e. it was changed by *this campaign's own canonical-application commit*
(2026-10-01T02:29:43-04:00, the three-branch-verdict application), seven hours after the auction
seal. The claim is accurate about the repair (W9 did not touch it) but the words "pre-existing" and
"an earlier pass" understate the campaign's own footprint on a path the AUCTION freeze sealed.
**Decision impact: none today** (that freeze was already invalidated as a preregistration, and no
measurement reads `materialize.py`), but the record's attribution is wrong and should be corrected
in a future append-only row.

### 5.3 [`observation`] `ceiling_permits_status = NO` on both bridge kills

`M1/output/status_derivation_review.csv` reports `ceiling_permits_status = NO` for
`TUP-CME-ES-H3-OFI-AGG` and `TUP-HYPERLIQUID-BTCPERP-H4-FUNDBASIS-MIX` (DEAD under a `NOT_ALIVE`
ceiling). This is **systemic, not bridge-specific**: the same flag appears on the three
pre-existing M2 `RECORDED_DECISION` kills. `M1/src/materialize.py:_ceiling_ok` requires
`ceiling == DEAD` for any DEAD row, while `candidate_gates.ceiling_violations` deliberately exempts
recorded kills — which is why the summary reports `ceiling_violations = 0` and `validate.py
--strict` passes. The review column therefore disagrees in letter with the rule the validator
enforces. **Decision impact: none** (no gate, count or verdict consumes the column), but the label
invites a false reading that the two kills were not permitted.

---

## 6. Negative controls (9 checks, all pass)

| id | control | result |
|---|---|---|
| NC1 | a **copy** of `candidate_tuples.csv` with `TUP-CME-NQ-H3-OFI-AGG` flipped to `ALIVE` | the canonical-state checker passes on the real file and **fails** on the copy, naming the `csv status counter` / `closure candidate_counts` check |
| NC2 | a **copy** of `evidence_ledger.csv` with the fabricated figures `0.0314159 bps` and `1,234,567` extra slots appended to EVD-0071 | the reverse trace passes on the real ledger (no unmatched numbers) and **reports both fabricated tokens as untraceable** in the copy |
| NC3 | a **copy** of the ledger with the headline `-0.0047336` changed to `-0.0047436` | the claim-vs-artifact numeric rule accepts the true value and **rejects** the perturbed one; the copy's perturbed token is reported unmatchable |

The checkers can fail, and they fail on exactly the perturbations introduced.

---

## 7. Read-only compliance and disclosed side effects

* All writes are under `.research/m2_bridge_001/verification/V4/`. The 16.7 MB spliced fixture and
  the fixture certificate/manifest copies live there too.
* `M2/src/basis_materiality --check` is verify-only and writes nothing.
* Two instructed commands have unavoidable side effects, both disclosed:
  1. the AUCTION v2 CLI writes its `--json-out`; it was pointed at
     `V4/auction_v2_rerun.json`, never at a sealed path (and the output proved byte-identical to
     the sealed file anyway);
  2. `M1/src/validate.py --strict` rewrites `M1/validation/report.{json,md}` with a fresh
     `generated_at`. Those files were already uncommitted-modified before this wave; the body is
     byte-deterministic modulo that field (proved by two consecutive runs,
     `_validate_run1.json` / `_validate_run2.json`). No canonical input changed.
* No canonical input was edited by this wave: nothing under `M1/data/**`, `M1/output/**`,
  `M1/src/**`, `M2/src/**`, `M2/tests/**` or `M2/experiments/**` was authored here. The only files
  outside V4 that changed at all are `M1/validation/report.{json,md}`, rewritten by the instructed
  `validate.py` run described above.

---

## 8. Import of V3's contested, rejected and unverified items

V3 left, per branch: A — 1 `CONTESTED` (the two instant sets) and 1 `UNVERIFIED` (pre-outcome
sealing); C — 2 `SUPPORTED_SCOPED` (the fee-rung choice and the 84 unresolved settlements) plus
1 `CONTESTED` (the premise that a reversed sign would change the verdict) and 1 `UNVERIFIED`
(sealing); B — 1 `SUPPORTED_SCOPED` (the entry book cannot be validated), 1 `CONTESTED` (the
degenerate far-band gate) and **1 `REJECTED`** (the freeze is not a valid preregistration).
This wave checks that they were carried, not dropped; §2's table maps each onto the canonical
rows. Two of them are carried as explicit *corrections of the verification brief itself* rather
than of the producer: the ES instant-set `CONTESTED` became the addendum (EVD-0074), and C's
sign-robustness `CONTESTED` is recorded on EVD-0072 limitation (iv) — the kill is sign-robust, and
the brief's premise is recorded as the thing that was wrong. Branch B's `REJECTED` preregistration
claim is carried as `INVALIDATED_FREEZE` on EXP-0012, SRC-0248 and OQ-0017. Nothing was converted
into a verdict: the auction row is `UNKNOWN` with no kill and no survival, and the parent auction
row is unrevived.

---

## 9. What remains UNVERIFIED, and what would close it

Nothing in the scope of this wave returned UNVERIFIED. The following are **outside** what retained
evidence can settle, and are inherited rather than new:

1. **Pre-outcome sealing for branches A and C** — the freeze precedes its results by artifact mtime
   and a live self-check, but no external anchor exists. *Closing evidence:* an RFC 3161 token or
   transparency-log entry over `freeze.sha256` taken before the run, or a git commit of the freeze
   that precedes the commit/mtime of `results.json`.
2. **The AUCTION freeze's live verifiability** — four sealed paths drift by construction (one file
   cannot hash to two values) and the seal recorded `00363c3a…` for `admission.py` while the tree
   now carries the BASIS-sealed `9f5862f7…`. The EVD records this as unavoidable and the freeze is
   already invalid. *Closing evidence:* a re-seal under the repaired tree as part of the
   warm-up-extended re-extract named in OQ-0017.
3. **The source-stream digests for AUCTION** — `raw` was streamed and not retained, so its 17.89 GB
   digest is a producer assertion (already noted in `admission_v2_result.json:notes`). *Closing
   evidence:* retain the source on the re-extract and hash it locally.
4. **`M1/src/materialize.py`'s pre-seal provenance** — attributable to `e64acb6` from git, but
   whether the AUCTION seal intended the pre- or post-`e64acb6` pipeline is not recorded. *Closing
   evidence:* a corrected append-only attribution row (see §5.2).

Everything else in this wave is reproduced from sealed artifacts by scripts whose hashes are listed
in §1.
