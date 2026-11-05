"""Build E8 transcripts deterministically (seeded): an agent partway through an ordered procedure.

Two task families:
  proc  - a model-generated ordered procedure (7 to 9 steps), data/procedures.json
  batch - processing a list of 24 items with random ids, one tool call per item

Three compaction timings (the compaction cut always keeps a verbatim tail of 2 turns):
  threshold  - step k completed, then 3 side-work filler turns, then compaction fires
               (the last step event is inside the summarized part)
  checkpoint - compaction fires right as step k closes with exit 0 (harness-verified
               subtask boundary); the step k event is the last verbatim turn
  midstep    - step k+1's command has been issued but its output has not been seen

Each case records the harness's own execution log (commands with exit codes), which a real
harness has. Truth labels (k, inflight) are kept separate from anything methods see.
Output: data/cases.json
"""
import json, random, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))
from common import sample_filler  # noqa: E402

SEED = 8008
N_BATCH_ITEMS = 24
BATCH_K = [5, 12, 19]
N_BATCH_INSTANCES = 10

BATCH_TEMPLATES = [
    dict(name="charge overdue invoices", unit="invoice", prefix="INV-", idempotent=False,
         cmd="billing-cli charge --invoice {id} --card-on-file --reason overdue-2026-09",
         out="Charged {amt} USD to card on file for {id}. Receipt RCPT-{r}.",
         verify="billing-cli invoice show {id} --field payment_status"),
    dict(name="send plan-renewal notices", unit="customer", prefix="CUS-", idempotent=False,
         cmd="notify-cli send --template renewal_notice_v3 --customer {id} --channel email",
         out="Queued email renewal_notice_v3 to customer {id} (message id msg_{r}).",
         verify="notify-cli history --customer {id} --template renewal_notice_v3"),
    dict(name="refund duplicate charges", unit="charge", prefix="ch_", idempotent=False,
         cmd="payments-cli refunds create --charge {id} --reason duplicate --full",
         out="Refund re_{r} created for charge {id}: {amt} USD, status pending.",
         verify="payments-cli refunds list --charge {id}"),
    dict(name="migrate tenant schemas to v14", unit="tenant", prefix="tnt_", idempotent=True,
         cmd="./bin/tenant-migrate --tenant {id} --to-version 14 --lock-timeout 30s",
         out="Tenant {id}: applied migrations 0131 to 0140, schema now at v14 ({r} ms).",
         verify="./bin/tenant-migrate --tenant {id} --status"),
    dict(name="re-encrypt document shards with the new KMS key", unit="shard", prefix="shard-", idempotent=True,
         cmd="docvault reencrypt --shard {id} --key alias/docs-2026q4 --concurrency 4",
         out="Shard {id}: re-encrypted {r} objects with alias/docs-2026q4, 0 failures.",
         verify="docvault shard-info {id} --show key-alias"),
    dict(name="issue loyalty credits", unit="account", prefix="acct_", idempotent=False,
         cmd="loyalty-cli credit --account {id} --points 500 --campaign fall-2026-apology",
         out="Credited 500 points to {id} (txn ltx_{r}); balance updated.",
         verify="loyalty-cli ledger --account {id} --campaign fall-2026-apology"),
]


def batch_procedure(t, rng, idx):
    ids = set()
    while len(ids) < N_BATCH_ITEMS:
        ids.add(t["prefix"] + str(rng.randrange(10000, 99999)))
    ids = list(ids)
    rng.shuffle(ids)
    steps = []
    for i in ids:
        r = rng.randrange(10000, 99999)
        amt = f"{rng.randrange(20, 900)}.{rng.randrange(0, 99):02d}"
        steps.append(dict(title=f"process {i}", command=t["cmd"].format(id=i),
                          output=t["out"].format(id=i, r=r, amt=amt), idempotent=t["idempotent"],
                          verify_command=t["verify"].format(id=i), item=i))
    return dict(id=f"B{idx:02d}", family="batch", name=t["name"],
                goal=f"For each of the {N_BATCH_ITEMS} {t['unit']}s listed, in the listed order, {t['name']} with one command per {t['unit']}.",
                steps=steps, item_ids=ids, cmd_template=t["cmd"], unit=t["unit"])


def task_turn(p):
    if p["family"] == "batch":
        return (f"Operator request: {p['goal']} Use `{p['cmd_template'].replace('{id}', '<ID>')}` for each one. "
                f"{p['unit'].capitalize()}s in order: " + ", ".join(p["item_ids"]) + ".")
    lines = "\n".join(f"{i}. {s['title']}: `{s['command']}`" for i, s in enumerate(p["steps"], 1))
    return f"Operator request: run the procedure '{p['name']}'. Goal: {p['goal']} Run these steps in order, one at a time:\n{lines}"


def step_turn(s):
    return f"Ran `{s['command']}` (exit 0):\n{s['output']}"


def build_case(p, k, timing, rng):
    """Return turns, ledger and truth. k = number of steps completed (1-based last done = k)."""
    turns = [task_turn(p)]
    ledger = []
    fill_every = 1 if p["family"] == "proc" else 3
    for i in range(k):
        if p["family"] == "proc" or i % fill_every == 0:
            for f in sample_filler(rng.choice([1, 1, 2]), rng):
                turns.append(f)
                ledger.append(_filler_ledger(f))
        turns.append(step_turn(p["steps"][i]))
        ledger.append(dict(cmd=p["steps"][i]["command"], exit=0))
    inflight = None
    if timing == "threshold":
        for f in sample_filler(3, rng):
            turns.append(f)
            ledger.append(_filler_ledger(f))
    elif timing == "midstep":
        s = p["steps"][k]
        turns.append(f"Issued `{s['command']}`. The command is still running; no output has been observed yet.")
        ledger.append(dict(cmd=s["command"], exit=None))
        inflight = k + 1
    ledger = [e for e in ledger if e]
    return dict(turns=turns, ledger=ledger, truth=dict(k=k, inflight=inflight, n_steps=len(p["steps"])))


def _filler_ledger(f):
    m = re.search(r"`([^`]{4,})`", f)
    if not m:
        return None
    return dict(cmd=m.group(1), exit=1 if re.search(r"\bfail|error|Traceback", f, re.I) else 0)


def main():
    rng = random.Random(SEED)
    procs = json.loads((HERE / "data" / "procedures.json").read_text())
    for p in procs:
        p["family"] = "proc"
    batches = [batch_procedure(BATCH_TEMPLATES[i % len(BATCH_TEMPLATES)], rng, i) for i in range(N_BATCH_INSTANCES)]
    cases = []
    for p in procs + batches:
        n = len(p["steps"])
        ks = BATCH_K if p["family"] == "batch" else sorted({2, n // 2, n - 2})
        for k, level in zip(ks, ["early", "mid", "late"]):
            for timing in ["threshold", "checkpoint", "midstep"]:
                crng = random.Random(f"{SEED}-{p['id']}-{k}-{timing}")
                c = build_case(p, k, timing, crng)
                c.update(case_id=f"{p['id']}-k{k}-{timing}", proc_id=p["id"], family=p["family"],
                         level=level, timing=timing)
                cases.append(c)
    (HERE / "data" / "batches.json").write_text(json.dumps(batches, indent=1))
    (HERE / "data" / "cases.json").write_text(json.dumps(cases, indent=1))
    print(len(cases), "cases;", sum(len(c["turns"]) for c in cases) / len(cases), "turns avg")


if __name__ == "__main__":
    main()
