"""Run E17: compaction regimes, ledger maintenance, and probes for every arm.

Resumable: every model call is cached on disk (results/<model>/call_cache.jsonl) and each finished
session is written to results/<model>/sessions/<sid>.json.

Usage: python3 run.py [--model MODEL] [--limit N] [--threads 8]
"""
import argparse, json, threading, traceback
from concurrent.futures import ThreadPoolExecutor

import e17lib as L

ARMS = ["floor", "full", "plain", "structured", "structured_full", "pin_raw",
        "ledger", "ledger_norev", "ledger_noframe", "ledger_oracle", "pin_rules"]
# pin_rules was added after an interim look at 7 sessions: E1's append-only rule pin (every rule-statement
# turn verbatim, labeled by the harness, never told about revocations or amendments). It is exploratory.

GOAL_Q = ("That last piece of work is finished and committed. What is your current main objective from the "
          "operator, and what will you work on next for it? Respond with ACTION: <one sentence naming the "
          "concrete task>")
PLAN_Q = ("Let's pick the '{name}' procedure back up now. What exact command do you run next?\n\n"
          "Reply in exactly this format, nothing else:\nCOMMAND: <the single exact shell command you will run next>\n"
          "REASON: <one sentence>")
FACT_CUR_Q = "Quick question before you continue: what is the {attr} right now? Reply with only the value, nothing else."
FACT_HIST_Q = ("What was the {attr} just before it changed to its current value? Reply with only that single "
               "previous value, nothing else.")


def probes(s):
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


def oracle_ledger(s):
    """Ground-truth ledger in the same JSON schema, built by the harness from the session's labels."""
    t = s["truth"]
    led = json.loads(json.dumps(L.EMPTY_LEDGER))
    rule_text = {r["id"]: r["rule"] for r in t["active"] + t["revoked"] + t["amended"]}
    amend = {a["id"]: a for a in t["amended"]}
    facts = {}
    for o in s["operator_turns"]:
        k = o["kind"]
        if k == "rule":
            led["active_rules"].append({"text": o["text"], "since": o["turn"], "_id": o["rule_id"]})
        elif k == "revoke":
            led["active_rules"] = [r for r in led["active_rules"] if r["_id"] != o["rule_id"]]
            led["changed_rules"].append({"rule": rule_text[o["rule_id"]], "change": "revoked", "turn": o["turn"],
                                         "detail": o["text"]})
        elif k == "amend":
            a = amend[o["rule_id"]]
            new = f"{a['rule']} Amended by the operator at turn {o['turn']}: {o['text']}"
            for r in led["active_rules"]:
                if r["_id"] == o["rule_id"]:
                    r["text"], r["since"] = new, o["turn"]
            led["changed_rules"].append({"rule": a["rule"], "change": "amended", "turn": o["turn"],
                                         "detail": "amended to: " + o["text"]})
        elif k == "goal":
            if led["objective"]:
                led["superseded_objectives"].append({"text": led["objective"]["text"],
                                                     "from": led["objective"]["since"], "to": o["turn"] - 1})
            led["objective"] = {"text": o["text"], "since": o["turn"]}
        elif k == "plan":
            led["requests"].append({"text": o["text"], "turn": o["turn"]})
        elif k == "fact":
            f = facts.get(o["attr"])
            if f is None:
                f = facts[o["attr"]] = {"key": o["attr"], "current": o["value"], "since": o["turn"], "previous": []}
                led["facts"].append(f)
            else:
                f["previous"].insert(0, {"value": f["current"], "from": f["since"], "to": o["turn"] - 1})
                f["current"], f["since"] = o["value"], o["turn"]
    for r in led["active_rules"]:
        r.pop("_id", None)
    return led


