"""Regenerate every E15 table from the raw files (no model calls).

Usage: python3 analyze.py [--data DIR] > results.md
Reads a_items.jsonl, a_decisions.jsonl, b_transcripts.jsonl, and (if present) hand-label files.
"""
import argparse, json, math, random, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from common import wilson  # noqa: E402

PRESENT = ("INTACT", "DETAIL_LOST")


def rj(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def pct(k, n):
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f}% ({k}/{n}) [{max(0, 100 * lo):.0f} to {100 * hi:.0f}]"


def mcnemar(pairs):
    """pairs: list of (a, b) booleans. Exact two-sided McNemar on discordant pairs."""
    b = sum(1 for x, y in pairs if x and not y)
    c = sum(1 for x, y in pairs if y and not x)
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return b, c, min(1.0, p)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def fmt_p(p):
    return f"{p:.2g}" if p >= 1e-4 else f"{p:.1e}"


def cluster_boot(units, stat, reps=2000, seed=7):
    """units: list of per-cluster data; stat(list) -> float. Percentile 95% CI."""
    rng = random.Random(seed)
    vals = sorted(stat([units[rng.randrange(len(units))] for _ in units]) for _ in range(reps))
    return stat(units), vals[int(0.025 * reps)], vals[int(0.975 * reps) - 1]


def kappa(a, b):
    labs = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[l] * cb[l] for l in labs) / n ** 2
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def cochran_armitage(groups):
    """groups: list of (score, k, n). Two-sided normal-approximation trend test."""
    N = sum(n for _, _, n in groups)
    K = sum(k for _, k, _ in groups)
    p = K / N
    sbar = sum(s * n for s, _, n in groups) / N
    T = sum(s * (k - n * p) for s, k, n in groups)
    V = p * (1 - p) * sum(n * (s - sbar) ** 2 for s, _, n in groups)
    if V == 0:
        return 1.0
    z = T / math.sqrt(V)
    return math.erfc(abs(z) / math.sqrt(2))

# ====================================================================== Part A


A_ORDER = (["ceiling", "pin_end", "pin_mid", "pin_para_end", "asis", "floor", "asis_t3", "pin_mid_t3"]
           + [f"in_{w}_{f}" for w in ("para", "verb") for f in ("bare", "active", "past")]
           + [f"sec_{w}_{p}_{f}" for w in ("para", "verb") for p in ("start", "mid", "end") for f in ("active", "past")])

A_PRIMARY = [
    ("P1 gap: asis vs pin_end", "asis", "pin_end"),
    ("P2 wording (block, end, active): para vs verb", "sec_para_end_active", "sec_verb_end_active"),
    ("P3 embedding (para, active): inline vs block after summary", "in_para_active", "sec_para_mid_active"),
    ("P4 position (verb, active block): start vs end", "sec_verb_start_active", "sec_verb_end_active"),
    ("P5 framing (verb block, end): past vs active", "sec_verb_end_past", "sec_verb_end_active"),
    ("P6 wording inside narrative: asis vs verbatim bare", "asis", "in_verb_bare"),
]


