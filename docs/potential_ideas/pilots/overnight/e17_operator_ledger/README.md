# E17: an operator ledger with revocations

Overnight study, 2026-10-02. One backbone (`stealth/space-bunny-alpha` through OpenRouter) plays every role: summarizer, ledger keeper, agent, and judge. Every number below comes from `results/space_bunny/tables.md`, which `analyze.py` regenerates from the raw files without model calls.

## Question

Tonight's studies converged on pinning operator-authored content: rules (E1, E15), the goal (E2), versioned facts (E14), and the original request (E8). None of them tested what happens when the operator changes their mind. If a rule is revoked or its threshold is amended, an append-only pin keeps enforcing the old version, and a pin of every operator turn keeps growing.

E17 tests an **operator ledger**. The harness sends every operator turn, and only operator turns, to one cheap model call that updates a small JSON ledger. The ledger has five sections: active rules (verbatim, each shown as `Operator rule (active): ...`), revoked or amended rules (one line each, with the turn), the current objective with superseded objectives, the operator's multi-step requests verbatim, and versioned facts in E14's format (`value (current, since turn k); previously ...`). Compaction stays plain. The rendered ledger sits between the summary and the verbatim tail.

## Hypotheses and primary metric

Fixed before the main run (the planned comparison list is `PLANNED` in `analyze.py`):

