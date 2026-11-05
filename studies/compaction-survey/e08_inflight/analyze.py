"""Regenerate every E8 table from raw files.

Usage: python3 analyze.py [--run main] > data/<run>/tables.txt
Reads data/cases.json, data/procedures.json, data/batches.json, data/<run>/{judged,extractions,responses}.jsonl,
../shared/usage.jsonl (tagged e8|<run>|...), and data/<run>/handlabels.json if present.
"""
import argparse, collections, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from common import wilson, rate  # noqa: E402

MAIN = ["full", "plain", "structured", "ledger", "ledger_only", "watchpoint", "note_always"]
FOLLOWUP = ["pin_plain", "pin_ledger", "pin_note"]
METHODS = list(MAIN)
TIMINGS = ["threshold", "checkpoint", "midstep"]


def outcome(case, steps, label):
    """Map a (kind, index) label to an outcome category given the truth (k done, maybe k+1 in flight)."""
    k, infl = case["truth"]["k"], case["truth"]["inflight"]
    kind, j = label.get("kind"), label.get("index")
    if kind not in ("step", "verify") or not isinstance(j, int) or not 1 <= j <= len(steps):
        return "other"
    if infl is None:
        if kind == "verify":
            return "verify"
        if j == k + 1:
            return "correct"
        if j <= k:
            return "repeat_harmful" if not steps[j - 1]["idempotent"] else "repeat_safe"
        return "skip"
    # mid-step: step k+1 issued, output unseen
    if kind == "verify":
        return "correct" if j == infl else "verify"
    if j == infl:
        return "rerun_inflight_safe" if steps[j - 1]["idempotent"] else "rerun_inflight_harmful"
    if j <= k:
        return "repeat_harmful" if not steps[j - 1]["idempotent"] else "repeat_safe"
    if j == infl + 1:
        return "proceed_unverified"
    return "skip"


def flags(o):
    return dict(correct=o in ("correct", "rerun_inflight_safe"),
                repeat=o.startswith("repeat") or o.startswith("rerun"),
                harmful=o in ("repeat_harmful", "rerun_inflight_harmful"),
                skip=o in ("skip", "proceed_unverified"), verify=o == "verify", other=o == "other")


