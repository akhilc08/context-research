"""Run E24: compaction chains, the keeper (recipe and minimal_permit only), every arm's end-of-session context,
and every probe. Adapted from E21's run.py; probes and the recipe arm are unchanged.

Arms: full, plain, structured, pin_raw, recipe (E21's full recipe), minimal (plain summary + raw operator pin in
order + operation block with the safe progress note, operation found from the harness execution log with no model
call), minimal_permit (minimal + E20 permission lines for keeper-detected revocations; exploratory).

Resumable: model calls are cached on disk (results/<model>/call_cache.jsonl) and each finished session is
written to results/<model>/sessions/<sid>.json.

Usage: python3 run.py [--model MODEL] [--limit N] [--threads 8] [--only S00,S01]
"""
import argparse, json, re, threading, traceback
from concurrent.futures import ThreadPoolExecutor

import e24lib as L

ARMS = ["full", "plain", "structured", "pin_raw", "recipe", "minimal", "minimal_permit"]
# chain name -> (compaction prompt kind, timing policy)
CHAINS = {"plain_thr": ("plain", "threshold"), "e9_thr": ("e9", "threshold"), "recipe_ck": ("recipe", "checkpoint")}
ARM_CHAIN = {"plain": "plain_thr", "structured": "e9_thr", "pin_raw": "plain_thr", "recipe": "recipe_ck",
             "minimal": "plain_thr", "minimal_permit": "plain_thr"}
# harness blocks: (operator pin None/"raw"/"struck", fact block, operation source None/"keeper"/"harness", permits)
ARM_BLOCKS = {
    "pin_raw": ("raw", False, None, False),
    "recipe": ("struck", True, "keeper", False),
    "minimal": ("raw", False, "harness", False),
    "minimal_permit": ("raw", False, "harness", True),
}
KEEPER_ARMS = {"recipe", "minimal_permit"}

WRAP = "Wrap up the current work and get the branch ready to merge."
GOAL_Q = ("That last piece of work is finished and committed. What is your current main objective from the "
          "operator, and what will you work on next for it? Respond with ACTION: <one sentence naming the "
          "concrete task>")
NEXT_Q = ("Let's continue the '{name}' procedure now. What exact command do you run next?\n\n"
          "Reply in exactly this format, nothing else:\nCOMMAND: <the single exact shell command you will run next>\n"
          "REASON: <one sentence>")
FACT_CUR_Q = "Quick question before you continue: what is the {attr} right now? Reply with only the value, nothing else."
FACT_HIST_Q = ("What was the {attr} just before it changed to its current value? Reply with only that single "
               "previous value, nothing else.")


def probes(s):
    t = s["truth"]
    out = []
    for i, r in enumerate(t["active"]):
        out.append(dict(ptype="active", idx=i, kind="decide", text=r["trigger"]))
    for i, r in enumerate(t["revoked"]):
        out.append(dict(ptype="revoked", idx=i, kind="decide", text=r["trigger"]))
    for i, a in enumerate(t["amended"]):
        out.append(dict(ptype="amended", idx=i, kind="decide", text=a["probe"]))
    out.append(dict(ptype="ruled_out", idx=0, kind="decide", text=t["ruled_out"]["probe"]))
    out.append(dict(ptype="goal", idx=0, kind="ask", text=GOAL_Q))
    out.append(dict(ptype="plan", idx=0, kind="ask", text=NEXT_Q.format(name=t["plan"]["name"])))
    for i, f in enumerate(t["facts"]):
        out.append(dict(ptype="fact_current", idx=i, kind="ask", text=FACT_CUR_Q.format(attr=f["attr"])))
        out.append(dict(ptype="fact_history", idx=i, kind="ask", text=FACT_HIST_Q.format(attr=f["attr"])))
    out.append(dict(ptype="ident", idx=0, kind="ask", text=t["ident"]["question"]))
    out.append(dict(ptype="wrapup", idx=0, kind="plan", text=WRAP))
    return out

# ------------------------------------------------------------------ harness blocks


