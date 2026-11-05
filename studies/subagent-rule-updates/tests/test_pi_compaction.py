"""Offline tests for the pi compaction port."""
import json
import unittest
from pathlib import Path

import pi_compaction as PI

PI_BINARY = Path.home() / ".local/share/mise/installs/pi/1.5.0/pi/pi"


def user(text):
    return {"role": "user", "content": text}


def assistant(text=None, calls=()):
    msg = {"role": "assistant", "content": text}
    if calls:
        msg["tool_calls"] = [{"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}} for i, (n, a) in enumerate(calls)]
    return msg


def tool(text):
    return {"role": "tool", "tool_call_id": "c0", "content": text}


def step(i, size=8000):
    """One delegated task: user order, a read call, a large result, a short answer. About size/4 tokens."""
    return [user(f"Task {i}"), assistant(None, [("read_file", {"path": f"logs/{i}.log"})]), tool("x" * size), assistant(f"Answer {i}")]


class Recorder:
    def __init__(self):
        self.prompts = []

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.prompts.append((messages[0]["content"], messages[1]["content"]))
        return {"id": "s", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": f"SUMMARY {len(self.prompts)}"}}]}


class PiCompactionTest(unittest.TestCase):
    def test_serialization_matches_pi_format(self):
        text = PI.serialize_conversation([user("hi"), assistant("ok", [("read_file", {"path": "a.py"})]), tool("y" * 2005), user("")])
        self.assertEqual(text, '[User]: hi\n\n[Assistant]: ok\n\n[Assistant tool calls]: read_file(path="a.py")\n\n'
                               "[Tool result]: " + "y" * 2000 + "\n\n[... 5 more characters truncated]")

    def test_cut_keeps_recent_tokens_at_a_user_boundary(self):
        history = [m for i in range(10) for m in step(i)]  # each step about 2,000 tokens
        cut = PI.find_cut_point(history, 0, len(history))
        kept = sum(PI.estimate_tokens(m) for m in history[cut["first_kept"]:])
        # pi stops at the message that crosses the budget, then moves forward to the next valid cut
        # point. Tool results are not cut points, so the kept tail can fall just short of 20k tokens.
        self.assertGreater(kept, PI.KEEP_RECENT_TOKENS - 2100)
        self.assertGreaterEqual(kept + PI.estimate_tokens(history[cut["first_kept"] - 1]), PI.KEEP_RECENT_TOKENS)
        self.assertEqual(history[cut["first_kept"]]["role"], "assistant")
        self.assertTrue(cut["split"])

    def test_rolling_compaction_uses_update_prompt_and_file_lists(self):
        client, state = Recorder(), PI.PiState()
        history = [user("RULE: log changes in docs/HISTORY.md")] + [m for i in range(12) for m in step(i)]
        history, first = PI.compact(client, history, state, "t0")
        self.assertFalse(first["skipped"])
        self.assertTrue(history[0]["content"].startswith("The conversation history before this point was compacted into the following summary:\n\n<summary>\n"))
        self.assertIn("RULE: log changes", client.prompts[0][1])
        self.assertTrue(client.prompts[0][1].startswith("<conversation>\n[User]: RULE"))
        self.assertIn("<read-files>\nlogs/0.log\n", first["summary"])
        n = len(client.prompts)
        history += [m for i in range(12, 24) for m in step(i)]
        history, second = PI.compact(client, history, state, "t1")
        update_prompts = [p for _, p in client.prompts[n:] if "<previous-summary>" in p]
        self.assertTrue(update_prompts and update_prompts[0].rstrip().endswith(PI.P["UPDATE_SUMMARIZATION_PROMPT"].rstrip()))
        self.assertNotIn("[User]: The conversation history before", "".join(p for _, p in client.prompts[n:]))
        self.assertTrue(all(s == PI.P["SUMMARIZATION_SYSTEM_PROMPT"] for s, _ in client.prompts))

    @unittest.skipUnless(PI_BINARY.exists(), "pi 1.5.0 binary not installed")
    def test_prompts_match_pi_binary(self):
        data = PI_BINARY.read_bytes().decode("utf8", "replace")
        for name in ("SUMMARIZATION_SYSTEM_PROMPT", "SUMMARIZATION_PROMPT", "UPDATE_SUMMARIZATION_INSTRUCTIONS",
                     "TURN_PREFIX_SUMMARIZATION_PROMPT", "COMPACTION_SUMMARY_PREFIX", "COMPACTION_SUMMARY_SUFFIX"):
            self.assertIn(f"{name} = `{PI.P[name]}`", data, name)


if __name__ == "__main__":
    unittest.main()
