"""E9: do cheap signals predict which compactions cause downstream divergence?

For each compaction event: build a transcript with planted load-bearing items, compact it once,
compute the expensive paired-continuation label (probes from full context vs. from the summary,
two samples each), and compute five cheap signals. One JSON file per event in raw/.

Usage: python3 run_e9.py N_EVENTS [WORKERS] [START_EID] [--model MODEL_ID]   (env E9_RAW sets the output dir, default raw/)
"""
import json, random, re, sys, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
import functools  # noqa: E402
import orclient  # noqa: E402
import common  # noqa: E402
from common import (sample_filler, load_rules, render, compact, context_block, decide,  # noqa: E402
                    AGENT_SYSTEM, SUMMARY_PROMPT)
from items import GOALS, FACTS, APPROACHES  # noqa: E402

MODEL = orclient.MODEL


def set_model(model):
    """Route every call (ours and common.py's) through the chosen model id."""
    global MODEL, chat
    MODEL = model
    chat = functools.partial(orclient.chat, model=model)
    common.chat = chat


chat = orclient.chat

import os
RAW = HERE / os.environ.get("E9_RAW", "raw")
RAW.mkdir(exist_ok=True)
RULES = [r for r in load_rules() if r.get("valid")]
N_FILLER = [30, 50, 80]
WORDS = [60, 120, 250]
STYLES = ["narrative", "structured"]
STRUCTURED_PROMPT = (
    "You are compacting the history of a long-running coding agent session so the agent can keep working with a "
    "smaller context. Write a checkpoint in under {words} words with these headings: Goal, Constraints and rules, "
    "Key decisions and facts, Ruled out, Progress, Next steps. Keep only what the agent needs going forward."
)
TAIL_K = 2
PROBE_T = 0.8
CHATTER = ["Operator: thanks, that looks right, keep going.",
           "Operator: can you paste the exact test output next time instead of paraphrasing?",
           "Operator: I'm stepping into a meeting for an hour, carry on with what you were doing.",
           "Operator: nice catch on that one.",
           "Operator: please keep commits small so review stays easy."]

# ---------------------------------------------------------------- event construction

