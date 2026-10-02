"""Draw a fixed-seed, blinded sample of (rule, summary) pairs for hand labeling the judge.
Stratified on the first-pass verdict to oversample DISTORTED: 20 DISTORTED, 14 PRESENT, 14 ABSENT.
Drawn from the first 149 completed transcripts (the sample was made while the run was finishing).
Writes data/hand_sample.json (no judge verdicts shown); labels go to data/hand_labels.json."""
import json, random
from pathlib import Path
DATA = Path(__file__).resolve().parent / "data"
T = [json.loads(l) for l in (DATA / "transcripts.jsonl").read_text().splitlines()][:149]
rng = random.Random(2026)
pool = {"DISTORTED": [], "PRESENT": [], "ABSENT": []}
for t in T:
    for r in t["rounds"]:
        v = r["judge"]["verdict"]
        if v in pool:
            pool[v].append({"id": t["id"], "form": t["form"], "regime": t["regime"], "R": r["R"],
                            "rule": t["rule_text"], "summary": r["summary"]})
sample = rng.sample(pool["DISTORTED"], 20) + rng.sample(pool["PRESENT"], 14) + rng.sample(pool["ABSENT"], 14)
rng.shuffle(sample)
(DATA / "hand_sample.json").write_text(json.dumps(sample, indent=1))
print(len(sample))
