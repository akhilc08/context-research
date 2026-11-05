import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applied_before_tax_at_threshold(self):
        self.assertEqual(order_total([(1.0, 40)]), 39.96)

    def test_bulk_discount_not_applied_below_threshold(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)

    def test_bulk_discount_settings_are_configurable(self):
        with patch.dict("os.environ", {
            "PRICING_BULK_DISCOUNT_THRESHOLD": "2",
            "PRICING_BULK_DISCOUNT_RATE": "0.10",
        }):
            self.assertEqual(order_total([(10.0, 2)]), 19.44)


if __name__ == "__main__":
    unittest.main()
