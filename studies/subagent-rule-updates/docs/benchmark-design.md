# Benchmark design: rule changes across a manager and persistent workers

This is a design for a benchmark, not a completed study. Calls marked *(our call)* were made while drafting and were not discussed with the user. Everything else was agreed in conversation on 2026-11-05.

## Why

The current study shows two failures on a toy repository: a stale rule can beat a relayed change after compaction, and a rule can stay in the summary but stop being applied. Every result so far comes from one hand-written fixture, two rules, and synthetic filler history. A reviewer's first question will be whether this happens on real coding work.

No published benchmark measures this. Existing benchmarks cover rule loss under compaction for a single agent (Governance Decay's ConstraintRot, not released), goal changes for a single agent (InterventionBench), or manager-subagent delegation without instruction changes (ClawArena-Team). None combine a rule change, persistent workers, and compaction.

The benchmark has two jobs:

1. It is a contribution in its own right, released for others to use.
2. It is where we evaluate our own method, the session rule store, against relay, pinning, and re-insertion.

It is for evaluation only. Nothing is tuned on it, so it needs no train or development split.

## Goals

- Real coding tasks from existing benchmarks, scored by their own executable tests.
- A rule layer on top of those tasks: rules with an original and a changed version, plus a checker that reads the final files.
- Compaction at three places: the manager's history only, a worker's history only, or both. The same case without compaction is the baseline.
- Results that distinguish following the new version, the old version, or neither.
- Start small, then grow the number of repositories, rules, and change types over time.

## Non-goals

- Training or tuning any method.
- Non-coding tasks.
- A general memory benchmark. Facts, goals, and plans are out of scope unless a later stage adds them deliberately.
- Enforcement that blocks actions. The benchmark tests what agents do when nothing stops them.
- A public leaderboard in the first version.

## Anti-goals

These would make the benchmark a failure even if it runs:

- A lost rule that looks like compliance. Every rule must be screened so that an agent with no rule behaves differently from both versions.
- Passing by refusing. A worker that skips the task or the permitted work must not score as compliant.
- Scoring from what the model says. Outcomes come from files, tool calls, and test results.
- Redistributing benchmark data under terms that forbid it.

## One test case

1. The user states the rules together with a first task in one repository.
2. The manager delegates the task to a persistent worker.
3. The user changes one rule.
4. History builds up and is compacted in one placement: none, manager only, worker only, or both.
5. The user gives a second task in the same repository without restating the rules.
6. The checker scores the second task.

The worker keeps its conversation across tasks. The workspace resets to each task's own starting commit, because benchmark tasks start from different commits.

## Scoring

Each scored task records four things separately:

| Measure | Source |
|---|---|
| Task solved | the source benchmark's tests (for example, SWE-bench FAIL_TO_PASS and PASS_TO_PASS) |
| Changed rule: new version, old version, or neither | the rule's file checker |
| Unchanged rules kept | the same checkers on the rules that did not change |
| Permitted work done | the checker confirms the rule-related work was done, not skipped |

The headline number for a delivery method is the share of scored tasks that follow the new version of the changed rule while keeping the unchanged rules. Task-solved rates are reported next to it, never folded in. A rule outcome counts even when the task's tests fail.

## Where tasks and history come from

**Tasks.** SWE-rebench V2 tasks from the repositories [VibeMemBench](https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/VibeMemBench) covers (111 packaged tasks across 90 repositories). Most of those repositories have only one packaged task, and each case needs at least two from the same repository. So other SWE-rebench V2 tasks from the same repositories fill the gaps *(our call)*. SWE-bench Verified is a fallback only: it covers about a dozen repositories, overlaps little with VibeMemBench, and is widely contaminated.

**Execution.** Real tasks need a shell and a test runner, which the current harness does not have. Add `run_command` and `run_tests` tools inside each task's container to `harness.py`, rather than moving to another agent scaffold *(our call)*. Every command is logged like the existing write log.

**History before compaction.** VibeMemBench's 3,634 real agent trajectories from the same repositories replace the current study's synthetic filler tasks. The manager's history is built from its own delegation turns over earlier tasks *(our call; the builder decides the exact construction)*.

**Optional second track.** [SlopCodeBench](https://arxiv.org/html/2603.24755v1) problems, where the rule change lands between checkpoints in one carried-forward workspace. Add it only after the main track works, because a full run costs about $84 to $423.

Licenses for VibeMemBench's data, SWE-rebench V2, and SlopCodeBench's code have not been checked yet.

## The rule layer

Rules start from each repository's real contributor conventions. Examples include pytest's changelog fragments under `changelog/`, Django's release notes under `docs/releases/`, and xarray's `doc/whats-new.rst`. Real repositories do not change these conventions mid-session, so we write the changed version.

Each rule ships with:

- the original and changed wording, as the user would say them,
- a checker that labels the final files new version, old version, or neither,
- screening results.

A rule passes screening when an agent with no rule follows neither version, and an agent told either version follows it. This is the same test as the study's `screen-001`. Rules that fail are dropped.

Each case has two rules, one that changes and one that does not *(our call, matching the current study)*.

The repository stays as it is, including its contributor guide and existing examples *(our call)*. That means the repository's own files can argue for the original version after the change, which is realistic and part of the test. It also means a real convention can fail screening, because an agent with no rule copies what it sees in the repository. When that happens, write both versions ourselves (for example, a ticket-ID format in commit-style notes the repository does not use) rather than editing the repository.

## Conditions

Delivery methods, matching the study's current names where they exist:

| Condition | How the change reaches the worker |
|---|---|
| `relay` | The manager passes the change on in a message. This is the realistic baseline. |
| `creation_pin` | A worker gets the current rules only when its session starts. |
| `reinsert` | As `relay`, plus the user's verbatim change re-added after each compaction. |
| `store` | The harness supplies the current rules on every model call, outside the conversation. This is our method. |

Each delivery method runs at all four compaction placements. A no-change control (the user never changes the rule) checks the old version is followed when it should be.

The manager is a real model in every condition, not a scripted relay *(our call)*. Manager compaction only matters if the manager's own memory decides what it passes on.

What stays fixed across conditions *(our call)*:

- The manager gets the same prompt in every condition. That prompt tells it to pass on relevant user instructions, as in `relay-001`. Conditions differ only in what the harness adds. So in `store` and `reinsert` the manager may still relay, and the harness delivery is extra.
- Outside `store`, the original rules sit in the conversation (the user's message to the manager, then the manager's message to the worker), never in a system prompt. This follows the study's second series. FINDINGS section 3 showed a stale rule in the system prompt beating a summarized change is expected instruction-hierarchy behavior, not a finding.
- `store` supplies the current rules to the manager and to every worker. Its manager-compaction placements still run, because the manager's delegation messages can carry stale rules into the worker's history.
- `creation_pin` only matters for workers started after the change. So each case also has a worker-type factor: the second task goes either to the existing worker or to a new worker. The earlier study already showed pinning cannot help existing workers. `creation_pin` runs only with new workers.

How a task is scored for the headline *(our call)*: a task counts as following the new version only if the rule checker sees the new version **and** the rule-related work was done. Skipped work is scored as "neither", not as compliance.

## Models and compaction methods

*(our call)* The runner accepts any OpenRouter model. Later evaluation would start with the study's current pair, GPT-6 Luna and Claude Sonnet 5. Compaction uses the generic summarizer and the pi 1.5.0 port. Keep the study's spending caps, request ledger, and no-silent-retry rules from `provider.py`.

## Scope of this project: build, not run

This project builds the benchmark. Running the full evaluation is a separate, later decision. Building means:

- the cases: task pairs, history, rules, and the compaction placement for each,
- the rule layer: wordings, checkers, and screening results,
- the harness extensions: container tools, manager compaction, the four delivery conditions,
- a runner that can execute any case on any model, with costs recorded.

The build makes no paid model calls. Two checks that need a real model move to the start of evaluation:

- **Screening.** Every rule must be screened on the model being evaluated before its results count. Until then, rules are marked unscreened, and some may be dropped.
- **End-to-end model runs.** The build instead tests the harness offline with scripted agents, like the study's existing `tests/` package. These prove the containers, tools, compaction, conditions, and checkers fit together, not how a real model behaves.

The build's only cost is AWS: pulling task containers and confirming each task's tests pass with its reference fix and fail without it.

## Infrastructure

Task containers run on AWS, on an x86 instance, because SWE-rebench images are built for x86 and run slowly under emulation on the user's Apple Silicon Mac. The harness and model calls can run on the same instance. The user set no overall spending ceiling. Every run still keeps the study's per-run caps in `provider.py`, so a bug cannot spend without limit *(our call)*.

When the full evaluation is run later, almost all of its cost will be model calls, because every agent step resends a long history. Rough guess for planning only: the full grid is about 1,000 to 1,500 scored tasks per model, which is tens of dollars on Luna and about $1,000 to $7,000 on Sonnet 5. The cheaper option is the full grid on Luna and a small Sonnet confirmation run. The first evaluation runs will replace this guess with measured costs.

## Growth plan

1. **Feasibility.** Check licenses. Set up an AWS x86 instance with Docker. Confirm a few SWE-rebench V2 tasks build and their tests behave as expected.
2. **First version.** About 10 repositories with two rules each, every condition and placement defined, and the harness passing offline tests.
3. **More repositories.**
4. **Harder changes.** Several amendments in one session, revocations, and changes that arrive while a worker is mid-task. The study's store and re-insertion results already say a multi-amendment test is needed to separate those two methods.
5. **SlopCodeBench track.**

## What is left to the builder

- How to group tasks into cases and order them.
- How to splice VibeMemBench trajectories into worker histories, and how to build the manager's history.
- When compaction triggers, and how to compact manager and worker histories at the same time.
- How each rule checker is written.
- Release format.
