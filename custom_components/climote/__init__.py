"""The Climate Climote integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    USERNAME,
    PASSWORD,
    CLIMOTE_ID,
    REFRESH_INTERVAL,
    BOOST_DURATION,
)

from .climote_service import ClimoteService

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.NUMBER]
import logging

_LOGGER = logging.getLogger(__name__)

# This seems to replace async_setup (which was used for configuration.yaml based settings)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Climate Climote from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.info(f"async_setup_entry UniqueID [{entry.unique_id}] Data [{entry.data}]")

    # TODO: Why did I end up back in here when I updated the configuration (when the entry previously didnt exist), I then didnt have a climote # as its not in my options flow.
    # NOW its happening when I refresh the page?
    # 1. Create API instance
    username = entry.data[USERNAME]
    password = entry.data[PASSWORD]
    climoteid = entry.data[CLIMOTE_ID]
    refresh_interval = entry.data[REFRESH_INTERVAL]
    default_boost_duration = entry.data[BOOST_DURATION]

    climote_svc = ClimoteService(
        username,
        password,
        climoteid,
        _LOGGER,
        refresh_interval=refresh_interval,
        default_boost_duration=default_boost_duration,
    )

    # 2. Validate the API connection (and authentication)
    # This now does the first HTTP request
    # if not (climote_svc.initialize()):
    #    return False

    init_successful = await hass.async_add_executor_job(climote_svc.initialize)
    if not init_successful:
        a = 1
        return False
        # TODO should this raise? or return can read to find out
        # raise ConfigEntryNotReady

    # 3. Store an API object for your platforms to access
    # TODO consider using a coordinator rather than class directly
    hass.data[DOMAIN][entry.entry_id] = climote_svc

    # 4. Delegate setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
