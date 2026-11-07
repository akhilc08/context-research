"""Order pricing."""

from app import config


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return an order total, applying eligible discounts before tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= config.VOLUME_DISCOUNT_MIN_ITEMS:
        subtotal *= 1 - config.VOLUME_DISCOUNT_RATE
    return round(subtotal * (1 + config.SALES_TAX_RATE), 2)
