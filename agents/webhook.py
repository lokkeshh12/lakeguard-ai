"""Outbound incident notifications with explicit destination configuration."""

import requests


def notify(url: str, incident_id: str, message: str) -> None:
    """Post an incident notification with a finite timeout."""
    if not url.startswith("https://"):
        raise ValueError("Webhook must use HTTPS")
    response = requests.post(
        url, json={"incident_id": incident_id, "message": message}, timeout=10
    )
    response.raise_for_status()
