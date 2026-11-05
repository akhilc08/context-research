"""Order pricing."""

from app import config


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total after any bulk discount and tax.

    Lines are (unit_price, quantity) pairs. The bulk discount is applied to
    the subtotal before tax when the total quantity reaches the configured
    minimum.
    """
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(qty for _, qty in lines)

    if total_quantity >= config.BULK_DISCOUNT_MIN_ITEMS:
        subtotal *= 1 - config.BULK_DISCOUNT_RATE

    return round(subtotal * (1 + config.TAX_RATE), 2)
