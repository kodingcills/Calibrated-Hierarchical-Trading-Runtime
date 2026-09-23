# M2-0.5 — AGGRESSIVE MONETIZATION FEASIBILITY BOUND

Candidate `TUP-NASDAQ-LARGETICK-H2-QIMB-AGG` · run `M2-0-NASDAQ-QIMB-BASELINE` · development sample day `2019-07-30` · dataset `NASDAQ-ITCH50-PUBLIC-SAMPLE-20190730` · cost ledger `M2-COST-LEDGER-v1`

**No data was acquired, no model was trained, no threshold was optimised, Jev was not used, M1 and the research framework were not modified, and no artifact of M2-0 was rewritten.** This pass reads the frozen M2-0 development artifacts and conditions the existing aggressive execution arithmetic on the predeclared state space. It promotes nothing and kills nothing.

| item | value |
|---|---|
| execution instant | delay_decisions.parquet, delay 0 ms (the M2-0 idealized aggressive instant) |
| observations (level 0) | 1,427,400 valid decision states of 1,427,400 delay rows |
| observations (level 1) | 1,340,431 with a defined signal side (imbalance != 0) |
| state space | 10 imbalance bins x 2 spread classes x 5 price bands = 100 cells per horizon, 400 rows over 4 horizons |
| cost regimes | structural_floor, accessible_fixed, accessible_tiered (round trip, 100-share representative size) |
| config sha256 | 0f366bb445418a85ca001a290006531a0bb6ca2cb759b7a11694030dac13a16b |
| cost ledger sha256 | 52ce785fc7210138af4059e327fc7101dff7f78dff3f5156c045973c1ed4cb17 |
| code sha256 | M2/src/feasibility.py caaf0efdbcdbae7b… |
| derived artifacts | decisions.parquet d1943b46a0e50d9a…; delay_decisions.parquet c98c417096099841… |

## 0. Observation accounting

The delay-0 slice of `delay_decisions.parquet` is a 1 s decimation of the predeclared 100 ms decision grid and carries the realised future two-sided quote that a cross-to-cross result requires. It is verified below (check `execution_instant_is_decision_instant`) to reproduce `decisions.parquet` exactly at the same `(ts_ns, locate)` on every row, so no observation is invented and none is redefined.

| observation set | count | note |
|---|---|---|
| delay rows at delay 0 | 1,427,400 | 1 s grid, 61 development-scope symbols |
| valid decision states | 1,427,400 | two-sided, uncrossed, arrival present |
|     of which imbalance == 0 | 86,969 | in the state space but with no sign to trade; kept in the oracle set, excluded from side-dependent cells (the M2-0 execution filter) |
| signal-defined observations | 1,340,431 | imbalance != 0; the base of every state-conditioned cell |
| outside the declared price bands | 0 | none: every observation falls in one of the five declared bands |
| future quote missing at 100 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 250 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 500 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| future quote missing at 1000 ms | 0 | rows kept in the state space, dropped from that horizon's cells |
| imbalance == 0 at 100 ms | 86,969 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 250 ms | 86,969 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 500 ms | 86,969 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
| imbalance == 0 at 1000 ms | 86,969 | no sign to trade; kept in the oracle set, excluded from the side-dependent cells |
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
| 100 | 1,340,431 | 0.0001 | 0.0143 | -1.6709 | -3.3548 | 3.3691 | 1.4445 | -4.7994 | -7.3534 | -6.2811 | 0.0004 |
| 250 | 1,340,431 | 0.0018 | 0.0304 | -1.6548 | -3.3381 | 3.3686 | 1.4445 | -4.7827 | -7.3366 | -6.2644 | 0.0011 |
| 500 | 1,340,431 | 0.0023 | 0.0511 | -1.6341 | -3.3172 | 3.3683 | 1.4445 | -4.7618 | -7.3157 | -6.2434 | 0.0024 |
| 1000 | 1,340,431 | 0.0032 | 0.0846 | -1.6006 | -3.2825 | 3.3671 | 1.4445 | -4.7271 | -7.2810 | -6.2087 | 0.0055 |

### 1b. By spread class

| horizon ms | spread class | obs | spread bps | signed mid move | cross-to-cross | net structural_floor | net accessible_fixed | net accessible_tiered | P(net>0) structural_floor |
|---|---|---|---|---|---|---|---|---|---|
| 100 | ONE_TICK | 810,436 | 2.7088 | 0.0167 | -2.6984 | -4.5825 | -8.1160 | -6.5900 | 0.0005 |
| 100 | WIDER_THAN_ONE_TICK | 529,995 | 4.3822 | 0.0106 | -4.3586 | -5.1310 | -6.1872 | -5.8086 | 0.0004 |
| 250 | ONE_TICK | 810,436 | 2.7088 | 0.0358 | -2.6856 | -4.5697 | -8.1031 | -6.5772 | 0.0012 |
| 250 | WIDER_THAN_ONE_TICK | 529,995 | 4.3822 | 0.0223 | -4.3359 | -5.1083 | -6.1646 | -5.7860 | 0.0011 |
| 500 | ONE_TICK | 810,436 | 2.7088 | 0.0611 | -2.6685 | -4.5526 | -8.0861 | -6.5601 | 0.0025 |
| 500 | WIDER_THAN_ONE_TICK | 529,995 | 4.3822 | 0.0358 | -4.3091 | -5.0816 | -6.1378 | -5.7592 | 0.0023 |
| 1000 | ONE_TICK | 810,436 | 2.7088 | 0.1026 | -2.6392 | -4.5233 | -8.0567 | -6.5308 | 0.0057 |
| 1000 | WIDER_THAN_ONE_TICK | 529,995 | 4.3822 | 0.0571 | -4.2663 | -5.0387 | -6.0949 | -5.7163 | 0.0051 |

### 1c. By price band

