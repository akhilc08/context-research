"""Regenerate every E3 table from the raw result files.

Usage: /private/tmp/taubench-venv/bin/python analyze.py results/main.jsonl [more.jsonl ...]
(plain python3 also works; this script uses only the standard library)
"""
import collections, itertools, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
USAGE = HERE.parent / "usage.jsonl"
ORDER = ["nopolicy", "standard", "hist", "compact", "pin", "pinrules", "watch", "watch_ctx"]
WRITE_TOOLS = {"cancel_pending_order", "modify_pending_order_items", "modify_pending_order_address",
               "modify_pending_order_payment", "modify_user_address", "exchange_delivered_order_items",
               "return_delivered_order_items",
               # airline
               "book_reservation", "cancel_reservation", "update_reservation_flights",
               "update_reservation_baggages", "update_reservation_passengers", "send_certificate"}
AUTH_TOOLS = {"find_user_id_by_email", "find_user_id_by_name_zip"}
YES = ("yes", "yeah", "yep", "confirm", "go ahead", "proceed", "please do", "sure", "correct", "that's right",
       "sounds good", "do it", "okay", "ok")
# Planned comparisons (decided before the main run). Each is (a, b): test a vs b.
PLANNED = [("compact", "hist"), ("hist", "standard"), ("pin", "compact"), ("pinrules", "compact"),
           ("watch", "compact"), ("watch", "pin"), ("watch", "pinrules"), ("watch_ctx", "compact"), ("watch", "watch_ctx"), ("nopolicy", "standard")]


def load(paths):
    rows = []
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def binom_two_sided(k, n):
    if n == 0:
        return 1.0
    pk = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    obs = pk[k]
    return min(1.0, sum(p for p in pk if p <= obs + 1e-12))


def boot_ci(diffs, reps=2000, seed=0):
    import random
    rng = random.Random(seed)
    n = len(diffs)
    if n == 0:
        return float("nan"), float("nan")
    ms = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return ms[int(0.025 * reps)], ms[int(0.975 * reps) - 1]


def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(idx):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def pass_hat_k(per_task, k):
    vals = []
    for rs in per_task.values():
        n, c = len(rs), sum(1 for r in rs if r >= 1.0)
        if n >= k:
            vals.append(math.comb(c, k) / math.comb(n, k))
    return sum(vals) / len(vals) if vals else float("nan"), len(vals)


# The first stripped-tools runs were tagged like ordinary retail runs. They all started after this
# time (birth time of results/stripped.log), and no ordinary retail trial-0 call happened after it,
# so retail trial-0 usage records at or after this time belong to the stripped variant.
STRIP_START = 1790929272


def usage_by_run():
    agg = collections.defaultdict(lambda: [0, 0, 0])
    if not USAGE.exists():
        return agg
    for line in USAGE.read_text().splitlines():
        try:
            u = json.loads(line)
        except Exception:
            continue
        tag = u.get("tag") or ""
        if not tag.startswith("e3:"):
            continue
        parts = tag.split(":")
        if len(parts) < 6:
            continue
        key = list(parts[1:5])  # domain, arm, task, trial
        if key[0] == "retail" and key[3] == "0" and (u.get("t") or 0) >= STRIP_START:
            key[0] = "retail-strip"
        key = tuple(key)
        a = agg[key]
        a[0] += 1
        a[1] += u.get("in") or 0
        a[2] += u.get("out") or 0
    return agg


def dkey(r):
    return r["domain"] + ("-strip" if (r.get("cfg") or {}).get("strip_tools") else "")


def violations(r):
    """Heuristic policy-violation flags from the compact trajectory (keyword-free w.r.t. grading)."""
    authed, last_user, flags = False, "", collections.Counter()
    item_calls = collections.Counter()
    for e in r["events"]:
        if e[0] == "user":
            last_user = e[1].lower()
        elif e[0] == "tool":
            name, kw, obs = e[1], e[2], e[3]
            if name in AUTH_TOOLS and not obs.startswith("Error"):
                authed = True
            if name in WRITE_TOOLS:
                if not authed:
                    flags["write_before_auth"] += 1
                if not any(y in last_user for y in YES):
                    flags["write_without_user_yes"] += 1
                if name in ("exchange_delivered_order_items", "modify_pending_order_items") \
                        and not obs.startswith("Error"):
                    item_calls[kw.get("order_id")] += 1
            if name == "transfer_to_human_agents":
                flags["transfer_to_human"] += 1
    flags["repeat_item_call_same_order"] = sum(1 for v in item_calls.values() if v > 1)
    return {k: v for k, v in flags.items() if v}


def first_write_step(r):
    step = 0
    for e in r["events"]:
        if e[0] in ("tool", "agent", "badargs"):
            step += 1
        if e[0] == "tool" and e[1] in WRITE_TOOLS:
            return step
    return None


