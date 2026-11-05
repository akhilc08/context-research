# E4: knowledge updates under bounded notes, with fact watchpoints

This experiment asks whether a side store of facts, used either as an always-on pin or as a watchpoint that patches the notes only when they drift, repairs what recursive compaction loses when facts change over time. It reuses Supersede's NOTES protocol, where an agent sees one session at a time and rewrites a capped notes field without ever re-reading old sessions. That protocol is recursive compaction in miniature.

All numbers come from one backbone (`stealth/space-bunny-alpha` through OpenRouter, low reasoning effort, temperature 0) and one run per arm. Every table below is regenerated from the raw files by `analyze.py`.

## Hypothesis and primary metric

These were fixed by the task brief before any model call:

- **H1.** Bounded notes (300 characters) lose knowledge-update accuracy relative to full context.
- **H2.** Adding a key-value fact store, extracted per session with newest-value-wins overwrite, recovers part of that loss, either pinned (4a) or as a watchpoint that patches only missing or stale values (4b).
- **H3.** The watchpoint matches the pin at lower memory cost.

**Primary metric:** answer accuracy on the 78 LongMemEval knowledge-update tasks, graded by LongMemEval's LLM-judge protocol. **Primary comparisons:** pin vs notes300, watch vs notes300, pin vs watch, with notes1200 as the budget ablation and full context as the ceiling. Secondary metrics are the stale-answer rate (exact on Supersede's synthetic tasks, judge-labeled on LongMemEval), tokens, and calls.

Anything marked **exploratory** below was decided after seeing the main results: the split of LongMemEval questions by whether they ask about an older value, the split of synthetic tasks by predicate, and both follow-up runs (store deduplication and a stricter comparator).

## Design

### Tasks

| set | n | sessions per task | source |
|---|---|---|---|
| `lme` | 78 | 2 (18,084 to 43,078 characters per task) | LongMemEval oracle, `question_type == "knowledge-update"`, loaded by Supersede's `load_longmemeval` from `/private/tmp/supersede/data/longmemeval_oracle.json` (SHA-1 `b81b6381...`, Supersede commit 677993d) |
| `synth_std` | 60 | 13 | Supersede `synthetic_tasks`, default config (6 tracked subjects, 3 values each, 6 distractors), seeds 0 to 59 |
| `synth_hard` | 60 | 17 | Supersede `synthetic_tasks`, 8 tracked subjects, 3 values each, 10 distractors, seeds 1000 to 1059 |

The two integer golds (120 and 1300) are converted to strings. Six LongMemEval items are abstention questions ("The information provided is not enough...").

### Arms

| arm | what the answering model sees |
|---|---|
| `full` | every session at once (ceiling) |
| `notes300` | Supersede's NOTES condition: per-session rewrite, hard cap 300 characters, answer from notes only |
| `notes1200` | the same with a 1200-character cap (budget ablation) |
| `pin` (4a) | the `notes300` notes plus the whole fact store appended at answer time |
| `watch` (4b) | its own 300-character notes trajectory; after each rewrite a check restates each stored fact from the notes, and every missing or mismatched fact is appended as a `[current] key: value` reminder below the notes |
| `kvonly` | the fact store alone, no notes (diagnostic for extraction errors) |

The notes prompts, the per-session loop, and the hard character cap are Supersede's own (`supersede.rollout.MEMORY_SYSTEM`, `memory_prompt`, `question_prompt`, `ANSWER_SYSTEM`). The `full` prompt is the one in Supersede's `eval_longmemeval.py`.

**Fact store.** After each session, one extraction call reads the current store and that session and returns facts the user stated or updated in that session as `{key, value}` pairs, at most 30. It is told to reuse an existing key when a fact is updated, so a newer value overwrites the older one. The store is shared by `pin`, `watch`, and `kvonly`. It never sees the question, gold, or stale labels.

