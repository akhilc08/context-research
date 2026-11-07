"""Order pricing."""


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the total including tax and any applicable quantity discount."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    if sum(qty for _, qty in lines) >= 40:
        subtotal *= 0.93
    return round(subtotal * 1.08, 2)
