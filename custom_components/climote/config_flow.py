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
from .climote_service_stub import ClimoteService as ClimoteServiceStub
from .const import (
    BOOST_DURATION,
    CLIMOTE_ID,
    DOMAIN,
    PASSWORD,
    REFRESH_INTERVAL,
    USERNAME,
)

_LOGGER = logging.getLogger(__name__)
# Temporary testing toggle
TEST = False

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CLIMOTE_ID): str,
        vol.Required(USERNAME): str,
        vol.Required(PASSWORD): str,
        vol.Required(BOOST_DURATION, default=0.5): float,
        vol.Required(REFRESH_INTERVAL, default=24): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    if TEST:
        climote = ClimoteServiceStub
    else:
        climote = ClimoteService

    temp_climote_object = climote(
        data[CLIMOTE_ID], data[USERNAME], data[PASSWORD], _LOGGER, 12, 1
    )

    try:
        auth_successful = await hass.async_add_executor_job(
            temp_climote_object.test_authenticate
        )
    except climote.TimeoutException as exc:
        raise CannotConnect from exc

    if not auth_successful:
        raise InvalidAuth

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

    # https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#reauthentication
    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        reauth_schema = vol.Schema(
            {
                vol.Required(USERNAME, default=self.init_data.get(USERNAME)): str,
                vol.Required(PASSWORD, default=self.init_data.get(PASSWORD)): str,
            }
        )

        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=reauth_schema,
            )
        return await self.async_step_user(user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Copy the data that wasn't up for modification
            user_input[CLIMOTE_ID] = self.config_entry.data[CLIMOTE_ID]
            user_input[BOOST_DURATION] = self.config_entry.data[BOOST_DURATION]

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
                    REFRESH_INTERVAL,
                    default=self.config_entry.data.get(REFRESH_INTERVAL),
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=update_data_schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
