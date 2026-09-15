# Long-running agents. Source ledger

Research cutoff September 13, 2026. The editable synthesis is `long-running-agents-research.docx`.

72 annotated source entries. Some entries group a paper with its implementation or first-party release. These are not 72 independent replications.

Performance figures are author-reported. Repository availability means inspected release evidence, not a successful local reproduction. Month-only dates are intentionally less precise than verified day-level dates.

## [A01] Prime Agent: A Self-Improving RLM Harness

Date. Paper August 24, 2026; launch blog August 5, 2026.

Evidence. Technical report and implementation.

Source. https://arxiv.org/html/2608.23552

Related original sources.
- https://www.primeintellect.ai/blog/prime-agent
- https://github.com/PrimeIntellect-ai/prime-agent

Finding. Persistent IPython, programmatic recursion, durable histories and editable harness state. Reports multi-day Factorio and nanoGPT runs.

Limit. ARC comparisons do not isolate a causal harness effect. nanoGPT final-record differences are within experimental noise. A separate Factorio trace preserves a cheating strategy as a skill.

## [A02] Recursive Language Models

Date. December 31, 2025; v3 May 11, 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2512.24601

Related original sources.
- https://arxiv.org/abs/2512.24601

Finding. Treat large inputs as external variables processed through code and recursive model calls. Studies both inference scaffolding and a trained small-model variant.

Limit. Long input is not long interactive autonomy. Benefits vary with information density, task and model. Recursive runs have costly tail behavior.

## [A03] Prime Agent runtime documentation

Date. Current documentation inspected September 13, 2026.

Evidence. Implementation contract.

Source. https://github.com/PrimeIntellect-ai/prime-agent/blob/main/packages/coding-agent/docs/long-running-agents.md

Related original sources.
- https://github.com/PrimeIntellect-ai/prime-agent/blob/main/packages/coding-agent/docs/rlm.md

Finding. Daemon sessions, goals, scheduling, compaction, restored subagent registry and persistent REPL ownership are separate mechanisms.

Limit. A REPL is not a security sandbox. Compaction survival is not complete process-restart survival. Unknown schedule delivery is not blindly replayed.

## [A04] Continual Harness

Date. arXiv submission May 11, 2026; inspected manuscript displays August 24.

Evidence. Research paper and project.

Source. https://arxiv.org/abs/2605.09998

Related original sources.
- https://sethkarten.ai/continual-harness

Finding. Online changes to prompts, skills, memory and subagents, plus teacher-assisted model–harness co-learning.

Limit. Capability-dependent gains. Smaller models can fall below the capability floor. Submission and manuscript dates differ.

## [H01] Anthropic: Effective harnesses for long-running agents

Date. November 26, 2025.

Evidence. Engineering account and example code.

Source. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

Related original sources.
- https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding

Finding. Initializer, explicit feature tests, incremental sessions, progress artifacts and end-to-end verification address premature completion and broken handoffs.

Limit. Web-app-oriented demonstration, not a randomized general reliability estimate.

## [H02] Anthropic: Effective context engineering for AI agents

Date. September 29, 2025.

Evidence. Engineering guidance.

Source. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

Finding. Just-in-time retrieval, compaction, structured notes and isolated subagent contexts are complementary tools.

Limit. Recommendations are not controlled causal effect estimates; context-retention requirements depend on the task.

## [H03] Anthropic: Building a C compiler with a team of parallel Claudes

Date. February 5, 2026.

Evidence. Engineering experiment and generated artifact.

Source. https://www.anthropic.com/engineering/building-c-compiler

Related original sources.
- https://github.com/anthropics/claudes-c-compiler

Finding. 16 agents, nearly 2,000 sessions and roughly $20,000 in API costs produced a compiler over two weeks. Oracle-based test partitioning enabled parallel debugging.

Limit. Human-designed and revised evaluation harness. Generated compiler has substantial limitations, including an external compiler dependency for one boot stage. Not proof of unsupervised general software delivery.

## [H04] Anthropic: Measuring AI agent autonomy in practice

