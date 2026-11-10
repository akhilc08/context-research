# Design: does compaction stop agents applying effortful rules on real tasks?

Status: draft, revised after an independent review. Nothing is built or run. Written on November 10, 2026.

## Claim under test

Stage 1 claim: on real tasks, compaction makes an agent stop applying a code prescription it was given in conversation, while still stating it in the summary, and restating the rule verbatim next to the task fixes it. Whether effort is the cause is a later question.

Background: on a toy repository, compaction kept a code rule in the summary but the agent stopped applying it. This happened for an effortful rule (read a tunable value with `app.settings.get`) and not for a light one (a constant in `app/config.py`), whether the rule was original or amended. Delivering the rules verbatim outside the summary removed the failures (`FINDINGS.md` sections 6 to 9). This study asks whether the same holds on real repositories and real tasks, and whether effort is the variable that decides it.

## What changes from the toy, and what stays

The study keeps the toy protocol (`rule_compaction.py`) and swaps the environment.

Kept:

- One persistent worker. A scripted manager gives it the rules once, at the start of its conversation, in the toy's relayed-instructions envelope, then bare work orders that never restate the rules.
- A read-only warmup, then read-only history that grows until compaction.
- The generic compactor (`compaction.py`) at 137,500 characters, at least 2 rounds, about 3 in practice. The pi port is a later replication.
- The scored task as a bare work order on a fresh checkout.
- GPT-6 Luna, temperature 0.2, low reasoning effort.
- No amendment. Section 9 found amendment status made no difference, so every session states the final rules from the start.

Changed:

- The repository and the scored task are real: SWE-rebench V2 tasks in their Docker images, with the benchmark's container tools (`bench/container.py`).
- The history is read-only work in the same repository at the task's base commit ("Read <file> and summarize its main classes and functions. Do not change any files."), described under History below. It replaces both the toy's synthetic log files and the benchmark's replayed trajectories, which hardcode values themselves and would show the worker counterexamples to the rule.

Why a scripted manager that does not restate: a real manager under our prompt restated the rules in 119 of 120 delegations (pilot 001). That rate comes from our own manager prompt. Single agents given conventions in chat, and subagents briefed once at spawn and reused, hold rules only in their history. Restating is tested as a fix (arm F1), not assumed away. Codex keeps earlier user messages verbatim and should not show the failure; the paper should say so.

## Tasks

The pool is real SWE-rebench V2 Python tasks whose gold fix introduces a genuine tunable value: a new threshold, limit, timeout, retry count, interval, or size that a project could want to configure. A mechanical scan found 302 candidate tasks. Three judging agents labeled 258 of them by hand as genuine, borderline, or not, and recorded whether the value relates to the issue and whether the issue already asks for it to be configurable (`bench/manifests/tunables-judged.json`). The remaining 44 candidates, in repositories with agent trajectories, were judged in summary and none was usable. Results:

- 67 genuine. Most rejected candidates were values that already existed, cloud or API spec limits, numerical tolerances, and counters.
- 41 usable: genuine, related to the issue, and the issue does not ask for configuration. They come from 37 repositories, so cases are almost one task per repository.
- Where the value lives in the gold fix: function default 13, inline literal 10, module constant 9, class attribute 5, other 4.

Judgments are by models, not people. Two weak calls are flagged in the file (sabnzbd-1969 and pytask-263).

Inclusion, fixed before any compaction run:

1. Genuine, related to the issue, and the issue does not already ask for configuration.
2. At most 3 tasks per repository.
3. The task validates (gold fix passes, tests fail at base) with `bench/validate.py`.
4. Screening (below) passes.

The full funnel is reported.

## Rules: two prescriptions with the same scope

An independent review (GPT-6.1 Sol, November 10) found that a three-level ladder bundles effort with convention, wording, new files, and configuration semantics, so it cannot show that effort is the cause. Stage 1 therefore tests prescription loss, not effort. It uses two rules with identical scope wording and the same file infrastructure, differing in one step:

- **R-const:** define each new tunable value (a threshold, rate, limit, timeout, retry count, or size) as a named UPPER_CASE constant at module level in the file that uses it, and use the constant.
- **R-env:** define each new tunable value as a module-level UPPER_CASE constant in the file that uses it, read from an environment variable with a default and a type conversion, for example `TIMEOUT = float(os.environ.get("<PKG>_TIMEOUT", "30"))`, and use the constant.

R-env adds one step to R-const: the environment read. This mirrors the toy pair, where the `config.py` rule held and the `settings.get` rule failed, without creating a new module. Effort as a variable is deferred to a later stage with its own design.

Values are frozen at import. Explicit arguments must still override defaults. Tasks whose tests break under a compliant fix are found at screening and reported.

