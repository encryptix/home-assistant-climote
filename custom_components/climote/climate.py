from datetime import timedelta
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

# TODO switch to data coordinator
# from homeassistant.util import Throttle


_LOGGER = logging.getLogger(__name__)

# this can be passed in when using a data coordinator
# TODO set back to 5 for now
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)
SCAN_INTERVAL = MIN_TIME_BETWEEN_UPDATES

NOCHANGE = "nochange"
ICON = "mdi:thermometer"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ephember thermostat."""
    _LOGGER.info("Setting up climote platform through asyncsetupentry")
    _LOGGER.info(
        f"2. async_setup_entry UniqueID [{entry.unique_id}] Data [{entry.entry_id}]"
    )

    climotesvc = hass.data[DOMAIN][entry.entry_id]

    entities = []
    if not climotesvc.zones:
        # TODO proper error handling
        raise Exception("There should have been zones by now")

    for zone_id, region in climotesvc.zones.items():
        entities.append(ClimoteEntity(climotesvc, zone_id, region))
    _LOGGER.info("3. Found entities %s", entities)

    add_entities(entities)
    return True


# flexit and adax climate.py are good examples
class ClimoteEntity(ClimateEntity):
    """Representation of a Climote device."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_max_temp = 30
    _attr_min_temp = 10
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, climote_service, zone_id, name):
        """Initialize the thermostat."""
        _LOGGER.info(
            "Initialize Climote Entity %s -  %s - %s"
            % (climote_service.device_id, zone_id, name)
        )
        self._climote = climote_service
        self._zoneid = zone_id
        self._name = f"climote_{self._climote.get_sanitized_device_id()}_{name}"
        self._force_update = False
        # self.throttled_update = Throttle(
        #     timedelta(minutes=self._climote.refresh_interval)
        # )(self._throttled_update)
        self._unique_id = f"climote_climate_{self._climote.device_id}_{self._zoneid}"

    @property
    def should_poll(self):
        return True

    @property
    def hvac_mode(self):
        """Return current operation. ie. heat, cool, off."""
        zone = "zone" + str(self._zoneid)
        _LOGGER.debug(self._climote.data)
        return (
            HVACMode.HEAT if self._climote.data[zone]["status"] == "5" else HVACMode.OFF
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
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def current_temperature(self):
        zone = "zone" + str(self._zoneid)
        _LOGGER.info(
            "current_temperature: Zone: %s, Temp %s C",
            zone,
            self._climote.data[zone]["temperature"],
        )
        return (
            int(self._climote.data[zone]["temperature"])
            if self._climote.data[zone]["temperature"] != "--"
            else 0
        )

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        zone = "zone" + str(self._zoneid)
        _LOGGER.info("target_temperature: %s", self._climote.data[zone]["thermostat"])
        return int(self._climote.data[zone]["thermostat"])

    @property
    def hvac_action(self):
        """Return current operation."""
        zone = "zone" + str(self._zoneid)
        return (
            HVACAction.HEATING
            if self._climote.data[zone]["status"] == "5"
            else HVACAction.IDLE
        )

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.HEAT:
            """Turn Heating Boost On."""
            res = self._climote.boost(self._zoneid)
            if res:
                self._force_update = True
            return res
        if hvac_mode == HVACAction.OFF:
            """Turn Heating Boost Off."""
            res = self._climote.off(self._zoneid, 0)
            if res:
                self._force_update = True
            return res

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        res = self._climote.set_target_temperature(self._zoneid, temperature)
        if res:
            self._force_update = True
        return res

    # TODO do I need to switch to this when using coordinator?
    # def async_update(self):
    #     _LOGGER.info(f"ASYNC UPDATE called for {self.unique_id}")
    #     a = 1

    def update(self):
        _LOGGER.info(f"UPDATE called for {self.unique_id}")
        # a = 1
        self._climote.attempt_timed_update()

    # TODO look into what this is and how update above works
    # Upon init, this method is wrapped inside a THrottle
    # Throttle has a time which prevents this being called again during it
    # That way this methof is only going to run once PER entity for the interval
    #
    # What I dont understand is how def update() wasn't forcing a lot of API calls
    # because by default, when polling, its ccalled once per minute
    # Putting the logic of has it been X minutes here simplifies the python class
    # async def _throttled_update(self, **kwargs):
    #     """Get the latest state from the thermostat with a throttle."""
    #     _LOGGER.info("_throttled_update Force: %s", self._force_update)
    #     self._climote.updateStatus(self._force_update)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._climote.device_id)},
            name="Climote Hub",
            manufacturer="Climote",
            model="Remote Heating Controller",
        )
