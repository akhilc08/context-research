"""Analyze E4 results: accuracy, stale rate, cost, watchpoint behavior, extraction errors,
judge validation. Writes results/per_task.json and results/summary.json, prints tables.

    /private/tmp/supersede-venv/bin/python analyze.py
"""
import json, math, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/private/tmp/supersede/src")
from supersede.scoring import classify, normalize  # noqa: E402

UNITS = HERE / "results" / "units"
SUFFIX = ""  # set by --model for a second-backbone tree
USAGE = HERE.parent / "shared" / "usage.jsonl"
ARMS = ["full", "notes300", "notes1200", "pin", "watch", "kvonly"]
COST_UNITS = {"full": ["full"], "notes300": ["notes300"], "notes1200": ["notes1200"],
              "pin": ["notes300", "extract", "pin"], "watch": ["extract", "watch"],
              "kvonly": ["extract", "kvonly"]}
FOLLOW = {"watch_strict": "judge_strict", "pin_dd": "judge_dd", "watch_dd": "judge_dd", "kvonly_dd": "judge_dd"}
COST_UNITS.update({"watch_strict": ["extract", "watch_strict"], "pin_dd": ["notes300", "extract", "extract_dd", "pin_dd"],
                   "watch_dd": ["extract", "extract_dd", "watch_dd"], "kvonly_dd": ["extract", "extract_dd", "kvonly_dd"]})
FPAIRS = [("watch_strict", "watch"), ("watch_strict", "pin"), ("watch_strict", "notes300"), ("pin_dd", "pin"),
          ("watch_dd", "watch"), ("watch_dd", "pin"), ("kvonly_dd", "kvonly")]
PAIRS = [("notes300", "full"), ("notes1200", "notes300"), ("pin", "notes300"), ("watch", "notes300"),
         ("pin", "watch"), ("pin", "notes1200"), ("watch", "notes1200"), ("pin", "full"),
         ("watch", "full"), ("kvonly", "pin")]
NUMW = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten "
                                        "eleven twelve".split())}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar(a, b):
    """Exact two-sided McNemar on paired booleans. Returns (b_only, a_only, p)."""
    x = sum(1 for i, j in zip(a, b) if i and not j)
    y = sum(1 for i, j in zip(a, b) if j and not i)
    n = x + y
    if n == 0:
        return x, y, 1.0
    k = min(x, y)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return x, y, min(1.0, p)


def kappa(pairs):
    """Cohen's kappa for a list of (bool, bool)."""
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def holm(ps):
    """Holm step-down adjusted p-values, same order as input."""
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def boot_diff(a, b, B=4000, seed=0):
    rng = random.Random(seed)
    n = len(a)
    ds = []
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        ds.append(sum(a[i] - b[i] for i in idx) / n)
    ds.sort()
    return ds[int(0.025 * B)], ds[int(0.975 * B)]


def numnorm(s):
    return " ".join(NUMW.get(w, w) for w in normalize(str(s)).split())


def load_usage():
    """Token use per (set, qid, unit). A unit rerun (smoke tests) overwrites earlier calls."""
    last = {}
    for line in USAGE.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        parts = r.get("tag", "").split("|")
        if len(parts) == 5 and parts[0] == "e4" and parts[1].endswith(SUFFIX) and ("@" in parts[1]) == bool(SUFFIX):
            parts[1] = parts[1][:len(parts[1]) - len(SUFFIX)] if SUFFIX else parts[1]
            last[tuple(parts[1:])] = r
    tok = defaultdict(lambda: [0, 0, 0])  # (set,qid,unit) -> in,out,calls
    for (s, q, unit, _), r in last.items():
        k = tok[(s, q, unit)]
        k[0] += r.get("in") or 0
        k[1] += r.get("out") or 0
        k[2] += 1
    return tok


