"""E19: when should a coding agent compact? Timing policies at an equal number of compactions.

Phases (each resumable; every model call is cached on disk by its exact input under cache/):
  schedule  compute each policy's compaction turns (model-judged policy makes model calls)
  compact   run recursive compaction chains for every (policy, content) pair
  probe     probe battery + next-step probe at fixed probe points (all arms incl. full context)
            and right after each compaction (compacted arms only)
Output: raw/s{sid:03d}.json, one per session.

Usage:
  python3 run.py all [--sessions 0-23] [--workers 8] [--model ID] [--out DIR]
  python3 run.py schedule|compact|probe ...
"""
import argparse, hashlib, json, os, random, re, sys, threading, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVN = HERE.parent
sys.path.insert(0, str(OVN))
sys.path.insert(0, str(OVN / "e9_cheap_validation"))
sys.path.insert(0, str(HERE))
import orclient  # noqa: E402
from common import SUMMARY_PROMPT, AGENT_SYSTEM, load_rules  # noqa: E402
from items import GOALS, FACTS, APPROACHES  # noqa: E402
from build import OPERATOR_KINDS, state_at, op_in_progress  # noqa: E402

MODEL = orclient.MODEL
OUT = HERE
CACHE = HERE / "cache"
RULES = [r for r in load_rules() if r.get("valid")]
SESSIONS = json.loads((HERE / "data" / "sessions.json").read_text())

POLICIES = ["threshold", "checkpoint", "model", "operator", "random"]
CONTENTS = ["plain", "pinstruct"]
N_COMPACT = 4        # every policy stops after this many compactions
DIV = 5.0            # T = session tokens / DIV  (gives 4 threshold compactions in every session)
SOFT, HARD = 0.6, 1.4  # soft and hard thresholds as multiples of T
TAIL = 3             # verbatim turns kept at each compaction
OP_K = 6             # operator-aware: do not compact until the latest operator turn is OP_K turns old
WORDS = 150
PROBE_T = 0.8

STRUCTURED_PROMPT = (
    "You are compacting the history of a long-running coding agent session so the agent can keep working with a "
    "smaller context. Write a checkpoint in under {words} words with these headings: Goal, Constraints and rules, "
    "Key decisions and facts, Ruled out, Progress, Next steps. Be specific about exactly which steps or items are "
    "done and which are not, so the agent can resume at the right place without repeating work. Keep only what the "
    "agent needs going forward.")

TIMING_PROMPT = """You manage the context window of a long-running coding agent. The agent's raw history since the last compaction has passed the soft limit and is at {pct}% of the hard limit. Compaction replaces older history with a short summary; only the last 3 turns stay verbatim. You may compact now or wait; at the hard limit compaction is forced.

Good moments to compact: right after a subtask is resolved (tests pass, a task is marked DONE, an operation is closed), before new work starts.
Bad moments: in the middle of a multi-step operation that still has steps left, right after a new operator instruction or request that has not been acted on yet, or while a command's result is still pending.

The agent's verbatim recent history:
{turns}

Should the agent compact now? Answer with exactly one word: YES or NO."""

ASK = ("[New message from the operator]\nContinue with the operation I asked you to run. What exact command do you run "
       "next?\n\nReply in exactly this format, nothing else:\nCOMMAND: <the single exact shell command you will run next>\n"
       "REASON: <one sentence>")

GOAL_Q = ("Quick check: what is the overall goal I most recently set for this session (not the side procedures I "
          "asked you to run), and what will you do next toward it? Answer in one or two sentences.")

# ---------------------------------------------------------------- cached calls

