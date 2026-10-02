"""E26: the combined compaction recipe, and every other compaction method, on process-graded tau-bench.

Adapted from ../e22_taubench_process/run.py. The agent loop, user simulator, tool stripping, compaction
schedule, E22 arms and cache scope are E22's, unchanged, so E22's arms replay from the copied cache and
new arms share each task's prefix with them until their contexts differ. Arm definitions are in
methods.py; the README maps each one to its source method.

  /private/tmp/taubench-venv/bin/python run.py --domain both --arms recipe minimal --trials 0-1
"""
import argparse, copy, json, math, re, sys, threading, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import llm  # noqa: E402
import methods as M  # noqa: E402

from tau_bench.envs.user import BaseUserSimulationEnv  # noqa: E402
from tau_bench.types import Action, RESPOND_ACTION_NAME  # noqa: E402

MODEL = "stealth/space-bunny-alpha"
USER_MODEL = None
SPLIT = "test"
SCOPE = "e22"  # cache scope prefix shared with E22; the pilot uses its own
LEDGER = {}    # domain -> rendered ledger text (built once per domain in main)

GENERIC_SYSTEM = {
    "retail": "You are a customer service representative for an online retail company. "
              "You are chatting with a customer, and you can call tools or respond to the user.",
    "airline": "You are a customer service representative for an airline. "
               "You are chatting with a customer, and you can call tools or respond to the user.",
}
POLICY_INTRO = ("[Operator message, not from the customer] Below is the policy you must follow "
                "for the whole conversation. The customer will write next.\n\n")
POLICY_ACK = "Understood. I will follow this policy for the whole conversation."
MARKER = "[Earlier messages were removed by the harness to save space.]"
MASK = "[Tool output removed by the harness to save space.]"
FIFO_CHARS = 1300  # about the 200-word summary budget

EXTRACT_PROMPT = (
    "[Harness check, not from the customer; do not call any tool for this message] "
    "List every policy rule you must follow in this conversation, as precisely and completely as "
    "you can, one rule per line. Only list rules; do not address the customer.")

COMPARE_PROMPT = """You are checking whether a customer-service agent still remembers the operator rules that matter for its current conversation.

(A) THE AGENT'S CURRENT CONTEXT (after its history was summarized):
{ctx}

(B) RULES THE AGENT WROTE DOWN FROM MEMORY:
{lst}

(C) REFERENCE RULES:
{rules}

For each reference rule decide two things.
1. relevant: could this rule govern something the agent does in THIS conversation, given what the customer has asked for so far and what is still pending? Rules about kinds of actions that have not come up (for example cancellation rules when the customer only wants an exchange, or booking rules when the customer only wants to cancel) are NOT relevant. Rules about general conduct that apply to any action (authentication, explicit confirmation before database changes, one user per conversation, not making things up, one tool call at a time, when to transfer) ARE relevant.
2. stated: does list (B) state this rule's essential requirement (same meaning, possibly different wording; partial coverage that drops the key condition does not count)?

Answer with JSON only, one entry per reference rule, in order:
{{"rules": [{{"id": 0, "relevant": true, "stated": false}}, ...]}}"""

USER_SYSTEM = """You are a user interacting with an agent.{instruction_display}
Rules:
- Just generate one line at a time to simulate the user's message.
- Do not give away all the instruction at once. Only provide the information that is necessary for the current step.
- Do not hallucinate information that is not provided in the instruction. For example, if the agent asks for the order id but it is not mentioned in the instruction, do not make up an order id, just say you do not remember or have it.
- If the instruction goal is satisified, generate '###STOP###' as a standalone message without anything else to end the conversation.
- Do not repeat the exact instruction in the conversation. Instead, use your own words to convey the same information.
- Try to make the conversation as natural as possible, and stick to the personalities in the instruction.{extra}"""
USER_EXTRA = ("\n- Facts stated in the instruction (your name, zip code, email, order ids, and so on) are "
              "things you know; share them when the agent asks for them.")

