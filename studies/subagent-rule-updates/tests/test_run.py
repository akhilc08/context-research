"""End-to-end orchestration tests with scripted responses, no network or keys."""
import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import harness as H
from analyze import analyze
from run import delivery_check, execute_study, main, prepare_brief, save


class ScriptedClient:
    def __init__(self):
        self.calls = []

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.calls.append(copy.deepcopy(messages))
        content, call = None, None
        if messages[0]["content"] == H.MANAGER_SYSTEM:
            content = json.dumps({"brief": "Perform the work order under the relayed user instructions.", "relay_user_message_ids": ["U0", "U1"]})
        else:
            last = max(i for i, msg in enumerate(messages) if msg["role"] == "user")
            task_text = messages[last]["content"]
            step = sum(msg["role"] == "assistant" for msg in messages[last + 1:])
            if task_text == H.WARMUP:
                if step == 0:
                    call = ("read_file", {"path": "requirements.txt"})
                else:
                    content = "httpx 0.27.0; rich 13.7.0."
            elif step == 0:
                call = ("read_file", {"path": "requirements.txt"})
            elif step == 1:
                call = ("read_file", {"path": "RELEASE_NOTES.md"})
            elif step == 2:
                if "Update httpx from" in task_text:
                    call = ("write_file", {"path": "requirements.txt", "content": "httpx==0.27.1\nrich==13.7.0\n"})
                else:
                    call = ("request_approval", {"package": "rich", "current_version": "13.7.0", "proposed_version": "13.8.0"})
            elif step == 3:
                call = ("write_file", {"path": "RELEASE_NOTES.md", "content": H.FIXTURE["RELEASE_NOTES.md"] + H.NOTE + "\n"})
            else:
                content = "Completed allowed work."
        message = {"role": "assistant", "content": content}
        if call:
            message["tool_calls"] = [{"id": f"tool_{len(self.calls)}", "type": "function", "function": {"name": call[0], "arguments": json.dumps(call[1])}}]
        return {"id": f"response_{len(self.calls)}", "choices": [{"message": message, "finish_reason": "tool_calls" if call else "stop"}]}


