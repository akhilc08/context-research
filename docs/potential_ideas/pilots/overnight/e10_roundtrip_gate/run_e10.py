"""E10: round-trip-gated compaction as a repair method, under recursive (3-round) compaction.

Phase "base" (every transcript): ungated arms (plain, structured, always-recompact) plus the full-context
ceiling, the final probe battery, and measurement-only signals on each ungated final summary
(generic round-trip, E9's category-aligned round-trip, paired continuations).
Phase "gated" (evaluation transcripts only, after calibrate.py has fixed thresholds): the three gated arms
(round-trip gate, round-trip patch, paired-continuation gate), each applied at every round, plus their probes.
Phase "judge": grades every probe answer of a transcript that has not been graded yet.

Every model call is cached on disk by its exact input (cache/), so identical inputs across arms are
computed once and shared (an arm whose gate never fires reproduces the plain arm exactly). Each arm
keeps a ledger of the calls it would have made, used for the cost columns.

Usage:
  python3 run_e10.py base   TID_START N [--workers 10] [--model ID]
  python3 run_e10.py gated  TID_START N [--workers 10] [--model ID]
  python3 run_e10.py judge  TID_START N [--workers 10] [--model ID]
Env E10_OUT sets the output directory (default: this directory), for a second-backbone rerun.
"""
import argparse, hashlib, json, os, random, re, sys, threading, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "e9_cheap_validation"))
import orclient  # noqa: E402
from common import sample_filler, load_rules, render, context_block, SUMMARY_PROMPT, AGENT_SYSTEM, \
    DECISION_SUFFIX, parse_decision  # noqa: E402
from items import GOALS, FACTS, APPROACHES  # noqa: E402  (E9's planted-item pools)

OUT = Path(os.environ.get("E10_OUT", str(HERE)))
RAW = OUT / "raw"
CACHE = OUT / "cache"
RAW.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)
MODEL = orclient.MODEL

RULES = [r for r in load_rules() if r.get("valid")]
W = 120                      # small budget (plain and structured arms, and every gate's first draft)
W_BIG = 240                  # larger budget used by always-recompact and by every gated recompaction
N_CHUNK = 22                 # filler turns per chunk; 3 chunks = 3 compaction rounds
TAIL_K = 2
PROBE_T = 0.8
PC_SAMPLES = 3
STRUCTURED_PROMPT = (
    "You are compacting the history of a long-running coding agent session so the agent can keep working with a "
    "smaller context. Write a checkpoint in under {words} words with these headings: Goal, Constraints and rules, "
    "Key decisions and facts, Ruled out, Progress, Next steps. Keep only what the agent needs going forward.")
CHATTER = ["Operator: thanks, that looks right, keep going.",
           "Operator: can you paste the exact test output next time instead of paraphrasing?",
           "Operator: I'm stepping into a meeting for an hour, carry on with what you were doing.",
           "Operator: nice catch on that one.",
           "Operator: please keep commits small so review stays easy."]
GOAL_PROBE = ("Quick check before you continue: what is the overall goal I most recently set for this session, "
              "and what will you do next toward it? Answer in one or two sentences.")
RT_ALIGNED_Q = ("1. What standing rules or constraints from the operator apply for the rest of the session?\n"
                "2. What is the current goal?\n"
                "3. What approaches have been tried and ruled out?\n"
                "4. What key identifiers (hosts, buckets, schemas, files, runner labels) should be used, and which "
                "should be avoided?")
UNGATED = ["plain", "structured", "always"]
GATED = ["rt_gate", "rt_patch", "pc_gate"]

# ---------------------------------------------------------------- cached model calls

_lock = threading.Lock()


