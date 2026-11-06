from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench import validate
from bench.cases import Case, save_manifest
from bench.evaluate import test_patch_paths
from bench.rules import RuleSpec
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

    def __init__(self, base_log=FAIL_LOG, gold_log=PASS_LOG, gold_apply=0, has_timeout=True,
                 test_conflict=(), has_base=True, ignored=None):
        self.calls, self.base_log, self.gold_log = [], base_log, gold_log
        self.gold_apply, self.has_timeout = gold_apply, has_timeout
        self.runs, self.removed, self.gold = 0, [], set()
        self.test_conflict, self.applies = test_conflict, []
        self.has_base, self.ignored = has_base, ignored

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
            earlier = [i for c, i in self.applies if c == cid]
            self.applies.append((cid, input))
            if any(test_patch_paths(e) & test_patch_paths(input) for e in earlier):
                return 1, "", "error: patch failed"
            if input == TEST_PATCH:
                phase = "gold" if cid in self.gold else "base"
                if phase in self.test_conflict:
                    return 1, "", "error: patch failed"
            if input == GOLD:
                if self.gold_apply:
                    return self.gold_apply, "", "error: patch failed"
                self.gold.add(cid)
            return 0, "", ""
        if "bash" in args:
            return 0, self.gold_log if cid in self.gold else self.base_log, ""
        if "cat-file" in args:
            return (0, "", "") if self.has_base else (128, "", "fatal: Not a valid object name")
        if "check-ignore" in args:
            hits = [p for p in args[args.index("--") + 1:] if p.startswith(self.ignored)] if self.ignored else []
            return (0, "".join(p + "\n" for p in hits), "") if hits else (1, "", "")
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


class ValidateRisksTest(unittest.TestCase):
    def test_gold_applied_before_test_patch(self):
        runner = FakeRunner()
        validate.validate_task(make_row(), runner, "/r")
        gold_cid = next(c for c, i in runner.applies if i == GOLD)
        order = [i for c, i in runner.applies if c == gold_cid]
        self.assertEqual(order, [GOLD, TEST_PATCH])
        base_cid = next(c for c, i in runner.applies if c != gold_cid)
        self.assertEqual([i for c, i in runner.applies if c == base_cid], [TEST_PATCH])

    def test_test_patch_conflict_at_base(self):
        res = validate.validate_task(make_row(), FakeRunner(test_conflict=("base",)), "/r")
        self.assertFalse(res["valid"])
        self.assertFalse(res["base_fail_to_pass_failing"])
        self.assertIn("test patch does not apply at base", res["reason"])

    def test_test_patch_conflict_after_gold(self):
        row = make_row()
        row = TaskRow(**{**row.__dict__, "patch": TEST_PATCH})  # gold edits the test file too
        runner = FakeRunner()
        res = validate.validate_task(row, runner, "/r")
        self.assertFalse(res["valid"])
        self.assertFalse(res["gold_resolved"])
        self.assertTrue(res["base_fail_to_pass_failing"])
        self.assertIn("on top of gold patch", res["reason"])
        self.assertEqual(len(runner.removed), 2)

    def test_missing_f2p_on_base_counts_as_failing(self):
        res = validate.validate_task(make_row(), FakeRunner(base_log="PASSED tests/t.py::p2p\n"), "/r")
        self.assertTrue(res["base_fail_to_pass_failing"])
        self.assertTrue(res["valid"])
        self.assertEqual(res["base_fail_to_pass"]["tests/t.py::f2p"], "MISSING")

    def test_exception_mid_run_stops_container(self):
        class Boom(FakeRunner):
            def run(self, args, **kw):
                if "bash" in args:
                    raise OSError("disk gone")
                return super().run(args, **kw)
        runner = Boom()
        res = validate.validate_task(make_row(), runner, "/r")
        self.assertFalse(res["valid"])
        self.assertIn("disk gone", res["error"])
        self.assertEqual(runner.removed, ["cid1"])

    def test_empty_fail_to_pass_is_invalid(self):
        row = make_row()
        row = TaskRow(**{**row.__dict__, "fail_to_pass": ()})
        res = validate.validate_task(row, FakeRunner(), "/r")
        self.assertFalse(res["base_fail_to_pass_failing"])
        self.assertFalse(res["valid"])
        self.assertIn("no FAIL_TO_PASS tests", res["reason"])


