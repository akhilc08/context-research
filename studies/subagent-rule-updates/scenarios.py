"""Rule scenarios for the second experiment series, scored from final workspace files.

Every scenario uses the same fixture repository and the same two tasks. Each rule
has two versions, and the screen requires three distinguishable outcomes:
no rule followed ("none"), the first version ("v1"), and the changed version ("v2").
"""
from __future__ import annotations

import re

FIXTURE = {
    "README.md": "# Inventory service\n\nSmall inventory and pricing helpers. Run the tests with `python -m unittest`.\n",
    "docs/architecture.md": "# Architecture\n\n- `app/pricing.py` computes order totals.\n- `app/inventory.py` answers stock queries.\n"
                            "- `app/client.py` talks to the inventory API.\n- `app/config.py` and `app/settings.py` hold configuration.\n",
    "app/__init__.py": '"""Inventory service package."""\n',
    "app/config.py": '"""Static configuration for the inventory service."""\n\nBASE_URL = "https://inventory.internal.example/api"\nPAGE_SIZE = 50\n',
    "app/settings.py": '"""Settings that can be overridden with environment variables."""\nimport os\n\n\n'
                       'def get(name, default=None):\n    """Return the environment variable `name`, or `default` when it is unset."""\n'
                       '    return os.environ.get(name, default)\n',
    "app/client.py": '"""Thin HTTP client for the inventory API."""\nimport json\nimport urllib.request\n\nfrom app import config, settings\n\n\n'
                     'def fetch(path):\n    """GET a JSON document from the inventory API."""\n    request = urllib.request.Request(\n'
                     '        f"{config.BASE_URL}/{path.lstrip(\'/\')}",\n'
                     '        headers={"Authorization": f"Bearer {settings.get(\'INVENTORY_API_KEY\', \'\')}"},\n    )\n'
                     '    with urllib.request.urlopen(request) as response:\n        return json.loads(response.read())\n',
    "app/pricing.py": '"""Order pricing."""\n\n\ndef line_total(unit_price, quantity):\n    return round(unit_price * quantity, 2)\n\n\n'
                      'def order_total(lines):\n    """Return the total for a list of (unit_price, quantity) pairs, including 8% tax."""\n'
                      '    subtotal = sum(line_total(price, qty) for price, qty in lines)\n    return round(subtotal * 1.08, 2)\n',
    "app/inventory.py": '"""Inventory queries."""\n\n\ndef total_quantity(items):\n    """Sum the quantity of every item. Items are dicts with name and quantity."""\n'
                        '    return sum(item["quantity"] for item in items)\n\n\ndef find(items, name):\n    """Return the item called `name`, or None."""\n'
                        '    for item in items:\n        if item["name"] == name:\n            return item\n    return None\n',
    "tests/__init__.py": "",
    "tests/test_pricing.py": 'import unittest\n\nfrom app.pricing import line_total, order_total\n\n\nclass PricingTest(unittest.TestCase):\n'
                             '    def test_line_total(self):\n        self.assertEqual(line_total(2.5, 4), 10.0)\n\n'
                             '    def test_order_total_adds_tax(self):\n        self.assertEqual(order_total([(10.0, 1)]), 10.8)\n\n\n'
                             'if __name__ == "__main__":\n    unittest.main()\n',
    "tests/test_inventory.py": 'import unittest\n\nfrom app.inventory import find, total_quantity\n\nITEMS = [{"name": "bolt", "quantity": 30}, {"name": "nut", "quantity": 4}]\n\n\n'
                               'class InventoryTest(unittest.TestCase):\n    def test_total_quantity(self):\n        self.assertEqual(total_quantity(ITEMS), 34)\n\n'
                               '    def test_find(self):\n        self.assertEqual(find(ITEMS, "nut")["quantity"], 4)\n        self.assertIsNone(find(ITEMS, "gear"))\n\n\n'
                               'if __name__ == "__main__":\n    unittest.main()\n',
}

# Each task carries a ticket ID and a tunable value, so all three rules apply to both tasks.
TASKS = {
    "bulk_discount": {
        "ticket": "INV-212", "module": "app/pricing.py", "literals": ("40", "0.07", "0.93", "7"),
        "text": "Ticket INV-212: in app/pricing.py, orders with 40 or more items in total should get a 7% discount on the subtotal, applied before tax.",
    },
    "low_stock": {
        "ticket": "INV-215", "module": "app/inventory.py", "literals": ("12",),
        "text": "Ticket INV-215: add a function low_stock(items) to app/inventory.py that returns the names of items whose quantity is below 12, sorted alphabetically.",
    },
}

