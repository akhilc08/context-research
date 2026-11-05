"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for an order, applying any quantity discount before tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    discount_threshold = int(settings.get("ORDER_DISCOUNT_ITEM_THRESHOLD", 40))
    discount_rate = float(settings.get("ORDER_DISCOUNT_RATE", 0.07))
    tax_rate = float(settings.get("TAX_RATE", 0.08))
    if item_count >= discount_threshold:
        subtotal *= 1 - discount_rate
    return round(subtotal * (1 + tax_rate), 2)