Date. February 18, 2026.

Evidence. Observational deployment study.

Source. https://www.anthropic.com/research/measuring-agent-autonomy

Finding. 99.9th-percentile interactive turn duration rose from under 25 to over 45 minutes between late 2025 and early 2026; median around 45 seconds.

Limit. Selected tail, not typical runtime or causal model capability. User oversight and task choice change with experience.

## [H05] OpenAI: Run long-horizon tasks with Codex

Date. February 23, 2026.

Evidence. Engineering demonstration.

Source. https://developers.openai.com/blog/run-long-horizon-tasks-with-codex

Related original sources.
- https://github.com/derrickchoi-openai/design-desk

Finding. Approximately 25-hour design-application run, 13 million tokens and 30,000 lines of output.

Limit. Author explicitly says the result was not production-ready. Runtime and output volume are not reliability metrics.

## [H06] Cursor: Scaling long-running autonomous coding

Date. January 14, 2026.

Evidence. Engineering account.

Source. https://cursor.com/blog/scaling-agents

Finding. Flat locks and shared coordination underperformed; planner–worker separation and fresh judge cycles helped. An integrator role became a bottleneck and was removed.

Limit. Week-scale generated projects are demonstrations, not matched-budget estimates of useful completion.

## [H07] Cognition: Multi-Agents: What's Actually Working

Date. April 22, 2026.

Evidence. Engineering account.

Source. https://cognition.ai/blog/multi-agents-working

Finding. One writer with independent-context advisory/review agents. Weak lead plus stronger advisor failed when the lead could not decide when or what to ask.

Limit. Internal observations, not randomized proof. Reported review findings lack a full precision estimate.

## [H08] Cognition: Local Fusion

Date. September 11, 2026.

Evidence. Product release with reported evaluations.

Source. https://cognition.ai/blog/local-fusion

Finding. Lead and cheaper sidekick maintain separate persistent contexts. Reported Fable pair costs $7.90 versus $12.36, with score 61.7 versus 62.2.

Limit. Other pairings lose more score. Lower cost is not unchanged capability. Product/evaluation setup matters.

## [H09] Sakana Fugu technical report and release

Date. Report June 19, 2026, revised June 23; general availability June 22.

Evidence. Technical report and product.

Source. https://arxiv.org/html/2606.21228v2

Related original sources.
- https://sakana.ai/fugu-release/
- https://sakana.ai/fugu/

Finding. Learned worker routing and workflow generation. Isolates tool trajectories within a workflow, shares prior history across workflows.

Limit. Provider baselines are not uniformly matched. Simpler Fugu beats Ultra on some tasks. Public training weights/code not established.

## [H10] TRINITY: An Evolved LLM Coordinator

Date. December 4, 2025; revised April 27, 2026; ICLR 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2512.04695v3

Finding. Small evolved coordinator selects model and Thinker, Worker or Verifier role.

Limit. Primarily workflows capped at five steps. Not evidence of week-long execution.

## [H11] Learning to Orchestrate Agents in Natural Language with the Conductor

Date. December 4, 2025; revised May 6, 2026; ICLR 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2512.04388v5

Finding. GRPO-trained model generates assignments, instructions and communication access lists.

Limit. Mostly short workflows. Worker selection alone does not explain performance; instruction quality matters.

## [H12] Google AI co-scientist biomedical validation

Date. Nature, May 19, 2026.

Evidence. Peer-reviewed experimental study.

Source. https://www.nature.com/articles/s41586-026-10644-y

Finding. Generate, debate and evolve hypotheses, followed by expert selection and laboratory validation. Two of three selected fibrosis hypotheses showed activity in organoids.

Limit. Humans select hypotheses and conduct experiments. Narrow biological validation, not autonomous science without oversight. Full implementation unavailable.

## [H13] Poolside: Through the Looking Glass

Date. May 11, 2026.

Evidence. Incident analysis with upstream fixes.

Source. https://poolside.ai/blog/through-the-looking-glass