| horizon ms | price band | obs | mean price | spread bps | signed mid move | cross-to-cross | fee structural_floor | fee accessible_fixed | fee accessible_tiered | net structural_floor | net accessible_fixed | net accessible_tiered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 100-200 | 303,035 | 128.33 | 3.0474 | 0.0118 | -3.0337 | 0.7100 | 1.6273 | 1.3131 | -3.7438 | -4.6610 | -4.3468 |
| 100 | 200+ | 184,237 | 671.21 | 3.6762 | 0.0069 | -3.6674 | 0.3871 | 0.5845 | 0.6037 | -4.0545 | -4.2520 | -4.2711 |
| 100 | 25-50 | 307,494 | 38.04 | 3.2901 | 0.0172 | -3.2715 | 1.9069 | 5.4913 | 3.9418 | -5.1785 | -8.7629 | -7.2133 |
| 100 | 5-25 | 115,190 | 14.37 | 7.9939 | 0.0301 | -7.9638 | 4.8696 | 15.0562 | 10.4488 | -12.8334 | -23.0199 | -18.4126 |
| 100 | 50-100 | 430,475 | 67.40 | 2.2872 | 0.0129 | -2.2733 | 1.1674 | 3.1037 | 2.3174 | -3.4407 | -5.3770 | -4.5908 |
| 250 | 100-200 | 303,035 | 128.33 | 3.0474 | 0.0227 | -3.0226 | 0.7100 | 1.6273 | 1.3131 | -3.7327 | -4.6499 | -4.3357 |
| 250 | 200+ | 184,237 | 671.21 | 3.6762 | 0.0159 | -3.6574 | 0.3871 | 0.5845 | 0.6037 | -4.0444 | -4.2419 | -4.2610 |
| 250 | 25-50 | 307,494 | 38.04 | 3.2901 | 0.0358 | -3.2519 | 1.9069 | 5.4913 | 3.9418 | -5.1589 | -8.7433 | -7.1937 |
| 250 | 5-25 | 115,190 | 14.37 | 7.9939 | 0.0735 | -7.9198 | 4.8696 | 15.0562 | 10.4488 | -12.7895 | -22.9760 | -18.3687 |
| 250 | 50-100 | 430,475 | 67.40 | 2.2872 | 0.0268 | -2.2591 | 1.1674 | 3.1037 | 2.3174 | -3.4265 | -5.3628 | -4.5766 |
| 500 | 100-200 | 303,035 | 128.33 | 3.0474 | 0.0346 | -3.0105 | 0.7100 | 1.6273 | 1.3131 | -3.7206 | -4.6378 | -4.3236 |
| 500 | 200+ | 184,237 | 671.21 | 3.6762 | 0.0253 | -3.6496 | 0.3871 | 0.5845 | 0.6037 | -4.0366 | -4.2341 | -4.2532 |
| 500 | 25-50 | 307,494 | 38.04 | 3.2901 | 0.0626 | -3.2247 | 1.9069 | 5.4913 | 3.9418 | -5.1316 | -8.7160 | -7.1665 |
| 500 | 5-25 | 115,190 | 14.37 | 7.9939 | 0.1272 | -7.8651 | 4.8696 | 15.0562 | 10.4488 | -12.7347 | -22.9213 | -18.3139 |
| 500 | 50-100 | 430,475 | 67.40 | 2.2872 | 0.0452 | -2.2400 | 1.1674 | 3.1037 | 2.3174 | -3.4074 | -5.3437 | -4.5575 |
| 1000 | 100-200 | 303,035 | 128.33 | 3.0474 | 0.0537 | -2.9895 | 0.7100 | 1.6273 | 1.3131 | -3.6996 | -4.6168 | -4.3026 |
| 1000 | 200+ | 184,237 | 671.21 | 3.6762 | 0.0387 | -3.6386 | 0.3871 | 0.5845 | 0.6037 | -4.0256 | -4.2231 | -4.2422 |
| 1000 | 25-50 | 307,494 | 38.04 | 3.2901 | 0.1085 | -3.1778 | 1.9069 | 5.4913 | 3.9418 | -5.0847 | -8.6691 | -7.1196 |
| 1000 | 5-25 | 115,190 | 14.37 | 7.9939 | 0.2108 | -7.7763 | 4.8696 | 15.0562 | 10.4488 | -12.6459 | -22.8324 | -18.2251 |
| 1000 | 50-100 | 430,475 | 67.40 | 2.2872 | 0.0752 | -2.2087 | 1.1674 | 3.1037 | 2.3174 | -3.3761 | -5.3124 | -4.5262 |

### 1d. By imbalance bin and horizon (structural floor)

| horizon ms | imbalance bin | obs | spread paid | signed mid move | cross-to-cross | net structural_floor | P(net>0) structural_floor |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 158,398 | 3.3242 | 0.0046 | -3.3196 | -4.9479 | 0.0003 |
| 100 | [-0.4,-0.2) | 189,759 | 3.3839 | 0.0098 | -3.3740 | -4.8561 | 0.0005 |
| 100 | [-0.6,-0.4) | 129,214 | 3.2743 | 0.0193 | -3.2549 | -4.7501 | 0.0005 |
| 100 | [-0.8,-0.6) | 92,542 | 3.3135 | 0.0269 | -3.2867 | -4.6952 | 0.0005 |
| 100 | [-1.0,-0.8) | 79,725 | 3.5694 | 0.0246 | -3.5448 | -4.4438 | 0.0006 |
| 100 | [0.0,0.2) | 167,020 | 3.3178 | 0.0029 | -3.3150 | -4.9469 | 0.0003 |
| 100 | [0.2,0.4) | 203,066 | 3.3792 | 0.0085 | -3.3707 | -4.8541 | 0.0004 |
| 100 | [0.4,0.6) | 137,827 | 3.2509 | 0.0176 | -3.2332 | -4.7502 | 0.0005 |
| 100 | [0.6,0.8) | 98,003 | 3.3408 | 0.0282 | -3.3126 | -4.7408 | 0.0006 |
| 100 | [0.8,1.0] | 84,877 | 3.7388 | 0.0262 | -3.7126 | -4.6443 | 0.0005 |
| 250 | [-0.2,0.0) | 158,398 | 3.3204 | 0.0075 | -3.3129 | -4.9413 | 0.0008 |
| 250 | [-0.4,-0.2) | 189,759 | 3.3829 | 0.0191 | -3.3638 | -4.8458 | 0.0012 |
| 250 | [-0.6,-0.4) | 129,214 | 3.2732 | 0.0388 | -3.2344 | -4.7296 | 0.0012 |
| 250 | [-0.8,-0.6) | 92,542 | 3.3160 | 0.0578 | -3.2581 | -4.6667 | 0.0017 |
| 250 | [-1.0,-0.8) | 79,725 | 3.5717 | 0.0505 | -3.5212 | -4.4201 | 0.0016 |
| 250 | [0.0,0.2) | 167,020 | 3.3150 | 0.0085 | -3.3066 | -4.9385 | 0.0007 |
| 250 | [0.2,0.4) | 203,066 | 3.3775 | 0.0208 | -3.3567 | -4.8402 | 0.0010 |
| 250 | [0.4,0.6) | 137,827 | 3.2501 | 0.0372 | -3.2129 | -4.7299 | 0.0011 |
| 250 | [0.6,0.8) | 98,003 | 3.3441 | 0.0634 | -3.2807 | -4.7089 | 0.0015 |
| 250 | [0.8,1.0] | 84,877 | 3.7427 | 0.0545 | -3.6881 | -4.6199 | 0.0012 |
| 500 | [-0.2,0.0) | 158,398 | 3.3179 | 0.0103 | -3.3077 | -4.9360 | 0.0019 |
| 500 | [-0.4,-0.2) | 189,759 | 3.3827 | 0.0316 | -3.3511 | -4.8331 | 0.0024 |
| 500 | [-0.6,-0.4) | 129,214 | 3.2714 | 0.0709 | -3.2005 | -4.6958 | 0.0028 |
| 500 | [-0.8,-0.6) | 92,542 | 3.3169 | 0.0998 | -3.2171 | -4.6256 | 0.0035 |
| 500 | [-1.0,-0.8) | 79,725 | 3.5750 | 0.0845 | -3.4906 | -4.3895 | 0.0029 |
| 500 | [0.0,0.2) | 167,020 | 3.3120 | 0.0130 | -3.2990 | -4.9309 | 0.0017 |
| 500 | [0.2,0.4) | 203,066 | 3.3765 | 0.0354 | -3.3410 | -4.8245 | 0.0021 |
| 500 | [0.4,0.6) | 137,827 | 3.2500 | 0.0624 | -3.1876 | -4.7046 | 0.0024 |
| 500 | [0.6,0.8) | 98,003 | 3.3491 | 0.1051 | -3.2441 | -4.6723 | 0.0030 |
| 500 | [0.8,1.0] | 84,877 | 3.7457 | 0.0887 | -3.6570 | -4.5887 | 0.0026 |
| 1000 | [-0.2,0.0) | 158,398 | 3.3132 | 0.0196 | -3.2936 | -4.9220 | 0.0045 |
| 1000 | [-0.4,-0.2) | 189,759 | 3.3824 | 0.0564 | -3.3259 | -4.8080 | 0.0055 |
| 1000 | [-0.6,-0.4) | 129,214 | 3.2712 | 0.1127 | -3.1585 | -4.6537 | 0.0061 |
| 1000 | [-0.8,-0.6) | 92,542 | 3.3203 | 0.1671 | -3.1533 | -4.5618 | 0.0073 |
| 1000 | [-1.0,-0.8) | 79,725 | 3.5680 | 0.1343 | -3.4337 | -4.3327 | 0.0069 |
| 1000 | [0.0,0.2) | 167,020 | 3.3074 | 0.0186 | -3.2887 | -4.9206 | 0.0038 |
| 1000 | [0.2,0.4) | 203,066 | 3.3747 | 0.0615 | -3.3132 | -4.7967 | 0.0049 |
| 1000 | [0.4,0.6) | 137,827 | 3.2507 | 0.1068 | -3.1439 | -4.6609 | 0.0054 |
| 1000 | [0.6,0.8) | 98,003 | 3.3502 | 0.1706 | -3.1796 | -4.6078 | 0.0068 |
| 1000 | [0.8,1.0] | 84,877 | 3.7503 | 0.1395 | -3.6108 | -4.5425 | 0.0060 |

