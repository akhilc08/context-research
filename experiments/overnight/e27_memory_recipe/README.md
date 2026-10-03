# E27: the combined recipe, and every other memory method, on LongMemEval and Supersede

Status: pre-registration written on 2026-10-02 after a one-task smoke test (one LongMemEval task and one task per synthetic config, written to a scratch directory and excluded from every result) and before any main-run call. Results are added below this section after the run. The pre-registration text is not edited afterwards.

## Pre-registration

### Question

E21 found that a combined compaction recipe beat full context on held-out synthetic coding-agent sessions. Its two load-bearing parts were pinning the operator's turns verbatim and in order, and pinning the active operation. E14 found that a versioned fact block was the best single method on LongMemEval knowledge-update questions. E27 asks whether the recipe carries over to a public memory benchmark, where the "operator" is the user in the conversation and there is no operation in progress. A coordinator update widened the study into a comparison of every compaction or memory method from the overnight studies on the same tasks, repeats, and judge.

### Tasks

The tasks are E14's, unchanged:

| set | n | sessions per task | questions |
|---|---|---|---|
| LongMemEval knowledge-update (`lme`) | 78 | 2 | the dataset's question. E4's regex split marks 13 of them as history questions |
| Supersede synthetic, default config (`synth_std`) | 30 (seeds 0 to 29) | 13 | the current value and the previous value (E14's history question) |
| Supersede synthetic, hard config (`synth_hard`) | 30 (seeds 1000 to 1029) | 17 | same two questions |

A LongMemEval user turn is a `user` message in the raw data (mean 11.7 user turns and 2,837 user characters per task, against 27,660 characters for the whole history). A synthetic session has no roles. It is a short block of statements about people, so each synthetic session counts as one user turn. This makes several arms degenerate on synthetic tasks, as listed below.

### Arms

All memory arms answer with Supersede's answer prompt (`ANSWER_SYSTEM`, "These notes are your entire memory..."). The full-context arm uses E14's full-history prompt. No method sees a question, gold answer, or stale label while it builds memory. The default backbone is `stealth/space-bunny-alpha` at temperature 0 for every role.

**Confirmatory arms**

| arm | what the answering model sees |
|---|---|
| `full` | every session (ceiling). Copied from E14 |
| `notes300` | Supersede's NOTES protocol: rewrite the notes after each session, hard cap 300 characters. Copied from E14 |
| `notes1200` | the same at 1,200 characters. Copied from E14 |
| `vpin_canon` | `notes300` plus E14's versioned fact block from the canonical-key extractor (E14's best single method). Copied from E14 |
| `minimal` | **minimal recipe:** `notes300` plus every user turn, verbatim and in order, under a header saying a later turn supersedes an earlier one about the same fact |
| `recipe` | **recipe:** (1) 1,200-character notes from a structured provenance prompt: user turns are labeled `[S<session>.U<turn>]` in the input, every fact is attributed to the turn where it was stated, assistant-only statements are marked or dropped, and an old value is kept and marked superseded next to the new one; (2) E14's versioned block from the canonical-key extractor; (3) the user turns that state or update a fact, verbatim and in order. A keeper call per session (one call, never sees the question or gold) picks those turns |
| `tm` | token-matched notes control: plain Supersede notes with a cap equal to the recipe's mean memory size on LongMemEval in repeat 1, rounded to 100 characters (LongMemEval only) |
| `r_nopin` | recipe without the pinned user turns |
| `r_novblock` | recipe without the versioned block |

The recipe notes use a 1,200-character cap so that `recipe` vs `notes1200` holds the notes budget fixed and measures what the provenance prompt, versioned block, and turn pin add. E21's recipe parts that have no counterpart here are dropped: the standing-rules list, the revocation strike, and the operation pin with its progress note. The recipe's versioned block reuses E14's canonical extraction (the same call E14 made), so the recipe costs three model calls per session (notes, extraction, keeper) plus the answer.

**Added arms (coordinator update)**

