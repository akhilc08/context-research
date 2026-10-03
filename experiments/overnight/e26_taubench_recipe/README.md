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

---

Everything below was written after the runs. All numbers come from `results/tables.md`, which `analyze.py` regenerates from the raw files with no model calls.

## Short answer

- **The recipe and the minimal recipe both repair compaction's process violations (H1 and H2 supported).** In retail, 7.8% of recipe runs and 7.4% of minimal runs broke at least one checked rule, against 28.3% under plain compaction (115 tasks, 2 trials; Holm p = 8e-8 and 3e-8). In airline the rates were 11% and 6% against 33% (50 tasks, 2 trials; Holm p = 0.001 and 2e-5).
- **Neither beats pinning the policy alone (H3 and H4 null).** Recipe vs pin: 7.8% vs 9.6% in retail (difference -1.7 points, 95% CI -6.1 to +3.0) and 11% vs 10% in airline (+1, CI -6 to +8). Minimal vs pin: -2.2 points in retail (CI -6.5 to +2.2) and -4 in airline (CI -9 to +1). No Holm p is below 1.
- **Non-inferiority to no compaction is not shown (H5 not supported).** Recipe minus hist is +2.2 points in retail (CI -1.7 to +6.1) and +1 in airline (CI -5 to +7). Both CIs cross the 3-point margin, so the data cannot rule out a small loss. This is a failure to show non-inferiority, not evidence that the recipe is worse.
- **The progress block does nothing measurable.** Recipe with and without it: 7.8% vs 7.4% (retail) and 11% vs 12% (airline). Plain compaction plus the block (`compact_prog`): 20.9% vs 28.3% in retail (unadjusted p = 0.11) and 31% vs 33% in airline. The block restates that actions need explicit confirmation, yet the agent kept skipping confirmation. The active ingredient is the verbatim policy.
- **Across all 25 methods, what matters is whether the policy text stays in context verbatim.** Every method that keeps it lands near the uncompacted level: pin, pinrules, recipe, minimal, the ledger, head plus tail truncation and observation masking (5% to 10% in retail, 6% to 14% in airline). Prompts that ask the summarizer to keep rules help partly (keep-rules sentence 13% and 12%, E15 list 14% and 16%). Provenance, anchor, grace buffer, source re-summarization, round-trip gate, repair passes and both watchpoints do not measurably help. FIFO truncation is the worst method, worse than plain compaction (43% and 52%).
- **Reward still does not see any of this.** No confirmatory reward comparison is significant (every Holm p is 0.99 or 1). The only reward effect near significance in the leaderboard is FIFO, which lowers retail reward (0.48 vs 0.65 on trial 0, Holm p = 0.057).
- **The detectors held up on new arms.** On 48 new hand-labeled writes, precision was 0.96 and Cohen's kappa 0.79. Recall weighted to the population was lower (0.57), because 4 of 24 unflagged writes were violations and the unflagged stratum is large.

## Deviations from the pre-registration

1. **One restart.** The first launch ran inside a shell with a 2-hour limit. I stopped it after 14 runs, all of them cache replays of E22 arms, and relaunched it detached. Finished rows were kept and the run resumed. No new-arm run was affected.
2. **No other deviations.** Arms, trials, schedule, detectors, tests and families are as written. Concurrency stayed at 25. Provider errors stayed below 1% of calls (367 logged errors over 56,660 calls, across all studies running at the time), so there was no reason to step down to 15.

## Results

E22's six arms replayed exactly from the copied cache: every replayed row has E22's events and reward, with zero API calls. Their numbers therefore equal E22's.

### Confirmatory comparisons (primary, Holm over 10)

