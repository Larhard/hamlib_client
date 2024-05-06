import json
import requests

class Wavelog:
    def __init__(self, url, api_key, radio_name):
        self._url = url
        self._api_key = api_key
        self._radio_name = radio_name

    def _get_base_request(self):
        return {
            "radio": self._radio_name,
            "key": self._api_key,
        }

    def post_config(self, frequency, mode):
        request = self._get_base_request()
        request["mode"] = mode
        request["frequency"] = frequency
        response = requests.post(f"{self._url}/api/radio", json=request)
        response.raise_for_status()
        return response.json()
