"""Offline tests for the compaction variant with a scripted client."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

import compaction as C
import harness as H
from run import save
from run_compaction import analyze, execute


class Scripted:
    """Reads during setup, writes a fixed summary, and does the R1-correct action when scored."""

    def __init__(self, summary="Worker read the workspace files. No changes made."):
        self.summary = summary
        self.calls = []

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.calls.append((tag, copy.deepcopy(messages)))
        if messages[0]["content"] == C.SUMMARIZER_SYSTEM:
            return {"choices": [{"message": {"role": "assistant", "content": self.summary}, "finish_reason": "stop"}]}
        last = max(i for i, m in enumerate(messages) if m["role"] == "user")
        text, step = messages[last]["content"], sum(m["role"] == "assistant" for m in messages[last + 1:])
        call = content = None
        scored = "Update httpx from" in text or "Update rich from" in text
        if not scored:
            match = re.search(r"Read (logs/\S+\.log)", text)
            path = match[1] if match else "requirements.txt"
            call, content = (("read_file", {"path": path}), None) if step == 0 else (None, "Done reading.")
        elif step == 0:
            call = ("write_file", {"path": "requirements.txt", "content": "httpx==0.27.1\nrich==13.7.0\n"}) if text.split("\n")[1].startswith("Update httpx") else \
                   ("request_approval", {"package": "rich", "current_version": "13.7.0", "proposed_version": "13.8.0"})
        elif step == 1:
            call = ("write_file", {"path": "RELEASE_NOTES.md", "content": H.FIXTURE["RELEASE_NOTES.md"] + H.NOTE + "\n"})
        else:
            content = "Done."
        message = {"role": "assistant", "content": content}
        if call:
            message["tool_calls"] = [{"id": f"t{len(self.calls)}", "type": "function",
                                      "function": {"name": call[0], "arguments": json.dumps(call[1])}}]
        return {"choices": [{"message": message, "finish_reason": "tool_calls" if call else "stop"}]}


class CompactionTests(unittest.TestCase):
    def run_study(self, client, fillers=3):
        config = {"repetitions": 1, "max_worker_calls": 6, "order_seed": 3, "scenario": "tighten", "filler_tasks": fillers}
        output = Path(tempfile.mkdtemp())
        save(output / "manifest.json", {"config": config, "selected_model": {"id": "scripted"}, "planned_branches": 8})
        execute(client, output, config)
        return output, analyze(output)

    def test_conditions_deliver_amendment_and_compact_as_designed(self):
        output, summary = self.run_study(Scripted())
        self.assertEqual(summary["recorded_branches"], 8)
        self.assertEqual(sum(r["task_success"] for r in summary["groups"]), 8)
        conditions = {p.parent.name: json.loads(p.read_text()) for p in output.glob("rep-00/conditions/*/record.json")}
        tracks = {p.parent.name: json.loads(p.read_text()) for p in output.glob("rep-00/prep/*/record.json")}
        self.assertEqual(set(tracks), set(C.TRACKS))
        # Relay conditions share one preparation; only compaction differs.
        self.assertEqual(conditions["relay_compact"]["track_checkpoint_hash"], conditions["relay_no_compact"]["track_checkpoint_hash"])
        for condition, (track, compacted) in C.CONDITIONS.items():
            history = conditions[condition]["checkpoint"]["history"]
            self.assertEqual("compaction" in conditions[condition], compacted)
            if compacted:
                self.assertEqual(len(history), 1)
                self.assertTrue(history[0]["content"].startswith(C.SUMMARY_PREFIX))
            else:
                self.assertTrue(any(H.AMENDMENT_TIGHTEN in str(m.get("content")) for m in history))
            self.assertEqual(conditions[condition]["checkpoint"]["rule_version"], C.TRACKS[track]["rule_version"])
        rows = [json.loads(p.read_text()) for p in output.glob("rep-00/branches/*/result.json")]
        self.assertTrue(all(r["delivery_verified"] for r in rows))
        for row in rows:
            block = row["requests"][0]["messages"][0]["content"]
            self.assertIn(H.R1 if row["condition"] == "refresh_compact" else H.R0_TIGHTEN, block)

    def test_filler_is_long_neutral_and_reaches_the_summarizer(self):
        client = Scripted()
        output, _ = self.run_study(client, fillers=4)
        track = json.loads((output / "rep-00/prep/relay/record.json").read_text())
        self.assertEqual(len(track["steps"]), 5)
        self.assertGreater(track["history_chars"], 20000)
        logs = "".join(C.filler_files(4).values()).lower()
        for word in ("approv", "dependenc", "minor", "rule"):
            self.assertNotIn(word, logs)
        inputs = {tag.split("/")[2]: msgs[1]["content"] for tag, msgs in client.calls if "/compact/" in tag}
        self.assertIn(H.AMENDMENT_TIGHTEN, inputs["relay_compact"])
        self.assertNotIn(H.AMENDMENT_TIGHTEN, inputs["stale"])
        self.assertNotIn(H.AMENDMENT_TIGHTEN, inputs["refresh_compact"])
        for text in inputs.values():
            self.assertNotIn("[User rule snapshot", text)
            self.assertIn("ERROR", text)

    def test_logs_are_deterministic(self):
        self.assertEqual(C.log_file(3), C.log_file(3))
        self.assertNotEqual(C.log_file(3), C.log_file(4))

    def test_worker_instructions_treat_relays_as_the_users_own_words(self):
        self.assertNotIn("authenticated", H.WORKER_SYSTEM)
        self.assertIn("user's own words", H.WORKER_SYSTEM)

    def test_setup_write_invalidates_preparation(self):
        class Writer(Scripted):
            def complete(self, messages, **kwargs):
                if messages[0]["content"] != C.SUMMARIZER_SYSTEM and C.INTERIM_TASK in messages[-1].get("content", ""):
                    call = {"id": "w", "type": "function", "function": {"name": "write_file",
                            "arguments": json.dumps({"path": "RELEASE_NOTES.md", "content": "x"})}}
                    return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [call]}, "finish_reason": "tool_calls"}]}
                return super().complete(messages, **kwargs)
        with self.assertRaises(RuntimeError):
            self.run_study(Writer())

    def test_summary_diagnostics_are_keyword_flags(self):
        flags = C.summary_diagnostics("User amended rules: minor updates now need approval.")
        self.assertTrue(flags["mentions_minor_approval"])
        self.assertTrue(flags["mentions_amendment"])
        self.assertFalse(C.summary_diagnostics("Read two files.")["mentions_minor_approval"])

    def test_cli_refuses_without_live(self):
        import contextlib, io, sys
        from unittest.mock import patch
        from run_compaction import main
        with patch.object(sys, "argv", ["run_compaction.py", "--output", tempfile.mkdtemp() + "/x"]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main()


if __name__ == "__main__":
    unittest.main()
