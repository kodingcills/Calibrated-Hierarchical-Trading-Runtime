# Calibrated Hierarchical Trading Runtime — M1-A Discovery, Evidence Lock, and Candidate Elimination

## Research State, Core Findings, and Coverage Map

**Milestone status: M1-A INCOMPLETE.** This pass produced a usable external-evidence substrate and several hard eliminations, but it does **not** meet the project's stopping criterion for a locked M1-A artifact. Two reasons are decisive. First, `Jev Trading Research Paper.pdf` and `trading_research_os_v0.2.zip` were not retrievable in this research environment, so their claims could not be audited against external evidence. Second, several facts that can change candidate survival—current venue-specific fees, historical order-level data availability/cost, queue reconstructability, signal decay, and after-cost replication on the actual proposed venue—remain unresolved.

The strongest conclusion is negative but decision-useful: **public evidence establishes that short-horizon order-book state contains predictive information; it does not establish that a small non-colocated operation can monetize that predictability net of current execution costs.** Queue imbalance predicted the direction of the next mid-price movement in a 2015 study of ten liquid Nasdaq stocks, especially in large-tick names; Cont, Kukanov, and Stoikov found a robust short-horizon relationship between order-flow imbalance and price changes in 50 U.S. equities; and the micro-price literature develops imbalance-sensitive estimators of future price. None of those results, by itself, supplies a current 2026 net-of-fees, net-of-slippage strategy result for CME equity futures, Nasdaq equities, or crypto venues. citeturn9academia36turn10search24turn10search28turn10search5

A second conclusion is much firmer: **venue economics can dominate model quality.** At the lowest Coinbase Exchange volume tier, a taker pays 60 bps and a maker 40 bps; two taker fills therefore cost 120 bps in exchange trading fees before spread, slippage, impact, or adverse selection. At Kraken's current Tier 1, spot maker/taker rates are 0.40%/0.80%, making two taker fills 1.60%, or 160 bps, before all other costs. These schedules do not prove that every short-horizon strategy on those venues is unprofitable, but they kill ordinary low-volume, aggressive microprice/one-tick hypotheses unless there is venue-specific evidence for gross movement vastly larger than the microstructure effects found in the cited literature. citeturn20view0turn18view2

A third conclusion is that **data availability is not equivalent to replay sufficiency**. CME's current MDP architecture supports full-depth Market by Order and Market by Price via UDP multicast/SBE; Nasdaq TotalView supplies full displayed depth and NOII auction-imbalance information; and Eurex's current T7 release documents EOBI, EMDI and ETI interfaces. But Nasdaq's easier-to-access U.S. Equity Tick History is explicitly consolidated **Level 1** history, not order-level queue history. A strategy that requires queue-position reconstruction therefore cannot substitute that L1 dataset for historical ITCH/MBO. citeturn17view6turn12search8turn16search12turn17view7

Hyperliquid is another useful example of why schema inspection matters. Its public WebSocket documentation exposes BBO, trades and an `l2Book`; the L2 feed may be requested at five or twenty levels, and the documented `WsBook` is a snapshot feed pushed on blocks at least 0.5 seconds apart. That is potentially useful at seconds-to-minutes horizons, but it is not an adequate observation channel for a 10–100 ms queue-reaction hypothesis. The L2 levels include price, aggregate size and number of orders rather than exchange-style individual-order queue identifiers. citeturn20view1

Finally, **current venue rules are heterogeneous enough that generic “futures,” “equities,” or “crypto” scoring would be invalid**. CME explicitly documents product/market-data-specific structures, including full-depth MBO and MBP, while its matching logic can vary by product; Cboe BZX's September 2026 equity schedule contains a standard $0.0016/share rebate for displayed added liquidity and a $0.0030/share charge for removing liquidity in securities priced at or above $1; Coinbase and Kraken have strongly volume-dependent percentage fee schedules; and Eurex maintains separate low-latency order-book and trading interfaces. citeturn17view6turn1search35turn1search3turn18view0turn20view0turn18view2turn17view7

**Epistemic status of these findings**

| Claim | Status | Decision implication |
|---|---|---|
| Short-horizon book imbalance/OFI contains predictive information in at least some electronic equity markets | **SUPPORTED FINDING** | Worth testing; not evidence of tradable alpha |
| Predictive accuracy is sufficient to overcome present-day fees/fills/adverse selection | **UNKNOWN** | Blocks M1 survival as a profitable hypothesis |
| Exact signal half-life on the proposed 2026 venues | **UNKNOWN** | Must be measured rather than inferred from “next tick” papers |
| Full-depth live data is technically available from CME and Nasdaq, and a low-latency order-book interface exists at Eurex | **CONSENSUS FACT / primary-source fact** | Data acquisition is physically possible for some venue classes |
| Consolidated Nasdaq Tick History is sufficient for queue replay | **False for the stated requirement** | It is L1 and cannot establish individual-order queue position |
| Low-tier Coinbase/Kraken aggressive fees are material enough to kill ordinary tiny-move HFT hypotheses | **SUPPORTED FINDING plus arithmetic inference** | Strong fast kill |
| Hyperliquid public L2 is suitable for 10–100 ms queue inference | **Contradicted by documented feed cadence for this use** | Kill H1/public-feed tuple |
| System-One/Jev adds execution-aware utility | **UNKNOWN** | Remains locked out under the project's admission rule |

**Research coverage map.** The pass concentrated on primary venue specifications and current fee pages for CME, Nasdaq, Cboe, Eurex, Coinbase, Kraken and Hyperliquid; primary empirical work on queue imbalance, order-flow imbalance and microprice; and current regulatory/access leads for event markets. CME MDP, Nasdaq TotalView/Tick History, Cboe September 2026 pricing, Eurex T7 14.1, Coinbase fee tiers, Kraken fee tiers and Hyperliquid public feed schemas received the strongest source coverage. citeturn17view5turn17view6turn16search12turn18view0turn17view7turn20view0turn18view2turn20view1

Coverage remains materially weaker for NYSE/IEX exact 2026 fees and direct-feed history, Deribit fee/data/access details, Kalshi and Polymarket nationwide access/fees/API history, institutional FX venues, current CME customer/FCM all-in fees, Eurex execution fees, Nasdaq main-book small-prop fee tiers, data-vendor price quotations, and modern independent after-cost replications of the candidate microstructure signals. Cboe's current options fee schedule was located and is effective September 1, 2026, but the class/order-type-specific economics were not decomposed far enough for an options tuple to clear an execution gate. citeturn16search30

No paid Bloomberg, Refinitiv, BMLL, MayStreet/LSEG or exchange historical dataset was actually acquired in this pass. Consequently, claims requiring those datasets are marked **UNKNOWN**, not inferred from marketing material.

## Annotated Evidence Ledger

The ledger below separates venue facts from empirical results. “Net treatment” asks whether an empirical result actually incorporated trading costs rather than merely predicting a price variable.

