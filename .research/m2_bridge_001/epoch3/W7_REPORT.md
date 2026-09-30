# W7 — BASIS grid-identity repair (GOAL-M2-BRIDGE-001, epoch 3)

Scope: repair the count-identity defect in the data-admission engine so branch C's
completeness verdict rests on a **grid identity**. Files touched (only these):

| file | sha256 |
| --- | --- |
| `M2/src/admission.py` | `a11d38c6013b40d2bac76a50867e7acbea339e26105ea182621e4bb0c81b674e` |
| `M2/tests/test_admission.py` | `f98c6477ad0f3091714f2ab26667bae616457ca57560b772fff25c5d501fe7bc` |

No commits. No producer artifact, freeze, config, `M1/**` or sibling module was
modified. The three adversarial reproductions below were run **in memory** against
the real branch-C manifest; nothing was written to `M2/data/**`.

## 1. New check ids

| check id | what it proves | contract gate |
| --- | --- | --- |
| `intervals.grid_identity` | the **set** of observed bucket ids equals the exact expected set derived from the declared window + interval (per id domain: `records.timestamps`, `intervals[].id`) | `require_full_interval_coverage` + `interval_period_seconds` |
| `coverage.claim` | every declared coverage count/ratio is recomputable from the manifest's own record list | `coverage_units == "records"` (`BASIS_CONTRACT` only; `AUCTION`/`ES` unaffected) |
| `session.window_alignment` | the declared epoch window agrees with the manifest's redundant anchors (`window_start_utc`/`window_end_utc`, `coverage_date`) | any manifest declaring those keys |

Both new gates are inert for `AUCTION`/`ES` (free-form interval labels, coverage
counts not records), so no pre-existing fixture changes verdict.

## 2. The derivation rule (documented in `_expected_bucket_ids`)

```
ts_floor(t) = (t // period) * period              # floor onto the grid
n           = (ts_floor(end) - ts_floor(start)) // period + 1
expected    = { ts_floor(start) + k * period : k in 0 .. n-1 }
```

`period = contract["interval_period_seconds"]`, `start/end =
manifest.session.window_start_unix / window_end_unix`. One id per period, both
window ends inclusive. Derived from **declarations only** — never from the
observed ids, which would make the comparison vacuous. A non-aligned bound is
floored (total function); the misalignment itself is reported by
`session.window_alignment`.

Machine-readable reasons, all carrying `observed`/`expected`/`detail`:

| reason | severity | payload |
| --- | --- | --- |
| shifted ids | INVALID | `{"domain", "shifted_seconds": ±k*period}`, offset named as `+1h`/`+4h` in `detail` |
| unexpected / extra ids | INVALID | `{"domain", "unexpected_ids"[≤8], "unexpected_count"}` |
| duplicated ids | INVALID | `{"domain", "duplicated_ids"[≤8], "duplicated_count"}` |
| missing ids | INCOMPLETE | `{"domain", "missing_ids"[≤8], "missing_count"}` (a real gap is *absent evidence*) |
| declared-but-absent ids | INCOMPLETE | `{"domain", "declared_but_absent"...}` (`present: false` entries) |
| coverage claim mismatch | INVALID | `{"admitted", "supported_by_records"}`, `{"ratio", "supported_by_records"}`, `{"missing_buckets"}`, `{"duplicate_buckets"}`, `{"window_hours"}`, `{"records.count", "timestamps_declared"}` |
| window mirror / date mismatch | INVALID | `{"window_start_unix", "utc"}` vs `{"window_start_utc"}`; `{"coverage_date"}` vs derived UTC date |

The coverage cross-check fires only in the direction that hides a defect
(claiming **more** coverage than the records carry); a conservative claim below
what the records support is left to `intervals.coverage` /
`intervals.grid_identity`, which report the deficit as INCOMPLETE. That
asymmetry is what keeps `test_basis_window_cannot_shrink_post_hoc` (an honest
small claim over a shrunk interval list) at DATA_INCOMPLETE instead of flipping it
to INVALID.

## 3. Fixture verdicts

`python3 -m unittest M2.tests.test_admission -v` → **66 tests, all OK**
(54 before this change; the 12 added are the 5 BASIS fixture rows + 7 explicit
tests. The ticket's "existing 38 tests" predates the current fixture table — the
measured pre-change baseline in this working tree is 54, and all 54 still pass
unchanged.) Fixtures are tiny and synthetic; the engine is exercised against the
real artifact separately (section 4).

