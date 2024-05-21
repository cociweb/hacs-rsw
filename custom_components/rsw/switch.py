"""Support for RESTful switches."""

import logging
import requests
import json
import xmltodict
from homeassistant.components.switch import SwitchEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_RESOURCE, CONF_HEADERS
from homeassistant.helpers.template import Template
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from datetime import timedelta
from urllib.parse import urlencode

_LOGGER = logging.getLogger(__name__)

CONF_BODY_ON = 'body_on'
CONF_BODY_OFF = 'body_off'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCE): cv.url,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_HEADERS): vol.Schema({cv.string: cv.string}),
    vol.Optional(CONF_BODY_ON): cv.template,
    vol.Optional(CONF_BODY_OFF): cv.template,
    vol.Optional('value_template', default=''): cv.template,
    vol.Optional('timeout', default=10): cv.positive_int,
    vol.Optional('unique_id'): cv.string,
    vol.Optional('verify_ssl', default=True): cv.boolean,
    vol.Optional('method', default='get'): cv.string,
    vol.Optional('scan_interval', default=30): cv.time_period,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    resource = config.get(CONF_RESOURCE)
    body_on = config.get(CONF_BODY_ON)
    body_off = config.get(CONF_BODY_OFF)
    headers = config.get(CONF_HEADERS)
    value_template = config.get('value_template')
    if value_template is None or not isinstance(value_template, Template):
        value_template = Template(value_template or '', hass)
    timeout = config.get('timeout')
    unique_id = config.get('unique_id')
    verify_ssl = config.get('verify_ssl')
    method = config.get('method')
    scan_interval = config.get('scan_interval')
    scan_interval_seconds = scan_interval.total_seconds()
    add_entities([MyRestfulSwitch(name, resource, body_on, body_off, headers, value_template, timeout, unique_id, verify_ssl, method, hass, scan_interval_seconds)])

class MyRestfulSwitch(SwitchEntity):
    def __init__(self, name, resource, body_on, body_off, headers, value_template, timeout, unique_id, verify_ssl, method, hass, scan_interval):
        self._name = name
        self._resource = resource
        self._body_on = body_on
        self._body_off = body_off
        self._headers = headers if headers is not None else {}
        self._value_template = value_template
        self._timeout = timeout
        self._unique_id = unique_id
        self._verify_ssl = verify_ssl
        self._method = method
        self._scan_interval = scan_interval
        self._state = None
        self._initialized = False
        self._request_sent = False  # Add this line to initialize the counter
        self.hass = hass
        if self.hass is None:
            _LOGGER.error("Home Assistant instance is None")
        async_call_later(self.hass, 10, self.async_update)  # Schedule the first update after 10 second

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

