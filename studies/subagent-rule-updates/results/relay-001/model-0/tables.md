# Relay sessions (condition A, no compaction)

Sessions: 20, statuses: {'finished': 20}.

| Changed rule | n | relayed | task 2 delegated | changed rule: none / v1 (stale) / v2 (current) / both | unchanged rule stays v1 | first task v1/v1 |
|---|---|---|---|---|---|---|
| changelog | 10 | 10 | 10 | 0 / 0 / 10 / 0 | 10 | 10 |
| config_values | 10 | 10 | 10 | 0 / 0 / 10 / 0 | 10 | 10 |