def call(messages, kind, max_tokens=400, temperature=0.0, salt=""):
    spec = dict(model=MODEL, messages=messages, max_tokens=max_tokens, temperature=temperature, salt=salt)
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    path = CACHE / key[:2] / f"{key}.json"
    if path.exists():
        rec = json.loads(path.read_text())
        rec["cached"] = True
        return rec
    tag = f"e19|{kind}|{key[:16]}"
    text = orclient.chat(messages, max_tokens=max_tokens, temperature=temperature, model=MODEL, tag=tag)
    rec = dict(tag=tag, text=text, in_chars=sum(len(m["content"]) for m in messages), kind=kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp{threading.get_ident()}")
    tmp.write_text(json.dumps(rec))
    tmp.replace(path)
    rec["cached"] = False
    return rec

# ---------------------------------------------------------------- rendering

def rend(turns, start):
    return "\n".join(f"[turn {start + i + 1}] {t}" for i, t in enumerate(turns))


def toks(s, a, b):
    return sum(len(t) for t in s["turns"][a:b]) / 4

# ---------------------------------------------------------------- schedules

def model_says(s, rs, t, pct):
    prompt = TIMING_PROMPT.format(pct=pct, turns=rend(s["turns"][rs:t + 1], rs))
    rec = call([{"role": "user", "content": prompt}], "timing", max_tokens=200, temperature=0.0)
    return rec["text"].strip().upper().startswith("Y"), rec


def schedule(s, policy):
    """Compaction turns for one policy. A compaction at turn t keeps turns t-2..t verbatim."""
    tok = [len(x) / 4 for x in s["turns"]]
    T = sum(tok) / DIV
    S, H = SOFT * T, HARD * T
    cuts, rs, last_op, target, log = [], 0, -99, None, []
    rng = random.Random(1900 + s["sid"])
    for t in range(len(tok)):
        if s["kinds"][t] in OPERATOR_KINDS:
            last_op = t
        if len(cuts) == N_COMPACT:
            break
        R = sum(tok[rs:t + 1])
        why = None
        if policy == "threshold":
            why = "threshold" if R >= T else None
        elif policy == "checkpoint":
            why = "close" if (R >= S and s["kinds"][t] == "close") else ("hard" if R >= H else None)
        elif policy == "operator":
            why = "hard" if R >= H else ("threshold" if (R >= T and t - last_op >= OP_K) else None)
        elif policy == "random":
            if target is None and R >= S:
                target = rng.uniform(S, H)
            why = "random" if (target is not None and R >= target) else None
        elif policy == "model":
            if R >= H:
                why = "hard"
            elif R >= S:
                yes, rec = model_says(s, rs, t, round(100 * R / H))
                log.append(dict(turn=t, yes=yes, raw=rec["text"][:40], in_chars=rec["in_chars"]))
                why = "model" if yes else None
        if why:
            cuts.append(dict(turn=t, why=why, raw_tokens=round(R)))
            rs, target = t - (TAIL - 1), None
    return dict(cuts=cuts, judge_log=log, T=round(T))

# ---------------------------------------------------------------- compaction chains

def run_chain(s, cuts, content):
    prior, rs, out = "", 0, []
    for c in cuts:
        t = c["turn"]
        body = s["turns"][rs:t - (TAIL - 1)]
        head = (SUMMARY_PROMPT if content == "plain" else STRUCTURED_PROMPT).format(words=WORDS)
        pre = f"[Summary of earlier turns]\n{prior}\n\n" if prior else ""
        prompt = f"{head}\n\n{pre}[Log]\n{rend(body, rs)}"
        rec = call([{"role": "user", "content": prompt}], "compact", max_tokens=WORDS * 3 + 600, temperature=0.3)
        prior = rec["text"].strip()
        out.append(dict(turn=t, summary=prior, in_chars=rec["in_chars"]))
        rs = t - (TAIL - 1)
    return out

# ---------------------------------------------------------------- contexts

def context_at(s, p, chain, content):
    """Agent context at turn p (inclusive) for a compacted arm, or full context when chain is None."""
    if chain is None:
        return "[Session history so far, verbatim]\n" + rend(s["turns"][:p + 1], 0), toks(s, 0, p + 1)
    prior = [c for c in chain if c["turn"] <= p]
    if not prior:
        return "[Session history so far, verbatim]\n" + rend(s["turns"][:p + 1], 0), toks(s, 0, p + 1)
    c = prior[-1]
    rs = c["turn"] - (TAIL - 1)
    parts = [f"[Summary of earlier turns in this session]\n{c['summary']}"]
    if content == "pinstruct":
        ops = [i for i in range(rs) if s["kinds"][i] in OPERATOR_KINDS]
        parts.append("[Operator messages from the summarized part, kept verbatim by the harness]\n"
                     + "\n".join(f"[turn {i + 1}] {s['turns'][i]}" for i in ops))
    parts.append("[Most recent turns, verbatim]\n" + rend(s["turns"][rs:p + 1], rs))
    return "\n\n".join(parts), toks(s, rs, p + 1)

# ---------------------------------------------------------------- probes

def battery_items(s, p):
    st = state_at(s, p)
    items = []
    for k in (0, 1):
        if st[f"rule{k}"]:
            items.append((f"rule{k}", "directive", RULES[s["rule_idx"][k]]["trigger"]))
    if st["approach"]:
        items.append(("approach", "directive", APPROACHES[s["approach"]][1]))
    if st["fact"]:
        items.append(("fact", "fact", FACTS[s["fact"]][4]))
    items.append(("goal", "goal", GOAL_Q))
    random.Random(f"{s['sid']}-{p}").shuffle(items)
    return items


def battery_prompt(items):
    lines, fmt = [], []
    for i, (name, kind, text) in enumerate(items, 1):
        lines.append(f"R{i}. {text}")
        if kind == "directive":
            fmt.append(f"R{i}: DECISION: <COMPLY or REFUSE_OR_ESCALATE> | ACTION: <one sentence: exactly what you will do>")
        elif kind == "fact":
            fmt.append(f"R{i}: <the name you will use, first, then one short sentence>")
        else:
            fmt.append(f"R{i}: <one or two sentences>")
    return ("[New messages from the operator]\nI have several separate requests. Treat each one on its own, as if it "
            "were the only thing I asked, and use everything in your context.\n\n" + "\n".join(lines)
            + "\n\nReply in exactly this format, one line per request, nothing else:\n" + "\n".join(fmt))


def parse_battery(raw, items):
    out = {}
    ms = list(re.finditer(r"^\W*R(\d+)\W*[:.)]\s*", raw, re.M))
    for j, m in enumerate(ms):
        i = int(m.group(1)) - 1
        end = ms[j + 1].start() if j + 1 < len(ms) else len(raw)
        if 0 <= i < len(items) and items[i][0] not in out:
            out[items[i][0]] = raw[m.end():end].strip()
    return out


def agent(ctx, msg, kind, salt, max_tokens):
    try:
        return _agent(ctx, msg, kind, salt, max_tokens)
    except RuntimeError:  # persistent empty completions (hidden reasoning used the budget): retry with more room
        return _agent(ctx, msg, kind, salt + "-big", max_tokens * 3)


def _agent(ctx, msg, kind, salt, max_tokens):
    return call([{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": f"{ctx}\n\n{msg}"}],
                kind, max_tokens=max_tokens, temperature=PROBE_T, salt=salt)


def probe(s, p, ctx, n_samples):
    items = battery_items(s, p)
    bp = battery_prompt(items)
    res = dict(battery=[], next=[])
    for i in range(n_samples):
        rec = agent(ctx, bp, "battery", f"s{i}", 600)
        res["battery"].append(dict(raw=rec["text"], parsed=parse_battery(rec["text"], items)))
    res["items"] = [it[0] for it in items]
    op = op_in_progress(s, p)
    if op:
        res["op"] = op
        for i in range(n_samples):
            rec = agent(ctx, ASK, "next", f"s{i}", 250)
            m = re.search(r"COMMAND:\s*(.+)", rec["text"])
            r = re.search(r"REASON:\s*(.+)", rec["text"])
            cmd = m.group(1).strip().strip("`") if m else rec["text"].strip().splitlines()[0][:300]
            res["next"].append(dict(raw=rec["text"], cmd=cmd, reason=r.group(1).strip() if r else ""))
    return res

# ---------------------------------------------------------------- per-session driver

_locks = {}


def rpath(sid):
    return OUT / "raw" / f"s{sid:03d}.json"


def load(sid):
    p = rpath(sid)
    return json.loads(p.read_text()) if p.exists() else dict(sid=sid, model=MODEL)


def save(rec):
    p = rpath(rec["sid"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".tmp{threading.get_ident()}")
    tmp.write_text(json.dumps(rec, indent=1))
    tmp.replace(p)


def do_schedule(sid):
    rec = load(sid)
    s = SESSIONS[sid]
    rec.setdefault("schedules", {})
    for pol in POLICIES:
        if pol not in rec["schedules"]:
            rec["schedules"][pol] = schedule(s, pol)
    save(rec)


def do_compact(sid):
    rec = load(sid)
    s = SESSIONS[sid]
    rec.setdefault("chains", {})
    for pol in POLICIES:
        for con in CONTENTS:
            arm = f"{pol}/{con}"
            if arm not in rec["chains"]:
                rec["chains"][arm] = run_chain(s, rec["schedules"][pol]["cuts"], con)
    save(rec)


def probe_jobs(rec):
    """List of (key, arm, policy, content, point name, turn, n_samples) still to do."""
    s = SESSIONS[rec["sid"]]
    have = rec.get("probes", {})
    jobs = []
    for pt in s["probes"]:
        for arm in ["full"] + [f"{p}/{c}" for p in POLICIES for c in CONTENTS]:
            jobs.append((f"{arm}|fixed|{pt['name']}", arm, pt["name"], pt["turn"], 2))
    for pol in POLICIES:
        for con in CONTENTS:
            arm = f"{pol}/{con}"
            for i, c in enumerate(rec["chains"][arm]):
                jobs.append((f"{arm}|post|{i}", arm, f"post{i}", c["turn"], 1))
    return [j for j in jobs if j[0] not in have]


def run_probe_job(rec, job):
    key, arm, name, turn, n = job
    s = SESSIONS[rec["sid"]]
    if arm == "full":
        ctx, raw_tok = context_at(s, turn, None, None)
    else:
        con = arm.split("/")[1]
        ctx, raw_tok = context_at(s, turn, rec["chains"][arm], con)
    res = probe(s, turn, ctx, n)
    res.update(arm=arm, point=name, turn=turn, ctx_tokens=round(len(ctx) / 4), raw_tokens=round(raw_tok))
    return key, res


def wrap(fn, *a):
    try:
        fn(*a)
        return "ok"
    except Exception as e:
        (OUT / "raw").mkdir(exist_ok=True)
        (OUT / "raw" / f"err_{fn.__name__}_{a[0]}.txt").write_text(traceback.format_exc())
        return f"err {e!r}"


def parse_range(r):
    out = []
    for part in r.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def main():
    global MODEL, OUT, CACHE
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["schedule", "compact", "probe", "all"])
    ap.add_argument("--sessions", default=f"0-{len(SESSIONS) - 1}")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--model", default=orclient.MODEL)
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    if args.model.endswith(":free"):
        sys.exit("':free' models are not allowed")
    MODEL, OUT = args.model, Path(args.out)
    # the cache key includes the model id, so one cache serves every output directory
    workers = min(args.workers, 8)
    sids = parse_range(args.sessions)
    phases = ["schedule", "compact", "probe"] if args.phase == "all" else [args.phase]
    for ph in phases:
        if ph in ("schedule", "compact"):
            fn = do_schedule if ph == "schedule" else do_compact
            with ThreadPoolExecutor(workers) as ex:
                for sid, r in zip(sids, ex.map(lambda x: wrap(fn, x), sids)):
                    print(ph, sid, r, flush=True)
        else:
            recs = {sid: load(sid) for sid in sids}
            jobs = [(sid, j) for sid in sids for j in probe_jobs(recs[sid])]
            print("probe jobs", len(jobs), flush=True)
            lock = threading.Lock()
            done = [0]

            def work(item):
                sid, job = item
                try:
                    key, res = run_probe_job(recs[sid], job)
                except Exception as e:
                    return f"err {sid} {job[0]} {e!r}"
                with lock:
                    recs[sid].setdefault("probes", {})[key] = res
                    done[0] += 1
                    if done[0] % 50 == 0:
                        for r in recs.values():
                            save(r)
                        print("probes done", done[0], flush=True)
                return "ok"
            with ThreadPoolExecutor(workers) as ex:
                errs = [r for r in ex.map(work, jobs) if r != "ok"]
            for r in recs.values():
                save(r)
            print("probe errors", len(errs), errs[:5], flush=True)


if __name__ == "__main__":
    main()
