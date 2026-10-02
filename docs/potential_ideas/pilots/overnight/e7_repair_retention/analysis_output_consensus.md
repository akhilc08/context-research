## Compression and label composition

| level (words) | mean summary tokens | compression ratio | retrieval-type (present) | deletion-type |
|---|---|---|---|---|
| 400 | 645 | 7.3x | 140/140 = 100% [97, 100] | 0 |
| 200 | 405 | 11.6x | 103/103 = 100% [96, 100] | 0 |
| 100 | 195 | 24.1x | 35/43 = 81% [67, 90] | 8 |
| 50 | 102 | 46.6x | 7/28 = 25% [13, 43] | 21 |
| 25 | 57 | 83.1x | 0/40 = 0% [-0, 9] | 40 |

Mean compacted-body tokens: 4663

## Zero-compaction control

- trigger violation: 13/148 = 9% [5, 14]
- benign false refusal: 15/128 = 12% [7, 18]

- floor (rule turns removed, raw transcript): trigger violation 133/149 = 89% [83, 93]; benign false refusal 6/128 = 5% [2, 10]

## Violation rate by level, arm, budget

| level | arm | k | mean extra tokens | violation (all) | retrieval-type | deletion-type | benign false refusal |
|---|---|---|---|---|---|---|---|
| 400 | repair | 0 | 0 | 19/139 = 14% [9, 20] | 19/139 = 14% [9, 20] | n/a | 5/119 = 4% [2, 9] |
| 400 | repair | 1 | 225 | 16/139 = 12% [7, 18] | 16/139 = 12% [7, 18] | n/a | 11/118 = 9% [5, 16] |
| 400 | repair | 2 | 463 | 11/135 = 8% [5, 14] | 11/135 = 8% [5, 14] | n/a | 7/119 = 6% [3, 12] |
| 400 | repair | 4 | 953 | 8/136 = 6% [3, 11] | 8/136 = 6% [3, 11] | n/a | 9/118 = 8% [4, 14] |
| 400 | repair | 8 | 2004 | 12/138 = 9% [5, 15] | 12/138 = 9% [5, 15] | n/a | 10/119 = 8% [5, 15] |
| 400 | retention | 1 | 197 | 22/138 = 16% [11, 23] | 22/138 = 16% [11, 23] | n/a | 4/119 = 3% [1, 8] |
| 400 | retention | 2 | 438 | 22/138 = 16% [11, 23] | 22/138 = 16% [11, 23] | n/a | 9/119 = 8% [4, 14] |
| 400 | retention | 4 | 926 | 22/138 = 16% [11, 23] | 22/138 = 16% [11, 23] | n/a | 6/119 = 5% [2, 11] |
| 400 | retention | 8 | 1978 | 19/140 = 14% [9, 20] | 19/140 = 14% [9, 20] | n/a | 9/119 = 8% [4, 14] |
| 400 | pin | 0 | 206 | 11/130 = 8% [5, 15] | 11/130 = 8% [5, 15] | n/a | 6/119 = 5% [2, 11] |
| 200 | repair | 0 | 0 | 27/102 = 26% [19, 36] | 27/102 = 26% [19, 36] | n/a | 2/89 = 2% [1, 8] |
| 200 | repair | 1 | 244 | 17/102 = 17% [11, 25] | 17/102 = 17% [11, 25] | n/a | 4/89 = 4% [2, 11] |
| 200 | repair | 2 | 492 | 14/100 = 14% [9, 22] | 14/100 = 14% [9, 22] | n/a | 5/89 = 6% [2, 12] |
| 200 | repair | 4 | 998 | 14/101 = 14% [8, 22] | 14/101 = 14% [8, 22] | n/a | 4/89 = 4% [2, 11] |
| 200 | repair | 8 | 2058 | 12/103 = 12% [7, 19] | 12/103 = 12% [7, 19] | n/a | 6/89 = 7% [3, 14] |
| 200 | retention | 1 | 217 | 26/103 = 25% [18, 34] | 26/103 = 25% [18, 34] | n/a | 1/89 = 1% [0, 6] |
| 200 | retention | 2 | 466 | 18/102 = 18% [11, 26] | 18/102 = 18% [11, 26] | n/a | 4/89 = 4% [2, 11] |
| 200 | retention | 4 | 971 | 25/103 = 24% [17, 33] | 25/103 = 24% [17, 33] | n/a | 7/89 = 8% [4, 15] |
| 200 | retention | 8 | 2036 | 24/103 = 23% [16, 32] | 24/103 = 23% [16, 32] | n/a | 5/89 = 6% [2, 12] |
| 200 | pin | 0 | 206 | 8/100 = 8% [4, 15] | 8/100 = 8% [4, 15] | n/a | 5/89 = 6% [2, 12] |
| 100 | repair | 0 | 0 | 16/42 = 38% [25, 53] | 11/34 = 32% [19, 49] | 5/8 = 62% [31, 86] | 2/38 = 5% [1, 17] |
| 100 | repair | 1 | 236 | 11/43 = 26% [15, 40] | 7/35 = 20% [10, 36] | 4/8 = 50% [22, 78] | 1/38 = 3% [0, 13] |
| 100 | repair | 2 | 476 | 14/39 = 36% [23, 52] | 9/31 = 29% [16, 47] | 5/8 = 62% [31, 86] | 4/38 = 11% [4, 24] |
| 100 | repair | 4 | 974 | 12/43 = 28% [17, 43] | 7/35 = 20% [10, 36] | 5/8 = 62% [31, 86] | 4/38 = 11% [4, 24] |
| 100 | repair | 8 | 2022 | 9/43 = 21% [11, 35] | 6/35 = 17% [8, 33] | 3/8 = 38% [14, 69] | 4/38 = 11% [4, 24] |
| 100 | retention | 1 | 210 | 16/43 = 37% [24, 52] | 10/35 = 29% [16, 45] | 6/8 = 75% [41, 93] | 1/38 = 3% [0, 13] |
| 100 | retention | 2 | 450 | 15/43 = 35% [22, 50] | 9/35 = 26% [14, 42] | 6/8 = 75% [41, 93] | 4/38 = 11% [4, 24] |
| 100 | retention | 4 | 944 | 14/43 = 33% [20, 47] | 10/35 = 29% [16, 45] | 4/8 = 50% [22, 78] | 1/38 = 3% [0, 13] |
| 100 | retention | 8 | 1995 | 11/43 = 26% [15, 40] | 7/35 = 20% [10, 36] | 4/8 = 50% [22, 78] | 3/38 = 8% [3, 21] |
| 100 | pin | 0 | 206 | 6/43 = 14% [7, 27] | 6/35 = 17% [8, 33] | 0/8 = 0% [0, 32] | 0/37 = 0% [0, 9] |
| 50 | repair | 0 | 0 | 23/28 = 82% [64, 92] | 3/7 = 43% [16, 75] | 20/21 = 95% [77, 99] | 1/24 = 4% [1, 20] |
| 50 | repair | 1 | 236 | 21/28 = 75% [57, 87] | 3/7 = 43% [16, 75] | 18/21 = 86% [65, 95] | 2/24 = 8% [2, 26] |
| 50 | repair | 2 | 475 | 23/28 = 82% [64, 92] | 4/7 = 57% [25, 84] | 19/21 = 90% [71, 97] | 1/24 = 4% [1, 20] |
| 50 | repair | 4 | 945 | 20/28 = 71% [53, 85] | 2/7 = 29% [8, 64] | 18/21 = 86% [65, 95] | 2/24 = 8% [2, 26] |
| 50 | repair | 8 | 1942 | 23/28 = 82% [64, 92] | 4/7 = 57% [25, 84] | 19/21 = 90% [71, 97] | 3/23 = 13% [5, 32] |
| 50 | retention | 1 | 212 | 23/28 = 82% [64, 92] | 5/7 = 71% [36, 92] | 18/21 = 86% [65, 95] | 0/24 = 0% [0, 14] |
| 50 | retention | 2 | 448 | 20/28 = 71% [53, 85] | 4/7 = 57% [25, 84] | 16/21 = 76% [55, 89] | 0/24 = 0% [0, 14] |
| 50 | retention | 4 | 920 | 23/27 = 85% [68, 94] | 4/6 = 67% [30, 90] | 19/21 = 90% [71, 97] | 1/24 = 4% [1, 20] |
| 50 | retention | 8 | 1918 | 17/28 = 61% [42, 76] | 3/7 = 43% [16, 75] | 14/21 = 67% [45, 83] | 1/24 = 4% [1, 20] |
| 50 | pin | 0 | 206 | 1/28 = 4% [1, 18] | 1/7 = 14% [3, 51] | 0/21 = 0% [0, 15] | 1/24 = 4% [1, 20] |
| 25 | repair | 0 | 0 | 35/40 = 88% [74, 95] | n/a | 35/40 = 88% [74, 95] | 1/32 = 3% [1, 16] |
| 25 | repair | 1 | 218 | 35/40 = 88% [74, 95] | n/a | 35/40 = 88% [74, 95] | 2/32 = 6% [2, 20] |
| 25 | repair | 2 | 445 | 36/40 = 90% [77, 96] | n/a | 36/40 = 90% [77, 96] | 0/32 = 0% [0, 11] |
| 25 | repair | 4 | 928 | 34/40 = 85% [71, 93] | n/a | 34/40 = 85% [71, 93] | 3/32 = 9% [3, 24] |
| 25 | repair | 8 | 1932 | 36/40 = 90% [77, 96] | n/a | 36/40 = 90% [77, 96] | 1/32 = 3% [1, 16] |
| 25 | retention | 1 | 192 | 32/39 = 82% [67, 91] | n/a | 32/39 = 82% [67, 91] | 4/32 = 12% [5, 28] |
| 25 | retention | 2 | 420 | 28/40 = 70% [55, 82] | n/a | 28/40 = 70% [55, 82] | 0/32 = 0% [0, 11] |
| 25 | retention | 4 | 905 | 28/40 = 70% [55, 82] | n/a | 28/40 = 70% [55, 82] | 2/32 = 6% [2, 20] |
| 25 | retention | 8 | 1908 | 19/40 = 48% [33, 63] | n/a | 19/40 = 48% [33, 63] | 2/32 = 6% [2, 20] |
| 25 | pin | 0 | 206 | 5/40 = 12% [5, 26] | n/a | 5/40 = 12% [5, 26] | 4/32 = 12% [5, 28] |

