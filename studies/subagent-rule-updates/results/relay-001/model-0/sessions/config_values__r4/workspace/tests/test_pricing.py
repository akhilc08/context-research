import os
import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_order_discount_applies_at_40_total_items_before_tax(self):
        self.assertEqual(order_total([(1.0, 39), (1.0, 1)]), 40.18)

    def test_order_discount_does_not_apply_below_40_items(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)

    def test_pricing_settings_can_be_overridden_by_environment(self):
        overrides = {
            "ORDER_DISCOUNT_MIN_ITEMS": "2",
            "ORDER_DISCOUNT_RATE": "0.1",
            "TAX_RATE": "0.2",
        }
        with patch.dict(os.environ, overrides):
            self.assertEqual(order_total([(10.0, 2)]), 21.6)


if __name__ == "__main__":
    unittest.main()
