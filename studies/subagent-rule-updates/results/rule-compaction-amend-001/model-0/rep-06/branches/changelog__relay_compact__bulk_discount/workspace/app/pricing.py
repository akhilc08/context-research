"""Order pricing."""

from app import config


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(quantity for _, quantity in lines)
    if total_quantity >= config.BULK_ORDER_ITEM_THRESHOLD:
        subtotal *= 1 - config.BULK_ORDER_DISCOUNT_RATE
    return round(subtotal * (1 + config.ORDER_TAX_RATE), 2)
