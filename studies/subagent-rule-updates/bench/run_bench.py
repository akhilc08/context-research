"""Run the rule-change benchmark cells and summarize them. No paid calls without --live.

python3 bench/run_bench.py --config configs/bench-v1.json --manifest <cases.json> --output results/bench-001
python3 bench/run_bench.py ... --live
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
from typing import Any, Dict, List, Optional

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

from bench import session as SE  # noqa: E402
from bench.cases import load_manifest  # noqa: E402
from relay import save  # noqa: E402

REPO = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").exists())
PARQUET = "swe-rebench-v2/data/train-00000-of-00001.parquet"
HISTORY_DIR = "vibemem/history"
OUTCOMES = ("new", "old", "both", "neither")
BY_ID = {SE.cell_id(c): c for c in SE.CELLS}


def check_output_path(output: Path) -> Path:
    """Refuse a path inside the repository unless it is covered by the results/bench-*/ ignore rule."""
    resolved = Path(output).resolve()
    try:
        parts = resolved.relative_to(REPO).parts
    except ValueError:
        return resolved
    if len(parts) >= 4 and parts[:3] == ("studies", "subagent-rule-updates", "results") and parts[3].startswith("bench-"):
        return resolved
    raise SystemExit("Refusing output %s: inside the repository but not under "
                     "studies/subagent-rule-updates/results/bench-*/, which is git-ignored." % resolved)


def select(wanted: Optional[str], known: List[str], what: str) -> List[str]:
    if not wanted:
        return list(known)
    names = [n for n in wanted.split(",") if n]
    bad = [n for n in names if n not in known]
    if bad:
        raise SystemExit("Unknown %s: %s" % (what, ", ".join(bad)))
    return names


def build_plan(config: dict, case_ids: List[str], cell_ids: List[str]) -> List[dict]:
    plan = [{"case_id": c, "cell_id": k, "repetition": r}
            for c in case_ids for k in cell_ids for r in range(config["repetitions"])]
    random.Random(config["order_seed"]).shuffle(plan)
    return plan


def record_dir(model_dir: Path, entry: dict) -> Path:
    return model_dir / "cells" / entry["case_id"] / entry["cell_id"] / ("rep%d" % entry["repetition"])


def load_rule_map(rules_dir: Path, repo: str) -> Dict[str, Any]:
    from bench.rules import load_rules
    return {r.id: r for r in load_rules(rules_dir / ("%s.json" % repo.replace("/", "__")))}


def execute(client: Any, model_dir: Path, plan: List[dict], cases: Dict[str, Any], config: dict, *, rows: dict,
            trajectories: dict, rules_dir: Path, workspace_factory: Any) -> Optional[str]:
    """Run plan entries in order. Returns the stopping reason, or None when the plan completed.

    infra_error and compaction_error records are saved and the run continues. provider_error
    is saved and stops the run, since a failed request may mean budget or billing trouble.
    """
    rule_cache: Dict[str, Any] = {}
    for entry in plan:
        outdir = record_dir(model_dir, entry)
        case = cases[entry["case_id"]]
        if case.repo not in rule_cache:
            rule_cache[case.repo] = load_rule_map(rules_dir, case.repo)
        before = client.summary()["budget_committed_usd"]
        record = SE.run_cell(client, case, BY_ID[entry["cell_id"]], rules=rule_cache[case.repo], rows=rows,
                             trajectories=trajectories, outdir=outdir, config=config, workspace_factory=workspace_factory)
        record["repetition"] = entry["repetition"]
        record["cost_usd"] = client.summary()["budget_committed_usd"] - before
        save(outdir / "record.json", record)
        if record["status"] == "provider_error":
            return "provider_error in %s/%s rep%d: %s" % (entry["case_id"], entry["cell_id"], entry["repetition"],
                                                          record.get("error"))
    return None


def setup_invalid(record: dict) -> bool:
    """True when the placement names a history that never had a non-skipped compaction."""
    if record.get("status") != "finished":
        return False
    placement = record.get("cell", {}).get("placement", "none")
    done = {e.get("history") for e in record.get("compactions", []) if not e.get("skipped")}
    return any(name not in done for name in SE.PLACEMENT_HISTORIES[placement])


DELEGATION_FLAGS = ("u0_delegated", "u2_delegated", "u2_worker_finished")


def delegation_invalid(record: dict) -> bool:
    """True when a finished record's manager never delegated U0 or U2, or the U2 worker did not finish."""
    return record.get("status") == "finished" and not all(record.get(k) is True for k in DELEGATION_FLAGS)