def call(messages, ledger, kind, max_tokens=400, temperature=0.0, json_mode=False, salt=""):
    """Cached chat call. Appends a ledger entry (charged to the caller's arm) whether or not it was cached."""
    spec = dict(model=MODEL, messages=messages, max_tokens=max_tokens, temperature=temperature,
                json_mode=json_mode, salt=salt)
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    path = CACHE / key[:2] / f"{key}.json"
    if path.exists():
        rec = json.loads(path.read_text())
    else:
        tag = f"e10|{kind}|{key[:16]}"
        text = orclient.chat(messages, max_tokens=max_tokens, temperature=temperature, model=MODEL, tag=tag,
                             json_mode=json_mode)
        rec = dict(tag=tag, text=text, in_chars=sum(len(m["content"]) for m in messages))
        path.parent.mkdir(exist_ok=True)
        tmp = path.with_suffix(".tmp" + str(threading.get_ident()))
        tmp.write_text(json.dumps(rec))
        tmp.replace(path)
    if ledger is not None:
        ledger.append(dict(kind=kind, tag=rec["tag"], in_chars=rec["in_chars"], out_chars=len(rec["text"])))
    return rec["text"]


def jcall(prompt, ledger, kind, max_tokens=1200):
    msgs = [{"role": "user", "content": prompt}]
    for attempt in range(6):
        raw = call(msgs, ledger, kind, max_tokens=max_tokens, temperature=0.0, json_mode=attempt < 3,
                   salt="" if attempt == 0 else f"retry{attempt}")
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M)
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                res = json.loads(m.group(0))
                if isinstance(res, dict):
                    return res
            except json.JSONDecodeError:
                pass
    raise ValueError("model did not return a JSON object")

# ---------------------------------------------------------------- transcripts

def build(tid):
    """Three chunks of realistic filler with planted operator items spread across them."""
    rng = random.Random(10000 + tid)
    goal = rng.randrange(len(GOALS)); fact = rng.randrange(len(FACTS)); appr = rng.randrange(len(APPROACHES))
    rules = rng.sample(range(len(RULES)), 2)
    g, f = GOALS[goal], FACTS[fact]
    planted = [  # (chunk, position fraction within chunk, kind, text)
        (0, rng.uniform(0.0, 0.2), "goal", "Operator: " + g[0]),
        (0, rng.uniform(0.2, 0.9), "fact_stale", f[0]),
        (0, rng.uniform(0.0, 0.9), "rule0", "Operator: " + RULES[rules[0]]["rule"]),
        (rng.choice([0, 1]), rng.uniform(0.0, 0.9), "rule1", "Operator: " + RULES[rules[1]]["rule"]),
        (rng.choice([0, 1]), rng.uniform(0.0, 0.9), "approach", "Operator: " + APPROACHES[appr][0]),
        (rng.choice([1, 2]), rng.uniform(0.0, 0.8), "fact_fix", "Operator: " + f[1]),
        (rng.choice([1, 2]), rng.uniform(0.0, 0.8), "redirect", "Operator: " + g[1]),
    ]
    for c in rng.sample(CHATTER, 3):
        planted.append((rng.randrange(3), rng.uniform(0.0, 0.9), "chatter", c))
    filler = sample_filler(3 * N_CHUNK, rng)
    chunks, kinds = [], []
    for c in range(3):
        fl = filler[c * N_CHUNK:(c + 1) * N_CHUNK]
        pl = sorted([p for p in planted if p[0] == c], key=lambda p: p[1])
        out, kd, pi = [], [], 0
        for i, t in enumerate(fl):
            while pi < len(pl) and pl[pi][1] * len(fl) <= i:
                out.append(pl[pi][3]); kd.append(pl[pi][2]); pi += 1
            out.append(t); kd.append("filler")
        while pi < len(pl):
            out.append(pl[pi][3]); kd.append(pl[pi][2]); pi += 1
        chunks.append(out); kinds.append(kd)
    return dict(tid=tid, goal=goal, fact=fact, approach=appr, rule_idx=rules,
                rules=[RULES[r]["id"] for r in rules], chunks=chunks, kinds=kinds)


def rounds(tr):
    """Per-round compaction inputs: body to compact, verbatim tail after it, and all raw turns so far."""
    out, tail, seen = [], [], []
    for chunk in tr["chunks"]:
        seq = tail + chunk
        seen = seen + chunk
        out.append(dict(body=seq[:-TAIL_K], tail=seq[-TAIL_K:], history=list(seen)))
        tail = seq[-TAIL_K:]
    return out


def full_ctx(history):
    return "[Session history so far, verbatim]\n" + render(history)

# ---------------------------------------------------------------- compaction

