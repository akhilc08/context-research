"""E14: a versioned fact pin (keep each fact's value history) with optional key canonicalization.

Builds on E4 (../e04_supersede). Same tasks, NOTES protocol, extraction prompt, and judge.
Run with the Supersede venv:

    PY=/private/tmp/supersede-venv/bin/python
    $PY e14.py --stage run      # every arm except the token-matched control, reps 1 and 2
    $PY e14.py --stage tm       # token-matched notes control (budget set from stage-run memory sizes)
    $PY e14.py --stage judge    # LongMemEval judging (synthetic tasks are graded exactly in analyze.py)
    $PY e14.py --stage orphan   # measurement-only duplicate-key audit of LongMemEval stores

Repeat 1 reuses E4's raw outputs for the arms E4 already ran (full, notes300, notes1200, the E4
extraction, and the E4 pin answer to the current-value question), copied into results/units/rep1.
Repeat 2 reruns every call from scratch. Everything is cached per unit, so reruns resume.
Model calls are tagged "e14|rep<r>|<set>|<qid>|<unit>|<kind>" in the shared usage.jsonl.
"""
import argparse, json, re, shutil, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
E4 = HERE.parent / "e04_supersede" / "results" / "units"
sys.path.insert(0, str(HERE.parent / "shared"))                 # orclient
sys.path.insert(0, "/private/tmp/supersede/src")     # supersede
from orclient import chat                            # noqa: E402
from supersede.rollout import MEMORY_SYSTEM, ANSWER_SYSTEM, memory_prompt, question_prompt  # noqa: E402
from supersede.dataset import load_longmemeval, synthetic_tasks                              # noqa: E402

LME_PATH = "/private/tmp/supersede/data/longmemeval_oracle.json"
DEFAULT_MODEL = "stealth/space-bunny-alpha"
CFG = {"model": DEFAULT_MODEL, "judge_model": DEFAULT_MODEL, "suffix": "", "units": HERE / "results" / "units"}
ANSWER_FULL = ("The following is the full history of your past conversations with the "
               "user. Answer the user's question based on it. Be concise.")
SYNTH_CFGS = {"synth_std": ({}, 0), "synth_hard": ({"n_tracked": 8, "chain_len": 3, "n_distractors": 10}, 1000)}

# ------------------------------------------------------------------ prompts

EXTRACT = (  # E4's extraction prompt, unchanged
    "You maintain a key-value FACT STORE about a user, built from their conversations with an "
    "assistant. Below are the current store and the transcript of ONE new session.\n\n"
    "List every concrete fact that the USER stated or updated in THIS session about themselves, "
    "people in their life, or their things: counts, amounts, times, dates, durations, frequencies, "
    "places, possessions, statuses, scores, records, goals, plans, and preferences. Facts stated "
    "only by the assistant do not count. Keep each value short and copy numbers exactly.\n"
    "If a fact updates or restates a fact already in the store, reuse that store KEY exactly, so "
    "the new value overwrites the old one. Otherwise make a new key of the form "
    "'<subject> | <attribute>' (lowercase).\n"
    "Return JSON: {{\"facts\": [{{\"key\": \"...\", \"value\": \"...\"}}]}} with at most 30 facts, "
    "or {{\"facts\": []}} if none.\n\n"
    "CURRENT STORE:\n{store}\n\nNEW SESSION:\n{session}"
)
EXTRACT_CANON = (  # E14: same task, plus an explicit key list and a hard key-reuse rule
    "You maintain a versioned FACT STORE about a user, built from their conversations with an "
    "assistant. Below are the EXISTING KEYS (with each key's current value) and the transcript of "
    "ONE new session.\n\n"
    "List every concrete fact that the USER stated or updated in THIS session about themselves, "
    "people in their life, or their things: counts, amounts, times, dates, durations, frequencies, "
    "places, possessions, statuses, scores, records, goals, plans, and preferences. Facts stated "
    "only by the assistant do not count. Keep each value short and copy numbers exactly.\n\n"
    "KEY RULE: one attribute gets exactly one key, for the whole history. Before writing a fact, "
    "look through EXISTING KEYS for a key about the same subject and the same attribute, even if "
    "it is worded differently or its value has changed (for example 'user | commute time' and "
    "'user | daily commute duration' are the same attribute). If there is one, you MUST copy that "
    "existing key exactly and set \"reused\": true; the store keeps the old value as history, so "
    "never invent a new key to hold an updated value. Only if no existing key covers the "
    "attribute, make a new key of the form '<subject> | <attribute>' (lowercase, general enough "
    "to hold future values, e.g. 'user | 5k personal best' not 'user | 5k personal best in may') "
    "and set \"reused\": false.\n"
    "Return JSON: {{\"facts\": [{{\"key\": \"...\", \"value\": \"...\", \"reused\": true}}]}} with at "
    "most 30 facts, or {{\"facts\": []}} if none.\n\n"
    "EXISTING KEYS:\n{keys}\n\nNEW SESSION:\n{session}"
)
PIN_BLOCK = ("\n\nTRACKED FACTS (latest value of each fact the user stated; a newer value "
             "always replaces an older one):\n{kv}")
