"""Run E13: compact each case at two summary budgets, build each arm's context, ask for the next command.

Arms (none sees truth labels; harness-derived notes use only the harness's execution ledger and the plan):
  full        - whole transcript verbatim (ceiling; budget-independent)
  plain       - recursive plain summary (common.SUMMARY_PROMPT) + verbatim tail
  structured  - recursive TRACE-style markdown checkpoint + verbatim tail
  pin         - original operator request verbatim + plain
  pin_ledger  - pin + harness ledger of every command and its exit code (in flight: "running, no exit code yet")
  pin_safe    - pin + safe progress note: in-flight command stated as "status unknown: check before re-running"
  pin_marker  - pin + harness in-flight marker only (nothing when no command is in flight)
  pin_unsafe  - control: pin + E8's progress note wording ("steps k+1 to N have not been completed; the command
                for step k+1 was issued but its result has not been observed")
Every compacted arm runs at budgets 150 and 400 words (method id "<arm>@<budget>"). Two samples per case at T=0.7.

Usage: python3 run.py [--model MODEL] [--run main] [--stride N] [--limit N] [--workers 8] [--samples 2]
Raw outputs: data/<run>/compactions.jsonl, data/<run>/responses.jsonl
"""
import argparse, json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor

from tasks import DATA, HERE, load_procs
sys.path.insert(0, str(HERE.parent))
from orclient import chat  # noqa: E402
from common import SUMMARY_PROMPT, AGENT_SYSTEM, render, context_block  # noqa: E402

TAIL_K, CHUNK = 3, 30
BUDGETS = [150, 400]
ARMS = ["plain", "structured", "pin", "pin_ledger", "pin_safe", "pin_marker", "pin_unsafe"]
METHODS = ["full"] + [f"{a}@{b}" for b in BUDGETS for a in ARMS]

STRUCTURED_PROMPT = (
    "You are compacting the history of a long-running coding agent session so the agent can keep "
    "working with a smaller context. Write a structured markdown checkpoint in under {words} words with "
    "these sections: ## Goal, ## Constraints, ## Progress (### Done, ### In progress, ### Blocked), "
    "## Key decisions, ## Next steps, ## Critical context. Be specific about exactly which steps or items "
    "are done and which are not, so the agent can resume at the right place without repeating work."
)

ASK = ("[New message from the operator]\nContinue with the operator's requested task. What exact command do you run next?\n\n"
       "Reply in exactly this format, nothing else:\nCOMMAND: <the single exact shell command you will run next>\n"
       "REASON: <one sentence>")

_lock = threading.Lock()


def compact(model, tag, instruction, words, prior, turns):
    head = instruction.format(words=words)
    pre = f"[Summary of earlier turns]\n{prior}\n\n" if prior else ""
    return chat([{"role": "user", "content": f"{head}\n\n{pre}[Log]\n{render(turns)}"}],
                max_tokens=words * 3 + 600, temperature=0.3, model=model, tag=tag).strip()


def recursive(model, tag, instruction, words, turns):
    """Compaction fires every CHUNK turns; each round sees the prior summary, the old tail, and the new chunk."""
    chunks = [turns[i:i + CHUNK] for i in range(0, len(turns), CHUNK)]
    summary, tail, rounds = "", [], 0
    for ch in chunks:
        seq = tail + ch
        body, tail = seq[:-TAIL_K], seq[-TAIL_K:]
        if body:
            summary = compact(model, tag, instruction, words, summary, body)
            rounds += 1
    return summary, tail, rounds


def ledger_text(ledger):
    lines = []
    for i, e in enumerate(ledger, 1):
        ex = "running, no exit code observed yet" if e["exit"] is None else f"exit {e['exit']}"
        lines.append(f"{i}. `{e['cmd']}` -> {ex}")
    return "[Harness execution ledger: every command executed this session, in order]\n" + "\n".join(lines)


def harness_progress(case, p):
    """From the harness's own ledger: highest plan step that returned exit 0, and the plan step in flight."""
    cmds = [s["command"] for s in p["steps"]]
    done = [cmds.index(e["cmd"]) + 1 for e in case["ledger"] if e["cmd"] in cmds and e["exit"] == 0]
    infl = [cmds.index(e["cmd"]) + 1 for e in case["ledger"] if e["cmd"] in cmds and e["exit"] is None]
    return (max(done) if done else 0), (infl[0] if infl else None)


def _names(p):
    return ("item", "items") if p["family"] == "batch" else ("step", "steps")


def _last(p, last):
    n = len(p["steps"])
    if p["family"] == "batch":
        return f"Last completed item: {p['item_ids'][last - 1]} (item {last} of {n})"
    return f"Last completed step: step {last} of {n} (`{p['steps'][last - 1]['command']}`)"


def unsafe_note(case, p):
    """E8's note_always wording, kept as the control."""
    last, infl = harness_progress(case, p)
    one, many = _names(p)
    n = len(p["steps"])
    s = f"[Harness progress watchpoint] {_last(p, last)}. {many.capitalize()} {last + 1} to {n} have not been completed"
    if infl:
        s += f"; the command for {one} {infl} was issued but its result has not been observed"
    return s + "."


