"""E27: the combined recipe, and every other compaction/memory method, on LongMemEval and Supersede.

Builds on E14 (../e14_versioned_pin). Same tasks, NOTES protocol, extraction prompts, and judge.
Run with the Supersede venv:

    PY=/private/tmp/supersede-venv/bin/python
    $PY e27.py --stage seed                    # copy E14's raw units (identical calls) into results/units
    $PY e27.py --stage run --arms confirm      # recipe, minimal, ablations (reps 1 and 2)
    $PY e27.py --stage tmbudget                # token-matched budget from the recipe's rep-1 memory size
    $PY e27.py --stage run --arms tm           # token-matched notes and truncation at that budget
    $PY e27.py --stage run --arms extra        # every other method
    $PY e27.py --stage judge                   # LongMemEval judging (synthetic is graded exactly in analyze.py)

Model calls are tagged "e27|rep<r>|<set>|<qid>|<unit>|<kind>" in the shared usage.jsonl.
"""
import argparse, json, re, shutil, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
E14 = HERE.parent / "e14_versioned_pin" / "results" / "units"
sys.path.insert(0, str(HERE.parent / "shared"))
sys.path.insert(0, "/private/tmp/supersede/src")
from orclient import chat                                                          # noqa: E402
from supersede.rollout import MEMORY_SYSTEM, ANSWER_SYSTEM, memory_prompt, question_prompt  # noqa: E402
from supersede.dataset import synthetic_tasks                                      # noqa: E402
import e27lib as L                                                                 # noqa: E402

LME_PATH = "/private/tmp/supersede/data/longmemeval_oracle.json"
DEFAULT_MODEL = "stealth/space-bunny-alpha"
CFG = {"model": DEFAULT_MODEL, "judge_model": DEFAULT_MODEL, "suffix": "", "units": HERE / "results" / "units",
       "tm": {}}
SYNTH_CFGS = {"synth_std": ({}, 0), "synth_hard": ({"n_tracked": 8, "chain_len": 3, "n_distractors": 10}, 1000)}
REUSED = ["full", "notes300", "notes1200", "pin", "vpin", "vpin_canon"]   # answers copied from E14
CONFIRM = ["minimal", "recipe", "r_nopin", "r_novblock"]
TM_ARMS = ["tm", "fifo_tm", "headtail_tm"]
EXTRA = ["fifo1200", "headtail1200", "mask", "resum", "struct", "carry", "prov300", "anchor", "watch",
         "watch_strict", "watch_self", "roundtrip", "repair", "ledger", "registry"]
NOT_SYNTH = {"mask", "tm", "fifo_tm", "headtail_tm"}   # identical to full, or budget undefined (README)

# ------------------------------------------------------------------ call plumbing

_locks, _lk = {}, threading.Lock()


def tg(t, rep, unit, kind):
    return f"e27|rep{rep}|{t['set']}{CFG['suffix']}|{t['qid']}|{unit}|{kind}"


def call(t, rep, unit, kind, content, max_tokens, system=None, json_mode=False, judge=False):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
    return chat(msgs, max_tokens=max_tokens, temperature=0, model=CFG["judge_model"] if judge else CFG["model"],
                tag=tg(t, rep, unit, kind), json_mode=json_mode).strip()


def unit_path(t, rep, unit):
    return CFG["units"] / f"rep{rep}" / t["set"] / t["qid"] / f"{unit}.json"


def cached(t, rep, unit, fn):
    p = unit_path(t, rep, unit)
    with _lk:
        lock = _locks.setdefault(str(p), threading.Lock())
    with lock:
        if p.exists():
            return json.loads(p.read_text())
        out = fn()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1))
        return out

# ------------------------------------------------------------------ memory builders


def rewrite(t, rep, unit, notes, session, budget, i, system=None):
    out = call(t, rep, unit, f"notes{i}", memory_prompt(notes, session, budget), max(800, budget * 2),
               system=(system or MEMORY_SYSTEM).format(budget=budget))
    return out[:budget], len(out)