VPIN_BLOCK = ("\n\nTRACKED FACTS WITH HISTORY (one line per fact. The first value is the CURRENT one "
              "and holds since the session shown. Values after 'previously' are older values it "
              "replaced, newest first, with the sessions in which each held. There were {n} "
              "sessions; a higher session number is more recent):\n{kv}")
JUDGE = (  # Supersede's LongMemEval judge, unchanged (as in E4)
    "You are grading whether a model answer is correct.\n"
    "Question: {q}\nGold answer: {gold}\nModel answer: {ans}\n\n"
    "Is the model answer correct, i.e. does it convey the gold answer (the "
    "current/updated value)? Minor wording differences are fine. Reply with "
    "exactly 'yes' or 'no'.")
JUDGE_ABST = (
    "You are grading whether a model answer is correct.\n"
    "Question: {q}\nExplanation of the correct answer: {gold}\nModel answer: {ans}\n\n"
    "This question cannot be answered from the conversation history. Does the model answer "
    "correctly identify the question as unanswerable (for example, say it does not know or that "
    "the information is not available)? Reply with exactly 'yes' or 'no'.")
JUDGE4 = (  # E4's four-way stale judge, unchanged
    "Classify a model answer to a question about a fact that changed over time.\n"
    "Question: {q}\nCorrect (gold) value: {gold}\nWrong-version value(s): {stale}\n"
    "Model answer: {ans}\n\nReply with exactly one word: 'correct' if it conveys the gold value "
    "and not a wrong-version value, 'stale' if it conveys a wrong-version value instead of the "
    "gold value, 'ambiguous' if it gives both as current, 'wrong' otherwise.")
ORPHAN = (  # measurement only (never shown to a method): E4's dedupe question, asked as an audit
    "Below is a key-value FACT STORE about a user. Some keys may describe the SAME attribute of "
    "the same thing as another key (for example 'user | parents length of stay' and "
    "'parents | length of stay'), so one fact is split across several keys. List every such "
    "group of two or more keys. Keys about different attributes (even of the same thing) are not "
    "a group.\nReturn JSON {{\"groups\": [[\"<key>\", \"<key>\", ...], ...]}} (empty list if none)."
    "\n\nSTORE:\n{store}")

# ------------------------------------------------------------------ helpers


def tg(t, rep, unit, kind):
    return f"e14|rep{rep}|{t['set']}{CFG['suffix']}|{t['qid']}|{unit}|{kind}"


def call(t, rep, unit, kind, content, max_tokens, system=None, json_mode=False, judge=False):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
    return chat(msgs, max_tokens=max_tokens, temperature=0, model=CFG["judge_model"] if judge else CFG["model"],
                tag=tg(t, rep, unit, kind), json_mode=json_mode).strip()


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return None


