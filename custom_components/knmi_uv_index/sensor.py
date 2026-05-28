"""Sensor platform for the KNMI UV Index integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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

from .coordinator import KnmiUvConfigEntry
from .entity import KnmiUvEntity
from .models import UvData


@dataclass(frozen=True, kw_only=True)
class KnmiUvSensorDescription(SensorEntityDescription):
    """Describes a KNMI UV Index sensor entity."""

    value_fn: Callable[[UvData], StateType]
    attrs_fn: Callable[[UvData], dict[str, Any]] | None = None


def _forecast_list(data: UvData) -> list[dict[str, Any]]:
    return [
        {"date": day.day.isoformat(), "uv_sunny": day.uv_sunny, "uv_cloudy": day.uv_cloudy}
        for day in data.days
    ]


def _today_attrs(data: UvData) -> dict[str, Any]:
    today = data.today
    return {
        "uv_cloudy": today.uv_cloudy if today else None,
        "date": today.day.isoformat() if today else None,
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


def _day_name(index: int) -> str:
    if index == 0:
        return "Today"
    if index == 1:
        return "Tomorrow"
    return f"+{index} days"


def _make_day_sensor(index: int) -> KnmiUvSensorDescription:
    return KnmiUvSensorDescription(
        key=f"uv_day_{index}",
        name=_day_name(index),
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UV_INDEX,
        suggested_display_precision=1,
        value_fn=lambda data, n=index: data.days[n].uv_sunny if n < len(data.days) else None,
        attrs_fn=lambda data, n=index: (
            {
                "date": data.days[n].day.isoformat(),
                "uv_cloudy": data.days[n].uv_cloudy,
                "description": data.days[n].description,
            }
            if n < len(data.days)
            else {}
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KnmiUvConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KNMI UV Index sensors."""
    coordinator = entry.runtime_data
    num_days = len(coordinator.data.days) if coordinator.data else 0

    entities: list[KnmiUvSensor] = [KnmiUvSensor(coordinator, CURRENT_SENSOR)]
    entities.extend(KnmiUvSensor(coordinator, _make_day_sensor(i)) for i in range(num_days))
    async_add_entities(entities)


class KnmiUvSensor(KnmiUvEntity, SensorEntity):
    """A KNMI UV Index sensor."""

    entity_description: KnmiUvSensorDescription

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
