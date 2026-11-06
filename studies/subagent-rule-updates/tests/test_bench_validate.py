from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench import validate
from bench.cases import Case, save_manifest
from bench.sources import TaskRow

PASS_LOG = "PASSED tests/t.py::f2p\nPASSED tests/t.py::p2p\n"
FAIL_LOG = "FAILED tests/t.py::f2p - boom\nPASSED tests/t.py::p2p\n"
TEST_PATCH = "diff --git a/tests/t.py b/tests/t.py\n"
GOLD = "diff --git a/src/a.py b/src/a.py\n"


def make_row(iid="o__r-1"):
    return TaskRow(iid, "o/r", "abc", "SECRET problem", "img:" + iid, "python", 0, "pytest -rA",
                   "parse_log_pytest", ("tests/t.py::f2p",), ("tests/t.py::p2p",), GOLD, TEST_PATCH,
                   "MIT", "/r")


class FakeRunner:
    """Gold applied in a container makes the tests pass; base_log is what an unpatched run prints."""

    def __init__(self, base_log=FAIL_LOG, gold_log=PASS_LOG, gold_apply=0, has_timeout=True):
        self.calls, self.base_log, self.gold_log = [], base_log, gold_log
        self.gold_apply, self.has_timeout = gold_apply, has_timeout
        self.runs, self.removed, self.gold = 0, [], set()

    def run(self, args, *, input=None, timeout, max_output=None):
        self.calls.append(list(args))
        if args[:2] == ["docker", "run"]:
            self.runs += 1
            return 0, "cid%d\n" % self.runs, ""
        if args[:3] == ["docker", "rm", "-f"]:
            self.removed.append(args[3])
            return 0, "", ""
        cid = None
        if args[:2] == ["docker", "exec"]:
            rest = args[2:]
            while rest[0] in ("-i", "-w"):
                rest = rest[2:] if rest[0] == "-w" else rest[1:]
            cid = rest[0]
        if "command -v timeout" in " ".join(args):
            return (0, "/usr/bin/timeout\n", "") if self.has_timeout else (1, "", "")
        if "apply" in args:
            if input == GOLD:
                if self.gold_apply:
                    return self.gold_apply, "", "error: patch failed"
                self.gold.add(cid)
            return 0, "", ""
        if "bash" in args:
            return 0, self.gold_log if cid in self.gold else self.base_log, ""
        return 0, "", ""


class ValidateTaskTest(unittest.TestCase):
    def test_valid(self):
        runner = FakeRunner()
        res = validate.validate_task(make_row(), runner, "/r")
        self.assertTrue(res["valid"])
        self.assertTrue(res["gold_resolved"])
        self.assertTrue(res["base_fail_to_pass_failing"])
        self.assertTrue(res["has_timeout"])
        self.assertEqual(res["instance_id"], "o__r-1")
        self.assertEqual(sorted(runner.removed), ["cid1", "cid2"])

    def test_f2p_already_passing_on_base(self):
        res = validate.validate_task(make_row(), FakeRunner(base_log=PASS_LOG), "/r")
        self.assertFalse(res["valid"])
        self.assertFalse(res["base_fail_to_pass_failing"])
        self.assertTrue(res["gold_resolved"])

    def test_gold_does_not_resolve(self):
        res = validate.validate_task(make_row(), FakeRunner(gold_log=FAIL_LOG), "/r")
        self.assertFalse(res["valid"])
        self.assertFalse(res["gold_resolved"])
        self.assertTrue(res["base_fail_to_pass_failing"])

    def test_gold_patch_fails_to_apply(self):
        runner = FakeRunner(gold_apply=1)
        res = validate.validate_task(make_row(), runner, "/r")
        self.assertFalse(res["valid"])
        self.assertFalse(res["gold_resolved"])
        self.assertIn("gold patch", res["reason"])
        self.assertEqual(len(runner.removed), 2)

    def test_missing_timeout_invalid(self):
        res = validate.validate_task(make_row(), FakeRunner(has_timeout=False), "/r")
        self.assertFalse(res["valid"])
        self.assertFalse(res["has_timeout"])
        self.assertIn("timeout", res["reason"])

    def test_error_is_recorded_not_raised(self):
        class Boom(FakeRunner):
            def run(self, args, **kw):
                if args[:2] == ["docker", "run"]:
                    return 1, "", "no such image"
                return super().run(args, **kw)
        res = validate.validate_task(make_row(), Boom(), "/r")
        self.assertFalse(res["valid"])
        self.assertIn("no such image", res["error"])


class CliTest(unittest.TestCase):
    def test_validate_manifest_dedups_and_writes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cases = [Case("c1", "o/r", "o__r-1", "o__r-2", (), "a", "b"),
                     Case("c2", "o/r", "o__r-2", "o__r-3", (), "a", "b")]
            save_manifest(cases, d / "m.json")
            rows = {i: make_row(i) for i in ("o__r-1", "o__r-2", "o__r-3")}
            runner = FakeRunner(base_log=PASS_LOG)  # everything invalid
            out = d / "out"
            summary = validate.validate_manifest(cases, rows, out, runner)
            self.assertEqual(sorted(summary["tasks"]), ["o__r-1", "o__r-2", "o__r-3"])
            self.assertEqual(summary["valid_ids"], [])
            self.assertTrue((out / "o__r-2.json").exists())
            text = (out / "validation.json").read_text()
            self.assertNotIn("SECRET", text)
            self.assertNotIn("tests/t.py", text)
            self.assertEqual(json.loads(text)["valid_ids"], [])

    def test_missing_row_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            cases = [Case("c1", "o/r", "x-1", "x-2", (), "a", "b")]
            summary = validate.validate_manifest(cases, {}, Path(d) / "o", FakeRunner())
            self.assertFalse(summary["tasks"]["x-1"]["valid"])
            self.assertIn("error", summary["tasks"]["x-1"])


if __name__ == "__main__":
    unittest.main()
