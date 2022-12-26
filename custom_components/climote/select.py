import logging
from .const import DOMAIN, VALID_BOOST_VALUES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.select import SelectEntity

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
        entities.append(BoostDuration(climotesvc, zone_id, region))
    _LOGGER.info("3. Found entities %s", entities)

    add_entities(entities)
    return True


# Could have also used a select entity with predefined durations
class BoostDuration(SelectEntity):
    """Representation of how long the boost time is for a zone."""

    _attr_icon = "mdi:clock"

    _attr_options = VALID_BOOST_VALUES

    @property
    def current_option(self) -> str:
        return self.cur_select

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        # If this was more complicated I would make a mapping
        self._climote.setZoneBoostTime(self._zoneid, option)
        self.cur_select = option

    def __init__(self, climote_service, zone_id, name):
        """Initialize the thermostat."""
        _LOGGER.info(
            "Initialize Climote Select Entity %s - %s - %s"
            % (climote_service.device_id, zone_id, name)
        )
        self._climote = climote_service
        self._zoneid = zone_id
        self._name = f"climote_{self._climote.get_sanitized_device_id()}_{name}"
        self._unique_id = f"climote_select_{self._climote.device_id}_{self._zoneid}"
        self.cur_select = self._climote.default_boost_duration

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
