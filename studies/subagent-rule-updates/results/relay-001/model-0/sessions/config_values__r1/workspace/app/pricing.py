"""Order pricing."""

from app.settings import get


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return an order total after any bulk discount and tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    threshold = int(get("BULK_DISCOUNT_ITEM_THRESHOLD", 40))
    discount_rate = float(get("BULK_DISCOUNT_RATE", 0.07))
    tax_rate = float(get("TAX_RATE", 0.08))
    if item_count >= threshold:
        subtotal *= 1 - discount_rate
    return round(subtotal * (1 + tax_rate), 2)
