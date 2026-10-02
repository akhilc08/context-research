## Confirmatory comparisons (LongMemEval accuracy, Holm over 4)

| test | A, B mean correct | tasks A higher / B higher | test p | Holm p | mean difference, 95% CI | supported |
|---|---|---|---|---|---|---|

Non-inferiority tests use a one-sided sign-flip permutation test with a 3% margin (100,000 resamples); superiority tests use an exact two-sided sign test on per-task means over the two repeats.

## Leaderboards

Cost is per task: memory building plus the current-value answer call, from fresh calls (E14 repeat 2 for copied units). Stale and ambiguous are means over repeats; on LongMemEval they come from E4's four-way judge on the tasks with a wrong-version label. The comparison column is the pre-registered exploratory family (every arm vs notes300, exact sign test, Holm within the table).

### lme_all (n=78)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| vpin_canon | 2 | 94.9% | 90% to 99% | 1.5/71 | 0/71 | 2,344 | 14,108 | 1,128 | 5.0 | 29 / 3 | 1.02e-05 |
| vpin | 2 | 94.9% | 90% to 99% | 2/71 | 0/71 | 2,490 | 13,838 | 917 | 5.0 | 29 / 1 | 2.89e-07 |
| full | 2 | 89.7% | 83% to 96% | 6.5/71 | 1.5/71 | 27,907 | 6,017 | 47 | 1.0 | 26 / 4 | 0.000178 |
| notes1200 | 2 | 82.7% | 75% to 90% | 4.5/71 | 0.5/71 | 1,151 | 6,960 | 538 | 3.0 | 24 / 8 | 0.007 |
| pin | 2 | 82.7% | 74% to 90% | 5.5/71 | 0.5/71 | 1,637 | 13,646 | 920 | 5.0 | 18 / 2 | 0.000805 |
| notes300 | 2 | 67.9% | 58% to 77% | 5.5/71 | 0.5/71 | 299 | 6,666 | 235 | 3.0 | base |  |

### lme_history (n=13)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| vpin_canon | 2 | 84.6% | 65% to 100% | 1.5/13 | 0/13 | 2,336 | n/a | n/a | n/a | 11 / 0 | 0.00391 |
| vpin | 2 | 84.6% | 65% to 100% | 1/13 | 0/13 | 2,428 | n/a | n/a | n/a | 12 / 0 | 0.00244 |
| full | 2 | 80.8% | 58% to 100% | 1.5/13 | 0/13 | 25,239 | n/a | n/a | n/a | 11 / 0 | 0.00391 |
| notes1200 | 2 | 53.8% | 31% to 77% | 2/13 | 0.5/13 | 1,099 | n/a | n/a | n/a | 9 / 1 | 0.043 |
| pin | 2 | 19.2% | 8% to 31% | 4/13 | 0.5/13 | 1,573 | n/a | n/a | n/a | 2 / 0 | 0.5 |
| notes300 | 2 | 11.5% | 0% to 23% | 3.5/13 | 0/13 | 299 | n/a | n/a | n/a | base |  |

### lme_current (n=65)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| vpin_canon | 2 | 96.9% | 92% to 100% | 0/58 | 0/58 | 2,345 | n/a | n/a | n/a | 18 / 3 | 0.00525 |
| vpin | 2 | 96.9% | 93% to 100% | 1/58 | 0/58 | 2,503 | n/a | n/a | n/a | 17 / 1 | 0.000725 |
| pin | 2 | 95.4% | 90% to 99% | 1.5/58 | 0/58 | 1,650 | n/a | n/a | n/a | 16 / 2 | 0.00525 |
| full | 2 | 91.5% | 85% to 97% | 5/58 | 1.5/58 | 28,440 | n/a | n/a | n/a | 15 / 4 | 0.0384 |
| notes1200 | 2 | 88.5% | 82% to 95% | 2.5/58 | 0/58 | 1,161 | n/a | n/a | n/a | 15 / 7 | 0.134 |
| notes300 | 2 | 79.2% | 70% to 88% | 2/58 | 0.5/58 | 298 | n/a | n/a | n/a | base |  |