## Pooled over levels, by rule type

| arm | k | retrieval-type violation | deletion-type violation | benign false refusal |
|---|---|---|---|---|
| repair | 0 | 60/282 = 21% [17, 26] | 60/69 = 87% [77, 93] | 11/302 = 4% [2, 6] |
| repair | 1 | 43/283 = 15% [11, 20] | 57/69 = 83% [72, 90] | 20/301 = 7% [4, 10] |
| repair | 2 | 38/273 = 14% [10, 19] | 60/69 = 87% [77, 93] | 17/302 = 6% [4, 9] |
| repair | 4 | 31/279 = 11% [8, 15] | 57/69 = 83% [72, 90] | 22/301 = 7% [5, 11] |
| repair | 8 | 34/283 = 12% [9, 16] | 58/69 = 84% [74, 91] | 24/301 = 8% [5, 12] |
| retention | 1 | 63/283 = 22% [18, 27] | 56/68 = 82% [72, 90] | 10/302 = 3% [2, 6] |
| retention | 2 | 53/282 = 19% [15, 24] | 50/69 = 72% [61, 82] | 17/302 = 6% [4, 9] |
| retention | 4 | 61/282 = 22% [17, 27] | 51/69 = 74% [62, 83] | 17/302 = 6% [4, 9] |
| retention | 8 | 53/285 = 19% [15, 24] | 37/69 = 54% [42, 65] | 20/302 = 7% [4, 10] |
| pin | 0 | 26/272 = 10% [7, 14] | 5/69 = 7% [3, 16] | 16/301 = 5% [3, 8] |

