# Overnight compaction studies, 2026-10-02

One unattended night of experiments on context compaction for long-running coding agents. A coordinator built shared infrastructure, ran about 15 studies in parallel through background agents, reviewed each result by regenerating its tables from raw outputs, and committed it. Every study has its own README with design, full tables, judge validation, and threats to validity. This page is the map and the synthesis.

Status: written while E3, E12, E13, E16, and E17 were still running. Their rows say so.

## Setup shared by every study

- **Model.** Every role (summarizer, agent, detector, judge) ran on `stealth/space-bunny-alpha` through OpenRouter, free during this run. About 235,000 calls, 378M input and 28M output tokens by 05:40. One small replication used `nvidia/nemotron-3-ultra-550b-a55b:free` (see X1).
- **Shared code.** `orclient.py` (client with retries, a 900-call-per-minute cap shared across processes, and a pause file), `watchdog.py` (pauses traffic on rate-limit spikes or quota errors), `common.py` (realistic filler, recursive compaction, the decision agent, statistics helpers).
- **Data.** `data/filler_turns.json` holds 308 realistic coding-agent turns with commands, outputs, and diffs, replacing the old one-line filler. `data/rules.json` holds 42 operator rules that passed both a floor check (the agent obeys the violating request when no rule is stated) and a ceiling check (it refuses when the rule is in full context). 29 of 96 candidates failed the ceiling: the agent broke them even with the rule uncompacted in context.
- **Standards.** Each study states its hypothesis and primary metric up front, reports Wilson 95% intervals, uses paired McNemar tests with Holm correction, validates every LLM judge against at least 40 blind hand labels (labeled by the study agent, not a human) with Cohen's kappa, keeps raw outputs, and has one script that regenerates its tables. Analyses added after seeing data are labeled exploratory.

## Studies

| ID | Question | Headline | Commit |
|---|---|---|---|
| E1 `e1_rule_scaling` | Does Watchpoint lose to pinning as the number of tracked rules N grows? | Plain compaction worsens with N (53% to 79% violations). Pin-all holds at 6 to 14% at every N. Batched watchpoint does not degrade with N but trails pinning (pooled 31 vs 16 of 192, p = 0.008) and costs more. The naive self-check fails (kappa 0.00). | `f03b9bc` |
| E2 `e2_goal_resurrection` | Goal resurrection without the old keyword leak, with a pinned-goal baseline | Pinned goal 97% ties watchpoint 98% at no extra calls; plain 81%. The failure is goal loss to recent work, not resurrection. The anchor prompt does not help (75%). Full context scores only 63%. | `43070de` |
| E3 `e3_taubench` | Compaction on a modified τ-bench retail | Running. | |
| E4 `e4_supersede` | Knowledge updates under bounded notes (Supersede, LongMemEval) | Newest-value pin 81% vs 300-char notes 67%. Watchpoint patched 153 of 154 rounds and did not beat pin. Newest-value pins fail history questions (1 of 13). | `3f40829` |
| E5 `e5_provenance` | Does compaction launder untrusted tool text into operator instructions? | Yes, in 17 to 23% of plain summaries, and the agent then usually acts on it. But rule loss dominates (violations 0% to 50%). Provenance-attributing prompt plus pinning blocked every injected action without hurting real updates. | `aac0b94` |
| E6 `e6_ratchet` | Recursive compaction ratchet over 16 rounds | Recursive keeps a rule in 2 to 5% of summaries at round 16, source re-summarization 21 to 31%. Lost rules rarely return (7 of 76). Conditional rules are not specially vulnerable. A one-sentence "carry forward standing rules" prompt keeps 93 to 100% at recursive cost. New "distorted" category: rules recast as resolved past events. | `6ed9d63` |
| E7 `e7_repair_retention` | Repair passes vs retained raw tokens at matched budgets | Repair fixes rules still in the summary (21% to 12%), not deleted ones (77% to 74%). Retention fixes both. Crossover near 24x compression. Pinning beats both at a tenth of the tokens. Repair invents constraints. | `9c34bb0` |
| E8 `e8_inflight` | Compaction in the middle of a multi-step procedure | The loss is the plan, not position: drift and invented ids. Ledger and progress watchpoint do nothing (31 to 34% vs 31%). Pinning the original request restores full-context performance. A naive progress note caused harmful repeats. Pilot. | `e40cc2c` |
| E9 `e9_cheap_validation` | Can cheap signals predict harmful compactions? | Draft agreement fails (AUROC 0.59). Round-trip reconstruction works (0.76, noise ceiling 0.78) at about 15% of the cost. Prompt style and budget alone predict nearly as well. | `c03929d` |
| E10 `e10_roundtrip_gate` | Round-trip as a gate that triggers recompaction | Generic self-written questions do not predict harm held out (0.55). The gate ties always-recompacting at 3.3x the tokens; the paired-continuation gate is near useless. A structured prompt beats every repair arm at no extra cost (53% vs 80 to 97% harm). | `ba34598` |
| E11 `e11_subtle_laundering` | E5 with subtle injections, a counterfactual causal test, and an attribution watchpoint | Writing a planted action into a summary as a remaining step makes the agent act 88% of the time, against 33% with its source named (Holm p = 1e-10). But renaming the source in naturally laundered summaries did not reduce acting (59% vs 64%). Procedural checklist items launder most. Provenance prompt plus pinning remains best (1% and 0%). Labeling laundered sentences `[UNVERIFIED]` did not stop the agent. | `3aa5aa5` |
| E12 `e12_rot_vs_compaction` | Session length at which compaction beats full context | Running. | |
| E13 `e13_plan_pinning` | E8 at realistic length, with a safe in-flight marker | Running. | |
| E14 `e14_versioned_pin` | Pin each fact's value history instead of only the newest value | Versioned pin 95% vs newest-value pin 83% on LongMemEval (Holm p = 0.025), history questions 19% to 85%, current questions unchanged, beats token-matched notes. Canonical keys add nothing measurable. | `c8b76c3` |
| E15 `e15_rule_salience` | Why is an intact summarized rule violated more than a pinned one? | Framing ("Operator rule (active):") is the biggest factor, then exact wording; position and separation barely matter. Pinned rules beat raw history (6% vs 15%). Keep-rules and structured-list prompts scale to 20 rules over 16 rounds; structured is indistinguishable from pin-all. | `d1e3fc7` |
| E16 `e16_schema_ablation` | Which sections of a structured compaction schema matter? | Running. | |
| X1 `x1_cross_model` | Replicate E1 and E2 on a second model | Direction replicates on Nemotron (plain loses, pin and watchpoint fix it and tie). Samples are tiny. The naive self-check works on Nemotron, so its failure may be model-specific. | `fb6bfce` |

