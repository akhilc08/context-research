# E19: when should a coding agent compact?

Overnight study on compaction timing. Every policy compacts the same number of times in the same sessions, so the policies differ only in *when* they compact. One backbone (`stealth/space-bunny-alpha`) plays every role: timing judge, summarizer, agent, and grader. The transcripts are synthetic and each probe is a single step. Treat every number as a pilot result.

## Short answer

- **With plain narrative summaries, timing matters, and almost all of the effect comes from one thing: whether the current operation's plan is still verbatim when the agent needs it.** Next-step correctness was 83% when the operator's request (the step list) was still in the verbatim part of the context and 23% when it had been summarized, pooled over all plain-summary policies.
- **The harness checkpoint was the best plain-summary policy.** It compacts at the next subtask close after a soft threshold. It reached 86% next-step correct against 69% for the token threshold (15 vs 3 discordant pairs, p = 0.008, Holm p = 0.07). The sample-1 replicate pointed the same way (p = 0.02). The direction is consistent, but it did not survive the pre-registered Holm correction.
- **Operator-aware timing backfired.** It waits until the latest operator message is 6 turns old before compacting. With plain summaries it was the worst policy: 43% next-step correct (Holm p = 0.002 against threshold) and battery harm of 83% against 71%. The reason is mechanical. An operation begins with an operator request, so the policy waits just long enough for that request to fall out of the verbatim tail and then summarizes it.
- **Model-judged timing (SelfCompact-style) tied the threshold (68% vs 69%) and cost 4.5 times the threshold policy's compaction-side input tokens.** It mostly declined to fire mid-operation, but it fired readily during ordinary coding work. That moved later compactions into operations.
- **Once content is protected, timing stops mattering.** The second content arm combines a structured checkpoint prompt with all operator messages pinned verbatim. With it, all five policies scored 81% to 83% next-step correct and 0% to 7% battery harm. No comparison came near significance. This matches full context (83% and 6%) at about half of its tokens.
- **Random timing at the same count matched the threshold (65% vs 69%).** The threshold has no advantage of its own. What helps is a trigger that knows where work boundaries are.

## Question and hypotheses

The study brief's H3 asks whether harness-verified timing (compact when tests pass or a subtask closes) loses less than a token threshold on coding work. It also asks whether such a trigger matches the model's own judgment, which SelfCompact found beats fixed thresholds on math and search. E8 had a hint (plain summary at a checkpoint 34% vs at a threshold 14%), but it used short single-procedure transcripts and only one compaction.

The hypotheses were written in the `analyze.py` docstring at 06:35, after a one-session pilot and before the main run.

- **Primary metric:** next-step correct on sample 0 at three fixed mid-operation probe points per session. All arms are probed at the same turns, so units pair by (session, point), with n = 72 per arm. The primary family is 10 exact McNemar tests with Holm correction. For each content type, it compares checkpoint, model, operator, and random each against threshold, plus checkpoint against model.
- H1. With plain content, the checkpoint beats the threshold on next-step correct.
- H2. Model-judged timing does not beat the checkpoint.
- H3. Operator-aware timing lowers battery failures relative to the threshold. This is tested in a secondary family of the same 10 comparisons on battery harm.
- H4. Random timing does not differ from the threshold (control).
- H5 (exploratory). Pinned structured content shrinks the timing gaps.

## Design

### Sessions

`build.py` (seeded, no model calls) builds 24 sessions of 159 to 187 turns (mean 175, about 10,000 tokens). Each session has six subtasks:

| Subtask | Content | How it ends |
|---|---|---|
| C1, C2, C3 | 24 to 32 realistic coding turns from the shared filler pool | A passing test run plus a `DONE: subtask N closed` marker |
| O1, O2 | One ordered operation (an E8/E13 procedure of 8 or 9 steps). It opens with an operator request that lists every step command. Each step is followed by 1 to 4 related E13 filler turns. | `DONE: operation closed` |
| O3 | A third operation, still in progress when the session ends | None |

Operator items are planted across the session:

