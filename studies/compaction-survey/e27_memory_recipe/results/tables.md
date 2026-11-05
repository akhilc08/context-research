## Confirmatory comparisons (LongMemEval accuracy, Holm over 4)

| test | A, B mean correct | tasks A higher / B higher | test p | Holm p | mean difference, 95% CI | supported |
|---|---|---|---|---|---|---|
| recipe beats notes1200 | 77, 64.5 | 19 / 1 | 4.01e-05 | 8.01e-05 | +9.0% to +23.7% | yes |
| recipe non-inferior to vpin_canon | 77, 74 | 5 / 0 | 1e-05 | 4e-05 | +0.6% to +7.7% | yes |
| recipe non-inferior to full | 77, 70 | 9 / 1 | 1e-05 | 4e-05 | +3.2% to +16.0% | yes |
| minimal beats notes1200 | 72.5, 64.5 | 15 / 2 | 0.00235 | 0.00235 | +3.2% to +17.9% | yes |

Non-inferiority tests use a one-sided sign-flip permutation test with a 3% margin (100,000 resamples); superiority tests use an exact two-sided sign test on per-task means over the two repeats.

## Leaderboards

Cost is per task: memory building plus the current-value answer call, from fresh calls (E14 repeat 2 for copied units). Stale and ambiguous are means over repeats; on LongMemEval they come from E4's four-way judge on the tasks with a wrong-version label. The comparison column is the pre-registered exploratory family (every arm vs notes300, exact sign test, Holm within the table).