Finding. Investigates apparent SWE-bench Pro gains caused by reference-solution access through Git history and other channels.

Limit. Specific observed exploits. Anti-cheating prompts and known-hack detectors do not prove absence of unseen exploitation.

## [H14] Towards a Science of Scaling Agent Systems

Date. December 9, 2025; revised April 8, 2026.

Evidence. Controlled research paper and code.

Source. https://arxiv.org/html/2512.08296v3

Related original sources.
- https://github.com/ybkim95/agent-scaling

Finding. Across 260 configurations, multi-agent effects vary strongly by task decomposability, with large positive and negative relative effects.

Limit. Current fitted R-squared is 0.373. Coding subsets are small. Amplification ratios describe extra work, not failure probability.

## [M01] Grounding Agent Memory

Date. September 10, 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2609.11060v1

Finding. Read-only environment tools improve memory curation evidence. On the CLBench drift schedule, probing has 73% pass rate versus 70% trajectory-only memory and 39% no memory.

Limit. Five paired runs with wide intervals. Reported online dollar savings exclude curation cost. Experiment-specific code release not verified.

## [M02] MemGuard

Date. August 22, 2026.

Evidence. Research paper and Apache-2.0 core.

Source. https://arxiv.org/html/2608.21867v1

Related original sources.
- https://github.com/whyyyyy123/MemGuard

Finding. Persistent verification metadata affects memory admission, retrieval, revision and archival. Includes verifier-only controls and all-in token/latency accounting.

Limit. Verifier is imperfect. Released core does not bundle benchmark harnesses, data, runtimes or model clients.

## [M03] MemHarness

Date. July 30, 2026.

Evidence. Research paper, Apache-2.0 code and weights.

Source. https://arxiv.org/html/2607.28272v1

Related original sources.
- https://github.com/KnowledgeXLab/MemHarness
- https://huggingface.co/KnowledgeXLab/MemHarness

Finding. End-to-end RL learns to reconstruct retrieved experience for the current state. ALFWorld 85.2 versus GRPO-only 76.4; memory-disabled trained model still scores 83.0.

Limit. Most gain survives without inference-time memory. Not a training-free memory-system result. Actual license overrides conflicting README badge.

## [M04] Recuris

Date. August 25, 2026.

Evidence. Research paper and Apache-2.0 code.

Source. https://arxiv.org/html/2608.24876v1

Related original sources.
- https://github.com/Gen-Verse/Recuris

Finding. State-conditioned skill use and localized validated memory evolution improve 35 of 37 completed model–benchmark pairs in author results.

Limit. Within-task adaptation versus equal-attempt frozen retries is +2.3 points with an interval including zero. Authors do not claim adaptation was necessary.

## [M05] Harness the Memory

Date. August 15, 2026.

Evidence. Controlled substrate comparison.

Source. https://arxiv.org/abs/2608.15008

Finding. 11 substrates, three backbones, four benchmarks. Distilled strategies, sparse retrieval and no memory have different task-dependent outcomes.

Limit. No universal winner. Managed production memory systems excluded where auxiliary budgets differ. Code promised, not verified released.

## [M06] Agentic Context Engineering (ACE)

Date. October 6, 2025; v3 March 29, 2026.

Evidence. Research paper and Apache-2.0 code.

Source. https://arxiv.org/abs/2510.04618

Related original sources.
- https://github.com/ace-agent/ace

Finding. Generator, reflector and curator evolve playbooks using incremental deltas rather than whole-context rewriting.

Limit. Strong prior art for procedural memory evolution. Benchmark gains do not establish unrestricted durable improvement.

## [M07] A-MEM

Date. February 17, 2025; v11 October 8, 2025.

Evidence. Research paper and MIT code.

Source. https://arxiv.org/abs/2502.12110

Related original sources.
- https://github.com/WujiangXu/A-mem-sys

Finding. Structured notes, learned links and neighboring-memory updates.

Limit. Conversational memory results do not establish long-running action reliability.

## [M08] MemGPT

Date. October 12, 2023; v2 February 12, 2024.

