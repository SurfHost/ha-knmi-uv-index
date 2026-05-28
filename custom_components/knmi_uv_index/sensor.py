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

from .const import DEFAULT_MAX_DAYS
from .coordinator import KnmiUvConfigEntry
from .entity import KnmiUvEntity
from .models import UvData


@dataclass(frozen=True, kw_only=True)
class KnmiUvSensorDescription(SensorEntityDescription):
    """Describes a KNMI UV Index sensor entity."""

    value_fn: Callable[[UvData], StateType]
    attrs_fn: Callable[[UvData], dict[str, Any]] | None = None


def _current_attrs(data: UvData) -> dict[str, Any]:
    """Return attributes for the current UV index sensor."""
    return {
        "forecast_time": data.current_time.isoformat() if data.current_time else None,
        "clear_sky_uv_index": data.current_clear,
        "grid_latitude": data.grid_latitude,
        "grid_longitude": data.grid_longitude,
        "source_file": data.source_file,
    }


CURRENT_SENSOR = KnmiUvSensorDescription(
    key="uv_current",
    name="UV index",
    icon="mdi:weather-sunny-alert",
    native_unit_of_measurement=UV_INDEX,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=1,
    value_fn=lambda data: data.current,
    attrs_fn=_current_attrs,
)


def _day_name(day_offset: int) -> str:
    """Human-readable name for a per-day maximum sensor."""
    if day_offset == 0:
        return "Max today"
    if day_offset == 1:
        return "Max tomorrow"
    return f"Max +{day_offset} days"


def _make_day_sensor(day_offset: int) -> KnmiUvSensorDescription:
    """Create a description for the maximum UV index on a forecast day."""
    return KnmiUvSensorDescription(
        key=f"uv_max_day_{day_offset}",
        name=_day_name(day_offset),
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UV_INDEX,
        suggested_display_precision=1,
        value_fn=lambda data, i=day_offset: data.days[i].uv_max if i < len(data.days) else None,
        attrs_fn=lambda data, i=day_offset: {
            "date": data.days[i].day.isoformat() if i < len(data.days) else None
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KnmiUvConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KNMI UV Index sensors."""
    coordinator = entry.runtime_data

    num_days = 0
    if coordinator.data is not None:
        num_days = min(len(coordinator.data.days), DEFAULT_MAX_DAYS)

    entities: list[KnmiUvSensor] = [KnmiUvSensor(coordinator, CURRENT_SENSOR)]
    entities.extend(KnmiUvSensor(coordinator, _make_day_sensor(n)) for n in range(num_days))
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