### lme_all (n=78)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| recipe | 2 | 98.7% | 97% to 100% | 0/71 | 0/71 | 6,251 | 17,397 | 1,804 | 7.0 | 31 / 1 | 3.84e-07 |
| r_nopin | 2 | 96.8% | 93% to 99% | 2/71 | 0/71 | 3,195 | 14,736 | 1,517 | 5.0 | 30 / 1 | 7.15e-07 |
| r_novblock | 2 | 95.5% | 91% to 99% | 2.5/71 | 0.5/71 | 4,206 | 9,955 | 904 | 5.0 | 29 / 2 | 9.72e-06 |
| vpin_canon | 2 | 94.9% | 90% to 99% | 1.5/71 | 0/71 | 2,344 | 14,108 | 1,128 | 5.0 | 29 / 3 | 4.86e-05 |
| vpin | 2 | 94.9% | 90% to 99% | 2/71 | 0/71 | 2,490 | 13,838 | 917 | 5.0 | 29 / 1 | 1.33e-06 |
| minimal | 2 | 92.9% | 87% to 97% | 4.5/71 | 0.5/71 | 3,520 | 7,387 | 234 | 3.0 | 27 / 1 | 4.75e-06 |
| registry | 2 | 92.3% | 87% to 97% | 6/71 | 0.5/71 | 1,963 | 13,733 | 925 | 5.0 | 28 / 4 | 0.000347 |
| ledger | 2 | 91.7% | 86% to 96% | 2/71 | 0.5/71 | 1,989 | 17,537 | 6,062 | 14.7 | 28 / 4 | 0.000347 |
| full | 2 | 89.7% | 83% to 96% | 6.5/71 | 1.5/71 | 27,907 | 6,017 | 47 | 1.0 | 26 / 4 | 0.000952 |
| mask | 2 | 88.5% | 81% to 95% | 4/71 | 2/71 | 3,170 | 900 | 49 | 1.0 | 25 / 5 | 0.00455 |
| tm | 2 | 85.9% | 79% to 92% | 5.5/71 | 1.5/71 | 3,268 | 7,547 | 1,130 | 3.0 | 26 / 8 | 0.0352 |
| notes1200 | 2 | 82.7% | 75% to 90% | 4.5/71 | 0.5/71 | 1,151 | 6,960 | 538 | 3.0 | 24 / 8 | 0.077 |
| pin | 2 | 82.7% | 74% to 90% | 5.5/71 | 0.5/71 | 1,637 | 13,646 | 920 | 5.0 | 18 / 2 | 0.00523 |
| watch_strict | 2 | 82.1% | 74% to 89% | 8/71 | 0.5/71 | 1,611 | 14,643 | 1,507 | 7.0 | 22 / 7 | 0.0813 |
| watch_self | 2 | 82.1% | 74% to 89% | 4.5/71 | 0.5/71 | 1,209 | 14,661 | 1,433 | 7.0 | 22 / 7 | 0.0813 |
| watch | 2 | 79.5% | 71% to 87% | 7.5/71 | 1.5/71 | 1,462 | 14,579 | 1,493 | 7.0 | 19 / 8 | 0.366 |
| roundtrip | 2 | 79.5% | 72% to 86% | 10.5/71 | 1.5/71 | 1,221 | 15,899 | 2,309 | 9.0 | 23 / 11 | 0.366 |
| prov300 | 2 | 76.3% | 69% to 83% | 6/71 | 0.5/71 | 298 | 6,761 | 252 | 3.0 | 17 / 5 | 0.135 |
| struct | 2 | 73.1% | 64% to 81% | 4.5/71 | 1/71 | 300 | 6,716 | 278 | 3.0 | 13 / 9 | 1 |
| resum | 2 | 71.2% | 63% to 79% | 6/71 | 0/71 | 298 | 9,531 | 220 | 3.0 | 18 / 14 | 1 |
| anchor | 2 | 70.5% | 62% to 79% | 4.5/71 | 1/71 | 299 | 6,746 | 237 | 3.0 | 12 / 10 | 1 |
| carry | 2 | 69.9% | 61% to 79% | 5.5/71 | 0/71 | 299 | 6,717 | 259 | 3.0 | 14 / 11 | 1 |
| notes300 | 2 | 67.9% | 58% to 77% | 5.5/71 | 0.5/71 | 299 | 6,666 | 235 | 3.0 | base |  |
| repair | 2 | 67.9% | 58% to 77% | 4.5/71 | 1.5/71 | 1,323 | 7,596 | 523 | 5.0 | 3 / 3 | 1 |
| fifo_tm | 2 | 35.3% | 25% to 46% | 3.5/71 | 0/71 | 6,200 | 1,462 | 41 | 1.0 | 9 / 36 | 0.000986 |
| headtail_tm | 2 | 31.4% | 22% to 41% | 23/71 | 1.5/71 | 6,207 | 1,497 | 44 | 1.0 | 9 / 43 | 4.08e-05 |
| fifo1200 | 2 | 14.7% | 7% to 23% | 2/71 | 1/71 | 1,200 | 436 | 42 | 1.0 | 5 / 50 | 5.55e-09 |
| headtail1200 | 2 | 10.9% | 4% to 18% | 16.5/71 | 0.5/71 | 1,207 | 441 | 48 | 1.0 | 3 / 54 | 1.16e-11 |