| family | arm | mapping |
|---|---|---|
| Truncation | `fifo1200`, `fifo_tm` | the last 1,200 (or token-matched) characters of the raw history |
| | `headtail1200`, `headtail_tm` | the first half and the last half of that budget, joined by `[...]` |
| Observation masking | `mask` | every user turn verbatim, assistant turns dropped, no notes |
| Re-summarization | `resum` | after each session, 300-character notes written from all raw sessions so far, never from prior notes |
| Notes prompt variants (300 characters) | `struct` | E9 structured checkpoint, headings adapted to user memory: Facts (current values), Recent changes, Plans and goals, Preferences |
| | `carry` | E6 keep-rules clause adapted to facts: "Always carry forward every fact the user has stated, with its latest value, even if it has not come up recently." |
| | `prov300` | E5 provenance clause adapted: the untrusted source is the assistant, so facts are attributed to the user and assistant-only statements are marked "assistant suggested" |
| | `anchor` | E2 anchor prompt adapted: write the most recent value of a changed fact first, as "Now: fact = value" |
| Detect and repair | `watch` | E4's watchpoint, unchanged: its own 300-character notes, a restatement check of each key in E4's newest-value store, and a keyword comparator that patches missing or mismatched keys as `[current]` reminders |
| | `watch_strict` | the same with E4's strict comparator (the value must be present and the restatement may add no other content words) |
| | `watch_self` | naive self-judgment: the same loop, but the model answers YES or NO per fact to "do the notes make its current value clear?" (batched into one JSON call per session, as E1's per-rule check would be too costly per key) and NO patches |
| | `roundtrip` | E9 and E10 round-trip check adapted: after each rewrite, four fixed generic questions about facts, changes, plans, and preferences are answered from the old notes plus the raw session (set R) and from the new notes (set S). A comparator lists discrepancies written as the correct information from R, and these are appended as reminders |
| | `repair` | E7 repair passes adapted to facts: two chained "fact check" passes over the final `notes300` notes, appended at answer time. Like E7, the passes see only the compacted memory |
| Fact stores | `pin` | E4 newest-value pin. Copied from E14 |
| | `vpin` | E14 versioned pin over E4's extraction. Copied from E14 |
| | `ledger` | E17 ledger adapted to facts: one JSON update per user message with facts (current, since, previous values with turn spans), plans, superseded plans, and preferences, rendered with E17's "current and authoritative" frame, next to `notes300` |
| | `registry` | E18's unlabeled registry: every value seen for each key in E4's extraction, in first-seen order with the session where it first appeared, under a neutral header and with no current or superseded marking, next to `notes300` |

Skipped, with reasons: E21's operation pin and in-flight progress note (no operation here); E5's quarantine filter (no untrusted tool output); E19 checkpoint timing (Supersede compacts once per session by design, so there is no trigger to move); E10's gated recompaction (the round-trip arm already patches on disagreement, and E10 found the gate tied always-recompacting). On synthetic tasks `mask` is identical to `full`, so it is not run, and the token-matched arms are not run because notes there never reach even 1,200 characters (E4 measured 325 to 462). `fifo1200` and `headtail1200` will often equal `full` on synthetic tasks, because a whole synthetic history is about 1,000 characters. This is reported, not hidden.

### Repeats

E4 measured 6.8% verdict noise for repeated identical calls, so every confirmatory arm runs twice. Repeats 1 and 2 of the copied arms are E14's repeats 1 and 2 (E14's repeat 1 partly reuses E4). The new arms build their own memory in each repeat. On LongMemEval every arm runs twice. On synthetic tasks the confirmatory arms run twice and the added arms run once (repeat 1), because the added loops cost up to 60 calls per task there and the run shares a 900-calls-per-minute cap. If time allows, repeat 2 of the added synthetic arms is run too, and the tables say which arms have one repeat.

### Grading

- **LongMemEval:** E4's validated yes/no judge (Supersede's prompt, with LongMemEval's abstention variant) and E4's four-way stale judge with E4's wrong-version labels. Verdicts for answers copied from E14 are E14's own verdicts for those exact answers. Every new answer is judged once.
- **Synthetic:** Supersede's exact string grader (correct, stale, ambiguous, wrong).
- **Judge spot check:** at least 40 new LongMemEval verdicts, sampled across new arms with balanced yes and no, labeled by hand from question, gold, and answer without the verdict. Cohen's kappa is reported.

### Hypotheses and confirmatory tests

