# W10 — ES matched-instant addendum, closeout repair recording, and the single canonical regeneration (GOAL-M2-BRIDGE-001, epoch 6)

Role: repair + record + regenerate. Two verified integrity defects were closed rather than merely
noted: the ES record's instant-set inconsistency by an addendum, and the basis freeze-verifiability
drift by recording the restoration W9 performed. The auction artefact defect V3 found is recorded
too. This was the campaign's single regeneration pass; W9 did not touch `M1/` and did not run
`materialize.py` or `validate.py`. No commit, no push, no sealed artefact modified.

## 1. Deliverables

| artefact | path | sha256 |
|---|---|---|
| addendum | `M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.json` | `ba3717274896f04100a2674e2735265e8ee76e179f11611b73c7078fba764cf1` |
| addendum script | `M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.py` | `e7d8405b745063c0f004abbaba9ac0055f897d135aeb5ac7f609f5ad01979dd0` |
| repair record (ES) | `M1/src/corpus/patches/p0013_es_matched_instant_addendum.py` → `M1/work/patches/P-0013.json` | patch `P-0013` |
| repair record (basis) | `M1/src/corpus/patches/p0014_basis_freeze_restoration.py` → `M1/work/patches/P-0014.json` | patch `P-0014` |
| artefact-defect record (auction) | `M1/src/corpus/patches/p0015_auction_artifact_defect.py` → `M1/work/patches/P-0015.json` | patch `P-0015` |

The addendum script re-runs byte-identically (`diff` clean) and is deterministic: it reuses
`M2/src/es_materiality.py` at its sealed hash `2a07bbd4…` unchanged (its loaders, `build_panel`,
`state_direction`, `quote_mask`, `observation_mask`, `gross_markout_bps`), on the sealed contract
`42a158c5…` and the admitted inputs. The addendum JSON records the script's path and sha256 itself.

## 2. The ES instant-set defect, closed

V3 claim B6': the published `unconditional_markout_bps` is the mean over the **598** quote-available
slots while the conditional gross is over the **583** non-zero-state observations. Reading the two
published columns side by side invited a same-population comparison the denominators do not support.

Recomputed on EXACTLY the conditional instants (both variants and all denominators stated):

| horizon | quote-available slots | conditional observations | unconditional over quote-available slots (published) | unconditional over the conditional instants | delta | conditional gross |
|---|---|---|---|---|---|---|
| 1 s (primary) | 598 | 583 | +0.0156746 bps | **+0.0208001 bps** | +0.0051255 | -0.0047336 bps |
| 5 s | 594 | 579 | +0.0631091 bps | **+0.0547556 bps** | -0.0083535 | -0.0014608 bps |
| 15 s | 584 | 569 | +0.1340817 bps | **+0.1240628 bps** | -0.0100189 | +0.0502825 bps |

The conditional state is BELOW its own matched-instant unconditional baseline at every horizon. The
1 s figures reproduce V3 exactly (+0.0208001 matched-instant, +0.0156746 published, 0.0051 apart);
the addendum also reproduces the published conditional gross, published unconditional and
observation counts at all three horizons (agreement asserted at 1e-12), so it is anchored to the
frozen record rather than to a re-implementation.

**Neither figure changes the verdict.** The kill fires on the conditional primary-horizon gross
being non-positive (`PRIMARY_HORIZON_GROSS_NOT_POSITIVE`) and, independently, on `hi` (0.0403358)
`<= C0` (0.5770016). The unconditional markout is the side-ignoring null baseline; it is not an
input to `classify_materiality`, and the verdict stays `KILL_MATERIALITY` with scope
`SAMPLE_SCOPED_DEVELOPMENT_KILL`. The frozen `results.json` keeps the quote-available-slot variant
in the field it was computed for — the addendum corrects the *comparison*, not the measurement.

Canonical recording (P-0013, decision `NO_CHANGE`, no gate move): new source `SRC-0249` (the
addendum artefact), new evidence `EVD-0074` (the full 1/5/15 s table and the explicit
verdict-unchanged statement), and an update to `SRC-0246.limitations` so the ES source no longer
flags the gap without the matched-instant numbers.

## 3. The basis freeze-verifiability defect, closed and recorded

W9 restored `M2/src/admission.py` byte-exactly to the sealed `9f5862f7…` and moved the unrelated
auction v2 contract verbatim into the new `M2/src/admission_auction.py` (`84fd3270…`), behind the
engine's existing `checks` seam. The basis freeze now verifies in place again.

Canonical recording (P-0014, decision `NO_CHANGE`): new source `SRC-0250` (the restoration, receipted
at `W9_REPORT.md`), new evidence `EVD-0075` (the restoration and its consequence), and an update to
`SRC-0247.limitations`. The honest consequence is stated rather than hidden: the **AUCTION** seal
recorded the drifted bytes (`00363c3a…`), so it now drifts in the **opposite** direction for
`admission.py`, together with the two auction consumers that had to be re-pointed
(`seal_freeze.py`: `813a1612…` → `e4e6e024…`; `test_auction_materiality.py`: `940c5b61…` →
`b08e7945…`). One file cannot hash to two values, and the basis seal is the live one; the auction
branch's freeze was already an `INVALIDATED_FREEZE`, so no live verdict depends on it.

## 4. The auction artefact defect V3 found, recorded

