"""Regenerate every E18 table from graded raw outputs (no model calls).

Usage: python3 analyze.py [--model MODEL]   -> prints tables and writes results/tables_<slug>.md

Pre-registered (fixed before probe results were read):
  Primary metric: wrong-but-confident rate, the share of probes whose COMMAND carries a concrete wrong
  value for the identifier, pooled over R in {1, 3, 6, 10} and both budgets.
  H1. Under plain recursive compaction, identifiers are mutated (not only dropped): summary mutation
      rate > 0, and plain's wrong-but-confident rate exceeds full context.
  H2. Mutation compounds: the mutated share grows from R=1 to R=10 (paired McNemar per identifier).
  H3. Each fix (verbatim prompt, registry, registry with recency, pin operator turns) lowers the
      wrong-but-confident rate relative to plain. Holm correction across the 6 primary comparisons
      (full vs plain at 120 and 300, and the four fixes vs plain).
  H4. Registry with recency beats plain registry on superseded and distractor identifiers.
"""
import argparse, collections, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import wilson  # noqa: E402

MODEL = "stealth/space-bunny-alpha"
ROUNDS = [1, 3, 6, 10]
ARMS = ["full", "plain", "verbatim", "registry", "registry_rec", "pin_op"]
OUT = []


def p(s=""):
    print(s)
    OUT.append(s)


