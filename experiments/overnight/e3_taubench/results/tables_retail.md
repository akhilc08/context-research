# E3 results (retail), files: results/main.jsonl

Runs dropped because the model provider failed mid-run: 0

| arm | runs | tasks | mean reward | 95% CI (Wilson, runs) | pass^1 | pass^2 | errors | max-steps | agent calls/run | all calls/run | input tok/run | output tok/run | compactions/run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nopolicy | 230 | 115 | 0.648 (149/230) | 0.584 to 0.707 | 0.648 | 0.548 (n=115) | 0 | 1 | 12.5 | 18.5 | 65,734 | 1,246 | 0.00 |
| standard | 230 | 115 | 0.626 (144/230) | 0.562 to 0.686 | 0.626 | 0.487 (n=115) | 0 | 0 | 12.6 | 18.8 | 80,780 | 1,207 | 0.00 |
| hist | 230 | 115 | 0.657 (151/230) | 0.593 to 0.715 | 0.657 | 0.530 (n=115) | 0 | 0 | 12.7 | 19.0 | 81,953 | 1,245 | 0.00 |
| compact | 230 | 115 | 0.626 (144/230) | 0.562 to 0.686 | 0.626 | 0.504 (n=115) | 0 | 4 | 14.0 | 22.4 | 75,109 | 1,873 | 2.06 |
| pin | 230 | 115 | 0.626 (144/230) | 0.562 to 0.686 | 0.626 | 0.504 (n=115) | 0 | 3 | 13.8 | 22.2 | 85,623 | 1,759 | 2.09 |
| pinrules | 230 | 115 | 0.600 (138/230) | 0.536 to 0.661 | 0.600 | 0.478 (n=115) | 0 | 3 | 13.7 | 22.1 | 78,614 | 1,784 | 2.05 |
| watch | 230 | 115 | 0.570 (131/230) | 0.505 to 0.632 | 0.570 | 0.443 (n=115) | 0 | 5 | 13.7 | 60.9 | 115,798 | 4,601 | 2.04 |
| watch_ctx | 230 | 115 | 0.613 (141/230) | 0.549 to 0.674 | 0.613 | 0.470 (n=115) | 0 | 2 | 14.1 | 60.0 | 115,379 | 3,219 | 2.07 |

## Paired comparisons (exact sign test on per-task mean reward over shared trials; Holm across planned family)

| comparison | shared tasks | a better | b better | ties | mean a | mean b | diff (95% paired bootstrap CI) | raw p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| compact vs hist | 115 | 19 | 25 | 71 | 0.626 | 0.657 | -0.030 (-0.100 to +0.035) | 0.451 | 1 |
| hist vs standard | 115 | 23 | 18 | 74 | 0.657 | 0.626 | +0.030 (-0.035 to +0.096) | 0.533 | 1 |
| pin vs compact | 115 | 21 | 21 | 73 | 0.626 | 0.626 | +0.000 (-0.065 to +0.065) | 1 | 1 |
| pinrules vs compact | 115 | 18 | 23 | 74 | 0.600 | 0.626 | -0.026 (-0.087 to +0.039) | 0.533 | 1 |
| watch vs compact | 115 | 17 | 27 | 71 | 0.570 | 0.626 | -0.057 (-0.130 to +0.013) | 0.174 | 1 |
| watch vs pin | 115 | 17 | 28 | 70 | 0.570 | 0.626 | -0.057 (-0.122 to +0.009) | 0.135 | 1 |
| watch vs pinrules | 115 | 21 | 26 | 68 | 0.570 | 0.600 | -0.030 (-0.100 to +0.035) | 0.56 | 1 |
| watch_ctx vs compact | 115 | 26 | 28 | 61 | 0.613 | 0.626 | -0.013 (-0.091 to +0.065) | 0.892 | 1 |
| watch vs watch_ctx | 115 | 20 | 29 | 66 | 0.570 | 0.613 | -0.043 (-0.117 to +0.030) | 0.253 | 1 |
| nopolicy vs standard | 115 | 16 | 15 | 84 | 0.648 | 0.626 | +0.022 (-0.039 to +0.083) | 1 | 1 |

## Exposure: compaction before the first database write (compaction arms)

