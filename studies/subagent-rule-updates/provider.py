"""Small, fail-closed OpenRouter chat client (stdlib only).

Transport injection: transport(method, url, *, headers: dict, body: bytes | None)
returns (HTTP status: int, response body: bytes). It must not retry. Metadata GETs
are unauthenticated; POSTs carry authorization only in headers, never logs.

Use a fresh output directory per client/run; an existing budget ledger is refused
rather than silently resetting a cap. This synchronous client is single-owner,
not a cross-process budget coordinator. All failed attempts stop the client; no
HTTP retries are made. Hung requests are retried only when timeout_retries is set, and HTTP 429
responses (unbilled, common on free models) only when rate_limit_retries is set. Unknown billing retains the entire reservation.
Prices/usage-derived costs are conservative estimates, not billing observations.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import tempfile
import time
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

BASE_URL = "https://openrouter.ai/api/v1"
# Nearest ancestor with AGENTS.md, so the file can move without edits.
REPOSITORY_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").exists())
SAFETY_MARGIN = Decimal("1.25")
ANTHROPIC_CACHE_PROVIDERS = {"Anthropic", "Amazon Bedrock", "Google", "Azure", "Claude Platform on AWS"}
TOKEN_ALLOWANCE = 4096
RATE_LIMIT_BACKOFF = 15.0
RATE_LIMIT_BACKOFF_MAX = 120.0


class ProviderError(RuntimeError):
    """Provider/protocol failure; inspect requests.jsonl for the raw response."""


class TransportTimeout(ProviderError):
    """The request hung past the transport timeout or its connection dropped. Billing is unknown."""


class RateLimited(ProviderError):
    """HTTP 429. OpenRouter does not bill it."""


class BudgetExceeded(ProviderError):
    """A request would exceed the dollar or request cap."""


def load_key(repository_root: Path | None = None) -> str:
    """Read environment, then repository .env, without modifying os.environ.

    Supports simple KEY=value, export KEY=value, and matching outer quotes; does
    not execute shell syntax or search the working directory/home directory.
    """
    value = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if value:
        return value
    path = (repository_root or REPOSITORY_ROOT) / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            key, sep, value = line.partition("=")
            if sep and key.strip() == "OPENROUTER_API_KEY":
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                else:
                    value = value.split(" #", 1)[0].rstrip()
                if value:
                    return value
    raise ProviderError("OPENROUTER_API_KEY is not configured")


def _transport(method: str, url: str, *, headers: dict, body: bytes | None):
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def _number(value, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ProviderError(f"Invalid {label}")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ProviderError(f"Invalid {label}") from None
    if not number.is_finite() or number < 0:
        raise ProviderError(f"Invalid {label}")
    return number


def _reject_nonfinite(value):
    raise ValueError("Non-finite JSON number")


def _tokens(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProviderError(f"Invalid {label}")
    return value


class OpenRouterClient:
    def __init__(
        self,
        output_dir: Path,
        model: str = "openai/gpt-6-luna",
        budget_usd: float = 20.0,
        max_calls: int = 500,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        provider_name: str = "OpenAI",
        *,
        reasoning_effort: str = "low",
        timeout_retries: int = 0,
        rate_limit_retries: int = 0,
        transport: Callable | None = None,
        sleep: Callable[[float], None] = time.sleep,
        prompt_cache: bool = True,
    ):
        self.prompt_cache = prompt_cache
        # Retries apply only to hung requests. Each abandoned attempt keeps its full reservation
        # as committed spend, so the dollar cap holds even if the provider billed it.
        self.timeout_retries = _tokens(timeout_retries, "timeout_retries")
        self._timeouts_retried = 0
        self.rate_limit_retries = _tokens(rate_limit_retries, "rate_limit_retries")
        self._rate_limits_retried = 0
        self._sleep = sleep
        self.output_dir = Path(output_dir)
        self.model = model
        self.provider_name = provider_name
        self.budget = _number(budget_usd, "budget_usd")
        self.max_calls = _tokens(max_calls, "max_calls")
        self.max_tokens = _tokens(max_tokens, "max_tokens")
        if not self.max_tokens:
            raise ProviderError("max_tokens must be positive")
        self.temperature = float(_number(temperature, "temperature"))
        if not isinstance(reasoning_effort, str) or not reasoning_effort.strip():
            raise ProviderError("reasoning_effort must be a nonempty string")
        self.reasoning_effort = reasoning_effort
        self._key = load_key()
        self._transport = transport or _transport
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if (self.output_dir / "budget.json").exists():
            raise ProviderError("Existing budget ledger: use a fresh output directory")
        self._actual = Decimal(0)
        self._estimated = Decimal(0)
        self._reserved = Decimal(0)
        self._requests = self._completed = self._actual_calls = self._estimated_calls = 0
        self._usage_requests = 0
        self._prompt = self._completion = self._cached = self._cache_write = 0
        self._cache_unknown = self._cache_write_unknown = 0
        self._latency = 0.0
        self._stopped = False
        self._save_budget()

        models = self._fetch("GET", BASE_URL + "/models")
        entries = models.get("data") if isinstance(models, dict) else None
        selected = next((m for m in entries if isinstance(m, dict) and m.get("id") == model), None) if isinstance(entries, list) else None
        if selected is None or "tools" not in selected.get("supported_parameters", []):
            raise ProviderError("Selected model is absent or does not advertise tools")
        endpoints_response = self._fetch("GET", BASE_URL + "/models/" + model + "/endpoints")
        data = endpoints_response.get("data", {})
        endpoints = data.get("endpoints", []) if isinstance(data, dict) else []
        if not isinstance(endpoints, list):
            raise ProviderError("Invalid endpoint metadata")
        fixed = [e for e in endpoints if isinstance(e, dict) and e.get("provider_name") == provider_name]
        if not fixed:
            raise ProviderError("Fixed provider has no published endpoints; refusing fallback")
        if any("tools" not in e.get("supported_parameters", []) for e in fixed):
            raise ProviderError("Fixed provider does not advertise tools on every endpoint")
        self._supported = set.intersection(*(set(e.get("supported_parameters", [])) for e in fixed))
        if "max_tokens" not in self._supported:
            raise ProviderError("Fixed provider does not advertise max_tokens")
        # Include every provider variant and all context-price tiers. Do not use
        # the model-level cheapest-provider price or assume any cache discount.
        prices = []
        for endpoint in fixed:
            price = endpoint.get("pricing", {})
            if not isinstance(price, dict):
                raise ProviderError("Missing endpoint pricing")
            prices.append(price)
            overrides = price.get("overrides", [])
            if not isinstance(overrides, list) or any(not isinstance(o, dict) for o in overrides):
                raise ProviderError("Invalid endpoint pricing overrides")
            for override in overrides:
                prices.append({**price, **override})
        if any(p.get("prompt") is None or p.get("completion") is None for p in prices):
            raise ProviderError("Missing fixed-provider prompt/completion prices")
        self._prices = {
            k: max(_number(p[k], "endpoint " + k) for p in prices)
            for k in ("prompt", "completion")
        }
        for key in ("input_cache_read", "input_cache_write", "input_cache_write_1h"):
            present = [p[key] for p in prices if p.get(key) is not None]
            self._prices[key] = max((_number(v, key) for v in present), default=None)
        self.model_metadata = {
            "model": selected,
            "provider_name": provider_name,
            "endpoints": fixed,
            "pricing_policy": "maximum fixed-provider endpoint and context-tier prices; no assumed cache hit",
            "reservation_prices_per_token": {k: float(v) if v is not None else None for k, v in self._prices.items()},
            "safety_margin": float(SAFETY_MARGIN),
            "prompt_token_allowance": TOKEN_ALLOWANCE,
            "temperature_requested": self.temperature,
            "temperature_sent": self.temperature if "temperature" in self._supported else None,
            "reasoning_effort_requested": self.reasoning_effort,
            "effective_settings": self._generation_settings(),
        }
        self._atomic_json("model_metadata.json", self.model_metadata)

    def _generation_settings(self) -> dict:
        settings = {"max_tokens": self.max_tokens}
        # Anthropic only caches when the request opts in. OpenAI caches automatically.
        if self.prompt_cache and self.provider_name in ANTHROPIC_CACHE_PROVIDERS:
            settings["cache_control"] = {"type": "ephemeral"}
        if "temperature" in self._supported:
            settings["temperature"] = self.temperature
        if "parallel_tool_calls" in self._supported:
            settings["parallel_tool_calls"] = False
        if "reasoning" in self._supported:
            settings["reasoning"] = {"effort": self.reasoning_effort}
        return settings

    def _safe_json(self, value) -> str:
        # Exact bodies are preserved except if the actual credential appears in
        # application text or an echoed error, where secret protection wins.
        return json.dumps(value, ensure_ascii=False, allow_nan=False).replace(self._key, "[REDACTED]")

    def _atomic_json(self, filename: str, value):
        fd, temp = tempfile.mkstemp(prefix="." + filename, dir=self.output_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(self._safe_json(value) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.output_dir / filename)
            directory = os.open(self.output_dir, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def _save_budget(self):
        self._atomic_json("budget.json", self.summary())

    def _fetch(self, method: str, url: str, body: bytes | None = None, tag: str = ""):
        headers = {"Content-Type": "application/json"}
        if method == "POST":
            headers["Authorization"] = "Bearer " + self._key
        start = time.monotonic()
        status = None
        raw = None
        parsed = None
        failure = None
        timed_out = False
        try:
            status, raw = self._transport(method, url, headers=headers, body=body)
            if not isinstance(raw, bytes):
                raise TypeError("transport must return bytes")
            try:
                parsed = json.loads(raw, parse_constant=_reject_nonfinite)
                # Also reject exponent overflow (e.g. 1e999 -> float infinity).
                json.dumps(parsed, allow_nan=False)
            except (ValueError, UnicodeError):
                parsed = None
        except Exception as error:
            # Exception messages can contain headers/credentials; log type only.
            failure = type(error).__name__
            # urllib raises socket read timeouts directly and wraps connect-stage timeouts in URLError.
            # socket.timeout is a separate class before Python 3.10, so check it explicitly.
            # Dropped connections (ConnectionError, including http.client.RemoteDisconnected) have the
            # same unknown-billing risk as a hang and are retried the same way.
            timeouts = (TimeoutError, socket.timeout, ConnectionError)
            timed_out = isinstance(error, timeouts) or isinstance(getattr(error, "reason", None), timeouts)
        latency = time.monotonic() - start
        raw_text = None
        raw_base64 = None
        if isinstance(raw, bytes):
            try:
                raw_text = raw.decode("utf-8")
            except UnicodeError:
                raw_base64 = base64.b64encode(raw).decode("ascii")
        record = {
            "method": method, "url": url, "tag": tag,
            "request_body": body.decode("utf-8") if body is not None else None,
            "request": json.loads(body) if body is not None else None,
            "response_body": raw_text, "response_body_base64": raw_base64,
            "response": parsed, "status": status, "latency_seconds": latency,
            "transport_error": failure,
        }
        with (self.output_dir / "requests.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(self._safe_json(record) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        if method == "POST":
            self._latency += latency
        if timed_out:
            raise TransportTimeout("Transport failed (" + failure + "); billing unknown")
        if failure:
            raise ProviderError("Transport failed (" + failure + "); no retry")
        if status == 429:
            raise RateLimited("HTTP 429 rate limited")
        if not isinstance(status, int) or not 200 <= status < 300:
            raise ProviderError("HTTP failure; no retry (billing unknown)")
        if not isinstance(parsed, dict):
            raise ProviderError("Invalid JSON response; billing unknown")
        return parsed

    def complete(self, messages: list, *, tools: list | None = None, json_mode: bool = False, tag: str = "") -> dict:
        if self._stopped:
            raise ProviderError("Client stopped after a previous failed attempt")
        request = {
            "model": self.model, "messages": messages, **self._generation_settings(),
            "provider": {"only": [self.provider_name], "order": [self.provider_name],
                         "allow_fallbacks": False, "require_parameters": True},
            "stream": False,
        }
        if tools is not None:
            if "tool_choice" not in self._supported:
                raise ProviderError("Fixed provider does not advertise tool_choice")
            request.update(tools=tools, tool_choice="auto")
        if json_mode:
            if "response_format" not in self._supported:
                raise ProviderError("Fixed provider does not advertise response_format")
            request["response_format"] = {"type": "json_object"}
        body = json.dumps(request, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        # One token per serialized UTF-8 byte is a deliberately loose bound;
        # allowance covers message framing and provider-side tool formatting.
        prompt_price = max(v for k, v in self._prices.items() if k != "completion" and v is not None)
        reservation = ((len(body) + TOKEN_ALLOWANCE) * prompt_price + self.max_tokens * self._prices["completion"]) * SAFETY_MARGIN
        timeouts = limited = 0
        retried_timeout = False
        while True:
            attempt = timeouts + limited
            if self._requests >= self.max_calls or self._actual + self._estimated + self._reserved + reservation > self.budget:
                raise BudgetExceeded("Request would exceed the dollar or request cap")
            if retried_timeout:
                self._timeouts_retried += 1
                retried_timeout = False
            self._reserved += reservation
            self._requests += 1
            self._stopped = True  # Persist a pending/unknown attempt before sending.
            self._save_budget()
            try:
                try:
                    response = self._fetch("POST", BASE_URL + "/chat/completions", body, f"{tag}/retry{attempt}" if attempt else tag)
                except TransportTimeout:
                    if timeouts == self.timeout_retries:
                        raise
                    # The hung attempt's reservation stays in _reserved for the rest of the run, and the
                    # client stays stopped unless the retry passes the caps and is sent.
                    timeouts += 1
                    retried_timeout = True
                    continue
                except RateLimited:
                    if limited == self.rate_limit_retries:
                        raise
                    # A 429 is not billed, so its reservation is released before waiting.
                    self._reserved -= reservation
                    limited += 1
                    self._rate_limits_retried += 1
                    self._sleep(min(RATE_LIMIT_BACKOFF * 2 ** (limited - 1), RATE_LIMIT_BACKOFF_MAX))
                    continue
                self._account(response, reservation)
                if response.get("error"):
                    raise ProviderError("Provider returned an error")
                choices = response.get("choices")
                if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                    raise ProviderError("Missing choices")
                choice = choices[0]
                if choice.get("finish_reason") not in ("stop", "tool_calls"):
                    raise ProviderError("Response truncated, filtered, or missing finish_reason")
                if not isinstance(choice.get("message"), dict):
                    raise ProviderError("Missing response message")
                self._completed += 1
                self._stopped = False
                return response
            finally:
                self._save_budget()

    def _account(self, response: dict, reservation: Decimal):
        usage = response.get("usage")
        if not isinstance(usage, dict):
            raise ProviderError("Missing usage; reservation retained")
        # Record a supplied charge even if the remaining usage is malformed.
        billed = _number(usage["cost"], "usage.cost") if usage.get("cost") is not None else None
        if billed is not None:
            self._actual += billed
            self._actual_calls += 1
        prompt = _tokens(usage.get("prompt_tokens"), "prompt_tokens")
        completion = _tokens(usage.get("completion_tokens"), "completion_tokens")
        if "total_tokens" in usage and _tokens(usage["total_tokens"], "total_tokens") != prompt + completion:
            raise ProviderError("Inconsistent total_tokens; reservation retained")
        details = usage.get("prompt_tokens_details")
        if details is None:
            details = {}
        if not isinstance(details, dict):
            raise ProviderError("Invalid cache usage; reservation retained")
        cached = _tokens(details["cached_tokens"], "cached_tokens") if details.get("cached_tokens") is not None else None
        written = _tokens(details["cache_write_tokens"], "cache_write_tokens") if details.get("cache_write_tokens") is not None else None
        if (cached or 0) + (written or 0) > prompt:
            raise ProviderError("Cache tokens exceed prompt tokens; reservation retained")
        self._usage_requests += 1
        self._prompt += prompt
        self._completion += completion
        self._cached += cached or 0
        self._cache_write += written or 0
        self._cache_unknown += cached is None
        self._cache_write_unknown += written is None
        if billed is None:
            read_price = self._prices["input_cache_read"]
            if read_price is None:
                read_price = self._prices["prompt"]
            write_price = max(v for v in (self._prices["input_cache_write"], self._prices["input_cache_write_1h"], self._prices["prompt"]) if v is not None)
            uncached_price = self._prices["prompt"] if written is not None else write_price
            self._estimated += ((prompt - (cached or 0) - (written or 0)) * uncached_price
                                + (cached or 0) * read_price + (written or 0) * write_price
                                + completion * self._prices["completion"])
            self._estimated_calls += 1
        self._reserved -= reservation
        if self._actual + self._estimated + self._reserved > self.budget:
            raise BudgetExceeded("Reported usage exceeded budget; client stopped")

    def summary(self) -> dict:
        committed = self._actual + self._estimated + self._reserved
        unaccounted = self._requests - self._usage_requests
        return {
            "model": self.model, "provider_name": self.provider_name,
            "budget_usd": float(self.budget), "max_calls": self.max_calls,
            "requests": self._requests, "completed_requests": self._completed,
            "usage_accounted_requests": self._usage_requests, "usage_unknown_requests": unaccounted,
            "actual_cost_usd": float(self._actual), "estimated_cost_usd": float(self._estimated),
            "actual_cost_requests": self._actual_calls, "estimated_cost_requests": self._estimated_calls,
            "accounted_cost_usd": float(self._actual + self._estimated),
            "reserved_cost_usd": float(self._reserved), "budget_committed_usd": float(committed),
            "remaining_budget_usd": float(self.budget - committed),
            "prompt_tokens": self._prompt, "completion_tokens": self._completion,
            "total_tokens": self._prompt + self._completion,
            "cached_tokens": self._cached if self._cache_unknown + unaccounted == 0 else None,
            "known_cached_tokens": self._cached, "cache_usage_unknown_requests": self._cache_unknown + unaccounted,
            "cache_write_tokens": self._cache_write if self._cache_write_unknown + unaccounted == 0 else None,
            "known_cache_write_tokens": self._cache_write,
            "cache_write_usage_unknown_requests": self._cache_write_unknown + unaccounted,
            "latency_seconds": self._latency, "stopped": self._stopped,
            "timeout_retries": self.timeout_retries, "timeouts_retried": self._timeouts_retried,
            "rate_limit_retries": self.rate_limit_retries, "rate_limits_retried": self._rate_limits_retried,
            "retry_policy": "only hung requests are retried, up to timeout_retries; every other failure aborts; unknown billing retains full reservation",
            "estimate_policy": "maximum fixed-provider prices; cache discounts only when reported; unknown writes use maximum input price",
        }
