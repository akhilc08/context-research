import unittest
from unittest.mock import patch

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_before_tax_at_40_items(self):
        self.assertEqual(order_total([(10.0, 40)]), 401.76)

    def test_bulk_discount_threshold_is_configurable(self):
        with patch("app.settings.get", side_effect=lambda name, default: "2" if name.endswith("MIN_ITEMS") else "0.1"):
            self.assertEqual(order_total([(10.0, 2)]), 19.44)


if __name__ == "__main__":
    unittest.main()
