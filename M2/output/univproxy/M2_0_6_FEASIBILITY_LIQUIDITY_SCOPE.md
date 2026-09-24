# M2-0.5 — AGGRESSIVE MONETIZATION FEASIBILITY BOUND

Candidate `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` · run `M2-0-6-NASDAQ-QIMB-UNIVPROXY` · development sample day `2019-07-30` · dataset `NASDAQ-ITCH50-PUBLIC-SAMPLE-20190730` · cost ledger `M2-COST-LEDGER-v1`

**No data was acquired, no model was trained, no threshold was optimised, Jev was not used, M1 and the research framework were not modified, and no artifact of M2-0 was rewritten.** This pass reads the frozen M2-0 development artifacts and conditions the existing aggressive execution arithmetic on the predeclared state space. It promotes nothing and kills nothing.

| item | value |
|---|---|
| execution instant | delay_decisions.parquet, delay 0 ms (the M2-0 idealized aggressive instant) |
| observations (level 0) | 2,691,000 valid decision states of 2,691,000 delay rows |
| observations (level 1) | 2,458,422 with a defined signal side (imbalance != 0) |
| state space | 10 imbalance bins x 2 spread classes x 5 price bands = 100 cells per horizon, 400 rows over 4 horizons |
| cost regimes | structural_floor, accessible_fixed, accessible_tiered (round trip, 100-share representative size) |
| config sha256 | 2ec5f58afeb2cf7462cb896642a53ccba62f26b0dfba0885cea57eb814b50119 |
| cost ledger sha256 | 52ce785fc7210138af4059e327fc7101dff7f78dff3f5156c045973c1ed4cb17 |
| code sha256 | M2/src/feasibility.py 855eccc6ca438ff6… |
| derived artifacts | decisions.parquet 4ce1082fe3bd7548…; delay_decisions.parquet 6fe1aba7a9923514… |

## 0. Observation accounting

The delay-0 slice of `delay_decisions.parquet` is a 1 s decimation of the predeclared 100 ms decision grid and carries the realised future two-sided quote that a cross-to-cross result requires. It is verified below (check `execution_instant_is_decision_instant`) to reproduce `decisions.parquet` exactly at the same `(ts_ns, locate)` on every row, so no observation is invented and none is redefined.

| observation set | count | note |
|---|---|---|
| delay rows at delay 0 | 2,691,000 | 1 s grid, 61 development-scope symbols |
| valid decision states | 2,691,000 | two-sided, uncrossed, arrival present |
|     of which imbalance == 0 | 232,578 | in the state space but with no sign to trade; kept in the oracle set, excluded from side-dependent cells (the M2-0 execution filter) |
| signal-defined observations | 2,458,422 | imbalance != 0; the base of every state-conditioned cell |
| outside the declared price bands | 0 | none: every observation falls in one of the five declared bands |
| future quote missing at 100 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 250 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 500 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 1000 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| imbalance == 0 at 100 ms | 232,578 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 250 ms | 232,578 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 500 ms | 232,578 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 1000 ms | 232,578 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| outside the declared state space at 100 ms | 0 signal / 0 valid | no declared price band contains the observation; excluded from the cells and counted, never folded in |
| outside the declared state space at 250 ms | 0 signal / 0 valid | no declared price band contains the observation; excluded from the cells and counted, never folded in |
| outside the declared state space at 500 ms | 0 signal / 0 valid | no declared price band contains the observation; excluded from the cells and counted, never folded in |
| outside the declared state space at 1000 ms | 0 signal / 0 valid | no declared price band contains the observation; excluded from the cells and counted, never folded in |

Declared dimensions: price bands are applied to the decision-instant mid in USD; a mid exactly on a band edge falls in the upper band; an observation outside every declared band would be reported as unbinned, never dropped.

## 1. Aggressive cross-to-cross economics by declared state (request §1)

`gross future mid move` is the unsigned mid-to-mid move over the horizon; `entry-to-future-mid markout` and `cross-to-cross` are side-adjusted (side = sign(imbalance)) with the entry at the far touch; the three `result` columns subtract the ledger round trip of the named regime. Every number is in bps of the arrival mid, except the fee columns which are the ledger's own bps of entry notional. All 400 cells are in `aggressive_feasibility_by_state.csv`; no cell is withheld and no winner is selected.

### 1a. Pooled over the whole declared state space, by horizon

| horizon ms | obs | mid move | signed mid move | markout | cross-to-cross | spread paid | fee structural_floor | net structural_floor | net accessible_fixed | net accessible_tiered | P(net>0) structural_floor |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 2,458,422 | 0.0004 | 0.0104 | -2.9021 | -5.8129 | 5.8232 | 0.9533 | -6.7662 | -8.2256 | -7.6603 | 0.0004 |
| 250 | 2,458,422 | 0.0015 | 0.0211 | -2.8914 | -5.8023 | 5.8234 | 0.9533 | -6.7557 | -8.2151 | -7.6497 | 0.0009 |
| 500 | 2,458,422 | 0.0011 | 0.0348 | -2.8777 | -5.7878 | 5.8226 | 0.9533 | -6.7411 | -8.2005 | -7.6352 | 0.0018 |
| 1000 | 2,458,422 | 0.0003 | 0.0578 | -2.8547 | -5.7633 | 5.8211 | 0.9533 | -6.7167 | -8.1761 | -7.6107 | 0.0041 |

### 1b. By spread class

| horizon ms | spread class | obs | spread bps | signed mid move | cross-to-cross | net structural_floor | net accessible_fixed | net accessible_tiered | P(net>0) structural_floor |
|---|---|---|---|---|---|---|---|---|---|
| 100 | ONE_TICK | 711,075 | 2.1720 | 0.0139 | -2.1661 | -3.7178 | -6.5104 | -5.3276 | 0.0006 |
| 100 | WIDER_THAN_ONE_TICK | 1,747,347 | 7.3116 | 0.0090 | -7.2969 | -8.0067 | -8.9236 | -8.6095 | 0.0003 |
| 250 | ONE_TICK | 711,075 | 2.1720 | 0.0284 | -2.1595 | -3.7111 | -6.5038 | -5.3210 | 0.0015 |
| 250 | WIDER_THAN_ONE_TICK | 1,747,347 | 7.3116 | 0.0181 | -7.2848 | -7.9946 | -8.9115 | -8.5974 | 0.0007 |
| 500 | ONE_TICK | 711,075 | 2.1720 | 0.0478 | -2.1503 | -3.7020 | -6.4946 | -5.3118 | 0.0031 |
| 500 | WIDER_THAN_ONE_TICK | 1,747,347 | 7.3116 | 0.0295 | -7.2680 | -7.9779 | -8.8947 | -8.5807 | 0.0013 |
| 1000 | ONE_TICK | 711,075 | 2.1720 | 0.0793 | -2.1346 | -3.6863 | -6.4789 | -5.2961 | 0.0069 |
| 1000 | WIDER_THAN_ONE_TICK | 1,747,347 | 7.3116 | 0.0490 | -7.2400 | -7.9499 | -8.8667 | -8.5527 | 0.0029 |