**Watchpoint check.** This is the paper's extraction-based check, not a self-judgment. The model restates each stored fact's value from the notes (or `NOT_IN_NOTES`), and a fixed keyword comparator decides whether the restatement matches: every number in the stored value must appear, and at least half of its content words. A miss is patched by appending the stored value. Patches sit outside the 300-character cap, and the next rewrite sees notes plus reminders, as in the paper's design. So the watch arm's memory is not capped at 300 characters, and its size is reported.

### Grading

- **Synthetic:** Supersede's `classify` string grader (correct, stale, ambiguous when both values are named, wrong). Stale values are labeled by the generator, so this is exact.
- **LongMemEval accuracy:** Supersede's LongMemEval yes/no judge prompt, unchanged, with LongMemEval's abstention variant for the six abstention items.
- **LongMemEval stale rate:** LongMemEval does not label stale values, so one judge call per task reads both sessions plus the gold and names the "wrong-version" value: the older value, or the newer one when the question asks for the previous value. A four-way judge then labels each answer correct, stale, ambiguous, or wrong. 71 of the 72 non-abstention tasks received a label.

The judge is the same model as the backbone. The methods never see golds or stale labels. Only the grader does.

## Results

### Primary: LongMemEval knowledge-update (n=78)

| arm | accuracy | 95% Wilson CI | stale (of 71) | mean input tokens | mean output tokens | calls | memory at answer time (chars) |
|---|---|---|---|---|---|---|---|
| full | 71/78 = 91.0% | 83% to 96% | 5 (7.0%) | 6,017 | 48 | 1 | whole history |
| notes300 | 52/78 = 66.7% | 56% to 76% | 6 (8.5%) | 6,668 | 234 | 3 | 298 |
| notes1200 | 68/78 = 87.2% | 78% to 93% | 4 (5.6%) | 6,967 | 546 | 3 | 1,154 |
| pin | 63/78 = 80.8% | 71% to 88% | 5 (7.0%) | 13,911 | 957 | 6 | 1,598 |
| watch | 61/78 = 78.2% | 68% to 86% | 10 (14.1%) | 14,592 | 1,485 | 7 | 1,482 |
| kvonly | 67/78 = 85.9% | 76% to 92% | 3 (4.2%) | 7,179 | 724 | 3 | 1,300 |

Token and call counts include each arm's share of the extraction calls and exclude grading. The store held 18.6 facts (1,300 characters) on average.

Paired exact McNemar tests on accuracy, with Holm correction across all 10 comparisons for this set:

| comparison | A vs B correct | A only | B only | raw p | Holm p | paired difference, 95% bootstrap CI |
|---|---|---|---|---|---|---|
| notes300 vs full | 52 vs 71 | 2 | 21 | 6.6e-05 | 0.0007 | -34.6 to -14.1 points |
| notes1200 vs notes300 | 68 vs 52 | 18 | 2 | 0.0004 | 0.004 | +10.3 to +30.8 points |
| pin vs notes300 | 63 vs 52 | 12 | 1 | 0.003 | 0.027 | +6.4 to +23.1 points |
| watch vs notes300 | 61 vs 52 | 14 | 5 | 0.064 | 0.34 | +1.3 to +21.8 points |
| pin vs watch | 63 vs 61 | 5 | 3 | 0.73 | 0.73 | -3.8 to +10.3 points |
| pin vs notes1200 | 63 vs 68 | 5 | 10 | 0.30 | 0.66 | -15.4 to +2.6 points |
| watch vs notes1200 | 61 vs 68 | 5 | 12 | 0.14 | 0.57 | -19.2 to +1.3 points |
| pin vs full | 63 vs 71 | 3 | 11 | 0.057 | 0.34 | -19.2 to -1.3 points |
| watch vs full | 61 vs 71 | 3 | 13 | 0.021 | 0.15 | -23.1 to -2.6 points |
| kvonly vs pin | 67 vs 63 | 5 | 1 | 0.22 | 0.66 | 0.0 to +11.5 points |

