"""Task rows from SWE-rebench V2 and the VibeMemBench trajectory index."""
from __future__ import annotations

import calendar
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pyarrow.parquet as pq


@dataclass(frozen=True)
class TaskRow:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    image_name: str
    language: str
    created_at: int
    test_cmd: str
    log_parser: str
    fail_to_pass: Tuple[str, ...]
    pass_to_pass: Tuple[str, ...]
    patch: str
    test_patch: str
    license: str


_COLUMNS = [
    "instance_id", "repo", "base_commit", "problem_statement", "image_name",
    "language", "created_at", "install_config", "FAIL_TO_PASS", "PASS_TO_PASS",
    "patch", "test_patch", "license",
]


def _epoch(value) -> int:
    if isinstance(value, int):
        return value
    if hasattr(value, "timestamp"):
        return int(calendar.timegm(value.utctimetuple()))
    return int(calendar.timegm(time.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")))


def load_rows(parquet: Path, *, language: Optional[str] = "python") -> List[TaskRow]:
    table = pq.read_table(str(parquet), columns=_COLUMNS)
    rows = []
    for r in table.to_pylist():
        if language is not None and r["language"] != language:
            continue
        cfg = r["install_config"] or {}
        rows.append(TaskRow(
            instance_id=r["instance_id"],
            repo=r["repo"],
            base_commit=r["base_commit"],
            problem_statement=r["problem_statement"] or "",
            image_name=r["image_name"] or "",
            language=r["language"],
            created_at=_epoch(r["created_at"]),
            test_cmd=cfg.get("test_cmd") or "",
            log_parser=cfg.get("log_parser") or "",
            fail_to_pass=tuple(r["FAIL_TO_PASS"] or ()),
            pass_to_pass=tuple(r["PASS_TO_PASS"] or ()),
            patch=r["patch"] or "",
            test_patch=r["test_patch"] or "",
            license=r["license"] or "",
        ))
    return rows


def issue_number(instance_id: str) -> int:
    match = re.search(r"-(\d+)$", instance_id)
    if not match:
        raise ValueError("no trailing issue number: %r" % instance_id)
    return int(match.group(1))


def trajectory_index(history_root: Path) -> Dict[str, Dict[str, Path]]:
    """Map repo ("owner/repo") to instance id to trajectory path.

    Layout: <language>/<owner>__<repo>/<instance_id>/<instance_id>.traj.json
    """
    index: Dict[str, Dict[str, Path]] = {}
    for traj in sorted(Path(history_root).glob("*/*/*/*.traj.json")):
        instance_id = traj.parent.name
        if traj.name != instance_id + ".traj.json":
            continue
        repo = traj.parent.parent.name.replace("__", "/", 1)
        index.setdefault(repo, {})[instance_id] = traj
    return index
