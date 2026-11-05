# context-research

Research on context management for long-running LLM coding agents, focused on context compaction: what it loses and how to fix it.

## Layout

| Folder | What it holds |
|---|---|
| [`docs/`](docs) | Research writing: briefs, the paper plan, idea write-ups, notes, and sources. |
| [`paper/`](paper) | The paper's LaTeX source, compiled PDF, and figures. |
| [`experiments/`](experiments) | Experiment code, input data, and results. Each study is a self-contained folder with its own README. |

## Research documents

- [`docs/session-rule-store-roadmap.md`](docs/session-rule-store-roadmap.md): current direction on instruction inheritance and updates across persistent subagents.
- [`docs/subagent-rule-update-scenario.md`](docs/subagent-rule-update-scenario.md): the first controlled dependency-approval scenario and its evaluation protocol.
- [`docs/compaction-study-brief.md`](docs/compaction-study-brief.md): main research brief with hypotheses, related work, and the study plan.
- [`docs/paper-plan.md`](docs/paper-plan.md): concrete benchmark and method designs for each idea below, ranked and prioritized toward a first submission.
- [`docs/lightweight-verify-repair-brief.md`](docs/lightweight-verify-repair-brief.md): offshoot brief on fingerprint-check-and-patch for silently dropped context.
- [`docs/ideas/`](docs/ideas/): candidate research ideas, each a narrow compaction loss mechanism paired with a cheap fix.
  - [`position-dependent-constraint-retention.md`](docs/ideas/position-dependent-constraint-retention.md)
  - [`drift-detection-rollback.md`](docs/ideas/drift-detection-rollback.md)
  - [`cheap-compaction-validation-stand-in.md`](docs/ideas/cheap-compaction-validation-stand-in.md)
  - [`goal-resurrection-after-compaction.md`](docs/ideas/goal-resurrection-after-compaction.md)
  - [`repair-vs-retention-compute-crossover.md`](docs/ideas/repair-vs-retention-compute-crossover.md)
  - [`recursive-compaction-trigger-ratchet.md`](docs/ideas/recursive-compaction-trigger-ratchet.md)
  - [`ratchet-vs-rescue-trigger-loss.md`](docs/ideas/ratchet-vs-rescue-trigger-loss.md)
- [`docs/trace-notes.md`](docs/trace-notes.md): working notes on the TRACE paper that supports the main brief.
- [`docs/SOURCES.md`](docs/SOURCES.md): annotated source ledger.

## Paper

[`paper/paper.pdf`](paper/paper.pdf): "Watchpoint Compaction," a general repair mechanism for two different compaction failure modes (a dropped rule, a resurrected stale goal), backed by roughly 2,200 real API trials. Includes a real negative result (a naive self-verification check that fails, and why) as part of its contribution, not just its narrative. Not yet reviewed or submitted anywhere; see its own Limitations section.

## Experiments

- [`experiments/subagent-rule-updates/`](experiments/subagent-rule-updates/): manager-worker study of rule changes reaching running subagents and surviving compaction. Start with its [FINDINGS.md](experiments/subagent-rule-updates/FINDINGS.md).
- [`experiments/position-dependent-retention/`](experiments/position-dependent-retention/): first single-backbone pilot for idea A.
- [`experiments/recency-study/`](experiments/recency-study/): the larger runs behind the paper, plus the figure scripts.
- [`experiments/benchmark-dryrun/`](experiments/benchmark-dryrun/): τ-bench gold-action replay used to check the benchmark harness.
- [`experiments/overnight/`](experiments/overnight/): one unattended night of studies (E1 to E25, plus X1). Its README is the map and synthesis.

Scripts that call a model need `OPENROUTER_API_KEY`. The overnight studies load it from a `.env` file at the repository root. The older pilots read it from the environment.

## Working in this repository

Repository guidance lives in [`AGENTS.md`](AGENTS.md). `CLAUDE.md` points to the same file. Shared agent skills live under [`.agents/skills`](.agents/skills), with Claude-compatible links under `.claude/skills`.