### lme_history (n=13)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| recipe | 2 | 100.0% | 100% to 100% | 0/13 | 0/13 | 6,002 | n/a | n/a | n/a | 13 / 0 | 0.00659 |
| r_novblock | 2 | 96.2% | 88% to 100% | 1/13 | 0/13 | 3,965 | n/a | n/a | n/a | 13 / 0 | 0.00659 |
| r_nopin | 2 | 88.5% | 69% to 100% | 1.5/13 | 0/13 | 3,168 | n/a | n/a | n/a | 12 / 0 | 0.0117 |
| registry | 2 | 88.5% | 77% to 100% | 1/13 | 0/13 | 1,895 | n/a | n/a | n/a | 13 / 0 | 0.00659 |
| vpin_canon | 2 | 84.6% | 65% to 100% | 1.5/13 | 0/13 | 2,336 | n/a | n/a | n/a | 11 / 0 | 0.0215 |
| vpin | 2 | 84.6% | 65% to 100% | 1/13 | 0/13 | 2,428 | n/a | n/a | n/a | 12 / 0 | 0.0117 |
| full | 2 | 80.8% | 58% to 100% | 1.5/13 | 0/13 | 25,239 | n/a | n/a | n/a | 11 / 0 | 0.0215 |
| minimal | 2 | 80.8% | 58% to 100% | 2/13 | 0.5/13 | 3,266 | n/a | n/a | n/a | 11 / 0 | 0.0215 |
| mask | 2 | 76.9% | 54% to 100% | 1/13 | 0/13 | 2,916 | n/a | n/a | n/a | 10 / 1 | 0.188 |
| ledger | 2 | 76.9% | 58% to 92% | 0.5/13 | 0.5/13 | 2,045 | n/a | n/a | n/a | 11 / 0 | 0.0215 |
| tm | 2 | 65.4% | 42% to 88% | 2.5/13 | 0/13 | 2,986 | n/a | n/a | n/a | 10 / 0 | 0.0352 |
| roundtrip | 2 | 61.5% | 42% to 81% | 2/13 | 0.5/13 | 1,256 | n/a | n/a | n/a | 10 / 0 | 0.0352 |
| notes1200 | 2 | 53.8% | 31% to 77% | 2/13 | 0.5/13 | 1,099 | n/a | n/a | n/a | 9 / 1 | 0.279 |
| headtail_tm | 2 | 42.3% | 15% to 69% | 3/13 | 0/13 | 6,207 | n/a | n/a | n/a | 5 / 1 | 1 |
| watch_self | 2 | 42.3% | 23% to 62% | 2/13 | 0/13 | 1,099 | n/a | n/a | n/a | 7 / 0 | 0.234 |
| prov300 | 2 | 38.5% | 23% to 54% | 3.5/13 | 0/13 | 298 | n/a | n/a | n/a | 7 / 0 | 0.234 |
| resum | 2 | 34.6% | 15% to 58% | 3.5/13 | 0/13 | 297 | n/a | n/a | n/a | 5 / 0 | 0.688 |
| watch_strict | 2 | 34.6% | 19% to 50% | 4/13 | 0.5/13 | 1,511 | n/a | n/a | n/a | 6 / 0 | 0.375 |
| watch | 2 | 26.9% | 8% to 46% | 4.5/13 | 0/13 | 1,435 | n/a | n/a | n/a | 4 / 0 | 1 |
| carry | 2 | 19.2% | 8% to 35% | 4/13 | 0/13 | 298 | n/a | n/a | n/a | 4 / 2 | 1 |
| repair | 2 | 19.2% | 8% to 31% | 2.5/13 | 0/13 | 1,370 | n/a | n/a | n/a | 2 / 0 | 1 |
| pin | 2 | 19.2% | 8% to 31% | 4/13 | 0.5/13 | 1,573 | n/a | n/a | n/a | 2 / 0 | 1 |
| notes300 | 2 | 11.5% | 0% to 23% | 3.5/13 | 0/13 | 299 | n/a | n/a | n/a | base |  |
| fifo_tm | 2 | 11.5% | 0% to 31% | 3.5/13 | 0/13 | 6,200 | n/a | n/a | n/a | 2 / 2 | 1 |
| struct | 2 | 11.5% | 0% to 23% | 3.5/13 | 0/13 | 300 | n/a | n/a | n/a | 0 / 0 | 1 |
| headtail1200 | 2 | 7.7% | 0% to 23% | 5/13 | 0/13 | 1,207 | n/a | n/a | n/a | 1 / 3 | 1 |
| anchor | 2 | 7.7% | 0% to 19% | 3/13 | 0/13 | 299 | n/a | n/a | n/a | 1 / 2 | 1 |
| fifo1200 | 2 | 3.8% | 0% to 12% | 2/13 | 0/13 | 1,200 | n/a | n/a | n/a | 1 / 3 | 1 |

