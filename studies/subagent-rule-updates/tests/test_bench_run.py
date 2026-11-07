"""Offline tests for the benchmark runner and analysis. No client is ever built."""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bench import run_bench as RB
from bench import session as SE
from bench.cases import Case, save_manifest
from tests.test_bench_session import NOTES, TAGS, row as task_row

CASES = [Case("o__r--a", "o/r", "o__r-1", "o__r-2", ("h1",), "notes", "tags"),
         Case("o__r--b", "o/r", "o__r-3", "o__r-4", ("h2",), "tags", "notes")]
CONFIG = {"repetitions": 2, "order_seed": 7, "models": [{"id": "m", "provider": "p", "budget_usd": 1}]}
UNSCREENED = {r.id: r for r in (NOTES, TAGS)}
SCREENED = {r.id: dataclasses.replace(r, screened=True) for r in (NOTES, TAGS)}
ROWS = {i: task_row(i, "Fix bug.") for i in ("o__r-1", "o__r-2", "o__r-3", "o__r-4")}


def write(tmp: Path):
    save_manifest(CASES, tmp / "cases.json")
    (tmp / "config.json").write_text(json.dumps(CONFIG))
    return ["--config", str(tmp / "config.json"), "--manifest", str(tmp / "cases.json")]


def rec(path: Path, placement, status="finished", changed="new", unchanged="old", compactions=(), resolved=True, cost=0.5,
        condition="relay", flags=(True, True, True), prior=None):
    record = {"case_id": "c", "status": status, "cost_usd": cost, "compactions": list(compactions),
              "cell": {"condition": condition, "placement": placement, "worker_type": "existing"}}
    record.update(zip(("u0_delegated", "u2_delegated", "u2_worker_finished"), flags))
    if status == "finished":
        record["rules"] = {"changed": {"outcome": changed}, "unchanged": {"outcome": unchanged}}
        if prior:
            record["rules"]["changed"]["repo_prior"] = prior
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

    def test_missing_rules_file_fails_before_model_dir_or_client(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("provider.OpenRouterClient") as client:
            tmp = Path(d)
            data = tmp / "data"
            (data / RB.PARQUET).parent.mkdir(parents=True)
            (data / RB.PARQUET).write_text("")
            (data / RB.HISTORY_DIR).mkdir(parents=True)
            CONFIG["data_root"] = str(data)
            args = write(tmp) + ["--output", str(tmp / "out"), "--live", "--allow-unvalidated"]
            with mock.patch.object(RB, "STUDY", tmp):
                with self.assertRaises(SystemExit) as cm:
                    RB.main(args)
            self.assertIn("rules", str(cm.exception))
            client.assert_not_called()
            self.assertFalse((tmp / "out" / "model-0").exists())
            CONFIG.pop("data_root")

    def live(self, tmp: Path, extra, *, rules=SCREENED, images_missing=(), freeze=None, execute=None):
        """Run main --live with data, rows, rules, Docker and the client mocked. Returns (client mock, exit)."""
        data = tmp / "data"
        (data / RB.PARQUET).parent.mkdir(parents=True, exist_ok=True)
        (data / RB.PARQUET).write_text("")
        (data / RB.HISTORY_DIR).mkdir(parents=True, exist_ok=True)
        (tmp / "config.json").write_text(json.dumps({**CONFIG, "data_root": str(data), "max_provider_calls": 1,
                                                     "temperature": 0, "max_output_tokens": 1,
                                                     "reasoning_effort": "low", "container_network": "none"}))
        save_manifest(CASES, tmp / "cases.json")
        args = ["--config", str(tmp / "config.json"), "--manifest", str(tmp / "cases.json"),
                "--output", str(tmp / "out"), "--live"] + extra
        patches = [mock.patch("provider.OpenRouterClient"), mock.patch("provider.load_key"),
                   mock.patch("bench.sources.load_rows", return_value=list(ROWS.values())),
                   mock.patch("bench.sources.trajectory_index", return_value={}),
                   mock.patch.object(RB, "load_rule_map", return_value=rules),
                   mock.patch.object(RB, "missing_images", return_value=list(images_missing)),
                   mock.patch.object(RB, "execute", side_effect=execute or (lambda *a, **k: None))]
        if freeze is not None:
            patches.append(mock.patch.object(RB, "freeze", side_effect=freeze))
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            mocks[0].return_value.summary.return_value = {"budget_committed_usd": 0.0}
            try:
                code = RB.main(args)
            except SystemExit as exc:
                code = exc
            return mocks[0], mocks[5], code

    def test_failed_freeze_removes_model_dir(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            with self.assertRaises(RuntimeError):
                self.live(tmp, ["--allow-unvalidated"], freeze=RuntimeError("boom"))
            self.assertFalse((tmp / "out" / "model-0").exists())

    def test_live_needs_validation_or_flag(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            client, _, code = self.live(tmp, [])
            self.assertIn("--validation", str(code))
            client.assert_not_called()
            self.assertFalse((tmp / "out" / "model-0").exists())

    def test_live_needs_screened_rules_or_flag(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            client, _, code = self.live(tmp, ["--allow-unvalidated"], rules=UNSCREENED)
            self.assertIn("Unscreened rules: o/r:notes, o/r:tags", str(code))
            client.assert_not_called()
            self.assertFalse((tmp / "out" / "model-0").exists())
            client, _, code = self.live(tmp, ["--allow-unvalidated", "--allow-unscreened"], rules=UNSCREENED)
            self.assertEqual(code, 0)
            client.assert_called_once()
            self.assertEqual(client.call_args.kwargs["timeout_retries"], 0)  # Not set in CONFIG.
            gates = json.loads((tmp / "out/model-0/manifest.json").read_text())["gates"]
            self.assertEqual(gates, {"validation": None, "dropped_cases": [], "allow_unvalidated": True,
                                     "allow_unscreened": True, "unscreened_rules": ["o/r:notes", "o/r:tags"]})

    def test_validation_filters_cases_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "validation.json").write_text(json.dumps({"valid_ids": ["o__r-1", "o__r-2", "o__r-3"]}))
            seen = []
            client, _, code = self.live(tmp, ["--validation", str(tmp / "validation.json")],
                                        execute=lambda c, m, plan, *a, **k: seen.extend(plan))
            self.assertEqual(code, 0)
            self.assertEqual({e["case_id"] for e in seen}, {"o__r--a"})
            manifest = json.loads((tmp / "out/model-0/manifest.json").read_text())
            self.assertEqual(manifest["gates"]["dropped_cases"], ["o__r--b"])
            self.assertEqual(manifest["gates"]["validation"], str(tmp / "validation.json"))
            self.assertFalse(manifest["gates"]["allow_unvalidated"])

    def test_validation_dropping_every_case_stops(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "v.json").write_text(json.dumps({"valid_ids": []}))
            with self.assertRaises(SystemExit) as cm:
                RB.main(write(tmp) + ["--output", str(tmp / "out"), "--validation", str(tmp / "v.json")])
            self.assertIn("No selected case", str(cm.exception))

    def test_missing_docker_image_stops_before_client(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            client, preflight, code = self.live(tmp, ["--allow-unvalidated"], images_missing=["img:o__r-2"])
            self.assertIn("Missing Docker images: img:o__r-2", str(code))
            client.assert_not_called()
            self.assertFalse((tmp / "out" / "model-0").exists())
            self.assertEqual(preflight.call_args[0][0], ["img:o__r-1", "img:o__r-2", "img:o__r-3", "img:o__r-4"])

    def test_missing_images_uses_docker_image_inspect(self):
        class Runner:
            calls = []

            def run(self, args, *, input=None, timeout, max_output=None):
                self.calls.append(args)
                return (1, "", "No such image") if args[-1] == "b" else (0, "[]", "")

        runner = Runner()
        self.assertEqual(RB.missing_images(["a", "b"], runner), ["b"])
        self.assertEqual(runner.calls, [["docker", "image", "inspect", "a"], ["docker", "image", "inspect", "b"]])

    def test_live_workspace_factory_sets_network(self):
        with tempfile.TemporaryDirectory() as d:
            ws = RB.live_workspace_factory("none")(task_row("o__r-1", "x"), Path(d))
            self.assertEqual(ws.network, "none")

    def test_config_workspace_factory_sets_both_networks(self):
        with tempfile.TemporaryDirectory() as d:
            ws = RB.config_workspace_factory({"container_network": "none", "scoring_network": "bridge"})(
                task_row("o__r-1", "x"), Path(d))
            self.assertEqual((ws.network, ws.scoring_network), ("none", "bridge"))
            ws = RB.config_workspace_factory({})(task_row("o__r-1", "x"), Path(d))
            self.assertEqual((ws.network, ws.scoring_network), ("none", None))

    def test_resume_flag_removed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                RB.main(write(Path(d)) + ["--output", str(Path(d) / "o"), "--resume"])

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
                return {"budget_committed_usd": 1.0}

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

    def test_execute_stops_after_three_unfinished_in_a_row(self):
        statuses = iter(["infra_error", "finished", "infra_error", "manager_call_limit", "compaction_error",
                         "finished"])
        seen = []

        class Client:
            def summary(self):
                return {"budget_committed_usd": 1.0}

        def fake(client, case, cell, **kw):
            seen.append(case.case_id)
            return {"status": next(statuses), "cell": {}}

        plan = [{"case_id": "o__r--a", "cell_id": "relay__none__existing", "repetition": i} for i in range(6)]
        with tempfile.TemporaryDirectory() as d, mock.patch.object(SE, "run_cell", fake), \
                mock.patch.object(RB, "load_rule_map", return_value={}), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            reason = RB.execute(Client(), Path(d), plan, {c.case_id: c for c in CASES}, {}, rows={}, trajectories={},
                                rules_dir=Path(d), workspace_factory=None)
        self.assertEqual(len(seen), 5)
        self.assertIn("3 consecutive unfinished records (last: compaction_error)", reason)
        self.assertIn("rep4", reason)
        self.assertIn("STATUS_COUNTS compaction_error=1 finished=1 infra_error=2 manager_call_limit=1", out.getvalue())


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

    def test_delegation_invalid_excluded_from_headline(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rec(out / "cells/a/ok", "none")
            rec(out / "cells/a/no_u0", "none", flags=(False, True, True))
            rec(out / "cells/a/no_u2", "none", flags=(True, False, False))
            rec(out / "cells/a/unfinished_u2", "none", flags=(True, True, False))
            rec(out / "cells/a/missing", "none", flags=())
            rec(out / "cells/a/err", "none", status="infra_error", flags=(False, False, False))
            cell = RB.analyze(out)["cells"]["relay__none__existing"]
            self.assertEqual((cell["delegation_invalid"], cell["valid_finished"], cell["headline_passes"]), (4, 1, 1))
            self.assertEqual(cell["setup_invalid"], 0)
            self.assertEqual(sorted(cell["delegation_invalid_records"]),
                             ["cells/a/missing", "cells/a/no_u0", "cells/a/no_u2", "cells/a/unfinished_u2"])
            self.assertEqual(cell["changed"]["new"], 1)
            self.assertIn("delegation_invalid", (out / "tables.md").read_text())

    def test_no_change_reported_as_control_not_headline(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rec(out / "cells/n/1", "none", condition="no_change", changed="old", unchanged="old")
            rec(out / "cells/n/2", "none", condition="no_change", changed="new", unchanged="old")
            rec(out / "cells/r/1", "none", changed="old", unchanged="old")
            cells = RB.analyze(out)["cells"]
            control, relay = cells["no_change__none__existing"], cells["relay__none__existing"]
            self.assertEqual((control["headline_passes"], control["control_passes"]), (0, 1))
            self.assertEqual((relay["headline_passes"], relay["control_passes"]), (0, 0))
            tables = (out / "tables.md").read_text()
            self.assertIn("No-change control", tables)
            self.assertIn("| no_change__none__existing | 2 | 1 |", tables)

    def test_headline_split_by_changed_rule_prior(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rec(out / "cells/a/1", "none", prior="old")
            rec(out / "cells/a/2", "none", prior="old", changed="old")
            rec(out / "cells/a/3", "none", prior="new")
            rec(out / "cells/a/4", "none")
            rec(out / "cells/a/5", "none", prior="old", flags=(False, True, True))
            cell = RB.analyze(out)["cells"]["relay__none__existing"]
            self.assertEqual(cell["by_changed_prior"], {"old": {"valid_finished": 2, "headline_passes": 1},
                                                        "new": {"valid_finished": 1, "headline_passes": 1},
                                                        "unknown": {"valid_finished": 1, "headline_passes": 1}})
            self.assertIn("| relay__none__existing | 1/1 | 1/2 | 1/1 |", (out / "tables.md").read_text())

    def test_malformed_finished_record_is_counted_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rec(out / "cells/a/ok", "none")
            rec(out / "cells/a/bad", "none")
            path = out / "cells/a/bad/record.json"
            data = json.loads(path.read_text())
            data["rules"] = {"changed": {}}
            path.write_text(json.dumps(data))
            cell = RB.analyze(out)["cells"]["relay__none__existing"]
            self.assertEqual(cell["statuses"], {"finished": 1, "malformed_record": 1})
            self.assertEqual(cell["valid_finished"], 1)


if __name__ == "__main__":
    unittest.main()