class RunTests(unittest.TestCase):
    def test_all_twelve_branches_and_recomputation(self):
        config = {"repetitions": 1, "max_worker_calls": 8, "manager_schema_retries": 1, "order_seed": 101}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            save(output / "manifest.json", {"config": config, "selected_model": {"id": "scripted"}, "planned_branches": 24})
            client = ScriptedClient()
            execute_study(client, output, config)
            summary = analyze(output)
            self.assertEqual(summary["recorded_branches"], 24)
            self.assertEqual(sum(r["task_success"] for r in summary["groups"]), 24)
            rows = [json.loads(p.read_text()) for p in output.glob("rep-*/branches/*/result.json")]
            for row in rows:
                self.assertTrue(row["delivery_verified"])
                if row["worker_type"] == "existing":
                    self.assertEqual(row["start_session"]["session_id"], "rep-00/E")
                    self.assertTrue(row["start_session"]["history"])
                else:
                    self.assertFalse(row["start_session"]["history"])
                events = row["events"]
                log = output / "rep-00/branches" / row["branch_id"] / "tool_events.jsonl"
                self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], events)
            for worker in H.WORKER_TYPES:
                for task in H.TASKS:
                    paired = [r for r in rows if r["briefing"] == "briefed" and r["worker_type"] == worker and r["task"] == task]
                    self.assertEqual(len({r["brief_hash"] for r in paired}), 1)
            new_pin = next(r for r in rows if r["briefing"] == "briefed" and r["arm"] == "creation_pin" and r["worker_type"] == "new" and r["task"] == "patch")
            new_refresh = next(r for r in rows if r["briefing"] == "briefed" and r["arm"] == "refreshed_store" and r["worker_type"] == "new" and r["task"] == "patch")
            self.assertEqual(new_pin["requests"][0]["messages"], new_refresh["requests"][0]["messages"])
            unbriefed = [r for r in rows if r["briefing"] == "unbriefed"]
            self.assertEqual(len(unbriefed), 12)
            for row in unbriefed:
                self.assertIsNone(row["brief_hash"])
                self.assertEqual(row["relay_user_message_ids"], [])
                sent = row["requests"][0]["messages"]
                self.assertIn(H.work_order_only(row["task"]), [m.get("content") for m in sent])
                self.assertFalse(any(H.AMENDMENT in str(m.get("content")) for m in sent[1:]))
            # Only the delivery arm controls whether an unbriefed worker sees R1.
            blocks = {(r["arm"], r["worker_type"]): r["requests"][0]["messages"][0]["content"] for r in unbriefed}
            self.assertIn(H.R1, blocks["refreshed_store", "existing"])
            self.assertNotIn(H.R1, blocks["manager_relay", "existing"])
            self.assertNotIn(H.R1, blocks["creation_pin", "existing"])
            self.assertNotIn(H.R0, blocks["manager_relay", "new"])
            self.assertNotIn(H.R1, blocks["manager_relay", "new"])
            # Deliberate score tampering cannot silently enter the summary.
            path = next(output.glob("rep-*/branches/*/result.json"))
            row = json.loads(path.read_text())
            row["score"]["task_success"] = False
            save(path, row)
            with self.assertRaises(ValueError):
                analyze(output)

    def test_manager_schema_retry_is_bounded_and_has_no_rule_hint(self):
        class Invalid:
            def __init__(self):
                self.messages = []
            def complete(self, messages, **kwargs):
                self.messages.append(copy.deepcopy(messages))
                return {"choices": [{"message": {"content": '{"brief":"x","relay_user_message_ids":["U1","U0"]}'}, "finish_reason": "stop"}]}
        client = Invalid()
        result = prepare_brief(client, "new", "patch", "test", 1)
        self.assertEqual(result["status"], "manager_protocol_error")
        self.assertEqual(len(client.messages), 2)
        self.assertIn("unique and chronological", client.messages[1][-1]["content"])
        self.assertNotIn(H.R1, client.messages[1][-1]["content"])

    def test_missing_credentials_fail_before_output_creation(self):
        from provider import ProviderError
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "never-created"
            with patch.object(sys, "argv", ["run.py", "--live", "--output", str(output)]), patch("provider.load_key", side_effect=ProviderError("Not configured")):
                with self.assertRaises(ProviderError):
                    main()
            self.assertFalse(output.exists())

    def test_no_live_flag_never_loads_credentials_or_creates_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "never-created"
            with patch.object(sys, "argv", ["run.py", "--output", str(output)]), patch("provider.load_key") as key, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 2)
            key.assert_not_called()
            self.assertFalse(output.exists())

    def test_manager_json_in_one_markdown_fence_is_accepted(self):
        class Fenced:
            def complete(self, messages, **kwargs):
                body = json.dumps({"brief": "Do the work.", "relay_user_message_ids": ["U1"]})
                return {"choices": [{"message": {"content": "```json\n" + body + "\n```"}, "finish_reason": "stop"}]}
        result = prepare_brief(Fenced(), "existing", "patch", "test", 0)
        self.assertEqual(result["status"], "valid")
        self.assertTrue(result["attempts"][0]["fence_stripped"])

    def test_text_around_a_fence_is_still_rejected(self):
        class Chatty:
            def complete(self, messages, **kwargs):
                body = json.dumps({"brief": "Do the work.", "relay_user_message_ids": ["U1"]})
                return {"choices": [{"message": {"content": "Here you go:\n```json\n" + body + "\n```"}, "finish_reason": "stop"}]}
        self.assertEqual(prepare_brief(Chatty(), "existing", "patch", "test", 0)["status"], "manager_protocol_error")

    def test_delivery_check_detects_missing_payload(self):
        text = H.delegation("patch", {"brief": "Work", "relay_user_message_ids": ["U1"]})
        record = {"supplied_rule_version": "R1", "messages": [{"role": "system", "content": H.WORKER_SYSTEM + H.rule_block("R1")}]}
        self.assertFalse(delivery_check({"requests": [record]}, "R1", text))


if __name__ == "__main__":
    unittest.main()
