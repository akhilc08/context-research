"""Regenerate every E26 table from the raw result files (standard library plus detectors.py).

Usage: python3 analyze.py > results/tables.md
"""
import collections, json, math, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import detectors as D  # noqa: E402
import methods as M  # noqa: E402

ORDER = ["nopolicy", "hist", "compact", "pin", "pinrules", "watch", "recipe", "minimal", "recipe_noprog",
         "compact_prog"] + M.ADDED_ARMS
CONFIRM = [("recipe", "compact", "sup"), ("minimal", "compact", "sup"), ("recipe", "pin", "sup"),
           ("minimal", "pin", "sup"), ("recipe", "hist", "ni")]
MARGIN = 0.03
EXTRA = [("recipe", "recipe_noprog"), ("compact_prog", "compact"), ("minimal", "compact_prog"),
         ("recipe_ckpt", "recipe")] + [(a, "pin") for a in M.ADDED_ARMS]


def load(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def sign_p(k, n):
    if n == 0:
        return 1.0
    pk = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, sum(p for p in pk if p <= pk[k] + 1e-12))


def boot(diffs, reps=2000, seed=0):
    rng = random.Random(seed)
    n = len(diffs)
    if not n:
        return float("nan"), float("nan")
    ms = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return ms[int(0.025 * reps)], ms[int(0.975 * reps) - 1]


def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-30 else 1e-30)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-30 else 1e-30
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-30 else 1e-30
        de = d * c
        h *= de
        if abs(de - 1) < 1e-12:
            break
    return h


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t, df):
    p = 0.5 * betainc(df / 2, 0.5, df / (df + t * t))
    return p if t < 0 else 1 - p


def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(idx):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def paired(by_arm, a, b, val, kind="sup", exclude=()):
    va = {(r["task"], r["trial"]): val(r) for r in by_arm.get(a, []) if r["task"] not in exclude}
    vb = {(r["task"], r["trial"]): val(r) for r in by_arm.get(b, []) if r["task"] not in exclude}
    shared = sorted(set(va) & set(vb))
    tasks = sorted({t for t, _ in shared})
    ma, mb = {}, {}
    for t in tasks:
        ks = [k for k in shared if k[0] == t]
        ma[t] = sum(va[k] for k in ks) / len(ks)
        mb[t] = sum(vb[k] for k in ks) / len(ks)
    w = sum(ma[t] > mb[t] for t in tasks)
    l = sum(ma[t] < mb[t] for t in tasks)
    n = max(1, len(tasks))
    diffs = [ma[t] - mb[t] for t in tasks]
    res = {"a": a, "b": b, "kind": kind, "tasks": len(tasks), "runs": len(shared), "w": w, "l": l,
           "ra": sum(ma.values()) / n, "rb": sum(mb.values()) / n, "ci": boot(diffs),
           "b10": sum(1 for k in shared if va[k] and not vb[k]), "b01": sum(1 for k in shared if vb[k] and not va[k])}
    if kind == "ni":
        mean = sum(diffs) / n
        sd = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (n - 1)) if n > 1 else 0.0
        se = sd / math.sqrt(n)
        p1 = (0.0 if mean < MARGIN else 1.0) if se == 0 else t_cdf((mean - MARGIN) / se, n - 1)
        res["p"] = min(1.0, 2 * p1)
        res["p1"] = p1
    else:
        res["p"] = sign_p(w, w + l)
    return res


