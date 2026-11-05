"""Order pricing."""

from app.config import (
    BULK_ORDER_DISCOUNT_MIN_ITEMS,
    BULK_ORDER_DISCOUNT_RATE,
    ORDER_TAX_RATE,
)


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the tax-inclusive total for a list of (unit_price, quantity) pairs."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(quantity for _, quantity in lines)
    discount_rate = (
        BULK_ORDER_DISCOUNT_RATE
        if item_count >= BULK_ORDER_DISCOUNT_MIN_ITEMS
        else 0
    )
    discounted_subtotal = subtotal * (1 - discount_rate)
    return round(discounted_subtotal * (1 + ORDER_TAX_RATE), 2)
