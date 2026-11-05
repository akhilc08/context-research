"""Order pricing."""

from app import settings


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the order total, including tax and any applicable bulk discount."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    threshold = int(settings.get("BULK_ORDER_ITEM_THRESHOLD", 40))
    discount_rate = float(settings.get("BULK_ORDER_DISCOUNT_RATE", 0.07))
    sales_tax_rate = float(settings.get("SALES_TAX_RATE", 0.08))
    if item_count >= threshold:
        subtotal *= 1 - discount_rate
    return round(subtotal * (1 + sales_tax_rate), 2)