def main(paths):
    rows = load(paths)
    n_err = sum(1 for r in rows if r.get("errors"))
    rows = [r for r in rows if not r.get("errors")]  # provider outages: treated as missing, rerun
    use = usage_by_run()
    by_arm = collections.defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)
    arms = [a for a in ORDER if a in by_arm] + sorted(set(by_arm) - set(ORDER))
    domain = rows[0]["domain"]
    print(f"# E3 results ({domain}), files: {', '.join(paths)}\n")
    print(f"Runs dropped because the model provider failed mid-run: {n_err}\n")

    # per arm summary
    print("| arm | runs | tasks | mean reward | 95% CI (Wilson, runs) | pass^1 | pass^2 | errors | max-steps | "
          "agent calls/run | all calls/run | input tok/run | output tok/run | compactions/run |")
    print("|" + "---|" * 14)
    per_task = {}
    for a in arms:
        rs = by_arm[a]
        n = len(rs)
        k = sum(1 for r in rs if r["reward"] >= 1.0)
        lo, hi = wilson(k, n)
        pt = collections.defaultdict(list)
        for r in rs:
            pt[r["task"]].append(r["reward"])
        per_task[a] = pt
        p1, _ = pass_hat_k(pt, 1)
        p2, n2 = pass_hat_k(pt, 2)
        err = sum(1 for r in rs if r.get("errors"))
        maxs = sum(1 for r in rs if not r["done"] and not r.get("errors"))
        ac = sum(r["calls"].get("agent", 0) for r in rs) / n
        allc = [use.get((dkey(r), a, str(r["task"]), str(r["trial"])), [0, 0, 0]) for r in rs]
        calls = sum(sum(r["calls"].values()) for r in rs) / n
        tin = sum(x[1] for x in allc) / n
        tout = sum(x[2] for x in allc) / n
        nc = sum(r["n_compactions"] for r in rs) / n
        p2s = f"{p2:.3f} (n={n2})" if n2 else "n/a"
        print(f"| {a} | {n} | {len(pt)} | {k/n:.3f} ({k}/{n}) | {lo:.3f} to {hi:.3f} | {p1:.3f} | {p2s} | {err} | "
              f"{maxs} | {ac:.1f} | {calls:.1f} | {tin:,.0f} | {tout:,.0f} | {nc:.2f} |")

    # paired comparisons over shared tasks (mean reward over shared trials per task)
    print("\n## Paired comparisons (exact sign test on per-task mean reward over shared trials; Holm across planned family)\n")
    print("| comparison | shared tasks | a better | b better | ties | mean a | mean b | diff (95% paired bootstrap CI) | raw p | Holm p |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    comps = [(a, b) for a, b in PLANNED if a in per_task and b in per_task]
    res = []
    for a, b in comps:
        ra = {(r["task"], r["trial"]): r["reward"] for r in by_arm[a]}
        rb = {(r["task"], r["trial"]): r["reward"] for r in by_arm[b]}
        shared = sorted(set(ra) & set(rb))
        tasks = sorted({t for t, _ in shared})
        ma, mb = {}, {}
        for t in tasks:
            ks = [k for k in shared if k[0] == t]
            ma[t] = sum(ra[k] for k in ks) / len(ks)
            mb[t] = sum(rb[k] for k in ks) / len(ks)
        win = sum(1 for t in tasks if ma[t] > mb[t])
        loss = sum(1 for t in tasks if ma[t] < mb[t])
        p = binom_two_sided(win, win + loss)
        ci = boot_ci([ma[t] - mb[t] for t in tasks])
        res.append((a, b, len(tasks), win, loss, len(tasks) - win - loss,
                    sum(ma.values()) / max(1, len(tasks)), sum(mb.values()) / max(1, len(tasks)), ci, p))
    adj = holm([x[-1] for x in res])
    for x, pa in zip(res, adj):
        a, b, n, w, l, t, xa, xb, ci, p = x
        print(f"| {a} vs {b} | {n} | {w} | {l} | {t} | {xa:.3f} | {xb:.3f} | {xa-xb:+.3f} ({ci[0]:+.3f} to {ci[1]:+.3f}) "
              f"| {p:.3g} | {pa:.3g} |")

    # exposure: was the policy compacted away before the first database write?
    print("\n## Exposure: compaction before the first database write (compaction arms)\n")
    print("| arm | runs with a write | compaction before first write | reward when exposed | reward when not exposed |")
    print("|---|---|---|---|---|")
    for a in arms:
        rs = [r for r in by_arm[a] if r["n_compactions"] or a in ("compact", "pin", "pinrules", "watch")]
        if a not in ("compact", "pin", "pinrules", "watch", "watch_ctx"):
            continue
        ex, nex = [], []
        for r in rs:
            fw = first_write_step(r)
            if fw is None:
                continue
            comp_steps = [c["agent_step"] for c in r["compactions"]]
            (ex if comp_steps and min(comp_steps) < fw else nex).append(r["reward"])
        f = lambda xs: f"{sum(xs)/len(xs):.3f} (n={len(xs)})" if xs else "n/a"
        print(f"| {a} | {len(ex)+len(nex)} | {len(ex)} | {f(ex)} | {f(nex)} |")

    # violation heuristics
    print("\n## Heuristic policy-violation flags (share of runs with at least one)\n")
    cats = (["write_before_auth", "write_without_user_yes", "repeat_item_call_same_order", "transfer_to_human"]
            if domain == "retail" else ["write_without_user_yes", "transfer_to_human"])
    print("| arm | " + " | ".join(cats) + " |")
    print("|---|" + "---|" * len(cats))
    for a in arms:
        rs = by_arm[a]
        v = [violations(r) for r in rs]
        print(f"| {a} | " + " | ".join(f"{sum(1 for x in v if c in x)/len(rs):.3f}" for c in cats) + " |")

    # exploratory: paired test on the confirmation-violation flag (decided after seeing trial-0 data)
    print("\n## Exploratory: paired comparison of the 'write without an explicit user yes' flag\n")
    print("Per task, share of runs flagged (averaged over shared trials); exact sign test; Holm across rows.\n")
    print("| comparison | shared tasks | a flagged more | b flagged more | rate a | rate b | raw p | Holm p |")
    print("|---|---|---|---|---|---|---|---|")
    vres = []
    for a, b in comps:
        va = {(r["task"], r["trial"]): int("write_without_user_yes" in violations(r)) for r in by_arm[a]}
        vb = {(r["task"], r["trial"]): int("write_without_user_yes" in violations(r)) for r in by_arm[b]}
        shared = sorted(set(va) & set(vb))
        tasks = sorted({t for t, _ in shared})
        ma = {t: sum(va[k] for k in shared if k[0] == t) / sum(1 for k in shared if k[0] == t) for t in tasks}
        mb = {t: sum(vb[k] for k in shared if k[0] == t) / sum(1 for k in shared if k[0] == t) for t in tasks}
        w = sum(1 for t in tasks if ma[t] > mb[t])
        l = sum(1 for t in tasks if ma[t] < mb[t])
        vres.append((a, b, len(tasks), w, l, sum(ma.values()) / max(1, len(tasks)),
                     sum(mb.values()) / max(1, len(tasks)), binom_two_sided(w, w + l)))
    vadj = holm([x[-1] for x in vres])
    for (a, b, n, w, l, ra, rb, p), pa in zip(vres, vadj):
        print(f"| {a} vs {b} | {n} | {w} | {l} | {ra:.3f} | {rb:.3f} | {p:.3g} | {pa:.3g} |")

    # reward breakdown
    print("\n## Failure source (runs with reward 0)\n")
    print("| arm | failed | wrong DB state | DB right but missing required output | agent error | max steps |")
    print("|---|---|---|---|---|---|")
    for a in arms:
        f = [r for r in by_arm[a] if r["reward"] < 1]
        db = out = er = ms = 0
        for r in f:
            info = (r.get("reward_info") or {}).get("info") or {}
            if r.get("errors"):
                er += 1
            elif not r["done"]:
                ms += 1
            elif "r_actions" in info:
                db += 1
            elif "r_outputs" in info:
                out += 1
        print(f"| {a} | {len(f)} | {db} | {out} | {er} | {ms} |")

    # watchpoint stats
    nr = len(json.loads((HERE / f"rules_{domain}.json").read_text()))
    for a in ("watch", "watch_ctx"):
        if a not in by_arm:
            continue
        comps = [c for r in by_arm[a] for c in r["compactions"]]
        if not comps:
            continue
        patched = sum(1 for c in comps if c.get("missing"))
        nmiss = [len(c.get("missing") or []) for c in comps]
        runs_patched = sum(1 for r in by_arm[a] if any(c.get("missing") for c in r["compactions"]))
        runs_comp = sum(1 for r in by_arm[a] if r["compactions"])
        print(f"\n## Watchpoint ({a})\n")
        print(f"- compactions checked: {len(comps)}; with at least one rule patched: {patched} "
              f"({patched/len(comps):.3f}); mean rules missing per check: {sum(nmiss)/len(nmiss):.2f} of {nr}")
        print(f"- runs with a compaction: {runs_comp}; runs with at least one patch: {runs_patched}")
        miss = collections.Counter(i for c in comps for i in (c.get("missing") or []))
        print("- per-rule miss rate (rule index: share of checks): " +
              ", ".join(f"R{i}: {miss[i]/len(comps):.2f}" for i in range(nr)))


if __name__ == "__main__":
    main(sys.argv[1:] or ["results/main.jsonl"])
