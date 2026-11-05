"""Legacy tag parsing."""
from beacon.config import SEPARATOR


def split_tags(text):
    """Split text on SEPARATOR, strip whitespace around each tag, and drop empty tags."""
    return [t for t in text.split(SEPARATOR)]
