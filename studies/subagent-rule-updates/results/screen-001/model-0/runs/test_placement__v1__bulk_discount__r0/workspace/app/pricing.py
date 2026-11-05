"""Order pricing."""


def line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def order_total(lines):
    """Return the taxed total, with a 7% subtotal discount for 40+ items."""
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    item_count = sum(qty for _, qty in lines)
    if item_count >= 40:
        subtotal *= 0.93
    return round(subtotal * 1.08, 2)
