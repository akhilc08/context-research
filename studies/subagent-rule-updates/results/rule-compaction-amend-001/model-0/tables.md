# Rule compaction (original rules in the conversation, screened rules)

Branches: 140, statuses: {'finished': 140}.

| Changed rule | Condition | n | changed rule: none / v1 (stale) / v2 (current) / both | unchanged rule stays v1 | task attempted |
|---|---|---|---|---|---|
| changelog | relay_compact | 20 | 0 / 0 / 20 / 0 | 20 | 20 |
| config_values | relay_compact | 20 | 8 / 0 / 12 / 0 | 20 | 20 |
| changelog_sfirst | relay_no_compact | 10 | 0 / 0 / 10 / 0 | 0 | 10 |
| changelog_sfirst | relay_compact | 40 | 4 / 0 / 36 / 0 | 0 | 40 |
| config_reverse | relay_no_compact | 10 | 0 / 10 / 0 / 0 | 10 | 10 |
| config_reverse | relay_compact | 40 | 3 / 37 / 0 / 0 | 40 | 40 |

## Final summary keywords (inspection only, not scored)

| Changed rule | Final summaries | mentions new version | mentions old version only | mentions neither |
|---|---|---|---|---|
| changelog (relay_compact) | 10 | 10 | 0 | 0 |
| config_values (relay_compact) | 10 | 10 | 0 | 0 |
| changelog_sfirst (relay_compact) | 20 | 18 | 0 | 2 |
| config_reverse (relay_compact) | 20 | 20 | 0 | 0 |

## Config rule by content and role

| Session | Condition | Config content | Config role | Task | followed |
|---|---|---|---|---|---|
| changelog | relay_compact | config.py | original | bulk_discount | 10/10 |
| changelog | relay_compact | config.py | original | low_stock | 10/10 |
| config_values | relay_compact | settings.get | amended | bulk_discount | 7/10 |
| config_values | relay_compact | settings.get | amended | low_stock | 5/10 |
| changelog_sfirst | relay_no_compact | settings.get | original | bulk_discount | 5/5 |
| changelog_sfirst | relay_no_compact | settings.get | original | low_stock | 5/5 |
| changelog_sfirst | relay_compact | settings.get | original | bulk_discount | 6/20 |
| changelog_sfirst | relay_compact | settings.get | original | low_stock | 6/20 |
| config_reverse | relay_no_compact | config.py | amended | bulk_discount | 5/5 |
| config_reverse | relay_no_compact | config.py | amended | low_stock | 5/5 |
| config_reverse | relay_compact | config.py | amended | bulk_discount | 20/20 |
| config_reverse | relay_compact | config.py | amended | low_stock | 17/20 |
