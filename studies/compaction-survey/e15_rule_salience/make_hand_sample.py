"""Draw the blinded hand-label sample for the Part B judge and merge labels afterwards.

  python3 make_hand_sample.py draw    -> data/hand_sample_b.json (rule + summary, no verdict),
                                         data/hand_key_b.json (verdicts, not read while labeling)
  python3 make_hand_sample.py merge   -> hand_labels_b.json from data/hand_my_labels_b.json + key

Stratified on the judge's verdict (up to 12 per label) over R=16 summaries, seed 2026.
"""
import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = HERE / "data"


def draw():
    T = [json.loads(l) for l in (D / "b_transcripts.jsonl").read_text().splitlines()]
    pool = {}
    for t in T:
        r16 = [r for r in t["rounds"] if r["R"] == 16][0]
        for rid, j in r16["judge"].items():
            pool.setdefault(j["verdict"], []).append(
                {"n": t["n"], "idx": t["idx"], "regime": t["regime"], "rule_id": rid,
                 "rule": t["rule_text"][rid], "summary": r16["summary"], "judge": j["verdict"]})
    rng = random.Random(2026)
    items = []
    for v in sorted(pool):
        if v == "ERROR":
            continue
        items += rng.sample(pool[v], min(12, len(pool[v])))
    rng.shuffle(items)
    for k, it in enumerate(items):
        it["k"] = k
    (D / "hand_key_b.json").write_text(json.dumps([{"k": i["k"], "judge": i["judge"]} for i in items], indent=1))
    (D / "hand_sample_b.json").write_text(json.dumps(
        [{k: v for k, v in i.items() if k != "judge"} for i in items], indent=1))
    print(len(items), "items drawn")


def merge():
    key = {x["k"]: x["judge"] for x in json.loads((D / "hand_key_b.json").read_text())}
    mine = json.loads((D / "hand_my_labels_b.json").read_text())
    out = [{"k": m["k"], "hand": m["hand"], "judge": key[m["k"]], "note": m.get("note", "")} for m in mine]
    (HERE / "hand_labels_b.json").write_text(json.dumps(out, indent=1))
    print(len(out), "merged")


if __name__ == "__main__":
    {"draw": draw, "merge": merge}[sys.argv[1]]()
