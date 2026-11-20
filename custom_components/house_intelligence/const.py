"""Constants for House Intelligence."""

from datetime import timedelta

DOMAIN = "house_intelligence"
PLATFORMS = ["sensor"]
UPDATE_INTERVAL = timedelta(minutes=5)

CONF_NAME = "name"
DEFAULT_NAME = "House"
