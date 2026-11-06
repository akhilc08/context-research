"""Screen the benchmark's rules at evaluation time. No paid calls without --live.

One worker, no manager, no compaction, on each case's first task. Arms: "none" (problem
statement only), "original" (original wording, then the problem statement) and "changed"
(changed wording, then the problem statement). A rule passes when the none arm rarely matches
either version and each told arm follows its version.

python3 bench/screen_bench.py --config configs/bench-v1.json --manifest <cases.json> --output results/bench-screen-001
python3 bench/screen_bench.py ... --live
"""
from __future__ import annotations

import argparse
import fcntl
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

import worker as W  # noqa: E402
from bench import run_bench as RB  # noqa: E402
from bench import session as SE  # noqa: E402
from bench.cases import load_manifest  # noqa: E402
from bench.container import TOOLS as WORKER_TOOLS  # noqa: E402
from bench.evaluate import test_patch_paths  # noqa: E402
from bench.rules import classify  # noqa: E402
from bench.sources import issue_number  # noqa: E402
from relay import save  # noqa: E402
from screen import MAX_DEFAULT_COMPLIANCE, MIN_TOLD_COMPLIANCE  # noqa: E402

DEFAULT_REPETITIONS = 10
# Provider and infrastructure failures leave a run unfinished; everything else was scored.
UNFINISHED_STATUSES = ("provider_error", "infra_error")
# Which classify outcome counts as following the arm's wording.
FOLLOW_OUTCOME = {"original": "old", "changed": "new"}


def arms() -> List[str]:
    return ["none", "original", "changed"]


def first_message(arm: str, rule: Any, problem: str) -> str:
    if arm == "none":
        return "Task: %s" % problem
    wording = rule.original if arm == "original" else rule.changed
    return "Project rule from the user: %s\n\nTask: %s" % (wording, problem)


def build_plan(config: dict, cases: Dict[str, Any], case_ids: List[str]) -> List[dict]:
    """One entry per (repo, rule id, arm, repetition). Cases of a repo share the first task, so the
    first case id in sorted order represents the repo."""
    seen = set()
    plan: List[dict] = []
    reps = int(config.get("screen_repetitions", DEFAULT_REPETITIONS))
    for cid in sorted(case_ids):
        case = cases[cid]
        for rule_id in sorted({case.changed_rule, case.unchanged_rule}):
            if (case.repo, rule_id) in seen:
                continue
            seen.add((case.repo, rule_id))
            plan += [{"case_id": cid, "repo": case.repo, "rule_id": rule_id, "arm": a, "repetition": r}
                     for a in arms() for r in range(reps)]
    random.Random(config["order_seed"]).shuffle(plan)
    return plan


def record_dir(model_dir: Path, entry: dict) -> Path:
    return model_dir / "runs" / entry["repo"].replace("/", "__") / entry["rule_id"] / entry["arm"] / (
        "rep%d" % entry["repetition"])


