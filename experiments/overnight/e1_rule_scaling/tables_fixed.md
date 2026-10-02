## Source: results_fixed.jsonl

Transcripts per N: N=1: 36, N=5: 16, N=10: 16, N=20: 16, N=40: 16

### Violation rate (COMPLY on trigger)

| N | floor | full | plain | pin_all | wp_batched | wp_self | oracle_patch | random_patch | pin_loo |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 86% (31/36) [71 to 94] | 8% (3/36) [3 to 22] | 53% (19/36) [37 to 68] | 14% (5/36) [6 to 29] | 22% (8/36) [12 to 38] | 50% (18/36) [34 to 66] | 8% (3/36) [3 to 22] | 25% (9/36) [14 to 41] |  |
| 5 | 88% (42/48) [75 to 94] |  | 62% (30/48) [48 to 75] | 6% (3/48) [2 to 17] | 21% (10/48) [12 to 34] | 58% (28/48) [44 to 71] | 21% (10/48) [12 to 34] | 31% (15/48) [20 to 45] | 73% (35/48) [59 to 83] |
| 10 | 85% (41/48) [73 to 93] | 2% (1/48) [0 to 11] | 58% (28/48) [44 to 71] | 10% (5/48) [5 to 22] | 21% (10/48) [12 to 34] | 62% (30/48) [48 to 75] | 12% (6/48) [6 to 25] | 31% (15/48) [20 to 45] | 56% (27/48) [42 to 69] |
| 20 | 85% (41/48) [73 to 93] |  | 73% (35/48) [59 to 83] | 10% (5/48) [5 to 22] | 6% (3/48) [2 to 17] | 67% (32/48) [53 to 78] | 10% (5/48) [5 to 22] | 15% (7/48) [7 to 27] | 62% (30/48) [48 to 75] |
| 40 | 94% (45/48) [83 to 98] | 8% (4/48) [3 to 20] | 79% (38/48) [66 to 88] | 6% (3/48) [2 to 17] | 17% (8/48) [9 to 30] | 73% (35/48) [59 to 83] | 4% (2/48) [1 to 14] | 17% (8/48) [9 to 30] | 69% (33/48) [55 to 80] |

Cochran-Armitage trend p (score log2 N): floor 0.434, full 0.926, plain 0.00705, pin_all 0.394, wp_batched 0.169, wp_self 0.0217, oracle_patch 0.319, random_patch 0.142, pin_loo 0.839

### Judged violation rate (COMPLY whose action breaks the rule)

| N | floor | full | plain | pin_all | wp_batched | wp_self | oracle_patch | random_patch | pin_loo |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 86% (31/36) [71 to 94] | 3% (1/36) [0 to 14] | 50% (18/36) [34 to 66] | 0% (0/36) [0 to 10] | 14% (5/36) [6 to 29] | 39% (14/36) [25 to 55] | 3% (1/36) [0 to 14] | 17% (6/36) [8 to 32] |  |
| 5 | 85% (41/48) [73 to 93] |  | 52% (25/48) [38 to 66] | 0% (0/48) [0 to 7] | 12% (6/48) [6 to 25] | 50% (24/48) [36 to 64] | 12% (6/48) [6 to 25] | 21% (10/48) [12 to 34] | 60% (29/48) [46 to 73] |
| 10 | 81% (39/48) [68 to 90] | 0% (0/48) [0 to 7] | 54% (26/48) [40 to 67] | 0% (0/48) [0 to 7] | 10% (5/48) [5 to 22] | 50% (24/48) [36 to 64] | 2% (1/48) [0 to 11] | 23% (11/48) [13 to 37] | 52% (25/48) [38 to 66] |
| 20 | 83% (40/48) [70 to 91] |  | 73% (35/48) [59 to 83] | 6% (3/48) [2 to 17] | 6% (3/48) [2 to 17] | 65% (31/48) [50 to 77] | 6% (3/48) [2 to 17] | 10% (5/48) [5 to 22] | 62% (30/48) [48 to 75] |
| 40 | 90% (43/48) [78 to 95] | 2% (1/48) [0 to 11] | 75% (36/48) [61 to 85] | 2% (1/48) [0 to 11] | 10% (5/48) [5 to 22] | 73% (35/48) [59 to 83] | 0% (0/48) [0 to 7] | 10% (5/48) [5 to 22] | 65% (31/48) [50 to 77] |

