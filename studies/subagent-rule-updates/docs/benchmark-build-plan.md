# Rule-change benchmark build plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a benchmark of real coding tasks where a user changes a rule mid-session in a manager-and-persistent-worker team, with compaction on the manager, the worker, both, or neither.

**Architecture:** A new `bench/` package inside the study reuses the existing tool loop (`worker.run_agent`), compactors (`compaction.compact`, `pi_compaction.compact`), and client (`provider.OpenRouterClient`). Tasks and their Docker images come from SWE-rebench V2. Real agent trajectories from VibeMemBench become the history that gets compacted. Rules are JSON specs with file-based matchers. Every model-facing component is tested offline with scripted clients and a fake container.

**Tech Stack:** Python 3.10+, standard library plus `pyarrow` (to read parquet), `unittest`, Docker on an AWS x86 host.

**Spec:** `studies/subagent-rule-updates/docs/benchmark-design.md`

## Global Constraints

- No paid model calls during the build. Every test uses scripted clients. Live runs need `--live`, as in the existing CLIs.
- Every client keeps `provider.py`'s per-run budget and request caps. No silent retries of paid requests.
- Raw request logs stay local and uncommitted (the study's `.gitignore` rule).
- Never commit benchmark data. Committed manifests hold instance IDs, rule specs, and validation results only, not problem statements, patches, or trajectories.
- Rules sit in the conversation in every condition except `store`. `creation_pin` puts the rules in a new worker's system prompt once, at creation.
- The manager prompt is identical in every condition.
- A task counts as following the new version only if the new-version matcher fires and the old one does not.
- Outcome labels are `new`, `old`, `both`, `neither`.
- First version: Python repositories only (`language == "python"`).
- Match the study's style: `from __future__ import annotations`, the atomic `save(path, value)` JSON writer, modules under 500 lines.
- Run tests with `python3 -m unittest discover -s studies/subagent-rule-updates/tests -t studies/subagent-rule-updates` from the repository root.
- Commit subjects follow the `commit-conventions` skill, for example `feat(subagent-rule-updates): add rule matchers`. One line, no trailers.

## Review Focus

1. A command that hangs or prints megabytes inside the container should time out after 120 seconds and return a truncated tail, not stall the run. Owned by Task 4.
2. A path that escapes the repository (`../`, absolute paths, symlinks) should be rejected for reads and writes. Owned by Task 4.
3. A worker that edits the same test files the hidden test patch touches should be scored with `test_patch_conflict: true`, not crash. Owned by Task 5.
4. A matcher must not fire on content that existed at the base commit, such as an old changelog entry. Only added lines and new files count. Owned by Task 3.
5. A trajectory with malformed steps (no command block, missing output) should skip those steps and keep the rest. Owned by Task 2.

---

### Task 1: Task and trajectory sources

**Files:**
- Create: `studies/subagent-rule-updates/bench/__init__.py` (empty)
- Create: `studies/subagent-rule-updates/bench/sources.py`
- Test: `studies/subagent-rule-updates/tests/test_bench_sources.py`

**Interfaces:**
- Produces:
  - `TaskRow` frozen dataclass with fields `instance_id: str, repo: str, base_commit: str, problem_statement: str, image_name: str, language: str, created_at: int, test_cmd: str, log_parser: str, fail_to_pass: tuple[str, ...], pass_to_pass: tuple[str, ...], patch: str, test_patch: str, license: str`.
  - `load_rows(parquet: Path, *, language: str | None = "python") -> list[TaskRow]`. `test_cmd` and `log_parser` come from `install_config`.
  - `issue_number(instance_id: str) -> int`: the trailing integer, for example `"owner__repo-1234"` gives `1234`.
  - `trajectory_index(history_root: Path) -> dict[str, dict[str, Path]]`: repo (`owner/repo`) to instance ID to `.traj.json` path, following `<language>/<repo>/<instance_id>/<instance_id>.traj.json`.

- [ ] **Step 1:** Download the datasets on the build machine (not into the repository): `hf download Tongyi-ConvAI/VibeMemBench --repo-type dataset --local-dir ~/bench-data/vibemem` and the `nebius/SWE-rebench-V2` parquet into `~/bench-data/swe-rebench-v2`. Record each dataset's license (SWE-rebench V2 is CC-BY-4.0 per its card; check VibeMemBench's card) in the design doc's sources section.
- [ ] **Step 2:** Write the failing tests. Build a two-row parquet in a temp dir with `pyarrow` (one Python, one JavaScript row) and a fake history tree. Assert `load_rows(p)` returns one row with `test_cmd` from `install_config`, `load_rows(p, language=None)` returns two, `issue_number("psf__requests-6028") == 6028`, and `trajectory_index` maps `"psf/requests"` to its instance IDs. Confirm the real repo folder naming in `history/` from Step 1 first and mirror it in the fixture.
- [ ] **Step 3:** Run the tests and see them fail.
- [ ] **Step 4:** Implement `sources.py`.
- [ ] **Step 5:** Run the tests and see them pass. Commit.

