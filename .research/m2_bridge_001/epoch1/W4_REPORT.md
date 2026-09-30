# W4 — DATA_ADMISSION ENGINE (GOAL-M2-BRIDGE-001, Epoch 1)

Status: complete. Data/tooling only, no economics, no strategy logic. Everything
uncommitted; no existing module, freeze artefact or M1 rule was touched.
Written 2026-09-29T22:02Z (suite accepted 2026-09-29T22:01:40Z).

## Deliverables

| artifact | note |
|---|---|
| `M2/src/admission.py` (new) | engine + three built-in branch contracts |
| `M2/tests/test_admission.py` (new) | 25 adversarial fixtures + feed-shape, boundary and CLI tests |
| `.research/m2_bridge_001/epoch1/W4_REPORT.md` | this file |

Run:

```
python3 -m unittest M2.tests.test_admission -v        # 72 tests, <0.2 s, OK
python3 -m M2.src.admission --manifest <manifest.json> --branch AUCTION|ES|BASIS --root .
# exit code 0 only for DATA_VALID; --json-out writes the full verdict
```

## Contract

Input: a **manifest** (what the producing worker claims, incl. raw/derived hashes)
plus a declarative **branch contract** (what must be true of data that may enter a
freeze). Output: exactly one of `DATA_VALID`, `DATA_INVALID`, `DATA_INCOMPLETE`,
with machine-readable reasons `{check, severity, observed, expected, detail}`.

Severity rule, applied uniformly:

* `INVALID` — evidence is present and **contradicts** the contract (hash mismatch,
  wrong session date, out-of-order event, duplicate/gapped sequence, wrong
  instrument, declared partial archive, ...).
* `INCOMPLETE` — the evidence needed to make the comparison is **absent** (missing
  required field, missing hash, missing interval, coverage below the declared
  tolerance, missing object on disk, ...).

Precedence: any INVALID wins; else any INCOMPLETE; else DATA_VALID. A check that
cannot run never yields DATA_VALID, so a missing hash or an unmet coverage contract
is refused rather than silently accepted. The engine is read-only: declared
`sha256` values are recomputed from disk and never written. Contracts contain data
requirements only; `test_contracts_carry_no_economics` asserts no economic key
(pnl/markout/hurdle/fee/carry/kill/...) appears in any built-in contract.

## Check inventory (23; `admission.CHECK_IDS`)

| check | decides | classes raised | fixture(s) |
|---|---|---|---|
| `manifest.load` | manifest parses to a JSON object | INCOMPLETE | missing-manifest-file test |
| `manifest.sections` | contract-required sections exist and are non-empty | INCOMPLETE | section_absent |
| `source.identity` | required provenance fields non-empty; pinned provenance honoured | INC / INV | source_field_absent |
| `schema.identity` | schema contract id and container format | INC / INV | schema_mismatch |
| `files.required` | every required file role is declared | INCOMPLETE | missing_file_role |
| `files.hash` | declared sha256 recomputed from disk, pinned hash honoured, byte count; `retained:false` entries require upstream_url/upstream_sha256/bytes and the contract's `allow_unretained_files` | INV / INC | hash_mismatch, missing_hash, unretained_source_* |
| `archive.completeness` | declared status is complete; `expected_bytes` equals disk size | INV / INC | partial_archive |
| `fields.required` | required fields declared; field names unique | INC / INV | missing_required_field |
| `fields.types` | types inside the contract vocabulary and type map | INV / INC | type_outside_vocabulary |
| `timestamp.identity` | timestamp field semantics/identity/timezone metadata | INV / INC | wrong_timestamp_semantics |
| `timezone.contract` | session timezone equals the contract timezone | INV / INC | unexpected_timezone |
| `session.identity` | coverage date (or allowed set); declared session window | INV / INC | wrong_session_date |
| `session.completeness` | contract-declared stream-completeness markers (container integrity, zero framing/trailing, final frame), an anchor artifact carrying them, an optional terminating-frame flag, and the required final session event | INV / INC | missing_terminating_frame, stream_completeness_* |
| `records.session_window` | every event timestamp inside the declared session bounds | INV / INC | event_outside_session |
| `instrument.identity` | symbol/venue vs contract; declared secondary instruments inside the contracted product family; record symbols subset of the PIT universe | INV / INC | wrong_instrument, symbol_outside_universe, secondary_instrument_outside_family |
| `universe.pit` | PIT flag true, frozen universe rule id, non-empty members | INV / INC | universe_not_pit |
| `ordering.causal` | event time non-decreasing (causal order) | INV / INC | out_of_order_event |
| `timestamps.monotonic` | strict monotonicity where the contract expects it | INV / INC | duplicate_timestamp |
| `sequence.integrity` | contiguity from the declared or pinned start: gap, duplicate, regression; in probe mode also the whole-window density identity `last - first + 1 == total` | INV / INC | duplicate_sequence, sequence_gap, sequence_start_*, sequence_probe_* |
| `records.duplicates` | event identity uniqueness | INV / INC | duplicate_event_key |
| `intervals.coverage` | required buckets present; full coverage of the derived window | INCOMPLETE | missing_interval |
| `coverage.contract` | admitted/qualified >= preregistered tolerance; declared ratio consistent with its counts | INC / INV | unmet_coverage |
| `objects.present` | contract-required artifacts on disk, above any size floor | INC / INV | required_object_absent |