def safe_note(case, p):
    """Same facts, but the in-flight command is reported as status unknown, to be checked before any re-run."""
    last, infl = harness_progress(case, p)
    one, many = _names(p)
    n = len(p["steps"])
    s = f"[Harness progress watchpoint] {_last(p, last)}."
    if infl:
        cmd = p["steps"][infl - 1]["command"]
        s += (f" {one.capitalize()} {infl} (`{cmd}`) was issued and has not returned; its status is unknown: "
              f"check its status before re-running it.")
        if infl < n:
            s += f" {many.capitalize()} {infl + 1} to {n} have not been started."
    elif last < n:
        s += f" {many.capitalize()} {last + 1} to {n} have not been started."
    return s


def inflight_marker(case, p):
    infl = [e["cmd"] for e in case["ledger"] if e["exit"] is None]
    return "\n".join(f"[Harness] Command `{c}` was issued and has not returned; do not re-run it without checking its status."
                     for c in infl)


def context_for(case, method, comp, p):
    if method == "full":
        return "[Session so far, verbatim]\n" + render(case["turns"])
    arm, b = method.split("@")
    pc, sc = comp[(case["case_id"], f"plain@{b}")], comp[(case["case_id"], f"structured@{b}")]
    if arm == "plain":
        return context_block(pc["summary"], pc["tail"])
    if arm == "structured":
        return context_block(sc["summary"], sc["tail"])
    pin = "[Original operator request, kept verbatim by the harness]\n" + case["turns"][0]
    extra = {"pin": "", "pin_ledger": ledger_text(case["ledger"]), "pin_safe": safe_note(case, p),
             "pin_marker": inflight_marker(case, p), "pin_unsafe": unsafe_note(case, p)}[arm]
    return context_block(pc["summary"], pc["tail"], pin + ("\n\n" + extra if extra else ""))


def load(path, key):
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            out[key(r)] = r
    return out


def append(path, rec):
    with _lock, open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    ap.add_argument("--run", default="main")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stride", type=int, default=1, help="take every Nth case")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--methods", default=",".join(METHODS))
    a = ap.parse_args()
    if ":free" in a.model:
        sys.exit("':free' models are not allowed in this study")
    a.workers = min(a.workers, 8)
    out = DATA / a.run
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(vars(a) | dict(TAIL_K=TAIL_K, CHUNK=CHUNK, BUDGETS=BUDGETS)))
    cases = json.loads((DATA / "cases.json").read_text())[::a.stride]
    if a.limit:
        cases = cases[:a.limit]
    procs = load_procs()
    methods = a.methods.split(",")
    tag = lambda s: f"e13|{a.run}|{s}"

    cpath, rpath = out / "compactions.jsonl", out / "responses.jsonl"
    comp = load(cpath, lambda r: (r["case_id"], r["kind"]))
    resp = load(rpath, lambda r: (r["case_id"], r["method"], r["sample"]))

    def safe(fn):
        def w(job):
            try:
                fn(job)
            except Exception as e:  # provider outage: skip now, retried on the next pass
                print("job failed:", repr(e)[:120], flush=True)
        return w

    @safe
    def do_compact(job):
        case, kind = job
        if (case["case_id"], kind) in comp:
            return
        arm, b = kind.split("@")
        instr = SUMMARY_PROMPT if arm == "plain" else STRUCTURED_PROMPT
        s, tail, rounds = recursive(a.model, tag(f"compact_{kind}"), instr, int(b), case["turns"])
        rec = dict(case_id=case["case_id"], kind=kind, summary=s, tail=tail, rounds=rounds, words=len(s.split()))
        comp[(case["case_id"], kind)] = rec
        append(cpath, rec)

    kinds = [f"{x}@{b}" for b in BUDGETS for x in ("plain", "structured")]
    for _ in range(6):
        with ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(do_compact, [(c, k) for c in cases for k in kinds]))
        if all((c["case_id"], k) in comp for c in cases for k in kinds):
            break
    print("compactions done", flush=True)

    @safe
    def do_agent(job):
        case, method, s = job
        if (case["case_id"], method, s) in resp:
            return
        p = procs[case["proc_id"]]
        ctx = context_for(case, method, comp, p)
        raw = chat([{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": f"{ctx}\n\n{ASK}"}],
                   max_tokens=800, temperature=0.7, model=a.model, tag=tag(f"agent_{method}"))
        m = re.search(r"COMMAND:\s*(.+)", raw)
        cmd = m.group(1).strip().strip("`") if m else raw.strip().splitlines()[0]
        rm = re.search(r"REASON:\s*(.+)", raw)
        append(rpath, dict(case_id=case["case_id"], method=method, sample=s, command=cmd,
                           reason=rm.group(1).strip() if rm else "", raw=raw, context_chars=len(ctx)))

    jobs = [(c, m, s) for s in range(a.samples) for c in cases for m in methods]
    for _ in range(6):
        jobs = [j for j in jobs if all((j[0]["case_id"], k) in comp for k in kinds)]
        with ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(do_agent, jobs))
        resp = load(rpath, lambda r: (r["case_id"], r["method"], r["sample"]))
        if all((c["case_id"], m, s) in resp for c, m, s in jobs):
            break
    print("agent done", len(jobs), flush=True)


if __name__ == "__main__":
    main()
