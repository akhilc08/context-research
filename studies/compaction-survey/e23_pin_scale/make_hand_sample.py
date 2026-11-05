"""Draw blind samples for hand validation (E23).

--part classifier: 60 unique operator messages (20 load-bearing, 20 chatter the classifier kept, 20 chatter it
  dropped) -> hand_classifier_sample.json (with labels, kept aside) and hand_classifier_input.json (text only).
--part judges: rule judge 40 (balanced by the judge's label), goal judge 20, plan judge 20
  -> hand_sample.json (with model labels) and hand_input.json (without).
--part audit: audit judge, 30 rule states (12 not in force, 18 in force) -> hand_audit_sample.json, hand_audit_input.json.
Hand labels are written to hand_classifier.json and hand_labels.json, which analyze.py reads.

Usage: python3 make_hand_sample.py --part classifier|judges|audit [--model MODEL]
"""
import argparse, json, random

import e23lib as L
from grade import field


def sessions_out(out):
    return [json.loads(f.read_text()) for f in sorted((out / "sessions").glob("M*.json"))]


def classifier_part(out, truth, rng):
    cls = {}
    for r in sessions_out(out):
        ops = {o["turn"]: o for o in truth[r["sid"]]["operator_turns"]}
        for c in r["prep"]["classify"]:
            cls[ops[c["turn"]]["text"]] = (c["truth"], c["directive"])
    items = sorted(cls.items())
    lb = [i for i in items if i[1][0]]
    ck = [i for i in items if not i[1][0] and i[1][1]]
    cd = [i for i in items if not i[1][0] and not i[1][1]]
    cs = rng.sample(lb, 20) + rng.sample(ck, min(20, len(ck))) + rng.sample(cd, 20)
    rng.shuffle(cs)
    (L.HERE / "hand_classifier_sample.json").write_text(json.dumps(
        [dict(i=n, text=t, generation=g, classifier=c) for n, (t, (g, c)) in enumerate(cs)], indent=1))
    (L.HERE / "hand_classifier_input.json").write_text(json.dumps(
        [dict(i=n, text=t) for n, (t, _) in enumerate(cs)], indent=1))
    print(len(cs), "classifier items")


def judges_part(out, truth, rng):
    graded = L.read_jsonl(out / "graded.jsonl")
    outs = sessions_out(out)
    raw = {(r["sid"], x["arm"], x["ptype"], x["idx"]): x for r in outs for x in r["results"]}
    sample = []
    rule_rows = [g for g in graded if g["ptype"] in ("active", "revoked", "amended")]
    for lab, k in (("APPLIES", 16), ("IGNORES", 16), ("OTHER", 8)):
        pool = [g for g in rule_rows if g["label"] == lab]
        for g in rng.sample(pool, min(k, len(pool))):
            t = truth[g["sid"]]["truth"][g["ptype"]][g["idx"]]
            x = raw[(g["sid"], g["arm"], g["ptype"], g["idx"])]
            sample.append(dict(judge="rule", key=[g["sid"], g["arm"], g["ptype"], g["idx"]], model=g["label"],
                               show=dict(rule=t["rule"], request=x["text"], reply=x["raw"])))
    for g in rng.sample([g for g in graded if g["ptype"] == "goal"], 20):
        s = truth[g["sid"]]
        x = raw[(g["sid"], g["arm"], "goal", 0)]
        sample.append(dict(judge="goal", key=[g["sid"], g["arm"], "goal", 0], model=g["label"],
                           show=dict(goals_in_order=[q["task"] for q in s["truth"]["goals"]],
                                     side_procedure=s["truth"]["plan"]["goal"], action=field(x["raw"], "ACTION"))))
    procs = {p["id"]: p for p in json.loads((L.OVERNIGHT / "e08_inflight" / "data" / "procedures.json").read_text())}
    for g in rng.sample([g for g in graded if g["ptype"] == "plan"], 20):
        s = truth[g["sid"]]
        p = procs[s["truth"]["plan"]["proc_id"]]
        sample.append(dict(judge="plan", key=[g["sid"], g["arm"], "plan", 0], model=g["label"],
                           show=dict(steps=[st["command"] for st in p["steps"]], done_through=s["truth"]["plan"]["k"],
                                     command=g["command"])))
    rng.shuffle(sample)
    (L.HERE / "hand_sample.json").write_text(json.dumps(sample, indent=1))
    (L.HERE / "hand_input.json").write_text(json.dumps(
        [dict(i=n, judge=s["judge"], **s["show"]) for n, s in enumerate(sample)], indent=1))
    print(len(sample), "judge items")


def audit_part(out, truth, rng):
    sample = []
    outs = sessions_out(out)
    au = L.read_jsonl(out / "audit.jsonl")
    blocks = {}
    for r in outs:
        blocks[(r["sid"], "consol_final")] = r["prep"]["consol_block"]
        if "ledger" in r:
            blocks[(r["sid"], "ledger_final")] = L.render_ledger(r["ledger"]["final"])
        for h in r["prep"]["consol_history"]:
            blocks[(r["sid"], f"consol_after_{h['after_turn']}")] = h["block"]
    cand = [(r, x) for r in au for x in r["rules"]]
    picked = rng.sample([c for c in cand if c[1]["state"] not in ("IN_FORCE_OLD", "IN_FORCE_NEW")], 12) + \
        rng.sample([c for c in cand if c[1]["state"] in ("IN_FORCE_OLD", "IN_FORCE_NEW")], 18)
    for r, x in picked:
        t = truth[r["sid"]]["truth"]
        item = next(i for i in t["active"] + t["revoked"] + t["amended"] if i["id"] == x["id"])
        sample.append(dict(judge="audit", key=[r["sid"], r["block"], x["id"]], model=x["state"],
                           show=dict(rule=item["rule"], change=item.get("amendment"),
                                     block=blocks[(r["sid"], r["block"])])))
    (L.HERE / "hand_audit_sample.json").write_text(json.dumps(sample, indent=1))
    (L.HERE / "hand_audit_input.json").write_text(json.dumps(
        [dict(i=n, judge=s["judge"], **s["show"]) for n, s in enumerate(sample)], indent=1))
    print(len(sample), "audit items")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    ap.add_argument("--part", choices=["judges", "classifier", "audit"], required=True)
    a = ap.parse_args()
    out = L.set_model(a.model)
    truth = {s["sid"]: s for s in json.loads((L.HERE / "data" / "sessions.json").read_text())}
    rng = random.Random(2323)
    {"classifier": classifier_part, "judges": judges_part, "audit": audit_part}[a.part](out, truth, rng)


if __name__ == "__main__":
    main()
