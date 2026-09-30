# W6 — Canonical registration + ES methodology correction (GOAL-M2-BRIDGE-001, epoch 2)

Scope: canonical M1 bookkeeping only — register the operator-authorized narrow auction candidate
and record the ES account-cost methodology correction. No research result is asserted: no data
source admitted, no sample owned, no cost verified, no gate passed on admission grounds, no M2 file
touched, no freeze sealed, no commit created.

## 1. Verification (all must-pass checks)

| check | command | result |
|---|---|---|
| materialize | `python3 M1/src/materialize.py` | OK — 30 candidate rows, `ALIVE=0`, `gate_eligible=0` |
| validator | `python3 M1/src/validate.py --strict` | **PASS, 0 failures** (19 rule groups / 19 check rows; `M1/validation/report.{json,md}`) |
| unit tests | `python3 -m unittest discover -s M1/tests -t .` | **OK — 99 tests, 0 failures** |
| campaign regen | `python3 M1/orchestrator/campaign.py compile` | OK — `M1/work/action_frontier.json` refreshed (5 actions, 1 external) |
| tree | `git status --short`, `git log --oneline -1` | no commit created; HEAD still `ccd637d` |

No validator rule was weakened, added or removed, and no test was edited or deleted.

## 2. Change 1 — narrow auction candidate registered

New row `TUP-NASDAQ-CLOSE-H4-LATENOII-AGG` (id as assigned; the mechanism column still names
`MECH-AUCTIONIMB`, and the id's `LATENOII` token follows the existing descriptive-token style of
`MICROOFI`/`QUEUEPOS`/`L1ONLY`, so no convention-forced deviation was needed):

| field | value |
|---|---|
| class / venue / horizon / mechanism / style | `TUPLE` / `VEN-NASDAQ-AUCTION` / `H4` (15 s–5 min) / `MECH-AUCTIONIMB` / `AUCTION` |
| universe | Nasdaq Closing Cross, same-day TotalView-ITCH Stock Directory (frozen `RESOL-001`) |
| computed gates | KG1 `BLOCKED` (KG1-R4), KG2 `BLOCKED` (KG2-R0), KG3 `BLOCKED` (KG3-R4), KG4 `BLOCKED` (KG4-R5), KG5 `PASS` (KG5-R5) |
| status | `UNKNOWN` — registered and blocked pending admission; ceiling `NOT_ALIVE` (no `ALIVE`, no death, no kill recorded); `status_source_id` is `UNKNOWN` because no source artifact carries this row's status (the M1-A ledger does not contain it), so provenance lives in `status_basis`, `notes`, `report_row_ref` and D-0041 |
| declared blockers | `UNK-0004 · UNK-0005 · UNK-0006 · UNK-0018 · UNK-0020 · UNK-0027` (parent ids; materialize expands them to the scoped children `UNK-0018-NASDAQ`, `UNK-0027-AUCTION`; registry additionally attributes `UNK-0028`) |

Ancestry is explicit in the row's `notes`: `descended_from=TUP-NASDAQ-ANYCAP-H4-AUCTION-AGG`,
`relation=NARROW_REFORMULATION` (the corpus already records lineage in `notes`, see `TUP-NASDAQ-LARGETICK-H2-QIMB-PAS`; adding a lineage column would have created a second convention). The
parent row is byte-for-byte unchanged in substance (same id, `UNKNOWN`, not dead, not revived); it
stays as historical provenance for the broad ANYCAP formulation, and the new row inherits none of
its verdict and no cleared prerequisite. KG5 `PASS` is a computability verdict (signal, outcome,
null, kill rule fixed before any result) and is stated as such in the row's `notes` and
`status_basis`; the universe rule `NASDAQ-CLOSING-CROSS-PIT-STOCK-DIRECTORY-v1` is declared in the
spec but has **no** approved spec artifact, so the unit of analysis is not canonically approved.

No auction cost conclusion was drawn: `VEN-NASDAQ-AUCTION` has no verified fee value, so
`required_round_trip_fee_bps_for_style = UNKNOWN` and `full_break_even_status = BLOCKED_UNKNOWN_COMPONENTS`. No data-feasibility row was authored for the row (precedent: `…H2-QIMB-PAS`), so KG2
reports `KG2-R0` and the row's `notes` points to the parent's authored assessment.

