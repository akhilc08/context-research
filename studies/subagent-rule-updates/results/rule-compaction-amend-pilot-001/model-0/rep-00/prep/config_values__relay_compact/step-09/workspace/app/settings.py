"""Settings that can be overridden with environment variables."""
import os


def get(name, default=None):
    """Return the environment variable `name`, or `default` when it is unset."""
    return os.environ.get(name, default)
