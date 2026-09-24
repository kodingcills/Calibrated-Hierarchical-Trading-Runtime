# QUEUE IDENTIFIABILITY — Nasdaq TotalView-ITCH 5.0, 2019-07-30

Question: what can the historical feed actually tell us about the position of a hypothetical
passive order in the matching queue, and what must be bounded rather than modelled?

Sources used: the provider's own specification, retained and hashed in this repository
(`M2/data/reference/NQTVITCHspecification.pdf`, sha256 `45e0531d…e68aacc3`), and primary
regulatory filings reachable through the Federal Register API (access date 2026-09-24). Where a
property could not be verified from a primary source, it is classified `UNKNOWN` and its effect is
bounded by a measured counter on the tape rather than hidden inside a heuristic.

## 1. What the feed contains per message

| message | content that matters for queue reconstruction | classification |
|---|---|---|
| `A` / `F` Add Order | day-unique order reference, side, shares, display price; the spec states the order "was added to the displayable book" | `DETERMINISTIC_FROM_FEED` |
| `E` Order Executed | order reference and executed shares; cumulative per reference | `DETERMINISTIC_FROM_FEED` |
| `C` Order Executed With Price | as `E`, plus the execution price when it differs from the display price, plus a printable flag | `DETERMINISTIC_FROM_FEED` |
| `X` Order Cancel | order reference and shares removed from the **display** size (partial cancellation) | `DETERMINISTIC_FROM_FEED` |
| `D` Order Delete | order reference; all remaining shares become inaccessible | `DETERMINISTIC_FROM_FEED` |
| `U` Order Replace | original reference, **new reference**, new shares, new price; "all remaining shares from the original order are no longer accessible" | `DETERMINISTIC_FROM_FEED` |
| `P` Trade (non-cross) | a match of a **non-displayable** order: shares, price, no book identity (the reference field has been zero since 2010-12-06) | `OBSERVABLE` as flow, `UNOBSERVABLE` as queue |
| `Q` Cross Trade | opening/closing/halt cross volume | out of scope (not continuous trading) |

## 2. Component-by-component classification