### 1c. By price band

| horizon ms | price band | obs | mean price | spread bps | signed mid move | cross-to-cross | fee structural_floor | fee accessible_fixed | fee accessible_tiered | net structural_floor | net accessible_fixed | net accessible_tiered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 100-200 | 737,368 | 138.18 | 5.2111 | 0.0093 | -5.2005 | 0.6714 | 1.5026 | 1.2282 | -5.8719 | -6.7031 | -6.4287 |
| 100 | 200+ | 652,387 | 481.76 | 7.2210 | 0.0054 | -7.2135 | 0.4005 | 0.6280 | 0.6332 | -7.6141 | -7.8415 | -7.8468 |
| 100 | 25-50 | 235,875 | 39.31 | 4.9674 | 0.0206 | -4.9456 | 1.8408 | 5.2778 | 3.7965 | -6.7864 | -10.2234 | -8.7421 |
| 100 | 5-25 | 43,419 | 13.81 | 15.7665 | 0.0172 | -15.7451 | 6.8402 | 21.4178 | 14.7767 | -22.5853 | -37.1630 | -30.5219 |
| 100 | 50-100 | 789,373 | 73.85 | 4.9542 | 0.0121 | -4.9401 | 1.0846 | 2.8365 | 2.1357 | -6.0247 | -7.7766 | -7.0758 |
| 250 | 100-200 | 737,368 | 138.18 | 5.2111 | 0.0187 | -5.1913 | 0.6714 | 1.5026 | 1.2282 | -5.8627 | -6.6939 | -6.4195 |
| 250 | 200+ | 652,387 | 481.76 | 7.2210 | 0.0117 | -7.2074 | 0.4005 | 0.6280 | 0.6332 | -7.6079 | -7.8353 | -7.8406 |
| 250 | 25-50 | 235,875 | 39.31 | 4.9674 | 0.0428 | -4.9216 | 1.8408 | 5.2778 | 3.7965 | -6.7624 | -10.1994 | -8.7182 |
| 250 | 5-25 | 43,419 | 13.81 | 15.7665 | 0.0381 | -15.7301 | 6.8402 | 21.4178 | 14.7767 | -22.5703 | -37.1479 | -30.5068 |
| 250 | 50-100 | 789,373 | 73.85 | 4.9542 | 0.0237 | -4.9290 | 1.0846 | 2.8365 | 2.1357 | -6.0136 | -7.7654 | -7.0646 |
| 500 | 100-200 | 737,368 | 138.18 | 5.2111 | 0.0292 | -5.1794 | 0.6714 | 1.5026 | 1.2282 | -5.8509 | -6.6820 | -6.4077 |
| 500 | 200+ | 652,387 | 481.76 | 7.2210 | 0.0185 | -7.2019 | 0.4005 | 0.6280 | 0.6332 | -7.6025 | -7.8299 | -7.8352 |
| 500 | 25-50 | 235,875 | 39.31 | 4.9674 | 0.0724 | -4.8919 | 1.8408 | 5.2778 | 3.7965 | -6.7327 | -10.1697 | -8.6884 |
| 500 | 5-25 | 43,419 | 13.81 | 15.7665 | 0.0436 | -15.7196 | 6.8402 | 21.4178 | 14.7767 | -22.5598 | -37.1374 | -30.4964 |
| 500 | 50-100 | 789,373 | 73.85 | 4.9542 | 0.0419 | -4.9088 | 1.0846 | 2.8365 | 2.1357 | -5.9934 | -7.7452 | -7.0444 |
| 1000 | 100-200 | 737,368 | 138.18 | 5.2111 | 0.0468 | -5.1594 | 0.6714 | 1.5026 | 1.2282 | -5.8309 | -6.6621 | -6.3877 |
| 1000 | 200+ | 652,387 | 481.76 | 7.2210 | 0.0328 | -7.1851 | 0.4005 | 0.6280 | 0.6332 | -7.5856 | -7.8131 | -7.8183 |
| 1000 | 25-50 | 235,875 | 39.31 | 4.9674 | 0.1228 | -4.8405 | 1.8408 | 5.2778 | 3.7965 | -6.6813 | -10.1183 | -8.6371 |
| 1000 | 5-25 | 43,419 | 13.81 | 15.7665 | 0.0816 | -15.6904 | 6.8402 | 21.4178 | 14.7767 | -22.5306 | -37.1082 | -30.4671 |
| 1000 | 50-100 | 789,373 | 73.85 | 4.9542 | 0.0679 | -4.8822 | 1.0846 | 2.8365 | 2.1357 | -5.9668 | -7.7186 | -7.0178 |

### 1d. By imbalance bin and horizon (structural floor)

