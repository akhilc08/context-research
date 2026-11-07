"""Order pricing."""

from app import config


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for lines, applying any bulk discount before tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= config.BULK_DISCOUNT_MIN_ITEMS:
        subtotal = round(subtotal * (1 - config.BULK_DISCOUNT_RATE), 2)
    return round(subtotal * (1 + config.TAX_RATE), 2)
