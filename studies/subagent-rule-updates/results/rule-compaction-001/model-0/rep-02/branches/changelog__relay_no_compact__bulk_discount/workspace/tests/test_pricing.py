import unittest

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_before_tax_at_item_threshold(self):
        self.assertEqual(order_total([(1.0, 40)]), 40.18)

    def test_bulk_discount_counts_quantities_across_lines(self):
        self.assertEqual(order_total([(1.0, 20), (1.0, 20)]), 40.18)

    def test_bulk_discount_not_applied_below_item_threshold(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)


if __name__ == "__main__":
    unittest.main()
