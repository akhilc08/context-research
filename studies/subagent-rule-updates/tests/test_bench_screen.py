"""Offline tests for the rule screening runner. No client is ever built."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bench import screen_bench as SB
from bench.cases import Case, save_manifest
from tests.test_bench_session import CASE, RULES, ROWS, Factory, call, reply

CASES = [Case("o__r--a", "o/r", "o__r-1", "o__r-2", ("h1",), "notes", "tags"),
         Case("o__r--b", "o/r", "o__r-1", "o__r-3", ("h2",), "tags", "notes")]
CONFIG = {"order_seed": 7, "max_worker_calls": 6, "models": [{"id": "m", "provider": "p", "budget_usd": 1}]}


def write(tmp: Path, config=CONFIG):
    save_manifest(CASES, tmp / "cases.json")
    (tmp / "config.json").write_text(json.dumps(config))
    return ["--config", str(tmp / "config.json"), "--manifest", str(tmp / "cases.json")]


def recs(rule, arm, outcomes, status="finished"):
    return [{"rule_id": rule, "arm": arm, "status": status, "outcome": o} if status == "finished"
            else {"rule_id": rule, "arm": arm, "status": status} for o in outcomes]


def make(none_matches, original_old, changed_new, n=10):
    return (recs("r", "none", ["old"] * none_matches + ["neither"] * (n - none_matches))
            + recs("r", "original", ["old"] * original_old + ["neither"] * (n - original_old))
            + recs("r", "changed", ["new"] * changed_new + ["neither"] * (n - changed_new)))


class VerdictTests(unittest.TestCase):
    def test_arms(self):
        self.assertEqual(SB.arms(), ["none", "original", "changed"])

    def test_boundaries_pass(self):
        v = SB.screen_verdicts(make(2, 9, 9))["r"]
        self.assertTrue(v["passed"])
        self.assertEqual((v["none_match_rate"], v["original_follow_rate"], v["changed_follow_rate"]), (0.2, 0.9, 0.9))

    def test_each_boundary_fails_just_past(self):
        self.assertFalse(SB.screen_verdicts(make(3, 10, 10))["r"]["passed"])
        self.assertFalse(SB.screen_verdicts(make(0, 8, 10))["r"]["passed"])
        self.assertFalse(SB.screen_verdicts(make(0, 10, 8))["r"]["passed"])

    def test_none_arm_both_or_new_counts_as_match(self):
        records = (recs("r", "none", ["both", "new"] + ["neither"] * 8) + recs("r", "original", ["old"] * 10)
                   + recs("r", "changed", ["new"] * 10))
        self.assertEqual(SB.screen_verdicts(records)["r"]["none_match_rate"], 0.2)
        self.assertTrue(SB.screen_verdicts(records)["r"]["passed"])

    def test_both_outcome_is_not_following(self):
        records = recs("r", "none", ["neither"] * 10) + recs("r", "original", ["both"] * 10) + recs("r", "changed", ["new"] * 10)
        self.assertFalse(SB.screen_verdicts(records)["r"]["passed"])

    def test_unfinished_excluded_from_rates_and_counted(self):
        records = make(0, 10, 10) + recs("r", "original", [None] * 5, status="provider_error") \
            + recs("r", "none", [None] * 2, status="infra_error")
        v = SB.screen_verdicts(records)["r"]
        self.assertTrue(v["passed"])
        self.assertEqual(v["original_follow_rate"], 1.0)
        counts = SB.run_counts(records)["r"]
        self.assertEqual(counts["original"], {"finished": 10, "unfinished": {"provider_error": 5}})
        self.assertEqual(counts["none"]["unfinished"], {"infra_error": 2})

    def test_zero_finished_arm_not_passed(self):
        records = make(0, 10, 10)
        records = [r for r in records if r["arm"] != "changed"] + recs("r", "changed", [None] * 3, status="infra_error")
        self.assertFalse(SB.screen_verdicts(records)["r"]["passed"])
        self.assertFalse(SB.screen_verdicts(recs("r", "none", ["neither"]))["r"]["passed"])


class FixRoundTests(unittest.TestCase):
    def test_none_arm_call_limit_is_excluded_not_counted_as_neither(self):
        # 3 of 10 finished none runs match (fails). Ten call_limit runs that wrote nothing must not dilute that.
        records = make(3, 10, 10) + [{"rule_id": "r", "arm": "none", "status": "call_limit", "outcome": "neither"}
                                     for _ in range(10)]
        v = SB.screen_verdicts(records)["r"]
        self.assertEqual(v["none_match_rate"], 0.3)
        self.assertFalse(v["passed"])

    def test_told_arm_model_protocol_error_excluded(self):
        records = make(0, 10, 10) + [{"rule_id": "r", "arm": "changed", "status": "model_protocol_error",
                                      "outcome": "neither"} for _ in range(5)]
        v = SB.screen_verdicts(records)["r"]
        self.assertEqual(v["changed_follow_rate"], 1.0)
        self.assertTrue(v["passed"])

    def test_status_breakdown_in_screening_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            records = make(0, 10, 10) + [{"rule_id": "r", "arm": "none", "status": s, "outcome": "neither"}
                                         for s in ("call_limit", "call_limit", "model_protocol_error")]
            for i, r in enumerate(records):
                (out / ("x%d" % i)).mkdir()
                (out / ("x%d" % i) / "record.json").write_text(json.dumps(r))
            runs = SB.analyze(out)["verdicts"]["r"]["runs"]
            self.assertEqual(runs["none"], {"finished": 10, "unfinished": {"call_limit": 2, "model_protocol_error": 1}})

    def test_planned_rule_without_records_is_not_passed(self):
        v = SB.screen_verdicts(make(0, 10, 10), rule_ids=["r", "missing"])
        self.assertTrue(v["r"]["passed"])
        self.assertEqual(v["missing"], {"passed": False, "none_match_rate": 0.0, "original_follow_rate": 0.0,
                                        "changed_follow_rate": 0.0})
        with tempfile.TemporaryDirectory() as d:
            result = SB.analyze(Path(d), rule_ids=["missing"])
            self.assertFalse(result["verdicts"]["missing"]["passed"])
            self.assertEqual(result["verdicts"]["missing"]["runs"]["none"], {"finished": 0, "unfinished": {}})


class PlanTests(unittest.TestCase):
    def test_dedupes_rules_per_repo_and_defaults_repetitions(self):
        plan = SB.build_plan({"order_seed": 1}, {c.case_id: c for c in CASES}, ["o__r--a", "o__r--b"])
        self.assertEqual(len(plan), 2 * 3 * 10)
        self.assertEqual({(e["rule_id"], e["arm"]) for e in plan}, {(r, a) for r in ("notes", "tags") for a in SB.arms()})
        self.assertEqual({e["case_id"] for e in plan}, {"o__r--a"})
        small = SB.build_plan({"order_seed": 1, "screen_repetitions": 2}, {c.case_id: c for c in CASES}, ["o__r--a"])
        self.assertEqual(len(small), 12)
        self.assertEqual(small, SB.build_plan({"order_seed": 1, "screen_repetitions": 2}, {c.case_id: c for c in CASES}, ["o__r--a"]))


class RunnerTests(unittest.TestCase):
    def test_dry_run_writes_plan_and_builds_no_client(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("provider.OpenRouterClient") as client:
            tmp = Path(d)
            self.assertEqual(SB.main(write(tmp) + ["--output", str(tmp / "out")]), 0)
            client.assert_not_called()
            self.assertEqual(len(json.loads((tmp / "out" / "plan.json").read_text())["entries"]), 60)

    def test_live_refuses_existing_model_directory(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("provider.OpenRouterClient") as client:
            tmp = Path(d)
            (tmp / "out" / "model-0").mkdir(parents=True)
            with self.assertRaises(SystemExit):
                SB.main(write(tmp) + ["--output", str(tmp / "out"), "--live"])
            client.assert_not_called()

    def test_refuses_output_in_repo_outside_ignored_path(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                SB.main(write(Path(d)) + ["--output", str(SB.RB.REPO / "results" / "x")])

    def test_missing_rules_fails_before_model_dir_or_client(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("provider.OpenRouterClient") as client:
            tmp = Path(d)
            data = tmp / "data"
            (data / SB.RB.PARQUET).parent.mkdir(parents=True)
            (data / SB.RB.PARQUET).write_text("")
            (data / SB.RB.HISTORY_DIR).mkdir(parents=True)
            args = write(tmp, {**CONFIG, "data_root": str(data)}) + ["--output", str(tmp / "out"), "--live"]
            with mock.patch.object(SB, "STUDY", tmp):
                with self.assertRaises(SystemExit):
                    SB.main(args)
            client.assert_not_called()
            self.assertFalse((tmp / "out" / "model-0").exists())

    def test_execute_runs_scripted_worker_and_scores(self):
        class Client:
            n = 0

            def summary(self):
                return {"budget_committed_usd": 0.0}

            def complete(self, messages, *, tools=None, tag="", **kw):
                self.n += 1
                text = [m for m in messages if m["role"] == "user"][0]["content"]
                if any(m["role"] == "tool" for m in messages):
                    return reply("Done.", self.n)
                if "release note as news/" in text:
                    return call("write_file", {"path": "news/1.txt", "content": "x\n"}, self.n)
                if "release note as changes/" in text:
                    return call("write_file", {"path": "changes/1.txt", "content": "x\n"}, self.n)
                return call("write_file", {"path": "other.txt", "content": "x\n"}, self.n)

        plan = [{"case_id": CASE.case_id, "repo": "o/r", "rule_id": "notes", "arm": a, "repetition": 0} for a in SB.arms()]
        with tempfile.TemporaryDirectory() as d, mock.patch.object(SB.RB, "load_rule_map", return_value=RULES):
            out = Path(d)
            reason = SB.execute(Client(), out, plan, {CASE.case_id: CASE}, CONFIG, rows=ROWS, rules_dir=out,
                                workspace_factory=Factory())
            self.assertIsNone(reason)
            result = SB.analyze(out)
            by_arm = {r["arm"]: r for r in result["runs"]}
            self.assertEqual({a: by_arm[a]["outcome"] for a in SB.arms()},
                             {"none": "neither", "original": "old", "changed": "new"})
            self.assertTrue(by_arm["none"]["first_message"].startswith("Task: "))
            self.assertTrue(by_arm["original"]["first_message"].startswith("Project rule from the user: Add a release note as changes/"))
            self.assertEqual(result["verdicts"]["notes"]["original_follow_rate"], 1.0)
            self.assertTrue((out / "screening.json").exists())

    def test_execute_stops_on_provider_error_and_continues_past_infra(self):
        class Client:
            def summary(self):
                return {"budget_committed_usd": 0.0}

            def complete(self, *a, **k):
                raise RuntimeError("down")

        def boom(row, d):
            raise OSError("no docker")

        plan = [{"case_id": CASE.case_id, "repo": "o/r", "rule_id": "notes", "arm": "none", "repetition": i} for i in range(2)]
        with tempfile.TemporaryDirectory() as d, mock.patch.object(SB.RB, "load_rule_map", return_value=RULES):
            out = Path(d)
            self.assertIsNone(SB.execute(Client(), out, plan, {CASE.case_id: CASE}, CONFIG, rows=ROWS, rules_dir=out,
                                         workspace_factory=boom))
            self.assertEqual(len(list(out.rglob("record.json"))), 2)
            reason = SB.execute(Client(), out / "b", plan, {CASE.case_id: CASE}, CONFIG, rows=ROWS, rules_dir=out,
                                workspace_factory=Factory())
            self.assertIn("provider_error", reason)
            self.assertEqual(len(list((out / "b").rglob("record.json"))), 1)


if __name__ == "__main__":
    unittest.main()