def comparisons_table(fams, title, what, note=""):
    print(f"\n## {title}\n")
    print(f"Paired over tasks on each task's mean {what} across shared trials; difference with paired bootstrap "
          f"95% CI over tasks; Holm across all rows of this table. {note}\n")
    print("| domain | comparison | type | tasks | a higher / b higher (tasks) | runs a only / b only | rate a | rate b | "
          "difference (95% CI) | p | Holm p |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    allres = [(d, x) for d, xs in fams for x in xs]
    adj = holm([x["p"] for _, x in allres])
    for (d, x), pa in zip(allres, adj):
        typ = f"non-inferiority (margin +{MARGIN*100:.0f})" if x["kind"] == "ni" else "two-sided sign"
        print(f"| {d} | {x['a']} vs {x['b']} | {typ} | {x['tasks']} | {x['w']} / {x['l']} | {x['b10']} / {x['b01']} | "
              f"{x['ra']:.3f} | {x['rb']:.3f} | {x['ra']-x['rb']:+.3f} ({x['ci'][0]:+.3f} to {x['ci'][1]:+.3f}) | "
              f"{x['p']:.3g} | {pa:.3g} |")
    return allres, adj


def pass_k(rs, k):
    per = collections.defaultdict(list)
    for r in rs:
        per[r["task"]].append(r["reward"])
    vals = [math.comb(sum(x >= 1 for x in v), k) / math.comb(len(v), k) for v in per.values() if len(v) >= k]
    return sum(vals) / len(vals) if vals else float("nan")


def words(r):
    s = [len((c.get("summary") or "").split()) for c in r["compactions"] if c.get("summary")]
    return s


def main():
    data = {}
    for d in ("retail", "airline"):
        p = HERE / f"results/{d}.jsonl"
        if p.exists():
            data[d] = load(p)
    print("# E26 tables (generated by analyze.py from results/retail.jsonl and results/airline.jsonl)")
    fams = collections.defaultdict(list)
    for dom, rows in data.items():
        for r in rows:
            r["_d"] = D.analyze(r)
            r["_v"] = int(D.primary_violation(r, r["_d"]))
            r["_vf"] = int(D.primary_violation(r, fixed=True))
            r["_c"] = int("confirm" in r["_d"]["run"])
        by_arm = collections.defaultdict(list)
        for r in rows:
            by_arm[r["arm"]].append(r)
        arms = [a for a in ORDER if a in by_arm]
        print(f"\n# {dom}\n")
        print("## Per arm (all runs of the arm)\n")
        print("| arm | trials | runs | violation rate (95% CI) | violation rate, trial 0 | corrected detector | "
              "reward (95% CI) | pass^2 | model calls/run | agent calls/run | input tok/run | output tok/run | "
              "API calls/run | compactions/run | summary words (mean) |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for a in arms:
            rs = by_arm[a]
            n = len(rs)
            kv, kr = sum(r["_v"] for r in rs), sum(r["reward"] >= 1 for r in rs)
            lv, hv = wilson(kv, n)
            lr, hr = wilson(kr, n)
            t0 = [r["_v"] for r in rs if r["trial"] == 0]
            ws = [w for r in rs for w in words(r)]
            print(f"| {a} | {len({r['trial'] for r in rs})} | {n} | {kv/n:.3f} ({lv:.3f} to {hv:.3f}) | "
                  f"{sum(t0)/max(1,len(t0)):.3f} | {sum(r['_vf'] for r in rs)/n:.3f} | "
                  f"{kr/n:.3f} ({lr:.3f} to {hr:.3f}) | {pass_k(rs, 2):.3f} | "
                  f"{sum(sum(r['calls'].values()) for r in rs)/n:.1f} | {sum(r['calls'].get('agent', 0) for r in rs)/n:.1f} | "
                  f"{sum(sum(r['tok_in'].values()) for r in rs)/n:,.0f} | {sum(sum(r['tok_out'].values()) for r in rs)/n:,.0f} | "
                  f"{sum(r['api_calls'] for r in rs)/n:.1f} | {sum(r['n_compactions'] for r in rs)/n:.2f} | "
                  f"{(sum(ws)/len(ws)) if ws else float('nan'):.0f} |")
        cats = D.PRIMARY[dom] + D.SECONDARY
        print(f"\n## {dom}: share of runs where each detector fires\n")
        print("| arm | " + " | ".join(cats) + " | runs with a write | writes/run |")
        print("|---|" + "---|" * (len(cats) + 2))
        for a in arms:
            rs = by_arm[a]
            n = len(rs)
            print(f"| {a} | " + " | ".join(f"{sum(c in r['_d']['run'] for r in rs)/n:.3f}" for c in cats) +
                  f" | {sum(1 for r in rs if r['_d']['writes'])/n:.3f} | {sum(len(r['_d']['writes']) for r in rs)/n:.2f} |")
        fams["conf"].append((dom, [paired(by_arm, a, b, lambda r: r["_v"], k) for a, b, k in CONFIRM]))
        fams["rew"].append((dom, [paired(by_arm, a, b, lambda r: r["reward"]) for a, b, _ in CONFIRM]))
        fams["fix"].append((dom, [paired(by_arm, a, b, lambda r: r["_vf"], k) for a, b, k in CONFIRM]))
        fams["cfm"].append((dom, [paired(by_arm, a, b, lambda r: r["_c"], k) for a, b, k in CONFIRM]))
        fams["sens"].append((dom, [paired(by_arm, a, b, lambda r: r["_v"], k, D.GOLD_CONFLICT.get(dom, set()))
                                   for a, b, k in CONFIRM]))
        fams["board"].append((dom, [paired(by_arm, a, "compact", lambda r: r["_v"]) for a in arms if a != "compact"]))
        fams["board_rew"].append((dom, [paired(by_arm, a, "compact", lambda r: r["reward"]) for a in arms if a != "compact"]))
        fams["extra"].append((dom, [paired(by_arm, a, b, lambda r: r["_v"]) for a, b in EXTRA
                                    if a in by_arm and b in by_arm]))
        # method-specific diagnostics
        print(f"\n## {dom}: method diagnostics\n")
        for a in ("recipe", "minimal", "compact_prog", "recipe_ckpt"):
            cs = [c for r in by_arm.get(a, []) for c in r["compactions"] if c.get("progress")]
            if cs:
                pend = sum("Proposed by the agent and not executed yet: \"" in c["progress"] for c in cs)
                exe = sum("do not repeat it):\n" in c["progress"] for c in cs)
                auth = sum("Authenticated customer: none" not in c["progress"] for c in cs)
                print(f"- {a}: {len(cs)} progress blocks; with an authenticated customer {auth/len(cs):.2f}, "
                      f"with an executed write {exe/len(cs):.2f}, with a pending proposal {pend/len(cs):.2f}")
        cs = [c for r in by_arm.get("roundtrip", []) for c in r["compactions"] if "rt" in c]
        if cs:
            fired = sum(c["rt"]["score"] >= M.RT_THRESHOLD for c in cs)
            print(f"- roundtrip: {len(cs)} checks, mean score {sum(c['rt']['score'] for c in cs)/len(cs):.2f}, "
                  f"fired (recompacted) {fired} ({fired/len(cs):.2f}); runs with any firing "
                  f"{sum(any(c['rt']['score'] >= M.RT_THRESHOLD for c in r['compactions']) for r in by_arm['roundtrip'])}"
                  f" of {len(by_arm['roundtrip'])}")
        for a in ("selfcheck", "watch"):
            cs = [c for r in by_arm.get(a, []) for c in r["compactions"] if "patched" in c]
            if cs:
                pat = [len(c["patched"]) for c in cs]
                print(f"- {a}: {len(cs)} checks, rules re-attached per check {sum(pat)/len(pat):.2f}, "
                      f"checks that re-attached nothing {sum(p == 0 for p in pat)/len(pat):.2f}")
                if a == "selfcheck":
                    print(f"  - self-check said the confirmation rule (rule 2 retail / rule 1 airline) was still active in "
                          f"{sum(c['covered'][2 if dom == 'retail' else 1] for c in cs)/len(cs):.2f} of checks")
        # reward failure source
        print(f"\n## {dom}: reward failure source\n")
        print("| arm | failed | wrong DB state | DB right, missing output | max steps |")
        print("|---|---|---|---|---|")
        for a in arms:
            fl = [r for r in by_arm[a] if r["reward"] < 1]
            db = sum(1 for r in fl if r["done"] and "r_actions" in ((r.get("reward_info") or {}).get("info") or {}))
            ms = sum(1 for r in fl if not r["done"])
            print(f"| {a} | {len(fl)} | {db} | {len(fl)-db-ms} | {ms} |")
    comparisons_table(fams["conf"], "Primary: confirmatory comparisons on process-violation presence (Holm over 10)",
                      "violation presence", "H5 (recipe vs hist) is a non-inferiority test: one-sided paired t-test "
                      "against a +3 point margin, one-sided p doubled before Holm.")
    comparisons_table(fams["rew"], "Secondary: the confirmatory comparisons on τ-bench reward", "reward")
    comparisons_table(fams["fix"], "Secondary: confirmatory comparisons with E22's corrected confirmation detector",
                      "violation presence")
    comparisons_table(fams["cfm"], "Secondary: the confirmation detector alone", "confirm-flag presence")
    comparisons_table(fams["sens"], "Sensitivity: confirmatory comparisons without tasks whose gold actions trip a detector",
                      "violation presence")
    comparisons_table(fams["board"], "Exploratory leaderboard: every arm vs compact (Holm across both domains)",
                      "violation presence", "One-trial arms are paired with compact's trial 0 only.")
    comparisons_table(fams["board_rew"], "Exploratory leaderboard on reward: every arm vs compact", "reward")
    comparisons_table(fams["extra"], "Exploratory pairs (Holm shown only for reference; read unadjusted p)",
                      "violation presence")


if __name__ == "__main__":
    main()
