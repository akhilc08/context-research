"""E15 Part A: which property of a preserved rule drives the summary-versus-pin gap?

Starts from E6 summaries (unconditional form) that E6's pass-2 judge labeled INTACT. For each,
an extraction call copies (a) the summary sentence(s) that carry the rule and (b) the shortest
span that states it (the summary's own paraphrase). Removing (a) gives the summary without the
rule; validation checks that the judge then calls the rule ABSENT or DISTORTED, and that (b) on
its own is INTACT or DETAIL_LOST. Every context below is built from that same material, and
only one property changes between matched cells.

Cells (tail = the 15 raw turns after round R, unless marked t3 = 3 turns as in E6):
  asis                       the original summary (paraphrase, inside the narrative)
  in_{para,verb}_{bare,active,past}   rule sentence(s) replaced inside the narrative by the
                             paraphrase or the verbatim rule, framed bare, as "Operator rule
                             (active): ...", or as "Earlier in the session, the operator said: ..."
  sec_{para,verb}_{start,mid,end}_{active,past}   rule removed from the narrative and stated in
                             a separate block placed before the summary, between summary and
                             tail, or after the tail; block framed as active rules or as past notes
  pin_end, pin_mid           original summary plus the verbatim rule in an active block
  floor                      summary with the rule removed, no block
  ceiling                    no compaction: raw chunk 0 (which states the rule) plus the tail
  asis_t3, pin_mid_t3        bridge to E6 (3-turn tail)

The default run uses 16 of these 25 cells (DEFAULT_CELLS below), chosen so that every
pre-specified contrast is covered; `--cells all` runs the full layout.

Usage: python3 run_a.py prepare | decide  [--model ID] [--threads N] [--reps 2] [--cells all]
Outputs: data/a_items.jsonl (items with spans and validation), data/a_decisions.jsonl.
"""
import argparse, json, random, re, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import e15lib as L

E6_DATA = L.OVERNIGHT / "e6_ratchet" / "data"
ITEMS_PER_RULE = 2
CANDIDATES_PER_RULE = 4
REGIME_ORDER = ("recursive", "source", "selective", "recursive_keeprules")

EXTRACT = """Below are an operator rule and a summary of a coding-agent session that restates it.

RULE:
{rule}

SUMMARY:
{summary}

Copy from the SUMMARY, character for character:
1. "sentences": the complete sentence(s) or bullet line(s) of the summary that carry this rule, as few as possible.
2. "phrase": the shortest contiguous span inside those sentences that on its own still states the rule's requirement.

Return JSON only: {{"sentences": ["..."], "phrase": "..."}}"""


def load_e6():
    T = [json.loads(l) for l in (E6_DATA / "transcripts.jsonl").read_text().splitlines()]
    J = {}
    for l in (E6_DATA / "rejudge.jsonl").read_text().splitlines():
        d = json.loads(l)
        J[(d["id"], d["form"], d["regime"], d["R"])] = d["judge2"]
    return T, J


def candidates(seed=15):
    T, J = load_e6()
    rng = random.Random(seed)
    by_rule = {}
    for t in T:
        if t["form"] != "rule":
            continue
        for rec in t["rounds"]:
            if rec["R"] >= 2 and J.get((t["id"], "rule", t["regime"], rec["R"]), {}).get("verdict") == "INTACT":
                by_rule.setdefault(t["id"], {}).setdefault(t["regime"], []).append(
                    {"id": t["id"], "regime": t["regime"], "R": rec["R"], "summary": rec["summary"],
                     "rule": t["rule_text"], "trigger": t["trigger"]})
    out = []
    for rid in sorted(by_rule):
        regs = list(by_rule[rid])
        rng.shuffle(regs)
        picks = [rng.choice(by_rule[rid][g]) for g in regs]
        # top up from any regime if fewer regimes than candidates wanted
        pool = [c for g in regs for c in by_rule[rid][g] if c not in picks]
        rng.shuffle(pool)
        out.extend((picks + pool)[:CANDIDATES_PER_RULE])
    return out


