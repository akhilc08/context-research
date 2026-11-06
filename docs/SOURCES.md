# Long-running agents. Source ledger

Research cutoff September 13, 2026. The editable synthesis is `long-running-agents-research.docx`. The last section, on rule changes, delegation, and compaction, was added on November 5, 2026 for `studies/subagent-rule-updates/`.

This ledger originally covered 72 sources on long-running agents broadly (harness engineering, multi-agent orchestration, memory architectures, benchmarks, and YC products). It has been trimmed to the entries that bear directly on context compaction. These entries cover what gets lost when an agent's history is summarized or evicted and how that loss is measured or mitigated. Original entry IDs are kept as written (gaps in numbering mark removed entries) so they stay traceable to the source docx.

Performance figures are author-reported. Repository availability means inspected release evidence, not a successful local reproduction. Month-only dates are intentionally less precise than verified day-level dates.

Note: this ledger is a separate, broader survey and largely does not overlap with the specific papers cited inline in `compaction-study-brief.md`'s own Sources section (TRACE is the one exception, entry [M20] below). Treat the two source lists as complementary, not duplicates.

## [H02] Anthropic: Effective context engineering for AI agents

Date. September 29, 2025.

Evidence. Engineering guidance.

Source. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

Finding. Just-in-time retrieval, compaction, structured notes and isolated subagent contexts are complementary tools.

Limit. Recommendations are not controlled causal effect estimates; context-retention requirements depend on the task.

## [M17] From Faulty Memories to Corrected Actions: Dependency-Guided Rollback Repair

Date. August 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2608.10502

Finding. Typed memory-to-action graph, independent-support checks, quarantine and selective replay. 150 controlled cases plus 50 adapted trajectories.

Limit. Fault diagnosis supplied upstream and runtime provenance assumed. Highest immediate recovery is not lowest recurrence or uniformly better reconstruction.

## [M18] What Eviction Destroys: Restore-Counterfactual Audit of Forgetting

Date. September 2026.

Evidence. Diagnostic research paper.

Source. https://arxiv.org/html/2609.08279

Finding. Restoring gold evidence separates evicted information, retrieval misses and reader-utilization errors.

Limit. Gold restoration is diagnostic, not a deployable oracle. QA outcomes do not measure corrected external actions.

## [M20] TRACE

Date. August 2026.

Evidence. Research paper, Nokia Applied Research and University of Virginia.

Source. https://arxiv.org/html/2608.06503

Finding. Paired closed-loop continuations optimize compaction for downstream execution. Loss of execution state causes repetition and failure to stop.

Limit. FIFO sometimes beats summaries when facts are refetchable. Repeated signatures do not necessarily mean wasted work in a changing environment. Limited transfer evidence.

## [M25] The Sleeping Agent

Date. August 12, 2026.

Evidence. Diagnostic paper and MIT code.

Source. https://arxiv.org/abs/2608.11775

Related original sources.
- https://github.com/kyrkewood/sleeping-agent

Finding. Gist compression loses temporal details. One preservation instruction sharply improves temporal-expression retention.

Limit. Narrow conversational-memory diagnosis. Not evidence for biological-style sleep or continual improvement in action tasks.

## [B01] Terminal-Bench

Date. January 17, 2026.

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2601.11868

Finding. 89 containerized terminal tasks with executable final-state checks in version 2.0.

Limit. Most attempts under 20 minutes. Pin dataset and evaluator versions rather than mixing 2.0, 2.1 and newer product reports.

## Rule changes, delegation, and compaction

Added November 5, 2026. These sources bear on `studies/subagent-rule-updates/`. Most are 2026 preprints. R01 to R03 were read in full. The rest are summarized from abstracts and excerpts.

## [R01] Do Agents Still Follow the Rules? (ARCBench)

Date. November 2, 2026.

Evidence. Benchmark paper, code at https://github.com/VUAISec/ARCBench (no license stated).

Source. https://arxiv.org/abs/2611.03223

