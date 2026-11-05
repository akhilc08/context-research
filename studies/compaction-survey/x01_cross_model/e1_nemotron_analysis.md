## Source: e1_nemotron.jsonl

Transcripts per N: N=10: 6

### Violation rate (COMPLY on trigger)

| N | floor | full | plain | pin_all | wp_batched | wp_self | oracle_patch | random_patch | pin_loo |
|---|---|---|---|---|---|---|---|---|---|
| 10 |  | 17% (3/18) [6 to 39] | 72% (13/18) [49 to 88] | 11% (2/18) [3 to 33] | 11% (2/18) [3 to 33] | 0% (0/18) [0 to 18] |  |  | 39% (7/18) [20 to 61] |

Cochran-Armitage trend p (score log2 N): 

Unparsed decisions (counted as non-violations): 44

### Pairwise comparisons (primary metric): Fisher two-sided p, and exact McNemar on paired trials

Confirmatory family: 5 comparisons x each N, McNemar p Holm-adjusted across the whole family. Other rows are exploratory (unadjusted).

| N | comparison | A | B | Fisher p | discordant (A only / B only) | McNemar p | Holm p | family |
|---|---|---|---|---|---|---|---|---|
| 10 | plain vs pin_all | 13/18 | 2/18 | 0.000491 | 12 / 1 | 0.00342 | 0.0103 | confirmatory |
| 10 | plain vs wp_batched | 13/18 | 2/18 | 0.000491 | 11 / 0 | 0.000977 | 0.00391 | confirmatory |
| 10 | plain vs wp_self | 13/18 | 0/18 | 7.42e-06 | 13 / 0 | 0.000244 | 0.00122 | confirmatory |
| 10 | pin_all vs wp_batched | 2/18 | 2/18 | 1 | 1 / 1 | 1 | 1 | confirmatory |
| 10 | pin_all vs wp_self | 2/18 | 0/18 | 0.486 | 2 / 0 | 0.5 | 1 | confirmatory |
| 10 | wp_batched vs wp_self | 2/18 | 0/18 | 0.486 | 2 / 0 | 0.5 |  | exploratory |
| 10 | pin_all vs pin_loo | 2/18 | 7/18 | 0.121 | 1 / 6 | 0.125 |  | exploratory |
| 10 | full vs pin_all | 3/18 | 2/18 | 1 | 2 / 1 | 1 |  | exploratory |

### Judge validation against hand labels (stratified samples)

| judge | n | agreement | Cohen's kappa |
|---|---|---|---|
| survival judge (ground truth) | 44 | 95% | 0.91 |
| wp_batched comparator 'covered' | 44 | 93% | 0.86 |
| wp_self self-judgment 'covered' | 44 | 45% | 0.00 |
| action judge (secondary metric) | 42 | 98% | 0.95 |

### Rule survival in the summary (independent judge) and detector quality

Truth: a rule is 'missing' when the judge says the compacted context does not state it.

| N | rules | survived (judge) | survived (judge + quote found) | detector | flagged missing (patch rate) | recall of misses | precision of flags |
|---|---|---|---|---|---|---|---|
| 10 | 60 | 0% (0/60) [-0 to 6] | 0% (0/60) [-0 to 6] | wp_batched | 100% (60/60) [94 to 100] | 100% (60/60) [94 to 100] | 100% (60/60) [94 to 100] |
| 10 | 60 | 0% (0/60) [-0 to 6] | 0% (0/60) [-0 to 6] | wp_self | 100% (60/60) [94 to 100] | 100% (60/60) [94 to 100] | 100% (60/60) [94 to 100] |

### Plain-method violation by judged survival of the tested rule

| N | rule survived | rule missing |
|---|---|---|
| 10 | n/a | 72% (13/18) [49 to 88] |

### Cost per transcript (means)

| N | summary words | method | extra model calls | added context tokens (est.) | detector input tokens (est.) |
|---|---|---|---|---|---|
| 10 | 86 | plain | 0 | 0 | 0 |
| 10 | 86 | pin_all | 0 | 355 | 0 |
| 10 | 86 | wp_batched | 11 | 355 | 1385 |
| 10 | 86 | wp_self | 10 | 355 | 3623 |

