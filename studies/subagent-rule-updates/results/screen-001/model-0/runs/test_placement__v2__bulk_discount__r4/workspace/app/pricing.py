"""Order pricing."""


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total for a list of (unit_price, quantity) pairs, including 8% tax.

    Orders with at least 40 items receive a 7% discount on the subtotal before tax.
    """
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    if sum(qty for _, qty in lines) >= 40:
        subtotal *= 0.93
    return round(subtotal * 1.08, 2)
