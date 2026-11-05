"""Analyze E27. Regenerates results/tables.md, results/summary.json, results/per_task.json.

    /private/tmp/supersede-venv/bin/python analyze.py [--model <backbone>]
"""
import argparse, json, math, random, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/private/tmp/supersede/src")
from supersede.scoring import classify                       # noqa: E402

E14_META = HERE.parent / "e14_versioned_pin" / "results" / "tasks_meta.json"
E4_SUMMARY = HERE.parent / "e04_supersede" / "results" / "summary.json"
USAGE = HERE.parent / "shared" / "usage.jsonl"
SEEDED = {"notes300", "notes1200", "extract", "extract_canon"} | {f"ans_{a}" for a in
                                                                 ["full", "notes300", "notes1200", "pin", "vpin", "vpin_canon"]}
ARMS = ["full", "notes300", "notes1200", "tm", "vpin_canon", "minimal", "recipe", "r_nopin", "r_novblock",
        "fifo1200", "headtail1200", "fifo_tm", "headtail_tm", "mask", "resum", "struct", "carry", "prov300", "anchor",
        "watch", "watch_strict", "watch_self", "roundtrip", "repair", "pin", "vpin", "ledger", "registry"]
COST = {"full": [], "notes300": ["notes300"], "notes1200": ["notes1200"], "tm": ["notes_tm*"],
        "vpin_canon": ["notes300", "extract_canon"], "minimal": ["notes300"],
        "recipe": ["pnotes", "extract_canon", "keeper"], "r_nopin": ["pnotes", "extract_canon"],
        "r_novblock": ["pnotes", "keeper"], "mask": [], "resum": ["resum"], "pin": ["notes300", "extract"],
        "vpin": ["notes300", "extract"], "repair": ["notes300", "repair"], "ledger": ["notes300", "ledger"],
        "registry": ["notes300", "extract"], "watch": ["watch", "extract"], "watch_strict": ["watch_strict", "extract"],
        "watch_self": ["watch_self", "extract"], "roundtrip": ["roundtrip"],
        **{v: [f"notes_{v}"] for v in ("struct", "carry", "prov300", "anchor")},
        **{a: [] for a in ("fifo1200", "headtail1200", "fifo_tm", "headtail_tm")}}
CONFIRM = [("recipe", "notes1200", "sup"), ("recipe", "vpin_canon", "ni"), ("recipe", "full", "ni"),
           ("minimal", "notes1200", "sup")]
SECONDARY = [("recipe", "r_nopin"), ("recipe", "r_novblock"), ("recipe", "tm"), ("recipe", "minimal"),
             ("minimal", "vpin_canon"), ("recipe", "notes1200"), ("minimal", "notes1200"), ("recipe", "vpin_canon"),
             ("recipe", "full")]
MARGIN = 0.03


def sign_test(a, b):
    x = sum(1 for i, j in zip(a, b) if i > j)
    y = sum(1 for i, j in zip(a, b) if j > i)
    n = x + y
    if n == 0:
        return x, y, 1.0
    return x, y, min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n)


def ni_perm(d, margin=MARGIN, B=100_000, seed=0):
    """One-sided sign-flip test of H0: mean(d) <= -margin."""
    s = [x + margin for x in d]
    obs = sum(s)
    rng = random.Random(seed)
    hits = sum(1 for _ in range(B) if sum(x if rng.random() < 0.5 else -x for x in s) >= obs - 1e-12)
    return (hits + 1) / (B + 1)


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
        if len(p) == 6 and p[0] in ("e14", "e27") and p[2].endswith(prefix) and ("@" in p[2]) == bool(prefix):
            s = p[2][:len(p[2]) - len(prefix)] if prefix else p[2]
            last[(p[0], p[1], s, p[3], p[4], p[5])] = r
    tok = defaultdict(lambda: [0, 0, 0])
    for (src, rep, s, q, unit, kind), r in last.items():
        if unit.startswith("ans_") and kind != "cur":
            continue
        u = "notes_tm*" if unit.startswith("notes_tm") else unit
        k = tok[(src, rep, s, q, u)]
        k[0] += r.get("in") or 0; k[1] += r.get("out") or 0; k[2] += 1
    return tok


