"""Analyze E14. Regenerates results/tables.md, results/summary.json, results/per_task.json.

    /private/tmp/supersede-venv/bin/python analyze.py [--model <backbone>]
"""
import argparse, json, math, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/private/tmp/supersede/src")
sys.path.insert(0, str(HERE))
from supersede.scoring import classify, normalize, _mentions          # noqa: E402
from supersede.timeline import generate_timeline, TimelineConfig      # noqa: E402
from e14 import build_versioned, newest, SYNTH_CFGS                   # noqa: E402

E4_SUMMARY = HERE.parent / "e4_supersede" / "results" / "summary.json"
USAGE = HERE.parent / "usage.jsonl"
ARMS = ["full", "notes300", "notes1200", "notes_tm", "pin", "vpin", "vpin_canon", "n1200_vpin"]
REPS = [1, 2]
# planned comparisons, fixed with the hypotheses
PAIRS = [("vpin_canon", "pin"), ("vpin", "pin"), ("vpin_canon", "vpin"), ("vpin_canon", "notes1200"),
         ("vpin_canon", "full"), ("n1200_vpin", "notes1200"), ("n1200_vpin", "full"), ("notes_tm", "vpin_canon")]
COST = {"full": ["ans_full"], "notes300": ["notes300", "ans_notes300"], "notes1200": ["notes1200", "ans_notes1200"],
        "pin": ["notes300", "extract", "ans_pin"], "vpin": ["notes300", "extract", "ans_vpin"],
        "vpin_canon": ["notes300", "extract_canon", "ans_vpin_canon"],
        "n1200_vpin": ["notes1200", "extract_canon", "ans_n1200_vpin"], "notes_tm": ["notes_tm*", "ans_notes_tm"]}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def sign_test(a, b):
    """Exact two-sided sign test on paired scores (McNemar when scores are 0/1)."""
    x = sum(1 for i, j in zip(a, b) if i > j)
    y = sum(1 for i, j in zip(a, b) if j > i)
    n = x + y
    if n == 0:
        return x, y, 1.0
    k = min(x, y)
    return x, y, min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def boot(xs, B=4000, seed=0):
    rng = random.Random(seed)
    n = len(xs)
    m = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return m[int(0.025 * B)], m[int(0.975 * B)]


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def load_usage(prefix):
    last = {}
    for line in USAGE.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        p = r.get("tag", "").split("|")
        if len(p) == 6 and p[0] == "e14" and p[2].endswith(prefix) and ("@" in p[2]) == bool(prefix):
            p[2] = p[2][:len(p[2]) - len(prefix)] if prefix else p[2]
            last[tuple(p[1:])] = r
    tok = defaultdict(lambda: [0, 0, 0])
    for (rep, s, q, unit, kind), r in last.items():
        if unit.startswith("ans_") and kind != "cur":
            continue  # cost per question: count the current-value answer call only
        u = "notes_tm*" if unit.startswith("notes_tm") else unit
        k = tok[(rep, s, q, u)]
        k[0] += r.get("in") or 0
        k[1] += r.get("out") or 0
        k[2] += 1
    return tok


def synth_chains(t):
    kw, _ = SYNTH_CFGS[t["set"]]
    seed = int(t["qid"].split("_")[1])
    tl = generate_timeline(seed, TimelineConfig(**kw) if kw else None)
    ch = defaultdict(list)
    for f in tl.facts:
        if f.metadata.get("role") == "tracked":
            ch[f.subject].append(f.object)
    return ch, tl.subject


