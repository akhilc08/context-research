from __future__ import annotations

import unittest

from bench.container import ContainerWorkspace
from bench.evaluate import parse_log, score_tests, test_patch_paths
from bench.sources import TaskRow

LOG = """============ test session starts ============
PASSED tests/test_a.py::test_one
FAILED tests/test_a.py::test_two - AssertionError: nope
SKIPPED tests/test_b.py::test_three
ERROR tests/test_b.py::test_four
PASSED tests/test_b.py::test_five
"""

PATCH = ("diff --git a/tests/test_a.py b/tests/test_a.py\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1 +1 @@\n-x\n+y\n"
         "diff --git a/tests/new_test.py b/tests/new_test.py\nnew file mode 100644\n--- /dev/null\n+++ b/tests/new_test.py\n@@ -0,0 +1 @@\n+z\n")


class FakeRunner:
    def __init__(self, apply_code=0, log=LOG):
        self.calls, self.apply_code, self.log = [], apply_code, log

    def run(self, args, *, input=None, timeout, max_output=None):
        self.calls.append({"args": list(args), "input": input, "max_output": max_output})
        if args[:2] == ["docker", "run"]:
            return 0, "cid\n", ""
        if "apply" in args:
            return self.apply_code, "", "error: patch failed" if self.apply_code else ""
        return 0, self.log, ""


def row(f2p, p2p):
    return TaskRow("i", "o/r", "abc", "", "img", "python", 0, "pytest -rA", "parse_log_pytest",
                   tuple(f2p), tuple(p2p), "", PATCH, "MIT", "/r")


def ws_for(runner):
    ws = ContainerWorkspace("img", runner, workdir="/r")
    ws.start()
    return ws


class EvaluateTest(unittest.TestCase):
    def test_parse_log(self):
        self.assertEqual(parse_log("parse_log_pytest", LOG), {
            "tests/test_a.py::test_one": "PASSED", "tests/test_a.py::test_two": "FAILED",
            "tests/test_b.py::test_three": "SKIPPED", "tests/test_b.py::test_four": "FAILED",
            "tests/test_b.py::test_five": "PASSED"})

    def test_unknown_parser(self):
        with self.assertRaises(ValueError):
            parse_log("parse_log_nope", LOG)

    def test_resolved_only_when_all_pass(self):
        r = FakeRunner()
        ok = score_tests(ws_for(r), row(["tests/test_a.py::test_one"], ["tests/test_b.py::test_five"]))
        self.assertTrue(ok["resolved"])
        self.assertFalse(ok["test_patch_conflict"])
        self.assertEqual(r.calls[1]["input"], PATCH)
        self.assertEqual(r.calls[2]["max_output"], 2000000)
        bad = score_tests(ws_for(FakeRunner()), row(["tests/test_a.py::test_one"], ["tests/test_a.py::test_two"]))
        self.assertFalse(bad["resolved"])
        self.assertEqual(bad["pass_to_pass"], {"tests/test_a.py::test_two": "FAILED"})
        missing = score_tests(ws_for(FakeRunner()), row(["tests/nothing"], []))
        self.assertFalse(missing["resolved"])

    def test_apply_conflict(self):
        r = FakeRunner(apply_code=1)
        res = score_tests(ws_for(r), row(["a"], []))
        self.assertTrue(res["test_patch_conflict"])
        self.assertFalse(res["resolved"])
        self.assertEqual(len(r.calls), 2)

    def test_patch_paths(self):
        self.assertEqual(test_patch_paths(PATCH), {"tests/test_a.py", "tests/new_test.py"})


if __name__ == "__main__":
    unittest.main()
