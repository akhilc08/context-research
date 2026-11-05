# E7: repair compute vs. retention compute at matched token budgets

Overnight pilot for idea B in [`studies/watchpoint/docs/paper-plan.md`](../../watchpoint/docs/paper-plan.md) and [`studies/watchpoint/docs/ideas/repair-vs-retention-compute-crossover.md`](../../watchpoint/docs/ideas/repair-vs-retention-compute-crossover.md). One backbone (`stealth/space-bunny-alpha`), synthetic transcripts, 30 transcripts with 5 rules each.

## Question and hypothesis

After compaction, a team can spend extra tokens in two ways: run repair passes in which the agent re-reads its compacted context and writes out the constraints it must follow, or keep more raw transcript instead. The hypothesis under test:

- **H1 (mechanism).** Repair passes lower violations only for rules whose requirement is still present in the summary (retrieval-type). They do not lower violations for rules the summary dropped (deletion-type). Retention lowers both.
- **H2 (crossover).** Because the share of deletion-type rules grows with compression, repair is the better use of a fixed budget at light compression and retention is better at heavy compression.

**Primary metric:** violation rate, meaning the agent answers COMPLY to an operator request that breaks a rule it was given earlier. Primary comparisons: the repair k=0 vs k=8 change split by rule type (H1), and repair vs retention at matched budget per compression level (H2). These were fixed before any decision data was collected. Analyses marked "exploratory" below were added later.

## Design

- **Transcripts.** 30 transcripts of 100 turns: 95 realistic coding-agent filler turns from `../shared/data/filler_turns.json` and 5 operator rules from `../shared/data/rules.json` (`OPERATOR: <rule>`). The rules sit at random positions in turns 1 to 96, at least 3 turns apart. Each rule has a validated violating trigger. Seed 7.
- **Compaction.** Turns 1 to 96 are summarized in one call at budgets of 400, 200, 100, 50 and 25 words. The last 4 turns stay verbatim. The compacted body averages 4,663 tokens, so these budgets give compression ratios of 7x, 12x, 24x, 47x and 83x.
- **Labels.** For each (summary, rule) pair, a separate judge call (temperature 0) decides whether the summary still states the requirement in actionable form. YES means retrieval-type and NO means deletion-type.
- **Repair arm.** 8 chained passes per summary. Each pass sees the summary, the tail and all earlier passes, and writes a numbered constraint list of up to 150 words, including any constraints that earlier passes missed. The context for k passes is the base context plus the first k pass outputs. k is 0, 1, 2, 4 or 8.
- **Retention arm.** Same summary. The verbatim tail is widened backwards, whole turns at a time, until it uses as many tokens as the first k repair passes added. This is a recency policy: it keeps the most recent raw turns.
- **Token matching (verified).** Tokens are counted as chars/4 for both arms. Retention uses 88% to 90% of the repair budget at k=1 and 99% at k=8 (it is never over budget), so any matching error slightly favours repair. The mean appended tokens at k=8 are 1,932 to 2,058. Real API completion tokens per repair pass averaged 226, close to the chars/4 estimate of about 235.
- **Baselines.**
  - Zero-compaction control: the raw 100 turns.
  - Floor: the raw transcript with the rule turns removed.
  - Pinning: the same summary plus all 5 operator rule turns kept verbatim (about 206 tokens). Pinning was added at the coordinator's request before any decisions were run.
- **Decisions.** The agent sees the context and a request, then answers COMPLY or REFUSE_OR_ESCALATE (`common.decide`, temperature 0.8, one sample per cell).
  - Every context gets each rule's trigger (n=150 per cell).
  - Every context also gets a benign near-miss request for each rule. These requests touch the same area without breaking the rule, and each was validated to get COMPLY at least 2 of 3 times both with and without the rule present. 35 of 42 benign requests passed validation, so the benign n is 128 per cell.
  - Total: 14,456 decisions.
- **Confabulation audit.** A judge reads the true rules, the summary and the 8-pass repair list. It records which true rules the list states and counts constraints that match neither the true rules nor the summary.
- **Statistics.**
  - Wilson 95% CIs on every rate.
  - Paired exact McNemar tests (arms share transcripts and rules), with Fisher tests also reported, and Holm correction across the 10-test family.
  - Cluster bootstrap over transcripts (2,000 resamples) for differences and for the interaction.
  - A split-half cross-validated router: choose the arm per compression level on even transcripts and test on odd ones, then the reverse.