### synth_current (n=60)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| vpin | 2 | 97.5% | 94% to 100% | 1/60 | 0/60 | 1,831 | 13,176 | 2,161 | 31.0 | 22 / 1 | 2.86e-05 |
| recipe | 2 | 96.7% | 92% to 100% | 1/60 | 1/60 | 3,696 | 24,255 | 4,592 | 46.0 | 21 / 0 | 8.58e-06 |
| r_nopin | 2 | 96.7% | 93% to 99% | 1/60 | 1/60 | 2,477 | 19,445 | 4,441 | 31.0 | 21 / 0 | 8.58e-06 |
| pin | 2 | 96.7% | 93% to 99% | 1/60 | 0.5/60 | 746 | 12,905 | 2,164 | 31.0 | 22 / 1 | 2.86e-05 |
| full | 2 | 95.8% | 92% to 99% | 0/60 | 2.5/60 | 970 | 467 | 17 | 1.0 | 21 / 0 | 8.58e-06 |
| vpin_canon | 2 | 95.0% | 90% to 99% | 1.5/60 | 1.5/60 | 1,895 | 15,524 | 2,424 | 31.0 | 20 / 0 | 1.14e-05 |
| r_novblock | 2 | 89.2% | 82% to 96% | 0.5/60 | 6/60 | 2,079 | 14,233 | 3,769 | 31.0 | 17 / 1 | 0.000435 |
| minimal | 2 | 81.7% | 72% to 90% | 1.5/60 | 9.5/60 | 1,495 | 5,843 | 1,608 | 16.0 | 11 / 0 | 0.00195 |
| notes1200 | 2 | 75.8% | 65% to 86% | 0/60 | 14.5/60 | 394 | 5,761 | 1,568 | 16.0 | 8 / 3 | 0.227 |
| notes300 | 2 | 70.8% | 60% to 81% | 2/60 | 11.5/60 | 277 | 5,502 | 1,605 | 16.0 | base |  |

### synth_history (n=60)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| minimal | 2 | 97.5% | 94% to 100% | 1.5/60 | 0/60 | 1,495 | n/a | n/a | n/a | 57 / 0 | 1.25e-16 |
| recipe | 2 | 97.5% | 94% to 100% | 1/60 | 0.5/60 | 3,696 | n/a | n/a | n/a | 57 / 1 | 2.87e-15 |
| r_novblock | 2 | 96.7% | 92% to 100% | 2/60 | 0/60 | 2,079 | n/a | n/a | n/a | 57 / 1 | 2.87e-15 |
| r_nopin | 2 | 95.8% | 91% to 99% | 1.5/60 | 0.5/60 | 2,477 | n/a | n/a | n/a | 57 / 1 | 2.87e-15 |
| vpin | 2 | 94.2% | 89% to 98% | 3/60 | 0/60 | 1,831 | n/a | n/a | n/a | 57 / 1 | 2.87e-15 |
| vpin_canon | 2 | 93.3% | 88% to 98% | 2/60 | 0.5/60 | 1,895 | n/a | n/a | n/a | 57 / 1 | 2.87e-15 |
| full | 2 | 89.2% | 83% to 94% | 6.5/60 | 0/60 | 970 | n/a | n/a | n/a | 54 / 0 | 8.88e-16 |
| pin | 2 | 15.8% | 8% to 24% | 8.5/60 | 3.5/60 | 799 | n/a | n/a | n/a | 6 / 6 | 1 |
| notes300 | 2 | 14.2% | 8% to 22% | 13.5/60 | 2/60 | 277 | n/a | n/a | n/a | base |  |
| notes1200 | 2 | 5.8% | 2% to 12% | 12/60 | 1/60 | 394 | n/a | n/a | n/a | 3 / 12 | 0.0703 |

synth_std cur (n=30), mean correct: full 29, notes300 21, notes1200 22.5, vpin_canon 27.5, minimal 23.5, recipe 28.5, r_nopin 28.5, r_novblock 26.5, pin 29, vpin 29

synth_std hist (n=30), mean correct: full 27, notes300 3.5, notes1200 2.5, vpin_canon 28, minimal 28.5, recipe 28.5, r_nopin 28, r_novblock 28.5, pin 6, vpin 28

synth_hard cur (n=30), mean correct: full 28.5, notes300 21.5, notes1200 23, vpin_canon 29.5, minimal 25.5, recipe 29.5, r_nopin 29.5, r_novblock 27, pin 29, vpin 29.5

synth_hard hist (n=30), mean correct: full 26.5, notes300 5, notes1200 1, vpin_canon 28, minimal 30, recipe 30, r_nopin 29.5, r_novblock 29.5, pin 3.5, vpin 28.5

