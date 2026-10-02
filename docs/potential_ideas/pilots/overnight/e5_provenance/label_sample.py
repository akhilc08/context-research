"""Judge validation helper.

  python label_sample.py sample   -> writes results/label_sample.json (fixed seed, stratified by judge verdict)
                                     and prints the items WITHOUT the judge verdicts, for blind hand labeling
  python label_sample.py merge FILE -> FILE holds {"<item key>": "<human label>"}; writes results/hand_labels.json
  python label_sample.py holdout  -> 30 fresh family-A replies (results/label_holdout.json) for the v2 judge
"""
import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCEN = json.loads((HERE / "data" / "scenarios.json").read_text())
BY_ID = {s["id"]: s for fam in SCEN.values() for s in fam}
SAMPLE = HERE / "results" / "label_sample.json"


def load():
    return [json.loads(l) for l in (HERE / "results" / "trials.jsonl").read_text().splitlines()]


def strat(items, key, per, rng, total):
    groups = {}
    for it in items:
        groups.setdefault(key(it), []).append(it)
    out = []
    for g in sorted(groups):
        rng.shuffle(groups[g])
        out += groups[g][:per]
    rest = [it for it in items if it not in out]
    rng.shuffle(rest)
    return (out + rest)[:total]


def sample():
    rng = random.Random(5)
    T = load()
    summ, viol, act = [], [], []
    for t in T:
        s = BY_ID[t["id"]]
        for c, o in t["conds"].items():
            j = o.get("summary_judge")
            if j and t["variant"] in ("inject", "legit"):
                summ.append({"key": f"S|{t['id']}|{t['variant']}|{c}", "judge": str(j.get("category")).upper(),
                             "variant": t["variant"],
                             "content": (s.get("injected_claim") or s.get("planted_action")) if t["variant"] == "inject"
                             else (s.get("operator_waiver") or s.get("operator_version")),
                             "summary": o["summary"]})
            if t["family"] == "A" and o.get("decision") == "COMPLY":
                viol.append({"key": f"V|{t['id']}|{t['variant']}|{c}", "judge": "YES" if o["acted"] else "NO",
                             "rule": s["rule"], "trigger": s["trigger"], "reply": o["raw"]})
            if t["family"] == "B":
                act.append({"key": f"B|{t['id']}|{t['variant']}|{c}", "judge": "YES" if o["acted"] else "NO",
                            "planted_action": s["planted_action"], "plan": o["plan"]})
    S = {"summary_category": strat(summ, lambda x: x["judge"], 12, rng, 44),
         "a_violation": strat(viol, lambda x: x["judge"], 20, rng, 40),
         "b_action": strat(act, lambda x: x["judge"], 20, rng, 40)}
    for v in S.values():
        rng.shuffle(v)
    SAMPLE.write_text(json.dumps(S, indent=1))
    for name, items in S.items():
        print(f"\n######## {name}")
        for it in items:
            print("\n---", it["key"])
            for k, v in it.items():
                if k not in ("key", "judge"):
                    print(f"{k}: {v}")


def merge(path):
    S = json.loads(SAMPLE.read_text())
    H = json.loads(Path(path).read_text())
    out = {name: [{"key": it["key"], "judge": it["judge"], "human": H[it["key"]]} for it in items if it["key"] in H]
           for name, items in S.items()}
    (HERE / "results" / "hand_labels.json").write_text(json.dumps(out, indent=1))
    print({k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sample()
    elif sys.argv[1] == "merge":
        merge(sys.argv[2])


def holdout(n=30):
    """Fresh A COMPLY replies not in the first sample, for validating the post hoc v2 violation judge."""
    S = json.loads(SAMPLE.read_text())
    used = {it["key"] for it in S["a_violation"]}
    rng = random.Random(11)
    pool = []
    for t in load():
        if t["family"] != "A":
            continue
        s = BY_ID[t["id"]]
        for c, o in t["conds"].items():
            k = f"V|{t['id']}|{t['variant']}|{c}"
            if o.get("decision") == "COMPLY" and k not in used:
                pool.append({"key": k, "judge": "YES" if o["acted"] else "NO", "rule": s["rule"],
                             "trigger": s["trigger"], "reply": o["raw"]})
    rng.shuffle(pool)
    H = pool[:n]
    (HERE / "results" / "label_holdout.json").write_text(json.dumps(H, indent=1))
    for it in H:
        print("\n---", it["key"])
        for k in ("rule", "trigger", "reply"):
            print(f"{k}: {it[k]}")


if __name__ == "__main__" and sys.argv[1] == "holdout":
    holdout()
