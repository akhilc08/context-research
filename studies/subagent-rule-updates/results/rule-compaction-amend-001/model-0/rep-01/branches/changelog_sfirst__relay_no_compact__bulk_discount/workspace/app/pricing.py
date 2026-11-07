"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total after discounts and tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)

    bulk_threshold = int(settings.get("PRICING_BULK_QUANTITY_THRESHOLD", 40))
    bulk_discount = float(settings.get("PRICING_BULK_DISCOUNT_RATE", 0.07))
    tax_rate = float(settings.get("PRICING_TAX_RATE", 0.08))
    if item_count >= bulk_threshold:
        subtotal *= 1 - bulk_discount

    return round(subtotal * (1 + tax_rate), 2)
