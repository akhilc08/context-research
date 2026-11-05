"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for order lines, including applicable discounts and 8% tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    discount_min_items = int(settings.get("PRICING_BULK_DISCOUNT_MIN_ITEMS", 40))
    discount_rate = float(settings.get("PRICING_BULK_DISCOUNT_RATE", 0.07))
    if item_count >= discount_min_items:
        subtotal *= 1 - discount_rate
    return round(subtotal * 1.08, 2)
