# Benchmark pilot 003: powered test of manager compaction (pre-registered)

Written on November 10, 2026, before the run.

## Question

In pilot 002 the worker's first U2 reply failed the headline in 5 of 47 cells with manager compaction and 2 of 48 without (Fisher p = 0.27). Final files differed less (3 against 2), because the manager's follow-ups rescued two compacted cells. Is the first-attempt drop real?

## Design

Same as pilot 002 (`relay__none__existing` against `relay__manager__existing`, generic compactor, explicit change message, all 20 v1 cases) with 11 repetitions per case and condition: 440 cells (`configs/bench-v1-manager-powered.json`). Cases run in six groups from `bench/manifests/manager-powered-groups.txt`, three at a time, through `bench/run_groups.sh`, each group with a $5 cap. A group that stops early leaves its other groups unaffected. Pilot 002's cells are not pooled in, so that this run tests its result.

## Analysis

- Primary outcome: headline failure at the worker's first U2 reply (`first_attempt`).
- Secondary: headline failure in the final files.
- Unit: the case. For each case, the failure rate per condition. The test is a paired sign-flip permutation test on the per-case differences (compacted minus not), two-sided, 20,000 permutations. Cases with no finished cell in one condition are dropped and reported.
- Also reported: pooled rates, failure types, and whether the manager's first U2 message named the new version.

## Predictions and decision rule

Planning numbers are 4% first-attempt failure without compaction and 11% with it, which needs about 220 cells per condition for 80% power before accounting for clustering.

- A real effect is a mean per-case difference of at least 4 points with p below 0.05. That would be the first real-task evidence that compaction (here, of the manager) lowers compliance.
- Otherwise, pilot 002's gap is treated as noise, and location rules are treated as unaffected by manager compaction at this sample size.

Prior belief before running: about even odds. The direction in pilot 002 matches the controlled study, but the effect is small and the manager restates the rules with the task.
