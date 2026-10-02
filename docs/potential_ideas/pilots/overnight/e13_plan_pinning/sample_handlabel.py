"""Print a seeded sample of graded responses for blind hand labelling (automatic labels are not shown).

60 procedure responses (judge-graded) and 12 batch responses (parser-graded), seeded, stratified over arms.
The labeller writes data/<run>/handlabels.json as a list of {case_id, method, sample, kind, index, invented}.
Usage: python3 sample_handlabel.py [--run main]
"""
import argparse, json, random

from tasks import DATA, load_procs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    a = ap.parse_args()
    procs = load_procs()
    resps = {(r["case_id"], r["method"], r["sample"]): r for r in map(json.loads, (DATA / a.run / "responses.jsonl").read_text().splitlines())}
    keys = sorted(resps)
    rng = random.Random(1313)
    proc = [k for k in keys if k[0].startswith("P")]
    batch = [k for k in keys if k[0].startswith("B")]
    sample = rng.sample(proc, 60) + rng.sample(batch, 12)
    for i, k in enumerate(sample):
        r = resps[k]
        p = procs[k[0].split("-")[0]]
        print(f"=== #{i} {k[0].split('-')[0]}")
        if p["family"] == "proc":
            for j, s in enumerate(p["steps"], 1):
                print(f"  {j}. {s['command']}\n     check: {s['verify_command']}")
        else:
            print("  items:", " ".join(f"{j}:{x}" for j, x in enumerate(p["item_ids"], 1)), "| template:", p["cmd_template"])
        print("  CMD:", r["command"])
        print("  REASON:", r.get("reason", ""))
    (DATA / a.run / "handlabel_sample.json").write_text(json.dumps(sample))


if __name__ == "__main__":
    main()
