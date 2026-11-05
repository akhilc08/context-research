"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the tax-inclusive total for order lines, applying volume discounts."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    discount_threshold = int(settings.get("ORDER_DISCOUNT_MIN_ITEMS", 40))
    discount_rate = float(settings.get("ORDER_DISCOUNT_RATE", 0.07))
    if item_count >= discount_threshold:
        subtotal *= 1 - discount_rate
    return round(subtotal * 1.08, 2)
