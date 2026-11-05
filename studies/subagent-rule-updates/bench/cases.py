"""Benchmark cases: two tasks from one repository plus earlier trajectories as history."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import compaction as C

from bench.history import load_trajectory, to_worker_messages
from bench.rules import RuleSpec
from bench.sources import TaskRow, issue_number

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
                rules: Dict[str, List[RuleSpec]], *, history_chars: int, seed: int) -> List[Case]:
    """Two cases per qualifying repository, one per changed rule.

    seed does not currently change any outcome: every ordering is fully
    determined by (created_at, issue number, instance id). It is accepted so
    callers can fix it in manifests and so later tie-breaks stay reproducible.
    """
    by_repo: Dict[str, List[TaskRow]] = {}
    for row in rows:
        by_repo.setdefault(row.repo, []).append(row)
    cases: List[Case] = []
    for repo in sorted(by_repo):
        repo_rules = rules.get(repo, [])
        tasks = by_repo[repo]
        if len(repo_rules) != 2 or len(tasks) < 2:
            continue
        ordered = sorted(tasks, key=_task_key)
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
    Path(path).write_text(json.dumps({"version": MANIFEST_VERSION, "cases": entries}, indent=2) + "\n")


def load_manifest(path: Path) -> List[Case]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or data.get("version") != MANIFEST_VERSION:
        raise ValueError("unsupported manifest version: %r" %
                         (data.get("version") if isinstance(data, dict) else None))
    return [Case(**{**e, "history": tuple(e["history"])}) for e in data["cases"]]
