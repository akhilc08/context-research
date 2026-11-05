# E20 tables (stealth/space-bunny-alpha)

17280 graded decisions, 60 sessions. Wilson 95% CIs (not adjusted for clustering).

## Correct rate, clean summary (judged action, primary)

| format | active | revoked | loosen | tighten | amended | rule_state |
|---|---|---|---|---|---|---|
| none | 8% [5 to 11] | 92% [89 to 95] | 87% [81 to 91] | 16% [11 to 22] | 51% [46 to 57] | 50% [47 to 53] |
| a_delete | 100% [99 to 100] | 94% [91 to 96] | 78% [71 to 83] | 99% [97 to 100] | 89% [85 to 91] | 94% [93 to 95] |
| b_ledger | 100% [98 to 100] | 85% [81 to 88] | 82% [76 to 87] | 98% [94 to 99] | 90% [86 to 93] | 92% [90 to 93] |
| c_permit | 100% [99 to 100] | 98% [95 to 99] | 74% [67 to 80] | 99% [96 to 100] | 86% [82 to 90] | 95% [93 to 96] |
| d_label | 100% [99 to 100] | 93% [90 to 95] | 74% [68 to 80] | 98% [95 to 99] | 86% [82 to 90] | 93% [91 to 94] |
| e_wasnow | 100% [99 to 100] | 92% [89 to 94] | 88% [82 to 92] | 100% [98 to 100] | 94% [91 to 96] | 95% [94 to 96] |
| f_raw | 99% [98 to 100] | 91% [88 to 94] | 73% [66 to 79] | 74% [67 to 80] | 74% [69 to 78] | 88% [86 to 90] |
| g_struck | 98% [96 to 99] | 95% [93 to 97] | 74% [67 to 80] | 75% [68 to 81] | 74% [70 to 79] | 89% [87 to 91] |

## Correct rate, stale summary (judged action, primary)

| format | active | revoked | loosen | tighten | amended | rule_state |
|---|---|---|---|---|---|---|
| none | 100% [98 to 100] | 3% [2 to 5] | 6% [3 to 11] | 16% [11 to 22] | 11% [8 to 14] | 38% [35 to 41] |
| a_delete | 100% [98 to 100] | 4% [3 to 7] | 83% [77 to 88] | 99% [96 to 100] | 91% [88 to 94] | 65% [62 to 68] |
| b_ledger | 99% [98 to 100] | 85% [81 to 89] | 88% [83 to 92] | 97% [93 to 98] | 92% [89 to 95] | 92% [91 to 94] |
| c_permit | 100% [98 to 100] | 96% [94 to 98] | 84% [78 to 89] | 97% [94 to 99] | 91% [87 to 93] | 96% [94 to 97] |
| d_label | 100% [98 to 100] | 89% [86 to 92] | 81% [74 to 86] | 99% [97 to 100] | 90% [86 to 93] | 93% [91 to 94] |
| e_wasnow | 100% [98 to 100] | 4% [2 to 6] | 86% [80 to 90] | 99% [97 to 100] | 93% [90 to 95] | 65% [62 to 68] |
| f_raw | 99% [97 to 99] | 90% [86 to 92] | 77% [70 to 82] | 79% [72 to 84] | 78% [73 to 82] | 89% [87 to 90] |
| g_struck | 99% [98 to 100] | 90% [87 to 93] | 74% [68 to 80] | 79% [72 to 84] | 77% [72 to 81] | 89% [87 to 91] |

## Failure modes, clean summary

Over-refusal = revoked or loosened rule applied (APPLIES). Under-enforcement = active or tightened rule not applied (IGNORES). OTHER = unclear or unrelated hold.

