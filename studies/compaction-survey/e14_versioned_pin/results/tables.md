## LongMemEval knowledge-update

Accuracy is E4's yes/no judge. Stale and ambiguous come from E4's four-way judge on tasks with an E4 wrong-version label. Means are over the two repeats. Rep 1 of full, notes300, notes1200, and pin reuses E4's answers (re-judged here).

### lme_all (n=78)

| arm | rep 1 | rep 2 | mean acc | 95% CI (bootstrap) | per-task agreement | stale (mean) | ambiguous (mean) | memory chars |
|---|---|---|---|---|---|---|---|---|
| full | 71 | 69 | 89.7% | 83% to 96% | 74/78 | 6.5/71 | 1.5/71 | 27,907 |
| notes300 | 51 | 55 | 67.9% | 58% to 77% | 64/78 | 5.5/71 | 0.5/71 | 299 |
| notes1200 | 67 | 62 | 82.7% | 75% to 90% | 67/78 | 4.5/71 | 0.5/71 | 1,151 |
| notes_tm | 66 | 69 | 86.5% | 79% to 92% | 67/78 | 3.5/71 | 1/71 | 2,089 |
| pin | 64 | 65 | 82.7% | 74% to 90% | 71/78 | 5.5/71 | 0.5/71 | 1,637 |
| vpin | 72 | 76 | 94.9% | 90% to 99% | 74/78 | 2/71 | 0/71 | 2,490 |
| vpin_canon | 74 | 74 | 94.9% | 90% to 99% | 74/78 | 1.5/71 | 0/71 | 2,344 |
| n1200_vpin | 76 | 75 | 96.8% | 93% to 99% | 75/78 | 1.5/71 | 0.5/71 | 3,196 |

| A vs B | mean correct A, B | tasks A higher | tasks B higher | sign test p | Holm p (8 tests) | McNemar p rep 1, rep 2 | mean diff 95% CI |
|---|---|---|---|---|---|---|---|
| vpin_canon vs pin | 74, 64.5 | 14 | 2 | 0.00418 | 0.0251 | 0.00635, 0.0117 | +5.1% to +19.9% |
| vpin vs pin | 74, 64.5 | 15 | 1 | 0.000519 | 0.00363 | 0.0215, 0.000977 | +5.8% to +19.2% |
| vpin_canon vs vpin | 74, 74 | 3 | 4 | 1 | 1 | 0.625, 0.625 | -3.8% to +3.8% |
| vpin_canon vs notes1200 | 74, 64.5 | 17 | 4 | 0.0072 | 0.036 | 0.0654, 0.00418 | +5.1% to +19.9% |
| vpin_canon vs full | 74, 70 | 9 | 6 | 0.607 | 1 | 0.508, 0.267 | -1.9% to +12.8% |
| n1200_vpin vs notes1200 | 75.5, 64.5 | 17 | 1 | 0.000145 | 0.00116 | 0.0117, 0.000244 | +7.7% to +21.2% |
| n1200_vpin vs full | 75.5, 70 | 9 | 3 | 0.146 | 0.438 | 0.18, 0.146 | +0.0% to +14.7% |
| notes_tm vs vpin_canon | 67.5, 74 | 3 | 12 | 0.0352 | 0.141 | 0.0574, 0.18 | -14.7% to -2.6% |

### lme_history (n=13)

| arm | rep 1 | rep 2 | mean acc | 95% CI (bootstrap) | per-task agreement | stale (mean) | ambiguous (mean) | memory chars |
|---|---|---|---|---|---|---|---|---|
| full | 11 | 10 | 80.8% | 58% to 100% | 12/13 | 1.5/13 | 0/13 | 25,239 |
| notes300 | 1 | 2 | 11.5% | 0% to 23% | 10/13 | 3.5/13 | 0/13 | 299 |
| notes1200 | 9 | 5 | 53.8% | 31% to 77% | 9/13 | 2/13 | 0.5/13 | 1,099 |
| notes_tm | 8 | 8 | 61.5% | 42% to 81% | 7/13 | 1.5/13 | 0.5/13 | 2,044 |
| pin | 1 | 4 | 19.2% | 8% to 31% | 8/13 | 4/13 | 0.5/13 | 1,573 |
| vpin | 10 | 12 | 84.6% | 65% to 100% | 11/13 | 1/13 | 0/13 | 2,428 |
| vpin_canon | 11 | 11 | 84.6% | 65% to 100% | 11/13 | 1.5/13 | 0/13 | 2,336 |
| n1200_vpin | 12 | 12 | 92.3% | 77% to 100% | 13/13 | 1/13 | 0/13 | 3,136 |