### Task 2: Trajectories as conversation history

**Files:**
- Create: `studies/subagent-rule-updates/bench/history.py`
- Test: `studies/subagent-rule-updates/tests/test_bench_history.py`

**Interfaces:**
- Consumes: `trajectory_index` paths from Task 1. The tool name `run_command` from Task 4.
- Produces:
  - `load_trajectory(path: Path) -> list[dict]`: the raw message list.
  - `to_worker_messages(raw: list[dict], *, call_prefix: str, max_output_chars: int = 2000) -> list[dict]`: each assistant step with a command block becomes an assistant message with one `run_command` tool call (`{"command": ...}`), and the next observation becomes the matching `tool` message, truncated to its last `max_output_chars`. The task statement becomes the first `user` message. The final assistant text becomes a closing assistant message.
  - `manager_block(problem_statement: str, worker_reply: str, call_id: str) -> list[dict]`: a user message with the problem statement, a manager `message_worker` call carrying it verbatim, its tool result `{"worker": "worker-1", "status": "finished", "reply": worker_reply}`, and a short manager reply `"Done."`.
  - `FillerBlock` dataclass: `instance_id: str, manager: list[dict], worker: list[dict]`.
  - `filler_block(instance_id: str, raw: list[dict]) -> FillerBlock`.

- [ ] **Step 1:** Open one real `.traj.json` from Step 1 of Task 1. Copy a trimmed three-step excerpt into `tests/fixtures/bench/sample.traj.json`, keeping the real field names and the real command-block and observation formats (mini-swe-agent at commit `bc85a456`).
- [ ] **Step 2:** Write failing tests on the fixture. Assert tool-call IDs are unique and prefixed by `call_prefix`, every tool call has exactly one matching `tool` message, a step with no command block produces no tool call and no error, an observation longer than 2,000 characters keeps only its tail, and `filler_block` puts the trajectory's final assistant text into the manager's tool result.
- [ ] **Step 3:** Run and see them fail. Implement. Run and see them pass. Commit.

### Task 3: Rule specs and matchers

**Files:**
- Create: `studies/subagent-rule-updates/bench/rules.py`
- Test: `studies/subagent-rule-updates/tests/test_bench_rules.py`

**Interfaces:**
- Produces:
  - `Changes = dict[str, tuple[str | None, str | None]]`: path to (base content, final content). `None` means absent.
  - `RuleSpec` frozen dataclass: `id: str, repo: str, original: str, changed: str, old: dict, new: dict`. `old` and `new` are matcher dicts.
  - Matcher types:
    - `{"type": "new_file", "dir": str, "name_regex": str}`: a file absent at base now exists under `dir` and its name matches.
    - `{"type": "added_line", "path_glob": str, "line_regex": str}`: a line present in the final file but not at base matches, in a file matching the glob.
    - Regexes may contain `{issue}`, filled from the scored task's issue number.
  - `matches(matcher: dict, changes: Changes, *, issue: int) -> bool`.
  - `classify(rule: RuleSpec, changes: Changes, *, issue: int) -> dict` returning `{"outcome": "new" | "old" | "both" | "neither", "old": bool, "new": bool}`.
  - `load_rules(path: Path) -> list[RuleSpec]`: reads `bench/rules/<owner>__<repo>.json` (a JSON list), and raises `ValueError` on duplicate IDs, an unknown matcher type, or `original == changed`.

