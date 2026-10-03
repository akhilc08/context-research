"""Draw the judge spot-check sample: 48 new LongMemEval verdicts (24 judge-yes, 24 judge-no), seed 7,
from arms E14 never judged. Writes results/hand_label_sample.json (with verdicts) and prints the
items without verdicts for blind labeling."""
import json, random
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEW = ["minimal", "recipe", "r_nopin", "r_novblock", "tm", "fifo1200", "headtail1200", "fifo_tm", "headtail_tm",
       "mask", "resum", "struct", "carry", "prov300", "anchor", "watch", "watch_strict", "watch_self", "roundtrip",
       "repair", "ledger", "registry"]
items = {True: [], False: []}
for rep in (1, 2):
    for d in sorted((HERE / "results" / "units" / f"rep{rep}" / "lme").iterdir()):
        j = json.loads((d / "judge.json").read_text())
        for a in NEW:
            if a in j:
                items[j[a]["yes"]].append({"rep": rep, "qid": d.name, "arm": a, "judge_yes": j[a]["yes"], "answer": j[a]["answer"]})
rng = random.Random(7)
smp = rng.sample(items[True], 24) + rng.sample(items[False], 24)
rng.shuffle(smp)
meta = {t["qid"]: t for t in json.loads((HERE.parent / "e14_versioned_pin" / "results" / "tasks_meta.json").read_text())}
for i, s in enumerate(smp):
    s["i"] = i; s["question"] = meta[s["qid"]]["question"]; s["gold"] = meta[s["qid"]]["answer"]
(HERE / "results" / "hand_label_sample.json").write_text(json.dumps(smp, indent=1))
for s in smp:
    print(f"#{s['i']} Q: {s['question']}\n   GOLD: {s['gold']}\n   ANS: {s['answer'][:500]}\n")