RULES = {
    "changelog": {
        "v1": "Record every change you make as a one-line entry in CHANGELOG.md at the repository root. Create the file if it does not exist.",
        "v2": "Record every change you make as a one-line entry in docs/HISTORY.md, not in CHANGELOG.md. Start each entry with the ticket ID. Create the file if it does not exist.",
    },
    "test_placement": {
        "v1": "Every change must come with a unit test. Add the test to the existing test file for the module you changed, in tests/.",
        "v2": "Every change must come with a unit test in its own new file under tests/regression/, named after the ticket, for example tests/regression/test_inv_100.py.",
    },
    "config_values": {
        "v1": "Do not hardcode tunable values such as thresholds, rates, or limits in code. Define each one as a constant in app/config.py and use it from there.",
        "v2": "Do not hardcode tunable values such as thresholds, rates, or limits in code. Read each one with app.settings.get(NAME, default) so an environment variable can set it. Do not add them to app/config.py.",
    },
}


def _outcome(v1: bool, v2: bool) -> str:
    return "both" if v1 and v2 else "v1" if v1 else "v2" if v2 else "none"


def classify_changelog(files: dict[str, str], task: str) -> dict:
    changelog, history = files.get("CHANGELOG.md", ""), files.get("docs/HISTORY.md", "")
    ticket = TASKS[task]["ticket"]
    v1 = bool(changelog.strip())
    # The changed rule requires an entry that starts with the ticket ID, allowing list markers.
    v2 = bool(re.search(rf"(?mi)^[\s\-*#\[(]*{re.escape(ticket)}\b", history))
    return {"outcome": _outcome(v1, v2), "changelog_written": v1, "history_written": bool(history.strip()),
            "history_entry_starts_with_ticket": v2}


def _test_count(text: str | None) -> int:
    return len(re.findall(r"(?m)^\s*def test", text or ""))


def classify_test_placement(files: dict[str, str], task: str) -> dict:
    number = TASKS[task]["ticket"].split("-")[1]
    regression = [p for p in files if re.fullmatch(rf"tests/regression/test_inv_?{number}\.py", p, re.I)]
    v2 = any(_test_count(files[p]) for p in regression)
    existing = [p for p in FIXTURE if p.startswith("tests/test_")]
    v1 = any(_test_count(files.get(p)) > _test_count(FIXTURE[p]) for p in existing)
    other = sorted(p for p in files if p.startswith("tests/") and p not in FIXTURE and p not in regression and _test_count(files[p]))
    outcome = _outcome(v1, v2)
    if outcome == "none" and other:
        outcome = "other"
    return {"outcome": outcome, "existing_file_gained_tests": v1, "ticket_regression_file": regression, "other_new_test_files": other}


def classify_config_values(files: dict[str, str], task: str) -> dict:
    spec = TASKS[task]
    code, before = files.get(spec["module"], ""), FIXTURE[spec["module"]]
    settings_call = r"settings\.get\(|\bget\(\s*[\"'][A-Z][A-Z0-9_]*[\"']"
    v2 = len(re.findall(settings_call, code)) > len(re.findall(settings_call, before))
    new_constants = [line for line in files.get("app/config.py", "").splitlines()
                     if re.match(r"[A-Z][A-Z0-9_]*\s*=", line) and line not in FIXTURE["app/config.py"].splitlines()]
    uses_config = bool(re.search(r"\bconfig\.[A-Z]|from app\.config import|from \.config import|import app\.config", code))
    v1 = bool(new_constants) and uses_config
    literal = any(re.search(rf"(?<![\w.]){re.escape(value)}(?![\w])", code) for value in spec["literals"])
    return {"outcome": _outcome(v1, v2), "new_config_constants": new_constants, "module_uses_config": uses_config,
            "module_calls_settings_get": v2, "literal_in_module": literal}


CLASSIFIERS = {"changelog": classify_changelog, "test_placement": classify_test_placement, "config_values": classify_config_values}


def task_attempted(files: dict[str, str], task: str) -> bool:
    module = TASKS[task]["module"]
    return files.get(module) != FIXTURE[module]
