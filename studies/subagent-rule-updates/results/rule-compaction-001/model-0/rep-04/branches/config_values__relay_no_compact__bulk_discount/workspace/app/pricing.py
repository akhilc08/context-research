"""Order pricing."""

from app import settings


TAX_RATE = float(settings.get("TAX_RATE", "0.08"))
BULK_DISCOUNT_MIN_ITEMS = int(settings.get("BULK_DISCOUNT_MIN_ITEMS", "40"))
BULK_DISCOUNT_RATE = float(settings.get("BULK_DISCOUNT_RATE", "0.07"))


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_items = sum(qty for _, qty in lines)
    if total_items >= BULK_DISCOUNT_MIN_ITEMS:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + TAX_RATE), 2)
