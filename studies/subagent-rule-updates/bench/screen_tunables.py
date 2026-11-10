"""Screening pilot for the real-task study (docs/real-task-study-design.md). No paid calls without --live.

Per task, in order: pull the image if missing, validate the task once (base fails, gold passes), extract
tunables from the gold fix (a check of the extractor on real code), then run a single worker with no
history and no compaction in three arms (no rule, R-const, R-env), `screen_repetitions` runs each, in a
seeded order. Each finished run records the changed scorable files, the extracted candidates, and the
task's test results. Adjudication of which candidates are tunables is a separate step
(bench/adjudicate_tunables.py). With --remove-images, a task's image is removed after its runs.

python3 bench/screen_tunables.py --config configs/tunables-screen.json --output results/bench-tunables-screen-001
python3 bench/screen_tunables.py ... --task-ids a,b --live --remove-images
"""
from __future__ import annotations

import argparse
import fcntl
import json
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

import worker as W  # noqa: E402
from bench import run_bench as RB  # noqa: E402
from bench import session as SE  # noqa: E402
from bench import tunables as T  # noqa: E402
from bench.container import TOOLS as WORKER_TOOLS  # noqa: E402
from bench.evaluate import score_tests, test_patch_paths  # noqa: E402
from relay import save  # noqa: E402

FINISHED = "finished"
POOL = STUDY / "bench/manifests/tunables-judged.json"
SCORABLE_CAP = 200000  # Characters of changed scorable source kept per run, for adjudication.


def pool_ids(path: Path = POOL) -> List[str]:
    return list(json.loads(Path(path).read_text())["usable_ids"])


def build_plan(task_ids: List[str], reps: int, seed: int) -> List[dict]:
    """Task-major, so each task's image is pulled once. Arm and repetition order is shuffled within a task."""
    plan: List[dict] = []
    for i, tid in enumerate(task_ids):
        runs = [{"task_id": tid, "arm": a, "repetition": r} for a in T.ARMS for r in range(reps)]
        random.Random(seed + i).shuffle(runs)
        plan += runs
    return plan


def scorable_changes(changes: dict) -> dict:
    kept, total = {}, 0
    for path, (base, final) in sorted(changes.items()):
        if not T.scorable_path(path):
            continue
        size = len(base or "") + len(final or "")
        if total + size > SCORABLE_CAP:
            kept[path] = None  # Recorded as present but too large to keep.
            continue
        kept[path], total = [base, final], total + size
    return kept


def _changes_and_tests(ws: Any, row: Any, record: dict, *, score: bool) -> None:
    changes = ws.changes(row.base_commit, exclude=frozenset(test_patch_paths(row.test_patch)))
    record["changed_paths"] = sorted(changes)
    record["scorable_files"] = scorable_changes(changes)
    record["extraction"] = T.extract(changes)
    if score:
        started = time.monotonic()
        ws.open_network()
        record["tests"] = score_tests(ws, row)
        record["test_seconds"] = round(time.monotonic() - started, 1)


def gold_check(row: Any, workspace_factory: Any, outdir: Path) -> dict:
    """Apply the gold fix and extract tunables from it. Tests are not run; validation covers them."""
    record: Dict[str, Any] = {"task_id": row.instance_id, "kind": "gold"}
    ws = workspace_factory(row, outdir)
    try:
        ws.start()
        code, _, err = ws._exec(["git", "apply", "-"], input=row.patch, interactive=True, cwd=ws.workdir,
                                timeout=120, max_output=10000)
        if code != 0:
            record.update({"status": "infra_error", "error": "gold patch does not apply: " + err.strip()[-300:]})
            return record
        _changes_and_tests(ws, row, record, score=False)
        record["status"] = FINISHED
    except Exception as exc:
        record.update({"status": "infra_error", "error": "%s: %s" % (type(exc).__name__, exc)})
    finally:
        ws.stop()
    return record


def run_one(client: Any, entry: dict, row: Any, *, outdir: Path, config: dict, workspace_factory: Any) -> dict:
    """One worker on the task. Never raises; failures are recorded in the status."""
    recorder = SE.RecordingClient(client)
    message = T.first_message(entry["arm"], row.problem_statement)
    record: Dict[str, Any] = {**entry, "status": "running", "first_message": message,
                              "worker_system": SE.BENCH_WORKER_SYSTEM}
    try:
        ws = workspace_factory(row, outdir)
        try:
            ws.start()
            started = time.monotonic()
            result = W.run_agent(recorder, SE.BENCH_WORKER_SYSTEM, [], message, tools=WORKER_TOOLS,
                                 execute=lambda n, a, i: ws.execute(n, a, call_index=i),
                                 tag="tunables/%s/%s/rep%d" % (entry["task_id"], entry["arm"], entry["repetition"]),
                                 max_calls=config["max_worker_calls"])
            record.update({"status": result["status"], "error": result["error"], "calls": recorder.calls,
                           "worker_seconds": round(time.monotonic() - started, 1),
                           "final_reply": W.final_text(result["history"])})
            if result["status"] == FINISHED:
                _changes_and_tests(ws, row, record, score=True)
        finally:
            ws.stop()
    except Exception as exc:  # Containers, git: record it unscored and let the runner decide.
        record.update({"status": "infra_error", "error": "%s: %s" % (type(exc).__name__, exc)})
    return record


def ensure_image(image: str, runner: Any) -> dict:
    started = time.monotonic()
    if runner.run(["docker", "image", "inspect", image], timeout=60, max_output=2000)[0] == 0:
        return {"pulled": False, "seconds": 0.0}
    code, _, err = runner.run(["docker", "pull", "-q", image], timeout=1800, max_output=4000)
    if code != 0:
        raise RuntimeError("docker pull failed: " + err.strip()[-300:])
    return {"pulled": True, "seconds": round(time.monotonic() - started, 1)}