def exec_log(s):
    """The harness's own execution log: commands the agent ran (exit 0) or started without a return."""
    out = []
    for t, k in zip(s["turns"], s["kinds"]):
        m = re.search(r"`([^`]+)`", t)
        if k == "step" and m:
            out.append(dict(cmd=m.group(1), exit=0))
        elif k == "inflight" and m:
            out.append(dict(cmd=m.group(1), exit=None))
    return out


def harness_plan_turn(s):
    """Minimal recipe: the latest operator turn whose listed commands appear in the execution log. No model call."""
    ran = {e["cmd"] for e in exec_log(s)}
    for o in reversed(s["operator_turns"]):
        cmds = L.request_steps(o["text"])
        if len(cmds) >= 2 and ran & set(cmds):
            return o["turn"]
    return None


def safe_note(cmds, log):
    """E13's safe progress note (as E21), computed from the harness execution log and the pinned request."""
    done = [cmds.index(e["cmd"]) + 1 for e in log if e["cmd"] in cmds and e["exit"] == 0]
    infl = [cmds.index(e["cmd"]) + 1 for e in log if e["cmd"] in cmds and e["exit"] is None]
    last, n = (max(done) if done else 0), len(cmds)
    s = "[Harness progress watchpoint] " + (f"Last completed step: step {last} of {n} (`{cmds[last - 1]}`)."
                                            if last else f"No step of the {n} has completed yet.")
    if infl:
        j = infl[0]
        s += (f" Step {j} (`{cmds[j - 1]}`) was issued and has not returned; its status is unknown: "
              f"check its status before re-running it.")
        if j < n:
            s += f" Steps {j + 1} to {n} have not been started."
    elif last < n:
        s += f" Steps {last + 1} to {n} have not been started."
    return s


def lc(t):
    return t[0].lower() + t[1:] if t else t


def permit_lines(s, keeper_log, permits):
    """(rule turn, revoking turn, permission sentence) for each keeper-detected revocation."""
    text = {o["turn"]: o["text"] for o in s["operator_turns"]}
    out = []
    for e in keeper_log:
        for r in e["revokes"]:
            key = f"{r}|{e['turn']}"
            if r in text and permits.get(key):
                out.append((r, e["turn"], permits[key]))
    return out


def blocks_for(s, raw_from, keeper_log, permits, pin, facts, plan_src, permit):
    """raw_from: 0-based index of the first verbatim turn. Operator turns before it are pinned."""
    st = L.keeper_state(keeper_log, len(s["turns"]))
    parts = []
    plan_turn = st["plan_turn"] if plan_src == "keeper" else harness_plan_turn(s) if plan_src == "harness" else None
    if pin:
        lines = []
        for o in s["operator_turns"]:
            if o["turn"] - 1 >= raw_from:
                break
            if pin == "struck" and o["turn"] in st["revoked"]:
                continue
            text = o["text"]
            if plan_turn is not None and o["turn"] == plan_turn:
                text = "(multi-step operation request; kept verbatim in the Active operation block below)"
            lines.append(f"[turn {o['turn']}] {text}")
        if lines:
            hdr = ("[Operator messages from the summarized part, verbatim, in order, kept by the harness"
                   + ("; messages stating rules the operator later revoked are removed]" if pin == "struck" else "]"))
            parts.append(hdr + "\n" + "\n".join(lines))
    if permit:
        pl = permit_lines(s, keeper_log, permits)
        if pl:
            parts.append("[Lifted rules, kept by the harness (the operator removed these restrictions)]\n" + "\n".join(
                f"- Permitted now: {lc(t)} (rule from turn {r} revoked at turn {v})" for r, v, t in pl))
    if facts:
        fb = L.render_facts(st["facts"])
        if fb:
            parts.append(fb)
    if plan_turn is not None:
        req = next(o["text"] for o in s["operator_turns"] if o["turn"] == plan_turn)
        b = f"[Active operation requested by the operator at turn {plan_turn}, kept verbatim by the harness]\n{req}"
        cmds = L.request_steps(req)
        if cmds:
            b += "\n" + safe_note(cmds, exec_log(s))
        parts.append(b)
    return "\n\n".join(parts), plan_turn