def unit_cost(tok, s, q, unit, prefix):
    """Fresh-call cost of one unit: E14 rep 2 for copied units, else E27 rep 2, else E27 rep 1."""
    if unit in SEEDED and not prefix:
        return tok.get(("e14", "rep2", s, q, unit), (0, 0, 0))
    for rep in ("rep2", "rep1"):
        if (("e27", rep, s, q, unit)) in tok:
            return tok[("e27", rep, s, q, unit)]
    return (0, 0, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    a = ap.parse_args()
    units, prefix, out = HERE / "results" / "units", "", HERE / "results"
    if a.model != "stealth/space-bunny-alpha":
        safe = re.sub(r"[^\w]+", "_", a.model)
        units, prefix, out = HERE / "results" / f"units_{safe}", f"@{safe}", HERE / "results" / f"analysis_{safe}"
        out.mkdir(exist_ok=True)
    meta = [t for t in json.loads(E14_META.read_text()) if t["set"] == "lme" or int(t["qid"].split("_")[1]) % 1000 < 30]
    hist_qids = set(json.loads(E4_SUMMARY.read_text())["lme_history_split"]["hist_qids"])
    tok = load_usage(prefix)

    per = []
    for t in meta:
        rec = {k: t.get(k) for k in ("set", "qid", "question", "answer", "hist_answer")}
        rec["is_hist"] = t["qid"] in hist_qids
        rec["arms"] = {}
        for rep in (1, 2):
            d = units / f"rep{rep}" / t["set"] / t["qid"]
            jd = json.loads((d / "judge.json").read_text()) if (d / "judge.json").exists() else {}
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
                        r.update(correct=jd[arm]["yes"], v4=jd[arm].get("v4"), labeled=bool(jd.get("stale_label")))
                        r.update(stale=r["v4"] == "stale", amb=r["v4"] == "ambiguous")
                    else:
                        gold, wrong = (t["answer"], t["stale"]) if qk == "cur" else (t["hist_answer"], t["hist_wrong"])
                        v = classify(u["answer"], gold, wrong)
                        r.update(verdict=v, correct=v == "correct", stale=v == "stale", amb=v == "ambiguous")
                    rec["arms"].setdefault(f"{arm}|{qk}", {})[rep] = r
        per.append(rec)
    (out / "per_task.json").write_text(json.dumps(per, indent=1))

    lines, summary = [], {}
    P = lines.append

    def reps_of(R, arm, qk):
        """Repeats available for every task in R (both, or rep 1 only)."""
        for reps in ((1, 2), (1,)):
            if R and all(all(rp in r["arms"].get(f"{arm}|{qk}", {}) for rp in reps) for r in R):
                return reps
        return None

    def m(r, arm, qk, reps, f="correct"):
        return sum(int(r["arms"][f"{arm}|{qk}"][rp][f]) for rp in reps) / len(reps)

    def cost(G, arm):
        X = []
        for r in G:
            ti = to = c = 0
            for unit in COST[arm] + [f"ans_{arm}"]:
                i_, o_, c_ = unit_cost(tok, r["set"], r["qid"], unit, prefix)
                ti += i_; to += o_; c += c_
            X.append((ti, to, c))
        X = [x for x in X if x[2]]
        return tuple(sum(x[i] for x in X) / len(X) for i in range(3)) if X else None

    def board(name, R, qk, base="notes300", with_cost=True):
        S = summary.setdefault(name, {"n": len(R), "arms": {}, "vs_base": {}})
        arms = [x for x in ARMS if reps_of(R, x, qk)]
        P(f"\n### {name} (n={len(R)})\n")
        P("| arm | repeats | mean accuracy | 95% CI | stale | ambiguous | memory chars | input tokens per task | output tokens | calls | vs " + base + ": tasks higher / lower | Holm p |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|")
        rows, tests = [], []
        for arm in arms:
            reps = reps_of(R, arm, qk)
            sc = [m(r, arm, qk, reps) for r in R]
            lab = [r for r in R if r["set"] != "lme" or r["arms"][f"{arm}|{qk}"][reps[0]].get("labeled")]
            st = sum(m(r, arm, qk, reps, "stale") for r in lab)
            am = sum(m(r, arm, qk, reps, "amb") for r in lab)
            mc = sum(r["arms"][f"{arm}|{qk}"][rp]["memory_chars"] for r in R for rp in reps) / (len(R) * len(reps))
            c = cost(R, arm) if with_cost else None
            br = reps_of(R, base, qk)
            t = None
            if arm != base and br:
                t = sign_test(sc, [m(r, base, qk, br) for r in R])
                tests.append((arm, t))
            rows.append((arm, reps, sc, st, am, len(lab), mc, c, t))
        hp = dict(zip([x for x, _ in tests], holm([t[2] for _, t in tests])))
        for arm, reps, sc, st, am, nl, mc, c, t in sorted(rows, key=lambda x: -sum(x[2])):
            lo, hi = boot(sc)
            acc = sum(sc) / len(sc)
            S["arms"][arm] = {"reps": len(reps), "acc": acc, "ci": [lo, hi], "stale": st, "amb": am, "n_labeled": nl,
                              "memory_chars": mc, "cost": c}
            if t:
                S["vs_base"][arm] = {"higher": t[0], "lower": t[1], "p": t[2], "p_holm": hp[arm]}
            cc = (f"{c[0]:,.0f} | {c[1]:,.0f} | {c[2]:.1f}" if c else "n/a | n/a | n/a")
            vs = f"{t[0]} / {t[1]} | {hp[arm]:.3g}" if t else "base | "
            P(f"| {arm} | {len(reps)} | {acc:.1%} | {lo:.0%} to {hi:.0%} | {st:g}/{nl} | {am:g}/{nl} | {mc:,.0f} | {cc} | {vs} |")

    def compare(name, R, qk, pairs):
        P(f"\n{name}:\n")
        P("| A vs B | mean A, B | tasks A higher / B higher | sign test p | mean difference, 95% CI |")
        P("|---|---|---|---|---|")
        for x, y in pairs:
            rx, ry = reps_of(R, x, qk), reps_of(R, y, qk)
            if not (rx and ry):
                continue
            a_, b_ = [m(r, x, qk, rx) for r in R], [m(r, y, qk, ry) for r in R]
            xo, yo, p = sign_test(a_, b_)
            lo, hi = boot([u - v for u, v in zip(a_, b_)])
            summary.setdefault("secondary", {})[f"{name}|{x}-{y}"] = {"a": sum(a_), "b": sum(b_), "higher": xo, "lower": yo, "p": p, "ci": [lo, hi]}
            P(f"| {x} vs {y} | {sum(a_):g}, {sum(b_):g} | {xo} / {yo} | {p:.3g} | {lo:+.1%} to {hi:+.1%} |")

    lme = [r for r in per if r["set"] == "lme"]
    syn = [r for r in per if r["set"] != "lme"]

    # ---------------------------------------------------------------- confirmatory
    P("## Confirmatory comparisons (LongMemEval accuracy, Holm over 4)\n")
    P("| test | A, B mean correct | tasks A higher / B higher | test p | Holm p | mean difference, 95% CI | supported |")
    P("|---|---|---|---|---|---|---|")
    res = []
    for x, y, kind in CONFIRM:
        rx, ry = reps_of(lme, x, "cur"), reps_of(lme, y, "cur")
        if not (rx and ry):
            continue
        a_, b_ = [m(r, x, "cur", rx) for r in lme], [m(r, y, "cur", ry) for r in lme]
        xo, yo, p = sign_test(a_, b_)
        if kind == "ni":
            p = ni_perm([u - v for u, v in zip(a_, b_)])
        res.append((x, y, kind, sum(a_), sum(b_), xo, yo, p, boot([u - v for u, v in zip(a_, b_)])))
    for (x, y, kind, sa, sb, xo, yo, p, (lo, hi)), ph in zip(res, holm([r[7] for r in res])):
        lab = f"{x} {'beats' if kind == 'sup' else 'non-inferior to'} {y}"
        ok = ph < 0.05 and (kind == "ni" or sa > sb)
        summary.setdefault("confirmatory", {})[f"{x}-{y}"] = {"kind": kind, "a": sa, "b": sb, "higher": xo, "lower": yo,
                                                            "p": p, "p_holm": ph, "ci": [lo, hi], "supported": ok}
        P(f"| {lab} | {sa:g}, {sb:g} | {xo} / {yo} | {p:.3g} | {ph:.3g} | {lo:+.1%} to {hi:+.1%} | {'yes' if ok else 'no'} |")
    P(f"\nNon-inferiority tests use a one-sided sign-flip permutation test with a {MARGIN:.0%} margin (100,000 resamples); "
      "superiority tests use an exact two-sided sign test on per-task means over the two repeats.")

    # ---------------------------------------------------------------- leaderboards
    P("\n## Leaderboards\n")
    P("Cost is per task: memory building plus the current-value answer call, from fresh calls (E14 repeat 2 for copied units). "
      "Stale and ambiguous are means over repeats; on LongMemEval they come from E4's four-way judge on the tasks with a wrong-version label. "
      "The comparison column is the pre-registered exploratory family (every arm vs notes300, exact sign test, Holm within the table).")
    board("lme_all", lme, "cur")
    board("lme_history", [r for r in lme if r["is_hist"]], "cur", with_cost=False)
    board("lme_current", [r for r in lme if not r["is_hist"]], "cur", with_cost=False)
    if syn:
        board("synth_current", syn, "cur")
        board("synth_history", syn, "hist", with_cost=False)
        for s in ("synth_std", "synth_hard"):
            G = [r for r in syn if r["set"] == s]
            for qk in ("cur", "hist"):
                P(f"\n{s} {qk} (n={len(G)}), mean correct: " + ", ".join(
                    f"{x} {sum(m(r, x, qk, reps_of(G, x, qk)) for r in G):g}" for x in ARMS if reps_of(G, x, qk)))

    # ---------------------------------------------------------------- secondary
    P("\n## Secondary comparisons (no correction)\n")
    compare("lme_all", lme, "cur", SECONDARY)
    compare("lme_history", [r for r in lme if r["is_hist"]], "cur", SECONDARY)
    if syn:
        compare("synth_current", syn, "cur", SECONDARY)
        compare("synth_history", syn, "hist", SECONDARY)

    # ---------------------------------------------------------------- keeper and repeat noise
    P("\n## Keeper and pin size\n")
    for name, G in (("lme", lme), ("synthetic", syn)):
        sel = tot = 0
        for r in G:
            for rep in (1, 2):
                p = units / f"rep{rep}" / r["set"] / r["qid"] / "keeper.json"
                if p.exists():
                    k = json.loads(p.read_text())
                    sel += sum(len(x) for x in k["selected"]); tot += sum(k["n_user"])
        if tot:
            summary.setdefault("keeper", {})[name] = {"selected": sel, "total": tot}
            P(f"- {name}: the keeper kept {sel} of {tot} user turns ({sel / tot:.0%}) across both repeats.")
    P("\n## Repeat noise (verdicts that differ between repeats)\n")
    P("| arm | lme | synthetic current | synthetic history |")
    P("|---|---|---|---|")
    for arm in ARMS:
        cells = []
        for G, qk in ((lme, "cur"), (syn, "cur"), (syn, "hist")):
            X = [r["arms"][f"{arm}|{qk}"] for r in G if len(r["arms"].get(f"{arm}|{qk}", {})) == 2]
            cells.append(f"{sum(x[1]['correct'] != x[2]['correct'] for x in X)}/{len(X)}" if X else "n/a")
        P(f"| {arm} | " + " | ".join(cells) + " |")

    hl = HERE / "results" / "hand_labels.json"
    if hl.exists():
        H = json.loads(hl.read_text())["labels"]
        pairs = [(x["judge_yes"], x["hand_correct"]) for x in H]
        summary["hand_labels"] = {"n": len(pairs), "agree": sum(a == b for a, b in pairs), "kappa": kappa(pairs)}
        P(f"\n## Judge validation\n\nHand labels on {len(pairs)} new LongMemEval verdicts: agreement "
          f"{sum(a == b for a, b in pairs)}/{len(pairs)}, Cohen's kappa {kappa(pairs):.3f}.")
        for x in H:
            if x["judge_yes"] != x["hand_correct"]:
                P(f"- rep {x['rep']} {x['qid']} {x['arm']}: judge {'yes' if x['judge_yes'] else 'no'}, hand "
                  f"{'yes' if x['hand_correct'] else 'no'}. {x.get('note', '')}")
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    (out / "tables.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
