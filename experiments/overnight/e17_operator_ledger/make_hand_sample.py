"""Draw a blind sample of free-text probe answers for hand labeling of the judges and the fact grader.

Usage:
  python3 make_hand_sample.py sample   -> hand_sample.json (items without judge verdicts)
  python3 make_hand_sample.py merge    -> hand_labels.json (hand labels from hand_input.json joined with judge verdicts)

hand_input.json is a list of {"i": <item index>, "hand": ...} written by the labeler. For rule items "hand"
is APPLIES, IGNORES or OTHER (the judge's categories); for the others it is true when the answer is correct
(current goal / correct next step / correct value).
"""
import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "space_bunny"
PROCS = {p["id"]: p for p in json.loads((HERE.parent / "e8_inflight" / "data" / "procedures.json").read_text())}


def sample():
    rows = [json.loads(l) for l in (OUT / "graded.jsonl").read_text().splitlines()]
    sess = {s["sid"]: s for s in json.loads((HERE / "data" / "sessions.json").read_text())}
    raws = {}
    for f in (OUT / "sessions").glob("S*.json"):
        o = json.loads(f.read_text())
        for r in o["results"]:
            raws[(o["sid"], r["arm"], r["ptype"], r["idx"])] = r["raw"]
    rng = random.Random(1717)
    items = []
    for kind, n in (("rule", 44), ("goal", 40), ("plan", 40), ("fact_history", 15), ("fact_current", 5)):
        if kind == "rule":
            pool = [r for r in rows if r["ptype"] in ("active", "revoked", "amended")]
            items_k = []
            for lab, m in (("APPLIES", 18), ("IGNORES", 18), ("OTHER", 8)):
                sub = [r for r in pool if r["label"] == lab]
                for r in rng.sample(sub, min(m, len(sub))):
                    t = sess[r["sid"]]["truth"]
                    item = t[r["ptype"]][r["idx"]]
                    req = item.get("trigger") or item.get("probe")
                    items_k.append(dict(kind="rule", ptype=r["ptype"], sid=r["sid"], arm=r["arm"], idx=r["idx"],
                                        rule=item["rule"], request=req,
                                        answer=raws[(r["sid"], r["arm"], r["ptype"], r["idx"])]))
            items += items_k
            continue
        pool = [r for r in rows if r["ptype"] == kind]
        # balance judge-positive and judge-negative so kappa is informative
        pos = [r for r in pool if r["correct"]]
        neg = [r for r in pool if not r["correct"]]
        pick = rng.sample(pos, min(len(pos), n // 2)) + rng.sample(neg, min(len(neg), n - n // 2))
        for r in pick:
            t = sess[r["sid"]]["truth"]
            it = dict(kind=kind, sid=r["sid"], arm=r["arm"], idx=r["idx"],
                      answer=raws[(r["sid"], r["arm"], r["ptype"], r["idx"])])
            if kind == "goal":
                it["goals_in_order"] = [g["task"] for g in t["goals"]]
                it["side_procedure"] = t["plan"]["name"]
            elif kind == "plan":
                p = PROCS[t["plan"]["proc_id"]]
                it["steps"] = [f"{i}. {s['command']}" for i, s in enumerate(p["steps"], 1)]
                it["steps_done"] = t["plan"]["k"]
            else:
                it["values_in_order"] = t["facts"][r["idx"]]["values"]
            items.append(it)
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["i"] = i
    (HERE / "hand_sample.json").write_text(json.dumps(items, indent=1))
    print(len(items), "items")


def merge():
    items = json.loads((HERE / "hand_sample.json").read_text())
    hand = {x["i"]: x["hand"] for x in json.loads((HERE / "hand_input.json").read_text())}
    rows = {(r["sid"], r["arm"], r["ptype"], r["idx"]): r for r in
            (json.loads(l) for l in (OUT / "graded.jsonl").read_text().splitlines())}
    out = []
    for it in items:
        pt = it.get("ptype", it["kind"])
        r = rows[(it["sid"], it["arm"], pt, it["idx"])]
        kind = "fact" if it["kind"].startswith("fact") else it["kind"]
        judge = r["label"] if kind == "rule" else bool(r["correct"])
        out.append(dict(i=it["i"], kind=kind, sid=it["sid"], arm=it["arm"], judge=judge, hand=hand.get(it["i"])))
    (HERE / "hand_labels.json").write_text(json.dumps(out, indent=1))
    print(sum(x["hand"] is not None for x in out), "labeled")


if __name__ == "__main__":
    {"sample": sample, "merge": merge}[sys.argv[1]]()
