# M2-0.5 — AGGRESSIVE MONETIZATION FEASIBILITY BOUND

Candidate `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` · run `M2-0-6-NASDAQ-QIMB-UNIVPROXY` · development sample day `2019-07-30` · dataset `NASDAQ-ITCH50-PUBLIC-SAMPLE-20190730` · cost ledger `M2-COST-LEDGER-v1`

**No data was acquired, no model was trained, no threshold was optimised, Jev was not used, M1 and the research framework were not modified, and no artifact of M2-0 was rewritten.** This pass reads the frozen M2-0 development artifacts and conditions the existing aggressive execution arithmetic on the predeclared state space. It promotes nothing and kills nothing.

| item | value |
|---|---|
| execution instant | delay_decisions.parquet, delay 0 ms (the M2-0 idealized aggressive instant) |
| observations (level 0) | 772,200 valid decision states of 772,200 delay rows |
| observations (level 1) | 737,768 with a defined signal side (imbalance != 0) |
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
| delay rows at delay 0 | 772,200 | 1 s grid, 61 development-scope symbols |
| valid decision states | 772,200 | two-sided, uncrossed, arrival present |
|     of which imbalance == 0 | 34,432 | in the state space but with no sign to trade; kept in the oracle set, excluded from side-dependent cells (the M2-0 execution filter) |
| signal-defined observations | 737,768 | imbalance != 0; the base of every state-conditioned cell |
| outside the declared price bands | 0 | none: every observation falls in one of the five declared bands |
| future quote missing at 100 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 250 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 500 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 1000 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| imbalance == 0 at 100 ms | 34,432 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 250 ms | 34,432 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 500 ms | 34,432 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 1000 ms | 34,432 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
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
| 100 | 737,768 | 0.0003 | 0.0140 | -1.2738 | -2.5612 | 2.5752 | 1.5281 | -4.0893 | -6.8294 | -5.6709 | 0.0005 |
| 250 | 737,768 | 0.0008 | 0.0286 | -1.2592 | -2.5462 | 2.5747 | 1.5281 | -4.0742 | -6.8143 | -5.6558 | 0.0013 |
| 500 | 737,768 | 0.0005 | 0.0479 | -1.2399 | -2.5265 | 2.5744 | 1.5281 | -4.0546 | -6.7947 | -5.6362 | 0.0028 |
| 1000 | 737,768 | 0.0012 | 0.0794 | -1.2084 | -2.4936 | 2.5730 | 1.5281 | -4.0217 | -6.7618 | -5.6033 | 0.0061 |

### 1b. By spread class

| horizon ms | spread class | obs | spread bps | signed mid move | cross-to-cross | net structural_floor | net accessible_fixed | net accessible_tiered | P(net>0) structural_floor |
|---|---|---|---|---|---|---|---|---|---|
| 100 | ONE_TICK | 598,595 | 2.3305 | 0.0139 | -2.3213 | -3.9712 | -6.9828 | -5.6985 | 0.0005 |
| 100 | WIDER_THAN_ONE_TICK | 139,173 | 3.6298 | 0.0145 | -3.5931 | -4.5972 | -6.1697 | -5.5520 | 0.0006 |
| 250 | ONE_TICK | 598,595 | 2.3305 | 0.0289 | -2.3110 | -3.9609 | -6.9725 | -5.6882 | 0.0012 |
| 250 | WIDER_THAN_ONE_TICK | 139,173 | 3.6298 | 0.0273 | -3.5576 | -4.5617 | -6.1342 | -5.5164 | 0.0015 |
| 500 | ONE_TICK | 598,595 | 2.3305 | 0.0491 | -2.2964 | -3.9463 | -6.9579 | -5.6737 | 0.0027 |
| 500 | WIDER_THAN_ONE_TICK | 139,173 | 3.6298 | 0.0428 | -3.5161 | -4.5202 | -6.0927 | -5.4750 | 0.0032 |
| 1000 | ONE_TICK | 598,595 | 2.3305 | 0.0825 | -2.2714 | -3.9213 | -6.9329 | -5.6487 | 0.0060 |
| 1000 | WIDER_THAN_ONE_TICK | 139,173 | 3.6298 | 0.0663 | -3.4492 | -4.4533 | -6.0258 | -5.4081 | 0.0065 |

### 1c. By price band

