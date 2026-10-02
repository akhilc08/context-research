"""E19 analysis: regenerates every table from raw/ and judged/ with no model calls.

Hypotheses and metrics, fixed before the main run (written at 06:35 after a one-session pilot whose design was then changed):

Primary metric: next-step correct (E13 "after" scoring: the proposed command performs step k+1) on sample 0,
at the three fixed mid-operation probe points per session (mid-O1, mid-O2, end/mid-O3). Every arm is probed at
the same turns, so units are paired by (session, point). n = 24 sessions x 3 points = 72 per arm.
Primary family: exact McNemar, Holm across 10 tests: for each content (plain, pinstruct)
  checkpoint vs threshold, model vs threshold, operator vs threshold, random vs threshold, checkpoint vs model.
Sample 1 is reported as a replicate.

  H1. With plain content, the harness-verified checkpoint beats the token threshold on next-step correct.
  H2. Model-judged timing does not beat the checkpoint (it costs extra calls and sees less than the harness).
  H3. Operator-aware timing lowers battery failures (rules, ruled-out approach, identifier, goal) relative to the
      threshold (secondary family, same 10 comparisons, Holm, on "battery harm": at least one battery item fails,
      an item failing when both samples are wrong).
  H4. Random timing at the same count does not differ from the threshold (control).
  H5. With pinned structured content, the timing gaps shrink (difference of checkpoint-minus-threshold gaps,
      session-cluster bootstrap CI; exploratory).
Everything else (post-compaction probes, repeated-work proxy, harmful repeats, cost) is descriptive.

Usage: python3 analyze.py [--out DIR]  -> writes results.md and results.json in DIR
"""
import argparse, json, math, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVN = HERE.parent
sys.path.insert(0, str(OVN))
sys.path.insert(0, str(OVN / "e9_cheap_validation"))
sys.path.insert(0, str(HERE))
from common import wilson  # noqa: E402
from items import FACTS  # noqa: E402
from build import state_at  # noqa: E402

SESSIONS = json.loads((HERE / "data" / "sessions.json").read_text())
PROCS = {p["id"]: p for p in json.loads((OVN / "e13_plan_pinning" / "data" / "procedures.json").read_text())}
POLICIES = ["threshold", "checkpoint", "model", "operator", "random"]
CONTENTS = ["plain", "pinstruct"]
ARMS = ["full"] + [f"{p}/{c}" for c in CONTENTS for p in POLICIES]
DIRECTIVE = ("rule0", "rule1", "approach")


def parse_fact(ans, fact):
    stale, correct = fact[2].strip(), fact[3]
    pc = re.search(re.escape(correct) + r"(?![\w])", ans)
    ps = re.search(re.escape(stale) + r"(?![\w-])", ans)
    if pc and (not ps or pc.start() <= ps.start()):
        return "CORRECT"
    return "STALE" if ps else "OTHER"


def norm(c):
    return re.sub(r"\s+", " ", c.strip().strip("`").strip()).rstrip(";")


READ_TOOLS = {"cat", "sed", "head", "tail", "less", "nl", "rg", "grep", "bat", "wc"}
PATH_RE = re.compile(r"[\w./-]+\.(?:py|yaml|yml|toml|json|cfg|ini|md|txt|sql|tf|sh|go|ts|js|lock|conf|hcl)\b")


def earlier_work(s, p):
    cmds, files = set(), set()
    for t in s["turns"][:p + 1]:
        for m in re.finditer(r"`([^`]{3,})`", t):
            c = m.group(1)
            cmds.add(norm(c))
            first = c.strip().split()[0] if c.strip() else ""
            if first in READ_TOOLS:
                files.update(PATH_RE.findall(c))
    return cmds, files


