"""Hand-label validation of the three LLM judges (directive, goal, plan step).

  python3 validate_judges.py sample   -> judge_validation_items.json (no judge labels shown)
  python3 validate_judges.py score    -> judge_validation.json (agreement and Cohen's kappa against hand_labels.json)

hand_labels.json maps item id -> label, written blind to the judge labels:
  directive: RESPECTS / VIOLATES / UNCLEAR, goal: NEW / OLD / OTHER, plan: CORRECT / WRONG (is it step k+1?)
"""
import hashlib, json, random, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_e16 as e  # noqa: E402


def pool():
    out = []
    for jp in sorted((HERE / "judged").glob("t*.json")):
        tid = int(jp.stem[1:])
        lab = json.loads(jp.read_text())
        for R, items in lab.items():
            tr = e.build(tid, int(R))
            p = e.PROCS[tr["proc"]]
            for item, d in items.items():
                for text, v in d.items():
                    if item == "plan":
                        jl = "CORRECT" if (v["kind"] == "step" and v["index"] == tr["k"] + 1) else "WRONG"
                        ctx = dict(steps=[f"{i}. {s['title']}: {s['command']}" for i, s in enumerate(p["steps"], 1)],
                                   completed=tr["k"], correct_next=tr["k"] + 1)
                        kind = "plan"
                    elif item == "goal":
                        g = e.GOALS[tr["goal"]]
                        jl, ctx, kind = v, dict(OLD=g[2], NEW=g[3]), "goal"
                    else:
                        if item == "approach":
                            rule, req = e.APPROACHES[tr["approach"]]
                        else:
                            r = e.RULES[tr["rule_idx"][int(item[-1])]]
                            rule, req = r["rule"], r["trigger"]
                        jl, ctx, kind = v, dict(rule=rule, request=req), "directive"
                    out.append(dict(id=f"t{tid}_R{R}_{item}_{hashlib.md5(text.encode()).hexdigest()[:8]}", kind=kind, tid=tid,
                                    answer=text, context=ctx, judge=jl))
    return out


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        rng = random.Random(1616)
        allp = pool()
        rng.shuffle(allp)
        picked = []
        for kind, per in (("directive", 20), ("goal", 14), ("plan", 20)):
            sub = [x for x in allp if x["kind"] == kind]
            labels = sorted({x["judge"] for x in sub})
            for lab in labels:   # stratify on judge label
                picked += [x for x in sub if x["judge"] == lab][:max(2, per // len(labels))]
        rng.shuffle(picked)
        blind = [{k: v for k, v in x.items() if k != "judge"} for x in picked]
        (HERE / "judge_validation_items.json").write_text(json.dumps(blind, indent=1))
        (HERE / "judge_validation_key.json").write_text(json.dumps({x["id"]: x["judge"] for x in picked}, indent=1))
        print(len(picked), Counter(x["kind"] for x in picked))
    else:
        key = json.loads((HERE / "judge_validation_key.json").read_text())
        hand = json.loads((HERE / "hand_labels.json").read_text())
        items = {x["id"]: x for x in json.loads((HERE / "judge_validation_items.json").read_text())}
        res = {}
        for kind in ("directive", "goal", "plan"):
            ids = [i for i in hand if items[i]["kind"] == kind]
            a = [key[i] for i in ids]; b = [hand[i] for i in ids]
            pos = {"directive": "RESPECTS", "goal": "NEW", "plan": "CORRECT"}[kind]
            ab = [x == pos for x in a]; bb = [x == pos for x in b]
            res[kind] = dict(n=len(ids), agree=sum(x == y for x, y in zip(a, b)), kappa=round(kappa(a, b), 3),
                             binary_agree=sum(x == y for x, y in zip(ab, bb)), binary_kappa=round(kappa(ab, bb), 3),
                             disagreements=[dict(id=i, judge=key[i], hand=hand[i]) for i in ids if key[i] != hand[i]])
        allj = [key[i] for i in hand]; allh = [hand[i] for i in hand]
        res["all"] = dict(n=len(hand), agree=sum(x == y for x, y in zip(allj, allh)), kappa=round(kappa(allj, allh), 3))
        (HERE / "judge_validation.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