def part_a(data, out):
    items = [r for r in rj(data / "a_items.jsonl")]
    D = rj(data / "a_decisions.jsonl")
    if not D:
        return
    sel = [r for r in items if r.get("selected")]
    P = lambda s: out.append(s)  # noqa: E731
    P("## Part A: factorial on the same summaries\n")
    P(f"Candidates: {len(items)}; extraction failed: {sum(r['why'] == 'extraction' for r in items)}; "
      f"failed validation: {sum(r['why'] == 'validation' for r in items)}; selected items: {len(sel)} "
      f"over {len({r['id'] for r in sel})} rules.")
    P(f"Selected items by source regime: {dict(Counter(r['regime'] for r in sel))}; "
      f"judge on summary-without-rule: {dict(Counter(r['judge_minus']['verdict'] for r in sel))}.")
    P(f"Unparsed decisions (counted as non-violations): {sum(d['decision'] == 'UNKNOWN' for d in D)} of {len(D)}.\n")

    V = {}
    for d in D:
        V[(d["id"], d["regime"], d["R"], d["cell"], d["rep"])] = d["decision"] == "COMPLY"
    keys = sorted({(d["id"], d["regime"], d["R"]) for d in D})
    reps = sorted({d["rep"] for d in D})
    minus_absent = {(r["id"], r["regime"], r["R"]) for r in sel if r["judge_minus"]["verdict"] == "ABSENT"}

    def cell_rate(cell, subset=None):
        vals = [V[k + (cell, r)] for k in keys for r in reps
                if (k + (cell, r)) in V and (subset is None or k in subset)]
        return sum(vals), len(vals)

    P("### Violation rate per cell (COMPLY on the trigger)\n")
    P("| cell | violation | items with rule-free summary judged ABSENT only |")
    P("|---|---|---|")
    present = {d["cell"] for d in D}
    for c in A_ORDER:
        if c in present:
            P(f"| {c} | {pct(*cell_rate(c))} | {pct(*cell_rate(c, minus_absent))} |")

    P("\n### Pre-specified paired comparisons (exact McNemar on item x repeat pairs, Holm over 6)\n")
    P("| comparison | A | B | discordant A-only / B-only | p | Holm p |")
    P("|---|---|---|---|---|---|")
    rows = []
    for name, a, b in A_PRIMARY:
        pairs = [(V[k + (a, r)], V[k + (b, r)]) for k in keys for r in reps
                 if k + (a, r) in V and k + (b, r) in V]
        bb, cc, p = mcnemar(pairs)
        rows.append((name, a, b, bb, cc, p))
    adj = holm([r[5] for r in rows])
    for (name, a, b, bb, cc, p), h in zip(rows, adj):
        P(f"| {name} | {pct(*cell_rate(a))} | {pct(*cell_rate(b))} | {bb} / {cc} | {fmt_p(p)} | {fmt_p(h)} |")

    # factor main effects, averaged over the other factors, item-cluster bootstrap
    units = []
    for k in keys:
        u = {}
        for c in A_ORDER:
            vs = [V[k + (c, r)] for r in reps if k + (c, r) in V]
            u[c] = sum(vs) / len(vs) if vs else 0.0
        units.append(u)

    def effect(cells_a, cells_b):
        def stat(us):
            da = [sum(u[c] for c in cells_a) / len(cells_a) for u in us]
            db = [sum(u[c] for c in cells_b) / len(cells_b) for u in us]
            return 100 * (sum(db) - sum(da)) / len(us)
        return stat

    sec = lambda w="*", p="*", f="*": [f"sec_{a}_{b}_{c}" for a in ("para", "verb") for b in ("start", "mid", "end")  # noqa
                                       for c in ("active", "past") if w in ("*", a) and p in ("*", b) and f in ("*", c)]
    inl = lambda w="*", f="*": [f"in_{a}_{c}" for a in ("para", "verb") for c in ("bare", "active", "past")  # noqa
                                if w in ("*", a) and f in ("*", c)]
    eff = [
        ("block: verbatim minus paraphrase (avg over 3 positions x 2 framings)", sec(w="para"), sec(w="verb")),
        ("block: active minus past framing", sec(f="past"), sec(f="active")),
        ("block: end minus start", sec(p="start"), sec(p="end")),
        ("block: end minus mid (after summary)", sec(p="mid"), sec(p="end")),
        ("block: mid minus start", sec(p="start"), sec(p="mid")),
        ("inline: verbatim minus paraphrase", inl(w="para"), inl(w="verb")),
        ("inline: active minus bare", inl(f="bare"), inl(f="active")),
        ("inline: past minus bare", inl(f="bare"), inl(f="past")),
        ("separate block (all 12) minus inline (all 6)", inl(), sec()),
        ("separate block, mid, active (2) minus inline active (2)", inl(f="active"), sec(p="mid", f="active")),
        ("block after summary: verbatim minus paraphrase (mid, active)", ["sec_para_mid_active"], ["sec_verb_mid_active"]),
        ("inline active: verbatim minus paraphrase", ["in_para_active"], ["in_verb_active"]),
        ("inline verbatim: active minus bare", ["in_verb_bare"], ["in_verb_active"]),
        ("verbatim active: block after summary minus inline", ["in_verb_active"], ["sec_verb_mid_active"]),
        ("verbatim active block: mid minus start", ["sec_verb_start_active"], ["sec_verb_mid_active"]),
        ("verbatim active block: end minus mid", ["sec_verb_mid_active"], ["sec_verb_end_active"]),
        ("follow-up: rule paraphrase as its own bare sentence (in_para_bare) minus asis", ["asis"], ["in_para_bare"]),
        ("follow-up: block, paraphrase, end: active minus past", ["sec_para_end_past"], ["sec_para_end_active"]),
        ("follow-up: asis + paraphrase block (pin_para_end) minus asis", ["asis"], ["pin_para_end"]),
        ("follow-up: pin_end (verbatim block) minus pin_para_end (paraphrase block)", ["pin_para_end"], ["pin_end"]),
        ("pin_end (summary keeps rule + block) minus sec_verb_end_active (rule moved)",
         ["sec_verb_end_active"], ["pin_end"]),
        ("pin_end minus pin_mid", ["pin_mid"], ["pin_end"]),
        ("asis (15-turn tail) minus asis_t3 (3-turn tail)", ["asis_t3"], ["asis"]),
    ]
    P("\n### Factor effects (exploratory): difference in violation rate, percentage points, 95% item-cluster bootstrap CI\n")
    P("Negative means the second level violates less.\n")
    P("| effect | difference | 95% CI |")
    P("|---|---|---|")
    for name, ca, cb in eff:
        if not set(ca + cb) <= present:
            continue
        est, lo, hi = cluster_boot(units, effect(ca, cb))
        P(f"| {name} | {est:+.1f} | {lo:+.1f} to {hi:+.1f} |")

    P("\n### Violation by source regime of the summary (asis vs pin_end)\n")
    P("| source regime | asis | pin_end | floor |")
    P("|---|---|---|---|")
    for g in ("recursive", "source", "selective", "recursive_keeprules"):
        sub = {k for k in keys if k[1] == g}
        P(f"| {g} | {pct(*cell_rate('asis', sub))} | {pct(*cell_rate('pin_end', sub))} | {pct(*cell_rate('floor', sub))} |")

    # per-rule heterogeneity: how many items drive the asis gap?
    gap = Counter()
    for k in keys:
        a = sum(V.get(k + ("asis", r), False) for r in reps)
        p = sum(V.get(k + ("pin_end", r), False) for r in reps)
        gap[(a, p)] += 1
    P(f"\nItems by (asis violations, pin_end violations) out of {len(reps)} repeats: "
      + ", ".join(f"{a}/{p}: {n}" for (a, p), n in sorted(gap.items())))

    hc = HERE / "hand_check_a.json"
    if hc.exists() and data == HERE / "data":
        H = json.loads(hc.read_text())
        ok_phrase = sum(h["phrase_states_rule"] for h in H)
        ok_minus = sum(h["minus_has_no_rule"] for h in H)
        ok_clean = sum(h["removal_clean"] for h in H)
        P(f"\nHand check of {len(H)} selected items: phrase states the rule in {ok_phrase}; "
          f"summary-without-rule really lacks it in {ok_minus}; removal left readable text in {ok_clean}.")

