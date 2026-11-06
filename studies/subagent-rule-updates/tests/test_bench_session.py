"""Offline tests for the session engine: scripted manager, worker, and summarizer over a fake container."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import compaction as C
import pi_compaction as PI

from bench import session as SE
from bench.cases import Case
from bench.container import ContainerWorkspace
from bench.rules import RuleSpec
from bench.sources import TaskRow

WD = "/r"
NOTES = RuleSpec("notes", "o/r", "Add a release note as changes/<issue>.txt for each fix.",
                 "Add a release note as news/<issue>.txt for each fix.",
                 {"type": "new_file", "dir": "changes", "name_regex": r"{issue}\.txt"},
                 {"type": "new_file", "dir": "news", "name_regex": r"{issue}\.txt"})
TAGS = RuleSpec("tags", "o/r", "Mark each changed Python file with a comment # OLD-TAG.",
                "Mark each changed Python file with a comment # NEW-TAG.",
                {"type": "added_line", "path_glob": "*.py", "line_regex": "# OLD-TAG"},
                {"type": "added_line", "path_glob": "*.py", "line_regex": "# NEW-TAG"})
RULES = {r.id: r for r in (NOTES, TAGS)}
LOG = "PASSED tests/test_a.py::test_one\n"


def row(iid, statement):
    return TaskRow(iid, "o/r", "base-" + iid, statement, "img:" + iid, "python", 0, "pytest -rA", "parse_log_pytest",
                   ("tests/test_a.py::test_one",), (), "", "diff --git a/tests/test_a.py b/tests/test_a.py\n", "MIT", WD)


ROWS = {"o__r-1": row("o__r-1", "Fix bug 1 in app.py."), "o__r-2": row("o__r-2", "Fix bug 2 in app.py.")}
HISTORY = ("o__r-h1", "o__r-h2", "o__r-h3")
CASE = Case("o__r--notes", "o/r", "o__r-1", "o__r-2", HISTORY, "notes", "tags")
CONFIG = {"max_manager_calls": 4, "max_worker_calls": 6, "compact_threshold_chars": 2000, "compactor": "generic"}


class FakeRunner:
    """An in-memory container: one dict of files per started container, base content fixed."""

    def __init__(self):
        self.base = {"app.py": "x = 1\n"}
        self.files = dict(self.base)
        self.started, self.removed = 0, 0

    def run(self, args, *, input=None, timeout, max_output=None):
        if args[:2] == ["docker", "run"]:
            self.started += 1
            return 0, "cid%d\n" % self.started, ""
        if args[:2] == ["docker", "rm"]:
            self.removed += 1
            return 0, "", ""
        rest = args[2:]
        if rest[0] == "-i":
            rest = rest[1:]
        if rest[0] == "-w":
            rest = rest[2:]
        cmd = rest[1:]
        rel = lambda p: p[len(WD) + 1:]
        if cmd[0] == "realpath":
            return 0, cmd[-1] + "\n", ""
        if cmd[0] == "cat":
            name = rel(cmd[1])
            return (0, self.files[name], "") if name in self.files else (1, "", "missing")
        if cmd[:2] == ["sh", "-c"]:
            self.files[rel(cmd[-1])] = input
            return 0, "", ""
        if cmd[0] == "git" and "diff" in cmd:
            out = "".join("M\0%s\0" % p for p in sorted(self.files) if p in self.base and self.files[p] != self.base[p])
            return 0, out, ""
        if cmd[0] == "git" and "ls-files" in cmd:
            return 0, "".join("%s\0" % p for p in sorted(self.files) if p not in self.base), ""
        if cmd[0] == "git" and "show" in cmd:
            return 0, self.base[cmd[-1].split(":", 1)[1]], ""
        if cmd[0] == "git" and "apply" in cmd:
            return 0, "", ""
        if cmd[:2] == ["bash", "-lc"]:
            return 0, LOG, ""
        return 0, "", ""


class Factory:
    def __init__(self):
        self.runners = []

    def __call__(self, task_row, directory):
        runner = FakeRunner()
        self.runners.append(runner)
        return ContainerWorkspace(task_row.image_name, runner, workdir=task_row.workdir)


def call(name, args, n):
    return {"id": "r%d" % n, "choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
            "tool_calls": [{"id": "c%d" % n, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}]}


def reply(text, n):
    return {"id": "r%d" % n, "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 1}}


class Scripted:
    """Manager forwards every user turn. Worker follows the latest rule wording found in its system prompt or
    user messages. Summarizer keeps every rule wording it sees. fail_at raises on that request number."""

    def __init__(self, fail_at=None):
        self.n, self.requests, self.fail_at = 0, [], fail_at

    def complete(self, messages, *, tools=None, tag="", **kwargs):
        self.n += 1
        self.requests.append({"tag": tag, "messages": json.loads(json.dumps(messages))})
        if self.n == self.fail_at:
            raise RuntimeError("provider down")
        system = messages[0]["content"]
        if system in (C.SUMMARIZER_SYSTEM, PI.P["SUMMARIZATION_SYSTEM_PROMPT"]):
            text = messages[1]["content"]
            kept = [getattr(r, v) for r in RULES.values() for v in ("original", "changed") if getattr(r, v) in text]
            return reply("SUMMARY %d: %s" % (self.n, " ".join(kept)), self.n)
        last = max(i for i, m in enumerate(messages) if m["role"] == "user")
        step = sum(m["role"] == "assistant" for m in messages[last + 1:])
        text = messages[last]["content"]
        if system.startswith(SE.MANAGER_SYSTEM):
            return reply("Done.", self.n) if step else call("message_worker", {"message": text}, self.n)
        match = re.search(r"Fix bug (\d+)", text)
        if not match:
            return reply("Noted.", self.n)
        issue = match.group(1)
        seen = "\n".join([system] + [m.get("content") or "" for m in messages if m["role"] == "user"])
        writes = []
        for rule in RULES.values():
            pos = {v: seen.rfind(getattr(rule, v)) for v in ("original", "changed")}
            version = max(pos, key=pos.get) if max(pos.values()) >= 0 else None
            if version is None:
                continue
            if rule.id == "notes":
                writes.append(("%s/%s.txt" % ("news" if version == "changed" else "changes", issue), "note\n"))
            else:
                writes.append(("app.py", "x = 2  # %s\n" % ("NEW-TAG" if version == "changed" else "OLD-TAG")))
        if step < len(writes):
            path, content = writes[step]
            return call("write_file", {"path": path, "content": content}, self.n)
        return reply("Finished.", self.n)


def trajectory(i):
    return {"messages": [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "<pr_description>Consider the following PR description:\nOld issue %d %s</pr_description>" % (i, "z" * 1200)},
        {"role": "assistant", "content": "look", "tool_calls": [{"id": "t1", "type": "function",
         "function": {"name": "bash", "arguments": json.dumps({"command": "cat app.py"})}}]},
        {"role": "tool", "tool_call_id": "t1", "content": "<returncode>0</returncode><output>%s</output>" % ("y" * 1500)},
        {"role": "assistant", "content": "Fixed issue %d." % i}]}


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.trajectories = {"o/r": {}}
        for i, iid in enumerate(HISTORY):
            path = root / "traj" / iid / (iid + ".traj.json")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(trajectory(i)))
            self.trajectories["o/r"][iid] = path
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def run_cell(self, cell, client=None, config=None, case=CASE):
        client = client or Scripted()
        factory = Factory()
        record = SE.run_cell(client, case, cell, rules=RULES, rows=ROWS, trajectories=self.trajectories,
                             outdir=self.root / "out" / SE.cell_id(cell), config=config or CONFIG, workspace_factory=factory)
        return record, client, factory

    def test_cells(self):
        self.assertEqual(len(SE.CELLS), 19)
        self.assertEqual(len(set(SE.CELLS)), 19)
        self.assertFalse([c for c in SE.CELLS if c.worker_type == "new" and c.placement in ("worker", "both")])
        self.assertIn(SE.Cell("no_change", "none", "existing"), SE.CELLS)
        self.assertEqual({c.condition for c in SE.CELLS if c.worker_type == "new"}, {"relay", "creation_pin", "store"})
        self.assertEqual({c.condition for c in SE.CELLS if c.worker_type == "existing"} - {"no_change"},
                         {"relay", "reinsert", "store"})

    def test_user_turns(self):
        turns = SE.user_turns(CASE, RULES, ROWS)
        self.assertEqual(len(turns), 3)
        self.assertIn(NOTES.original, turns[0])
        self.assertIn(TAGS.original, turns[0])
        self.assertIn("Fix bug 1", turns[0])
        self.assertEqual(turns[1], "A change to one of my rules, effective now: " + NOTES.changed)
        self.assertIn("Fix bug 2", turns[2])
        self.assertNotIn(NOTES.original, turns[2])
        self.assertNotIn(TAGS.original, turns[2])
        nc = SE.user_turns(CASE, RULES, ROWS, change=False)
        self.assertEqual(nc, [turns[0], turns[2]])

    def test_relay_none_has_no_compaction_and_scores(self):
        record, client, factory = self.run_cell(SE.Cell("relay", "none", "existing"))
        self.assertEqual(record["status"], "finished")
        self.assertEqual(record["compactions"], [])
        self.assertFalse(any(r["messages"][0]["content"] == C.SUMMARIZER_SYSTEM for r in client.requests))
        self.assertEqual(record["rules"]["changed"]["outcome"], "new")
        self.assertEqual(record["rules"]["unchanged"]["outcome"], "old")
        self.assertTrue(SE.headline_pass(record))
        self.assertTrue(record["tests"]["resolved"])
        self.assertEqual([r.started for r in factory.runners], [1, 1])
        self.assertEqual([r.removed for r in factory.runners], [1, 1])
        # Fillers were appended to both histories.
        u2 = next(r for r in client.requests if "/t2/manager" in r["tag"])
        self.assertTrue(any(m.get("tool_calls") and m["tool_calls"][0]["id"] == "mgr-o__r-h2" for m in u2["messages"]))
        # One context hash per model request.
        self.assertEqual(len(record["calls"]), len(client.requests))
        self.assertTrue(all(len(c["context_hash"]) == 64 for c in record["calls"]))

    def test_placement_selects_histories(self):
        for placement, names in (("manager", {"manager"}), ("worker", {"worker-1"}), ("both", {"manager", "worker-1"})):
            record, _, _ = self.run_cell(SE.Cell("relay", placement, "existing"))
            self.assertEqual(record["status"], "finished")
            self.assertTrue(record["compactions"])
            self.assertEqual({e["history"] for e in record["compactions"]}, names, placement)

    def test_pi_compactor(self):
        with mock.patch.object(PI, "KEEP_RECENT_TOKENS", 200):
            record, client, _ = self.run_cell(SE.Cell("relay", "worker", "existing"), config={**CONFIG, "compactor": "pi"})
        self.assertEqual(record["status"], "finished")
        self.assertTrue(record["compactions"])
        self.assertTrue(any(r["messages"][0]["content"] == PI.P["SUMMARIZATION_SYSTEM_PROMPT"] for r in client.requests))

    def test_reinsert_follows_every_compaction(self):
        u1 = SE.user_turns(CASE, RULES, ROWS)[1]
        record, client, _ = self.run_cell(SE.Cell("reinsert", "both", "existing"))
        self.assertEqual(record["status"], "finished")
        self.assertGreaterEqual(len(record["compactions"]), 2)
        self.assertTrue(all(e["reinserted"] for e in record["compactions"]))
        for name, tag in (("manager", "/t2/manager"), ("worker-1", "/t2/worker-1")):
            messages = next(r for r in client.requests if tag in r["tag"])["messages"]
            summaries = [i for i, m in enumerate(messages) if (m.get("content") or "").startswith(C.SUMMARY_PREFIX)]
            self.assertTrue(summaries, name)
            for i in summaries:
                self.assertEqual(messages[i + 1], {"role": "user", "content": u1}, name)
        # A later summarizer request sees the reinserted U1 right after the earlier summary.
        summarizer = [r for r in client.requests if r["messages"][0]["content"] == C.SUMMARIZER_SYSTEM]
        later = [r for r in summarizer if C.SUMMARY_PREFIX in r["messages"][1]["content"]]
        self.assertTrue(later)
        for r in later:
            self.assertIn("USER: " + u1, r["messages"][1]["content"])

    def test_relay_compaction_has_no_reinsert(self):
        u1 = SE.user_turns(CASE, RULES, ROWS)[1]
        record, client, _ = self.run_cell(SE.Cell("relay", "both", "existing"))
        self.assertFalse(any(e["reinserted"] for e in record["compactions"]))
        messages = next(r for r in client.requests if "/t2/manager" in r["tag"])["messages"]
        self.assertFalse(any(m.get("content") == u1 for m in messages))

    def test_store_switches_rule_block_at_u1(self):
        for cell in (SE.Cell("store", "both", "existing"), SE.Cell("store", "manager", "new")):
            record, client, _ = self.run_cell(cell)
            self.assertEqual(record["status"], "finished")
            agents = [r for r in client.requests
                      if r["messages"][0]["content"] not in (C.SUMMARIZER_SYSTEM, PI.P["SUMMARIZATION_SYSTEM_PROMPT"])]
            before = [r for r in agents if "/t0/" in r["tag"]]
            after = [r for r in agents if "/t1/" in r["tag"] or "/t2/" in r["tag"]]
            self.assertTrue(before and after)
            self.assertTrue(any("/worker-1/" in r["tag"] for r in before))
            self.assertTrue(any("/t2/worker-1/" in r["tag"] for r in after))
            for r in before:
                system = r["messages"][0]["content"]
                self.assertNotIn(NOTES.changed, system)
                self.assertIn(NOTES.original, system)
                self.assertIn(TAGS.original, system)
            for r in after:
                system = r["messages"][0]["content"]
                self.assertIn(NOTES.changed, system)
                self.assertNotIn(NOTES.original, system)
                self.assertIn(TAGS.original, system)

    def test_non_store_systems_carry_no_rules(self):
        record, client, _ = self.run_cell(SE.Cell("relay", "none", "existing"))
        for r in client.requests:
            system = r["messages"][0]["content"]
            self.assertTrue(system in (SE.MANAGER_SYSTEM, SE.BENCH_WORKER_SYSTEM), r["tag"])

    def test_creation_pin_new_worker(self):
        record, client, _ = self.run_cell(SE.Cell("creation_pin", "manager", "new"))
        self.assertEqual(record["status"], "finished")
        first_u2 = next(r for r in client.requests if "/t2/worker-1/" in r["tag"])["messages"]
        self.assertIn(NOTES.changed, first_u2[0]["content"])
        self.assertIn(TAGS.original, first_u2[0]["content"])
        self.assertTrue(first_u2[0]["content"].startswith(SE.BENCH_WORKER_SYSTEM))
        self.assertEqual([m["role"] for m in first_u2], ["system", "user"])
        self.assertEqual(record["worker_reset"]["history_messages_before"] > 0, True)
        for r in client.requests:
            if "/t0/worker-1/" in r["tag"] or "/t1/worker-1/" in r["tag"]:
                self.assertEqual(r["messages"][0]["content"], SE.BENCH_WORKER_SYSTEM)
        self.assertTrue(SE.headline_pass(record))

    def test_new_relay_worker_starts_empty(self):
        record, client, _ = self.run_cell(SE.Cell("relay", "none", "new"))
        first_u2 = next(r for r in client.requests if "/t2/worker-1/" in r["tag"])["messages"]
        self.assertEqual(first_u2[0]["content"], SE.BENCH_WORKER_SYSTEM)
        self.assertEqual([m["role"] for m in first_u2], ["system", "user"])
        # The scripted manager forwards only U2, so the new worker never sees a rule.
        self.assertEqual(record["rules"]["changed"]["outcome"], "neither")
        self.assertFalse(SE.headline_pass(record))

    def test_no_change_control(self):
        u1 = SE.user_turns(CASE, RULES, ROWS)[1]
        record, client, _ = self.run_cell(SE.Cell("no_change", "none", "existing"))
        self.assertEqual([t["label"] for t in record["turns"]], ["U0", "U2"])
        self.assertFalse(any(u1 in json.dumps(r["messages"]) for r in client.requests))
        self.assertEqual(record["rules"]["changed"]["outcome"], "old")
        self.assertFalse(SE.headline_pass(record))

    def test_manager_system_identical_across_cells(self):
        bases = set()
        for cell in SE.CELLS:
            record, client, _ = self.run_cell(cell)
            self.assertEqual(record["status"], "finished", cell)
            bases.add(record["manager_system"])
            for r in client.requests:
                if re.search(r"/t\d/manager", r["tag"]):
                    system = r["messages"][0]["content"]
                    self.assertTrue(system.startswith(SE.MANAGER_SYSTEM), cell)
                    if cell.condition != "store":
                        self.assertEqual(system, SE.MANAGER_SYSTEM, cell)
            u0 = next(r for r in client.requests if "/t0/manager" in r["tag"])["messages"][1]
            self.assertEqual(u0["content"], SE.user_turns(CASE, RULES, ROWS)[0])
        self.assertEqual(bases, {SE.MANAGER_SYSTEM})
        self.assertIn("Pass on any user instructions the worker needs.", SE.MANAGER_SYSTEM)

    def test_provider_error_stops_cell_unscored(self):
        record, client, factory = self.run_cell(SE.Cell("relay", "none", "existing"), client=Scripted(fail_at=2))
        self.assertEqual(record["status"], "provider_error")
        self.assertNotIn("rules", record)
        self.assertNotIn("tests", record)
        self.assertFalse(SE.headline_pass(record))
        self.assertTrue(all(r.started == r.removed for r in factory.runners))

    def test_summarizer_error_stops_cell(self):
        # Request numbers: U0 manager 1, worker 2-4, manager 5; U1 manager 6, worker 7, manager 8; next is a summary.
        record, _, factory = self.run_cell(SE.Cell("relay", "manager", "existing"), client=Scripted(fail_at=9))
        self.assertEqual(record["status"], "provider_error")
        self.assertNotIn("rules", record)
        self.assertTrue(all(r.started == r.removed for r in factory.runners))

    def test_incomplete_summary_stops_cell(self):
        class EmptySummary(Scripted):
            def complete(self, messages, **kwargs):
                response = super().complete(messages, **kwargs)
                if messages[0]["content"] == C.SUMMARIZER_SYSTEM:
                    response["choices"][0]["message"]["content"] = ""
                return response

        record, _, factory = self.run_cell(SE.Cell("relay", "worker", "existing"), client=EmptySummary())
        self.assertEqual(record["status"], "compaction_error")
        self.assertNotIn("rules", record)
        self.assertFalse(SE.headline_pass(record))
        self.assertEqual(len(factory.runners), 1)

    def test_record_saved(self):
        record, _, _ = self.run_cell(SE.Cell("store", "none", "existing"))
        saved = json.loads((self.root / "out" / SE.cell_id(SE.Cell("store", "none", "existing")) / "record.json").read_text())
        self.assertEqual(saved["cell"], {"condition": "store", "placement": "none", "worker_type": "existing"})
        self.assertEqual(saved["status"], record["status"])


if __name__ == "__main__":
    unittest.main()