Spec retarget: `M1/work/reselection_specs/TUP-NASDAQ-CLOSING-AUCTION-LATE-NOII.json` — `candidate_id`
now the new row, plus an `ancestry` block (`descended_from`, `relation`, decision) and a
`provenance_note` recording the retarget. Frozen formulation text is unchanged (diff: 7 insertions,
1 deletion).

## 3. Change 2 — ES methodology correction (D-0042)

Replaces "exact account-level all-in cost required before the gross-materiality precursor" with
causal admitted data + verified structural cost **C0** + parameterized unresolved cost **C1**
(unknown never zero) + break-even residual **C\***; exact broker/FCM/account costs become the gate
before shadow/micro-live. Methodology-stage correction only: timestamps/ordering, identity,
historical completeness, venue mechanics, mandatory fees and execution realism unchanged; no data
admitted, no cost verified, no gate moved.

Applied to `M1/work/reselection_specs/TUP-CME-ES-H3-OFI-AGG.json`: `decision_question`,
`friction_comparator`, `primary_metric`, `kill_criterion`, `continuation_criterion`,
`external_prerequisites` (account schedule removed), plus two explicit records — `account_cost_gate`
and `methodology_correction` (what was replaced, what is unchanged, that nothing is admitted).

## 4. Files

Hand-edited (declarative corpus + live M1 code/prose):

| file | change |
|---|---|
| `M1/src/corpus/tuples.py` | new candidate row + ancestry/limitation notes; `add()` gains an explicit `status_source_id` (default `SRC-0011`, unchanged for every existing row) so a later-registered row cannot borrow the M1-A ledger's status provenance |
| `M1/src/materialize.py` | generated `status_basis` wording: only a row whose `status_source_id` is `SRC-0011` may say "M1-A label preserved"; the new row says "registered status preserved (no M1-A ledger row)" |
| `M1/src/corpus/staging.py` | `UNK-0001` card: title/required answer/evidence/success/kill/reason → C0 verified + declared C1 |
| `M1/src/corpus/unknowns.py` | `UNK-0001` claim/evidence corrected; new row added to `UNK-0004`, `UNK-0005`, `UNK-0020` scope; `OQ-0002` corrected |
| `M1/src/corpus/child_issues.py` | `_NASDAQ_ROWS` += new row; `UNK-0027-AUCTION` re-scoped (what the freeze settles, what stays open); `UNK-0009-ECON-CME-MEASURED` = pre-shadow account-cost gate |
| `M1/src/corpus/experiments.py` | `EXP-0005` (cost sensitivity) dataset = C0 + declared C1 range |
| `M1/src/readiness.py` | two generated-report strings: C0/C1 + pre-shadow gate |
| `M1/orchestrator/frontier.py` | `CLUSTERS["NASDAQ_EQUITY"]` += new row (keeps cluster mapping total) |
| `M1/orchestrator/resolvers.py` | `UNK-0001` request content (C0 ask, C1 rule, pre-shadow clause) and `COST_SENSITIVITY` spec dataset/baseline |
| `M1/orchestrator/campaign.py` | ES closure prerequisites + ES minimum-precursor result text |
| `M1/work/reselection_specs/TUP-NASDAQ-CLOSING-AUCTION-LATE-NOII.json` | retarget + ancestry + provenance note |
| `M1/work/reselection_specs/TUP-CME-ES-H3-OFI-AGG.json` | corrected friction comparator/metric/kill/continuation + `account_cost_gate` + `methodology_correction` |
| `DECISIONS.md` | `D-0041` (auction registration, ancestry, non-inheritance), `D-0042` (ES correction, supersedes the D-0039/D-0040 account-cost clause) |
| `PROJECT_STATE.md` | hand-authored prose only: ES H1 blocker cell, ES next required external action, UNKNOWN-row enumeration (14 → 15) |

