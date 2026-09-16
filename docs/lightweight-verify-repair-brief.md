# Lightweight Verify-and-Repair for Silently Lost Context: Research Brief

Date: 2026-09-15. Status: direction sketched via a multi-agent literature sweep and follow-up spot checks, no independent verification of most citations, no experiments run.

## 1. Relationship to the compaction study

This is a narrower, candidate offshoot of [`compaction-study-brief.md`](compaction-study-brief.md), not a replacement for it. That brief studies *when and how* to compact on long-running coding agents. This brief studies one specific *fix mechanism*: detect what a compaction silently dropped, then patch just that piece back in. It asks whether a cheap version is competitive with the expensive versions that already exist.

It overlaps most with that brief's Phase 2 candidate "Post-compaction re-verification: rerun tests after compaction and inject the real result." This generalizes that idea two ways: (a) beyond coding-specific test reruns to any fact/constraint/entity worth checking, and (b) beyond coding agents to long-running agents generally. If the pilot in the main study has room, this could slot in as a fifth Phase 2 arm rather than a separate project.

## 2. The problem, restated simply

A long-running agent can't keep everything in view forever, so it compacts (summarizes, trims, evicts). Compaction is usually silent about what it loses. The agent doesn't know something is gone until it acts on the gap. Three known flavors of this come from separate lines of work:

- **Rules get dropped.** A standing instruction ("don't email outside the org") quietly disappears from a summary. Governance Decay / ConstraintRot measured this directly.
- **Entities get mixed up.** The agent is correct about *which* customer/file/order it's working on early, then silently drifts to a different one later without any single step looking wrong. Binding Drift / Entity Binding Failures measured this.
- **Facts go stale or get lost outright**, e.g. a deadline that changed twice, or a detail mentioned once and never repeated.

These are studied as separate problems by separate papers with separate benchmarks. Nothing found puts all three under one roof.

## 3. What already exists (the honest inventory)