def _empty() -> dict:
    return {"records": 0, "statuses": {}, "setup_invalid": 0, "setup_invalid_records": [],
            "delegation_invalid": 0, "delegation_invalid_records": [], "valid_finished": 0,
            "changed": dict.fromkeys(OUTCOMES, 0), "unchanged": dict.fromkeys(OUTCOMES, 0),
            "headline_passes": 0, "control_passes": 0, "tests_resolved": 0, "cost_usd": 0.0}


def analyze(output: Path) -> dict:
    """Summarize every record.json under output; writes summary.json and tables.md."""
    output = Path(output)
    cells: Dict[str, dict] = {}
    for path in sorted(output.rglob("record.json")):
        record = json.loads(path.read_text())
        cid = SE.cell_id(SE.Cell(**record["cell"]))
        row = cells.setdefault(cid, _empty())
        row["records"] += 1
        status = record.get("status")
        row["statuses"][status] = row["statuses"].get(status, 0) + 1
        row["cost_usd"] += float(record.get("cost_usd") or 0.0)
        try:
            invalid = {"setup_invalid": setup_invalid(record), "delegation_invalid": delegation_invalid(record)}
            if not any(invalid.values()) and status == "finished" and record.get("rules"):
                changed = record["rules"]["changed"]["outcome"]
                unchanged = record["rules"]["unchanged"]["outcome"]
                if changed not in OUTCOMES or unchanged not in OUTCOMES:
                    raise KeyError("outcome")
                passed = int(SE.headline_pass(record))
                control = int(SE.control_pass(record))
                resolved = int(bool((record.get("tests") or {}).get("resolved")))
        except (KeyError, TypeError, AttributeError):
            row["statuses"][status] -= 1
            row["statuses"]["malformed_record"] = row["statuses"].get("malformed_record", 0) + 1
            if not row["statuses"][status]:
                del row["statuses"][status]
            continue
        for kind, flagged in invalid.items():
            if flagged:
                row[kind] += 1
                row[kind + "_records"].append(str(path.parent.relative_to(output)))
        if any(invalid.values()) or status != "finished" or not record.get("rules"):
            continue
        row["valid_finished"] += 1
        row["changed"][changed] += 1
        row["unchanged"][unchanged] += 1
        row["headline_passes"] += passed
        row["control_passes"] += control
        row["tests_resolved"] += resolved
    summary = {"cells": cells, "totals": {"records": sum(c["records"] for c in cells.values()),
                                          "cost_usd": sum(c["cost_usd"] for c in cells.values()),
                                          "statuses": dict(sum((Counter(c["statuses"]) for c in cells.values()), Counter()))}}
    save(output / "summary.json", summary)
    (output / "tables.md").write_text(render_tables(summary))
    return summary


def render_tables(summary: dict) -> str:
    def fmt(counts: dict) -> str:
        return "/".join(str(counts[o]) for o in OUTCOMES)
    lines = ["Outcome counts are new/old/both/neither over valid finished records. "
             "setup_invalid and delegation_invalid records are excluded from them. "
             "The no_change control has no headline; see the control table.", "",
             "| cell | records | statuses | setup_invalid | delegation_invalid | valid | changed | unchanged | headline "
             "| tests | cost USD |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    control = []
    for cid, c in sorted(summary["cells"].items()):
        statuses = ", ".join("%s %d" % (k, v) for k, v in sorted(c["statuses"].items()))
        is_control = cid.startswith("no_change__")
        lines.append("| %s | %d | %s | %d | %d | %d | %s | %s | %s | %d | %.4f |" % (
            cid, c["records"], statuses, c["setup_invalid"], c["delegation_invalid"], c["valid_finished"],
            fmt(c["changed"]), fmt(c["unchanged"]), "n/a" if is_control else str(c["headline_passes"]),
            c["tests_resolved"], c["cost_usd"]))
        if is_control:
            control.append("| %s | %d | %d |" % (cid, c["valid_finished"], c["control_passes"]))
    if control:
        lines += ["", "No-change control: both rules kept in their original version (changed old, unchanged old).", "",
                  "| cell | valid | both old |", "|---|---|---|"] + control
    return "\n".join(lines) + "\n"


def freeze(model_dir: Path, config: dict, selected: dict, config_path: Path, plan: List[dict]) -> None:
    source = model_dir / "source"
    source.mkdir(parents=True, exist_ok=True)
    for path in sorted(STUDY.glob("bench/*.py")) + [STUDY / n for n in ("worker.py", "relay.py", "compaction.py",
                                                                           "pi_compaction.py", "provider.py", "harness.py")]:
        dest = source / path.relative_to(STUDY)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    shutil.copyfile(config_path, source / "config.json")
    save(model_dir / "manifest.json", {
        "started_utc": datetime.now(timezone.utc).isoformat(), "config": config, "selected_model": selected,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True),
        "manager_system": SE.MANAGER_SYSTEM, "worker_system": SE.BENCH_WORKER_SYSTEM, "planned_runs": len(plan)})


