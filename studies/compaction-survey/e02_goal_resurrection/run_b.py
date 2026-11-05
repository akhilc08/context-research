"""Follow-up E2b (decided after seeing the main results, so exploratory): stale-work pressure.

Same methods, judge, and analysis as run.py, but after each superseded goal the transcript contains up to 12
turns of the agent actually working on that goal (data/goal_work.json), instead of only unrelated filler.
After the final redirect, turns are unrelated filler as in the main run. Positions: mid and late only
(an early final redirect leaves no room for stale work).

Usage: python3 run_b.py [--model M] [--reps 2] [--out results/trials_b.jsonl]
"""
import json, sys
from pathlib import Path

import e2lib as L
import run

HERE = Path(__file__).resolve().parent
WORK = json.loads((HERE / "data" / "goal_work.json").read_text())


def build_sequence_b(scen, position, rng):
    goals = scen["goals"]
    Ln = L.N_FILLER + len(goals)
    pos = L.goal_positions(len(goals), position, Ln)
    filler = iter(L.sample_filler(L.N_FILLER, rng))
    seq, is_goal = [], []
    gi, work = 0, iter(())
    for i in range(Ln):
        if gi < len(pos) and i == pos[gi]:
            seq.append(L.goal_turn_text(goals[gi], gi)); is_goal.append(True)
            work = iter(WORK[scen["id"]][gi]) if gi < len(goals) - 1 else iter(())
            gi += 1
            continue
        t = next(work, None)
        seq.append("[Agent] " + (t if t is not None else next(filler))); is_goal.append(False)
    bounds = [round(Ln * r / L.ROUNDS) for r in range(L.ROUNDS + 1)]
    chunks = [list(range(bounds[r], bounds[r + 1])) for r in range(L.ROUNDS)]
    return seq, is_goal, chunks, pos


_orig_trial = run.trial


def trial_b(scen, position, rep):
    r = _orig_trial(scen, position, f"b{rep}")
    r["variant"] = "stale_work"
    return r


run.build_sequence = build_sequence_b
run.trial = trial_b

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--out" not in args:
        args += ["--out", str(HERE / "results" / "trials_b.jsonl")]
    if "--positions" not in args:
        args += ["--positions", "mid,late"]
    if "--reps" not in args:
        args += ["--reps", "2"]
    sys.argv = [sys.argv[0]] + args
    run.main()
