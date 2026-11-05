"""Run E8: compact each case, build each method's context, ask the agent for its next command.

Methods (all see the same transcript; none sees truth labels):
  full        - whole transcript, no compaction (ceiling)
  plain       - recursive plain summary (common.SUMMARY_PROMPT), tail_k=2
  structured  - recursive TRACE-style markdown checkpoint (goal, done / in progress / next), tail_k=2
  ledger      - plain summary + harness ledger of executed commands and exit codes (no model call)
  ledger_only - ablation: ledger + tail, no summary
  watchpoint  - plain summary; extraction asks the agent which step it last completed; the
                harness compares with its own execution record and appends a progress note only if wrong
  note_always - ablation: plain summary + the harness progress note always appended (no comparator)

Usage: python3 run.py [--model MODEL] [--run RUNID] [--limit N] [--workers 8]
Raw outputs: data/<run>/compactions.jsonl, data/<run>/responses.jsonl, data/<run>/extractions.jsonl
"""
import argparse, json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from orclient import chat  # noqa: E402
from common import SUMMARY_PROMPT, AGENT_SYSTEM, render, context_block  # noqa: E402

TAIL_K, CHUNK, WORDS = 2, 6, 150

STRUCTURED_PROMPT = (
    "You are compacting the history of a long-running coding agent session so the agent can keep "
    "working with a smaller context. Write a structured markdown checkpoint in under {words} words with "
    "these sections: ## Goal, ## Constraints, ## Progress (### Done, ### In progress, ### Blocked), "
    "## Key decisions, ## Next steps, ## Critical context. Be specific about exactly which steps or items "
    "are done and which are not, so the agent can resume at the right place without repeating work."
)

METHODS = ["full", "plain", "structured", "ledger", "ledger_only", "watchpoint", "note_always"]
# Follow-up (added after seeing main results, exploratory): pin the operator's original request
# (the plan or item list) verbatim, as many harnesses keep the first user message.
FOLLOWUP = ["pin_plain", "pin_ledger", "pin_note"]

ASK = ("[New message from the operator]\nContinue with the operator's requested task. What exact command do you run next?\n\n"
       "Reply in exactly this format, nothing else:\nCOMMAND: <the single exact shell command you will run next>\n"
       "REASON: <one sentence>")

_lock = threading.Lock()


def compact(model, tag, instruction, prior, turns):
    head = instruction.format(words=WORDS)
    pre = f"[Summary of earlier turns]\n{prior}\n\n" if prior else ""
    return chat([{"role": "user", "content": f"{head}\n\n{pre}[Log]\n{render(turns)}"}],
                max_tokens=WORDS * 4, temperature=0.3, model=model, tag=tag).strip()


def recursive(model, tag, instruction, turns):
    """Recursive compaction: chunks of CHUNK turns; each round sees prior summary + old tail + chunk."""
    chunks = [turns[i:i + CHUNK] for i in range(0, len(turns), CHUNK)]
    summary, tail, rounds = "", [], 0
    for ch in chunks:
        seq = tail + ch
        body, tail = seq[:-TAIL_K], seq[-TAIL_K:]
        if body:
            summary = compact(model, tag, instruction, summary, body)
            rounds += 1
    return summary, tail, rounds


def ledger_text(ledger):
    lines = []
    for i, e in enumerate(ledger, 1):
        ex = "running, no exit code observed yet" if e["exit"] is None else f"exit {e['exit']}"
        lines.append(f"{i}. `{e['cmd']}` -> {ex}")
    return "[Harness execution ledger: every command executed this session, in order]\n" + "\n".join(lines)


def harness_progress(case, procs):
    """What the harness itself knows from its execution record: the task commands that returned exit 0
    and the one in flight. Derived from the ledger by matching against the operator's plan."""
    p = procs[case["proc_id"]]
    cmds = [s["command"] for s in p["steps"]]
    done = [cmds.index(e["cmd"]) + 1 for e in case["ledger"] if e["cmd"] in cmds and e["exit"] == 0]
    infl = [cmds.index(e["cmd"]) + 1 for e in case["ledger"] if e["cmd"] in cmds and e["exit"] is None]
    return (max(done) if done else 0), (infl[0] if infl else None)


def progress_note(case, procs):
    p = procs[case["proc_id"]]
    last, infl = harness_progress(case, procs)
    n = len(p["steps"])
    if p["family"] == "batch":
        s = (f"[Harness progress watchpoint] Last completed item: {p['item_ids'][last - 1]} "
             f"(item {last} of {n}). Items {last + 1} to {n} have not been completed")
    else:
        s = (f"[Harness progress watchpoint] Last completed step: step {last} of {n} "
             f"(`{p['steps'][last - 1]['command']}`). Steps {last + 1} to {n} have not been completed")
    if infl:
        s += f"; the command for {'item' if p['family'] == 'batch' else 'step'} {infl} was issued but its result has not been observed"
    return s + "."