Evidence. Foundational research paper.

Source. https://arxiv.org/abs/2310.08560

Finding. Model-directed tiered memory and context management.

Limit. Foundational architecture, not evidence that a particular current implementation dominates newer methods.

## [M09] Letta: Benchmarking AI agent memory

Date. August 2025.

Evidence. First-party benchmark analysis.

Source. https://www.letta.com/blog/benchmarking-ai-agent-memory

Finding. A filesystem-based agent with GPT-4o-mini reports 74.0% on LoCoMo, challenging substrate-only rankings.

Limit. Recall benchmark and particular harness/model setup. Not a universal result for files over retrieval systems.

## [M10] Mem0 paper and current implementation

Date. Paper April 28, 2025; implementation inspected September 13, 2026.

Evidence. Research paper and open implementation with managed service.

Source. https://arxiv.org/abs/2504.19413

Related original sources.
- https://github.com/mem0ai/mem0

Finding. Extraction, consolidation and retrieval with optional graph memory.

Limit. README says April 2026 advertised scores include proprietary managed-platform optimizations unavailable in OSS.

## [M11] Hindsight

Date. December 14, 2025.

Evidence. Research paper and MIT code.

Source. https://arxiv.org/abs/2512.12818

Related original sources.
- https://github.com/vectorize-io/hindsight

Finding. Retain, recall and reflect over facts, experiences, entity summaries and beliefs, including temporal retrieval.

Limit. Same-backbone score gains do not automatically imply matched total compute. Causal relations are not causal identification.

## [M12] Hindsight Memory-PRM

Date. August 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2608.29605

Finding. Deletion/re-answer counterfactuals and operation-conditioned critics shape memory management. Includes limited replay credit validation.

Limit. Final-entry presence is not a full action intervention. Domain-specific schemas and lossless storage limit forgetting claims. Direct benchmark transfer drops from 77.5 to 58.4.

## [M13] MemTX: Transactional Belief Commit for Stateful Agent Memory

Date. July 2026.

Evidence. Research paper with mechanical protocol checks.

Source. https://arxiv.org/html/2607.23929

Finding. Staging, commit validation, permission boundaries and typed cascading repair.

Limit. Recorded provenance only. Transcription and fresh-transaction retries bypass scope. Gate can be satisfied by unrelated beliefs. Compensation is logged, not real environmental replay.

## [M14] Invalidation Contracts for Cross-Episode Agent Memory

Date. September 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2609.00243

Finding. Version/cacheability contracts, row-level invalidation and dependency propagation. Seven models, roughly 9,400 episodes.

Limit. Declared dependencies and correct server information are prerequisites. Protocol validity and model compliance are different results.

## [M15] Fresh Memory, Stale Plans: Dependency-Scoped Validation for Distributed LLM-Agent Memory (PlanFence)

Date. September 2026.

Evidence. Research paper and controlled systems study.

Source. https://arxiv.org/html/2609.03340

Finding. Plans cite exact source records. Tool-boundary gate checks action-relevant versions, then replans or blocks. Thirty constructed live workflows plus replay studies of churn and cost.

Limit. Trusted complete tool-declared dependencies and owners. Validation point is not an atomic transaction spanning the external action. Not general task-accuracy evidence.

## [M16] EA-Graph: Artifact-Anchored Verification Memory for Coding Agents under Upstream Drift

Date. August 2026.

Evidence. Research paper and generated-world study.

Source. https://arxiv.org/html/2608.04278

Finding. Sub-path content anchors separate evidence from freshness and allow unaffected, affected and unprovable outcomes.

Limit. 42 sessions over seven generated worlds. Measures judgment, not code repair. Larger-model controls often reach ceiling. No efficiency or concurrency claim.

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

## [M19] CICL decision-aware memory cards

Date. June 2026, inspected v2.

Evidence. Research paper.

Source. https://arxiv.org/html/2606.08151v2

Finding. Cards rank evidence by estimated relevance to the next decision.

