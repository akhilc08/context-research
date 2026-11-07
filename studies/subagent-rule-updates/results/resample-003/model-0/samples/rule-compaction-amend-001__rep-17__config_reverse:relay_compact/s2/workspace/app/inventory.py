"""Inventory queries."""

from app.config import LOW_STOCK_THRESHOLD


def total_quantity(items):
    """Sum the quantity of every item. Items are dicts with name and quantity."""
    return sum(item["quantity"] for item in items)


def find(items, name):
    """Return the item called `name`, or None."""
    for item in items:
        if item["name"] == name:
            return item
    return None


def low_stock(items):
    """Return alphabetized names of items below the low-stock threshold."""
    return sorted(
        item["name"] for item in items
        if item["quantity"] < LOW_STOCK_THRESHOLD
    )
