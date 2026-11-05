import os
import unittest
from unittest.mock import patch

from app.inventory import find, low_stock, total_quantity

ITEMS = [{"name": "bolt", "quantity": 30}, {"name": "nut", "quantity": 4}]


class InventoryTest(unittest.TestCase):
    def test_total_quantity(self):
        self.assertEqual(total_quantity(ITEMS), 34)

    def test_find(self):
        self.assertEqual(find(ITEMS, "nut")["quantity"], 4)
        self.assertIsNone(find(ITEMS, "gear"))

    def test_low_stock_sorts_names_and_excludes_threshold(self):
        items = [
            {"name": "zinc", "quantity": 11},
            {"name": "alpha", "quantity": 3},
            {"name": "boundary", "quantity": 12},
        ]
        self.assertEqual(low_stock(items), ["alpha", "zinc"])

    def test_low_stock_threshold_can_be_overridden(self):
        with patch.dict(os.environ, {"LOW_STOCK_THRESHOLD": "20"}):
            self.assertEqual(low_stock([{"name": "part", "quantity": 19}]), ["part"])


if __name__ == "__main__":
    unittest.main()