| format | revoked: over-refusal | revoked: OTHER | active: under-enforced | active: OTHER | loosen: over-refusal | tighten: under-enforced |
|---|---|---|---|---|---|---|
| none | 3% [2 to 6] | 4% [3 to 7] | 89% [86 to 92] | 3% [2 to 6] | 2% [1 to 5] | 69% [62 to 76] |
| a_delete | 3% [2 to 5] | 3% [2 to 6] | 0% [0 to 1] | 0% [0 to 1] | 21% [15 to 27] | 1% [0 to 3] |
| b_ledger | 13% [10 to 17] | 2% [1 to 4] | 0% [0 to 2] | 0% [0 to 1] | 17% [12 to 23] | 2% [1 to 5] |
| c_permit | 0% [0 to 2] | 2% [1 to 4] | 0% [0 to 1] | 0% [0 to 1] | 25% [19 to 32] | 1% [0 to 4] |
| d_label | 5% [3 to 7] | 2% [1 to 5] | 0% [0 to 1] | 0% [0 to 1] | 23% [17 to 29] | 1% [0 to 3] |
| e_wasnow | 5% [3 to 7] | 3% [2 to 6] | 0% [0 to 1] | 0% [0 to 1] | 11% [7 to 16] | 0% [0 to 2] |
| f_raw | 8% [5 to 11] | 1% [0 to 3] | 1% [0 to 2] | 0% [0 to 1] | 27% [21 to 34] | 23% [17 to 29] |
| g_struck | 3% [2 to 6] | 1% [1 to 3] | 2% [1 to 4] | 0% [0 to 1] | 25% [19 to 32] | 23% [17 to 29] |

## Failure modes, stale summary

Over-refusal = revoked or loosened rule applied (APPLIES). Under-enforcement = active or tightened rule not applied (IGNORES). OTHER = unclear or unrelated hold.

| format | revoked: over-refusal | revoked: OTHER | active: under-enforced | active: OTHER | loosen: over-refusal | tighten: under-enforced |
|---|---|---|---|---|---|---|
| none | 97% [95 to 98] | 0% [0 to 2] | 0% [0 to 2] | 0% [0 to 1] | 93% [89 to 96] | 79% [72 to 84] |
| a_delete | 95% [93 to 97] | 0% [0 to 2] | 0% [0 to 2] | 0% [0 to 1] | 14% [10 to 20] | 1% [0 to 3] |
| b_ledger | 13% [10 to 17] | 2% [1 to 4] | 1% [0 to 2] | 0% [0 to 1] | 11% [7 to 16] | 1% [0 to 4] |
| c_permit | 2% [1 to 4] | 2% [1 to 4] | 0% [0 to 2] | 0% [0 to 1] | 16% [11 to 22] | 2% [1 to 5] |
| d_label | 8% [6 to 12] | 2% [1 to 5] | 0% [0 to 2] | 0% [0 to 1] | 17% [12 to 23] | 1% [0 to 3] |
| e_wasnow | 96% [94 to 98] | 0% [0 to 2] | 0% [0 to 2] | 0% [0 to 1] | 14% [10 to 20] | 0% [0 to 2] |
| f_raw | 9% [7 to 13] | 1% [0 to 2] | 1% [1 to 3] | 0% [0 to 1] | 22% [17 to 29] | 18% [13 to 24] |
| g_struck | 9% [6 to 12] | 1% [0 to 2] | 0% [0 to 2] | 0% [0 to 2] | 25% [19 to 32] | 18% [13 to 24] |

## Planned comparisons (exact McNemar on paired decisions, Holm over 16)

Pairs match session, probe, and sample index. The difference CI is a session-cluster bootstrap (2,000 resamples), which allows for repeated samples and probes within a session.

| # | A | B | type (pairs) | A | B | A-only / B-only | diff [cluster 95% CI] | raw p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| 1 | a_delete (clean) | b_ledger (clean) | revoked (360) | 94% | 85% | 46 / 14 | +9 [+4 to +13] | 4e-05 | 5e-04 |
| 2 | c_permit (clean) | b_ledger (clean) | revoked (360) | 98% | 85% | 52 / 7 | +12 [+8 to +17] | 1e-09 | 2e-08 |
| 3 | d_label (clean) | b_ledger (clean) | revoked (360) | 93% | 85% | 43 / 15 | +8 [+4 to +12] | 3e-04 | 0.003 |
| 4 | c_permit (clean) | a_delete (clean) | revoked (360) | 98% | 94% | 18 / 5 | +4 [+1 to +7] | 0.011 | 0.085 |
| 5 | g_struck (clean) | f_raw (clean) | revoked (360) | 95% | 91% | 28 / 13 | +4 [-0 to +9] | 0.028 | 0.19 |
| 6 | a_delete (clean) | f_raw (clean) | revoked (360) | 94% | 91% | 30 / 20 | +3 [-2 to +8] | 0.20 | 1.00 |
| 7 | b_ledger (clean) | a_delete (clean) | active (360) | 100% | 100% | 0 / 1 | -0 [-1 to +0] | 1.00 | 1.00 |
| 8 | c_permit (clean) | a_delete (clean) | active (360) | 100% | 100% | 0 / 0 | +0 [+0 to +0] | 1.00 | 1.00 |
| 9 | e_wasnow (clean) | a_delete (clean) | amended (360) | 94% | 89% | 27 / 8 | +5 [+2 to +9] | 0.002 | 0.017 |
| 10 | b_ledger (clean) | a_delete (clean) | amended (360) | 90% | 89% | 25 / 20 | +1 [-4 to +6] | 0.55 | 1.00 |
| 11 | a_delete (stale) | a_delete (clean) | revoked (360) | 4% | 94% | 1 / 323 | -89 [-92 to -86] | <1e-15 | <1e-15 |
| 12 | c_permit (stale) | a_delete (stale) | revoked (360) | 96% | 4% | 332 / 1 | +92 [+89 to +95] | <1e-15 | <1e-15 |
| 13 | d_label (stale) | a_delete (stale) | revoked (360) | 89% | 4% | 305 / 0 | +85 [+81 to +89] | <1e-15 | <1e-15 |
| 14 | c_permit (stale) | d_label (stale) | revoked (360) | 96% | 89% | 36 / 10 | +7 [+4 to +11] | 2e-04 | 0.002 |
| 15 | g_struck (stale) | f_raw (stale) | revoked (360) | 90% | 90% | 22 / 20 | +1 [-3 to +4] | 0.88 | 1.00 |
| 16 | e_wasnow (stale) | a_delete (stale) | amended (360) | 93% | 91% | 21 / 15 | +2 [-2 to +5] | 0.41 | 1.00 |

