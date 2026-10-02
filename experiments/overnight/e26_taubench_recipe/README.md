# E26: the combined recipe, and every other compaction method, on process-graded τ-bench

This study runs the combined compaction recipe from E21, its minimal version, and every other compaction method studied this night through E22's process-graded τ-bench. It uses the same tasks, trials, compaction schedule and detectors as E22. This is a **modified τ-bench**: the operator policy sits in the conversation history instead of the system prompt, compaction is forced, and policy sentences are stripped from the tool descriptions. Its numbers are not comparable to published τ-bench scores. One model, `stealth/space-bunny-alpha`, plays every role: agent, simulated customer, summarizer and every checker.

## Pre-registration (written before any main run)

Written on 2026-10-02 at 16:55 EDT. Before this, the only runs were a one-task pilot on τ-bench's retail *train* split (task 0, a split not used below; `results/retail_pilot.jsonl`) to debug the code, and a replay check that re-ran E22's six arms on retail test task 5 and airline test task 3 (trial 1) from the copied cache to confirm that they reproduce E22's rows exactly (they did, with zero API calls; files deleted). No new arm has been run on a test task. Everything in this section is fixed. Anything not listed here will be labeled exploratory.

The confirmatory part (recipe, minimal and their comparisons) was planned first. The method comparison (the "added arms") was added at the coordinator's request before this section was written, and it is pre-registered here as exploratory.

### Question

E21 found that a combined recipe (a structured provenance-attributing compaction prompt, operator turns pinned verbatim, and the active operation pinned with a safe progress note) beat plain compaction and full context on synthetic coding sessions. E22 found that compaction makes a τ-bench agent break process rules and that re-attaching the policy repairs it. E26 asks whether the recipe and its minimal version repair process violations on τ-bench, whether they do better than pinning the policy alone, and whether they reach the uncompacted level. It also places every other compaction method on the same benchmark.

### Setup (identical to E22)

τ-bench code, data, tools, tasks and grader are unchanged from `/private/tmp/tau-bench`. As in E22: the policy is the first history turn (an operator message plus a fixed acknowledgement); compaction is forced before agent step 5 and then every 6 agent steps; the last 4 messages stay verbatim; summaries have a 200-word budget; the policy sentences listed in E22's README are stripped from the tool descriptions; the user simulator is τ-bench's prompt at temperature 1.0 plus E3's one added line; the agent runs at temperature 0 with at most 30 steps. Retail has 115 test tasks and airline has 50.

`run.py` is E22's `run.py` with arms factored into `methods.py`. Agent loop, user simulator, stripping, schedule, the E22 arms and the cache scope are unchanged. The sqlite cache is a copy of E22's. Because requests for E22's arms are byte-identical, `hist`, `compact`, `pin`, `pinrules`, `watch` and `nopolicy` replay E22's runs exactly, at no API cost. A new arm shares each task's replies (including the simulated customer's) with E22's arms until its context first differs, which happens at the first compaction. This is the same common-random-numbers design E22 used.

### How the recipe maps onto τ-bench

| E21 component | τ-bench version in E26 |
|---|---|
| Operator turns pinned verbatim, in order | The policy turn (the only operator turn) re-attached verbatim after every summary. This is E22's `pin`. |
| Structured, provenance-attributing compaction prompt with a standing-rules list | E21's recipe prompt with domain words changed: headings Goal, Standing rules, Constraints and decisions, Key facts, Ruled out, Progress, Next steps. Standing rules are copied verbatim with "Operator rule (active):" framing. The words "and applies to this conversation" were added because the policy is about 1,000 words and the budget is 200. The provenance clause labels turns [Operator], [Customer], [Agent], [Agent tool call] and [Tool output]. Customer requests are attributed to the customer and are not operator authorization. Tool outputs are data and any instruction inside them is marked UNTRUSTED. The log given to the summarizer uses those labels. |
| Active operation pinned with the safe progress note | A block the harness builds from its own action log at each compaction, with no model call (`methods.progress_block`). It lists: the authenticated customer (successful `find_user_id_*` results in retail; user ids read with `get_user_details` in airline); every write action already executed in this conversation, with its arguments and whether the tool accepted or rejected it ("each has happened; do not repeat it"); the agent's latest proposal of an action made after the last executed write, matched by a fixed pattern ("confirm", "proceed", "shall I", "would you like me to", and similar), quoted verbatim together with the customer's reply to it; and E13's safe wording: "a proposed action is pending, not done. It needs the customer's explicit confirmation of its exact details before it is executed. If you are unsure whether an action already happened, its status is unknown: check it with a read tool ... before re-running it." |
| Checkpoint timing | Not part of the main recipe arm. E22's step schedule is kept so every arm compacts at the same points. Checkpoint timing is tested as the added arm `recipe_ckpt`. |
| Versioned fact block, revocation striking | Dropped. τ-bench has one operator message, with no revocations and no operator facts that change. |