## Results

### Label composition

The retrieval-type share falls with compression, as intended:

| Budget | Compression | Retrieval-type share |
|---|---|---|
| 400 words | 7x | 140/150 = 93% [88, 96] |
| 200 words | 12x | 69% [61, 76] |
| 100 words | 24x | 23% [17, 31] |
| 50 words | 47x | 5% [2, 9] |
| 25 words | 83x | 0/150 |

### Controls

| Context | Violation | Benign false refusal |
|---|---|---|
| Zero-compaction control (5,097 prompt tokens) | 13/148 = 9% [5, 14] | 15/128 = 12% [7, 18] |
| Floor (rules removed) | 133/149 = 89% [83, 93] | 6/128 = 5% [2, 10] |
| Pinning, pooled over levels (about 206 extra tokens) | about 8% (5% to 11% per level) | 5% |

Pinning reaches the uncompacted ceiling at every compression level and at a tenth of the k=8 budget.

### H1: repair helps retrieval-type rules and barely moves deletion-type rules

Pooled over levels, paired, McNemar p with Holm adjustment:

| Arm | Retrieval-type violation | Deletion-type violation |
|---|---|---|
| Repair k=0 | 60/282 = 21% [17, 26] | 359/465 = 77% [73, 81] |
| Repair k=1 | 15% [11, 20] | 73% [69, 77] |
| Repair k=2 | 14% [10, 19] | 72% [67, 75] |
| Repair k=4 | 11% [8, 15] | 70% [65, 74] |
| Repair k=8 | 34/283 = 12% [9, 16] | 341/463 = 74% [69, 77] |
| Retention k=8 | 53/285 = 19% [15, 24] | 244/464 = 53% [48, 57] |

Paired tests behind this table:

- **Repair, k=0 vs k=8, retrieval-type:** 40 violations fixed, 14 newly broken, p = 0.0005 (Holm 0.004).
- **Repair, k=0 vs k=8, deletion-type:** 48 fixed, 31 broken, p = 0.071 (Holm 0.23).
- **Retention k=8 vs repair k=0, deletion-type:** 143 fixed, 29 broken, p = 3e-19 (Holm 3e-18).
- **Retention k=8 vs repair k=0, retrieval-type:** p = 0.37, not significant.

The interaction (drop for retrieval-type minus drop for deletion-type, k=0 to k=8, cluster bootstrap) is:

- Repair: +5.7 points [-0.6, +12.1]. Retrieval-type drop is 9.3 [3.6, 14.9] and deletion-type drop is 3.6 [0.5, 6.9].
- Retention: -21.9 points [-28.7, -14.8]. Retrieval-type drop is 2.7 [-1.1, 6.4] and deletion-type drop is 24.6 [18.3, 31.3].

The direction matches H1, and the repair curve saturates by k=2 to k=4 (k=8 is no better than k=4). But the repair interaction CI just crosses zero, so the result is "repair's effect on deletion-type rules is small and mostly noise", not "exactly zero".

A consensus-label sensitivity check is exploratory. It keeps only the 69 deletion-type cases where both judges say absent. There, repair moves deletion-type violations from 87% to 84% (5 fixed, 3 broken, p = 0.73), while retention moves them from 87% to 54% (p = 2e-5). The small pooled repair effect on deletion-type rules shrinks to nothing on the high-confidence deletion set. This supports the reading that it came from mislabeled retrieval-type rules plus generic caution.

### H2: crossover in compression space

Violation for repair minus violation for retention, at matched budget (negative means repair is better), cluster bootstrap 95% CI:

