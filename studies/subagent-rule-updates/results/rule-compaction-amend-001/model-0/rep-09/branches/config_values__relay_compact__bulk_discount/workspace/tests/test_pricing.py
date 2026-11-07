import unittest

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_order_with_39_items_has_no_discount(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)

    def test_order_with_40_items_discount_applied_before_tax(self):
        self.assertEqual(order_total([(1.0, 40)]), 40.18)

    def test_item_count_summed_across_lines(self):
        self.assertEqual(order_total([(1.0, 20), (1.0, 20)]), 40.18)


if __name__ == "__main__":
    unittest.main()
