"""A generic tool-using coding worker over a local fixture workspace.

The original harness.py stays frozen so earlier runs reproduce. This module holds
the scenario-independent worker used by the second experiment series. No provider
calls happen on import; the client is injected.
"""
from __future__ import annotations

import copy
import json
import os
import time
from pathlib import Path
from typing import Any

WORKER_SYSTEM = """You are a coding agent working in a small Python repository. Use the tools to inspect and change files. File writes really execute. There is no shell, so you cannot run tests or commands.

Finish with a short summary of what you changed."""

MAX_FILE_BYTES = 65536


def _tool(name: str, description: str, fields: dict) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}}}


TOOLS = [
    _tool("list_files", "List every file in the repository.", {}),
    _tool("read_file", "Read a UTF-8 file. Paths are relative to the repository root.", {"path": {"type": "string"}}),
    _tool("write_file", "Write the full UTF-8 contents of a file, creating it and its folders if needed.",
          {"path": {"type": "string"}, "content": {"type": "string"}}),
]
TOOL_FIELDS = {t["function"]["name"]: set(t["function"]["parameters"]["required"]) for t in TOOLS}


class Workspace:
    """Executes every tool call against a real directory and logs it."""

    def __init__(self, root: Path, fixture: dict[str, str], event_log: Path | None = None):
        self.root = Path(root).resolve()
        self.event_log = event_log
        if self.root.exists() and any(self.root.iterdir()):
            raise ValueError("Workspace must start empty")
        for name, content in fixture.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.root.mkdir(parents=True, exist_ok=True)
        if event_log is not None:
            event_log.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []

    def snapshot(self) -> dict[str, str]:
        return {p.relative_to(self.root).as_posix(): p.read_text() for p in sorted(self.root.rglob("*")) if p.is_file()}

    def _path(self, name: str) -> Path:
        rel = Path(name)
        if not name or rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Expected a relative path without ..")
        dest = (self.root / rel).resolve()
        if not dest.is_relative_to(self.root) or dest == self.root:
            raise ValueError("Path escapes the repository")
        if any(p.is_symlink() for p in [self.root / rel, *(self.root / rel).parents] if p.is_relative_to(self.root)):
            raise ValueError("Symlinks are not allowed")
        return dest

    def execute(self, name: str, args: Any, *, call_index: int) -> dict:
        event = {"sequence": len(self.events), "call_index": call_index, "tool": name, "arguments": copy.deepcopy(args)}
        try:
            if name not in TOOL_FIELDS or not isinstance(args, dict) or set(args) != TOOL_FIELDS[name]:
                raise ValueError("Unknown tool or wrong argument fields")
            if any(not isinstance(v, str) for v in args.values()):
                raise ValueError("Tool arguments must be strings")
            if name == "list_files":
                result = {"files": sorted(self.snapshot())}
            else:
                path = self._path(args["path"])
                event["path"] = path.relative_to(self.root).as_posix()
                if name == "read_file":
                    if not path.is_file():
                        raise ValueError("No such file")
                    result = {"content": path.read_text()}
                else:
                    if len(args["content"].encode()) > MAX_FILE_BYTES:
                        raise ValueError("File exceeds 64 KiB limit")
                    event["before"] = path.read_text() if path.is_file() else None
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(args["content"])
                    result = {"written": event["path"], "bytes": len(args["content"].encode())}
        except (ValueError, OSError, UnicodeError) as exc:
            result = {"error": str(exc)}
        event["result"] = result
        self.events.append(event)
        if self.event_log is not None:
            with self.event_log.open("a") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        return result


def run_worker(client: Any, system: str, history: list[dict], workspace: Workspace, message: str, *,
               tag: str, max_calls: int = 12) -> dict:
    """Append one user message and run the tool loop until the worker answers without tools."""
    history = copy.deepcopy(history) + [{"role": "user", "content": message}]
    started = time.monotonic()
    responses, status, error = [], "call_limit", None
    for i in range(max_calls):
        try:
            response = client.complete([{"role": "system", "content": system}] + copy.deepcopy(history), tools=TOOLS, tag=f"{tag}/call{i}")
        except Exception as exc:
            status, error = "provider_error", f"{type(exc).__name__}: {exc}"
            break
        responses.append({"call_index": i, "id": response.get("id"), "usage": response.get("usage")})
        choices = response.get("choices") or []
        if not choices or not isinstance(choices[0].get("message"), dict):
            status, error = "model_protocol_error", "Missing assistant message"
            break
        choice, raw = choices[0], choices[0]["message"]
        msg = {k: copy.deepcopy(raw[k]) for k in ("content", "tool_calls", "reasoning_details", "reasoning") if k in raw}
        msg["role"] = "assistant"
        calls = msg.get("tool_calls") or []
        if choice.get("finish_reason") in ("length", "content_filter", "error"):
            status, error = "model_protocol_error", f"Incomplete response: {choice.get('finish_reason')}"
            break
        if not calls:
            if not isinstance(msg.get("content"), str) or not msg["content"].strip():
                status, error = "model_protocol_error", "Empty final response"
                break
            history.append(msg)
            status = "finished"
            break
        try:
            parsed, seen = [], set()
            for call in calls:
                if not isinstance(call.get("id"), str) or not call["id"] or call["id"] in seen or call.get("type") != "function":
                    raise ValueError("Missing, repeated, or unsupported tool call")
                seen.add(call["id"])
                parsed.append((call["id"], call["function"]["name"], json.loads(call["function"]["arguments"] or "{}")))
        except (TypeError, KeyError, ValueError) as exc:
            status, error = "model_protocol_error", str(exc)
            break
        history.append(msg)
        for call_id, name, args in parsed:
            result = workspace.execute(name, args, call_index=i)
            history.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result)})
    return {"status": status, "error": error, "history": history, "responses": responses,
            "wallclock_seconds": time.monotonic() - started, "events": copy.deepcopy(workspace.events), "files": workspace.snapshot()}
