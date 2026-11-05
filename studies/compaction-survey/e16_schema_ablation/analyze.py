"""Regenerate every E16 table from raw/ and judged/ (no model calls).

Writes results.md, results.json, examples.json.
Usage: python3 analyze.py   (env E16_OUT for a rerun directory)
"""
import json, math, os, random, re, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("E16_OUT", str(HERE)))
ITEMS = ["rule0", "rule1", "approach", "fact", "goal", "plan"]
SECS = ["S1", "S2", "S3", "S4", "S5", "S6"]
SEC_ITEMS = {"S1": ["rule0", "rule1"], "S2": ["goal"], "S3": ["fact"], "S4": ["approach"], "S5": ["plan"], "S6": []}
ARM_ORDER = ["plain", "e9_structured", "schema"] + [f"loo_{s}" for s in SECS] + [f"add_{s}" for s in SECS[:5]] + \
    ["pin", "schema_pin", "minimal", "minimal_pin", "full"]
HEADINGS = {"S1": "Standing operator rules", "S2": "Current objective", "S3": "Key identifiers",
            "S4": "Ruled-out approaches", "S5": "Plan and progress", "S6": "Recent work"}

# ---------------------------------------------------------------- stats

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n; d = 1 + z * z / n; c = ph + z * z / (2 * n)
    r = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def rate(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.0f}% [{100 * lo:.0f} to {100 * hi:.0f}]" if n else "n/a"


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
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def boot_diff(a, b, reps=4000, seed=1):
    """95% CI of mean(a - b) for paired per-transcript values."""
    rng = random.Random(seed)
    n = len(a)
    d = [x - y for x, y in zip(a, b)]
    ms = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return sum(d) / n, ms[int(0.025 * reps)], ms[int(0.975 * reps) - 1]

# ---------------------------------------------------------------- loading and labels

def load():
    labs = {}
    for fp in (OUT / "judged").glob("t*.json"):
        labs[int(fp.stem[1:])] = json.loads(fp.read_text())
    data = defaultdict(dict)   # (R, W) -> {arm: {tid: rec}}
    for fp in (OUT / "raw").glob("r*_w*/t*/*.json"):
        rec = json.loads(fp.read_text())
        data[(rec["R"], rec["W"])].setdefault(rec["arm"], {})[rec["tid"]] = rec
    return data, labs


def sample_ok(item, s, rec, L):
    if item == "fact":
        return s["parsed"] == "CORRECT"
    if L is None:
        return None
    if item == "plan":
        v = L.get("plan", {}).get(s["cmd"])
        return None if v is None else (v["kind"] == "step" and v["index"] == rec["k"] + 1)
    v = L.get(item, {}).get(s["raw"])
    if v is None:
        return None
    return v == "NEW" if item == "goal" else v == "RESPECTS"


def scores(rec, labs):
    L = labs.get(rec["tid"], {}).get(str(rec["R"]))
    out = {}
    for it in ITEMS:
        vals = [sample_ok(it, s, rec, L) for s in rec["probes"][it]]
        if any(v is None for v in vals):
            return None
        out[it] = sum(vals) / len(vals)
    return out


def outcome(sc, items=ITEMS):
    return int(any(sc[i] == 0 for i in items))

# ---------------------------------------------------------------- summary shape

def words(t):
    return len(re.findall(r"\S+", t or ""))


def truncated(t):
    t = (t or "").rstrip()
    return bool(t) and t[-1] not in ".!?)`'\"*:]|" and not t.lower().endswith("none")


def section_words(summary):
    """Words per schema heading (only for summaries that use '## ' headings)."""
    parts = re.split(r"^#+\s*(.+)$", summary or "", flags=re.M)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        h = parts[i].strip()
        for s, name in HEADINGS.items():
            if name.lower() in h.lower():
                out[s] = words(parts[i + 1])
    return out

# ---------------------------------------------------------------- main

def condition_table(arms, labs, tset):
    """Arms that cover every transcript in tset (scored); rows paired on that set."""
    common = set(tset)
    arms = {a: recs for a, recs in arms.items()
            if all(t in recs and scores(recs[t], labs) is not None for t in tset)}
    tids = sorted(common or [])
    rows = {}
    for a in [x for x in ARM_ORDER if x in arms]:
        sc = [scores(arms[a][t], labs) for t in tids]
        recs = [arms[a][t] for t in tids]
        rows[a] = dict(
            n=len(tids), harm=[outcome(s) for s in sc], harm5=[outcome(s, ITEMS[:5]) for s in sc],
            failed=[sum(s[i] == 0 for i in ITEMS) for s in sc],
            item={i: [s[i] for s in sc] for i in ITEMS},
            words=[words(r["summary"]) for r in recs if r["summary"] is not None],
            ctx_tokens=[len(r["context"]) / 4 for r in recs],
            trunc=[truncated(r["summary"]) for r in recs if r["summary"] is not None],
            per_round_words=[[words(x) for x in r["per_round"]] for r in recs],
            secwords=[section_words(r["summary"]) for r in recs if r["summary"]])
    return tids, rows