| domain | comparison | type | tasks a higher / b higher | rate a | rate b | difference (95% CI) | p | Holm p |
|---|---|---|---|---|---|---|---|---|
| retail | recipe vs compact (H1) | superiority | 4 / 41 | 7.8% | 28.3% | -20.4 (-26.5 to -13.9) | 9e-9 | 8e-8 |
| retail | minimal vs compact (H2) | superiority | 3 / 40 | 7.4% | 28.3% | -20.9 (-27.4 to -14.8) | 3e-9 | 3e-8 |
| retail | recipe vs pin (H3) | superiority | 10 / 14 | 7.8% | 9.6% | -1.7 (-6.1 to +3.0) | 0.54 | 1 |
| retail | minimal vs pin (H4) | superiority | 9 / 13 | 7.4% | 9.6% | -2.2 (-6.5 to +2.2) | 0.52 | 1 |
| retail | recipe vs hist (H5) | non-inferiority, margin +3 | 10 / 6 | 7.8% | 5.7% | +2.2 (-1.7 to +6.1) | 0.66 | 1 |
| airline | recipe vs compact (H1) | superiority | 1 / 17 | 11% | 33% | -22 (-33 to -12) | 1e-4 | 0.001 |
| airline | minimal vs compact (H2) | superiority | 1 / 23 | 6% | 33% | -27 (-37 to -18) | 3e-6 | 2e-5 |
| airline | recipe vs pin (H3) | superiority | 7 / 6 | 11% | 10% | +1 (-6 to +8) | 1 | 1 |
| airline | minimal vs pin (H4) | superiority | 1 / 5 | 6% | 10% | -4 (-9 to +1) | 0.22 | 1 |
| airline | recipe vs hist (H5) | non-inferiority, margin +3 | 4 / 2 | 11% | 10% | +1 (-5 to +7) | 0.51 | 1 |

Differences are in percentage points. Superiority rows use an exact two-sided sign test over tasks. Non-inferiority rows use the one-sided paired t-test against +3 points, with the p doubled.

The secondary analyses agree:

- **Corrected confirmation detector.** H1 and H2 hold in both domains (Holm p from 2e-7 to 0.001), and H3, H4 and H5 stay null. Minimal vs pin in airline comes closest (3% vs 8%, Holm p = 0.75).
- **Gold-conflict tasks removed.** Removing the tasks whose gold actions trip a detector changes no conclusion.
- **Confirmation detector alone.** In retail, recipe and minimal cut confirmation failures from 22.6% to 3.5% and 4.3%, the same level as hist (3.5%). In airline, compaction's confirmation effect is small to begin with (12% vs 6%), and nothing is significant.

### Leaderboard: retail (115 tasks)

Rates are over all runs of an arm. Added arms ran trial 0 only; plain compaction's trial-0 rate is 31.3%, and the "vs compact" column pairs one-trial arms with that trial. Holm runs across both domains' leaderboard rows (48 tests).

| arm | trials | violation rate (95% CI) | reward | pass^2 | model calls/run | input tok/run | output tok/run | vs compact (points) | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| hist (no compaction) | 2 | 5.7% (3.3 to 9.4) | 0.626 | 0.496 | 19.0 | 78,430 | 1,203 | -22.6 | 1e-9 |
| mask | 1 | 5.2% (2.4 to 10.9) | 0.626 | | 19.6 | 79,597 | 1,288 | -26.1 | 7e-7 |
| recipe_ckpt | 1 | 6.1% (3.0 to 12.0) | 0.609 | | 21.9 | 85,002 | 2,610 | -25.2 | 2e-5 |
| pinrules | 2 | 6.5% (4.0 to 10.5) | 0.600 | 0.443 | 21.9 | 74,323 | 1,773 | -21.7 | 2e-8 |
| ledger | 1 | 7.0% (3.6 to 13.1) | 0.643 | | 22.1 | 87,555 | 1,755 | -24.3 | 3e-5 |
| minimal | 2 | 7.4% (4.7 to 11.5) | 0.617 | 0.478 | 21.9 | 83,035 | 1,723 | -20.9 | 1e-7 |
| recipe_noprog | 2 | 7.4% (4.7 to 11.5) | 0.609 | 0.470 | 21.8 | 84,066 | 2,588 | -20.9 | 3e-7 |
| recipe | 2 | 7.8% (5.0 to 12.0) | 0.591 | 0.452 | 21.7 | 84,757 | 2,547 | -20.4 | 4e-7 |
| pin | 2 | 9.6% (6.4 to 14.1) | 0.630 | 0.496 | 21.4 | 78,947 | 1,698 | -18.7 | 3e-4 |
| headtail | 1 | 9.6% (5.4 to 16.3) | 0.574 | | 21.6 | 84,665 | 1,449 | -21.7 | 6e-5 |
| keeprules | 1 | 13.0% (8.1 to 20.4) | 0.617 | | 21.6 | 70,081 | 2,059 | -18.3 | 0.024 |
| e15list | 1 | 13.9% (8.7 to 21.4) | 0.583 | | 22.3 | 77,610 | 3,301 | -17.4 | 0.036 |
| e9 | 1 | 17.4% (11.5 to 25.3) | 0.548 | | 21.4 | 69,431 | 2,087 | -13.9 | 0.16 |
| selfcheck | 1 | 19.1% (13.0 to 27.3) | 0.600 | | 54.8 | 103,029 | 2,165 | -12.2 | 0.49 |
| compact_prog | 2 | 20.9% (16.1 to 26.6) | 0.613 | 0.470 | 21.1 | 69,110 | 1,723 | -7.4 | 1 |
| anchor | 1 | 23.5% (16.7 to 32.0) | 0.609 | | 21.4 | 68,759 | 1,783 | -7.8 | 1 |
| watch | 2 | 23.5% (18.5 to 29.4) | 0.574 | 0.452 | 25.8 | 82,841 | 4,490 | -4.8 | 1 |
| repair | 1 | 26.1% (18.9 to 34.8) | 0.591 | | 24.7 | 74,710 | 2,755 | -5.2 | 1 |
| source | 1 | 27.8% (20.5 to 36.6) | 0.661 | | 21.0 | 69,378 | 1,810 | -3.5 | 1 |
| prov | 1 | 27.8% (20.5 to 36.6) | 0.600 | | 21.4 | 69,665 | 1,971 | -3.5 | 1 |
| compact | 2 | 28.3% (22.8 to 34.4) | 0.596 | 0.470 | 20.9 | 67,000 | 1,771 | | |
| grace | 1 | 33.0% (25.1 to 42.1) | 0.617 | | 20.8 | 68,367 | 1,686 | +1.7 | 1 |
| roundtrip | 1 | 33.0% (25.1 to 42.1) | 0.643 | | 29.1 | 85,421 | 3,266 | +1.7 | 1 |
| fifo | 1 | 42.6% (34.0 to 51.7) | 0.478 | | 19.2 | 65,015 | 1,329 | +11.3 | 0.96 |
| nopolicy | 2 | 52.6% (46.2 to 59.0) | 0.574 | 0.443 | 17.6 | 59,469 | 1,235 | +24.3 | 3e-5 |

