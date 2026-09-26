import json
from analyze import rate, fisher_p

def main():
    data = json.load(open("results2.json"))
    exp1 = [r for r in data if r["exp"] == "constraint"]
    exp2 = [r for r in data if r["exp"] == "goal"]

    print("=" * 70)
    print("EXPERIMENT 1b: constraint retention, plain/grace/pin/watch, round=1")
    print("=" * 70)
    for pos in ["early", "mid", "late"]:
        for method in ["plain", "grace", "pin", "watch"]:
            rows = [r for r in exp1 if r["position"] == pos and r["method"] == method and r["rounds"] == 1]
            v, n, pct = rate(rows, "decision", {"COMPLY"})
            print(f"{pos:6s} {method:6s} rounds=1 violation={v}/{n} = {pct}%")
        print()

    print("--- Fisher exact vs plain, round=1, pooled over backbones+scenarios ---")
    for pos in ["early", "mid", "late"]:
        plain_rows = [r for r in exp1 if r["position"] == pos and r["method"] == "plain" and r["rounds"] == 1]
        vp, np_, pp = rate(plain_rows, "decision", {"COMPLY"})
        for method in ["grace", "pin", "watch"]:
            rows = [r for r in exp1 if r["position"] == pos and r["method"] == method and r["rounds"] == 1]
            v, n, pct = rate(rows, "decision", {"COMPLY"})
            p = fisher_p(vp, np_ - vp, v, n - v)
            print(f"{pos:6s} plain={vp}/{np_}({pp}%) vs {method}={v}/{n}({pct}%) p={p:.4g}")

    print("\n--- round=3, plain vs watch (does the fix survive heavy recursion?) ---")
    for pos in ["early", "mid", "late"]:
        plain_rows = [r for r in exp1 if r["position"] == pos and r["method"] == "plain" and r["rounds"] == 3]
        watch_rows = [r for r in exp1 if r["position"] == pos and r["method"] == "watch" and r["rounds"] == 3]
        vp, np_, pp = rate(plain_rows, "decision", {"COMPLY"})
        vw, nw, pw = rate(watch_rows, "decision", {"COMPLY"})
        p = fisher_p(vp, np_ - vp, vw, nw - vw)
        print(f"{pos:6s} plain={vp}/{np_}({pp}%) watch={vw}/{nw}({pw}%) p={p:.4g}")

    print("\n--- watch patch rate (how often did the audit actually trigger a repair?) ---")
    for pos in ["early", "mid", "late"]:
        for rounds in [1, 3]:
            rows = [r for r in exp1 if r["position"] == pos and r["method"] == "watch" and r["rounds"] == rounds]
            if not rows:
                continue
            patched = sum(1 for r in rows if r["patched"])
            print(f"{pos:6s} rounds={rounds} patched={patched}/{len(rows)}")

    print("\n--- pin vs watch cost: watch only patches when needed ---")
    for pos in ["early", "mid", "late"]:
        rows = [r for r in exp1 if r["position"] == pos and r["method"] == "watch" and r["rounds"] == 1]
        patched = sum(1 for r in rows if r["patched"])
        print(f"{pos:6s} watch patched {patched}/{len(rows)} trials (pin would append every single time)")

    print("\n" + "=" * 70)
    print("EXPERIMENT 2b: goal resurrection, plain/anchor/watch")
    print("=" * 70)
    for pos in ["early", "mid", "late"]:
        for method in ["plain", "anchor", "watch"]:
            rows = [r for r in exp2 if r["position"] == pos and r["method"] == method]
            v, n, pct = rate(rows, "decision", {"REVISED_TASK"})
            print(f"{pos:6s} {method:6s} correct(revised)={v}/{n} = {pct}%")

    print("\n--- Fisher exact vs plain ---")
    for pos in ["early", "mid", "late"]:
        plain_rows = [r for r in exp2 if r["position"] == pos and r["method"] == "plain"]
        vp, np_, pp = rate(plain_rows, "decision", {"REVISED_TASK"})
        for method in ["anchor", "watch"]:
            rows = [r for r in exp2 if r["position"] == pos and r["method"] == method]
            v, n, pct = rate(rows, "decision", {"REVISED_TASK"})
            p = fisher_p(vp, np_ - vp, v, n - v)
            print(f"{pos:6s} plain={vp}/{np_}({pp}%) vs {method}={v}/{n}({pct}%) p={p:.4g}")

    print("\n--- watch patch rate for goal task ---")
    for pos in ["early", "mid", "late"]:
        rows = [r for r in exp2 if r["position"] == pos and r["method"] == "watch"]
        patched = sum(1 for r in rows if r["patched"])
        print(f"{pos:6s} patched={patched}/{len(rows)}")

if __name__ == "__main__":
    main()
