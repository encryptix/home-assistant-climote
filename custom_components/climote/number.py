import logging
from .const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.number import NumberEntity

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:clock"


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
        entities.append(BoostDuration(climotesvc, zone_id, region))
    _LOGGER.info("3. Found entities %s", entities)

    add_entities(entities)
    return True


# Could have also used a select entity with predefined durations
class BoostDuration(NumberEntity):
    """Representation of how long the boost time is for a zone."""

    @property
    def native_value(self) -> float:
        """Return value of number."""
        # return cast(float, self.attribute_value)
        if self.cur_val_a:
            return self.cur_val_a
        else:
            return self.default_boost

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        a = 1
        self._climote.setZoneBoostTime(self._zoneid, value)
        self.cur_val_a = value
        # self.async_write_ha_state()

    def __init__(self, climote_service, zone_id, name):
        """Initialize the thermostat."""
        _LOGGER.info(
            "Initialize Climote Number Entity %s - %s - %s"
            % (climote_service.device_id, zone_id, name)
        )
        self._climote = climote_service
        self._zoneid = zone_id
        self._name = f"climote_{self._climote.get_sanitized_device_id()}_{name}"
        self._unique_id = f"climote_number_{self._climote.device_id}_{self._zoneid}"

        # TODO set default
        self.default_boost = self._climote.default_boost_duration
        self.cur_val_a = None

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
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._climote.device_id)},
            name="Climote Hub",
            manufacturer="Climote",
            model="Remote Heating Controller",
        )
