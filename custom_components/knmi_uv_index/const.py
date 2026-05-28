"""Constants for the KNMI UV Index integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "knmi_uv_index"

CONF_API_KEY: Final = "api_key"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCAN_INTERVAL: Final = 3600
MIN_SCAN_INTERVAL: Final = 900
MAX_SCAN_INTERVAL: Final = 86400

KNMI_API_BASE: Final = "https://api.dataplatform.knmi.nl/open-data/v1"
DATASET_NAME: Final = "uv_index"
DATASET_VERSION: Final = "1.0"

MANUFACTURER: Final = "KNMI"
ATTRIBUTION: Final = "Data provided by the KNMI Data Platform (uv-index dataset)"
REGISTER_URL: Final = "https://developer.dataplatform.knmi.nl/register/"