- the session goal at turn 1;
- one standing rule in C1 and a second in O1 or C2;
- a ruled-out approach in C2;
- a stale identifier in C1, corrected by the operator in C2 or C3;
- a goal redirect in C3;
- three harmless chatter turns.

The operation requests are framed as side requests, separate from the session goal. Operator chatter inside E13's related filler was removed, so the only operator turns are the planted ones.

### Timing policies

Each policy watches R, the raw tokens since the last compaction. T is the session's tokens divided by 5. The soft limit is 0.6T and the hard limit is 1.4T. Every policy stops after 4 compactions.

| Policy | Fires when |
|---|---|
| threshold | R reaches T |
| checkpoint | R has passed the soft limit and the current turn is a subtask close (harness-observed `DONE` turn). Hard limit as fallback. |
| model | Past the soft limit, the model is asked at every turn whether now is a good time. It sees the verbatim history since the last compaction and a short rubric: fire when a subtask resolves; hold mid-operation, right after a new operator instruction, or while a result is pending. Hard limit as fallback. |
| operator | R reaches T and the latest operator turn is at least 6 turns old. Hard limit as fallback. |
| random | At a uniformly random point in token space between the soft and hard limits |

Timing never sees the summary, so each policy fires at the same turns under both content types. Every policy made exactly 4 compactions in all 24 sessions. Hard-limit fallbacks were rare (checkpoint 3 of 96, operator 2 of 96).

### Compaction content

Compaction is recursive. Each round summarizes the previous summary plus the new turns. The last 3 turns stay verbatim, the budget is 150 words, and `max_tokens` is words × 3 + 600.

- **plain:** the shared narrative `SUMMARY_PROMPT`.
- **pinstruct:** a structured checkpoint prompt (Goal, Constraints and rules, Key decisions and facts, Ruled out, Progress, Next steps) plus every operator message from the summarized part, kept verbatim by the harness. Among methods finished by 06:30, this combined the pinning that E2, E13, and E15 found best with the structured prompt that E10 and E15 found best. E16 and E17 were not finished, so neither informed the choice.
- **full:** the whole transcript, as a reference.

### Probes

- **Fixed points (primary):** mid-O1 and mid-O2 (step k done, followed by 2 to 4 related turns) and the final turn (mid-O3). Every arm is probed at the same turns with two samples at temperature 0.8.
- **Right after each compaction (secondary):** each compacted arm is probed at its own compaction turns with one sample. These probes are not paired across policies, because the turns and the truth differ.
- **Battery.** E10's items, asked together in one message as separate numbered requests: the two rule triggers, the ruled-out approach (as directives), the identifier question, and the goal question. Only items already established by the probe turn are asked. An item fails when every sample is wrong. Battery harm means at least one item fails. Asking the items in one message is a cost-saving departure from E10, which asked each item separately.
- **Next step.** E13's prompt asks for the exact next command for the operation. It is scored as in E13's "after" condition: correct means step k+1. A step at or before k is a repeat, and a harmful repeat if that step is non-idempotent. A step after k+1 is a skip. Verify and other are the remaining categories.
- **Repeated-work proxy.** The proposed command repeats a completed step, re-runs a command already run in the session, or re-reads a file already read. This is a crude regex heuristic.

### Grading

`grade.py` grades the answers.

- Directive and goal answers go to E10's validated judges. Answers for each session item are deduplicated, shuffled, and batched, so the judge never sees the arm, the policy, or the turn.
- The identifier answer is scored by E10's regex.
- Next-step commands are matched exactly against the step and verify commands where possible (after normalization). Everything else goes to E13's validated procedure judge.

## Results

All tables are in `results.md`, generated by `analyze.py`.

### Fixed probe points (n = 72 per arm, paired)