Primary metric: LongMemEval accuracy, per task averaged over the two repeats (0, 0.5, or 1). One Holm family of four tests:

1. **H1. recipe beats notes1200.** Exact two-sided sign test on per-task means.
2. **H2. recipe is non-inferior to vpin_canon, margin 3 points.** One-sided paired sign-flip permutation test of H0: mean(recipe minus vpin_canon) ≤ -0.03, on per-task differences shifted by +0.03 (100,000 resamples, seed 0).
3. **H3. recipe is non-inferior to full, margin 3 points.** Same test against `full`.
4. **H4. minimal beats notes1200.** Exact two-sided sign test.

Holm-adjusted p < 0.05 counts as support. Each test also reports the paired bootstrap 95% interval of the mean difference.

Secondary, not in the Holm family: the same comparisons on the LongMemEval history and current-value splits and on synthetic current and history questions; the ablations (`recipe` vs `r_nopin`, `recipe` vs `r_novblock`); and `recipe` vs `tm`.

**Pre-registered exploratory leaderboard.** Every other arm vs `notes300` on LongMemEval accuracy, exact sign test on per-task means, Holm-corrected across that family. One leaderboard table per dataset reports accuracy with a bootstrap 95% interval, stale and ambiguous rates, the current vs history split, memory size at answer time, and input tokens and calls per task for building memory plus the answer.

### What would count against the recipe

H2 or H3 failing would mean the extra parts cost accuracy relative to E14's single method or full context. A large gap between `recipe` and `tm` in favor of `tm` would mean the gain is just memory size. The pinned user turns will cost many tokens on LongMemEval (about 2,800 characters per task for all of them), and the tables report that cost honestly.

## Deviations from the pre-registration

- **Repeats.** The plan allowed one repeat for the added arms on synthetic tasks. Throughput was better than expected (the coordinator also raised the concurrency limit from 10 to 25 calls during the run), so every arm in every set ran twice. No arm has a single repeat.
- **Concurrency.** Runs used up to 25 concurrent calls after the coordinator's update. Provider errors stayed low (about 2 to 25 logged errors per 10 minutes against several thousand successful calls), so there was no need to step back to 15.
- Nothing else changed. The confirmatory family, tests, margin, token-matched budget rule, and arm definitions are as written above.

## Results

All numbers come from one backbone (`stealth/space-bunny-alpha`, temperature 0), two repeats per arm. Every table here is a condensed copy of `results/tables.md`, which `analyze.py` regenerates from the raw files.

### Confirmatory comparisons (LongMemEval accuracy, n = 78, Holm over 4)

| test | mean correct (A, B) | tasks A higher / B higher | test p | Holm p | mean difference, 95% CI | supported |
|---|---|---|---|---|---|---|
| H1: recipe beats notes1200 | 77, 64.5 | 19 / 1 | 4.0e-05 | 8.0e-05 | +9.0 to +23.7 points | yes |
| H2: recipe non-inferior to vpin_canon (3-point margin) | 77, 74 | 5 / 0 | 1e-05 | 4e-05 | +0.6 to +7.7 points | yes |
| H3: recipe non-inferior to full (3-point margin) | 77, 70 | 9 / 1 | 1e-05 | 4e-05 | +3.2 to +16.0 points | yes |
| H4: minimal beats notes1200 | 72.5, 64.5 | 15 / 2 | 0.0024 | 0.0024 | +3.2 to +17.9 points | yes |

All four hypotheses are supported. The non-inferiority p values sit at the resolution floor of 100,000 resamples. The recipe also scores above E14's versioned pin and above full context outright, but those were not pre-registered as superiority tests. Uncorrected sign tests give p = 0.06 against `vpin_canon` (5 tasks to 0) and p = 0.02 against `full` (9 to 1).

### LongMemEval leaderboard (n = 78)

Accuracy is the mean of the two repeats. Stale and ambiguous count answers (mean over repeats) among the 71 tasks with an E4 wrong-version label. Memory is the text at answer time. Tokens and calls are per task, for building memory plus the answer call, excluding grading. The last column is the pre-registered exploratory family: every arm vs `notes300`, exact sign test, Holm over 27 tests.

