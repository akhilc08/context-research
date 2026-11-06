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


def reset_test_patch_files(ws: ContainerWorkspace, row: TaskRow) -> dict:
    """Put every file the test patch touches back to base: restore those that exist at base_commit
    and delete the rest, so worker edits to test files cannot block the test patch."""
    paths = sorted(test_patch_paths(row.test_patch))
    if not paths:
        return {"restored": [], "removed": []}
    code, out, err = ws._git("ls-tree", "-r", "--name-only", "-z", row.base_commit, "--", *paths)
    if code != 0:
        raise RuntimeError("git ls-tree failed: " + err.strip()[-300:])
    at_base = set(out.split("\0")) & set(paths)
    restored = [p for p in paths if p in at_base]
    removed = [p for p in paths if p not in at_base]
    if restored:
        code, _, err = ws._git("checkout", row.base_commit, "--", *restored)
        if code != 0:
            raise RuntimeError("git checkout of test files failed: " + err.strip()[-300:])
    if removed:
        code, _, err = ws._exec(["rm", "-f", "--"] + removed, cwd=ws.workdir, timeout=60, max_output=10000)
        if code != 0:
            raise RuntimeError("removing test-patch files failed: " + err.strip()[-300:])
    return {"restored": restored, "removed": removed}


def score_tests(ws: ContainerWorkspace, row: TaskRow, *, reset_test_files: bool = True) -> dict:
    """Apply the test patch and run the tests. With reset_test_files (the default when scoring a
    worker), test-patch files are first reset to base. Validation's gold run turns it off so a gold
    patch that edits test files still shows up as a conflict."""
    reset = reset_test_patch_files(ws, row) if reset_test_files else None
    code, _, err = ws._exec(["git", "apply", "-"], input=row.test_patch, interactive=True,
                            cwd=ws.workdir, timeout=120, max_output=10000)
    if code != 0:
        return {"resolved": False, "test_patch_conflict": True, "test_patch_apply_error": err.strip()[-500:],
                "test_patch_reset": reset, "fail_to_pass": {}, "pass_to_pass": {}}
    code, out, err = ws._exec(["bash", "-lc", row.test_cmd], cwd=ws.workdir, timeout=TEST_TIMEOUT,
                              max_output=TEST_OUTPUT_CAP)
    statuses = parse_log(row.log_parser, out + "\n" + err)
    f2p = {t: statuses.get(t, MISSING) for t in row.fail_to_pass}
    p2p = {t: statuses.get(t, MISSING) for t in row.pass_to_pass}
    resolved = all(s == "PASSED" for s in list(f2p.values()) + list(p2p.values()))
    return {"resolved": resolved, "test_patch_conflict": False, "test_patch_reset": reset,
            "fail_to_pass": f2p, "pass_to_pass": p2p}
