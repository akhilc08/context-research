# Potential Research Idea: Drift Detection Linked to Automatic Code Rollback

Date: 2026-09-16. Status: candidate direction sketched through conversational research (parallel web-research sweeps), checked once for novelty and feasibility. No experiments run, not yet chosen for the main study.

See [`../paper-plan.md`](../paper-plan.md) (idea G) for this idea's concretized design and why it is ranked lowest priority there.

## Relationship to the compaction study

Candidate offshoot of [`compaction-study-brief.md`](../compaction-study-brief.md) and, more directly, of [`lightweight-verify-repair-brief.md`](../lightweight-verify-repair-brief.md), whose fingerprint-check-and-patch pilot this direction proposes to extend. Not as developed as either brief's own plan; this is a proposal-stage sketch.

## The mechanism

The lightweight-verify-repair-brief already detects when compaction has corrupted the agent's belief about something, such as which file it is editing, and repairs that belief. But by the time the mismatch is caught, the agent may already have committed code based on the wrong belief. Repairing the belief going forward does not undo the bad commit. Today a person has to notice and revert it by hand.

## Novelty

Open at the specific link, though the surrounding pieces exist separately. AgentRewind (arXiv 2608.14380, found via search, not independently read) checkpoints and restores agent and environment state together but is invoked manually or on task failure, not triggered by a drift signal. Dependency-Guided Rollback Repair (arXiv 2608.10502, already verified in this repo's source ledger) repairs the agent's internal memory graph but never touches the repository or commit history the agent produced. A rollback survey (arXiv 2606.12485, found via search) found only 27 of 435 surveyed agent systems expose any rollback mechanism at all, which suggests the base capability is rare, let alone one conditioned on a drift signal.

## Feasibility

High. Checkpointing primitives already exist off the shelf (a git commit per turn, or Claude Code's own file checkpointing). The missing piece is the trigger, not the infrastructure.

## Benchmark-then-build plan

Extend the lightweight-verify-repair pilot's synthetic trajectories so each includes a real small repository, and add a step where the agent naturally commits based on the planted binding after a compaction event. Run three arms: context-patch only (the existing plan), context-patch plus auto-revert of any commit made downstream of the flagged belief, and no repair. Metrics: task success, a false-revert rate on trajectories where the binding never actually drifted (to check the method is not trigger-happy), and a count of manual git resets a person would otherwise have needed.

The hard design question is attribution: how to know which commit depended on which belief, without building the full dependency graph that Dependency-Guided Rollback Repair uses. The cheap version tags each commit with the fingerprints active in context at commit time; a more precise but costlier version asks the model to name, in one line, which fact it relied on for that specific commit. Comparing the two on false-revert rate is a good first, small experiment before the full three-arm pilot.

## Notes on source verification

Dependency-Guided Rollback Repair (arXiv 2608.10502) was already verified in this repository's ledger before this brief. AgentRewind and the rollback mechanism survey were found via a research sweep during this conversation and not independently re-read here; treat them as leads, not settled citations, until read directly.

## Sources

- AgentRewind, arXiv 2608.14380 (found via search, not independently read)
- Dependency-Guided Rollback Repair, arXiv 2608.10502 (already verified in this repo's ledger)
- Rollback mechanism survey, arXiv 2606.12485 (found via search, not independently read)

See `SOURCES.md` for this repo's main citation ledger; the entries above are not yet merged into it.