## Fixture verdicts (all 26 verified in-suite)

| fixture | intended | must fire | observed | checks fired |
|---|---|---|---|---|
| missing_required_field | DATA_INCOMPLETE | fields.required | DATA_INCOMPLETE | fields.required |
| duplicate_sequence | DATA_INVALID | sequence.integrity | DATA_INVALID | sequence.integrity |
| sequence_gap | DATA_INVALID | sequence.integrity | DATA_INVALID | sequence.integrity |
| out_of_order_event | DATA_INVALID | ordering.causal | DATA_INVALID | ordering.causal, timestamps.monotonic |
| duplicate_timestamp | DATA_INVALID | timestamps.monotonic | DATA_INVALID | timestamps.monotonic |
| missing_interval | DATA_INCOMPLETE | intervals.coverage | DATA_INCOMPLETE | intervals.coverage |
| wrong_instrument | DATA_INVALID | instrument.identity | DATA_INVALID | instrument.identity |
| symbol_outside_universe | DATA_INVALID | instrument.identity | DATA_INVALID | instrument.identity |
| secondary_instrument_outside_family | DATA_INVALID | instrument.identity | DATA_INVALID | instrument.identity |
| wrong_session_date | DATA_INVALID | session.identity | DATA_INVALID | session.identity |
| unexpected_timezone | DATA_INVALID | timezone.contract | DATA_INVALID | timezone.contract |
| wrong_timestamp_semantics | DATA_INVALID | timestamp.identity | DATA_INVALID | timestamp.identity |
| hash_mismatch | DATA_INVALID | files.hash | DATA_INVALID | files.hash |
| missing_hash | DATA_INCOMPLETE | files.hash | DATA_INCOMPLETE | files.hash |
| partial_archive | DATA_INVALID | archive.completeness | DATA_INVALID | archive.completeness |
| missing_file_role | DATA_INCOMPLETE | files.required | DATA_INCOMPLETE | files.required |
| unmet_coverage | DATA_INCOMPLETE | coverage.contract | DATA_INCOMPLETE | coverage.contract |
| missing_terminating_frame | DATA_INVALID | session.completeness | DATA_INVALID | session.completeness |
| event_outside_session | DATA_INVALID | records.session_window | DATA_INVALID | records.session_window |
| schema_mismatch | DATA_INVALID | schema.identity | DATA_INVALID | schema.identity |
| universe_not_pit | DATA_INVALID | universe.pit | DATA_INVALID | universe.pit |
| duplicate_event_key | DATA_INVALID | records.duplicates | DATA_INVALID | records.duplicates |
| type_outside_vocabulary | DATA_INVALID | fields.types | DATA_INVALID | fields.types |
| source_field_absent | DATA_INCOMPLETE | source.identity | DATA_INCOMPLETE | source.identity |
| section_absent | DATA_INCOMPLETE | manifest.sections | DATA_INCOMPLETE | manifest.sections, coverage.contract |
| required_object_absent | DATA_INCOMPLETE | objects.present | DATA_INCOMPLETE | objects.present |

