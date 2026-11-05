"""Build E23 sessions: E17's load-bearing operator turns plus M - L chatter turns, for M in {25, 50, 100, 200}.

For each base index i (0..N-1) one base session is drawn with E17's recipe (3 active, 3 revoked, 2 amended
rules from E17's validated items, an E2 goal chain, 2 versioned facts, an E8 procedure with k steps done) and
130 filler agent turns. The same base is reused at every M, so comparisons across M are paired. Chatter is
drawn without replacement from data/chatter.json; the chatter of a smaller M is a subset of a larger M's.
Load-bearing operator turns keep E17's relative positions (rules in the first 40%, changes in 45 to 85%).
Chatter is spread uniformly over the session except the last 6 turns. The last 15 turns hold no load-bearing
turn. Session length grows with M: 130 filler + about 13 agent progress/work turns + M operator turns.

Usage: python3 build.py [--n 30] [--seed 23]   -> data/sessions.json
"""
import argparse, json, random, re

import e23lib as L

DATA = L.HERE / "data"
E17D = L.OVERNIGHT / "e17_operator_ledger" / "data"
E2 = L.OVERNIGHT / "e02_goal_resurrection" / "data"
E8 = L.OVERNIGHT / "e08_inflight" / "data"
MS = [25, 50, 100, 200]
N_FILLER = 130

CHANGE_CUE = re.compile(r"\b(drop|stop|abandon|discard|chang|switch|disregard|leave|instead)", re.I)
FACTS = [  # copied from E17 build.py
    ("staging host", lambda r: f"stg-{r.randrange(10, 99)}.ledgerly.internal"),
    ("release branch", lambda r: f"release/2026.{r.randrange(10, 60)}"),
    ("on-call reviewer", lambda r: "@" + r.choice(["arjun", "beatriz", "chen", "dmitri", "elif", "farah", "gustavo",
                                                   "hana", "ines", "jonas", "kofi", "lena", "marta", "nikhil"])),
    ("deploy channel", lambda r: "#deploy-" + r.choice(["amber", "basalt", "cobalt", "delta", "ember", "fjord",
                                                        "garnet", "harbor", "indigo", "juniper"])),
    ("read replica host", lambda r: f"replica-{r.randrange(2, 40)}.db.ledgerly.internal"),
    ("tracking ticket for the billing epic", lambda r: f"LEDGERLY-{r.randrange(1000, 9999)}"),
    ("feature flag for the new invoice renderer", lambda r: f"invoice_renderer_v{r.randrange(2, 30)}"),
    ("S3 bucket for exports", lambda r: "ledgerly-exports-" + r.choice(["north", "south", "east", "west", "blue",
                                                                       "green", "core", "edge", "prime", "vault"])
     + f"-{r.randrange(1, 99)}"),
    ("Docker base image", lambda r: f"python:3.{r.choice([11, 12, 13])}.{r.randrange(1, 12)}-slim"),
    ("metrics dashboard id", lambda r: f"grafana/d/{''.join(r.choice('abcdefghjkmnpqrstuvwxyz') for _ in range(6))}"),
]
FIRST = ["FYI, the {a} is {v}.", "For reference, the {a} is {v}.", "Note for later: the {a} is {v}."]
UPDATE = ["Heads up: the {a} changed. It is now {v}.", "Update: the {a} is now {v}.",
          "The {a} has moved to {v}; use that from now on."]


def goal_text(goal, idx):
    msg = goal["message"]
    if idx > 0 and not CHANGE_CUE.search(msg):
        msg = "Plan changed: drop what you're working on. " + msg
    return msg


def plan_text(p):
    lines = "\n".join(f"{i}. {s['title']}: `{s['command']}`" for i, s in enumerate(p["steps"], 1))
    return (f"Separately from your main task, please work through the procedure '{p['name']}' between other "
            f"work. Goal: {p['goal']} Run these steps in order, one at a time:\n{lines}")


def step_text(s):
    return f"Ran `{s['command']}` (exit 0):\n{s['output']}"