| arm | accuracy | 95% CI | history (n=13) | current (n=65) | stale | memory chars | input tokens | output tokens | calls | vs notes300 (higher / lower, Holm p) |
|---|---|---|---|---|---|---|---|---|---|---|
| **recipe** | **98.7%** | 97 to 100 | 100% | 98.5% | 0 | 6,251 | 17,397 | 1,804 | 7 | 31 / 1, 4e-07 |
| r_nopin | 96.8% | 93 to 99 | 88.5% | 98.5% | 2 | 3,195 | 14,736 | 1,517 | 5 | 30 / 1, 7e-07 |
| r_novblock | 95.5% | 91 to 99 | 96.2% | 95.4% | 2.5 | 4,206 | 9,955 | 904 | 5 | 29 / 2, 1e-05 |
| vpin_canon | 94.9% | 90 to 99 | 84.6% | 96.9% | 1.5 | 2,344 | 14,108 | 1,128 | 5 | 29 / 3, 5e-05 |
| vpin | 94.9% | 90 to 99 | 84.6% | 96.9% | 2 | 2,490 | 13,838 | 917 | 5 | 29 / 1, 1e-06 |
| **minimal** | 92.9% | 87 to 97 | 80.8% | 95.4% | 4.5 | 3,520 | 7,387 | 234 | 3 | 27 / 1, 5e-06 |
| registry | 92.3% | 87 to 97 | 88.5% | 93.1% | 6 | 1,963 | 13,733 | 925 | 5 | 28 / 4, 3e-04 |
| ledger | 91.7% | 86 to 96 | 76.9% | 94.6% | 2 | 1,989 | 17,537 | 6,062 | 14.7 | 28 / 4, 3e-04 |
| full | 89.7% | 83 to 96 | 80.8% | 91.5% | 6.5 | 27,907 | 6,017 | 47 | 1 | 26 / 4, 0.001 |
| mask | 88.5% | 81 to 95 | 76.9% | 90.8% | 4 | 3,170 | 900 | 49 | 1 | 25 / 5, 0.005 |
| tm | 85.9% | 79 to 92 | 65.4% | 90.0% | 5.5 | 3,268 | 7,547 | 1,130 | 3 | 26 / 8, 0.035 |
| notes1200 | 82.7% | 75 to 90 | 53.8% | 88.5% | 4.5 | 1,151 | 6,960 | 538 | 3 | 24 / 8, 0.08 |
| pin | 82.7% | 74 to 90 | 19.2% | 95.4% | 5.5 | 1,637 | 13,646 | 920 | 5 | 18 / 2, 0.005 |
| watch_strict | 82.1% | 74 to 89 | 34.6% | 91.5% | 8 | 1,611 | 14,643 | 1,507 | 7 | 22 / 7, 0.08 |
| watch_self | 82.1% | 74 to 89 | 42.3% | 90.0% | 4.5 | 1,209 | 14,661 | 1,433 | 7 | 22 / 7, 0.08 |
| watch | 79.5% | 71 to 87 | 26.9% | 90.0% | 7.5 | 1,462 | 14,579 | 1,493 | 7 | 19 / 8, 0.37 |
| roundtrip | 79.5% | 72 to 86 | 61.5% | 83.1% | 10.5 | 1,221 | 15,899 | 2,309 | 9 | 23 / 11, 0.37 |
| prov300 | 76.3% | 69 to 83 | 38.5% | 83.8% | 6 | 298 | 6,761 | 252 | 3 | 17 / 5, 0.14 |
| struct | 73.1% | 64 to 81 | 11.5% | 85.4% | 4.5 | 300 | 6,716 | 278 | 3 | 13 / 9, 1 |
| resum | 71.2% | 63 to 79 | 34.6% | 78.5% | 6 | 298 | 9,531 | 220 | 3 | 18 / 14, 1 |
| anchor | 70.5% | 62 to 79 | 7.7% | 83.1% | 4.5 | 299 | 6,746 | 237 | 3 | 12 / 10, 1 |
| carry | 69.9% | 61 to 79 | 19.2% | 80.0% | 5.5 | 299 | 6,717 | 259 | 3 | 14 / 11, 1 |
| notes300 | 67.9% | 58 to 77 | 11.5% | 79.2% | 5.5 | 299 | 6,666 | 235 | 3 | base |
| repair | 67.9% | 58 to 77 | 19.2% | 77.7% | 4.5 | 1,323 | 7,596 | 523 | 5 | 3 / 3, 1 |
| fifo_tm | 35.3% | 25 to 46 | 11.5% | 40.0% | 3.5 | 6,200 | 1,462 | 41 | 1 | 9 / 36, 0.001 (worse) |
| headtail_tm | 31.4% | 22 to 41 | 42.3% | 29.2% | 23 | 6,207 | 1,497 | 44 | 1 | 9 / 43, 4e-05 (worse) |
| fifo1200 | 14.7% | 7 to 23 | 3.8% | 16.9% | 2 | 1,200 | 436 | 42 | 1 | 5 / 50, 6e-09 (worse) |
| headtail1200 | 10.9% | 4 to 18 | 7.7% | 11.5% | 16.5 | 1,207 | 441 | 48 | 1 | 3 / 54, 1e-11 (worse) |

