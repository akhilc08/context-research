"""Order pricing."""

from app.config import (
    BULK_ORDER_DISCOUNT_RATE,
    BULK_ORDER_MIN_ITEMS,
    ORDER_TAX_RATE,
)


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for lines, including bulk discount and tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= BULK_ORDER_MIN_ITEMS:
        subtotal *= 1 - BULK_ORDER_DISCOUNT_RATE
    return round(subtotal * (1 + ORDER_TAX_RATE), 2)
