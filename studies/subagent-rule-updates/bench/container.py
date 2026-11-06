"""Docker-backed workspace for SWE-rebench V2 task containers.

Worker agents get read_file, write_file, and run_command inside the container.
The Runner protocol keeps docker out of the unit tests.
"""
from __future__ import annotations

import codecs
import copy
import json
import os
import subprocess
import threading
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from bench.history import RUN_COMMAND
from bench.rules import Changes

MAX_FILE_BYTES = 65536
TIMEOUT_EXIT = 124
CHANGES_CAP = 1 << 20
LISTING_CAP = 4 << 20
KILL_GRACE = 5
HOST_SLACK = 15


class _Tail:
    """Keeps only the last `cap` characters of a stream."""

    def __init__(self, cap: int):
        self.cap = max(cap, 1)
        self.text = ""

    def add(self, chunk: str) -> None:
        self.text += chunk
        if len(self.text) > 2 * self.cap:
            self.text = self.text[-self.cap:]

    def value(self) -> str:
        return self.text[-self.cap:]


def _drain(stream: Any, tail: _Tail) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    while True:
        chunk = stream.read1(65536) if hasattr(stream, "read1") else stream.read(65536)
        if not chunk:
            break
        tail.add(decoder.decode(chunk))
    tail.add(decoder.decode(b"", final=True))


class DockerRunner:
    """Runs docker through subprocess. A timeout returns exit code 124.

    Output is read incrementally and only the last `max_output` characters of each
    stream are kept (per-call argument, else the runner default). Line endings are
    not translated.
    """

    def __init__(self, max_output: int = 10000):
        self.max_output = max_output

    def run(self, args: List[str], *, input: Optional[str] = None, timeout: int,
            max_output: Optional[int] = None) -> Tuple[int, str, str]:
        cap = max_output or self.max_output
        out, err = _Tail(cap), _Tail(cap)
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def feed() -> None:
            try:
                if input is not None:
                    proc.stdin.write(input.encode("utf-8"))
            except OSError:
                pass
            finally:
                try:
                    proc.stdin.close()
                except OSError:
                    pass

        threads = [threading.Thread(target=t, daemon=True) for t in
                   (feed, lambda: _drain(proc.stdout, out), lambda: _drain(proc.stderr, err))]
        for t in threads:
            t.start()
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            code = TIMEOUT_EXIT
        for t in threads:
            t.join(5)
        for stream in (proc.stdout, proc.stderr):
            stream.close()
        return code, out.value(), err.value()


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
                 command_timeout: int = 120, max_output_chars: int = 10000, network: Optional[str] = None):
        self.image = image
        self.network = network  # Passed to docker run --network when set, e.g. "none".
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
        args = ["docker", "run", "-d", "--rm"] + (["--network", self.network] if self.network else [])
        code, out, err = self.runner.run(args + [self.image, "sleep", "infinity"], timeout=300)
        if code != 0 or not out.strip():
            raise RuntimeError("docker run failed (%s): %s" % (code, err.strip()))
        self.container_id = out.strip().splitlines()[-1]

    def stop(self) -> None:
        if self.container_id is None:
            return
        self.runner.run(["docker", "rm", "-f", self.container_id], timeout=60)
        self.container_id = None

    def _exec(self, cmd: List[str], *, input: Optional[str] = None, timeout: Optional[int] = None,
              interactive: bool = False, cwd: Optional[str] = None,
              max_output: Optional[int] = None) -> Tuple[int, str, str]:
        args = ["docker", "exec"]
        if interactive:
            args.append("-i")
        if cwd:
            args += ["-w", cwd]
        args.append(str(self.container_id))
        return self.runner.run(args + cmd, input=input, timeout=timeout or self.command_timeout,
                               max_output=max_output)

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
                    code, before, _ = self._exec(["cat", absolute], max_output=CHANGES_CAP)
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
        code, out, _ = self._exec(["cat", absolute], max_output=MAX_FILE_BYTES + 1)
        if code != 0:
            raise ValueError("No such file")
        if len(out.encode()) > MAX_FILE_BYTES:
            raise ValueError("File exceeds 64 KiB limit")
        if "�" in out:
            raise ValueError("File is not valid UTF-8")
        return {"content": out}

    def _run_command(self, command: str) -> dict:
        wrapped = ["timeout", "-k", str(KILL_GRACE), str(self.command_timeout), "bash", "-lc", command]
        code, out, err = self._exec(wrapped, cwd=self.workdir, timeout=self.command_timeout + HOST_SLACK,
                                    max_output=self.max_output_chars + 1)
        timed_out = code == TIMEOUT_EXIT
        if timed_out:
            # Backstop: kill everything except pid 1 in case the process outlived the timeout.
            self._exec(["sh", "-c", "kill -9 -1"], timeout=30, max_output=1000)
        text = out + err
        truncated = len(text) > self.max_output_chars
        if truncated:
            text = text[-self.max_output_chars:]
        return {"exit_code": code, "output": text, "timed_out": timed_out, "truncated": truncated}

    def _git(self, *args: str, cap: int = CHANGES_CAP) -> Tuple[int, str, str]:
        return self._exec(["git", "-C", self.workdir] + list(args), max_output=cap)

    def changes(self, base_commit: str, *, exclude: frozenset = frozenset()) -> Changes:
        """Files changed against base_commit, including untracked ones: path -> (base, final)."""
        if self.container_id is None:
            raise RuntimeError("Container not started")
        code, out, err = self._git("diff", "--no-renames", "--name-status", "-z", base_commit, cap=LISTING_CAP)
        if code != 0:
            raise RuntimeError("git diff failed: " + err.strip())
        entries: Dict[str, str] = {}
        tokens = out.split("\0")
        for i in range(0, len(tokens) - 1, 2):
            if tokens[i] and tokens[i + 1]:
                entries[tokens[i + 1]] = tokens[i][0]
        code, out, err = self._git("ls-files", "--others", "--exclude-standard", "-z", cap=LISTING_CAP)
        if code != 0:
            raise RuntimeError("git ls-files failed: " + err.strip())
        for line in out.split("\0"):
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
                code, text, _ = self._exec(["cat", self.workdir + "/" + path], max_output=CHANGES_CAP)
                if code == 0:
                    final = text
            if any(t is not None and len(t) >= CHANGES_CAP for t in (base, final)):
                continue
            if any(t is not None and ("\x00" in t or "�" in t) for t in (base, final)):
                continue
            if base is None and final is None:
                continue
            result[path] = (base, final)
        return result