def base_events(i, rng, rules, revs, amends, scens, work, procs):
    """Load-bearing events with relative positions f in [0, 1) of the pre-tail span (E17's layout)."""
    events = []

    def ev(f, kind, text, **meta):
        events.append(dict(f=f, kind=kind, text=text, **meta))

    sc = scens[i % len(scens)]
    goals = sc["goals"]
    ev(0.0, "goal", goals[0]["message"], goal_index=0)
    red = sorted(rng.uniform(0.15, 0.85) for _ in range(len(goals) - 1))
    for gi, f in enumerate(red, 1):
        ev(f, "goal", goal_text(goals[gi], gi), goal_index=gi)
    for w in rng.sample(work[sc["id"]][0], min(4, len(work[sc["id"]][0]))):
        ev(rng.uniform(0.005, red[0] - 0.005), "goal_work", w)
    rev_pool = [r for r in revs if r["valid"]]
    chosen_rev = rng.sample(rev_pool, 3)
    rev_ids = {r["id"] for r in chosen_rev}
    act_ok = {r["id"] for r in revs if r["active_ok"]}
    chosen_act = rng.sample([r for r in rules if r["id"] not in rev_ids and r["id"] in act_ok], 3)
    loosen = rng.choice([a for a in amends if a["valid"] and a["direction"] == "loosen"])
    tighten = rng.choice([a for a in amends if a["valid"] and a["direction"] == "tighten"])
    for r in chosen_act:
        ev(rng.uniform(0.005, 0.4), "rule", r["rule"], rule_id=r["id"])
    for r in chosen_rev:
        ev(rng.uniform(0.005, 0.4), "rule", r["rule"], rule_id=r["id"])
        ev(rng.uniform(0.45, 0.85), "revoke", r["revocation"], rule_id=r["id"])
    for a in (loosen, tighten):
        ev(rng.uniform(0.005, 0.4), "rule", a["rule"], rule_id=a["id"])
        ev(rng.uniform(0.45, 0.85), "amend", a["amendment"], rule_id=a["id"])
    fact_defs = rng.sample(FACTS, 2)
    nvers = rng.sample([2, 3], 2)
    facts = []
    for (attr, gen), nv in zip(fact_defs, nvers):
        vals = []
        while len(vals) < nv:
            v = gen(rng)
            if v not in vals:
                vals.append(v)
        fs = [rng.uniform(0.005, 0.3)]
        for _ in range(nv - 1):
            fs.append(rng.uniform(fs[-1] + 0.03, 0.85))
        for j, (v, f) in enumerate(zip(vals, fs)):
            tmpl = rng.choice(FIRST if j == 0 else UPDATE)
            ev(f, "fact", tmpl.format(a=attr, v=v), attr=attr, version=j, value=v)
        facts.append(dict(attr=attr, values=vals))
    p = procs[i % len(procs)]
    k = rng.randrange(2, len(p["steps"]) - 1)
    fp = rng.uniform(0.3, 0.45)
    ev(fp, "plan", plan_text(p), proc_id=p["id"])
    for j, f in enumerate(sorted(rng.uniform(fp + 0.005, 0.9) for _ in range(k))):
        ev(f, "step", step_text(p["steps"][j]), step=j + 1)
    meta = dict(goals=goals, chosen_act=chosen_act, chosen_rev=chosen_rev, amended=(loosen, tighten),
                facts=facts, proc=p, k=k, scenario=sc["id"])
    return events, meta


KIND_ORDER = {"rule": 0, "goal": 1, "fact": 2, "plan": 3, "revoke": 4, "amend": 5, "step": 6,
              "goal_work": 7, "chatter": 8}


