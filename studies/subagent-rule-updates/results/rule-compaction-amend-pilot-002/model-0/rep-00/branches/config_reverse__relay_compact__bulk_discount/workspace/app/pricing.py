"""Order pricing."""


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total, including 8% tax and any qualifying quantity discount."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(qty for _, qty in lines)
    if total_quantity >= 40:
        subtotal *= 0.93
    return round(subtotal * 1.08, 2)