| ID | Claim | Source and exact temporal context | Methodology / sample | Gross vs. net | Limitation | Epistemic status |
|---|---|---|---|---|---|---|
| E-01 | CME's current MDP supports event-based SBE market data; CME MDP Premium supports MBO Full Depth and MBP | CME MDP current documentation, accessed Sept. 20, 2026 | Official technical specification; not an empirical sample | N/A | Does not itself establish historical-data price or strategy economics | **CONSENSUS FACT** citeturn17view5turn17view6 |
| E-02 | CME's direct MDP uses dual-feed UDP multicast and MDP 3.0/SBE | Current CME documentation | Official systems specification | N/A | Network availability is not the same as inexpensive retail/broker access | **CONSENSUS FACT** citeturn17view5 |
| E-03 | CME matching behavior is not safely modeled as one universal FIFO rule across all products | CME matching-process materials and a CME service notice changing Treasury calendar-spread matching | Official venue rules/change notice | N/A | Exact matching rule must be looked up per candidate instrument | **CONSENSUS FACT** citeturn1search35turn1search3 |
| E-04 | Nasdaq TotalView exposes displayed depth/order information and NOII exposes auction imbalance information | Nasdaq TotalView-ITCH current product documentation | Official feed description | N/A | Feed availability does not establish a profitable imbalance strategy | **CONSENSUS FACT** citeturn12search8turn16search20 |
| E-05 | Nasdaq U.S. Equity Tick History is consolidated Level-1 tick data, with history back to Jan. 2014 | Current Nasdaq page | Official historical-data description | N/A | Explicitly insufficient for individual-order queue reconstruction | **CONSENSUS FACT** citeturn16search12 |
| E-06 | Cboe BZX standard rates for stocks ≥$1 are a $0.0016/share displayed-add rebate and $0.0030/share remove fee | Fee schedule effective Sept. 1, 2026 | Official current exchange schedule | Actual exchange fee/rebate, not total execution cost | Volume tiers, special fee codes, routing, CAT/broker/clearing and realized fills still matter | **CONSENSUS FACT** citeturn18view0 |
| E-07 | Coinbase's $0–$10k tier is 60 bps taker / 40 bps maker; $400m+ is 4/0 bps outside its liquidity program | Current Coinbase Exchange fee page accessed Sept. 20, 2026 | Official current schedule | Actual exchange fee only | Account/program eligibility can change realized economics | **CONSENSUS FACT** citeturn20view0 |
| E-08 | Kraken Tier 1 spot is 0.40% maker / 0.80% taker, with rates declining at high volume/assets | Current Kraken schedule accessed Sept. 20, 2026 | Official current schedule | Actual platform fee only | Does not include spread, slippage, impact or funding | **CONSENSUS FACT** citeturn18view2 |
| E-09 | Hyperliquid public WebSocket includes BBO, trades and L2; `WsBook` provides price, size and number of orders; documented L2 snapshots are block-cadenced with ≥0.5 s between pushes | Current Hyperliquid API documentation accessed Sept. 20, 2026 | Official API schema | N/A | Aggregate L2 is not exchange-style MBO; fee schedule was not verified in this pass | **CONSENSUS FACT** citeturn20view1 |
| E-10 | Hyperliquid info/API endpoints operate for spot and perpetuals; time-range responses may require pagination | Current Hyperliquid API documentation | Official API specification | N/A | Does not establish full historical L2 replay availability | **CONSENSUS FACT** citeturn20view2turn20view3 |
| E-11 | Eurex T7 14.1 provides EOBI, market/reference data interfaces and ETI documentation | Manuals dated Feb.–Mar. 2026; network docs updated Aug. 2026 | Official technical documentation | N/A | Fee, matching-rule and historical replay economics still need instrument-specific verification | **CONSENSUS FACT** citeturn17view7 |
| E-12 | Queue imbalance predicts next mid-price direction for the studied Nasdaq stocks, especially large-tick stocks | Gould & Bonart, 2015; ten liquid Nasdaq stocks | Logistic regression, next-price-move prediction | Primarily predictive/gross; not a current full execution result | Old sample; venue/market regime changed; next-tick accuracy ≠ net P&L | **SUPPORTED FINDING** citeturn9academia36 |
| E-13 | Short-horizon price changes are strongly related to order-flow imbalance and inversely related to market depth | Cont, Kukanov & Stoikov; 50 U.S. stocks using NYSE TAQ | Event/order-flow empirical analysis across stocks/time scales | Price-impact relationship; not a sealed net strategy | Equity sample cannot be silently transferred to CME/crypto; publication is not current-venue proof | **SUPPORTED FINDING** citeturn10search24turn10search28 |
| E-14 | Microprice can improve on midpoint as an estimator by incorporating order-book imbalance | Stoikov, 2018 | High-frequency price estimator | Predictive estimator, not after-cost strategy evidence | No justification for treating microprice accuracy as economic edge | **SUPPORTED FINDING** citeturn10search5 |
| E-15 | Nasdaq IPO opening involves a display-only period of at least ten minutes in which orders may be cancelled before the opening process | Current Nasdaq IPO process | Official market-process documentation | N/A | IPO opening is a special event, not ordinary continuous trading | **CONSENSUS FACT** citeturn16search16 |
| E-16 | Event-market access cannot be assumed uniform across U.S. states; Washington obtained a 2026 court order affecting Kalshi operations in the state | Washington Attorney General, 2026 | Government legal notice | N/A | Does not by itself establish nationwide status of every Kalshi contract | **CONSENSUS FACT for Washington; broader access UNKNOWN** citeturn7search32 |

Several distinctions follow directly from this ledger.

First, **E-12 through E-14 are evidence for information content, not profit**. A model can predict the next tick better than chance and still have negative expected economic value because the conditional move may be smaller than spread, fees and adverse selection. citeturn9academia36turn10search24turn10search5

Second, **the evidence is cross-venue, not interchangeable**. Cont et al.'s U.S. equity findings are useful for forming an OFI hypothesis, but applying their coefficients or decay to ES, NQ, Hyperliquid BTC perpetuals or Eurex futures would be an **EXTRAPOLATION**. citeturn10search24turn10search28

Third, **there is no verified empirical half-life in the current evidence package for any proposed tuple**. “Next tick,” “short horizon,” and “predictive” do not constitute a measured economic half-life. M2 must estimate the delay-to-EV curve rather than manufacture an exponential decay parameter.

## Market, Venue, Data, and Execution Fact Ledgers

The table intentionally contains many `UNKNOWN` cells. Those cells are not omissions to be smoothed over; they are the facts preventing premature candidate promotion.

