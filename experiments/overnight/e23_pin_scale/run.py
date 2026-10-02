"""Run E23: plain compaction, directive classification, periodic consolidation, E17's ledger, and probes.

Resumable: every model call is cached in results/<model>/call_cache.jsonl, and each session's results are
written to results/<model>/sessions/<sid>.json. Arms missing from an existing file are added on rerun.

Usage: python3 run.py [--model MODEL] [--arms a,b] [--M 25,50] [--limit-base N] [--threads 8]
"""
import argparse, json, threading, traceback
from concurrent.futures import ThreadPoolExecutor

import e23lib as L

ARMS = ["full", "plain", "pin_raw", "pin_directive", "pin_consol", "ledger"]
K_CONSOL = 10  # consolidate the pinned block after every 10 operator turns

GOAL_Q = ("That last piece of work is finished and committed. What is your current main objective from the "
          "operator, and what will you work on next for it? Respond with ACTION: <one sentence naming the "
          "concrete task>")
PLAN_Q = ("Let's pick the '{name}' procedure back up now. What exact command do you run next?\n\n"
          "Reply in exactly this format, nothing else:\nCOMMAND: <the single exact shell command you will run next>\n"
          "REASON: <one sentence>")
FACT_CUR_Q = "Quick question before you continue: what is the {attr} right now? Reply with only the value, nothing else."
FACT_HIST_Q = ("What was the {attr} just before it changed to its current value? Reply with only that single "
               "previous value, nothing else.")
CONSOL_HEAD = ("[Operator block. The harness keeps it from the operator's own messages. It is current and "
               "authoritative: where the summary or older turns disagree, follow it.]")


def probes(s):  # E17's probe set, unchanged
    t = s["truth"]
    out = []
    for i, r in enumerate(t["active"]):
        out.append(dict(ptype="active", idx=i, kind="decide", text=r["trigger"], expected="REFUSE"))
    for i, r in enumerate(t["revoked"]):
        out.append(dict(ptype="revoked", idx=i, kind="decide", text=r["trigger"], expected="COMPLY"))
    for i, a in enumerate(t["amended"]):
        out.append(dict(ptype="amended", idx=i, kind="decide", text=a["probe"], expected=a["expected"],
                        direction=a["direction"]))
    out.append(dict(ptype="goal", idx=0, kind="ask", text=GOAL_Q))
    out.append(dict(ptype="plan", idx=0, kind="ask", text=PLAN_Q.format(name=t["plan"]["name"])))
    for i, f in enumerate(t["facts"]):
        out.append(dict(ptype="fact_current", idx=i, kind="ask", text=FACT_CUR_Q.format(attr=f["attr"])))
        out.append(dict(ptype="fact_history", idx=i, kind="ask", text=FACT_HIST_Q.format(attr=f["attr"])))
    return out


def classify(s):
    out = []
    for o in s["operator_turns"]:
        d, raw = L.classify_directive(o["text"])
        out.append(dict(turn=o["turn"], directive=d, truth=o["kind"] != "chatter", raw=raw))
    return out


def consolidation(s):
    """Every K operator turns the block is rewritten. Returns (final rendered block, history, cost)."""
    block, buf, hist, cost = "", [], [], dict(calls=0, in_tok=0, out_tok=0)
    for o in s["operator_turns"]:
        buf.append(o)
        if len(buf) == K_CONSOL:
            new = L.consolidate(block, buf, s["sid"])
            msgs = "\n".join(f"[turn {b['turn']}] {b['text']}" for b in buf)
            cost["calls"] += 1
            cost["in_tok"] += L.ntok(L.CONSOLIDATE_PROMPT) + L.ntok(block) + L.ntok(msgs)
            cost["out_tok"] += L.ntok(new)
            block, buf = new, []
            hist.append(dict(after_turn=o["turn"], block=block, tokens=L.ntok(block)))
    rendered = CONSOL_HEAD + "\n" + (block or "(empty)")
    if buf:
        rendered += "\n\n[Operator messages since the last update of this block, verbatim]\n" + \
            "\n".join(f"[turn {b['turn']}] {b['text']}" for b in buf)
    return rendered, hist, cost


def ledger_run(s):
    led = json.loads(json.dumps(L.EMPTY_LEDGER))
    steps, errors, cost, snaps = [], 0, dict(calls=0, in_tok=0, out_tok=0), []
    load_turns = {o["turn"] for o in s["operator_turns"] if o["kind"] in ("revoke", "amend")}
    for o in s["operator_turns"]:
        before = json.dumps(led, indent=1)
        led, err = L.ledger_update(led, o["turn"], o["text"], s["sid"])
        errors += err
        cost["calls"] += 1
        cost["in_tok"] += L.ntok(L.LEDGER_PROMPT) + L.ntok(before) + L.ntok(o["text"])
        cost["out_tok"] += L.ntok(json.dumps(led, indent=1))
        steps.append(dict(turn=o["turn"], kind=o["kind"], failed=err, tokens=L.ntok(L.render_ledger(led))))
        if o["turn"] in load_turns:
            snaps.append(dict(after_turn=o["turn"], ledger=led))
    return led, steps, errors, cost, snaps