The input-token column for `full` (6,017) is lower than for most memory arms, because full context reads the history once in a single answer call, while memory arms read each session to build memory and then answer. What memory arms save is context at answer time (the memory column), not total tokens on a two-session task.

### Supersede synthetic tasks (n = 60, both configs pooled, exact grading)

| arm | current value | history (previous value) | ambiguous on current | memory chars | input tokens | calls |
|---|---|---|---|---|---|---|
| ledger | 98.3% | 99.2% | 0.5 | 1,622 | 24,713 | 31 |
| recipe | 96.7% | 97.5% | 1 | 3,696 | 24,255 | 46 |
| minimal | 81.7% | 97.5% | 9.5 | 1,495 | 5,843 | 16 |
| r_nopin | 96.7% | 95.8% | 1 | 2,477 | 19,445 | 31 |
| r_novblock | 89.2% | 96.7% | 6 | 2,079 | 14,233 | 31 |
| registry | 85.8% | 95.8% | 7.5 | 1,229 | 13,043 | 31 |
| vpin | 97.5% | 94.2% | 0 | 1,831 | 13,176 | 31 |
| vpin_canon | 95.0% | 93.3% | 1.5 | 1,895 | 15,524 | 31 |
| headtail1200 | 96.7% | 92.5% | 1.5 | 970 | 466 | 1 |
| full | 95.8% | 89.2% | 2.5 | 970 | 467 | 1 |
| fifo1200 | 96.7% | 88.3% | 1 | 970 | 466 | 1 |
| roundtrip | 70.8% | 44.2% | 11 | 849 | 30,160 | 61 |
| watch_strict | 97.5% | 13.3% | 0 | 416 | 19,855 | 46 |
| pin | 96.7% | 15.8% | 0.5 | 746 | 12,905 | 31 |
| resum | 80.0% | 8.3% | 8 | 269 | 6,700 | 16 |
| anchor | 76.7% | 4.2% | 10.5 | 277 | 6,080 | 16 |
| watch_self | 76.7% | 10.8% | 12 | 325 | 19,774 | 46 |
| notes1200 | 75.8% | 5.8% | 14.5 | 394 | 5,761 | 16 |
| watch | 75.8% | 11.7% | 12.5 | 340 | 19,550 | 46 |
| struct | 73.3% | 16.7% | 12.5 | 299 | 5,948 | 16 |
| notes300 | 70.8% | 14.2% | 11.5 | 277 | 5,502 | 16 |
| repair | 70.0% | 5.0% | 11.5 | 1,075 | 6,432 | 18 |
| carry | 69.2% | 13.3% | 13 | 286 | 5,846 | 16 |
| prov300 | 67.5% | 17.5% | 12.5 | 287 | 6,182 | 16 |

A whole synthetic history is about 970 characters, so `fifo1200` and `headtail1200` hold the full history and equal `full` here. On these tasks `minimal` and the recipe's turn pin also hold the whole history, because each session is one user turn and the keeper kept all 1,800 of them.

### Ablations and the token-matched control (secondary, uncorrected)

