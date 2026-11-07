"""Offline tests for per-history compaction thresholds, forced compaction, and delegation flags."""
from __future__ import annotations

import json
import unittest
from unittest import mock

import compaction as C
import pi_compaction as PI

from bench import session as SE
from tests import test_bench_session as TS
from tests.test_bench_session import CASE, CONFIG, ROWS, RULES, Scripted

NEVER = 10 ** 9


class SessionTest(unittest.TestCase):
    """Same fixtures as test_bench_session.SessionTest, without re-running its tests here."""

    setUp = TS.SessionTest.setUp
    tearDown = TS.SessionTest.tearDown
    run_cell = TS.SessionTest.run_cell


class ThresholdTests(SessionTest):
    def test_manager_threshold_is_separate_from_worker(self):
        config = {**CONFIG, "compact_threshold_chars": NEVER, "manager_compact_threshold_chars": 500}
        record, _, _ = self.run_cell(SE.Cell("relay", "both", "existing"), config=config)
        self.assertEqual(record["status"], "finished")
        manager = [e for e in record["compactions"] if e["history"] == "manager"]
        worker = [e for e in record["compactions"] if e["history"] == "worker-1"]
        self.assertTrue(manager and not any(e["forced"] for e in manager))
        self.assertEqual(manager[0]["after_block"], 0)
        self.assertEqual([e["forced"] for e in worker], [True])
        self.assertEqual(record["config"]["manager_compact_threshold_chars"], 500)

    def test_worker_threshold_does_not_apply_to_manager(self):
        config = {**CONFIG, "compact_threshold_chars": 500, "manager_compact_threshold_chars": NEVER}
        record, _, _ = self.run_cell(SE.Cell("relay", "both", "existing"), config=config)
        manager = [e for e in record["compactions"] if e["history"] == "manager"]
        worker = [e for e in record["compactions"] if e["history"] == "worker-1"]
        self.assertEqual([e["forced"] for e in manager], [True])
        self.assertFalse(any(e["forced"] for e in worker))

    def test_forced_compaction_after_last_block(self):
        config = {**CONFIG, "compact_threshold_chars": NEVER, "manager_compact_threshold_chars": NEVER}
        for placement, names in (("none", []), ("manager", ["manager"]), ("worker", ["worker-1"]),
                                 ("both", ["manager", "worker-1"])):
            record, client, _ = self.run_cell(SE.Cell("relay", placement, "existing"), config=config)
            self.assertEqual(record["status"], "finished", placement)
            events = record["compactions"]
            self.assertEqual([e["history"] for e in events], names, placement)
            for e in events:
                self.assertTrue(e["forced"])
                self.assertFalse(e["skipped"])
                self.assertFalse(e["forced_generic"])
                self.assertEqual(e["after_block"], 2)
            u2 = next(r for r in client.requests if "/t2/manager" in r["tag"])["messages"]
            has_summary = any((m.get("content") or "").startswith(C.SUMMARY_PREFIX) for m in u2)
            self.assertEqual(has_summary, "manager" in names, placement)

    def test_compaction_records_summary_rule_mentions(self):
        config = {**CONFIG, "compact_threshold_chars": NEVER, "manager_compact_threshold_chars": NEVER}
        record, _, _ = self.run_cell(SE.Cell("relay", "both", "existing"), config=config)
        for e in record["compactions"]:
            mentions = e["summary_rule_mentions"]
            self.assertEqual(set(mentions), {"changed", "unchanged"})
            self.assertEqual(set(mentions["changed"]), {"old", "new"})
            expected = SE.rule_mentions(e["summary"], CASE, RULES)
            self.assertEqual(mentions, expected)

    def test_forced_compaction_reinserts_u1(self):
        u1 = SE.user_turns(CASE, RULES, ROWS)[1]
        config = {**CONFIG, "compact_threshold_chars": NEVER, "manager_compact_threshold_chars": NEVER}
        record, client, _ = self.run_cell(SE.Cell("reinsert", "worker", "existing"), config=config)
        self.assertEqual([(e["forced"], e["reinserted"]) for e in record["compactions"]], [(True, True)])
        worker = next(r for r in client.requests if "/t2/worker-1" in r["tag"])["messages"]
        self.assertIn({"role": "user", "content": u1}, worker)

    def test_forced_pi_skip_falls_back_to_generic(self):
        config = {**CONFIG, "compactor": "pi", "compact_threshold_chars": 0, "manager_compact_threshold_chars": 0}
        with mock.patch.object(PI, "KEEP_RECENT_TOKENS", NEVER):
            record, client, _ = self.run_cell(SE.Cell("relay", "both", "existing"), config=config)
        self.assertEqual(record["status"], "finished")
        for name in ("manager", "worker-1"):
            events = [e for e in record["compactions"] if e["history"] == name]
            self.assertTrue(all(e["skipped"] for e in events[:-1]), name)
            self.assertGreaterEqual(len(events), 4, name)  # Three skipped threshold attempts, then the forced one.
            last = events[-1]
            self.assertEqual((last["forced"], last["forced_generic"], last["skipped"]), (True, True, False), name)
            self.assertIn("summary", last)
        self.assertTrue(any(r["messages"][0]["content"] == C.SUMMARIZER_SYSTEM for r in client.requests))

    def test_threshold_events_are_not_forced(self):
        record, _, _ = self.run_cell(SE.Cell("relay", "both", "existing"))
        self.assertTrue(record["compactions"])
        self.assertFalse(any(e["forced"] or e["forced_generic"] for e in record["compactions"]))