def r(k, n):
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% [{100 * lo:.0f}, {100 * hi:.0f}] ({k}/{n})"


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    slug = a.model.replace("/", "_").replace(":", "_")
    d = HERE / "data" / slug
    GS = [json.loads(l) for l in (d / "graded_summaries.jsonl").read_text().splitlines()]
    GP = [json.loads(l) for l in (d / "graded_probes.jsonl").read_text().splitlines()]
    p(f"# E18 tables ({a.model})\n")

    # ------------------------------------------------ summary-level fate
    p("## Summary-level fate of planted identifiers (deterministic check + near-match judge)\n")
    p("| summarizer | budget | R | kept | partial | mutated | dropped |")
    p("|---|---|---|---|---|---|---|")
    for s in ["plain", "verbatim"]:
        for w in [120, 300]:
            for R in ROUNDS:
                xs = [g for g in GS if g["summarizer"] == s and g["budget"] == w and g["round"] == R]
                c = collections.Counter(g["status"] for g in xs)
                p(f"| {s} | {w} | {R} | " + " | ".join(r(c[k], len(xs)) for k in ["kept", "partial", "mutated", "dropped"]) + " |")
    p()

    # mutation among identifiers still present in some form (kept, partial or mutated)
    p("Mutated share among identifiers still stated with a value (mutated / (kept + partial + mutated)):\n")
    p("| summarizer | budget | R=1 | R=3 | R=6 | R=10 |")
    p("|---|---|---|---|---|---|")
    for s in ["plain", "verbatim"]:
        for w in [120, 300]:
            row = []
            for R in ROUNDS:
                xs = [g for g in GS if g["summarizer"] == s and g["budget"] == w and g["round"] == R and g["status"] != "dropped"]
                row.append(r(sum(g["status"] == "mutated" for g in xs), len(xs)))
            p(f"| {s} | {w} | " + " | ".join(row) + " |")
    p()

    # by type and by condition (plain summaries, rounds 1 to 10 all pooled)
    for key in ["type", "cond"]:
        p(f"### Plain summaries by {key}, rounds 1 to 10 and both budgets pooled\n")
        p(f"| {key} | kept | partial | mutated | dropped |")
        p("|---|---|---|---|---|")
        groups = collections.defaultdict(list)
        for g in GS:
            if g["summarizer"] == "plain":
                groups[g[key]].append(g)
        for k in sorted(groups, key=lambda k: -sum(g["status"] == "mutated" for g in groups[k]) / len(groups[k])):
            c = collections.Counter(g["status"] for g in groups[k])
            p(f"| {k} | " + " | ".join(r(c[s], len(groups[k])) for s in ["kept", "partial", "mutated", "dropped"]) + " |")
        p()

    p("### Mutation kinds (all summaries, rounds 1 to 10)\n")
    p("| summarizer | kind | count |")
    p("|---|---|---|")
    for s in ["plain", "verbatim"]:
        c = collections.Counter(g["kind"] for g in GS if g["summarizer"] == s and g["status"] == "mutated")
        for k, v in c.most_common():
            p(f"| {s} | {k} | {v} |")
    p()

    # compounding: trajectories
    p("### Compounding over rounds (per identifier chain, rounds 1 to 10)\n")
    traj = collections.defaultdict(dict)
    for g in GS:
        traj[(g["scenario"], g["budget"], g["summarizer"], g["type"])][g["round"]] = g
    for s in ["plain", "verbatim"]:
        ts = {k: v for k, v in traj.items() if k[2] == s}
        ever_mut = sum(any(v[R]["status"] == "mutated" for R in v) for v in ts.values())
        trans = collections.Counter()
        for v in ts.values():
            for R in range(2, 11):
                trans[(v[R - 1]["status"], v[R]["status"])] += 1
        mut_next = sum(n for (x, y), n in trans.items() if x == "mutated")
        p(f"- {s}: {ever_mut} of {len(ts)} identifier chains are mutated in at least one round. "
          f"Transitions out of 'mutated' to the next round: " +
          ", ".join(f"{y} {n}" for (x, y), n in sorted(trans.items()) if x == "mutated") + f" (total {mut_next}). "
          f"Into 'mutated' from: " + ", ".join(f"{x} {n}" for (x, y), n in sorted(trans.items()) if y == "mutated" and x != "mutated") + ". "
          f"Into 'kept' from 'dropped' (recovery): {trans[('dropped', 'kept')]}.")
        b = sum(1 for v in ts.values() if v[1]["status"] != "mutated" and v[10]["status"] == "mutated")
        c_ = sum(1 for v in ts.values() if v[1]["status"] == "mutated" and v[10]["status"] != "mutated")
        p(f"  H2 McNemar, mutated at R=10 vs R=1: {b} newly mutated, {c_} no longer mutated, exact p = {mcnemar(b, c_):.3g}.")
    p()

    # ------------------------------------------------ probes
    p("## Behavioral probe: identifier in the agent's next command\n")
    P = collections.defaultdict(list)
    for g in GP:
        P[(g["arm"], g["budget"], g["R"])].append(g)
    outs = ["correct", "partial", "ask_known", "ask", "missing", "wrong"]
    p("ask_known: the agent asked about something else but its question already states the correct value.\n")
    p("| arm | budget | R | correct | partial | ask_known | ask | missing | wrong (harm) |")
    p("|---|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        for w in ([None] if arm == "full" else [120, 300]):
            for R in ROUNDS:
                xs = P[(arm, w, R)]
                c = collections.Counter(g["outcome"] for g in xs)
                p(f"| {arm} | {w or '-'} | {R} | " + " | ".join(r(c[o], len(xs)) for o in outs) + " |")
    p()

    p("### Pooled over R and budgets (primary table)\n")
    p("| arm | n | correct | wrong (harm) | ask or missing | mean context tokens (chars/4) | added harness tokens |")
    p("|---|---|---|---|---|---|---|")
    for arm in ARMS:
        xs = [g for g in GP if g["arm"] == arm]
        c = collections.Counter(g["outcome"] for g in xs)
        ctx = sum(g["ctx_chars"] for g in xs) / len(xs) / 4
        ext = sum(g["extra_chars"] for g in xs) / len(xs) / 4
        p(f"| {arm} | {len(xs)} | {r(c['correct'], len(xs))} | {r(c['wrong'], len(xs))} | "
          f"{r(c['ask'] + c['missing'], len(xs))} | {ctx:.0f} | {ext:.0f} |")
    p()

    # paired tests
    idx = {(g["arm"], g["budget"], g["R"], g["scenario"], g["type"]): g for g in GP}
    keys = sorted({(g["budget"], g["R"], g["scenario"], g["type"]) for g in GP if g["arm"] == "plain"})

    def paired(arm_a, arm_b, metric, budgets=(120, 300), types=None, conds=None):
        b = c = n = 0
        for (w, R, s, t) in keys:
            if w not in budgets:
                continue
            if types and t not in types:
                continue
            ga = idx.get((arm_a, None if arm_a == "full" else w, R, s, t))
            gb = idx.get((arm_b, None if arm_b == "full" else w, R, s, t))
            if not ga or not gb:
                continue
            if conds and ga["cond"] not in conds:
                continue
            xa, xb = metric(ga), metric(gb)
            n += 1
            b += xa and not xb
            c += xb and not xa
        return b, c, n

    wrong = lambda g: g["outcome"] == "wrong"  # noqa: E731
    correct = lambda g: g["outcome"] == "correct"  # noqa: E731
    comps = [("full", "plain", (120,)), ("full", "plain", (300,))] + [(f, "plain", (120, 300)) for f in ["verbatim", "registry", "registry_rec", "pin_op"]]
    wrong_det = lambda g: g["outcome"] == "wrong" and g["judge"] is None  # noqa: E731
    for name, metric in [("wrong (harm), primary", wrong),
                         ("wrong, deterministic only (judge-decided wrongs counted as missing; sensitivity)", wrong_det),
                         ("correct, secondary", correct)]:
        res = [paired(x, y, metric, bud) for x, y, bud in comps]
        ps = [mcnemar(b, c) for b, c, n in res]
        adj = holm(ps)
        p(f"### Paired McNemar, {name}, Holm across 6 comparisons\n")
        p("| comparison | budgets | n pairs | A only | plain only | rate A | rate plain | p | Holm p |")
        p("|---|---|---|---|---|---|---|---|---|")
        for (x, y, bud), (b, c, n), pv, pa in zip(comps, res, ps, adj):
            ra = sum(metric(idx[(x, None if x == 'full' else w, R, s, t)]) for (w, R, s, t) in keys if w in bud)
            rb = sum(metric(idx[(y, w, R, s, t)]) for (w, R, s, t) in keys if w in bud)
            p(f"| {x} vs {y} | {'/'.join(map(str, bud))} | {n} | {b} | {c} | {100 * ra / n:.1f}% | {100 * rb / n:.1f}% | {pv:.3g} | {pa:.3g} |")
        p()

    p("### H4: registry with recency vs plain registry, superseded and distractor identifiers (wrong rate)\n")
    for conds in [("superseded",), ("distractor",)]:
        b, c, n = paired("registry_rec", "registry", wrong, conds=conds)
        ra = sum(1 for g in GP if g["arm"] == "registry_rec" and g["cond"] in conds and wrong(g))
        rb = sum(1 for g in GP if g["arm"] == "registry" and g["cond"] in conds and wrong(g))
        p(f"- {conds[0]}: registry_rec wrong {ra}/{n}, registry wrong {rb}/{n}; discordant {b} vs {c}, exact p = {mcnemar(b, c):.3g}")
    p()

    for key in ["type", "cond"]:
        p(f"### Wrong-but-confident rate by {key} and arm (pooled R and budgets)\n")
        p(f"| {key} | " + " | ".join(ARMS) + " |")
        p("|---|" + "---|" * len(ARMS))
        for k in sorted({g[key] for g in GP}):
            row = []
            for arm in ARMS:
                xs = [g for g in GP if g["arm"] == arm and g[key] == k]
                row.append(f"{100 * sum(wrong(g) for g in xs) / len(xs):.0f}% ({sum(wrong(g) for g in xs)}/{len(xs)})")
            p(f"| {k} | " + " | ".join(row) + " |")
        p()

    p("### What wrong values were (all arms)\n")
    p("| arm | wrong kind | count |")
    p("|---|---|---|")
    for arm in ARMS:
        c = collections.Counter(g["wrong_kind"] for g in GP if g["arm"] == arm and g["outcome"] == "wrong")
        for k, v in c.most_common():
            p(f"| {arm} | {k} | {v} |")
    p()

    # exploratory: where wrong values come from
    S = {s["id"]: s for s in json.loads((HERE / "data" / "scenarios.json").read_text())}
    p("### Exploratory: source of wrong values (deterministically extracted wrong values only)\n")
    p("borrowed = the wrong value appears verbatim somewhere in the session transcript (distractor, old value, "
      "or an unrelated identifier from other work); invented = it appears nowhere in the transcript.\n")
    p("| arm | borrowed: distractor or old value | borrowed: other identifier in session | invented |")
    p("|---|---|---|---|")
    for arm in ARMS:
        c = collections.Counter()
        for g in GP:
            if g["arm"] != arm or g["outcome"] != "wrong" or not g.get("wrong_value"):
                continue
            txt = "\n".join(S[g["scenario"]]["turns"])
            if g["wrong_kind"] in ("distractor_swap", "stale_value"):
                c["near"] += 1
            elif g["wrong_value"] in txt:
                c["other"] += 1
            else:
                c["invented"] += 1
        p(f"| {arm} | {c['near']} | {c['other']} | {c['invented']} |")
    p()

    # link summary state to behavior (plain arm)
    p("### Summary state at R vs probe outcome, plain arm\n")
    gsi = {(g["scenario"], g["budget"], g["summarizer"], g["round"], g["type"]): g for g in GS}
    link = collections.defaultdict(collections.Counter)
    for g in GP:
        if g["arm"] != "plain":
            continue
        st = gsi[(g["scenario"], g["budget"], "plain", g["R"], g["type"])]["status"]
        link[st][g["outcome"]] += 1
    p("| summary status | n | correct | partial | ask_known | ask | missing | wrong |")
    p("|---|---|---|---|---|---|---|---|")
    for st in ["kept", "partial", "mutated", "dropped"]:
        n = sum(link[st].values())
        p(f"| {st} | {n} | " + " | ".join(r(link[st][o], n) for o in outs) + " |")
    p()

    # ------------------------------------------------ judge validation
    p("## Judge validation (blind labels by the study agent)\n")
    for name in ["summary_judge", "probe_judge"]:
        f = d / f"labels_{name}.json"
        if not f.exists():
            p(f"- {name}: no labels file")
            continue
        L = json.loads(f.read_text())
        hl = [x["hand"] for x in L]
        jl = [x["judge"] for x in L]
        agree = sum(x == y for x, y in zip(hl, jl))
        p(f"- {name}: n = {len(L)}, agreement {agree}/{len(L)}, Cohen's kappa = {kappa(hl, jl):.2f}; "
          f"judge YES {sum(jl)}, hand YES {sum(hl)}")
    p()
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"tables_{slug}.md").write_text("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
