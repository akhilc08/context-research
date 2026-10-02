## Source: results_scaled.jsonl

Transcripts per N: N=5: 12, N=10: 12, N=20: 12, N=40: 12

### Violation rate (COMPLY on trigger)

| N | floor | full | plain | pin_all | wp_batched | wp_self | oracle_patch | random_patch | pin_loo |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 86% (31/36) [71 to 94] |  | 50% (18/36) [34 to 66] | 6% (2/36) [2 to 18] | 11% (4/36) [4 to 25] | 36% (13/36) [22 to 52] | 14% (5/36) [6 to 29] | 28% (10/36) [16 to 44] | 50% (18/36) [34 to 66] |
| 10 | 89% (32/36) [75 to 96] | 3% (1/36) [0 to 14] | 53% (19/36) [37 to 68] | 8% (3/36) [3 to 22] | 28% (10/36) [16 to 44] | 50% (18/36) [34 to 66] | 11% (4/36) [4 to 25] | 28% (10/36) [16 to 44] | 50% (18/36) [34 to 66] |
| 20 | 94% (34/36) [82 to 98] |  | 50% (18/36) [34 to 66] | 3% (1/36) [0 to 14] | 8% (3/36) [3 to 22] | 53% (19/36) [37 to 68] | 0% (0/36) [0 to 10] | 11% (4/36) [4 to 25] | 53% (19/36) [37 to 68] |
| 40 | 94% (34/36) [82 to 98] | 3% (1/36) [0 to 14] | 64% (23/36) [48 to 78] | 3% (1/36) [0 to 14] | 14% (5/36) [6 to 29] | 61% (22/36) [45 to 75] | 14% (5/36) [6 to 29] | 28% (10/36) [16 to 44] | 69% (25/36) [53 to 82] |

Cochran-Armitage trend p (score log2 N): floor 0.153, plain 0.295, pin_all 0.386, wp_batched 0.679, wp_self 0.0369, oracle_patch 0.615, random_patch 0.599, pin_loo 0.0989

### Judged violation rate (COMPLY whose action breaks the rule)

| N | floor | full | plain | pin_all | wp_batched | wp_self | oracle_patch | random_patch | pin_loo |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 86% (31/36) [71 to 94] |  | 39% (14/36) [25 to 55] | 0% (0/36) [0 to 10] | 8% (3/36) [3 to 22] | 28% (10/36) [16 to 44] | 8% (3/36) [3 to 22] | 19% (7/36) [10 to 35] | 39% (14/36) [25 to 55] |
| 10 | 86% (31/36) [71 to 94] | 3% (1/36) [0 to 14] | 50% (18/36) [34 to 66] | 3% (1/36) [0 to 14] | 19% (7/36) [10 to 35] | 44% (16/36) [30 to 60] | 6% (2/36) [2 to 18] | 19% (7/36) [10 to 35] | 50% (18/36) [34 to 66] |
| 20 | 92% (33/36) [78 to 97] |  | 50% (18/36) [34 to 66] | 3% (1/36) [0 to 14] | 8% (3/36) [3 to 22] | 53% (19/36) [37 to 68] | 0% (0/36) [0 to 10] | 8% (3/36) [3 to 22] | 53% (19/36) [37 to 68] |
| 40 | 94% (34/36) [82 to 98] | 3% (1/36) [0 to 14] | 58% (21/36) [42 to 73] | 0% (0/36) [0 to 10] | 6% (2/36) [2 to 18] | 56% (20/36) [40 to 70] | 6% (2/36) [2 to 18] | 14% (5/36) [6 to 29] | 64% (23/36) [48 to 78] |

Cochran-Armitage trend p (score log2 N): floor 0.18, plain 0.117, pin_all 1, wp_batched 0.393, wp_self 0.0135, oracle_patch 0.386, random_patch 0.3, pin_loo 0.0368

Unparsed decisions (counted as non-violations): 1

### Pairwise comparisons (primary metric): Fisher two-sided p, and exact McNemar on paired trials

Confirmatory family: 5 comparisons x each N, McNemar p Holm-adjusted across the whole family. Other rows are exploratory (unadjusted).

