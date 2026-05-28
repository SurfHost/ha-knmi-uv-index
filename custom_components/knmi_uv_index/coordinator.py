"""DataUpdateCoordinator for the KNMI UV Index integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import KnmiUvClient
from .const import DOMAIN
from .errors import KnmiApiError, KnmiAuthError, KnmiConnectionError
from .models import UvData
from .parser import UvParseError, parse_uv_xml, select_today

_LOGGER = logging.getLogger(__name__)

type KnmiUvConfigEntry = ConfigEntry[KnmiUvCoordinator]


class KnmiUvCoordinator(DataUpdateCoordinator[UvData]):
    """Coordinator that downloads and parses the KNMI UV (zonkracht) forecast."""

    config_entry: KnmiUvConfigEntry

    def __init__(self, hass: HomeAssistant, client: KnmiUvClient, scan_interval: int) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._raw: bytes | None = None
        self._raw_filename: str | None = None

    async def _async_update_data(self) -> UvData:
        """Fetch the latest forecast file (if new) and parse it."""
        try:
            filename = await self.client.async_get_latest_filename()
            if filename != self._raw_filename or self._raw is None:
                url = await self.client.async_get_download_url(filename)
                self._raw = await self.client.async_download_file(url)
                self._raw_filename = filename
                _LOGGER.debug("Downloaded new KNMI UV file: %s", filename)
        except KnmiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (KnmiConnectionError, KnmiApiError) as err:
            raise UpdateFailed(str(err)) from err

        try:
            data = parse_uv_xml(self._raw)
        except UvParseError as err:
            raise UpdateFailed(f"Could not parse KNMI UV data: {err}") from err

        data.source_file = self._raw_filename
        data.today = select_today(data, dt_util.now().date())
        return data
