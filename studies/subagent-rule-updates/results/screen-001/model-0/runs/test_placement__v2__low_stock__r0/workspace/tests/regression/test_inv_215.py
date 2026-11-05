import unittest

from app.inventory import low_stock


class LowStockTest(unittest.TestCase):
    def test_returns_names_below_threshold_sorted_alphabetically(self):
        items = [
            {"name": "zinc", "quantity": 3},
            {"name": "bolt", "quantity": 11},
            {"name": "nut", "quantity": 12},
            {"name": "washer", "quantity": 0},
        ]

        self.assertEqual(low_stock(items), ["bolt", "washer", "zinc"])

    def test_empty_inventory(self):
        self.assertEqual(low_stock([]), [])


if __name__ == "__main__":
    unittest.main()
