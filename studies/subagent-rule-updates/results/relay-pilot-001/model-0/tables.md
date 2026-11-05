# Relay sessions (condition A, no compaction)

Sessions: 2, statuses: {'finished': 2}.

| Changed rule | n | relayed | routed to first worker | changed rule: none / v1 (stale) / v2 (current) / both | unchanged rule stays v1 | first task v1/v1 |
|---|---|---|---|---|---|---|
| changelog | 1 | 1 | 1 | 0 / 0 / 1 / 0 | 1 | 1 |
| config_values | 1 | 0 | 0 | 0 / 0 / 1 / 0 | 1 | 1 |
