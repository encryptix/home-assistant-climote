"""The Climate Climote integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

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
PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.NUMBER]
# Temporary testing toggle
TEST = False

# Signal Updates https://developers.home-assistant.io/docs/config_entries_options_flow_handler/#signal-updates
async def update_listener(hass, entry):
    """Handle options update."""

    climoteid = entry.data[CLIMOTE_ID]

    username = entry.data[USERNAME]
    password = entry.data[PASSWORD]
    refresh_interval = entry.data[REFRESH_INTERVAL]

    if TEST:
        climote = ClimoteServiceStub
    else:
        climote = ClimoteService

    climote.update_instance(climoteid, username, password, refresh_interval)


def get_climote_instance(entry):
    climoteid = entry.data[CLIMOTE_ID]

    username = entry.data[USERNAME]
    password = entry.data[PASSWORD]
    refresh_interval = entry.data[REFRESH_INTERVAL]
    default_boost_duration = entry.data[BOOST_DURATION]

    if TEST:
        climote = ClimoteServiceStub
    else:
        climote = ClimoteService

    climote_svc = climote.get_instance(
        climoteid,
        username,
        password,
        _LOGGER,
        refresh_interval=refresh_interval,
        default_boost_duration=default_boost_duration,
    )

    return climote_svc


# This seems to replace async_setup (which was used for configuration.yaml based settings)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Climate Climote from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.info(f"async_setup_entry UniqueID [{entry.unique_id}] Data [{entry.data}]")

    entry.async_on_unload(entry.add_update_listener(update_listener))

    # 1. Create API instance
    climote_svc = get_climote_instance(entry)

    # 2. Validate the API connection (and authentication)
    try:
        init_successful = await hass.async_add_executor_job(climote_svc.initialize)
    except climote_svc.TimeoutException as ex:
        raise ConfigEntryNotReady(ex) from ex

    if not init_successful:
        raise ConfigEntryAuthFailed("Credentials were not accepted")

    # 3. Store an API object for your platforms to access
    # TODO consider using a coordinator rather than class and singleton directly
    hass.data[DOMAIN][entry.entry_id] = climote_svc

    # 4. Delegate setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
