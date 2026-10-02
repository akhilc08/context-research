"""Grade E18 outputs.

Summaries: for every chain, round 1 to 10, and planted identifier, a deterministic check gives
exact | normalized | partial | candidate | absent. Only 'candidate' (a same-type token within edit
distance of the target, or equal to the distractor or old value) goes to an LLM judge, which decides
whether the summary presents that token as the item. Final status: kept, partial, mutated, dropped.

Probes: the reply's COMMAND is checked deterministically (correct, partial, wrong when a same-type
near token appears). ASK replies are 'ask'. Commands with no same-type token and no placeholder go to
a judge that decides whether the command fills in a concrete value for the item (wrong) or not (missing).

Usage: python3 grade.py [--model MODEL]
Writes data/<slug>/graded_summaries.jsonl, data/<slug>/graded_probes.jsonl
"""
import argparse, json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from orclient import MODEL  # noqa: E402
import idents as I  # noqa: E402
from run import Cache, slug  # noqa: E402

JUDGE_MODEL = MODEL  # judge stays on the default backbone unless --judge-model is given

SUM_JUDGE = """Below is a summary of a coding agent's session.

[Summary]
{summary}

Item: {role}.
Question: Does the summary present `{cand}` as {role}, that is, as the value an agent reading only this summary would use for that item? Answer YES if the summary uses `{cand}` for that item, even if that might be wrong. Answer NO if `{cand}` is mentioned only as something else (for example an unrelated thing, an old or replaced value, or a value explicitly rejected)."""

PROBE_JUDGE = """An operator asked a coding agent: "{probe}"
The task needs {role}.
The agent replied:
{reply}

Question: Does the agent's command fill in a specific, concrete value for {role} (any concrete value, right or wrong)? Answer NO if it leaves a placeholder, a variable to be filled in later, searches or asks for the value, or omits it."""

PLACEHOLDER = re.compile(r"<[^>]+>|\{[a-z_ ]+\}|YOUR_|REPLACE|XXX|\.\.\.|UNKNOWN|TBD|CHANGEME", re.I)


def yes(cache, prompt, tag):
    msgs = [{"role": "user", "content": prompt + "\n\nAnswer with exactly one word: YES or NO."}]
    if cache.has(msgs, 200, 0.0, JUDGE_MODEL, salt="judge"):  # a previously needed fallback
        return cache.call(msgs, 200, 0.0, JUDGE_MODEL, tag, salt="judge").strip().upper().startswith("Y"), ""
    try:
        raw = cache.call(msgs, 10, 0.0, JUDGE_MODEL, tag, salt="judge")
    except RuntimeError:  # rare persistent empty completions at 10 tokens: retry with more room
        raw = cache.call(msgs, 200, 0.0, JUDGE_MODEL, tag, salt="judge")
    return raw.strip().upper().startswith("Y"), raw


def parse_reply(reply):
    for line in reply.splitlines():
        s = line.strip().strip("*`").strip()
        if s.upper().startswith("COMMAND:"):
            return "COMMAND", s.split(":", 1)[1].strip().strip("`")
        if s.upper().startswith("ASK:"):
            return "ASK", s.split(":", 1)[1].strip()
    return "OTHER", reply.strip()


