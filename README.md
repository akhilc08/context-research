# context-research

Research on context management for long-running LLM coding agents: what history compaction loses, and how to keep the instructions an agent must follow intact.

## Studies

Each study is a self-contained folder under `studies/` with its own README, code, and results.

| Study | Status | Question |
|---|---|---|
| [`subagent-rule-updates`](studies/subagent-rule-updates/) | Active | Do a user's rule changes reach worker agents that are already running, and survive compaction? Start with its [findings](studies/subagent-rule-updates/FINDINGS.md). |
| [`compaction-survey`](studies/compaction-survey/) | Archived | One night of studies (E1 to E27) on what compaction loses (rules, goals, plans, facts) and which cheap fixes restore it. |
| [`watchpoint`](studies/watchpoint/) | Archived | The first thread: rule and goal loss under compaction, ending in a paper draft on Watchpoint Compaction. |

The studies ran in reverse order of that table. The watchpoint work came first, the survey tested its ideas broadly, and the current study builds on the survey's operator-rule results.

## Background

Shared across studies, in [`docs/`](docs/):

- [`compaction-study-brief.md`](docs/compaction-study-brief.md): the original research brief, with hypotheses and related work.
- [`SOURCES.md`](docs/SOURCES.md): annotated source ledger on context compaction.
- [`trace-notes.md`](docs/trace-notes.md): working notes on the TRACE compression paper.

## Running code

Scripts that call a model need `OPENROUTER_API_KEY`. The current study and the survey read it from the environment or from a `.env` file at the repository root. The watchpoint pilots read only the environment. Each study's README describes its commands and offline checks.

## Working in this repository

Repository guidance lives in [`AGENTS.md`](AGENTS.md). `CLAUDE.md` points to the same file. Shared agent skills live under [`.agents/skills`](.agents/skills), with Claude-compatible links under `.claude/skills`.