| Instrument / venue class | Structure and live observability | Matching / queue facts | Verified fee facts | Historical / replay state | Access constraint | Status |
|---|---|---|---|---|---|---|
| **ES/NQ / CME Globex** | Electronic futures; CME MDP Premium supports full-depth MBO plus MBP over SBE/UDP. citeturn14search1turn17view6 | Product-specific matching must be verified; universal FIFO assumption is unsafe. citeturn1search35turn1search3 | **UNKNOWN** for the exact small-prop/FCM all-in tuple in this pass | CME Data Services advertises historical/real-time products including up to full order book, but exact MBO history, license and cost for this project were not locked. citeturn14search6 | Direct CME connectivity exists; economical broker/direct path and measured latency remain unverified. citeturn17view5 | **Data feasible; execution envelope incomplete** |
| **Treasury futures / CME-CBOT** | CME MDP architecture applies; fixed-income security definitions are documented in MDP 3.0. citeturn14search0turn17view6 | A CME notice explicitly demonstrates that Treasury calendar-spread matching algorithms can change. citeturn1search3 | **UNKNOWN** | Full replay specifics/cost not locked | FCM/direct-feed arrangement required | **UNKNOWN** |
| **Energy futures / CME-NYMEX** | CME MDP data infrastructure available. citeturn17view5turn17view6 | Instrument-specific rule required | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** |
| **Eurex equity/rates futures** | T7 14.1 has EOBI, EMDI/MDI and ETI; 2026 network guides are current. citeturn17view7 | Exact product allocation rule not locked in this pass | **UNKNOWN** | Historical order-level acquisition/cost **UNKNOWN** | Participant/broker route and economic feasibility **UNKNOWN** | **UNKNOWN** |
| **Nasdaq U.S. equities / continuous** | TotalView gives full displayed depth/order information. citeturn12search8turn16search20 | Exact queue/matching semantics for a chosen order type still need rulebook lock | Main-book small-prop fee tier **UNKNOWN** | Easily verified Tick History is only consolidated L1; L3/ITCH historical procurement remains a separate requirement. citeturn16search12 | Fragmentation means one venue book is not the whole national market | **Potentially data-feasible; historical queue replay unresolved** |
| **Nasdaq opening/closing/IPO processes** | NOII/auction information is available; IPO process includes a minimum ten-minute display-only period. citeturn12search8turn16search16 | Auction-specific, not continuous-book queue logic | Exact relevant cross/auction fees **UNKNOWN** | Historical NOII depth/cost not locked | Accessible only if order types/timing can be replicated PIT | **Observable mechanism; economic edge UNKNOWN** |
| **Cboe BZX equities** | U.S. equity CLOB venue; Cboe runs BZX/BYX/EDGA/EDGX. citeturn16search26 | Queue details need candidate-specific rule lookup | ≥$1 standard displayed add rebate $0.0016/share; remove $0.0030/share, effective Sept. 1, 2026. citeturn18view0 | Historical order-level source not locked | Broker/membership routing changes realized fee codes | **Fee facts strong; fill economics unresolved** |
| **U.S. listed options / Cboe venues** | Multiple options venues and current schedules exist | Complex order priority and class-specific mechanics require separate hypotheses | Cboe schedule located, effective Sept. 1, 2026, but exact class/order fees not decomposed. citeturn16search30 | OPRA vs proprietary depth history not locked | Fragmentation, options symbology and many fee codes | **UNKNOWN** |
| **Coinbase spot / BTC-USD-type book** | Centralized maker-taker exchange | Queue semantics not researched deeply enough for replay | $0–10k: 60 bps taker / 40 bps maker; tiers fall with 30-day volume. citeturn20view0 | Required historical L2/L3 schema not locked in this pass | U.S. access broadly practical, but account/program-specific fee eligibility matters | **Aggressive low-tier H1–H4 severely cost-constrained** |
| **Kraken spot** | Centralized maker-taker market | Queue semantics not locked | Tier 1 0.40% maker / 0.80% taker; material reductions require volume/assets. citeturn18view2 | Historical order-book replay not locked | Product availability varies by geography; Kraken notes product availability constraints. citeturn18view2 | **Aggressive low-tier microstructure tuple killed below** |
| **Kraken perps** | Kraken currently describes perpetual products, geography-dependent | **UNKNOWN** | Kraken page states 0.25% notional to open and 0.25% on closing notional for the referenced perp product, availability geography-dependent. citeturn18view2 | **UNKNOWN** | Geography material | **Cost/access constrained; no survivor** |
| **Hyperliquid perpetuals** | Public API exposes L2, trades, BBO and account-state information; L2 can be 5/20 levels. citeturn20view1turn20view2 | L2 reports aggregate price/size/order count, not an MBO queue ID; documented book feed is block/snapshot-based. citeturn20view1 | **UNKNOWN in this evidence lock** | Exact historical event-by-event L2/MBO source not verified; info endpoints paginate some time-range results. citeturn20view2 | Legal/account/access assessment not completed | **H1 public-feed tuple dead; slower tuples UNKNOWN** |
| **Deribit crypto options** | Venue remains relevant to crypto options research, but current primary specifications were not sufficiently locked | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | Current jurisdictional/access state not locked | **UNKNOWN** |
| **Kalshi** | Regulated event-market venue class, but this pass did not lock API/fee schema | Contract-specific | **UNKNOWN** | **UNKNOWN** | State-level access can differ; Washington 2026 restriction is direct evidence against assuming universal U.S. availability. citeturn7search32 | **UNKNOWN / access-blocked until resolved** |
| **Polymarket** | Candidate event-market class | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | Current U.S. jurisdiction/access requires fresh primary verification | **UNKNOWN** |
| **Institutional FX / ECN** | Distinct from retail broker feeds | Venue-specific, potentially last-look/RFQ/CLOB differences | **UNKNOWN** | **UNKNOWN** | Institutional onboarding/capital may dominate feasibility | **UNKNOWN** |
| **Retail FX broker feed** | Broker-specific price/execution | Not safely treated as institutional price discovery | **UNKNOWN** | Broker-specific | Broker is part of execution mechanism | **UNKNOWN** |

**Data feasibility matrix.**

| Candidate data need | Minimum acceptable field set | Verified source state | PIT assessment | M1 effect |
|---|---|---|---|---|
| CME queue/OFI | Order add/modify/delete/trade, sequence, side, price, size, security definition, receive/exchange timing where available | Live MBOFD/MBP verified through MDP Premium. citeturn17view6 | Technically plausible live | Historical procurement/cost remains **blocking** for queue replay |
| Nasdaq queue imbalance | TotalView/ITCH order events; executions/cancels; timestamps; cross/NOII where relevant | Live/full-depth product verified. citeturn12search8turn16search20 | Plausible if direct historical ITCH is procured | Consolidated L1 Tick History is **not sufficient**. citeturn16search12 |
| Nasdaq auction imbalance | NOII message state, auction reference/indicative price, imbalance side/size, exact dissemination timestamp | NOII existence verified. citeturn12search8 | Potentially PIT | Historical NOII source/cost unresolved |
| Cboe passive execution | Full proprietary book events + own-order acknowledgments for live; fee code | Fee schedule verified, data history not | Unknown | Queue/fill model cannot yet be calibrated |
| Coinbase/Kraken aggressive crypto | BBO/L2/trades with exchange timestamps and exact account fee tier | Fee side is verified; data package not locked | Unknown | Fees already kill some low-tier tuples without needing fill simulation |
| Hyperliquid seconds-scale book | `l2Book`, trades, BBO, timestamps, asset context | Live public schema verified. citeturn20view1turn20view2 | Good enough to construct PIT snapshots at documented cadence | Not suitable for H1; slower historical availability still unresolved |
| Eurex queue/OFI | EOBI order-book messages and instrument reference data | Interface documentation verified. citeturn17view7 | Technically plausible | Historical data/access/fees unresolved |
| Options surface | Quotes across strikes/expiries, trades, NBBO/proprietary depth, greeks derived PIT from contemporaneous state | Not sufficiently locked | Unknown | Options RV/VRP candidates cannot pass Gate 2 yet |

**Execution envelope matrix.**

