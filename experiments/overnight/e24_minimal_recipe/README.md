# E24: does the two-component minimal recipe hold up on new held-out sessions?

Status: pre-registration written 2026-10-02 at 11:15 EDT, before any item was generated or any session was built. Results are added below this section after the run; the pre-registration text is not edited afterwards. Deviations, if any, get their own section.

## Pre-registration

### Question

E21 tested a seven-part compaction recipe on 60 held-out sessions and found that two parts carried nearly all of its gain: pinning the operator's turns verbatim and in order, and pinning the active operation's request with a harness-written progress note. The five other parts (provenance clause, standing-rules list, striking revoked rules, checkpoint timing, fact block) showed no measurable effect. Those ablations were exploratory. E24 tests the two-part "minimal recipe" as a confirmatory claim, once, on a new benchmark in a new domain.

### Benchmark (held out)

Everything is new: a new fictional codebase ("furrow", an agricultural sensing and irrigation platform in Go, with TimescaleDB, NATS, MQTT, a Vue dashboard, Pulumi on GCP, and GitLab CI), new filler, and newly generated and validated rules, revocations, amendments, goal chains, procedures, ruled-out approaches, injected actions, and legitimate operator updates. Facts and identifiers are generated in code from new attribute lists with a new seed (2424). Neither ledgerly (E1 to E20) nor harborline (E21) items are reused.

Each session has 150 to 250 turns and the same item mix as E21: 2 active rules, 2 rules later revoked, 2 threshold rules later amended (one loosened, one tightened), a goal chain with 2 redirects, 2 versioned facts (2 and 3 values) with current and history questions, an exact identifier stated by the operator with a near-duplicate in a later tool output, a ruled-out approach, a subtle injected action in a tool output, a legitimate operator update, and a multi-step operation in progress (half the sessions end after a completed step, half with a non-idempotent step in flight). Planned n is 80 sessions.

Every generated item must pass a floor and a ceiling check in a short uncompacted context (3 samples, at least 2 of 3), as in E21. Three fixes for E21's known problems:

1. **Legitimate update made unambiguous.** The operator's request says plainly that the action is to be done at wrap-up, and the operator re-confirms it later in the session ("when you wrap up, still do X"). The validation ceiling uses the same wording.
2. **In-flight procedures with clearer async semantics.** The operator's procedure request lists each step's command and its read-only check command and says to wait for each step to finish and to check any step whose outcome is unknown before doing anything else. Completed steps are logged as "finished with exit 0"; the in-flight step is logged as a background job with no exit status yet. Non-idempotent steps must be plainly non-idempotent (no guards such as IF NOT EXISTS, ON CONFLICT, or a status filter). Pre-registered rule: if at least 10 procedures pass the in-flight ceiling check, in-flight sessions use only passing procedures and their next-step outcomes count in the primary metric. If fewer pass, in-flight sessions use all procedures, and their next-step outcomes are excluded from the primary metric and reported separately.
3. **Injection items kept but secondary.** The injected-action outcome is reported but is not part of the primary metric.

### Arms

All compacting arms use recursive compaction with a 250-word budget, 4 turns kept verbatim at each compaction, and E21's code for timing, the keeper, and the progress note.

| arm | compaction | timing | harness blocks |
|---|---|---|---|
| full | none (whole session) | | |
| plain | plain narrative (`common.SUMMARY_PROMPT`) | token threshold | none |
| structured | E9 structured checkpoint | threshold | none |
| pin_raw | plain | threshold | every operator turn from the summarized part, verbatim, in order |
| recipe | E21's full recipe, unchanged | checkpoint with threshold fallback | struck operator pin, versioned fact block, operation block with progress note (keeper-driven) |
| **minimal** | plain | threshold | operator turns verbatim in order, plus the operation request pinned with E13's safe progress note. Nothing else. |
| minimal_permit (exploratory) | plain | threshold | minimal plus one "Permitted now: you may ..." line per revoked rule (E20's best format) |

`plain`, `pin_raw`, `minimal`, and `minimal_permit` share one compaction chain, so they differ only in the harness blocks. The minimal recipe finds the operation request without any model call: it is the latest operator turn whose listed commands appear in the harness's own execution log. In the pin, that turn is replaced by a pointer to the operation block, as in E21. `minimal_permit` needs to know which rules were revoked; it uses E21's keeper for that and E20's permission rewrite prompt (one call per detected revocation, no hand edits).

### Metrics

Each session yields 16 graded outcomes per arm, as in E21: 2 active, 2 revoked, and 2 amended rule probes, 1 ruled-out probe, 1 goal probe, 1 operation next-step probe, 2 current-fact and 2 fact-history questions, 1 identifier question, and one wrap-up probe judged twice (injected action not performed; legitimate update performed).

- **Primary metric: mean per-item accuracy.** The mean of the 15 non-injection outcomes within a session (14 in in-flight sessions if the in-flight rule above excludes them), averaged over sessions, with a session-bootstrap 95% interval.
- Secondary, descriptive: harm (any primary outcome wrong; expected to saturate, so not tested), per-type accuracy with Wilson intervals, harmful repeats of non-idempotent steps, injected-action rate, legitimate-update rate, context tokens, and model calls per session.

### Confirmatory comparisons (one Holm family of 4, alpha 0.05)

All on per-session mean accuracy, paired by session.

1. minimal vs plain: superiority.
2. minimal vs full: superiority.
3. minimal vs pin_raw: superiority.
4. minimal vs recipe: non-inferiority with a margin of 3 percentage points.

Superiority tests are two-sided paired sign-flip permutation tests on per-session differences (100,000 resamples, seed 24); superiority is concluded when the Holm-adjusted p is below 0.05 and the mean difference favors minimal. The non-inferiority test is one-sided: H0 is that the mean of (minimal minus recipe) is at most -3 points. It is a sign-flip permutation test on the per-session differences shifted by +3 points (one-sided, 100,000 resamples). A paired session bootstrap 95% interval for the difference is reported next to it. Non-inferiority is concluded when the Holm-adjusted p is below 0.05.

**Margin rationale.** With 15 outcomes per session, one item is 6.7 points, so 3 points is less than half an item per session. It is smaller than the smallest component effect that mattered in E21 (the operation block, 3.2 points) and well below the operator pin (7.9). It is larger than any single dropped component's effect in E21 (0.3 to 1.6 points). So the test asks whether the five dropped components together are worth less than one component that clearly matters. A margin this tight is only affordable because the arms are paired on the same sessions.

Everything else is exploratory, including minimal_permit vs minimal, minimal vs structured, and all per-type comparisons.

### Judges

Reused unchanged from E21: E17's rule-application judge (version 2), the ruled-out judge, E13's step judge with its outcome rules, and E11's action judge. E2's goal judge is reused with its example nouns changed from freight terms to this domain's terms, as E21 itself did. Facts and identifiers use exact string matching. At least 40 judge verdicts are hand-checked blind, with Cohen's kappa per judge family.

### Second backbone

The run scripts take `--model`. The command is listed at the end; whether it is run depends on time and budget.

---
