import unittest

from app.pricing import order_total


class Inv212PricingRegressionTest(unittest.TestCase):
    def test_discount_applies_at_40_items_before_tax(self):
        # $400 subtotal, less 7% ($28), then 8% tax on the discounted subtotal.
        self.assertEqual(order_total([(10.0, 40)]), 401.76)

    def test_discount_does_not_apply_below_40_items(self):
        self.assertEqual(order_total([(10.0, 39)]), 421.2)

    def test_item_quantities_are_combined_for_discount_threshold(self):
        self.assertEqual(order_total([(10.0, 20), (5.0, 20)]), 301.32)


if __name__ == "__main__":
    unittest.main()
