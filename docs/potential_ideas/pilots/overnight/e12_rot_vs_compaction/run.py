"""Main E12 run. One trial = (item type, item, session length L, item position). Each trial builds one coding
transcript and one matched low-salience transcript and evaluates every arm on them, so arms are paired.

Design per length L: all 42 rules, each at one position (rotating with L so every rule visits every position
across lengths), and all 27 E2 goal scenarios at two of the three positions (also rotating): 42 rule trials and
54 goal trials per L.

Usage:
  python3 run.py                                     # default model, L = 20,50,100,200,400,800
  python3 run.py --lengths 1600                      # add a length
  python3 run.py --model provider/model --lengths 20,100,400 --max-items 14 --out results/trials_<name>.jsonl
Appends one JSON line per trial to --out and skips trials already present (resumable).
"""
import argparse, json, threading, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import e12lib as E

HERE = Path(__file__).resolve().parent
_lock = threading.Lock()
ALL_L = (20, 50, 100, 200, 400, 800, 1600)


def jobs_for(L, max_items=0, kinds=("rule", "goal")):
    li = ALL_L.index(L) if L in ALL_L else L
    out = []
    if "rule" in kinds:
        rules = E.RULES[:max_items] if max_items else E.RULES
        for i, r in enumerate(rules):
            out.append(("rule", r, L, E.POSITIONS[(i + li) % 3]))
    if "goal" in kinds:
        scen = E.SCENARIOS[:max_items] if max_items else E.SCENARIOS
        for i, s in enumerate(scen):
            skip = (i + li) % 3
            for k, p in enumerate(E.POSITIONS):
                if k != skip:
                    out.append(("goal", s, L, p))
    return out


def tid_of(kind, item, L, position):
    return f"{kind}-{item['id']}-L{L}-{position}"


def trial(kind, item, L, position):
    tid = tid_of(kind, item, L, position)
    seq, nseq, ipos = E.build(kind, item, position, L, tid)
    summary, tail, hist = E.run_recursive(seq, tag=f"e12_compact|{tid}")
    ctxs = E.contexts(kind, item, seq, nseq, summary, tail)
    arms = {}
    if kind == "rule":
        for arm, ctx in ctxs.items():
            dec, raw = E.rule_decide(ctx, item["trigger"], tag=f"e12_decide|{tid}|{arm}")
            a = {"decision": dec, "raw": raw, "ctx_chars": len(ctx)}
            if dec == "COMPLY":
                a["breaks"], a["breaks_raw"] = E.rule_action_breaks(item, raw, tag=f"e12_action|{tid}")
            arms[arm] = a
        extra = {"rule": item["rule"], "trigger": item["trigger"]}
    else:
        tasks = [g["task"] for g in item["goals"]]
        for arm, ctx in ctxs.items():
            arms[arm] = E.goal_act(ctx, tasks, tid, arm)
        extra = {"tasks": tasks, "latest": len(tasks) - 1}
    return {"tid": tid, "kind": kind, "item": item["id"], "L": L, "position": position, "model": E.MODEL,
            "item_turns": ipos, "rounds": len(hist), "summaries": hist, "tail": tail,
            "neutral_chars": sum(len(t) for t in nseq), "coding_chars": sum(len(t) for t in seq),
            "arms": arms, **extra}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=E.MODEL)
    ap.add_argument("--lengths", default="20,50,100,200,400,800")
    ap.add_argument("--kinds", default="rule,goal")
    ap.add_argument("--max-items", type=int, default=0)
    ap.add_argument("--out", default=str(HERE / "results" / "trials.jsonl"))
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    E.set_model(a.model)
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {json.loads(l)["tid"] for l in out.read_text().splitlines() if l.strip()}
    jobs = [j for L in map(int, a.lengths.split(",")) for j in jobs_for(L, a.max_items, a.kinds.split(","))
            if tid_of(*j) not in done]
    # Long trials first so the slow sequential compaction chains start early.
    jobs.sort(key=lambda j: -j[2])
    print(f"{len(jobs)} trials to run with {a.model}", flush=True)

    def go(j):
        try:
            res = trial(*j)
        except Exception:
            traceback.print_exc()
            return
        with _lock, open(out, "a") as f:
            f.write(json.dumps(res) + "\n")
        print("done", res["tid"], flush=True)

    with ThreadPoolExecutor(min(a.workers, 10)) as ex:
        list(ex.map(go, jobs))


if __name__ == "__main__":
    main()