### lme_current (n=65)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| recipe | 2 | 98.5% | 96% to 100% | 0/58 | 0/58 | 6,301 | n/a | n/a | n/a | 18 / 1 | 0.00175 |
| r_nopin | 2 | 98.5% | 96% to 100% | 0.5/58 | 0/58 | 3,201 | n/a | n/a | n/a | 18 / 1 | 0.00175 |
| vpin_canon | 2 | 96.9% | 92% to 100% | 0/58 | 0/58 | 2,345 | n/a | n/a | n/a | 18 / 3 | 0.0253 |
| vpin | 2 | 96.9% | 93% to 100% | 1/58 | 0/58 | 2,503 | n/a | n/a | n/a | 17 / 1 | 0.00304 |
| minimal | 2 | 95.4% | 91% to 99% | 2.5/58 | 0/58 | 3,571 | n/a | n/a | n/a | 16 / 1 | 0.00549 |
| r_novblock | 2 | 95.4% | 90% to 99% | 1.5/58 | 0.5/58 | 4,254 | n/a | n/a | n/a | 16 / 2 | 0.0249 |
| pin | 2 | 95.4% | 90% to 99% | 1.5/58 | 0/58 | 1,650 | n/a | n/a | n/a | 16 / 2 | 0.0249 |
| ledger | 2 | 94.6% | 89% to 98% | 1.5/58 | 0/58 | 1,978 | n/a | n/a | n/a | 17 / 4 | 0.115 |
| registry | 2 | 93.1% | 88% to 98% | 5/58 | 0.5/58 | 1,976 | n/a | n/a | n/a | 15 / 4 | 0.288 |
| full | 2 | 91.5% | 85% to 97% | 5/58 | 1.5/58 | 28,440 | n/a | n/a | n/a | 15 / 4 | 0.288 |
| watch_strict | 2 | 91.5% | 85% to 96% | 4/58 | 0/58 | 1,631 | n/a | n/a | n/a | 16 / 7 | 1 |
| mask | 2 | 90.8% | 84% to 97% | 3/58 | 2/58 | 3,221 | n/a | n/a | n/a | 15 / 4 | 0.288 |
| tm | 2 | 90.0% | 83% to 95% | 3/58 | 1.5/58 | 3,324 | n/a | n/a | n/a | 16 / 8 | 1 |
| watch | 2 | 90.0% | 85% to 95% | 3/58 | 1.5/58 | 1,467 | n/a | n/a | n/a | 15 / 8 | 1 |
| watch_self | 2 | 90.0% | 84% to 95% | 2.5/58 | 0.5/58 | 1,231 | n/a | n/a | n/a | 15 / 7 | 1 |
| notes1200 | 2 | 88.5% | 82% to 95% | 2.5/58 | 0/58 | 1,161 | n/a | n/a | n/a | 15 / 7 | 1 |
| struct | 2 | 85.4% | 78% to 92% | 1/58 | 1/58 | 300 | n/a | n/a | n/a | 13 / 9 | 1 |
| prov300 | 2 | 83.8% | 76% to 91% | 2.5/58 | 0.5/58 | 299 | n/a | n/a | n/a | 10 / 5 | 1 |
| anchor | 2 | 83.1% | 76% to 90% | 1.5/58 | 1/58 | 299 | n/a | n/a | n/a | 11 / 8 | 1 |
| roundtrip | 2 | 83.1% | 75% to 90% | 8.5/58 | 1/58 | 1,214 | n/a | n/a | n/a | 13 / 11 | 1 |
| carry | 2 | 80.0% | 72% to 88% | 1.5/58 | 0/58 | 300 | n/a | n/a | n/a | 10 / 9 | 1 |
| notes300 | 2 | 79.2% | 70% to 88% | 2/58 | 0.5/58 | 298 | n/a | n/a | n/a | base |  |
| resum | 2 | 78.5% | 71% to 85% | 2.5/58 | 0/58 | 298 | n/a | n/a | n/a | 13 / 14 | 1 |
| repair | 2 | 77.7% | 68% to 86% | 2/58 | 1.5/58 | 1,313 | n/a | n/a | n/a | 1 / 3 | 1 |
| fifo_tm | 2 | 40.0% | 28% to 51% | 0/58 | 0/58 | 6,200 | n/a | n/a | n/a | 7 / 34 | 0.000608 |
| headtail_tm | 2 | 29.2% | 19% to 39% | 20/58 | 1.5/58 | 6,207 | n/a | n/a | n/a | 4 / 42 | 1.28e-07 |
| fifo1200 | 2 | 16.9% | 8% to 26% | 0/58 | 1/58 | 1,200 | n/a | n/a | n/a | 4 / 47 | 6.28e-09 |
| headtail1200 | 2 | 11.5% | 5% to 19% | 11.5/58 | 0.5/58 | 1,207 | n/a | n/a | n/a | 2 / 51 | 8.59e-12 |

