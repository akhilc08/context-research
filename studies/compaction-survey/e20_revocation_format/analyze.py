"""Regenerate every E20 table from results/<model>/graded.jsonl, blocks.json, and the hand labels.
No model calls. Usage: python3 analyze.py [--model MODEL]  -> results/<model>/tables.md
"""
import argparse, collections, json, math, random

import e20lib as L
from formats import FORMATS

TYPES = ["active", "revoked", "loosen", "tighten", "amended", "rule_state"]

# Planned comparisons, fixed after the 3-session pilot and before the main run. (A, B, cond A, cond B, type)
PLANNED = [
    ("a_delete", "b_ledger", "clean", "clean", "revoked"),
    ("c_permit", "b_ledger", "clean", "clean", "revoked"),
    ("d_label", "b_ledger", "clean", "clean", "revoked"),
    ("c_permit", "a_delete", "clean", "clean", "revoked"),
    ("g_struck", "f_raw", "clean", "clean", "revoked"),
    ("a_delete", "f_raw", "clean", "clean", "revoked"),
    ("b_ledger", "a_delete", "clean", "clean", "active"),
    ("c_permit", "a_delete", "clean", "clean", "active"),
    ("e_wasnow", "a_delete", "clean", "clean", "amended"),
    ("b_ledger", "a_delete", "clean", "clean", "amended"),
    ("a_delete", "a_delete", "stale", "clean", "revoked"),
    ("c_permit", "a_delete", "stale", "stale", "revoked"),
    ("d_label", "a_delete", "stale", "stale", "revoked"),
    ("c_permit", "d_label", "stale", "stale", "revoked"),
    ("g_struck", "f_raw", "stale", "stale", "revoked"),
    ("e_wasnow", "a_delete", "stale", "stale", "amended"),
]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, ps[i] * (len(ps) - r)))
        adj[i] = run
    return adj


def pct(k, n):
    if not n:
        return "n/a"
    lo, hi = L.wilson(k, n)
    return f"{100 * k / n:.0f}% [{100 * max(0, lo):.0f} to {100 * min(1, hi):.0f}]"


def fmtp(p):
    return "<1e-15" if p < 1e-15 else (f"{p:.0e}" if p < 0.001 else f"{p:.3f}" if p < 0.1 else f"{p:.2f}")


def in_type(r, t):
    if t == "rule_state":
        return True
    if t == "amended":
        return r["ptype"] == "amended"
    if t in ("loosen", "tighten"):
        return r["ptype"] == "amended" and r.get("direction") == t
    return r["ptype"] == t


def key(r):
    return (r["sid"], r["ptype"], r["idx"], r["sample"])


def table(rows, cond, field="correct"):
    out = ["| format | " + " | ".join(TYPES) + " |", "|---" * (len(TYPES) + 1) + "|"]
    for f in FORMATS:
        cells = []
        for t in TYPES:
            xs = [r[field] for r in rows if r["cond"] == cond and r["fmt"] == f and in_type(r, t)]
            cells.append(pct(sum(xs), len(xs)))
        out.append(f"| {f} | " + " | ".join(cells) + " |")
    return out


