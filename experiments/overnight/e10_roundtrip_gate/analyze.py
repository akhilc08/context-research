"""Regenerate every E10 table from raw/ (no model calls).

python3 analyze.py   -> results.json, results.md, pareto.svg, examples.json
Env E10_OUT selects the run directory (default: this directory).
"""
import json, os, statistics
from pathlib import Path

from labels import ITEMS, item_scores, harm, judged, auroc, wilson, mcnemar_exact, holm, cluster_boot

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("E10_OUT", str(HERE)))
USAGE = HERE.parent / "usage.jsonl"
ARMS = ["plain", "structured", "always", "rt_gate", "rt_patch", "pc_gate", "full"]
SIGS = ["rt_generic", "rt_aligned", "pc"]


def load_usage():
    u = {}
    if USAGE.exists():
        for line in open(USAGE):
            if '"e10|' not in line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            u[r["tag"]] = (r.get("in") or 0) + (r.get("out") or 0)
    return u


def tokens(ledger, U):
    """Tokens of a ledger: real usage when logged, else characters / 4."""
    return sum(U.get(c["tag"], (c["in_chars"] + c["out_chars"]) / 4) for c in ledger)


def load_recs():
    split = json.loads((HERE / "split.json").read_text())
    recs = {}
    for p in sorted((OUT / "raw").glob("t*.json")):
        r = json.loads(p.read_text())
        recs[r["tid"]] = r
    return split, recs


def f(x, d=2):
    return "n/a" if x != x else f"{x:.{d}f}"


