"""Session engine for the rule-change benchmark: one case run under one cell.

A scripted user talks to a real manager model that delegates to a persistent worker,
worker-1, through message_worker. U0 gives both original rules and the first task, U1
changes one rule, real trajectories from the same repository are appended as history and
compacted where the cell's placement says, and U2 gives the second task without restating
the rules. The second task's final files are scored for both rules and against the task's
tests. No provider calls happen on import; the client is injected.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

import compaction as C
import harness as H
import pi_compaction as PI
import relay as R
import worker as W

from bench.cases import Case
from bench.container import TOOLS as WORKER_TOOLS, ContainerWorkspace
from bench.evaluate import score_tests, test_patch_paths
from bench.history import MESSAGE_WORKER, WORKER_NAME, filler_block, load_trajectory
from bench.rules import RuleSpec, classify
from bench.sources import TaskRow, issue_number


@dataclass(frozen=True)
class Cell:
    condition: str
    placement: str
    worker_type: str


CELLS = tuple(
    [Cell(c, p, "existing") for c in ("relay", "reinsert", "store") for p in ("none", "manager", "worker", "both")]
    + [Cell(c, p, "new") for c in ("relay", "creation_pin", "store") for p in ("none", "manager")]
    + [Cell("no_change", "none", "existing")])

# Held fixed in every cell. Conditions differ only in what the harness adds.
MANAGER_SYSTEM = R.MANAGER_SYSTEM + "\n\nPass on any user instructions the worker needs."
MANAGER_TOOLS = R.MANAGER_TOOLS
BENCH_WORKER_SYSTEM = """You are a coding agent working in a software repository. Use the tools to inspect and change it: read_file and write_file for files, and run_command for shell commands such as searching the code or running tests. File writes and commands really execute.

