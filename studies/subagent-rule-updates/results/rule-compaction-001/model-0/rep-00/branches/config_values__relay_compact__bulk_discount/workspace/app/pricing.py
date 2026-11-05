"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including 8% tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(qty for _, qty in lines)
    bulk_quantity_min = int(settings.get("PRICING_BULK_QUANTITY_MIN", 40))
    bulk_discount_rate = float(settings.get("PRICING_BULK_DISCOUNT_RATE", 0.07))
    if total_quantity >= bulk_quantity_min:
        subtotal *= 1 - bulk_discount_rate
    return round(subtotal * 1.08, 2)
