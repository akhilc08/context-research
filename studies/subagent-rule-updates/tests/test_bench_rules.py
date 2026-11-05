from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bench import rules as R

LOG_BASE = "Changelog\n- 6000: old entry\n"


class MatcherTests(unittest.TestCase):
    def added(self, regex="^- {issue}:", glob="CHANGELOG.md"):
        return {"type": "added_line", "path_glob": glob, "line_regex": regex}

    def test_existing_entry_does_not_fire(self):
        ch = {"CHANGELOG.md": (LOG_BASE, LOG_BASE)}
        self.assertFalse(R.matches(self.added("^- 6000:"), ch, issue=6000))
        self.assertFalse(R.matches(self.added(), ch, issue=6028))

    def test_added_line_fires(self):
        ch = {"CHANGELOG.md": (LOG_BASE, LOG_BASE + "- 6028: fix redirect\n")}
        self.assertTrue(R.matches(self.added(), ch, issue=6028))

    def test_reorder_not_added(self):
        base = "- 6028: x\nb\n"
        ch = {"CHANGELOG.md": (base, "b\n- 6028: x\n")}
        self.assertFalse(R.matches(self.added(), ch, issue=6028))

    def test_duplicate_line_counts_as_added(self):
        base = "- 6028: x\n"
        ch = {"CHANGELOG.md": (base, base + base)}
        self.assertTrue(R.matches(self.added(), ch, issue=6028))

    def test_deleted_file_does_not_fire(self):
        ch = {"CHANGELOG.md": (LOG_BASE + "- 6028: x\n", None)}
        self.assertFalse(R.matches(self.added(), ch, issue=6028))

    def test_new_file_added_line(self):
        ch = {"CHANGELOG.md": (None, "- 6028: new\n")}
        self.assertTrue(R.matches(self.added(), ch, issue=6028))

    def test_glob_filters(self):
        ch = {"docs/other.md": (None, "- 6028: new\n")}
        self.assertFalse(R.matches(self.added(), ch, issue=6028))

    def test_regex_braces_preserved(self):
        m = self.added(r"^\d{2,}: {issue}$", glob="*.md")
        ch = {"a.md": ("", "12: 6028\n")}
        self.assertTrue(R.matches(m, ch, issue=6028))

    def new_file(self):
        return {"type": "new_file", "dir": "changelog",
                "name_regex": r"^{issue}\.bugfix\.rst$"}

    def test_new_file_fires(self):
        ch = {"changelog/6028.bugfix.rst": (None, "Fixed.\n")}
        self.assertTrue(R.matches(self.new_file(), ch, issue=6028))

    def test_new_file_deep_dir(self):
        ch = {"changelog/sub/6028.bugfix.rst": (None, "x")}
        self.assertTrue(R.matches(self.new_file(), ch, issue=6028))

    def test_edited_existing_file_does_not_fire(self):
        ch = {"changelog/6028.bugfix.rst": ("old", "new")}
        self.assertFalse(R.matches(self.new_file(), ch, issue=6028))

    def test_new_file_deleted_or_wrong_name(self):
        self.assertFalse(R.matches(self.new_file(),
                                   {"changelog/6028.bugfix.rst": ("a", None)}, issue=6028))
        self.assertFalse(R.matches(self.new_file(),
                                   {"changelog/6029.bugfix.rst": (None, "x")}, issue=6028))
        self.assertFalse(R.matches(self.new_file(),
                                   {"other/6028.bugfix.rst": (None, "x")}, issue=6028))

    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            R.matches({"type": "zzz"}, {}, issue=1)


class ClassifyTests(unittest.TestCase):
    def rule(self):
        return R.RuleSpec(
            id="r1", repo="o/r", original="o", changed="c",
            old={"type": "new_file", "dir": "changelog", "name_regex": r"^{issue}\.rst$"},
            new={"type": "added_line", "path_glob": "CHANGELOG.md", "line_regex": "^- {issue}:"})

    def test_all_outcomes(self):
        r = self.rule()
        old = {"changelog/1.rst": (None, "x")}
        new = {"CHANGELOG.md": ("", "- 1: x\n")}
        both = dict(old, **new)
        self.assertEqual(R.classify(r, both, issue=1),
                         {"outcome": "both", "old": True, "new": True})
        self.assertEqual(R.classify(r, old, issue=1)["outcome"], "old")
        self.assertEqual(R.classify(r, new, issue=1)["outcome"], "new")
        self.assertEqual(R.classify(r, {}, issue=1)["outcome"], "neither")


class LoadTests(unittest.TestCase):
    def entry(self, id_="a", **kw):
        d = {"id": id_, "repo": "o/r", "original": "x", "changed": "y",
             "old": {"type": "new_file", "dir": "d", "name_regex": "a"},
             "new": {"type": "added_line", "path_glob": "*", "line_regex": "b"}}
        d.update(kw)
        return d

    def load(self, entries):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "o__r.json"
            p.write_text(json.dumps(entries))
            return R.load_rules(p)

    def test_ok_with_screened(self):
        rules = self.load([self.entry("a", screened=True), self.entry("b")])
        self.assertEqual([r.id for r in rules], ["a", "b"])

    def test_duplicate_id(self):
        with self.assertRaises(ValueError):
            self.load([self.entry("a"), self.entry("a")])

    def test_unknown_matcher(self):
        with self.assertRaises(ValueError):
            self.load([self.entry(old={"type": "nope"})])

    def test_original_equals_changed(self):
        with self.assertRaises(ValueError):
            self.load([self.entry(original="same", changed="same")])


if __name__ == "__main__":
    unittest.main()
