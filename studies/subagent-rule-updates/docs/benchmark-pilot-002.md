# Benchmark pilot 002: manager compaction with the explicit change message

Written on November 8, 2026, before the run.

## Question

Pilot 001 showed that a real manager restates the rules when it delegates the second task, so the worker never has to remember them. The history that carries the rules is then the manager's. This pilot asks whether compacting the manager's history changes what the worker does.

## Design

- Cells: `relay__none__existing` and `relay__manager__existing`. Only compaction of the manager's history differs. The worker's history is not compacted.
- All 20 v1 cases, 3 repetitions each, GPT-6 Luna, generic compactor, `change_message: "explicit"` (`configs/bench-v1-manager.json`). The manager compacts at `manager_compact_threshold_chars` (4,000), with a forced compaction after the last history block if it never reached the threshold.
- Validated tasks only. Rules screened in `bench-screen-001` (294 of 294 runs correct), run with `--allow-unscreened` because the rule files are not marked screened.
- Run in three parallel groups of cases, each with its own budget cap ($4).

## Measures

- Headline: the changed rule follows its new version and the unchanged rule its original version, from the final files. Also at the worker's first U2 reply.
- What the manager's first U2 delivery names: new version only, old version only, both, or neither (`rule_mentions`).
- Whether each manager summary still names each rule version (`summary_rule_mentions`).

## Prediction

Headline pass rates are high in both cells and differ by at most 10 points. Even if the manager's summary weakens or drops a rule, the worker's own uncompacted history still holds the original rules and the relayed change. A larger drop in the compacted cell would mean a stale or garbled restatement from the manager overrides the worker's own memory, which would be the more interesting result.
