"""Order pricing."""

from app.config import ORDER_DISCOUNT_MIN_ITEMS, ORDER_DISCOUNT_RATE


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total, including applicable discounts and 8% tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_items = sum(qty for _, qty in lines)
    if total_items >= ORDER_DISCOUNT_MIN_ITEMS:
        subtotal *= 1 - ORDER_DISCOUNT_RATE
    return round(subtotal * 1.08, 2)
