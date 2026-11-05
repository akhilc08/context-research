# Rule screen

Runs: 70, finished: 70.

## changelog: PASS

| Arm | n | none | v1 | v2 | both | other |
|---|---|---|---|---|---|---|
| none | 10 | 10 | 0 | 0 | 0 | 0 |
| changelog:v1 | 10 | 0 | 10 | 0 | 0 | 0 |
| changelog:v2 | 10 | 0 | 0 | 10 | 0 | 0 |

Checks: against_default=yes, follows_v1=yes, follows_v2=yes

## test_placement: FAIL

| Arm | n | none | v1 | v2 | both | other |
|---|---|---|---|---|---|---|
| none | 10 | 5 | 5 | 0 | 0 | 0 |
| test_placement:v1 | 10 | 0 | 10 | 0 | 0 | 0 |
| test_placement:v2 | 10 | 0 | 0 | 10 | 0 | 0 |

Checks: against_default=no, follows_v1=yes, follows_v2=yes

## config_values: PASS

| Arm | n | none | v1 | v2 | both | other |
|---|---|---|---|---|---|---|
| none | 10 | 10 | 0 | 0 | 0 | 0 |
| config_values:v1 | 10 | 0 | 10 | 0 | 0 | 0 |
| config_values:v2 | 10 | 0 | 0 | 10 | 0 | 0 |

Checks: against_default=yes, follows_v1=yes, follows_v2=yes