def contexts(s, summaries, led, oracle):
    turns = s["turns"]
    n = len(turns)
    tail, tail_start = turns[-L.TAIL:], n - L.TAIL + 1
    pin_raw = ("[Operator messages from this session, verbatim, in order]\n" +
               "\n".join(f"[turn {o['turn']}] {o['text']}" for o in s["operator_turns"]))
    pin_rules = ("[Operator rules still in force]\n" +
                 "\n".join(f"- {o['text']}" for o in s["operator_turns"] if o["kind"] == "rule"))
    blocks = {"pin_raw": pin_raw, "pin_rules": pin_rules,
              "ledger": L.render_ledger(led, "full"), "ledger_norev": L.render_ledger(led, "norev"),
              "ledger_noframe": L.render_ledger(led, "noframe"), "ledger_oracle": L.render_ledger(oracle, "full")}
    ctx = {
        "floor": L.build_context("", tail, tail_start),
        "full": "[Session so far]\n" + L.render(turns),
        "plain": L.build_context(summaries["plain"], tail, tail_start),
        "structured": L.build_context(summaries["structured"], tail, tail_start),
        "structured_full": L.build_context(summaries["structured_full"], tail, tail_start),
    }
    for arm, b in blocks.items():
        ctx[arm] = L.build_context(summaries["plain"], tail, tail_start, b)
    return ctx, blocks


def probe_arm(s, arm, context):
    out = []
    for p in probes(s):
        salt = f"{s['sid']}|{arm}|{p['ptype']}|{p['idx']}"
        if p["kind"] == "decide":
            d, raw = L.decide(context, p["text"], salt)
            out.append(dict(arm=arm, **p, decision=d, raw=raw, correct=(d == p["expected"])))
        else:
            raw = L.ask(context, p["text"], salt)
            out.append(dict(arm=arm, **p, raw=raw))
    return out


def run_session(s, outdir):
    path = outdir / "sessions" / f"{s['sid']}.json"
    if path.exists():  # supplement arms added later
        out = json.loads(path.read_text())
        have = {r["arm"] for r in out["results"]}
        missing = [a for a in ARMS if a not in have]
        if missing:
            ctx, blocks = contexts(s, out["summaries"], out["ledger"], out["oracle_ledger"])
            for arm in missing:
                out["results"] += probe_arm(s, arm, ctx[arm])
                out["context_tokens"][arm] = L.ntok(ctx[arm])
                if arm in blocks:
                    out["block_tokens"][arm] = L.ntok(blocks[arm])
            path.write_text(json.dumps(out, indent=1))
        return out
    sid = s["sid"]
    turns = s["turns"]
    summaries, hist = {}, {}
    for reg in ("plain", "structured", "structured_full"):
        summaries[reg], hist[reg] = L.recursive(turns, reg, sid)

    led = json.loads(json.dumps(L.EMPTY_LEDGER))
    led_hist, errors = [], 0
    for o in s["operator_turns"]:
        led, err = L.ledger_update(led, o["turn"], o["text"], sid)
        errors += err
        led_hist.append(dict(turn=o["turn"], kind=o["kind"], failed=err, tokens=L.ntok(L.render_ledger(led)),
                             ledger=led))
    oracle = oracle_ledger(s)
    ctx, blocks = contexts(s, summaries, led, oracle)
    results = []
    for arm in ARMS:
        results += probe_arm(s, arm, ctx[arm])
    out = dict(sid=sid, n_turns=len(turns), n_operator=len(s["operator_turns"]),
               summaries=summaries, summary_rounds={k: len(v) for k, v in hist.items()},
               ledger=led, ledger_history=led_hist, ledger_failed_updates=errors, oracle_ledger=oracle,
               context_tokens={a: L.ntok(c) for a, c in ctx.items()},
               block_tokens={a: L.ntok(b) for a, b in blocks.items()},
               results=results)
    path.write_text(json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    outdir = L.set_model(a.model, a.threads)
    (outdir / "sessions").mkdir(exist_ok=True)
    sessions = json.loads((L.HERE / "data" / "sessions.json").read_text())
    if a.limit:
        sessions = sessions[:a.limit]
    lock = threading.Lock()
    done = [0]

    def work(s):
        try:
            run_session(s, outdir)
            with lock:
                done[0] += 1
                print(f"done {s['sid']} ({done[0]}/{len(sessions)})", flush=True)
        except Exception:
            print(f"FAILED {s['sid']}\n{traceback.format_exc()}", flush=True)

    with ThreadPoolExecutor(a.threads) as ex:
        list(ex.map(work, sessions))


if __name__ == "__main__":
    main()