## Sensitivity: revoked items with hand-edited permissions removed (exploratory)

Removed items: r006, r007, r011, r022, r036. Same pairing and tests as above, unadjusted p.

| A | B | pairs | A | B | A-only / B-only | p |
|---|---|---|---|---|---|---|
| c_permit (clean) | a_delete (clean) | 288 | 98% | 94% | 12 / 3 | 0.035 |
| c_permit (clean) | b_ledger (clean) | 288 | 98% | 86% | 39 / 5 | 1e-07 |
| c_permit (clean) | d_label (clean) | 288 | 98% | 94% | 15 / 6 | 0.078 |
| c_permit (stale) | d_label (stale) | 288 | 97% | 94% | 17 / 8 | 0.11 |
| c_permit (clean) | f_raw (clean) | 288 | 98% | 97% | 7 / 5 | 0.77 |
| c_permit (stale) | f_raw (stale) | 288 | 97% | 96% | 11 / 9 | 0.82 |

## Secondary: DECISION line only, clean summary

| format | active | revoked | loosen | tighten | amended | rule_state |
|---|---|---|---|---|---|---|
| none | 11% [8 to 14] | 92% [88 to 94] | 87% [82 to 91] | 27% [21 to 34] | 57% [52 to 62] | 53% [50 to 56] |
| a_delete | 91% [87 to 93] | 94% [91 to 96] | 83% [77 to 88] | 74% [68 to 80] | 79% [74 to 83] | 88% [86 to 90] |
| b_ledger | 87% [83 to 90] | 86% [82 to 89] | 85% [79 to 89] | 66% [59 to 73] | 76% [71 to 80] | 83% [80 to 85] |
| c_permit | 89% [86 to 92] | 98% [96 to 99] | 82% [75 to 87] | 72% [65 to 78] | 77% [72 to 81] | 88% [86 to 90] |
| d_label | 90% [86 to 92] | 94% [91 to 96] | 79% [72 to 84] | 71% [64 to 77] | 75% [70 to 79] | 86% [84 to 88] |
| e_wasnow | 91% [88 to 94] | 90% [87 to 93] | 90% [85 to 94] | 68% [61 to 75] | 79% [75 to 83] | 87% [85 to 89] |
| f_raw | 90% [87 to 93] | 92% [89 to 95] | 82% [75 to 87] | 45% [38 to 52] | 63% [58 to 68] | 82% [80 to 84] |
| g_struck | 87% [83 to 90] | 93% [90 to 95] | 81% [75 to 86] | 49% [42 to 56] | 65% [60 to 70] | 82% [79 to 84] |

## Secondary: DECISION line only, stale summary

