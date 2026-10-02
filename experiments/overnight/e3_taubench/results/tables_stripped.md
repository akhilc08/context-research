# E3 results (retail), files: results/stripped.jsonl

Runs dropped because the model provider failed mid-run: 0

| arm | runs | tasks | mean reward | 95% CI (Wilson, runs) | pass^1 | pass^2 | errors | max-steps | agent calls/run | all calls/run | input tok/run | output tok/run | compactions/run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nopolicy | 115 | 115 | 0.617 (71/115) | 0.526 to 0.701 | 0.617 | n/a | 0 | 0 | 11.9 | 17.3 | 57,537 | 1,180 | 0.00 |
| hist | 115 | 115 | 0.643 (74/115) | 0.553 to 0.725 | 0.643 | n/a | 0 | 0 | 12.3 | 18.4 | 75,873 | 1,170 | 0.00 |
| compact | 115 | 115 | 0.557 (64/115) | 0.465 to 0.644 | 0.557 | n/a | 0 | 1 | 13.4 | 21.2 | 73,508 | 1,947 | 1.98 |
| pin | 115 | 115 | 0.652 (75/115) | 0.561 to 0.733 | 0.652 | n/a | 0 | 2 | 13.3 | 21.3 | 80,389 | 1,727 | 1.97 |
| watch | 115 | 115 | 0.643 (74/115) | 0.553 to 0.725 | 0.643 | n/a | 0 | 2 | 13.6 | 60.7 | 116,336 | 4,747 | 2.05 |

## Paired comparisons (exact sign test on per-task mean reward over shared trials; Holm across planned family)

| comparison | shared tasks | a better | b better | ties | mean a | mean b | diff (95% paired bootstrap CI) | raw p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| compact vs hist | 115 | 13 | 23 | 79 | 0.557 | 0.643 | -0.087 (-0.183 to +0.017) | 0.132 | 0.397 |
| pin vs compact | 115 | 20 | 9 | 86 | 0.652 | 0.557 | +0.096 (+0.009 to +0.183) | 0.0614 | 0.246 |
| watch vs compact | 115 | 24 | 14 | 77 | 0.643 | 0.557 | +0.087 (-0.017 to +0.191) | 0.143 | 0.397 |
| watch vs pin | 115 | 18 | 19 | 78 | 0.643 | 0.652 | -0.009 (-0.104 to +0.096) | 1 | 1 |

## Exposure: compaction before the first database write (compaction arms)

| arm | runs with a write | compaction before first write | reward when exposed | reward when not exposed |
|---|---|---|---|---|
| compact | 101 | 100 | 0.580 (n=100) | 0.000 (n=1) |
| pin | 99 | 99 | 0.657 (n=99) | n/a |
| watch | 101 | 101 | 0.644 (n=101) | n/a |

## Heuristic policy-violation flags (share of runs with at least one)

| arm | write_before_auth | write_without_user_yes | repeat_item_call_same_order | transfer_to_human |
|---|---|---|---|---|
| nopolicy | 0.052 | 0.487 | 0.000 | 0.235 |
| hist | 0.000 | 0.043 | 0.000 | 0.139 |
| compact | 0.000 | 0.261 | 0.000 | 0.243 |
| pin | 0.000 | 0.087 | 0.000 | 0.174 |
| watch | 0.000 | 0.078 | 0.000 | 0.191 |

## Exploratory: paired comparison of the 'write without an explicit user yes' flag

Per task, share of runs flagged (averaged over shared trials); exact sign test; Holm across rows.

| comparison | shared tasks | a flagged more | b flagged more | rate a | rate b | raw p | Holm p |
|---|---|---|---|---|---|---|---|
| compact vs hist | 115 | 27 | 2 | 0.261 | 0.043 | 1.62e-06 | 6.5e-06 |
| pin vs compact | 115 | 5 | 25 | 0.087 | 0.261 | 0.000325 | 0.000972 |
| watch vs compact | 115 | 6 | 27 | 0.078 | 0.261 | 0.000324 | 0.000972 |
| watch vs pin | 115 | 7 | 8 | 0.078 | 0.087 | 1 | 1 |

## Failure source (runs with reward 0)

| arm | failed | wrong DB state | DB right but missing required output | agent error | max steps |
|---|---|---|---|---|---|
| nopolicy | 44 | 27 | 17 | 0 | 0 |
| hist | 41 | 26 | 15 | 0 | 0 |
| compact | 51 | 33 | 17 | 0 | 1 |
| pin | 40 | 27 | 11 | 0 | 2 |
| watch | 41 | 24 | 15 | 0 | 2 |

## Watchpoint (watch)

- compactions checked: 236; with at least one rule patched: 236 (1.000); mean rules missing per check: 10.34 of 18
- runs with a compaction: 115; runs with at least one patch: 115
- per-rule miss rate (rule index: share of checks): R0: 0.47, R1: 0.63, R2: 0.29, R3: 0.69, R4: 0.93, R5: 0.22, R6: 0.43, R7: 0.78, R8: 0.18, R9: 0.60, R10: 0.50, R11: 0.98, R12: 0.83, R13: 0.31, R14: 0.70, R15: 0.62, R16: 0.77, R17: 0.42
