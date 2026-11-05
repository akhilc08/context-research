# E8: compaction in the middle of a multi-step operation

Overnight pilot on whether a compacted agent resumes an ordered procedure at the right step, or repeats completed steps, skips pending ones, or wanders off. One backbone (`stealth/space-bunny-alpha`), synthetic transcripts, single-step probe. Treat every number here as a pilot result.

## Question and hypotheses

When compaction fires partway through an ordered procedure (a migration, a release checklist, a rename across files, a batch of invoices), does the agent pick the correct next command? And does it matter whether compaction fires after a run of side work (threshold), exactly when a step closes (harness-verified checkpoint), or while a step's command is still running (mid-step)?

Hypotheses, fixed in `analyze.py` before the main results were read:

- H1. Plain summary lowers correct-next relative to full context.
- H2. A structured TRACE-style checkpoint, a harness execution ledger, and a progress watchpoint each raise correct-next over plain summary.
- H3. For plain summary, compacting at a checkpoint beats compacting at a threshold.
- Mid-step compaction produces the most harmful repeats.

**Primary metric:** correct-next rate (the proposed command is the next pending step), all timings pooled, compared with paired exact McNemar tests and Holm correction across the 12 comparisons listed under Results. Everything labelled "exploratory" was added after seeing the data, including the plan-pinning follow-up.

## Design

**Procedures.** The model generated 20 procedures of 7 to 9 ordered steps (`gen_procedures.py`, `data/procedures.json`). Each step has a distinct shell command, a realistic success output, an idempotency flag, and a read-only verify command. Every procedure has at least 2 non-idempotent steps. Domains include a Postgres column migration, a PyPI release, a Go rename across 7 files, credential rotation, payroll, refunds, and a Kafka repartition. I also built 10 batch tasks by hand (`build.py`): 24 items with random ids (invoices to charge, customers to email, charges to refund, tenants to migrate, shards to re-encrypt, accounts to credit), one command per item. 4 of the 6 batch templates are non-idempotent.

**Transcripts** (`build.py`, seed 8008). Turn 1 is the operator's request, which lists every step's command (or every item id). The agent has completed k steps. Each completed step is one turn, `Ran <cmd> (exit 0): <output>`. Turns from the shared realistic filler pool (unrelated coding work by the same agent) are interleaved: 1 or 2 before every procedure step, and some before every third batch item. k is early, mid or late (2, about N/2, N-2 for procedures; 5, 12, 19 of 24 for batches). Three timings:

- threshold: step k completes, then 3 filler turns, then compaction. The last step event is inside the summarized part.
- checkpoint: compaction fires right as step k returns exit 0. The step k event is the last verbatim turn.
- mid-step: step k+1's command was issued, but its output was never seen.

That gives 30 tasks x 3 levels x 3 timings = 270 transcripts, averaging 15 turns.

**Compaction.** Recursive, in chunks of 6 turns. Each round sees the previous summary, the previous verbatim tail, and the new chunk. The verbatim tail is tail_k=2 and the summary is capped at 150 words. This gives 2 to 3 compaction rounds per transcript.

**Methods.** All methods see the same transcript, and none sees the grader's labels.

| method | context the agent sees |
|---|---|
| full | the whole transcript, no compaction (ceiling) |
| plain | plain summary (`common.SUMMARY_PROMPT`) plus tail |
| structured | TRACE-style markdown checkpoint (Goal, Constraints, Progress done / in progress / blocked, Next steps) plus tail |
| ledger | plain summary plus a harness ledger of every executed command and its exit code (in-flight shown as "running, no exit code"); no model call |
| ledger_only | ablation: ledger plus tail, no summary |
| watchpoint | plain summary. A harness question asks the agent which step it last completed. The harness compares the answer with its own execution record and appends a progress note only if the answer is wrong |
| note_always | ablation: plain summary plus the same progress note, always appended (no comparator) |
| pin_plain, pin_ledger, pin_note | exploratory follow-up: the original operator request (the plan with its commands, or the item list), kept verbatim, plus plain, ledger, or note_always |

The progress note reads, for example: "Last completed step: step 5 of 8 (`cmd`). Steps 6 to 8 have not been completed; the command for step 6 was issued but its result has not been observed." It is derived from the harness's own ledger, not from the truth labels.