def run_notes(t, rep, budget, unit, system=None, labeled=False):
    notes, traj, raw = "", [], []
    for i, s in enumerate(t["sessions"]):
        sess = L.labeled_session(t["turns"][i], i + 1) if labeled else s
        notes, n = rewrite(t, rep, unit, notes, sess, budget, i, system)
        traj.append(notes); raw.append(n)
    return {"notes": notes, "trajectory": traj, "raw_lens": raw, "budget": budget,
            "truncated": sum(r > budget for r in raw), "calls": len(t["sessions"])}


def run_extract(t, rep):  # E4 extractor (only used when no E14 unit exists, e.g. a second backbone)
    store, per = {}, []
    for i, s in enumerate(t["sessions"]):
        j = L.parse_json(call(t, rep, "extract", f"ext{i}", L.EXTRACT.format(store=L.render_kv(store), session=s),
                              3000, json_mode=True)) or {}
        facts = [(str(f["key"]).strip().lower(), str(f.get("value", "")).strip())
                 for f in j.get("facts", []) if isinstance(f, dict) and f.get("key")]
        store.update(dict(facts)); per.append(facts)
    return {"facts": per, "calls": len(t["sessions"])}


def run_extract_canon(t, rep):  # E14 canonical extractor (fallback, as above)
    hist, per = {}, []
    for i, s in enumerate(t["sessions"]):
        keys = "\n".join(f"- {k}: {h[-1]['v']}" for k, h in hist.items()) or "(none yet)"
        j = L.parse_json(call(t, rep, "extract_canon", f"ext{i}", L.EXTRACT_CANON.format(keys=keys, session=s),
                              3000, json_mode=True)) or {}
        per.append([(L.canon_key(f["key"]), str(f.get("value", "")).strip())
                    for f in j.get("facts", []) if isinstance(f, dict) and f.get("key")])
        hist = L.build_versioned(per)
    return {"facts": per, "calls": len(t["sessions"])}


def run_keeper(t, rep):
    sel, raw = [], []
    for i, turns in enumerate(t["turns"]):
        n_user = len(L.user_turns(turns))
        out = call(t, rep, "keeper", f"keep{i}", L.KEEPER.format(session=L.labeled_session(turns, None, 300)),
                   600, json_mode=True)
        j = L.parse_json(out) or {}
        nums = [str(x).strip().lstrip("Uu") for x in (j.get("turns") or [])]
        sel.append(sorted({int(x) for x in nums if x.isdigit() and 1 <= int(x) <= n_user})); raw.append(out)
    return {"selected": sel, "raw": raw, "n_user": [len(L.user_turns(x)) for x in t["turns"]],
            "calls": len(t["turns"])}


def run_resum(t, rep, budget=300):
    notes = ""
    for i in range(len(t["sessions"])):
        src = "\n\n".join(f"[Session {k + 1}]\n{s}" for k, s in enumerate(t["sessions"][:i + 1]))
        out = call(t, rep, "resum", f"notes{i}", f"ALL SESSIONS SO FAR:\n{src}\n\nWrite your complete notes "
                   f"(max {budget} chars).", max(800, budget * 2), system=L.RESUM_SYSTEM.format(budget=budget))
        notes = out[:budget]
    return {"notes": notes, "calls": len(t["sessions"])}