def extraction(model, run, context, case, procs):
    p = procs[case["proc_id"]]
    if p["family"] == "batch":
        q = (f"Before continuing: which {p['unit']} did you last finish processing successfully? "
             f"Reply with only its id, or NONE.")
    else:
        q = "Before continuing: which step number of the procedure did you last complete successfully? Reply with only the integer (0 if none)."
    raw = chat([{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": f"{context}\n\n[Harness question]\n{q}"}],
               max_tokens=400, temperature=0.0, model=model, tag=f"e8|{run}|extract")
    if p["family"] == "batch":
        ids = [i for i in p["item_ids"] if i in raw]
        val = p["item_ids"].index(ids[0]) + 1 if ids else 0
    else:
        m = re.search(r"\d+", raw)
        val = int(m.group(0)) if m else -1
    return val, raw


def load_done(path, key):
    if not path.exists():
        return {}
    out = {}
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
    ap.add_argument("--limit", type=int, default=0, help="only the first N cases (smoke/second-backbone runs)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--methods", default=",".join(METHODS), help="comma list; follow-up: " + ",".join(FOLLOWUP))
    ap.add_argument("--stride", type=int, default=1, help="take every Nth case")
    a = ap.parse_args()
    if ":free" in a.model:
        sys.exit("':free' models are reserved for the coordinator")
    out = HERE / "data" / a.run
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(vars(a) | dict(TAIL_K=TAIL_K, CHUNK=CHUNK, WORDS=WORDS)))
    cases = json.loads((HERE / "data" / "cases.json").read_text())[::a.stride]
    if a.limit:
        cases = cases[:a.limit]
    procs = {p["id"]: p | {"family": "proc"} for p in json.loads((HERE / "data" / "procedures.json").read_text())}
    procs.update({p["id"]: p for p in json.loads((HERE / "data" / "batches.json").read_text())})

    cpath, rpath, epath = out / "compactions.jsonl", out / "responses.jsonl", out / "extractions.jsonl"
    comp = load_done(cpath, lambda r: (r["case_id"], r["kind"]))
    resp = load_done(rpath, lambda r: (r["case_id"], r["method"]))
    extr = load_done(epath, lambda r: r["case_id"])

    def do_compact(job):
        case, kind = job
        if (case["case_id"], kind) in comp:
            return
        instr = SUMMARY_PROMPT if kind == "plain" else STRUCTURED_PROMPT
        s, tail, rounds = recursive(a.model, f"e8|{a.run}|compact_{kind}", instr, case["turns"])
        rec = dict(case_id=case["case_id"], kind=kind, summary=s, tail=tail, rounds=rounds)
        comp[(case["case_id"], kind)] = rec
        append(cpath, rec)

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(do_compact, [(c, k) for c in cases for k in ["plain", "structured"]]))
    print("compactions done", flush=True)

    def do_extract(case):
        if case["case_id"] in extr:
            return
        pc = comp[(case["case_id"], "plain")]
        ctx = context_block(pc["summary"], pc["tail"])
        val, raw = extraction(a.model, a.run, ctx, case, procs)
        hl, _ = harness_progress(case, procs)
        rec = dict(case_id=case["case_id"], extracted=val, raw=raw, harness_last=hl, patched=val != hl)
        extr[case["case_id"]] = rec
        append(epath, rec)

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(do_extract, cases))
    print("extractions done", flush=True)

    def context_for(case, method):
        pc, sc = comp[(case["case_id"], "plain")], comp[(case["case_id"], "structured")]
        tail = pc["tail"]
        if method == "full":
            return "[Session so far, verbatim]\n" + render(case["turns"])
        if method == "plain":
            return context_block(pc["summary"], tail)
        if method == "structured":
            return context_block(sc["summary"], sc["tail"])
        if method == "ledger":
            return context_block(pc["summary"], tail, ledger_text(case["ledger"]))
        if method == "ledger_only":
            return context_block("", tail, ledger_text(case["ledger"]))
        if method == "watchpoint":
            note = progress_note(case, procs) if extr[case["case_id"]]["patched"] else ""
            return context_block(pc["summary"], tail, note)
        if method == "note_always":
            return context_block(pc["summary"], tail, progress_note(case, procs))
        if method.startswith("pin_"):
            pin = "[Original operator request, kept verbatim by the harness]\n" + case["turns"][0]
            extra = {"pin_plain": "", "pin_ledger": ledger_text(case["ledger"]),
                     "pin_note": progress_note(case, procs)}[method]
            return context_block(pc["summary"], tail, pin + ("\n\n" + extra if extra else ""))
        raise ValueError(method)

    def do_agent(job):
        case, method = job
        if (case["case_id"], method) in resp:
            return
        ctx = context_for(case, method)
        raw = chat([{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": f"{ctx}\n\n{ASK}"}],
                   max_tokens=800, temperature=0.7, model=a.model, tag=f"e8|{a.run}|agent_{method}")
        m = re.search(r"COMMAND:\s*(.+)", raw)
        cmd = m.group(1).strip().strip("`") if m else raw.strip().splitlines()[0]
        append(rpath, dict(case_id=case["case_id"], method=method, command=cmd, raw=raw, context_chars=len(ctx)))

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(do_agent, [(c, m) for c in cases for m in a.methods.split(",")]))
    print("agent done", flush=True)


if __name__ == "__main__":
    main()
