import unittest

from app.inventory import find, low_stock, total_quantity

ITEMS = [{"name": "bolt", "quantity": 30}, {"name": "nut", "quantity": 4}]


class InventoryTest(unittest.TestCase):
    def test_total_quantity(self):
        self.assertEqual(total_quantity(ITEMS), 34)

    def test_find(self):
        self.assertEqual(find(ITEMS, "nut")["quantity"], 4)
        self.assertIsNone(find(ITEMS, "gear"))

    def test_low_stock_returns_below_threshold_names_sorted(self):
        items = [
            {"name": "zinc", "quantity": 11},
            {"name": "at_threshold", "quantity": 12},
            {"name": "alpha", "quantity": 0},
        ]
        self.assertEqual(low_stock(items), ["alpha", "zinc"])

    def test_low_stock_empty_input(self):
        self.assertEqual(low_stock([]), [])


if __name__ == "__main__":
    unittest.main()