def run_watch(t, rep, unit, ext, mode):
    """E4 watchpoint over its own 300-char notes trajectory. mode: loose (E4), strict (E4 follow-up), self."""
    snaps = L.snapshots(ext["facts"])
    memory, rounds = "", []
    for i, s in enumerate(t["sessions"]):
        notes, _ = rewrite(t, rep, unit, memory, s, 300, i)
        store = snaps[i]
        if not store:
            memory = notes; rounds.append({"keys": 0, "patched": []}); continue
        keys = list(store)
        if mode == "self":
            j = L.parse_json(call(t, rep, unit, f"check{i}", L.SELFCHECK.format(notes=notes, facts="\n".join(
                f"K{n + 1}: {k}: {store[k]}" for n, k in enumerate(keys))), 3000, json_mode=True)) or {}
            patched = [k for n, k in enumerate(keys) if not str(j.get(f"K{n + 1}", "NO")).upper().startswith("Y")]
        else:
            m = L.value_matches if mode == "loose" else L.value_matches_strict
            j = L.parse_json(call(t, rep, unit, f"check{i}", L.CHECK.format(notes=notes, keys="\n".join(
                f"K{n + 1}: {k}" for n, k in enumerate(keys))), 3000, json_mode=True)) or {}
            patched = [k for n, k in enumerate(keys) if not m(store[k], j.get(f"K{n + 1}"))]
        patch = "".join(f"\n[current] {k}: {store[k]}" for k in patched)
        memory = notes + (("\n\nREMINDERS (current values):" + patch) if patched else "")
        rounds.append({"keys": len(keys), "patched": patched, "parse_ok": j != {}})
    return {"memory": memory, "rounds": rounds, "calls": 2 * len(t["sessions"])}


def run_roundtrip(t, rep):
    memory, rounds = "", []
    for i, s in enumerate(t["sessions"]):
        notes, _ = rewrite(t, rep, "roundtrip", memory, s, 300, i)
        r = call(t, rep, "roundtrip", f"rtR{i}", L.RT_ANSWER.format(
            ctx=f"[Your notes before this session]\n{memory or '(empty)'}\n\n[The latest session]\n{s}", q=L.RT_Q), 600)
        a = call(t, rep, "roundtrip", f"rtS{i}", L.RT_ANSWER.format(ctx=f"[Your notes]\n{notes}", q=L.RT_Q), 600)
        j = L.parse_json(call(t, rep, "roundtrip", f"rtC{i}", L.RT_COMPARE.format(q=L.RT_Q, r=r, s=a), 800,
                              json_mode=True)) or {}
        d = [str(x) for x in j.get("discrepancies", []) if str(x).strip()][:8]
        memory = notes + (("\n\nREMINDERS (from a consistency check against the session):\n" +
                           "\n".join(f"- {x}" for x in d)) if d else "")
        rounds.append({"n_disc": len(d), "disc": d})
    return {"memory": memory, "rounds": rounds, "calls": 4 * len(t["sessions"])}


def run_repair(t, rep, notes, k=2):
    passes = []
    for i in range(k):
        ctx = f"NOTES (your only memory):\n{notes}" + "".join(
            f"\n\n[Your own fact check, pass {n}]\n{p}" for n, p in enumerate(passes, 1))
        passes.append(call(t, rep, "repair", f"pass{i + 1}", f"{ctx}\n\n{L.REPAIR}", 500))
    return {"passes": passes, "calls": k}


def run_ledger(t, rep):
    led, errs, n = json.loads(json.dumps(L.EMPTY_LEDGER)), 0, 0
    for si, turns in enumerate(t["turns"], 1):
        for k, msg in enumerate(L.user_turns(turns), 1):
            out = call(t, rep, "ledger", f"S{si}U{k}", L.LEDGER_PROMPT.format(
                ledger=json.dumps(led, indent=1), turn=f"S{si}.U{k}", message=msg), 4000, json_mode=True)
            n += 1
            j = L.parse_json(out)
            if isinstance(j, dict) and "facts" in j:
                for key, v in L.EMPTY_LEDGER.items():
                    j.setdefault(key, type(v)())
                led = j
            else:
                errs += 1
    return {"ledger": led, "errors": errs, "calls": n}

# ------------------------------------------------------------------ arms


def get(t, rep, unit):
    """Shared units (E14 copies when present, else built here)."""
    fns = {"notes300": lambda: run_notes(t, rep, 300, "notes300"),
           "notes1200": lambda: run_notes(t, rep, 1200, "notes1200"),
           "extract": lambda: run_extract(t, rep), "extract_canon": lambda: run_extract_canon(t, rep),
           "pnotes": lambda: run_notes(t, rep, 1200, "pnotes", L.PROV_SYSTEM, labeled=True),
           "keeper": lambda: run_keeper(t, rep)}
    return cached(t, rep, unit, fns[unit])