def synth_store_audit(t, facts):
    """Exact orphan audit on synthetic stores. A chain is orphaned when two or more keys for that
    subject currently hold a value from the chain (so an old value survives as if current)."""
    hist = build_versioned(facts)
    cur = newest(hist)
    ch, queried = synth_chains(t)
    orph, stale_alive, chains = 0, 0, 0
    q_hist_ok = False
    for subj, vals in ch.items():
        if len(vals) < 2:
            continue
        chains += 1
        keys = [k for k, v in cur.items() if k.split("|")[0].strip().startswith(subj.lower())
                and any(_mentions(normalize(v), x) for x in vals)]
        if len(keys) >= 2:
            orph += 1
            if any(not _mentions(normalize(cur[k]), vals[-1]) for k in keys):
                stale_alive += 1
        if subj == queried:
            for k in keys:
                h = hist[k]
                if (len(h) >= 2 and _mentions(normalize(h[-1]["v"]), vals[-1])
                        and _mentions(normalize(h[-2]["v"]), vals[-2])):
                    q_hist_ok = True
    return {"chains": chains, "orphan_chains": orph, "stale_alive": stale_alive, "queried_history_ok": q_hist_ok,
            "n_keys": len(cur), "n_versions": sum(len(h) for h in hist.values())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    a = ap.parse_args()
    units, prefix, out_dir = HERE / "results" / "units", "", HERE / "results"
    if a.model != "stealth/space-bunny-alpha":
        safe = re.sub(r"[^\w]+", "_", a.model)
        units, prefix, out_dir = HERE / "results" / f"units_{safe}", f"@{safe}", HERE / "results" / f"analysis_{safe}"
        out_dir.mkdir(exist_ok=True)
    meta = json.loads((HERE / "results" / "tasks_meta.json").read_text())
    hist_qids = set(json.loads(E4_SUMMARY.read_text())["lme_history_split"]["hist_qids"])
    tok = load_usage(prefix)

    # ---------------------------------------------------------------- per task records
    per = []
    for t in meta:
        rec = {k: t.get(k) for k in ("set", "qid", "question", "answer", "hist_answer")}
        rec["is_hist"] = t["qid"] in hist_qids
        rec["reps"] = {}
        ok = True
        for rep in REPS:
            d = units / f"rep{rep}" / t["set"] / t["qid"]
            if not (d / "ans_n1200_vpin_cur.json").exists():
                ok = False
                break
            R = rec["reps"][rep] = {"arms": {}}
            jd = json.loads((d / "judge.json").read_text()) if (d / "judge.json").exists() else None
            if t["set"] == "lme" and jd is None:
                ok = False
                break
            for arm in ARMS:
                for qk in ("cur", "hist"):
                    p = d / f"ans_{arm}_{qk}.json"
                    if not p.exists():
                        continue
                    u = json.loads(p.read_text())
                    r = {"answer": u["answer"], "memory_chars": u["memory_chars"]}
                    if t["set"] == "lme":
                        if arm not in jd:
                            continue
                        r.update(correct=jd[arm]["yes"], v4=jd[arm].get("v4"))
                        r.update(stale=r["v4"] == "stale", amb=r["v4"] == "ambiguous")
                    else:
                        gold, wrong = (t["answer"], t["stale"]) if qk == "cur" else (t["hist_answer"], t["hist_wrong"])
                        v = classify(u["answer"], gold, wrong)
                        r.update(verdict=v, correct=v == "correct", stale=v == "stale", amb=v == "ambiguous")
                    if qk == "cur":
                        ti = to = calls = 0
                        for cu in COST[arm]:
                            i_, o_, c_ = tok.get((f"rep{rep}", t["set"], t["qid"], cu), (0, 0, 0))
                            ti += i_; to += o_; calls += c_
                        r.update(tok_in=ti, tok_out=to, calls=calls)
                    R["arms"][f"{arm}|{qk}"] = r
            stores = {}
            for unit in ("extract", "extract_canon"):
                ext = json.loads((d / f"{unit}.json").read_text())
                h = build_versioned(ext["facts"])
                st = {"n_keys": len(h), "n_versions": sum(len(x) for x in h.values()),
                      "multi_version_keys": sum(len(x) > 1 for x in h.values())}
                if t["set"] != "lme":
                    st.update(synth_store_audit(t, ext["facts"]))
                if unit == "extract_canon":
                    lg = ext["log"]
                    st.update(new_keys_after_s1=sum(x["new_keys"] for x in lg[1:]),
                              facts_after_s1=sum(x["n"] for x in lg[1:]))
                stores[unit] = st
            if (d / "orphan_audit.json").exists():
                oa = json.loads((d / "orphan_audit.json").read_text())
                for unit in oa:
                    gs = oa[unit]["groups"]
                    stores[unit].update(audit_groups=len(gs), audit_redundant=sum(len(g) - 1 for g in gs),
                                        audit_groups_list=gs)
            R["stores"] = stores
        if ok:
            per.append(rec)
    (out_dir / "per_task.json").write_text(json.dumps(per, indent=1))

    lines, summary = [], {}
    P = lines.append

    def present(R, qk):
        return [a for a in ARMS if all(f"{a}|{qk}" in r["reps"][rep]["arms"] for r in R for rep in REPS)]

    def score(r, arm, qk, field="correct"):
        return [int(r["reps"][rep]["arms"][f"{arm}|{qk}"][field]) for rep in REPS]

    def acc_table(name, R, qk, stale_base=None):
        n = len(R)
        arms = present(R, qk)
        S = summary.setdefault(name, {"n": n, "arms": {}, "pairs": {}})
        P(f"\n### {name} (n={n})\n")
        P("| arm | rep 1 | rep 2 | mean acc | 95% CI (bootstrap) | per-task agreement | stale (mean) | ambiguous (mean) | memory chars |")
        P("|---|---|---|---|---|---|---|---|---|")
        base = stale_base if stale_base is not None else R
        for arm in arms:
            k1 = sum(score(r, arm, qk)[0] for r in R)
            k2 = sum(score(r, arm, qk)[1] for r in R)
            m = [sum(score(r, arm, qk)) / 2 for r in R]
            lo, hi = boot(m)
            agree = sum(len(set(score(r, arm, qk))) == 1 for r in R)
            st = sum(sum(score(r, arm, qk, "stale")) for r in base) / 2
            am = sum(sum(score(r, arm, qk, "amb")) for r in base) / 2
            mc = sum(r["reps"][rep]["arms"][f"{arm}|{qk}"]["memory_chars"] for r in R for rep in REPS) / (2 * n)
            S["arms"][arm] = {"rep1": k1, "rep2": k2, "mean_acc": (k1 + k2) / (2 * n), "ci": [lo, hi],
                              "agree": agree, "stale_mean": st, "amb_mean": am, "stale_n": len(base), "memory_chars": mc}
            P(f"| {arm} | {k1} | {k2} | {(k1 + k2) / (2 * n):.1%} | {lo:.0%} to {hi:.0%} | {agree}/{n} | "
              f"{st:g}/{len(base)} | {am:g}/{len(base)} | {mc:,.0f} |")
        pairs = [(x, y) for x, y in PAIRS if x in arms and y in arms]
        rows = []
        for x, y in pairs:
            mx = [sum(score(r, x, qk)) / 2 for r in R]
            my = [sum(score(r, y, qk)) / 2 for r in R]
            xo, yo, p = sign_test(mx, my)
            mcn = [sign_test([score(r, x, qk)[i] for r in R], [score(r, y, qk)[i] for r in R]) for i in range(2)]
            lo, hi = boot([u - v for u, v in zip(mx, my)])
            rows.append((x, y, sum(mx), sum(my), xo, yo, p, mcn, lo, hi))
        if rows:
            P(f"\n| A vs B | mean correct A, B | tasks A higher | tasks B higher | sign test p | Holm p ({len(rows)} tests) | McNemar p rep 1, rep 2 | mean diff 95% CI |")
            P("|---|---|---|---|---|---|---|---|")
            for (x, y, sx, sy, xo, yo, p, mcn, lo, hi), ph in zip(rows, holm([r[6] for r in rows])):
                S["pairs"][f"{x}-{y}"] = {"a_higher": xo, "b_higher": yo, "p": p, "p_holm": ph,
                                          "mcnemar_rep": [m[2] for m in mcn], "diff_ci": [lo, hi]}
                P(f"| {x} vs {y} | {sx:g}, {sy:g} | {xo} | {yo} | {p:.3g} | {ph:.3g} | {mcn[0][2]:.3g}, {mcn[1][2]:.3g} | "
                  f"{lo:+.1%} to {hi:+.1%} |")

    lme = [r for r in per if r["set"] == "lme"]
    syn = [r for r in per if r["set"] != "lme"]
    if lme:
        P("## LongMemEval knowledge-update\n")
        P("Accuracy is E4's yes/no judge. Stale and ambiguous come from E4's four-way judge on tasks with an "
          "E4 wrong-version label. Means are over the two repeats. Rep 1 of full, notes300, notes1200, and pin "
          "reuses E4's answers (re-judged here).")
        lab = [r for r in lme if r["reps"][1]["arms"]["full|cur"].get("v4") is not None]
        acc_table("lme_all", lme, "cur", lab)
        hist = [r for r in lme if r["is_hist"]]
        oth = [r for r in lme if not r["is_hist"]]
        acc_table("lme_history", hist, "cur", [r for r in hist if r in lab])
        acc_table("lme_current", oth, "cur", [r for r in oth if r in lab])
    if syn:
        P("\n## Synthetic Supersede tasks (exact grading)\n")
        P("Each task is asked two questions from the same memory: the current value (Supersede's query) and "
          "the previous value (the value just before the current one). Both configs pooled.")
        acc_table("synth_current", syn, "cur")
        acc_table("synth_history", syn, "hist")
        for s in ("synth_std", "synth_hard"):
            G = [r for r in syn if r["set"] == s]
            for qk in ("cur", "hist"):
                arms = present(G, qk)
                P(f"\n{s} {qk} (n={len(G)}), mean correct over 2 reps: " +
                  ", ".join(f"{a} {sum(sum(score(r, a, qk)) for r in G) / 2:g}" for a in arms))
        P("\nVerdict breakdown, synthetic, both reps summed (correct / stale / ambiguous / wrong):\n")
        P("| arm | current: allergy | current: other | history: allergy | history: other |")
        P("|---|---|---|---|---|")
        for a in present(syn, "hist"):
            cells = []
            for qk in ("cur", "hist"):
                for G in ([r for r in syn if "allergic" in r["question"]], [r for r in syn if "allergic" not in r["question"]]):
                    c = Counter(r["reps"][rep]["arms"][f"{a}|{qk}"]["verdict"] for r in G for rep in REPS)
                    cells.append(f"{c['correct']} / {c['stale']} / {c['ambiguous']} / {c['wrong']} (2x{len(G)})")
            P(f"| {a} | " + " | ".join(cells) + " |")

    # ---------------------------------------------------------------- stores, orphan keys, cost
    P("\n## Stores and orphan keys\n")
    for name, G in (("lme", lme), ("synthetic", syn)):
        if not G:
            continue
        P(f"\n### {name}\n")
        P("| store | rep | keys | versions | keys with history | audit: tasks with a duplicate group | audit: redundant keys per task | exact: orphaned chains | exact: orphan holds a stale value | exact: queried fact has correct previous version |")
        P("|---|---|---|---|---|---|---|---|---|---|")
        for unit in ("extract", "extract_canon"):
            for rep in REPS:
                S = [r["reps"][rep]["stores"][unit] for r in G]
                n = len(S)
                mean = lambda f: sum(s.get(f, 0) for s in S) / n
                aud = [s for s in S if "audit_groups" in s]
                a1 = f"{sum(s['audit_groups'] > 0 for s in aud)}/{len(aud)}" if aud else "n/a"
                a2 = f"{sum(s['audit_redundant'] for s in aud) / len(aud):.2f}" if aud else "n/a"
                if name == "synthetic":
                    ch = sum(s["chains"] for s in S)
                    e1 = f"{sum(s['orphan_chains'] for s in S)}/{ch}"
                    e2 = f"{sum(s['stale_alive'] for s in S)}/{ch}"
                    e3 = f"{sum(s['queried_history_ok'] for s in S)}/{n}"
                else:
                    e1 = e2 = e3 = "n/a"
                label = "E4 extractor" if unit == "extract" else "canonical-key extractor"
                summary.setdefault("stores", {})[f"{name}|{unit}|{rep}"] = {
                    "keys": mean("n_keys"), "versions": mean("n_versions"), "multi": mean("multi_version_keys"),
                    "audit_tasks": a1, "audit_redundant": a2, "orphan_chains": e1, "stale_alive": e2, "q_hist_ok": e3}
                P(f"| {label} | {rep} | {mean('n_keys'):.1f} | {mean('n_versions'):.1f} | {mean('multi_version_keys'):.2f} | "
                  f"{a1} | {a2} | {e1} | {e2} | {e3} |")
    P("\nCost per task (rep 2, all calls fresh; memory building plus the current-value answer call; excludes grading):\n")
    P("| arm | lme: mean input tokens | lme: mean output tokens | lme: calls | synthetic: mean input tokens | synthetic: calls |")
    P("|---|---|---|---|---|---|")
    for arm in ARMS:
        cells = []
        for G in (lme, syn):
            X = [r["reps"][2]["arms"].get(f"{arm}|cur") for r in G]
            X = [x for x in X if x and "tok_in" in x]
            if X:
                cells.append((sum(x["tok_in"] for x in X) / len(X), sum(x["tok_out"] for x in X) / len(X),
                              sum(x["calls"] for x in X) / len(X)))
            else:
                cells.append(None)
        f = lambda c, i, fmt: (fmt.format(c[i]) if c else "n/a")
        P(f"| {arm} | {f(cells[0], 0, '{:,.0f}')} | {f(cells[0], 1, '{:,.0f}')} | {f(cells[0], 2, '{:.1f}')} | "
          f"{f(cells[1], 0, '{:,.0f}')} | {f(cells[1], 2, '{:.1f}')} |")

    # ---------------------------------------------------------------- repeat noise
    P("\n## Repeat noise\n")
    P("Fraction of (task, question) verdicts that differ between rep 1 and rep 2, per arm and set:\n")
    P("| arm | lme | synthetic current | synthetic history |")
    P("|---|---|---|---|")
    for arm in ARMS:
        cells = []
        for G, qk in ((lme, "cur"), (syn, "cur"), (syn, "hist")):
            X = [score(r, arm, qk) for r in G if all(f"{arm}|{qk}" in r["reps"][rep]["arms"] for rep in REPS)]
            cells.append(f"{sum(x[0] != x[1] for x in X)}/{len(X)}" if X else "n/a")
        P(f"| {arm} | " + " | ".join(cells) + " |")

    # ---------------------------------------------------------------- judge validation
    hl = HERE / "results" / "hand_labels.json"
    if hl.exists():
        smp = {(x["rep"], x["qid"], x["arm"]): x for x in json.loads((HERE / "results" / "hand_label_sample.json").read_text())}
        hp = [(smp[(x["rep"], x["qid"], x["arm"])]["judge_yes"], x["hand_correct"]) for x in json.loads(hl.read_text())["labels"]]
        ag = sum(a == b for a, b in hp)
        summary["hand_labels"] = {"n": len(hp), "agree": ag, "kappa": kappa(hp)}
        P(f"\n## Judge validation\n\nHand labels on {len(hp)} LongMemEval verdicts: agreement {ag}/{len(hp)}, Cohen's kappa {kappa(hp):.3f}.")
        for x in json.loads(hl.read_text())["labels"]:
            s = smp[(x["rep"], x["qid"], x["arm"])]
            if s["judge_yes"] != x["hand_correct"]:
                P(f"- disagreement: rep {x['rep']} {x['qid']} {x['arm']}: judge {'yes' if s['judge_yes'] else 'no'}, "
                  f"hand {'yes' if x['hand_correct'] else 'no'}. {x.get('note', '')}")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    (out_dir / "tables.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
