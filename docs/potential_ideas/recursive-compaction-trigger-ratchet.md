# Potential Research Idea: Recursive Compaction Ratchets Away Dormant, Trigger-Conditioned Constraints

Date: 2026-09-18. Status: candidate direction from an external idea-generation and diversity-aware ranking pass (Elo-scored, selected as a "combine" in a top-3), not yet checked against the literature by this repo's own research process. No experiments run, not yet chosen for the main study.

See [`../paper-plan.md`](../paper-plan.md) (idea C) for this idea's concretized benchmark, baseline, and proposed-method design. A very recent paper (CliffCompaction, arXiv 2609.26779) now gives the recursive-versus-source-anchored axis a real citable baseline instead of a hypothetical one; the related-work section there has been rewritten accordingly.

## Relationship to the compaction study

Candidate offshoot of [`../compaction-study-brief.md`](../compaction-study-brief.md). Distinct from [`position-dependent-constraint-retention.md`](position-dependent-constraint-retention.md) in this folder: that idea varies *when* a constraint is stated relative to a compaction boundary, while this one varies the compaction *architecture* (recursive vs. source-anchored regeneration) as the causal lever behind loss of constraints whose trigger has not yet fired. They are siblings, not duplicates. See also [`ratchet-vs-rescue-trigger-loss.md`](ratchet-vs-rescue-trigger-loss.md), which merges this idea with [`repair-vs-retention-compute-crossover.md`](repair-vs-retention-compute-crossover.md).

## Problem and gap

Two open problems are treated separately but are plausibly connected. First, it is unknown whether frequent compaction helps or hurts, because no work isolates whether each compaction round regenerates from the raw transcript or from the prior round's summary. Second, the single highest-stakes fidelity failure, silent erosion of constraints conditional on a rare, not-yet-fired trigger (for example, "if you touch payments, require a migration script"), has no proposed mechanism explaining why it would be worse under some compaction architectures than others. Recursion depth may be exactly what turns an occasional conditional-constraint miss into a near-certain one.

## Mechanism

Recursive compaction (each round conditions only on the prior summary) is a form of generation loss: each round treats the previous summary's errors as ground truth, so anything a round drops is permanently gone for all future rounds. The channel through which this loss is non-random is a recency heuristic: a trigger-conditioned constraint has zero supporting mentions after it is first stated, so it is surface-indistinguishable from a resolved or abandoned thread, which a summarizer is otherwise correct to prune. In the recursive regime, that heuristic is reapplied round after round to a summary that has already lost some of the conditional framing, so each round has strictly less signal to tell "dormant but armed" apart from "resolved," producing a ratchet toward complete erasure that scales with round count. Source-anchored compaction (each round re-reads the full raw transcript-so-far) applies the same heuristic fresh each round against the unabridged original statement. It may misjudge occasionally, but there is no accumulating disadvantage, so errors do not compound with round count, only with per-round sampling noise.

## Method

Build synthetic, roughly 200-turn coding-agent transcripts containing matched constraint pairs at the same position and token length: unconditional constraints ("never modify config.yml") and trigger-conditioned constraints ("if you ever touch config.yml, ask first"), with the trigger event engineered to fire at controlled distances after compaction. Cross two compaction regimes, recursive and source-anchored, with compaction frequency (every 5, 10, 20, or 40 turns), matching total compaction events per regime. At the trigger point, measure whether the constraint is still stated with its conditional clause intact when probed, and whether the agent actually obeys it.

## Prediction

Under recursive compaction, violation and omission rate for trigger-conditioned constraints grows super-linearly with the number of compaction rounds and is far larger than for matched unconditional constraints at the same round count. Under source-anchored compaction, violation rates for both constraint types stay flat and low regardless of frequency or round count, and the gap between conditional and unconditional constraints stays near zero.

## Falsification

The hypothesis fails if trigger-conditioned constraint erosion under recursive compaction does not scale with round count, for example if a constraint compacted twenty times shows the same erosion rate as one compacted twice at a matched trigger-firing distance, which would kill the compounding-ratchet mechanism. It also fails if source-anchored compaction shows conditional-constraint erosion equal to or worse than recursive compaction at matched round counts, which would show that the regime axis is not the variable doing the work and the effect is really just about trigger-conditioning in general.

## Related-work delta

Two threads come closest without combining. A recursion-depth or source-anchoring account of the "does frequent compaction help or hurt" question tests aggregate fidelity and predicts a regime-by-frequency interaction, but treats all facts as an undifferentiated pool. A rare-trigger constraint account identifies the recency-heuristic misfire on dormant conditionals, but tests it only under a single, implicitly source-anchored compaction setup with trigger distance as the sole independent variable. This idea predicts that the recursive-versus-source-anchored choice is not a general fidelity multiplier but is specifically catastrophic for dormant trigger-conditioned constraints through a ratchet that compounds with round count, a prediction neither parent thread makes alone.

## A practical caveat worth flagging

If source-anchored regeneration turns out to resist the ratchet, that does not mean "always re-read the full raw transcript" is a deployable fix. Re-reading the entire transcript every compaction round becomes expensive at genuine long horizons and works against the reason to compact at all. Source-anchoring functions here as a diagnostic instrument for isolating the mechanism, not as the proposed production fix. A narrower follow-up, such as keeping only trigger-tagged spans verbatim and re-anchoring those, is the more realistic deployment path if the mechanism holds.

## Notes on source verification

This idea came from an external idea-generation and ranking pass, not from this repository's own literature search. No specific paper is cited for either "prior thread" described in the related-work delta above; the descriptions are generic, and no arXiv ID has been checked in this session. Treat the novelty claim as unconfirmed until a direct search is run, matching this repository's existing standard for the rest of this folder.

## Sources

No sources independently verified in this repository for this idea yet.