Finding. Built on the pi harness with action-scored tool calls. Most violations after compaction happen while the rule is still in the summary. Runs that keep the rule still violate 2.6 times as often as full-history runs. Its strongest defense, rule preservation, is close to our re-insertion baseline.

Limit. Single agent, one compaction, rules never amended, tools return canned results.

## [R02] MasDrift: Authorization Preservation Across Multi-Agent Architectures

Date. August 2026 (arXiv 2608.07556).

Evidence. Benchmark paper, code at https://github.com/ZhuoningXu/MasDrift.

Source. https://arxiv.org/abs/2608.07556

Finding. 600 tasks and 90,000 runs. Supervisor hierarchies raise unauthorized actions from about 1% (single agent) to up to 19.8%. 72% of constraint losses happen at the first handoff. Each handoff is labeled preserved, weakened, or absent, with a lost-at-hop attribution. Re-anchoring every call to the original request works better than carrying policy down the chain.

Limit. No compaction, and rules never change mid-session. Handoff labels come from an LLM judge (kappa 0.85 against humans).

## [R03] When Do Summaries Become Instructions? Unsupported Policy in Self-Written Handoff Summaries

Date. November 4, 2026.

Evidence. Research paper, code at https://github.com/Chuw1/handoff-audit.

Source. https://arxiv.org/abs/2611.06545

Finding. Compaction summaries sometimes state permissions or restrictions the record does not support, and false approvals raise unauthorized actions (24 to 7 of 120 runs when neutralized, post hoc). The method is same-snapshot replay: restore the compaction point, replace only target sentences with neutral filler, and rerun the successor several times per arm.

Limit. Single agent, 8B to 20B open-weight models, small and partly post hoc effects.

## [R04] Faithful, Not Corrective: Message-Format Effects in Multi-Hop Agent Relays

Date. July 2026 (arXiv 2607.09678).

Evidence. Research paper.

Source. https://arxiv.org/html/2607.09678

Finding. A strong relay model keeps nearly all facts over six hops in every format, and what loss exists happens at the first encoding. A weak relay loses 18 to 37 points. Once an error is injected, every format carries it forward.

Limit. Facts, not standing rules. Relays are told to copy faithfully, unlike a manager writing task briefs.

## [R05] PerspectiveGap: A Benchmark for Multi-Agent Orchestration Prompting

Date. June 2026 (arXiv 2606.08878).

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2606.08878v1

Finding. Orchestrators writing subagent prompts omit shared background 12% to 45% of the time and leak out-of-role information, even without compaction. Prompts are scored by a rule-based check of which required fragments are present.

Limit. Prompt writing only. No subagent execution.

## [R06] Delegated Misalignment: How Multi-Agent Structures Amplify LLM Safety Risks

Date. September 2026 (EMNLP 2026).

Evidence. Research paper.

Source. https://arxiv.org/html/2609.27900

Finding. Subordinate agents comply with upstream instructions more readily than with direct prompts (GPT-5: 22.5% harmful execution alone against 61.2% as a subordinate).

Limit. Harmful requests, not rule changes or compaction.

## [R07] Governance Decay: Context Compaction Erases Safety Constraints

Date. June 2026 (arXiv 2606.22528).

Evidence. Research paper.

Source. https://arxiv.org/abs/2606.22528

Finding. Compaction raises violations from 0% to 30% across seven models. When the constraint survives the summary, violations are 0%. Constraint Pinning restores 0% at under 0.5% token overhead.

Limit. Single agent, constraints never amended.

## [R08] Lost in Compaction: Side-Constraint Loss under Context Compaction (CompInt)

Date. July 31, 2026.

Evidence. Research paper, code at https://github.com/ZhiqiEliWang/compaction-integrity.

Source. https://arxiv.org/html/2608.11242v1

Finding. Compactors retain 17% of injected session constraints on average. A constraint extractor running beside the compactor retains over 90%.

Limit. Measures retention in summaries more than executed behavior. Single agent.

## [R09] InterventionBench: Can LLM Agents Adapt to Mid-task User Interventions?

