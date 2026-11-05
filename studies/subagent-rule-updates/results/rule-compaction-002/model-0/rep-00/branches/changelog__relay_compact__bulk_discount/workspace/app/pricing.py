"""Order pricing."""

from app.config import BULK_DISCOUNT_MIN_ITEMS, BULK_DISCOUNT_RATE, ORDER_TAX_RATE


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total after applicable discounts and tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_items = sum(qty for _, qty in lines)
    if total_items >= BULK_DISCOUNT_MIN_ITEMS:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + ORDER_TAX_RATE), 2)