def unit_path(t, rep, unit):
    return CFG["units"] / f"rep{rep}" / t["set"] / t["qid"] / f"{unit}.json"


def cached(t, rep, unit, fn):
    p = unit_path(t, rep, unit)
    if p.exists():
        return json.loads(p.read_text())
    out = fn()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    return out


def canon_key(k):
    k = re.sub(r"\s+", " ", str(k).strip().lower())
    return re.sub(r"\s*\|\s*", " | ", k)


def vnorm(v):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(v).lower())).strip()


def render_kv(store):
    return "\n".join(f"- {k}: {v}" for k, v in store.items()) or "(empty)"


def build_versioned(facts_per_session):
    """facts_per_session: list (one per session) of [(key, value)]. Returns key -> [{v, s}] in time
    order, where s is the 1-based session in which the value was first stated. A restatement of the
    current value is not a new version."""
    hist = {}
    for i, facts in enumerate(facts_per_session):
        for k, v in facts:
            h = hist.setdefault(k, [])
            if h and vnorm(h[-1]["v"]) == vnorm(v):
                continue
            if h and h[-1]["s"] == i + 1:   # two values for one key in one session: keep the later
                h[-1]["v"] = v
                continue
            h.append({"v": v, "s": i + 1})
    return hist


def render_versioned(hist, n_sessions):
    lines = []
    for k, h in hist.items():
        cur = h[-1]
        line = f"- {k}: {cur['v']} (current, since session {cur['s']})"
        if len(h) > 1:
            olds = []
            for j in range(len(h) - 2, -1, -1):
                a, b = h[j]["s"], h[j + 1]["s"] - 1
                when = f"session {a}" if a >= b else f"sessions {a} to {b}"
                olds.append(f"{h[j]['v']} ({when})")
            line += "; previously " + ", ".join(olds)
        lines.append(line)
    return "\n".join(lines) or "(empty)"


def newest(hist):
    return {k: h[-1]["v"] for k, h in hist.items()}

# ------------------------------------------------------------------ method units


def rewrite(t, rep, unit, notes, session, budget, i):
    out = call(t, rep, unit, f"notes{i}", memory_prompt(notes, session, budget),
               max(800, budget * 2), system=MEMORY_SYSTEM.format(budget=budget))
    return out[:budget], len(out)


def run_notes(t, rep, budget, unit=None):
    unit = unit or f"notes{budget}"
    notes, traj, raw = "", [], []
    for i, s in enumerate(t["sessions"]):
        notes, n_raw = rewrite(t, rep, unit, notes, s, budget, i)
        traj.append(notes); raw.append(n_raw)
    return {"notes": notes, "trajectory": traj, "raw_lens": raw, "budget": budget,
            "truncated": sum(r > budget for r in raw), "calls": len(t["sessions"])}


def run_extract(t, rep):
    """E4's extractor; the per-session fact lists are kept so both semantics can be built."""
    store, per, log = {}, [], []
    for i, s in enumerate(t["sessions"]):
        out = call(t, rep, "extract", f"ext{i}", EXTRACT.format(store=render_kv(store), session=s),
                   3000, json_mode=True)
        j = parse_json(out) or {}
        facts = [(str(f["key"]).strip().lower(), str(f.get("value", "")).strip())
                 for f in j.get("facts", []) if isinstance(f, dict) and f.get("key")]
        for k, v in facts:
            store[k] = v
        per.append(facts)
        log.append({"n": len(facts), "parse_ok": j != {}})
    return {"facts": per, "log": log, "calls": len(t["sessions"]), "source": "e14"}