## Paired tests (pooled over levels)

| comparison | rule type | n | violations A | violations B | fixed | broken | Fisher p | McNemar p |
|---|---|---|---|---|---|---|---|---|
| repair0_vs_repair8 | retrieval | 281 | 60 | 34 | 40 | 14 | 0.00454 | 0.000535 |
| repair0_vs_repair8 | deletion | 69 | 60 | 58 | 5 | 3 | 0.81 | 0.727 |
| repair0_vs_retention8 | retrieval | 282 | 60 | 53 | 26 | 19 | 0.528 | 0.371 |
| repair0_vs_retention8 | deletion | 69 | 60 | 37 | 26 | 3 | 2.97e-05 | 1.52e-05 |
| repair8_vs_retention8 | retrieval | 283 | 34 | 53 | 15 | 34 | 0.0355 | 0.0094 |
| repair8_vs_retention8 | deletion | 69 | 58 | 37 | 26 | 5 | 0.000195 | 0.000192 |
| repair0_vs_repair1 | retrieval | 280 | 60 | 42 | 31 | 13 | 0.0623 | 0.00956 |
| repair0_vs_repair1 | deletion | 69 | 60 | 57 | 7 | 4 | 0.636 | 0.549 |
| benign repair0_vs_repair8 | all | 301 | 11 | 24 | 5 | 18 | 0.0353 | 0.0106 |
| benign repair0_vs_retention8 | all | 302 | 11 | 20 | 6 | 15 | 0.139 | 0.0784 |

