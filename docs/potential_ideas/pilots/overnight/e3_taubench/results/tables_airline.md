# E3 results (airline), files: results/airline.jsonl

Runs dropped because the model provider failed mid-run: 0

| arm | runs | tasks | mean reward | 95% CI (Wilson, runs) | pass^1 | pass^2 | errors | max-steps | agent calls/run | all calls/run | input tok/run | output tok/run | compactions/run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nopolicy | 50 | 50 | 0.360 (18/50) | 0.241 to 0.499 | 0.360 | n/a | 0 | 1 | 11.3 | 16.2 | 60,394 | 1,861 | 0.00 |
| standard | 50 | 50 | 0.520 (26/50) | 0.385 to 0.652 | 0.520 | n/a | 0 | 0 | 11.4 | 17.3 | 73,782 | 1,715 | 0.00 |
| hist | 50 | 50 | 0.400 (20/50) | 0.276 to 0.538 | 0.400 | n/a | 0 | 0 | 11.5 | 17.4 | 73,477 | 1,738 | 0.00 |
| compact | 50 | 50 | 0.440 (22/50) | 0.312 to 0.577 | 0.440 | n/a | 0 | 2 | 12.8 | 20.5 | 76,487 | 2,938 | 2.00 |
| pin | 50 | 50 | 0.460 (23/50) | 0.330 to 0.596 | 0.460 | n/a | 0 | 3 | 12.9 | 20.8 | 89,464 | 2,784 | 1.96 |
| pinrules | 50 | 50 | 0.380 (19/50) | 0.259 to 0.518 | 0.380 | n/a | 0 | 1 | 11.8 | 18.8 | 74,556 | 2,502 | 1.64 |
| watch | 50 | 50 | 0.460 (23/50) | 0.330 to 0.596 | 0.460 | n/a | 0 | 0 | 10.9 | 47.8 | 131,061 | 6,608 | 1.52 |
| watch_ctx | 50 | 50 | 0.460 (23/50) | 0.330 to 0.596 | 0.460 | n/a | 0 | 0 | 11.6 | 50.1 | 142,777 | 5,240 | 1.66 |

## Paired comparisons (exact sign test on per-task mean reward over shared trials; Holm across planned family)

| comparison | shared tasks | a better | b better | ties | mean a | mean b | diff (95% paired bootstrap CI) | raw p | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| compact vs hist | 50 | 6 | 4 | 40 | 0.440 | 0.400 | +0.040 (-0.080 to +0.160) | 0.754 | 1 |
| hist vs standard | 50 | 6 | 12 | 32 | 0.400 | 0.520 | -0.120 (-0.300 to +0.040) | 0.238 | 1 |
| pin vs compact | 50 | 6 | 5 | 39 | 0.460 | 0.440 | +0.020 (-0.100 to +0.160) | 1 | 1 |
| pinrules vs compact | 50 | 4 | 7 | 39 | 0.380 | 0.440 | -0.060 (-0.200 to +0.060) | 0.549 | 1 |
| watch vs compact | 50 | 5 | 4 | 41 | 0.460 | 0.440 | +0.020 (-0.100 to +0.140) | 1 | 1 |
| watch vs pin | 50 | 5 | 5 | 40 | 0.460 | 0.460 | +0.000 (-0.120 to +0.120) | 1 | 1 |
| watch vs pinrules | 50 | 8 | 4 | 38 | 0.460 | 0.380 | +0.080 (-0.040 to +0.220) | 0.388 | 1 |
| watch_ctx vs compact | 50 | 6 | 5 | 39 | 0.460 | 0.440 | +0.020 (-0.100 to +0.160) | 1 | 1 |
| watch vs watch_ctx | 50 | 7 | 7 | 36 | 0.460 | 0.460 | +0.000 (-0.140 to +0.140) | 1 | 1 |
| nopolicy vs standard | 50 | 6 | 14 | 30 | 0.360 | 0.520 | -0.160 (-0.340 to +0.020) | 0.115 | 1 |

## Exposure: compaction before the first database write (compaction arms)

