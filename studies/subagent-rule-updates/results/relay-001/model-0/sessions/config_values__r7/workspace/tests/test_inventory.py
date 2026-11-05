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

    def test_low_stock_returns_names_sorted_alphabetically(self):
        items = [
            {"name": "washer", "quantity": 11},
            {"name": "bolt", "quantity": 3},
            {"name": "nut", "quantity": 12},
        ]
        self.assertEqual(low_stock(items), ["bolt", "washer"])

    def test_low_stock_uses_environment_backed_threshold(self):
        with patch("app.inventory.settings.get", return_value="5"):
            self.assertEqual(low_stock(ITEMS), ["nut"])


if __name__ == "__main__":
    unittest.main()