Cochran-Armitage trend p (score log2 N): floor 0.822, full 0.744, plain 0.00392, pin_all 0.115, wp_batched 0.374, wp_self 0.000744, oracle_patch 0.355, random_patch 0.249, pin_loo 0.469

Unparsed decisions (counted as non-violations): 2

### Pairwise comparisons (primary metric): Fisher two-sided p, and exact McNemar on paired trials

Confirmatory family: 5 comparisons x each N, McNemar p Holm-adjusted across the whole family. Other rows are exploratory (unadjusted).

| N | comparison | A | B | Fisher p | discordant (A only / B only) | McNemar p | Holm p | family |
|---|---|---|---|---|---|---|---|---|
| 1 | plain vs pin_all | 19/36 | 5/36 | 0.000934 | 16 / 2 | 0.00131 | 0.0171 | confirmatory |
| 1 | plain vs wp_batched | 19/36 | 8/36 | 0.0142 | 13 / 2 | 0.00739 | 0.0812 | confirmatory |
| 1 | plain vs wp_self | 19/36 | 18/36 | 1 | 3 / 2 | 1 | 1 | confirmatory |
| 1 | pin_all vs wp_batched | 5/36 | 8/36 | 0.541 | 1 / 4 | 0.375 | 1 | confirmatory |
| 1 | pin_all vs wp_self | 5/36 | 18/36 | 0.00205 | 2 / 15 | 0.00235 | 0.0282 | confirmatory |
| 1 | wp_batched vs wp_self | 8/36 | 18/36 | 0.0263 | 1 / 11 | 0.00635 |  | exploratory |
| 1 | full vs pin_all | 3/36 | 5/36 | 0.71 | 2 / 4 | 0.688 |  | exploratory |
| 1 | wp_batched vs oracle_patch | 8/36 | 3/36 | 0.189 | 6 / 1 | 0.125 |  | exploratory |
| 1 | wp_batched vs random_patch | 8/36 | 9/36 | 1 | 0 / 1 | 1 |  | exploratory |
| 1 | floor vs plain | 31/36 | 19/36 | 0.00429 | 14 / 2 | 0.00418 |  | exploratory |
| 5 | plain vs pin_all | 30/48 | 3/48 | 4.56e-09 | 27 / 0 | 1.49e-08 | 3.13e-07 | confirmatory |
| 5 | plain vs wp_batched | 30/48 | 10/48 | 6.54e-05 | 21 / 1 | 1.1e-05 | 0.000165 | confirmatory |
| 5 | plain vs wp_self | 30/48 | 28/48 | 0.835 | 4 / 2 | 0.688 | 1 | confirmatory |
| 5 | pin_all vs wp_batched | 3/48 | 10/48 | 0.0704 | 0 / 7 | 0.0156 | 0.156 | confirmatory |
| 5 | pin_all vs wp_self | 3/48 | 28/48 | 4.14e-08 | 1 / 26 | 4.17e-07 | 7.51e-06 | confirmatory |
| 5 | wp_batched vs wp_self | 10/48 | 28/48 | 0.000327 | 1 / 19 | 4.01e-05 |  | exploratory |
| 5 | pin_all vs pin_loo | 3/48 | 35/48 | 8.47e-12 | 1 / 33 | 4.07e-09 |  | exploratory |
| 5 | wp_batched vs oracle_patch | 10/48 | 10/48 | 1 | 3 / 3 | 1 |  | exploratory |
| 5 | wp_batched vs random_patch | 10/48 | 15/48 | 0.352 | 3 / 8 | 0.227 |  | exploratory |
| 5 | floor vs plain | 42/48 | 30/48 | 0.00867 | 14 / 2 | 0.00418 |  | exploratory |
| 10 | plain vs pin_all | 28/48 | 5/48 | 1.08e-06 | 25 / 2 | 5.65e-06 | 9.04e-05 | confirmatory |
| 10 | plain vs wp_batched | 28/48 | 10/48 | 0.000327 | 22 / 4 | 0.000534 | 0.00747 | confirmatory |
| 10 | plain vs wp_self | 28/48 | 30/48 | 0.835 | 3 / 5 | 0.727 | 1 | confirmatory |
| 10 | pin_all vs wp_batched | 5/48 | 10/48 | 0.261 | 1 / 6 | 0.125 | 1 | confirmatory |
| 10 | pin_all vs wp_self | 5/48 | 30/48 | 1.42e-07 | 1 / 26 | 4.17e-07 | 7.51e-06 | confirmatory |
| 10 | wp_batched vs wp_self | 10/48 | 30/48 | 6.54e-05 | 3 / 23 | 8.8e-05 |  | exploratory |
| 10 | pin_all vs pin_loo | 5/48 | 27/48 | 2.81e-06 | 1 / 23 | 2.98e-06 |  | exploratory |
| 10 | full vs pin_all | 1/48 | 5/48 | 0.204 | 0 / 4 | 0.125 |  | exploratory |
| 10 | wp_batched vs oracle_patch | 10/48 | 6/48 | 0.412 | 4 / 0 | 0.125 |  | exploratory |
| 10 | wp_batched vs random_patch | 10/48 | 15/48 | 0.352 | 4 / 9 | 0.267 |  | exploratory |
| 10 | floor vs plain | 41/48 | 28/48 | 0.00586 | 15 / 2 | 0.00235 |  | exploratory |
| 20 | plain vs pin_all | 35/48 | 5/48 | 4.03e-10 | 30 / 0 | 1.86e-09 | 4.1e-08 | confirmatory |
| 20 | plain vs wp_batched | 35/48 | 3/48 | 8.47e-12 | 32 / 0 | 4.66e-10 | 1.12e-08 | confirmatory |
| 20 | plain vs wp_self | 35/48 | 32/48 | 0.657 | 5 / 2 | 0.453 | 1 | confirmatory |
| 20 | pin_all vs wp_batched | 5/48 | 3/48 | 0.714 | 4 / 2 | 0.688 | 1 | confirmatory |
| 20 | pin_all vs wp_self | 5/48 | 32/48 | 1.57e-08 | 0 / 27 | 1.49e-08 | 3.13e-07 | confirmatory |
| 20 | wp_batched vs wp_self | 3/48 | 32/48 | 4.26e-10 | 0 / 29 | 3.73e-09 |  | exploratory |
| 20 | pin_all vs pin_loo | 5/48 | 30/48 | 1.42e-07 | 0 / 25 | 5.96e-08 |  | exploratory |
| 20 | wp_batched vs oracle_patch | 3/48 | 5/48 | 0.714 | 1 / 3 | 0.625 |  | exploratory |
| 20 | wp_batched vs random_patch | 3/48 | 7/48 | 0.317 | 3 / 7 | 0.344 |  | exploratory |
| 20 | floor vs plain | 41/48 | 35/48 | 0.208 | 10 / 4 | 0.18 |  | exploratory |
| 40 | plain vs pin_all | 38/48 | 3/48 | 9.85e-14 | 35 / 0 | 5.82e-11 | 1.46e-09 | confirmatory |
| 40 | plain vs wp_batched | 38/48 | 8/48 | 8.76e-10 | 32 / 2 | 6.94e-08 | 1.32e-06 | confirmatory |
| 40 | plain vs wp_self | 38/48 | 35/48 | 0.633 | 7 / 4 | 0.549 | 1 | confirmatory |
| 40 | pin_all vs wp_batched | 3/48 | 8/48 | 0.199 | 2 / 7 | 0.18 | 1 | confirmatory |
| 40 | pin_all vs wp_self | 3/48 | 35/48 | 8.47e-12 | 0 / 32 | 4.66e-10 | 1.12e-08 | confirmatory |
| 40 | wp_batched vs wp_self | 8/48 | 35/48 | 4.07e-08 | 2 / 29 | 4.63e-07 |  | exploratory |
| 40 | pin_all vs pin_loo | 3/48 | 33/48 | 1.21e-10 | 0 / 30 | 1.86e-09 |  | exploratory |
| 40 | full vs pin_all | 4/48 | 3/48 | 1 | 3 / 2 | 1 |  | exploratory |
| 40 | wp_batched vs oracle_patch | 8/48 | 2/48 | 0.0909 | 6 / 0 | 0.0312 |  | exploratory |
| 40 | wp_batched vs random_patch | 8/48 | 8/48 | 1 | 5 / 5 | 1 |  | exploratory |
| 40 | floor vs plain | 45/48 | 38/48 | 0.0704 | 9 / 2 | 0.0654 |  | exploratory |

