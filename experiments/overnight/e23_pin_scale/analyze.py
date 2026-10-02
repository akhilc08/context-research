"""Regenerate every E23 table and the plot from raw outputs (no model calls).

Usage: python3 analyze.py [--model MODEL]
Writes results/<model>/tables.md and results/<model>/accuracy_tokens_vs_M.svg.
"""
import argparse, json, math, re, statistics, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import wilson  # noqa: E402

DEFAULT_MODEL = "stealth/space-bunny-alpha"
ARMS = ["full", "plain", "pin_raw", "pin_directive", "pin_consol", "ledger"]
MS = [25, 50, 100, 200]
PTYPES = ["active", "revoked", "amended", "rule_state", "goal", "plan", "fact_current", "fact_history", "overall"]
RULE = ("active", "revoked", "amended")
# Planned comparisons, fixed before the main run: (arm A, M A, arm B, M B, probe type). Holm over all.
PLANNED = [
    ("pin_raw", 200, "pin_raw", 25, "rule_state"),
    ("pin_raw", 200, "plain", 200, "rule_state"),
    ("pin_directive", 200, "pin_raw", 200, "rule_state"),
    ("pin_consol", 200, "pin_raw", 200, "rule_state"),
    ("ledger", 200, "pin_raw", 200, "rule_state"),
    ("pin_raw", 200, "full", 200, "rule_state"),
    ("full", 200, "full", 25, "rule_state"),
    ("pin_directive", 200, "pin_raw", 200, "goal"),
    ("pin_consol", 200, "pin_raw", 200, "goal"),
    ("ledger", 200, "pin_raw", 200, "goal"),
    ("pin_consol", 200, "pin_raw", 200, "fact_history"),
]
EXPLORATORY = [
    ("pin_raw", 200, "pin_raw", 25, "goal"),
    ("pin_directive", 200, "pin_directive", 25, "goal"),
    ("plain", 200, "plain", 25, "goal"),
    ("full", 200, "full", 25, "goal"),
    ("pin_consol", 200, "pin_consol", 25, "goal"),
    ("ledger", 200, "ledger", 25, "goal"),
    ("ledger", 200, "pin_consol", 200, "rule_state"),
    ("ledger", 200, "pin_consol", 200, "goal"),
]


def slug(model):
    return "space_bunny" if model == DEFAULT_MODEL else re.sub(r"[^A-Za-z0-9]+", "_", model)


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


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
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f}% [{100 * max(0, lo):.0f} to {100 * min(1, hi):.0f}]"


def fmtp(p):
    return f"{p:.2g}" if p >= 0.001 else f"{p:.0e}"