- [ ] **Step 1:** Write failing tests:
  - `added_line` on a changelog with an existing old entry and no new line gives `False`.
  - Adding `"- 6028: fix redirect"` with `line_regex` `"^- {issue}:"` and `issue=6028` gives `True`.
  - `new_file` with `dir="changelog"` and `name_regex` `"^{issue}\\.bugfix\\.rst$"` fires for a new `changelog/6028.bugfix.rst` and not for an edited existing file.
  - `classify` returns `both` when both matchers fire.
  - `load_rules` rejects a duplicate ID.
- [ ] **Step 2:** Run and see them fail. Implement. Run and see them pass. Commit.

### Task 4: Container workspace

**Files:**
- Create: `studies/subagent-rule-updates/bench/container.py`
- Test: `studies/subagent-rule-updates/tests/test_bench_container.py`

**Interfaces:**
- Consumes: `Changes` from Task 3.
- Produces:
  - `Runner` protocol: `run(args: list[str], *, input: str | None = None, timeout: int) -> tuple[int, str, str]`.
  - `DockerRunner()`: runs `docker` through `subprocess`. A timeout returns exit code `124`.
  - `TOOLS`: the OpenAI-format tool list for `read_file(path)`, `write_file(path, content)`, `run_command(command)`, built like `worker._tool`.
  - `ContainerWorkspace(image: str, runner: Runner, *, workdir: str, event_log: Path | None = None, command_timeout: int = 120, max_output_chars: int = 10000)`, with:
    - `start() -> None` and `stop() -> None`, which run `docker run -d` and `docker rm -f`.
    - `execute(name: str, args: Any, *, call_index: int) -> dict`, with the same contract and event log format as `worker.Workspace.execute`.
    - `changes(base_commit: str, *, exclude: set[str] = frozenset()) -> Changes`, from `git diff --name-status <base>` plus untracked files, reading base content with `git show <base>:<path>`.
    - `events: list[dict]`.

- [ ] **Step 1:** Look up the repository working directory inside SWE-rebench V2 images (`install_config.docker_specs` or the base Dockerfiles in `SWE-rebench/SWE-rebench-V2`). Store it as `workdir` per row if it varies, and add it to `TaskRow` in Task 1 if so.
- [ ] **Step 2:** Write failing tests with a `FakeRunner` that records argument lists and returns scripted outputs:
  - `read_file("../etc/passwd")` and `write_file("/abs", ...)` return `{"error": ...}` and issue no docker call.
  - A `run_command` whose runner returns exit code `124` gives `{"exit_code": 124, "timed_out": true, ...}`.
  - A 50,000-character output is cut to its last 10,000 characters with `"truncated": true`.
  - `write_file` sends the content through `input=`, not the command line.
  - `changes()` parses a scripted name-status listing into the expected `Changes`, including an added untracked file with base `None`.
- [ ] **Step 3:** Run and see them fail. Implement. Run and see them pass. Commit.

### Task 5: Test scoring

**Files:**
- Create: `studies/subagent-rule-updates/bench/evaluate.py`
- Create: `studies/subagent-rule-updates/bench/vendor/` holding the pytest log parser copied from `SWE-rebench/SWE-rebench-V2`, with its license file
- Test: `studies/subagent-rule-updates/tests/test_bench_evaluate.py`

**Interfaces:**
- Consumes: `TaskRow` (Task 1), `ContainerWorkspace` (Task 4).
- Produces:
  - `parse_log(log_parser: str, output: str) -> dict[str, str]`: test ID to `PASSED`, `FAILED`, or `SKIPPED`. It raises `ValueError` for a parser name it does not support.
  - `score_tests(ws: ContainerWorkspace, row: TaskRow) -> dict` returning `{"resolved": bool, "test_patch_conflict": bool, "fail_to_pass": {id: status}, "pass_to_pass": {id: status}}`. It applies `row.test_patch` with `git apply`. A failed apply sets `test_patch_conflict: true` and `resolved: false` without raising. It then runs `row.test_cmd`.
  - `test_patch_paths(test_patch: str) -> set[str]`: the files a test patch touches, for use as `exclude` in `changes()`.

