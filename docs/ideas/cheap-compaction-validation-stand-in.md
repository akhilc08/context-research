# Potential Research Idea: A Cheap Stand-In for Paired-Continuation Compaction Validation

Date: 2026-09-16. Status: candidate direction sketched through conversational research (parallel web-research sweeps), checked once for novelty and feasibility. No experiments run, not yet chosen for the main study.

See [`../paper-plan.md`](../paper-plan.md) (idea E) for this idea's concretized benchmark, baseline, and proposed-method design toward an actual submission.

## Relationship to the compaction study

Candidate offshoot of [`compaction-study-brief.md`](../compaction-study-brief.md), targeting its Phase 2 compaction-gate candidate directly. Not as developed as that brief's own plan; this is a proposal-stage sketch.

## The mechanism

The main brief's Phase 2 plan already includes a compaction gate: continue the agent down two paths from the same state and check whether they diverge before committing to a summary. This is TRACE's method, and it is expensive, since it requires an extra full rollout. The candidate cheaper proxy: instead of continuing execution, generate two or three quick draft summaries of the same history and check whether they agree on the load-bearing facts (file names, decisions, what remains to be done). Disagreement between drafts stands in for the expensive continuation's divergence signal.

## Novelty

Open in this setting. A close relative, Context Codec (arXiv 2605.17304, reported by a research fork as confirmed via direct fetch, not independently re-confirmed here), proposes almost the same confidence mechanism (extractor self-consistency, cross-model agreement, round-trip reconstruction) but is explicitly a small design sketch of five hand-scored examples, applied to single-document compression, never to a long-running coding agent, and never compared against a rollout-based baseline.

## Feasibility

High and cheap: two or three extra summary calls plus a fact-comparison step, no new infrastructure.

## Benchmark-then-build plan

Add draft-agreement checking as a fourth arm in the main brief's compaction-gate comparison. The reference points for the expensive baseline both have usable code:

- TRACE's own repository (github.com/nokia-applied-research/Trace, confirmed to exist and contain the paired closed-loop evaluation and compression-prompt optimizer, though it depends on AppWorld externally, carries no license file yet, and shows minimal activity).
- Slipstream (arXiv 2605.08580, already verified in this repo; its code repository, reported by a research fork as github.com/chenzhuofu/slipstream, is not independently confirmed here), which validates compaction by running a parallel continuation and has already been tested on SWE-bench Verified, closer to this project's coding setting than AppWorld.

The key question: does draft disagreement actually predict the real downstream mistakes that the expensive continuation catches, or is it a weak signal that misses cases the expensive version would flag. Either answer is a useful, reportable result.

## Notes on source verification

The TRACE paper (arXiv 2608.06503) and Slipstream (arXiv 2605.08580) were already verified in this repository's ledger before this brief; the TRACE paper's title and authors were re-confirmed directly in this session after an initial fetch of its abstract page failed to surface the Nokia Applied Research and University of Virginia affiliation already on record, which a fuller search then resolved. The TRACE code repository was confirmed to exist via direct fetch in this session; it carries no license file as of that check. Context Codec was reported as verified via direct fetch by a research fork but not independently re-confirmed here. Slipstream's code repository was found via search and not independently confirmed. Treat unconfirmed items as leads, not settled citations, until read directly.

## Sources

- Context Codec, arXiv 2605.17304 (reported as verified via direct fetch by a research fork, not independently re-confirmed here)
- Slipstream, arXiv 2605.08580 (already verified in this repo); code at github.com/chenzhuofu/slipstream (found via search, not independently confirmed)
- TRACE, arXiv 2608.06503 (already verified in this repo's ledger; re-confirmed directly in this session); code at github.com/nokia-applied-research/Trace (confirmed via direct fetch in this session; no license file as of this check)

See `SOURCES.md` for this repo's main citation ledger; the entries above are not yet merged into it.