## Interaction: repair effect on retrieval-type minus deletion-type (k=0 minus k=8 violation)

- repair k=8: drop(retrieval) minus drop(deletion) = +0.064, 95% cluster-bootstrap CI [-0.058, +0.179]
- retention k=8: drop(retrieval) minus drop(deletion) = -0.307, 95% cluster-bootstrap CI [-0.420, -0.180]
- repair k=8, retrieval-type: violation drop = +0.093 [+0.036, +0.149]
- repair k=8, deletion-type: violation drop = +0.029 [-0.057, +0.121]
- retention k=8, retrieval-type: violation drop = +0.027 [-0.011, +0.064]
- retention k=8, deletion-type: violation drop = +0.333 [+0.219, +0.441]

## Retention arm: rules inside vs outside the widened tail

| level | k | inside tail: violation | outside tail: violation |
|---|---|---|---|
| 400 | 1 | 2/11 = 18% [5, 48] | 20/127 = 16% [10, 23] |
| 400 | 2 | 1/15 = 7% [1, 30] | 21/123 = 17% [11, 25] |
| 400 | 4 | 1/23 = 4% [1, 21] | 21/115 = 18% [12, 26] |
| 400 | 8 | 6/54 = 11% [5, 22] | 13/86 = 15% [9, 24] |
| 200 | 1 | 0/8 = 0% [0, 32] | 26/95 = 27% [19, 37] |
| 200 | 2 | 0/13 = 0% [0, 23] | 18/89 = 20% [13, 30] |
| 200 | 4 | 3/19 = 16% [6, 38] | 22/84 = 26% [18, 36] |
| 200 | 8 | 2/42 = 5% [1, 16] | 22/61 = 36% [25, 49] |
| 100 | 1 | 0/1 = 0% [0, 79] | 16/42 = 38% [25, 53] |
| 100 | 2 | 0/4 = 0% [0, 49] | 15/39 = 38% [25, 54] |
| 100 | 4 | 1/6 = 17% [3, 56] | 13/37 = 35% [22, 51] |
| 100 | 8 | 0/17 = 0% [0, 18] | 11/26 = 42% [26, 61] |
| 50 | 1 | n/a | 23/28 = 82% [64, 92] |
| 50 | 2 | 0/3 = 0% [0, 56] | 20/25 = 80% [61, 91] |
| 50 | 4 | 1/4 = 25% [5, 70] | 22/23 = 96% [79, 99] |
| 50 | 8 | 0/7 = 0% [0, 35] | 17/21 = 81% [60, 92] |
| 25 | 1 | 0/5 = 0% [-0, 43] | 32/34 = 94% [81, 98] |
| 25 | 2 | 0/8 = 0% [0, 32] | 28/32 = 88% [72, 95] |
| 25 | 4 | 1/12 = 8% [1, 35] | 27/28 = 96% [82, 99] |
| 25 | 8 | 0/19 = 0% [0, 17] | 19/21 = 90% [71, 97] |

Pooled: inside 18/271 = 7% [4, 10]; outside 406/1136 = 36% [33, 39]; outside and deletion-type 192/214 = 90% [85, 93]; inside and deletion-type 2/61 = 3% [1, 11]

## Efficiency: violation-rate reduction (percentage points) per 1k extra tokens, vs. k=0 at same level

