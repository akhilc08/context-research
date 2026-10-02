"""Validate the goal-probe LLM judge against hand labels.

python3 validate_judge.py dump    -> writes judge_validation_items.json (blind: no judge labels)
python3 validate_judge.py score   -> compares hand_labels.json with the judge's labels
"""
import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from items import GOALS  # noqa: E402

ITEMS = HERE / "judge_validation_items.json"
HAND = HERE / "hand_labels.json"


def collect():
    rows = []
    for p in sorted((HERE / "raw").glob("ev*.json")):
        e = json.loads(p.read_text())
        g = e["probes"]["goal"]
        for ctx in ("full", "summ"):
            for i in range(2):
                rows.append(dict(id=f"{e['eid']}-{ctx}-{i}", old=GOALS[e["goal"]][2], new=GOALS[e["goal"]][3],
                                 answer=g["raw"][ctx][i], judge=g[ctx][i]))
    return rows


def dump(n=48):
    rows = collect()
    rng = random.Random(7)
    # stratify on judge label so rare classes are represented, but keep labels hidden in the output
    by = {}
    for r in rows:
        by.setdefault(r["judge"], []).append(r)
    pick = []
    for lab, rs in by.items():
        rng.shuffle(rs)
        pick += rs[:max(8, n * len(rs) // len(rows))]
    rng.shuffle(pick)
    ITEMS.write_text(json.dumps([{k: r[k] for k in ("id", "old", "new", "answer")} for r in pick], indent=1))
    print(len(pick), {k: len(v) for k, v in by.items()})


def score():
    hand = json.loads(HAND.read_text())
    judge = {r["id"]: r["judge"] for r in collect()}
    a = [hand[k] for k in hand]; b = [judge[k] for k in hand]
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    k = (po - pe) / (1 - pe)
    conf = {}
    for x, y in zip(a, b):
        conf[f"hand={x},judge={y}"] = conf.get(f"hand={x},judge={y}", 0) + 1
    out = dict(n=n, agreement=po, kappa=k, confusion=conf,
               disagreements=[kk for kk in hand if hand[kk] != judge[kk]])
    (HERE / "judge_validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"dump": dump, "score": score}[sys.argv[1]]()
