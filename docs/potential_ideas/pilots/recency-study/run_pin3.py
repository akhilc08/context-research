import json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import lib
from lib import build_filler_pool, run_multiround, agent_decide, pin_fact
from scenarios import CONSTRAINT_SCENARIOS

lib.MODELS["minimax"] = {"id": "minimax/minimax-01", "reasoning": None}
VALID_IDS = {"merge_pr", "db_migration", "dependency_license", "force_push", "rate_limiter", "hardcoded_creds"}
CONSTRAINT_SCENARIOS = [s for s in CONSTRAINT_SCENARIOS if s["id"] in VALID_IDS]
POOL = build_filler_pool(96)

def trial(sc, backbone, position, rep):
    summary, tail = run_multiround(backbone, POOL, sc["policy"], position, 2, 3, 16)
    summary = pin_fact(summary, sc["policy"], "Active rule")
    decision, raw = agent_decide(backbone, summary, tail, sc["trigger"])
    return {"scenario": sc["id"], "backbone": backbone, "position": position, "method": "pin",
            "rounds": 3, "rep": rep, "decision": decision}

def main():
    jobs = []
    for sc in CONSTRAINT_SCENARIOS:
        for backbone in ["qwen", "minimax"]:
            for position in ["early", "mid", "late"]:
                for rep in range(3):
                    jobs.append((sc, backbone, position, rep))
    results = []
    with ThreadPoolExecutor(max_workers=14) as ex:
        futs = [ex.submit(trial, *j) for j in jobs]
        for f in as_completed(futs):
            results.append(f.result())
    json.dump(results, open("results_pin3.json", "w"), indent=2)
    print("done", len(results))

if __name__ == "__main__":
    main()
