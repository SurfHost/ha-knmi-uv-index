"""Client for the Open-Meteo air-quality UV index API (no API key required).

Open-Meteo provides an hourly UV index (and clear-sky UV index) for any
location, derived from the CAMS model. It is used here for the live/current
UV value and the intraday curve, complementing the KNMI national forecast.
"""

from __future__ import annotations

import logging
from datetime import datetime

import aiohttp

from .errors import OpenMeteoError
from .models import UvHourPoint
from .parser import parse_open_meteo

_LOGGER = logging.getLogger(__name__)

OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


class OpenMeteoUvClient:
    """Client for fetching the current and hourly UV index from Open-Meteo."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self._session = session

    async def async_get_uv(
        self, latitude: float, longitude: float
    ) -> tuple[float | None, float | None, datetime | None, list[UvHourPoint]]:
        """Return (current_uv, current_uv_clear, current_time, hourly points)."""
        params = {
            "latitude": f"{latitude}",
            "longitude": f"{longitude}",
            "current": "uv_index,uv_index_clear_sky",
            "hourly": "uv_index,uv_index_clear_sky",
            "timezone": "auto",
            "forecast_days": "2",
        }
        try:
            async with self._session.get(
                OPEN_METEO_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise OpenMeteoError(f"Cannot reach Open-Meteo: {err}") from err

        return parse_open_meteo(payload)