STRIP_PATTERNS = {
    "retail": [
        r"If the order is already processed or delivered, it cannot be cancelled\.",
        r"The agent needs to explain[^.]*\.(?: [^.]*to proceed\.)?",
        r"For a delivered order, return or exchange can be only done once by the agent\.",
        r"For a pending order, this function can only be called once\.",
        r"Only transfer if[^.]*\.",
        r"By default, find user id by email[^.]*\.",
        r"If the user confirms, ",
        r", which should be either 'no longer needed' or 'ordered by mistake'",
        r"Be careful the product id is different from the item id\.",
    ],
    "airline": [r"Only transfer if[^.]*\.", r"Be careful!"],
}
WRITE_TOOLS = {
    "retail": {"cancel_pending_order", "modify_pending_order_items", "modify_pending_order_address",
               "modify_pending_order_payment", "modify_user_address", "exchange_delivered_order_items",
               "return_delivered_order_items"},
    "airline": {"book_reservation", "cancel_reservation", "update_reservation_flights",
                "update_reservation_baggages", "update_reservation_passengers", "send_certificate"},
}


def strip_tool_policy(tools, domain):
    tools = copy.deepcopy(tools)
    removed = []
    for t in tools:
        f = t["function"]
        for pat in STRIP_PATTERNS[domain]:
            new = re.sub(pat, "", f["description"]).strip()
            if new != f["description"]:
                removed.append((f["name"], pat))
            new = re.sub(r"\s{2,}", " ", new)
            f["description"] = re.sub(r"\. ([a-z])", lambda m: ". " + m.group(1).upper(), new)
            for pname, prop in f["parameters"]["properties"].items():
                if "description" in prop:
                    new = re.sub(pat, "", prop["description"]).strip()
                    if new != prop["description"]:
                        removed.append((f["name"] + "." + pname, pat))
                    prop["description"] = new
    return tools, removed


class Counter:
    def __init__(self):
        self.calls, self.tok_in, self.tok_out, self.api = {}, {}, {}, 0

    def add(self, kind, usage, cached):
        self.calls[kind] = self.calls.get(kind, 0) + 1
        self.tok_in[kind] = self.tok_in.get(kind, 0) + usage.get("in", 0)
        self.tok_out[kind] = self.tok_out.get(kind, 0) + usage.get("out", 0)
        self.api += 0 if cached else 1


class ORUser(BaseUserSimulationEnv):
    def __init__(self, runner):
        self.r, self.messages = runner, []

    def _gen(self):
        msg = self.r.call(self.messages, "user", max_tokens=400, temperature=1.0, model=USER_MODEL or MODEL)
        txt = msg["content"]
        self.messages.append({"role": "assistant", "content": txt})
        return txt

    def reset(self, instruction=None):
        disp = ("\n\nInstruction: " + instruction + "\n") if instruction is not None else ""
        self.messages = [{"role": "system", "content": USER_SYSTEM.format(instruction_display=disp, extra=USER_EXTRA)},
                         {"role": "user", "content": "Hi! How can I help you today?"}]
        return self._gen()

    def step(self, content):
        self.messages.append({"role": "user", "content": content})
        return self._gen()

    def get_total_cost(self):
        return 0.0


def make_env(domain, split=None):
    if domain == "retail":
        from tau_bench.envs.retail.env import MockRetailDomainEnv as E
    else:
        from tau_bench.envs.airline.env import MockAirlineDomainEnv as E
    return E(user_strategy="human", task_split=split or SPLIT, task_index=0)


def clean(msg):
    m = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        tc = msg["tool_calls"][0]
        m["tool_calls"] = [{"id": tc.get("id") or "call_0", "type": "function",
                            "function": {"name": tc["function"]["name"],
                                         "arguments": tc["function"].get("arguments") or "{}"}}]
    return m


def strip(m):
    return {k: v for k, v in m.items() if not k.startswith("_")}


