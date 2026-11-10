# Tunables screening pilot 001

Run on November 10 and 11, 2026, for the real-task study (`docs/real-task-study-design.md`). Raw outputs hold problem statements and are not committed. They are archived in the benchmark host's S3 bucket (`results/bench-tunables-screen-001.tgz`).

## What ran

All 41 usable tasks from `bench/manifests/tunables-judged.json`, in three groups. Per task: validation, a gold-fix extraction check, then one worker with no history and no compaction in three arms (no rule, R-const, R-env), 3 runs each, on GPT-6 Luna. Claude Opus 5.5 then adjudicated every extracted value, without seeing the arm or the rules.

- 338 runs finished, 5 ended in a model protocol error, and 1 in a provider error. The provider error (a response missing usage data) stopped group 1 on its last task, yelp-mrjob-2197, after 5 of 9 runs.
- Worker runs cost about $1.19 and adjudication about $1.15.
- A run took about 50 seconds including about 14 seconds of tests, and each task's setup (image pull and validation) about 1.5 minutes. The whole pilot took about 2.8 hours with three runners.
- Two tasks failed validation: pipx-318 and sabnzbd-1969.

## Results

The extractor and judge work on real code. They found the gold fix's tunable in 37 of 39 valid tasks.

When told, the worker followed the rules. Among told runs that added a tunable, R-const was followed in 37 of 41 and R-env in 37 of 39.

The bottleneck is applicability. Without a rule, the worker added a tunable in only 34 of 113 runs (24 inline, 10 already as a named constant). It usually fixed the bug without one. Told runs were the same: 70 of 111 R-const runs and 75 of 112 R-env runs added no tunable.

| Screening outcome | Tasks |
|---|---|
| Kept | 7 |
| Worker did not hardcode a tunable without a rule (fewer than 2 of 3 runs) | 30 |
| Hardcoded without a rule, but a told arm was not followed in 2 of 3 runs | 2 |
| Invalid | 2 |

Kept tasks: ecmwf-earthkit-data-126, fsspec-filesystem_spec-1791, googleapis-python-bigquery-2135, googlecloudplatform-cloud-sql-python-connector-1241, leshchenko1979-fast_bitrix24-114, pydap-495, senth-minecraft-mod-manager-171.

The two tasks that hardcoded without a rule but failed a told arm: fatiando-harmonica-487 added no tunable in any told run, and mlcommons-medperf-604 violated R-env in 2 of 3 runs.

## What this means

Seven tasks are too few for the planned study. Choosing tasks by what the gold fix contains does not predict what the agent writes: a gold fix with a tunable led the agent to hardcode one in only about a quarter of tasks.

The next pool should be chosen by agent behavior, not gold content. A cheap first stage would run only the no-rule arm on a broad, mechanically chosen pool (for example every task whose gold fix adds a numeric literal to non-test source) and keep tasks that hardcode a tunable in at least 2 of 3 runs, then run the told arms on those. At the measured rate this needs several hundred candidate tasks to reach 40 or more.

## Problems found while running

- The judge sometimes wrote a sentence before its JSON despite JSON mode. The parser now reads the object wherever it starts (`274b7c0f`).
- A host-side `pgrep -fc <script>` count matched the remote command's own text, so liveness checks in watchers overcounted. A rerun was started twice and one copy was stopped. Adjudication resumes by key, so nothing was lost or double counted in the results.
