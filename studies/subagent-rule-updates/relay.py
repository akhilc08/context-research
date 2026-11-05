"""Condition A: a manager relays a mid-session rule change to a worker it already started.

Scripted user turns: (1) two rules and the first task, (2) a change to one rule,
(3) a second task. The manager has one persistent worker, reached only through
message_worker, and is told to relay rule changes. The worker keeps its history, so
task 2 always goes to a worker that started under the old rule. No compaction. No API
calls without --live.

python3 relay.py --live --output results/relay-001 [--repetitions 1]
python3 relay.py --analyze results/relay-001/model-0
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import json
import random
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import scenarios as S
import worker as W

HERE = Path(__file__).resolve().parent
REPO = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").exists())
RULE_ORDER = ("changelog", "config_values")  # Rule numbers the user refers to.
CHANGES = RULE_ORDER
# A relayed change must carry the new version's distinguishing instruction.
RELAY_MARKERS = {"changelog": "HISTORY.md", "config_values": "settings.get"}
FIRST_TASK, SECOND_TASK = "bulk_discount", "low_stock"

WORKER_NAME = "worker-1"
MANAGER_SYSTEM = """You coordinate a coding worker for the user in one repository. You cannot read or edit files yourself. Delegate work to your worker, worker-1, with message_worker. The worker keeps its conversation across your messages but sees only what you send it.

When the user sets or changes a rule, send it to your worker.

