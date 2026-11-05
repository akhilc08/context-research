"""Thin HTTP client for the inventory API."""
import json
import urllib.request

from app import config, settings


def fetch(path):
    """GET a JSON document from the inventory API."""
    request = urllib.request.Request(
        f"{config.BASE_URL}/{path.lstrip('/')}",
        headers={"Authorization": f"Bearer {settings.get('INVENTORY_API_KEY', '')}"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())
