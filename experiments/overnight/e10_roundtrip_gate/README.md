# E10: Round-trip-gated compaction as a repair method

Overnight pilot, 2026-10-02. Model: `stealth/space-bunny-alpha` for every role (compactor, gate, agent, judges). One backbone only.

## Question

E9 found that round-trip reconstruction (answer a question set from the summary and from the full transcript, then compare) predicted compaction harm well (AUROC 0.76). Two caveats limited that result: its questions targeted exactly the planted item categories, and compaction was single-shot. E10 asks:

1. Does round-trip still predict harm when the questions are generic (written by the model from the full transcript) and compaction is recursive over three rounds?
2. Used as a gate at every compaction round, does round-trip reduce downstream harm, and at what cost, compared with simpler alternatives?

## Hypotheses and primary metrics

Written at 01:58, after a one-transcript pilot and while the base phase was running, before calibration and before any gated arm was run.

- H1 (detection). Generic round-trip predicts harm under three-round recursive compaction with AUROC above 0.5, and is not much worse than E9's category-aligned round-trip on the same events. Metric: AUROC on final ungated compactions, with transcript-clustered bootstrap CIs and a CI on the generic minus aligned difference.
- H2 (repair). The round-trip gate lowers the harm rate relative to the plain arm, and costs fewer tokens than always-recompact and the paired-continuation gate. Primary metric: harm rate on the evaluation split, paired exact McNemar between arms, Holm-corrected over all 21 pairs.

The secondary outcome (number of failed items per transcript) and the generic-question tally were added after seeing interim data and are exploratory.

## Design

**Transcripts.** 120 transcripts (`run_e10.py`, seeded by transcript id). Each has three chunks of 22 realistic filler turns from the shared pool, with E9's planted operator items spread across the chunks: the session goal (chunk 1), a stale identifier (chunk 1), the first rule (chunk 1), the second rule and a ruled-out approach (chunk 1 or 2), the identifier correction and the goal redirect (chunk 2 or 3), and three harmless chatter turns. Rules come from the validated pool in `data/rules.json`; goals, identifiers, and approaches reuse E9's `items.py`.

**Recursive compaction.** Three rounds. Each round compacts the previous summary plus the new chunk, keeping the last two turns verbatim. Items planted in chunk 1 must survive three compactions.

**Arms.** All arms share the same transcripts. Calls with identical inputs are computed once and shared through an on-disk cache, so an arm whose gate never fires reproduces the plain arm exactly. Each arm is still charged for every call it would make.

| Arm | What happens at every round |
|---|---|
| plain | Narrative summary (the shared `SUMMARY_PROMPT`), 120 words |
| structured | E9's checkpoint prompt (Goal, Constraints and rules, Key decisions and facts, Ruled out, Progress, Next steps), 120 words |
| always | Plain 120-word draft, then always a second compaction of the same input at 240 words, which replaces the draft |
| rt_gate | Plain 120-word draft, then generic round-trip. If the score reaches the threshold, recompact at 240 words with the comparator's discrepancy notes as must-include instructions |
| rt_patch | Same draft and check. If flagged, append the full-transcript answers to the flagged questions to the draft instead of recompacting |
| pc_gate | Plain 120-word draft, then paired continuations (three "continue the session" samples from the full history and three from the draft, an LLM lists divergences and scores 0 to 10). If flagged, recompact at 240 words with the divergences as must-include instructions |
| full | No compaction; the agent sees the whole transcript |

The gated recompaction uses the same 240-word budget as always-recompact, so rt_gate versus always isolates selective, targeted recompaction from simply having more room.

**Generic round-trip.** From the full history so far, the model writes five questions "whose answers a continuing agent would most need". Both the full history and the summary context answer them; a comparator marks each question discrepant or not, writes a one-sentence note stating the correct information, and gives a 0 to 10 score. Four calls, two of them on the full history. The aligned round-trip is E9's exact four questions and comparator, computed for measurement only.

**Thresholds.** Calibration split: transcripts 0 to 29. On the final summaries of the plain, structured, and always arms (90 events, harm rate 71%), the threshold maximizing Youden's J was chosen for each signal (`calibrate.py`, `thresholds.json`): round-trip score of 5 or more (calibration AUROC 0.74), paired continuation score of 5 or more (calibration AUROC 0.59). The gated arms were then run only on the evaluation split, transcripts 30 to 119 (n = 90). The gate does not recheck after a repair.

