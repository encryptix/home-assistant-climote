import requests
import json
from bs4 import BeautifulSoup
import polling
import xmljson
from lxml import etree as ET

# This would eventually be a python package, nothing HA specific in it
class ClimoteService:
    def __init__(
        self,
        username,
        password,
        passcode,
        logger,
        refresh_interval: 12,
        default_boost_duration: 1,
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
        self.refresh_interval = refresh_interval
        self.default_boost_duration = default_boost_duration

    @staticmethod
    def sanitized_device_id(device_id):
        return f"******{device_id[-4:]}"

    def get_sanitized_device_id(self):
        return ClimoteService.sanitized_device_id(self.device_id)

    def initialize(self):
        try:
            self.__login()
            self.__setConfig()
            self.__setZones()
            self.updateStatus(force=False)
            return True if (self.config is not None) else False
        finally:
            self.__logout()

    def setZoneBoostTime(self, zone, duration):
        self.zones_boost_duration[zone] = duration

    def __login(self):
        return True

        r = self.s.post(_LOGIN_URL, data=self.creds)
        if r.status_code == requests.codes.ok:
            soup = BeautifulSoup(r.content, "lxml")
            input = soup.find("input")  # First input has token "cs_token_rf"
            if len(input["value"]) < 2:
                return False
            self.logged_in = True
            self.token = input["value"]
            str = r.text
            sched = str.find(_SCHEDULE_ELEMENT)
            if sched:
                cut = str.find("&startday", sched)
                str2 = str[sched : -(len(str) - cut)]
                self.config_id = str2[49:]
                _LOGGER.debug("heatingScheduleId:%s", self.config_id)
            return self.logged_in

    def __logout(self):
        return True
        _LOGGER.info("Logging Out")
        r = self.s.get(_LOGOUT_URL)
        _LOGGER.debug("Logging Out Result: %s", r.status_code)
        return r.status_code == requests.codes.ok

    def boost_new(self, zoneid):
        _LOGGER.info("Boosting Zone %s", zoneid)
        time = self.zones_boost_duration.get(zoneid, self.default_boost_duration)
        self.set_hvac_mode_on(zoneid)
        return self.__boost(zoneid, time)

    def boost(self, zoneid, time):
        _LOGGER.info("Boosting Zone %s", zoneid)
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
            self.__logout()

    def __getStatus(self, force):
        return False
        res = None
        tmp = self.s.headers
        try:
            # Make the initial request (force the update)
            if force:
                r = self.s.get(_GET_STATUS_FORCE_URL, data=self.creds)
            else:
                r = self.s.get(_STATUS_URL, data=self.creds)
            if r.text == "0":
                res = False
            else:
                self.data = json.loads(r.text)
                res = True
        except requests.exceptions.ConnectTimeout:
            res = False
        finally:
            self.s.headers = tmp
        return res

    def __updateStatus(self, force):
        return False

        def is_done(r):
            return r.text != "0"

        res = None
        tmp = self.s.headers
        try:
            # Make the initial request (force the update)
            if force:
                r = self.s.post(_STATUS_FORCE_URL, data=self.creds)
            else:
                r = self.s.post(_STATUS_URL, data=self.creds)

            # Poll for the actual result. It happens over SMS so takes a while
            self.s.headers.update({"X-Requested-With": "XMLHttpRequest"})
            r = polling.poll(
                lambda: self.s.post(_STATUS_RESPONSE_URL, data=self.creds),
                step=10,
                check_success=is_done,
                poll_forever=False,
                timeout=3,  # TODO 120
            )
            if r.text == "0":
                res = False
            else:
                self.data = json.loads(r.text)
                res = True
        except polling.TimeoutException:
            res = False
        finally:
            self.s.headers = tmp
        return res

    def __setConfig(self):
        # I added
        self.config = {}
        return
        if self.logged_in is False:
            raise IllegalStateException("Not logged in")

        r = self.s.get(_GET_SCHEDULE_URL + self.config_id)
        data = r.content
        xml = ET.fromstring(data)
        self.config = xmljson.parker.data(xml)

    def __setZones(self):
        default_zone = {"temperature": 1, "status": "5", "thermostat": 0, "active": 1}
        self.zones = {1: "up", 2: "down", 3: "left"}
        return

        if self.config is None:
            return

        zones = {}
        i = 0
        _LOGGER.debug("zoneInfo: %s", self.config["zoneInfo"]["zone"])
        for zone in self.config["zoneInfo"]["zone"]:
            i += 1
            if zone["active"] == 1:
                zones[i] = zone["label"]
        self.zones = zones

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
        res = False
        try:
            self.__login()
            data = {"zoneIds[" + str(zoneid) + "]": time, "cs_token_rf": self.token}
            r = self.s.post(_BOOST_URL, data=data)
            _LOGGER.info("Boosting Result: %d", r.status_code)
            res = r.status_code == requests.codes.ok
        finally:
            self.__logout()
        return res


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