FAMILY = [("schema", "plain"), ("schema", "e9_structured"), ("e9_structured", "plain")] + \
    [(f"loo_{s}", "schema") for s in SECS] + [(f"add_{s}", "plain") for s in SECS[:5]] + \
    [("pin", "plain"), ("schema_pin", "schema"), ("schema_pin", "pin")]


def mean(x):
    return sum(x) / len(x) if x else float("nan")


def goal_of(rec):
    """Goal index of the transcript (rebuilt with E16's seed, no model calls)."""
    sys.path.insert(0, str(HERE))
    import run_e16
    return run_e16.build(rec["tid"], rec["R"])["goal"]


def examples(data, labs):
    """A few seeded qualitative contrasts from the 3-round, 150-word selection set."""
    arms = data.get((3, 150), {})
    out = []
    def item_ok(a, t, it):
        sc = scores(arms[a][t], labs)
        return None if sc is None else sc[it]
    def section(text, name):
        m = re.search(r"#+\s*" + re.escape(name) + r".*?\n(.*?)(?=\n#|\Z)", text or "", re.S | re.I)
        return m.group(1).strip() if m else None
    for t in sorted(arms.get("schema", {})):
        if t >= 40:
            continue
        if item_ok("schema", t, "plan") == 0 and item_ok("pin", t, "plan") == 1 and len(out) < 2:
            out.append(dict(kind="schema loses plan, pin keeps it", tid=t, k=arms["schema"][t]["k"],
                            schema_plan_section=section(arms["schema"][t]["summary"], "Plan and progress"),
                            schema_commands=[s["cmd"] for s in arms["schema"][t]["probes"]["plan"]],
                            pin_commands=[s["cmd"] for s in arms["pin"][t]["probes"]["plan"]]))
    for t in sorted(arms.get("schema", {})):
        if t < 40 and item_ok("loo_S1", t, "rule0") == 0 and item_ok("schema", t, "rule0") == 1:
            out.append(dict(kind="dropping S1 loses a rule", tid=t,
                            schema_rules_section=section(arms["schema"][t]["summary"], "Standing operator rules"),
                            loo_S1_summary=arms["loo_S1"][t]["summary"],
                            loo_S1_answer=arms["loo_S1"][t]["probes"]["rule0"][0]["raw"]))
            break
    for t in sorted(arms.get("add_S1", {})):
        if t < 40 and item_ok("add_S1", t, "plan") == 1:
            out.append(dict(kind="S1 copies the procedure request as a standing rule", tid=t,
                            add_S1_rules_section=section(arms["add_S1"][t]["summary"], "Standing operator rules")))
            break
    for t in sorted(arms.get("schema", {})):
        if t < 40 and item_ok("schema", t, "goal") == 0 and item_ok("pin", t, "goal") == 1:
            out.append(dict(kind="schema states the wrong objective", tid=t,
                            objective_section=section(arms["schema"][t]["summary"], "Current objective"),
                            goal_answers=[s["raw"] for s in arms["schema"][t]["probes"]["goal"]]))
            break
    return out