def memory(t, rep, arm):
    n = len(t["sessions"])
    blocks = "\n\n".join(f"[Session {i + 1}]\n{s}" for i, s in enumerate(t["sessions"]))
    vblock = lambda u: L.VPIN_BLOCK.format(n=n, kv=L.render_versioned(L.build_versioned(get(t, rep, u)["facts"]), n))
    tm = CFG["tm"].get(t["set"])
    if arm == "notes300" or arm == "notes1200":
        return get(t, rep, arm)["notes"]
    if arm == "pin":
        return get(t, rep, "notes300")["notes"] + L.PIN_BLOCK.format(kv=L.render_kv(L.newest(L.build_versioned(get(t, rep, "extract")["facts"]))))
    if arm == "vpin":
        return get(t, rep, "notes300")["notes"] + vblock("extract")
    if arm == "vpin_canon":
        return get(t, rep, "notes300")["notes"] + vblock("extract_canon")
    if arm == "minimal":
        return get(t, rep, "notes300")["notes"] + L.pin_block(t, None, L.PIN_ALL_HDR)
    if arm in ("recipe", "r_nopin", "r_novblock"):
        m = get(t, rep, "pnotes")["notes"]
        if arm != "r_novblock":
            m += vblock("extract_canon")
        if arm != "r_nopin":
            m += L.pin_block(t, [set(x) for x in get(t, rep, "keeper")["selected"]], L.PIN_SEL_HDR)
        return m
    if arm == "tm":
        return cached(t, rep, f"notes_tm{tm}", lambda: run_notes(t, rep, tm, f"notes_tm{tm}"))["notes"]
    if arm.startswith("fifo") or arm.startswith("headtail"):
        b = tm if arm.endswith("_tm") else 1200
        if arm.startswith("fifo"):
            return blocks[-b:]
        return blocks[:b // 2] + "\n[...]\n" + blocks[-(b - b // 2):] if len(blocks) > b else blocks
    if arm == "mask":
        return L.pin_block(t, None, L.MASK_HDR).lstrip()
    if arm == "resum":
        return cached(t, rep, "resum", lambda: run_resum(t, rep))["notes"]
    if arm in L.VARIANT_SYSTEMS:
        return cached(t, rep, f"notes_{arm}", lambda: run_notes(t, rep, 300, f"notes_{arm}", L.VARIANT_SYSTEMS[arm]))["notes"]
    if arm in ("watch", "watch_strict", "watch_self"):
        mode = {"watch": "loose", "watch_strict": "strict", "watch_self": "self"}[arm]
        return cached(t, rep, arm, lambda: run_watch(t, rep, arm, get(t, rep, "extract"), mode))["memory"]
    if arm == "roundtrip":
        return cached(t, rep, "roundtrip", lambda: run_roundtrip(t, rep))["memory"]
    if arm == "repair":
        notes = get(t, rep, "notes300")["notes"]
        ps = cached(t, rep, "repair", lambda: run_repair(t, rep, notes))["passes"]
        return f"{notes}" + "".join(f"\n\n[Your own fact check, pass {i}]\n{p}" for i, p in enumerate(ps, 1))
    if arm == "ledger":
        return get(t, rep, "notes300")["notes"] + L.render_ledger(cached(t, rep, "ledger", lambda: run_ledger(t, rep))["ledger"])
    if arm == "registry":
        return get(t, rep, "notes300")["notes"] + L.render_registry(L.build_versioned(get(t, rep, "extract")["facts"]))
    raise ValueError(arm)


def questions(t):
    return [("cur", t["question"])] + ([("hist", t["hist_question"])] if t.get("hist_question") else [])


def run_arm(t, rep, arm):
    if t["set"] != "lme" and arm in NOT_SYNTH:
        return
    blocks = "\n\n".join(f"[Session {i + 1}]\n{s}" for i, s in enumerate(t["sessions"]))
    for qk, q in questions(t):
        if arm == "full":
            cached(t, rep, f"ans_full_{qk}", lambda: {"answer": call(t, rep, "ans_full", qk, f"{blocks}\n\nQuestion: {q}",
                                                                      400, system=L.ANSWER_FULL), "memory_chars": len(blocks)})
            continue
        def ans():
            m = memory(t, rep, arm)
            return {"answer": call(t, rep, f"ans_{arm}", qk, question_prompt(m, q), 400, system=ANSWER_SYSTEM),
                    "memory_chars": len(m)}
        cached(t, rep, f"ans_{arm}_{qk}", ans)

# ------------------------------------------------------------------ judging

ABST = "information provided is not enough"


def run_judge(t, rep, arms):
    p = unit_path(t, rep, "judge")
    with _lk:
        lock = _locks.setdefault(str(p), threading.Lock())
    with lock:
        prev = json.loads(p.read_text()) if p.exists() else {}
    if "stale_label" not in prev:
        e4j = HERE.parent / "e04_supersede" / "results" / "units" / "lme" / t["qid"] / "judge.json"
        prev["stale_label"] = json.loads(e4j.read_text()).get("stale_label", []) if e4j.exists() else []
    stale = prev["stale_label"]
    abst = ABST in t["answer"].lower()
    new = {}
    for a in arms:
        ap = unit_path(t, rep, f"ans_{a}_cur")
        if a in prev or not ap.exists():
            continue
        ans = json.loads(ap.read_text())["answer"]
        yn = call(t, rep, "judge", f"yn_{a}", (L.JUDGE_ABST if abst else L.JUDGE).format(
            q=t["question"], gold=t["answer"], ans=ans), 200, judge=True)
        v4 = None
        if stale:
            v4 = call(t, rep, "judge", f"j4_{a}", L.JUDGE4.format(q=t["question"], gold=t["answer"],
                      stale="; ".join(stale), ans=ans), 200, judge=True).lower().split()[0].strip(".'\"")
        new[a] = {"yes": yn.lower().startswith("y"), "raw": yn, "v4": v4, "answer": ans}
    if new:
        with lock:
            cur = json.loads(p.read_text()) if p.exists() else {"stale_label": stale}
            cur.update(new)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(cur, indent=1))