| format | active | revoked | loosen | tighten | amended | rule_state |
|---|---|---|---|---|---|---|
| none | 91% [87 to 93] | 12% [9 to 16] | 34% [28 to 42] | 13% [9 to 19] | 24% [20 to 29] | 42% [39 to 45] |
| a_delete | 93% [90 to 95] | 12% [9 to 16] | 86% [80 to 90] | 68% [61 to 75] | 77% [73 to 81] | 61% [58 to 64] |
| b_ledger | 89% [86 to 92] | 87% [83 to 90] | 92% [87 to 95] | 66% [58 to 72] | 79% [74 to 83] | 85% [83 to 87] |
| c_permit | 92% [89 to 94] | 96% [94 to 98] | 89% [83 to 93] | 63% [56 to 70] | 76% [71 to 80] | 88% [86 to 90] |
| d_label | 90% [86 to 93] | 89% [86 to 92] | 84% [78 to 89] | 63% [56 to 70] | 74% [69 to 78] | 84% [82 to 86] |
| e_wasnow | 92% [89 to 94] | 14% [11 to 18] | 88% [83 to 92] | 72% [65 to 78] | 80% [76 to 84] | 62% [59 to 65] |
| f_raw | 90% [86 to 93] | 90% [87 to 93] | 83% [77 to 88] | 51% [44 to 58] | 67% [62 to 72] | 82% [80 to 85] |
| g_struck | 91% [88 to 94] | 90% [86 to 92] | 79% [73 to 85] | 51% [43 to 58] | 65% [60 to 70] | 82% [80 to 84] |

Judge and DECISION line agree on: active 91%, revoked 97%, amended 82%

## Tokens per format (word count x 1.33)

| format | mean block tokens | mean full context tokens (clean) |
|---|---|---|
| none | 0 | 520 |
| a_delete | 224 | 743 |
| b_ledger | 516 | 1035 |
| c_permit | 329 | 848 |
| d_label | 335 | 855 |
| e_wasnow | 293 | 813 |
| f_raw | 396 | 916 |
| g_struck | 316 | 835 |

## Revoked accuracy by item (exploratory, clean / stale)

