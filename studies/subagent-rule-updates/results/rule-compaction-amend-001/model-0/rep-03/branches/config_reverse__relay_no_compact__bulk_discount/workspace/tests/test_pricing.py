import unittest

from app import config
from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_at_item_threshold_before_tax(self):
        self.assertEqual(
            order_total([(10.0, config.BULK_DISCOUNT_ITEM_THRESHOLD)]),
            round(10.0 * config.BULK_DISCOUNT_ITEM_THRESHOLD * (1 - config.BULK_DISCOUNT_RATE) * 1.08, 2),
        )

    def test_bulk_discount_does_not_apply_below_item_threshold(self):
        quantity = config.BULK_DISCOUNT_ITEM_THRESHOLD - 1
        self.assertEqual(order_total([(10.0, quantity)]), round(10.0 * quantity * 1.08, 2))


if __name__ == "__main__":
    unittest.main()