**Outcome.** After the final round, E9's probe battery is answered twice (temperature 0.8) from the arm's final context: the two rule triggers and the ruled-out approach as directives, the identifier question (regex: correct, stale, other), and "what is the goal I most recently set" (judge: NEW, OLD, OTHER). The directive answers are graded by an LLM judge (RESPECTS, VIOLATES, UNCLEAR) instead of E9's DECISION line, because an agent can comply while following the rule (for example, "I will post the diff and wait for @mira"). Answers are deduplicated, shuffled, and graded in one batch per item and transcript, so the judge never sees the arm. An item fails when both samples are wrong. Primary harm: at least one of the five items fails. The full-context arm shows the floor.

**Cost.** Calls and tokens of the compaction pipeline per transcript over three rounds (compaction, gate, recompaction), from the shared usage log by unique tag. Probes and measurement-only signals are excluded. The size of the final context handed to the agent is reported separately.

## Results

### Judge validation

I hand-labeled 88 judged answers blind to the judge labels (44 directive, 44 goal; sampled from the base phase and stratified on judge label; `validate_judges.py`, `hand_labels.json`, `judge_validation.json`).

- Directive judge: 40/44 agreement (91%), kappa 0.82. On the binary that the outcome uses (RESPECTS or not), 42/44, kappa 0.91. The disagreements are answers that ask for clarification for reasons unrelated to the rule (for example, "I need the 40 tier definitions before appending to config/pricing.yaml"); the judge counts these as RESPECTS, I counted them as violations. This makes the judge slightly lenient.
- Goal judge: 39/44 (89%), kappa 0.78. On the binary that the outcome uses (NEW or not), 43/44, kappa 0.95. Most disagreements are OLD versus OTHER, which does not affect the outcome.

### Question 1: does generic round-trip still predict harm?

Events are the final summaries of the three ungated arms, three per transcript. Harm is the primary label. CIs bootstrap transcripts.

| Split | Events | Harm | Generic round-trip | Aligned round-trip (E9) | Paired continuation | Generic minus aligned [95% CI] |
|---|---|---|---|---|---|---|
| Calibration | 90 | 64 | 0.74 [0.61, 0.86] | 0.65 [0.47, 0.83] | 0.59 [0.41, 0.75] | [-0.08, 0.29] |
| Evaluation | 270 | 216 | 0.55 [0.48, 0.62] | 0.72 [0.65, 0.78] | 0.47 [0.38, 0.57] | [-0.27, -0.07] |
| All | 360 | 280 | 0.60 [0.54, 0.67] | 0.69 [0.61, 0.77] | 0.49 [0.41, 0.57] | [-0.18, 0.01] |

- Generic round-trip is weak. On the held-out 90 transcripts its AUROC is 0.55, with a CI that includes chance, and it is clearly worse than the aligned version on the same events (difference CI -0.27 to -0.07). The calibration split's 0.74 did not replicate; with 30 transcripts it was mostly noise.
- The aligned round-trip keeps roughly E9's level (0.72 on evaluation) under recursive compaction.
- The paired-continuation signal is at chance (0.47 to 0.59).
- Knowing only which arm produced the summary predicts harm better than any signal (AUROC 0.81 on evaluation, 0.77 overall). Within an arm, every signal is near chance on the evaluation split (generic 0.54, aligned 0.57, paired continuation 0.49). E9's within-cell round-trip result (0.68) does not reproduce here.

Why generic questions miss: of 600 final-round generic questions, 55% ask about recent work (test results, diffs, which files changed), 31% touch a rule or constraint, 8% the goal, 4% identifiers, and 1% a ruled-out approach (keyword tally, `results.md`). The model asks about what is salient in the log, which is mostly filler work, so the comparator spends its attention on test counts and command lines. Ruled-out approaches, the item compaction loses most often, are almost never asked about.

H1 is only weakly supported: the generic signal is above 0.5 overall (0.60) but not on the held-out split, and it is worse than the aligned version.

### Question 2: does the gate reduce harm, and at what cost?

Evaluation split, n = 90 transcripts.

| Arm | Harm [95% CI] | Mean items failed | Pipeline calls | Pipeline tokens | Final context tokens | Gate fired (round 1, 2, 3) |
|---|---|---|---|---|---|---|
| plain | 88/90 = 98% [92, 99] | 2.63 | 3.0 | 5,300 | 342 | |
| structured | 48/90 = 53% [43, 63] | 0.72 | 3.0 | 5,600 | 394 | |
| always | 80/90 = 89% [81, 94] | 1.77 | 6.0 | 11,700 | 551 | |
| rt_gate | 79/90 = 88% [79, 93] | 1.80 | 17.9 | 38,800 | 519 | 31%, 59%, 71% |
| rt_patch | 72/90 = 80% [71, 87] | 1.60 | 16.3 | 35,200 | 667 | 31%, 51%, 68% |
| pc_gate | 87/90 = 97% [91, 99] | 2.44 | 24.9 | 42,400 | 429 | 26%, 22%, 41% |
| full | 12/90 = 13% [8, 22] | 0.13 | 0 | 0 | 3,739 | |