### Leaderboard: airline (50 tasks)

Plain compaction's trial-0 rate is 34%.

| arm | trials | violation rate (95% CI) | reward | pass^2 | model calls/run | input tok/run | output tok/run | vs compact (points) | Holm p |
|---|---|---|---|---|---|---|---|---|---|
| minimal | 2 | 6% (3 to 13) | 0.48 | 0.34 | 20.2 | 76,072 | 2,367 | -27 | 1e-4 |
| recipe_ckpt | 1 | 8% (3 to 19) | 0.54 | | 18.3 | 70,011 | 2,715 | -26 | 0.066 |
| mask | 1 | 8% (3 to 19) | 0.44 | | 15.9 | 58,777 | 1,491 | -26 | 0.11 |
| ledger | 1 | 8% (3 to 19) | 0.54 | | 18.9 | 77,839 | 2,071 | -26 | 0.030 |
| hist (no compaction) | 2 | 10% (6 to 17) | 0.49 | 0.38 | 16.6 | 70,878 | 1,643 | -23 | 0.002 |
| pin | 2 | 10% (6 to 17) | 0.50 | 0.40 | 19.6 | 72,238 | 2,238 | -23 | 0.009 |
| headtail | 1 | 10% (4 to 21) | 0.42 | | 19.3 | 73,465 | 1,771 | -24 | 0.053 |
| recipe | 2 | 11% (6 to 19) | 0.46 | 0.36 | 20.2 | 77,805 | 2,859 | -22 | 0.005 |
| recipe_noprog | 2 | 12% (7 to 20) | 0.44 | 0.30 | 20.1 | 75,794 | 2,910 | -21 | 0.067 |
| keeprules | 1 | 12% (6 to 24) | 0.60 | | 18.7 | 60,927 | 2,547 | -22 | 0.085 |
| pinrules | 2 | 14% (9 to 22) | 0.45 | 0.34 | 18.8 | 63,738 | 2,182 | -19 | 0.067 |
| e15list | 1 | 16% (8 to 29) | 0.46 | | 18.0 | 59,300 | 2,921 | -18 | 0.26 |
| watch | 2 | 19% (13 to 28) | 0.44 | 0.30 | 22.5 | 72,204 | 4,934 | -14 | 0.40 |
| e9 | 1 | 28% (18 to 42) | 0.32 | | 18.3 | 58,195 | 2,349 | -6 | 1 |
| prov | 1 | 30% (19 to 44) | 0.34 | | 19.8 | 64,645 | 2,558 | -4 | 1 |
| selfcheck | 1 | 30% (19 to 44) | 0.42 | | 58.3 | 109,783 | 3,389 | -4 | 1 |
| repair | 1 | 30% (19 to 44) | 0.36 | | 24.3 | 75,464 | 3,695 | -4 | 1 |
| compact_prog | 2 | 31% (23 to 41) | 0.35 | 0.22 | 19.3 | 63,008 | 2,387 | -2 | 1 |
| source | 1 | 32% (21 to 46) | 0.50 | | 18.7 | 61,248 | 2,266 | -2 | 1 |
| anchor | 1 | 32% (21 to 46) | 0.40 | | 19.1 | 60,369 | 2,338 | -2 | 1 |
| compact | 2 | 33% (25 to 43) | 0.40 | 0.22 | 19.1 | 60,796 | 2,314 | | |
| roundtrip | 1 | 34% (22 to 48) | 0.38 | | 25.9 | 77,181 | 3,771 | 0 | 1 |
| grace | 1 | 36% (24 to 50) | 0.40 | | 18.6 | 62,211 | 2,222 | +2 | 1 |
| fifo | 1 | 52% (39 to 65) | 0.38 | | 17.0 | 56,274 | 1,729 | +18 | 0.67 |
| nopolicy | 2 | 61% (51 to 70) | 0.33 | 0.24 | 16.2 | 56,336 | 1,782 | +28 | 0.003 |