| horizon ms | imbalance bin | obs | spread paid | signed mid move | cross-to-cross | net structural_floor | P(net>0) structural_floor |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 259,416 | 5.3694 | 0.0028 | -5.3666 | -6.5491 | 0.0003 |
| 100 | [-0.4,-0.2) | 341,450 | 5.8173 | 0.0073 | -5.8100 | -6.8813 | 0.0004 |
| 100 | [-0.6,-0.4) | 216,442 | 5.5789 | 0.0127 | -5.5662 | -6.6124 | 0.0004 |
| 100 | [-0.8,-0.6) | 169,523 | 5.9565 | 0.0179 | -5.9386 | -6.8594 | 0.0003 |
| 100 | [-1.0,-0.8) | 239,823 | 6.5330 | 0.0138 | -6.5192 | -7.1817 | 0.0004 |
| 100 | [0.0,0.2) | 270,249 | 5.3814 | 0.0031 | -5.3783 | -6.4083 | 0.0003 |
| 100 | [0.2,0.4) | 349,323 | 5.7533 | 0.0075 | -5.7458 | -6.7070 | 0.0003 |
| 100 | [0.4,0.6) | 217,698 | 5.5471 | 0.0146 | -5.5325 | -6.4970 | 0.0004 |
| 100 | [0.6,0.8) | 167,147 | 5.9688 | 0.0179 | -5.9509 | -6.8613 | 0.0005 |
| 100 | [0.8,1.0] | 227,351 | 6.5246 | 0.0156 | -6.5089 | -7.1838 | 0.0003 |
| 250 | [-0.2,0.0) | 259,416 | 5.3671 | 0.0054 | -5.3617 | -6.5443 | 0.0007 |
| 250 | [-0.4,-0.2) | 341,450 | 5.8174 | 0.0126 | -5.8048 | -6.8761 | 0.0009 |
| 250 | [-0.6,-0.4) | 216,442 | 5.5782 | 0.0265 | -5.5517 | -6.5980 | 0.0011 |
| 250 | [-0.8,-0.6) | 169,523 | 5.9563 | 0.0366 | -5.9196 | -6.8405 | 0.0011 |
| 250 | [-1.0,-0.8) | 239,823 | 6.5348 | 0.0270 | -6.5078 | -7.1703 | 0.0008 |
| 250 | [0.0,0.2) | 270,249 | 5.3802 | 0.0085 | -5.3717 | -6.4017 | 0.0007 |
| 250 | [0.2,0.4) | 349,323 | 5.7527 | 0.0163 | -5.7364 | -6.6976 | 0.0008 |
| 250 | [0.4,0.6) | 217,698 | 5.5470 | 0.0294 | -5.5176 | -6.4821 | 0.0010 |
| 250 | [0.6,0.8) | 167,147 | 5.9716 | 0.0374 | -5.9343 | -6.8447 | 0.0011 |
| 250 | [0.8,1.0] | 227,351 | 6.5285 | 0.0313 | -6.4972 | -7.1720 | 0.0008 |
| 500 | [-0.2,0.0) | 259,416 | 5.3645 | 0.0091 | -5.3554 | -6.5379 | 0.0016 |
| 500 | [-0.4,-0.2) | 341,450 | 5.8157 | 0.0213 | -5.7945 | -6.8658 | 0.0019 |
| 500 | [-0.6,-0.4) | 216,442 | 5.5761 | 0.0471 | -5.5290 | -6.5753 | 0.0023 |
| 500 | [-0.8,-0.6) | 169,523 | 5.9585 | 0.0622 | -5.8963 | -6.8172 | 0.0025 |
| 500 | [-1.0,-0.8) | 239,823 | 6.5375 | 0.0464 | -6.4911 | -7.1536 | 0.0016 |
| 500 | [0.0,0.2) | 270,249 | 5.3776 | 0.0117 | -5.3659 | -6.3959 | 0.0014 |
| 500 | [0.2,0.4) | 349,323 | 5.7508 | 0.0256 | -5.7252 | -6.6864 | 0.0018 |
| 500 | [0.4,0.6) | 217,698 | 5.5449 | 0.0462 | -5.4987 | -6.4632 | 0.0020 |
| 500 | [0.6,0.8) | 167,147 | 5.9715 | 0.0631 | -5.9084 | -6.8188 | 0.0023 |
| 500 | [0.8,1.0] | 227,351 | 6.5306 | 0.0502 | -6.4805 | -7.1553 | 0.0016 |
| 1000 | [-0.2,0.0) | 259,416 | 5.3569 | 0.0194 | -5.3374 | -6.5200 | 0.0038 |
| 1000 | [-0.4,-0.2) | 341,450 | 5.8138 | 0.0369 | -5.7769 | -6.8483 | 0.0041 |
| 1000 | [-0.6,-0.4) | 216,442 | 5.5729 | 0.0747 | -5.4982 | -6.5444 | 0.0048 |
| 1000 | [-0.8,-0.6) | 169,523 | 5.9596 | 0.1032 | -5.8564 | -6.7772 | 0.0053 |
| 1000 | [-1.0,-0.8) | 239,823 | 6.5432 | 0.0805 | -6.4628 | -7.1253 | 0.0037 |
| 1000 | [0.0,0.2) | 270,249 | 5.3724 | 0.0159 | -5.3565 | -6.3865 | 0.0031 |
| 1000 | [0.2,0.4) | 349,323 | 5.7478 | 0.0421 | -5.7058 | -6.6669 | 0.0040 |
| 1000 | [0.4,0.6) | 217,698 | 5.5408 | 0.0774 | -5.4634 | -6.4279 | 0.0043 |
| 1000 | [0.6,0.8) | 167,147 | 5.9731 | 0.1019 | -5.8712 | -6.7816 | 0.0049 |
| 1000 | [0.8,1.0] | 227,351 | 6.5357 | 0.0815 | -6.4542 | -7.1290 | 0.0034 |

### 1e. The best and worst declared cells (descriptive only — nothing is selected)

| cell | obs | share of obs | spread bps | signed mid move | cross-to-cross | net structural_floor | block SE | block cells |
|---|---|---|---|---|---|---|---|---|
| [-1.0,-0.8) · ONE_TICK · $200+ · 250 ms | 1,050 | 0.0004 | 0.4724 | 0.0980 | -0.4521 | -0.9507 | 0.0654 | 42 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 500 ms | 1,050 | 0.0004 | 0.4724 | 0.1380 | -0.4579 | -0.9566 | 0.0593 | 42 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 100 ms | 1,050 | 0.0004 | 0.4724 | 0.0615 | -0.4592 | -0.9578 | 0.0388 | 42 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 1000 ms | 1,050 | 0.0004 | 0.4724 | 0.1745 | -0.4705 | -0.9691 | 0.0657 | 42 |
| [-0.8,-0.6) · ONE_TICK · $200+ · 100 ms | 1,332 | 0.0005 | 0.4751 | 0.0380 | -0.4800 | -0.9803 | 0.0089 | 36 |

Worst five cells by `net structural_floor`: [-0.2,0.0)/ONE_TICK/$5-25/500 ms = -26.1164 bps; [-0.2,0.0)/ONE_TICK/$5-25/250 ms = -26.1049 bps; [-0.2,0.0)/ONE_TICK/$5-25/1000 ms = -26.1037 bps; [-0.2,0.0)/ONE_TICK/$5-25/100 ms = -26.1026 bps; [0.0,0.2)/ONE_TICK/$5-25/500 ms = -25.6196 bps.

## 2. Break-even hurdles (request §2)

Hurdle A is the current quoted spread (cross in, cross out); B adds the structural floor round trip; C adds each accessible reference path. `realized_move_bps` is the side-signed mid move, so `realized > hurdle` is the break-even test and `P(realized > hurdle A)` equals `P(cross-to-cross > 0)` up to the measured spread-change term. Full distributions and ratios per cell are in `breakeven_hurdle.csv`; the pooled view is below.

| horizon ms | realized (mean) | required A (spread) | required structural_floor | required accessible_fixed | required accessible_tiered | P(>A) | P(>structural_floor) | P(>accessible_fixed) | P(>accessible_tiered) |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 0.0104 | 5.8250 | 6.7783 | 8.2377 | 7.6724 | 0.0006 | 0.0004 | 0.0001 | 0.0001 |
| 250 | 0.0211 | 5.8250 | 6.7783 | 8.2377 | 7.6724 | 0.0015 | 0.0009 | 0.0003 | 0.0003 |
| 500 | 0.0348 | 5.8250 | 6.7783 | 8.2377 | 7.6724 | 0.0030 | 0.0018 | 0.0006 | 0.0007 |
| 1000 | 0.0578 | 5.8250 | 6.7783 | 8.2377 | 7.6724 | 0.0061 | 0.0041 | 0.0013 | 0.0017 |

