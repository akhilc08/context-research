
## lme (n=78)

Tasks with a judge-labeled wrong-version value: 71
| arm | acc | 95% CI | stale | 95% CI | ambiguous (both values) | mean tok in | mean tok out | mean calls |
|---|---|---|---|---|---|---|---|---|
| full | 71/78 = 91.0% | 83% to 96% | 5/71 = 7.0% | 3% to 15% | 4/71 | 6,017 | 48 | 1.0 |
| notes300 | 52/78 = 66.7% | 56% to 76% | 6/71 = 8.5% | 4% to 17% | 1/71 | 6,668 | 234 | 3.0 |
| notes1200 | 68/78 = 87.2% | 78% to 93% | 4/71 = 5.6% | 2% to 14% | 1/71 | 6,967 | 546 | 3.0 |
| pin | 63/78 = 80.8% | 71% to 88% | 5/71 = 7.0% | 3% to 15% | 0/71 | 13,911 | 957 | 6.0 |
| watch | 61/78 = 78.2% | 68% to 86% | 10/71 = 14.1% | 8% to 24% | 0/71 | 14,592 | 1,485 | 7.0 |
| kvonly | 67/78 = 85.9% | 76% to 92% | 3/71 = 4.2% | 1% to 12% | 0/71 | 7,179 | 724 | 3.0 |

| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p (10 tests) | diff 95% CI |
|---|---|---|---|---|---|---|
| notes300 vs full | 52 to 71 | 2 | 21 | 6.6e-05 | 0.00066 | -34.6% to -14.1% |
| notes1200 vs notes300 | 68 to 52 | 18 | 2 | 0.000402 | 0.00362 | +10.3% to +30.8% |
| pin vs notes300 | 63 to 52 | 12 | 1 | 0.00342 | 0.0273 | +6.4% to +23.1% |
| watch vs notes300 | 61 to 52 | 14 | 5 | 0.0636 | 0.344 | +1.3% to +21.8% |
| pin vs watch | 63 to 61 | 5 | 3 | 0.727 | 0.727 | -3.8% to +10.3% |
| pin vs notes1200 | 63 to 68 | 5 | 10 | 0.302 | 0.656 | -15.4% to +2.6% |
| watch vs notes1200 | 61 to 68 | 5 | 12 | 0.143 | 0.574 | -19.2% to +1.3% |
| pin vs full | 63 to 71 | 3 | 11 | 0.0574 | 0.344 | -19.2% to -1.3% |
| watch vs full | 61 to 71 | 3 | 13 | 0.0213 | 0.149 | -23.1% to -2.6% |
| kvonly vs pin | 67 to 63 | 5 | 1 | 0.219 | 0.656 | +0.0% to +11.5% |

Memory at answer time: notes300 298 chars, notes1200 1154 chars; KV store 18.6 facts / 1300 chars; pin memory 1598 chars; watch memory 1482 chars. Watch rounds with any patch: 153/154; keys checked 2291, missing 852, differs 748.

KV store alone answers correctly: 67/78.
pin failures: 15; of these the KV store alone was also wrong on 10.
watch failures: 17; of these the KV store alone was also wrong on 10.

## synth_std (n=60)

| arm | acc | 95% CI | stale | 95% CI | ambiguous (both values) | mean tok in | mean tok out | mean calls |
|---|---|---|---|---|---|---|---|---|
| full | 59/60 = 98.3% | 91% to 100% | 0/60 = 0.0% | 0% to 6% | 1/60 | 427 | 13 | 1.0 |
| notes300 | 42/60 = 70.0% | 57% to 80% | 2/60 = 3.3% | 1% to 11% | 10/60 | 4,643 | 1,124 | 14.0 |
| notes1200 | 46/60 = 76.7% | 65% to 86% | 0/60 = 0.0% | 0% to 6% | 14/60 | 4,775 | 1,083 | 14.0 |
| pin | 57/60 = 95.0% | 86% to 98% | 2/60 = 3.3% | 1% to 11% | 1/60 | 10,992 | 1,631 | 28.0 |
| watch | 45/60 = 75.0% | 63% to 84% | 2/60 = 3.3% | 1% to 11% | 13/60 | 15,917 | 2,829 | 40.0 |
| kvonly | 58/60 = 96.7% | 89% to 99% | 1/60 = 1.7% | 0% to 9% | 1/60 | 6,285 | 505 | 14.0 |

| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p (10 tests) | diff 95% CI |
|---|---|---|---|---|---|---|
| notes300 vs full | 42 to 59 | 0 | 17 | 1.53e-05 | 0.000153 | -40.0% to -18.3% |
| notes1200 vs notes300 | 46 to 42 | 6 | 2 | 0.289 | 1 | -1.7% to +16.7% |
| pin vs notes300 | 57 to 42 | 15 | 0 | 6.1e-05 | 0.000549 | +15.0% to +36.7% |
| watch vs notes300 | 45 to 42 | 6 | 3 | 0.508 | 1 | -5.0% to +15.0% |
| pin vs watch | 57 to 45 | 12 | 0 | 0.000488 | 0.00342 | +10.0% to +30.0% |
| pin vs notes1200 | 57 to 46 | 11 | 0 | 0.000977 | 0.00586 | +8.3% to +28.3% |
| watch vs notes1200 | 45 to 46 | 1 | 2 | 1 | 1 | -8.3% to +3.3% |
| pin vs full | 57 to 59 | 1 | 3 | 0.625 | 1 | -10.0% to +3.3% |
| watch vs full | 45 to 59 | 0 | 14 | 0.000122 | 0.000977 | -35.0% to -13.3% |
| kvonly vs pin | 58 to 57 | 1 | 0 | 1 | 1 | +0.0% to +5.0% |

| stale pair | A only stale | B only stale | McNemar p |
|---|---|---|---|
| notes300 vs full | 2 | 0 | 0.5 |
| pin vs notes300 | 2 | 2 | 1 |
| watch vs notes300 | 1 | 1 | 1 |
| notes1200 vs notes300 | 0 | 2 | 0.5 |

Memory at answer time: notes300 269 chars, notes1200 325 chars; KV store 12.2 facts / 340 chars; pin memory 609 chars; watch memory 287 chars. Watch rounds with any patch: 159/780; keys checked 9449, missing 150, differs 58.

KV store alone answers correctly: 58/60.
Final KV store value for the queried fact (exact grader): {'correct': 56, 'ambiguous': 3, 'wrong': 1}
pin failures: 3; of these the KV store alone was also wrong on 2.
watch failures: 15; of these the KV store alone was also wrong on 2.

## synth_hard (n=60)

| arm | acc | 95% CI | stale | 95% CI | ambiguous (both values) | mean tok in | mean tok out | mean calls |
|---|---|---|---|---|---|---|---|---|
| full | 57/60 = 95.0% | 86% to 98% | 0/60 = 0.0% | 0% to 6% | 3/60 | 508 | 16 | 1.0 |
| notes300 | 42/60 = 70.0% | 57% to 80% | 0/60 = 0.0% | 0% to 6% | 10/60 | 6,355 | 2,063 | 18.0 |
| notes1200 | 47/60 = 78.3% | 66% to 87% | 0/60 = 0.0% | 0% to 6% | 13/60 | 6,734 | 2,011 | 18.0 |
| pin | 57/60 = 95.0% | 86% to 98% | 1/60 = 1.7% | 0% to 9% | 2/60 | 15,419 | 2,720 | 36.0 |
| watch | 48/60 = 80.0% | 68% to 88% | 1/60 = 1.7% | 0% to 9% | 11/60 | 23,405 | 5,620 | 52.0 |
| kvonly | 58/60 = 96.7% | 89% to 99% | 1/60 = 1.7% | 0% to 9% | 1/60 | 8,982 | 656 | 18.0 |

| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p (10 tests) | diff 95% CI |
|---|---|---|---|---|---|---|
| notes300 vs full | 42 to 57 | 0 | 15 | 6.1e-05 | 0.00061 | -36.7% to -15.0% |
| notes1200 vs notes300 | 47 to 42 | 6 | 1 | 0.125 | 0.547 | +0.0% to +16.7% |
| pin vs notes300 | 57 to 42 | 15 | 0 | 6.1e-05 | 0.00061 | +15.0% to +36.7% |
| watch vs notes300 | 48 to 42 | 8 | 2 | 0.109 | 0.547 | +0.0% to +20.0% |
| pin vs watch | 57 to 48 | 9 | 0 | 0.00391 | 0.0273 | +6.7% to +25.0% |
| pin vs notes1200 | 57 to 47 | 10 | 0 | 0.00195 | 0.0156 | +8.3% to +26.7% |
| watch vs notes1200 | 48 to 47 | 2 | 1 | 1 | 1 | -3.3% to +6.7% |
| pin vs full | 57 to 57 | 2 | 2 | 1 | 1 | -6.7% to +6.7% |
| watch vs full | 48 to 57 | 0 | 9 | 0.00391 | 0.0273 | -25.0% to -6.7% |
| kvonly vs pin | 58 to 57 | 1 | 0 | 1 | 1 | +0.0% to +5.0% |

