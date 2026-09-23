# Repository state consistency notes (M2-0)

Recorded as required by the M2-0 handoff section 0: where repository prose and
machine-readable state disagree, the disagreement is recorded here and the
**machine-readable state is used** for this pass. Nothing in M1 was redesigned,
and no M1 status was changed by M2-0.

## 1. Verified consistent

Checked directly against the artifacts, not from memory:

| claim | source | verified |
|---|---|---|
| candidate `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` is WEAK, `NOT_ALIVE`, gate vector KG1 PASS / KG2 BLOCKED / KG3 BLOCKED / KG4 PASS / KG5 PASS | `M1/output/candidate_gate_status.csv`, `M1/output/M1_CLOSURE_STATUS.json` gate vectors | yes |
| counts ALIVE 0 / WEAK 5 / UNKNOWN 16 / DEAD 7 over 28 registered rows | `PROJECT_STATE.md` vs `candidate_gate_status.csv` | yes |
| closure terminal state `M1_OPEN`; M1-B and M1-D1 not authorized | `M1_CLOSURE_STATUS.json` | yes |
| universe rule `NASDAQ-LARGETICK-QIMB-UNIV-v1` effective status APPROVED, `point_in_time_membership_status = REQUIRED_DATA_NOT_SECURED` | candidate spec JSON | yes |
| Nasdaq remove fee 0.0030 USD/share and rebate 0.0018/0.0013 USD/share | `M1/data/venue_facts.csv` (SRC-0203) | yes, and re-confirmed against Nasdaq's live trading price list on 2026-09-22 |

## 2. Inconsistencies found

### 2.1 Literature URLs are described as unrecoverable, but they are in the registry
`PROJECT_STATE.md` finding 6e states that the two KG1-passing Nasdaq rows rest on
report-mediated sources whose "URLs are not recoverable from the repository
(`EVD-0012`, `EVD-0014`)", and that re-deriving those citations is the cheapest way
to make the only positive gate results checkable (UNK-0023).
`M1/data/source_registry.csv` in fact carries URLs for the relevant records:

* `SRC-0238` — https://arxiv.org/abs/1512.03492 (Queue Imbalance as a One-Tick-Ahead Price Predictor, arXiv record)
* `SRC-0241` — https://arxiv.org/pdf/1512.03492 (author full text PDF)
* `SRC-0239` — https://doi.org/10.1080/14697688.2018.1489139 (micro-price, publisher metadata)

Consequence for this pass: the mechanism citation behind the candidate's KG1 can be
reached from machine-readable state alone. **M2-0 does not change M1 status or
resolve UNK-0023**; it records that the machine-readable state is more complete than
the prose that flags it as unrecoverable.

### 2.2 Historical ITCH coverage start differs between two primary pages
* repo-verified `SRC-0201` (Nasdaq Historical TotalView-ITCH SFTP access specification): files from **2007-08-13**;
* nasdaq.com product page retrieved 2026-09-22: historical data **back to 2014**.

Both are recorded in the cost ledger's known-unknowns and in
`M2/output/DATA_ACQUISITION_PLAN.md`. Unresolved; no number is invented.

### 2.3 KG3 blocking reason is now partly outdated in substance (M1 unchanged)
`M1_CLOSURE_STATUS.json` blocks KG3 for this candidate with "No verified fee
component exists for this venue". M1's own `venue_facts.csv` (SRC-0203) already
carries the verified Nasdaq remove fee, and this pass additionally verified the
reference broker path from primary pages (see `M2/config/cost_ledger_v1.json`).
The pass therefore reports a verified venue component and a verified reference-path
component. **M1's gate values are untouched**; changing them is an M1 decision, not
an M2-0 one.

### 2.4 Dataset identity for the M2-0 run
Neither `PROJECT_STATE.md` nor the closure artifacts record any order-level dataset
for this candidate; the M1 data-feasibility row is `L3_available = FAIL` for the
L1-only history product and `historical_feed = BLOCKED` for order-level history.
M2-0 therefore used a free public Nasdaq sample day and labelled it DEVELOPMENT
(never a holdout), and produced `DATA_ACQUISITION_PLAN.md` for the paid path.
