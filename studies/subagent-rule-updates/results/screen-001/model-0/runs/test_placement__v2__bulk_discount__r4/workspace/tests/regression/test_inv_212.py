import unittest

from app.pricing import order_total


class LargeOrderDiscountTest(unittest.TestCase):
    def test_exactly_40_items_get_discount_before_tax(self):
        # 40 * $10 = $400; 7% off gives $372, then 8% tax gives $401.76.
        self.assertEqual(order_total([(10.0, 40)]), 401.76)

    def test_fewer_than_40_items_do_not_get_discount(self):
        self.assertEqual(order_total([(10.0, 39)]), 421.2)

    def test_quantities_are_summed_across_lines(self):
        self.assertEqual(order_total([(10.0, 20), (5.0, 20)]), 301.32)


if __name__ == "__main__":
    unittest.main()
