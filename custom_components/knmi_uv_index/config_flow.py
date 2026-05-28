"""Config flow for the KNMI UV Index integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import KnmiUvClient
from .const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_SCAN_INTERVAL,
    CONF_ZONE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    REGISTER_URL,
)
from .coordinator import KnmiUvConfigEntry
from .errors import KnmiAuthError, KnmiConnectionError

_LOGGER = logging.getLogger(__name__)

_API_KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _zone_choices(hass: HomeAssistant) -> list[SelectOptionDict]:
    """Build dropdown options from the available Home Assistant zones."""
    options: list[SelectOptionDict] = []
    for state in hass.states.async_all("zone"):
        label = state.attributes.get("friendly_name") or state.entity_id
        options.append(SelectOptionDict(value=state.entity_id, label=str(label)))
    if not options:
        options.append(SelectOptionDict(value="zone.home", label="Home"))
    return options


def _default_zone(options: list[SelectOptionDict]) -> str:
    """Return the default zone (Home if present)."""
    if any(option["value"] == "zone.home" for option in options):
        return "zone.home"
    return options[0]["value"]


def _resolve_zone(hass: HomeAssistant, zone_entity_id: str) -> tuple[float, float, str]:
    """Resolve a zone entity id to (latitude, longitude, name)."""
    state = hass.states.get(zone_entity_id)
    if state is not None:
        latitude = state.attributes.get("latitude")
        longitude = state.attributes.get("longitude")
        name = state.attributes.get("friendly_name") or zone_entity_id
        if latitude is not None and longitude is not None:
            return float(latitude), float(longitude), str(name)
    return float(hass.config.latitude), float(hass.config.longitude), "Home"


class KnmiUvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KNMI UV Index."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the API key step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = KnmiUvClient(session, user_input[CONF_API_KEY])
            try:
                await client.async_validate_key()
            except KnmiAuthError:
                errors["base"] = "invalid_auth"
            except KnmiConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception validating KNMI API key")
                errors["base"] = "unknown"
            else:
                self._api_key = user_input[CONF_API_KEY]
                return await self.async_step_location()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): _API_KEY_SELECTOR}),
            errors=errors,
            description_placeholders={"register_url": REGISTER_URL},
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the location selection step."""
        options = _zone_choices(self.hass)

        if user_input is not None:
            zone_id = user_input[CONF_ZONE]
            latitude, longitude, name = _resolve_zone(self.hass, zone_id)
            await self.async_set_unique_id(f"{latitude:.3f}_{longitude:.3f}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"KNMI UV Index ({name})",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_LATITUDE: latitude,
                    CONF_LONGITUDE: longitude,
                    CONF_LOCATION_NAME: name,
                    CONF_ZONE: zone_id,
                },
                options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
            )

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE, default=_default_zone(options)): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: KnmiUvConfigEntry) -> KnmiUvOptionsFlow:
        """Get the options flow for this handler."""
        return KnmiUvOptionsFlow()


class KnmiUvOptionsFlow(OptionsFlow):
    """Handle KNMI UV Index options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage update interval and location."""
        entry = self.config_entry
        options = _zone_choices(self.hass)

        if user_input is not None:
            zone_id = user_input[CONF_ZONE]
            latitude, longitude, name = _resolve_zone(self.hass, zone_id)
            self.hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_LATITUDE: latitude,
                    CONF_LONGITUDE: longitude,
                    CONF_LOCATION_NAME: name,
                    CONF_ZONE: zone_id,
                },
            )
            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        current_zone = entry.data.get(CONF_ZONE) or _default_zone(options)
        if not any(option["value"] == current_zone for option in options):
            current_zone = _default_zone(options)
        current_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE, default=current_zone): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    ),
                    vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    ),
                }
            ),
        )