| arm | runs with a write | compaction before first write | reward when exposed | reward when not exposed |
|---|---|---|---|---|
| compact | 205 | 203 | 0.626 (n=203) | 1.000 (n=2) |
| pin | 204 | 204 | 0.618 (n=204) | n/a |
| pinrules | 202 | 202 | 0.604 (n=202) | n/a |
| watch | 202 | 202 | 0.564 (n=202) | n/a |
| watch_ctx | 203 | 203 | 0.631 (n=203) | n/a |

## Heuristic policy-violation flags (share of runs with at least one)

| arm | write_before_auth | write_without_user_yes | repeat_item_call_same_order | transfer_to_human |
|---|---|---|---|---|
| nopolicy | 0.057 | 0.083 | 0.000 | 0.178 |
| standard | 0.000 | 0.061 | 0.000 | 0.183 |
| hist | 0.000 | 0.030 | 0.000 | 0.122 |
| compact | 0.004 | 0.078 | 0.000 | 0.196 |
| pin | 0.000 | 0.048 | 0.000 | 0.165 |
| pinrules | 0.000 | 0.004 | 0.000 | 0.152 |
| watch | 0.000 | 0.039 | 0.000 | 0.191 |
| watch_ctx | 0.000 | 0.057 | 0.000 | 0.170 |

## Exploratory: paired comparison of the 'write without an explicit user yes' flag

Per task, share of runs flagged (averaged over shared trials); exact sign test; Holm across rows.

| comparison | shared tasks | a flagged more | b flagged more | rate a | rate b | raw p | Holm p |
|---|---|---|---|---|---|---|---|
| compact vs hist | 115 | 15 | 6 | 0.078 | 0.030 | 0.0784 | 0.627 |
| hist vs standard | 115 | 6 | 12 | 0.030 | 0.061 | 0.238 | 1 |
| pin vs compact | 115 | 5 | 10 | 0.048 | 0.078 | 0.302 | 1 |
| pinrules vs compact | 115 | 0 | 15 | 0.004 | 0.078 | 6.1e-05 | 0.00061 |
| watch vs compact | 115 | 8 | 15 | 0.039 | 0.078 | 0.21 | 1 |
| watch vs pin | 115 | 8 | 10 | 0.039 | 0.048 | 0.815 | 1 |
| watch vs pinrules | 115 | 9 | 1 | 0.039 | 0.004 | 0.0215 | 0.193 |
| watch_ctx vs compact | 115 | 11 | 14 | 0.057 | 0.078 | 0.69 | 1 |
| watch vs watch_ctx | 115 | 7 | 11 | 0.039 | 0.057 | 0.481 | 1 |
| nopolicy vs standard | 115 | 15 | 12 | 0.083 | 0.061 | 0.701 | 1 |

## Failure source (runs with reward 0)

| arm | failed | wrong DB state | DB right but missing required output | agent error | max steps |
|---|---|---|---|---|---|
| nopolicy | 81 | 56 | 24 | 0 | 1 |
| standard | 86 | 56 | 30 | 0 | 0 |
| hist | 79 | 53 | 26 | 0 | 0 |
| compact | 86 | 59 | 23 | 0 | 4 |
| pin | 86 | 59 | 24 | 0 | 3 |
| pinrules | 92 | 61 | 28 | 0 | 3 |
| watch | 99 | 60 | 34 | 0 | 5 |
| watch_ctx | 89 | 62 | 25 | 0 | 2 |

## Watchpoint (watch)

- compactions checked: 470; with at least one rule patched: 470 (1.000); mean rules missing per check: 10.26 of 18
- runs with a compaction: 228; runs with at least one patch: 228
- per-rule miss rate (rule index: share of checks): R0: 0.55, R1: 0.76, R2: 0.06, R3: 0.67, R4: 0.94, R5: 0.40, R6: 0.48, R7: 0.70, R8: 0.10, R9: 0.52, R10: 0.50, R11: 0.97, R12: 0.76, R13: 0.26, R14: 0.71, R15: 0.68, R16: 0.74, R17: 0.44

## Watchpoint (watch_ctx)

- compactions checked: 477; with at least one rule patched: 477 (1.000); mean rules missing per check: 10.58 of 18
- runs with a compaction: 229; runs with at least one patch: 229
- per-rule miss rate (rule index: share of checks): R0: 0.31, R1: 0.50, R2: 0.15, R3: 0.44, R4: 0.48, R5: 0.64, R6: 0.58, R7: 0.57, R8: 0.59, R9: 0.86, R10: 0.74, R11: 0.89, R12: 0.68, R13: 0.60, R14: 0.64, R15: 0.71, R16: 0.63, R17: 0.56
