from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench import container
from bench.container import ContainerWorkspace

WD = "/requests"


class FakeRunner:
    def __init__(self, script=None):
        self.calls = []
        self.script = script or (lambda args, input: (0, "", ""))

    def run(self, args, *, input=None, timeout):
        self.calls.append({"args": list(args), "input": input, "timeout": timeout})
        if args[:2] == ["docker", "run"]:
            return 0, "cid123\n", ""
        return self.script(args, input)


def make(script=None, **kw):
    runner = FakeRunner(script)
    ws = ContainerWorkspace("img:1", runner, workdir=WD, **kw)
    ws.start()
    runner.calls.clear()
    return ws, runner


class ContainerTest(unittest.TestCase):
    def test_start_stop(self):
        runner = FakeRunner()
        ws = ContainerWorkspace("img:1", runner, workdir=WD)
        ws.start()
        self.assertEqual(runner.calls[0]["args"], ["docker", "run", "-d", "--rm", "img:1", "sleep", "infinity"])
        ws.stop()
        self.assertEqual(runner.calls[1]["args"], ["docker", "rm", "-f", "cid123"])

    def test_execute_before_start_errors(self):
        ws = ContainerWorkspace("img:1", FakeRunner(), workdir=WD)
        self.assertIn("error", ws.execute("run_command", {"command": "ls"}, call_index=0))

    def test_unsafe_paths_make_no_docker_call(self):
        ws, runner = make()
        for path in ("../etc/passwd", "", "a/../../b"):
            self.assertIn("error", ws.execute("read_file", {"path": path}, call_index=0))
        self.assertIn("error", ws.execute("write_file", {"path": "/abs", "content": "x"}, call_index=1))
        self.assertEqual(runner.calls, [])

    def test_bad_args_and_unknown_tool(self):
        ws, runner = make()
        self.assertIn("error", ws.execute("nope", {}, call_index=0))
        self.assertIn("error", ws.execute("read_file", {"path": 3}, call_index=0))
        self.assertIn("error", ws.execute("read_file", {}, call_index=0))
        self.assertEqual(runner.calls, [])

    def test_symlink_escape_rejected(self):
        def script(args, input):
            if "realpath" in args:
                return 0, "/etc/passwd\n", ""
            return 0, "secret", ""
        ws, runner = make(script)
        self.assertIn("error", ws.execute("read_file", {"path": "link"}, call_index=0))
        self.assertIn("error", ws.execute("write_file", {"path": "link", "content": "x"}, call_index=1))
        self.assertEqual(len(runner.calls), 2)
        self.assertTrue(all("realpath" in c["args"] for c in runner.calls))

    def test_read_file(self):
        def script(args, input):
            if "realpath" in args:
                return 0, WD + "/a.py\n", ""
            return 0, "print(1)\n", ""
        ws, runner = make(script)
        self.assertEqual(ws.execute("read_file", {"path": "a.py"}, call_index=0), {"content": "print(1)\n"})
        self.assertEqual(ws.events[0]["path"], "a.py")

    def test_read_file_too_large(self):
        def script(args, input):
            if "realpath" in args:
                return 0, WD + "/a.py\n", ""
            return 0, "x" * 70000, ""
        ws, _ = make(script)
        self.assertIn("error", ws.execute("read_file", {"path": "a.py"}, call_index=0))

    def test_write_file_uses_input(self):
        def script(args, input):
            if "realpath" in args:
                return 0, WD + "/pkg/new.py\n", ""
            if input is None and "cat" in args:
                return 0, "old", ""
            return 0, "", ""
        ws, runner = make(script)
        res = ws.execute("write_file", {"path": "pkg/new.py", "content": "hello"}, call_index=0)
        self.assertEqual(res["written"], "pkg/new.py")
        writes = [c for c in runner.calls if c["input"] == "hello"]
        self.assertEqual(len(writes), 1)
        self.assertNotIn("hello", writes[0]["args"])
        self.assertEqual(writes[0]["args"][:5], ["docker", "exec", "-i", "cid123", "sh"])
        self.assertEqual(writes[0]["args"][-1], WD + "/pkg/new.py")
        self.assertEqual(ws.events[0]["before"], "old")

    def test_write_file_too_large(self):
        ws, runner = make()
        self.assertIn("error", ws.execute("write_file", {"path": "a", "content": "x" * 70000}, call_index=0))
        self.assertEqual(runner.calls, [])

    def test_run_command_timeout(self):
        ws, runner = make(lambda a, i: (124, "partial", ""), command_timeout=7)
        res = ws.execute("run_command", {"command": "sleep 99"}, call_index=0)
        self.assertEqual(res["exit_code"], 124)
        self.assertTrue(res["timed_out"])
        self.assertEqual(runner.calls[0]["timeout"], 7)
        self.assertEqual(runner.calls[0]["args"], ["docker", "exec", "-w", WD, "cid123", "bash", "-lc", "sleep 99"])

    def test_run_command_truncates_to_tail(self):
        out = "a" * 40000 + "b" * 10000
        ws, _ = make(lambda a, i: (0, out, ""))
        res = ws.execute("run_command", {"command": "x"}, call_index=0)
        self.assertTrue(res["truncated"])
        self.assertEqual(res["output"], "b" * 10000)
        self.assertFalse(res["timed_out"])

    def test_event_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "sub" / "e.jsonl"
            ws, _ = make(lambda a, i: (0, "ok", ""), event_log=log)
            ws.execute("run_command", {"command": "x"}, call_index=3)
            ev = json.loads(log.read_text().splitlines()[0])
            self.assertEqual((ev["sequence"], ev["call_index"], ev["tool"]), (0, 3, "run_command"))

    def test_changes(self):
        files = {"m.py": "new m", "added.py": "add", "untracked.txt": "u", "skip.txt": "s"}
        base = {"m.py": "old m", "gone.py": "bye", "skip.txt": "s0"}

        def script(args, input):
            if "diff" in args:
                return 0, "M\tm.py\nD\tgone.py\nA\tadded.py\nM\tskip.txt\n", ""
            if "ls-files" in args:
                return 0, "untracked.txt\n", ""
            if "show" in args:
                p = args[-1].split(":", 1)[1]
                return (0, base[p], "") if p in base else (128, "", "fatal")
            if "cat" in args:
                p = args[-1][len(WD) + 1:]
                return (0, files[p], "") if p in files else (1, "", "no")
            raise AssertionError(args)

        ws, _ = make(script)
        ch = ws.changes("BASE", exclude={"skip.txt"})
        self.assertEqual(ch["m.py"], ("old m", "new m"))
        self.assertEqual(ch["gone.py"], ("bye", None))
        self.assertEqual(ch["added.py"], (None, "add"))
        self.assertEqual(ch["untracked.txt"], (None, "u"))
        self.assertNotIn("skip.txt", ch)

    def test_changes_skips_binary(self):
        def script(args, input):
            if "diff" in args:
                return 0, "M\tb.bin\n", ""
            if "ls-files" in args:
                return 0, "", ""
            return 0, "\x00bin�", ""
        ws, _ = make(script)
        self.assertEqual(ws.changes("BASE"), {})


class TestTools(unittest.TestCase):
    def test_tools(self):
        names = [t["function"]["name"] for t in container.TOOLS]
        self.assertEqual(names, ["read_file", "write_file", "run_command"])


if __name__ == "__main__":
    unittest.main()
