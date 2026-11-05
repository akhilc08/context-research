"""Order pricing."""

from app.config import BULK_DISCOUNT_MIN_ITEMS, BULK_DISCOUNT_RATE, TAX_RATE


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total including applicable discounts and tax."""
    item_count = sum(quantity for _, quantity in lines)
    subtotal = sum(line_total(price, quantity) for price, quantity in lines)
    if item_count >= BULK_DISCOUNT_MIN_ITEMS:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + TAX_RATE), 2)
