from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench import cases
from bench.rules import RuleSpec
from bench.sources import TaskRow

M = {"type": "new_file", "dir": "d", "name_regex": "x"}


def _row(iid, repo, created, ps="PROBLEM TEXT", patch="PATCH TEXT"):
    return TaskRow(instance_id=iid, repo=repo, base_commit="c", problem_statement=ps,
                   image_name="i", language="python", created_at=created, test_cmd="",
                   log_parser="", fail_to_pass=(), pass_to_pass=(), patch=patch,
                   test_patch="", license="MIT", workdir="/r")


def _rule(rid, repo):
    return RuleSpec(id=rid, repo=repo, original="a", changed="b", old=M, new=M)


class CasesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = "o/r"
        self.rows = [_row("o__r-10", self.repo, 100), _row("o__r-20", self.repo, 200),
                     _row("o__r-30", self.repo, 300)]
        self.trajs = {self.repo: {}}
        for n in (1, 2, 3, 5, 20, 40):
            iid = "o__r-%d" % n
            p = self.tmp / (iid + ".traj.json")
            p.write_text(json.dumps({"messages": [
                {"role": "system", "content": "s"},
                {"role": "user", "content": "task %d " % n + "x" * 100}]}))
            self.trajs[self.repo][iid] = p
        self.rules = {self.repo: [_rule("r1", self.repo), _rule("r2", self.repo)]}

    def build(self, **kw):
        args = dict(history_chars=150, seed=0)
        args.update(kw)
        return cases.build_cases(self.rows, self.trajs, self.rules, **args)

    def test_history_below_second_and_excludes_tasks(self):
        out = self.build()
        self.assertTrue(out)
        for c in out:
            self.assertEqual((c.first, c.second), ("o__r-20", "o__r-30"))
            nums = [int(h.rsplit("-", 1)[1]) for h in c.history]
            self.assertTrue(all(n < 30 for n in nums))
            self.assertNotIn("o__r-20", c.history)
            self.assertEqual(nums, sorted(nums))

    def test_newest_first_selection(self):
        out = self.build(history_chars=1)
        self.assertEqual(out[0].history, ("o__r-5",))

    def test_one_rule_yields_nothing(self):
        self.rules[self.repo] = self.rules[self.repo][:1]
        self.assertEqual(self.build(), [])

    def test_insufficient_history_skips_repo(self):
        self.assertEqual(self.build(history_chars=10 ** 6), [])

    def test_two_cases_swapped(self):
        out = self.build()
        self.assertEqual(len(out), 2)
        self.assertEqual([(c.changed_rule, c.unchanged_rule) for c in out],
                         [("r1", "r2"), ("r2", "r1")])
        self.assertEqual(out[0].case_id, "o__r--r1")

    def test_tie_break_by_issue_number(self):
        self.rows = [_row("o__r-10", self.repo, 100), _row("o__r-30", self.repo, 100),
                     _row("o__r-20", self.repo, 100)]
        out = self.build()
        self.assertEqual((out[0].first, out[0].second), ("o__r-20", "o__r-30"))

    def test_manifest_round_trip_without_task_text(self):
        out = self.build()
        path = self.tmp / "m.json"
        cases.save_manifest(out, path)
        self.assertEqual(cases.load_manifest(path), out)
        text = path.read_text()
        self.assertNotIn("PROBLEM TEXT", text)
        self.assertNotIn("PATCH TEXT", text)
        self.assertNotIn("problem_statement", text)
        self.assertNotIn("patch", text)
        self.assertEqual(json.loads(text)["version"], 1)

    def test_unknown_version_rejected(self):
        path = self.tmp / "m.json"
        path.write_text(json.dumps({"version": 2, "cases": []}))
        with self.assertRaises(ValueError):
            cases.load_manifest(path)


if __name__ == "__main__":
    unittest.main()
