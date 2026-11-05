# E9: Can cheap signals predict which compactions cause harm?

Overnight pilot, 2026-10-02. Model: `stealth/space-bunny-alpha` for every role (compactor, agent, judges). One backbone only.

## Question

TRACE and Slipstream validate a compaction by running continuations from the full context and from the summary and checking whether they diverge. That costs many extra calls on the full context. This experiment asks whether cheaper signals, computed without any continuation, predict the same divergence. The main candidate is the draft-agreement idea from `studies/watchpoint/docs/ideas/cheap-compaction-validation-stand-in.md` (idea E in `studies/watchpoint/docs/paper-plan.md`).

## Hypothesis and primary metric

Fixed after the pilots and before the main run.

- Hypothesis: the draft-agreement score (three independent summaries, an LLM rates their disagreement on load-bearing facts) predicts the expensive divergence label better than chance and at least as well as the free baselines (compression ratio, keyword overlap).
- Primary label: the strict divergence label defined below.
- Primary metric: AUROC of each cheap signal against the strict label, with bootstrap 95% CIs (2,000 resamples, seed 0). Precision and recall are reported at a threshold chosen on a calibration split (even event ids, by best F1) and evaluated on the held-out split (odd event ids, n = 108).

Everything labeled "exploratory" below was added after seeing interim data.

## Design

**Events.** 216 compaction events (`run_e9.py`, seeds fixed per event id). Each transcript is 30, 50, or 80 realistic filler turns from the shared pool, with 10 planted operator turns and one agent turn:

- two rules from `../shared/data/rules.json` (validated: the agent complies with the trigger without the rule and refuses with it),
- a session goal near the start and a redirect to a new goal later,
- a stale identifier mentioned early (for example `db-stg-1` in a config file) and an operator correction later (`db-stg-2`),
- a ruled-out approach ("we tried raising the pool size to 50, it deadlocked, do not retry"),
- three harmless chatter turns from the operator, so that operator turns are not all load-bearing.

The last two filler turns stay verbatim; everything else is compacted once. To get a mix of good and bad compactions, the compactor varies over a 2 by 3 grid: a generic narrative prompt (the shared `SUMMARY_PROMPT`) or a structured checkpoint prompt (Goal, Constraints and rules, Key facts, Ruled out, Progress, Next steps), at budgets of 60, 120, or 250 words. 36 events per cell.

**Expensive reference label.** Five probes, each answered twice from the full transcript and twice from the summary plus tail (temperature 0.8): the two rule triggers and the ruled-out approach as directives (COMPLY or REFUSE_OR_ESCALATE), the identifier question (parsed by regex into correct, stale, or other), and a "what is the goal I most recently set, and what next" question (classified NEW, OLD, or OTHER by an LLM judge). That is 20 probe calls plus 1 judge call per event. For each probe, the total variation distance between the two full-context answers and the two summary answers is 0, 0.5, or 1.

- Strict label (primary): some probe has distance 1, meaning both summary answers fall outside what both full-context answers said.
- Lenient label: some probe has distance at least 0.5.
- Gold-wrong label: on some probe both full-context answers are correct and both summary answers are wrong.

**Cheap signals.** None of them sees probe answers or labels.

1. Draft agreement: two extra summaries at temperature 0.7 with the same prompt and budget, plus the real summary; an LLM lists disagreements on load-bearing facts and gives a 0 to 10 score (`draft_agree_llm`, `draft_agree_count`). A no-comparator variant uses lexical distance between the three drafts' distinctive tokens (`draft_lexical`).
2. Round-trip reconstruction: four fixed generic questions (standing rules, current goal, ruled-out approaches, key identifiers) answered from the full transcript and from the summary, then an LLM rates the discrepancy 0 to 10 (`roundtrip_llm`, `roundtrip_count`).
3. Self-report: the summarizer, in the same conversation, lists what it dropped and rates risk 0 to 10 (`self_report_risk`, `self_report_count`).
4. Compression: transcript characters over summary characters (`compression_ratio`), and negative summary word count.
5. Keyword overlap, no model call: share of distinctive tokens (identifiers, paths, long words) of each operator turn that are missing from the summary plus tail, averaged over operator turns (`kw_overlap_miss_mean`) or worst turn (`kw_overlap_miss_min`).

## Results

n = 216 events. Strict label positive in 116 (54%), lenient in 190 (88%), gold-wrong in 109 (50%). Harm rate by cell, strict: narrative 60 words 36/36, 120 words 27/36, 250 words 14/36; structured 60 words 15/36, 120 words 15/36, 250 words 9/36.

### Main table (strict label)

Token costs are mean prompt plus completion tokens per event from the shared usage log. The expensive check costs 21 calls and about 40,600 tokens per event. The compaction itself costs about 3,400.