### synth_current (n=60)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ledger | 2 | 98.3% | 96% to 100% | 0.5/60 | 0.5/60 | 1,622 | 24,713 | 14,295 | 31.0 | 22 / 0 | 1.1e-05 |
| watch_strict | 2 | 97.5% | 94% to 100% | 1/60 | 0/60 | 416 | 19,855 | 4,232 | 46.0 | 22 / 1 | 9.16e-05 |
| vpin | 2 | 97.5% | 94% to 100% | 1/60 | 0/60 | 1,831 | 13,176 | 2,161 | 31.0 | 22 / 1 | 9.16e-05 |
| recipe | 2 | 96.7% | 92% to 100% | 1/60 | 1/60 | 3,696 | 24,255 | 4,592 | 46.0 | 21 / 0 | 2.1e-05 |
| r_nopin | 2 | 96.7% | 93% to 99% | 1/60 | 1/60 | 2,477 | 19,445 | 4,441 | 31.0 | 21 / 0 | 2.1e-05 |
| fifo1200 | 2 | 96.7% | 93% to 99% | 1/60 | 1/60 | 970 | 466 | 10 | 1.0 | 21 / 0 | 2.1e-05 |
| headtail1200 | 2 | 96.7% | 92% to 100% | 0.5/60 | 1.5/60 | 970 | 466 | 15 | 1.0 | 21 / 0 | 2.1e-05 |
| pin | 2 | 96.7% | 93% to 99% | 1/60 | 0.5/60 | 746 | 12,905 | 2,164 | 31.0 | 22 / 1 | 9.16e-05 |
| full | 2 | 95.8% | 92% to 99% | 0/60 | 2.5/60 | 970 | 467 | 17 | 1.0 | 21 / 0 | 2.1e-05 |
| vpin_canon | 2 | 95.0% | 90% to 99% | 1.5/60 | 1.5/60 | 1,895 | 15,524 | 2,424 | 31.0 | 20 / 0 | 3.24e-05 |
| r_novblock | 2 | 89.2% | 82% to 96% | 0.5/60 | 6/60 | 2,079 | 14,233 | 3,769 | 31.0 | 17 / 1 | 0.00188 |
| registry | 2 | 85.8% | 78% to 92% | 0.5/60 | 7.5/60 | 1,229 | 13,043 | 2,177 | 31.0 | 16 / 1 | 0.0033 |
| minimal | 2 | 81.7% | 72% to 90% | 1.5/60 | 9.5/60 | 1,495 | 5,843 | 1,608 | 16.0 | 11 / 0 | 0.0107 |
| resum | 2 | 80.0% | 71% to 88% | 1.5/60 | 8/60 | 269 | 6,700 | 2,672 | 16.0 | 13 / 4 | 0.49 |
| anchor | 2 | 76.7% | 67% to 86% | 0.5/60 | 10.5/60 | 277 | 6,080 | 1,669 | 16.0 | 9 / 4 | 1 |
| watch_self | 2 | 76.7% | 67% to 86% | 1/60 | 12/60 | 325 | 19,774 | 4,116 | 46.0 | 9 / 3 | 1 |
| notes1200 | 2 | 75.8% | 65% to 86% | 0/60 | 14.5/60 | 394 | 5,761 | 1,568 | 16.0 | 8 / 3 | 1 |
| watch | 2 | 75.8% | 66% to 85% | 1.5/60 | 12.5/60 | 340 | 19,550 | 4,247 | 46.0 | 12 / 7 | 1 |
| struct | 2 | 73.3% | 62% to 83% | 1/60 | 12.5/60 | 299 | 5,948 | 2,198 | 16.0 | 8 / 6 | 1 |
| notes300 | 2 | 70.8% | 60% to 81% | 2/60 | 11.5/60 | 277 | 5,502 | 1,605 | 16.0 | base |  |
| roundtrip | 2 | 70.8% | 62% to 80% | 2/60 | 11/60 | 849 | 30,160 | 16,172 | 61.0 | 11 / 12 | 1 |
| repair | 2 | 70.0% | 59% to 80% | 2/60 | 11.5/60 | 1,075 | 6,432 | 1,889 | 18.0 | 0 / 1 | 1 |
| carry | 2 | 69.2% | 57% to 80% | 0.5/60 | 13/60 | 286 | 5,846 | 1,639 | 16.0 | 4 / 6 | 1 |
| prov300 | 2 | 67.5% | 57% to 78% | 1/60 | 12.5/60 | 287 | 6,182 | 1,719 | 16.0 | 6 / 11 | 1 |

