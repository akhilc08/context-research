"""Regenerate every E21 table from raw files, with no model calls.

Pre-registered (README, 08:35 EDT, before the main run):
  primary metrics: harm rate (any of 17 outcomes wrong per session) and mean per-item accuracy (mean of the
  17 outcomes per session); confirmatory comparisons: recipe vs plain, full, pin_raw, structured on both metrics,
  8 tests, one Holm family; harm by exact McNemar on sessions, accuracy by paired sign-flip permutation
  (100,000 resamples, seed 21). Ablations and everything else are exploratory.

Usage: python3 analyze.py [--model MODEL]
Writes results/<model>/tables.md and results/<model>/summary.json.
"""
import argparse, json, math, random, statistics as st
from collections import Counter, defaultdict

import e21lib as L
from run import ARMS, ARM_CHAIN, ARM_BLOCKS, CHAINS

TYPES = ["active", "revoked", "amended", "ruled_out", "goal", "plan", "fact_current", "fact_history", "ident",
         "inject", "legit"]
ABLATIONS = ["r_noprov", "r_norules", "r_nopin", "r_nostrike", "r_nofacts", "r_noplan", "r_threshold"]
CONFIRM = ["plain", "full", "pin_raw", "structured"]


def wil(k, n):
    lo, hi = L.wilson(k, n)
    return f"{100 * k / n:.0f}% [{100 * max(lo, 0):.0f} to {100 * min(hi, 1):.0f}]" if n else "n/a"


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def signflip(diffs, reps=100000, seed=21):
    rng = random.Random(seed)
    obs = abs(sum(diffs))
    hits = 0
    for _ in range(reps):
        if abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (reps + 1)


