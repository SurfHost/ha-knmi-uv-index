"""Base entity for the KNMI UV Index integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_LOCATION_NAME, DOMAIN, MANUFACTURER
from .coordinator import KnmiUvCoordinator


class KnmiUvEntity(CoordinatorEntity[KnmiUvCoordinator]):
    """Base entity for KNMI UV Index sensors."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: KnmiUvCoordinator, description: EntityDescription) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        location_name = entry.data.get(CONF_LOCATION_NAME, "KNMI")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"KNMI UV {location_name}",
            manufacturer=MANUFACTURER,
            model="UV index forecast",
            entry_type=DeviceEntryType.SERVICE,
        )
