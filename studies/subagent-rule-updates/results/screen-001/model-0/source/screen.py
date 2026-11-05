"""Screen candidate rules: does the model break each rule by default, and follow each version when told?

One worker, no manager, no compaction. Arms: no rule, and each rule version stated in
the worker's first message (like a manager's spawn prompt). No API calls without --live.

python3 screen.py --live --output results/screen-001
python3 screen.py --analyze results/screen-001/model-0
"""
from __future__ import annotations

import argparse
import fcntl
import json
import random
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import scenarios as S
import worker as W

HERE = Path(__file__).resolve().parent
REPO = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").exists())
NO_RULE = "none"
# Pass criteria, fixed before the run.
MAX_DEFAULT_COMPLIANCE = 0.2  # With no rule, at most 2 in 10 runs may already match a version.
MIN_TOLD_COMPLIANCE = 0.9  # Told a version, at least 9 in 10 runs must follow it.


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def arms() -> list[str]:
    return [NO_RULE] + [f"{rule}:{version}" for rule in S.RULES for version in ("v1", "v2")]


def first_message(arm: str, task: str) -> str:
    task_text = S.TASKS[task]["text"]
    if arm == NO_RULE:
        return f"Task: {task_text}"
    rule, version = arm.split(":")
    return f"Project rule from the user: {S.RULES[rule][version]}\n\nTask: {task_text}"


def score(files: dict[str, str], task: str) -> dict:
    return {"task_attempted": S.task_attempted(files, task),
            **{rule: classify(files, task) for rule, classify in S.CLASSIFIERS.items()}}


def execute(client: Any, output: Path, config: dict) -> None:
    runs = [(arm, task, rep) for arm in arms() for task in S.TASKS for rep in range(config["repetitions"])]
    random.Random(config["order_seed"]).shuffle(runs)
    save(output / "run_order.json", runs)
    for index, (arm, task, rep) in enumerate(runs):
        run_id = f"{arm.replace(':', '__')}__{task}__r{rep}"
        rundir = output / "runs" / run_id
        workspace = W.Workspace(rundir / "workspace", S.FIXTURE, rundir / "tool_events.jsonl")
        message = first_message(arm, task)
        result = W.run_worker(client, W.WORKER_SYSTEM, [], workspace, message, tag=run_id, max_calls=config["max_worker_calls"])
        result.update({"run_id": run_id, "arm": arm, "task": task, "rep": rep, "execution_index": index,
                       "first_message": message, "score": score(result["files"], task)})
        save(rundir / "result.json", result)
        print(f"RUN {index + 1}/{len(runs)} {run_id} status={result['status']}", flush=True)
        if result["status"] == "provider_error":
            raise RuntimeError(f"Stopping after provider error; partial run kept at {rundir}")


def analyze(output: Path) -> dict:
    results = [json.loads(p.read_text()) for p in sorted((output / "runs").glob("*/result.json"))]
    valid = [r for r in results if r["status"] == "finished"]
    summary = {"runs": len(results), "finished": len(valid), "statuses": dict(Counter(r["status"] for r in results)),
               "task_attempted": sum(r["score"]["task_attempted"] for r in valid), "rules": {}}
    lines = ["# Rule screen", "", f"Runs: {len(results)}, finished: {len(valid)}.", ""]
    for rule in S.RULES:
        cells = {}
        for arm in (NO_RULE, f"{rule}:v1", f"{rule}:v2"):
            subset = [r for r in valid if r["arm"] == arm]
            cells[arm] = {"n": len(subset), "outcomes": dict(Counter(r["score"][rule]["outcome"] for r in subset))}
        default = cells[NO_RULE]
        default_matches = sum(default["outcomes"].get(o, 0) for o in ("v1", "v2", "both"))
        told = {v: cells[f"{rule}:{v}"] for v in ("v1", "v2")}
        checks = {
            "against_default": bool(default["n"]) and default_matches / default["n"] <= MAX_DEFAULT_COMPLIANCE,
            **{f"follows_{v}": bool(c["n"]) and c["outcomes"].get(v, 0) / c["n"] >= MIN_TOLD_COMPLIANCE for v, c in told.items()},
        }
        summary["rules"][rule] = {"cells": cells, "checks": checks, "passes": all(checks.values())}
        lines += [f"## {rule}: {'PASS' if all(checks.values()) else 'FAIL'}", "", "| Arm | n | none | v1 | v2 | both | other |", "|---|---|---|---|---|---|---|"]
        for arm, cell in cells.items():
            o = cell["outcomes"]
            lines.append(f"| {arm} | {cell['n']} | " + " | ".join(str(o.get(k, 0)) for k in ("none", "v1", "v2", "both", "other")) + " |")
        lines += ["", "Checks: " + ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in checks.items()), ""]
    save(output / "summary.json", summary)
    (output / "tables.md").write_text("\n".join(lines))
    return summary


def freeze_manifest(output: Path, config: dict, selected: dict, config_path: Path) -> None:
    paths = [HERE / name for name in ("scenarios.py", "worker.py", "screen.py", "provider.py")] + [config_path.resolve()]
    for path in paths:
        dest = output / "source" / path.relative_to(HERE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    save(output / "manifest.json", {
        "started_utc": datetime.now(timezone.utc).isoformat(), "config": config, "selected_model": selected,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True),
        "arms": arms(), "tasks": S.TASKS, "rules": S.RULES, "worker_system": W.WORKER_SYSTEM,
        "pass_criteria": {"max_default_compliance": MAX_DEFAULT_COMPLIANCE, "min_told_compliance": MIN_TOLD_COMPLIANCE},
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "configs/screen.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-index", type=int, default=0)
    parser.add_argument("--live", action="store_true", help="Authorize paid provider calls for this fixed config")
    parser.add_argument("--analyze", type=Path, help="Recompute summary.json and tables.md for a model directory")
    args = parser.parse_args()
    if args.analyze:
        print((analyze(args.analyze) and (args.analyze / "tables.md").read_text()))
        return 0
    if not args.live or not args.output:
        parser.error("No model calls made. Pass --output and --live to run.")
    config = json.loads(args.config.read_text())
    if config["total_budget_usd"] != sum(m["budget_usd"] for m in config["models"]):
        raise ValueError("Per-model caps must sum to the authorized total")
    selected = config["models"][args.model_index]
    from provider import OpenRouterClient, load_key
    load_key()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        output = root / f"model-{args.model_index}"
        output.mkdir()
        freeze_manifest(output, config, selected, args.config)
        client = OpenRouterClient(output, model=selected["id"], provider_name=selected["provider"],
                                  budget_usd=selected["budget_usd"], max_calls=config["max_provider_calls"],
                                  temperature=config["temperature"], max_tokens=config["max_output_tokens"],
                                  reasoning_effort=config["reasoning_effort"])
        failure = None
        try:
            execute(client, output, config)
        except Exception as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)}
            save(output / "run_error.json", failure)
        finally:
            save(output / "provider_summary.json", client.summary())
            analyze(output)
        print(f"RUN_COMPLETE output={output} error={failure}", flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
