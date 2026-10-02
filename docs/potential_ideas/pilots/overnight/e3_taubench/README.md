# E3: forced compaction on a modified τ-bench

This experiment asks whether compacting away an operator policy hurts a tool-using agent on τ-bench (Sierra), and whether re-attaching the policy (pinning) or a Watchpoint check repairs the damage. It runs on a **modified τ-bench**: the policy is moved out of the system prompt into the conversation history and compaction is forced partway through every task. Numbers here are not comparable to published τ-bench scores.

Both the agent and the simulated user run on `stealth/space-bunny-alpha` through `../orclient.py`. Grading is τ-bench's own reward: the final database hash must match the gold one, and any required output strings must appear in the agent's replies. No keyword lists or judges are involved in the reward.

## Summary

- **In standard retail τ-bench, compaction barely changes reward, and the Watchpoint does not help.** Over 115 tasks with 2 trials each (230 runs per arm), reward was 0.657 with the policy in history and no compaction, and 0.626 with compaction. The paired difference is -0.030 (95% CI -0.100 to +0.035; sign test p = 0.45, Holm-adjusted p = 1). Pinning scored 0.626 and Watchpoint 0.570. None of the 10 planned comparisons is significant, before or after Holm correction.
- **The main reason is that this policy carries little reward-relevant information for this model.** Removing the policy entirely scored 0.648, no lower than the τ-bench default with the policy in the system prompt (0.626). The retail tool descriptions repeat the key rules, the tools enforce several rules in code, and the reward only checks the final database, which the simulated user's cooperation usually makes correct anyway. This was not a timing problem: in 203 of 205 compacted runs that wrote to the database, the policy had already been compacted away before the first write.
- **Compaction does make the agent break process rules that the reward cannot see** (exploratory). With the policy sentences stripped out of the tool descriptions, writes made without first getting an explicit "yes" from the user rose from 4.3% of runs (no compaction) to 26.1% (compaction), Holm p = 7e-6. Pinning (8.7%) and Watchpoint (7.8%) both brought it back down (Holm p = 0.001 each). Reward moved in the same direction but not significantly: compaction 0.557 vs 0.643 without it, pin 0.652, Watchpoint 0.643 (one trial, n = 115).
- **Watchpoint was never selective.** Every one of 470 post-compaction checks in the main run found missing rules (10.3 of 18 on average) and patched them, so it behaved like a partial pin that costs about 3 times as many model calls per task as plain compaction (60.9 vs 22.4) and 1.5 times the input tokens (116k vs 75k).
- **Airline (50 tasks, one trial) is also null for compaction.** Reward was 0.40 with the policy in history, 0.44 with compaction, 0.46 with pin or Watchpoint. Moving the policy out of the system prompt cost 12 points before any compaction (0.52 to 0.40, CI -0.30 to +0.04, not significant).

For loose orientation only: the `standard` arm (0.626 retail, 0.52 airline) sits in the range the original τ-bench paper reported for strong tool-calling models (roughly 0.6 retail and 0.35 to 0.45 airline for GPT-4o-class agents), but the model, user simulator and one prompt line differ, so this is not a replication.

Everything above uses one model as agent, user, summarizer and checker. Nulls here mean "no effect large enough to see with about 115 tasks", roughly 7 to 10 points.

## Hypotheses and metrics (set before the main run)

- **H1.** Compacting the policy out of verbatim context lowers reward compared with keeping the same policy-in-history conversation uncompacted.
- **H2.** Re-attaching the policy after each summary (pin) or patching the rules a Watchpoint check finds missing recovers that loss.
- **H3.** Watchpoint recovers the loss at lower cost than pinning, because it patches only rules that were actually lost.

The **primary metric** is average τ-bench reward (pass^1) on the 115 retail test tasks, compared per task between arms (paired). The **primary comparison** is `compact` vs `hist`. Secondary comparisons are `hist` vs `standard`, `pin`, `pinrules` and `watch` vs `compact`, `watch` vs `pin` and `pinrules`, the `watch_ctx` ablation, and `nopolicy` vs `standard`. All of these are one Holm-corrected family.

Analyses added after seeing data are labeled **exploratory** below. These are: the policy-violation flags and their paired test, the "stripped tool descriptions" variant, the exposure table, and the airline domain (planned as "if time permits" but its arms were not pre-registered beyond reusing the retail ones).

## What was modified in τ-bench

The τ-bench code, data, tools, tasks and grader are used unchanged from `/private/tmp/tau-bench`. The agent loop and the user simulator are reimplemented in `run.py` so both use `orclient.chat`.

