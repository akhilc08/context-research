"""Order pricing."""

from app.settings import get


TAX_RATE = float(get("TAX_RATE", 0.08))
BULK_DISCOUNT_THRESHOLD = int(get("BULK_DISCOUNT_THRESHOLD", 40))
BULK_DISCOUNT_RATE = float(get("BULK_DISCOUNT_RATE", 0.07))


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed total, applying any bulk discount before tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(qty for _, qty in lines)
    if total_quantity >= BULK_DISCOUNT_THRESHOLD:
        subtotal *= 1 - BULK_DISCOUNT_RATE
    return round(subtotal * (1 + TAX_RATE), 2)
