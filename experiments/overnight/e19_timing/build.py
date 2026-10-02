"""E19: build long multi-subtask sessions (seeded, no model calls).

Each session is about 170 to 230 turns made of six subtasks:
  C1  coding work from the shared realistic filler pool, closed by a passing test run and a DONE marker
  O1  an ordered multi-step operation (an E8/E13 procedure) with related E13 filler between steps
  C2  coding work
  O2  operation
  C3  coding work
  O3  operation still in progress when the session ends (the final probe point)
Operator turns are planted: the session goal (turn 1), a standing rule in C1, a second rule in O1 or C2,
a ruled-out approach in C2, an identifier correction in C2 or O2 (the stale value appears in C1), a goal
redirect in C3, three harmless chatter turns, and each operation's request (which lists every step command).

Fixed probe points (shared by every policy): mid-O1 and mid-O2 (step k done, then 2 to 4 related turns),
and the last turn (mid-O3). Writes data/sessions.json.
Usage: python3 build.py [--n 24]
"""
import argparse, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVN = HERE.parent
sys.path.insert(0, str(OVN))
sys.path.insert(0, str(OVN / "e9_cheap_validation"))
from common import sample_filler, load_rules  # noqa: E402
from items import GOALS, FACTS, APPROACHES  # noqa: E402

PROCS = json.loads((OVN / "e13_plan_pinning" / "data" / "procedures.json").read_text())
RELATED = json.loads((OVN / "e13_plan_pinning" / "data" / "filler.json").read_text())
RULES = [r for r in load_rules() if r.get("valid")]
CHATTER = ["Operator: thanks, that looks right, keep going.",
           "Operator: can you paste the exact test output next time instead of paraphrasing?",
           "Operator: I'm stepping into a meeting for an hour, carry on with what you were doing.",
           "Operator: nice catch on that one.",
           "Operator: please keep commits small so review stays easy."]
CLOSES = ["Ran `pytest -q` (exit 0): {n} passed in {s:.1f}s. DONE: subtask {i} closed; committed as `{sha}`.",
          "Ran `make check` (exit 0): lint clean, {n} tests passed. DONE: subtask {i} is complete and committed (`{sha}`).",
          "Ran `pytest -q && ruff check .` (exit 0): {n} passed, no lint errors. DONE: marked subtask {i} done (`{sha}`)."]
OPERATOR_KINDS = {"goal", "rule0", "rule1", "approach", "fact_fix", "redirect", "chatter", "op_request"}


def op_request(p):
    lines = "\n".join(f"{i}. {s['title']}: `{s['command']}`" for i, s in enumerate(p["steps"], 1))
    return (f"Operator: side request, separate from the session goal: run the procedure '{p['name']}'. Purpose: "
            f"{p['goal']} Run these steps in order, one at a time:\n{lines}")


def related_turns(pid, n, rng):
    pool = [t for t in RELATED[pid]["turns"] if not t.startswith("Operator")]
    start = rng.randrange(len(pool))
    return [pool[(start + i) % len(pool)] for i in range(n)]


def coding_subtask(turns, idx, rng):
    out = [(t, "filler") for t in turns]
    out.append((rng.choice(CLOSES).format(n=rng.randint(150, 420), s=rng.uniform(20, 90), i=idx,
                                          sha=f"{rng.getrandbits(28):07x}"), "close"))
    return out


def op_subtask(p, rng, stop_after=None):
    """Turns of one operation. Returns (turns, probe_offset, k). If stop_after is set, the operation is
    cut after step stop_after plus 2 to 4 related turns (end of session)."""
    steps = p["steps"]
    n_fill = 3 * len(steps) + 6
    fill = related_turns(p["id"], n_fill, rng)
    fi = 0
    out = [(op_request(p), "op_request")]
    for _ in range(2):
        out.append((fill[fi], "ofill")); fi += 1
    k_probe = stop_after if stop_after else rng.randint(2, len(steps) - 2)
    probe_off = None
    for j, s in enumerate(steps, 1):
        out.append((f"Ran `{s['command']}` (exit 0):\n{s['output']}", f"step{j}"))
        gap = rng.randint(2, 4) if j == k_probe else rng.randint(1, 3)
        for _ in range(gap):
            out.append((fill[fi % len(fill)], "ofill")); fi += 1
        if j == k_probe:
            probe_off = len(out) - 1
            if stop_after:
                return out, probe_off, k_probe
    out.append((f"Agent: all {len(steps)} steps of '{p['name']}' finished with exit 0. DONE: operation closed.", "close"))
    return out, probe_off, k_probe


def insert(seq, item, rng, lo=0.05, hi=0.9):
    """Insert (text, kind) at a random position inside a subtask, never after its close turn."""
    n = len(seq) - (1 if seq and seq[-1][1] == "close" else 0)
    pos = int(rng.uniform(lo, hi) * n)
    seq.insert(max(1 if seq and seq[0][1] == "op_request" else 0, pos), item)


