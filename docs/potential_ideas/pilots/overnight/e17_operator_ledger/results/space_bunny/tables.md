# E17 tables (stealth/space-bunny-alpha), 60 sessions

## Correct rate by probe type and arm (Wilson 95% CI)

| arm | active | revoked | amended | rule_state | goal | plan | fact_current | fact_history | overall |
|---|---|---|---|---|---|---|---|---|---|
| floor | 3% [2 to 7] | 92% [87 to 95] | 42% [34 to 51] | 46% [42 to 51] | 0% [0 to 6] | 0% [0 to 6] | 0% [0 to 3] | 0% [0 to 3] | 27% [24 to 30] |
| full | 92% [87 to 95] | 93% [88 to 96] | 76% [67 to 83] | 88% [85 to 91] | 80% [68 to 88] | 93% [84 to 97] | 100% [97 to 100] | 88% [81 to 93] | 90% [88 to 92] |
| plain | 7% [4 to 11] | 95% [91 to 97] | 48% [40 to 57] | 50% [46 to 55] | 30% [20 to 43] | 7% [3 to 16] | 44% [36 to 53] | 0% [0 to 3] | 38% [34 to 41] |
| structured | 98% [95 to 99] | 77% [70 to 82] | 75% [67 to 82] | 84% [81 to 87] | 28% [19 to 41] | 13% [7 to 24] | 61% [52 to 69] | 12% [8 to 20] | 62% [58 to 65] |
| structured_full | 98% [94 to 99] | 89% [83 to 93] | 85% [78 to 90] | 91% [88 to 93] | 58% [46 to 70] | 33% [23 to 46] | 98% [93 to 99] | 61% [52 to 69] | 81% [79 to 84] |
| pin_raw | 97% [94 to 99] | 90% [85 to 94] | 73% [65 to 80] | 89% [85 to 91] | 55% [42 to 67] | 47% [35 to 59] | 100% [97 to 100] | 91% [84 to 95] | 85% [83 to 87] |
| ledger | 99% [97 to 100] | 81% [74 to 86] | 94% [88 to 97] | 91% [88 to 93] | 98% [91 to 100] | 35% [24 to 48] | 100% [97 to 100] | 80% [72 to 86] | 87% [85 to 89] |
| ledger_norev | 99% [97 to 100] | 85% [79 to 89] | 91% [84 to 95] | 92% [89 to 94] | 100% [94 to 100] | 37% [26 to 49] | 100% [97 to 100] | 81% [73 to 87] | 88% [86 to 90] |
| ledger_noframe | 100% [98 to 100] | 59% [52 to 66] | 82% [75 to 88] | 80% [76 to 84] | 90% [80 to 95] | 32% [21 to 44] | 99% [95 to 100] | 82% [74 to 88] | 80% [78 to 83] |
| ledger_oracle | 99% [97 to 100] | 86% [80 to 90] | 92% [86 to 96] | 92% [90 to 95] | 100% [94 to 100] | 28% [19 to 41] | 99% [95 to 100] | 80% [72 to 86] | 88% [85 to 90] |
| pin_rules | 99% [97 to 100] | 3% [1 to 6] | 14% [9 to 22] | 42% [38 to 46] | 32% [21 to 44] | 7% [3 to 16] | 43% [35 to 52] | 1% [0 to 5] | 33% [30 to 36] |

## Amended rules by direction

| arm | loosen (expect COMPLY) | tighten (expect REFUSE) |
|---|---|---|
| floor | 82% [70 to 89] | 3% [1 to 11] |
| full | 75% [63 to 84] | 77% [65 to 86] |
| plain | 83% [72 to 91] | 13% [7 to 24] |
| structured | 70% [57 to 80] | 80% [68 to 88] |
| structured_full | 78% [66 to 87] | 92% [82 to 96] |
| pin_raw | 72% [59 to 81] | 75% [63 to 84] |
| ledger | 92% [82 to 96] | 97% [89 to 99] |
| ledger_norev | 85% [74 to 92] | 97% [89 to 99] |
| ledger_noframe | 70% [57 to 80] | 95% [86 to 98] |
| ledger_oracle | 90% [80 to 95] | 95% [86 to 98] |
| pin_rules | 3% [1 to 11] | 25% [16 to 37] |