def main():
    data, labs = load()
    md, res = ["# E16 results (generated by analyze.py)\n"], {}
    blocks = []
    for (R, W) in sorted(data):
        alltids = sorted({t for recs in data[(R, W)].values() for t in recs})
        if (R, W) == (3, 150):
            blocks.append((R, W, "selection set, transcripts 0 to 39", [t for t in alltids if t < 40], ""))
            blocks.append((R, W, "held-out confirmation, transcripts 40 to 69", [t for t in alltids if 40 <= t < 70],
                           "_holdout"))
        else:
            blocks.append((R, W, f"transcripts {alltids[0]} to {alltids[-1]}", alltids, ""))
    for (R, W, label, tset, suffix) in blocks:
        tids, rows = condition_table(data[(R, W)], labs, tset)
        if not tids or not rows:
            continue
        key = f"r{R}_w{W}{suffix}"
        res[key] = {}
        md.append(f"\n## {R} rounds, {W}-word budget, {label} (n = {len(tids)})\n")
        md.append("| Arm | Harm (6 items) [95% CI] | Harm without plan item | Mean items failed | Final summary words "
                  "(median) | Context tokens (mean) | Truncated |")
        md.append("|---|---|---|---|---|---|---|")
        for a, r in rows.items():
            ws = sorted(r["words"])
            med = ws[len(ws) // 2] if ws else 0
            md.append(f"| {a} | {rate(sum(r['harm']), r['n'])} | {rate(sum(r['harm5']), r['n'])} | "
                      f"{mean(r['failed']):.2f} | {med if ws else '-'} | {mean(r['ctx_tokens']):.0f} | "
                      f"{sum(r['trunc'])}/{len(r['trunc'])} |" if ws else
                      f"| {a} | {rate(sum(r['harm']), r['n'])} | {rate(sum(r['harm5']), r['n'])} | "
                      f"{mean(r['failed']):.2f} | - | {mean(r['ctx_tokens']):.0f} | - |")
            res[key][a] = dict(n=r["n"], harm=sum(r["harm"]), harm5=sum(r["harm5"]), failed=mean(r["failed"]),
                               item={i: mean(v) for i, v in r["item"].items()}, words_median=med if ws else None,
                               ctx_tokens=mean(r["ctx_tokens"]), truncated=sum(r["trunc"]))
        md.append("\nPer-item accuracy (mean over transcripts and both samples):\n")
        md.append("| Arm | " + " | ".join(ITEMS) + " |")
        md.append("|---" * (len(ITEMS) + 1) + "|")
        for a, r in rows.items():
            md.append(f"| {a} | " + " | ".join(f"{mean(r['item'][i]):.2f}" for i in ITEMS) + " |")

        # paired McNemar, Holm within this condition's pre-specified family
        fam = [(x, y) for x, y in FAMILY if x in rows and y in rows]
        fam += [(x, y) for x, y in (("minimal", "schema"), ("minimal", "plain"), ("minimal", "add_S1"),
                                    ("minimal_pin", "minimal"), ("minimal_pin", "pin"), ("minimal_pin", "schema_pin"))
                if x in rows and y in rows]
        if "full" in rows:
            fam += [("schema_pin", "full")]
        for outc, title in (("harm", "harm (primary, 6 items)"),
                            ("harm5", "harm without the plan item (added after the primary outcome saturated)")):
            if not fam:
                break
            stats = []
            for x, y in fam:
                b = sum(p and not q for p, q in zip(rows[x][outc], rows[y][outc]))
                c = sum(q and not p for p, q in zip(rows[x][outc], rows[y][outc]))
                stats.append((x, y, b, c, mcnemar(b, c)))
            adj = holm([st[4] for st in stats])
            md.append(f"\nPaired exact McNemar on {title}, Holm over these {len(stats)} comparisons:\n")
            md.append("| First | Second | Harmed only under first | Harmed only under second | p | Holm p |")
            md.append("|---|---|---|---|---|---|")
            res[key][f"_mcnemar_{outc}"] = []
            for (x, y, b, c, p), q in zip(stats, adj):
                md.append(f"| {x} | {y} | {b} | {c} | {p:.3g} | {q:.3g} |")
                res[key][f"_mcnemar_{outc}"].append(dict(a=x, b=y, only_a=b, only_b=c, p=p, holm=q))

        # marginal value per section and item
        if "schema" in rows and any(a.startswith(("loo_", "add_S2")) for a in rows):
            md.append("\nLeave-one-out drop (accuracy of full schema minus accuracy without the section; positive = "
                      "the section helps), and single-section gain (narrative plus the section minus plain). Mean "
                      "over transcripts with paired bootstrap 95% CIs. Bold marks the item the section targets.\n")
            md.append("| Section | Item | LOO drop [95% CI] | Single-section gain [95% CI] |")
            md.append("|---|---|---|---|")
            res[key]["_marginal"] = {}
            for s in SECS:
                for it in ITEMS + ["harm", "harm5"]:
                    cells = []
                    for arm, base, sign in ((f"loo_{s}", "schema", 1), (f"add_{s}", "plain", -1)):
                        if arm not in rows or base not in rows:
                            cells.append("-"); continue
                        if it in ("harm", "harm5"):
                            a_, b_ = [-h for h in rows[arm][it]], [-h for h in rows[base][it]]
                        else:
                            a_, b_ = rows[arm]["item"][it], rows[base]["item"][it]
                        m, lo, hi = boot_diff(b_, a_) if sign == 1 else boot_diff(a_, b_)
                        cells.append(f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]")
                        res[key]["_marginal"][f"{arm}|{it}"] = [m, lo, hi]
                    name = f"**{it}**" if it in SEC_ITEMS[s] else it
                    if it in ("harm", "harm5"):
                        name = "no harm" if it == "harm" else "no harm (5 items)"
                    md.append(f"| {s} | {name} | {cells[0]} | {cells[1]} |")

        # section length allocation
        sw = {a: r["secwords"] for a, r in rows.items() if r["secwords"] and any(r["secwords"])}
        if sw:
            md.append("\nWords per section in the final summary (mean over summaries that contain the heading; "
                      "share of summaries with the heading in parentheses):\n")
            md.append("| Arm | " + " | ".join(SECS) + " |")
            md.append("|---" * 7 + "|")
            for a, lst in sw.items():
                if not a.startswith(("schema", "loo", "add", "minimal")):
                    continue
                cells = []
                for s in SECS:
                    v = [d[s] for d in lst if s in d]
                    cells.append(f"{mean(v):.0f} ({100 * len(v) / len(lst):.0f}%)" if v else "-")
                md.append(f"| {a} | " + " | ".join(cells) + " |")
        md.append("\nFinal summary words by round (median over transcripts):\n")
        md.append("| Arm | " + " | ".join(f"R{i + 1}" for i in range(R)) + " |")
        md.append("|---" * (R + 1) + "|")
        for a, r in rows.items():
            if r["per_round_words"] and r["per_round_words"][0]:
                cols = list(zip(*r["per_round_words"]))
                md.append(f"| {a} | " + " | ".join(str(sorted(c)[len(c) // 2]) for c in cols) + " |")

    # cross-condition contrasts (budget and rounds), paired on shared transcripts
    md.append("\n## Budget and rounds interactions (harm without the plan item; plan accuracy in the per-condition tables)\n")
    md.append("| Arm | Contrast | n | Harm A | Harm B | A-only | B-only | McNemar p |")
    md.append("|---|---|---|---|---|---|---|---|")
    res["_interactions"] = []
    for A, B, label in (((3, 150), (3, 300), "150 vs 300 words, 3 rounds"),
                        ((3, 150), (6, 150), "3 vs 6 rounds, 150 words")):
        if A not in data or B not in data:
            continue
        for a in ARM_ORDER:
            if a not in data[A] or a not in data[B]:
                continue
            ts = sorted(t for t in set(data[A][a]) & set(data[B][a])
                        if scores(data[A][a][t], labs) and scores(data[B][a][t], labs))
            if not ts:
                continue
            ha = [outcome(scores(data[A][a][t], labs), ITEMS[:5]) for t in ts]
            hb = [outcome(scores(data[B][a][t], labs), ITEMS[:5]) for t in ts]
            b = sum(x and not y for x, y in zip(ha, hb)); c = sum(y and not x for x, y in zip(ha, hb))
            md.append(f"| {a} | {label} | {len(ts)} | {sum(ha)} | {sum(hb)} | {b} | {c} | {mcnemar(b, c):.3g} |")
            res["_interactions"].append(dict(arm=a, contrast=label, n=len(ts), harm_a=sum(ha), harm_b=sum(hb),
                                             only_a=b, only_b=c, p=mcnemar(b, c)))
    # diagnostic: does the S2 "Current objective" section name the redirected goal? (file path of the new goal)
    sys.path.insert(0, str(HERE.parent / "e09_cheap_validation"))
    from items import GOALS
    md.append("\n## Diagnostic: does the objective section name the redirected goal?\n")
    md.append("Share of final summaries whose 'Current objective' section contains the file path of the operator's "
              "latest goal, and goal-probe accuracy within each group.\n")
    md.append("| Condition | Arm | Section names new goal | Goal accuracy when it does | Goal accuracy when it does not |")
    md.append("|---|---|---|---|---|")
    for (R, W) in sorted(data):
        for a in ("schema", "loo_S6", "add_S2", "minimal", "schema_pin", "minimal_pin"):
            recs = [r for t, r in sorted(data[(R, W)].get(a, {}).items()) if t < 40 and scores(r, labs)]
            if not recs:
                continue
            yes, no = [], []
            for r in recs:
                path = re.search(r"ledgerly/\S+\.py", GOALS[goal_of(r)][3]).group(0)
                m = re.search(r"#+\s*Current objective.*?\n(.*?)(?=\n#|\Z)", r["summary"] or "", re.S | re.I)
                (yes if m and path in m.group(1) else no).append(scores(r, labs)["goal"])
            md.append(f"| r{R}_w{W} | {a} | {len(yes)}/{len(recs)} | {mean(yes):.2f} | {mean(no):.2f} |")
    (OUT / "examples.json").write_text(json.dumps(examples(data, labs), indent=1))
    (OUT / "results.md").write_text("\n".join(md) + "\n")
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    main()
