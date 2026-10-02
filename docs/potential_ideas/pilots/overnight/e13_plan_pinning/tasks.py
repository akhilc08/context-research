"""E13 task definitions shared by gen_filler.py, build.py, run.py, grade.py and analyze.py.

Procedures (P00 to P19) are copied unchanged from E8 (data/procedures.json).
Batch tasks use 8 hand-written templates; 6 of the 8 are non-idempotent.
Each batch template has an action token (identifies a run of the action) and a verify token
(identifies a read-only status check), used by the deterministic id parser in grade.py.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
N_BATCH_ITEMS = 40

BATCH_TEMPLATES = [
    dict(key="charge", name="charge overdue invoices", unit="invoice", prefix="INV-", idempotent=False,
         cmd="billing-cli charge --invoice {id} --card-on-file --reason overdue-2026-09",
         out="Charged {amt} USD to card on file for {id}. Receipt RCPT-{r}.",
         fail="Error: payment gateway timeout after 30s (upstream 504). No charge was created for {id}.",
         verify="billing-cli invoice show {id} --field payment_status",
         action_token="charge --invoice", verify_token="invoice show"),
    dict(key="notify", name="send plan-renewal notices", unit="customer", prefix="CUS-", idempotent=False,
         cmd="notify-cli send --template renewal_notice_v3 --customer {id} --channel email",
         out="Queued email renewal_notice_v3 to customer {id} (message id msg_{r}).",
         fail="Error: SMTP relay returned 451 (temporary local problem). Nothing was queued for {id}.",
         verify="notify-cli history --customer {id} --template renewal_notice_v3",
         action_token="send --template", verify_token="history"),
    dict(key="refund", name="refund duplicate charges", unit="charge", prefix="ch_", idempotent=False,
         cmd="payments-cli refunds create --charge {id} --reason duplicate --full",
         out="Refund re_{r} created for charge {id}: {amt} USD, status pending.",
         fail="Error: rate limited by processor (429, retry after 20s). No refund was created for {id}.",
         verify="payments-cli refunds list --charge {id}",
         action_token="refunds create", verify_token="refunds list"),
    dict(key="migrate", name="migrate tenant schemas to v14", unit="tenant", prefix="tnt_", idempotent=True,
         cmd="./bin/tenant-migrate --tenant {id} --to-version 14 --lock-timeout 30s",
         out="Tenant {id}: applied migrations 0131 to 0140, schema now at v14 ({r} ms).",
         fail="Error: could not obtain lock on schema {id} within 30s; transaction rolled back, schema unchanged.",
         verify="./bin/tenant-migrate --tenant {id} --status",
         action_token="--to-version", verify_token="--status"),
    dict(key="reencrypt", name="re-encrypt document shards with the new KMS key", unit="shard", prefix="shard-", idempotent=True,
         cmd="docvault reencrypt --shard {id} --key alias/docs-2026q4 --concurrency 4",
         out="Shard {id}: re-encrypted {r} objects with alias/docs-2026q4, 0 failures.",
         fail="Error: KMS throttled GenerateDataKey (ThrottlingException); shard {id} left on previous key, 0 objects changed.",
         verify="docvault shard-info {id} --show key-alias",
         action_token="reencrypt", verify_token="shard-info"),
    dict(key="credit", name="issue loyalty credits", unit="account", prefix="acct_", idempotent=False,
         cmd="loyalty-cli credit --account {id} --points 500 --campaign fall-2026-apology",
         out="Credited 500 points to {id} (txn ltx_{r}); balance updated.",
         fail="Error: loyalty ledger service unavailable (503). No points were credited to {id}.",
         verify="loyalty-cli ledger --account {id} --campaign fall-2026-apology",
         action_token="credit --account", verify_token="ledger --account"),
    dict(key="payout", name="send vendor payouts", unit="vendor", prefix="VEN-", idempotent=False,
         cmd="payouts-cli transfer --vendor {id} --batch 2026-09-close --method ach",
         out="ACH transfer tr_{r} of {amt} USD initiated to vendor {id}.",
         fail="Error: bank API returned 502 Bad Gateway. No transfer was initiated for {id}.",
         verify="payouts-cli transfers list --vendor {id} --batch 2026-09-close",
         action_token="transfer --vendor", verify_token="transfers list"),
    dict(key="giftcard", name="issue replacement gift cards", unit="order", prefix="ORD-", idempotent=False,
         cmd="giftcard-cli issue --order {id} --value 25 --reason shipping-delay",
         out="Issued gift card GC-{r} (25 USD) for order {id}; emailed to purchaser.",
         fail="Error: inventory service timeout. No gift card was issued for order {id}.",
         verify="giftcard-cli lookup --order {id} --reason shipping-delay",
         action_token="issue --order", verify_token="lookup --order"),
]
TEMPLATES = {t["key"]: t for t in BATCH_TEMPLATES}


def load_procs():
    """All tasks by id: procedures P00..P19 and batches B00..B11 (after build.py has run)."""
    procs = {p["id"]: p | {"family": "proc"} for p in json.loads((DATA / "procedures.json").read_text())}
    bp = DATA / "batches.json"
    if bp.exists():
        procs.update({p["id"]: p for p in json.loads(bp.read_text())})
    return procs


def task_turn(p):
    """The operator's original request: the plan with every step's command, or the full item list."""
    if p["family"] == "batch":
        return (f"Operator request: {p['goal']} Use `{p['cmd_template'].replace('{id}', '<ID>')}` for each one. "
                f"{p['unit'].capitalize()}s in order: " + ", ".join(p["item_ids"]) + ".")
    lines = "\n".join(f"{i}. {s['title']}: `{s['command']}`" for i, s in enumerate(p["steps"], 1))
    return f"Operator request: run the procedure '{p['name']}'. Goal: {p['goal']} Run these steps in order, one at a time:\n{lines}"
