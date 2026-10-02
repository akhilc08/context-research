"""Main E2 run. One trial = (scenario, redirect position, repeat). Each trial builds one transcript and
evaluates every method on it, so arms are paired.

Usage:
  python3 run.py                                   # default model, 3 repeats, all valid scenarios
  python3 run.py --model some/model --reps 1 --out results/trials_some-model.jsonl

Appends one JSON line per trial to --out and skips trials already present (resumable).
"""
import argparse, json, random, threading, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import e2lib as L
from e2lib import (build_sequence, chunks_text, run_recursive, context_block, render, agent_action,
                   extract_objective, compare, selfcheck, judge, goal_turn_text, SUMMARY_PROMPT, ANCHOR_PROMPT,
                   POSITIONS, TAIL_K, WORDS)

HERE = Path(__file__).resolve().parent
_lock = threading.Lock()


def slot(label, text):
    return f"[{label}]\nCurrent objective: {text}"


def trial(scen, position, rep):
    tid = f"{scen['id']}-{position}-{rep}"
    rng = random.Random(f"e2-{tid}")
    seq, is_goal, chunks, gpos = build_sequence(scen, position, rng)
    tasks = [g["task"] for g in scen["goals"]]
    latest = len(tasks) - 1
    tracked = goal_turn_text(scen["goals"][-1], latest).replace("[Operator message] ", "")

    sp, tp, hp = run_recursive(chunks_text(seq, chunks), TAIL_K, WORDS, SUMMARY_PROMPT, tag=f"e2_compact_plain|{tid}")
    sa, ta, ha = run_recursive(chunks_text(seq, chunks), TAIL_K, WORDS, ANCHOR_PROMPT, tag=f"e2_compact_anchor|{tid}")
    keep = [not g for g in is_goal]
    sc, tc, hc = run_recursive(chunks_text(seq, chunks, keep), TAIL_K, WORDS, SUMMARY_PROMPT, tag=f"e2_compact_clean|{tid}")

    plain_ctx = context_block(sp, tp)
    contexts = {
        "full": "[Session log, verbatim]\n" + render(seq),
        "plain": plain_ctx,
        "anchor": context_block(sa, ta),
        "pin": context_block(sp, tp, slot("Harness-maintained objective slot", tracked)),
        "pin_clean": context_block(sc, tc, slot("Harness-maintained objective slot", tracked)),
        "floor": context_block(sc, tc),
    }

    # Watchpoint v4: extraction on the plain context, comparator sees only the sentence and the tracked goal.
    extracted = extract_objective(plain_ctx, tag=f"e2_wp_extract|{tid}")
    match, cmp_raw = compare(tracked, extracted, tag=f"e2_wp_compare|{tid}")
    wp_patch = not match
    # Ablation: naive self-judgment check over the whole context (old v1 detector).
    sc_ok, sc_raw = selfcheck(plain_ctx, tracked, tag=f"e2_selfcheck|{tid}")
    sc_patch = not sc_ok
    patched_ctx = context_block(sp, tp, slot("Watchpoint reminder", tracked))
    if wp_patch:
        contexts["watchpoint"] = patched_ctx
    if sc_patch and not wp_patch:
        contexts["selfcheck"] = patched_ctx

    arms = {}
    for m, ctx in contexts.items():
        action, raw, nchar = agent_action(ctx, tag=f"e2_agent_{m}|{tid}")
        arms[m] = {"action": action, "raw": raw, "ctx_chars": nchar}
    # Unpatched watchpoint/selfcheck contexts are identical to plain, so they reuse plain's sampled action.
    for m, patched in (("watchpoint", wp_patch), ("selfcheck", sc_patch)):
        if patched:
            if m == "selfcheck" and wp_patch:  # same context as the patched watchpoint: reuse that draw
                arms[m] = dict(arms["watchpoint"], shared_with="watchpoint")
        else:
            arms[m] = dict(arms["plain"], shared_with="plain")
    for m, a in arms.items():
        ja, ra = judge(a["action"], tasks, seed=f"A-{tid}-{m}", phrasing="A", tag=f"e2_judge|{tid}")
        jb, rb = judge(a["action"], tasks, seed=f"B-{tid}-{m}", phrasing="B", tag=f"e2_judgeB|{tid}")
        a.update(judge_A=ja, judge_A_raw=ra, judge_B=jb, judge_B_raw=rb)
    je, _ = judge(extracted, tasks, seed=f"A-{tid}-extract", phrasing="A", tag=f"e2_judge|{tid}")

    return {
        "tid": tid, "scenario": scen["id"], "position": position, "rep": rep, "model": L.MODEL,
        "n_goals": len(tasks), "latest": latest, "goal_positions": gpos, "tasks": tasks, "tracked": tracked,
        "summaries": {"plain": hp, "anchor": ha, "clean": hc}, "tails": {"plain": tp, "anchor": ta, "clean": tc},
        "watchpoint": {"extracted": extracted, "extracted_judged": je, "compare_raw": cmp_raw, "patched": wp_patch},
        "selfcheck": {"raw": sc_raw, "patched": sc_patch},
        "arms": arms,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.MODEL)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--rep-start", type=int, default=0)
    ap.add_argument("--max-scenarios", type=int, default=0)
    ap.add_argument("--positions", default=",".join(POSITIONS))
    ap.add_argument("--out", default=str(HERE / "results" / "trials.jsonl"))
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    L.set_model(a.model)
    scen = json.loads((HERE / "data" / "scenarios.json").read_text())
    if a.max_scenarios:
        scen = scen[:a.max_scenarios]
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {json.loads(l)["tid"] for l in out.read_text().splitlines() if l.strip()}
    jobs = [(s, p, r) for r in range(a.rep_start, a.rep_start + a.reps) for p in a.positions.split(",") for s in scen
            if f"{s['id']}-{p}-{r}" not in done]
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

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(go, jobs))


if __name__ == "__main__":
    main()