def execute(client: Any, model_dir: Path, plan: List[dict], rows: Dict[str, Any], config: dict, *,
            workspace_factory: Any, runner: Any, validate: Any, remove_images: bool) -> Optional[str]:
    """Run the plan task by task. Returns the stopping reason, or None when the plan completed."""
    streak = RB.FailureStreak()
    try:
        for tid in dict.fromkeys(e["task_id"] for e in plan):
            row = rows[tid]
            taskdir = model_dir / "tasks" / tid
            setup: Dict[str, Any] = {"task_id": tid, "image": row.image_name}
            try:
                setup["image_pull"] = ensure_image(row.image_name, runner)
                started = time.monotonic()
                setup["validation"] = validate(row)
                setup["validation_seconds"] = round(time.monotonic() - started, 1)
            except Exception as exc:
                setup["error"] = "%s: %s" % (type(exc).__name__, exc)
            valid = bool(setup.get("validation", {}).get("valid"))
            if valid:
                setup["gold"] = gold_check(row, workspace_factory, taskdir / "gold")
            save(taskdir / "setup.json", setup)
            print("TASK %s valid=%s gold_candidates=%s" % (tid, valid, len(setup.get("gold", {}).get(
                "extraction", {}).get("candidates", []))), flush=True)
            if valid:
                for entry in (e for e in plan if e["task_id"] == tid):
                    outdir = taskdir / entry["arm"] / ("rep%d" % entry["repetition"])
                    before = client.summary()["budget_committed_usd"]
                    record = run_one(client, entry, row, outdir=outdir, config=config, workspace_factory=workspace_factory)
                    record["cost_usd"] = client.summary()["budget_committed_usd"] - before
                    save(outdir / "record.json", record)
                    where = "%s/%s rep%d" % (tid, entry["arm"], entry["repetition"])
                    print("RUN %s status=%s candidates=%d" % (where, record["status"],
                          len(record.get("extraction", {}).get("candidates", []))), flush=True)
                    stop = streak.add(record["status"])
                    if record["status"] == "provider_error":
                        return "provider_error in %s: %s" % (where, record.get("error"))
                    if stop:
                        return "%s, ending at %s" % (stop, where)
            if remove_images:
                runner.run(["docker", "rmi", "-f", row.image_name], timeout=300, max_output=2000)
        return None
    finally:
        streak.report()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=STUDY / "configs/tunables-screen.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-ids", help="Comma list of instance ids (default: every usable task in the pool)")
    parser.add_argument("--model-index", type=int, default=0)
    parser.add_argument("--remove-images", action="store_true")
    parser.add_argument("--live", action="store_true", help="Authorize paid provider calls")
    args = parser.parse_args(argv)
    root = RB.check_output_path(args.output)
    config = json.loads(args.config.read_text())
    ids = RB.select(args.task_ids, pool_ids(), "task ids")
    plan = build_plan(ids, int(config["screen_repetitions"]), int(config["order_seed"]))
    if not args.live:
        save(root / "plan.json", {"entries": plan})
        print("PLAN_WRITTEN entries=%d path=%s (no model calls made)" % (len(plan), root / "plan.json"))
        return 0
    selected = config["models"][args.model_index]
    model_dir = root / ("model-%d" % args.model_index)
    if model_dir.exists():
        raise SystemExit("Refusing existing output directory %s" % model_dir)
    data_root = Path(config["data_root"]).expanduser()
    from bench.container import DockerRunner
    from bench.sources import load_rows
    from bench.validate import validate_task
    from provider import OpenRouterClient, load_key
    pool = json.loads(POOL.read_text())["judgments"]
    repos = {j["repo"] for j in pool if j["instance_id"] in ids}
    rows = {r.instance_id: r for r in load_rows(data_root / RB.PARQUET, repos=repos) if r.instance_id in ids}
    missing = sorted(set(ids) - set(rows))
    if missing:
        raise SystemExit("Missing task rows: %s" % ", ".join(missing))
    load_key()
    runner = DockerRunner()
    network, scoring = config.get("container_network", "none"), config.get("scoring_network")
    validate = lambda row: validate_task(row, runner, row.workdir, network=network, scoring_network=scoring,  # noqa: E731
                                         gold_runs=int(config.get("gold_runs", 1)))
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        model_dir.mkdir()
        try:
            RB.freeze(model_dir, config, selected, args.config, plan, {"task_ids": ids, "rules": T.RULES})
            save(model_dir / "plan.json", {"entries": plan})
        except BaseException:
            shutil.rmtree(model_dir, ignore_errors=True)
            raise
        client = OpenRouterClient(model_dir, model=selected["id"], provider_name=selected["provider"],
                                  budget_usd=selected["budget_usd"], max_calls=config["max_provider_calls"],
                                  temperature=config["temperature"], max_tokens=config["max_output_tokens"],
                                  reasoning_effort=config["reasoning_effort"],
                                  rate_limit_retries=config.get("rate_limit_retries", 0),
                                  timeout_retries=config.get("timeout_retries", 0))
        failure = None
        try:
            failure = execute(client, model_dir, plan, rows, config, workspace_factory=RB.config_workspace_factory(config),
                              runner=runner, validate=validate, remove_images=args.remove_images)
        finally:
            save(model_dir / "provider_summary.json", client.summary())
        print("SCREEN_COMPLETE output=%s error=%s" % (model_dir, failure), flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
