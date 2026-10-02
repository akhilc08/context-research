"""Extra arms added after the main run, at the coordinator's request for a floor control and
ablations. They reuse each transcript's saved summary and tail, so they stay paired with the
main arms. Arms:
  floor         no summary and no rules: only the verbatim tail (no rule is ever in the tail)
  oracle_patch  patch exactly the rules the independent judge says are missing (detector upper bound)
  random_patch  patch a random subset the same size as wp_batched's patch (does selection matter?)
Writes supplement_<results stem>.jsonl, one line per decision; resumable.

Usage: python supplement.py results_fixed.jsonl [--model ID] [--seed 7]
"""
import argparse, json, random, threading
from concurrent.futures import ThreadPoolExecutor

import run  # patches common.chat with the concurrency cap and model override
from run import HERE, common, rule_block


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--model", default=run.orclient.MODEL)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    run.set_model(a.model)
    src = HERE / a.results
    out = HERE / f"supplement_{src.stem}.jsonl"
    done = set()
    if out.exists():
        for l in out.read_text().splitlines():
            d = json.loads(l)
            done.add((d["n"], d["idx"], d["rule"], d["method"]))
    rules = {r["id"]: r for r in common.load_rules()}
    jobs = []
    for line in src.read_text().splitlines():
        rec = json.loads(line)
        n, idx = rec["n"], rec["idx"]
        rng = random.Random(a.seed * 7919 + n * 101 + idx)
        picked = [rules[i] for i in rec["rules"]]
        missing = [r for r in picked if not rec["truth"][r["id"]]["stated"]]
        k = len(rec["wp_batched"]["patched"])
        rand = rng.sample(picked, k)
        ctxs = {
            "floor": common.context_block("", rec["tail"]),
            "oracle_patch": common.context_block(rec["summary"], rec["tail"], rule_block(missing)),
            "random_patch": common.context_block(rec["summary"], rec["tail"], rule_block(rand)),
        }
        for rid in rec["tested"]:
            for m, c in ctxs.items():
                if (n, idx, rid, m) not in done:
                    jobs.append((n, idx, rid, m, c, len(rule_block(missing if m == "oracle_patch" else rand if m == "random_patch" else [])) / 4))
    print(f"{len(jobs)} supplementary decisions", flush=True)
    lock = threading.Lock()

    def one(j):
        n, idx, rid, m, c, added = j
        dec, raw = common.decide(c, rules[rid]["trigger"], tag="e1_supp")
        with lock, open(out, "a") as f:
            f.write(json.dumps({"n": n, "idx": idx, "rule": rid, "method": m, "decision": dec,
                                "raw": raw, "added_tokens": added, "model": run.MODEL["id"]}) + "\n")

    with ThreadPoolExecutor(12) as ex:
        list(ex.map(one, jobs))


if __name__ == "__main__":
    main()
