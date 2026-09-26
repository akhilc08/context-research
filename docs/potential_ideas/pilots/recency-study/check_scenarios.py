import sys, json
sys.path.insert(0, ".")
from lib import build_filler_pool, agent_decide, agent_decide_goal, MODELS
from scenarios import CONSTRAINT_SCENARIOS, GOAL_SCENARIOS

pool = build_filler_pool(96)

def check_constraint_scenario(sc, model_key, n=2):
    # no policy at all in context: expect COMPLY every time
    decisions = [agent_decide(model_key, "", pool[:6], sc["trigger"])[0] for _ in range(n)]
    return decisions

def check_goal_scenario(sc, model_key, n=2):
    # G1 only, never redirected: expect ORIGINAL_TASK
    orig = [agent_decide_goal(model_key, "", [sc["g1"]] + pool[:4], sc["trigger"], sc["g1_kw"], sc["g2_kw"])[0] for _ in range(n)]
    # both G1 and G2 fully visible, no compaction: expect REVISED_TASK
    revised = [agent_decide_goal(model_key, "", [sc["g1"], sc["g2"]] + pool[:4], sc["trigger"], sc["g1_kw"], sc["g2_kw"])[0] for _ in range(n)]
    return orig, revised

if __name__ == "__main__":
    results = {"constraint": {}, "goal": {}}
    print("=== Constraint scenario floor checks (expect all COMPLY) ===")
    for sc in CONSTRAINT_SCENARIOS:
        row = {}
        for mk in MODELS:
            d = check_constraint_scenario(sc, mk)
            row[mk] = d
            print(f"{sc['id']:20s} {mk:10s} {d}")
        results["constraint"][sc["id"]] = row

    print()
    print("=== Goal scenario floor/ceiling checks (expect ORIGINAL then REVISED) ===")
    for sc in GOAL_SCENARIOS:
        orig, revised = check_goal_scenario(sc, "qwen")
        print(f"{sc['id']:20s} orig(no redirect)={orig}  revised(full context)={revised}")
        results["goal"][sc["id"]] = {"orig": orig, "revised": revised}

    with open("check_results.json", "w") as f:
        json.dump(results, f, indent=2)