On LongMemEval, H1 holds (300-character notes lose 24 points against full context, Holm p < 0.001). H2 holds for the pin (+14 points, Holm p = 0.027) but not clearly for the watchpoint (+12 points, Holm p = 0.34). H3 is not supported: the watchpoint patched in 153 of 154 rounds, so its memory ended up as large as the pin's (1,482 vs 1,598 characters) at more calls, and its stale rate was the highest of any arm (10 of 71; 6 vs 1 against the pin, McNemar p = 0.125, so not significant). The plain budget increase to 1,200 characters did at least as well as either store arm (87.2%), at half the tokens and with no extra calls.

### Synthetic tasks (exact grading, stale values known)

| arm | synth_std acc (n=60) | 95% CI | synth_hard acc (n=60) | 95% CI | stale, std / hard | ambiguous, std / hard | mean calls, std / hard | mean input tokens, std / hard |
|---|---|---|---|---|---|---|---|---|
| full | 59 (98.3%) | 91% to 100% | 57 (95.0%) | 86% to 98% | 0 / 0 | 1 / 3 | 1 / 1 | 427 / 508 |
| notes300 | 42 (70.0%) | 57% to 80% | 42 (70.0%) | 57% to 80% | 2 / 0 | 10 / 10 | 14 / 18 | 4,643 / 6,355 |
| notes1200 | 46 (76.7%) | 65% to 86% | 47 (78.3%) | 66% to 87% | 0 / 0 | 14 / 13 | 14 / 18 | 4,775 / 6,734 |
| pin | 57 (95.0%) | 86% to 98% | 57 (95.0%) | 86% to 98% | 2 / 1 | 1 / 2 | 28 / 36 | 10,992 / 15,419 |
| watch | 45 (75.0%) | 63% to 84% | 48 (80.0%) | 68% to 88% | 2 / 1 | 13 / 11 | 40 / 52 | 15,917 / 23,405 |
| kvonly | 58 (96.7%) | 89% to 99% | 58 (96.7%) | 89% to 99% | 1 / 1 | 1 / 1 | 14 / 18 | 6,285 / 8,982 |

Holm-adjusted McNemar p values (10 tests per set), std / hard: pin vs notes300 0.0005 / 0.0006; pin vs watch 0.003 / 0.027; pin vs notes1200 0.006 / 0.016; pin vs full 1 / 1; watch vs notes300 1 / 0.55; notes1200 vs notes300 1 / 0.55. Full tables are in `results/tables.md`.

On synthetic tasks, the pin closes the whole gap to full context (95% vs 95 to 98%), and the watchpoint and the larger budget barely help. The strict "stale" rate stays low in every arm (0 to 3%). Instead, the failure shows up as **ambiguous** answers that list the current value next to superseded ones: 10 to 14 per set for every notes-based arm, and 1 to 3 for the pin.

### Where the failures come from

**Notes "accumulate" instead of overwrite (exploratory, synthetic).** Almost all ambiguous answers come from one predicate. Supersede phrases updates as "X is now allergic to Y", which reads as a new allergy rather than a replacement, so the notes keep a list:

| arm | "allergic to" queries (n=27): correct / stale / ambiguous / wrong | other predicates (n=93): correct / stale / ambiguous / wrong |
|---|---|---|
| full | 23 / 0 / 4 / 0 | 93 / 0 / 0 / 0 |
| notes300 | 3 / 1 / 20 / 3 | 81 / 1 / 0 / 11 |
| notes1200 | 0 / 0 / 27 / 0 | 93 / 0 / 0 / 0 |
| pin | 21 / 3 / 3 / 0 | 93 / 0 / 0 / 0 |
| watch | 3 / 2 / 22 / 0 | 90 / 1 / 2 / 0 |

