"""Offline tests for tunable extraction and session labels, including adversarial cases."""
import unittest

from bench import tunables as T

BASE = '''import os


def fetch(url, timeout=10):
    return get(url, timeout=timeout)
'''


def forms(changes):
    return sorted((c["value"], c["form"]) for c in T.extract(changes)["candidates"])


class ExtractTests(unittest.TestCase):
    def test_inline_function_default(self):
        final = BASE.replace("def fetch(url, timeout=10):", "def fetch(url, timeout=10, retries=3):")
        self.assertEqual(forms({"pkg/net.py": (BASE, final)}), [(3.0, "inline")])

    def test_const_form_needs_use(self):
        used = BASE + "\nMAX_RETRIES = 3\n\n\ndef again():\n    return MAX_RETRIES\n"
        unused = BASE + "\nMAX_RETRIES = 3\n"
        self.assertEqual(forms({"pkg/net.py": (BASE, used)}), [(3.0, "const")])
        self.assertEqual(forms({"pkg/net.py": (BASE, unused)}), [(3.0, "inline")])

    def test_env_form_with_string_and_number_defaults(self):
        string = BASE + '\nMAX_RETRIES = int(os.environ.get("PKG_MAX_RETRIES", "3"))\nX = MAX_RETRIES\n'
        number = BASE + '\nDELAY = float(os.getenv("PKG_DELAY", 0.5))\nY = DELAY\n'
        self.assertEqual(forms({"pkg/net.py": (BASE, string)}), [(3.0, "env")])
        self.assertEqual(forms({"pkg/net.py": (BASE, number)}), [(0.5, "env")])

    def test_env_read_inside_function_is_inline(self):
        final = BASE + '\n\ndef delay():\n    return float(os.environ.get("PKG_DELAY", "2.5"))\n'
        self.assertEqual(forms({"pkg/net.py": (BASE, final)}), [(2.5, "inline")])
        final2 = BASE + '\n\ndef delay():\n    return float(os.environ.get("PKG_DELAY", 2.5))\n'
        self.assertEqual(forms({"pkg/net.py": (BASE, final2)}), [(2.5, "inline")])

    def test_moved_value_is_not_added(self):
        moved = BASE.replace("timeout=10", "timeout=DEFAULT_TIMEOUT") + "\nDEFAULT_TIMEOUT = 10\n"
        self.assertEqual(forms({"pkg/net.py": (BASE, moved)}), [])

    def test_trivial_values_tests_and_class_attributes(self):
        final = BASE + "\n\ndef f(x):\n    return x[0] + 1 - 1\n\n\nclass C:\n    LIMIT = 50\n"
        self.assertEqual(forms({"pkg/net.py": (BASE, final)}), [(50.0, "inline")])
        self.assertEqual(forms({"tests/test_net.py": (None, "LIMIT = 50\nx = LIMIT\n")}), [])
        self.assertEqual(forms({"pkg/conftest.py": (None, "LIMIT = 50\n")}), [])

    def test_version_comparisons_are_skipped(self):
        final = BASE + "\n\nimport sys\nif sys.version_info >= (3, 11) and x > 250:\n    pass\nif PY_VERSION < (3, 8):\n    pass\n"
        self.assertEqual(forms({"pkg/net.py": (BASE, final)}), [(250.0, "inline")])

    def test_negative_values_count_once(self):
        final = BASE + "\n\ndef f(x):\n    return x > -5\n"
        self.assertEqual(forms({"pkg/net.py": (BASE, final)}), [(-5.0, "inline")])

    def test_new_file_and_cross_file_move(self):
        self.assertEqual(forms({"pkg/new.py": (None, "WAIT = 30\n\n\ndef w():\n    return WAIT\n")}), [(30.0, "const")])
        a_base, a_final = "def f(t=30):\n    return t\n", "from pkg.b import T\n\n\ndef f(t=T):\n    return t\n"
        self.assertEqual(forms({"pkg/a.py": (a_base, a_final), "pkg/b.py": (None, "T = 30\n")}), [])

    def test_unparsable_file_is_reported(self):
        out = T.extract({"pkg/bad.py": (BASE, "def broken(:\n")})
        self.assertEqual((out["candidates"], out["unscorable"]), ([], ["pkg/bad.py"]))

    def test_snippet_and_ids(self):
        final = BASE.replace("def fetch(url, timeout=10):", "def fetch(url, timeout=10, retries=3):")
        c = T.extract({"pkg/net.py": (BASE, final)})["candidates"][0]
        self.assertEqual((c["id"], c["path"], c["line"]), (0, "pkg/net.py", 4))
        self.assertIn("retries=3", c["snippet"])


class LabelTests(unittest.TestCase):
    C = [{"id": 0, "form": "inline"}, {"id": 1, "form": "const"}, {"id": 2, "form": "env"}]

    def test_labels(self):
        self.assertEqual(T.label_session("const", self.C, [], []), "no_tunable")
        self.assertEqual(T.label_session("const", self.C, [], ["x.py"]), "unscorable")
        self.assertEqual(T.label_session("const", self.C, [1, 2], []), "follows")
        self.assertEqual(T.label_session("env", self.C, [1, 2], []), "partial")
        self.assertEqual(T.label_session("env", self.C, [2], []), "follows")
        self.assertEqual(T.label_session("env", self.C, [0], []), "violates")
        self.assertEqual(T.label_session("none", self.C, [0, 1], []), "bare")
        self.assertEqual(T.label_session("none", self.C, [1], []), "named")

    def test_messages(self):
        self.assertEqual(T.first_message("none", "Fix it."), "Task: Fix it.")
        self.assertIn("os.environ.get", T.first_message("env", "Fix it."))
        self.assertTrue(T.RULES["env"].startswith(T.RULES["const"].split(" at module level")[0]))


if __name__ == "__main__":
    unittest.main()