| horizon ms | price band | obs | mean price | spread bps | signed mid move | cross-to-cross | fee structural_floor | fee accessible_fixed | fee accessible_tiered | net structural_floor | net accessible_fixed | net accessible_tiered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 100-200 | 86,108 | 122.14 | 1.2783 | 0.0133 | -1.2641 | 0.7208 | 1.6621 | 1.3367 | -1.9850 | -2.9262 | -2.6009 |
| 100 | 200+ | 22,373 | 208.56 | 0.7250 | 0.0128 | -0.7131 | 0.5030 | 0.9590 | 0.8584 | -1.2161 | -1.6721 | -1.5715 |
| 100 | 25-50 | 161,454 | 38.75 | 2.8772 | 0.0199 | -2.8569 | 1.8773 | 5.3955 | 3.8766 | -4.7342 | -8.2524 | -6.7335 |
| 100 | 5-25 | 23,387 | 6.21 | 16.1042 | 0.0014 | -16.1022 | 10.1834 | 32.2113 | 22.1196 | -26.2856 | -48.3134 | -38.2218 |
| 100 | 50-100 | 444,446 | 68.28 | 2.0987 | 0.0128 | -2.0856 | 1.1538 | 3.0597 | 2.2876 | -3.2393 | -5.1453 | -4.3732 |
| 250 | 100-200 | 86,108 | 122.14 | 1.2783 | 0.0253 | -1.2515 | 0.7208 | 1.6621 | 1.3367 | -1.9723 | -2.9136 | -2.5882 |
| 250 | 200+ | 22,373 | 208.56 | 0.7250 | 0.0233 | -0.7016 | 0.5030 | 0.9590 | 0.8584 | -1.2047 | -1.6606 | -1.5600 |
| 250 | 25-50 | 161,454 | 38.75 | 2.8772 | 0.0423 | -2.8340 | 1.8773 | 5.3955 | 3.8766 | -4.7113 | -8.2296 | -6.7107 |
| 250 | 5-25 | 23,387 | 6.21 | 16.1042 | 0.0069 | -16.0966 | 10.1834 | 32.2113 | 22.1196 | -26.2801 | -48.3079 | -38.2163 |
| 250 | 50-100 | 444,446 | 68.28 | 2.0987 | 0.0256 | -2.0722 | 1.1538 | 3.0597 | 2.2876 | -3.2260 | -5.1320 | -4.3598 |
| 500 | 100-200 | 86,108 | 122.14 | 1.2783 | 0.0392 | -1.2379 | 0.7208 | 1.6621 | 1.3367 | -1.9587 | -2.9000 | -2.5746 |
| 500 | 200+ | 22,373 | 208.56 | 0.7250 | 0.0342 | -0.6907 | 0.5030 | 0.9590 | 0.8584 | -1.1937 | -1.6496 | -1.5491 |
| 500 | 25-50 | 161,454 | 38.75 | 2.8772 | 0.0710 | -2.8055 | 1.8773 | 5.3955 | 3.8766 | -4.6828 | -8.2011 | -6.6822 |
| 500 | 5-25 | 23,387 | 6.21 | 16.1042 | 0.0124 | -16.0918 | 10.1834 | 32.2113 | 22.1196 | -26.2752 | -48.3031 | -38.2114 |
| 500 | 50-100 | 444,446 | 68.28 | 2.0987 | 0.0438 | -2.0534 | 1.1538 | 3.0597 | 2.2876 | -3.2072 | -5.1131 | -4.3410 |
| 1000 | 100-200 | 86,108 | 122.14 | 1.2783 | 0.0578 | -1.2179 | 0.7208 | 1.6621 | 1.3367 | -1.9388 | -2.8800 | -2.5547 |
| 1000 | 200+ | 22,373 | 208.56 | 0.7250 | 0.0413 | -0.6840 | 0.5030 | 0.9590 | 0.8584 | -1.1870 | -1.6430 | -1.5424 |
| 1000 | 25-50 | 161,454 | 38.75 | 2.8772 | 0.1211 | -2.7546 | 1.8773 | 5.3955 | 3.8766 | -4.6319 | -8.1502 | -6.6313 |
| 1000 | 5-25 | 23,387 | 6.21 | 16.1042 | 0.0448 | -16.0580 | 10.1834 | 32.2113 | 22.1196 | -26.2415 | -48.2693 | -38.1776 |
| 1000 | 50-100 | 444,446 | 68.28 | 2.0987 | 0.0722 | -2.0233 | 1.1538 | 3.0597 | 2.2876 | -3.1770 | -5.0830 | -4.3108 |

### 1d. By imbalance bin and horizon (structural floor)

| horizon ms | imbalance bin | obs | spread paid | signed mid move | cross-to-cross | net structural_floor | P(net>0) structural_floor |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 98,350 | 3.1865 | 0.0038 | -3.1827 | -5.1477 | 0.0004 |
| 100 | [-0.4,-0.2) | 112,253 | 2.8683 | 0.0097 | -2.8586 | -4.5453 | 0.0005 |
| 100 | [-0.6,-0.4) | 80,322 | 2.5839 | 0.0154 | -2.5685 | -4.1052 | 0.0005 |
| 100 | [-0.8,-0.6) | 55,070 | 2.4253 | 0.0259 | -2.3994 | -3.7314 | 0.0004 |
| 100 | [-1.0,-0.8) | 22,224 | 2.2261 | 0.0416 | -2.1844 | -3.4111 | 0.0009 |
| 100 | [0.0,0.2) | 95,153 | 2.6832 | 0.0031 | -2.6801 | -4.3409 | 0.0004 |
| 100 | [0.2,0.4) | 112,419 | 2.3807 | 0.0089 | -2.3718 | -3.7429 | 0.0005 |
| 100 | [0.4,0.6) | 79,321 | 2.1910 | 0.0175 | -2.1735 | -3.4970 | 0.0006 |
| 100 | [0.6,0.8) | 56,134 | 2.1615 | 0.0275 | -2.1340 | -3.4214 | 0.0008 |
| 100 | [0.8,1.0] | 26,522 | 2.1070 | 0.0404 | -2.0667 | -3.2477 | 0.0008 |
| 250 | [-0.2,0.0) | 98,350 | 3.1833 | 0.0072 | -3.1761 | -5.1410 | 0.0010 |
| 250 | [-0.4,-0.2) | 112,253 | 2.8674 | 0.0175 | -2.8499 | -4.5366 | 0.0013 |
| 250 | [-0.6,-0.4) | 80,322 | 2.5833 | 0.0344 | -2.5490 | -4.0856 | 0.0014 |
| 250 | [-0.8,-0.6) | 55,070 | 2.4274 | 0.0566 | -2.3708 | -3.7028 | 0.0015 |
| 250 | [-1.0,-0.8) | 22,224 | 2.2292 | 0.0763 | -2.1529 | -3.3796 | 0.0021 |
| 250 | [0.0,0.2) | 95,153 | 2.6804 | 0.0065 | -2.6739 | -4.3347 | 0.0008 |
| 250 | [0.2,0.4) | 112,419 | 2.3795 | 0.0190 | -2.3606 | -3.7316 | 0.0012 |
| 250 | [0.4,0.6) | 79,321 | 2.1915 | 0.0357 | -2.1558 | -3.4793 | 0.0014 |
| 250 | [0.6,0.8) | 56,134 | 2.1649 | 0.0586 | -2.1062 | -3.3936 | 0.0019 |
| 250 | [0.8,1.0] | 26,522 | 2.1108 | 0.0738 | -2.0370 | -3.2180 | 0.0019 |
| 500 | [-0.2,0.0) | 98,350 | 3.1804 | 0.0121 | -3.1683 | -5.1332 | 0.0021 |
| 500 | [-0.4,-0.2) | 112,253 | 2.8671 | 0.0301 | -2.8370 | -4.5236 | 0.0026 |
| 500 | [-0.6,-0.4) | 80,322 | 2.5832 | 0.0623 | -2.5209 | -4.0575 | 0.0031 |
| 500 | [-0.8,-0.6) | 55,070 | 2.4299 | 0.0914 | -2.3384 | -3.6705 | 0.0035 |
| 500 | [-1.0,-0.8) | 22,224 | 2.2331 | 0.1294 | -2.1037 | -3.3304 | 0.0039 |
| 500 | [0.0,0.2) | 95,153 | 2.6773 | 0.0086 | -2.6687 | -4.3295 | 0.0018 |
| 500 | [0.2,0.4) | 112,419 | 2.3794 | 0.0329 | -2.3465 | -3.7175 | 0.0025 |
| 500 | [0.4,0.6) | 79,321 | 2.1909 | 0.0607 | -2.1302 | -3.4537 | 0.0029 |
| 500 | [0.6,0.8) | 56,134 | 2.1681 | 0.0958 | -2.0723 | -3.3597 | 0.0036 |
| 500 | [0.8,1.0] | 26,522 | 2.1137 | 0.1200 | -1.9937 | -3.1747 | 0.0043 |
| 1000 | [-0.2,0.0) | 98,350 | 3.1756 | 0.0229 | -3.1527 | -5.1176 | 0.0047 |
| 1000 | [-0.4,-0.2) | 112,253 | 2.8664 | 0.0520 | -2.8144 | -4.5011 | 0.0059 |
| 1000 | [-0.6,-0.4) | 80,322 | 2.5827 | 0.1000 | -2.4827 | -4.0194 | 0.0063 |
| 1000 | [-0.8,-0.6) | 55,070 | 2.4304 | 0.1484 | -2.2820 | -3.6140 | 0.0075 |
| 1000 | [-1.0,-0.8) | 22,224 | 2.2279 | 0.2043 | -2.0236 | -3.2503 | 0.0099 |
| 1000 | [0.0,0.2) | 95,153 | 2.6722 | 0.0169 | -2.6553 | -4.3161 | 0.0041 |
| 1000 | [0.2,0.4) | 112,419 | 2.3777 | 0.0569 | -2.3208 | -3.6918 | 0.0059 |
| 1000 | [0.4,0.6) | 79,321 | 2.1918 | 0.1019 | -2.0899 | -3.4135 | 0.0064 |
| 1000 | [0.6,0.8) | 56,134 | 2.1701 | 0.1561 | -2.0140 | -3.3015 | 0.0081 |
| 1000 | [0.8,1.0] | 26,522 | 2.1178 | 0.1850 | -1.9327 | -3.1137 | 0.0089 |

