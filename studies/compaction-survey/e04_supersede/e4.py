"""E4: knowledge-update under bounded notes (recursive compaction) with fact watchpoints.

Reuses Supersede's data loaders, NOTES protocol (prompts, per-session rewrite, hard
character cap), and string grader. Run with the Supersede venv:

    /private/tmp/supersede-venv/bin/python e4.py --sets lme synth_std synth_hard

Every unit (task x arm chain) is cached to results/units/<set>/<qid>/<unit>.json, so a
rerun resumes where it stopped. Model calls are tagged "e4|<set>|<qid>|<unit>|<kind>"
so token use can be recovered from the shared usage.jsonl.
"""
import argparse, json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))                 # orclient
sys.path.insert(0, "/private/tmp/supersede/src")     # supersede
from orclient import chat                            # noqa: E402
from supersede.rollout import MEMORY_SYSTEM, ANSWER_SYSTEM, memory_prompt, question_prompt  # noqa: E402
from supersede.dataset import load_longmemeval, synthetic_tasks                              # noqa: E402

LME_PATH = "/private/tmp/supersede/data/longmemeval_oracle.json"
DEFAULT_MODEL = "stealth/space-bunny-alpha"
UNITS = HERE / "results" / "units"
CFG = {"model": DEFAULT_MODEL, "judge_model": DEFAULT_MODEL, "suffix": ""}
ANSWER_FULL = ("The following is the full history of your past conversations with the "
               "user. Answer the user's question based on it. Be concise.")
WORKERS = 12

# ------------------------------------------------------------------ prompts (new)

EXTRACT = (
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
CHECK = (
    "Below are an assistant's NOTES (its only memory) and a list of fact KEYS. For each key, "
    "state the value the NOTES give for it right now, copying it from the notes. If the notes do "
    "not state it, write NOT_IN_NOTES. Use only the notes.\n"
    "Return JSON keyed by each key's ID: {{\"K1\": \"<value or NOT_IN_NOTES>\", ...}} with every ID.\n\n"
    "NOTES:\n{notes}\n\nKEYS:\n{keys}"
)
PIN_BLOCK = ("\n\nTRACKED FACTS (latest value of each fact the user stated; a newer value "
             "always replaces an older one):\n{kv}")
JUDGE = (  # Supersede's LongMemEval judge, unchanged
    "You are grading whether a model answer is correct.\n"
    "Question: {q}\nGold answer: {gold}\nModel answer: {ans}\n\n"
    "Is the model answer correct, i.e. does it convey the gold answer (the "
    "current/updated value)? Minor wording differences are fine. Reply with "
    "exactly 'yes' or 'no'.")
JUDGE_ABST = (  # LongMemEval's abstention protocol, same yes/no form
    "You are grading whether a model answer is correct.\n"
    "Question: {q}\nExplanation of the correct answer: {gold}\nModel answer: {ans}\n\n"
    "This question cannot be answered from the conversation history. Does the model answer "
    "correctly identify the question as unanswerable (for example, say it does not know or that "
    "the information is not available)? Reply with exactly 'yes' or 'no'.")
LABEL_STALE = (
    "Below are two conversation sessions between a user and an assistant, a question asked "
    "afterwards, and its gold answer. The sessions contain a fact that changed between versions. "
    "Give the OTHER version's value: the value a model would give if it used the wrong version "
    "of the fact (normally the older, superseded value; if the question asks for the previous "
    "value, give the newer one). Return JSON {{\"wrong_version\": [\"...\"]}}, or an empty list if "
    "there is no such value.\n\n{sessions}\n\nQuestion: {q}\nGold answer: {gold}")
JUDGE4 = (
    "Classify a model answer to a question about a fact that changed over time.\n"
    "Question: {q}\nCorrect (gold) value: {gold}\nWrong-version value(s): {stale}\n"
    "Model answer: {ans}\n\nReply with exactly one word: 'correct' if it conveys the gold value "
    "and not a wrong-version value, 'stale' if it conveys a wrong-version value instead of the "
    "gold value, 'ambiguous' if it gives both as current, 'wrong' otherwise.")

# ------------------------------------------------------------------ helpers

def tg(t, unit, kind):
    return f"e4|{t['set']}{CFG['suffix']}|{t['qid']}|{unit}|{kind}"


def call(t, unit, kind, content, max_tokens, system=None, json_mode=False):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
    model = CFG["judge_model"] if unit == "judge" else CFG["model"]
    return chat(msgs, max_tokens=max_tokens, temperature=0, model=model, tag=tg(t, unit, kind),
                json_mode=json_mode).strip()


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


def render_kv(store):
    return "\n".join(f"- {k}: {v}" for k, v in store.items()) or "(empty)"


NUMW = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven "
                                        "twelve thirteen fourteen fifteen sixteen seventeen eighteen "
                                        "nineteen twenty".split())}
