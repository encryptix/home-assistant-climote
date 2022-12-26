# Test version of climote_service, eventually would be replaced by something else
import requests
import json
import datetime

DEFAULT_BOOST_DURATION = "0.5"
DEFAULT_REFRESH_INTERVAL = 12

# This would eventually be a python package, nothing HA specific in it
class ClimoteService:
    _climote_service_instances = {}

    @staticmethod
    def update_instance(
        passcode,
        username,
        password,
        refresh_interval,
    ):
        instance = ClimoteService._climote_service_instances.get(passcode, None)
        instance.creds = {
            "password": username,
            "username": passcode,
            "passcode": password,
        }
        instance.refresh_interval = instance.hours_to_seconds(refresh_interval)
        instance.logged_in = False
        instance.update_in_progress = False
        instance.last_update_complete = None
        instance.seconds_since_update = None

    @staticmethod
    def get_instance(
        passcode,
        username,
        password,
        logger,
        refresh_interval: DEFAULT_REFRESH_INTERVAL,
        default_boost_duration: DEFAULT_BOOST_DURATION,
    ):
        if not ClimoteService._climote_service_instances.get(passcode, None):
            ClimoteService._climote_service_instances[passcode] = ClimoteService(
                passcode,
                username,
                password,
                logger,
                refresh_interval=refresh_interval,
                default_boost_duration=default_boost_duration,
            )

        return ClimoteService._climote_service_instances[passcode]

    class TimeoutException(RuntimeError):
        def __init__(self, arg):
            self.args = arg

    def __init__(
        self,
        passcode,
        username,
        password,
        logger,
        refresh_interval: DEFAULT_REFRESH_INTERVAL,
        default_boost_duration: DEFAULT_BOOST_DURATION,
    ):
        self.s = requests.Session()
        self.s.headers.update(
            {"User-Agent": "Mozilla/5.0 Home Assistant Climote Service"}
        )
        self.config_id = None
        self.config = None
        self.logged_in = False
        self.creds = {"password": username, "username": passcode, "passcode": password}
        self.data = json.loads(_DEFAULT_JSON)
        self.zones = None
        self.zones_boost_duration = {}
        global _LOGGER
        _LOGGER = logger

        self.device_id = passcode
        self.refresh_interval = self.hours_to_seconds(refresh_interval)
        self.default_boost_duration = default_boost_duration

        self.update_in_progress = False
        self.last_update_complete = None
        self.last_update_attempt = None
        self.seconds_since_update = None

    def hours_to_seconds(self, hours):
        return hours * 60 * 60

    @staticmethod
    def sanitized_device_id(device_id):
        return f"******{device_id[-4:]}"

    def get_sanitized_device_id(self):
        return ClimoteService.sanitized_device_id(self.device_id)

    def initialize(self):
        # Set to false to simulate a failed login
        # return False
        try:
            self.__login()
            self.__setConfig()
            self.__setZones()
            self.updateStatus(force=False)
            return True if (self.config is not None) else False
        finally:
            self.__logout()

    def test_authenticate(self):
        return True
        # return False
        # raise TimeoutException("Test exception")

    def setZoneBoostTime(self, zone, duration: str):
        self.zones_boost_duration[zone] = float(duration)

    def __login(self):
        return True
        # raise TimeoutException("Test exception")

    def __logout(self):
        return True

    def boost(self, zoneid):
        _LOGGER.info("Boosting Zone %s", zoneid)
        time = self.zones_boost_duration.get(zoneid, self.default_boost_duration)
        self.set_hvac_mode_on(zoneid)
        return self.__boost(zoneid, time)

    def off(self, zoneid, time):
        _LOGGER.info("Turning Off Zone %s", zoneid)
        self.set_hvac_mode_off(zoneid)
        return self.__boost(zoneid, time)

    def set_hvac_mode_on(self, zoneid):
        zone = "zone" + str(zoneid)
        self.data[zone]["status"] = "5"

    def set_hvac_mode_off(self, zoneid):
        zone = "zone" + str(zoneid)
        self.data[zone]["status"] = "null"

    def set_temp_data(self, zoneid, temp):
        zone = "zone" + str(zoneid)
        self.data[zone]["thermostat"] = temp

    def getStatus(self, force):
        # TODO: what uses this method?
        try:
            self.__login()
            _LOGGER.info("Beginning Get Status")
            self.__getStatus(force=True)
            _LOGGER.info("Ended Get Status")
        finally:
            self.__logout()

    def updateStatus(self, force):
        try:
            self.__login()
            _LOGGER.info("Beginning Update Status")
            self.__updateStatus(force=True)
            _LOGGER.info("Ended Update Status")
        finally:
            self.update_in_progress = False
            self.__logout()

    def __getStatus(self, force):
        return False

    def __updateStatus(self, force):
        return False

    def __setConfig(self):
        self.config = {}
        return

    def __setZones(self):
        self.zones = {1: "Living", 2: "Bed", 3: "Water"}
        return

    def set_target_temperature(self, zone, temp):
        _LOGGER.debug("set_temperature zome:%s, temp:%s", zone, temp)
        res = False
        try:
            self.__login()
            data = {
                "temp-set-input[" + str(zone) + "]": temp,
                "do": "Set",
                "cs_token_rf": self.token,
            }
            r = self.s.post(_SET_TEMP_URL, data=data)
            _LOGGER.info("set_temperature: %d", r.status_code)
            res = r.status_code == requests.codes.ok
            self.set_temp_data(zone, temp=temp)

        finally:
            self.__logout()
        return res

    def __boost(self, zoneid, time):
        """Turn on the heat for a given zone, for a given number of hours"""
        return True

    # Temporary method until I make a data coordinator and tidy up class
    def attempt_timed_update(self):
        # Last time this method was called
        self.last_update_attempt = datetime.datetime.now()
        # When to allow updates?
        # Only allow updates every X hours, otherwise do nothing
        # (Time of Attempt - Time Last Update) > X hours
        # Also limit concurrently to one with update_in_progress bool
        if self.update_in_progress:
            # Already updating (Should be impossible given HA is singular by default)
            _LOGGER.info("Climote update is already running")

            return False

        if self.last_update_complete:
            self.seconds_since_update = (
                self.last_update_attempt - self.last_update_complete
            ).total_seconds()
            if self.seconds_since_update < self.refresh_interval:
                # Last update was within interval
                _LOGGER.info(
                    "%ds is still within interval %s. Not getting new data"
                    % (self.seconds_since_update, self.refresh_interval)
                )
                return False

        self.update_in_progress = True
        self.updateStatus(True)
        self.last_update_complete = datetime.datetime.now()

        return True