| Venue / tuple family | Fee state | Queue/fill concern | Adverse selection | Latency class | Colocation dependency | Gate result |
|---|---|---|---|---|---|---|
| CME H1 queue/depletion | Exact all-in cost unknown | Critical; MBO helps reconstruct book but own queue/fills still need simulator | Critical | 10–100 ms | Potentially material; not quantitatively established here | **WEAK / unresolved** |
| CME H3 OFI aggressive | Exact all-in cost unknown | Lower queue concern if crossing | Spread + slippage still critical | 1–15 s | Raw colo race less obviously dispositive, but measured delay-to-EV missing | **UNKNOWN** |
| Nasdaq H2 queue imbalance aggressive | Exact Nasdaq fee tier unknown | Signal observable, fill simpler when crossing | Crossing after imbalance can select into already-moving price | 100 ms–1 s | May be material | **UNKNOWN** |
| Nasdaq passive spread capture | Fee/rebate not locked for Nasdaq main book | First-order problem | First-order problem | H2/H3 | Potentially material | **WEAK** |
| Cboe BZX passive add | $0.0016/share standard displayed-add rebate at ≥$1; remove $0.003/share. citeturn18view0 | Queue and partial fills unmeasured | Central risk | H2/H3 | Unknown | **WEAK** |
| Coinbase low-tier aggressive | 60 bps each taker fill. citeturn20view0 | Minimal queue issue when marketable | Still additional to fee | H1–H4 | Irrelevant to primary kill reason | **DEAD for ordinary tiny-move microstructure thesis** |
| Kraken Tier-1 aggressive spot | 80 bps each taker fill. citeturn18view2 | Minimal queue issue when marketable | Additional | H1–H4 | Irrelevant to primary kill reason | **DEAD for ordinary tiny-move microstructure thesis** |
| Hyperliquid H1 public L2 | Fee unknown | Aggregate rather than MBO queue | Unknown | 10–100 ms | Public feed itself is too coarse for the hypothesized observation loop | **DEAD as specified** |
| Hyperliquid H3/H4 | Fee unknown | Aggregate L2 | Unknown | 1 s–5 min | Public API physically plausible for observation | **UNKNOWN** |
| Eurex H2/H3 | Fees/matching unresolved | Requires EOBI-aware replay | Unknown | 100 ms–15 s | Network path must be measured | **UNKNOWN** |

The most important result here is methodological: **`touch = fill` is disallowed by the evidence**. A passive strategy's economics cannot be evaluated from price paths alone. It needs queue evolution, partial-fill logic, cancellation behavior and markout conditional on fill. None of the current sources gives a portable numeric fill probability, so no fill rate is estimated.

## Mechanism Taxonomy and Candidate Kill-Gate Ledger

The mechanism review deliberately separates “there is a phenomenon” from “we have an economic edge.”

| Mechanism | Economic interpretation | Payer / transfer source | Observable signature | Likely horizon class | Evidence status | Strongest critique / unresolved issue |
|---|---|---|---|---|---|---|
| **Order-flow imbalance** | Net aggressive demand relative to available liquidity moves price | Urgent liquidity demand; exact motive is an **EXTRAPOLATION** | Signed book/trade events versus depth | H1–H3 | **SUPPORTED FINDING** in U.S. equities. citeturn10search24turn10search28 | Current venue-specific net edge and decay are unknown |
| **Queue imbalance/depletion** | One side's displayed queue is more vulnerable than the other | Liquidity demand and cancellations | Bid/ask queue-size asymmetry, depletion | H1–H3 | **SUPPORTED FINDING** for next-price direction in studied Nasdaq names. citeturn9academia36 | 2015 result; execution cost and latency may consume it |
| **Microprice** | Imbalance-adjusted fair-price estimator | Not itself a payer mechanism | Midpoint adjusted by book state | H1–H3 | **SUPPORTED FINDING as estimator**. citeturn10search5 | Better estimator does not imply executable alpha |
| **Liquidity replenishment failure** | Book fails to refill after aggressive flow | Liquidity suppliers withdrawing under toxicity | Depth recovery rate/cancel-add dynamics | H2–H3 | **EXTRAPOLATION** from order-flow literature | No current direct replication locked |
| **Adverse-selection avoidance** | Value comes from *not* providing liquidity when informed/urgent flow arrives | Avoided losses to toxic takers | Conditional post-fill markouts | H2–H4 | **CONTESTED/UNMEASURED here** | Requires real/simulated fills, not just forecasts |
| **Spread capture** | Passive trader earns spread/rebate for warehousing inventory/liquidity risk | Aggressive traders pay immediacy | Passive fills and subsequent markout | H2–H4 | Mechanical fee/spread structure exists; profitability **UNKNOWN** | Queue + adverse selection can reverse gross spread |
| **Inventory effects** | Dealer/MM inventory creates temporary pressure | Risk-averse liquidity suppliers/takers | Price response conditional on inferred inventory | H3–H5 | **UNKNOWN** | Inventory is usually latent |
| **Volatility transitions** | Regime shifts may alter conditional edge and execution cost | Risk transfer | Book thinning, trade intensity, realized vol | H3–H5 | **UNKNOWN** | Regime classification can lag and costs rise precisely in transitions |
| **Forced liquidation cascades** | Leveraged positions are mechanically closed | Liquidated accounts | Liquidation events, rapid directional flow, leverage state | H2–H4 | Mechanically plausible; direct edge evidence **UNKNOWN** | Need marketwide PIT liquidation data and after-cost decay |
| **Stop cascades** | Price triggers clustered conditional market orders | Stop holders | Burst flow near salient levels | H2–H4 | **CONTESTED HYPOTHESIS** | Stop inventory often unobservable ex ante |
| **Funding/basis dislocation** | Position demand creates a carry wedge between venues/instruments | Leveraged directional demand / balance-sheet users | Funding, futures basis, borrow/carry | H4–H5+ | **UNKNOWN in this lock** | Capital, funding, borrow and regime risk matter |
| **Calendar roll effects** | Mandated migration between expiries creates predictable flow | Hedgers/indexed mandates | Spread volume/OI migration around roll | H4–H5+ | **UNKNOWN here** | Highly visible and professionally arbitraged |
| **Index/rebalance flows** | Funds must trade to benchmark composition/weight changes | Benchmark-tracking mandates | Published changes plus closing flow/auction imbalance | H4–H5 | Structural mechanism plausible; net edge **UNKNOWN** | Anticipation/crowding may transfer gains to earlier participants |
| **Auction imbalances** | Benchmark/close demand is concentrated into a clearing event | Funds seeking benchmark execution | NOII/indicative price/imbalance | H3–H5 | **OBSERVABLE FACT** on Nasdaq. citeturn12search8turn16search16 | Observability does not establish excess return after auction impact |
| **Cross-venue lead–lag** | One venue discovers price first | Slower venue participants | Conditional lag after source-venue move | H1–H3 | **UNKNOWN** | Likely highly latency-sensitive; stale quotes may vanish before fill |
| **Fragmented stale pricing** | Routing/fragmentation leaves temporary price discrepancies | Participants posting stale liquidity | Cross-book crossed/locked/stale state | H1–H2 | **UNKNOWN** | Most obvious forms invite dedicated low-latency competition |
| **Options surface relative value** | Relative mispricing across strikes/expiries | Hedgers/flow imbalance | Residual versus surface model | H4–H5+ | **UNKNOWN** | Model risk, spreads, legging, vol/spot hedging and fee complexity |
| **Dealer hedging / gamma effects** | Option inventory can induce predictable hedging demand | Option dealers/users | Spot flow conditional on option positioning | H4–H5 | **CONTESTED HYPOTHESIS** in this package | Dealer positioning is imperfectly observed; causal attribution difficult |
| **Volatility risk premium** | Investors pay to transfer crash/variance risk | Protection buyers | Implied versus realized volatility | H5+ | Established research area but **not adequately audited here for this M1 tuple** | Risk premium is compensation for tail risk, not necessarily alpha |
| **Fee/rebate effects** | Venue incentives change optimal provision/routing behavior | Venue/participants via fee schedule | Fill economics conditional on fee code | H2–H5 | **CONSENSUS FACT that incentives differ materially**. citeturn18view0turn20view0turn18view2 | Rebate harvesting without adverse-selection modeling is invalid |
| **Market-design quirks** | Rules create localized flow/priority effects | Participants constrained by rules | Order-type/matching-event signatures | Any | **SUPPORTED as venue heterogeneity** | Must be evaluated one rule and one venue at a time |
| **Event/news latency** | Public information is incorporated at different speeds | Slower information processors | Timestamped event → market reaction | H1–H5 | **UNKNOWN** | Lowest-latency version is likely infrastructure-dominated; semantic model value must beat faster baselines |
| **Behavioral flow** | Recurrent human/institutional behavior creates conditional demand | Behaviorally constrained traders | Time/event-conditioned flow | H4–H5+ | **UNKNOWN** | Easy to overfit calendar patterns |
| **Horizon mismatch** | Large institutions cannot optimize tiny capacity opportunities | Mandate/capacity-constrained large participants | Small-capacity repeatable micro-edge | H3–H5 | **CONTESTED HYPOTHESIS** | Must demonstrate the opportunity is actually too small or operationally unattractive to larger firms |
| **Balance-sheet-constrained liquidity provision** | Capital/risk limits make compensation for warehousing risk persistent | Hedgers/liquidity demanders | Spreads/basis increase when balance sheet scarce | H4–H5+ | **STRUCTURALLY PLAUSIBLE, empirical lock incomplete** | Often earns a risk premium rather than pure alpha |