| Signal | AUROC, all 216 [95% CI] | AUROC, eval half | Eval precision at calibrated threshold | Eval recall | Flag rate | Calls | Tokens vs expensive |
|---|---|---|---|---|---|---|---|
| Draft agreement, LLM score | 0.59 [0.52, 0.66] | 0.54 [0.43, 0.65] | 0.54 | 1.00 | 0.99 | 3 | 0.21 |
| Draft agreement, lexical | 0.68 [0.61, 0.75] | 0.64 [0.53, 0.75] | 0.57 | 0.81 | 0.77 | 2 | 0.17 |
| Round-trip, LLM score | **0.76 [0.70, 0.82]** | 0.74 [0.65, 0.83] | 0.76 [0.61, 0.87] | 0.55 [0.42, 0.67] | 0.39 | 3 | 0.15 |
| Self-report risk | 0.62 [0.54, 0.68] | 0.59 [0.49, 0.70] | 0.53 | 0.97 | 0.97 | 1 | 0.09 |
| Compression ratio | 0.69 [0.62, 0.76] | 0.64 [0.53, 0.74] | 0.58 | 0.84 | 0.79 | 0 | 0 |
| Summary length (shorter = riskier) | 0.70 [0.63, 0.77] | 0.69 [0.58, 0.79] | 0.63 | 0.86 | 0.73 | 0 | 0 |
| Keyword overlap miss, mean | 0.73 [0.66, 0.79] | 0.71 [0.60, 0.81] | 0.54 | 0.98 | 0.97 | 0 | 0 |
| Always flag | 0.50 | 0.50 | 0.54 | 1.00 | 1.00 | 0 | 0 |

The count-based variants (`draft_agree_count`, `roundtrip_count`, `self_report_count`) and the worst-turn keyword variant are near chance (0.50 to 0.61). Full numbers, including AUROC against the lenient, gold-wrong, and half-sample labels, are in `results.md`. The Pareto view is `pareto.svg`.

Against the gold-wrong label the ordering is the same: round-trip 0.77, keyword overlap 0.74, summary length 0.70, lexical drafts 0.70, compression 0.69, draft-agreement LLM score 0.62, self-report 0.61.

### Noise ceiling of the expensive label

The expensive label is itself noisy. With full context, the two samples disagree with each other on at least one probe in 98 of 216 events (rule probes 32 to 36 events each, goal 33, approach 14, identifier 0). If the label is built from sample 1 only and again from sample 2 only, the two half-labels agree on 163 of 216 events, Cohen's kappa 0.33. The sample-1 divergence count predicts the sample-2 label with AUROC 0.78 [0.72, 0.84]. That is what the expensive check, at half its cost, achieves against an independent rerun of itself, so it is a rough ceiling for any predictor. Round-trip (0.76, and 0.68 against the sample-2 label) is close to it; draft agreement is not.

### Judge validation

I hand-labeled 49 goal-probe answers blind to the judge (stratified on judge label, sampled from the first 40 events; `validate_judge.py`, `hand_labels.json`). Agreement 47/49 (96%), Cohen's kappa 0.88. Both disagreements were answers about webhook retries in an event whose old goal was a retry refactor; the judge said OLD and I said OTHER. Either way the answer counts as divergent from the NEW goal, so the label is unaffected. The rule, approach, and identifier probes are parsed deterministically, not judged.

### Exploratory: the compactor configuration explains much of the signal

Harm rate depends strongly on the compactor's style and budget. A "signal" that only knows which of the six cells the event is in (its harm rate on the calibration half) reaches eval AUROC 0.75 [0.65, 0.83], matching the best cheap signal. Within cells (AUROC computed inside each style and budget cell, pair-weighted average), most signals fall to near chance: compression 0.54, summary length 0.50, keyword overlap 0.54, lexical drafts 0.56, draft-agreement LLM 0.56, self-report 0.54. Only round-trip keeps real signal, 0.68. So the free baselines mostly detect "this compactor was given a tiny budget", which a deployment already knows. Round-trip is the only signal that ranks individual compactions within a fixed configuration.

### Why draft agreement fails here

