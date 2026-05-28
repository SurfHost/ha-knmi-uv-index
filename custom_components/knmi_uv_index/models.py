"""Data models for the KNMI UV Index integration.

This module is intentionally free of Home Assistant imports so the parsing
logic can be unit-tested standalone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class UvDayForecast:
    """UV index forecast for a single day (national, the Netherlands)."""

    day: date
    valid_id: str
    description: str
    uv_sunny: float | None
    uv_cloudy: float | None


@dataclass(slots=True)
class UvData:
    """Container for the parsed KNMI UV (zonkracht) forecast."""

    days: list[UvDayForecast] = field(default_factory=list)
    issued: datetime | None = None
    source_file: str | None = None
    today: UvDayForecast | None = None