| A vs B | mean correct A, B | tasks A higher | tasks B higher | sign test p | Holm p (8 tests) | McNemar p rep 1, rep 2 | mean diff 95% CI |
|---|---|---|---|---|---|---|---|
| vpin_canon vs pin | 11, 2.5 | 11 | 0 | 0.000977 | 0.00684 | 0.00195, 0.0156 | +46.2% to +84.6% |
| vpin vs pin | 11, 2.5 | 12 | 0 | 0.000488 | 0.00391 | 0.00391, 0.00781 | +50.0% to +80.8% |
| vpin_canon vs vpin | 11, 11 | 2 | 2 | 1 | 1 | 1, 1 | -15.4% to +15.4% |
| vpin_canon vs notes1200 | 11, 7 | 7 | 2 | 0.18 | 0.898 | 0.625, 0.0703 | +3.8% to +57.7% |
| vpin_canon vs full | 11, 10.5 | 3 | 3 | 1 | 1 | 1, 1 | -23.1% to +34.6% |
| n1200_vpin vs notes1200 | 12, 7 | 7 | 0 | 0.0156 | 0.0938 | 0.25, 0.0156 | +19.2% to +61.5% |
| n1200_vpin vs full | 12, 10.5 | 3 | 1 | 0.625 | 1 | 1, 0.625 | -15.4% to +38.5% |
| notes_tm vs vpin_canon | 8, 11 | 2 | 6 | 0.289 | 1 | 0.453, 0.375 | -50.0% to +3.8% |

### lme_current (n=65)

| arm | rep 1 | rep 2 | mean acc | 95% CI (bootstrap) | per-task agreement | stale (mean) | ambiguous (mean) | memory chars |
|---|---|---|---|---|---|---|---|---|
| full | 60 | 59 | 91.5% | 85% to 97% | 62/65 | 5/58 | 1.5/58 | 28,440 |
| notes300 | 50 | 53 | 79.2% | 70% to 88% | 54/65 | 2/58 | 0.5/58 | 298 |
| notes1200 | 58 | 57 | 88.5% | 82% to 95% | 58/65 | 2.5/58 | 0/58 | 1,161 |
| notes_tm | 58 | 61 | 91.5% | 85% to 97% | 60/65 | 2/58 | 0.5/58 | 2,098 |
| pin | 63 | 61 | 95.4% | 90% to 99% | 63/65 | 1.5/58 | 0/58 | 1,650 |
| vpin | 62 | 64 | 96.9% | 93% to 100% | 63/65 | 1/58 | 0/58 | 2,503 |
| vpin_canon | 63 | 63 | 96.9% | 92% to 100% | 63/65 | 0/58 | 0/58 | 2,345 |
| n1200_vpin | 64 | 63 | 97.7% | 95% to 100% | 62/65 | 0.5/58 | 0.5/58 | 3,208 |