### synth_history (n=60)

| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs notes300: tasks higher / lower | Holm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ledger | 2 | 99.2% | 98% to 100% | 0.5/60 | 0/60 | 1,622 | n/a | n/a | n/a | 57 / 0 | 3.19e-16 |
| minimal | 2 | 97.5% | 94% to 100% | 1.5/60 | 0/60 | 1,495 | n/a | n/a | n/a | 57 / 0 | 3.19e-16 |
| recipe | 2 | 97.5% | 94% to 100% | 1/60 | 0.5/60 | 3,696 | n/a | n/a | n/a | 57 / 1 | 7.37e-15 |
| r_novblock | 2 | 96.7% | 92% to 100% | 2/60 | 0/60 | 2,079 | n/a | n/a | n/a | 57 / 1 | 7.37e-15 |
| r_nopin | 2 | 95.8% | 91% to 99% | 1.5/60 | 0.5/60 | 2,477 | n/a | n/a | n/a | 57 / 1 | 7.37e-15 |
| registry | 2 | 95.8% | 92% to 99% | 2.5/60 | 0/60 | 1,229 | n/a | n/a | n/a | 56 / 0 | 5.83e-16 |
| vpin | 2 | 94.2% | 89% to 98% | 3/60 | 0/60 | 1,831 | n/a | n/a | n/a | 57 / 1 | 7.37e-15 |
| vpin_canon | 2 | 93.3% | 88% to 98% | 2/60 | 0.5/60 | 1,895 | n/a | n/a | n/a | 57 / 1 | 7.37e-15 |
| headtail1200 | 2 | 92.5% | 87% to 98% | 4.5/60 | 0/60 | 970 | n/a | n/a | n/a | 54 / 0 | 2.22e-15 |
| full | 2 | 89.2% | 83% to 94% | 6.5/60 | 0/60 | 970 | n/a | n/a | n/a | 54 / 0 | 2.22e-15 |
| fifo1200 | 2 | 88.3% | 82% to 94% | 7/60 | 0/60 | 970 | n/a | n/a | n/a | 52 / 2 | 2.14e-12 |
| roundtrip | 2 | 44.2% | 36% to 53% | 10.5/60 | 6/60 | 849 | n/a | n/a | n/a | 37 / 8 | 0.000184 |
| prov300 | 2 | 17.5% | 11% to 26% | 8/60 | 5/60 | 287 | n/a | n/a | n/a | 13 / 10 | 1 |
| struct | 2 | 16.7% | 11% to 23% | 17/60 | 4.5/60 | 299 | n/a | n/a | n/a | 10 / 7 | 1 |
| pin | 2 | 15.8% | 8% to 24% | 8.5/60 | 3.5/60 | 799 | n/a | n/a | n/a | 6 / 6 | 1 |
| notes300 | 2 | 14.2% | 8% to 22% | 13.5/60 | 2/60 | 277 | n/a | n/a | n/a | base |  |
| carry | 2 | 13.3% | 8% to 20% | 8/60 | 3.5/60 | 286 | n/a | n/a | n/a | 10 / 11 | 1 |
| watch_strict | 2 | 13.3% | 7% to 21% | 20.5/60 | 4.5/60 | 416 | n/a | n/a | n/a | 9 / 8 | 1 |
| watch | 2 | 11.7% | 6% to 18% | 17/60 | 3.5/60 | 340 | n/a | n/a | n/a | 7 / 9 | 1 |
| watch_self | 2 | 10.8% | 6% to 17% | 12/60 | 6/60 | 325 | n/a | n/a | n/a | 7 / 10 | 1 |
| resum | 2 | 8.3% | 3% to 13% | 8.5/60 | 3/60 | 269 | n/a | n/a | n/a | 5 / 11 | 1 |
| notes1200 | 2 | 5.8% | 2% to 12% | 12/60 | 1/60 | 394 | n/a | n/a | n/a | 3 / 12 | 0.316 |
| repair | 2 | 5.0% | 2% to 9% | 23/60 | 5/60 | 1,075 | n/a | n/a | n/a | 0 / 9 | 0.043 |
| anchor | 2 | 4.2% | 1% to 8% | 11/60 | 1.5/60 | 277 | n/a | n/a | n/a | 3 / 13 | 0.213 |

