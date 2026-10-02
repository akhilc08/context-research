"""Print a seeded sample of judged responses for hand labelling (judge labels hidden).

The sample takes 48 responses: 36 procedure cases and 12 batch cases, seeded. The labeller writes
data/<run>/handlabels.json as a list of {case_id, method, kind, index}.
Usage: python3 sample_handlabel.py [--run main]
"""
import argparse, json, random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    a = ap.parse_args()
    d = HERE / "data"
    procs = {p["id"]: p for p in json.loads((d / "procedures.json").read_text())}
    procs.update({p["id"]: p for p in json.loads((d / "batches.json").read_text())})
    judged = [json.loads(l) for l in (d / a.run / "judged.jsonl").read_text().splitlines()]
    judged.sort(key=lambda r: (r["case_id"], r["method"]))
    rng = random.Random(4040)
    proc = [r for r in judged if r["case_id"].startswith("P")]
    batch = [r for r in judged if r["case_id"].startswith("B")]
    sample = rng.sample(proc, 36) + rng.sample(batch, 12)
    for i, r in enumerate(sample):
        p = procs[r["case_id"].split("-")[0]]
        print(f"=== #{i} {r['case_id']} {r['method']}")
        if r["case_id"].startswith("P"):
            for j, s in enumerate(p["steps"], 1):
                print(f"  {j}. {s['command']}")
        else:
            print("  items:", " ".join(f"{j}:{x}" for j, x in enumerate(p["item_ids"], 1)), "| template:", p["cmd_template"])
        print("  CMD:", r["command"])
    (d / a.run / "handlabel_sample.json").write_text(json.dumps([[r["case_id"], r["method"]] for r in sample]))


if __name__ == "__main__":
    main()
