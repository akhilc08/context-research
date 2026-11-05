import unittest

from app.inventory import low_stock


class LowStockTest(unittest.TestCase):
    def test_returns_below_threshold_names_in_alphabetical_order(self):
        items = [
            {"name": "zinc", "quantity": 2},
            {"name": "bolt", "quantity": 11},
            {"name": "nut", "quantity": 12},
            {"name": "washer", "quantity": 0},
        ]

        self.assertEqual(low_stock(items), ["bolt", "washer", "zinc"])

    def test_empty_items(self):
        self.assertEqual(low_stock([]), [])


if __name__ == "__main__":
    unittest.main()