| Compression | k=1 | k=2 | k=4 | k=8 (about 2k tokens) |
|---|---|---|---|---|
| 7x (400 w) | -4.1 [-12.8, 3.9] | -7.9 [-12.8, -3.7] | -10.0 [-15.9, -4.7] | -5.1 [-10.9, 0.8] |
| 12x (200 w) | -5.8 [-13.3, 1.6] | -4.4 [-11.3, 2.0] | -8.9 [-17.8, 0.5] | -7.3 [-15.3, 1.3] |
| 24x (100 w) | -4.0 [-8.7, 0.7] | -2.6 [-11.6, 6.5] | -0.7 [-8.7, 6.7] | +13.3 [3.3, 22.7] |
| 47x (50 w) | +2.7 [-4.0, 9.3] | +0.7 [-9.3, 10.7] | +1.5 [-7.0, 10.0] | +22.1 [12.1, 32.0] |
| 83x (25 w) | -1.2 [-7.3, 4.9] | +8.7 [1.3, 16.5] | +7.9 [0.0, 16.6] | +29.3 [20.7, 38.0] |

Efficiency at k=8, in violation points removed per 1k extra tokens relative to k=0:

| Compression | Repair | Retention |
|---|---|---|
| 7x | +2.3 | -0.3 |
| 12x | +6.9 | +3.4 |
| 24x | +3.8 | +10.6 |
| 47x | +0.4 | +12.0 |
| 83x | +1.0 | +16.4 |

At small budgets (k=1 or 2), repair has the best per-token efficiency at 12x to 24x, about 25 to 33 points per 1k tokens, because its gain comes almost entirely from the first one or two passes.

**Crossover.** At about a 2k-token budget, the crossover lies between 12x and 24x compression, where the retrieval-type share falls from about 70% to about 25%. With smaller budgets (under 1k tokens), the two arms are mostly within noise below 24x. Retention only pulls ahead at 83x, because a few hundred tokens of recency tail rarely reach back to a rule.

**Router** (split-half cross-validated, k=8): the router picks repair at 7x and 12x and retention at 24x and above, in both folds. Violation rates:

| Policy | Violation |
|---|---|
| Router | 278/746 = 37% [34, 41] |
| Retention-only | 297/749 = 40% [36, 43] |
| Repair-only | 375/746 = 50% [47, 54] |

At k=1 to 4 the router is within 1 to 3 points of the best single arm. Both arms and the router are far worse than pinning (8%) at a tenth of the tokens.

### Why retention works here (exploratory)

Retention is a recency tail, so it helps only when a rule falls inside the widened window. Pooled over retention cells, violation is 7% [5, 9] for rules inside the tail (n=548) and 58% [56, 60] for rules outside it (n=2,441). Deletion-type rules inside the tail drop to 7% [4, 10]. The retention benefit is therefore the mechanical recovery of raw rule text, not a general effect of a longer context.

### Cost

Per-decision prompt tokens are matched by design, within about 25 tokens. Repair also costs a one-time compute bill that retention does not have: about 600 to 1,200 tokens at k=1 and 11,700 to 16,700 tokens at k=8 (input plus output summed over passes, per compacted context).

| Arm | Decision prompt (per decision) | One-time compute |
|---|---|---|
| Repair k=0 | 272 to 861 tokens | none |
| Repair k=8 | 2,200 to 2,870 tokens | 11,700 to 16,700 tokens |
| Retention k=8 | about the same as repair k=8 | none |
| Pinning | k=0 plus 206 tokens | none |
| Uncompacted control | 5,097 tokens | none |

Total spend for this experiment was 18,252 calls, 26.8M input tokens and 1.56M output tokens.

### Confabulation and invented constraints

**Recovery of deleted rules.**

- The 8-pass repair lists stated deletion-type rules only rarely: 50% at 7x (only 10 cases, most of them likely judge false negatives, see below), 19% at 12x, 3% at 24x, 1% at 47x and 0/150 at 83x.
- Of the 48 deletion-type violations that 8 repair passes "fixed", the repair list stated the rule in only 5. The other 43 were generic caution, such as "Please provide the 40 pricing-tier definitions" or "ask an authorized operator to merge". These are refusals with no rule-specific grounding, and they are offset by 31 cases that repair broke.
- We found no case of a repair list reconstructing a specific deleted rule (a person, channel or threshold) from general knowledge.

**Invented constraints.**

- Repair raises false refusals on benign requests from 32/640 = 5% at k=0 to 52/639 = 8% at k=8 (paired McNemar p = 0.007, Holm 0.046). Retention k=8 stays at 6% (p = 0.44).
- Examples of new refusals after repair:
  - "I need confirmation that modifying the protected tests/test_billing.py file is authorized". No such protection was ever stated.
  - Over-applying a real rule's prefix requirement to a benign rename.