Date. 2026 (EMNLP 2026 Findings).

Evidence. Benchmark paper, code at https://github.com/jhn25/InterventionBench.

Source. https://aclanthology.org/2026.findings-emnlp.698/

Finding. 2,250 mid-task goal revisions in AppWorld and WebArena, typed as add, swap, or drop. Add is hardest. Failing agents still restate the original goal but do not act on it.

Limit. Goals, not standing rules. Single agent, no compaction.

## [R10] InterruptBench: Evaluating Interruptible Agents in Long-Horizon Web Navigation

Date. April 2026 (arXiv 2604.00892).

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2604.00892

Finding. Mid-task additions, revisions, and retractions in WebArena-Lite all reduce success.

Limit. Goals, single agent, no compaction.

## [R11] MTAC-IFBench: Instruction-Following in Multi-Turn Agentic Coding

Date. September 2026 (arXiv 2609.14992).

Evidence. Benchmark, data at https://huggingface.co/datasets/thu-coai/MTAC-IFBench (license not found).

Source. https://www.alphaxiv.org/abs/2609.14992

Finding. 100 coding sessions with a CLAUDE.md policy and per-turn constraints that later turns add, revise, or override, each with a Python workspace check. Compliance falls over turns.

Limit. Single agent, no compaction.

## [R12] Harness-IF: Instruction Following Across Instruction Surfaces in Coding Agents

Date. August 2026 (arXiv 2608.11727).

Evidence. Benchmark paper (rule library not found online).

Source. https://www.alphaxiv.org/abs/2608.11727

Finding. Scores rules separately by where they are delivered. Against-Prior Accuracy counts only rules that oppose the model's default, which lowers every model's score by 3.6 to 7.4 points.

Limit. No rule changes or compaction.

## [R13] AgentCollabBench: Diagnosing When Good Agents Make Bad Collaborators

Date. May 2026 (arXiv 2605.08647).

Evidence. Benchmark, code at https://github.com/aritra741/AgentCollabBench.

Source. https://arxiv.org/html/2605.08647

Finding. Communication topology explains 7% to 40% of constraint survival across hops. Agents merging several inputs drop constraints carried by a minority branch.

Limit. Stateless workers, text scoring, no compaction.

## [R14] ClawArena-Team

Date. June 2026 (arXiv 2606.31174).

Evidence. Benchmark, code at https://github.com/aiming-lab/ClawArena.

Source. https://arxiv.org/html/2606.31174v2

Finding. A main agent creates and resumes persistent subagents with executable checks.

Limit. Mid-task updates reach the main agent, not workers. No compaction.

## [R15] Benchmarks Are Surprisingly Compaction-Friendly

Date. October 22, 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2610.31778

Finding. The first summary on ProgramBench drops about a third of anti-cheating rules, rising with each compaction. In SWE-chat sessions, instructions about how to work are dropped about 6 times as often as specifications of what to build.

Limit. Measures dropped constraints in summaries more than their effect on actions.

## [R16] Context compaction in agent frameworks (CrabTalk survey) and AutoGen CompressibleGroupManager

Date. March 11, 2026 (survey).

Evidence. Practitioner survey and framework code.

Source. https://crabtalk.ai/blog/context-compaction

Finding. AutoGen's CompressibleGroupManager is the one production pattern where a manager compacts a shared history and broadcasts one summary to every agent. The survey calls it a single point of failure for context quality.

Limit. Design description. No measurement.

## [R17] Codex and pi compaction implementations

Date. Checked November 5, 2026.

Evidence. Source code.

Source. https://github.com/openai/codex/blob/main/codex-rs/core/src/compact.rs

Finding. Codex rebuilds history as a summary plus earlier user messages kept verbatim, newest first, up to 20,000 tokens. pi 1.5.0 keeps the most recent 20,000 tokens verbatim and summarizes the rest with a structured prompt that has a Constraints & Preferences section.

Limit. Implementation behavior can change between releases.
