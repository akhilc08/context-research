"""Order pricing."""

from app import settings


SALES_TAX_RATE = float(settings.get("SALES_TAX_RATE", 0.08))
BULK_DISCOUNT_ITEM_THRESHOLD = int(
    settings.get("BULK_DISCOUNT_ITEM_THRESHOLD", 40)
)
BULK_DISCOUNT_RATE = float(settings.get("BULK_DISCOUNT_RATE", 0.07))


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the tax-inclusive total, applying bulk discount before tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)

    if item_count >= BULK_DISCOUNT_ITEM_THRESHOLD:
        subtotal *= 1 - BULK_DISCOUNT_RATE

    return round(subtotal * (1 + SALES_TAX_RATE), 2)
