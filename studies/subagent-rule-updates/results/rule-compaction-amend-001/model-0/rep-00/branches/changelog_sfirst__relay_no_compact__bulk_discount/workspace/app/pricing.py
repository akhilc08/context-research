"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)

    discount_threshold = int(settings.get("PRICING_BULK_DISCOUNT_THRESHOLD", 40))
    discount_rate = float(settings.get("PRICING_BULK_DISCOUNT_RATE", 0.07))
    tax_rate = float(settings.get("PRICING_TAX_RATE", 0.08))

    if item_count >= discount_threshold:
        subtotal *= 1 - discount_rate

    return round(subtotal * (1 + tax_rate), 2)
