"""Ceiling check: with the full uncompacted transcript, the agent's next action must follow the latest
goal in at least 2 of 3 samples (graded by the judge, phrasing A). Also a judge sanity check: each goal's
own operator message, used as the 'action', must be mapped back to that goal.
Writes data/scenarios.json (valid scenarios only) and data/validation.json."""
import json, random
from concurrent.futures import ThreadPoolExecutor
from e2lib import build_sequence, render, agent_action, judge, goal_turn_text

HERE = __import__("pathlib").Path(__file__).resolve().parent
raw = json.loads((HERE / "data/scenarios_raw.json").read_text())


def check(s):
    tasks = [g["task"] for g in s["goals"]]
    latest = len(tasks) - 1
    samples = []
    for k in range(3):
        rng = random.Random(f"ceil-{s['id']}-{k}")
        seq, *_ = build_sequence(s, "mid", rng)
        action, _, _ = agent_action("[Session log, verbatim]\n" + render(seq), tag="e2_ceiling")
        j, jr = judge(action, tasks, seed=f"ceil-{s['id']}-{k}")
        samples.append({"action": action, "judged": j})
    sanity = []
    for gi, g in enumerate(s["goals"]):
        j, _ = judge(g["message"], tasks, seed=f"san-{s['id']}-{gi}")
        sanity.append(j == gi)
    ok = sum(x["judged"] == latest for x in samples) >= 2 and all(sanity)
    return {"id": s["id"], "ok": ok, "ceiling": samples, "judge_sanity": sanity}


def safe(s):
    try:
        return check(s)
    except Exception as e:  # provider failure: count as invalid, record why
        return {"id": s["id"], "ok": False, "error": repr(e)[:200], "ceiling": [], "judge_sanity": []}


with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(safe, raw))
(HERE / "data/validation.json").write_text(json.dumps(res, indent=1))
valid = [s for s, r in zip(raw, res) if r["ok"]]
(HERE / "data/scenarios.json").write_text(json.dumps(valid, indent=1))
for r in res:
    print(r["id"], r["ok"], [x["judged"] for x in r["ceiling"]], r["judge_sanity"])
print("valid", len(valid), "of", len(raw))