### 2a. Hurdle coverage by imbalance bin and horizon (mean realized move / mean required move, structural)

| horizon ms | imbalance bin | obs | realized | required | coverage | P(realized > B) | P(QIMB bound > 0) |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 259,416 | 0.0028 | 6.5564 | 0.000 | 0.0004 | 0.0003 |
| 100 | [-0.4,-0.2) | 341,450 | 0.0073 | 6.8923 | 0.001 | 0.0005 | 0.0004 |
| 100 | [-0.6,-0.4) | 216,442 | 0.0127 | 6.6287 | 0.002 | 0.0006 | 0.0004 |
| 100 | [-0.8,-0.6) | 169,523 | 0.0179 | 6.8763 | 0.003 | 0.0006 | 0.0003 |
| 100 | [-1.0,-0.8) | 239,823 | 0.0138 | 7.1926 | 0.002 | 0.0006 | 0.0004 |
| 100 | [0.0,0.2) | 270,249 | 0.0031 | 6.4160 | 0.000 | 0.0004 | 0.0003 |
| 100 | [0.2,0.4) | 349,323 | 0.0075 | 6.7174 | 0.001 | 0.0005 | 0.0003 |
| 100 | [0.4,0.6) | 217,698 | 0.0146 | 6.5126 | 0.002 | 0.0006 | 0.0004 |
| 100 | [0.6,0.8) | 167,147 | 0.0179 | 6.8787 | 0.003 | 0.0007 | 0.0005 |
| 100 | [0.8,1.0] | 227,351 | 0.0156 | 7.1978 | 0.002 | 0.0006 | 0.0003 |
| 250 | [-0.2,0.0) | 259,416 | 0.0054 | 6.5564 | 0.001 | 0.0010 | 0.0007 |
| 250 | [-0.4,-0.2) | 341,450 | 0.0126 | 6.8923 | 0.002 | 0.0012 | 0.0009 |
| 250 | [-0.6,-0.4) | 216,442 | 0.0265 | 6.6287 | 0.004 | 0.0013 | 0.0011 |
| 250 | [-0.8,-0.6) | 169,523 | 0.0366 | 6.8763 | 0.005 | 0.0015 | 0.0011 |
| 250 | [-1.0,-0.8) | 239,823 | 0.0270 | 7.1926 | 0.004 | 0.0013 | 0.0008 |
| 250 | [0.0,0.2) | 270,249 | 0.0085 | 6.4160 | 0.001 | 0.0010 | 0.0007 |
| 250 | [0.2,0.4) | 349,323 | 0.0163 | 6.7174 | 0.002 | 0.0012 | 0.0008 |
| 250 | [0.4,0.6) | 217,698 | 0.0294 | 6.5126 | 0.005 | 0.0014 | 0.0010 |
| 250 | [0.6,0.8) | 167,147 | 0.0374 | 6.8787 | 0.005 | 0.0018 | 0.0011 |
| 250 | [0.8,1.0] | 227,351 | 0.0313 | 7.1978 | 0.004 | 0.0014 | 0.0008 |
| 500 | [-0.2,0.0) | 259,416 | 0.0091 | 6.5564 | 0.001 | 0.0021 | 0.0016 |
| 500 | [-0.4,-0.2) | 341,450 | 0.0213 | 6.8923 | 0.003 | 0.0023 | 0.0019 |
| 500 | [-0.6,-0.4) | 216,442 | 0.0471 | 6.6287 | 0.007 | 0.0027 | 0.0023 |
| 500 | [-0.8,-0.6) | 169,523 | 0.0622 | 6.8763 | 0.009 | 0.0030 | 0.0025 |
| 500 | [-1.0,-0.8) | 239,823 | 0.0464 | 7.1926 | 0.006 | 0.0023 | 0.0016 |
| 500 | [0.0,0.2) | 270,249 | 0.0117 | 6.4160 | 0.002 | 0.0019 | 0.0014 |
| 500 | [0.2,0.4) | 349,323 | 0.0256 | 6.7174 | 0.004 | 0.0024 | 0.0018 |
| 500 | [0.4,0.6) | 217,698 | 0.0462 | 6.5126 | 0.007 | 0.0026 | 0.0020 |
| 500 | [0.6,0.8) | 167,147 | 0.0631 | 6.8787 | 0.009 | 0.0032 | 0.0023 |
| 500 | [0.8,1.0] | 227,351 | 0.0502 | 7.1978 | 0.007 | 0.0026 | 0.0016 |
| 1000 | [-0.2,0.0) | 259,416 | 0.0194 | 6.5564 | 0.003 | 0.0044 | 0.0038 |
| 1000 | [-0.4,-0.2) | 341,450 | 0.0369 | 6.8923 | 0.005 | 0.0049 | 0.0041 |
| 1000 | [-0.6,-0.4) | 216,442 | 0.0747 | 6.6287 | 0.011 | 0.0056 | 0.0048 |
| 1000 | [-0.8,-0.6) | 169,523 | 0.1032 | 6.8763 | 0.015 | 0.0061 | 0.0053 |
| 1000 | [-1.0,-0.8) | 239,823 | 0.0805 | 7.1926 | 0.011 | 0.0050 | 0.0037 |
| 1000 | [0.0,0.2) | 270,249 | 0.0159 | 6.4160 | 0.002 | 0.0040 | 0.0031 |
| 1000 | [0.2,0.4) | 349,323 | 0.0421 | 6.7174 | 0.006 | 0.0051 | 0.0040 |
| 1000 | [0.4,0.6) | 217,698 | 0.0774 | 6.5126 | 0.012 | 0.0056 | 0.0043 |
| 1000 | [0.6,0.8) | 167,147 | 0.1019 | 6.8787 | 0.015 | 0.0064 | 0.0049 |
| 1000 | [0.8,1.0] | 227,351 | 0.0815 | 7.1978 | 0.011 | 0.0053 | 0.0034 |

`coverage` is mean realized move / mean required move (the hurdle); `P(realized > B)` is the per-observation probability that the side-signed mid move beats the current spread plus the structural floor fee; `P(QIMB bound > 0)` adds clairvoyant abstention inside the dictated side.

## 3. Oracle aggressive upper bound — ORACLE_UPPER_BOUND (request §3)

**ORACLE_UPPER_BOUND uses future information by construction: at each decision instant it takes max(0, net_long, net_short) from the realised future bid/ask. It bounds what any causal side choice at these instants could have earned; it is not a strategy, not achievable, and must never enter model training, a backtest or a promotion decision.**

At each decision instant the oracle takes `max(0, net_buy, net_sell)` using the realised future bid/ask. The `mean_oracle_net` columns are therefore per-observation upper bounds on *any* causal aggressive execution at these instants after that regime's costs. `mean_oracle_gross` is the same bound before costs, and `oracle_trade_fraction` is the share of instants at which trading beats abstaining.

