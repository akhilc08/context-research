import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_to_subtotal_before_tax(self):
        self.assertEqual(order_total([(1.0, 40)]), 39.96)

    def test_bulk_discount_counts_quantities_across_lines(self):
        self.assertEqual(order_total([(1.0, 20), (1.0, 20)]), 39.96)

    def test_below_bulk_threshold_has_no_discount(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)

    def test_bulk_discount_settings_are_overridable(self):
        with patch("app.pricing.settings.get", side_effect=lambda name, default: {
            "PRICING_BULK_DISCOUNT_THRESHOLD": "2",
            "PRICING_BULK_DISCOUNT_RATE": "0.10",
            "PRICING_TAX_RATE": "0.05",
        }.get(name, default)):
            self.assertEqual(order_total([(10.0, 2)]), 18.9)


if __name__ == "__main__":
    unittest.main()
