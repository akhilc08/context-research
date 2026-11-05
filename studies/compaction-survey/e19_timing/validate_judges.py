"""Judge validation for E19.

  python3 validate_judges.py sample   -> writes judge_validation_items.json (seeded, blind: no arm, turn, or label)
  python3 validate_judges.py score    -> compares hand_labels.json with the judge labels, prints agreement and kappa

The sample has 24 directive answers (E10 judge), 12 goal answers (E10 judge), and 24 next-step commands that
the exact-match rule could not settle (E13 judge). Hand labels are written by the study agent into
hand_labels.json as {"id": label}, using the same label sets as the judges
(directive: RESPECTS / VIOLATES / UNCLEAR; goal: OLD / NEW / OTHER; next: "step j" / "verify j" / "other").
"""
import json, random, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
sys.path.insert(0, str(HERE.parent / "e09_cheap_validation"))
from common import load_rules  # noqa: E402
from items import GOALS, APPROACHES  # noqa: E402

RULES = [r for r in load_rules() if r.get("valid")]
SESSIONS = json.loads((HERE / "data" / "sessions.json").read_text())
PROCS = {p["id"]: p for p in json.loads((HERE.parent / "e13_plan_pinning" / "data" / "procedures.json").read_text())}


def pool():
    out = []
    for p in sorted((HERE / "judged").glob("s*.json")):
        sid = int(p.stem[1:])
        J = json.loads(p.read_text())
        s = SESSIONS[sid]
        specs = {f"rule{k}": (RULES[r]["rule"], RULES[r]["trigger"]) for k, r in enumerate(s["rule_idx"])}
        specs["approach"] = APPROACHES[s["approach"]]
        for item in ("rule0", "rule1", "approach"):
            for ans, lab in J.get(item, {}).items():
                out.append(dict(type="directive", sid=sid, item=item, rule=specs[item][0], request=specs[item][1],
                                answer=ans, judge=lab))
        g = GOALS[s["goal"]]
        for ans, lab in J.get("goal", {}).items():
            out.append(dict(type="goal", sid=sid, old=g[2], new=g[3], answer=ans, judge=lab))
        for key, lab in J.get("next", {}).items():
            if lab.get("how") != "judge":
                continue
            pid, cmd, reason = key.split("\x1f")
            steps = [f"{i}. {st['title']}: `{st['command']}`  (check: `{st['verify_command']}`)"
                     for i, st in enumerate(PROCS[pid]["steps"], 1)]
            j = lab["kind"] if lab["kind"] == "other" else f"{lab['kind']} {lab['index']}"
            out.append(dict(type="next", sid=sid, proc=pid, steps=steps, cmd=cmd, reason=reason, judge=j))
    return out


def sample():
    rng = random.Random(1919)
    P = pool()
    by = {t: [x for x in P if x["type"] == t] for t in ("directive", "goal", "next")}
    # stratify directive answers on judge label so that violations are represented
    d = by["directive"]
    resp = [x for x in d if x["judge"] == "RESPECTS"]
    other = [x for x in d if x["judge"] != "RESPECTS"]
    pick = rng.sample(resp, min(14, len(resp))) + rng.sample(other, min(10, len(other)))
    pick += rng.sample(by["goal"], min(12, len(by["goal"])))
    pick += rng.sample(by["next"], min(24, len(by["next"])))
    rng.shuffle(pick)
    items = []
    for i, x in enumerate(pick):
        x = dict(x, id=f"h{i:02d}")
        items.append(x)
    (HERE / "judge_validation_items.json").write_text(json.dumps(items, indent=1))
    for x in items:  # blind print: no judge label
        print(f"--- {x['id']} [{x['type']}]")
        if x["type"] == "directive":
            print("RULE:", x["rule"]); print("REQUEST:", x["request"]); print("ANSWER:", x["answer"])
        elif x["type"] == "goal":
            print("OLD:", x["old"]); print("NEW:", x["new"]); print("ANSWER:", x["answer"])
        else:
            print("\n".join(x["steps"])); print("CMD:", x["cmd"]); print("REASON:", x["reason"])


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def score():
    items = {x["id"]: x for x in json.loads((HERE / "judge_validation_items.json").read_text())}
    hand = json.loads((HERE / "hand_labels.json").read_text())
    res = {}
    for t in ("directive", "goal", "next", "all"):
        ids = [i for i in hand if t == "all" or items[i]["type"] == t]
        a = [hand[i] for i in ids]
        b = [items[i]["judge"] for i in ids]
        if t == "directive":  # binary used by the outcome: RESPECTS or not
            a2, b2 = [x == "RESPECTS" for x in a], [x == "RESPECTS" for x in b]
        elif t == "next":  # the primary outcome needs "performs step j" (with j) versus anything else
            a2 = [x if x.startswith("step") else "not-step" for x in a]
            b2 = [x if x.startswith("step") else "not-step" for x in b]
        else:
            a2, b2 = a, b
        agree = sum(x == y for x, y in zip(a, b))
        res[t] = dict(n=len(ids), agree=agree, kappa=round(kappa(a, b), 3),
                      binary_agree=sum(x == y for x, y in zip(a2, b2)), binary_kappa=round(kappa(a2, b2), 3),
                      disagreements=[dict(id=i, hand=hand[i], judge=items[i]["judge"]) for i in ids
                                     if hand[i] != items[i]["judge"]])
    (HERE / "judge_validation.json").write_text(json.dumps(res, indent=1))
    for t, r in res.items():
        print(t, {k: v for k, v in r.items() if k != "disagreements"})
        for d in r["disagreements"]:
            print("   ", d)


if __name__ == "__main__":
    {"sample": sample, "score": score}[sys.argv[1]]()