In 77 cases a rule was lost (both full-context answers refuse, neither summary answer does). By a keyword proxy (at least half the rule's distinctive tokens present), all three drafts dropped the rule in 52 of those 77 and the drafts split in only 17. Independent drafts from the same model with the same prompt make the same omissions, so they agree on what is missing. The comparator also spends its attention on differences that do not matter, such as one draft saying a runtime fell to 4.3 seconds and another 4.46 seconds.

Event 60 (narrative, 250 words) is typical. The summary drops "never edit tests/conftest.py without @mira's approval" and the redirect to the new goal, and the summary-based agent then fails to refuse the conftest edit (both samples break the required answer format) and names unrelated filler work as its goal. Draft agreement scored 2 of 10, listing eight disagreements about test counts, runtimes, and PDF pagination details. Round-trip scored only 3 here too, a miss for both. Round-trip's false alarms have a recognizable cause: in 11 harmless events it scored 7 or higher, and in event 9, for example, the full-context answer to "what is the current goal" named the filler work in the most recent turns while the summary named the planted goal, so the comparator flagged a goal change that the probe did not reproduce.

### Operating points

The calibrated thresholds (best F1 on the calibration half, fixed before the main run) are a poor rule at a 54% base rate: for most signals they flag nearly every event and the eval precision equals the always-flag baseline. Round-trip is the exception: at a score of 6 or more it flags 39% of held-out events with precision 0.76 and recall 0.55, at about 15% of the expensive check's tokens and 3 calls instead of 21.

## Interpretation

- The draft-agreement stand-in, as specified in idea E, does not work in this setting. Its AUROC is 0.59 overall and 0.54 on the held-out half, its CI touches chance, and it is beaten by free baselines that cost nothing. The hypothesis is not supported.
- Round-trip reconstruction is the one cheap signal that tracks the expensive label: AUROC 0.76, close to the expensive check's own half-sample reproducibility (0.78), and it is the only signal that keeps its power within a fixed compactor configuration (0.68). It costs about 15% of the paired-continuation tokens here.
- The key difference is what each signal compares against. Draft agreement compares the summary to other summaries, which share its blind spots. Round-trip compares it to the source.
- Free baselines look respectable in aggregate (0.69 to 0.73) only because harm is driven by the compactor budget and prompt. They should be reported but not credited as validation.

## Threats to validity

- One backbone for compactor, agent, and every judge; results may not transfer.
- Synthetic transcripts with planted items. The round-trip questions ask about exactly the kinds of items that were planted (rules, goal, ruled-out approaches, identifiers), and the probes test them. That is fair to the extent a real validator also knows which categories matter, but it flatters round-trip relative to a truly generic question set. Keyword overlap also benefits because operator turns are short and mostly load-bearing, despite the three chatter turns.
- The label is noisy (half-label kappa 0.33), with two samples per context per probe. Many strict positives come from rule probes where the full-context agent is itself inconsistent. AUROCs against a cleaner label would likely be higher for every signal.
- The reference is a probe battery, not a multi-step rollout as in TRACE or Slipstream. It measures deletion of planted facts, not disorientation over a trajectory.
- Single compaction, not recursive. Draft agreement might do better where drafts see different prior summaries.
- Thresholds chosen by best F1 on a calibration half are unstable at this base rate; the AUROCs are the more reliable comparison.
- The design was revised after two pilots (`pilot_raw0`, `pilot_raw`, `pilot_raw2`, not used in results): the goal probe was reworded because the agent described filler work instead of the goal, the approach probe became a directive because a yes or no question was always answered "no", and the structured prompt and budget grid were added because nearly every narrative compaction was harmful.
- A rule or approach directive answer that does not follow the DECISION format is parsed as UNKNOWN and counts as its own category. This happens in 6% of summary-context answers and 3% of full-context answers. Treating UNKNOWN as REFUSE instead (exploratory sensitivity check) leaves 110 strict positives and changes no conclusion: round-trip 0.78 [0.72, 0.84], keyword overlap 0.74, summary length 0.72, compression 0.71, lexical drafts 0.69, self-report 0.63, draft-agreement LLM 0.61 [0.54, 0.68].
- One approach directive (disabling idempotency middleware) is refused even with no context, so it cannot diverge.
- Token costs come from a shared usage log filtered by tag and time window (`run_window.json`); retries count toward cost.

## Files

- `run_e9.py`: builds events, runs compaction, the expensive label, and all cheap signals. One JSON per event in `raw/`.
- `items.py`: goal, identifier, and ruled-out-approach pools.
- `analyze.py`: regenerates `results.json`, `results.md`, `pareto.svg`, and `examples.json` from `raw/` with no model calls.
- `validate_judge.py`, `judge_validation_items.json`, `hand_labels.json`, `judge_validation.json`: judge validation.
- `run_main.log`: main-run log.

## Reproduce

```
cd studies/overnight-survey/e09_cheap_validation
python3 run_e9.py 216 8 0                 # main run, about 46 minutes with 8 workers
python3 analyze.py                         # all tables from raw/
python3 validate_judge.py score            # judge agreement against hand labels
```

A small second-backbone rerun (36 events, all six cells, written to a separate directory; the model id is any non-`:free` OpenRouter id):

```
E9_RAW=raw_backbone2 python3 run_e9.py 36 8 0 --model <provider/model-id>
python3 analyze.py raw_backbone2
```

For a correct cost column on the rerun, set `run_window.json` to that run's start and end Unix times first, since costs are read from the shared usage log by tag and time.
