"""Client for connection with rapidpro"""

from django.conf import settings

from marketplace.clients.base import RequestClient
from marketplace.interfaces.rapidpro.protocol import RapidproClientProtocol


class Authentication(RequestClient):
    def __get_module_token(self):
        token = settings.RAPIDPRO_API_TOKEN
        return f"Token {token}"

    @property
    def headers(self):
        return {
            "Content-Type": "application/json; charset: utf-8",
            "Authorization": self.__get_module_token(),
        }


class RapidproClient(RequestClient, RapidproClientProtocol):
    def __init__(self):
        self.base_url = settings.RAPIDPRO_URL
        self.authentication_instance = Authentication()

    def send_alert(self, incident_name: str, monitor_name: str, details: dict):
        data = {
            "flow": settings.RAPIDPRO_FLOW_UUID,
            "groups": [settings.RAPIDPRO_FLOW_GROUP_UUID],
            "extra": {
                "incident_name": incident_name,
                "monitor_name": monitor_name,
                "status": "Down",
                "details": details,
            },
        }
        url = f"{self.base_url}/api/v2/flow_starts.json"

        response = self.make_request(
            url,
            method="POST",
            headers=self.authentication_instance.headers,
            json=data,
        )
        return response