class IllegalStateException(RuntimeError):
    def __init__(self, arg):
        self.args = arg


_DEFAULT_JSON = (
    '{ "holiday": "00", "hold": null, "updated_at": "00:00", '
    '"unit_time": "00:00", "zone1": { "burner": 0, "status": null, '
    '"temperature": "0", "thermostat": 0 }, "zone2": { "burner": 0, '
    '"status": "0", "temperature": "0", "thermostat": 0 }, '
    '"zone3": { "burner": 0, "status": null, "temperature": "0", '
    '"thermostat": 0 } }'
)

# Updated
_LOGGED_IN_JSON_NEW = {
    '{"holiday": "00", "hold": None, "updated_at": "15:15", "unit_time": "15:15", '
    '"zone1": {"burner": 1, "timeRemaining": None, "status": None, "temperature": "17", "thermostat": 0}, '
    '"zone2": {"burner": 1, "timeRemaining": None, "status": None, "temperature": "0", "thermostat": 0}, '
    '"zone3": {"burner": 0, "timeRemaining": None, "status": None, "temperature": False, "thermostat": 0}}'
}

_LOGIN_URL = "https://climote.climote.ie/manager/login"
_LOGOUT_URL = "https://climote.climote.ie/manager/logout"
_SCHEDULE_ELEMENT = "/manager/edit-heating-schedule?heatingScheduleId"

_STATUS_URL = "https://climote.climote.ie/manager/get-status"
_STATUS_FORCE_URL = _STATUS_URL + "?force=1"
_GET_STATUS_FORCE_URL = _STATUS_URL + "?force=0"
_STATUS_RESPONSE_URL = (
    "https://climote.climote.ie/manager/" "waiting-get-status-response"
)
_BOOST_URL = "https://climote.climote.ie/manager/boost"
_SET_TEMP_URL = "https://climote.climote.ie/manager/temperature"
_GET_SCHEDULE_URL = (
    "https://climote.climote.ie/manager/" "get-heating-schedule?heatingScheduleId="
)