def next_outcome(s, pr, x, J):
    op = pr["op"]
    k = op["k"]
    lab = J["next"].get(f"{op['proc']}\x1f{x['cmd']}\x1f{x['reason']}")
    if lab is None:
        return None
    steps = PROCS[op["proc"]]["steps"]
    if lab["kind"] == "step" and lab["index"]:
        j = lab["index"]
        if j == k + 1:
            out = "correct"
        elif j <= k:
            out = "harmful_repeat" if not steps[j - 1]["idempotent"] else "repeat"
        else:
            out = "skip"
    elif lab["kind"] == "verify":
        out = "verify"
    else:
        out = "other"
    cmds, files = earlier_work(s, pr["turn"])
    c = x["cmd"].strip()
    first = c.split()[0] if c else ""
    reread = first in READ_TOOLS and any(f in files for f in PATH_RE.findall(c))
    rerun = norm(c) in cmds and out != "correct"
    return dict(out=out, repeated_work=out in ("repeat", "harmful_repeat") or reread or rerun,
                reread=reread, rerun=rerun)


def item_ok(s, pr, item, text, J):
    if text is None:
        return False
    if item in DIRECTIVE:
        return J[item].get(text) == "RESPECTS"
    if item == "goal":
        want = "NEW" if state_at(s, pr["turn"])["goal_new"] else "OLD"
        return J["goal"].get(text) == want
    if item == "fact":
        return parse_fact(text, FACTS[s["fact"]]) == "CORRECT"
    raise KeyError(item)


def score_probe(s, pr, J):
    """Per-item fail (all samples wrong), per-sample item correctness, next-step outcomes per sample."""
    res = dict(items={}, items_s=defaultdict(list), next=[], unparsed=0)
    for item in pr["items"]:
        oks = []
        for b in pr["battery"]:
            t = b["parsed"].get(item)
            res["unparsed"] += t is None
            oks.append(item_ok(s, pr, item, t, J))
        res["items"][item] = not any(oks)  # True = failed
        res["items_s"][item] = oks
    for x in pr.get("next", []):
        res["next"].append(next_outcome(s, pr, x, J))
    return res

# ---------------------------------------------------------------- statistics

def mcnemar(a, b):
    """Exact two-sided McNemar on paired booleans. Returns (b_only_a, only_b, p)."""
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n10 + n01
    if n == 0:
        return n10, n01, 1.0
    k = min(n10, n01)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return n10, n01, p


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def rate(k, n):
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.0f}% [{100 * lo:.0f} to {100 * hi:.0f}]"


