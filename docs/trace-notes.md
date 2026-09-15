# TRACE — Paper Notes and Benchmark Ideas

Raw working notes on **TRACE: Trajectory-Relative Agent ContExt compression**, plus benchmark ideas that build on it. Feeds into [`compaction-study-brief.md`](compaction-study-brief.md).

## 1. What TRACE is about

- A failure mode in agent context compaction that is not information loss.
- A method for optimizing the compression prompt against that failure mode directly, instead of against agent final task success.

## 2. Context: long-horizon agents

- Standard loop: action, observation, action, observation.
- When the token budget exceeds a limit `B`, the harness replaces history with a summary.
- The summary produced becomes the input to the next summarization, so errors compound.
- Later compactions only ever see the previous summary plus the new turns since then — not the original raw history.

### The substitution assumption

- Standard assumption: if a summary retains task-relevant facts, it can stand in for raw history.
- TRACE's authors argue this is wrong:
  - A trajectory is directed — the agent knows what it tried, where it is, and whether it's done.
  - A summary flattens this into a declarative report ("completed X, next to do Y").
  - Even with perfect compaction of all the facts, the agent still loses its position in the sequence.
  - Perfect compaction of information alone is not enough.

### Two ways compression hurts an agent

1. **Deletion.** Something the agent needs is deleted and it can never get it back.
2. **Disorientation.** The agent could still get the info, but no longer knows where it is in the job.
   - Example: summary says "12 out of 18 payments are approved" but doesn't say *which* 12.
   - Example: agent hit an error but doesn't know why exactly — it encountered a 422 on the transaction call but doesn't know that `recipient_id` should have been `recipient_email`.
   - Example: agent doesn't know the task is finished — a summary line like "next steps: 1. verify" reads as if there's more to do.
   - Example: agent doesn't know what happened recently vs. what happened 30 steps ago.

## 3. AppWorld (evaluation environment)

- A simulated world of apps the agent drives through Python API calls (e.g. Venmo, Spotify, file system, a supervisor app for passwords).
- Apps hold persistent state: if the agent forgets a contact ID, it calls search-contacts again — dropping an observation from context doesn't delete it from the world.
- Agent/harness used in the paper: MiniMax + OpenClaw.

## 4. Experiment 1 — compaction policy vs. budget

- Two compaction policies, five budgets: 2k, 4k, 8k, 16k, unlimited.
- **FIFO** (dumb baseline): when context is too big, delete whole turns from the front, oldest first, until it fits. System prompt, task, and most recent turn are always kept.
- **Summary** (smart): call an LLM to write a structured markdown checkpoint — goal, constraints, progress (done / in-progress / blocked), key decisions, next steps, critical context.
- What FIFO does that Summary doesn't: keeps a verbatim record of the last few things done, in order.
- Summary trades that verbatim tail for broader coverage of older history.
- At the 2k budget: FIFO is too short to be useful, so Summary wins — but only barely.

### Metrics beyond mean pass rate

Mean pass rate hides a lot, so the paper adds:

- **pass@2** — solved at least once across two runs.
- **P²** — solved both times across two runs.
- As the context budget shrinks, both fall, but P² falls faster.
- P² falling faster than pass@2 means the "flaky" bucket is growing — tasks that used to be reliably solved (both runs) migrate into "solved in one run only."
- **Takeaway: compression converts reliably-solved tasks into intermittently-solved ones.**

### Horizon result

- Bucket tasks by how many steps the full-context agent needed: 8–16, 16–20, 20–32.
- Short tasks barely degrade as the budget shrinks.
- Long tasks fall off a cliff.
- Reason: a short task compacts once; a long task needs 5–6 compactions, so errors compound.

## 5. Probe 1 — does the agent know when to stop?

- In AppWorld, finishing means calling `apis.supervisor.complete_task(answer=...)`.
- *Note: this probe's method and result weren't fully clear from the source notes — revisit the paper directly before citing this probe.*

## 6. Probe 2 — how much does recent history still matter

Four experimental settings:

1. Full context.
2. Raw prefix summary + new turns uncompressed.
3. Raw prefix summary + new turns compressed.
4. Raw prefix summary only.

