import json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import lib
from lib import (
    build_filler_pool, run_multiround, agent_decide, agent_decide_goal,
    SUMMARY_INSTRUCTION, ANCHOR_INSTRUCTION, compact_once,
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
METHODS = {"plain": 2, "grace": 8}
ROUNDS = [1, 3]
TURNS_PER_ROUND = 16
REPEATS_EXP1 = 4

def exp1_trial(sc, backbone, position, method, rounds, rep):
    tail_k = METHODS[method]
    summary, tail = run_multiround(backbone, POOL, sc["policy"], position, tail_k, rounds, TURNS_PER_ROUND)
    decision, raw = agent_decide(backbone, summary, tail, sc["trigger"])
    return {
        "exp": "constraint", "scenario": sc["id"], "backbone": backbone, "position": position,
        "method": method, "rounds": rounds, "rep": rep, "decision": decision,
        "summary": summary, "tail_len": len(tail), "raw": raw,
    }

def exp1_control_full_context(sc, backbone, rep):
    tail = [sc["policy"]] + POOL[:4]
    decision, raw = agent_decide(backbone, "", tail, sc["trigger"])
    return {
        "exp": "constraint", "scenario": sc["id"], "backbone": backbone, "position": "full_context_control",
        "method": "none", "rounds": 0, "rep": rep, "decision": decision, "summary": "", "tail_len": len(tail), "raw": raw,
    }

def exp1_control_no_policy(sc, backbone, rep):
    summary, tail = compact_once(backbone, "", POOL[:16], 2)
    decision, raw = agent_decide(backbone, summary, tail, sc["trigger"])
    return {
        "exp": "constraint", "scenario": sc["id"], "backbone": backbone, "position": "no_policy_control",
        "method": "plain", "rounds": 1, "rep": rep, "decision": decision, "summary": summary,
        "tail_len": len(tail), "raw": raw,
    }

REPEATS_EXP2 = 4
GOAL_METHODS = {
    "plain": ("plain", 2, SUMMARY_INSTRUCTION),
    "grace": ("grace", 8, SUMMARY_INSTRUCTION),
    "anchor": ("anchor", 2, ANCHOR_INSTRUCTION),
}

def exp2_trial(sc, backbone, position, method_name, rep):
    _, tail_k, instruction = GOAL_METHODS[method_name]
    g2_line = sc["g2"]
    transcript = [sc["g1"]] + POOL[:]
    summary, tail = run_multiround(backbone, transcript, g2_line, position, tail_k, 1, 20, instruction=instruction)
    decision, raw = agent_decide_goal(backbone, summary, tail, sc["trigger"], sc["g1_kw"], sc["g2_kw"])
    return {
        "exp": "goal", "scenario": sc["id"], "backbone": backbone, "position": position,
        "method": method_name, "rep": rep, "decision": decision, "summary": summary,
        "tail_len": len(tail), "raw": raw,
    }

def exp2_control_orig(sc, backbone, rep):
    decision, raw = agent_decide_goal(backbone, "", [sc["g1"]] + POOL[:4], sc["trigger"], sc["g1_kw"], sc["g2_kw"])
    return {
        "exp": "goal", "scenario": sc["id"], "backbone": backbone, "position": "no_redirect_control",
        "method": "none", "rep": rep, "decision": decision, "summary": "", "tail_len": 5, "raw": raw,
    }

def exp2_control_full(sc, backbone, rep):
    decision, raw = agent_decide_goal(backbone, "", [sc["g1"], sc["g2"]] + POOL[:4], sc["trigger"], sc["g1_kw"], sc["g2_kw"])
    return {
        "exp": "goal", "scenario": sc["id"], "backbone": backbone, "position": "full_context_control",
        "method": "none", "rep": rep, "decision": decision, "summary": "", "tail_len": 6, "raw": raw,
    }

def build_jobs():
    jobs = []
    for sc in CONSTRAINT_SCENARIOS:
        for backbone in BACKBONES:
            for position in POSITIONS:
                for method in METHODS:
                    for rounds in ROUNDS:
                        for rep in range(REPEATS_EXP1):
                            jobs.append(("exp1", exp1_trial, (sc, backbone, position, method, rounds, rep)))
            for rep in range(4):
                jobs.append(("exp1_ctrl", exp1_control_full_context, (sc, backbone, rep)))
            for rep in range(2):
                jobs.append(("exp1_ctrl", exp1_control_no_policy, (sc, backbone, rep)))

    backbone = "qwen"
    for sc in GOAL_SCENARIOS:
        for position in POSITIONS:
            for method in GOAL_METHODS:
                for rep in range(REPEATS_EXP2):
                    jobs.append(("exp2", exp2_trial, (sc, backbone, position, method, rep)))
        for rep in range(4):
            jobs.append(("exp2_ctrl", exp2_control_orig, (sc, backbone, rep)))
            jobs.append(("exp2_ctrl", exp2_control_full, (sc, backbone, rep)))
    return jobs

def main():
    jobs = build_jobs()
    print(f"Total jobs: {len(jobs)}")
    results = []
    errors = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=14) as ex:
        futs = {ex.submit(fn, *args): (kind, args) for kind, fn, args in jobs}
        done = 0
        for fut in as_completed(futs):
            kind, args = futs[fut]
            done += 1
            try:
                r = fut.result()
                r["kind"] = kind
                results.append(r)
            except Exception as e:
                errors.append({"kind": kind, "error": str(e)})
            if done % 25 == 0 or done == len(jobs):
                elapsed = time.time() - t0
                print(f"[{done}/{len(jobs)}] elapsed={elapsed:.0f}s errors={len(errors)}")

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    with open("errors.json", "w") as f:
        json.dump(errors, f, indent=2)
    print(f"Done. {len(results)} results, {len(errors)} errors. Elapsed {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