BASIS fixtures (`BASIS_FIXTURES`, evaluated against `BASIS_CONTRACT` on the
complete panel `build_valid_basis_panel`):

| fixture | attack | verdict | firing check |
| --- | --- | --- | --- |
| `basis_global_shift_4h` | every epoch field (records, interval ids, window bounds) shifted +4 h, mirrors left behind — internally consistent | DATA_INVALID | `session.window_alignment` |
| `basis_records_shortened_coverage_claim_intact` | record list truncated to 1, coverage still asserts 3/3, `missing_buckets: 0`, `records.count: 3` | DATA_INVALID | `coverage.claim` |
| `basis_interval_ids_shifted_one_hour` | every interval id offset +3600 s | DATA_INVALID | `intervals.grid_identity` (`shifted_seconds: 3600`) |
| `basis_midwindow_gap` | middle bucket genuinely absent, claim reduced honestly (`2/3`, `missing_buckets: 1`) | DATA_INCOMPLETE | `intervals.grid_identity` (missing id named) |
| `basis_window_moved_a_day_from_coverage_date` | window + mirrors + data moved +1 day, `coverage_date` left behind | DATA_INVALID | `session.window_alignment` (date anchor branch) |

Explicit tests:

* `test_basis_complete_panel_is_admitted` — positive control: complete panel →
  DATA_VALID with `reasons == []` and `notes == []`.
* `test_basis_grid_identity_is_load_bearing` — **negative control**: with
  `intervals.grid_identity` stripped from `admission.CHECKS`, the shifted-id
  fixture returns **DATA_VALID** (verdict degrades exactly as required); with the
  check present it is DATA_INVALID.
* `test_basis_shifted_ids_name_the_offset`, `test_basis_shortened_records_cannot_keep_the_coverage_claim`,
  `test_basis_midwindow_gap_records_the_missing_id`,
  `test_basis_global_shift_is_caught_by_the_declared_mirror` — pin the observed /
  expected payloads, not just the verdict.
* `test_basis_new_checks_stay_inert_where_the_contract_does_not_pin_them` — the
  new gates add no phantom findings to `AUCTION`/`ES` shapes.
* `test_every_check_has_a_fixture` extended to the BASIS table, so the advertised
  check inventory still cannot shrink silently (3 new ids, 3+ firing fixtures).

## 4. Engine verdict on the real branch-C manifest (READ-ONLY)

```
$ python3 -m M2.src.admission --manifest M2/data/derived_basis/manifest_basis.json --branch BASIS --root .
DATA_VALID  branch=BASIS  contract=ADMISSION-BASIS-C-v1  manifest=BASIS-FREE-PUBLIC-2026-03-05T11:00:00Z--2026-09-28T23:00:00Z
  no findings
exit=0
```

**DATA_VALID, no findings, no notes.** The producer's artifact survives the
stricter identity checks; independently re-derived values:

* `window_start_unix = 1772708400` = `2026-03-05T11:00:00Z` — equals
  `window_start_utc` and the UTC date of `coverage_date = "2026-03-05"`;
  `window_end_unix = 1790636400` = `2026-09-28T23:00:00Z` equals
  `window_end_utc`. `session.window_alignment`: no findings.
* expected grid `n = (1790636400//3600 - 1772708400//3600) + 1 = 4981`;
  `intervals[].id` (all `present: true`) and `records.timestamps` both equal that
  set exactly, spaced 3600 s. `intervals.grid_identity`: no findings.
* `coverage = {qualified: 4981, admitted: 4981, ratio: 1.0, window_hours: 4981,
  missing_buckets: 0, duplicate_buckets: 0}`, `records.count = 4981` =
  `len(records.timestamps)`. `coverage.claim`: no findings.

The three attacks, replayed **in memory** on this real manifest (no file written),
old verdict measured by running the pre-fix check registry (the three new ids
removed) on the identical manifest:

