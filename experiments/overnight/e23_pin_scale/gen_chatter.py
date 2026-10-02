"""Generate the pool of non-directive operator messages (chatter) for E23.

Five categories. Every message must leave the session state unchanged: no new rule, task, value, or
procedure. `near_miss` messages sound directive but decide nothing ("maybe we should consider X someday").

Usage: python3 gen_chatter.py [--model MODEL]   -> data/chatter.json
"""
import argparse, json, re

import e23lib as L

CATS = {
    "ack": (90, "short acknowledgements, thanks, or praise for work just done (\"thanks, looks good\", "
                "\"nice, that diff reads well\")"),
    "status": (90, "status or progress questions that ask but do not instruct (\"how is it going?\", "
                   "\"did the last test run pass?\", \"roughly how long until you have something to show?\")"),
    "clarify": (70, "passing clarifications or answers to a question the agent might have asked about the work "
                    "in front of it, with no lasting effect and no new value to remember (\"yes, that is the "
                    "test I meant\", \"either wording is fine for that comment\")"),
    "logistics": (70, "small talk or logistics about the operator's day (\"stepping out for lunch\", "
                      "\"back now\", \"my laptop is updating, give me a minute\")"),
    "near_miss": (140, "messages that sound like instructions but decide nothing: musing about ideas for "
                       "someday, hypotheticals, opinions without a decision, ideas explicitly deferred, or "
                       "questions about why something is done a certain way (\"maybe we should consider "
                       "moving the cron jobs to a queue someday, not now\", \"I wonder if we should drop the "
                       "legacy CSV export eventually; no need to act on it\", \"in an ideal world we'd have "
                       "property tests for the tax code\")"),
}

PROMPT = """You are writing realistic messages that a human operator types to an autonomous coding agent during a long working session on "Ledgerly", a Python billing service (invoices, payments, ledgers, tax, exports, CI).

Write {n} distinct messages of this kind: {desc}.

Constraints:
- Each message must leave the agent's instructions unchanged. It must NOT set, change, or lift any rule, approval requirement, threshold, or constraint; must NOT assign or redirect a task; must NOT state a host name, branch, channel, person's handle, ticket id, version, or other value to remember; must NOT ask for a procedure.
- Do not mention specific file paths, Slack channels, @handles, hostnames, or numeric thresholds.
- Vary length (3 to 35 words), tone, and wording. Some lowercase, some with typos, like real chat.
- Batch {batch}: avoid the most obvious phrasings; make these different from typical examples.

Return JSON: {{"messages": ["...", "..."]}}"""


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=L.DEFAULT_MODEL)
    a = ap.parse_args()
    L.set_model(a.model)
    out, seen = [], set()
    for cat, (target, desc) in CATS.items():
        got, b = 0, 0
        while got < target and b < 20:
            d = L.json_call(PROMPT.format(n=25, desc=desc, batch=b), max_tokens=3000, temperature=1.0,
                            tag="e23_gen_chatter", salt=f"{cat}|{b}")
            b += 1
            for m in (d.get("messages") if isinstance(d, dict) else d) or []:
                if not isinstance(m, str) or not m.strip():
                    continue
                k = norm(m)
                if k in seen or len(k.split()) > 45:
                    continue
                seen.add(k)
                out.append(dict(id=f"c{len(out):03d}", category=cat, text=m.strip()))
                got += 1
                if got >= target:
                    break
        print(cat, got)
    (L.HERE / "data" / "chatter.json").write_text(json.dumps(out, indent=1))
    print(len(out), "chatter messages")


if __name__ == "__main__":
    main()