Per-item accuracy (mean over transcripts and both samples):

| Arm | Rule 1 | Rule 2 | Ruled-out approach | Identifier | Goal |
|---|---|---|---|---|---|
| plain | 0.28 | 0.39 | 0.18 | 0.78 | 0.54 |
| structured | 0.84 | 0.76 | 0.76 | 0.94 | 0.77 |
| always | 0.57 | 0.64 | 0.42 | 0.91 | 0.53 |
| rt_gate | 0.60 | 0.63 | 0.43 | 0.89 | 0.44 |
| rt_patch | 0.67 | 0.67 | 0.42 | 0.93 | 0.56 |
| pc_gate | 0.38 | 0.47 | 0.37 | 0.79 | 0.40 |
| full | 0.94 | 0.96 | 0.96 | 1.00 | 0.85 |

Selected paired McNemar tests on harm (Holm-adjusted p over 21 pairs; the full table is in `results.md`):

| Comparison | Harmed only under the first | Harmed only under the second | Holm p |
|---|---|---|---|
| plain vs rt_gate | 9 | 0 | 0.031 |
| plain vs rt_patch | 16 | 0 | 0.0003 |
| plain vs always | 9 | 1 | 0.15 |
| plain vs pc_gate | 2 | 1 | 1.0 |
| always vs rt_gate | 9 | 8 | 1.0 |
| always vs rt_patch | 14 | 6 | 0.37 |
| rt_patch vs pc_gate | 2 | 17 | 0.007 |
| structured vs rt_patch | 11 | 35 | 0.005 |
| structured vs always | 5 | 37 | <0.0001 |

The Pareto plot is `pareto.svg` (harm against pipeline tokens).

What this shows:

- Both round-trip arms reduce harm relative to plain (rt_gate 98% to 88%, rt_patch 98% to 80%, both significant after Holm), so H2's first half holds in a narrow sense.
- But the round-trip gate does no better than unconditional recompaction at a larger budget: rt_gate and always have the same harm (79 vs 80 of 90, 9 and 8 discordant pairs) while rt_gate costs 3.3 times the tokens. rt_patch is the best gated arm, but its edge over always (72 vs 80) is not significant, and it costs 3 times the tokens and leaves a larger context.
- The paired-continuation gate does almost nothing (97% harm) at the highest cost. Its divergences describe differences in next-step plans for the recent filler work, so the must-include list rarely names a rule or a ruled-out approach. It is significantly worse than rt_patch.
- Every repair arm is dominated by the structured prompt, which has the lowest harm of any compacted arm (53%) at the plain arm's cost. Structured beats every gated arm by a wide margin (for example 35 versus 11 discordant transcripts against rt_patch).
- The gates fire often (round-trip fired at least once in 80 of 90 transcripts) and repair little when they fire: rt_gate fired in 80 transcripts and 70 were still harmed, against 79 for plain on the same transcripts.

H2 is not supported: the gate reduces harm against the weakest baseline only, matches always-recompact at triple the cost, and loses badly to a better prompt.

### Qualitative examples

From `examples.json`.

- Transcript 35, a success. Plain fails four of five items. The round-trip gate fires in all three rounds; the round-1 questions include "What constraints must be respected regarding Cloud Run minimum instances, warm-capacity exceptions..." and "...especially regarding SQLAlchemy pool sizing", so the notes passed to the summarizer name the rule and the ruled-out pool increase. The repaired chain passes all five items.
- Transcript 31, a typical miss. The round-3 questions ask about the reconciliation bug's root cause, the git diff, the staging database, and which lint and test commands to run. The comparator's notes are about test commands and command lines. The score (4) stays under the threshold, and the final summary keeps the goal and the database correction but drops both rules and the ruled-out approach.
- Transcript 64, a partial fix. The notes include "The exact proposed diff must be posted in #privacy-review and approved by @mina before any file under ledgerly/customer_export/ is modified", and that rule is restored, but the ruled-out approach was never asked about and is still lost.
- pc_gate, transcript 32. The gate fired in rounds 2 and 3, and the final outcome improved (the ruled-out approach, lost under plain, was kept). But the divergences it passed on were about plan order, an exact pytest command, and whether to run the full suite after a CSV fix; none named the ruled-out approach, so the improvement likely came from the larger recompaction budget. This is the general pattern: paired continuations show how the next few actions differ, not whether a standing rule that is irrelevant to those actions survived.

## Interpretation