`M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/freeze.json` carries
`as_run_deviations_from_freeze = "recorded in results.json:as_run_deviations_from_freeze …"`, but the
sealed `results.json` has **no such key** (`has(...) == false`). The real record is the standalone
`as_run_deviations.json` beside the freeze (B5-A1..A5, complete and unmodified), whose own statement
explains why it lives there rather than inside `results.json`.

Canonical recording (P-0015, decision `NO_CHANGE`): an update to `SRC-0248.limitations` carrying the
stale pointer, the four drifted AUCTION `run_inputs.json` paths, and the note that
`M1/src/materialize.py`'s drift is **pre-existing** and unrelated (the pipeline file changed after
the auction seal). No verdict, gate or figure depends on the pointer.

## 5. The single regeneration and validation pass

```
$ python3 M1/src/materialize.py
{"candidates": 30, "status": {"total": 30, "ALIVE": 0, "WEAK": 3, "UNKNOWN": 15, "DEAD": 12}, …}

$ python3 M1/src/validate.py --strict
{"overall": "PASS", "failures": 0, "checks": 19}

$ python3 -m unittest discover -s M1/tests -t .
Ran 99 tests in 0.098s
OK
```

Patch accounting after the pass: **15 proposed / 15 applied / 0 rejected** (12 from W8 + `P-0013`,
`P-0014`, `P-0015`). Canonical counts: evidence records 72 → **74**, source registry 99 → **101**,
candidate status distribution unchanged (ALIVE 0 / WEAK 3 / UNKNOWN 15 / DEAD 12), 0 ceiling
violations. No gate moved and no candidate's status changed: `EVD-0074` and `EVD-0075` are
`NEUTRAL` records that are appended to the two dead rows' evidence trails and read by the gate
engine (e.g. the ES `KG4_HALF_LIFE` reason now cites `EVD-0074`) without altering any gate value.

## 6. Files changed

New:

- `M2/experiments/M2-BRIDGE-ES-H3-OFI/addendum_unconditional_matched_instants.{json,py}`
- `M1/src/corpus/patches/p0013_es_matched_instant_addendum.py`,
  `p0014_basis_freeze_restoration.py`, `p0015_auction_artifact_defect.py`
- `M1/work/patches/P-0013.json`, `P-0014.json`, `P-0015.json`

Regenerated by the pass (timestamp/derived churn plus the three recorded effects):

- `M1/data/evidence_ledger.csv` (+EVD-0074, +EVD-0075),
  `M1/data/source_registry.csv` (+SRC-0249, +SRC-0250, SRC-0246 & SRC-0248 limitations),
  `M1/data/dead_candidates.csv`, `M1/data/candidate_tuples.csv`, `M1/data/discrepancies.csv`
- `M1/output/*` (closure status, readiness, blocked, state summary, evidence coverage, gate trace),
  `M1/validation/report.{json,md}`
- `M1/work/cards/*.json`, `M1/work/frontier.json`, `M1/work/m2_specs/registry.json`,
  `M1/work/patches/P-0001..P-0012.json` (re-emitted)
- root renderings: `EVIDENCE_LEDGER.csv`, `DEAD_ENDS.md`, `DISCREPANCIES_AND_UNKNOWNS.md`,
  `PROJECT_STATE.md`
- `M1/src/corpus/patches/__init__.py` (registers the three new patch modules)

`EVIDENCE_LEDGER.csv` is byte-identical to `M1/data/evidence_ledger.csv` (validator V11).

## 7. Deliberately left unchanged

- **Every sealed artefact.** `freeze.json`, `freeze.sha256`, `run_inputs.json`, `results.json`,
  `certificate.json`, `entry_prints.json`, `signal_extract.json` in all three bridge experiments are
  untouched; the ES addendum is a companion file, not an edit to `results.json`.
- **`M2/src/es_materiality.py` and `M2/src/basis_materiality.py`** — the addendum reuses the frozen
  module rather than changing it.
- **`M1/src/validate.py` and `M1/src/materialize.py`** — pipeline rules, never edited. The
  `M1/src/materialize.py` drift against the AUCTION seal (`bdec4cc1…` sealed vs `ad1d18d2…` on the
  tree) is pre-existing, unrelated to this pass, and recorded rather than repaired.
- **`EVD-0072`'s stale limitation (iii)** — evidence rows are append-only in this corpus, so the row
  keeps the text that says the basis freeze drifted; the correction is recorded as `EVD-0075` and on
  `SRC-0247`, which explicitly names the superseded limitation.
- **The AUCTION freeze's stale deviation pointer** — the freeze is read-only, so the pointer is
  recorded on `SRC-0248` rather than corrected in place.
- **The published ES `unconditional_markout_bps` field** — left in place with both denominators now
  documented beside it.

## 8. Verification boundary

- `validate.py --strict`: PASS, 0 failures, 19 checks; M1 suite 99/99; all 15 patches VERIFIED.
- The addendum is a recomputation of the frozen arithmetic, not independent evidence; it is marked
  `NEUTRAL`, is not an input to `classify_materiality`, and cannot move either fired arm.
- The basis restoration is an infrastructure repair: it changes no number, and the basis kill stands
  exactly as recorded. Its own verification (`--check`, the rehash sweep, the 40-test auction suite,
  the 332-test M2 suite) is W9's receipt, quoted, not re-run here.
- No commit, no push: the working tree holds all of the above for the controller to commit.
