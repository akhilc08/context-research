r"""Benchmark cases: two tasks from one repository plus earlier trajectories as history.

python3 bench/cases.py --data-root ~/bench-data --output bench/manifests/v1.json \
    --exclude-invalid bench/manifests/validation-v1-network-bridge.json \
    --exclude-invalid bench/manifests/validation-v1-scoring-network.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

import compaction as C  # noqa: E402

from bench.history import load_trajectory, to_worker_messages  # noqa: E402
from bench.rules import RuleSpec, load_rules  # noqa: E402
from bench.sources import TaskRow, issue_number, load_rows, trajectory_index  # noqa: E402

MANIFEST_VERSION = 1


@dataclass(frozen=True)
class Case:
    case_id: str
    repo: str
    first: str
    second: str
    history: Tuple[str, ...]
    changed_rule: str
    unchanged_rule: str


def _task_key(row: TaskRow):
    """Order by created_at; ties break on issue number, then instance id."""
    return (row.created_at, issue_number(row.instance_id), row.instance_id)


def rendered_length(path: Path, instance_id: str) -> int:
    messages = to_worker_messages(load_trajectory(path), call_prefix="h-%s-" % instance_id)
    return len(C.render_history(messages))


def _pick_history(trajs: Dict[str, Path], exclude, below: int, history_chars: int):
    """Newest first (issue number descending) until the rendered length reaches
    history_chars. Returns instance ids in chronological order, or None."""
    candidates = []
    for iid in trajs:
        if iid in exclude:
            continue
        try:
            number = issue_number(iid)
        except ValueError:
            continue
        if number < below:
            candidates.append((number, iid))
    candidates.sort(reverse=True)
    chosen, total = [], 0
    for _, iid in candidates:
        chosen.append(iid)
        total += rendered_length(trajs[iid], iid)
        if total >= history_chars:
            return list(reversed(chosen))
    return None


def build_cases(rows: List[TaskRow], trajectories: Dict[str, Dict[str, Path]],
                rules: Dict[str, List[RuleSpec]], *, history_chars: int, seed: int,
                exclude_tasks: Iterable[str] = ()) -> List[Case]:
    """Two cases per qualifying repository, one per changed rule. The two tasks are the
    repository's latest two, skipping exclude_tasks (tasks that failed validation).

    seed does not currently change any outcome: every ordering is fully
    determined by (created_at, issue number, instance id). It is accepted so
    callers can fix it in manifests and so later tie-breaks stay reproducible.
    """
    exclude_tasks = set(exclude_tasks)
    by_repo: Dict[str, List[TaskRow]] = {}
    for row in rows:
        if row.instance_id in exclude_tasks:
            continue
        by_repo.setdefault(row.repo, []).append(row)
    cases: List[Case] = []
    for repo in sorted(by_repo):
        repo_rules = rules.get(repo, [])
        tasks = by_repo[repo]
        if len(repo_rules) != 2 or len(tasks) < 2:
            continue
        try:
            ordered = sorted(tasks, key=_task_key)
        except ValueError:
            continue  # malformed instance id: skip the repository
        first, second = ordered[-2], ordered[-1]
        history = _pick_history(trajectories.get(repo, {}), {first.instance_id, second.instance_id},
                                issue_number(second.instance_id), history_chars)
        if history is None:
            continue
        for changed, other in ((repo_rules[0], repo_rules[1]), (repo_rules[1], repo_rules[0])):
            cases.append(Case(case_id="%s--%s" % (repo.replace("/", "__"), changed.id), repo=repo,
                              first=first.instance_id, second=second.instance_id,
                              history=tuple(history), changed_rule=changed.id,
                              unchanged_rule=other.id))
    return cases


def save_manifest(cases: List[Case], path: Path) -> None:
    entries = []
    for c in cases:
        d = asdict(c)
        d["history"] = list(c.history)
        entries.append(d)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps({"version": MANIFEST_VERSION, "cases": entries}, indent=2) + "\n")
    temp.replace(path)


def load_manifest(path: Path) -> List[Case]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or data.get("version") != MANIFEST_VERSION:
        raise ValueError("unsupported manifest version: %r" %
                         (data.get("version") if isinstance(data, dict) else None))
    return [Case(**{**e, "history": tuple(e["history"])}) for e in data["cases"]]


def invalid_tasks(validation: Path) -> List[str]:
    """Task ids a validate.py summary marks invalid."""
    tasks = json.loads(Path(validation).read_text())["tasks"]
    return sorted(i for i, t in tasks.items() if not t["valid"])


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=STUDY / "configs/bench-v1.json",
                        help="Read history_chars and order_seed from it")
    parser.add_argument("--rules-dir", type=Path, default=STUDY / "bench" / "rules")
    parser.add_argument("--exclude-invalid", type=Path, action="append", default=[],
                        help="A validation.json whose invalid tasks are skipped (repeatable)")
    args = parser.parse_args(argv)
    from bench.run_bench import HISTORY_DIR, PARQUET
    config = json.loads(args.config.read_text())
    rules: Dict[str, List[RuleSpec]] = {}
    for path in sorted(args.rules_dir.glob("*.json")):
        repo_rules = load_rules(path)
        rules[repo_rules[0].repo] = repo_rules
    rows = [r for r in load_rows(args.data_root.expanduser() / PARQUET) if r.repo in rules]
    exclude = sorted({i for v in args.exclude_invalid for i in invalid_tasks(v)})
    cases = build_cases(rows, trajectory_index(args.data_root.expanduser() / HISTORY_DIR), rules,
                        history_chars=config["history_chars"], seed=config["order_seed"], exclude_tasks=exclude)
    save_manifest(cases, args.output)
    print("%d cases from %d repositories; excluded tasks: %s" %
          (len(cases), len({c.repo for c in cases}), ", ".join(exclude) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
