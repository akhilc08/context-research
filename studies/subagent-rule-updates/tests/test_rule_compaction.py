"""Offline tests for rule_compaction.py with a scripted worker and summarizer."""
import json
import tempfile
from unittest import mock
import unittest
from pathlib import Path

import compaction as C
import pi_compaction as PI
import rule_compaction as RC
import scenarios as S

CONFIG = {"repetitions": 1, "order_seed": 1, "max_worker_calls": 6, "filler_tasks": 3, "log_lines": 20,
          "compact_threshold_chars": 1500, "min_compactions": 1, "conditions": ["relay_no_compact", "relay_compact"]}


def call(name, args, n):
    return {"id": f"r{n}", "choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
            "tool_calls": [{"id": f"c{n}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}]}


def reply(text, n):
    return {"id": f"r{n}", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 10}}


class Scripted:
    """The worker follows the latest version of each rule found anywhere in its context.
    The summarizer keeps the amendment unless drop_amendment is set."""

    def __init__(self, drop_amendment=False):
        self.drop, self.n, self.summaries = drop_amendment, 0, 0

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.n += 1
        if messages[0]["content"] in (C.SUMMARIZER_SYSTEM, PI.P["SUMMARIZATION_SYSTEM_PROMPT"]):
            self.summaries += 1
            text = messages[1]["content"]
            kept = [S.RULES[r][v] for r in S.RULES for v in ("v1", "v2") if S.RULES[r][v] in text]
            if self.drop:
                kept = [k for k in kept if k not in (S.RULES["changelog"]["v2"], S.RULES["config_values"]["v2"])]
            return reply("Rules: " + " ".join(kept), self.n)
        context = "\n".join(m.get("content") or "" for m in messages if m["role"] in ("system", "user"))
        last = max(i for i, m in enumerate(messages) if m["role"] == "user")
        step = sum(m["role"] == "assistant" for m in messages[last + 1:])
        task = next((t for t, spec in S.TASKS.items() if spec["text"] in messages[last]["content"]), None)
        if task is None:
            return reply("Read-only report.", self.n)
        current = {r: "v2" if S.RULES[r]["v2"] in context else "v1" if S.RULES[r]["v1"] in context else None for r in S.RULES}
        spec = S.TASKS[task]
        writes = []
        if current["config_values"] == "v2":
            writes.append((spec["module"], "from app import settings\n" + S.FIXTURE[spec["module"]] + "X = settings.get('L', 1)\n"))
        elif current["config_values"] == "v1":
            writes += [("app/config.py", S.FIXTURE["app/config.py"] + "LIMIT = 1\n"),
                       (spec["module"], "from app import config\n" + S.FIXTURE[spec["module"]] + "X = config.LIMIT\n")]
        if current["changelog"] == "v2":
            writes.append(("docs/HISTORY.md", f"{spec['ticket']}: change\n"))
        elif current["changelog"] == "v1":
            writes.append(("CHANGELOG.md", "- change\n"))
        if step < len(writes):
            return call("write_file", {"path": writes[step][0], "content": writes[step][1]}, self.n)
        return reply("Done.", self.n)


class RuleCompactionTest(unittest.TestCase):
    def test_messages(self):
        self.assertIn(S.RULES["changelog"]["v1"], RC.inline_u0_message())
        self.assertIn(S.RULES["config_values"]["v1"], RC.inline_u0_message())
        self.assertIn("rule 2", RC.relay_message("config_values"))
        self.assertIn(S.RULES["config_values"]["v2"], RC.relay_message("config_values"))
        self.assertNotIn("rule", RC.task_message("low_stock").split("[Manager briefing")[0].lower().replace("ticket", ""))

    def run_study(self, client):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        RC.execute(client, out, CONFIG)
        return out, RC.analyze(out)

    def test_kept_amendment_is_followed_in_both_conditions(self):
        out, summary = self.run_study(Scripted())
        self.assertEqual(summary["branches"], 8)
        for key, cell in summary["cells"].items():
            self.assertEqual((cell["n"], cell["changed_outcomes"], cell["unchanged_v1"]), (2, {"v2": 2}, 2), key)
        record = json.loads((out / "rep-00/prep/changelog__relay_compact/record.json").read_text())
        self.assertTrue(record["setup_valid"] and record["compactions"])
        self.assertTrue(record["compactions"][-1]["markers"]["changelog_v2"])
        self.assertFalse(json.loads((out / "rep-00/prep/changelog__relay_no_compact/record.json").read_text())["compactions"])
        # Filler steps were read-only, so their workspace copies were removed.
        self.assertFalse((out / "rep-00/prep/changelog__relay_compact/step-01/workspace").exists())

    def test_dropped_amendment_shows_as_stale(self):
        _, summary = self.run_study(Scripted(drop_amendment=True))
        for change in RC.CHANGES:
            self.assertEqual(summary["cells"][f"{change}__relay_compact"]["changed_outcomes"], {"v1": 2})
            self.assertEqual(summary["cells"][f"{change}__relay_no_compact"]["changed_outcomes"], {"v2": 2})
            self.assertEqual(summary["summaries"][f"{change}__relay_compact"]["old_only"], 1)


class PiConditionTest(unittest.TestCase):
    def test_pi_condition_compacts_on_schedule(self):
        config = {**CONFIG, "filler_tasks": 6, "pi_compact_after_steps": [2, 4], "conditions": ["relay_compact_pi"]}
        # Scripted workers write tiny histories, so shrink the verbatim tail to force real cuts.
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(PI, "KEEP_RECENT_TOKENS", 20):
            out = Path(tmp)
            RC.execute(Scripted(), out, config)
            record = json.loads((out / "rep-00/prep/changelog__relay_compact_pi/record.json").read_text())
            self.assertTrue(record["setup_valid"])
            self.assertEqual([c["after_step"] for c in record["compactions"]], [2, 4])
            self.assertTrue(record["final_history"][0]["content"].startswith(PI.P["COMPACTION_SUMMARY_PREFIX"]))
            summary = RC.analyze(out)
            self.assertEqual(summary["cells"]["changelog__relay_compact_pi"]["changed_outcomes"], {"v2": 2})


class StoreAndReinsertTest(unittest.TestCase):
    def test_store_and_reinsert_survive_a_summarizer_that_drops_the_amendment(self):
        config = {**CONFIG, "compact_threshold_chars": 600, "conditions": ["store_compact", "reinsert_compact"]}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            RC.execute(Scripted(drop_amendment=True), out, config)
            summary = RC.analyze(out)
            for change in RC.CHANGES:
                for condition in ("store_compact", "reinsert_compact"):
                    cell = summary["cells"][f"{change}__{condition}"]
                    self.assertEqual((cell["changed_outcomes"], cell["unchanged_v1"]), ({"v2": 2}, 2), (change, condition))
            store = json.loads((out / "rep-00/prep/config_values__store_compact/record.json").read_text())
            self.assertNotIn(S.RULES["config_values"]["v1"], json.dumps(store["final_history"]))
            self.assertIn(S.RULES["config_values"]["v2"], store["system"])
            warm = json.loads((out / "rep-00/warmup-store.json").read_text())
            self.assertIn(S.RULES["config_values"]["v1"], warm["system"])
            reinsert = json.loads((out / "rep-00/prep/changelog__reinsert_compact/record.json").read_text())
            self.assertEqual(reinsert["final_history"][1]["content"], RC.reinsert_message("changelog"))


if __name__ == "__main__":
    unittest.main()
