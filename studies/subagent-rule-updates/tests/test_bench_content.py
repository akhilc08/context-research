"""Content checks for the first-version rule files and manifest.

Hand-written examples name, for every rule, one file the old version leaves and one the new
version leaves. The gold-patch tests rebuild each task's real changes from ~/bench-data at test
time (no patch text lives in the repository) and skip when that data is absent.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Dict, List, Optional

from bench import cases as K
from bench import rules as R

STUDY = Path(__file__).resolve().parents[1]
RULES_DIR = STUDY / "bench" / "rules"
MANIFEST = STUDY / "bench" / "manifests" / "v1.json"
PARQUET = Path(os.path.expanduser("~/bench-data/swe-rebench-v2/data/train-00000-of-00001.parquet"))

# (repo, rule id) -> a path the old version leaves and a path the new version leaves.
EXAMPLES = {
    ("aio-libs/aiohttp", "change-note"): ("UNRELEASED.rst", "news/pending/client-redirects.rst"),
    ("aio-libs/aiohttp", "regression-test"): ("tests/regressions/test_redirects.py",
                                              "tests/issues/test_redirects.py"),
    ("python-attrs/attrs", "news-entry"): ("docs/unreleased.md", "notes/unreleased/kw-only.change.md"),
    ("python-attrs/attrs", "upgrade-note"): ("UPGRADING.md", "docs/upgrading/kw-only.md"),
    ("pallets/click", "changes-entry"): ("NEXT_RELEASE.rst", "changes/next/completion.rst"),
    ("pallets/click", "behavior-note"): ("docs/behavior-notes.rst", "docs/notes/completion.rst"),
    ("pypa/setuptools", "news-entry"): ("docs/unreleased.rst", "changes/pending/editable.rst"),
    ("pypa/setuptools", "regression-test"): ("setuptools/tests/regressions/test_editable.py",
                                             "setuptools/tests/issues/test_editable.py"),
    ("HypothesisWorks/hypothesis", "change-summary"): ("hypothesis-python/SUMMARY.rst",
                                                       "hypothesis-python/notes/shrinker.rst"),
    ("HypothesisWorks/hypothesis", "upgrade-note"): ("hypothesis-python/UPGRADING.rst",
                                                     "hypothesis-python/docs/upgrading/shrinker.rst"),
    ("Qiskit/qiskit-terra", "change-entry"): ("CHANGELOG.md", "changes/unreleased/stabilizer-equiv.md"),
    ("Qiskit/qiskit-terra", "regression-test"): ("test/python/regressions/test_stabilizer.py",
                                                 "test/python/issues/test_stabilizer.py"),
    ("Delgan/loguru", "change-entry"): ("docs/project/unreleased.rst", "changelog.d/force-color.rst"),
    ("Delgan/loguru", "behavior-note"): ("docs/behavior-notes.rst", "docs/notes/force-color.rst"),
    ("dbt-labs/dbt-redshift", "change-entry"): ("UNRELEASED.md", "docs/changes/idc-auth.md"),
    ("dbt-labs/dbt-redshift", "upgrade-note"): ("UPGRADING.md", "docs/upgrading/idc-auth.md"),
    ("PennyLaneAI/pennylane", "change-entry"): ("doc/releases/unreleased-notes.md",
                                                "doc/release-fragments/circuit-graph.md"),
    ("PennyLaneAI/pennylane", "regression-test"): ("tests/regressions/test_circuit_graph.py",
                                                   "tests/issues/test_circuit_graph.py"),
    ("stac-utils/pystac", "change-entry"): ("UNRELEASED.md", "changes/catalog-links.fixed.md"),
    ("stac-utils/pystac", "behavior-note"): ("docs/behavior-notes.rst", "docs/notes/catalog-links.rst"),
}

ISSUE = 4242  # No first-version matcher depends on the issue number; any value works.


def rule_files() -> List[Path]:
    return sorted(RULES_DIR.glob("*.json"))


def all_rules() -> Dict[str, List[R.RuleSpec]]:
    return {p.stem.replace("__", "/", 1): R.load_rules(p) for p in rule_files()}


def content_for(path: str) -> str:
    if path.endswith(".py"):
        return "def test_regression():\n    assert True\n"
    return "- Fixed the reported behavior.\n"


def example(path: str, base: Optional[R.Changes] = None) -> R.Changes:
    changes = dict(base or {})
    changes[path] = (None, content_for(path))
    return changes


def parse_patch(patch: str) -> R.Changes:
    """Approximate (base, final) per file from a unified diff: context plus removed lines
    for base, context plus added lines for final. Enough for added-line and new-file checks."""
    changes: R.Changes = {}
    path, base, final, is_new, is_deleted = None, [], [], False, False

    def flush():
        if path is not None:
            changes[path] = (None if is_new else "\n".join(base) + "\n",
                             None if is_deleted else "\n".join(final) + "\n")

    for line in patch.splitlines():
        if line.startswith("diff --git "):
            flush()
            path = line.split(" b/", 1)[1]
            base, final, is_new, is_deleted = [], [], False, False
        elif line.startswith("--- "):
            is_new = line == "--- /dev/null"
        elif line.startswith("+++ "):
            is_deleted = line == "+++ /dev/null"
        elif line.startswith("@@") or line.startswith("\\") or path is None:
            continue
        elif line.startswith("+"):
            final.append(line[1:])
        elif line.startswith("-"):
            base.append(line[1:])
        elif line.startswith(" "):
            base.append(line[1:])
            final.append(line[1:])
    flush()
    return changes


class RuleFileTests(unittest.TestCase):
    def test_about_ten_repositories(self):
        self.assertGreaterEqual(len(rule_files()), 8)
        self.assertLessEqual(len(rule_files()), 12)

    def test_every_rule_file_loads_with_two_rules(self):
        for path in rule_files():
            with self.subTest(path=path.name):
                rules = R.load_rules(path)
                self.assertEqual(len(rules), 2)
                repo = path.stem.replace("__", "/", 1)
                self.assertEqual({r.repo for r in rules}, {repo})
                entries = json.loads(path.read_text())
                self.assertTrue(all(e.get("screened") is False for e in entries))

    def test_every_rule_has_examples(self):
        found = {(repo, r.id) for repo, rules in all_rules().items() for r in rules}
        self.assertEqual(found, set(EXAMPLES))

    def test_wording_is_short(self):
        for repo, rules in all_rules().items():
            for r in rules:
                with self.subTest(repo=repo, rule=r.id):
                    for text in (r.original, r.changed):
                        self.assertLessEqual(text.count(". "), 2)
                        self.assertLess(len(text), 300)

    def test_every_rule_has_a_valid_repo_prior(self):
        for path in rule_files():
            for e in json.loads(path.read_text()):
                with self.subTest(path=path.name, rule=e["id"]):
                    self.assertIn(e.get("repo_prior"), ("old", "new", "none"))

    def test_each_wording_stands_alone(self):
        """store and creation_pin give a fresh worker only the current wording, so neither
        version may lean on the other: it names its own location and not the other's."""
        for repo, rules in all_rules().items():
            for r in rules:
                old_loc = r.old.get("dir") or r.old.get("path_glob")
                new_loc = r.new.get("dir") or r.new.get("path_glob")
                with self.subTest(repo=repo, rule=r.id):
                    self.assertIn(old_loc, r.original)
                    self.assertNotIn(new_loc, r.original)
                    self.assertIn(new_loc, r.changed)
                    self.assertNotIn(old_loc, r.changed)
                    for text in (r.original, r.changed):
                        self.assertNotRegex(text, r"(?i)\binstead\b|\bstop using\b|\bno longer\b")