- [ ] **Step 1:** Write failing tests. Parse a captured pytest log fixture into the expected statuses. Check `resolved` is true only when every FAIL_TO_PASS and PASS_TO_PASS ID passes. A scripted `git apply` failure gives `test_patch_conflict: true` with no exception. `test_patch_paths` on a two-file diff returns both paths.
- [ ] **Step 2:** Run and see them fail. Vendor the parser and implement. Run and see them pass. Commit.

### Task 6: Cases

**Files:**
- Create: `studies/subagent-rule-updates/bench/cases.py`
- Test: `studies/subagent-rule-updates/tests/test_bench_cases.py`

**Interfaces:**
- Consumes: `TaskRow`, `issue_number`, `trajectory_index` (Task 1), `load_trajectory` and `to_worker_messages` (Task 2), `RuleSpec` (Task 3), `compaction.render_history`.
- Produces:
  - `Case` frozen dataclass: `case_id: str, repo: str, first: str, second: str, history: tuple[str, ...], changed_rule: str, unchanged_rule: str`. Task fields are instance IDs.
  - `build_cases(rows: list[TaskRow], trajectories: dict[str, dict[str, Path]], rules: dict[str, list[RuleSpec]], *, history_chars: int, seed: int) -> list[Case]`:
    - For each repository with exactly two rules and at least two tasks, pick `second` as the latest-created task and `first` as the next latest.
    - Pick history trajectories with `issue_number` below the second task's, excluding both task IDs, newest first, until the rendered worker messages reach `history_chars`. Skip the repository if they never do.
    - Emit two cases, one per changed rule. `case_id` is `"<owner>__<repo>--<changed_rule>"`.
  - `save_manifest(cases: list[Case], path: Path) -> None` and `load_manifest(path: Path) -> list[Case]`.

- [ ] **Step 1:** Write failing tests with three fake rows and four fake trajectories:
  - History never includes a trajectory with an issue number at or above the second task's.
  - A repository with one rule yields no cases.
  - Each qualifying repository yields exactly two cases with swapped changed and unchanged rules.
  - The manifest round-trips.
  - The saved manifest contains no `problem_statement` or `patch` text.
- [ ] **Step 2:** Run and see them fail. Implement. Run and see them pass. Commit.

### Task 7: Session engine (conditions and placements)

**Files:**
- Create: `studies/subagent-rule-updates/bench/session.py`
- Test: `studies/subagent-rule-updates/tests/test_bench_session.py`

**Interfaces:**
- Consumes: `worker.run_agent`, `worker.final_text`, `compaction.compact`, `compaction.render_history`, `pi_compaction.compact` and `PiState`, plus Tasks 1 to 6.
- Produces:
  - `Cell` frozen dataclass: `condition: str, placement: str, worker_type: str`.
  - `CELLS: tuple[Cell, ...]`, which must equal exactly:
    - existing worker × {`relay`, `reinsert`, `store`} × {`none`, `manager`, `worker`, `both`}
    - new worker × {`relay`, `creation_pin`, `store`} × {`none`, `manager`}
    - plus the control `Cell("no_change", "none", "existing")`.

    That is 19 cells.
  - `MANAGER_SYSTEM: str`: as `relay.MANAGER_SYSTEM`, plus "Pass on any user instructions the worker needs." The same in every cell.
  - `user_turns(case: Case, rules: dict[str, RuleSpec], rows: dict[str, TaskRow]) -> list[str]`:
    - U0: both original rules, then the first problem statement.
    - U1: `"A change to one of my rules, effective now: <changed>"`.
    - U2: the second problem statement, with no rules restated.
    - `no_change` omits U1.
  - `run_cell(client, case: Case, cell: Cell, *, rules, rows, trajectories, outdir: Path, config: dict, workspace_factory: Callable[[TaskRow, Path], ContainerWorkspace]) -> dict`:
    1. Run U0 live. The manager delegates and worker-1 works in task 1's container.
    2. Run U1 live.
    3. Append each history `FillerBlock` (manager part to the manager's history, worker part to worker-1's). After each block, compact each history named by the placement once its `render_history` length passes `config["compact_threshold_chars"]`, using `config["compactor"]` (`"generic"` or `"pi"`). In `reinsert`, append U1 verbatim after each compaction of that history.
    4. For `new` worker cells, replace worker-1's history with an empty one and, under `creation_pin`, set its system prompt to `worker.WORKER_SYSTEM` plus the current rules.
    5. Run U2 live in task 2's container.
    6. Score with `classify` on `changes(base, exclude=test_patch_paths(...))` for both rules, and with `score_tests`.

    Under `store`, both system prompts carry a current-rules block on every call, switched at U1. The record holds the cell, per-turn status, deliveries, compaction events, the final rule outcomes, the tests, and the context hashes per call (as in `harness.digest`).
  - `headline_pass(record: dict) -> bool`: true when the changed rule is `new` and the unchanged rule is `old`.