STOP = set("a an the of to in on at for and or my your is are was were i you it its with by from "
           "as be has have had that this per at least about around approximately roughly just".split())


def norm(s):
    s = re.sub(r"[^\w\s]", " ", str(s).lower())
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s)
    return [re.sub(r"(?<=\w\w\w)s$", "", NUMW.get(w, w)) for w in s.split()]


def value_matches(kv_value, restated):
    """Fixed keyword comparator (the paper's extraction-based check): every number in the
    tracked value must appear in the restatement, and at least half its content words must too."""
    if not restated or "NOT_IN_NOTES" in str(restated).upper():
        return False
    a, b = norm(kv_value), set(norm(restated))
    nums = [w for w in a if any(c.isdigit() for c in w)]
    if any(n not in b for n in nums):
        return False
    content = [w for w in a if w not in STOP and w not in nums]
    if not content:
        return bool(nums)
    return sum(w in b for w in content) / len(content) >= 0.5


def value_matches_strict(kv_value, restated):
    """Follow-up comparator: the tracked value must be present (as above) AND the restatement
    may add no content words beyond it, so notes that list a stale value next to the current
    one (e.g. 'pollen, gluten, soy' for 'soy') count as a miss and get patched."""
    if not value_matches(kv_value, restated):
        return False
    a = set(norm(kv_value))
    extra = [w for w in norm(restated) if w not in a and w not in STOP]
    return not extra


def unit_path(t, unit):
    return UNITS / t["set"] / t["qid"] / f"{unit}.json"


def cached(t, unit, fn):
    p = unit_path(t, unit)
    if p.exists():
        return json.loads(p.read_text())
    out = fn()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    return out

# ------------------------------------------------------------------ arms

def run_full(t):
    blocks = "\n\n".join(f"[Session {i + 1}]\n{s}" for i, s in enumerate(t["sessions"]))
    ans = call(t, "full", "answer", f"{blocks}\n\nQuestion: {t['question']}", 400, system=ANSWER_FULL)
    return {"answer": ans, "calls": 1, "context_chars": len(blocks)}


def rewrite(t, unit, notes, session, budget, i):
    out = call(t, unit, f"notes{i}", memory_prompt(notes, session, budget),
               max(800, budget * 2), system=MEMORY_SYSTEM.format(budget=budget))
    return out[:budget], len(out)


def run_notes(t, budget):
    unit = f"notes{budget}"
    notes, traj, raw = "", [], []
    for i, s in enumerate(t["sessions"]):
        notes, n_raw = rewrite(t, unit, notes, s, budget, i)
        traj.append(notes); raw.append(n_raw)
    ans = call(t, unit, "answer", question_prompt(notes, t["question"]), 400, system=ANSWER_SYSTEM)
    return {"answer": ans, "notes": notes, "trajectory": traj, "raw_lens": raw,
            "truncated": sum(r > budget for r in raw), "calls": len(t["sessions"]) + 1}


