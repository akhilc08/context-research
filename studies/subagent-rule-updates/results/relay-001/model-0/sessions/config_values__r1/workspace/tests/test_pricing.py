import os
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

    def test_bulk_discount_does_not_apply_below_40_items(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)

    def test_item_count_combines_all_lines(self):
        self.assertEqual(order_total([(1.0, 20), (1.0, 20)]), 40.18)

    def test_pricing_values_can_be_overridden_by_environment(self):
        values = {
            "BULK_DISCOUNT_ITEM_THRESHOLD": "2",
            "BULK_DISCOUNT_RATE": "0.5",
            "TAX_RATE": "0",
        }
        with patch.dict(os.environ, values):
            self.assertEqual(order_total([(1.0, 2)]), 1.0)


if __name__ == "__main__":
    unittest.main()
