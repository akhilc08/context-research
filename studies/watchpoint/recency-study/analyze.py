import json, math
from collections import defaultdict

def load(path="results.json"):
    return json.load(open(path))

def rate(rows, hit_key, hit_vals):
    if not rows:
        return None
    v = sum(1 for r in rows if r[hit_key] in hit_vals)
    return v, len(rows), round(100 * v / len(rows), 1)

def fisher_p(a, b, c, d):
    n = a + b + c + d
    row1, row2, col1 = a + b, c + d, a + c
    def p_of(x):
        return math.comb(row1, x) * math.comb(row2, col1 - x) / math.comb(n, col1)
    obs = p_of(a)
    lo, hi = max(0, col1 - row2), min(row1, col1)
    return sum(p_of(x) for x in range(lo, hi + 1) if p_of(x) <= obs * 1.0000001)

def main():
    data = load()
    exp1 = [r for r in data if r["exp"] == "constraint" and r["kind"] == "exp1"]
    exp1_ctrl = [r for r in data if r["exp"] == "constraint" and r["kind"] == "exp1_ctrl"]
    exp2 = [r for r in data if r["exp"] == "goal" and r["kind"] == "exp2"]
    exp2_ctrl = [r for r in data if r["exp"] == "goal" and r["kind"] == "exp2_ctrl"]

    print("=" * 70)
    print("EXPERIMENT 1: constraint retention")
    print("=" * 70)
    print(f"total exp1 trials: {len(exp1)}, control trials: {len(exp1_ctrl)}")

    print("\n--- Controls (pooled over scenario x backbone) ---")
    for pos in ["full_context_control", "no_policy_control"]:
        rows = [r for r in exp1_ctrl if r["position"] == pos]
        v, n, pct = rate(rows, "decision", {"COMPLY"})
        print(f"{pos:24s} violation={v}/{n} = {pct}%")

    print("\n--- By backbone x position x method x rounds (pooled over 6 scenarios) ---")
    table = {}
    for backbone in ["qwen", "minimax"]:
        for pos in ["early", "mid", "late"]:
            for method in ["plain", "grace"]:
                for rounds in [1, 3]:
                    rows = [r for r in exp1 if r["backbone"] == backbone and r["position"] == pos
                            and r["method"] == method and r["rounds"] == rounds]
                    v, n, pct = rate(rows, "decision", {"COMPLY"})
                    table[(backbone, pos, method, rounds)] = (v, n, pct)
                    print(f"{backbone:8s} {pos:6s} {method:6s} rounds={rounds} violation={v}/{n} = {pct}%")

    print("\n--- Pooled across both backbones, by position x method x rounds ---")
    pooled = {}
    for pos in ["early", "mid", "late"]:
        for method in ["plain", "grace"]:
            for rounds in [1, 3]:
                rows = [r for r in exp1 if r["position"] == pos and r["method"] == method and r["rounds"] == rounds]
                v, n, pct = rate(rows, "decision", {"COMPLY"})
                pooled[(pos, method, rounds)] = (v, n, pct)
                print(f"{pos:6s} {method:6s} rounds={rounds} violation={v}/{n} = {pct}%")

    print("\n--- Fisher exact: plain vs grace at each position, rounds pooled ---")
    for pos in ["early", "mid", "late"]:
        plain_rows = [r for r in exp1 if r["position"] == pos and r["method"] == "plain"]
        grace_rows = [r for r in exp1 if r["position"] == pos and r["method"] == "grace"]
        vp, np_, pp = rate(plain_rows, "decision", {"COMPLY"})
        vg, ng, pg = rate(grace_rows, "decision", {"COMPLY"})
        p = fisher_p(vp, np_ - vp, vg, ng - vg)
        print(f"{pos:6s} plain={vp}/{np_}({pp}%) grace={vg}/{ng}({pg}%) Fisher p={p:.4g}")

    print("\n--- Round-count effect (compounding check): rounds=1 vs rounds=3, plain method only ---")
    for pos in ["early", "mid", "late"]:
        r1 = [r for r in exp1 if r["position"] == pos and r["method"] == "plain" and r["rounds"] == 1]
        r3 = [r for r in exp1 if r["position"] == pos and r["method"] == "plain" and r["rounds"] == 3]
        v1, n1, p1 = rate(r1, "decision", {"COMPLY"})
        v3, n3, p3 = rate(r3, "decision", {"COMPLY"})
        p = fisher_p(v1, n1 - v1, v3, n3 - v3)
        print(f"{pos:6s} rounds1={v1}/{n1}({p1}%) rounds3={v3}/{n3}({p3}%) Fisher p={p:.4g}")

    print("\n" + "=" * 70)
    print("EXPERIMENT 2: goal resurrection")
    print("=" * 70)
    print(f"total exp2 trials: {len(exp2)}, control trials: {len(exp2_ctrl)}")

    print("\n--- Controls (pooled over scenarios) ---")
    for pos in ["no_redirect_control", "full_context_control"]:
        rows = [r for r in exp2_ctrl if r["position"] == pos]
        v, n, pct = rate(rows, "decision", {"REVISED_TASK"})
        print(f"{pos:24s} stale_or_other={n-v}/{n}, revised={v}/{n} = {pct}%")

    print("\n--- By position x method (pooled over 5 scenarios), rate of correctly following REVISED goal ---")
    for pos in ["early", "mid", "late"]:
        for method in ["plain", "grace", "anchor"]:
            rows = [r for r in exp2 if r["position"] == pos and r["method"] == method]
            v, n, pct = rate(rows, "decision", {"REVISED_TASK"})
            print(f"{pos:6s} {method:6s} correct(revised)={v}/{n} = {pct}%")

    print("\n--- Fisher exact vs plain, at each position ---")
    for pos in ["early", "mid", "late"]:
        plain_rows = [r for r in exp2 if r["position"] == pos and r["method"] == "plain"]
        vp, np_, pp = rate(plain_rows, "decision", {"REVISED_TASK"})
        for method in ["grace", "anchor"]:
            rows = [r for r in exp2 if r["position"] == pos and r["method"] == method]
            v, n, pct = rate(rows, "decision", {"REVISED_TASK"})
            p = fisher_p(vp, np_ - vp, v, n - v)
            print(f"{pos:6s} plain={vp}/{np_}({pp}%) vs {method}={v}/{n}({pct}%) Fisher p={p:.4g}")

    unk1 = sum(1 for r in exp1 if r["decision"] == "UNKNOWN")
    unk2 = sum(1 for r in exp2 if r["decision"] not in ("REVISED_TASK", "ORIGINAL_TASK", "AMBIGUOUS"))
    print(f"\nUnparseable: exp1={unk1}/{len(exp1)}, exp2={unk2}/{len(exp2)}")

if __name__ == "__main__":
    main()
