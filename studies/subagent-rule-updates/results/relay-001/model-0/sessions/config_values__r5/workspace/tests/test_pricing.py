import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_at_40_items_before_tax(self):
        self.assertEqual(order_total([(1.0, 40)]), 40.18)

    def test_bulk_discount_counts_items_across_lines(self):
        self.assertEqual(order_total([(1.0, 20), (1.0, 20)]), 40.18)

    def test_no_bulk_discount_below_40_items(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)

    def test_pricing_tunables_can_be_overridden_by_environment(self):
        overrides = {
            "BULK_DISCOUNT_MIN_ITEMS": "2",
            "BULK_DISCOUNT_RATE": "0.10",
            "ORDER_TAX_RATE": "0.05",
        }
        with patch.dict("os.environ", overrides):
            self.assertEqual(order_total([(10.0, 2)]), 18.9)


if __name__ == "__main__":
    unittest.main()
