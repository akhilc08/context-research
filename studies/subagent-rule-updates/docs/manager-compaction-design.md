# Design: manager compaction

Status: draft for review. Nothing is built yet.

## Question

The user states two rules, then changes one mid-session. Later the manager's own history is compacted. When the manager then hands a task to a subagent, does the subagent follow the current rule?

This is the step after subagent compaction (`FINDINGS.md` sections 6 to 8). There, only the subagent's history was compacted, and the manager was a fixed script. Here, only the manager's history is compacted, and the manager is a real model, because what it writes after compaction is the thing being measured.

## Why it matters

In `relay-001` the manager restated the full current rules with every task it delegated. So the manager's history is the copy of the rules that every subagent depends on. If compaction weakens or drops a rule there, the manager can pass the weakened version to every subagent it delegates to afterward. A single agent has no equivalent of this.

No publication we found measures it. MasDrift (`docs/SOURCES.md` R02) measures constraint loss at handoffs without compaction. Governance Decay, CompInt, and ARCBench (R07, R08, R01) measure compaction loss in a single agent. "When Do Summaries Become Instructions?" (R03) measures summaries that rewrite policy, also in a single agent. AutoGen's group manager (R16) compacts a shared history for every agent, but nobody has measured the effect.

## What stays fixed

Everything established in the second series:

- The fixture repository, the two screened rules (changelog and config values), and both scored tasks (INV-212 bulk discount and INV-215 low stock), scored from the final files by `scenarios.py`.
- The worker's system prompt and tools (`worker.py`).
- The generic compactor (`compaction.py`), its prompt, the 137,500-character threshold, and at least two rounds.
- The read-only log filler (25 tasks, 220 lines each).
- GPT-6 Luna, temperature 0.2, low reasoning effort.
- The manager instruction from `relay-001`: relay rule changes to workers.

## Session

1. **Rules.** The user gives the manager both rules and a read-only warmup task.
2. **Change.** The user changes one rule and gives a read-only task.
3. **Filler.** The user gives the manager the 25 read-only log tasks. The manager does them itself with read-only tools, so only the manager's history grows.
4. **Compaction.** In the compacted condition, the manager's history is compacted whenever it passes the threshold, as in the subagent series. The manager's system prompt is never compacted, and the rules exist only in its conversation.
5. **Scored task.** The user gives a coding task on a fresh copy of the repository. The manager cannot write files, so it must delegate.

The manager gets three tools: `list_files` and `read_file` (read-only), and `spawn_worker(name, prompt)`.

**Conditions.** `manager_no_compact` and `manager_compact`, with an identical session except for compaction. Each runs once with the changelog rule changed and once with the config rule changed.

## Decision for review: which subagent does the scored task

| Variant | What happens | What it isolates |
|---|---|---|
| **A. New subagent** (recommended first) | The scored task goes to a subagent spawned after the manager compacted. It knows the rules only from the manager's spawn prompt. | The manager's compacted memory alone. Nothing else carries the rules. |
| B. Existing subagent | A subagent that received the verbatim relay before the manager compacted also does the scored task. | Whether a weakened restatement from the manager overrides an earlier verbatim relay. Two copies of the rule compete. |

Variant A is closest to the setup where a manager writes the rules into spawn prompts. In variant A the manager never delegates before the scored task. All earlier tasks are read-only, and the manager does them itself.

## What we measure

Following MasDrift's handoff labels (R02), each scored session is checked at three points.

| Point | Label | How |
|---|---|---|
| 1. Manager's final summary | Changed rule current, old, weakened, or absent | Keyword markers, as in the subagent series, plus reading every summary |
| 2. Manager's spawn prompt | Changed rule verbatim or close, weakened, old, or absent. Same for the unchanged rule. | Keyword markers for presence. Force markers for weakening, such as "do not hardcode" for the config rule and "start each entry with the ticket ID" for the changelog rule. Ambiguous prompts are read by hand. |
| 3. Subagent's files | New version, old version, or neither | `scenarios.py` classifiers, unchanged |

Each failure is assigned to the first point where the rule degraded: lost in the summary, lost in the restatement, or ignored by the subagent despite a correct prompt.

## Predictions, written before any run

1. Without compaction, the spawn prompt carries the current rules in nearly every session, as in `relay-001`, and the subagent follows the changed rule in at least 19 of 20 branches.
2. With compaction, the changelog rule survives, as it did under subagent compaction.
3. With compaction, the config rule fails in some branches.
4. Most failures trace to point 1 or 2, a weakened or missing rule in the manager's summary or spawn prompt. When the spawn prompt states the rule correctly, the subagent follows it. The rule screen showed 10 of 10 when the rule is stated next to the task.
5. Loss happens mostly at the first compaction (the first encoding), and later restatements copy the summary faithfully, as Faithful, Not Corrective (R04) found for relays.

Any of these can fail. Prediction 4 failing would mean subagents ignore correctly relayed rules, which would point back at the subagent.

## Causal follow-up

After the main run, same-snapshot replay, following R03 and our `resample.py`:

1. **Resample the handoff.** From each saved compacted manager state, rerun the scored turn 5 times. This shows whether a weak spawn prompt is a property of the state or of sampling.
2. **Edit the summary.** In states whose spawn prompts were weak, replace only the rule line in the manager's summary with the user's original wording and rerun. If spawn prompts and subagent behavior recover, the summary's wording is the cause.

## Size and cost

10 repetitions, 2 changed rules, 2 conditions, and 2 scored tasks per prepared session make 80 scored branches. Based on the subagent runs, this should cost about $3 on Luna, plus about $0.50 for the follow-up. A one-repetition pilot runs first.

## Out of scope for this step

- Both agents compacting. That comes after this step, one variable at a time.
- The store and re-insertion. The store bypasses the manager by design, so it is a later comparison.
- Other models and compaction prompts.

## Built on

`relay.py` for the real manager and tool loop, `rule_compaction.py` for filler and compaction, `scenarios.py` and `worker.py` unchanged. The new code would be a manager session runner with read-only manager tools, `spawn_worker`, and the three-point scoring.
