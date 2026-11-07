# Benchmark design: rule changes across a manager and persistent workers

This is a design for a benchmark, not a completed study. The benchmark is now built in `bench/`, and the [As built](#as-built) section records what the build settled and what is still open. Calls marked *(our call)* were made while drafting and were not discussed with the user. Everything else was agreed in conversation on 2026-11-05.

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

**Execution.** Real tasks need a shell and a test runner, which the current harness does not have. The build adds `read_file`, `write_file`, and `run_command` tools inside each task's container (`bench/container.py`), rather than moving to another agent scaffold *(our call)*. There is no separate `run_tests` tool. Workers run tests through `run_command`, and the source benchmark's tests are run only by the scorer. Every command is logged like the existing write log.

**History before compaction.** VibeMemBench's 3,634 real agent trajectories from the same repositories replace the current study's synthetic filler tasks. The manager's history is built from generated delegation turns over earlier tasks *(our call)*. The build settled the construction under [As built](#as-built).

**Optional second track.** [SlopCodeBench](https://arxiv.org/html/2603.24755v1) problems, where the rule change lands between checkpoints in one carried-forward workspace. Add it only after the main track works, because a full run costs about $84 to $423.

SWE-rebench V2 is CC-BY-4.0. VibeMemBench is Apache-2.0, but its problem statements, patches, and tests keep each upstream repository's license, recorded in its `license` column. SlopCodeBench's license has not been checked yet.

## The rule layer

Rules start from each repository's real contributor conventions. Examples include pytest's changelog fragments under `changelog/`, Django's release notes under `docs/releases/`, and xarray's `doc/whats-new.rst`. Real repositories do not change these conventions mid-session, so we write the changed version.

Each rule ships with:

- the original and changed wording, as the user would say them,
- a checker that labels the final files new version, old version, or neither,
- screening results.

A rule passes screening when an agent with no rule follows neither version, and an agent told either version follows it. This is the same test as the study's `screen-001`. Rules that fail are dropped.

Each case has two rules, one that changes and one that does not *(our call, matching the current study)*. The v1 manifest makes each repository's two rules two cases, with each rule taking a turn as the changed one.

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

The build made no paid model calls. Two checks that need a real model move to the start of evaluation:

- **Screening.** Every rule must be screened on the model being evaluated before its results count. Until then, rules are marked unscreened, and some may be dropped.
- **End-to-end model runs.** The build instead tests the harness offline with scripted agents, like the study's existing `tests/` package. These prove the containers, tools, compaction, conditions, and checkers fit together, not how a real model behaves.

The build's only cost is AWS: pulling task containers and confirming each task's tests pass with its reference fix and fail without it. That validation is done (see [Validation](#validation)).

## Infrastructure

Task containers run on AWS, on an x86 instance, because SWE-rebench images are built for x86 and run slowly under emulation on the user's Apple Silicon Mac. The harness and model calls can run on the same instance. The user set no overall spending ceiling. Every run still keeps the study's per-run caps in `provider.py`, so a bug cannot spend without limit *(our call)*.

When the full evaluation is run later, almost all of its cost will be model calls, because every agent step resends a long history. Rough guess for planning only: the full grid is about 1,000 to 1,500 scored tasks per model, which is tens of dollars on Luna and about $1,000 to $7,000 on Sonnet 5. The cheaper option is the full grid on Luna and a small Sonnet confirmation run. The first evaluation runs will replace this guess with measured costs.

## Growth plan

1. **Feasibility.** Check licenses. Set up an AWS x86 instance with Docker. Confirm a few SWE-rebench V2 tasks build and their tests behave as expected. Licenses are checked for SWE-rebench V2 and VibeMemBench. The AWS host is set up and every v1 task is validated (see [Validation](#validation)).
2. **First version.** About 10 repositories with two rules each, every condition and placement defined, and the harness passing offline tests. This is built (see below), with the open items listed there.
3. **More repositories.**
4. **Harder changes.** Several amendments in one session, revocations, and changes that arrive while a worker is mid-task. The study's store and re-insertion results already say a multi-amendment test is needed to separate those two methods.
5. **SlopCodeBench track.**

## As built

This section records what the build in `bench/` settled. It changes the design only where stated.

### Trajectories and history replay

VibeMemBench trajectories use native tool calls: assistant messages carry `tool_calls` with a bash `command`, and tool messages carry the output. `bench/history.py` replays them as `run_command` calls, keeps one user message plus the assistant and tool turns, truncates long outputs, and drops the final submit step. Replayed worker history is real agent work.

Three edits keep the replay from contradicting the session:

- **The first user message is the bare problem statement.** The trajectory's own first message also carries mini-swe-agent's instructions, such as "DO NOT MODIFY tests", "MODIFY source files in /testbed", and the submit protocol. Those instructions could conflict with a rule (a regression-test rule asks for a new test file) and would differ in strength between placements. So they are dropped.
- **`/testbed` becomes the case's working directory.** Trajectories ran in `/testbed`, but the task containers check out the repository at `/<repo name>`. Commands, outputs, and assistant text are rewritten to match.
- **Call IDs are sanitized.** Replayed tool-call IDs use only letters, digits, `_`, and `-`, and are at most 64 characters, so every provider accepts them.

The manager side of each earlier task is generated, not taken from the trajectory. The manager receives the task's problem statement, delegates it with a `message_worker` call, gets the worker's reply, and answers "Done." These delegation turns never restate the rules. So a rule can only reach the worker through the first user message, the change, or the condition's delivery.

### Compaction triggers

The manager and worker histories have separate thresholds. The worker uses `compact_threshold_chars` (137,500 characters in `configs/bench-v1.json`). The manager uses `manager_compact_threshold_chars` (4,000). The manager's history is much shorter, because its side of each earlier task is only four messages. Its replayed part ranges from about 4,900 to 40,400 characters across the v1 cases, so with the worker's threshold the manager would never compact.

After the last history block, each history the placement names that has not yet had a real compaction is compacted once anyway. That event records `forced: true`. With the pi port, a forced compaction can still skip, because pi keeps the recent tail and may find nothing older to summarize. In that case the generic summarizer runs instead and the event also records `forced_generic: true`. A content test replays every v1 case's real history under the shipped config. Both histories compact on their thresholds alone in every case but one. Setuptools' manager history is a single short task (about 2,900 characters), so its one manager compaction is forced. Lowering the manager threshold to cover it would roughly double the manager compactions in most other cases.

### Containers

- The working directory is `/<repo name>`, the checkout path in SWE-rebench V2 images.
- `run_command` uses an in-container `timeout`, because that is the only reliable way to kill the whole process tree. The host timeout is longer. A timed-out command returns exit code 124. `bench/validate.py` checks that each image has `timeout`.
- Task 1 and task 2 each get their own container, started from that task's image and commit. The workspace does not carry over between them.
- The agent works with no network: containers start with `--network none` (`container_network` in the config). Just before the hidden tests run, the scorer moves the container to `scoring_network` (`bridge` in `configs/bench-v1.json`). Some tasks' tests need the network, for example aiohttp's proxy tests and setuptools' editable installs. The agent still cannot download packages or fetch the upstream fix. Validation uses the same two settings. Leaving `scoring_network` unset keeps the container on `container_network` throughout.
- Before the test patch is applied for scoring, every file it touches is reset to the base commit. Files that exist at base are checked out again, and files the patch creates are deleted. A worker that edited a test file therefore cannot block scoring. Validation's gold run skips this reset, so a gold patch that edits test files still shows up as a conflict.

### Cells and statuses

The grid has 19 cells:

| Delivery | Worker | Placements | Cells |
|---|---|---|---|
| `relay`, `reinsert`, `store` | existing | none, manager, worker, both | 12 |
| `relay`, `creation_pin`, `store` | new | none, manager | 6 |
| `no_change` | existing | none | 1 |

A run ends in one status:

- `finished`: both turns completed and the second task was scored.
- `provider_error`: a model request raised. The record is saved and the run stops, because the failure may mean budget or billing trouble.
- `compaction_error`: the summarizer answered without a complete summary.
- `infra_error`: a container or other setup failure.

Unfinished records are never scored. Manager turns that end without finishing are recorded with a `manager_` status prefix. A worker's own status, such as `call_limit`, never sets the record's status directly. It goes back to the manager as the `message_worker` result, and only the manager's turn status reaches the record, through the `manager_` prefix.

Analysis excludes two kinds of finished record from rates and counts each separately:

- `setup_invalid`: the placement names a history that never had a non-skipped compaction. Forced compaction should make this rare, but the check stays.
- `delegation_invalid`: the record's `u0_delegated`, `u2_delegated`, or `u2_worker_finished` flag is false or missing. These flags come from the worker deliveries. They catch a manager that answered a task itself and a worker whose last U2 delivery did not finish.

The manager can follow up after the worker's first U2 reply, for example by asking whether the notes were written. A follow-up like that can rescue a rule the worker forgot. The record therefore also scores the files as they stood when the worker first returned from U2 (`first_attempt`), and analysis reports a headline for that moment next to the final one. Two more fields show how much help the worker got: `u2_deliveries` counts the U2 deliveries, so more than one means the manager followed up, and `u2_first_restated_rules` is true when the first U2 delivery named a rule's path. Each delivery also records `rule_mentions`, which says which rule versions it names by path. These fields let a reader check what the manager relayed before blaming a failure on compaction. The free-model pilot showed all of these effects: in its audit, a manager reminder rescued a control run, and a manager relayed one unchanged rule wrongly.

The worker's system prompt says that each task starts in a fresh checkout, so the worker does not assume its task 1 files are still present.

The `no_change` control has no headline pass, since it never changes a rule. Analysis reports it in its own table instead: how many valid records kept both rules in their original version.

There is no resume. A partial run needs a fresh output root, and `--resume` would have bypassed the spending cap. The runner refuses an existing model directory.

### Live-run gates

`run_bench.py --live` refuses to start unless these hold. Each check runs before any output directory or client exists.

- **Validation.** It needs `--validation <validation.json>` from `bench/validate.py`, which keeps only cases whose two tasks are both valid, or `--allow-unvalidated`.
- **Screening.** Every rule the plan uses must be marked `screened: true` in its rule file, or the run needs `--allow-unscreened`.
- **Images.** `docker image inspect` must find every planned task image.

The frozen manifest records the validation file, the dropped cases, both override flags, and any unscreened rules. During a run, `run_bench.py` and `screen_bench.py` both stop after three unfinished records in a row, of any status, and print status counts.

`bench/validate.py` also marks a task invalid when the image lacks the base commit (`git cat-file -e`) or when `git check-ignore` reports any rule path for the repository as ignored. An ignored rule directory would hide the worker's new files from scoring.

### Validation

`bench/validate.py --gold-runs 3` passes all 20 v1 tasks under the shipped config, so all 20 cases are usable. Each task's new tests fail at base, and the reference fix makes all its tests pass in three fresh containers in a row. The summary is `bench/manifests/validation-v1.json`, and live runs take it as `--validation`.

The case pairs changed twice on the way there:

| Validation file | Network | Valid | What it found |
|---|---|---|---|
| `validation-v1-network-none.json` | none, even for the tests | 16 of 20 | aiohttp, dbt-redshift, and setuptools tests need the network |
| `validation-v1-network-bridge.json` | on throughout | 19 of 20 | `pypa__setuptools-4985`'s reference fix fails its own tests |
| `validation-v1-scoring-network.json` | only while scoring | 19 of 20 | `pypa__setuptools-4980` is flaky |

setuptools-4980 passed once with the network on throughout. It then failed three runs in a row, each time on a different set of editable-install tests, which download packages. Repeating the gold run (`--gold-runs`) was added to catch this kind of task. With 4980 and 4985 both excluded, setuptools uses tasks 4870 and 4911. The two earlier files are the source of the `--exclude-invalid` flags in the manifest command above.

### Screening

Screening uses one worker on each case's first task, with three arms: no rule, original wording, and changed wording. Only `finished` runs count. Runs that end on `call_limit` or `model_protocol_error` are treated as unfinished in every arm and reported as a status mix, because truncated no-rule runs would bias the no-rule arm toward passing.

### v1 content

Ten repositories, two rules each, which gives 20 rules and 20 cases: `aio-libs/aiohttp`, `dbt-labs/dbt-redshift`, `Delgan/loguru`, `HypothesisWorks/hypothesis`, `pallets/click`, `PennyLaneAI/pennylane`, `pypa/setuptools`, `python-attrs/attrs`, `Qiskit/qiskit-terra`, and `stac-utils/pystac`. Each case carries a first task, a second task, and earlier tasks as history, all from the same repository. History takes the newest earlier trajectories until they reach `history_chars` (150,000 characters), which is one to five trajectories per repository.

The two tasks are the repository's latest two that pass validation. `bench/cases.py` rebuilds the manifest from the data, the rule files, and the config. It skips tasks that a validation summary marks invalid:

```sh
python3 bench/cases.py --data-root ~/bench-data --output bench/manifests/v1.json \
    --exclude-invalid bench/manifests/validation-v1-network-bridge.json \
    --exclude-invalid bench/manifests/validation-v1-scoring-network.json
```

That excludes setuptools tasks 4985 and 4980 (see [Validation](#validation)), so setuptools uses tasks 4870 and 4911. Its history is one earlier task.

Rule names are `change-entry`, `change-note`, `change-summary`, `changes-entry`, and `news-entry` (a change record), and `behavior-note`, `upgrade-note`, and `regression-test` (a second kind of file). Rule files are in `bench/rules/` and the manifest is `bench/manifests/v1.json`.

Three choices shaped the rules:

- **No issue number.** Rules omit the issue number because agents are never told it. The problem statements do not contain it. This keeps rules followable without changing how tasks are shown. The cost is that rules are less ticket-specific. A later option is for the harness to prefix "Issue #N:".
- **One change type.** Every rule changes in the same way: from one file, either an existing file or a location that may not exist yet, to a new file per change in a new directory. The checker labels the final files by looking for an added line in the old file or a new file in the new directory.
- **`repo_prior`.** Each rule records `repo_prior` as `old`, `new`, or `none`. It says whether the repository's own files pull an agent toward the old location, the new one, or neither. The change direction stays file to per-change directory for all rules. Recording the prior keeps v1 stable and lets analysis stratify by it. Without stratifying, the repository's pull confounds comparisons of delivery methods. Each scored record stores both rules' `repo_prior`, and `tables.md` reports each cell's headline split by the changed rule's prior.

### Infrastructure state

`bench/aws/user-data.sh` is the cloud-init script for the Ubuntu x86 host. It installs Docker and Python 3.12, installs pyarrow with pip into the `/opt/bench-venv` virtualenv, and creates `ssm-user` in the docker group. The host is a c7i.4xlarge in us-east-1 with a 500 GB disk. It has no inbound ports and is reached only through SSM Session Manager. Code and data reach it through a private S3 bucket. It is stopped between uses.

### Open items

- All 20 rules are unscreened. Some may be dropped at screening.
- The live path has run against real Docker but not a real model. A smoke test on the click task checked file writes, path checks, command timeouts, change detection, and the network switch: the agent's request to PyPI fails, and the scorer's succeeds. Offline tests use scripted clients and a fake container runner.
- One qiskit-terra history trajectory contains a submit command that failed in the original run. It is left as recorded.
- The SlopCodeBench track is not started, and its license is unchecked.

## What is left to the builder

This list is historical. It records what the design left open before the build. "As built" above records how each item was settled.

- How to group tasks into cases and order them.
- How to splice VibeMemBench trajectories into worker histories, and how to build the manager's history.
- When compaction triggers, and how to compact manager and worker histories at the same time.
- How each rule checker is written.
- Release format.
