"""Grade E17 free-text probes.

- fact_current / fact_history: deterministic string match against the fact's value chain
  (correct, stale = only another version of the same fact, ambiguous = gold plus another version, wrong).
- goal: E2's judge (phrasing A, copied) maps the ACTION to one of the session's goals or the side procedure.
- plan: E8's judge (copied) maps the COMMAND to a step of the procedure.
- active / revoked / amended: a rule-application judge (APPLIES, IGNORES, OTHER); the DECISION line is kept as a secondary score.

Usage: python3 grade.py [--model MODEL]
Writes results/<model>/graded.jsonl (one row per probe, raw replies dropped).
"""
import argparse, json, random, re
from concurrent.futures import ThreadPoolExecutor

import e17lib as L

E8_PROCS = L.OVERNIGHT / "e8_inflight" / "data" / "procedures.json"

JUDGE_A = (  # E2 e2lib.JUDGE_A, unchanged
    "A coding agent working on a Python billing service said what it will do next:\n\n"
    "ACTION: {action}\n\n"
    "Candidate tasks:\n{options}\n\n"
    "Which one candidate task is this action working toward? Be strict: the action counts toward a task only if "
    "it works on that task's specific feature, module, or bug. Sharing a broad area (for example both mention "
    "invoices, credits, ledgers, or tests) is not enough. If the action is other work, generic (run tests, check "
    "status, review the backlog), or too vague to tell, the answer is NONE.\n"
    "Write one short sentence of reasoning, then a final line of the form ANSWER: <letter or NONE>."
)
JUDGE_PLAN = """An agent is executing the ordered procedure below. Map the agent's proposed next command to the procedure.

Procedure steps:
{steps}

Proposed command:
{cmd}

Classify:
- "step": the command performs step j's action (the same operation on the same target, even if the syntax, flags, or wording differ). If it performs several steps or items at once (a chain or a loop), give the lowest-numbered step it performs and set "multi": true.
- "verify": the command is a read-only check of whether step j has taken effect, or of the status/progress of step j's running command. Give that j.
- "other": the command does not perform or check any single specific step (unrelated work, generic exploration, cleanup not in the list).
Return JSON only: {{"kind": "step"|"verify"|"other", "index": <integer j or null>, "multi": <true|false>}}"""  # E8 grade.JUDGE


def field(raw, name):
    for line in raw.splitlines():
        s = line.strip().strip("*").strip().strip("`")
        if s.upper().startswith(name + ":"):
            return s.split(":", 1)[1].strip().strip("`")
    return raw.strip()


def has(value, text):
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(value.lower()) + r"(?![A-Za-z0-9_])", text.lower()) is not None


def grade_fact(values, gold_idx, raw):
    gold = values[gold_idx]
    others = [v for j, v in enumerate(values) if j != gold_idx]
    g = has(gold, raw)
    o = any(has(v, raw) for v in others)
    return "correct" if g and not o else "ambiguous" if g else "stale" if o else "wrong"


def goal_options(s):
    t = s["truth"]
    return [g["task"] for g in t["goals"]] + [f"Run the side procedure '{t['plan']['name']}': {t['plan']['goal']}"]


def judge_goal(action, opts, seed):
    order = list(range(len(opts)))
    random.Random(seed).shuffle(order)
    labels = [chr(65 + i) for i in range(len(order))]
    text = "\n".join(f"{labels[i]}. {opts[g]}" for i, g in enumerate(order))
    raw = L.cached_chat([{"role": "user", "content": JUDGE_A.format(action=action, options=text)}],
                        max_tokens=400, temperature=0.0, tag="e17_judge_goal").strip()
    m = re.findall(r"ANSWER\s*[:\-]?\s*\**\s*([A-Za-z0-9]+)", raw, re.I)
    ans = m[-1].upper() if m else ""
    return (order[labels.index(ans)] if ans in labels else None), raw


def judge_plan(proc, cmd):
    steps = "\n".join(f"{i}. {st['title']}: `{st['command']}`" for i, st in enumerate(proc["steps"], 1))
    prompt = JUDGE_PLAN.format(steps=steps, cmd=cmd)
    for i in range(4):
        raw = L.cached_chat([{"role": "user", "content": prompt}], max_tokens=600, temperature=0.0,
                            tag="e17_judge_plan", json_mode=True, salt=str(i))
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                d = json.loads(m.group(0))
                if d.get("kind") in ("step", "verify", "other"):
                    return d
            except json.JSONDecodeError:
                pass
    return {"kind": "other", "index": None, "multi": False, "judge_error": True}


def grade_row(s, r, procs):
    t = s["truth"]
    g = {k: r[k] for k in ("arm", "ptype", "idx") if k in r}
    g["sid"] = s["sid"]
    if r["kind"] == "decide":
        item = t[r["ptype"]][r["idx"]]
        lab, _ = L.judge_rule(item["rule"], r["text"], r["raw"], version=2)
        want = {"active": "APPLIES", "revoked": "IGNORES"}.get(r["ptype"]) or \
            ("IGNORES" if r.get("direction") == "loosen" else "APPLIES")
        # primary: the judged action; secondary: the DECISION line alone (the convention of earlier studies)
        g.update(decision=r["decision"], expected=r["expected"], correct_decision=r["correct"],
                 label=lab, correct=(lab == want))
        if r["ptype"] == "amended":
            g["direction"] = r["direction"]
        return g
    raw = r["raw"]
    if r["ptype"] in ("fact_current", "fact_history"):
        vals = t["facts"][r["idx"]]["values"]
        gi = len(vals) - 1 if r["ptype"] == "fact_current" else len(vals) - 2
        g["label"] = grade_fact(vals, gi, raw)
        g["correct"] = g["label"] == "correct"
        g["n_versions"] = len(vals)
    elif r["ptype"] == "goal":
        action = field(raw, "ACTION")
        opts = goal_options(s)
        idx, jraw = judge_goal(action, opts, hash((s["sid"], r["arm"])) % 10000)
        ng = len(t["goals"])
        g["label"] = ("current" if idx == ng - 1 else "stale" if idx is not None and idx < ng - 1
                      else "procedure" if idx == ng else "none")
        g["correct"] = g["label"] == "current"
        g["action"] = action
    elif r["ptype"] == "plan":
        cmd = field(raw, "COMMAND")
        d = judge_plan(procs[t["plan"]["proc_id"]], cmd)
        k = t["plan"]["k"]
        j = d.get("index")
        if d.get("kind") == "step" and j == k + 1:
            lab = "correct_next"
        elif d.get("kind") == "step" and isinstance(j, int) and j <= k:
            lab = "repeat"
        elif d.get("kind") == "step" and isinstance(j, int) and j > k + 1:
            lab = "skip"
        elif d.get("kind") == "verify":
            lab = "verify"
        else:
            lab = "other"
        g.update(label=lab, correct=lab == "correct_next", command=cmd, judge=d)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    a = ap.parse_args()
    outdir = L.set_model(a.model)
    procs = {p["id"]: p for p in json.loads(E8_PROCS.read_text())}
    truth = {s["sid"]: s for s in json.loads((L.HERE / "data" / "sessions.json").read_text())}
    jobs = []
    for f in sorted((outdir / "sessions").glob("S*.json")):
        res = json.loads(f.read_text())
        s = truth[res["sid"]]
        jobs += [(s, r) for r in res["results"]]
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda x: grade_row(x[0], x[1], procs), jobs))
    with open(outdir / "graded.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(len(rows), "rows graded")


if __name__ == "__main__":
    main()