# ------------------------------------------------------------------ tasks, seeding, driver


def hist_question(q):
    m = re.search(r"'(\w+) (.+?) ___'", q)
    return (f"What was the previous value for: '{m.group(1)} {m.group(2)} ___', i.e. the value it had "
            f"just before it changed to its current value? Reply with only that single previous value, "
            f"nothing else.")


def load_tasks(sets, n_synth):
    from supersede.dataset import render_session
    tasks = []
    if "lme" in sets:
        for x in json.loads(Path(LME_PATH).read_text()):
            if x.get("question_type") != "knowledge-update":
                continue
            tasks.append({"set": "lme", "qid": x["question_id"], "question": x["question"], "answer": str(x["answer"]),
                          "sessions": [render_session(s) for s in x["haystack_sessions"]],
                          "turns": [[(u["role"], u["content"]) for u in s] for s in x["haystack_sessions"]]})
    for name, (kw, start) in SYNTH_CFGS.items():
        if name in sets:
            for x in synthetic_tasks(n_synth, start_seed=start, **kw):
                st = x["info"]["stale_values"]
                tasks.append({"set": name, "qid": x["info"]["qid"], "question": x["question"], "answer": x["answer"],
                              "sessions": x["sessions"], "turns": [[("user", s)] for s in x["sessions"]],
                              "stale": st, "hist_question": hist_question(x["question"]), "hist_answer": st[-1],
                              "hist_wrong": [x["answer"]] + st[:-1]})
    return tasks


