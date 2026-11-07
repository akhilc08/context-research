"""Order pricing."""

from app.config import (
    BULK_DISCOUNT_MIN_ITEMS,
    BULK_DISCOUNT_RATE,
    TAX_RATE,
)


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(qty for _, qty in lines)
    if total_quantity >= BULK_DISCOUNT_MIN_ITEMS:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + TAX_RATE), 2)