### 1e. The best and worst declared cells (descriptive only — nothing is selected)

| cell | obs | share of obs | spread bps | signed mid move | cross-to-cross | net structural_floor | block SE | block cells |
|---|---|---|---|---|---|---|---|---|
| [-1.0,-0.8) · ONE_TICK · $200+ · 1000 ms | 934 | 0.0013 | 0.4798 | 0.0925 | -0.4716 | -0.9748 | 0.0128 | 13 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 100 ms | 934 | 0.0013 | 0.4798 | 0.0337 | -0.4731 | -0.9763 | 0.0048 | 13 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 250 ms | 934 | 0.0013 | 0.4798 | 0.0499 | -0.4762 | -0.9794 | 0.0065 | 13 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 500 ms | 934 | 0.0013 | 0.4798 | 0.0650 | -0.4777 | -0.9809 | 0.0085 | 13 |
| [0.8,1.0] · ONE_TICK · $200+ · 250 ms | 890 | 0.0012 | 0.4795 | 0.0477 | -0.4784 | -0.9814 | 0.0077 | 13 |

Worst five cells by `net structural_floor`: [-1.0,-0.8)/WIDER_THAN_ONE_TICK/$5-25/100 ms = NaN bps; [-0.8,-0.6)/WIDER_THAN_ONE_TICK/$5-25/100 ms = NaN bps; [-0.6,-0.4)/WIDER_THAN_ONE_TICK/$5-25/100 ms = NaN bps; [-0.4,-0.2)/WIDER_THAN_ONE_TICK/$5-25/100 ms = NaN bps; [0.2,0.4)/WIDER_THAN_ONE_TICK/$5-25/100 ms = NaN bps.

## 2. Break-even hurdles (request §2)

Hurdle A is the current quoted spread (cross in, cross out); B adds the structural floor round trip; C adds each accessible reference path. `realized_move_bps` is the side-signed mid move, so `realized > hurdle` is the break-even test and `P(realized > hurdle A)` equals `P(cross-to-cross > 0)` up to the measured spread-change term. Full distributions and ratios per cell are in `breakeven_hurdle.csv`; the pooled view is below.

| horizon ms | realized (mean) | required A (spread) | required structural_floor | required accessible_fixed | required accessible_tiered | P(>A) | P(>structural_floor) | P(>accessible_fixed) | P(>accessible_tiered) |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 0.0140 | 2.5756 | 4.1037 | 6.8438 | 5.6853 | 0.0009 | 0.0005 | 0.0001 | 0.0001 |
| 250 | 0.0286 | 2.5756 | 4.1037 | 6.8438 | 5.6853 | 0.0022 | 0.0013 | 0.0002 | 0.0003 |
| 500 | 0.0479 | 2.5756 | 4.1037 | 6.8438 | 5.6853 | 0.0044 | 0.0028 | 0.0004 | 0.0007 |
| 1000 | 0.0794 | 2.5756 | 4.1037 | 6.8438 | 5.6853 | 0.0090 | 0.0061 | 0.0010 | 0.0016 |

### 2a. Hurdle coverage by imbalance bin and horizon (mean realized move / mean required move, structural)

