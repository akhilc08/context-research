# context-research

Research on context management for long-running LLM coding agents, focused on context compaction: what it loses and how to fix it.

## Contents

- [`docs/compaction-study-brief.md`](docs/compaction-study-brief.md): main research brief with hypotheses, related work, and the study plan.
- [`docs/paper-plan.md`](docs/paper-plan.md): concrete benchmark and method designs for each idea below, ranked and prioritized toward a first submission.
- [`docs/paper/paper.pdf`](docs/paper/paper.pdf): "Watchpoint Compaction," a general repair mechanism for two different compaction failure modes (a dropped rule, a resurrected stale goal), backed by roughly 2,200 real API trials. Includes a real negative result (a naive self-verification check that fails, and why) as part of its contribution, not just its narrative. Not yet reviewed or submitted anywhere; see its own Limitations section.
- [`docs/lightweight-verify-repair-brief.md`](docs/lightweight-verify-repair-brief.md): offshoot brief on fingerprint-check-and-patch for silently dropped context.
- [`docs/potential_ideas/`](docs/potential_ideas/): candidate research ideas, each a narrow compaction loss mechanism paired with a cheap fix.
  - [`position-dependent-constraint-retention.md`](docs/potential_ideas/position-dependent-constraint-retention.md)
  - [`drift-detection-rollback.md`](docs/potential_ideas/drift-detection-rollback.md)
  - [`cheap-compaction-validation-stand-in.md`](docs/potential_ideas/cheap-compaction-validation-stand-in.md)
  - [`goal-resurrection-after-compaction.md`](docs/potential_ideas/goal-resurrection-after-compaction.md)
  - [`repair-vs-retention-compute-crossover.md`](docs/potential_ideas/repair-vs-retention-compute-crossover.md)
  - [`recursive-compaction-trigger-ratchet.md`](docs/potential_ideas/recursive-compaction-trigger-ratchet.md)
  - [`ratchet-vs-rescue-trigger-loss.md`](docs/potential_ideas/ratchet-vs-rescue-trigger-loss.md)
- [`docs/trace-notes.md`](docs/trace-notes.md): working notes on the TRACE paper that supports the main brief.
- [`docs/SOURCES.md`](docs/SOURCES.md): annotated source ledger.

## Working in this repository

Research briefs, paper notes, and source records live in [`docs`](docs). Repository guidance lives in [`AGENTS.md`](AGENTS.md). `CLAUDE.md` points to the same file. Shared agent skills live under [`.agents/skills`](.agents/skills), with Claude-compatible links under `.claude/skills`.