Limit. Small coding retrieval evaluation, not patch success. Generic extractive summaries beat typed cards on one repository benchmark slice. Counterfactual-inspired scoring is not identified causal effect.

## [M20] TRACE

Date. August 2026.

Evidence. Research paper, Nokia Applied Research and University of Virginia.

Source. https://arxiv.org/html/2608.06503

Finding. Paired closed-loop continuations optimize compaction for downstream execution. Loss of execution state causes repetition and failure to stop.

Limit. FIFO sometimes beats summaries when facts are refetchable. Repeated signatures do not necessarily mean wasted work in a changing environment. Limited transfer evidence.

## [M21] CHILL-Harness

Date. July 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2607.25825

Finding. Checkpointed paired continuations provide intervention signals to train adaptive harness orchestration with a frozen deployment policy.

Limit. State-sufficient replay is an assumption. Offline replay collection cost must be charged separately from reported inference cost. Checkpoint-based harness selection is not new.

## [M22] PM-Bench

Date. July 2026.

Evidence. Benchmark and code.

Source. https://arxiv.org/html/2607.12385

Related original sources.
- https://github.com/genglinliu/PMBench

Finding. Simulated seven-day Virtual Week tests delayed obligations, updates, hidden-channel checks and monitoring tradeoffs.

Limit. A simulated week is not a real week of runtime. No universally best Todo/heartbeat/hierarchical scaffold.

## [M23] TriggerBench

Date. June 2026.

Evidence. Benchmark and code.

Source. https://arxiv.org/html/2606.23459

Related original sources.
- https://github.com/KristenZHANG/TriggerBench-Official

Finding. Separates recalling an intention from acting when a cue arrives; tests positive, negative and overloaded triggers.

Limit. Strong retrospective recall can coexist with poor prospective behavior. More reasoning may cause false alarms rather than better discrimination.

## [M24] Prospective Intention Store

Date. September 1, 2026.

Evidence. Research paper.

Source. https://arxiv.org/abs/2609.01272

Finding. Typed trigger/action/status records with lifecycle handling and hidden-channel checks. Author reports 82.9% PM-Bench Set-F1 versus 67.7% own baseline.

Limit. One synthetic week. Side calls excluded from token accounting. Code release not verified. Executable obligations are existing prior art.

## [M25] The Sleeping Agent

Date. August 12, 2026.

Evidence. Diagnostic paper and MIT code.

Source. https://arxiv.org/abs/2608.11775

Related original sources.
- https://github.com/kyrkewood/sleeping-agent

Finding. Gist compression loses temporal details. One preservation instruction sharply improves temporal-expression retention.

Limit. Narrow conversational-memory diagnosis. Not evidence for biological-style sleep or continual improvement in action tasks.

## [M26] Don't Offer What Can't Be Done: Deterministic Executability Gating for LLM Skill Selection at Scale

Date. August 2026.

Evidence. Wix production analysis and counterfactual replay.

Source. https://arxiv.org/html/2608.01050

Finding. Semantic matching followed by deterministic skill precondition checks. Analyses 756,641 messages; gates 59.4% of matched skill–message pairs.

Limit. Predicate parity and fresh authoritative state required. Measures menu exposure and selected blocked skills, not downstream customer outcomes.

## [M27] Counterexample Guided Learning in the Large using Reasoning Agents

Date. June 2026.

Evidence. Controlled symbolic-learning research.

Source. https://arxiv.org/html/2606.11521

Finding. Verifier-generated counterexamples improve regular-expression induction and refinement.

Limit. Regex oracle setting, not arbitrary agent skills. Counterexample-guided synthesis and skill preconditions have older classical prior art.

## [M28] Last Step Matters: Early Uncertainty Cannot Predict Failure in Long-Horizon Agents

Date. August 2026.

Evidence. Research paper, Ant Group and Zhejiang University.

Source. https://arxiv.org/html/2608.29685

Finding. Five models and three deep-research benchmarks. Final confidence mean AUROC 0.85; no evaluated signal exceeds 0.60 halfway through a trajectory.