synth_std cur (n=30), mean correct: full 29, notes300 21, notes1200 22.5, vpin_canon 27.5, minimal 23.5, recipe 28.5, r_nopin 28.5, r_novblock 26.5, fifo1200 29.5, headtail1200 29, resum 23.5, struct 21.5, carry 20.5, prov300 20, anchor 22, watch 22, watch_strict 29, watch_self 23.5, roundtrip 22.5, repair 21, pin 29, vpin 29, ledger 29.5, registry 25

synth_std hist (n=30), mean correct: full 27, notes300 3.5, notes1200 2.5, vpin_canon 28, minimal 28.5, recipe 28.5, r_nopin 28, r_novblock 28.5, fifo1200 27.5, headtail1200 27, resum 2, struct 5, carry 2.5, prov300 3.5, anchor 0.5, watch 4.5, watch_strict 4, watch_self 3, roundtrip 14.5, repair 2, pin 6, vpin 28, ledger 29.5, registry 28.5

synth_hard cur (n=30), mean correct: full 28.5, notes300 21.5, notes1200 23, vpin_canon 29.5, minimal 25.5, recipe 29.5, r_nopin 29.5, r_novblock 27, fifo1200 28.5, headtail1200 29, resum 24.5, struct 22.5, carry 21, prov300 20.5, anchor 24, watch 23.5, watch_strict 29.5, watch_self 22.5, roundtrip 20, repair 21, pin 29, vpin 29.5, ledger 29.5, registry 26.5

synth_hard hist (n=30), mean correct: full 26.5, notes300 5, notes1200 1, vpin_canon 28, minimal 30, recipe 30, r_nopin 29.5, r_novblock 29.5, fifo1200 25.5, headtail1200 28.5, resum 3, struct 5, carry 5.5, prov300 7, anchor 2, watch 2.5, watch_strict 4, watch_self 3.5, roundtrip 12, repair 1, pin 3.5, vpin 28.5, ledger 30, registry 29

## Secondary comparisons (no correction)


lme_all:

