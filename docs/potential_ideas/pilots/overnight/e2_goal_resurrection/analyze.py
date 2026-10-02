"""Regenerate every E2 table from raw files.

Inputs: results/trials*.jsonl (raw per-trial records), data/hand_labels.json (my hand labels),
../usage.jsonl (token usage, matched by trial id in the call tag).
Usage: python3 analyze.py [results/trials.jsonl]  (writes results/analysis.txt as well as printing)
"""
import collections, io, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import wilson, fisher_two_sided  # noqa: E402

HERE = Path(__file__).resolve().parent
METHODS = ["full", "plain", "anchor", "pin", "pin_clean", "watchpoint", "selfcheck", "floor"]
POS = ["early", "mid", "late"]
out = io.StringIO()


def P(*a):
    print(*a)
    print(*a, file=out)


def rate(k, n):
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} {100*k/n:.0f}% [{max(0, 100*lo):.0f}, {min(100, 100*hi):.0f}]"


def mcnemar(x, y):
    """Exact two-sided McNemar (sign test on discordant pairs). x, y: lists of bools."""
    b = sum(1 for a, c in zip(x, y) if a and not c)
    c = sum(1 for a, d in zip(x, y) if not a and d)
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return b, c, min(1.0, p)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0] * len(ps), 0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((sum(x == k for x in a) / n) * (sum(y == k for y in b) / n) for k in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def outcome(t, j):
    if j is None:
        return "none"
    if j == t["latest"]:
        return "current"
    return "stale_prev" if j == t["latest"] - 1 else "stale_older"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results" / "trials.jsonl"
    T = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    P(f"# E2 analysis from {path.name}: {len(T)} trials, {len({t['scenario'] for t in T})} scenarios, "
      f"model(s) {sorted({t['model'] for t in T})}")

    def ok(t, m):
        return t["arms"][m]["judge_A"] == t["latest"]

    # ---- main table
    P("\n## Current-goal rate (judge phrasing A), n and 95% Wilson CI")
    for m in METHODS:
        row = [m.ljust(11)]
        for p in POS + ["all"]:
            sub = [t for t in T if p == "all" or t["position"] == p]
            row.append(rate(sum(ok(t, m) for t in sub), len(sub)))
        P(" | ".join(row))

    P("\n## Outcome breakdown, all positions pooled (current / stale previous / stale older / none)")
    for m in METHODS:
        c = collections.Counter(outcome(t, t["arms"][m]["judge_A"]) for t in T)
        older_n = sum(1 for t in T if t["latest"] >= 2)
        P(f"{m.ljust(11)} current {rate(c['current'], len(T))} | stale_prev {rate(c['stale_prev'], len(T))} | "
          f"stale_older {rate(c['stale_older'], older_n)} (of chains with an older goal) | none {rate(c['none'], len(T))}")

    P("\n## Stale-goal rate by position")
    for m in METHODS:
        row = [m.ljust(11)]
        for p in POS:
            sub = [t for t in T if t["position"] == p]
            row.append(rate(sum(outcome(t, t["arms"][m]["judge_A"]).startswith("stale") for t in sub), len(sub)))
        P(" | ".join(row))

    P("\n## Current-goal rate by chain length (all positions)")
    for g in sorted({t["n_goals"] for t in T}):
        sub = [t for t in T if t["n_goals"] == g]
        P(f"{g} goals: " + " | ".join(f"{m} {rate(sum(ok(t, m) for t in sub), len(sub))}"
                                     for m in ["plain", "anchor", "pin", "watchpoint"]))

    # ---- paired tests
    P("\n## Paired comparisons on current-goal success, all positions pooled (exact McNemar; Holm over the family)")
    pairs = [("pin", "watchpoint"), ("watchpoint", "plain"), ("pin", "plain"), ("anchor", "plain"),
             ("pin", "anchor"), ("watchpoint", "anchor"), ("pin_clean", "pin"), ("watchpoint", "selfcheck"),
             ("full", "pin")]
    res = []
    for a, b in pairs:
        x = [ok(t, a) for t in T]; y = [ok(t, b) for t in T]
        bb, cc, p = mcnemar(x, y)
        fp = fisher_two_sided(sum(x), len(x), sum(y), len(y))
        res.append((a, b, sum(x), sum(y), len(T), bb, cc, p, fp))
    adj = holm([r[7] for r in res])
    for r, pa in zip(res, adj):
        a, b, sa, sb, n, bb, cc, p, fp = r
        P(f"{a} vs {b}: {sa}/{n} vs {sb}/{n}; discordant {a}-only {bb}, {b}-only {cc}; "
          f"McNemar p={p:.3g}, Holm p={pa:.3g}; unpaired Fisher p={fp:.3g}")

    P("\n## Exploratory: per-position paired tests (no correction)")
    for p in POS:
        sub = [t for t in T if t["position"] == p]
        for a, b in [("pin", "watchpoint"), ("watchpoint", "plain"), ("pin", "plain"), ("anchor", "plain")]:
            bb, cc, pv = mcnemar([ok(t, a) for t in sub], [ok(t, b) for t in sub])
            P(f"{p} {a} vs {b}: {a}-only {bb}, {b}-only {cc}, p={pv:.3g}")

    # ---- detector behaviour
    P("\n## Patch rates")
    for d in ["watchpoint", "selfcheck"]:
        P(d.ljust(11) + " | ".join(f"{p} {rate(sum(t[d]['patched'] for t in T if t['position'] == p), sum(t['position'] == p for t in T))}"
                                    for p in POS) + f" | all {rate(sum(t[d]['patched'] for t in T), len(T))}")
    P("\n## Selectivity: patch rate split by whether the plain arm (same summary) failed")
    for d in ["watchpoint", "selfcheck"]:
        fail = [t for t in T if not ok(t, "plain")]; succ = [t for t in T if ok(t, "plain")]
        P(f"{d}: patch | plain failed {rate(sum(t[d]['patched'] for t in fail), len(fail))}; "
          f"patch | plain succeeded {rate(sum(t[d]['patched'] for t in succ), len(succ))}")
    P("\n## Comparator vs independent judge on the extracted objective sentence")
    cm = collections.Counter((t["watchpoint"]["extracted_judged"] == t["latest"], not t["watchpoint"]["patched"]) for t in T)
    P(f"judge says extraction is current & comparator says match: {cm[(True, True)]}; current & mismatch (needless patch): "
      f"{cm[(True, False)]}; not current & match (missed drift): {cm[(False, True)]}; not current & mismatch (caught): {cm[(False, False)]}")
    ext = collections.Counter(outcome(t, t["watchpoint"]["extracted_judged"]) for t in T)
    P(f"extraction outcome distribution: {dict(ext)}")

    P("\n## Stale conflict: does a stale goal in the summary compete with the pin?")
    stale_sum = [t for t in T if outcome(t, t["watchpoint"]["extracted_judged"]).startswith("stale")]
    clean_sum = [t for t in T if t["watchpoint"]["extracted_judged"] == t["latest"]]
    for name, sub in [("summary conveys a stale goal (by judged extraction)", stale_sum),
                      ("summary conveys the current goal", clean_sum)]:
        P(f"{name}: n={len(sub)}; pin {rate(sum(ok(t, 'pin') for t in sub), len(sub))}; "
          f"pin_clean {rate(sum(ok(t, 'pin_clean') for t in sub), len(sub))}; "
          f"plain {rate(sum(ok(t, 'plain') for t in sub), len(sub))}; watchpoint {rate(sum(ok(t, 'watchpoint') for t in sub), len(sub))}")

    # ---- judge validation
    P("\n## Judge self-consistency (phrasing A vs B over every graded action)")
    a = [str(t["arms"][m]["judge_A"]) for t in T for m in METHODS]
    b = [str(t["arms"][m]["judge_B"]) for t in T for m in METHODS]
    P(f"agreement {sum(x == y for x, y in zip(a, b))}/{len(a)} = {100*sum(x == y for x, y in zip(a, b))/len(a):.1f}%, "
      f"Cohen kappa {kappa(a, b):.3f}")
    for m in METHODS:
        P(f"  current-goal rate under phrasing B, {m}: {rate(sum(t['arms'][m]['judge_B'] == t['latest'] for t in T), len(T))}")
    hl = HERE / "data" / "hand_labels.json"
    if hl.exists():
        H = json.loads(hl.read_text())
        idx = {t["tid"]: t for t in T}
        H = [h for h in H if h["tid"] in idx]
        if H:
            ja = [str(idx[h["tid"]]["arms"][h["method"]]["judge_A"]) for h in H]
            hb = [str(h["label"]) for h in H]
            agree = sum(x == y for x, y in zip(ja, hb))
            P(f"\n## Hand labels vs judge A: {agree}/{len(H)} = {100*agree/len(H):.1f}% agreement, kappa {kappa(hb, ja):.3f}")
            cur_h = [y == str(idx[h['tid']]['latest']) for h, y in zip(H, hb)]
            cur_j = [x == str(idx[h['tid']]['latest']) for h, x in zip(H, ja)]
            P(f"binary current-vs-not agreement {sum(x == y for x, y in zip(cur_h, cur_j))}/{len(H)}, "
              f"kappa {kappa([str(x) for x in cur_h], [str(x) for x in cur_j]):.3f}")
            for h, x, y in zip(H, ja, hb):
                if x != y:
                    P(f"  disagreement {h['tid']} {h['method']}: judge {x}, me {y}")

    # ---- cost
    P("\n## Cost per trial (mean): model calls and tokens attributable to each method")
    usage = collections.defaultdict(lambda: [0, 0, 0])
    tids = {t["tid"] for t in T}
    for l in (HERE.parent / "usage.jsonl").read_text().splitlines():
        try:
            u = json.loads(l)
        except json.JSONDecodeError:
            continue
        if "|" not in u.get("tag", "") or not u["tag"].startswith("e2_"):
            continue
        tag, tid = u["tag"].split("|", 1)
        if tid in tids:
            usage[tag][0] += 1; usage[tag][1] += u["in"] or 0; usage[tag][2] += u["out"] or 0
    n = len(T)
    comp = {k: usage[f"e2_compact_{k}"] for k in ["plain", "anchor", "clean"]}
    extra = {"watchpoint": [usage["e2_wp_extract"], usage["e2_wp_compare"]], "selfcheck": [usage["e2_selfcheck"]]}
    for m in METHODS:
        if m == "full":
            c = [0, 0, 0]
        else:
            c = list(comp["anchor" if m == "anchor" else "clean" if m in ("pin_clean", "floor") else "plain"])
        for e in extra.get(m, []):
            c = [c[0] + e[0], c[1] + e[1], c[2] + e[2]]
        ctx = sum(t["arms"][m]["ctx_chars"] for t in T) / n / 4
        P(f"{m.ljust(11)} compaction+check calls {c[0]/n:.2f}, tokens in {c[1]/n:.0f} out {c[2]/n:.0f}; "
          f"agent decision context ~{ctx:.0f} tokens (chars/4)")
    (HERE / "results" / ("analysis.txt" if path.name == "trials.jsonl" else f"analysis_{path.stem}.txt")).write_text(out.getvalue())


if __name__ == "__main__":
    main()
