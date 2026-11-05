"""Print a condensed, human-readable trajectory of one E25 episode, for hand-checking the grader.

Usage: python3 view.py results/main/episodes/<eid>.json.gz [--full]
"""
import gzip, json, sys


def main(path, full=False):
    ep = json.load(gzip.open(path, "rt"))
    ev = {e["after_calls"]: [] for e in ep["events"]}
    for e in ep["events"]:
        ev[e["after_calls"]].append(e["kind"])
    comp = {c["after_calls"]: c for c in ep["compactions"]}
    print(f"== {ep['eid']}  end={ep['end']} calls={ep['calls']} nudges={ep['nudges']}")
    for k in ev.get(0, []):
        print(f"   >>> operator: {k}")
    for r in ep["log"]:
        a = r["args"]
        if r["name"] == "write_file":
            c = a.get("content") or ""
            extra = " [imports re]" if "import re" in c else ""
            desc = f"{r.get('path')} ({len(c)} chars{', NOOP' if r.get('noop') else ''}){extra}"
        elif r["name"] == "git_commit":
            desc = f"{a.get('message', '')!r} -> {r['output'].splitlines()[-1][:120]}"
        elif r["name"] == "run_tests":
            last = [x for x in r["output"].splitlines() if x.strip()][-1:] or [""]
            desc = f"{a.get('test_file') or '(all)'} -> {last[0][:100]}"
        else:
            desc = json.dumps(a)[:100]
        ok = "" if r["ok"] else "  !ERR " + r["output"][:80]
        print(f"{r['i']:3d} {r['name']:11s} {desc}{ok}")
        if full and r["name"] == "write_file":
            print("      | " + (a.get("content") or "").replace("\n", "\n      | "))
        for k in ev.get(r["i"], []):
            print(f"   >>> operator: {k}")
        if r["i"] in comp:
            print(f"   ### compaction (raw from entry {comp[r['i']]['raw_from']})")
    o = ep["outcome"]
    print("-- outcome:", {k: v for k, v in o.items() if k.startswith(("v_", "pass_", "dropped", "task", "core", "redirect", "wrote", "regex", "viol"))})
    print("-- changed:", ep["changed"])


if __name__ == "__main__":
    main(sys.argv[1], "--full" in sys.argv)
