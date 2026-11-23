import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bedrock_provider as B
import worker as W
from provider import BudgetExceeded, ProviderError

PRICES = {"input": 2.0, "output": 10.0, "cache_read": 0.2, "cache_write": 2.5}


class Error(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def converse_reply(content, stop="end_turn", inp=10, out=5, read=0, write=0):
    return {"output": {"message": {"role": "assistant", "content": content}}, "stopReason": stop,
            "usage": {"inputTokens": inp, "outputTokens": out, "cacheReadInputTokens": read, "cacheWriteInputTokens": write},
            "ResponseMetadata": {"RequestId": "req"}}


class FakeRuntime:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def converse(self, **request):
        self.requests.append(json.loads(json.dumps(request)))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


HISTORY = [
    {"role": "system", "content": "sys"},
    {"role": "user", "content": "do it"},
    {"role": "assistant", "content": None, "tool_calls": [
        {"id": "t1", "type": "function", "function": {"name": "read_file", "arguments": "{\"path\": \"a.py\"}"}},
        {"id": "t2", "type": "function", "function": {"name": "list_files", "arguments": "{}"}}]},
    {"role": "tool", "tool_call_id": "t1", "content": "{\"content\": \"x\"}"},
    {"role": "tool", "tool_call_id": "t2", "content": "{\"files\": []}"},
    {"role": "assistant", "content": "Done."},
    {"role": "user", "content": "summary"},
    {"role": "user", "content": "next task"},
]


class ConversionTests(unittest.TestCase):
    def test_to_converse(self):
        req = B.to_converse(HISTORY, W.TOOLS, cache=True)
        self.assertEqual(req["system"], [{"text": "sys"}, B.CACHE_POINT])
        roles = [t["role"] for t in req["messages"]]
        self.assertEqual(roles, ["user", "assistant", "user", "assistant", "user"])
        uses = req["messages"][1]["content"]
        self.assertEqual(uses[0]["toolUse"], {"toolUseId": "t1", "name": "read_file", "input": {"path": "a.py"}})
        self.assertEqual([b["toolResult"]["toolUseId"] for b in req["messages"][2]["content"]], ["t1", "t2"])
        # Two consecutive user messages are merged, and the cache point closes the last turn.
        self.assertEqual(req["messages"][4]["content"], [{"text": "summary"}, {"text": "next task"}, B.CACHE_POINT])
        self.assertEqual(req["toolConfig"]["tools"][0]["toolSpec"]["name"], "list_files")

    def test_no_cache(self):
        req = B.to_converse(HISTORY, None, cache=False)
        self.assertEqual(req["system"], [{"text": "sys"}])
        self.assertNotIn("toolConfig", req)
        self.assertNotIn(B.CACHE_POINT, req["messages"][-1]["content"])

    def test_from_converse(self):
        out = B.from_converse(converse_reply(
            [{"text": "Reading."}, {"toolUse": {"toolUseId": "t9", "name": "read_file", "input": {"path": "b"}}}],
            stop="tool_use", inp=3, out=4, read=100, write=20))
        choice = out["choices"][0]
        self.assertEqual(choice["finish_reason"], "tool_calls")
        self.assertEqual(choice["message"]["content"], "Reading.")
        self.assertEqual(json.loads(choice["message"]["tool_calls"][0]["function"]["arguments"]), {"path": "b"})
        self.assertEqual(out["usage"]["prompt_tokens"], 123)
        self.assertEqual(out["usage"]["prompt_tokens_details"], {"cached_tokens": 100, "cache_write_tokens": 20})

    def test_must_start_with_user(self):
        with self.assertRaises(ProviderError):
            B.to_converse([{"role": "assistant", "content": "hi"}], None, cache=False)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sleeps = []

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, replies, **kwargs):
        runtime = FakeRuntime(replies)
        options = {"budget_usd": 1.0, "max_calls": 10}
        options.update(kwargs)
        c = B.BedrockClient(Path(self.tmp.name) / "out", model="m", region="us-east-1", prices_per_mtok=PRICES,
                            runtime=runtime, sleep=self.sleeps.append, **options)
        return c, runtime

    def test_complete_accounts_cost(self):
        c, runtime = self.client([converse_reply([{"text": "ok"}], inp=1000, out=100, read=10000, write=500)])
        response = c.complete([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], tag="t")
        self.assertEqual(response["choices"][0]["message"]["content"], "ok")
        expected = (1000 * 2.0 + 10000 * 0.2 + 500 * 2.5 + 100 * 10.0) / 1e6
        s = c.summary()
        self.assertAlmostEqual(s["estimated_cost_usd"], expected)
        self.assertEqual(s["reserved_cost_usd"], 0.0)
        self.assertEqual((s["cached_tokens"], s["cache_write_tokens"], s["prompt_tokens"]), (10000, 500, 11500))
        self.assertEqual(runtime.requests[0]["inferenceConfig"], {"maxTokens": 4096, "temperature": 0.2})
        logged = (Path(self.tmp.name) / "out" / "requests.jsonl").read_text().splitlines()
        self.assertEqual(json.loads(logged[0])["tag"], "t")

    def test_throttle_retried_without_charge(self):
        c, _ = self.client([Error("ThrottlingException"), converse_reply([{"text": "ok"}])])
        c.complete([{"role": "user", "content": "u"}])
        s = c.summary()
        self.assertEqual((s["requests"], s["throttles_retried"], s["reserved_cost_usd"]), (2, 1, 0.0))
        self.assertEqual(self.sleeps, [15.0])

    def test_other_errors_stop(self):
        c, _ = self.client([Error("ValidationException")])
        with self.assertRaises(ProviderError):
            c.complete([{"role": "user", "content": "u"}])
        with self.assertRaisesRegex(ProviderError, "stopped"):
            c.complete([{"role": "user", "content": "u"}])

    def test_truncation_fails(self):
        c, _ = self.client([converse_reply([{"text": "par"}], stop="max_tokens")])
        with self.assertRaisesRegex(ProviderError, "length"):
            c.complete([{"role": "user", "content": "u"}])

    def test_caps(self):
        c, _ = self.client([], budget_usd=0.0001)
        with self.assertRaises(BudgetExceeded):
            c.complete([{"role": "user", "content": "u"}])

    def test_request_cap(self):
        tmp = Path(self.tmp.name) / "cap"
        c = B.BedrockClient(tmp, model="m", region="r", prices_per_mtok=PRICES, budget_usd=1.0, max_calls=1,
                            runtime=FakeRuntime([converse_reply([{"text": "ok"}])]), sleep=self.sleeps.append)
        c.complete([{"role": "user", "content": "u"}])
        with self.assertRaises(BudgetExceeded):
            c.complete([{"role": "user", "content": "u"}])

    def test_worker_runs_through_client(self):
        replies = [converse_reply([{"toolUse": {"toolUseId": "a1", "name": "list_files", "input": {}}}], stop="tool_use"),
                   converse_reply([{"text": "All done."}])]
        c, runtime = self.client(replies)
        ws = W.Workspace(Path(self.tmp.name) / "ws", {"app.py": "x = 1\n"})
        result = W.run_worker(c, "sys", [], ws, "list the files", tag="w", max_calls=4)
        self.assertEqual(result["status"], "finished")
        second = runtime.requests[1]["messages"]
        self.assertEqual([t["role"] for t in second], ["user", "assistant", "user"])
        self.assertIn("toolResult", second[2]["content"][0])