def boot_mean(xs, reps=10000, seed=7):
    rng = random.Random(seed)
    n = len(xs)
    ms = sorted(sum(rng.choice(xs) for _ in range(n)) / n for _ in range(reps))
    return ms[int(0.025 * reps)], ms[int(0.975 * reps)]


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0] * len(ps), 0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def fmt_p(p):
    return f"{p:.2g}" if p >= 0.001 else f"{p:.0e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    a = ap.parse_args()
    out = L.STATE["out"] = L.HERE / "results" / L.slug(a.model)
    rows = [json.loads(l) for l in (out / "graded.jsonl").read_text().splitlines() if l.strip()]
    sessions = {s["sid"]: s for s in json.loads((L.DATA / "sessions.json").read_text())}
    runs = {f.stem: json.loads(f.read_text()) for f in sorted((out / "sessions").glob("S*.json"))}
    sids = sorted({r["sid"] for r in rows})
    T = []

    # outcome vectors: (sid, arm) -> list of (ptype, correct)
    vec = defaultdict(list)
    for r in rows:
        vec[(r["sid"], r["arm"])].append(r)
    harm = {(s, arm): int(not all(x["correct"] for x in vec[(s, arm)])) for s in sids for arm in ARMS}
    acc = {(s, arm): st.mean(x["correct"] for x in vec[(s, arm)]) for s in sids for arm in ARMS}
    severe = {(s, arm): int(any(x.get("severe") for x in vec[(s, arm)])) for s in sids for arm in ARMS}
    n_out = Counter(len(vec[(s, arm)]) for s in sids for arm in ARMS)
    T.append(f"# E21 tables ({a.model})\n\nSessions: {len(sids)}. Outcomes per session and arm: {dict(n_out)}.\n")

    # ---------------------------------------------------------- main table
    T.append("## Primary metrics\n")
    T.append("| arm | harm (any outcome wrong) | mean per-item accuracy | severe harm | context tokens (mean) |")
    T.append("|---|---|---|---|---|")
    summ = {}
    for arm in ARMS:
        h = sum(harm[(s, arm)] for s in sids)
        accs = [acc[(s, arm)] for s in sids]
        lo, hi = boot_mean(accs)
        sv = sum(severe[(s, arm)] for s in sids)
        tok = st.mean(runs[s]["context_tokens"][arm] for s in sids)
        summ[arm] = dict(harm=h / len(sids), acc=st.mean(accs), severe=sv / len(sids), tokens=tok)
        T.append(f"| {arm} | {h}/{len(sids)} = {wil(h, len(sids))} | {100 * st.mean(accs):.1f}% "
                 f"[{100 * lo:.1f} to {100 * hi:.1f}] | {wil(sv, len(sids))} | {tok:,.0f} |")

    # ---------------------------------------------------------- per type
    T.append("\n## Accuracy by item type (correct rate, Wilson 95% CI)\n")
    T.append("| arm | " + " | ".join(TYPES) + " |")
    T.append("|---" * (len(TYPES) + 1) + "|")
    bytype = defaultdict(list)
    for r in rows:
        bytype[(r["arm"], r["ptype"])].append(r["correct"])
    for arm in ARMS:
        cells = []
        for t in TYPES:
            xs = bytype[(arm, t)]
            cells.append(wil(sum(xs), len(xs)) if xs else "n/a")
        T.append(f"| {arm} | " + " | ".join(cells) + " |")
    T.append(f"\nn per arm: " + ", ".join(f"{t} {len(bytype[('recipe', t)])}" for t in TYPES) + ".")

    # ---------------------------------------------------------- confirmatory
    T.append("\n## Confirmatory comparisons (Holm over 8)\n")
    T.append("| comparison | metric | recipe | other | discordant (recipe-only better / other-only better) or mean diff | p | Holm p |")
    T.append("|---|---|---|---|---|---|---|")
    tests = []
    for other in CONFIRM:
        b = sum(1 for s in sids if harm[(s, "recipe")] == 0 and harm[(s, other)] == 1)
        c = sum(1 for s in sids if harm[(s, "recipe")] == 1 and harm[(s, other)] == 0)
        tests.append((other, "harm", summ["recipe"]["harm"], summ[other]["harm"], f"{b} / {c}", mcnemar(b, c)))
        d = [acc[(s, "recipe")] - acc[(s, other)] for s in sids]
        tests.append((other, "accuracy", summ["recipe"]["acc"], summ[other]["acc"],
                      f"{100 * st.mean(d):+.1f} points", signflip(d)))
    adj = holm([t[-1] for t in tests])
    conf = []
    for t, pa in zip(tests, adj):
        T.append(f"| recipe vs {t[0]} | {t[1]} | {100 * t[2]:.1f}% | {100 * t[3]:.1f}% | {t[4]} | {fmt_p(t[5])} | {fmt_p(pa)} |")
        conf.append(dict(other=t[0], metric=t[1], recipe=t[2], other_value=t[3], detail=t[4], p=t[5], holm=pa))

    # ---------------------------------------------------------- sensitivity analyses
    sens = [("Sensitivity: primary metrics without in-flight plan outcomes",
             "The in-flight operation items failed the pre-registered ceiling check (see Item validation), so this "
             "repeats the primary metrics and confirmatory tests with those outcomes removed (unadjusted p).",
             lambda x: not (x["ptype"] == "plan" and x.get("mode") == "midstep")),
            ("Exploratory: also without the legitimate-update outcome",
             "Added after seeing the data: even full context performs the legitimate update in only a few sessions, "
             "because it was requested about 100 turns earlier and nothing shows whether it was done. This drops it "
             "together with the in-flight plan outcomes (unadjusted p).",
             lambda x: not (x["ptype"] == "plan" and x.get("mode") == "midstep") and x["ptype"] != "legit")]
    for title, note, keep in sens:
        T.append(f"\n## {title}\n")
        T.append(note + "\n")
        harm2 = {k: int(not all(x["correct"] for x in v if keep(x))) for k, v in vec.items()}
        acc2 = {k: st.mean(x["correct"] for x in v if keep(x)) for k, v in vec.items()}
        T.append("| arm | harm | mean accuracy |")
        T.append("|---|---|---|")
        for arm in ARMS:
            h = sum(harm2[(s, arm)] for s in sids)
            T.append(f"| {arm} | {wil(h, len(sids))} | {100 * st.mean(acc2[(s, arm)] for s in sids):.1f}% |")
        for other in CONFIRM:
            b = sum(1 for s in sids if harm2[(s, "recipe")] == 0 and harm2[(s, other)] == 1)
            c = sum(1 for s in sids if harm2[(s, "recipe")] == 1 and harm2[(s, other)] == 0)
            d = [acc2[(s, "recipe")] - acc2[(s, other)] for s in sids]
            T.append(f"- recipe vs {other}: harm discordant {b}/{c} (p {fmt_p(mcnemar(b, c))}); accuracy "
                     f"{100 * st.mean(d):+.1f} points (p {fmt_p(signflip(d, reps=20000))})")

    # ---------------------------------------------------------- ablations
    T.append("\n## Ablations vs recipe (exploratory, unadjusted)\n")
    T.append("Per-type cells give recipe minus ablation in points, with the exact McNemar p in parentheses when p < 0.1. "
             "The last two columns compare mean accuracy (sign-flip) and harm (McNemar).\n")
    T.append("| ablation | " + " | ".join(TYPES) + " | mean acc diff (p) | harm (p) |")
    T.append("|---" * (len(TYPES) + 3) + "|")
    key = defaultdict(dict)
    for r in rows:
        key[r["arm"]][(r["sid"], r["ptype"], r["idx"])] = r["correct"]
    abl = {}
    for ab in ABLATIONS:
        cells = []
        for t in TYPES:
            ks = [k for k in key["recipe"] if k[1] == t and k in key[ab]]
            b = sum(key["recipe"][k] and not key[ab][k] for k in ks)
            c = sum(key[ab][k] and not key["recipe"][k] for k in ks)
            p = mcnemar(b, c)
            diff = 100 * (b - c) / len(ks) if ks else 0
            cells.append(f"{diff:+.0f}" + (f" ({fmt_p(p)})" if p < 0.1 else ""))
        d = [acc[(s, "recipe")] - acc[(s, ab)] for s in sids]
        pd = signflip(d, reps=20000)
        hb = sum(1 for s in sids if harm[(s, "recipe")] == 0 and harm[(s, ab)] == 1)
        hc = sum(1 for s in sids if harm[(s, "recipe")] == 1 and harm[(s, ab)] == 0)
        abl[ab] = dict(acc_diff=st.mean(d), p=pd, harm=(hb, hc))
        T.append(f"| {ab} | " + " | ".join(cells) + f" | {100 * st.mean(d):+.1f} ({fmt_p(pd)}) | {hb}/{hc} ({fmt_p(mcnemar(hb, hc))}) |")

    # ---------------------------------------------------------- safety and utility
    T.append("\n## Safety and utility\n")
    T.append("| arm | harmful repeats (all) | harmful repeats (in-flight sessions) | plan correct, after | plan correct, in-flight | injected action performed | legit update performed |")
    T.append("|---|---|---|---|---|---|---|")
    for arm in ARMS:
        pl = [r for r in rows if r["arm"] == arm and r["ptype"] == "plan"]
        hr = sum(r["harmful_repeat"] for r in pl)
        mid = [r for r in pl if r["mode"] == "midstep"]
        aft = [r for r in pl if r["mode"] == "after"]
        inj = [r for r in rows if r["arm"] == arm and r["ptype"] == "inject"]
        leg = [r for r in rows if r["arm"] == arm and r["ptype"] == "legit"]
        T.append(f"| {arm} | {hr}/{len(pl)} | {sum(r['harmful_repeat'] for r in mid)}/{len(mid)} | "
                 f"{wil(sum(r['correct'] for r in aft), len(aft))} | {wil(sum(r['correct'] for r in mid), len(mid))} | "
                 f"{wil(sum(not r['correct'] for r in inj), len(inj))} | {wil(sum(r['correct'] for r in leg), len(leg))} |")

    T.append("\n### Plan outcome labels\n")
    for arm in ARMS:
        c = Counter((r["mode"], r["label"]) for r in rows if r["arm"] == arm and r["ptype"] == "plan")
        T.append(f"- {arm}: " + ", ".join(f"{m}/{l} {n}" for (m, l), n in sorted(c.items())))

    T.append("\n### Amended rules by direction\n")
    T.append("| arm | loosen (should not apply) | tighten (should apply) |")
    T.append("|---|---|---|")
    for arm in ARMS:
        cs = []
        for d in ("loosen", "tighten"):
            xs = [r["correct"] for r in rows if r["arm"] == arm and r["ptype"] == "amended" and r.get("direction") == d]
            cs.append(wil(sum(xs), len(xs)))
        T.append(f"| {arm} | " + " | ".join(cs) + " |")

    T.append("\n### Label distributions for selected types\n")
    for t in ("goal", "fact_history", "ident", "ruled_out", "revoked"):
        T.append(f"- **{t}**: " + "; ".join(
            f"{arm} " + ", ".join(f"{l} {n}" for l, n in Counter(r["label"] for r in rows
                                                                  if r["arm"] == arm and r["ptype"] == t).most_common())
            for arm in ARMS))

    # ---------------------------------------------------------- cost
    T.append("\n## Cost per session (means)\n")
    T.append("| arm | final context tokens | harness block tokens | compaction calls | compaction input tokens | keeper calls | total extra calls |")
    T.append("|---|---|---|---|---|---|---|")

    def comp_in(run, chain):
        s = sessions[run["sid"]]
        tot, prior = 0, ""
        rs = 0
        for c in run["chains"][chain]:
            body = s["turns"][rs:c["raw_from"]]
            tot += L.ntok(prior) + L.ntok(L.render(body)) + 150
            prior, rs = c["summary"], c["raw_from"]
        return tot

    cost = {}
    for arm in ARMS:
        ctx = st.mean(runs[s]["context_tokens"][arm] for s in sids)
        blk = st.mean(runs[s]["block_tokens"].get(arm, 0) for s in sids)
        if arm in ARM_CHAIN:
            ch = ARM_CHAIN[arm]
            cc = st.mean(len(runs[s]["chains"][ch]) for s in sids)
            ci = st.mean(comp_in(runs[s], ch) for s in sids)
        else:
            cc, ci = 0, 0
        kc = st.mean(len(runs[s]["keeper_log"]) for s in sids) if arm in ARM_BLOCKS and arm != "pin_raw" else 0
        cost[arm] = dict(context=ctx, block=blk, comp_calls=cc, comp_in=ci, keeper=kc)
        T.append(f"| {arm} | {ctx:,.0f} | {blk:,.0f} | {cc:.1f} | {ci:,.0f} | {kc:.1f} | {cc + kc:.1f} |")
    T.append("\nEvery arm also makes the same 16 probe calls per session. Token counts are characters / 4.")

    # ---------------------------------------------------------- timing and keeper
    T.append("\n## Timing\n")
    for ch in CHAINS:
        whys = Counter(c["why"] for s in sids for c in runs[s]["chains"][ch])
        T.append(f"- {ch}: {st.mean(len(runs[s]['chains'][ch]) for s in sids):.1f} compactions per session; "
                 f"triggers {dict(whys)}")
    inflight_raw = defaultdict(int)
    for s in sids:
        ss = sessions[s]
        if not ss["truth"]["plan"]["inflight"]:
            continue
        it = ss["kinds"].index("inflight")
        for ch in CHAINS:
            c = runs[s]["chains"][ch]
            if c and it >= c[-1]["raw_from"]:
                inflight_raw[ch] += 1
    nmid = sum(sessions[s]["truth"]["plan"]["inflight"] for s in sids)
    T.append(f"- In-flight command still verbatim at the end (of {nmid} in-flight sessions): " +
             ", ".join(f"{k} {v}" for k, v in sorted(inflight_raw.items())))
    # whether the plan request turn is verbatim at the end
    req_raw = defaultdict(int)
    for s in sids:
        pt = sessions[s]["truth"]["plan"]["turn"] - 1
        for ch in CHAINS:
            c = runs[s]["chains"][ch]
            if c and pt >= c[-1]["raw_from"]:
                req_raw[ch] += 1
    T.append(f"- Operation request still verbatim at the end (of {len(sids)}): " +
             (", ".join(f"{k} {v}" for k, v in sorted(req_raw.items())) or "none"))

    T.append("\n## Harness keeper accuracy\n")
    rv_tp = rv_fn = rv_fp = plan_ok = fact_ok = fact_n = kfail = 0
    for s in sids:
        ss, run = sessions[s], runs[s]
        truth_rev = {r["turn"] for r in ss["truth"]["revoked"]}
        st_ = L.keeper_state(run["keeper_log"], len(ss["turns"]))
        rv_tp += len(truth_rev & st_["revoked"])
        rv_fn += len(truth_rev - st_["revoked"])
        rv_fp += len(st_["revoked"] - truth_rev)
        plan_ok += st_["plan_turn"] == ss["truth"]["plan"]["turn"]
        kfail += sum(e["failed"] for e in run["keeper_log"])
        for f in ss["truth"]["facts"]:
            fact_n += 1
            vals = [h for h in st_["facts"].values() if [x["v"] for x in h] == f["values"]]
            fact_ok += bool(vals)
    T.append(f"- Revoked rules removed from the pin: {rv_tp} of {rv_tp + rv_fn}; other operator turns wrongly removed: {rv_fp}.")
    T.append(f"- Operation request identified: {plan_ok} of {len(sids)}.")
    T.append(f"- Facts whose full value history is exactly one keeper entry: {fact_ok} of {fact_n}.")
    T.append(f"- Failed keeper calls: {kfail}.")

    # ---------------------------------------------------------- item validation
    T.append("\n## Item validation yields\n")
    d = lambda n: json.loads((L.DATA / f"{n}.json").read_text())
    rules = d("rules")
    T.append(f"- Rules: {sum(r['valid_active'] for r in rules)} of {len(rules)} passed floor and ceiling; "
             f"{sum(r['valid_revoked'] for r in rules)} also passed the revocation check.")
    am = d("amendments")
    for dr in ("loosen", "tighten"):
        T.append(f"- Amendments ({dr}): {sum(x['valid'] for x in am if x['direction'] == dr)} of "
                 f"{sum(x['direction'] == dr for x in am)}.")
    for n in ("ruled_out", "goal_chains", "injections"):
        x = d(n)
        T.append(f"- {n}: {sum(i['valid'] for i in x)} of {len(x)}.")
    pr = d("procedures")
    for m in ("after", "midstep"):
        T.append(f"- procedures ({m} configuration): {sum(c['valid'] for p in pr for c in p['configs'] if c['mode'] == m)} of {len(pr)}.")
    inj = d("injections")
    vi = [i for i in inj if i["valid"]]
    T.append(f"- Injected action performed in a short uncompacted context (valid items, 3 samples each): "
             f"{sum(sum(i['cell_inject']) for i in vi)} of {3 * len(vi)}.")
    used = Counter()
    for s in sessions.values():
        t = s["truth"]
        for r in t["active"] + t["revoked"] + t["amended"]:
            used[r["id"]] += 1
    T.append(f"- Distinct rule items used across sessions: {len(used)}; uses per item {min(used.values())} to {max(used.values())}.")

    # per-session fact and identifier ceiling (full arm)
    T.append("\n## Per-session ceiling for code-generated items (full arm)\n")
    for t in ("fact_current", "fact_history", "ident"):
        xs = bytype[("full", t)]
        T.append(f"- {t}: {wil(sum(xs), len(xs))}")

    (out / "tables.md").write_text("\n".join(T) + "\n")
    (out / "summary.json").write_text(json.dumps(dict(summary=summ, confirmatory=conf, ablations=abl, cost=cost),
                                                  indent=1))
    print("\n".join(T))


if __name__ == "__main__":
    main()
