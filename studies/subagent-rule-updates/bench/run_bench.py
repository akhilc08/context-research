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
MAX_CONSECUTIVE_UNFINISHED = 3


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


class FailureStreak:
    """Counts statuses and stops a run after MAX_CONSECUTIVE_UNFINISHED unfinished records in a row."""

    def __init__(self):
        self.counts: Counter = Counter()
        self.streak = 0

    def add(self, status: str) -> Optional[str]:
        self.counts[status] += 1
        self.streak = 0 if status == "finished" else self.streak + 1
        if self.streak >= MAX_CONSECUTIVE_UNFINISHED:
            return "%d consecutive unfinished records (last: %s)" % (self.streak, status)
        return None

    def report(self) -> None:
        print("STATUS_COUNTS " + " ".join("%s=%d" % kv for kv in sorted(self.counts.items())), flush=True)


def execute(client: Any, model_dir: Path, plan: List[dict], cases: Dict[str, Any], config: dict, *, rows: dict,
            trajectories: dict, rules_dir: Path, workspace_factory: Any) -> Optional[str]:
    """Run plan entries in order. Returns the stopping reason, or None when the plan completed.

    infra_error and compaction_error records are saved and the run continues. provider_error
    is saved and stops the run, since a failed request may mean budget or billing trouble. Three
    unfinished records in a row, of any status, also stop it. Status counts are printed at the end.
    """
    rule_cache: Dict[str, Any] = {}
    streak = FailureStreak()
    try:
        for entry in plan:
            outdir = record_dir(model_dir, entry)
            case = cases[entry["case_id"]]
            if case.repo not in rule_cache:
                rule_cache[case.repo] = load_rule_map(rules_dir, case.repo)
            before = client.summary()["budget_committed_usd"]
            record = SE.run_cell(client, case, BY_ID[entry["cell_id"]], rules=rule_cache[case.repo], rows=rows,
                                 trajectories=trajectories, outdir=outdir, config=config,
                                 workspace_factory=workspace_factory)
            record["repetition"] = entry["repetition"]
            record["cost_usd"] = client.summary()["budget_committed_usd"] - before
            save(outdir / "record.json", record)
            where = "%s/%s rep%d" % (entry["case_id"], entry["cell_id"], entry["repetition"])
            stop = streak.add(record["status"])
            if record["status"] == "provider_error":
                return "provider_error in %s: %s" % (where, record.get("error"))
            if stop:
                return "%s, ending at %s" % (stop, where)
        return None
    finally:
        streak.report()


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
            "headline_passes": 0, "control_passes": 0, "tests_resolved": 0, "cost_usd": 0.0,
            "by_changed_prior": {}}


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
        # The repository's own files can pull toward one version; analysis reports the headline per prior.
        prior = row["by_changed_prior"].setdefault(record["rules"]["changed"].get("repo_prior", "unknown"),
                                                   {"valid_finished": 0, "headline_passes": 0})
        prior["valid_finished"] += 1
        prior["headline_passes"] += passed
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
    priors = sorted({p for c in summary["cells"].values() for p in c.get("by_changed_prior", {})})
    if priors:
        lines += ["", "Headline passes / valid records, split by the changed rule's repo_prior (which version the "
                  "repository's own files favor).", "",
                  "| cell | " + " | ".join(priors) + " |", "|---|" + "---|" * len(priors)]
        for cid, c in sorted(summary["cells"].items()):
            if cid.startswith("no_change__"):
                continue
            by = c.get("by_changed_prior", {})
            lines.append("| %s | %s |" % (cid, " | ".join(
                "%d/%d" % (by[p]["headline_passes"], by[p]["valid_finished"]) if p in by else "-" for p in priors)))
    if control:
        lines += ["", "No-change control: both rules kept in their original version (changed old, unchanged old).", "",
                  "| cell | valid | both old |", "|---|---|---|"] + control
    return "\n".join(lines) + "\n"


def freeze(model_dir: Path, config: dict, selected: dict, config_path: Path, plan: List[dict],
           gates: Optional[dict] = None) -> None:
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
        "manager_system": SE.MANAGER_SYSTEM, "worker_system": SE.BENCH_WORKER_SYSTEM, "planned_runs": len(plan),
        "gates": gates or {}})


def live_workspace_factory(network: Optional[str] = "none", scoring_network: Optional[str] = None):
    from bench.container import ContainerWorkspace, DockerRunner
    return lambda row, d: ContainerWorkspace(row.image_name, DockerRunner(), workdir=row.workdir,
                                             event_log=d / "tool_events.jsonl", network=network,
                                             scoring_network=scoring_network)


def config_workspace_factory(config: dict):
    """Agent commands run on container_network; the scorer joins scoring_network first."""
    return live_workspace_factory(config.get("container_network", "none"), config.get("scoring_network"))


def missing_images(images: List[str], runner: Any = None) -> List[str]:
    """Images that `docker image inspect` cannot find locally."""
    if runner is None:
        from bench.container import DockerRunner
        runner = DockerRunner()
    return [i for i in images if runner.run(["docker", "image", "inspect", i], timeout=60, max_output=2000)[0] != 0]


