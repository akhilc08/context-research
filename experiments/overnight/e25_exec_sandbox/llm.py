"""Cached chat client for E25 (adapted from E22's llm.py).

Uses the shared orclient for the API key, URL, cross-process rate cap and logs, but does the HTTP call itself so it
can return token usage, keep an on-disk sqlite cache, cap concurrency at 8 in-flight calls (the semaphore is held
only during the HTTP attempt, not during backoff), and deduplicate identical requests that are in flight at once.

Cache key = sha256(scope + request body). Scope is "<repo>:t<trial>", so arms of the same repo and trial that send
byte-identical requests (every arm before the first compaction; the three compacting arms at the first compaction)
get the same reply: a common-random-numbers design. Different trials never share replies.
"""
import hashlib, json, os, random, sqlite3, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import orclient  # noqa: E402

CACHE = HERE / "results" / "cache.sqlite"
MODEL = os.environ.get("E25_MODEL", orclient.MODEL)  # second backbone: E25_MODEL=<openrouter id>
_lock = threading.Lock()
_sem = threading.Semaphore(8)
_inflight = {}
_db = None


def _conn():
    global _db
    if _db is None:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        _db = sqlite3.connect(str(CACHE), check_same_thread=False, timeout=60)
        _db.execute("PRAGMA journal_mode=WAL")
        _db.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT)")
        _db.commit()
    return _db


def _get(k):
    with _lock:
        row = _conn().execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
    return json.loads(row[0]) if row else None


def _put(k, v):
    with _lock:
        _conn().execute("INSERT OR REPLACE INTO c VALUES (?,?)", (k, json.dumps(v)))
        _conn().commit()


def chat(messages, *, scope, model=None, max_tokens=4000, temperature=0.7, tools=None,
         reasoning_effort="low", tag="", retries=12):
    """Return (message_dict, usage_dict, cached_bool). Raises RuntimeError after retries."""
    model = model or MODEL
    assert ":free" not in model, "':free' models are not allowed"
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if reasoning_effort:
        body["reasoning"] = {"effort": reasoning_effort, "exclude": True}
    if tools:
        body["tools"] = tools
    data = json.dumps(body, sort_keys=True)
    key = hashlib.sha256((scope + "\n" + data).encode()).hexdigest()
    while True:
        hit = _get(key)
        if hit is not None:
            return hit["msg"], hit["usage"], True
        with _lock:
            ev = _inflight.get(key)
            if ev is None:
                _inflight[key] = threading.Event()
                break
        ev.wait(600)
    try:
        return _call(key, data.encode(), model, tag, retries)
    finally:
        with _lock:
            _inflight.pop(key).set()


def _call(key, payload, model, tag, retries):
    delay, last = 2.0, None
    for attempt in range(retries):
        orclient._throttle()
        req = urllib.request.Request(orclient.URL, data=payload, headers={
            "Authorization": f"Bearer {orclient.KEY}", "Content-Type": "application/json",
            "X-Title": "context-research overnight"})
        t0 = time.time()
        try:
            with _sem:
                with urllib.request.urlopen(req, timeout=300) as r:
                    resp = json.loads(r.read())
            if "error" in resp:
                raise RuntimeError(str(resp["error"])[:300])
            msg = resp["choices"][0]["message"]
            if not (msg.get("content") or "").strip() and not msg.get("tool_calls"):
                raise RuntimeError("empty completion")
            u = resp.get("usage", {}) or {}
            usage = {"in": u.get("prompt_tokens") or 0, "out": u.get("completion_tokens") or 0}
            with orclient._lock, open(orclient.USAGE_LOG, "a") as f:
                f.write(json.dumps({"t": round(t0), "tag": tag, "in": usage["in"], "out": usage["out"],
                                    "sec": round(time.time() - t0, 2)}) + "\n")
            tcs = msg.get("tool_calls") or None
            if tcs:
                tcs = [{"id": tc.get("id"), "type": "function",
                        "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments") or "{}"}}
                       for tc in tcs]
            keep = {"content": msg.get("content") or "", "tool_calls": tcs}
            _put(key, {"msg": keep, "usage": usage})
            return keep, usage, False
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
            orclient._log_error(f"http{e.code}", f"{model} {last}")
            if e.code in (400, 401, 403) and attempt > 1:
                break
        except Exception as e:
            last = repr(e)[:300]
            orclient._log_error("other", f"{model} {last}")
        time.sleep(delay + random.random() * delay)
        delay = min(delay * 1.7, 90)
    raise RuntimeError(f"chat failed after {retries} tries: {last}")