- [ ] **Step 1:** Write failing tests with a scripted client (pattern: `tests/test_relay.py::ScriptedTeam`), a scripted summarizer, and a fake workspace factory over the `FakeRunner`:
  - `len(CELLS) == 19` and no `new`-worker cell has placement `worker` or `both`.
  - Under `relay` with placement `none`, no compaction events occur.
  - Under placement `manager`, only the manager history is compacted; under `worker`, only worker-1's.
  - Under `reinsert`, U1's exact text follows every compaction.
  - Under `store`, every request's system message after U1 contains the changed rule and none before it does.
  - Under `creation_pin` with a new worker, the U2 worker request's system prompt contains the changed rule and its history is empty before U2.
  - The manager system prompt is byte-identical across all 19 cells.
- [ ] **Step 2:** Run and see them fail. Implement. Run and see them pass. Commit.

### Task 8: Runner and analysis

**Files:**
- Create: `studies/subagent-rule-updates/bench/run_bench.py`
- Create: `studies/subagent-rule-updates/configs/bench-v1.json`
- Test: `studies/subagent-rule-updates/tests/test_bench_run.py`

**Interfaces:**
- Consumes: Tasks 1 to 7, `provider.OpenRouterClient`.
- Produces:
  - CLI `python3 studies/subagent-rule-updates/bench/run_bench.py --config <json> --manifest <json> --output <dir> [--cells <comma list>] [--cases <comma list>] [--model-index N] [--live]`. Without `--live`, it writes `plan.json` (case × cell × repetition, shuffled by `order_seed`) and makes no calls.
  - `analyze(output: Path) -> dict`, writing `summary.json` and `tables.md`. For each cell it reports the counts of `new`, `old`, `both`, and `neither` for the changed rule, the unchanged rule kept, the headline passes, the tests resolved, and the provider cost.
  - The config keys are those in `configs/rule-compaction.json`, plus `data_root`, `compactor`, `history_chars`, `compact_threshold_chars`, and `max_manager_calls`.

- [ ] **Step 1:** Write failing tests:
  - A run without `--live` writes `plan.json` and never builds a client.
  - `--live` refuses an existing output directory, matching `run.py`.
  - `analyze` over two hand-written records gives the expected counts.
- [ ] **Step 2:** Run and see them fail. Implement. Run and see them pass. Commit.

### Task 9: Rule screening runner (for evaluation time)

**Files:**
- Create: `studies/subagent-rule-updates/bench/screen_bench.py`
- Test: `studies/subagent-rule-updates/tests/test_bench_screen.py`

**Interfaces:**
- Consumes: Tasks 1 to 4, `screen.MAX_DEFAULT_COMPLIANCE`, `screen.MIN_TOLD_COMPLIANCE`.
- Produces:
  - `arms() -> list[str]` returning `["none", "original", "changed"]`.
  - A CLI with the same flags as Task 8. It runs one worker, with no manager and no compaction, on each case's first task under each arm.
  - `screen_verdicts(records: list[dict]) -> dict[str, dict]`: rule ID to `{"passed": bool, "none_match_rate": float, "original_follow_rate": float, "changed_follow_rate": float}`. A rule passes only if the `none` arm matches either version in at most 20% of runs, and each told arm follows its version in at least 90%.

- [ ] **Step 1:** Write failing tests. Check `screen_verdicts` on hand-built records at the 20% and 90% boundaries, and that a run without `--live` makes no calls.
- [ ] **Step 2:** Run and see them fail. Implement. Run and see them pass. Commit. Do not run it live. Screening is the first step of evaluation.

### Task 10: AWS host and task validation

