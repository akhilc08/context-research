"""Offline tests for the benchmark runner and analysis. No client is ever built."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bench import run_bench as RB
from bench import session as SE
from bench.cases import Case, save_manifest

CASES = [Case("o__r--a", "o/r", "o__r-1", "o__r-2", ("h1",), "notes", "tags"),
         Case("o__r--b", "o/r", "o__r-3", "o__r-4", ("h2",), "tags", "notes")]
CONFIG = {"repetitions": 2, "order_seed": 7, "models": [{"id": "m", "provider": "p", "budget_usd": 1}]}


def write(tmp: Path):
    save_manifest(CASES, tmp / "cases.json")
    (tmp / "config.json").write_text(json.dumps(CONFIG))
    return ["--config", str(tmp / "config.json"), "--manifest", str(tmp / "cases.json")]


def rec(path: Path, placement, status="finished", changed="new", unchanged="old", compactions=(), resolved=True, cost=0.5,
        condition="relay"):
    record = {"case_id": "c", "status": status, "cost_usd": cost, "compactions": list(compactions),
              "cell": {"condition": condition, "placement": placement, "worker_type": "existing"}}
    if status == "finished":
        record["rules"] = {"changed": {"outcome": changed}, "unchanged": {"outcome": unchanged}}
        record["tests"] = {"resolved": resolved}
    path.mkdir(parents=True)
    (path / "record.json").write_text(json.dumps(record))


class RunnerTests(unittest.TestCase):
    def test_dry_run_writes_plan_and_builds_no_client(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("provider.OpenRouterClient") as client:
            tmp = Path(d)
            self.assertEqual(RB.main(write(tmp) + ["--output", str(tmp / "out"), "--cells", "relay__none__existing"]), 0)
            client.assert_not_called()
            plan = json.loads((tmp / "out" / "plan.json").read_text())["entries"]
            self.assertEqual(len(plan), 4)
            self.assertEqual({e["cell_id"] for e in plan}, {"relay__none__existing"})
            self.assertEqual(sorted((e["case_id"], e["repetition"]) for e in plan),
                             [("o__r--a", 0), ("o__r--a", 1), ("o__r--b", 0), ("o__r--b", 1)])
            again = RB.build_plan(CONFIG, ["o__r--a", "o__r--b"], ["relay__none__existing"])
            self.assertEqual(plan, again)

    def test_live_refuses_existing_model_directory(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("provider.OpenRouterClient") as client:
            tmp = Path(d)
            (tmp / "out" / "model-0").mkdir(parents=True)
            with self.assertRaises(SystemExit):
                RB.main(write(tmp) + ["--output", str(tmp / "out"), "--live"])
            client.assert_not_called()

    def test_unknown_cell_or_case_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            with self.assertRaises(SystemExit):
                RB.main(write(tmp) + ["--output", str(tmp / "o"), "--cells", "nope"])
            with self.assertRaises(SystemExit):
                RB.main(write(tmp) + ["--output", str(tmp / "o"), "--cases", "nope"])

    def test_refuses_output_inside_repo_outside_ignored_pattern(self):
        for bad in (RB.REPO / "results" / "x", RB.REPO / "studies/subagent-rule-updates/results/other-001"):
            with self.assertRaises(SystemExit):
                RB.check_output_path(bad)
        ok = RB.REPO / "studies/subagent-rule-updates/results/bench-001"
        self.assertEqual(RB.check_output_path(ok), ok)
        with tempfile.TemporaryDirectory() as d:
            RB.check_output_path(Path(d) / "anything")

    def test_ignore_rule_present(self):
        text = (RB.REPO / ".gitignore").read_text()
        self.assertIn("studies/subagent-rule-updates/results/bench-*/", text)

    def test_execute_continues_past_infra_and_stops_on_provider_error(self):
        statuses = iter(["infra_error", "compaction_error", "provider_error", "finished"])
        seen = []

        class Client:
            def summary(self):
                return {"accounted_cost_usd": 1.0}

        def fake(client, case, cell, **kw):
            seen.append(case.case_id)
            return {"status": next(statuses), "cell": {}}

        plan = [{"case_id": "o__r--a", "cell_id": "relay__none__existing", "repetition": i} for i in range(4)]
        with tempfile.TemporaryDirectory() as d, mock.patch.object(SE, "run_cell", fake), \
                mock.patch.object(RB, "load_rule_map", return_value={}):
            reason = RB.execute(Client(), Path(d), plan, {c.case_id: c for c in CASES}, {}, rows={}, trajectories={},
                                rules_dir=Path(d), workspace_factory=None)
            self.assertEqual(len(seen), 3)
            self.assertIn("provider_error", reason)
            self.assertTrue((Path(d) / "cells/o__r--a/relay__none__existing/rep2/record.json").exists())


class AnalyzeTests(unittest.TestCase):
    def test_counts_for_two_records(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rec(out / "cells/a/1", "none", changed="new", unchanged="old", resolved=True, cost=0.25)
            rec(out / "cells/b/1", "none", changed="old", unchanged="both", resolved=False, cost=0.5)
            summary = RB.analyze(out)
            cell = summary["cells"]["relay__none__existing"]
            self.assertEqual(cell["records"], 2)
            self.assertEqual(cell["statuses"], {"finished": 2})
            self.assertEqual(cell["changed"], {"new": 1, "old": 1, "both": 0, "neither": 0})
            self.assertEqual(cell["unchanged"], {"new": 0, "old": 1, "both": 1, "neither": 0})
            self.assertEqual((cell["headline_passes"], cell["tests_resolved"]), (1, 1))
            self.assertAlmostEqual(cell["cost_usd"], 0.75)
            self.assertTrue((out / "summary.json").exists())
            self.assertIn("relay__none__existing", (out / "tables.md").read_text())

    def test_setup_invalid_excluded_from_headline(self):
        real = {"history": "manager", "skipped": False}
        skipped = {"history": "manager", "skipped": True}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rec(out / "cells/a/good", "manager", compactions=[real])
            rec(out / "cells/a/skip", "manager", compactions=[skipped])
            rec(out / "cells/a/none", "manager", compactions=[])
            rec(out / "cells/a/half", "both", compactions=[real])
            rec(out / "cells/a/err", "manager", status="infra_error")
            cells = RB.analyze(out)["cells"]
            manager, both = cells["relay__manager__existing"], cells["relay__both__existing"]
            self.assertEqual((manager["setup_invalid"], manager["valid_finished"], manager["headline_passes"]), (2, 1, 1))
            self.assertEqual(manager["statuses"], {"finished": 3, "infra_error": 1})
            self.assertEqual((both["setup_invalid"], both["valid_finished"], both["headline_passes"]), (1, 0, 0))
            self.assertEqual(len(manager["setup_invalid_records"]), 2)


if __name__ == "__main__":
    unittest.main()