### 1e. The best and worst declared cells (descriptive only — nothing is selected)

| cell | obs | share of obs | spread bps | signed mid move | cross-to-cross | net structural_floor | block SE | block cells |
|---|---|---|---|---|---|---|---|---|
| [-1.0,-0.8) · ONE_TICK · $200+ · 250 ms | 1,002 | 0.0007 | 0.4763 | 0.1023 | -0.4515 | -0.9526 | 0.0661 | 30 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 500 ms | 1,002 | 0.0007 | 0.4763 | 0.1435 | -0.4558 | -0.9569 | 0.0653 | 30 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 1000 ms | 1,002 | 0.0007 | 0.4763 | 0.1848 | -0.4594 | -0.9605 | 0.0662 | 30 |
| [-1.0,-0.8) · ONE_TICK · $200+ · 100 ms | 1,002 | 0.0007 | 0.4763 | 0.0641 | -0.4600 | -0.9611 | 0.0402 | 30 |
| [-0.8,-0.6) · ONE_TICK · $200+ · 100 ms | 1,304 | 0.0010 | 0.4771 | 0.0410 | -0.4764 | -0.9780 | 0.0078 | 27 |

Worst five cells by `net structural_floor`: [-1.0,-0.8)/WIDER_THAN_ONE_TICK/$5-25/1000 ms = -36.6438 bps; [-1.0,-0.8)/WIDER_THAN_ONE_TICK/$5-25/100 ms = -36.4789 bps; [-1.0,-0.8)/WIDER_THAN_ONE_TICK/$5-25/250 ms = -36.3571 bps; [-1.0,-0.8)/WIDER_THAN_ONE_TICK/$5-25/500 ms = -36.2343 bps; [0.8,1.0]/WIDER_THAN_ONE_TICK/$5-25/100 ms = -30.9354 bps.

## 2. Break-even hurdles (request §2)

Hurdle A is the current quoted spread (cross in, cross out); B adds the structural floor round trip; C adds each accessible reference path. `realized_move_bps` is the side-signed mid move, so `realized > hurdle` is the break-even test and `P(realized > hurdle A)` equals `P(cross-to-cross > 0)` up to the measured spread-change term. Full distributions and ratios per cell are in `breakeven_hurdle.csv`; the pooled view is below.

| horizon ms | realized (mean) | required A (spread) | required structural_floor | required accessible_fixed | required accessible_tiered | P(>A) | P(>structural_floor) | P(>accessible_fixed) | P(>accessible_tiered) |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 0.0143 | 3.3704 | 4.8150 | 7.3690 | 6.2967 | 0.0008 | 0.0004 | 0.0001 | 0.0001 |
| 250 | 0.0304 | 3.3704 | 4.8150 | 7.3690 | 6.2967 | 0.0020 | 0.0011 | 0.0003 | 0.0004 |
| 500 | 0.0511 | 3.3704 | 4.8150 | 7.3690 | 6.2967 | 0.0040 | 0.0024 | 0.0006 | 0.0008 |
| 1000 | 0.0846 | 3.3704 | 4.8150 | 7.3690 | 6.2967 | 0.0084 | 0.0055 | 0.0015 | 0.0020 |

### 2a. Hurdle coverage by imbalance bin and horizon (mean realized move / mean required move, structural)