| Approach | What it does | Loss type covered | Repairs automatically? | Cost profile |
|---|---|---|---|---|
| **Constraint Pinning** (from the Governance Decay paper, arXiv 2606.22528) | Reserves a protected slot for flagged constraints; compaction can't touch it | Constraints only | N/A. It prevents loss instead of repairing it. | Pays a fixed tax on everything pinned, whether or not it turns out to matter (~47 tokens/constraint per the paper) |
| **session-vitals** (github.com/edwinquick/session-vitals) | Periodically asks the agent to recall task/rules/entities, scores the answer against the real transcript (never trusts the model's self-assessment) | Constraints, task state, edited files | No. It flags a mismatch that a human or downstream system has to act on. | Cheap (hooks parse the transcript, ~300ms, no model call for the metrics layer; the recall probe itself is one LLM call) |
| **Binding Drift's own defenses** (github.com/shashank-indukuri/binding-drift) | Repo includes scenarios + existing mitigations for entity drift specifically | Entity binding only | Unconfirmed. Repo not yet inspected directly. | Unknown |
| **Dependency-Guided Rollback Repair** (arXiv 2608.10502) | Builds a full typed memory-to-action graph over the session, traces what depended on a faulty memory, selectively deactivates/replays | General memory faults (framed as corrupted/stale/misattributed, not specifically "dropped by compaction") | Yes | Requires full runtime provenance tracking for the whole session; paper reports 85.3% recovery vs. 77.3% for the next-best method, but does not publish token/latency/dollar overhead numbers |
| **Slipstream** (arXiv 2605.08580) | Runs the compactor and a continuation of the full, uncompressed context in parallel; a judge model checks the candidate summary against what the agent actually needed next, before committing | Prevents bad compactions from landing at all | Prevention, not post-hoc repair | Roughly doubles compute during the compaction window (parallel branch) |

## 4. The gap

Nothing found does a **lightweight, per-item check**: fingerprint a fact/constraint/entity-binding at write time, cheaply re-derive that fingerprint after compaction (no session-wide dependency graph, no parallel branch), and patch only the item that fails the check. Nobody has published a cost number for any of the heavier alternatives, so there is no existing baseline to show whether "lightweight" would be cheaper in practice. That has to be measured, not assumed.

## 5. Two-part plan

**Part 1: combined benchmark of existing fixes.** Reuse ConstraintRot's scenario shape (policy stated → context grows past budget → a request arrives that would violate the policy if it were forgotten) and Binding Drift's open harness (entity resolved once, acted on repeatedly, possibly re-bound later), run on the *same* set of trajectories:

1. No protection (plain summarization): baseline
2. Head-tail truncation: the one thing ConstraintRot found actually works for constraints
3. Constraint Pinning
4. Retention-probe / detect-only (session-vitals style)
5. Binding Drift's existing defense(s)

Metric per method: violation/drift/loss rate, split by loss type (constraint vs. entity vs. fact), plus token/latency overhead. This is new mainly because methods built for one loss type (e.g. Constraint Pinning) have never been checked against the *other* loss types (does pinning constraints help or hurt entity-binding drift? Unknown.).

**Part 2: the lightweight method, and the one claim to test.** Build the fingerprint-check-and-patch mechanism described above, generalized across all three loss types. Headline, falsifiable claim:

> At matched recovery rate, this costs meaningfully less than Constraint Pinning (no permanent reserved tax) and meaningfully less than Dependency-Guided Rollback Repair (no session-wide provenance graph). It should get somewhere in the neighborhood of that paper's 85.3% recovery number on a similarly-shaped test without needing the graph.

If it doesn't land near that recovery rate, or doesn't actually cost less once measured, the idea is dead and that's a useful, fast answer.

## 6. Cheap kill test

Build ~30 synthetic long trajectories with planted constraints, entity-binding chains, and superseded facts (distractor turns in between). Fingerprint each at write time with a short canonical restatement or embedding, not a cryptographic hash, because the check needs to tolerate paraphrase. After a compaction pass, re-derive each fingerprint from what's left and flag mismatches; on a flag, reinject the original verbatim from an untouched store. Compare loss rate and added tokens/calls against the Part-1 baselines on the same trajectories. Pure API calls, no GPU, well under a day of work.

## 7. Caveats on the sources below

Most of the specific papers below came out of a parallel five-agent web-research sweep in one conversation, not from directly reading each paper. Independently re-confirmed in this session (direct search and/or fetch): Governance Decay, Binding Drift, Entity Binding Failures, Dependency-Guided Rollback Repair, Slipstream, and session-vitals (fetched directly). Not independently re-confirmed: any paper mentioned only once by a single research agent and not re-checked here (e.g. IntentKV, ReCache, SinkTrack, A-Mem, LightMem, FiFA, ACON, PEEK, MEMPROBE). Treat those as leads, not settled citations, until read directly. The rest of this repo follows the same standard.

## Sources

- Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents, arXiv 2606.22528 (verified)
- Binding Drift in Multi-Step Tool-Augmented Agents, arXiv 2607.18316, code at github.com/shashank-indukuri/binding-drift (verified)
- Entity Binding Failures in Tool-Augmented Agents, arXiv 2606.30531 (found via search, not independently read in full)
- From Faulty Memories to Corrected Actions: Dependency-Guided Rollback Repair for Memory-Augmented Agents, arXiv 2608.10502 (verified via direct fetch; no code release found)
- Slipstream: Trajectory-Grounded Compaction Validation for Long-Horizon Agents, arXiv 2605.08580 (verified)
- session-vitals, github.com/edwinquick/session-vitals (verified via direct fetch; author describes thresholds as "first guesses," not yet rigorously validated)
- Leads not independently verified. Treat with caution: IntentKV (arXiv 2606.09916), ReCache (arXiv 2608.19662), SinkTrack (arXiv 2604.10027), A-Mem (arXiv 2502.12110), LightMem (arXiv 2510.18866), FiFA (arXiv 2512.12856), ACON (arXiv 2510.00615), PEEK (arXiv 2605.19932), MEMPROBE (arXiv 2606.24595)

See `SOURCES.md` for this repo's main citation ledger; the entries above are not yet merged into it.
