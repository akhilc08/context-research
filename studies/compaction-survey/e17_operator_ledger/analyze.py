"""Regenerate every E17 table from raw outputs (no model calls).

Usage: python3 analyze.py [--model MODEL]   -> prints Markdown and writes results/<model>/tables.md
"""
import argparse, json, math, re, statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE.parent / "shared"))
from common import wilson  # noqa: E402

DEFAULT_MODEL = "stealth/space-bunny-alpha"
ARMS = ["floor", "full", "plain", "structured", "structured_full", "pin_raw",
        "ledger", "ledger_norev", "ledger_noframe", "ledger_oracle", "pin_rules"]
PTYPES = ["active", "revoked", "amended", "rule_state", "goal", "plan", "fact_current", "fact_history", "overall"]
RULE_TYPES = ("active", "revoked", "amended")

# Pre-specified comparisons (fixed before the main run), Holm-corrected together.
PLANNED = [
    ("ledger", "plain", "rule_state"),
    ("ledger", "structured", "rule_state"),
    ("ledger", "pin_raw", "revoked"),
    ("ledger", "pin_raw", "active"),
    ("ledger", "pin_raw", "amended"),
    ("ledger", "structured", "revoked"),
    ("ledger", "ledger_norev", "revoked"),
    ("ledger", "ledger_noframe", "active"),
    ("ledger", "ledger_noframe", "rule_state"),
    ("ledger", "structured_full", "rule_state"),
    ("ledger", "full", "rule_state"),
    ("ledger", "ledger_oracle", "rule_state"),
    ("ledger", "plain", "goal"),
    ("ledger", "plain", "plan"),
    ("ledger", "plain", "fact_history"),
]


def slug(model):
    return "space_bunny" if model == DEFAULT_MODEL else re.sub(r"[^A-Za-z0-9]+", "_", model)


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, p)


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
    lo, hi = max(0.0, lo), min(1.0, hi)
    return f"{100 * k / n:.0f}% [{100 * lo:.0f} to {100 * hi:.0f}]"


def fmtp(p):
    return f"{p:.2g}" if p >= 0.001 else f"{p:.0e}"


def toks(s):
    return set(re.sub(r"[^a-z0-9]+", " ", str(s).lower()).split())


def overlap(a, b):
    A = toks(a)
    return len(A & toks(b)) / max(1, len(A))