## Scoring

"A new tunable value" is a semantic judgment, so scoring has two steps.

1. **Deterministic extraction.** From base and final source (untracked files included, captured before hidden tests run), extract every numeric literal added to non-test source other than 0, 1, and -1, with its site: function default, assignment, call argument, comparison, or arithmetic. Values that moved without changing are matched across versions and excluded.
2. **Blind adjudication.** A reviewer who does not know the arm labels each extracted value as tunable or not. Reviewers are a model from a different family, validated against hand labels on a sample before use.

For each tunable, record whether it is a named constant, whether it reads the environment, and whether the constant is used. A session follows its rule only if every tunable it adds follows the rule. Sessions are labeled follows, partial, violates, no tunable added, or unscorable. "No tunable added" is reported separately and never counted as compliance. A behavioral probe sets the environment variable and checks that behavior changes. Adversarial fixtures cover unused constants, dead code, shadowing, aliases, computed thresholds, and moved values.

## Screening (no history, no compaction)

Per task: a no-rule arm and one arm per rule, 3 runs each. A task is kept if the no-rule arm adds a bare tunable literal in at least 2 of 3 runs and each told arm follows its rule in at least 2 of 3. Gold eligibility does not guarantee the agent adds a tunable, so this is also the applicability check. The full funnel is reported, and screening is also the resource pilot: tokens, dollars, test time, memory, disk, and compaction rounds are measured there before the main run is sized.

## Conditions

Per task and rule, each with its own independent preparation replicates:

- `fresh`: the rules then the scored task, with no history.
- `long_no_compact`: the same history, never compacted.
- `compact`: the same history, compacted.
- `compact_restated`: branched from each compacted state, with the verbatim rules restated next to the task, as a restating manager would.
- `no_rule_compact`: the default under the same history.

The system-prompt store is dropped from stage 1. It changes the rules' authority as well as their location, so it is a separate intervention.

## History

Read-only "summarize file X" tasks on the same base commit. The run checks that the checkout is at the base commit, since the container start does not. Files over the 64 KB read limit are skipped. The schedule does not depend on the gold patch: files are drawn in a seeded random order from the base commit's non-test source files, without excluding the files the fix touches. Live history, cumulative delivered content, truncations, compaction rounds, and final tail length are logged. This is a controlled stressor, not realistic coding history. Repository source still contains hardcoded values, which is the convention the rule asks the agent to break.

## Analysis

- Unit: the task. Independent preparation replicates per task and arm, with modest branch replication. Resampling is hierarchical, paired by task and history, and clustered by repository.
- Primary contrast: the compaction-by-rule interaction. Does compaction raise violation more for R-env than for R-const?
- Secondary: `compact` against `long_no_compact` for each rule. Restatement uses a noninferiority interval against `long_no_compact`, not close point estimates.
- Sample size comes from a simulation with task and state heterogeneity, fixed before the main run. A simple illustration: if compaction made 15% of tasks fail completely and the rest not at all, a task-level sign-flip test would reach significance only 7% of the time with 20 tasks.
- Task tests are reported separately, and also jointly with compliance.

## Predictions (fixed after screening, before any compaction run)

- P1: In `fresh` and `long_no_compact`, both rules are followed in at least 90% of sessions that add a tunable.
- P2 (primary): The compaction-by-rule interaction is positive: compaction raises R-env violation more than R-const violation.
- P3: Most compacted R-env violations come from states whose final summary still states the rule.
- P4: `compact_restated` is noninferior to `long_no_compact` within a margin fixed at freeze.
- P5: `no_rule_compact` adds bare tunable literals in nearly every session that adds one.

Decision rules: if P2 fails, report the null with its interval. If both rules fail equally under compaction, the claim becomes "compaction weakens code prescriptions," not one tied to the environment read.

## Size and cost

Not fixed yet. Screening measures cost and time per run. An earlier estimate of about 1,300 scored runs works out to roughly 1,560 runs plus up to about 490 screening runs. At five minutes a run with three runners, that is over 40 hours, so the size will be set from measured numbers and the power simulation. Images are 2 to 3 GB each: about 100 GB for all 41 tasks, so screening runs in batches that remove images afterward. Three test containers at once may need more than 16 GB of memory, so the pilot measures that too.

## Risks

- Tests may pin a literal or import a constant by name. Screening and validation catch tasks where a compliant fix breaks the tests, and those are reported.
- Some repositories make an environment-variable rule unnatural (numerical libraries with solver tolerances as arguments). The judged pool excludes most of them.
- A real task may not lead the agent to add a tunable at all. The no-rule screening arm catches this.
- Read-only history is less varied than real coding work. It is the controlled choice, and self-generated coding history is a later robustness check.