def boot_diff(pairs, n_boot=2000, seed=20):
    """Session-cluster bootstrap CI for the difference in correct rate (A minus B)."""
    by = collections.defaultdict(list)
    for sid, a, b in pairs:
        by[sid].append(a - b)
    sids = sorted(by)
    rng = random.Random(seed)
    ds = []
    for _ in range(n_boot):
        xs = [x for s in (rng.choice(sids) for _ in sids) for x in by[s]]
        ds.append(sum(xs) / len(xs))
    ds.sort()
    return ds[int(0.025 * n_boot)], ds[int(0.975 * n_boot)]


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    a = ap.parse_args()
    outdir = L.HERE / "results" / L.slug(a.model)
    rows = [json.loads(l) for l in (outdir / "graded.jsonl").read_text().splitlines() if l.strip()]
    blocks = json.loads((outdir / "blocks.json").read_text())
    idx = {(r["cond"], r["fmt"]) + key(r): r for r in rows}
    md = [f"# E20 tables ({a.model})", "", f"{len(rows)} graded decisions, "
          f"{len({r['sid'] for r in rows})} sessions. Wilson 95% CIs (not adjusted for clustering).", ""]

    for cond in ("clean", "stale"):
        md += [f"## Correct rate, {cond} summary (judged action, primary)", ""] + table(rows, cond) + [""]
    for cond in ("clean", "stale"):
        md += [f"## Failure modes, {cond} summary", "",
               "Over-refusal = revoked or loosened rule applied (APPLIES). Under-enforcement = active or tightened "
               "rule not applied (IGNORES). OTHER = unclear or unrelated hold.", "",
               "| format | revoked: over-refusal | revoked: OTHER | active: under-enforced | active: OTHER | "
               "loosen: over-refusal | tighten: under-enforced |", "|---|---|---|---|---|---|---|"]
        for f in FORMATS:
            def rate(t, lab):
                xs = [r for r in rows if r["cond"] == cond and r["fmt"] == f and in_type(r, t)]
                return pct(sum(r["label"] == lab for r in xs), len(xs))
            md.append(f"| {f} | {rate('revoked', 'APPLIES')} | {rate('revoked', 'OTHER')} | "
                      f"{rate('active', 'IGNORES')} | {rate('active', 'OTHER')} | {rate('loosen', 'APPLIES')} | "
                      f"{rate('tighten', 'IGNORES')} |")
        md.append("")

    # planned comparisons
    res = []
    for fa, fb, ca, cb, t in PLANNED:
        pairs = []
        for r in rows:
            if r["cond"] == ca and r["fmt"] == fa and in_type(r, t):
                o = idx.get((cb, fb) + key(r))
                if o is not None:
                    pairs.append((r["sid"], int(r["correct"]), int(o["correct"])))
        b = sum(1 for _, x, y in pairs if x and not y)
        c = sum(1 for _, x, y in pairs if y and not x)
        lo, hi = boot_diff(pairs)
        n = len(pairs)
        res.append(dict(a=f"{fa} ({ca})", b=f"{fb} ({cb})", t=t, n=n, pa=sum(x for _, x, _ in pairs) / n,
                        pb=sum(y for _, _, y in pairs) / n, b_=b, c_=c, p=mcnemar(b, c), lo=lo, hi=hi))
    adj = holm([r["p"] for r in res])
    md += ["## Planned comparisons (exact McNemar on paired decisions, Holm over 16)", "",
           "Pairs match session, probe, and sample index. The difference CI is a session-cluster bootstrap "
           "(2,000 resamples), which allows for repeated samples and probes within a session.", "",
           "| # | A | B | type (pairs) | A | B | A-only / B-only | diff [cluster 95% CI] | raw p | Holm p |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for i, (r, p) in enumerate(zip(res, adj), 1):
        md.append(f"| {i} | {r['a']} | {r['b']} | {r['t']} ({r['n']}) | {100 * r['pa']:.0f}% | {100 * r['pb']:.0f}% "
                  f"| {r['b_']} / {r['c_']} | {100 * (r['pa'] - r['pb']):+.0f} [{100 * r['lo']:+.0f} to "
                  f"{100 * r['hi']:+.0f}] | {fmtp(r['p'])} | {fmtp(p)} |")
    md.append("")

    # sensitivity: drop revoked items whose permission sentence was hand-edited (exploratory)
    rw = json.loads((L.HERE / "data" / "rewrites.json").read_text())
    edited = sorted(k for k, v in rw.items() if v.get("override"))
    md += ["## Sensitivity: revoked items with hand-edited permissions removed (exploratory)", "",
           f"Removed items: {', '.join(edited)}. Same pairing and tests as above, unadjusted p.", "",
           "| A | B | pairs | A | B | A-only / B-only | p |", "|---|---|---|---|---|---|---|"]
    for fa, fb, ca, cb in [("c_permit", "a_delete", "clean", "clean"), ("c_permit", "b_ledger", "clean", "clean"),
                           ("c_permit", "d_label", "clean", "clean"), ("c_permit", "d_label", "stale", "stale"),
                           ("c_permit", "f_raw", "clean", "clean"), ("c_permit", "f_raw", "stale", "stale")]:
        pairs = []
        for r in rows:
            if r["cond"] == ca and r["fmt"] == fa and r["ptype"] == "revoked" and r["item"] not in edited:
                o = idx[(cb, fb) + key(r)]
                pairs.append((int(r["correct"]), int(o["correct"])))
        b = sum(1 for x, y in pairs if x and not y)
        c = sum(1 for x, y in pairs if y and not x)
        n = len(pairs)
        md.append(f"| {fa} ({ca}) | {fb} ({cb}) | {n} | {100 * sum(x for x, _ in pairs) / n:.0f}% | "
                  f"{100 * sum(y for _, y in pairs) / n:.0f}% | {b} / {c} | {fmtp(mcnemar(b, c))} |")
    md.append("")

    # secondary: DECISION line
    for cond in ("clean", "stale"):
        md += [f"## Secondary: DECISION line only, {cond} summary", ""] + table(rows, cond, "correct_decision") + [""]
    agree = collections.Counter((r["ptype"], r["correct"] == r["correct_decision"]) for r in rows)
    md += ["Judge and DECISION line agree on: " + ", ".join(
        f"{t} {100 * agree[(t, True)] / max(1, agree[(t, True)] + agree[(t, False)]):.0f}%"
        for t in ("active", "revoked", "amended")), ""]

    # tokens
    md += ["## Tokens per format (word count x 1.33)", "",
           "| format | mean block tokens | mean full context tokens (clean) |", "|---|---|---|"]
    for f in FORMATS:
        bt = [v["tokens"] for k, v in blocks.items() if k.endswith("|" + f)]
        ct = [r["context_tokens"] for r in rows if r["fmt"] == f and r["cond"] == "clean"]
        md.append(f"| {f} | {sum(bt) / len(bt):.0f} | {sum(ct) / max(1, len(ct)):.0f} |")
    md.append("")

    # per-item revoked accuracy (exploratory)
    md += ["## Revoked accuracy by item (exploratory, clean / stale)", "",
           "| item | n per cell | " + " | ".join(FORMATS[1:]) + " |", "|---" * (len(FORMATS) + 1) + "|"]
    items = sorted({r["item"] for r in rows if r["ptype"] == "revoked"})
    for it in items:
        cells, nn = [], 0
        for f in FORMATS[1:]:
            v = []
            for cond in ("clean", "stale"):
                xs = [r["correct"] for r in rows if r["ptype"] == "revoked" and r["item"] == it and r["fmt"] == f and r["cond"] == cond]
                nn = len(xs)
                v.append(f"{sum(xs)}/{len(xs)}")
            cells.append(" ".join(v))
        md.append(f"| {it} | {nn} | " + " | ".join(cells) + " |")
    md.append("")

    # judge validation
    hp, sp = L.HERE / "hand_labels.json", L.HERE / "hand_sample.json"
    if hp.exists() and sp.exists():
        hand = json.loads(hp.read_text())
        samp = {x["hid"]: x for x in json.loads(sp.read_text())}
        js = [samp[h]["judge_label"] for h in hand]
        hs = [hand[h]["label"] for h in hand]
        po, k = kappa(js, hs)
        conf = collections.Counter(zip(js, hs))
        md += ["## Judge validation (blind hand labels by the study agent)", "",
               f"n = {len(hs)}, agreement {100 * po:.0f}%, Cohen's kappa {k:.2f}", "",
               "| judge \\ hand | " + " | ".join(["APPLIES", "IGNORES", "OTHER"]) + " |", "|---|---|---|---|"]
        for jl in ("APPLIES", "IGNORES", "OTHER"):
            md.append(f"| {jl} | " + " | ".join(str(conf[(jl, hl)]) for hl in ("APPLIES", "IGNORES", "OTHER")) + " |")
        md.append("")
    (outdir / "tables.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
