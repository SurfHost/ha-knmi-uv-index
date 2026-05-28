"""Config flow for the KNMI UV Index integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import KnmiUvClient
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
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


class KnmiUvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KNMI UV Index."""

    VERSION = 1

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
                return self.async_create_entry(
                    title="KNMI UV Index",
                    data={CONF_API_KEY: user_input[CONF_API_KEY]},
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): _API_KEY_SELECTOR}),
            errors=errors,
            description_placeholders={"register_url": REGISTER_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: KnmiUvConfigEntry) -> KnmiUvOptionsFlow:
        """Get the options flow for this handler."""
        return KnmiUvOptionsFlow()


class KnmiUvOptionsFlow(OptionsFlow):
    """Handle KNMI UV Index options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the update interval."""
        if user_input is not None:
            return self.async_create_entry(
                title="", data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]}
            )

        current_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    )
                }
            ),
        )