| stale pair | A only stale | B only stale | McNemar p |
|---|---|---|---|
| notes300 vs full | 0 | 0 | 1 |
| pin vs notes300 | 1 | 0 | 1 |
| watch vs notes300 | 1 | 0 | 1 |
| notes1200 vs notes300 | 0 | 0 | 1 |

Memory at answer time: notes300 288 chars, notes1200 462 chars; KV store 18.2 facts / 495 chars; pin memory 783 chars; watch memory 397 chars. Watch rounds with any patch: 584/1020; keys checked 18478, missing 1132, differs 583.

KV store alone answers correctly: 58/60.
Final KV store value for the queried fact (exact grader): {'correct': 57, 'ambiguous': 2, 'wrong': 1}
pin failures: 3; of these the KV store alone was also wrong on 2.
watch failures: 12; of these the KV store alone was also wrong on 2.

## Exploratory: LongMemEval split by whether the question asks about an older value

History questions (regex on the question, abstention items excluded): n=13; others: n=65.

| arm | history acc | 95% CI | other acc | 95% CI |
|---|---|---|---|---|
| full | 11/13 | 58% to 96% | 60/65 | 83% to 97% |
| notes300 | 1/13 | 1% to 33% | 51/65 | 67% to 87% |
| notes1200 | 9/13 | 42% to 87% | 59/65 | 81% to 96% |
| pin | 1/13 | 1% to 33% | 62/65 | 87% to 98% |
| watch | 3/13 | 8% to 50% | 58/65 | 79% to 95% |
| kvonly | 4/13 | 13% to 58% | 63/65 | 89% to 99% |
| watch_strict | 7/13 | 29% to 77% | 59/65 | 81% to 96% |
| pin_dd | 4/13 | 13% to 58% | 64/65 | 92% to 100% |
| watch_dd | 3/13 | 8% to 50% | 59/65 | 81% to 96% |
| kvonly_dd | 5/13 | 18% to 64% | 63/65 | 89% to 99% |
- other: pin vs notes300: 12 vs 1 discordant, McNemar p=0.00342 (uncorrected, exploratory)
- history: pin vs notes300: 0 vs 0 discordant, McNemar p=1 (uncorrected, exploratory)
- other: pin vs full: 3 vs 1 discordant, McNemar p=0.625 (uncorrected, exploratory)
- history: pin vs full: 0 vs 10 discordant, McNemar p=0.00195 (uncorrected, exploratory)
- other: notes1200 vs pin: 2 vs 5 discordant, McNemar p=0.453 (uncorrected, exploratory)
- history: notes1200 vs pin: 8 vs 0 discordant, McNemar p=0.00781 (uncorrected, exploratory)

## Exploratory: synthetic tasks (both configs pooled) split by queried predicate

| arm | allergy: correct / stale / ambiguous / wrong | other predicates: correct / stale / ambiguous / wrong |
|---|---|---|
| full | 23 / 0 / 4 / 0 (n=27) | 93 / 0 / 0 / 0 (n=93) |
| notes300 | 3 / 1 / 20 / 3 (n=27) | 81 / 1 / 0 / 11 (n=93) |
| notes1200 | 0 / 0 / 27 / 0 (n=27) | 93 / 0 / 0 / 0 (n=93) |
| pin | 21 / 3 / 3 / 0 (n=27) | 93 / 0 / 0 / 0 (n=93) |
| watch | 3 / 2 / 22 / 0 (n=27) | 90 / 1 / 2 / 0 (n=93) |
| kvonly | 23 / 2 / 2 / 0 (n=27) | 93 / 0 / 0 / 0 (n=93) |
| watch_strict | 23 / 3 / 1 / 0 (n=27) | 93 / 0 / 0 / 0 (n=93) |

## Exploratory follow-ups (decided after seeing the main results)


### lme (n=78)

