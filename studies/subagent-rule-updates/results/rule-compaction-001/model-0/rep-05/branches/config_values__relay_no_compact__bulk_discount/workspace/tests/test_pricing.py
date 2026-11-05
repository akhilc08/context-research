import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_at_total_quantity_threshold_before_tax(self):
        # Subtotal 400, less 7% = 372, then 8% tax = 401.76.
        self.assertEqual(order_total([(10.0, 20), (5.0, 0), (10.0, 20)]), 401.76)

    def test_bulk_discount_does_not_apply_below_threshold(self):
        self.assertEqual(order_total([(10.0, 39)]), 421.2)

    def test_bulk_discount_settings_can_be_overridden(self):
        def overridden_setting(name, default=None):
            return {"BULK_DISCOUNT_MIN_ITEMS": "2", "BULK_DISCOUNT_RATE": "0.1"}.get(name, default)

        with patch("app.pricing.settings.get", side_effect=overridden_setting):
            self.assertEqual(order_total([(10.0, 2)]), 19.44)


if __name__ == "__main__":
    unittest.main()