class ReplayTests(SessionTest):
    def test_replayed_worker_history_uses_problem_statement_and_workdir(self):
        record, client, _ = self.run_cell(SE.Cell("relay", "none", "existing"))
        worker = next(r for r in client.requests if "/t2/worker-1" in r["tag"])["messages"]
        replayed = [m for m in worker if m["role"] == "user" and "Old issue" in (m.get("content") or "")]
        self.assertEqual(len(replayed), 3)
        for m in replayed:
            self.assertTrue(m["content"].startswith("Old issue"))
        self.assertNotIn("/testbed", json.dumps(worker))


class DelegationTests(SessionTest):
    def test_flags_when_everything_delegated(self):
        record, _, _ = self.run_cell(SE.Cell("relay", "none", "existing"))
        self.assertEqual((record["u0_delegated"], record["u2_delegated"], record["u2_worker_finished"]),
                         (True, True, True))

    def test_flags_when_manager_answers_u2_itself(self):
        class NoU2(Scripted):
            def complete(self, messages, **kwargs):
                last = [m for m in messages if m["role"] == "user"][-1]["content"]
                if messages[0]["content"].startswith(SE.MANAGER_SYSTEM) and last.startswith("Next task"):
                    self.n += 1
                    self.requests.append({"tag": kwargs.get("tag", ""), "messages": messages})
                    return {"id": "x", "choices": [{"finish_reason": "stop",
                                                    "message": {"role": "assistant", "content": "Did it myself."}}]}
                return super().complete(messages, **kwargs)

        record, _, _ = self.run_cell(SE.Cell("relay", "none", "existing"), client=NoU2())
        self.assertEqual(record["status"], "finished")
        self.assertEqual((record["u0_delegated"], record["u2_delegated"], record["u2_worker_finished"]),
                         (True, False, False))

    def test_unfinished_u2_worker(self):
        flags = SE.delegation_flags([{"turn": "U0", "status": "finished"}, {"turn": "U2", "status": "finished"},
                                     {"turn": "U2", "status": "call_limit"}])
        self.assertEqual(flags, {"u0_delegated": True, "u2_delegated": True, "u2_worker_finished": False,
                                 "u2_deliveries": 2, "u2_first_restated_rules": False})
        self.assertFalse(SE.delegation_flags([{"turn": "U2", "status": "finished"}])["u0_delegated"])


class ControlTests(unittest.TestCase):
    def rec(self, condition, changed, unchanged):
        return {"status": "finished", "cell": {"condition": condition, "placement": "none", "worker_type": "existing"},
                "rules": {"changed": {"outcome": changed}, "unchanged": {"outcome": unchanged}}}

    def test_no_change_has_its_own_pass(self):
        self.assertTrue(SE.control_pass(self.rec("no_change", "old", "old")))
        self.assertFalse(SE.headline_pass(self.rec("no_change", "old", "old")))
        self.assertFalse(SE.headline_pass(self.rec("no_change", "new", "old")))
        self.assertFalse(SE.control_pass(self.rec("relay", "old", "old")))
        self.assertTrue(SE.headline_pass(self.rec("relay", "new", "old")))

    def test_first_attempt_pass(self):
        rec = self.rec("relay", "new", "old")
        self.assertFalse(SE.headline_pass(rec, first=True))  # no first_attempt recorded
        rec["first_attempt"] = {"rules": {"changed": {"outcome": "old"}, "unchanged": {"outcome": "old"}}}
        self.assertFalse(SE.headline_pass(rec, first=True))
        self.assertTrue(SE.headline_pass(rec))
        ctl = self.rec("no_change", "old", "old")
        ctl["first_attempt"] = {"rules": {"changed": {"outcome": "neither"}, "unchanged": {"outcome": "neither"}}}
        self.assertFalse(SE.control_pass(ctl, first=True))
        self.assertTrue(SE.control_pass(ctl))


if __name__ == "__main__":
    unittest.main()