def find_span(text, span):
    """Exact location of span in text, tolerant only of whitespace differences."""
    if span in text:
        i = text.index(span)
        return i, i + len(span)
    pat = r"\s+".join(re.escape(w) for w in span.split())
    m = re.search(pat, text)
    return (m.start(), m.end()) if m else None


def extract(c):
    for attempt in range(3):
        try:
            j = L.json_call(EXTRACT.format(rule=c["rule"], summary=c["summary"]), max_tokens=600,
                            temperature=0.0 if attempt == 0 else 0.4, tag="e15a_extract")
        except ValueError:
            continue
        sents = [s for s in j.get("sentences", []) if isinstance(s, str) and s.strip()]
        phrase = str(j.get("phrase", "")).strip()
        locs = [find_span(c["summary"], s.strip()) for s in sents]
        if not sents or not phrase or any(l is None for l in locs):
            continue
        if not any(find_span(s, phrase) for s in sents):
            continue
        return sents, phrase, locs
    return None


def remove_spans(summary, locs, replacement=""):
    """Replace the first span with `replacement` and delete the rest; tidy whitespace."""
    locs = sorted(locs)
    out, prev = [], 0
    for k, (a, b) in enumerate(locs):
        out.append(summary[prev:a])
        if k == 0 and replacement:
            out.append(replacement)
        prev = b
    out.append(summary[prev:])
    s = "".join(out)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"(?m)^\s*[-*]\s*$\n?", "", s)  # empty bullet left behind
    s = re.sub(r"  +", " ", s)
    return s.strip()


def prepare(args, data):
    out = data / "a_items.jsonl"
    cands = candidates()
    print(len(cands), "candidates", flush=True)

    def go(c):
        ex = extract(c)
        if ex is None:
            return {**c, "ok": False, "why": "extraction"}
        sents, phrase, locs = ex
        minus = remove_spans(c["summary"], locs)
        j_minus = L.judge2(c["rule"], minus, tag="e15a_valid")
        j_phrase = L.judge2(c["rule"], phrase, tag="e15a_valid")
        ok = j_minus["verdict"] in ("ABSENT", "DISTORTED") and j_phrase["verdict"] in ("INTACT", "DETAIL_LOST")
        return {**c, "sentences": sents, "phrase": phrase, "locs": locs, "summary_minus": minus,
                "judge_minus": j_minus, "judge_phrase": j_phrase, "ok": ok,
                "why": "" if ok else "validation"}

    raw = data / "a_prepare_raw.jsonl"  # per-candidate cache so an interrupted prepare resumes
    have = {(r["id"], r["regime"], r["R"]): r for r in L.read_jsonl(raw)}
    lock = threading.Lock()

    def go_cached(c):
        k = (c["id"], c["regime"], c["R"])
        if k in have:
            return have[k]
        try:
            r = go(c)
        except RuntimeError as e:
            print("FAILED", k, repr(e)[:120], flush=True)
            return None
        L.append_jsonl(raw, r, lock)
        return r

    with ThreadPoolExecutor(8) as ex:
        res = [f.result() for f in as_completed([ex.submit(go_cached, c) for c in cands])]
    if any(r is None for r in res):
        raise SystemExit("some candidates failed; rerun prepare to resume")
    res.sort(key=lambda r: (r["id"], REGIME_ORDER.index(r["regime"]), r["R"]))
    # keep ITEMS_PER_RULE valid items per rule, in candidate order (candidate order is random)
    order = {(c["id"], c["regime"], c["R"]): k for k, c in enumerate(cands)}
    res.sort(key=lambda r: order[(r["id"], r["regime"], r["R"])])
    kept = {}
    for r in res:
        r["selected"] = bool(r["ok"]) and kept.get(r["id"], 0) < ITEMS_PER_RULE
        if r["selected"]:
            kept[r["id"]] = kept.get(r["id"], 0) + 1
    with open(out, "w") as f:
        for r in res:
            f.write(json.dumps(r) + "\n")
    print(f"ok {sum(r['ok'] for r in res)}/{len(res)}, selected {sum(r['selected'] for r in res)} "
          f"over {len(kept)} rules", flush=True)


def sentence(text):
    text = text.strip().rstrip(".;:,")
    return text[0].upper() + text[1:] + "." if text else text


