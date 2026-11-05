"""Re-run the deterministic grader on saved episodes (needs the sandboxes under /private/tmp/e25_sandboxes).

Rewrites results/<run>/outcomes.jsonl in place, keeping the run metadata fields and replacing the graded ones.
Usage: python3 regrade.py <run>
"""
import gzip, json, sys
from pathlib import Path

import grade as G
from sandbox import SANDBOX_BASE, Sandbox

HERE = Path(__file__).resolve().parent
META_KEYS = ("eid", "rid", "arm", "trial", "end", "calls", "nudges", "n_compactions", "max_ctx_tokens_est", "sec")


def main(run):
    d = HERE / "results" / run
    rows = [json.loads(l) for l in open(d / "outcomes.jsonl")]
    out = []
    for r in rows:
        ep = json.load(gzip.open(d / "episodes" / f"{r['eid']}.json.gz", "rt"))
        meta = json.loads((HERE / "data" / "repos" / r["rid"] / "meta.json").read_text())
        root = Path(SANDBOX_BASE) / r["eid"] / "repo"
        sb = Sandbox(root)
        o = G.grade(meta, root, ep["log"], ep["events"], sb.commits(), sb.changed_since_initial(),
                    HERE / "results" / "grading" / r["eid"])
        o.update({k: r[k] for k in META_KEYS if k in r})
        o.update({k: v for k, v in r.items() if k.startswith("tok_")})
        changed = [k for k in o if k in r and o[k] != r[k]]
        if changed:
            print(r["eid"], {k: (r[k], o[k]) for k in changed})
        out.append(o)
    (d / "outcomes.jsonl").write_text("".join(json.dumps(o) + "\n" for o in out))


if __name__ == "__main__":
    main(sys.argv[1])
