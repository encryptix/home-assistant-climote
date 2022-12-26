import logging
from .const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity

import datetime
from datetime import timedelta
import time
import math

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Set up numbers for device."""
    _LOGGER.info("Setting up climote boost timings through asyncsetupentry")
    _LOGGER.info(
        f"2. async_setup_entry UniqueID [{entry.unique_id}] Data [{entry.entry_id}]"
    )

    climotesvc = hass.data[DOMAIN][entry.entry_id]

    entities = []
    if not climotesvc.zones:
        raise Exception("There should have been zones by now")

    for zone_id, region in climotesvc.zones.items():
        entities.append(BoostRemaining(climotesvc, zone_id, region))
    _LOGGER.info("3. Found entities %s", entities)

    add_entities(entities)
    return True


SCAN_INTERVAL = timedelta(minutes=1)

# Could have also used a select entity with predefined durations
class BoostRemaining(SensorEntity):
    """Representation of how long the boost time is for a zone."""

    _attr_icon = "mdi:clock"

    _attr_native_unit_of_measurement = "min"
    _attr_device_class = "duration"
    # Intentionally None
    _attr_state_class = None

    def __init__(self, climote_service, zone_id, name):
        """Initialize the thermostat."""
        _LOGGER.info(
            "Initialize Climote Sensor Entity %s - %s - %s"
            % (climote_service.device_id, zone_id, name)
        )
        self._climote = climote_service
        self._zoneid = zone_id
        self._name = f"climote_{self._climote.get_sanitized_device_id()}_{name}"
        self._unique_id = f"climote_sensor_{self._climote.device_id}_{self._zoneid}"
        self.measurement = 0

    @property
    def native_value(self) -> float:
        """Return value of number."""
        return self.measurement

    async def async_update(self):
        # These dont really have timezones, they also may not be times as the device time
        # Could be different to real time. Instead they're more like "how old is the info from the device?"
        # Not a "how old is the info compared to now". Not safe to assume that unit_time ~ now but thats what i'll do anyway
        zone_data = self._climote.data.get("zone" + str(self._zoneid), {})
        unit_burn_time_remaining = zone_data.get("timeRemaining", None)
        # unit_burn_time_remaining = 50

        if not unit_burn_time_remaining:
            self.measurement = None
            return

        # Very naive to just do as we dont know when the unit time is from
        # especially if we're only polling > 1 hour, this number wont change
        # And the device may not be syncing too
        # self.measurement = unit_burn_time_remaining

        # Instead I should workout a 'unit_offset' and a 'polling_interval_offset'
        # unit_offset
        # unit_updated goes ahead e.g. 16.02 vs 16.00
        unit_updated = self._climote.data.get("updated_at", None)
        unit_time = self._climote.data.get("unit_time", None)

        # TODO incomplete and what if it goes past mightnight?
        unit_updated_obj = time.strptime(unit_updated, "%H:%M")
        unit_time_obj = time.strptime(unit_time, "%H:%M")

        unit_offset = 0  # TOOD unit_time - unit_updated

        # polling_interval_offset
        last_data_retrieval = self._climote.seconds_since_update
        if last_data_retrieval is None:
            last_data_retrieval = 1
        # Floor version
        # polling_interval_offset = last_data_retrieval // 60
        polling_interval_offset = round(math.ceil(last_data_retrieval / 60), 2)

        self.measurement = unit_burn_time_remaining - (
            unit_offset + polling_interval_offset
        )

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._climote.device_id)},
            name="Climote Hub",
            manufacturer="Climote",
            model="Remote Heating Controller",
        )
