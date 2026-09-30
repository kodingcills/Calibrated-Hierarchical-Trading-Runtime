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
