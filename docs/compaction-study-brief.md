# Context Compaction in Long-Running Coding Agents: Research Brief

Date: 2026-09-14. Status: direction settled, pre-registration not yet written, no experiments run.

## 1. Background

A coding agent works by repeatedly choosing an action (read a file, run a command, edit code), observing the result, and deciding again. Everything it has seen and done accumulates in its context window, which is the only thing the model can see when it decides. On a task that runs for hours, that history grows past what the model can hold.

When it does, the harness must shrink it. That step is context compaction. The common approach is to ask a model to summarize the older part of the history into a few paragraphs, keep the most recent turns verbatim, and continue. Whatever the summary omits is gone unless the agent rediscovers it from the repository or by redoing work.

Compaction rarely fails loudly. The agent keeps going with a degraded picture of where it is. That is why its cost is hard to see and why task completion rate alone does not capture it.

Three kinds of loss are known from short-task studies:

- Repeated work. The agent rereads files it already read, reruns commands whose results still hold, or retries an approach it already ruled out.
- Dropped constraints. Session instructions such as "do not modify test files" are dropped by summarizers that optimize for narrative progress. Two 2026 studies measured 17% and 53% retention after one compaction on short traces.
- Tool-state errors. Branch, environment, and background-process state set up by the agent is not recorded, so post-compaction commands run against the wrong state.

All of this has been measured on tasks that run minutes, with one or two compaction events. Nobody in the sources we have read has measured it on coding tasks that run one to four hours with repeated compaction, which is the regime where long-running agents actually operate.

## 2. What we are researching

The effect of compaction strategy and compaction timing on a single long-running coding agent, measured on multi-hour coding tasks, using frozen frontier models and harness-level changes only.

The unit of study is a compaction event. At each event we fork the run and continue under different compaction strategies from the identical state, then measure what each strategy loses in the following window of actions. This is the boundary-local design used by TRACE, applied to coding tasks at long horizons.

Out of scope: multi-agent orchestration, self-modifying environments, cross-session memory, and any method requiring model training.

## 3. Hypotheses

H1. On multi-hour coding tasks with repeated compaction, prompted summarization increases repeated work, dropped constraints, and tool-state errors relative to a full-context reference, and these losses grow with the number of compaction events.

H2. Observation masking is regime-dependent on long coding tasks. The May 2026 regime map (Zhang et al.) found masking helps mid-capacity models and collapses when the model is saturated, on search agents. The 2025 Complexity Trap result found it matched summarization on SWE-bench. Multi-hour coding with frontier models is where those two predictions diverge, and neither has been tested there. Either outcome is informative.

H3. Harness-verified compaction timing (compact when tests pass or a subtask closes, as observed by the harness) loses less than a token threshold on coding tasks with frontier models. SelfCompact (Jun 2026) already showed model-judged semantic timing beats fixed thresholds on math and search with open models. Our test is whether the effect holds on coding with frontier models, and whether a harness-verified trigger matches or beats the model's own judgment.

H4. At least one of four harness-level fixes reduces the primary loss relative to the default without increasing per-event cost beyond a small bound.

A pre-registered null on H1 through H3 is a publishable result. It would place long-horizon coding on the masking regime map and redirect effort away from compaction machinery.

Observational evidence that the effect exists: a trace study of 873 real Claude Code compactions (LangWatch, Aug 2026) found the median event shrinks 575k tokens to 4.4k and the agent re-ingests context above its steady rate for about 28 steps afterward. That study cannot attribute the cost to strategy or timing. Ours is designed to.

## 4. Publications we build on and how we differ