1. **Policy placement.** In τ-bench the retail policy (`wiki.md`, 5,718 characters) is the agent's system prompt. In every arm except `standard`, the system prompt is the one-line generic description from τ-bench's own `rules.py` ("You are a customer service representative for an online retail company..."). The policy is inserted as the first history turn: a user-role message starting "[Operator message, not from the customer] Below is the policy you must follow for the whole conversation...", followed by a fixed assistant acknowledgement, followed by the customer's first message.
2. **Forced compaction.** In the compaction arms, compaction runs before the agent's 5th model call (after 4 agent steps), then again every 6 agent steps. Everything except the last 4 messages is folded into a summary; the cut moves forward if it would leave a tool result without its tool call. The policy is always in the folded part, so after the first compaction it is no longer in verbatim context. Compaction is recursive: later rounds see only the previous summary plus the new messages, never the original policy text. The summarizer gets a generic prompt (summarize "in under 200 words", "capture what has been done and what is still relevant going forward") with no instruction about policies. The summary is placed in a user-role message headed "[Summary of the conversation so far, written by the harness]".
3. **User simulator.** The τ-bench user prompt (`LLMUserSimulationEnv`) is copied verbatim, at temperature 1.0, with one added rule: "Facts stated in the instruction (your name, zip code, email, order ids, and so on) are things you know; share them when the agent asks for them." This was added after a smoke test where the simulated user claimed not to know the zip code in its own instruction and every task ended in a transfer before any policy mattered. `--plain_user` turns the line off.
4. **Agent settings.** Agent temperature 0, at most 30 agent steps (τ-bench default), only the first tool call of a message is executed (as in τ-bench's tool-calling agent), reasoning effort "low" (the `orclient` default), max 2,000 output tokens per call.

The tool schemas are never compacted, and τ-bench's retail tool descriptions repeat several policy rules (for example "The agent needs to explain the cancellation detail and ask for explicit user confirmation (yes/no) to proceed"). The retail tools also enforce some rules in code (order status checks, cancellation reasons, gift card balance). Both of these matter for interpretation, see the results.

## Arms

| arm | policy location | compaction | after each summary |
|---|---|---|---|
| `nopolicy` | nowhere (tool descriptions still carry some rules) | no | |
| `standard` | system prompt (τ-bench default) | no | |
| `hist` | first history turn | no | |
| `compact` | first history turn | yes | nothing |
| `pin` | first history turn | yes | full 5,718-character policy re-attached (Constraint Pinning) |
| `pinrules` | first history turn | yes | all 18 hand-split rules re-attached |
| `watch` | first history turn | yes | Watchpoint: extraction, per-rule comparator, patch missing rules only |
| `watch_ctx` | first history turn | yes | ablation: comparator reads the compacted context directly, no extraction |

**Watchpoint details.** The policy was hand-split once into 18 load-bearing rules (`rules_retail.json`; 19 for airline in `rules_airline.json`). Rules were written from the policy text alone, before any run, without looking at tasks or gold actions. After each compaction:

1. Extraction. The agent's compacted context plus "[Harness check, not from the customer; do not call any tool for this message] List every policy rule you must follow in this conversation..." is sent to the model. The reply is not added to the agent's history.
2. Comparator. For each of the 18 rules, a separate call sees only that rule and the agent's list, and answers YES or NO to "Does the agent's list state this rule's essential requirement?".
3. Patch. Rules judged NO are appended verbatim after the summary under "[Operator policy reminder, re-attached by the harness]". The patch then lives in context and is folded into the next summary, where the next check can catch it again.

`watch_ctx` ablates step 1: the comparator reads the rendered compacted context instead of an extraction. `pinrules` is the "patch everything always" end of the same design, so `watch` vs `pinrules` isolates selectivity.

Nothing in any arm sees the task instruction's hidden goals, the gold actions, the gold outputs, or the grader.

## Results

All tables are regenerated by `analyze.py` and saved in `results/tables_retail.md`, `results/tables_stripped.md` and `results/tables_airline.md`. Those files also hold the exposure table, failure sources, per-rule Watchpoint miss rates and the remaining violation flags.

### Retail, main run (115 tasks, 2 trials, 230 runs per arm)

Per-arm reward intervals are Wilson 95% intervals over runs. pass^2 is τ-bench's pass^k with k = 2 (both trials of a task succeed). Calls and tokens are per run and include the user simulator, summarizer, extractor and comparator calls.

| arm | reward (95% CI) | pass^2 | model calls/run | input tokens/run | output tokens/run | writes without user "yes" |
|---|---|---|---|---|---|---|
| nopolicy | 0.648 (0.584 to 0.707) | 0.548 | 18.5 | 65,734 | 1,246 | 8.3% |
| standard | 0.626 (0.562 to 0.686) | 0.487 | 18.8 | 80,780 | 1,207 | 6.1% |
| hist | 0.657 (0.593 to 0.715) | 0.530 | 19.0 | 81,953 | 1,245 | 3.0% |
| compact | 0.626 (0.562 to 0.686) | 0.504 | 22.4 | 75,109 | 1,873 | 7.8% |
| pin | 0.626 (0.562 to 0.686) | 0.504 | 22.2 | 85,623 | 1,759 | 4.8% |
| pinrules | 0.600 (0.536 to 0.661) | 0.478 | 22.1 | 78,614 | 1,784 | 0.4% |
| watch | 0.570 (0.505 to 0.632) | 0.443 | 60.9 | 115,798 | 4,601 | 3.9% |
| watch_ctx | 0.613 (0.549 to 0.674) | 0.470 | 60.0 | 115,379 | 3,219 | 5.7% |

Paired comparisons use each task's mean reward over its two trials. The p-value is an exact two-sided sign test over tasks where the arms differ; the interval is a paired bootstrap over tasks (2,000 resamples, seed 0).

| comparison | a better / b better / tied tasks | difference (95% CI) | p | Holm p |
|---|---|---|---|---|
| compact vs hist (primary) | 19 / 25 / 71 | -0.030 (-0.100 to +0.035) | 0.45 | 1 |
| hist vs standard | 23 / 18 / 74 | +0.030 (-0.035 to +0.096) | 0.53 | 1 |
| pin vs compact | 21 / 21 / 73 | +0.000 (-0.065 to +0.065) | 1 | 1 |
| pinrules vs compact | 18 / 23 / 74 | -0.026 (-0.087 to +0.039) | 0.53 | 1 |
| watch vs compact | 17 / 27 / 71 | -0.057 (-0.130 to +0.013) | 0.17 | 1 |
| watch vs pin | 17 / 28 / 70 | -0.057 (-0.122 to +0.009) | 0.14 | 1 |
| watch vs pinrules | 21 / 26 / 68 | -0.030 (-0.100 to +0.035) | 0.56 | 1 |
| watch_ctx vs compact | 26 / 28 / 61 | -0.013 (-0.091 to +0.065) | 0.89 | 1 |
| watch vs watch_ctx | 20 / 29 / 66 | -0.043 (-0.117 to +0.030) | 0.25 | 1 |
| nopolicy vs standard | 16 / 15 / 84 | +0.022 (-0.039 to +0.083) | 1 | 1 |

H1, H2 and H3 are all unsupported on this run. The Watchpoint arm is the lowest-scoring arm, and it fails more often than the others on required output strings (34 of 99 failures, versus 23 to 30 elsewhere). That pattern is exploratory and not significant.

**Why compaction does not hurt here.** Four observations, all from the same data:

1. The policy is not load-bearing for the reward. `nopolicy` (no policy text anywhere) matches `standard` and `hist`.
2. The summaries keep part of the policy on their own. With no instruction to do so, 81% of `compact` summaries mention confirmation and 74% mention authentication. Only 2.7% mention that the exchange and modify tools can be used only once.
3. The tool schemas are never compacted and repeat several rules, and the tools reject invalid cancellations, wrong order statuses and overdrawn gift cards in code.
4. The reward checks outcomes, not process. Skipping the confirmation step only costs reward when the user would have refused, and the simulated user rarely refuses.

The compaction schedule was already aggressive (first compaction after 4 agent steps, about 2 compactions per task, summaries with a median of 111 words), so compacting earlier would not change point 1. Instead of a more aggressive schedule, the exploratory variant below removes point 3.

**Watchpoint behaviour.** The extraction-plus-comparator check found missing rules in all 470 checks (mean 10.3 of 18 rules). The comparator judges each rule against everything the agent listed, so rules that do not apply to the current task (cancellation rules during an exchange, for example) count as missing and get patched. The ablation that compares the rules against the compacted context directly (`watch_ctx`) also patched on every check (mean 10.6 of 18). Selectivity, the point of H3, never appears: Watchpoint behaves like `pinrules` with a random subset of rules, at almost 3 times the calls.

### Retail, policy sentences removed from tool descriptions (exploratory; 115 tasks, 1 trial)

`--strip_tools` deletes the policy sentences that τ-bench repeats in the retail tool descriptions: "The agent needs to explain ... (yes/no) to proceed", the two "can only be done/called once" sentences, "Only transfer if ...", "By default, find user id by email ...", "If the user confirms," and the list of valid cancellation reasons in the parameter description (the JSON-schema enum is kept). The policy text in the conversation is then the only place those rules appear. This variant was added after the main trial-0 results showed no effect.

| arm | reward (95% CI) | model calls/run | input tokens/run | writes without user "yes" |
|---|---|---|---|---|
| nopolicy | 0.617 (0.526 to 0.701) | 17.3 | 57,537 | 48.7% |
| hist | 0.643 (0.553 to 0.725) | 18.4 | 75,873 | 4.3% |
| compact | 0.557 (0.465 to 0.644) | 21.2 | 73,508 | 26.1% |
| pin | 0.652 (0.561 to 0.733) | 21.3 | 80,389 | 8.7% |
| watch | 0.643 (0.553 to 0.725) | 60.7 | 116,336 | 7.8% |

| comparison | reward difference (95% CI) | reward p / Holm p | "no yes" flag rate a vs b | flag p / Holm p |
|---|---|---|---|---|
| compact vs hist | -0.087 (-0.183 to +0.017) | 0.13 / 0.40 | 26.1% vs 4.3% (27 vs 2 tasks) | 1.6e-6 / 6.5e-6 |
| pin vs compact | +0.096 (+0.009 to +0.183) | 0.061 / 0.25 | 8.7% vs 26.1% (5 vs 25 tasks) | 3.3e-4 / 9.7e-4 |
| watch vs compact | +0.087 (-0.017 to +0.191) | 0.14 / 0.40 | 7.8% vs 26.1% (6 vs 27 tasks) | 3.2e-4 / 9.7e-4 |
| watch vs pin | -0.009 (-0.104 to +0.096) | 1 / 1 | 7.8% vs 8.7% | 1 / 1 |

Once the tool descriptions stop repeating the confirmation rule, the policy text is what keeps the agent asking for a "yes", and compaction removes it. Pinning and Watchpoint restore it equally well. Reward follows the same direction, by about 9 points, which this sample cannot distinguish from zero after correction. Even here, `nopolicy` reward (0.617) stays close to `hist` (0.643), although half of its runs skip confirmation: τ-bench's outcome-based reward simply does not penalize most of these violations.

In the main run, where tool descriptions still carry the rule, the same flag shows a smaller version of the effect: 3.0% (`hist`) to 7.8% (`compact`), p = 0.078 before correction. Re-attaching the hand-split rule list (`pinrules`) cut it to 0.4% (Holm p = 6e-4 vs `compact`).

### Airline (50 tasks, 1 trial)

Planned as "if time permits". A second airline trial was started and stopped to finish on time, so pass^2 is not available.

| arm | reward (95% CI) | model calls/run | input tokens/run | writes without user "yes" |
|---|---|---|---|---|
| nopolicy | 0.36 (0.24 to 0.50) | 16.2 | 60,394 | 28% |
| standard | 0.52 (0.39 to 0.65) | 17.3 | 73,782 | 0% |
| hist | 0.40 (0.28 to 0.54) | 17.4 | 73,477 | 6% |
| compact | 0.44 (0.31 to 0.58) | 20.5 | 76,487 | 18% |
| pin | 0.46 (0.33 to 0.60) | 20.8 | 89,464 | 4% |
| pinrules | 0.38 (0.26 to 0.52) | 18.8 | 74,556 | 4% |
| watch | 0.46 (0.33 to 0.60) | 47.8 | 131,061 | 6% |
| watch_ctx | 0.46 (0.33 to 0.60) | 50.1 | 142,777 | 18% |

No planned comparison is significant (smallest Holm p = 1; compact vs hist +0.04, CI -0.08 to +0.16). Two patterns are worth a follow-up: moving the policy out of the system prompt cost 12 points before any compaction (hist vs standard, CI -0.30 to +0.04), and removing the policy entirely cost 16 points (CI -0.34 to +0.02). So in airline the policy does matter for reward, but where it sits seems to matter more than whether it survives compaction. The confirmation flag again rises with compaction (6% to 18%, 8 vs 2 tasks, p = 0.11) and falls with pin and Watchpoint. Here Watchpoint found 16.2 of 19 rules missing per check on average.

### Total cost

E3 made 85,940 model calls (243 million input tokens, 6.4 million output tokens) across the pilot, the main retail run, the stripped variant and airline, including reruns of jobs interrupted by provider outages.

## Validation of the simulated user

`audit_user.py` flags three behaviours over all retail runs, and prints a fixed random sample (seed 0) for reading.

| file | runs | user ended without ###STOP### and without a transfer | user stopped before any write on a task that needs one | user denied knowing a zip or email stated in its instruction | user copied 12+ words of its instruction |
|---|---|---|---|---|---|
| retail main | 1,840 | 1.0% | 1.1% | 1.1% | 0.7% |
| retail stripped | 575 | 1.0% | 0.9% | 0.5% | 0.2% |
| airline | 400 | 2.0% | 2.8% | n/a | 1.0% |

Conversations that end in a transfer to a human (17% of retail runs, 55% of airline runs) also lack ###STOP###; that is τ-bench's normal ending for a transfer, so they are counted separately and not as misbehaviour. I also read about 25 complete trajectories (the fixed sample from `audit_user.py`, every `standard` failure in the pilot, and the cases quoted below). The simulated user generally followed its instruction, including scripted changes of mind. Problems seen: in an early smoke test, before the added prompt line, it invented an email address and claimed not to know a zip code that its instruction stated; several instructions describe a "private person", and the user then withholds the zip code by design, which makes those tasks fail in every arm. Misbehaviour rates are similar across arms, so they add noise rather than bias.

## Qualitative failures after compaction

**The "only once" rule lost to compaction (retail task 0, `compact`, trial 0).** The customer wants to exchange a keyboard and a thermostat from one delivered order. After the first compaction (step 4) the summary reads, in part, "No order details, exchange eligibility, item availability, payment method, or required confirmation has been established yet." It says nothing about the exchange tool being usable once per order. The agent exchanges the keyboard alone, then tries the thermostat: the tool returns "Error: non-delivered order cannot be exchanged", and the agent transfers the customer to a human. Reward 0. In the same task and trial, the `hist` and `standard` arms put both items into one exchange call and scored 1. Across all main-run `compact` summaries, only 2.7% mention the once-only rule.

**Confirmation dropped after compaction (retail task 71, stripped variant).** The customer wants to change a pending order's address, then its desk lamp and backpack. In `hist`, before modifying items the agent writes "Please confirm this modification for order #W5270061 (this can only be done once, so be sure all changes are included)" and waits for "Yes, I confirm." In `compact`, after the user says "I'll take the black, high-brightness lamp with the AC adapter", the agent immediately calls `modify_pending_order_items` for the lamp alone, charging the gift card, with no summary of the change and no question. The order can no longer be modified, so the backpack change that follows fails, and the agent retries the same call twice before transferring. All three arms score 0 on this hard task, which is exactly why the reward does not register the difference.

**A Watchpoint check (retail task 9, `watch`, trial 0).** After the first compaction the summary already said "obtain explicit confirmation before submitting the action". The agent's extraction listed 11 rules, including "Exchanges and returns on a delivered order can only be performed once per order". The comparator still marked 13 of 18 rules missing, among them the once-only rule (because the reference rule also requires collecting all items into one list) and several cancellation, modification and return rules that do not apply to an exchange. All 13 were appended. This is typical: the check is strict and task-blind, so it patches on every compaction.

## Threats to validity

- **Modified benchmark.** Moving the policy into history and forcing compaction is our construction. τ-bench numbers from papers use the policy in the system prompt and different models and user simulators.
- **One backbone.** The agent, the user simulator, the summarizer, the extractor and the comparator are all the same model. A self-consistent model may summarize in a way it later reads well. A second-backbone rerun is described below but was not run.
- **Single trial per task in most cells.** τ-bench is known to be noisy across trials. Per-arm 95% intervals are roughly ±9 points at n=115, larger than every reward difference observed.
- **The reward cannot see process violations.** τ-bench grades the final database and required outputs. An agent that skips the confirmation step still gets full reward when the simulated user would have said yes anyway. The violation flags measure this, but they are a heuristic (the last user message before a write must contain a yes-like word such as "yes", "confirm", "go ahead", "proceed", "sure", "ok"). A manual check of 10 randomly chosen flagged writes in the stripped `compact` arm found 10 genuine cases of a write made right after the user stated a choice, without the agent restating details and asking for a yes. False negatives were not measured.
- **Policy redundancy.** The policy is partly duplicated in tool descriptions and partly enforced by tool code, so removing it from context removes less than it seems. The stripped variant addresses the first, not the second.
- **User-simulator deviation.** One added line in the user prompt (see above). It applies to every arm equally.
- **Provider instability.** The model provider returned bursts of HTTP 502 during the night. A run whose model call failed after all retries was discarded and rerun from scratch. Agent-side failures that were recorded instead of crashing are excluded from analysis and listed as "dropped". This could bias results only if outages correlate with arm, which the job ordering (arms interleaved per task) makes unlikely.
- **Small mid-run code changes.** Three settings changed while runs were in progress, all affecting only calls that would otherwise fail: the comparator's output cap was raised from 10 to 400 tokens before any kept Watchpoint run (reasoning tokens were exhausting it and the call returned empty), the summarizer's cap was raised from 800 to 2,000 tokens after two summary calls failed, and the client retry count was raised from 6 to 10. The first 11 rows of `main.jsonl` (`standard` and `compact`, tasks 0 to 7) come from the smoke test, which used the same settings for those arms.
- **Exploratory variant decided after seeing data.** The stripped-tool variant and the violation flags were added after the main trial-0 run came back null, so their p-values should be read as exploratory even though they are Holm-corrected within their own tables.
- **Seeds.** Model sampling through the API is not seedable. The agent, extractor and comparator run at temperature 0, the summarizer at 0.3 and the simulated user at 1.0 (as in τ-bench). The bootstrap and the trajectory sample use seed 0.
- **Comparator calibration.** The Watchpoint comparator was not validated against hand labels in this experiment. Its judgments matter only for which rules get patched, and it patched something on every check.

## Reproduce

All commands run from this directory with the τ-bench venv (`/private/tmp/taubench-venv`, which has `tau_bench` installed in editable mode from `/private/tmp/tau-bench`).

```bash
PY=/private/tmp/taubench-venv/bin/python
# main retail comparison (trial 0 and 1), all 8 arms
$PY run.py --tasks 0-114 --trials 0-1 --out results/main.jsonl
# exploratory: policy sentences removed from tool descriptions
$PY run.py --strip_tools --arms nopolicy hist compact pin watch --tasks 0-114 --out results/stripped.jsonl
# airline
$PY run.py --domain airline --tasks 0-49 --out results/airline.jsonl
# tables (stdlib only)
python3 analyze.py results/main.jsonl > results/tables_retail.md
python3 analyze.py results/stripped.jsonl > results/tables_stripped.md
python3 analyze.py results/airline.jsonl > results/tables_airline.md
python3 audit_user.py results/main.jsonl --sample 12
```

`run.py` resumes: finished (arm, task, trial) rows in the output file are skipped, so rerunning the same command retries crashed jobs. It uses at most 12 worker threads (`--workers`).

**Second backbone.** Every model call takes `--model` (default `stealth/space-bunny-alpha`) and the user simulator can be split off with `--user_model`. `:free` models are refused. A small rerun of the primary comparison on another model would be, for example:

```bash
$PY run.py --model <openrouter-model-id> --arms hist compact pin watch --tasks 0-39 --out results/backbone2.jsonl
python3 analyze.py results/backbone2.jsonl
```

Usage tags in `../usage.jsonl` do not include the model id, so token columns for a second backbone written to the same log would merge with the first. Use a separate output file and read token costs from a separate run window, or add the model to the tag first.

## Files

- `run.py`: agent loop, user simulator, compaction, pin, Watchpoint, and the run queue entry point.
- `rules_retail.json`, `rules_airline.json`: the hand-split rule lists used by `pinrules`, `watch` and `watch_ctx`.
- `analyze.py`: regenerates every table from the raw files (standard library only).
- `audit_user.py`: simulated-user audit and trajectory sampler.
- `queue.sh`: the sequential queue used overnight.
- `results/main.jsonl` (retail), `results/stripped.jsonl` (retail, stripped tool descriptions), `results/airline.jsonl`: one JSON object per run with reward, reward info, per-kind call counts, every summary, every Watchpoint extraction and missing-rule list, and a compact trajectory (`events`: user and agent turns truncated to 300 and 500 characters, every tool call with full arguments and the first 200 characters of its result).
- `results/pilot.jsonl`: the 20-task pilot (its rows are also the first rows of `main.jsonl`). `results/airline_errored.jsonl` and `results/stripped_errored.jsonl`: runs discarded because of provider outages and rerun.
- `results/tables_*.md`: the generated tables.
