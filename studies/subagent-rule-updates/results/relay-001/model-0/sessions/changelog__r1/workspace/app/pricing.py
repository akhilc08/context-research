"""Order pricing."""

from app.config import BULK_DISCOUNT_RATE, BULK_DISCOUNT_THRESHOLD


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the tax-inclusive total, applying bulk discounts before tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= BULK_DISCOUNT_THRESHOLD:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * 1.08, 2)