For other predicates, 300-character notes simply drop facts (11 wrong), a 1,200-character budget fixes that completely, and the watchpoint fixes nearly all of it. For the allergy predicate, nothing notes-based works, because the current value is present and the check only asks whether it is present. The notes "Devin: allergic to pollen, gluten, soy" pass a check for `soy`, so nothing is patched. The pin works because the store's overwrite semantics hold a single value.

**Overwrite semantics cannot answer questions about the past (exploratory, LongMemEval).** Thirteen non-abstention questions ask about an older value ("What was my previous personal best...", "Where do I initially keep...", "did I increase or decrease..."), picked by a regex on the question text:

| arm | history questions (n=13) | other questions (n=65) |
|---|---|---|
| full | 11 | 60 |
| notes300 | 1 | 51 |
| notes1200 | 9 | 59 |
| pin | 1 | 62 |
| watch | 3 | 58 |
| kvonly | 4 | 63 |

On current-value questions the pin is as good as full context (62 vs 60 of 65; 3 vs 1 discordant, p = 0.63) and beats notes300 (12 vs 1, p = 0.003, uncorrected). On history questions it is no better than notes300 (1 of 13) and far below notes1200 (0 vs 8 discordant, p = 0.008, uncorrected). The store discards the old value by design, and the reminders push the model toward the newest one. This one split explains most of the gap between pin and notes1200 in the primary table.

**Extraction errors.** On synthetic tasks, the final store held the queried fact's current value in 113 of 120 tasks (5 ambiguous, 2 wrong). Of the pin's 6 synthetic failures, the store alone was also wrong on 4. On LongMemEval, the store alone failed on 11 tasks: 9 are history questions where the old value was correctly overwritten, and the other 2 are values extracted incompletely (for example, the coin count only stored as "a 1915-S Barber quarter"). Of the pin's 15 LongMemEval failures, 10 coincide with a store failure.

**The watchpoint can re-inject stale values.** On LongMemEval the watch arm gave the wrong-version value 10 times against the pin's 5. Reading those cases shows a specific mechanism. When the extractor writes an update under a new key instead of reusing the old one (for example `user | parents' length of stay: six months` in session 1, then `parents' length of stay: nine months` in session 2), the old value survives as an orphan key. The notes correctly say "nine months", so the new key passes the check, and the orphan fails it, because it disagrees with the correct notes. The watchpoint then appends `[current] user | parents' length of stay: six months`, and the answer follows the reminder. A selective check surfaces exactly the facts that disagree with the notes, and an orphaned stale value is always one of them. The pin shows both keys and the model usually picks the newer one. A second source of stale reminders is overly granular keys, such as `bbq sauce plan: Stock up on Sweet Baby Ray's`, kept alongside a changed `favorite bbq sauce` value.

### Exploratory follow-ups

Both follow-ups were decided after seeing the results above, and use the same tasks, judge, and stored extraction outputs.

**1. A stricter comparator (presence plus exclusivity).** The restatement must contain the stored value and add no other content words, so "pollen, gluten, soy" fails a check for `soy` and gets a reminder. Only the comparator changes.

| set | watch_strict | vs watch (Holm p) | vs pin (Holm p) | patch rate (keys) | memory chars |
|---|---|---|---|---|---|
| synth_std (n=60) | 57 (95.0%, CI 86% to 98%) | 12 vs 0, p = 0.001 | 0 vs 0, p = 1 | 1,266 of 9,449 (13%) | 353 |
| synth_hard (n=60) | 59 (98.3%, CI 91% to 100%) | 11 vs 0, p = 0.002 | 2 vs 0, p = 0.5 | 3,690 of 18,478 (20%) | 441 |
| lme (n=78) | 66 (84.6%, CI 75% to 91%) | 7 vs 2, p = 0.90 | 7 vs 4, p = 1 | 1,924 of 2,291 (84%) | 1,619 |