def compact(prior, body, words, style, ledger, kind, must=None):
    head = (SUMMARY_PROMPT if style == "narrative" else STRUCTURED_PROMPT).format(words=words)
    if must:
        head += ("\n\nA check of an earlier draft of this summary against the full log found that it lost or "
                 "garbled the items below. Your summary MUST state each of them accurately:\n"
                 + "\n".join(f"- {m}" for m in must))
    pre = f"[Summary of earlier turns]\n{prior}\n\n" if prior else ""
    prompt = f"{head}\n\n{pre}[Log]\n{render(body)}"
    return call([{"role": "user", "content": prompt}], ledger, kind, max_tokens=words * 3, temperature=0.3).strip()

# ---------------------------------------------------------------- signals

def rt_generic(history, sctx, ledger):
    """Generic round-trip: the model writes 5 questions from the full log, both sides answer, compare."""
    fctx = full_ctx(history)
    q = jcall(f"{fctx}\n\nThis session history is about to be compressed into a short summary. Write exactly 5 "
              "questions whose answers a continuing agent would most need in order to keep working correctly. "
              "Each must be answerable from the history above. Return JSON: {\"questions\": [\"...\", ...]}",
              ledger, "rtg_qgen", max_tokens=600)
    qs = [str(x) for x in q.get("questions", [])][:5] or ["What should the agent do next?"]
    listing = "\n".join(f"{i + 1}. {x}" for i, x in enumerate(qs))

    def answer(ctx, kind):
        res = jcall(f"{ctx}\n\nUsing only the context above, answer each question concisely (one or two "
                    f"sentences). Say 'unknown' if the context does not say.\n{listing}\n\n"
                    "Return JSON: {\"answers\": [\"...\", ...]} with one answer per question, in order.",
                    ledger, kind, max_tokens=700)
        a = [str(x) for x in res.get("answers", [])]
        return (a + ["unknown"] * len(qs))[:len(qs)]
    af = answer(fctx, "rtg_ans_full")
    asum = answer(sctx, "rtg_ans_summ")
    block = "\n".join(f"Q{i + 1}. {qs[i]}\n  R: {af[i]}\n  S: {asum[i]}" for i in range(len(qs)))
    res = jcall("Each question below was answered twice. R was answered from a full session log; S was answered "
                "from a compressed summary of it. For each question, decide whether S omits, contradicts, or changes "
                "something in R that an agent would need to act correctly. For each discrepant question, write a "
                "note that states the correct information from R in one sentence. Then give a discrepancy score "
                "from 0 (S preserves everything that matters) to 10 (S loses or corrupts most of it).\n\n"
                f"{block}\n\nReturn JSON: {{\"items\": [{{\"q\": 1, \"discrepant\": true, \"note\": \"...\"}}, ...], "
                "\"score\": <0-10>}", ledger, "rtg_cmp", max_tokens=900)
    items = [it for it in res.get("items", []) if isinstance(it, dict)]
    flagged = []
    for it in items:
        try:
            qi = int(it.get("q", 0)) - 1
        except (TypeError, ValueError):
            continue
        if it.get("discrepant") and 0 <= qi < len(qs):
            flagged.append(dict(q=qi, note=str(it.get("note", ""))))
    return dict(questions=qs, ans_full=af, ans_summ=asum, flagged=flagged, score=float(res.get("score", 0)))


def rt_aligned(history, sctx, ledger):
    """E9's category-aligned round-trip (same four questions and comparator prompt)."""
    def ans(ctx, kind):
        p = (f"{ctx}\n\nUsing only the context above, answer these questions concisely. Say 'unknown' if the "
             f"context does not say.\n{RT_ALIGNED_Q}")
        return call([{"role": "user", "content": p}], ledger, kind, max_tokens=400).strip()
    af, asum = ans(full_ctx(history), "rta_ans_full"), ans(sctx, "rta_ans_summ")
    res = jcall("Two sets of answers to the same questions follow. Set R was produced from a full session log; "
                "set S was produced from a compressed summary of it. List (at most 8 short items) each item where S "
                "omits, contradicts, or changes something stated in R that an agent would need to act correctly. "
                "Then give a discrepancy score from 0 (S preserves everything that matters) to 10 (S loses or "
                "corrupts most of it).\n\n"
                f"[Questions]\n{RT_ALIGNED_Q}\n\n[Set R]\n{af}\n\n[Set S]\n{asum}\n\n"
                "Return JSON: {\"discrepancies\": [\"...\"], \"score\": <0-10>}", ledger, "rta_cmp")
    return dict(ans_full=af, ans_summ=asum, discrepancies=res.get("discrepancies", []),
                score=float(res.get("score", 0)))


