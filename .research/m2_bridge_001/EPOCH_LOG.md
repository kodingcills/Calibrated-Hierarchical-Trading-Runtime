# GOAL-M2-BRIDGE-001 — epoch log

Budget basis: explicit re-baseline authorized by operator (Q12 = b). Grilling + probe
consumption is recorded as pre-execution campaign overhead; execution starts with a fresh
120,000 aggregate-token reserve and the epoch ceiling remains 6 execution epochs. Token
figures are byte/token proxies with LOW confidence, never evidence.

## Epoch 0 — design closure (pre-execution overhead)
- Facts established by controller reads: canonical state, three freeze-ready reselection
  specs, M2 kill lineage, ITCH tape inventory.
- Read-only probes (no purchase, no credentials, no signup):
  - PROBE_A_ES_DATA: free no-auth CME Globex MDP 3.0 sample PCAPs; ES channel 310;
    one trade date (2023-07-17 RTH open, 10 min) reachable; CME's own pages 403.
  - PROBE_B_ITCH_FREE_DAYS: additional free full-session ITCH 5.0 tapes exist; no provider
    checksum published; end-of-file/terminal-frame evidence must substitute.
  - PROBE_C_CRYPTO_PATHS: free Binance archive host works (451 host is environment-only);
    HL hourly funding paginates with 0 gaps; sub-second jitter requires hour-flooring;
    HL oracle free path absent (requester-pays only).
- Design decisions settled (see conversation): dev-grade admissibility with asymmetric
  kill/survive semantics; ES account-cost prerequisite corrected to C0 + parameterized C1 +
  C*; new narrow auction candidate row; per-branch preregistered rules; no universalized
  R bars; extend existing engine; no commits.

## Epoch 1 — allocation
State observed: A/B/C all reachable from free sources; no freeze sealed yet; no outcome
inspected for any branch.

Actions selected (all independent, launched together):
- W1 auction data acquisition + structural admission (modern primary 2026-06-12; replication
  candidate 2026-05-15 reserved, retrievability only).
- W2 ES sample acquisition + admission (2023-07-17 RTH-open 10-min slice; cost inputs only).
- W3 branch C availability-derived window + 100% hourly pairing admission.
- W4 DATA_ADMISSION engine (new modules + adversarial fixtures).
- W5 ECONOMIC_ENVELOPE arithmetic (new modules + deterministic tests).

Topology: PARALLEL_SEARCH (W1-W3) + PARALLEL_SAFE_ENGINEERING (W4, W5, disjoint files).
No worker may compute an economic outcome in this epoch.
Results: W1 auction tape admitted (17.89 GB streamed, gzip CRC/ISIZE PASS, 0 framing errors over
1.30e9 frames, 0 trailing bytes); W2 ES MDP 3.0 slice admitted (byte-identical independent
re-derivation); W3 basis panel 4981/4981 paired; W4 admission engine; W5 economic envelope.

## Epoch 2 — integration + first verification
Actions: W6 canonical registration (new narrow auction candidate with ancestry, ES cost
prerequisite correction, validator PASS 19/19, 99 M1 tests); V1 adversarial verification of
W3/W4/W5/W6 (14 VERIFIED, 1 SUPPORTED_SCOPED, 2 CONTESTED, 1 REJECTED).
Decision-changing: REJECTED the HL price leg as a mid (it is a trade-derived candle close, a
named kill condition in the frozen contract); CONTESTED the remove-liquidity fee as a
Closing-Cross cost; CONTESTED the admission engine's pairing check as a count identity.

## Epoch 3 — defect repair
W7 added interval grid identity, a coverage-claim cross-check and session window alignment, with
a load-bearing negative control; the three adversarial manifests that had passed now fail; the
real basis manifest still returns DATA_VALID.

## Epoch 4 — second verification
V2 attacked both data admissions: 13 VERIFIED, 2 CONTESTED, 1 UNVERIFIED, 7 negative controls.
Decision-changing: the zero-length terminator is absent from BOTH the 2026 tape and the repo's
admitted 2019 tape, and a re-compressed head+tail splice of 0.92% of the session passes every
transport marker (NC8) - so transport markers cannot prove session completeness.

## Epoch 5 — sealed runs
Operator authorized: universe transcription repair, completeness contract B1 (measurement-window
continuity + coverage certificate), and a versioned reference-price amendment for branch C.
B5 auction (worker failed at the reporting step; artifacts complete; INDETERMINATE with
ENTRY_BOOK_RECONSTRUCTION_UNVALIDATED + SIGNAL_SCOPE_SUBFLOOR), A5 ES (KILL_MATERIALITY,
sample-scoped), C5 basis (KILL_MATERIALITY, one-hour formulation). V3 verification launched
before any canonical mutation.
