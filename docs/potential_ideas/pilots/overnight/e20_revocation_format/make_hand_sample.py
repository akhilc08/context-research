"""Draw a blind sample of graded replies for hand labeling of the rule judge.

Stratified by the judge's label (16 APPLIES, 16 IGNORES, up to 16 OTHER, topped up from the others), across
formats and conditions, seed 20. Writes hand_sample.json (with the judge label, for scoring) and
hand_input.json (rule, request, reply only; what the labeler sees).
"""
import json, random

import e20lib as L

OUT = L.HERE / "results" / "space_bunny"


def main():
    raw = {(r["sid"], r["cond"], r["fmt"], r["ptype"], r["idx"], r["sample"]): r
           for r in map(json.loads, (OUT / "raw.jsonl").read_text().splitlines())}
    graded = [json.loads(l) for l in (OUT / "graded.jsonl").read_text().splitlines()]
    rng = random.Random(20)
    rng.shuffle(graded)
    by = {"APPLIES": [], "IGNORES": [], "OTHER": []}
    for g in graded:
        by[g["label"]].append(g)
    pick = by["OTHER"][:16]
    need = 48 - len(pick)
    pick += by["APPLIES"][:need // 2] + by["IGNORES"][:need - need // 2]
    rng.shuffle(pick)
    sample, inp = [], []
    for i, g in enumerate(pick):
        r = raw[(g["sid"], g["cond"], g["fmt"], g["ptype"], g["idx"], g["sample"])]
        hid = f"h{i:02d}"
        sample.append(dict(hid=hid, judge_label=g["label"], sid=g["sid"], cond=g["cond"], fmt=g["fmt"],
                           ptype=g["ptype"], rule=r["rule"], request=r["text"], reply=r["raw"]))
        inp.append(dict(hid=hid, rule=r["rule"], request=r["text"], reply=r["raw"]))
    (L.HERE / "hand_sample.json").write_text(json.dumps(sample, indent=1))
    (L.HERE / "hand_input.json").write_text(json.dumps(inp, indent=1))
    print(len(inp), "items")


if __name__ == "__main__":
    main()
