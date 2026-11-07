"""Order pricing."""

from app.config import BULK_ORDER_DISCOUNT_RATE, BULK_ORDER_ITEM_THRESHOLD


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total, including tax and any qualifying bulk discount."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= BULK_ORDER_ITEM_THRESHOLD:
        subtotal *= 1 - BULK_ORDER_DISCOUNT_RATE
    return round(subtotal * 1.08, 2)
