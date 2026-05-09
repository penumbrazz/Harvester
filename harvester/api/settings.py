"""API settings for Harvester."""

import os


class APISettings:
    """Load API configuration from environment variables."""

    def __init__(self) -> None:
        self.api_token = os.environ.get("HARVESTER_API_TOKEN", "")
        self.database_url = os.environ.get("HARVESTER_DATABASE_URL", "")


def get_api_settings() -> APISettings:
    """Return cached API settings."""
    return APISettings()