**Files:**
- Create: `studies/subagent-rule-updates/bench/validate.py`
- Create: `studies/subagent-rule-updates/bench/aws/user-data.sh`
- Test: `studies/subagent-rule-updates/tests/test_bench_validate.py`

**Interfaces:**
- Consumes: Tasks 1, 4, 5, 6.
- Produces:
  - `validate_task(row: TaskRow, runner: Runner, workdir: str) -> dict` returning `{"instance_id", "gold_resolved": bool, "base_fail_to_pass_failing": bool, "valid": bool}`:
    - Gold patch plus test patch must resolve.
    - Test patch alone must leave every FAIL_TO_PASS test failing.
  - The CLI `validate.py --manifest <json> --data-root <dir> --output <dir>` writes one JSON per task and `validation.json`.

- [ ] **Step 1:** Write failing tests for `validate_task` with a `FakeRunner`. One test scripts a gold run that passes and a base run that fails, giving `valid: true`. Another scripts a base run where a FAIL_TO_PASS test already passes, giving `valid: false`.
- [ ] **Step 2:** Run and see them fail. Implement. Run and see them pass. Commit.
- [ ] **Step 3:** Write `user-data.sh`: install Docker and Python 3.12 on Ubuntu 24.04, add the `ubuntu` user to the `docker` group.
- [ ] **Step 4:** Confirm with the user before launching paid resources. Then use the AWS MCP `run_script` tool to launch one `c7i.4xlarge` instance in `us-east-1`:
  - Ubuntu 24.04 with a 500 GB gp3 root volume and the user data above
  - access through SSM Session Manager, with no SSH key or open inbound ports
  - tags `project=context-research` and `owner=subagent-rule-updates`

  Record the instance ID in the design doc's infrastructure section.
- [ ] **Step 5:** On the instance, clone the repository, download the data (Task 1 Step 1), and run `validate.py` on the manifest from Task 11. Expected: `validation.json` lists every task, and invalid tasks are dropped from the manifest.
- [ ] **Step 6:** Stop the instance when idle. Do not terminate it without asking.

### Task 11: First-version content

**Files:**
- Create: `studies/subagent-rule-updates/bench/rules/<owner>__<repo>.json`, one per repository
- Create: `studies/subagent-rule-updates/bench/manifests/v1.json`
- Test: `studies/subagent-rule-updates/tests/test_bench_content.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 6, 10.

- [ ] **Step 1:** List Python repositories that appear in both VibeMemBench's history and SWE-rebench V2, with at least two SWE-rebench V2 tasks and enough history to reach `history_chars` (Task 6). Pick about 10, preferring ones with a written contributor convention (changelog fragments, release notes, a "what's new" file, docs for config, and similar).
- [ ] **Step 2:** For each repository, write two rules into its JSON file.
  - The original wording follows the repository's real convention where one exists.
  - The changed wording is ours.
  - Where the real convention is visible enough that a no-rule agent would follow it, write both versions ourselves instead (design doc, "The rule layer").
  - Each rule's three outcomes (old, new, neither) must leave different files.
- [ ] **Step 3:** Write failing content tests. For every rule file, `load_rules` succeeds. For every rule, hand-written `Changes` examples labeled old, new, and neither classify as labeled. At least one example per rule is built from the real task's gold patch plus the rule-related file.
- [ ] **Step 4:** Run and see them fail, then add the examples until they pass.
- [ ] **Step 5:** Build `manifests/v1.json` with `build_cases`. Run Task 10 Step 5 against it. Drop invalid tasks, rebuild, and commit the rules, the manifest, and `validation.json`. Mark every rule `"screened": false` in the manifest.

### Task 12: Documentation

**Files:**
- Modify: `studies/subagent-rule-updates/README.md` (the file table and a short "Benchmark" section)
- Modify: `studies/subagent-rule-updates/docs/benchmark-design.md` (sources' licenses, AWS instance, any calls changed during the build)

- [ ] **Step 1:** Add the `bench/` modules to the README's file table. Add the dry-run command and the offline test command, plus one paragraph saying rules are unscreened until evaluation starts. Use the `plain-docs` skill.
- [ ] **Step 2:** Run the full offline suite. Expected: all tests pass, including the existing ones. Commit.