The **candidate tuple ledger** follows. `ALIVE` is deliberately not used merely because a signal looks promising. A candidate can only earn that label after the five invariants are sufficiently evidenced. On that standard, no tuple is yet `ALIVE`.

| Tuple | Status | Kill-gate / evidence assessment | Remaining M1 question |
|---|---|---|---|
| `<ES, CME, H1 10–100ms, queue depletion, passive>` | **WEAK** | Live MBO is feasible, but exact matching/queue, all-in fees, fill model and delay-to-EV are unresolved. citeturn17view6turn1search35 | Can a non-colocated path retain positive conditional markout after queue/adverse selection? |
| `<ES, CME, H3 1–15s, OFI continuation, aggressive>` | **UNKNOWN** | Mechanism supported in equities, not current ES; full-depth observation feasible. citeturn10search24turn17view6 | Current ES effect size/decay versus spread + fees + slippage |
| `<NQ, CME, H3, OFI continuation, aggressive>` | **UNKNOWN** | Same cross-market extrapolation issue as ES | Venue-specific current replication and costs |
| `<Treasury future, CME, H2/H3, queue/replenishment, mixed>` | **UNKNOWN** | Data architecture exists; product-specific matching can change. citeturn1search3turn17view6 | Instrument matching, fees and empirical effect |
| `<WTI, CME, H4, flow/volatility transition, aggressive>` | **UNKNOWN** | No modern venue-specific edge evidence locked | Economic payer, half-life and event treatment |
| `<large-tick stock, Nasdaq, H2 100ms–1s, queue imbalance, aggressive>` | **WEAK** | Direct empirical support exists but is old and gross; live depth feasible; historical L3 procurement and current net economics unresolved. citeturn9academia36turn12search8 | Modern replication after fee + spread + latency |
| `<large-tick stock, Nasdaq, H2/H3, microprice, aggressive>` | **WEAK** | Estimator evidence exists; profit evidence does not. citeturn10search5 | Does calibration improve execution-aware utility over OFI/logistic baseline? |
| `<Nasdaq stock, H4, closing-auction imbalance, auction order>` | **UNKNOWN** | NOII makes mechanism observable; no locked current net edge. citeturn12search8 | Conditional return after imbalance publication and auction execution cost |
| `<BZX stock, H2/H3, spread capture, passive>` | **WEAK** | Fee/rebate known; queue/adverse-selection economics unknown. citeturn18view0 | Fill-conditioned markout distribution |
| `<BTC-USD, Coinbase, H3, microprice/OFI, aggressive at $0–10k tier>` | **DEAD** | 60 bps taker each way implies 120 bps round-trip exchange fees before spread/slippage; no supporting evidence for that gross edge on a seconds-scale microprice strategy. citeturn20view0turn10search5 | New evidence or radically different fee tier would be required to resurrect |
| `<BTC/USD, Kraken, H3, microprice/OFI, aggressive Tier 1>` | **DEAD** | 80 bps taker each way → 160 bps round-trip trading fee before spread/slippage. citeturn18view2 | Same |
| `<BTC perp, Hyperliquid public WS, H1 10–100ms, queue depletion, aggressive/passive>` | **DEAD** | Documented L2 observation cadence is incompatible with a 10–100 ms market-state reaction thesis. citeturn20view1 | A fundamentally different direct observation path would constitute a new tuple |
| `<BTC perp, Hyperliquid, H3 1–15s, OFI/liquidation, aggressive>` | **UNKNOWN** | L2/trades are observable, but fee schedule, historical event replay, marketwide liquidation observability and effect size are not locked. citeturn20view1turn20view2 | All four of those items |
| `<BTC perp, Hyperliquid, H4, funding/basis, mixed>` | **UNKNOWN** | API infrastructure is usable; economic evidence incomplete | Funding/basis history, costs, capital and cross-venue hedge |
| `<FESX/DAX future, Eurex, H2/H3, OFI/queue, mixed>` | **UNKNOWN** | EOBI/ETI make technical observation/trading plausible; costs, matching and empirical edge not locked. citeturn17view7 | Exact instrument economics and current signal replication |
| `<US option, Cboe venue, H5, surface relative value, mixed>` | **UNKNOWN** | Current fee schedule exists but tuple-specific economics and historical surface data not locked. citeturn16search30 | Full data/hedging/fee execution envelope |
| `<BTC options, Deribit, H5, surface RV, mixed>` | **UNKNOWN** | Required current access/fee/data facts were not verified | Gate 2 before mechanism scoring |
| `<event contract, Kalshi, H5, event/news inference, aggressive>` | **UNKNOWN** | Access cannot be assumed nationally; Washington provides direct contrary evidence. citeturn7search32 | Contract legality/access, API timing, fee and fill mechanics |
| `<event contract, Polymarket, H5, event/news/cross-market, aggressive>` | **UNKNOWN** | Current primary access and execution facts insufficient | Regulatory and venue-data lock |
| `<US stock cross-venue, H1, stale quote, aggressive>` | **WEAK** | Attractive in theory but likely demands fast cross-feed and routing; no evidence package establishing non-colocated feasibility | Measure source→decision→venue latency and stale-quote survival |
| `<institutional FX pair, ECN, H2/H3, lead-lag, aggressive>` | **UNKNOWN** | Venue/feed/access not specified tightly enough | Must first define one exact ECN and participant class |
| `<retail FX pair, broker, H3/H4, broker-feed lag, aggressive>` | **UNKNOWN** | Broker-specific execution is part of the hypothesis | Define broker, last-look/execution policy and actual data |

