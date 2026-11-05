# Potential Research Idea: Position-Dependent Constraint Retention

Date: 2026-09-16. Status: candidate direction sketched through conversational research (parallel web-research sweeps), checked once for novelty and feasibility. No experiments run, not yet chosen for the main study.

See [`../paper-plan.md`](../paper-plan.md) (idea A) for this idea's concretized benchmark, baseline, and proposed-method design, including a pilot run, and the repository's top-ranked candidate for a first submission.

## Relationship to the compaction study

Candidate offshoot of [`compaction-study-brief.md`](../../../../docs/compaction-study-brief.md). Not as developed as that brief's Phase 1 and Phase 2 design; this is a proposal-stage sketch.

## The mechanism

ConstraintRot, the benchmark behind the Governance Decay paper, states a policy before the task begins, grows the context past budget, then sends a request that would violate the policy if it were forgotten. Every published version of this test injects the constraint at the start of the session. None varies *when* the constraint is introduced relative to a compaction event and measures whether that timing changes survival. A correction given by a user midway through a long session, shortly before a compaction fires, has not yet been repeated enough times to be "baked in" the way an early system-prompt rule has, so it may be more fragile, not less, than the recency intuition would suggest.

## Novelty

Open. ConstraintRot and Governance Decay (arXiv 2606.22528, verified in this repo already) only test start-of-session constraints. A practitioner blog post found during this research explicitly flags the gap: "no compaction experiment was conducted... reports none of actual retention rates" for constraints introduced later in a trajectory.

## Feasibility

High and cheap. This is a parameter sweep over ConstraintRot's existing nine scenarios, not a new benchmark. The only change is where in the trajectory the constraint is introduced.

## Benchmark-then-build plan

Cross constraint-injection position (start, mid-trajectory, just before a compaction event, just after as a new turn) with compactor (plain summary, head-tail truncation, Constraint Pinning) and number of subsequent compactions, holding trajectory length fixed. Measure violation rate as a function of position. If corrections given right before compaction survive worse than old, already-summarized ones, build the fix: a short verbatim grace buffer that holds the last few turns uncompacted regardless of budget. The deliverable is a retention-by-position curve nobody has published, plus a one-parameter harness fix if the curve shows the expected pattern.

## Notes on source verification

ConstraintRot and Governance Decay (arXiv 2606.22528) were already verified in this repository's ledger before this brief. The practitioner blog post naming the gap directly was found via a research sweep during this conversation and not independently re-read here; treat it as a lead, not a settled citation, until read directly.

## Sources

- Governance Decay / ConstraintRot, arXiv 2606.22528 (already verified in this repo's ledger)
- Practitioner blog post noting untested compaction retention rates for later-introduced instructions (found via search, not independently read; source URL not yet recorded)

See `SOURCES.md` for this repo's main citation ledger; the entry above is not yet merged into it.
