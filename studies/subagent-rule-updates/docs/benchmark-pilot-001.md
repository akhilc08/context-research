# Benchmark pilot 001: do location rules survive worker compaction on real tasks?

Written on November 8, 2026, before the run. The outcome is at the end.

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

## Outcome (added after the run)

All 120 cells finished, at a cost of about $3.72 on GPT-6 Luna. The run used four groups of five cases. Three groups first ran out of host memory because every runner loaded the whole SWE-rebench parquet, so `load_rows` now filters while reading, and the groups were rerun. Raw outputs hold problem statements and are not committed. They are archived in the private S3 bucket of the benchmark host (`results/bench-results-2026-11-08.tgz`).

| Cell | Headline pass, final files | Headline pass, worker's first U2 reply |
|---|---|---|
| `relay__none__existing` | 49/60 | 45/60 |
| `relay__worker__existing` | 49/60 | 46/60 |

The prediction held: the two cells did not differ. The comparison could not have shown a compaction effect, for two reasons.

1. **The manager restated the rules with the second task.** Its first U2 delivery named a rule path in 119 of 120 cells. The worker never had to remember the rules, so compacting the worker's history could not matter. This matches `relay-001` in the controlled study. With a real manager, the history whose compaction can matter is the manager's.
2. **Most failures came from an ambiguous change message, not from memory.** 20 of the 22 failures were "both": the worker wrote the note in the old location and the new one. In 17 of those 20, the manager's U2 message listed the old and new versions as both active. The user's change message says "A change to one of my rules, effective now: <changed wording>". It does not say which rule changes, and no changed wording says it replaces the old location. So the manager often treated the change as an added rule. The other 2 failures, both in the compacted cell, followed neither rule.

Screening (`bench-screen-001`) found every rule passing in every repository: 294 of 294 finished runs correct.

## What this changes

- The change message should be unambiguous: number the rules in U0, say which rule changes in U1, and add "instead of <old location>" to each changed wording. This is one variable and should remove most "both" failures.
- With a real manager that restates rules, worker-only compaction under relay tests nothing. The informative placements are manager compaction and both, or worker compaction under a condition where the manager does not restate the rules.
- Location rules still have no evidence of compaction loss. Code-style rules remain the open addition.


## Follow-up: wording check (pre-registered)

Written before the run. `configs/bench-v1-wording.json` repeats the `relay__none__existing` cell with `change_message: "explicit"`, which names the changed rule by its number and the old location it replaces. Only the five cases with no-compaction failures in pilot 001 run, three repetitions each: `HypothesisWorks__hypothesis--change-summary`, `HypothesisWorks__hypothesis--upgrade-note`, `dbt-labs__dbt-redshift--change-entry`, `pallets__click--changes-entry`, and `stac-utils__pystac--change-entry`. In pilot 001, 10 of these 15 cells failed, nearly all as "both".

Prediction: at most 3 of the 15 fail. If more do, the "both" failures have another cause.

### Outcome of the wording check (added after the run)

All 15 cells finished, at a cost of about $0.47, and all 15 passed: the changed rule followed its new version and the unchanged rule its original version. With the old wording, 10 of the same 15 failed. The prediction (at most 3 failures) held. The manager's U2 message still named the old location in 9 of the 15 cells, now as the location to stop using, and the worker wrote only the new version every time. Raw outputs are archived in the host's S3 bucket (`results/bench-wording-001.tgz`).

The "both" failures in pilot 001 came from the ambiguous change message. Benchmark runs should use `change_message: "explicit"`.
