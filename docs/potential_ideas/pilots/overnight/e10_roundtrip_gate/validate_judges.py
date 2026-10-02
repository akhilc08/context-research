"""Validate the two LLM judges (directive RESPECTS/VIOLATES and goal NEW/OLD/OTHER) against hand labels.

python3 validate_judges.py dump    -> judge_validation_items.json (blind: judge labels hidden)
python3 validate_judges.py score   -> compares hand_labels.json with the judges, writes judge_validation.json
"""
import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "e9_cheap_validation"))
from common import load_rules  # noqa: E402
from items import GOALS, APPROACHES  # noqa: E402

RULES = {r["id"]: r for r in load_rules() if r.get("valid")}
ITEMS = HERE / "judge_validation_items.json"
HAND = HERE / "hand_labels.json"


def collect():
    rows = {}
    for p in sorted((HERE / "raw").glob("t*.json")):
        r = json.loads(p.read_text())
        tr = r["transcript"]
        for arm, a in r["arms"].items():
            if "probes" not in a:
                continue
            for item in ("rule0", "rule1", "approach", "goal"):
                for i, s in enumerate(a["probes"][item]):
                    if "judge" not in s:
                        continue
                    if item == "goal":
                        ctx = dict(old=GOALS[tr["goal"]][2], new=GOALS[tr["goal"]][3])
                        kind = "goal"
                    elif item == "approach":
                        ctx = dict(instruction=APPROACHES[tr["approach"]][0], request=APPROACHES[tr["approach"]][1])
                        kind = "directive"
                    else:
                        rule = RULES[tr["rules"][int(item[-1])]]
                        ctx = dict(instruction=rule["rule"], request=rule["trigger"])
                        kind = "directive"
                    key = f"{r['tid']}|{item}|{s['raw'][:60]}"
                    rows[key] = dict(id=key, kind=kind, answer=s["raw"], judge=s["judge"], **ctx)
    return list(rows.values())


def dump(n_each=44):
    rows = collect()
    rng = random.Random(11)
    pick = []
    for kind in ("directive", "goal"):
        rs = [r for r in rows if r["kind"] == kind]
        by = {}
        for r in rs:
            by.setdefault(r["judge"], []).append(r)
        chosen = []
        for lab, group in by.items():  # stratify so minority labels are represented
            rng.shuffle(group)
            chosen += group[:max(8, n_each * len(group) // len(rs))]
        rng.shuffle(chosen)
        pick += chosen[:n_each]
    rng.shuffle(pick)
    ITEMS.write_text(json.dumps([{k: v for k, v in r.items() if k != "judge"} for r in pick], indent=1))
    print(len(pick))


def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def score():
    hand = json.loads(HAND.read_text())
    judge = {r["id"]: r for r in collect()}
    out = {}
    for kind in ("directive", "goal"):
        keys = [k for k in hand if judge[k]["kind"] == kind]
        a = [hand[k] for k in keys]; b = [judge[k]["judge"] for k in keys]
        po, k = kappa(a, b)
        conf = {}
        for x, y in zip(a, b):
            conf[f"hand={x},judge={y}"] = conf.get(f"hand={x},judge={y}", 0) + 1
        good = "NEW" if kind == "goal" else "RESPECTS"
        pob, kb = kappa([x == good for x in a], [y == good for y in b])
        out[kind] = dict(n=len(keys), agreement=po, kappa=k, binary_agreement=pob, binary_kappa=kb, confusion=conf,
                         disagreements=[kk for kk in keys if hand[kk] != judge[kk]["judge"]])
    (HERE / "judge_validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"dump": dump, "score": score}[sys.argv[1]]()
