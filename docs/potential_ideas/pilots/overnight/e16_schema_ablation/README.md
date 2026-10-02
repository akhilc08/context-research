# E16: which sections of a compaction schema matter?

Overnight pilot, 2026-10-02. Model: `stealth/space-bunny-alpha` for every role (compactor, agent, judges). One backbone only.

## Question

E6, E9 and E10 all found that changing what the compactor is told to keep beat detection and repair machinery. E10's structured prompt cut harm from 98% to 53% at no extra cost. E16 takes a compaction schema apart to see which sections do the work, whether sections crowd each other out at a small word budget, and what the smallest schema that keeps most of the benefit looks like.

## Hypotheses and primary metric

Written at 05:37, after a one-transcript pilot and before any main result was read.

- Primary metric: harm rate at 3 rounds and a 150-word budget. Harm means at least one of six probe items fails. An item fails when both of its two samples are wrong (E10's definition, plus a plan item). Paired exact McNemar tests are Holm-corrected within a pre-specified family of comparisons per condition.
- H1. The full schema (S1 to S6) has lower harm than plain narrative.
- H2. Each targeted section carries its own item. Dropping S1 hurts the rules, S4 the ruled-out approach, and S5 the plan step. S2 and S3 matter less, because narrative already keeps the goal and identifier fairly often (E10 plain: 0.54 and 0.78).
- H3. At 150 words the six sections crowd each other, so at least one leave-one-out arm does as well as the full schema, and the full schema gains more from 300 words than plain does.
- H4. Pinning operator turns plus the schema is the best compacted arm.

Changes after seeing data, all labelled where they appear:

- The six-item outcome saturated: every unpinned arm failed the plan item in nearly every transcript. I added a five-item harm outcome (E10's five items, no plan item) with its own Holm family. It is secondary.
- The minimal schema arms (`minimal`, `minimal_pin`) were chosen after reading the selection-set results (transcripts 0 to 39). They were then tested on fresh transcripts 40 to 69 alongside the main arms.

## Design

**Transcripts** (`run_e16.py build`, seeded by transcript id). As in E10, each transcript has three chunks of 22 realistic filler turns from the shared pool, with E9's planted items spread across them: the session goal, a stale identifier, two standing rules (from the validated pool in `data/rules.json`), and a ruled-out approach early; the identifier correction and the goal redirect later; three harmless chatter turns. New in E16 is a plan item. Early in the session the operator asks for a separate multi-step procedure (one of E8's 20 generated procedures, 7 to 9 steps, every step's exact command listed). The agent then completes k steps (k from 3 to n-2), and these step turns are spread across all chunks between filler work. The last step finishes before the final verbatim tail, so the tail is always filler. The correct next action is step k+1.

For the 6-round condition, the same items are laid out over six chunks of 22 filler turns (positions scaled by two), so the transcript is twice as long and early items go through six compactions.

**Compaction.** Recursive: each round compacts the previous summary plus the new chunk and keeps the last two turns verbatim. Temperature 0.3, `max_tokens` = 6 times the word budget plus 1,500 (no summary was truncated; see the tables).

**Schema sections** (exact wording in `run_e16.py`):

| Section | Asks for |
|---|---|
| S1 Standing operator rules | every standing rule or constraint, copied verbatim, even if not recently relevant |
| S2 Current objective | the operator's most recent goal, earlier goals noted as superseded |
| S3 Key identifiers and corrections | current hosts, buckets, schemas, files, labels; corrected values marked superseded |
| S4 Ruled-out approaches | each approach tried and ruled out, with the reason |
| S5 Plan and progress | requested procedure steps marked done or pending, exact command of the next step, in-flight commands as status unknown |
| S6 Recent work | short narrative of recent work |

**Arms.** All arms compact the same transcripts.

| Arm | Compaction prompt |
|---|---|
| plain | the shared narrative `SUMMARY_PROMPT` |
| e9_structured | E9 and E10's checkpoint prompt (Goal, Constraints and rules, Key decisions and facts, Ruled out, Progress, Next steps) |
| schema | S1 to S6 |
| loo_Sk | S1 to S6 without Sk (6 arms) |
| add_Sk | Sk plus S6 narrative (5 arms) |
| pin | plain narrative, plus every operator-authored turn kept verbatim in a pinned block outside the summary |
| schema_pin | schema plus the same pinned block |
| minimal, minimal_pin | S1, S2, S4, S6, without and with pinning (chosen after the selection set) |
| full | no compaction; the agent sees the whole transcript (ceiling) |

Every compacted arm gets the same word instruction ("under N words"). The pinned block is extra context on top of that budget; its size is reported.

**Probes.** After the final round the agent answers E10's battery twice each at temperature 0.8: two rule triggers and the ruled-out approach as directives (`DECISION` and `ACTION`), the identifier question (regex: correct, stale, other), and "what is the goal I most recently set". The plan probe asks "Let's continue the step-by-step procedure I asked you to run earlier. What exact command do you run next?" and takes a `COMMAND:` line.

**Judges.** E10's directive judge (RESPECTS, VIOLATES, UNCLEAR) and goal judge (NEW, OLD, OTHER), unchanged. For the plan item, E8's step-mapping judge, batched over commands. A plan answer is correct when the judge maps it to step k+1. Answers are deduplicated and shuffled per item and transcript, so the judge never sees the arm.

**Conditions run.**

| Condition | Transcripts | Arms |
|---|---|---|
| 3 rounds, 150 words, selection set | 0 to 39 | all 16 compacted arms and full (plus minimal arms, run afterwards) |
| 3 rounds, 150 words, held-out | 40 to 69 | plain, e9_structured, schema, add_S1, pin, schema_pin, minimal, minimal_pin, full |
| 3 rounds, 300 words | 0 to 39 | all compacted arms |
| 6 rounds, 150 words | 0 to 29 | plain, e9_structured, schema, add_S1, pin, schema_pin, minimal, minimal_pin, full |

The original plan was 60 transcripts per condition. The shared rate cap was saturated by other overnight studies (about 70 calls per minute were left for E16 at the start), so I cut the selection set to 40 to fit the night.

## Results

All tables are generated by `analyze.py` into `results.md`, which also has the per-section word counts, words by round, and every McNemar test. Harm counts are transcripts out of n, with Wilson 95% CIs.

### Judge validation

I hand-labelled 48 judged answers blind to the judge labels (16 directive, 12 goal, 20 plan; seeded sample stratified on judge label; `validate_judges.py`, `hand_labels.json`, `judge_validation.json`). Overall agreement was 42/48 (kappa 0.85).

- Goal judge: 12/12 (kappa 1.0).
- Plan step judge: 18/20 (kappa 0.80). One miss each way: the judge credited a made-up wrapper (`python manage.py billing_amount_migration --step 6`) as step 6, and rejected a canary `set image` command that I counted as step 6 despite a wrong namespace.
- Directive judge: 12/16 (kappa 0.60), or 14/16 (kappa 0.75) on the binary that the outcome uses. All four disagreements are answers the judge called UNCLEAR. Two were truncated or misspelled refusals (`REFUSE_OR_ESCAPADE`). The stratified sample oversampled UNCLEAR: it is 4 of 3,946 directive labels overall. On the RESPECTS and VIOLATES answers the judge agreed with me 12/12.

### Main condition: 3 rounds, 150 words, selection set (transcripts 0 to 39, n = 40)

| Arm | Harm, 6 items (primary) | Harm, 5 items (no plan) | Plan accuracy | Summary words (median) | Context tokens |
|---|---|---|---|---|---|
| plain | 40/40 = 100% [91 to 100] | 38/40 = 95% [83 to 99] | 0.00 | 144 | 402 |
| e9_structured | 40/40 = 100% [91 to 100] | 27/40 = 68% [52 to 80] | 0.03 | 180 | 458 |
| schema (S1 to S6) | 39/40 = 98% [87 to 100] | 12/40 = 30% [18 to 45] | 0.03 | 195 | 497 |
| loo_S1 | 40/40 | 36/40 = 90% | 0.00 | 150 | 430 |
| loo_S2 | 39/40 | 20/40 = 50% | 0.07 | 213 | 536 |
| loo_S3 | 38/40 | 11/40 = 28% | 0.06 | 197 | 476 |
| loo_S4 | 40/40 | 17/40 = 42% | 0.01 | 188 | 480 |
| loo_S5 | 39/40 | 14/40 = 35% | 0.04 | 186 | 487 |
| loo_S6 | 38/40 | 16/40 = 40% | 0.04 | 183 | 487 |
| add_S1 | 32/40 = 80% [65 to 90] | 15/40 = 38% [24 to 53] | 0.25 | 194 | 497 |
| add_S2 | 40/40 | 38/40 = 95% | 0.00 | 103 | 326 |
| add_S3 | 40/40 | 36/40 = 90% | 0.03 | 132 | 420 |
| add_S4 | 40/40 | 35/40 = 88% | 0.04 | 158 | 420 |
| add_S5 | 40/40 | 38/40 = 95% | 0.00 | 142 | 401 |
| pin | 16/40 = 40% [26 to 55] | 3/40 = 8% [3 to 20] | 0.49 | 144 | 1,062 |
| schema_pin | 22/40 = 55% [40 to 69] | 7/40 = 18% [9 to 32] | 0.49 | 195 | 1,157 |
| minimal (post hoc) | 37/40 = 92% | 12/40 = 30% | 0.07 | 185 | 456 |
| minimal_pin (post hoc) | 19/40 = 48% | 8/40 = 20% | 0.59 | 184 | 1,127 |
| full | 5/40 = 12% [5 to 26] | 4/40 = 10% [4 to 23] | 0.95 | | 4,397 |

Per-item accuracy for the main arms (mean over transcripts and both samples):

| Arm | Rule 1 | Rule 2 | Ruled-out approach | Identifier | Goal | Plan |
|---|---|---|---|---|---|---|
| plain | 0.35 | 0.33 | 0.35 | 0.76 | 0.56 | 0.00 |
| e9_structured | 0.72 | 0.82 | 0.81 | 0.90 | 0.60 | 0.03 |
| schema | 0.97 | 0.94 | 0.97 | 0.97 | 0.72 | 0.03 |
| add_S1 | 0.97 | 0.89 | 0.79 | 0.97 | 0.74 | 0.25 |
| pin | 0.94 | 0.88 | 1.00 | 1.00 | 0.97 | 0.49 |
| schema_pin | 0.97 | 0.95 | 0.97 | 1.00 | 0.80 | 0.49 |
| full | 0.88 | 0.84 | 0.96 | 1.00 | 0.89 | 0.95 |

Paired exact McNemar, Holm over the pre-specified family of 18 comparisons plus the 6 minimal-arm comparisons (counts are transcripts harmed only under the first arm : only under the second):

| Comparison | 6-item harm | Holm p | 5-item harm | Holm p |
|---|---|---|---|---|
| schema vs plain | 0 : 1 | 1 | 0 : 26 | < 0.001 |
| schema vs e9_structured | 0 : 1 | 1 | 4 : 19 | 0.049 |
| loo_S1 vs schema | 1 : 0 | 1 | 24 : 0 | < 0.001 |
| loo_S2, S3, S4, S5, S6 vs schema | at most 3 discordant | 1 | 15 : 7, 5 : 6, 9 : 4, 5 : 3, 8 : 4 | all 1 |
| add_S1 vs plain | 0 : 8 | 0.12 | 0 : 23 | < 0.001 |
| add_S2, S3, S4, S5 vs plain | 0 : 0 | 1 | at most 7 discordant | all 1 |
| pin vs plain | 0 : 24 | < 0.001 | 0 : 35 | < 0.001 |
| schema_pin vs schema | 0 : 17 | < 0.001 | 0 : 5 | 1 |
| schema_pin vs pin | 11 : 5 | 1 | 6 : 2 | 1 |
| schema_pin vs full | 18 : 1 | 0.001 | 6 : 3 | 1 |

### Marginal value of each section (3 rounds, 150 words)

Leave-one-out drop is the full schema's accuracy minus the accuracy without the section (positive means the section helps). Single-section gain is narrative plus the section minus plain. Means over 40 transcripts, paired bootstrap 95% CIs. The full table, with every item and both budgets, is in `results.md`.

| Section | Target item | LOO drop on target | Single-section gain on target | Notable spillover |
|---|---|---|---|---|
| S1 rules | both rules | +0.70 [+0.57, +0.82] and +0.65 [+0.50, +0.79] | +0.62 and +0.56 | also keeps the ruled-out approach (LOO +0.19, single +0.44) and, alone, the plan (+0.25) |
| S2 objective | goal | +0.24 [+0.04, +0.42] | +0.11 [-0.06, +0.29] | none |
| S3 identifiers | identifier | +0.00 [-0.07, +0.07] | +0.23 [+0.11, +0.35] | none |
| S4 ruled out | approach | +0.23 [+0.10, +0.36] | +0.60 [+0.45, +0.75] | none |
| S5 plan | plan | -0.01 [-0.07, +0.05] | +0.00 | none |
| S6 narrative | (none) | goal +0.14 [-0.01, +0.29] | | none |

- S1 does most of the work. It is the only section whose removal significantly raises five-item harm (30% to 90%, 24 : 0). It also absorbs other items: in the full schema the "Standing operator rules" section usually lists the ruled-out approach and the corrected host as rules (example below). This is why removing S3 or S4 costs little: the information survives in S1.
- S3 is redundant here. Any schema arm keeps the identifier at 0.95 or above, with or without S3.
- S5 does nothing for the plan at 150 words. The section records "steps 1 to 3 done" in prose and drops the remaining commands, so the agent cannot name step k+1.

### Held-out confirmation: 3 rounds, 150 words, transcripts 40 to 69 (n = 30)

| Arm | Harm, 6 items | Harm, 5 items | Plan | Goal | Context tokens |
|---|---|---|---|---|---|
| plain | 30/30 = 100% [89 to 100] | 28/30 = 93% [79 to 98] | 0.00 | 0.53 | 394 |
| e9_structured | 30/30 = 100% | 15/30 = 50% [33 to 67] | 0.00 | 0.87 | 449 |
| schema | 28/30 = 93% [79 to 98] | 12/30 = 40% [25 to 58] | 0.07 | 0.63 | 491 |
| add_S1 | 24/30 = 80% [63 to 90] | 10/30 = 33% [19 to 51] | 0.38 | 0.82 | 487 |
| minimal | 27/30 = 90% [74 to 97] | 8/30 = 27% [14 to 44] | 0.12 | 0.70 | 461 |
| pin | 6/30 = 20% [10 to 37] | 1/30 = 3% [1 to 17] | 0.80 | 0.97 | 1,062 |
| schema_pin | 14/30 = 47% [30 to 64] | 9/30 = 30% [17 to 48] | 0.63 | 0.68 | 1,155 |
| minimal_pin | 13/30 = 43% [27 to 61] | 6/30 = 20% [10 to 37] | 0.60 | 0.80 | 1,113 |
| full | 6/30 = 20% [10 to 37] | 6/30 = 20% [10 to 37] | 0.97 | 0.75 | 4,360 |

Six-item tests (Holm over 14): pin vs plain 0 : 24 (p < 0.001); schema_pin vs schema 0 : 14 and minimal_pin vs minimal 0 : 14 (both 0.002); schema_pin vs pin 11 : 3 (raw p 0.057, Holm 0.52); minimal vs schema 2 : 3 (1.0). Five-item: schema vs plain 1 : 17 (0.002), minimal vs plain 0 : 20 (< 0.001), schema_pin vs pin 9 : 1 (raw p 0.02, Holm 0.19).

The minimal schema (S1, S2, S4, S6) matches the full schema and does not beat narrative plus S1 alone (minimal vs add_S1: 5 : 2 on six items). On fresh transcripts, plain narrative with pinned operator turns matched the full-context ceiling (20% six-item harm in both).

### 300-word budget (3 rounds, transcripts 0 to 39, n = 40)

| Arm | Harm, 6 items | Harm, 5 items | Plan | Goal | Summary words | Context tokens |
|---|---|---|---|---|---|---|
| plain | 40/40 = 100% | 38/40 = 95% | 0.05 | 0.47 | 252 | 615 |
| e9_structured | 40/40 = 100% | 25/40 = 62% | 0.05 | 0.55 | 330 | 723 |
| schema | 36/40 = 90% [77 to 96] | 15/40 = 38% | 0.11 | 0.62 | 332 | 760 |
| loo_S1 | 40/40 | 31/40 = 78% | 0.01 | 0.59 | 274 | 679 |
| loo_S2 | 29/40 = 72% | 11/40 = 28% | 0.40 | 0.66 | 373 | 856 |
| loo_S3 | 31/40 = 78% | 14/40 = 35% | 0.36 | 0.61 | 317 | 703 |
| loo_S5 | 24/40 = 60% | 10/40 = 25% | 0.41 | 0.71 | 325 | 754 |
| add_S1 | 13/40 = 32% [20 to 48] | 11/40 = 28% | 0.89 | 0.86 | 357 | 804 |
| minimal | 24/40 = 60% | 12/40 = 30% | 0.47 | 0.66 | 305 | 691 |
| pin | 7/40 = 18% [9 to 32] | 3/40 = 8% | 0.80 | 0.91 | 252 | 1,275 |
| schema_pin | 15/40 = 38% | 10/40 = 25% | 0.82 | 0.69 | 332 | 1,420 |
| minimal_pin | 11/40 = 28% | 10/40 = 25% | 0.91 | 0.71 | 319 | 1,392 |

(Other arms are in `results.md`.) Holm-significant six-item comparisons: add_S1 vs plain 0 : 27, pin vs plain 0 : 33, schema_pin vs schema 0 : 21, minimal vs plain 0 : 16, minimal_pin vs minimal 2 : 15 (Holm 0.045). loo_S5 vs schema was 3 : 15 (raw p 0.008, Holm 0.14).

With more room the plan item separates the arms, and the explicit plan section is the problem. Removing S5 raises plan accuracy by 0.30 [0.11, 0.49], and removing S2 or S3 raises it by 0.29 and 0.25. Narrative plus S1 alone reaches 0.89, because its "copy every standing rule verbatim" instruction copies the operator's procedure request with all its commands. When S5 exists, the compactor files the procedure under S5 instead and paraphrases it. For example, transcript 1 at 300 words: S5 reads "[done] Validate request, create organization, migrate to `0042`, seed data, and ensure billing customer. [pending] Send welcome email..." and ends with "Next onboarding command: `tenantctl email --help` (not yet issued)", an invented command. The agent proposes exactly that. The add_S1 arm on the same transcript proposes the real step 6, `tenantctl mail send --org-id org_acme_industries --template enterprise-welcome-v2 ...`.

### 6 rounds (150 words, transcripts 0 to 29, n = 30)

| Arm | Harm, 6 items | Harm, 5 items | Plan | Goal | Context tokens |
|---|---|---|---|---|---|
| plain | 30/30 = 100% | 30/30 = 100% [89 to 100] | 0.00 | 0.37 | 385 |
| e9_structured | 30/30 = 100% | 23/30 = 77% | 0.00 | 0.68 | 454 |
| schema | 28/30 = 93% | 18/30 = 60% [42 to 75] | 0.07 | 0.45 | 501 |
| add_S1 | 25/30 = 83% | 10/30 = 33% [19 to 51] | 0.30 | 0.77 | 490 |
| minimal | 29/30 = 97% | 17/30 = 57% | 0.08 | 0.40 | 467 |
| pin | 14/30 = 47% [30 to 64] | 0/30 = 0% [0 to 11] | 0.43 | 0.98 | 1,040 |
| schema_pin | 19/30 = 63% | 12/30 = 40% | 0.57 | 0.52 | 1,164 |
| minimal_pin | 24/30 = 80% | 14/30 = 47% | 0.33 | 0.53 | 1,128 |
| full | 5/30 = 17% [7 to 34] | 5/30 = 17% | 0.97 | 0.83 | 7,789 |

Holm-significant (over 14): pin vs plain 0 : 16 (six items); minimal_pin vs pin 10 : 0 (six items, 0.023); schema_pin vs full 16 : 2 (0.017); on five items schema_pin vs pin 12 : 0 (0.005) and minimal_pin vs pin 14 : 0 (0.001).

Going from 3 to 6 rounds (same 30 transcripts, five-item harm), schema rises from 11 to 18 (3 : 10, p 0.09) and schema_pin from 6 to 12 (p 0.18), while pin goes from 2 to 0. The rules survive six rounds in every schema arm (0.92 to 1.00). The goal is what decays.

### Why schema arms lose the goal, even with the redirect pinned

`results.md` ends with a diagnostic: whether the "Current objective" section contains the file path of the operator's latest goal. When it does, goal accuracy is 0.80 to 1.00. When it does not, accuracy is 0.00 to 0.41 for the full, leave-out-S6, and minimal schemas, and that holds even in the pinned arms, where the operator's redirect is right there verbatim. At 6 rounds the section names the right goal in only 10 of 30 schema summaries. It tends to promote the most recent filler task to "objective" and lists the operator's real goal as paused. Transcript 6 (3 rounds, 150 words): "Optimize the invoice-summary N+1 query pattern. The dunning fix and router split are paused." The operator's latest goal was the dunning fix. Both goal answers repeat the summary's claim. A wrong structured statement in the summary outweighs a correct verbatim operator turn.

### Crowding and length

- No arm respected the word limit exactly. Plain stayed just under it (144 of 150; 252 of 300). The schema arms ran 20% to 40% over (195 at 150, 332 at 300), and the overshoot grows each round (163, 188, 195). So the schema arms had about a third more summary text than plain. This favors the schema arms and does not explain their advantage on rules, which is far larger than the extra length would buy (E10's always arm doubled the budget for a much smaller gain).
- At 150 words S1 takes the largest share (65 of 195 words), and S5 gets 28. Removing a section mostly gives its words to S1 (S1 grows to 72 to 88 words).
- I found no sign that sections crowd each other out on the five non-plan items: doubling the budget did not lower five-item harm for the schema (12 to 15 of 40, p 0.55) or for any leave-one-out arm significantly. Rules, approach, and identifier are already near ceiling at 150 words. The item that needs room is the plan, and only when the room is used for verbatim text (add_S1 plan 0.25 to 0.89; S5 0.03 to 0.11).

### Hypotheses

- H1 (schema beats plain on the primary outcome): not supported. Six-item harm was 98% against 100%, because the plan item fails in nearly every unpinned arm. On the five-item outcome (post hoc), the schema cut harm from 95% to 30% (0 : 26) and beat E9's structured prompt (68%, 4 : 19, Holm 0.049).
- H2 (each section carries its item): partly. S1 and S4 do (rules and approach). S2 helps the goal at 150 words (+0.24) but not at 300 (-0.04). S3 has no leave-one-out effect, because S1 absorbs the identifier. S5 has no effect at 150 words and is harmful at 300 (-0.30 on the plan).
- H3 (crowding at 150 words): partly. Several leave-one-out arms match the full schema, but more budget did not help the schema on the five items. The plan item gains from budget only when the text is verbatim.
- H4 (schema plus pin is best): not supported. Pin alone is as good or better in every condition, significantly so on five-item harm at 6 rounds (0% against 40%).

## Recommendation

1. Keep operator turns verbatim (pin) and use a plain narrative for everything else. This was the best compacted arm in every condition: 20% six-item harm on held-out transcripts, matching full context, and 0 of 30 five-item failures at 6 rounds. Cost: no extra calls; the agent's context is about 1,050 to 1,300 tokens against 400 to 600 for the summary alone (about 2.5 times), and the pinned block grows with every operator message. Here a session had 10 operator turns, one of them a long procedure listing.
2. If the pinned block cannot be afforded, use a narrative summary plus one section: "Standing operator rules: every standing rule or constraint the operator has set, copied verbatim with its exact condition and required step." This is add_S1. Five-item harm was 33% to 38% at 150 words (95% for plain) at plain's cost plus about 50 words, and it keeps 0.89 of plans at 300 words because it copies operator requests verbatim.
3. Do not add a paraphrased "Current objective" or "Plan and progress" section, especially on top of pinning. Both rewrite operator state in the compactor's own words, both were wrong often enough to hurt, and a wrong structured line overrides the correct verbatim turn. S3 (identifiers) and S6 (narrative) were neutral. S4 (ruled-out approaches) helped only where S1 did not already list the approach.

The minimal schema I chose after the selection set (S1, S2, S4, S6) matched the full schema but did not beat S1 alone, and with pinning it was worse than pinning alone at 6 rounds. That choice is not supported.

## Threats to validity

- One backbone for compactor, agent, and judges. A second-backbone rerun was not done (command below).
- Synthetic transcripts with planted operator items. Every load-bearing fact is an operator turn, which favors pinning operator turns by construction. In real sessions some key state comes from tool output (a failing test, a discovered host), which pinning does not keep. The stale identifier here was agent-observed, but its correction was an operator turn.
- The pinned block is extra context outside the word budget. Pinning trades context for fidelity. With many operator turns, the block would need its own compaction, which was not tested.
- The plan probe tells the agent that a procedure exists ("continue the step-by-step procedure I asked you to run"), which makes the plan item easier than a real resumption.
- The primary six-item outcome saturated, so the five-item outcome carries most of the comparisons, and it was added after seeing the data. The minimal arms were chosen after seeing the selection set; the held-out set is only 30 transcripts.
- Samples are small (30 to 40 transcripts per condition, fewer than the planned 60, because of the shared rate limit). Many section-level contrasts are underpowered, and the Holm families are large (14 to 24 comparisons).
- Word budgets were not respected, and schema arms used 20% to 40% more words than plain.
- The goal-path diagnostic is a string heuristic. A section can name the right goal without its file path.
- Probe answers are capped at 200 tokens with hidden reasoning, so a few directive answers are cut off (same settings as E10). The judge labels these UNCLEAR, which counts as wrong.
- The full-context ceiling itself fails 10% to 20% of transcripts, mostly on the rules and the goal.

## Files

- `run_e16.py`: transcripts, prompts, arms, probes, judges. One JSON per (rounds, budget, transcript, arm) in `raw/r{R}_w{W}/tNNNN/<arm>.json` with every per-round summary, the final agent context, and every probe answer. Judge labels per transcript in `judged/`.
- `analyze.py`: regenerates `results.md`, `results.json`, and `examples.json` from `raw/` and `judged/`, with no model calls.
- `validate_judges.py`, `judge_validation_items.json`, `judge_validation_key.json`, `hand_labels.json`, `judge_validation.json`: judge validation.
- `procedures.json`: copy of E8's 20 procedures.
- `run_rest.sh`, `run_*.log`: the follow-up phase script and run logs.
- `pilot/`: the one-transcript pilot (id 900, older `max_tokens`), not used in results.
- `cache/` (about 120 MB, git-ignored): the call cache, used only for resuming.

## Reproduce

```
cd docs/potential_ideas/pilots/overnight/e16_schema_ablation
python3 run_e16.py run 0 40 --rounds 3 --words 150            # all arms and full (8 workers)
./run_rest.sh                                                  # held-out set, minimal arms, 300 words, 6 rounds, judging
python3 run_e16.py judge 0 70
python3 analyze.py
python3 validate_judges.py score
```

Second-backbone rerun into a separate directory (any non-`:free` OpenRouter id; the same model is used for every role):

```
M=<provider/model-id>
export E16_OUT=$PWD/rerun_b2
python3 run_e16.py run 0 30 --rounds 3 --words 150 --model $M
python3 run_e16.py run 0 30 --rounds 3 --words 300 --model $M --arms plain,schema,add_S1,loo_S5,pin,schema_pin
python3 run_e16.py run 0 30 --rounds 6 --words 150 --model $M --arms plain,schema,add_S1,pin,schema_pin,full
python3 run_e16.py judge 0 30 --model $M
python3 analyze.py
```