class ExampleTests(unittest.TestCase):
    def test_examples_classify_as_labeled(self):
        for repo, rules in all_rules().items():
            for r in rules:
                old_path, new_path = EXAMPLES[(repo, r.id)]
                with self.subTest(repo=repo, rule=r.id):
                    self.assertEqual(R.classify(r, example(old_path), issue=ISSUE)["outcome"], "old")
                    self.assertEqual(R.classify(r, example(new_path), issue=ISSUE)["outcome"], "new")
                    self.assertEqual(R.classify(r, {}, issue=ISSUE)["outcome"], "neither")
                    both = example(new_path, example(old_path))
                    self.assertEqual(R.classify(r, both, issue=ISSUE)["outcome"], "both")

    def test_editing_an_existing_file_of_the_new_location_is_not_new(self):
        for repo, rules in all_rules().items():
            for r in rules:
                _, new_path = EXAMPLES[(repo, r.id)]
                with self.subTest(repo=repo, rule=r.id):
                    edited = {new_path: ("old text\n", "old text\nmore\n")}
                    self.assertEqual(R.classify(r, edited, issue=ISSUE)["outcome"], "neither")

    def test_rules_in_a_repository_are_independent(self):
        for repo, rules in all_rules().items():
            for r in rules:
                for other in rules:
                    if other.id == r.id:
                        continue
                    for path in EXAMPLES[(repo, other.id)]:
                        with self.subTest(repo=repo, rule=r.id, other_path=path):
                            self.assertEqual(R.classify(r, example(path), issue=ISSUE)["outcome"], "neither")

    def test_repository_convention_files_do_not_fire(self):
        """The repositories' own conventions (what a no-rule agent copies) match neither version."""
        convention = {
            "aio-libs/aiohttp": ["CHANGES/1234.bugfix.rst", "tests/test_client_functional.py"],
            "python-attrs/attrs": ["changelog.d/1234.change.md", "CHANGELOG.md"],
            "pallets/click": ["CHANGES.rst", "docs/shell-completion.rst"],
            "pypa/setuptools": ["newsfragments/1234.feature.rst", "NEWS.rst"],
            "HypothesisWorks/hypothesis": ["hypothesis-python/RELEASE.rst",
                                           "hypothesis-python/docs/changelog.rst"],
            "Qiskit/qiskit-terra": ["releasenotes/notes/fix-example-0123456789abcdef.yaml",
                                    "test/python/quantum_info/states/test_example.py"],
            "Delgan/loguru": ["CHANGELOG.rst", "docs/project/changelog.rst"],
            "dbt-labs/dbt-redshift": [".changes/unreleased/Fixes-20250101-000000.yaml", "CHANGELOG.md"],
            "PennyLaneAI/pennylane": ["doc/releases/changelog-dev.md", "tests/test_circuit_graph.py"],
            "stac-utils/pystac": ["CHANGELOG.md", "docs/api/pystac.rst"],
        }
        rules = all_rules()
        self.assertEqual(set(convention), set(rules))
        for repo, paths in convention.items():
            for r in rules[repo]:
                for path in paths:
                    with self.subTest(repo=repo, rule=r.id, path=path):
                        self.assertEqual(R.classify(r, example(path), issue=ISSUE)["outcome"], "neither")
                        edited = {path: ("x\n", "x\n- Fixed it.\n")}
                        self.assertEqual(R.classify(r, edited, issue=ISSUE)["outcome"], "neither")


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_rule_files(self):
        cases = K.load_manifest(MANIFEST)
        rules = all_rules()
        self.assertEqual({c.repo for c in cases}, set(rules))
        self.assertEqual(len(cases), 2 * len(rules))
        for c in cases:
            with self.subTest(case=c.case_id):
                ids = {r.id for r in rules[c.repo]}
                self.assertEqual({c.changed_rule, c.unchanged_rule}, ids)
                self.assertNotEqual(c.first, c.second)
                self.assertTrue(c.history)
        self.assertEqual(len({c.case_id for c in cases}), len(cases))