| horizon ms | imbalance bin | obs | realized | required | coverage | P(realized > B) | P(QIMB bound > 0) |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 98,350 | 0.0038 | 5.1546 | 0.001 | 0.0004 | 0.0004 |
| 100 | [-0.4,-0.2) | 112,253 | 0.0097 | 4.5560 | 0.002 | 0.0006 | 0.0005 |
| 100 | [-0.6,-0.4) | 80,322 | 0.0154 | 4.1211 | 0.004 | 0.0006 | 0.0005 |
| 100 | [-0.8,-0.6) | 55,070 | 0.0259 | 3.7548 | 0.007 | 0.0005 | 0.0004 |
| 100 | [-1.0,-0.8) | 22,224 | 0.0416 | 3.4468 | 0.012 | 0.0010 | 0.0009 |
| 100 | [0.0,0.2) | 95,153 | 0.0031 | 4.3473 | 0.001 | 0.0004 | 0.0004 |
| 100 | [0.2,0.4) | 112,419 | 0.0089 | 3.7521 | 0.002 | 0.0005 | 0.0005 |
| 100 | [0.4,0.6) | 79,321 | 0.0175 | 3.5141 | 0.005 | 0.0006 | 0.0006 |
| 100 | [0.6,0.8) | 56,134 | 0.0275 | 3.4470 | 0.008 | 0.0008 | 0.0008 |
| 100 | [0.8,1.0] | 26,522 | 0.0404 | 3.2838 | 0.012 | 0.0009 | 0.0008 |
| 250 | [-0.2,0.0) | 98,350 | 0.0072 | 5.1546 | 0.001 | 0.0010 | 0.0010 |
| 250 | [-0.4,-0.2) | 112,253 | 0.0175 | 4.5560 | 0.004 | 0.0014 | 0.0013 |
| 250 | [-0.6,-0.4) | 80,322 | 0.0344 | 4.1211 | 0.008 | 0.0014 | 0.0014 |
| 250 | [-0.8,-0.6) | 55,070 | 0.0566 | 3.7548 | 0.015 | 0.0015 | 0.0015 |
| 250 | [-1.0,-0.8) | 22,224 | 0.0763 | 3.4468 | 0.022 | 0.0024 | 0.0021 |
| 250 | [0.0,0.2) | 95,153 | 0.0065 | 4.3473 | 0.001 | 0.0009 | 0.0008 |
| 250 | [0.2,0.4) | 112,419 | 0.0190 | 3.7521 | 0.005 | 0.0012 | 0.0012 |
| 250 | [0.4,0.6) | 79,321 | 0.0357 | 3.5141 | 0.010 | 0.0014 | 0.0014 |
| 250 | [0.6,0.8) | 56,134 | 0.0586 | 3.4470 | 0.017 | 0.0020 | 0.0019 |
| 250 | [0.8,1.0] | 26,522 | 0.0738 | 3.2838 | 0.022 | 0.0021 | 0.0019 |
| 500 | [-0.2,0.0) | 98,350 | 0.0121 | 5.1546 | 0.002 | 0.0022 | 0.0021 |
| 500 | [-0.4,-0.2) | 112,253 | 0.0301 | 4.5560 | 0.007 | 0.0027 | 0.0026 |
| 500 | [-0.6,-0.4) | 80,322 | 0.0623 | 4.1211 | 0.015 | 0.0032 | 0.0031 |
| 500 | [-0.8,-0.6) | 55,070 | 0.0914 | 3.7548 | 0.024 | 0.0036 | 0.0035 |
| 500 | [-1.0,-0.8) | 22,224 | 0.1294 | 3.4468 | 0.038 | 0.0042 | 0.0039 |
| 500 | [0.0,0.2) | 95,153 | 0.0086 | 4.3473 | 0.002 | 0.0019 | 0.0018 |
| 500 | [0.2,0.4) | 112,419 | 0.0329 | 3.7521 | 0.009 | 0.0027 | 0.0025 |
| 500 | [0.4,0.6) | 79,321 | 0.0607 | 3.5141 | 0.017 | 0.0030 | 0.0029 |
| 500 | [0.6,0.8) | 56,134 | 0.0958 | 3.4470 | 0.028 | 0.0039 | 0.0036 |
| 500 | [0.8,1.0] | 26,522 | 0.1200 | 3.2838 | 0.037 | 0.0045 | 0.0043 |
| 1000 | [-0.2,0.0) | 98,350 | 0.0229 | 5.1546 | 0.004 | 0.0047 | 0.0047 |
| 1000 | [-0.4,-0.2) | 112,253 | 0.0520 | 4.5560 | 0.011 | 0.0060 | 0.0059 |
| 1000 | [-0.6,-0.4) | 80,322 | 0.1000 | 4.1211 | 0.024 | 0.0065 | 0.0063 |
| 1000 | [-0.8,-0.6) | 55,070 | 0.1484 | 3.7548 | 0.040 | 0.0076 | 0.0075 |
| 1000 | [-1.0,-0.8) | 22,224 | 0.2043 | 3.4468 | 0.059 | 0.0104 | 0.0099 |
| 1000 | [0.0,0.2) | 95,153 | 0.0169 | 4.3473 | 0.004 | 0.0043 | 0.0041 |
| 1000 | [0.2,0.4) | 112,419 | 0.0569 | 3.7521 | 0.015 | 0.0060 | 0.0059 |
| 1000 | [0.4,0.6) | 79,321 | 0.1019 | 3.5141 | 0.029 | 0.0066 | 0.0064 |
| 1000 | [0.6,0.8) | 56,134 | 0.1561 | 3.4470 | 0.045 | 0.0085 | 0.0081 |
| 1000 | [0.8,1.0] | 26,522 | 0.1850 | 3.2838 | 0.056 | 0.0097 | 0.0089 |

`coverage` is mean realized move / mean required move (the hurdle); `P(realized > B)` is the per-observation probability that the side-signed mid move beats the current spread plus the structural floor fee; `P(QIMB bound > 0)` adds clairvoyant abstention inside the dictated side.

## 3. Oracle aggressive upper bound — ORACLE_UPPER_BOUND (request §3)

**ORACLE_UPPER_BOUND uses future information by construction: at each decision instant it takes max(0, net_long, net_short) from the realised future bid/ask. It bounds what any causal side choice at these instants could have earned; it is not a strategy, not achievable, and must never enter model training, a backtest or a promotion decision.**