Limit. Search/visit agents with at most 80 tool calls, no compaction, model-judged final answers. Does not prove all early failure predictors are impossible.

## [B01] Terminal-Bench

Date. January 17, 2026.

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2601.11868

Finding. 89 containerized terminal tasks with executable final-state checks in version 2.0.

Limit. Most attempts under 20 minutes. Pin dataset and evaluator versions rather than mixing 2.0, 2.1 and newer product reports.

## [B02] LongDS-Bench

Date. May 28, 2026; revised September 5.

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2605.30434

Finding. 68 tasks, 2,225 turns, evolving analysis, counterfactual changes and rollback. Large early-to-late degradation.

Limit. Dependency/turn depth is not wall time. Reset analyses include heuristic choices, not a validated deployment policy.

## [B03] GAIA2

Date. February 12, 2026.

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2602.11964

Finding. Dynamic asynchronous environments with notifications, deadlines and state-changing actions; a 160-scenario mini is available.

Limit. Time scenarios capped at five minutes and simulated time can accelerate. Not multi-day endurance.

## [B04] MemoryArena

Date. February 18, 2026.

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2602.16313

Finding. Interdependent multi-session memory–agent–environment loops link recall to later action.

Limit. Some domains have floor effects. Multiple sessions do not by themselves establish long runtime.

## [B05] PaperBench

Date. April 2, 2025; revised April 7.

Evidence. Benchmark and original experiments.

Source. https://arxiv.org/html/2504.01848

Finding. Reproduce 20 research papers using executable rubrics, with 12-hour attempts and a 36-hour extension.

Limit. Rubric nodes are not independent tasks. Original attempts and grading were expensive. More runtime did not reliably translate into proportionate progress.

## [B06] Vending-Bench

Date. February 20, 2025.

Evidence. Benchmark and original experiments.

Source. https://arxiv.org/html/2502.15840

Finding. Persistent inventories, deliveries and cumulative business outcomes over roughly 5 to 10 real hours in original runs.

Limit. Business days are simulated. Small run counts and partly model-generated dynamics complicate comparisons.

## [B07] Factorio Learning Environment

Date. March 2025.

Evidence. Environment and benchmark paper.

Source. https://arxiv.org/html/2503.09617

Finding. Seeded persistent production world and long open-play trajectories with technological milestones.

Limit. Spatial/API capability can dominate harness effects. Steps are not hours; privileged APIs require careful scoring boundaries.

## [B08] METR task-completion time horizons

Date. Inspected page updated May 8, 2026.

Evidence. Independent evaluation methodology and current results.

Source. https://metr.org/time-horizons/

Finding. Measures human-expert task duration at a specified modeled agent success probability.

Limit. Not agent runtime. Current suite marks estimates above 16 hours unreliable. Software-heavy self-contained tasks do not imply deployment reliability.

## [B09] LongHorizon-Harness

Date. August 3, 2026.

Evidence. Research paper.

Source. https://arxiv.org/html/2608.01964

Finding. Manage–Execute–Audit with bounded fresh-context execution, explicit persistent state and read-only auditing.

Limit. Some gains cost 2.3 to 3.6 times the tokens; other tasks improve with fewer tokens. Auditor-supported state is not infallible verification.

## [B10] AARRI-Bench

Date. June 5, 2026.

Evidence. Benchmark paper.

Source. https://arxiv.org/html/2606.07462v1

Finding. Mini-SWE-Agent plus Opus 4.7 outscores richer harnesses in the reported configuration.

Limit. Mostly short runs, single-trial main protocol. Appendix documents a correct fabrication refusal failing a lexical scorer. Deterministic scoring can still be invalid.

## [B11] SWE-bench Pro Verified

Date. September 8, 2026.

Evidence. Evaluation-integrity research.

Source. https://arxiv.org/html/2609.08149

Finding. Reports a 21.48-point drop for one model after controls against solution leakage through repository and external channels.

Limit. Specific dataset and models; some attribution uses model annotations. Not a universal contamination adjustment.

