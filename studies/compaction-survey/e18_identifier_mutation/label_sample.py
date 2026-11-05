"""Judge validation helper.

  python3 label_sample.py dump  -> writes data/<slug>/handlabel_<name>.txt with blind items (no judge verdict)
  python3 label_sample.py merge -> reads data/<slug>/hand_<name>.json ({content key: 0 or 1}) and writes
                                    data/<slug>/labels_<name>.json with hand and judge labels for analyze.py

Samples (seed 7): up to 60 summary-judge decisions, stratified to include both verdicts, and up to 60
probe-judge decisions.
"""
import hashlib, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run import slug  # noqa: E402

MODEL = "stealth/space-bunny-alpha"


def key(x):
    """Content key for an item, so hand labels survive re-sampling."""
    return hashlib.sha1((x.get("summary", x.get("reply", "")) + "|" + x.get("cand", x.get("probe", ""))).encode()).hexdigest()[:12]


def load(model):
    d = HERE / "data" / slug(model)
    S = {s["id"]: s for s in json.loads((HERE / "data" / "scenarios.json").read_text())}
    chains = {(c["scenario"], c["budget"], c["summarizer"]): c["rounds"]
              for c in map(json.loads, (d / "chains.jsonl").read_text().splitlines())}
    GS = [json.loads(l) for l in (d / "graded_summaries.jsonl").read_text().splitlines()]
    gp = d / "graded_probes.jsonl"
    GP = [json.loads(l) for l in gp.read_text().splitlines()] if gp.exists() else []
    return d, S, chains, GS, GP


def samples(model):
    d, S, chains, GS, GP = load(model)
    rng = random.Random(7)
    items = {(sid, it["type"]): it for sid, s in S.items() for it in s["items"]}
    # dedupe identical (summary, cand) decisions
    sj, seen = [], set()
    for g in GS:
        for j in g["judged"]:
            summ = chains[(g["scenario"], g["budget"], g["summarizer"])][g["round"] - 1]["summary"]
            k = (summ, j["cand"])
            if k in seen:
                continue
            seen.add(k)
            sj.append({"summary": summ, "cand": j["cand"], "role": items[(g["scenario"], g["type"])]["role"],
                       "judge": int(j["yes"])})
    yes_ = [x for x in sj if x["judge"]]
    no_ = [x for x in sj if not x["judge"]]
    rng.shuffle(yes_); rng.shuffle(no_)
    sj = (yes_ + no_) if len(yes_) + len(no_) <= 60 else yes_[:30] + no_[:max(30, 60 - len(yes_[:30]))]
    rng.shuffle(sj)
    pj, seen_p = [], set()
    for g in GP:
        if g["judge"] is None:
            continue
        k = (g["body"], items[(g["scenario"], g["type"])]["probe"])
        if k not in seen_p:  # identical prompts get identical cached verdicts; label each once
            seen_p.add(k)
            pj.append(g)
    rng.shuffle(pj)
    pj = [{"probe": items[(g["scenario"], g["type"])]["probe"], "role": items[(g["scenario"], g["type"])]["role"],
           "reply": g["body"], "target": g["target"], "judge": int(g["judge"])} for g in pj[:60]]
    return d, {"summary_judge": sj, "probe_judge": pj}


def main():
    mode = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else MODEL
    d, sets = samples(model)
    for name, xs in sets.items():
        if mode == "dump":
            with open(d / f"handlabel_{name}.txt", "w") as f:
                for i, x in enumerate(xs):
                    f.write(f"### {key(x)}\nITEM: {x['role']}\n")
                    if name == "summary_judge":
                        f.write(f"CANDIDATE: {x['cand']}\nSUMMARY: {x['summary']}\n\n")
                    else:
                        f.write(f"TASK: {x['probe']}\nREPLY: {x['reply']}\n\n")
            print(name, len(xs))
        else:
            hand = json.loads((d / f"hand_{name}.json").read_text())
            out = [dict(x, hand=int(hand[key(x)])) for x in xs if key(x) in hand]
            if len(out) < len(xs):
                print(f"{name}: {len(xs) - len(out)} sampled items have no hand label")
            (d / f"labels_{name}.json").write_text(json.dumps(out, indent=1))
            print(name, len(out))


if __name__ == "__main__":
    main()