| horizon ms | imbalance bin | obs | realized | required | coverage | P(realized > B) | P(QIMB bound > 0) |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 158,398 | 0.0046 | 4.9565 | 0.001 | 0.0004 | 0.0003 |
| 100 | [-0.4,-0.2) | 189,759 | 0.0098 | 4.8685 | 0.002 | 0.0006 | 0.0005 |
| 100 | [-0.6,-0.4) | 129,214 | 0.0193 | 4.7707 | 0.004 | 0.0006 | 0.0005 |
| 100 | [-0.8,-0.6) | 92,542 | 0.0269 | 4.7196 | 0.006 | 0.0008 | 0.0005 |
| 100 | [-1.0,-0.8) | 79,725 | 0.0246 | 4.4656 | 0.006 | 0.0009 | 0.0006 |
| 100 | [0.0,0.2) | 167,020 | 0.0029 | 4.9536 | 0.001 | 0.0004 | 0.0003 |
| 100 | [0.2,0.4) | 203,066 | 0.0085 | 4.8659 | 0.002 | 0.0005 | 0.0004 |
| 100 | [0.4,0.6) | 137,827 | 0.0176 | 4.7683 | 0.004 | 0.0006 | 0.0005 |
| 100 | [0.6,0.8) | 98,003 | 0.0282 | 4.7666 | 0.006 | 0.0009 | 0.0006 |
| 100 | [0.8,1.0] | 84,877 | 0.0262 | 4.6678 | 0.006 | 0.0009 | 0.0005 |
| 250 | [-0.2,0.0) | 158,398 | 0.0075 | 4.9565 | 0.002 | 0.0011 | 0.0008 |
| 250 | [-0.4,-0.2) | 189,759 | 0.0191 | 4.8685 | 0.004 | 0.0014 | 0.0012 |
| 250 | [-0.6,-0.4) | 129,214 | 0.0388 | 4.7707 | 0.008 | 0.0014 | 0.0012 |
| 250 | [-0.8,-0.6) | 92,542 | 0.0578 | 4.7196 | 0.012 | 0.0019 | 0.0017 |
| 250 | [-1.0,-0.8) | 79,725 | 0.0505 | 4.4656 | 0.011 | 0.0020 | 0.0016 |
| 250 | [0.0,0.2) | 167,020 | 0.0085 | 4.9536 | 0.002 | 0.0010 | 0.0007 |
| 250 | [0.2,0.4) | 203,066 | 0.0208 | 4.8659 | 0.004 | 0.0013 | 0.0010 |
| 250 | [0.4,0.6) | 137,827 | 0.0372 | 4.7683 | 0.008 | 0.0014 | 0.0011 |
| 250 | [0.6,0.8) | 98,003 | 0.0634 | 4.7666 | 0.013 | 0.0022 | 0.0015 |
| 250 | [0.8,1.0] | 84,877 | 0.0545 | 4.6678 | 0.012 | 0.0021 | 0.0012 |
| 500 | [-0.2,0.0) | 158,398 | 0.0103 | 4.9565 | 0.002 | 0.0022 | 0.0019 |
| 500 | [-0.4,-0.2) | 189,759 | 0.0316 | 4.8685 | 0.006 | 0.0027 | 0.0024 |
| 500 | [-0.6,-0.4) | 129,214 | 0.0709 | 4.7707 | 0.015 | 0.0031 | 0.0028 |
| 500 | [-0.8,-0.6) | 92,542 | 0.0998 | 4.7196 | 0.021 | 0.0040 | 0.0035 |
| 500 | [-1.0,-0.8) | 79,725 | 0.0845 | 4.4656 | 0.019 | 0.0037 | 0.0029 |
| 500 | [0.0,0.2) | 167,020 | 0.0130 | 4.9536 | 0.003 | 0.0020 | 0.0017 |
| 500 | [0.2,0.4) | 203,066 | 0.0354 | 4.8659 | 0.007 | 0.0026 | 0.0021 |
| 500 | [0.4,0.6) | 137,827 | 0.0624 | 4.7683 | 0.013 | 0.0029 | 0.0024 |
| 500 | [0.6,0.8) | 98,003 | 0.1051 | 4.7666 | 0.022 | 0.0042 | 0.0030 |
| 500 | [0.8,1.0] | 84,877 | 0.0887 | 4.6678 | 0.019 | 0.0040 | 0.0026 |
| 1000 | [-0.2,0.0) | 158,398 | 0.0196 | 4.9565 | 0.004 | 0.0050 | 0.0045 |
| 1000 | [-0.4,-0.2) | 189,759 | 0.0564 | 4.8685 | 0.012 | 0.0060 | 0.0055 |
| 1000 | [-0.6,-0.4) | 129,214 | 0.1127 | 4.7707 | 0.024 | 0.0067 | 0.0061 |
| 1000 | [-0.8,-0.6) | 92,542 | 0.1671 | 4.7196 | 0.035 | 0.0080 | 0.0073 |
| 1000 | [-1.0,-0.8) | 79,725 | 0.1343 | 4.4656 | 0.030 | 0.0085 | 0.0069 |
| 1000 | [0.0,0.2) | 167,020 | 0.0186 | 4.9536 | 0.004 | 0.0045 | 0.0038 |
| 1000 | [0.2,0.4) | 203,066 | 0.0615 | 4.8659 | 0.013 | 0.0059 | 0.0049 |
| 1000 | [0.4,0.6) | 137,827 | 0.1068 | 4.7683 | 0.022 | 0.0064 | 0.0054 |
| 1000 | [0.6,0.8) | 98,003 | 0.1706 | 4.7666 | 0.036 | 0.0086 | 0.0068 |
| 1000 | [0.8,1.0] | 84,877 | 0.1395 | 4.6678 | 0.030 | 0.0086 | 0.0060 |

`coverage` is mean realized move / mean required move (the hurdle); `P(realized > B)` is the per-observation probability that the side-signed mid move beats the current spread plus the structural floor fee; `P(QIMB bound > 0)` adds clairvoyant abstention inside the dictated side.

## 3. Oracle aggressive upper bound — ORACLE_UPPER_BOUND (request §3)

**ORACLE_UPPER_BOUND uses future information by construction: at each decision instant it takes max(0, net_long, net_short) from the realised future bid/ask. It bounds what any causal side choice at these instants could have earned; it is not a strategy, not achievable, and must never enter model training, a backtest or a promotion decision.**

At each decision instant the oracle takes `max(0, net_buy, net_sell)` using the realised future bid/ask. The `mean_oracle_net` columns are therefore per-observation upper bounds on *any* causal aggressive execution at these instants after that regime's costs. `mean_oracle_gross` is the same bound before costs, and `oracle_trade_fraction` is the share of instants at which trading beats abstaining.

| horizon ms | obs | oracle gross | oracle trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered | P(net>0) structural_floor | oracle net structural_floor (signal-defined) |
|---|---|---|---|---|---|---|---|---|
| 100 | 1,340,431 | 0.0018 | 0.0010 | 0.0009 | 0.0004 | 0.0005 | 0.0008 | 0.0009 |
| 250 | 1,340,431 | 0.0047 | 0.0024 | 0.0024 | 0.0010 | 0.0013 | 0.0019 | 0.0023 |
| 500 | 1,340,431 | 0.0103 | 0.0051 | 0.0054 | 0.0025 | 0.0031 | 0.0042 | 0.0053 |
| 1000 | 1,340,431 | 0.0240 | 0.0113 | 0.0129 | 0.0060 | 0.0076 | 0.0095 | 0.0127 |