def run_extract_canon(t, rep):
    hist, per, log = {}, [], []
    for i, s in enumerate(t["sessions"]):
        keys = "\n".join(f"- {k}: {h[-1]['v']}" for k, h in hist.items()) or "(none yet)"
        out = call(t, rep, "extract_canon", f"ext{i}", EXTRACT_CANON.format(keys=keys, session=s),
                   3000, json_mode=True)
        j = parse_json(out) or {}
        facts, claimed_bad = [], 0
        for f in j.get("facts", []):
            if not (isinstance(f, dict) and f.get("key")):
                continue
            k = canon_key(f["key"])
            if f.get("reused") and k not in hist:
                claimed_bad += 1
            facts.append((k, str(f.get("value", "")).strip()))
        per.append(facts)
        hist = build_versioned(per)
        log.append({"n": len(facts), "parse_ok": j != {}, "reused_but_new_key": claimed_bad,
                    "new_keys": sum(1 for k, _ in facts if k not in build_versioned(per[:-1]))})
    return {"facts": per, "log": log, "calls": len(t["sessions"])}


def e4_extract_as_facts(e4ext):
    """Recover per-session fact lists from E4's store snapshots (diff of consecutive snapshots).
    A restatement with an unchanged value is invisible here, which the versioned store ignores anyway."""
    per, prev = [], {}
    for snap in e4ext["snapshots"]:
        per.append([(k, v) for k, v in snap.items() if prev.get(k) != v])
        prev = snap
    return {"facts": per, "log": e4ext["log"], "calls": e4ext["calls"], "source": "e4"}


def answer(t, rep, arm, qk, memory_text, question):
    return {"answer": call(t, rep, f"ans_{arm}", qk, question_prompt(memory_text, question), 400,
                           system=ANSWER_SYSTEM), "memory_chars": len(memory_text)}


def questions(t):
    qs = [("cur", t["question"])]
    if t.get("hist_question"):
        qs.append(("hist", t["hist_question"]))
    return qs


def memories(t, rep, n300, n1200, ext, extc):
    """Answer-time memory text for each memory-based arm."""
    n = len(t["sessions"])
    h_e4 = build_versioned(ext["facts"])
    h_c = build_versioned(extc["facts"])
    return {
        "notes300": n300["notes"],
        "notes1200": n1200["notes"],
        "pin": n300["notes"] + PIN_BLOCK.format(kv=render_kv(newest(h_e4))),
        "vpin": n300["notes"] + VPIN_BLOCK.format(n=n, kv=render_versioned(h_e4, n)),
        "vpin_canon": n300["notes"] + VPIN_BLOCK.format(n=n, kv=render_versioned(h_c, n)),
        "n1200_vpin": n1200["notes"] + VPIN_BLOCK.format(n=n, kv=render_versioned(h_c, n)),
    }


def e4_unit(t, unit):
    p = E4 / t["set"] / t["qid"] / f"{unit}.json"
    return json.loads(p.read_text()) if p.exists() else None


def seed_rep1_from_e4(t):
    """Copy E4's raw outputs into rep1 for the units E4 already ran (same model, prompts, temperature)."""
    for unit in ("notes300", "notes1200"):
        p = unit_path(t, 1, unit)
        src = e4_unit(t, unit)
        if not p.exists() and src:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({**src, "source": "e4"}, indent=1))
    p = unit_path(t, 1, "extract")
    src = e4_unit(t, "extract")
    if not p.exists() and src:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(e4_extract_as_facts(src), indent=1))
    for arm, unit in (("full", "full"), ("notes300", "notes300"), ("notes1200", "notes1200"), ("pin", "pin")):
        p = unit_path(t, 1, f"ans_{arm}_cur")
        src = e4_unit(t, unit)
        if not p.exists() and src:
            p.parent.mkdir(parents=True, exist_ok=True)
            mc = src.get("memory_chars", src.get("context_chars", len(src.get("notes", ""))))
            p.write_text(json.dumps({"answer": src["answer"], "memory_chars": mc, "source": "e4"}, indent=1))


