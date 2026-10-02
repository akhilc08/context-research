"""Grade E8 responses: map each proposed command to a step of its procedure.

The LLM judge sees only the step list and the proposed command (never k, timing, or method).
For batch tasks a deterministic parser (item id + action token) is also run as a cross-check.

Usage: python3 grade.py [--run main] [--model MODEL]
Output: data/<run>/judged.jsonl
"""
import argparse, json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from orclient import chat  # noqa: E402

JUDGE = """An agent is executing the ordered procedure below. Map the agent's proposed next command to the procedure.

Procedure steps:
{steps}

Proposed command:
{cmd}

Classify:
- "step": the command performs step j's action (the same operation on the same target, even if the syntax, flags, or wording differ). If it performs several steps or items at once (a chain or a loop), give the lowest-numbered step it performs and set "multi": true.
- "verify": the command is a read-only check of whether step j has taken effect, or of the status/progress of step j's running command. Give that j.
- "other": the command does not perform or check any single specific step (unrelated work, generic exploration, cleanup not in the list).
Return JSON only: {{"kind": "step"|"verify"|"other", "index": <integer j or null>, "multi": <true|false>}}"""

ACTION_TOKENS = {"charge overdue invoices": "charge --invoice", "send plan-renewal notices": "send --template",
                 "refund duplicate charges": "refunds create", "migrate tenant schemas to v14": "--to-version",
                 "re-encrypt document shards with the new KMS key": "reencrypt", "issue loyalty credits": "credit --account"}

_lock = threading.Lock()


def steps_text(p):
    return "\n".join(f"{i}. {s['title']}: `{s['command']}`" for i, s in enumerate(p["steps"], 1))


def judge(model, p, cmd):
    prompt = JUDGE.format(steps=steps_text(p), cmd=cmd)
    for _ in range(4):
        raw = chat([{"role": "user", "content": prompt}], max_tokens=600, temperature=0.0, model=model,
                   tag="e8|judge", json_mode=True)
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                d = json.loads(m.group(0))
                if d.get("kind") in ("step", "verify", "other"):
                    return d
            except json.JSONDecodeError:
                pass
    return {"kind": "other", "index": None, "multi": False, "judge_error": True}


def batch_parse(p, cmd):
    hits = sorted(p["item_ids"].index(i) + 1 for i in p["item_ids"] if re.search(re.escape(i) + r"(?![0-9])", cmd))
    if not hits:
        return {"kind": "other", "index": None, "multi": False}
    kind = "step" if ACTION_TOKENS[p["name"]] in cmd else "verify"
    return {"kind": kind, "index": hits[0], "multi": len(hits) > 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    a = ap.parse_args()
    out = HERE / "data" / a.run
    procs = {p["id"]: p for p in json.loads((HERE / "data" / "procedures.json").read_text())}
    procs.update({p["id"]: p for p in json.loads((HERE / "data" / "batches.json").read_text())})
    jpath = out / "judged.jsonl"
    done = set()
    if jpath.exists():
        done = {(r["case_id"], r["method"]) for r in map(json.loads, jpath.read_text().splitlines())}
    resps = [json.loads(l) for l in (out / "responses.jsonl").read_text().splitlines()]

    def work(r):
        if (r["case_id"], r["method"]) in done:
            return
        p = procs[r["case_id"].split("-")[0]]
        rec = dict(case_id=r["case_id"], method=r["method"], command=r["command"], judge=judge(a.model, p, r["command"]))
        if p.get("family") == "batch":
            rec["parse"] = batch_parse(p, r["command"])
        with _lock, open(jpath, "a") as f:
            f.write(json.dumps(rec) + "\n")

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(work, resps))
    print("judged", len(resps))


if __name__ == "__main__":
    main()
