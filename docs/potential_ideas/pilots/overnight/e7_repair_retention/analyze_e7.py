"""Analysis for E7. Reads raw/*.json, prints markdown tables, writes results.json."""
import json, math, random, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import fisher_two_sided, wilson  # noqa: E402

import argparse  # noqa: E402

AP = argparse.ArgumentParser()
AP.add_argument("--raw", default="raw", help="raw directory (raw_<model> for a second backbone)")
AP.add_argument("--labels", default="judge1", choices=["judge1", "consensus"],
                help="judge1: primary judge; consensus: keep only rules where both judges agree")
ARGS = AP.parse_args()
HERE = Path(__file__).resolve().parent
RAW = HERE / ARGS.raw
LEVELS = [400, 200, 100, 50, 25]
KS = [1, 2, 4, 8]
BOOT = 2000


def L(name):
    return json.loads((RAW / f"{name}.json").read_text())


T = L("transcripts")
LAB1 = L("labels")
LAB2 = L("labels2") if (RAW / "labels2.json").exists() else None
if ARGS.labels == "consensus":
    LAB = {k: v for k, v in LAB1.items() if LAB2 and k in LAB2 and LAB2[k]["present"] == v["present"]}
else:
    LAB = LAB1
REP = L("repairs")
META = L("contexts_meta")
DEC = L("decisions")
SUM = L("summaries")
AUD = L("audit") if (RAW / "audit.json").exists() else {}
TIDS = [t["tid"] for t in T]
POS = {t["tid"]: t["rule_pos"] for t in T}


def toks(s):
    return max(1, round(len(s) / 4))


BODY_TOK = {t["tid"]: toks("\n".join(t["turns"][:-4])) for t in T}


def fmt(k, n):
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100*k/n:.0f}% [{100*lo:.0f}, {100*hi:.0f}]"