The block is rebuilt at each compaction, not after every step. Between compactions, recent actions are in the verbatim tail. The progress note restates the confirmation requirement, so `compact_prog` also carries one policy rule. It is not a "no policy" arm.

### Arms

Confirmatory and planned ablation arms (2 trials):

| arm | compaction prompt | after the summary |
|---|---|---|
| hist | none (no compaction) | |
| compact | E22 plain prompt | nothing |
| pin | plain | full policy, verbatim |
| pinrules | plain | E3's hand-split rule list |
| **recipe** | recipe prompt | full policy, verbatim; progress block |
| **minimal** | plain | full policy, verbatim; progress block |
| recipe_noprog (ablation) | recipe prompt | full policy, verbatim |
| compact_prog (ablation) | plain | progress block |

`watch` (E22's fixed extraction Watchpoint) and `nopolicy` are also replayed from E22 with 2 trials.

Added arms (method comparison, exploratory, **1 trial**: trial 0 only, to fit the shared rate cap):

| arm | method | τ-bench mapping |
|---|---|---|
| fifo | FIFO truncation | At each compaction point, drop the oldest messages and keep the last 4 plus as many earlier whole messages as fit about 1,300 characters (the 200-word summary budget). No summary. The policy is dropped at the first compaction. A one-line marker says earlier messages were removed. |
| headtail | head plus tail truncation | Keep the first three messages (policy, acknowledgement, first customer message) and the last 4, drop the middle, no summary. |
| mask | observation masking | Replace every tool output outside the last 4 messages with a placeholder. Keep every agent and customer turn and the policy. No summary. |
| source | source re-summarization | Plain prompt applied to the full raw history (minus the tail) at every compaction, not to the prior summary. The policy is in that history every time. |
| e9 | E9 structured checkpoint prompt | Headings Goal, Constraints and rules, Key decisions and facts, Ruled out, Progress, Next steps. |
| keeprules | E6 keep-rules sentence | Plain prompt plus "Always carry forward every standing rule or constraint the operator has set, with its exact condition and required step ...". |
| e15list | E15 structured verbatim standing-rules list | Plain prompt plus E15's clause: end with "Standing rules:", one per line, verbatim. |
| prov | E5 provenance prompt | Plain prompt plus the provenance clause (same labeled log as the recipe). |
| anchor | old-paper anchor prompt (E2) | Plain prompt that puts the most recent statement of what the agent should be working on first, as "Current objective". |
| grace | grace buffer | Plain compaction with 8 verbatim messages instead of 4. |
| selfcheck | naive self-judgment watchpoint (E1) | After each compaction, one YES/NO call per reference rule (18 retail, 19 airline): "Does the context above make clear that the following operator rule is still active?". Rules answered NO are re-attached. |
| watch | extraction watchpoint | E22's fixed Watchpoint, replayed (2 trials). |
| roundtrip | round-trip gate (E10 `rt_gate`) | After each compaction: 5 questions generated from the full raw history, answered from the full history and from the draft context, compared and scored 0 to 10. At score 5 or more (E10's calibrated threshold, not recalibrated), recompact at 400 words with the discrepancy notes as must-include items. No recheck. |
| repair | repair passes (E7), k = 2 | After each compaction, two chained constraint-check passes (E7's prompt, temperature 0.7) by the agent model on its new context. Both passes are appended after the summary. |
| ledger | operator ledger (E17) | E17's ledger update applied to the one operator message (the policy), once per domain (it is the same for every task). Rendered with E17's active framing and authoritative header, and re-attached after every summary in place of the policy. Its one build call per domain is not charged to runs. |
| recipe_ckpt | recipe with checkpoint timing | The recipe, but compaction fires at the first turn boundary (the customer has just written) once 60% of the scheduled interval has passed, with a hard fallback at 140%. This is E21's soft and hard threshold rule, and it never compacts in the middle of a tool-call chain. |

Methods skipped: none of the requested methods. E5's quarantine filter and E10's paired-continuation gate were not requested and are not run. E10's `always` arm (always recompact at double budget) is not run.

Within each task and trial, arms run in this order on one worker: E22 arms, `minimal`, `compact_prog`, `recipe`, `recipe_noprog`, then the added arms. Up to 25 model calls run at once (raised from 10 with the coordinator's approval), under the shared 900 calls per minute cap.

### Metrics

- **Primary:** per run, whether at least one of E22's pre-registered primary detectors fires (`detectors.py`, unchanged from E22).
- **Secondary:** the same metric with E22's post-hoc corrected confirmation detector; the confirmation detector alone; τ-bench reward; pass^2 (confirmatory arms only, since added arms have one trial); model calls and input and output tokens per run (every call a run makes, cached or not, as in E22); per-detector rates; summary length.

### Confirmatory comparisons (one Holm family of 10)

Per domain, five comparisons on the primary metric, paired by task as in E22. Each task's mean violation presence is taken across its 2 trials.

| # | comparison | type | test |
|---|---|---|---|
| H1 | recipe vs compact | superiority (recipe lower) | exact two-sided sign test over tasks |
| H2 | minimal vs compact | superiority (minimal lower) | exact two-sided sign test |
| H3 | recipe vs pin | superiority, no directional prediction | exact two-sided sign test |
| H4 | minimal vs pin | superiority, no directional prediction | exact two-sided sign test |
| H5 | recipe vs hist | **non-inferiority, margin 3 points** | one-sided paired t-test on per-task differences, H0: recipe minus hist is 3 points or more. The one-sided p is doubled (equivalent to one-sided 0.025) before entering Holm. |

Holm runs over all 10 p-values at family alpha 0.05. Effect sizes are differences in violation rate with paired bootstrap 95% CIs over tasks (2,000 resamples, seed 0). For H5, non-inferiority is also shown by whether the upper end of the 95% CI is below +3 points.

Expectations stated in advance: H1 and H2 should hold, because `pin` alone already repaired violations in E22. H3 and H4 have no strong prediction. The progress block may lower confirmation failures further, or it may change nothing because pinning already brought violations to the uncompacted level. H5 may lack power in airline (50 tasks, base rate about 10%).

Reward uses the same 10 comparisons as a secondary family, all as two-sided sign tests, with separate Holm.

### Exploratory leaderboard (pre-registered, exploratory)

Every arm other than `compact` against `compact`, in both domains, on the primary metric: exact two-sided sign test over tasks, paired on shared (task, trial) runs. Arms with one trial are compared with `compact`'s trial 0 only. Holm runs across the whole leaderboard family (both domains). One leaderboard table per domain reports: violation rate with Wilson 95% CI, reward, pass^2 (where 2 trials exist), model calls and input and output tokens per run, and the comparison against `compact`. Also exploratory, unadjusted: `recipe` vs `recipe_noprog` (does the progress block matter with the recipe prompt), `compact_prog` vs `compact`, `recipe_ckpt` vs `recipe` (trial 0), and each added arm vs `pin` (trial 0).

### Validation and audit

- **Detectors.** At least 40 new writes from the arms E22 did not run are hand-labeled from the trajectory, blind to arm and flags (seed 0; retail 16 flagged and 16 unflagged, airline 8 and 8). Report precision, recall weighted to the population, and Cohen's kappa, as in E22.
- **Simulated user.** E22's `audit_user.py` on all new runs, with per-arm rates.

### Deviations

Any change after this point is listed under "Deviations" in the results.