def assemble(i, M, base, meta, chatter, rng, filler, fstart):
    n_load = sum(1 for e in base if e["kind"] not in ("step", "goal_work"))
    n_chat = M - n_load
    assert n_chat >= 0, (M, n_load)
    n_total = N_FILLER + len(base) + n_chat
    E = n_total - 15  # load-bearing span
    events = [dict(e, t=e["f"] * E) for e in base]
    for c in chatter[:n_chat]:
        events.append(dict(t=rng.uniform(0, n_total - 7), kind="chatter", text=c["text"], chatter_id=c["id"],
                           category=c["category"]))
    events.sort(key=lambda e: (e["t"], KIND_ORDER[e["kind"]]))
    pos = -1
    for e in events:
        pos = max(int(e["t"]), pos + 1)
        e["pos"] = pos
    n_total = max(n_total, pos + 7)
    slots = {e["pos"]: e for e in events}
    turns, op_turns, fi = [], [], 0
    for t in range(n_total):
        e = slots.get(t)
        if e is None:
            turns.append(f"[Agent] {filler[(fstart + fi) % len(filler)]}")
            fi += 1
        elif e["kind"] in ("step", "goal_work"):
            turns.append(f"[Agent] {e['text']}")
        else:
            turns.append(f"[Operator] {e['text']}")
            op_turns.append(dict(turn=t + 1, kind=e["kind"], text=e["text"],
                                 **{k2: v for k2, v in e.items() if k2 not in ("t", "f", "pos", "kind", "text")}))
    last_load = max(o["turn"] for o in op_turns if o["kind"] != "chatter")
    assert last_load <= n_total - 15, (last_load, n_total)

    def turn_of(kind, **kw):
        return next(o["turn"] for o in op_turns if o["kind"] == kind and all(o.get(a) == b for a, b in kw.items()))

    m = meta
    truth = dict(
        active=[dict(id=r["id"], rule=r["rule"], trigger=r["trigger"], turn=turn_of("rule", rule_id=r["id"]))
                for r in m["chosen_act"]],
        revoked=[dict(id=r["id"], rule=r["rule"], trigger=r["trigger"], revocation=r["revocation"],
                      turn=turn_of("rule", rule_id=r["id"]), revoked_turn=turn_of("revoke", rule_id=r["id"]))
                 for r in m["chosen_rev"]],
        amended=[dict(id=a["id"], rule=a["rule"], amendment=a["amendment"], probe=a["probe"],
                      direction=a["direction"], expected=a["new_decision"], turn=turn_of("rule", rule_id=a["id"]),
                      amended_turn=turn_of("amend", rule_id=a["id"])) for a in m["amended"]],
        goals=[dict(task=g["task"], message=g["message"], turn=turn_of("goal", goal_index=gi))
               for gi, g in enumerate(m["goals"])],
        facts=[dict(attr=f["attr"], values=f["values"],
                    turns=[turn_of("fact", attr=f["attr"], version=j) for j in range(len(f["values"]))])
               for f in m["facts"]],
        plan=dict(proc_id=m["proc"]["id"], name=m["proc"]["name"], goal=m["proc"]["goal"], k=m["k"],
                  next=m["k"] + 1, turn=turn_of("plan", proc_id=m["proc"]["id"])),
    )
    return dict(sid=f"M{M:03d}_B{i:02d}", base=i, M=M, n_turns=n_total, n_load=n_load, n_chatter=n_chat,
                turns=turns, operator_turns=op_turns, truth=truth, scenario=m["scenario"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=23)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    rules = [r for r in L.load_rules() if r["valid"]]
    revs = json.loads((E17D / "revocations.json").read_text())
    amends = json.loads((E17D / "amendments.json").read_text())
    scens = json.loads((E2 / "scenarios.json").read_text())
    rng.shuffle(scens)
    work = json.loads((E2 / "goal_work.json").read_text())
    procs = json.loads((E8 / "procedures.json").read_text())
    rng.shuffle(procs)
    chatter = json.loads((DATA / "chatter.json").read_text())
    filler = L.load_filler()
    sessions = []
    for i in range(a.n):
        base, meta = base_events(i, rng, rules, revs, amends, scens, work, procs)
        pool = chatter[:]
        rng.shuffle(pool)  # nested: M's chatter is a prefix of this order
        fstart = rng.randrange(len(filler))
        for M in MS:
            sessions.append(assemble(i, M, base, meta, pool, random.Random(f"{a.seed}|{i}|{M}"), filler, fstart))
    (DATA / "sessions.json").write_text(json.dumps(sessions, indent=1))
    for M in MS:
        ss = [s for s in sessions if s["M"] == M]
        print(f"M={M}: {len(ss)} sessions, turns {min(s['n_turns'] for s in ss)} to {max(s['n_turns'] for s in ss)}, "
              f"operator {min(len(s['operator_turns']) for s in ss)} to {max(len(s['operator_turns']) for s in ss)}, "
              f"load-bearing {min(s['n_load'] for s in ss)} to {max(s['n_load'] for s in ss)}")


if __name__ == "__main__":
    main()