| A vs B | mean correct A, B | tasks A higher | tasks B higher | sign test p | Holm p (8 tests) | McNemar p rep 1, rep 2 | mean diff 95% CI |
|---|---|---|---|---|---|---|---|
| vpin_canon vs pin | 63, 62 | 3 | 2 | 1 | 1 | 1, 0.625 | -2.3% to +6.2% |
| vpin vs pin | 63, 62 | 3 | 1 | 0.625 | 1 | 1, 0.25 | -1.5% to +4.6% |
| vpin_canon vs vpin | 63, 63 | 1 | 2 | 1 | 1 | 1, 1 | -3.1% to +3.8% |
| vpin_canon vs notes1200 | 63, 57.5 | 10 | 2 | 0.0386 | 0.27 | 0.125, 0.0703 | +2.3% to +15.4% |
| vpin_canon vs full | 63, 59.5 | 6 | 3 | 0.508 | 1 | 0.375, 0.289 | -0.8% to +13.1% |
| n1200_vpin vs notes1200 | 63.5, 57.5 | 10 | 1 | 0.0117 | 0.0938 | 0.0703, 0.0312 | +3.1% to +16.2% |
| n1200_vpin vs full | 63.5, 59.5 | 6 | 2 | 0.289 | 1 | 0.219, 0.289 | +0.0% to +13.1% |
| notes_tm vs vpin_canon | 59.5, 63 | 1 | 6 | 0.125 | 0.75 | 0.125, 0.625 | -10.8% to -0.8% |

## Synthetic Supersede tasks (exact grading)

