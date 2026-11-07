import unittest

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_order_discount_at_40_items_is_applied_before_tax(self):
        self.assertEqual(order_total([(1.0, 40)]), 40.18)

    def test_order_discount_counts_items_across_lines(self):
        self.assertEqual(order_total([(2.0, 20), (3.0, 20)]), 100.44)

    def test_order_with_fewer_than_40_items_has_no_discount(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)


if __name__ == "__main__":
    unittest.main()