### Exploratory: pooled primary metric, and judged-violation comparisons (McNemar, unadjusted)

| N | comparison | A | B | discordant (A only / B only) | McNemar p |
|---|---|---|---|---|---|
| pooled N>=5, PRIMARY metric | pin_all vs wp_batched | 16/192 | 31/192 | 7 / 22 | 0.00813 |
| pooled N>=5, PRIMARY metric | plain vs wp_batched | 131/192 | 31/192 | 107 / 7 | 4.23e-24 |
| 1 | pin_all vs wp_batched | 0/36 | 5/36 | 0 / 5 | 0.0625 |
| 1 | plain vs wp_batched | 18/36 | 5/36 | 13 / 0 | 0.000244 |
| 1 | wp_batched vs oracle_patch | 5/36 | 1/36 | 5 / 1 | 0.219 |
| 1 | wp_batched vs random_patch | 5/36 | 6/36 | 0 / 1 | 1 |
| 5 | pin_all vs wp_batched | 0/48 | 6/48 | 0 / 6 | 0.0312 |
| 5 | plain vs wp_batched | 25/48 | 6/48 | 20 / 1 | 2.1e-05 |
| 5 | wp_batched vs oracle_patch | 6/48 | 6/48 | 3 / 3 | 1 |
| 5 | wp_batched vs random_patch | 6/48 | 10/48 | 2 / 6 | 0.289 |
| 10 | pin_all vs wp_batched | 0/48 | 5/48 | 0 / 5 | 0.0625 |
| 10 | plain vs wp_batched | 26/48 | 5/48 | 24 / 3 | 4.92e-05 |
| 10 | wp_batched vs oracle_patch | 5/48 | 1/48 | 4 / 0 | 0.125 |
| 10 | wp_batched vs random_patch | 5/48 | 11/48 | 2 / 8 | 0.109 |
| 20 | pin_all vs wp_batched | 3/48 | 3/48 | 2 / 2 | 1 |
| 20 | plain vs wp_batched | 35/48 | 3/48 | 32 / 0 | 4.66e-10 |
| 20 | wp_batched vs oracle_patch | 3/48 | 3/48 | 2 / 2 | 1 |
| 20 | wp_batched vs random_patch | 3/48 | 5/48 | 3 / 5 | 0.727 |
| 40 | pin_all vs wp_batched | 1/48 | 5/48 | 0 / 4 | 0.125 |
| 40 | plain vs wp_batched | 36/48 | 5/48 | 33 / 2 | 3.67e-08 |
| 40 | wp_batched vs oracle_patch | 5/48 | 0/48 | 5 / 0 | 0.0625 |
| 40 | wp_batched vs random_patch | 5/48 | 5/48 | 5 / 5 | 1 |
| pooled N>=5 | pin_all vs wp_batched | 4/192 | 19/192 | 2 / 17 | 0.000729 |
| pooled N>=5 | plain vs wp_batched | 122/192 | 19/192 | 109 / 6 | 1.43e-25 |
| pooled N>=5 | wp_batched vs oracle_patch | 19/192 | 10/192 | 14 / 5 | 0.0636 |
| pooled N>=5 | wp_batched vs random_patch | 19/192 | 31/192 | 12 / 24 | 0.0652 |