On synthetic tasks this fixes the accumulation failure (allergy queries go from 3 to 23 of 27 correct) and ties the pin while carrying about half the pin's memory (353 to 441 characters vs 609 to 783), at about 1.4 times the pin's calls. On LongMemEval, the paraphrased notes almost never restate a value word for word, so the strict check patches 84% of keys and becomes a more expensive pin. Its 66 of 78 is not distinguishable from the pin or the original watchpoint.

**2. Store deduplication.** One extra call per session lists older keys that are superseded by a newer key for the same fact, and the code deletes them, but only keys written before the current session. It removed keys in only 5 of 78 LongMemEval tasks (0.12 keys per task), and it fixed the orphan-key case above (`db467c8c`). Overall: pin_dd 68 vs pin 63 (5 vs 0, Holm p = 0.38) and watch_dd 62 vs watch 61 (5 vs 4, p = 1). **The pin_dd gain is not a dedup effect.** All 5 flips happened on tasks where deduplication deleted nothing, so the stores and prompts were identical. See the next section.

### Repeat-call noise

The deduplication run repeated the pin's answer call with a byte-identical prompt on 73 tasks (temperature 0). The verdict changed on 5 of 73 (6.8%). For example, on `dfde3500` one call answered "Thursday" and the repeat answered "Wednesday". The backbone is not deterministic at temperature 0, so any single-run difference of about 5 tasks out of 78 between arms is within run-to-run noise. Every comparison above that is not Holm-significant should be read that way.

## Judge validation

| check | reference | n | agreement | Cohen's kappa |
|---|---|---|---|---|
| yes/no judge, synthetic answers | Supersede's exact string grader | 720 (120 tasks x 6 arms) | 701 (97.4%) | 0.887 |
| yes/no judge, LongMemEval short golds (3 words or fewer, not abstention) | number-word-normalized string containment | 354 (59 tasks x 6 arms) | 323 (91.2%) | 0.709 |
| same set | Supersede's unmodified string grader | 354 | 292 (82.5%) | |
| yes/no judge, LongMemEval | my hand labels, stratified 24 judge-yes and 24 judge-no, seed 7 | 48 | 48 (100%) | 1.000 |
| four-way stale judge, LongMemEval | my hand labels, 20 judged stale, 12 wrong, 8 correct, 4 ambiguous, seed 11 | 44 | 41 exact; 44 on stale vs not stale | 1.000 (stale vs not stale) |

The hand labels were made from printouts showing only the question, gold (and wrong-version value), and answer, not the judge's verdict. The labeler was this agent (a Claude model), not a human, so "hand labels" here means a different model from the judge reading every item, not human annotation. Most judge vs string disagreements are string-match errors ("weekly" for "every week", "above the bed in the bedroom" for "in my bedroom", "1,300" for "1300"). On synthetic tasks, 16 of the 19 disagreements are the judge accepting an "ambiguous" answer that lists the current value among stale ones. The yes/no judge prompt asks whether the answer "conveys the gold answer", so it is lenient on hedged lists. That is why the synthetic accuracy here uses the exact grader. The three four-way disagreements are answers that name both values but frame the gold as current (judge: ambiguous; me: correct), plus one non-committal answer.

Supersede's raw grader crashes on the two integer golds. That is fixed by converting them to strings. Its string match is unreliable on LongMemEval (82.5% agreement even on short golds), which supports using the judge there.

## Threats to validity