## Rule probes scored by the DECISION line only (secondary; the convention of E1 to E15)

| arm | active | revoked | amended | rule_state |
|---|---|---|---|---|
| floor | 9% [6 to 14] | 90% [85 to 94] | 53% [44 to 62] | 50% [46 to 55] |
| full | 85% [79 to 89] | 93% [89 to 96] | 69% [60 to 77] | 84% [81 to 87] |
| plain | 11% [7 to 16] | 94% [90 to 97] | 58% [49 to 66] | 54% [49 to 58] |
| structured | 88% [83 to 92] | 77% [71 to 83] | 68% [60 to 76] | 79% [75 to 83] |
| structured_full | 87% [82 to 91] | 87% [81 to 91] | 70% [61 to 77] | 83% [79 to 86] |
| pin_raw | 86% [80 to 90] | 91% [85 to 94] | 60% [51 to 68] | 81% [78 to 84] |
| ledger | 88% [82 to 92] | 83% [77 to 88] | 79% [71 to 85] | 84% [80 to 87] |
| ledger_norev | 84% [78 to 89] | 86% [80 to 90] | 77% [68 to 83] | 83% [80 to 86] |
| ledger_noframe | 88% [83 to 92] | 63% [56 to 70] | 72% [64 to 80] | 75% [71 to 78] |
| ledger_oracle | 85% [79 to 89] | 87% [82 to 91] | 77% [68 to 83] | 84% [80 to 87] |
| pin_rules | 88% [83 to 92] | 11% [7 to 17] | 23% [17 to 32] | 43% [39 to 48] |

Agreement of judged action and DECISION line on rule probes: active 89%, revoked 97%, amended 83%

## Judge labels per probe type (counts)


active

| arm | APPLIES | IGNORES | OTHER |
|---|---|---|---|
| floor | 6 | 163 | 11 |
| full | 166 | 14 | 0 |
| plain | 12 | 159 | 9 |
| structured | 177 | 2 | 1 |
| structured_full | 176 | 4 | 0 |
| pin_raw | 175 | 4 | 1 |
| ledger | 179 | 1 | 0 |
| ledger_norev | 179 | 1 | 0 |
| ledger_noframe | 180 | 0 | 0 |
| ledger_oracle | 179 | 1 | 0 |
| pin_rules | 179 | 1 | 0 |

revoked

| arm | APPLIES | IGNORES | OTHER |
|---|---|---|---|
| floor | 9 | 166 | 5 |
| full | 13 | 167 | 0 |
| plain | 5 | 171 | 4 |
| structured | 35 | 138 | 7 |
| structured_full | 10 | 160 | 10 |
| pin_raw | 18 | 162 | 0 |
| ledger | 30 | 145 | 5 |
| ledger_norev | 18 | 153 | 9 |
| ledger_noframe | 72 | 106 | 2 |
| ledger_oracle | 24 | 154 | 2 |
| pin_rules | 175 | 5 | 0 |

amended

| arm | APPLIES | IGNORES | OTHER |
|---|---|---|---|
| floor | 3 | 94 | 23 |
| full | 60 | 58 | 2 |
| plain | 10 | 90 | 20 |
| structured | 63 | 50 | 7 |
| structured_full | 67 | 52 | 1 |
| pin_raw | 61 | 56 | 3 |
| ledger | 63 | 57 | 0 |
| ledger_norev | 66 | 53 | 1 |
| ledger_noframe | 74 | 45 | 1 |
| ledger_oracle | 62 | 56 | 2 |
| pin_rules | 73 | 44 | 3 |

goal

| arm | current | none | procedure | stale |
|---|---|---|---|---|
| floor | 0 | 58 | 0 | 2 |
| full | 48 | 4 | 4 | 4 |
| plain | 18 | 24 | 9 | 9 |
| structured | 17 | 25 | 6 | 12 |
| structured_full | 35 | 8 | 16 | 1 |
| pin_raw | 33 | 20 | 0 | 7 |
| ledger | 59 | 1 | 0 | 0 |
| ledger_norev | 60 | 0 | 0 | 0 |
| ledger_noframe | 54 | 6 | 0 | 0 |
| ledger_oracle | 60 | 0 | 0 | 0 |
| pin_rules | 19 | 30 | 7 | 4 |