Finish with a short summary of what you changed."""
RULES_OPEN = "[Current project rules from the user, supplied by the harness]"
RULES_CLOSE = "[/Current project rules]"
PLACEMENT_HISTORIES = {"none": (), "manager": ("manager",), "worker": (WORKER_NAME,), "both": ("manager", WORKER_NAME)}


class ProviderError(RuntimeError):
    """A model request raised. The cell stops and is never scored."""


class CompactionError(RuntimeError):
    """The summarizer answered but gave no complete summary. The cell stops and is never scored."""


def cell_id(cell: Cell) -> str:
    return "%s__%s__%s" % (cell.condition, cell.placement, cell.worker_type)


def rule_order(case: Case) -> List[str]:
    """Rules are numbered by id, so the order does not reveal which rule will change."""
    return sorted((case.changed_rule, case.unchanged_rule))


def current_rules(case: Case, rules: Dict[str, RuleSpec], changed: bool) -> str:
    return "\n".join("%d. %s" % (i, rules[rid].changed if changed and rid == case.changed_rule else rules[rid].original)
                     for i, rid in enumerate(rule_order(case), 1))


def with_rules(system: str, case: Case, rules: Dict[str, RuleSpec], changed: bool) -> str:
    return "%s\n\n%s\n%s\n%s" % (system, RULES_OPEN, current_rules(case, rules, changed), RULES_CLOSE)


def user_turns(case: Case, rules: Dict[str, RuleSpec], rows: Dict[str, TaskRow], *, change: bool = True) -> List[str]:
    """[U0, U1, U2], or [U0, U2] for the no-change control. Byte-identical across cells."""
    u0 = "Two project rules for this session:\n%s\n\nFirst task: %s" % (
        current_rules(case, rules, False), rows[case.first].problem_statement)
    u1 = "A change to one of my rules, effective now: %s" % rules[case.changed_rule].changed
    u2 = "Next task: %s" % rows[case.second].problem_statement
    return [u0, u1, u2] if change else [u0, u2]


class RecordingClient:
    """Records a context hash for every request and turns provider failures into ProviderError."""

    def __init__(self, client: Any):
        self.client = client
        self.calls: List[dict] = []

    def complete(self, messages: List[dict], **kwargs: Any) -> dict:
        self.calls.append({"index": len(self.calls), "tag": kwargs.get("tag", ""), "context_hash": H.digest(messages),
                           "system_hash": H.digest(messages[0].get("content") if messages else None),
                           "messages": len(messages)})
        try:
            return self.client.complete(messages, **kwargs)
        except Exception as exc:
            raise ProviderError("%s: %s" % (type(exc).__name__, exc)) from exc


class Team:
    """Holds the session state: both histories, both system prompts, and the current workspace."""

    def __init__(self, client: RecordingClient, cell: Cell, case: Case, rules: Dict[str, RuleSpec], tag: str, config: dict):
        self.client, self.cell, self.case, self.rules, self.tag, self.config = client, cell, case, rules, tag, config
        self.manager_history: List[dict] = []
        self.worker_history: List[dict] = []
        self.worker_system = BENCH_WORKER_SYSTEM
        self.changed = False  # Whether the harness-side rule state has switched at U1.
        self.workspace: Optional[ContainerWorkspace] = None
        self.deliveries: List[dict] = []
        self.label = "U0"

    def store(self) -> bool:
        return self.cell.condition == "store"

    def manager_system(self) -> str:
        return with_rules(MANAGER_SYSTEM, self.case, self.rules, self.changed) if self.store() else MANAGER_SYSTEM

    def current_worker_system(self) -> str:
        if self.store():
            return with_rules(BENCH_WORKER_SYSTEM, self.case, self.rules, self.changed)
        return self.worker_system

    def execute(self, name: str, args: Any, call_index: int) -> dict:
        if name != MESSAGE_WORKER or not isinstance(args, dict) or set(args) != {"message"}:
            return {"error": "Unknown tool or wrong argument fields"}
        text = args["message"]
        if not isinstance(text, str) or not text.strip():
            return {"error": "Expected a nonempty message"}
        workspace = self.workspace
        first_event = len(workspace.events)
        system = self.current_worker_system()
        result = W.run_agent(self.client, system, self.worker_history, text, tools=WORKER_TOOLS,
                             execute=lambda n, a, i: workspace.execute(n, a, call_index=i),
                             tag="%s/t%s/%s/d%d" % (self.tag, self.label[1:], WORKER_NAME, len(self.deliveries)),
                             max_calls=self.config["max_worker_calls"])
        self.worker_history = result["history"]
        self.deliveries.append({"turn": self.label, "worker": WORKER_NAME, "text": text, "status": result["status"],
                                "error": result["error"], "system_hash": H.digest(system),
                                "events": [first_event, len(workspace.events)], "calls": len(result["responses"])})
        if result["status"] == "provider_error":
            raise ProviderError("Worker provider error: %s" % result["error"])
        return {"worker": WORKER_NAME, "status": result["status"], "reply": W.final_text(result["history"])}

    def run_turn(self, label: str, message: str) -> dict:
        self.label = label
        result = W.run_agent(self.client, self.manager_system(), self.manager_history, message, tools=MANAGER_TOOLS,
                             execute=self.execute, tag="%s/t%s/manager" % (self.tag, label[1:]),
                             max_calls=self.config["max_manager_calls"])
        self.manager_history = result["history"]
        return {"label": label, "user": message, "status": result["status"], "error": result["error"],
                "reply": W.final_text(result["history"]), "manager_calls": len(result["responses"])}


def threshold(config: dict, name: str) -> int:
    """Manager history uses manager_compact_threshold_chars when set; the worker uses compact_threshold_chars."""
    if name == "manager" and config.get("manager_compact_threshold_chars") is not None:
        return config["manager_compact_threshold_chars"]
    return config["compact_threshold_chars"]


def _summarize(team: Team, name: str, history: List[dict], compactor: str, tag: str,
               pi_states: Dict[str, PI.PiState]) -> tuple:
    """Return (history, event, skipped) from one compactor call."""
    if compactor == "generic":
        session = SimpleNamespace(history=history)
        event = C.compact(team.client, session, tag)
        return session.history, event, False
    if compactor == "pi":
        history, event = PI.compact(team.client, history, pi_states.setdefault(name, PI.PiState()), tag)
        return history, event, event["skipped"]
    raise ValueError("Unknown compactor: %r" % (compactor,))


def _compact(team: Team, name: str, after_block: int, pi_states: Dict[str, PI.PiState], u1: Optional[str], *,
             forced: bool = False) -> Optional[dict]:
    """Compact one history once it passes its threshold, or unconditionally when forced.

    A forced pi compaction that skips (the tail already fits) falls back to the generic compactor,
    so the placement's history is always really compacted; the event records forced_generic."""
    history = team.manager_history if name == "manager" else team.worker_history
    chars = len(C.render_history(history))
    if not forced and chars <= threshold(team.config, name):
        return None
    tag = "%s/compact/%s/b%d%s" % (team.tag, name, after_block, "/forced" if forced else "")
    compactor = team.config["compactor"]
    forced_generic = False
    try:
        new_history, event, skipped = _summarize(team, name, history, compactor, tag, pi_states)
        if forced and skipped:
            pi_cut = event.get("cut")
            new_history, event, skipped = _summarize(team, name, history, "generic", tag + "/generic", pi_states)
            event["pi_skipped_cut"] = pi_cut
            forced_generic = True
    except ProviderError:
        raise
    except (RuntimeError, KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise CompactionError("%s compaction failed: %s: %s" % (name, type(exc).__name__, exc)) from exc
    history = new_history
    reinserted = team.cell.condition == "reinsert" and not skipped and u1 is not None
    if reinserted:
        history = history + [{"role": "user", "content": u1}]
    if name == "manager":
        team.manager_history = history
    else:
        team.worker_history = history
    event.update({"history": name, "after_block": after_block, "compactor": compactor, "history_chars_before": chars,
                  "history_chars_after": len(C.render_history(history)), "reinserted": reinserted,
                  "history_after_hash": H.digest(history), "skipped": skipped, "forced": forced,
                  "forced_generic": forced_generic})
    return event


def add_history(team: Team, case: Case, trajectories: Dict[str, Dict[str, Path]], u1: Optional[str],
                workdir: str) -> List[dict]:
    """Append each filler block and compact the placement's histories once they pass their thresholds.

    After the last block, each placement-named history that never had a real compaction is
    compacted once anyway (forced), so a placement is never a no-op."""
    events: List[dict] = []
    pi_states: Dict[str, PI.PiState] = {}
    names = PLACEMENT_HISTORIES[team.cell.placement]
    for index, iid in enumerate(case.history):
        block = filler_block(iid, load_trajectory(trajectories[case.repo][iid]), workdir=workdir)
        team.manager_history = team.manager_history + copy.deepcopy(block.manager)
        team.worker_history = team.worker_history + copy.deepcopy(block.worker)
        for name in names:
            event = _compact(team, name, index, pi_states, u1)
            if event is not None:
                events.append(event)
    done = {e["history"] for e in events if not e["skipped"]}
    for name in names:
        if name not in done:
            events.append(_compact(team, name, len(case.history) - 1, pi_states, u1, forced=True))
    return events


def reset_worker(team: Team) -> dict:
    """New-worker cells: worker-1 restarts with an empty history. The manager is not told."""
    before = len(team.worker_history)
    team.worker_history = []
    if team.cell.condition == "creation_pin":
        team.worker_system = with_rules(BENCH_WORKER_SYSTEM, team.case, team.rules, team.changed)
    return {"history_messages_before": before, "system": team.current_worker_system()}


def score(ws: ContainerWorkspace, case: Case, rules: Dict[str, RuleSpec], row: TaskRow) -> dict:
    changes = ws.changes(row.base_commit, exclude=frozenset(test_patch_paths(row.test_patch)))
    issue = issue_number(row.instance_id)
    outcomes = {"changed": {"rule": case.changed_rule, **classify(rules[case.changed_rule], changes, issue=issue)},
                "unchanged": {"rule": case.unchanged_rule, **classify(rules[case.unchanged_rule], changes, issue=issue)}}
    ws.open_network()
    return {"rules": outcomes, "changed_paths": sorted(changes), "tests": score_tests(ws, row)}


def _run_task(team: Team, ws: ContainerWorkspace, turns: List[dict], labelled: List[tuple]) -> bool:
    """Run user turns in one workspace. True when every manager turn finished."""
    team.workspace = ws
    for label, message in labelled:
        if label == "U1":
            team.changed = True
        turn = team.run_turn(label, message)
        turn["workspace_events"] = len(ws.events)
        turns.append(turn)
        if turn["status"] != "finished":
            return False
    return True


def _failed(turn: dict) -> str:
    return "provider_error" if turn["status"] == "provider_error" else "manager_%s" % turn["status"]


def run_cell(client: Any, case: Case, cell: Cell, *, rules: Dict[str, RuleSpec], rows: Dict[str, TaskRow],
             trajectories: Dict[str, Dict[str, Path]], outdir: Path, config: dict,
             workspace_factory: Callable[[TaskRow, Path], ContainerWorkspace]) -> dict:
    """Run one case under one cell. trajectories maps repo -> instance id -> trajectory path."""
    if cell not in CELLS:
        raise ValueError("Unknown cell: %r" % (cell,))
    outdir = Path(outdir)
    recorder = RecordingClient(client)
    team = Team(recorder, cell, case, rules, "%s/%s" % (case.case_id, cell_id(cell)), config)
    texts = user_turns(case, rules, rows, change=cell.condition != "no_change")
    labels = ["U0", "U1", "U2"] if len(texts) == 3 else ["U0", "U2"]
    labelled = list(zip(labels, texts))
    u1 = texts[1] if len(texts) == 3 else None
    record: Dict[str, Any] = {"case_id": case.case_id, "cell": asdict(cell), "status": "running",
                              "manager_system": MANAGER_SYSTEM, "worker_system": BENCH_WORKER_SYSTEM,
                              "user_turns": texts, "turns": [], "compactions": [], "config": {
                                  k: config.get(k) for k in ("compact_threshold_chars", "manager_compact_threshold_chars",
                                                             "compactor", "max_manager_calls", "max_worker_calls",
                                                             "container_network", "scoring_network")}}
    status = "finished"
    try:
        ws = workspace_factory(rows[case.first], outdir / "task1")
        try:
            ws.start()
            ok = _run_task(team, ws, record["turns"], labelled[:-1])
        finally:
            ws.stop()
        if not ok:
            status = _failed(record["turns"][-1])
        else:
            record["compactions"] = add_history(team, case, trajectories, u1, rows[case.first].workdir)
            if cell.worker_type == "new":
                record["worker_reset"] = reset_worker(team)
            ws = workspace_factory(rows[case.second], outdir / "task2")
            try:
                ws.start()
                ok = _run_task(team, ws, record["turns"], labelled[-1:])
                if ok:
                    record.update(score(ws, case, rules, rows[case.second]))
            finally:
                ws.stop()
            if not ok:
                status = _failed(record["turns"][-1])
    except ProviderError as exc:
        status, record["error"] = "provider_error", str(exc)
    except CompactionError as exc:
        status, record["error"] = "compaction_error", str(exc)
    except Exception as exc:  # Containers, git, trajectories: record it unscored and let the runner decide.
        status, record["error"] = "infra_error", "%s: %s" % (type(exc).__name__, exc)
    if status != "finished":
        record.pop("rules", None)
        record.pop("tests", None)
    record.update(delegation_flags(team.deliveries))
    record.update({"status": status, "deliveries": team.deliveries, "calls": recorder.calls,
                   "manager_system_final": team.manager_system(), "worker_system_final": team.current_worker_system(),
                   "manager_history": team.manager_history, "worker_history": team.worker_history})
    R.save(outdir / "record.json", record)
    return record


def delegation_flags(deliveries: List[dict]) -> dict:
    """Whether the manager delegated U0 and U2, and whether the worker finished its last U2 delivery."""
    u2 = [d for d in deliveries if d["turn"] == "U2"]
    return {"u0_delegated": any(d["turn"] == "U0" for d in deliveries), "u2_delegated": bool(u2),
            "u2_worker_finished": bool(u2) and u2[-1]["status"] == "finished"}


def _outcomes(record: dict) -> Optional[tuple]:
    rules = record.get("rules") if record.get("status") == "finished" else None
    if not rules:
        return None
    return rules["changed"]["outcome"], rules["unchanged"]["outcome"]


def headline_pass(record: dict) -> bool:
    """Changed rule followed in its new version and unchanged rule kept. Not defined for no_change."""
    if record.get("cell", {}).get("condition") == "no_change":
        return False
    return _outcomes(record) == ("new", "old")


def control_pass(record: dict) -> bool:
    """The no_change control: both rules still followed in their original version."""
    return record.get("cell", {}).get("condition") == "no_change" and _outcomes(record) == ("old", "old")

