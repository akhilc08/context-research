"""Judge validation helper (blind hand labels).

  python label_sample.py sample      -> results/label_sample.json (fixed seed, stratified by judge verdict) and
                                        results/label_view.txt (the items WITHOUT judge verdicts, for labeling)
  python label_sample.py merge FILE  -> FILE holds {"<item key>": "<human label>"}; writes results/hand_labels.json
"""
import json, random, sys

from lib import HERE, load_scen

SAMPLE = HERE / "results" / "label_sample.json"
VIEW = HERE / "results" / "label_view.txt"


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
    out = (out + rest)[:total]
    rng.shuffle(out)
    return out


def sample():
    rng = random.Random(23)
    BY = {s["id"]: s for f in load_scen().values() for s in f}
    T = [json.loads(l) for l in (HERE / "results" / "trials_label_snapshot.jsonl").read_text().splitlines()]  # inject sessions, 03:52 snapshot
    summ, viol, act = [], [], []
    for t in T:
        s = BY[t["id"]]
        if t["variant"] in ("inject", "legit"):
            for ch, d in t["sjudge"].items():
                for rd, j in d.items():
                    content = ((s.get("injected_claim") or s.get("planted_action")) if t["variant"] == "inject"
                               else (s.get("operator_waiver") or s.get("operator_version")))
                    summ.append({"key": f"S|{t['id']}|{t['variant']}|{t['rep']}|{ch}|{rd}",
                                 "judge": str(j.get("category")).upper(), "variant": t["variant"],
                                 "source": s["tool_cmd"] if t["variant"] == "inject" else "operator",
                                 "content": content, "summary": t["summaries"][ch][rd]})
        for rd, cs in t["cp"].items():
            for c, o in cs.items():
                k = f"{t['id']}|{t['variant']}|{t['rep']}|{rd}|{c}"
                if t["family"] == "A" and o.get("decision") == "COMPLY":
                    viol.append({"key": "V|" + k, "judge": "YES" if o["acted"] else "NO", "rule": s["rule"],
                                 "trigger": s["trigger"], "reply": o["raw"]})
                if t["family"] == "B":
                    act.append({"key": "B|" + k, "judge": "YES" if o["acted"] else "NO",
                                "action": s["planted_action"], "plan": o["raw"]})
    over = [{"key": f"O|{s['id']}", "judge": str(s["overtness"]), "tool_output": s["tool_output"]} for s in BY.values()]
    S = {"summary_category": strat(summ, lambda x: x["judge"], 10, rng, 44),
         "a_violation": strat(viol, lambda x: x["judge"], 20, rng, 40),
         "b_action": strat(act, lambda x: x["judge"], 20, rng, 40),
         "overtness": strat(over, lambda x: x["judge"], 14, rng, 40)}
    SAMPLE.write_text(json.dumps(S, indent=1))
    with open(VIEW, "w") as fh:
        for name, items in S.items():
            fh.write(f"\n######## {name}\n")
            for it in items:
                fh.write(f"\n--- {it['key']}\n")
                for k, v in it.items():
                    if k not in ("key", "judge"):
                        fh.write(f"{k}: {v}\n")
    print({k: len(v) for k, v in S.items()})


def merge(path):
    S = json.loads(SAMPLE.read_text())
    H = json.loads(open(path).read())
    out = {name: [{"key": it["key"], "judge": it["judge"], "human": H[it["key"]]} for it in items if it["key"] in H]
           for name, items in S.items()}
    (HERE / "results" / "hand_labels.json").write_text(json.dumps(out, indent=1))
    print({k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    {"sample": sample, "merge": lambda: merge(sys.argv[2])}[sys.argv[1]]()