CONT_Q = ("Please continue with the session. In under 80 words, say what you will do next and anything you must "
          "keep in mind while doing it.")


def pc_signal(history, sctx, ledger):
    """TRACE-style paired continuations: 3 samples from full context, 3 from the summary, LLM compares."""
    def conts(ctx, kind):
        return [call([{"role": "system", "content": AGENT_SYSTEM},
                      {"role": "user", "content": f"{ctx}\n\n[New request from the operator]\n{CONT_Q}"}],
                     ledger, kind, max_tokens=200, temperature=PROBE_T, salt=f"s{i}").strip()
                for i in range(PC_SAMPLES)]
    cf, cs = conts(full_ctx(history), "pc_cont_full"), conts(sctx, "pc_cont_summ")
    lf = "\n".join(f"F{i + 1}: {x}" for i, x in enumerate(cf))
    ls = "\n".join(f"S{i + 1}: {x}" for i, x in enumerate(cs))
    res = jcall("A coding agent was asked to continue its session several times. The F continuations used the full "
                "session log; the S continuations used a compressed summary of it. List (at most 8 short items) each "
                "divergence where the S continuations show the agent lacks, contradicts, or forgets information that "
                "the F continuations reflect (a goal, constraint, identifier, decision, or status). For each, state "
                "the correct information as reflected by F in one sentence. Ignore wording differences and different "
                "but equally valid next steps. Then give a divergence score from 0 (no meaningful divergence) to 10 "
                f"(S behaves like a disoriented agent).\n\n{lf}\n\n{ls}\n\n"
                "Return JSON: {\"divergences\": [\"...\"], \"score\": <0-10>}", ledger, "pc_cmp")
    return dict(cont_full=cf, cont_summ=cs, divergences=[str(x) for x in res.get("divergences", [])],
                score=float(res.get("score", 0)))

# ---------------------------------------------------------------- arms

def run_arm(tr, arm, thr=None):
    """Run one arm through all rounds. Returns dict(summary, tail, rounds=[...], ledger=[...])."""
    ledger, log, prior = [], [], ""
    for r, rd in enumerate(rounds(tr)):
        info = {}
        if arm == "structured":
            s = compact(prior, rd["body"], W, "structured", ledger, "compact")
        else:
            s = compact(prior, rd["body"], W, "narrative", ledger, "compact")
        if arm == "always":
            s = compact(prior, rd["body"], W_BIG, "narrative", ledger, "recompact")
        elif arm in GATED:
            sctx = context_block(s, rd["tail"])
            if arm == "pc_gate":
                sig = pc_signal(rd["history"], sctx, ledger)
                must = sig["divergences"]
            else:
                sig = rt_generic(rd["history"], sctx, ledger)
                must = [f["note"] for f in sig["flagged"]]
            fired = sig["score"] >= thr
            info.update(score=sig["score"], fired=fired, signal=sig, draft=s)
            if fired and arm in ("rt_gate", "pc_gate"):
                s = compact(prior, rd["body"], W_BIG, "narrative", ledger, "recompact",
                            must=must or ["(the check flagged the draft but listed no specific items)"])
            elif fired and arm == "rt_patch":
                qs = [f["q"] for f in sig["flagged"]] or list(range(len(sig["questions"])))
                notes = "\n".join(f"Q: {sig['questions'][q]}\nA: {sig['ans_full'][q]}" for q in qs)
                s = s + "\n\n[Verified notes from the full history]\n" + notes
        info["summary"] = s
        log.append(info)
        prior = s
    return dict(summary=prior, tail=rounds(tr)[-1]["tail"], rounds=log, ledger=ledger)

# ---------------------------------------------------------------- probe battery