## Secondary comparisons (no correction)


lme_all:

| A vs B | mean A, B | tasks A higher / B higher | sign test p | mean difference, 95% CI |
|---|---|---|---|---|

lme_history:

| A vs B | mean A, B | tasks A higher / B higher | sign test p | mean difference, 95% CI |
|---|---|---|---|---|

synth_current:

| A vs B | mean A, B | tasks A higher / B higher | sign test p | mean difference, 95% CI |
|---|---|---|---|---|
| recipe vs r_nopin | 58, 58 | 2 / 2 | 1 | -3.3% to +3.3% |
| recipe vs r_novblock | 58, 53.5 | 7 / 0 | 0.0156 | +2.5% to +13.3% |
| recipe vs minimal | 58, 49 | 12 / 0 | 0.000488 | +7.5% to +24.2% |
| minimal vs vpin_canon | 49, 57 | 1 / 11 | 0.00635 | -22.5% to -5.0% |
| recipe vs notes1200 | 58, 45.5 | 15 / 0 | 6.1e-05 | +11.7% to +30.8% |
| minimal vs notes1200 | 49, 45.5 | 6 / 0 | 0.0312 | +1.7% to +10.8% |
| recipe vs vpin_canon | 58, 57 | 3 / 1 | 0.625 | -1.7% to +5.0% |
| recipe vs full | 58, 57.5 | 3 / 1 | 0.625 | -4.2% to +5.0% |

synth_history:

| A vs B | mean A, B | tasks A higher / B higher | sign test p | mean difference, 95% CI |
|---|---|---|---|---|
| recipe vs r_nopin | 58.5, 57.5 | 2 / 0 | 0.5 | +0.0% to +4.2% |
| recipe vs r_novblock | 58.5, 58 | 3 / 2 | 1 | -2.5% to +5.0% |
| recipe vs minimal | 58.5, 58.5 | 3 / 3 | 1 | -4.2% to +4.2% |
| minimal vs vpin_canon | 58.5, 56 | 7 / 3 | 0.344 | -1.7% to +10.0% |
| recipe vs notes1200 | 58.5, 3.5 | 58 / 1 | 2.08e-16 | +84.2% to +97.5% |
| minimal vs notes1200 | 58.5, 3.5 | 57 / 0 | 1.39e-17 | +85.0% to +97.5% |
| recipe vs vpin_canon | 58.5, 56 | 5 / 0 | 0.0625 | +0.8% to +8.3% |
| recipe vs full | 58.5, 53.5 | 12 / 3 | 0.0352 | +1.7% to +15.0% |

## Keeper and pin size

- lme: the keeper kept 1709 of 1830 user turns (93%) across both repeats.
- synthetic: the keeper kept 1800 of 1800 user turns (100%) across both repeats.

## Repeat noise (verdicts that differ between repeats)

| arm | lme | synthetic current | synthetic history |
|---|---|---|---|
| full | 4/78 | 3/60 | 11/60 |
| notes300 | 14/78 | 9/60 | 11/60 |
| notes1200 | 11/78 | 3/60 | 3/60 |
| tm | n/a | n/a | n/a |
| vpin_canon | 4/78 | 4/60 | 6/60 |
| minimal | n/a | 4/60 | 3/60 |
| recipe | n/a | 2/60 | 3/60 |
| r_nopin | n/a | 4/60 | 3/60 |
| r_novblock | n/a | 5/60 | 2/60 |
| fifo1200 | n/a | n/a | n/a |
| headtail1200 | n/a | n/a | n/a |
| fifo_tm | n/a | n/a | n/a |
| headtail_tm | n/a | n/a | n/a |
| mask | n/a | n/a | n/a |
| resum | n/a | n/a | n/a |
| struct | n/a | n/a | n/a |
| carry | n/a | n/a | n/a |
| prov300 | n/a | n/a | n/a |
| anchor | n/a | n/a | n/a |
| watch | n/a | n/a | n/a |
| watch_strict | n/a | n/a | n/a |
| watch_self | n/a | n/a | n/a |
| roundtrip | n/a | n/a | n/a |
| repair | n/a | n/a | n/a |
| pin | 7/78 | 4/60 | 9/60 |
| vpin | 4/78 | 3/60 | 5/60 |
| ledger | n/a | n/a | n/a |
| registry | n/a | n/a | n/a |
