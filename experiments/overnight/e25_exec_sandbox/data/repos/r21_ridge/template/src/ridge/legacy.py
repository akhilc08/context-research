"""Legacy lookup helpers."""
from ridge.config import normalize_key


def lookup(table, key, default=None):
    """Return table's value for key, matching keys case-insensitively and ignoring surrounding whitespace.
    Return default when nothing matches."""
    for k, v in table.items():
        if normalize_key(k) == normalize_key(key):
            return v
    return default
