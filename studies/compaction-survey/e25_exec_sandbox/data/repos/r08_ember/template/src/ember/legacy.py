"""Legacy retry helpers."""
from ember.config import BASE_DELAY, MAX_RETRIES


def backoff_schedule():
    """Return the delay before each retry: BASE_DELAY doubled each time, one entry per retry
    (MAX_RETRIES entries in total)."""
    return [BASE_DELAY * 2 ** i for i in range(MAX_RETRIES - 1)]