@unittest.skipUnless(PARQUET.exists(), "SWE-rebench V2 data not available")
class GoldPatchTests(unittest.TestCase):
    """Built from each case's real gold patches: the patch alone is neither, and the patch plus
    the rule-related file is the labeled version."""

    @classmethod
    def setUpClass(cls):
        from bench.sources import issue_number, load_rows
        cls.issue_number = staticmethod(issue_number)
        cases = K.load_manifest(MANIFEST)
        wanted = {c.first for c in cases} | {c.second for c in cases}
        cls.rows = {r.instance_id: r for r in load_rows(PARQUET) if r.instance_id in wanted}
        cls.cases = cases

    def test_gold_patches_plus_rule_files(self):
        rules = all_rules()
        for c in self.cases:
            for iid in (c.first, c.second):
                row = self.rows[iid]
                gold = parse_patch(row.patch)
                self.assertTrue(gold, iid)
                issue = self.issue_number(iid)
                for r in rules[c.repo]:
                    old_path, new_path = EXAMPLES[(c.repo, r.id)]
                    with self.subTest(task=iid, rule=r.id):
                        self.assertEqual(R.classify(r, gold, issue=issue)["outcome"], "neither")
                        self.assertEqual(R.classify(r, example(old_path, gold), issue=issue)["outcome"], "old")
                        self.assertEqual(R.classify(r, example(new_path, gold), issue=issue)["outcome"], "new")


if __name__ == "__main__":
    unittest.main()
