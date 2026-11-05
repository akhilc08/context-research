"""Order pricing."""

from app.settings import get


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    discount_threshold = int(get("BULK_DISCOUNT_ITEM_THRESHOLD", 40))
    discount_rate = float(get("BULK_DISCOUNT_RATE", 0.07))
    if item_count >= discount_threshold:
        subtotal *= 1 - discount_rate
    return round(subtotal * 1.08, 2)