plan

| arm | correct_next | other | repeat | skip | verify |
|---|---|---|---|---|---|
| floor | 0 | 52 | 1 | 2 | 5 |
| full | 56 | 0 | 4 | 0 | 0 |
| plain | 4 | 32 | 9 | 4 | 11 |
| structured | 8 | 43 | 5 | 3 | 1 |
| structured_full | 20 | 25 | 5 | 6 | 4 |
| pin_raw | 28 | 0 | 27 | 5 | 0 |
| ledger | 21 | 1 | 29 | 8 | 1 |
| ledger_norev | 22 | 2 | 33 | 3 | 0 |
| ledger_noframe | 19 | 3 | 30 | 8 | 0 |
| ledger_oracle | 17 | 0 | 32 | 11 | 0 |
| pin_rules | 4 | 37 | 5 | 7 | 7 |

fact_current

| arm | correct | stale | wrong |
|---|---|---|---|
| floor | 0 | 0 | 120 |
| full | 120 | 0 | 0 |
| plain | 53 | 1 | 66 |
| structured | 73 | 4 | 43 |
| structured_full | 117 | 1 | 2 |
| pin_raw | 120 | 0 | 0 |
| ledger | 120 | 0 | 0 |
| ledger_norev | 120 | 0 | 0 |
| ledger_noframe | 119 | 0 | 1 |
| ledger_oracle | 119 | 0 | 1 |
| pin_rules | 52 | 1 | 67 |

fact_history

| arm | correct | stale | wrong |
|---|---|---|---|
| floor | 0 | 0 | 120 |
| full | 106 | 13 | 1 |
| plain | 0 | 4 | 116 |
| structured | 15 | 11 | 94 |
| structured_full | 73 | 18 | 29 |
| pin_raw | 109 | 11 | 0 |
| ledger | 96 | 22 | 2 |
| ledger_norev | 97 | 20 | 3 |
| ledger_noframe | 98 | 19 | 3 |
| ledger_oracle | 96 | 24 | 0 |
| pin_rules | 1 | 8 | 111 |

## Pre-specified paired comparisons (exact McNemar, Holm over all 15)

| A | B | probes | A correct | B correct | A-only / B-only | p | Holm p |
|---|---|---|---|---|---|---|---|
| ledger | plain | rule_state (n = 480) | 91% | 50% | 233 / 37 | 6e-36 | 9e-35 |
| ledger | structured | rule_state (n = 480) | 91% | 84% | 59 / 27 | 7e-04 | 0.0066 |
| ledger | pin_raw | revoked (n = 180) | 81% | 90% | 10 / 27 | 0.0076 | 0.061 |
| ledger | pin_raw | active (n = 180) | 99% | 97% | 5 / 1 | 0.22 | 1 |
| ledger | pin_raw | amended (n = 120) | 94% | 73% | 30 / 5 | 2e-05 | 2e-04 |
| ledger | structured | revoked (n = 180) | 81% | 77% | 30 / 23 | 0.41 | 1 |
| ledger | ledger_norev | revoked (n = 180) | 81% | 85% | 16 / 24 | 0.27 | 1 |
| ledger | ledger_noframe | active (n = 180) | 99% | 100% | 0 / 1 | 1 | 1 |
| ledger | ledger_noframe | rule_state (n = 480) | 91% | 80% | 61 / 9 | 1e-10 | 2e-09 |
| ledger | structured_full | rule_state (n = 480) | 91% | 91% | 33 / 34 | 1 | 1 |
| ledger | full | rule_state (n = 480) | 91% | 88% | 50 / 37 | 0.2 | 1 |
| ledger | ledger_oracle | rule_state (n = 480) | 91% | 92% | 23 / 30 | 0.41 | 1 |
| ledger | plain | goal (n = 60) | 98% | 30% | 41 / 0 | 9e-13 | 1e-11 |
| ledger | plain | plan (n = 60) | 35% | 7% | 17 / 0 | 2e-05 | 2e-04 |
| ledger | plain | fact_history (n = 120) | 80% | 0% | 96 / 0 | 3e-29 | 4e-28 |

## Exploratory paired comparisons (not corrected)