**Probe.** "Continue with the operator's requested task. What exact command do you run next?", answered as `COMMAND: ... / REASON: ...` at temperature 0.7, one sample per case.

**Grading.** An LLM judge (`grade.py`, temperature 0) sees only the step list and the proposed command, never k, the timing, or the method. It labels the command step j, verify j (a read-only check of step j or of its running command), or other. The outcome follows from the truth:

- After a completed step: step k+1 is correct; step j ≤ k is a repeat (harmful if step j is non-idempotent); step j ≥ k+2 is a skip.
- Mid-step: verifying step k+1, or re-running it when it is idempotent, is correct. Re-running it when it is non-idempotent is a harmful repeat. Moving on to step k+2 is "proceed unverified" and counts as a skip.

## Results

n = 270 transcripts per method (180 procedure, 90 batch). Each timing has 90. Brackets are 95% Wilson intervals.

### Correct-next, primary metric (all timings pooled)

| method | correct-next | repeat | harmful repeat | skip | other |
|---|---|---|---|---|---|
| full | 189/270 = 70% [64, 75] | 2% | 1/270 | 29% | 2 |
| plain | 84/270 = 31% [26, 37] | 9% | 5/270 | 8% | 124 |
| structured | 130/270 = 48% [42, 54] | 6% | 1/270 | 12% | 71 |
| ledger | 93/270 = 34% [29, 40] | 7% | 2/270 | 6% | 123 |
| ledger_only | 69/270 = 26% [21, 31] | 6% | 1/270 | 2% | 161 |
| watchpoint | 85/270 = 31% [26, 37] | 8% | 3/270 | 10% | 118 |
| note_always | 100/270 = 37% [31, 43] | 12% | 11/270 | 10% | 97 |
| pin_plain (exploratory) | 176/270 = 65% [59, 71] | 5% | 1/270 | 27% | 10 |
| pin_ledger (exploratory) | 190/270 = 70% [65, 76] | 3% | 1/270 | 24% | 7 |
| pin_note (exploratory) | 210/270 = 78% [72, 82] | 15% | 20/270 | 13% | 1 |

The pooled numbers mix in mid-step cases, where even full context scores low (see below). The cleaner view uses only the timings that follow a completed step (threshold and checkpoint, n=180):

| method | correct-next, completed-step timings |
|---|---|
| full | 178/180 = 99% [96, 100] |
| plain | 44/180 = 24% [19, 31] |
| structured | 86/180 = 48% [41, 55] |
| ledger | 42/180 = 23% [18, 30] |
| ledger_only | 7/180 = 4% [2, 8] |
| watchpoint | 49/180 = 27% [21, 34] |
| note_always | 56/180 = 31% [25, 38] |
| pin_plain | 158/180 = 88% [82, 92] |
| pin_ledger | 171/180 = 95% [91, 97] |
| pin_note | 178/180 = 99% [96, 100] |

### By timing (correct-next, n=90 each)

| method | threshold | checkpoint | mid-step (strict) | mid-step (lenient: also proceed) |
|---|---|---|---|---|
| full | 98% [92, 99] | 100% [96, 100] | 12% [7, 21] | 96% [89, 98] |
| plain | 14% [9, 23] | 34% [25, 45] | 44% [35, 55] | 62% [52, 72] |
| structured | 40% [30, 50] | 56% [45, 65] | 49% [39, 59] | 78% [68, 85] |
| ledger | 16% [9, 24] | 31% [22, 41] | 57% [46, 66] | 62% [52, 72] |
| ledger_only | 1% [0, 6] | 7% [3, 14] | 69% [59, 78] | 70% [60, 78] |
| watchpoint | 20% [13, 29] | 34% [25, 45] | 40% [30, 50] | 60% [50, 70] |
| note_always | 28% [20, 38] | 34% [25, 45] | 49% [39, 59] | 69% [59, 78] |
| pin_plain | 78% [68, 85] | 98% [92, 99] | 20% [13, 29] | 97% [91, 99] |
| pin_ledger | 91% [83, 95] | 99% [94, 100] | 21% [14, 31] | 93% [86, 97] |
| pin_note | 98% [92, 99] | 100% [96, 100] | 36% [26, 46] | 76% [66, 83] |

