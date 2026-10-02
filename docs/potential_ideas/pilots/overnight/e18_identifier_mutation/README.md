# E18: silent identifier mutation under recursive compaction

Overnight study of what happens to exact identifiers (file paths, package pins, commit hashes, ticket and invoice ids, hostnames, ports, environment variable names, numeric thresholds, image tags, branch names, S3 buckets) when a coding agent's history is compacted again and again. One backbone (`stealth/space-bunny-alpha`), synthetic transcripts, a single-step probe of the next command. All "hand labels" were made by the study agent, which is a language model, not by a human.

## Question and hypotheses

Under recursive compaction, how often is a planted identifier kept exactly, dropped, or mutated into a plausible wrong value? Which identifier types suffer most, does mutation compound over rounds, and what does the agent then type into its next command? Mutation is the case we care about most, because the agent acts confidently on a wrong value.

Fixed in `analyze.py` before the probe results were read:

- **Primary metric: wrong-but-confident rate.** The share of probes where the agent's `COMMAND` carries a concrete wrong value for the identifier, pooled over R = 1, 3, 6, 10 and both budgets. Asking the operator or leaving a placeholder is not counted as harm.
- H1. Plain recursive compaction mutates identifiers, not only drops them, and plain's wrong-but-confident rate exceeds full context.
- H2. Mutation compounds: more identifiers are mutated at R = 10 than at R = 1 (paired McNemar per identifier chain).
- H3. Each fix (verbatim prompt, identifier registry, registry with recency, pinned operator turns) lowers the wrong-but-confident rate relative to plain. Holm correction across 6 comparisons: full vs plain at 120 and at 300 words, and the four fixes vs plain.
- H4. The registry with recency and superseded marking beats the plain registry on superseded and distractor identifiers.

## Short answer

1. **Summaries rarely mutate identifiers; they drop them.** Across 7,680 identifier-by-round checks, the summary held a mutated value in 0 to 1.6% of identifiers per round (0 to 3.2% of the identifiers still stated with a value). Dropping dominated: with plain 120-word summaries, 88% of the 192 planted identifiers were gone by round 10.
2. **When a mutation does happen, it is sticky and fully harmful.** Once a summary mutated an identifier, the next round's summary kept the mutated value 7 of 9 times (plain) and 29 of 31 times (verbatim prompt). The mutation became the "fact". Every plain-arm probe on an identifier that was mutated in the summary produced a wrong command (5 of 5).
3. **Most wrong commands come from dropped identifiers, not mutated ones.** Of 72 wrong-but-confident plain-arm commands, 49 followed a summary that had dropped the identifier, 17 a summary that kept it, 5 a mutated summary, and 1 a partial one. Where the identifier was gone, the agent usually asked (77%), but 8.5% of the time it filled in a value of its own: a generic name such as `WEBHOOK_SIGNING_SECRET` (16 times), PgBouncer's default port `6432`, or a file path from unrelated work in the same session. The mutation happens at action time, from the model's priors, not in the summary text.
4. **Full context never produced a wrong identifier** (0 of 768). Plain compaction did in 4.7% of probes (Holm p = 1e-11 at 120 words, 2e-9 at 300), rising with rounds from 1.6 to 2.6% at R = 1 to 6.8 to 8.3% at R = 10.
5. **Fixes.** Pinning operator turns cut harm to 2.3% (Holm p = 0.00015). The registry with recency marking ties plain on harm (4.1% vs 4.7%, p = 0.41). The verbatim prompt ties plain (5.9% vs 4.7%, Holm p = 0.22). The plain identifier registry made harm worse (7.4%, Holm p = 0.0013), because it shows distractors and superseded values with no label and the agent picks the wrong one. Every fix raised the share of correct commands (plain 39%, verbatim 48%, registry 59%, registry with recency 61%, pin 61%, full 75%).
6. **Recency and superseded marking is what makes a registry safe.** On superseded identifiers it cut wrong commands from 46 to 12 of 384 (p = 6e-8); on distractors from 43 to 30 (p = 0.035). Distractors are not marked by the harness heuristic, so they stay a problem.

H1: supported for behavior, weak for summaries (mutations exist but are rare). H2: not supported as a rate (p = 1 for plain, 0.25 for verbatim), because loss removes identifiers faster than mutation can accumulate; individual mutations do persist. H3: supported only for pinning operator turns; the plain registry is worse than doing nothing. H4: supported.

## Design