def seed(tasks, reps):
    """Copy E14's raw units for identical calls (same model, prompts, temperature, inputs)."""
    files = ["notes300", "notes1200", "extract", "extract_canon"] + [f"ans_{a}_{q}" for a in REUSED for q in ("cur", "hist")]
    n = 0
    for rep in reps:
        for t in tasks:
            src = E14 / f"rep{rep}" / t["set"] / t["qid"]
            for f in files:
                s, d = src / f"{f}.json", unit_path(t, rep, f)
                if s.exists() and not d.exists():
                    d.parent.mkdir(parents=True, exist_ok=True); shutil.copy(s, d); n += 1
            sj, dj = src / "judge.json", unit_path(t, rep, "judge")
            if sj.exists() and not dj.exists():
                j = json.loads(sj.read_text())
                dj.write_text(json.dumps({k: v for k, v in j.items() if k == "stale_label" or k in REUSED}, indent=1)); n += 1
    print(f"seeded {n} files from E14")


_print = threading.Lock()


def pool(jobs, workers):
    with ThreadPoolExecutor(min(workers, 25)) as ex:
        futs = [ex.submit(*j) for j in jobs]
        done = 0
        for f in futs:
            try:
                f.result(); done += 1
                if done % 50 == 0:
                    with _print:
                        print(f"{done}/{len(futs)} done", flush=True)
            except Exception as e:
                with _print:
                    print("FAILED", repr(e)[:300], flush=True)
        print(f"finished {done}/{len(futs)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["seed", "run", "tmbudget", "judge"], default="run")
    ap.add_argument("--arms", nargs="+", default=["confirm"], help="confirm | tm | extra | reused | <arm names>")
    ap.add_argument("--sets", nargs="+", default=["lme", "synth_std", "synth_hard"])
    ap.add_argument("--reps", nargs="+", type=int, default=[1, 2])
    ap.add_argument("--n-synth", type=int, default=30)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=25)
    ap.add_argument("--units", default="", help="override the units directory (smoke tests)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--judge-model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    if ":free" in a.model or ":free" in a.judge_model:
        sys.exit("':free' models are not allowed")
    CFG.update(model=a.model, judge_model=a.judge_model)
    if a.model != DEFAULT_MODEL:   # second backbone: separate tree and tags, no E14 reuse
        safe = re.sub(r"[^\w]+", "_", a.model)
        CFG.update(suffix=f"@{safe}", units=HERE / "results" / f"units_{safe}")
    if a.units:
        CFG["units"] = Path(a.units)
    tmf = CFG["units"].parent / ("tm_budget.json" if not CFG["suffix"] else f"tm_budget{CFG['suffix']}.json")
    if tmf.exists():
        CFG["tm"] = json.loads(tmf.read_text())["budget"]
    tasks = load_tasks(a.sets, a.n_synth)
    if a.limit:
        by = {}
        for t in tasks:
            by.setdefault(t["set"], []).append(t)
        tasks = [t for v in by.values() for t in v[:a.limit]]
    groups = {"confirm": CONFIRM, "tm": TM_ARMS, "extra": EXTRA, "reused": REUSED}
    arms = [x for g in a.arms for x in groups.get(g, [g])]
    if a.stage == "seed":
        if CFG["suffix"] == "" and not a.units:
            seed(tasks, a.reps)
    elif a.stage == "run":
        if any(x in TM_ARMS for x in arms) and not CFG["tm"]:
            sys.exit("run --stage tmbudget first")
        pool([(run_arm, t, r, arm) for r in a.reps for arm in arms for t in tasks], a.workers)
    elif a.stage == "tmbudget":
        sz = [json.loads(unit_path(t, 1, "ans_recipe_cur").read_text())["memory_chars"]
              for t in tasks if t["set"] == "lme" and unit_path(t, 1, "ans_recipe_cur").exists()]
        b = int(round(sum(sz) / len(sz), -2))
        tmf.write_text(json.dumps({"budget": {"lme": b}, "how": f"mean recipe memory chars, LongMemEval rep 1, "
                                   f"n={len(sz)}, rounded to 100", "mean": sum(sz) / len(sz)}, indent=1))
        print("tm budget", b)
    elif a.stage == "judge":
        pool([(run_judge, t, r, arms) for r in a.reps for t in tasks if t["set"] == "lme"], a.workers)


if __name__ == "__main__":
    main()
