import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_discount_applies_at_item_threshold_before_tax(self):
        with patch("app.pricing.settings.get", side_effect=lambda name, default: default):
            self.assertEqual(order_total([(1.0, 40)]), 40 * 0.93 * 1.08)

    def test_discount_does_not_apply_below_item_threshold(self):
        with patch("app.pricing.settings.get", side_effect=lambda name, default: default):
            self.assertEqual(order_total([(1.0, 39)]), round(39 * 1.08, 2))


if __name__ == "__main__":
    unittest.main()