| arm | acc | 95% CI | stale | ambiguous | mean tok in | mean tok out | mean calls | mean memory chars |
|---|---|---|---|---|---|---|---|---|
| watch_strict | 66/78 = 84.6% | 75% to 91% | 7/71 | 0/71 | 14,655 | 1,496 | 7.0 | 1619 |
| pin_dd | 68/78 = 87.2% | 78% to 93% | 4/71 | 0/71 | 13,909 | 956 | 6.0 | nan |
| watch_dd | 62/78 = 79.5% | 69% to 87% | 9/71 | 0/71 | 14,579 | 1,491 | 7.0 | nan |
| kvonly_dd | 68/78 = 87.2% | 78% to 93% | 3/71 | 0/71 | 7,178 | 722 | 3.0 | nan |

watch_strict rounds with any patch: 154/154; keys patched 1924/2291.

| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p (7 tests) | diff 95% CI |
|---|---|---|---|---|---|---|
| watch_strict vs watch | 66 to 61 | 7 | 2 | 0.18 | 0.898 | -1.3% to +14.1% |
| watch_strict vs pin | 66 to 63 | 7 | 4 | 0.549 | 1 | -3.8% to +11.5% |
| watch_strict vs notes300 | 66 to 52 | 17 | 3 | 0.00258 | 0.018 | +7.7% to +28.2% |
| pin_dd vs pin | 68 to 63 | 5 | 0 | 0.0625 | 0.375 | +1.3% to +12.8% |
| watch_dd vs watch | 62 to 61 | 5 | 4 | 1 | 1 | -6.4% to +9.0% |
| watch_dd vs pin | 62 to 63 | 4 | 5 | 1 | 1 | -9.0% to +6.4% |
| kvonly_dd vs kvonly | 68 to 67 | 2 | 1 | 1 | 1 | -2.6% to +6.4% |

### synth_std (n=60)

| arm | acc | 95% CI | stale | ambiguous | mean tok in | mean tok out | mean calls | mean memory chars |
|---|---|---|---|---|---|---|---|---|
| watch_strict | 57/60 = 95.0% | 86% to 98% | 3/60 | 0/60 | 16,107 | 2,881 | 40.0 | 353 |

watch_strict rounds with any patch: 503/780; keys patched 1266/9449.

| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p (3 tests) | diff 95% CI |
|---|---|---|---|---|---|---|
| watch_strict vs watch | 57 to 45 | 12 | 0 | 0.000488 | 0.000977 | +10.0% to +30.0% |
| watch_strict vs pin | 57 to 57 | 0 | 0 | 1 | 1 | +0.0% to +0.0% |
| watch_strict vs notes300 | 57 to 42 | 15 | 0 | 6.1e-05 | 0.000183 | +15.0% to +36.7% |

### synth_hard (n=60)

| arm | acc | 95% CI | stale | ambiguous | mean tok in | mean tok out | mean calls | mean memory chars |
|---|---|---|---|---|---|---|---|---|
| watch_strict | 59/60 = 98.3% | 91% to 100% | 0/60 | 1/60 | 23,685 | 5,438 | 52.0 | 441 |

watch_strict rounds with any patch: 878/1020; keys patched 3690/18478.

| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p (3 tests) | diff 95% CI |
|---|---|---|---|---|---|---|
| watch_strict vs watch | 59 to 48 | 11 | 0 | 0.000977 | 0.00195 | +10.0% to +28.3% |
| watch_strict vs pin | 59 to 57 | 2 | 0 | 0.5 | 0.5 | +0.0% to +8.3% |
| watch_strict vs notes300 | 59 to 42 | 17 | 0 | 1.53e-05 | 4.58e-05 | +16.7% to +40.0% |

## Judge validation

