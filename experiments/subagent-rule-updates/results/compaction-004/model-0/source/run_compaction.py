"""Run the compaction variant for one model. No API calls without --live.

python3 run_compaction.py --live --model-index 0 --output results/compaction-001
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

import compaction as C
import harness as H
from run import delivery_check, save, warmup_valid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ERRORS = {"provider_error", "delivery_instrumentation_error", "model_protocol_error"}


def selected_conditions(config: dict) -> list[str]:
    """Optional subset of conditions, in canonical order. Defaults to all."""
    chosen = config.get("conditions", list(C.CONDITIONS))
    unknown = set(chosen) - set(C.CONDITIONS)
    if unknown or not chosen:
        raise ValueError(f"Unknown or empty conditions: {sorted(unknown)}")
    return [c for c in C.CONDITIONS if c in chosen]


def prepare_condition(client: Any, warm: H.Session, condition: str, scenario: str, prepdir: Path, tag: str,
                      config: dict) -> tuple[H.Session, dict]:
    """Interim task (relay or not), then long read-only filler with optional rolling compaction."""
    track, rolling = C.CONDITIONS[condition]
    spec = C.TRACKS[track]
    session = warm.fork()
    session.rule_version = spec["rule_version"]
    refresh = spec["rule_version"] == "R1"
    count, lines, threshold = config["filler_tasks"], config["log_lines"], config["compact_threshold_chars"]
    extra = C.filler_files(count, lines)
    record = {"condition": condition, "track": track, "rolling": rolling, **spec, "steps": [], "compactions": []}
    messages = [C.interim_message(spec["relay"], scenario)] + [C.envelope(t) for t in C.filler_tasks(count, lines)]
    for index, text in enumerate(messages):
        workspace = H.Workspace(prepdir / f"step-{index:02d}" / "workspace", prepdir / f"step-{index:02d}" / "tool_events.jsonl",
                                extra_files=extra)
        result = H.run_worker(client, session, workspace, text, tag=f"{tag}/step{index:02d}",
                              max_calls=config["max_worker_calls"], refresh=refresh, active_rule_version="R1")
        mutations = [e for e in result["events"] if e["tool"] != "read_file"]
        record["steps"].append({"index": index, "status": result["status"], "mutations": mutations,
                                "calls": len(result["requests"]), "history_chars": len(C.render_history(session.history))})
        if result["status"] != "finished" or mutations:
            record["setup_valid"] = False
            return session, record
        # Verified read-only: drop the duplicated filler copy, keep the tool event log.
        shutil.rmtree(prepdir / f"step-{index:02d}" / "workspace")
        if rolling and len(C.render_history(session.history)) > threshold:
            event = C.compact(client, session, f"{tag}/compact{len(record['compactions'])}")
            event["after_step"] = index
            record["compactions"].append(event)
    record["setup_valid"] = not rolling or len(record["compactions"]) >= config.get("min_compactions", 1)
    record["final_history_chars"] = len(C.render_history(session.history))
    record["checkpoint"] = session.checkpoint()
    return session, record


def execute(client: Any, output: Path, config: dict) -> None:
    scenario = config["scenario"]
    for rep in range(config["repetitions"]):
        repdir = output / f"rep-{rep:02d}"
        warm = H.Session(f"rep-{rep:02d}/E", "R0", scenario=scenario)
        warm_ws = H.Workspace(repdir / "warmup" / "workspace", repdir / "warmup" / "tool_events.jsonl")
        result = H.run_worker(client, warm, warm_ws, H.WARMUP, tag=f"rep{rep}/warmup",
                              max_calls=config["max_worker_calls"], active_rule_version="R0")
        result["setup_valid"] = warmup_valid(result)
        save(repdir / "warmup.json", result)
        if not result["setup_valid"]:
            raise RuntimeError(f"Invalid warmup in repetition {rep}")
        prepared = {}
        for condition in selected_conditions(config):
            session, record = prepare_condition(client, warm, condition, scenario, repdir / "prep" / condition,
                                                f"rep{rep}/prep/{condition}", config)
            save(repdir / "prep" / condition / "record.json", record)
            if not record["setup_valid"]:
                raise RuntimeError(f"Invalid preparation for {condition} in repetition {rep}")
            prepared[condition] = session
        branches = [(c, t) for c in selected_conditions(config) for t in H.TASKS]
        random.Random(config["order_seed"] + rep).shuffle(branches)
        save(repdir / "branch_order.json", branches)
        for index, (condition, task) in enumerate(branches):
            branch_id = f"{condition}__{task}"
            branchdir = repdir / "branches" / branch_id
            base_session = prepared[condition]
            base_hash = H.digest(base_session.checkpoint())
            session = base_session.fork()
            start = session.checkpoint()
            text = H.work_order_only(task)
            workspace = H.Workspace(branchdir / "workspace", branchdir / "tool_events.jsonl")
            result = H.run_worker(client, session, workspace, text, tag=f"rep{rep}/{branch_id}",
                                  max_calls=config["max_worker_calls"], refresh=C.TRACKS[C.CONDITIONS[condition][0]]["rule_version"] == "R1")
            result.update({"rep": rep, "condition": condition, "task": task, "branch_id": branch_id, "scenario": scenario,
                           "execution_index": index, "controller_rule_version": "R1", "start_session": start})
            result["delivery_verified"] = delivery_check(result, start["rule_version"], text, scenario)
            result["score"] = H.score(task, result["events"], result["files"], finished=result["status"] == "finished",
                                      scenario=scenario)
            if not result["delivery_verified"]:
                result["status"] = "delivery_instrumentation_error"
            save(branchdir / "result.json", result)
            assert base_hash == H.digest(base_session.checkpoint()), "Prepared session mutated"
            print(f"BRANCH {rep}:{branch_id} status={result['status']} success={result['score']['task_success']}", flush=True)
            if result["status"] in ("provider_error", "delivery_instrumentation_error"):
                raise RuntimeError(f"Stopping after {result['status']} at {branchdir}")


def analyze(output: Path) -> dict:
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text())
    scenario = manifest["config"]["scenario"]
    rows, records = [], []
    for path in sorted(output.glob("rep-*/branches/*/result.json")):
        row = json.loads(path.read_text())
        recomputed = H.score(row["task"], row["events"], row["files"], finished=row["score"]["finished"],
                             active_rule_version=row["controller_rule_version"], scenario=scenario)
        if recomputed != row["score"]:
            raise ValueError(f"Stored score does not match recorded actions: {path}")
        records.append(row)
    for condition in selected_conditions(manifest["config"]):
        for task in H.TASKS:
            data = [r for r in records if r["condition"] == condition and r["task"] == task]
            valid = [r for r in data if r["status"] not in ERRORS]
            rows.append({"condition": condition, "task": task, "recorded": len(data), "scored": len(valid),
                         "task_success": sum(r["score"]["task_success"] for r in valid),
                         "policy_violation": sum(r["score"]["policy_adherence"] is False for r in valid),
                         "policy_unknown": sum(r["score"]["policy_adherence"] is None for r in valid),
                         "unnecessary_or_wrong_approval": sum(bool(r["score"]["unnecessary_or_wrong_approval_requests"]) for r in valid),
                         "approval_workflow_ok": sum(r["score"]["approval_workflow_ok"] for r in valid)})
    diagnostics = {}
    for path in sorted(output.glob("rep-*/prep/*/record.json")):
        record = json.loads(path.read_text())
        rounds = [{**c["diagnostics"], "after_step": c["after_step"], "transcript_chars": c["transcript_chars"],
                   "summary_chars": c["summary_chars"], "summarizer_prompt_tokens": c["summarizer_prompt_tokens"]}
                  for c in record.get("compactions", [])]
        if rounds:
            diagnostics.setdefault(record["condition"], []).append(rounds)
    summary = {"model": manifest["selected_model"], "scenario": scenario, "planned_branches": manifest["planned_branches"],
               "recorded_branches": len(records), "statuses": dict(Counter(r["status"] for r in records)),
               "groups": rows, "summary_diagnostics": diagnostics,
               "scope": "Compaction variant. Existing workers only, unbriefed scored task, one synthetic scenario. Descriptive counts."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# Compaction variant results", "", f"Model: `{summary['model']['id']}`. Scenario: `{scenario}`.", "",
             summary["scope"], "", f"Recorded {len(records)} of {summary['planned_branches']} planned branches.", "",
             "| Condition | Task | Scored | Success | Violation | Policy unknown | Wrong/extra approval | Approval workflow OK |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['condition']} | {r['task']} | {r['scored']} | {r['task_success']} | {r['policy_violation']} | "
                     f"{r['policy_unknown']} | {r['unnecessary_or_wrong_approval']} | {r['approval_workflow_ok']} |")
    lines += ["", "## Summary keyword diagnostics (not scored)", "", "```json", json.dumps(diagnostics, indent=2), "```", "",
              "The relay is a fixed scripted message, not model-written. The summarizer sees conversation history only, not the harness rule block. Rolling conditions compact whenever the rendered history passes the configured threshold, so diagnostics list one entry per compaction round.", ""]
    (output / "tables.md").write_text("\n".join(lines))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "configs/compaction.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-index", type=int, choices=(0, 1), default=0)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("No model calls made. Use --live to authorize paid provider calls.")
    config = json.loads(args.config.read_text())
    selected = config["models"][args.model_index]
    from provider import OpenRouterClient, load_key
    load_key()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".run.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        output = root / f"model-{args.model_index}"
        output.mkdir()
        (output / "source").mkdir()
        sources = {}
        for name in ("harness.py", "compaction.py", "run_compaction.py", "run.py", "provider.py"):
            shutil.copyfile(HERE / name, output / "source" / name)
            sources[name] = H.digest((HERE / name).read_text())
        shutil.copyfile(args.config, output / "source" / "config.json")
        save(output / "manifest.json", {
            "started_utc": datetime.now(timezone.utc).isoformat(), "config": config, "selected_model": selected,
            "source_hashes": sources, "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "rules": H.rules(config["scenario"]), "user_messages": H.user_messages(config["scenario"]),
            "conditions": {k: list(v) for k, v in C.CONDITIONS.items()}, "tracks": C.TRACKS, "summarizer_system": C.SUMMARIZER_SYSTEM,
            "planned_branches": config["repetitions"] * len(selected_conditions(config)) * len(H.TASKS)})
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
