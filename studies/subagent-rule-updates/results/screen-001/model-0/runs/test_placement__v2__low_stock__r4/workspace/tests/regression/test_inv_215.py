import unittest

from app.inventory import low_stock


class LowStockTest(unittest.TestCase):
    def test_returns_names_below_threshold_sorted_alphabetically(self):
        items = [
            {"name": "zinc", "quantity": 3},
            {"name": "bolt", "quantity": 12},
            {"name": "washer", "quantity": 11},
            {"name": "nut", "quantity": 0},
        ]

        self.assertEqual(low_stock(items), ["nut", "washer", "zinc"])

    def test_empty_items_returns_empty_list(self):
        self.assertEqual(low_stock([]), [])


if __name__ == "__main__":
    unittest.main()