At each decision instant the oracle takes `max(0, net_buy, net_sell)` using the realised future bid/ask. The `mean_oracle_net` columns are therefore per-observation upper bounds on *any* causal aggressive execution at these instants after that regime's costs. `mean_oracle_gross` is the same bound before costs, and `oracle_trade_fraction` is the share of instants at which trading beats abstaining.

| horizon ms | obs | oracle gross | oracle trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered | P(net>0) structural_floor | oracle net structural_floor (signal-defined) |
|---|---|---|---|---|---|---|---|---|
| 100 | 737,768 | 0.0017 | 0.0010 | 0.0007 | 0.0001 | 0.0003 | 0.0009 | 0.0007 |
| 250 | 737,768 | 0.0043 | 0.0025 | 0.0018 | 0.0005 | 0.0008 | 0.0022 | 0.0018 |
| 500 | 737,768 | 0.0093 | 0.0053 | 0.0041 | 0.0011 | 0.0018 | 0.0047 | 0.0040 |
| 1000 | 737,768 | 0.0215 | 0.0118 | 0.0097 | 0.0026 | 0.0043 | 0.0104 | 0.0094 |

### 3a. Oracle upper bound by imbalance bin (all valid states)

| horizon ms | imbalance bin | obs | oracle gross | trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 98,350 | 0.0011 | 0.0007 | 0.0005 | 0.0002 | 0.0002 |
| 100 | [-0.4,-0.2) | 112,253 | 0.0016 | 0.0010 | 0.0006 | 0.0001 | 0.0003 |
| 100 | [-0.6,-0.4) | 80,322 | 0.0027 | 0.0012 | 0.0014 | 0.0006 | 0.0008 |
| 100 | [-0.8,-0.6) | 55,070 | 0.0011 | 0.0007 | 0.0004 | 0.0000 | 0.0001 |
| 100 | [-1.0,-0.8) | 22,224 | 0.0024 | 0.0016 | 0.0009 | 0.0001 | 0.0003 |
| 100 | [0.0,0.2) | 129,585 | 0.0015 | 0.0010 | 0.0006 | 0.0001 | 0.0002 |
| 100 | [0.2,0.4) | 112,419 | 0.0014 | 0.0009 | 0.0004 | 0.0000 | 0.0001 |
| 100 | [0.4,0.6) | 79,321 | 0.0016 | 0.0010 | 0.0005 | 0.0000 | 0.0001 |
| 100 | [0.6,0.8) | 56,134 | 0.0022 | 0.0012 | 0.0008 | 0.0001 | 0.0003 |
| 100 | [0.8,1.0] | 26,522 | 0.0021 | 0.0013 | 0.0009 | 0.0001 | 0.0003 |
| 250 | [-0.2,0.0) | 98,350 | 0.0037 | 0.0019 | 0.0018 | 0.0007 | 0.0009 |
| 250 | [-0.4,-0.2) | 112,253 | 0.0042 | 0.0025 | 0.0018 | 0.0005 | 0.0007 |
| 250 | [-0.6,-0.4) | 80,322 | 0.0050 | 0.0027 | 0.0023 | 0.0006 | 0.0010 |
| 250 | [-0.8,-0.6) | 55,070 | 0.0041 | 0.0025 | 0.0018 | 0.0004 | 0.0008 |
| 250 | [-1.0,-0.8) | 22,224 | 0.0065 | 0.0045 | 0.0026 | 0.0008 | 0.0012 |
| 250 | [0.0,0.2) | 129,585 | 0.0041 | 0.0024 | 0.0018 | 0.0004 | 0.0008 |
| 250 | [0.2,0.4) | 112,419 | 0.0039 | 0.0024 | 0.0016 | 0.0003 | 0.0006 |
| 250 | [0.4,0.6) | 79,321 | 0.0035 | 0.0025 | 0.0011 | 0.0001 | 0.0002 |
| 250 | [0.6,0.8) | 56,134 | 0.0061 | 0.0033 | 0.0027 | 0.0011 | 0.0014 |
| 250 | [0.8,1.0] | 26,522 | 0.0050 | 0.0030 | 0.0021 | 0.0004 | 0.0008 |
| 500 | [-0.2,0.0) | 98,350 | 0.0079 | 0.0042 | 0.0036 | 0.0012 | 0.0018 |
| 500 | [-0.4,-0.2) | 112,253 | 0.0084 | 0.0050 | 0.0034 | 0.0009 | 0.0014 |
| 500 | [-0.6,-0.4) | 80,322 | 0.0102 | 0.0055 | 0.0046 | 0.0012 | 0.0020 |
| 500 | [-0.8,-0.6) | 55,070 | 0.0095 | 0.0058 | 0.0041 | 0.0011 | 0.0018 |
| 500 | [-1.0,-0.8) | 22,224 | 0.0141 | 0.0078 | 0.0071 | 0.0027 | 0.0039 |
| 500 | [0.0,0.2) | 129,585 | 0.0092 | 0.0052 | 0.0041 | 0.0011 | 0.0018 |
| 500 | [0.2,0.4) | 112,419 | 0.0084 | 0.0050 | 0.0034 | 0.0007 | 0.0013 |
| 500 | [0.4,0.6) | 79,321 | 0.0089 | 0.0054 | 0.0037 | 0.0008 | 0.0015 |
| 500 | [0.6,0.8) | 56,134 | 0.0113 | 0.0061 | 0.0049 | 0.0014 | 0.0021 |
| 500 | [0.8,1.0] | 26,522 | 0.0132 | 0.0075 | 0.0060 | 0.0017 | 0.0028 |
| 1000 | [-0.2,0.0) | 98,350 | 0.0171 | 0.0094 | 0.0076 | 0.0022 | 0.0033 |
| 1000 | [-0.4,-0.2) | 112,253 | 0.0198 | 0.0111 | 0.0086 | 0.0022 | 0.0037 |
| 1000 | [-0.6,-0.4) | 80,322 | 0.0215 | 0.0114 | 0.0099 | 0.0022 | 0.0042 |
| 1000 | [-0.8,-0.6) | 55,070 | 0.0223 | 0.0132 | 0.0098 | 0.0030 | 0.0045 |
| 1000 | [-1.0,-0.8) | 22,224 | 0.0353 | 0.0178 | 0.0189 | 0.0078 | 0.0109 |
| 1000 | [0.0,0.2) | 129,585 | 0.0204 | 0.0113 | 0.0092 | 0.0024 | 0.0041 |
| 1000 | [0.2,0.4) | 112,419 | 0.0209 | 0.0112 | 0.0094 | 0.0022 | 0.0041 |
| 1000 | [0.4,0.6) | 79,321 | 0.0203 | 0.0118 | 0.0087 | 0.0020 | 0.0036 |
| 1000 | [0.6,0.8) | 56,134 | 0.0267 | 0.0139 | 0.0117 | 0.0031 | 0.0050 |
| 1000 | [0.8,1.0] | 26,522 | 0.0309 | 0.0164 | 0.0150 | 0.0045 | 0.0074 |