| Work | What it established | How we differ |
|---|---|---|
| TRACE (Aug 2026) | Paired closed-loop continuations from the same state to evaluate individual compaction events. Used offline to tune a compression prompt. AppWorld, 4k window, 50 steps, open models. | Same measurement idea, applied to coding tasks at one to four hours with frontier models. We also test the paired check online as a fix, not only as an offline tuning signal. |
| Lost in Compaction (Jul 2026) | Session constraints retained at 17% on average across compactors. Plug-in extractor restores over 90%. Chat, short agentic traces, research tasks. | We inject constraints into multi-hour coding runs and measure retention across repeated compaction events. |
| Compaction Cliff (Aug 2026) | Claude Code's compactor keeps 53% of safety rules after one round, 10% after five. Typed retention policy fixes it. Production agent configs, not live runs. | We measure the same loss inside live long-running tasks and treat typed retention as a control arm rather than a contribution. |
| Governance Decay / ConstraintRot (Jun 2026) | Seven models, 1,323 episodes. One compaction raises pooled violation from 0% to 30%, up to 59%. Constraint survives: 0% violation. Dropped: 38%. Compounds to 78% over four rounds. Constraint Pinning restores 0% for about 47 tokens. Enterprise tool-call tasks, not coding. | Same loss class inside multi-hour coding runs. Constraint Pinning is a control arm for us, not a contribution. |
| SelfCompact (Jun 2026) | Model decides when to compact via a tool plus a rubric (fire when a subtask resolves, suppress mid-derivation). Training-free. Matches or beats fixed-interval at 30 to 70% lower cost on math and agentic search, seven open-weight models. Frontier models and coding excluded by the authors. | Coding with frontier models. Harness-verified triggers (test results, checkpoints) compared against the model's rubric judgment. Timing is no longer our headline; it is one arm. |
| LangWatch trace study (Aug 2026) | 873 real Claude Code compactions. Median 575k to 4.4k tokens, 142 s per event, about 28 steps of elevated re-ingestion afterward. Cost model suggests compacting around 220k to 450k. | Observational, single user, no arms. We attribute the same fog to strategy and timing with controlled forks. |
| Masking regime map (Zhang et al., May 2026) | Observation masking's benefit follows an inverted U against model capacity: plateau with weak retrievers (+6 to 7), peak for mid-capacity models (+11.7), harm when saturated (−1.1 offline, −4.8 on GAIA). Tool calls surge under masking for strong models. Search agents, open-weight 4B to 284B, frontier omitted. Authors name SWE code localization as untested. | We test which regime multi-hour coding with frontier models falls into. Coding has no retriever, so the mechanism may differ. |
| Complexity Trap (Lindenbauer et al., 2025) | Origin of the masking-matches-summarization result on SWE-bench at half the cost. Still cited as an open question by Ledger (Aug 2026). | Historical anchor for H2. The regime map is the frontier statement we build on. |
| Ledger (Aug 2026) | Deterministic execution state (observed, modified, attempted) derived from the trajectory, injected before each step. +5 to +8 points on SWE-bench Verified, no extra model calls. Never touches compaction. | We reuse its state extraction as a loss detector and test its execution state as compaction content (the state-anchored summary fix). |
| Interaction cost paper (Aug 2026) | Under compression, retrieval tool calls triple while completion is statistically unchanged. Bounded-horizon planning environment. | We adopt the retrieval-versus-execution decomposition as a secondary metric on real coding tasks. |
| Measure Before You Manage (Aug 2026) | On 55 coding trajectories, working-memory objects have different retention profiles, and compression calibration does not transfer to held-out tasks. | Motivates measuring on held-out tasks and reporting per-object-type loss. We run live forks rather than replaying archives. |
| Scroll (Aug 2026) | Lossless event log plus Python kernel; evicted spans stay recoverable. QA and memory benchmarks. | Reversible archive is a control arm on coding tasks, not a contribution. |
| CompactionRL, ACM, ContextPilot (2026) | Training the model to compact or manage context. | We stay inference-only. These set the ceiling our harness-only results can be compared against. |

