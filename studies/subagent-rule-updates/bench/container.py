"""Docker-backed workspace for SWE-rebench V2 task containers.

Worker agents get read_file, write_file, and run_command inside the container.
The Runner protocol keeps docker out of the unit tests.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from bench.history import RUN_COMMAND
from bench.rules import Changes

MAX_FILE_BYTES = 65536
TIMEOUT_EXIT = 124


class DockerRunner:
    """Runs docker through subprocess. A timeout returns exit code 124."""

    def run(self, args: List[str], *, input: Optional[str] = None, timeout: int) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(args, input=input, capture_output=True, text=True,
                                  errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            def _text(v):
                return v.decode("utf-8", "replace") if isinstance(v, bytes) else (v or "")
            return TIMEOUT_EXIT, _text(exc.stdout), _text(exc.stderr)
        return proc.returncode, proc.stdout, proc.stderr


def _tool(name: str, description: str, fields: dict) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": fields, "required": list(fields),
                           "additionalProperties": False}}}


TOOLS = [
    _tool("read_file", "Read a UTF-8 file. Paths are relative to the repository root.", {"path": {"type": "string"}}),
    _tool("write_file", "Write the full UTF-8 contents of a file, creating it and its folders if needed.",
          {"path": {"type": "string"}, "content": {"type": "string"}}),
    _tool(RUN_COMMAND, "Run a bash command in the repository root and return its exit code and output.",
          {"command": {"type": "string"}}),
]
TOOL_FIELDS = {t["function"]["name"]: set(t["function"]["parameters"]["required"]) for t in TOOLS}

_WRITE_SCRIPT = 'mkdir -p "$(dirname "$1")" && cat > "$1"'


class ContainerWorkspace:
    def __init__(self, image: str, runner: Any, *, workdir: str, event_log: Optional[Path] = None,
                 command_timeout: int = 120, max_output_chars: int = 10000):
        self.image = image
        self.runner = runner
        self.workdir = workdir.rstrip("/")
        self.event_log = event_log
        self.command_timeout = command_timeout
        self.max_output_chars = max_output_chars
        self.container_id: Optional[str] = None
        self.events: List[dict] = []
        if event_log is not None:
            event_log.parent.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        code, out, err = self.runner.run(["docker", "run", "-d", "--rm", self.image, "sleep", "infinity"],
                                         timeout=300)
        if code != 0 or not out.strip():
            raise RuntimeError("docker run failed (%s): %s" % (code, err.strip()))
        self.container_id = out.strip().splitlines()[-1]

    def stop(self) -> None:
        if self.container_id is None:
            return
        self.runner.run(["docker", "rm", "-f", self.container_id], timeout=60)
        self.container_id = None

    def _exec(self, cmd: List[str], *, input: Optional[str] = None, timeout: Optional[int] = None,
              interactive: bool = False, cwd: Optional[str] = None) -> Tuple[int, str, str]:
        args = ["docker", "exec"]
        if interactive:
            args.append("-i")
        if cwd:
            args += ["-w", cwd]
        args.append(str(self.container_id))
        return self.runner.run(args + cmd, input=input, timeout=timeout or self.command_timeout)

    def _rel(self, name: str) -> str:
        rel = PurePosixPath(name)
        if not name or rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Expected a relative path without ..")
        return rel.as_posix()

    def _resolve(self, rel: str) -> str:
        """Absolute path in the container, rejecting symlink escapes from workdir."""
        absolute = self.workdir + "/" + rel
        code, out, _ = self._exec(["realpath", "-m", absolute])
        real = out.strip()
        if code != 0 or not (real.startswith(self.workdir + "/")):
            raise ValueError("Path escapes the repository")
        return absolute

    def execute(self, name: str, args: Any, *, call_index: int) -> dict:
        event: Dict[str, Any] = {"sequence": len(self.events), "call_index": call_index,
                                 "tool": name, "arguments": copy.deepcopy(args)}
        try:
            if self.container_id is None:
                raise ValueError("Container not started")
            if name not in TOOL_FIELDS or not isinstance(args, dict) or set(args) != TOOL_FIELDS[name]:
                raise ValueError("Unknown tool or wrong argument fields")
            if any(not isinstance(v, str) for v in args.values()):
                raise ValueError("Tool arguments must be strings")
            if name == RUN_COMMAND:
                result = self._run_command(args["command"])
            else:
                rel = self._rel(args["path"])
                event["path"] = rel
                if name == "read_file":
                    result = self._read(self._resolve(rel))
                else:
                    if len(args["content"].encode()) > MAX_FILE_BYTES:
                        raise ValueError("File exceeds 64 KiB limit")
                    absolute = self._resolve(rel)
                    code, before, _ = self._exec(["cat", absolute])
                    event["before"] = before if code == 0 else None
                    code, _, err = self._exec(["sh", "-c", _WRITE_SCRIPT, "sh", absolute],
                                              input=args["content"], interactive=True)
                    if code != 0:
                        raise ValueError("Write failed: " + err.strip()[-500:])
                    result = {"written": rel, "bytes": len(args["content"].encode())}
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

    def _read(self, absolute: str) -> dict:
        code, out, _ = self._exec(["cat", absolute])
        if code != 0:
            raise ValueError("No such file")
        if len(out.encode()) > MAX_FILE_BYTES:
            raise ValueError("File exceeds 64 KiB limit")
        if "�" in out:
            raise ValueError("File is not valid UTF-8")
        return {"content": out}

    def _run_command(self, command: str) -> dict:
        code, out, err = self._exec(["bash", "-lc", command], cwd=self.workdir)
        text = out + err
        truncated = len(text) > self.max_output_chars
        if truncated:
            text = text[-self.max_output_chars:]
        return {"exit_code": code, "output": text, "timed_out": code == TIMEOUT_EXIT, "truncated": truncated}

    def _git(self, *args: str) -> Tuple[int, str, str]:
        return self._exec(["git", "-C", self.workdir] + list(args))

    def changes(self, base_commit: str, *, exclude: frozenset = frozenset()) -> Changes:
        """Files changed against base_commit, including untracked ones: path -> (base, final)."""
        if self.container_id is None:
            raise RuntimeError("Container not started")
        code, out, err = self._git("diff", "--no-renames", "--name-status", base_commit)
        if code != 0:
            raise RuntimeError("git diff failed: " + err.strip())
        entries: Dict[str, str] = {}
        for line in out.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2 and parts[0]:
                entries[parts[1]] = parts[0][0]
        code, out, err = self._git("ls-files", "--others", "--exclude-standard")
        if code != 0:
            raise RuntimeError("git ls-files failed: " + err.strip())
        for line in out.splitlines():
            if line:
                entries.setdefault(line, "U")
        result: Changes = {}
        for path in sorted(entries):
            if path in exclude:
                continue
            status = entries[path]
            base: Optional[str] = None
            final: Optional[str] = None
            if status != "A" and status != "U":
                code, text, _ = self._git("show", "%s:%s" % (base_commit, path))
                if code == 0:
                    base = text
            if status != "D":
                code, text, _ = self._exec(["cat", self.workdir + "/" + path])
                if code == 0:
                    final = text
            if any(t is not None and ("\x00" in t or "�" in t) for t in (base, final)):
                continue
            if base is None and final is None:
                continue
            result[path] = (base, final)
        return result