# ====================================================================== Part B


def part_b(data, out):
    T = rj(data / "b_transcripts.jsonl")
    if not T:
        return
    P = lambda s: out.append(s)  # noqa: E731
    NS = sorted({t["n"] for t in T})
    REG = ("plain", "keeprules", "structured")
    P("\n## Part B: keep-rules prompts at scale\n")
    cnt = Counter((t["n"], t["regime"]) for t in T)
    P("Chains per (N, regime): " + ", ".join(f"N={n}: " + "/".join(str(cnt[(n, g)]) for g in REG) for n in NS)
      + " (plain/keeprules/structured).")
    P(f"Word budget 150 + 10N. Unparsed decisions: "
      f"{sum(d['decision'] == 'UNKNOWN' for t in T for r in t['rounds'] for d in r.get('decisions', []))}.\n")
    Rs = (4, 8, 16)

    P("### Rule survival in the summary (E6 pass-2 judge: INTACT or DETAIL_LOST), per rule\n")
    P("R=16 covers every rule in the transcript; R=4 and R=8 cover only the tested rules.\n")
    P("| N | regime | R=4 | R=8 | R=16 | R=16 INTACT only |")
    P("|---|---|---|---|---|---|")
    surv16 = {}
    for n in NS:
        for g in REG:
            cells = []
            for R in Rs:
                v = [j["verdict"] for t in T if t["n"] == n and t["regime"] == g
                     for r in t["rounds"] if r["R"] == R for rid, j in r["judge"].items()
                     if R == 16 or rid in t["tested"]]
                cells.append((sum(x in PRESENT for x in v), len(v)))
                if R == 16:
                    surv16[(n, g)] = cells[-1]
                    intact = (sum(x == "INTACT" for x in v), len(v))
            P(f"| {n} | {g} | " + " | ".join(pct(*c) for c in cells) + f" | {pct(*intact)} |")
    for g in REG:
        p = cochran_armitage([(math.log2(n), *surv16[(n, g)]) for n in NS])
        P(f"\nTrend in R=16 survival over log2 N, {g}: Cochran-Armitage p = {fmt_p(p)}.")

    P("\n### Verbatim retention (normalized rule text is a substring of the summary)\n")
    P("| N | regime | R=4 | R=8 | R=16 |")
    P("|---|---|---|---|---|")
    for n in NS:
        for g in REG:
            row = []
            for R in Rs:
                v = [x for t in T if t["n"] == n and t["regime"] == g for r in t["rounds"] if r["R"] == R
                     for x in r["verbatim"].values()]
                row.append(pct(sum(v), len(v)))
            P(f"| {n} | {g} | " + " | ".join(row) + " |")

    P("\n### Summary length (mean words) and budget\n")
    P("| N | budget | regime | R=4 | R=8 | R=16 | share of R=16 summaries over budget |")
    P("|---|---|---|---|---|---|---|")
    for n in NS:
        for g in REG:
            row = []
            for R in Rs:
                w = [r["words"] for t in T if t["n"] == n and t["regime"] == g for r in t["rounds"] if r["R"] == R]
                row.append(f"{sum(w) / len(w):.0f}" if w else "n/a")
            w16 = [r["words"] for t in T if t["n"] == n and t["regime"] == g for r in t["rounds"] if r["R"] == 16]
            over = sum(x > 150 + 10 * n for x in w16)
            P(f"| {n} | {150 + 10 * n} | {g} | " + " | ".join(row) + f" | {over}/{len(w16)} |")

    P("\n### Non-rule content: task-fact retention (fact's key string present in the summary)\n")
    P("| N | regime | R=4 | R=8 | R=16 |")
    P("|---|---|---|---|---|")
    for n in NS:
        for g in REG:
            row = []
            for R in Rs:
                v = [x for t in T if t["n"] == n and t["regime"] == g for r in t["rounds"] if r["R"] == R for x in r["facts"]]
                row.append(pct(sum(v), len(v)))
            P(f"| {n} | {g} | " + " | ".join(row) + " |")
    # pooled fact test plain vs keeprules vs structured at R=16, paired by (n, idx, fact)
    fk = {}
    for t in T:
        for r in t["rounds"]:
            if r["R"] == 16:
                for i, x in enumerate(r["facts"]):
                    fk[(t["n"], t["idx"], i, t["regime"])] = x
    for a, b in (("plain", "keeprules"), ("plain", "structured"), ("keeprules", "structured")):
        pairs = [(fk[k[:3] + (a,)], fk[k[:3] + (b,)]) for k in fk if k[3] == a and k[:3] + (b,) in fk]
        bb, cc, p = mcnemar(pairs)
        P(f"\nFacts at R=16 pooled over N, {a} vs {b}: {sum(x for x, _ in pairs)}/{len(pairs)} vs "
          f"{sum(y for _, y in pairs)}/{len(pairs)}, discordant {bb}/{cc}, McNemar p = {fmt_p(p)} (exploratory).")

    # non-rule content: concrete specifics (backticked code spans from non-operator turns)
    import re as _re
    import run_b  # deterministic rebuild of each transcript; makes no model calls
    span_re = _re.compile(r"`([^`]{4,80})`")
    built = {}
    for t in T:
        key = (t["n"], t["idx"], t["seed"])
        if key not in built:
            built[key] = run_b.build(t["n"], t["idx"], t["seed"])[2]
    P("\n### Non-rule content: concrete specifics carried by the summary\n")
    P("Code spans are backticked strings (commands, paths, identifiers) from non-operator turns. "
      "'Distinct spans' counts how many from the whole history so far appear in the summary; "
      "'latest chunk' is the share of spans from the newest 15 turns that appear.\n")
    P("| N | regime | distinct spans R=4 | R=8 | R=16 | latest-chunk share R=16 |")
    P("|---|---|---|---|---|---|")
    for n in NS:
        for g in REG:
            cnts, share = {4: [], 8: [], 16: []}, []
            for t in T:
                if t["n"] != n or t["regime"] != g:
                    continue
                chunks = built[(t["n"], t["idx"], t["seed"])]
                for r in t["rounds"]:
                    if r["R"] not in cnts:
                        continue
                    hist = {m for c in chunks[:r["R"]] for turn in c if not turn.startswith("OPERATOR:")
                            for m in span_re.findall(turn)}
                    cnts[r["R"]].append(sum(1 for m in hist if m in r["summary"]))
                    if r["R"] == 16:
                        last = {m for turn in chunks[15] for m in span_re.findall(turn)}
                        if last:
                            share.append(sum(1 for m in last if m in r["summary"]) / len(last))
            row = [f"{sum(v) / len(v):.1f}" if v else "n/a" for v in cnts.values()]
            P(f"| {n} | {g} | " + " | ".join(row) + f" | {100 * sum(share) / max(1, len(share)):.0f}% |")

    # behaviour
    dec = {}
    verdict = {}
    for t in T:
        for r in t["rounds"]:
            for d in r.get("decisions", []):
                if r["R"] < 16 and d["rep"] > 0:
                    continue  # first 9 chains ran 2 repeats at every R; the rest run 1 at R=4, 8
                dec[(t["n"], t["idx"], d["rule"], r["R"], d["rep"], d["arm"])] = d["decision"] == "COMPLY"
                verdict[(t["n"], t["idx"], d["rule"], r["R"], d["arm"])] = (
                    r["judge"][d["rule"]]["verdict"] if d["arm"] != "pin_all" else "PINNED")
    ARMS = ("plain", "keeprules", "structured", "pin_all")
    P("\n### Primary metric: violation rate on the trigger (2 repeats per tested rule at R=16, 1 at R=4 and 8)\n")
    P("| N | R | plain | keeprules | structured | pin_all |")
    P("|---|---|---|---|---|---|")
    for n in NS:
        for R in Rs:
            row = []
            for a in ARMS:
                v = [x for k, x in dec.items() if k[0] == n and k[3] == R and k[5] == a]
                row.append(pct(sum(v), len(v)))
            P(f"| {n} | {R} | " + " | ".join(row) + " |")
    P("| all | 16 | " + " | ".join(
        pct(sum(x for k, x in dec.items() if k[3] == 16 and k[5] == a),
            sum(1 for k in dec if k[3] == 16 and k[5] == a)) for a in ARMS) + " |")

    P("\n### Pre-specified tests at R=16 (exact McNemar, pairs matched on rule x repeat, Holm over 16)\n")
    P("| N | comparison | discordant A-only / B-only | p | Holm p |")
    P("|---|---|---|---|---|")
    comps = [("keeprules", "pin_all"), ("structured", "pin_all"), ("plain", "keeprules"), ("keeprules", "structured")]
    rows = []
    for n in NS:
        for a, b in comps:
            pairs = [(x, dec[k[:5] + (b,)]) for k, x in dec.items()
                     if k[0] == n and k[3] == 16 and k[5] == a and k[:5] + (b,) in dec]
            rows.append((n, a, b, *mcnemar(pairs)))
    adj = holm([r[5] for r in rows])
    for (n, a, b, bb, cc, p), h in zip(rows, adj):
        P(f"| {n} | {a} vs {b} | {bb} / {cc} | {fmt_p(p)} | {fmt_p(h)} |")
    for a, b in comps:
        pairs = [(x, dec[k[:5] + (b,)]) for k, x in dec.items() if k[3] == 16 and k[5] == a and k[:5] + (b,) in dec]
        bb, cc, p = mcnemar(pairs)
        P(f"\nPooled over N at R=16 (exploratory), {a} vs {b}: discordant {bb}/{cc}, p = {fmt_p(p)}.")

    P("\n### Violation by the judge's verdict on the tested rule (all R)\n")
    P("| arm | INTACT | DETAIL_LOST | DISTORTED | ABSENT |")
    P("|---|---|---|---|---|")
    for a in ("plain", "keeprules", "structured"):
        row = []
        for v in ("INTACT", "DETAIL_LOST", "DISTORTED", "ABSENT"):
            xs = [x for k, x in dec.items() if k[5] == a and verdict.get(k[:4] + (a,)) == v]
            row.append(pct(sum(xs), len(xs)))
        P(f"| {a} | " + " | ".join(row) + " |")
    # intact-and-verbatim vs intact-paraphrased in the structured arm
    vb = {}
    for t in T:
        for r in t["rounds"]:
            for rid, x in r["verbatim"].items():
                vb[(t["n"], t["idx"], rid, r["R"], t["regime"])] = x
    for a in ("keeprules", "structured"):
        for flag in (True, False):
            xs = [x for k, x in dec.items() if k[5] == a and verdict.get(k[:4] + (a,)) == "INTACT"
                  and vb.get(k[:4] + (a,)) == flag]
            P(f"\n{a}, rule judged INTACT and {'verbatim' if flag else 'not verbatim'} in summary: {pct(sum(xs), len(xs))}")

    hl = HERE / "hand_labels_b.json"
    if hl.exists() and data == HERE / "data":
        H = json.loads(hl.read_text())
        jl = [h["judge"] for h in H]
        ml = [h["hand"] for h in H]
        po4, k4 = kappa(jl, ml)
        col = lambda v: "PRESENT" if v in PRESENT else v  # noqa: E731
        po3, k3 = kappa([col(x) for x in jl], [col(x) for x in ml])
        bin_ = lambda v: v in PRESENT  # noqa: E731
        po2, k2 = kappa([bin_(x) for x in jl], [bin_(x) for x in ml])
        P(f"\n### Judge validation on Part B summaries\n\n{len(H)} hand-labeled items (stratified on the judge's verdict): "
          f"four labels agreement {po4:.2f}, kappa {k4:.2f}; three labels (PRESENT/DISTORTED/ABSENT) {po3:.2f}, "
          f"kappa {k3:.2f}; present vs not {po2:.2f}, kappa {k2:.2f}.")
        P("Confusions (judge -> hand): " + ", ".join(f"{a}->{b}: {c}" for (a, b), c in
                                                       sorted(Counter((x, y) for x, y in zip(jl, ml) if x != y).items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data"))
    data = Path(ap.parse_args().data)
    out = [f"# E15 results (generated by analyze.py from {data.name}/)\n"]
    part_a(data, out)
    part_b(data, out)
    print("\n".join(out))


if __name__ == "__main__":
    main()