| A vs B | mean A, B | tasks A higher / B higher | sign test p | mean difference, 95% CI |
|---|---|---|---|---|
| recipe vs r_nopin | 77, 75.5 | 3 / 1 | 0.625 | -1.3% to +5.8% |
| recipe vs r_novblock | 77, 74.5 | 5 / 1 | 0.219 | +0.0% to +7.1% |
| recipe vs tm | 77, 67 | 16 / 1 | 0.000275 | +6.4% to +19.9% |
| recipe vs minimal | 77, 72.5 | 6 / 1 | 0.125 | +0.6% to +11.5% |
| minimal vs vpin_canon | 72.5, 74 | 5 / 6 | 1 | -7.7% to +3.8% |
| recipe vs notes1200 | 77, 64.5 | 19 / 1 | 4.01e-05 | +9.0% to +23.7% |
| minimal vs notes1200 | 72.5, 64.5 | 15 / 2 | 0.00235 | +3.2% to +17.9% |
| recipe vs vpin_canon | 77, 74 | 5 / 0 | 0.0625 | +0.6% to +7.7% |
| recipe vs full | 77, 70 | 9 / 1 | 0.0215 | +3.2% to +16.0% |

lme_history:

| A vs B | mean A, B | tasks A higher / B higher | sign test p | mean difference, 95% CI |
|---|---|---|---|---|
| recipe vs r_nopin | 13, 11.5 | 2 / 0 | 0.5 | +0.0% to +30.8% |
| recipe vs r_novblock | 13, 12.5 | 1 / 0 | 1 | +0.0% to +11.5% |
| recipe vs tm | 13, 8.5 | 6 / 0 | 0.0312 | +15.4% to +57.7% |
| recipe vs minimal | 13, 10.5 | 3 / 0 | 0.25 | +0.0% to +42.3% |
| minimal vs vpin_canon | 10.5, 11 | 2 / 3 | 1 | -30.8% to +19.2% |
| recipe vs notes1200 | 13, 7 | 8 / 0 | 0.00781 | +23.1% to +69.2% |
| minimal vs notes1200 | 10.5, 7 | 7 / 2 | 0.18 | -11.5% to +61.5% |
| recipe vs vpin_canon | 13, 11 | 3 / 0 | 0.25 | +0.0% to +34.6% |
| recipe vs full | 13, 10.5 | 3 / 0 | 0.25 | +0.0% to +42.3% |

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
| tm | 10/78 | n/a | n/a |
| vpin_canon | 4/78 | 4/60 | 6/60 |
| minimal | 3/78 | 4/60 | 3/60 |
| recipe | 2/78 | 2/60 | 3/60 |
| r_nopin | 3/78 | 4/60 | 3/60 |
| r_novblock | 3/78 | 5/60 | 2/60 |
| fifo1200 | 1/78 | 4/60 | 10/60 |
| headtail1200 | 1/78 | 2/60 | 5/60 |
| fifo_tm | 3/78 | n/a | n/a |
| headtail_tm | 5/78 | n/a | n/a |
| mask | 4/78 | n/a | n/a |
| resum | 21/78 | 12/60 | 8/60 |
| struct | 16/78 | 6/60 | 18/60 |
| carry | 15/78 | 5/60 | 12/60 |
| prov300 | 21/78 | 13/60 | 13/60 |
| anchor | 16/78 | 10/60 | 5/60 |
| watch | 14/78 | 9/60 | 10/60 |
| watch_strict | 14/78 | 3/60 | 10/60 |
| watch_self | 14/78 | 6/60 | 11/60 |
| roundtrip | 20/78 | 17/60 | 29/60 |
| repair | 16/78 | 10/60 | 6/60 |
| pin | 7/78 | 4/60 | 9/60 |
| vpin | 4/78 | 3/60 | 5/60 |
| ledger | 7/78 | 2/60 | 1/60 |
| registry | 8/78 | 9/60 | 5/60 |

## Judge validation

Hand labels on 48 new LongMemEval verdicts: agreement 47/48, Cohen's kappa 0.958.
- rep 1 6aeb4375_abs minimal: judge yes, hand no. Abstention item: the answer notes Italian restaurants were never mentioned but then answers 'zero' instead of saying the question cannot be answered. I said no.
