"""Generate procedure-RELATED filler turns for E13 (model calls, run once).

For each procedure (P00..P19) and each batch template, two generation calls produce a pool of turns
that belong to the same task: read-only diagnostics on the systems the procedure touches, log and
metric checks with warnings or partial failures, flaky checks retried, debugging notes, and operator
chatter about the task. The turns must not run any step command, must not say which step is done or
pending, and must not introduce new work, so that the build script controls all progress information.
For procedures, a third field gives a transient failure output (no side effects) for each step,
used to build failed-then-retried step attempts.

Usage: python3 gen_filler.py [--model MODEL]
Output: data/filler.json  {task_key: {"turns": [...], "failures": [...]}}
"""
import argparse, json, sys
from concurrent.futures import ThreadPoolExecutor

from tasks import DATA, BATCH_TEMPLATES, HERE
sys.path.insert(0, str(HERE.parent / "shared"))
from common import json_call  # noqa: E402

STYLE = """Turn formats (use these exactly):
- A command the agent ran: "Ran `<exact read-only command>` (exit <0 or 1>):\\n<1 to 5 lines of realistic output>"
- Operator chatter: "Operator: <message about this task>\\nAgent: <short reply>"
- An agent working note: "Note: <one or two sentences of debugging reasoning>"
"""

RULES = """Hard rules:
- Every turn belongs to THIS task: it inspects, monitors, or discusses the systems and data the task touches.
- NEVER run, re-run, or paste any of the task's own action commands listed above, and never perform any write action.
- NEVER say which step or item has been completed, is pending, is running, or comes next; never mention step numbers, counts of items processed, or progress percentages.
- NEVER mention specific item ids from a list (invent none).
- NEVER introduce new tasks, change the plan, or ask the agent to do something different.
- Make about a third of the turns show warnings, flaky results, partial failures in logs, or a read-only check that fails and is retried.
- Vary the commands and topics; no two turns alike. Output is realistic and concrete (hosts, metrics, timestamps, file paths)."""

PROC_PROMPT = """A coding agent is executing this ordered operational procedure for an operator:
Name: {name}
Goal: {goal}
Steps:
{steps}

Write {n} realistic transcript turns that would be interleaved with the procedure while it runs. Focus: {focus}
{style}
{rules}
{extra}Return JSON: {{"turns": [<{n} strings>]{failfield}}}"""

FOCUS = {
    "A": "read-only diagnostics, log tails, metric and health checks, config inspection, and checks that fail transiently and are re-run.",
    "B": "operator chatter about the task (timing, maintenance window, approvals, questions about risk), debugging notes, and short investigations of warnings seen in logs.",
}

BATCH_PROMPT = """A coding agent is working through a batch task for an operator: {name}. It runs `{cmd}` once per {unit}, for a list of {unit}s.
Write {n} realistic transcript turns that would be interleaved with the batch while it runs. Focus: {focus}
{style}
{rules}
Return JSON: {{"turns": [<{n} strings>]}}"""


def steps_text(p):
    return "\n".join(f"{i}. {s['title']}: `{s['command']}`" for i, s in enumerate(p["steps"], 1))


def gen_proc(job):
    p, part, model = job
    want_fail = part == "A"
    extra = ("Also, for EACH step above, write a realistic 1 to 3 line error output for a transient failure of that step's "
             "command that applied NO changes (timeouts, lock contention, network errors), so the step can simply be retried.\n"
             if want_fail else "")
    failfield = f', "failures": [<{len(p["steps"])} strings, one per step, in order>]' if want_fail else ""
    prompt = PROC_PROMPT.format(name=p["name"], goal=p["goal"], steps=steps_text(p), n=32, focus=FOCUS[part],
                                style=STYLE, rules=RULES, extra=extra, failfield=failfield)
    cmds = [s["command"] for s in p["steps"]]
    for _ in range(5):
        try:
            d = json_call(prompt, max_tokens=9000, temperature=0.8, tag="e13|gen|filler")
        except ValueError:
            continue
        turns = [t for t in d.get("turns", []) if isinstance(t, str) and t.strip() and not any(c in t for c in cmds)]
        if len(turns) < 24:
            continue
        if want_fail and len(d.get("failures", [])) != len(p["steps"]):
            continue
        return p["id"], part, turns, d.get("failures")
    raise RuntimeError(f"filler failed for {p['id']} {part}")


def gen_batch(job):
    t, part, model = job
    prompt = BATCH_PROMPT.format(name=t["name"], cmd=t["cmd"].replace("{id}", "<ID>"), unit=t["unit"], n=32,
                                 focus=FOCUS[part], style=STYLE, rules=RULES)
    for _ in range(5):
        try:
            d = json_call(prompt, max_tokens=9000, temperature=0.8, tag="e13|gen|filler")
        except ValueError:
            continue
        turns = [x for x in d.get("turns", []) if isinstance(x, str) and x.strip() and t["action_token"] not in x
                 and t["prefix"] not in x]
        if len(turns) >= 24:
            return t["key"], part, turns, None
    raise RuntimeError(f"filler failed for {t['key']} {part}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    a = ap.parse_args()
    procs = json.loads((DATA / "procedures.json").read_text())
    jobs_p = [(p, part, a.model) for p in procs for part in "AB"]
    jobs_b = [(t, part, a.model) for t in BATCH_TEMPLATES for part in "AB"]
    out = {}
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(gen_proc, jobs_p)) + list(ex.map(gen_batch, jobs_b))
    for key, part, turns, fails in res:
        e = out.setdefault(key, {"turns": [], "failures": None})
        e["turns"] += turns
        if fails:
            e["failures"] = fails
    (DATA / "filler.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(k, len(v["turns"]), "turns", "failures" if v["failures"] else "")


if __name__ == "__main__":
    main()
