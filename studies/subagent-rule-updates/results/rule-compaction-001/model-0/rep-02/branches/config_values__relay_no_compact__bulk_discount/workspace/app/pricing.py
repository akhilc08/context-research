"""Order pricing."""

from app.settings import get


BULK_DISCOUNT_ITEM_THRESHOLD = int(get("BULK_DISCOUNT_ITEM_THRESHOLD", 40))
BULK_DISCOUNT_RATE = float(get("BULK_DISCOUNT_RATE", 0.07))
TAX_RATE = float(get("TAX_RATE", 0.08))


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed order total, applying any qualifying bulk discount first."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= BULK_DISCOUNT_ITEM_THRESHOLD:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + TAX_RATE), 2)
