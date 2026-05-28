"""Constants for the KNMI UV Index integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "knmi_uv_index"

CONF_API_KEY: Final = "api_key"
CONF_LATITUDE: Final = "latitude"
CONF_LONGITUDE: Final = "longitude"
CONF_LOCATION_NAME: Final = "location_name"
CONF_ZONE: Final = "zone"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCAN_INTERVAL: Final = 900
MIN_SCAN_INTERVAL: Final = 300
MAX_SCAN_INTERVAL: Final = 21600

DEFAULT_MAX_DAYS: Final = 8

KNMI_API_BASE: Final = "https://api.dataplatform.knmi.nl/open-data/v1"
DATASET_NAME: Final = "uv_index"
DATASET_VERSION: Final = "1.0"

MANUFACTURER: Final = "KNMI"
ATTRIBUTION: Final = "Data provided by the KNMI Data Platform (uv-index dataset)"
REGISTER_URL: Final = "https://developer.dataplatform.knmi.nl/register/"
