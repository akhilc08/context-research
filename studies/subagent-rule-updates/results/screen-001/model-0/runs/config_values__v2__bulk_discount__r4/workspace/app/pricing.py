"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total, applying eligible discounts before tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)

    discount_threshold = int(settings.get("BULK_DISCOUNT_THRESHOLD", 40))
    discount_rate = float(settings.get("BULK_DISCOUNT_RATE", 0.07))
    if item_count >= discount_threshold:
        subtotal *= 1 - discount_rate

    tax_rate = float(settings.get("TAX_RATE", 0.08))
    return round(subtotal * (1 + tax_rate), 2)