### 3b. Oracle upper bound by price band (all valid states)

| horizon ms | price band | obs | oracle gross | trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered |
|---|---|---|---|---|---|---|---|
| 100 | 100-200 | 93,600 | 0.0029 | 0.0025 | 0.0011 | 0.0003 | 0.0005 |
| 100 | 200+ | 23,400 | 0.0033 | 0.0047 | 0.0010 | 0.0004 | 0.0006 |
| 100 | 25-50 | 163,838 | 0.0016 | 0.0005 | 0.0007 | 0.0001 | 0.0002 |
| 100 | 5-25 | 23,400 | 0.0007 | 0.0000 | 0.0003 | 0.0000 | 0.0000 |
| 100 | 50-100 | 467,962 | 0.0014 | 0.0007 | 0.0006 | 0.0001 | 0.0002 |
| 250 | 100-200 | 93,600 | 0.0075 | 0.0060 | 0.0031 | 0.0011 | 0.0016 |
| 250 | 200+ | 23,400 | 0.0102 | 0.0148 | 0.0030 | 0.0013 | 0.0017 |
| 250 | 25-50 | 163,838 | 0.0050 | 0.0016 | 0.0021 | 0.0003 | 0.0006 |
| 250 | 5-25 | 23,400 | 0.0007 | 0.0000 | 0.0003 | 0.0000 | 0.0000 |
| 250 | 50-100 | 467,962 | 0.0034 | 0.0017 | 0.0015 | 0.0004 | 0.0007 |
| 500 | 100-200 | 93,600 | 0.0166 | 0.0124 | 0.0074 | 0.0031 | 0.0043 |
| 500 | 200+ | 23,400 | 0.0235 | 0.0324 | 0.0077 | 0.0031 | 0.0041 |
| 500 | 25-50 | 163,838 | 0.0110 | 0.0034 | 0.0050 | 0.0006 | 0.0016 |
| 500 | 5-25 | 23,400 | 0.0014 | 0.0001 | 0.0005 | 0.0000 | 0.0000 |
| 500 | 50-100 | 467,962 | 0.0070 | 0.0035 | 0.0031 | 0.0008 | 0.0013 |
| 1000 | 100-200 | 93,600 | 0.0366 | 0.0262 | 0.0175 | 0.0074 | 0.0103 |
| 1000 | 200+ | 23,400 | 0.0538 | 0.0693 | 0.0200 | 0.0085 | 0.0110 |
| 1000 | 25-50 | 163,838 | 0.0273 | 0.0080 | 0.0130 | 0.0023 | 0.0048 |
| 1000 | 5-25 | 23,400 | 0.0028 | 0.0001 | 0.0015 | 0.0000 | 0.0004 |
| 1000 | 50-100 | 467,962 | 0.0157 | 0.0079 | 0.0068 | 0.0015 | 0.0028 |

## 4. QIMB-constrained upper bound (request §4)

**QIMB_CONSTRAINED_BOUND keeps the side dictated by queue imbalance (the sign that defines the bin) and adds clairvoyant abstention only: max(0, net_side). No new threshold, no side choice and no model enters this bound.**