def main():
    split, recs = load_recs()
    U = load_usage()
    cal, ev = set(split["calibration"]), set(split["evaluation"])
    res = dict(model=sorted({r["model"] for r in recs.values()}))

    # ------------------------------------------------ question 1: signal AUROC on ungated final events
    groups = {"all": [], "calibration": [], "evaluation": []}
    for tid, r in recs.items():
        if not r.get("base_done") or not judged(r, ["plain", "structured", "always"]):
            continue
        g = []
        for arm in ("plain", "structured", "always"):
            a = r["arms"][arm]
            g.append(dict(tid=tid, arm=arm, y=harm(a), **{s: a["sig"][s]["score"] for s in SIGS}))
        groups["all"].append(g)
        groups["calibration" if tid in cal else "evaluation"].append(g)
    q1 = {}
    for name, G in groups.items():
        E = [e for g in G for e in g]
        if not E:
            continue
        y = [e["y"] for e in E]
        row = dict(n_events=len(E), n_transcripts=len(G), harm=sum(y))
        for s in SIGS:
            row[s] = auroc([e[s] for e in E], y)
            row[s + "_ci"] = cluster_boot(G, lambda S, s=s: auroc([e[s] for e in S], [e["y"] for e in S]))
        row["diff_generic_minus_aligned_ci"] = cluster_boot(G, lambda S: auroc([e["rt_generic"] for e in S], [e["y"] for e in S]) - auroc([e["rt_aligned"] for e in S], [e["y"] for e in S]))
        arm_rate = {a: statistics.mean(e["y"] for e in E if e["arm"] == a) for a in ("plain", "structured", "always")}
        row["condition_only"] = auroc([arm_rate[e["arm"]] for e in E], y)
        within = {}
        for s in SIGS:
            num = den = 0
            for a in ("plain", "structured", "always"):
                sub = [e for e in E if e["arm"] == a]
                ys = [e["y"] for e in sub]
                pairs = sum(ys) * (len(ys) - sum(ys))
                if pairs:
                    num += auroc([e[s] for e in sub], ys) * pairs; den += pairs
            within[s] = num / den if den else float("nan")
        row["within_arm"] = within
        q1[name] = row
    res["q1_auroc"] = q1

    # ------------------------------------------------ question 2: arms on evaluation transcripts
    E = [recs[t] for t in sorted(ev) if t in recs and recs[t].get("gated_done") and judged(recs[t], ARMS)]
    n = len(E)
    res["n_eval"] = n
    arms = {}
    for a in ARMS:
        h = [harm(r["arms"][a]) for r in E]
        hp = [harm(r["arms"][a], parser=True) for r in E]
        exc = [int(any(item_scores(r["arms"][a])[k] == 0 and item_scores(r["arms"]["full"])[k] == 1 for k in ITEMS)) for r in E]
        led = [r["arms"][a].get("ledger", []) for r in E]
        row = dict(harm=sum(h), rate=sum(h) / n if n else float("nan"), ci=wilson(sum(h), n),
                   harm_parser=sum(hp), excess_harm=sum(exc),
                   items={k: statistics.mean(item_scores(r["arms"][a])[k] for r in E) for k in ITEMS} if n else {},
                   calls=statistics.mean(len(l) for l in led) if n else 0,
                   tokens=statistics.mean(tokens(l, U) for l in led) if n else 0,
                   context_tokens=statistics.mean(r["arms"][a]["context_chars"] / 4 for r in E) if n else 0)
        if a in ("rt_gate", "rt_patch", "pc_gate"):
            fired = [[rd["fired"] for rd in r["arms"][a]["rounds"]] for r in E]
            row["fire_rate_by_round"] = [statistics.mean(fr[i] for fr in fired) for i in range(3)]
            row["any_fire"] = statistics.mean(any(fr) for fr in fired)
            row["threshold"] = E[0]["arms"][a]["threshold"]
        arms[a] = row
    # cost of a full-context agent is not a compaction cost; report its context size only
    res["arms"] = arms
    pairs, pv = [], []
    for i, a in enumerate(ARMS):
        for b in ARMS[i + 1:]:
            ha = [harm(r["arms"][a]) for r in E]; hb = [harm(r["arms"][b]) for r in E]
            b10 = sum(x and not y for x, y in zip(ha, hb)); b01 = sum(y and not x for x, y in zip(ha, hb))
            pairs.append(dict(a=a, b=b, a_only=b10, b_only=b01, p=mcnemar_exact(b10, b01)))
            pv.append(pairs[-1]["p"])
    for p, adj in zip(pairs, holm(pv)):
        p["p_holm"] = adj
    res["mcnemar"] = pairs
    # secondary: number of failed items (0 to 5) per transcript, paired difference vs plain
    nf = lambda arm_rec: sum(v == 0 for v in item_scores(arm_rec).values())
    sec = {}
    for a in ARMS:
        d = [[nf(r["arms"][a]) - nf(r["arms"]["plain"])] for r in E]
        sec[a] = dict(mean_failed=statistics.mean(nf(r["arms"][a]) for r in E) if n else float("nan"),
                      diff_vs_plain=statistics.mean(x[0] for x in d) if n else float("nan"),
                      diff_ci=cluster_boot(d, lambda S: statistics.mean(S)) if n else (float("nan"),) * 2)
    res["failed_items"] = sec
    # gate diagnostics: did firing repair the round's draft?
    diag = {}
    for a in ("rt_gate", "rt_patch", "pc_gate"):
        fired_h = [harm(r["arms"][a]) for r in E if any(rd["fired"] for rd in r["arms"][a]["rounds"])]
        plain_when_fired = [harm(r["arms"]["plain"]) for r in E if any(rd["fired"] for rd in r["arms"][a]["rounds"])]
        nf_h = [harm(r["arms"][a]) for r in E if not any(rd["fired"] for rd in r["arms"][a]["rounds"])]
        diag[a] = dict(n_fired=len(fired_h), harm_when_fired=sum(fired_h), plain_harm_same_transcripts=sum(plain_when_fired),
                       n_not_fired=len(nf_h), harm_when_not_fired=sum(nf_h))
    res["gate_diag"] = diag
    # what the generic questions ask about (keyword heuristic, final-round questions of the base phase)
    cats = {"rule or constraint": ["rule", "constraint", "never", "must", "approval", "policy", "require"],
            "goal or priority": ["goal", "priority", "current task", "working on", "paused"],
            "ruled-out approach": ["ruled out", "tried", "avoid", "should not", "approach"],
            "identifier": ["host", "bucket", "schema", "runner", "url", "redis", "database"]}
    tally, nq = {k: 0 for k in list(cats) + ["other (recent work, tests, files)"]}, 0
    for r in recs.values():
        if not r.get("base_done"):
            continue
        for q in r["arms"]["plain"]["sig"]["rt_generic"]["questions"]:
            nq += 1
            ql = q.lower()
            hit = next((k for k, ws in cats.items() if any(w in ql for w in ws)), "other (recent work, tests, files)")
            tally[hit] += 1
    res["generic_question_categories"] = dict(n=nq, counts=tally)
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
    write_md(res)
    write_svg(res)
    write_examples(E)
    print((OUT / "results.md").read_text())