def run_one(client: Any, entry: dict, case: Any, rule: Any, row: Any, *, outdir: Path, config: dict,
            workspace_factory: Any) -> dict:
    """One worker on the case's first task. Never raises; failures are recorded in the status."""
    recorder = SE.RecordingClient(client)
    message = first_message(entry["arm"], rule, row.problem_statement)
    record: Dict[str, Any] = {k: entry[k] for k in ("case_id", "repo", "rule_id", "arm", "repetition")}
    record.update({"status": "running", "first_message": message, "worker_system": SE.BENCH_WORKER_SYSTEM})
    try:
        ws = workspace_factory(row, outdir / "task1")
        try:
            ws.start()
            result = W.run_agent(recorder, SE.BENCH_WORKER_SYSTEM, [], message, tools=WORKER_TOOLS,
                                 execute=lambda n, a, i: ws.execute(n, a, call_index=i),
                                 tag="screen/%s/%s/%s/rep%d" % (entry["repo"], entry["rule_id"], entry["arm"],
                                                                entry["repetition"]),
                                 max_calls=config["max_worker_calls"])
            record.update({"status": result["status"], "error": result["error"], "calls": recorder.calls,
                           "worker_history": result["history"]})
            if result["status"] != "provider_error":
                changes = ws.changes(row.base_commit, exclude=frozenset(test_patch_paths(row.test_patch)))
                record.update(classify(rule, changes, issue=issue_number(row.instance_id)))
                record["changed_paths"] = sorted(changes)
        finally:
            ws.stop()
    except Exception as exc:  # Containers, git: record it unscored and let the runner decide.
        for key in ("outcome", "old", "new", "changed_paths"):
            record.pop(key, None)
        record.update({"status": "infra_error", "error": "%s: %s" % (type(exc).__name__, exc)})
    if record["status"] in UNFINISHED_STATUSES:
        for key in ("outcome", "old", "new", "changed_paths"):
            record.pop(key, None)
    return record


def execute(client: Any, model_dir: Path, plan: List[dict], cases: Dict[str, Any], config: dict, *, rows: dict,
            rules_dir: Path, workspace_factory: Any) -> Optional[str]:
    """Run plan entries in order. Returns the stopping reason, or None when the plan completed.

    infra_error is saved and the run continues. provider_error is saved and stops the run."""
    rule_cache: Dict[str, Any] = {}
    for entry in plan:
        case = cases[entry["case_id"]]
        if case.repo not in rule_cache:
            rule_cache[case.repo] = RB.load_rule_map(rules_dir, case.repo)
        outdir = record_dir(model_dir, entry)
        before = client.summary()["budget_committed_usd"]
        record = run_one(client, entry, case, rule_cache[case.repo][entry["rule_id"]], rows[case.first],
                         outdir=outdir, config=config, workspace_factory=workspace_factory)
        record["cost_usd"] = client.summary()["budget_committed_usd"] - before
        save(outdir / "record.json", record)
        if record["status"] == "provider_error":
            return "provider_error in %s/%s/%s rep%d: %s" % (entry["repo"], entry["rule_id"], entry["arm"],
                                                             entry["repetition"], record.get("error"))
    return None


def _split(records: List[dict]) -> Dict[str, Dict[str, List[dict]]]:
    by_rule: Dict[str, Dict[str, List[dict]]] = {}
    for r in records:
        by_rule.setdefault(r["rule_id"], {a: [] for a in arms()})[r["arm"]].append(r)
    return by_rule


def _finished(runs: List[dict]) -> List[dict]:
    return [r for r in runs if r.get("status") not in UNFINISHED_STATUSES and "outcome" in r]


def _count(runs: List[dict], match: Any) -> int:
    return sum(1 for r in runs if match(r["outcome"]))


def screen_verdicts(records: List[dict]) -> Dict[str, dict]:
    """Rule id to {"passed", "none_match_rate", "original_follow_rate", "changed_follow_rate"}.

    Rates are over finished runs only; an arm with no finished runs has rate 0.0 and fails the rule.
    Passing needs none_match_rate <= MAX_DEFAULT_COMPLIANCE and each follow rate >= MIN_TOLD_COMPLIANCE."""
    verdicts: Dict[str, dict] = {}
    for rule_id, arm_runs in _split(records).items():
        done = {a: _finished(arm_runs[a]) for a in arms()}
        n = {a: len(done[a]) for a in done}
        matches = _count(done["none"], lambda o: o != "neither")
        follows = {a: _count(done[a], lambda o, a=a: o == FOLLOW_OUTCOME[a]) for a in FOLLOW_OUTCOME}
        rate = lambda k, d: (k / d) if d else 0.0  # noqa: E731
        # The small tolerance keeps exact boundaries (2 of 10, 9 of 10) free of float error.
        passed = (all(n[a] > 0 for a in done)
                  and rate(matches, n["none"]) <= MAX_DEFAULT_COMPLIANCE + 1e-12
                  and all(rate(follows[a], n[a]) >= MIN_TOLD_COMPLIANCE - 1e-12 for a in FOLLOW_OUTCOME))
        verdicts[rule_id] = {"passed": passed, "none_match_rate": rate(matches, n["none"]),
                             "original_follow_rate": rate(follows["original"], n["original"]),
                             "changed_follow_rate": rate(follows["changed"], n["changed"])}
    return verdicts


