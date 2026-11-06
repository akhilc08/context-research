"""Validate benchmark tasks in their containers before any worker run.

A task is valid when the test patch alone leaves every FAIL_TO_PASS test unpassed, the gold
patch plus test patch resolves it, the image has `timeout` (run_command depends on it), the
image's checkout has the base commit, and no rule path for the repository is gitignored (an
ignored rule directory would hide the worker's new files from scoring).

python3 bench/validate.py --manifest <cases.json> --data-root ~/bench-data --output results/bench-validation
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

from bench.container import ContainerWorkspace, DockerRunner  # noqa: E402
from bench.evaluate import score_tests  # noqa: E402
from bench.sources import TaskRow  # noqa: E402

PARQUET = "swe-rebench-v2/data/train-00000-of-00001.parquet"
APPLY_TIMEOUT = 120
RULES_DIR = STUDY / "bench" / "rules"
PROBE = "test_bench_probe"
_EXT = re.compile(r"\\\.([A-Za-z0-9]+)\$?$")


def _has_timeout(ws: ContainerWorkspace) -> bool:
    code, _, _ = ws._exec(["sh", "-c", "command -v timeout"], timeout=60, max_output=1000)
    return code == 0


def rule_paths(rules: Iterable[Any]) -> List[str]:
    """Paths whose ignore status decides whether a rule's files can be seen: each added_line path,
    and each new_file directory plus a probe file in it named to fit the rule's name pattern."""
    out: List[str] = []
    for rule in rules:
        for m in (rule.old, rule.new):
            if m["type"] == "added_line":
                out.append(m["path_glob"].replace("**/", "").replace("*", PROBE).replace("?", "x"))
            else:
                ext = _EXT.search(m["name_regex"])
                out += [m["dir"].rstrip("/"), "%s/%s%s" % (m["dir"].rstrip("/"), PROBE, "." + ext.group(1) if ext else "")]
    return sorted(set(out))


def _check_base(ws: ContainerWorkspace, row: TaskRow, paths: List[str], result: dict) -> None:
    code, _, _ = ws._git("cat-file", "-e", row.base_commit)
    result["has_base_commit"] = code == 0
    if code != 0:
        result["reasons"].append("base commit %s missing from the image" % row.base_commit)
    if not paths:
        return
    # Exit 0: some paths are ignored (listed on stdout). Exit 1: none are. Anything else is an error.
    code, out, err = ws._git("check-ignore", "--", *paths)
    if code not in (0, 1):
        result["reasons"].append("git check-ignore failed: " + err.strip()[-300:])
        return
    result["ignored_rule_paths"] = [p for p in out.splitlines() if p] if code == 0 else []
    if result["ignored_rule_paths"]:
        result["reasons"].append("rule paths are gitignored: " + ", ".join(result["ignored_rule_paths"]))


def _base_run(row: TaskRow, runner: Any, workdir: str, result: dict, paths: List[str], network: Optional[str],
              scoring_network: Optional[str]) -> None:
    ws = ContainerWorkspace(row.image_name, runner, workdir=workdir, network=network, scoring_network=scoring_network)
    ws.start()
    try:
        result["has_timeout"] = _has_timeout(ws)
        _check_base(ws, row, paths, result)
        ws.open_network()
        scored = score_tests(ws, row)
    finally:
        ws.stop()
    if scored["test_patch_conflict"]:
        result["reasons"].append("test patch does not apply at base")
        return
    result["base_fail_to_pass"] = scored["fail_to_pass"]
    if not scored["fail_to_pass"]:
        result["reasons"].append("no FAIL_TO_PASS tests")
        return
    result["base_fail_to_pass_failing"] = all(s != "PASSED" for s in scored["fail_to_pass"].values())
    if not result["base_fail_to_pass_failing"]:
        result["reasons"].append("a FAIL_TO_PASS test passes without the gold patch")


def _gold_run(row: TaskRow, runner: Any, workdir: str, result: dict, network: Optional[str],
              scoring_network: Optional[str]) -> None:
    result["gold_resolved"] = False  # each repeat must earn its own pass
    ws = ContainerWorkspace(row.image_name, runner, workdir=workdir, network=network, scoring_network=scoring_network)
    ws.start()
    try:
        code, _, err = ws._exec(["git", "apply", "-"], input=row.patch, interactive=True, cwd=workdir,
                                timeout=APPLY_TIMEOUT, max_output=10000)
        if code != 0:
            result["reasons"].append("gold patch does not apply: " + err.strip()[-300:])
            return
        # No reset here: a gold patch that edits test-patch files must still show up as a conflict.
        ws.open_network()
        scored = score_tests(ws, row, reset_test_files=False)
    finally:
        ws.stop()
    if scored["test_patch_conflict"]:
        result["reasons"].append("test patch does not apply on top of gold patch")
        return
    result["gold_resolved"] = scored["resolved"]
    result["gold_statuses"] = {"fail_to_pass": scored["fail_to_pass"], "pass_to_pass": scored["pass_to_pass"]}
    if not scored["resolved"]:
        result["reasons"].append("gold patch does not resolve the tests")