def framed(text, framing):
    if framing == "bare":
        return sentence(text)
    if framing == "active":
        return "Operator rule (active): " + sentence(text)
    return 'Earlier in the session, the operator said: "' + sentence(text) + '"'


def block(text, framing):
    if framing == "active":
        return "[Standing operator rules, in force for every action]\n- " + framed(text, "active")
    return "[Notes from earlier in the session]\n- " + framed(text, "past")


def contexts(item):
    chunks = L.e6_transcript(item["rule"], item["id"])
    tail, tail3 = chunks[item["R"]], chunks[item["R"]][:3]
    S, M, locs = item["summary"], item["summary_minus"], [tuple(x) for x in item["locs"]]
    text = {"para": item["phrase"], "verb": item["rule"]}
    C = {"asis": L.build_context(S, tail)}
    for w in ("para", "verb"):
        for fr in ("bare", "active", "past"):
            C[f"in_{w}_{fr}"] = L.build_context(remove_spans(S, locs, framed(text[w], fr)), tail)
        for pos in ("start", "mid", "end"):
            for fr in ("active", "past"):
                C[f"sec_{w}_{pos}_{fr}"] = L.build_context(M, tail, **{pos: block(text[w], fr)})
    pin = block(item["rule"], "active")
    C["pin_end"] = L.build_context(S, tail, end=pin)
    C["pin_mid"] = L.build_context(S, tail, mid=pin)
    C["pin_para_end"] = L.build_context(S, tail, end=block(item["phrase"], "active"))  # follow-up
    C["floor"] = L.build_context(M, tail)
    C["ceiling"] = L.build_context("", chunks[0] + tail)
    C["asis_t3"] = L.build_context(S, tail3)
    C["pin_mid_t3"] = L.build_context(S, tail3, mid=pin)
    return C


# Cells actually run (the provider's ~45% empty-response rate forced a fractional design).
# Every pre-specified contrast is covered; `--cells all` runs the full 26-cell layout.
# FOLLOWUP_CELLS were added after an interim look at half the data (exploratory).
FOLLOWUP_CELLS = ["in_para_bare", "in_para_past", "in_verb_past", "sec_para_end_past", "pin_para_end"]
DEFAULT_CELLS = ["ceiling", "floor", "asis", "pin_end", "pin_mid", "asis_t3", "pin_mid_t3",
                 "in_verb_bare", "in_para_active", "in_verb_active",
                 "sec_para_mid_active", "sec_para_end_active", "sec_verb_start_active",
                 "sec_verb_mid_active", "sec_verb_end_active", "sec_verb_end_past"]


def decide_phase(args, data):
    items = [r for r in L.read_jsonl(data / "a_items.jsonl") if r["selected"]]
    out = data / "a_decisions.jsonl"
    done = {(d["id"], d["regime"], d["R"], d["cell"], d["rep"]) for d in L.read_jsonl(out)}
    jobs = []
    for it in items:
        for cell, ctx in contexts(it).items():
            if args.cells != "all" and cell not in args.cells.split(","):
                continue
            for k in range(args.reps):
                if (it["id"], it["regime"], it["R"], cell, k) not in done:
                    jobs.append((it, cell, k, ctx))
    print(len(done), "done,", len(jobs), "to run", flush=True)
    lock = threading.Lock()

    def go(j):
        it, cell, k, ctx = j
        d, raw = L.decide(ctx, it["trigger"], tag="e15a_decide")
        L.append_jsonl(out, {"id": it["id"], "regime": it["regime"], "R": it["R"], "cell": cell, "rep": k,
                             "decision": d, "raw": raw, "ctx_chars": len(ctx)}, lock)

    with ThreadPoolExecutor(args.threads) as ex:
        for n, f in enumerate(as_completed([ex.submit(go, j) for j in jobs]), 1):
            f.result()
            if n % 250 == 0:
                print(n, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["prepare", "decide"])
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--cells", default=",".join(DEFAULT_CELLS), help="comma list or 'all'")
    a = ap.parse_args()
    d = L.set_model(a.model, a.threads)
    {"prepare": prepare, "decide": decide_phase}[a.phase](a, d)