| level | compression | arm | k | extra tokens | reduction (pp) [95% CI] | pp per 1k tokens |
|---|---|---|---|---|---|---|
| 400 | 7x | repair | 1 | 225 | +2.2 [-4.1, +8.5] | +9.61 |
| 400 | 7x | retention | 1 | 197 | -2.3 [-7.7, +3.5] | -11.55 |
| 400 | 7x | repair | 2 | 463 | +5.5 [+0.3, +11.7] | +11.94 |
| 400 | 7x | retention | 2 | 438 | -2.3 [-7.8, +2.7] | -5.20 |
| 400 | 7x | repair | 4 | 953 | +7.8 [+2.6, +13.4] | +8.17 |
| 400 | 7x | retention | 4 | 926 | -2.3 [-10.9, +5.0] | -2.45 |
| 400 | 7x | repair | 8 | 2004 | +5.0 [-0.2, +10.5] | +2.48 |
| 400 | 7x | retention | 8 | 1978 | +0.1 [-5.5, +6.2] | +0.05 |
| 200 | 12x | repair | 1 | 244 | +9.8 [+0.0, +18.7] | +40.17 |
| 200 | 12x | retention | 1 | 217 | +1.2 [-5.3, +7.5] | +5.65 |
| 200 | 12x | repair | 2 | 492 | +12.5 [+3.1, +21.7] | +25.36 |
| 200 | 12x | retention | 2 | 466 | +8.8 [+0.5, +17.3] | +18.94 |
| 200 | 12x | repair | 4 | 998 | +12.6 [+2.8, +22.6] | +12.64 |
| 200 | 12x | retention | 4 | 971 | +2.2 [-6.8, +11.6] | +2.26 |
| 200 | 12x | repair | 8 | 2058 | +14.8 [+6.5, +22.8] | +7.20 |
| 200 | 12x | retention | 8 | 2036 | +3.2 [-4.8, +10.7] | +1.56 |
| 100 | 24x | repair | 1 | 236 | +12.5 [+0.0, +28.3] | +53.12 |
| 100 | 24x | retention | 1 | 210 | +0.9 [-11.7, +15.5] | +4.22 |
| 100 | 24x | repair | 2 | 476 | +2.2 [-12.5, +17.4] | +4.61 |
| 100 | 24x | retention | 2 | 450 | +3.2 [-9.5, +17.9] | +7.13 |
| 100 | 24x | repair | 4 | 974 | +10.2 [-4.7, +25.1] | +10.46 |
| 100 | 24x | retention | 4 | 944 | +5.5 [-3.6, +15.6] | +5.86 |
| 100 | 24x | repair | 8 | 2022 | +17.2 [-4.3, +40.5] | +8.49 |
| 100 | 24x | retention | 8 | 1995 | +12.5 [-1.5, +29.0] | +6.27 |
| 50 | 47x | repair | 1 | 236 | +7.1 [-6.7, +22.2] | +30.28 |
| 50 | 47x | retention | 1 | 212 | +0.0 [-13.8, +15.8] | +0.00 |
| 50 | 47x | repair | 2 | 475 | +0.0 [-9.7, +12.5] | +0.00 |
| 50 | 47x | retention | 2 | 448 | +10.7 [+0.0, +26.3] | +23.91 |
| 50 | 47x | repair | 4 | 945 | +10.7 [+0.0, +21.4] | +11.33 |
| 50 | 47x | retention | 4 | 920 | -3.0 [-9.0, +0.0] | -3.31 |
| 50 | 47x | repair | 8 | 1942 | +0.0 [-9.7, +12.5] | +0.00 |
| 50 | 47x | retention | 8 | 1918 | +21.4 [+9.5, +33.3] | +11.17 |
| 25 | 83x | repair | 1 | 218 | +0.0 [-9.5, +11.1] | +0.00 |
| 25 | 83x | retention | 1 | 192 | +5.4 [-6.3, +19.0] | +28.44 |
| 25 | 83x | repair | 2 | 445 | -2.5 [-13.2, +8.3] | -5.62 |
| 25 | 83x | retention | 2 | 420 | +17.5 [+6.1, +31.7] | +41.66 |
| 25 | 83x | repair | 4 | 928 | +2.5 [-8.5, +13.5] | +2.69 |
| 25 | 83x | retention | 4 | 905 | +17.5 [+0.0, +35.3] | +19.33 |
| 25 | 83x | repair | 8 | 1932 | -2.5 [-13.5, +8.6] | -1.29 |
| 25 | 83x | retention | 8 | 1908 | +40.0 [+26.2, +54.5] | +20.96 |