Each task is asked two questions from the same memory: the current value (Supersede's query) and the previous value (the value just before the current one). Both configs pooled.

### synth_current (n=60)

| arm | rep 1 | rep 2 | mean acc | 95% CI (bootstrap) | per-task agreement | stale (mean) | ambiguous (mean) | memory chars |
|---|---|---|---|---|---|---|---|---|
| full | 57 | 58 | 95.8% | 92% to 99% | 57/60 | 0/60 | 2.5/60 | 970 |
| notes300 | 44 | 41 | 70.8% | 60% to 81% | 51/60 | 2/60 | 11.5/60 | 277 |
| notes1200 | 46 | 45 | 75.8% | 65% to 86% | 57/60 | 0/60 | 14.5/60 | 394 |
| pin | 57 | 59 | 96.7% | 93% to 99% | 56/60 | 1/60 | 0.5/60 | 746 |
| vpin | 58 | 59 | 97.5% | 94% to 100% | 57/60 | 1/60 | 0/60 | 1,831 |
| vpin_canon | 56 | 58 | 95.0% | 90% to 99% | 56/60 | 1.5/60 | 1.5/60 | 1,895 |
| n1200_vpin | 56 | 58 | 95.0% | 90% to 99% | 56/60 | 1.5/60 | 1.5/60 | 2,011 |

| A vs B | mean correct A, B | tasks A higher | tasks B higher | sign test p | Holm p (7 tests) | McNemar p rep 1, rep 2 | mean diff 95% CI |
|---|---|---|---|---|---|---|---|
| vpin_canon vs pin | 57, 58 | 2 | 4 | 0.688 | 1 | 1, 1 | -5.8% to +2.5% |
| vpin vs pin | 58.5, 58 | 1 | 0 | 1 | 1 | 1, 1 | +0.0% to +2.5% |
| vpin_canon vs vpin | 57, 58.5 | 1 | 4 | 0.375 | 1 | 0.5, 1 | -6.7% to +0.8% |
| vpin_canon vs notes1200 | 57, 45.5 | 15 | 0 | 6.1e-05 | 0.000427 | 0.00195, 0.000244 | +10.8% to +28.3% |
| vpin_canon vs full | 57, 57.5 | 3 | 3 | 1 | 1 | 1, 1 | -5.8% to +4.2% |
| n1200_vpin vs notes1200 | 57, 45.5 | 15 | 0 | 6.1e-05 | 0.000427 | 0.00195, 0.000244 | +10.8% to +28.3% |
| n1200_vpin vs full | 57, 57.5 | 3 | 3 | 1 | 1 | 1, 1 | -5.8% to +4.2% |

### synth_history (n=60)

| arm | rep 1 | rep 2 | mean acc | 95% CI (bootstrap) | per-task agreement | stale (mean) | ambiguous (mean) | memory chars |
|---|---|---|---|---|---|---|---|---|
| full | 55 | 52 | 89.2% | 83% to 94% | 49/60 | 6.5/60 | 0/60 | 970 |
| notes300 | 10 | 7 | 14.2% | 8% to 22% | 49/60 | 13.5/60 | 2/60 | 277 |
| notes1200 | 3 | 4 | 5.8% | 2% to 12% | 57/60 | 12/60 | 1/60 | 394 |
| pin | 11 | 8 | 15.8% | 8% to 24% | 51/60 | 8.5/60 | 3.5/60 | 799 |
| vpin | 55 | 58 | 94.2% | 89% to 98% | 55/60 | 3/60 | 0/60 | 1,831 |
| vpin_canon | 56 | 56 | 93.3% | 88% to 98% | 54/60 | 2/60 | 0.5/60 | 1,895 |
| n1200_vpin | 57 | 58 | 95.8% | 92% to 99% | 55/60 | 1/60 | 0.5/60 | 2,011 |

| A vs B | mean correct A, B | tasks A higher | tasks B higher | sign test p | Holm p (7 tests) | McNemar p rep 1, rep 2 | mean diff 95% CI |
|---|---|---|---|---|---|---|---|
| vpin_canon vs pin | 56, 9.5 | 54 | 1 | 3.11e-15 | 1.87e-14 | 6.82e-13, 7.11e-15 | +67.5% to +86.7% |
| vpin vs pin | 56.5, 9.5 | 54 | 0 | 1.11e-16 | 7.77e-16 | 1.14e-13, 1.78e-15 | +69.2% to +86.7% |
| vpin_canon vs vpin | 56, 56.5 | 2 | 3 | 1 | 1 | 1, 0.625 | -4.2% to +2.5% |
| vpin_canon vs notes1200 | 56, 3.5 | 58 | 2 | 3.18e-15 | 1.87e-14 | 3.11e-15, 4.43e-14 | +77.5% to +95.0% |
| vpin_canon vs full | 56, 53.5 | 11 | 6 | 0.332 | 0.665 | 1, 0.388 | -3.3% to +11.7% |
| n1200_vpin vs notes1200 | 57.5, 3.5 | 57 | 2 | 6.14e-15 | 2.46e-14 | 1.58e-15, 1.58e-15 | +80.8% to +96.7% |
| n1200_vpin vs full | 57.5, 53.5 | 12 | 5 | 0.143 | 0.43 | 0.727, 0.109 | +0.0% to +14.2% |

synth_std cur (n=30), mean correct over 2 reps: full 29, notes300 21, notes1200 22.5, pin 29, vpin 29, vpin_canon 27.5, n1200_vpin 27.5

synth_std hist (n=30), mean correct over 2 reps: full 27, notes300 3.5, notes1200 2.5, pin 6, vpin 28, vpin_canon 28, n1200_vpin 28

synth_hard cur (n=30), mean correct over 2 reps: full 28.5, notes300 21.5, notes1200 23, pin 29, vpin 29.5, vpin_canon 29.5, n1200_vpin 29.5

synth_hard hist (n=30), mean correct over 2 reps: full 26.5, notes300 5, notes1200 1, pin 3.5, vpin 28.5, vpin_canon 28, n1200_vpin 29.5

Verdict breakdown, synthetic, both reps summed (correct / stale / ambiguous / wrong):

| arm | current: allergy | current: other | history: allergy | history: other |
|---|---|---|---|---|
| full | 23 / 0 / 5 / 0 (2x14) | 92 / 0 / 0 / 0 (2x46) | 28 / 0 / 0 / 0 (2x14) | 79 / 13 / 0 / 0 (2x46) |
| notes300 | 2 / 4 / 21 / 1 (2x14) | 83 / 0 / 2 / 7 (2x46) | 8 / 6 / 4 / 10 (2x14) | 9 / 21 / 0 / 62 (2x46) |
| notes1200 | 1 / 0 / 27 / 0 (2x14) | 90 / 0 / 2 / 0 (2x46) | 7 / 6 / 2 / 13 (2x14) | 0 / 18 / 0 / 74 (2x46) |
| pin | 25 / 2 / 1 / 0 (2x14) | 91 / 0 / 0 / 1 (2x46) | 11 / 5 / 7 / 5 (2x14) | 8 / 12 / 0 / 72 (2x46) |
| vpin | 26 / 2 / 0 / 0 (2x14) | 91 / 0 / 0 / 1 (2x46) | 23 / 4 / 0 / 1 (2x14) | 90 / 2 / 0 / 0 (2x46) |
| vpin_canon | 22 / 3 / 3 / 0 (2x14) | 92 / 0 / 0 / 0 (2x46) | 22 / 2 / 1 / 3 (2x14) | 90 / 2 / 0 / 0 (2x46) |
| n1200_vpin | 22 / 3 / 3 / 0 (2x14) | 92 / 0 / 0 / 0 (2x46) | 23 / 2 / 1 / 2 (2x14) | 92 / 0 / 0 / 0 (2x46) |

## Stores and orphan keys


### lme

| store | rep | keys | versions | keys with history | audit: tasks with a duplicate group | audit: redundant keys per task | exact: orphaned chains | exact: orphan holds a stale value | exact: queried fact has correct previous version |
|---|---|---|---|---|---|---|---|---|---|
| E4 extractor | 1 | 18.6 | 20.8 | 2.17 | 18/78 | 0.36 | n/a | n/a | n/a |
| E4 extractor | 2 | 18.2 | 20.3 | 2.08 | 19/78 | 0.31 | n/a | n/a | n/a |
| canonical-key extractor | 1 | 16.6 | 18.7 | 2.10 | 11/78 | 0.18 | n/a | n/a | n/a |
| canonical-key extractor | 2 | 17.7 | 19.7 | 1.97 | 14/78 | 0.21 | n/a | n/a | n/a |

### synthetic

| store | rep | keys | versions | keys with history | audit: tasks with a duplicate group | audit: redundant keys per task | exact: orphaned chains | exact: orphan holds a stale value | exact: queried fact has correct previous version |
|---|---|---|---|---|---|---|---|---|---|
| E4 extractor | 1 | 15.2 | 29.0 | 6.98 | n/a | n/a | 11/420 | 11/420 | 56/60 |
| E4 extractor | 2 | 14.9 | 28.3 | 6.92 | n/a | n/a | 13/420 | 13/420 | 58/60 |
| canonical-key extractor | 1 | 15.4 | 29.0 | 6.82 | n/a | n/a | 13/420 | 13/420 | 57/60 |
| canonical-key extractor | 2 | 15.4 | 29.1 | 6.88 | n/a | n/a | 11/420 | 11/420 | 57/60 |

Cost per task (rep 2, all calls fresh; memory building plus the current-value answer call; excludes grading):

| arm | lme: mean input tokens | lme: mean output tokens | lme: calls | synthetic: mean input tokens | synthetic: calls |
|---|---|---|---|---|---|
| full | 6,017 | 47 | 1.0 | 467 | 1.0 |
| notes300 | 6,666 | 235 | 3.0 | 5,502 | 16.0 |
| notes1200 | 6,960 | 538 | 3.0 | 5,761 | 16.0 |
| notes_tm | 7,251 | 834 | 3.0 | n/a | n/a |
| pin | 13,646 | 920 | 5.0 | 12,905 | 31.0 |
| vpin | 13,838 | 917 | 5.0 | 13,176 | 31.0 |
| vpin_canon | 14,108 | 1,128 | 5.0 | 15,524 | 31.0 |
| n1200_vpin | 14,402 | 1,434 | 5.0 | 15,784 | 31.0 |

## Repeat noise

Fraction of (task, question) verdicts that differ between rep 1 and rep 2, per arm and set:

| arm | lme | synthetic current | synthetic history |
|---|---|---|---|
| full | 4/78 | 3/60 | 11/60 |
| notes300 | 14/78 | 9/60 | 11/60 |
| notes1200 | 11/78 | 3/60 | 3/60 |
| notes_tm | 11/78 | n/a | n/a |
| pin | 7/78 | 4/60 | 9/60 |
| vpin | 4/78 | 3/60 | 5/60 |
| vpin_canon | 4/78 | 4/60 | 6/60 |
| n1200_vpin | 3/78 | 4/60 | 5/60 |

## Judge validation

Hand labels on 48 LongMemEval verdicts: agreement 46/48, Cohen's kappa 0.917.
- disagreement: rep 2 89941a94 notes_tm: judge no, hand yes. 
- disagreement: rep 1 f685340e_abs n1200_vpin: judge yes, hand no. 