### 3a. Oracle upper bound by imbalance bin (all valid states)

| horizon ms | imbalance bin | obs | oracle gross | trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered |
|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 158,398 | 0.0011 | 0.0007 | 0.0005 | 0.0002 | 0.0003 |
| 100 | [-0.4,-0.2) | 189,759 | 0.0015 | 0.0009 | 0.0007 | 0.0002 | 0.0004 |
| 100 | [-0.6,-0.4) | 129,214 | 0.0024 | 0.0011 | 0.0013 | 0.0005 | 0.0007 |
| 100 | [-0.8,-0.6) | 92,542 | 0.0021 | 0.0009 | 0.0011 | 0.0005 | 0.0007 |
| 100 | [-1.0,-0.8) | 79,725 | 0.0026 | 0.0013 | 0.0017 | 0.0012 | 0.0013 |
| 100 | [0.0,0.2) | 253,989 | 0.0017 | 0.0009 | 0.0008 | 0.0003 | 0.0004 |
| 100 | [0.2,0.4) | 203,066 | 0.0015 | 0.0008 | 0.0007 | 0.0003 | 0.0004 |
| 100 | [0.4,0.6) | 137,827 | 0.0016 | 0.0009 | 0.0007 | 0.0002 | 0.0003 |
| 100 | [0.6,0.8) | 98,003 | 0.0029 | 0.0013 | 0.0016 | 0.0009 | 0.0011 |
| 100 | [0.8,1.0] | 84,877 | 0.0018 | 0.0011 | 0.0010 | 0.0005 | 0.0006 |
| 250 | [-0.2,0.0) | 158,398 | 0.0039 | 0.0019 | 0.0019 | 0.0008 | 0.0010 |
| 250 | [-0.4,-0.2) | 189,759 | 0.0042 | 0.0024 | 0.0020 | 0.0008 | 0.0011 |
| 250 | [-0.6,-0.4) | 129,214 | 0.0055 | 0.0025 | 0.0028 | 0.0010 | 0.0014 |
| 250 | [-0.8,-0.6) | 92,542 | 0.0056 | 0.0028 | 0.0029 | 0.0012 | 0.0016 |
| 250 | [-1.0,-0.8) | 79,725 | 0.0064 | 0.0032 | 0.0041 | 0.0029 | 0.0032 |
| 250 | [0.0,0.2) | 253,989 | 0.0042 | 0.0022 | 0.0021 | 0.0008 | 0.0011 |
| 250 | [0.2,0.4) | 203,066 | 0.0041 | 0.0022 | 0.0020 | 0.0007 | 0.0010 |
| 250 | [0.4,0.6) | 137,827 | 0.0040 | 0.0021 | 0.0016 | 0.0005 | 0.0006 |
| 250 | [0.6,0.8) | 98,003 | 0.0070 | 0.0030 | 0.0038 | 0.0019 | 0.0023 |
| 250 | [0.8,1.0] | 84,877 | 0.0045 | 0.0029 | 0.0025 | 0.0014 | 0.0017 |
| 500 | [-0.2,0.0) | 158,398 | 0.0085 | 0.0042 | 0.0042 | 0.0017 | 0.0022 |
| 500 | [-0.4,-0.2) | 189,759 | 0.0092 | 0.0048 | 0.0045 | 0.0020 | 0.0025 |
| 500 | [-0.6,-0.4) | 129,214 | 0.0115 | 0.0052 | 0.0059 | 0.0024 | 0.0032 |
| 500 | [-0.8,-0.6) | 92,542 | 0.0129 | 0.0060 | 0.0070 | 0.0034 | 0.0042 |
| 500 | [-1.0,-0.8) | 79,725 | 0.0136 | 0.0060 | 0.0091 | 0.0063 | 0.0070 |
| 500 | [0.0,0.2) | 253,989 | 0.0098 | 0.0048 | 0.0052 | 0.0023 | 0.0030 |
| 500 | [0.2,0.4) | 203,066 | 0.0085 | 0.0046 | 0.0041 | 0.0015 | 0.0021 |
| 500 | [0.4,0.6) | 137,827 | 0.0104 | 0.0049 | 0.0051 | 0.0019 | 0.0026 |
| 500 | [0.6,0.8) | 98,003 | 0.0136 | 0.0061 | 0.0071 | 0.0033 | 0.0041 |
| 500 | [0.8,1.0] | 84,877 | 0.0109 | 0.0063 | 0.0061 | 0.0034 | 0.0039 |
| 1000 | [-0.2,0.0) | 158,398 | 0.0203 | 0.0095 | 0.0102 | 0.0040 | 0.0053 |
| 1000 | [-0.4,-0.2) | 189,759 | 0.0224 | 0.0107 | 0.0118 | 0.0052 | 0.0068 |
| 1000 | [-0.6,-0.4) | 129,214 | 0.0245 | 0.0112 | 0.0129 | 0.0051 | 0.0071 |
| 1000 | [-0.8,-0.6) | 92,542 | 0.0290 | 0.0133 | 0.0161 | 0.0079 | 0.0099 |
| 1000 | [-1.0,-0.8) | 79,725 | 0.0302 | 0.0136 | 0.0198 | 0.0131 | 0.0148 |
| 1000 | [0.0,0.2) | 253,989 | 0.0221 | 0.0105 | 0.0118 | 0.0053 | 0.0068 |
| 1000 | [0.2,0.4) | 203,066 | 0.0213 | 0.0104 | 0.0109 | 0.0043 | 0.0059 |
| 1000 | [0.4,0.6) | 137,827 | 0.0233 | 0.0109 | 0.0120 | 0.0052 | 0.0066 |
| 1000 | [0.6,0.8) | 98,003 | 0.0306 | 0.0135 | 0.0161 | 0.0071 | 0.0090 |
| 1000 | [0.8,1.0] | 84,877 | 0.0274 | 0.0140 | 0.0167 | 0.0101 | 0.0117 |

### 3b. Oracle upper bound by price band (all valid states)