| horizon ms | obs | oracle gross | oracle trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered | P(net>0) structural_floor | oracle net structural_floor (signal-defined) |
|---|---|---|---|---|---|---|---|---|
| 100 | 2,458,422 | 0.0015 | 0.0007 | 0.0009 | 0.0005 | 0.0006 | 0.0006 | 0.0009 |
| 250 | 2,458,422 | 0.0038 | 0.0018 | 0.0022 | 0.0012 | 0.0015 | 0.0015 | 0.0022 |
| 500 | 2,458,422 | 0.0082 | 0.0038 | 0.0049 | 0.0028 | 0.0034 | 0.0032 | 0.0049 |
| 1000 | 2,458,422 | 0.0186 | 0.0082 | 0.0114 | 0.0065 | 0.0079 | 0.0071 | 0.0113 |

### 3a. Oracle upper bound by imbalance bin (all valid states)

| horizon ms | imbalance bin | obs | oracle gross | trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 259,416 | 0.0010 | 0.0006 | 0.0005 | 0.0002 | 0.0003 |
| 100 | [-0.4,-0.2) | 341,450 | 0.0017 | 0.0008 | 0.0010 | 0.0005 | 0.0007 |
| 100 | [-0.6,-0.4) | 216,442 | 0.0020 | 0.0009 | 0.0012 | 0.0006 | 0.0008 |
| 100 | [-0.8,-0.6) | 169,523 | 0.0013 | 0.0007 | 0.0007 | 0.0003 | 0.0005 |
| 100 | [-1.0,-0.8) | 239,823 | 0.0014 | 0.0007 | 0.0009 | 0.0006 | 0.0007 |
| 100 | [0.0,0.2) | 502,827 | 0.0015 | 0.0007 | 0.0009 | 0.0005 | 0.0006 |
| 100 | [0.2,0.4) | 349,323 | 0.0015 | 0.0007 | 0.0008 | 0.0004 | 0.0005 |
| 100 | [0.4,0.6) | 217,698 | 0.0015 | 0.0008 | 0.0008 | 0.0003 | 0.0004 |
| 100 | [0.6,0.8) | 167,147 | 0.0022 | 0.0010 | 0.0013 | 0.0009 | 0.0010 |
| 100 | [0.8,1.0] | 227,351 | 0.0014 | 0.0006 | 0.0009 | 0.0006 | 0.0007 |
| 250 | [-0.2,0.0) | 259,416 | 0.0030 | 0.0016 | 0.0016 | 0.0008 | 0.0010 |
| 250 | [-0.4,-0.2) | 341,450 | 0.0041 | 0.0020 | 0.0023 | 0.0012 | 0.0015 |
| 250 | [-0.6,-0.4) | 216,442 | 0.0043 | 0.0020 | 0.0023 | 0.0011 | 0.0014 |
| 250 | [-0.8,-0.6) | 169,523 | 0.0042 | 0.0020 | 0.0024 | 0.0012 | 0.0016 |
| 250 | [-1.0,-0.8) | 239,823 | 0.0035 | 0.0017 | 0.0023 | 0.0016 | 0.0018 |
| 250 | [0.0,0.2) | 502,827 | 0.0036 | 0.0016 | 0.0021 | 0.0011 | 0.0014 |
| 250 | [0.2,0.4) | 349,323 | 0.0037 | 0.0018 | 0.0021 | 0.0011 | 0.0014 |
| 250 | [0.4,0.6) | 217,698 | 0.0036 | 0.0019 | 0.0019 | 0.0010 | 0.0012 |
| 250 | [0.6,0.8) | 167,147 | 0.0050 | 0.0023 | 0.0029 | 0.0017 | 0.0020 |
| 250 | [0.8,1.0] | 227,351 | 0.0035 | 0.0017 | 0.0023 | 0.0015 | 0.0017 |
| 500 | [-0.2,0.0) | 259,416 | 0.0067 | 0.0035 | 0.0037 | 0.0018 | 0.0023 |
| 500 | [-0.4,-0.2) | 341,450 | 0.0085 | 0.0039 | 0.0050 | 0.0028 | 0.0034 |
| 500 | [-0.6,-0.4) | 216,442 | 0.0095 | 0.0042 | 0.0054 | 0.0027 | 0.0034 |
| 500 | [-0.8,-0.6) | 169,523 | 0.0096 | 0.0044 | 0.0058 | 0.0034 | 0.0040 |
| 500 | [-1.0,-0.8) | 239,823 | 0.0078 | 0.0033 | 0.0054 | 0.0038 | 0.0043 |
| 500 | [0.0,0.2) | 502,827 | 0.0078 | 0.0035 | 0.0048 | 0.0027 | 0.0032 |
| 500 | [0.2,0.4) | 349,323 | 0.0080 | 0.0038 | 0.0046 | 0.0025 | 0.0031 |
| 500 | [0.4,0.6) | 217,698 | 0.0081 | 0.0039 | 0.0046 | 0.0024 | 0.0030 |
| 500 | [0.6,0.8) | 167,147 | 0.0100 | 0.0047 | 0.0058 | 0.0033 | 0.0039 |
| 500 | [0.8,1.0] | 227,351 | 0.0077 | 0.0034 | 0.0051 | 0.0033 | 0.0038 |
| 1000 | [-0.2,0.0) | 259,416 | 0.0158 | 0.0078 | 0.0089 | 0.0045 | 0.0056 |
| 1000 | [-0.4,-0.2) | 341,450 | 0.0189 | 0.0083 | 0.0114 | 0.0061 | 0.0076 |
| 1000 | [-0.6,-0.4) | 216,442 | 0.0203 | 0.0090 | 0.0119 | 0.0060 | 0.0076 |
| 1000 | [-0.8,-0.6) | 169,523 | 0.0229 | 0.0097 | 0.0144 | 0.0085 | 0.0101 |
| 1000 | [-1.0,-0.8) | 239,823 | 0.0170 | 0.0072 | 0.0118 | 0.0080 | 0.0091 |
| 1000 | [0.0,0.2) | 502,827 | 0.0173 | 0.0075 | 0.0107 | 0.0061 | 0.0074 |
| 1000 | [0.2,0.4) | 349,323 | 0.0186 | 0.0083 | 0.0111 | 0.0059 | 0.0074 |
| 1000 | [0.4,0.6) | 217,698 | 0.0193 | 0.0088 | 0.0114 | 0.0064 | 0.0077 |
| 1000 | [0.6,0.8) | 167,147 | 0.0225 | 0.0099 | 0.0134 | 0.0074 | 0.0089 |
| 1000 | [0.8,1.0] | 227,351 | 0.0176 | 0.0076 | 0.0119 | 0.0079 | 0.0090 |

### 3b. Oracle upper bound by price band (all valid states)

