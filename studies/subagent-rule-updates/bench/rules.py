"""Rule specs and matchers for the rule-change benchmark.

A matcher inspects file changes (base content vs final content) and says
whether the worker's edits satisfy one version of a rule. Content that
existed at the base commit never counts: only lines added relative to base
and files absent at base can fire.
"""
from __future__ import annotations

import collections
import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Changes = Dict[str, Tuple[Optional[str], Optional[str]]]

MATCHER_TYPES = ("new_file", "added_line")


@dataclass(frozen=True)
class RuleSpec:
    id: str
    repo: str
    original: str
    changed: str
    old: dict
    new: dict


def _fill(pattern: str, issue: int) -> str:
    return pattern.replace("{issue}", re.escape(str(issue)))


def _added_lines(base: Optional[str], final: str) -> List[str]:
    """Lines of final that appear more times there than in base (multiset)."""
    remaining = collections.Counter((base or "").splitlines())
    added = []
    for line in final.splitlines():
        if remaining[line] > 0:
            remaining[line] -= 1
        else:
            added.append(line)
    return added


def matches(matcher: dict, changes: Changes, *, issue: int) -> bool:
    kind = matcher.get("type")
    if kind == "new_file":
        prefix = matcher["dir"].rstrip("/") + "/"
        rx = re.compile(_fill(matcher["name_regex"], issue))
        for path, (base, final) in changes.items():
            if base is not None or final is None:
                continue
            if path.startswith(prefix) and rx.fullmatch(path.rsplit("/", 1)[-1]):
                return True
        return False
    if kind == "added_line":
        rx = re.compile(_fill(matcher["line_regex"], issue))
        for path, (base, final) in changes.items():
            if final is None or not fnmatch.fnmatch(path, matcher["path_glob"]):
                continue
            if any(rx.search(line) for line in _added_lines(base, final)):
                return True
        return False
    raise ValueError("unknown matcher type: %r" % (kind,))


def classify(rule: RuleSpec, changes: Changes, *, issue: int) -> dict:
    old = matches(rule.old, changes, issue=issue)
    new = matches(rule.new, changes, issue=issue)
    if old and new:
        outcome = "both"
    elif new:
        outcome = "new"
    elif old:
        outcome = "old"
    else:
        outcome = "neither"
    return {"outcome": outcome, "old": old, "new": new}


def load_rules(path: Path) -> List[RuleSpec]:
    entries = json.loads(Path(path).read_text())
    seen = set()
    rules = []
    for e in entries:
        rule = RuleSpec(id=e["id"], repo=e["repo"], original=e["original"],
                        changed=e["changed"], old=e["old"], new=e["new"])
        if rule.id in seen:
            raise ValueError("duplicate rule id: %s" % rule.id)
        seen.add(rule.id)
        if rule.original == rule.changed:
            raise ValueError("rule %s: original equals changed" % rule.id)
        for m in (rule.old, rule.new):
            if m.get("type") not in MATCHER_TYPES:
                raise ValueError("rule %s: unknown matcher type %r" % (rule.id, m.get("type")))
        rules.append(rule)
    return rules