- **One backbone, one run.** Repeat-call noise is about 7% of verdicts, measured above. Differences without Holm significance are not evidence.
- **The judge is the backbone.** It is validated against exact grading, string matching, and 92 hand-labeled items, but the hand labels come from an AI labeler, and self-preference cannot be ruled out.
- **LongMemEval oracle has only 2 sessions per task**, so "recursive" compaction is only 2 rounds there. The synthetic sets supply 13 to 17 rounds but are short (under 700 characters of facts), and the 1200-character budget is not binding on them: the model writes 325 to 462 characters even when allowed 1,200.
- **The stale labels on LongMemEval come from a judge** that sees the gold. They were hand-checked on 44 answers but not on all 71 labels.
- **The history-question split is a regex** chosen after seeing failures (n=13). It is exploratory.
- **The keyword comparator** was tuned once during the smoke test (ordinal suffixes, a few hedge words, threshold 0.5) before any main-run result. It is still crude on paraphrase: on LongMemEval it flagged 748 "differs" out of 2,291 checks, mostly paraphrases.
- **The synthetic "allergic to" phrasing is arguably ambiguous in English**, so some of the notes arms' "ambiguous" answers are defensible readings. The full-context arm also gave 4 such answers.
- **Patches sit outside the notes budget**, so the watch arm is not memory-matched to notes300. Memory sizes are reported so the comparison can be made by size.
- One LongMemEval task (`89941a94`) failed grading three times on empty completions with a 20-token judge cap. The cap was raised to 200 for the remaining uncached judge calls only. The prompt was unchanged.

## Interpretation

Bounded notes lose knowledge updates in two different ways, and the fixes split along that line. The first is **dropping**: a fact or its update does not fit in 300 characters. A bigger budget, the pin, and the watchpoint all fix it. The second is **failing to supersede**: the notes keep the old value next to the new one, or keep the wrong one. Only overwrite semantics fix it (the pin, or a watchpoint whose check also rejects extra values). A presence-only check cannot see it.

For a harness builder, the evidence points to pinning a newest-value-wins store for facts that are queried by their current value. On synthetic tasks it reaches full-context accuracy, and on LongMemEval current-value questions it matches full context. Do not rely on it for questions about history, because overwrite semantics delete exactly what those questions need, and a larger plain notes budget beats it there. The watchpoint did not earn its selectivity in this setting. On long real sessions it patches almost every round, so it costs as much as the pin. Its presence-only check misses accumulated stale values. And it can actively resurrect stale values that survive as orphaned keys in the store. The stricter comparator repairs the second problem on clean synthetic data, at about half the pin's memory, but on real paraphrased notes it collapses into pinning. This matches the paper's discussion section: once a check is strict enough to work, it patches nearly every time, and selectivity only pays off where values are short and canonical.

## Files

- `e4.py`: main driver (all six arms, extraction, check, judging). Model calls go through `../shared/orclient.py`.
- `e4_strict.py`, `e4_dedupe.py`: the two exploratory follow-ups.
- `analyze.py`: regenerates every table from raw files (`results/tables.md`, `results/summary.json`, `results/per_task.json`).
- `results/units/<set>/<qid>/*.json`: raw per-task, per-arm outputs. These include answers, notes trajectories, store snapshots per session, watch rounds with patched keys and restated values, and judge outputs.
- `results/tasks_meta.json`: questions, golds, and synthetic stale values.
- `results/hand_label_sample.json`, `results/hand_labels.json`, `results/hand_label_sample_v4.json`, `results/hand_labels_v4.json`: judge validation samples and labels.
- `results/run*.log`: run logs. Token use per call is in the shared `../usage.jsonl` under tags `e4|<set>|<qid>|<unit>|<kind>`. In total, E4 made 18,325 tagged calls (10.7M input and 1.7M output tokens), including grading.

## Reproduce

```bash
cd studies/overnight-survey/e04_supersede
PY=/private/tmp/supersede-venv/bin/python
$PY e4.py                                   # main run, resumable (cached per unit)
$PY e4_strict.py                            # follow-up 1
$PY e4_dedupe.py --sets lme                 # follow-up 2
$PY analyze.py                              # all tables
```

A small second-backbone rerun keeps the judge fixed and writes to `results/units_<model>/` with its own usage tags. `':free'` models are refused:

```bash
$PY e4.py --model openai/gpt-4.1-mini --sets lme synth_hard --n-synth 30 --workers 8
$PY analyze.py --model openai/gpt-4.1-mini   # writes results/analysis_openai_gpt_4_1_mini/
```
