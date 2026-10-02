"""Heuristic audit of the simulated user, plus a fixed random sample for manual reading.

Flags per run:
  withholds_known_fact  the user says they do not remember/have their email or zip, although the
                        instruction states it and does not say they forgot it
  leaks_instruction     a user turn copies 12+ consecutive words of the instruction
  no_stop               the conversation ended without ###STOP### (max steps or transfer)
Usage: python3 audit_user.py results/main.jsonl [--sample N]
"""
import json, random, re, sys
sys.path.insert(0, "/private/tmp/tau-bench")


def instr(domain, i):
    if domain == "retail":
        from tau_bench.envs.retail.tasks_test import TASKS_TEST as T
    else:
        from tau_bench.envs.airline.tasks_test import TASKS as T
    return T[i].instruction


DENY = re.compile(r"(don.?t|do not|can.?t|cannot) (remember|recall|have|know)([^.]{0,40})", re.I)


def denies(u, ins):
    """True if the user denies knowing a fact (zip or email) that the instruction states."""
    for m in DENY.finditer(u):
        span = m.group(0).lower()
        if "zip" in span and re.search(r"\b\d{5}\b", ins):
            return True
        if ("email" in span or "e-mail" in span) and "@" in ins:
            return True
    return False


WRITES = {"cancel_pending_order", "modify_pending_order_items", "modify_pending_order_address",
          "modify_pending_order_payment", "modify_user_address", "exchange_delivered_order_items",
          "return_delivered_order_items", "book_reservation", "cancel_reservation",
          "update_reservation_flights", "update_reservation_baggages", "update_reservation_passengers",
          "send_certificate"}


def gold_writes(r):
    if r["domain"] == "retail":
        from tau_bench.envs.retail.tasks_test import TASKS_TEST as T
    else:
        from tau_bench.envs.airline.tasks_test import TASKS as T
    return any(a.name in WRITES for a in T[r["task"]].actions)


def flags(r):
    ins = instr(r["domain"], r["task"])
    users = [e[1] for e in r["events"] if e[0] == "user"]
    f = {}
    forgot = re.search(r"forg|not remember|don't remember|do not remember", ins, re.I)
    if not forgot and any(denies(u, ins) for u in users):
        f["withholds_known_fact"] = 1
    words = ins.lower().split()
    grams = {" ".join(words[i:i + 12]) for i in range(len(words) - 11)}
    if any(g in " ".join(u.lower().split()) for u in users for g in grams):
        f["leaks_instruction"] = 1
    transferred = any(e[0] == "tool" and e[1] == "transfer_to_human_agents" for e in r["events"])
    if not any("###STOP###" in u for u in users):
        f["no_stop_after_transfer" if transferred else "no_stop_no_transfer"] = 1
    # user ends the conversation before any database write although the task's gold actions write
    if any("###STOP###" in u for u in users) and not any(
            e[0] == "tool" and e[1] in WRITES for e in r["events"]) and gold_writes(r):
        f["stopped_without_any_write"] = 1
    return f


def main():
    path = sys.argv[1]
    n = int(sys.argv[sys.argv.index("--sample") + 1]) if "--sample" in sys.argv else 0
    rows = [json.loads(l) for l in open(path) if l.strip()]
    agg = {}
    for r in rows:
        for k in flags(r):
            agg[k] = agg.get(k, 0) + 1
    print(f"runs={len(rows)}", {k: f"{v} ({v/len(rows):.3f})" for k, v in sorted(agg.items())})
    rng = random.Random(0)
    for r in rng.sample(rows, n):
        print(f"\n=== {r['arm']} task {r['task']} reward {r['reward']} flags {flags(r)}")
        print("INSTRUCTION:", instr(r["domain"], r["task"]))
        for e in r["events"]:
            if e[0] in ("user", "agent"):
                print(f"  {e[0]}: {e[1][:200]}")
            elif e[0] == "tool":
                print(f"  tool: {e[1]} {json.dumps(e[2])[:120]}")


if __name__ == "__main__":
    main()
