import json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import lib
from lib import (
    build_filler_pool, run_multiround, agent_decide, agent_decide_goal,
    SUMMARY_INSTRUCTION, ANCHOR_INSTRUCTION, watchpoint_patch, pin_fact,
    CONSTRAINT_AUDIT_TEMPLATE, GOAL_AUDIT_TEMPLATE,
)
from scenarios import CONSTRAINT_SCENARIOS, GOAL_SCENARIOS

lib.MODELS["minimax"] = {"id": "minimax/minimax-01", "reasoning": None}

VALID_CONSTRAINT_IDS = {
    "merge_pr", "db_migration", "dependency_license", "force_push", "rate_limiter", "hardcoded_creds"
}
CONSTRAINT_SCENARIOS = [s for s in CONSTRAINT_SCENARIOS if s["id"] in VALID_CONSTRAINT_IDS]
VALID_GOAL_IDS = {"auth_feature", "perf_vs_refactor", "export_vs_databug", "docs_vs_migration", "tests_vs_security"}
GOAL_SCENARIOS = [s for s in GOAL_SCENARIOS if s["id"] in VALID_GOAL_IDS]

POOL = build_filler_pool(96)
BACKBONES = ["qwen", "minimax"]
POSITIONS = ["early", "mid", "late"]
TAIL_K = 2  # every method here uses the same short plain tail; the fix is what's appended, not the window
TURNS_PER_ROUND = 16
REPEATS = 3

def exp1_trial(sc, backbone, position, method, rounds, rep):
    tail_k = 8 if method == "grace" else TAIL_K
    summary, tail = run_multiround(backbone, POOL, sc["policy"], position, tail_k, rounds, TURNS_PER_ROUND)
    patched = False
    if method == "pin":
        summary = pin_fact(summary, sc["policy"], "Active rule")
    elif method == "watch":
        summary, patched = watchpoint_patch(backbone, summary, tail, sc["policy"], CONSTRAINT_AUDIT_TEMPLATE, "Active rule")
    decision, raw = agent_decide(backbone, summary, tail, sc["trigger"])
    return {
        "exp": "constraint", "scenario": sc["id"], "backbone": backbone, "position": position,
        "method": method, "rounds": rounds, "rep": rep, "decision": decision, "patched": patched,
    }

GOAL_METHODS_PROMPT = {"plain": SUMMARY_INSTRUCTION, "anchor": ANCHOR_INSTRUCTION, "watch": SUMMARY_INSTRUCTION}

def exp2_trial(sc, backbone, position, method, rep):
    instruction = GOAL_METHODS_PROMPT[method]
    transcript = [sc["g1"]] + POOL[:]
    summary, tail = run_multiround(backbone, transcript, sc["g2"], position, TAIL_K, 1, 20, instruction=instruction)
    patched = False
    if method == "watch":
        summary, patched = watchpoint_patch(backbone, summary, tail, sc["g2"], GOAL_AUDIT_TEMPLATE, "Current objective")
    decision, raw = agent_decide_goal(backbone, summary, tail, sc["trigger"], sc["g1_kw"], sc["g2_kw"])
    return {
        "exp": "goal", "scenario": sc["id"], "backbone": backbone, "position": position,
        "method": method, "rep": rep, "decision": decision, "patched": patched,
    }

def build_jobs():
    jobs = []
    round1_methods = ["plain", "grace", "pin", "watch"]
    round3_methods = ["plain", "watch"]
    for sc in CONSTRAINT_SCENARIOS:
        for backbone in BACKBONES:
            for position in POSITIONS:
                for method in round1_methods:
                    for rep in range(REPEATS):
                        jobs.append((exp1_trial, (sc, backbone, position, method, 1, rep)))
                for method in round3_methods:
                    for rep in range(REPEATS):
                        jobs.append((exp1_trial, (sc, backbone, position, method, 3, rep)))
    backbone = "qwen"
    for sc in GOAL_SCENARIOS:
        for position in POSITIONS:
            for method in ["plain", "anchor", "watch"]:
                for rep in range(4):
                    jobs.append((exp2_trial, (sc, backbone, position, method, rep)))
    return jobs

def main():
    jobs = build_jobs()
    print(f"Total jobs: {len(jobs)}")
    results, errors = [], []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=14) as ex:
        futs = {ex.submit(fn, *args): None for fn, args in jobs}
        done = 0
        for fut in as_completed(futs):
            done += 1
            try:
                results.append(fut.result())
            except Exception as e:
                errors.append(str(e))
            if done % 25 == 0 or done == len(jobs):
                print(f"[{done}/{len(jobs)}] elapsed={time.time()-t0:.0f}s errors={len(errors)}")
    with open("results2.json", "w") as f:
        json.dump(results, f, indent=2)
    with open("errors2.json", "w") as f:
        json.dump(errors, f, indent=2)
    print(f"Done. {len(results)} results, {len(errors)} errors. Elapsed {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
