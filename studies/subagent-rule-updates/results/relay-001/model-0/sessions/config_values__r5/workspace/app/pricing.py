"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for an order, including tax and any qualifying bulk discount."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_items = sum(qty for _, qty in lines)
    discount_min_items = int(settings.get("BULK_DISCOUNT_MIN_ITEMS", 40))
    discount_rate = float(settings.get("BULK_DISCOUNT_RATE", 0.07))
    tax_rate = float(settings.get("ORDER_TAX_RATE", 0.08))
    if total_items >= discount_min_items:
        subtotal *= 1 - discount_rate
    return round(subtotal * (1 + tax_rate), 2)