| comparison | LongMemEval | LongMemEval history | synthetic current | synthetic history |
|---|---|---|---|---|
| recipe vs r_nopin (drop the turn pin) | 3 / 1 tasks, p = 0.63 | 2 / 0 | 2 / 2 | 2 / 0 |
| recipe vs r_novblock (drop the versioned block) | 5 / 1, p = 0.22 | 1 / 0 | 7 / 0, p = 0.016 | 3 / 2 |
| recipe vs minimal | 6 / 1, p = 0.13 | 3 / 0 | 12 / 0, p = 0.0005 | 3 / 3 |
| recipe vs tm | 16 / 1, p = 0.0003 | 6 / 0, p = 0.03 | n/a | n/a |
| minimal vs vpin_canon | 5 / 6, p = 1 | 2 / 3 | 1 / 11, p = 0.006 | 7 / 3 |

Neither component is individually necessary on LongMemEval. Dropping the turn pin costs 1.9 points and dropping the versioned block costs 3.2 points, neither significant, and each version without one part still scores 95% to 97%. They are partly redundant: both carry old values forward explicitly. On synthetic current-value questions the versioned block matters (7 to 0), because without it the answer model lists every allergy ever stated (see below).

The token-matched notes control did not use its budget. With a 6,200-character cap, the plain notes prompt wrote 3,268 characters on average and hit the cap in only 4 of 156 rewrites. So `tm` is matched on the cap, not on the memory actually used. Even so it sits 12.8 points below the recipe (16 tasks to 1), and it carries about as much text as `minimal` while scoring 7 points lower. The gain is not just memory size.

### Keeper

The keeper kept 1,709 of 1,830 LongMemEval user turns (93%) and every synthetic session. In this benchmark almost every user turn states a personal fact in passing ("I'm planning my fitness schedule... when is my next soccer game with my coworkers?"), so the selective pin is close to pinning everything. On LongMemEval the recipe's pinned-turn block averaged about 3,050 characters per task (the gap between `recipe` and `r_nopin` memory).

### Repeat noise

Verdicts that differ between the two repeats, LongMemEval (of 78): recipe 2, minimal 3, r_nopin 3, r_novblock 3, full 4, vpin and vpin_canon 4, ledger 7, pin 7, registry 8, tm 10, notes1200 11, notes300 14, the watchpoints 14 each, the 300-character prompt variants 15 to 21, roundtrip 20, resum 21. Arms that keep raw or structured text are stable. Arms whose answer depends on one free-text 300-character rewrite flip on 18% to 27% of tasks, which is larger than most differences between those arms.

## What each family showed

- **Pinning raw user text is strong and cheap.** `mask` (every user turn, nothing else, 3,170 characters) reaches 88.5% at 900 input tokens per task, about level with full context (89.7%, not tested) at a ninth of its memory. Adding 300-character notes (`minimal`) reaches 92.9%.
- **Truncation is the worst family.** Keeping the last 1,200 characters keeps only the end of the second session, and the answer model mostly says it does not know (14.7%). Head plus tail is worse (10.9%) and the most stale method on LongMemEval (16.5 of 71), because the head keeps the first session's old value. Even at 6,200 characters, truncation stays near 31% to 35%.
- **Notes-prompt variants barely move the needle.** At 300 characters, the structured, carry-forward, provenance, and anchor prompts all land within 2 to 8 points of plain notes and none survives Holm. The anchor prompt is the worst on history questions (4% synthetic), as designed: it promotes the newest value and drops the old. Re-summarizing from all raw sessions (`resum`) does no better than recursive notes at this budget.
- **Detect-and-repair costs more and fixes only current values.** The watchpoints patched 307 of 312 LongMemEval rounds, so they act as a costly pin (E4 saw the same). They help current values somewhat and do nothing for history. The round-trip check found discrepancies in every one of 312 rounds, and its reminders sometimes injected a wrong value (below). It was the most stale method among the notes-based arms (10.5 of 71) and the most expensive overall (61 calls per synthetic task). E7-style repair passes, which see only the compacted notes, added 1,000 characters of restatement and changed nothing (3 tasks up, 3 down), matching E7's finding that repair cannot recover what compaction deleted.
- **Fact stores need history.** The newest-value pin fails history questions (19% LongMemEval, 16% synthetic). Every store that keeps old values (versioned pin, ledger, unlabeled registry) handles them (77% to 100%). The unlabeled registry is close behind the versioned pin on accuracy but has the most stale answers of any store (6 of 71 on LongMemEval) and 7.5 ambiguous synthetic answers, against 1.5 to 2 and 0 to 1.5 for labeled stores. This is E18's failure mode in milder form: without a "current" label the model sometimes picks or lists an old value. The E17-style ledger is the best synthetic method (98% and 99%) but the costliest store (one call per user message, 6,000 output tokens per LongMemEval task) and ranks only eighth on LongMemEval.