| horizon ms | imbalance bin | obs | net structural_floor | bound structural_floor | gap | bound accessible_fixed | bound accessible_tiered | P(bound>0) structural_floor |
|---|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 98,350 | -5.1477 | 0.0003 | 5.1479 | 0.0001 | 0.0001 | 0.0004 |
| 100 | [-0.4,-0.2) | 112,253 | -4.5453 | 0.0003 | 4.5456 | 0.0000 | 0.0001 | 0.0005 |
| 100 | [-0.6,-0.4) | 80,322 | -4.1052 | 0.0009 | 4.1060 | 0.0005 | 0.0006 | 0.0005 |
| 100 | [-0.8,-0.6) | 55,070 | -3.7314 | 0.0002 | 3.7317 | 0.0000 | 0.0001 | 0.0004 |
| 100 | [-1.0,-0.8) | 22,224 | -3.4111 | 0.0005 | 3.4116 | 0.0000 | 0.0001 | 0.0009 |
| 100 | [0.0,0.2) | 95,153 | -4.3409 | 0.0003 | 4.3412 | 0.0000 | 0.0001 | 0.0004 |
| 100 | [0.2,0.4) | 112,419 | -3.7429 | 0.0002 | 3.7431 | 0.0000 | 0.0000 | 0.0005 |
| 100 | [0.4,0.6) | 79,321 | -3.4970 | 0.0003 | 3.4973 | 0.0000 | 0.0000 | 0.0006 |
| 100 | [0.6,0.8) | 56,134 | -3.4214 | 0.0005 | 3.4219 | 0.0000 | 0.0001 | 0.0008 |
| 100 | [0.8,1.0] | 26,522 | -3.2477 | 0.0006 | 3.2483 | 0.0000 | 0.0001 | 0.0008 |
| 250 | [-0.2,0.0) | 98,350 | -5.1410 | 0.0011 | 5.1421 | 0.0006 | 0.0007 | 0.0010 |
| 250 | [-0.4,-0.2) | 112,253 | -4.5366 | 0.0009 | 4.5374 | 0.0001 | 0.0003 | 0.0013 |
| 250 | [-0.6,-0.4) | 80,322 | -4.0856 | 0.0013 | 4.0869 | 0.0003 | 0.0005 | 0.0014 |
| 250 | [-0.8,-0.6) | 55,070 | -3.7028 | 0.0011 | 3.7039 | 0.0003 | 0.0004 | 0.0015 |
| 250 | [-1.0,-0.8) | 22,224 | -3.3796 | 0.0009 | 3.3805 | 0.0001 | 0.0002 | 0.0021 |
| 250 | [0.0,0.2) | 95,153 | -4.3347 | 0.0008 | 4.3355 | 0.0002 | 0.0004 | 0.0008 |
| 250 | [0.2,0.4) | 112,419 | -3.7316 | 0.0007 | 3.7323 | 0.0001 | 0.0002 | 0.0012 |
| 250 | [0.4,0.6) | 79,321 | -3.4793 | 0.0007 | 3.4800 | 0.0000 | 0.0001 | 0.0014 |
| 250 | [0.6,0.8) | 56,134 | -3.3936 | 0.0020 | 3.3957 | 0.0009 | 0.0011 | 0.0019 |
| 250 | [0.8,1.0] | 26,522 | -3.2180 | 0.0012 | 3.2192 | 0.0001 | 0.0004 | 0.0019 |
| 500 | [-0.2,0.0) | 98,350 | -5.1332 | 0.0022 | 5.1354 | 0.0009 | 0.0012 | 0.0021 |
| 500 | [-0.4,-0.2) | 112,253 | -4.5236 | 0.0017 | 4.5254 | 0.0004 | 0.0006 | 0.0026 |
| 500 | [-0.6,-0.4) | 80,322 | -4.0575 | 0.0028 | 4.0603 | 0.0006 | 0.0011 | 0.0031 |
| 500 | [-0.8,-0.6) | 55,070 | -3.6705 | 0.0024 | 3.6729 | 0.0005 | 0.0009 | 0.0035 |
| 500 | [-1.0,-0.8) | 22,224 | -3.3304 | 0.0034 | 3.3338 | 0.0007 | 0.0014 | 0.0039 |
| 500 | [0.0,0.2) | 95,153 | -4.3295 | 0.0015 | 4.3311 | 0.0003 | 0.0006 | 0.0018 |
| 500 | [0.2,0.4) | 112,419 | -3.7175 | 0.0019 | 3.7194 | 0.0004 | 0.0007 | 0.0025 |
| 500 | [0.4,0.6) | 79,321 | -3.4537 | 0.0021 | 3.4558 | 0.0003 | 0.0007 | 0.0029 |
| 500 | [0.6,0.8) | 56,134 | -3.3597 | 0.0035 | 3.3632 | 0.0011 | 0.0016 | 0.0036 |
| 500 | [0.8,1.0] | 26,522 | -3.1747 | 0.0040 | 3.1787 | 0.0013 | 0.0019 | 0.0043 |
| 1000 | [-0.2,0.0) | 98,350 | -5.1176 | 0.0041 | 5.1217 | 0.0013 | 0.0019 | 0.0047 |
| 1000 | [-0.4,-0.2) | 112,253 | -4.5011 | 0.0045 | 4.5056 | 0.0010 | 0.0018 | 0.0059 |
| 1000 | [-0.6,-0.4) | 80,322 | -4.0194 | 0.0059 | 4.0252 | 0.0012 | 0.0024 | 0.0063 |
| 1000 | [-0.8,-0.6) | 55,070 | -3.6140 | 0.0058 | 3.6199 | 0.0016 | 0.0025 | 0.0075 |
| 1000 | [-1.0,-0.8) | 22,224 | -3.2503 | 0.0111 | 3.2613 | 0.0039 | 0.0058 | 0.0099 |
| 1000 | [0.0,0.2) | 95,153 | -4.3161 | 0.0029 | 4.3190 | 0.0005 | 0.0009 | 0.0041 |
| 1000 | [0.2,0.4) | 112,419 | -3.6918 | 0.0050 | 3.6968 | 0.0011 | 0.0020 | 0.0059 |
| 1000 | [0.4,0.6) | 79,321 | -3.4135 | 0.0049 | 3.4184 | 0.0009 | 0.0018 | 0.0064 |
| 1000 | [0.6,0.8) | 56,134 | -3.3015 | 0.0075 | 3.3090 | 0.0020 | 0.0031 | 0.0081 |
| 1000 | [0.8,1.0] | 26,522 | -3.1137 | 0.0079 | 3.1216 | 0.0019 | 0.0032 | 0.0089 |

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
| 100 | 0.0140 | 1.2878 | 1.2874 | 2.5752 | 1.5281 | 2.7401 | 1.5816 | -4.0893 | -6.8294 | -5.6709 |
| 250 | 0.0286 | 1.2878 | 1.2869 | 2.5747 | 1.5281 | 2.7401 | 1.5816 | -4.0742 | -6.8143 | -5.6558 |
| 500 | 0.0479 | 1.2878 | 1.2866 | 2.5744 | 1.5281 | 2.7401 | 1.5816 | -4.0546 | -6.7947 | -5.6362 |
| 1000 | 0.0794 | 1.2878 | 1.2852 | 2.5730 | 1.5281 | 2.7401 | 1.5816 | -4.0217 | -6.7618 | -5.6033 |

### 5a. Mechanism, computed from the decomposition

| horizon ms | signal (signed mid move) | full spread paid | mandatory fee (structural_floor) | required move | spread share of required | fee share of required | signal coverage | net structural_floor |
|---|---|---|---|---|---|---|---|---|
| 100 | 0.0140 | 2.5752 | 1.5281 | 4.1033 | 62.8% | 37.2% | 0.34% | -4.0893 |
| 250 | 0.0286 | 2.5747 | 1.5281 | 4.1028 | 62.8% | 37.2% | 0.70% | -4.0742 |
| 500 | 0.0479 | 2.5744 | 1.5281 | 4.1025 | 62.8% | 37.2% | 1.17% | -4.0546 |
| 1000 | 0.0794 | 2.5730 | 1.5281 | 4.1011 | 62.7% | 37.3% | 1.94% | -4.0217 |