def run_extract(t):
    store, snaps, log = {}, [], []
    for i, s in enumerate(t["sessions"]):
        out = call(t, "extract", f"ext{i}", EXTRACT.format(store=render_kv(store), session=s),
                   3000, json_mode=True)
        j = parse_json(out) or {}
        facts = [f for f in j.get("facts", []) if isinstance(f, dict) and f.get("key")]
        overwritten = 0
        for f in facts:
            k = str(f["key"]).strip().lower()
            v = str(f.get("value", "")).strip()
            if k in store and store[k] != v:
                overwritten += 1
            store[k] = v
        snaps.append(dict(store))
        log.append({"n_new": len(facts), "overwritten": overwritten, "parse_ok": j != {}})
    return {"snapshots": snaps, "log": log, "calls": len(t["sessions"]),
            "store_size": len(store), "store_chars": len(render_kv(store))}


def run_pin(t, n300, ext):
    kv = ext["snapshots"][-1]
    q = question_prompt(n300["notes"] + PIN_BLOCK.format(kv=render_kv(kv)), t["question"])
    ans = call(t, "pin", "answer", q, 400, system=ANSWER_SYSTEM)
    return {"answer": ans, "calls": 1, "memory_chars": len(n300["notes"]) + len(render_kv(kv))}


def run_kv_only(t, ext):
    kv = ext["snapshots"][-1]
    q = question_prompt("(no notes)" + PIN_BLOCK.format(kv=render_kv(kv)), t["question"])
    ans = call(t, "kvonly", "answer", q, 400, system=ANSWER_SYSTEM)
    return {"answer": ans, "calls": 1}


def run_watch(t, ext, budget=300, unit="watch", matcher=None):
    matcher = matcher or value_matches
    memory, rounds = "", []
    for i, s in enumerate(t["sessions"]):
        notes, _ = rewrite(t, unit, memory, s, budget, i)
        store = ext["snapshots"][i]
        if not store:
            memory = notes
            rounds.append({"keys": 0, "ok": 0, "missing": 0, "differs": 0, "patched": []})
            continue
        keys = list(store)
        out = call(t, unit, f"check{i}", CHECK.format(notes=notes, keys="\n".join(
                   f"K{n + 1}: {k}" for n, k in enumerate(keys))),
                   3000, json_mode=True)
        j = parse_json(out) or {}
        patched, miss, diff, restated = [], 0, 0, {}
        for n, k in enumerate(keys):
            r = j.get(f"K{n + 1}")
            if matcher(store[k], r):
                continue
            if r is None or "NOT_IN_NOTES" in str(r).upper():
                miss += 1
            else:
                diff += 1
                restated[k] = r
            patched.append(k)
        patch = "".join(f"\n[current] {k}: {store[k]}" for k in patched)
        memory = notes + (("\n\nREMINDERS (current values):" + patch) if patched else "")
        rounds.append({"keys": len(keys), "ok": len(keys) - len(patched), "missing": miss,
                       "differs": diff, "patched": patched, "restated": restated,
                       "parse_ok": j != {}})
    ans = call(t, unit, "answer", question_prompt(memory, t["question"]), 400, system=ANSWER_SYSTEM)
    return {"answer": ans, "memory": memory, "memory_chars": len(memory), "rounds": rounds,
            "calls": 2 * len(t["sessions"]) + 1}

# ------------------------------------------------------------------ judging

ABST = "information provided is not enough"


def run_judge(t, arms):
    out = {}
    if t["set"] == "lme":
        sess = "\n\n".join(f"[Session {i + 1}]\n{s}" for i, s in enumerate(t["sessions"]))
        abst = ABST in t["answer"].lower()
        lab = None if abst else parse_json(call(
            t, "judge", "label", LABEL_STALE.format(sessions=sess, q=t["question"], gold=t["answer"]),
            300, json_mode=True))
        stale = [str(x) for x in (lab or {}).get("wrong_version", [])] if lab else []
        out["stale_label"] = stale
        for a, r in arms.items():
            tmpl = JUDGE_ABST if abst else JUDGE
            yn = call(t, "judge", f"yn_{a}", tmpl.format(q=t["question"], gold=t["answer"], ans=r["answer"]), 200)
            v4 = None
            if stale:
                v4 = call(t, "judge", f"j4_{a}", JUDGE4.format(q=t["question"], gold=t["answer"],
                          stale="; ".join(stale), ans=r["answer"]), 200).lower().split()[0].strip(".'\"")
            out[a] = {"yes": yn.lower().startswith("y"), "raw": yn, "v4": v4}
    else:  # synthetic: judge only to validate the yes/no judge against the exact grader
        for a, r in arms.items():
            yn = call(t, "judge", f"yn_{a}", JUDGE.format(q=t["question"], gold=t["answer"], ans=r["answer"]), 200)
            out[a] = {"yes": yn.lower().startswith("y"), "raw": yn}
    return out

