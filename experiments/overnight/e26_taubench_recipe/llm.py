"""Cached chat client, copied from E22 for E26 (unchanged except this note; the cache file is E26's own copy
of E22's cache, and E26 keeps E22's scope format so identical requests reuse E22's replies).

Uses the shared orclient for the API key, URL, cross-process rate cap and logs, but does the HTTP call
itself so it can return token usage and keep an on-disk cache (sqlite).

Cache key = sha256 of (scope, model, request body). The scope is "<domain>:<task>:<trial>", so two arms
of the same task and trial that send byte-identical requests (for example hist and compact before the
first compaction) get the same reply. This is a deliberate common-random-numbers design: arms share
their trajectory up to the point where their contexts differ. Different trials never share replies.
"""
import hashlib, json, random, sqlite3, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import orclient  # noqa: E402

CACHE = HERE / "results" / "cache.sqlite"
_lock = threading.Lock()
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


def chat(messages, *, scope, model, max_tokens=400, temperature=0.0, tools=None,
         reasoning_effort="low", tag="", retries=10):
    """Return (message_dict, usage_dict, cached_bool). Raises RuntimeError after retries."""
    assert ":free" not in model, "':free' models are not allowed"
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if reasoning_effort:
        body["reasoning"] = {"effort": reasoning_effort, "exclude": True}
    if tools:
        body["tools"] = tools
    data = json.dumps(body, sort_keys=True)
    key = hashlib.sha256((scope + "\n" + data).encode()).hexdigest()
    hit = _get(key)
    if hit is not None:
        return hit["msg"], hit["usage"], True
    payload = data.encode()
    delay, last = 2.0, None
    for attempt in range(retries):
        orclient._throttle()
        req = urllib.request.Request(orclient.URL, data=payload, headers={
            "Authorization": f"Bearer {orclient.KEY}", "Content-Type": "application/json",
            "X-Title": "context-research overnight"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
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
            keep = {"content": msg.get("content") or "", "tool_calls": msg.get("tool_calls")}
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
