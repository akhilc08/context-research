"""Order pricing."""

from app import config


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total, applying bulk discounts before 8% tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(qty for _, qty in lines)

    if total_quantity >= config.BULK_ORDER_DISCOUNT_THRESHOLD:
        subtotal *= 1 - config.BULK_ORDER_DISCOUNT_RATE

    return round(subtotal * 1.08, 2)
