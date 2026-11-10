"""Tunable-value rules for the real-task study (docs/real-task-study-design.md).

Two rules with the same scope: R-const (a named module-level constant in the file that uses it) and
R-env (the same, read from an environment variable). Scoring has two steps:

1. extract(): deterministic. Every numeric literal added to non-test Python source, other than 0, 1 and
   -1, plus numeric strings given as the default of an environment read, with its form:
   "env"    the default of os.environ.get / os.getenv inside the value of a module-level UPPER_CASE
            assignment whose name is used in the file,
   "const"  inside the value of a module-level UPPER_CASE assignment (no environment read) whose name
            is used in the file,
   "inline" anywhere else (function default, call argument, comparison, class attribute, ...).
   A value counts as added only if it appears more often in the changed files than at base and its
   line is new, so values that only moved are excluded.
2. Adjudication (adjudicate_tunables.py) decides which extracted values are tunables. label_session()
   then combines the forms of the tunables into a session label.
"""
from __future__ import annotations

import ast
import collections
import re
from typing import Dict, List, Optional, Tuple

Changes = Dict[str, Tuple[Optional[str], Optional[str]]]

SCOPE = "tunable values such as thresholds, rates, limits, timeouts, retry counts, intervals, or sizes"
RULES = {
    "const": ("Define each new %s as a named UPPER_CASE constant at module level in the file that uses it, "
              "and use that constant instead of writing the number directly." % SCOPE),
    "env": ("Define each new %s as a named UPPER_CASE constant at module level in the file that uses it, read "
            "from an environment variable with a default and a type conversion, for example "
            "TIMEOUT = float(os.environ.get(\"PROJECT_TIMEOUT\", \"30\")), and use that constant instead of "
            "writing the number directly." % SCOPE),
}
ARMS = ("none", "const", "env")
TEST_PATH = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_tests?\.py$|(^|/)conftest\.py$")
UPPER = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
ENV_CALLS = {"getenv", "get"}
TRIVIAL = {0.0, 1.0, -1.0}
CONTEXT_LINES = 3


def first_message(arm: str, problem_statement: str) -> str:
    if arm == "none":
        return "Task: %s" % problem_statement
    return "Project rule from the user: %s\n\nTask: %s" % (RULES[arm], problem_statement)


def scorable_path(path: str) -> bool:
    return path.endswith(".py") and not TEST_PATH.search(path)