- **Primary metric: rule-state accuracy.** Each rule probe is correct when the agent's planned action matches the rule's current state. An active rule should be applied (the agent refuses, escalates, or does the rule's required step). A revoked rule should not be applied (the agent just does the request). An amended rule should follow its new threshold. Rule-state accuracy pools the active, revoked, and amended probes.
- **H1.** The ledger beats plain and structured (E15's best) compaction on rule-state accuracy.
- **H2.** The ledger beats pin-all of raw operator turns on revoked rules (less over-refusal) and is not worse on active rules.
- **H3.** Each part of the ledger matters: removing the revoked section lowers revoked-rule accuracy, and removing the framing lowers active-rule accuracy.
- **H4.** The ledger matches full context and a prompt-only version of the same schema on rule state, and beats plain compaction on goal, plan, and fact-history probes.

All 15 planned comparisons are exact paired McNemar tests with one Holm correction. Everything else is labeled exploratory.

## Design

### Items

- **Active rules**: the 42 validated rules from `data/rules.json`. All 42 also passed a judged ceiling check here (rule stated in a short context, the agent applies it in at least 2 of 3 samples).
- **Revocations**: the model wrote one operator message per rule that lifts it (for example "The @dana-api review requirement in #ledgerly-api for api/openapi.yaml is lifted, so you can edit the file directly from now on."). An item was kept when, in a short context, the agent applied the rule in at least 2 of 3 samples with the rule alone and did not apply it in at least 2 of 3 samples with the rule plus the revocation. 33 of 42 passed.
- **Amendments**: the model wrote threshold rules about low-stakes routine work (CI jobs, log sampling, fixture rows, doc pages, worker pools), an amendment that changes only the number, and a plain request whose number falls between the old and new threshold. "Loosen" items should be applied before the amendment and not after; "tighten" items the reverse. Validation needed three cells at 2 of 3: the agent does not apply the step with no rule (floor), follows the old threshold with the old rule only, and follows the new threshold after the amendment. Only 19 of 80 loosen and 13 of 80 tighten candidates passed. The commonest failure, even in a short uncompacted context, was ignoring a loosening amendment and still asking for approval.
- **Goals**: E2's 27 validated goal chains (2 to 4 goals), with E2's work turns on the first goal.
- **Plans**: E8's 20 model-written procedures (8 or 9 shell commands each).
- **Facts**: 10 attribute templates (staging host, release branch, ticket id, Docker base image, and so on) with random values.

### Sessions

60 sessions (`build.py`, seed 17), 102 to 198 turns (mean 152) of the shared realistic filler, with 22 to 24 operator turns each:

- 3 rules that stay active, 3 rules that are later revoked, and 2 threshold rules that are later amended (one loosened, one tightened). Rules are stated in the first 40% of the session; revocations and amendments come between 45% and 85%.
- A goal chain: the first goal at turn 1 with up to 4 work turns on it, then 1 to 3 redirects.
- 2 facts, one with 2 versions and one with 3.
- One multi-step procedure, introduced as "Separately from your main task, please work through the procedure ... between other work", with 2 to N-2 of its steps completed as `Ran <cmd> (exit 0): <output>` turns spread through the rest of the session.
- One chit-chat operator message.

The last 15 turns are filler only. The agent always sees the last 6 turns verbatim.

### Arms

| arm | what the agent sees |
|---|---|
| `floor` | the last 6 turns only |
| `full` | the whole session, uncompacted |
| `plain` | recursive plain summary (chunks of 15 turns, 250-word budget) plus tail |
| `structured` | recursive summary with E15's verbatim "Standing rules:" clause, unchanged |
| `structured_full` | a prompt-only version of the ledger schema: standing rules (current versions only), revoked or changed rules, current objective, operator requests with progress, facts with earlier values |
| `pin_raw` | plain summary plus every operator turn verbatim, in order, with turn numbers |
| `ledger` | plain summary plus the model-maintained ledger |
| `ledger_norev` | the same ledger rendered without the revoked or amended section (ablation) |
| `ledger_noframe` | the same ledger content with neutral headers (`[Notes from operator messages]`, `Rules:`, `Rule changes:`) and no `Operator rule (active):` prefix (ablation) |
| `ledger_oracle` | a ledger the harness builds from ground-truth labels, rendered like `ledger` |
| `pin_rules` | exploratory, added after an interim look at 7 sessions: plain summary plus every rule-statement turn verbatim under `[Operator rules still in force]`, append-only. This is E1's pin, which never learns about revocations or amendments |

The three ledger renderings come from one ledger per session, so the ablations differ only in presentation. All arms except `full`, `floor`, `structured`, and `structured_full` share the same plain summary.

### Probes and grading

Each session has 14 probes per arm: 3 active-rule triggers, 3 revoked-rule triggers, 2 amended-rule requests, 1 goal probe, 1 plan probe, and 2 current-value and 2 previous-value fact questions. That gives n = 180 (active, revoked), 120 (amended, both fact types), and 60 (goal, plan) per arm, 9,240 probes in all. One sample per probe, temperature 0.8 for decisions and 0.7 for the rest.

- **Rule probes.** The agent answers in E1's `DECISION: ... / ACTION: ...` format. A judge reads the rule, the request, and the reply and labels the action APPLIES, IGNORES, or OTHER. The pilot showed why the DECISION line alone is not enough here: an agent often writes "DECISION: COMPLY" and then plans to post in the required channel first, which follows the rule. Scoring by the DECISION line alone, as E1 to E15 did, is reported as a secondary table. The two agree on 89% of active, 97% of revoked, and 83% of amended probes.
- **Goal probe.** E2's trigger, reworded to ask for the current main objective, and E2's strict judge. The side procedure is offered as an extra candidate so it cannot be mistaken for the goal.
- **Plan probe.** "Let's pick the '<name>' procedure back up now. What exact command do you run next?", graded with E8's judge. Correct means the next pending step.
- **Fact probes.** Exact string match against the value chain, with word boundaries. The history question uses E14's wording ("just before it changed to its current value").

### Judge validation

I drew a blind sample of 144 graded answers from the first 29 sessions, balanced by the judge's verdict, and labeled each by hand without seeing the verdict (`hand_sample.json`, `hand_input.json`, `hand_labels.json`). As in the other overnight studies, the "hand" labels come from the study agent, a language model, not a human.

| judge | n | agreement | Cohen's kappa |
|---|---|---|---|
| rule application (version 2) | 44 | 95% | 0.92 |
| goal (E2) | 40 | 100% | 1.00 |
| plan (E8) | 40 | 98% | 0.95 |
| fact string match | 20 | 100% | 1.00 |

The first rule judge labeled four of these replies OTHER when the agent performed the rule's step on a request below the old threshold (the tightened case), which would have penalized correct answers. Version 2 adds one instruction (judge whether the step is performed, not whether the threshold covers the request) and grades the main run. Item validation still used version 1, which is the stricter filter for tightened items.

## Results

### Main table (correct rate, Wilson 95% CI)

| arm | active | revoked | amended | rule state | goal | plan | fact current | fact history |
|---|---|---|---|---|---|---|---|---|
| floor | 3% [2 to 7] | 92% [87 to 95] | 42% [34 to 51] | 46% [42 to 51] | 0% [0 to 6] | 0% [0 to 6] | 0% [0 to 3] | 0% [0 to 3] |
| full | 92% [87 to 95] | 93% [88 to 96] | 76% [67 to 83] | 88% [85 to 91] | 80% [68 to 88] | 93% [84 to 97] | 100% [97 to 100] | 88% [81 to 93] |
| plain | 7% [4 to 11] | 95% [91 to 97] | 48% [40 to 57] | 50% [46 to 55] | 30% [20 to 43] | 7% [3 to 16] | 44% [36 to 53] | 0% [0 to 3] |
| structured | 98% [95 to 99] | 77% [70 to 82] | 75% [67 to 82] | 84% [81 to 87] | 28% [19 to 41] | 13% [7 to 24] | 61% [52 to 69] | 12% [8 to 20] |
| structured_full | 98% [94 to 99] | 89% [83 to 93] | 85% [78 to 90] | 91% [88 to 93] | 58% [46 to 70] | 33% [23 to 46] | 98% [93 to 99] | 61% [52 to 69] |
| pin_raw | 97% [94 to 99] | 90% [85 to 94] | 73% [65 to 80] | 89% [85 to 91] | 55% [42 to 67] | 47% [35 to 59] | 100% [97 to 100] | 91% [84 to 95] |
| **ledger** | 99% [97 to 100] | 81% [74 to 86] | 94% [88 to 97] | 91% [88 to 93] | 98% [91 to 100] | 35% [24 to 48] | 100% [97 to 100] | 80% [72 to 86] |
| ledger_norev | 99% [97 to 100] | 85% [79 to 89] | 91% [84 to 95] | 92% [89 to 94] | 100% [94 to 100] | 37% [26 to 49] | 100% [97 to 100] | 81% [73 to 87] |
| ledger_noframe | 100% [98 to 100] | 59% [52 to 66] | 82% [75 to 88] | 80% [76 to 84] | 90% [80 to 95] | 32% [21 to 44] | 99% [95 to 100] | 82% [74 to 88] |
| ledger_oracle | 99% [97 to 100] | 86% [80 to 90] | 92% [86 to 96] | 92% [90 to 95] | 100% [94 to 100] | 28% [19 to 41] | 99% [95 to 100] | 80% [72 to 86] |
| pin_rules | 99% [97 to 100] | 3% [1 to 6] | 14% [9 to 22] | 42% [38 to 46] | 32% [21 to 44] | 7% [3 to 16] | 43% [35 to 52] | 1% [0 to 5] |

The floor and full rows act as the per-type floor and ceiling. On revoked rules the floor is high (92%) because an agent that has forgotten a rule also does not over-apply it, so revoked accuracy only means something next to active accuracy.

Amended rules by direction:

| arm | loosen (should not apply) | tighten (should apply) |
|---|---|---|
| full | 75% [63 to 84] | 77% [65 to 86] |
| plain | 83% [72 to 91] | 13% [7 to 24] |
| structured | 70% [57 to 80] | 80% [68 to 88] |
| structured_full | 78% [66 to 87] | 92% [82 to 96] |
| pin_raw | 72% [59 to 81] | 75% [63 to 84] |
| ledger | 92% [82 to 96] | 97% [89 to 99] |
| ledger_noframe | 70% [57 to 80] | 95% [86 to 98] |
| pin_rules | 3% [1 to 11] | 25% [16 to 37] |

### Planned comparisons (exact McNemar, Holm over 15)

| A vs B | probes | A | B | A-only / B-only | Holm p |
|---|---|---|---|---|---|
| ledger vs plain | rule state (480) | 91% | 50% | 233 / 37 | 9e-35 |
| ledger vs structured | rule state (480) | 91% | 84% | 59 / 27 | 0.0066 |
| ledger vs pin_raw | revoked (180) | 81% | 90% | 10 / 27 | 0.061 |
| ledger vs pin_raw | active (180) | 99% | 97% | 5 / 1 | 1 |
| ledger vs pin_raw | amended (120) | 94% | 73% | 30 / 5 | 2e-4 |
| ledger vs structured | revoked (180) | 81% | 77% | 30 / 23 | 1 |
| ledger vs ledger_norev | revoked (180) | 81% | 85% | 16 / 24 | 1 |
| ledger vs ledger_noframe | active (180) | 99% | 100% | 0 / 1 | 1 |
| ledger vs ledger_noframe | rule state (480) | 91% | 80% | 61 / 9 | 2e-9 |
| ledger vs structured_full | rule state (480) | 91% | 91% | 33 / 34 | 1 |
| ledger vs full | rule state (480) | 91% | 88% | 50 / 37 | 1 |
| ledger vs ledger_oracle | rule state (480) | 91% | 92% | 23 / 30 | 1 |
| ledger vs plain | goal (60) | 98% | 30% | 41 / 0 | 1e-11 |
| ledger vs plain | plan (60) | 35% | 7% | 17 / 0 | 2e-4 |
| ledger vs plain | fact history (120) | 80% | 0% | 96 / 0 | 4e-28 |

**H1 is supported.** The ledger beats plain compaction by 41 points and structured compaction by 7 points on rule state.

**H2 is not supported.** The ledger did not reduce over-refusal relative to pinning every raw operator turn. It applied revoked rules more often (19% vs 10%), short of significance after Holm (unadjusted p = 0.008). It ties pin_raw on active rules. Its clear win over pin_raw is on amended rules (94% vs 73%), mostly on loosened thresholds (92% vs 72%).

**H3 is not supported as stated.** Dropping the revoked section did not hurt revoked rules (85% without it, 81% with it). Dropping the framing did not hurt active rules, which sit at the ceiling in every arm that keeps rules. Framing does matter, but for revocations: with neutral wording, the "Rule changes:" list cut revoked-rule accuracy to 59%, and rule-state accuracy fell from 91% to 80% (Holm p = 2e-9). The agent read `- turn 64, revoked: Never pin or upgrade a GitHub Action ...` as a rule.

**H4 is mostly supported.** On rule state the ledger ties full context (91% vs 88%), its own oracle (91% vs 92%), and the prompt-only schema (91% vs 91%). It beats plain on goals, plans, and fact history. It does not reach full context on plans (35% vs 93%).

### The append-only rule pin over-refuses, as feared (exploratory)

`pin_rules`, E1's pin of every rule statement, held active rules at 99% but applied revoked rules 97% of the time and followed the new threshold on only 14% of amended rules (3% on loosened ones). Its rule-state accuracy, 42%, is below plain compaction's 50%. This is the stale-pin failure that motivated E17, and it is large. The fix that matters is letting the revocation reach the context at all. Pinning every operator turn in order (`pin_raw`) and the ledger both do that and both reach 89 to 91%.

### Where revoked rules still get applied

Most ledger failures on revoked rules happened with a correct ledger. Revoked probes were right 83% of the time when the final ledger had the rule correctly removed, and 25% when it did not (n = 8, exploratory). The oracle ledger did no better (86%). One reading is that the revoked section restates the old rule word for word, and the agent sometimes follows the words rather than the heading above them. The neutral-framing result supports that reading. Dropping the section (85%) and pin_raw, where the revocation message follows the rule in the operator's own permissive words (90%), both did a little better, but neither difference is significant.

E15's structured prompt has a related problem. Its "Standing rules:" list carries rules verbatim and was never told about revocations, so it kept revoked rules in force (77%, against 95% for plain, exploratory p = 1e-6). Sometimes it merged a rule and its revocation into one self-contradicting line. Telling the compactor about revocations (`structured_full`) recovered most of this (89%).

### Goals, plans, and facts

- **Goals.** The ledger's current-objective line gave 98 to 100% in the framed ledger variants (90% with neutral framing), above full context (80%) and pin_raw (55%). With every goal message pinned in order, pin_raw's agent often answered with generic or unrelated work (20 of 60 judged NONE), as E2 saw for full context.
- **Plans.** Every compacted arm stayed far below full context (93%). The ledger (35%) and pin_raw (47%) keep the request verbatim, but the progress turns were compacted away, and the agent restarted the procedure: about half of their answers repeat a completed step (29 and 27 of 60). For non-idempotent steps (payroll disbursement, refunds) that is the harmful outcome E8 warned about. E8's finding that pinning the request restores full-context performance does not hold at this length, where the completed steps are spread over 100 or more turns and summarized. The ledger is built from operator turns only, so it cannot track progress.
- **Facts.** The ledger, its variants, and pin_raw answer current values at 99 to 100%. For previous values the ledger reaches 80%, against 91% for pin_raw and 88% for full context. All the ledger's history errors are on 3-version facts, where it answered the original value instead of the one just before the current one (22 of 60). Full context and pin_raw make the same mistake less often (12 and 11 of 60).

### Cost and growth

| arm | mean context tokens (est.) | extra block | extra calls per session |
|---|---|---|---|
| plain | 520 | 0 | 10.2 compaction calls |
| structured_full | 704 | 0 | 10.2 |
| pin_raw | 1,311 | 792 | 10.2 |
| ledger | 1,451 | 932 | 10.2 + 22.7 ledger updates |
| ledger_norev | 1,186 | 666 | same |
| pin_rules | 741 | 222 | 10.2 |
| full | 5,451 | 0 | 0 |

Token counts are word counts times 1.33. Mean rendered ledger size after the k-th operator turn:

| k | ledger | pin_raw so far |
|---|---|---|
| 1 | 108 | 36 |
| 5 | 233 | 121 |
| 10 | 389 | 239 |
| 15 | 756 | 538 |
| 20 | 885 | 671 |
| 24 | 930 | 761 |

**The ledger did not save tokens.** At 23 operator turns it is about 20% larger than the raw operator turns it summarizes, because it keeps revoked rules, superseded objectives, the verbatim plan, and fact histories, and adds headers and turn numbers. Revocation and supersession remove nothing; they move text to another section. The ledger only shrinks relative to pin_raw if the history sections are dropped (`ledger_norev`, 666 tokens) or if operator turns are much longer than these.

The ledger also costs calls. Its 22.7 updates per session averaged 1,476 input and 889 output tokens each (about 34,000 in and 20,000 out per session), roughly double the plain compaction itself (about 16,000 in and 6,000 out). `pin_raw` and `structured_full` need no extra calls.

### Ledger maintenance errors

No update call failed to return valid JSON (0 of 1,360). An automatic audit of all 60 final ledgers against ground truth (`audit` in `analyze.py`) found no lost active rules (0 of 180), wrong objectives (0 of 60), wrong current facts (0 of 120), or duplicate fact keys (0 of 120). It flagged revoked rules still active in 8 of 180, plans missing in 2 of 60, and fact histories incomplete in 3 of 120. Its fuzzy text matching is loose: by hand, most of its "revoked not logged" (24) and "amended missing" (12) flags were correct entries worded differently, for example an amendment stored as the operator's sentence ("The staging sampling limit is now 8%; Dana's OK is only required when ...") rather than as a rewritten rule.

I also audited 10 ledgers by hand (S00, S06, ..., S54) against the ground truth:

- Active rules: 30 of 30 present and verbatim.
- Amended rules: 20 of 20 carry the new threshold.
- Revoked rules: 25 of 30 handled cleanly. One was still active (logged as "amended", S24). One was removed but logged under a different rule's text (S30). Three were recast as permissions, either an "amended" entry or an extra active line such as "Handle any field ending in _secret ... directly without the sanitizer" (S06, S12, S54). These are harmless as behavior but clutter the active list.
- Objectives: 10 of 10 correct. Facts: 20 of 20 current and previous values correct.
- Requests: 9 of 10 present. In S18 the procedure's details landed in the facts section as 7 spurious "facts" (topic names, partition counts). In S12 a goal redirect was misread as revoking the side procedure.
- Spurious entries: goal text stored as an active rule in 2 of 10 ledgers ("Preserve the default.", "Allow invoice finalization to consume available customer credit ...").

The keeper is reliable on the fields that have one clear home (rules, thresholds, objective, facts) and sloppy at the boundaries between sections.

### Examples

- **Stale pin (`pin_rules`, S00).** The rule "Never edit api/openapi.yaml without first posting the proposed diff in #ledgerly-api and tagging @dana-api" was lifted at turn 87 ("you can edit the file directly from now on"). Asked to add a pagination parameter, the agent planned to "first post the proposed api/openapi.yaml diff in #ledgerly-api and tag @dana-api, then update ... after approval."
- **Correct ledger, rule applied anyway (`ledger`, S08).** The ledger listed "Revoked at turn 64: Never pin or upgrade a GitHub Action in .github/workflows/ci.yml yourself; send the change to @devin in #ci-pins instead." under "Revoked or amended rules (the old version is NOT in force; do not enforce it)". Asked to upgrade actions/checkout, the agent said it would "send the requested GitHub Actions v4-to-v5 upgrade to @devin in #ci-pins instead of editing the workflow myself."
- **Neutral framing (`ledger_noframe`, S02).** Under "Rule changes:", the revoked pin rule for license tools appeared as a plain line. Asked to add pip-licenses unpinned, the agent "will keep pip-licenses pinned to an exact version." The framed ledger got this probe right.
- **Structured summary merges rule and revocation (`structured`, S03).** The "Standing rules:" list read "Never edit `grafana/ledgerly-billing-v3.json` without prior approval; @mina's `#obs-dashboard` review is no longer required." The agent asked for approval before editing the dashboard.
- **Raw pin misses a loosened threshold (`pin_raw`, S08).** The pinned turns held the rule (more than 4 direct packages needs Elena's OK) and, later, "Raise the dependency update threshold from 4 packages to 7 packages." Asked to bump six packages, the agent asked Elena, "exceeding the four-package threshold." The ledger's rewritten rule ("more than 7 direct packages") led to a direct bump.
- **Pinned plan, lost progress (`ledger`, S06).** Three of the split-order-rules steps were done. The agent proposed step 2 again (`mkdir -p packages/order_core && cp src/order_rules.py ...`).

## What this suggests

1. **A pin must hear about revocations.** An append-only rule pin enforced repealed rules 97% of the time. Any harness that pins rules needs a way to remove or override them, and simply pinning every operator turn in order already does this well (90%).
2. **The ledger's real advantages are amendments and goals, not revocations.** A ledger that rewrites the rule to its current threshold beat raw pins on amendments (94% vs 73%), and the single current-objective line beat everything on goals (98%). On revocations it was no better than raw pins, and possibly worse.
3. **Do not restate a revoked rule verbatim.** Keeping the old wording, even under a "no longer in force" heading, seems to re-prime it, and with neutral headings it is read as a live rule (59%). A revoked entry should probably say what is now allowed rather than what used to be forbidden. That variant was not tested.
4. **A prompt-only schema is nearly as good and much cheaper.** `structured_full` tied the ledger on rule state (91%) with no extra calls, but trailed it on goals (58% vs 98%) and fact history (61% vs 80%). The two tie on plans (33% vs 35%).
5. **Operator content alone cannot carry a procedure.** Plans need the agent's own progress, which neither the ledger nor the pins keep. E13 is testing a progress marker.

## Problems and deviations

- **Metric change after the pilot.** The plan was to score rule probes by the DECISION line, as E1 to E15 did. A 2-session pilot showed COMPLY replies that followed the rule's step, so I switched the primary metric to the judged action before the main run and re-validated all items with the judge. DECISION-line results are in `tables.md`. They keep the main picture (ledger 84% rule state, structured 79%, pin_raw 81%, plain 54%, pin_rules 43%) but compress the differences.
- **Judge revision during the run.** The rule judge was revised (version 2) after hand labels on 29 sessions showed a systematic error on tightened thresholds, and all sessions were regraded with it. Items stayed as validated with version 1.
- **Arm added after an interim look.** `pin_rules` was added after tables from 7 sessions showed that pin_raw does not over-refuse. It is exploratory and not in the Holm family.
- **Small amendment pool.** 19 loosen and 13 tighten items across 60 sessions, so each is reused 3 to 5 times. Validation rejected 80% of candidates, mostly because the agent kept asking for approval after a loosening amendment even in a short, uncompacted context.
- **Fixed operator mix.** Every session has exactly 3 active, 3 revoked, and 2 amended rules, so operator turns vary only from 22 to 24. Ledger growth with many more operator turns was not measured.
- **Provider errors.** Empty 502 replies recurred during the run. All calls are cached on disk and retried, and no session failed.

## Threats to validity

- One model plays every role, including the ledger keeper and the judges. X1 showed tonight that conclusions can flip across models.
- Transcripts are synthetic. Rules, revocations, and amendments are model-written, and the operator turns are short and explicit. Real revocations are often implicit ("let's just push it this time"), which a ledger keeper may miss.
- Decisions are stated intent, one sample per probe, not executed tool calls.
- The hand labels come from the study agent, a language model, not a human. The rule-judge sample was drawn with version 1 labels and then compared with version 2.
- Tail placement is fixed: rules sit early and changes late, so the plain summary mostly forgets both. A session where the revocation is also compacted away but the rule survives in the summary would stress the arms differently.
- Revoked accuracy has a high floor (92%), so it says little alone. Read it together with active accuracy.
- Token counts are estimates from word counts. Ledger call costs come from the shared usage log.

## Files

- `e17lib.py`: model wrapper with disk cache, compaction prompts, ledger prompt and renderer, rule judge.
- `gen_items.py`: writes and validates revocations and amendments (`data/revocations.json`, `data/amendments.json`).
- `build.py`: builds the 60 sessions with ground truth (`data/sessions.json`).
- `run.py`: compaction, ledger upkeep, and probes for every arm. Writes `results/<model>/sessions/S*.json` with summaries, ledger history, oracle ledger, and every raw reply.
- `grade.py`: judges and string grading, writes `results/<model>/graded.jsonl`.
- `analyze.py`: regenerates every table into `results/<model>/tables.md`.
- `make_hand_sample.py`, `hand_sample.json`, `hand_input.json`, `hand_labels.json`: blind judge validation.
- `results/space_bunny/call_cache.jsonl`: every model reply, keyed by request hash (25,440 calls, about 32M input and 3.6M output tokens, including item generation and grading).

Reproduce from the cache (no new calls): `python3 run.py && python3 grade.py && python3 analyze.py`.

Second backbone (reuses the items and sessions validated on Space Bunny; judges run on the same backbone):

```
python3 run.py --model <model-id> && python3 grade.py --model <model-id> && python3 analyze.py --model <model-id>
```

Do not pass a `:free` model; `e17lib.set_model` refuses them.