## What the night suggests

These are cross-study readings, not pre-registered claims. All rest on one model plus a small replication, synthetic transcripts, and stated-intent decisions rather than executed tool calls.

1. **Pinning beats checking.** In E1, E2, E4, E7, E8, and E15, always reinjecting operator-authored content (rules, goals, the original request) ties or beats Watchpoint's check-then-patch, at lower cost. Watchpoint's selectivity mostly disappears where loss is common: it patched 89 to 99% of the time in E1 and E4. The old paper's own conclusion ("pin rules") extends to goals and plans.
2. **Tell the compactor what to keep instead of repairing afterwards.** A one-sentence keep-rules prompt (E6, E15), a structured prompt (E9, E10), and a provenance-attributing prompt (E5) each beat post-hoc detection and repair. Paired-continuation and round-trip gates added cost without matching a better prompt (E10).
3. **How a kept fact is presented matters, not just whether it survives.** An intact rule inside a narrative summary is still violated 26 to 28% of the time, against 6 to 8% when framed as an active operator rule (E6, E15).
4. **Overwrite-style memory needs history.** Newest-value-wins stores fail questions about earlier values; a versioned store fixes this with no cost on current values (E4, E14).
5. **The failure is usually deletion of what comes next, not disorientation.** In E2 the goal is lost to recent work rather than resurrected; in E8 the plan disappears. Position trackers (ledgers, progress watchpoints) do not help when the plan is gone.
6. **Some old-paper claims did not survive.** The anchor prompt did not help goals (E2). The naive self-check failed on Space Bunny but looked fine on Nemotron (X1), so "self-verification is misleading" may be model-specific.
7. **Full context is not a perfect ceiling.** Full transcripts lost to compacted or pinned contexts on goals (E2) and rules (E15), consistent with distraction in long contexts. E12 tests this directly.

## Known issues that cut across studies

- **Provider outage.** From about 04:00 to 05:00 the provider returned empty 502 responses on more than half of all calls. Clients retried; several studies reran failed units from caches or cut sample sizes, as each README records.
- **Summary truncation.** The shared `compact` capped output at three tokens per word; about 7% of summaries were cut mid-sentence in studies started before 01:30. This applies equally to every arm within a study.
- **Decision parsing.** Replies that open with a bare `REFUSE_OR_ESCALATE` were unparsed before commit `f03b9bc`; studies re-parse raw replies leniently.
- **Self-labeled validation.** "Hand labels" were made by the study agents, which are language models, not by a human.
