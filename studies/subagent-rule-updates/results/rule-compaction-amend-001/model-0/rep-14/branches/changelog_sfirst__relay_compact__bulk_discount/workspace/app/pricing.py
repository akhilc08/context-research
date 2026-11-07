"""Order pricing."""


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for an order, including discounts and 8% tax."""
    subtotal = 0
    total_quantity = 0
    for price, qty in lines:
        subtotal += line_total(price, qty)
        total_quantity += qty

    if total_quantity >= 40:
        subtotal *= 0.93
    return round(subtotal * 1.08, 2)
