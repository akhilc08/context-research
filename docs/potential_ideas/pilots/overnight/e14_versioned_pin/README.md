# E14: a versioned fact pin

E4 found that pinning a newest-value-wins fact store next to 300-character notes fixes current-value questions but fails on questions about the past ("What was my previous...", "Where did I initially..."), because overwriting deletes the old value. This experiment keeps the history instead. Each key holds an ordered list of values with the session in which each was first stated, and the pin shows it as one line per fact:

```
- user | charity 5k personal best: 25:50 (current, since session 2); previously 27:12 (session 1)
- frank | city of residence: Chicago (current, since session 15); previously Detroit (sessions 10 to 14), Dallas (sessions 1 to 9)
```

All numbers come from one backbone (`stealth/space-bunny-alpha` through OpenRouter, low reasoning effort, temperature 0), run twice. Every table is regenerated from the raw files by `analyze.py`.

## Hypotheses and primary metric

Fixed before the main run, after a one-task smoke test:

- **H1.** A versioned pin recovers the history questions that E4's newest-value-wins pin loses, without hurting current-value questions.
- **H2.** Canonical keys (the extractor sees the existing key list and must reuse a key for the same attribute) reduce orphan keys, where an update is stored under a new key and the old value stays alive as if current.
- **H3.** 1,200-character notes plus the versioned pin match full context.

**Primary metric:** LongMemEval knowledge-update accuracy (n=78) under E4's judge, averaged over two repeats. **Primary comparison:** versioned pin with canonical keys (`vpin_canon`) vs E4's pin (`pin`). **Key secondary:** accuracy on history questions, which are E4's 13 LongMemEval history questions plus one new history question for each synthetic task. All planned comparisons are listed in `analyze.py` (`PAIRS`) and are Holm-corrected together within each table.

## Design

### Tasks

| set | n | sessions per task | questions |
|---|---|---|---|
| LongMemEval (`lme`) | 78 | 2 | the dataset's question; 13 of them ask about an older value (E4's regex split, reused unchanged) |
| Supersede synthetic, default config (`synth_std`) | 30 (seeds 0 to 29) | 13 | the current value (Supersede's query) and the previous value |
| Supersede synthetic, hard config (`synth_hard`) | 30 (seeds 1000 to 1029) | 17 | same two questions |

The synthetic history question is new in E14: "What was the previous value for: 'Frank lives in ___', i.e. the value it had just before it changed to its current value? Reply with only that single previous value, nothing else." Its gold is the second-to-last value of the queried chain, and the wrong-version values are the current value and the original value. It is asked from the same memory as the current-value question, so the two questions share every notes trajectory and store and differ only in the answer call. The first draft of this wording ("Before its most recent change, what was the value...") was replaced after the smoke test because the full-context arm read it as "the original value". The synthetic sets were cut from a planned 40 to 30 tasks each when provider errors (above 50% of calls for about two hours) slowed the run. The extra rep 1 units for `synth_std` seeds 30 to 36 are on disk but excluded, since analysis needs both repeats.

### Arms

| arm | what the answering model sees |
|---|---|
| `full` | every session (ceiling) |
| `notes300` | Supersede's NOTES protocol: per-session rewrite, hard cap 300 characters |
| `notes1200` | the same at 1,200 characters |
| `notes_tm` | token-matched control (LongMemEval only): the same at 2,300 characters, the mean size of `vpin_canon`'s memory in rep 1 |
| `pin` | E4's arm: `notes300` notes plus the store from E4's extractor, newest value wins |
| `vpin` | `notes300` notes plus the **same** extraction rendered as a versioned store. Only the storage semantics differ from `pin` |
| `vpin_canon` | `notes300` notes plus a versioned store from the canonical-key extractor |
| `n1200_vpin` | `notes1200` notes plus the canonical versioned store |

The notes prompts, answer prompts, and full-context prompt are E4's (Supersede's own). E4's extractor prompt is reused unchanged. The canonical-key extractor adds a list of existing keys with their current values and a rule: one attribute gets exactly one key for the whole history, an update must reuse the existing key and set `"reused": true`, and new keys should be general enough to hold future values. A restatement of the current value is not a new version. Keys are lowercased with whitespace collapsed. The versioned block's header tells the model that the first value is current, later values are older, and a higher session number is more recent. No method sees a question, gold, or stale label while building memory.

