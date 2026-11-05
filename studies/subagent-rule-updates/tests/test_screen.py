"""Offline tests for the rule screen: fixture validity, classifiers, worker, and analysis."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import scenarios as S
import worker as W
from screen import analyze, arms, execute, first_message


def edit(**changes):
    files = copy.deepcopy(S.FIXTURE)
    files.update(changes)
    return files


DISCOUNTED = S.FIXTURE["app/pricing.py"].replace(
    "    return round(subtotal * 1.08, 2)\n",
    "    if sum(qty for _, qty in lines) >= 40:\n        subtotal *= 0.93\n    return round(subtotal * 1.08, 2)\n")


class FixtureTest(unittest.TestCase):
    def test_fixture_tests_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, content in S.FIXTURE.items():
                (Path(tmp) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(tmp) / name).write_text(content)
            done = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_untouched_fixture_scores_none(self):
        for rule, classify in S.CLASSIFIERS.items():
            for task in S.TASKS:
                self.assertEqual(classify(S.FIXTURE, task)["outcome"], "none", (rule, task))
        self.assertFalse(S.task_attempted(S.FIXTURE, "bulk_discount"))


class ClassifierTest(unittest.TestCase):
    def test_changelog(self):
        c = S.classify_changelog
        self.assertEqual(c(edit(**{"CHANGELOG.md": "- Bulk discount\n"}), "bulk_discount")["outcome"], "v1")
        self.assertEqual(c(edit(**{"docs/HISTORY.md": "- INV-212: bulk discount\n"}), "bulk_discount")["outcome"], "v2")
        # The changed rule requires the entry to start with the ticket ID.
        self.assertEqual(c(edit(**{"docs/HISTORY.md": "Bulk discount (INV-212)\n"}), "bulk_discount")["outcome"], "none")
        self.assertEqual(c(edit(**{"docs/HISTORY.md": "INV-999: other\n"}), "bulk_discount")["outcome"], "none")
        both = edit(**{"CHANGELOG.md": "x\n", "docs/HISTORY.md": "INV-215 low stock\n"})
        self.assertEqual(c(both, "low_stock")["outcome"], "both")

    def test_test_placement(self):
        c = S.classify_test_placement
        gained = S.FIXTURE["tests/test_pricing.py"].replace("\n\nif __name__", "\n    def test_bulk(self):\n        pass\n\n\nif __name__")
        self.assertEqual(c(edit(**{"tests/test_pricing.py": gained}), "bulk_discount")["outcome"], "v1")
        reg = "import unittest\n\nclass T(unittest.TestCase):\n    def test_bulk(self):\n        pass\n"
        self.assertEqual(c(edit(**{"tests/regression/test_inv_212.py": reg}), "bulk_discount")["outcome"], "v2")
        self.assertEqual(c(edit(**{"tests/regression/test_INV212.py": reg}), "bulk_discount")["outcome"], "v2")
        self.assertEqual(c(edit(**{"tests/regression/test_inv_215.py": reg}), "bulk_discount")["outcome"], "other")
        self.assertEqual(c(edit(**{"tests/test_bulk.py": reg}), "bulk_discount")["outcome"], "other")

    def test_config_values(self):
        c = S.classify_config_values
        hardcoded = c(edit(**{"app/pricing.py": DISCOUNTED}), "bulk_discount")
        self.assertEqual((hardcoded["outcome"], hardcoded["literal_in_module"]), ("none", True))
        via_config = DISCOUNTED.replace('"""Order pricing."""\n', '"""Order pricing."""\nfrom app import config\n').replace(">= 40", ">= config.BULK_MIN_ITEMS")
        files = edit(**{"app/pricing.py": via_config, "app/config.py": S.FIXTURE["app/config.py"] + "BULK_MIN_ITEMS = 40\n"})
        self.assertEqual(c(files, "bulk_discount")["outcome"], "v1")
        # A config constant the module never uses is not compliance.
        files = edit(**{"app/pricing.py": DISCOUNTED, "app/config.py": S.FIXTURE["app/config.py"] + "BULK_MIN_ITEMS = 40\n"})
        self.assertEqual(c(files, "bulk_discount")["outcome"], "none")
        via_settings = DISCOUNTED.replace('"""Order pricing."""\n', '"""Order pricing."""\nfrom app import settings\n').replace(
            ">= 40", '>= int(settings.get("BULK_MIN_ITEMS", 40))')
        self.assertEqual(c(edit(**{"app/pricing.py": via_settings}), "bulk_discount")["outcome"], "v2")
        from_import = DISCOUNTED.replace('"""Order pricing."""\n', '"""Order pricing."""\nfrom app.settings import get\n').replace(
            ">= 40", '>= int(get("BULK_MIN_ITEMS", 40))')
        self.assertEqual(c(edit(**{"app/pricing.py": from_import}), "bulk_discount")["outcome"], "v2")


class WorkspaceTest(unittest.TestCase):
    def test_rejects_escape_and_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = W.Workspace(Path(tmp) / "ws", S.FIXTURE, Path(tmp) / "events.jsonl")
            self.assertIn("error", ws.execute("write_file", {"path": "../x", "content": "y"}, call_index=0))
            self.assertIn("error", ws.execute("read_file", {"path": "missing.py"}, call_index=0))
            self.assertIn("error", ws.execute("write_file", {"path": "a"}, call_index=0))
            self.assertEqual(ws.execute("list_files", {}, call_index=0)["files"], sorted(S.FIXTURE))
            ws.execute("write_file", {"path": "docs/HISTORY.md", "content": "INV-1\n"}, call_index=1)
            self.assertEqual(ws.snapshot()["docs/HISTORY.md"], "INV-1\n")
            self.assertEqual(len((Path(tmp) / "events.jsonl").read_text().splitlines()), 5)


class ScriptedClient:
    """Follows whichever rule the first message states, so every arm can be checked offline."""

    def __init__(self):
        self.calls = 0

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.calls += 1
        first = messages[1]["content"]
        step = sum(m["role"] == "assistant" for m in messages)
        task = next(t for t, spec in S.TASKS.items() if spec["text"] in first)
        writes = [("write_file", {"path": S.TASKS[task]["module"], "content": S.FIXTURE[S.TASKS[task]["module"]] + "\n# 40 12\n"})]
        if S.RULES["changelog"]["v1"] in first:
            writes.append(("write_file", {"path": "CHANGELOG.md", "content": "- change\n"}))
        if S.RULES["changelog"]["v2"] in first:
            writes.append(("write_file", {"path": "docs/HISTORY.md", "content": f"- {S.TASKS[task]['ticket']}: change\n"}))
        if step < len(writes):
            name, args = writes[step]
            return {"id": f"r{self.calls}", "choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
                    "tool_calls": [{"id": f"c{self.calls}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}]}
        return {"id": f"r{self.calls}", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Done."}}]}


class ScreenTest(unittest.TestCase):
    def test_messages(self):
        self.assertEqual(len(arms()), 7)
        self.assertNotIn("rule", first_message("none", "low_stock").lower())
        self.assertIn(S.RULES["config_values"]["v2"], first_message("config_values:v2", "low_stock"))

    def test_end_to_end_offline(self):
        config = {"repetitions": 1, "order_seed": 1, "max_worker_calls": 6}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            execute(ScriptedClient(), out, config)
            summary = analyze(out)
            self.assertEqual((summary["runs"], summary["finished"], summary["task_attempted"]), (14, 14, 14))
            changelog = summary["rules"]["changelog"]
            self.assertEqual(changelog["cells"]["none"]["outcomes"], {"none": 2})
            self.assertEqual(changelog["cells"]["changelog:v1"]["outcomes"], {"v1": 2})
            self.assertEqual(changelog["cells"]["changelog:v2"]["outcomes"], {"v2": 2})
            self.assertTrue(changelog["passes"])
            # The scripted client ignores the other rules, so they must fail the screen.
            self.assertFalse(summary["rules"]["test_placement"]["passes"])
            self.assertTrue((out / "tables.md").read_text().startswith("# Rule screen"))


if __name__ == "__main__":
    unittest.main()
