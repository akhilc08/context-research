# Amendment-status test: state-level analysis

## This run alone (rule-compaction-amend-001)

| Cell | States | Runs | Failures | Mean state failure rate |
|---|---|---|---|---|
| O-C (config.py, original) | 10 | 60 | 0 | 0.00 |
| A-C (config.py, amended) | 20 | 120 | 13 | 0.11 |
| O-S (settings.get, original) | 20 | 120 | 90 | 0.75 |
| A-S (settings.get, amended) | 10 | 60 | 34 | 0.57 |

| Comparison | Difference | Permutation p |
|---|---|---|
| content, original rules (O-S vs O-C) | +0.75 | 0.0001 |
| content, amended rules (A-S vs A-C) | +0.46 | 0.0018 |
| status, config.py (A-C vs O-C) | +0.11 | 0.1893 |
| status, settings.get (A-S vs O-S) | -0.18 | 0.2890 |

## Pooled with the earlier O-C and A-S sessions (rule-compaction-001 and 002)

| Cell | States | Runs | Failures | Mean state failure rate |
|---|---|---|---|---|
| O-C (config.py, original) | 19 | 114 | 2 | 0.02 |
| A-C (config.py, amended) | 20 | 120 | 13 | 0.11 |
| O-S (settings.get, original) | 20 | 120 | 90 | 0.75 |
| A-S (settings.get, amended) | 20 | 120 | 67 | 0.56 |

| Comparison | Difference | Permutation p |
|---|---|---|
| content, original rules (O-S vs O-C) | +0.73 | 0.0000 |
| content, amended rules (A-S vs A-C) | +0.45 | 0.0005 |
| status, config.py (A-C vs O-C) | +0.09 | 0.1021 |
| status, settings.get (A-S vs O-S) | -0.19 | 0.1745 |