| horizon ms | price band | obs | oracle gross | trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered |
|---|---|---|---|---|---|---|---|
| 100 | 100-200 | 823,688 | 0.0013 | 0.0009 | 0.0007 | 0.0004 | 0.0005 |
| 100 | 200+ | 714,284 | 0.0009 | 0.0006 | 0.0006 | 0.0006 | 0.0006 |
| 100 | 25-50 | 246,806 | 0.0040 | 0.0009 | 0.0024 | 0.0011 | 0.0015 |
| 100 | 5-25 | 46,800 | 0.0030 | 0.0004 | 0.0017 | 0.0002 | 0.0007 |
| 100 | 50-100 | 859,422 | 0.0015 | 0.0007 | 0.0008 | 0.0003 | 0.0004 |
| 250 | 100-200 | 823,688 | 0.0035 | 0.0023 | 0.0020 | 0.0012 | 0.0014 |
| 250 | 200+ | 714,284 | 0.0020 | 0.0014 | 0.0014 | 0.0012 | 0.0012 |
| 250 | 25-50 | 246,806 | 0.0089 | 0.0022 | 0.0051 | 0.0019 | 0.0028 |
| 250 | 5-25 | 46,800 | 0.0090 | 0.0011 | 0.0057 | 0.0021 | 0.0032 |
| 250 | 50-100 | 859,422 | 0.0038 | 0.0016 | 0.0021 | 0.0009 | 0.0012 |
| 500 | 100-200 | 823,688 | 0.0080 | 0.0048 | 0.0048 | 0.0032 | 0.0036 |
| 500 | 200+ | 714,284 | 0.0044 | 0.0030 | 0.0032 | 0.0027 | 0.0027 |
| 500 | 25-50 | 246,806 | 0.0183 | 0.0045 | 0.0104 | 0.0037 | 0.0056 |
| 500 | 5-25 | 46,800 | 0.0189 | 0.0022 | 0.0121 | 0.0046 | 0.0070 |
| 500 | 50-100 | 859,422 | 0.0081 | 0.0033 | 0.0045 | 0.0022 | 0.0028 |
| 1000 | 100-200 | 823,688 | 0.0178 | 0.0104 | 0.0109 | 0.0070 | 0.0081 |
| 1000 | 200+ | 714,284 | 0.0096 | 0.0065 | 0.0069 | 0.0058 | 0.0059 |
| 1000 | 25-50 | 246,806 | 0.0441 | 0.0102 | 0.0264 | 0.0106 | 0.0152 |
| 1000 | 5-25 | 46,800 | 0.0410 | 0.0044 | 0.0275 | 0.0115 | 0.0170 |
| 1000 | 50-100 | 859,422 | 0.0184 | 0.0072 | 0.0106 | 0.0052 | 0.0067 |

## 4. QIMB-constrained upper bound (request §4)

**QIMB_CONSTRAINED_BOUND keeps the side dictated by queue imbalance (the sign that defines the bin) and adds clairvoyant abstention only: max(0, net_side). No new threshold, no side choice and no model enters this bound.**

| horizon ms | imbalance bin | obs | net structural_floor | bound structural_floor | gap | bound accessible_fixed | bound accessible_tiered | P(bound>0) structural_floor |
|---|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 259,416 | -6.5491 | 0.0002 | 6.5494 | 0.0001 | 0.0001 | 0.0003 |
| 100 | [-0.4,-0.2) | 341,450 | -6.8813 | 0.0005 | 6.8818 | 0.0002 | 0.0003 | 0.0004 |
| 100 | [-0.6,-0.4) | 216,442 | -6.6124 | 0.0008 | 6.6133 | 0.0005 | 0.0006 | 0.0004 |
| 100 | [-0.8,-0.6) | 169,523 | -6.8594 | 0.0004 | 6.8598 | 0.0002 | 0.0002 | 0.0003 |
| 100 | [-1.0,-0.8) | 239,823 | -7.1817 | 0.0006 | 7.1824 | 0.0005 | 0.0005 | 0.0004 |
| 100 | [0.0,0.2) | 270,249 | -6.4083 | 0.0003 | 6.4085 | 0.0001 | 0.0002 | 0.0003 |
| 100 | [0.2,0.4) | 349,323 | -6.7070 | 0.0003 | 6.7073 | 0.0002 | 0.0002 | 0.0003 |
| 100 | [0.4,0.6) | 217,698 | -6.4970 | 0.0005 | 6.4975 | 0.0002 | 0.0003 | 0.0004 |
| 100 | [0.6,0.8) | 167,147 | -6.8613 | 0.0008 | 6.8621 | 0.0005 | 0.0006 | 0.0005 |
| 100 | [0.8,1.0] | 227,351 | -7.1838 | 0.0006 | 7.1844 | 0.0004 | 0.0005 | 0.0003 |
| 250 | [-0.2,0.0) | 259,416 | -6.5443 | 0.0009 | 6.5451 | 0.0005 | 0.0005 | 0.0007 |
| 250 | [-0.4,-0.2) | 341,450 | -6.8761 | 0.0012 | 6.8773 | 0.0006 | 0.0008 | 0.0009 |
| 250 | [-0.6,-0.4) | 216,442 | -6.5980 | 0.0016 | 6.5996 | 0.0008 | 0.0010 | 0.0011 |
| 250 | [-0.8,-0.6) | 169,523 | -6.8405 | 0.0017 | 6.8422 | 0.0010 | 0.0012 | 0.0011 |
| 250 | [-1.0,-0.8) | 239,823 | -7.1703 | 0.0017 | 7.1720 | 0.0013 | 0.0014 | 0.0008 |
| 250 | [0.0,0.2) | 270,249 | -6.4017 | 0.0008 | 6.4025 | 0.0003 | 0.0005 | 0.0007 |
| 250 | [0.2,0.4) | 349,323 | -6.6976 | 0.0009 | 6.6985 | 0.0004 | 0.0005 | 0.0008 |
| 250 | [0.4,0.6) | 217,698 | -6.4821 | 0.0011 | 6.4833 | 0.0005 | 0.0007 | 0.0010 |
| 250 | [0.6,0.8) | 167,147 | -6.8447 | 0.0017 | 6.8464 | 0.0010 | 0.0012 | 0.0011 |
| 250 | [0.8,1.0] | 227,351 | -7.1720 | 0.0015 | 7.1736 | 0.0010 | 0.0012 | 0.0008 |
| 500 | [-0.2,0.0) | 259,416 | -6.5379 | 0.0020 | 6.5399 | 0.0010 | 0.0013 | 0.0016 |
| 500 | [-0.4,-0.2) | 341,450 | -6.8658 | 0.0025 | 6.8684 | 0.0013 | 0.0017 | 0.0019 |
| 500 | [-0.6,-0.4) | 216,442 | -6.5753 | 0.0035 | 6.5788 | 0.0019 | 0.0023 | 0.0023 |
| 500 | [-0.8,-0.6) | 169,523 | -6.8172 | 0.0038 | 6.8210 | 0.0022 | 0.0026 | 0.0025 |
| 500 | [-1.0,-0.8) | 239,823 | -7.1536 | 0.0036 | 7.1572 | 0.0026 | 0.0029 | 0.0016 |
| 500 | [0.0,0.2) | 270,249 | -6.3959 | 0.0015 | 6.3974 | 0.0006 | 0.0009 | 0.0014 |
| 500 | [0.2,0.4) | 349,323 | -6.6864 | 0.0022 | 6.6887 | 0.0011 | 0.0014 | 0.0018 |
| 500 | [0.4,0.6) | 217,698 | -6.4632 | 0.0023 | 6.4656 | 0.0010 | 0.0014 | 0.0020 |
| 500 | [0.6,0.8) | 167,147 | -6.8188 | 0.0033 | 6.8221 | 0.0018 | 0.0021 | 0.0023 |
| 500 | [0.8,1.0] | 227,351 | -7.1553 | 0.0031 | 7.1584 | 0.0020 | 0.0023 | 0.0016 |
| 1000 | [-0.2,0.0) | 259,416 | -6.5200 | 0.0048 | 6.5248 | 0.0025 | 0.0030 | 0.0038 |
| 1000 | [-0.4,-0.2) | 341,450 | -6.8483 | 0.0059 | 6.8542 | 0.0030 | 0.0038 | 0.0041 |
| 1000 | [-0.6,-0.4) | 216,442 | -6.5444 | 0.0074 | 6.5519 | 0.0039 | 0.0049 | 0.0048 |
| 1000 | [-0.8,-0.6) | 169,523 | -6.7772 | 0.0091 | 6.7863 | 0.0054 | 0.0064 | 0.0053 |
| 1000 | [-1.0,-0.8) | 239,823 | -7.1253 | 0.0078 | 7.1331 | 0.0055 | 0.0062 | 0.0037 |
| 1000 | [0.0,0.2) | 270,249 | -6.3865 | 0.0034 | 6.3899 | 0.0015 | 0.0020 | 0.0031 |
| 1000 | [0.2,0.4) | 349,323 | -6.6669 | 0.0053 | 6.6722 | 0.0026 | 0.0033 | 0.0040 |
| 1000 | [0.4,0.6) | 217,698 | -6.4279 | 0.0061 | 6.4340 | 0.0032 | 0.0039 | 0.0043 |
| 1000 | [0.6,0.8) | 167,147 | -6.7816 | 0.0065 | 6.7881 | 0.0031 | 0.0039 | 0.0049 |
| 1000 | [0.8,1.0] | 227,351 | -7.1290 | 0.0064 | 7.1354 | 0.0041 | 0.0047 | 0.0034 |

