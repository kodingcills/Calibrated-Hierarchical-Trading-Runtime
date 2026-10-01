# W9 — restore the sealed admission module and quarantine the auction addition (GOAL-M2-BRIDGE-001, epoch 6)

Role: repair. Two verified integrity defects were closed by changing code, not by recording them.
No new research, no new verdicts, no commit, no push. The basis freeze verifies in place again; the
auction tooling is intact and green; no sealed artefact was modified. Restoring the sealed module
does move the *auction* freeze's recorded hash in the opposite direction — stated in §6 rather than
hidden.

## 1. Defect being repaired

`M2/src/admission.py` is a sealed input of the basis freeze
(`M2-BRIDGE-HL-BINANCE-BASIS/freeze.json` → `inputs_sha256.code["M2/src/admission.py"]`). An
unrelated branch (the auction B5 pass) added the AUCTION v2 contract, two contract-scoped checks and
an `extra_checks` hook to `evaluate()` in that shared module **after** the basis seal was written, so
the basis freeze no longer verified in place (`CODE_DRIFT`-class failure) even though V3 showed the
added code is inert for the basis result. Repair: move the addition out of the sealed module and
restore the module byte-exactly.

## 2. Files changed

| file | change | sha256 before | sha256 after |
|---|---|---|---|
| `M2/src/admission.py` | restored byte-exactly from `ac28929` (`git show ac28929:M2/src/admission.py`) | `00363c3ac7e76366196581a254cb2b4baae73fcdeb69335da493d0b26f764c60` | `9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477` |
| `M2/src/admission_auction.py` | **new** — AUCTION v2 contract + `session.continuity` / `coverage.certificate` checks, moved verbatim; shared primitives imported from `M2.src.admission`, never copied | (did not exist) | `84fd3270cc382248b6e57bd8111abc2fdb37f546150ea9f043df83fd47110caf` |
| `M2/tests/test_auction_materiality.py` | v2 consumers re-pointed at `M2.src.admission_auction` (import, `AUCTION_CONTRACT_V2`, `evaluate`, `contract_for`, `Context`, `BUILTIN_CONTRACTS["AUCTION_V2"]`) | `940c5b611a85f17ab2f11418e78d7efa26ec9e31191a01e93eba3bf235c261ec` | `b08e79459cb780b412620364757049ffa615dd47567914ebed73b6e67f567675` |
| `M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/seal_freeze.py` | `M2/src/admission_auction.py` added to `MODULES`; recorded admission command re-pointed to `-m M2.src.admission_auction` | `813a1612c7528384c8ac776d136f04dc54202928786a1377ae53c565ffa4a10d` | `e4e6e024f689a5c79fc16c9a44ab81c176141f2d191acfde0621adfe35dd9eb8` |

Not touched: any sealed artefact (`freeze.json`, `freeze.sha256`, `run_inputs.json`, `results.json`,
`certificate.json`, `entry_prints.json`, `signal_extract.json`), `M2/src/es_materiality.py`,
`M2/src/basis_materiality.py`, `M1/src/validate.py`, anything under `M1/`.

### 2.1 How the semantics were preserved

- The moved block is character-for-character the block that lived at `M2/src/admission.py:2112-2417`,
  with only a W9 provenance note added above it. Same check ids (`session.continuity`,
  `coverage.certificate`), same severities (`INCOMPLETE` for absent evidence, `INVALID` for
  contradiction), same reason-ordering, same `CONTINUITY_FIGURES`.
- The sealed engine keeps its `checks=` seam (`admission.evaluate(..., checks=registry)`), and
  `admission_auction.evaluate` uses exactly that seam to append the contract's `extra_checks` after
  the global registry — the same order the engine ran while the hook lived inside it. No evaluation
  loop, no registry, and no check body is duplicated.
- Importing `M2.src.admission_auction` re-registers `BUILTIN_CONTRACTS["AUCTION_V2"]` in the
  engine's own (shared) dictionary, so `contract_for("AUCTION_V2")` keeps resolving as before. The
  sealed engine file itself is byte-identical to the freeze.

## 3. Commands run (each with its result)

**3.1 the sealed hash is back**

```
$ shasum -a 256 M2/src/admission.py
9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477  M2/src/admission.py
```

equals the value the basis freeze sealed.

**3.2 the basis freeze verifies in place again** (its own CLI, `M2/src/basis_materiality.py`)

```
$ .venv/bin/python3 -m M2.src.basis_materiality --check
{
  "freeze_sha256_matches": true,
  "code_unchanged": true,
  "inputs_unchanged": true,
  "drifted_inputs": [],
  "sealed_contract_sha256": "389b8f4d65b1b2f54bf5eb29266c74c078ca7187e8c1b4455052fa52d780e3a7"
}
EXIT=0
```

No `REFUSED:` line on stderr: `verify_seal` accepts the tree.

**3.3 the auction tooling still passes its 40 tests**

```
$ .venv/bin/python3 -m unittest M2.tests.test_auction_materiality -v
...
Ran 40 tests in 8.358s

OK
```

**3.4 the full M2 suite is green**

```
$ .venv/bin/python3 -m unittest discover -s M2/tests -t .
Ran 332 tests in 11.803s

OK
```

(332 was the pre-change count; no test was added, removed or weakened.)

**3.5 the re-pointed CLI reproduces the sealed auction verdict end-to-end**

