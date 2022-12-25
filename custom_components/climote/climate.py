import logging
from .const import DOMAIN
from homeassistant.helpers.entity import DeviceInfo
from datetime import timedelta
from homeassistant.util import Throttle

# If climate needs this, number probably does too
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
)

_LOGGER = logging.getLogger(__name__)

# TODO look into what all of this is for
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)
SCAN_INTERVAL = MIN_TIME_BETWEEN_UPDATES
#: Interval in hours that module will try to refresh data from the climote.
CONF_REFRESH_INTERVAL = "refresh_interval"
NOCHANGE = "nochange"
ICON = "mdi:thermometer"

MAX_TEMP = 75
MIN_TEMP = 0

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


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

    # interval = int(config.get(CONF_REFRESH_INTERVAL))

    # Add devices (these arent really devices.... are they? is a zone a device?)
    entities = []

    if not climotesvc.zones:
        # TODO proper error handling
        raise Exception("There should have been zones by now")

    for zone_id, region in climotesvc.zones.items():
        entities.append(ClimoteEntity(climotesvc, zone_id, region))
    _LOGGER.info("3. Found entities %s", entities)

    add_entities(entities)
    # async_add_entities??
    return True


class ClimoteEntity(ClimateEntity):
    """Representation of a Climote device."""

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
        self.throttled_update = Throttle(
            timedelta(minutes=self._climote.refresh_interval)
        )(self._throttled_update)
        self._unique_id = f"climote_climate_{self._climote.device_id}_{self._zoneid}"

    @property
    def should_poll(self):
        return True

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def hvac_mode(self):
        """Return current operation. ie. heat, cool, off."""
        zone = "zone" + str(self._zoneid)
        _LOGGER.debug(self._climote.data)
        return "heat" if self._climote.data[zone]["status"] == "5" else "off"

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return SUPPORT_MODES

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
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

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
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

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
            CURRENT_HVAC_HEAT
            if self._climote.data[zone]["status"] == "5"
            else CURRENT_HVAC_IDLE
        )

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_HEAT:
            """Turn Heating Boost On."""
            res = self._climote.boost_new(self._zoneid)
            # res = self._climote.boost(self._zoneid, 1)
            if res:
                self._force_update = True
            return res
        if hvac_mode == HVAC_MODE_OFF:
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

    def update(self):
        self._climote.updateStatus(self._force_update)

    # TODO look into what this is and how update above works
    async def _throttled_update(self, **kwargs):
        """Get the latest state from the thermostat with a throttle."""
        _LOGGER.info("_throttled_update Force: %s", self._force_update)
        self._climote.updateStatus(self._force_update)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN),
                self._climote.device_id,
            },
            name="Climote Hub",
            manufacturer="Climote",
            model="Remote Heating Controller",
        )