- Measures how agent behavior changes across these settings — specifically, what the agent's next tool call would be — and measures the divergence from the full-history behavior.

## 7. Probe 3 — recent history + actually running the outcome

- Pick a moment right before a compaction would happen.
- Compare raw history vs. summarized history.
- Play five moves forward from that point, count screwups:
  - **Type 1**: environment rejected the action (bad parameter, expired token).
  - **Type 2**: agent redid something it already did (same API call, already executed).
- Score = Type 1 count minus Type 2 count.

## 8. TRACE — the method itself

**Core idea:** use Probe 3 as a grader. Have the compressor write several candidate summaries, see which one causes fewer screwups, and use those compressions to rewrite the compressor's own instructions.

### Why not train on task success directly

- You only know pass/fail at the very end of a long-running task, so you can't attribute blame to which specific compression event caused the failure.
- Deeper problem: the agent doing a task keeps an implicit table of facts about the world (which tool is loaded, where a key is, which prerequisite is satisfied) — and the world keeps changing, so the agent can't keep this table up to date through compaction alone.
- **Paper's fix:** let the agent spend a turn asking the environment "what's the current value of field X?" instead of taking a task action — i.e., an explicit verification/probing turn.

### The budget problem with probing

- Probe too little → stale/bad environment data.
- Probe too much → wastes turns on auditing instead of progressing.

### EnvProbe — the rule for choosing what to check

Each field gets a score based on:

- How important the field is.
- How long since it was last verified.
- How unconfident the model says it is.
- Whether it blocks the next planned action.

Notably, **agent confidence is a bad signal on its own** — when the agent is wrong, it is confidently wrong 94% of the time. Down-weighting confidence in the scoring rule makes beliefs more accurate.

### Results

- World-state accuracy: 0.431 (EnvProbe) vs. 0.313 (periodic probing baseline).
- Task success: 20% vs. 80% — **reason for the drop**: when the agent probes, it loses its chain of thought and struggles to pick it back up.
- When the model rarely probes, task success rises to 91.8%.

## 9. Governance decay / ConstraintRot

- Agents compact via summarization, which sometimes silently drops specific rules stated at the start.
- Result: the agent does something at turn N that it explicitly refused to do 20 turns earlier. The authors call this **governance decay**.
- The authors built **ConstraintRot** to measure it:
  - 9 scenarios where a policy is stated, context is grown past budget, and a request arrives whose completion would break the policy.
  - Policy visible in context → 0% violation.
  - After 1 compaction → 30% violation.
  - On weaker models → up to 59% violation.
  - When the constraint survives the summary → 0% violation.
  - When it doesn't survive the summary → 38% violation.
- **Takeaway: safety here is a product of the compactor, not the model's alignment** (as the notes put it: "obviously").
- Only rules that lived in *context* got erased — rules baked into *training* all survived (also "obviously").

### Fix

Pull governance constraints into a buffer the compactor cannot touch, and reinject them verbatim at every compaction step.

## 10. Open-source resources to build on

- **AppWorld** — simulated world of apps the agent drives, with tasks and supporting infrastructure already built.
- **Binding Drift** — open-source benchmark: harness, scenarios, existing defenses, trajectory logs. https://github.com/shashank-indukuri/binding-drift. Covers the "entity gets bound to the wrong thing over time" failure mode.
- **ConstraintRot** — the "rules get silently dropped" benchmark (see §9).

## 11. Benchmark ideas

Compaction strategies to compare:

- Plain summarization.
- Only keep beginning and end, trim the middle.
- FIFO.
- Constraint Pinning — pin specific constraints so they survive compaction.

**Why this is worth doing and hasn't been done:** right now the "rules get dropped" research (ConstraintRot / governance decay) and the "entities get mixed up" research (Binding Drift) are two separate lines of work that don't talk to each other. Nobody has checked whether a fix built for one problem (e.g. Constraint Pinning, built for rule-dropping) also helps — or accidentally hurts — the other problem (entity binding drift). Running all of these strategies on one combined benchmark is a genuinely new comparison, and it's cheap because it reuses existing scenarios instead of inventing new ones.

## 12. Open research question

> Can a much cheaper, lightweight check-and-patch approach match the recovery rate of the heavier dependency-graph approach, at a fraction of the cost?