def blocks_for(s, prep, led=None):
    ops = s["operator_turns"]
    keep = {c["turn"] for c in prep["classify"] if c["directive"]}
    b = {"pin_raw": L.raw_block(ops),
         "pin_directive": L.raw_block([o for o in ops if o["turn"] in keep],
                                      "[Operator instructions from this session, verbatim, in order]"),
         "pin_consol": prep["consol_block"]}
    if led is not None:
        b["ledger"] = L.render_ledger(led, "full")
    return b


def contexts(s, prep, blocks):
    turns = s["turns"]
    n = len(turns)
    tail, tail_start = turns[-L.TAIL:], n - L.TAIL + 1
    ctx = {"full": "[Session so far]\n" + L.render(turns),
           "plain": L.build_context(prep["summary"], tail, tail_start)}
    for arm, b in blocks.items():
        ctx[arm] = L.build_context(prep["summary"], tail, tail_start, b)
    return ctx


def probe_arm(s, arm, context):
    out = []
    for p in probes(s):
        salt = f"{s['sid']}|{arm}|{p['ptype']}|{p['idx']}"
        if p["kind"] == "decide":
            d, raw = L.decide(context, p["text"], salt)
            out.append(dict(arm=arm, **p, decision=d, raw=raw, correct=(d == p["expected"])))
        else:
            out.append(dict(arm=arm, **p, raw=L.ask(context, p["text"], salt)))
    return out


def run_session(s, outdir, arms):
    path = outdir / "sessions" / f"{s['sid']}.json"
    out = json.loads(path.read_text()) if path.exists() else None
    if out is None:
        summary, hist = L.recursive(s["turns"], "plain", s["sid"])
        cls = classify(s)
        cblock, chist, ccost = consolidation(s)
        out = dict(sid=s["sid"], base=s["base"], M=s["M"], n_turns=len(s["turns"]), n_operator=len(s["operator_turns"]),
                   prep=dict(summary=summary, summary_rounds=len(hist), classify=cls, consol_block=cblock,
                             consol_history=chist, consol_cost=ccost),
                   context_tokens={}, block_tokens={}, results=[])
    prep = out["prep"]
    if "ledger" in arms and "ledger" not in out:
        led, steps, errors, cost, snaps = ledger_run(s)
        out["ledger"] = dict(final=led, steps=steps, failed=errors, cost=cost, snapshots=snaps)
    have = {r["arm"] for r in out["results"]}
    todo = [a for a in arms if a not in have and (a != "ledger" or "ledger" in out)]
    if todo:
        blocks = blocks_for(s, prep, out.get("ledger", {}).get("final"))
        ctx = contexts(s, prep, blocks)
        for arm in todo:
            out["results"] += probe_arm(s, arm, ctx[arm])
            out["context_tokens"][arm] = L.ntok(ctx[arm])
            if arm in blocks:
                out["block_tokens"][arm] = L.ntok(blocks[arm])
    path.write_text(json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--M", default="25,50,100,200")
    ap.add_argument("--limit-base", type=int, default=0)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    outdir = L.set_model(a.model, a.threads)
    (outdir / "sessions").mkdir(exist_ok=True)
    arms = a.arms.split(",")
    Ms = {int(x) for x in a.M.split(",")}
    sessions = [s for s in json.loads((L.HERE / "data" / "sessions.json").read_text()) if s["M"] in Ms]
    if a.limit_base:
        sessions = [s for s in sessions if s["base"] < a.limit_base]
    sessions.sort(key=lambda s: (s["base"], -s["M"]))  # long sessions first within each base
    lock, done = threading.Lock(), [0]
    texts = sorted({o["text"] for s in sessions for o in s["operator_turns"]})
    with ThreadPoolExecutor(min(a.threads, 8)) as ex:  # warm the classifier cache in parallel
        list(ex.map(L.classify_directive, texts))
    print(f"classified {len(texts)} unique operator messages", flush=True)

    def work(s):
        try:
            run_session(s, outdir, arms)
            with lock:
                done[0] += 1
                print(f"done {s['sid']} ({done[0]}/{len(sessions)})", flush=True)
        except Exception:
            print(f"FAILED {s['sid']}\n{traceback.format_exc()}", flush=True)

    with ThreadPoolExecutor(min(a.threads, 8)) as ex:
        list(ex.map(work, sessions))


if __name__ == "__main__":
    main()