def run_task(t, rep):
    if rep == 1 and CFG["suffix"] == "":
        seed_rep1_from_e4(t)
    n300 = cached(t, rep, "notes300", lambda: run_notes(t, rep, 300))
    n1200 = cached(t, rep, "notes1200", lambda: run_notes(t, rep, 1200))
    ext = cached(t, rep, "extract", lambda: run_extract(t, rep))
    extc = cached(t, rep, "extract_canon", lambda: run_extract_canon(t, rep))
    mem = memories(t, rep, n300, n1200, ext, extc)
    blocks = "\n\n".join(f"[Session {i + 1}]\n{s}" for i, s in enumerate(t["sessions"]))
    for qk, q in questions(t):
        cached(t, rep, f"ans_full_{qk}", lambda: {
            "answer": call(t, rep, "ans_full", qk, f"{blocks}\n\nQuestion: {q}", 400, system=ANSWER_FULL),
            "memory_chars": len(blocks)})
        for arm, m in mem.items():
            cached(t, rep, f"ans_{arm}_{qk}", lambda: answer(t, rep, arm, qk, m, q))
    return t["qid"]


def run_tm(t, rep, budget):
    unit = f"notes_tm{budget}"
    ntm = cached(t, rep, unit, lambda: run_notes(t, rep, budget, unit=unit))
    for qk, q in questions(t):
        cached(t, rep, f"ans_notes_tm_{qk}", lambda: {**answer(t, rep, "notes_tm", qk, ntm["notes"], q),
                                                      "budget": budget})
    return t["qid"]

# ------------------------------------------------------------------ judging and audits

ABST = "information provided is not enough"


def judge_lme(t, rep, arms, stale_label):
    """E4's yes/no judge plus its four-way stale judge, using E4's per-task wrong-version labels."""
    out = {"stale_label": stale_label}
    abst = ABST in t["answer"].lower()
    for a in arms:
        p = unit_path(t, rep, f"ans_{a}_cur")
        if not p.exists():
            continue
        ans = json.loads(p.read_text())["answer"]
        tmpl = JUDGE_ABST if abst else JUDGE
        yn = call(t, rep, "judge", f"yn_{a}", tmpl.format(q=t["question"], gold=t["answer"], ans=ans), 200, judge=True)
        v4 = None
        if stale_label:
            v4 = call(t, rep, "judge", f"j4_{a}", JUDGE4.format(q=t["question"], gold=t["answer"],
                      stale="; ".join(stale_label), ans=ans), 200, judge=True).lower().split()[0].strip(".'\"")
        out[a] = {"yes": yn.lower().startswith("y"), "raw": yn, "v4": v4, "answer": ans}
    return out


def run_judge(t, rep, arms):
    e4j = e4_unit(t, "judge") or {}
    stale = e4j.get("stale_label", [])
    p = unit_path(t, rep, "judge")
    prev = json.loads(p.read_text()) if p.exists() else {}
    todo = [a for a in arms if a not in prev and unit_path(t, rep, f"ans_{a}_cur").exists()]
    if todo:
        new = judge_lme(t, rep, todo, stale)
        prev.update({k: v for k, v in new.items()})
        p.write_text(json.dumps(prev, indent=1))
    return t["qid"]


def run_orphan(t, rep):
    out = {}
    for unit in ("extract", "extract_canon"):
        ext = json.loads(unit_path(t, rep, unit).read_text())
        cur = newest(build_versioned(ext["facts"]))
        if len(cur) < 2:
            out[unit] = {"groups": [], "n_keys": len(cur)}
            continue
        j = parse_json(call(t, rep, "orphan", unit, ORPHAN.format(store=render_kv(cur)), 1500,
                            json_mode=True, judge=True)) or {}
        groups = [[canon_key(k) for k in g] for g in j.get("groups", []) if isinstance(g, list)]
        groups = [[k for k in g if k in {canon_key(x) for x in cur}] for g in groups]
        out[unit] = {"groups": [g for g in groups if len(g) > 1], "n_keys": len(cur)}
    return out

# ------------------------------------------------------------------ tasks and driver

def hist_question(q):
    m = re.search(r"'(\w+) (.+?) ___'", q)
    return (f"What was the previous value for: '{m.group(1)} {m.group(2)} ___', i.e. the value it had "
            f"just before it changed to its current value? Reply with only that single previous value, "
            f"nothing else.")


