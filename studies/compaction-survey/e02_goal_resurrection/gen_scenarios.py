"""Generate candidate goal-redirect chains for ledgerly with the model.

Writes data/scenarios_raw.json. Each scenario is a chain of 2 to 4 goals: an initial objective
and 1 to 3 redirects, each superseding the previous one with a clearly different concrete task.
"""
import json, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from common import json_call  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "scenarios_raw.json"

FILLER_THEMES = ("fixing a flaky invoice-sync integration test, API pagination, profiling a slow report job, "
                 "the invoice PDF renderer, ORM upgrade, structured logging, timezone scheduling bug, currency "
                 "rounding tests, a worker memory leak, CLI argument parsing, webhook retries, search index rebuild, "
                 "CSV export encoding, type hints, CI lint, test-suite fixtures")

PROMPT = """You are writing test scenarios for a study of coding agents. The agent works on "ledgerly", a Python billing service (invoices, payments, subscriptions, tax, refunds, dunning, customer accounts, ledgers, reporting, admin API).

Write {n} scenarios. In each scenario an operator gives the agent an initial objective, then later changes their mind {k} time(s). Each change supersedes the previous objective completely. So each scenario has exactly {g} goals in order.

Requirements for every goal:
- One clearly different, concrete engineering task in ledgerly, naming a specific feature, module, or bug. The {g} goals in a scenario must be in different areas of the codebase and must not overlap, so that an action toward one could never be mistaken for an action toward another.
- Avoid these topics entirely (they appear elsewhere in the transcripts): {avoid}.
- "task": a short canonical description (8 to 16 words).
- "message": the operator's message to the agent stating that objective, 15 to 40 words, natural and specific. For goal 1 it states the objective. For later goals it says the plan changed, that the agent should drop whatever it is currently doing, and states the new objective. A later message must NOT name or describe any earlier objective (say e.g. "drop what you're on" rather than naming it).
Use varied wording across scenarios. Avoid these already-used tasks: {used}.

Return JSON: {{"scenarios": [{{"goals": [{{"task": "...", "message": "..."}}, ...]}}, ...]}}"""


def gen(args):
    n, k, used = args
    d = json_call(PROMPT.format(n=n, k=k, g=k + 1, avoid=FILLER_THEMES, used=used or "none"),
                  max_tokens=5000, temperature=0.9, tag="e2_gen")
    out = []
    for s in d["scenarios"]:
        goals = s.get("goals", [])
        if len(goals) == k + 1 and all(g.get("task") and g.get("message") for g in goals):
            out.append({"goals": [{"task": g["task"].strip(), "message": g["message"].strip()} for g in goals]})
    return out


if __name__ == "__main__":
    # Batch 1 (ids s00 to s23) used these jobs; batch 2 (run again with --more) appends s24 onward.
    if "--more" in sys.argv:
        jobs = [(4, 1, "tax exemptions, dunning pause, account closure"), (4, 1, "proration, idempotent capture"),
                (4, 2, "refund approvals, credit notes"), (4, 2, "ledger immutability, revenue reports"),
                (4, 3, "tax jurisdiction, account merging"), (4, 3, "invoice numbering, vault tokens")]
    else:
        jobs = [(4, 1, ""), (4, 1, "invoice PDF, refunds"), (4, 2, ""), (4, 2, "tax, dunning"),
                (4, 3, ""), (4, 3, "subscriptions, webhooks")]
    with ThreadPoolExecutor(6) as ex:
        batches = list(ex.map(gen, jobs))
    scen = json.loads(OUT.read_text()) if "--more" in sys.argv else []
    start = len(scen)
    for b in batches:
        scen.extend(b)
    for i, s in enumerate(scen[start:], start):
        s["id"] = f"s{i:02d}"
    OUT.write_text(json.dumps(scen, indent=1))
    print(len(scen), [len(s["goals"]) for s in scen])
