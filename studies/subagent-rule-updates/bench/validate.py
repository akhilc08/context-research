"""Validate benchmark tasks in their containers before any worker run.

A task is valid when the test patch alone leaves every FAIL_TO_PASS test unpassed, the gold
patch plus test patch resolves it, and the image has `timeout` (run_command depends on it).

python3 bench/validate.py --manifest <cases.json> --data-root ~/bench-data --output results/bench-validation
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

from bench.container import ContainerWorkspace, DockerRunner  # noqa: E402
from bench.evaluate import score_tests  # noqa: E402
from bench.sources import TaskRow  # noqa: E402

PARQUET = "swe-rebench-v2/data/train-00000-of-00001.parquet"
APPLY_TIMEOUT = 120


def _has_timeout(ws: ContainerWorkspace) -> bool:
    code, _, _ = ws._exec(["sh", "-c", "command -v timeout"], timeout=60, max_output=1000)
    return code == 0


def _base_run(row: TaskRow, runner: Any, workdir: str, result: dict) -> None:
    ws = ContainerWorkspace(row.image_name, runner, workdir=workdir)
    ws.start()
    try:
        result["has_timeout"] = _has_timeout(ws)
        scored = score_tests(ws, row)
    finally:
        ws.stop()
    if scored["test_patch_conflict"]:
        result["reasons"].append("test patch does not apply at base")
        return
    result["base_fail_to_pass"] = scored["fail_to_pass"]
    result["base_fail_to_pass_failing"] = all(s != "PASSED" for s in scored["fail_to_pass"].values())
    if not result["base_fail_to_pass_failing"]:
        result["reasons"].append("a FAIL_TO_PASS test passes without the gold patch")


def _gold_run(row: TaskRow, runner: Any, workdir: str, result: dict) -> None:
    ws = ContainerWorkspace(row.image_name, runner, workdir=workdir)
    ws.start()
    try:
        code, _, err = ws._exec(["git", "apply", "-"], input=row.patch, interactive=True, cwd=workdir,
                                timeout=APPLY_TIMEOUT, max_output=10000)
        if code != 0:
            result["reasons"].append("gold patch does not apply: " + err.strip()[-300:])
            return
        scored = score_tests(ws, row)
    finally:
        ws.stop()
    if scored["test_patch_conflict"]:
        result["reasons"].append("test patch does not apply on top of gold patch")
        return
    result["gold_resolved"] = scored["resolved"]
    result["gold_statuses"] = {"fail_to_pass": scored["fail_to_pass"], "pass_to_pass": scored["pass_to_pass"]}
    if not scored["resolved"]:
        result["reasons"].append("gold patch does not resolve the tests")


def validate_task(row: TaskRow, runner: Any, workdir: str) -> dict:
    result: Dict[str, Any] = {"instance_id": row.instance_id, "gold_resolved": False,
                              "base_fail_to_pass_failing": False, "has_timeout": False,
                              "valid": False, "reasons": []}
    try:
        _base_run(row, runner, workdir, result)
        _gold_run(row, runner, workdir, result)
        if not result["has_timeout"]:
            result["reasons"].append("image has no timeout command")
    except Exception as exc:  # one bad task must not stop the rest
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    result["valid"] = bool(result["gold_resolved"] and result["base_fail_to_pass_failing"]
                           and result["has_timeout"] and "error" not in result)
    result["reason"] = "; ".join(result["reasons"])
    return result


def task_ids(cases: Iterable[Any]) -> List[str]:
    seen: Dict[str, None] = {}
    for c in cases:
        seen.setdefault(c.first)
        seen.setdefault(c.second)
    return list(seen)


def validate_manifest(cases: Iterable[Any], rows: Dict[str, TaskRow], output: Path, runner: Any) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    tasks: Dict[str, dict] = {}
    for iid in task_ids(cases):
        row = rows.get(iid)
        if row is None:
            full = {"instance_id": iid, "valid": False, "error": "task not found in dataset"}
        else:
            full = validate_task(row, runner, row.workdir)
        (output / (iid + ".json")).write_text(json.dumps(full, indent=2) + "\n")
        # Summary keeps ids, booleans and reason strings only: no test names, no problem text.
        tasks[iid] = {k: full[k] for k in ("valid", "gold_resolved", "base_fail_to_pass_failing",
                                           "has_timeout", "reason", "error") if k in full}
    summary = {"tasks": tasks, "valid_ids": [i for i, t in tasks.items() if t["valid"]]}
    (output / "validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    from bench.cases import load_manifest
    from bench.sources import load_rows
    cases = load_manifest(args.manifest)
    rows = {r.instance_id: r for r in load_rows(args.data_root / PARQUET)}
    summary = validate_manifest(cases, rows, args.output, DockerRunner())
    print("%d of %d tasks valid" % (len(summary["valid_ids"]), len(summary["tasks"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