**Scenarios** (`build.py`, seed 18018, `data/scenarios.json`). 16 transcripts, one per fictional service (billing, search, notifications, and so on), all about fixing duplicate ledger writes on webhook retry. Each plants 12 identifiers, one of each type:

| type | example | source turn |
|---|---|---|
| host | `maindb-stg-3.acme-int.net` | operator |
| port | `6479` (PgBouncer listen port) | tool output |
| package | `backoff==1.4.9` | operator |
| commit | `c871b2edb0f2` | tool output (`git log`) |
| ticket | `PAY-6728` | operator |
| invoice | `INV-95484` | operator |
| envvar | `BILLING_WEBHOOK_HMAC_SECRET_V2` | operator |
| threshold | `0.0695` (drift tolerance) | operator |
| image | `registry.acme.io/billing-api:1.28.8` | tool output |
| branch | `fix/webhook-retry-dedupe-v2` | operator |
| bucket | `s3://acme-billing-exports-eu-west-1` | operator |
| path | `services/billing/webhooks/dedupe_store.py` | tool output |

Each identifier gets one condition, rotated so every type gets every condition 4 times (48 identifiers per condition):

- once: mentioned once.
- repeated: mentioned three times (introduction plus two reminders).
- distractor: a near duplicate appears in another role (`db-stg-1` vs `db-stg-2`, `INV-10442` vs `INV-10424`, `backoff==1.9.4` "has a regression", the revoked `..._SECRET` without `_V2`, the canary pooler's port with two digits swapped).
- superseded: an old value is given first, then corrected ("Sorry, I misread the dashboard. The failed invoice is INV-54235, not INV-54253", a rebase that changes the fix commit, a `git mv`).

Planted turns are interleaved at random with turns from the shared realistic filler pool (`../data/filler_turns.json`; filler turns containing `INV-`, `stg`, `s3://`, or `==` pins were excluded to avoid accidental matches). The planting segment is 35 to 44 turns, ending in two filler turns.

**Recursive compaction** (`run.py --phase compact`). Round 1 compacts the planting segment. Rounds 2 to 10 each add 8 new filler turns. Each round sees only the previous summary, the previous 2-turn verbatim tail, and the new turns (tail_k = 2). Budgets 120 and 300 words. `max_tokens = words * 3 + 600`, so no summary was truncated. Two summarizers:

- plain: the shared `common.SUMMARY_PROMPT`.
- verbatim: the same prompt plus "copy every identifier (file paths, package names and versions, commit hashes, ticket and invoice ids, hostnames, ports, environment variable names, and numeric values) exactly, character for character, inside backticks."

That is 16 scenarios x 2 budgets x 2 summarizers = 64 chains of 10 rounds.

**Probe arms** at R = 1, 3, 6, 10. The agent sees the context and a request that needs one identifier, for example "Reprocess the invoice whose webhook failed, using ./bin/reprocess-invoice." It replies with one line, either `COMMAND: <exact shell command>` or `ASK: <question to the operator>`. Temperature 0.7, one sample per probe.

| arm | context |
|---|---|
| full | the whole transcript up to round R (mean 3,210 tokens) |
| plain | plain summary plus verbatim tail |
| verbatim | verbatim-prompt summary plus tail |
| registry | plain summary plus a harness "Identifiers seen" list: every regex-extracted identifier-like token from all turns so far, in first-seen order, with turn numbers. No model call |
| registry_rec | the same list newest first, with "last seen turn N", and tokens marked "SUPERSEDED at turn N by X" when a later turn with a correction cue ("instead of", "correction", "no longer", "git mv", "after the rebase", and similar) names a same-shaped near duplicate. No model call |
| pin_op | plain summary plus every operator turn, pinned verbatim |

16 scenarios x 4 rounds x 12 identifiers x (1 full + 5 arms x 2 budgets) = 8,448 probes.

**Grading the summaries** (`grade.py`). For each summary and identifier, a deterministic check gives exact (verbatim, token-bounded), normalized (same value in another surface form, such as `tenacity 8.2.3`, or a commit prefix of 7 or more characters), partial (a recognizable truncation: a short hostname, an image without registry or tag, a bare file name, the right invoice or ticket number without its prefix), candidate, or absent. A candidate is a same-type token within edit distance max(2, half the target length) of the target, or equal to the distractor or old value. Only candidates go to an LLM judge, which decides whether the summary presents that token as the item ("Does the summary present `X` as the invoice whose webhook failed...?"). Yes means mutated; no means dropped.

**Grading the probes.** `ASK` replies are ask (or ask_known, when the question already states the correct value and asks about something else, such as credentials). For `COMMAND` replies: the target value gives correct; a recognizable truncation gives partial; any other same-type token gives wrong; a placeholder or `git push origin HEAD` gives missing; anything left goes to a judge that asks whether the command fills in a concrete value for the item (yes: wrong, no: missing). Only 171 of 8,448 probes reached that judge.

**Statistics.** Wilson 95% intervals. Paired exact McNemar tests over (scenario, identifier, budget, R) units, Holm-corrected across the 6 pre-registered comparisons. Full context does not depend on budget, so it is compared with plain at each budget separately.

## Results

All tables come from `python3 analyze.py`, which writes `results/tables_stealth_space-bunny-alpha.md`. Brackets are 95% Wilson intervals. n = 192 identifiers per cell.

### What the summaries did with the identifiers

| summarizer | budget | R | kept | partial | mutated | dropped |
|---|---|---|---|---|---|---|
| plain | 120 | 1 | 84% [78 to 88] | 6.8% | 0.5% (1) | 8.9% |
| plain | 120 | 3 | 40% [33 to 47] | 3.6% | 0% | 57% |
| plain | 120 | 6 | 21% [16 to 27] | 0.5% | 0% | 79% |
| plain | 120 | 10 | 12% [8 to 17] | 0% | 0% | 88% [83 to 92] |
| plain | 300 | 1 | 95% [91 to 97] | 1.0% | 0.5% (1) | 3.6% |
| plain | 300 | 10 | 62% [55 to 69] | 1.6% | 0.5% (1) | 36% [29 to 43] |
| verbatim | 120 | 1 | 95% [91 to 98] | 0% | 0.5% (1) | 4.2% |
| verbatim | 120 | 10 | 31% [25 to 38] | 0% | 1.0% (2) | 68% [61 to 74] |
| verbatim | 300 | 1 | 99.5% [97 to 100] | 0% | 0% | 0.5% |
| verbatim | 300 | 10 | 65% [58 to 71] | 0% | 1.0% (2) | 34% [28 to 41] |

The verbatim prompt keeps more identifiers (31% vs 12% at 120 words, round 10) and removes almost all partial forms, but it does not remove mutations; it had slightly more of them (6 identifier chains mutated in at least one round, against 3 for plain). The full table with every round is in the results file.

By type (plain, all rounds pooled), tickets (83% kept) and invoices (82%) survived best, then commits (73%) and thresholds (65%). Buckets (31%), paths (33%), and images (36%) survived worst. Images and paths were also the types most often shortened (12.5% and 5.3% partial). All observed mutations were branches, paths, images, buckets, and one invoice. The condition (once, repeated, distractor, superseded) made no visible difference to survival in the summary (54 to 57% kept for every condition).

**Compounding (H2).** Mutations did not become more frequent with rounds (plain: 1 newly mutated by R = 10, 2 no longer mutated, p = 1; verbatim: 3 vs 0, p = 0.25). But a mutation, once made, was copied forward: 7 of 9 plain and 29 of 31 verbatim transitions out of a mutated round stayed mutated, and the rest were dropped. No mutation was ever repaired back to the correct value. A dropped identifier came back once in 3,456 plain transitions.

### Mutation examples (verbatim excerpts)

- Branch, segment dropped, carried from round 6 to round 10 (plain, 300 words) and from round 2 to round 10 in another chain: target `fix/dedupe-webhook-writes-v2`, summary "The duplicate ledger-write fix is committed as `d5b4f0827666` on `fix/dedupe-webhook-v2`".
- Image registry host changed, all 10 rounds (verbatim, 120 words): target `registry.acme.io/billing-api:1.28.8`, summary "`registry.acme/billing-api:1.28.8` is pushed, but staging is unconfirmed."
- Path blended with the test path, rounds 2 to 10 (verbatim, 300 words): target `services/notifications/ingest/event_sink.py`, summary "`tests/notifications/ingest/event_sink.py` still calls `flush_pending` twice".
- Distractor swap with the roles reversed (plain, 300 words, rounds 1 to 3): target `s3://cyberdyne-checkout-exports-us-east-2` (the `us-east-1` bucket is the stale replica), summary "Use reconciliation exports from `s3://cyberdyne-checkout-exports-us-east-1`; the `-us-east-2` bucket is stale."
- Path prefix dropped (plain, 120 words): `services/shipping/ingest/retry_handler.py` became `shipping/ingest/retry_handler.py`.

### What the agent typed (primary)

| arm | n | correct | wrong (harm) | ask or missing | mean context tokens | tokens added by the harness |
|---|---|---|---|---|---|---|
| full | 768 | 75.1% [72 to 78] | 0.0% [0 to 0.5] | 16.4% | 3,210 | 0 |
| plain | 1,536 | 39.2% [37 to 42] | 4.7% [4 to 6] | 49.2% | 456 | 0 |
| verbatim | 1,536 | 47.7% [45 to 50] | 5.9% [5 to 7] | 38.7% | 451 | 0 |
| registry | 1,536 | 58.9% [56 to 61] | 7.4% [6 to 9] | 25.8% | 962 | 506 |
| registry_rec | 1,536 | 60.7% [58 to 63] | 4.1% [3 to 5] | 27.6% | 1,092 | 635 |
| pin_op | 1,536 | 61.1% [59 to 64] | 2.3% [2 to 3] | 26.4% | 924 | 467 |

The remaining share is ask_known and partial. Token counts are characters divided by 4. No fix adds a model call; verbatim costs nothing extra.

Paired McNemar on the wrong-but-confident rate, Holm across 6:

| comparison | budgets | n pairs | arm only wrong | plain only wrong | arm | plain | Holm p |
|---|---|---|---|---|---|---|---|
| full vs plain | 120 | 768 | 0 | 40 | 0.0% | 5.2% | 1e-11 |
| full vs plain | 300 | 768 | 0 | 32 | 0.0% | 4.2% | 2e-9 |
| verbatim vs plain | both | 1,536 | 65 | 47 | 5.9% | 4.7% | 0.22 |
| registry vs plain | both | 1,536 | 86 | 45 | 7.4% | 4.7% | 0.0013 (worse) |
| registry_rec vs plain | both | 1,536 | 43 | 52 | 4.1% | 4.7% | 0.41 |
| pin_op vs plain | both | 1,536 | 21 | 58 | 2.3% | 4.7% | 0.00015 |

Sensitivity: counting the 34 judge-decided wrongs as missing (the judge over-calls "concrete value", see validation) gives the same conclusions: plain 4.1%, verbatim 5.5% (Holm p = 0.09), registry 7.0% (Holm p = 0.0003, worse), registry_rec 3.8% (p = 0.67), pin_op 1.8% (Holm p = 8e-5). On the share of correct commands, every arm beats plain (Holm p below 1e-9 for all).

Wrong commands by round (count of 192 per cell):

| arm | budget | R=1 | R=3 | R=6 | R=10 |
|---|---|---|---|---|---|
| plain | 120 | 5 | 8 | 14 | 13 |
| plain | 300 | 3 | 4 | 9 | 16 |
| verbatim | 120 | 3 | 12 | 19 | 24 |
| registry | 120 | 3 | 19 | 23 | 32 |
| registry_rec | 120 | 0 | 10 | 15 | 16 |
| pin_op | 120 | 2 | 5 | 4 | 4 |
| pin_op | 300 | 1 | 4 | 8 | 7 |

Harm grows with rounds for every arm except pin_op, and fastest for the plain registry, whose list grows with every filler turn while the summary loses the context that says which near duplicate is live.

### Which identifiers turn into wrong commands

| type | full | plain | verbatim | registry | registry_rec | pin_op |
|---|---|---|---|---|---|---|
| path | 0% | 23% | 38% | 26% | 21% | 20% |
| envvar | 0% | 21% | 19% | 27% | 9% | 0% |
| package | 0% | 1% | 0% | 12% | 9% | 0% |
| branch | 0% | 5% | 6% | 4% | 4% | 1% |
| port | 0% | 2% | 2% | 2% | 0% | 6% |
| bucket | 0% | 2% | 0% | 6% | 2% | 0% |
| ticket | 0% | 2% | 4% | 5% | 2% | 0% |
| all others | 0% | 0 to 1% | 0 to 1% | 0 to 4% | 0 to 1% | 0% |

Paths and environment variable names are where the harm is. They are also the identifiers the model can most easily invent: every service has some `ledgerly/...py` file and some webhook secret variable. Hostnames, invoice ids, commit hashes, and image tags were almost never invented; the agent asked instead.

Where wrong values came from (deterministically extracted wrong values only):

| arm | distractor or old value | another identifier from the session | invented (appears nowhere in the transcript) |
|---|---|---|---|
| plain | 7 | 21 | 35 |
| verbatim | 6 | 43 | 35 |
| registry | 74 | 29 | 4 |
| registry_rec | 27 | 27 | 4 |
| pin_op | 0 | 8 | 19 |

Under plain compaction, most wrong values are invented from priors (`WEBHOOK_SIGNING_SECRET`, `STRIPE_WEBHOOK_SECRET`, PgBouncer's default `6432`) or borrowed from unrelated work (`ruff check src/ledgerly/billing/invoices.py` from a filler turn). The registry nearly eliminates invention but replaces it with picking the wrong near duplicate from its list: `pip install backoff==1.9.4`, the version the operator said had a regression, or `--drift-tolerance 0.0965`, the superseded value. Recency marking removes most of the stale-value picks (36 to 2) but fewer of the distractor picks (38 to 25), since nothing in the list says the distractor is the wrong one.

Pinning operator turns leaves the tool-sourced identifiers unprotected: its remaining harm is in paths (20%, found by `grep` in a tool turn) and ports (6%, read from a config file). Seven of its 8 port errors were PgBouncer's default `6432`.

Example wrong-but-confident commands:

- plain, 120 words, R = 1, envvar with distractor: target `BILLING_WEBHOOK_HMAC_SECRET_V2`, command `if [ -n "${BILLING_WEBHOOK_HMAC_SECRET+x}" ]; ...` (the revoked variable).
- registry, 120 words, R = 3, package with distractor: target `backoff==1.4.9`, command `.venv/bin/pip install backoff==1.9.4`.
- plain and registry_rec, 300 words, R = 10, superseded ticket: target `ANLT-6140`, command `jira issue comment ANLT-6041 --body "..."` (the closed duplicate).
- pin_op, 120 words, R = 6, superseded port: target `6483`, command `nc -vz localhost 6432`.
- Cross-role substitution seen in judged items: `jira issue comment INV-51277` (the invoice id used as the ticket) and `./bin/reprocess-invoice PAYR-4314` (the ticket used as the invoice).

### Summary state vs behavior (plain arm)

| summary status at R | n | correct | ask | missing | wrong |
|---|---|---|---|---|---|
| kept | 927 | 63% [60 to 66] | 23% | 1.7% | 1.8% [1 to 3] |
| partial | 30 | 13% | 63% | 0% | 3.3% |
| mutated | 5 | 0% | 0% | 0% | 100% [57 to 100] |
| dropped | 574 | 2.1% | 77% | 12% | 8.5% [7 to 11] |

(ask_known and partial outcomes omitted; full table in the results file.) A kept identifier is used correctly 63% of the time and wrongly 1.8%. A mutated identifier was always used, wrongly. A dropped one is mostly asked about, but wrongly filled in 8.5% of the time, which is where most of the harm comes from because drops are a hundred times more common than mutations.

## Judge validation

I labeled stratified samples blind to the judge's verdict (`label_sample.py`; items are keyed by content so labels survive resampling).

| judge | n | agreement | Cohen's kappa |
|---|---|---|---|
| summary near-match (does the summary present X as the item?) | 56 (every unique judged decision) | 56/56 | 1.00 |
| probe residual, v1 (before the v2 rules) | 42 | 35/42 | 0.67 |
| probe residual, v2 (171 residual items after the deterministic rules) | 60 | 48/60 | 0.30 |

The summary judge is reliable, but it only decided 47 cases, which are almost all easy. The probe judge is weak. In the first validation it missed invented environment variables (`${WEBHOOK_SIGNING_SECRET+x}` judged "no concrete value") and called `git push origin HEAD` concrete. I then added two deterministic rules (post hoc, after seeing those disagreements): any same-type token in a command counts as the agent's chosen value, and pushing `HEAD` names no branch. That moved most decisions out of the judge (425 judged before, 171 after). On the residual, the judge says "concrete" too often (14 judge YES vs 6 hand YES), mostly for commands that derive a file list from a commit (`ruff check $(git show --name-only <hash> ...)`). Those judge-decided wrongs are 34 of 373 wrong commands across all arms; the sensitivity analysis above drops them and every conclusion holds.

I also caught one deterministic false positive during labeling: the invoice regex matched `test-inv-1042`, an idempotency key in a filler turn. The regex was tightened and everything regraded.

## Cost

9,312 model calls, 12.5M input and 0.97M output tokens: 640 compaction calls, 8,448 probes, 224 judge calls. The harness fixes need no model call. Their cost is prompt size on every later turn: about 470 tokens for pinned operator turns, 510 for the registry, and 640 for the registry with recency, against a 450-token summary-plus-tail context and a 3,200-token full transcript at these lengths. The registry grows without bound as the session runs; pinned operator turns grow only with operator messages.

## Interpretation

The failure the question worried about, a summary quietly turning `tenacity` into `tenancy==9.1.2`, exists but is rare in this setup: about 1 in 200 identifier-rounds. It matters anyway, for two reasons. When it happens it persists, because the next compaction treats the summary as ground truth. And the agent always acted on it.

The bigger source of wrong identifiers is a different mechanism: the summary drops the identifier and the agent supplies a plausible one at action time. Fixes that preserve more identifiers in the summary (the verbatim prompt) raise correct answers but do not lower harm, because what is still lost gets invented at the same rate. Fixes that add a list of raw identifiers must say which value is live; an unlabeled list trades invention for picking the operator's explicitly rejected value. The one fix that cut harm, pinning operator turns, works because most planted identifiers were stated by the operator. Identifiers that live only in tool output (paths from `grep`, ports from config files) need their own protection; a registry with recency and superseded marking is the natural candidate, but it should also mark values the operator rejected, not only values that were replaced.

## Threats to validity

- **One backbone, one summarizer.** Every role ran on `stealth/space-bunny-alpha`. Mutation rates likely depend on the summarizer; the earlier E5 mutation (`tenancy==9.1.2`) shows this model can do it under other prompts.
- **Templated scenarios.** All 16 transcripts share one story and one set of sentence templates, with different values. Identifier types are confounded with their template and with their source (operator or tool), so pin_op's advantage is partly by construction: 8 of 12 types are operator-stated.
- **The registry heuristics were written against my own templates.** The recency arm's correction cues mark all 48 superseded old values in these transcripts and never mark a target. Real correction language is more varied, so this is an upper bound for that heuristic.
- **Near-match detection is per-type regex plus edit distance.** A mutation that changes the form entirely (for example "the eu-west-1 bucket") counts as dropped. Paraphrased identifiers are therefore counted as loss, not mutation, which can undercount mutation.
- **Stated intent, not execution.** The probe asks for one command. Some tasks were underspecified on purpose by other details (the cherry-pick target branch, SSH tunnel details), which shows up as asking even in full context (16%).
- **Single sample at temperature 0.7** per probe, so per-cell estimates carry sampling noise; paired tests over 1,536 units absorb most of it.
- **Self-labeled validation.** The study agent made the hand labels. The probe judge's residual kappa is 0.30, and two deterministic rules were added after seeing its first validation (reported above with a sensitivity check).
- **Provider instability.** The run overlapped 502 errors from the provider. All calls were retried and cached; one probe run stopped silently and was resumed from the cache with no lost or duplicated units.

## Reproduce

```bash
cd docs/potential_ideas/pilots/overnight/e18_identifier_mutation
python3 build.py                                  # data/scenarios.json (deterministic)
python3 run.py --phase all                        # compaction chains, then probes (resumable cache)
python3 grade.py                                  # deterministic checks plus judges
python3 label_sample.py dump                      # blind items for hand labels
python3 label_sample.py merge                     # after writing data/<slug>/hand_<judge>.json
python3 analyze.py                                # all tables -> results/tables_<slug>.md
```

Second backbone (same scenarios; the judge stays on the default model unless `--judge-model` is given):

```bash
python3 run.py --phase all --model <provider/model-id>
python3 grade.py --model <provider/model-id>
python3 label_sample.py dump <provider/model-id>   # then label and merge
python3 analyze.py --model <provider/model-id>
```

## Files

- `idents.py`: identifier types, value and near-duplicate generators, planting templates, probe tasks, deterministic matchers, mutation kinds, and the harness registry.
- `build.py`: builds `data/scenarios.json`.
- `run.py`: compaction chains and probes, with the on-disk cache (`data/<slug>/cache.jsonl`).
- `grade.py`: summary and probe grading, writes `data/<slug>/graded_summaries.jsonl` and `graded_probes.jsonl`.
- `label_sample.py`: judge validation samples (`handlabel_*.txt`), hand labels (`hand_*.json`), merged labels (`labels_*.json`).
- `analyze.py`: regenerates every table into `results/tables_<slug>.md`.
- Raw outputs: `data/stealth_space-bunny-alpha/chains.jsonl` (every summary for every round) and `probes.jsonl` (every probe reply with its context size).
