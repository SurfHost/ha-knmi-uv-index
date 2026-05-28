"""Sensor platform for the KNMI UV Index integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UV_INDEX
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import KnmiUvConfigEntry, KnmiUvCoordinator
from .entity import KnmiUvEntity
from .models import UvData

_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _format_date(day: date) -> str:
    """Format a date like 'Saturday 30 May'."""
    return f"{_WEEKDAYS[day.weekday()]} {day.day} {_MONTHS[day.month - 1]}"


def _day_label(index: int, day: date) -> str:
    """Friendly label for a forecast day sensor."""
    if index == 0:
        return "Today"
    if index == 1:
        return "Tomorrow"
    return _format_date(day)


@dataclass(frozen=True, kw_only=True)
class KnmiUvSensorDescription(SensorEntityDescription):
    """Describes a KNMI UV Index sensor entity."""

    value_fn: Callable[[UvData], StateType]
    attrs_fn: Callable[[UvData], dict[str, Any]] | None = None
    day_index: int | None = None


def _forecast_list(data: UvData) -> list[dict[str, Any]]:
    return [
        {
            "date": day.day.isoformat(),
            "weekday": _WEEKDAYS[day.day.weekday()],
            "uv_sunny": day.uv_sunny,
            "uv_cloudy": day.uv_cloudy,
        }
        for day in data.days
    ]


def _today_attrs(data: UvData) -> dict[str, Any]:
    today = data.today
    return {
        "uv_cloudy": today.uv_cloudy if today else None,
        "date": today.day.isoformat() if today else None,
        "weekday": _WEEKDAYS[today.day.weekday()] if today else None,
        "issued": data.issued.isoformat() if data.issued else None,
        "source_file": data.source_file,
        "forecast": _forecast_list(data),
    }


CURRENT_SENSOR = KnmiUvSensorDescription(
    key="uv_current",
    name=None,
    icon="mdi:weather-sunny-alert",
    native_unit_of_measurement=UV_INDEX,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=1,
    value_fn=lambda data: data.today.uv_sunny if data.today else None,
    attrs_fn=_today_attrs,
)


def _now_attrs(data: UvData) -> dict[str, Any]:
    return {
        "clear_sky_uv_index": data.current_uv_clear,
        "time": data.current_uv_time.isoformat() if data.current_uv_time else None,
        "source": "Open-Meteo",
        "hourly": [
            {
                "time": point.time.isoformat(),
                "uv_index": point.uv,
                "uv_index_clear_sky": point.uv_clear,
            }
            for point in data.hourly
        ],
    }


NOW_SENSOR = KnmiUvSensorDescription(
    key="uv_now",
    name="Now",
    icon="mdi:weather-sunny",
    native_unit_of_measurement=UV_INDEX,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=1,
    value_fn=lambda data: data.current_uv,
    attrs_fn=_now_attrs,
)


def _day_attrs(data: UvData, index: int) -> dict[str, Any]:
    if index >= len(data.days):
        return {}
    day = data.days[index]
    return {
        "date": day.day.isoformat(),
        "weekday": _WEEKDAYS[day.day.weekday()],
        "uv_cloudy": day.uv_cloudy,
        "description": day.description,
    }


def _make_day_sensor(index: int) -> KnmiUvSensorDescription:
    return KnmiUvSensorDescription(
        key=f"uv_day_{index}",
        name=f"Day {index}",
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UV_INDEX,
        suggested_display_precision=1,
        day_index=index,
        value_fn=lambda data, n=index: data.days[n].uv_sunny if n < len(data.days) else None,
        attrs_fn=lambda data, n=index: _day_attrs(data, n),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KnmiUvConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KNMI UV Index sensors."""
    coordinator = entry.runtime_data
    num_days = len(coordinator.data.days) if coordinator.data else 0

    entities: list[KnmiUvSensor] = [
        KnmiUvSensor(coordinator, CURRENT_SENSOR),
        KnmiUvSensor(coordinator, NOW_SENSOR),
    ]
    entities.extend(KnmiUvSensor(coordinator, _make_day_sensor(i)) for i in range(num_days))
    async_add_entities(entities)


class KnmiUvSensor(KnmiUvEntity, SensorEntity):
    """A KNMI UV Index sensor."""

    entity_description: KnmiUvSensorDescription

    def __init__(
        self, coordinator: KnmiUvCoordinator, description: KnmiUvSensorDescription
    ) -> None:
        """Initialize the sensor and pin a stable entity id for day sensors."""
        super().__init__(coordinator, description)
        if description.day_index is not None:
            self.entity_id = f"sensor.{DOMAIN}_day_{description.day_index}"

    @property
    def name(self) -> str | None:
        """Return a dynamic, readable name for forecast day sensors."""
        description = self.entity_description
        if description.day_index is not None:
            data = self.coordinator.data
            if data is not None and description.day_index < len(data.days):
                return _day_label(description.day_index, data.days[description.day_index].day)
        return super().name

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.coordinator.data is None or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