class ImageChecksTest(unittest.TestCase):
    PATHS = ["changes", "changes/test_bench_probe.md", "UNRELEASED.md"]

    def test_rule_paths_from_matchers(self):
        rules = [RuleSpec("a", "o/r", "x", "y", {"type": "added_line", "path_glob": "UNRELEASED.md", "line_regex": "."},
                          {"type": "new_file", "dir": "changes/", "name_regex": r".+\.md"}),
                 RuleSpec("b", "o/r", "x", "y", {"type": "new_file", "dir": "t/reg", "name_regex": r"test_.+\.py"},
                          {"type": "added_line", "path_glob": "docs/*.rst", "line_regex": "."})]
        self.assertEqual(validate.rule_paths(rules), ["UNRELEASED.md", "changes", "changes/test_bench_probe.md",
                                                      "docs/test_bench_probe.rst", "t/reg", "t/reg/test_bench_probe.py"])

    def test_checks_pass(self):
        runner = FakeRunner()
        res = validate.validate_task(make_row(), runner, "/r", paths=self.PATHS)
        self.assertTrue(res["valid"])
        self.assertTrue(res["has_base_commit"])
        self.assertEqual(res["ignored_rule_paths"], [])
        self.assertIn(["git", "-C", "/r", "cat-file", "-e", "abc"], [c[3:] for c in runner.calls])
        self.assertIn(["git", "-C", "/r", "check-ignore", "--"] + self.PATHS, [c[3:] for c in runner.calls])

    def test_missing_base_commit_invalid(self):
        res = validate.validate_task(make_row(), FakeRunner(has_base=False), "/r", paths=self.PATHS)
        self.assertFalse(res["valid"])
        self.assertFalse(res["has_base_commit"])
        self.assertIn("base commit abc missing", res["reason"])

    def test_ignored_rule_dir_invalid(self):
        res = validate.validate_task(make_row(), FakeRunner(ignored="changes"), "/r", paths=self.PATHS)
        self.assertFalse(res["valid"])
        self.assertEqual(res["ignored_rule_paths"], ["changes", "changes/test_bench_probe.md"])
        self.assertIn("gitignored: changes", res["reason"])

    def test_network_passed_to_docker_run(self):
        runner = FakeRunner()
        validate.validate_task(make_row(), runner, "/r", network="none")
        runs = [c for c in runner.calls if c[:2] == ["docker", "run"]]
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(c[4:6] == ["--network", "none"] for c in runs))

    def test_scoring_network_joined_before_tests_in_both_runs(self):
        runner = FakeRunner()
        res = validate.validate_task(make_row(), runner, "/r", network="none", scoring_network="bridge")
        self.assertTrue(res["valid"], res["reason"])
        for cid in ("cid1", "cid2"):
            calls = [c for c in runner.calls if cid in c]
            connect = calls.index(["docker", "network", "connect", "bridge", cid])
            self.assertEqual(calls[connect - 1], ["docker", "network", "disconnect", "none", cid])
            test_apply = next(i for i, c in enumerate(calls) if "apply" in c and i > connect)
            self.assertGreater(test_apply, connect)
            # Base checks and the gold patch ran before the network opened.
            self.assertTrue(any("apply" in c or "cat-file" in c for c in calls[:connect]))

    def test_gold_runs_repeat_in_fresh_containers(self):
        runner = FakeRunner()
        res = validate.validate_task(make_row(), runner, "/r", gold_runs=3)
        self.assertTrue(res["valid"], res["reason"])
        self.assertEqual(res["gold_runs_passed"], 3)
        self.assertEqual(len([c for c in runner.calls if c[:2] == ["docker", "run"]]), 4)

    def test_flaky_gold_run_is_invalid(self):
        class Flaky(FakeRunner):
            def run(self, args, *, input=None, timeout, max_output=None):
                if args[:2] == ["docker", "run"] and self.runs == 2:
                    self.gold_log = FAIL_LOG  # the second gold container fails
                return super().run(args, input=input, timeout=timeout, max_output=max_output)
        res = validate.validate_task(make_row(), Flaky(), "/r", gold_runs=3)
        self.assertFalse(res["valid"])
        self.assertEqual(res["gold_runs_passed"], 1)
        self.assertIn("flaky: gold resolved 1 of 2 runs", res["reason"])

    def test_gold_run_does_not_reset_test_files(self):
        runner = FakeRunner()
        validate.validate_task(make_row(), runner, "/r")
        gold_cid = next(c for c, i in runner.applies if i == GOLD)
        gold_calls = [c for c in runner.calls if gold_cid in c]
        self.assertFalse([c for c in gold_calls if "checkout" in c or "ls-tree" in c])

    def test_manifest_checks_rule_paths_from_rules_dir(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "rules").mkdir()
            (d / "rules" / "o__r.json").write_text(json.dumps([{
                "id": "a", "repo": "o/r", "original": "x", "changed": "y",
                "old": {"type": "added_line", "path_glob": "UNRELEASED.md", "line_regex": "."},
                "new": {"type": "new_file", "dir": "changes", "name_regex": r".+\.md"}}]))
            cases = [Case("c1", "o/r", "o__r-1", "o__r-2", (), "a", "b")]
            rows = {i: make_row(i) for i in ("o__r-1", "o__r-2")}
            summary = validate.validate_manifest(cases, rows, d / "out", FakeRunner(ignored="changes"),
                                                 rules_dir=d / "rules", network="none")
            self.assertEqual(summary["valid_ids"], [])
            self.assertIn("gitignored", summary["tasks"]["o__r-1"]["reason"])

    def test_cli_refuses_output_inside_repo(self):
        from bench.run_bench import REPO
        with self.assertRaises(SystemExit) as cm:
            validate.main(["--manifest", "m.json", "--data-root", "d", "--output", str(REPO / "results" / "x")])
        self.assertIn("Refusing output", str(cm.exception))


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
