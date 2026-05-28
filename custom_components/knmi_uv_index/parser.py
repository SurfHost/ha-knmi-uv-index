"""Parsing of the KNMI UV index (zonkrachtverwachting) XML files.

The KNMI ``uv_index`` dataset publishes a small XML document
(``zonkrachtverwachting_*.xml``) with a national UV forecast for the
Netherlands: for each of the next days it gives the UV index ("zonkracht")
for sunny weather and for cloudy weather.

This module is intentionally free of Home Assistant imports so it can be
unit-tested standalone, and it only uses the standard library.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from xml.etree import ElementTree

from .models import UvData, UvDayForecast, UvHourPoint

_LOGGER = logging.getLogger(__name__)

FIELD_SUNNY = "zonkracht_zonnig"
FIELD_CLOUDY = "zonkracht_bewolkt"


class UvParseError(Exception):
    """Raised when the KNMI XML cannot be interpreted."""


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    return element.text.strip()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    dt = _parse_datetime(value)
    return dt.date() if dt else None


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_float_any(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_uv_xml(raw: bytes) -> UvData:
    """Parse a KNMI zonkrachtverwachting XML document."""
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as err:
        raise UvParseError(f"Invalid KNMI XML: {err}") from err

    metadata = root.find("metadata")
    if metadata is None:
        raise UvParseError("KNMI XML is missing the <metadata> element")

    issued = _parse_datetime(_text(metadata.find("report_info/report_dtg_issued")))

    # Map valid_id -> (date, description).
    periods: dict[str, tuple[date, str]] = {}
    for period in metadata.findall("report_valid_periods/report_valid_period"):
        valid_id = _text(period.find("valid_id"))
        start = _parse_date(_text(period.find("valid_start")))
        descr = _text(period.find("valid_descr")) or ""
        if valid_id and start:
            periods[valid_id] = (start, descr)

    if not periods:
        raise UvParseError("KNMI XML contains no valid forecast periods")

    # Collect field values per valid_id. Prefer the NL location if present.
    locations = root.findall("data/location")
    if not locations:
        raise UvParseError("KNMI XML contains no <data>/<location> element")
    location = next(
        (loc for loc in locations if _text(loc.find("location_id")) == "NL"),
        locations[0],
    )

    values: dict[tuple[str, str], float | None] = {}
    for block in location.findall("block"):
        field_id = _text(block.find("field_id"))
        valid_id = _text(block.find("valid_id"))
        if field_id and valid_id:
            values[(field_id, valid_id)] = _to_float(_text(block.find("field_content")))

    days: list[UvDayForecast] = []
    for valid_id, (day, descr) in periods.items():
        days.append(
            UvDayForecast(
                day=day,
                valid_id=valid_id,
                description=descr,
                uv_sunny=values.get((FIELD_SUNNY, valid_id)),
                uv_cloudy=values.get((FIELD_CLOUDY, valid_id)),
            )
        )

    days.sort(key=lambda d: d.day)
    if not days:
        raise UvParseError("KNMI XML produced no forecast days")

    return UvData(days=days, issued=issued)


def select_today(data: UvData, today: date) -> UvDayForecast | None:
    """Return the forecast for `today`, falling back to the earliest day."""
    for day in data.days:
        if day.day == today:
            return day
    return data.days[0] if data.days else None


def parse_open_meteo(
    payload: dict[str, Any],
) -> tuple[float | None, float | None, datetime | None, list[UvHourPoint]]:
    """Parse an Open-Meteo air-quality response into (uv, uv_clear, time, hourly)."""
    current = payload.get("current") or {}
    current_uv = _to_float_any(current.get("uv_index"))
    current_clear = _to_float_any(current.get("uv_index_clear_sky"))
    current_time = _parse_datetime(current.get("time"))

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    uv_values = hourly.get("uv_index") or []
    clear_values = hourly.get("uv_index_clear_sky") or []

    points: list[UvHourPoint] = []
    for index, raw_time in enumerate(times):
        timestamp = _parse_datetime(raw_time)
        if timestamp is None:
            continue
        uv = _to_float_any(uv_values[index]) if index < len(uv_values) else None
        clear = _to_float_any(clear_values[index]) if index < len(clear_values) else None
        points.append(UvHourPoint(time=timestamp, uv=uv, uv_clear=clear))

    return current_uv, current_clear, current_time, points
