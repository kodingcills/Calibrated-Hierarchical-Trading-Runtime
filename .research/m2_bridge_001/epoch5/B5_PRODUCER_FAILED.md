# B5 producer failure — provenance note

The B5 auction worker **failed with exit 1 after 54 minutes** while writing its report. Its
narration output contains only partial progress text and no summary. Therefore
`.research/m2_bridge_001/epoch5/B5_REPORT.md` **does not exist** and no producer-authored claim
about this branch's verdict should be treated as an assertion by B5.

What exists, written by that same process before it died (all under
`M2/experiments/M2-BRIDGE-AUCTION-LATENOII-MATERIALITY/`):

| artifact | bytes | role |
|---|---|---|
| `freeze.json` + `freeze.sha256` | 16 620 + 78 | sealed contract |
| `run_inputs.json` | 5 488 | as-run inputs, code hashes |
| `results.json` | 3 182 301 | measured result and decision |
| `certificate.json` | 3 380 665 | in-window continuity + coverage certificate |
| `admission_manifest_v2.json` + `admission_v2_result.json` | 493 748 + 2 523 | v2 contract and engine verdict |
| `signal_extract.json`, `entry_prints.json` | 12 543 155 + 534 587 | sealed run inputs (hashed inside results.json) |
| `proposal.json`, `as_run_deviations.json`, `cli_transcript.txt` | 21 089 + 4 029 + 945 | canonical-update proposal, deviations, transcript |
| `build_manifest.py`, `seal_freeze.py`, `spec_prev_retained.json` | — | tooling + retained pre-repair spec |

Standing of the result: recorded verdict **INDETERMINATE** with clauses
`ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED` and `SIGNAL_SCOPE_SUBFLOOR`; the rule verdict would have
been `KILL_MATERIALITY`. Executable capture −108.89 bps, `C0` 1.0218 bps, `C*` −109.92 bps,
mechanism metric (secondary) +6.5168 bps side-signed. Because the producing process died and
because a positive secondary metric coexists with a catastrophic primary metric, this branch's
verdict is verified separately in `verification/V3/` before any canonical mutation. Its test
module (`M2/tests/test_auction_materiality.py`, 40 tests) passes, including a fixture that
replays the known splice attack against the continuity rules.
