"""Amazon Bedrock (or direct Anthropic API) client with the same interface as provider.OpenRouterClient.

With AnthropicRuntime as its runtime, the same client calls the Anthropic Messages API directly.

complete() takes OpenAI-style chat messages and tools, calls the Bedrock Converse API, and returns an
OpenAI-style response, so the worker, relay and compaction code run unchanged. It keeps the same
safeguards: a dollar cap and a request cap checked before every call, a budget ledger written before
each request is sent, every request and response logged to requests.jsonl, and fail-closed behavior.

Costs are estimates from the per-million-token prices in the run config, since Bedrock responses carry
token counts but no charge. Prompt caching uses two cache points, after the system prompt and after the
last message, so each call reads the conversation prefix the previous call wrote.

Throttling is retried with backoff and is not billed. A timed-out or dropped request is retried up to
timeout_retries, keeping its reservation as committed spend because its billing is unknown. Every
other failure stops the client.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from provider import BudgetExceeded, ProviderError, RateLimited, SAFETY_MARGIN, TransportTimeout, _number, _tokens

THROTTLE_CODES = {"ThrottlingException", "ServiceUnavailableException", "TooManyRequestsException",
                  "ModelNotReadyException"}
THROTTLE_BACKOFF = 15.0
THROTTLE_BACKOFF_MAX = 120.0
STOP_REASONS = {"end_turn": "stop", "stop_sequence": "stop", "tool_use": "tool_calls", "max_tokens": "length",
                "guardrail_intervened": "content_filter", "content_filtered": "content_filter"}
PRICE_KEYS = ("input", "output", "cache_read", "cache_write")
CACHE_POINT = {"cachePoint": {"type": "default"}}


def to_converse(messages: list, tools: list | None, *, cache: bool) -> dict:
    """OpenAI chat messages and tools to Converse system, messages and toolConfig.

    Tool results become toolResult blocks in a user message, and consecutive messages with the same
    role are merged, since Converse requires user and assistant turns to alternate."""
    system: list = []
    turns: list = []

    def add(role: str, blocks: list) -> None:
        if not blocks:
            return
        if turns and turns[-1]["role"] == role:
            turns[-1]["content"].extend(blocks)
        else:
            turns.append({"role": role, "content": blocks})

    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            if content:
                system.append({"text": content})
        elif role == "user":
            if not isinstance(content, str) or not content:
                raise ProviderError("User message without text")
            add("user", [{"text": content}])
        elif role == "assistant":
            blocks = [{"text": content}] if isinstance(content, str) and content.strip() else []
            for call in m.get("tool_calls") or []:
                fn = call["function"]
                args = fn.get("arguments") or "{}"
                blocks.append({"toolUse": {"toolUseId": call["id"], "name": fn["name"],
                                           "input": json.loads(args) if isinstance(args, str) else args}})
            if not blocks:
                raise ProviderError("Assistant message with no text or tool calls")
            add("assistant", blocks)
        elif role == "tool":
            add("user", [{"toolResult": {"toolUseId": m["tool_call_id"], "content": [{"text": content or ""}]}}])
        else:
            raise ProviderError("Unknown message role: %r" % (role,))
    if not turns or turns[0]["role"] != "user":
        raise ProviderError("Conversation must start with a user message")
    if cache:
        if system:
            system.append(dict(CACHE_POINT))
        turns[-1]["content"].append(dict(CACHE_POINT))
    request: dict = {"messages": turns}
    if system:
        request["system"] = system
    if tools:
        request["toolConfig"] = {"tools": [{"toolSpec": {
            "name": t["function"]["name"], "description": t["function"].get("description", ""),
            "inputSchema": {"json": t["function"]["parameters"]}}} for t in tools]}
        # Converse has no switch for one tool call per turn, so Anthropic's own tool_choice is passed through
        # (verified on Bedrock with Sonnet 4.6). The OpenRouter runs set parallel_tool_calls to false.
        request["additionalModelRequestFields"] = {"tool_choice": {"type": "auto", "disable_parallel_tool_use": True}}
    return request


def from_converse(response: dict) -> dict:
    """Converse output to an OpenAI-style response with usage in OpenRouter's field names."""
    message = (response.get("output") or {}).get("message") or {}
    texts, calls = [], []
    for block in message.get("content") or []:
        if "text" in block:
            texts.append(block["text"])
        elif "toolUse" in block:
            use = block["toolUse"]
            calls.append({"id": use["toolUseId"], "type": "function",
                          "function": {"name": use["name"], "arguments": json.dumps(use.get("input", {}))}})
    out: dict = {"role": "assistant", "content": "".join(texts) or None}
    if calls:
        out["tool_calls"] = calls
    usage = response.get("usage") or {}
    read = usage.get("cacheReadInputTokens") or 0
    written = usage.get("cacheWriteInputTokens") or 0
    prompt = (usage.get("inputTokens") or 0) + read + written
    completion = usage.get("outputTokens") or 0
    stop = response.get("stopReason")
    return {"id": (response.get("ResponseMetadata") or {}).get("RequestId"),
            "choices": [{"finish_reason": STOP_REASONS.get(stop, stop), "message": out}],
            "usage": {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion,
                      "prompt_tokens_details": {"cached_tokens": read, "cache_write_tokens": written}}}


