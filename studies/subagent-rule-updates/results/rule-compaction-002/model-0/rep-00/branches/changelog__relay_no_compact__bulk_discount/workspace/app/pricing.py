"""Order pricing."""

from app.config import ORDER_DISCOUNT_ITEM_THRESHOLD, ORDER_DISCOUNT_RATE, TAX_RATE


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total, applying any volume discount before tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= ORDER_DISCOUNT_ITEM_THRESHOLD:
        subtotal *= 1 - ORDER_DISCOUNT_RATE
    return round(subtotal * (1 + TAX_RATE), 2)