class AnthropicRuntimeTests(unittest.TestCase):
    def runtime(self, *replies):
        sent = []

        def transport(body):
            sent.append(json.loads(body))
            reply = replies[len(sent) - 1]
            if isinstance(reply, Exception):
                raise reply
            return reply
        return B.AnthropicRuntime("k", transport=transport), sent

    def request(self):
        return {"modelId": "claude-x", **B.to_converse(HISTORY, W.TOOLS, cache=True),
                "inferenceConfig": {"maxTokens": 100, "temperature": 0.2}}

    def test_request_and_response_mapping(self):
        reply = {"id": "msg1", "stop_reason": "tool_use",
                 "content": [{"type": "text", "text": "Hi"}, {"type": "tool_use", "id": "u1", "name": "read_file", "input": {"path": "a"}}],
                 "usage": {"input_tokens": 5, "output_tokens": 7, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 9}}
        rt, sent = self.runtime((200, json.dumps(reply).encode()))
        out = B.from_converse(rt.converse(**self.request()))
        body = sent[0]
        self.assertEqual(body["system"], [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}])
        self.assertEqual(body["messages"][-1]["content"][-1], {"type": "text", "text": "next task", "cache_control": {"type": "ephemeral"}})
        self.assertEqual(body["messages"][1]["content"][0], {"type": "tool_use", "id": "t1", "name": "read_file", "input": {"path": "a.py"}})
        self.assertEqual(body["messages"][2]["content"][0]["type"], "tool_result")
        self.assertEqual(body["tools"][0]["input_schema"]["type"], "object")
        self.assertEqual(out["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(out["usage"]["prompt_tokens"], 114)

    def test_errors(self):
        rt, _ = self.runtime((429, b"{}"), (529, b"{}"), (500, b"{}"), TimeoutError(),
                             (400, b'{"error": {"type": "invalid_request_error"}}'))
        with self.assertRaises(B.ThrottlingError):
            rt.converse(**self.request())
        with self.assertRaises(B.ThrottlingError):
            rt.converse(**self.request())
        with self.assertRaises(B.ReadTimeoutError):
            rt.converse(**self.request())
        with self.assertRaises(B.ReadTimeoutError):
            rt.converse(**self.request())
        with self.assertRaisesRegex(ProviderError, "invalid_request_error"):
            rt.converse(**self.request())


if __name__ == "__main__":
    unittest.main()
