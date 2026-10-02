"""Shared OpenRouter client for the overnight studies.

Loads OPENROUTER_API_KEY from the repository's .env at import time (never printed),
retries on rate limits and transient errors, and logs every call's token usage.
"""
import json, os, random, threading, time, urllib.error, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MODEL = "stealth/space-bunny-alpha"
URL = "https://openrouter.ai/api/v1/chat/completions"
USAGE_LOG = Path(__file__).resolve().parent / "usage.jsonl"
_lock = threading.Lock()


def _load_key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENROUTER_API_KEY not found")


KEY = _load_key()


def chat(messages, max_tokens=400, temperature=0.7, model=MODEL, reasoning_effort="low",
         tag="", retries=12, json_mode=False, tools=None, raw=False):
    """Return the assistant text (or the full message dict when raw=True)."""
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if reasoning_effort:
        body["reasoning"] = {"effort": reasoning_effort, "exclude": True}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if tools:
        body["tools"] = tools
    data = json.dumps(body).encode()
    delay = 2.0
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(URL, data=data, headers={
            "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
            "X-Title": "context-research overnight"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                resp = json.loads(r.read())
            if "error" in resp:
                raise RuntimeError(str(resp["error"])[:300])
            msg = resp["choices"][0]["message"]
            text = msg.get("content") or ""
            if not text.strip() and not msg.get("tool_calls"):
                raise RuntimeError("empty completion")
            u = resp.get("usage", {})
            with _lock, open(USAGE_LOG, "a") as f:
                f.write(json.dumps({"t": round(t0), "tag": tag, "in": u.get("prompt_tokens"),
                                    "out": u.get("completion_tokens"), "sec": round(time.time() - t0, 2)}) + "\n")
            return msg if raw else text
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
            if e.code in (400, 401, 403) and attempt > 1:
                break
        except Exception as e:  # network, timeout, empty, provider error
            last = repr(e)[:300]
        time.sleep(delay + random.random() * delay)
        delay = min(delay * 1.7, 90)
    raise RuntimeError(f"chat failed after {retries} tries: {last}")


if __name__ == "__main__":
    t = time.time()
    print(chat([{"role": "user", "content": "Reply with exactly: pong"}], max_tokens=20, tag="ping"))
    print(f"{time.time() - t:.1f}s")