Synthetic (exact grader as reference): agreement 701/720 = 97.4%; judge yes & grader not correct: 16; judge no & grader correct: 3
LongMemEval, 59 tasks with short golds (3 words or fewer, not abstention), x 6 arms: judge vs number-normalized string containment agreement 323/354 = 91.2%.
Judge vs Supersede's unmodified string grader on the same set: 292/354 = 82.5%.
Cohen's kappa: synthetic 0.887; LongMemEval short-gold string check 0.709.
Hand labels (stratified sample of 48 LongMemEval answers, 24 judge-yes and 24 judge-no, seed 7): agreement 48/48, Cohen's kappa 1.000.
Four-way stale judge vs hand labels (44 answers: 20 judged stale, 12 wrong, 8 correct, 4 ambiguous; seed 11): exact 4-way agreement 41/44; stale-vs-not agreement 44/44, Cohen's kappa 1.000.
Disagreements with the string check (qid, arm, gold, answer, judge):
- 852ce960 notes1200 gold='$400,000' judge=no ans='The amount noted for your Wells Fargo pre-approval was **$350,000**. A later reference mentioned **$400,000**, but that amount wasn’t confirmed.'
- 07741c44 full gold='under my bed' judge=yes ans='You initially kept your old sneakers stored under your bed.'
- 2698e78f notes300 gold='every week' judge=yes ans='You see Dr. Smith weekly.'
- 2698e78f notes1200 gold='every week' judge=yes ans='You see Dr. Smith weekly.'
- 2698e78f watch gold='every week' judge=yes ans='You see Dr. Smith weekly.'
- e493bb7c full gold='in my bedroom' judge=yes ans='“Ethereal Dreams” by Emma Taylor is currently hanging above your bed in the bedroom.'
- e493bb7c notes300 gold='in my bedroom' judge=yes ans='“Ethereal Dreams” by Emma Taylor is hanging above the bed in the user’s bedroom.'
- e493bb7c notes1200 gold='in my bedroom' judge=yes ans='“Ethereal Dreams” by Emma Taylor is currently hanging above the bed in the bedroom.'
- e493bb7c pin gold='in my bedroom' judge=yes ans='“Ethereal Dreams” by Emma Taylor is hanging above the bed in the bedroom.'
- e493bb7c watch gold='in my bedroom' judge=yes ans='“Ethereal Dreams” by Emma Taylor is hanging above the bed in the bedroom.'
- e493bb7c kvonly gold='in my bedroom' judge=yes ans='“Ethereal Dreams” by Emma Taylor is hanging above the bed in the bedroom.'
- 0e4e4c46 notes300 gold='132 points' judge=yes ans='Your current personal best in Ticket to Ride is **132**.'
- 59524333 full gold='6:00 pm' judge=no ans='You usually go to the gym at **7:00 PM on Mondays, Wednesdays, and Fridays**. (In one later conversation, you mentioned 6:00 PM, but your original routine was 7'
- 59524333 notes300 gold='6:00 pm' judge=yes ans='You usually go to the gym at **6 PM on Monday, Wednesday, and Friday**.'
- eace081b notes1200 gold='Oahu' judge=yes ans='You’re planning to stay on Oʻahu, Hawaii.'
- cc5ded98 notes300 gold='about two hours' judge=yes ans='You dedicate **2 hours each day** to coding exercises.'
- cf22b7bf notes300 gold='10 pounds' judge=yes ans='You’ve lost **10 lb (about 4.5 kg)** since you started going to the gym consistently.'
- cf22b7bf notes1200 gold='10 pounds' judge=yes ans='You’ve lost **10 lb** over the past **3 months** since attending the gym consistently.'
- cf22b7bf watch gold='10 pounds' judge=yes ans='You’ve lost **10 lb (about 4.5 kg)** since becoming consistent at the gym.'
- cf22b7bf kvonly gold='10 pounds' judge=no ans='I don’t have an exact amount recorded. You’ve set a goal to lose **10 pounds in 3 months**, and your progress is described as **slow but steady**.'
- a2f3aa27 notes300 gold='1300' judge=yes ans='You currently have about **1,300 Instagram followers**.'
- a2f3aa27 notes1200 gold='1300' judge=yes ans='You’re believed to have close to **1,300 Instagram followers** now.'
- a2f3aa27 pin gold='1300' judge=yes ans='You have close to **1,300 Instagram followers** now.'
- a2f3aa27 watch gold='1300' judge=yes ans='You have close to **1,300 Instagram followers** now.'
- a2f3aa27 kvonly gold='1300' judge=yes ans='You have close to 1,300 Instagram followers now.'
- dad224aa full gold='7:30 am' judge=yes ans='You mentioned two different times: initially around **8:30 a.m.**, but later said you like to wake at **7:30 a.m.** on Saturdays.'
- dad224aa notes300 gold='7:30 am' judge=yes ans='You wake up at 7:30 a.m. on Saturday mornings.'
- dad224aa notes1200 gold='7:30 am' judge=yes ans='Around 7:30 a.m.'
- dad224aa pin gold='7:30 am' judge=yes ans='You usually wake up at **7:30 a.m. on Saturday mornings**.'
- dad224aa watch gold='7:30 am' judge=yes ans='You wake up at **7:30 a.m. on Saturday mornings**.'
- dad224aa kvonly gold='7:30 am' judge=yes ans='You usually wake up at **7:30 a.m. on Saturday mornings**.'
