import unittest

from app.pricing import order_total


class Inv212PricingRegressionTest(unittest.TestCase):
    def test_40_items_receive_discount_before_tax(self):
        self.assertEqual(order_total([(10.0, 40)]), 401.76)

    def test_fewer_than_40_items_do_not_receive_discount(self):
        self.assertEqual(order_total([(10.0, 39)]), 421.2)


if __name__ == "__main__":
    unittest.main()