| arm | runs with a write | compaction before first write | reward when exposed | reward when not exposed |
|---|---|---|---|---|
| compact | 24 | 24 | 0.208 (n=24) | n/a |
| pin | 26 | 24 | 0.375 (n=24) | 0.500 (n=2) |
| pinrules | 27 | 27 | 0.259 (n=27) | n/a |
| watch | 24 | 24 | 0.292 (n=24) | n/a |
| watch_ctx | 28 | 27 | 0.296 (n=27) | 1.000 (n=1) |

## Heuristic policy-violation flags (share of runs with at least one)

| arm | write_without_user_yes | transfer_to_human |
|---|---|---|
| nopolicy | 0.280 | 0.500 |
| standard | 0.000 | 0.480 |
| hist | 0.060 | 0.540 |
| compact | 0.180 | 0.440 |
| pin | 0.040 | 0.540 |
| pinrules | 0.040 | 0.580 |
| watch | 0.060 | 0.680 |
| watch_ctx | 0.180 | 0.640 |

## Exploratory: paired comparison of the 'write without an explicit user yes' flag

Per task, share of runs flagged (averaged over shared trials); exact sign test; Holm across rows.

| comparison | shared tasks | a flagged more | b flagged more | rate a | rate b | raw p | Holm p |
|---|---|---|---|---|---|---|---|
| compact vs hist | 50 | 8 | 2 | 0.180 | 0.060 | 0.109 | 0.656 |
| hist vs standard | 50 | 3 | 0 | 0.060 | 0.000 | 0.25 | 1 |
| pin vs compact | 50 | 1 | 8 | 0.040 | 0.180 | 0.0391 | 0.352 |
| pinrules vs compact | 50 | 1 | 8 | 0.040 | 0.180 | 0.0391 | 0.352 |
| watch vs compact | 50 | 1 | 7 | 0.060 | 0.180 | 0.0703 | 0.492 |
| watch vs pin | 50 | 3 | 2 | 0.060 | 0.040 | 1 | 1 |
| watch vs pinrules | 50 | 3 | 2 | 0.060 | 0.040 | 1 | 1 |
| watch_ctx vs compact | 50 | 7 | 7 | 0.180 | 0.180 | 1 | 1 |
| watch vs watch_ctx | 50 | 3 | 9 | 0.060 | 0.180 | 0.146 | 0.73 |
| nopolicy vs standard | 50 | 14 | 0 | 0.280 | 0.000 | 0.000122 | 0.00122 |

## Failure source (runs with reward 0)

| arm | failed | wrong DB state | DB right but missing required output | agent error | max steps |
|---|---|---|---|---|---|
| nopolicy | 32 | 29 | 2 | 0 | 1 |
| standard | 24 | 22 | 2 | 0 | 0 |
| hist | 30 | 26 | 4 | 0 | 0 |
| compact | 28 | 23 | 3 | 0 | 2 |
| pin | 27 | 21 | 3 | 0 | 3 |
| pinrules | 31 | 26 | 4 | 0 | 1 |
| watch | 27 | 24 | 3 | 0 | 0 |
| watch_ctx | 27 | 23 | 4 | 0 | 0 |

## Watchpoint (watch)

- compactions checked: 76; with at least one rule patched: 76 (1.000); mean rules missing per check: 16.21 of 19
- runs with a compaction: 46; runs with at least one patch: 46
- per-rule miss rate (rule index: share of checks): R0: 0.99, R1: 0.22, R2: 0.76, R3: 0.89, R4: 0.59, R5: 0.92, R6: 0.99, R7: 0.95, R8: 0.95, R9: 0.97, R10: 0.76, R11: 0.96, R12: 0.89, R13: 0.83, R14: 0.88, R15: 0.72, R16: 0.96, R17: 0.97, R18: 0.99

## Watchpoint (watch_ctx)

- compactions checked: 83; with at least one rule patched: 83 (1.000); mean rules missing per check: 13.83 of 19
- runs with a compaction: 43; runs with at least one patch: 43
- per-rule miss rate (rule index: share of checks): R0: 0.84, R1: 0.14, R2: 0.55, R3: 0.36, R4: 0.77, R5: 0.75, R6: 0.64, R7: 0.88, R8: 0.83, R9: 0.89, R10: 0.83, R11: 0.84, R12: 0.88, R13: 0.66, R14: 0.70, R15: 0.70, R16: 0.77, R17: 0.89, R18: 0.89
