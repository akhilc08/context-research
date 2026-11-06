from __future__ import annotations

import json
import unittest
from pathlib import Path

from bench import history

FIXTURE = Path(__file__).parent / "fixtures" / "bench" / "sample.traj.json"


def _calls(messages):
    return [c for m in messages for c in (m.get("tool_calls") or [])]


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.raw = history.load_trajectory(FIXTURE)

    def test_load_returns_message_list(self):
        self.assertIsInstance(self.raw, list)
        self.assertEqual(self.raw[1]["role"], "user")

    def test_task_statement_is_first_user_message(self):
        msgs = history.to_worker_messages(self.raw, call_prefix="p-")
        self.assertEqual(msgs[0]["role"], "user")
        self.assertIn("Widget cache returns stale", msgs[0]["content"])
        self.assertNotIn("system", [m["role"] for m in msgs])

    def test_first_user_message_is_problem_statement_only(self):
        """mini-swe-agent's instructions (do not modify tests, submit protocol) would contradict the rules."""
        msgs = history.to_worker_messages(self.raw, call_prefix="p-")
        first = msgs[0]["content"]
        self.assertTrue(first.startswith("Widget cache returns stale entries after reset"))
        for banned in ("<instructions>", "DO NOT MODIFY", "MODIFY source files", "/testbed",
                       history.SUBMIT_MARKER, "<pr_description>", "Consider the following PR description"):
            self.assertNotIn(banned, first)
        self.assertEqual(sum(m["role"] == "user" for m in msgs), 1)

    def test_testbed_rewritten_to_workdir(self):
        fb = history.filler_block("inst-1", self.raw, workdir="/widgets")
        text = json.dumps(fb.worker) + json.dumps(fb.manager)
        self.assertNotIn("/testbed", text)
        commands = [json.loads(c["function"]["arguments"])["command"] for c in _calls(fb.worker)]
        self.assertTrue(commands[0].startswith("cd /widgets && "))
        raw = [{"role": "user", "content": "t"},
               {"role": "assistant", "content": "in /testbed now", "tool_calls": [self._call("a", json.dumps(
                   {"command": "ls /testbed/src /testbed2 /testbedx"}))]},
               {"role": "tool", "tool_call_id": "a", "content": "<returncode>0</returncode>\n<output>\n/testbed/src/a.py\n</output>"},
               {"role": "assistant", "content": "fin"}]
        msgs = history.to_worker_messages(raw, call_prefix="q-", workdir="/r")
        self.assertEqual(json.loads(msgs[1]["tool_calls"][0]["function"]["arguments"])["command"],
                         "ls /r/src /testbed2 /testbedx")
        self.assertEqual(msgs[1]["content"], "in /r now")
        self.assertEqual(json.loads(msgs[2]["content"])["output"], "/r/src/a.py\n")

    def test_replayed_call_ids_are_sanitized(self):
        iid = "own.er__re.po-" + "x" * 80 + "-12"
        fb = history.filler_block(iid, self.raw, workdir="/r")
        ids = [c["id"] for c in _calls(fb.worker) + _calls(fb.manager)]
        ids += [m["tool_call_id"] for m in fb.worker + fb.manager if m["role"] == "tool"]
        self.assertTrue(ids)
        for i in ids:
            self.assertRegex(i, r"^[A-Za-z0-9_-]{1,64}$")
        worker_ids = [c["id"] for c in _calls(fb.worker)]
        self.assertEqual(len(worker_ids), len(set(worker_ids)))

    def test_call_ids_unique_prefixed_and_paired(self):
        msgs = history.to_worker_messages(self.raw, call_prefix="p-")
        calls = _calls(msgs)
        self.assertGreaterEqual(len(calls), 3)
        ids = [c["id"] for c in calls]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i.startswith("p-") for i in ids))
        tool_ids = [m["tool_call_id"] for m in msgs if m["role"] == "tool"]
        self.assertEqual(sorted(tool_ids), sorted(ids))
        for c in calls:
            self.assertEqual(c["type"], "function")
            self.assertEqual(c["function"]["name"], history.RUN_COMMAND)
            self.assertIn("command", json.loads(c["function"]["arguments"]))

    def test_tool_result_is_json_with_exit_code_and_output(self):
        msgs = history.to_worker_messages(self.raw, call_prefix="p-")
        first = next(m for m in msgs if m["role"] == "tool")
        body = json.loads(first["content"])
        self.assertEqual(set(body), {"exit_code", "output"})
        self.assertEqual(body["exit_code"], 0)

    def test_ends_with_closing_assistant_text(self):
        msgs = history.to_worker_messages(self.raw, call_prefix="p-")
        self.assertEqual(msgs[-1]["role"], "assistant")
        self.assertNotIn("tool_calls", msgs[-1])
        self.assertTrue(msgs[-1]["content"].strip())

    def test_step_without_command_makes_no_tool_call(self):
        raw = [{"role": "user", "content": "task"},
               {"role": "assistant", "content": "thinking out loud"},
               {"role": "assistant", "content": "done here"}]
        msgs = history.to_worker_messages(raw, call_prefix="q-")
        self.assertEqual(_calls(msgs), [])
        self.assertEqual(msgs[-1]["content"], "done here")

    def test_empty_trajectory_closing_fallback(self):
        msgs = history.to_worker_messages([{"role": "user", "content": "t"}], call_prefix="q-")
        self.assertEqual(msgs[-1], {"role": "assistant", "content": "Task finished."})

    def test_long_observation_keeps_tail(self):
        long = "<returncode>2</returncode>\n<output>\n" + "A" * 3000 + "TAILEND\n</output>"
        raw = [{"role": "user", "content": "t"},
               {"role": "assistant", "content": "", "tool_calls": [
                   {"id": "x", "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": "ls"})}}]},
               {"role": "tool", "tool_call_id": "x", "content": long},
               {"role": "assistant", "content": "ok"}]
        msgs = history.to_worker_messages(raw, call_prefix="q-")
        body = json.loads(next(m for m in msgs if m["role"] == "tool")["content"])
        self.assertEqual(body["exit_code"], 2)
        self.assertEqual(len(body["output"]), 2000)
        self.assertTrue(body["output"].endswith("TAILEND\n"))

    def _call(self, cid, args='{"command": "ls"}'):
        c = {"type": "function", "function": {"name": "bash", "arguments": args}}
        if cid is not None:
            c["id"] = cid
        return c

    def _assert_paired(self, msgs):
        calls = [c["id"] for c in _calls(msgs)]
        tools = [m["tool_call_id"] for m in msgs if m["role"] == "tool"]
        self.assertEqual(sorted(calls), sorted(tools))
        for m in msgs:
            if m["role"] == "assistant" and "tool_calls" not in m:
                self.assertTrue(m["content"].strip())

    def test_missing_observation_drops_call(self):
        raw = [{"role": "user", "content": "t"},
               {"role": "assistant", "content": "", "tool_calls": [self._call("a")]},
               {"role": "assistant", "content": "fin"}]
        msgs = history.to_worker_messages(raw, call_prefix="q-")
        self._assert_paired(msgs)
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant"])

    def test_bad_json_arguments_dropped(self):
        raw = [{"role": "user", "content": "t"},
               {"role": "assistant", "content": "x", "tool_calls": [self._call("a", "{not json")]},
               {"role": "tool", "tool_call_id": "a", "content": "<returncode>0</returncode>"},
               {"role": "assistant", "content": "fin"}]
        msgs = history.to_worker_messages(raw, call_prefix="q-")
        self._assert_paired(msgs)
        self.assertEqual(_calls(msgs), [])

    def test_call_without_id_dropped(self):
        raw = [{"role": "user", "content": "t"},
               {"role": "assistant", "content": "", "tool_calls": [self._call(None)]},
               {"role": "tool", "tool_call_id": None, "content": "<returncode>0</returncode>"},
               {"role": "assistant", "content": "fin"}]
        msgs = history.to_worker_messages(raw, call_prefix="q-")
        self._assert_paired(msgs)
        self.assertEqual(_calls(msgs), [])

    def test_truncated_after_command(self):
        raw = [{"role": "user", "content": "t"},
               {"role": "assistant", "content": "", "tool_calls": [self._call("a")]},
               {"role": "tool", "tool_call_id": "a", "content": "<returncode>0</returncode>"},
               {"role": "assistant", "content": "", "tool_calls": [self._call("b")]}]
        msgs = history.to_worker_messages(raw, call_prefix="q-")
        self._assert_paired(msgs)
        self.assertEqual(len(_calls(msgs)), 1)
        self.assertEqual(msgs[-1]["content"], "Task finished.")

    def test_multiple_calls_in_one_message(self):
        raw = [{"role": "user", "content": "t"},
               {"role": "assistant", "content": "", "tool_calls": [
                   self._call("a", '{"command": "ls"}'), self._call("b", '{"command": "pwd"}')]},
               {"role": "tool", "tool_call_id": "a", "content": "<returncode>0</returncode>\n<output>\nx\n</output>"},
               {"role": "tool", "tool_call_id": "b", "content": "<returncode>1</returncode>\n<output>\ny\n</output>"},
               {"role": "assistant", "content": "fin"}]
        msgs = history.to_worker_messages(raw, call_prefix="q-")
        self._assert_paired(msgs)
        self.assertEqual(len(msgs[1]["tool_calls"]), 2)
        self.assertEqual([json.loads(m["content"])["exit_code"] for m in msgs if m["role"] == "tool"], [0, 1])

    def test_manager_block(self):
        block = history.manager_block("fix the bug", "all fixed", "m1")
        self.assertEqual([m["role"] for m in block], ["user", "assistant", "tool", "assistant"])
        call = block[1]["tool_calls"][0]
        self.assertEqual(call["id"], "m1")
        self.assertEqual(call["function"]["name"], "message_worker")
        self.assertEqual(json.loads(call["function"]["arguments"]), {"message": "fix the bug"})
        self.assertEqual(block[2]["tool_call_id"], "m1")
        self.assertEqual(json.loads(block[2]["content"]),
                         {"worker": "worker-1", "status": "finished", "reply": "all fixed"})
        self.assertEqual(block[3]["content"], "Done.")

    def test_filler_block_reply_is_final_assistant_text(self):
        fb = history.filler_block("inst-1", self.raw, workdir="/r")
        self.assertEqual(fb.instance_id, "inst-1")
        closing = fb.worker[-1]["content"]
        reply = json.loads(fb.manager[2]["content"])["reply"]
        self.assertEqual(reply, closing)
        self.assertIn("Widget cache", fb.manager[0]["content"])
        self.assertNotIn("<instructions>", fb.manager[0]["content"])
        ids = [c["id"] for c in _calls(fb.worker)]
        self.assertTrue(all("inst-1" in i for i in ids))


if __name__ == "__main__":
    unittest.main()