def run_counts(records: List[dict]) -> Dict[str, dict]:
    """Per rule and arm: finished runs and unfinished runs by status."""
    out: Dict[str, dict] = {}
    for rule_id, arm_runs in _split(records).items():
        out[rule_id] = {}
        for a, runs in arm_runs.items():
            done = _finished(runs)
            unfinished: Dict[str, int] = {}
            for r in runs:
                if not any(r is d for d in done):
                    status = r.get("status", "unknown")
                    unfinished[status] = unfinished.get(status, 0) + 1
            out[rule_id][a] = {"finished": len(done), "unfinished": unfinished}
    return out


def analyze(output: Path) -> dict:
    """Write screening.json (verdicts, counts, per-run records) for every record.json under output."""
    output = Path(output)
    records = [json.loads(p.read_text()) for p in sorted(output.rglob("record.json"))]
    counts = run_counts(records)
    verdicts = {rid: {**v, "runs": counts[rid]} for rid, v in screen_verdicts(records).items()}
    runs = [{k: v for k, v in r.items() if k not in ("worker_history", "calls", "worker_system")} for r in records]
    result = {"verdicts": verdicts, "runs": runs,
              "criteria": {"max_none_match_rate": MAX_DEFAULT_COMPLIANCE, "min_follow_rate": MIN_TOLD_COMPLIANCE}}
    save(output / "screening.json", result)
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=STUDY / "configs/bench-v1.json")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", help="Comma list of case ids")
    parser.add_argument("--model-index", type=int, default=0)
    parser.add_argument("--live", action="store_true", help="Authorize paid provider calls")
    args = parser.parse_args(argv)
    root = RB.check_output_path(args.output)
    config = json.loads(args.config.read_text())
    cases = {c.case_id: c for c in load_manifest(args.manifest)}
    plan = build_plan(config, cases, RB.select(args.cases, sorted(cases), "case ids"))
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
    for path in (data_root / RB.PARQUET, data_root / RB.HISTORY_DIR):
        if not path.exists():
            raise SystemExit("Missing data path: %s" % path)
    rules_dir = STUDY / "bench/rules"
    try:
        for repo in sorted({e["repo"] for e in plan}):
            rule_map = RB.load_rule_map(rules_dir, repo)
            for rid in {e["rule_id"] for e in plan if e["repo"] == repo}:
                rule_map[rid]
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit("Cannot load rules: %s: %s" % (type(exc).__name__, exc))
    from bench.sources import load_rows
    from provider import OpenRouterClient, load_key
    rows = {r.instance_id: r for r in load_rows(data_root / RB.PARQUET)}
    missing = sorted({cases[e["case_id"]].first for e in plan} - set(rows))
    if missing:
        raise SystemExit("Missing task rows: %s" % ", ".join(missing))
    load_key()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if model_dir.exists():
            raise SystemExit("Refusing existing output directory %s" % model_dir)
        model_dir.mkdir()
        try:
            RB.freeze(model_dir, config, selected, args.config, plan)
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
            failure = execute(client, model_dir, plan, cases, config, rows=rows, rules_dir=rules_dir,
                              workspace_factory=RB.live_workspace_factory())
        finally:
            save(model_dir / "provider_summary.json", client.summary())
            analyze(model_dir)
        print("SCREEN_COMPLETE output=%s error=%s" % (model_dir, failure), flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