Progress level (early, mid, late) made little difference for any method. See `data/main/tables.txt`.

### Paired tests (exact McNemar on correct-next; Holm across this family of 12)

| comparison | counts | discordant | p | Holm p |
|---|---|---|---|---|
| full vs plain | 189 vs 84 | 141:36 | 7e-16 | 8e-15 |
| structured vs plain | 130 vs 84 | 73:27 | 5e-6 | 4e-5 |
| ledger vs plain | 93 vs 84 | 30:21 | 0.26 | 0.89 |
| watchpoint vs plain | 85 vs 84 | 33:32 | 1.0 | 1.0 |
| note_always vs plain | 100 vs 84 | 37:21 | 0.048 | 0.27 |
| ledger_only vs ledger | 69 vs 93 | 23:47 | 0.006 | 0.039 |
| note_always vs watchpoint | 100 vs 85 | 32:17 | 0.044 | 0.27 |
| ledger vs full | 93 vs 189 | 45:141 | 1e-12 | 1e-11 |
| plain: checkpoint vs threshold (paired by task and k) | 31 vs 13 of 90 | 27:9 | 0.004 | 0.032 |
| full: checkpoint vs threshold | 90 vs 88 | 2:0 | 0.5 | 1.0 |
| plain: checkpoint vs mid-step | 31 vs 40 | 17:26 | 0.22 | 0.89 |
| full: checkpoint vs mid-step | 90 vs 11 | 79:0 | 3e-24 | 4e-23 |

The exploratory follow-up family, Holm-corrected within itself:

| comparison | counts | p | Holm p |
|---|---|---|---|
| pin_plain vs plain | 176 vs 84 | 1e-14 | 7e-14 |
| pin_ledger vs pin_plain | 190 vs 176 | 0.039 | 0.077 |
| pin_note vs pin_plain | 210 vs 176 | 6e-8 | 2e-7 |
| pin_ledger vs ledger | 190 vs 93 | 6e-14 | 2e-13 |
| pin_note vs note_always | 210 vs 100 | 1e-20 | 8e-20 |
| pin_ledger vs full | 190 vs 189 | 1.0 | 1.0 |

Harmful repeats are rare overall (0 to 5 of 270 for most methods), so the per-method comparisons are underpowered. One is clear: pin_note has more harmful repeats than plain (20 vs 5, discordant 20:5, exact p=0.004, exploratory). All 20 are re-runs of the in-flight non-idempotent command in mid-step cases.

### Where the "other" answers go (exploratory, heuristic split)

The largest failure is not repeating or skipping but leaving the procedure altogether. I split "other" by whether the command's leading tool appears in any procedure step:

- Threshold timing: the compacted agent mostly resumes the filler side work from the verbatim tail (`pytest`, `sed -n` on a test file, `rg`). Off-task rates are plain 64% [54, 74], ledger 53%, watchpoint 50%, structured 36%, and ledger_only 89%. Full context: 0%.
- Checkpoint timing on batch tasks: the summary drops the 24-id list, so the agent calls the right tool on an id that is not in the list (made up, such as `tnt_53108`) or on a placeholder (`--charge <next_charge_id>`). This happened in 17 of 30 plain cases, 14 of 30 ledger cases, and 13 of 30 watchpoint and note_always cases. This is deletion, not disorientation: no position hint can fix it because the remaining work itself is gone.
- Pinning the original request removes both. pin_note has 0 off-task answers and 0 bad targets in all 270 cases.

### Progress watchpoint

The extraction question ("which step did you last complete?") matched the harness's record in only 128 of 270 cases (47%). Errors almost always under-counted, by 1 to 3 steps. So the comparator patched 142 cases. On patched cases, watchpoint reached 36% [28, 44] correct-next against 32% [25, 40] for plain on the same cases. The patch tells the agent its position, but without the plan the agent still does not know what step k+1 is, or prefers the side work in the tail.

### Cost

Per case, from the shared usage log. Output tokens exclude hidden reasoning tokens.