This is the most favourable economics obtainable inside each declared state once the side is fixed by queue imbalance and only abstention is free. No new threshold and no side choice is introduced.

## 5. Where the loss comes from (request §5)

The decomposition is an identity, reconciled to 1e-9 in `feasibility_status.json`:

```
cross_to_cross = realized_move - half_spread_entry - half_spread_future
net(regime)    = cross_to_cross - fee(regime)
fee(accessible) = fee(structural) + broker_layer
```

| horizon ms | realized move | half spread in | half spread out | full spread paid | mandatory fee (structural_floor) | broker layer (accessible_fixed) | broker layer (accessible_tiered) | net structural_floor | net accessible_fixed | net accessible_tiered |
|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 0.0104 | 2.9125 | 2.9107 | 5.8232 | 0.9533 | 1.4594 | 0.8941 | -6.7662 | -8.2256 | -7.6603 |
| 250 | 0.0211 | 2.9125 | 2.9109 | 5.8234 | 0.9533 | 1.4594 | 0.8941 | -6.7557 | -8.2151 | -7.6497 |
| 500 | 0.0348 | 2.9125 | 2.9101 | 5.8226 | 0.9533 | 1.4594 | 0.8941 | -6.7411 | -8.2005 | -7.6352 |
| 1000 | 0.0578 | 2.9125 | 2.9086 | 5.8211 | 0.9533 | 1.4594 | 0.8941 | -6.7167 | -8.1761 | -7.6107 |

### 5a. Mechanism, computed from the decomposition

| horizon ms | signal (signed mid move) | full spread paid | mandatory fee (structural_floor) | required move | spread share of required | fee share of required | signal coverage | net structural_floor |
|---|---|---|---|---|---|---|---|---|
| 100 | 0.0104 | 5.8232 | 0.9533 | 6.7766 | 85.9% | 14.1% | 0.15% | -6.7662 |
| 250 | 0.0211 | 5.8234 | 0.9533 | 6.7768 | 85.9% | 14.1% | 0.31% | -6.7557 |
| 500 | 0.0348 | 5.8226 | 0.9533 | 6.7760 | 85.9% | 14.1% | 0.51% | -6.7411 |
| 1000 | 0.0578 | 5.8211 | 0.9533 | 6.7744 | 85.9% | 14.1% | 0.85% | -6.7167 |

The same decomposition expressed as what the signal would have to become: at 1000 ms the spread alone requires a mid move 100.8x larger than the realised one, and the mandatory floor fee alone requires 16.5x. Both multiples are measured, not projected: they are the ratio of a cost component to the realised edge at the same horizon.

| flag | holds | rule |
|---|---|---|
| SPREAD_DOMINATES | TRUE | the mean full spread paid is more than half of the required move at the longest declared horizon |
| FEES_DOMINATE | FALSE | the mean floor fee is more than half of the required move at the longest declared horizon |
| SIGNAL_MAGNITUDE_TOO_SMALL | TRUE | the side-signed mid move covers less than 10% of the required move at every declared horizon |
| WRONG_HORIZON | FALSE | extending the horizon across the whole declared grid (100 ms to 1000 ms, a factor of ten) closes at least half of the remaining gap |
| POOLED_LOW_QUALITY_STATES | TRUE | the dispersion of the net result across the declared (bin x horizon) states is less than half of its mean, i.e. the states barely separate |

Horizon increments of `net structural_floor` across the declared grid: 0.0105, 0.0145, 0.0244 bps, i.e. a ten-fold extension of the horizon closes 0.7% of the remaining gap (the required move itself is horizon-invariant: 6.7766 bps at 100 ms against 6.7744 bps at 1000 ms). Cross-state dispersion of the net result over the 40 (bin x horizon) states is 0.7973 bps, 11.8% of the mean, so the declared states barely separate. Holding flags: SPREAD_DOMINATES, SIGNAL_MAGNITUDE_TOO_SMALL, POOLED_LOW_QUALITY_STATES.

## 6. Answers (request §6)

**1. Is there any development-sample state in the predeclared state space where aggressive execution approaches or exceeds the structural hurdle?**

