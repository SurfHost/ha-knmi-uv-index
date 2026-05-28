"""Data models for the KNMI UV Index integration.

This module is intentionally free of Home Assistant imports so the parsing
logic can be unit-tested standalone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class UvForecastPoint:
    """A single UV index forecast point in time."""

    timestamp: datetime
    uv: float
    uv_clear: float | None = None


@dataclass(frozen=True, slots=True)
class UvDayMax:
    """The maximum UV index for a single day."""

    day: date
    uv_max: float


@dataclass(slots=True)
class UvData:
    """Container for the parsed UV data at a single location."""

    current: float | None = None
    current_time: datetime | None = None
    current_clear: float | None = None
    days: list[UvDayMax] = field(default_factory=list)
    points: list[UvForecastPoint] = field(default_factory=list)
    grid_latitude: float | None = None
    grid_longitude: float | None = None
    source_file: str | None = None