# ------------------------------------------------------------------ driver

def load_tasks(sets, n_synth):
    tasks = []
    if "lme" in sets:
        for x in load_longmemeval(LME_PATH):
            x["answer"] = str(x["answer"])  # two golds are ints (120, 1300)
            tasks.append({"set": "lme", "qid": x["info"]["qid"], "question": x["question"],
                          "answer": x["answer"], "sessions": x["sessions"], "stale": []})
    cfgs = {"synth_std": {}, "synth_hard": {"n_tracked": 8, "chain_len": 3, "n_distractors": 10}}
    for name, kw in cfgs.items():
        if name in sets:
            for x in synthetic_tasks(n_synth, start_seed=1000 if kw else 0, **kw):
                tasks.append({"set": name, "qid": x["info"]["qid"], "question": x["question"],
                              "answer": x["answer"], "sessions": x["sessions"],
                              "stale": x["info"]["stale_values"]})
    return tasks


_print = threading.Lock()


def run_task(t):
    full = cached(t, "full", lambda: run_full(t))
    n300 = cached(t, "notes300", lambda: run_notes(t, 300))
    n1200 = cached(t, "notes1200", lambda: run_notes(t, 1200))
    ext = cached(t, "extract", lambda: run_extract(t))
    pin = cached(t, "pin", lambda: run_pin(t, n300, ext))
    watch = cached(t, "watch", lambda: run_watch(t, ext))
    kvo = cached(t, "kvonly", lambda: run_kv_only(t, ext))
    arms = {"full": full, "notes300": n300, "notes1200": n1200, "pin": pin, "watch": watch, "kvonly": kvo}
    jud = cached(t, "judge", lambda: run_judge(t, arms))
    with _print:
        print(t["set"], t["qid"], {a: jud[a]["yes"] for a in arms}, flush=True)
    return t["qid"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["lme", "synth_std", "synth_hard"])
    ap.add_argument("--n-synth", type=int, default=60)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--model", default=DEFAULT_MODEL, help="backbone for every method call")
    ap.add_argument("--judge-model", default=DEFAULT_MODEL, help="grader model (keep fixed across backbones)")
    a = ap.parse_args()
    if ":free" in a.model or ":free" in a.judge_model:
        sys.exit("':free' models are reserved for the coordinator")
    global UNITS
    CFG.update(model=a.model, judge_model=a.judge_model)
    if a.model != DEFAULT_MODEL:  # second backbone: separate result tree and usage tags
        safe = re.sub(r"[^\w]+", "_", a.model)
        CFG["suffix"] = f"@{safe}"
        UNITS = HERE / "results" / f"units_{safe}"
    tasks = load_tasks(a.sets, a.n_synth)
    if a.limit:
        by = {}
        for t in tasks:
            by.setdefault(t["set"], []).append(t)
        tasks = [t for v in by.values() for t in v[:a.limit]]
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "tasks_meta.json").write_text(json.dumps(
        [{k: t[k] for k in ("set", "qid", "question", "answer", "stale")} | {"n_sessions": len(t["sessions"]),
          "chars": sum(map(len, t["sessions"]))} for t in load_tasks(["lme", "synth_std", "synth_hard"], a.n_synth)], indent=1))
    with ThreadPoolExecutor(min(a.workers, 12)) as ex:
        for f in [ex.submit(run_task, t) for t in tasks]:
            try:
                f.result()
            except Exception as e:  # keep going; rerun resumes
                print("FAILED", repr(e)[:300], flush=True)


if __name__ == "__main__":
    main()