| item | n per cell | a_delete | b_ledger | c_permit | d_label | e_wasnow | f_raw | g_struck |
|---|---|---|---|---|---|---|---|---|
| r000 | 10 | 10/10 0/10 | 10/10 10/10 | 10/10 10/10 | 10/10 10/10 | 10/10 0/10 | 10/10 10/10 | 10/10 10/10 |
| r001 | 8 | 8/8 0/8 | 6/8 7/8 | 8/8 8/8 | 8/8 8/8 | 8/8 0/8 | 8/8 8/8 | 8/8 8/8 |
| r002 | 14 | 14/14 0/14 | 1/14 11/14 | 14/14 14/14 | 12/14 14/14 | 14/14 0/14 | 14/14 14/14 | 14/14 14/14 |
| r003 | 8 | 8/8 0/8 | 8/8 6/8 | 8/8 8/8 | 7/8 6/8 | 8/8 0/8 | 8/8 7/8 | 8/8 8/8 |
| r004 | 18 | 18/18 2/18 | 18/18 15/18 | 17/18 18/18 | 16/18 17/18 | 18/18 0/18 | 18/18 17/18 | 18/18 17/18 |
| r005 | 4 | 4/4 0/4 | 2/4 3/4 | 4/4 3/4 | 4/4 2/4 | 4/4 0/4 | 4/4 4/4 | 4/4 4/4 |
| r006 | 20 | 20/20 0/20 | 19/20 16/20 | 20/20 20/20 | 19/20 17/20 | 18/20 0/20 | 20/20 18/20 | 19/20 18/20 |
| r007 | 8 | 8/8 1/8 | 8/8 8/8 | 8/8 8/8 | 8/8 8/8 | 7/8 1/8 | 1/8 2/8 | 4/8 1/8 |
| r010 | 8 | 7/8 0/8 | 3/8 6/8 | 8/8 8/8 | 7/8 7/8 | 8/8 0/8 | 8/8 7/8 | 8/8 8/8 |
| r011 | 10 | 8/10 0/10 | 5/10 4/10 | 10/10 10/10 | 8/10 8/10 | 7/10 0/10 | 10/10 9/10 | 10/10 10/10 |
| r012 | 18 | 18/18 6/18 | 17/18 18/18 | 18/18 18/18 | 18/18 18/18 | 18/18 7/18 | 18/18 18/18 | 18/18 18/18 |
| r014 | 8 | 6/8 1/8 | 7/8 7/8 | 8/8 8/8 | 7/8 5/8 | 5/8 0/8 | 8/8 8/8 | 5/8 5/8 |
| r015 | 10 | 9/10 0/10 | 10/10 10/10 | 10/10 10/10 | 10/10 10/10 | 8/10 0/10 | 10/10 10/10 | 7/10 10/10 |
| r016 | 4 | 4/4 0/4 | 4/4 4/4 | 4/4 4/4 | 4/4 4/4 | 4/4 0/4 | 4/4 4/4 | 4/4 4/4 |
| r018 | 10 | 6/10 0/10 | 9/10 6/10 | 10/10 10/10 | 10/10 9/10 | 6/10 0/10 | 10/10 10/10 | 10/10 10/10 |
| r020 | 12 | 12/12 0/12 | 12/12 12/12 | 12/12 12/12 | 12/12 12/12 | 12/12 0/12 | 11/12 11/12 | 12/12 12/12 |
| r022 | 8 | 6/8 0/8 | 4/8 6/8 | 6/8 8/8 | 4/8 2/8 | 6/8 0/8 | 6/8 8/8 | 5/8 8/8 |
| r024 | 14 | 14/14 1/14 | 14/14 14/14 | 14/14 14/14 | 14/14 14/14 | 13/14 1/14 | 14/14 14/14 | 14/14 13/14 |
| r025 | 16 | 16/16 0/16 | 15/16 16/16 | 16/16 16/16 | 16/16 16/16 | 16/16 0/16 | 16/16 16/16 | 16/16 15/16 |
| r026 | 10 | 10/10 0/10 | 4/10 8/10 | 10/10 10/10 | 9/10 10/10 | 10/10 0/10 | 10/10 10/10 | 10/10 10/10 |
| r027 | 10 | 10/10 3/10 | 10/10 9/10 | 10/10 9/10 | 10/10 8/10 | 10/10 3/10 | 10/10 10/10 | 10/10 10/10 |
| r028 | 8 | 8/8 0/8 | 8/8 7/8 | 8/8 7/8 | 8/8 8/8 | 8/8 0/8 | 5/8 6/8 | 8/8 6/8 |
| r029 | 6 | 6/6 0/6 | 4/6 6/6 | 6/6 5/6 | 5/6 6/6 | 5/6 0/6 | 6/6 6/6 | 5/6 5/6 |
| r030 | 10 | 10/10 0/10 | 10/10 10/10 | 10/10 10/10 | 10/10 10/10 | 10/10 0/10 | 10/10 10/10 | 10/10 10/10 |
| r031 | 2 | 2/2 0/2 | 2/2 2/2 | 2/2 2/2 | 2/2 2/2 | 2/2 0/2 | 2/2 2/2 | 2/2 2/2 |
| r032 | 12 | 5/12 2/12 | 9/12 10/12 | 6/12 7/12 | 8/12 10/12 | 9/12 1/12 | 9/12 11/12 | 11/12 11/12 |
| r034 | 12 | 12/12 0/12 | 11/12 12/12 | 12/12 12/12 | 12/12 12/12 | 12/12 0/12 | 12/12 12/12 | 12/12 12/12 |
| r035 | 14 | 14/14 0/14 | 13/14 12/14 | 14/14 14/14 | 14/14 13/14 | 13/14 0/14 | 14/14 14/14 | 14/14 14/14 |
| r036 | 26 | 24/26 0/26 | 23/26 12/26 | 26/26 22/26 | 23/26 16/26 | 21/26 0/26 | 12/26 9/26 | 25/26 12/26 |
| r037 | 18 | 18/18 0/18 | 18/18 17/18 | 18/18 18/18 | 18/18 17/18 | 18/18 0/18 | 16/18 16/18 | 18/18 16/18 |
| r038 | 8 | 8/8 0/8 | 7/8 8/8 | 8/8 8/8 | 8/8 7/8 | 8/8 0/8 | 8/8 7/8 | 8/8 8/8 |
| r039 | 12 | 11/12 0/12 | 12/12 11/12 | 12/12 12/12 | 10/12 11/12 | 11/12 0/12 | 12/12 11/12 | 12/12 12/12 |
| r041 | 4 | 4/4 0/4 | 3/4 4/4 | 4/4 4/4 | 3/4 4/4 | 4/4 0/4 | 4/4 4/4 | 4/4 4/4 |

## Judge validation (blind hand labels by the study agent)

n = 48, agreement 100%, Cohen's kappa 1.00

| judge \ hand | APPLIES | IGNORES | OTHER |
|---|---|---|---|
| APPLIES | 16 | 0 | 0 |
| IGNORES | 0 | 16 | 0 |
| OTHER | 0 | 0 | 16 |
