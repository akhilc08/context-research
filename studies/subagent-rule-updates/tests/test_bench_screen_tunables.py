"""Offline tests for the tunables screening runner over the fake container from test_bench_session."""
import json
import tempfile
import unittest
from pathlib import Path

from bench import screen_tunables as ST
from bench import tunables as T
from tests.test_bench_session import ROWS, FakeRunner, Factory, call, reply

CONFIG = {"max_worker_calls": 6, "screen_repetitions": 2, "order_seed": 1}
ROW = ROWS["o__r-1"]


class ArmWorker:
    """Writes app.py with an inline literal, a named constant, or an environment read, by the rule it was told."""

    def __init__(self):
        self.n = 0

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.n += 1
        if sum(m["role"] == "assistant" for m in messages):
            return reply("Done.", self.n)
        first = messages[1]["content"]
        if T.RULES["env"] in first:
            code = 'import os\nWAIT = float(os.environ.get("APP_WAIT", "30"))\n\n\ndef f():\n    return WAIT\n'
        elif T.RULES["const"] in first:
            code = "WAIT = 30\n\n\ndef f():\n    return WAIT\n"
        else:
            code = "def f(wait=30):\n    return wait\n"
        return call("write_file", {"path": "app.py", "content": code}, self.n)


class Summary:
    def summary(self):
        return {"budget_committed_usd": 0.0}


class Client(ArmWorker, Summary):
    pass


class Runner(FakeRunner):
    def run(self, args, **kw):
        if args[:3] == ["docker", "image", "inspect"]:
            return 0, "", ""
        return super().run(args, **kw)


class ScreenTunablesTest(unittest.TestCase):
    def test_plan_is_task_major_and_balanced(self):
        plan = ST.build_plan(["a", "b"], 2, 7)
        self.assertEqual([e["task_id"] for e in plan], ["a"] * 6 + ["b"] * 6)
        self.assertEqual(sorted((e["arm"], e["repetition"]) for e in plan[:6]),
                         sorted((a, r) for a in T.ARMS for r in range(2)))

    def test_execute_records_forms_tests_and_gold(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            plan = ST.build_plan([ROW.instance_id], 2, 1)
            failure = ST.execute(Client(), out, plan, {ROW.instance_id: ROW}, CONFIG, workspace_factory=Factory(),
                                 runner=Runner(), validate=lambda row: {"valid": True}, remove_images=True)
            self.assertIsNone(failure)
            setup = json.loads((out / "tasks" / ROW.instance_id / "setup.json").read_text())
            self.assertEqual(setup["gold"]["status"], "finished")
            records = [json.loads(p.read_text()) for p in out.glob("tasks/*/*/rep*/record.json")]
            self.assertEqual(len(records), 6)
            for r in records:
                self.assertEqual(r["status"], "finished")
                forms = {c["form"] for c in r["extraction"]["candidates"]}
                self.assertEqual(forms, {{"none": "inline", "const": "const", "env": "env"}[r["arm"]]}, r["arm"])
                self.assertIn("app.py", r["scorable_files"])
                self.assertTrue(r["tests"]["resolved"])
                self.assertIn("test_seconds", r)

    def test_invalid_task_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            client = Client()
            ST.execute(client, out, ST.build_plan([ROW.instance_id], 1, 1), {ROW.instance_id: ROW}, CONFIG,
                       workspace_factory=Factory(), runner=Runner(), validate=lambda row: {"valid": False},
                       remove_images=False)
            self.assertEqual(client.n, 0)
            self.assertNotIn("gold", json.loads((out / "tasks" / ROW.instance_id / "setup.json").read_text()))

    def test_scorable_changes_skips_tests_and_caps(self):
        kept = ST.scorable_changes({"pkg/a.py": ("x", "y"), "tests/test_a.py": ("x", "y"), "README.md": ("a", "b")})
        self.assertEqual(kept, {"pkg/a.py": ["x", "y"]})
        big = ST.scorable_changes({"a.py": (None, "x" * (ST.SCORABLE_CAP + 1))})
        self.assertEqual(big, {"a.py": None})

    def test_pool_has_usable_ids(self):
        self.assertGreaterEqual(len(ST.pool_ids()), 40)


if __name__ == "__main__":
    unittest.main()


class AdjudicateTest(unittest.TestCase):
    def test_parse_verdicts(self):
        from bench import adjudicate_tunables as A
        text = '```json\n{"values": [{"id": 0, "tunable": true, "reason": "timeout"}]}\n```'
        self.assertEqual(A.parse_verdicts(text, [0]), {0: {"tunable": True, "reason": "timeout"}})
        prose = 'The first value is a cap.\n\n{"values": [{"id": 0, "tunable": false, "reason": "unit"}]} trailing'
        self.assertFalse(A.parse_verdicts(prose, [0])[0]["tunable"])
        with self.assertRaises(ValueError):
            A.parse_verdicts('{"values": []}', [0])
        with self.assertRaises(ValueError):
            A.parse_verdicts("no json here", [0])

    def test_adjudicate_and_summarize_end_to_end(self):
        from bench import adjudicate_tunables as A

        class Judge:
            def __init__(self):
                self.prompts = []

            def complete(self, messages, **kw):
                self.prompts.append(messages[1]["content"])
                ids = [int(i) for i in __import__("re").findall(r"Value (\d+):", messages[1]["content"])]
                return reply(json.dumps({"values": [{"id": i, "tunable": True, "reason": "wait"} for i in ids]}), 1)

        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            ST.execute(Client(), out, ST.build_plan([ROW.instance_id], 2, 1), {ROW.instance_id: ROW}, CONFIG,
                       workspace_factory=Factory(), runner=Runner(), validate=lambda row: {"valid": True},
                       remove_images=False)
            judge = Judge()
            adj = A.adjudicate(judge, out, out / "adjudications.json")
            self.assertEqual(len(judge.prompts), 6)  # Six runs with candidates; the gold extraction has none.
            for prompt in judge.prompts:  # Blind to the arm and the rules.
                self.assertNotIn("Project rule", prompt)
                self.assertNotIn("UPPER_CASE", prompt)
            again = Judge()
            A.adjudicate(again, out, out / "adjudications.json")
            self.assertEqual(again.prompts, [])  # Resumes without re-asking.
            summary = A.summarize(out, adj)
            arms = summary["tasks"][ROW.instance_id]["arms"]
            self.assertEqual(arms, {"none": {"bare": 2}, "const": {"follows": 2}, "env": {"follows": 2}})
            self.assertEqual(summary["kept"], [ROW.instance_id])
