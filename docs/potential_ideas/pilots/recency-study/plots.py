import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

data = json.load(open("results.json"))
exp1 = [r for r in data if r["exp"] == "constraint" and r["kind"] == "exp1"]
exp2 = [r for r in data if r["exp"] == "goal" and r["kind"] == "exp2"]

def rate(rows, key, vals):
    if not rows:
        return 0
    return 100 * sum(1 for r in rows if r[key] in vals) / len(rows)

positions = ["early", "mid", "late"]

# Figure 1: exp1, pooled both backbones & rounds, plain vs grace violation rate by position
fig, ax = plt.subplots(figsize=(6.8, 4.2))
plain = [rate([r for r in exp1 if r["position"] == p and r["method"] == "plain"], "decision", {"COMPLY"}) for p in positions]
grace = [rate([r for r in exp1 if r["position"] == p and r["method"] == "grace"], "decision", {"COMPLY"}) for p in positions]
x = range(len(positions))
w = 0.35
ax.bar([i - w/2 for i in x], plain, width=w, label="plain (tail=2)", color="#c0392b")
ax.bar([i + w/2 for i in x], grace, width=w, label="grace (tail=8)", color="#2980b9")
ax.set_xticks(list(x)); ax.set_xticklabels(["early", "mid", "late"])
ax.set_ylabel("Violation rate (%)")
ax.set_title("Experiment 1: constraint violation by position and tail width\n(pooled across 2 backbones, 6 scenarios, both round counts)")
ax.set_ylim(0, 100)
ax.legend()
fig.tight_layout()
fig.savefig("fig1_exp1_position_method.pdf")
fig.savefig("fig1_exp1_position_method.png", dpi=150)

# Figure 2: exp1, round-count compounding effect, plain method only, by position
fig, ax = plt.subplots(figsize=(5.5, 4))
r1 = [rate([r for r in exp1 if r["position"] == p and r["method"] == "plain" and r["rounds"] == 1], "decision", {"COMPLY"}) for p in positions]
r3 = [rate([r for r in exp1 if r["position"] == p and r["method"] == "plain" and r["rounds"] == 3], "decision", {"COMPLY"}) for p in positions]
ax.bar([i - w/2 for i in x], r1, width=w, label="1 round", color="#f39c12")
ax.bar([i + w/2 for i in x], r3, width=w, label="3 rounds (recursive)", color="#8e44ad")
ax.set_xticks(list(x)); ax.set_xticklabels(["early", "mid", "late"])
ax.set_ylabel("Violation rate (%)")
ax.set_title("Experiment 1: effect of recursive round count\n(plain method, pooled across 2 backbones, 6 scenarios)")
ax.set_ylim(0, 100)
ax.legend()
fig.tight_layout()
fig.savefig("fig2_exp1_rounds.pdf")
fig.savefig("fig2_exp1_rounds.png", dpi=150)

# Figure 3: exp2, correct (revised-goal) rate by position and method
fig, ax = plt.subplots(figsize=(5.5, 4))
methods = ["plain", "grace", "anchor"]
colors = ["#c0392b", "#2980b9", "#27ae60"]
w2 = 0.25
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for i, m in enumerate(methods):
    vals = [rate([r for r in exp2 if r["position"] == p and r["method"] == m], "decision", {"REVISED_TASK"}) for p in positions]
    offset = (i - 1) * w2
    ax.bar([j + offset for j in x], vals, width=w2, label=m, color=colors[i])
ax.set_xticks(list(x)); ax.set_xticklabels(["early", "mid", "late"])
ax.set_ylabel("Correctly follows revised goal (%)")
ax.set_title("Experiment 2: goal-resurrection correctness by position and method\n(1 backbone, 5 scenarios)")
ax.set_ylim(0, 100)
ax.legend()
fig.tight_layout()
fig.savefig("fig3_exp2_position_method.pdf")
fig.savefig("fig3_exp2_position_method.png", dpi=150)

print("wrote fig1, fig2, fig3 (pdf+png)")
