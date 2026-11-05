import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_is_applied_before_tax(self):
        self.assertEqual(order_total([(1.0, 40)]), 40.18)

    def test_bulk_discount_counts_quantities_across_lines(self):
        with patch("app.pricing.settings.get", side_effect=lambda name, default=None: {
            "PRICING_BULK_DISCOUNT_THRESHOLD": "40",
            "PRICING_BULK_DISCOUNT_RATE": "0.07",
            "PRICING_TAX_RATE": "0.08",
        }.get(name, default)):
            self.assertEqual(order_total([(1.0, 20), (1.0, 20)]), 40.18)


if __name__ == "__main__":
    unittest.main()
