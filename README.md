# context-research

Research on context management for long-running LLM coding agents, focused on context compaction: what it loses and how to fix it.

## Contents

- [`docs/compaction-study-brief.md`](docs/compaction-study-brief.md): main research brief with hypotheses, related work, and the study plan.
- [`docs/lightweight-verify-repair-brief.md`](docs/lightweight-verify-repair-brief.md): offshoot brief on fingerprint-check-and-patch for silently dropped context.
- [`docs/trace-notes.md`](docs/trace-notes.md): working notes on the TRACE paper that supports the main brief.
- [`docs/SOURCES.md`](docs/SOURCES.md): annotated source ledger.

## Working in this repository

Research briefs, paper notes, and source records live in [`docs`](docs). Repository guidance lives in [`AGENTS.md`](AGENTS.md). `CLAUDE.md` points to the same file. Shared agent skills live under [`.agents/skills`](.agents/skills), with Claude-compatible links under `.claude/skills`.