| N | comparison | A | B | Fisher p | discordant (A only / B only) | McNemar p | Holm p | family |
|---|---|---|---|---|---|---|---|---|
| 5 | plain vs pin_all | 18/36 | 2/36 | 3.87e-05 | 17 / 1 | 0.000145 | 0.00174 | confirmatory |
| 5 | plain vs wp_batched | 18/36 | 4/36 | 0.000671 | 16 / 2 | 0.00131 | 0.0131 | confirmatory |
| 5 | plain vs wp_self | 18/36 | 13/36 | 0.341 | 7 / 2 | 0.18 | 1 | confirmatory |
| 5 | pin_all vs wp_batched | 2/36 | 4/36 | 0.674 | 0 / 2 | 0.5 | 1 | confirmatory |
| 5 | pin_all vs wp_self | 2/36 | 13/36 | 0.00277 | 0 / 11 | 0.000977 | 0.0107 | confirmatory |
| 5 | wp_batched vs wp_self | 4/36 | 13/36 | 0.0246 | 0 / 9 | 0.00391 |  | exploratory |
| 5 | pin_all vs pin_loo | 2/36 | 18/36 | 3.87e-05 | 0 / 16 | 3.05e-05 |  | exploratory |
| 5 | wp_batched vs oracle_patch | 4/36 | 5/36 | 1 | 2 / 3 | 1 |  | exploratory |
| 5 | wp_batched vs random_patch | 4/36 | 10/36 | 0.135 | 1 / 7 | 0.0703 |  | exploratory |
| 5 | floor vs plain | 31/36 | 18/36 | 0.00205 | 14 / 1 | 0.000977 |  | exploratory |
| 10 | plain vs pin_all | 19/36 | 3/36 | 7.39e-05 | 16 / 0 | 3.05e-05 | 0.000488 | confirmatory |
| 10 | plain vs wp_batched | 19/36 | 10/36 | 0.0537 | 13 / 4 | 0.049 | 0.441 | confirmatory |
| 10 | plain vs wp_self | 19/36 | 18/36 | 1 | 1 / 0 | 1 | 1 | confirmatory |
| 10 | pin_all vs wp_batched | 3/36 | 10/36 | 0.0632 | 2 / 9 | 0.0654 | 0.523 | confirmatory |
| 10 | pin_all vs wp_self | 3/36 | 18/36 | 0.000182 | 0 / 15 | 6.1e-05 | 0.000916 | confirmatory |
| 10 | wp_batched vs wp_self | 10/36 | 18/36 | 0.0898 | 4 / 12 | 0.0768 |  | exploratory |
| 10 | pin_all vs pin_loo | 3/36 | 18/36 | 0.000182 | 0 / 15 | 6.1e-05 |  | exploratory |
| 10 | full vs pin_all | 1/36 | 3/36 | 0.614 | 1 / 3 | 0.625 |  | exploratory |
| 10 | wp_batched vs oracle_patch | 10/36 | 4/36 | 0.135 | 7 / 1 | 0.0703 |  | exploratory |
| 10 | wp_batched vs random_patch | 10/36 | 10/36 | 1 | 6 / 6 | 1 |  | exploratory |
| 10 | floor vs plain | 32/36 | 19/36 | 0.00149 | 15 / 2 | 0.00235 |  | exploratory |
| 20 | plain vs pin_all | 18/36 | 1/36 | 5.69e-06 | 17 / 0 | 1.53e-05 | 0.000259 | confirmatory |
| 20 | plain vs wp_batched | 18/36 | 3/36 | 0.000182 | 15 / 0 | 6.1e-05 | 0.000916 | confirmatory |
| 20 | plain vs wp_self | 18/36 | 19/36 | 1 | 3 / 4 | 1 | 1 | confirmatory |
| 20 | pin_all vs wp_batched | 1/36 | 3/36 | 0.614 | 0 / 2 | 0.5 | 1 | confirmatory |
| 20 | pin_all vs wp_self | 1/36 | 19/36 | 2.03e-06 | 0 / 18 | 7.63e-06 | 0.000137 | confirmatory |
| 20 | wp_batched vs wp_self | 3/36 | 19/36 | 7.39e-05 | 1 / 17 | 0.000145 |  | exploratory |
| 20 | pin_all vs pin_loo | 1/36 | 19/36 | 2.03e-06 | 0 / 18 | 7.63e-06 |  | exploratory |
| 20 | wp_batched vs oracle_patch | 3/36 | 0/36 | 0.239 | 3 / 0 | 0.25 |  | exploratory |
| 20 | wp_batched vs random_patch | 3/36 | 4/36 | 1 | 2 / 3 | 1 |  | exploratory |
| 20 | floor vs plain | 34/36 | 18/36 | 3.87e-05 | 18 / 2 | 0.000402 |  | exploratory |
| 40 | plain vs pin_all | 23/36 | 1/36 | 2.12e-08 | 22 / 0 | 4.77e-07 | 9.54e-06 | confirmatory |
| 40 | plain vs wp_batched | 23/36 | 5/36 | 2.51e-05 | 20 / 2 | 0.000121 | 0.00157 | confirmatory |
| 40 | plain vs wp_self | 23/36 | 22/36 | 1 | 2 / 1 | 1 | 1 | confirmatory |
| 40 | pin_all vs wp_batched | 1/36 | 5/36 | 0.199 | 0 / 4 | 0.125 | 0.875 | confirmatory |
| 40 | pin_all vs wp_self | 1/36 | 22/36 | 7.14e-08 | 0 / 21 | 9.54e-07 | 1.81e-05 | confirmatory |
| 40 | wp_batched vs wp_self | 5/36 | 22/36 | 6.71e-05 | 2 / 19 | 0.000221 |  | exploratory |
| 40 | pin_all vs pin_loo | 1/36 | 25/36 | 1.59e-09 | 0 / 24 | 1.19e-07 |  | exploratory |
| 40 | full vs pin_all | 1/36 | 1/36 | 1 | 1 / 1 | 1 |  | exploratory |
| 40 | wp_batched vs oracle_patch | 5/36 | 5/36 | 1 | 3 / 3 | 1 |  | exploratory |
| 40 | wp_batched vs random_patch | 5/36 | 10/36 | 0.245 | 2 / 7 | 0.18 |  | exploratory |
| 40 | floor vs plain | 34/36 | 23/36 | 0.00277 | 13 / 2 | 0.00739 |  | exploratory |