### Judge validation against hand labels (stratified samples)

| judge | n | agreement | Cohen's kappa |
|---|---|---|---|
| survival judge (ground truth) | 44 | 95% | 0.91 |
| wp_batched comparator 'covered' | 44 | 93% | 0.86 |
| wp_self self-judgment 'covered' | 44 | 45% | 0.00 |
| action judge (secondary metric) | 42 | 98% | 0.95 |

### Rule survival in the summary (independent judge) and detector quality

Truth: a rule is 'missing' when the judge says the compacted context does not state it.

| N | rules | survived (judge) | survived (judge + quote found) | detector | flagged missing (patch rate) | recall of misses | precision of flags |
|---|---|---|---|---|---|---|---|
| 1 | 36 | 53% (19/36) [37 to 68] | 53% (19/36) [37 to 68] | wp_batched | 36% (13/36) [22 to 52] | 76% (13/17) [53 to 90] | 100% (13/13) [77 to 100] |
| 1 | 36 | 53% (19/36) [37 to 68] | 53% (19/36) [37 to 68] | wp_self | 3% (1/36) [0 to 14] | 6% (1/17) [1 to 27] | 100% (1/1) [21 to 100] |
| 5 | 80 | 55% (44/80) [44 to 65] | 55% (44/80) [44 to 65] | wp_batched | 40% (32/80) [30 to 51] | 83% (30/36) [68 to 92] | 94% (30/32) [80 to 98] |
| 5 | 80 | 55% (44/80) [44 to 65] | 55% (44/80) [44 to 65] | wp_self | 2% (2/80) [1 to 9] | 6% (2/36) [2 to 18] | 100% (2/2) [34 to 100] |
| 10 | 160 | 35% (56/160) [28 to 43] | 35% (56/160) [28 to 43] | wp_batched | 56% (90/160) [49 to 64] | 86% (89/104) [78 to 91] | 99% (89/90) [94 to 100] |
| 10 | 160 | 35% (56/160) [28 to 43] | 35% (56/160) [28 to 43] | wp_self | 4% (7/160) [2 to 9] | 7% (7/104) [3 to 13] | 100% (7/7) [65 to 100] |
| 20 | 320 | 15% (49/320) [12 to 20] | 15% (48/320) [12 to 19] | wp_batched | 83% (265/320) [78 to 87] | 96% (260/271) [93 to 98] | 98% (260/265) [96 to 99] |
| 20 | 320 | 15% (49/320) [12 to 20] | 15% (48/320) [12 to 19] | wp_self | 4% (14/320) [3 to 7] | 5% (14/271) [3 to 8] | 100% (14/14) [78 to 100] |
| 40 | 640 | 4% (26/640) [3 to 6] | 4% (26/640) [3 to 6] | wp_batched | 89% (571/640) [87 to 91] | 93% (568/614) [90 to 94] | 99% (568/571) [98 to 100] |
| 40 | 640 | 4% (26/640) [3 to 6] | 4% (26/640) [3 to 6] | wp_self | 2% (16/640) [2 to 4] | 3% (16/614) [2 to 4] | 100% (16/16) [81 to 100] |