## Qualitative examples

From LongMemEval, gold in brackets:

- `6071bd76`, "did I switch to more water per tablespoon of coffee, or less?" [less]. `vpin_canon` in repeat 1: "more water... from 5 oz to 6 oz". Its canonical extractor had missed the session 2 update (E14 documented this case). The recipe answered "less water per tablespoon: from 6 ounces to 5 ounces", because the user's own turn stating the new ratio was pinned verbatim.
- `0ddfec37`, "How many autographed baseballs have I added in the first three months?" [15]. Every store arm in E14 answered 20, the later total. The recipe answered 15 in both repeats. Its provenance notes kept the superseded value together with its time frame: "added 20 autographed baseballs in the past few months (S2.U1; supersedes: 15 over the past three months, S1.U1)".
- `c4ea545c`, "Do I go to the gym more frequently than I did previously?" [Yes]. `full`: "you haven't specified exactly how often you went previously". The recipe and the versioned arms answered yes from the explicit old and new values.
- `2133c1b5_abs`, the recipe's only miss in repeat 2. The question asks about an apartment in Shinjuku, which the user never mentioned. The recipe answered "3 months. It's in Harajuku, not Shinjuku." The judge required an abstention.
- `a2f3aa27`, "How many followers do I have on Instagram now?" [1300]. The round-trip comparator wrote the reminder "Confirmed follower count is 1,250; being close to 1,300 is only an estimate", and the answer followed it. In `603deb26` and `852ce960` the comparator likewise wrote reminders asserting a specific version of a changed value as "the correct information", and the answer repeated it. A repair loop that trusts its own comparison can overwrite good notes.

From the synthetic tasks: `minimal` answered "pollen, gluten, soy" for "Devin is allergic to ___" [soy]. 22 of its 28 wrong current-value answers across repeats are on the allergy predicate, against 5 for `full`. Supersede writes "Devin is now allergic to soy", which can be read as an added allergy (E4 and E14 flagged this). The 300-character notes in `minimal` list all three, and the pinned turns do not contradict them. The versioned block resolves it, which is why `r_novblock` also loses on these items.

## Judge validation

The judges are E4's (validated there at kappa 0.887 against exact grading, and with 92 hand labels; E14 added 48 more at kappa 0.917). For E27 I drew 48 new LongMemEval verdicts with seed 7 from the 22 arms E14 never judged, 24 judged yes and 24 judged no, and labeled them from question, gold, and answer without seeing the verdict (`make_hand_sample.py`). Agreement was 47 of 48 (Cohen's kappa 0.958). The one disagreement is an abstention item (`6aeb4375_abs`, `minimal`) where the answer noted Italian restaurants were never mentioned and then answered "zero". The judge accepted it and I did not. The labeler is this agent (a Claude model), not a human. Verdicts for answers copied from E14 are E14's verdicts.

## Threats to validity

- **One backbone, which is also the judge.** Self-preference cannot be ruled out, though the hand labels agree with the judge.
- **Only two sessions per LongMemEval task.** Pinning every fact-bearing user turn costs about 3,000 characters here. In a real assistant with hundreds of sessions the pin would grow without bound, and the recipe's memory (6,251 characters, 2.7 times `vpin_canon`) would need its own compaction. The synthetic tasks have 13 to 17 sessions but are tiny (970 characters in total).
- **The keeper was not selective.** It kept 93% of LongMemEval user turns, so this study does not test whether selecting turns beats pinning all of them.
- **The token-matched control under-used its cap** (3,268 of 6,200 characters), so it is matched on the budget, not on actual memory.
- **Recipe notes use a larger budget than `vpin_canon`'s notes** (1,200 vs 300 characters). E14's `n1200_vpin` arm (notes1200 plus the same block) reached 96.8%, so part of the recipe's margin over `vpin_canon` is the notes budget. The recipe's remaining edge over that E14 arm (98.7% vs 96.8%, not tested here) is small.
- **History questions are few** (13 on LongMemEval). The synthetic history questions are E14's construction and ask for the immediately previous value.
- **Adapted prompts.** Every borrowed method was adapted from coding-agent rules or goals to user facts (mappings in the pre-registration). A different adaptation could do better, especially for the round-trip questions and the structured headings.
- **Copied runs.** Repeat 1 of the six copied arms is E14's repeat 1, which itself partly reuses E4's run from earlier the same night. Repeat 2 of those arms is E14's fresh repeat. Every new arm ran fresh in both repeats.