| horizon ms | price band | obs | oracle gross | trade fraction | oracle net structural_floor | oracle net accessible_fixed | oracle net accessible_tiered |
|---|---|---|---|---|---|---|---|
| 100 | 100-200 | 338,060 | 0.0023 | 0.0017 | 0.0011 | 0.0006 | 0.0008 |
| 100 | 200+ | 200,140 | 0.0018 | 0.0013 | 0.0013 | 0.0011 | 0.0012 |
| 100 | 25-50 | 317,006 | 0.0017 | 0.0005 | 0.0009 | 0.0003 | 0.0004 |
| 100 | 5-25 | 117,000 | 0.0021 | 0.0002 | 0.0010 | 0.0001 | 0.0003 |
| 100 | 50-100 | 455,194 | 0.0014 | 0.0007 | 0.0006 | 0.0001 | 0.0002 |
| 250 | 100-200 | 338,060 | 0.0059 | 0.0042 | 0.0030 | 0.0017 | 0.0021 |
| 250 | 200+ | 200,140 | 0.0041 | 0.0034 | 0.0027 | 0.0022 | 0.0023 |
| 250 | 25-50 | 317,006 | 0.0047 | 0.0014 | 0.0024 | 0.0006 | 0.0010 |
| 250 | 5-25 | 117,000 | 0.0060 | 0.0007 | 0.0025 | 0.0002 | 0.0005 |
| 250 | 50-100 | 455,194 | 0.0036 | 0.0017 | 0.0017 | 0.0005 | 0.0008 |
| 500 | 100-200 | 338,060 | 0.0131 | 0.0089 | 0.0072 | 0.0043 | 0.0051 |
| 500 | 200+ | 200,140 | 0.0101 | 0.0075 | 0.0069 | 0.0058 | 0.0059 |
| 500 | 25-50 | 317,006 | 0.0102 | 0.0029 | 0.0051 | 0.0013 | 0.0022 |
| 500 | 5-25 | 117,000 | 0.0140 | 0.0017 | 0.0059 | 0.0004 | 0.0011 |
| 500 | 50-100 | 455,194 | 0.0075 | 0.0036 | 0.0035 | 0.0010 | 0.0016 |
| 1000 | 100-200 | 338,060 | 0.0306 | 0.0194 | 0.0177 | 0.0108 | 0.0127 |
| 1000 | 200+ | 200,140 | 0.0218 | 0.0162 | 0.0149 | 0.0124 | 0.0127 |
| 1000 | 25-50 | 317,006 | 0.0253 | 0.0068 | 0.0134 | 0.0041 | 0.0064 |
| 1000 | 5-25 | 117,000 | 0.0302 | 0.0035 | 0.0135 | 0.0011 | 0.0031 |
| 1000 | 50-100 | 455,194 | 0.0175 | 0.0083 | 0.0080 | 0.0021 | 0.0035 |

## 4. QIMB-constrained upper bound (request §4)

**QIMB_CONSTRAINED_BOUND keeps the side dictated by queue imbalance (the sign that defines the bin) and adds clairvoyant abstention only: max(0, net_side). No new threshold, no side choice and no model enters this bound.**

| horizon ms | imbalance bin | obs | net structural_floor | bound structural_floor | gap | bound accessible_fixed | bound accessible_tiered | P(bound>0) structural_floor |
|---|---|---|---|---|---|---|---|---|
| 100 | [-0.2,0.0) | 158,398 | -4.9479 | 0.0002 | 4.9482 | 0.0001 | 0.0001 | 0.0003 |
| 100 | [-0.4,-0.2) | 189,759 | -4.8561 | 0.0004 | 4.8565 | 0.0001 | 0.0002 | 0.0005 |
| 100 | [-0.6,-0.4) | 129,214 | -4.7501 | 0.0008 | 4.7510 | 0.0005 | 0.0006 | 0.0005 |
| 100 | [-0.8,-0.6) | 92,542 | -4.6952 | 0.0007 | 4.6959 | 0.0003 | 0.0004 | 0.0005 |
| 100 | [-1.0,-0.8) | 79,725 | -4.4438 | 0.0012 | 4.4450 | 0.0010 | 0.0010 | 0.0006 |
| 100 | [0.0,0.2) | 167,020 | -4.9469 | 0.0003 | 4.9472 | 0.0000 | 0.0001 | 0.0003 |
| 100 | [0.2,0.4) | 203,066 | -4.8541 | 0.0003 | 4.8544 | 0.0000 | 0.0001 | 0.0004 |
| 100 | [0.4,0.6) | 137,827 | -4.7502 | 0.0003 | 4.7505 | 0.0000 | 0.0001 | 0.0005 |
| 100 | [0.6,0.8) | 98,003 | -4.7408 | 0.0010 | 4.7418 | 0.0004 | 0.0006 | 0.0006 |
| 100 | [0.8,1.0] | 84,877 | -4.6443 | 0.0005 | 4.6448 | 0.0003 | 0.0003 | 0.0005 |
| 250 | [-0.2,0.0) | 158,398 | -4.9413 | 0.0010 | 4.9423 | 0.0004 | 0.0006 | 0.0008 |
| 250 | [-0.4,-0.2) | 189,759 | -4.8458 | 0.0012 | 4.8471 | 0.0005 | 0.0007 | 0.0012 |
| 250 | [-0.6,-0.4) | 129,214 | -4.7296 | 0.0017 | 4.7314 | 0.0007 | 0.0009 | 0.0012 |
| 250 | [-0.8,-0.6) | 92,542 | -4.6667 | 0.0020 | 4.6687 | 0.0010 | 0.0012 | 0.0017 |
| 250 | [-1.0,-0.8) | 79,725 | -4.4201 | 0.0031 | 4.4232 | 0.0024 | 0.0025 | 0.0016 |
| 250 | [0.0,0.2) | 167,020 | -4.9385 | 0.0008 | 4.9393 | 0.0002 | 0.0003 | 0.0007 |
| 250 | [0.2,0.4) | 203,066 | -4.8402 | 0.0009 | 4.8410 | 0.0002 | 0.0003 | 0.0010 |
| 250 | [0.4,0.6) | 137,827 | -4.7299 | 0.0008 | 4.7307 | 0.0001 | 0.0002 | 0.0011 |
| 250 | [0.6,0.8) | 98,003 | -4.7089 | 0.0025 | 4.7113 | 0.0012 | 0.0014 | 0.0015 |
| 250 | [0.8,1.0] | 84,877 | -4.6199 | 0.0014 | 4.6213 | 0.0008 | 0.0009 | 0.0012 |
| 500 | [-0.2,0.0) | 158,398 | -4.9360 | 0.0022 | 4.9383 | 0.0010 | 0.0012 | 0.0019 |
| 500 | [-0.4,-0.2) | 189,759 | -4.8331 | 0.0025 | 4.8357 | 0.0011 | 0.0014 | 0.0024 |
| 500 | [-0.6,-0.4) | 129,214 | -4.6958 | 0.0040 | 4.6997 | 0.0017 | 0.0022 | 0.0028 |
| 500 | [-0.8,-0.6) | 92,542 | -4.6256 | 0.0050 | 4.6307 | 0.0025 | 0.0031 | 0.0035 |
| 500 | [-1.0,-0.8) | 79,725 | -4.3895 | 0.0059 | 4.3954 | 0.0042 | 0.0046 | 0.0029 |
| 500 | [0.0,0.2) | 167,020 | -4.9309 | 0.0017 | 4.9326 | 0.0005 | 0.0007 | 0.0017 |
| 500 | [0.2,0.4) | 203,066 | -4.8245 | 0.0021 | 4.8266 | 0.0006 | 0.0009 | 0.0021 |
| 500 | [0.4,0.6) | 137,827 | -4.7046 | 0.0023 | 4.7069 | 0.0004 | 0.0008 | 0.0024 |
| 500 | [0.6,0.8) | 98,003 | -4.6723 | 0.0046 | 4.6768 | 0.0020 | 0.0024 | 0.0030 |
| 500 | [0.8,1.0] | 84,877 | -4.5887 | 0.0031 | 4.5919 | 0.0015 | 0.0018 | 0.0026 |
| 1000 | [-0.2,0.0) | 158,398 | -4.9220 | 0.0054 | 4.9274 | 0.0024 | 0.0030 | 0.0045 |
| 1000 | [-0.4,-0.2) | 189,759 | -4.8080 | 0.0066 | 4.8146 | 0.0029 | 0.0037 | 0.0055 |
| 1000 | [-0.6,-0.4) | 129,214 | -4.6537 | 0.0083 | 4.6619 | 0.0032 | 0.0045 | 0.0061 |
| 1000 | [-0.8,-0.6) | 92,542 | -4.5618 | 0.0113 | 4.5731 | 0.0058 | 0.0071 | 0.0073 |
| 1000 | [-1.0,-0.8) | 79,725 | -4.3327 | 0.0140 | 4.3466 | 0.0096 | 0.0106 | 0.0069 |
| 1000 | [0.0,0.2) | 167,020 | -4.9206 | 0.0039 | 4.9246 | 0.0012 | 0.0017 | 0.0038 |
| 1000 | [0.2,0.4) | 203,066 | -4.7967 | 0.0055 | 4.8021 | 0.0017 | 0.0026 | 0.0049 |
| 1000 | [0.4,0.6) | 137,827 | -4.6609 | 0.0063 | 4.6672 | 0.0022 | 0.0030 | 0.0054 |
| 1000 | [0.6,0.8) | 98,003 | -4.6078 | 0.0086 | 4.6164 | 0.0028 | 0.0039 | 0.0068 |
| 1000 | [0.8,1.0] | 84,877 | -4.5425 | 0.0078 | 4.5503 | 0.0040 | 0.0048 | 0.0060 |

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
| 100 | 0.0143 | 1.6852 | 1.6839 | 3.3691 | 1.4445 | 2.5540 | 1.4817 | -4.7994 | -7.3534 | -6.2811 |
| 250 | 0.0304 | 1.6852 | 1.6833 | 3.3686 | 1.4445 | 2.5540 | 1.4817 | -4.7827 | -7.3366 | -6.2644 |
| 500 | 0.0511 | 1.6852 | 1.6831 | 3.3683 | 1.4445 | 2.5540 | 1.4817 | -4.7618 | -7.3157 | -6.2434 |
| 1000 | 0.0846 | 1.6852 | 1.6819 | 3.3671 | 1.4445 | 2.5540 | 1.4817 | -4.7271 | -7.2810 | -6.2087 |