```
$ .venv/bin/python3 -m M2.src.admission_auction --manifest \
    M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/admission_manifest_v2.json \
    --branch AUCTION_V2 --root . --json-out /tmp/admission_v2_recheck.json
DATA_VALID  branch=AUCTION  contract=ADMISSION-AUCTION-v2  manifest=M2-BRIDGE-AUCTION-LATENOII-AGG-2026-06-12-v2
  no findings
  [NOTE] files.retained: ...
  [NOTE] session.completeness: ...
  [NOTE] session.terminating_frame: ...
EXIT=0

$ diff <(canonicalise /tmp/admission_v2_recheck.json) \
       <(canonicalise M2/.../admission_v2_result.json)
IDENTICAL (canonicalised)
```

The quarantined module's CLI resolves `AUCTION_V2`, runs the contract checks, and emits the sealed
`admission_v2_result.json` verdict unchanged (`DATA_VALID`, no findings, same notes). That the two
contract-scoped checks really run through the new path is pinned by
`test_missing_certificate_object_is_incomplete` (asserts both `session.continuity` and
`coverage.certificate` fire) inside the passing 40-test file.

## 4. Sealed-hash sweep over all three bridge `run_inputs.json`

Every recorded path in each file was hashed from the tree (paths relative to the repo root, or to
the experiment directory where the record uses a relative name).

| experiment | sealed entries | verify | drift |
|---|---|---|---|
| `M2-BRIDGE-AUCTION-LATENOII-MATERIALITY` | 22 | 18 | 4 |
| `M2-BRIDGE-ES-H3-OFI` | 13 | 13 | 0 |
| `M2-BRIDGE-HL-BINANCE-BASIS` | 155 | 155 | 0 |

The basis experiment's 155 sealed entries — including `M2/src/admission.py` at
`9f5862f7…` — all verify; this is the same set `--check` walks in §3.2. The ES experiment verifies
completely.

## 5. Remaining drift — all four are in the AUCTION seal

The AUCTION `run_inputs.json` was sealed at a moment when the tree already carried the drifted
admission module, so three of these four are the direct, intended consequence of this repair and one
is pre-existing and unrelated.

| recorded path | sealed | tree now | cause |
|---|---|---|---|
| `M2/src/admission.py` | `00363c3ac7e76366196581a254cb2b4baae73fcdeb69335da493d0b26f764c60` | `9f5862f71efd7fec97766f069344c9a60a3751108aec76df23de9e096b2cf477` | **this repair** (§6) |
| `M2/…/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/seal_freeze.py` | `813a1612c7528384c8ac776d136f04dc54202928786a1377ae53c565ffa4a10d` | `e4e6e024f689a5c79fc16c9a44ab81c176141f2d191acfde0621adfe35dd9eb8` | this repair — step 3 requires re-pointing this consumer |
| `M2/tests/test_auction_materiality.py` | `940c5b611a85f17ab2f11418e78d7efa26ec9e31191a01e93eba3bf235c261ec` | `b08e79459cb780b412620364757049ffa615dd47567914ebed73b6e67f567675` | this repair — step 3 requires re-pointing this consumer |
| `M1/src/materialize.py` | `bdec4cc1ef1821a83210a646e041113b6fb6cdab75cb48d4de17d95fb971a08c` | `ad1d18d2bf8c597cff951ca976fab1d9c7bee9e17b07ef21439650ddd2e722a0` | **pre-existing, not caused by this repair** — the working tree is clean at HEAD (`git status` shows no modification), so an earlier pass changed `materialize.py` after the auction seal, exactly as the admission module drifted after the basis seal |

`M1/src/materialize.py` is a named finding, not papered over: the AUCTION freeze was already drifted
before W9 ran, in a file W9 did not touch. It is out of W9's scope to repair (M1 is W10's) and is
recorded here so the AUCTION seal's non-verifiability is not misattributed to this pass.

## 6. Consequence for the (already invalidated) AUCTION freeze — stated, not hidden

The AUCTION seal recorded `M2/src/admission.py = 00363c3a…`, i.e. the *drifted* bytes that carried
the v2 block, because it was sealed after that addition. Restoring the file to the basis-frozen
`9f5862f7…` therefore creates drift in the **opposite direction** in the AUCTION seal:

- Before W9: basis freeze ✗ (drifted), auction freeze ✓ for `admission.py`.
- After W9: basis freeze ✓ (restored), auction freeze ✗ for `admission.py`
  (`00363c3a…` sealed vs `9f5862f7…` on disk).

This is unavoidable: a single file cannot hash to two different values, and the basis seal is the
one whose contract is still live. The auction branch was already invalidated by V3
(development-grade single session; its freeze is recorded as `INVALIDATED_FREEZE` in the canonical
registers), so no live verdict depends on its seal verifying. The forward state is now consistent:
`M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/seal_freeze.py` hashes `M2/src/admission.py` (restored) plus
the new `M2/src/admission_auction.py` and records the `-m M2.src.admission_auction` command, so a
future re-seal — not performed here, since the sealed artefacts are read-only to this pass — would
seal the quarantined layout. Until such a re-seal, the AUCTION `run_inputs.json` shows the four
drifted paths in §5 and must be read as historical, not as a live verification.

## 7. Verification boundary

- The four drifted AUCTION paths in §5 are the only remaining drift across the three bridge seals.
- No sealed artefact was written: `git status` lists exactly the three tracked files of §2 plus W10's
  in-flight ES addendum artefacts; no `freeze.json`, `freeze.sha256`, `run_inputs.json`,
  `results.json`, `certificate.json`, `entry_prints.json` or `signal_extract.json` is modified.
- No commit, no push (the controller commits).