Calls and tokens count every call a run makes (agent, simulated customer, summarizer and checkers), including calls answered from the shared cache. The ledger's one build call per domain is not included. Airline has only 50 tasks and one trial for added arms, so its leaderboard has little power: no added arm except the ledger survives Holm there, although several sit at the hist level.

### What the method comparison shows

**Verbatim policy is the whole effect.** The methods at the hist level differ in mechanism but share one property: the policy text is still in context word for word. Pin, pinrules, recipe and minimal re-attach it after every summary. The ledger re-attaches a model-made verbatim copy of its rules. Head plus tail truncation keeps the policy as the head. Observation masking never removes it. Methods that rely on a summarizer to carry the rules, however the prompt asks, do worse. The best of them are the keep-rules sentence and the E15 standing-rules list, at 12% to 16%. They roughly halve plain compaction's rate but stay above pinning. E9's structured checkpoint, the provenance clause and the anchor prompt do not reliably help.

**Detect-and-repair methods do not repair this failure.** The naive self-check, E22's extraction Watchpoint, the round-trip gate and E7's repair passes are all within about 12 points of plain compaction. None is significant after correction. As in E22, the checks ask whether the agent can recall the rules, and it usually can. The self-check said the confirmation rule was "still active" in 97% of retail checks and 94% of airline checks, so it re-attached that rule only rarely. The round-trip gate fired on 10% of retail checks and 21% of airline checks. Its questions were about the customer's request (order ids, refund method), not about rules. Repair passes produced reasonable rule lists, and the agent still skipped confirmation about as often. The self-check also costs the most: 55 to 58 model calls per run, against 21 for plain compaction.

**The progress block is redundant here.** It was meant to carry the active operation. A τ-bench conversation's operation is short, and the verbatim tail usually still holds it. Blocks had a pending proposal in 20% of retail compactions and 41% of airline compactions. With the policy pinned, adding the block changed nothing. Without the policy, the block's one-sentence restatement of the confirmation rule did not stop the agent from skipping confirmation (see the example below).

**Timing does not matter once the policy is pinned.** Checkpoint timing gave 6.1% vs the recipe's 7.0% on trial 0 in retail, and 8% vs 10% in airline. Neither difference is significant. This matches E19, where timing mattered only for plain summaries.

**Truncation behaves as expected.** FIFO drops the policy at the first compaction and keeps nothing in its place, so it is the worst compacted method. Head plus tail keeps the policy, so it is safe. Its retail runs more often hit the 30-step limit (10.4% of runs end with no stop and no transfer, against 1.7% for compaction), probably because it keeps no record of the middle of the conversation. A grace buffer of 8 messages instead of 4 does not help. The rules sit in the first message, far outside any tail.

**Masking is not compression on τ-bench.** τ-bench tool outputs are short, and the roughly 1,000-word policy dominates the context. Masking saved almost nothing: 79,597 input tokens per retail run against 78,430 with no compaction. It is safe for the same reason it is cheap to keep: it changes almost nothing.

