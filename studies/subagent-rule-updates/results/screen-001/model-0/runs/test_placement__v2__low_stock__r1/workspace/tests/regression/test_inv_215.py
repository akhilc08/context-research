import unittest

from app.inventory import low_stock


class LowStockTest(unittest.TestCase):
    def test_returns_names_below_threshold_in_alphabetical_order(self):
        items = [
            {"name": "zinc", "quantity": 11},
            {"name": "bolt", "quantity": 3},
            {"name": "nut", "quantity": 12},
            {"name": "washer", "quantity": 0},
        ]

        self.assertEqual(low_stock(items), ["bolt", "washer", "zinc"])

    def test_returns_empty_list_when_no_items_are_low(self):
        self.assertEqual(low_stock([{"name": "nut", "quantity": 12}]), [])


if __name__ == "__main__":
    unittest.main()
