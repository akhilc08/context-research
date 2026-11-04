# Session rule store

## Goal

Help long-running agents follow the user's current rules across delegation, persistent subagent sessions, and repeated context compaction. Test whether reliably supplying shared session rules improves actual behavior over simpler alternatives. The mechanism can remain simple. The research contribution may be empirical findings about instruction inheritance and updates.

## Agreed scope

The system is a temporary, automatically maintained `AGENTS.md` for one session.

- Capture explicit user rules and corrections from ordinary language. No special save command is required.
- Start with mandatory, session-wide workflow rules. Keep them active until the user amends or revokes them.
- Maintain the current rule state outside the conversation summary. Compaction must not rewrite or discard it.
- Remove revoked rules from the active set. Whether to retain a separate change record remains a design question.
- Have the harness supply all active rules directly. Do not depend on the agent remembering to read a file or matching rules to individual actions.
- Reflect accepted rule updates in the next model call. This does not cancel actions already in flight.
- Do not automatically carry rules into unrelated sessions.

Focus on one manager and persistent subagents within a session. Compare rule delivery to new and existing workers. Establish behavior without compaction before adding one fixed compaction method. Agent-generated lessons, soft preferences, ambiguous instructions, automatic task-specific expiry, and adversarial attacks are outside the initial study. Summary and plan rewriting are not part of the initial design.

Build a concrete, well-designed implementation, not a throwaway prototype. Bounded scope means fewer supported capabilities, not weaker engineering. The initial deliverable is a research system, not a general-purpose memory platform or production rollout.

## Research commitments

- Measure executed behavior, not just whether the agent can repeat a rule.
- Test permitted actions as well as prohibited ones. Blanket refusal is not success.
- Distinguish capture errors, incorrect updates, compaction loss, and violations despite correct rules being available.
- Evaluate a context intervention, not a new action-blocking enforcement layer.
- Hold one compaction method fixed before varying conditions. Do not start with a large matrix of methods and tweaks.
- Treat existing experiments as exploratory evidence. Do not assume their methods or conclusions are correct.
- Do not assume the rule store is novel. A properly maintained and reloaded instruction file is a legitimate baseline.
- Accept useful negative or diagnostic findings. A new mechanism is not required for a worthwhile result.

## Roadmap

1. **Design the rule store.** Specify capture, amendments, revocations, failures, and what the agent receives. Work through concrete examples before choosing storage or model details.
2. **Challenge the design with existing evidence.** Check relevant failures and prior work alongside the design. E17 already includes a maintained ledger and a ground-truth control. Identify what remains unanswered rather than repeat that study.
3. **Build the implementation and evaluation.** Use one inspectable manager-worker harness. Start with the [dependency-approval scenario](subagent-rule-update-scenario.md), using correct rule state to isolate delivery and adherence. Compare manager-mediated updates, creation-time pinning, and refreshed session rules. Reuse suitable tasks and create focused executable tasks where needed. Evaluate automatic capture and compaction after validating this comparison.
4. **Validate, then run the main study.** Check the implementation and grading before freezing the method and evaluating on held-out tasks. Measure adherence, permitted-task success, rule-state errors, context overhead, calls, and latency. Use a controlled executable sandbox with a smaller coding-task validation.
5. **Explain and publish the findings.** Establish what works, why it works, where it fails, and what it costs. Run targeted follow-ups needed to support those claims. Release the implementation, tasks, results, and paper.

## Still open

The exact rule representation, update mechanism, harness, models, tasks, grading, sample sizes, and budget remain to be specified. The novel contribution is not yet established.

The endpoint is a reproducible study of instruction inheritance and updates across persistent subagents, including their interaction with compaction. Building a store and reporting one score is not enough. General swarm coordination, arbitrary task-context sharing, and production integration are outside this scope.