Regenerated by `materialize.py` (never hand-edited): `M1/data/{candidate_tuples,discrepancies,open_questions,experiments,execution_envelopes,kill_gates}.csv`;
all 17 `M1/output/*` tables/reports; `M1/work/{frontier.json,cards/*.json,external_requests/*.md,m2_specs/*,patches/P-*.json}`;
`M1/validation/report.{json,md}`; `PROJECT_STATE.md` generated blocks; root mirrors
`DISCREPANCIES_AND_UNKNOWNS.md`, `OPEN_QUESTIONS.md`, `WATCHLIST.md`, `EXPERIMENTS.csv`.
Regenerated by `campaign.py compile`: `M1/work/action_frontier.json`.
Unavoidable side effects of running the required commands: tracked `__pycache__/*.pyc` and the
`gate_recompute_date` column now carry the new generation timestamp.

## 5. Rules that needed attention (data fixed, rule untouched)

1. `test_unknown_registry_ids_are_unique_and_referenced` — candidate `blocking_issue_ids` must use
   registry-parent ids (`UNK-0018`, `UNK-0027`), not child ids; children are attached by
   `expand_parent_refs`. First attempt declared child ids and failed. Fixed the **row's data**.
2. `test_cluster_mapping_is_total` — a new row is `UNCLUSTERED` until it is added to
   `frontier.CLUSTERS`. Fixed the cluster table, not the test.
3. V3 gate ceiling — the new row's declared vector must be `BLOCKED` on KG1–KG4 (no `FAIL`, so no
   death; no all-PASS, so no eligibility). Declared vector equals the computed vector
   (`gates_diverged_from_m1a = NONE`).
4. V2/V10 — the correction introduced no cost number: C0 stays unverified (no numeric cell
   populated), C1 is a declared range in a spec, and the auction envelope stays fully `UNKNOWN`.
   Neither rule needed weakening.
5. Status provenance (self-imposed, no rule flagged it) — `add()` hard-coded `status_source_id =
   "SRC-0011"`, and the generated `status_basis` asserted "M1-A label preserved" for every blocked
   row. Both are false for a row registered after the M1-A pass, so the row now declares
   `status_source_id = UNKNOWN` and `apply_computed_gates` distinguishes ledger rows from
   later-registered ones. Existing rows keep byte-identical wording.

## 6. Deliberately not changed (with reason)

- `M1/output/M1_CANDIDATE_RESELECTION.{md,json}` (dated 2026-09-28 record of D-0039) still states the
  superseded account-cost ordering. `DECISIONS.md` is append-only and D-0042 names the clause it
  replaces; rewriting a dated decision record was judged worse than recording the supersession.
- `M1/work/patches/P-0003.json` / venue fee notes ("pending a broker/FCM quote …") are the dated
  record of the exhausted public fee search; they remain the practical path to a *verified* C0 and
  assert no ordering.
- `M1/work/external_requests/RESOLUTION_SPRINT_001_HUMAN_ACTIONS.md` and
  `.research/**` epoch-1 reports are dated records; the spec path they name is unchanged.
- `campaign.py`'s `ACT-E01-DIVERSITY-AUCTION` still targets the parent auction row: the ticket
  authorizes no action retarget, and the parent stays a registered (non-dead) row. Flagged for the
  operator: the operative formulation is now the narrow row, so that action's target is worth
  revisiting in a later bookkeeping pass.
- No universe-rule spec artifact was created under `M1/hypotheses/candidate_specs/`: approving (or
  proposing) a universe rule is a separate canonical act, and `load_universe_specs` only admits
  `APPROVED` artifacts, so adding a file would not have changed any gate.

## 7. Residual state after the change

`ALIVE=0`, `TEST_NOW=NONE`, candidate rows 30 (25 tradable tuples + 5 non-tuple registrations),
`UNKNOWN=17 / WEAK=3 / DEAD=10`, M1 frontier 27 items, `gate_eligible=0`, `next_autonomous_branch =
TUP-COINBASE-BTCUSD-H3-MICROOFI-AGG` (mechanical field, unchanged in kind). The new row is
`DISPATCHABLE`-classified by the closure metrics like the other blocked-but-not-externally-closed
rows; it earns no promotion and opens no budget.
