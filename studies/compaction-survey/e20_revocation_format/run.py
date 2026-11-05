"""Run E20: one agent decision per (session, summary condition, format, rule probe, sample).

The session tail, the plain summary, and the probes are fixed (from E17); only the rule block changes.
Conditions: clean (E17's plain summary) and stale (the same summary plus a 'Standing rules:' list that
still states every rule as first given). Samples: 2 per active and revoked probe, 3 per amended probe.

Resumable: every call is cached in results/<model>/call_cache.jsonl.
Usage: python3 run.py [--model MODEL] [--limit N] [--threads 8] [--conds clean,stale]
Writes results/<model>/raw.jsonl (every reply) and results/<model>/blocks.json (every rendered block).
"""
import argparse, json, threading, time
from concurrent.futures import ThreadPoolExecutor

import e20lib as L
from formats import FORMATS, render, stale_summary

SAMPLES = {"active": 2, "revoked": 2, "amended": 3}


def probes(s):
    out = []
    for i, r in enumerate(s["active"]):
        out.append(dict(ptype="active", idx=i, item=r["id"], rule=r["rule"], text=r["trigger"], want="APPLIES"))
    for i, r in enumerate(s["revoked"]):
        out.append(dict(ptype="revoked", idx=i, item=r["id"], rule=r["rule"], text=r["trigger"], want="IGNORES"))
    for i, a in enumerate(s["amended"]):
        out.append(dict(ptype="amended", idx=i, item=a["id"], rule=a["rule"], text=a["probe"],
                        direction=a["direction"], want="IGNORES" if a["direction"] == "loosen" else "APPLIES"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--conds", default="clean,stale")
    ap.add_argument("--formats", default=",".join(FORMATS))
    a = ap.parse_args()
    outdir = L.set_model(a.model, a.threads)
    S = json.loads((L.HERE / "data" / "sessions_e20.json").read_text())
    if a.limit:
        S = S[:a.limit]
    rw = json.loads((L.HERE / "data" / "rewrites.json").read_text())
    conds, fmts = a.conds.split(","), a.formats.split(",")

    blocks, jobs = {}, []
    for s in S:
        summ = {"clean": s["plain_summary"], "stale": stale_summary(s)}
        for f in fmts:
            b = render(f, s, rw)
            blocks[f"{s['sid']}|{f}"] = dict(block=b, tokens=L.ntok(b))
            for c in conds:
                ctx = L.build_context(summ[c], s["tail"], s["tail_start"], b)
                for p in probes(s):
                    for k in range(SAMPLES[p["ptype"]]):
                        jobs.append((s["sid"], c, f, p, k, ctx))
    (outdir / "blocks.json").write_text(json.dumps(blocks, indent=1))
    print(len(jobs), "decisions", flush=True)
    lock, done, t0 = threading.Lock(), [0], time.time()

    def work(j):
        sid, c, f, p, k, ctx = j
        d, raw = L.decide(ctx, p["text"], salt=f"{sid}|{c}|{f}|{p['ptype']}|{p['idx']}|{k}")
        with lock:
            done[0] += 1
            if done[0] % 500 == 0:
                print(f"{done[0]}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
        return dict(sid=sid, cond=c, fmt=f, sample=k, decision=d, raw=raw, context_tokens=L.ntok(ctx),
                    **{x: p[x] for x in p})

    with ThreadPoolExecutor(a.threads) as ex:
        rows = list(ex.map(work, jobs))
    with open(outdir / "raw.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("wrote", len(rows), flush=True)


if __name__ == "__main__":
    main()