def kappa(a, b):
    n = len(a)
    if not n:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def read_jsonl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()] if Path(p).exists() else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    out = HERE / "results" / slug(a.model)
    rows = read_jsonl(out / "graded.jsonl")
    sess = {f.stem: json.loads(f.read_text()) for f in sorted((out / "sessions").glob("M*.json"))}
    truth = {s["sid"]: s for s in json.loads((HERE / "data" / "sessions.json").read_text())}
    md = [f"# E23 tables ({a.model})", ""]

    def cell(arm, M, pt):
        if pt == "rule_state":
            rs = [r for r in rows if r["arm"] == arm and r["M"] == M and r["ptype"] in RULE]
        elif pt == "overall":
            rs = [r for r in rows if r["arm"] == arm and r["M"] == M]
        else:
            rs = [r for r in rows if r["arm"] == arm and r["M"] == M and r["ptype"] == pt]
        return rs

    nb = {M: len({r["base"] for r in rows if r["M"] == M}) for M in MS}
    md.append("Sessions graded per M: " + ", ".join(f"M={M}: {nb[M]}" for M in MS))
    md.append("")
    # ---------------------------------------------------------------- primary table
    md += ["## Rule-state accuracy by arm and M (Wilson 95% CI)", "",
           "| arm | " + " | ".join(f"M={M}" for M in MS) + " |", "|---|" + "---|" * len(MS)]
    acc = {}
    for arm in ARMS:
        cells = []
        for M in MS:
            rs = cell(arm, M, "rule_state")
            k = sum(r["correct"] for r in rs)
            acc[(arm, M)] = (k, len(rs))
            cells.append(pct(k, len(rs)))
        md.append(f"| {arm} | " + " | ".join(cells) + " |")
    md.append("")
    for pt in PTYPES:
        if pt == "rule_state":
            continue
        md += [f"### {pt}", "", "| arm | " + " | ".join(f"M={M}" for M in MS) + " |", "|---|" + "---|" * len(MS)]
        for arm in ARMS:
            md.append(f"| {arm} | " + " | ".join(pct(sum(r["correct"] for r in cell(arm, M, pt)), len(cell(arm, M, pt)))
                                                 for M in MS) + " |")
        md.append("")
    md += ["### Amended rules by direction (pooled over M)", "", "| arm | loosen | tighten |", "|---|---|---|"]
    for arm in ARMS:
        c = []
        for d in ("loosen", "tighten"):
            rs = [r for r in rows if r["arm"] == arm and r["ptype"] == "amended" and r.get("direction") == d]
            c.append(pct(sum(r["correct"] for r in rs), len(rs)))
        md.append(f"| {arm} | {c[0]} | {c[1]} |")
    md.append("")
    md += ["### Plan probe labels (pooled over M)", "", "| arm | correct_next | repeat | skip | verify | other |",
           "|---|---|---|---|---|---|"]
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm and r["ptype"] == "plan"]
        md.append(f"| {arm} | " + " | ".join(str(sum(r["label"] == l for r in rs))
                                             for l in ("correct_next", "repeat", "skip", "verify", "other")) + " |")
    md.append("")
    md += ["### Goal probe labels (pooled over M)", "", "| arm | current | stale | procedure | none |", "|---|---|---|---|---|"]
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm and r["ptype"] == "goal"]
        md.append(f"| {arm} | " + " | ".join(str(sum(r["label"] == l for r in rs))
                                             for l in ("current", "stale", "procedure", "none")) + " |")
    md.append("")
    md += ["### Rule state scored by the DECISION line only (secondary)", "",
           "| arm | " + " | ".join(f"M={M}" for M in MS) + " |", "|---|" + "---|" * len(MS)]
    for arm in ARMS:
        md.append(f"| {arm} | " + " | ".join(pct(sum(r["correct_decision"] for r in cell(arm, M, "rule_state")),
                                                 len(cell(arm, M, "rule_state"))) for M in MS) + " |")
    md.append("")

    # ---------------------------------------------------------------- planned comparisons
    idx = {(r["arm"], r["M"], r["base"], r["ptype"], r["idx"]): r["correct"] for r in rows}
    res = []
    for A, MA, B, MB, pt in PLANNED:
        types = RULE if pt == "rule_state" else (pt,)
        b = c = ka = kb = n = 0
        for (arm, M, base, ptype, i), v in idx.items():
            if arm != A or M != MA or ptype not in types:
                continue
            w = idx.get((B, MB, base, ptype, i))
            if w is None:
                continue
            n += 1; ka += v; kb += w
            b += v and not w; c += w and not v
        res.append((A, MA, B, MB, pt, n, ka, kb, b, c, mcnemar(b, c)))
    adj = holm([r[-1] for r in res])
    md += ["## Planned comparisons (exact McNemar, paired by base session and probe; Holm over all)", "",
           "| A | B | probes | n | A | B | A-only / B-only | p | Holm p |", "|---|---|---|---|---|---|---|---|---|"]
    for (A, MA, B, MB, pt, n, ka, kb, b, c, p), h in zip(res, adj):
        md.append(f"| {A} M={MA} | {B} M={MB} | {pt} | {n} | {100 * ka / max(n, 1):.0f}% | {100 * kb / max(n, 1):.0f}% "
                  f"| {b} / {c} | {fmtp(p)} | {fmtp(h)} |")
    md.append("")

    res2 = []
    for A, MA, B, MB, pt in EXPLORATORY:
        types = RULE if pt == "rule_state" else (pt,)
        b = c = ka = kb = n = 0
        for (arm, M, base, ptype, i), v in idx.items():
            if arm != A or M != MA or ptype not in types:
                continue
            w = idx.get((B, MB, base, ptype, i))
            if w is None:
                continue
            n += 1; ka += v; kb += w
            b += v and not w; c += w and not v
        res2.append((A, MA, B, MB, pt, n, ka, kb, b, c, mcnemar(b, c)))
    md += ["## Exploratory comparisons (chosen after seeing the goal table; unadjusted exact McNemar)", "",
           "| A | B | probes | n | A | B | A-only / B-only | p |", "|---|---|---|---|---|---|---|---|"]
    for (A, MA, B, MB, pt, n, ka, kb, b, c, p) in res2:
        md.append(f"| {A} M={MA} | {B} M={MB} | {pt} | {n} | {100 * ka / max(n, 1):.0f}% | {100 * kb / max(n, 1):.0f}% "
                  f"| {b} / {c} | {fmtp(p)} |")
    md.append("")

    # ---------------------------------------------------------------- tokens and calls
    md += ["## Pinned block and context size (mean estimated tokens, words x 1.33)", "",
           "| arm | " + " | ".join(f"block M={M}" for M in MS) + " | " + " | ".join(f"context M={M}" for M in MS) + " |",
           "|---|" + "---|" * (2 * len(MS))]
    tok = defaultdict(list)
    for s in sess.values():
        for arm, v in s["context_tokens"].items():
            tok[("ctx", arm, s["M"])].append(v)
        for arm, v in s["block_tokens"].items():
            tok[("blk", arm, s["M"])].append(v)

    def mean(xs):
        return f"{statistics.mean(xs):,.0f}" if xs else "n/a"
    for arm in ARMS:
        md.append(f"| {arm} | " + " | ".join(mean(tok[("blk", arm, M)]) for M in MS) + " | " +
                  " | ".join(mean(tok[("ctx", arm, M)]) for M in MS) + " |")
    md.append("")
    md += ["## Extra model calls per session beyond plain compaction (mean; tokens estimated from text)", "",
           "| M | compaction rounds | classifier calls | consolidation calls | consolidation in / out tokens | "
           "ledger calls | ledger in / out tokens | ledger failed updates |", "|---|---|---|---|---|---|---|---|"]
    for M in MS:
        ss = [s for s in sess.values() if s["M"] == M]
        if not ss:
            continue
        cc = [s["prep"]["consol_cost"] for s in ss]
        ls = [s["ledger"] for s in ss if "ledger" in s]
        md.append(f"| {M} | {statistics.mean(s['prep']['summary_rounds'] for s in ss):.1f} | {M} | "
                  f"{statistics.mean(c['calls'] for c in cc):.1f} | "
                  f"{statistics.mean(c['in_tok'] for c in cc):,.0f} / {statistics.mean(c['out_tok'] for c in cc):,.0f} | "
                  + (f"{statistics.mean(l['cost']['calls'] for l in ls):.0f} | "
                     f"{statistics.mean(l['cost']['in_tok'] for l in ls):,.0f} / {statistics.mean(l['cost']['out_tok'] for l in ls):,.0f} | "
                     f"{sum(l['failed'] for l in ls)} of {sum(l['cost']['calls'] for l in ls)} |" if ls else "n/a | n/a | n/a |"))
    md.append("")
    md += ["### Consolidated block size after the j-th consolidation (mean tokens, pooled over M)", "",
           "| j | n | consolidated block | raw operator turns so far |", "|---|---|---|---|"]
    growth = defaultdict(list)
    for s in sess.values():
        ops = truth[s["sid"]]["operator_turns"]
        for j, h in enumerate(s["prep"]["consol_history"], 1):
            raw = sum(len(o["text"].split()) for o in ops[:j * 10]) * 1.33
            growth[j].append((h["tokens"], raw))
    for j in sorted(growth):
        if j in (1, 2, 3, 5, 10, 15, 20):
            g = growth[j]
            md.append(f"| {j} | {len(g)} | {statistics.mean(x for x, _ in g):,.0f} | {statistics.mean(y for _, y in g):,.0f} |")
    md.append("")
    lg = defaultdict(list)
    for s in sess.values():
        if "ledger" in s:
            for j, st in enumerate(s["ledger"]["steps"], 1):
                lg[j].append(st["tokens"])
    if lg:
        md += ["### Ledger size after the k-th operator turn (mean tokens, pooled over M)", "", "| k | n | ledger |",
               "|---|---|---|"]
        for j in (1, 10, 25, 50, 100, 150, 200):
            if j in lg:
                md.append(f"| {j} | {len(lg[j])} | {statistics.mean(lg[j]):,.0f} |")
        md.append("")

    # ---------------------------------------------------------------- classifier
    md += ["## Directive classifier against generation labels", "",
           "| M | operator turns | load-bearing | kept | recall (load-bearing kept) | precision | chatter kept |",
           "|---|---|---|---|---|---|---|"]
    for M in MS:
        ss = [s for s in sess.values() if s["M"] == M]
        cl = [c for s in ss for c in s["prep"]["classify"]]
        if not cl:
            continue
        tp = sum(c["directive"] and c["truth"] for c in cl)
        pos = sum(c["truth"] for c in cl)
        kept = sum(c["directive"] for c in cl)
        neg = len(cl) - pos
        md.append(f"| {M} | {len(cl)} | {pos} | {kept} | {pct(tp, pos)} | {pct(tp, kept)} | {pct(kept - tp, neg)} |")
    md.append("")
    # unique-message view by category
    cat = {c["text"]: c["category"] for c in json.loads((HERE / "data" / "chatter.json").read_text())}
    uniq = {}
    for s in sess.values():
        ops = {o["turn"]: o for o in truth[s["sid"]]["operator_turns"]}
        for c in s["prep"]["classify"]:
            o = ops[c["turn"]]
            uniq[o["text"]] = (o["kind"] if o["kind"] != "chatter" else "chatter:" + cat.get(o["text"], "?"), c["directive"])
    byk = defaultdict(lambda: [0, 0])
    for k, d in uniq.values():
        byk[k][0] += d; byk[k][1] += 1
    md += ["### Kept rate by message kind (unique messages)", "", "| kind | kept / unique |", "|---|---|"]
    for k in sorted(byk):
        md.append(f"| {k} | {pct(*byk[k])} |")
    md.append("")
    hl = HERE / "hand_classifier.json"
    if hl.exists():
        H = json.loads(hl.read_text())
        hand = [h["hand"] for h in H]
        clf = [h["classifier"] for h in H]
        gen = [h["generation"] for h in H]
        tp = sum(x and y for x, y in zip(clf, hand))
        md += ["### Classifier against hand labels (blind sample)", "",
               f"n = {len(H)}. Hand vs generation label agreement {sum(x == y for x, y in zip(hand, gen))}/{len(H)}, "
               f"kappa {kappa(hand, gen):.2f}. Classifier vs hand: agreement {sum(x == y for x, y in zip(hand, clf))}/{len(H)}, "
               f"kappa {kappa(hand, clf):.2f}, precision {pct(tp, sum(clf))}, recall {pct(tp, sum(hand))} "
               "(the sample is stratified, so these are not population rates).", ""]

    # ---------------------------------------------------------------- audit
    au = read_jsonl(out / "audit.jsonl")
    if au:
        md += ["## Audit of the consolidated block and the ledger against ground truth", "",
               "| block | M | sessions | active dropped | revoked still in force | amended not in new form | "
               "objective current | fact current present | all fact versions present |",
               "|---|---|---|---|---|---|---|---|---|"]
        for blk in ("consol_final", "ledger_final"):
            for M in MS:
                rs = [r for r in au if r["block"] == blk and r["M"] == M]
                if not rs:
                    continue
                rl = [x for r in rs for x in r["rules"]]
                act = [x for x in rl if x["kind"] == "active"]
                rev = [x for x in rl if x["kind"] == "revoked"]
                amd = [x for x in rl if x["kind"] == "amended"]
                fa = [f for r in rs for f in r["facts"]]
                md.append(f"| {blk} | {M} | {len(rs)} | {sum(x['state'] != 'IN_FORCE_OLD' for x in act)} of {len(act)} | "
                          f"{sum(x['state'] in ('IN_FORCE_OLD', 'CONFLICT') for x in rev)} of {len(rev)} | "
                          f"{sum(x['state'] != 'IN_FORCE_NEW' for x in amd)} of {len(amd)} | "
                          f"{sum(r['objective'] == 'current' for r in rs)} of {len(rs)} | "
                          f"{sum(f['current'] for f in fa)} of {len(fa)} | {sum(f['all_versions'] for f in fa)} of {len(fa)} |")
        md.append("")
        # resurrection: revoked rule handled (LIFTED/ABSENT) in the first snapshot after its revocation, in force at the end
        md += ["### Revoked rules over consolidation rounds", "",
               "| M | revoked rules | in force right after revocation | handled then, in force at the end (resurrected) |",
               "|---|---|---|---|"]
        for M in MS:
            first_bad = res_n = tot = 0
            for sid in {r["sid"] for r in au if r["M"] == M}:
                snaps = sorted([r for r in au if r["sid"] == sid and r["block"].startswith("consol_after_")],
                               key=lambda r: r["after_turn"])
                fin = next((r for r in au if r["sid"] == sid and r["block"] == "consol_final"), None)
                for rv in truth[sid]["truth"]["revoked"]:
                    snap = next((r for r in snaps if r["after_turn"] >= rv["revoked_turn"]), None)
                    if snap is None or fin is None:
                        continue
                    tot += 1
                    st = next(x["state"] for x in snap["rules"] if x["id"] == rv["id"])
                    fs = next(x["state"] for x in fin["rules"] if x["id"] == rv["id"])
                    bad = lambda z: z in ("IN_FORCE_OLD", "CONFLICT")
                    first_bad += bad(st)
                    res_n += (not bad(st)) and bad(fs)
            md.append(f"| {M} | {tot} | {first_bad} | {res_n} |")
        md.append("")
        # probe accuracy conditional on the audited state (exploratory)
        md += ["### pin_consol revoked-probe accuracy by audited final state (exploratory)", "",
               "| final state | n | correct |", "|---|---|---|"]
        cond = defaultdict(lambda: [0, 0])
        fin = {r["sid"]: r for r in au if r["block"] == "consol_final"}
        for r in rows:
            if r["arm"] == "pin_consol" and r["ptype"] in ("revoked", "active") and r["sid"] in fin:
                rid = truth[r["sid"]]["truth"][r["ptype"]][r["idx"]]["id"]
                st = next(x["state"] for x in fin[r["sid"]]["rules"] if x["id"] == rid)
                cond[(r["ptype"], st)][0] += r["correct"]; cond[(r["ptype"], st)][1] += 1
        for k in sorted(cond):
            md.append(f"| {k[0]}: {k[1]} | {cond[k][1]} | {pct(*cond[k])} |")
        md.append("")

    # ---------------------------------------------------------------- judge validation
    hj = HERE / "hand_labels.json"
    if hj.exists():
        H = json.loads(hj.read_text())
        md += ["## Judge validation (blind hand labels by the study agent)", "", "| judge | n | agreement | kappa |",
               "|---|---|---|---|"]
        for j in sorted({h["judge"] for h in H}):
            hs = [h for h in H if h["judge"] == j]
            x, y = [h["hand"] for h in hs], [h["model"] for h in hs]
            md.append(f"| {j} | {len(hs)} | {sum(p == q for p, q in zip(x, y))}/{len(hs)} | {kappa(x, y):.2f} |")
        md.append("")

    (out / "tables.md").write_text("\n".join(md))
    print("\n".join(md))
    goal = {(arm, M): (sum(r["correct"] for r in cell(arm, M, "goal")), len(cell(arm, M, "goal"))) for arm in ARMS for M in MS}
    plot(acc, goal, tok, out)


