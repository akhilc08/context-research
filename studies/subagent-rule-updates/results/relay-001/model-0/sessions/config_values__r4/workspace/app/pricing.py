"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed total, applying a discount to qualifying order subtotals."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    discount_min_items = int(settings.get("ORDER_DISCOUNT_MIN_ITEMS", 40))
    discount_rate = float(settings.get("ORDER_DISCOUNT_RATE", 0.07))
    tax_rate = float(settings.get("TAX_RATE", 0.08))
    if item_count >= discount_min_items:
        subtotal *= 1 - discount_rate
    return round(subtotal * (1 + tax_rate), 2)
