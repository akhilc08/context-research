import unittest

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_order_total_applies_discount_at_40_items_before_tax(self):
        self.assertEqual(order_total([(1.0, 40)]), 40 * 0.93 * 1.08)

    def test_order_total_does_not_discount_fewer_than_40_items(self):
        self.assertEqual(order_total([(1.0, 39)]), round(39 * 1.08, 2))


if __name__ == "__main__":
    unittest.main()
