import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_at_40_total_items_before_tax(self):
        self.assertEqual(order_total([(10.0, 20), (5.0, 20)]), 301.32)

    def test_bulk_discount_not_applied_below_threshold(self):
        self.assertEqual(order_total([(10.0, 39)]), 421.2)

    def test_bulk_discount_settings_can_be_overridden(self):
        with patch("app.pricing.settings.get", side_effect=lambda name, default: {
            "PRICING_BULK_QUANTITY_THRESHOLD": "2",
            "PRICING_BULK_DISCOUNT_RATE": "0.1",
            "PRICING_TAX_RATE": "0.05",
        }.get(name, default)):
            self.assertEqual(order_total([(10.0, 2)]), 18.9)


if __name__ == "__main__":
    unittest.main()
