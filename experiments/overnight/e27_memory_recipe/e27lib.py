"""E27 prompts and pure helpers (no model calls here).

Prompts copied from earlier studies are marked with their source. Adaptations to the
LongMemEval/Supersede setting (the "operator" is the user) are documented in README.md.
"""
import json, re

from supersede.rollout import MEMORY_SYSTEM

# ------------------------------------------------------------------ E14 / E4 prompts, unchanged

EXTRACT = (  # E4 extraction prompt (used by pin, vpin, registry, watchpoints)
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
EXTRACT_CANON = (  # E14 canonical-key extraction (used by vpin_canon and the recipe's versioned block)
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
ANSWER_FULL = ("The following is the full history of your past conversations with the "
               "user. Answer the user's question based on it. Be concise.")
JUDGE = (  # Supersede's LongMemEval judge (E4, E14)
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
JUDGE4 = (
    "Classify a model answer to a question about a fact that changed over time.\n"
    "Question: {q}\nCorrect (gold) value: {gold}\nWrong-version value(s): {stale}\n"
    "Model answer: {ans}\n\nReply with exactly one word: 'correct' if it conveys the gold value "
    "and not a wrong-version value, 'stale' if it conveys a wrong-version value instead of the "
    "gold value, 'ambiguous' if it gives both as current, 'wrong' otherwise.")
CHECK = (  # E4 watchpoint restatement check, unchanged
    "Below are an assistant's NOTES (its only memory) and a list of fact KEYS. For each key, "
    "state the value the NOTES give for it right now, copying it from the notes. If the notes do "
    "not state it, write NOT_IN_NOTES. Use only the notes.\n"
    "Return JSON keyed by each key's ID: {{\"K1\": \"<value or NOT_IN_NOTES>\", ...}} with every ID.\n\n"
    "NOTES:\n{notes}\n\nKEYS:\n{keys}"
)

# ------------------------------------------------------------------ E27 notes-prompt variants


def _with_clause(clause):
    """Supersede's MEMORY_SYSTEM with a clause inserted before the cap sentence."""
    return MEMORY_SYSTEM.replace(" Your notes are hard-capped", " " + clause + " Your notes are hard-capped")


VARIANT_SYSTEMS = {
    # E9 structured checkpoint: headings, adapted from coding-agent headings to user memory
    "struct": _with_clause("Write the notes under these headings: Facts (current values), Recent changes, "
                           "Plans and goals, Preferences."),
    # E6 keep-rules clause, adapted from rules to facts
    "carry": _with_clause("Always carry forward every fact the user has stated, with its latest value, even if "
                          "it has not come up recently."),
    # E5 provenance clause, adapted: the untrusted source here is the assistant, not tool output
    "prov300": _with_clause("Provenance matters. Attribute every fact to its source: record facts the user "
                            "stated as the user's own, and mark anything stated only by the assistant as "
                            "'assistant suggested'. Never restate an assistant suggestion as a fact about the user."),
    # E2 anchor prompt, adapted from 'most recent objective' to 'most recent value'
    "anchor": _with_clause("If a fact has had more than one value in the notes or the session, identify the "
                           "MOST RECENT value and write it first, as 'Now: <fact> = <value>'."),
}

RESUM_SYSTEM = (  # source re-summarization: rewrite from all raw sessions, never from prior notes
    "You maintain a NOTES field that is your ONLY memory of a long, ongoing conversation with a "
    "user. Each time, you receive the COMPLETE transcripts of every session so far. Write notes "
    "that capture everything about the user that may matter later. When later information changes "
    "something, keep only the latest value; never keep outdated facts. Your notes are hard-capped "
    "at {budget} characters. Output ONLY the notes.")

PROV_SYSTEM = (  # the recipe's structured provenance notes (E21 recipe, adapted)
    "You maintain a NOTES field that is your ONLY memory of a long, ongoing conversation with a "
    "user. You will never see earlier sessions again, only your notes. Each turn you receive your "
    "current notes and the transcript of one new session, in which each user turn is labeled "
    "[S<session>.U<turn>]. Rewrite your COMPLETE notes to capture everything about the user that "
    "may matter later. Provenance matters: attribute every fact to the user turn where it was "
    "stated, for example 'commute 45 min (S2.U3)'. Record as fact only what the user said; mark "
    "anything stated only by the assistant as 'assistant suggested', or leave it out. When new "
    "information changes a fact you already noted, write the new value first and keep the old "
    "value marked as superseded, for example 'commute 30 min (S2.U3; superseded: 45 min, S1.U2)'. "
    "Your notes are hard-capped at {budget} characters. Output ONLY the new notes.")

KEEPER = (  # recipe keeper, one call per session; never sees the question or gold
    "Below is ONE session of a conversation between a user and an assistant. The user's turns are "
    "labeled [U<number>]; assistant turns are shortened. List the numbers of the user turns that "
    "STATE or UPDATE a concrete fact about the user, people in their life, or their things: counts, "
    "amounts, times, dates, durations, frequencies, places, possessions, statuses, scores, records, "
    "goals, plans, or preferences. A fact mentioned in passing inside a request counts. Skip user "
    "turns that only ask for help or information without stating such a fact.\n"
    "Return JSON {{\"turns\": [<numbers>]}}.\n\nSESSION:\n{session}")

SELFCHECK = (  # naive self-judgment watchpoint (E1/E2 style yes/no), batched per key
    "Below are an assistant's NOTES (its only memory) and a list of facts with their current "
    "values. For each fact, do the notes make its current value clear? Answer YES or NO for each ID.\n"
    "Return JSON keyed by each ID: {{\"K1\": \"YES\", ...}} with every ID.\n\n"
    "NOTES:\n{notes}\n\nFACTS:\n{facts}")

RT_Q = ("1. What concrete facts has the user stated about themselves, people in their life, or their things "
        "(counts, amounts, times, places, possessions, statuses, scores, records), with their current values?\n"
        "2. Which of those facts has the user changed, and what were the old and new values?\n"
        "3. What plans, goals, or upcoming events has the user mentioned?\n"
        "4. What preferences has the user stated?")
RT_ANSWER = ("{ctx}\n\nUsing only the context above, answer these questions concisely. Say 'unknown' if the "
             "context does not say.\n{q}")
RT_COMPARE = (  # E9/E10 comparator, adapted: items are written as the correct information from R
    "Two sets of answers to the same questions follow. Set R was produced from an assistant's earlier "
    "notes plus the full transcript of the latest session; set S was produced from its new compressed "
    "notes alone. List (at most 8 short items) each item where S omits, contradicts, or changes "
    "something stated in R that would matter later. Write each item as the correct information "
    "according to R (for example 'commute is now 30 min, was 45 min').\n\n"
    "[Questions]\n{q}\n\n[Set R]\n{r}\n\n[Set S]\n{s}\n\n"
    "Return JSON: {{\"discrepancies\": [\"...\"]}}")

REPAIR = (  # E7 repair pass, adapted from operator constraints to user facts
    "Before you answer any question, do a fact check. Re-read your notes above carefully, including "
    "any earlier fact checks. Write a concise list of every fact about the user and its current "
    "value, and add any fact that earlier checks missed. Only list facts you can ground in your "
    "notes. Keep it under 150 words.")

LEDGER_PROMPT = """You maintain a ledger of what a user has told an assistant about themselves, people in their life, and their things, across many conversation sessions. The ledger records only what the user said. You get the current ledger as JSON and ONE new user message. Return the complete updated ledger as JSON with exactly the same keys.

How to update:
- "facts": concrete values the user stated (counts, amounts, times, dates, durations, frequencies, places, possessions, statuses, scores, records). Use one entry per attribute: {{"key": <short attribute name>, "current": <value>, "since": <turn id>, "previous": [{{"value": ..., "from": <turn id>, "to": <turn id>}}]}}. When the user gives a new value for an existing attribute, put the old current value at the front of "previous" and set the new current value. Never create a second entry for the same attribute.
- "plans": goals, plans, and upcoming events, as {{"text": ..., "since": <turn id>}}. When the user replaces a plan, move the old one to "superseded_plans" as {{"text": ..., "from": <turn id>, "to": <turn id>}}.
- "preferences": stated preferences, as {{"text": ..., "since": <turn id>}}.
- Ignore requests for help and chit-chat with no lasting fact. Never invent anything that is not in the user's messages. Leave every other entry unchanged.

Current ledger:
{ledger}

New user message (turn {turn}):
{message}

Return only the updated JSON ledger."""
EMPTY_LEDGER = {"facts": [], "plans": [], "superseded_plans": [], "preferences": []}

# ------------------------------------------------------------------ helpers


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return None


def canon_key(k):
    k = re.sub(r"\s+", " ", str(k).strip().lower())
    return re.sub(r"\s*\|\s*", " | ", k)


def vnorm(v):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(v).lower())).strip()


def render_kv(store):
    return "\n".join(f"- {k}: {v}" for k, v in store.items()) or "(empty)"


def build_versioned(facts_per_session):  # E14, unchanged
    hist = {}
    for i, facts in enumerate(facts_per_session):
        for k, v in facts:
            h = hist.setdefault(k, [])
            if h and vnorm(h[-1]["v"]) == vnorm(v):
                continue
            if h and h[-1]["s"] == i + 1:
                h[-1]["v"] = v
                continue
            h.append({"v": v, "s": i + 1})
    return hist


def render_versioned(hist, n_sessions):  # E14, unchanged
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


def render_registry(hist):
    """E18-style unlabeled registry: every value seen per fact, first-seen order, with the session
    where it was first seen. No 'current' or 'superseded' marking, neutral header."""
    lines = [f"- {k}: " + "; ".join(f"{x['v']} (session {x['s']})" for x in h) for k, h in hist.items()]
    return "\n\nFACT REGISTRY (values the user has mentioned for each fact):\n" + ("\n".join(lines) or "(empty)")


def newest(hist):
    return {k: h[-1]["v"] for k, h in hist.items()}


def snapshots(facts_per_session):
    """Newest-value-wins store after each session (E4 semantics)."""
    store, out = {}, []
    for facts in facts_per_session:
        for k, v in facts:
            store[k] = v
        out.append(dict(store))
    return out


# E4 comparators, unchanged
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
    if not value_matches(kv_value, restated):
        return False
    a = set(norm(kv_value))
    return not [w for w in norm(restated) if w not in a and w not in STOP]


# ------------------------------------------------------------------ session renderings


def labeled_session(turns, si, asst_cap=None):
    """Session with user turns labeled [S<i>.U<k>] (or [U<k>] when si is None)."""
    out, k = [], 0
    for role, content in turns:
        if role == "user":
            k += 1
            lab = f"[U{k}]" if si is None else f"[S{si}.U{k}]"
            out.append(f"{lab} user: {content}")
        else:
            c = content if asst_cap is None or len(content) <= asst_cap else content[:asst_cap] + " [...]"
            out.append(f"assistant: {c}")
    return "\n".join(out)


def user_turns(turns):
    return [c for r, c in turns if r == "user"]


def pin_block(t, selected=None, header=None):
    """Verbatim user turns in order. selected: per-session sets of 1-based user-turn numbers (None = all)."""
    lines = []
    for si, turns in enumerate(t["turns"], 1):
        for k, c in enumerate(user_turns(turns), 1):
            if selected is None or k in selected[si - 1]:
                lines.append(f"[Session {si}, turn U{k}] {c}")
    return f"\n\n{header}\n" + ("\n".join(lines) or "(none)")


PIN_ALL_HDR = ("USER TURNS (every message the user sent, verbatim and in order; a later turn supersedes "
               "an earlier one about the same fact):")
PIN_SEL_HDR = ("USER TURNS THAT STATED OR UPDATED A FACT (verbatim and in order; a later turn supersedes "
               "an earlier one about the same fact):")
MASK_HDR = "USER MESSAGES (verbatim and in order; the assistant's replies are omitted):"


def render_ledger(L):
    def prev(p):
        out = []
        for x in p or []:
            if isinstance(x, dict):
                out.append(f"{x.get('value')} ({x.get('from')} to {x.get('to')})")
            else:
                out.append(str(x))
        return ", ".join(out)
    lines = ["[User ledger. The harness maintains it from the user's own messages. It is current and "
             "authoritative: where the notes disagree, follow the ledger.]",
             "Facts (current value first; earlier values it replaced, newest first):"]
    for f in L.get("facts") or []:
        if isinstance(f, dict):
            s = f"- {f.get('key')}: {f.get('current')} (since {f.get('since')})"
            if f.get("previous"):
                s += "; previously " + prev(f["previous"])
            lines.append(s)
    lines.append("Plans and goals (current):")
    lines += [f"- {p.get('text')} (since {p.get('since')})" if isinstance(p, dict) else f"- {p}"
              for p in L.get("plans") or []]
    if L.get("superseded_plans"):
        lines.append("Superseded plans (no longer current):")
        lines += [f"- {p.get('text')} ({p.get('from')} to {p.get('to')})" if isinstance(p, dict) else f"- {p}"
                  for p in L["superseded_plans"]]
    lines.append("Preferences:")
    lines += [f"- {p.get('text')} (since {p.get('since')})" if isinstance(p, dict) else f"- {p}"
              for p in L.get("preferences") or []]
    return "\n\n" + "\n".join(lines)