- Per list, the audit counts 2.9 constraints at 7x rising to 9.6 at 83x that are not in the true rules or the summary. This count overstates invention because the audit judge did not see the 4 verbatim tail turns. Most flagged items are task-state notes taken from the tail, or echoes of the repair instruction itself ("keep the list under 150 words"). As the summary empties, repair fills the list with procedural filler rather than rules.

### Judge validation

The primary judge was compared with hand labels on 45 stratified pairs (hand-labelled blind to the judge, in `handlabels.json`):

- Agreement was 87%, Cohen's kappa 0.74.
- All 6 disagreements were the judge saying "absent" where the summary does state the rule. One example is the 400-word summary that says "audit-log BigQuery retention must remain at least 365 days".

The deletion-type bucket is therefore contaminated with some retrieval-type cases, which biases toward finding a repair effect on deletion-type rules, the opposite of H1. A second, trigger-framed judge failed validation (kappa 0.18, 16 false "present" calls). It is used only for the high-precision consensus check above.

## Threats to validity

- **One backbone.** A single model, which also served as summarizer, repairer, decider and judge. The rules were validated on this model.
- **Synthetic setting.** Single-shot compaction rather than recursive compaction, and synthetic rules among realistic filler. The retention arm is a pure recency tail. Rule positions are uniform, so retention's value depends on how often rules are recent. A relevance-ranked retention policy could do better or worse.
- **Generic repair prompt.** Repair passes do not see the upcoming request. A trigger-aware "check before acting" repair could behave differently.
- **Label noise.** Judge kappa is 0.74 and errors run toward false "deleted". There is one decision sample per cell (temperature 0.8), so cell-level CIs are wide (n=150 per cell, 7 to 10 points).
- **Fragile crossover location.** The crossover point depends on budget size. It is reported for this summary prompt and this model only.
- **Exploratory analyses.** Pinning was added on request before data collection. The consensus check, the inside/outside-tail split, the confabulation audit counts and the qualitative examples are exploratory.
- **No plot.** matplotlib is not installed in this environment, so all results are tables.

## Interpretation

The prediction holds in direction and roughly in size. Repair passes recover rules still written in the summary, with a saturating curve where most of the gain comes in the first one or two passes. They do almost nothing for rules the summary dropped, and on the high-confidence deletion set the effect is null. When they appear to "recover" a deleted rule, it is generic caution, not reconstruction. Repair also adds a measurable false-refusal cost from invented constraints. Retention fixes deleted rules, but only when the raw rule text falls inside the retained window.

As a result, the better use of a fixed budget flips between about 12x and 24x compression at a 2k-token budget, and a simple compression-threshold router beats either fixed arm slightly. The practical finding that dominates all of this is that pinning the 5 operator rule turns verbatim costs about 206 tokens and matches the uncompacted ceiling at every compression level. That is about 8% violations, against 37% for the best router and 88% for 25-word summaries with repair. For constraint retention specifically, repair versus retention is a second-order choice once rule pinning is available.

## Files and how to regenerate

- `run_e7.py`: all model calls, in stages `benign build compact label label2 repair decide audit`. It resumes from `raw/*.json`. Seeds are fixed: transcripts use seed 7 and decision order uses seed 1.
- `analyze_e7.py`: regenerates every table from the raw files. `python3 analyze_e7.py > analysis_output.md` writes `results.json`. Add `--labels consensus` for the sensitivity check, which writes `analysis_output_consensus.md` and `results_raw_consensus.json`.
- `raw/`: transcripts, summaries, labels (judge 1 and judge 2), repair passes, contexts metadata, all 14,456 decisions with raw model text, benign requests and their validation, audits and logs.
- `handlabels.json`: 45 hand labels for judge validation, with the sample keys in `raw/handlabel_sample.json`.

**Second-backbone rerun.** For a small second-backbone run (10 transcripts, about 5k decisions), use any non-`:free` OpenRouter id. Its raw files go to `raw_<model>/`.

```
cd studies/overnight-survey/e07_repair_retention
python3 run_e7.py --model <provider/model-id> --n 10
python3 analyze_e7.py --raw raw_<provider>_<model-id>
```

The rule pool was validated on the default model, and the benign requests are revalidated on the new model in the `benign` stage.
