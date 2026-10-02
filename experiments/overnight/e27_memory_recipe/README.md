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
