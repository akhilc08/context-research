"""Order pricing."""


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including 8% tax."""
    lines = list(lines)
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    total_quantity = sum(qty for _, qty in lines)
    if total_quantity >= 40:
        subtotal *= 0.93
    return round(subtotal * 1.08, 2)