This is intentionally **not a ranking**. A `WEAK` candidate is not “better” than an `UNKNOWN` candidate; it simply has more evidence against or constraining it.

No formal **Edge Provenance Memo** is issued at this stage because no candidate has passed all of economic mechanism, observability, half-life, execution envelope and persistence. Doing so would prematurely convert a partially evidenced tuple into an apparent survivor.

For the two best-studied *mechanism classes*, however, the provenance state can already be bounded without promoting them:

**CME equity-index OFI, H3.** The empirically supported mechanism is that net order flow relative to available depth is associated with short-horizon price change in electronic limit-order markets. The proposed payer—urgent liquidity demand—is an **EXTRAPOLATION**, not something measured in the cited study. CME can expose the necessary order-book state through MBOFD/MBP. But the literature used here does not measure ES/NQ's current economic half-life, and exact project-level all-in fees/slippage remain unresolved. Therefore this does **not** pass the execution invariant. citeturn10search24turn10search28turn17view6

**Nasdaq queue imbalance, H2/H3.** The 2015 study gives direct next-move evidence on Nasdaq stocks, and TotalView provides the kind of current full-depth information needed for a live signal. The structural payer is again not irrationality: a plausible mechanism is that urgent liquidity demand and heterogeneous order urgency leave observable asymmetry. That payer interpretation is an **EXTRAPOLATION**. The major disconfirmation is that the result is old, primarily predictive, and not evidence that a small 2026 operation can cross the spread or win passive queue competition profitably. Historical consolidated L1 data also cannot support the required fill/queue replay. citeturn9academia36turn12search8turn16search12

## Technology Fit and System-One Admission State

Nothing discovered in M1-A creates an exception to the project's System-One lockout.

The central technology question is not whether a model can predict direction. It is whether, on identical point-in-time information,

\[
\Delta U
=
U_{\text{execution-aware}}(\text{System-One policy})
-
U_{\text{execution-aware}}(\text{classical policy})
>0
\]

on sealed data after all modeled execution costs.

No evidence in the external research establishes that inequality.

| Candidate class | Rules / deterministic | Logistic / LightGBM / XGBoost | Local neural | Local System-One | Hosted Jev | Frontier LLM | Current assessment |
|---|---|---|---|---|---|---|---|
| H1 10–100 ms queue reaction | **Candidate baseline**; actual runtime must be measured | **Candidate baseline** if engineered locally | Possible only after local p99 profiling | **Not admitted without measured incremental value and latency** | **Not admitted**; no verified p99 evidence | **Not admitted** | Latency budget too tight to allocate to semantic sophistication without proof |
| H2 100 ms–1 s OFI/queue | Strong baseline | Strong baseline | Candidate | Candidate only after baseline/calibration test | **UNKNOWN / locked out by default** | **UNKNOWN / locked out by default** | Model complexity must justify decision-to-market delay |
| H3 1–15 s OFI/toxicity | Strong baseline | Strong baseline | Plausible | Potentially testable | Physically unresolved until p99 is measured | Potentially testable only as noncritical judgment | This is the first horizon where semantic/selective inference could be experimentally considered without presuming value |
| H4 15 s–5 min auction/regime/liquidation context | Strong baseline | Strong baseline | Plausible | Plausible experimental challenger | Plausible only after real latency/reliability measurement | Plausible for semantic event processing, not hard execution | Economic value rather than raw speed becomes easier to test |
| H5 minutes+ options/event/funding | Strong baseline | Strong baseline | Plausible | Plausible | Plausible from latency standpoint, still economically unproven | Plausible for unstructured information | Execution/risk arithmetic remains deterministic regardless |

This matrix means **physical plausibility only**; it is not a recommendation.

The strongest current use case for a System-One-like model is therefore not queue arithmetic or raw price direction. Its conceivable incremental roles remain selective judgments such as regime/toxicity classification, heterogeneous evidence composition, or semantic event interpretation—precisely where a same-information classical policy can be built and falsified. That conclusion follows from the project policy, not from evidence that Jev is profitable.

The following functions remain categorically outside hosted Jev/System-One ownership under the supplied research policy: arithmetic, explicit expected-utility computation, hard risk, Kelly-style sizing from semantic confidence, queue mechanics and latency-critical order dispatch. Nothing found externally argues for relaxing that boundary.

**Probability quality is also not one scalar problem.** A model can be well calibrated for event probabilities yet badly calibrated economically if, for example, its high-confidence predictions occur exactly when spreads/adverse selection are largest. Consequently, M2 eventually needs separate diagnostics for statistical probability calibration, selective/abstention performance, conformal coverage where applicable, and realized conditional utility. This is an experiment-design inference, not a claim that any specific method will improve P&L.

Most importantly, **hosted Jev latency remains UNKNOWN**. No M1 source verified its complete request-to-decision p50/p95/p99, network path, failure tail, rate-limit behavior or availability under trading-like load. It therefore cannot be assigned an H1–H3 role by assumption.

## Disconfirming Evidence, Discrepancies, and Unknowns

The disconfirming ledger is deliberately more prominent than an “opportunities” list because the dominant M1 failure mode is mistaking statistical information for obtainable economic surplus.