**Summary budgets were not respected by structured prompts.** The 200-word budget held for the plain, anchor and grace prompts (103 to 117 words on average). The recipe prompt averaged 346 words, the keep-rules sentence 216 to 238, E9 about 225, and E15's verbatim rules list 545 to 634. The rule-keeping prompts partly work by spending more words on the policy. They are not matched in tokens to plain compaction.

### Qualitative examples

**The progress block's rule did not stop an unconfirmed write (retail task 11, trial 0).** The customer wants refunds cross-swapped between two orders. The agent refuses and offers original-method refunds. The customer answers "Damn. Fine. Just return both to the original payment methods." In `compact_prog`, the context after compaction contained the progress block, which says an action "needs the customer's explicit confirmation of its exact details before it is executed". The agent called `return_delivered_order_items` immediately anyway. In `minimal` (the same block plus the pinned policy), on the same task and trial, the agent first listed both returns with item ids, amounts and refund methods, asked for "yes", and wrote only after the customer said "Yes."

**A recipe failure that pinning avoided (retail task 41, both trials).** The recipe arm ran a second item change on an order whose one-shot change was already used, and the `once` detector fired. The pinned policy states the rule ("can only be called once"), and the recipe's own checkpoint also mentioned the one-time limit. The agent still made the call, on the same customer turn as an earlier write. On a few tasks like this, recipe and pin each fail where the other does not. The counts are close to even (retail 10 tasks vs 14), which is what a null difference looks like.

**FIFO forgets the confirmation step.** After the first FIFO compaction the context starts with "[Earlier messages were removed by the harness to save space.]" and the last few turns. The policy is gone, and nothing replaces it. Runs with a write made without confirmation rise from 22.6% (plain compaction) to 33.9% in retail (no policy at all: 43.5%) and from 12% to 40% in airline (no policy: 36%).

## Detector validation

`validate.py dump` drew 48 writes with seed 0 from arms E22 did not run: 16 flagged and 16 unflagged retail writes, and 8 and 8 airline writes. Arm and flags were hidden. I (the agent that ran this study) labeled each from the shown trajectory: 1 if it breaks a checked rule as the written policy states it. A write made after the customer only picked among options, without the agent listing the final details and getting a yes, was labeled a violation. Labels and reasons are in `results/validation_labels.json`.

| domain | precision | recall in sample | recall weighted to population | Cohen's kappa |
|---|---|---|---|---|
| retail | 0.94 (15/16) | 0.88 | 0.54 | 0.81 |
| airline | 1.00 (8/8) | 0.80 | 0.64 | 0.75 |
| all | 0.96 (23/24) | 0.85 | 0.57 | 0.79 |

The one false positive is E22's known bug: "No longer needed" (a cancellation reason) read as a refusal. E22's corrected detector fixes it (precision 1.00, kappa 0.83). The four misses are:

- a write executed after the customer chose options, with no final details and yes (two cases);
- a cabin upgrade made without listing price or payment;
- a write that used a different card from the one the customer confirmed. No detector checks that.

Weighted recall is low because each miss is multiplied by the large unflagged population (3,511 unflagged against 539 flagged retail writes). With 4 misses in 24 unflagged items, that estimate is very uncertain. It matches E22's finding that the confirmation detector under-counts writes made after vague consent. Under-counting affects every arm, so it would bias comparisons only if it depended on arm. No sign of that appeared. Precision here is higher than E22's 0.78, partly because this sample has fewer confirmation flags.

## Simulated user audit

`audit_user.py` over every run (`results/audit_retail.txt`, `results/audit_airline.txt`):

| domain | runs | ended with no stop and no transfer | stopped before any write on a task that needs one | denied a fact from its instruction | copied 12+ words of its instruction |
|---|---|---|---|---|---|
| retail | 4,025 | 1.4% | 1.1% | 0.2% | 0.6% |
| airline | 1,750 | 3.7% | 2.1% | n/a | 0% |

Rates are similar across arms. The exceptions are retail `headtail` (10.4% with no stop and no transfer, from hitting the step limit) and airline `selfcheck` (10%). Transfers to a human end 19% of retail runs and 54% of airline runs, as in E22.

## Threats to validity