def _number(node: ast.AST) -> Optional[float]:
    """The value of a numeric literal, with a leading minus folded in. Booleans are not numbers."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        inner = _number(node.operand)
        return None if inner is None else (-inner if isinstance(node.op, ast.USub) else inner)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    return None


def _is_env_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr in ENV_CALLS:
        if f.attr == "getenv":
            return True
        target = f.value  # os.environ.get / environ.get
        return (isinstance(target, ast.Attribute) and target.attr == "environ") or (
            isinstance(target, ast.Name) and target.id == "environ")
    return isinstance(f, ast.Name) and f.id == "getenv"


def _env_default(call: ast.Call) -> Optional[ast.AST]:
    if len(call.args) >= 2:
        return call.args[1]
    for kw in call.keywords:
        if kw.arg in ("default", "value"):
            return kw.value
    return None


def _string_number(node: ast.AST) -> Optional[float]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return float(node.value.strip())
        except ValueError:
            return None
    return None


def _names_used(tree: ast.AST) -> collections.Counter:
    return collections.Counter(n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))


def _occurrences(source: str) -> List[dict]:
    """Every scorable numeric occurrence in a module with its form. Raises SyntaxError."""
    tree = ast.parse(source)
    used = _names_used(tree)
    # The operand of a folded minus is not counted separately, so -5 is one occurrence.
    folded = {id(n.operand) for n in ast.walk(tree) if isinstance(n, ast.UnaryOp) and _number(n) is not None}
    found: List[dict] = []
    seen = set()

    def add(node: ast.AST, value: float, form: str, name: Optional[str]) -> None:
        if value in TRIVIAL or id(node) in seen:
            return
        seen.add(id(node))
        found.append({"value": value, "line": node.lineno, "form": form, "name": name})

    # Module-level UPPER_CASE assignments first, so their literals get const or env forms.
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            targets, value = stmt.targets, stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            targets, value = [stmt.target], stmt.value
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if not names or len(names) != len(targets) or not all(UPPER.match(n) for n in names):
            continue
        is_used = any(used[n] > 0 for n in names)
        defaults = []
        for call in (n for n in ast.walk(value) if _is_env_call(n)):
            default = _env_default(call)
            if default is not None:
                defaults.append(default)
                number = _string_number(default)
                if number is None:
                    number = _number(default)
                if number is not None:
                    add(default, number, "env" if is_used else "inline", names[0])
        for node in ast.walk(value):
            if id(node) in folded or any(node is d for d in defaults):
                continue
            number = _number(node)
            if number is not None:
                add(node, number, "const" if is_used else "inline", names[0])
    for node in ast.walk(tree):
        if id(node) in folded:
            continue
        number = _number(node)
        if number is None and _is_env_call(node):
            default = _env_default(node)
            number = _string_number(default) if default is not None else None
            if number is not None:
                add(default, number, "inline", None)  # An environment read outside a module constant.
            continue
        if number is not None:
            add(node, number, "inline", None)
    return found


def extract(changes: Changes) -> dict:
    """Added numeric values in non-test Python files. Returns {"candidates": [...], "unscorable": [...]}."""
    base_counts: collections.Counter = collections.Counter()
    final_items: List[dict] = []
    unscorable: List[str] = []
    for path, (base, final) in sorted(changes.items()):
        if not scorable_path(path) or final is None:
            continue
        try:
            occ = _occurrences(final)
            base_occ = _occurrences(base) if base is not None else []
        except SyntaxError:
            unscorable.append(path)
            continue
        base_lines = collections.Counter(line.strip() for line in (base or "").splitlines())
        lines = final.splitlines()
        for o in base_occ:
            base_counts[o["value"]] += 1
        for o in occ:
            text = lines[o["line"] - 1].strip() if 0 < o["line"] <= len(lines) else ""
            o.update({"path": path, "text": text, "new_line": base_lines[text] == 0,
                      "snippet": "\n".join(lines[max(0, o["line"] - 1 - CONTEXT_LINES):o["line"] + CONTEXT_LINES])})
            final_items.append(o)
    final_counts = collections.Counter(o["value"] for o in final_items)
    candidates = []
    for value in sorted(final_counts):
        surplus = final_counts[value] - base_counts[value]
        if surplus <= 0:
            continue
        new = [o for o in final_items if o["value"] == value and o["new_line"]]
        candidates += new
    for i, c in enumerate(candidates):
        c["id"] = i
        c.pop("new_line", None)
    return {"candidates": candidates, "unscorable": unscorable}


def label_session(arm: str, candidates: List[dict], tunable_ids: List[int], unscorable: List[str]) -> str:
    """Combine adjudicated tunables into one label.

    no_tunable: no adjudicated tunable was added. unscorable: a changed file did not parse and no
    tunable was found elsewhere. For a told arm: follows (every tunable in the told form; env also
    satisfies const), partial, or violates. For the none arm: bare (at least one inline tunable) or
    named (every tunable already in a named form)."""
    tunables = [c for c in candidates if c["id"] in set(tunable_ids)]
    if not tunables:
        return "unscorable" if unscorable else "no_tunable"
    forms = [c["form"] for c in tunables]
    if arm == "none":
        return "bare" if "inline" in forms else "named"
    ok = {"const": ("const", "env"), "env": ("env",)}[arm]
    good = sum(f in ok for f in forms)
    return "follows" if good == len(forms) else ("violates" if good == 0 else "partial")
