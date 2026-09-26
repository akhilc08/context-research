# Potential Research Idea: Compaction Resurrects an Old, Already-Replaced Goal

Date: 2026-09-16. Status: candidate direction sketched through conversational research (parallel web-research sweeps), checked once for novelty and feasibility. No experiments run, not yet chosen for the main study.

See [`../paper-plan.md`](../paper-plan.md) (idea F) for this idea's concretized benchmark, baseline, and proposed-method design, ranked as part of the recommended first submission.

## Relationship to the compaction study

Candidate offshoot of [`compaction-study-brief.md`](../compaction-study-brief.md). Not as developed as that brief's Phase 1 and Phase 2 design; this is a proposal-stage sketch.

## The mechanism

When a task changes mid-session (the user redirects the agent, or a subtask is superseded by a later one), the trajectory contains more than one past statement of "what the agent is doing." Compaction can anchor its summary to an old one instead of the most recent one, so the agent goes back to working on something that was already replaced, without any single step looking wrong.

## Novelty

Open, and currently documented only as an unresolved bug report rather than a study, which is itself a sign the mechanism is real and unstudied rather than already handled: OpenAI's Codex repository, issue #45464 (found via search, not independently read), describes exactly this failure and notes that the precise boundary, whether it is a summary-prioritization problem, a continuation-state-selection problem, or an interaction between stale checkpoints and new input, is unknown even to the reporter.

## Feasibility

High and cheap. Give every stated goal or objective a counter that only increases. Require the compactor to anchor its stated current objective to the highest counter present, and add a small validator that checks the post-compaction summary's stated objective against the last real user message before compaction fired.

## Benchmark-then-build plan

No existing benchmark tests this directly, but two open pieces can be combined:

- Supersede (arXiv 2606.27472, confirmed via direct fetch in this repo's research: code, dataset, and a trained model are publicly released, including a Hugging Face and Prime Intellect Environments Hub listing) validates the right task-construction pattern, state a fact, supersede it, test which value the agent's bounded memory reflects, but on general conversational data, not code, and on a self-maintained notes field rather than a harness's automatic compaction.
- SWE-Interact (arXiv 2606.30573; its GitHub repository, github.com/scaleapi/SWE-Interact, confirmed via direct fetch: 75 tasks, Apache-2.0 license, runs on the Harbor harness) supplies a realistic coding-agent setting where a simulated user progressively reveals requirements and issues revisions, though it was not confirmed whether any of its tasks actually contradict an earlier instruction rather than only add detail to it; that needs checking against the task files directly before relying on it.

Build trajectories, ideally reusing Supersede's supersession pattern inside SWE-Interact-style or Long-Horizon-Terminal-Bench coding tasks, where the goal changes two or three times mid-session, force a compaction after the latest change, and measure how often the resulting summary reflects the newest goal against an older one, across compactors, with and without the sequence-ID anchor.

## Notes on source verification

Directly re-confirmed by fetching the source in this session: the Supersede paper's HTML version and the SWE-Interact code repository. The SWE-Interact paper itself and the OpenAI Codex bug report were found via search and not independently read. Long-Horizon-Terminal-Bench is already cited in `compaction-study-brief.md`; its code repository was found via search and not independently confirmed here.

## Sources

- OpenAI Codex, GitHub issue #45464 (found via search, not independently read)
- Supersede, arXiv 2606.27472 (confirmed via direct fetch in this session)
- SWE-Interact, arXiv 2606.30573 (found via search, not independently read); code at github.com/scaleapi/SWE-Interact (confirmed via direct fetch in this session)
- Long-Horizon-Terminal-Bench, arXiv 2607.08964 (already cited in `compaction-study-brief.md`); code at github.com/zli12321/LHTB (found via search, not independently confirmed)

See `SOURCES.md` for this repo's main citation ledger; the entries above are not yet merged into it.
