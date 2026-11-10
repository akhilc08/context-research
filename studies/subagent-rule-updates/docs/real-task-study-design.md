# Design: does compaction stop agents applying effortful rules on real tasks?

Status: draft for review. Nothing is built or run. Written on November 10, 2026.

## Claim under test

On a toy repository, compaction kept a code rule in the summary but the agent stopped applying it. This happened for an effortful rule (read a tunable value with `app.settings.get`) and not for a light one (a constant in `app/config.py`), whether the rule was original or amended. Delivering the rules verbatim outside the summary removed the failures (`FINDINGS.md` sections 6 to 9). This study asks whether the same holds on real repositories and real tasks, and whether effort is the variable that decides it.

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
- The history is read-only work in the same repository at the task's base commit: "Read <file> and summarize its main classes and functions. Do not change any files." Files are chosen deterministically from the base commit's source files, excluding every file the gold patch or test patch touches, largest first, until the history passes about 450,000 characters. This replaces both the toy's synthetic log files and the benchmark's replayed trajectories. Replayed trajectories hardcode values themselves and would show the worker counterexamples to the rule. Read-only work cannot violate it.

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

## Rules: effort as a variable

One nested ladder on one code event, adding a tunable value to non-test source. Each wording keeps the toy's scope ("tunable values such as thresholds, rates, limits, timeouts, or sizes").

- **L1 (light):** define it as a named UPPER_CASE constant at module level in the same file and use it.
- **L2 (medium):** define it as a constant in `<pkg>/_tunables.py`, creating the file if needed, and import it where it is used. This matches the toy's `config.py` rule.
- **L3 (heavy):** as L2, but the constant is read from an environment variable with a default and type conversion, for example `TIMEOUT = float(os.environ.get("<PKG>_TIMEOUT", "30"))`. This matches the toy's `settings.get` rule.

A deterministic AST checker labels each scored run by the highest level it satisfies: none (bare literal), L1, L2, or L3. A run follows its rule if it satisfies the told level. A failed L3 run can then be seen falling back to L2, L1, or a bare literal.

Each session also carries a light note rule, R_N: "List every tunable value you add, with its file, in `TUNABLES.md`." If R_N is followed while L3 fails, the worker recognized the tunable and skipped only the costly rule.

Effort is measured, not asserted: extra diff size of compliant runs over no-rule runs per task, and whether the repository already uses environment variables or a constants module (`repo_prior`).

## Screening (no history, no compaction)

Per task: a no-rule arm and one arm per told level, 3 runs each. A task is kept if the no-rule arm leaves a bare literal in at least 2 of 3 runs and each told arm follows its level in 3 of 3. This also checks the checker on every task.

## Conditions

Sessions, each producing saved states, per task and level (L2, L3, and L1 if it screens):

- `no_compact`
- `compact`
- `no_rule_compact`: the default under the same history.

Branches from every saved compacted state:

- **F1, rules next to the task:** the verbatim rules restated in the work order, as a restating manager would.
- **F2, store at task time:** the verbatim rules in the system prompt.

Later: store from the start, re-insertion after each compaction, the summary's own rule sentence pasted next to the task (salience against wording), the pi compactor, a second model.

## Analysis

- Unit: the compacted state. Each state gets the scored branch plus 5 resamples.
- Per-task rate per arm, compared with a paired sign-flip permutation test over tasks, stratified by repository, two-sided, 20,000 permutations. A mixed logistic model with task and state effects as a robustness check.
- Functional audit: set the environment variable and check that behavior changes, as `semantic_audit.py` did.
- Task tests are reported separately and never folded into rule outcomes.
- Final summaries are checked for whether they still state the rule, by keywords and a blind manual read.

## Predictions (to be fixed before any compaction run)

- P1: Without compaction, L2 and L3 are each followed in at least 90% of runs.
- P2 (primary): L3 failure with compaction exceeds L3 failure without it by at least 15 points, p < 0.05.
- P3: L3 failure with compaction exceeds L2 failure with compaction by at least 15 points, p < 0.05.
- P4: At least 80% of compacted L3 failures come from states whose final summary still states the rule.
- P5: F1 and F2 each bring compacted L3 failure to within 5 points of no compaction.
- P6: R_N is followed in at least 90% of compacted sessions, including those where L3 failed.
- P7: `no_rule_compact` leaves a bare literal in at least 90% of runs.

Decision rules: if P2 fails, report a null with its interval; a new rule set is a new pre-registration. If P2 holds and P3 fails with L2 also failing, the claim becomes "code rules fail" rather than "effort". If P5 holds, the fix claim stands.

## Size and cost (planning)

About 20 tasks, two levels, 3 compacted states per task and level with 6 runs each, 2 fix branches with 3 runs each, 3 uncompacted runs: roughly 1,300 scored runs plus about 120 compacted session preparations and screening. Estimated $60 to $100 on Luna, capped at $120, and about one to two days on the AWS host. Task images are 2 to 3 GB each, so about 20 tasks fit the 200 GB disk.

## Risks

- Tests may pin a literal or import a constant by name. Screening and validation catch tasks where a compliant fix breaks the tests, and those are reported.
- Some repositories make an environment-variable rule unnatural (numerical libraries with solver tolerances as arguments). The judged pool excludes most of them.
- A real task may not lead the agent to add a tunable at all. The no-rule screening arm catches this.
- Read-only history is less varied than real coding work. It is the controlled choice, and self-generated coding history is a later robustness check.