def snapshot(domain, data, name, kw):
    """E22's pre-write database snapshot (unchanged)."""
    pre = {}
    try:
        if domain == "retail":
            oid = kw.get("order_id")
            if oid and oid in data["orders"]:
                o = data["orders"][oid]
                pre["order"] = {"status": o["status"], "user_id": o["user_id"],
                                "payment_history": o.get("payment_history")}
        else:
            rid = kw.get("reservation_id")
            res = data["reservations"].get(rid) if rid else None
            if res:
                pre["reservation"] = copy.deepcopy(res)
                pre["flight_status"] = [data["flights"].get(f["flight_number"], {}).get("dates", {})
                                        .get(f["date"], {}).get("status") for f in res["flights"]]
            uid = kw.get("user_id") or (res or {}).get("user_id")
            if uid and uid in data["users"]:
                u = data["users"][uid]
                pre["membership"] = u.get("membership")
                if name == "send_certificate":
                    pre["user_reservations"] = [
                        {"id": r, "cabin": data["reservations"][r]["cabin"],
                         "insurance": data["reservations"][r]["insurance"]}
                        for r in u.get("reservations", []) if r in data["reservations"]]
            if name in ("update_reservation_flights", "book_reservation"):
                pre["new_flights"] = [
                    {"flight_number": f.get("flight_number"), "date": f.get("date"),
                     "origin": data["flights"].get(f.get("flight_number"), {}).get("origin"),
                     "destination": data["flights"].get(f.get("flight_number"), {}).get("destination")}
                    for f in (kw.get("flights") or []) if isinstance(f, dict)]
    except Exception as e:
        pre["error"] = repr(e)[:200]
    return pre


def tail_cut(hist, k):
    cut = max(0, len(hist) - k)
    while cut < len(hist) and hist[cut]["role"] == "tool":
        cut += 1
    return cut


