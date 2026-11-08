# Benchmark pilot 001: do location rules survive worker compaction on real tasks?

Written on November 8, 2026, before the run.

## Question

The controlled study found that rules about where to write a change note never failed after compaction, while a rule about how code is written did (`FINDINGS.md` sections 6 to 9). All 20 v1 benchmark rules are location rules. This pilot checks whether they hold under worker compaction on real tasks. If they do, the v1 rules cannot separate delivery methods.

## Design

- Cells: `relay__none__existing` and `relay__worker__existing`. Only compaction of the worker's history differs.
- All 20 v1 cases, 3 repetitions each, GPT-6 Luna, generic compactor, `configs/bench-v1-pilot.json`.
- Validated tasks only (`bench/manifests/validation-v1.json`).
- Screening (`bench-screen-001`, stopped at 299 of 600 runs by an invalid provider response) found every rule passing in every finished run: 294 of 294 runs correct, 2 to 9 per arm and repository. The pilot runs with `--allow-unscreened` because the rule files are not yet marked screened.

## Measures

- Headline: the changed rule follows its new version and the unchanged rule its original version, from the final files. Also the same at the worker's first U2 reply (`first_attempt`).
- Whether each compaction summary still names each rule version (`summary_rule_mentions`).
- Whether the manager restated the rules in its first U2 delivery (`u2_first_restated_rules`), because a restatement means the worker did not have to remember them.

## Prediction

Headline pass rates are high in both cells and do not differ by more than 10 points. The location rules survive worker compaction on real tasks, as the changelog rule did in the controlled study. If the compacted cell is at least 15 points lower, the prediction fails and the v1 rules can measure compaction loss.