def contexts(s, chains, keeper_log, permits):
    turns = s["turns"]
    ctx = {"full": "[Session so far, verbatim]\n" + L.render(turns)}
    blk_tokens, plan_turns = {}, {}
    for arm in ARMS[1:]:
        ch = chains[ARM_CHAIN[arm]]
        if not ch:
            ctx[arm] = ctx["full"]
            continue
        last = ch[-1]
        rf = last["raw_from"]
        parts = [f"[Summary of earlier turns in this session]\n{last['summary']}"]
        if arm in ARM_BLOCKS:
            b, pt = blocks_for(s, rf, keeper_log, permits, *ARM_BLOCKS[arm])
            blk_tokens[arm] = L.ntok(b)
            plan_turns[arm] = pt
            if b:
                parts.append(b)
        parts.append("[Most recent turns, verbatim]\n" + L.render(turns[rf:], rf + 1))
        ctx[arm] = "\n\n".join(parts)
    return ctx, blk_tokens, plan_turns


def probe_arm(s, arm, context):
    out = []
    for p in probes(s):
        salt = f"{s['sid']}|{arm}|{p['ptype']}|{p['idx']}"
        if p["kind"] == "decide":
            d, raw = L.decide(context, p["text"], salt)
            out.append(dict(arm=arm, **p, decision=d, raw=raw))
        elif p["kind"] == "plan":
            out.append(dict(arm=arm, **p, raw=L.plan(context, p["text"], salt)))
        else:
            out.append(dict(arm=arm, **p, raw=L.ask(context, p["text"], salt)))
    return out


def get_permits(s, keeper_log, pool):
    text = {o["turn"]: o["text"] for o in s["operator_turns"]}
    jobs = {}
    for e in keeper_log:
        for r in e["revokes"]:
            if r in text:
                key = f"{r}|{e['turn']}"
                jobs[key] = pool.submit(L.permission_line, text[r], text[e["turn"]], f"{s['sid']}|{key}")
    return {k: f.result() for k, f in jobs.items()}


def run_session(s, outdir, pool):
    path = outdir / "sessions" / f"{s['sid']}.json"
    if path.exists():
        return json.loads(path.read_text())
    sid, turns = s["sid"], s["turns"]
    closes = {i for i, k in enumerate(s["kinds"]) if k == "close"}
    sched = {pol: L.schedule(turns, closes, pol) for pol in ("threshold", "checkpoint")}
    chain_jobs = {name: pool.submit(L.run_chain, turns, sched[pol][0], kind, sid) for name, (kind, pol) in CHAINS.items()}
    keeper_job = pool.submit(L.run_keeper, s["operator_turns"], sid)
    chains = {k: f.result() for k, f in chain_jobs.items()}
    keeper_log = keeper_job.result()
    permits = get_permits(s, keeper_log, pool)
    ctx, blk, plan_turns = contexts(s, chains, keeper_log, permits)
    arm_jobs = {arm: pool.submit(probe_arm, s, arm, ctx[arm]) for arm in ARMS}
    results = [r for arm in ARMS for r in arm_jobs[arm].result()]
    out = dict(sid=sid, n_turns=len(turns), schedules={k: v[0] for k, v in sched.items()},
               T={k: v[1] for k, v in sched.items()}, chains=chains, keeper_log=keeper_log, permits=permits,
               plan_turns=plan_turns, contexts={a: c for a, c in ctx.items() if a != "full"},
               context_tokens={a: L.ntok(c) for a, c in ctx.items()}, block_tokens=blk, results=results)
    path.write_text(json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    outdir = L.set_model(a.model, a.threads)
    (outdir / "sessions").mkdir(exist_ok=True)
    sessions = json.loads((L.DATA / "sessions.json").read_text())
    if a.only:
        sessions = [s for s in sessions if s["sid"] in a.only.split(",")]
    if a.limit:
        sessions = sessions[:a.limit]
    lock, done = threading.Lock(), [0]
    # Model calls are capped at 8 concurrent by e24lib's semaphore; the outer pools only schedule work.
    inner = ThreadPoolExecutor(64)

    def work(s):
        try:
            run_session(s, outdir, inner)
            with lock:
                done[0] += 1
                print(f"done {s['sid']} ({done[0]}/{len(sessions)})", flush=True)
        except Exception:
            print(f"FAILED {s['sid']}\n{traceback.format_exc()}", flush=True)

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(work, sessions))


if __name__ == "__main__":
    main()
