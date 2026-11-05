"""Offline tests for rule_compaction.py with a scripted worker and summarizer."""
import json
import tempfile
import unittest
from pathlib import Path

import compaction as C
import rule_compaction as RC
import scenarios as S

CONFIG = {"repetitions": 1, "order_seed": 1, "max_worker_calls": 6, "filler_tasks": 3, "log_lines": 20,
          "compact_threshold_chars": 1500, "min_compactions": 1, "conditions": list(RC.CONDITIONS)}


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
        if messages[0]["content"] == C.SUMMARIZER_SYSTEM:
            self.summaries += 1
            text = messages[1]["content"]
            kept = [S.RULES[r][v] for r in S.RULES for v in ("v1", "v2") if S.RULES[r][v] in text]
            if self.drop:
                kept = [k for k in kept if k not in (S.RULES["changelog"]["v2"], S.RULES["config_values"]["v2"])]
            return reply("Rules: " + " ".join(kept), self.n)
        context = "\n".join(m.get("content") or "" for m in messages if m["role"] == "user")
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
            self.assertEqual(summary["summaries"][change]["old_only"], 1)


if __name__ == "__main__":
    unittest.main()
