"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return total including tax and any eligible bulk discount."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    quantity = sum(qty for _, qty in lines)
    discount_threshold = int(settings.get("ORDER_BULK_DISCOUNT_THRESHOLD", 40))
    discount_rate = float(settings.get("ORDER_BULK_DISCOUNT_RATE", 0.07))
    if quantity >= discount_threshold:
        subtotal *= 1 - discount_rate
    return round(subtotal * 1.08, 2)