## Interpretation

On LongMemEval knowledge-update questions the combined recipe carries over well. It is the most accurate method tested (98.7%), above notes1200, non-inferior to (and nominally above) both E14's versioned pin and full context, and the most stable across repeats. The minimal version, plain 300-character notes plus every user turn verbatim, reaches 92.9% with less than half the recipe's input tokens and about half its memory. Pinning the user's turns alone, with no notes at all, already reaches full-context accuracy.

The two recipe parts that matter are the same ones E21 found, translated to this setting: keep the user's own words, and keep old values with explicit current-or-superseded labels. Here they overlap, so removing either one costs little on LongMemEval. The versioned block becomes necessary when the source text is ambiguous about replacement (the synthetic allergy predicate). Everything that rewrites memory into a small free-text summary, whatever the prompt, stays far behind and flips between repeats. Detect-and-repair loops cost two to four times as many calls as a store and fail on history. The cost of the recipe is memory size: 6,251 characters on a two-session benchmark, which will not stay bounded on long histories without further work.

## Files

- `e27.py`: driver for all stages (`seed`, `run`, `tmbudget`, `judge`), the memory builders, and the arm definitions. Model calls go through `../orclient.py`.
- `e27lib.py`: every prompt (copied ones marked with their source study) and the pure helpers (versioned store, registry, ledger rendering, E4 comparators).
- `analyze.py`: regenerates `results/tables.md`, `results/summary.json`, and `results/per_task.json`.
- `make_hand_sample.py`, `results/hand_label_sample.json`, `results/hand_labels.json`: judge spot check.
- `results/units/rep{1,2}/<set>/<qid>/`: raw outputs. Notes trajectories, extractions, keeper selections, ledgers, watchpoint and round-trip rounds, every answer (`ans_<arm>_<cur|hist>.json` with memory size), and LongMemEval verdicts (`judge.json`). Files copied from E14 are byte-identical copies of E14's (`notes300`, `notes1200`, `extract`, `extract_canon`, and the answers of `full`, `notes300`, `notes1200`, `pin`, `vpin`, `vpin_canon`); their `judge.json` entries are E14's.
- `results/tm_budget.json`: the token-matched budget and how it was set.
- `results/run_*.log`: run logs. Token use per call is in `../usage.jsonl` under tags `e27|rep<r>|<set>|<qid>|<unit>|<kind>`. E27 made 55,464 tagged calls (37.8M input and 9.0M output tokens), including judging and the smoke test.

## Reproduce

```bash
cd experiments/overnight/e27_memory_recipe
PY=/private/tmp/supersede-venv/bin/python
$PY e27.py --stage seed
$PY e27.py --stage run --arms confirm
$PY e27.py --stage tmbudget
$PY e27.py --stage run --arms tm --sets lme
$PY e27.py --stage run --arms extra
$PY e27.py --stage judge --arms confirm tm extra --sets lme
$PY make_hand_sample.py
$PY analyze.py
```

A second backbone keeps the judge fixed, copies nothing from E14 (it rebuilds notes, extractions, and full-context answers itself), and writes to `results/units_<model>/` with its own usage tags and token-matched budget. ':free' models are refused.

```bash
M=openai/gpt-4.1-mini
$PY e27.py --model $M --stage run --arms reused confirm
$PY e27.py --model $M --stage tmbudget
$PY e27.py --model $M --stage run --arms tm --sets lme
$PY e27.py --model $M --stage run --arms extra
$PY e27.py --model $M --stage judge --arms reused confirm tm extra --sets lme
$PY analyze.py --model $M   # writes results/analysis_openai_gpt_4_1_mini/
```