def boot_diff(units, f, B=4000, seed=7):
    """Session-cluster bootstrap CI for statistic f(list of units); units are lists per session."""
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        samp = [units[rng.randrange(len(units))] for _ in units]
        v = f([u for sess in samp for u in sess])
        if v is not None:
            vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def pfmt(p):
    return f"{p:.2g}" if p >= 0.001 else f"{p:.1e}"

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    out = Path(args.out)
    raws = {int(p.stem[1:]): json.loads(p.read_text()) for p in sorted((out / "raw").glob("s*.json"))}
    judged = {int(p.stem[1:]): json.loads(p.read_text()) for p in sorted((out / "judged").glob("s*.json"))}
    sids = [sid for sid in sorted(raws) if sid in judged and "probes" in raws[sid]
            and all(f"{a}|fixed|{pt['name']}" in raws[sid]["probes"] for a in ARMS for pt in SESSIONS[sid]["probes"])]
    md, R = [], dict(sessions=sids)
    md.append(f"# E19 results (generated by analyze.py)\n\nSessions analysed: {len(sids)}. Fixed probe points per "
              f"session: 3. Model: {raws[sids[0]]['model'] if sids else '?'}.\n")

    # ---- schedules
    md.append("## Schedules\n")
    md.append("| Policy | Compactions per session | Mid-operation compactions | Hard-limit fallbacks | Model timing calls per session | Raw tokens at fire (mean) |")
    md.append("|---|---|---|---|---|---|")
    sched = {}
    for pol in POLICIES:
        counts, mid, hard, calls, rawt, tot = [], 0, 0, [], [], 0
        for sid in sids:
            s, sc = SESSIONS[sid], raws[sid]["schedules"][pol]
            counts.append(len(sc["cuts"]))
            for c in sc["cuts"]:
                t = c["turn"]
                tot += 1
                mid += s["sub"][t].startswith("O") and s["kinds"][t] not in ("close",)
                hard += c["why"] == "hard"
                rawt.append(c["raw_tokens"])
            calls.append(len(sc["judge_log"]))
        sched[pol] = dict(counts=Counter(counts), mid=mid, hard=hard, total=tot, calls=sum(calls) / len(sids),
                          raw_at_fire=sum(rawt) / len(rawt))
        md.append(f"| {pol} | {dict(sorted(Counter(counts).items()))} | {rate(mid, tot)} | {hard}/{tot} | "
                  f"{sum(calls) / len(sids):.1f} | {sum(rawt) / len(rawt):.0f} |")
    R["schedules"] = {k: {**v, "counts": dict(v["counts"])} for k, v in sched.items()}

    # ---- plan survival at fixed points: is the operation request verbatim in the agent's context?
    md.append("\nOperation request still verbatim at the fixed probe points (mechanism check):\n")
    md.append("| Policy | mid_O1 | mid_O2 | end_O3 |")
    md.append("|---|---|---|---|")
    for pol in POLICIES:
        row = []
        for pi, name in enumerate(["mid_O1", "mid_O2", "end_O3"]):
            k = 0
            for sid in sids:
                s = SESSIONS[sid]
                pt = s["probes"][pi]
                prior = [c["turn"] for c in raws[sid]["schedules"][pol]["cuts"] if c["turn"] <= pt["turn"]]
                rs = prior[-1] - 2 if prior else 0
                k += rs <= s["starts"][pt["op"]]
            row.append(f"{k}/{len(sids)}")
        md.append(f"| {pol} | " + " | ".join(row) + " |")

    # ---- fixed-point scores
    S = {}  # arm -> list per session of list per point of score dicts
    for arm in ARMS:
        S[arm] = []
        for sid in sids:
            s = SESSIONS[sid]
            S[arm].append([dict(score_probe(s, raws[sid]["probes"][f"{arm}|fixed|{pt['name']}"], judged[sid]),
                                ctx=raws[sid]["probes"][f"{arm}|fixed|{pt['name']}"]["ctx_tokens"],
                                raw=raws[sid]["probes"][f"{arm}|fixed|{pt['name']}"]["raw_tokens"], point=pt["name"])
                           for pt in s["probes"]])

    def flat(arm):
        return [u for sess in S[arm] for u in sess]

    def nc(u, i=0):
        return u["next"][i] is not None and u["next"][i]["out"] == "correct"

    def bharm(u):
        return any(u["items"].values())

    md.append("\n## Fixed probe points (paired across arms)\n")
    md.append("Next-step outcome uses sample 0 unless noted. Battery harm: at least one battery item fails (both "
              "samples wrong). Brackets are 95% Wilson intervals.\n")
    md.append("| Arm | Next-step correct (s0) | Correct (s1) | Harmful repeat (s0) | Repeated-work proxy (s0) | Battery harm | Mean battery items failed | Agent context tokens | Verbatim tokens |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    fixed = {}
    for arm in ARMS:
        U = flat(arm)
        n = len(U)
        c0 = sum(nc(u, 0) for u in U)
        c1 = sum(nc(u, 1) for u in U)
        hr = sum(u["next"][0] is not None and u["next"][0]["out"] == "harmful_repeat" for u in U)
        rw = sum(u["next"][0] is not None and u["next"][0]["repeated_work"] for u in U)
        bh = sum(bharm(u) for u in U)
        mf = sum(sum(u["items"].values()) for u in U) / n
        fixed[arm] = dict(n=n, correct0=c0, correct1=c1, harmful=hr, repeated=rw, battery_harm=bh, mean_failed=mf,
                          ctx=sum(u["ctx"] for u in U) / n, raw=sum(u["raw"] for u in U) / n)
        md.append(f"| {arm} | {rate(c0, n)} | {rate(c1, n)} | {hr}/{n} | {rate(rw, n)} | {rate(bh, n)} | {mf:.2f} | "
                  f"{fixed[arm]['ctx']:.0f} | {fixed[arm]['raw']:.0f} |")
    R["fixed"] = fixed

    md.append("\nNext-step correct (sample 0) by probe point:\n")
    md.append("| Arm | mid_O1 | mid_O2 | end_O3 |")
    md.append("|---|---|---|---|")
    for arm in ARMS:
        cells = []
        for pi in range(3):
            us = [sess[pi] for sess in S[arm]]
            cells.append(rate(sum(nc(u) for u in us), len(us)))
        md.append(f"| {arm} | " + " | ".join(cells) + " |")

    md.append("\nNext-step outcome categories (sample 0):\n")
    cats = ["correct", "verify", "repeat", "harmful_repeat", "skip", "other"]
    md.append("| Arm | " + " | ".join(cats) + " |")
    md.append("|---|" + "---|" * len(cats))
    for arm in ARMS:
        cn = Counter(u["next"][0]["out"] for u in flat(arm) if u["next"][0] is not None)
        md.append(f"| {arm} | " + " | ".join(str(cn.get(c, 0)) for c in cats) + " |")

    md.append("\nPer-item battery accuracy (mean over probes and samples; n = probes where the item exists):\n")
    items = ["rule0", "rule1", "approach", "fact", "goal"]
    md.append("| Arm | " + " | ".join(items) + " |")
    md.append("|---|" + "---|" * len(items))
    for arm in ARMS:
        cells = []
        for it in items:
            v = [ok for u in flat(arm) for ok in u["items_s"].get(it, [])]
            cells.append(f"{sum(v) / len(v):.2f} (n={len(v) // 2})" if v else "n/a")
        md.append(f"| {arm} | " + " | ".join(cells) + " |")
    unp = sum(u["unparsed"] for arm in ARMS for u in flat(arm))
    tot_items = sum(len(u["items"]) * 2 for arm in ARMS for u in flat(arm))
    md.append(f"\nBattery answers that could not be parsed (counted as wrong): {unp}/{tot_items}.\n")

    # ---- tests
    comps = [("checkpoint", "threshold"), ("model", "threshold"), ("operator", "threshold"),
             ("random", "threshold"), ("checkpoint", "model")]

    def family(metric, label):
        rows, ps = [], []
        for con in CONTENTS:
            for a, b in comps:
                A, B = f"{a}/{con}", f"{b}/{con}"
                xa, xb = [metric(u) for u in flat(A)], [metric(u) for u in flat(B)]
                n10, n01, p = mcnemar(xa, xb)
                rows.append([f"{A} vs {B}", sum(xa), sum(xb), n10, n01, p])
                ps.append(p)
        for r, h in zip(rows, holm(ps)):
            r.append(h)
        md.append(f"\n### {label}\n")
        md.append("| Comparison | First | Second | Only first | Only second | p | Holm p |")
        md.append("|---|---|---|---|---|---|---|")
        for r in rows:
            md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {pfmt(r[5])} | {pfmt(r[6])} |")
        return rows

    md.append("\n## Paired tests (exact McNemar, Holm within each family of 10)\n")
    R["primary"] = family(lambda u: nc(u, 0), "Primary: next-step correct, sample 0")
    R["replicate"] = family(lambda u: nc(u, 1), "Replicate: next-step correct, sample 1 (not part of the primary family)")
    R["battery"] = family(bharm, "Secondary: battery harm (at least one item failed)")
    R["vs_full"] = family(lambda u: nc(u, 0) and not bharm(u), "Exploratory: fully correct probe (next step right and no battery item failed)")

    # ---- mechanism: next-step correct split by whether the operation request was still verbatim (exploratory)
    md.append("\n### Mechanism: next-step correct by whether the operation request is still verbatim (exploratory)\n")
    md.append("| Content | Request verbatim | Request summarized |")
    md.append("|---|---|---|")
    R["mechanism"] = {}
    for con in CONTENTS:
        yes, no = [0, 0], [0, 0]
        for pol in POLICIES:
            for i, sid in enumerate(sids):
                s = SESSIONS[sid]
                for pi, pt in enumerate(s["probes"]):
                    prior = [c["turn"] for c in raws[sid]["schedules"][pol]["cuts"] if c["turn"] <= pt["turn"]]
                    rs = prior[-1] - 2 if prior else 0
                    bucket = yes if rs <= s["starts"][pt["op"]] else no
                    bucket[0] += nc(S[f"{pol}/{con}"][i][pi])
                    bucket[1] += 1
        R["mechanism"][con] = dict(verbatim=yes, summarized=no)
        md.append(f"| {con} | {rate(*yes)} | {rate(*no)} |")

    # ---- H5 interaction
    md.append("\n### H5: does pinned structured content shrink the timing gap? (exploratory)\n")
    md.append("| Policy vs threshold | Gap with plain (points) | Gap with pinstruct | Difference [95% bootstrap CI] |")
    md.append("|---|---|---|---|")
    R["h5"] = {}
    for pol in ["checkpoint", "model", "operator", "random"]:
        units = [[(nc(u), nc(v), nc(w), nc(x)) for u, v, w, x in zip(S[f"{pol}/plain"][i], S["threshold/plain"][i],
                                                                     S[f"{pol}/pinstruct"][i], S["threshold/pinstruct"][i])]
                 for i in range(len(sids))]

        def gap(us, j):
            return 100 * (sum(u[j] for u in us) - sum(u[j + 1] for u in us)) / len(us)

        def dd(us):
            return gap(us, 0) - gap(us, 2)
        allu = [u for sess in units for u in sess]
        lo, hi = boot_diff(units, dd)
        R["h5"][pol] = dict(plain=gap(allu, 0), pin=gap(allu, 2), dd=dd(allu), ci=[lo, hi])
        md.append(f"| {pol} | {gap(allu, 0):+.0f} | {gap(allu, 2):+.0f} | {dd(allu):+.0f} [{lo:+.0f} to {hi:+.0f}] |")

    # ---- post-compaction probes
    md.append("\n## Right after each compaction (descriptive; each policy probes at its own turns)\n")
    md.append("One sample per probe. Next-step is scored only when an operation was in progress at the compaction.\n")
    md.append("| Arm | Probes | Battery harm | Mean items failed | Op in progress | Next-step correct | Harmful repeat | Repeated-work proxy |")
    md.append("|---|---|---|---|---|---|---|---|")
    R["post"] = {}
    for arm in ARMS[1:]:
        U = []
        for sid in sids:
            s = SESSIONS[sid]
            for key, pr in raws[sid]["probes"].items():
                if key.startswith(arm + "|post|"):
                    U.append(score_probe(s, pr, judged[sid]))
        n = len(U)
        bh = sum(bharm(u) for u in U)
        mf = sum(sum(u["items"].values()) for u in U) / max(1, n)
        ops = [u for u in U if u["next"]]
        c = sum(nc(u) for u in ops)
        hr = sum(u["next"][0] is not None and u["next"][0]["out"] == "harmful_repeat" for u in ops)
        rw = sum(u["next"][0] is not None and u["next"][0]["repeated_work"] for u in ops)
        R["post"][arm] = dict(n=n, battery_harm=bh, mean_failed=mf, ops=len(ops), correct=c, harmful=hr, repeated=rw)
        md.append(f"| {arm} | {n} | {rate(bh, n)} | {mf:.2f} | {len(ops)} | {rate(c, len(ops))} | {hr} | {rate(rw, len(ops))} |")

    # ---- cost
    md.append("\n## Cost per session\n")
    md.append("Compaction calls and input characters per session for plain content; timing calls are the model-judged "
              "policy's extra calls (shared by both contents, since timing never sees the summary).\n")
    md.append("| Policy | Compaction calls | Compaction input chars | Timing calls | Timing input chars | Extra input relative to threshold |")
    md.append("|---|---|---|---|---|---|")
    base = None
    R["cost"] = {}
    for pol in POLICIES:
        cc = sum(len(raws[sid]["chains"][f"{pol}/plain"]) for sid in sids) / len(sids)
        ci = sum(c["in_chars"] for sid in sids for c in raws[sid]["chains"][f"{pol}/plain"]) / len(sids)
        tc = sum(len(raws[sid]["schedules"][pol]["judge_log"]) for sid in sids) / len(sids)
        ti = sum(x["in_chars"] for sid in sids for x in raws[sid]["schedules"][pol]["judge_log"]) / len(sids)
        base = base or (ci + ti)
        R["cost"][pol] = dict(compact_calls=cc, compact_chars=ci, timing_calls=tc, timing_chars=ti)
        md.append(f"| {pol} | {cc:.1f} | {ci:,.0f} | {tc:.1f} | {ti:,.0f} | {100 * ((ci + ti) / base - 1):+.0f}% |")

    (out / "results.md").write_text("\n".join(md) + "\n")
    (out / "results.json").write_text(json.dumps(R, indent=1, default=str))
    print("\n".join(md))


if __name__ == "__main__":
    main()