The gap we fill: no published study measures compaction loss on coding tasks long enough for compaction to fire repeatedly, with frontier models, using a design that attributes loss to the compaction event itself. The fixes we test borrow established components (paired continuation, execution state, semantic timing) and place them at the compaction boundary on coding tasks, where none has been tested.

Gap check performed 2026-09-14: bounded searches over arXiv and Exa for June to September 2026 combining compaction, coding agents, long horizon, and evaluation. Closest matches are TRACE, SelfCompact, the LangWatch trace study, Governance Decay, and the interaction-cost paper, each covering one axis but not the combination. This does not guarantee absence. Repeat before the pre-registration is committed.

## 5. Plan

Harness: Pi, using its `session_before_compact` hook to swap strategies and its JSONL sessions plus git snapshots as fork points. Pi is used as a harness in at least three recent papers (Harness-of-Harness, Prime Agent, CapScope).

Tasks: Long-Horizon-Terminal-Bench (46 tasks, mean 85 minutes and 9.9M tokens per run, dense subtask grading, built to stress context management), plus long-duration Terminal-Bench 2.x tasks and FrontierSWE. About ten for the pilot, thirty to fifty for the main run. Two backbones, one Anthropic and one OpenAI.

Reference: compaction is triggered at a deliberately low fraction of the context window so a full-context continuation exists as the reference. The threshold level is a pilot variable, not a fixed choice.

Phase 1, existing strategies:

- Full-context reference
- Pi default prompted summary
- Observation masking
- Appendix subset: typed summary, Constraint Pinning, reversible archive

Phase 2, pre-registered fix candidates, each alone on top of the default:

- Compaction gate: compact early while full context exists, run a short paired continuation, recompact with the divergence as instruction if the continuations disagree.
- State-anchored summary: build the summary from workspace diff, command results, test status, and branch rather than from the transcript.
- Boundary-triggered compaction: compact at harness-verified checkpoints with a threshold fallback. Compared against SelfCompact's model-judged rubric as a second timing arm.
- Post-compaction re-verification: rerun tests after compaction and inject the real result.

The pilot runs all four. The two with the largest reduction in the primary metric versus default, ties broken by cost per event, go to the main run. This rule is written before the pilot.

Metrics, all computed from logs:

- Primary: repeated-work rate per window (identical reads, identical commands, retried ruled-out approaches).
- Secondary: dropped-constraint rate on an injected subset, tool-state errors, retrieval share of tool calls, tokens per window.
- Optional end-to-end check on about ten tasks if boundary-local effects are strong.

Settled by the pilot, not now: fork window length, threshold levels, number of seeds.

Pre-registration: a short committed document written before the main run stating the above plus the stopping condition. The pilot is exempt from it by design.

## 6. Known risks

- Task pool. Long-Horizon-Terminal-Bench averages 85 minutes per run, which largely settles this, but its 46 tasks cap the main run size unless Terminal-Bench 2.x and FrontierSWE supply the rest.
- Frontier models may flatten every difference on completion. The interaction-cost metrics exist for this case.
- The low-threshold regime is artificial. Relative comparisons should hold; absolute loss at a full window may differ. A threshold sweep on a subset is the planned check.
- Another group may publish a similar comparison first. Pre-registration and the long-horizon focus are the protection.

## Sources

See SOURCES.md in this folder for the full ledger. Primary sources for this brief: arXiv 2608.06503 (TRACE), 2608.11242 (Lost in Compaction), 2608.22752 (Compaction Cliff), 2606.22528 (Governance Decay), 2606.00408 (masking regime map), 2606.23525 (SelfCompact), 2607.08964 (Long-Horizon-Terminal-Bench), langwatch.ai/blog/context-tax-when-to-compact (trace study), 2508.21433 (Complexity Trap), 2608.00808 (Ledger), 2608.16370 (interaction cost), 2608.31057 (Measure Before You Manage), 2608.21690 (Scroll), 2607.05378 (CompactionRL), 2607.23809 (ACM), 2608.28476 (ContextPilot).
