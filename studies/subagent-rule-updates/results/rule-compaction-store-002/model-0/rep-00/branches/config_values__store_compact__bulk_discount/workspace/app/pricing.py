"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including 8% tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_threshold = int(settings.get("ORDER_DISCOUNT_MIN_ITEMS", 40))
    discount_rate = float(settings.get("ORDER_DISCOUNT_RATE", 0.07))
    if sum(qty for _, qty in lines) >= item_threshold:
        subtotal *= 1 - discount_rate
    return round(subtotal * 1.08, 2)
