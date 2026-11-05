# Potential Research Idea: Ratchet vs. Rescue — Trigger-Conditioned Loss Resists Repair, Not Retention

Date: 2026-09-18. Status: candidate direction from an external idea-generation and diversity-aware ranking pass (Elo-scored, selected as a "combine" in a top-3), not yet checked against the literature by this repo's own research process. No experiments run, not yet chosen for the main study.

See [`../paper-plan.md`](../paper-plan.md) (idea D) for this idea's concretized design, gated on the individual results of the two parent ideas (B and C there) landing first.

## Relationship to the compaction study

Candidate offshoot of [`compaction-study-brief.md`](../../../../docs/compaction-study-brief.md). This idea is a merge of two others in this folder: [`repair-vs-retention-compute-crossover.md`](repair-vs-retention-compute-crossover.md) and [`recursive-compaction-trigger-ratchet.md`](recursive-compaction-trigger-ratchet.md). The merge is not just a concatenation: it uses the repair-versus-retention compute split from the first idea as a diagnostic instrument for the causal claim of the second, applying it specifically to constraints already damaged by the recursive ratchet. If repair passes fail to rescue them while retention succeeds, that is simultaneously stronger evidence that the ratchet produces genuine deletion rather than a retrieval failure a cheap repair pass could fix.

## Problem and gap

Three unresolved threads collide. It is unknown whether frequent compaction helps or hurts, because no work isolates whether each round regenerates from the raw transcript or the prior summary. Teams do not know whether to spend inference budget on repair and self-verification passes or on retaining more raw context, because no account predicts which failures each fixes. And the single highest-stakes fidelity failure, silent erosion of dormant, trigger-conditioned constraints, has no mechanism explaining why it would be architecture-dependent or why it would resist cheap fixes. Practitioners need one answer: when a dormant constraint has been damaged by compaction, is a repair pass enough, or does the compaction pipeline itself have to change?

## Mechanism

Two mechanisms compose. Recursive compaction is lossy re-encoding of a lossy encoding: each round treats the prior summary's errors as ground truth, so anything dropped in round N is permanently gone from round N+1 onward. The channel through which this loss is non-random is a recency heuristic: a trigger-conditioned constraint has no supporting mentions after it is stated, so it looks indistinguishable from a resolved thread and gets pruned, and in the recursive regime this heuristic is reapplied each round to a summary with strictly less signal than the last, producing a ratchet. Once the conditional clause is gone from the text, it is gone from what a repair pass would condition on. A repair pass re-samples the model's belief state over the same fixed summary, which can only fix search or attention failures where information is present but not surfaced, not information-absence, because there is no channel for deleted content to re-enter generation except confabulation. Source-anchored compaction and retention-compute both change the input itself, so neither shares this ceiling.

## Method

Build roughly 200-turn synthetic coding-agent transcripts with matched trigger-conditioned ("if X, then C") and unconditional ("always C") constraints, with trigger events fired at controlled distances after compaction. Cross recursive versus source-anchored regeneration at several compaction frequencies, matched on total compaction events. At the trigger point, take the resulting summary and run a token-budget-matched comparison: a repair arm with zero to eight self-verification passes that ask the agent to list and check for missing constraints, versus a retention arm with an equivalent number of extra raw tokens retained before compaction instead of any repair pass, crossed with regime. Label each violation as retrieval-type (the conditional clause is present in the summary, entailment-checkable) or deletion-type (the clause is absent) before applying the repair or retention arms, then measure post-arm violation rate per constraint type.

## Prediction

Under recursive compaction, trigger-conditioned violations grow super-linearly with round count and are classified overwhelmingly as deletion-type at moderate to high compaction frequency. In the repair arm, violation rate for these deletion-type failures stays flat across pass count, meaning no rescue, while the retention arm and the source-anchored regime both reduce it substantially and comparably per token spent. Unconditional constraints and retrieval-type failures show the opposite pattern: repair passes measurably reduce their violation rate.

## Falsification

The hypothesis fails if repair-pass count reduces trigger-conditioned violation rate at a slope statistically indistinguishable from the token-matched retention arm, meaning repair rescues deletion-type failures as well as adding raw tokens does. That would mean the information was not actually deleted, undermining both the ratchet-as-generation-loss mechanism and the retrieval-versus-deletion distinction. It also fails if trigger-conditioned erosion under recursive compaction does not scale with round count at a fixed trigger-firing distance, which kills the compounding-ratchet claim independent of the repair-versus-retention result.

## Related-work delta

The closest prior threads are a recursion-depth account (a regime-by-frequency interaction on aggregate fidelity, with no differentiation by fact class or repair-compute), a repair-versus-retention account (predicting repair fixes retrieval-type but not deletion-type failures, tested on generic truncation-induced omissions rather than a specific compounding architectural failure), and a trigger-conditioned-ratchet account (fusing regime and constraint type, but never asking whether the resulting damage is repairable). This idea's contribution is using the repair-versus-retention compute split as a diagnostic instrument to prove the ratchet mechanism is genuine deletion rather than mere retrieval failure, giving a concrete, testable answer to a practitioner-facing question none of the three parent ideas answers alone: for the worst compaction failure mode, is more repair compute worth it, or does the pipeline itself have to change?

## Notes on source verification

This idea came from an external idea-generation and ranking pass, not from this repository's own literature search. It is a synthesis of the other two ideas in this folder rather than an independent literature claim, and none of the related-work references have been checked against arXiv in this session. Treat the novelty claim as unconfirmed until a direct search is run, matching this repository's existing standard for the rest of this folder. Given the design complexity here (regime by frequency by repair-versus-retention arm by constraint type), running [`repair-vs-retention-compute-crossover.md`](repair-vs-retention-compute-crossover.md) and [`recursive-compaction-trigger-ratchet.md`](recursive-compaction-trigger-ratchet.md) individually first is the lower-risk path: if either parent's core prediction fails on its own, this merged prediction collapses too, and a failure in the combined design would be harder to attribute to one mechanism or the other.

## Sources

No sources independently verified in this repository for this idea yet.