| method | calls | input tokens | output tokens | agent context (chars) |
|---|---|---|---|---|
| full | 1.0 | 1350 | 94 | 3844 |
| plain | 3.8 | 2548 | 951 | 1368 |
| structured | 3.8 | 2997 | 1276 | 1689 |
| ledger | 3.8 | 2927 | 916 | 2560 |
| ledger_only | 1.0 | 745 | 175 | 1618 |
| watchpoint | 4.8 | 3135 | 1030 | 1495 |
| note_always | 3.8 | 2605 | 958 | 1578 |
| pin_plain | 3.8 | 2890 | 797 | 2563 |
| pin_ledger | 3.8 | 3269 | 786 | 3755 |
| pin_note | 3.8 | 2947 | 789 | 2773 |

The transcripts are short, so the compacted contexts are not much smaller than full context. The cost comparison that matters is the extra cost on top of plain summary. Ledger, note and pin add no model calls. Watchpoint adds one. Structured costs the same number of calls with about 35% more summary tokens. The whole experiment used 7,489 calls (about 6.1M input and 1.4M output tokens), including 2,742 judge calls.

## Judge validation

I hand-labelled a seeded sample of 48 judged responses (36 procedure, 12 batch; `sample_handlabel.py`, `data/main/handlabels.json`). I labelled them blind to the judge's labels, from the step list and the command only. Outcome-category agreement was 41/48 = 85% [73, 93], Cohen's kappa 0.79. Of the 7 disagreements, 3 were commands I counted as the correct next step that the judge called "other". These were paraphrases: a generic `python3 -m pytest -q` for a step running specific tests, a replay job with a different name, and `ps | grep perl` for an in-flight rename. The other 4 were ambiguous verify-or-repeat boundaries. So the judge probably understates correct-next somewhat for compacted methods, which paraphrase more. The direction of the main effects (plain far below full, pinning near full) is much larger than this error. On batch cases, a deterministic id parser agreed with the judge on (kind, index) in 815/900 = 91% of cases and on the step index in 500/500 cases where both said "step". The parser's misses were mostly its own naive verify-or-act rule. The hand-label sample predates the follow-up and contains only the main methods.

Known judge error: in two cases the judge mapped a placeholder id (`<NEXT_UNCOMPLETED_ACCOUNT_ID>`) to an earlier step, which counts as a harmful repeat. These should be "other" and slightly inflate the harmful-repeat counts for plain and structured.

## Interpretation

1. **Plain summary disorients badly mid-procedure (H1 supported).** After a completed step, correct-next falls from 99% with full context to 24% with plain summary. Repeats and skips are a small part of this. Mostly the agent either takes up the side work in its verbatim tail or, for batches, invents the next target.
2. **Most of the loss here is deletion of the plan, not loss of position (H2 mostly not supported).** A ledger of executed commands (34%, Holm p=0.89) or a progress watchpoint (31%, p=1.0) barely helped. Both tell the agent where it is, but the summary has already dropped what comes next. A structured checkpoint helped significantly (48%) because it tends to keep the step list. Keeping the original request verbatim brought plain to 88% on completed-step timings. Adding the ledger brought it to 95%, and adding the progress note to 99%, matching full context. The order matters: position information pays off only once the plan is present. In this setup, TRACE's disorientation is real (pin_note beats pin_plain, p=2e-7), but it is the smaller of the two losses.
3. **Timing matters for plain summary (H3 supported).** Plain at a checkpoint got 34%, against 14% at a threshold (paired Holm p=0.03). The difference is mainly that at a checkpoint the last step stays in the verbatim tail, while at a threshold the tail is side work. With the plan pinned, the gap narrows (pin_plain 98% vs 78%), and with the progress note it disappears.
4. **The mid-step case does not behave the way the brief assumed.** With full context, the agent proceeded to step k+2 without checking the in-flight step 83% of the time and rarely re-ran it. Compaction made agents more cautious. They verified more and proceeded less, which is why plain "beats" full on strict mid-step correctness. That is not a benefit of compaction, and the strict mid-step metric mostly measures caution. Whether proceeding is wrong depends on the harness. Most real harnesses return the tool result before compacting, so this case may be rare in practice.
5. **A progress note can cause the harm it is meant to prevent.** Telling the agent "steps 6 to 8 have not been completed; the command for step 6 was issued but its result has not been observed" led it to re-issue step 6. Harmful repeats rose from 1 of 90 (plain, mid-step) to 7 (note_always) and 20 (pin_note), for example re-sending a renewal email or re-running a `payrollctl payments submit`. Any in-flight note should say "check its status before re-running", or omit "not completed" for the in-flight step. This is untested.