#    @property
#    def should_poll(self):
#        return False


    async def async_update(self, now=None):
        _LOGGER.debug("RSW Update method called")
        try:
            if not self._request_sent:  # Add this line
                state = str(self._value_template.async_render()).lower()
                _LOGGER.debug("State returned by value_template: %s", state)
                if state in ['true', 'on', '1']:
                    self._state = True
                elif state in ['false', 'off', '0']:
                    self._state = False
                elif state in ['unknown', 'unavailable', '-1']:
                    self._state = None
                    if not self._initialized:
                        _LOGGER.debug("Unexpected state value during initialization: %s", state)
                    else:
                        _LOGGER.error("Got an unexpected state value: %s", state)
                else:
                    _LOGGER.error("Unexpected state value: %s", state)
            self._initialized = True
        except Exception as ex:
            _LOGGER.error("Error fetching state: %s", ex)
        _LOGGER.debug("async_update completed")

    
    def parse_body(self, body_str):
        try:
            json.loads(body_str)
            return 'json', body_str
        except json.JSONDecodeError:
            try:
                xmltodict.parse(body_str)
                return 'xml', body_str
            except Exception:
                _LOGGER.error("The body is not a json or xml, but it's going to be used as a simple string: %s", body_str)
                return 'string', body_str
    

    def is_subset(self, dict1, dict2):
        """Check if dict1 is a subset of dict2."""
        for key, value in dict1.items():
            if key not in dict2:
                _LOGGER.debug("Key %s is not in both dicts", key)
                return False
            if isinstance(value, dict):
                if not isinstance(dict2[key], dict) or not self.is_subset(value, dict2[key]):
                    _LOGGER.debug("Value %s is not a subset of %s", value, dict2[key])
                    return False
            else:
                if str(dict2[key]) != str(value):
                    _LOGGER.debug("Value %s does not match %s where the Key is %s", dict2[key], value, key)
                    return False
        _LOGGER.debug("Dict %s is a subset of %s", dict1, dict2)
        return True


    def handle_response(self, response_text, expected_body):
        """Check if the response text contains the expected body."""
        response_text = str(response_text).lower()
        expected_body = str(expected_body).lower()
        try:
            # Try to parse as JSON
            response_json = json.loads(response_text)
            expected_json = json.loads(expected_body)
            return self.is_subset(expected_json, response_json)
        except json.JSONDecodeError:
            try:
                # If not JSON, try to parse as XML
                response_xml = xmltodict.parse(response_text)
                expected_xml = xmltodict.parse(expected_body)
                return self.is_subset(expected_xml, response_xml)
            except Exception:
                # Fallback to string comparison if not valid JSON or XML
                _LOGGER.debug("There is an exact matching!")
                return response_text == 'true' or response_text == 'on' or response_text == '1' or expected_body in response_text



    def send_request(self, method, resource, headers, body, timeout, verify_ssl):
        _LOGGER.debug("The body is: %s", body)
        _LOGGER.debug("The timeout is: %s", timeout)
        _LOGGER.debug("The url is: %s", resource)
        _LOGGER.debug("The method is: %s", method)
        try:
            if method.lower() == 'get':
                resource = f"{resource}?{urlencode(body)}"
                response = requests.get(resource, headers=headers, timeout=timeout, verify=verify_ssl)
            else:
                body_type, body = self.parse_body(body)  # Call parse_body here
                if body_type == 'json':
                    headers['Content-Type'] = 'application/json'
                elif body_type == 'xml':
                    headers['Content-Type'] = 'application/xml'
                _LOGGER.debug("The headers is: %s", headers)
                response = requests.post(resource, headers=headers, data=body, timeout=timeout, verify=verify_ssl)
            _LOGGER.debug("The response is: %s", response.text)
            return self.handle_response(response.text, body)  # Call handle_response here
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.packages.urllib3.exceptions.MaxRetryError) and \
               isinstance(e.reason, requests.packages.urllib3.exceptions.ProtocolError) and \
               isinstance(e.reason.original_exception, http.client.RemoteDisconnected):
               _LOGGER.error("Remote end closed connection without response")
            else:
               _LOGGER.error("Request failed: %s", e)
            return False


    
    def turn_on(self, **kwargs):
        _LOGGER.debug("turn_on called")
        self._request_sent = True
        body_on = str(self._body_on.render())
        self._state = self.send_request(self._method, self._resource, self._headers, body_on, self._timeout, self._verify_ssl)
        self._request_sent = False
        async_call_later(self.hass, self._scan_interval, self.schedule_update_ha_state)
        _LOGGER.debug("turn_on completed")
    
    def turn_off(self, **kwargs):
        _LOGGER.debug("turn_off called")
        self._request_sent = True
        body_off = str(self._body_off.render())
        self._state = self.send_request(self._method, self._resource, self._headers, body_off, self._timeout, self._verify_ssl)
        self._request_sent = False
        async_call_later(self.hass, self._scan_interval, self.schedule_update_ha_state)
        _LOGGER.debug("turn_off completed")

#    async def async_added_to_hass(self):
#        async_track_time_interval(self.hass, self.async_update, timedelta(seconds=self._poll))
#        await self.async_update()