| Thesis under attack | Strongest disconfirming evidence | Why it matters | Severity |
|---|---|---|---|
| “Queue imbalance is an edge” | The cited Nasdaq evidence predicts a next price move; it does not establish current net profitability. citeturn9academia36 | Classification accuracy can coexist with negative EV | **Blocking** |
| “OFI works everywhere because market microstructure is universal” | Empirical support cited here is for a particular U.S.-equity sample; CME, Eurex and crypto have different fees, matching and participants. citeturn10search24turn10search28turn17view6turn17view7 | Coefficients/decay cannot be transferred silently | **Blocking** |
| “Microprice improves midpoint, therefore trade it” | Microprice is an estimator; the evidence does not prove its prediction exceeds execution cost. citeturn10search5 | Prevents model-metric → P&L fallacy | **Blocking** |
| “Historical L1 is enough for passive backtesting” | Nasdaq explicitly calls its Tick History consolidated Level 1. citeturn16search12 | Queue priority, cancellations and order-level state are missing | **Blocking** |
| “Maker rebate = spread-capture edge” | BZX simultaneously has removal fees, and the schedule says nothing about fill-conditioned adverse selection. citeturn18view0 | Rebate can be compensation for being selected against | **Blocking** |
| “Crypto is easier because APIs are public” | Coinbase and Kraken low-tier fees are very large relative to ordinary microstructure horizons. citeturn20view0turn18view2 | Public accessibility can coexist with poor unit economics | **Blocking for specified low-tier aggressive tuples** |
| “Hyperliquid public data supports sub-100-ms alpha” | Public `l2Book` is documented as a block/snapshot feed with at least 0.5 s between pushes. citeturn20view1 | Signal cannot be observed at the hypothesized horizon | **Fatal to H1 tuple** |
| “Full-depth data solves fill simulation” | Full depth describes public book state, not the actual live latency/ack path of the research system; product matching rules also matter. citeturn17view6turn1search35 | Own-order queue position and race conditions remain model-dependent | **Blocking for passive M2** |
| “Auction imbalance is free alpha” | Nasdaq proves the information is disseminated publicly through NOII, which means sophisticated competitors can observe it too. citeturn12search8 | Persistence must come from risk/capacity/mandates, not secrecy | **Important** |
| “Any U.S.-facing event market is simply accessible” | Washington's 2026 Kalshi action is direct evidence that state-level restrictions can matter. citeturn7search32 | Legal/access status is part of the tuple | **Blocking before experiment** |
| “One fee number describes U.S. equities” | Cboe's fee table contains standard rates plus many special fee codes and routing outcomes. citeturn18view0 | Backtests need actual route/order-type assumptions | **Important** |
| “One CME queue model describes CME” | CME documents product-specific matching processes and has changed Treasury spread matching rules. citeturn1search35turn1search3 | Queue simulator must be product-specific | **Blocking for passive candidate** |

**Material discrepancies and unknowns ledger**

**Current CME execution cost.**  
**Claim needed:** exact marginal cost for an ES/NQ/Treasury/energy candidate under the brokerage/membership arrangement available to the project.  
**Checked:** CME product/MDP documentation and market-data infrastructure.  
**Conflict:** none; the problem is incompleteness. Exchange fee, clearing fee, NFA/FCM commission and data/connectivity are distinct cost components.  
**Status:** **UNKNOWN, blocking.**  
**Resolution:** obtain current CME/FCM schedule for the actual account path and register it as an immutable M2 cost configuration.  
**Research result:** **Search exhausted within this run; could not verify the project's exact all-in CME per-contract execution cost.**

**CME historical MBO acquisition.**  
CME currently confirms full-depth live MBOFD and offers historical/real-time data products, but the exact history depth, licensing, delivery format and project cost for candidate products were not sufficiently locked. citeturn14search6turn17view6  
**Status:** **UNKNOWN, blocking for queue-based M2.**  
**Resolution:** vendor/exchange quote plus sample-file schema validation.  
**Research result:** **Search exhausted within this run; could not verify the exact historical MBO package and cost required for queue replay.**

**Nasdaq historical queue data.**  
Nasdaq's consolidated Tick History is L1, while TotalView is the full-depth product. citeturn16search12turn12search8  
There is no contradiction: they are different products. The risk is accidentally backtesting a queue strategy on the easier L1 product.  
**Status:** **Historical ITCH package, price and licensing UNKNOWN; blocking.**

**Nasdaq/Cboe current economics.**  
Cboe BZX rates are current and explicit, but the chosen Nasdaq main-book fee tier and routing economics were not locked. Cboe itself illustrates why “equity fee” is not one number: standard and special fee codes differ. citeturn18view0  
**Status:** **Important/blocking once an equity tuple is specified.**

**Hyperliquid fee and historical replay.**  
The public live schema is well specified, including L2 levels, timestamps and feed cadence. citeturn20view1turn20view2  
The trading-fee schedule and a sufficiently precise historical L2 source were not verified in the evidence collected.  
**Status:** **Blocking for net-edge evaluation.**  
**Research result:** **Search exhausted within this run; could not verify the exact current Hyperliquid maker/taker fee schedule and historical L2 replay product needed for the proposed tuples.**

**Signal half-life.**  
The queue-imbalance paper uses next-price-move prediction, while the OFI literature establishes short-horizon relationships. Neither supplies the needed current tuple-specific curve

\[
EV(\delta)
\]

for delay \(\delta\). citeturn9academia36turn10search24  
**Status:** **UNKNOWN for every serious candidate; M2 measurable.**  
**Required measurement:** replay each candidate signal at controlled delays—e.g. 0, 10, 25, 50, 100, 250, 500 ms, 1 s, 2 s, 5 s where physically appropriate—and report both gross conditional markout and execution-aware EV. The grid is an experiment-design proposal, not an asserted market half-life.

**Passive fill probability.**  
No defensible universal fill probability was found, and none should be borrowed from another market.  
**Status:** **UNKNOWN; M2 measurable if proper order-level data exist.**  
A simulator must maintain ahead-of-order quantity under the venue's actual matching rule, distinguish executions from cancellations where the feed allows it, support partial fills, and validate simulated markouts against shadow/live observations.

**Eurex fees, matching and historical EOBI data.**  
Current EOBI/ETI/market-data documentation is strong evidence of technical feasibility, but not of economic accessibility for this project. citeturn17view7  
**Status:** **UNKNOWN; blocking before any Eurex candidate moves beyond universe status.**

**Deribit.**  
Current options venue relevance alone is not enough. Exact 2026 U.S./project access, fees, API semantics and historical book/surface data were not locked from primary sources in this pass.  
**Status:** **UNKNOWN; Gate 2 not passed.**

**Kalshi/Polymarket.**  
The Washington Kalshi order demonstrates that state-level legal status can matter. citeturn7search32  
A nationwide statement about either platform requires current contract- and jurisdiction-specific primary research.  
**Status:** **UNKNOWN/blocking.**  
**Research result:** **Search exhausted within this run; could not verify a complete September 20, 2026 jurisdiction-by-jurisdiction access matrix, exact fee schedule, and historical API package for Kalshi and Polymarket.**

**Institutional FX.**  
“FX” is not a candidate. A valid tuple requires an exact ECN/venue, participant status, feed, order protocol and last-look/execution mechanics.  
**Status:** **UNKNOWN; universe definition incomplete.**

**Jev/System-One artifact audit.**  
The supplied prompt says the Jev paper is a candidate architecture specimen and the Research OS is methodological source of truth. Those files were not retrievable in this run, so no paper claim about profitability, calibration transfer, Kelly sizing, latency, costs or architecture was audited.  
**PROJECT SOURCE CLAIM:** unavailable for document-level inspection.  
**EXTERNAL VERIFIED EVIDENCE:** none should be attributed to the paper.  
**CURRENT ASSESSMENT:** System-One remains unadmitted; no positive economic claim is carried forward from it.

## Dead Candidate Cemetery and Decision Impact

The cemetery is version-worthy because these are not casual dislikes; each entry identifies the fact that must change before resurrection.

