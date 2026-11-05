import unittest

from app.pricing import line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(2.5, 4), 10.0)

    def test_order_total_adds_tax(self):
        self.assertEqual(order_total([(10.0, 1)]), 10.8)

    def test_bulk_discount_applies_at_40_items_before_tax(self):
        self.assertEqual(order_total([(1.0, 40)]), 40.18)

    def test_bulk_discount_does_not_apply_below_40_items(self):
        self.assertEqual(order_total([(1.0, 39)]), 42.12)

    def test_bulk_item_count_spans_multiple_lines(self):
        self.assertEqual(order_total([(1.0, 20), (2.0, 20)]), 60.26)


if __name__ == "__main__":
    unittest.main()