### 5a. Mechanism, computed from the decomposition

| horizon ms | signal (signed mid move) | full spread paid | mandatory fee (structural_floor) | required move | spread share of required | fee share of required | signal coverage | net structural_floor |
|---|---|---|---|---|---|---|---|---|
| 100 | 0.0143 | 3.3691 | 1.4445 | 4.8137 | 70.0% | 30.0% | 0.30% | -4.7994 |
| 250 | 0.0304 | 3.3686 | 1.4445 | 4.8131 | 70.0% | 30.0% | 0.63% | -4.7827 |
| 500 | 0.0511 | 3.3683 | 1.4445 | 4.8129 | 70.0% | 30.0% | 1.06% | -4.7618 |
| 1000 | 0.0846 | 3.3671 | 1.4445 | 4.8117 | 70.0% | 30.0% | 1.76% | -4.7271 |

The same decomposition expressed as what the signal would have to become: at 1000 ms the spread alone requires a mid move 39.8x larger than the realised one, and the mandatory floor fee alone requires 17.1x. Both multiples are measured, not projected: they are the ratio of a cost component to the realised edge at the same horizon.

| flag | holds | rule |
|---|---|---|
| SPREAD_DOMINATES | TRUE | the mean full spread paid is more than half of the required move at the longest declared horizon |
| FEES_DOMINATE | FALSE | the mean floor fee is more than half of the required move at the longest declared horizon |
| SIGNAL_MAGNITUDE_TOO_SMALL | TRUE | the side-signed mid move covers less than 10% of the required move at every declared horizon |
| WRONG_HORIZON | FALSE | extending the horizon across the whole declared grid (100 ms to 1000 ms, a factor of ten) closes at least half of the remaining gap |
| POOLED_LOW_QUALITY_STATES | TRUE | the dispersion of the net result across the declared (bin x horizon) states is less than half of its mean, i.e. the states barely separate |

Horizon increments of `net structural_floor` across the declared grid: 0.0167, 0.0209, 0.0347 bps, i.e. a ten-fold extension of the horizon closes 1.5% of the remaining gap (the required move itself is horizon-invariant: 4.8137 bps at 100 ms against 4.8117 bps at 1000 ms). Cross-state dispersion of the net result over the 40 (bin x horizon) states is 0.6153 bps, 13.0% of the mean, so the declared states barely separate. Holding flags: SPREAD_DOMINATES, SIGNAL_MAGNITUDE_TOO_SMALL, POOLED_LOW_QUALITY_STATES.

## 6. Answers (request §6)

**1. Is there any development-sample state in the predeclared state space where aggressive execution approaches or exceeds the structural hurdle?**

No. 0 of the 400 declared cells (10 imbalance bins × 2 spread classes × 5 price bands × 4 horizons) have a positive structural-cost-adjusted result, and 0 of the 40 cells of the aggregated (bin × horizon) view do. The best cell in the whole declared space is `[-1.0,-0.8) · ONE_TICK · $200+ · 250 ms` — -0.9526 bps net, i.e. still losing — with a hurdle coverage of 0.097 (mean side-signed mid move 0.1023 bps against a 1.0548 bps required move) on 1,002 observations.

Cells at each declared hurdle-coverage cut — the full 400-cell grid first, then the (bin × horizon) view: ≥1.0×: 0, ≥0.9×: 0, ≥0.75×: 0, ≥0.5×: 0 (full grid); ≥1.0×: 0, ≥0.9×: 0, ≥0.75×: 0, ≥0.5×: 0 (bin × horizon). These cuts are descriptive buckets, not selection rules: no state is promoted and none is killed, and the best cell is named only because the question asks where the maximum lies.

