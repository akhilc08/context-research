# X1: second-backbone replication of E1 and E2

Run on 2026-10-02, 03:00 to 04:30 EDT, by the overnight coordinator. Every other overnight study used one model (`stealth/space-bunny-alpha`) for every role. This directory reruns the headline comparisons of E1 (rule-count scaling) and E2 (goal resurrection) on a different model family to check that the main results are not specific to that model.

## Model choice

The free-model quota allows 1,000 requests a day, so these runs are small.

- `qwen/qwen3.8-27b:free` was the first choice. During the run it was rate-limited upstream and returned empty completions, so it could not be used.
- `nvidia/nemotron-3-ultra-550b-a55b:free` (550B parameters, a different family from Space Bunny) answered a realistic summarization probe correctly and was used instead.
- `shim.py` runs each study's own `run.py` unchanged except for three things: it lifts the studies' refusal of `:free` model ids, disables the reasoning parameter, and (for the E2 rerun) raises every output cap to at least 1,500 tokens. The cap change is needed because Nemotron writes its reasoning into the visible reply and short caps cut it off before the answer line. Prompts are unchanged. Every role (summarizer, agent, detector, judge) runs on Nemotron, as every role ran on Space Bunny in the original studies.

## E1 replication (N = 10 rules, 6 transcripts, 18 trigger tests per arm)

Command: `python3 shim.py e1 --budget fixed --ns 10 --scale 0.375 --out $PWD/e1_nemotron.jsonl`. Full analysis in `e1_nemotron_analysis.md`.

This run used the original 200-token decision cap, before the cap fix. 46 of 108 decisions were cut off before the `DECISION:` line. The study's analysis counts those as non-violations, which flatters every arm. The fairer view excludes them (`e1_nemotron_parsed_only.txt`):

| arm | violations among parsed decisions | truncated |
|---|---|---|
| plain | 12/13 | 5 |
| pin_all | 2/13 | 5 |
| wp_batched | 2/10 | 8 |
| wp_self | 0/10 | 8 |
| full context | 3/9 | 9 |
| pin_loo (all rules but the tested one) | 7/7 | 11 |

With truncated decisions counted as non-violations, plain versus pin_all is 13/18 vs 2/18 (McNemar Holm p = 0.01) and plain versus wp_batched is 13/18 vs 2/18 (Holm p = 0.004). pin_all and wp_batched tie (1 vs 1 discordant pairs).

What replicates: plain compaction loses most rules, and both pinning and the batched watchpoint restore them, tying each other. What does not: the naive self-check (`wp_self`), which failed completely on Space Bunny (kappa 0.00, violations equal to plain), looks effective on Nemotron (0/10 parsed). The sample is small and 8 of its 18 decisions are truncated, so this is a lead, not a result. It suggests the self-check failure may be model-specific.

## E2 replication (8 scenarios, early redirect position, 1 repeat)

Command: `python3 shim.py e2 --reps 1 --max-scenarios 8 --positions early --out $PWD/e2_nemotron.jsonl`. Full analysis in `e2_nemotron_analysis.txt`. A first attempt without the output-cap fix was stopped after 4 trials because half of the plain-arm replies never reached the `ACTION:` line. It is kept as `e2_nemotron_truncated_discarded.*` and excluded. In the clean rerun all 64 replies contain an `ACTION:` line.

| arm | follows current goal |
|---|---|
| full context | 7/8 |
| plain | 6/8 |
| anchor prompt | 7/8 |
| pin | 8/8 |
| pin_clean | 8/8 |
| watchpoint | 8/8 |
| selfcheck | 8/8 |
| floor (no goals) | 0/8 |

Direction replicates: pin, watchpoint, and the self-check all reach 8/8 and plain trails at 6/8. No comparison is significant at n = 8 (pin versus plain: 2 vs 0 discordant, p = 0.5). Two Space Bunny findings do not show here: full context (7/8) is not below plain, and the anchor prompt (7/8) is not below plain. Neither difference can be resolved at this size.

## Limitations

- Very small samples: these runs can confirm direction, not effect sizes.
- The E1 run has heavy decision truncation, as described above.
- Scenarios and rules were validated (floor and ceiling checks) on Space Bunny, not on Nemotron.
- Quota used: about 950 of the 1,000 daily free-model requests, including probes and the discarded attempt.
