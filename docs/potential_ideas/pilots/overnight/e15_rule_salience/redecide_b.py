"""Re-run Part B decisions for chains made before the decision max_tokens fix (200 -> 800).

The first 38 chains ran decisions with max_tokens=200. This keeps their summaries and judge
labels, re-runs every decision on the identical contexts at 800 tokens, and rewrites
b_transcripts.jsonl. The replaced decisions are kept in b_decisions_mt200.jsonl.
Repeat counts follow run_b.REPS (1 at R = 4 and 8, 2 at R = 16).
Usage: python3 redecide_b.py [--model ID] [--threads 8]
"""
import argparse, json
from concurrent.futures import ThreadPoolExecutor

import e15lib as L
import run_b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    data = L.set_model(a.model, a.threads)
    path = data / "b_transcripts.jsonl"
    T = L.read_jsonl(path)
    old = [t for t in T if "decide_max_tokens" not in t]
    print(len(old), "chains to redo", flush=True)
    with open(data / "b_decisions_mt200.jsonl", "a") as f:
        for t in old:
            for r in t["rounds"]:
                if "decisions" in r:
                    f.write(json.dumps({"n": t["n"], "idx": t["idx"], "regime": t["regime"], "R": r["R"],
                                        "decisions": r["decisions"]}) + "\n")
    jobs = []
    for t in old:
        picked, facts, chunks, tested = run_b.build(t["n"], t["idx"], t["seed"])
        for r in t["rounds"]:
            if r["R"] not in run_b.MEASURE_R:
                continue
            tail = chunks[r["R"]][:3]
            ctxs = {t["regime"]: L.context_block_e6(r["summary"], tail)}
            if t["regime"] == "plain":
                pin = run_b.PIN_HEADER + "\n" + "\n".join(f"- {x['rule']}" for x in picked)
                ctxs["pin_all"] = L.context_block_e6(r["summary"], tail, pin)
            r["decisions"] = []
            for arm, c in ctxs.items():
                for x in tested:
                    for k in range(run_b.REPS[r["R"]]):
                        jobs.append((r, arm, x, k, c))

    def go(j):
        r, arm, x, k, c = j
        d, raw = L.decide(c, x["trigger"], 0.8, "e15b_redecide")
        return r, {"arm": arm, "rule": x["id"], "rep": k, "decision": d, "raw": raw}

    with ThreadPoolExecutor(a.threads) as ex:
        for r, d in ex.map(go, jobs):
            r["decisions"].append(d)
    for t in old:
        t["decide_max_tokens"] = L.DECIDE_MAX_TOKENS
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(t) + "\n" for t in T))
    tmp.replace(path)
    print("redone", len(jobs), "decisions", flush=True)


if __name__ == "__main__":
    main()
