"""Audit the consolidated block and the ledger against ground truth (E23).

For each session, an audit judge reads a block and reports the state it gives each of the session's 8 rules
(IN_FORCE_OLD, IN_FORCE_NEW, LIFTED, ABSENT, CONFLICT) and which goal it names as the current objective.
Blocks audited:
  consol_final     the final pin_consol block (consolidated text plus raw turns since the last update)
  consol_after_k   the first consolidated block written after each revocation or amendment (state at that time)
  ledger_final     the final rendered ledger
Fact values are checked by string match. Errors of interest: a dropped active rule (not IN_FORCE_OLD), a
revoked rule still in force (IN_FORCE_OLD or CONFLICT), an amended rule not in its new form, and a revoked
rule that a snapshot handled but the final block shows in force again (resurrection).

Usage: python3 audit.py [--model MODEL]   -> results/<model>/audit.jsonl
"""
import argparse, json, random, re, zlib
from concurrent.futures import ThreadPoolExecutor

import e23lib as L
from grade import has

AUDIT = """Below is a block of notes that a coding agent sees on every step.

BLOCK:
{block}

For each numbered rule, report what the block tells the agent about that rule NOW:
- IN_FORCE_OLD: the block presents the rule in its original version (as written below) as currently in force.
- IN_FORCE_NEW: the block presents the rule as in force in its changed version (only for rules with a listed change).
- LIFTED: the block says the rule was lifted or revoked, or that the restricted action is now permitted, and does not present the rule as in force.
- CONFLICT: the block presents the rule as in force and also says it was lifted, or gives both versions as in force.
- ABSENT: the block does not mention the rule.

Rules:
{rules}

Also: which candidate does the block name as the operator's current main objective? Candidates:
{goals}
Answer with the letter, or NONE if it names none of them.

Return JSON only: {{"rules": [{{"n": 1, "state": "..."}}, ...], "objective": "<letter or NONE>"}}"""


def audit_block(block, s, salt):
    t = s["truth"]
    items = ([("active", r, None) for r in t["active"]] + [("revoked", r, None) for r in t["revoked"]] +
             [("amended", a, a["amendment"]) for a in t["amended"]])
    order = list(range(len(items)))
    random.Random(zlib.crc32(salt.encode())).shuffle(order)
    lines = []
    for n, j in enumerate(order, 1):
        kind, r, change = items[j]
        lines.append(f"{n}. {r['rule']}" + (f"\n   Listed change: {change}" if change else ""))
    goals = [g["task"] for g in t["goals"]]
    gtext = "\n".join(f"{chr(65 + i)}. {g}" for i, g in enumerate(goals))
    prompt = AUDIT.format(block=block, rules="\n".join(lines), goals=gtext)
    d = L.json_call(prompt, max_tokens=1500, temperature=0.0, tag="e23_audit", salt=salt)
    states = {int(x.get("n", 0)): str(x.get("state", "")).upper() for x in d.get("rules", []) if isinstance(x, dict)}
    out = []
    for n, j in enumerate(order, 1):
        kind, r, _ = items[j]
        out.append(dict(kind=kind, id=r["id"], state=states.get(n, "MISSING"),
                        direction=r.get("direction"), changed_turn=r.get("revoked_turn") or r.get("amended_turn")))
    obj = str(d.get("objective", "NONE")).strip().upper()[:1]
    gi = ord(obj) - 65 if obj and obj.isalpha() and ord(obj) - 65 < len(goals) else None
    return out, gi


def fact_check(block, s):
    res = []
    for f in s["truth"]["facts"]:
        v = f["values"]
        res.append(dict(attr=f["attr"], n_versions=len(v), current=has(v[-1], block),
                        all_versions=all(has(x, block) for x in v)))
    return res


def audit_session(s, res):
    rows = []
    t = s["truth"]
    ng = len(t["goals"])
    pc = res["prep"]
    jobs = [("consol_final", pc["consol_block"], None)]
    changes = sorted({r["revoked_turn"] for r in t["revoked"]} | {a["amended_turn"] for a in t["amended"]})
    seen = set()
    for ct in changes:
        snap = next((h for h in pc["consol_history"] if h["after_turn"] >= ct), None)
        if snap and snap["after_turn"] not in seen:
            seen.add(snap["after_turn"])
            jobs.append((f"consol_after_{snap['after_turn']}", snap["block"], snap["after_turn"]))
    if "ledger" in res:
        jobs.append(("ledger_final", L.render_ledger(res["ledger"]["final"]), None))
    for name, block, at in jobs:
        rules, gi = audit_block(block, s, f"{s['sid']}|{name}")
        rows.append(dict(sid=s["sid"], M=s["M"], base=s["base"], block=name, after_turn=at, rules=rules,
                         objective=("current" if gi == ng - 1 else "stale" if gi is not None else "none"),
                         facts=fact_check(block, s), tokens=L.ntok(block)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    a = ap.parse_args()
    outdir = L.set_model(a.model)
    truth = {s["sid"]: s for s in json.loads((L.HERE / "data" / "sessions.json").read_text())}
    jobs = []
    for f in sorted((outdir / "sessions").glob("M*.json")):
        res = json.loads(f.read_text())
        jobs.append((truth[res["sid"]], res))
    with ThreadPoolExecutor(8) as ex:
        rows = [r for rs in ex.map(lambda x: audit_session(*x), jobs) for r in rs]
    with open(outdir / "audit.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(len(rows), "blocks audited")


if __name__ == "__main__":
    main()