The token-matched control was run only on LongMemEval, because on the synthetic sets the notes never reach even 1,200 characters (E4 measured 325 to 462), so a larger budget changes nothing there. The model wrote 2,089 characters on average at the 2,300 cap.

### Repeats

Each arm was run twice. Repeat 1 reuses E4's raw outputs for the units E4 already ran with the same model and prompts: full-context answers, `notes300` and `notes1200` trajectories and answers, E4's extraction (per-session facts recovered as the difference between E4's store snapshots), and the pin's answer to the current-value question. These are copied into `results/units/rep1`. Everything else in repeat 1, and every call in repeat 2, is new. Repeat 2 reruns the whole pipeline, including notes and extraction, so the repeat-to-repeat difference includes extraction noise.

### Grading

- **LongMemEval:** E4's yes/no judge (Supersede's prompt, with LongMemEval's abstention variant), applied fresh to every answer in both repeats, including the E4 answers reused in repeat 1. Stale and ambiguous answers use E4's four-way judge with E4's per-task wrong-version labels (71 of 78 tasks have one).
- **Synthetic:** Supersede's exact string grader (`classify`): correct, stale (a wrong-version value only), ambiguous (both), or wrong.
- **Statistics:** each task gets a mean score over the two repeats (0, 0.5, or 1). The paired test is an exact two-sided sign test on those means (McNemar's test when scores are 0 or 1), Holm-corrected across the planned comparisons in each table. Per-repeat McNemar p values are also reported. Confidence intervals are percentile bootstraps over tasks (4,000 resamples).
- **Orphan keys.** On synthetic tasks the timelines are regenerated from their seeds, so orphans are counted exactly: a tracked chain is orphaned when two or more keys for that subject currently hold a value from the chain. On LongMemEval there is no ground truth, so a separate audit call (the same model, measurement only, never shown to a method) lists groups of keys that describe the same attribute. I hand-read 16 audit outputs. They mix true orphans (`user | parents' length of stay` next to `parents' length of stay`) with looser groupings of related keys (`user | dinner party plan` with `user | selected main course`), so treat the audit as a rough relative measure.

## Results

### Primary: LongMemEval (n=78)

| arm | rep 1 | rep 2 | mean accuracy | 95% CI | same verdict in both repeats | stale (mean of 71) | memory at answer time (chars) | input tokens per task | calls |
|---|---|---|---|---|---|---|---|---|---|
| full | 71 | 69 | 89.7% | 83% to 96% | 74 | 6.5 | 27,907 (whole history) | 6,017 | 1 |
| notes300 | 51 | 55 | 67.9% | 58% to 77% | 64 | 5.5 | 299 | 6,666 | 3 |
| notes1200 | 67 | 62 | 82.7% | 75% to 90% | 67 | 4.5 | 1,151 | 6,960 | 3 |
| notes_tm (2,300) | 66 | 69 | 86.5% | 79% to 92% | 67 | 3.5 | 2,089 | 7,251 | 3 |
| pin (E4) | 64 | 65 | 82.7% | 74% to 90% | 71 | 5.5 | 1,637 | 13,646 | 5 |
| vpin | 72 | 76 | **94.9%** | 90% to 99% | 74 | 2.0 | 2,490 | 13,838 | 5 |
| vpin_canon | 74 | 74 | **94.9%** | 90% to 99% | 74 | 1.5 | 2,344 | 14,108 | 5 |
| n1200_vpin | 76 | 75 | **96.8%** | 93% to 99% | 75 | 1.5 | 3,196 | 14,402 | 5 |

Token and call counts come from repeat 2, where every call is fresh. They cover building the memory plus the answer call and exclude grading.

| comparison (A vs B) | mean correct A, B | tasks where A scores higher | tasks where B scores higher | sign test p | Holm p (8 tests) | paired difference, 95% CI |
|---|---|---|---|---|---|---|
| vpin_canon vs pin | 74, 64.5 | 14 | 2 | 0.004 | **0.025** | +5.1 to +19.9 points |
| vpin vs pin | 74, 64.5 | 15 | 1 | 0.0005 | **0.004** | +5.8 to +19.2 points |
| vpin_canon vs vpin | 74, 74 | 3 | 4 | 1 | 1 | -3.8 to +3.8 points |
| vpin_canon vs notes1200 | 74, 64.5 | 17 | 4 | 0.007 | **0.036** | +5.1 to +19.9 points |
| vpin_canon vs full | 74, 70 | 9 | 6 | 0.61 | 1 | -1.9 to +12.8 points |
| n1200_vpin vs notes1200 | 75.5, 64.5 | 17 | 1 | 0.0001 | **0.001** | +7.7 to +21.2 points |
| n1200_vpin vs full | 75.5, 70 | 9 | 3 | 0.15 | 0.44 | 0.0 to +14.7 points |
| notes_tm vs vpin_canon | 67.5, 74 | 3 | 12 | 0.035 | 0.14 | -14.7 to -2.6 points |

On the primary comparison, the versioned pin with canonical keys beats E4's pin by 12 points (94.9% vs 82.7%, Holm p = 0.025), and it beats notes1200 too. Both repeats agree in direction and size: 74 and 74 vs 64 and 65. The canonical keys add nothing measurable on top of versioning (`vpin` and `vpin_canon` are tied at 74 of 78 mean correct). The versioned arms score above full context (94.9% and 96.8% vs 89.7%), but that difference is not significant. The token-matched notes control (86.5%) does not reach the versioned pin, so the gain is not just extra memory (3 vs 12 tasks, p = 0.035 uncorrected, 0.14 after Holm).

### Split by question type (LongMemEval)

| arm | history questions (n=13), mean correct | 95% CI | current-value questions (n=65), mean correct | 95% CI |
|---|---|---|---|---|
| full | 10.5 (80.8%) | 58% to 100% | 59.5 (91.5%) | 85% to 97% |
| notes300 | 1.5 (11.5%) | 0% to 23% | 51.5 (79.2%) | 70% to 88% |
| notes1200 | 7 (53.8%) | 31% to 77% | 57.5 (88.5%) | 82% to 95% |
| notes_tm | 8 (61.5%) | 42% to 81% | 59.5 (91.5%) | 85% to 97% |
| pin | 2.5 (19.2%) | 8% to 31% | 62 (95.4%) | 90% to 99% |
| vpin | 11 (84.6%) | 65% to 100% | 63 (96.9%) | 93% to 100% |
| vpin_canon | 11 (84.6%) | 65% to 100% | 63 (96.9%) | 92% to 100% |
| n1200_vpin | 12 (92.3%) | 77% to 100% | 63.5 (97.7%) | 95% to 100% |

The whole LongMemEval gain comes from history questions. There, `vpin_canon` beats `pin` on 11 tasks and loses on none (Holm p = 0.007 within the history table). On current-value questions it is tied with `pin` (3 vs 2 tasks, p = 1), so H1's "without hurting current questions" holds here. The history split was defined in E4 after E4 saw its results, but it was reused unchanged here and fixed before this run.

### Synthetic tasks (n=60, both configs pooled, exact grading)

| arm | current value: mean correct | 95% CI | history: mean correct | 95% CI | history: stale (mean) | memory chars |
|---|---|---|---|---|---|---|
| full | 57.5 (95.8%) | 92% to 99% | 53.5 (89.2%) | 83% to 94% | 6.5 | 970 |
| notes300 | 42.5 (70.8%) | 60% to 81% | 8.5 (14.2%) | 8% to 22% | 13.5 | 277 |
| notes1200 | 45.5 (75.8%) | 65% to 86% | 3.5 (5.8%) | 2% to 12% | 12 | 394 |
| pin | 58 (96.7%) | 93% to 99% | 9.5 (15.8%) | 8% to 24% | 8.5 | 746 to 799 |
| vpin | 58.5 (97.5%) | 94% to 100% | 56.5 (94.2%) | 89% to 98% | 3 | 1,831 |
| vpin_canon | 57 (95.0%) | 90% to 99% | 56 (93.3%) | 88% to 98% | 2 | 1,895 |
| n1200_vpin | 57 (95.0%) | 90% to 99% | 57.5 (95.8%) | 92% to 99% | 1 | 2,011 |

On history questions over 13 to 17 rounds of compaction, every notes-based arm and E4's pin collapse (6% to 16%), because the notes are told to overwrite outdated facts and the pin overwrites by design. The usual answer is "unknown". The versioned pin answers 93% to 96% of them, slightly above full context (89%). `vpin_canon` vs `pin`: 54 tasks higher, 1 lower, Holm p < 1e-13. On current-value questions the versioned pin ties the newest-value pin and full context (all 95% to 98%, every comparison p ≥ 0.37).

Full context misses 11% of synthetic history questions. In 12 of its 13 misses across both repeats, it answered with the original value instead of the previous one (the other gave the current value) (for example "Dallas" instead of "Detroit" for a city chain Dallas, Detroit, Chicago). When reading raw sessions, the model sometimes counts back to the first value rather than the one just before the current value. The versioned line orders this explicitly, so the answering model does not have to count.

### Orphan keys (H2)

| store | LongMemEval: tasks with a duplicate group (audit), rep 1 / rep 2 | LongMemEval: redundant keys per task | synthetic: orphaned chains (exact), rep 1 / rep 2 | synthetic: store holds the queried fact's correct previous value |
|---|---|---|---|---|
| E4 extractor | 18 / 19 of 78 | 0.36 / 0.31 | 11 / 13 of 420 | 56 / 58 of 60 |
| canonical-key extractor | 11 / 14 of 78 | 0.18 / 0.21 | 13 / 11 of 420 | 57 / 57 of 60 |

H2 gets weak support. On LongMemEval the audit finds duplicate groups in about a third fewer tasks with canonical keys (12.5 vs 18.5 per repeat), and the E4 orphan example (`db467c8c`, the parents' length of stay) is gone in both canonical repeats. But fewer orphans did not change accuracy (`vpin_canon` vs `vpin`: 3 vs 4 tasks). With a versioned store an orphan is less harmful than in E4's watchpoint, because nothing labels the orphan "[current]", and the model can compare session numbers. On synthetic tasks, canonical keys changed nothing. Every exact orphan there is the allergy predicate: both extractors read "X is now allergic to Y" as an added allergy and store one key per allergen (`liam | pollen allergy`, `liam | shellfish allergy`). That is a defensible reading of the sentence, which E4 already flagged as ambiguous, not a key-naming failure, so a key-reuse rule cannot fix it. Canonicalization also costs about 2,300 more input tokens per synthetic task, because the key list is longer than E4's store rendering.

### Repeat noise

| arm | LongMemEval verdicts that differ between repeats | synthetic current | synthetic history |
|---|---|---|---|
| full | 4 of 78 | 3 of 60 | 11 of 60 |
| notes300 | 14 | 9 | 11 |
| notes1200 | 11 | 3 | 3 |
| notes_tm | 11 | n/a | n/a |
| pin | 7 | 4 | 9 |
| vpin | 4 | 3 | 5 |
| vpin_canon | 4 | 4 | 6 |
| n1200_vpin | 3 | 4 | 5 |

Repeats flip 4% to 18% of LongMemEval verdicts per arm (E4 measured 6.8% for a byte-identical answer call; these repeats also redo notes and extraction). The notes arms are the noisiest, because the 300- and 1,200-character rewrites change from run to run. `notes1200` fell from 67 to 62 between repeats, so its single-run 87% in E4 was on the lucky side. The versioned arms were the most stable (3 to 4 flips of 78). The primary result holds in each repeat on its own: `vpin_canon` vs `pin` McNemar p = 0.006 in repeat 1 and 0.012 in repeat 2.

### Cost

On LongMemEval every store arm costs about twice the input tokens of the notes arms (13,600 to 14,400 vs 6,700 to 7,300 per task), because each session is read once more by the extractor. The versioned store adds almost nothing over E4's pin at build time (+200 to +460 input tokens per task). Its cost is at answer time: about 700 to 900 more characters in the prompt on LongMemEval (2,344 to 2,490 vs 1,637), and about 2.4 times the pin's size on synthetic tasks (1,831 to 1,895 vs 746 to 799), because every tracked chain carries two old values. On synthetic tasks the store arms make 31 calls per task against 16 for notes.

## Qualitative examples

From repeat 1 on LongMemEval (gold in brackets):

- `50635ada`, "What was my previous frequent flyer status on United Airlines?" [Premier Silver]. `pin`: "Your previous United Airlines frequent-flyer status wasn't provided; the only noted status is your current Premier Gold status." `vpin`: "Premier Silver." The same extraction under both arms. The only difference is that the old value was kept.
- `c4ea545c`, "Do I go to the gym more frequently than I did previously?" [Yes]. `full`: "...you haven't specified exactly how often you went previously, so I can't determine..." `vpin_canon`: "Yes. You increased your gym schedule from 3 days a week previously to 4 days a week now." Full context missed a value that the versioned line made explicit.
- `e66b632c`, "What was my previous personal best time for the charity 5K run?" [27:45]. `full` and `pin` both answer 26:30. All three versioned arms answer 27:45.
- `6071bd76`, "did I switch to more water per tablespoon of coffee, or less?" [less]. `vpin` (E4 extractor) stored `french_press_ratio: 1 tbsp per 5 oz (current, since session 2); previously 1 tbsp per 6 oz (session 1)` and answered correctly. In repeat 1 the canonical extractor never recorded the session 2 update, so its store held only the old 6-ounce ratio, and the model answered "more water ... from 5 oz to 6 oz". A versioned store is only as good as its extraction.
- `0ddfec37`, "How many autographed baseballs have I added in the first three months?" [15]. Every store held `autographed baseball count: 20 (current, since session 2); previously 15 (session 1)`, and every store arm answered 20. The history was there, but the model did not connect "first three months" to the session 1 value. This one fails in all arms except full context.
- `9bbe84a2`, "What was my previous goal for my Apex Legends level?" [level 100]. E4's extractor wrote all its Apex keys in session 2, so the level 100 goal from session 1 was never stored, and `vpin` said it was not recorded. The canonical extractor stored `apex legends level goal: Reach level 150 eventually (current, since session 2); previously Reach level 100 before the end of the year (session 1)`.

## Judge validation

The judges are E4's, which were validated there against exact grading (kappa 0.887 on 720 synthetic answers) and against 92 hand labels. For E14 I labeled 48 new LongMemEval verdicts, drawn with seed 7 from the arms E4 never judged (`vpin`, `vpin_canon`, `n1200_vpin`, `notes_tm`) plus `pin`. The sample has 24 judge-yes and 24 judge-no verdicts, includes 8 history-question yeses, and was labeled from question, gold, and answer only, without seeing the verdict. Agreement was 46 of 48 (Cohen's kappa 0.917). The two disagreements:

- `89941a94`, `notes_tm`. The judge said no to "you have a road bike and a hybrid bike", because the hybrid is the bike bought afterwards. I said yes.
- `f685340e_abs`, `n1200_vpin`, an abstention item about table tennis. The judge accepted an answer about tennis. I did not.

The labeler is this agent (a Claude model), not a human. Synthetic grading is exact and needs no judge.

## Threats to validity

- **One backbone.** The judge is the same model as the backbone. Self-preference cannot be ruled out, though the hand labels agree with it.
- **Repeat 1 is partly E4's run.** Repeat 1 reuses E4's outputs for full, notes300, notes1200, the E4 extraction, and the pin's current-value answer, made with the same model and prompts but on an earlier day. Repeat 2 is entirely fresh, and every primary comparison holds within repeat 2 alone (`vpin_canon` vs `pin` 74 vs 65, McNemar p = 0.012).
- **The history question sets are small or constructed.** LongMemEval has 13 history questions. The synthetic history questions are mine, built from the generator's chains. They ask for the immediately previous value, which is the case the versioned format makes easiest.
- **LongMemEval has only 2 sessions per task,** so the versioned line there is at most "current since session 2; previously ... (session 1)". Longer real histories with many small updates could make the versioned block much larger. On synthetic tasks with 13 to 17 sessions it grew to about 2.4 times the size of the newest-value store.
- **The token-matched control is matched on characters at the cap,** and the model used 2,089 of 2,300 characters, about 250 below `vpin_canon`'s memory. It was run on LongMemEval only.
- **The LongMemEval orphan audit is a model's judgment**, and by my reading of 16 outputs it over-counts related keys as duplicates. The synthetic orphan count is exact but is driven entirely by the allergy wording.
- **Versioned beats full context** on LongMemEval (95% to 97% vs 90%) and on synthetic history (93% to 96% vs 89%), but neither difference is significant. Do not read it as "better than full context".
- **Provider instability.** For about two hours over half of all calls returned empty 502 errors. The client retried them (up to 12 tries), and 6 LongMemEval units that failed outright were rerun from cache. No answer was dropped from the analysis.

## Interpretation

E4's pin works on current values and fails on history for a structural reason: it overwrites. Keeping the history and showing it with session numbers fixes that failure almost completely. LongMemEval history questions go from 19% to 85% correct, and synthetic history questions from 16% to 93%, with no cost on current-value questions and a modest prompt-size cost. On LongMemEval this makes the 300-character notes plus versioned pin the best bounded-memory arm tested in E4 or E14: 94.9%, above notes1200 (Holm p = 0.036) and a 2,300-character notes budget, and level with full context. Adding 1,200-character notes on top changes little (96.8%).

The canonical-key extractor did what it was designed to do on LongMemEval (fewer duplicate keys) but bought no accuracy, and it did nothing on synthetic tasks, where the remaining "orphans" are a reading of the source text rather than a naming problem. For a harness builder, the evidence says to keep history in the fact store and render it with when each value held. Key canonicalization is optional at this scale. The remaining failures are extraction misses (an update never recorded) and answer-time misreadings of a correct history, not storage semantics.

## Files

- `e14.py`: driver for all stages (`run`, `tm`, `judge`, `orphan`). It has the extraction prompts, the versioned store (`build_versioned`, `render_versioned`), and the E4 reuse logic. Model calls go through `../orclient.py`.
- `analyze.py`: regenerates every table (`results/tables.md`, `results/summary.json`, `results/per_task.json`).
- `results/units/rep{1,2}/<set>/<qid>/`: raw outputs. Notes trajectories, per-session extracted facts for both extractors, every answer (`ans_<arm>_<cur|hist>.json`, with memory size), LongMemEval judge verdicts (`judge.json`), and orphan audits (`orphan_audit.json`). Units copied from E4 carry `"source": "e4"`.
- `results/tasks_meta.json`: questions, golds, and stale values for all tasks (synthetic sets listed to seed 39, analysis uses those complete in both repeats, seeds 0 to 29 and 1000 to 1029).
- `results/tm_budget.json`: the token-matched budget and how it was set.
- `results/hand_label_sample.json`, `results/hand_labels.json`: judge spot check.
- `results/run*.log`: run logs. Token use per call is in `../usage.jsonl` under tags `e14|rep<r>|<set>|<qid>|<unit>|<kind>`. E14 made 10,938 tagged calls (8.7M input and 0.84M output tokens), including grading and the smoke test.

## Reproduce

```bash
cd docs/potential_ideas/pilots/overnight/e14_versioned_pin
PY=/private/tmp/supersede-venv/bin/python
$PY e14.py --stage run --sets lme
$PY e14.py --stage tm --sets lme          # budget from results/tm_budget.json
$PY e14.py --stage judge
$PY e14.py --stage orphan
$PY e14.py --stage run --sets synth_std synth_hard --n-synth 30
$PY analyze.py
```

A second backbone keeps the judge fixed, does not reuse E4's outputs, and writes to `results/units_<model>/` with its own usage tags. ':free' models are refused. The token-matched budget should be reset from that backbone's `vpin_canon` memory size with `--tm-budget`.

```bash
$PY e14.py --model openai/gpt-4.1-mini --stage run --sets lme synth_hard --n-synth 30
$PY e14.py --model openai/gpt-4.1-mini --stage tm --sets lme --tm-budget 2300
$PY e14.py --model openai/gpt-4.1-mini --stage judge
$PY e14.py --model openai/gpt-4.1-mini --stage orphan
$PY analyze.py --model openai/gpt-4.1-mini   # writes results/analysis_openai_gpt_4_1_mini/
```