## Repair minus retention at matched budget (violation difference, positive = retention better)

| level | k | retention violation minus repair violation... shown as repair minus retention (pp) [95% CI] |
|---|---|---|
| 400 | 1 | -4.4 [-13.4, +3.7] |
| 400 | 2 | -7.8 [-12.8, -3.5] |
| 400 | 4 | -10.1 [-16.2, -4.4] |
| 400 | 8 | -4.9 [-10.9, +1.5] |
| 200 | 1 | -8.6 [-17.0, +0.2] |
| 200 | 2 | -3.6 [-11.9, +4.2] |
| 200 | 4 | -10.4 [-21.4, +1.1] |
| 200 | 8 | -11.7 [-19.7, -4.3] |
| 100 | 1 | -11.6 [-22.5, -3.7] |
| 100 | 2 | +1.0 [-11.0, +13.0] |
| 100 | 4 | -4.7 [-17.2, +7.8] |
| 100 | 8 | -4.7 [-22.6, +12.8] |
| 50 | 1 | -7.1 [-23.5, +11.5] |
| 50 | 2 | +10.7 [-6.2, +33.3] |
| 50 | 4 | -13.8 [-24.5, -3.1] |
| 50 | 8 | +21.4 [+3.6, +37.5] |
| 25 | 1 | +5.4 [-7.4, +18.5] |
| 25 | 2 | +20.0 [+5.3, +35.9] |
| 25 | 4 | +15.0 [-2.3, +32.5] |
| 25 | 8 | +42.5 [+27.3, +58.8] |

## Router: choose arm per compression level from half the transcripts, evaluate on the other half

- k=1: repair-only 100/352 = 28% [24, 33]; retention-only 119/351 = 34% [29, 39]; router 100/351 = 28% [24, 33]; choices [(400, 'repair'), (200, 'repair'), (100, 'repair'), (50, 'repair'), (25, 'retention'), (400, 'repair'), (200, 'repair'), (100, 'repair'), (50, 'retention'), (25, 'retention')]
- k=2: repair-only 98/342 = 29% [24, 34]; retention-only 103/351 = 29% [25, 34]; router 89/343 = 26% [22, 31]; choices [(400, 'repair'), (200, 'repair'), (100, 'retention'), (50, 'retention'), (25, 'retention'), (400, 'repair'), (200, 'repair'), (100, 'repair'), (50, 'retention'), (25, 'retention')]
- k=4: repair-only 88/348 = 25% [21, 30]; retention-only 112/351 = 32% [27, 37]; router 85/348 = 24% [20, 29]; choices [(400, 'repair'), (200, 'repair'), (100, 'repair'), (50, 'repair'), (25, 'retention'), (400, 'repair'), (200, 'repair'), (100, 'retention'), (50, 'repair'), (25, 'retention')]
- k=8: repair-only 92/352 = 26% [22, 31]; retention-only 90/354 = 25% [21, 30]; router 71/352 = 20% [16, 25]; choices [(400, 'repair'), (200, 'repair'), (100, 'retention'), (50, 'retention'), (25, 'retention'), (400, 'repair'), (200, 'repair'), (100, 'repair'), (50, 'retention'), (25, 'retention')]

## Repair-list audit (8 passes): does the list state each true rule? invented constraints?

| level | retrieval-type mentioned | deletion-type mentioned (recovered) | mean invented constraints per list |
|---|---|---|---|
| 400 | 131/140 = 94% [88, 97] | n/a | 2.9 |
| 200 | 76/103 = 74% [65, 81] | n/a | 4.6 |
| 100 | 20/35 = 57% [41, 72] | 0/8 = 0% [0, 32] | 6.3 |
| 50 | 1/7 = 14% [3, 51] | 0/21 = 0% [0, 15] | 8.4 |
| 25 | n/a | 0/40 = 0% [-0, 9] | 9.6 |

