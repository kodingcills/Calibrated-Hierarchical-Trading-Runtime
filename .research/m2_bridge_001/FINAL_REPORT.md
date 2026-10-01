# GOAL-M2-BRIDGE-001 — final report

Status: canonical-state application complete; closeout repairs executed and pending the V4
independent check at the moment of writing. Machine-readable verdicts live in `M1/data/*.csv`
and `M1/output/*`; this file is the campaign's narrative provenance.

## Terminal state

**`M2_BRIDGE_DECISION_COMPLETE`.** Two branches reached a causally valid, preregistered,
execution-aware economic-materiality decision from real admitted historical data; a third reached
a principled `INDETERMINATE` and was not converted into a verdict.

One limitation is carried explicitly rather than hedged: for branches A and C the freeze was
written and hashed before the measurement ran (artifact ordering, plus a live self-check), but
that ordering has **no external anchor** — no RFC3161 timestamp and no pre-result commit — so V3
rates pre-outcome sealing `UNVERIFIED`. The fix is procedural: commit or timestamp a freeze before
running against it.

## Canonical starting state

M1 with `ALIVE=0`, `TEST_NOW=NONE`; M2-0/0.6/1/2 all `KILLED`; ES H3
`EXTERNAL_BLOCKED_NOT_AUTHORIZED`; Nasdaq continuous-book family `CLOSED`; auction and
funding/basis `EXTERNAL_ONLY`; 29 candidate rows, 0 gate-eligible. Every one of the goal's three
branches was recorded as blocked on **data access**, not on economics.

## Epoch allocation trace

| epoch | state observed | actions selected | topology |
|---|---|---|---|
| 0 | three freeze-ready specs, all "external only" | design grilling + three read-only data probes | fact-finding |
| 1 | branches reachable, no tooling | auction tape, ES slice, basis panel, admission engine, economic envelope | 3× PARALLEL_SEARCH + 2× ENGINEERING |
| 2 | artifacts exist, uncertified | canonical registration + ES prerequisite correction; verification V1 | ENGINEERING + ADVERSARIAL |
| 3 | verified engine defect | grid-identity repair with negative control | SERIAL |
| 4 | two admissions unverified | verification V2 (splice attack NC8) | ADVERSARIAL |
| 5 | operator answered A/B/C | three sealed runs, then verification V3 | PARALLEL_SEARCH ×3 |
| 6 | three verdicts, two integrity defects | canonical application, two repairs, single regeneration, verification V4 | ENGINEERING + ADVERSARIAL |

## Data-admitted branches

| branch | admission | sample |
|---|---|---|
| A ES | `DATA_VALID` | ESU3, 2023-07-17 13:30:00Z–13:40:00Z, 66,692,366 B extract, sha256 c938273d… |
| B auction | `DATA_VALID` under the v2 contract | TotalView-ITCH 2026-06-12, 17,894,268,560 B streamed, sha256 1f9d35e1… |
| C basis | `DATA_VALID` | 4,981-hour panel, 2026-03-05T11:00Z–2026-09-28T23:00Z |

## Empirical results

| | A ES H3 OFI | B auction late-NOII | C funding/basis |
|---|---|---|---|
| gross | −0.0047336124 bps pooled at 1 s; −0.0047 / −0.0015 / +0.0503 at 1/5/15 s | −108.8946 bps executable capture (reconstruction artifact) | +0.0344051 bps per one-hour hold |
| unconditional / secondary | +0.0157 / +0.0631 / +0.1341 bps (598-slot variant); matched-instants addendum attached | mechanism +6.5168 bps (CI [2.0026, 10.9985]), non-executable | HL +0.0596998, Binance −0.0267530, hedge residual −0.0004616 |
| CI | [−0.04685, +0.04034] | [−169.84, −64.04] | [−0.0101126, +0.0755247] |
| coverage | 583/599 slots, quoted 0.99833 | 1.0000 input availability, signal scope 0.5217 | 4981/4981 buckets, 4979/4979 holds |
| `C0` | 0.5770 bps (observed half-spread sum) | 1.0218 bps | 4.8 bps (2 × lowest published HL rung 0.024 %) |
| `C*` | −0.5817 bps | −109.92 bps | −4.7655949 bps; T* 145.69 h |
| decision | **KILL_MATERIALITY** (sample-scoped) | **INDETERMINATE**, freeze invalidated | **KILL_MATERIALITY** |

