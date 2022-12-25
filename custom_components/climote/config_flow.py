"""Config flow for Climate Climote integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from .climote_service import ClimoteService

from .const import (
    DOMAIN,
    CLIMOTE_ID,
    USERNAME,
    PASSWORD,
    REFRESH_INTERVAL,
    BOOST_DURATION,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CLIMOTE_ID): str,
        vol.Required(USERNAME): str,
        vol.Required(PASSWORD): str,
        vol.Required(BOOST_DURATION, default=0.5): float,
        vol.Required(REFRESH_INTERVAL, default=24): int,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = PlaceholderHub(data[CLIMOTE_ID])

    if not await hub.authenticate(data[USERNAME], data[PASSWORD]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": ClimoteService.sanitized_device_id(data[CLIMOTE_ID])}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Climate Climote."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        if user_input.get(CLIMOTE_ID, None):
            await self.async_set_unique_id("climote_" + user_input[CLIMOTE_ID])
            self._abort_if_unique_id_configured()

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # This line taken from https://github.com/PeteRager/lennoxs30/blob/master/custom_components/lennoxs30/config_flow.py#L303 due to https://community.home-assistant.io/t/configflowhandler-and-optionsflowhandler-managing-the-same-parameter/365582/5
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input, options=self.config_entry.options
            )
            return self.async_create_entry(title="Update Climote", data=user_input)

        update_data_schema = vol.Schema(
            {
                vol.Required(
                    USERNAME, default=self.config_entry.data.get(USERNAME)
                ): str,
                vol.Required(
                    PASSWORD, default=self.config_entry.data.get(PASSWORD)
                ): str,
                vol.Required(
                    BOOST_DURATION,
                    default=self.config_entry.data.get(BOOST_DURATION),
                ): float,
                vol.Required(
                    REFRESH_INTERVAL,
                    default=self.config_entry.data.get(REFRESH_INTERVAL),
                ): int,
            }
        )

        # TODO , Signal Updates https://developers.home-assistant.io/docs/config_entries_options_flow_handler/#signal-updates

        return self.async_show_form(step_id="init", data_schema=update_data_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
