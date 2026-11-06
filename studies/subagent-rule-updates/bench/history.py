"""Turn VibeMemBench trajectories into conversation history for the worker and manager."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

RUN_COMMAND = "run_command"
MESSAGE_WORKER = "message_worker"
WORKER_NAME = "worker-1"
SUBMIT_MARKER = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
FALLBACK_CLOSING = "Task finished."

_RETURNCODE = re.compile(r"<returncode>\s*(-?\d+)\s*</returncode>")
_OUTPUT = re.compile(r"<output>\n?(.*?)</output>", re.S)
_PR = re.compile(r"<pr_description>\s*(.*?)\s*</pr_description>", re.S)
_PR_HEADER = "Consider the following PR description:"
_TESTBED = re.compile(r"/testbed(?![A-Za-z0-9_-])")
_BAD_ID_CHARS = re.compile(r"[^A-Za-z0-9_-]")
MAX_CALL_ID = 64


def load_trajectory(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    messages = data["messages"] if isinstance(data, dict) else data
    if not isinstance(messages, list):
        raise ValueError("trajectory has no message list: %s" % path)
    return messages


def _text(message: Dict[str, Any]) -> str:
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _commands(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return [{'id', 'command'}] for each bash tool call in an assistant message."""
    out = []
    for call in message.get("tool_calls") or []:
        try:
            args = json.loads(call["function"].get("arguments") or "{}")
        except (KeyError, TypeError, ValueError):
            continue
        command = args.get("command") if isinstance(args, dict) else None
        if isinstance(command, str) and command.strip():
            out.append({"id": call.get("id"), "command": command})
    return out


def safe_call_id(prefix: str, suffix: str = "") -> str:
    """A tool-call id in [A-Za-z0-9_-]{1,64}. The suffix (a counter) is kept whole so ids stay unique."""
    prefix = _BAD_ID_CHARS.sub("_", prefix)[:MAX_CALL_ID - len(suffix)]
    return (prefix + suffix) or "call"


def _rewrite(text: str, workdir: Optional[str]) -> str:
    """Point the trajectory's /testbed checkout at the case's working directory."""
    return _TESTBED.sub(workdir, text) if workdir else text


def _observation(content: str, max_chars: int) -> str:
    code: Optional[int] = None
    match = _RETURNCODE.search(content)
    if match:
        code = int(match.group(1))
    out = _OUTPUT.search(content)
    output = out.group(1) if out else content
    if len(output) > max_chars:
        output = output[-max_chars:]
    return json.dumps({"exit_code": code, "output": output})


def _is_submit(commands: List[Dict[str, Any]]) -> bool:
    return any(SUBMIT_MARKER in c["command"] for c in commands)


def _split_final(raw: List[Dict[str, Any]]):
    """Return (steps, closing text). The final step is dropped when it is the submit step or has no command."""
    body = [m for m in raw if m.get("role") in ("user", "assistant", "tool")]
    last = max((i for i, m in enumerate(body) if m["role"] == "assistant"), default=None)
    if last is None:
        return body, FALLBACK_CLOSING
    cmds = _commands(body[last])
    if cmds and not _is_submit(cmds):
        return body, FALLBACK_CLOSING
    closing = _text(body[last]).strip() or FALLBACK_CLOSING
    return body[:last], closing


def to_worker_messages(raw: List[Dict[str, Any]], *, call_prefix: str, workdir: Optional[str] = None,
                       max_output_chars: int = 2000) -> List[Dict[str, Any]]:
    """Replay a trajectory as worker turns. The first user message is replaced by the bare problem
    statement, so mini-swe-agent's own instructions (submit protocol, which files to touch) never
    reach the worker. With workdir, /testbed is rewritten to it in every replayed message."""
    steps, closing = _split_final(raw)
    out: List[Dict[str, Any]] = []
    id_map: Dict[str, str] = {}
    counter = 0
    seen_user = False
    replied = {m.get("tool_call_id") for m in steps
               if m["role"] == "tool" and isinstance(m.get("tool_call_id"), str)}
    for m in steps:
        role = m["role"]
        if role == "user":
            if not seen_user:
                out.append({"role": "user", "content": _rewrite(_problem_statement(raw), workdir)})
                seen_user = True
        elif role == "assistant":
            cmds = _commands(m)
            text = _rewrite(_text(m), workdir)
            if not cmds:
                if text.strip():
                    out.append({"role": "assistant", "content": text})
                continue
            calls = []
            for c in cmds:
                if not isinstance(c["id"], str) or c["id"] not in replied:
                    continue
                replied.discard(c["id"])
                counter += 1
                new_id = safe_call_id(call_prefix, str(counter))
                id_map[c["id"]] = new_id
                calls.append({"id": new_id, "type": "function", "function": {
                    "name": RUN_COMMAND, "arguments": json.dumps({"command": _rewrite(c["command"], workdir)})}})
            if not calls:
                if text.strip():
                    out.append({"role": "assistant", "content": text})
                continue
            out.append({"role": "assistant", "content": text, "tool_calls": calls})
        elif role == "tool":
            new_id = id_map.pop(m.get("tool_call_id"), None)
            if new_id is not None:
                out.append({"role": "tool", "tool_call_id": new_id,
                            "content": _observation(_rewrite(_text(m), workdir), max_output_chars)})
    out.append({"role": "assistant", "content": _rewrite(closing, workdir)})
    return out


def manager_block(problem_statement: str, worker_reply: str, call_id: str) -> List[Dict[str, Any]]:
    return [
        {"role": "user", "content": problem_statement},
        {"role": "assistant", "content": "", "tool_calls": [{
            "id": call_id, "type": "function",
            "function": {"name": MESSAGE_WORKER, "arguments": json.dumps({"message": problem_statement})}}]},
        {"role": "tool", "tool_call_id": call_id,
         "content": json.dumps({"worker": WORKER_NAME, "status": "finished", "reply": worker_reply})},
        {"role": "assistant", "content": "Done."},
    ]


@dataclass
class FillerBlock:
    instance_id: str
    manager: List[Dict[str, Any]]
    worker: List[Dict[str, Any]]


def _problem_statement(raw: List[Dict[str, Any]]) -> str:
    first = next((_text(m) for m in raw if m.get("role") == "user"), "")
    match = _PR.search(first)
    if not match:
        return first
    text = match.group(1)
    if text.startswith(_PR_HEADER):
        text = text[len(_PR_HEADER):].lstrip("\n")
    return text.strip()


def filler_block(instance_id: str, raw: List[Dict[str, Any]], *, workdir: str) -> FillerBlock:
    worker = to_worker_messages(raw, call_prefix="%s-" % instance_id, workdir=workdir)
    reply = worker[-1]["content"]
    manager = manager_block(_rewrite(_problem_statement(raw), workdir), reply, safe_call_id("mgr-%s" % instance_id))
    return FillerBlock(instance_id=instance_id, manager=manager, worker=worker)
