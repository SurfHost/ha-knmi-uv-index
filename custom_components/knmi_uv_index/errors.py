"""Exceptions for the KNMI UV Index integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class KnmiUvError(HomeAssistantError):
    """Base exception for KNMI UV Index."""


class KnmiConnectionError(KnmiUvError):
    """Raised when unable to connect to the KNMI Data Platform."""


class KnmiAuthError(KnmiUvError):
    """Raised when the API key is invalid."""


class KnmiApiError(KnmiUvError):
    """Raised when the KNMI Data Platform returns an error."""


class KnmiDataError(KnmiUvError):
    """Raised when the downloaded data cannot be parsed."""


class OpenMeteoError(KnmiUvError):
    """Raised when the Open-Meteo UV request fails."""