- **Modified benchmark.** The policy is in history, compaction is forced, and tool descriptions are stripped. Reward is not a τ-bench score, and the process metric has no published baseline.
- **One model plays every role.** Agent, simulated customer, summarizer, ledger keeper and every checker are `stealth/space-bunny-alpha`. Other models may summarize, recall or follow rules differently. X1 found that the naive self-check behaves differently on another model.
- **Added arms have one trial.** They are compared with plain compaction's trial 0. Airline has 50 tasks, so most airline leaderboard rows are underpowered.
- **Budgets are not matched.** Head plus tail, masking, pinning and the ledger keep far more tokens than a 200-word summary, and structured prompts overran the summary budget. The leaderboard compares methods as specified, not at equal context size.
- **Adapted methods.** Every method was mapped onto a conversation with one long operator message. Several were designed for many operator turns: the ledger, revocation handling, and the progress block's operation tracking. The progress block's "pending proposal" comes from a fixed pattern, not from a model. The round-trip gate uses E10's threshold without recalibration. FIFO's budget (1,300 characters) is an approximation of the summary budget.
- **Shared cache.** New arms reuse E22's replies, including the simulated customer's, until their context first differs. This reduces noise in paired comparisons, and it means arms are not independent samples.
- **Hand labels from the study's author.** Labels were blind to arm and flags but written by the agent that ran the study. The validation sample is small (48 writes).
- **Detector coverage.** The detectors miss writes made after vague consent and do not check that executed details match confirmed details.

## Cost

The main runs made 56,660 API calls (203 million input tokens, 6.6 million output tokens; `../usage.jsonl` tags starting `e26:`), over about 2.8 hours. E22's six arms cost nothing because they were replayed from cache. Per-arm costs, counting cached calls, are in the leaderboard tables.

## Reproduce

Run from this directory with the τ-bench venv. `results/cache.sqlite` starts as a copy of `../e22_taubench_process/results/cache.sqlite`.

```bash
PY=/private/tmp/taubench-venv/bin/python
cp ../e22_taubench_process/results/cache.sqlite results/cache.sqlite   # E22 replies, for exact replay
./run_all.sh                                                           # both phases (WORKERS=25 by default)
python3 analyze.py > results/tables.md
python3 validate.py dump        # blind sample; then label results/validation_labels.json
python3 validate.py score > results/validation_scores.md
$PY audit_user.py results/retail.jsonl > results/audit_retail.txt
$PY audit_user.py results/airline.jsonl > results/audit_airline.txt
```

`run.py` resumes: finished (domain, arm, task, trial) rows are skipped. No run crashed in the main runs, so no `_errored.jsonl` file exists.

**Second backbone.** `--model` sets every model call, and `--user_model` can split off the simulated customer. `:free` models are refused. The cache key includes the model, so a second backbone never reuses these replies. Use a separate output suffix so the results do not mix:

```bash
$PY run.py --model <openrouter-model-id> --domain both --trials 0-1 --out_suffix _backbone2 \
  --arms hist compact pin pinrules minimal compact_prog recipe recipe_noprog
$PY run.py --model <openrouter-model-id> --domain both --trials 0 --out_suffix _backbone2 \
  --arms recipe_ckpt fifo headtail mask source e9 keeprules e15list prov anchor grace selfcheck roundtrip repair ledger watch nopolicy
```

Then run `python3 analyze.py _backbone2`, which reads `results/<domain>_backbone2.jsonl`. The ledger is rebuilt for the new model only if `results/ledger_<domain>.json` is removed or moved first. Otherwise the first backbone's ledger is reused. That second backbone was not run.

## Files

- `run.py`: agent loop, user simulator, stripping, schedule and every method's harness logic (E22's code for E22's arms). `methods.py`: arm table, every compaction prompt with its source, the progress block, and the check prompts.
- `run_all.sh`: the two main-run phases.
- `llm.py`, `detectors.py`, `gold_check.py`, `audit_user.py`, `rules_*.json`: copied from E22 unchanged (`llm.py` has a new header note only).
- `analyze.py`: regenerates `results/tables.md`, including the confirmatory family, secondary families, the leaderboard and method diagnostics.
- `validate.py`: E22's validation script, restricted to the new arms.
- `results/retail.jsonl`, `results/airline.jsonl`: one row per run, with compaction records (summaries, progress blocks, check outputs) and full trajectories.
- `results/ledger_retail.json`, `results/ledger_airline.json`: the E17 ledger built from each policy.
- `results/tables.md`, `results/validation_*`, `results/audit_*.txt`, `results/main_A.log`, `results/main_B.log`: generated outputs and run logs.
- `results/retail_pilot.jsonl`, `results/pilot.log`, `results/ledger_retail_e26pilot.json`: the one-task pilot on the retail train split.
- `results/cache.sqlite`: model reply cache (git-ignored).