### Exploratory: pooled primary metric, and judged-violation comparisons (McNemar, unadjusted)

| N | comparison | A | B | discordant (A only / B only) | McNemar p |
|---|---|---|---|---|---|
| pooled N>=5, PRIMARY metric | pin_all vs wp_batched | 7/144 | 22/144 | 2 / 17 | 0.000729 |
| pooled N>=5, PRIMARY metric | plain vs wp_batched | 78/144 | 22/144 | 64 / 8 | 5.77e-12 |
| 5 | pin_all vs wp_batched | 0/36 | 3/36 | 0 / 3 | 0.25 |
| 5 | plain vs wp_batched | 14/36 | 3/36 | 13 / 2 | 0.00739 |
| 5 | wp_batched vs oracle_patch | 3/36 | 3/36 | 2 / 2 | 1 |
| 5 | wp_batched vs random_patch | 3/36 | 7/36 | 2 / 6 | 0.289 |
| 10 | pin_all vs wp_batched | 1/36 | 7/36 | 1 / 7 | 0.0703 |
| 10 | plain vs wp_batched | 18/36 | 7/36 | 14 / 3 | 0.0127 |
| 10 | wp_batched vs oracle_patch | 7/36 | 2/36 | 5 / 0 | 0.0625 |
| 10 | wp_batched vs random_patch | 7/36 | 7/36 | 5 / 5 | 1 |
| 20 | pin_all vs wp_batched | 1/36 | 3/36 | 0 / 2 | 0.5 |
| 20 | plain vs wp_batched | 18/36 | 3/36 | 15 / 0 | 6.1e-05 |
| 20 | wp_batched vs oracle_patch | 3/36 | 0/36 | 3 / 0 | 0.25 |
| 20 | wp_batched vs random_patch | 3/36 | 3/36 | 3 / 3 | 1 |
| 40 | pin_all vs wp_batched | 0/36 | 2/36 | 0 / 2 | 0.5 |
| 40 | plain vs wp_batched | 21/36 | 2/36 | 20 / 1 | 2.1e-05 |
| 40 | wp_batched vs oracle_patch | 2/36 | 2/36 | 1 / 1 | 1 |
| 40 | wp_batched vs random_patch | 2/36 | 5/36 | 1 / 4 | 0.375 |
| pooled N>=5 | pin_all vs wp_batched | 2/144 | 15/144 | 1 / 14 | 0.000977 |
| pooled N>=5 | plain vs wp_batched | 71/144 | 15/144 | 62 / 6 | 8.18e-13 |
| pooled N>=5 | wp_batched vs oracle_patch | 15/144 | 7/144 | 11 / 3 | 0.0574 |
| pooled N>=5 | wp_batched vs random_patch | 15/144 | 22/144 | 11 / 18 | 0.265 |

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
| 5 | 60 | 63% (38/60) [51 to 74] | 63% (38/60) [51 to 74] | wp_batched | 33% (20/60) [23 to 46] | 91% (20/22) [72 to 97] | 100% (20/20) [84 to 100] |
| 5 | 60 | 63% (38/60) [51 to 74] | 63% (38/60) [51 to 74] | wp_self | 7% (4/60) [3 to 16] | 18% (4/22) [7 to 39] | 100% (4/4) [51 to 100] |
| 10 | 120 | 42% (50/120) [33 to 51] | 41% (49/120) [32 to 50] | wp_batched | 49% (59/120) [40 to 58] | 84% (59/70) [74 to 91] | 100% (59/59) [94 to 100] |
| 10 | 120 | 42% (50/120) [33 to 51] | 41% (49/120) [32 to 50] | wp_self | 2% (3/120) [1 to 7] | 4% (3/70) [1 to 12] | 100% (3/3) [44 to 100] |
| 20 | 240 | 29% (70/240) [24 to 35] | 29% (69/240) [23 to 35] | wp_batched | 61% (146/240) [55 to 67] | 85% (145/170) [79 to 90] | 99% (145/146) [96 to 100] |
| 20 | 240 | 29% (70/240) [24 to 35] | 29% (69/240) [23 to 35] | wp_self | 4% (10/240) [2 to 7] | 6% (10/170) [3 to 10] | 100% (10/10) [72 to 100] |
| 40 | 480 | 24% (113/480) [20 to 28] | 23% (112/480) [20 to 27] | wp_batched | 71% (340/480) [67 to 75] | 92% (338/367) [89 to 94] | 99% (338/340) [98 to 100] |
| 40 | 480 | 24% (113/480) [20 to 28] | 23% (112/480) [20 to 27] | wp_self | 5% (22/480) [3 to 7] | 6% (22/367) [4 to 9] | 100% (22/22) [85 to 100] |

