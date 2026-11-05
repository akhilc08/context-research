import unittest

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_order_of_40_items_gets_discount_before_tax(self):
        self.assertEqual(order_total([(10.0, 40)]), 401.76)

    def test_order_below_40_items_has_no_discount(self):
        self.assertEqual(order_total([(10.0, 39)]), 421.2)

    def test_item_quantities_are_summed_across_lines(self):
        self.assertEqual(order_total([(10.0, 20), (5.0, 20)]), 302.4)


if __name__ == "__main__":
    unittest.main()