class ThrottlingError(Exception):
    """An HTTP 429 or 529 from the Anthropic API, shaped like a botocore throttling error."""

    def __init__(self, status: int):
        super().__init__("HTTP %d" % status)
        self.response = {"Error": {"Code": "ThrottlingException"}}


class ReadTimeoutError(Exception):
    """A timed-out or dropped Anthropic API request. Named like botocore's so the client retries it."""


class AnthropicRuntime:
    """Anthropic Messages API behind the Converse interface: converse(**request) takes and returns
    Converse-shaped dicts, so BedrockClient's caps, ledger, logging and retries apply unchanged."""

    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, key: str, timeout: float = 600.0, transport: Callable | None = None):
        self._key, self._timeout = key, timeout
        self._transport = transport or self._post

    def _post(self, body: bytes) -> tuple:
        import urllib.error
        import urllib.request
        request = urllib.request.Request(self.URL, data=body, method="POST", headers={
            "x-api-key": self._key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    @staticmethod
    def _block(block: dict) -> dict:
        if "text" in block:
            return {"type": "text", "text": block["text"]}
        if "toolUse" in block:
            use = block["toolUse"]
            return {"type": "tool_use", "id": use["toolUseId"], "name": use["name"], "input": use["input"]}
        if "toolResult" in block:
            result = block["toolResult"]
            return {"type": "tool_result", "tool_use_id": result["toolUseId"],
                    "content": "".join(c.get("text", "") for c in result["content"])}
        raise ProviderError("Unsupported content block: %s" % sorted(block))

    @classmethod
    def _blocks(cls, content: list) -> list:
        """Converse blocks to Messages blocks; a cachePoint marks the block before it for caching."""
        out: list = []
        for block in content:
            if "cachePoint" in block:
                if out:
                    out[-1]["cache_control"] = {"type": "ephemeral"}
            else:
                out.append(cls._block(block))
        return out

    def to_messages(self, request: dict) -> dict:
        body = {"model": request["modelId"], "max_tokens": request["inferenceConfig"]["maxTokens"],
                "messages": [{"role": t["role"], "content": self._blocks(t["content"])} for t in request["messages"]]}
        if "temperature" in request["inferenceConfig"]:
            body["temperature"] = request["inferenceConfig"]["temperature"]
        if request.get("system"):
            body["system"] = self._blocks(request["system"])
        if request.get("toolConfig"):
            body["tools"] = [{"name": t["toolSpec"]["name"], "description": t["toolSpec"]["description"],
                              "input_schema": t["toolSpec"]["inputSchema"]["json"]} for t in request["toolConfig"]["tools"]]
            # One tool call per turn, as the OpenRouter runs set parallel_tool_calls to false.
            body["tool_choice"] = {"type": "auto", "disable_parallel_tool_use": True}
        return body

    @staticmethod
    def from_messages(response: dict) -> dict:
        content = []
        for block in response.get("content") or []:
            if block.get("type") == "text":
                content.append({"text": block["text"]})
            elif block.get("type") == "tool_use":
                content.append({"toolUse": {"toolUseId": block["id"], "name": block["name"], "input": block["input"]}})
        usage = response.get("usage") or {}
        return {"output": {"message": {"role": "assistant", "content": content}}, "stopReason": response.get("stop_reason"),
                "usage": {"inputTokens": usage.get("input_tokens", 0), "outputTokens": usage.get("output_tokens", 0),
                          "cacheReadInputTokens": usage.get("cache_read_input_tokens") or 0,
                          "cacheWriteInputTokens": usage.get("cache_creation_input_tokens") or 0},
                "ResponseMetadata": {"RequestId": response.get("id")}}

    def converse(self, **request: Any) -> dict:
        import socket
        body = json.dumps(self.to_messages(request), ensure_ascii=False).encode("utf-8")
        try:
            status, raw = self._transport(body)
        except (TimeoutError, socket.timeout, ConnectionError, OSError) as error:
            raise ReadTimeoutError(type(error).__name__) from None
        if status in (429, 529):
            raise ThrottlingError(status)
        if status >= 500:
            raise ReadTimeoutError("HTTP %d" % status)
        try:
            parsed = json.loads(raw)
        except ValueError:
            raise ReadTimeoutError("invalid JSON") from None
        if status != 200:
            detail = parsed.get("error") or {}
            error = ProviderError("Anthropic API HTTP %d: %s: %s" % (status, detail.get("type"), str(detail.get("message"))[:300]))
            error.response = {"Error": {"Code": (parsed.get("error") or {}).get("type")}}
            raise error
        return self.from_messages(parsed)


def _runtime(region: str) -> Any:
    import boto3
    from botocore.config import Config
    return boto3.client("bedrock-runtime", region_name=region,
                        config=Config(read_timeout=600, connect_timeout=30, retries={"max_attempts": 1, "mode": "standard"}))


class BedrockClient:
    def __init__(self, output_dir: Path, *, model: str, region: str, prices_per_mtok: dict, budget_usd: float,
                 max_calls: int, temperature: float | None = 0.2, max_tokens: int = 4096, timeout_retries: int = 0,
                 throttle_retries: int = 8, prompt_cache: bool = True, runtime: Any = None,
                 sleep: Callable[[float], None] = time.sleep, provider_name: str = "Amazon Bedrock"):
        self.output_dir = Path(output_dir)
        self.model, self.region = model, region
        self.provider_name = provider_name
        if set(prices_per_mtok) != set(PRICE_KEYS):
            raise ProviderError("prices_per_mtok needs exactly %s" % (PRICE_KEYS,))
        self._prices = {k: _number(v, "price " + k) / Decimal(1_000_000) for k, v in prices_per_mtok.items()}
        self.budget = _number(budget_usd, "budget_usd")
        self.max_calls = _tokens(max_calls, "max_calls")
        self.max_tokens = _tokens(max_tokens, "max_tokens")
        if not self.max_tokens:
            raise ProviderError("max_tokens must be positive")
        # None omits temperature: Claude 5.5 models reject it and use their default.
        self.temperature = None if temperature is None else float(_number(temperature, "temperature"))
        self.timeout_retries = _tokens(timeout_retries, "timeout_retries")
        self.throttle_retries = _tokens(throttle_retries, "throttle_retries")
        self.prompt_cache = prompt_cache
        self._runtime = runtime if runtime is not None else _runtime(region)
        self._sleep = sleep
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if (self.output_dir / "budget.json").exists():
            raise ProviderError("Existing budget ledger: use a fresh output directory")
        self._estimated = self._reserved = Decimal(0)
        self._requests = self._completed = self._usage_requests = 0
        self._prompt = self._completion = self._cached = self._cache_write = 0
        self._timeouts_retried = self._throttles_retried = 0
        self._latency = 0.0
        self._stopped = False
        self._save_budget()
        self.model_metadata = {
            "model": model, "region": region, "provider_name": self.provider_name,
            "prices_per_mtok": {k: float(v) for k, v in prices_per_mtok.items()},
            "pricing_policy": "config prices; cache read and write priced as reported in usage",
            "safety_margin": float(SAFETY_MARGIN), "temperature_sent": self.temperature,
            "max_tokens": self.max_tokens, "prompt_cache": prompt_cache, "thinking": "disabled",
        }
        self._atomic_json("model_metadata.json", self.model_metadata)

    def _atomic_json(self, filename: str, value) -> None:
        fd, temp = tempfile.mkstemp(prefix="." + filename, dir=self.output_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(json.dumps(value, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.output_dir / filename)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def _save_budget(self) -> None:
        self._atomic_json("budget.json", self.summary())

    def _log(self, record: dict) -> None:
        with (self.output_dir / "requests.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _call(self, request: dict, tag: str) -> dict:
        start = time.monotonic()
        raw, failure, code = None, None, None
        try:
            raw = self._runtime.converse(**request)
        except Exception as error:  # botocore errors: classify by code, log type only.
            failure = type(error).__name__
            code = getattr(error, "response", {}).get("Error", {}).get("Code") if hasattr(error, "response") else None
        latency = time.monotonic() - start
        self._latency += latency
        self._log({"tag": tag, "request": request, "response": raw, "latency_seconds": latency,
                   "transport_error": failure, "error_code": code})
        if failure is None:
            return raw
        if code in THROTTLE_CODES:
            raise RateLimited("Bedrock throttled: %s" % code)
        if failure in ("ReadTimeoutError", "ConnectTimeoutError", "EndpointConnectionError", "ConnectionClosedError") \
                or code in ("ModelTimeoutException", "InternalServerException"):
            raise TransportTimeout("Bedrock %s; billing unknown" % (code or failure))
        raise ProviderError("Bedrock request failed: %s %s" % (failure, code or ""))

    def complete(self, messages: list, *, tools: list | None = None, json_mode: bool = False, tag: str = "") -> dict:
        if self._stopped:
            raise ProviderError("Client stopped after a previous failed attempt")
        if json_mode:
            raise ProviderError("json_mode is not supported by the Bedrock client")
        request = {"modelId": self.model, **to_converse(messages, tools, cache=self.prompt_cache),
                   "inferenceConfig": {"maxTokens": self.max_tokens,
                                       **({} if self.temperature is None else {"temperature": self.temperature})}}
        size = len(json.dumps(request, ensure_ascii=False).encode("utf-8"))
        # One token per byte, all at the highest input price: a loose upper bound, released after usage.
        input_price = max(self._prices["input"], self._prices["cache_write"])
        reservation = (size * input_price + self.max_tokens * self._prices["output"]) * SAFETY_MARGIN
        timeouts = throttled = 0
        while True:
            if self._requests >= self.max_calls or self._estimated + self._reserved + reservation > self.budget:
                raise BudgetExceeded("Request would exceed the dollar or request cap")
            self._reserved += reservation
            self._requests += 1
            self._stopped = True
            self._save_budget()
            attempt = timeouts + throttled
            try:
                try:
                    raw = self._call(request, f"{tag}/retry{attempt}" if attempt else tag)
                except TransportTimeout:
                    if timeouts == self.timeout_retries:
                        raise
                    timeouts += 1
                    self._timeouts_retried += 1
                    continue
                except RateLimited:
                    if throttled == self.throttle_retries:
                        raise
                    self._reserved -= reservation  # Throttled requests are not billed.
                    throttled += 1
                    self._throttles_retried += 1
                    self._sleep(min(THROTTLE_BACKOFF * 2 ** (throttled - 1), THROTTLE_BACKOFF_MAX))
                    continue
                response = from_converse(raw)
                self._account(response["usage"], reservation)
                choice = response["choices"][0]
                if choice["finish_reason"] not in ("stop", "tool_calls"):
                    raise ProviderError("Response truncated, filtered, or missing finish_reason: %s" % choice["finish_reason"])
                self._completed += 1
                self._stopped = False
                return response
            finally:
                self._save_budget()

    def _account(self, usage: dict, reservation: Decimal) -> None:
        read = usage["prompt_tokens_details"]["cached_tokens"]
        written = usage["prompt_tokens_details"]["cache_write_tokens"]
        fresh = usage["prompt_tokens"] - read - written
        self._estimated += (fresh * self._prices["input"] + read * self._prices["cache_read"]
                            + written * self._prices["cache_write"] + usage["completion_tokens"] * self._prices["output"])
        self._usage_requests += 1
        self._prompt += usage["prompt_tokens"]
        self._completion += usage["completion_tokens"]
        self._cached += read
        self._cache_write += written
        self._reserved -= reservation
        if self._estimated + self._reserved > self.budget:
            raise BudgetExceeded("Reported usage exceeded budget; client stopped")

    def summary(self) -> dict:
        committed = self._estimated + self._reserved
        return {
            "model": self.model, "provider_name": self.provider_name, "region": self.region,
            "budget_usd": float(self.budget), "max_calls": self.max_calls,
            "requests": self._requests, "completed_requests": self._completed,
            "usage_accounted_requests": self._usage_requests,
            "usage_unknown_requests": self._requests - self._usage_requests,
            "actual_cost_usd": 0.0, "estimated_cost_usd": float(self._estimated),
            "accounted_cost_usd": float(self._estimated), "reserved_cost_usd": float(self._reserved),
            "budget_committed_usd": float(committed), "remaining_budget_usd": float(self.budget - committed),
            "prompt_tokens": self._prompt, "completion_tokens": self._completion,
            "total_tokens": self._prompt + self._completion,
            "cached_tokens": self._cached, "known_cached_tokens": self._cached,
            "cache_write_tokens": self._cache_write, "known_cache_write_tokens": self._cache_write,
            "latency_seconds": self._latency, "stopped": self._stopped,
            "timeout_retries": self.timeout_retries, "timeouts_retried": self._timeouts_retried,
            "throttle_retries": self.throttle_retries, "throttles_retried": self._throttles_retried,
            "estimate_policy": "config per-million-token prices applied to reported input, cache and output tokens",
        }