**2. What fraction of opportunities does that state represent?**

For the best aggregated state (`[-1.0,-0.8)` at 1000 ms): 5.948% of the signal-defined observations (79,725 of 1,340,431). For the best individual cell (`[-1.0,-0.8) · ONE_TICK · $200+ · 250 ms`): 0.0748% (1,002 observations, 30 symbol-block cells, block-bootstrap SE 0.0661 bps). Both fractions are reported so that a reader can see how little of the opportunity set a favourable cell addresses even if it were real.

**3. Does a clairvoyant aggressive trader have meaningful room after costs?**

No. At the longest declared horizon (1000 ms), perfect side selection earns 0.0129 bps per observation after the structural floor and 0.0060 bps after accessible_fixed, 0.0076 bps after accessible_tiered, on 1,340,431 observations; it beats abstaining on 1.13% of them before costs and on 0.95% after the structural floor. That bound is 0.27% of the 4.8117 bps required move at the same horizon: the entire value of perfect foresight is about 0.013 bps per decision, three orders of magnitude below what the execution formulation needs. No predictive model can close that, and this is the strongest statement this calculation supports — it does not depend on any model, only on the realised future quotes.

**4. Which component creates the dominant economic gap?**

The gap is `required move - realised move` = 4.8117 - (0.0846) bps, decomposed exactly in §5: **the full spread paid contributes 70.0%** of the required move, **the mandatory venue/regulatory fee 30.0%**, and the signal supplies 1.76%. The broker reference layer on top of the floor is an additional 2.5540 bps (accessible_fixed), 1.4817 bps (accessible_tiered). Flags holding, with their rules in §5a: SPREAD_DOMINATES, SIGNAL_MAGNITUDE_TOO_SMALL, POOLED_LOW_QUALITY_STATES.

Reading: the dominant component is the **spread** (70.0% of the hurdle), the fee is second, and the signal is not a large contributor to the gap because it is negligible in absolute terms — it would need to be 39.8x larger merely to pay the spread. That is a combination, and the decomposition is the evidence for it; nothing here is inferred from the shape of the results alone.

## 7. Reconciliation and limitations

| check | observations | mismatches / max abs difference / ratio | tolerance | outcome |
|---|---|---|---|---|
| execution_instant_is_decision_instant | 1,427,400 | 0 | 0 | PASS |
| frozen_execution_markout_reproduced_exactly | 5,361,724 | 0.0000 | 1e-06 | PASS |
| frozen_cross_to_cross_is_half_of_true_bps | 5,361,724 | ratio 2.000000 (expected 2.0000) | 1e-09 | PASS |
| frozen_cost_column_is_ledger_at_half_price | 5,361,724 | 0.0000 | 1e-09 | PASS |
| frozen_execution_adjusted_is_its_own_markout_minus_its_own_cost | 5,361,724 | 0.0000 | 1e-09 | PASS |
| decomposition_identity_pooled | 5,361,724 | 0.0000 | 1e-09 | PASS |
| spread_hurdle_is_cross_to_cross_breakeven | 5,361,724 | 0.0000 | 1e-09 | PASS |
| oracle_bound_dominates_and_is_non_negative | 17,128,800 | 0 | 1e-09 | PASS |
| qimb_bound_below_oracle_bound | 16,085,172 | 0 | 1e-09 | PASS |
| state_partition_covers_every_observation | 1,340,431 | 1,340,431 in cells | 0 | PASS |
| fee_lookup_matches_ledger_at_observation_prices | 1,503 | 0.0000 | 1e-09 | PASS |
| tick_and_half_spread_arithmetic | 1,427,400 | 0 | 1e-09 | PASS |

### 7a. Discrepancies found in the frozen M2-0 execution table — reported, not repaired

The frozen table could not be reproduced in two of its columns, and the difference is not a tolerance: it is exact. Both defects are in `M2/src/calculate.py::execution_rows`, they are reproduced here bit for bit by recomputing M2-0's own expressions (`frozen_cross_to_cross_is_half_of_true_bps`, `frozen_cost_column_is_ledger_at_half_price`), and **no frozen artifact was modified, regenerated or overwritten by this pass**.

| id | expression in the frozen artifact | correct expression | effect | verified by |
|---|---|---|---|---|
| M2-0-D1 | `10000 * (fut_bid - entry_ask) / arrival_mid2  with arrival_mid2 = entry_bid + entry_ask` | `10000 * (fut_bid - entry_ask) / mid, mid = (entry_bid + entry_ask) / 2  =>  2 * the frozen value` | the frozen cross-to-cross column is half the true basis-point value | frozen_cross_to_cross_is_half_of_true_bps |
| M2-0-D2 | `entry_price = where(side>0, entry_ask, entry_bid) / 2.0 / 10000.0` | `entry_price_usd = raw_price / 10000.0 (Price(4) scale); the frozen expression halves every price` | the fee is evaluated at half the true price, so mean_known_cost_bps is overstated (2.6831 bps instead of 1.4445 bps on this sample) | frozen_cost_column_is_ledger_at_half_price |
| M2-0-D3 | `mean_cost_adjusted_bps = mean_gross_markout_bps - mean_known_cost_bps` | `net = cross_to_cross - fee = -3.3548 - 1.4445 = -4.7994 bps at 100 ms (the frozen -4.3540 bps mixes the correct markout with an inflated fee and is not a cross-to-cross result)` | the frozen cost-adjusted column is not the cross-to-cross net; both defects push the reported figure in the same (more favourable) direction | decomposition_identity_pooled and this pass's pooled table |

Affected artifacts: M2/output/M2_0_STATUS.md (the cross-to-cross column of the idealized execution table: -1.6774 / -1.6691 / -1.6586 / -1.6413 bps, each half the true value); M2/output/M2_0_STATUS.md (the idealized-execution paragraph, which is the only place these two columns are quoted); M2/output/M2_0_STATUS.md (the known cost 2.6831 bps and the cost-adjusted column: -4.3540 / -4.3379 / -4.3172 / -4.2837 bps); M2/output/calculations/ev_delay_descriptive.csv::mean_cross_to_cross_bps; M2/output/calculations/ev_delay_descriptive.csv::mean_known_cost_bps and the three columns derived from it; M2/output/calculations/idealized_execution_summary.csv::mean_cost_adjusted_bps; M2/output/calculations/idealized_execution_summary.csv::mean_cross_to_cross_bps; M2/output/calculations/idealized_execution_summary.csv::mean_known_cost_bps; M2/output/calculations/idealized_execution_summary.csv::median_cost_adjusted_bps; M2/output/calculations/idealized_execution_summary.csv::prob_adjusted_positive.

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