def mcnemar(b, c):
    """Exact two-sided McNemar on discordant counts b (yes->no) and c (no->yes)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def rows(arm, level, k, kind="trigger"):
    """List of (tid, rid, violated/refused bool, rtype, in_tail) for one cell."""
    out = []
    for tid in TIDS:
        if arm == "control":
            ck = f"{tid}|ctrl"
        elif arm == "floor":
            ck = f"{tid}|floor"
        elif arm == "pin":
            ck = f"{tid}|{level}|pin"
        else:
            ck = f"{tid}|{level}|{'rep' if arm == 'repair' or k == 0 else 'ret'}{k}"
        m = META.get(ck)
        if m is None:
            continue
        for rid, pos in POS[tid].items():
            d = DEC.get(f"{ck}|{rid}|{kind}")
            if not d or d["d"] == "UNKNOWN":
                continue
            bad = d["d"] == "COMPLY" if kind == "trigger" else d["d"] == "REFUSE"
            rtype = None
            if level:
                lab = LAB.get(f"{tid}|{level}|{rid}")
                if lab is None:
                    continue
                rtype = "retrieval" if lab["present"] else "deletion"
            in_tail = m.get("tail_start_idx", 10**6) <= pos
            out.append((tid, rid, bad, rtype, in_tail))
    return out


def count(rs, f=lambda r: True):
    sel = [r for r in rs if f(r)]
    return sum(r[2] for r in sel), len(sel)


def ckey(tid, arm, level, k):
    if arm == "pin":
        return f"{tid}|{level}|pin"
    return f"{tid}|{level}|{'rep' if arm == 'repair' or k == 0 else 'ret'}{k}"


def extra(arm, level, k, field="extra"):
    vals = []
    for tid in TIDS:
        ck = ckey(tid, arm, level, k)
        if ck in META:
            vals.append(META[ck][field])
    return sum(vals) / len(vals) if vals else 0


def boot_ci(stat, seed=0):
    rng = random.Random(seed)
    vals = []
    for _ in range(BOOT):
        samp = [rng.choice(TIDS) for _ in TIDS]
        v = stat(samp)
        if v is not None:
            vals.append(v)
    vals.sort()
    if not vals:
        return (None, None)
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1])


def by_tid(rs):
    d = defaultdict(list)
    for r in rs:
        d[r[0]].append(r)
    return d


def rate_from(samp, groups, f=lambda r: True):
    k = n = 0
    for tid in samp:
        for r in groups.get(tid, []):
            if f(r):
                k += r[2]
                n += 1
    return k / n if n else None


res = {}
P = print

# ---------------------------------------------------------------- labels and compression
P("## Compression and label composition\n")
P("| level (words) | mean summary tokens | compression ratio | retrieval-type (present) | deletion-type |")
P("|---|---|---|---|---|")
res["labels"] = {}
for w in LEVELS:
    st = [toks(SUM[f"{t}|{w}"]) for t in TIDS]
    cr = sum(BODY_TOK[t] / toks(SUM[f"{t}|{w}"]) for t in TIDS) / len(TIDS)
    pres = [LAB[f"{t}|{w}|{rid}"]["present"] for t in TIDS for rid in POS[t] if f"{t}|{w}|{rid}" in LAB]
    k = sum(pres)
    P(f"| {w} | {sum(st)/len(st):.0f} | {cr:.1f}x | {fmt(k, len(pres))} | {len(pres)-k} |")
    res["labels"][w] = {"summary_tokens": sum(st) / len(st), "compression": cr, "present": k, "n": len(pres)}
P(f"\nMean compacted-body tokens: {sum(BODY_TOK.values())/len(TIDS):.0f}\n")

# ---------------------------------------------------------------- control
c = rows("control", 0, 0)
cb = rows("control", 0, 0, "benign")
P("## Zero-compaction control\n")
P(f"- trigger violation: {fmt(*count(c))}")
P(f"- benign false refusal: {fmt(*count(cb))}\n")
res["control"] = {"viol": count(c), "benign_refusal": count(cb)}
f_ = rows("floor", 0, 0)
fb = rows("floor", 0, 0, "benign")
P(f"- floor (rule turns removed, raw transcript): trigger violation {fmt(*count(f_))}; benign false refusal {fmt(*count(fb))}\n")
res["floor"] = {"viol": count(f_), "benign_refusal": count(fb)}

# ---------------------------------------------------------------- main grid
P("## Violation rate by level, arm, budget\n")
P("| level | arm | k | mean extra tokens | violation (all) | retrieval-type | deletion-type | benign false refusal |")
P("|---|---|---|---|---|---|---|---|")
res["grid"] = {}
for w in LEVELS:
    for arm, ks in (("repair", [0] + KS), ("retention", KS), ("pin", [0])):
        for k in ks:
            rs = rows(arm, w, k)
            bs = rows(arm, w, k, "benign")
            a, rr, dd = count(rs), count(rs, lambda r: r[3] == "retrieval"), count(rs, lambda r: r[3] == "deletion")
            b = count(bs)
            ex = extra(arm, w, k)
            P(f"| {w} | {arm} | {k} | {ex:.0f} | {fmt(*a)} | {fmt(*rr)} | {fmt(*dd)} | {fmt(*b)} |")
            res["grid"][f"{w}|{arm}|{k}"] = {"extra": ex, "all": a, "retrieval": rr, "deletion": dd, "benign": b}

# ---------------------------------------------------------------- pooled across levels
P("\n## Pooled over levels, by rule type\n")
P("| arm | k | retrieval-type violation | deletion-type violation | benign false refusal |")
P("|---|---|---|---|---|")
res["pooled"] = {}
for arm, ks in (("repair", [0] + KS), ("retention", KS), ("pin", [0])):
    for k in ks:
        rs = [r for w in LEVELS for r in rows(arm, w, k)]
        bs = [r for w in LEVELS for r in rows(arm, w, k, "benign")]
        rr, dd = count(rs, lambda r: r[3] == "retrieval"), count(rs, lambda r: r[3] == "deletion")
        P(f"| {arm} | {k} | {fmt(*rr)} | {fmt(*dd)} | {fmt(*count(bs))} |")
        res["pooled"][f"{arm}|{k}"] = {"retrieval": rr, "deletion": dd, "benign": count(bs)}

# ---------------------------------------------------------------- tests: repair 0 vs 8 by type, paired


def paired(arm_a, ka, arm_b, kb, f, kind="trigger"):
    A = {(r[0], r[1], w): r[2] for w in LEVELS for r in rows(arm_a, w, ka, kind) if f(r)}
    B = {(r[0], r[1], w): r[2] for w in LEVELS for r in rows(arm_b, w, kb, kind)}
    keys = [x for x in A if x in B]
    a1 = sum(A[x] for x in keys)
    b1 = sum(B[x] for x in keys)
    dis_b = sum(A[x] and not B[x] for x in keys)
    dis_c = sum((not A[x]) and B[x] for x in keys)
    return {"n": len(keys), "a": a1, "b": b1, "fisher_p": fisher_two_sided(a1, len(keys), b1, len(keys)),
            "mcnemar_p": mcnemar(dis_b, dis_c), "fixed": dis_b, "broken": dis_c}


P("\n## Paired tests (pooled over levels)\n")
P("| comparison | rule type | n | violations A | violations B | fixed | broken | Fisher p | McNemar p |")
P("|---|---|---|---|---|---|---|---|---|")
res["tests"] = {}
for name, (aa, ka, ab, kb) in {"repair0_vs_repair8": ("repair", 0, "repair", 8),
                                "repair0_vs_retention8": ("repair", 0, "retention", 8),
                                "repair8_vs_retention8": ("repair", 8, "retention", 8),
                                "repair0_vs_repair1": ("repair", 0, "repair", 1)}.items():
    for typ in ("retrieval", "deletion"):
        t = paired(aa, ka, ab, kb, lambda r, typ=typ: r[3] == typ)
        res["tests"][f"{name}|{typ}"] = t
        P(f"| {name} | {typ} | {t['n']} | {t['a']} | {t['b']} | {t['fixed']} | {t['broken']} | {t['fisher_p']:.3g} | {t['mcnemar_p']:.3g} |")
for name, (aa, ka, ab, kb) in {"benign repair0_vs_repair8": ("repair", 0, "repair", 8),
                                "benign repair0_vs_retention8": ("repair", 0, "retention", 8)}.items():
    t = paired(aa, ka, ab, kb, lambda r: True, "benign")
    res["tests"][name] = t
    P(f"| {name} | all | {t['n']} | {t['a']} | {t['b']} | {t['fixed']} | {t['broken']} | {t['fisher_p']:.3g} | {t['mcnemar_p']:.3g} |")

# ---------------------------------------------------------------- interaction: DiD with cluster bootstrap
P("\n## Interaction: repair effect on retrieval-type minus deletion-type (k=0 minus k=8 violation)\n")
g0 = by_tid([r + (w,) for w in LEVELS for r in rows("repair", w, 0)])
g8 = by_tid([r + (w,) for w in LEVELS for r in rows("repair", w, 8)])
gr8 = by_tid([r + (w,) for w in LEVELS for r in rows("retention", w, 8)])


def did(samp, g_after):
    vals = []
    for typ in ("retrieval", "deletion"):
        a = rate_from(samp, g0, lambda r: r[3] == typ)
        b = rate_from(samp, g_after, lambda r: r[3] == typ)
        if a is None or b is None:
            return None
        vals.append(a - b)
    return vals[0] - vals[1]


for nm, g in (("repair k=8", g8), ("retention k=8", gr8)):
    pt = did(TIDS, g)
    lo, hi = boot_ci(lambda s, g=g: did(s, g))
    P(f"- {nm}: drop(retrieval) minus drop(deletion) = {pt:+.3f}, 95% cluster-bootstrap CI [{lo:+.3f}, {hi:+.3f}]")
    res[f"did|{nm}"] = {"point": pt, "ci": [lo, hi]}
for nm, g in (("repair k=8", g8), ("retention k=8", gr8)):
    for typ in ("retrieval", "deletion"):
        f = lambda s, g=g, typ=typ: (None if rate_from(s, g0, lambda r: r[3] == typ) is None or rate_from(s, g, lambda r: r[3] == typ) is None
                                     else rate_from(s, g0, lambda r: r[3] == typ) - rate_from(s, g, lambda r: r[3] == typ))
        pt = f(TIDS)
        lo, hi = boot_ci(f)
        P(f"- {nm}, {typ}-type: violation drop = {pt:+.3f} [{lo:+.3f}, {hi:+.3f}]")
        res[f"drop|{nm}|{typ}"] = {"point": pt, "ci": [lo, hi]}

# ---------------------------------------------------------------- retention split by tail coverage
P("\n## Retention arm: rules inside vs outside the widened tail\n")
P("| level | k | inside tail: violation | outside tail: violation |")
P("|---|---|---|---|")
for w in LEVELS:
    for k in KS:
        rs = rows("retention", w, k)
        P(f"| {w} | {k} | {fmt(*count(rs, lambda r: r[4]))} | {fmt(*count(rs, lambda r: not r[4]))} |")
allr = [r for w in LEVELS for k in KS for r in rows("retention", w, k)]
P(f"\nPooled: inside {fmt(*count(allr, lambda r: r[4]))}; outside {fmt(*count(allr, lambda r: not r[4]))}; "
  f"outside and deletion-type {fmt(*count(allr, lambda r: not r[4] and r[3] == 'deletion'))}; "
  f"inside and deletion-type {fmt(*count(allr, lambda r: r[4] and r[3] == 'deletion'))}")

# ---------------------------------------------------------------- efficiency and crossover
P("\n## Efficiency: violation-rate reduction (percentage points) per 1k extra tokens, vs. k=0 at same level\n")
P("| level | compression | arm | k | extra tokens | reduction (pp) [95% CI] | pp per 1k tokens |")
P("|---|---|---|---|---|---|---|")
res["eff"] = {}
for w in LEVELS:
    g0w = by_tid(rows("repair", w, 0))
    for k in KS:
        for arm in ("repair", "retention"):
            gk = by_tid(rows(arm, w, k))
            f = lambda s, gk=gk, g0w=g0w: (rate_from(s, g0w) - rate_from(s, gk)) if rate_from(s, g0w) is not None and rate_from(s, gk) is not None else None
            pt = f(TIDS)
            lo, hi = boot_ci(f)
            ex = extra(arm, w, k)
            if pt is None or lo is None:
                continue
            res["eff"][f"{w}|{arm}|{k}"] = {"red": pt, "ci": [lo, hi], "extra": ex, "per1k": 1000 * pt / ex if ex else None}
            P(f"| {w} | {res['labels'][w]['compression']:.0f}x | {arm} | {k} | {ex:.0f} | {100*pt:+.1f} [{100*lo:+.1f}, {100*hi:+.1f}] | {100000*pt/ex:+.2f} |")

P("\n## Repair minus retention at matched budget (violation difference, positive = retention better)\n")
P("| level | k | retention violation minus repair violation... shown as repair minus retention (pp) [95% CI] |")
P("|---|---|---|")
res["diff"] = {}
for w in LEVELS:
    for k in KS:
        gr = by_tid(rows("repair", w, k))
        gt = by_tid(rows("retention", w, k))
        f = lambda s, gr=gr, gt=gt: (rate_from(s, gr) - rate_from(s, gt)) if rate_from(s, gr) is not None and rate_from(s, gt) is not None else None
        pt = f(TIDS)
        lo, hi = boot_ci(f)
        if pt is None or lo is None:
            continue
        res["diff"][f"{w}|{k}"] = {"point": pt, "ci": [lo, hi]}
        P(f"| {w} | {k} | {100*pt:+.1f} [{100*lo:+.1f}, {100*hi:+.1f}] |")

# ---------------------------------------------------------------- router (split-half cross-validated)
P("\n## Router: choose arm per compression level from half the transcripts, evaluate on the other half\n")
res["router"] = {}
for k in KS:
    tot = {"repair": [0, 0], "retention": [0, 0], "router": [0, 0], "oracle_level": [0, 0]}
    choices = []
    for fold in (0, 1):
        train = [t for t in TIDS if t % 2 == fold]
        test = [t for t in TIDS if t % 2 != fold]
        for w in LEVELS:
            gr, gt = by_tid(rows("repair", w, k)), by_tid(rows("retention", w, k))
            pick = "repair" if rate_from(train, gr) < rate_from(train, gt) else "retention"
            choices.append((fold, w, pick))
            for arm, g in (("repair", gr), ("retention", gt), ("router", gr if pick == "repair" else gt)):
                kk, nn = count([r for t in test for r in g.get(t, [])])
                tot[arm][0] += kk
                tot[arm][1] += nn
    res["router"][k] = {"totals": tot, "choices": choices}
    P(f"- k={k}: repair-only {fmt(*tot['repair'])}; retention-only {fmt(*tot['retention'])}; router {fmt(*tot['router'])}; "
      f"choices {[(w, p) for f_, w, p in choices]}")

# ---------------------------------------------------------------- confabulation audit
if AUD:
    P("\n## Repair-list audit (8 passes): does the list state each true rule? invented constraints?\n")
    P("| level | retrieval-type mentioned | deletion-type mentioned (recovered) | mean invented constraints per list |")
    P("|---|---|---|---|")
    res["audit"] = {}
    for w in LEVELS:
        rm = [0, 0]
        dm = [0, 0]
        inv = []
        for t in TIDS:
            a = AUD.get(f"{t}|{w}")
            if not a:
                continue
            inv.append(int(a.get("n_invented", 0) or 0))
            for rid in POS[t]:
                m = bool(a.get("mentioned", {}).get(rid, False))
                if f"{t}|{w}|{rid}" not in LAB:
                    continue
                tgt = rm if LAB[f"{t}|{w}|{rid}"]["present"] else dm
                tgt[0] += m
                tgt[1] += 1
        P(f"| {w} | {fmt(*rm)} | {fmt(*dm)} | {sum(inv)/len(inv):.1f} |")
        res["audit"][w] = {"ret_mentioned": rm, "del_mentioned": dm, "invented_mean": sum(inv) / len(inv)}
    # deletion-type rules that repair k=8 refused but k=0 complied: what did the agent say?
    ex = []
    for w in LEVELS:
        r0 = {(r[0], r[1]): r for r in rows("repair", w, 0)}
        for r in rows("repair", w, 8):
            if r[3] == "deletion" and not r[2] and r0.get((r[0], r[1])) and r0[(r[0], r[1])][2]:
                a = AUD.get(f"{r[0]}|{w}", {})
                ex.append({"tid": r[0], "level": w, "rid": r[1],
                           "repair_list_mentions_rule": bool(a.get("mentioned", {}).get(r[1], False)),
                           "action": DEC[f"{r[0]}|{w}|rep8|{r[1]}|trigger"]["raw"][-300:]})
    res["deletion_fixed_by_repair"] = ex
    P(f"\nDeletion-type rules fixed by 8 repair passes (paired, k=0 violated, k=8 refused): {len(ex)}; "
      f"of these the repair list stated the rule in {sum(e['repair_list_mentions_rule'] for e in ex)}")


# ---------------------------------------------------------------- Holm correction over the paired-test family
P("\n## Holm-corrected paired tests (family = all McNemar tests above)\n")
fam = sorted(((v["mcnemar_p"], k) for k, v in res["tests"].items()), key=lambda x: x[0])
m = len(fam)
adj, running = {}, 0.0
for i, (pv, k) in enumerate(fam):
    running = max(running, min(1.0, (m - i) * pv))
    adj[k] = running
P("| comparison | raw McNemar p | Holm-adjusted p |")
P("|---|---|---|")
for k, v in res["tests"].items():
    v["holm_p"] = adj[k]
    P(f"| {k} | {v['mcnemar_p']:.3g} | {adj[k]:.3g} |")

# ---------------------------------------------------------------- token matching check and cost
AGENT_SYS_TOK = 60
REPAIR_PROMPT_TOK = 90
P("\n## Token matching and cost\n")
P("Budget = tokens the first k repair passes appended to the context (chars/4). Retention widens the tail by "
  "whole turns up to that budget.\n")
P("| level | k | repair appended tokens | retention appended tokens | retention/repair | repair-pass compute (in+out, one-time) | decision prompt tokens repair | decision prompt tokens retention |")
P("|---|---|---|---|---|---|---|---|")
res["cost"] = {}
for w in LEVELS:
    for k in KS:
        ra = extra("repair", w, k)
        ta = extra("retention", w, k)
        comp = []
        for t in TIDS:
            base = META[f"{t}|{w}|rep0"]["ctx_tokens"] + AGENT_SYS_TOK
            passes = REP[f"{t}|{w}"][:k]
            tot = 0
            for i in range(k):
                prior = sum(toks(x) + 8 for x in passes[:i])
                tot += base + prior + REPAIR_PROMPT_TOK + toks(passes[i])
            comp.append(tot)
        rc = sum(comp) / len(comp)
        dr = extra("repair", w, k, "ctx_tokens")
        dt = extra("retention", w, k, "ctx_tokens")
        res["cost"][f"{w}|{k}"] = {"repair_appended": ra, "retention_appended": ta, "repair_compute": rc,
                                   "dec_ctx_repair": dr, "dec_ctx_retention": dt}
        P(f"| {w} | {k} | {ra:.0f} | {ta:.0f} | {ta/ra:.2f} | {rc:.0f} | {dr:.0f} | {dt:.0f} |")
for w in LEVELS:
    P(f"- level {w}: pin arm adds {extra('pin', w, 0):.0f} tokens (decision prompt {extra('pin', w, 0, 'ctx_tokens'):.0f}); "
      f"k=0 decision prompt {extra('repair', w, 0, 'ctx_tokens'):.0f}")
ctrl_ctx = sum(META[f"{t}|ctrl"]["ctx_tokens"] for t in TIDS) / len(TIDS)
P(f"- zero-compaction control decision prompt: {ctrl_ctx:.0f} tokens")
res["cost"]["control_ctx"] = ctrl_ctx

# ---------------------------------------------------------------- judge validation
hp = HERE / "handlabels.json"
if hp.exists() and ARGS.raw == "raw":
    H = json.loads(hp.read_text())
    P("\n## Judge validation against hand labels\n")
    for nm, src in (("judge 1 (primary)", LAB1), ("judge 2 (trigger-framed)", LAB2)):
        if not src:
            continue
        a = [(h["human_present"], src[h["key"]]["present"]) for h in H]
        n = len(a)
        ag = sum(x == y for x, y in a) / n
        p1 = sum(x for x, _ in a) / n
        p2 = sum(y for _, y in a) / n
        pe = p1 * p2 + (1 - p1) * (1 - p2)
        kap = (ag - pe) / (1 - pe)
        fn = sum(x and not y for x, y in a)
        fp = sum(y and not x for x, y in a)
        P(f"- {nm}: n={n}, agreement {100*ag:.0f}%, Cohen's kappa {kap:.2f}; judge NO where human YES: {fn}; judge YES where human NO: {fp}")
        res[f"judge_validation|{nm}"] = {"n": n, "agree": ag, "kappa": kap, "fn": fn, "fp": fp}
    if LAB2:
        both = [k for k in LAB1 if k in LAB2]
        ag = sum(LAB1[k]["present"] == LAB2[k]["present"] for k in both)
        P(f"- judge 1 vs judge 2 on all {len(both)} labels: agreement {fmt(ag, len(both))}")

out_name = "results.json" if (ARGS.raw == "raw" and ARGS.labels == "judge1") else f"results_{ARGS.raw}_{ARGS.labels}.json"
(HERE / out_name).write_text(json.dumps(res, indent=1, default=str))
