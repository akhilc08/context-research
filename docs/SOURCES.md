# Long-running agents. Source ledger

Research cutoff September 13, 2026. The editable synthesis is `long-running-agents-research.docx`.

This ledger originally covered 72 sources on long-running agents broadly (harness engineering, multi-agent orchestration, memory architectures, benchmarks, and YC products). It has been trimmed to the entries that bear directly on context compaction — what gets lost when an agent's history is summarized or evicted, and how that loss is measured or mitigated. Original entry IDs are kept as written (gaps in numbering mark removed entries) so they stay traceable to the source docx.

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
