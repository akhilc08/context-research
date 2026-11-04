"""Run one model's fixed exploratory protocol. No API calls without --live.

python3 run.py --live --model-index 0 --output results/exploratory-001
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import harness as H

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def prepare_brief(client: Any, worker_type: str, task: str, tag: str, retries: int) -> dict:
    messages = H.manager_messages(worker_type, task)
    attempts = []
    for attempt in range(retries + 1):
        response = client.complete(messages, json_mode=True, tag=f"{tag}/attempt{attempt}")
        record = {"messages": copy.deepcopy(messages), "response": response}
        attempts.append(record)
        try:
            choice = response["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("Manager did not finish normally")
            value = json.loads(choice["message"]["content"])
            brief = H.validate_brief(value)
            return {"status": "valid", "brief": brief, "brief_hash": H.digest(brief), "attempts": attempts}
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            record["protocol_error"] = str(exc)
            if attempt < retries:
                # Retry from the same checkpoint with only schema feedback, never policy hints.
                messages = H.manager_messages(worker_type, task) + [
                    {"role": "assistant", "content": response.get("choices", [{}])[0].get("message", {}).get("content") or ""},
                    {"role": "user", "content": f"Your delegation response violated the output schema: {exc}. Return the required JSON object."},
                ]
    return {"status": "manager_protocol_error", "attempts": attempts}


def warmup_valid(result: dict) -> bool:
    return (result["status"] == "finished" and result["files"] == H.FIXTURE
            and all(e["tool"] == "read_file" and "error" not in e["result"] for e in result["events"])
            and any(e.get("path") == "requirements.txt" for e in result["events"]))


def delivery_check(result: dict, expected_version: str | None, text: str) -> bool:
    if not result["requests"]:
        return False
    expected = H.WORKER_SYSTEM + H.rule_block(expected_version)
    for request in result["requests"]:
        messages = request["messages"]
        if request["supplied_rule_version"] != expected_version or messages[0] != {"role": "system", "content": expected}:
            return False
        if not any(m.get("role") == "user" and m.get("content") == text for m in messages):
            return False
    return True


def execute_study(client: Any, output: Path, config: dict, *, repetitions: int | None = None) -> None:
    """Provider-injected orchestration; fake clients can exercise the entire flow offline."""
    count = config["repetitions"] if repetitions is None else repetitions
    for rep in range(count):
        repdir = output / f"rep-{rep:02d}"
        repdir.mkdir(parents=True)
        checkpoint = H.Session(f"rep-{rep:02d}/E", "R0")
        warm_workspace = H.Workspace(repdir / "warmup" / "workspace", repdir / "warmup" / "tool_events.jsonl")
        warm = H.run_worker(client, checkpoint, warm_workspace, H.WARMUP, tag=f"rep{rep}/warmup",
                            max_calls=config["max_worker_calls"], active_rule_version="R0")
        warm["setup_valid"] = warmup_valid(warm)
        save(repdir / "warmup.json", warm)
        if not warm["setup_valid"]:
            raise RuntimeError(f"Invalid warmup in repetition {rep}; no scored branches run for it")
        checkpoint_hash = H.digest(checkpoint.checkpoint())
        save(repdir / "checkpoint.json", checkpoint.checkpoint())
        briefs = {}
        for worker_type in H.WORKER_TYPES:
            for task in H.TASKS:
                record = prepare_brief(client, worker_type, task, f"rep{rep}/manager/{worker_type}/{task}", config["manager_schema_retries"])
                briefs[worker_type, task] = record
                save(repdir / "briefs" / f"{worker_type}-{task}.json", record)
        branches = [(arm, worker_type, task) for arm in H.ARMS for worker_type in H.WORKER_TYPES for task in H.TASKS]
        random.Random(config["order_seed"] + rep).shuffle(branches)
        save(repdir / "branch_order.json", branches)
        for index, (arm, worker_type, task) in enumerate(branches):
            branch_id = f"{arm}__{worker_type}__{task}"
            branchdir = repdir / "branches" / branch_id
            record = briefs[worker_type, task]
            base = {"rep": rep, "arm": arm, "worker_type": worker_type, "task": task, "branch_id": branch_id,
                    "execution_index": index, "controller_rule_version": "R1", "checkpoint_hash": checkpoint_hash}
            if record["status"] != "valid":
                save(branchdir / "result.json", {**base, "status": "manager_protocol_error", "score": None})
                continue
            brief = record["brief"]
            text = H.delegation(task, brief)
            session = H.session_for(arm, worker_type, checkpoint, f"rep-{rep:02d}/N/{task}")
            start = session.checkpoint()
            if worker_type == "existing":
                assert start["session_id"] == checkpoint.session_id and start["history_hash"] == H.digest(checkpoint.history)
            else:
                assert not start["history"]
            workspace = H.Workspace(branchdir / "workspace", branchdir / "tool_events.jsonl")
            result = H.run_worker(client, session, workspace, text, tag=f"rep{rep}/{branch_id}",
                                  max_calls=config["max_worker_calls"], refresh=arm == "refreshed_store")
            result.update(base)
            result["start_session"] = start
            result["brief_hash"] = record["brief_hash"]
            result["relay_user_message_ids"] = brief["relay_user_message_ids"]
            result["delivery_verified"] = delivery_check(result, start["rule_version"], text)
            result["score"] = H.score(task, result["events"], result["files"], finished=result["status"] == "finished")
            if not result["delivery_verified"]:
                result["status"] = "delivery_instrumentation_error"
            save(branchdir / "result.json", result)
            assert checkpoint_hash == H.digest(checkpoint.checkpoint()), "Shared checkpoint mutated"
            print(f"BRANCH {rep}:{branch_id} status={result['status']} success={result['score']['task_success']}", flush=True)
            if result["status"] in ("provider_error", "delivery_instrumentation_error"):
                raise RuntimeError(f"Stopping after {result['status']}; partial branch preserved at {branchdir}")


def freeze_manifest(output: Path, config: dict, selected: dict) -> None:
    paths = [HERE / name for name in ("harness.py", "run.py", "provider.py", "analyze.py", "configs/exploratory.json")]
    sources = {}
    for path in paths:
        relative = path.relative_to(HERE)
        sources[str(relative)] = H.digest(path.read_text())
        dest = output / "source" / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    spec = REPO / "docs/subagent-rule-update-scenario.md"
    save(output / "manifest.json", {
        "started_utc": datetime.now(timezone.utc).isoformat(), "config": config, "selected_model": selected,
        "source_hashes": sources, "spec_hash": H.digest(spec.read_text()),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True),
        "rules": H.RULES, "user_messages": H.USER_MESSAGES, "tasks": H.TASKS, "fixture": H.FIXTURE,
        "stage": "exploratory_no_compaction_correct_state", "planned_branches": config["repetitions"] * 12,
        "notes": ["No automatic rule extraction, compaction, or summary rewriting.",
                  "Existing-worker session IDs are retained within independent checkpoint forks.",
                  "New creation-pin and refreshed-store contexts are initially identical controls.",
                  "Existing manager-relay and creation-pin contexts are identical because R0 delivery is controlled.",
                  "Manager briefs differ by worker/task but are matched across arms.",
                  "Three repetitions are descriptive, not independent evidence across tasks."],
    })
    shutil.copyfile(spec, output / "source" / "scenario.md")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "configs/exploratory.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-index", type=int, choices=(0, 1), default=0)
    parser.add_argument("--live", action="store_true", help="Authorize paid provider calls for this fixed config")
    args = parser.parse_args()
    if not args.live:
        parser.error("No model calls made. Use --live only after offline validation and review.")
    config = json.loads(args.config.read_text())
    if config["total_budget_usd"] != sum(m["budget_usd"] for m in config["models"]):
        raise ValueError("Per-model caps must sum to the authorized total")
    selected = config["models"][args.model_index]
    from provider import OpenRouterClient, load_key
    load_key()  # Fail before creating output if credentials are missing.
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        output = root / f"model-{args.model_index}"
        output.mkdir()  # Existing output is never overwritten or silently resumed.
        freeze_manifest(output, config, selected)
        client = OpenRouterClient(output, model=selected["id"], provider_name=selected["provider"],
                                  budget_usd=selected["budget_usd"], max_calls=config["max_provider_calls"],
                                  temperature=config["temperature"], max_tokens=config["max_output_tokens"],
                                  reasoning_effort=config["reasoning_effort"])
        failure = None
        try:
            execute_study(client, output, config)
        except Exception as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)}
            save(output / "run_error.json", failure)
        finally:
            save(output / "provider_summary.json", client.summary())
            from analyze import analyze
            analyze(output)
        print(f"RUN_COMPLETE output={output} error={failure}", flush=True)
        return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