def synth_store_status(t, store):
    """For synthetic tasks: does the final KV store hold the queried fact's current value?"""
    subj = re.search(r"'(\w+) ", t["question"]).group(1).lower()
    vals = [v for k, v in store.items() if k.split("|")[0].strip().startswith(subj)]
    if not vals:
        return "missing"
    verdicts = [classify(v, t["answer"], t["stale"]) for v in vals]
    if "correct" in verdicts and "stale" not in verdicts:
        return "correct"
    if "stale" in verdicts and "correct" not in verdicts:
        return "stale"
    return "ambiguous" if "correct" in verdicts else "wrong"


def main():
    global UNITS, SUFFIX, OUT
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    a = ap.parse_args()
    OUT = HERE / "results"
    if a.model != "stealth/space-bunny-alpha":
        safe = re.sub(r"[^\w]+", "_", a.model)
        UNITS, SUFFIX, OUT = HERE / "results" / f"units_{safe}", f"@{safe}", HERE / "results" / f"analysis_{safe}"
        OUT.mkdir(exist_ok=True)
    meta = json.loads((HERE / "results" / "tasks_meta.json").read_text())
    tok = load_usage()
    per_task, summary = [], {}
    for t in meta:
        d = UNITS / t["set"] / t["qid"]
        if not (d / "judge.json").exists():
            continue
        u = {a: json.loads((d / f"{a}.json").read_text()) for a in ARMS}
        ext = json.loads((d / "extract.json").read_text())
        jd = json.loads((d / "judge.json").read_text())
        rec = {k: t[k] for k in ("set", "qid", "question", "answer", "stale", "n_sessions", "chars")}
        rec["stale_label"] = jd.get("stale_label", t["stale"])
        rec["store_size"] = ext["store_size"]
        rec["store_chars"] = ext["store_chars"]
        rec["watch_rounds"] = [{k: r[k] for k in ("keys", "ok", "missing", "differs")} for r in u["watch"]["rounds"]]
        rec["watch_memory_chars"] = u["watch"]["memory_chars"]
        rec["pin_memory_chars"] = u["pin"]["memory_chars"]
        rec["notes300_chars"] = len(u["notes300"]["notes"])
        rec["notes1200_chars"] = len(u["notes1200"]["notes"])
        if t["set"] != "lme":
            rec["store_status"] = synth_store_status(t, ext["snapshots"][-1])
        rec["arms"] = {}
        for a, jf in FOLLOW.items():
            if (d / f"{a}.json").exists() and (d / f"{jf}.json").exists():
                u[a] = json.loads((d / f"{a}.json").read_text())
                jd[a] = json.loads((d / f"{jf}.json").read_text())[a]
        if "watch_strict" in u:
            rec["watch_strict_memory_chars"] = u["watch_strict"]["memory_chars"]
            rec["watch_strict_rounds"] = [{k: r[k] for k in ("keys", "ok")} for r in u["watch_strict"]["rounds"]]
        for a in [x for x in ARMS + list(FOLLOW) if x in u]:
            ans = u[a]["answer"]
            r = {"answer": ans, "judge_yes": jd[a]["yes"]}
            if t["set"] == "lme":
                r["correct"] = jd[a]["yes"]
                r["v4"] = jd[a].get("v4")
                r["stale"] = r["v4"] == "stale"
                r["amb"] = r["v4"] == "ambiguous"
                r["string_verdict"] = classify(ans, t["answer"], [])
                r["string_numnorm"] = numnorm(t["answer"]) in numnorm(ans)
            else:
                v = classify(ans, t["answer"], t["stale"])
                r.update(verdict=v, correct=v == "correct", stale=v == "stale", amb=v == "ambiguous")
            cin = cout = calls = 0
            for unit in COST_UNITS[a]:
                i, o, c = tok.get((t["set"], t["qid"], unit), (0, 0, 0))
                cin += i; cout += o; calls += c
            r.update(tok_in=cin, tok_out=cout, calls=calls)
            rec["arms"][a] = r
        per_task.append(rec)
    (OUT / "per_task.json").write_text(json.dumps(per_task, indent=1))

    out = []
    P = out.append
    for s in ["lme", "synth_std", "synth_hard"]:
        R = [r for r in per_task if r["set"] == s]
        if not R:
            continue
        n = len(R)
        S = summary[s] = {"n": n, "arms": {}, "pairs": {}}
        P(f"\n## {s} (n={n})\n")
        if s == "lme":
            lab = [r for r in R if r["stale_label"]]
            P(f"Tasks with a judge-labeled wrong-version value: {len(lab)}")
        P("| arm | acc | 95% CI | stale | 95% CI | ambiguous (both values) | mean tok in | mean tok out | mean calls |")
        P("|---|---|---|---|---|---|---|---|---|")
        for a in ARMS:
            k = sum(r["arms"][a]["correct"] for r in R)
            base = [r for r in R if (s != "lme" or r["stale_label"])]
            st = sum(r["arms"][a]["stale"] for r in base)
            lo, hi = wilson(k, n)
            slo, shi = wilson(st, len(base))
            ti = sum(r["arms"][a]["tok_in"] for r in R) / n
            to = sum(r["arms"][a]["tok_out"] for r in R) / n
            ca = sum(r["arms"][a]["calls"] for r in R) / n
            S["arms"][a] = {"acc": k / n, "k": k, "ci": [lo, hi], "stale": st / max(1, len(base)),
                            "stale_k": st, "stale_n": len(base), "stale_ci": [slo, shi],
                            "tok_in": ti, "tok_out": to, "calls": ca}
            am = sum(r["arms"][a]["amb"] for r in base)
            S["arms"][a]["amb_k"] = am
            P(f"| {a} | {k}/{n} = {k / n:.1%} | {lo:.0%} to {hi:.0%} | {st}/{len(base)} = {st / max(1, len(base)):.1%} "
              f"| {slo:.0%} to {shi:.0%} | {am}/{len(base)} | {ti:,.0f} | {to:,.0f} | {ca:.1f} |")
        P(f"\n| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p ({len(PAIRS)} tests) | diff 95% CI |")
        P("|---|---|---|---|---|---|---|")
        rows = []
        for a, b in PAIRS:
            xa = [int(r["arms"][a]["correct"]) for r in R]
            xb = [int(r["arms"][b]["correct"]) for r in R]
            ao, bo, p = mcnemar(xa, xb)
            lo, hi = boot_diff(xa, xb)
            rows.append((a, b, xa, xb, ao, bo, p, lo, hi))
        for (a, b, xa, xb, ao, bo, p, lo, hi), padj in zip(rows, holm([x[6] for x in rows])):
            S["pairs"][f"{a}-{b}"] = {"a_only": ao, "b_only": bo, "p": p, "p_holm": padj, "diff_ci": [lo, hi]}
            P(f"| {a} vs {b} | {sum(xa)} to {sum(xb)} | {ao} | {bo} | {p:.3g} | {padj:.3g} | {lo:+.1%} to {hi:+.1%} |")
        # stale McNemar for synthetic
        if s != "lme":
            P("\n| stale pair | A only stale | B only stale | McNemar p |")
            P("|---|---|---|---|")
            for a, b in [("notes300", "full"), ("pin", "notes300"), ("watch", "notes300"), ("notes1200", "notes300")]:
                xa = [r["arms"][a]["stale"] for r in R]
                xb = [r["arms"][b]["stale"] for r in R]
                ao, bo, p = mcnemar(xa, xb)
                P(f"| {a} vs {b} | {ao} | {bo} | {p:.3g} |")
        # memory sizes and watchpoint behaviour
        mean = lambda xs: sum(xs) / max(1, len(xs))
        rounds = [x for r in R for x in r["watch_rounds"] if x["keys"]]
        mem = {"notes300_chars": mean([r["notes300_chars"] for r in R]),
               "notes1200_chars": mean([r["notes1200_chars"] for r in R]),
               "store_size": mean([r["store_size"] for r in R]),
               "store_chars": mean([r["store_chars"] for r in R]),
               "pin_memory_chars": mean([r["pin_memory_chars"] for r in R]),
               "watch_memory_chars": mean([r["watch_memory_chars"] for r in R]),
               "watch_rounds": len(rounds),
               "watch_rounds_with_patch": sum(x["ok"] < x["keys"] for x in rounds),
               "watch_keys_checked": sum(x["keys"] for x in rounds),
               "watch_keys_missing": sum(x["missing"] for x in rounds),
               "watch_keys_differs": sum(x["differs"] for x in rounds)}
        S["memory"] = mem
        P(f"\nMemory at answer time: notes300 {mem['notes300_chars']:.0f} chars, notes1200 {mem['notes1200_chars']:.0f} chars; KV store {mem['store_size']:.1f} facts / {mem['store_chars']:.0f} chars; "
          f"pin memory {mem['pin_memory_chars']:.0f} chars; watch memory {mem['watch_memory_chars']:.0f} chars. "
          f"Watch rounds with any patch: {mem['watch_rounds_with_patch']}/{mem['watch_rounds']}; "
          f"keys checked {mem['watch_keys_checked']}, missing {mem['watch_keys_missing']}, "
          f"differs {mem['watch_keys_differs']}.")
        # extraction failure analysis
        kv_ok = [r["arms"]["kvonly"]["correct"] for r in R]
        P(f"\nKV store alone answers correctly: {sum(kv_ok)}/{n}.")
        if s != "lme":
            from collections import Counter
            c = Counter(r["store_status"] for r in R)
            S["store_status"] = dict(c)
            P(f"Final KV store value for the queried fact (exact grader): {dict(c)}")
        for a in ["pin", "watch"]:
            fails = [r for r in R if not r["arms"][a]["correct"]]
            kvbad = sum(not r["arms"]["kvonly"]["correct"] for r in fails)
            S.setdefault("fail_attrib", {})[a] = {"fails": len(fails), "kv_also_wrong": kvbad}
            P(f"{a} failures: {len(fails)}; of these the KV store alone was also wrong on {kvbad}.")
    # exploratory: LongMemEval questions about an OLD value (overwrite semantics discard it)
    H = re.compile(r"previous(?! company)|previously|initially|increase or decrease|more water|when i just started|"
                   r"earlier|first three months|before i", re.I)
    R = [r for r in per_task if r["set"] == "lme"]
    if R:
        hist = [r for r in R if H.search(r["question"]) and "not enough" not in r["answer"].lower()]
        rest = [r for r in R if r not in hist]
        allarms = [a for a in ARMS + list(FOLLOW) if all(a in r["arms"] for r in R)]
        P("\n## Exploratory: LongMemEval split by whether the question asks about an older value\n")
        P(f"History questions (regex on the question, abstention items excluded): n={len(hist)}; others: n={len(rest)}.\n")
        P("| arm | history acc | 95% CI | other acc | 95% CI |")
        P("|---|---|---|---|---|")
        summary["lme_history_split"] = {"hist_qids": [r["qid"] for r in hist]}
        for a in allarms:
            kh, ko = sum(r["arms"][a]["correct"] for r in hist), sum(r["arms"][a]["correct"] for r in rest)
            (hl, hh), (ol, oh) = wilson(kh, len(hist)), wilson(ko, len(rest))
            summary["lme_history_split"][a] = {"hist_k": kh, "hist_n": len(hist), "other_k": ko, "other_n": len(rest)}
            P(f"| {a} | {kh}/{len(hist)} | {hl:.0%} to {hh:.0%} | {ko}/{len(rest)} | {ol:.0%} to {oh:.0%} |")
        for a, b in [("pin", "notes300"), ("pin", "full"), ("notes1200", "pin")]:
            for name, G in [("other", rest), ("history", hist)]:
                ao, bo, p = mcnemar([r["arms"][a]["correct"] for r in G], [r["arms"][b]["correct"] for r in G])
                P(f"- {name}: {a} vs {b}: {ao} vs {bo} discordant, McNemar p={p:.3g} (uncorrected, exploratory)")
    # exploratory: synthetic split by predicate ("is now allergic to" reads as an addition, not a replacement)
    R = [r for r in per_task if r["set"] != "lme"]
    if R:
        allarms = [a for a in ARMS + list(FOLLOW) if all(a in r["arms"] for r in R)]
        P("\n## Exploratory: synthetic tasks (both configs pooled) split by queried predicate\n")
        P("| arm | allergy: correct / stale / ambiguous / wrong | other predicates: correct / stale / ambiguous / wrong |")
        P("|---|---|---|")
        for a in allarms:
            cells = []
            for G in ([r for r in R if "allergic" in r["question"]], [r for r in R if "allergic" not in r["question"]]):
                c = Counter(r["arms"][a]["verdict"] for r in G)
                cells.append(f"{c['correct']} / {c['stale']} / {c['ambiguous']} / {c['wrong']} (n={len(G)})")
            P(f"| {a} | {cells[0]} | {cells[1]} |")
    # exploratory follow-ups
    P("\n## Exploratory follow-ups (decided after seeing the main results)\n")
    for s in ["lme", "synth_std", "synth_hard"]:
        R = [r for r in per_task if r["set"] == s]
        arms = [a for a in FOLLOW if R and all(a in r["arms"] for r in R)]
        if not arms:
            continue
        n = len(R)
        base = [r for r in R if (s != "lme" or r["stale_label"])]
        F = summary[s]["followups"] = {"arms": {}, "pairs": {}}
        P(f"\n### {s} (n={n})\n")
        P("| arm | acc | 95% CI | stale | ambiguous | mean tok in | mean tok out | mean calls | mean memory chars |")
        P("|---|---|---|---|---|---|---|---|---|")
        for a in arms:
            k = sum(r["arms"][a]["correct"] for r in R)
            lo, hi = wilson(k, n)
            st = sum(r["arms"][a]["stale"] for r in base)
            am = sum(r["arms"][a]["amb"] for r in base)
            ti, to, ca = (sum(r["arms"][a][f] for r in R) / n for f in ("tok_in", "tok_out", "calls"))
            mc = (sum(r.get("watch_strict_memory_chars", 0) for r in R) / n) if a == "watch_strict" else float("nan")
            F["arms"][a] = {"k": k, "acc": k / n, "ci": [lo, hi], "stale_k": st, "amb_k": am, "stale_n": len(base),
                            "tok_in": ti, "tok_out": to, "calls": ca}
            P(f"| {a} | {k}/{n} = {k / n:.1%} | {lo:.0%} to {hi:.0%} | {st}/{len(base)} | {am}/{len(base)} | {ti:,.0f} | {to:,.0f} | {ca:.1f} | {mc:.0f} |")
        if "watch_strict" in arms:
            rr = [x for r in R for x in r["watch_strict_rounds"] if x["keys"]]
            P(f"\nwatch_strict rounds with any patch: {sum(x['ok'] < x['keys'] for x in rr)}/{len(rr)}; "
              f"keys patched {sum(x['keys'] - x['ok'] for x in rr)}/{sum(x['keys'] for x in rr)}.")
        fp = [(a, b) for a, b in FPAIRS if a in arms]
        rows = []
        for a, b in fp:
            xa = [int(r["arms"][a]["correct"]) for r in R]
            xb = [int(r["arms"][b]["correct"]) for r in R]
            rows.append((a, b, xa, xb) + mcnemar(xa, xb) + boot_diff(xa, xb))
        P(f"\n| pair (A vs B) | acc A to B | A only | B only | McNemar p | Holm p ({len(rows)} tests) | diff 95% CI |")
        P("|---|---|---|---|---|---|---|")
        for (a, b, xa, xb, ao, bo, p, lo, hi), padj in zip(rows, holm([x[6] for x in rows])):
            F["pairs"][f"{a}-{b}"] = {"a_only": ao, "b_only": bo, "p": p, "p_holm": padj, "diff_ci": [lo, hi]}
            P(f"| {a} vs {b} | {sum(xa)} to {sum(xb)} | {ao} | {bo} | {p:.3g} | {padj:.3g} | {lo:+.1%} to {hi:+.1%} |")
    # judge validation
    P("\n## Judge validation\n")
    syn = [(r["arms"][a]["judge_yes"], r["arms"][a]["correct"]) for r in per_task if r["set"] != "lme" for a in ARMS]
    agree = sum(j == c for j, c in syn)
    P(f"Synthetic (exact grader as reference): agreement {agree}/{len(syn)} = {agree / max(1, len(syn)):.1%}; "
      f"judge yes & grader not correct: {sum(j and not c for j, c in syn)}; judge no & grader correct: {sum(c and not j for j, c in syn)}")
    reliable = [r for r in per_task if r["set"] == "lme" and len(normalize(r["answer"]).split()) <= 3
                and "not enough" not in r["answer"].lower()]
    pairs = [(r["arms"][a]["judge_yes"], r["arms"][a]["string_numnorm"], r, a) for r in reliable for a in ARMS]
    ag = sum(j == st for j, st, _, _ in pairs)
    P(f"LongMemEval, {len(reliable)} tasks with short golds (3 words or fewer, not abstention), x {len(ARMS)} arms: "
      f"judge vs number-normalized string containment agreement {ag}/{len(pairs)} = {ag / max(1, len(pairs)):.1%}.")
    raw = sum(j == (r["arms"][a]["string_verdict"] == "correct") for j, _, r, a in pairs)
    P(f"Judge vs Supersede's unmodified string grader on the same set: {raw}/{len(pairs)} = {raw / max(1, len(pairs)):.1%}.")
    dis = [(r["qid"], a, r["answer"], r["arms"][a]["answer"][:160], j) for j, st, r, a in pairs if j != st]
    summary["judge_validation"] = {"synthetic_agree": agree, "synthetic_n": len(syn), "lme_reliable_tasks": len(reliable),
                                   "lme_agree": ag, "lme_n": len(pairs), "lme_raw_agree": raw,
                                   "disagreements": dis}
    syn_k, lme_k = kappa([(j, c) for j, c in syn]), kappa([(j, st) for j, st, _, _ in pairs])
    P(f"Cohen's kappa: synthetic {syn_k:.3f}; LongMemEval short-gold string check {lme_k:.3f}.")
    hl = HERE / "results" / "hand_labels.json"
    if hl.exists():
        smp = {(x["qid"], x["arm"]): x for x in json.loads((HERE / "results" / "hand_label_sample.json").read_text())}
        hp = [(smp[(x["qid"], x["arm"])]["judge_yes"], x["human_correct"]) for x in json.loads(hl.read_text())["labels"]]
        ha = sum(a == b for a, b in hp)
        summary["judge_validation"].update(hand_n=len(hp), hand_agree=ha, hand_kappa=kappa(hp),
                                           hand_yes=sum(b for _, b in hp))
        P(f"Hand labels (stratified sample of {len(hp)} LongMemEval answers, 24 judge-yes and 24 judge-no, seed 7): "
          f"agreement {ha}/{len(hp)}, Cohen's kappa {kappa(hp):.3f}.")
    hl4 = HERE / "results" / "hand_labels_v4.json"
    if hl4.exists():
        smp = {(x["qid"], x["arm"]): x for x in json.loads((HERE / "results" / "hand_label_sample_v4.json").read_text())}
        hp = [(smp[(x["qid"], x["arm"])]["judge_v4"], x["human_v4"]) for x in json.loads(hl4.read_text())["labels"]]
        ag4 = sum(a == b for a, b in hp)
        ks = kappa([(a == "stale", b == "stale") for a, b in hp])
        summary["judge_validation"].update(v4_hand_n=len(hp), v4_hand_agree=ag4, v4_stale_kappa=ks)
        P(f"Four-way stale judge vs hand labels ({len(hp)} answers: 20 judged stale, 12 wrong, 8 correct, 4 ambiguous; seed 11): "
          f"exact 4-way agreement {ag4}/{len(hp)}; stale-vs-not agreement "
          f"{sum((a == 'stale') == (b == 'stale') for a, b in hp)}/{len(hp)}, Cohen's kappa {ks:.3f}.")
    summary["judge_validation"].update(synthetic_kappa=syn_k, lme_string_kappa=lme_k)
    P("Disagreements with the string check (qid, arm, gold, answer, judge):")
    for x in dis:
        P(f"- {x[0]} {x[1]} gold={x[2]!r} judge={'yes' if x[4] else 'no'} ans={x[3]!r}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    text = "\n".join(out)
    (OUT / "tables.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