## [O01] Letta Mods and Letta Code

Date. Mods announcement June 24, 2026.

Evidence. Product implementation and Apache-2.0 coding harness.

Source. https://www.letta.com/blog/introducing-mods/

Related original sources.
- https://github.com/letta-ai/letta-code
- https://github.com/letta-ai/letta-evals
- https://github.com/letta-ai/mods

Finding. Git-backed memory/context and agent-authored tools, commands and context/compaction modifications. Evals supports repeated runs and saved-trajectory regrading.

Limit. Ability to modify a harness is not evidence that modification improves it reliably.

## [O02] Nous Research Hermes Agent

Date. Current repository inspected September 13, 2026.

Evidence. MIT implementation.

Source. https://github.com/NousResearch/hermes-agent

Related original sources.
- https://nousresearch.com/

Finding. Persistent memory, skill creation/refinement, session search, isolated subagents, scheduling and execution backends.

Limit. No controlled cumulative self-improvement result established in this survey. Repository superlatives are promotional.

## [O03] Simular Sai OSWorld 2.0 report and Agent-S

Date. August 28, 2026 report.

Evidence. Product evaluation and separate Apache-2.0 research implementation.

Source. https://www.simular.ai/articles/sai-tops-osworld-2-0

Related original sources.
- https://github.com/simular-ai/Agent-S
- https://arxiv.org/abs/2510.02250

Finding. Sai reports 73% partial score, $15.70 per task and 28.25% binary success.

Limit. Partial credit is not completion. Sai production scores are not automatically reproducible with the separate open Agent-S release.

## [O04] Mechanize GBA Eval

Date. Announcement May 11, 2026.

Evidence. Applied-lab benchmark.

Source. https://gbaeval.com/blog/announcement/

Related original sources.
- https://gbaeval.com/
- https://www.mechanize.work/

Finding. Implement a Game Boy Advance emulator from scratch within 24 hours, graded against Mesen2.

Limit. Public benchmark does not establish that full evaluator/harness code is open. Executable grader quality remains central.

## [Y01] Assemble, YC Summer 2026

Date. Batch and product verified September 13, 2026.

Evidence. Verified YC membership and product description.

Source. https://www.ycombinator.com/companies/assemble

Related original sources.
- https://www.assemble.ai/

Finding. Enterprise IT agents with dependency scoping, validation, change ledger and differentiated rollback/compensation.

Limit. Product demo, not controlled productivity evidence. Backend openness not established.

## [Y02] Inkbox, YC Summer 2026

Date. Batch and product verified September 13, 2026.

Evidence. Verified YC membership, docs and integration code.

Source. https://www.ycombinator.com/companies/inkbox

Related original sources.
- https://inkbox.ai/llms.txt
- https://github.com/inkbox-ai/claude-code-plugin

Finding. Persistent agent identity and communication through email, phone, iMessage, tunnels and scoped keys.

Limit. Identity continuity is not durable computation. Public plugin is not the full hosted backend.

## [Y03] Archal, YC Summer 2026

Date. Batch and product verified September 13, 2026.

Evidence. Verified YC membership and technical documentation.

Source. https://www.ycombinator.com/companies/archal

Related original sources.
- https://docs.archal.ai/introduction

Finding. Resettable stateful API simulations for agent integration testing and RL.

Limit. Independently built simulations, not live upstream services or complete provider coverage. Transfer fidelity must be tested.

## [Y04] hiloop, YC Summer 2026; Search is enough

Date. Technical post July 2, 2026; batch verified September 13.

Evidence. Verified YC membership and company-run experiment.

Source. https://hiloop.ai/blog/search-is-enough/

Related original sources.
- https://www.ycombinator.com/companies/hiloop

Finding. 4,188 training-recipe experiments over two days using 50 B200s; 25 paired confirmation runs for the reported final result.

Limit. Large search budget, narrow task and selected human direction. Complete campaign reproduction release not established.

## [Y05] Akon Labs / GitNexus, YC Summer 2026

Date. Batch, benchmark and license verified September 13, 2026.