def mcnemar(a, b):
    """Exact two-sided McNemar on paired booleans."""
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n10 + n01
    if n == 0:
        return n10, n01, 1.0
    p = sum(math.comb(n, i) for i in range(0, min(n10, n01) + 1)) / 2 ** n
    return n10, n01, min(1.0, 2 * p)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def kappa(x, y):
    cats = sorted(set(x) | set(y))
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    a = ap.parse_args()
    d = HERE / "data"
    cases = {c["case_id"]: c for c in json.loads((d / "cases.json").read_text())}
    procs = {p["id"]: p for p in json.loads((d / "procedures.json").read_text())}
    procs.update({p["id"]: p for p in json.loads((d / "batches.json").read_text())})
    out = d / a.run
    judged = {(r["case_id"], r["method"]): r for r in map(json.loads, (out / "judged.jsonl").read_text().splitlines())}
    extr = {r["case_id"]: r for r in map(json.loads, (out / "extractions.jsonl").read_text().splitlines())}
    resps = {(r["case_id"], r["method"]): r for r in map(json.loads, (out / "responses.jsonl").read_text().splitlines())}
    if all((c, m) in judged for c in cases for m in FOLLOWUP):
        METHODS.extend(FOLLOWUP)
    cids = sorted({c for c, _ in judged if all((c, m) in judged for m in MAIN)})
    O = {}
    for (cid, m), r in judged.items():
        c = cases[cid]
        O[(cid, m)] = outcome(c, procs[c["proc_id"]]["steps"], r["judge"])

    def sel(**kw):
        return [c for c in cids if all(cases[c][k] == v for k, v in kw.items())]

    print(f"# E8 tables (run={a.run}); complete cases: {len(cids)}\n")
    for title, subset in [("ALL timings pooled", cids)] + [(f"timing={t}", sel(timing=t)) for t in TIMINGS]:
        print(f"## {title}")
        for fam in [None, "proc", "batch"]:
            sub = [c for c in subset if fam is None or cases[c]["family"] == fam]
            if not sub:
                continue
            print(f"### family={fam or 'both'} (n={len(sub)} per method)")
            print(f"{'method':12s} | {'correct-next':22s} | {'repeat':22s} | {'harmful repeat':22s} | {'skip':22s} | verify | other")
            for m in METHODS:
                f = [flags(O[(c, m)]) for c in sub]
                n = len(f)
                cnt = {k: sum(x[k] for x in f) for k in f[0]}
                print(f"{m:12s} | {rate(cnt['correct'], n):22s} | {rate(cnt['repeat'], n):22s} | "
                      f"{rate(cnt['harmful'], n):22s} | {rate(cnt['skip'], n):22s} | {cnt['verify']:6d} | {cnt['other']}")
            print()

    print("## Correct-next, threshold and checkpoint pooled (completed-step timings; no in-flight ambiguity)")
    s2 = [c for c in cids if cases[c]["timing"] != "midstep"]
    for m in METHODS:
        print(f"{m:12s} {rate(sum(flags(O[(c, m)])['correct'] for c in s2), len(s2))}")
    print()
    print("## Outcome distribution, mid-step timing")
    for m in METHODS:
        print(m, dict(collections.Counter(O[(c, m)] for c in sel(timing="midstep"))))
    print("\n## Lenient mid-step correct (verify in-flight, safe rerun, or proceed to next step)")
    for m in METHODS:
        s = sel(timing="midstep")
        k = sum(O[(c, m)] in ("correct", "rerun_inflight_safe", "proceed_unverified") for c in s)
        print(f"{m:12s} {rate(k, len(s))}")

    print("\n## Correct-next by progress level (all timings)")
    for m in METHODS:
        print(f"{m:12s} " + " | ".join(f"{lv}: {rate(sum(flags(O[(c, m)])['correct'] for c in sel(level=lv)), len(sel(level=lv)))}"
                                        for lv in ["early", "mid", "late"]))

    print("\n## Correct-next by method x timing (on-task only: excludes 'other')")
    for m in METHODS:
        row = []
        for t in TIMINGS:
            s = [c for c in sel(timing=t) if O[(c, m)] != "other"]
            row.append(f"{t}: {rate(sum(flags(O[(c, m)])['correct'] for c in s), len(s))}")
        print(f"{m:12s} " + " | ".join(row))

    # confirmatory family: paired McNemar on correct-next, all timings pooled, plus timing contrasts
    print("\n## Paired tests on correct-next (exact McNemar, Holm across the family below)")
    tests = []
    for x, y in [("full", "plain"), ("structured", "plain"), ("ledger", "plain"), ("watchpoint", "plain"),
                 ("note_always", "plain"), ("ledger_only", "ledger"), ("note_always", "watchpoint"), ("ledger", "full")]:
        tests.append((f"{x} vs {y} (all timings)", [flags(O[(c, x)])["correct"] for c in cids],
                      [flags(O[(c, y)])["correct"] for c in cids]))
    for t1, t2 in [("checkpoint", "threshold"), ("checkpoint", "midstep")]:
        for m in ["plain", "full"]:
            pairs = [(c, c.replace(t1, t2)) for c in sel(timing=t1) if c.replace(t1, t2) in cids]
            tests.append((f"{m}: {t1} vs {t2} (paired by procedure and k)", [flags(O[(p, m)])["correct"] for p, _ in pairs],
                          [flags(O[(q, m)])["correct"] for _, q in pairs]))
    res = [(name,) + mcnemar(x, y) + (sum(x), sum(y), len(x)) for name, x, y in tests]
    adj = holm([r[3] for r in res])
    for (name, n10, n01, p, sx, sy, n), pa in zip(res, adj):
        print(f"{name:58s} {sx}/{n} vs {sy}/{n}; discordant {n10}:{n01}; p={p:.3g}; Holm p={pa:.3g}")

    if "pin_plain" in METHODS:
        print("\n## EXPLORATORY follow-up family (plan pinning, decided after seeing data; Holm within this family)")
        ft = [(x, y) for x, y in [("pin_plain", "plain"), ("pin_ledger", "pin_plain"), ("pin_note", "pin_plain"),
                                  ("pin_ledger", "ledger"), ("pin_note", "note_always"), ("pin_ledger", "full")]]
        fr = []
        for x, y in ft:
            xs = [flags(O[(c, x)])["correct"] for c in cids]
            ys = [flags(O[(c, y)])["correct"] for c in cids]
            fr.append((f"{x} vs {y} (all timings)",) + mcnemar(xs, ys) + (sum(xs), sum(ys), len(xs)))
        for (name, n10, n01, p, sx, sy, n), pa in zip(fr, holm([r[3] for r in fr])):
            print(f"{name:58s} {sx}/{n} vs {sy}/{n}; discordant {n10}:{n01}; p={p:.3g}; Holm p={pa:.3g}")

    print("\n## Harmful repeats, paired (exploratory, not in the Holm family)")
    for x in [m for m in METHODS if m != "plain"]:
        n10, n01, p = mcnemar([flags(O[(c, x)])["harmful"] for c in cids], [flags(O[(c, "plain")])["harmful"] for c in cids])
        print(f"{x:12s} vs plain: discordant {n10}:{n01}; p={p:.3g}")

    print("\n## Watchpoint extraction")
    for t in TIMINGS:
        s = sel(timing=t)
        ok = sum(not extr[c]["patched"] for c in s)
        print(f"{t:10s} extraction matched harness record: {rate(ok, len(s))}; patched {len(s) - ok}")
    s = [c for c in cids if extr[c]["patched"]]
    print("patched cases: watchpoint correct", rate(sum(flags(O[(c, 'watchpoint')])['correct'] for c in s), len(s)),
          "| plain correct", rate(sum(flags(O[(c, 'plain')])['correct'] for c in s), len(s)))
    s = [c for c in cids if not extr[c]["patched"]]
    print("unpatched cases: plain correct", rate(sum(flags(O[(c, 'plain')])['correct'] for c in s), len(s)),
          "| note_always correct", rate(sum(flags(O[(c, 'note_always')])['correct'] for c in s), len(s)))

    # cost
    print("\n## Cost per case (model calls and tokens; compaction shared by methods that reuse the plain summary)")
    use = collections.defaultdict(lambda: [0, 0, 0])
    for line in (HERE.parent / "shared" / "usage.jsonl").read_text().splitlines():
        r = json.loads(line)
        parts = r.get("tag", "").split("|")
        if len(parts) == 3 and parts[0] == "e8" and parts[1] == a.run:
            u = use[parts[2]]
            u[0] += 1; u[1] += r.get("in") or 0; u[2] += r.get("out") or 0
    nc = len(cases) if a.run == "main" else len({c for c, _ in resps})
    comps = {"full": [], "plain": ["compact_plain"], "structured": ["compact_structured"], "ledger": ["compact_plain"],
             "ledger_only": [], "watchpoint": ["compact_plain", "extract"], "note_always": ["compact_plain"],
             "pin_plain": ["compact_plain"], "pin_ledger": ["compact_plain"], "pin_note": ["compact_plain"]}
    for m in METHODS:
        tags = comps[m] + [f"agent_{m}"]
        calls = sum(use[t][0] for t in tags) / nc
        tin = sum(use[t][1] for t in tags) / nc
        tout = sum(use[t][2] for t in tags) / nc
        ctx = sum(resps[(c, m)]["context_chars"] for c in cids) / len(cids)
        print(f"{m:12s} calls/case {calls:.2f}  input tok/case {tin:7.0f}  output tok/case {tout:6.0f}  agent context chars {ctx:6.0f}")
    print("(output tokens exclude hidden reasoning tokens; logged usage only)")

    # exploratory: what is inside "other"
    print("\n## EXPLORATORY: decomposition of 'other' (heuristic, decided after seeing data)")
    print("off-task = leading tool not used by any procedure step (mostly resuming the filler side work);")
    print("batch bad-target = the batch tool is invoked on an id not in the list or a placeholder")
    for t in TIMINGS:
        for m in METHODS:
            s = sel(timing=t)
            off = bad = on = 0
            for c in s:
                if O[(c, m)] != "other":
                    continue
                p = procs[cases[c]["proc_id"]]
                cmd = judged[(c, m)]["command"]
                tool = lead_tool(cmd)
                tools = {lead_tool(x["command"]) for x in p["steps"]}
                if p.get("family") == "batch" and tool in tools:
                    bad += 1
                elif tool in tools:
                    on += 1
                else:
                    off += 1
            print(f"{t:10s} {m:12s} other={off + bad + on:3d}: off-task {rate(off, len(s))}; on-tool unmapped {on}; batch bad-target {bad}")

    # judge checks
    print("\n## Judge cross-check: deterministic batch parser vs LLM judge (batch cases)")
    bt = [(r["judge"], r["parse"]) for r in judged.values() if "parse" in r]
    agree = sum(outcome_key(j) == outcome_key(p) for j, p in bt)
    print(f"(kind, index) agreement: {rate(agree, len(bt))}")
    print(f"step-index agreement where both say step: {rate(sum(j.get('index') == p.get('index') for j, p in bt if j['kind'] == p['kind'] == 'step'), sum(j['kind'] == p['kind'] == 'step' for j, p in bt))}")
    hp = out / "handlabels.json"
    if hp.exists():
        hl = json.loads(hp.read_text())
        jo, ho = [], []
        for h in hl:
            c = cases[h["case_id"]]
            steps = procs[c["proc_id"]]["steps"]
            jo.append(outcome(c, steps, judged[(h["case_id"], h["method"])]["judge"]))
            ho.append(outcome(c, steps, h))
        n = len(hl)
        print(f"\n## Judge validation against hand labels (n={n})")
        print(f"outcome-category agreement: {rate(sum(x == y for x, y in zip(jo, ho)), n)}; Cohen's kappa {kappa(jo, ho):.2f}")
        print(f"(kind, index) agreement: {rate(sum(outcome_key(judged[(h['case_id'], h['method'])]['judge']) == outcome_key(h) for h in hl), n)}")
        for h, x, y in zip(hl, jo, ho):
            if x != y:
                print(f"  disagree {h['case_id']} {h['method']}: judge={x} hand={y}")


def lead_tool(cmd):
    toks = [t for t in cmd.replace("(", " ").split() if "=" not in t and t not in ("sudo", "env", "umask", "077;", "cd")]
    t = toks[0] if toks else ""
    if t in ("python", "python3", "python3.11") and len(toks) > 2 and toks[1] == "-m":
        t = toks[2]
    return t.split("/")[-1]


def outcome_key(lbl):
    return (lbl.get("kind"), lbl.get("index") if lbl.get("kind") != "other" else None)


if __name__ == "__main__":
    main()