| queue component | classification | basis |
|---|---|---|
| Displayed orders resting at a price, and their arrival order | `DETERMINISTIC_FROM_FEED` | the feed carries every displayed order's arrival, modification and removal, and disseminates payload messages in engine order (the FPGA product is documented as guaranteeing the same payload order as the software feed) |
| Time priority within the displayed class at one price | `DETERMINISTIC_FROM_FEED`, validated empirically | modelled as feed order; the tape's own execution pattern is used as the test (section 4) |
| Priority of a cancel-replace | `DETERMINISTIC_FROM_FEED` | `U` carries a new reference number and the original's shares become inaccessible, so the replacement cannot retain the original's place |
| Reserve-order replenishment | `DETERMINISTIC_BY_RULE` | SEC order approving Nasdaq Equity 4, Section 4703(h) amendments (Release 34-91109, 2021-02-11, SR-NASDAQ-2020-090): "a new displayed order will be entered and receive a new timestamp, while the size of the non-displayed order will be reduced by the same amount and will not receive a new timestamp". A replenished display therefore moves behind us, and the feed shows it as a new `A` with a new reference. The rule post-dates the tape; the behaviour it describes (new timestamp on replenishment) is the long-standing one, and the modification it introduced concerns locking, not ranking. |
| Non-displayed (hidden) interest resting at our price | `UNOBSERVABLE` | no `A` message is generated for a non-displayed order (spec, section 1.5.1). Order-level ranking rules place displayed interest ahead of non-displayed interest at the same price, but the verbatim text of Nasdaq Equity 4, Section 4703(h) as in force on 2019-07-30 could not be retrieved with the available tooling (search exhausted: the rulebook site is not fetchable; sec.gov returns HTTP 403 to this client; the Federal Register API holds filings, not the rulebook). **Therefore the model does not rely on the rule.** It assumes only displayed FIFO and measures the residual (section 4). |
| Priority-preserving order attributes at a different price (for example Nasdaq's Extended Life Priority, referenced in SEC filing 34-84924 of 2018) | `PARTIALLY_OBSERVABLE` | such an order can display at one price while ranking at another. The feed shows the displayed price only. Any occurrence appears as an execution whose reference was not resting at our level, which is counted as a priority anomaly (section 4). |
| Odd-lot orders | `OBSERVABLE` with a note | the Stock Directory `Round Lots Only` field documents that "odd and mixed lot orders are allowed" when it is `N`; odd-lot orders that are displayed appear in the feed like any other add. No separate treatment is applied, and the residual is measured by the same counters. |
| Aggressor identity, order intent, hidden size behind a displayed order | `UNOBSERVABLE` | not carried by the feed and not needed for the fill question |
| Whether the engine's ranking for messages sharing one timestamp equals feed order | `DETERMINISTIC_FROM_FEED` for payload order, `UNKNOWN` for equal-timestamp ties | the feed is sequenced and ordered, but the spec does not state a tie-break rule. The tape's own 3,858,123 identical-timestamp messages (M2-0 audit) are treated as ordered, and the effect is bounded by the anomaly counters. |

## 3. What the model therefore assumes, and in which direction it errs

1. **Displayed FIFO only.** A fill requires depletion of the displayed quantity ahead and a real
   execution at our price. If non-displayed interest were in fact able to trade ahead of a
   displayed order at the same price, the model would fill *more often* than reality: the primary
   fill probability is an **optimistic bound** on that axis.
2. **No fill from `P` prints.** Non-displayed flow at our price is counted per attempt
   (`hidden_flow_at_level_shares`) but never fills us. This is the conservative direction on fills
   and it is also what display priority implies.
3. **No cancel policy.** The order rests until its TTL, so it is exposed to every sweep. This is
   conservative on adverse selection: a real participant cancelling on signal invalidation would
   suffer fewer of the worst fills, and no cancellation-latency assumption is smuggled in.
4. **No queue-jumping.** Joining at the back of the level is the most conservative queue position
   available; a participant could in principle improve it by joining earlier or by queue-position
   selection, which is neither assumed nor optimised here.
5. **Exit at the first message after fill + horizon.** The realized lag is recorded
   (`exit_lag_mean_ns`, `exit_lag_max_ns`) so a reader can see how tightly the exit clock tracks the
   requested horizon on these names.

## 4. How identifiability is tested rather than asserted

Three counters are produced by the replay itself, per attempt and in aggregate, and are the
evidence that the displayed-FIFO model is or is not a faithful description of this tape:

* `priority_anomalies` / `priority_anomaly_shares` — an execution hit a displayed order that was
  **not** resting ahead of us while quantity that **was** resting ahead of us remained queued. Under
  plain FIFO this cannot happen; every occurrence is a case where either an unmodelled priority
  attribute applied or the ranking assumption is wrong.
* `orphan_executes`, `orphan_cancels`, `orphan_deletes`, `orphan_replaces` — events that reference
  an order the feed never showed as live. Any non-zero count bounds reconstruction defects.
* `hidden_flow_shares` versus `executed_shares_at_level` — the size of the invisible (non-displayed)
  flow at our price relative to the visible flow that is allowed to fill us. This is the width of
  the assumption in section 3.2.

`K1_QUEUE_NON_IDENTIFIABLE` in the frozen decision rule fires if priority anomalies or orphan
executions exceed 1% of fill events, in which case the honest terminal state is `EXTERNAL_BLOCK`
(modern order-level data plus a queue-truth source), not a fabricated fill model.

## 5. Verification status summary

| property | status |
|---|---|
| displayed order identity and lifecycle | `VERIFIED` (provider specification, read directly) |
| feed ordering equals engine ordering | `VERIFIED` (provider specification, FPGA product note) |
| cancel-replace loses priority | `VERIFIED` (provider specification) |
| reserve replenishment receives a new timestamp | `SUPPORTED_FINDING` (SEC approval order quoting Nasdaq Equity 4, Section 4703(h)) |
| displayed-before-non-displayed priority ranking | `UNKNOWN` (verbatim rule text not retrievable; search exhausted). Not required by the model: violating it only makes the measured fill count optimistic |
| odd-lot participation in the displayed book | `SUPPORTED_FINDING` (Stock Directory semantics) |
| equal-timestamp tie-break | `UNKNOWN` (unstated in the specification; bounded by the anomaly counters) |
