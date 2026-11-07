"""Pre-registered analysis for docs/amendment-status-test.md.

Unit: compacted state. A state's failure rate is the share of its low-stock runs (the scored branch
plus the resamples) that do not follow the config rule. Cells are compared with a two-sided
permutation test on state-level failure rates.

python3 analyze_amendment.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from rule_compaction import SESSIONS

HERE = Path(__file__).resolve().parent
R = HERE / "results"
CELLS = {"changelog": "O-C (config.py, original)", "config_reverse": "A-C (config.py, amended)",
         "changelog_sfirst": "O-S (settings.get, original)", "config_values": "A-S (settings.get, amended)"}
RESAMPLES = [R / "resample-002/model-0", R / "resample-003/model-0"]


def followed(r: dict, session: str) -> bool:
    """Recomputed from the stored outcome, since runs before the amendment test lack config_followed."""
    spec = SESSIONS[session]
    expected = spec["to"] if spec["change"] == "config_values" else spec["start"]["config_values"]
    return r["score"]["details"]["config_values"]["outcome"] == expected


def state_rates(runs: list[str]) -> dict[str, dict[str, list[int]]]:
    """session -> state id -> list of failures (1) and successes (0)."""
    out: dict[str, dict[str, list[int]]] = {s: {} for s in CELLS}
    for run in runs:
        for path in sorted((R / run / "model-0").glob("rep-*/branches/*__relay_compact__low_stock/result.json")):
            r = json.loads(path.read_text())
            if r["status"] != "finished" or r["change"] not in CELLS:
                continue
            out[r["change"]].setdefault(f"{run}/{r['rep']:02d}", []).append(0 if followed(r, r["change"]) else 1)
    # Resamples. A later resample run replaces an earlier one for the same state (top-up of a partial state).
    samples: dict[str, list[int]] = {}
    for resample in RESAMPLES:
        found: dict[str, list[int]] = {}
        for path in sorted(resample.glob("samples/*/*/result.json")):
            r = json.loads(path.read_text())
            if r["status"] != "finished":
                continue
            session = r.get("session") or "config_values"
            found.setdefault(r["state"], []).append(0 if followed(r, session) else 1)
        samples.update(found)
    for state, values in samples.items():
        run, rep, cond = state.split("/")
        session = cond.split(":")[0] if ":" in cond else "config_values"
        key = f"{run}/{int(rep.split('-')[1]):02d}"
        if run in runs and session in out and key in out[session]:
            out[session][key] += values
    return out


def permutation(a: list[float], b: list[float], n: int = 20000, seed: int = 0) -> float:
    observed = abs(sum(a) / len(a) - sum(b) / len(b))
    pool, k, rng, hits = a + b, len(a), random.Random(seed), 0
    for _ in range(n):
        rng.shuffle(pool)
        hits += abs(sum(pool[:k]) / k - sum(pool[k:]) / (len(pool) - k)) >= observed - 1e-12
    return hits / n


def report(runs: list[str], label: str) -> list[str]:
    data = state_rates(runs)
    means = {s: [sum(v) / len(v) for v in states.values()] for s, states in data.items() if states}
    lines = [f"## {label}", "", "| Cell | States | Runs | Failures | Mean state failure rate |", "|---|---|---|---|---|"]
    for s, name in CELLS.items():
        if s not in means:
            continue
        runs_n = sum(len(v) for v in data[s].values())
        fails = sum(sum(v) for v in data[s].values())
        lines.append(f"| {name} | {len(means[s])} | {runs_n} | {fails} | {sum(means[s]) / len(means[s]):.2f} |")
    lines += ["", "| Comparison | Difference | Permutation p |", "|---|---|---|"]
    for a, b, what in [("changelog_sfirst", "changelog", "content, original rules (O-S vs O-C)"),
                       ("config_values", "config_reverse", "content, amended rules (A-S vs A-C)"),
                       ("config_reverse", "changelog", "status, config.py (A-C vs O-C)"),
                       ("config_values", "changelog_sfirst", "status, settings.get (A-S vs O-S)")]:
        if a in means and b in means:
            d = sum(means[a]) / len(means[a]) - sum(means[b]) / len(means[b])
            lines.append(f"| {what} | {d:+.2f} | {permutation(means[a], means[b]):.4f} |")
    return lines + [""]


if __name__ == "__main__":
    out = ["# Amendment-status test: state-level analysis", ""]
    out += report(["rule-compaction-amend-001"], "This run alone (rule-compaction-amend-001)")
    out += report(["rule-compaction-amend-001", "rule-compaction-001", "rule-compaction-002"],
                  "Pooled with the earlier O-C and A-S sessions (rule-compaction-001 and 002)")
    text = "\n".join(out)
    (R / "rule-compaction-amend-001/model-0/amendment-analysis.md").write_text(text + "\n")
    print(text)
