"""Order pricing."""

from app.config import (
    BULK_DISCOUNT_ITEM_THRESHOLD,
    BULK_DISCOUNT_RATE,
    ORDER_TAX_RATE,
)


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed total, applying any bulk discount before tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= BULK_DISCOUNT_ITEM_THRESHOLD:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + ORDER_TAX_RATE), 2)