def main():
    global JUDGE_MODEL
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--judge-model", default=MODEL)
    a = ap.parse_args()
    JUDGE_MODEL = a.judge_model
    out = HERE / "data" / slug(a.model)
    cache = Cache(out / "cache.jsonl")
    S = {s["id"]: s for s in json.loads((HERE / "data" / "scenarios.json").read_text())}
    items = {(sid, it["type"]): it for sid, s in S.items() for it in s["items"]}

    # ---------------- summaries
    units = []
    for line in (out / "chains.jsonl").read_text().splitlines():
        ch = json.loads(line)
        sc = S[ch["scenario"]]
        for rd in ch["rounds"]:
            for it in sc["items"]:
                units.append((ch, rd, sc, it))

    def g_sum(u):
        ch, rd, sc, it = u
        st, cands = I.classify_text(it["type"], rd["summary"], it["target"], it["near"], sc)
        rec = {"scenario": sc["id"], "budget": ch["budget"], "summarizer": ch["summarizer"], "round": rd["round"],
               "type": it["type"], "cond": it["cond"], "target": it["target"], "near": it["near"], "det": st,
               "judged": []}
        status, kind = {"exact": "kept", "normalized": "kept", "partial": "partial", "absent": "dropped"}.get(st), None
        if st == "candidate":
            status = "dropped"
            for c in cands:
                ok, raw = yes(cache, SUM_JUDGE.format(summary=rd["summary"], role=it["role"], cand=c), "e18|judge_sum")
                rec["judged"].append({"cand": c, "yes": ok})
                if ok and status != "mutated":
                    status, kind = "mutated", I.mutation_kind(it["type"], c, it["target"], it["near"], it["cond"])
        rec.update({"status": status, "kind": kind})
        return rec

    with ThreadPoolExecutor(8) as ex:
        gs = list(ex.map(g_sum, units))
    with open(out / "graded_summaries.jsonl", "w") as f:
        for r in gs:
            f.write(json.dumps(r) + "\n")
    print(f"graded {len(gs)} summary-identifier units; judged {sum(1 for r in gs if r['det'] == 'candidate')}")

    # ---------------- probes
    probes = [json.loads(l) for l in (out / "probes.jsonl").read_text().splitlines()] if (out / "probes.jsonl").exists() else []

    def g_probe(p):
        sc = S[p["scenario"]]
        it = items[(p["scenario"], p["type"])]
        kind, body = parse_reply(p["reply"])
        rec = dict(p)
        rec.update({"kind": kind, "body": body, "judge": None, "wrong_kind": None})
        if kind == "ASK":
            st, _ = I.classify_text(it["type"], body, it["target"], it["near"], sc)
            # an ASK that already states the correct value asks about something else (credentials, namespace)
            rec["outcome"] = "ask_known" if st in ("exact", "normalized") else "ask"
            return rec
        st, cands = I.classify_text(it["type"], body, it["target"], it["near"], sc)
        if st in ("exact", "normalized"):
            rec["outcome"] = "correct"
        elif st == "partial":
            rec["outcome"] = "partial"
        elif st == "candidate":
            rec["outcome"] = "wrong"
            rec["wrong_kind"] = I.mutation_kind(it["type"], cands[0], it["target"], it["near"], it["cond"])
            rec["wrong_value"] = cands[0]
        elif [c for c in I.candidates(it["type"], body, sc["tprefix"], sc["package"]) if not I.same(it["type"], c, it["target"])]:
            # v2 rule (added after the first judge validation): in a command, any same-type token in the
            # item's slot is the agent's chosen value, even when it is far from the target
            c = [c for c in I.candidates(it["type"], body, sc["tprefix"], sc["package"]) if not I.same(it["type"], c, it["target"])][0]
            rec["outcome"] = "wrong"
            rec["wrong_kind"] = I.mutation_kind(it["type"], c, it["target"], it["near"], it["cond"])
            rec["wrong_value"] = c
        elif PLACEHOLDER.search(body) or (it["type"] == "branch" and re.search(r"\bHEAD\b", body)):
            # v2 rule: pushing HEAD names no branch, so it is not a concrete branch value
            rec["outcome"] = "missing"
        else:
            ok, raw = yes(cache, PROBE_JUDGE.format(probe=it["probe"], role=it["role"], reply=body), "e18|judge_probe")
            rec["judge"] = ok
            rec["outcome"] = "wrong" if ok else "missing"
            if ok:
                rec["wrong_kind"] = "other_value"
        return rec

    with ThreadPoolExecutor(8) as ex:
        gp = list(ex.map(g_probe, probes))
    with open(out / "graded_probes.jsonl", "w") as f:
        for r in gp:
            f.write(json.dumps(r) + "\n")
    print(f"graded {len(gp)} probes; judged {sum(1 for r in gp if r['judge'] is not None)}")


if __name__ == "__main__":
    main()
