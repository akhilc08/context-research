import unittest

from app.pricing import order_total


class Inv212PricingRegressionTest(unittest.TestCase):
    def test_40_items_get_seven_percent_discount_before_tax(self):
        # $400 subtotal less 7% is $372; adding 8% tax gives $401.76.
        self.assertEqual(order_total([(10.0, 40)]), 401.76)

    def test_fewer_than_40_items_do_not_get_discount(self):
        self.assertEqual(order_total([(10.0, 39)]), 421.2)

    def test_quantities_are_combined_across_lines(self):
        # The threshold is based on the total quantity in the complete order.
        self.assertEqual(order_total([(10.0, 20), (10.0, 20)]), 401.76)


if __name__ == "__main__":
    unittest.main()