No. 0 of the 400 declared cells (10 imbalance bins × 2 spread classes × 5 price bands × 4 horizons) have a positive structural-cost-adjusted result, and 0 of the 40 cells of the aggregated (bin × horizon) view do. The best cell in the whole declared space is `[-1.0,-0.8) · ONE_TICK · $200+ · 250 ms` — -0.9507 bps net, i.e. still losing — with a hurdle coverage of 0.093 (mean side-signed mid move 0.0980 bps against a 1.0487 bps required move) on 1,050 observations.

Cells at each declared hurdle-coverage cut — the full 400-cell grid first, then the (bin × horizon) view: ≥1.0×: 0, ≥0.9×: 0, ≥0.75×: 0, ≥0.5×: 0 (full grid); ≥1.0×: 0, ≥0.9×: 0, ≥0.75×: 0, ≥0.5×: 0 (bin × horizon). These cuts are descriptive buckets, not selection rules: no state is promoted and none is killed, and the best cell is named only because the question asks where the maximum lies.

**2. What fraction of opportunities does that state represent?**

For the best aggregated state (`[0.0,0.2)` at 1000 ms): 10.993% of the signal-defined observations (270,249 of 2,458,422). For the best individual cell (`[-1.0,-0.8) · ONE_TICK · $200+ · 250 ms`): 0.0427% (1,050 observations, 42 symbol-block cells, block-bootstrap SE 0.0654 bps). Both fractions are reported so that a reader can see how little of the opportunity set a favourable cell addresses even if it were real.

**3. Does a clairvoyant aggressive trader have meaningful room after costs?**

No. At the longest declared horizon (1000 ms), perfect side selection earns 0.0114 bps per observation after the structural floor and 0.0065 bps after accessible_fixed, 0.0079 bps after accessible_tiered, on 2,458,422 observations; it beats abstaining on 0.82% of them before costs and on 0.71% after the structural floor. That bound is 0.17% of the 6.7744 bps required move at the same horizon: the entire value of perfect foresight is about 0.013 bps per decision, three orders of magnitude below what the execution formulation needs. No predictive model can close that, and this is the strongest statement this calculation supports — it does not depend on any model, only on the realised future quotes.

**4. Which component creates the dominant economic gap?**

The gap is `required move - realised move` = 6.7744 - (0.0578) bps, decomposed exactly in §5: **the full spread paid contributes 85.9%** of the required move, **the mandatory venue/regulatory fee 14.1%**, and the signal supplies 0.85%. The broker reference layer on top of the floor is an additional 1.4594 bps (accessible_fixed), 0.8941 bps (accessible_tiered). Flags holding, with their rules in §5a: SPREAD_DOMINATES, SIGNAL_MAGNITUDE_TOO_SMALL, POOLED_LOW_QUALITY_STATES.

Reading: the dominant component is the **spread** (85.9% of the hurdle), the fee is second, and the signal is not a large contributor to the gap because it is negligible in absolute terms — it would need to be 100.8x larger merely to pay the spread. That is a combination, and the decomposition is the evidence for it; nothing here is inferred from the shape of the results alone.

## 7. Reconciliation and limitations

| check | observations | mismatches / max abs difference / ratio | tolerance | outcome |
|---|---|---|---|---|
| execution_instant_is_decision_instant | 2,691,000 | 0 | 0 | PASS |
| frozen_execution_comparison | 9,833,688 | NaN |  | NOT_EVALUATED_REFERENCE_ABSENT |
| decomposition_identity_pooled | 9,833,688 | 0.0000 | 1e-09 | PASS |
| spread_hurdle_is_cross_to_cross_breakeven | 9,833,688 | 0.0000 | 1e-09 | PASS |
| oracle_bound_dominates_and_is_non_negative | 32,292,000 | 0 | 1e-09 | PASS |
| qimb_bound_below_oracle_bound | 29,501,064 | 0 | 1e-09 | PASS |
| state_partition_covers_every_observation | 2,458,422 | 2,458,422 in cells | 0 | PASS |
| fee_lookup_matches_ledger_at_observation_prices | 1,506 | 0.0000 | 1e-09 | PASS |
| tick_and_half_spread_arithmetic | 2,691,000 | 0 | 1e-09 | PASS |

### 7a. Discrepancies found in the frozen M2-0 execution table — reported, not repaired

The frozen table could not be reproduced in two of its columns, and the difference is not a tolerance: it is exact. Both defects are in `M2/src/calculate.py::execution_rows`, they are reproduced here bit for bit by recomputing M2-0's own expressions (`frozen_cross_to_cross_is_half_of_true_bps`, `frozen_cost_column_is_ledger_at_half_price`), and **no frozen artifact was modified, regenerated or overwritten by this pass**.

| id | expression in the frozen artifact | correct expression | effect | verified by |
|---|---|---|---|---|

Affected artifacts: .

Impact on M2-0's conclusions: `mean_gross_markout_bps` is unaffected and reproduces exactly. Both defects make the aggressive arithmetic look *better* than it is, so the direction of M2-0's qualitative statement (aggressive execution loses money on this sample) is unchanged — the corrected cross-to-cross result is more negative, and the corrected fee is smaller. The columns this pass reports are the corrected ones; a reader comparing the two tables should expect the exact factor of two recorded above.

Limitations, stated so the bound cannot be read as more than it is:

- **Development sample only.** One 2019 sample day, 61 development-scope symbols that are *not* frozen universe membership. No modern-regime claim transfers from it, and no out-of-sample claim is made.
- **Costs are 2026 rate cards on a 2019 tape.** They validate the arithmetic and the ordering of the components; they do not reconstruct 2019 economics. The structural floor is a lower bound that no achievable path reaches, and it excludes commission, clearing, market data, slippage and impact — so every result here is optimistic, not conservative.
- **Idealized fills.** Sufficient displayed size, immediate aggressive fill, no impact, no queue effect.
- **The delay-0 instant is the arrival instant.** Latency beyond it is not modelled here; M2-0's delay surface shows this arithmetic is essentially flat across the delay grid on this sample.
- **The oracle bound is not achievable** and must never be used for training, selection or reporting as performance. It exists only to bound what prediction could possibly be worth.

## 8. Artifacts

| artifact | content |
|---|---|
| `M2/output/calculations/aggressive_feasibility_by_state.csv` | request §1: the 100 declared cells × 4 horizons = 400 rows |
| `M2/output/calculations/breakeven_hurdle.csv` | request §2, hurdle and realized distributions plus P(realized > hurdle) |
| `M2/output/calculations/oracle_upper_bound.csv` | request §3, ORACLE_UPPER_BOUND per declared cell |
| `M2/output/calculations/qimb_constrained_bound.csv` | request §4, QIMB_CONSTRAINED_BOUND per declared cell |
| `M2/output/calculations/feasibility_status.json` | run status, observation accounting, every reconciliation row, the mechanism verdict and the answers |

Reproduce with `python -m M2.src.feasibility --config M2/config/nasdaq_qimb_m2_0.yaml`.