def audit(sess, out):
    """Compare the final model-maintained ledger with ground truth. Returns a dict of error flags."""
    t, led = sess["truth"], out["ledger"]
    act = [r.get("text", "") if isinstance(r, dict) else str(r) for r in led.get("active_rules") or []]
    chg = [r if isinstance(r, dict) else {"rule": str(r)} for r in led.get("changed_rules") or []]
    e = defaultdict(list)
    for r in t["active"]:
        e["active_missing"].append(not any(overlap(r["rule"], a) >= 0.6 for a in act))
    for r in t["revoked"]:
        e["revoked_still_active"].append(any(overlap(r["rule"], a) >= 0.6 for a in act))
        e["revoked_not_logged"].append(not any(overlap(r["rule"], c.get("rule", "")) >= 0.6 and
                                               str(c.get("change", "")).lower().startswith("rev") for c in chg))
    for a in t["amended"]:
        nums_new = set(re.findall(r"\d[\d,.]*", a["amendment"])) - set(re.findall(r"\d[\d,.]*", a["rule"]))
        match = [x for x in act if overlap(a["rule"], x) >= 0.4]
        e["amended_missing"].append(not match)
        e["amended_not_updated"].append(bool(match) and not any(any(n.strip(".,") in x for n in nums_new)
                                                                for x in match))
    goals = t["goals"]
    ob = led.get("objective") or {}
    obt = ob.get("text", "") if isinstance(ob, dict) else str(ob)
    sc = [overlap(g["message"], obt) for g in goals]
    e["objective_wrong"].append(not obt or max(range(len(sc)), key=lambda i: sc[i]) != len(goals) - 1)
    reqs = " ".join((r.get("text", "") if isinstance(r, dict) else str(r)) for r in led.get("requests") or [])
    e["plan_missing"].append(t["plan"]["name"].lower() not in reqs.lower())
    facts = [f for f in led.get("facts") or [] if isinstance(f, dict)]
    for f in t["facts"]:
        vals = f["values"]
        cur_holders = [x for x in facts if str(x.get("current", "")).strip() in vals]
        good = [x for x in cur_holders if str(x.get("current", "")).strip() == vals[-1]]
        e["fact_current_wrong"].append(not good)
        e["fact_orphan"].append(len(cur_holders) > 1)
        hist_ok = False
        for x in good:
            prev = " ".join(str(p.get("value", p) if isinstance(p, dict) else p) for p in x.get("previous") or [])
            hist_ok = all(v in prev for v in vals[:-1])
        e["fact_history_missing"].append(not hist_ok)
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    out_dir = HERE / "results" / slug(a.model)
    rows = [json.loads(l) for l in (out_dir / "graded.jsonl").read_text().splitlines() if l.strip()]
    sessions = {s["sid"]: s for s in json.loads((HERE / "data" / "sessions.json").read_text())}
    outs = {json.loads(f.read_text())["sid"]: json.loads(f.read_text()) for f in sorted((out_dir / "sessions").glob("S*.json"))}
    md = []
    P = md.append
    P(f"# E17 tables ({a.model}), {len(outs)} sessions\n")

    # outcome lookup: (arm, unit) -> correct, unit = (sid, ptype, idx)
    res = {}
    for r in rows:
        res[(r["arm"], (r["sid"], r["ptype"], r["idx"]))] = bool(r["correct"])

    def units(arm, ptype):
        if ptype == "overall":
            return {u: v for (ar, u), v in res.items() if ar == arm}
        if ptype == "rule_state":
            return {u: v for (ar, u), v in res.items() if ar == arm and u[1] in RULE_TYPES}
        return {u: v for (ar, u), v in res.items() if ar == arm and u[1] == ptype}

    P("## Correct rate by probe type and arm (Wilson 95% CI)\n")
    P("| arm | " + " | ".join(PTYPES) + " |")
    P("|---|" + "---|" * len(PTYPES))
    for arm in ARMS:
        cells = []
        for pt in PTYPES:
            u = units(arm, pt)
            cells.append(pct(sum(u.values()), len(u)))
        P(f"| {arm} | " + " | ".join(cells) + " |")

    P("\n## Amended rules by direction\n")
    P("| arm | loosen (expect COMPLY) | tighten (expect REFUSE) |")
    P("|---|---|---|")
    for arm in ARMS:
        c = []
        for d in ("loosen", "tighten"):
            sub = [r for r in rows if r["arm"] == arm and r["ptype"] == "amended" and r.get("direction") == d]
            c.append(pct(sum(r["correct"] for r in sub), len(sub)))
        P(f"| {arm} | {c[0]} | {c[1]} |")

    P("\n## Rule probes scored by the DECISION line only (secondary; the convention of E1 to E15)\n")
    P("| arm | active | revoked | amended | rule_state |")
    P("|---|---|---|---|---|")
    for arm in ARMS:
        c = []
        for pts in (("active",), ("revoked",), ("amended",), RULE_TYPES):
            sub = [r for r in rows if r["arm"] == arm and r["ptype"] in pts]
            c.append(pct(sum(r["correct_decision"] for r in sub), len(sub)))
        P(f"| {arm} | " + " | ".join(c) + " |")
    P("\nAgreement of judged action and DECISION line on rule probes: " + ", ".join(
        f"{pt} {100 * sum(r['correct'] == r['correct_decision'] for r in rows if r['ptype'] == pt) / max(1, sum(1 for r in rows if r['ptype'] == pt)):.0f}%"
        for pt in RULE_TYPES))

    P("\n## Judge labels per probe type (counts)\n")
    for pt in ("active", "revoked", "amended", "goal", "plan", "fact_current", "fact_history"):
        labs = sorted({r["label"] for r in rows if r["ptype"] == pt})
        P(f"\n{pt}\n")
        P("| arm | " + " | ".join(labs) + " |")
        P("|---|" + "---|" * len(labs))
        for arm in ARMS:
            sub = [r["label"] for r in rows if r["arm"] == arm and r["ptype"] == pt]
            P(f"| {arm} | " + " | ".join(str(sub.count(l)) for l in labs) + " |")

    P("\n## Pre-specified paired comparisons (exact McNemar, Holm over all 15)\n")
    P("| A | B | probes | A correct | B correct | A-only / B-only | p | Holm p |")
    P("|---|---|---|---|---|---|---|---|")
    raw = []
    for A, B, pt in PLANNED:
        ua, ub = units(A, pt), units(B, pt)
        common = sorted(set(ua) & set(ub))
        b = sum(ua[u] and not ub[u] for u in common)
        c = sum(ub[u] and not ua[u] for u in common)
        raw.append((A, B, pt, len(common), sum(ua[u] for u in common), sum(ub[u] for u in common), b, c,
                    mcnemar(b, c)))
    adj = holm([x[-1] for x in raw])
    for x, h in zip(raw, adj):
        A, B, pt, n, ka, kb, b, c, p = x
        P(f"| {A} | {B} | {pt} (n = {n}) | {100 * ka / n:.0f}% | {100 * kb / n:.0f}% | {b} / {c} | {fmtp(p)} | {fmtp(h)} |")

    P("\n## Exploratory paired comparisons (not corrected)\n")
    P("| A | B | probes | A | B | A-only / B-only | p |")
    P("|---|---|---|---|---|---|---|")
    for A, B, pt in [("structured_full", "structured", "revoked"), ("structured_full", "plain", "rule_state"),
                     ("pin_raw", "plain", "rule_state"), ("pin_raw", "full", "revoked"),
                     ("structured", "plain", "revoked"), ("ledger_noframe", "ledger_norev", "rule_state"),
                     ("ledger", "pin_raw", "overall"), ("ledger", "structured_full", "overall"),
                     ("ledger", "full", "overall"), ("ledger_oracle", "pin_raw", "rule_state"),
                     ("ledger", "pin_rules", "revoked"), ("ledger", "pin_rules", "rule_state"),
                     ("pin_raw", "pin_rules", "revoked"), ("pin_rules", "plain", "active")]:
        ua, ub = units(A, pt), units(B, pt)
        common = sorted(set(ua) & set(ub))
        b = sum(ua[u] and not ub[u] for u in common)
        c = sum(ub[u] and not ua[u] for u in common)
        n = len(common)
        if n:
            P(f"| {A} | {B} | {pt} (n = {n}) | {100 * sum(ua[u] for u in common) / n:.0f}% | "
              f"{100 * sum(ub[u] for u in common) / n:.0f}% | {b} / {c} | {fmtp(mcnemar(b, c))} |")

    # ---------------- cost
    P("\n## Context size and cost\n")
    P("| arm | mean context tokens (est.) | extra block tokens | extra model calls per session |")
    P("|---|---|---|---|")
    nops = statistics.mean(o["n_operator"] for o in outs.values())
    rounds = {k: statistics.mean(o["summary_rounds"][k] for o in outs.values()) for k in ("plain", "structured", "structured_full")}
    for arm in ARMS:
        ct = statistics.mean(o["context_tokens"][arm] for o in outs.values())
        bt = statistics.mean(o["block_tokens"][arm] for o in outs.values()) if arm in next(iter(outs.values()))["block_tokens"] else 0
        calls = {"floor": "0", "full": "0", "pin_raw": f"{rounds['plain']:.1f} (plain compaction)",
                 "pin_rules": f"{rounds['plain']:.1f} (plain compaction)",
                 "plain": f"{rounds['plain']:.1f}", "structured": f"{rounds['structured']:.1f}",
                 "structured_full": f"{rounds['structured_full']:.1f}",
                 "ledger_oracle": f"{rounds['plain']:.1f} (oracle needs labels)"}.get(
            arm, f"{rounds['plain']:.1f} + {nops:.1f} ledger updates")
        P(f"| {arm} | {ct:.0f} | {bt:.0f} | {calls} |")
    sw = {k: statistics.mean(len(o["summaries"][k].split()) for o in outs.values()) for k in rounds}
    P("\nMean final summary words (budget 250): " + ", ".join(f"{k} {v:.0f}" for k, v in sw.items()))
    P(f"\nMean operator turns per session: {nops:.1f}; mean session length "
      f"{statistics.mean(o['n_turns'] for o in outs.values()):.0f} turns.")

    # ---------------- ledger growth
    P("\n## Ledger growth (rendered ledger tokens after the k-th operator turn, mean over sessions)\n")
    P("| operator turn k | ledger tokens | pin_raw tokens so far |")
    P("|---|---|---|")
    for k in (1, 5, 10, 15, 20, 24):
        lt, pt_ = [], []
        for sid, o in outs.items():
            h = o["ledger_history"]
            if len(h) >= k:
                lt.append(h[k - 1]["tokens"])
                ops = sessions[sid]["operator_turns"][:k]
                pt_.append(round(sum(len(x["text"].split()) for x in ops) * 1.33) + 10)
        if lt:
            P(f"| {k} | {statistics.mean(lt):.0f} | {statistics.mean(pt_):.0f} |")
    fl = [o["block_tokens"]["ledger"] for o in outs.values()]
    fo = [o["block_tokens"]["ledger_oracle"] for o in outs.values()]
    fp = [o["block_tokens"]["pin_raw"] for o in outs.values()]
    P(f"\nFinal ledger {statistics.mean(fl):.0f} tokens (range {min(fl)} to {max(fl)}), oracle ledger "
      f"{statistics.mean(fo):.0f}, pin_raw {statistics.mean(fp):.0f}.")

    # ---------------- ledger maintenance audit
    P("\n## Ledger maintenance errors (final ledger vs ground truth, automatic audit)\n")
    agg = defaultdict(list)
    for sid, o in outs.items():
        for k, v in audit(sessions[sid], o).items():
            agg[k] += v
    P("| check | errors |")
    P("|---|---|")
    for k, v in agg.items():
        P(f"| {k} | {sum(v)}/{len(v)} |")
    fails = sum(o["ledger_failed_updates"] for o in outs.values())
    total = sum(o["n_operator"] for o in outs.values())
    P(f"\nFailed ledger update calls (no valid JSON, old ledger kept): {fails}/{total}.")

    # rule probes conditioned on ledger state (exploratory)
    P("\n## Ledger arm outcome by ledger correctness for that rule (exploratory)\n")
    cond = defaultdict(lambda: [0, 0])
    for sid, o in outs.items():
        e = audit(sessions[sid], o)
        for i in range(3):
            ok_r = not e["revoked_still_active"][i]
            r = res.get(("ledger", (sid, "revoked", i)))
            if r is not None:
                cond[("revoked", ok_r)][0] += r; cond[("revoked", ok_r)][1] += 1
            ok_a = not e["active_missing"][i]
            r = res.get(("ledger", (sid, "active", i)))
            if r is not None:
                cond[("active", ok_a)][0] += r; cond[("active", ok_a)][1] += 1
        for i in range(2):
            ok_m = not (e["amended_missing"][i] or e["amended_not_updated"][i])
            r = res.get(("ledger", (sid, "amended", i)))
            if r is not None:
                cond[("amended", ok_m)][0] += r; cond[("amended", ok_m)][1] += 1
    P("| probe | ledger entry correct | ledger entry wrong |")
    P("|---|---|---|")
    for pt in RULE_TYPES:
        P(f"| {pt} | {pct(*cond[(pt, True)])} | {pct(*cond[(pt, False)])} |")

    # ---------------- judge validation
    hl = HERE / "hand_labels.json"
    if hl.exists():
        P("\n## Judge validation against blind hand labels\n")
        labels = json.loads(hl.read_text())
        P("| judge | n | agreement | Cohen's kappa |")
        P("|---|---|---|---|")
        for kind in sorted({x["kind"] for x in labels}):
            sub = [x for x in labels if x["kind"] == kind and x.get("hand") is not None]
            if not sub:
                continue
            j = [x["judge"] for x in sub]
            h = [x["hand"] for x in sub]
            n = len(sub)
            po = sum(x == y for x, y in zip(j, h)) / n
            cats = set(j) | set(h)
            pe = sum((j.count(c) / n) * (h.count(c) / n) for c in cats)
            kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
            P(f"| {kind} | {n} | {100 * po:.0f}% | {kappa:.2f} |")

    text = "\n".join(md)
    (out_dir / "tables.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
