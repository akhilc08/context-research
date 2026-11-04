"""Tightening scenario: a stale permissive rule can cause real violations."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import harness as H
from analyze import analyze
from run import execute_study, save
from test_run import ScriptedClient


class TightenTests(unittest.TestCase):
    def test_blocks_and_relays_use_tighten_text_with_the_same_current_rule(self):
        self.assertIn(H.R0_TIGHTEN, H.rule_block("R0", "tighten"))
        self.assertIn(H.R1, H.rule_block("R1", "tighten"))
        self.assertEqual(H.rule_block("R1", "tighten"), H.rule_block("R1", "loosen"))
        text = H.delegation("minor", {"brief": "Work", "relay_user_message_ids": ["U1"]}, "tighten")
        self.assertIn(H.AMENDMENT_TIGHTEN, text)
        self.assertNotIn(H.AMENDMENT, text)
        contents = [m["content"] for m in H.manager_messages("existing", "minor", "tighten")]
        self.assertTrue(any(H.R0_TIGHTEN in c for c in contents))
        self.assertFalse(any(H.R0 in c for c in contents))

    def test_existing_fork_keeps_scenario_and_stale_permissive_block(self):
        checkpoint = H.Session("E", "R0", scenario="tighten")
        stale = H.session_for("creation_pin", "existing", checkpoint, "unused")
        fresh = H.session_for("refreshed_store", "existing", checkpoint, "unused")
        new = H.session_for("creation_pin", "new", checkpoint, "N")
        self.assertIn(H.R0_TIGHTEN, stale.request_messages()[0]["content"])
        self.assertIn(H.R1, fresh.request_messages()[0]["content"])
        self.assertEqual(new.scenario, "tighten")

    def test_unapproved_minor_edit_is_a_violation_under_current_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            ws = H.Workspace(Path(directory) / "ws")
            ws.execute("write_file", {"path": "requirements.txt", "content": "httpx==0.27.0\nrich==13.8.0\n"}, call_index=0)
            ws.execute("write_file", {"path": "RELEASE_NOTES.md", "content": "# Release notes\nDependency review recorded.\n"}, call_index=1)
            now = H.score("minor", ws.events, ws.snapshot(), scenario="tighten")
            before = H.score("minor", ws.events, ws.snapshot(), scenario="tighten", active_rule_version="R0")
        self.assertIs(now["policy_adherence"], False)
        self.assertFalse(now["task_success"])
        self.assertIs(before["policy_adherence"], True)
        self.assertTrue(before["task_success"])

    def test_scripted_tighten_study_runs_all_branches(self):
        config = {"repetitions": 1, "max_worker_calls": 8, "manager_schema_retries": 1, "order_seed": 7, "scenario": "tighten"}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            save(output / "manifest.json", {"config": config, "scenario": "tighten", "selected_model": {"id": "scripted"}, "planned_branches": 24})
            execute_study(ScriptedClient(), output, config)
            summary = analyze(output)
            self.assertEqual(summary["recorded_branches"], 24)
            rows = [json.loads(p.read_text()) for p in output.glob("rep-*/branches/*/result.json")]
            self.assertTrue(all(r["scenario"] == "tighten" and r["delivery_verified"] for r in rows))
            stale = next(r for r in rows if r["branch_id"] == "unbriefed__creation_pin__existing__minor")
            self.assertIn(H.R0_TIGHTEN, stale["requests"][0]["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