| attack on the real manifest | old verdict | new verdict | firing check |
| --- | --- | --- | --- |
| all epoch fields +4 h (window + ids + records), mirrors untouched | DATA_VALID | DATA_INVALID | `session.window_alignment` — `window_start_unix 1772722800 (2026-03-05T15:00:00Z)` vs `window_start_utc 2026-03-05T11:00:00Z`, `+14400 s (+4h)` |
| `records.timestamps` 4981 → 2, coverage claim untouched | DATA_VALID | DATA_INVALID | `coverage.claim` — `records.count 4981` vs `timestamps_declared 2`; `admitted 4981` vs `supported_by_records 2`; `ratio 1.0` vs `0.00040153` (plus `intervals.grid_identity` INCOMPLETE, 4979 missing ids) |
| every interval id +3600 s (records untouched) | DATA_VALID | DATA_INVALID | `intervals.grid_identity` — `shifted_seconds: 3600`, `+1h`; with that check stripped the same manifest returns DATA_VALID |
| window + mirrors + data moved +1 day, `coverage_date` untouched (self-consistent, wrong absolute window) | DATA_VALID | DATA_INVALID | `session.window_alignment` — `coverage_date "2026-03-05"` vs derived `2026-03-06` |
| genuine mid-window gap (bucket 2000 dropped, claim reduced to 4980/4981, `missing_buckets: 1`) | DATA_INCOMPLETE | DATA_INCOMPLETE | `intervals.grid_identity` missing id `1779908400`; `intervals.coverage` `present 4980` vs `buckets_in_window 4981`; `coverage.contract` `ratio 0.99980 < 1.0` |
| post-hoc window shrink (ids and record list cut to 10, `window_hours: 10`, `records.count: 10` kept, window bounds kept) | DATA_INCOMPLETE | DATA_INVALID | `coverage.claim` (`records.count 4981` vs `timestamps_declared 10`, `admitted 4981` vs `supported_by_records 10`), plus `intervals.grid_identity`, `intervals.coverage` |

The unmodified real manifest is DATA_VALID in both registries: the repair changes
verdicts only for manifests that actually violate a grid identity or overstate a
coverage claim.

So: a genuine gap is still reported as a gap, a complete panel still passes.

## 5. Contract expressiveness (BLOCK condition check)

No contract gap. The declared BASIS contract carries everything the derivation
needs: `interval_period_seconds = 3600` (the grid step),
`require_full_interval_coverage = true` (the demand), `timestamp_semantics =
"unix_seconds_utc_hour_floor"` with `timezone = "UTC"` (the id domain), and
`require_session_window = true` so the manifest must declare
`window_start_unix` / `window_end_unix`. One contract key was added —
`coverage_units: "records"` — to state explicitly that the coverage block counts
records, which is what licenses the recompute; that is a declaration of a fact the
BASIS contract already assumed (its frozen formulation says "100% paired hourly
buckets"), not an invention.

Stated limit (documented in `_check_session_window_alignment`'s docstring rather
than pretended away): if a manifest shifts the data, the window bounds **and** the
redundant mirrors (`*_utc`, `coverage_date`) together, the shift is not detectable
from the manifest alone — the declared contract pins no absolute clock independent
of the window the data declares. For a contract timestamping in local
wall-clock nanoseconds since midnight (AUCTION) there is no epoch to align at all;
there the frozen coverage date and declared session bounds are the only anchors.
Both cases are recorded as notes, never as passes.

## 6. Out-of-scope finding (not patched — flagged for the main agent)

While probing the new checks I found a **pre-existing** robustness hole, present
with the pre-fix registry as well, outside this ticket's defect:

```
$ python3 - <<'PY'   # in-memory only, no file touched
panel = build_valid_basis_panel(root); panel["records"]["timestamps"][1] = "2023-07-05T01Z"
admission.evaluate(panel, admission.BASIS_CONTRACT, ctx)
PY
TypeError: '<' not supported between instances of 'str' and 'int'
  admission.py:800 in _check_records_session_window   (min(timestamps), max(timestamps))
```

A timestamp series mixing numbers and strings crashes `records.session_window`
(also reachable from `ordering.causal` / `timestamps.monotonic`) instead of
yielding one of the three declared states — i.e. `evaluate` is not total for a
malformed series. It is unrelated to the count-vs-identity defect, so per the
ticket's "additive fix only" constraint I did **not** widen this repair to patch
it; the three named attacks are all rejected without touching that code path. The
engine's new grid check is itself type-safe (`_as_epoch_seconds` guards every
comparison).
