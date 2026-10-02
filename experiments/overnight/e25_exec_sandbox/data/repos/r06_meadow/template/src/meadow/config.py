"""Shared settings. Owned by the platform team."""

DEFAULT_REGION = "us-east"


def normalize_key(key):
    """Strip surrounding whitespace from a lookup key."""
    return key.strip()
