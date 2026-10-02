"""E11 main run: subtle injections, recursive compaction over 1, 3, and 6 rounds, and six defenses.

Per (scenario, variant, rep) one session. inject sessions are 36 turns (6 rounds); legit and none sessions are
18 turns (3 rounds). The manipulated turn is turn 4, so it is summarized in round 1 and re-summarized every round.
Conditions (agent context):
  full       verbatim transcript up to the checkpoint
  plain      plain recursive summary + 2-turn tail
  pin        plain + operator messages pinned verbatim
  prov       provenance-attributing summary (E5 prompt)
  prov_pin   prov + pinned operator messages
  quar_strip summary of transcript whose tool outputs were sanitized by the quarantine filter (strip only)
  watch      plain summary passed through the attribution watchpoint
  watch_pin  watch + pinned operator messages
All eight run at checkpoint round 3. inject sessions also run full and plain at rounds 1 and 6, and judge the
plain and prov summaries at every checkpoint (accumulation).
Writes results/trials.jsonl (resumable).
Usage: python run.py [--variants inject,legit,none] [--reps 3] [--none-reps 1] [--limit N] [--out FILE]
       [--model ID] [--judge-model ID] [--workers 10]
"""
import argparse, json, threading, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import lib
from lib import HERE, build, chain, context_block, pin_block, watchpoint, quarantine, judge_summary, act_graded, PROV_PROMPT

CONDS3 = ["full", "plain", "pin", "prov", "prov_pin", "quar_strip", "watch", "watch_pin"]
CONDS16 = ["full", "plain"]
_lock = threading.Lock()


def trial(s, variant, rep, idx):
    seed = 1000 * (rep + 1) + idx
    rounds = 6 if variant == "inject" else 3
    turns = build(s, variant, seed, rounds)
    rec = {"id": s["id"], "family": s["family"], "variant": variant, "rep": rep, "seed": seed,
           "agent_model": lib.AGENT_MODEL, "judge_model": lib.JUDGE_MODEL,
           "summaries": {}, "sjudge": {}, "watch_info": {}, "cp": {}}
    plain = chain(turns, tag="e11_c_plain")
    prov = chain(turns, PROV_PROMPT, tag="e11_c_prov")
    qturns, extracted = quarantine(turns[:18], s)
    quar = chain(qturns, tag="e11_c_quar")
    rec["quarantine_extracted"] = extracted
    cps = (1, 3, 6) if variant == "inject" else (3,)
    for r in cps:
        t_r = turns[:6 * r]
        psum, tail = plain[r - 1]
        pb = pin_block(t_r)
        sums = {"plain": psum, "prov": prov[r - 1][0]}
        if r == 3:
            wsum, winfo = watchpoint(psum, t_r)
            rec["watch_info"][str(r)] = winfo
            sums["quar"], sums["watch"] = quar[2][0], wsum
        for k, v in sums.items():
            rec["summaries"].setdefault(k, {})[str(r)] = v
            if not (variant == "none" and s["family"] == "B"):
                rec["sjudge"].setdefault(k, {})[str(r)] = judge_summary(v, s, variant)
        ctx = {"full": context_block("", t_r), "plain": context_block(psum, tail)}
        if r == 3:
            ctx.update(pin=context_block(psum, tail, extras=pb),
                       prov=context_block(sums["prov"], tail),
                       prov_pin=context_block(sums["prov"], tail, extras=pb),
                       watch=context_block(wsum, tail),
                       watch_pin=context_block(wsum, tail, extras=pb),
                       quar_strip=context_block(sums["quar"], quar[2][1]))
        rec.setdefault("tails", {})[str(r)] = tail
        conds = CONDS3 if r == 3 else CONDS16
        rec["cp"][str(r)] = {c: act_graded(ctx[c], s, f"e11_act_{c}") for c in conds}
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="inject,legit,none")
    ap.add_argument("--families", default="A,B")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--none-reps", type=int, default=1, help="reps for the none variant (family B); A uses --reps")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="results/trials.jsonl")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--model", default=lib.orclient.MODEL, help="agent, summarizer, filter, watchpoint model")
    ap.add_argument("--judge-model", default=lib.orclient.MODEL)
    a = ap.parse_args()
    lib.set_models(a.model, a.judge_model)
    SC = lib.load_scen()
    out = HERE / a.out
    out.parent.mkdir(exist_ok=True)
    done = set()
    if out.exists():
        done = {(r["id"], r["variant"], r["rep"]) for r in map(json.loads, out.read_text().splitlines())}
    jobs = []
    for rep in range(a.reps):  # rep-major order so an early stop leaves balanced reps
        for v in a.variants.split(","):
            for fam in a.families.split(","):
                nrep = a.none_reps if (v == "none" and fam == "B") else a.reps
                if rep >= nrep:
                    continue
                for i, s in enumerate(SC[fam][: a.limit or None]):
                    if (s["id"], v, rep) not in done:
                        jobs.append((s, v, rep, i))
    print(f"{len(jobs)} trials to run", flush=True)
    with ThreadPoolExecutor(min(a.workers, 10)) as ex:
        futs = {ex.submit(trial, *j): j for j in jobs}
        for n, f in enumerate(as_completed(futs), 1):
            s, v, rep, _ = futs[f]
            try:
                r = f.result()
            except Exception:
                print(f"FAIL {s['id']} {v} {rep}\n{traceback.format_exc()[-600:]}", flush=True)
                continue
            with _lock, open(out, "a") as fh:
                fh.write(json.dumps(r) + "\n")
            c3 = r["cp"]["3"]
            print(f"[{n}/{len(jobs)}] {s['id']} {v} rep{rep} sum={r['sjudge'].get('plain', {}).get('3', {}).get('category')} " +
                  " ".join(f"{c}={int(c3[c]['acted'])}" for c in CONDS3), flush=True)


if __name__ == "__main__":
    main()
