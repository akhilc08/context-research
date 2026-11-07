# Rule compaction (original rules in the conversation, screened rules)

Branches: 12, statuses: {'finished': 12}.

| Changed rule | Condition | n | changed rule: none / v1 (stale) / v2 (current) / both | unchanged rule stays v1 | task attempted |
|---|---|---|---|---|---|
| changelog | relay_compact | 2 | 0 / 0 / 2 / 0 | 2 | 2 |
| config_values | relay_compact | 2 | 2 / 0 / 0 / 0 | 2 | 2 |
| changelog_sfirst | relay_no_compact | 2 | 0 / 0 / 2 / 0 | 0 | 2 |
| changelog_sfirst | relay_compact | 2 | 0 / 0 / 2 / 0 | 0 | 2 |
| config_reverse | relay_no_compact | 2 | 0 / 2 / 0 / 0 | 2 | 2 |
| config_reverse | relay_compact | 2 | 2 / 0 / 0 / 0 | 0 | 2 |

## Final summary keywords (inspection only, not scored)

| Changed rule | Final summaries | mentions new version | mentions old version only | mentions neither |
|---|---|---|---|---|
| changelog (relay_compact) | 1 | 1 | 0 | 0 |
| config_values (relay_compact) | 1 | 1 | 0 | 0 |
| changelog_sfirst (relay_compact) | 1 | 1 | 0 | 0 |
| config_reverse (relay_compact) | 1 | 0 | 0 | 1 |

## Config rule by content and role

| Session | Condition | Config content | Config role | Task | followed |
|---|---|---|---|---|---|
| changelog | relay_compact | config.py | original | bulk_discount | 1/1 |
| changelog | relay_compact | config.py | original | low_stock | 1/1 |
| config_values | relay_compact | settings.get | amended | bulk_discount | 0/1 |
| config_values | relay_compact | settings.get | amended | low_stock | 0/1 |
| changelog_sfirst | relay_no_compact | settings.get | original | bulk_discount | 1/1 |
| changelog_sfirst | relay_no_compact | settings.get | original | low_stock | 1/1 |
| changelog_sfirst | relay_compact | settings.get | original | bulk_discount | 0/1 |
| changelog_sfirst | relay_compact | settings.get | original | low_stock | 0/1 |
| config_reverse | relay_no_compact | config.py | amended | bulk_discount | 1/1 |
| config_reverse | relay_no_compact | config.py | amended | low_stock | 1/1 |
| config_reverse | relay_compact | config.py | amended | bulk_discount | 0/1 |
| config_reverse | relay_compact | config.py | amended | low_stock | 0/1 |