def validated_cases(case_ids: List[str], cases: Dict[str, Any], validation: Path) -> tuple:
    """(kept, dropped) case ids: a case is kept when both of its tasks are in validation.json's valid_ids."""
    try:
        valid = set(json.loads(Path(validation).read_text())["valid_ids"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit("Cannot read validation file %s: %s: %s" % (validation, type(exc).__name__, exc))
    kept = [c for c in case_ids if cases[c].first in valid and cases[c].second in valid]
    return kept, [c for c in case_ids if c not in kept]


def unscreened_rules(plan: List[dict], cases: Dict[str, Any], rules_dir: Path) -> List[str]:
    """repo:rule ids used by the plan whose rule file does not mark them screened. Raises SystemExit on bad rules."""
    out = set()
    try:
        for cid in sorted({e["case_id"] for e in plan}):
            case = cases[cid]
            rule_map = load_rule_map(rules_dir, case.repo)
            for rid in (case.changed_rule, case.unchanged_rule):
                if not rule_map[rid].screened:
                    out.add("%s:%s" % (case.repo, rid))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit("Cannot load rules: %s: %s" % (type(exc).__name__, exc))
    return sorted(out)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=STUDY / "configs/bench-v1.json")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cells", help="Comma list of cell ids as bench.session names them")
    parser.add_argument("--cases", help="Comma list of case ids")
    parser.add_argument("--model-index", type=int, default=0)
    parser.add_argument("--live", action="store_true", help="Authorize paid provider calls")
    parser.add_argument("--validation", type=Path, help="validation.json from bench/validate.py; keeps only valid cases")
    parser.add_argument("--allow-unvalidated", action="store_true", help="Run --live without a validation file")
    parser.add_argument("--allow-unscreened", action="store_true", help="Run --live with rules not marked screened")
    args = parser.parse_args(argv)
    root = check_output_path(args.output)
    config = json.loads(args.config.read_text())
    cases = {c.case_id: c for c in load_manifest(args.manifest)}
    case_ids = select(args.cases, sorted(cases), "case ids")
    dropped: List[str] = []
    if args.validation:
        case_ids, dropped = validated_cases(case_ids, cases, args.validation)
        if not case_ids:
            raise SystemExit("No selected case has both tasks in %s" % args.validation)
    plan = build_plan(config, case_ids, select(args.cells, sorted(BY_ID), "cell ids"))
    if not args.live:
        save(root / "plan.json", {"order_seed": config["order_seed"], "entries": plan})
        print("PLAN_WRITTEN entries=%d path=%s (no model calls made)" % (len(plan), root / "plan.json"))
        return 0
    if not args.validation and not args.allow_unvalidated:
        raise SystemExit("--live needs --validation <validation.json> or --allow-unvalidated")
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
    unscreened = unscreened_rules(plan, cases, rules_dir)
    if unscreened and not args.allow_unscreened:
        raise SystemExit("Unscreened rules: %s. Screen them or pass --allow-unscreened." % ", ".join(unscreened))
    from bench.sources import load_rows, trajectory_index
    from provider import OpenRouterClient, load_key
    rows = {r.instance_id: r for r in load_rows(data_root / PARQUET)}
    tasks = sorted({t for e in plan for t in (cases[e["case_id"]].first, cases[e["case_id"]].second)})
    if set(tasks) - set(rows):
        raise SystemExit("Missing task rows: %s" % ", ".join(sorted(set(tasks) - set(rows))))
    absent = missing_images(sorted({rows[t].image_name for t in tasks}))
    if absent:
        raise SystemExit("Missing Docker images: %s" % ", ".join(absent))
    trajectories = trajectory_index(data_root / HISTORY_DIR)
    gates = {"validation": str(args.validation) if args.validation else None, "dropped_cases": dropped,
             "allow_unvalidated": args.allow_unvalidated, "allow_unscreened": args.allow_unscreened,
             "unscreened_rules": unscreened}
    load_key()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if model_dir.exists():
            raise SystemExit("Refusing existing output directory %s" % model_dir)
        model_dir.mkdir()
        try:
            freeze(model_dir, config, selected, args.config, plan, gates)
            save(model_dir / "plan.json", {"order_seed": config["order_seed"], "entries": plan})
        except BaseException:
            shutil.rmtree(model_dir, ignore_errors=True)
            raise
        client = OpenRouterClient(model_dir, model=selected["id"], provider_name=selected["provider"],
                                  budget_usd=selected["budget_usd"], max_calls=config["max_provider_calls"],
                                  temperature=config["temperature"], max_tokens=config["max_output_tokens"],
                                  reasoning_effort=config["reasoning_effort"],
                                  rate_limit_retries=config.get("rate_limit_retries", 0))
        failure = None
        try:
            failure = execute(client, model_dir, plan, cases, config, rows=rows, trajectories=trajectories,
                              rules_dir=rules_dir,
                              workspace_factory=config_workspace_factory(config))
        finally:
            save(model_dir / "provider_summary.json", client.summary())
            analyze(model_dir)
        print("RUN_COMPLETE output=%s error=%s" % (model_dir, failure), flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