COLORS = {"full": "#444444", "plain": "#999999", "pin_raw": "#1f77b4", "pin_directive": "#2ca02c",
          "pin_consol": "#d62728", "ledger": "#9467bd"}


def plot(acc, goal, tok, out):
    """Two-panel SVG (no plotting library needed): rule-state accuracy with Wilson CIs, and block tokens, vs M."""
    W, H, PAD = 460, 320, 55
    xs = {M: PAD + i * (W - 2 * PAD) / (len(MS) - 1) for i, M in enumerate(MS)}
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{3 * W}" height="{H + 40}" font-family="sans-serif" font-size="11">',
           f'<rect width="{3 * W}" height="{H + 40}" fill="white"/>']

    def panel(ox, title, ylab, ymin, ymax, series, log=False, leg=(70, 200)):
        def y(v):
            if log:
                v, lo, hi = math.log10(max(v, 1)), math.log10(ymin), math.log10(ymax)
            else:
                lo, hi = ymin, ymax
            return H - PAD + 15 - (v - lo) / (hi - lo) * (H - 2 * PAD)
        svg.append(f'<text x="{ox + W / 2}" y="18" text-anchor="middle" font-size="13">{title}</text>')
        svg.append(f'<line x1="{ox + PAD}" y1="{y(ymin)}" x2="{ox + W - PAD}" y2="{y(ymin)}" stroke="black"/>')
        svg.append(f'<line x1="{ox + PAD}" y1="{y(ymin)}" x2="{ox + PAD}" y2="{y(ymax)}" stroke="black"/>')
        ticks = [ymin, (ymin + ymax) / 2, ymax] if not log else [t for t in (100, 300, 1000, 3000, 10000) if ymin <= t <= ymax]
        for t in ticks:
            svg.append(f'<text x="{ox + PAD - 5}" y="{y(t) + 4}" text-anchor="end">{t:g}</text>')
        for M in MS:
            svg.append(f'<text x="{ox + xs[M]}" y="{y(ymin) + 15}" text-anchor="middle">{M}</text>')
        svg.append(f'<text x="{ox + W / 2}" y="{H + 25}" text-anchor="middle">operator turns M</text>')
        svg.append(f'<text x="{ox + 14}" y="{H / 2}" text-anchor="middle" transform="rotate(-90 {ox + 14} {H / 2})">{ylab}</text>')
        for li, (arm, pts) in enumerate(series):
            if not pts:
                continue
            c = COLORS.get(arm, "black")
            d = " ".join(f"{ox + xs[M]:.1f},{y(v):.1f}" for M, v, _, _ in pts)
            svg.append(f'<polyline points="{d}" fill="none" stroke="{c}" stroke-width="2"/>')
            for M, v, lo, hi in pts:
                svg.append(f'<circle cx="{ox + xs[M]:.1f}" cy="{y(v):.1f}" r="3" fill="{c}"/>')
                if lo is not None:
                    svg.append(f'<line x1="{ox + xs[M]:.1f}" y1="{y(lo):.1f}" x2="{ox + xs[M]:.1f}" y2="{y(hi):.1f}" stroke="{c}"/>')
            if leg is None:
                continue
            lx, ly = ox + leg[0], leg[1] + 14 * li
            svg.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 15}" y2="{ly}" stroke="{c}" stroke-width="2"/>')
            svg.append(f'<text x="{lx + 19}" y="{ly + 4}">{arm}</text>')

    s1 = []
    for arm in ARMS:
        pts = []
        for M in MS:
            k, n = acc.get((arm, M), (0, 0))
            if n:
                lo, hi = wilson(k, n)
                pts.append((M, 100 * k / n, 100 * lo, 100 * hi))
        s1.append((arm, pts))
    panel(0, "Rule-state accuracy (95% Wilson CI; legend applies to all panels)", "accuracy (%)", 0, 100, s1)
    s3 = []
    for arm in ARMS:
        pts = []
        for M in MS:
            k, n = goal.get((arm, M), (0, 0))
            if n:
                lo, hi = wilson(k, n)
                pts.append((M, 100 * k / n, 100 * lo, 100 * hi))
        s3.append((arm, pts))
    panel(W, "Goal accuracy (95% Wilson CI)", "accuracy (%)", 0, 100, s3, leg=None)
    s2 = [(arm, [(M, statistics.mean(tok[("blk", arm, M)]), None, None) for M in MS if tok.get(("blk", arm, M))])
          for arm in ARMS]
    panel(2 * W, "Pinned block size (mean tokens, log scale)", "tokens", 300, 10000, s2, log=True, leg=None)
    svg.append("</svg>")
    (out / "accuracy_tokens_vs_M.svg").write_text("\n".join(svg))


if __name__ == "__main__":
    main()
