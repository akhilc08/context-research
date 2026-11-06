from __future__ import annotations

import json
import sys
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

    def run(self, args, *, input=None, timeout, max_output=None):
        self.calls.append({"args": list(args), "input": input, "timeout": timeout, "max_output": max_output})
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

    def test_network_flag(self):
        runner = FakeRunner()
        ContainerWorkspace("img:1", runner, workdir=WD, network="none").start()
        self.assertEqual(runner.calls[0]["args"],
                         ["docker", "run", "-d", "--rm", "--network", "none", "img:1", "sleep", "infinity"])

    def test_open_network_moves_container_to_scoring_network(self):
        ws, runner = make(network="none", scoring_network="bridge")
        ws.open_network()
        self.assertEqual([c["args"] for c in runner.calls],
                         [["docker", "network", "disconnect", "none", "cid123"],
                          ["docker", "network", "connect", "bridge", "cid123"]])
        self.assertEqual(ws.network, "bridge")

    def test_open_network_noop_without_scoring_network(self):
        for kw in ({"network": "none"}, {"network": "bridge", "scoring_network": "bridge"}, {}):
            ws, runner = make(**kw)
            ws.open_network()
            self.assertEqual(runner.calls, [])

    def test_open_network_without_starting_network(self):
        ws, runner = make(scoring_network="bridge")  # already on the default bridge
        ws.open_network()
        self.assertEqual(runner.calls, [])
        ws, runner = make(scoring_network="scoring")
        ws.open_network()
        self.assertEqual([c["args"] for c in runner.calls], [["docker", "network", "connect", "scoring", "cid123"]])

    def test_open_network_failure_raises(self):
        ws, _ = make(lambda args, input: (1, "", "no such network"), network="none", scoring_network="nope")
        with self.assertRaises(RuntimeError) as cm:
            ws.open_network()
        self.assertIn("no such network", str(cm.exception))
        with self.assertRaises(RuntimeError):
            ContainerWorkspace("img:1", FakeRunner(), workdir=WD, scoring_network="bridge").open_network()

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
        self.assertEqual(runner.calls[0]["timeout"], 22)
        self.assertEqual(runner.calls[0]["args"], ["docker", "exec", "-w", WD, "cid123", "timeout", "-k", "5", "7",
                                                   "bash", "-lc", "sleep 99"])
        self.assertEqual(runner.calls[1]["args"], ["docker", "exec", "cid123", "sh", "-c", "kill -9 -1"])

    def test_no_cleanup_without_timeout(self):
        ws, runner = make(lambda a, i: (1, "x", ""))
        res = ws.execute("run_command", {"command": "false"}, call_index=0)
        self.assertFalse(res["timed_out"])
        self.assertEqual(len(runner.calls), 1)

    def test_run_command_truncated_flag_from_cap_plus_one(self):
        ws, runner = make(lambda a, i: (0, "z" * 10001, ""))
        res = ws.execute("run_command", {"command": "x"}, call_index=0)
        self.assertTrue(res["truncated"])
        self.assertEqual(len(res["output"]), 10000)
        self.assertEqual(runner.calls[0]["max_output"], 10001)
        ws, _ = make(lambda a, i: (0, "z" * 10000, ""))
        self.assertFalse(ws.execute("run_command", {"command": "x"}, call_index=0)["truncated"])

    def test_read_preserves_crlf(self):
        def script(args, input):
            return (0, WD + "/a\n", "") if "realpath" in args else (0, "a\r\nb\r\n", "")
        ws, _ = make(script)
        self.assertEqual(ws.execute("read_file", {"path": "a"}, call_index=0)["content"], "a\r\nb\r\n")

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
        files = {"my dir/a b.py": "sp", "new dir/c d.txt": "sp2", "m.py": "new m", "added.py": "add", "untracked.txt": "u", "skip.txt": "s"}
        base = {"my dir/a b.py": "sp0", "m.py": "old m", "gone.py": "bye", "skip.txt": "s0"}

        def script(args, input):
            if "diff" in args:
                self.assertIn("-z", args)
                return 0, "M\0m.py\0D\0gone.py\0A\0added.py\0M\0skip.txt\0M\0my dir/a b.py\0", ""
            if "ls-files" in args:
                self.assertIn("-z", args)
                return 0, "untracked.txt\0new dir/c d.txt\0", ""
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
        self.assertEqual(ch["my dir/a b.py"], ("sp0", "sp"))
        self.assertEqual(ch["new dir/c d.txt"], (None, "sp2"))

    def test_changes_skips_binary(self):
        def script(args, input):
            if "diff" in args:
                return 0, "M\tb.bin\n", ""
            if "ls-files" in args:
                return 0, "", ""
            return 0, "\x00bin�", ""
        ws, _ = make(script)
        self.assertEqual(ws.changes("BASE"), {})


class DockerRunnerTest(unittest.TestCase):
    def test_success(self):
        code, out, err = container.DockerRunner().run(
            [sys.executable, "-c", "import sys; print('ok'); sys.stderr.write('e')"], timeout=10)
        self.assertEqual((code, out.strip(), err), (0, "ok", "e"))

    def test_nonzero(self):
        code, out, _ = container.DockerRunner().run([sys.executable, "-c", "print('x'); raise SystemExit(3)"], timeout=10)
        self.assertEqual((code, out.strip()), (3, "x"))

    def test_timeout_keeps_partial_output(self):
        code, out, _ = container.DockerRunner().run(
            [sys.executable, "-c", "print('hi', flush=True); import time; time.sleep(5)"], timeout=1)
        self.assertEqual(code, 124)
        self.assertEqual(out.strip(), "hi")

    def test_input_and_crlf_preserved(self):
        code, out, _ = container.DockerRunner().run(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
            input="a\r\nb", timeout=10)
        self.assertEqual(out, "a\r\nb")

    def test_output_bounded_to_tail(self):
        code, out, _ = container.DockerRunner().run(
            [sys.executable, "-c", "print('a' * 3000000); print('END')"], timeout=20, max_output=100)
        self.assertEqual(code, 0)
        self.assertEqual(len(out), 100)
        self.assertTrue(out.endswith("END\n"))

    def test_runner_default_cap(self):
        _, out, _ = container.DockerRunner(max_output=50).run(
            [sys.executable, "-c", "print('a' * 5000)"], timeout=10)
        self.assertEqual(len(out), 50)


class TestTools(unittest.TestCase):
    def test_tools(self):
        names = [t["function"]["name"] for t in container.TOOLS]
        self.assertEqual(names, ["read_file", "write_file", "run_command"])


if __name__ == "__main__":
    unittest.main()
