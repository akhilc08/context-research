import json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import lib
from lib import (
    build_filler_pool, run_multiround, agent_decide, agent_decide_goal,
    SUMMARY_INSTRUCTION, watchpoint_v2_constraint, watchpoint_v2_goal,
)
from scenarios import CONSTRAINT_SCENARIOS, GOAL_SCENARIOS

lib.MODELS["minimax"] = {"id": "minimax/minimax-01", "reasoning": None}

VALID_CONSTRAINT_IDS = {
    "merge_pr", "db_migration", "dependency_license", "force_push", "rate_limiter", "hardcoded_creds"
}
CONSTRAINT_SCENARIOS = [s for s in CONSTRAINT_SCENARIOS if s["id"] in VALID_CONSTRAINT_IDS]
VALID_GOAL_IDS = {"auth_feature", "perf_vs_refactor", "export_vs_databug", "docs_vs_migration", "tests_vs_security"}
GOAL_SCENARIOS = [s for s in GOAL_SCENARIOS if s["id"] in VALID_GOAL_IDS]

CONSTRAINT_KW = {
    "merge_pr": "approval",
    "db_migration": "rollback",
    "dependency_license": "license",
    "force_push": "force-push",
    "rate_limiter": "alert",
    "hardcoded_creds": "secrets manager",
}

POOL = build_filler_pool(96)
BACKBONES = ["qwen", "minimax"]
POSITIONS = ["early", "mid", "late"]
TAIL_K = 2
TURNS_PER_ROUND = 16
REPEATS = 3

def exp1_trial(sc, backbone, position, rounds, rep):
    summary, tail = run_multiround(backbone, POOL, sc["policy"], position, TAIL_K, rounds, TURNS_PER_ROUND)
    summary, patched = watchpoint_v2_constraint(backbone, summary, tail, sc["policy"], CONSTRAINT_KW[sc["id"]])
    decision, raw = agent_decide(backbone, summary, tail, sc["trigger"])
    return {
        "exp": "constraint", "scenario": sc["id"], "backbone": backbone, "position": position,
        "method": "watch2", "rounds": rounds, "rep": rep, "decision": decision, "patched": patched,
    }

def exp2_trial(sc, backbone, position, rep):
    transcript = [sc["g1"]] + POOL[:]
    summary, tail = run_multiround(backbone, transcript, sc["g2"], position, TAIL_K, 1, 20, instruction=SUMMARY_INSTRUCTION)
    summary, patched = watchpoint_v2_goal(backbone, summary, tail, sc["g2"], sc["g1_kw"], sc["g2_kw"])
    decision, raw = agent_decide_goal(backbone, summary, tail, sc["trigger"], sc["g1_kw"], sc["g2_kw"])
    return {
        "exp": "goal", "scenario": sc["id"], "backbone": backbone, "position": position,
        "method": "watch2", "rep": rep, "decision": decision, "patched": patched,
    }

def build_jobs():
    jobs = []
    for sc in CONSTRAINT_SCENARIOS:
        for backbone in BACKBONES:
            for position in POSITIONS:
                for rounds in [1, 3]:
                    for rep in range(REPEATS):
                        jobs.append((exp1_trial, (sc, backbone, position, rounds, rep)))
    backbone = "qwen"
    for sc in GOAL_SCENARIOS:
        for position in POSITIONS:
            for rep in range(4):
                jobs.append((exp2_trial, (sc, backbone, position, rep)))
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
    with open("results3.json", "w") as f:
        json.dump(results, f, indent=2)
    with open("errors3.json", "w") as f:
        json.dump(errors, f, indent=2)
    print(f"Done. {len(results)} results, {len(errors)} errors. Elapsed {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
