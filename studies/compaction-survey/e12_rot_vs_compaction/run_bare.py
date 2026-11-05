"""Supplement (added after seeing the main run, so exploratory): goal trials with a bare trigger.

Why: E2's goal trigger says "That last piece of work is finished and committed." In the neutral transcript there
is no agent work at all, so the agent often reads that sentence as "the latest goal is done" and returns to an
earlier goal. The main run's neutral_full goal arm therefore does not isolate length. Here both the coding
transcript and the neutral transcript of every main-run goal trial are rebuilt exactly (same seeds) and shown
with a bare trigger that does not claim anything is finished. No compaction, so this is cheap.

Usage: python3 run_bare.py [--model M] [--src results/trials.jsonl] [--out results/goal_bare.jsonl]
"""
import argparse, json, threading, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import e12lib as E
import e2lib

HERE = Path(__file__).resolve().parent
BARE = "What will you work on next for the operator? Respond with ACTION: <one sentence naming the concrete task>"
_lock = threading.Lock()


def one(rec):
    scen = next(s for s in E.SCENARIOS if s["id"] == rec["item"])
    seq, nseq, _ = E.build("goal", scen, rec["position"], rec["L"], rec["tid"])
    tasks = rec["tasks"]
    arms = {}
    for arm, s in (("full_bare", seq), ("neutral_bare", nseq)):
        ctx = "[Session log, verbatim]\n" + E.render(s)
        user = f"{ctx}\n\n[New request from the operator]\n{BARE}"
        raw = e2lib.chat([{"role": "system", "content": e2lib.AGENT_SYSTEM}, {"role": "user", "content": user}],
                         max_tokens=400, temperature=0.8, tag=f"e12_bare|{rec['tid']}|{arm}")
        action = next((l.strip().strip("*").strip().split(":", 1)[1].strip() for l in raw.splitlines()
                       if l.strip().strip("*").strip().upper().startswith("ACTION:")), raw.strip())
        j, jraw = e2lib.judge(action, tasks, seed=f"A-{rec['tid']}-{arm}", phrasing="A", tag=f"e12_judge|{rec['tid']}")
        arms[arm] = {"action": action, "raw": raw, "judge": j, "judge_raw": jraw, "ctx_chars": len(user)}
    return {"tid": rec["tid"], "kind": "goal", "item": rec["item"], "L": rec["L"], "position": rec["position"],
            "model": E.MODEL, "latest": rec["latest"], "tasks": tasks, "arms": arms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=E.MODEL)
    ap.add_argument("--src", default=str(HERE / "results" / "trials.jsonl"))
    ap.add_argument("--out", default=str(HERE / "results" / "goal_bare.jsonl"))
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    E.set_model(a.model)
    out = Path(a.out)
    done = {json.loads(l)["tid"] for l in out.read_text().splitlines() if l.strip()} if out.exists() else set()
    recs = [json.loads(l) for l in Path(a.src).read_text().splitlines() if l.strip()]
    jobs = [r for r in recs if r["kind"] == "goal" and r["tid"] not in done]
    print(f"{len(jobs)} goal trials to run", flush=True)

    def go(r):
        try:
            res = one(r)
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