Load-bearing proof: every fixture test asserts both the verdict and the check id
that must fire, and `test_every_check_has_a_fixture` asserts the union of fired
checks equals `set(admission.CHECK_IDS)`; removing or weakening a check therefore
fails the suite. `test_check_registry_is_load_bearing` additionally evaluates the
duplicate-sequence fixture with `sequence.integrity` stripped from the registry
and shows the verdict degrades to `DATA_VALID` — the check, not luck, is what
catches the defect.

Boundary tests worth naming: coverage tolerance is inclusive
(95/100 passes, 94/100 does not); a missing hash is INCOMPLETE, never a pass; the
BASIS contract enforces the frozen 100% hourly pairing structurally
(`interval_period_seconds` 3600 over the availability-derived window), and
`test_basis_window_cannot_shrink_post_hoc` shows that keeping the window while
dropping buckets is a coverage deficit, not a pass (no imputation, no window
shrinking).

## Verdict plus notes

The verdict says what was *proven*; a separate `notes` list says what was merely
*asserted*. Notes never change a state — they exist so a pass cannot be silent
about an unverifiable claim. Exactly three things produce a note: a
`retained:false` source (streamed and never kept, so its digest is a producer
assertion rather than a disk-verified hash), a producer-declared sequence start,
and a bounded sequence probe standing in for the full series.

## Feed-shape extensions (raised by W2 from the real CME sample)

Real feeds broke five assumptions that were fine for synthetic fixtures; all
five were fixed by adding declarations and checks, never by relaxing one:

1. **Sequence start.** `sequence_start: 1` is unsatisfiable for CME MDP3: the
   channel-310 packet sequence was observed at 1,118,771 and persists across
   sessions. Contracts may now set `sequence_start_from_manifest: true`; the
   manifest must then declare `records.sequence_start` **and**
   `records.sequence_start_basis`, a declared start that disagrees with a pinned
   one is INVALID, and a missing declaration is INCOMPLETE. (AUCTION needs the
   opposite: a captured ITCH file carries no payload sequence at all — the repo's
   schema contract records that sequencing is transport-layer — so its
   `require_sequence` is now false, while a sequence the producer *does* declare
   is still checked: declared implies checked.)
2. **Sequence granularity.** A 10-minute MDP3 window holds millions of packets,
   so a full series cannot live in a manifest. With `sequence_probe`
   `{head_rows, tail_rows}` the manifest declares a head run, a tail run and the
   first / last / total values; the engine verifies each run's contiguity, the
   run/declared agreement, run ordering, and the whole-window density identity
   `last - first + 1 == sequence_count_total`. That identity proves the entire
   window is gap-free, which two runs alone could not; a mismatched total is
   INVALID and undersized runs are INCOMPLETE.
3. **Unretained source.** The upstream ES object is 6,817,448,746 B and the epoch
   forbids retaining sources > 5 GB, so it cannot be hashed from disk. Where the
   contract sets `allow_unretained_files`, such an entry must declare
   `retained: false` with `upstream_url` / `upstream_sha256` / `bytes` (missing
   or malformed → INCOMPLETE / INVALID), is not treated as disk-verified, and the
   verdict carries a note. Where the contract forbids it, it is INVALID. ES roles
   are therefore `raw_extract` / `trades` / `book`, all retained and hashed.