| Dead hypothesis | Kill gate | Exact cause of death | Resurrection condition |
|---|---|---|---|
| `<BTC-USD, Coinbase, H3, microprice/OFI, aggressive, $0–10k tier>` | **Execution envelope** | 60 bps taker per fill gives 120 bps round-trip exchange trading fees before spread/slippage/adverse selection; no venue-specific evidence establishes the required seconds-scale gross edge. citeturn20view0turn10search5 | Materially lower verified fee tier **and** sealed evidence that gross conditional movement clears total costs |
| `<BTC/USD, Kraken, H3, microprice/OFI, aggressive, Tier 1>` | **Execution envelope** | 0.80% taker per fill → 1.60% round-trip before all other costs. citeturn18view2 | Different verified fee economics plus evidence of enough gross edge |
| `<BTC perp, Hyperliquid public l2Book, H1 10–100 ms, queue depletion>` | **Data feasibility / compute-fit boundary** | Public book snapshot cadence documented at ≥0.5 s between pushes; observation is slower than the hypothesis horizon. citeturn20view1 | A materially different authenticated/direct feed with verified sub-100-ms state information |
| `<Nasdaq stock, H1/H2, queue position, using only consolidated Tick History>` | **Data feasibility** | Historical product is Level 1; individual queue reconstruction is impossible from that dataset alone. citeturn16search12 | Acquire order-level historical TotalView/ITCH or equivalent |
| `Passive spread-capture backtest with touch = fill` | **Execution integrity** | The proposed fill rule omits queue and adverse selection, so it cannot answer the economic question | Validated queue-aware simulator/shadow-fill process |
| `Generic “crypto microstructure” strategy` | **Universe-definition gate** | Not a valid unit of analysis; Coinbase, Kraken and Hyperliquid have materially different fees/data mechanics. citeturn20view0turn18view2turn20view1 | Reformulate as an exact instrument × venue × horizon × mechanism × execution tuple |
| `Generic “CME queue strategy”` | **Market-structure definition** | CME matching processes are product-specific; a generic queue model is unjustified. citeturn1search35turn1search3 | Specify product/order type and implement the actual matching rule |
| `System-One/Jev as direct arithmetic, sizing, queue-math or hard-risk engine` | **Project admission policy** | Violates the governing separation of deterministic computation/risk from probabilistic judgment; no external evidence supplies an exception | New governance decision plus overwhelming evidence; not an M1 trading hypothesis |
| `Hosted Jev assumed to be latency-feasible without measurement` | **Technology admission** | Request-to-market p99 is unverified; no signal half-life is established against which to compare it | Reproducible latency profile and candidate-specific EV-versus-delay curve |

Several attractive ideas are **not** in the cemetery because insufficient evidence is not evidence of impossibility. Nasdaq auction imbalance, CME H3 OFI, slower Hyperliquid flow/liquidation signals, Eurex OFI, options relative value, funding/basis and event-market strategies remain `UNKNOWN` or `WEAK`, not dead.

The immediate decision impact of M1-A is therefore narrower and more useful than a premature shortlist:

**The research should not spend M2 engineering effort on low-tier aggressive Coinbase/Kraken microstructure, public-feed Hyperliquid H1, L1-only passive queue simulations, or any strategy whose fill model equates quote touch with execution.** Those branches already fail on observable facts. citeturn20view0turn18view2turn20view1turn16search12

**The order-book-predictability literature earns only the right to run venue-specific execution-aware tests.** It does not earn production architecture, capital allocation, a System-One layer, or even an `ALIVE` M1 label. citeturn9academia36turn10search24turn10search5

**The next gate is primarily empirical, not architectural.** Before a candidate can be promoted to `ALIVE`, the evidence substrate must contain, for that exact tuple: current fee schedule; historical PIT feed schema; modern venue-specific predictive replication; measured signal decay; replay with spread/slippage/adverse-selection treatment; and, for passive execution, queue-aware fill modeling. No model family should be chosen before those quantities are available.

The M2 experiment skeleton that is already justified—but **not yet a registered M2 hypothesis**—is:

\[
\text{raw PIT events}
\rightarrow
\text{causal state}
\rightarrow
\text{simple signal}
\rightarrow
\text{delay sweep}
\rightarrow
\text{execution model}
\rightarrow
\text{net conditional utility}.
\]

The baseline order should start with deterministic imbalance/microprice formulas and logistic/tree models, because the primary literature already shows that simple order-book variables have information content. Only after those same-information baselines are sealed should local neural/System-One variants be admitted. citeturn9academia36turn10search24turn10search5

The minimum measurements that could change survival status are:

| Measurement | Decision changed |
|---|---|
| Exact account-level fee/commission schedule | Kills or preserves aggressive execution |
| Historical MBO/L3 sample with timestamp semantics | Determines whether causal replay is possible |
| Gross conditional markout versus signal quantile | Establishes whether predictive information has economically relevant magnitude |
| EV versus artificial delay | Establishes half-life and permissible compute/network budget |
| Passive fill probability conditional on queue state | Determines whether apparent spread capture is real |
| Fill-conditioned markout | Measures adverse selection |
| Cost sensitivity at conservative fee/slippage assumptions | Tests execution-envelope robustness |
| Same-information logistic/tree baseline | Sets System-One burden of proof |
| Shadow/live latency p50/p95/p99 | Determines which model/venue/horizon pairings are physically admissible |
| Sealed post-cost out-of-sample utility | Determines promotion or kill |

No weighted ranking is appropriate yet. Too many dimensions that would drive any score—net-edge headroom, half-life, passive fill quality, current historical-data cost and exact venue fees—are `UNKNOWN`. Assigning numerical values would turn missing evidence into fabricated precision.

**M1-A INCOMPLETE**

The exact blocking research still required is:

1. **Project-source audit:** retrieve and audit `Jev Trading Research Paper.pdf` and `trading_research_os_v0.2.zip`, explicitly separating project-source claims from external verification.
2. **CME lock:** exact ES/NQ/Treasury candidate tick/contract/order rule, matching allocation, current exchange + clearing + FCM fees, historical MBO product/schema/cost, and a modern venue-specific OFI/queue replication.
3. **U.S.-equity lock:** historical TotalView/ITCH or equivalent L3 procurement; exact Nasdaq/NYSE/IEX/Cboe candidate fee and order rules; auction-history source; fragmented-market routing assumptions.
4. **Crypto lock:** current Hyperliquid fee schedule/historical replay/access; Deribit current options fees/data/access; exact Coinbase/Kraken data schemas where a non-dead execution style remains under consideration.
5. **Event-market lock:** primary-source September 2026 Kalshi/Polymarket access, fee, matching/API and historical-data facts; state/jurisdiction differences must be encoded as venue-access constraints, not footnotes.
6. **Eurex lock:** exact candidate product, matching rule, execution fee, historical EOBI source/cost and broker/participant access path.
7. **Empirical half-life:** no serious candidate currently has a verified actionable information half-life. This must be obtained from venue-specific delay sweeps; it must not be imported from “next-tick” papers.
8. **Execution reality gap:** every passive candidate needs queue-aware replay and fill-conditioned adverse-selection evidence; every aggressive candidate needs a conservative spread/fee/slippage envelope.
9. **Modern disconfirmation search:** the surviving OFI/queue/microprice mechanisms require current independent evidence specifically seeking post-cost failure, crowding, market-structure drift and disappearance.
10. **Technology measurement:** only after an economic candidate survives should local rules/tree/neural/System-One and hosted Jev be latency-profiled on identical information, with System-One judged solely on incremental execution-aware net utility.

Until those blocks are cleared, proceeding to M1-B comparative selection would violate the evidence-lock requirement: it would force ranking on dimensions that are presently unknown rather than measured.