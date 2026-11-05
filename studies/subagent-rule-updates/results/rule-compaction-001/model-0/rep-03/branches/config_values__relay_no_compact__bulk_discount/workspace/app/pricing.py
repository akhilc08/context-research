"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed order total, discounting orders over the configured quantity."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    quantity_threshold = int(settings.get("BULK_DISCOUNT_QUANTITY", "40"))
    discount_rate = float(settings.get("BULK_DISCOUNT_RATE", "0.07"))
    tax_rate = float(settings.get("TAX_RATE", "0.08"))

    if sum(qty for _, qty in lines) >= quantity_threshold:
        subtotal *= 1 - discount_rate

    return round(subtotal * (1 + tax_rate), 2)
