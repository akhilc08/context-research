from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from bench import sources


def _row(instance_id, repo, language, created_at):
    return {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": "abc123",
        "problem_statement": "fix it",
        "image_name": "docker.io/x/y:1",
        "language": language,
        "created_at": created_at,
        "FAIL_TO_PASS": ["t1"],
        "PASS_TO_PASS": ["t2", "t3"],
        "patch": "diff a",
        "test_patch": "diff b",
        "license": "MIT",
        "install_config": {
            "test_cmd": "pytest -rA" if language == "python" else "npm test",
            "log_parser": "parse_log_pytest" if language == "python" else "parse_log_js_4",
            "install": ["pip install ."],
        },
    }


class SourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _parquet(self):
        rows = [
            _row("psf__requests-6028", "psf/requests", "python", "2021-06-22 22:21:33"),
            _row("elastic__synthetics-316", "elastic/synthetics", "js", "2021-06-22 22:21:34"),
        ]
        path = self.root / "t.parquet"
        pq.write_table(pa.Table.from_pylist(rows), path)
        return path

    def test_load_rows_filters_python_by_default(self):
        rows = sources.load_rows(self._parquet())
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.instance_id, "psf__requests-6028")
        self.assertEqual(r.test_cmd, "pytest -rA")
        self.assertEqual(r.log_parser, "parse_log_pytest")
        self.assertEqual(r.fail_to_pass, ("t1",))
        self.assertEqual(r.pass_to_pass, ("t2", "t3"))
        self.assertEqual(r.created_at, 1624400493)
        self.assertEqual(r.license, "MIT")
        self.assertEqual(r.workdir, "/requests")

    def test_load_rows_all_languages(self):
        self.assertEqual(len(sources.load_rows(self._parquet(), language=None)), 2)

    def test_issue_number(self):
        self.assertEqual(sources.issue_number("psf__requests-6028"), 6028)
        self.assertEqual(sources.issue_number("a__b-c-12"), 12)

    def test_trajectory_index(self):
        for lang, repo, iid in [
            ("python", "psf__requests", "psf__requests-6028"),
            ("python", "psf__requests", "psf__requests-1"),
            ("js", "a__b", "a__b-2"),
        ]:
            d = self.root / "history" / lang / repo / iid
            d.mkdir(parents=True)
            (d / f"{iid}.traj.json").write_text("{}")
        (self.root / "history" / "python" / "psf__requests" / "psf__requests-9").mkdir()
        idx = sources.trajectory_index(self.root / "history")
        self.assertEqual(set(idx), {"psf/requests", "a/b"})
        self.assertEqual(set(idx["psf/requests"]), {"psf__requests-6028", "psf__requests-1"})
        self.assertTrue(idx["psf/requests"]["psf__requests-1"].name.endswith(".traj.json"))


if __name__ == "__main__":
    unittest.main()