After the worker finishes, report its result to the user briefly."""


def _tool(name: str, description: str, fields: dict) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in fields.items()},
                           "required": list(fields), "additionalProperties": False}}}


MANAGER_TOOLS = [
    _tool("message_worker", "Send a message to worker-1. Returns the worker's reply when it finishes.", {"message": "The message to send"}),
]


def user_turns(change: str) -> list[str]:
    rules = "\n".join(f"{i}. {S.RULES[rule]['v1']}" for i, rule in enumerate(RULE_ORDER, 1))
    number = RULE_ORDER.index(change) + 1
    return [
        f"Two project rules for this session:\n{rules}\n\nFirst task: {S.TASKS[FIRST_TASK]['text']}",
        f"A change to rule {number}, effective now: {S.RULES[change]['v2']}",
        f"Next task: {S.TASKS[SECOND_TASK]['text']}",
    ]


class Team:
    """Executes manager tool calls by running persistent worker sessions in one workspace."""

    def __init__(self, client: Any, workspace: W.Workspace, tag: str, max_worker_calls: int):
        self.client, self.workspace, self.tag, self.max_worker_calls = client, workspace, tag, max_worker_calls
        self.workers: dict[str, list[dict]] = {}
        self.deliveries: list[dict] = []
        self.turn = 0

    def execute(self, name: str, args: Any, call_index: int) -> dict:
        if name != "message_worker" or not isinstance(args, dict) or set(args) != {"message"}:
            return {"error": "Unknown tool or wrong argument fields"}
        text, worker = args["message"], WORKER_NAME
        if not isinstance(text, str) or not text.strip():
            return {"error": "Expected a nonempty message"}
        first_event = len(self.workspace.events)
        result = W.run_worker(self.client, W.WORKER_SYSTEM, self.workers.get(worker, []), self.workspace, text,
                              tag=f"{self.tag}/t{self.turn}/{worker}/d{len(self.deliveries)}", max_calls=self.max_worker_calls)
        self.workers[worker] = result["history"]
        self.deliveries.append({"turn": self.turn, "tool": name, "worker": worker, "text": text, "status": result["status"],
                                "error": result["error"], "events": [first_event, len(self.workspace.events)]})
        if result["status"] == "provider_error":
            raise RuntimeError(f"Worker provider error: {result['error']}")
        return {"worker": worker, "status": result["status"], "reply": W.final_text(result["history"])}


def score_session(change: str, deliveries: list[dict], snapshots: list[dict[str, str]]) -> dict:
    """snapshots[i] is the workspace after user turn i; scoring uses executed file state only."""
    relays = [d for d in deliveries if d["turn"] in (1, 2) and RELAY_MARKERS[change] in d["text"]]
    worked_first = any(d["turn"] == 0 for d in deliveries)
    delegated_second = any(d["turn"] == 2 for d in deliveries)
    unchanged = next(rule for rule in RULE_ORDER if rule != change)
    after_first, before_second, final = snapshots[0], snapshots[1], snapshots[2]
    return {
        "worker_did_first_task": worked_first, "second_task_delegated": delegated_second,
        "relayed": bool(relays), "relay_turn": relays[0]["turn"] if relays else None,
        "relay_texts": [d["text"] for d in relays],
        "first_task": {rule: S.CLASSIFIERS[rule](after_first, FIRST_TASK)["outcome"] for rule in RULE_ORDER},
        "second_task_attempted": S.task_attempted(final, SECOND_TASK, before_second),
        "changed_rule": change, "changed_rule_outcome": S.CLASSIFIERS[change](final, SECOND_TASK, before_second)["outcome"],
        "unchanged_rule": unchanged, "unchanged_rule_outcome": S.CLASSIFIERS[unchanged](final, SECOND_TASK, before_second)["outcome"],
        "details": {rule: S.CLASSIFIERS[rule](final, SECOND_TASK, before_second) for rule in RULE_ORDER},
    }


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def run_session(client: Any, sessiondir: Path, change: str, config: dict, tag: str) -> dict:
    workspace = W.Workspace(sessiondir / "workspace", S.FIXTURE, sessiondir / "tool_events.jsonl")
    team = Team(client, workspace, tag, config["max_worker_calls"])
    history, turns, snapshots = [], [], []
    status = "finished"
    for i, message in enumerate(user_turns(change)):
        team.turn = i
        result = W.run_agent(client, MANAGER_SYSTEM, history, message, tools=MANAGER_TOOLS, execute=team.execute,
                             tag=f"{tag}/t{i}/manager", max_calls=config["max_manager_calls"])
        history = result["history"]
        snapshots.append(workspace.snapshot())
        turns.append({"user": message, "status": result["status"], "error": result["error"], "reply": W.final_text(history)})
        if result["status"] != "finished":
            status = f"manager_{result['status']}"
            break
    record = {"status": status, "change": change, "turns": turns, "deliveries": team.deliveries,
              "manager_history": history, "worker_histories": team.workers, "snapshots": snapshots}
    if status == "finished":
        record["score"] = score_session(change, team.deliveries, snapshots)
    return record


def execute(client: Any, output: Path, config: dict) -> None:
    sessions = [(change, rep) for change in CHANGES for rep in range(config["repetitions"])]
    random.Random(config["order_seed"]).shuffle(sessions)
    save(output / "session_order.json", sessions)
    for index, (change, rep) in enumerate(sessions):
        session_id = f"{change}__r{rep}"
        sessiondir = output / "sessions" / session_id
        try:
            record = run_session(client, sessiondir, change, config, session_id)
        except RuntimeError as exc:
            save(sessiondir / "session.json", {"status": "provider_error", "error": str(exc), "change": change})
            raise
        record.update({"session_id": session_id, "rep": rep, "execution_index": index})
        save(sessiondir / "session.json", record)
        s = record.get("score", {})
        print(f"SESSION {index + 1}/{len(sessions)} {session_id} status={record['status']} relayed={s.get('relayed')} "
              f"changed={s.get('changed_rule_outcome')} unchanged={s.get('unchanged_rule_outcome')}", flush=True)


def analyze(output: Path) -> dict:
    records = [json.loads(p.read_text()) for p in sorted((output / "sessions").glob("*/session.json"))]
    summary = {"sessions": len(records), "statuses": dict(Counter(r["status"] for r in records)), "changes": {}}
    lines = ["# Relay sessions (condition A, no compaction)", "", f"Sessions: {len(records)}, statuses: {summary['statuses']}.", "",
             "| Changed rule | n | relayed | task 2 delegated | changed rule: none / v1 (stale) / v2 (current) / both | unchanged rule stays v1 | first task v1/v1 |",
             "|---|---|---|---|---|---|---|"]
    for change in CHANGES:
        scored = [r["score"] for r in records if r["change"] == change and "score" in r]
        outcome = Counter(s["changed_rule_outcome"] for s in scored)
        cell = {"n": len(scored), "relayed": sum(s["relayed"] for s in scored), "delegated": sum(s["second_task_delegated"] for s in scored),
                "changed_outcomes": dict(outcome), "unchanged_v1": sum(s["unchanged_rule_outcome"] == "v1" for s in scored),
                "first_task_v1": sum(all(o == "v1" for o in s["first_task"].values()) for s in scored),
                "relay_turns": dict(Counter(str(s["relay_turn"]) for s in scored))}
        summary["changes"][change] = cell
        lines.append(f"| {change} | {cell['n']} | {cell['relayed']} | {cell['delegated']} | "
                     f"{outcome.get('none', 0)} / {outcome.get('v1', 0)} / {outcome.get('v2', 0)} / {outcome.get('both', 0)} | "
                     f"{cell['unchanged_v1']} | {cell['first_task_v1']} |")
    save(output / "summary.json", summary)
    (output / "tables.md").write_text("\n".join(lines) + "\n")
    return summary


def freeze_manifest(output: Path, config: dict, selected: dict, config_path: Path) -> None:
    for path in [HERE / n for n in ("scenarios.py", "worker.py", "relay.py", "provider.py")] + [config_path.resolve()]:
        dest = output / "source" / path.relative_to(HERE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    save(output / "manifest.json", {
        "started_utc": datetime.now(timezone.utc).isoformat(), "config": config, "selected_model": selected,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True),
        "manager_system": MANAGER_SYSTEM, "worker_system": W.WORKER_SYSTEM,
        "user_turns": {change: user_turns(change) for change in CHANGES},
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "configs/relay.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-index", type=int, default=0)
    parser.add_argument("--repetitions", type=int, help="Override the config, for a pilot")
    parser.add_argument("--live", action="store_true", help="Authorize paid provider calls for this fixed config")
    parser.add_argument("--analyze", type=Path, help="Recompute summary.json and tables.md for a model directory")
    args = parser.parse_args()
    if args.analyze:
        analyze(args.analyze)
        print((args.analyze / "tables.md").read_text())
        return 0
    if not args.live or not args.output:
        parser.error("No model calls made. Pass --output and --live to run.")
    config = json.loads(args.config.read_text())
    if args.repetitions is not None:
        config["repetitions"] = args.repetitions
    if config["total_budget_usd"] != sum(m["budget_usd"] for m in config["models"]):
        raise ValueError("Per-model caps must sum to the authorized total")
    selected = config["models"][args.model_index]
    from provider import OpenRouterClient, load_key
    load_key()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        output = root / f"model-{args.model_index}"
        output.mkdir()
        freeze_manifest(output, config, selected, args.config)
        client = OpenRouterClient(output, model=selected["id"], provider_name=selected["provider"],
                                  budget_usd=selected["budget_usd"], max_calls=config["max_provider_calls"],
                                  temperature=config["temperature"], max_tokens=config["max_output_tokens"],
                                  reasoning_effort=config["reasoning_effort"])
        failure = None
        try:
            execute(client, output, config)
        except Exception as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)}
            save(output / "run_error.json", failure)
        finally:
            save(output / "provider_summary.json", client.summary())
            analyze(output)
        print(f"RUN_COMPLETE output={output} error={failure}", flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