4. **Instrument family.** A product sample declares one primary instrument plus
   many secondary ones (W2's ES manifest lists the whole channel-310 family).
   Contracts may now set `allowed_instrument_prefixes`, checked over the primary
   *and* every declared secondary instrument, and any declared instrument without
   a symbol is INCOMPLETE; a stray symbol is INVALID. ES pins `["ES"]`.

5. **Session completeness.** The delivered ITCH object carries no zero-length
   BinaryFILE terminator; its completeness is container- and parse-level: gzip
   CRC32 + ISIZE, `received_bytes == Content-Range total`, framing errors 0,
   trailing bytes 0, and an `S` system event with code `C` as the last frame.
   Demanding `terminating_frame_present: true` therefore forced an honest
   producer to declare false and fail. The contract now sets
   `require_stream_completeness` with `stream_completeness_markers` (each key
   present and equal to the expected value, else INCOMPLETE / INVALID),
   `completeness_evidence_role` (a retained, hash-verified artifact that carries
   the markers), and `required_final_event`; a declared frame flag is recorded as
   a note instead of deciding the verdict. This is strictly stronger than the old
   boolean: a truncated gz (failed CRC/ISIZE), an early EOF, a non-zero trailing
   or framing count, or a wrong final event is now caught, and the marker block
   itself is surfaced as producer-declared evidence in the notes.

W1/W2/W3 were sent the exact shapes; `test_contracts_pin_feed_shapes` pins them.

## Engine verdicts on existing W1/W2/W3 manifests

Checked read-only at 2026-09-29T22:01–22:45Z:

| path | verdict |
|---|---|
| `M2/data/derived_auction/2026-06-12/admission_manifest.json` | **`DATA_VALID`, 23 checks run, 0 findings, 3 notes** (W1's auction manifest, independently re-run ~22:45Z, exit 0). 2,497 universe members, 7,491 records, declared coverage 2497/2497, all retained files hashed from disk; notes record the unretained 17,894,268,560 B source, the producer-declared stream-completeness markers, and the declared `terminating_frame_present: false`. |
| `M2/data/derived_auction/2026-06-12/admission.json` | absent at 22:04Z → `DATA_INCOMPLETE` (`manifest.load`) (W1's stream was still in flight; its canonical manifest later landed under a different name, row above) |
| `M2/data/derived_es/2023-07-17T133000Z/admission.json` | **`DATA_VALID`, 23 checks run, 0 findings, 4 notes** (W2's ES manifest, independently re-run ~22:30Z, exit 0). I re-hashed all seven retained files myself (raw_extract 66,692,366 B, trades, book, acquisition_record and three reference objects) and each matched its declared sha256; the 6,817,448,746 B upstream object is a `retained:false` entry and appears as a note; declared sequence start 1,118,771 with probe first/last 1,118,771 / 1,501,663 and total 382,893 satisfy `last-first+1 == total`; the fourth note records the declared `terminating_frame_present: false`, which the pcap slice honestly has. |
| `M2/data/derived_basis/admission.json` | present (183,561 bytes, 27 top-level keys, `artifact: BRANCH_C_AVAILABILITY_AND_PAIRING_ADMISSION`) → `DATA_INCOMPLETE`: it is an evidence document, not a W4-canonical manifest, so no structural section exists to verify and every check reports absence. The engine recomputed nothing and accepted nothing. |
| `M2/data/derived_basis/manifest_basis.json` | **`DATA_VALID`, 23 checks run, 0 findings** (independently re-run at 22:10Z; W3's own saved verdict `manifest_engine_verdict.json` agrees). Declared sha256 `08e05d0a…6ab9fb` matches the file; the three declared inputs (roles hl_funding / hl_mid / binance_mark) were hashed from disk by the engine, and 4981/4981 hourly buckets are present. |

The first basis verdict is the designed refusal of an unverifiable document, not a
judgement of the producer's data; the second is an admission of the canonical
manifest, verified from disk rather than taken on trust. It was re-run after the
feed-shape contract extensions and still returns `DATA_VALID` with 0 reasons and
0 notes.

**Auction rule defects (reported by W1, recorded not resolved — engine
unchanged):** (1) the frozen universe clause `Issue Sub-Type = C` admits 31 of
12,809 names here (72 of 8,849 in the 2019 tape) because common stock is
classification `C` with sub-type `Z`; a classification-only reading admits 4,543.
(2) 8,528 of 12,809 closing-cross `Q` messages carry zero shares and zero price
(no cross interest), systematically by venue: 2,465/2,483 valid for Q/G/S versus
32/2,060 for N/A/P/Z. (3) Frozen-literal boundary coverage is 0/17 (the first NOII
read lands at 15:50:00.000298551, after the nominal boundary); the freeze-ready
first-at/after fallback gives 2,497/2,497 = 1.00, which is what the manifest
declares. The engine verifies the declared counts and cannot adjudicate these
three rule readings: they belong to the freeze epoch. Detail in W1's own report.

**ES identity evidence (flagged by W2, recorded not resolved):** template 30
SecurityStatus is not transmitted on ES channel 310 anywhere in this sample, so
the ingest-side channel/group identity rests on the CME channel configuration
(A 224.0.31.1:14310 / B 224.0.32.1:15310) plus the per-instrument channel tag
(1180 = 310) for all 497,636 SecurityID-bearing entries. The engine's ES
`instrument.identity` check therefore validates the declared identity evidence
(symbol, venue, `allowed_instrument_prefixes` over primary and secondary
instruments) and not any raw SecurityStatus template: a future contract check
demanding SecurityStatus evidence for this sample would be unsatisfiable. The
manifest documents its own basis (secdef SecurityID 3445 = ESU3, SecurityGroup
ES, channel 310).

**Residual limit on that DATA_VALID** (flagged, not resolved here): the BASIS
contract enforces 100% hourly completeness *inside the window the manifest
declares*; it cannot adjudicate which availability definition produces that
window. W3's canonical manifest declares the primary availability window
2026-03-05T11:00:00Z → 2026-09-28T23:00:00Z (4981 h, internally consistent:
`(end-start)//3600 + 1 = 4981`), while its evidence document reported a
Binance-funding-constrained sub-window of 4302 h over
2026-03-05T11:00Z → 2026-08-31T16:00Z. Choosing between those definitions is a
verification-epoch question about the frozen "availability-derived window" rule;
the engine's DATA_VALID says the declared window is complete and internally
consistent, not that it is the correct window.

All three branches now have a canonical manifest that the engine admits. The
canonical manifest shape, the feed-shape extensions and the exact evaluation
commands were sent to W1/W2/W3. Re-run (read-only):

```
python3 -m M2.src.admission --manifest M2/data/derived_auction/2026-06-12/admission_manifest.json --branch AUCTION --root .
python3 -m M2.src.admission --manifest M2/data/derived_es/2023-07-17T133000Z/admission.json --branch ES --root .
python3 -m M2.src.admission --manifest M2/data/derived_basis/manifest_basis.json --branch BASIS --root .
```

These verdicts are provisional until the verification epoch; the engine's verdict
on a producer-authored manifest is evidence about the manifest, not about the
market data behind it.

## Limits / defects

* No tooling defect found; no check was weakened and no convenience pass exists.
* There is deliberately no switch that skips hash recomputation: a corrupt file
  cannot be admitted by asking the engine not to look.
* The engine cannot verify facts a manifest does not declare: an undeclared
  quantity surfaces as INCOMPLETE, which is the intended refusal.
* The engine verifies declared raw/derived file hashes; it does not hash the
  manifest document itself. Sealing the manifest is the freeze epoch's job, and
  `source.retrieved_at_utc` is producer-volatile: it changes the manifest file's
  own sha256 on regeneration while every checked property stays identical.
* No formatter, linter or project-wide suite was run; only
  `python3 -m unittest M2.tests.test_admission`.