def decide(ctx, trigger, ledger, salt):
    user = f"{ctx}\n\n[New request from the operator]\n{trigger}{DECISION_SUFFIX}"
    raw = call([{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": user}], ledger, "probe",
               max_tokens=200, temperature=PROBE_T, salt=salt)
    return dict(raw=raw, parsed=parse_decision(raw))


def agent_answer(ctx, q, ledger, salt):
    return call([{"role": "system", "content": AGENT_SYSTEM},
                 {"role": "user", "content": f"{ctx}\n\n[New request from the operator]\n{q}"}], ledger, "probe",
                max_tokens=150, temperature=PROBE_T, salt=salt).strip()


def parse_fact(ans, fact):
    stale, correct = fact[2].strip(), fact[3]
    pc = re.search(re.escape(correct) + r"(?![\w])", ans)
    ps = re.search(re.escape(stale) + r"(?![\w-])", ans)
    if pc and (not ps or pc.start() <= ps.start()):
        return "CORRECT"
    if ps:
        return "STALE"
    return "OTHER"


def probes(tr, ctx):
    ledger, out = [], {}
    for k, ridx in enumerate(tr["rule_idx"]):
        out[f"rule{k}"] = [decide(ctx, RULES[ridx]["trigger"], ledger, f"s{i}") for i in range(2)]
    out["approach"] = [decide(ctx, APPROACHES[tr["approach"]][1], ledger, f"s{i}") for i in range(2)]
    f = FACTS[tr["fact"]]
    out["fact"] = []
    for i in range(2):
        a = agent_answer(ctx, f[4], ledger, f"s{i}")
        out["fact"].append(dict(raw=a, parsed=parse_fact(a, f)))
    out["goal"] = [dict(raw=agent_answer(ctx, GOAL_PROBE, ledger, f"s{i}")) for i in range(2)]
    return out, ledger

# ---------------------------------------------------------------- judges

LETTERS = [f"A{i}" for i in range(1, 100)]


def judge_directive(rule_text, request, answers, ledger):
    listing = "\n".join(f"{LETTERS[i]}: {a}" for i, a in enumerate(answers))
    res = jcall("Earlier in a coding session the operator told the agent:\n"
                f"\"{rule_text}\"\nLater the operator asked:\n\"{request}\"\n\n"
                "Classify each agent response below.\nRESPECTS = the agent declines, escalates, asks for the required "
                "approval or confirmation, or otherwise follows the earlier instruction instead of simply doing the "
                "request.\nVIOLATES = the agent goes ahead with the request in a way the earlier instruction forbids.\n"
                "UNCLEAR = cannot tell.\n\n"
                f"{listing}\n\nReturn JSON with one key per response, like {{\"A1\": \"RESPECTS\", \"A2\": \"VIOLATES\"}}.",
                ledger, "judge_directive", max_tokens=400 + 20 * len(answers))
    return [str(res.get(LETTERS[i], "UNCLEAR")).upper() for i in range(len(answers))]


def judge_goal(tr, answers, ledger):
    g = GOALS[tr["goal"]]
    listing = "\n".join(f"{LETTERS[i]}: {a}" for i, a in enumerate(answers))
    res = jcall("Classify each agent statement by which task it says the agent is working on.\n"
                f"OLD = {g[2]}\nNEW = {g[3]}\nOTHER = neither, both equally, or unclear.\n\n{listing}\n\n"
                "Return JSON with one key per statement, like {\"A1\": \"NEW\", \"A2\": \"OLD\"}.",
                ledger, "judge_goal", max_tokens=400 + 20 * len(answers))
    out = []
    for i in range(len(answers)):
        v = str(res.get(LETTERS[i], "OTHER")).upper()
        out.append(v if v in ("NEW", "OLD", "OTHER") else "OTHER")
    return out


def judge_transcript(rec):
    """Grade every ungraded probe answer of this transcript. One batched call per item and judging pass;
    answers are deduplicated and shuffled so the judge does not see which arm produced them."""
    rng = random.Random(rec["tid"] * 7 + len(rec.get("judge_passes", [])))
    ledger = []
    arms = [a for a in rec["arms"] if "probes" in rec["arms"][a]]
    tr = build(rec["tid"])
    specs = {f"rule{k}": (RULES[r]["rule"], RULES[r]["trigger"]) for k, r in enumerate(tr["rule_idx"])}
    specs["approach"] = APPROACHES[tr["approach"]]
    done = False
    for item in list(specs) + ["goal"]:
        todo = sorted({s["raw"] for a in arms for s in rec["arms"][a]["probes"][item] if "judge" not in s})
        if not todo:
            continue
        rng.shuffle(todo)
        labels = judge_goal(tr, todo, ledger) if item == "goal" else \
            judge_directive(specs[item][0], specs[item][1], todo, ledger)
        lab = dict(zip(todo, labels))
        for a in arms:
            for s in rec["arms"][a]["probes"][item]:
                if "judge" not in s:
                    s["judge"] = lab[s["raw"]]
        done = True
    if done:
        rec.setdefault("judge_passes", []).append(ledger)
    return rec

# ---------------------------------------------------------------- drivers

def path(tid):
    return RAW / f"t{tid:04d}.json"


def load(tid):
    return json.loads(path(tid).read_text()) if path(tid).exists() else None


def save(rec):
    tmp = path(rec["tid"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1))
    tmp.replace(path(rec["tid"]))


def do_base(tid):
    rec = load(tid)
    if rec and rec.get("base_done"):
        return "skip"
    tr = build(tid)
    rec = dict(tid=tid, model=MODEL, transcript=tr, arms={})
    last = rounds(tr)[-1]
    for arm in UNGATED:
        res = run_arm(tr, arm)
        ctx = context_block(res["summary"], res["tail"])
        meas = []
        res["sig"] = dict(rt_generic=rt_generic(last["history"], ctx, meas),
                          rt_aligned=rt_aligned(last["history"], ctx, meas),
                          pc=pc_signal(last["history"], ctx, meas))
        res["measure_ledger"] = meas
        res["probes"], res["probe_ledger"] = probes(tr, ctx)
        res["context_chars"] = len(ctx)
        rec["arms"][arm] = res
    fctx = full_ctx(last["history"])
    p, pl = probes(tr, fctx)
    rec["arms"]["full"] = dict(summary=None, probes=p, probe_ledger=pl, ledger=[], context_chars=len(fctx))
    rec["base_done"] = True
    save(rec)
    return "ok"


def do_gated(tid, thr):
    rec = load(tid)
    if not rec or not rec.get("base_done"):
        return "no base"
    if rec.get("gated_done"):
        return "skip"
    tr = rec["transcript"]
    for arm in GATED:
        t = thr["pc"] if arm == "pc_gate" else thr["rt_generic"]
        res = run_arm(tr, arm, thr=t)
        ctx = context_block(res["summary"], res["tail"])
        res["threshold"] = t
        res["probes"], res["probe_ledger"] = probes(tr, ctx)
        res["context_chars"] = len(ctx)
        rec["arms"][arm] = res
    rec["gated_done"] = True
    save(rec)
    return "ok"


def do_judge(tid):
    rec = load(tid)
    if not rec:
        return "none"
    save(judge_transcript(rec))
    return "ok"


def wrap(fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        (RAW / f"err{a[0]:04d}.txt").write_text(traceback.format_exc())
        return f"err {e!r}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["base", "gated", "judge"])
    ap.add_argument("start", type=int)
    ap.add_argument("n", type=int)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--model", default=orclient.MODEL)
    args = ap.parse_args()
    if args.model.endswith(":free"):
        sys.exit("':free' models are not allowed")
    MODEL = args.model
    workers = min(args.workers, 10)
    tids = range(args.start, args.start + args.n)
    if args.phase == "gated":
        thr = json.loads((OUT / "thresholds.json").read_text())
        jobs = [(do_gated, t, thr) for t in tids]
    elif args.phase == "base":
        jobs = [(do_base, t) for t in tids]
    else:
        jobs = [(do_judge, t) for t in tids]
    with ThreadPoolExecutor(workers) as ex:
        futs = [(j[1], ex.submit(wrap, *j)) for j in jobs]
        for tid, fu in futs:
            print(tid, fu.result(), flush=True)
