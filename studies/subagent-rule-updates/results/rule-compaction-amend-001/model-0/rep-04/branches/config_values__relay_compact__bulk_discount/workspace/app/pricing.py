"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed total for ``(unit_price, quantity)`` pairs."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    bulk_threshold = int(settings.get("ORDER_BULK_THRESHOLD", 40))
    bulk_discount = float(settings.get("ORDER_BULK_DISCOUNT", 0.07))
    if sum(qty for _, qty in lines) >= bulk_threshold:
        subtotal *= 1 - bulk_discount
    return round(subtotal * 1.08, 2)
