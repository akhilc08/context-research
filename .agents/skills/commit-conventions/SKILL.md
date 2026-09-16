---
name: commit-conventions
description: Name commits in this repository. Use whenever writing, amending, squashing, or proposing a commit subject.
---

# Commit conventions

Inspect the actual change before naming it.

Use `<type>(<scope>): <summary>`. The scope is optional and names a stable lowercase area. Omit it for broad changes.

Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `revert`.

Write a lowercase imperative summary with no ending period. Describe the outcome, not the files.

Use a subject alone unless the user asks for a body or the reason cannot be recovered from the diff.
