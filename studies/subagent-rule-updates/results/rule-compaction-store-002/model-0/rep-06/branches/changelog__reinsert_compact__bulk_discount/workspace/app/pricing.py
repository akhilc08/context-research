"""Order pricing."""

from app.config import BULK_DISCOUNT_RATE, BULK_DISCOUNT_THRESHOLD, ORDER_TAX_RATE


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed total, applying the bulk discount before tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    if sum(qty for _, qty in lines) >= BULK_DISCOUNT_THRESHOLD:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + ORDER_TAX_RATE), 2)
