"""Static configuration for the inventory service."""

BASE_URL = "https://inventory.internal.example/api"
PAGE_SIZE = 50

# Pricing configuration.
TAX_RATE = 0.08
BULK_DISCOUNT_MIN_ITEMS = 40
BULK_DISCOUNT_RATE = 0.07

# Inventory configuration.
LOW_STOCK_THRESHOLD = 12