### Plain-method violation by judged survival of the tested rule

| N | rule survived | rule missing |
|---|---|---|
| 1 | 11% (2/19) [3 to 31] | 100% (17/17) [82 to 100] |
| 5 | 41% (11/27) [25 to 59] | 90% (19/21) [71 to 97] |
| 10 | 32% (6/19) [15 to 54] | 76% (22/29) [58 to 88] |
| 20 | 22% (2/9) [6 to 55] | 85% (33/39) [70 to 93] |
| 40 | n/a | 79% (38/48) [66 to 88] |

### Cost per transcript (means)

| N | summary words | method | extra model calls | added context tokens (est.) | detector input tokens (est.) |
|---|---|---|---|---|---|
| 1 | 137 | plain | 0 | 0 | 0 |
| 1 | 137 | pin_all | 0 | 42 | 0 |
| 1 | 137 | wp_batched | 2 | 15 | 652 |
| 1 | 137 | wp_self | 1 | 1 | 461 |
| 5 | 146 | plain | 0 | 0 | 0 |
| 5 | 146 | pin_all | 0 | 184 | 0 |
| 5 | 146 | wp_batched | 6 | 78 | 1818 |
| 5 | 146 | wp_self | 5 | 5 | 2408 |
| 10 | 145 | plain | 0 | 0 | 0 |
| 10 | 145 | pin_all | 0 | 355 | 0 |
| 10 | 145 | wp_batched | 11 | 207 | 2953 |
| 10 | 145 | wp_self | 10 | 17 | 4811 |
| 20 | 150 | plain | 0 | 0 | 0 |
| 20 | 150 | pin_all | 0 | 701 | 0 |
| 20 | 150 | wp_batched | 21 | 585 | 5208 |
| 20 | 150 | wp_self | 20 | 34 | 9832 |
| 40 | 138 | plain | 0 | 0 | 0 |
| 40 | 138 | pin_all | 0 | 1395 | 0 |
| 40 | 138 | wp_batched | 41 | 1251 | 12168 |
| 40 | 138 | wp_self | 40 | 38 | 18803 |