def live_workspace_factory():
    from bench.container import ContainerWorkspace, DockerRunner
    return lambda row, d: ContainerWorkspace(row.image_name, DockerRunner(), workdir=row.workdir,
                                             event_log=d / "tool_events.jsonl")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=STUDY / "configs/bench-v1.json")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cells", help="Comma list of cell ids as bench.session names them")
    parser.add_argument("--cases", help="Comma list of case ids")
    parser.add_argument("--model-index", type=int, default=0)
    parser.add_argument("--live", action="store_true", help="Authorize paid provider calls")
    args = parser.parse_args(argv)
    root = check_output_path(args.output)
    config = json.loads(args.config.read_text())
    cases = {c.case_id: c for c in load_manifest(args.manifest)}
    plan = build_plan(config, select(args.cases, sorted(cases), "case ids"), select(args.cells, sorted(BY_ID), "cell ids"))
    if not args.live:
        save(root / "plan.json", {"order_seed": config["order_seed"], "entries": plan})
        print("PLAN_WRITTEN entries=%d path=%s (no model calls made)" % (len(plan), root / "plan.json"))
        return 0
    selected = config["models"][args.model_index]
    model_dir = root / ("model-%d" % args.model_index)
    if model_dir.exists():
        raise SystemExit("Refusing existing output directory %s" % model_dir)
    # Everything that can fail at setup runs before any directory, lock, or client exists.
    data_root = Path(config["data_root"]).expanduser()
    for path in (data_root / PARQUET, data_root / HISTORY_DIR):
        if not path.exists():
            raise SystemExit("Missing data path: %s" % path)
    rules_dir = STUDY / "bench/rules"
    try:
        for repo in sorted({cases[e["case_id"]].repo for e in plan}):
            load_rule_map(rules_dir, repo)
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit("Cannot load rules: %s: %s" % (type(exc).__name__, exc))
    from bench.sources import load_rows, trajectory_index
    from provider import OpenRouterClient, load_key
    rows = {r.instance_id: r for r in load_rows(data_root / PARQUET)}
    trajectories = trajectory_index(data_root / HISTORY_DIR)
    load_key()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if model_dir.exists():
            raise SystemExit("Refusing existing output directory %s" % model_dir)
        model_dir.mkdir()
        try:
            freeze(model_dir, config, selected, args.config, plan)
            save(model_dir / "plan.json", {"order_seed": config["order_seed"], "entries": plan})
        except BaseException:
            shutil.rmtree(model_dir, ignore_errors=True)
            raise
        client = OpenRouterClient(model_dir, model=selected["id"], provider_name=selected["provider"],
                                  budget_usd=selected["budget_usd"], max_calls=config["max_provider_calls"],
                                  temperature=config["temperature"], max_tokens=config["max_output_tokens"],
                                  reasoning_effort=config["reasoning_effort"])
        failure = None
        try:
            failure = execute(client, model_dir, plan, cases, config, rows=rows, trajectories=trajectories,
                              rules_dir=rules_dir, workspace_factory=live_workspace_factory())
        finally:
            save(model_dir / "provider_summary.json", client.summary())
            analyze(model_dir)
        print("RUN_COMPLETE output=%s error=%s" % (model_dir, failure), flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
