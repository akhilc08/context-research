"""Build E17 sessions with ground truth.

Each session is 100 to 200 turns of realistic filler (shared pool) plus 21 to 26 operator turns:
3 rules that stay active, 3 rules that are later revoked, 2 threshold rules that are later amended
(one loosened, one tightened), a goal chain from E2 (initial goal plus 1 to 3 redirects, with work
on the initial goal), 2 operator facts with 2 or 3 versions, one multi-step procedure from E8 with
k steps completed, and one chit-chat message. The last 15 turns are filler only.

Usage: python3 build.py [--n 60] [--seed 17]
Writes data/sessions.json.
"""
import argparse, json, random, re

import e17lib as L

DATA = L.HERE / "data"
E2 = L.OVERNIGHT / "e2_goal_resurrection" / "data"
E8 = L.OVERNIGHT / "e8_inflight" / "data"

CHANGE_CUE = re.compile(r"\b(drop|stop|abandon|discard|chang|switch|disregard|leave|instead)", re.I)
CHITCHAT = [
    "Thanks, that looks good so far.",
    "I will be in meetings for an hour; keep going.",
    "Nice work on that last fix.",
    "Quick note: I'm back online now if you need anything.",
]

# attribute, first-mention template, update template, value generator
FACTS = [
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


def build_session(i, rng, rules, revs, amends, scens, work, procs):
    n_total = rng.randrange(100, 201)
    E = n_total - 15
    events = []  # (target index, order key, kind, payload)

    def ev(t, kind, text, **meta):
        events.append(dict(t=int(t), kind=kind, text=text, **meta))

    # goals
    sc = scens[i % len(scens)]
    goals = sc["goals"]
    ev(0, "goal", goals[0]["message"], goal_index=0)
    red = sorted(rng.uniform(0.15 * E, 0.85 * E) for _ in range(len(goals) - 1))
    for gi, t in enumerate(red, 1):
        ev(t, "goal", goal_text(goals[gi], gi), goal_index=gi)
    first_red = red[0]
    for w in rng.sample(work[sc["id"]][0], min(4, len(work[sc["id"]][0]))):
        ev(rng.uniform(1, first_red - 1), "goal_work", w)

    # rules
    rev_pool = [r for r in revs if r["valid"]]
    chosen_rev = rng.sample(rev_pool, 3)
    rev_ids = {r["id"] for r in chosen_rev}
    act_ok = {r["id"] for r in revs if r["active_ok"]}
    chosen_act = rng.sample([r for r in rules if r["id"] not in rev_ids and r["id"] in act_ok], 3)
    loosen = rng.choice([a for a in amends if a["valid"] and a["direction"] == "loosen"])
    tighten = rng.choice([a for a in amends if a["valid"] and a["direction"] == "tighten"])
    for r in chosen_act:
        ev(rng.uniform(1, 0.4 * E), "rule", r["rule"], rule_id=r["id"])
    for r in chosen_rev:
        ev(rng.uniform(1, 0.4 * E), "rule", r["rule"], rule_id=r["id"])
        ev(rng.uniform(0.45 * E, 0.85 * E), "revoke", r["revocation"], rule_id=r["id"])
    for a in (loosen, tighten):
        ev(rng.uniform(1, 0.4 * E), "rule", a["rule"], rule_id=a["id"])
        ev(rng.uniform(0.45 * E, 0.85 * E), "amend", a["amendment"], rule_id=a["id"])

    # facts
    fact_defs = rng.sample(FACTS, 2)
    nvers = rng.sample([2, 3], 2)
    facts = []
    for (attr, gen), nv in zip(fact_defs, nvers):
        vals = []
        while len(vals) < nv:
            v = gen(rng)
            if v not in vals:
                vals.append(v)
        ts = [rng.uniform(1, 0.3 * E)]
        for _ in range(nv - 1):
            ts.append(rng.uniform(ts[-1] + 5, 0.85 * E))
        for j, (v, t) in enumerate(zip(vals, ts)):
            tmpl = rng.choice(FIRST if j == 0 else UPDATE)
            ev(t, "fact", tmpl.format(a=attr, v=v), attr=attr, version=j, value=v)
        facts.append(dict(attr=attr, values=vals))

    # plan
    p = procs[i % len(procs)]
    nsteps = len(p["steps"])
    k = rng.randrange(2, nsteps - 1)  # steps 1..k done, next is k+1 (1-based)
    tp = rng.uniform(0.3 * E, 0.45 * E)
    ev(tp, "plan", plan_text(p), proc_id=p["id"])
    sts = sorted(rng.uniform(tp + 1, 0.9 * E) for _ in range(k))
    for j, t in enumerate(sts):
        ev(t, "step", step_text(p["steps"][j]), step=j + 1)

    ev(rng.uniform(1, E), "chitchat", rng.choice(CHITCHAT))

    # place events in order; shift forward on collisions
    kind_order = {"rule": 0, "goal": 1, "fact": 2, "plan": 3, "revoke": 4, "amend": 5, "step": 6,
                  "goal_work": 7, "chitchat": 8}
    events.sort(key=lambda e: (e["t"], kind_order[e["kind"]]))
    pos = -1
    for e in events:
        pos = max(e["t"], pos + 1)
        e["pos"] = pos
    assert pos < n_total - 15, (pos, n_total)
    slots = {e["pos"]: e for e in events}
    filler = L.load_filler()
    fstart = rng.randrange(len(filler))
    turns, op_turns, fi = [], [], 0
    for t in range(n_total):
        if t in slots:
            e = slots[t]
            if e["kind"] in ("step", "goal_work"):
                turns.append(f"[Agent] {e['text']}")
            else:
                turns.append(f"[Operator] {e['text']}")
                op_turns.append(dict(turn=t + 1, kind=e["kind"], text=e["text"],
                                     **{k2: v for k2, v in e.items() if k2 not in ("t", "pos", "kind", "text")}))
        else:
            turns.append(f"[Agent] {filler[(fstart + fi) % len(filler)]}")
            fi += 1
    turn_of = lambda kind, **kw: next(o["turn"] for o in op_turns if o["kind"] == kind and
                                      all(o.get(a) == b for a, b in kw.items()))

    truth = dict(
        active=[dict(id=r["id"], rule=r["rule"], trigger=r["trigger"], turn=turn_of("rule", rule_id=r["id"]))
                for r in chosen_act],
        revoked=[dict(id=r["id"], rule=r["rule"], trigger=r["trigger"], revocation=r["revocation"],
                      turn=turn_of("rule", rule_id=r["id"]), revoked_turn=turn_of("revoke", rule_id=r["id"]))
                 for r in chosen_rev],
        amended=[dict(id=a["id"], rule=a["rule"], amendment=a["amendment"], probe=a["probe"],
                      direction=a["direction"], expected=a["new_decision"], turn=turn_of("rule", rule_id=a["id"]),
                      amended_turn=turn_of("amend", rule_id=a["id"])) for a in (loosen, tighten)],
        goals=[dict(task=g["task"], message=g["message"], turn=turn_of("goal", goal_index=gi))
               for gi, g in enumerate(goals)],
        facts=[dict(attr=f["attr"], values=f["values"],
                    turns=[turn_of("fact", attr=f["attr"], version=j) for j in range(len(f["values"]))])
               for f in facts],
        plan=dict(proc_id=p["id"], name=p["name"], goal=p["goal"], k=k, next=k + 1,
                  turn=turn_of("plan", proc_id=p["id"])),
    )
    return dict(sid=f"S{i:02d}", n_turns=n_total, turns=turns, operator_turns=op_turns, truth=truth,
                scenario=sc["id"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=17)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    rules = [r for r in L.load_rules() if r["valid"]]
    revs = json.loads((DATA / "revocations.json").read_text())
    amends = json.loads((DATA / "amendments.json").read_text())
    scens = json.loads((E2 / "scenarios.json").read_text())
    rng.shuffle(scens)
    work = json.loads((E2 / "goal_work.json").read_text())
    procs = json.loads((E8 / "procedures.json").read_text())
    rng.shuffle(procs)
    sessions = [build_session(i, rng, rules, revs, amends, scens, work, procs) for i in range(a.n)]
    (DATA / "sessions.json").write_text(json.dumps(sessions, indent=1))
    nops = [len(s["operator_turns"]) for s in sessions]
    print(f"{len(sessions)} sessions, turns {min(s['n_turns'] for s in sessions)} to "
          f"{max(s['n_turns'] for s in sessions)}, operator turns {min(nops)} to {max(nops)}")


if __name__ == "__main__":
    main()