| Arm | Next-step correct (s0) | Replicate (s1) | Battery harm | Agent context tokens | Verbatim tokens |
|---|---|---|---|---|---|
| full | 83% [73 to 90] | 86% | 6% [2 to 13] | 6,818 | 6,492 |
| threshold / plain | 69% [58 to 79] | 72% | 71% [59 to 80] | 2,121 | 1,751 |
| checkpoint / plain | 86% [76 to 92] | 83% | 57% [45 to 68] | 2,333 | 1,957 |
| model / plain | 68% [57 to 78] | 74% | 64% [52 to 74] | 2,921 | 2,518 |
| operator / plain | 43% [32 to 55] | 47% | 83% [73 to 90] | 1,544 | 1,196 |
| random / plain | 65% [54 to 75] | 64% | 74% [62 to 82] | 2,210 | 1,834 |
| threshold / pinstruct | 82% [72 to 89] | 81% | 3% [1 to 10] | 2,840 | 1,751 |
| checkpoint / pinstruct | 83% [73 to 90] | 83% | 6% [2 to 13] | 2,953 | 1,957 |
| model / pinstruct | 83% [73 to 90] | 88% | 7% [3 to 15] | 3,552 | 2,518 |
| operator / pinstruct | 82% [72 to 89] | 88% | 0% [0 to 5] | 2,418 | 1,196 |
| random / pinstruct | 81% [70 to 88] | 75% | 6% [2 to 13] | 2,947 | 1,834 |

Brackets are 95% Wilson intervals. Harmful repeats were 0 or 1 of 72 in every arm, so this setup cannot compare them.

### Primary tests (exact McNemar, Holm across 10)

| Comparison | Correct | Discordant | p | Holm p |
|---|---|---|---|---|
| checkpoint vs threshold, plain | 62 vs 50 | 15 : 3 | 0.008 | 0.068 |
| model vs threshold, plain | 49 vs 50 | 10 : 11 | 1.0 | 1.0 |
| operator vs threshold, plain | 31 vs 50 | 3 : 22 | 0.0002 | 0.002 |
| random vs threshold, plain | 47 vs 50 | 8 : 11 | 0.65 | 1.0 |
| checkpoint vs model, plain | 62 vs 49 | 18 : 5 | 0.011 | 0.085 |
| all five pinstruct comparisons | 58 to 60 vs 59 to 60 | at most 7 : 6 | ≥ 0.58 | 1.0 |

On battery harm (the secondary family), checkpoint vs threshold with plain content was 41 vs 51 harmed (2 : 12, p = 0.013, Holm p = 0.12). Operator vs threshold was 60 vs 51 (10 : 1, p = 0.012, Holm p = 0.12), the opposite of H3's predicted direction. In an exploratory family, the "fully correct probe" outcome (next step right and no battery failure) gave checkpoint 27 vs threshold 14 (Holm p = 0.02) and operator 2 vs 14 (Holm p = 0.02).

### What decides the outcome

Whether the operation request is still verbatim at the probe (exploratory, pooled over the five policies):

| Content | Request verbatim | Request summarized |
|---|---|---|
| plain | 216/260 = 83% [78 to 87] | 23/100 = 23% [16 to 32] |
| pinstruct | 215/260 = 83% [78 to 87] | 81/100 = 81% [72 to 87] |

The verbatim request rates per policy (mid-O1, mid-O2, end) were:

- checkpoint: 24, 24, and 24 of 24;
- threshold: 15, 17, and 24;
- random: 16, 11, and 24;
- model: 8, 22, and 24;
- operator: 0, 4, and 23.

The per-policy results follow these counts. The checkpoint compacts right after a subtask closes, before the next operation starts, so the step list always stays verbatim. The operator-aware rule summarizes the request just after it leaves the 3-turn tail. At the end probe, the request was verbatim for nearly every policy, and all plain policies scored 79% to 88% there.

Where compaction happened:

| Policy | Compactions mid-operation | Model timing calls per session | Compaction-side input vs threshold |
|---|---|---|---|
| threshold | 68/96 = 71% | 0 | +0% |
| checkpoint | 3/96 = 3% | 0 | +0% |
| model | 39/96 = 41% | 17.7 | +351% |
| operator | 53/96 = 55% | 0 | +11% |
| random | 60/96 = 62% | 0 | -4% |