## Qualitative examples

- Off-task drift (P17-k4-threshold, ledger). The ledger correctly shows 4 Kafka steps with exit 0. The tail is filler about a CSV exporter, and the agent answers `grep -n "open\|write_rows" ledgerly/exporters/csv_export.py`.
- Made-up target (B09-k19-checkpoint, watchpoint). The agent proposes `./bin/tenant-migrate --tenant tnt_53108 --to-version 14 ...`, but tnt_53108 is not one of the 24 tenants. The summary had dropped the list.
- Genuine double refund (B08-k19-checkpoint, plain, watchpoint, and note_always all agree): `payments-cli refunds create --charge ch_51416 ...`. ch_51416 is item 10, refunded long before.
- Full context proceeding past an in-flight step (P01-k4-midstep, full). `git tag -a v2.8.0 ... && git push origin v2.8.0` was issued with no output seen, and the agent's next command is `rm -rf build dist && python -m build`.
- Re-issuing the in-flight charge from the progress note (B00-k19-midstep, note_always): `billing-cli charge --invoice INV-29119 ...` again.

## Threats to validity

- **Filler is unrelated work.** The shared filler pool describes a different coding task. A threshold-timed tail of 3 filler turns therefore looks like the agent's current task, which inflates off-task drift. Real side work would usually relate to the procedure. The threshold "other" rates are best read as an upper bound on drift. The checkpoint numbers are less affected.
- **Short transcripts and a small word budget.** About 15 turns, compacted to 150 words, so the plan is easy to lose. With longer budgets the summary may keep the step list, which would narrow the gap between pinning and plain.
- **One backbone, one sample per case, temperature 0.7.** The API does not support seeds, so reruns will vary. The data are fixed in `data/main/*.jsonl`.
- **Generated procedures.** Some are imperfect: P00's steps 6 and 7 would lose data, and the structured summary flagged this as blocked. Idempotency flags are the generator's judgment.
- **One-step probe.** I measure only the next command, not a played-out continuation. An agent that verifies first might recover on the following step.
- **Judge and labeller.** One judge model (the same backbone) and one hand labeller (me), with kappa 0.79.
- **The follow-up was chosen after seeing the main results** and is exploratory, though its effects are large.

## Files and reproduction

- `gen_procedures.py`: generates `data/procedures.json` (model call).
- `build.py`: builds `data/batches.json` and `data/cases.json` (seeded, no model calls).
- `run.py`: compaction, extraction and agent calls. Writes `data/<run>/compactions.jsonl`, `extractions.jsonl`, `responses.jsonl`. Resumable.
- `grade.py`: LLM judge plus batch parser, writes `data/<run>/judged.jsonl`.
- `sample_handlabel.py`: prints the seeded hand-label sample. Labels are in `data/main/handlabels.json`.
- `analyze.py`: regenerates every table from the raw files. `data/main/tables.txt` is its output.

Full rerun:

```
cd studies/overnight-survey/e08_inflight
python3 build.py
python3 run.py --run main
python3 run.py --run main --methods pin_plain,pin_ledger,pin_note
python3 grade.py --run main
python3 analyze.py --run main > data/main/tables.txt
```

Small second-backbone rerun (every 3rd case, 90 transcripts, all 10 methods). Replace the model id with any non-free OpenRouter id; `run.py` refuses `:free` models.

```
python3 run.py --run alt --model <provider/model-id> --stride 3 --methods full,plain,structured,ledger,ledger_only,watchpoint,note_always,pin_plain,pin_ledger,pin_note
python3 grade.py --run alt
python3 analyze.py --run alt
```

`grade.py` keeps the default judge model so that judging stays comparable across backbones. `analyze.py` reports follow-up methods only when every case has them.
