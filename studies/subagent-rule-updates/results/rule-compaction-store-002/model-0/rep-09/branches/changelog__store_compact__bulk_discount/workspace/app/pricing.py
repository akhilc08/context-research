"""Order pricing."""

from app import config


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for an order, including applicable discounts and tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= config.BULK_ORDER_ITEM_THRESHOLD:
        subtotal *= 1 - config.BULK_ORDER_DISCOUNT_RATE
    return round(subtotal * (1 + config.TAX_RATE), 2)