def build(sid):
    rng = random.Random(19000 + sid)
    g, f, a = rng.randrange(len(GOALS)), rng.randrange(len(FACTS)), rng.randrange(len(APPROACHES))
    r0, r1 = rng.sample(range(len(RULES)), 2)
    procs = rng.sample(range(len(PROCS)), 3)
    lens = [rng.randint(24, 32) for _ in range(3)]
    pool = sample_filler(sum(lens), rng)
    cs = [coding_subtask(pool[sum(lens[:i]):sum(lens[:i + 1])], i * 2 + 1, rng) for i in range(3)]
    o1, off1, k1 = op_subtask(PROCS[procs[0]], rng)
    o2, off2, k2 = op_subtask(PROCS[procs[1]], rng)
    p3 = PROCS[procs[2]]
    k3 = rng.randint(2, len(p3["steps"]) - 2)
    o3, off3, _ = op_subtask(p3, rng, stop_after=k3)
    G, F = GOALS[g], FACTS[f]
    cs[0].insert(0, ("Operator: " + G[0], "goal"))
    insert(cs[0], (F[0], "fact_stale"), rng, 0.1, 0.5)
    insert(cs[0], ("Operator: " + RULES[r0]["rule"], "rule0"), rng, 0.3, 0.9)
    # rule1 in O1 (after the probe point, so mid-O1 tests only rule0) or in C2
    if rng.random() < 0.5:
        o1.insert(off1 + 1 + rng.randint(0, max(0, len(o1) - off1 - 3)), ("Operator: " + RULES[r1]["rule"], "rule1"))
    else:
        insert(cs[1], ("Operator: " + RULES[r1]["rule"], "rule1"), rng, 0.05, 0.5)
    insert(cs[1], ("Operator: " + APPROACHES[a][0], "approach"), rng, 0.4, 0.9)
    if rng.random() < 0.5:
        insert(cs[1], ("Operator: " + F[1], "fact_fix"), rng, 0.6, 0.95)
    else:
        insert(cs[2], ("Operator: " + F[1], "fact_fix"), rng, 0.05, 0.4)
    insert(cs[2], ("Operator: " + G[1], "redirect"), rng, 0.3, 0.9)
    for c in rng.sample(CHATTER, 3):
        insert(cs[rng.randrange(3)], (c, "chatter"), rng)
    order = [("C1", cs[0]), ("O1", o1), ("C2", cs[1]), ("O2", o2), ("C3", cs[2]), ("O3", o3)]
    turns, kinds, sub = [], [], []
    starts = {}
    for name, seq in order:
        starts[name] = len(turns)
        for t, k in seq:
            turns.append(t); kinds.append(k); sub.append(name)
    # probe points: recompute by locating step k turns (robust to insertions)
    def probe_at(name, k):
        i = next(j for j in range(len(turns)) if sub[j] == name and kinds[j] == f"step{k}")
        j = i + 1
        while j < len(turns) and sub[j] == name and kinds[j] == "ofill":
            j += 1
        return j - 1
    probes = [dict(name="mid_O1", turn=probe_at("O1", k1), op="O1", proc=PROCS[procs[0]]["id"], k=k1),
              dict(name="mid_O2", turn=probe_at("O2", k2), op="O2", proc=PROCS[procs[1]]["id"], k=k2),
              dict(name="end_O3", turn=len(turns) - 1, op="O3", proc=p3["id"], k=k3)]
    return dict(sid=sid, goal=g, fact=f, approach=a, rule_idx=[r0, r1], rules=[RULES[r0]["id"], RULES[r1]["id"]],
                procs=[PROCS[i]["id"] for i in procs], turns=turns, kinds=kinds, sub=sub, starts=starts,
                probes=probes, chars=sum(map(len, turns)))


def state_at(s, t):
    """What the operator has established by turn t (inclusive): which items exist, which goal is current."""
    seen = set(s["kinds"][:t + 1])
    return dict(rule0="rule0" in seen, rule1="rule1" in seen, approach="approach" in seen,
                fact="fact_fix" in seen, goal_new="redirect" in seen)


def op_in_progress(s, t):
    """(op name, proc id, k completed) if an operation is in progress at turn t, else None."""
    name = s["sub"][t]
    if not name.startswith("O") or s["kinds"][t] == "close":
        return None
    seg = [j for j in range(s["starts"][name], t + 1)]
    k = max([int(s["kinds"][j][4:]) for j in seg if s["kinds"][j].startswith("step")] or [0])
    if s["kinds"][t] == "op_request":
        return None  # the request itself is the last turn; nothing run yet is still a valid "next = step 1"
    return dict(op=name, proc=s["procs"][int(name[1]) - 1], k=k)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    args = ap.parse_args()
    sessions = [build(i) for i in range(args.n)]
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "sessions.json").write_text(json.dumps(sessions, indent=1))
    import statistics as st
    print("turns", min(len(s["turns"]) for s in sessions), st.mean(len(s["turns"]) for s in sessions),
          max(len(s["turns"]) for s in sessions))
    print("approx tokens", st.mean(s["chars"] / 4 for s in sessions))
    for s in sessions[:3]:
        print(s["sid"], len(s["turns"]), s["starts"], [(p["name"], p["turn"], p["k"]) for p in s["probes"]])
