"""Grade E13 responses: map each proposed command to a step of its task.

Procedure cases: an LLM judge (temperature 0) that sees only the step list (each step's action command and
read-only verify command), the agent's command and its one-sentence reason. It never sees k, the timing,
the arm, or the truth. Changes from E8's judge, aimed at E8's undercount of correct answers:
  - the judge sees each step's verify command, so status checks are recognised;
  - the judge sees the agent's stated reason, used only to resolve which step an ambiguous command targets;
  - explicit rules that paraphrases (different flags, a generic form of the same operation, a wrapper script)
    still count as the step, and that a check on a running process or job of step j counts as verify j.
Batch cases: a deterministic id parser only (ids in the list, the template's action and verify tokens).

Usage: python3 grade.py [--run main] [--model MODEL]
Output: data/<run>/judged.jsonl with {case_id, method, sample, label: {kind, index, multi, invented}}
"""
import argparse, json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor

from tasks import DATA, HERE, TEMPLATES, load_procs
sys.path.insert(0, str(HERE.parent))
from orclient import chat  # noqa: E402

JUDGE = """An agent is executing the ordered procedure below. Decide which step, if any, the agent's proposed next command belongs to.

Procedure steps (action command, then a read-only command that checks whether the step took effect):
{steps}

Agent's proposed command:
{cmd}

Agent's stated reason:
{reason}

Classify the command:
- "step": it performs step j's action: the same operation on the same target. Different flags, ordering, quoting, a generic form of the same operation (for example running the same test suite more broadly, or the same tool call with slightly different options), or a wrapper around it still counts as step j. If it performs several steps at once (a chain or loop), give the lowest-numbered step it performs and set "multi": true.
- "verify": it only reads state to check whether step j took effect, or checks the status, progress, logs, or process of step j's command (for example ps or pgrep for its process, its job status, a query of the rows or objects step j changes). It need not match the listed verify command. Give that j.
- "other": it neither performs nor checks one specific step: unrelated or general diagnostics (health checks, log scans, metrics) not tied to one step's effect, cleanup not in the list, or a placeholder command.
Use the reason only to decide WHICH step an ambiguous command targets; classify by what the command actually does (a read-only command is never "step").
Return JSON only: {{"kind": "step"|"verify"|"other", "index": <integer j or null>, "multi": <true|false>}}"""

READONLY = re.compile(r"\b(show|list|history|status|lookup|info|ledger|get|describe|grep|cat|tail|log|logs|ps|pgrep|jobs|wait)\b")

PROC_CHECK = {"ps", "pgrep", "pidof", "grep", "egrep", "rg", "jobs", "wait", "tail", "cat", "less", "lsof", "journalctl"}

_lock = threading.Lock()


def steps_text(p):
    return "\n".join(f"{i}. {s['title']}\n   action: `{s['command']}`\n   check:  `{s['verify_command']}`"
                     for i, s in enumerate(p["steps"], 1))


def judge(model, p, cmd, reason):
    prompt = JUDGE.format(steps=steps_text(p), cmd=cmd, reason=reason or "(none given)")
    for _ in range(4):
        raw = chat([{"role": "user", "content": prompt}], max_tokens=600, temperature=0.0, model=model,
                   tag="e13|judge", json_mode=True)
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                d = json.loads(m.group(0))
                if d.get("kind") in ("step", "verify", "other"):
                    if d["kind"] == "other":
                        d["index"] = None
                    return d
            except json.JSONDecodeError:
                pass
    return {"kind": "other", "index": None, "multi": False, "judge_error": True}


def batch_parse(p, cmd):
    """Deterministic: which listed ids appear, and is the command the action, a check, or neither.
    invented = the action is invoked on no listed id (a made-up id or a placeholder)."""
    t = TEMPLATES[p["template"]]
    lead = next((x for x in re.split(r"[\s;|&(]+", cmd.strip()) if x and x not in ("sudo", "env", "time", "set", "-e", "-euo", "pipefail")), "")
    lead = lead.split("/")[-1]
    hits = sorted(p["item_ids"].index(i) + 1 for i in p["item_ids"] if re.search(re.escape(i) + r"(?![0-9])", cmd))
    # A process or log check (ps, pgrep, grep ...) quotes the action command but does not run it.
    proc_check = lead in PROC_CHECK
    act = t["action_token"] in cmd and not proc_check
    ver = proc_check or t["verify_token"] in cmd or bool(READONLY.search(cmd))
    if not hits:
        return {"kind": "other", "index": None, "multi": False, "invented": act}
    kind = "step" if act else ("verify" if ver else "other")
    return {"kind": kind, "index": hits[0] if kind != "other" else None, "multi": len(hits) > 1, "invented": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    ap.add_argument("--reparse", action="store_true", help="recompute batch parser labels in place (no model calls)")
    a = ap.parse_args()
    out = DATA / a.run
    procs = load_procs()
    jpath = out / "judged.jsonl"
    if a.reparse:
        rows = [json.loads(l) for l in jpath.read_text().splitlines()]
        for r in rows:
            p = procs[r["case_id"].split("-")[0]]
            if p["family"] == "batch":
                r["label"] = batch_parse(p, r["command"])
        jpath.write_text("".join(json.dumps(r) + "\n" for r in rows))
        print("reparsed", sum(r["source"] == "parser" for r in rows))
        return
    done = set()
    if jpath.exists():
        done = {(r["case_id"], r["method"], r["sample"]) for r in map(json.loads, jpath.read_text().splitlines())}
    resps = [json.loads(l) for l in (out / "responses.jsonl").read_text().splitlines()]

    def work(r):
        key = (r["case_id"], r["method"], r["sample"])
        if key in done:
            return
        p = procs[r["case_id"].split("-")[0]]
        if p["family"] == "batch":
            label, src = batch_parse(p, r["command"]), "parser"
        else:
            label, src = judge(a.model, p, r["command"], r.get("reason", "")), "judge"
        with _lock, open(jpath, "a") as f:
            f.write(json.dumps(dict(case_id=r["case_id"], method=r["method"], sample=r["sample"], command=r["command"],
                                    label=label, source=src)) + "\n")

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(work, resps))
    print("judged", len(resps))


if __name__ == "__main__":
    main()
