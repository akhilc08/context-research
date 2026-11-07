"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including 8% tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    bulk_threshold = int(settings.get("BULK_ORDER_MIN_ITEMS", 40))
    bulk_discount = float(settings.get("BULK_ORDER_DISCOUNT", 0.07))
    if item_count >= bulk_threshold:
        subtotal *= 1 - bulk_discount
    return round(subtotal * 1.08, 2)