def write_md(res):
    L = [f"# E10 results (generated by analyze.py)\n\nModel: {', '.join(res['model'])}\n"]
    L.append("## Question 1: AUROC of each signal for primary harm, on ungated final compactions\n")
    L.append("Events are the final summaries of the plain, structured, and always-recompact arms (three per transcript). "
             "CIs bootstrap transcripts (2,000 resamples).\n")
    L.append("| Split | Events (transcripts) | Harm | Generic round-trip | Aligned round-trip (E9) | Paired continuation | Generic minus aligned, 95% CI | Condition only |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k, r in res["q1_auroc"].items():
        cells = [f"{f(r[s])} [{f(r[s + '_ci'][0])}, {f(r[s + '_ci'][1])}]" for s in SIGS]
        d = r["diff_generic_minus_aligned_ci"]
        L.append(f"| {k} | {r['n_events']} ({r['n_transcripts']}) | {r['harm']} | " + " | ".join(cells)
                 + f" | [{f(d[0])}, {f(d[1])}] | {f(r['condition_only'])} |")
    L.append("\nWithin-arm AUROC (pair-weighted average over the three arms):\n")
    L.append("| Split | Generic round-trip | Aligned round-trip | Paired continuation |\n|---|---|---|---|")
    for k, r in res["q1_auroc"].items():
        L.append(f"| {k} | " + " | ".join(f(r["within_arm"][s]) for s in SIGS) + " |")
    n = res["n_eval"]
    L.append(f"\n## Question 2: arms on the evaluation split (n = {n} transcripts)\n")
    L.append("Harm = some probe item wrong in both samples after the final round. Calls and tokens are the compaction "
             "pipeline's cost per transcript (all compaction, gate, and recompaction calls over three rounds; probes "
             "excluded). Context tokens = size of the final context handed to the agent (characters / 4).\n")
    L.append("| Arm | Harm [95% CI] | Harm, DECISION parser | Excess harm vs full | Calls | Tokens | Final context tokens | Gate fired (round 1, 2, 3) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for a in ARMS:
        r = res["arms"][a]
        fire = ", ".join(f"{x:.2f}" for x in r.get("fire_rate_by_round", [])) or ""
        L.append(f"| {a} | {r['harm']}/{n} = {100 * r['rate']:.0f}% [{100 * r['ci'][0]:.0f}, {100 * r['ci'][1]:.0f}] | "
                 f"{r['harm_parser']}/{n} | {r['excess_harm']}/{n} | {r['calls']:.1f} | {r['tokens']:.0f} | "
                 f"{r['context_tokens']:.0f} | {fire} |")
    L.append("\nPer-item accuracy (mean over transcripts and both samples):\n")
    L.append("| Arm | " + " | ".join(ITEMS) + " |\n|---|" + "---|" * len(ITEMS))
    for a in ARMS:
        L.append(f"| {a} | " + " | ".join(f(res["arms"][a]["items"].get(k, float('nan'))) for k in ITEMS) + " |")
    L.append("\nSecondary outcome: items failed (both samples wrong, 0 to 5) per transcript, and the paired difference "
             "from the plain arm with a bootstrap 95% CI:\n")
    L.append("| Arm | Mean items failed | Difference vs plain [95% CI] |\n|---|---|---|")
    for a in ARMS:
        s = res["failed_items"][a]
        L.append(f"| {a} | {f(s['mean_failed'])} | {f(s['diff_vs_plain'])} [{f(s['diff_ci'][0])}, {f(s['diff_ci'][1])}] |")
    L.append("\nPaired exact McNemar on harm, Holm-corrected over all 21 pairs (a_only = harmed under a but not b):\n")
    L.append("| a | b | a only | b only | p | p (Holm) |\n|---|---|---|---|---|---|")
    for p in res["mcnemar"]:
        L.append(f"| {p['a']} | {p['b']} | {p['a_only']} | {p['b_only']} | {p['p']:.4f} | {p['p_holm']:.4f} |")
    L.append("\nGate diagnostics (transcripts where the gate fired in at least one round):\n")
    L.append("| Arm | Fired | Harm when fired | Plain-arm harm on the same transcripts | Not fired | Harm when not fired |\n|---|---|---|---|---|---|")
    for a, d in res["gate_diag"].items():
        L.append(f"| {a} | {d['n_fired']} | {d['harm_when_fired']} | {d['plain_harm_same_transcripts']} | {d['n_not_fired']} | {d['harm_when_not_fired']} |")
    qc = res["generic_question_categories"]
    L.append(f"\nWhat the generic round-trip questions ask about (first matching keyword class, {qc['n']} questions "
             "from the final round of every transcript):\n")
    L.append("| Class | Questions |\n|---|---|")
    for k, v in qc["counts"].items():
        L.append(f"| {k} | {v} ({100 * v / max(1, qc['n']):.0f}%) |")
    (OUT / "results.md").write_text("\n".join(L) + "\n")


def write_svg(res):
    pts = [(a, res["arms"][a]["tokens"], res["arms"][a]["rate"]) for a in ARMS if a != "full"]
    if not pts:
        return
    W, H, P = 640, 400, 60
    xmax = max(p[1] for p in pts) * 1.1 or 1
    X = lambda v: P + (W - 2 * P) * v / xmax
    Y = lambda v: H - P - (H - 2 * P) * v
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<line x1="{P}" y1="{H - P}" x2="{W - P}" y2="{H - P}" stroke="#333"/>',
         f'<line x1="{P}" y1="{P}" x2="{P}" y2="{H - P}" stroke="#333"/>',
         f'<text x="{W / 2}" y="{H - 20}" text-anchor="middle">compaction pipeline tokens per transcript</text>',
         f'<text x="18" y="{H / 2}" transform="rotate(-90 18 {H / 2})" text-anchor="middle">harm rate (evaluation split)</text>']
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        s.append(f'<text x="{P - 8}" y="{Y(v) + 4}" text-anchor="end">{v:.2f}</text>')
    full = res["arms"]["full"]["rate"]
    s.append(f'<line x1="{P}" y1="{Y(full)}" x2="{W - P}" y2="{Y(full)}" stroke="#999" stroke-dasharray="4 4"/>')
    s.append(f'<text x="{W - P}" y="{Y(full) - 6}" text-anchor="end" fill="#666">full-context ceiling</text>')
    for a, x, y in pts:
        s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="5" fill="#2a6fb0"/>')
        s.append(f'<text x="{X(x) + 8}" y="{Y(y) - 6}">{a} ({x:.0f})</text>')
    s.append("</svg>")
    (OUT / "pareto.svg").write_text("\n".join(s))


def write_examples(E):
    """A few transcripts where the round-trip gate fired: what it flagged and whether the outcome changed."""
    ex = []
    for r in E:
        for a in ("rt_gate", "rt_patch", "pc_gate"):
            rd = [x for x in r["arms"][a]["rounds"] if x["fired"]]
            if not rd:
                continue
            ex.append(dict(tid=r["tid"], arm=a, plain_harm=harm(r["arms"]["plain"]), arm_harm=harm(r["arms"][a]),
                           plain_items=item_scores(r["arms"]["plain"]), arm_items=item_scores(r["arms"][a]),
                           fired_rounds=[i for i, x in enumerate(r["arms"][a]["rounds"]) if x["fired"]],
                           first_flag=dict(score=rd[0]["score"],
                                           notes=rd[0]["signal"].get("flagged") or rd[0]["signal"].get("divergences"),
                                           questions=rd[0]["signal"].get("questions")),
                           plain_final=r["arms"]["plain"]["summary"], arm_final=r["arms"][a]["summary"]))
    (OUT / "examples.json").write_text(json.dumps(ex, indent=1))


if __name__ == "__main__":
    main()
