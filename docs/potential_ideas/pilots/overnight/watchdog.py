"""Protect the shared OpenRouter quota during unattended runs.

Every minute: read recent errors and call volume. Pause all traffic (create PAUSE) for a
cooldown when rate-limit errors spike; pause until a probe succeeds when a quota or credit
error appears. Writes one status line per minute to monitor.log. Runs for --minutes then exits.
"""
import argparse, json, os, time, urllib.request
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAUSE, ERRORS, USAGE, LOG = HERE / "PAUSE", HERE / "errors.jsonl", HERE / "usage.jsonl", HERE / "monitor.log"
QUOTA_WORDS = ("quota", "credit", "insufficient", "exceeded", "limit reached", "daily")


def tail_records(path, seconds, max_lines=60000):
    if not path.exists():
        return []
    with open(path) as f:
        lines = deque(f, maxlen=max_lines)
    now, out = time.time(), []
    for line in lines:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if now - r.get("t", 0) < seconds:
            out.append(r)
    return out


def probe():
    """One tiny call that bypasses the PAUSE file; returns (ok, detail)."""
    import orclient
    body = json.dumps({"model": orclient.MODEL, "max_tokens": 5,
                       "messages": [{"role": "user", "content": "Say ok"}]}).encode()
    req = urllib.request.Request(orclient.URL, data=body, headers={
        "Authorization": f"Bearer {orclient.KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        return ("choices" in d), str(d.get("error", ""))[:200]
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} {e.read()[:200]!r}"
    except Exception as e:
        return False, repr(e)[:200]


def log(msg):
    with open(LOG, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=110)
    args = ap.parse_args()
    end = time.time() + args.minutes * 60
    paused_until, hard = 0, False
    while time.time() < end:
        errs = tail_records(ERRORS, 300)
        calls = len(tail_records(USAGE, 300))
        n429 = sum(e["kind"] == "http429" for e in errs)
        quota = [e for e in errs if e["kind"] in ("http402",) or any(w in e["detail"].lower() for w in QUOTA_WORDS)]
        if quota and not hard:
            hard = True
            PAUSE.write_text("quota/credit error: " + quota[-1]["detail"])
            log(f"HARD PAUSE: {quota[-1]['detail']}")
        elif n429 > max(30, 0.25 * calls) and not PAUSE.exists():
            paused_until = time.time() + 300
            PAUSE.write_text(f"429 spike: {n429} in 5 min vs {calls} calls")
            log(f"PAUSE 5 min: {n429} 429s vs {calls} calls")
        if PAUSE.exists() and (hard or time.time() > paused_until):
            ok, detail = probe()
            if ok:
                PAUSE.unlink(missing_ok=True)
                hard = False
                log("probe ok, resumed")
            else:
                paused_until = time.time() + 300
                log(f"probe failed, staying paused: {detail}")
        log(f"calls/5min={calls} errors/5min={len(errs)} 429={n429} paused={PAUSE.exists()}")
        time.sleep(60)
    log("watchdog exiting (time limit)")


if __name__ == "__main__":
    main()
