"""Resample the scored task from saved compacted states, to separate session effects from sampling noise.

For each prepared session in the given runs, rerun one task several times from the exact
final history saved in its record.json. No API calls without --live.

python3 resample.py --live --output results/resample-001 --runs results/rule-compaction-001/model-0 ... \
    --condition relay_compact --change config_values --task low_stock --samples 5
"""
from __future__ import annotations

import argparse
import fcntl
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import rule_compaction as RC
import scenarios as S
import worker as W

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "AGENTS.md").exists())


def states(runs: list[Path], conditions: list[str], change: str) -> list[tuple[str, dict]]:
    found = []
    for run in runs:
        for condition in conditions:
            for record_path in sorted(run.glob(f"rep-*/prep/{change}__{condition}/record.json")):
                record = json.loads(record_path.read_text())
                if record.get("setup_valid") and "final_history" in record:
                    found.append((f"{run.parent.name}/{record_path.parts[-4]}/{condition}", record))
    return found


def execute(client, output: Path, args) -> None:
    for state_id, record in states(args.runs, args.condition, args.change):
        system = record.get("system", W.WORKER_SYSTEM)
        for sample in range(args.samples):
            branchdir = output / "samples" / state_id.replace("/", "__") / f"s{sample}"
            workspace = W.Workspace(branchdir / "workspace", S.FIXTURE, branchdir / "tool_events.jsonl")
            result = W.run_worker(client, system, record["final_history"], workspace, RC.task_message(args.task),
                                  tag=f"{state_id}/s{sample}", max_calls=args.max_worker_calls)
            result.update({"state": state_id, "sample": sample, "task": args.task, "score": RC.score(result["files"], args.task, args.change)})
            RC.save(branchdir / "result.json", result)
            print(f"SAMPLE {state_id} s{sample} status={result['status']} changed={result['score']['changed_rule_outcome']}", flush=True)
            if result["status"] == "provider_error":
                raise RuntimeError(f"Stopping after provider error at {branchdir}")


def analyze(output: Path) -> dict:
    by_state: dict[str, Counter] = {}
    for path in sorted(output.glob("samples/*/*/result.json")):
        r = json.loads(path.read_text())
        if r["status"] == "finished":
            by_state.setdefault(r["state"], Counter())[r["score"]["changed_rule_outcome"]] += 1
    lines = ["# Resampled scored task", "", "| State | none | v1 | v2 |", "|---|---|---|---|"]
    for state, c in sorted(by_state.items()):
        lines.append(f"| {state} | {c.get('none', 0)} | {c.get('v1', 0)} | {c.get('v2', 0)} |")
    summary = {state: dict(c) for state, c in by_state.items()}
    RC.save(output / "summary.json", summary)
    (output / "tables.md").write_text("\n".join(lines) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runs", type=Path, nargs="+", default=[])
    parser.add_argument("--condition", nargs="+", default=["relay_compact"])
    parser.add_argument("--change", default="config_values")
    parser.add_argument("--task", default="low_stock")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--max-worker-calls", type=int, default=14)
    parser.add_argument("--budget", type=float, default=2.0)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--analyze", type=Path)
    args = parser.parse_args()
    if args.analyze:
        analyze(args.analyze)
        print((args.analyze / "tables.md").read_text())
        return 0
    if not args.live or not args.output or not args.runs:
        parser.error("No model calls made. Pass --runs, --output, and --live.")
    from provider import OpenRouterClient, load_key
    load_key()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        output = root / "model-0"
        output.mkdir()
        (output / "source").mkdir()
        for name in ("resample.py", "rule_compaction.py", "scenarios.py", "worker.py", "provider.py"):
            shutil.copyfile(HERE / name, output / "source" / name)
        RC.save(output / "manifest.json", {
            "started_utc": datetime.now(timezone.utc).isoformat(), "args": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
            "runs": [str(r) for r in args.runs],
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()})
        # Same generation settings as the rule-compaction runs.
        client = OpenRouterClient(output, model="openai/gpt-6-luna", provider_name="OpenAI", budget_usd=args.budget, max_calls=2000,
                                  temperature=0.2, max_tokens=4096, reasoning_effort="low", timeout_retries=2)
        failure = None
        try:
            execute(client, output, args)
        except Exception as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)}
            RC.save(output / "run_error.json", failure)
        finally:
            RC.save(output / "provider_summary.json", client.summary())
            analyze(output)
        print(f"RUN_COMPLETE output={output} error={failure}", flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
