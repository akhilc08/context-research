# Potential Research Idea: Repair-Compute vs. Retention-Compute Crossover in Compaction Fidelity

Date: 2026-09-18. Status: candidate direction from an external idea-generation and diversity-aware ranking pass (Elo-scored, selected as "divergent" in a top-3), not yet checked against the literature by this repo's own research process. No experiments run, not yet chosen for the main study.

See [`../paper-plan.md`](../paper-plan.md) (idea B) for this idea's concretized benchmark, baseline, and proposed-method design, ranked as a strong second submission candidate.

## Relationship to the compaction study

Candidate offshoot of [`../compaction-study-brief.md`](../compaction-study-brief.md), and a sharper, more mechanistic version of that brief's own H4 fix candidates and this folder's verification-cost question. It also refines a distinction TRACE's own notes gesture at without measuring precisely (see [`../trace-notes.md`](../trace-notes.md) section 2, "deletion" vs. "disorientation").

## Problem and gap

Coding agent frameworks spend real inference budget fighting compaction-induced errors two different ways: retaining more raw context before summarizing, or running extra self-verification and repair passes against an already-compacted summary before acting. No existing account predicts when each strategy is worth its compute cost, so teams tune this allocation by trial and error, and papers claiming repair passes "help" rarely control for whether the gain is just proportional to tokens spent rather than to the repair mechanism itself.

## Mechanism

A repair pass re-samples the model's belief state conditioned on the same fixed summary text. It can correct stochastic lapses in surfacing information that is physically present in the context (a search or attention problem), but it cannot inject information the summarizer already discarded, because there is no channel left for that information to re-enter generation except confabulation. Retention-compute changes the input itself, so it fixes both search failures and true information-absence failures. This predicts an interaction effect between repair-pass count and error type, not a uniform benefit, and a diminishing-then-flat repair curve rather than one that keeps improving with more passes.

## Method

Build synthetic agent transcripts with a ground-truth list of constraints at known positions. Compact each transcript at several compression ratios (for example, retain 70%, 50%, 30%, or 10% of tokens), and for each resulting summary, label each constraint as retrieval-type (present, verbatim or paraphrased, in the summary text) or deletion-type (absent from the summary), using string or entailment matching against the summary itself, not the original transcript. Under a token-budget-matched design, compare two arms that spend the same total extra tokens: additional repair passes that re-prompt the agent to list and check for missing constraints, versus retaining that many extra raw tokens instead of running any repair pass. Measure downstream violation rate per constraint, split by error type and arm.

An explicit zero-compaction control arm is worth adding to this design: at high retention ratios almost nothing is classified deletion-type by construction, so the ratio sweep implies a baseline rather than measuring one directly, and a true uncompacted arm would separate compaction-induced retrieval failure from ordinary instruction-following error that has nothing to do with compaction.

## Prediction

In the repair-pass arm, violation rate for retrieval-type constraints drops sub-linearly with pass count and plateaus by four to eight passes; violation rate for deletion-type constraints stays flat across all pass counts. In the matched-retention arm, violation rate drops for both error types. The cost-effectiveness of repair-compute (violation-rate reduction per token spent) exceeds retention-compute at low compaction ratios, where errors are mostly retrieval-type, and crosses below it at high compaction ratios, where errors become mostly deletion-type, producing a measurable crossover point in compaction-ratio space.

## Falsification

The mechanism is wrong if repair-pass count reduces deletion-type violations at a slope statistically indistinguishable from its effect on retrieval-type violations. That would mean repair passes are reconstructing deleted content from general knowledge (confabulation) rather than surfacing it, or that the retrieval and deletion classification is not capturing a real causal distinction. It is also wrong if the retrieval-type repair curve keeps improving linearly with pass count rather than saturating, which would indicate repair is not bounded by a fixed information floor.

## Related-work delta

The closest prior work is test-time-compute scaling research, which treats inference-time repair as a generically useful lever whose returns depend on task difficulty, and self-refine and reflexion-style repair agents, which make the same generic assumption. This idea differs by predicting a hard, mechanism-specific ceiling on repair's usefulness that is set by whether information still physically exists in the context, not by task difficulty in general, and by requiring a token-budget-matched retention-compute control arm specifically to rule out the confound that more compute of any kind helps, a control absent from the prior work as summarized here.

## Notes on source verification

This idea came from an external idea-generation and ranking pass, not from this repository's own literature search. The related-work references above (test-time-compute scaling, self-refine and reflexion-style repair) are named generically, without a precise citation checked in this session, and the "no existing account predicts this" claim has not been independently verified against arXiv. Treat the novelty claim as unconfirmed until a direct search is run, matching this repository's existing standard for the rest of this folder.

## Sources

No sources independently verified in this repository for this idea yet.