The same decomposition expressed as what the signal would have to become: at 1000 ms the spread alone requires a mid move 32.4x larger than the realised one, and the mandatory floor fee alone requires 19.2x. Both multiples are measured, not projected: they are the ratio of a cost component to the realised edge at the same horizon.

| flag | holds | rule |
|---|---|---|
| SPREAD_DOMINATES | TRUE | the mean full spread paid is more than half of the required move at the longest declared horizon |
| FEES_DOMINATE | FALSE | the mean floor fee is more than half of the required move at the longest declared horizon |
| SIGNAL_MAGNITUDE_TOO_SMALL | TRUE | the side-signed mid move covers less than 10% of the required move at every declared horizon |
| WRONG_HORIZON | FALSE | extending the horizon across the whole declared grid (100 ms to 1000 ms, a factor of ten) closes at least half of the remaining gap |
| POOLED_LOW_QUALITY_STATES | FALSE | the dispersion of the net result across the declared (bin x horizon) states is less than half of its mean, i.e. the states barely separate |

Horizon increments of `net structural_floor` across the declared grid: 0.0150, 0.0197, 0.0329 bps, i.e. a ten-fold extension of the horizon closes 1.7% of the remaining gap (the required move itself is horizon-invariant: 4.1033 bps at 100 ms against 4.1011 bps at 1000 ms). Cross-state dispersion of the net result over the 40 (bin x horizon) states is 2.0339 bps, 52.4% of the mean, so the declared states barely separate. Holding flags: SPREAD_DOMINATES, SIGNAL_MAGNITUDE_TOO_SMALL.

## 6. Answers (request §6)

**1. Is there any development-sample state in the predeclared state space where aggressive execution approaches or exceeds the structural hurdle?**

No. 0 of the 400 declared cells (10 imbalance bins × 2 spread classes × 5 price bands × 4 horizons) have a positive structural-cost-adjusted result, and 0 of the 40 cells of the aggregated (bin × horizon) view do. The best cell in the whole declared space is `[-1.0,-0.8) · ONE_TICK · $200+ · 1000 ms` — -0.9748 bps net, i.e. still losing — with a hurdle coverage of 0.087 (mean side-signed mid move 0.0925 bps against a 1.0673 bps required move) on 934 observations.

Cells at each declared hurdle-coverage cut — the full 400-cell grid first, then the (bin × horizon) view: ≥1.0×: 0, ≥0.9×: 0, ≥0.75×: 0, ≥0.5×: 0 (full grid); ≥1.0×: 0, ≥0.9×: 0, ≥0.75×: 0, ≥0.5×: 0 (bin × horizon). These cuts are descriptive buckets, not selection rules: no state is promoted and none is killed, and the best cell is named only because the question asks where the maximum lies.

**2. What fraction of opportunities does that state represent?**

For the best aggregated state (`[0.8,1.0]` at 1000 ms): 3.595% of the signal-defined observations (26,522 of 737,768). For the best individual cell (`[-1.0,-0.8) · ONE_TICK · $200+ · 1000 ms`): 0.1266% (934 observations, 13 symbol-block cells, block-bootstrap SE 0.0128 bps). Both fractions are reported so that a reader can see how little of the opportunity set a favourable cell addresses even if it were real.

**3. Does a clairvoyant aggressive trader have meaningful room after costs?**

No. At the longest declared horizon (1000 ms), perfect side selection earns 0.0097 bps per observation after the structural floor and 0.0026 bps after accessible_fixed, 0.0043 bps after accessible_tiered, on 737,768 observations; it beats abstaining on 1.18% of them before costs and on 1.04% after the structural floor. That bound is 0.24% of the 4.1011 bps required move at the same horizon: the entire value of perfect foresight is about 0.013 bps per decision, three orders of magnitude below what the execution formulation needs. No predictive model can close that, and this is the strongest statement this calculation supports — it does not depend on any model, only on the realised future quotes.

**4. Which component creates the dominant economic gap?**

The gap is `required move - realised move` = 4.1011 - (0.0794) bps, decomposed exactly in §5: **the full spread paid contributes 62.7%** of the required move, **the mandatory venue/regulatory fee 37.3%**, and the signal supplies 1.94%. The broker reference layer on top of the floor is an additional 2.7401 bps (accessible_fixed), 1.5816 bps (accessible_tiered). Flags holding, with their rules in §5a: SPREAD_DOMINATES, SIGNAL_MAGNITUDE_TOO_SMALL.

Reading: the dominant component is the **spread** (62.7% of the hurdle), the fee is second, and the signal is not a large contributor to the gap because it is negligible in absolute terms — it would need to be 32.4x larger merely to pay the spread. That is a combination, and the decomposition is the evidence for it; nothing here is inferred from the shape of the results alone.

## 7. Reconciliation and limitations

| check | observations | mismatches / max abs difference / ratio | tolerance | outcome |
|---|---|---|---|---|
| execution_instant_is_decision_instant | 772,200 | 0 | 0 | PASS |
| frozen_execution_comparison | 2,951,072 | NaN |  | NOT_EVALUATED_REFERENCE_ABSENT |
| decomposition_identity_pooled | 2,951,072 | 0.0000 | 1e-09 | PASS |
| spread_hurdle_is_cross_to_cross_breakeven | 2,951,072 | 0.0000 | 1e-09 | PASS |
| oracle_bound_dominates_and_is_non_negative | 9,266,400 | 0 | 1e-09 | PASS |
| qimb_bound_below_oracle_bound | 8,853,216 | 0 | 1e-09 | PASS |
| state_partition_covers_every_observation | 737,768 | 737,768 in cells | 0 | PASS |
| fee_lookup_matches_ledger_at_observation_prices | 1,620 | 0.0000 | 1e-09 | PASS |
| tick_and_half_spread_arithmetic | 772,200 | 0 | 1e-09 | PASS |

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
