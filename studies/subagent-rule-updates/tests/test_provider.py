"""Offline provider tests: python3 -m unittest discover -s experiments/subagent-rule-updates -p test_provider.py -v"""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from provider import BudgetExceeded, OpenRouterClient, ProviderError, RateLimited, load_key


MODEL = "openai/gpt-6-luna"
SECRET = "sk-test-credential-never-log"
PARAMETERS = ["tools", "tool_choice", "temperature", "max_tokens", "response_format"]
PRICING = {"prompt": "0.0000001", "completion": "0.0000005", "input_cache_read": "0.00000001"}
TOOLS = [{"type": "function", "function": {"name": "read_file", "description": "Read a file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]


def success(cost=0.000123):
    usage = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120,
             "prompt_tokens_details": {"cached_tokens": 40, "cache_write_tokens": 0}}
    if cost is not None:
        usage["cost"] = cost
    return {"id": "gen-test", "provider": "OpenAI", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "done"}}], "usage": usage}


class FakeTransport:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses if responses is not None else [success()])
        self.models = {"data": [{"id": MODEL, "supported_parameters": PARAMETERS, "pricing": {"prompt": "0", "completion": "0"}}]}
        self.endpoints = {"data": {"endpoints": [{"provider_name": "OpenAI", "tag": "openai", "supported_parameters": PARAMETERS, "pricing": copy.deepcopy(PRICING)}]}}

    def __call__(self, method, url, *, headers, body):
        self.calls.append({"method": method, "url": url, "headers": headers, "body": body})
        if method == "GET":
            response = self.endpoints if url.endswith("/endpoints") else self.models
            return 200, json.dumps(response).encode()
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, tuple):
            return response
        return 200, json.dumps(response, ensure_ascii=False).encode()

    @property
    def posts(self):
        return [c for c in self.calls if c["method"] == "POST"]


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {"OPENROUTER_API_KEY": SECRET})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def client(self, fake=None, **kwargs):
        fake = fake or FakeTransport()
        return OpenRouterClient(self.root / "run", transport=fake, **kwargs), fake

    def records(self):
        return [json.loads(line) for line in (self.root / "run" / "requests.jsonl").read_text().splitlines()]

    def test_hung_request_is_retried_and_keeps_its_reservation(self):
        client, fake = self.client(FakeTransport([TimeoutError(), success()]), timeout_retries=1)
        self.assertEqual(client.complete([{"role": "user", "content": "hi"}], tag="t")["choices"][0]["message"]["content"], "done")
        summary = client.summary()
        self.assertEqual((summary["requests"], summary["completed_requests"], summary["timeouts_retried"]), (2, 1, 1))
        self.assertGreater(summary["reserved_cost_usd"], 0)  # the abandoned attempt still counts against the budget
        self.assertFalse(summary["stopped"])
        self.assertEqual([r["tag"] for r in self.records() if r["method"] == "POST"], ["t", "t/retry1"])

    def test_timeouts_are_not_retried_by_default_or_past_the_limit(self):
        client, _ = self.client(FakeTransport([TimeoutError()]))
        with self.assertRaises(ProviderError):
            client.complete([{"role": "user", "content": "hi"}])
        self.assertTrue(client.summary()["stopped"])
        client2 = OpenRouterClient(self.root / "two", transport=FakeTransport([TimeoutError(), TimeoutError()]), timeout_retries=1)
        with self.assertRaises(ProviderError):
            client2.complete([{"role": "user", "content": "hi"}])
        self.assertEqual(client2.summary()["timeouts_retried"], 1)

    def test_wrapped_connect_timeout_is_retried(self):
        import urllib.error
        client, fake = self.client(FakeTransport([urllib.error.URLError(TimeoutError("connect")), success()]), timeout_retries=1)
        client.complete([{"role": "user", "content": "hi"}])
        self.assertEqual((len(fake.posts), client.summary()["timeouts_retried"]), (2, 1))

    def test_socket_timeout_is_retried(self):
        import socket
        client, fake = self.client(FakeTransport([socket.timeout("read"), success()]), timeout_retries=1)
        client.complete([{"role": "user", "content": "hi"}])
        self.assertEqual((len(fake.posts), client.summary()["timeouts_retried"]), (2, 1))

    def test_retry_blocked_by_cap_leaves_client_stopped(self):
        client, fake = self.client(FakeTransport([TimeoutError(), success()]), timeout_retries=1, max_calls=1)
        with self.assertRaises(BudgetExceeded):
            client.complete([{"role": "user", "content": "hi"}])
        summary = client.summary()
        self.assertEqual((summary["stopped"], summary["timeouts_retried"], len(fake.posts)), (True, 0, 1))

    def test_rate_limited_request_is_retried_with_backoff_and_releases_reservation(self):
        waits = []
        client, fake = self.client(FakeTransport([(429, b"{}"), (429, b"{}"), success()]),
                                   rate_limit_retries=2, sleep=waits.append)
        client.complete([{"role": "user", "content": "x"}])
        summary = client.summary()
        self.assertEqual((len(fake.posts), summary["rate_limits_retried"], summary["requests"]), (3, 2, 3))
        self.assertEqual(waits, [15.0, 30.0])
        self.assertEqual(summary["reserved_cost_usd"], 0.0)
        self.assertEqual(summary["timeouts_retried"], 0)

    def test_rate_limits_are_not_retried_by_default_or_past_the_limit(self):
        client, fake = self.client(FakeTransport([(429, b"{}"), success()]))
        with self.assertRaises(RateLimited):
            client.complete([{"role": "user", "content": "x"}])
        self.assertEqual(len(fake.posts), 1)
        fake2 = FakeTransport([(429, b"{}"), (429, b"{}"), success()])
        client2 = OpenRouterClient(self.root / "two", transport=fake2, rate_limit_retries=1, sleep=lambda s: None)
        with self.assertRaises(RateLimited):
            client2.complete([{"role": "user", "content": "x"}])
        self.assertEqual(len(fake2.posts), 2)
        with self.assertRaises(ProviderError):
            client2.complete([{"role": "user", "content": "x"}])

    def test_timeout_and_rate_limit_retries_are_counted_separately(self):
        client, fake = self.client(FakeTransport([TimeoutError(), (429, b"{}"), success()]),
                                   timeout_retries=1, rate_limit_retries=1, sleep=lambda s: None)
        client.complete([{"role": "user", "content": "x"}])
        summary = client.summary()
        self.assertEqual((summary["timeouts_retried"], summary["rate_limits_retried"], len(fake.posts)), (1, 1, 3))

    def test_other_transport_failures_are_never_retried(self):
        client, fake = self.client(FakeTransport([ConnectionResetError(), success()]), timeout_retries=2)
        with self.assertRaises(ProviderError):
            client.complete([{"role": "user", "content": "hi"}])
        self.assertEqual(len(fake.posts), 1)

    def test_exact_full_logging_and_tools_each_call(self):
        response = success()
        response["extra"] = {"unknown": [1, "retained"]}
        response["choices"][0] = {"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": '{"path":"requirements.txt"}'}}]}}
        client, fake = self.client(FakeTransport([response, success()]))
        messages = [{"role": "user", "content": "Read café requirements"}]
        self.assertEqual(client.complete(messages, tools=TOOLS, tag="worker-E"), response)
        client.complete(messages, tools=TOOLS)
        self.assertEqual(len(fake.posts), 2)
        for call, record in zip(fake.posts, self.records()[2:]):
            request = json.loads(call["body"])
            self.assertEqual(record["request_body"].encode(), call["body"])
            self.assertEqual(record["request"], request)
            self.assertEqual(request["messages"], messages)
            self.assertEqual(request["tools"], TOOLS)
            self.assertEqual(request["tool_choice"], "auto")
            self.assertNotIn("parallel_tool_calls", request)
            self.assertEqual(request["provider"], {"only": ["OpenAI"], "order": ["OpenAI"], "allow_fallbacks": False, "require_parameters": True})
            self.assertNotIn("headers", record)
            self.assertGreaterEqual(record["latency_seconds"], 0)
            self.assertNotIn("seed", request)
            self.assertNotIn("reasoning", request)
        record = self.records()[2]
        self.assertEqual(json.loads(record["response_body"]), response)
        self.assertEqual(record["response"], response)
        self.assertEqual(record["tag"], "worker-E")
        self.assertEqual(client.summary()["requests"], 2)
        self.assertEqual(client.summary()["reserved_cost_usd"], 0)
        self.assertEqual(json.loads((client.output_dir / "budget.json").read_text()), client.summary())
        self.assertEqual(json.loads((client.output_dir / "model_metadata.json").read_text()), client.model_metadata)
        self.assertTrue(all("Authorization" not in c["headers"] for c in fake.calls[:2]))

    def test_cap_enforced_before_post_and_tools_count_toward_bound(self):
        client, fake = self.client(budget_usd=0.00001)
        with self.assertRaises(BudgetExceeded):
            client.complete([{"role": "user", "content": "hello"}], tools=TOOLS)
        self.assertEqual(fake.posts, [])
        self.assertEqual(client.summary()["requests"], 0)
        self.assertEqual(client.summary()["reserved_cost_usd"], 0)
        # A huge tool schema alone must consume the serialized-byte allowance.
        other = self.root / "large-tools"
        fake2 = FakeTransport()
        client2 = OpenRouterClient(other, transport=fake2, budget_usd=0.002, max_tokens=1)
        tools = copy.deepcopy(TOOLS)
        tools[0]["function"]["description"] = "x" * 30000
        with self.assertRaises(BudgetExceeded):
            client2.complete([], tools=tools)
        self.assertEqual(fake2.posts, [])

    def test_request_count_cap(self):
        client, fake = self.client(max_calls=1)
        client.complete([])
        with self.assertRaises(BudgetExceeded):
            client.complete([])
        self.assertEqual(len(fake.posts), 1)

    def test_failures_retain_reservation_never_retry_or_fallback(self):
        for response in [TimeoutError(SECRET), (500, b'{"error":{"message":"server"}}'), (429, b'{"error":"rate limit"}'), (200, b"not json")]:
            with self.subTest(response=type(response).__name__):
                output = self.root / str(len(list(self.root.iterdir())))
                fake = FakeTransport([response, success()])
                client = OpenRouterClient(output, transport=fake)
                with self.assertRaises(ProviderError):
                    client.complete([], tools=TOOLS)
                self.assertEqual(len(fake.posts), 1)
                self.assertEqual(client.summary()["requests"], 1)
                self.assertGreater(client.summary()["reserved_cost_usd"], 0)
                self.assertTrue(client.summary()["stopped"])
                with self.assertRaises(ProviderError):
                    client.complete([])
                self.assertEqual(len(fake.posts), 1)
                self.assertNotIn(SECRET, (output / "requests.jsonl").read_text())
                self.assertGreater(json.loads((output / "budget.json").read_text())["reserved_cost_usd"], 0)

    def test_reservation_is_fsynced_before_transport(self):
        fake = FakeTransport()
        original = fake.__call__
        observations = []

        def check(method, url, *, headers, body):
            if method == "POST":
                ledger = json.loads((self.root / "run" / "budget.json").read_text())
                observations.append(ledger)
                self.assertGreater(ledger["reserved_cost_usd"], 0)
                self.assertEqual(ledger["requests"], 1)
                self.assertTrue(ledger["stopped"])
            return original(method, url, headers=headers, body=body)

        client, _ = self.client(check)
        with patch("provider.os.fsync", wraps=os.fsync) as fsync:
            client.complete([])
        self.assertTrue(observations)
        self.assertGreaterEqual(fsync.call_count, 5)

    def test_billed_cost_and_reported_cache(self):
        client, _ = self.client()
        client.complete([])
        summary = client.summary()
        self.assertEqual(summary["actual_cost_usd"], 0.000123)
        self.assertEqual(summary["estimated_cost_usd"], 0)
        self.assertEqual(summary["cached_tokens"], 40)
        self.assertEqual(summary["prompt_tokens"], 100)
        self.assertEqual(summary["completion_tokens"], 20)

    def test_missing_cost_uses_declared_estimate_not_free(self):
        client, _ = self.client(FakeTransport([success(None)]))
        client.complete([])
        summary = client.summary()
        self.assertEqual(summary["actual_cost_usd"], 0)
        self.assertAlmostEqual(summary["estimated_cost_usd"], 60 * 1e-7 + 40 * 1e-8 + 20 * 5e-7)
        self.assertEqual(summary["estimated_cost_requests"], 1)
        self.assertEqual(summary["reserved_cost_usd"], 0)

    def test_unknown_cache_is_not_assumed_hit(self):
        response = success(None)
        del response["usage"]["prompt_tokens_details"]
        client, _ = self.client(FakeTransport([response]))
        client.complete([])
        summary = client.summary()
        self.assertIsNone(summary["cached_tokens"])
        self.assertIsNone(summary["cache_write_tokens"])
        self.assertEqual(summary["cache_usage_unknown_requests"], 1)
        self.assertAlmostEqual(summary["estimated_cost_usd"], 100 * 1e-7 + 20 * 5e-7)

    def test_missing_or_invalid_usage_keeps_reservation_and_raw_response(self):
        cases = [None, {}, {"prompt_tokens": -1, "completion_tokens": 1},
                 {"prompt_tokens": 1, "completion_tokens": True},
                 {"prompt_tokens": 1, "completion_tokens": 1, "cost": "NaN"},
                 {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 99},
                 {"prompt_tokens": 1, "completion_tokens": 1, "prompt_tokens_details": []},
                 {"prompt_tokens": 1, "completion_tokens": 1, "prompt_tokens_details": {"cached_tokens": 2}}]
        for index, usage in enumerate(cases):
            with self.subTest(usage=usage):
                response = success()
                response["usage"] = usage
                output = self.root / f"bad-{index}"
                client = OpenRouterClient(output, transport=FakeTransport([response]))
                with self.assertRaises(ProviderError):
                    client.complete([])
                self.assertGreater(client.summary()["reserved_cost_usd"], 0)
                self.assertEqual(client.summary()["usage_unknown_requests"], 1)
                self.assertIsNone(client.summary()["cached_tokens"])
                record = json.loads((output / "requests.jsonl").read_text().splitlines()[-1])
                self.assertEqual(record["response"], response)

    def test_truncation_errors_and_malformed_choices_are_logged_and_stop(self):
        for index, kind in enumerate(["length", "content_filter", "error", "choices"]):
            response = success()
            if kind == "error":
                response["error"] = {"message": "provider failed"}
            elif kind == "choices":
                response["choices"] = []
            else:
                response["choices"][0]["finish_reason"] = kind
            output = self.root / f"stop-{index}"
            client = OpenRouterClient(output, transport=FakeTransport([response]))
            with self.assertRaises(ProviderError):
                client.complete([])
            self.assertEqual(client.summary()["actual_cost_usd"], 0.000123)
            self.assertEqual(client.summary()["reserved_cost_usd"], 0)
            self.assertTrue(client.summary()["stopped"])
            self.assertEqual(client.summary()["completed_requests"], 0)
            self.assertEqual(json.loads((output / "requests.jsonl").read_text().splitlines()[-1])["response"], response)

    def test_zero_cost_is_billed_not_estimated(self):
        client, _ = self.client(FakeTransport([success(0)]))
        client.complete([])
        self.assertEqual(client.summary()["actual_cost_requests"], 1)
        self.assertEqual(client.summary()["estimated_cost_requests"], 0)

    def test_fixed_provider_price_variants_and_context_overrides(self):
        fake = FakeTransport()
        endpoint = fake.endpoints["data"]["endpoints"][0]
        endpoint["pricing"]["overrides"] = [{"min_prompt_tokens": 272000, "prompt": "0.0000002", "completion": "0.00000075"}]
        fast = copy.deepcopy(endpoint)
        fast["tag"] = "openai/fast"
        fast["pricing"]["completion"] = "0.000001"
        fake.endpoints["data"]["endpoints"].append(fast)
        client, _ = self.client(fake)
        prices = client.model_metadata["reservation_prices_per_token"]
        self.assertEqual(prices["prompt"], 2e-7)
        self.assertEqual(prices["completion"], 1e-6)
        self.assertNotEqual(prices["prompt"], 0)  # Model-level minimum is not used.

    def test_cache_write_estimate_and_bound(self):
        fake = FakeTransport([success(None)])
        fake.endpoints["data"]["endpoints"][0]["pricing"].update(input_cache_write="0.000000125", input_cache_write_1h="0.0000002")
        fake.responses[0]["usage"]["prompt_tokens_details"] = {"cached_tokens": 10, "cache_write_tokens": 20}
        client, _ = self.client(fake)
        client.complete([])
        self.assertAlmostEqual(client.summary()["estimated_cost_usd"], 70e-7 + 10e-8 + 20 * 2e-7 + 20 * 5e-7)
        self.assertEqual(client.summary()["cache_write_tokens"], 20)

    def test_unknown_cache_writes_use_conservative_input_price(self):
        fake = FakeTransport([success(None)])
        fake.endpoints["data"]["endpoints"][0]["pricing"]["input_cache_write"] = "0.0000002"
        del fake.responses[0]["usage"]["prompt_tokens_details"]
        client, _ = self.client(fake)
        client.complete([])
        self.assertAlmostEqual(client.summary()["estimated_cost_usd"], 100 * 2e-7 + 20 * 5e-7)
        self.assertIsNone(client.summary()["cache_write_tokens"])

    def test_json_mode_and_supported_temperature_only(self):
        fake = FakeTransport()
        fake.endpoints["data"]["endpoints"][0]["supported_parameters"] = [p for p in PARAMETERS if p != "temperature"]
        client, _ = self.client(fake, temperature=0.7, max_tokens=123, reasoning_effort="high")
        client.complete([], json_mode=True)
        request = json.loads(fake.posts[0]["body"])
        self.assertNotIn("temperature", request)
        self.assertNotIn("parallel_tool_calls", request)
        self.assertNotIn("reasoning", request)
        self.assertEqual(request["max_tokens"], 123)
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertIsNone(client.model_metadata["temperature_sent"])
        self.assertEqual(client.model_metadata["reasoning_effort_requested"], "high")
        self.assertEqual(client.model_metadata["effective_settings"], {"max_tokens": 123})

    def test_parallel_tool_calls_false_only_when_advertised(self):
        fake = FakeTransport()
        fake.endpoints["data"]["endpoints"][0]["supported_parameters"] = PARAMETERS + ["parallel_tool_calls"]
        client, _ = self.client(fake)
        client.complete([], tools=TOOLS)
        request = json.loads(fake.posts[0]["body"])
        self.assertIs(request["parallel_tool_calls"], False)
        self.assertEqual(request["max_tokens"], 4096)
        self.assertEqual(client.model_metadata["effective_settings"], {
            "max_tokens": 4096, "temperature": 0.2, "parallel_tool_calls": False,
        })

    def test_reasoning_settings_and_response_history_are_preserved(self):
        cases = [(MODEL, "OpenAI", "low"), ("anthropic/claude-sonnet-5", "Anthropic", "medium")]
        for index, (model, provider_name, effort) in enumerate(cases):
            with self.subTest(model=model, effort=effort):
                response = success()
                message = response["choices"][0]["message"]
                message["reasoning"] = "Raw reasoning returned by provider"
                message["reasoning_details"] = [
                    {"type": "reasoning.text", "text": "Preserve this", "index": 0},
                    {"type": "reasoning.encrypted", "data": "opaque-data", "id": "reasoning-1", "index": 1},
                ]
                fake = FakeTransport([response, success()])
                fake.models["data"][0]["id"] = model
                endpoint = fake.endpoints["data"]["endpoints"][0]
                endpoint["provider_name"] = provider_name
                endpoint["supported_parameters"] = [p for p in PARAMETERS if p != "temperature"] + ["reasoning"]
                kwargs = {"reasoning_effort": effort} if effort != "low" else {}
                client = OpenRouterClient(self.root / f"reasoning-{index}", model=model,
                                          provider_name=provider_name, transport=fake, **kwargs)
                messages = [{"role": "user", "content": "Do permitted work"}]
                returned = client.complete(messages, tools=TOOLS)
                self.assertEqual(returned, response)
                history = messages + [returned["choices"][0]["message"], {"role": "user", "content": "Continue"}]
                client.complete(history, tools=TOOLS)
                settings = {"max_tokens": 4096, "reasoning": {"effort": effort}}
                if provider_name == "Anthropic":
                    settings["cache_control"] = {"type": "ephemeral"}
                self.assertEqual(client.model_metadata["effective_settings"], settings)
                for call in fake.posts:
                    request = json.loads(call["body"])
                    for key, value in settings.items():
                        self.assertEqual(request[key], value)
                    self.assertNotIn("temperature", request)
                    self.assertNotIn("parallel_tool_calls", request)
                    self.assertNotIn("exclude", request["reasoning"])
                self.assertEqual(json.loads(fake.posts[1]["body"])["messages"], history)
                records = [json.loads(line) for line in (client.output_dir / "requests.jsonl").read_text().splitlines()]
                self.assertEqual(records[2]["response"], response)
                self.assertEqual(records[3]["request"]["messages"][1], message)
                snapshot = json.loads((client.output_dir / "model_metadata.json").read_text())
                self.assertEqual(snapshot["effective_settings"], settings)

    def test_anthropic_is_explicit_and_no_cross_provider_fallback(self):
        fake = FakeTransport()
        model = "anthropic/claude-sonnet-5"
        fake.models["data"][0]["id"] = model
        fake.endpoints["data"]["endpoints"][0]["provider_name"] = "Anthropic"
        client, _ = self.client(fake, model=model, provider_name="Anthropic")
        client.complete([], tools=TOOLS)
        request = json.loads(fake.posts[0]["body"])
        self.assertEqual(request["provider"]["only"], ["Anthropic"])
        self.assertEqual(request["model"], model)
        self.assertEqual(request["cache_control"], {"type": "ephemeral"})

    def test_cache_control_only_for_anthropic_and_can_be_disabled(self):
        fake = FakeTransport()
        client, _ = self.client(fake)
        client.complete([], tools=TOOLS)
        self.assertNotIn("cache_control", json.loads(fake.posts[0]["body"]))
        fake2 = FakeTransport()
        model = "anthropic/claude-sonnet-5"
        fake2.models["data"][0]["id"] = model
        fake2.endpoints["data"]["endpoints"][0]["provider_name"] = "Anthropic"
        client2 = OpenRouterClient(self.root / "no-cache", model=model, provider_name="Anthropic", transport=fake2, prompt_cache=False)
        client2.complete([], tools=TOOLS)
        self.assertNotIn("cache_control", json.loads(fake2.posts[0]["body"]))

    def test_missing_fixed_provider_and_missing_tools_fail_closed(self):
        fake = FakeTransport()
        fake.endpoints["data"]["endpoints"][0]["provider_name"] = "Azure"
        with self.assertRaises(ProviderError):
            self.client(fake)
        self.assertEqual(fake.posts, [])
        fake2 = FakeTransport()
        fake2.models["data"][0]["supported_parameters"] = []
        with self.assertRaises(ProviderError):
            OpenRouterClient(self.root / "missing-tools", transport=fake2)
        self.assertEqual(fake2.posts, [])

    def test_key_loading_is_explicit_root_only_and_never_logged(self):
        (self.root / ".env").write_text('export OPENROUTER_API_KEY="file-secret"\n')
        self.assertEqual(load_key(self.root), SECRET)  # Environment wins.
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            self.assertEqual(load_key(self.root), "file-secret")
            with self.assertRaises(ProviderError):
                load_key(self.root / "missing")
        fake = FakeTransport([success()])
        client, _ = self.client(fake)
        client.complete([{"role": "user", "content": SECRET}], tag=SECRET)
        for path in client.output_dir.iterdir():
            self.assertNotIn(SECRET, path.read_text())
        self.assertIn("[REDACTED]", (client.output_dir / "requests.jsonl").read_text())
        self.assertEqual(fake.posts[0]["headers"]["Authorization"], "Bearer " + SECRET)

    def test_nonfinite_json_is_preserved_and_fails_closed(self):
        client, _ = self.client(FakeTransport([(200, b'{"usage":{"cost":NaN}}')]))
        with self.assertRaises(ProviderError):
            client.complete([])
        self.assertEqual(self.records()[-1]["response_body"], '{"usage":{"cost":NaN}}')
        self.assertGreater(client.summary()["reserved_cost_usd"], 0)

    def test_invalid_metadata_price_fails_without_completion(self):
        fake = FakeTransport()
        del fake.endpoints["data"]["endpoints"][0]["pricing"]["prompt"]
        with self.assertRaises(ProviderError):
            self.client(fake)
        self.assertEqual(fake.posts, [])

    def test_existing_ledger_cannot_reset_cap(self):
        self.client()
        with self.assertRaises(ProviderError):
            self.client()


if __name__ == "__main__":
    unittest.main()
