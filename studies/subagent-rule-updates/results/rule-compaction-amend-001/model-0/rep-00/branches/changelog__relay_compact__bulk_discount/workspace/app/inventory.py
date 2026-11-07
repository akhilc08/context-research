"""Inventory queries."""


def total_quantity(items):
    """Sum the quantity of every item. Items are dicts with name and quantity."""
    return sum(item["quantity"] for item in items)


def find(items, name):
    """Return the item called `name`, or None."""
    for item in items:
        if item["name"] == name:
            return item
    return None
