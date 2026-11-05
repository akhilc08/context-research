# Watchpoint Compaction

Archived. The first research thread in this repository, from September 2026.

It studied two ways compaction silently loses context: a rule stated early in a session stops being followed, and a superseded goal comes back after the summary drops the redirect. It ended in a paper draft proposing **Watchpoint Compaction**. That method tracks load-bearing statements, lets compaction run normally, then checks whether the model still holds each statement and patches back any that were lost. A naive self-judgment check failed. An extraction-based check worked and tied the best failure-specific fix on both failure modes.

The draft has not been reviewed or submitted. Its own Limitations section is the accurate account of what is unsettled.

## Layout

| Path | Contents |
|---|---|
| [`paper/`](paper/) | The draft's LaTeX source, compiled PDF, and figures |
| [`docs/paper-plan.md`](docs/paper-plan.md) | Experiment designs for seven candidate ideas, the benchmark dry runs, and how the paper came out of ideas A and F |
| [`docs/ideas/`](docs/ideas/) | The seven candidate ideas, each a narrow loss mechanism paired with a cheap fix |
| [`docs/lightweight-verify-repair-brief.md`](docs/lightweight-verify-repair-brief.md) | Offshoot brief on detecting and patching what a compaction dropped |
| [`recency-study/`](recency-study/) | Code and raw results for the three runs behind the paper, plus the figure scripts |
| [`position-dependent-retention/`](position-dependent-retention/) | The first single-backbone pilot for idea A |
| [`benchmark-dryrun/`](benchmark-dryrun/) | τ-bench gold-action replay used to check the benchmark harness |

The repository-wide research brief and source ledger that motivated this thread are in [`../../docs/`](../../docs/). The later [compaction survey](../compaction-survey/) followed up on several of these ideas.