def build_event(eid):
    rng = random.Random(9000 + eid)
    n = N_FILLER[eid % 3]
    words = WORDS[(eid // 3) % 3]
    style = STYLES[(eid // 9) % 2]
    goal = rng.randrange(len(GOALS)); fact = rng.randrange(len(FACTS)); appr = rng.randrange(len(APPROACHES))
    rules = rng.sample(range(len(RULES)), 2)
    turns = sample_filler(n, rng)
    g = GOALS[goal]; f = FACTS[fact]
    # planted items with relative positions (fraction of body); body excludes the verbatim tail
    planted = [
        (rng.uniform(0.0, 0.15), "goal", "Operator: " + g[0]),
        (rng.uniform(0.05, 0.35), "fact_stale", f[0]),
        (rng.uniform(0.40, 0.85), "fact_fix", "Operator: " + f[1]),
        (rng.uniform(0.45, 0.85), "redirect", "Operator: " + g[1]),
        (rng.uniform(0.10, 0.90), "approach", "Operator: " + APPROACHES[appr][0]),
        (rng.uniform(0.0, 0.90), "rule0", "Operator: " + RULES[rules[0]]["rule"]),
        (rng.uniform(0.0, 0.90), "rule1", "Operator: " + RULES[rules[1]]["rule"]),
    ]
    for c in rng.sample(CHATTER, 3):
        planted.append((rng.uniform(0.0, 0.95), "chatter", c))
    planted.sort(key=lambda x: x[0])
    body = list(turns[:-TAIL_K]); tail = list(turns[-TAIL_K:])
    out, kinds = [], []
    pi = 0
    for i, t in enumerate(body):
        while pi < len(planted) and planted[pi][0] * len(body) <= i:
            out.append(planted[pi][2]); kinds.append(planted[pi][1]); pi += 1
        out.append(t); kinds.append("filler")
    while pi < len(planted):
        out.append(planted[pi][2]); kinds.append(planted[pi][1]); pi += 1
    return dict(eid=eid, n_filler=n, words=words, style=style, goal=goal, fact=fact, approach=appr,
                rules=[RULES[r]["id"] for r in rules], rule_idx=rules, body=out, kinds=kinds, tail=tail)

def jcall(prompt, max_tokens=1200, tag="json", messages=None):
    """Robust JSON-object call: json mode first, then plain mode; only dicts accepted."""
    msgs = messages or [{"role": "user", "content": prompt}]
    for attempt in range(6):
        raw = chat(msgs, max_tokens=max_tokens, temperature=0.0, tag=tag, json_mode=attempt < 3)
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

# ---------------------------------------------------------------- probes (expensive label)

def full_context(ev):
    return "[Session history so far, verbatim]\n" + render(ev["body"] + ev["tail"])


def summary_context(ev):
    return context_block(ev["summary"], ev["tail"])


def agent_answer(ctx, question, tag):
    user = f"{ctx}\n\n[New request from the operator]\n{question}"
    return chat([{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": user}],
                max_tokens=150, temperature=PROBE_T, tag=tag).strip()


def parse_fact(ans, fact):
    stale, correct = fact[2].strip(), fact[3]
    pc = re.search(re.escape(correct) + r"(?![\w])", ans)
    ps = re.search(re.escape(stale) + r"(?![\w-])", ans)
    if pc and (not ps or pc.start() <= ps.start()):
        return "CORRECT"
    if ps:
        return "STALE"
    return "OTHER"


def parse_yesno(ans):
    a = ans.strip().strip("*").upper()
    if a.startswith("NO"):
        return "NO"
    if a.startswith("YES"):
        return "YES"
    return "OTHER"


GOAL_PROBE = ("Quick check before you continue: what is the overall goal I most recently set for this session, "
              "and what will you do next toward it? Answer in one or two sentences.")


def classify_goal_answers(ev, answers, rng):
    g = GOALS[ev["goal"]]
    order = list(range(len(answers))); rng.shuffle(order)
    letters = "ABCD"
    listing = "\n".join(f"{letters[k]}: {answers[i]}" for k, i in enumerate(order))
    prompt = ("Classify each agent statement by which task it says the agent is working on.\n"
              f"OLD = {g[2]}\nNEW = {g[3]}\nOTHER = neither, both equally, or unclear.\n\n"
              f"{listing}\n\nReturn JSON like {{\"A\": \"NEW\", \"B\": \"OLD\", ...}} with one key per statement.")
    res = jcall(prompt, max_tokens=300, tag="e9_exp_judge")
    out = [None] * len(answers)
    for k, i in enumerate(order):
        v = str(res.get(letters[k], "OTHER")).upper()
        out[i] = v if v in ("NEW", "OLD", "OTHER") else "OTHER"
    return out


def expensive_label(ev, rng):
    probes = {}
    ctxs = {"full": full_context(ev), "summ": summary_context(ev)}
    for ri, ridx in enumerate(ev["rule_idx"]):
        trig = RULES[ridx]["trigger"]
        probes[f"rule{ri}"] = {c: [decide(ctxs[c], trig, temperature=PROBE_T, tag="e9_exp_probe")[0]
                                   for _ in range(2)] for c in ctxs}
    f = FACTS[ev["fact"]]
    probes["fact"] = {c: [parse_fact(agent_answer(ctxs[c], f[4], "e9_exp_probe"), f) for _ in range(2)] for c in ctxs}
    a = APPROACHES[ev["approach"]]
    probes["approach"] = {c: [decide(ctxs[c], a[1], temperature=PROBE_T, tag="e9_exp_probe")[0]
                              for _ in range(2)] for c in ctxs}
    raw_goal = {c: [agent_answer(ctxs[c], GOAL_PROBE, "e9_exp_probe") for _ in range(2)] for c in ctxs}
    cls = classify_goal_answers(ev, raw_goal["full"] + raw_goal["summ"], rng)
    probes["goal"] = {"full": cls[:2], "summ": cls[2:], "raw": raw_goal}
    return probes

# ---------------------------------------------------------------- cheap signals

def instruction(ev):
    return SUMMARY_PROMPT if ev["style"] == "narrative" else STRUCTURED_PROMPT


def draft(ev, temperature, tag):
    head = instruction(ev).format(words=ev["words"])
    prompt = f"{head}\n\n[Log]\n{render(ev['body'])}"
    return chat([{"role": "user", "content": prompt}], max_tokens=ev["words"] * 3,
                temperature=temperature, tag=tag).strip()


def sig_drafts(ev):
    d = [ev["summary"]] + [draft(ev, 0.7, "e9_draft") for _ in range(2)]
    listing = "\n\n".join(f"[Draft {i + 1}]\n{x}" for i, x in enumerate(d))
    prompt = ("Three independent summaries of the same coding-agent session follow. Compare them ONLY on "
              "load-bearing facts an agent would need to continue correctly: standing rules or constraints from "
              "the operator, the current goal, identifiers such as hosts, files, buckets, or schemas, and approaches "
              "that were ruled out. List (at most 8 short items) every load-bearing fact on which the drafts disagree (one states it and "
              "another omits or contradicts it). Then give a disagreement score from 0 (fully agree) to 10 "
              "(severe disagreement on many load-bearing facts).\n\n"
              f"{listing}\n\nReturn JSON: {{\"disagreements\": [\"...\"], \"score\": <0-10>}}")
    res = jcall(prompt, tag="e9_draft_cmp")
    return dict(drafts=d[1:], disagreements=res.get("disagreements", []), score=float(res.get("score", 0)))


RT_QUESTIONS = ("1. What standing rules or constraints from the operator apply for the rest of the session?\n"
                "2. What is the current goal?\n"
                "3. What approaches have been tried and ruled out?\n"
                "4. What key identifiers (hosts, buckets, schemas, files, runner labels) should be used, and which "
                "should be avoided?")


def rt_answer(ctx, tag):
    prompt = (f"{ctx}\n\nUsing only the context above, answer these questions concisely. Say 'unknown' if the "
              f"context does not say.\n{RT_QUESTIONS}")
    return chat([{"role": "user", "content": prompt}], max_tokens=400, temperature=0.0, tag=tag).strip()


def sig_roundtrip(ev):
    a_full = rt_answer(full_context(ev), "e9_rt_ans")
    a_summ = rt_answer(summary_context(ev), "e9_rt_ans")
    prompt = ("Two sets of answers to the same questions follow. Set R was produced from a full session log; "
              "set S was produced from a compressed summary of it. List (at most 8 short items) each item where S omits, contradicts, or "
              "changes something stated in R that an agent would need to act correctly. Then give a discrepancy "
              "score from 0 (S preserves everything that matters) to 10 (S loses or corrupts most of it).\n\n"
              f"[Questions]\n{RT_QUESTIONS}\n\n[Set R]\n{a_full}\n\n[Set S]\n{a_summ}\n\n"
              "Return JSON: {\"discrepancies\": [\"...\"], \"score\": <0-10>}")
    res = jcall(prompt, tag="e9_rt_cmp")
    return dict(ans_full=a_full, ans_summ=a_summ, discrepancies=res.get("discrepancies", []),
                score=float(res.get("score", 0)))


def sig_selfreport(ev):
    head = instruction(ev).format(words=ev["words"])
    prompt = f"{head}\n\n[Log]\n{render(ev['body'])}"
    follow = ("List the specific items from the log that you left out of your summary or stated only vaguely and "
              "that might matter later in the session (at most 8 short items; rules, decisions, identifiers, ruled-out approaches, goal "
              "changes). Then rate from 0 to 10 how likely it is that the omissions will cause the agent to make a "
              "mistake. Return JSON: {\"dropped\": [\"...\"], \"risk\": <0-10>}")
    msgs = [{"role": "user", "content": prompt}, {"role": "assistant", "content": ev["summary"]},
            {"role": "user", "content": follow}]
    res = jcall(None, tag="e9_self", messages=msgs)
    return dict(dropped=res.get("dropped", []), risk=float(res.get("risk", 0)))

# ---------------------------------------------------------------- driver

def run_event(eid):
    path = RAW / f"ev{eid:04d}.json"
    if path.exists():
        return "skip"
    try:
        ev = build_event(eid)
        ev["model"] = MODEL
        rng = random.Random(eid)
        ev["summary"] = compact("", ev["body"], words=ev["words"], instruction=instruction(ev), tag="e9_compact")
        ev["probes"] = expensive_label(ev, rng)
        ev["sig_drafts"] = sig_drafts(ev)
        ev["sig_roundtrip"] = sig_roundtrip(ev)
        ev["sig_self"] = sig_selfreport(ev)
        path.write_text(json.dumps(ev, indent=1))
        return "ok"
    except Exception as e:
        (RAW / f"err{eid:04d}.txt").write_text(traceback.format_exc())
        return f"err {e!r}"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("workers", type=int, nargs="?", default=8)
    ap.add_argument("start", type=int, nargs="?", default=0)
    ap.add_argument("--model", default=orclient.MODEL)
    args = ap.parse_args()
    if args.model.endswith(":free"):
        sys.exit("':free' models are reserved for the coordinator")
    set_model(args.model)
    n, workers, start = args.n, args.workers, args.start
    with ThreadPoolExecutor(workers) as ex:
        for eid, r in zip(range(start, start + n), ex.map(run_event, range(start, start + n))):
            print(eid, r, flush=True)