def load_tasks(sets, n_synth):
    tasks = []
    if "lme" in sets:
        for x in load_longmemeval(LME_PATH):
            tasks.append({"set": "lme", "qid": x["info"]["qid"], "question": x["question"],
                          "answer": str(x["answer"]), "sessions": x["sessions"], "stale": []})
    for name, (kw, start) in SYNTH_CFGS.items():
        if name in sets:
            for x in synthetic_tasks(n_synth, start_seed=start, **kw):
                st = x["info"]["stale_values"]
                tasks.append({"set": name, "qid": x["info"]["qid"], "question": x["question"],
                              "answer": x["answer"], "sessions": x["sessions"], "stale": st,
                              "hist_question": hist_question(x["question"]),
                              "hist_answer": st[-1], "hist_wrong": [x["answer"]] + st[:-1]})
    return tasks


_print = threading.Lock()


def pool(jobs, workers):
    with ThreadPoolExecutor(min(workers, 8)) as ex:
        futs = [ex.submit(*j) for j in jobs]
        done = 0
        for f in futs:
            try:
                f.result()
                done += 1
                if done % 25 == 0:
                    with _print:
                        print(f"{done}/{len(futs)} done", flush=True)
            except Exception as e:
                with _print:
                    print("FAILED", repr(e)[:300], flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["run", "tm", "judge", "orphan"], default="run")
    ap.add_argument("--sets", nargs="+", default=["lme", "synth_std", "synth_hard"])
    ap.add_argument("--reps", nargs="+", type=int, default=[1, 2])
    ap.add_argument("--n-synth", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--tm-budget", type=int, default=0, help="token-matched notes budget (chars); 0 = read results/tm_budget.json")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="backbone for every method call")
    ap.add_argument("--judge-model", default=DEFAULT_MODEL, help="grader model (keep fixed across backbones)")
    a = ap.parse_args()
    if ":free" in a.model or ":free" in a.judge_model:
        sys.exit("':free' models are not allowed")
    CFG.update(model=a.model, judge_model=a.judge_model)
    if a.model != DEFAULT_MODEL:   # second backbone: separate tree and tags, no E4 reuse
        safe = re.sub(r"[^\w]+", "_", a.model)
        CFG.update(suffix=f"@{safe}", units=HERE / "results" / f"units_{safe}")
    tasks = load_tasks(a.sets, a.n_synth)
    if a.limit:
        by = {}
        for t in tasks:
            by.setdefault(t["set"], []).append(t)
        tasks = [t for v in by.values() for t in v[:a.limit]]
    (HERE / "results").mkdir(exist_ok=True)
    meta = HERE / "results" / "tasks_meta.json"
    if not meta.exists():
        meta.write_text(json.dumps([{k: t.get(k) for k in ("set", "qid", "question", "answer", "stale", "hist_question",
                                                           "hist_answer", "hist_wrong")} | {"n_sessions": len(t["sessions"])}
                                    for t in load_tasks(["lme", "synth_std", "synth_hard"], a.n_synth)], indent=1))
    if a.stage == "run":
        pool([(run_task, t, r) for r in a.reps for t in tasks], a.workers)
    elif a.stage == "tm":
        tm = json.loads((HERE / "results" / "tm_budget.json").read_text())
        jobs = []
        for r in a.reps:
            for t in tasks:
                b = a.tm_budget or tm.get(t["set"])
                if b:
                    jobs.append((run_tm, t, r, b))
        pool(jobs, a.workers)
    elif a.stage == "judge":
        arms = ["full", "notes300", "notes1200", "pin", "vpin", "vpin_canon", "n1200_vpin", "notes_tm"]
        pool([(run_judge, t, r, arms) for r in a.reps for t in tasks if t["set"] == "lme"], a.workers)
    elif a.stage == "orphan":
        jobs = [(lambda t, r: cached(t, r, "orphan_audit", lambda: run_orphan(t, r)), t, r)
                for r in a.reps for t in tasks if t["set"] == "lme"]
        pool(jobs, a.workers)


if __name__ == "__main__":
    main()