def validate_task(row: TaskRow, runner: Any, workdir: str, *, paths: Iterable[str] = (),
                  network: Optional[str] = None, scoring_network: Optional[str] = None, gold_runs: int = 1) -> dict:
    """paths: rule paths to check with git check-ignore (see rule_paths). network: docker run --network.
    scoring_network: joined just before the tests run, as in a live run. gold_runs: the gold patch must
    resolve the tests in this many fresh containers in a row, which catches flaky tests."""
    result: Dict[str, Any] = {"instance_id": row.instance_id, "gold_resolved": False,
                              "base_fail_to_pass_failing": False, "has_timeout": False,
                              "has_base_commit": False, "ignored_rule_paths": None, "valid": False, "reasons": []}
    paths = list(paths)
    try:
        _base_run(row, runner, workdir, result, paths, network, scoring_network)
        result["gold_runs_passed"] = 0
        for _ in range(gold_runs):
            _gold_run(row, runner, workdir, result, network, scoring_network)
            if not result["gold_resolved"]:
                break
            result["gold_runs_passed"] += 1
        if 0 < result["gold_runs_passed"] < gold_runs:
            result["reasons"].append("flaky: gold resolved %d of %d runs" % (result["gold_runs_passed"],
                                                                               result["gold_runs_passed"] + 1))
        if not result["has_timeout"]:
            result["reasons"].append("image has no timeout command")
    except Exception as exc:  # one bad task must not stop the rest
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    result["valid"] = bool(result["gold_resolved"] and result["base_fail_to_pass_failing"]
                           and result["has_timeout"] and result["has_base_commit"]
                           and (result["ignored_rule_paths"] == [] or not paths) and "error" not in result)
    result["reason"] = "; ".join(result["reasons"])
    return result


def task_ids(cases: Iterable[Any]) -> List[str]:
    seen: Dict[str, None] = {}
    for c in cases:
        seen.setdefault(c.first)
        seen.setdefault(c.second)
    return list(seen)


def validate_manifest(cases: Iterable[Any], rows: Dict[str, TaskRow], output: Path, runner: Any, *,
                      rules_dir: Optional[Path] = None, network: Optional[str] = None,
                      scoring_network: Optional[str] = None, gold_runs: int = 1) -> dict:
    """With rules_dir, each task's repository rule paths are checked for being gitignored."""
    from bench.rules import load_rules
    cases = list(cases)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths_by_repo: Dict[str, List[str]] = {}
    if rules_dir is not None:
        for repo in sorted({c.repo for c in cases}):
            paths_by_repo[repo] = rule_paths(load_rules(Path(rules_dir) / ("%s.json" % repo.replace("/", "__"))))
    tasks: Dict[str, dict] = {}
    for iid in task_ids(cases):
        row = rows.get(iid)
        if row is None:
            full = {"instance_id": iid, "valid": False, "error": "task not found in dataset"}
        else:
            full = validate_task(row, runner, row.workdir, paths=paths_by_repo.get(row.repo, ()), network=network,
                                 scoring_network=scoring_network, gold_runs=gold_runs)
        (output / (iid + ".json")).write_text(json.dumps(full, indent=2) + "\n")
        # Summary keeps ids, booleans and reason strings only: no test names, no problem text.
        tasks[iid] = {k: full[k] for k in ("valid", "gold_resolved", "base_fail_to_pass_failing", "has_timeout",
                                           "has_base_commit", "gold_runs_passed", "reason", "error") if k in full}
    summary = {"tasks": tasks, "valid_ids": [i for i, t in tasks.items() if t["valid"]]}
    (output / "validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=STUDY / "configs/bench-v1.json",
                        help="Read container_network (default none) and scoring_network from it")
    parser.add_argument("--gold-runs", type=int, default=1,
                        help="Fresh gold-patch runs that must all resolve the tests (default 1)")
    args = parser.parse_args(argv)
    if args.gold_runs < 1:
        parser.error("--gold-runs must be at least 1")
    from bench.cases import load_manifest
    from bench.run_bench import check_output_path
    from bench.sources import load_rows
    output = check_output_path(args.output)
    config = json.loads(args.config.read_text())
    cases = load_manifest(args.manifest)
    rows = {r.instance_id: r for r in load_rows(args.data_root / PARQUET)}
    summary = validate_manifest(cases, rows, output, DockerRunner(), rules_dir=RULES_DIR,
                                 network=config.get("container_network", "none"),
                                 scoring_network=config.get("scoring_network"), gold_runs=args.gold_runs)
    print("%d of %d tasks valid" % (len(summary["valid_ids"]), len(summary["tasks"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