class Runner:
    def __init__(self, arm, domain, task_index, trial, cfg):
        self.arm, self.domain, self.ti, self.trial, self.cfg = arm, domain, task_index, trial, cfg
        self.A = M.ARMS[arm]
        self.scope = f"{SCOPE}:{domain}:{task_index}:{trial}"
        self.tag = f"e26:{domain}:{arm}:{task_index}:{trial}"
        self.counter = Counter()
        self.rules = json.loads((HERE / f"rules_{domain}.json").read_text())
        self.events, self.compactions, self.summary = [], [], ""

    def call(self, messages, kind, model=None, **kw):
        msg, usage, cached = llm.chat(messages, scope=self.scope, model=model or MODEL,
                                      tag=f"{self.tag}:{kind}", **kw)
        self.counter.add(kind, usage, cached)
        return msg

    # ---------------------------------------------------------- timing
    def due_now(self, msgs, since):
        due = self.cfg.first if not self.compactions else self.cfg.every
        if self.A.get("timing") == "checkpoint":
            soft, hard = math.ceil(0.6 * due), math.ceil(1.4 * due)
            # fire at a turn boundary (the customer has just written) once past the soft threshold
            return since >= hard or (since >= soft and msgs[-1]["role"] == "user")
        return since >= due

    # ---------------------------------------------------------- compaction
    def summarize(self, old, prior, words, extra=""):
        p = self.A.get("prompt", "plain")
        rend = M.render_labeled if p in M.LABELED else M.render
        pre = f"[Summary of earlier conversation]\n{prior}\n\n" if prior else ""
        prompt = M.PROMPTS[p].format(words=words) + extra + "\n\n" + pre + "[Log]\n" + rend(old)
        return self.call([{"role": "user", "content": prompt}], "compact" if not extra else "recompact",
                         max_tokens=max(2000, words * 6), temperature=0.3)["content"].strip()

    def compact(self, msgs):
        mode, k = self.A.get("mode"), self.A.get("tail", self.cfg.tail)
        if mode == "mask":
            cut = len(msgs) - k
            new = [msgs[0]] + [dict(m, content=MASK) if (m["role"] == "tool" and i < cut and m["content"] != MASK)
                               else m for i, m in enumerate(msgs[1:], 1)]
            self.compactions.append({"agent_step": self.step_no, "masked": sum(
                1 for a, b in zip(msgs, new) if a is not b)})
            self.events.append(["compact", self.step_no, 0, k])
            return new
        if mode == "headtail":
            hist = self.raw[1:]
            cut = max(3, tail_cut(hist, k))
            if cut <= 3:
                return msgs
            new = [msgs[0]] + hist[:3] + [{"role": "user", "content": MARKER, "_marker": True}] + hist[cut:]
            self.compactions.append({"agent_step": self.step_no, "dropped": cut - 3})
            self.events.append(["compact", self.step_no, cut - 3, len(hist) - cut])
            return new
        sys_msg, hist = msgs[0], msgs[1:]
        if hist and (hist[0].get("_summary") or hist[0].get("_marker")):
            hist = hist[1:]
        if self.A.get("source"):
            hist = self.raw[1:]
        cut = tail_cut(hist, k)
        old, tail = hist[:cut], hist[cut:]
        if not old:
            return msgs
        if mode == "fifo":
            keep, used = [], 0
            for m in reversed(old):
                c = len(m.get("content") or "") + sum(len(t["function"]["arguments"]) for t in m.get("tool_calls") or [])
                if used + c > FIFO_CHARS:
                    break
                keep.insert(0, m)
                used += c
            while keep and keep[0]["role"] == "tool":
                keep.pop(0)
            self.compactions.append({"agent_step": self.step_no, "kept_extra": len(keep)})
            self.events.append(["compact", self.step_no, len(old) - len(keep), len(tail) + len(keep)])
            return [sys_msg, {"role": "user", "content": MARKER, "_marker": True}] + keep + tail
        words = self.cfg.words
        prior = "" if self.A.get("source") else self.summary
        summ = self.summarize(old, prior, words)
        rec = {"agent_step": self.step_no, "summary": summ}
        if self.A.get("check") == "roundtrip":
            draft_ctx = [{"role": "user", "content": "[Summary of the conversation so far, written by the harness]\n"
                          + summ, "_summary": True}] + tail
            sig = self.roundtrip(draft_ctx)
            rec["rt"] = sig
            if sig["score"] >= M.RT_THRESHOLD:
                must = [f["note"] for f in sig["flagged"]] or ["(the check flagged the draft but listed no specific items)"]
                rec["draft"] = summ
                summ = self.summarize(old, prior, words * 2, extra=M.RT_MUST + "\n".join(f"- {m}" for m in must))
                rec["summary"] = summ
        self.summary = summ
        body = "[Summary of the conversation so far, written by the harness]\n" + summ
        pin = self.A.get("pin")
        if pin == "wiki":
            body += "\n\n[Operator policy, re-attached by the harness]\n" + self.wiki
        elif pin == "rules":
            body += "\n\n[Operator policy rules, re-attached by the harness]\n" + "\n".join(f"- {r}" for r in self.rules)
        elif pin == "ledger":
            body += "\n\n" + LEDGER[self.domain]
        summary_msg = {"role": "user", "content": body, "_summary": True}
        new = [sys_msg, summary_msg] + tail
        chk = self.A.get("check")
        if chk in ("watch", "self"):
            res = self.watch_check(new) if chk == "watch" else self.self_check(new)
            rec.update(res)
            if res["patched"]:
                patch = "\n\n[Operator policy reminder, re-attached by the harness]\n" + "\n".join(
                    f"- {self.rules[i]}" for i in res["patched"])
                summary_msg["content"] += patch
                self.summary += patch
        elif chk == "repair":
            passes = self.repair(new)
            rec["repair"] = passes
            summary_msg["content"] += "\n\n" + "\n\n".join(
                f"[Your own constraint check, pass {i}]\n{p}" for i, p in enumerate(passes, 1))
        if self.A.get("progress"):
            blk = M.progress_block(self.events, WRITE_TOOLS[self.domain], self.domain)
            summary_msg["content"] += "\n\n" + blk
            rec["progress"] = blk
        self.compactions.append(rec)
        self.events.append(["compact", self.step_no, len(old), len(tail)])
        return new

    def watch_check(self, ctx):
        """E22's fixed Watchpoint (unchanged)."""
        probe = [strip(m) for m in ctx] + [{"role": "user", "content": EXTRACT_PROMPT}]
        listing = None
        msg = self.call(probe, "extract", max_tokens=1200, temperature=0.0, tools=self.tools)
        if msg.get("content") and not msg.get("tool_calls"):
            listing = msg["content"]
        if listing is None:
            listing = self.call([{"role": "user", "content": M.render(ctx[1:]) + "\n\n" + EXTRACT_PROMPT}],
                                "extract", max_tokens=1200, temperature=0.0)["content"]
        rules_txt = "\n".join(f"{i}. {r}" for i, r in enumerate(self.rules))
        prompt = COMPARE_PROMPT.format(ctx=M.render(ctx[1:]), lst=listing, rules=rules_txt)
        parsed = None
        for attempt in range(2):
            p = prompt if attempt == 0 else prompt + "\n\nReturn valid JSON only."
            out = self.call([{"role": "user", "content": p}], "compare", max_tokens=3000, temperature=0.0)
            parsed = parse_judgment(out["content"], len(self.rules))
            if parsed is not None:
                break
        if parsed is None:
            relevant, stated, ok = list(range(len(self.rules))), [], False
        else:
            relevant = [i for i, (rel, st) in enumerate(parsed) if rel]
            stated = [i for i, (rel, st) in enumerate(parsed) if st]
            ok = True
        patched = [i for i in relevant if i not in stated]
        return {"extraction": listing, "relevant": relevant, "stated": stated, "patched": patched, "judge_ok": ok}

    def self_check(self, ctx):
        """E1's naive self-judgment watchpoint: one YES/NO call per reference rule; NO -> re-attach."""
        rc = M.render(ctx[1:])
        answers = []
        for r in self.rules:
            out = self.call([{"role": "system", "content": GENERIC_SYSTEM[self.domain]},
                             {"role": "user", "content": M.SELF_PROMPT.format(ctx=rc, rule=r)}],
                            "selfcheck", max_tokens=300, temperature=0.0)["content"]
            answers.append(out.strip().strip("*").strip().upper().startswith("Y"))
        return {"covered": answers, "patched": [i for i, a in enumerate(answers) if not a]}

    def repair(self, ctx):
        """E7 repair passes, k = 2, chained; each pass sees the context and the earlier passes."""
        passes = []
        base = M.render(ctx[1:])
        for _ in range(2):
            prior = ("\n\n" + "\n\n".join(f"[Your own constraint check, pass {i}]\n{p}"
                                          for i, p in enumerate(passes, 1))) if passes else ""
            out = self.call([{"role": "system", "content": GENERIC_SYSTEM[self.domain]},
                             {"role": "user", "content": f"{base}{prior}\n\n{M.REPAIR_PROMPT}"}],
                            "repair", max_tokens=1200, temperature=0.7)["content"].strip()
            passes.append(out)
        return passes

    def jcall(self, prompt, kind, max_tokens):
        for attempt in range(2):
            p = prompt if attempt == 0 else prompt + "\n\nReturn valid JSON only."
            d = M.parse_json(self.call([{"role": "user", "content": p}], kind, max_tokens=max_tokens,
                                       temperature=0.0)["content"])
            if isinstance(d, dict):
                return d
        return {}

    def roundtrip(self, draft_ctx):
        """E10 generic round-trip signal: 5 questions from the full raw history, answered from both sides."""
        full = M.render(self.raw[1:])
        summ = M.render(draft_ctx)
        q = self.jcall(M.RT_QGEN.format(ctx=full), "rt_qgen", 1500)
        qs = [str(x) for x in q.get("questions", [])][:5] or ["What should the agent do next?"]
        listing = "\n".join(f"{i + 1}. {x}" for i, x in enumerate(qs))

        def answer(ctx, kind):
            a = [str(x) for x in self.jcall(M.RT_ANS.format(ctx=ctx, listing=listing), kind, 1500).get("answers", [])]
            return (a + ["unknown"] * len(qs))[:len(qs)]
        af, asum = answer(full, "rt_ans_full"), answer(summ, "rt_ans_summ")
        block = "\n".join(f"Q{i + 1}. {qs[i]}\n  R: {af[i]}\n  S: {asum[i]}" for i in range(len(qs)))
        res = self.jcall(M.RT_CMP.format(block=block), "rt_cmp", 1500)
        flagged = []
        for it in [x for x in res.get("items", []) if isinstance(x, dict)]:
            try:
                qi = int(it.get("q", 0)) - 1
            except (TypeError, ValueError):
                continue
            if it.get("discrepant") and 0 <= qi < len(qs):
                flagged.append(dict(q=qi, note=str(it.get("note", ""))))
        try:
            score = float(res.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        return dict(questions=qs, ans_full=af, ans_summ=asum, flagged=flagged, score=score)

    # ---------------------------------------------------------- main loop
    def run(self):
        env = make_env(self.domain)
        env.user = ORUser(self)
        self.wiki = env.wiki
        self.tools, _ = strip_tool_policy(env.tools_info, self.domain)
        writes = WRITE_TOOLS[self.domain]
        obs = env.reset(task_index=self.ti).observation
        self.events.append(["user", obs])
        if self.A.get("policy", True) is False:
            msgs = [{"role": "system", "content": GENERIC_SYSTEM[self.domain]}]
        else:
            msgs = [{"role": "system", "content": GENERIC_SYSTEM[self.domain]},
                    {"role": "user", "content": POLICY_INTRO + env.wiki, "_policy": True},
                    {"role": "assistant", "content": POLICY_ACK}]
        msgs.append({"role": "user", "content": obs})
        self.raw = list(msgs)
        reward, done, info = 0.0, False, None
        self.step_no, since = 0, 0
        compacting = self.A.get("compact", True) is not False
        for _ in range(self.cfg.max_steps):
            if compacting and self.due_now(msgs, since):
                msgs = self.compact(msgs)
                since = 0
            raw = self.call([strip(m) for m in msgs], "agent", max_tokens=2000, temperature=0.0, tools=self.tools)
            self.step_no += 1
            since += 1
            m = clean(raw)
            if m.get("tool_calls"):
                f = m["tool_calls"][0]["function"]
                try:
                    kwargs = json.loads(f["arguments"]) if f["arguments"] else {}
                    if not isinstance(kwargs, dict):
                        raise ValueError("arguments not an object")
                except Exception as e:
                    add = [m, {"role": "tool", "tool_call_id": m["tool_calls"][0]["id"],
                               "content": f"Error: could not parse arguments: {e}"}]
                    msgs += add
                    self.raw += add
                    self.events.append(["badargs", f["name"], f["arguments"][:500]])
                    continue
                pre = snapshot(self.domain, env.data, f["name"], kwargs) if f["name"] in writes else None
                r = env.step(Action(name=f["name"], kwargs=kwargs))
                add = [m, {"role": "tool", "tool_call_id": m["tool_calls"][0]["id"], "content": r.observation}]
                ev = ["tool", f["name"], kwargs, r.observation[:1500], self.step_no]
                if pre is not None:
                    ev.append(pre)
                self.events.append(ev)
            else:
                r = env.step(Action(name=RESPOND_ACTION_NAME, kwargs={"content": m["content"]}))
                add = [m, {"role": "user", "content": r.observation}]
                self.events.append(["agent", m["content"], self.step_no])
                self.events.append(["user", r.observation])
            msgs += add
            self.raw += add
            if r.done:
                done, reward = True, r.reward
                info = r.info.reward_info.model_dump() if r.info.reward_info else None
                break
        if not done:
            info = env.calculate_reward().model_dump()
            reward = 0.0
        if info and "actions" in info:
            info.pop("actions")
        c = self.counter
        return {"domain": self.domain, "arm": self.arm, "task": self.ti, "trial": self.trial,
                "reward": reward, "done": done, "reward_info": info, "agent_steps": self.step_no,
                "calls": c.calls, "tok_in": c.tok_in, "tok_out": c.tok_out, "api_calls": c.api,
                "n_compactions": len(self.compactions), "compactions": self.compactions,
                "events": self.events, "model": MODEL, "user_model": USER_MODEL or MODEL,
                "split": SPLIT, "cfg": {k: v for k, v in vars(self.cfg).items()}}


def parse_judgment(text, n):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        items = json.loads(m.group(0))["rules"]
        out = [None] * n
        for k, it in enumerate(items):
            i = int(it.get("id", k))
            if 0 <= i < n:
                out[i] = (bool(it.get("relevant")), bool(it.get("stated")))
        return None if any(x is None for x in out) else out
    except Exception:
        return None


def build_ledger(domain):
    """E17 ledger update applied to the one operator message (the policy). Built once per domain."""
    path = HERE / f"results/ledger_{domain}{'' if SCOPE == 'e22' else '_' + SCOPE}.json"
    if path.exists():
        d = json.loads(path.read_text())
        return d["rendered"]
    wiki = make_env(domain).wiki
    prompt = M.LEDGER_PROMPT.format(ledger=json.dumps(M.EMPTY_LEDGER, indent=1), turn=1, message=wiki)
    L = None
    for attempt in range(3):
        p = prompt if attempt == 0 else prompt + "\n\nReturn valid JSON only."
        msg, usage, cached = llm.chat([{"role": "user", "content": p}], scope=f"e26ledger:{domain}", model=MODEL,
                                      max_tokens=12000, temperature=0.0, tag=f"e26:{domain}:ledger")
        L = M.parse_json(msg["content"])
        if isinstance(L, dict) and L.get("active_rules"):
            break
    if not (isinstance(L, dict) and L.get("active_rules")):
        raise RuntimeError("ledger build failed")
    rendered = M.render_ledger(L)
    path.write_text(json.dumps({"ledger": L, "rendered": rendered, "usage": usage}, indent=1))
    return rendered


def parse_tasks(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main():
    global MODEL, USER_MODEL, USER_EXTRA, SPLIT, SCOPE
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=M.RUN_ORDER)
    ap.add_argument("--domain", default="both", choices=["retail", "airline", "both"])
    ap.add_argument("--tasks_retail", default="0-114")
    ap.add_argument("--tasks_airline", default="0-49")
    ap.add_argument("--trials", default="0-1")
    ap.add_argument("--first", type=int, default=4)
    ap.add_argument("--every", type=int, default=6)
    ap.add_argument("--tail", type=int, default=4)
    ap.add_argument("--words", type=int, default=200)
    ap.add_argument("--max_steps", type=int, default=30)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out_suffix", default="", help="results/<domain><suffix>.jsonl")
    ap.add_argument("--split", default="test")
    ap.add_argument("--scope", default="e22", help="cache scope prefix; keep e22 to reuse E22's replies")
    ap.add_argument("--model", default="stealth/space-bunny-alpha")
    ap.add_argument("--user_model", default=None)
    ap.add_argument("--plain_user", action="store_true")
    cfg = ap.parse_args()
    MODEL, USER_MODEL, SPLIT, SCOPE = cfg.model, cfg.user_model, cfg.split, cfg.scope
    assert ":free" not in MODEL and ":free" not in (USER_MODEL or "")
    if MODEL != "stealth/space-bunny-alpha" and SCOPE == "e22":
        pass  # the cache key includes the model, so a second backbone never reuses these replies
    if cfg.plain_user:
        USER_EXTRA = ""
    unknown = [a for a in cfg.arms if a not in M.ARMS]
    assert not unknown, unknown
    doms = ["retail", "airline"] if cfg.domain == "both" else [cfg.domain]
    for d in doms:
        if "ledger" in cfg.arms:
            LEDGER[d] = build_ledger(d)
    outs, done = {}, set()
    for d in doms:
        outs[d] = HERE / f"results/{d}{cfg.out_suffix}.jsonl"
        if outs[d].exists():
            for line in outs[d].read_text().splitlines():
                r = json.loads(line)
                done.add((d, r["arm"], r["task"], r["trial"]))
    groups = []
    tasks = {"retail": parse_tasks(cfg.tasks_retail), "airline": parse_tasks(cfg.tasks_airline)}
    for tr in parse_tasks(cfg.trials):
        per = {d: [t for t in tasks[d]] for d in doms}
        # interleave domains so both progress together
        order = []
        for i in range(max(len(v) for v in per.values())):
            for d in doms:
                if i < len(per[d]):
                    order.append((d, per[d][i]))
        for d, t in order:
            arms = [a for a in M.RUN_ORDER if a in cfg.arms and (d, a, t, tr) not in done]
            if arms:
                groups.append((d, t, tr, arms))
    print(f"{sum(len(g[3]) for g in groups)} runs in {len(groups)} groups ({len(done)} done)", flush=True)
    lock, t0, n = threading.Lock(), time.time(), [0]

    def work(group):
        d, t, tr, arms = group
        for a in arms:
            try:
                row = Runner(a, d, t, tr, cfg).run()
            except Exception:
                tb = traceback.format_exc()[-800:]
                print("FAILED", (d, a, t, tr), tb, flush=True)
                with lock, open(outs[d].with_name(outs[d].stem + "_errored.jsonl"), "a") as fh:
                    fh.write(json.dumps({"arm": a, "task": t, "trial": tr, "error": tb}) + "\n")
                continue
            with lock:
                with open(outs[d], "a") as fh:
                    fh.write(json.dumps(row) + "\n")
                n[0] += 1
                print(f"[{n[0]} {time.time()-t0:.0f}s] {(d, a, t, tr)} reward={row['reward']} "
                      f"steps={row['agent_steps']} comp={row['n_compactions']} api={row['api_calls']}", flush=True)

    with ThreadPoolExecutor(cfg.workers) as ex:
        list(as_completed([ex.submit(work, g) for g in groups]))


if __name__ == "__main__":
    main()