Evidence. Verified YC membership, company benchmark and source-available code.

Source. https://www.ycombinator.com/companies/akon-labs

Related original sources.
- https://www.akonlabs.com/benchmarks
- https://github.com/abhigyanpatwari/GitNexus
- https://github.com/abhigyanpatwari/GitNexus/blob/main/LICENSE

Finding. Repository graph captures symbols, calls, imports, ownership and history for agent retrieval.

Limit. Company's 68.37 versus 36.99 comparison needs independent reproduction; raw trajectories require contact. PolyForm Noncommercial 1.0.0 is not unrestricted OSS.

## [Y06] Jcode, YC Summer 2026

Date. Batch and implementation verified September 13, 2026.

Evidence. Verified YC membership and MIT implementation.

Source. https://www.ycombinator.com/companies/jcode

Related original sources.
- https://jcode.sh/
- https://github.com/1jehuang/jcode

Finding. Rust coding harness emphasizing low per-session process memory, with measurement scripts and transcripts.

Limit. Reported approximately 10.4 MB additional PSS versus 212.7 MB is resource use in its setup, not a productivity multiplier.

## [Y07] Screenpipe, YC Summer 2026

Date. Batch and current license verified September 13, 2026.

Evidence. Verified YC membership and source-available product.

Source. https://www.ycombinator.com/companies/screenpipe

Related original sources.
- https://github.com/screenpipe/screenpipe
- https://github.com/screenpipe/screenpipe/blob/main/LICENSE.md

Finding. Local screen/accessibility/audio history searchable by agents.

Limit. Current commercial license restricts use; earlier MIT releases differ. Product privacy claims are not an independent audit. Capture requires consent and minimization.

## [Y08] Orchestra, formerly Understudy, YC Summer 2026

Date. Batch and product verified September 13, 2026.

Evidence. Verified YC membership and product description.

Source. https://www.ycombinator.com/companies/orchestra

Related original sources.
- https://orchestra.ai/

Finding. Production traces and corrections feed held-out evaluations and model/specialist promotion.

Limit. 100-times pitch is not a universal finding. Reported case-study savings and backend implementation are not independently reproduced.

## [N01] Google Research: Titans and MIRAS

Date. Blog December 4, 2025; Titans paper January 2025.

Evidence. Architecture research and first-party explanation.

Source. https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/

Related original sources.
- https://arxiv.org/abs/2501.00663

Finding. Learn neural memory during inference, with retention and surprise-sensitive updates; MIRAS unifies associative-memory design choices.

Limit. Long-sequence language/recall results are not week-long tool-use reliability. Not a drop-in capability of an arbitrary hosted model.

## [N02] Google Research: Nested Learning and HOPE

Date. November 7, 2025; NeurIPS 2025.

Evidence. Architecture research and first-party explanation.

Source. https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/

Finding. Multiple optimization timescales and continuum memory modules in a proof-of-concept self-modifying architecture.

Limit. Does not demonstrate general deployed continual learning without forgetting or eliminate the need for exact external records.

## [N03] End-to-End Test-Time Training for Long Context

Date. Paper December 2025; NVIDIA post January 9, 2026.

Evidence. Research paper, code and technical post.

Source. https://developer.nvidia.com/blog/reimagining-llm-memory-using-context-as-training-data-unlocks-models-that-learn-at-test-time/

Related original sources.
- https://arxiv.org/abs/2512.23675
- https://github.com/test-time-training/e2e

Finding. Meta-learn initialization for next-token test-time training. Reports 2.7-times latency advantage at 128K and 35-times at 2M in a matched 3B-model experiment.

Limit. Meta-training is 3.4 times slower at 8K in the reported implementation. Sequence-model result, not observed long-running agent success.

## YC batch exclusions

Runtime is Spring 2026. https://www.ycombinator.com/companies/runtime

Maritime is Fall 2026. https://www.ycombinator.com/companies/maritime

These pages were inspected on September 13, 2026. They are excluded from the Summer 2026 shortlist.
