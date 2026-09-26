import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

old = json.load(open("results2.json"))
new = json.load(open("results3.json"))
pin3 = json.load(open("results_pin3.json"))
exp1_old = [r for r in old if r["exp"] == "constraint"]
exp1_new = [r for r in new if r["exp"] == "constraint"]
exp2_old = [r for r in old if r["exp"] == "goal"]
exp2_new = [r for r in new if r["exp"] == "goal"]

def rate(rows, key, vals):
    if not rows:
        return 0
    return 100 * sum(1 for r in rows if r[key] in vals) / len(rows)

positions = ["early", "mid", "late"]
x = range(len(positions))

# Figure 1: round=1 constraint, all methods
fig, ax = plt.subplots(figsize=(8.5, 4.5))
methods = [
    ("plain", "#c0392b", lambda p: [r for r in exp1_old if r["position"] == p and r["method"] == "plain" and r["rounds"] == 1]),
    ("grace", "#e67e22", lambda p: [r for r in exp1_old if r["position"] == p and r["method"] == "grace" and r["rounds"] == 1]),
    ("naive watchpoint", "#f1c40f", lambda p: [r for r in exp1_old if r["position"] == p and r["method"] == "watch" and r["rounds"] == 1]),
    ("pin", "#8e44ad", lambda p: [r for r in exp1_old if r["position"] == p and r["method"] == "pin" and r["rounds"] == 1]),
    ("watchpoint (extraction)", "#2980b9", lambda p: [r for r in exp1_new if r["position"] == p and r["rounds"] == 1]),
]
w = 0.16
for i, (name, color, fn) in enumerate(methods):
    vals = [rate(fn(p), "decision", {"COMPLY"}) for p in positions]
    offset = (i - 2) * w
    ax.bar([j + offset for j in x], vals, width=w, label=name, color=color)
ax.set_xticks(list(x)); ax.set_xticklabels(positions)
ax.set_ylabel("Violation rate (%)")
ax.set_title("Constraint violation, single compaction event (round=1)\npooled across 2 backbones, 6 scenarios")
ax.set_ylim(0, 100)
ax.legend(fontsize=8, ncol=2)
fig.tight_layout()
fig.savefig("fig4_exp1_round1_allmethods.pdf")
fig.savefig("fig4_exp1_round1_allmethods.png", dpi=150)

# Figure 2: round=3 constraint (heavy recursion), plain / naive-watch / pin / watch2
fig, ax = plt.subplots(figsize=(7.5, 4.5))
def r3(method, source):
    return [
        rate([r for r in source if r["position"] == p and r.get("method") == method and r.get("rounds") == 3], "decision", {"COMPLY"})
        for p in positions
    ]
plain3 = r3("plain", exp1_old)
naive3 = r3("watch", exp1_old)
pin3vals = [rate([r for r in pin3 if r["position"] == p], "decision", {"COMPLY"}) for p in positions]
watch2_3 = [rate([r for r in exp1_new if r["position"] == p and r["rounds"] == 3], "decision", {"COMPLY"}) for p in positions]
w = 0.2
data = [("plain", plain3, "#c0392b"), ("naive watchpoint", naive3, "#f1c40f"), ("pin", pin3vals, "#8e44ad"), ("watchpoint (extraction)", watch2_3, "#2980b9")]
for i, (name, vals, color) in enumerate(data):
    offset = (i - 1.5) * w
    ax.bar([j + offset for j in x], vals, width=w, label=name, color=color)
ax.set_xticks(list(x)); ax.set_xticklabels(positions)
ax.set_ylabel("Violation rate (%)")
ax.set_title("Constraint violation under heavy recursive compaction (3 rounds)\npooled across 2 backbones, 6 scenarios")
ax.set_ylim(0, 100)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("fig5_exp1_round3_allmethods.pdf")
fig.savefig("fig5_exp1_round3_allmethods.png", dpi=150)

# Figure 3: goal task, plain / anchor / naive-watch / watch2
fig, ax = plt.subplots(figsize=(8, 4.5))
def goalrate(method, source):
    return [rate([r for r in source if r["position"] == p and r.get("method") == method], "decision", {"REVISED_TASK"}) for p in positions]
plain_g = goalrate("plain", exp2_old)
anchor_g = goalrate("anchor", exp2_old)
naive_g = goalrate("watch", exp2_old)
watch2_g = [rate([r for r in exp2_new if r["position"] == p], "decision", {"REVISED_TASK"}) for p in positions]
w = 0.18
gdata = [("plain", plain_g, "#c0392b"), ("naive watchpoint", naive_g, "#f1c40f"), ("anchor", anchor_g, "#27ae60"), ("watchpoint (extraction)", watch2_g, "#2980b9")]
for i, (name, vals, color) in enumerate(gdata):
    offset = (i - 1.5) * w
    ax.bar([j + offset for j in x], vals, width=w, label=name, color=color)
ax.set_xticks(list(x)); ax.set_xticklabels(positions)
ax.set_ylabel("Correctly follows revised goal (%)")
ax.set_title("Goal-resurrection correctness by position and method\n(1 backbone, 5 scenarios)")
ax.set_ylim(0, 100)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig("fig6_exp2_allmethods.pdf")
fig.savefig("fig6_exp2_allmethods.png", dpi=150)

print("wrote fig4, fig5, fig6")