| A | B | probes | A | B | A-only / B-only | p |
|---|---|---|---|---|---|---|
| structured_full | structured | revoked (n = 180) | 89% | 77% | 31 / 9 | 7e-04 |
| structured_full | plain | rule_state (n = 480) | 91% | 50% | 225 / 28 | 2e-39 |
| pin_raw | plain | rule_state (n = 480) | 89% | 50% | 214 / 30 | 2e-35 |
| pin_raw | full | revoked (n = 180) | 90% | 93% | 8 / 13 | 0.38 |
| structured | plain | revoked (n = 180) | 77% | 95% | 7 / 40 | 1e-06 |
| ledger_noframe | ledger_norev | rule_state (n = 480) | 80% | 92% | 18 / 74 | 3e-09 |
| ledger | pin_raw | overall (n = 840) | 87% | 85% | 78 / 60 | 0.15 |
| ledger | structured_full | overall (n = 840) | 87% | 81% | 109 / 59 | 1e-04 |
| ledger | full | overall (n = 840) | 87% | 90% | 73 / 94 | 0.12 |
| ledger_oracle | pin_raw | rule_state (n = 480) | 92% | 89% | 45 / 26 | 0.032 |
| ledger | pin_rules | revoked (n = 180) | 81% | 3% | 140 / 0 | 1e-42 |
| ledger | pin_rules | rule_state (n = 480) | 91% | 42% | 238 / 2 | 3e-68 |
| pin_raw | pin_rules | revoked (n = 180) | 90% | 3% | 157 / 0 | 1e-47 |
| pin_rules | plain | active (n = 180) | 99% | 7% | 167 / 0 | 1e-50 |

## Context size and cost

| arm | mean context tokens (est.) | extra block tokens | extra model calls per session |
|---|---|---|---|
| floor | 215 | 0 | 0 |
| full | 5451 | 0 | 0 |
| plain | 520 | 0 | 10.2 |
| structured | 659 | 0 | 10.2 |
| structured_full | 704 | 0 | 10.2 |
| pin_raw | 1311 | 792 | 10.2 (plain compaction) |
| ledger | 1451 | 932 | 10.2 + 22.7 ledger updates |
| ledger_norev | 1186 | 666 | 10.2 + 22.7 ledger updates |
| ledger_noframe | 1350 | 830 | 10.2 + 22.7 ledger updates |
| ledger_oracle | 1416 | 897 | 10.2 (oracle needs labels) |
| pin_rules | 741 | 222 | 10.2 (plain compaction) |

Mean final summary words (budget 250): plain 222, structured 327, structured_full 361

Mean operator turns per session: 22.7; mean session length 152 turns.

## Ledger growth (rendered ledger tokens after the k-th operator turn, mean over sessions)

| operator turn k | ledger tokens | pin_raw tokens so far |
|---|---|---|
| 1 | 108 | 36 |
| 5 | 233 | 121 |
| 10 | 389 | 239 |
| 15 | 756 | 538 |
| 20 | 885 | 671 |
| 24 | 930 | 761 |

Final ledger 932 tokens (range 689 to 1342), oracle ledger 897, pin_raw 792.

## Ledger maintenance errors (final ledger vs ground truth, automatic audit)

| check | errors |
|---|---|
| active_missing | 0/180 |
| revoked_still_active | 8/180 |
| revoked_not_logged | 24/180 |
| amended_missing | 12/120 |
| amended_not_updated | 3/120 |
| objective_wrong | 0/60 |
| plan_missing | 2/60 |
| fact_current_wrong | 0/120 |
| fact_orphan | 0/120 |
| fact_history_missing | 3/120 |

Failed ledger update calls (no valid JSON, old ledger kept): 0/1360.

## Ledger arm outcome by ledger correctness for that rule (exploratory)

| probe | ledger entry correct | ledger entry wrong |
|---|---|---|
| active | 99% [97 to 100] | n/a |
| revoked | 83% [77 to 88] | 25% [7 to 59] |
| amended | 97% [92 to 99] | 73% [48 to 89] |

## Judge validation against blind hand labels

| judge | n | agreement | Cohen's kappa |
|---|---|---|---|
| fact | 20 | 100% | 1.00 |
| goal | 40 | 100% | 1.00 |
| plan | 40 | 98% | 0.95 |
| rule | 44 | 95% | 0.92 |
