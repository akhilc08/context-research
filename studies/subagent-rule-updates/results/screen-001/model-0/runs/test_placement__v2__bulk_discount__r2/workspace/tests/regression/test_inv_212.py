import unittest

from app.pricing import order_total


class Inv212PricingRegressionTest(unittest.TestCase):
    def test_discount_applies_at_40_total_items_before_tax(self):
        self.assertEqual(order_total([(2.5, 20), (2.5, 20)]), 100.44)

    def test_discount_does_not_apply_below_40_total_items(self):
        self.assertEqual(order_total([(2.5, 20), (2.5, 19)]), 105.3)

    def test_discount_uses_quantity_across_all_lines(self):
        self.assertEqual(order_total([(1.0, 25), (1.0, 15)]), 40.18)


if __name__ == "__main__":
    unittest.main()
