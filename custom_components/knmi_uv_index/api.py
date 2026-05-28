"""Client for the KNMI Data Platform Open Data API."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import DATASET_NAME, DATASET_VERSION, KNMI_API_BASE
from .errors import KnmiApiError, KnmiAuthError, KnmiConnectionError

_LOGGER = logging.getLogger(__name__)

_LIST_PARAM_VARIANTS: tuple[dict[str, str], ...] = (
    {"maxKeys": "1", "orderBy": "created", "sorting": "desc"},
    {"maxKeys": "1", "orderBy": "lastModified", "sorting": "desc"},
    {"maxKeys": "1", "sorting": "desc"},
)


class KnmiUvClient:
    """Client for downloading UV index files from the KNMI Data Platform."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key

    @property
    def _files_url(self) -> str:
        return f"{KNMI_API_BASE}/datasets/{DATASET_NAME}/versions/{DATASET_VERSION}/files"

    async def _get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        """Perform an authenticated GET request and return parsed JSON."""
        try:
            async with self._session.get(
                url,
                params=params,
                headers={"Authorization": self._api_key},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status in (401, 403):
                    raise KnmiAuthError("Invalid KNMI Data Platform API key")
                if response.status == 429:
                    raise KnmiApiError("KNMI Data Platform rate limit exceeded")
                if response.status >= 400:
                    text = await response.text()
                    raise KnmiApiError(f"KNMI API error {response.status}: {text[:200]}")
                return await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise KnmiConnectionError(f"Cannot connect to the KNMI Data Platform: {err}") from err

    async def async_validate_key(self) -> bool:
        """Validate the API key by listing the dataset files."""
        await self._get_json(self._files_url, {"maxKeys": "1"})
        return True

    async def async_get_latest_filename(self) -> str:
        """Return the filename of the most recent file in the dataset."""
        last_error: KnmiApiError | None = None
        for params in _LIST_PARAM_VARIANTS:
            try:
                data = await self._get_json(self._files_url, params)
            except KnmiApiError as err:
                last_error = err
                continue
            files = data.get("files") or []
            if files:
                filename = files[0].get("filename")
                if filename:
                    return str(filename)
        if last_error is not None:
            raise last_error
        raise KnmiApiError(f"No files available for dataset '{DATASET_NAME}'")

    async def async_get_download_url(self, filename: str) -> str:
        """Return a temporary download URL for the given file."""
        data = await self._get_json(f"{self._files_url}/{filename}/url")
        url = data.get("temporaryDownloadUrl")
        if not url:
            raise KnmiApiError(f"No download URL returned for '{filename}'")
        return str(url)

    async def async_download_file(self, url: str) -> bytes:
        """Download the raw file bytes from a temporary download URL."""
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                return await response.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise KnmiConnectionError(f"Cannot download KNMI file: {err}") from err

    async def async_get_latest_file(self) -> tuple[str, bytes]:
        """Fetch the latest file: returns (filename, raw bytes)."""
        filename = await self.async_get_latest_filename()
        url = await self.async_get_download_url(filename)
        raw = await self.async_download_file(url)
        return filename, raw