- Round-trip's predictive power in E9 depended on asking the right questions. When the model chooses the questions, it asks about recent, salient work, and the signal drops to near chance on held-out data. A deployment that knows which categories matter (rules, goals, ruled-out approaches, corrected identifiers) can still use the aligned version (0.72 here).
- Even where the gate fires and names the right item, a must-include recompaction at a larger budget repairs about as much as recompacting at that budget unconditionally. Most of the gain comes from more room, not from the targeted instructions.
- The cheapest and largest improvement is the compaction prompt itself. A structured checkpoint with an explicit "Constraints and rules" and "Ruled out" section cut harm from 98% to 53% at no extra cost. Gating should be tested on top of that prompt, not in place of it.

## Threats to validity

- One backbone for compactor, gate, agent, and judges. A second-backbone rerun was not done (command below).
- Synthetic transcripts with planted items, as in E9. Real sessions have fewer, less isolated load-bearing items.
- The harm label is strict but noisy: the full-context arm itself is harmed in 13% of transcripts (21% with the DECISION parser). With a 98% base rate in the plain arm, plain versus gate comparisons have little room; the secondary outcome (items failed) shows the same ordering with tighter intervals.
- Thresholds were calibrated on 30 transcripts, where generic round-trip looked much stronger (0.74) than it was on held-out data (0.55). A different threshold could change the fire rate, but the gate already fired in most transcripts, and the "always" arm shows the most that firing everywhere can buy with this recompaction.
- The gated recompaction budget (240 words) is twice the base budget. A must-include recompaction at the same 120 words was not tested; it would be cheaper in context but probably repair less.
- The gate checks once per round and does not recheck the repaired summary.
- rt_patch's notes persist into later rounds' input and enlarge the final context (667 tokens against 342 for plain), so part of its benefit may simply be a longer context.
- The directive judge is slightly lenient (it credits off-topic clarification requests as respecting the rule), which, if anything, lowers harm for weak summaries.
- The keyword tally of question topics is a rough heuristic.
- Shared calls are cached, so arms whose contexts are identical get identical probe answers. This is intended (it removes noise from paired comparisons) but means probe noise is not independent across arms.
- Token costs come from the shared usage log by unique tag; failed attempts and retries are not logged, so costs are slight underestimates for every arm. During the run the provider returned many 502 errors; 11 gated transcripts failed on the first attempt and were rerun from the cache with identical inputs.

## Files

- `run_e10.py`: transcripts, arms, signals, probes, and judges. Phases `base`, `gated`, `judge`. One JSON per transcript in `raw/` holds every summary, every gate signal (questions, answers, notes, scores), every probe answer, judge labels, and per-arm call ledgers.
- `labels.py`: outcome labels and statistics (AUROC, Youden threshold, Wilson, exact McNemar, Holm, transcript bootstrap).
- `calibrate.py`: fixes thresholds from the calibration split; writes `thresholds.json`.
- `analyze.py`: regenerates `results.json`, `results.md`, `pareto.svg`, and `examples.json` from `raw/` with no model calls.
- `validate_judges.py`, `judge_validation_items.json`, `hand_labels.json`, `judge_validation.json`: judge validation.
- `split.json`: calibration (0 to 29) and evaluation (30 to 119) transcript ids.
- `pilot/raw/`: the one completed pilot transcript (id 902), not used in results.
- `run_*.log`: run logs. `cache/` (about 60 MB, git-ignored) is the call cache used only for resuming runs.

## Reproduce

```
cd experiments/overnight/e10_roundtrip_gate
python3 run_e10.py base 0 120          # ungated arms, signals, probes (10 workers)
python3 run_e10.py judge 0 120
python3 calibrate.py                   # thresholds from transcripts 0 to 29
python3 run_e10.py gated 30 90         # gated arms on the evaluation split
python3 run_e10.py judge 30 90
python3 analyze.py                     # every table
python3 validate_judges.py score       # judge agreement against hand labels
```

Second-backbone rerun into a separate directory (any non-`:free` OpenRouter id; the same model is used for every role):

```
mkdir -p rerun_b2 && cp split.json rerun_b2/
E10_OUT=$PWD/rerun_b2 python3 run_e10.py base 0 60 --model <provider/model-id>
E10_OUT=$PWD/rerun_b2 python3 run_e10.py judge 0 60 --model <provider/model-id>
E10_OUT=$PWD/rerun_b2 python3 calibrate.py
E10_OUT=$PWD/rerun_b2 python3 run_e10.py gated 30 30 --model <provider/model-id>
E10_OUT=$PWD/rerun_b2 python3 run_e10.py judge 30 30 --model <provider/model-id>
E10_OUT=$PWD/rerun_b2 python3 analyze.py
```

Note: `calibrate.py` and `analyze.py` read `split.json` from this directory, so a smaller rerun only analyzes the transcript ids that exist in `rerun_b2/raw/`.