The model-judged policy said YES to 52 of 99 coding-filler turns, 13 of 95 step turns, 24 of 209 related operation turns, and 5 of 5 subtask closes. It respected "hold mid-operation" fairly well, but it fired early in coding work rather than waiting for the close. That left its next soft-limit crossing inside the following operation.

### Right after each compaction (descriptive)

| Arm | Battery harm | Next-step correct when an operation was in progress |
|---|---|---|
| threshold / plain | 78% | 10/51 = 20% |
| checkpoint / plain | 68% | 0/3 |
| model / plain | 74% | 9/38 = 24% |
| operator / plain | 84% | 8/53 = 15% |
| random / plain | 78% | 15/45 = 33% |
| threshold / pinstruct | 9% | 28/51 = 55% |
| model / pinstruct | 6% | 28/38 = 74% |
| operator / pinstruct | 6% | 38/53 = 72% |
| random / pinstruct | 6% | 31/45 = 69% |

Right after a compaction that fired mid-operation, plain summaries rarely resumed the operation correctly (15% to 33%). The checkpoint almost never creates this state (3 of 96 compactions). Pinning the request raised the rate to 55% to 74%. It did not reach the fixed-point level, because right after a mid-operation compaction the agent also loses its position (E13's finding). Since each policy is probed at its own turns, these rows are not paired comparisons.

### Repeated work

The repeated-work proxy fired on 10% to 17% of fixed-point next-step answers in every arm, including full context (12%). It did not separate the policies. Most hits are re-runs of a diagnostic or a step-k check, not completed steps.

## Judge validation

`validate_judges.py` draws a seeded, blind sample. I (the study agent, a language model, not a human) labeled 60 items without seeing the judge labels: 24 directive answers stratified on judge label, 12 goal answers, and 24 next-step commands that needed the LLM judge.

- Directive judge: 24/24 agreement, kappa 1.00.
- Goal judge: 11/12 agreement, kappa 0.87. The one miss was an answer mentioning both the operation and the old goal.
- Next-step judge: exact label 17/24 (kappa 0.65). On the distinction the primary metric uses (performs step j vs anything else), 21/24 (kappa 0.78). Four of the seven disagreements are verify-vs-other, which does not affect correctness. Three are commands that run a read-only plan step, which the judge prompt forbids calling "step". This slightly understates correctness for read-only steps in every arm.
- Overall: 52/60, kappa 0.85.

Exact matching settled most next-step answers without the judge.

## Qualitative examples

- **Operator-aware summarizes the plan** (session 0, mid-O1, k = 7). The operator/plain summary opens with "The invoice PDF async-queue migration remains the primary session goal". It describes the coding subtask in detail and mentions the rename procedure only briefly. The agent runs `rg -n '\bget_user_record\b' .` to "verify that the rename is complete". The checkpoint/plain agent, and the operator/pinstruct agent with the same timing, both run step 8 (`git tag -f rename-fetch-account-v1 HEAD`).
- **Skipping without the plan** (session 2, mid-O1, k = 3). Operator/plain runs step 5 (`ALTER TABLE ... SET NOT NULL`), reasoning that "the backfill is fully validated". Step 4, the validation query, has not run. Checkpoint/plain and operator/pinstruct both run step 4.
- **Model-judged firing in coding work** (session 0). The model said NO at the first two soft-limit turns in C1 and YES at the third, a filler turn four turns before C1's close. Its next soft-limit crossing fell inside O1, where it said NO twice and then fired two turns after step 5.

## Interpretation

1. **H1, directionally supported but not confirmed.** The harness checkpoint beat the threshold by 17 points with plain content, and both samples agree. The pre-registered Holm correction left it at p = 0.07. The effect is a mechanism, not a mystery: compacting at the close keeps the next operation's plan out of the summary.
2. **H2 supported, and more.** The model-judged policy did not beat the checkpoint (49 vs 62, Holm p = 0.09). It did not beat the threshold either, and it added 17.7 timing calls per session. The rubric asked it to fire when a subtask resolves, but it would not wait for one.
3. **H3 rejected in the opposite direction.** Delaying compaction until an operator message is a few turns old guarantees that message gets summarized at its next opportunity. That is worse for both the plan and the battery. A useful operator-aware rule would have to keep operator messages verbatim through compaction, which is pinning, not timing.
4. **H4 supported.** Random timing at the same count tied the threshold.
5. **H5 supported (exploratory).** Under pinstruct, all timing gaps were 0 to 1 points. The checkpoint gap shrank by 15 points (95% CI -1 to +32) and the operator gap by 26 (CI -44 to -6). If the plan and operator messages are pinned, timing does not matter in this setup. The harness checkpoint is only a partial fix for not pinning.

## Threats to validity

- **Short sessions.** About 10,000 tokens, scaled so that 4 compactions happen. Real sessions run to hundreds of thousands of tokens, and compaction events are fewer and much larger relative to a subtask.
- **Subtask closes are clean.** Every subtask ends with an explicit `DONE` turn, and operations never overlap with coding work. Real harnesses see messier signals (flaky tests, interleaved tasks). This favors the checkpoint policy.
- **The probe points are at operation positions where the plan matters most.** The end probe was nearly uninformative for timing, because every policy had the O3 request verbatim.
- **Unequal verbatim context at the probes.** The policies leave different amounts of verbatim text at the fixed points (1,196 to 2,518 tokens). This is a real consequence of timing, not a confound I can remove, but it means "timing" includes "how recently you compacted".
- **The operator-aware rule is one reading of the design.** K = 6 turns with a 3-turn tail. A version that compacts before an operator message, or keeps it in the tail, was not tested.
- **The model-judged policy sees only the verbatim history since the last compaction, not the summary.** This keeps its timing identical across content arms, but it is less information than an agent would have. A different rubric could wait for closes.
- **One backbone for every role.** Probes are single-step. The battery is asked in one combined message, a departure from E10.
- **Self-labeled validation.** The hand labels were made by an AI agent, not a human.
- **One failed probe.** One post-compaction probe (session 19, model/plain) kept returning empty completions and was retried with a larger output budget (`run.py` falls back to 3x `max_tokens` after 12 failed tries).
- **The pilot was discarded.** The one-session pilot used an operation request that said "Goal:", which made the agent report the operation as the session goal. The wording was changed to "side request ... Purpose:" and the goal probe now says "not the side procedures". The pilot data were discarded.

## Cost

About 6,700 model calls, 17.7M input tokens, and 1.3M output tokens, including the discarded pilot. Of these, 458 were timing calls, 942 compaction calls, 4,503 probe calls, and 840 judge calls. Per session, the model-judged policy added 17.7 timing calls and about 130,000 input characters. That is 4.5 times the threshold policy's compaction input. The pinning and structured prompt add no calls.

## Files and reproduction

- `build.py`: builds `data/sessions.json` (seeded, no model calls).
- `run.py`: schedules, compaction chains, and probes. Writes `raw/s{sid}.json`. Every call is cached in `cache/` (git-ignored), so the run can be resumed.
- `grade.py`: judges. Writes `judged/s{sid}.json`.
- `analyze.py`: hypotheses in its docstring. Regenerates `results.md` and `results.json` with no model calls.
- `validate_judges.py`, `judge_validation_items.json`, `hand_labels.json`, `judge_validation.json`: judge validation.
- `run_main.log`, `grade_main.log`: run logs.

```
cd studies/overnight-survey/e19_timing
python3 build.py --n 24
python3 run.py all --sessions 0-23 --workers 8
python3 grade.py
python3 analyze.py
python3 validate_judges.py score
```

Second-backbone rerun into a separate directory. Use any non-`:free` OpenRouter id (`run.py` refuses `:free`). The judge keeps the default model, so grading stays comparable.

```
python3 run.py all --sessions 0-11 --model <provider/model-id> --out rerun_b2
python3 grade.py --out rerun_b2
python3 analyze.py --out rerun_b2
```
