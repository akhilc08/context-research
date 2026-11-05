"""Score a worker's final container state against a task's tests."""
from __future__ import annotations

import re
from typing import Dict, Set

from bench.container import ContainerWorkspace
from bench.sources import TaskRow
from bench.vendor.log_parsers import parse_log_pytest

PARSERS = {"parse_log_pytest": parse_log_pytest}
TEST_TIMEOUT = 1800
TEST_OUTPUT_CAP = 2000000
MISSING = "MISSING"
_DIFF_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$", re.M)


def parse_log(log_parser: str, output: str) -> Dict[str, str]:
    """Test ID to PASSED, FAILED, or SKIPPED. ERROR counts as FAILED."""
    parser = PARSERS.get(log_parser)
    if parser is None:
        raise ValueError("Unsupported log parser: %r" % (log_parser,))
    return {k: ("FAILED" if v == "ERROR" else str(v.value if hasattr(v, "value") else v))
            for k, v in parser(output).items()}


def test_patch_paths(test_patch: str) -> Set[str]:
    paths: Set[str] = set()
    for old, new in _DIFF_HEADER.findall(test_patch):
        paths.update((old, new))
    return paths


def score_tests(ws: ContainerWorkspace, row: TaskRow) -> dict:
    code, _, _ = ws._exec(["git", "apply", "-"], input=row.test_patch, interactive=True,
                          cwd=ws.workdir, timeout=120, max_output=10000)
    if code != 0:
        return {"resolved": False, "test_patch_conflict": True, "fail_to_pass": {}, "pass_to_pass": {}}
    code, out, err = ws._exec(["bash", "-lc", row.test_cmd], cwd=ws.workdir, timeout=TEST_TIMEOUT,
                              max_output=TEST_OUTPUT_CAP)
    statuses = parse_log(row.log_parser, out + "\n" + err)
    f2p = {t: statuses.get(t, MISSING) for t in row.fail_to_pass}
    p2p = {t: statuses.get(t, MISSING) for t in row.pass_to_pass}
    resolved = all(s == "PASSED" for s in list(f2p.values()) + list(p2p.values()))
    return {"resolved": resolved, "test_patch_conflict": False, "fail_to_pass": f2p, "pass_to_pass": p2p}