### Plain-method violation by judged survival of the tested rule

| N | rule survived | rule missing |
|---|---|---|
| 5 | 29% (6/21) [14 to 50] | 80% (12/15) [55 to 93] |
| 10 | 24% (4/17) [10 to 47] | 79% (15/19) [57 to 91] |
| 20 | 11% (1/9) [2 to 44] | 63% (17/27) [44 to 78] |
| 40 | 46% (6/13) [23 to 71] | 74% (17/23) [54 to 87] |

### Cost per transcript (means)

| N | summary words | method | extra model calls | added context tokens (est.) | detector input tokens (est.) |
|---|---|---|---|---|---|
| 5 | 196 | plain | 0 | 0 | 0 |
| 5 | 196 | pin_all | 0 | 186 | 0 |
| 5 | 196 | wp_batched | 6 | 62 | 1838 |
| 5 | 196 | wp_self | 5 | 14 | 2899 |
| 10 | 231 | plain | 0 | 0 | 0 |
| 10 | 231 | pin_all | 0 | 358 | 0 |
| 10 | 231 | wp_batched | 11 | 185 | 3223 |
| 10 | 231 | wp_self | 10 | 9 | 6516 |
| 20 | 314 | plain | 0 | 0 | 0 |
| 20 | 314 | pin_all | 0 | 702 | 0 |
| 20 | 314 | wp_batched | 21 | 429 | 7709 |
| 20 | 314 | wp_self | 20 | 30 | 16124 |
| 40 | 449 | plain | 0 | 0 | 0 |
| 40 | 449 | pin_all | 0 | 1396 | 0 |
| 40 | 449 | wp_batched | 41 | 993 | 18030 |
| 40 | 449 | wp_self | 40 | 68 | 42487 |

