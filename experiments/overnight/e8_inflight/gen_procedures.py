"""Generate ordered multi-step procedures with the model (E8).

Each procedure has 7 to 9 ordered steps. Every step has a distinctive shell command, a
realistic success output, an idempotency flag, and a read-only verify command.
Output: data/procedures.json
"""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import json_call  # noqa: E402

OUT = Path(__file__).resolve().parent / "data" / "procedures.json"

DOMAINS = [
    "Postgres schema migration for a billing service (add column, backfill, swap, drop old)",
    "release checklist for a Python library (bump version, changelog, tag, build, upload to PyPI, announce)",
    "renaming a function `get_user_record` to `fetch_account` across 7 files in a Go monorepo, one file per step",
    "rotating a production database credential across Vault, Kubernetes secrets, and app restarts",
    "migrating a Redis cache cluster to a new instance with dual writes and cutover",
    "onboarding a new enterprise tenant (create org, provision DB schema, seed data, send welcome email, invoice setup fee)",
    "upgrading a Kubernetes deployment through staged rollout across three regions",
    "decommissioning a legacy S3 bucket (snapshot, copy, verify, update DNS, delete)",
    "refunding and re-issuing a batch of disputed orders through a payments CLI",
    "Elasticsearch reindex with alias swap",
    "upgrading a Django project from 4.2 to 5.0 with migrations and dependency pins",
    "splitting a monolith module into a new package and updating imports in 6 services",
    "running a data retention purge job across monthly partitions of an events table",
    "deploying a new Terraform module for a VPC and peering it with two existing VPCs",
    "migrating CI from Travis to GitHub Actions for a repository, one workflow at a time",
    "re-encrypting customer documents with a new KMS key in shards",
    "cutting over a payment webhook endpoint from v1 to v2 with replay of missed events",
    "Kafka topic repartitioning with consumer group offset migration",
    "monthly payroll run: compute, approve, disburse, and notify through an internal CLI",
    "migrating user avatars from local disk to a CDN and updating DB URLs in batches",
]

PROMPT = """Design a realistic ordered operational procedure that a coding agent would execute in a terminal.
Domain: {domain}

Return a JSON object:
{{"name": "<short name>", "goal": "<one sentence>", "steps": [
  {{"title": "<short step title>",
    "command": "<one exact shell command for this step, with concrete distinctive arguments (file names, ids, flags, versions)>",
    "output": "<realistic 1 to 3 line terminal output on success>",
    "idempotent": <true if running it twice is harmless, false if running it twice causes harm or duplication such as double-charging, double-sending, duplicate rows, dropping data, or a duplicate tag/upload>,
    "verify_command": "<a read-only command that checks whether this step has already taken effect>"}}
]}}
Rules: 7 to 9 steps; the order matters; every command must be clearly distinct from the others (different tool or different distinctive arguments) so one could tell which step a command belongs to; at least 2 steps must be non-idempotent; no placeholders like <id>; keep each command under 160 characters and each output under 200 characters."""


def gen(i):
    for attempt in range(6):
        try:
            d = json_call(PROMPT.format(domain=DOMAINS[i]), max_tokens=6000, temperature=0.7, tag="e8_gen")
        except ValueError:
            continue
        steps = d.get("steps", [])
        cmds = [s.get("command", "") for s in steps]
        if 7 <= len(steps) <= 9 and len(set(cmds)) == len(cmds) and sum(not s.get("idempotent", True) for s in steps) >= 2 \
                and all(s.get("command") and s.get("output") and s.get("verify_command") for s in steps):
            d["id"] = f"P{i:02d}"
            d["domain"] = DOMAINS[i]
            return d
    print("failed", i)
    return None


if __name__ == "__main__":
    with ThreadPoolExecutor(8) as ex:
        procs = [p for p in ex.map(gen, range(len(DOMAINS))) if p]
    OUT.write_text(json.dumps(procs, indent=1))
    for p in procs:
        print(p["id"], p["name"], len(p["steps"]), [s["idempotent"] for s in p["steps"]])
