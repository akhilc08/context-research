"""Order pricing."""


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including 8% tax."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    return round(subtotal * 1.08, 2)
