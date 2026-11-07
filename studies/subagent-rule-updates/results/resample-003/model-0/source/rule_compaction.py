"""The established compaction protocol, run on the screened rules with the original rules in the conversation.

Held fixed from run_compaction.py and compaction.py: original rules placed first in the
worker's conversation (compaction-006 `relay_compact_inline`), a read-only warmup, the
amendment relayed during a read-only interim task in the same envelope, 25 read-only log
filler tasks, the same summarizer prompt, rolling compaction at the same threshold, and the
scored task as a bare work order on a fresh workspace.

Changed: the scenario (fixture, rules, tasks, scoring from scenarios.py) and the worker's
system prompt and tools (worker.py), under which screen-001 validated the rules. There is no
system-prompt rule block. No API calls without --live.

python3 rule_compaction.py --live --output results/rule-compaction-001 [--repetitions 1]
python3 rule_compaction.py --live --config configs/rule-compaction-pi.json --output results/rule-compaction-pi-001
python3 rule_compaction.py --live --config configs/rule-compaction-store.json --output results/rule-compaction-store-001
python3 rule_compaction.py --analyze results/rule-compaction-001/model-0
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
from types import SimpleNamespace
from typing import Any

import compaction as C
import pi_compaction as PI
import scenarios as S
import worker as W

HERE = Path(__file__).resolve().parent
REPO = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").exists())
RULE_ORDER = ("changelog", "config_values")
CHANGES = RULE_ORDER
# A session names the version each rule starts at and which rule changes to which version.
# "changelog" and "config_values" are the original design. The last two swap which config content is
# the original rule and which is the amendment, for the amendment-status test
# (docs/amendment-status-test.md). Keys must not contain "__".
SESSIONS = {
    "changelog": {"start": {"changelog": "v1", "config_values": "v1"}, "change": "changelog", "to": "v2"},
    "config_values": {"start": {"changelog": "v1", "config_values": "v1"}, "change": "config_values", "to": "v2"},
    "changelog_sfirst": {"start": {"changelog": "v1", "config_values": "v2"}, "change": "changelog", "to": "v2"},
    "config_reverse": {"start": {"changelog": "v1", "config_values": "v2"}, "change": "config_values", "to": "v1"},
}
# condition -> compactor. "generic" compacts at the size threshold with compaction.py and replaces the
# whole history. "pi" runs pi_compaction.py after the configured steps, the steps where generic
# compaction happened in rule-compaction-001 and 002 (8, 16, 24).
CONDITIONS = {"relay_no_compact": None, "relay_compact": "generic", "relay_compact_pi": "pi",
              "store_compact": "generic", "reinsert_compact": "generic"}
# store: the rules are never in the conversation. The harness puts the current rules in the system
# prompt on every call and changes them at the step where the other conditions receive the relay.
STORE_CONDITIONS = {"store_compact"}
# reinsert: like relay_compact, plus the verbatim relayed amendment re-added after each compaction.
REINSERT_CONDITIONS = {"reinsert_compact"}
WARMUP = "Read README.md and report what it says. Do not change any files."
INTERIM_TASK = "Read docs/architecture.md and report what it contains. Do not change any files."
RELAY_BRIEFING = "The user has amended one of their rules since you started. Their amendment is relayed below."
U0_LABEL = "original author: user | the user's first rule message in this session"
U1_LABEL = "original author: user | a later amendment, sent after U0"
# Keywords for summary inspection only, never scoring.
SUMMARY_MARKERS = {"changelog": {"v1": "CHANGELOG", "v2": "HISTORY.md"}, "config_values": {"v1": "config.py", "v2": "settings.get"}}


def original_rules(session: str = "changelog") -> str:
    start = SESSIONS[session]["start"]
    return "\n".join(f"{i}. {S.RULES[rule][start[rule]]}" for i, rule in enumerate(RULE_ORDER, 1))


def amendment(session: str) -> str:
    spec = SESSIONS[session]
    return f"A change to rule {RULE_ORDER.index(spec['change']) + 1}, effective now: {S.RULES[spec['change']][spec['to']]}"


def inline_u0_message(session: str = "changelog") -> str:
    return C.envelope("No task. Recording the user's project rules for this session.", relay=f"U0 | {U0_LABEL}\n{original_rules(session)}")


def current_rules(change: str | None) -> str:
    """The rules after `change` has moved to its second version. None means before any change."""
    return "\n".join(f"{i}. {S.RULES[rule]['v2' if rule == change else 'v1']}" for i, rule in enumerate(RULE_ORDER, 1))


def store_system(change: str | None) -> str:
    return (f"{W.WORKER_SYSTEM}\n\n[Current project rules from the user, kept up to date by the harness]\n"
            f"{current_rules(change)}\n[/Current project rules]")


def reinsert_message(change: str) -> str:
    return C.envelope(C.REINSERT_TASK, RELAY_BRIEFING, f"U1 | {U1_LABEL}\n{amendment(change)}")


def relay_message(change: str) -> str:
    return C.envelope(INTERIM_TASK, RELAY_BRIEFING, f"U1 | {U1_LABEL}\n{amendment(change)}")


def task_message(task: str) -> str:
    return C.envelope(S.TASKS[task]["text"])


def summary_markers(summary: str, change: str) -> dict:
    return {f"{rule}_{version}": marker in summary for rule, versions in SUMMARY_MARKERS.items() for version, marker in versions.items()}


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def read_only_step(client: Any, history: list[dict], stepdir: Path, message: str, tag: str, config: dict,
                   extra: dict[str, str], system: str = W.WORKER_SYSTEM) -> tuple[list[dict], dict]:
    workspace = W.Workspace(stepdir / "workspace", {**S.FIXTURE, **extra}, stepdir / "tool_events.jsonl")
    result = W.run_worker(client, system, history, workspace, message, tag=tag, max_calls=config["max_worker_calls"])
    mutations = [e for e in result["events"] if e["tool"] == "write_file"]
    step = {"status": result["status"], "error": result["error"], "mutations": mutations, "calls": len(result["responses"]),
            "history_chars": len(C.render_history(result["history"]))}
    if result["status"] == "finished" and not mutations:
        shutil.rmtree(stepdir / "workspace")  # Verified read-only: keep the event log, drop the copy.
    return result["history"], step


def prepare(client: Any, warm: list[dict], change: str, condition: str, prepdir: Path, tag: str, config: dict) -> tuple[list[dict], dict]:
    compactor = CONDITIONS[condition]
    store = condition in STORE_CONDITIONS
    system = store_system(change) if store else W.WORKER_SYSTEM
    pi_state = PI.PiState()
    count, lines, threshold = config["filler_tasks"], config["log_lines"], config["compact_threshold_chars"]
    extra = C.filler_files(count, lines)
    history = copy.deepcopy(warm)
    record = {"condition": condition, "change": change, "compactor": compactor, "system": system, "steps": [], "compactions": []}
    first = C.envelope(INTERIM_TASK) if store else relay_message(change)
    messages = [first] + [C.envelope(t) for t in C.filler_tasks(count, lines)]
    for index, text in enumerate(messages):
        history, step = read_only_step(client, history, prepdir / f"step-{index:02d}", text, f"{tag}/step{index:02d}", config, extra, system)
        record["steps"].append({"index": index, **step})
        if step["status"] != "finished" or step["mutations"]:
            record["setup_valid"] = False
            return history, record
        compact_tag = f"{tag}/compact{len(record['compactions'])}"
        if compactor == "generic" and len(C.render_history(history)) > threshold:
            session = SimpleNamespace(history=history)
            event = C.compact(client, session, compact_tag)
            history = session.history
        elif compactor == "pi" and index in config["pi_compact_after_steps"]:
            history, event = PI.compact(client, history, pi_state, compact_tag)
        else:
            continue
        event.update({"after_step": index, "markers": summary_markers(event.get("summary", ""), change)})
        record["compactions"].append(event)
        if condition in REINSERT_CONDITIONS:
            history = history + [{"role": "user", "content": reinsert_message(change)}]
    if compactor == "pi":
        record["setup_valid"] = [c["after_step"] for c in record["compactions"] if not c["skipped"]] == config["pi_compact_after_steps"]
    else:
        record["setup_valid"] = compactor is None or len(record["compactions"]) >= config["min_compactions"]
    record["final_history_chars"] = len(C.render_history(history))
    record["final_history"] = history
    return history, record


def score(files: dict[str, str], task: str, session: str) -> dict:
    spec = SESSIONS[session]
    change = spec["change"]
    unchanged = next(rule for rule in RULE_ORDER if rule != change)
    expected = {change: spec["to"], unchanged: spec["start"][unchanged]}
    details = {rule: S.CLASSIFIERS[rule](files, task) for rule in RULE_ORDER}
    return {"task_attempted": S.task_attempted(files, task), "session": session, "changed_rule": change,
            "changed_rule_outcome": details[change]["outcome"], "changed_rule_expected": expected[change],
            "unchanged_rule": unchanged, "unchanged_rule_outcome": details[unchanged]["outcome"],
            "unchanged_rule_expected": expected[unchanged],
            "config_role": "amended" if change == "config_values" else "original",
            "config_expected": expected["config_values"],
            "config_followed": details["config_values"]["outcome"] == expected["config_values"], "details": details}


def planned(config: dict, session: str, condition: str, rep: int) -> bool:
    """repetition_caps limits a session, a condition, or one "session:condition" pair to fewer repetitions."""
    caps = config.get("repetition_caps", {})
    limit = min([config["repetitions"]] + [caps[k] for k in (session, condition, f"{session}:{condition}") if k in caps])
    return rep < limit


def warmup(client: Any, history: list[dict], system: str, stepdir: Path, tag: str, config: dict) -> list[dict]:
    warm, step = read_only_step(client, history, stepdir, WARMUP, tag, config, {}, system)
    save(stepdir.with_suffix(".json"), {**step, "system": system, "history": warm})
    if step["status"] != "finished" or step["mutations"]:
        raise RuntimeError(f"Invalid warmup at {stepdir}")
    return warm


def execute(client: Any, output: Path, config: dict) -> None:
    for rep in range(config["repetitions"]):
        repdir = output / f"rep-{rep:02d}"
        sessions = config.get("sessions", list(CHANGES))
        pairs = [(s, c) for s in sessions for c in config["conditions"] if planned(config, s, c, rep)]
        if any(s not in CHANGES for s, c in pairs if c in STORE_CONDITIONS):
            raise ValueError("Store conditions support only the original sessions")
        warms = {}
        for session in dict.fromkeys(s for s, c in pairs if c not in STORE_CONDITIONS):
            start = tuple(SESSIONS[session]["start"][r] for r in RULE_ORDER)
            if start in warms:
                continue
            # Original rules first in the conversation, then the read-only warmup (compaction-006 inline order).
            name = "warmup" if start == ("v1", "v1") else "warmup-" + "-".join(start)
            warms[start] = warmup(client, [{"role": "user", "content": inline_u0_message(session)}], W.WORKER_SYSTEM,
                                  repdir / name, f"rep{rep}/{name}", config)
        if any(c in STORE_CONDITIONS for s, c in pairs):
            # No rules in the conversation. The store supplies the original rules in the system prompt.
            warms["store"] = warmup(client, [], store_system(None), repdir / "warmup-store", f"rep{rep}/warmup-store", config)
        prepared = {}
        for change, condition in pairs:
            key = f"{change}__{condition}"
            warm = warms["store"] if condition in STORE_CONDITIONS else warms[tuple(SESSIONS[change]["start"][r] for r in RULE_ORDER)]
            history, record = prepare(client, warm, change, condition, repdir / "prep" / key, f"rep{rep}/prep/{key}", config)
            save(repdir / "prep" / key / "record.json", record)
            if not record["setup_valid"]:
                raise RuntimeError(f"Invalid preparation for {key} in repetition {rep}")
            prepared[key] = (history, record["system"])
        branches = [(key, task) for key in prepared for task in S.TASKS]
        random.Random(config["order_seed"] + rep).shuffle(branches)
        save(repdir / "branch_order.json", branches)
        for index, (key, task) in enumerate(branches):
            change, condition = key.split("__")
            branchdir = repdir / "branches" / f"{key}__{task}"
            workspace = W.Workspace(branchdir / "workspace", S.FIXTURE, branchdir / "tool_events.jsonl")
            history, system = prepared[key]
            result = W.run_worker(client, system, history, workspace, task_message(task),
                                  tag=f"rep{rep}/{key}/{task}", max_calls=config["max_worker_calls"])
            result.update({"rep": rep, "change": change, "condition": condition, "task": task, "execution_index": index,
                           "system": system, "start_history_chars": len(C.render_history(history)),
                           "score": score(result["files"], task, change)})
            save(branchdir / "result.json", result)
            s = result["score"]
            print(f"BRANCH {rep}:{key}__{task} status={result['status']} changed={s['changed_rule_outcome']} "
                  f"unchanged={s['unchanged_rule_outcome']} config_followed={s['config_followed']}", flush=True)
            if result["status"] == "provider_error":
                raise RuntimeError(f"Stopping after provider error at {branchdir}")


def analyze(output: Path) -> dict:
    results = [json.loads(p.read_text()) for p in sorted(output.glob("rep-*/branches/*/result.json"))]
    records = [json.loads(p.read_text()) for p in sorted(output.glob("rep-*/prep/*/record.json"))]
    valid = [r for r in results if r["status"] == "finished"]
    summary = {"branches": len(results), "statuses": dict(Counter(r["status"] for r in results)), "cells": {}, "summaries": {}}
    lines = ["# Rule compaction (original rules in the conversation, screened rules)", "",
             f"Branches: {len(results)}, statuses: {summary['statuses']}.", "",
             "| Changed rule | Condition | n | changed rule: none / v1 (stale) / v2 (current) / both | unchanged rule stays v1 | task attempted |",
             "|---|---|---|---|---|---|"]
    for change in SESSIONS:
        for condition in CONDITIONS:
            subset = [r for r in valid if r["change"] == change and r["condition"] == condition]
            if not subset:
                continue
            o = Counter(r["score"]["changed_rule_outcome"] for r in subset)
            cell = {"n": len(subset), "changed_outcomes": dict(o),
                    "unchanged_v1": sum(r["score"]["unchanged_rule_outcome"] == "v1" for r in subset),
                    "task_attempted": sum(r["score"]["task_attempted"] for r in subset)}
            summary["cells"][f"{change}__{condition}"] = cell
            lines.append(f"| {change} | {condition} | {cell['n']} | {o.get('none', 0)} / {o.get('v1', 0)} / {o.get('v2', 0)} / {o.get('both', 0)} | "
                         f"{cell['unchanged_v1']} | {cell['task_attempted']} |")
    lines += ["", "## Final summary keywords (inspection only, not scored)", "",
              "| Changed rule | Final summaries | mentions new version | mentions old version only | mentions neither |", "|---|---|---|---|---|"]
    for change in SESSIONS:
        for condition in CONDITIONS:
            group = [r for r in records if r["change"] == change and r["condition"] == condition and r.get("compactions")]
            if not group:
                continue
            spec = SESSIONS[change]
            rule, new_v, old_v = spec["change"], spec["to"], spec["start"][spec["change"]]
            finals = [r["compactions"][-1]["markers"] for r in group]
            new = sum(m[f"{rule}_{new_v}"] for m in finals)
            old_only = sum(m[f"{rule}_{old_v}"] and not m[f"{rule}_{new_v}"] for m in finals)
            neither = sum(not m[f"{rule}_{old_v}"] and not m[f"{rule}_{new_v}"] for m in finals)
            summary["summaries"][f"{change}__{condition}"] = {"final_summaries": len(finals), "new": new, "old_only": old_only,
                                                              "neither": neither, "rounds": [len(r["compactions"]) for r in group]}
            lines.append(f"| {change} ({condition}) | {len(finals)} | {new} | {old_only} | {neither} |")
    if any("config_followed" in r["score"] for r in valid):
        lines += ["", "## Config rule by content and role", "",
                  "| Session | Condition | Config content | Config role | Task | followed |", "|---|---|---|---|---|---|"]
        for change in SESSIONS:
            for condition in CONDITIONS:
                for task in S.TASKS:
                    subset = [r for r in valid if r["change"] == change and r["condition"] == condition and r["task"] == task
                              and "config_followed" in r["score"]]
                    if not subset:
                        continue
                    content = {"v1": "config.py", "v2": "settings.get"}[subset[0]["score"]["config_expected"]]
                    followed = sum(r["score"]["config_followed"] for r in subset)
                    summary.setdefault("config_by_role", {})[f"{change}__{condition}__{task}"] = {
                        "content": content, "role": subset[0]["score"]["config_role"], "n": len(subset), "followed": followed}
                    lines.append(f"| {change} | {condition} | {content} | {subset[0]['score']['config_role']} | {task} | {followed}/{len(subset)} |")
    save(output / "summary.json", summary)
    (output / "tables.md").write_text("\n".join(lines) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "configs/rule-compaction.json")
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
        for name in ("scenarios.py", "worker.py", "compaction.py", "pi_compaction.py", "pi_compaction_prompts.json", "rule_compaction.py", "provider.py"):
            (output / "source").mkdir(exist_ok=True)
            shutil.copyfile(HERE / name, output / "source" / name)
        shutil.copyfile(args.config, output / "source" / "config.json")
        save(output / "manifest.json", {
            "started_utc": datetime.now(timezone.utc).isoformat(), "config": config, "selected_model": selected,
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "git_status": subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True),
            "worker_system": W.WORKER_SYSTEM, "summarizer_system": C.SUMMARIZER_SYSTEM,
            "inline_u0": {s: inline_u0_message(s) for s in config.get("sessions", CHANGES)},
            "relays": {s: relay_message(s) for s in config.get("sessions", CHANGES)}, "sessions": SESSIONS,
            "store_systems": {str(c): store_system(c) for c in (None, *CHANGES)}, "reinserts": {c: reinsert_message(c) for c in CHANGES},
            "tasks": {t: task_message(t) for t in S.TASKS}})
        client = OpenRouterClient(output, model=selected["id"], provider_name=selected["provider"],
                                  budget_usd=selected["budget_usd"], max_calls=config["max_provider_calls"],
                                  temperature=config["temperature"], max_tokens=config["max_output_tokens"],
                                  reasoning_effort=config["reasoning_effort"], timeout_retries=config.get("timeout_retries", 0))
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