## Verification results

- **V1** (18 claims): 14 VERIFIED, 1 SUPPORTED_SCOPED, 2 CONTESTED, 1 REJECTED. Rejected the HL
  price leg as a mid; contested the remove-liquidity fee as a Closing-Cross cost; contested the
  pairing check as a count identity.
- **V2** (14 claims): 13 VERIFIED, 1 SUPPORTED_SCOPED, 2 CONTESTED, 1 UNVERIFIED, 7 negative
  controls. NC8: a re-compressed head+tail splice of 0.92 % of a session passes every transport
  marker.
- **V3** (three runs): branch A 9 VERIFIED / 1 CONTESTED / 1 UNVERIFIED; branch C 5 VERIFIED /
  2 SUPPORTED_SCOPED / 1 CONTESTED / 1 UNVERIFIED; branch B 8 VERIFIED / 1 SUPPORTED_SCOPED /
  1 CONTESTED / **1 REJECTED** (the freeze is not a valid preregistration: its sealed input was
  written before the seal and already contained the Closing Cross exit price).

## Cross-pollination and invalidation

Transferred: grid-identity checking, archive completeness reasoning, hour-flooring, and the
freeze-anchor rule (these apply to every future archive-backed experiment). Not transferred, by
rule: A's magnitude to NQ, B's mechanism metric to any continuous-book candidate, C's magnitude to
CME. The M2 Nasdaq H2/H3 top-of-book family remains `CLOSED`; nothing here reopens it.

## Remaining external requirements

1. `≥ 2` non-overlapping ES sessions (or a materially different regime) + verified
   account-independent CME charges — the only route to lifting A's sample-scoped kill.
2. A warm-up-extended auction extract (pre-15:49:50) under an externally anchored freeze — the
   named next action for B, which is undecided rather than killed.
3. Binance 2026-09 funding file (84 settlements), a verified Binance fee schedule, and any
   longer-horizon carry reformulation registered as its own candidate.

## Orchestration audit (§30)

- **Serial collapse**: none in execution. Epoch 0 was serial by operator instruction (design
  before work); the 20 k early-spend rule was superseded by the operator's explicit budget
  re-baseline, which is recorded rather than assumed.
- **Spurious parallelism**: none identified. The three data workstreams were independent paths; the
  two engineering workers owned disjoint files.
- **Duplicate work**: none identified across eight workers and four verification waves.
- **Dead-branch spend**: one producer (B5) ran 54 minutes and exited 1 at its reporting step after
  completing the run — artifacts recovered, verdict reconstructed from `results.json`, failure
  recorded in `epoch5/B5_PRODUCER_FAILED.md`. The Hyperliquid oracle path was abandoned after
  bounded attempts once requester-pays access was proven.
- **Verification yield**: 4 waves, 63 primary claims, 7 CONTESTED, 2 REJECTED and 3 UNVERIFIED —
  i.e. roughly one in seven claims taken to independent review did not survive as stated, and every
  contested finding changed a contract, a cost floor or an artifact.
- **Decision-changing outputs**: 8 — universe transcription error; terminator/NC8 completeness
  defect; admission count-vs-grid identity defect; HL price-leg rejection; remove-liquidity fee
  exclusion; rate-period scoping; and the three branch verdicts.
- **Cost of the campaign per verified decision**: 2 verified kills from 9 worker agents and 4
  verification waves, with no purchased data, no credentials and no account creation.

## What the campaign established about allocation

Blockers recorded as "external data required" were wrong for two of three branches: free, no-auth,
publicly published venue data reached a decision. Verdicts also rest on their weakest link rather
than their best number — A's kill survives on the absence of detectable conditional displacement
and the independent `hi ≤ C0` arm, C's kill is sign-robust under the lowest published fee rung, and
B's positive secondary metric was correctly refused as evidence because its entry price was not
executable. Verification, not production, was the highest-yield spend.