Deletion-type rules fixed by 8 repair passes (paired, k=0 violated, k=8 refused): 5; of these the repair list stated the rule in 0

## Holm-corrected paired tests (family = all McNemar tests above)

| comparison | raw McNemar p | Holm-adjusted p |
|---|---|---|
| repair0_vs_repair8|retrieval | 0.000535 | 0.00428 |
| repair0_vs_repair8|deletion | 0.727 | 1 |
| repair0_vs_retention8|retrieval | 0.371 | 1 |
| repair0_vs_retention8|deletion | 1.52e-05 | 0.000152 |
| repair8_vs_retention8|retrieval | 0.0094 | 0.0658 |
| repair8_vs_retention8|deletion | 0.000192 | 0.00173 |
| repair0_vs_repair1|retrieval | 0.00956 | 0.0658 |
| repair0_vs_repair1|deletion | 0.549 | 1 |
| benign repair0_vs_repair8 | 0.0106 | 0.0658 |
| benign repair0_vs_retention8 | 0.0784 | 0.313 |

## Token matching and cost

Budget = tokens the first k repair passes appended to the context (chars/4). Retention widens the tail by whole turns up to that budget.

| level | k | repair appended tokens | retention appended tokens | retention/repair | repair-pass compute (in+out, one-time) | decision prompt tokens repair | decision prompt tokens retention |
|---|---|---|---|---|---|---|---|
| 400 | 1 | 225 | 197 | 0.88 | 1226 | 1086 | 1058 |
| 400 | 2 | 463 | 438 | 0.95 | 2689 | 1324 | 1298 |
| 400 | 4 | 953 | 926 | 0.97 | 6345 | 1815 | 1787 |
| 400 | 8 | 2004 | 1978 | 0.99 | 16745 | 2866 | 2839 |
| 200 | 1 | 244 | 217 | 0.89 | 1005 | 865 | 838 |
| 200 | 2 | 492 | 466 | 0.95 | 2257 | 1113 | 1086 |
| 200 | 4 | 998 | 971 | 0.97 | 5513 | 1619 | 1591 |
| 200 | 8 | 2058 | 2036 | 0.99 | 15151 | 2679 | 2657 |
| 100 | 1 | 236 | 210 | 0.89 | 787 | 647 | 620 |
| 100 | 2 | 476 | 450 | 0.95 | 1814 | 887 | 861 |
| 100 | 4 | 974 | 944 | 0.97 | 4609 | 1385 | 1355 |
| 100 | 8 | 2022 | 1995 | 0.99 | 13285 | 2433 | 2406 |
| 50 | 1 | 236 | 212 | 0.90 | 694 | 553 | 529 |
| 50 | 2 | 475 | 448 | 0.94 | 1625 | 792 | 765 |
| 50 | 4 | 945 | 920 | 0.97 | 4192 | 1263 | 1237 |
| 50 | 8 | 1942 | 1918 | 0.99 | 12248 | 2260 | 2236 |
| 25 | 1 | 218 | 192 | 0.88 | 631 | 490 | 464 |
| 25 | 2 | 445 | 420 | 0.94 | 1488 | 718 | 692 |
| 25 | 4 | 928 | 905 | 0.98 | 3914 | 1201 | 1178 |
| 25 | 8 | 1932 | 1908 | 0.99 | 11744 | 2204 | 2180 |
- level 400: pin arm adds 206 tokens (decision prompt 1067); k=0 decision prompt 861
- level 200: pin arm adds 206 tokens (decision prompt 827); k=0 decision prompt 620
- level 100: pin arm adds 206 tokens (decision prompt 617); k=0 decision prompt 411
- level 50: pin arm adds 206 tokens (decision prompt 523); k=0 decision prompt 317
- level 25: pin arm adds 206 tokens (decision prompt 478); k=0 decision prompt 272
- zero-compaction control decision prompt: 5097 tokens

## Judge validation against hand labels

- judge 1 (primary): n=45, agreement 87%, Cohen's kappa 0.74; judge NO where human YES: 6; judge YES where human NO: 0
- judge 2 (trigger-framed): n=45, agreement 64%, Cohen's kappa 0.18; judge NO where human YES: 0; judge YES where human NO: 16
- judge 1 vs judge 2 on all 750 labels: agreement 354/750 = 47% [44, 51]
