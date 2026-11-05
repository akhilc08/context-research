"""Offline tests for the relay sessions with a scripted manager and workers."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import relay as R
import scenarios as S
import worker as W


def call(name, args, n):
    return {"id": f"r{n}", "choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
            "tool_calls": [{"id": f"c{n}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}]}


def reply(text, n):
    return {"id": f"r{n}", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}]}


class ScriptedTeam:
    """Manager relays (or not) by echoing user turns; workers follow the latest rule text they have seen."""

    def __init__(self, relay=True):
        self.relay, self.n = relay, 0

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.n += 1
        last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
        step = sum(m["role"] == "assistant" for m in messages[last_user + 1:])
        text = messages[last_user]["content"]
        if messages[0]["content"] == R.MANAGER_SYSTEM:
            turn = sum(m["role"] == "user" for m in messages) - 1
            if step:
                return reply("Done.", self.n)
            if turn == 1 and not self.relay:
                return reply("Noted.", self.n)
            return call("message_worker", {"message": text}, self.n)
        seen = "\n".join(m["content"] for m in messages if m["role"] == "user")
        task = next((t for t, spec in S.TASKS.items() if spec["text"] in text), None)
        if task is None:
            return reply("Noted.", self.n)
        current = {rule: "v2" if v["v2"] in seen else "v1" if v["v1"] in seen else None for rule, v in S.RULES.items()}
        workspace_writes = []
        spec = S.TASKS[task]
        module_text = S.FIXTURE[spec["module"]] + f"\n# {spec['literals'][0]}\n"
        if current["config_values"] == "v1":
            module_text = "from app import config\n" + S.FIXTURE[spec["module"]] + "\nX = config.LIMIT\n"
            workspace_writes.append(("app/config.py", S.FIXTURE["app/config.py"] + f"LIMIT_{task.upper()} = 1\n"))
        elif current["config_values"] == "v2":
            module_text = "from app import settings\n" + S.FIXTURE[spec["module"]] + "\nX = settings.get('LIMIT', 1)\n"
        workspace_writes.append((spec["module"], module_text))
        if current["changelog"] == "v1":
            workspace_writes.append(("CHANGELOG.md", f"- {spec['ticket']}\n" * (1 + (task == "low_stock"))))
        elif current["changelog"] == "v2":
            workspace_writes.append(("docs/HISTORY.md", f"{spec['ticket']}: change\n"))
        if step < len(workspace_writes):
            path, content = workspace_writes[step]
            return call("write_file", {"path": path, "content": content}, self.n)
        return reply("Finished.", self.n)


def run(client, change):
    with tempfile.TemporaryDirectory() as tmp:
        return R.run_session(client, Path(tmp) / "s", change, {"max_manager_calls": 4, "max_worker_calls": 6}, "t")


class RelayTest(unittest.TestCase):
    def test_user_turns(self):
        turns = R.user_turns("config_values")
        self.assertIn(S.RULES["changelog"]["v1"], turns[0])
        self.assertIn("rule 2", turns[1])
        self.assertIn(S.RULES["config_values"]["v2"], turns[1])
        self.assertIn("INV-215", turns[2])

    def test_relayed_change_is_followed(self):
        for change in R.CHANGES:
            record = run(ScriptedTeam(relay=True), change)
            score = record["score"]
            self.assertEqual(record["status"], "finished")
            self.assertEqual((score["relayed"], score["relay_turn"], score["second_task_delegated"]), (True, 1, True))
            self.assertEqual(score["first_task"], {"changelog": "v1", "config_values": "v1"})
            self.assertEqual((score["changed_rule_outcome"], score["unchanged_rule_outcome"]), ("v2", "v1"), change)

    def test_missing_relay_leaves_worker_stale(self):
        score = run(ScriptedTeam(relay=False), "changelog")["score"]
        self.assertFalse(score["relayed"])
        self.assertEqual((score["changed_rule_outcome"], score["unchanged_rule_outcome"]), ("v1", "v1"))

    def test_team_rejects_bad_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            team = R.Team(ScriptedTeam(), W.Workspace(Path(tmp) / "w", S.FIXTURE), "t", 4)
            self.assertIn("error", team.execute("message_worker", {"name": "x", "message": "hi"}, 0))
            self.assertIn("error", team.execute("message_worker", {"message": " "}, 0))
            self.assertIn("error", team.execute("spawn_worker", {"message": "hi"}, 0))

    def test_earlier_changelog_entries_do_not_count(self):
        after_first = dict(S.FIXTURE, **{"CHANGELOG.md": "- INV-212\n"})
        self.assertEqual(S.classify_changelog(after_first, "low_stock", after_first)["outcome"], "none")
        grown = dict(after_first, **{"CHANGELOG.md": "- INV-212\n- INV-215\n"})
        self.assertEqual(S.classify_changelog(grown, "low_stock", after_first)["outcome"], "v1")

    def test_execute_and_analyze_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            R.execute(ScriptedTeam(), out, {"repetitions": 2, "order_seed": 1, "max_manager_calls": 4, "max_worker_calls": 6})
            summary = R.analyze(out)
            self.assertEqual(summary["sessions"], 4)
            for change in R.CHANGES:
                cell = summary["changes"][change]
                self.assertEqual((cell["n"], cell["relayed"], cell["delegated"], cell["changed_outcomes"], cell["unchanged_v1"]),
                                 (2, 2, 2, {"v2": 2}, 2))


if __name__ == "__main__":
    unittest.main()
